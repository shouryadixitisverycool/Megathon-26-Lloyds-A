"""ML evidence adaptation, batching, historical cutoffs and provider selection."""

from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from greenr import config
from greenr.contracts import ConfidenceResult, CustomerSnapshot as ScoringSnapshot
from greenr.contracts import PropensityResult as ScoringResult, TrustAssessment as ScoringTrust
from greenr.contracts.enums import ConfidenceBucket, ConfidenceStatus, Product, RecommendationState
from greenr.contracts.fixtures import load_model
from greenr.demo.artifacts import ArtifactRepository, default_repository
from greenr.recommendation.service import RecommendationService


class FakeRuntime:
    def __init__(self):
        self.calls = []
        self.low_confidence = False
        self.source = load_model("customer_snapshot_C10001", ScoringSnapshot)
        self.result = load_model("propensity_result_C10001_EV", ScoringResult)
        self.assessment = load_model("trust_assessment_C10001_EV", ScoringTrust)
        self.bundles = {p: SimpleNamespace(model_version=f"trained-{p.value}", threshold=0.6) for p in Product}
        self.snapshots = SimpleNamespace(default_cutoff=date(2026, 6, 30),
            cutoffs=[date(2026, 5, 31), date(2026, 6, 30)], snapshots=self.sources)
        self.propensity = SimpleNamespace(score_many=self.score_many)
        self.trust = SimpleNamespace(assess_many=self.assess_many)

    def sources(self, cutoff):
        # May has no reliable ownership, June does. Historical decisions must differ.
        source = self.source.model_copy(update={"feature_cutoff": cutoff})
        if cutoff.month == 5:
            source = source.model_copy(update={"home": source.home.model_copy(update={"home_owner": None})})
        return [source]

    def score_many(self, sources, product):
        self.calls.append(("score", sources[0].feature_cutoff, product))
        confidence = (ConfidenceResult(status=ConfidenceStatus.VALIDATED, value=.3,
            bucket=ConfidenceBucket.LOW, method_version="validated-v1") if self.low_confidence else
            ConfidenceResult(status=ConfidenceStatus.SUPPRESSED, method_version="test-v1", limitation="Not validated"))
        return [self.result.model_copy(update={"product": product, "propensity": .8,
            "feature_cutoff": source.feature_cutoff, "confidence": confidence}) for source in sources]

    def assess_many(self, sources, product):
        self.calls.append(("trust", sources[0].feature_cutoff, product))
        return [self.assessment.model_copy(update={"product": product}) for source in sources]


def test_trained_adapter_keeps_source_and_does_not_invent_permissions():
    runtime = FakeRuntime()
    repository = ArtifactRepository(runtime)
    snapshot = repository.get_snapshot("C10001")
    assert snapshot.source_snapshot == runtime.source
    assert snapshot.decision_profile == "trained"
    assert "marketing_consent" not in snapshot.features
    assert "roof_available" not in snapshot.features
    assert "ev_interest" not in snapshot.features
    assert set(snapshot.product_trust) == set(Product)
    result = repository.get_propensity("C10001", Product.EV_FINANCE)
    assert result.probability == Decimal("0.8")
    assert result.calibration_version == runtime.result.calibration_version
    assert result.source_result.confidence.status == ConfidenceStatus.SUPPRESSED
    assert result.confidence is None and not result.confidence_validated
    snapshot.features.clear()
    assert repository.get_snapshot("C10001").features
    assert len(runtime.calls) == 8


def test_real_monthly_cutoffs_and_cached_batches():
    runtime = FakeRuntime()
    repository = ArtifactRepository(runtime)
    decisions = RecommendationService(repository, repository, repository).recommendations("C10001")
    assert all(r.state == RecommendationState.RECOMMEND for r in decisions)
    assert all(r.impact.value is None for r in decisions)
    assert all(any(i.code == "MISSING_INPUT" for i in r.impact.issues) for r in decisions)
    assert all(r.impact.feature_cutoff == r.feature_cutoff for r in decisions)
    assert all(not r.impact.factors for r in decisions)
    history = repository.list_history()
    solar = {r.month: r.state for r in history if r.product == Product.SOLAR_FINANCE}
    assert solar == {"2026-05": RecommendationState.INSUFFICIENT_INFORMATION, "2026-06": RecommendationState.RECOMMEND}
    assert len(runtime.calls) == 16
    assert repository.list_history() is history
    assert len(runtime.calls) == 16


def test_current_preparation_does_not_prepare_history():
    runtime = FakeRuntime()
    repository = ArtifactRepository(runtime)
    repository.prepare_current()
    assert len(runtime.calls) == 8
    assert {call[1] for call in runtime.calls} == {runtime.snapshots.default_cutoff}
    assert repository.history_status["phase"] == "pending"
    assert repository._history is None
    repository.prepare_current()
    assert len(runtime.calls) == 8


def cached_repository(tmp_path, monkeypatch, runtime=None):
    for setting, directory in (("ARTIFACT_DIR", "artifacts"), ("RAW_DIR", "raw"),
                               ("REPORTS_DIR", "reports")):
        path = tmp_path / directory
        path.mkdir(exist_ok=True)
        monkeypatch.setattr(config, setting, path)
    repository = ArtifactRepository(runtime or FakeRuntime())
    from greenr.pipelines.snapshot_provider import Customer360SnapshotProvider
    monkeypatch.setattr(Customer360SnapshotProvider, "from_parquet",
                        lambda *paths, **kwargs: repository.runtime.snapshots)
    repository._history_cache_dir = config.ARTIFACT_DIR / "history_cache"
    repository._historical_paths = {}
    for cutoff in repository.history_cutoffs:
        path = tmp_path / f"customer360_{cutoff}.parquet"
        if not path.exists():
            path.write_bytes(str(cutoff).encode())
        repository._historical_paths[cutoff] = path
    return repository


def test_history_cache_roundtrip_keeps_real_monthly_decisions_and_impact(tmp_path, monkeypatch):
    first = cached_repository(tmp_path, monkeypatch)
    expected = first.list_history()
    fresh = cached_repository(tmp_path, monkeypatch)
    def forbidden(*args):
        pytest.fail("Persisted history must not rescore or load historical frames")
    fresh._at = forbidden
    assert fresh.list_history() == expected
    assert fresh.history_status == {"phase": "ready", "cutoff": None, "completed_cutoffs": 2}
    solar = {r.month: r.state for r in expected if r.product == Product.SOLAR_FINANCE}
    assert solar["2026-05"] != solar["2026-06"]
    assert all(r.impact.feature_cutoff.month == int(r.month[-2:]) for r in expected)
    assert all(r.propensity == Decimal("0.8") and r.trust_score == Decimal("0.91") for r in expected)


@pytest.mark.parametrize("changed", ["frame", "model", "confidence", "ood", "scenario", "rules", "threshold", "trust", "outcome"])
def test_history_cache_provenance_invalidates(tmp_path, monkeypatch, changed):
    repository = cached_repository(tmp_path, monkeypatch)
    cutoff = repository.history_cutoffs[0]
    before = repository._history_key(cutoff)
    if changed == "threshold":
        repository.runtime.bundles[Product.EV_FINANCE].threshold = .9
    elif changed == "rules":
        from pathlib import Path
        path = tmp_path / "rules.py"
        path.write_text("changed rules")
        original = Path.rglob
        monkeypatch.setattr(Path, "rglob", lambda root, pattern:
                            iter([*original(root, pattern), path]) if pattern == "*.py"
                            else original(root, pattern))
    else:
        path = {
            "frame": repository._historical_paths[cutoff],
            "model": config.ARTIFACT_DIR / "models" / "ev.joblib",
            "confidence": config.ARTIFACT_DIR / "confidence" / "decisions.json",
            "ood": config.ARTIFACT_DIR / "ood" / "ev.joblib",
            "scenario": config.RAW_DIR / "scenario_evidence.parquet",
            "trust": config.ARTIFACT_DIR / "trust_thresholds.json",
            "outcome": config.ARTIFACT_DIR / "portfolio_scores.parquet",
        }[changed]
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(b"changed content")
    assert repository._history_key(cutoff) != before


def test_truncated_history_cache_is_recomputed(tmp_path, monkeypatch):
    repository = cached_repository(tmp_path, monkeypatch)
    expected = repository.list_history()
    path = next(repository._history_cache_dir.glob("*.jsonl"))
    lines = path.read_bytes().splitlines(keepends=True)
    path.write_bytes(b"".join(lines[:-1]))
    fresh = cached_repository(tmp_path, monkeypatch)
    actual = fresh.list_history()
    # A recomputation has a new calculation time; persisted cache hits retain the old one.
    assert [r.model_dump(exclude={"impact": {"timestamp"}}) for r in actual] == [
        r.model_dump(exclude={"impact": {"timestamp"}}) for r in expected]
    assert len(fresh.runtime.calls) == 8
    assert not list(fresh._history_cache_dir.glob("tmp*"))


def test_history_cache_threshold_change_recomputes_rules(tmp_path, monkeypatch):
    original = cached_repository(tmp_path, monkeypatch)
    original.list_history()
    fresh = cached_repository(tmp_path, monkeypatch)
    for bundle in fresh.runtime.bundles.values():
        bundle.threshold = .9
    history = fresh.list_history()
    assert len(fresh.runtime.calls) == 16
    assert all(row.state != RecommendationState.RECOMMEND for row in history)
    assert all(row.propensity == Decimal("0.8") for row in history)


def test_history_cache_failed_atomic_publish_does_not_break_history(tmp_path, monkeypatch):
    import os
    repository = cached_repository(tmp_path, monkeypatch)
    def fail(*args):
        raise OSError("cache publish unavailable")
    monkeypatch.setattr(os, "replace", fail)
    assert len(repository.list_history()) == 8
    assert repository.history_status["phase"] == "ready"
    assert not list(repository._history_cache_dir.iterdir())


def test_default_runtime_loads_only_current_frame_then_loads_history_lazily(tmp_path, monkeypatch):
    from greenr.pipelines import runtime as runtime_module
    from greenr.pipelines import snapshot_provider
    current = date(2026, 6, 30)
    earlier = date(2026, 5, 31)
    monkeypatch.setattr(config, "FEATURE_CUTOFF", current)
    monkeypatch.setattr(config, "TREND_CUTOFFS", [earlier, current])
    for setting in ("ARTIFACT_DIR", "RAW_DIR", "REPORTS_DIR"):
        monkeypatch.setattr(config, setting, tmp_path / setting)
    paths = {c: tmp_path / f"customer360_{c}.parquet" for c in (earlier, current)}
    for path in paths.values():
        path.write_bytes(b"test frame provenance")
    monkeypatch.setattr(snapshot_provider, "customer360_path", lambda cutoff: paths[cutoff])
    runtime = FakeRuntime()
    runtime.snapshots.cutoffs = [current]
    loads = []
    def load_runtime(*, cutoffs):
        loads.append(tuple(cutoffs))
        return runtime
    monkeypatch.setattr(runtime_module, "load_runtime", load_runtime)
    historical_loads = []
    def from_parquet(path, *, default_cutoff):
        historical_loads.append((path, default_cutoff))
        return FakeRuntime().snapshots
    monkeypatch.setattr(snapshot_provider.Customer360SnapshotProvider, "from_parquet", from_parquet)
    repository = ArtifactRepository()
    repository.prepare_current()
    assert loads == [(current,)]
    assert historical_loads == []
    assert repository.history_cutoffs == (earlier, current)
    repository.list_history()
    assert historical_loads == [(paths[earlier], earlier)]
    assert set(repository._cache) == {current}


def test_impact_inputs_and_history_use_each_cutoffs_physical_evidence():
    runtime = FakeRuntime()
    original_sources = runtime.snapshots.snapshots

    def sources(cutoff):
        source = original_sources(cutoff)[0]
        return [source.model_copy(update={
            "vehicle": source.vehicle.model_copy(update={"annual_mileage_km": float(cutoff.month * 1000)}),
            "features": {**source.features, "ice_litres_per_100km": 6.5,
                         "ev_kwh_per_100km": 18.0, "charging_efficiency": 0.9},
        })]

    runtime.snapshots.snapshots = sources
    repository = ArtifactRepository(runtime)
    payload = repository.get_impact_input("C10001", Product.EV_FINANCE)
    assert payload.vehicle.annual_mileage_km == 6000
    payload.features.clear()
    assert repository.get_impact_input("C10001", Product.EV_FINANCE).features
    assert repository.get_impact_input("unknown", Product.EV_FINANCE) is None
    calculator = repository.impact_calculators[Product.EV_FINANCE]
    original_calculate = calculator.calculate
    observed = []

    def calculate(payload):
        result = original_calculate(payload)
        observed.append((result.feature_cutoff.date(),
            next(e.value for e in result.evidence if e.field == "annual_mileage_km")))
        return result

    calculator.calculate = calculate
    repository.list_history()
    assert observed == [(date(2026, 5, 31), Decimal("5000")),
                        (date(2026, 6, 30), Decimal("6000"))]


def test_validated_low_confidence_abstains_without_conflating_trust():
    runtime = FakeRuntime()
    runtime.low_confidence = True
    repository = ArtifactRepository(runtime)
    decisions = RecommendationService(repository, repository, repository).recommendations("C10001")
    assert all(r.state == RecommendationState.INSUFFICIENT_INFORMATION for r in decisions)
    assert all(r.reason_codes == ("CONFIDENCE_BELOW_MINIMUM",) for r in decisions)
    assert all(r.trust.status == "TRUSTED" for r in decisions)


def test_explicit_trained_scenario_exposes_available_co2e_through_api():
    from fastapi.testclient import TestClient
    from greenr.api.main import create_app
    from greenr.contracts.impact_detail import ImpactResult

    runtime = FakeRuntime()
    from greenr.data_generation.scenarios import generate_scenario_table
    from greenr.pipelines.scenario_provider import ScenarioProvider
    table = generate_scenario_table([runtime.source.customer_id],
        effective_on=runtime.source.feature_cutoff, available_on=runtime.source.feature_cutoff)
    scenarios = ScenarioProvider(table[table["product"] == Product.EV_FINANCE])
    repository = ArtifactRepository(runtime, scenario_provider=scenarios)
    expected = repository.impact_calculators[Product.EV_FINANCE].calculate(scenarios.attach(runtime.source, Product.EV_FINANCE))
    with TestClient(create_app(repository)) as client:
        rows = client.get("/customers/C10001/recommendations").json()["recommendations"]
        ev = next(row for row in rows if row["product"] == "EV_FINANCE")
        assert ev["state"] == "RECOMMEND"
        actual = ImpactResult.model_validate(ev["impact"])
        assert actual.status == "AVAILABLE" and actual.units == "kg CO2e/year"
        assert actual.value == expected.value
        assert actual.baseline == expected.baseline and actual.scenario == expected.scenario
        assert actual.factors == expected.factors and actual.evidence == expected.evidence
        assert actual.feature_cutoff == datetime.fromisoformat(ev["feature_cutoff"])
        assert all(row["impact"]["value"] is None for row in rows if row != ev)
        explanation = client.get("/customers/C10001/explanations/EV_FINANCE").json()
        assert explanation["validation_passed"] is True
        assert explanation["impact_value"] == ev["impact"]["value"]
        assert explanation["units"] == "kg CO2e/year"
        assert "kg CO2e/year" in explanation["text"]
        assert client.get("/portfolio/summary").json()["available_impact_count"] == 1


def test_injected_scenarios_use_historical_cutoff_without_reading_raw(monkeypatch):
    import pandas as pd
    from greenr.data_generation.scenarios import generate_scenario_table
    from greenr.pipelines.scenario_provider import ScenarioProvider
    runtime = FakeRuntime()
    scenarios = ScenarioProvider(generate_scenario_table(["C10001"],
        effective_on=date(2026, 6, 30), available_on=date(2026, 6, 30)))
    monkeypatch.setattr(pd, "read_parquet", lambda *a, **kw: pytest.fail("Injected runtime must not load raw tables"))
    repository = ArtifactRepository(runtime, scenario_provider=scenarios)
    assert repository.get_impact_input("C10001", Product.EV_FINANCE).scenario
    history = {row.month: row for row in repository.list_history() if row.product == Product.EV_FINANCE}
    assert history["2026-05"].impact_status == "UNAVAILABLE"
    assert history["2026-06"].impact_status == "AVAILABLE"


def test_auto_fixture_and_partial_artifacts_fail_visibly(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ARTIFACT_DIR", tmp_path / "artifacts")
    monkeypatch.setattr(config, "PROCESSED_DIR", tmp_path / "processed")
    assert default_repository("auto").mode == "fixture"
    (tmp_path / "artifacts" / "models").mkdir(parents=True)
    with pytest.raises(RuntimeError, match="missing, incomplete or corrupt"):
        default_repository("auto")
    assert default_repository("fixture").mode == "fixture"
    with pytest.raises(ValueError, match="must be auto"):
        default_repository("unknown")


def test_trend_metrics_use_actual_scored_values_and_absent_outcomes_stay_absent():
    from greenr.api.portfolio import historical_trends
    repository = ArtifactRepository(FakeRuntime())
    trends = historical_trends(repository.list_snapshots(), repository.list_history())
    assert all(point.average_propensity == Decimal("0.8") for point in trends.observations)
    assert all(point.average_trust == Decimal("0.91") for point in trends.observations)
    assert all(point.average_validated_confidence is None and point.validated_confidence_count == 0
               for point in trends.observations)
    assert all(point.observed_outcome_count == 0 and point.observed_adoptions_90d is None
               for point in trends.observations)
    assert len(repository._cache) == 1


def test_trained_api_warms_and_reuses_portfolio_summary():
    from fastapi.testclient import TestClient
    from greenr.api.main import create_app
    repository = ArtifactRepository(FakeRuntime())
    with TestClient(create_app(repository)) as client:
        first = client.get("/portfolio/summary")
        assert first.status_code == 200 and first.json()["total_customers"] == 1
        def fail(customer_id):
            raise AssertionError("Cached unfiltered summary should not rescore a customer")
        repository.get_snapshot = fail
        assert client.get("/portfolio/summary").json() == first.json()


def test_trend_high_confidence_uses_recommended_rows_and_paperless_fact_is_not_future_label():
    from greenr.api.portfolio import historical_trends
    from greenr.contracts.product import HistoryRecord
    repository = ArtifactRepository(FakeRuntime())
    snapshot = repository.get_snapshot("C10001")
    snapshots = tuple(snapshot.model_copy(update={"customer_id": name, "source_snapshot": None}) for name in ("a", "b", "c"))
    history = (
        HistoryRecord(customer_id="a", month="2026-06", product=Product.PAPERLESS_BANKING,
            state=RecommendationState.RECOMMEND, confidence_high=True, is_paperless=False, observed_adoption_90d=1),
        HistoryRecord(customer_id="b", month="2026-06", product=Product.PAPERLESS_BANKING,
            state=RecommendationState.RECOMMEND, confidence_high=None, is_paperless=False, observed_adoption_90d=1),
        HistoryRecord(customer_id="c", month="2026-06", product=Product.PAPERLESS_BANKING,
            state=RecommendationState.NOT_APPLICABLE, confidence_high=True, is_paperless=True, observed_adoption_90d=0),
    )
    point = historical_trends(snapshots, history).observations[0]
    assert point.high_confidence_opportunity_count == 1
    assert point.validated_confidence_opportunity_count == 1
    assert point.high_confidence_opportunity_share == Decimal("0.5")
    assert point.paperless_observed_count == 3 and point.paperless_active_count == 1
    assert point.paperless_adoption_rate == Decimal(1) / 3
    assert point.observed_adoptions_90d == 2


def test_summary_kpis_keep_supported_confidence_and_trust_counts_separate():
    from greenr.api.portfolio import summarize
    repository = ArtifactRepository(FakeRuntime())
    snapshots = repository.list_snapshots()
    service = RecommendationService(repository, repository, repository)
    result = summarize(snapshots, {s.customer_id: service.recommendations(s.customer_id) for s in snapshots})
    assert result.customers_with_opportunity == 1
    assert result.high_trust_opportunities == 4
    assert result.high_confidence_opportunities == 0 and result.validated_confidence_opportunities == 0
    assert result.funnel_counts == {"analyzed_customers": 1, "in_population_scored_opportunities": 4,
        "supported_opportunities": 4, "supported_with_validated_confidence": 0, "supported_with_high_confidence": 0}
