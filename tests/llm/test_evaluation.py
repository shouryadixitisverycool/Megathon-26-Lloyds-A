"""Coverage and integrity checks for the fixed offline evaluation suite."""

import pytest

from greenpath.contracts.product import RecommendationState
from greenpath.impact import Product
from greenpath.llm import ExplanationService
from greenpath.llm.evaluation import (
    INJECTION_MARKER, MALICIOUS_FIELDS, FixedProvider, evaluation_cases,
    run_evaluation, synthetic_recommendation,
)


@pytest.fixture(scope="module")
def report():
    return run_evaluation()


def test_fixed_suite_is_unique_and_preserves_original_cases(report):
    cases = evaluation_cases()
    assert len(cases) == 196
    assert 100 <= len(cases) <= 200
    signatures = [(attack, rec.model_dump_json()) for attack, rec, _, _, _ in cases.values()]
    assert len(set(signatures)) == len(signatures)
    assert signatures == [(attack, rec.model_dump_json())
                          for attack, rec, _, _, _ in evaluation_cases().values()]
    original = list(cases.values())[:18]
    assert [row[0] for row in original] == [
        "valid", "reverse", "product", "state", "reason", "number", "units", "eligibility",
        "free_text", "omit", "duplicate", "invent_sentence", "malformed", "error", "timeout",
        "wrong_null", "sign", "number",
    ]
    assert original[-2][1].impact.value < 0
    assert original[-1][1].impact.value is None
    assert [row["case"] for row in report["cases"]] == list(cases)
    assert all(row["passed"] and row["prompt_safe"] for row in report["cases"])


def test_product_state_and_signed_impact_coverage(report):
    rows = report["cases"]
    for product in Product:
        for state in RecommendationState:
            missing = [row for row in rows if row["product"] == product.value
                       and row["state"] == state.value and row["impact_kind"] == "missing"]
            assert {"valid", "product", "state", "units"} <= {row["attack"] for row in missing}
            assert all(row["impact_value"] is None for row in missing)
    for state in RecommendationState:
        for kind in ("positive", "negative", "zero"):
            signed = [row for row in rows if row["product"] == Product.EV_FINANCE.value
                      and row["state"] == state.value and row["impact_kind"] == kind]
            assert {"valid", "reverse", "wrong_null", "units"} <= {row["attack"] for row in signed}
    assert all(row["impact_kind"] == "missing" for row in rows
               if row["product"] == Product.PAPERLESS_BANKING.value)


@pytest.mark.parametrize("product", list(Product))
@pytest.mark.parametrize("state", list(RecommendationState))
@pytest.mark.parametrize("units", ["kg CO2", "kg CO2/year", "kg CO2e/year"])
def test_identity_attacks_always_change_the_requested_claim(product, state, units):
    provider = FixedProvider()
    ExplanationService(provider).explain(synthetic_recommendation(product=product, state=state))
    request = provider.requests[0].model_copy(update={"units": units})
    for attack in ("product", "state", "units"):
        output = FixedProvider(attack).generate(request, timeout_seconds=1)
        expected = getattr(request, attack)
        assert output[attack] != expected


@pytest.mark.parametrize("field", MALICIOUS_FIELDS)
@pytest.mark.parametrize("product", list(Product))
def test_each_malicious_field_is_excluded_from_the_prompt_and_text(field, product):
    rec = synthetic_recommendation(product=product, malicious_field=field)
    assert INJECTION_MARKER in rec.model_dump_json()
    provider = FixedProvider()
    result = ExplanationService(provider).explain(rec)
    assert result.source == "llm"
    assert len(provider.requests) == 1
    assert INJECTION_MARKER not in provider.requests[0].model_dump_json()
    assert INJECTION_MARKER not in result.text
    if field == "propensity":
        assert "0.99" not in provider.requests[0].model_dump_json()
        assert "0.95" not in provider.requests[0].model_dump_json()


def test_summary_schema_and_offline_limitations_are_unchanged(report):
    summary = report["summary"]
    assert set(summary) == {
        "total", "passed", "groundedness_rate", "numeric_consistency_rate", "unsupported_claims",
        "fallback_rate", "local_mean_latency_ms", "live_provider_latency_ms", "live_provider_cost",
    }
    assert summary["total"] == summary["passed"] == 196
    assert summary["live_provider_latency_ms"] is summary["live_provider_cost"] is None
    assert "no live LLM called" in report["provider"]
    assert summary["fallback_rate"] == sum(not row["accepted"] for row in report["cases"]) / 196
    unknown = [row for row in report["cases"] if row["attack"] == "unknown_reason"]
    assert len(unknown) == 4
    assert all(row["fallback_reason"] == "UNRECOGNIZED_REASON_CODE" for row in unknown)
