import json
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from greenr.confidence.validation import baseline_diagnostics, validate_confidence, write_confidence_report
from greenr.contracts import Product
from greenr.pipelines import run


def test_small_cohort_keeps_scoring_and_support_without_passing():
    v = validate_confidence([0.9, 0.6, 0.2], [True, False, False])
    assert not v.passed and "insufficient data" in v.reasons[0]
    assert (v.n, v.n_correct, v.n_incorrect) == (3, 1, 2)
    assert v.overall_error == pytest.approx(2 / 3)
    assert v.brier == pytest.approx((0.01 + 0.36 + 0.04) / 3)
    assert v.ece == pytest.approx((0.1 + 0.6 + 0.2) / 3)
    assert v.calibration_gap == pytest.approx(1.7 / 3 - 1 / 3)
    assert v.correctness_auc == 1
    assert v.deciles
    json.dumps(v.to_dict(), allow_nan=False)


def test_baselines_use_frozen_fit_accuracy_and_operational_decision():
    # At threshold .3, p=.4 is a positive decision: q=.4, NOT max(p,1-p)=.6.
    result = baseline_diagnostics([True, False], [0.4, 0.2], 0.3, 0.75)
    constant = result["constant_correctness"]
    assert constant["probability"] == 0.75
    assert constant["estimated_on"] == "validation"
    assert constant["validation"]["brier"] == pytest.approx((0.25**2 + 0.75**2) / 2)
    deployed = result["deployed_propensity_correctness"]["validation"]
    assert deployed["brier"] == pytest.approx((0.6**2 + 0.8**2) / 2)
    assert deployed["correctness_auc"] == 0
    # Changing reserved labels affects metrics, never the frozen estimate.
    changed = baseline_diagnostics([False, False], [0.4, 0.2], 0.3, 0.75)
    assert changed["constant_correctness"]["probability"] == 0.75


def test_fitting_failure_reports_distinct_release_support_and_baselines(monkeypatch, tmp_path):
    product = Product.EV_FINANCE
    monkeypatch.setattr(run, "PRODUCTS", [product])
    monkeypatch.setattr(run.config, "ARTIFACT_DIR", tmp_path)
    seen = []

    def rows(*args):
        which = args[-1]
        seen.append(which)
        correct = np.array([True, True, False]) if which == "validation" else np.array([False, True])
        return pd.DataFrame(index=range(len(correct))), correct, np.full(len(correct), 0.4), np.zeros(len(correct))

    monkeypatch.setattr(run, "_confidence_rows", rows)
    d = run.train_confidence(None, None, None, {product: SimpleNamespace(threshold=0.3)}, {product: None})[product.value]
    assert seen == ["validation", "confidence_release"]
    assert not d["surfaced"]
    assert d["fitting_status"] == "FAILED_INSUFFICIENT_SUPPORT"
    assert d["release_status"] == "NOT_RUN_FITTING_FAILED"
    assert d["cohorts"]["fitting_validation"]["n_correct"] == 2
    assert d["cohorts"]["release_selection"]["n_incorrect"] == 1
    assert d["validation"]["n_correct"] == 1
    assert d["baselines"]["constant_correctness"]["probability"] == pytest.approx(2 / 3)
    assert d["baselines"]["deployed_propensity_correctness"]["validation"]["brier"] is not None
    # The report must retain provenance rather than silently discard it.
    d["held_out_test_diagnostic"] = validate_confidence([0.5], [False]).to_dict()
    write_confidence_report({product.value: d}, tmp_path / "report.md", tmp_path / "report.json")
    report = json.loads((tmp_path / "report.json").read_text())[product.value]
    for key in ("n_validation", "n_release_selection", "release_selection_split",
                "test_used_for_release_selection", "held_out_test_diagnostic", "cohorts", "baselines"):
        assert report[key] == d[key]
    assert report["decision"] == "SUPPRESSED"
    assert "NOT_RUN_FITTING_FAILED" in (tmp_path / "report.md").read_text()


def test_release_failure_is_distinct_from_successful_fit(monkeypatch, tmp_path):
    product = Product.EV_FINANCE
    monkeypatch.setattr(run, "PRODUCTS", [product])
    monkeypatch.setattr(run.config, "ARTIFACT_DIR", tmp_path)

    class Model:
        def fit(self, features, correct):
            assert len(correct) == 200
            return self

        def save(self, path):
            pass

        def predict(self, features):
            return np.full(len(features), 0.8)

        def coefficients(self):
            return {}

        bucket_thresholds = {}

    def rows(*args):
        n = 200 if args[-1] == "validation" else 10
        return pd.DataFrame(index=range(n)), np.arange(n) % 2 == 0, np.full(n, 0.4), np.zeros(n)

    monkeypatch.setattr(run, "_confidence_rows", rows)
    monkeypatch.setattr(run, "ConfidenceModel", Model)
    monkeypatch.setattr(run, "ablation", lambda *args: pd.DataFrame())
    d = run.train_confidence(None, None, None, {product: SimpleNamespace(threshold=0.3)}, {product: None})[product.value]
    assert not d["surfaced"]
    assert d["fitting_status"] == "FITTED" and d["release_status"] == "FAILED"
    assert d["validation"]["brier"] == pytest.approx(0.34)
    assert d["validation"]["n_incorrect"] == 5
