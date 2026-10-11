"""Short promotional copy (banner one-liners and 2-4 line cards) from structured outputs.

Explanations only let a provider reorder approved sentences. Promo copy lets it
write prose, but only inside mechanical limits: no digits or currency, a closed
placeholder set filled by code from the carbon engine, closed claim blocklists,
length/line limits and no other product names. The call-to-action and disclaimer
are attached by code. Any rejection returns a deterministic template.

Copy is generated only when the communication rules already permit engagement;
the provider never decides who is contacted, eligibility, propensity or impact.
"""

import hashlib
import json
import math
import re
from collections import OrderedDict
from decimal import ROUND_HALF_UP, Decimal
from queue import Empty, Queue
from threading import BoundedSemaphore, Lock, Thread
from typing import Literal

from pydantic import AwareDatetime, Field, ValidationError

from greenpath.contracts.impact_detail import ImpactStatus, Model, Product
from greenpath.contracts.product import Recommendation, RecommendationState

from .service import PRODUCT_LABELS

PROMO_TEMPLATE_VERSION = "promo-template-v1"
PROMO_PROMPT_VERSION = "promo-copy-v1"
PROMO_DISCLAIMER = "Subject to status and eligibility. Impact figures are estimates, not guaranteed reductions."
ENGAGE_ACTIONS = frozenset({"SHOW_EDUCATION", "RM_DISCUSSION"})

PromoFormat = Literal["push", "one_liner", "short", "medium"]
# (min lines, max lines, max rendered characters per line, max rendered characters in total)
LIMITS = {"push": (1, 1, 50, 50), "one_liner": (1, 1, 80, 80), "short": (2, 4, 110, 320),
          "medium": (3, 5, 110, 480)}
# Formats with room for the rendered carbon estimate.
IMPACT_FORMATS = frozenset({"short", "medium"})
IMPACT_PLACEHOLDER = "{impact}"

CTA_LABEL = {
    Product.EV_FINANCE: "Explore EV options",
    Product.GREEN_HOME: "See green home options",
    Product.SOLAR_FINANCE: "Explore solar finance",
    Product.PAPERLESS_BANKING: "Go paperless",
}
# Names that identify a product in copy; copy may only name its own product.
PRODUCT_NAMES = {
    Product.EV_FINANCE: ("ev finance",),
    Product.GREEN_HOME: ("green home",),
    Product.SOLAR_FINANCE: ("solar",),
    Product.PAPERLESS_BANKING: ("paperless", "paper-free", "e-statement"),
}
# Closed themes per fitted reason code. They name a topic, never a customer value.
ANGLE_TEXT = {
    "HIGH_FUEL_SPEND": "fuel costs",
    "HIGH_ANNUAL_MILEAGE": "frequent driving",
    "ICE_VEHICLE_OWNER": "moving on from a petrol or diesel car",
    "OLDER_VEHICLE": "replacing an older car",
    "EXISTING_VEHICLE_FINANCE": "spreading the cost of a car",
    "HOMEOWNER": "improving a home you own",
    "MORTGAGE_CUSTOMER": "home improvements alongside a mortgage",
    "NO_EXISTING_SOLAR": "adding solar panels",
    "HIGH_ELECTRICITY_USE": "home electricity use",
    "HIGH_GAS_USE": "home heating",
    "UTILITY_SPEND_RISING": "home energy use",
    "RECENT_HOME_IMPROVEMENT_SPEND": "ongoing home improvements",
    "PAPER_STATEMENTS_ACTIVE": "paper statements",
    "HIGH_DIGITAL_ENGAGEMENT": "using the mobile app",
    "STATED_SUSTAINABILITY_PREFERENCE": "lower-carbon choices",
}

_CLAIMS = {
    "ELIGIBILITY_CLAIM": (r"pre-?approved", r"approv\w*", r"guarantee\w*", r"eligib\w*", r"qualif\w*",
                          r"no credit checks?", r"instant (decision|approval)", r"accepted",
                          r"you('ve| have) been (selected|chosen)", r"free", r"risk-?free"),
    "GREENWASH_CLAIM": (r"carbon[- ]neutral", r"net[- ]zero", r"zero[- ](emissions?|carbon)", r"emissions?[- ]free",
                        r"carbon[- ]free", r"eco[- ]friendly", r"planet[- ]friendly", r"save the planet",
                        r"climate[- ]positive", r"(fully|totally|completely|truly) (green|sustainable)",
                        r"pollution[- ]free", r"clean car"),
    "FINANCIAL_CLAIM": (r"cheap(er|est)?", r"savings", r"save (money|cash|you|on)", r"(lower|cut|reduce|slash) (your )?"
                        r"(bills|costs|payments|repayments|rates?)", r"low(est)? (rates?|interest|apr)", r"apr",
                        r"interest[- ]free", r"pay (nothing|less)", r"cashback", r"discount\w*", r"best rates?"),
    "PERSONAL_DATA_CLAIM": (r"we('ve| have)? (noticed|seen|spotted)", r"we can see", r"your (spending|transactions|purchases|"
                            r"data|account activity|statements show)", r"you('ve| have)? spen[dt]", r"based on your",
                            r"according to (our|your) records", r"you drive a lot", r"your mileage"),
}
CLAIM_PATTERNS = {code: re.compile(r"\b(" + "|".join(patterns) + r")\b", re.IGNORECASE)
                  for code, patterns in _CLAIMS.items()}
DIGITS = re.compile(r"[0-9£$€%¼½¾]")
PLACEHOLDER = re.compile(r"\{[^{}]*\}")
URL = re.compile(r"https?:|www\.|\.(com|co\.uk|org|net|io)\b|@", re.IGNORECASE)
MARKUP = re.compile(r"[<>\[\]`*#|\\{}\r\n\t]")

TEMPLATES = {
    Product.EV_FINANCE: {
        "push": (
            ("ev-p-1", ("Thinking about going electric?",)),
            ("ev-p-2", ("Could your next car be electric?",)),
        ),
        "one_liner": (
            ("ev-ol-1", ("Thinking about going electric? Ask us about EV finance.",)),
            ("ev-ol-2", ("Could your next car be electric? Explore EV finance with us.",)),
        ),
        "short": (
            ("ev-s-impact", ("Thinking about going electric?",
                             "EV finance can help you spread the cost of your next car.",
                             "Switching could cut your driving emissions by {impact}.")),
            ("ev-s-1", ("Would you be interested in EV finance?",
                        "We can help you explore electric options for your next car.")),
        ),
        "medium": (
            ("ev-m-impact", ("Is your next car going to be electric?",
                             "EV finance lets you spread the cost of an electric car over time.",
                             "Switching could cut your driving emissions by {impact}.",
                             "Talk to us about the options that fit how you drive.")),
            ("ev-m-1", ("Is your next car going to be electric?",
                        "EV finance lets you spread the cost of an electric car over time.",
                        "Talk to us about the options that fit how you drive.")),
        ),
    },
    Product.GREEN_HOME: {
        "push": (
            ("gh-p-1", ("Planning energy upgrades at home?",)),
            ("gh-p-2", ("Thinking about a heat pump?",)),
        ),
        "one_liner": (
            ("gh-ol-1", ("Planning energy upgrades at home? Explore Green Home finance.",)),
            ("gh-ol-2", ("Insulation or a heat pump on your list? See Green Home options.",)),
        ),
        "short": (
            ("gh-s-impact", ("Thinking about insulation or a heat pump?",
                             "Green Home finance can help you plan energy upgrades.",
                             "Upgrades like these could cut home emissions by {impact}.")),
            ("gh-s-1", ("Would you be interested in Green Home finance?",
                        "We can help you plan upgrades that make your home more efficient.")),
        ),
        "medium": (
            ("gh-m-impact", ("Ready to make your home more energy efficient?",
                             "Green Home finance can help with insulation, glazing or a heat pump.",
                             "Upgrades like these could cut home emissions by {impact}.",
                             "Talk to us about planning the work that suits your home.")),
            ("gh-m-1", ("Ready to make your home more energy efficient?",
                        "Green Home finance can help with insulation, glazing or a heat pump.",
                        "Talk to us about planning the work that suits your home.")),
        ),
    },
    Product.SOLAR_FINANCE: {
        "push": (
            ("sf-p-1", ("Thinking about solar panels?",)),
            ("sf-p-2", ("Could your roof generate power?",)),
        ),
        "one_liner": (
            ("sf-ol-1", ("Thinking about solar panels? Explore Solar Finance with us.",)),
            ("sf-ol-2", ("Could your roof generate power? Ask us about Solar Finance.",)),
        ),
        "short": (
            ("sf-s-impact", ("Have you considered solar panels for your home?",
                             "Solar Finance can help you spread the cost of an installation.",
                             "Panels could cut your electricity emissions by {impact}.")),
            ("sf-s-1", ("Would you be interested in Solar Finance?",
                        "We can help you explore generating your own electricity at home.")),
        ),
        "medium": (
            ("sf-m-impact", ("Could your roof be working harder?",
                             "Solar Finance can help you spread the cost of a panel installation.",
                             "Panels could cut your electricity emissions by {impact}.",
                             "Talk to us about whether solar suits your home.")),
            ("sf-m-1", ("Could your roof be working harder?",
                        "Solar Finance can help you spread the cost of a panel installation.",
                        "Talk to us about whether solar suits your home.")),
        ),
    },
    Product.PAPERLESS_BANKING: {
        "push": (
            ("pb-p-1", ("Ready to go paperless?",)),
            ("pb-p-2", ("Your statements, in the app.",)),
        ),
        "one_liner": (
            ("pb-ol-1", ("Go paperless and keep every statement to hand in the app.",)),
            ("pb-ol-2", ("Still getting paper statements? Switch to paperless in a few taps.",)),
        ),
        "short": (
            ("pb-s-1", ("Still getting paper statements?",
                        "Switch to paperless and view every statement in the app, any time.")),
            ("pb-s-2", ("Fewer letters through the door.",
                        "Go paperless and keep your statements together in the app.")),
        ),
        "medium": (
            ("pb-m-1", ("Still getting paper statements?",
                        "Go paperless and every statement is in the app the day it is ready.",
                        "You can search, download or share them whenever you need to.",
                        "It takes a few taps to switch.")),
        ),
    },
}


class PromoRequest(Model):
    """Everything the provider sees: closed themes and limits, no customer data."""

    schema_version: Literal["promo-copy-request-v1"] = "promo-copy-request-v1"
    product: Product
    product_label: str
    format: PromoFormat
    channel: Literal["app", "email", "phone", "rm"]
    min_lines: int
    max_lines: int
    max_chars_per_line: int
    max_total_chars: int
    angles: tuple[str, ...]
    impact_placeholder_allowed: bool
    impact_placeholder_rendered_example: str | None
    call_to_action_added_separately: str


class ProviderPromo(Model):
    product: Product
    format: PromoFormat
    lines: tuple[str, ...] = Field(min_length=1)


class PromoCopy(Model):
    status: Literal["AVAILABLE", "PREVIEW", "WITHHELD"]
    withheld_reason: str | None = None
    customer_id: str
    product: Product
    format: PromoFormat
    channel: Literal["app", "email", "phone", "rm"]
    next_action: str
    lines: tuple[str, ...] = ()
    text: str | None = None
    cta_label: str | None = None
    disclaimer: str | None = None
    angles: tuple[str, ...] = ()
    source: Literal["llm", "template"] | None = None
    template_id: str | None = None
    provider_version: str | None = None
    prompt_version: str | None = None
    fallback_reason: str | None = None
    reason_codes: tuple[str, ...] = ()
    impact_value: Decimal | None = None
    units: str | None = None
    decision_id: str | None = None
    data_timestamp: AwareDatetime


def impact_phrase(rec: Recommendation) -> str | None:
    """Rounded carbon-engine reduction, labelled as an estimate; None when it cannot be stated."""
    impact = rec.impact
    if impact.status != ImpactStatus.AVAILABLE or impact.value is None or not impact.units.endswith("/year"):
        return None
    value = impact.value.to_integral_value(rounding=ROUND_HALF_UP)
    if value < 1:
        return None
    return f"around {format(value, ',f')} {impact.units.removesuffix('/year')} a year (estimate)"


def angles(rec: Recommendation) -> tuple[str, ...]:
    from greenpath.models.propensity.reason_codes import REASON_CODE_CATALOGUE

    codes = list(rec.reason_codes)
    if rec.propensity is not None and rec.propensity.source_result is not None:
        codes.extend(str(code) for code in rec.propensity.source_result.reason_codes)
    themes = []
    for code in dict.fromkeys(codes):
        definition = REASON_CODE_CATALOGUE.get(code)
        if code in ANGLE_TEXT and definition is not None and rec.product in definition.applicable_products:
            themes.append(ANGLE_TEXT[code])
    return tuple(dict.fromkeys(themes))


def validate_promo(lines, product: Product, fmt: str, impact: str | None) -> str | None:
    """Return a controlled rejection code, or None when the raw provider lines are acceptable."""
    min_lines, max_lines, _, _ = LIMITS[fmt]
    if not min_lines <= len(lines) <= max_lines or any(not isinstance(line, str) or not line.strip() for line in lines):
        return "LENGTH_REJECTED"
    for line in lines:
        if DIGITS.search(line):
            return "DIGIT_REJECTED"
        for token in PLACEHOLDER.findall(line):
            if token != IMPACT_PLACEHOLDER or impact is None or fmt not in IMPACT_FORMATS:
                return "PLACEHOLDER_REJECTED"
        bare = line.replace(IMPACT_PLACEHOLDER, "")
        if URL.search(bare):
            return "URL_REJECTED"
        if MARKUP.search(bare):
            return "MARKUP_REJECTED"
        for code, pattern in CLAIM_PATTERNS.items():
            if pattern.search(bare):
                return code
        lowered = bare.lower()
        if any(name in lowered for other, names in PRODUCT_NAMES.items() if other != product for name in names):
            return "OTHER_PRODUCT_REJECTED"
    if sum(line.count(IMPACT_PLACEHOLDER) for line in lines) > 1:
        return "PLACEHOLDER_REJECTED"
    rendered = render(lines, impact)
    _, _, per_line, total = LIMITS[fmt]
    if any(len(line) > per_line for line in rendered) or len(" ".join(rendered)) > total:
        return "LENGTH_REJECTED"
    return None


def render(lines, impact: str | None) -> tuple[str, ...]:
    return tuple(" ".join(line.split()).replace(IMPACT_PLACEHOLDER, impact or "") for line in lines)


def template(rec: Recommendation, fmt: str, impact: str | None) -> tuple[str, tuple[str, ...]]:
    variants = TEMPLATES[rec.product][fmt]
    usable = [v for v in variants if IMPACT_PLACEHOLDER in "".join(v[1])] if impact else []
    usable = usable or [v for v in variants if IMPACT_PLACEHOLDER not in "".join(v[1])]
    index = int(hashlib.sha256(f"{rec.customer_id}|{rec.product}|{fmt}".encode()).hexdigest(), 16) % len(usable)
    return usable[index]


class PromoService:
    """Template by default; an injected provider writes copy that must pass `validate_promo`."""

    def __init__(self, provider=None, *, timeout_seconds: float | None = None, max_inflight: int = 2,
                 cache_size: int = 512):
        if timeout_seconds is None:
            timeout_seconds = getattr(provider, "timeout_seconds", 2.0)
        if isinstance(timeout_seconds, bool) or not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive and finite")
        self.provider = provider
        self.timeout_seconds = timeout_seconds
        self.provider_version = getattr(provider, "version", None)
        self.prompt_version = getattr(provider, "promo_prompt_version", PROMO_PROMPT_VERSION)
        self.cache_size = cache_size
        self._cache = OrderedDict()
        self._lock = Lock()
        self._slots = BoundedSemaphore(max_inflight)
        self._requests = self._hits = self._provider_calls = self._accepted = 0
        self._fallbacks: dict[str, int] = {}

    def generate(self, recommendation: Recommendation, action: str, action_reason: str, *,
                 fmt: str = "one_liner", channel: str = "app", preview: bool = False) -> PromoCopy:
        """Copy for an engage action; `preview` also shows a supported decision blocked only by contact rules."""
        if fmt not in LIMITS:
            raise ValueError(f"Unsupported promo format: {fmt}")
        rec = Recommendation.model_validate(recommendation.model_dump(mode="python"))
        common = {"customer_id": rec.customer_id, "product": rec.product, "format": fmt, "channel": channel,
                  "next_action": action, "reason_codes": rec.reason_codes, "decision_id": rec.decision_id,
                  "data_timestamp": rec.feature_cutoff}
        if action not in ENGAGE_ACTIONS:
            # A preview is never sendable, and never drafts copy for a decision that does not support the product.
            if not preview or rec.state != RecommendationState.RECOMMEND:
                return PromoCopy(status="WITHHELD", withheld_reason=action_reason, **common)
            return self._copy(rec, fmt, channel, common).model_copy(
                update={"status": "PREVIEW", "withheld_reason": action_reason})
        return self._copy(rec, fmt, channel, common)

    def _copy(self, rec, fmt, channel, common) -> PromoCopy:
        payload = rec.model_dump(mode="json")
        for key in ("timestamp", "decision_id", "provenance"):
            payload.pop(key, None)
        payload["impact"].pop("timestamp", None)
        key = hashlib.sha256(json.dumps([payload, fmt, channel, self.prompt_version, self.provider_version],
                                        sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        with self._lock:
            self._requests += 1
            cached = self._cache.get(key)
            if cached is not None:
                self._hits += 1
                self._cache.move_to_end(key)
                return cached.model_copy(update={"decision_id": rec.decision_id, "next_action": common["next_action"]})
        result = self._generate(rec, fmt, channel, common)
        with self._lock:
            if result.source == "llm":
                self._accepted += 1
            elif result.fallback_reason:
                self._fallbacks[result.fallback_reason] = self._fallbacks.get(result.fallback_reason, 0) + 1
            if self.cache_size and result.fallback_reason in {None, "PROVIDER_NOT_CONFIGURED"}:
                self._cache[key] = result
                while len(self._cache) > self.cache_size:
                    self._cache.popitem(last=False)
        return result

    def metrics(self) -> dict:
        with self._lock:
            return {"requests": self._requests, "cache_hits": self._hits, "provider_attempts": self._provider_calls,
                    "provider_accepted": self._accepted, "fallbacks": dict(self._fallbacks),
                    "prompt_version": self.prompt_version,
                    "model_version": self.provider_version or PROMO_TEMPLATE_VERSION}

    def _generate(self, rec, fmt, channel, common) -> PromoCopy:
        impact = impact_phrase(rec)
        themes = angles(rec)

        def result(lines, source, fallback_reason=None, template_id=None):
            rendered = render(lines, impact)
            used_impact = any(IMPACT_PLACEHOLDER in line for line in lines)
            return PromoCopy(
                status="AVAILABLE", lines=rendered, text=" ".join(rendered), cta_label=CTA_LABEL[rec.product],
                disclaimer=PROMO_DISCLAIMER, angles=themes, source=source, template_id=template_id,
                provider_version=self.provider_version if source == "llm" else PROMO_TEMPLATE_VERSION,
                prompt_version=self.prompt_version if source == "llm" else None, fallback_reason=fallback_reason,
                impact_value=rec.impact.value if used_impact else None,
                units=rec.impact.units if used_impact else None, **common)

        def fallback(reason):
            template_id, lines = template(rec, fmt, impact if fmt in IMPACT_FORMATS else None)
            return result(lines, "template", reason, template_id)

        if self.provider is None:
            return fallback("PROVIDER_NOT_CONFIGURED")
        if not isinstance(self.provider_version, str) or not self.provider_version:
            return fallback("PROVIDER_VERSION_NOT_CONFIGURED")
        min_lines, max_lines, per_line, total = LIMITS[fmt]
        allowed = impact is not None and fmt in IMPACT_FORMATS
        request = PromoRequest(
            product=rec.product, product_label=PRODUCT_LABELS[rec.product], format=fmt, channel=channel,
            min_lines=min_lines, max_lines=max_lines, max_chars_per_line=per_line, max_total_chars=total,
            angles=themes, impact_placeholder_allowed=allowed,
            impact_placeholder_rendered_example=impact if allowed else None,
            call_to_action_added_separately=CTA_LABEL[rec.product],
        )
        if not self._slots.acquire(blocking=False):
            return fallback("PROVIDER_BUSY")
        results = Queue(maxsize=1)

        def invoke():
            with self._lock:
                self._provider_calls += 1
            try:
                results.put((True, self.provider.generate_promo(request, timeout_seconds=self.timeout_seconds)))
            except Exception:
                results.put((False, None))
            finally:
                self._slots.release()

        try:
            Thread(target=invoke, daemon=True, name="greenpath-promo").start()
        except Exception:
            self._slots.release()
            return fallback("PROVIDER_ERROR")
        try:
            success, raw = results.get(timeout=self.timeout_seconds)
        except Empty:
            return fallback("PROVIDER_TIMEOUT")
        if not success:
            return fallback("PROVIDER_ERROR")
        try:
            if isinstance(raw, ProviderPromo):
                output = ProviderPromo.model_validate(raw.model_dump(mode="python"))
            elif isinstance(raw, str):
                output = ProviderPromo.model_validate_json(raw)
            else:
                output = ProviderPromo.model_validate(raw)
        except (ValidationError, TypeError, ValueError):
            return fallback("SCHEMA_REJECTED")
        if output.product != rec.product or output.format != fmt:
            return fallback("CLAIMS_REJECTED")
        rejection = validate_promo(output.lines, rec.product, fmt, impact if allowed else None)
        if rejection is not None:
            return fallback(rejection)
        return result(output.lines, "llm")
