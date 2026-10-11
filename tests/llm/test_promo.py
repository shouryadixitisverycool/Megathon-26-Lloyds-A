"""Promo copy: engage-only gating, template fallback and mechanical claim checks."""

import json
import threading

import httpx
import pytest

from greenpath.contracts.product import RecommendationState
from greenpath.impact import Product
from greenpath.llm.evaluation import synthetic_recommendation
from greenpath.llm.http_provider import HTTPExplanationProvider
from greenpath.llm.promo import (
    CTA_LABEL, LIMITS, PROMO_DISCLAIMER, TEMPLATES, PromoRequest, PromoService, impact_phrase, validate_promo,
)


class Writer:
    version = "fixture-writer-v1"

    def __init__(self, lines, product=None, fmt=None):
        self.lines, self.product, self.fmt, self.requests = lines, product, fmt, []

    def generate_promo(self, request, *, timeout_seconds):
        self.requests.append(request)
        return {"product": (self.product or request.product).value, "format": self.fmt or request.format,
                "lines": list(self.lines)}


def generate(provider=None, *, product=Product.EV_FINANCE, fmt="one_liner", action="SHOW_EDUCATION", rec=None):
    rec = rec or synthetic_recommendation(product=product)
    return PromoService(provider, timeout_seconds=.5).generate(rec, action, "rule reason", fmt=fmt)


@pytest.mark.parametrize("product", list(Product))
@pytest.mark.parametrize("fmt", list(LIMITS))
def test_no_key_template_for_every_product_and_format(product, fmt):
    result = generate(product=product, fmt=fmt)
    assert result.status == "AVAILABLE" and result.source == "template"
    assert result.fallback_reason == "PROVIDER_NOT_CONFIGURED"
    assert result.cta_label == CTA_LABEL[product] and result.disclaimer == PROMO_DISCLAIMER
    min_lines, max_lines, per_line, total = LIMITS[fmt]
    assert min_lines <= len(result.lines) <= max_lines
    assert all(len(line) <= per_line for line in result.lines) and len(result.text) <= total
    assert "{" not in result.text


@pytest.mark.parametrize("product", list(Product))
@pytest.mark.parametrize("fmt", list(LIMITS))
def test_every_template_passes_its_own_validator(product, fmt):
    rec = synthetic_recommendation(product=product)
    impact = impact_phrase(rec) if fmt == "short" else None
    for _, lines in TEMPLATES[product][fmt]:
        if "{impact}" in "".join(lines) and impact is None:
            continue
        assert validate_promo(lines, product, fmt, impact) is None


def test_impact_is_rendered_by_code_from_the_carbon_engine():
    rec = synthetic_recommendation()
    result = generate(fmt="short", rec=rec)
    assert result.template_id == "ev-s-impact"
    assert impact_phrase(rec) in result.text and "(estimate)" in result.text
    assert result.impact_value == rec.impact.value and result.units == rec.impact.units
    unavailable = generate(fmt="short", rec=synthetic_recommendation(available=False))
    assert unavailable.impact_value is None and "kg" not in unavailable.text
    zero = synthetic_recommendation(zero=True)
    assert impact_phrase(zero) is None


@pytest.mark.parametrize("action", ["SUPPRESS", "DEFER", "REQUEST_CONSENT", "REQUEST_REVIEW", "REQUEST_INFORMATION"])
def test_non_engage_actions_are_withheld_without_calling_the_provider(action):
    writer = Writer(("Would you be interested in EV finance?",))
    result = generate(writer, action=action)
    assert result.status == "WITHHELD" and result.withheld_reason == "rule reason"
    assert result.lines == () and result.text is None and not writer.requests


def test_valid_provider_copy_is_accepted_with_code_attached_cta_and_disclaimer():
    writer = Writer(("Would you be interested in EV finance for your next car?",))
    result = generate(writer)
    assert result.source == "llm" and result.fallback_reason is None
    assert result.lines == ("Would you be interested in EV finance for your next car?",)
    assert result.cta_label == "Explore EV options" and result.disclaimer == PROMO_DISCLAIMER
    assert result.provider_version == "fixture-writer-v1"


def test_provider_may_use_the_impact_placeholder_only_in_short_copy_with_available_impact():
    lines = ("Thinking about going electric?", "An EV could cut your driving emissions by {impact}.")
    rec = synthetic_recommendation()
    accepted = generate(Writer(lines), fmt="short", rec=rec)
    assert accepted.source == "llm" and impact_phrase(rec) in accepted.lines[1]
    unavailable = generate(Writer(lines), fmt="short", rec=synthetic_recommendation(available=False))
    assert unavailable.fallback_reason == "PLACEHOLDER_REJECTED"
    one_liner = generate(Writer(("Cut your driving emissions by {impact}.",)), rec=rec)
    assert one_liner.fallback_reason == "PLACEHOLDER_REJECTED"


@pytest.mark.parametrize("line,reason", [
    ("Cut emissions by over a tonne with EV finance at 3.9%!", "DIGIT_REJECTED"),
    ("Borrow up to £30k with EV finance.", "DIGIT_REJECTED"),
    ("You're pre-approved for EV finance today.", "ELIGIBILITY_CLAIM"),
    ("Guaranteed EV finance for drivers like you.", "ELIGIBILITY_CLAIM"),
    ("See if you qualify for EV finance.", "ELIGIBILITY_CLAIM"),
    ("EV finance with no credit check.", "ELIGIBILITY_CLAIM"),
    ("Go carbon neutral with EV finance.", "GREENWASH_CLAIM"),
    ("Drive net zero with EV finance.", "GREENWASH_CLAIM"),
    ("An eco-friendly car is closer than you think.", "GREENWASH_CLAIM"),
    ("Save money on fuel with EV finance.", "FINANCIAL_CLAIM"),
    ("EV finance could lower your bills.", "FINANCIAL_CLAIM"),
    ("Electric is cheaper to run. Ask about EV finance.", "FINANCIAL_CLAIM"),
    ("We noticed you spend a lot on fuel. Try EV finance.", "PERSONAL_DATA_CLAIM"),
    ("Based on your transactions, EV finance could suit you.", "PERSONAL_DATA_CLAIM"),
    ("Explore EV finance at www.example.com", "URL_REJECTED"),
    ("<b>EV finance</b> is here", "MARKUP_REJECTED"),
    ("EV finance and Solar Finance, together.", "OTHER_PRODUCT_REJECTED"),
    ("Go paperless and get EV finance.", "OTHER_PRODUCT_REJECTED"),
    ("Thinking about EV finance? {customer_name}, ask us today.", "PLACEHOLDER_REJECTED"),
    ("Thinking about going electric? " * 4, "LENGTH_REJECTED"),
])
def test_unsafe_provider_copy_falls_back_to_template(line, reason):
    result = generate(Writer((line,)))
    assert result.source == "template" and result.fallback_reason == reason
    assert line not in result.text


def test_line_count_schema_and_echo_failures_fall_back():
    assert generate(Writer(("One.", "Two."))).fallback_reason == "LENGTH_REJECTED"
    assert generate(Writer(("Only one line.",)), fmt="short").fallback_reason == "LENGTH_REJECTED"
    assert generate(Writer(("a", "b", "c", "d", "e")), fmt="short").fallback_reason == "LENGTH_REJECTED"
    assert generate(Writer(("Ask about EV finance.",), product=Product.GREEN_HOME)).fallback_reason == "CLAIMS_REJECTED"
    assert generate(Writer(("Ask about EV finance.",), fmt="short")).fallback_reason == "CLAIMS_REJECTED"

    class Broken(Writer):
        def generate_promo(self, request, *, timeout_seconds):
            return {"product": request.product.value, "format": request.format, "lines": ["ok"], "extra": 1}
    assert generate(Broken(())).fallback_reason == "SCHEMA_REJECTED"

    class Failing(Writer):
        def generate_promo(self, request, *, timeout_seconds):
            raise RuntimeError("boom")
    assert generate(Failing(())).fallback_reason == "PROVIDER_ERROR"


def test_timeout_and_busy_fall_back_and_are_not_cached():
    release = threading.Event()

    class Slow(Writer):
        def generate_promo(self, request, *, timeout_seconds):
            release.wait(5)
            return super().generate_promo(request, timeout_seconds=timeout_seconds)

    service = PromoService(Slow(("Would you be interested in EV finance?",)), timeout_seconds=.05, max_inflight=1)
    rec = synthetic_recommendation()
    assert service.generate(rec, "SHOW_EDUCATION", "ok").fallback_reason == "PROVIDER_TIMEOUT"
    assert service.generate(rec, "SHOW_EDUCATION", "ok").fallback_reason == "PROVIDER_BUSY"
    release.set()
    assert service.metrics()["cache_hits"] == 0


def test_request_carries_no_customer_identifiers_or_amounts():
    writer = Writer(("Would you be interested in EV finance?",))
    generate(writer, rec=synthetic_recommendation(malicious_field="evidence"))
    request = writer.requests[0]
    assert isinstance(request, PromoRequest)
    dumped = request.model_dump_json()
    assert "evaluation-synthetic" not in dumped and "MERCHANT" not in dumped
    assert not any(ch.isdigit() for ch in json.dumps(request.angles))


def test_successful_copy_is_cached():
    writer = Writer(("Would you be interested in EV finance?",))
    service = PromoService(writer, timeout_seconds=.5)
    rec = synthetic_recommendation()
    first = service.generate(rec, "SHOW_EDUCATION", "ok")
    assert service.generate(rec, "SHOW_EDUCATION", "ok") == first
    assert len(writer.requests) == 1 and service.metrics()["cache_hits"] == 1


def test_http_provider_sends_promo_schema_and_parses_lines():
    def handle(request):
        payload = json.loads(request.content)
        assert payload["response_format"]["json_schema"]["name"] == "promo_copy"
        assert payload["response_format"]["json_schema"]["strict"]
        facts = PromoRequest.model_validate_json(payload["messages"][1]["content"])
        content = {"product": facts.product.value, "format": facts.format,
                   "lines": ["Would you be interested in EV finance?"]}
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(content)}}],
                                         "usage": {"prompt_tokens": 50, "completion_tokens": 10}})
    provider = HTTPExplanationProvider(endpoint="https://example.test/completions", model="pinned-model",
                                       model_version="pinned-model-v1", api_key="fixture-secret",
                                       transport=httpx.MockTransport(handle))
    result = PromoService(provider, timeout_seconds=.5).generate(synthetic_recommendation(), "RM_DISCUSSION", "ok")
    assert result.source == "llm" and result.prompt_version == "promo-copy-v1"
    assert provider.metrics()["completed_calls"] == 1


def test_state_is_not_reinterpreted_by_the_promo_service():
    # Gating is the communication rules' job; a non-recommend state never reaches an engage action there.
    rec = synthetic_recommendation(state=RecommendationState.SUPPRESSED)
    assert PromoService().generate(rec, "SUPPRESS", "Decision does not support engagement").status == "WITHHELD"


def test_fixed_promo_evaluation_passes_with_no_unsafe_copy_accepted():
    from greenpath.llm.promo_evaluation import run_evaluation

    summary = run_evaluation()["summary"]
    assert summary["passed"] == summary["total"] >= 100
    assert summary["unsafe_accepted"] == 0 and summary["safe_acceptance_rate"] == 1


def test_preview_shows_copy_only_for_supported_decisions_blocked_by_contact_rules():
    rec = synthetic_recommendation()
    preview = PromoService().generate(rec, "REQUEST_CONSENT", "No consent", fmt="medium", preview=True)
    assert preview.status == "PREVIEW" and preview.withheld_reason == "No consent" and preview.lines
    excluded = synthetic_recommendation(state=RecommendationState.DO_NOT_RECOMMEND)
    blocked = PromoService().generate(excluded, "SUPPRESS", "Decision does not support engagement", preview=True)
    assert blocked.status == "WITHHELD" and not blocked.lines
    sendable = PromoService().generate(rec, "SHOW_EDUCATION", "ok", preview=True)
    assert sendable.status == "AVAILABLE"
