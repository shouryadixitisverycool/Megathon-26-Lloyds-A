import ast
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from greenpath.app.client import APIClient, APIError
from greenpath.app.presentation import decimal_number, impact_label, percentage, trends_chart


@pytest.mark.parametrize("value", [None, True, False, "NaN", "Infinity", "-Infinity", "invalid"])
def test_invalid_numbers_are_unavailable(value):
    assert decimal_number(value) is None
    assert percentage(value) == "Unavailable"


def test_decimal_strings_preserve_zero_and_negative():
    assert decimal_number("0.000") == Decimal("0")
    assert percentage("0.82") == "82.0%"
    assert percentage("1.01") == "Unavailable"
    assert impact_label({"status": "AVAILABLE", "value": "-1.25", "units": "kg CO2"}) == "-1.25 kg CO2"
    assert impact_label({"status": "AVAILABLE", "value": "0", "units": "kg CO2"}) == "0.00 kg CO2"
    assert impact_label({"status": "UNAVAILABLE", "value": "123", "units": "kg CO2"}) == "UNAVAILABLE"


@pytest.mark.parametrize("url", ["file:///tmp/data", "api.example", "https://name:secret@example.org", "ftp://example.org"])
def test_invalid_api_url(url):
    with pytest.raises(APIError):
        APIClient(url)


def test_configured_api_and_encoded_id(monkeypatch):
    monkeypatch.setenv("GREENPATH_API_URL", "https://example.org/api/")
    assert APIClient().base_url == "https://example.org/api"
    assert APIClient.customer_path("a/b c") == "/customers/a%2Fb%20c"


@pytest.mark.parametrize("status", [404, 422, 500])
def test_status_errors(monkeypatch, status):
    monkeypatch.setattr(httpx, "get", lambda url, **kwargs: httpx.Response(status, request=httpx.Request("GET", url)))
    with pytest.raises(APIError, match=f"HTTP {status}"):
        APIClient().get("/customers/missing")


@pytest.mark.parametrize("body", ["not json", "null", "1", '"text"'])
def test_invalid_json_shape(monkeypatch, body):
    monkeypatch.setattr(httpx, "get", lambda url, **kwargs: httpx.Response(200, text=body, request=httpx.Request("GET", url)))
    with pytest.raises(APIError):
        APIClient().get("/health")


def test_timeout_is_visible(monkeypatch):
    def timeout(url, **kwargs):
        raise httpx.ConnectTimeout("timed out")
    monkeypatch.setattr(httpx, "get", timeout)
    with pytest.raises(APIError, match="timed out"):
        APIClient().get("/health")


def test_ui_has_no_domain_imports():
    directory = Path(__file__).resolve().parents[2] / "src/greenpath/app"
    forbidden = ("greenpath.impact", "greenpath.recommendation", "greenpath.models", "greenpath.llm", "greenpath.demo", "greenpath.api")
    for file in directory.glob("*.py"):
        tree = ast.parse(file.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith(forbidden), file
            if isinstance(node, ast.Import):
                assert all(not alias.name.startswith(forbidden) for alias in node.names), file


def test_trends_use_only_supplied_months_and_products():
    figure = trends_chart([{"month": "2025-12", "product": "EV_FINANCE", "recommended_count": 3},
                          {"month": "2025-10", "product": "EV_FINANCE", "recommended_count": 1}])
    assert len(figure.data) == 1
    assert list(figure.data[0].x) == ["2025-10", "2025-12"]
    assert list(figure.data[0].y) == [1, 3]
    assert figure.layout.xaxis.type == "category"
    assert figure.layout.xaxis.title.text == "Month"
    assert list(figure.layout.xaxis.categoryarray) == ["2025-10", "2025-12"]
