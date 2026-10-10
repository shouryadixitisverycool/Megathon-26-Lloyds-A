"""Held-out validation of the confidence layer (spec 16.4).

Acceptance criteria (implementing "higher-confidence buckets must exhibit materially
lower empirical error than lower-confidence buckets"). Run on HELD-OUT data, never
on the rows the meta-model was fitted on. ``passed`` requires ALL of:

1. n >= ``MIN_ROWS`` (200); otherwise passed=False with a reason.
2. Spearman correlation between confidence-bin rank (1 = lowest confidence) and bin
   error rate <= -0.6 (error falls as confidence rises).
3. error(top 30% confidence) <= 0.5 * error(bottom 30% confidence).
4. error(bottom 30%) >= 0.02, i.e. the baseline error is meaningfully above zero so the
   ratio in (3) is not a degenerate 0 <= 0 pass.

Bins/groups are by confidence rank, preserving ties. Identical scores cannot create
different confidence groups merely because the input rows happen to be ordered.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

from greenpath.confidence.meta_model import FEATURE_COLUMNS, ConfidenceModel

MIN_ROWS = 200
SPEARMAN_MAX = -0.6
RATIO_MAX = 0.5
MIN_BOTTOM_ERROR = 0.02
GROUP_FRAC = 0.30


def _clean(x):
    if isinstance(x, dict):
        return {k: _clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_clean(v) for v in x]
    if isinstance(x, (np.floating, float)):
        return None if not math.isfinite(float(x)) else float(x)
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, np.bool_):
        return bool(x)
    return x


@dataclass
class ConfidenceValidation:
    n: int
    passed: bool
    reasons: list[str] = field(default_factory=list)
    spearman: float = float("nan")
    top30_error: float = float("nan")
    bottom30_error: float = float("nan")
    error_ratio: float = float("nan")
    overall_error: float = float("nan")
    deciles: list[dict] = field(default_factory=list)  # bin, n, mean_confidence, error_rate, accuracy, calibration_gap
    criteria: dict = field(default_factory=dict)
    n_correct: int = 0
    n_incorrect: int = 0
    brier: float = float("nan")
    ece: float = float("nan")  # ten fixed-width probability bins
    calibration_gap: float = float("nan")  # mean probability minus accuracy
    correctness_auc: float = float("nan")

    def to_dict(self) -> dict:
        return _clean(
            {
                "n": self.n, "passed": self.passed, "reasons": self.reasons,
                "spearman": self.spearman, "top30_error": self.top30_error,
                "bottom30_error": self.bottom30_error, "error_ratio": self.error_ratio,
                "overall_error": self.overall_error, "deciles": self.deciles,
                "criteria": self.criteria,
                "n_correct": self.n_correct, "n_incorrect": self.n_incorrect,
                "brier": self.brier, "ece": self.ece,
                "calibration_gap": self.calibration_gap, "correctness_auc": self.correctness_auc,
            }
        )

    def decile_frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.deciles)


def validate_confidence(confidence, correct, n_bins: int = 10) -> ConfidenceValidation:
    """Evaluate whether confidence ranks decision errors (see module docstring)."""
    conf = np.asarray(confidence, dtype=float).reshape(-1)
    ok = np.asarray(correct).astype(bool).reshape(-1)
    if len(conf) != len(ok):
        raise ValueError("confidence and correct differ in length")
    n = len(conf)
    criteria = {
        "min_rows": MIN_ROWS, "spearman_max": SPEARMAN_MAX,
        "top30_error_max_ratio_of_bottom30": RATIO_MAX, "min_bottom30_error": MIN_BOTTOM_ERROR,
    }
    if n_bins < 3:
        raise ValueError("confidence validation needs at least three bins")
    support = correctness_support(ok)
    if not n or not np.isfinite(conf).all() or ((conf < 0) | (conf > 1)).any():
        why = (f"insufficient data: {n} rows < {MIN_ROWS}" if n < MIN_ROWS else
               "confidence values must be finite probabilities in [0, 1]")
        return ConfidenceValidation(**support, passed=False, reasons=[why], criteria=criteria)

    err = (~ok).astype(float)
    rank = pd.Series(conf).rank(method="average").to_numpy() - 1
    bins = np.minimum((rank * n_bins / n).astype(int), n_bins - 1)
    rows = []
    for b in range(n_bins):
        m = bins == b
        if not m.any():
            continue
        e = float(err[m].mean())
        rows.append(
            {"bin": b + 1, "n": int(m.sum()), "mean_confidence": float(conf[m].mean()),
             "error_rate": e, "accuracy": 1 - e, "calibration_gap": float(conf[m].mean() - (1 - e))}
        )
    bottom = conf <= np.quantile(conf, GROUP_FRAC)
    top = conf >= np.quantile(conf, 1 - GROUP_FRAC)
    bottom_err = float(err[bottom].mean())
    top_err = float(err[top].mean())
    ratio = top_err / bottom_err if bottom_err > 0 else float("nan")
    rho = float("nan")
    if len(rows) >= 3:
        er = [r["error_rate"] for r in rows]
        if len(set(er)) > 1:
            rho = float(spearmanr([r["bin"] for r in rows], er).statistic)

    reasons = [f"insufficient data: {n} rows < {MIN_ROWS}"] if n < MIN_ROWS else []
    if (bottom & top).any():
        reasons.append("tied scores do not separate low- and high-confidence groups")
    if not (rho <= SPEARMAN_MAX):
        reasons.append(f"Spearman(bin, error) = {rho:.3f} is not <= {SPEARMAN_MAX}"
                       if math.isfinite(rho) else "Spearman undefined")
    if not (bottom_err >= MIN_BOTTOM_ERROR):
        reasons.append(f"bottom-30% error {bottom_err:.3f} < {MIN_BOTTOM_ERROR}")
    if not (top_err <= RATIO_MAX * bottom_err):
        reasons.append(f"top-30% error {top_err:.3f} is not <= {RATIO_MAX} x bottom-30% error {bottom_err:.3f}")
    probability_bins = np.minimum((conf * 10).astype(int), 9)
    ece = sum(float((probability_bins == b).mean()) *
              abs(float(conf[probability_bins == b].mean() - ok[probability_bins == b].mean()))
              for b in np.unique(probability_bins))
    return ConfidenceValidation(
        **support, passed=not reasons, reasons=reasons, spearman=rho, top30_error=top_err,
        bottom30_error=bottom_err, error_ratio=ratio,
        deciles=rows, criteria=criteria,
        brier=float(np.mean((conf - ok) ** 2)), ece=ece,
        calibration_gap=float(conf.mean() - ok.mean()),
        correctness_auc=float(roc_auc_score(ok, conf)) if len(np.unique(ok)) == 2 else float("nan"),
    )


def correctness_support(correct) -> dict:
    """Counts remain available even when fitting or release validation cannot run."""
    ok = np.asarray(correct).astype(bool).reshape(-1)
    return {"n": len(ok), "n_correct": int(ok.sum()), "n_incorrect": int((~ok).sum()),
            "overall_error": float((~ok).mean()) if len(ok) else float("nan")}


def baseline_diagnostics(correct, propensity, threshold: float, constant_correctness: float | None) -> dict:
    """Fixed baselines only: callers estimate the constant on fitting validation, never here.

    The propensity baseline follows the deployed decision, not max(p, 1-p): the
    operational threshold need not be 0.5. These diagnostics never change release.
    """
    p = np.asarray(propensity, dtype=float)
    out = {"deployed_propensity_correctness": {
        "formula": "where(p >= operational_threshold, p, 1-p)",
        "operational_threshold": float(threshold),
        "validation": validate_confidence(np.where(p >= threshold, p, 1 - p), correct).to_dict(),
    }}
    if constant_correctness is not None:
        out["constant_correctness"] = {
            "probability": float(constant_correctness), "estimated_on": "validation",
            "validation": validate_confidence(np.full(len(p), constant_correctness), correct).to_dict(),
        }
    return out


def ablation(features_df_val, correct_val, features_df_test, correct_test) -> pd.DataFrame:
    """Refit dropping each component; report test AUC for predicting correctness and pass/fail."""
    present = [c for c in FEATURE_COLUMNS if c in features_df_val.columns]
    variants = [("full", None)] + [(f"drop_{c}", c) for c in present]
    y_test = np.asarray(correct_test).astype(int)
    rows = []
    for name, dropped in variants:
        cols = [c for c in present if c != dropped]
        model = ConfidenceModel(feature_columns=cols).fit(features_df_val, correct_val)
        conf = model.predict(features_df_test)
        auc = float(roc_auc_score(y_test, conf)) if len(np.unique(y_test)) > 1 else float("nan")
        v = validate_confidence(conf, correct_test)
        rows.append(
            {"variant": name, "dropped": dropped, "features": ",".join(cols), "test_auc": auc,
             "passed": v.passed, "spearman": v.spearman, "top30_error": v.top30_error,
             "bottom30_error": v.bottom30_error}
        )
    return pd.DataFrame(rows)


def stress_report(model: ConfidenceModel, scenarios: dict) -> dict:
    """Apply ``validate_confidence`` per named scenario ``{name: (features_df, correct)}``.

    Returns ``{name: ConfidenceValidation}`` (use ``.to_dict()`` for JSON).
    """
    return {
        name: validate_confidence(model.predict(feats), correct)
        for name, (feats, correct) in scenarios.items()
    }


def _as_dict(v) -> dict:
    return v.to_dict() if isinstance(v, ConfidenceValidation) else _clean(v)


def write_confidence_report(results: dict, path_md, path_json) -> None:
    """Write markdown + JSON. ``results[product]`` is a ``ConfidenceValidation`` or a dict:

    ``{"validation": ConfidenceValidation, "ablation": DataFrame?, "stress": {name: ConfidenceValidation}?,
    "coefficients": dict?, "bucket_thresholds": dict?}``.
    Decision per product: SURFACED iff the main held-out validation passed, else SUPPRESSED.
    Ablation and stress results are reported alongside (spec 16.4) and do not alter the decision.
    """
    payload, md = {}, ["# Confidence validation report", "",
                       "Confidence = validated probability that the displayed propensity yields a correct "
                       "decision at the operational threshold (spec 16.3). Not eligibility, not a second propensity.", ""]
    for product, res in results.items():
        if isinstance(res, ConfidenceValidation):
            res = {"validation": res}
        val = _as_dict(res["validation"])
        decision = "SURFACED" if val["passed"] else "SUPPRESSED"
        entry = {"decision": decision, "validation": val}
        for key in ("n_validation", "n_release_selection", "release_selection_split",
                    "test_used_for_release_selection", "held_out_test_diagnostic",
                    "held_out_test_baselines", "cohorts", "fitting_status", "release_status", "baselines"):
            if key in res:
                entry[key] = _clean(res[key])
        md += [f"## {product}", "", f"**Decision: {decision}**  (n={val['n']})", ""]
        if res.get("cohorts"):
            md += ["### Cohort support", "", "| cohort | rows | correct | incorrect |", "|---|---|---|---|"]
            md += [f"| {name} | {s['n']} | {s['n_correct']} | {s['n_incorrect']} |"
                   for name, s in res["cohorts"].items()]
            md += ["", f"Fitting: {res.get('fitting_status', 'unknown')}; release: {res.get('release_status', 'unknown')}.",
                   f"Release split: {res.get('release_selection_split', 'unknown')}; test used for release selection: "
                   f"{res.get('test_used_for_release_selection', 'unknown')}.", ""]
        if val["reasons"]:
            md += ["Reasons:"] + [f"- {r}" for r in val["reasons"]] + [""]
        sp, t, b = val["spearman"], val["top30_error"], val["bottom30_error"]
        fmt = lambda x: "n/a" if x is None else f"{x:.3f}"  # noqa: E731
        md += [f"- Spearman(bin, error): {fmt(sp)} (need <= {SPEARMAN_MAX})",
               f"- Error top 30% confidence: {fmt(t)}; bottom 30%: {fmt(b)} (need top <= {RATIO_MAX} x bottom, bottom >= {MIN_BOTTOM_ERROR})", ""]
        md += ["### Held-out correctness diagnostics (do not alter release)", "",
               "ECE uses ten fixed-width probability bins; calibration gap is mean probability minus accuracy.", "",
               "| predictor | Brier | ECE | calibration gap | correctness AUC |", "|---|---|---|---|---|"]
        diagnostic_rows = [("confidence meta-model", val)] + [
            (name, baseline["validation"]) for name, baseline in res.get("baselines", {}).items()]
        md += [f"| {name} | {fmt(v.get('brier'))} | {fmt(v.get('ece'))} | "
               f"{fmt(v.get('calibration_gap'))} | {fmt(v.get('correctness_auc'))} |"
               for name, v in diagnostic_rows]
        md += ["", "Constant baseline is estimated on fitting validation only. Propensity baseline is "
               "q = where(p >= operational threshold, p, 1-p); neither baseline is tuned on release or test.", ""]
        if res.get("held_out_test_diagnostic"):
            md += ["### Held-out test diagnostic (not release selection)", "",
                   "```json", json.dumps(_clean(res["held_out_test_diagnostic"]), indent=2), "```", ""]
        if val["deciles"]:
            md += ["| bin | n | mean confidence | error rate | calibration gap |", "|---|---|---|---|---|"]
            md += [f"| {d['bin']} | {d['n']} | {d['mean_confidence']:.3f} | {d['error_rate']:.3f} | {d['calibration_gap']:+.3f} |"
                   for d in val["deciles"]]
            md.append("")
        if res.get("coefficients"):
            entry["coefficients"] = _clean(res["coefficients"])
            md += ["Standardised coefficients: " + ", ".join(f"{k}={v:+.3f}" for k, v in entry["coefficients"].items()), ""]
        if res.get("bucket_thresholds"):
            entry["bucket_thresholds"] = _clean(res["bucket_thresholds"])
        if res.get("ablation") is not None:
            ab = res["ablation"]
            if not isinstance(ab, pd.DataFrame):
                ab = pd.DataFrame(ab)
            entry["ablation"] = _clean(ab.to_dict(orient="records"))
            md += ["### Ablation", "", "| variant | held-out AUC | passed |", "|---|---|---|"]
            md += [f"| {r['variant']} | {r['test_auc']:.3f} | {r['passed']} |" for r in ab.to_dict(orient="records")]
            md.append("")
        if res.get("stress"):
            entry["stress"] = {k: _as_dict(v) for k, v in res["stress"].items()}
            md += ["### Stress scenarios", "", "| scenario | n | passed | Spearman | top30 err | bottom30 err |", "|---|---|---|---|---|---|"]
            md += [f"| {k} | {v['n']} | {v['passed']} | {fmt(v['spearman'])} | {fmt(v['top30_error'])} | {fmt(v['bottom30_error'])} |"
                   for k, v in entry["stress"].items()]
            md.append("")
        payload[product] = entry
    Path(path_md).parent.mkdir(parents=True, exist_ok=True)
    Path(path_json).parent.mkdir(parents=True, exist_ok=True)
    Path(path_md).write_text("\n".join(md), encoding="utf-8")
    Path(path_json).write_text(json.dumps(payload, indent=2), encoding="utf-8")
