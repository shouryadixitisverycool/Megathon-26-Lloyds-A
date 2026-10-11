"""Evaluation stage for Agent A (spec 8.3-8.4, 10.4, 12, 13, 14, 15, 16, 62).

Every number here is computed on synthetic data. Model selection, calibration and
thresholds were fixed on validation; this module only reads held-out test customers,
the perturbed-generator dataset and an earlier temporal cutoff.
"""

from __future__ import annotations

import json
import time
from datetime import date

import numpy as np
import pandas as pd
from sklearn.metrics import precision_recall_curve, roc_curve
from scipy.stats import ks_2samp

from greenr import config
from greenr.confidence.meta_model import ConfidenceModel
from greenr.confidence.validation import (
    baseline_diagnostics, correctness_support, stress_report, validate_confidence, write_confidence_report,
)
from greenr.contracts import ModelType, Product
from greenr.evaluation import metrics as M
from greenr.evaluation.reports import write_all_reports
from greenr.evaluation.transaction import evaluate_categoriser
from greenr.evaluation.transaction import write_report as write_transaction_report
from greenr.models.propensity import (
    PROXY_ABLATION_FEATURES,
    add_proxy_features,
    load_all,
    population_mask,
    predict_calibrated,
    predict_raw,
    train_product,
)
from greenr.models.transaction_classifier import TransactionCategoriser
from greenr.pipelines import runtime
from greenr.pipelines.customer360 import build_customer360
from greenr.pipelines.run import (
    CATEGORISER_PATH,
    categorise,
    load_tables,
    log,
    raw_only,
    write_json,
    json_value,
    update_timings,
)
from greenr.pipelines.snapshot_provider import row_to_snapshot
from greenr.pipelines.split import make_labels
from greenr.trust.provider import TrustScorer, trust_frame

PRODUCTS = list(Product)
MODEL_TYPES = [ModelType.HEURISTIC, ModelType.LOGISTIC, ModelType.GRADIENT_BOOSTING]
AUDIT_GROUPS = ("age_band", "income_band", "region")
SYNTHETIC_NOTICE = ("All results are computed on synthetic data generated for this demonstration; "
                    "they do not establish real-world predictive performance or eligibility.")

# Missing-data stress scenarios (spec 13, 16.4): columns blanked on held-out rows.
MISSING_SCENARIOS: dict[str, list[str] | float] = {
    "mileage_missing": ["annual_mileage_km", "mileage_is_estimated"],
    "energy_missing": ["electricity_kwh_12m", "gas_kwh_12m", "electricity_trend", "energy_months_present"],
    "home_ownership_unknown": ["home_owner"],
    "sustainability_preference_missing": ["sustainability_preference"],
    "digital_missing": ["paper_statements_3m", "paper_statements_12m", "digital_statement_ratio",
                        "digital_txn_3m_avg", "app_logins_3m_avg", "app_logins_trend", "branch_visits_3m"],
    "random_30pct_cells": 0.3,
}


def _clean(d):
    return json_value(d)


def population(frame: pd.DataFrame, product: Product, split: pd.Series | None = None, which: str | None = None):
    mask, _ = population_mask(frame, product)
    if split is not None and which is not None:
        mask = mask & (split.reindex(frame.index) == which)
    return frame[mask]


def model_metrics(bundle, rows: pd.DataFrame, y: np.ndarray) -> dict:
    """Held-out metrics for each model type, calibrated, at that type's validation-chosen threshold."""
    out = {}
    for mt in MODEL_TYPES:
        p = predict_calibrated(bundle, rows, mt)
        out[mt.value] = M.summary(y, p, threshold=bundle.thresholds[mt])
        if mt is not ModelType.HEURISTIC:
            raw = np.clip(predict_raw(bundle, rows, mt), 0, 1)
            out[mt.value]["brier_uncalibrated"] = M.brier(y, raw)
            out[mt.value]["ece_uncalibrated"] = M.ece(y, raw)
    return out


def mask_columns(rows: pd.DataFrame, spec, seed: int) -> pd.DataFrame:
    out = rows.copy()
    if isinstance(spec, float):
        rng = np.random.default_rng(seed)
        from greenr.pipelines.feature_registry import PROPENSITY_FEATURES
        cols = [c for c in PROPENSITY_FEATURES if c in out.columns]
        m = rng.random((len(out), len(cols))) < spec
        vals = out[cols].to_numpy(dtype="float64", copy=True)
        vals[m] = np.nan
        out[cols] = vals
    else:
        for c in spec:
            if c in out.columns:
                out[c] = np.nan
    return out


def disparity(sub: pd.DataFrame) -> dict:
    rates = sub["selection_rate"].dropna()
    aucs = sub["roc_auc"].dropna()
    gaps = sub["calibration_gap"].dropna()
    return {"selection_rate_range": float(rates.max() - rates.min()) if len(rates) else None,
            "auc_range": float(aucs.max() - aucs.min()) if len(aucs) else None,
            "max_abs_calibration_gap": float(gaps.abs().max()) if len(gaps) else None}


def feature_drift(reference: pd.DataFrame, comparison: pd.DataFrame) -> dict:
    """Descriptive generator-shift diagnostics, separate from predictive performance."""
    from greenr.pipelines.feature_registry import PROPENSITY_FEATURES
    rows = []
    for name in PROPENSITY_FEATURES:
        if name not in reference or name not in comparison:
            continue
        a = pd.to_numeric(reference[name], errors="coerce").replace([np.inf, -np.inf], np.nan)
        b = pd.to_numeric(comparison[name], errors="coerce").replace([np.inf, -np.inf], np.nan)
        clean_a, clean_b = a.dropna(), b.dropna()
        rows.append({"feature": name, "reference_observed": len(clean_a), "comparison_observed": len(clean_b),
                     "reference_missing_rate": float(a.isna().mean()),
                     "comparison_missing_rate": float(b.isna().mean()),
                     "missingness_delta": float(b.isna().mean() - a.isna().mean()),
                     "reference_median": float(clean_a.median()) if len(clean_a) else None,
                     "comparison_median": float(clean_b.median()) if len(clean_b) else None,
                     "ks_statistic": float(ks_2samp(clean_a, clean_b).statistic)
                         if len(clean_a) and len(clean_b) else None})
    return {"reference": "held-out base-generator customers", "comparison": "perturbed-generator customers",
            "reference_customers": len(reference), "comparison_customers": len(comparison), "features": rows,
            "limitation": "Descriptive synthetic distribution changes. KS statistics are not causal effects, real-world drift alerts or eligibility checks."}


def trust_diagnostics(frame: pd.DataFrame, rows_by_product: dict, labels, bundles, scorer: TrustScorer) -> dict:
    out = {}
    for p, rows in rows_by_product.items():
        snaps = [row_to_snapshot(r, config.FEATURE_CUTOFF) for _, r in rows.iterrows()]
        tf = trust_frame(scorer.assess_many(snaps, p)).set_index("customer_id")
        y = labels.loc[rows.index, p.value].to_numpy()
        prob = predict_calibrated(bundles[p], rows)
        tf = tf.reindex(rows.index)
        status_rows = []
        for status, idx in tf.groupby("status").groups.items():
            sel = rows.index.get_indexer(idx)
            status_rows.append({"status": status, "n": int(len(sel)), "share": len(sel) / len(rows),
                                "roc_auc": M.roc_auc(y[sel], prob[sel]), "brier": M.brier(y[sel], prob[sel]),
                                "calibration_gap": float(prob[sel].mean() - y[sel].mean())})
        out[p.value] = {
            "by_status": status_rows,
            "critical_missing_rate": float((~tf["critical_fields_present"].astype(bool)).mean()),
            "high_conflict_rate": float(tf["has_high_conflict"].astype(bool).mean()),
            "ood_flag_rate": float((tf["ood_score"] >= 0.99).mean()),
            "mean_score": float(tf["score"].mean()),
        }
    return out


def stage_evaluate() -> None:
    t0 = time.time()
    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    tables = load_tables(config.RAW_DIR)
    frame = pd.read_parquet(config.PROCESSED_DIR / f"customer360_{config.FEATURE_CUTOFF.isoformat()}.parquet")
    labels = pd.read_parquet(config.PROCESSED_DIR / "labels.parquet")
    split = pd.read_csv(config.PROCESSED_DIR / "split_manifest.csv", dtype=str).set_index("customer_id")["split"]
    bundles = load_all()
    proxies = load_all(variant="proxy")
    detectors = runtime.load_detectors()
    decisions = json.loads((config.ARTIFACT_DIR / runtime.CONFIDENCE_DIR / "decisions.json").read_text())
    audit = tables["customers"].set_index("customer_id")[list(AUDIT_GROUPS)]
    results: dict = {"notice": SYNTHETIC_NOTICE, "products": {}}

    # perturbed generator dataset, processed with the frozen categoriser
    log("processing perturbed-generator dataset")
    ptables = load_tables(config.PERTURBED_DIR)
    categoriser = TransactionCategoriser.load(CATEGORISER_PATH)
    ptxns = categorise(categoriser, ptables["transactions"])
    pframe = build_customer360(raw_only(ptables), ptxns, config.FEATURE_CUTOFF)
    plabels = make_labels(ptables["customer_outcomes"], pframe.index, config.FEATURE_CUTOFF)
    results["feature_drift"] = feature_drift(frame.loc[split.reindex(frame.index) == "test"], pframe)
    write_json(config.REPORTS_DIR / "feature_drift.json", results["feature_drift"])
    pcat_acc = float((ptxns["category"].to_numpy() == ptxns.merge(
        ptables["transaction_truth"], on="transaction_id", how="left")["true_category"].to_numpy()).mean())

    # temporal holdout: retrain at the earlier cutoff on train/validation customers, test at the canonical cutoff
    hframe = pd.read_parquet(config.PROCESSED_DIR / f"customer360_{config.TEMPORAL_HOLDOUT_CUTOFF.isoformat()}.parquet")
    hlabels = make_labels(tables["customer_outcomes"], hframe.index, config.TEMPORAL_HOLDOUT_CUTOFF)

    test_rows = {}
    for p in PRODUCTS:
        log(f"evaluating {p.value}")
        b = bundles[p]
        rows = population(frame, p, split, "test")
        test_rows[p] = rows
        y = labels.loc[rows.index, p.value].to_numpy()
        res: dict = {"selected_model": b.selected_model_type.value, "model_version": b.model_version,
                     "calibration": {"method": b.calibrator.method, "version": b.calibration_version,
                                     "cv_brier": b.calibrator.cv_brier},
                     "thresholds": {k.value: v for k, v in b.thresholds.items()},
                     "validation_metrics": {k.value: v for k, v in b.validation_metrics.items()},
                     "counts": {"n_train": b.n_train, "n_train_positive": b.n_train_positive,
                                "n_validation": b.n_validation, "n_validation_positive": b.n_validation_positive,
                                "n_test": int(len(rows)), "n_test_positive": int(y.sum())},
                     "features": b.features, "notes": b.notes}
        res["test"] = model_metrics(b, rows, y)
        from greenr.models.propensity.shap_audit import audit_shap
        shap_path = config.REPORTS_DIR / "shap" / f"{p.value.lower()}.json"
        shap = audit_shap(b, rows.head(100), shap_path)
        res["shap_audit"] = {"path": str(shap_path.relative_to(config.REPO_ROOT)),
                             "method": shap["method"], "output_space": shap["output_space"],
                             "rows": len(shap["rows"]), "background": shap["background"]}
        p_sel = predict_calibrated(b, rows)
        raw_sel = np.clip(predict_raw(b, rows), 0, 1)
        res["calibration_curve"] = {"before": M.calibration_curve(y, raw_sel).to_dict("records"),
                                    "after": M.calibration_curve(y, p_sel).to_dict("records")}
        if len(np.unique(y)) == 2:
            fpr, tpr, _ = roc_curve(y, p_sel)
            precision, recall, _ = precision_recall_curve(y, p_sel)
            res["ranking_curves"] = {"roc": {"x": fpr.tolist(), "y": tpr.tolist()},
                                     "precision_recall": {"x": recall.tolist(), "y": precision.tolist()}}

        # subgroup diagnostics (audit-only attributes joined here, never model inputs)
        grp = audit.reindex(rows.index)
        res["subgroups"] = {}
        for g in AUDIT_GROUPS:
            sub = M.subgroup_metrics(y, p_sel, grp[g].astype(str).fillna("UNKNOWN").to_numpy(), b.threshold)
            res["subgroups"][g] = {"table": sub.to_dict("records"), "disparity": disparity(sub)}

        # proxy ablation (spec 12.2)
        pb = proxies[p]
        prows = add_proxy_features(frame.loc[rows.index], audit)
        pp = predict_calibrated(pb, prows)
        psub = M.subgroup_metrics(y, pp, grp["income_band"].astype(str).fillna("UNKNOWN").to_numpy(), pb.threshold)
        res["proxy_ablation"] = {
            "without_proxies": res["test"][b.selected_model_type.value],
            "with_proxies": M.summary(y, pp, threshold=pb.threshold),
            "with_proxies_selected_model": pb.selected_model_type.value,
            "income_disparity_without": res["subgroups"]["income_band"]["disparity"],
            "income_disparity_with": disparity(psub),
        }
        res["proxy_ablation"]["delta"] = M.shift_table(res["proxy_ablation"]["without_proxies"],
                                                       res["proxy_ablation"]["with_proxies"])

        # missing-data stress
        res["missing_data"] = {}
        for name, spec in MISSING_SCENARIOS.items():
            masked = mask_columns(rows, spec, config.SEED_PERTURBATION)
            res["missing_data"][name] = M.summary(y, predict_calibrated(b, masked), threshold=b.threshold)

        # generator shift (spec 8.3/8.4)
        prow = population(pframe, p)
        py = plabels.loc[prow.index, p.value].to_numpy()
        res["generator_shift"] = {"in_distribution": {}, "perturbed": {}, "shift": {}}
        for mt in MODEL_TYPES:
            a = res["test"][mt.value]
            bb = M.summary(py, predict_calibrated(b, prow, mt), threshold=b.thresholds[mt])
            res["generator_shift"]["in_distribution"][mt.value] = a
            res["generator_shift"]["perturbed"][mt.value] = bb
            res["generator_shift"]["shift"][mt.value] = M.shift_table(a, bb)

        # temporal holdout (spec 9.3)
        try:
            hsplit = split.copy()
            hb = train_product(hframe, hlabels, hsplit.reindex(hframe.index).fillna("demo"), p)
            res["temporal_holdout"] = {
                "train_cutoff": config.TEMPORAL_HOLDOUT_CUTOFF.isoformat(),
                "test_cutoff": config.FEATURE_CUTOFF.isoformat(),
                "selected_model": hb.selected_model_type.value,
                "test": M.summary(y, predict_calibrated(hb, rows), threshold=hb.threshold),
            }
        except ValueError as exc:
            res["temporal_holdout"] = {"status": "NOT_RUN", "reason": str(exc)}

        # confidence under stress (validation decision itself was made in `train`)
        scen = {}
        pcp = predict_calibrated(b, prow)
        scen["perturbed_generator"] = (runtime.confidence_features(b, prow, pcp, detectors.get(p)),
                                       (pcp >= b.threshold) == (py == 1))
        masked = mask_columns(rows, 0.3, config.SEED_PERTURBATION)
        mcp = predict_calibrated(b, masked)
        scen["missing_data_30pct"] = (runtime.confidence_features(b, masked, mcp, detectors.get(p)),
                                      (mcp >= b.threshold) == (y == 1))
        confidence_path = config.ARTIFACT_DIR / runtime.CONFIDENCE_DIR / f"{p.value.lower()}.joblib"
        test_correct = (p_sel >= b.threshold) == (y == 1)
        constant = decisions[p.value].get("baselines", {}).get("constant_correctness", {}).get("probability")
        decisions[p.value]["held_out_test_baselines"] = baseline_diagnostics(test_correct, p_sel, b.threshold, constant)
        if confidence_path.exists():
            cm = ConfidenceModel.load(confidence_path)
            test_features = runtime.confidence_features(b, rows, p_sel, detectors.get(p))
            decisions[p.value]["held_out_test_diagnostic"] = validate_confidence(
                cm.predict(test_features), test_correct).to_dict()
            stress = stress_report(cm, scen)
            decisions[p.value]["stress"] = {k: v.to_dict() for k, v in stress.items()}
        else:
            from greenr.confidence.validation import ConfidenceValidation
            decisions[p.value]["held_out_test_diagnostic"] = ConfidenceValidation(
                **correctness_support(test_correct), passed=False,
                reasons=[decisions[p.value]["limitation"]]).to_dict()
            decisions[p.value]["stress"] = {
                name: ConfidenceValidation(**correctness_support(correct), passed=False,
                    reasons=[decisions[p.value]["limitation"]]).to_dict()
                for name, (_, correct) in scen.items()}
        res["confidence"] = decisions[p.value]
        results["products"][p.value] = res

    results["perturbed_generator"] = {"customers": int(len(pframe)),
                                      "categorisation_accuracy": pcat_acc,
                                      "config": json.loads((config.PERTURBED_DIR / "generator_config.json").read_text())}

    # trust diagnostics on held-out customers
    log("trust diagnostics")
    from greenr.trust.selection import load_thresholds
    results["trust"] = trust_diagnostics(frame, test_rows, labels, bundles, TrustScorer(
        ood_detectors=detectors, thresholds=load_thresholds(config.ARTIFACT_DIR / "trust_thresholds.json")))

    # transaction categorisation: unseen- vs known-merchant evaluation
    log("transaction categorisation evaluation")
    truth = tables["transactions"][["transaction_id", "merchant_description"]].merge(
        tables["transaction_truth"], on="transaction_id")
    txn_eval = evaluate_categoriser(truth["merchant_description"].tolist(), truth["true_category"].astype(str).tolist(),
                                    truth["merchant_id"].astype(str).tolist(), seed=config.SEED_SPLIT)
    write_transaction_report(txn_eval, config.REPORTS_DIR)
    results["transaction_categorisation"] = txn_eval

    # confidence report
    write_confidence_report({p: {
        **d,
        "validation": validate_confidence_from(d),
        "ablation": pd.DataFrame(d["ablation"]),
        "coefficients": d.get("coefficients"),
        "bucket_thresholds": d.get("bucket_thresholds"),
        "stress": {k: validate_confidence_from({"validation": v}) for k, v in d.get("stress", {}).items()},
    } for p, d in decisions.items()},
        config.REPORTS_DIR / "CONFIDENCE_VALIDATION.md", config.REPORTS_DIR / "confidence_validation.json")

    results = _clean(results)
    write_json(config.REPORTS_DIR / "ml_evaluation.json", results)
    write_all_reports(results, tables)
    update_timings(evaluation_seconds=time.time() - t0)
    log(f"evaluate finished in {time.time() - t0:.0f}s")


def validate_confidence_from(decision: dict):
    """Re-hydrate the stored held-out validation for the markdown report."""
    from greenr.confidence.validation import ConfidenceValidation
    v = decision["validation"]
    fields = ConfidenceValidation.__dataclass_fields__
    return ConfidenceValidation(**{k: v[k] for k in fields if k in v})
