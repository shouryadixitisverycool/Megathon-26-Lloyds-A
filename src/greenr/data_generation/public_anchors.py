"""Pinned public aggregates used to shape synthetic energy, with provenance."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

_PATH = Path(__file__).with_name("public_energy_anchor.json")
_BYTES = _PATH.read_bytes()
ENERGY_ANCHOR = json.loads(_BYTES)
ENERGY_ANCHOR_SHA256 = hashlib.sha256(_BYTES).hexdigest()


def anchored_demand(score: np.ndarray, fuel: str, rng: np.random.Generator) -> np.ndarray:
    """Rank-align a lognormal marginal to a noisy synthetic demand score.

    The lognormal median and theoretical mean match the pinned public aggregates.
    Ranking preserves synthetic correlations without changing the sampled marginal.
    Gas scores must contain only gas-consuming customers, because the reference
    excludes non-consuming meters.
    """
    stats = ENERGY_ANCHOR[fuel]
    sigma = np.sqrt(2 * np.log(stats["mean_kwh"] / stats["median_kwh"]))
    sample = rng.lognormal(np.log(stats["median_kwh"]), sigma, len(score))
    result = np.empty(len(score), dtype=float)
    result[np.argsort(score, kind="stable")] = np.sort(sample)
    return result


def anchor_manifest(energy: pd.DataFrame) -> dict:
    """Compare complete first-calendar-year observations to aggregate anchors.

    This is a descriptive drift diagnostic, never a real-world model validation.
    It includes simulation effects and excludes incomplete annual histories.
    """
    year = int(energy["month"].dt.year.min()) if len(energy) else None
    annual = energy.loc[energy["month"].dt.year == year].groupby("customer_id")
    diagnostics = {}
    for fuel in ("electricity", "gas"):
        column = f"{fuel}_kwh"
        totals = annual[column].sum(min_count=12)
        totals = totals[annual[column].count() == 12].dropna()
        if fuel == "gas":
            totals = totals[totals > 0]
        reference = ENERGY_ANCHOR[fuel]
        diagnostics[fuel] = {
            "n_complete_consumers": int(len(totals)),
            "observed_mean_kwh": float(totals.mean()) if len(totals) else None,
            "observed_median_kwh": float(totals.median()) if len(totals) else None,
            "reference_mean_kwh": reference["mean_kwh"],
            "reference_median_kwh": reference["median_kwh"],
        }
    return {"energy": ENERGY_ANCHOR, "energy_anchor_sha256": ENERGY_ANCHOR_SHA256,
            "diagnostic_year": year, "energy_marginal_diagnostics": diagnostics,
            "diagnostic_scope": "Complete calendar-year synthetic observations, including adoption effects and observation noise. Gas includes positive consumers only. Not a real-world predictive validation."}
