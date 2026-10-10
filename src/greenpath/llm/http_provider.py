"""Optional explicitly configured HTTP adapter for structured sentence selection.

The endpoint implements a chat-completions-shaped JSON protocol. No credentials
or network access are needed for the default deterministic explanation service.
"""

import json
import math
import os
from pathlib import Path
from threading import Lock

import httpx

from .ports import ProviderExplanation


class HTTPExplanationProvider:
    def __init__(self, *, endpoint, model, model_version, api_key, prompt_version="grounded-selection-v1",
                 temperature=0.0, max_output_tokens=800, transport=None,
                 input_price_per_million=None, output_price_per_million=None,
                 cached_input_price_per_million=None, token_limit_parameter="max_tokens",
                 timeout_seconds=30.0):
        if not endpoint or not model or not model_version or not api_key:
            raise ValueError("HTTP explanations require endpoint, exact model, model version and API key")
        for price in (input_price_per_million, output_price_per_million, cached_input_price_per_million):
            if price is not None and (not math.isfinite(price) or price < 0):
                raise ValueError("Token pricing must be non-negative and finite")
        if temperature is not None and (not math.isfinite(temperature) or not 0 <= temperature <= 2):
            raise ValueError("Temperature must be between zero and two")
        if token_limit_parameter not in {"max_tokens", "max_completion_tokens"}:
            raise ValueError("Unsupported token limit parameter")
        if isinstance(timeout_seconds, bool) or not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive and finite")
        if isinstance(max_output_tokens, bool) or not isinstance(max_output_tokens, int) or max_output_tokens < 1:
            raise ValueError("max_output_tokens must be a positive integer")
        self.endpoint, self.model, self.version, self.api_key = endpoint, model, model_version, api_key
        self.prompt_version, self.temperature, self.max_output_tokens = prompt_version, temperature, max_output_tokens
        self.transport = transport
        self.token_limit_parameter, self.timeout_seconds = token_limit_parameter, timeout_seconds
        self.input_price, self.output_price = input_price_per_million, output_price_per_million
        self.cached_input_price = cached_input_price_per_million
        self._lock = Lock()
        self._calls = self._input_tokens = self._output_tokens = self._usage_calls = 0
        self._cached_tokens = 0
        self._attempts = 0

    def generate(self, request, *, timeout_seconds):
        payload = {
            "model": self.model, self.token_limit_parameter: self.max_output_tokens,
            "messages": [
                {"role": "system", "content": "Return the exact structured claims and every required sentence ID once. You may only reorder approved sentences. Do not invent facts, numbers, eligibility or new reasons."},
                {"role": "user", "content": request.model_dump_json()},
            ],
            "response_format": {"type": "json_schema", "json_schema": {
                "name": "grounded_explanation", "strict": True, "schema": strict_response_schema(),
            }},
        }
        if self.temperature is not None:
            payload["temperature"] = self.temperature
        # HTTP timeout and the service's bounded caller deadline both apply.
        with self._lock:
            self._attempts += 1
        with httpx.Client(timeout=httpx.Timeout(timeout_seconds), transport=self.transport) as client:
            response = client.post(self.endpoint, headers={"Authorization": f"Bearer {self.api_key}"}, json=payload)
            response.raise_for_status()
            body = response.json()
        usage = body.get("usage", {})
        input_tokens, output_tokens = usage.get("prompt_tokens"), usage.get("completion_tokens")
        cached_tokens = usage.get("prompt_tokens_details", {}).get("cached_tokens", 0)
        with self._lock:
            self._calls += 1
            if (isinstance(input_tokens, int) and not isinstance(input_tokens, bool) and input_tokens >= 0
                    and isinstance(output_tokens, int) and not isinstance(output_tokens, bool) and output_tokens >= 0
                    and isinstance(cached_tokens, int) and not isinstance(cached_tokens, bool)
                    and 0 <= cached_tokens <= input_tokens):
                self._usage_calls += 1
                self._input_tokens += input_tokens
                self._output_tokens += output_tokens
                self._cached_tokens += cached_tokens
        raw = body["choices"][0]["message"]["content"]
        return ProviderExplanation.model_validate_json(raw) if isinstance(raw, str) else ProviderExplanation.model_validate(raw)

    def metrics(self):
        with self._lock:
            measured = self._usage_calls == self._attempts and self._attempts > 0
            priced = (measured and self.input_price is not None and self.output_price is not None
                      and (not self._cached_tokens or self.cached_input_price is not None))
            cost = (((self._input_tokens - self._cached_tokens) * self.input_price
                     + self._cached_tokens * (self.cached_input_price or 0)
                     + self._output_tokens * self.output_price) / 1_000_000) if priced else None
            return {
                "provider": "configured-http", "model": self.model, "model_version": self.version,
                "prompt_version": self.prompt_version, "completed_calls": self._calls,
                "attempted_calls": self._attempts,
                "average_input_tokens": self._input_tokens / self._usage_calls if measured else None,
                "average_output_tokens": self._output_tokens / self._usage_calls if measured else None,
                "total_input_tokens": self._input_tokens if measured else None,
                "total_output_tokens": self._output_tokens if measured else None,
                "total_cached_input_tokens": self._cached_tokens if measured else None,
                "usage_complete": measured,
                "configured_prices_per_million": {"input": self.input_price, "output": self.output_price,
                                                  "cached_input": self.cached_input_price},
                "measured_cost": cost,
                "cost_per_1000_explanations": cost * 1000 / self._calls if priced else None,
                "pricing_basis": "explicit configured token prices" if priced else "unmeasured",
            }


def strict_response_schema():
    """Require every object key, representing optional values as explicit nulls."""
    schema = ProviderExplanation.model_json_schema()
    def normalize(node):
        if isinstance(node, dict):
            node.pop("default", None)
            if "properties" in node:
                required = node.get("required", [])
                for name, value in node["properties"].items():
                    if name not in required:
                        node["properties"][name] = {"anyOf": [value, {"type": "null"}]}
                node["required"] = list(node["properties"])
                node["additionalProperties"] = False
            for value in node.values():
                normalize(value)
        elif isinstance(node, list):
            for value in node:
                normalize(value)
    normalize(schema)
    return schema


def configured_provider(manifest=None):
    """Use explicit environment overrides over the manifest; no key means offline."""
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("GREENPATH_LLM_API_KEY")
    if not api_key:
        return None
    config = manifest if manifest is not None else json.loads(
        Path(__file__).with_name("provider_manifest.json").read_text(encoding="utf-8"))
    def price(name):
        value = os.environ.get(name)
        return float(value) if value else None
    model = os.environ.get("LLM_MODEL", config["model"])
    temperature = os.environ.get("TEMPERATURE", config["temperature"])
    return HTTPExplanationProvider(
        endpoint=os.environ.get("GREENPATH_LLM_ENDPOINT", config["endpoint"]), model=model,
        model_version=os.environ.get("LLM_MODEL_VERSION", model if "LLM_MODEL" in os.environ else config["model_version"]), api_key=api_key,
        prompt_version=os.environ.get("PROMPT_VERSION", config["prompt_version"]),
        temperature=float(temperature) if temperature not in (None, "") else None,
        max_output_tokens=int(os.environ.get("MAX_OUTPUT_TOKENS", config["max_output_tokens"])),
        token_limit_parameter=os.environ.get("GREENPATH_LLM_TOKEN_LIMIT_PARAMETER", config["token_limit_parameter"]),
        timeout_seconds=float(os.environ.get("GREENPATH_LLM_TIMEOUT_SECONDS", config["timeout_seconds"])),
        input_price_per_million=price("GREENPATH_LLM_INPUT_PRICE_PER_MILLION"),
        output_price_per_million=price("GREENPATH_LLM_OUTPUT_PRICE_PER_MILLION"),
        cached_input_price_per_million=price("GREENPATH_LLM_CACHED_INPUT_PRICE_PER_MILLION"),
    )
