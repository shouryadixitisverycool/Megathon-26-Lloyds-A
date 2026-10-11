"""Behavioral tests for durable feedback and constrained local campaigns."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from greenr.api.main import create_app
from greenr.extensions.store import MemoryStore


@pytest.fixture
def client(tmp_path):
    app = create_app(provider_mode="fixture")
    app.state.extension_service.store = MemoryStore(tmp_path / "memory.sqlite3")
    return TestClient(app)


def feedback(client, response, request_id):
    return client.post("/feedback", json={"customer_id": "GP-001", "product": "EV_FINANCE",
                                         "response": response, "request_id": request_id})


def allow(client, customer_id="GP-001"):
    assert client.post(f"/customers/{customer_id}/preferences", json={"channel_consent": {"app": True}}).status_code == 200


def test_completion_suppresses_outreach_without_editing_scores_and_replays_after_closure(client):
    before = client.get("/customers/GP-001/recommendations").json()["recommendations"][0]
    completed = feedback(client, "ALREADY_COMPLETED", "complete-1")
    assert completed.status_code == 200
    assert feedback(client, "CLOSED", "close-1").status_code == 200
    replay = feedback(client, "ALREADY_COMPLETED", "complete-1")
    assert replay.status_code == 200 and replay.json() == completed.json()
    after = client.get("/customers/GP-001/recommendations").json()["recommendations"][0]
    assert before["propensity"] == after["propensity"]
    assert before["impact"]["value"] == after["impact"]["value"]
    assert client.get("/customers/GP-001/next-actions").json()["opportunities"][0]["next_action"]["action"] == "SUPPRESS"
    assert feedback(client, "INTERESTED", "reopen-1").status_code == 409


def test_feedback_ids_cannot_be_reused_with_other_content_and_reviews_cannot_edit_scores(client):
    assert feedback(client, "INTERESTED", "response-1").status_code == 200
    assert feedback(client, "NOT_INTERESTED", "response-1").status_code == 409
    review = {"customer_id": "GP-001", "product": "EV_FINANCE", "action": "SUPPRESS",
              "reviewer": "Demo reviewer", "note": "Wait for updated evidence"}
    assert client.post("/review", json={**review, "propensity": 1}).status_code == 422
    result = client.post("/review", json=review)
    assert result.status_code == 200
    audit = client.get("/audit/recommendations/" + result.json()["id"])
    assert audit.status_code == 200 and audit.json()["recommendation"]["propensity"]["probability"] == "0.82"


def test_contact_consent_capacity_and_whole_campaign_idempotency(client):
    request = {"product": "EV_FINANCE", "target_count": 10, "conversion_rate": .1,
               "channel_capacity": 1, "execute": True, "request_id": "campaign-1"}
    assert client.post("/campaigns/optimise", json={**request, "execute": False}).json()["selected_count"] == 0
    allow(client)
    first = client.post("/campaigns/optimise", json=request)
    assert first.status_code == 200 and first.json()["selected_count"] == 1
    assert first.json()["scenario_adopters"] == .1
    second = client.post("/campaigns/optimise", json=request)
    assert second.status_code == 200 and second.json() == first.json()
    events = client.get("/customers/GP-001/history").json()["events"]
    assert len([e for e in events if e["kind"] == "contact"]) == 1
    next_campaign = client.post("/campaigns/optimise", json={**request, "request_id": "campaign-2"})
    assert next_campaign.json()["selected_count"] == 0
    assert client.post("/campaigns/optimise", json={**request, "conversion_rate": .2}).status_code == 409


def test_concurrent_campaigns_cannot_bypass_fatigue_window(client):
    allow(client)
    def run(i):
        return client.post("/campaigns/optimise", json={"product": "EV_FINANCE", "execute": True,
                                                     "request_id": f"parallel-{i}"}).json()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, (1, 2)))
    assert sum(r["selected_count"] for r in results) == 1


def test_decline_cooling_off_and_do_not_contact_override_consent(client):
    allow(client)
    assert feedback(client, "NOT_INTERESTED", "decline").status_code == 200
    result = client.post("/portfolio/scenarios", json={"product": "EV_FINANCE"}).json()
    assert result["selected_count"] == 0
    assert "60-day cooling-off after decline" in result["excluded"]
    assert feedback(client, "SHOWN", "after-decline").status_code == 200
    assert client.post("/portfolio/scenarios", json={"product": "EV_FINANCE"}).json()["selected_count"] == 0
    assert client.post("/customers/GP-001/preferences", json={"do_not_contact": True, "channel_consent": {"app": True}}).status_code == 200
    assert client.get("/customers/GP-001/next-actions").json()["opportunities"][0]["next_action"]["reason"] == "Do not contact preference"


def test_later_feedback_cannot_bypass_permanent_human_suppression(client):
    allow(client)
    assert client.post("/review", json={"customer_id": "GP-001", "product": "EV_FINANCE", "action": "SUPPRESS",
                                       "reviewer": "RM", "note": "Wait for verified new evidence"}).status_code == 200
    assert feedback(client, "SHOWN", "shown-after-review").status_code == 200
    assert feedback(client, "INTERESTED", "interest-after-review").status_code == 200
    result = client.post("/portfolio/scenarios", json={"product": "EV_FINANCE"}).json()
    assert result["selected_count"] == 0
    assert "Human reviewer suppression" in result["excluded"]


def test_simulator_preserves_inputs_records_provenance_and_does_not_change_decision(client):
    original = client.get("/customers/GP-001/simulation-inputs/EV_FINANCE").json()["inputs"]
    scenario = deepcopy(original)
    scenario["charging_electricity"]["value"] = "1000"
    scenario["charging_electricity"]["evidence"].update(basis="engineering_forecast", reference="scenario-test")
    result = client.post("/customers/GP-001/simulate", json={"product": "EV_FINANCE", "inputs": scenario})
    assert result.status_code == 200
    assert result.json()["impact"]["status"] == "AVAILABLE"
    assert result.json()["method_version"]
    assert client.get("/customers/GP-001/simulation-inputs/EV_FINANCE").json()["inputs"] == original
    bad = client.post("/customers/GP-001/simulate", json={"product": "EV_FINANCE", "inputs": {"untrusted": 1}})
    assert bad.status_code == 200 and bad.json()["impact"]["status"] == "UNAVAILABLE"


def test_evidence_graph_and_priority_do_not_invent_validated_confidence(client):
    graph = client.get("/customers/GP-001/evidence-graph/EV_FINANCE").json()
    assert any(n["type"] == "feature" for n in graph["nodes"])
    assert all(e["from"] in {n["id"] for n in graph["nodes"]} and e["to"] in {n["id"] for n in graph["nodes"]} for e in graph["edges"])
    rows = client.get("/portfolio/opportunities", params={"product": "EV_FINANCE", "status": "RECOMMEND"}).json()["opportunities"]
    assert len(rows) == 1 and rows[0]["priority"]["score"] is None
    assert rows[0]["priority"]["components"]["validated_confidence"] is None


def test_fixture_sensitivity_is_unavailable_and_unknown_customers_fail_closed(client):
    assert client.post("/customers/GP-001/sensitivity", json={"product": "EV_FINANCE", "changes": {"annual_mileage_km": 5000}}).status_code == 409
    assert client.get("/customers/unknown/history").status_code == 404
    assert client.post("/customers/unknown/simulate", json={"product": "EV_FINANCE", "inputs": {}}).status_code == 404
