"""Write an offline integration report for the six fixed synthetic personas."""

import argparse
import json
from pathlib import Path

from greenpath.api.portfolio import historical_trends, summarize
from greenpath.impact import ImpactStatus, Product, build_registry
from greenpath.llm import ExplanationService
from greenpath.recommendation import RecommendationService

from .providers import CUTOFF, FIXTURE_VERSION, PERSONAS, DemoRepository


def run_evaluation():
    repository = DemoRepository()
    service = RecommendationService(
        repository, repository, repository,
        calculators=build_registry(clock=lambda: CUTOFF), clock=lambda: CUTOFF,
    )
    explanations = ExplanationService()
    decisions = {}
    cases = []
    for customer_id, _, _, _, expected_state in PERSONAS:
        rows = service.recommendations(customer_id)
        decisions[customer_id] = rows
        for row in rows:
            explanation = explanations.explain(row)
            null_matches_status = (row.impact.value is None) == (row.impact.status == ImpactStatus.UNAVAILABLE)
            passed = (
                row.state == expected_state and null_matches_status
                and explanation.source == "template" and explanation.validation_passed
                and explanation.product == row.product and explanation.state == row.state
                and explanation.reason_codes == row.reason_codes
                and explanation.impact_value == row.impact.value
                and explanation.units == row.impact.units
                and row.propensity.confidence is None
                and (row.product != Product.PAPERLESS_BANKING or row.impact.value is None)
            )
            cases.append({
                "customer_id": customer_id, "product": row.product.value,
                "expected_state": expected_state.value, "state": row.state.value,
                "reason_codes": list(row.reason_codes), "impact_status": row.impact.status.value,
                "impact_value": str(row.impact.value) if row.impact.value is not None else None,
                "units": row.impact.units, "explanation_source": explanation.source,
                "passed": passed,
            })
    snapshots = repository.list_snapshots()
    summary = summarize(snapshots, decisions)
    trends = historical_trends(snapshots, repository.list_history())
    return {
        "evaluation_version": "agent-b-integrated-scenarios-v1", "fixture_version": FIXTURE_VERSION,
        "synthetic_demo": True, "feature_cutoff": CUTOFF.isoformat(),
        "cases": cases, "summary": {
            "total": len(cases), "passed": sum(case["passed"] for case in cases),
            "states_covered": sorted({case["state"] for case in cases}),
        },
        "portfolio": summary.model_dump(mode="json"),
        "trends": trends.model_dump(mode="json"),
        "limitations": "Fixed fixtures verify Agent B integration. They do not train or evaluate Agent A models, establish predictive performance, or record realized carbon reductions.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("reports/scenario_evaluation.json"))
    args = parser.parse_args()
    report = run_evaluation()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Integrated scenarios: {report['summary']['passed']}/{report['summary']['total']} passed; report: {args.output}")
    return 0 if report["summary"]["passed"] == report["summary"]["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
