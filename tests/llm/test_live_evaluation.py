"""Mock-only live evaluator checks. These tests never use credentials or network."""

import json
import sys

import httpx
import pytest

from greenpath.llm.evaluation import approved_output, confidence_recommendation, run_evaluation, synthetic_recommendation
from greenpath.llm.evaluation import FixedProvider
from greenpath.llm.http_provider import HTTPExplanationProvider
from greenpath.llm.live_evaluation import live_cases, main, run_live_evaluation
from greenpath.llm.ports import ExplanationRequest
from greenpath.llm.service import ExplanationService


def test_public_fields_retain_legacy_text_and_grounded_confidence():
    from greenpath.contracts.product import Explanation

    for suppressed in (False, True):
        result = ExplanationService().explain(confidence_recommendation(suppressed=suppressed))
        assert result.headline.startswith("EV Finance:")
        assert result.why_recommended
        assert result.missing_information
        assert "Review" in result.action_text
        assert result.estimated_impact_text in result.text
        assert result.confidence_text in result.text
        assert ("withheld" in result.confidence_text) == suppressed
        assert ("0.2" in result.confidence_text) != suppressed
        assert result.model_dump(mode="json")["why_recommended"] == list(result.why_recommended)
        canonical = Explanation.model_validate_json(result.model_dump_json())
        assert canonical.headline == result.headline
        assert canonical.action_text == result.action_text
        assert canonical.why_recommended == result.why_recommended


def test_complete_evaluation_categories():
    report = run_evaluation()
    categories = {category for row in report["cases"] for category in row["categories"]}
    assert categories >= {
        "normal_recommendation", "missing_data", "conflicting_signals", "low_confidence",
        "no_impact_available", "product_excluded", "multiple_opportunities", "paperless_case",
        "negative_or_zero_impact", "adversarial_request", "prompt_injection", "guarantee_savings",
        "claim_eligibility", "alter_model_score",
    }
    assert all(row["structured_consistency"] for row in report["cases"])
    multiple = [row for row in report["cases"] if "multiple_opportunities" in row["categories"]]
    assert len({row["product"] for row in multiple}) == 2


def test_mock_live_usage_cost_cache_and_fixed_case_count():
    def handle(request):
        payload = json.loads(request.content)
        facts = ExplanationRequest.model_validate_json(payload["messages"][1]["content"])
        return httpx.Response(200, json={
            "choices": [{"message": {"content": json.dumps(approved_output(facts))}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 40,
                      "prompt_tokens_details": {"cached_tokens": 20}},
        })
    provider = HTTPExplanationProvider(
        endpoint="https://example.test", model="gpt-4.1-mini-2025-04-14",
        model_version="gpt-4.1-mini-2025-04-14", api_key="mock-only-secret",
        transport=httpx.MockTransport(handle), input_price_per_million=1,
        output_price_per_million=2, cached_input_price_per_million=.5,
    )
    report = run_live_evaluation(provider, count=100)
    assert report["complete"]
    assert report["completed_cases"] == 100
    assert report["summary"]["acceptance_rate"] == 1
    assert all(row["cost"] == pytest.approx(.00017) for row in report["cases"])
    assert report["cache_experiment"]["cache_hits"] == 1
    assert report["provider_measurements"]["completed_calls"] == 101
    assert "mock-only-secret" not in json.dumps(report)
    assert all(row["latency_ms"] >= 0 for row in report["cases"])
    assert len(live_cases(200)) == 200
    with pytest.raises(ValueError):
        live_cases(99)


def test_live_cli_requires_authorization_and_credentials(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "argv", ["live_evaluation", "--output", str(tmp_path / "report.json")])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2
    monkeypatch.delenv("GREENPATH_LLM_API_KEY", raising=False)
    monkeypatch.setattr(sys, "argv", ["live_evaluation", "--allow-paid-provider", "--output", str(tmp_path / "report.json")])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2
    assert not (tmp_path / "report.json").exists()


def test_live_inputs_are_distinct_grounded_prompts():
    provider = FixedProvider()
    service = ExplanationService(provider, cache_size=0)
    for _, (_, rec, _, _, _) in live_cases(200):
        assert service.explain(rec).source == "llm"
    assert len({request.model_dump_json() for request in provider.requests}) == 200


def test_live_failure_stops_without_fabricated_zero_cost():
    calls = []
    def handle(request):
        calls.append(request)
        if len(calls) == 2:
            raise httpx.ReadTimeout("mock failure")
        payload = json.loads(request.content)
        facts = ExplanationRequest.model_validate_json(payload["messages"][1]["content"])
        return httpx.Response(200, json={
            "choices": [{"message": {"content": json.dumps(approved_output(facts))}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 40},
        })
    provider = HTTPExplanationProvider(endpoint="https://example.test", model="mock", model_version="mock-v1",
        api_key="mock-only", transport=httpx.MockTransport(handle),
        input_price_per_million=1, output_price_per_million=2)
    report = run_live_evaluation(provider)
    assert not report["complete"]
    assert report["completed_cases"] == len(calls) == 2
    assert report["cases"][1]["cost"] is None
    assert report["cases"][1]["input_tokens"] is None
    assert report["provider_measurements"]["measured_cost"] is None
    assert report["provider_measurements"]["attempted_calls"] == 2
    assert report["cache_experiment"]["requests"] == 0


def test_co2e_limit_wording_tracks_units():
    from greenpath.contracts.customer import CustomerSnapshot
    from greenpath.contracts.fixtures import load_model
    from greenpath.impact import Product
    from greenpath.impact.uk_adapter import UKImpactCalculator

    snapshot = load_model("customer_snapshot_C10001", CustomerSnapshot)
    snapshot = snapshot.model_copy(update={"features": {**snapshot.features,
        "ice_litres_per_100km": 6.5, "ev_kwh_per_100km": 18.0, "charging_efficiency": .9}})
    impact = UKImpactCalculator(Product.EV_FINANCE).calculate(snapshot)
    rec = synthetic_recommendation().model_copy(update={"impact": impact})
    result = ExplanationService().explain(rec)
    assert "operational CO2e" in result.estimated_impact_text
    assert "operational CO2 within" not in result.text


@pytest.mark.parametrize("usage", [{}, {"prompt_tokens": 100, "completion_tokens": 40,
                                        "prompt_tokens_details": {"cached_tokens": 20}}])
def test_missing_usage_or_cached_pricing_leaves_cost_null(usage):
    def handle(request):
        payload = json.loads(request.content)
        facts = ExplanationRequest.model_validate_json(payload["messages"][1]["content"])
        return httpx.Response(200, json={
            "choices": [{"message": {"content": json.dumps(approved_output(facts))}}], "usage": usage,
        })
    provider = HTTPExplanationProvider(endpoint="https://example.test", model="mock", model_version="mock-v1",
        api_key="mock-only", transport=httpx.MockTransport(handle),
        input_price_per_million=1, output_price_per_million=2)
    assert ExplanationService(provider).explain(synthetic_recommendation()).source == "llm"
    assert provider.metrics()["measured_cost"] is None
