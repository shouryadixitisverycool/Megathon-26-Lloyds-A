"""Optional explicitly configured HTTP adapter for structured sentence selection.

The endpoint implements a chat-completions-shaped JSON protocol. No credentials
or network access are needed for the default deterministic explanation service.
"""

import json
import math
import os
from threading import Lock

import httpx

from .ports import ProviderExplanation


class HTTPExplanationProvider:
    def __init__(self, *, endpoint, model, model_version, api_key, prompt_version="grounded-selection-v1",
                 temperature=0.0, max_output_tokens=800, transport=None,
                 input_price_per_million=None, output_price_per_million=None):
        if not endpoint or not model or not model_version or not api_key:
            raise ValueError("HTTP explanations require endpoint, exact model, model version and API key")
        for price in (input_price_per_million, output_price_per_million):
            if price is not None and (not math.isfinite(price) or price < 0):
                raise ValueError("Token pricing must be non-negative and finite")
        if not math.isfinite(temperature) or not 0 <= temperature <= 2:
            raise ValueError("Temperature must be between zero and two")
        if isinstance(max_output_tokens, bool) or not isinstance(max_output_tokens, int) or max_output_tokens < 1:
            raise ValueError("max_output_tokens must be a positive integer")
        self.endpoint, self.model, self.version, self.api_key = endpoint, model, model_version, api_key
        self.prompt_version, self.temperature, self.max_output_tokens = prompt_version, temperature, max_output_tokens
        self.transport = transport
        self.input_price, self.output_price = input_price_per_million, output_price_per_million
        self._lock = Lock()
        self._calls = self._input_tokens = self._output_tokens = self._usage_calls = 0

    def generate(self, request, *, timeout_seconds):
        payload = {
            "model": self.model, "temperature": self.temperature, "max_tokens": self.max_output_tokens,
            "messages": [
                {"role": "system", "content": "Return the exact structured claims and every required sentence ID once. You may only reorder approved sentences. Do not invent facts, numbers, eligibility or new reasons."},
                {"role": "user", "content": request.model_dump_json()},
            ],
            "response_format": {"type": "json_schema", "json_schema": {
                "name": "grounded_explanation", "strict": True, "schema": ProviderExplanation.model_json_schema(),
            }},
        }
        # HTTP timeout and the service's bounded caller deadline both apply.
        with httpx.Client(timeout=httpx.Timeout(timeout_seconds), transport=self.transport) as client:
            response = client.post(self.endpoint, headers={"Authorization": f"Bearer {self.api_key}"}, json=payload)
            response.raise_for_status()
            body = response.json()
        raw = body["choices"][0]["message"]["content"]
        usage = body.get("usage", {})
        input_tokens, output_tokens = usage.get("prompt_tokens"), usage.get("completion_tokens")
        with self._lock:
            self._calls += 1
            if (isinstance(input_tokens, int) and not isinstance(input_tokens, bool) and input_tokens >= 0
                    and isinstance(output_tokens, int) and not isinstance(output_tokens, bool) and output_tokens >= 0):
                self._usage_calls += 1
                self._input_tokens += input_tokens
                self._output_tokens += output_tokens
        return ProviderExplanation.model_validate_json(raw) if isinstance(raw, str) else ProviderExplanation.model_validate(raw)

    def metrics(self):
        with self._lock:
            measured = self._usage_calls == self._calls and self._calls > 0
            priced = measured and self.input_price is not None and self.output_price is not None
            cost = ((self._input_tokens * self.input_price + self._output_tokens * self.output_price) / 1_000_000) if priced else None
            return {
                "provider": "configured-http", "model": self.model, "model_version": self.version,
                "prompt_version": self.prompt_version, "completed_calls": self._calls,
                "average_input_tokens": self._input_tokens / self._usage_calls if measured else None,
                "average_output_tokens": self._output_tokens / self._usage_calls if measured else None,
                "measured_cost": cost,
                "cost_per_1000_explanations": cost * 1000 / self._calls if priced else None,
                "pricing_basis": "explicit configured token prices" if priced else "unmeasured",
            }


def configured_provider():
    """No key means offline mode; partial keyed configuration is rejected clearly."""
    api_key = os.environ.get("GREENPATH_LLM_API_KEY")
    if not api_key:
        return None
    def price(name):
        value = os.environ.get(name)
        return float(value) if value else None
    return HTTPExplanationProvider(
        endpoint=os.environ.get("GREENPATH_LLM_ENDPOINT"), model=os.environ.get("LLM_MODEL"),
        model_version=os.environ.get("LLM_MODEL_VERSION"), api_key=api_key,
        prompt_version=os.environ.get("PROMPT_VERSION", "grounded-selection-v1"),
        temperature=float(os.environ.get("TEMPERATURE", "0")),
        max_output_tokens=int(os.environ.get("MAX_OUTPUT_TOKENS", "800")),
        input_price_per_million=price("GREENPATH_LLM_INPUT_PRICE_PER_MILLION"),
        output_price_per_million=price("GREENPATH_LLM_OUTPUT_PRICE_PER_MILLION"),
    )
