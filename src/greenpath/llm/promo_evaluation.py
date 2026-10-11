"""Offline fixed evaluation of promo-copy validation: python -m greenpath.llm.promo_evaluation."""

import argparse
import json
import time
from pathlib import Path

from greenpath.impact import Product

from .evaluation import synthetic_recommendation
from .promo import LIMITS, PROMO_DISCLAIMER, PromoService, impact_phrase

ENGAGE_ACTIONS = ("SHOW_EDUCATION", "RM_DISCUSSION")
WITHHELD_ACTIONS = ("SUPPRESS", "DEFER", "REQUEST_CONSENT", "REQUEST_REVIEW", "REQUEST_INFORMATION")
NAME = {Product.EV_FINANCE: "EV finance", Product.GREEN_HOME: "Green Home finance",
        Product.SOLAR_FINANCE: "Solar Finance", Product.PAPERLESS_BANKING: "paperless statements"}
OTHER = {Product.EV_FINANCE: "Solar Finance", Product.GREEN_HOME: "EV finance",
         Product.SOLAR_FINANCE: "paperless", Product.PAPERLESS_BANKING: "EV finance"}
# (attack, expected rejection code, one-liner text template using {name})
UNSAFE = (
    ("digit_rate", "DIGIT_REJECTED", "{name} from just 4.9% APR."),
    ("currency", "DIGIT_REJECTED", "Borrow £20k with {name} today."),
    ("pre_approved", "ELIGIBILITY_CLAIM", "You're pre-approved for {name}."),
    ("guaranteed", "ELIGIBILITY_CLAIM", "Guaranteed {name} for customers like you."),
    ("qualify", "ELIGIBILITY_CLAIM", "Check if you qualify for {name}."),
    ("free", "ELIGIBILITY_CLAIM", "Free {name} consultation, no strings."),
    ("carbon_neutral", "GREENWASH_CLAIM", "Go carbon neutral with {name}."),
    ("net_zero", "GREENWASH_CLAIM", "Reach net zero sooner with {name}."),
    ("eco_friendly", "GREENWASH_CLAIM", "Make the eco-friendly choice with {name}."),
    ("savings", "FINANCIAL_CLAIM", "Big savings await with {name}."),
    ("lower_bills", "FINANCIAL_CLAIM", "{name} could lower your bills."),
    ("cheaper", "FINANCIAL_CLAIM", "It's cheaper than you think: {name}."),
    ("we_noticed", "PERSONAL_DATA_CLAIM", "We noticed your energy use. Try {name}."),
    ("your_spending", "PERSONAL_DATA_CLAIM", "Your spending suggests {name} could suit you."),
    ("url", "URL_REJECTED", "Find {name} at www.example.co.uk"),
    ("markup", "MARKUP_REJECTED", "**{name}** is here"),
    ("other_product", "OTHER_PRODUCT_REJECTED", "{name} and {other}, together."),
    ("unknown_placeholder", "PLACEHOLDER_REJECTED", "{{first_name}}, ask about {name}."),
    ("too_long", "LENGTH_REJECTED", "Would you be interested in {name}? We would love to tell you all about it soon."),
)
SAFE = ("Would you be interested in {name}?", "Thinking about a greener next step? Ask about {name}.")


class FixedWriter:
    version = "offline-fixed-writer-v1"

    def __init__(self, lines):
        self.lines, self.requests = lines, []

    def generate_promo(self, request, *, timeout_seconds):
        self.requests.append(request)
        return {"product": request.product.value, "format": request.format, "lines": list(self.lines)}


def evaluation_cases():
    cases = []
    for product in Product:
        name, other = NAME[product], OTHER[product]
        for attack, expected, text in UNSAFE:
            cases.append((f"{product.value}:{attack}", product, "one_liner", "SHOW_EDUCATION",
                          (text.format(name=name, other=other),), expected))
        for index, text in enumerate(SAFE):
            for action in ENGAGE_ACTIONS:
                cases.append((f"{product.value}:safe-{index}:{action}", product, "one_liner", action,
                              (text.format(name=name),), None))
        cases.append((f"{product.value}:short-safe", product, "short", "SHOW_EDUCATION",
                      (f"Would you be interested in {name}?", "We can help you take a lower-carbon step."), None))
        cases.append((f"{product.value}:short-too-many-lines", product, "short", "SHOW_EDUCATION",
                      ("One.", "Two.", "Three.", "Four.", "Five."), "LENGTH_REJECTED"))
        for action in WITHHELD_ACTIONS:
            cases.append((f"{product.value}:withheld:{action}", product, "one_liner", action,
                          (SAFE[0].format(name=name),), "WITHHELD"))
    cases.append(("EV_FINANCE:impact-placeholder", Product.EV_FINANCE, "short", "SHOW_EDUCATION",
                  ("Thinking about going electric?", "An EV could cut your driving emissions by {impact}."), None))
    cases.append(("GREEN_HOME:impact-unavailable", Product.GREEN_HOME, "short", "SHOW_EDUCATION",
                  ("Thinking about home upgrades?", "They could cut home emissions by {impact}."),
                  "PLACEHOLDER_REJECTED"))
    return cases


def run_evaluation():
    """Measure local validator behaviour on fixed outputs, not live model quality or cost."""
    records = []
    for case_id, product, fmt, action, lines, expected in evaluation_cases():
        started = time.perf_counter()
        rec = synthetic_recommendation(product=product)
        writer = FixedWriter(lines)
        result = PromoService(writer, timeout_seconds=.5).generate(rec, action, "fixed rule reason", fmt=fmt)
        min_lines, max_lines, per_line, total = LIMITS[fmt]
        if expected == "WITHHELD":
            passed = result.status == "WITHHELD" and not result.lines and not writer.requests
        else:
            shape = (min_lines <= len(result.lines) <= max_lines and all(len(x) <= per_line for x in result.lines)
                     and len(result.text) <= total and result.disclaimer == PROMO_DISCLAIMER)
            outcome = (result.source == "llm") if expected is None else (result.fallback_reason == expected)
            unsafe_leaked = expected is not None and any(line in result.text for line in lines)
            impact = impact_phrase(rec)
            numbers = all(not ch.isdigit() for ch in result.text.replace(impact or "\0", ""))
            passed = shape and outcome and not unsafe_leaked and numbers
        records.append({
            "case": case_id, "product": product.value, "format": fmt, "next_action": action,
            "expected": expected or "ACCEPT", "status": result.status, "source": result.source,
            "fallback_reason": result.fallback_reason, "passed": passed,
            "local_latency_ms": round((time.perf_counter() - started) * 1000, 3),
        })
    count = len(records)
    unsafe = [r for r in records if r["expected"] not in {"ACCEPT", "WITHHELD"}]
    breakdown = {}
    for row in unsafe:
        breakdown[row["expected"]] = breakdown.get(row["expected"], 0) + 1
    return {
        "evaluation_version": "fixed-promo-copy-v1", "synthetic_demo": True,
        "provider": "offline fixed responses; no live LLM called", "cases": records,
        "summary": {
            "total": count, "passed": sum(r["passed"] for r in records),
            "unsafe_cases": len(unsafe), "unsafe_accepted": sum(r["source"] == "llm" for r in unsafe),
            "safe_acceptance_rate": (sum(r["source"] == "llm" for r in records if r["expected"] == "ACCEPT")
                                     / max(1, sum(r["expected"] == "ACCEPT" for r in records))),
            "withheld_cases": sum(r["expected"] == "WITHHELD" for r in records),
            "rejection_breakdown": breakdown,
            "local_mean_latency_ms": round(sum(r["local_latency_ms"] for r in records) / count, 3),
            "live_provider_latency_ms": None, "live_provider_cost": None,
        },
        "limitations": "Fixed offline outputs test the mechanical validator only. Blocklists cannot prove a "
                       "live model's copy is persuasive, fair or free of every implied claim; human review of "
                       "copy before any real campaign remains required.",
    }


def main(*, default_output="reports/promo_evaluation.json"):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(default_output) if default_output else None)
    args = parser.parse_args()
    report = run_evaluation()
    rendered = json.dumps(report, indent=2)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    return 0 if report["summary"]["passed"] == report["summary"]["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
