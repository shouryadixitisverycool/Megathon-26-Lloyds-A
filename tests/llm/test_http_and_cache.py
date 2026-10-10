"""Offline transport checks for caching, fixed claims and measured usage."""

import json
from datetime import timedelta

import httpx
import pytest

from greenpath.llm.evaluation import approved_output, synthetic_recommendation
from greenpath.llm.http_provider import HTTPExplanationProvider, configured_provider
from greenpath.llm.ports import ExplanationRequest
from greenpath.llm.service import ExplanationService


def provider(transport):
    return HTTPExplanationProvider(endpoint="https://example.test/completions", model="pinned-model",
        model_version="pinned-model-v1", api_key="fixture-secret", transport=transport,
        input_price_per_million=1., output_price_per_million=2.)


def test_http_schema_timeout_usage_and_cache():
    calls = []
    def handle(request):
        calls.append(request)
        payload = json.loads(request.content)
        assert payload["model"] == "pinned-model"
        assert payload["response_format"]["json_schema"]["strict"]
        assert request.extensions["timeout"]["read"] == .5
        facts = ExplanationRequest.model_validate_json(payload["messages"][1]["content"])
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(approved_output(facts))}}],
                                       "usage": {"prompt_tokens": 100, "completion_tokens": 40}})
    service = ExplanationService(provider(httpx.MockTransport(handle)), timeout_seconds=.5)
    rec = synthetic_recommendation()
    first = service.explain(rec)
    assert first.source == "llm"
    assert service.explain(rec.model_copy(update={"timestamp": rec.timestamp + timedelta(seconds=1)})) == first
    assert len(calls) == 1
    metrics = service.metrics()
    assert metrics["cache_hits"] == metrics["cache_misses"] == 1
    assert metrics["cache_hit_rate"] == .5
    assert metrics["provider_measurements"]["average_input_tokens"] == 100
    assert metrics["live_provider_cost"] == pytest.approx(.00018)
    assert metrics["live_provider_latency_ms"] >= 0
    assert "fixture-secret" not in json.dumps(metrics)


def test_cache_changes_with_model_prompt_locale_and_evidence():
    service = ExplanationService()
    rec = synthetic_recommendation()
    service.explain(rec)
    service.explain(rec)
    assert service.metrics()["cache_hits"] == 1
    service.prompt_version = "changed-prompt"
    service.explain(rec)
    service.locale = "hi"
    service.explain(rec)
    service.provider_version = "changed-model"
    service.explain(rec)
    service.explain(rec.model_copy(update={"rules_version": "new-rules"}))
    assert service.metrics()["cache_misses"] == 5
    assert service.metrics()["offline_cost"] == 0
    assert service.metrics()["live_provider_cost"] is None


def test_http_claim_change_and_transport_error_use_template():
    def malicious(request):
        payload = json.loads(request.content)
        facts = ExplanationRequest.model_validate_json(payload["messages"][1]["content"])
        output = approved_output(facts)
        output["state"] = "SUPPRESSED"
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(output)}}]})
    service = ExplanationService(provider(httpx.MockTransport(malicious)))
    assert service.explain(synthetic_recommendation()).fallback_reason == "CLAIMS_REJECTED"
    assert service.metrics()["live_provider_cost"] is None
    def failed(request):
        raise httpx.ReadTimeout("fixture timeout")
    service = ExplanationService(provider(httpx.MockTransport(failed)))
    assert service.explain(synthetic_recommendation()).fallback_reason == "PROVIDER_ERROR"


def test_no_key_offline_and_partial_keyed_config_rejected(monkeypatch):
    monkeypatch.delenv("GREENPATH_LLM_API_KEY", raising=False)
    assert configured_provider() is None
    monkeypatch.setenv("GREENPATH_LLM_API_KEY", "test-key")
    monkeypatch.delenv("GREENPATH_LLM_ENDPOINT", raising=False)
    with pytest.raises(ValueError, match="require endpoint"):
        configured_provider()
