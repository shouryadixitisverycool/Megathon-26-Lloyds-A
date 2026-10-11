import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import httpx
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from greenr.contracts.product import PropensityResult
from greenr.contracts.propensity import PropensityResult as ScoringResult
from greenr.demo.providers import DemoRepository
from greenr.demo.readiness import generate_readiness, read_report, report_hash
from greenr.impact import Product


def test_fixtures_are_blocked_with_actual_states_and_no_confidence():
    repository = DemoRepository()
    report = generate_readiness(repository)
    assert report["status"] == "BLOCKED"
    assert report["population_customers"] == 6
    assert report["examples"]["abstention"]["customer_id"] == "GP-002"
    assert report["examples"]["conflict"]["state"] == "CONFLICT_REQUIRES_REVIEW"
    assert report["examples"]["already_adopted"]["reason_codes"] == ["ALREADY_ADOPTED"]
    for entry in report["products"].values():
        assert entry["status"] == "BLOCKED"
        assert entry["coverage"]["validated_confidence"] == 0
        assert entry["candidate"]["propensity"]["confidence"] is None
        assert "Fixture" in entry["confidence_limitation"]
    assert generate_readiness(repository) == report


def test_report_rejects_stale_artifacts_and_modified_content(tmp_path, monkeypatch):
    monkeypatch.setattr("greenr.demo.readiness.confidence_decisions_hash", lambda: None)
    report = generate_readiness(DemoRepository())
    path = tmp_path / "readiness.json"
    path.write_text(json.dumps(report))
    assert read_report(path, report["artifact_signature"]) == report
    assert read_report(path, "different-loaded-models") is None
    report["status"] = "READY"
    path.write_text(json.dumps(report))
    assert read_report(path, report["artifact_signature"]) is None
    report["report_sha256"] = report_hash(report)
    path.write_text(json.dumps(report))
    monkeypatch.setattr("greenr.demo.readiness.confidence_decisions_hash", lambda: "new-release-decision")
    assert read_report(path, report["artifact_signature"]) is None


def test_artifact_shortlist_does_not_turn_claimed_confidence_into_ready():
    repository = DemoRepository()
    repository.mode = "trained"
    repository._cache = {"already_loaded": True}
    repository.runtime = SimpleNamespace(
        snapshots=SimpleNamespace(default_cutoff=date(2026, 1, 3)),
        confidence=SimpleNamespace(limitations={p: "Insufficient release-selection rows: 128 < 200" for p in Product},
                                   validated={p: False for p in Product}),
    )
    scores = pd.DataFrame([{"cutoff": "2026-01-03", "customer_id": cid, "product": p.value,
                            "in_model_population": True, "above_threshold": True,
                            "confidence_status": "VALIDATED", "trust_status": "TRUSTED"}
                           for cid in ("GP-003", "GP-001", "GP-002") for p in Product])
    first = generate_readiness(repository, scored=scores, signature="loaded-signature")
    second = generate_readiness(repository, scored=scores.iloc[::-1], signature="loaded-signature")
    assert first == second
    assert first["status"] == "BLOCKED"
    assert all(entry["candidate"]["propensity"]["confidence_validated"] is False
               for entry in first["products"].values())


def test_confidence_limitation_is_derived_not_accepted_from_caller():
    result = PropensityResult(product=Product.EV_FINANCE, model_version="fixture",
                              confidence_limitation="Everything passed")
    assert "no validated confidence" in result.confidence_limitation
    assert PropensityResult.model_validate(result.model_dump()).confidence_limitation == result.confidence_limitation


def test_ready_requires_live_validated_source_and_available_impact():
    repository = DemoRepository()
    repository.mode = "trained"
    repository._cache = {"loaded": True}
    repository.runtime = SimpleNamespace(
        snapshots=SimpleNamespace(default_cutoff=date(2026, 1, 3)),
        confidence=SimpleNamespace(limitations={}, validated={p: True for p in Product}),
    )
    for product in Product:
        source = ScoringResult.model_validate({
            "customer_id": "GP-001", "product": product.value, "propensity": 0.82, "raw_score": 0.7,
            "model_type": "LOGISTIC", "model_version": "test-trained-model", "calibration_method": "sigmoid",
            "calibration_version": "test-calibration", "feature_version": "test-features", "feature_cutoff": "2026-01-03",
            "outcome_window_end": "2026-04-03", "prediction_timestamp": "2026-01-03T00:00:00Z",
            "in_model_population": True, "confidence": {"status": "VALIDATED", "value": 0.9,
                "bucket": "HIGH", "method_version": "test-confidence"},
        })
        repository._propensities[("GP-001", product)] = PropensityResult(
            product=product, probability="0.82", model_version=source.model_version,
            calibration_version=source.calibration_version, confidence="0.9", confidence_validated=True,
            source_result=source,
        )
    scores = pd.DataFrame([{"cutoff": "2026-01-03", "customer_id": "GP-001", "product": p.value,
                            "in_model_population": True, "above_threshold": True,
                            "confidence_status": "VALIDATED", "trust_status": "TRUSTED"} for p in Product])
    report = generate_readiness(repository, scored=scores, signature="test-loaded-artifacts")
    assert report["products"]["EV_FINANCE"]["status"] == "READY"
    assert report["products"]["EV_FINANCE"]["candidate"]["propensity"]["confidence"] == "0.9"
    assert report["products"]["PAPERLESS_BANKING"]["status"] == "BLOCKED"
    assert report["status"] == "BLOCKED"


def test_endpoint_uses_raw_service_and_caches_scan(tmp_path, monkeypatch):
    monkeypatch.setenv("GREENR_PROVIDER", "fixture")
    from greenr.api.main import create_app
    from greenr.recommendation.service import RecommendationService
    from greenr.extensions.store import MemoryStore

    repository = DemoRepository()
    calls = []
    domain_service = RecommendationService(repository, repository, repository)

    class Service:
        def recommendations(self, cid):
            calls.append(cid)
            return domain_service.recommendations(cid)

    def forbidden(*args, **kwargs):
        pytest.fail("Readiness must not persist recommendations or call explanations")

    monkeypatch.setattr(MemoryStore, "save_recommendation", forbidden)
    monkeypatch.setattr("greenr.demo.readiness.REPORT_PATH", tmp_path / "missing.json")
    application = create_app(repository, recommendation_service=Service(),
                             explanation_service=SimpleNamespace(explain=forbidden),
                             memory_path=tmp_path / "memory.sqlite3")
    client = TestClient(application)
    first = client.get("/demo/readiness")
    assert first.status_code == 200
    assert first.json()["status"] == "BLOCKED"
    assert len(calls) == 6
    assert client.get("/demo/readiness").json() == first.json()
    assert len(calls) == 6


def test_manifest_shortcut_and_specific_suppression(api_fixture, monkeypatch):
    for row in api_fixture["decisions"]["GP-003"]:
        row["propensity"]["confidence_limitation"] = "Release validation has 128 rows; 200 required."

    def get(url, **kwargs):
        if url.endswith("/demo/readiness"):
            return httpx.Response(200, request=httpx.Request("GET", url), json={
                "status": "BLOCKED", "population_customers": 6,
                "products": {"EV_FINANCE": {"status": "BLOCKED", "candidate": None,
                    "missing_features": ["Release validation has 128 rows; 200 required."]}},
                "examples": {"conflict": {"customer_id": "GP-003", "product": "SOLAR_FINANCE", "state": "CONFLICT_REQUIRES_REVIEW"}},
                "missing_features": ["No validated green-home candidate."],
            })
        return api_fixture["get"](url, **kwargs)

    monkeypatch.setattr(httpx, "get", get)
    app_path = Path(__file__).resolve().parents[3] / "src/greenr/app/main.py"
    app = AppTest.from_file(str(app_path), default_timeout=15).run()
    assert not app.exception
    app.button(key="open_showcase").click().run()
    assert not app.exception
    assert app.selectbox(key="customer_id").value == "GP-003"
    assert app.selectbox(key="why_product").value == "SOLAR_FINANCE"
    captions = "\n".join(str(row.value) for row in app.caption)
    assert "Release validation has 128 rows; 200 required." in captions
    assert "99.0%" not in captions
    assert "No validated green-home candidate." in "\n".join(str(row.value) for row in app.sidebar.caption)
