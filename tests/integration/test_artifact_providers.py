"""ML evidence adaptation, batching, historical cutoffs and provider selection."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from greenpath import config
from greenpath.contracts import ConfidenceResult, CustomerSnapshot as ScoringSnapshot
from greenpath.contracts import PropensityResult as ScoringResult, TrustAssessment as ScoringTrust
from greenpath.contracts.enums import ConfidenceBucket, ConfidenceStatus, Product, RecommendationState
from greenpath.contracts.fixtures import load_model
from greenpath.demo.artifacts import ArtifactRepository, default_repository
from greenpath.recommendation.service import RecommendationService


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
    assert all(r.impact.issues[0].code == "UNSUPPORTED_SCOPE" for r in decisions)
    assert all(not r.impact.factors for r in decisions)
    history = repository.list_history()
    solar = {r.month: r.state for r in history if r.product == Product.SOLAR_FINANCE}
    assert solar == {"2026-05": RecommendationState.INSUFFICIENT_INFORMATION, "2026-06": RecommendationState.RECOMMEND}
    assert len(runtime.calls) == 16
    assert repository.list_history() is history
    assert len(runtime.calls) == 16


def test_validated_low_confidence_abstains_without_conflating_trust():
    runtime = FakeRuntime()
    runtime.low_confidence = True
    repository = ArtifactRepository(runtime)
    decisions = RecommendationService(repository, repository, repository).recommendations("C10001")
    assert all(r.state == RecommendationState.INSUFFICIENT_INFORMATION for r in decisions)
    assert all(r.reason_codes == ("CONFIDENCE_BELOW_MINIMUM",) for r in decisions)
    assert all(r.trust.status == "TRUSTED" for r in decisions)


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
    from greenpath.api.portfolio import historical_trends
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
    from greenpath.api.main import create_app
    repository = ArtifactRepository(FakeRuntime())
    with TestClient(create_app(repository)) as client:
        first = client.get("/portfolio/summary")
        assert first.status_code == 200 and first.json()["total_customers"] == 1
        def fail(customer_id):
            raise AssertionError("Cached unfiltered summary should not rescore a customer")
        repository.get_snapshot = fail
        assert client.get("/portfolio/summary").json() == first.json()


def test_trend_high_confidence_uses_recommended_rows_and_paperless_fact_is_not_future_label():
    from greenpath.api.portfolio import historical_trends
    from greenpath.contracts.product import HistoryRecord
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
    from greenpath.api.portfolio import summarize
    repository = ArtifactRepository(FakeRuntime())
    snapshots = repository.list_snapshots()
    service = RecommendationService(repository, repository, repository)
    result = summarize(snapshots, {s.customer_id: service.recommendations(s.customer_id) for s in snapshots})
    assert result.customers_with_opportunity == 1
    assert result.high_trust_opportunities == 4
    assert result.high_confidence_opportunities == 0 and result.validated_confidence_opportunities == 0
    assert result.funnel_counts == {"analyzed_customers": 1, "in_population_scored_opportunities": 4,
        "supported_opportunities": 4, "supported_with_validated_confidence": 0, "supported_with_high_confidence": 0}
