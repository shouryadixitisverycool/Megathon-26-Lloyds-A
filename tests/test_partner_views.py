"""Partner showcase stays read-only and separate from customer evidence."""

from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

import httpx
import pytest
from streamlit.testing.v1 import AppTest

from tests.app.conftest import api_fixture

APP = Path(__file__).resolve().parents[1] / "src/greenpath/app/main.py"
HANDOFF_NOTICE = "Demo only. No application submitted. No customer details shared."
_DEFAULT_CATALOGUE = object()


def offer(offer_id, *, promoted=True, placeholder=True):
    return {
        "id": offer_id,
        "partner": f"Demo partner {offer_id}",
        "relationship": "Illustrative referral relationship",
        "title": f"A green choice · {offer_id}",
        "summary": "A demonstration offer for exploring lower-carbon home choices.",
        "highlights": ["Clear example terms", "No application is made from this screen"],
        "suitability": "Illustrative scope only; this is not a suitability assessment.",
        "disclosure": "Placeholder information, subject to future partner review.",
        "revenue_path": "Example referral fee; no payment is taken here.",
        "source": {"label": "Demo source", "url": "https://example.org/offer"},
        "destination_url": "https://example.org/should-not-open" if placeholder else None,
        "cta_label": "Preview this offer",
        "placeholder": placeholder,
        "promoted": promoted,
    }


def catalogue():
    return {
        "version": "partner-catalogue-v1",
        "reviewed_on": "2026-10-01",
        "disclaimer": "Illustrative offers only; terms have not been assessed.",
        "commercial_disclaimer": "Demo commercial disclosure: referral relationships may be remunerated.",
        "products": [
            {
                "product": product,
                "title": title,
                "subtitle": "Examples for greener transport and homes.",
                "hero_tag": "Explore an illustrative option",
                "options": [
                    offer(f"{product.lower()}-one"),
                    offer(f"{product.lower()}-two"),
                    offer(f"{product.lower()}-unpromoted", promoted=False),
                ],
            }
            for product, title in (
                ("EV_FINANCE", "Electric vehicle finance"),
                ("SOLAR_FINANCE", "Solar finance"),
                ("GREEN_HOME", "Green-home improvements"),
            )
        ],
    }


def text_content(app):
    kinds = (app.caption, app.markdown, app.info, app.warning, app.error,
             app.subheader, app.header, app.get("html"))
    return "\n".join(str(element.value) for kind in kinds for element in kind)


def start(api_fixture, monkeypatch, catalogue_payload=_DEFAULT_CATALOGUE):
    payload = catalogue() if catalogue_payload is _DEFAULT_CATALOGUE else catalogue_payload

    def get(url, params=None, **kwargs):
        if urlparse(url).path == "/partners/catalogue":
            api_fixture["calls"].append(("/partners/catalogue", params or {}))
            if payload is None:
                request = httpx.Request("GET", url, params=params)
                return httpx.Response(404, json={"detail": "Not found"}, request=request)
            return httpx.Response(200, json=payload, request=httpx.Request("GET", url, params=params))
        return api_fixture["get"](url, params=params, **kwargs)

    monkeypatch.setattr(httpx, "get", get)
    app = AppTest.from_file(str(APP), default_timeout=20).run()
    assert not app.exception
    return app


def test_explore_is_separate_from_evidence_and_placeholder_handoff_is_local(api_fixture, monkeypatch):
    app = start(api_fixture, monkeypatch)
    assert not any(button.key == "explore_PAPERLESS_BANKING" for button in app.button)
    assert any(button.key == "review_evidence_PAPERLESS_BANKING" for button in app.button)
    app.selectbox(key="why_product").select("SOLAR_FINANCE").run()
    assert not app.exception
    app.button(key="explore_EV_FINANCE").click().run()

    assert not app.exception
    assert app.session_state["partner_product"] == "EV_FINANCE"
    assert app.selectbox(key="why_product").value == "SOLAR_FINANCE"
    assert ("/partners/catalogue", {}) in api_fixture["calls"]
    assert "partner-catalogue-v1" in text_content(app)
    assert "Demo commercial disclosure" in text_content(app)
    assert "A green choice · ev_finance-unpromoted" not in text_content(app)
    assert any("fixture:ownership" in list(frame.value["References"]) for frame in app.dataframe)

    offer_id = "ev_finance-one"
    app.button(key=f"partner_details_EV_FINANCE_{offer_id}").click().run()
    assert not app.exception
    assert "Illustrative scope only" in text_content(app)
    assert "Example referral fee" in text_content(app)
    app.button(key=f"partner_preview_EV_FINANCE_{offer_id}").click().run()
    assert not app.exception
    assert HANDOFF_NOTICE in text_content(app)
    assert not any("should-not-open" in str(button.value) for button in app.get("link_button"))

    # A category switch clears selected offer and preview state, but not evidence choice.
    app.button(key="explore_SOLAR_FINANCE").click().run()
    assert not app.exception
    assert app.session_state["partner_product"] == "SOLAR_FINANCE"
    assert "partner_offer_id" not in app.session_state
    assert "partner_preview_id" not in app.session_state
    assert app.selectbox(key="why_product").value == "SOLAR_FINANCE"

    app.button(key="partner_close").click().run()
    assert not app.exception
    assert app.session_state["partner_product"] is None
    assert app.selectbox(key="why_product").value == "SOLAR_FINANCE"
    app.button(key="explore_EV_FINANCE").click().run()
    app.button(key="review_evidence_GREEN_HOME").click().run()
    assert not app.exception
    assert app.session_state["partner_product"] is None
    assert app.selectbox(key="why_product").value == "GREEN_HOME"


@pytest.mark.parametrize(
    ("destination_url", "has_partner_link"),
    [
        ("https://provider.example/apply", True),
        ("http://provider.example/apply", False),
        ("https://user:secret@provider.example/apply", False),
    ],
)
def test_non_placeholder_handoff_requires_https_and_uses_catalogue_label(
    api_fixture, monkeypatch, destination_url, has_partner_link
):
    payload = catalogue()
    selected = payload["products"][0]["options"][0]
    selected.update(
        placeholder=False,
        source={"label": "Provider product information", "url": "https://provider.example/info"},
        destination_url=destination_url,
        cta_label="Visit provider offer",
    )
    app = start(api_fixture, monkeypatch, catalogue_payload=payload)
    app.button(key="explore_EV_FINANCE").click().run()
    app.button(key="partner_details_EV_FINANCE_ev_finance-one").click().run()

    assert not app.exception
    labels = [button.value for button in app.get("link_button")]
    assert "Open source" in labels
    assert ("Open partner offer" in labels) is has_partner_link
    assert "Visit provider offer" in text_content(app)
    if not has_partner_link:
        assert any("No secure HTTPS partner destination" in warning.value for warning in app.warning)
    assert not any(button.key == "partner_preview_EV_FINANCE_ev_finance-one" for button in app.button)


class RenderedTagCounter(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag.lower())


def test_catalogue_copy_is_literal_and_never_creates_links_or_images(api_fixture, monkeypatch):
    payload = catalogue()
    attack = ('[Apply now](https://evil.example/apply) https://bare.example/offer '
              '<a href="https://evil.example/link">Link</a>'
              '<img src="https://evil.example/pixel">')
    payload.update(version=attack, reviewed_on=attack, disclaimer=attack, commercial_disclaimer=attack)
    category = payload["products"][0]
    category.update(title=attack, subtitle=attack, hero_tag=attack)
    selected = category["options"][0]
    selected.update(
        partner=attack,
        relationship=attack,
        title=attack,
        summary=attack,
        highlights=[attack],
        suitability=attack,
        disclosure=attack,
        revenue_path=attack,
        placeholder=False,
        source={"label": attack, "url": "https://source.example/catalogue"},
        destination_url="https://partner.example/apply",
        cta_label=attack,
    )

    app = start(api_fixture, monkeypatch, catalogue_payload=payload)
    app.button(key="explore_EV_FINANCE").click().run()
    app.button(key="partner_details_EV_FINANCE_ev_finance-one").click().run()

    assert not app.exception
    rendered = [str(element.value) for element in app.get("html")]
    rendered_html = "\n".join(rendered)
    assert escape(attack, quote=True) in rendered_html

    tags = RenderedTagCounter()
    for markup in rendered:
        tags.feed(markup)
    assert "a" not in tags.tags
    assert "img" not in tags.tags
    assert tags.tags.count("svg") == 2  # Original local artwork remains intact.

    labels = [button.value for button in app.get("link_button")]
    assert labels.count("Open source") == 1
    assert labels.count("Open partner offer") == 1
    assert all(attack not in label for label in labels)


def test_suppressed_state_cannot_be_overridden_and_customer_change_clears_offer(api_fixture, monkeypatch):
    api_fixture["decisions"]["GP-001"][0]["state"] = "SUPPRESSED"
    app = start(api_fixture, monkeypatch)
    app.button(key="explore_EV_FINANCE").click().run()
    assert not app.exception
    assert "Decision state: SUPPRESSED, not RECOMMEND." in text_content(app)
    assert "SUPPRESSED decisions remain suppressed." in text_content(app)
    assert "never override this decision or customer consent" in text_content(app)

    # Open an offer, then select another customer; the old customer's detail/preview
    # must not persist even though the catalogue itself is customer-independent.
    app.button(key="partner_details_EV_FINANCE_ev_finance-one").click().run()
    app.button(key="partner_preview_EV_FINANCE_ev_finance-one").click().run()
    app.selectbox(key="customer_id").select("GP-002").run()
    assert not app.exception
    assert app.session_state["partner_product"] is None
    assert "partner_offer_id" not in app.session_state
    assert "partner_preview_id" not in app.session_state
    assert HANDOFF_NOTICE not in text_content(app)


def test_older_api_without_catalogue_keeps_evidence_review_available(api_fixture, monkeypatch):
    app = start(api_fixture, monkeypatch, catalogue_payload=None)
    app.button(key="explore_EV_FINANCE").click().run()

    assert not app.exception
    assert "not available from this API yet" in text_content(app)
    assert app.selectbox(key="why_product").value == "EV_FINANCE"
    assert any("fixture:ownership" in list(frame.value["References"]) for frame in app.dataframe)
    partner_requests = [call for call in api_fixture["calls"] if call[0] == "/partners/catalogue"]
    assert partner_requests == [("/partners/catalogue", {})]
