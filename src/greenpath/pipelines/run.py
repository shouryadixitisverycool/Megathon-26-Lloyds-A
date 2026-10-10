"""One-command pipeline for Agent A (spec 56.2).

    python -m greenpath.pipelines.run env|train|evaluate|predict|demo|all

``train``    categorise transactions, build Customer 360 (point-in-time), split customers,
             run leakage checks, train heuristic/logistic/boosted models, calibrate on
             validation, fit OOD detectors and the confidence meta-model.
``evaluate`` held-out, generator-shift, missing-data, subgroup, proxy-ablation, temporal,
             categorisation, trust and confidence evaluation + reports/model cards.
``predict``  held-out test predictions, demo persona outputs, portfolio and monthly trend scores.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
import time
from datetime import date
from importlib import metadata
from pathlib import Path

import numpy as np
import pandas as pd

from greenpath import config
from greenpath.confidence.meta_model import ConfidenceModel
from greenpath.confidence.validation import ConfidenceValidation, ablation, validate_confidence
from greenpath.contracts import Product
from greenpath.models.propensity import (
    PROXY_ABLATION_FEATURES,
    add_proxy_features,
    population_mask,
    predict_calibrated,
    save_all,
    save_bundle,
    train_product,
)
from greenpath.models.transaction_classifier import TransactionCategoriser
from greenpath.pipelines import runtime
from greenpath.pipelines.customer360 import build_customer360
from greenpath.pipelines.feature_registry import PROPENSITY_FEATURES
from greenpath.pipelines.leakage_checks import EventSource, LeakageError, run_all_checks
from greenpath.pipelines.schemas import ALL_TABLES, RAW_TABLES, validate_table
from greenpath.pipelines.snapshot_provider import Customer360SnapshotProvider
from greenpath.pipelines.split import make_labels, split_customers, write_split_manifest
from greenpath.trust.ood import OODDetector

PRODUCTS = list(Product)
CATEGORISER_PATH = config.ARTIFACT_DIR / "transaction_categoriser.joblib"
CATEGORISED_PATH = config.PROCESSED_DIR / "transactions_categorised.parquet"
SPLIT_PATH = config.PROCESSED_DIR / "split_manifest.csv"
LABELLED_MERCHANT_FRACTION = 0.7  # simulated manually-labelled merchant reference set
LABELLED_ROW_CAP = 400_000
MIN_CONFIDENCE_ROWS = 200


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_value(obj), indent=2, allow_nan=False) + "\n", encoding="utf-8")


def json_value(o):
    """Convert undefined evaluation metrics to JSON null, never non-standard NaN/Infinity."""
    if isinstance(o, dict):
        return {str(k): json_value(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [json_value(v) for v in o]
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, (float, np.floating)):
        return None if not math.isfinite(float(o)) else float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, (date, pd.Timestamp)):
        return o.isoformat()
    if isinstance(o, np.ndarray):
        return json_value(o.tolist())
    if hasattr(o, "value"):
        return o.value
    return o


# ---- data loading ------------------------------------------------------------------------------

def load_tables(directory: Path) -> dict[str, pd.DataFrame]:
    missing = [n for n in ALL_TABLES if not (directory / f"{n}.parquet").exists()]
    if missing:
        raise FileNotFoundError(f"{directory}: missing {missing}; run `make data`/`make perturbed` first")
    manifest_path = directory / "generator_config.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"{manifest_path}: generator metadata is required for reproducibility")
    manifest = json.loads(manifest_path.read_text())
    for name, expected in manifest.get("file_sha256", {}).items():
        path = directory / name
        if path.name != name or not path.exists() or sha256_file(path) != expected:
            raise ValueError(f"{path}: dataset hash differs from generator manifest; regenerate the dataset")
    tables = {n: pd.read_parquet(directory / f"{n}.parquet") for n in ALL_TABLES}
    for name, df in tables.items():
        validate_table(df, ALL_TABLES[name])
    return tables


def raw_only(tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Feature-pipeline inputs: truth tables are never passed on."""
    return {n: tables[n] for n in RAW_TABLES}


def categorise(categoriser: TransactionCategoriser, txns: pd.DataFrame) -> pd.DataFrame:
    pred = categoriser.predict(txns["merchant_description"].reset_index(drop=True))
    out = txns.reset_index(drop=True).copy()
    out["category"] = pred["category"].to_numpy()
    out["category_confidence"] = pred["category_confidence"].to_numpy()
    out["category_method"] = pred["method"].to_numpy()
    return out


def labelled_reference(tables: dict[str, pd.DataFrame], seed: int,
                       cutoff: date | None = None) -> pd.DataFrame:
    """Simulated manual labelling: a seeded subset of merchant brands with reviewed categories.

    Merchants outside the subset (and all shift-only merchants) stay unlabelled, so the model
    path is exercised on genuinely unseen merchants in production scoring as well.
    """
    merchants = tables["merchants"]
    eligible = merchants.loc[~merchants["is_shift_only"].astype(bool), "merchant_id"].astype(str).sort_values()
    rng = np.random.default_rng(seed)
    labelled = set(rng.choice(eligible.to_numpy(), size=int(len(eligible) * LABELLED_MERCHANT_FRACTION),
                              replace=False).tolist())
    truth = tables["transaction_truth"]
    cutoff = cutoff or min(config.TREND_CUTOFFS + [config.TEMPORAL_HOLDOUT_CUTOFF, config.FEATURE_CUTOFF])
    txns = tables["transactions"]
    txns = txns[txns["date"] <= pd.Timestamp(cutoff)]
    ref = txns[["transaction_id", "merchant_description"]].merge(
        truth[["transaction_id", "merchant_id", "true_category"]], on="transaction_id")
    ref = ref[ref["merchant_id"].astype(str).isin(labelled)]
    if len(ref) > LABELLED_ROW_CAP:
        ref = ref.sample(n=LABELLED_ROW_CAP, random_state=seed)
    return ref


# ---- stages ------------------------------------------------------------------------------------

def stage_env() -> dict:
    if sys.version_info[:2] != (3, 12):
        raise SystemExit(f"Python 3.12 required, found {platform.python_version()}")
    pkgs = {p: metadata.version(p) for p in
            ("numpy", "pandas", "scikit-learn", "scipy", "pydantic", "pyarrow", "joblib")}
    info = {"python": platform.python_version(), "packages": pkgs}
    log(f"environment ok: {info}")
    return info


def stage_train() -> None:
    t0 = time.time()
    timings = {}
    for d in (config.PROCESSED_DIR, config.ARTIFACT_DIR, config.REPORTS_DIR):
        d.mkdir(parents=True, exist_ok=True)
    tables = load_tables(config.RAW_DIR)
    log(f"loaded {len(tables['customers'])} customers, {len(tables['transactions'])} transactions")

    # 1. transaction categorisation (rules + TF-IDF/LogReg) trained on the labelled reference only
    start = time.perf_counter()
    ref = labelled_reference(tables, config.SEED_MODEL)
    if ref.empty:
        raise ValueError("no labelled transactions available before the earliest scoring cutoff")
    categoriser = TransactionCategoriser().fit(ref["merchant_description"].tolist(), ref["true_category"].tolist())
    categoriser.save(CATEGORISER_PATH)
    txns = categorise(categoriser, tables["transactions"])
    txns.to_parquet(CATEGORISED_PATH)
    timings["transaction_categorisation_seconds"] = time.perf_counter() - start
    log(f"categorised transactions ({len(ref)} labelled reference rows, {len(categoriser.rules)} rules)")

    # 2. Customer 360 at every cutoff we need (canonical, temporal holdout, monthly trends)
    raw = raw_only(tables)
    start = time.perf_counter()
    cutoffs = sorted({config.FEATURE_CUTOFF, config.TEMPORAL_HOLDOUT_CUTOFF, *config.TREND_CUTOFFS})
    frames = {c: build_customer360(raw, txns, c) for c in cutoffs}
    Customer360SnapshotProvider(frames).save(config.PROCESSED_DIR)
    frame = frames[config.FEATURE_CUTOFF]
    timings["customer360_seconds"] = time.perf_counter() - start
    log(f"built Customer 360 for {len(cutoffs)} cutoffs ({len(frame)} customers at {config.FEATURE_CUTOFF})")

    # 3. point-in-time verification: rebuilding from data truncated at the cutoff must be identical
    pit = point_in_time_check(raw, txns, frame, config.FEATURE_CUTOFF)
    historical_pit = {c.isoformat(): point_in_time_check(raw, txns, frames[c], c) for c in cutoffs}
    log(f"point-in-time check: {pit['status']}")

    # 4. labels + customer-level split
    labels = make_labels(tables["customer_outcomes"], frame.index, config.FEATURE_CUTOFF)
    split = split_customers(frame.index)
    split_hash = write_split_manifest(split, SPLIT_PATH)
    labels.to_parquet(config.PROCESSED_DIR / "labels.parquet")

    # 5. automated leakage checks (fail the run on any violation)
    leakage = {"point_in_time_rebuild": pit, "historical_point_in_time": historical_pit}
    sources = feature_event_sources(raw, txns, config.FEATURE_CUTOFF)
    for p in PRODUCTS:
        from greenpath.models.propensity import PRODUCT_FEATURES
        leakage[p.value] = run_all_checks(cutoff=config.FEATURE_CUTOFF, split=split,
                                          event_sources=sources,
                                          feature_names=PRODUCT_FEATURES[p], products=[p])
    write_json(config.REPORTS_DIR / "leakage_checks.json", leakage)
    failed = {c: result["differences"] for c, result in historical_pit.items() if result["status"] != "PASS"}
    if failed:
        raise LeakageError(f"point-in-time rebuild differs: {failed}")
    log("leakage checks passed")

    # 6. propensity models (+ proxy ablation variants), calibrated on validation only
    audit = tables["customers"].set_index("customer_id")[["income_band", "region", "age_band"]]
    start = time.perf_counter()
    bundles = {}
    for p in PRODUCTS:
        bundles[p] = train_product(frame, labels, split, p)
        proxy = train_product(add_proxy_features(frame, audit), labels, split, p,
                              extra_features=PROXY_ABLATION_FEATURES, variant="proxy")
        save_bundle(proxy)
        log(f"{p.value}: selected {bundles[p].selected_model_type.value} "
            f"(val AUC {bundles[p].validation_metrics[bundles[p].selected_model_type].get('roc_auc', float('nan')):.3f}), "
            f"calibration {bundles[p].calibrator.method}")
    save_all(bundles)
    timings["propensity_training_seconds"] = time.perf_counter() - start

    # 7. OOD detectors fitted on training rows of each product population
    detectors = {}
    for p in PRODUCTS:
        mask, _ = population_mask(frame, p)
        train_rows = frame[mask & (split.reindex(frame.index) == "train")]
        detectors[p] = OODDetector().fit(train_rows[bundles[p].features])
        path = config.ARTIFACT_DIR / runtime.OOD_DIR / f"{p.value.lower()}.joblib"
        path.parent.mkdir(parents=True, exist_ok=True)
        detectors[p].save(path)

    # 8. confidence meta-model: fit on validation, validate on held-out test, surface only if it passes
    start = time.perf_counter()
    decisions = train_confidence(frame, labels, split, bundles, detectors)
    timings["confidence_training_seconds"] = time.perf_counter() - start
    write_json(config.ARTIFACT_DIR / runtime.CONFIDENCE_DIR / "decisions.json", decisions)
    for p, d in decisions.items():
        log(f"confidence {p}: {'SURFACED' if d['surfaced'] else 'SUPPRESSED'}")

    timings["train_seconds"] = time.time() - t0
    write_json(config.REPORTS_DIR / "pipeline_timings.json", timings)
    write_run_manifest(split_hash)
    log(f"train finished in {time.time() - t0:.0f}s")


def feature_inputs_at_cutoff(raw, txns, cutoff: date):
    """Independent cutoff filtering used by both the audit and rebuild comparison."""
    ts = pd.Timestamp(cutoff)
    month_ok = lambda m: (m + pd.offsets.MonthEnd(0)) <= ts  # noqa: E731
    trunc = dict(raw)
    trunc["financial_products"] = raw["financial_products"][raw["financial_products"]["start_date"] <= ts]
    trunc["vehicles"] = raw["vehicles"][raw["vehicles"]["record_updated_at"] <= ts]
    trunc["energy_usage"] = raw["energy_usage"][month_ok(raw["energy_usage"]["month"])]
    trunc["digital_usage"] = raw["digital_usage"][month_ok(raw["digital_usage"]["month"])]
    return trunc, txns[txns["date"] <= ts]


def feature_event_sources(raw, txns, cutoff: date) -> list[EventSource]:
    trunc, txns = feature_inputs_at_cutoff(raw, txns, cutoff)
    sources = [EventSource("transactions", txns, "date")]
    for name in ("financial_products", "vehicles", "energy_usage", "digital_usage"):
        schema = RAW_TABLES[name]
        sources.append(EventSource(name, trunc[name], schema.event_time_column,
                                   monthly=name in {"energy_usage", "digital_usage"}))
    # A current customer profile is not a historical event: future profiles are masked by
    # Customer 360 rather than dropping the customer identity and its past transactions.
    customers = raw["customers"]
    sources.append(EventSource("customers_available_profiles",
                               customers[customers["record_updated_at"] <= pd.Timestamp(cutoff)],
                               "record_updated_at"))
    return sources


def point_in_time_check(raw, txns, frame, cutoff: date) -> dict:
    """Rebuild Customer 360 from cutoff-filtered inputs and compare (spec 7.3, 8.5)."""
    trunc, txns = feature_inputs_at_cutoff(raw, txns, cutoff)
    rebuilt = build_customer360(trunc, txns, cutoff)
    cols = list(PROPENSITY_FEATURES)
    a = frame[cols].sort_index()
    b = rebuilt.reindex(a.index)[cols]
    diff = ~((a == b) | (a.isna() & b.isna()) | np.isclose(a.fillna(0), b.fillna(0)))
    bad = diff.any(axis=0)
    return {"status": "PASS" if not bad.any() else "FAIL",
            "features_compared": len(cols), "customers_compared": int(len(a)),
            "differences": [c for c in cols if bad[c]],
            "detail": "Customer 360 rebuilt from inputs truncated at the cutoff equals the production build"}


def _confidence_rows(frame, labels, split, bundle, detector, product, which: str):
    mask, _ = population_mask(frame, product)
    rows = frame[mask & (split.reindex(frame.index) == which)]
    y = labels.loc[rows.index, product.value].to_numpy()
    p = predict_calibrated(bundle, rows) if len(rows) else np.array([], dtype=float)
    feats = runtime.confidence_features(bundle, rows, p, detector)
    correct = (p >= bundle.threshold) == (y == 1)
    return feats, correct, p, y


def train_confidence(frame, labels, split, bundles, detectors) -> dict:
    decisions = {}
    out_dir = config.ARTIFACT_DIR / runtime.CONFIDENCE_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    for p in PRODUCTS:
        fv, cv, _, _ = _confidence_rows(frame, labels, split, bundles[p], detectors[p], p, "validation")
        ft, ct, _, _ = _confidence_rows(frame, labels, split, bundles[p], detectors[p], p, "test")
        path = out_dir / f"{p.value.lower()}.joblib"
        if len(cv) < MIN_CONFIDENCE_ROWS or len(np.unique(cv)) < 2:
            limitation = (f"Confidence suppressed: validation has {len(cv)} rows and "
                          f"{len(np.unique(cv))} correctness classes; at least {MIN_CONFIDENCE_ROWS} "
                          "rows and both correct and incorrect decisions are required.")
            path.unlink(missing_ok=True)
            decisions[p.value] = {
                "surfaced": False, "limitation": limitation,
                "validation": ConfidenceValidation(n=len(ct), passed=False, reasons=[limitation]).to_dict(),
                "ablation": [], "coefficients": {}, "bucket_thresholds": {},
                "n_validation": len(cv), "n_test": len(ct),
            }
            continue
        model = ConfidenceModel().fit(fv, cv)
        model.save(path)
        val = validate_confidence(model.predict(ft) if len(ft) else [], ct)
        abl = ablation(fv, cv, ft, ct) if len(ft) else pd.DataFrame()
        limitation = None if val.passed else (
            "Confidence did not show materially lower held-out error at higher confidence; not shown. "
            + "; ".join(val.reasons))
        decisions[p.value] = {
            "surfaced": bool(val.passed), "limitation": limitation,
            "validation": val.to_dict(), "ablation": abl.to_dict("records"),
            "coefficients": model.coefficients(), "bucket_thresholds": model.bucket_thresholds,
            "n_validation": int(len(cv)), "n_test": int(len(ct)),
        }
    return decisions


def update_timings(**values: float) -> None:
    path = config.REPORTS_DIR / "pipeline_timings.json"
    timings = json.loads(path.read_text()) if path.exists() else {}
    timings.update(values)
    write_json(path, timings)


def write_run_manifest(split_hash: str | None = None) -> None:
    gen = json.loads((config.RAW_DIR / "generator_config.json").read_text())
    def hashes(directory: Path) -> dict[str, str]:
        return {str(p.relative_to(config.REPO_ROOT)): sha256_file(p)
                for p in sorted(directory.rglob("*")) if p.is_file()
                and p.name != "RUN_MANIFEST.json"}
    artifacts = hashes(config.ARTIFACT_DIR)
    outputs = hashes(config.REPORTS_DIR)
    outputs.update({p.name: sha256_file(p) for p in sorted(config.REPO_ROOT.glob("*.md"))
                    if p.name.startswith(("MODEL_CARD_", "DATA_CARD", "LEAKAGE_AUDIT", "EVALUATION_REPORT_AGENT_A"))})
    factor_files = {str(p.relative_to(config.REPO_ROOT)): sha256_file(p)
                    for folder in (config.REPO_ROOT / "data" / "factors", config.REPO_ROOT / "config")
                    if folder.exists() for p in sorted(folder.rglob("*"))
                    if p.is_file() and p.suffix in {".yaml", ".yml", ".json", ".csv", ".xlsx"}}
    package_root = Path(__file__).resolve().parents[1]
    for path in (package_root / "extensions" / "uk_factors_2025.json",
                 package_root / "data_generation" / "public_energy_anchor.json"):
        if path.is_file():
            factor_files["greenpath/" + str(path.relative_to(package_root))] = sha256_file(path)
    write_json(config.REPORTS_DIR / "RUN_MANIFEST.json", {
        "seeds": {"data": config.SEED_DATA, "split": config.SEED_SPLIT, "model": config.SEED_MODEL,
                  "perturbation": config.SEED_PERTURBATION},
        "timeline": {"feature_cutoff": config.FEATURE_CUTOFF, "outcome_window_end": config.OUTCOME_WINDOW_END,
                     "prediction_timestamp": config.PREDICTION_TIMESTAMP.isoformat()},
        "generator": gen,
        "split_manifest_sha256": split_hash or sha256_file(SPLIT_PATH),
        "feature_version": config.FEATURE_VERSION,
        "environment": stage_env(),
        "artifacts_sha256": artifacts,
        "inputs_sha256": {**hashes(config.RAW_DIR), **hashes(config.PERTURBED_DIR)},
        "processed_sha256": hashes(config.PROCESSED_DIR),
        "outputs_sha256": outputs,
        "factor_files_sha256": factor_files,
    })


def main(argv: list[str] | None = None) -> None:
    from greenpath.data_generation.__main__ import DEFAULT_CUSTOMERS, generate_dataset

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", nargs="?", default="all",
                        choices=("env", "data", "train", "evaluate", "predict", "demo", "all"))
    parser.add_argument("--customers", type=int, default=DEFAULT_CUSTOMERS,
                        help="synthetic customers per dataset, excluding base demo personas")
    args = parser.parse_args(argv)
    if args.customers < 1:
        parser.error("--customers must be positive")
    stage = args.stage
    started = time.perf_counter()
    if stage in ("env", "all"):
        stage_env()
    if stage in ("data", "all"):
        generate_dataset(customers=args.customers)
        generate_dataset(customers=args.customers, perturbed=True)
    if stage in ("train", "all"):
        stage_train()
    if stage in ("evaluate", "all"):
        from greenpath.evaluation.ml import stage_evaluate
        stage_evaluate()
    if stage in ("predict", "all"):
        from greenpath.pipelines.predict import stage_predict
        stage_predict()
    if stage == "demo":
        from greenpath.pipelines.predict import stage_demo
        stage_demo()
    if stage in ("train", "evaluate", "predict", "all"):
        update_timings(**{f"{stage}_command_seconds": time.perf_counter() - started})
        write_run_manifest()


if __name__ == "__main__":
    main()
