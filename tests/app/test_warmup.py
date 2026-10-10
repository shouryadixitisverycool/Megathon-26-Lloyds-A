"""Pending portfolio responses must not become failures or fabricated results."""

from urllib.parse import urlparse

import httpx
import pytest

from greenpath.app.client import APIClient, APIError, APIPreparing
from test_app import displayed, start


def preparing_response(url, resource, message=None):
    return httpx.Response(503, json={"detail": {
        "code": "PORTFOLIO_PREPARING", "resource": resource,
        "message": message or f"Portfolio {resource} is preparing. Please refresh shortly.",
        "progress": {"phase": "loading_history", "completed": 2, "total": 12},
    }}, headers={"Retry-After": "2"}, request=httpx.Request("GET", url))


@pytest.mark.parametrize("resource,path", [("summary", "/portfolio/summary"), ("history", "/portfolio/trends")])
def test_pending_503_is_typed_and_preserves_safe_detail(monkeypatch, resource, path):
    monkeypatch.setattr(httpx, "get", lambda url, **kwargs: preparing_response(url, resource))
    with pytest.raises(APIPreparing) as caught:
        APIClient().get(path)
    assert isinstance(caught.value, APIError)
    assert str(caught.value) == f"Portfolio {resource} is preparing. Please refresh shortly."
    assert caught.value.resource == resource
    assert caught.value.progress == {"phase": "loading_history", "completed": 2, "total": 12}


@pytest.mark.parametrize("message", [None, "", "  ", 12, {"internal": "not user text"}])
def test_pending_message_has_safe_fallback(monkeypatch, message):
    def get(url, **kwargs):
        response = preparing_response(url, "summary")
        body = response.json()
        body["detail"]["message"] = message
        return httpx.Response(503, json=body, request=response.request)
    monkeypatch.setattr(httpx, "get", get)
    with pytest.raises(APIPreparing, match="Use Refresh data"):
        APIClient().get("/portfolio/summary")


def test_pending_message_is_bounded(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda url, **kwargs: preparing_response(url, "summary", "x" * 1000))
    with pytest.raises(APIPreparing) as caught:
        APIClient().get("/portfolio/summary")
    assert str(caught.value) == "x" * 500


def test_preparing_code_requires_503(monkeypatch):
    def get(url, **kwargs):
        response = preparing_response(url, "summary")
        return httpx.Response(500, json=response.json(), request=response.request)
    monkeypatch.setattr(httpx, "get", get)
    with pytest.raises(APIError, match="HTTP 500") as caught:
        APIClient().get("/portfolio/summary")
    assert not isinstance(caught.value, APIPreparing)


@pytest.mark.parametrize("body", [{"detail": {"code": "OTHER_FAILURE"}}, {"detail": "Unavailable"}, [], None])
def test_other_503_remains_generic_error(monkeypatch, body):
    monkeypatch.setattr(httpx, "get", lambda url, **kwargs: httpx.Response(
        503, json=body, request=httpx.Request("GET", url)))
    with pytest.raises(APIError, match="HTTP 503") as caught:
        APIClient().get("/portfolio/summary")
    assert not isinstance(caught.value, APIPreparing)


@pytest.mark.parametrize("resource", ["summary", "history"])
def test_portfolio_warmup_preserves_ready_results_and_refresh(api_fixture, monkeypatch, resource):
    pending = True
    calls = []
    pending_path = "/portfolio/summary" if resource == "summary" else "/portfolio/trends"

    def get(url, **kwargs):
        path = urlparse(url).path
        calls.append(path)
        if path == "/health":
            response = api_fixture["get"](url, **kwargs)
            body = response.json()
            body["runtime"] = {"warmup": {"phase": "loading_history", "status": "preparing"}}
            return httpx.Response(200, json=body, request=response.request)
        if pending and path == pending_path:
            return preparing_response(url, resource)
        return api_fixture["get"](url, **kwargs)

    monkeypatch.setattr(httpx, "get", get)
    app = start()
    assert app.header[0].value == "Person 1"
    assert any(metric.value == "82.0%" for metric in app.metric)
    assert not any(path.startswith("/portfolio/") for path in calls)
    app.radio(key="workspace").set_value("Portfolio").run()
    assert not app.exception
    assert not app.error
    assert f"Portfolio {resource} is preparing" in displayed(app)
    assert app.button(key="refresh").label == "Refresh data"
    assert "No customers match" not in displayed(app)
    assert "No historical observations" not in displayed(app)
    if resource == "summary":
        assert not app.metric
        assert not app.get("plotly_chart")
        assert not app.dataframe
        assert "/portfolio/trends" not in calls
    else:
        assert [metric.value for metric in app.metric] == ["6", "4", "24", "15"]
        assert len(app.get("plotly_chart")) == 3
        assert len(app.dataframe) == 3
        assert "Monthly trend" in [item.value for item in app.subheader]

    app.radio(key="workspace").set_value("Customer").run()
    app.selectbox(key="customer_id").select("GP-003").run()
    assert not app.exception
    assert not app.error
    assert app.header[0].value == "Person 3"
    app.radio(key="workspace").set_value("Portfolio").run()
    assert not app.exception
    assert f"Portfolio {resource} is preparing" in displayed(app)

    pending = False
    app.button(key="refresh").click().run()
    assert not app.exception
    assert not app.error
    assert len(app.get("plotly_chart")) == 4
    assert "is preparing" not in displayed(app)
