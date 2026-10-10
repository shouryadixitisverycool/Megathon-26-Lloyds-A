"""CLI safety and reproducibility regression checks."""

import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from xml.etree import ElementTree

import numpy as np
import pandas as pd
import pytest

from greenpath import config
from greenpath.contracts import ConfidenceStatus, Product
from greenpath.evaluation.reports import leakage_audit, write_plots
from greenpath.pipelines import run
from greenpath.pipelines.runtime import ConfidenceScorer
from greenpath.pipelines import runtime


def test_strict_json_replaces_undefined_metrics(tmp_path):
    target = tmp_path / "metrics.json"
    run.write_json(target, {"auc": np.nan, "ratio": np.inf,
                            "count": np.int64(3), "day": date(2026, 6, 30)})
    payload = json.loads(target.read_text(), parse_constant=lambda value: pytest.fail(value))
    assert payload == {"auc": None, "ratio": None, "count": 3, "day": "2026-06-30"}


def test_all_cli_generates_both_datasets_before_training(monkeypatch):
    from greenpath.data_generation import __main__ as generation
    from greenpath.evaluation import ml
    from greenpath.pipelines import predict
    events = []
    monkeypatch.setattr(generation, "generate_dataset", lambda **kw: events.append(("data", kw)))
    for name in ("stage_env", "stage_train", "write_run_manifest", "update_timings"):
        monkeypatch.setattr(run, name, lambda *a, _name=name, **kw: events.append((_name, kw)))
    monkeypatch.setattr(ml, "stage_evaluate", lambda: events.append(("evaluate", {})))
    monkeypatch.setattr(predict, "stage_predict", lambda: events.append(("predict", {})))
    run.main(["all", "--customers", "400"])
    assert events[1:4] == [("data", {"customers": 400}),
                           ("data", {"customers": 400, "perturbed": True}),
                           ("stage_train", {})]
    assert [name for name, _ in events[4:6]] == ["evaluate", "predict"]


def test_cli_rejects_zero_customers():
    with pytest.raises(SystemExit) as exc:
        run.main(["all", "--customers", "0"])
    assert exc.value.code == 2


def test_one_class_confidence_is_suppressed_and_stale_model_removed(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "ARTIFACT_DIR", tmp_path)
    monkeypatch.setattr(run, "PRODUCTS", [Product.EV_FINANCE])
    monkeypatch.setattr(run, "_confidence_rows", lambda *args: (
        pd.DataFrame(index=range(300)), np.ones(300, dtype=bool), np.ones(300), np.ones(300)))
    path = tmp_path / "confidence" / "ev_finance.joblib"
    path.parent.mkdir()
    path.write_bytes(b"stale artifact")
    decision = run.train_confidence(None, None, None, {Product.EV_FINANCE: SimpleNamespace()},
                                    {Product.EV_FINANCE: None})[Product.EV_FINANCE.value]
    assert decision["surfaced"] is False
    assert "both correct and incorrect" in decision["limitation"]
    assert not path.exists()


def test_suppressed_runtime_does_not_evaluate_a_meta_model():
    class ExplodingModel:
        def predict(self, frame):
            pytest.fail("suppressed confidence model was used")
    scorer = ConfidenceScorer({}, {Product.EV_FINANCE: ExplodingModel()},
                              {Product.EV_FINANCE: False}, {Product.EV_FINANCE: "Insufficient evidence"})
    results = scorer(Product.EV_FINANCE, pd.DataFrame(index=range(2)), np.array([0.1, 0.9]))
    assert all(r.status is ConfidenceStatus.SUPPRESSED and r.value is None for r in results)


def test_historical_leakage_audit_is_a_separate_section(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "REPORTS_DIR", tmp_path)
    summary = {"status": "PASS", "features_compared": 5, "customers_compared": 10, "differences": []}
    run.write_json(tmp_path / "leakage_checks.json", {
        "point_in_time_rebuild": summary, "historical_point_in_time": {"2026-01-31": summary},
        "EV_FINANCE": {"checks": [{"check": "split", "target": "all", "status": "PASS", "detail": "disjoint"}]}})
    report = leakage_audit({})
    assert "Historical cutoff rebuilds" in report and "2026-01-31" in report
    assert "### EV_FINANCE" in report


def test_evaluation_charts_are_standalone_valid_svg(tmp_path):
    write_plots({"products": {"EV_FINANCE": {
        "calibration_curve": {"after": [{"n": 3, "mean_predicted": 0.2, "observed_rate": 0.3}]},
        "ranking_curves": {"roc": {"x": [0, 1], "y": [0, 1]}}}}}, tmp_path)
    paths = list(tmp_path.glob("*.svg"))
    assert len(paths) == 2
    for path in paths:
        assert ElementTree.parse(path).getroot().tag.endswith("svg")
        assert "EV_FINANCE" in path.read_text()


def test_runtime_refuses_partial_trained_artifacts(monkeypatch, tmp_path):
    from greenpath.pipelines.snapshot_provider import Customer360SnapshotProvider
    monkeypatch.setattr(Customer360SnapshotProvider, "from_parquet", lambda *args: object())
    monkeypatch.setattr(runtime, "load_all", lambda **kwargs: {p: object() for p in Product})
    monkeypatch.setattr(runtime, "load_detectors", lambda *args: {})
    decisions_path = tmp_path / "confidence" / "decisions.json"
    run.write_json(decisions_path, {p.value: {"surfaced": False} for p in Product})
    with pytest.raises(FileNotFoundError, match="OOD detector for EV_FINANCE"):
        runtime.load_runtime(root=tmp_path)


def test_runtime_refuses_validated_confidence_without_model(monkeypatch, tmp_path):
    from greenpath.pipelines.snapshot_provider import Customer360SnapshotProvider
    monkeypatch.setattr(Customer360SnapshotProvider, "from_parquet", lambda *args: object())
    monkeypatch.setattr(runtime, "load_all", lambda **kwargs: {p: object() for p in Product})
    monkeypatch.setattr(runtime, "load_detectors", lambda *args: {p: object() for p in Product})
    run.write_json(tmp_path / "confidence" / "decisions.json", {p.value: {"surfaced": True} for p in Product})
    with pytest.raises(FileNotFoundError, match="validated confidence model"):
        runtime.load_runtime(root=tmp_path)


def test_feature_drift_separates_distribution_and_missingness():
    from greenpath.evaluation.ml import feature_drift
    name = "annual_mileage_km"
    report = feature_drift(pd.DataFrame({name: [1, 1, 1, 1]}),
                           pd.DataFrame({name: [10, 10, None, None]}))
    row = next(row for row in report["features"] if row["feature"] == name)
    assert row["ks_statistic"] == 1
    assert row["missingness_delta"] == 0.5
    assert row["reference_median"] == 1 and row["comparison_median"] == 10
