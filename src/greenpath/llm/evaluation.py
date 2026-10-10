"""Offline fixed adversarial evaluation: python -m greenpath.llm.evaluation."""

import argparse
import json
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from greenpath.contracts.product import (
    ELIGIBILITY_DISCLAIMER, Recommendation, RecommendationState, TrustAssessment,
)
from greenpath.impact import EVImpactCalculator, Product, build_registry

from .service import ExplanationService


def synthetic_recommendation(*, product=Product.EV_FINANCE, charging="1800", available=True,
                             state=RecommendationState.RECOMMEND, reason_codes=("RELEVANCE_SUPPORTED",)):
    """Self-contained synthetic evidence, independent of test and demo files."""
    now = datetime(2026, 1, 3, tzinfo=timezone.utc)
    impact = build_registry(clock=lambda: now)[product].calculate(None)
    if available and product == Product.EV_FINANCE:
        period = {"start": "2025-01-01", "end": "2026-01-01"}

        def evidence(value, name, unit=None):
            data = {"value": value, "evidence": {
                "reference": f"synthetic-evaluation:{name}", "basis": "synthetic_demo",
                "observed_at": "2026-01-02T00:00:00Z", "period": period,
                "freshness": "current", "conflicts": [],
            }}
            if unit is not None:
                data["unit"] = unit
            return data

        payload = {"context": {
            "period": period, "feature_cutoff": now, "geography": "IN", "synthetic_demo": True,
        }}
        for key, value, unit in (
            ("baseline_fuel", "unblended_fossil_motor_gasoline", None),
            ("baseline_fuel_mass", "600", "kg"),
            ("baseline_distance", "12000", "km"), ("scenario_distance", "12000", "km"),
            ("charging_electricity", charging, "kWh"),
            ("charging_measurement_point", "charger_input", None),
            ("baseline_powertrain", "internal_combustion", None),
            ("scenario_powertrain", "battery_electric", None),
            ("replaces_baseline", True, None), ("charging_supply", "indian_grid", None),
        ):
            payload[key] = evidence(value, key, unit)
        impact = EVImpactCalculator(clock=lambda: now).calculate(payload)
    return Recommendation(
        customer_id="evaluation-synthetic", product=product, propensity=None,
        state=state, reason_codes=reason_codes, evidence=(), impact=impact,
        trust=TrustAssessment(score=Decimal("0.8"), status="TRUSTED"),
        feature_cutoff=now, rules_version="offline-evaluation-v1", timestamp=now,
    )


def approved_output(request):
    return {
        "product": request.product.value, "state": request.state.value,
        "reason_codes": list(request.reason_codes),
        "impact_value": str(request.impact_value) if request.impact_value is not None else None,
        "units": request.units, "eligibility_disclaimer": request.eligibility_disclaimer,
        "sentence_ids": list(request.required_sentence_ids),
    }


class FixedProvider:
    version = "offline-fixed-adversary-v1"

    def __init__(self, attack="valid"):
        self.attack = attack
        self.requests = []

    def generate(self, request, *, timeout_seconds):
        self.requests.append(request)
        result = approved_output(request)
        if self.attack == "error":
            raise RuntimeError("simulated provider failure")
        if self.attack == "timeout":
            time.sleep(timeout_seconds * 4)
        elif self.attack == "product":
            result["product"] = Product.SOLAR_FINANCE.value
        elif self.attack == "state":
            result["state"] = RecommendationState.NOT_APPLICABLE.value
        elif self.attack == "reason":
            result["reason_codes"] = ["APPROVED_LOAN"]
        elif self.attack == "number":
            result["impact_value"] = "99999"
        elif self.attack == "units":
            result["units"] = "kg CO2e/year"
        elif self.attack == "eligibility":
            result["eligibility_disclaimer"] = "You are eligible and your loan is approved."
        elif self.attack == "free_text":
            result["text"] = "Guaranteed approval, carbon neutral and saves 999 tonnes."
        elif self.attack == "omit":
            result["sentence_ids"] = result["sentence_ids"][:-1]
        elif self.attack == "duplicate":
            result["sentence_ids"][-1] = result["sentence_ids"][0]
        elif self.attack == "invent_sentence":
            result["sentence_ids"][-1] = "approved_and_carbon_neutral"
        elif self.attack == "malformed":
            return "{broken JSON"
        elif self.attack == "reverse":
            result["sentence_ids"].reverse()
        elif self.attack == "wrong_null":
            result["impact_value"] = None
        elif self.attack == "sign":
            result["impact_value"] = str(abs(request.impact_value))
        return result


def run_evaluation():
    """Measure local fixed-case validation, not live model quality or cost."""
    cases = [(name, synthetic_recommendation(), name in ("valid", "reverse")) for name in (
        "valid", "reverse", "product", "state", "reason", "number", "units", "eligibility",
        "free_text", "omit", "duplicate", "invent_sentence", "malformed", "error", "timeout", "wrong_null",
    )]
    cases.extend([
        ("sign", synthetic_recommendation(charging="3000"), False),
        ("number", synthetic_recommendation(available=False), False),
    ])
    records = []
    for attack, recommendation, should_accept in cases:
        start = time.perf_counter()
        result = ExplanationService(FixedProvider(attack), timeout_seconds=0.02).explain(recommendation)
        template = ExplanationService().explain(recommendation)
        facts = result.product == recommendation.product and result.state == recommendation.state and result.reason_codes == recommendation.reason_codes
        numbers = result.impact_value == recommendation.impact.value and result.units == recommendation.impact.units
        # Provider ordering may vary, but the sentence set and exact words cannot.
        supported = sorted(result.text.split(". ")) == sorted(template.text.split(". ")) if attack != "reverse" else all(
            sentence.text in result.text for sentence in ExplanationService._sentences(recommendation)
        )
        records.append({
            "case": f"{attack}:{recommendation.impact.status.value}",
            "expected_acceptance": should_accept, "accepted": result.source == "llm",
            "passed": (result.source == "llm") == should_accept and facts and numbers and supported,
            "grounded": facts and supported, "numeric_consistency": numbers,
            "unsupported_claims": 0 if supported and ELIGIBILITY_DISCLAIMER in result.text else 1,
            "fallback_reason": result.fallback_reason,
            "local_latency_ms": round((time.perf_counter() - start) * 1000, 3),
        })
    count = len(records)
    return {
        "evaluation_version": "fixed-adversarial-explanations-v1", "synthetic_demo": True,
        "provider": "offline fixed responses; no live LLM called", "cases": records,
        "summary": {
            "total": count, "passed": sum(row["passed"] for row in records),
            "groundedness_rate": sum(row["grounded"] for row in records) / count,
            "numeric_consistency_rate": sum(row["numeric_consistency"] for row in records) / count,
            "unsupported_claims": sum(row["unsupported_claims"] for row in records),
            "fallback_rate": sum(not row["accepted"] for row in records) / count,
            "local_mean_latency_ms": round(sum(row["local_latency_ms"] for row in records) / count, 3),
            "live_provider_latency_ms": None, "live_provider_cost": None,
        },
        "limitations": "Fixed offline validator cases do not establish live model performance. Live latency, token use and cost are unavailable.",
    }


def main(*, default_output=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(default_output) if default_output else None,
                        help="Optional local JSON report path")
    args = parser.parse_args()
    report = run_evaluation()
    rendered = json.dumps(report, indent=2)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if report["summary"]["passed"] == report["summary"]["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
