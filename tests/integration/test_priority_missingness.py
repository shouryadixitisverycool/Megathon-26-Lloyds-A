"""Composite priority requires every governed component, including validation."""

from copy import deepcopy
import json

import pytest
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from greenpath.api.main import create_app
from greenpath.extensions.service import prioritise
from greenpath.extensions.store import MemoryStore


def opportunity(customer_id="GP-001", probability="0.8"):
    return {
        "customer_id": customer_id, "product": "EV_FINANCE", "state": "RECOMMEND",
        "propensity": {"probability": probability, "confidence": "0.6", "confidence_validated": True},
        "trust": {"score": "0.9", "status": "TRUSTED"},
        "impact": {"status": "AVAILABLE", "value": "100", "units": "kgCO2e/year",
                   "boundary": "operational", "period": "annual", "method_version": "test-v1",
                   "factor_catalogue_version": "test-v1"},
    }


@pytest.mark.parametrize("confidence,validated,impact_status,impact_value", [
    ("0.6", False, "AVAILABLE", "100"),
    (None, True, "AVAILABLE", "100"),
    ("0.6", True, "UNAVAILABLE", None),
    ("0.6", True, "AVAILABLE", None),
    (None, False, "UNAVAILABLE", None),
])
def test_missing_components_leave_score_and_rank_unavailable(confidence, validated, impact_status, impact_value):
    row = opportunity()
    row["propensity"].update(confidence=confidence, confidence_validated=validated)
    row["impact"].update(status=impact_status, value=impact_value)
    original = deepcopy(row)
    priority = prioritise([row])[0]["priority"]
    assert priority["score"] is None
    assert priority["rank"] is None
    assert priority["ordering_basis"] == "calibrated_propensity"
    assert priority["weights"] == {"calibrated_propensity": .40, "validated_confidence": .25,
                                   "normalised_impact": .20, "trust": .15}
    assert row == original


def test_complete_priority_retains_formula_and_fallback_order_is_separate():
    complete = opportunity("complete", "0.2")
    higher = opportunity("higher", "0.8")
    higher["impact"]["value"] = "200"
    fallback_low = opportunity("fallback-low", "0.5")
    fallback_high = opportunity("fallback-high", "0.99")
    for row in (fallback_low, fallback_high):
        row["propensity"]["confidence_validated"] = False
    rows = prioritise([fallback_low, complete, fallback_high, higher])
    assert [r["customer_id"] for r in rows] == ["higher", "complete", "fallback-high", "fallback-low"]
    assert [r["priority"]["rank"] for r in rows] == [1, 2, None, None]
    assert rows[0]["priority"]["score"] == pytest.approx(.8 * .40 + .6 * .25 + 1 * .20 + .9 * .15)
    assert rows[1]["priority"]["score"] == pytest.approx(.2 * .40 + .6 * .25 + .5 * .20 + .9 * .15)
    assert rows[0]["priority"]["ordering_basis"] == "composite_priority"


def test_missing_propensity_does_not_claim_a_propensity_ranking():
    row = opportunity(probability=None)
    priority = prioritise([row])[0]["priority"]
    assert priority["score"] is priority["rank"] is None
    assert priority["ordering_basis"] == "deterministic_tie_break"
    assert "propensity is unavailable" in priority["limitation"]


@pytest.mark.parametrize("confidence,validated", [("0.99", False), (None, True), (None, False)])
def test_confidence_filter_still_excludes_suppressed_or_missing_values(tmp_path, monkeypatch, confidence, validated):
    app = create_app(provider_mode="fixture")
    app.state.extension_service.store = MemoryStore(tmp_path / "memory.sqlite3")
    row = opportunity()
    row["propensity"].update(confidence=confidence, confidence_validated=validated)
    monkeypatch.setattr(app.state.extension_service, "rows", lambda customer_id: [deepcopy(row)] if customer_id == "GP-001" else [])
    client = TestClient(app)
    response = client.get("/portfolio/opportunities")
    assert response.status_code == 200
    result = response.json()["opportunities"]
    assert len(result) == 1
    assert result[0]["priority"]["score"] is None
    assert result[0]["priority"]["rank"] is None
    filtered = client.get("/portfolio/opportunities", params={"min_confidence": "0.1"})
    assert filtered.status_code == 200
    assert filtered.json()["opportunities"] == []


def test_planning_ui_identifies_unavailable_rank_and_propensity_fallback():
    row = opportunity()
    row["impact"].update(status="UNAVAILABLE", value=None)
    rows = prioritise([row])
    script = f'''
import json
from greenpath.app.workspaces import planning_view
rows = json.loads({json.dumps(rows)!r})
planning_view([{{"customer_id": "GP-001", "region": "UK", "segment": "test"}}],
              lambda path, params: {{"disclaimer": "Test", "opportunities": rows}},
              lambda path, payload: {{}})
'''
    app = AppTest.from_string(script).run()
    assert not app.exception
    table = app.dataframe[0].value
    assert table.iloc[0]["Priority"] == "Unavailable"
    assert table.iloc[0]["Priority rank"] == "Unavailable"
    assert table.iloc[0]["Ordering basis"] == "Calibrated propensity (not composite priority)"
    assert "Rank" not in table.columns
