"""Explain validated recommendations without accepting unsupported prose."""

import math
import hashlib
import json
import time
from collections import OrderedDict
import re
from queue import Empty, Queue
from threading import BoundedSemaphore, Lock, Thread

from pydantic import ValidationError

from greenpath.contracts.product import (
    ELIGIBILITY_DISCLAIMER, Explanation, Recommendation, RecommendationState,
)
from greenpath.contracts.impact_detail import ImpactStatus, Product

from .ports import ApprovedSentence, ExplanationProvider, ExplanationRequest, ProviderExplanation
from .schema import StructuredExplanation

TEMPLATE_VERSION = "grounded-template-v2"
PRODUCT_LABELS = {
    Product.EV_FINANCE: "EV Finance",
    Product.GREEN_HOME: "Green Home",
    Product.SOLAR_FINANCE: "Solar Finance",
    Product.PAPERLESS_BANKING: "Paperless Banking",
}
STATE_TEXT = {
    RecommendationState.RECOMMEND: "The available evidence supports a product relevance recommendation.",
    RecommendationState.DO_NOT_RECOMMEND: "The available evidence does not support a product relevance recommendation.",
    RecommendationState.INSUFFICIENT_INFORMATION: "There is insufficient reliable information to decide product relevance.",
    RecommendationState.CONFLICT_REQUIRES_REVIEW: "Conflicting evidence requires review before a product relevance decision.",
    RecommendationState.NOT_APPLICABLE: "The product relevance opportunity is not applicable to the current evidence.",
    RecommendationState.SUPPRESSED: "Contact about this product is suppressed by the relevance rules.",
}
# Closed vocabulary. Input issue messages, evidence text, version strings and
# provider/propensity reason strings are never copied into the provider request.
REASON_TEXT = {
    "MARKETING_CONSENT_WITHDRAWN": "Marketing contact consent does not permit this recommendation.",
    "ALREADY_ADOPTED": "The evidence indicates the product or supported activity is already adopted.",
    "EVIDENCE_CONFLICT": "The relevance evidence contains an unresolved conflict that requires review.",
    "OUT_OF_DISTRIBUTION": "The evidence falls outside the supported model scope.",
    "MISSING_EVIDENCE": "Required relevance evidence is missing.",
    "STALE_EVIDENCE": "Required relevance evidence is stale.",
    "FUTURE_EVIDENCE": "Required evidence was observed after the permitted cutoff.",
    "FUTURE_FEATURE_CUTOFF": "The feature cutoff is after the decision time; relevance cannot be determined.",
    "TRUST_LIMITATION": "A high-severity evidence quality limitation requires review before product relevance can be determined.",
    "VEHICLE_REQUIRED": "The relevance evidence does not support vehicle ownership for this opportunity.",
    "FUEL_UNSUPPORTED": "The relevance evidence identifies a fuel outside the supported EV comparison.",
    "HOME_REQUIRED": "The relevance evidence does not support home ownership for this opportunity.",
    "ROOF_UNAVAILABLE": "The relevance evidence records no available roof for this solar opportunity.",
    "NO_PAPER_STATEMENTS": "The relevance evidence records no paper statements to replace.",
    "PAPERLESS_CONSENT_WITHDRAWN": "The relevance evidence records no consent to switch to paperless statements.",
    "INTEREST_NOT_SUPPORTED": "The relevance evidence does not support interest in this opportunity.",
    "CONFIDENCE_BELOW_MINIMUM": "Validated model confidence is below the supported reliability level, so product relevance is withheld.",
    "PROPENSITY_UNAVAILABLE": "A usable product propensity estimate is unavailable.",
    "PROPENSITY_BELOW_THRESHOLD": "The synthetic propensity is below the demo relevance threshold.",
    "RELEVANCE_SUPPORTED": "The product-specific relevance signals support the opportunity.",
    "PROPENSITY_THRESHOLD_MET": "The synthetic propensity meets the demo relevance threshold.",
}


class ExplanationService:
    """Default to deterministic text; optionally validate provider composition.

    A bounded number of daemon calls prevents timed-out providers from creating
    unbounded workers. An abandoned call occupies a slot until it returns.
    """

    def __init__(self, provider: ExplanationProvider | None = None, *,
                 timeout_seconds: float | None = None, provider_version: str | None = None,
                 max_inflight: int = 2, prompt_version: str = "grounded-selection-v1",
                 locale: str = "en", cache_size: int = 512):
        if timeout_seconds is None:
            timeout_seconds = getattr(provider, "timeout_seconds", 2.0)
        if isinstance(timeout_seconds, bool) or not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive and finite")
        if isinstance(max_inflight, bool) or not isinstance(max_inflight, int) or max_inflight < 1:
            raise ValueError("max_inflight must be a positive integer")
        if isinstance(cache_size, bool) or not isinstance(cache_size, int) or cache_size < 0:
            raise ValueError("cache_size must be a non-negative integer")
        self.prompt_version = getattr(provider, "prompt_version", prompt_version)
        self.locale = locale
        self.cache_size = cache_size
        self._cache = OrderedDict()
        self._cache_lock = Lock()
        self._requests = self._hits = self._misses = self._provider_calls = self._provider_completed = 0
        self._latency_ms = self._provider_latency_ms = 0.0
        self.provider = provider
        self.timeout_seconds = timeout_seconds
        self.provider_version = provider_version if provider_version is not None else getattr(provider, "version", None)
        self._slots = BoundedSemaphore(max_inflight)

    def explain(self, recommendation: Recommendation) -> Explanation:
        started = time.perf_counter()
        recommendation = Recommendation.model_validate(recommendation.model_dump(mode="python"))
        payload = recommendation.model_dump(mode="json")
        # Decision/impact wall-clock generation times are not evidence changes.
        payload.pop("timestamp", None)
        payload["impact"].pop("timestamp", None)
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        key = hashlib.sha256(json.dumps([canonical, self.prompt_version, self.provider_version or TEMPLATE_VERSION,
                                        self.locale], separators=(",", ":")).encode()).hexdigest()
        with self._cache_lock:
            self._requests += 1
            cached = self._cache.get(key)
            if cached is not None:
                self._hits += 1
                self._cache.move_to_end(key)
                self._latency_ms += (time.perf_counter() - started) * 1000
                return cached
            self._misses += 1
        output = self._explain_uncached(recommendation)
        with self._cache_lock:
            self._latency_ms += (time.perf_counter() - started) * 1000
            # Transient failures must be retried and preserve worker-cap behavior.
            if self.cache_size and output.fallback_reason in {None, "PROVIDER_NOT_CONFIGURED"}:
                self._cache[key] = output
                while len(self._cache) > self.cache_size:
                    self._cache.popitem(last=False)
        return output

    def metrics(self) -> dict:
        with self._cache_lock:
            result = {"requests": self._requests, "cache_hits": self._hits, "cache_misses": self._misses,
                      "cache_hit_rate": self._hits / self._requests if self._requests else 0.0,
                      "average_latency_ms": self._latency_ms / self._requests if self._requests else None,
                      "provider_attempts": self._provider_calls,
                      "provider_completed": self._provider_completed,
                      "live_provider_latency_ms": self._provider_latency_ms / self._provider_completed if self._provider_completed else None,
                      "prompt_version": self.prompt_version, "model_version": self.provider_version or TEMPLATE_VERSION,
                      "locale": self.locale, "offline_cost": 0 if self.provider is None else None,
                      "live_provider_cost": None}
        if self.provider is not None and hasattr(self.provider, "metrics"):
            measured = self.provider.metrics()
            result["provider_measurements"] = measured
            result["live_provider_cost"] = measured.get("measured_cost")
        return result

    def _explain_uncached(self, recommendation: Recommendation) -> Explanation:
        # Revalidate even a model_construct/model_copy input at this boundary.
        recommendation = Recommendation.model_validate(recommendation.model_dump(mode="python"))
        if recommendation.impact.product != recommendation.product:
            raise ValueError("Impact product must match the recommendation")
        if recommendation.propensity is not None and recommendation.propensity.product != recommendation.product:
            raise ValueError("Propensity product must match the recommendation")
        sentences = self._sentences(recommendation)
        fallback = lambda reason: self._result(recommendation, sentences, "template", TEMPLATE_VERSION, reason)
        if self.provider is None:
            return fallback("PROVIDER_NOT_CONFIGURED")
        if not isinstance(self.provider_version, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}", self.provider_version):
            return fallback("PROVIDER_VERSION_NOT_CONFIGURED")
        if any(code not in REASON_TEXT for code in recommendation.reason_codes):
            return fallback("UNRECOGNIZED_REASON_CODE")
        request = ExplanationRequest(
            product=recommendation.product, state=recommendation.state,
            reason_codes=recommendation.reason_codes, impact_value=recommendation.impact.value,
            units=recommendation.impact.units, eligibility_disclaimer=ELIGIBILITY_DISCLAIMER,
            approved_sentences=sentences,
            required_sentence_ids=tuple(item.sentence_id for item in sentences),
        )
        if not self._slots.acquire(blocking=False):
            return fallback("PROVIDER_BUSY")
        result_queue = Queue(maxsize=1)

        def invoke():
            provider_started = time.perf_counter()
            with self._cache_lock:
                self._provider_calls += 1
            try:
                result_queue.put((True, self.provider.generate(request, timeout_seconds=self.timeout_seconds)))
            except Exception:
                result_queue.put((False, None))
            finally:
                with self._cache_lock:
                    self._provider_latency_ms += (time.perf_counter() - provider_started) * 1000
                    self._provider_completed += 1
                self._slots.release()

        try:
            Thread(target=invoke, daemon=True, name="greenpath-explanation").start()
        except Exception:
            self._slots.release()
            return fallback("PROVIDER_ERROR")
        try:
            success, raw = result_queue.get(timeout=self.timeout_seconds)
        except Empty:
            return fallback("PROVIDER_TIMEOUT")
        if not success:
            return fallback("PROVIDER_ERROR")
        try:
            if isinstance(raw, ProviderExplanation):
                output = ProviderExplanation.model_validate(raw.model_dump(mode="python"))
            elif isinstance(raw, str):
                output = ProviderExplanation.model_validate_json(raw)
            else:
                output = ProviderExplanation.model_validate(raw)
        except (ValidationError, TypeError, ValueError):
            return fallback("SCHEMA_REJECTED")
        if any(getattr(output, field) != getattr(request, field) for field in (
            "product", "state", "reason_codes", "impact_value", "units", "eligibility_disclaimer",
        )):
            return fallback("CLAIMS_REJECTED")
        if len(output.sentence_ids) != len(request.required_sentence_ids) or set(output.sentence_ids) != set(request.required_sentence_ids):
            return fallback("SENTENCES_REJECTED")
        by_id = {item.sentence_id: item for item in sentences}
        selected = tuple(by_id[key] for key in output.sentence_ids)
        return self._result(recommendation, selected, "llm", self.provider_version, None)

    @staticmethod
    def _sentences(rec: Recommendation) -> tuple[ApprovedSentence, ...]:
        def sentence(key, text):
            return ApprovedSentence(sentence_id=key, text=text)
        items = [sentence("decision", f"{PRODUCT_LABELS[rec.product]}: {STATE_TEXT[rec.state]}")]
        known_codes = tuple(dict.fromkeys(code for code in rec.reason_codes if code in REASON_TEXT))
        items.extend(sentence(f"reason:{code}", REASON_TEXT[code]) for code in known_codes)
        if any(code not in REASON_TEXT for code in rec.reason_codes):
            items.append(sentence("reason:unrecognized", "An additional reason is recorded in the structured decision; its text is not approved for explanation."))
        propensity = rec.propensity
        if propensity is not None and propensity.source_result is not None:
            source = propensity.source_result
            # Enum reasons come from the canonical fitted reason catalogue.
            # Provider text and arbitrary reason strings are never trusted here.
            from greenpath.models.propensity.reason_codes import REASON_CODE_CATALOGUE
            for code in dict.fromkeys(source.reason_codes):
                definition = REASON_CODE_CATALOGUE.get(code)
                if definition is not None and rec.product in definition.applicable_products:
                    items.append(sentence(f"model-reason:{code.value}", definition.rm_wording))
            if propensity.probability is not None and propensity.in_model_population:
                items.append(sentence("propensity", f"The calibrated synthetic-data take-up probability is {format(propensity.probability, 'f')}. This estimates product interest, not credit eligibility."))
            if propensity.confidence_validated and propensity.confidence is not None:
                items.append(sentence("confidence", f"Validated model confidence is {format(propensity.confidence, 'f')}. This describes prediction reliability and is separate from evidence Trust."))
            else:
                items.append(sentence("confidence", "Model confidence is withheld because held-out reliability validation does not support displaying it."))
        else:
            if propensity is not None:
                # Fixture reasons: only applicable catalogue wording; unvalidated numbers stay out.
                from greenpath.models.propensity.reason_codes import REASON_CODE_CATALOGUE
                for code in dict.fromkeys(propensity.reason_codes):
                    definition = REASON_CODE_CATALOGUE.get(code)
                    if definition is not None and rec.product in definition.applicable_products:
                        items.append(sentence(f"model-reason:{code}", definition.rm_wording))
            items.append(sentence("confidence", "Model confidence is unavailable because no validated model source is attached to this decision."))
        impact = rec.impact
        if impact.status == ImpactStatus.AVAILABLE:
            value = format(impact.value, "f")
            direction = "a decrease" if impact.value > 0 else "an increase" if impact.value < 0 else "no change"
            items.append(sentence("impact", f"The synthetic scenario's baseline minus scenario impact is {value} {impact.units}, indicating {direction} within the stated comparison period and accounting boundary."))
            gas = "CO2e" if impact.units == "kg CO2e/year" else "CO2"
            items.append(sentence("impact:limits", f"This is a scenario estimate of operational {gas} within the recorded method, assumptions and exclusions. It is not a realized reduction or a lifecycle estimate."))
        else:
            items.append(sentence("impact", "Carbon impact is unavailable because the required input, evidence or method basis is inadequate. No numeric carbon estimate is presented."))
        limitation = ("Synthetic-data scores do not establish real-world predictive performance."
                      if propensity is not None and propensity.source_result is not None
                      else "Synthetic fixture scores do not establish predictive performance.")
        items.append(sentence("trust", "Trust describes input evidence quality and is separate from model confidence. " + limitation))
        if rec.state == RecommendationState.RECOMMEND:
            action = f"Explore {PRODUCT_LABELS[rec.product]} and review the supporting evidence and scenario assumptions."
        elif rec.state == RecommendationState.SUPPRESSED:
            action = f"Do not initiate outreach about {PRODUCT_LABELS[rec.product]}; respect the recorded contact preferences."
        elif rec.state in {RecommendationState.INSUFFICIENT_INFORMATION, RecommendationState.CONFLICT_REQUIRES_REVIEW}:
            action = f"Review the missing or conflicting evidence before exploring {PRODUCT_LABELS[rec.product]}."
        else:
            action = f"Review the {PRODUCT_LABELS[rec.product]} decision evidence; no recommendation is made."
        items.append(sentence("action", action))
        items.append(sentence("eligibility", ELIGIBILITY_DISCLAIMER))
        return tuple(items)

    @staticmethod
    def _result(rec, sentences, source, version, fallback_reason):
        by_id = {item.sentence_id: item.text for item in sentences}
        reasons = tuple(item.text for item in sentences if item.sentence_id.startswith(("reason:", "model-reason:")))
        missing = tuple(REASON_TEXT[code] for code in dict.fromkeys(rec.reason_codes)
                        if code in {"MISSING_EVIDENCE", "STALE_EVIDENCE", "FUTURE_EVIDENCE",
                                    "PROPENSITY_UNAVAILABLE", "CONFIDENCE_BELOW_MINIMUM"})
        if rec.impact.status != ImpactStatus.AVAILABLE:
            missing += (by_id["impact"],)
        return StructuredExplanation(
            customer_id=rec.customer_id, product=rec.product, state=rec.state,
            headline=f"{PRODUCT_LABELS[rec.product]}: {rec.state.value.replace('_', ' ').lower()}",
            explanation=" ".join(by_id[key] for key in ("decision", "propensity", "trust") if key in by_id),
            why_recommended=reasons,
            estimated_impact_text=" ".join(by_id[key] for key in ("impact", "impact:limits") if key in by_id),
            confidence_text=by_id["confidence"], action_text=by_id["action"],
            missing_information=missing,
            text=" ".join(item.text for item in sentences), reason_codes=rec.reason_codes,
            impact_value=rec.impact.value, units=rec.impact.units,
            source=source, provider_version=version, validation_passed=True,
            fallback_reason=fallback_reason, eligibility_disclaimer=ELIGIBILITY_DISCLAIMER,
        )
