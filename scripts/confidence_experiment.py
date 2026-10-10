"""Isolated, canonical-cutoff confidence experiment (not the full release pipeline).

Generate base/perturbed data with GREENPATH_WORKSPACE set to the same workspace,
then run this script's prepare, train and evaluate stages. Rates, product populations,
calibration and the reserved confidence gate are the normal pipeline's unchanged rules.
Historical/proxy/SHAP/UI certification is deliberately outside this focused experiment.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("prepare", "train", "evaluate"))
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.expanduser().resolve()
    source_root = Path(__file__).resolve().parents[1]
    if workspace == source_root or source_root in workspace.parents:
        parser.error("use an isolated workspace outside the source checkout")
    os.environ["GREENPATH_WORKSPACE"] = str(workspace)

    import json
    import hashlib
    import subprocess
    import time

    import numpy as np
    import pandas as pd

    from greenpath import config
    from greenpath.contracts import Product
    from greenpath.models.propensity import load_all, population_mask, save_all, train_product
    from greenpath.models.transaction_classifier import TransactionCategoriser
    from greenpath.pipelines import run, runtime
    from greenpath.pipelines.customer360 import build_customer360
    from greenpath.pipelines.snapshot_provider import Customer360SnapshotProvider
    from greenpath.pipelines.split import make_labels, split_customers, write_split_manifest

    if config.REPO_ROOT != workspace:
        raise RuntimeError("workspace configuration was imported before isolation was set")
    for path in (config.PROCESSED_DIR, config.ARTIFACT_DIR, config.REPORTS_DIR):
        path.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    frame_path = config.PROCESSED_DIR / f"customer360_{config.FEATURE_CUTOFF.isoformat()}.parquet"

    if args.stage == "prepare":
        from greenpath.models.propensity import PRODUCT_FEATURES
        from greenpath.pipelines.leakage_checks import LeakageError, run_all_checks

        tables = run.load_tables(config.RAW_DIR)
        run.log(f"loaded {len(tables['customers'])} customers; fitting normal merchant reference")
        ref = run.labelled_reference(tables, config.SEED_MODEL)
        categoriser = TransactionCategoriser().fit(ref["merchant_description"].tolist(), ref["true_category"].tolist())
        categoriser.save(config.ARTIFACT_DIR / "transaction_categoriser.joblib")
        del ref
        txns = run.categorise(categoriser, tables["transactions"])
        txns.to_parquet(config.PROCESSED_DIR / "transactions_categorised.parquet")
        raw = run.raw_only(tables)
        run.log("building canonical point-in-time Customer 360")
        frame = build_customer360(raw, txns, config.FEATURE_CUTOFF)
        Customer360SnapshotProvider({config.FEATURE_CUTOFF: frame}).save(config.PROCESSED_DIR)
        labels = make_labels(tables["customer_outcomes"], frame.index, config.FEATURE_CUTOFF,
                             coverage=tables.get("outcome_observation"))
        split = split_customers(frame.index)
        validation_ids = split.index[split == "validation"].sort_values()
        split.loc[np.random.default_rng(config.SEED_SPLIT).permutation(validation_ids)[::3]] = "confidence_release"
        write_split_manifest(split, config.PROCESSED_DIR / "split_manifest.csv")
        labels.to_parquet(config.PROCESSED_DIR / "labels.parquet")
        run.log("checking point-in-time rebuild and leakage")
        pit = run.point_in_time_check(raw, txns, frame, config.FEATURE_CUTOFF)
        if pit["status"] != "PASS":
            raise LeakageError(str(pit))
        sources = run.feature_event_sources(raw, txns, config.FEATURE_CUTOFF)
        checks = {p.value: run_all_checks(cutoff=config.FEATURE_CUTOFF, split=split,
                  event_sources=sources, feature_names=PRODUCT_FEATURES[p], products=[p]) for p in Product}
        run.write_json(config.REPORTS_DIR / "leakage_checks.json", {"point_in_time_rebuild": pit, **checks})
        run.write_json(config.REPORTS_DIR / "experiment_scope.json", {
            "scope": "canonical-cutoff core confidence scaling experiment",
            "split_counts": split.value_counts().to_dict(),
            "not_run": ["historical cutoffs", "proxy ablations", "SHAP", "UI", "full make all"],
            "notice": "All data and outcomes are synthetic; no real-world reliability claim.",
        })

    else:
        frame = pd.read_parquet(frame_path)
        labels = pd.read_parquet(config.PROCESSED_DIR / "labels.parquet")
        split = pd.read_csv(config.PROCESSED_DIR / "split_manifest.csv", dtype=str).set_index("customer_id")["split"]
        if args.stage == "train":
            from greenpath.trust.ood import OODDetector
            from greenpath.trust.selection import select_thresholds

            bundles, detectors = {}, {}
            for p in Product:
                observed = labels[p.value].notna()
                bundles[p] = train_product(frame.loc[observed], labels.loc[observed], split, p)
                mask, _ = population_mask(frame, p)
                rows = frame[mask & split.reindex(frame.index).eq("train")]
                detectors[p] = OODDetector().fit(rows[bundles[p].features])
                detector_path = config.ARTIFACT_DIR / runtime.OOD_DIR / f"{p.value.lower()}.joblib"
                detector_path.parent.mkdir(parents=True, exist_ok=True)
                detectors[p].save(detector_path)
                run.log(f"{p.value}: selected {bundles[p].selected_model_type.value}, threshold {bundles[p].threshold:.6f}")
            save_all(bundles)
            select_thresholds(frame, split, bundles, detectors, config.ARTIFACT_DIR / "trust_thresholds.json")
            decisions = run.train_confidence(frame, labels, split, bundles, detectors)
            run.write_json(config.ARTIFACT_DIR / runtime.CONFIDENCE_DIR / "decisions.json", decisions)
            for product, decision in decisions.items():
                run.log(f"{product}: {'SURFACED' if decision['surfaced'] else 'SUPPRESSED'}; {decision['validation']['reasons']}")
            from greenpath.confidence.validation import ConfidenceValidation, write_confidence_report

            write_confidence_report({p: {**d, "validation": ConfidenceValidation(**d["validation"])}
                                     for p, d in decisions.items()},
                                    config.REPORTS_DIR / "CONFIDENCE_VALIDATION.md",
                                    config.REPORTS_DIR / "confidence_validation.json")

        else:
            from greenpath.confidence.meta_model import METHOD_VERSION, ConfidenceModel
            from greenpath.confidence.validation import (
                ConfidenceValidation, baseline_diagnostics, validate_confidence, write_confidence_report,
            )
            from greenpath.evaluation.ml import mask_columns

            bundles, detectors = load_all(), runtime.load_detectors()
            decisions = json.loads((config.ARTIFACT_DIR / runtime.CONFIDENCE_DIR / "decisions.json").read_text())
            run.log("building independent perturbed-generator features")
            tables = run.load_tables(config.PERTURBED_DIR)
            categoriser = TransactionCategoriser.load(config.ARTIFACT_DIR / "transaction_categoriser.joblib")
            pframe = build_customer360(run.raw_only(tables), run.categorise(categoriser, tables["transactions"]), config.FEATURE_CUTOFF)
            plabels = make_labels(tables["customer_outcomes"], pframe.index, config.FEATURE_CUTOFF,
                                  coverage=tables.get("outcome_observation"))
            del tables
            report = {}
            for p in Product:
                b, d = bundles[p], decisions[p.value]
                cm_path = config.ARTIFACT_DIR / runtime.CONFIDENCE_DIR / f"{p.value.lower()}.joblib"
                if cm_path.exists():
                    cm = ConfidenceModel.load(cm_path)
                    feats, correct, test_prob, _ = run._confidence_rows(frame, labels, split, b, detectors[p], p, "test")
                    d["held_out_test_diagnostic"] = validate_confidence(cm.predict(feats), correct).to_dict()
                    constant = d.get("baselines", {}).get("constant_correctness", {}).get("probability")
                    d["held_out_test_baselines"] = baseline_diagnostics(correct, test_prob, b.threshold, constant)
                    observed = labels[p.value].notna()
                    mask, _ = population_mask(frame, p)
                    test = frame[observed & mask & split.reindex(frame.index).eq("test")]
                    sample = test.head(12)
                    sample_prob = runtime.predict_calibrated(b, sample)
                    bulk = runtime.confidence_features(b, sample, sample_prob, detectors[p])
                    single = pd.concat([runtime.confidence_features(b, sample.iloc[i:i + 1], sample_prob[i:i + 1], detectors[p])
                                        for i in range(len(sample))], ignore_index=True)
                    np.testing.assert_allclose(bulk.to_numpy(), single.to_numpy(), rtol=1e-12, atol=1e-12, equal_nan=True)
                    bulk_values, single_values = cm.predict(bulk), cm.predict(single)
                    np.testing.assert_allclose(bulk_values, single_values, rtol=1e-12, atol=1e-12)
                    assert cm.bucket(bulk_values) == cm.bucket(single_values)
                    d["runtime_equivalence"] = {"rows": len(sample), "single_vs_batch": "PASS",
                                                "confidence_max_abs_difference": float(np.max(np.abs(bulk_values - single_values)))}
                    masked = mask_columns(test, 0.3, config.SEED_PERTURBATION)
                    pmask, _ = population_mask(pframe, p)
                    shifted = pframe[pmask & plabels[p.value].notna()]
                    d["stress"] = {}
                    for name, rows, y in (("missing_data_30pct", masked, labels.loc[test.index, p.value]),
                                          ("perturbed_generator", shifted, plabels.loc[shifted.index, p.value])):
                        prob = runtime.predict_calibrated(b, rows)
                        confidence = cm.predict(runtime.confidence_features(b, rows, prob, detectors[p]))
                        d["stress"][name] = validate_confidence(confidence, (prob >= b.threshold) == y.to_numpy()).to_dict()
                d["deployed_propensity"] = {"model_version": b.model_version, "calibration_version": b.calibration_version,
                                            "operational_threshold": b.threshold}
                report[p.value] = {**d, "validation": ConfidenceValidation(**d["validation"]),
                                   "ablation": pd.DataFrame(d["ablation"]),
                                   "stress": {k: ConfidenceValidation(**v) for k, v in d.get("stress", {}).items()}}
            write_confidence_report(report, config.REPORTS_DIR / "CONFIDENCE_VALIDATION.md",
                                    config.REPORTS_DIR / "confidence_validation.json")
            run.write_json(config.REPORTS_DIR / "confidence_experiment.json", decisions)
            source_hashes = {str(path.relative_to(source_root)): hashlib.sha256(path.read_bytes()).hexdigest()
                             for path in sorted((source_root / "src" / "greenpath").rglob("*.py"))}
            source_hashes["scripts/confidence_experiment.py"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
            run.write_json(config.REPORTS_DIR / "experiment_source.json", {
                "git_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source_root, text=True).strip(),
                "source_sha256": source_hashes,
                "method_version": METHOD_VERSION,
                "scope": "isolated canonical confidence experiment, not full end-to-end release certification",
            })
            run.write_run_manifest()
    run.log(f"{args.stage} completed in {time.perf_counter() - started:.1f}s")


if __name__ == "__main__":
    main()
