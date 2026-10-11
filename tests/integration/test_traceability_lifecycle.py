"""Immutable served decisions and authorized source-driven model lifecycle."""

from decimal import Decimal
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from greenr.api.main import create_app
from greenr.contracts.enums import Product
from greenr.contracts.customer import CustomerSnapshot
from greenr.contracts.trust import TrustAssessment
from greenr.contracts.fixtures import load_model
from greenr.demo.artifacts import ArtifactRepository
from greenr.extensions.store import MemoryStore
from greenr.models.propensity import ModelPropensityProvider, train_product


@pytest.fixture(scope="module")
def bundles():
    source = load_model("customer_snapshot_C10001", CustomerSnapshot)
    rng = np.random.default_rng(41)
    frame = pd.DataFrame([source.features] * 600)
    frame["annual_mileage_km"] = rng.uniform(1000, 100000, len(frame))
    for field in ("holds_ev_finance", "holds_green_home_loan", "holds_solar_finance", "has_existing_solar", "is_paperless"):
        frame[field] = 0
    probability = 1 / (1 + np.exp(3 - frame["annual_mileage_km"] / 18000))
    labels = pd.DataFrame({p.value: (rng.random(len(frame)) < probability).astype(int) for p in Product})
    split = pd.Series(["train"] * 360 + ["validation"] * 120 + ["test"] * 120)
    return {p: train_product(frame, labels, split, p) for p in Product}


def runtime(bundles):
    source = load_model("customer_snapshot_C10001", CustomerSnapshot)
    trust = load_model("trust_assessment_C10001_EV", TrustAssessment)
    return SimpleNamespace(bundles=bundles, propensity=ModelPropensityProvider(bundles),
        snapshots=SimpleNamespace(default_cutoff=source.feature_cutoff, cutoffs=[source.feature_cutoff],
                                  snapshots=lambda cutoff: [source]),
        trust=SimpleNamespace(assess_many=lambda sources, product: [trust.model_copy(update={"product": product}) for s in sources]))


def update(**changes):
    return {"request_id": "source-1", "actor": "local-demo-admin", "reason": "Verified synthetic source record",
            "source_reference": "demo:digital:1", "event_at": "2026-06-30T00:00:00Z",
            "available_at": "2026-06-30T00:00:00Z", "feature_cutoff": "2026-06-30T00:00:00Z", **changes}


def rows(client, customer="C10001"):
    response = client.get(f"/customers/{customer}/recommendations")
    assert response.status_code == 200, response.text
    return {r["product"]: r for r in response.json()["recommendations"]}


def test_every_served_decision_is_durable_and_explanation_runs_are_linked(tmp_path):
    path = tmp_path / "memory.sqlite3"
    app = create_app(provider_mode="fixture", memory_path=path)
    with TestClient(app) as client:
        first = rows(client, "GP-001")["EV_FINANCE"]
        assert first["decision_id"].startswith("decision-")
        assert rows(client, "GP-001")["EV_FINANCE"] == first
        assert client.get("/audit/recommendations/" + first["decision_id"]).json()["propensity"] == first["propensity"]
        explanation = client.get("/customers/GP-001/explanations/EV_FINANCE")
        assert explanation.status_code == 200
        audit = client.get("/audit/recommendations/" + first["decision_id"]).json()
        assert audit["provenance"]["snapshot"]["customer_id"] == "GP-001"
        assert audit["explanations"][0]["prompt_version"]
        assert audit["explanations"][0]["explanation"] == explanation.json()
        assert len(client.get("/customers/GP-001/history").json()["recommendations"]) == 4
    with TestClient(create_app(provider_mode="fixture", memory_path=path)) as client:
        assert rows(client, "GP-001")["EV_FINANCE"] == first
    store = MemoryStore(path)
    rec = app.state.recommendation_service.recommendations("GP-001")[0]
    with pytest.raises(ValueError, match="immutable evidence"):
        store.save_recommendation(rec.model_copy(update={"reason_codes": ("CHANGED",)}))
    assert store.get_recommendation(first["decision_id"])["reason_codes"] == first["reason_codes"]


def test_factual_update_reruns_deployed_models_and_survives_restart(bundles, tmp_path, monkeypatch):
    monkeypatch.setenv("GREENR_DEMO_ADMIN_TOKEN", "test-admin")
    path = tmp_path / "memory.sqlite3"
    repo = ArtifactRepository(runtime(bundles))
    app = create_app(repo, memory_path=path)
    headers = {"X-Demo-Admin-Token": "test-admin"}
    request = update(vehicle={"annual_mileage_km": 90000}, digital={"is_paperless": True}, ownership={"home_owner": False})
    with TestClient(app) as client:
        before = rows(client)
        history = repo.list_history()
        result = client.post("/customers/C10001/source-updates", json=request, headers=headers)
        assert result.status_code == 200, result.text
        assert result.json()["lifecycle_state"] == "CLOSED"
        after = rows(client)
        source = repo.get_snapshot("C10001").source_snapshot
        expected = repo.runtime.propensity.score(source, Product.EV_FINANCE)
        assert Decimal(after["EV_FINANCE"]["propensity"]["probability"]) == Decimal(str(expected.propensity))
        assert after["EV_FINANCE"]["propensity"]["probability"] != before["EV_FINANCE"]["propensity"]["probability"]
        assert after["GREEN_HOME"]["state"] == "NOT_APPLICABLE"
        assert after["PAPERLESS_BANKING"]["state"] == "NOT_APPLICABLE"
        assert after["PAPERLESS_BANKING"]["propensity"]["probability"] is None
        assert source.features["is_paperless"] is True and source.features["home_owner"] is False
        assert len(repo.source_snapshot_history("C10001")) == 2
        assert repo.list_history() == history
        provenance = after["EV_FINANCE"]["provenance"]
        assert provenance["snapshot"]["source_snapshot"]["source_versions"]["digital"].startswith("local-demo:")
        assert provenance["snapshot"]["source_snapshot"]["source_events"][0]["available_at"]
        assert client.get("/audit/recommendations/" + before["EV_FINANCE"]["decision_id"]).json()["propensity"] == before["EV_FINANCE"]["propensity"]
        assert client.post("/customers/C10001/source-updates", json=request, headers=headers).json() == result.json()
        assert client.post("/customers/C10001/source-updates", json={**request, "reason": "Different"}, headers=headers).status_code == 409
        assert len(client.get("/customers/C10001/history").json()["source_updates"]) == 1
    fresh = ArtifactRepository(runtime(bundles))
    with TestClient(create_app(fresh, memory_path=path)) as client:
        assert rows(client) == after
        assert fresh.get_snapshot("C10001").source_snapshot.digital.is_paperless is True


def test_feedback_completion_is_not_factual_paperless_closure(bundles, tmp_path):
    repo = ArtifactRepository(runtime(bundles))
    with TestClient(create_app(repo, memory_path=tmp_path / "memory.sqlite3")) as client:
        before = rows(client)["PAPERLESS_BANKING"]
        response = client.post("/feedback", json={"customer_id": "C10001", "product": "PAPERLESS_BANKING",
                                                  "response": "ALREADY_COMPLETED", "request_id": "claim"})
        assert response.status_code == 200
        assert response.json()["lifecycle_state"] != "CLOSED"
        assert client.post("/feedback", json={"customer_id": "C10001", "product": "PAPERLESS_BANKING",
                                              "response": "CLOSED", "request_id": "claim-close"}).status_code == 409
        assert rows(client)["PAPERLESS_BANKING"] == before
        assert not repo.get_snapshot("C10001").source_snapshot.digital.is_paperless
        assert client.get("/customers/C10001/history").json()["source_updates"] == []


@pytest.mark.parametrize("changes,code", [
    ({"digital": {"is_paperless": True}}, 403),
    ({"digital": {"propensity": 1}}, 409),
    ({"digital": {"is_paperless": "true"}}, 409),
    ({"digital": {"paper_statements_3m": -1}}, 422),
    ({"digital": {"is_paperless": True}, "available_at": "2026-07-01T00:00:00Z"}, 422),
    ({"digital": {"is_paperless": True}, "feature_cutoff": "2099-01-01T00:00:00Z"}, 422),
])
def test_source_updates_fail_closed(bundles, tmp_path, monkeypatch, changes, code):
    monkeypatch.setenv("GREENR_DEMO_ADMIN_TOKEN", "test-admin")
    repo = ArtifactRepository(runtime(bundles))
    with TestClient(create_app(repo, memory_path=tmp_path / "memory.sqlite3")) as client:
        before = rows(client)
        headers = {} if code == 403 else {"X-Demo-Admin-Token": "test-admin"}
        response = client.post("/customers/C10001/source-updates", json=update(**changes), headers=headers)
        assert response.status_code == code, response.text
        assert rows(client) == before


def test_failed_rescore_rolls_back_source_decisions_and_history(bundles, tmp_path, monkeypatch):
    monkeypatch.setenv("GREENR_DEMO_ADMIN_TOKEN", "test-admin")
    repo = ArtifactRepository(runtime(bundles))
    app = create_app(repo, memory_path=tmp_path / "memory.sqlite3")
    with TestClient(app, raise_server_exceptions=False) as client:
        before = rows(client)
        original = repo.runtime.propensity.score_many

        def fail_on_updated_source(sources, product):
            if sources[0].digital.is_paperless:
                raise RuntimeError("Injected scoring failure")
            return original(sources, product)

        monkeypatch.setattr(repo.runtime.propensity, "score_many", fail_on_updated_source)
        response = client.post("/customers/C10001/source-updates", json=update(digital={"is_paperless": True}),
                               headers={"X-Demo-Admin-Token": "test-admin"})
        assert response.status_code == 500
        assert rows(client) == before
        assert app.state.memory_store.source_updates("C10001") == []
        assert len(app.state.memory_store.recommendation_history("C10001")) == 4
        assert len(repo.source_snapshot_history("C10001")) == 1
        assert not repo.get_snapshot("C10001").source_snapshot.digital.is_paperless


def test_shap_and_portfolio_filters_are_exposed(bundles, tmp_path):
    with TestClient(create_app(ArtifactRepository(runtime(bundles)), memory_path=tmp_path / "memory.sqlite3")) as client:
        shap = client.get("/customers/C10001/shap/EV_FINANCE")
        assert shap.status_code == 200
        assert shap.json()["output_space"] == "raw_uncalibrated_log_odds"
        assert abs(shap.json()["rows"][0]["additivity_residual"]) < 2e-5
        filtered = client.get("/portfolio/opportunities", params={"min_confidence": .9, "min_impact": 100, "data_quality": "TRUSTED"})
        assert filtered.status_code == 200 and filtered.json()["opportunities"] == []


def test_persistent_campaign_capacity_helpers(tmp_path):
    store = MemoryStore(tmp_path / "memory.sqlite3")
    campaign = store.append("PORTFOLIO", "EV_FINANCE", "campaign", {"channel": "app", "request_id": "campaign"},
                            {"result": {"executed": True, "selected_count": 3}})
    assert store.remaining_campaign_capacity("app", 5) == 2
    assert store.remaining_campaign_capacity("app", 5, max_active_campaigns=1) == 0
    store.append("PORTFOLIO", "EV_FINANCE", "campaign_closed", {}, {"campaign_id": campaign["id"]})
    assert MemoryStore(store.path).remaining_campaign_capacity("app", 5, max_active_campaigns=1) == 5
