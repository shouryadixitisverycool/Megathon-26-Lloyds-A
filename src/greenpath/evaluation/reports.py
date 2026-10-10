"""Markdown reports generated from evaluation results (spec 2.3 voluntary artefacts, 62).

Writes into the repository root: EVALUATION_REPORT_AGENT_A.md, MODEL_CARD_{EV,GREEN_HOME,SOLAR,PAPERLESS}.md,
LEAKAGE_AUDIT.md, DATA_CARD.md. Numbers are always read from the run, never hand-typed.
"""

from __future__ import annotations

import json
from html import escape
import math
from pathlib import Path

import pandas as pd

from greenpath import config
from greenpath.pipelines.feature_registry import registry_frame

CARD_NAMES = {"EV_FINANCE": "EV", "GREEN_HOME": "GREEN_HOME", "SOLAR_FINANCE": "SOLAR",
              "PAPERLESS_BANKING": "PAPERLESS"}
KEY_METRICS = ["roc_auc", "pr_auc", "brier", "ece", "precision_at_k", "recall_at_k", "lift_at_k",
               "precision", "recall", "f1"]


def f(x, nd=3) -> str:
    if x is None:
        return "n/a"
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return str(x)


def table(rows: list[dict], cols: list[str], header: list[str] | None = None) -> list[str]:
    header = header or cols
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(cols)]
    out += ["| " + " | ".join(f(r.get(c)) for c in cols) + " |" for r in rows]
    return out + [""]


def metrics_table(test: dict) -> list[str]:
    rows = [{"model": m, **v} for m, v in test.items()]
    return table(rows, ["model", *KEY_METRICS, "threshold"],
                 ["model", "ROC-AUC", "PR-AUC", "Brier", "ECE", "P@10%", "R@10%", "Lift@10%",
                  "precision", "recall", "F1", "threshold"])


def product_section(name: str, r: dict, level: str = "##") -> list[str]:
    c = r["counts"]
    sel = r["selected_model"]
    md = [f"{level} {name}", "",
          f"Selected model (by validation ROC-AUC, Brier tie-break): **{sel}** `{r['model_version']}`; "
          f"calibration **{r['calibration']['method']}** `{r['calibration']['version']}` fitted on validation only.",
          f"Train {c['n_train']} ({c['n_train_positive']} positive), validation {c['n_validation']} "
          f"({c['n_validation_positive']}), held-out test {c['n_test']} ({c['n_test_positive']}).", "",
          "**Held-out test metrics** (calibrated probabilities; confusion metrics at each model's validation-chosen F1 threshold):", ""]
    md += metrics_table(r["test"])
    md += ["Calibration effect (selected model, test): Brier "
           f"{f(r['test'][sel].get('brier_uncalibrated'))} → {f(r['test'][sel]['brier'])}, ECE "
           f"{f(r['test'][sel].get('ece_uncalibrated'))} → {f(r['test'][sel]['ece'])}.", ""]
    h, s = r["test"]["HEURISTIC"], r["test"][sel]
    delta_auc = (s["roc_auc"] - h["roc_auc"]
                 if s["roc_auc"] is not None and h["roc_auc"] is not None else None)
    verdict = ("materially better than" if delta_auc is not None and delta_auc > 0.02
               else "lower than" if delta_auc is not None and delta_auc < -0.02
               else "only marginally different from" if delta_auc is not None else "not comparable with")
    md += [f"Baseline comparison: the selected model's ROC-AUC {f(s['roc_auc'])} is {verdict} the heuristic "
           f"baseline ({f(h['roc_auc'])}); logistic baseline {f(r['test']['LOGISTIC']['roc_auc'])}.", ""]
    gs = r["generator_shift"]
    md += ["**Generator shift** (models trained on generator A, scored on perturbed generator B):", ""]
    md += table([{"model": m, "auc_a": gs["in_distribution"][m]["roc_auc"], "auc_b": gs["perturbed"][m]["roc_auc"],
                  "pr_a": gs["in_distribution"][m]["pr_auc"], "pr_b": gs["perturbed"][m]["pr_auc"],
                  "d_brier": gs["shift"][m].get("brier"), "d_ece": gs["shift"][m].get("ece"),
                  "d_lift": gs["shift"][m].get("lift_at_k")} for m in gs["in_distribution"]],
                ["model", "auc_a", "auc_b", "pr_a", "pr_b", "d_brier", "d_ece", "d_lift"],
                ["model", "ROC-AUC A", "ROC-AUC B", "PR-AUC A", "PR-AUC B", "ΔBrier", "ΔECE (calibration shift)", "ΔLift@10%"])
    md += ["**Missing-data stress** (selected model, held-out test):", ""]
    md += table([{"scenario": k, **v} for k, v in r["missing_data"].items()],
                ["scenario", "roc_auc", "pr_auc", "brier", "ece", "lift_at_k"],
                ["scenario", "ROC-AUC", "PR-AUC", "Brier", "ECE", "Lift@10%"])
    th = r.get("temporal_holdout", {})
    if "test" in th:
        md += [f"**Temporal holdout:** retrained at {th['train_cutoff']}, tested at {th['test_cutoff']} on held-out customers: "
               f"ROC-AUC {f(th['test']['roc_auc'])}, Brier {f(th['test']['brier'])}, ECE {f(th['test']['ece'])}.", ""]
    else:
        md += [f"**Temporal holdout:** not run ({th.get('reason', 'n/a')}).", ""]
    pa = r["proxy_ablation"]
    md += ["**Proxy ablation** (spec 12.2):", ""]
    md += table([{"variant": "without proxies (default)", **pa["without_proxies"], **{k: v for k, v in pa["income_disparity_without"].items()}},
                 {"variant": "with income band + region", **pa["with_proxies"], **{k: v for k, v in pa["income_disparity_with"].items()}}],
                ["variant", "roc_auc", "brier", "ece", "selection_rate_range", "max_abs_calibration_gap"],
                ["variant", "ROC-AUC", "Brier", "ECE", "selection-rate range across income bands", "max |calibration gap| across income bands"])
    dauc = pa["delta"].get("roc_auc")
    md += [f"Decision: default to the model **without** proxies (ΔROC-AUC with proxies = {f(dauc)}); "
           "proxies are not justified unless they add clear value without widening disparity.", ""]
    md += ["**Subgroup diagnostics** (audit-only attributes, selected model):", ""]
    for g, sub in r["subgroups"].items():
        md += [f"*{g}*", ""]
        md += table(sub["table"], ["group", "n", "positives", "roc_auc", "mean_pred", "observed_rate",
                                   "calibration_gap", "selection_rate", "fpr", "fnr"])
    conf = r["confidence"]
    dec = "SURFACED" if conf["surfaced"] else "SUPPRESSED"
    v = conf["validation"]
    md += [f"**Confidence:** {dec} — Spearman(bin, error) {f(v.get('spearman'))}, error top-30% "
           f"{f(v.get('top30_error'))} vs bottom-30% {f(v.get('bottom30_error'))}. See reports/CONFIDENCE_VALIDATION.md.", ""]
    return md


def evaluation_report(results: dict) -> str:
    md = ["# Greenr — Agent A evaluation report (data, ML, reliability)", "",
          f"> {results['notice']}", "",
          f"Feature cutoff {config.FEATURE_CUTOFF}; outcome = adoption within 90 days (to {config.OUTCOME_WINDOW_END}); "
           f"prediction timestamp {config.PREDICTION_TIMESTAMP:%Y-%m-%d}. Customer-level 55/15/15/15 train/validation/confidence-release/test split; release customers reserved before tuning/calibration; demo personas excluded from all fitting and selection. Cohort counts are recorded in reports/dataset_quality.json.", "",
          "## Summary", ""]
    rows = []
    for p, r in results["products"].items():
        sel = r["selected_model"]
        rows.append({"product": p, "selected": sel, "auc": r["test"][sel]["roc_auc"],
                     "heur": r["test"]["HEURISTIC"]["roc_auc"], "logit": r["test"]["LOGISTIC"]["roc_auc"],
                     "brier": r["test"][sel]["brier"], "ece": r["test"][sel]["ece"],
                     "lift": r["test"][sel]["lift_at_k"],
                     "auc_b": r["generator_shift"]["perturbed"][sel]["roc_auc"],
                     "conf": "SURFACED" if r["confidence"]["surfaced"] else "SUPPRESSED"})
    md += table(rows, ["product", "selected", "auc", "heur", "logit", "brier", "ece", "lift", "auc_b", "conf"],
                ["product", "selected", "ROC-AUC", "heuristic AUC", "logistic AUC", "Brier", "ECE", "Lift@10%",
                 "ROC-AUC perturbed", "confidence"])
    tc = results["transaction_categorisation"]
    md += ["## Transaction categorisation", "",
           "Hybrid categoriser (deterministic merchant rules, then TF-IDF + logistic regression). Merchant-group split: "
           "test merchants never seen in training. Full details: reports/TRANSACTION_CATEGORISATION.md.", ""]
    hy = tc.get("models", {}).get("hybrid", {})
    for split_name in ("unseen_merchants", "known_merchants"):
        blk = hy.get(split_name, {})
        if blk:
            md += [f"- {split_name.replace('_', ' ')}: macro F1 {f(blk.get('macro_f1'))}, weighted F1 {f(blk.get('weighted_f1'))}, "
                   f"rule coverage {f(blk.get('rule_coverage'))}"]
    md += [f"- perturbed-generator transactions (frozen categoriser): accuracy {f(results['perturbed_generator']['categorisation_accuracy'])}", ""]
    md += ["## Trust diagnostics (held-out test)", "",
           "Trust measures evidence adequacy and is separate from confidence. Model quality by Trust status:", ""]
    for p, t in results["trust"].items():
        md += [f"*{p}* — mean score {f(t['mean_score'])}, critical-field missing {f(t['critical_missing_rate'])}, "
               f"high-severity conflict {f(t['high_conflict_rate'])}, OOD flag {f(t['ood_flag_rate'])}", ""]
        md += table(t["by_status"], ["status", "n", "share", "roc_auc", "brier", "calibration_gap"])
    md += ["## Per-product detail", ""]
    for p, r in results["products"].items():
        md += product_section(p, r, "###")
    drift = results.get("feature_drift")
    if drift:
        md += ["## Feature and missingness drift", "", drift["limitation"], "",
               "Reference uses held-out base customers; comparison uses independent perturbed-generator customers. "
               "Complete per-feature diagnostics are in reports/feature_drift.json.", ""]
        strongest = sorted(drift["features"], key=lambda row: row.get("ks_statistic") or 0, reverse=True)[:12]
        md += table(strongest, ["feature", "ks_statistic", "reference_median", "comparison_median",
                               "reference_missing_rate", "comparison_missing_rate", "missingness_delta"])
    md += ["## Limitations", "",
           "- Labels are simulated from latent stochastic drivers; relationships are not causal and the "
           "generator's structure bounds what any model can learn.",
           "- Generator-shift and temporal results quantify robustness to *simulated* change only.",
           "- Subgroup diagnostics use synthetic audit attributes; disparities are reported, not hidden or 'fixed'.",
           "- Propensity is interest, not eligibility; confidence is reliability of the propensity decision; "
           "Trust is evidence adequacy. None of these determine financial eligibility.", ""]
    return "\n".join(md)


def model_card(product: str, r: dict) -> str:
    md = [f"# Model card — {product}", "", f"> Synthetic demonstration model. Not for real customer decisions.", "",
          "## Intended use", "",
          f"Estimate the probability that a customer adopts {product} within 90 days of the feature cutoff, "
          "to prioritise relevant sustainability conversations. **Not** an eligibility, credit or suitability decision.", "",
          "## Inputs", "",
          f"{len(r['features'])} approved Customer 360 features (point-in-time at the cutoff): " + ", ".join(f"`{x}`" for x in r["features"]), "",
          "Excluded by policy: exact postcode, income band, region, age band (proxy-risk policy, spec 12), the product's own holding flags, "
          "and any post-cutoff information.", "",
          "## Training", "",
          f"Population: customers not already holding the product at the cutoff. Heuristic baseline, logistic regression and "
          f"histogram gradient boosting trained on the train split; calibration ({r['calibration']['method']}) and the operational "
          "threshold (max F1) fitted on validation only; deployed model chosen on validation.", ""]
    md += product_section("Evaluation", r)
    md += ["## Known limitations", "", "- Synthetic labels; performance does not transfer to real data without re-validation.",
           "- Reason codes summarise the transparent logistic surrogate's positive contributions and controlled thresholds; "
           "they are explanations of evidence, not causal claims.", ""]
    return "\n".join(md)


def leakage_audit(results: dict) -> str:
    checks = json.loads((config.REPORTS_DIR / "leakage_checks.json").read_text())
    pit = checks.pop("point_in_time_rebuild")
    historical = checks.pop("historical_point_in_time", {})
    md = ["# Leakage audit", "", "Automated checks run in `make train`; the run fails on any violation "
          "(implementation: `greenpath.pipelines.leakage_checks`, tests: `tests/pipelines/test_leakage_checks.py` "
          "include deliberately invalid examples that must fail).", "",
          "| Area | Control | Result |", "|---|---|---|",
          f"| Feature provenance | Feature registry records source table, event-time column and availability for each feature (DATA_CARD.md) | documented |",
          f"| Cutoff timing | Customer 360 rebuilt from inputs truncated at {config.FEATURE_CUTOFF} equals production build ({pit['features_compared']} features × {pit['customers_compared']} customers) | **{pit['status']}** |",
           "| Customer split integrity | No customer in more than one of train/validation/confidence-release/test/demo | see below |",
          "| Label construction | Labels = adoption in (cutoff, cutoff+90d] from `customer_outcomes`, a truth table never read by the feature pipeline | by construction + tests |",
          "| Latent-variable leakage | Generator latent traits are never written to any raw table | by construction |",
          "| Target-derived features | No feature name matching adopt/label/target/take_up/outcome | see below |",
          "| Post-adoption flags | Product's own holding flags (holds_*, is_ev, has_existing_solar, is_paperless) excluded from that product's features; used only as population filters | see below |",
          "| Merchant duplication | Categoriser evaluated on a merchant-group split (unseen merchants) | reports/TRANSACTION_CATEGORISATION.md |",
          "| Future information | Vehicle history as-of cutoff; products as-of start/end dates; monthly data only once the month has ended | point-in-time rebuild |",
          "| Proxy / audit attributes | age band, income band, region, postcode excluded from propensity features | see below |", "",
          "## Check results", ""]
    for product, summary in checks.items():
        md += [f"### {product}", ""] + table(summary["checks"], ["check", "target", "status", "detail"])
    if historical:
        md += ["## Historical cutoff rebuilds", ""]
        md += table([{"cutoff": cutoff, **summary} for cutoff, summary in historical.items()],
                    ["cutoff", "status", "features_compared", "customers_compared", "differences"])
    return "\n".join(md)


def data_card(results: dict, tables: dict[str, pd.DataFrame]) -> str:
    gen = json.loads((config.RAW_DIR / "generator_config.json").read_text())
    anchors = gen.get("public_anchors", {})
    public_scope = ("Pinned DESNZ Great Britain domestic-meter electricity and gas annual mean/median; "
                    "aggregate statistical anchors, with no public customer-level data bundled."
                    if anchors else "No public statistical anchor recorded in this dataset manifest.")
    md = ["# Data card", "", "**All data is synthetic.** No real customer, banking or confidential data is used.", "",
          "| Kind | Content |", "|---|---|",
          f"| Observed public data | {public_scope} |",
          "| Synthetic features | customers, transactions, financial_products, vehicles (history), energy_usage, digital_usage |",
          "| Synthetic labels | customer_outcomes: adoption dates simulated from latent stochastic drivers + noise (spec 8.2) |",
          "| Simulator-derived evaluation truth | transaction_truth, merchants (categorisation evaluation only) |", "",
          f"Generator config hash: `{gen.get('config_hash', 'n/a')}`; seed {config.SEED_DATA}; perturbed generator seed {config.SEED_PERTURBATION}.", "",
          "## Tables", "", "| table | rows | sha256 |", "|---|---|---|"]
    hashes = gen.get("file_sha256", gen.get("files", {}))
    for name, df in tables.items():
        h = hashes.get(f"{name}.parquet", hashes.get(name, "")) if isinstance(hashes, dict) else ""
        md.append(f"| {name} | {len(df)} | `{str(h)[:16]}` |")
    if anchors:
        source = anchors.get("energy", {})
        md += ["", "## Public energy anchors", "",
               f"Source: [{source.get('title', 'Public energy statistics')}]({source.get('source_url', '')}). "
               f"Publisher: {source.get('publisher', 'n/a')}; licence: {source.get('licence', 'n/a')}.",
               f"Pinned reference SHA256: `{anchors.get('energy_anchor_sha256', 'n/a')}`.",
               "Annual household demand is sampled from a lognormal distribution matched to public mean and median, "
               "then ranked against synthetic household scores. Gas references apply to gas-consuming households.", "",
               f"Diagnostic calendar year: {anchors.get('diagnostic_year', 'n/a')}. "
               f"{anchors.get('diagnostic_scope', '')}", ""]
        md += table([{"fuel": fuel, **values} for fuel, values in anchors.get("energy_marginal_diagnostics", {}).items()],
                    ["fuel", "n_complete_consumers", "observed_mean_kwh", "reference_mean_kwh",
                     "observed_median_kwh", "reference_median_kwh"])
    reg = registry_frame()
    md += ["", "## Feature registry", "", "Every feature is labelled with source, event time, prediction-time availability and policy (spec 7.3).", ""]
    md += table(reg.to_dict("records"), [c for c in reg.columns if c not in ("description",)])
    md += ["## Limitations", "", "- Aggregate energy anchors constrain demand marginals; behavioural structure remains simulated.",
           "- Synthetic relationships are designed, not observed; they cannot validate real-world performance.", ""]
    return "\n".join(md)


def write_all_reports(results: dict, tables: dict[str, pd.DataFrame]) -> None:
    root = config.REPO_ROOT
    (root / "EVALUATION_REPORT_AGENT_A.md").write_text(evaluation_report(results))
    for p, r in results["products"].items():
        (root / f"MODEL_CARD_{CARD_NAMES[p]}.md").write_text(model_card(p, r))
    (root / "LEAKAGE_AUDIT.md").write_text(leakage_audit(results))
    (root / "DATA_CARD.md").write_text(data_card(results, tables))
    write_plots(results, config.REPORTS_DIR / "plots")


def write_plots(results: dict, directory: Path) -> None:
    """Standalone SVG charts, computed entirely from held-out evaluation records."""
    directory.mkdir(parents=True, exist_ok=True)
    for product, result in results["products"].items():
        calibration = result.get("calibration_curve", {})
        lines = {
            name: [(row["mean_predicted"], row["observed_rate"]) for row in rows if row["n"]]
            for name, rows in calibration.items()
        }
        if lines:
            _write_curve(directory / f"{product.lower()}_calibration.svg", product + " calibration",
                         lines, "Mean predicted probability", "Observed adoption rate", diagonal=True)
        for name, curve in result.get("ranking_curves", {}).items():
            _write_curve(directory / f"{product.lower()}_{name}.svg", product + " " + name.replace("_", " "),
                         {"selected model": list(zip(curve["x"], curve["y"], strict=True))},
                         "False positive rate" if name == "roc" else "Recall",
                         "True positive rate" if name == "roc" else "Precision", diagonal=name == "roc")


def _write_curve(path: Path, title: str, lines: dict, x_label: str, y_label: str,
                 *, diagonal: bool = False) -> None:
    width, height = 640, 460
    left, top, plot_width, plot_height = 80, 55, 500, 320
    def point(x, y):
        return f"{left + float(x) * plot_width:.2f},{top + (1 - float(y)) * plot_height:.2f}"
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
           f'viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">',
           '<rect width="100%" height="100%" fill="white"/>',
           f'<text x="320" y="28" text-anchor="middle" font-family="sans-serif" font-size="18">{escape(title)}</text>']
    for tick in range(6):
        fraction = tick / 5
        x = left + fraction * plot_width
        y = top + (1 - fraction) * plot_height
        svg += [f'<path d="M {x} {top} V {top + plot_height} M {left} {y} H {left + plot_width}" stroke="#e5e7eb" fill="none"/>',
                f'<text x="{x}" y="{top + plot_height + 22}" text-anchor="middle" font-family="sans-serif" font-size="12">{fraction:.1f}</text>',
                f'<text x="{left - 12}" y="{y + 4}" text-anchor="end" font-family="sans-serif" font-size="12">{fraction:.1f}</text>']
    if diagonal:
        svg.append(f'<polyline points="{point(0, 0)} {point(1, 1)}" stroke="#9ca3af" stroke-dasharray="6 4" fill="none"/>')
    for index, (label, values) in enumerate(lines.items()):
        color = ("#047857", "#1d4ed8", "#b45309")[index % 3]
        points = " ".join(point(x, y) for x, y in values
                          if x is not None and y is not None and math.isfinite(x) and math.isfinite(y))
        svg += [f'<polyline points="{points}" stroke="{color}" stroke-width="2.5" fill="none"/>',
                f'<text x="{left + index * 170}" y="{height - 14}" fill="{color}" font-family="sans-serif" font-size="12">{escape(label)}</text>']
    svg += [f'<text x="330" y="424" text-anchor="middle" font-family="sans-serif" font-size="13">{escape(x_label)}</text>',
            f'<text transform="translate(22 215) rotate(-90)" text-anchor="middle" font-family="sans-serif" font-size="13">{escape(y_label)}</text>',
            '</svg>']
    path.write_text("\n".join(svg) + "\n", encoding="utf-8")
