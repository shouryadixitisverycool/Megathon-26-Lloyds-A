"""Fresh, isolated training through the public API, without keys or shipped artifacts."""

from collections import Counter
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from greenpath import config
from greenpath.api.main import create_app
from greenpath.contracts.product import RecommendationState as State
from greenpath.data_generation.__main__ import generate_dataset
from greenpath.impact import Product
from greenpath.pipelines import run


def test_fresh_small_training_api_acceptance(tmp_path, monkeypatch):
    # Use the production training and loading paths, not fake scores or a tuned
    # threshold. Keep every generated file outside the shared workspace.
    for name, path in {
        "REPO_ROOT": tmp_path, "DATA_DIR": tmp_path / "data",
        "RAW_DIR": tmp_path / "data" / "synthetic",
        "PERTURBED_DIR": tmp_path / "data" / "perturbed",
        "PROCESSED_DIR": tmp_path / "data" / "processed",
        "ARTIFACT_DIR": tmp_path / "data" / "artifacts",
        "REPORTS_DIR": tmp_path / "reports",
    }.items():
        monkeypatch.setattr(config, name, path)
    cutoffs = [date(2026, 5, 31), config.FEATURE_CUTOFF]
    monkeypatch.setattr(config, "TREND_CUTOFFS", cutoffs)
    monkeypatch.setattr(config, "TEMPORAL_HOLDOUT_CUTOFF", cutoffs[0])
    monkeypatch.setattr(run, "CATEGORISER_PATH", config.ARTIFACT_DIR / "transaction_categoriser.joblib")
    monkeypatch.setattr(run, "CATEGORISED_PATH", config.PROCESSED_DIR / "transactions_categorised.parquet")
    monkeypatch.setattr(run, "SPLIT_PATH", config.PROCESSED_DIR / "split_manifest.csv")
    monkeypatch.delenv("GREENPATH_LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("GREENPATH_PROVIDER", "trained")
    generate_dataset(customers=400)
    run.stage_train()

    with TestClient(create_app()) as client:
        repository = client.app.state.repository
        ev_input = repository.get_impact_input("C10001", Product.EV_FINANCE)
        ev_impact = repository.impact_calculators[Product.EV_FINANCE].calculate(ev_input)
        assert ev_impact.status == "AVAILABLE"
        assert any(e.basis == "SYNTHETIC_SCENARIO" for e in ev_impact.evidence)
        assert not repository.scenario_provider.get_scenario("C200001", Product.EV_FINANCE, config.FEATURE_CUTOFF)
        paperless_input = repository.get_impact_input("C10001", Product.PAPERLESS_BANKING)
        from greenpath.pipelines.scenario_provider import UKImpactInput
        # Ingestion delays leave an incomplete annual window; only an explicit forecast may fill it.
        source = paperless_input.snapshot
        assert source.data_quality.digital_months_present < 12
        incomplete = repository.impact_calculators[Product.PAPERLESS_BANKING].calculate(paperless_input)
        assert incomplete.status == "UNAVAILABLE"
        forecast = paperless_input.scenario[0].model_copy(update={"field": "annual_statements",
            "value": 12, "unit": "statements/year", "basis": "EXPLICIT_FORECAST",
            "description": "Caller-selected annual statement forecast, not measured"})
        paperless = repository.impact_calculators[Product.PAPERLESS_BANKING].calculate(
            UKImpactInput(snapshot=source, scenario=(*paperless_input.scenario, forecast)))
        assert paperless.status == "NOT_CLAIMED"
        assert paperless.secondary_metrics[1].value == 24
        assert any(e.basis == "EXPLICIT_FORECAST" for e in paperless.evidence)
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["provider_mode"] == "trained"
        assert health.json()["source_version"].startswith("trained:")
        customers_response = client.get("/customers")
        assert customers_response.status_code == 200
        customers = customers_response.json()
        assert len(customers) == 400 + len(config.DEMO_PERSONA_IDS)
        counts = Counter()
        by_product = {p.value: Counter() for p in Product}
        solar_reasons = Counter()
        solar_supported_probabilities = []
        abstention = None
        for customer in customers:
            customer_id = customer["customer_id"]
            assert customer["decision_profile"] == "trained"
            assert "marketing_consent" not in customer["features"]
            assert "paperless_consent" not in customer["features"]
            response = client.get(f"/customers/{customer_id}/recommendations")
            assert response.status_code == 200
            rows = response.json()["recommendations"]
            assert {r["product"] for r in rows} == {p.value for p in Product}
            for row in rows:
                counts[row["state"]] += 1
                by_product[row["product"]][row["state"]] += 1
                assert row["rules_version"] == "trained-relevance-rules-v1"
                assert any("absent permissions are not consent" in e for e in row["exclusions"])
                assert "not a credit eligibility" in row["eligibility_disclaimer"]
                propensity = row["propensity"]
                assert propensity is not None
                source = propensity["source_result"]
                assert source["customer_id"] == customer_id
                assert source["feature_cutoff"] == customer["feature_cutoff"][:10]
                assert propensity["model_version"] == source["model_version"]
                assert propensity["calibration_version"] == source["calibration_version"]
                bundle = client.app.state.repository.runtime.bundles[Product(row["product"])]
                assert Decimal(propensity["decision_threshold"]) == Decimal(str(bundle.threshold))
                assert propensity["in_model_population"] == source["in_model_population"]
                assert propensity["probability"] == (str(source["propensity"]) if source["in_model_population"] else None)
                # This runtime is too small to validate confidence. Never fabricate it.
                assert source["confidence"]["status"] == "SUPPRESSED"
                assert propensity["confidence"] is None
                assert propensity["confidence_validated"] is False
                if row["state"] == State.RECOMMEND.value:
                    assert Decimal(propensity["probability"]) >= Decimal(propensity["decision_threshold"])
                    assert row["trust"]["status"] == "TRUSTED"
                    assert row["reason_codes"] == ["RELEVANCE_SUPPORTED", "PROPENSITY_THRESHOLD_MET"]
                elif row["state"] == State.DO_NOT_RECOMMEND.value:
                    assert row["reason_codes"] == ["PROPENSITY_BELOW_THRESHOLD"]
                    assert Decimal(propensity["probability"]) < Decimal(str(bundle.threshold))
                elif row["state"] in {State.INSUFFICIENT_INFORMATION.value, State.CONFLICT_REQUIRES_REVIEW.value}:
                    abstention = row
                if row["product"] == Product.SOLAR_FINANCE.value:
                    solar_reasons.update(row["reason_codes"])
                    if row["state"] in {State.RECOMMEND.value, State.DO_NOT_RECOMMEND.value}:
                        solar_supported_probabilities.append(Decimal(propensity["probability"]))
                explanation_response = client.get(f"/customers/{customer_id}/explanations/{row['product']}")
                assert explanation_response.status_code == 200
                explanation = explanation_response.json()
                assert explanation["source"] == "template"
                assert explanation["fallback_reason"] == "PROVIDER_NOT_CONFIGURED"
                assert explanation["validation_passed"] is True
                assert explanation["state"] == row["state"]
                assert explanation["reason_codes"] == row["reason_codes"]
                assert explanation["impact_value"] == row["impact"]["value"]
        assert abstention is not None
        assert client.get("/customers/unknown/recommendations").status_code == 404
        assert client.get("/customers/unknown/explanations/SOLAR_FINANCE").status_code == 404

        summary_response = client.get("/portfolio/summary")
        assert summary_response.status_code == 200
        summary = summary_response.json()
        assert summary["total_customers"] == len(customers)
        assert summary["total_recommendations"] == len(customers) * len(Product)
        assert summary["state_counts"] == {s.value: counts[s.value] for s in State}
        assert summary["recommended_count"] == counts[State.RECOMMEND.value]
        assert summary["high_confidence_opportunities"] == summary["validated_confidence_opportunities"] == 0
        assert "No cross-product carbon total" in summary["disclaimer"]
        for opportunity in summary["product_opportunities"]:
            assert opportunity["state_counts"] == {s.value: by_product[opportunity["product"]][s.value] for s in State}

        trends_response = client.get("/portfolio/trends")
        assert trends_response.status_code == 200
        trends = trends_response.json()
        assert "not observed customer behavior" in trends["disclaimer"]
        assert len(trends["observations"]) == len(cutoffs) * len(Product)
        for point in trends["observations"]:
            assert point["customer_count"] == sum(point["state_counts"].values()) == len(customers)
            assert point["abstained_count"] == sum(point["state_counts"][s.value] for s in (
                State.INSUFFICIENT_INFORMATION, State.CONFLICT_REQUIRES_REVIEW, State.SUPPRESSED))
            assert point["average_validated_confidence"] is None
            assert point["validated_confidence_count"] == 0
            assert point["observed_outcome_count"] == 0
            assert point["observed_adoptions_90d"] is None
            if point["month"] == config.FEATURE_CUTOFF.strftime("%Y-%m"):
                assert point["state_counts"] == {s.value: by_product[point["product"]][s.value] for s in State}
        metrics = client.get("/explanations/metrics").json()
        assert metrics["provider_attempts"] == 0
        assert metrics["offline_cost"] == 0
        # Recommendation volume, including zero Solar recommendations, is not
        # an acceptance criterion. Calibrated evidence and abstention are.
        print("Fresh trained API state counts:", by_product)
        print("Solar reasons:", solar_reasons, "threshold:",
              client.app.state.repository.runtime.bundles[Product.SOLAR_FINANCE].threshold,
              "maximum otherwise-supported probability:", max(solar_supported_probabilities, default=None))
