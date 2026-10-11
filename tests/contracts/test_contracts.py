"""Contract validators, strictness and the committed JSON Schemas.

Invalid payloads are built by mutating a valid fixture, so each rejection is checked against
a realistic object rather than a hand-made stub.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from greenr.contracts import (
    CONTRACT_VERSION,
    CustomerSnapshot,
    Explanation,
    ImpactResult,
    PortfolioSummary,
    PortfolioTrends,
    PropensityResult,
    Recommendation,
    RecommendationState,
    TrustAssessment,
)
from greenr.contracts.export_schemas import (
    SCHEMA_DIR,
    TOP_LEVEL_CONTRACTS,
    build_schemas,
    render_schema,
)
from greenr.contracts.fixtures import load_fixture


def _payload(name: str) -> dict[str, Any]:
    return load_fixture(name)


# ---------------------------------------------------------------------------
# Confidence and propensity (spec 16, PropensityResult population rules)
# ---------------------------------------------------------------------------


def test_suppressed_confidence_must_not_carry_a_value() -> None:
    payload = _payload("propensity_result_C10005_SOLAR")
    payload["confidence"]["value"] = 0.5
    with pytest.raises(ValidationError, match="suppressed confidence must not carry"):
        PropensityResult.model_validate(payload)


def test_suppressed_confidence_must_not_carry_a_bucket() -> None:
    payload = _payload("propensity_result_C10005_SOLAR")
    payload["confidence"]["bucket"] = "LOW"
    with pytest.raises(ValidationError, match="suppressed confidence must not carry"):
        PropensityResult.model_validate(payload)


def test_suppressed_confidence_must_state_its_limitation() -> None:
    payload = _payload("propensity_result_C10005_SOLAR")
    payload["confidence"]["limitation"] = None
    with pytest.raises(ValidationError, match="must state its limitation"):
        PropensityResult.model_validate(payload)


def test_validated_confidence_without_bucket_is_rejected() -> None:
    payload = _payload("propensity_result_C10001_EV")
    payload["confidence"]["bucket"] = None
    with pytest.raises(ValidationError, match="requires value and bucket"):
        PropensityResult.model_validate(payload)


def test_validated_confidence_without_value_is_rejected() -> None:
    payload = _payload("propensity_result_C10001_EV")
    payload["confidence"]["value"] = None
    with pytest.raises(ValidationError, match="requires value and bucket"):
        PropensityResult.model_validate(payload)


def test_population_exclusion_set_while_in_population_is_rejected() -> None:
    payload = _payload("propensity_result_C10001_EV")
    payload["population_exclusion"] = "ALREADY_HOLDS_PRODUCT"
    with pytest.raises(ValidationError, match="population_exclusion must be set iff"):
        PropensityResult.model_validate(payload)


def test_population_exclusion_missing_when_outside_population_is_rejected() -> None:
    payload = _payload("propensity_result_C10001_EV")
    payload["in_model_population"] = False
    with pytest.raises(ValidationError, match="population_exclusion must be set iff"):
        PropensityResult.model_validate(payload)


def test_propensity_must_lie_in_unit_interval() -> None:
    for bad in (1.2, -0.1):
        payload = _payload("propensity_result_C10001_EV")
        payload["propensity"] = bad
        with pytest.raises(ValidationError):
            PropensityResult.model_validate(payload)


def test_propensity_bounds_apply_to_recommendations_too() -> None:
    payload = _payload("recommendation_RECOMMEND")
    payload["propensity"] = 1.01
    with pytest.raises(ValidationError):
        Recommendation.model_validate(payload)


# ---------------------------------------------------------------------------
# Impact status consistency (spec 21-26)
# ---------------------------------------------------------------------------


def test_available_impact_without_factor_source_is_rejected() -> None:
    payload = _payload("impact_result_ev_available")
    payload["factor_source"] = None
    with pytest.raises(ValidationError, match="AVAILABLE impact requires"):
        ImpactResult.model_validate(payload)


def test_available_impact_without_factor_version_is_rejected() -> None:
    payload = _payload("impact_result_ev_available")
    payload["factor_version"] = None
    with pytest.raises(ValidationError, match="AVAILABLE impact requires"):
        ImpactResult.model_validate(payload)


def test_available_impact_without_carbon_numbers_is_rejected() -> None:
    payload = _payload("impact_result_ev_available")
    payload["scenario"] = None
    with pytest.raises(ValidationError, match="AVAILABLE impact requires"):
        ImpactResult.model_validate(payload)


def test_unavailable_impact_with_numbers_is_rejected() -> None:
    payload = _payload("impact_result_solar_unavailable")
    payload["baseline"] = 100.0
    with pytest.raises(ValidationError, match="must not carry carbon numbers"):
        ImpactResult.model_validate(payload)


def test_unavailable_impact_without_reason_is_rejected() -> None:
    payload = _payload("impact_result_solar_unavailable")
    payload["unavailable_reason"] = None
    with pytest.raises(ValidationError, match="requires unavailable_reason"):
        ImpactResult.model_validate(payload)


def test_not_claimed_impact_with_carbon_numbers_is_rejected() -> None:
    payload = _payload("impact_result_paperless_not_claimed")
    payload["estimated_reduction"] = 10.0
    with pytest.raises(ValidationError, match="must not carry carbon numbers"):
        ImpactResult.model_validate(payload)


# ---------------------------------------------------------------------------
# Recommendation cross-field rules
# ---------------------------------------------------------------------------


def test_recommendation_product_id_mismatch_is_rejected() -> None:
    payload = _payload("recommendation_RECOMMEND")
    payload["product_id"] = "GP02"
    with pytest.raises(ValidationError, match="product_id does not match opportunity_id"):
        Recommendation.model_validate(payload)


def test_recommendation_trust_for_another_product_is_rejected() -> None:
    payload = _payload("recommendation_RECOMMEND")
    payload["trust"]["product"] = "GREEN_HOME"
    with pytest.raises(ValidationError, match="trust assessment is for a different product"):
        Recommendation.model_validate(payload)


def test_recommendation_impact_for_another_product_is_rejected() -> None:
    payload = _payload("recommendation_INSUFFICIENT_INFORMATION")
    payload["impact"]["product"] = "EV_FINANCE"
    with pytest.raises(ValidationError, match="impact result is for a different product"):
        Recommendation.model_validate(payload)


def test_eligibility_status_other_than_not_assessed_is_rejected() -> None:
    payload = _payload("recommendation_RECOMMEND")
    payload["eligibility"]["status"] = "ELIGIBLE"
    with pytest.raises(ValidationError):
        Recommendation.model_validate(payload)


def test_eligibility_status_not_assessed_is_accepted() -> None:
    payload = _payload("recommendation_RECOMMEND")
    payload["eligibility"]["status"] = "NOT_ASSESSED"
    assert Recommendation.model_validate(payload).eligibility.status == "NOT_ASSESSED"


def test_unknown_recommendation_state_is_rejected() -> None:
    payload = _payload("recommendation_RECOMMEND")
    payload["recommendation_status"] = "ELIGIBLE_FOR_LOAN"
    with pytest.raises(ValidationError):
        Recommendation.model_validate(payload)


def test_priority_rank_must_be_positive() -> None:
    payload = _payload("recommendation_RECOMMEND")
    payload["priority"]["rank"] = 0
    with pytest.raises(ValidationError):
        Recommendation.model_validate(payload)


# ---------------------------------------------------------------------------
# Strictness: unknown fields are rejected everywhere
# ---------------------------------------------------------------------------

_TOP_LEVEL_FIXTURES: list[tuple[str, type]] = [
    ("customer_snapshot_C10001", CustomerSnapshot),
    ("propensity_result_C10001_EV", PropensityResult),
    ("trust_assessment_C10001_EV", TrustAssessment),
    ("impact_result_ev_available", ImpactResult),
    ("recommendation_RECOMMEND", Recommendation),
    ("explanation_template", Explanation),
    ("portfolio_summary", PortfolioSummary),
    ("portfolio_trends", PortfolioTrends),
]


@pytest.mark.parametrize(("fixture", "cls"), _TOP_LEVEL_FIXTURES, ids=[f for f, _ in _TOP_LEVEL_FIXTURES])
def test_unknown_top_level_field_is_forbidden(fixture: str, cls: type) -> None:
    payload = _payload(fixture)
    payload["unexpected_field"] = "value"
    with pytest.raises(ValidationError, match="unexpected_field"):
        cls.model_validate(payload)


def test_unknown_nested_field_is_forbidden() -> None:
    payload = _payload("customer_snapshot_C10001")
    payload["vehicle"]["colour"] = "red"
    with pytest.raises(ValidationError, match="colour"):
        CustomerSnapshot.model_validate(payload)


def test_audit_only_attributes_cannot_enter_the_snapshot() -> None:
    for field in ("age_band", "income_band", "postcode_sector"):
        payload = _payload("customer_snapshot_C10001")
        payload[field] = "25-34"
        with pytest.raises(ValidationError):
            CustomerSnapshot.model_validate(payload)


def test_contract_models_are_frozen() -> None:
    snapshot = CustomerSnapshot.model_validate(_payload("customer_snapshot_C10001"))
    with pytest.raises(ValidationError):
        snapshot.customer_id = "C99999"  # type: ignore[misc]


def test_contract_version_is_the_documented_release() -> None:
    assert CONTRACT_VERSION == "1.0.0"


def test_recommendation_states_are_exactly_the_spec_six() -> None:
    assert {state.value for state in RecommendationState} == {
        "RECOMMEND",
        "DO_NOT_RECOMMEND",
        "INSUFFICIENT_INFORMATION",
        "CONFLICT_REQUIRES_REVIEW",
        "NOT_APPLICABLE",
        "SUPPRESSED",
    }


def test_trust_high_severity_conflict_property() -> None:
    conflicted = TrustAssessment.model_validate(_payload("trust_assessment_C10004_EV"))
    clean = TrustAssessment.model_validate(_payload("trust_assessment_C10001_EV"))
    assert conflicted.has_high_severity_conflict is True
    assert clean.has_high_severity_conflict is False


# ---------------------------------------------------------------------------
# JSON Schemas
# ---------------------------------------------------------------------------


def test_schema_files_are_up_to_date() -> None:
    for file_name, schema in build_schemas().items():
        text = (SCHEMA_DIR / file_name).read_text(encoding="utf-8")
        assert text == render_schema(schema), (
            f"{file_name} is stale; regenerate with `make schemas`"
        )


def test_no_stale_schema_files_remain() -> None:
    expected = set(build_schemas()) | {"CONTRACT_VERSION"}
    actual = {path.name for path in SCHEMA_DIR.iterdir() if path.is_file()}
    assert actual == expected


def test_contract_version_file_matches_constant() -> None:
    text = (SCHEMA_DIR / "CONTRACT_VERSION").read_text(encoding="utf-8")
    assert text.strip() == CONTRACT_VERSION


@pytest.mark.parametrize("name", list(TOP_LEVEL_CONTRACTS))
def test_each_schema_describes_its_contract(name: str) -> None:
    cls = TOP_LEVEL_CONTRACTS[name]
    schema = build_schemas()[f"{name}.schema.json"]
    assert schema["title"] == cls.__name__
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
