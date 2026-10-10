"""Native Streamlit views receiving only API JSON."""

from urllib.parse import urlparse

import streamlit as st

from greenpath.app.client import APIError
from greenpath.app.presentation import (
    PRODUCTS, STATES, decimal_number, groups_chart, impact_label,
    opportunities_chart, percentage, trends_chart,
)


def safe_select(label, options, key, **kwargs):
    if st.session_state.get(key) not in options:
        st.session_state[key] = options[0]
    return st.selectbox(label, options, key=key, **kwargs)


def bullets(items):
    for item in items:
        st.markdown(f"- {item}")


def customer_view(customers, load, save=None, provider_mode=None):
    lookup = {item["customer_id"]: item for item in customers}
    with st.sidebar:
        st.caption("CUSTOMER FIELD NOTES")
        abstention_id = "C10004" if "C10004" in lookup else "GP-002" if "GP-002" in lookup else None
        if abstention_id:
            def abstention():
                st.session_state["customer_id"] = abstention_id
            st.button("See responsible abstention", on_click=abstention, key="abstention", width="stretch")
        customer_id = safe_select("Customer", list(lookup), "customer_id",
                                  format_func=lambda key: f"{key} · {lookup[key]['display_name']}")
        if "C10001" in lookup:
            st.caption("C10001 EV candidate · C10002 solar candidate · C10004 sparse evidence · C10005 conflicting records · C10006 already green")
        elif "GP-001" in lookup:
            st.caption("GP-001 supported · GP-002 missing evidence · GP-003 conflict · GP-004 adopted · GP-005 suppressed · GP-006 low propensity")
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
                st.caption(f"Model confidence: {confidence}. Validation is required before display.")
                st.markdown(f"Potential impact: **{impact_label(row['impact'])}**")
                if row["impact"]["status"] == "AVAILABLE":
                    st.caption("Baseline minus scenario; this is a modeled opportunity, not a realized reduction.")
                else:
                    st.caption("No defensible carbon estimate is available. An unavailable impact never means zero.")
    if not recommendations:
        st.info("The API returned no product decisions for this customer.")
        return
    st.header("Why this result?", icon=":material/fact_check:")
    by_product = {row["product"]: row for row in recommendations}
    product = safe_select("Inspect a product", list(by_product), "why_product", format_func=lambda value: PRODUCTS.get(value, value))
    row = by_product[product]
    try:
        explanation = load(f"/customers/{customer_id}/explanations/{product}")
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
    with st.expander("Versions and decision exclusions"):
        propensity = row.get("propensity") or {}
        st.text(f"Cutoff: {row['feature_cutoff']}\nDecision timestamp: {row['timestamp']}\nRules: {row['rules_version']}\nModel: {propensity.get('model_version', 'Unavailable')}\nCalibration: {propensity.get('calibration_version') or 'Unavailable'}\nTrust: {row['trust'].get('version', 'Unavailable')}\nContract: {row['contract_version']}")
        bullets(row.get("exclusions", []))
    impact_details(row["impact"])
    if save:
        from greenpath.app.workspaces import journey_tools, scenario_tools
        if st.toggle("Manage contact preferences and record a response", key="journey_open"):
            journey_tools(customer_id, product, load, save)
        if st.toggle("Explore a what-if scenario", key="scenario_open"):
            scenario_tools(customer_id, product, load, save)


def impact_details(impact):
    with st.expander("Impact method, factors and assumptions", expanded=True):
        st.subheader("Potential impact · " + impact_label(impact))
        st.markdown(impact["boundary"])
        st.caption(f"Units: {impact['units']} · Method: {impact['method_version']} · Release: {impact['method_release']} · Factor catalogue: {impact['factor_catalogue_version']}")
        st.caption(f"Calculated at: {impact['timestamp']} · Impact feature cutoff: {impact.get('feature_cutoff') or 'Unavailable'}")
        st.text(f"Factor catalogue SHA-256: {impact['factor_catalogue_sha256']}")
        if impact.get("period"):
            st.caption(f"Activity period: {impact['period']['start']} inclusive to {impact['period']['end']} exclusive")
        for key in ("baseline", "scenario"):
            scenario = impact[key]
            number = decimal_number(scenario.get("emissions_kg_co2"))
            value = f"{number:,.2f} kg CO2" if number is not None else "UNAVAILABLE"
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
    summary = load("/portfolio/summary", params)
    trends = load("/portfolio/trends", params)
    st.caption(summary["disclaimer"])
    with st.container(horizontal=True):
        st.metric("Customers", summary["total_customers"], border=True)
        st.metric("Supported opportunities", summary["recommended_count"], border=True)
        st.metric("Product decisions", summary["total_recommendations"], border=True)
        st.metric("Available impact estimates", summary["available_impact_count"], border=True)
    if summary["total_customers"] == 0:
        st.info("No customers match these filters. Clear filters to return to the full synthetic portfolio.")
        return
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
        st.caption(trends["disclaimer"])
        if trends["observations"]:
            st.plotly_chart(trends_chart(trends["observations"]), key="trends_chart", alt="Historical synthetic monthly supported opportunities for each product", config={"scrollZoom": False})
            with st.expander("Historical observations"):
                st.dataframe(trends["observations"], hide_index=True, alt="Synthetic historical monthly product decisions")
        else:
            st.info("No historical observations are available for these filters.")
