"""Optional cards remain separate and never infer a green loan purpose."""

from pathlib import Path
from urllib.parse import urlparse

import httpx
from streamlit.testing.v1 import AppTest

from greenr.extensions.optional_models import unavailable

APP = Path(__file__).resolve().parents[2] / "src/greenr/app/main.py"


def test_optional_cards_and_purpose_request(api_fixture, monkeypatch):
    def get(url, params=None, **kwargs):
        if urlparse(url).path.endswith("/optional-opportunities"):
            params = params or {}
            api_fixture["calls"].append((urlparse(url).path, params))
            rows = [unavailable("GREEN_INVESTMENTS", "NOT_AVAILABLE", "TRAINED_SOURCE_REQUIRED"),
                    unavailable("GREEN_LOANS", "INSUFFICIENT_INFORMATION", "DOCUMENTED_GREEN_PURPOSE_REQUIRED", params.get("purpose"))]
            if params.get("purpose"):
                rows[1].update(probability=.42, status="OPPORTUNITY_SIGNAL", model_version="optional-model-v1")
            return httpx.Response(200, json={"opportunities": rows}, request=httpx.Request("GET", url))
        return api_fixture["get"](url, params=params, **kwargs)
    monkeypatch.setattr(httpx, "get", get)
    app = AppTest.from_file(str(APP), default_timeout=15).run()
    assert not app.exception
    titles = [s.value for s in app.subheader]
    assert "Optional Green Investments" in titles and "Optional Green Loans" in titles
    assert app.selectbox(key="optional_purpose_GP-001").value == "Not declared"
    assert ("/customers/GP-001/optional-opportunities", {}) in api_fixture["calls"]
    app.selectbox(key="optional_purpose_GP-001").select("HEAT_PUMP").run()
    assert not app.exception
    assert ("/customers/GP-001/optional-opportunities", {"purpose": "HEAT_PUMP"}) in api_fixture["calls"]
    assert any(metric.value == "42.0%" for metric in app.metric)
    text = "\n".join(str(e.value) for kind in (app.caption, app.markdown) for e in kind)
    assert "Eligibility: NOT_ASSESSED" in text and "Impact: not claimed" in text
    assert "credit eligibility has not been assessed" in text
    assert "optional-model-v1" in text
    assert len(app.selectbox(key="why_product").options) == 4


def test_optional_api_error_does_not_hide_core_cards(api_fixture, monkeypatch):
    def get(url, **kwargs):
        if urlparse(url).path.endswith("/optional-opportunities"):
            return httpx.Response(503, json={"detail": "Unavailable"}, request=httpx.Request("GET", url))
        return api_fixture["get"](url, **kwargs)
    monkeypatch.setattr(httpx, "get", get)
    app = AppTest.from_file(str(APP), default_timeout=15).run()
    assert not app.exception
    assert len(app.selectbox(key="why_product").options) == 4
    assert sum("Optional Green" in s.value for s in app.subheader) == 2
