from copy import deepcopy
from urllib.parse import urlparse

import httpx
import pytest

from test_app import start, displayed


@pytest.fixture
def workspace_api(api_fixture, monkeypatch):
    writes = []
    def get(url, **kwargs):
        path = urlparse(url).path
        request = httpx.Request("GET", url)
        if path.endswith("/preferences"):
            body = {"do_not_contact": False, "channel_consent": {}}
        elif path.endswith("/history"):
            body = {"events": [], "source_history": [], "limitation": "Feedback does not edit scored evidence."}
        elif "/simulation-inputs/" in path:
            body = {"inputs": None, "limitation": "No verified inputs"}
        elif path.endswith("/next-actions"):
            rows = deepcopy(api_fixture["decisions"]["GP-001"])
            for row in rows:
                row.update(priority={"score": None, "rank": 1}, next_action={"action": "REQUEST_CONSENT", "reason": "No channel consent"})
            body = {"opportunities": rows}
        elif "/promos/" in path:
            body = {"status": "WITHHELD", "withheld_reason": "No recorded consent for the selected channel", "lines": []}
        elif "/evidence-graph/" in path:
            body = {"nodes": [{"id": "decision", "label": "RECOMMEND"}], "edges": [], "limitation": "Evidence is not causality."}
        elif path == "/governance/diagnostics":
            body = {"model_source": "test-trained-source", "limitations": ["Synthetic labels are not real-world validation"],
                    "reports": {"confidence_validation": {"passed": False}, "ml_evaluation": {"status": "NOT_RUN"}}}
        else:
            return api_fixture["get"](url, **kwargs)
        return httpx.Response(200, json=body, request=request)
    def post(url, **kwargs):
        writes.append((urlparse(url).path, kwargs["json"]))
        return httpx.Response(200, json={"id": "saved-event", "limitation": "Scores remain immutable"}, request=httpx.Request("POST", url))
    monkeypatch.setattr(httpx, "get", get)
    monkeypatch.setattr(httpx, "post", post)
    return writes


def click(app, label):
    next(button for button in app.button if button.label == label).click().run()
    assert not app.exception


def test_customer_preferences_and_feedback_are_explicit_posts(workspace_api):
    app = start()
    app.toggle(key="journey_open").set_value(True).run()
    next(item for item in app.checkbox if item.label == "Do not contact me").check()
    click(app, "Save contact preferences")
    path, payload = workspace_api[-1]
    assert path == "/customers/GP-001/preferences"
    assert payload["do_not_contact"] is True
    assert payload["channel_consent"] == {"app": False, "email": False, "phone": False, "rm": False}
    click(app, "Record response")
    assert workspace_api[-1][0] == "/feedback"
    assert workspace_api[-1][1]["customer_id"] == "GP-001"
    assert workspace_api[-1][1]["request_id"] != payload["request_id"]
    assert "Scores remain immutable" in displayed(app)


def test_rm_requires_review_rationale_before_post(workspace_api):
    app = start()
    app.radio(key="workspace").set_value("Relationship Manager").run()
    assert not app.exception
    click(app, "Record human review")
    assert "reviewer name and rationale" in app.error[0].value
    assert not workspace_api
    next(item for item in app.text_input if item.label == "Reviewer name").set_value("Reviewer A")
    next(item for item in app.text_area if item.label == "Review rationale").set_value("Source evidence conflicts")
    click(app, "Record human review")
    assert workspace_api[-1][0] == "/review"
    assert workspace_api[-1][1]["note"] == "Source evidence conflicts"


def test_governance_displays_missing_and_failed_validation(workspace_api):
    app = start()
    app.radio(key="workspace").set_value("Governance").run()
    assert not app.exception
    assert any("NOT_RUN" in warning.value for warning in app.warning)
    assert "test-trained-source" in displayed(app)


def test_unavailable_scenario_never_displays_zero(workspace_api):
    app = start()
    app.toggle(key="scenario_open").set_value(True).run()
    assert not app.exception
    assert any("No verified inputs" in info.value for info in app.info)
    assert not workspace_api


def test_uk_scenario_requires_explicit_forecasts(workspace_api, monkeypatch):
    previous = httpx.get
    def get(url, **kwargs):
        if "/simulation-inputs/" in url:
            return httpx.Response(200, json={"profile": "uk", "inputs": {"annual_mileage_km": 12000.0,
                "fuel_type": "PETROL"}, "limitation": "Observed synthetic baseline"}, request=httpx.Request("GET", url))
        return previous(url, **kwargs)
    monkeypatch.setattr(httpx, "get", get)
    app = start()
    app.toggle(key="scenario_open").set_value(True).run()
    assert not app.exception
    mileage = next(widget for widget in app.number_input if widget.label == "Annual scenario distance, km")
    assert mileage.value == 12000.0
    assert next(widget for widget in app.number_input if widget.label == "Proposed EV battery use, kWh per 100 km").value is None
    click(app, "Calculate UK scenario")
    assert "Supply each physical scenario input" in app.error[0].value
    assert not workspace_api
