"""Committed fixtures: validity, round-trips, generator agreement, content and fake providers."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from greenpath.config import FEATURE_CUTOFF, OUTCOME_WINDOW_END, PREDICTION_TIMESTAMP, TREND_CUTOFFS
from greenpath.contracts import (
    ELIGIBILITY_MESSAGE,
    PRODUCT_IDS,
    CustomerSnapshot,
    Explanation,
    ImpactResult,
    PortfolioSummary,
    PortfolioTrends,
    Product,
    PropensityResult,
    Recommendation,
    RecommendationState,
    TrustAssessment,
)
from greenpath.contracts.base import Contract
from greenpath.contracts.fixtures import (
    APPROVED_FEATURES,
    FIXTURE_DIR,
    FixturePropensityProvider,
    FixtureSnapshotProvider,
    FixtureTrustProvider,
    build_fixtures,
    load_fixture,
    load_model,
    render_fixture,
    write_fixtures,
)
from greenpath.ports import CustomerSnapshotProvider, PropensityProvider, TrustProvider

FIXTURE_MODELS: dict[str, type[Contract]] = {
    "customer_snapshot_C10001": CustomerSnapshot,
    "customer_snapshot_C10005": CustomerSnapshot,
    "propensity_result_C10001_EV": PropensityResult,
    "propensity_result_C10005_SOLAR": PropensityResult,
    "trust_assessment_C10001_EV": TrustAssessment,
    "trust_assessment_C10004_EV": TrustAssessment,
    "trust_assessment_C10005_SOLAR": TrustAssessment,
    "impact_result_ev_available": ImpactResult,
    "impact_result_solar_unavailable": ImpactResult,
    "impact_result_paperless_not_claimed": ImpactResult,
    "recommendation_RECOMMEND": Recommendation,
    "recommendation_CONFLICT_REQUIRES_REVIEW": Recommendation,
    "recommendation_INSUFFICIENT_INFORMATION": Recommendation,
    "recommendation_SUPPRESSED": Recommendation,
    "recommendation_NOT_APPLICABLE": Recommendation,
    "recommendation_DO_NOT_RECOMMEND": Recommendation,
    "explanation_template": Explanation,
    "portfolio_summary": PortfolioSummary,
    "portfolio_trends": PortfolioTrends,
}

RECOMMENDATION_FIXTURES = {
    RecommendationState.RECOMMEND: "recommendation_RECOMMEND",
    RecommendationState.CONFLICT_REQUIRES_REVIEW: "recommendation_CONFLICT_REQUIRES_REVIEW",
    RecommendationState.INSUFFICIENT_INFORMATION: "recommendation_INSUFFICIENT_INFORMATION",
    RecommendationState.SUPPRESSED: "recommendation_SUPPRESSED",
    RecommendationState.NOT_APPLICABLE: "recommendation_NOT_APPLICABLE",
    RecommendationState.DO_NOT_RECOMMEND: "recommendation_DO_NOT_RECOMMEND",
}


def _committed_text(name: str) -> str:
    return (FIXTURE_DIR / f"{name}.json").read_text(encoding="utf-8")


def _committed(name: str) -> Contract:
    return FIXTURE_MODELS[name].model_validate_json(_committed_text(name))


# ---------------------------------------------------------------------------
# Presence, validity and round-trips
# ---------------------------------------------------------------------------


def test_fixture_map_matches_generator_and_directory() -> None:
    on_disk = {path.stem for path in FIXTURE_DIR.glob("*.json")}
    assert set(FIXTURE_MODELS) == set(build_fixtures()) == on_disk


@pytest.mark.parametrize("name", list(FIXTURE_MODELS))
def test_every_fixture_validates_as_its_contract(name: str) -> None:
    model = FIXTURE_MODELS[name].model_validate_json(_committed_text(name))
    assert isinstance(model, FIXTURE_MODELS[name])


@pytest.mark.parametrize("name", list(FIXTURE_MODELS))
def test_every_fixture_round_trips(name: str) -> None:
    cls = FIXTURE_MODELS[name]
    model = cls.model_validate_json(_committed_text(name))
    again = cls.model_validate_json(model.model_dump_json())
    assert again == model
    assert json.loads(model.model_dump_json()) == json.loads(_committed_text(name))


@pytest.mark.parametrize("name", list(FIXTURE_MODELS))
def test_committed_fixture_files_are_generator_output(name: str) -> None:
    assert _committed_text(name) == render_fixture(build_fixtures()[name])


def test_generator_is_deterministic() -> None:
    first = {name: render_fixture(model) for name, model in build_fixtures().items()}
    second = {name: render_fixture(model) for name, model in build_fixtures().items()}
    assert first == second


def test_write_fixtures_reproduces_committed_files(tmp_path: Path) -> None:
    write_fixtures(tmp_path)
    for name in FIXTURE_MODELS:
        assert (tmp_path / f"{name}.json").read_text(encoding="utf-8") == _committed_text(name)


# ---------------------------------------------------------------------------
# Coverage of the controlled states
# ---------------------------------------------------------------------------


def test_all_six_recommendation_states_are_covered() -> None:
    states = {_committed(name).recommendation_status for name in RECOMMENDATION_FIXTURES.values()}
    assert states == set(RecommendationState)


@pytest.mark.parametrize(
    ("state", "customer_id", "product"),
    [
        (RecommendationState.RECOMMEND, "C10001", Product.EV_FINANCE),
        (RecommendationState.CONFLICT_REQUIRES_REVIEW, "C10004", Product.EV_FINANCE),
        (RecommendationState.INSUFFICIENT_INFORMATION, "C10005", Product.SOLAR_FINANCE),
        (RecommendationState.SUPPRESSED, "C10006", Product.EV_FINANCE),
        (RecommendationState.NOT_APPLICABLE, "C10006", Product.PAPERLESS_BANKING),
        (RecommendationState.DO_NOT_RECOMMEND, "C10007", Product.GREEN_HOME),
    ],
)
def test_recommendation_fixture_subjects(
    state: RecommendationState, customer_id: str, product: Product
) -> None:
    rec = _committed(RECOMMENDATION_FIXTURES[state])
    assert isinstance(rec, Recommendation)
    subject = (rec.recommendation_status, rec.customer_id, rec.opportunity_id)
    assert subject == (state, customer_id, product)
    assert rec.product_id == PRODUCT_IDS[product]


def test_recommendation_fixtures_share_their_trust_and_impact_files() -> None:
    recommend = _committed("recommendation_RECOMMEND")
    insufficient = _committed("recommendation_INSUFFICIENT_INFORMATION")
    conflict = _committed("recommendation_CONFLICT_REQUIRES_REVIEW")
    assert recommend.impact == _committed("impact_result_ev_available")
    assert recommend.trust == _committed("trust_assessment_C10001_EV")
    assert insufficient.impact == _committed("impact_result_solar_unavailable")
    assert insufficient.trust == _committed("trust_assessment_C10005_SOLAR")
    assert conflict.trust == _committed("trust_assessment_C10004_EV")


def test_recommendations_repeat_their_propensity_and_confidence() -> None:
    ev = _committed("propensity_result_C10001_EV")
    solar = _committed("propensity_result_C10005_SOLAR")
    recommend = _committed("recommendation_RECOMMEND")
    insufficient = _committed("recommendation_INSUFFICIENT_INFORMATION")
    assert recommend.propensity == ev.propensity
    assert recommend.confidence == ev.confidence
    assert insufficient.propensity == solar.propensity
    assert insufficient.confidence.status is solar.confidence.status


def test_fixture_dates_follow_the_config_timeline() -> None:
    for name in FIXTURE_MODELS:
        model = _committed(name)
        if isinstance(model, Recommendation):
            assert model.data_cutoff == FEATURE_CUTOFF
            assert model.outcome_window_end == OUTCOME_WINDOW_END
            assert model.prediction_timestamp == PREDICTION_TIMESTAMP
        if isinstance(model, CustomerSnapshot):
            assert model.feature_cutoff == FEATURE_CUTOFF
        if isinstance(model, PropensityResult):
            assert model.feature_cutoff == FEATURE_CUTOFF
            assert model.outcome_window_end == OUTCOME_WINDOW_END


# ---------------------------------------------------------------------------
# Content: the spec's worked numbers and personas
# ---------------------------------------------------------------------------


def test_recommend_fixture_carries_spec_section_5_numbers() -> None:
    rec = _committed("recommendation_RECOMMEND")
    assert isinstance(rec, Recommendation)
    assert rec.propensity == pytest.approx(0.84)
    assert rec.confidence.value == pytest.approx(0.87)
    assert rec.priority is not None and rec.priority.score == pytest.approx(0.81)
    assert rec.reason_codes == ["HIGH_FUEL_SPEND", "HIGH_ANNUAL_MILEAGE", "ICE_VEHICLE_OWNER"]
    assert rec.evidence["monthly_fuel_spend"] == pytest.approx(310.0)
    assert rec.evidence["annual_mileage"] == pytest.approx(15200.0)
    assert rec.evidence["vehicle_fuel_type"] == "PETROL"
    assert rec.eligibility.message == ELIGIBILITY_MESSAGE
    assert rec.eligibility.status == "NOT_ASSESSED"


def test_customer_snapshot_c10001_carries_spec_numbers() -> None:
    snapshot = _committed("customer_snapshot_C10001")
    assert isinstance(snapshot, CustomerSnapshot)
    assert snapshot.spend.fuel_spend_90d_monthly_avg == pytest.approx(310.0)
    assert snapshot.vehicle.annual_mileage_km == pytest.approx(15200.0)
    assert snapshot.vehicle.fuel_type is not None and snapshot.vehicle.fuel_type.value == "PETROL"
    assert snapshot.features["fuel_spend_90d_avg"] == pytest.approx(310.0)


def test_snapshot_features_are_the_approved_numeric_view() -> None:
    for name in ("customer_snapshot_C10001", "customer_snapshot_C10005"):
        snapshot = _committed(name)
        assert isinstance(snapshot, CustomerSnapshot)
        assert list(snapshot.features) == list(APPROVED_FEATURES)
        assert len(APPROVED_FEATURES) == 87
        for key, value in snapshot.features.items():
            assert value is None or (type(value) is float), f"{name}.{key} is {type(value).__name__}"


def test_insufficient_snapshot_keeps_unknowns_as_none() -> None:
    snapshot = _committed("customer_snapshot_C10005")
    assert isinstance(snapshot, CustomerSnapshot)
    assert snapshot.home.home_owner is None
    assert snapshot.features["home_owner"] is None
    assert snapshot.features["electricity_kwh_12m"] is None
    assert snapshot.data_quality.transaction_months_observed == 2
    assert "home_owner" in snapshot.data_quality.missing_fields


def test_trust_fixtures_tell_their_stories() -> None:
    high = _committed("trust_assessment_C10001_EV")
    conflict = _committed("trust_assessment_C10004_EV")
    insufficient = _committed("trust_assessment_C10005_SOLAR")
    assert isinstance(high, TrustAssessment) and isinstance(conflict, TrustAssessment)
    assert isinstance(insufficient, TrustAssessment)
    assert high.status.value == "HIGH" and high.issues == []
    assert conflict.has_high_severity_conflict
    assert conflict.issues[0].code.value == "EV_RECORD_WITH_RECURRING_FUEL_SPEND"
    assert insufficient.status.value == "INSUFFICIENT"
    assert insufficient.critical_fields_present is False
    assert any(issue.code.value == "HOME_OWNERSHIP_UNKNOWN" for issue in insufficient.issues)


def test_propensity_fixtures_tell_their_stories() -> None:
    validated = _committed("propensity_result_C10001_EV")
    suppressed = _committed("propensity_result_C10005_SOLAR")
    assert isinstance(validated, PropensityResult) and isinstance(suppressed, PropensityResult)
    assert validated.confidence.status.value == "VALIDATED"
    assert validated.confidence.bucket is not None and validated.confidence.bucket.value == "HIGH"
    assert suppressed.confidence.status.value == "SUPPRESSED"
    assert suppressed.confidence.value is None and suppressed.confidence.bucket is None


def test_impact_fixtures_tell_their_stories() -> None:
    ev = _committed("impact_result_ev_available")
    solar = _committed("impact_result_solar_unavailable")
    paperless = _committed("impact_result_paperless_not_claimed")
    assert isinstance(ev, ImpactResult) and isinstance(solar, ImpactResult)
    assert isinstance(paperless, ImpactResult)
    assert (ev.baseline, ev.scenario, ev.estimated_reduction) == (2850.0, 1180.0, 1670.0)
    assert ev.methodology_id == "EV_OPERATIONAL_WTW_V1"
    assert ev.factor_source == "UK Government GHG Conversion Factors"
    assert ev.factor_version == "PINNED_AT_BUILD"
    assert solar.status.value == "UNAVAILABLE"
    assert solar.unavailable_reason == "INSUFFICIENT_SOLAR_GENERATION_INPUTS"
    assert paperless.status.value == "NOT_CLAIMED"
    assert paperless.baseline is None and paperless.estimated_reduction is None
    assert [m.name for m in paperless.secondary_metrics] == ["paper_statements_avoided_per_year"]


def test_explanation_is_grounded_in_the_recommend_fixture() -> None:
    explanation = _committed("explanation_template")
    rec = _committed("recommendation_RECOMMEND")
    assert isinstance(explanation, Explanation) and isinstance(rec, Recommendation)
    assert explanation.recommendation_id == rec.recommendation_id
    assert explanation.source.value == "TEMPLATE"
    assert explanation.grounding_result.value == "NOT_RUN"
    assert ELIGIBILITY_MESSAGE in explanation.eligibility_disclaimer
    assert "1,670" in (explanation.estimated_impact_text or "")
    assert "0.87" in (explanation.confidence_text or "")


def test_portfolio_summary_is_internally_consistent() -> None:
    summary = _committed("portfolio_summary")
    assert isinstance(summary, PortfolioSummary)
    assert sorted(row.product.value for row in summary.by_product) == sorted(p.value for p in Product)
    assert summary.customers_with_opportunity <= summary.customers_analysed
    for row in summary.by_product:
        assert row.high_trust <= row.candidates
        assert row.actionable <= row.candidates
        assert row.high_confidence <= row.actionable
    ev = next(row for row in summary.by_product if row.product is Product.EV_FINANCE)
    assert ev.estimated_impact_kg_co2e == pytest.approx(ev.actionable * 1670.0)


def test_portfolio_trends_cover_each_product_at_each_trend_cutoff() -> None:
    trends = _committed("portfolio_trends")
    assert isinstance(trends, PortfolioTrends)
    assert len(trends.points) == len(TREND_CUTOFFS) * len(Product)
    pairs = {(point.month, point.product) for point in trends.points}
    assert pairs == {(month, product) for month in TREND_CUTOFFS for product in Product}
    assert all(point.month <= FEATURE_CUTOFF for point in trends.points)
    assert date(2026, 7, 31) not in {point.month for point in trends.points}


def test_trend_points_carry_product_specific_fields_only() -> None:
    trends = _committed("portfolio_trends")
    assert isinstance(trends, PortfolioTrends)
    for point in trends.points:
        if point.product is not Product.EV_FINANCE:
            assert point.estimated_impact_kg_co2e is None
        if point.product is not Product.PAPERLESS_BANKING:
            assert point.paperless_adoption_rate is None


# ---------------------------------------------------------------------------
# Loading helpers
# ---------------------------------------------------------------------------


def test_load_fixture_accepts_bare_and_suffixed_names() -> None:
    assert load_fixture("recommendation_RECOMMEND") == load_fixture("recommendation_RECOMMEND.json")


def test_load_fixture_rejects_unknown_names() -> None:
    with pytest.raises(FileNotFoundError):
        load_fixture("no_such_fixture")


def test_load_model_returns_validated_instance() -> None:
    rec = load_model("recommendation_SUPPRESSED", Recommendation)
    assert isinstance(rec, Recommendation)
    assert rec.recommendation_status is RecommendationState.SUPPRESSED


# ---------------------------------------------------------------------------
# Fake providers
# ---------------------------------------------------------------------------


def test_fake_providers_satisfy_the_protocols() -> None:
    assert isinstance(FixtureSnapshotProvider(), CustomerSnapshotProvider)
    assert isinstance(FixturePropensityProvider(), PropensityProvider)
    assert isinstance(FixtureTrustProvider(), TrustProvider)


def test_snapshot_provider_serves_fixture_customers() -> None:
    provider = FixtureSnapshotProvider()
    assert provider.list_customer_ids() == ["C10001", "C10005"]
    snapshot = provider.get_snapshot("C10001")
    assert snapshot == _committed("customer_snapshot_C10001")
    assert provider.get_snapshot("C10001", cutoff=FEATURE_CUTOFF) == snapshot
    assert provider.get_snapshot("C10001", cutoff=date(2026, 3, 31)) is None
    assert provider.get_snapshot("C99999") is None


def test_propensity_provider_scores_fixture_pairs() -> None:
    provider = FixturePropensityProvider()
    ev_snapshot = _committed("customer_snapshot_C10001")
    solar_snapshot = _committed("customer_snapshot_C10005")
    assert isinstance(ev_snapshot, CustomerSnapshot) and isinstance(solar_snapshot, CustomerSnapshot)
    assert provider.score(ev_snapshot, Product.EV_FINANCE) == _committed("propensity_result_C10001_EV")
    solar_result = _committed("propensity_result_C10005_SOLAR")
    ev_result = _committed("propensity_result_C10001_EV")
    assert provider.score(solar_snapshot, Product.SOLAR_FINANCE) == solar_result
    assert provider.score_many([ev_snapshot], Product.EV_FINANCE) == [ev_result]
    with pytest.raises(LookupError):
        provider.score(ev_snapshot, Product.SOLAR_FINANCE)


def test_trust_provider_assesses_fixture_pairs() -> None:
    provider = FixtureTrustProvider()
    ev_snapshot = _committed("customer_snapshot_C10001")
    solar_snapshot = _committed("customer_snapshot_C10005")
    conflict_snapshot = ev_snapshot.model_copy(update={"customer_id": "C10004"})
    assert isinstance(ev_snapshot, CustomerSnapshot) and isinstance(solar_snapshot, CustomerSnapshot)
    assert provider.assess(ev_snapshot, Product.EV_FINANCE).status.value == "HIGH"
    assert provider.assess(conflict_snapshot, Product.EV_FINANCE).status.value == "LOW"
    assert provider.assess(solar_snapshot, Product.SOLAR_FINANCE).status.value == "INSUFFICIENT"
    with pytest.raises(LookupError):
        provider.assess(ev_snapshot, Product.SOLAR_FINANCE)


def test_providers_accept_injected_records() -> None:
    assert FixtureSnapshotProvider([]).list_customer_ids() == []
    assert FixturePropensityProvider([]).score_many([], Product.EV_FINANCE) == []
    assert FixtureTrustProvider([]) is not None
