"""Native Streamlit views receiving only API JSON."""

from urllib.parse import urlparse

import streamlit as st

from greenr.app.client import APIError, APIPreparing
from greenr.app.presentation import (
    PRODUCTS, STATES, decimal_number, groups_chart, impact_label,
    opportunities_chart, percentage, trends_chart,
)
from greenr.app.partners import PARTNER_PRODUCTS, partner_showcase


def safe_select(label, options, key, **kwargs):
    if st.session_state.get(key) not in options:
        st.session_state[key] = options[0]
    return st.selectbox(label, options, key=key, **kwargs)


def bullets(items):
    for item in items:
        st.markdown(f"- {item}")


def clear_partner_selection():
    """Drop offer state when the customer, category, or view changes."""
    st.session_state["partner_product"] = None
    st.session_state.pop("partner_offer_id", None)
    st.session_state.pop("partner_preview_id", None)


def customer_view(customers, load, save=None, provider_mode=None):
    lookup = {item["customer_id"]: item for item in customers}
    if st.session_state.get("customer_id") not in lookup and "C10001" in lookup:
        st.session_state["customer_id"] = "C10001"
    with st.sidebar:
        st.caption("CUSTOMER FIELD NOTES")
        try:
            readiness = load("/demo/readiness")
        except APIError:
            readiness = {"products": {}, "examples": {}, "missing_features": ["Readiness report is not served by this API."]}
        st.caption("SHOWCASE READINESS")
        if readiness.get("status"):
            st.caption(f"{readiness['status']} · {readiness.get('population_customers', 'Unknown')} scored customers")
        shortcuts = {}
        for product, entry in readiness.get("products", {}).items():
            candidate = entry.get("candidate")
            st.caption(f"{PRODUCTS.get(product, product)}: {entry['status']}")
            if candidate and candidate["customer_id"] in lookup:
                name = f"{PRODUCTS.get(product, product)} · {candidate['state']} · {candidate['customer_id']}"
                shortcuts[name] = candidate
            for missing in entry.get("missing_features", []):
                st.caption(missing)
        for label, candidate in readiness.get("examples", {}).items():
            if candidate["customer_id"] in lookup:
                shortcuts[f"{label.replace('_', ' ').title()} · {candidate['customer_id']}"] = candidate
        if shortcuts:
            def showcase():
                chosen = shortcuts[st.session_state["showcase_choice"]]
                if chosen["customer_id"] != st.session_state.get("customer_id"):
                    clear_partner_selection()
                st.session_state["customer_id"] = chosen["customer_id"]
                st.session_state["why_product"] = chosen["product"]
            safe_select("Showcase evidence", list(shortcuts), "showcase_choice")
            st.button("Open showcase customer", on_click=showcase, key="open_showcase", width="stretch")
        for missing in readiness.get("missing_features", []):
            st.caption(missing)
        if readiness.get("limitation"):
            st.caption(readiness["limitation"])
        abstention_candidate = readiness.get("examples", {}).get("abstention")
        abstention_id = "C10005" if "C10005" in lookup else "GP-002" if "GP-002" in lookup else None
        if abstention_candidate:
            abstention_id = abstention_candidate["customer_id"]
        elif readiness.get("status"):
            abstention_id = None
        if abstention_id:
            def abstention():
                clear_partner_selection()
                st.session_state["customer_id"] = abstention_id
            st.button("See responsible abstention", on_click=abstention, key="abstention", width="stretch")
        customer_id = safe_select("Customer", list(lookup), "customer_id",
                                  format_func=lambda key: f"{key} · {lookup[key]['display_name']}",
                                  on_change=clear_partner_selection)
    customer = load(f"/customers/{customer_id}")
    recommendations = load(f"/customers/{customer_id}/recommendations")["recommendations"]
    st.header(customer["display_name"], icon=":material/person:")
    st.caption(f"{customer_id} · {customer['region']} · {customer['segment']} · Synthetic demo")
    trust = customer["trust"]
    with st.container(horizontal=True):
        st.metric("Data Trust", f"{percentage(trust.get('score'))} · {trust['status']}", border=True)
        st.metric("Feature cutoff", customer["feature_cutoff"], border=True)
    st.caption("Trust describes the quality of customer evidence. It is separate from model confidence. Synthetic probabilities do not establish predictive performance.")
    if trust.get("issues"):
        for issue in trust["issues"]:
            st.warning(f"{issue['code']} · {issue['field']} · {issue['message']}")
    if recommendations and all(row["state"] != "RECOMMEND" for row in recommendations):
        st.info("No supported recommendation for this customer. Abstention is a valid result; review the evidence before any outreach.")
    st.subheader("Product opportunities")
    columns = st.columns(2)
    for index, row in enumerate(recommendations):
        with columns[index % 2]:
            with st.container(border=True):
                product = row["product"]
                label, color = STATES.get(row["state"], (row["state"], "gray"))
                st.subheader(PRODUCTS.get(product, product))
                st.badge(label, color=color)
                st.caption(row["state"])
                propensity = row.get("propensity") or {}
                label = "Calibrated propensity · synthetic model" if provider_mode in {"artifacts", "trained"} else "Propensity · synthetic demo"
                st.metric(label, percentage(propensity.get("probability")))
                confidence = percentage(propensity.get("confidence")) if propensity.get("confidence_validated") is True else "Unavailable"
                limitation = propensity.get("confidence_limitation") or (propensity.get("source_result") or {}).get("confidence", {}).get("limitation")
                if propensity.get("confidence_validated") is True:
                    st.caption(f"Model confidence: {confidence}. Validated on synthetic release-selection evidence, not real-world performance.")
                else:
                    st.caption(f"Model confidence: {confidence} (suppressed). {limitation or 'No validated confidence source was supplied for this product.'}")
                st.markdown(f"Potential impact: **{impact_label(row['impact'])}**")
                if row["impact"]["status"] == "AVAILABLE":
                    st.caption("Baseline minus scenario; this is a modeled opportunity, not a realized reduction.")
                else:
                    st.caption("No defensible carbon estimate is available. An unavailable impact never means zero.")
                def inspect_product(value=product):
                    st.session_state["partner_product"] = value
                    st.session_state.pop("partner_offer_id", None)
                    st.session_state.pop("partner_preview_id", None)
                def review_product(value=product):
                    clear_partner_selection()
                    st.session_state["why_product"] = value
                if product in PARTNER_PRODUCTS:
                    st.button(f"Explore {PRODUCTS.get(product, product)}", key=f"explore_{product}",
                              on_click=inspect_product, width="stretch")
                st.button("Review evidence", key=f"review_evidence_{product}",
                          on_click=review_product, width="stretch")
                if product in PARTNER_PRODUCTS:
                    st.caption("Explore illustrative partner options, not financial eligibility or approval.")
    by_product = {row["product"]: row for row in recommendations}
    partner_product = st.session_state.get("partner_product")
    if partner_product is not None:
        if partner_product in PARTNER_PRODUCTS and partner_product in by_product:
            partner_showcase(load, partner_product, by_product[partner_product].get("state", "UNKNOWN"))
        else:
            clear_partner_selection()
    optional_cards(customer_id, load)
    if not recommendations:
        st.info("The API returned no product decisions for this customer.")
        return
    st.header("Why this result?", icon=":material/fact_check:")
    product = safe_select("Inspect a product", list(by_product), "why_product", format_func=lambda value: PRODUCTS.get(value, value))
    row = by_product[product]
    try:
        explanation = load(f"/customers/{customer_id}/explanations/{product}")
        # Older shipped API responses only expose text.
        if explanation.get("headline") is not None:
            st.subheader(explanation["headline"])
            st.markdown(explanation["explanation"])
            bullets(explanation["why_recommended"])
            st.markdown(explanation["estimated_impact_text"])
            st.caption(explanation["confidence_text"])
            st.markdown(explanation["action_text"])
            if explanation["missing_information"]:
                st.markdown("**Missing information**")
                bullets(explanation["missing_information"])
        else:
            st.markdown(explanation["text"])
        st.caption(f"Explanation source: {explanation['source']} · {explanation['provider_version']} · Validation: {explanation['validation_passed']}")
        if explanation.get("fallback_reason"):
            st.caption(f"Template fallback: {explanation['fallback_reason']}")
    except APIError as error:
        st.error(str(error))
        st.caption("Explanation unavailable. The API decision and its evidence remain below.")
    st.caption(row["eligibility_disclaimer"])
    evidence_rows = [{"Reason code": item["code"], "Evidence": item["message"],
                      "Fields": ", ".join(item.get("fields", [])),
                      "References": ", ".join(item.get("references", []))} for item in row.get("evidence", [])]
    st.subheader("Decision evidence")
    if evidence_rows:
        st.dataframe(evidence_rows, hide_index=True, alt="Evidence and references for the selected product decision")
    else:
        st.caption("No decision evidence supplied by the API.")
    st.caption("Reason codes: " + ", ".join(row.get("reason_codes", [])))
    with st.expander("Customer evidence and data quality"):
        features = [{"Field": name, "Value": str(value.get("value")), "Observed at": value["observed_at"],
                     "Freshness": value["freshness"], "Reference": value["reference"],
                     "Conflicts": "; ".join(value.get("conflicts", []))} for name, value in customer["features"].items()]
        st.dataframe(features, hide_index=True, alt="Approved customer evidence with freshness and conflicts")
        if customer.get("source_snapshot"):
            st.json(customer["source_snapshot"])
    with st.expander("Versions and decision exclusions"):
        propensity = row.get("propensity") or {}
        st.text(f"Cutoff: {row['feature_cutoff']}\nDecision timestamp: {row['timestamp']}\nRules: {row['rules_version']}\nModel: {propensity.get('model_version', 'Unavailable')}\nCalibration: {propensity.get('calibration_version') or 'Unavailable'}\nTrust: {row['trust'].get('version', 'Unavailable')}\nContract: {row['contract_version']}")
        bullets(row.get("exclusions", []))
    impact_details(row["impact"])
    if save:
        from greenr.app.workspaces import journey_tools, scenario_tools
        if st.toggle("Manage contact preferences and record a response", key="journey_open"):
            journey_tools(customer_id, product, load, save)
        if st.toggle("Explore a what-if scenario", key="scenario_open"):
            scenario_tools(customer_id, product, load, save)


def optional_cards(customer_id, load):
    st.subheader("Optional opportunities")
    st.caption("Experimental synthetic signals, separate from the four core products. Not investment advice, suitability or credit approval.")
    purpose = safe_select("Declared green loan purpose", ["Not declared", "INSULATION", "HEAT_PUMP", "EV_CHARGING"],
                          f"optional_purpose_{customer_id}")
    params = {} if purpose == "Not declared" else {"purpose": purpose}
    try:
        payload = load(f"/customers/{customer_id}/optional-opportunities", params)
    except (APIError, KeyError, IndexError):
        payload = {"opportunities": [{"product": name, "status": "NOT_AVAILABLE", "probability": None}
                                     for name in ("GREEN_INVESTMENTS", "GREEN_LOANS")]}
    columns = st.columns(2)
    for column, row in zip(columns, payload["opportunities"]):
        with column, st.container(border=True):
            investment = row["product"] == "GREEN_INVESTMENTS"
            st.subheader("Optional Green Investments" if investment else "Optional Green Loans")
            st.caption("Experimental · " + row["status"])
            st.metric("Calibrated propensity · synthetic optional model", percentage(row.get("probability")))
            if row["status"] == "LOW_RELEVANCE":
                st.write("The experimental model shows low relevance. This is not a financial recommendation.")
            elif row.get("probability") is not None:
                st.write("Your existing investment activity and stated sustainability preference support exploring this optional signal."
                         if investment else "Your existing borrowing relationship and declared green purpose support exploring this optional signal. Your credit eligibility has not been assessed.")
            elif row["status"] == "NOT_RELEVANT":
                st.write("The required existing investment activity is not confirmed." if investment
                         else "The required existing borrowing relationship is not confirmed.")
            elif not investment and purpose == "Not declared":
                st.write("Declare a supported green purpose to explore this signal. We do not infer your intended use from spending.")
            else:
                st.write("There is not enough verified evidence or a current trained model to show this optional signal.")
            st.caption("Confidence: suppressed. Impact: not claimed. Eligibility: NOT_ASSESSED.")
            st.caption(row.get("confidence_limitation", "No validated optional confidence is available."))
            st.caption("Reasons: " + ", ".join(row.get("reason_codes", [])))
            if row.get("reason_evidence"):
                st.json(row["reason_evidence"])
            st.caption(f"Model: {row.get('model_version') or 'Unavailable'} · Calibration: {row.get('calibration_version') or 'Unavailable'} · Features: {row.get('feature_version') or 'Unavailable'} · Cutoff: {row.get('cutoff') or 'Unavailable'}")


def impact_details(impact):
    with st.expander("Impact method, factors and assumptions", expanded=True):
        st.subheader("Potential impact · " + impact_label(impact))
        st.markdown(impact["boundary"])
        st.caption(f"Units: {impact['units']} · Method: {impact['method_version']} · Release: {impact['method_release']} · Factor catalogue: {impact['factor_catalogue_version']}")
        st.caption(f"Calculated at: {impact['timestamp']} · Impact feature cutoff: {impact.get('feature_cutoff') or 'Unavailable'}")
        st.text(f"Factor catalogue SHA-256: {impact['factor_catalogue_sha256']}")
        if impact.get("period"):
            st.caption(f"Activity period: {impact['period']['start']} inclusive to {impact['period']['end']} exclusive")
        if impact.get("secondary_metrics"):
            st.markdown("**Physical action metrics**")
            st.dataframe([{"Metric": metric["name"], "Value": metric["value"], "Unit": metric["unit"],
                           "Method": metric["method_version"], "Evidence": metric["evidence_references"]}
                          for metric in impact["secondary_metrics"]], hide_index=True)
            st.caption("Physical actions are not carbon savings; no lifecycle carbon impact is inferred.")
        for key in ("baseline", "scenario"):
            scenario = impact[key]
            field = "emissions_kg_co2e" if impact["units"] == "kg CO2e/year" else "emissions_kg_co2"
            number = decimal_number(scenario.get(field))
            value = f"{number:,.2f} {impact['units']}" if number is not None else "UNAVAILABLE"
            st.markdown(f"**{key.capitalize()}** · {scenario['description']} · {value}")
        for issue in impact.get("issues", []):
            st.warning(f"{issue['code']} · {issue['field']} · {issue['message']}")
        st.markdown("**Assumptions**")
        bullets(impact.get("assumptions", []))
        st.markdown("**Exclusions**")
        bullets(impact.get("exclusions", []))
        if impact.get("evidence"):
            st.dataframe([{"Field": item["field"], "Value": str(item["value"]),
                           "Unit": item.get("unit"), "Basis": item["basis"],
                           "Reference": item["reference"], "Freshness": item["freshness"],
                           "Observed at": item["observed_at"]} for item in impact["evidence"]],
                         hide_index=True, alt="Activity inputs and sources used by the impact calculator")
        for factor in impact.get("factors", []):
            st.markdown(f"**{factor['factor_id']}** · {factor['value']} {factor['unit']}")
            st.text(f"Source: {factor['source_title']}\nPublisher: {factor['source_publisher']}\nEdition: {factor['source_edition']}\nLocator: {factor['source_locator']}\nGeography: {factor['geography']}\nActivity period: {factor.get('activity_period') or 'Unavailable'}\nBoundary: {factor['boundary']}\nApplicability: {factor['applicability']}\nVerification: {factor['verification_basis']}\nSource SHA-256: {factor.get('source_sha256') or 'Unavailable'}")
            url = factor.get("source_url", "")
            if urlparse(url).scheme in {"https", "http"}:
                st.link_button("Open factor source", url)
            if factor.get("source_limitation"):
                st.warning(factor["source_limitation"])


def portfolio_view(customers, load):
    def reset():
        for key in ("region", "segment", "product"):
            st.session_state[key] = "All"
    with st.sidebar:
        st.caption("PORTFOLIO FILTERS")
        st.button("Clear filters", on_click=reset, key="clear_filters", width="stretch")
        region = safe_select("Region", ["All"] + sorted({row["region"] for row in customers}), "region")
        matching = [row for row in customers if region == "All" or row["region"] == region]
        segment = safe_select("Segment", ["All"] + sorted({row["segment"] for row in matching}), "segment")
        product = safe_select("Product", ["All"] + list(PRODUCTS), "product", format_func=lambda value: PRODUCTS.get(value, value))
    params = {key: value for key, value in {"region": region, "segment": segment, "product": product}.items() if value != "All"}
    st.header("Portfolio opportunities", icon=":material/forest:")
    st.caption(f"Synthetic demo · Region: {region} · Segment: {segment} · Product: {PRODUCTS.get(product, product)}")
    try:
        summary = load("/portfolio/summary", params)
    except APIPreparing as error:
        st.info(str(error))
        st.caption("Use Refresh data in the sidebar to check again. Customer results remain available in the Customer workspace.")
        return
    st.caption(summary["disclaimer"])
    with st.container(horizontal=True):
        st.metric("Customers", summary["total_customers"], border=True)
        st.metric("Supported opportunities", summary["recommended_count"], border=True)
        st.metric("Product decisions", summary["total_recommendations"], border=True)
        st.metric("Available impact estimates", summary["available_impact_count"], border=True)
    if summary["total_customers"] == 0:
        st.info("No customers match these filters. Clear filters to return to the full synthetic portfolio.")
        return
    analytics = summary.get("analytics", {})
    if analytics:
        st.subheader("Physical potential and evidence quality")
        physical = analytics["physical_impact"]
        st.caption(physical["limitation"])
        if physical["groups"]:
            st.dataframe(physical["groups"], hide_index=True)
        else:
            st.info("Physical potential is unavailable for this selection.")
        st.write("Data quality counts", analytics["quality_counts"])
        st.write("Missing evidence counts", analytics["missingness"])
    with st.container(border=True):
        st.subheader("Product decision states")
        st.plotly_chart(opportunities_chart(summary["product_opportunities"]), key="products_chart",
                        alt="Counts of all six recommendation states by product", config={"scrollZoom": False})
        st.dataframe(summary["product_opportunities"], hide_index=True, alt="Product opportunity counts and available impact counts")
    cols = st.columns(2)
    for col, key, title in zip(cols, ("region_summaries", "segment_summaries"), ("By region", "By segment")):
        with col:
            with st.container(border=True):
                st.subheader(title)
                st.plotly_chart(groups_chart(summary[key]), key=key + "_chart", alt=f"Supported opportunity counts {title.lower()}", config={"scrollZoom": False})
                st.dataframe(summary[key], hide_index=True, alt=f"Customer and supported opportunity counts {title.lower()}")
    with st.container(border=True):
        st.subheader("Monthly trend")
        try:
            trends = load("/portfolio/trends", params)
        except APIPreparing as error:
            st.info(str(error))
            st.caption("Monthly history is preparing. Use Refresh data in the sidebar to check again; the portfolio summary above is ready.")
            return
        st.caption(trends["disclaimer"])
        historical = trends.get("analytics", {})
        if historical:
            st.caption(historical["limitation"])
            evidence = historical["observations"]
            st.dataframe([{**{key: value for key, value in row.items() if key != "physical_impact_groups"},
                           "observed_conversion_rate": percentage(row["observed_conversion_rate"])}
                          for row in evidence], hide_index=True)
            impact_rows = [{"month": row["month"], "product": row["product"], **group}
                           for row in evidence for group in row["physical_impact_groups"]]
            if impact_rows:
                st.dataframe(impact_rows, hide_index=True)
        if trends["observations"]:
            st.plotly_chart(trends_chart(trends["observations"]), key="trends_chart", alt="Historical synthetic monthly supported opportunities for each product", config={"scrollZoom": False})
            with st.expander("Historical observations"):
                st.dataframe(trends["observations"], hide_index=True, alt="Synthetic historical monthly product decisions")
        else:
            st.info("No historical observations are available for these filters.")
