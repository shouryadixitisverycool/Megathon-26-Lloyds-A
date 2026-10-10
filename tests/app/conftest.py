"""JSON API fixtures. Deliberately independent of domain services/contracts."""

from copy import deepcopy
from urllib.parse import urlparse

import httpx
import pytest
import streamlit as st

PRODUCTS = ["EV_FINANCE", "GREEN_HOME", "SOLAR_FINANCE", "PAPERLESS_BANKING"]
STATES = ["RECOMMEND", "INSUFFICIENT_INFORMATION", "CONFLICT_REQUIRES_REVIEW", "NOT_APPLICABLE", "SUPPRESSED", "DO_NOT_RECOMMEND"]
CUTOFF = "2026-01-03T00:00:00Z"


def impact(product, unavailable=False):
    missing = unavailable or product == "PAPERLESS_BANKING"
    return {
        "product": product, "status": "UNAVAILABLE" if missing else "AVAILABLE",
        "value": None if missing else "-12.50", "units": "kg CO2/year",
        "baseline": {"description": "Measured activity baseline", "emissions_kg_co2": None if missing else "100.0"},
        "scenario": {"description": "Supported scenario", "emissions_kg_co2": None if missing else "112.5"},
        "boundary": "Operational energy CO2 only", "assumptions": ["Constant activity over the stated period"],
        "exclusions": ["Manufacture and disposal excluded"], "factors": [] if missing else [{
            "factor_id": "fixture-grid", "value": "0.7", "unit": "kg CO2/kWh", "source_title": "Fixture source",
            "source_publisher": "Fixture publisher", "source_edition": "2025", "source_locator": "Table 1",
            "source_url": "https://example.org/factor", "source_sha256": "c" * 64,
            "geography": "India", "activity_period": "2025", "boundary": "Operational CO2",
            "applicability": "Fixture only", "verification_basis": "Fixture source verification",
            "source_limitation": "Fixture source limitation", "original_value": "0.7", "original_unit": "kg CO2/kWh",
        }],
        "period": {"start": "2025-01-01", "end": "2026-01-01"}, "feature_cutoff": CUTOFF,
        "factor_catalogue_version": "fixture-factor-v1", "factor_catalogue_sha256": "b" * 64,
        "method_version": "fixture-method-v1", "method_release": "2026-01-01", "timestamp": CUTOFF,
        "evidence": [{"field": "energy", "value": "1000", "unit": "kWh", "basis": "measured",
                      "reference": "fixture:energy", "freshness": "current", "observed_at": CUTOFF}],
        "issues": [{"code": "MISSING_INPUT", "field": "activity", "message": "Missing defensible activity basis"}] if missing else [],
    }


@pytest.fixture
def api_fixture(monkeypatch):
    st.cache_data.clear()
    customers = []
    decisions = {}
    calls = []
    for index, state in enumerate(STATES, 1):
        customer_id = f"GP-{index:03d}"
        trust = {"score": "0.45" if index == 2 else "0.95", "status": "LIMITED" if index == 2 else "TRUSTED",
                 "version": "fixture-trust-v1", "issues": [{"code": "MISSING_EVIDENCE", "field": "ownership",
                 "severity": "WARNING", "message": "Ownership evidence is missing"}] if index == 2 else []}
        customer = {"customer_id": customer_id, "display_name": f"Person {index}", "region": "South" if index % 2 else "West",
                    "segment": "Salaried" if index % 2 else "Self-employed", "feature_cutoff": CUTOFF,
                    "trust": trust, "synthetic_demo": True, "contract_version": "fixture-contract-v1",
                    "features": {"owns_home": {"value": None if index == 2 else True, "reference": "fixture:ownership",
                        "observed_at": CUTOFF, "freshness": "unknown" if index == 2 else "current", "conflicts": []}}}
        customers.append(customer)
        decisions[customer_id] = [{"customer_id": customer_id, "product": product, "state": state,
            "propensity": {"probability": "0.82", "model_version": "fixture-model-v1", "calibration_version": "fixture-calibration-v1",
                           "confidence": "0.99", "confidence_validated": False},
            "reason_codes": ["MISSING_EVIDENCE" if index == 2 else "SUPPORTED_EVIDENCE"],
            "evidence": [{"code": "MISSING_EVIDENCE" if index == 2 else "SUPPORTED_EVIDENCE", "message": "Review ownership evidence",
                          "fields": ["owns_home"], "references": ["fixture:ownership"]}],
            "impact": impact(product, index == 2), "trust": trust, "feature_cutoff": CUTOFF,
            "rules_version": "fixture-rules-v1", "timestamp": CUTOFF, "exclusions": ["No eligibility assessment"],
            "eligibility_disclaimer": "Synthetic demonstration of product relevance, not credit eligibility or approval.",
            "synthetic_demo": True, "contract_version": "fixture-contract-v1"} for product in PRODUCTS]

    def get(url, params=None, **kwargs):
        path = urlparse(url).path
        params = params or {}
        calls.append((path, deepcopy(params)))
        request = httpx.Request("GET", url, params=params)
        if path == "/health":
            body = {"status": "ok", "synthetic_demo": True, "contract_version": "fixture-contract-v1"}
        elif path == "/customers":
            body = customers
        elif path.startswith("/customers/"):
            pieces = path.split("/")
            customer_id = pieces[2]
            selected = next((row for row in customers if row["customer_id"] == customer_id), None)
            if selected is None:
                return httpx.Response(404, json={"detail": "Not found"}, request=request)
            if len(pieces) == 3:
                body = selected
            elif pieces[3] == "recommendations":
                body = {"customer_id": customer_id, "recommendations": decisions[customer_id]}
            else:
                row = next(row for row in decisions[customer_id] if row["product"] == pieces[4])
                body = {"customer_id": customer_id, "product": row["product"], "state": row["state"],
                        "text": f"Decision for {customer_id}: {row['state']}. Review the approved evidence.",
                        "source": "template", "provider_version": "fixture-template-v1", "validation_passed": True,
                        "fallback_reason": None}
        elif path.startswith("/portfolio/"):
            selected = [row for row in customers if all(row.get(key) == value for key, value in params.items() if key != "product")]
            products = [params["product"]] if params.get("product") else PRODUCTS
            rows = [row for person in selected for row in decisions[person["customer_id"]] if row["product"] in products]
            counts = {state: sum(row["state"] == state for row in rows) for state in STATES}
            if path.endswith("summary"):
                groups = lambda field: [{"name": value, "customer_count": sum(person[field] == value for person in selected),
                    "recommended_count": sum(row["state"] == "RECOMMEND" for person in selected if person[field] == value
                                             for row in decisions[person["customer_id"]] if row["product"] in products)}
                    for value in sorted({person[field] for person in selected})]
                body = {"total_customers": len(selected), "total_recommendations": len(rows), "recommended_count": counts["RECOMMEND"],
                    "state_counts": counts, "available_impact_count": sum(row["impact"]["status"] == "AVAILABLE" for row in rows),
                    "product_opportunities": [{"product": product, "total": len(selected),
                        "recommended": sum(row["state"] == "RECOMMEND" for row in rows if row["product"] == product),
                        "state_counts": {state: sum(row["state"] == state for row in rows if row["product"] == product) for state in STATES},
                        "available_impact_count": sum(row["impact"]["status"] == "AVAILABLE" for row in rows if row["product"] == product)} for product in products],
                    "region_summaries": groups("region"), "segment_summaries": groups("segment"), "synthetic_demo": True,
                    "disclaimer": "Synthetic fixture counts. No cross-product carbon total is calculated."}
            else:
                body = {"observations": [{"month": month, "product": product, "customer_count": len(selected),
                        "recommended_count": sum(row["state"] == "RECOMMEND" for row in rows if row["product"] == product),
                        "state_counts": counts} for month in ["2025-10", "2025-11", "2025-12"] for product in products],
                        "synthetic_demo": True, "disclaimer": "Historical states are synthetic fixtures, not predictions of real customer behavior."}
        else:
            return httpx.Response(404, json={"detail": "Not found"}, request=request)
        return httpx.Response(200, json=deepcopy(body), request=request)

    monkeypatch.setattr(httpx, "get", get)
    yield {"customers": customers, "decisions": decisions, "calls": calls, "get": get}
    st.cache_data.clear()
