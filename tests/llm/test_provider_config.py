"""Configuration and strict-schema checks without live provider calls."""

import json
import sys

import httpx
import pytest

from greenr.llm.evaluation import approved_output, synthetic_recommendation
from greenr.llm.http_provider import configured_provider, strict_response_schema
from greenr.llm.ports import ExplanationRequest
from greenr.llm.service import ExplanationService
from greenr.llm import live_evaluation


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    for name in ("OPENAI_API_KEY", "GREENR_LLM_API_KEY", "GREENR_LLM_ENDPOINT",
                 "LLM_MODEL", "LLM_MODEL_VERSION", "PROMPT_VERSION", "TEMPERATURE",
                 "MAX_OUTPUT_TOKENS", "GREENR_LLM_TOKEN_LIMIT_PARAMETER",
                 "GREENR_LLM_TIMEOUT_SECONDS", "GREENR_LLM_INPUT_PRICE_PER_MILLION",
                 "GREENR_LLM_OUTPUT_PRICE_PER_MILLION", "GREENR_LLM_CACHED_INPUT_PRICE_PER_MILLION"):
        monkeypatch.delenv(name, raising=False)


def test_manifest_defaults_and_key_precedence(monkeypatch):
    assert configured_provider() is None
    monkeypatch.setenv("GREENR_LLM_API_KEY", "fallback-only")
    provider = configured_provider()
    assert provider.api_key == "fallback-only"
    monkeypatch.setenv("OPENAI_API_KEY", "standard-only")
    provider = configured_provider()
    assert provider.api_key == "standard-only"
    assert provider.model == provider.version == "gpt-6-luna"
    assert provider.endpoint == "https://api.openai.com/v1/chat/completions"
    assert provider.temperature is None
    assert provider.token_limit_parameter == "max_completion_tokens"
    assert provider.max_output_tokens == 1600
    assert provider.timeout_seconds == 30


def test_explicit_environment_overrides(monkeypatch):
    for name, value in {"OPENAI_API_KEY": "mock-only", "GREENR_LLM_ENDPOINT": "https://example.test",
                        "LLM_MODEL": "custom-alias", "PROMPT_VERSION": "custom-prompt",
                        "TEMPERATURE": "0.2", "MAX_OUTPUT_TOKENS": "99",
                        "GREENR_LLM_TOKEN_LIMIT_PARAMETER": "max_tokens",
                        "GREENR_LLM_TIMEOUT_SECONDS": "7"}.items():
        monkeypatch.setenv(name, value)
    provider = configured_provider()
    assert provider.model == provider.version == "custom-alias"
    assert provider.endpoint == "https://example.test"
    assert provider.prompt_version == "custom-prompt"
    assert provider.temperature == .2
    assert provider.max_output_tokens == 99
    assert provider.token_limit_parameter == "max_tokens"
    assert provider.timeout_seconds == 7
    monkeypatch.setenv("LLM_MODEL_VERSION", "explicit-version")
    assert configured_provider().version == "explicit-version"


def test_luna_request_options_and_strict_nullable_schema(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "mock-only")
    provider = configured_provider()
    def handle(request):
        payload = json.loads(request.content)
        assert payload["model"] == "gpt-6-luna"
        assert payload["max_completion_tokens"] == 1600
        assert "max_tokens" not in payload and "temperature" not in payload
        schema = payload["response_format"]["json_schema"]["schema"]
        assert set(schema["required"]) == set(schema["properties"])
        assert schema["additionalProperties"] is False
        assert {"type": "null"} in schema["properties"]["impact_value"]["anyOf"]
        facts = ExplanationRequest.model_validate_json(payload["messages"][1]["content"])
        assert facts.impact_value is None
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(approved_output(facts))}}]})
    provider.transport = httpx.MockTransport(handle)
    assert ExplanationService(provider, timeout_seconds=.5).explain(synthetic_recommendation(available=False)).source == "llm"
    for definition in strict_response_schema().get("$defs", {}).values():
        if "properties" in definition:
            assert set(definition["required"]) == set(definition["properties"])
            assert definition["additionalProperties"] is False


def test_live_cli_accepts_alias_and_records_effective_overrides(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "mock-secret")
    monkeypatch.setenv("GREENR_LLM_TIMEOUT_SECONDS", "9")
    for kind in ("INPUT", "OUTPUT", "CACHED_INPUT"):
        monkeypatch.setenv(f"GREENR_LLM_{kind}_PRICE_PER_MILLION", "1")
    def run(provider, *, count, timeout_seconds):
        assert provider.model == "gpt-6-luna"
        assert timeout_seconds == 9
        return {"complete": True}
    monkeypatch.setattr(live_evaluation, "run_live_evaluation", run)
    output = tmp_path / "report.json"
    monkeypatch.setattr(sys, "argv", ["live", "--allow-paid-provider", "--output", str(output)])
    assert live_evaluation.main() == 0
    report = json.loads(output.read_text())
    assert report["effective_configuration"]["timeout_seconds"] == 9
    assert "mock-secret" not in output.read_text()


def test_live_cli_requires_prices_before_any_call(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "mock-only")
    monkeypatch.setattr(sys, "argv", ["live", "--allow-paid-provider", "--output", str(tmp_path / "report.json")])
    with pytest.raises(SystemExit) as error:
        live_evaluation.main()
    assert error.value.code == 2
    assert not (tmp_path / "report.json").exists()
