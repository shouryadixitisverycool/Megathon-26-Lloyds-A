"""Exercise the HTTP boundary with independent fake providers and services."""

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from greenpath.contracts.product import (
    CONTRACT_VERSION,
    CustomerSnapshot,
    Explanation,
    HistoryRecord,
    PropensityResult,
    Recommendation,
    RecommendationState,
    TrustAssessment,
)
from greenpath.api.main import create_app
from greenpath.impact import Product, build_registry


API_NOW = datetime(2026, 1, 3, tzinfo=timezone.utc)
API_STATES = tuple(RecommendationState)


class FakeRepository:
    def __init__(self):
        self.snapshots = tuple(
            CustomerSnapshot(
                customer_id=f"fake-{index}", display_name=f"Person {index}",
                region="South" if index < 3 else "North",
                segment="Salaried" if index % 2 == 0 else "Retired",
                feature_cutoff=API_NOW, features={},
                trust=TrustAssessment(score=Decimal("0.75"), status="LIMITED"),
            )
            for index in range(6)
        )
        self.history = tuple(
            HistoryRecord(customer_id=snapshot.customer_id, month=month, product=product, state=state)
            for index, snapshot in enumerate(self.snapshots)
            for month, state in (("2025-10", RecommendationState.SUPPRESSED), ("2025-12", API_STATES[index]))
            for product in Product
        )
        self.history_calls = 0

    def list_snapshots(self):
        return self.snapshots

    def get_snapshot(self, customer_id):
        return next((item for item in self.snapshots if item.customer_id == customer_id), None)

    def list_history(self):
        self.history_calls += 1
        return self.history


class FakeRecommendationService:
    def __init__(self, repository):
        self.calls = []
        calculators = build_registry(clock=lambda: API_NOW)
        fixture_root = Path(__file__).parents[1] / "impact" / "fixtures"
        files = {
            Product.EV_FINANCE: "ev.json", Product.GREEN_HOME: "green_home.json",
            Product.SOLAR_FINANCE: "solar.json", Product.PAPERLESS_BANKING: "paperless.json",
        }
        self.results = {}
        for index, snapshot in enumerate(repository.list_snapshots()):
            self.results[snapshot.customer_id] = tuple(
                Recommendation(
                    customer_id=snapshot.customer_id, product=product,
                    propensity=PropensityResult(
                        product=product, probability=Decimal("0.82"), model_version="fake-v1",
                    ),
                    state=API_STATES[index], reason_codes=("FAKE_EVIDENCE",), evidence=(),
                    impact=calculators[product].calculate(json.loads((fixture_root / files[product]).read_text())),
                    trust=snapshot.trust, feature_cutoff=API_NOW, rules_version="fake-rules-v1", timestamp=API_NOW,
                )
                for product in Product
            )

    def recommendations(self, customer_id):
        self.calls.append(customer_id)
        return self.results[customer_id]


class FakeExplanationService:
    def __init__(self):
        self.calls = []

    def explain(self, recommendation):
        self.calls.append(recommendation)
        return Explanation(
            customer_id=recommendation.customer_id, product=recommendation.product,
            state=recommendation.state, text="A controlled test explanation.",
            reason_codes=recommendation.reason_codes, impact_value=recommendation.impact.value,
            units=recommendation.impact.units, source="template", provider_version="fake-template-v1",
            validation_passed=True,
        )


@pytest.fixture
def api_fixture():
    repository = FakeRepository()
    recommendation_service = FakeRecommendationService(repository)
    explanation_service = FakeExplanationService()
    application = create_app(
        snapshot_provider=repository, history_provider=repository,
        recommendation_service=recommendation_service, explanation_service=explanation_service,
    )
    with TestClient(application) as client:
        yield client, repository, recommendation_service, explanation_service


def test_health_and_snapshot_decimal_serialization(api_fixture):
    client, _, _, _ = api_fixture
    assert client.get("/health").json() == {
        "status": "ok", "synthetic_demo": True, "contract_version": CONTRACT_VERSION,
        "provider_mode": "injected", "source_version": "injected-provider",
    }
    customers = client.get("/customers").json()
    assert len(customers) == 6
    assert customers[0]["trust"]["score"] == "0.75"
    assert client.get("/customers/fake-0").json() == customers[0]


def test_partner_catalogue_is_public_editorial_content_without_scoring(api_fixture, monkeypatch):
    monkeypatch.delenv("GREENPATH_PARTNER_CATALOGUE", raising=False)
    client, _, recommendations, explanations = api_fixture
    response = client.get("/partners/catalogue")
    assert response.status_code == 200
    catalogue = response.json()
    assert {category["product"] for category in catalogue["products"]} == {"EV_FINANCE", "SOLAR_FINANCE", "GREEN_HOME"}
    for category in catalogue["products"]:
        assert len(category["options"]) == 2
        assert all(option["placeholder"] and option["promoted"] for option in category["options"])
        assert all(option["destination_url"] is None and option["source"] is None for option in category["options"])
    assert "customer_id" not in response.text
    assert not recommendations.calls
    assert not explanations.calls
    assert client.post("/partners/catalogue", json={"request_id": "no-lead"}).status_code == 405


def test_operator_can_choose_exactly_which_partner_products_are_promoted(api_fixture, monkeypatch, tmp_path):
    monkeypatch.delenv("GREENPATH_PARTNER_CATALOGUE", raising=False)
    client, _, recommendations, _ = api_fixture
    catalogue = client.get("/partners/catalogue").json()
    hidden = catalogue["products"][0]["options"][0]
    hidden["promoted"] = False
    selected = catalogue["products"][0]["options"][1]
    selected["title"] = "Operator-selected partner product"
    path = tmp_path / "selected-products.json"
    path.write_text(json.dumps(catalogue))
    monkeypatch.setenv("GREENPATH_PARTNER_CATALOGUE", str(path))
    response = client.get("/partners/catalogue")
    assert response.status_code == 200
    options = response.json()["products"][0]["options"]
    assert [option["id"] for option in options] == [selected["id"]]
    assert options[0]["title"] == selected["title"]
    assert hidden["id"] not in response.text
    assert not recommendations.calls


@pytest.mark.parametrize("contents", [None, "not valid json", "{}"])
def test_unavailable_partner_catalogue_does_not_block_customer_evidence(api_fixture, monkeypatch, tmp_path, contents):
    catalogue = tmp_path / "operator-catalogue.json"
    if contents is not None:
        catalogue.write_text(contents)
    monkeypatch.setenv("GREENPATH_PARTNER_CATALOGUE", str(catalogue))
    client, _, _, _ = api_fixture
    response = client.get("/partners/catalogue")
    assert response.status_code == 503
    assert "Customer evidence remains available" in response.json()["detail"]
    assert str(catalogue) not in response.text
    assert client.get("/customers/fake-0/recommendations").status_code == 200


def test_recommendations_alias_preserves_contract_and_numbers(api_fixture):
    client, _, _, _ = api_fixture
    response = client.get("/customers/fake-0/recommendations")
    assert response.status_code == 200
    assert response.json() == client.get("/customers/fake-0/opportunities").json()
    decisions = response.json()["recommendations"]
    assert len(decisions) == 4
    assert decisions[0]["propensity"]["probability"] == "0.82"
    assert isinstance(decisions[0]["impact"]["value"], str)
    assert Decimal(decisions[0]["impact"]["value"]) == Decimal("553.194")
    assert all(item["contract_version"] == CONTRACT_VERSION for item in decisions)
    assert all(item["synthetic_demo"] is True for item in decisions)
    assert all("not a credit eligibility" in item["eligibility_disclaimer"] for item in decisions)
    assert decisions[-1]["impact"]["value"] is None


@pytest.mark.parametrize("suffix", ["", "/recommendations", "/opportunities", "/explanations/EV_FINANCE"])
def test_unknown_customer_returns_404(api_fixture, suffix):
    client, _, service, explanation = api_fixture
    response = client.get(f"/customers/unknown{suffix}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Customer not found"}
    assert not service.calls
    assert not explanation.calls


def test_explanation_calls_injected_service_for_requested_product(api_fixture):
    client, _, _, service = api_fixture
    response = client.get("/customers/fake-0/explanations/GREEN_HOME")
    assert response.status_code == 200
    assert response.json()["product"] == "GREEN_HOME"
    assert isinstance(response.json()["impact_value"], str)
    assert Decimal(response.json()["impact_value"]) == Decimal("716")
    assert len(service.calls) == 1
    assert service.calls[0].product == Product.GREEN_HOME


@pytest.mark.parametrize("path", [
    "/portfolio/summary?product=invalid", "/portfolio/trends?product=invalid",
    "/customers/fake-0/explanations/invalid",
])
def test_invalid_product_returns_422(api_fixture, path):
    client, _, service, _ = api_fixture
    assert client.get(path).status_code == 422
    assert not service.calls


def test_summary_all_states_coverage_and_no_carbon_sum(api_fixture):
    client, _, service, _ = api_fixture
    response = client.get("/portfolio/summary").json()
    assert response["total_customers"] == 6
    assert response["total_recommendations"] == 24
    assert response["recommended_count"] == 4
    assert response["state_counts"] == {state.value: 4 for state in API_STATES}
    assert response["available_impact_count"] == 3
    assert len(response["product_opportunities"]) == 4
    assert all(item["total"] == 6 and item["recommended"] == 1 for item in response["product_opportunities"])
    assert sum(item["available_impact_count"] for item in response["product_opportunities"]) == 3
    assert response["region_summaries"] == [
        {"name": "North", "customer_count": 3, "recommended_count": 0},
        {"name": "South", "customer_count": 3, "recommended_count": 4},
    ]
    assert len(service.calls) == 6
    assert not any("carbon" in key or "impact_value" in key for key in response)


def test_summary_intersects_all_three_filters(api_fixture):
    client, _, service, _ = api_fixture
    response = client.get("/portfolio/summary?region=South&segment=Salaried&product=EV_FINANCE").json()
    assert response["total_customers"] == 2
    assert response["total_recommendations"] == 2
    assert response["recommended_count"] == 1
    assert response["available_impact_count"] == 1
    assert len(response["product_opportunities"]) == 1
    assert len(response["state_counts"]) == 6
    assert response["state_counts"]["INSUFFICIENT_INFORMATION"] == 1
    assert response["region_summaries"] == [{"name": "South", "customer_count": 2, "recommended_count": 1}]
    assert response["segment_summaries"] == [{"name": "Salaried", "customer_count": 2, "recommended_count": 1}]
    assert service.calls == ["fake-0", "fake-2"]


def test_empty_cohort_summary_and_trends(api_fixture):
    client, _, service, _ = api_fixture
    summary = client.get("/portfolio/summary?region=missing").json()
    assert summary["total_customers"] == summary["total_recommendations"] == 0
    assert summary["state_counts"] == {state.value: 0 for state in API_STATES}
    assert len(summary["product_opportunities"]) == 4
    assert summary["region_summaries"] == summary["segment_summaries"] == []
    assert client.get("/portfolio/trends?segment=missing").json()["observations"] == []
    assert not service.calls


def test_trends_use_history_and_keep_missing_month_absent(api_fixture):
    client, repository, service, _ = api_fixture
    response = client.get("/portfolio/trends").json()
    assert repository.history_calls == 1
    assert not service.calls
    observations = response["observations"]
    assert len(observations) == 8
    assert {item["month"] for item in observations} == {"2025-10", "2025-12"}
    for item in observations:
        assert item["customer_count"] == 6
        assert sum(item["state_counts"].values()) == 6
        assert len(item["state_counts"]) == 6
        assert item["recommended_count"] == (0 if item["month"] == "2025-10" else 1)


def test_trends_intersect_filters_and_ignore_orphan_history(api_fixture):
    client, repository, service, _ = api_fixture
    repository.history += (HistoryRecord(
        customer_id="unknown", month="2025-09", product=Product.EV_FINANCE, state=RecommendationState.RECOMMEND,
    ),)
    observations = client.get("/portfolio/trends?region=South&segment=Salaried&product=EV_FINANCE").json()["observations"]
    assert len(observations) == 2
    assert all(item["product"] == "EV_FINANCE" and item["customer_count"] == 2 for item in observations)
    assert observations[0]["state_counts"]["SUPPRESSED"] == 2
    assert observations[1]["recommended_count"] == 1
    assert not service.calls


def test_duplicate_history_counts_once_and_conflicts_fail_closed(api_fixture):
    client, repository, _, _ = api_fixture
    record = repository.history[0]
    repository.history += (record,)
    observations = client.get("/portfolio/trends").json()["observations"]
    assert all(item["customer_count"] == sum(item["state_counts"].values()) == 6 for item in observations)
    repository.history += (record.model_copy(update={"state": RecommendationState.RECOMMEND}),)
    with pytest.raises(ValueError, match="Conflicting historical states"):
        client.get("/portfolio/trends")


def test_repository_injection_is_equivalent_to_narrow_provider_injection(api_fixture):
    _, repository, recommendations, explanations = api_fixture
    with TestClient(create_app(repository, recommendation_service=recommendations, explanation_service=explanations)) as client:
        assert len(client.get("/customers").json()) == 6
        assert client.get("/portfolio/summary").json()["recommended_count"] == 4


def test_unknown_customer_keyerror_from_provider_becomes_404(api_fixture):
    _, repository, recommendations, explanations = api_fixture

    def lookup_raises(customer_id):
        raise KeyError(customer_id)

    repository.get_snapshot = lookup_raises
    with TestClient(create_app(repository, recommendation_service=recommendations, explanation_service=explanations)) as client:
        assert client.get("/customers/unknown").status_code == 404


def test_missing_service_customer_and_missing_product_become_404(api_fixture):
    client, _, service, explanation = api_fixture
    service.results.pop("fake-1")
    assert client.get("/customers/fake-1/recommendations").status_code == 404
    service.results["fake-0"] = tuple(item for item in service.results["fake-0"] if item.product != Product.GREEN_HOME)
    assert client.get("/customers/fake-0/explanations/GREEN_HOME").status_code == 404
    assert not explanation.calls


def test_default_demo_wires_real_services_and_explicit_history():
    with TestClient(create_app(provider_mode="fixture")) as client:
        customers = client.get("/customers").json()
        assert {item["customer_id"] for item in customers} == {f"GP-00{index}" for index in range(1, 7)}
        summary = client.get("/portfolio/summary").json()
        assert summary["total_recommendations"] == 24
        assert summary["state_counts"] == {state.value: 4 for state in API_STATES}
        assert summary["available_impact_count"] == 3
        explanation = client.get("/customers/GP-001/explanations/EV_FINANCE").json()
        assert explanation["source"] == "template"
        assert explanation["validation_passed"] is True
        observations = client.get("/portfolio/trends?region=South&segment=Salaried&product=EV_FINANCE").json()["observations"]
        assert [item["month"] for item in observations] == ["2025-10", "2025-11", "2025-12"]
        assert [item["recommended_count"] for item in observations] == [0, 0, 1]
