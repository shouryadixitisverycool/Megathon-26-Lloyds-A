"""Owned service interfaces: optional analytics never invent missing evidence."""

from copy import deepcopy
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from greenr.api.main import create_app
from greenr.api.portfolio import historical_analytics, impact_totals, portfolio_analytics
from greenr.contracts.enums import Product
from greenr.contracts.product import HistoryRecord
from greenr.extensions.contracts import CampaignRequest, CounterfactualRequest, PlanningRequest
from greenr.extensions.service import prioritise
from greenr.extensions.store import MemoryStore


@pytest.fixture
def service(tmp_path):
    app = create_app(provider_mode="fixture")
    service = app.state.extension_service
    service.store = MemoryStore(tmp_path / "analytics.sqlite3")
    return service


def consent(service, customer, channel="app"):
    service.store.append(customer, "ALL", "preferences", {}, {"preferences": {"channel_consent": {channel: True}}})


def test_filters_exclude_missing_even_at_explicit_zero(service):
    assert service.opportunities(product=Product.EV_FINANCE, state="RECOMMEND")
    assert not service.opportunities(min_confidence=0)
    impact_rows = service.opportunities(min_impact=0)
    assert impact_rows and all(row["impact"]["status"] == "AVAILABLE" for row in impact_rows)
    assert not service.opportunities(min_impact=10**12)
    assert all(row["trust"]["status"] == "TRUSTED" for row in service.opportunities(data_quality="TRUSTED"))


def test_expected_impact_is_exact_and_preserves_compatibility(service):
    row = service.opportunities(product=Product.EV_FINANCE, state="RECOMMEND")[0]
    expected = row["expected_sustainability_impact"]
    assert Decimal(expected["value"]) == Decimal(row["propensity"]["probability"]) * Decimal(row["impact"]["value"])
    assert expected["units"] == row["impact"]["units"]
    row["impact"]["status"] = "UNAVAILABLE"
    assert prioritise([row])[0]["expected_sustainability_impact"]["value"] is None


def test_scenario_uses_selected_channel_consent(service):
    consent(service, "GP-001", "email")
    assert service.plan(PlanningRequest(product=Product.EV_FINANCE))["selected_count"] == 0
    assert service.plan(PlanningRequest(product=Product.EV_FINANCE, channel="email"))["selected_count"] == 1


def test_persistent_active_budget_and_simultaneous_limit(service, monkeypatch):
    row = service.opportunities(product=Product.EV_FINANCE, state="RECOMMEND")[0]
    first, second = deepcopy(row), deepcopy(row)
    second["customer_id"] = "second-customer"
    consent(service, first["customer_id"])
    consent(service, second["customer_id"])
    monkeypatch.setattr(service, "opportunities", lambda *args, **kwargs: [first])
    request = CampaignRequest(product=Product.EV_FINANCE, channel_capacity=1, execute=True, request_id="first")
    assert service.plan(request, campaign=True)["selected_count"] == 1
    monkeypatch.setattr(service, "opportunities", lambda *args, **kwargs: [second])
    next_request = request.model_copy(update={"request_id": "second"})
    result = service.plan(next_request, campaign=True)
    assert result["selected_count"] == 0 and result["capacity_budget"]["used"] == 1
    assert len(service.store.active_campaigns()) == 1
    limited = next_request.model_copy(update={"request_id": "third", "channel_capacity": 10, "max_active_campaigns": 1})
    assert service.plan(limited, campaign=True)["selected_count"] == 0
    event = service.store.active_campaigns()[0]
    service.store.append("PORTFOLIO", "ALL", "campaign_closed", {}, {"campaign_id": event["id"]})
    assert service.plan(next_request.model_copy(update={"request_id": "after-close"}), campaign=True)["selected_count"] == 1


def test_physical_totals_do_not_mix_units_and_missing_is_unavailable(service):
    recommendation = service.recommendations.recommendations("GP-001")[0]
    other = recommendation.model_copy(update={"impact": recommendation.impact.model_copy(update={"units": "kg CO2e/year"})})
    report = impact_totals([recommendation, other])
    assert len(report["groups"]) == 2
    assert impact_totals([])["status"] == "UNAVAILABLE"
    assert portfolio_analytics([recommendation])["missingness"]["validated_confidence"] == 1


def test_historical_conversion_uses_observed_denominator_and_no_current_impact():
    rows = [HistoryRecord(customer_id=str(i), month="2026-01", product=Product.EV_FINANCE,
                          state="RECOMMEND", observed_adoption_90d=outcome) for i, outcome in enumerate([1, 0, None])]
    report = historical_analytics(rows)["observations"][0]
    assert report["observed_conversion_rate"] == "0.5"
    assert report["outcome_missing_count"] == 1
    assert report["quality_missing_count"] == 3
    assert report["physical_impact_status"] == "UNAVAILABLE"
    assert report["physical_impact_missing_count"] == 3


class SearchSource(BaseModel):
    features: dict[str, float | None]


def test_bounded_search_calls_trained_inference_without_mutation(service, monkeypatch):
    source = SearchSource(features={"paper_statements_12m": 10, "app_logins_3m_avg": 1})
    monkeypatch.setattr(service, "snapshot", lambda _: SimpleNamespace(source_snapshot=source))
    calls = []

    def score(snapshot, product):
        calls.append(snapshot)
        return SimpleNamespace(propensity=1 - snapshot.features["paper_statements_12m"] / 100,
                               in_model_population=True, model_version="trained", calibration_version="calibrated")

    service.repository = SimpleNamespace(runtime=SimpleNamespace(
        bundles={Product.PAPERLESS_BANKING: SimpleNamespace(features=list(source.features))},
        propensity=SimpleNamespace(score=score)))
    request = CounterfactualRequest(product=Product.PAPERLESS_BANKING,
                                   candidates={"paper_statements_12m": [0, 10, 20], "app_logins_3m_avg": [1, 2]},
                                   max_evaluations=3)
    report = service.counterfactual_search("customer", request)
    assert report["evaluated_count"] == 3 and report["candidate_count"] == 6 and report["truncated"]
    assert len(calls) == 4
    assert report["best"]["changes"]["paper_statements_12m"] == 10
    assert source.features["paper_statements_12m"] == 10
    assert report["feature_classes"]["app_logins_3m_avg"] == "contextual"
    for candidates in ({"age": [30]}, {"paper_statements_12m": [1001]}, {"paper_statements_12m": []}):
        with pytest.raises(ValueError):
            service.counterfactual_search("customer", request.model_copy(update={"candidates": candidates}))


def test_fixture_counterfactual_fails_closed(service):
    request = CounterfactualRequest(product=Product.EV_FINANCE, candidates={"annual_mileage_km": [1000]})
    with pytest.raises(ValueError, match="trained inference"):
        service.counterfactual_search("GP-001", request)


def test_http_analytics_are_scoped_and_serialized(tmp_path):
    app = create_app(provider_mode="fixture")
    app.state.extension_service.store = MemoryStore(tmp_path / "http.sqlite3")
    client = TestClient(app)
    summary = client.get("/portfolio/summary", params={"product": "EV_FINANCE"})
    assert summary.status_code == 200
    report = summary.json()
    assert report["analytics"]["decision_count"] == report["total_customers"]
    assert all(group["product"] == "EV_FINANCE" for group in report["analytics"]["physical_impact"]["groups"])
    trends = client.get("/portfolio/trends", params={"product": "EV_FINANCE"}).json()
    assert trends["analytics"]["observations"]
    assert all(row["product"] == "EV_FINANCE" for row in trends["analytics"]["observations"])
    empty = client.get("/portfolio/trends", params={"region": "missing"}).json()
    assert empty["analytics"]["observations"] == []


def test_http_counterfactual_contract_and_dispatch(service, monkeypatch):
    app = create_app(provider_mode="fixture")
    client = TestClient(app)
    payload = {"product": "EV_FINANCE", "candidates": {"annual_mileage_km": [1000]}}
    path = "/customers/GP-001/counterfactual-search"
    assert client.post(path, json=payload).status_code == 409
    assert client.post("/customers/missing/counterfactual-search", json=payload).status_code == 404
    assert client.post(path, json={**payload, "max_evaluations": 129}).status_code == 422
    calls = []
    monkeypatch.setattr(app.state.extension_service, "counterfactual_search",
                        lambda customer_id, request: calls.append((customer_id, request)) or {"evaluated_count": 1})
    assert client.post(path, json=payload).json() == {"evaluated_count": 1}
    assert calls[0][0] == "GP-001" and isinstance(calls[0][1], CounterfactualRequest)


def test_http_campaign_capacity_persists_and_closure_requires_permission(tmp_path, monkeypatch):
    database = tmp_path / "persistent.sqlite3"
    app = create_app(provider_mode="fixture")
    app.state.extension_service.store = MemoryStore(database)
    client = TestClient(app)
    for customer_id in ("GP-001", "GP-002"):
        assert client.post(f"/customers/{customer_id}/preferences",
                           json={"channel_consent": {"app": True}}).status_code == 200
    request = {"product": "EV_FINANCE", "channel_capacity": 1, "execute": True, "request_id": "first"}
    first = client.post("/campaigns/optimise", json=request).json()
    assert first["selected_count"] == 1
    campaign_id = first["campaign_event_id"]
    assert client.post("/campaigns/optimise", json=request).json() == first
    restarted = create_app(provider_mode="fixture")
    service = restarted.state.extension_service
    service.store = MemoryStore(database)
    second = deepcopy(service.opportunities(product=Product.EV_FINANCE, state="RECOMMEND")[0])
    second["customer_id"] = "GP-002"
    monkeypatch.setattr(service, "opportunities", lambda *args, **kwargs: [second])
    client = TestClient(restarted)
    blocked = client.post("/campaigns/optimise", json={**request, "request_id": "second"}).json()
    assert blocked["selected_count"] == 0 and blocked["capacity_budget"]["used"] == 1
    path = f"/campaigns/{campaign_id}/close"
    monkeypatch.delenv("GREENR_DEMO_ADMIN_TOKEN", raising=False)
    assert client.post(path, headers={"X-Demo-Admin-Token": "admin"}).status_code == 403
    monkeypatch.setenv("GREENR_DEMO_ADMIN_TOKEN", "admin")
    assert client.post(path).status_code == 403
    assert client.post(path, headers={"X-Demo-Admin-Token": "wrong"}).status_code == 403
    assert len(service.store.active_campaigns()) == 1
    headers = {"X-Demo-Admin-Token": "admin"}
    assert client.post("/campaigns/missing/close", headers=headers).status_code == 404
    assert client.post(f"/campaigns/{service.store.history('GP-001')[-1]['id']}/close", headers=headers).status_code == 404
    closed = client.post(path, headers=headers)
    assert closed.status_code == 200 and closed.json()["kind"] == "campaign_closed"
    assert closed.json()["campaign_id"] == campaign_id
    assert client.post(path, headers=headers).json() == closed.json()
    assert not service.store.active_campaigns()
    released = client.post("/campaigns/optimise", json={**request, "request_id": "after-close"}).json()
    assert released["selected_count"] == 1 and released["capacity_budget"]["used"] == 0
