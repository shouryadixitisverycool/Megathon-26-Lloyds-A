"""Partner catalogue presentation; offers and promotion decisions come from the API."""

from html import escape
from urllib.parse import urlsplit

import streamlit as st

from greenr.app.client import APIError

PARTNER_PRODUCTS = {"EV_FINANCE", "SOLAR_FINANCE", "GREEN_HOME"}
_HANDOFF_NOTICE = "Demo only. No application submitted. No customer details shared."
_LITERAL_STYLES = {
    "section": "font-size:1.35rem;font-weight:650;color:#243c31;line-height:1.3;margin:.35rem 0 .6rem",
    "title": "font-size:1.12rem;font-weight:650;color:#243c31;line-height:1.3;margin:.35rem 0",
    "body": "font-size:.95rem;color:#293f34;line-height:1.55;margin:.25rem 0 .65rem",
    "muted": "font-size:.82rem;color:#52665a;line-height:1.45;margin:.15rem 0 .35rem",
    "tag": "display:inline-block;background:#e7efe6;color:#315c4b;border:1px solid #c7dac8;border-radius:999px;padding:.25rem .65rem;font-size:.8rem;font-weight:600;margin:.2rem .35rem .45rem 0",
    "highlight": "font-size:.92rem;color:#293f34;line-height:1.5;margin:.18rem 0 .18rem .2rem",
}

# Static original artwork only. Catalogue values are rendered by native Streamlit
# elements below, never interpolated into this HTML.
_ILLUSTRATIONS = {
    "EV_FINANCE": """<div class="partner-art" role="img" aria-label="Illustration of an electric vehicle">
<svg width="100%" height="190" viewBox="0 0 520 190" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
<defs><linearGradient id="ev-bg" x2="1" y2="1"><stop stop-color="#f5efdf"/><stop offset="1" stop-color="#d8e8d8"/></linearGradient></defs>
<rect width="520" height="190" rx="24" fill="url(#ev-bg)"/><circle cx="414" cy="45" r="23" fill="#f0c971"/>
<path d="M0 145 Q130 113 260 145 T520 140 V190 H0Z" fill="#c5d8c9"/>
<path d="M100 123l22-36q7-12 21-12h151q13 0 22 12l25 36 30 9v29H75v-28z" fill="#315c4b"/>
<path d="M149 83h58v35h-77zm72 0h70q8 0 14 9l17 26H221z" fill="#dce9df"/>
<path d="M182 88h24v29h-24zm116 0 16 29h-35V88z" fill="#c1d6c9"/>
<circle cx="140" cy="158" r="19" fill="#273b33"/><circle cx="140" cy="158" r="8" fill="#eee8d8"/>
<circle cx="323" cy="158" r="19" fill="#273b33"/><circle cx="323" cy="158" r="8" fill="#eee8d8"/>
<path d="M417 32l-10 15h10l-6 13 17-19h-11l8-9z" fill="#8a6726"/>
</svg></div>""",
    "SOLAR_FINANCE": """<div class="partner-art" role="img" aria-label="Illustration of a home with solar panels">
<svg width="100%" height="190" viewBox="0 0 520 190" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
<defs><linearGradient id="solar-bg" x2="1" y2="1"><stop stop-color="#f4ecd8"/><stop offset="1" stop-color="#dcebdd"/></linearGradient></defs>
<rect width="520" height="190" rx="24" fill="url(#solar-bg)"/><circle cx="409" cy="49" r="26" fill="#edc46b"/>
<path d="M0 147 Q140 126 260 147 T520 140 V190 H0Z" fill="#c4d8c6"/>
<path d="M112 99l112-63 116 63v70H112z" fill="#faf6e9"/><path d="M88 102l136-76 139 76-12 17-127-70-125 70z" fill="#52745e"/>
<path d="M144 72l24-14 13 29-24 14zm35-20 26-15 13 30-26 15zm39-22 27-15 13 30-27 15zm-16 68 27-15 13 30-27 15zm36-21 28-15 13 30-28 15z" fill="#456f78" stroke="#eff0df" stroke-width="3"/>
<rect x="209" y="121" width="39" height="48" rx="2" fill="#c89058"/><rect x="130" y="124" width="43" height="32" rx="2" fill="#b7d4ca"/>
<path d="M366 126h42m-21-21v42" stroke="#78966e" stroke-width="5" stroke-linecap="round"/>
</svg></div>""",
    "GREEN_HOME": """<div class="partner-art" role="img" aria-label="Illustration of a comfortable green home">
<svg width="100%" height="190" viewBox="0 0 520 190" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
<defs><linearGradient id="home-bg" x2="1" y2="1"><stop stop-color="#f4efdf"/><stop offset="1" stop-color="#d9e8d8"/></linearGradient></defs>
<rect width="520" height="190" rx="24" fill="url(#home-bg)"/><circle cx="408" cy="48" r="25" fill="#edc675"/>
<path d="M0 148 Q136 120 260 148 T520 139 V190 H0Z" fill="#c5d9c8"/>
<path d="M114 101l111-64 119 65v68H114z" fill="#fbf7eb"/><path d="M91 103l134-79 141 79-12 18-129-72-123 72z" fill="#58785f"/>
<rect x="207" y="119" width="39" height="50" rx="2" fill="#b78351"/><rect x="138" y="119" width="45" height="34" rx="2" fill="#b8d5c9"/>
<rect x="274" y="119" width="45" height="34" rx="2" fill="#b8d5c9"/><path d="M374 159q-2-45 25-60 2 33-14 45 13-24 38-25-9 24-40 31" fill="#78986e"/>
<path d="M390 162v-39" stroke="#66845f" stroke-width="4" stroke-linecap="round"/>
</svg></div>""",
}


def _text(value, fallback=""):
    return value.strip() if isinstance(value, str) and value.strip() else fallback


def _literal_text(value, *, style="body", fallback="", prefix=""):
    """Render catalogue copy as escaped HTML text, never as Markdown or markup."""
    selected_style = style if style in _LITERAL_STYLES else "body"
    text = prefix + _text(value, fallback)
    st.html(
        f'<div class="partner-literal partner-literal--{selected_style}" '
        f'style="{_LITERAL_STYLES[selected_style]};white-space:pre-wrap;'
        f'overflow-wrap:anywhere;font-family:inherit">{escape(text, quote=True)}</div>'
    )


def _safe_https_url(value):
    if (not isinstance(value, str) or value != value.strip()
            or any(char.isspace() or ord(char) < 32 for char in value)):
        return None
    try:
        parsed = urlsplit(value)
        port = parsed.port
        if (parsed.scheme.lower() != "https" or not parsed.netloc or not parsed.hostname
                or parsed.username is not None or parsed.password is not None
                or (port is not None and not 1 <= port <= 65535)):
            return None
        return value
    except ValueError:
        return None


def _close_showcase():
    st.session_state["partner_product"] = None
    _clear_offer_selection()


def _clear_offer_selection():
    st.session_state.pop("partner_offer_id", None)
    st.session_state.pop("partner_preview_id", None)


def _select_offer(offer_id):
    st.session_state["partner_offer_id"] = offer_id
    st.session_state.pop("partner_preview_id", None)


def _preview_offer(offer_id):
    st.session_state["partner_preview_id"] = offer_id


def _valid_offers(category):
    options = category.get("options")
    if not isinstance(options, list):
        return None
    offers = []
    for option in options:
        if (isinstance(option, dict) and option.get("promoted") is True
                and _text(option.get("id")) and _text(option.get("title"))
                and _text(option.get("partner"))):
            offers.append(option)
    return offers


def partner_showcase(load, product, decision_state):
    """Render promoted offers from the read-only API catalogue for one category."""
    st.header("Illustrative partner offers", icon=":material/eco:")
    st.caption("Partner offers are examples, not financial advice, suitability, credit eligibility or approval.")
    state = _text(decision_state, "UNKNOWN")
    if state == "RECOMMEND":
        st.info("Decision state: RECOMMEND. This is not an approval; partner offers do not bypass customer consent.")
    else:
        state_notice = ("SUPPRESSED decisions remain suppressed. " if state == "SUPPRESSED" else "")
        st.info(f"Decision state: {state}, not RECOMMEND. {state_notice}Partner offers never override this decision or customer consent.")
    if st.button("Back to product opportunities", key="partner_close", width="stretch"):
        _close_showcase()
        st.rerun()

    try:
        catalogue = load("/partners/catalogue")
    except (APIError, KeyError, IndexError, TypeError, ValueError):
        _clear_offer_selection()
        st.warning("The partner catalogue is not available from this API yet. You can still review the product evidence below.")
        return
    if not isinstance(catalogue, dict):
        _clear_offer_selection()
        st.warning("The partner catalogue response is incomplete. You can still review the product evidence below.")
        return

    products = catalogue.get("products")
    if not isinstance(products, list):
        _clear_offer_selection()
        st.warning("The partner catalogue is missing its product list. Product evidence remains available below.")
        return
    category = next((item for item in products
                     if isinstance(item, dict) and item.get("product") == product), None)
    if category is None:
        _clear_offer_selection()
        st.info("No partner offers are published for this product yet. Product evidence remains available below.")
        return

    _literal_text(category.get("title"), style="section", fallback=product.replace("_", " ").title())
    if _text(category.get("subtitle")):
        _literal_text(category["subtitle"])
    meta = " · ".join(value for value in (
        f"Catalogue { _text(catalogue.get('version'), 'unversioned') }",
        f"Reviewed { _text(catalogue.get('reviewed_on'), 'date not supplied') }",
    ))
    _literal_text(meta, style="muted")
    _literal_text(catalogue.get("disclaimer"), style="muted",
                  fallback="Illustrative offers only; terms have not been assessed.")
    _literal_text(catalogue.get("commercial_disclaimer"), style="muted",
                  fallback="Commercial relationships and revenue terms have not been verified.")

    offers = _valid_offers(category)
    if offers is None:
        _clear_offer_selection()
        st.warning("The partner catalogue is missing its offer list. Product evidence remains available below.")
        return
    if not offers:
        _clear_offer_selection()
        st.info("There are no promoted partner options for this product. Product evidence remains available below.")
        return

    selected_id = st.session_state.get("partner_offer_id")
    if selected_id not in {offer["id"] for offer in offers}:
        st.session_state.pop("partner_offer_id", None)
        st.session_state.pop("partner_preview_id", None)
        selected_id = None

    columns = st.columns(2)
    for index, offer in enumerate(offers):
        with columns[index % len(columns)], st.container(border=True):
            st.html(_ILLUSTRATIONS[product])
            _literal_text(category.get("hero_tag"), style="tag", fallback="Illustrative option")
            st.badge("Illustrative offer", color="green")
            partner_label = ("Demo partner" if offer.get("placeholder") is True else
                             "Partner offer" if offer.get("placeholder") is False else "Unverified offer")
            st.badge(partner_label, color="blue")
            _literal_text(offer["title"], style="title")
            _literal_text(offer["partner"], style="muted")
            if _text(offer.get("relationship")):
                _literal_text(offer["relationship"], style="muted")
            _literal_text(offer.get("summary"), fallback="Offer details have not been supplied.")
            highlights = offer.get("highlights")
            if isinstance(highlights, list) and highlights:
                for highlight in highlights:
                    if _text(highlight):
                        _literal_text(highlight, style="highlight", prefix="• ")
            st.button("View offer details", key=f"partner_details_{product}_{offer['id']}",
                      on_click=_select_offer, args=(offer["id"],), width="stretch")

    selected = next((offer for offer in offers if offer["id"] == selected_id), None)
    if selected:
        st.subheader("Offer details")
        _literal_text(selected["title"], style="title")
        with st.container(border=True):
            for label, key in (("Suitability scope", "suitability"),
                               ("Disclosure", "disclosure"),
                               ("Commercial relationship", "revenue_path")):
                st.markdown(f"**{label}**")
                _literal_text(selected.get(key), fallback="Not supplied by the catalogue.")
            source = selected.get("source")
            if selected.get("placeholder") is False and isinstance(source, dict):
                source_label = _text(source.get("label"), "Partner source")
                _literal_text(source_label, style="muted")
                source_url = _safe_https_url(source.get("url"))
                if source_url:
                    st.link_button("Open source", source_url)
                else:
                    st.caption("Secure HTTPS source unavailable.")

            cta_label = _text(selected.get("cta_label"), "Continue to partner")
            _literal_text(cta_label, style="muted")
            destination = _safe_https_url(selected.get("destination_url"))
            if selected.get("placeholder") is True:
                st.button("Preview partner handoff", key=f"partner_preview_{product}_{selected['id']}",
                          on_click=_preview_offer, args=(selected["id"],), width="stretch")
                if st.session_state.get("partner_preview_id") == selected["id"]:
                    st.info(_HANDOFF_NOTICE)
            elif selected.get("placeholder") is False and destination:
                st.link_button("Open partner offer", destination, width="stretch")
            elif selected.get("placeholder") is False:
                st.warning("No secure HTTPS partner destination is configured; no handoff is available.")
            else:
                st.warning("This offer's partner status is unavailable, so no handoff is shown.")
