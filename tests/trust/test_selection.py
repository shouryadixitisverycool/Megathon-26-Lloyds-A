import json

import numpy as np
import pandas as pd

from greenpath.contracts import Product
from greenpath.trust.ood import OODDetector
from greenpath.trust.selection import load_thresholds, select_thresholds


def test_validation_scenario_selection_persists_and_ignores_test(tmp_path):
    rng = np.random.default_rng(17)
    frame = pd.DataFrame({"fuel_spend_90d_avg": rng.uniform(30, 200, 80),
                          "txn_months_observed": 12., "last_txn_date": pd.Timestamp("2026-06-29"),
                          "home_owner": 1., "annual_mileage_km": rng.uniform(3000, 25000, 80)},
                         index=[f"C{i}" for i in range(80)])
    split = pd.Series(["train"] * 40 + ["validation"] * 20 + ["test"] * 20, index=frame.index)
    detectors = {p: OODDetector().fit(frame.iloc[:40][["fuel_spend_90d_avg", "annual_mileage_km"]]) for p in Product}
    path = tmp_path / "thresholds.json"
    a = select_thresholds(frame, split, {}, detectors, path)
    assert a == json.loads(path.read_text())
    assert load_thresholds(path).ood == a["thresholds"]["ood"]
    assert a["n_validation"] == 20 and len(a["band_candidates"]) == 27
    frame.loc[split == "test", "annual_mileage_km"] = 1e15
    b = select_thresholds(frame, split, {}, detectors, path)
    assert a == b


def test_confidence_release_never_reads_test(monkeypatch, tmp_path):
    from greenpath.pipelines import run
    seen = []

    def rows(*args):
        seen.append(args[-1])
        return pd.DataFrame(), np.array([], dtype=bool), np.array([]), np.array([])

    monkeypatch.setattr(run, "_confidence_rows", rows)
    monkeypatch.setattr(run.config, "ARTIFACT_DIR", tmp_path)
    mapping = {p: None for p in Product}
    result = run.train_confidence(None, None, None, mapping, mapping)
    assert set(seen) == {"validation", "confidence_release"}
    assert all(not decision["test_used_for_release_selection"] for decision in result.values())
