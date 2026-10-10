from pathlib import Path

import httpx
import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[2] / "src/greenpath/app/main.py"


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
