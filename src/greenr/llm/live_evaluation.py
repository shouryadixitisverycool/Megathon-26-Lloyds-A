"""Explicitly authorized optional live evaluation. No calls on import or by default."""

import argparse
import json
import math
import os
import time
from pathlib import Path

from greenr.contracts.product import RecommendationState
from greenr.impact import Product

from .evaluation import case_categories, confidence_recommendation, synthetic_recommendation
from .http_provider import configured_provider
from .service import ExplanationService


def live_cases(count=100):
    if not 100 <= count <= 200:
        raise ValueError("Live evaluation requires 100-200 cases")
    cases = []
    reasons = {
        RecommendationState.RECOMMEND: ("RELEVANCE_SUPPORTED",),
        RecommendationState.DO_NOT_RECOMMEND: ("INTEREST_NOT_SUPPORTED",),
        RecommendationState.INSUFFICIENT_INFORMATION: ("MISSING_EVIDENCE", "STALE_EVIDENCE"),
        RecommendationState.CONFLICT_REQUIRES_REVIEW: ("EVIDENCE_CONFLICT", "TRUST_LIMITATION"),
        RecommendationState.NOT_APPLICABLE: ("ALREADY_ADOPTED",),
        RecommendationState.SUPPRESSED: ("MARKETING_CONSENT_WITHDRAWN",),
    }
    def add(rec, variant):
        value = rec.impact.value
        kind = "missing" if value is None else "positive" if value > 0 else "negative" if value < 0 else "zero"
        key = f"live:{rec.product.value}:{rec.state.value}:{variant}"
        cases.append((key, ("valid", rec, True, variant, kind)))
    # Cover all products/states, signs, confidence and product-isolated opportunities
    # before filling with distinct synthetic numerical scenarios. No repeated
    # offline response attacks masquerade as distinct live model input cases.
    for product in Product:
        for state in RecommendationState:
            add(synthetic_recommendation(product=product, state=state, available=False,
                                         reason_codes=reasons[state]), "missing_impact")
    for state in RecommendationState:
        for charging, zero in (("1800", False), ("3000", False), ("1800", True)):
            add(synthetic_recommendation(state=state, charging=charging, zero=zero,
                                         reason_codes=reasons[state]), "zero" if zero else f"charging_{charging}")
    add(confidence_recommendation(), "confidence_low")
    add(confidence_recommendation(suppressed=True), "confidence_suppressed")
    for product in (Product.EV_FINANCE, Product.GREEN_HOME):
        add(synthetic_recommendation(product=product, reason_codes=(
            "RELEVANCE_SUPPORTED", "PROPENSITY_THRESHOLD_MET")).model_copy(update={
                "customer_id": "evaluation-multiple-opportunities"}), "multiple_opportunities")
    for charging in range(1000, 4100, 100):
        if charging in (1800, 3000):
            continue
        for state in RecommendationState:
            add(synthetic_recommendation(state=state, charging=str(charging), reason_codes=reasons[state]),
                f"charging_{charging}")
    return cases[:count]


def run_live_evaluation(provider, *, count=100, timeout_seconds=30):
    records = []
    interrupted = False
    # Disable cache for first passes: each fixed case measures an actual request.
    service = ExplanationService(provider, timeout_seconds=timeout_seconds, cache_size=0)
    for key, (attack, rec, _, variant, _) in live_cases(count):
        before = provider.metrics()
        started = time.perf_counter()
        result = service.explain(rec)
        elapsed = (time.perf_counter() - started) * 1000
        after = provider.metrics()
        template = ExplanationService().explain(rec)
        grounded = all(getattr(result, field) == getattr(template, field) for field in (
            "headline", "explanation", "estimated_impact_text", "confidence_text", "action_text", "missing_information",
        )) and sorted(result.why_recommended) == sorted(template.why_recommended)
        def delta(field):
            end, start = after.get(field), before.get(field)
            # A first measured response has no previous totals; missing usage
            # after a completed call must not be converted into a zero estimate.
            if (after["completed_calls"] == before["completed_calls"] or end is None
                    or (before["completed_calls"] and start is None)):
                return None
            return end - (start or 0)
        records.append({
            "case": key, "product": rec.product.value, "state": rec.state.value,
            "categories": case_categories(attack, rec, variant),
            "accepted": result.source == "llm", "fallback_reason": result.fallback_reason,
            "grounded_final_output": grounded, "latency_ms": elapsed,
            "input_tokens": delta("total_input_tokens"), "output_tokens": delta("total_output_tokens"),
            "cached_input_tokens": delta("total_cached_input_tokens"), "cost": delta("measured_cost"),
        })
        if result.fallback_reason in {"PROVIDER_ERROR", "PROVIDER_TIMEOUT", "PROVIDER_BUSY"}:
            # Stop on quota/auth/network failure rather than spend on a broken run.
            interrupted = True
            break
    # Separate app-cache experiment; only accepted responses become cache entries.
    cache_service = ExplanationService(provider, timeout_seconds=timeout_seconds)
    complete = len(records) == count and not interrupted
    if complete:
        rec = live_cases(count)[0][1][1]
        cache_service.explain(rec)
        cache_service.explain(rec)
    metrics = service.metrics()
    measured = provider.metrics()
    return {
        "evaluation_version": "optional-live-v1", "requested_cases": count, "completed_cases": len(records),
        "complete": complete, "provider_measurements": measured,
        "service_metrics": metrics, "cache_experiment": cache_service.metrics(), "cases": records,
        "summary": {"acceptance_rate": sum(row["accepted"] for row in records) / len(records),
                    "fallback_rate": sum(not row["accepted"] for row in records) / len(records),
                    "grounded_final_output_rate": sum(row["grounded_final_output"] for row in records) / len(records),
                    "mean_latency_ms": sum(row["latency_ms"] for row in records) / len(records)},
        "limitations": "Grounded final output includes safe template fallbacks, not raw model quality. Fixed synthetic live inputs are distinct from offline adversarial response mutations; no live jailbreak-resistance score is measured. Prices are user-configured, not independently verified. Cache experiment adds up to two calls and is included in provider totals.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-paid-provider", action="store_true")
    parser.add_argument("--cases", type=int, default=100)
    parser.add_argument("--manifest", type=Path, default=Path(__file__).with_name("provider_manifest.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.allow_paid_provider:
        parser.error("Live calls require explicit --allow-paid-provider authorization")
    if not 100 <= args.cases <= 200:
        parser.error("Live evaluation requires 100-200 cases")
    config = json.loads(args.manifest.read_text(encoding="utf-8"))
    key = os.environ.get("OPENAI_API_KEY") or os.environ.get("GREENR_LLM_API_KEY")
    if not key:
        parser.error("No configured API key; no provider was called")
    for kind in ("INPUT", "OUTPUT", "CACHED_INPUT"):
        raw = os.environ.get(f"GREENR_LLM_{kind}_PRICE_PER_MILLION")
        if not raw:
            parser.error(f"Set current {kind} token pricing per million before authorizing calls")
        try:
            value = float(raw)
        except ValueError:
            parser.error("Prices must be numeric")
        if not math.isfinite(value) or value < 0:
            parser.error("Prices must be finite and non-negative")
    provider = configured_provider(config)
    report = run_live_evaluation(provider, count=args.cases, timeout_seconds=provider.timeout_seconds)
    report["selection_manifest"] = config
    report["effective_configuration"] = {name: getattr(provider, name) for name in (
        "endpoint", "model", "prompt_version", "temperature", "max_output_tokens",
        "token_limit_parameter", "timeout_seconds",
    )}
    report["effective_configuration"]["model_version"] = provider.version
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if report["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
