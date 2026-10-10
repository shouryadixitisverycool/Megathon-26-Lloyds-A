"""Validation-only synthetic evidence-scenario selection, not real-world validation."""

from dataclasses import asdict
from itertools import product as grid
import json
from pathlib import Path

import numpy as np

from greenpath import config
from greenpath.contracts import Product
from greenpath.pipelines.snapshot_provider import row_to_snapshot
from greenpath.trust.provider import TrustScorer, TrustThresholds
from greenpath.models.propensity.features import population_mask


def select_thresholds(frame, split, bundles, detectors, output_path):
    """OOD: scenario recall constrained by validation false alarms. Bands: ordinal policy loss.

    Scenario targets are policy expectations, not observed quality labels. Caps, weights
    and excess-start remain explicit safety policy rather than fitted parameters.
    """
    validation = frame.loc[split.reindex(frame.index) == "validation"]
    scenarios, ood_rows = {}, []
    for p in Product:
        mask, _ = population_mask(validation, p)
        rows = validation.loc[mask].head(250)
        if rows.empty:
            raise ValueError("trust threshold selection needs validation rows")
        shifted = rows.copy()
        for c in detectors[p].feature_names:
            shifted[c] = 1e12
        clean_scores, stress_scores = detectors[p].score(rows), detectors[p].score(shifted)
        for t in (0.95, 0.975, 0.99, 0.995, 1.0):
            ood_rows.append({"product": p.value, "threshold": t,
                             "false_alarm": float(np.mean(clean_scores >= t)),
                             "stress_recall": float(np.mean(stress_scores >= t))})
        stale = rows.copy()
        stale["txn_months_observed"] = 0.0
        stale["last_txn_date"] = np.datetime64("2020-01-01")
        scenarios[p] = [(rows, 3), (stale, 1), (shifted, 1)]
    ood_candidates = []
    for t in (0.95, 0.975, 0.99, 0.995, 1.0):
        results = [r for r in ood_rows if r["threshold"] == t]
        fa = float(np.mean([r["false_alarm"] for r in results]))
        recall = float(np.mean([r["stress_recall"] for r in results]))
        ood_candidates.append((fa > 0.05, -recall, fa, t))
    ood = min(ood_candidates)[-1]
    assessments = []
    scorer = TrustScorer(detectors, thresholds=TrustThresholds(ood=ood))
    for p, cases in scenarios.items():
        for rows, target in cases:
            snapshots = [row_to_snapshot(row, config.FEATURE_CUTOFF) for _, row in rows.iterrows()]
            assessments.extend((a, target) for a in scorer.assess_many(snapshots, p))
    candidates = []
    for low, adequate, high in grid((0.35, 0.4, 0.45), (0.55, 0.6, 0.65), (0.75, 0.8, 0.85)):
        errors = []
        for a, target in assessments:
            predicted = (int(a.score >= low) + int(a.score >= adequate) + int(a.score >= high)
                         if a.critical_fields_present else 0)
            errors.append(abs(predicted - target))
        candidates.append({"low": low, "adequate": adequate, "high": high,
                           "ordinal_loss": float(np.mean(errors))})
    best = min(candidates, key=lambda r: (r["ordinal_loss"], -r["adequate"], -r["high"], -r["low"]))
    thresholds = TrustThresholds(low=best["low"], adequate=best["adequate"], high=best["high"], ood=ood)
    artifact = {"version": "trust_threshold_selection_v1", "split": "validation",
                "n_validation": len(validation), "scenario_rows": len(assessments),
                "notice": "Synthetic scenario policy targets, not public data or empirical quality labels.",
                "scenario_targets": {"original": "HIGH", "short_stale_history": "LOW", "extreme_values": "LOW"},
                "objective": "minimum absolute ordinal policy error; OOD recall with <=5% mean false alarms",
                "thresholds": asdict(thresholds), "band_candidates": candidates, "ood_candidates": ood_rows}
    artifact["selected_ordinal_loss"] = best["ordinal_loss"]
    artifact["ood_false_alarm_constraint_met"] = not min(ood_candidates)[0]
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact, indent=2) + "\n")
    return artifact


def load_thresholds(path):
    artifact = json.loads(Path(path).read_text())
    if artifact["version"] != "trust_threshold_selection_v1" or artifact["split"] != "validation":
        raise ValueError("invalid trust threshold selection artifact")
    return TrustThresholds(**artifact["thresholds"])
