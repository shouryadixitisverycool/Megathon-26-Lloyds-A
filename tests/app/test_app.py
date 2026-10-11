from pathlib import Path

import httpx
import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[2] / "src/greenr/app/main.py"


def start():
    app = AppTest.from_file(str(APP), default_timeout=15).run()
    assert not app.exception
    return app


def displayed(app):
    return "\n".join(str(element.value) for kind in (app.caption, app.markdown, app.text, app.info, app.warning) for element in kind)


def test_customer_cards_and_http_only_why(api_fixture):
    app = start()
    assert app.header[0].value == "Person 1"
    assert any(metric.value == "82.0%" for metric in app.metric)
    text = displayed(app)
    for expected in ["Synthetic demo", "Model confidence: Unavailable", "fixture-model-v1", "fixture-calibration-v1",
                     "fixture-rules-v1", "fixture-trust-v1", "fixture-contract-v1", "fixture-method-v1",
                     "Operational energy CO2 only", "Manufacture and disposal excluded", "-12.50 kg CO2/year",
                     "UNAVAILABLE", "not credit eligibility", "2026-01-03"]:
        assert expected in text
    assert any("References" in frame.value and "fixture:ownership" in list(frame.value["References"]) for frame in app.dataframe)
    assert "99.0%" not in text
    assert ("/customers/GP-001/explanations/EV_FINANCE", {}) in api_fixture["calls"]
    app.selectbox(key="why_product").select("PAPERLESS_BANKING").run()
    assert not app.exception
    assert "Potential impact · UNAVAILABLE" in [row.value for row in app.subheader]
    assert any("Missing defensible activity" in row.value for row in app.warning)


def test_trained_source_and_default_customer_do_not_depend_on_api_order(api_fixture, monkeypatch):
    customer = api_fixture["customers"][0]
    customer["customer_id"] = "C10001"
    api_fixture["decisions"]["C10001"] = api_fixture["decisions"].pop("GP-001")
    api_fixture["customers"].reverse()
    def get(url, **kwargs):
        response = api_fixture["get"](url, **kwargs)
        if url.endswith("/health"):
            body = response.json()
            body.update(provider_mode="trained", source_version="trained:current-model")
            return httpx.Response(200, json=body, request=response.request)
        return response
    monkeypatch.setattr(httpx, "get", get)
    app = start()
    assert app.selectbox(key="customer_id").value == "C10001"
    assert any(metric.label == "Calibrated propensity · synthetic model" for metric in app.metric)
    assert "Data source: trained" in displayed(app.sidebar)
    assert "Source version: trained:current-model" in displayed(app.sidebar)
    app.selectbox(key="customer_id").select("GP-003").run()
    assert not app.exception
    assert app.selectbox(key="customer_id").value == "GP-003"


def test_responsible_abstention_shortcut_replaces_customer(api_fixture):
    app = start()
    app.button(key="abstention").click().run()
    assert not app.exception
    assert app.selectbox(key="customer_id").value == "GP-002"
    assert app.header[0].value == "Person 2"
    assert "No supported recommendation" in displayed(app)
    assert displayed(app).count("INSUFFICIENT_INFORMATION") >= 4
    assert "GP-001" not in displayed(app).split("Decision for")[-1]
    assert all("-12.50" not in row.value for row in app.markdown)


@pytest.mark.parametrize("customer_id,state", [("GP-003", "CONFLICT_REQUIRES_REVIEW"), ("GP-004", "NOT_APPLICABLE"),
                                               ("GP-005", "SUPPRESSED"), ("GP-006", "DO_NOT_RECOMMEND")])
def test_other_decision_states(api_fixture, customer_id, state):
    app = start()
    app.selectbox(key="customer_id").select(customer_id).run()
    assert not app.exception
    assert displayed(app).count(state) >= 4


def test_portfolio_filters_reset_and_plots(api_fixture):
    app = start()
    app.radio(key="workspace").set_value("Portfolio").run()
    assert not app.exception
    assert len(app.get("plotly_chart")) == 4
    assert [metric.value for metric in app.metric][:3] == ["6", "4", "24"]
    app.selectbox(key="region").select("West").run()
    app.selectbox(key="segment").select("Self-employed").run()
    app.selectbox(key="product").select("SOLAR_FINANCE").run()
    assert not app.exception
    assert [metric.value for metric in app.metric][:3] == ["3", "0", "3"]
    assert ("/portfolio/trends", {"region": "West", "segment": "Self-employed", "product": "SOLAR_FINANCE"}) in api_fixture["calls"]
    # Region changes invalidate the prior dependent segment before its widget runs.
    app.selectbox(key="region").select("South").run()
    assert not app.exception
    assert app.selectbox(key="segment").value == "All"
    assert "Self-employed" not in app.selectbox(key="segment").options
    app.button(key="clear_filters").click().run()
    assert not app.exception
    assert all(app.selectbox(key=key).value == "All" for key in ("region", "segment", "product"))
    assert [metric.value for metric in app.metric][:3] == ["6", "4", "24"]
    assert "No cross-product carbon total" in displayed(app)


def test_portfolio_renders_compatible_impact_conversion_and_quality(api_fixture, monkeypatch):
    group = {"units": "kg CO2e/year", "boundary": "Operational", "period": "2025",
             "method_version": "method-v1", "factor_catalogue_version": "factor-v1", "value": "123.45"}
    def get(url, **kwargs):
        response = api_fixture["get"](url, **kwargs)
        body = response.json()
        if url.endswith("/portfolio/summary"):
            body["analytics"] = {"physical_impact": {"groups": [{"product": "EV_FINANCE", **group}],
                                                    "limitation": "Modelled potential, not realised savings."},
                                 "quality_counts": {"TRUSTED": 4}, "missingness": {"validated_confidence": 24}}
        elif url.endswith("/portfolio/trends"):
            body["analytics"] = {"limitation": "Recorded outcomes only; missing evidence remains unavailable.",
                                 "observations": [{"month": "2025-12", "product": "EV_FINANCE",
                                                   "observed_conversion_rate": "0.5", "observed_outcome_count": 2,
                                                   "quality_counts": {"TRUSTED": 1}, "quality_missing_count": 5,
                                                   "physical_impact_groups": [group]}]}
        return httpx.Response(response.status_code, json=body, request=response.request)
    monkeypatch.setattr(httpx, "get", get)
    app = start()
    app.radio(key="workspace").set_value("Portfolio").run()
    assert not app.exception
    assert "Modelled potential, not realised savings." in displayed(app)
    frames = [frame.value for frame in app.dataframe]
    conversions = next(frame for frame in frames if "observed_conversion_rate" in frame)
    assert conversions.iloc[0]["observed_conversion_rate"] == "50.0%"
    assert conversions.iloc[0]["quality_missing_count"] == 5
    physical = [frame for frame in frames if "units" in frame]
    assert len(physical) == 2
    assert all(frame.iloc[0]["units"] == "kg CO2e/year" for frame in physical)


def test_health_failure_clears_prior_customer_results(api_fixture, monkeypatch):
    app = start()
    def offline(url, **kwargs):
        raise httpx.ConnectError("refused")
    monkeypatch.setattr(httpx, "get", offline)
    app.run()
    assert not app.exception
    assert "Cannot reach the API" in app.error[0].value
    assert not app.metric
    assert not app.get("plotly_chart")
    assert not any(header.value == "Person 1" for header in app.header)


def test_explanation_failure_preserves_structured_evidence(api_fixture, monkeypatch):
    def get(url, **kwargs):
        if "/explanations/" in url:
            return httpx.Response(503, request=httpx.Request("GET", url))
        return api_fixture["get"](url, **kwargs)
    monkeypatch.setattr(httpx, "get", get)
    app = start()
    assert "HTTP 503" in app.error[0].value
    assert "Explanation unavailable" in displayed(app)
    assert any("References" in frame.value.columns for frame in app.dataframe)


def test_only_validated_confidence_is_shown(api_fixture):
    api_fixture["decisions"]["GP-001"][0]["propensity"]["confidence_validated"] = True
    app = start()
    assert "Model confidence: 99.0%" in displayed(app)


def test_co2e_baseline_and_scenario_keep_api_units(api_fixture):
    impact = api_fixture["decisions"]["GP-001"][0]["impact"]
    impact["units"] = "kg CO2e/year"
    for key in ("baseline", "scenario"):
        impact[key]["emissions_kg_co2e"] = impact[key].pop("emissions_kg_co2")
    app = start()
    text = displayed(app)
    assert "-12.50 kg CO2e/year" in text
    assert "100.00 kg CO2e/year" in text
    assert "112.50 kg CO2e/year" in text
    assert "100.00 kg CO2/year" not in text


def test_paperless_secondary_metrics_are_not_carbon_claims(api_fixture):
    impact = api_fixture["decisions"]["GP-001"][3]["impact"]
    impact["status"] = "NOT_CLAIMED"
    impact["secondary_metrics"] = [{"name": "paper_statements_avoided", "value": "12",
                                    "unit": "statements/year", "method_version": "paper-action-v1",
                                    "evidence_references": ["source:statements"]}]
    app = start()
    app.selectbox(key="why_product").select("PAPERLESS_BANKING").run()
    assert not app.exception
    assert "Physical actions are not carbon savings" in displayed(app)
    frames = [frame.value for frame in app.dataframe if "Metric" in frame.value]
    assert len(frames) == 1
    assert frames[0].iloc[0]["Value"] == "12"
    assert frames[0].iloc[0]["Unit"] == "statements/year"


def test_empty_customer_list(api_fixture):
    api_fixture["customers"].clear()
    app = start()
    assert "No synthetic customers" in app.info[0].value
    assert not app.metric


def test_refresh_requests_fresh_recommendations(api_fixture):
    app = start()
    api_fixture["decisions"]["GP-001"][0]["propensity"]["probability"] = "0.42"
    app.button(key="refresh").click().run()
    assert not app.exception
    assert any(metric.value == "42.0%" for metric in app.metric)
    assert sum(path == "/customers/GP-001/recommendations" for path, _ in api_fixture["calls"]) == 2


def test_portfolio_error_removes_prior_charts(api_fixture, monkeypatch):
    app = start()
    app.radio(key="workspace").set_value("Portfolio").run()
    assert len(app.get("plotly_chart")) == 4
    def get(url, **kwargs):
        if url.endswith("/portfolio/summary"):
            return httpx.Response(500, request=httpx.Request("GET", url))
        return api_fixture["get"](url, **kwargs)
    monkeypatch.setattr(httpx, "get", get)
    app.button(key="refresh").click().run()
    assert not app.exception
    assert "HTTP 500" in app.error[0].value
    assert not app.get("plotly_chart")
    assert not app.metric


def test_invalid_saved_filter_resets_safely(api_fixture):
    app = AppTest.from_file(str(APP), default_timeout=15)
    app.session_state["workspace"] = "Portfolio"
    app.session_state["region"] = "Removed region"
    app.session_state["segment"] = "Removed segment"
    app.session_state["product"] = "Removed product"
    app.run()
    assert not app.exception
    assert all(app.selectbox(key=key).value == "All" for key in ("region", "segment", "product"))
