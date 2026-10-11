"""HTTP-only tools for customer journeys, staff review and scenario planning."""

from copy import deepcopy
import json
from uuid import uuid4

import pandas as pd
import plotly.express as px
import streamlit as st

from greenpath.app.client import APIClient, APIError
from greenpath.app.presentation import PRODUCTS, STATES, percentage, impact_label
from greenpath.app.views import safe_select, impact_details


def submit(save, path, payload):
    try:
        result = save(path, {**payload, "request_id": str(uuid4())})
    except APIError as error:
        st.error(str(error))
        return None
    st.success("Saved to the local demonstration audit trail.")
    if result.get("limitation"):
        st.caption(result["limitation"])
    if result.get("id"):
        st.caption("Audit event: " + result["id"])
    return result


def select_customer(customers, key):
    lookup = {row["customer_id"]: row for row in customers}
    return safe_select("Customer", list(lookup), key,
                       format_func=lambda value: f"{value} · {lookup[value]['display_name']}")


def journey_tools(customer_id, product, load, save):
    path = APIClient.customer_path(customer_id)
    st.subheader("Your preferences and response")
    prefs = load(path + "/preferences")
    with st.form("preferences_" + customer_id):
        stop = st.checkbox("Do not contact me", value=prefs.get("do_not_contact", False))
        consent = {}
        cols = st.columns(4)
        for col, channel in zip(cols, ("app", "email", "phone", "rm"), strict=True):
            consent[channel] = col.checkbox("Allow " + ("relationship manager" if channel == "rm" else channel),
                                           value=prefs.get("channel_consent", {}).get(channel, False))
        if st.form_submit_button("Save contact preferences"):
            submit(save, path + "/preferences", {"do_not_contact": stop, "channel_consent": consent})
    with st.form("feedback_" + customer_id + product):
        response = st.selectbox("Response", ["INTERESTED", "NOT_INTERESTED", "LATER", "ALREADY_COMPLETED", "DO_NOT_SHOW_AGAIN", "SHOWN", "ACCEPTED", "CLOSED"])
        note = st.text_area("Optional note", max_chars=2000)
        if st.form_submit_button("Record response"):
            submit(save, "/feedback", {"customer_id": customer_id, "product": product,
                                       "response": response, "channel": "app", "note": note})
    history = load(path + "/history", {"product": product})
    st.caption(history.get("limitation", ""))
    events = history.get("events", [])
    if events:
        st.dataframe([{"When": e["timestamp"], "Event": e["kind"],
                       "State": e.get("lifecycle_state", e.get("action", "")),
                       "Note": e.get("note", ""), "Audit event": e["id"]} for e in events], hide_index=True)
    else:
        st.info("No response or review events recorded yet.")
    with st.expander("Source decision history"):
        st.json(history.get("source_history", []))


def scenario_tools(customer_id, product, load, save):
    path = APIClient.customer_path(customer_id)
    st.subheader("What-if laboratory")
    st.caption("Scenario assumptions change the physical estimate. They do not update your customer record, model propensity or financial eligibility.")
    try:
        template = load(path + "/simulation-inputs/" + product)
    except APIError as error:
        st.info(str(error))
        model_sensitivity_tools(customer_id, product, save)
        return
    original = template.get("inputs")
    if template.get("profile") == "uk":
        uk_scenario_tools(customer_id, product, template, save)
        model_sensitivity_tools(customer_id, product, save)
        return
    if not original:
        st.info(template.get("limitation", "No complete input evidence is available for this scenario."))
        model_sensitivity_tools(customer_id, product, save)
        return
    with st.form("physical_" + customer_id + product):
        edits = {}
        if product == "EV_FINANCE":
            for key, label in (("scenario_distance", "Scenario annual distance, km"), ("charging_electricity", "Scenario annual charging electricity, kWh")):
                edits[key] = st.number_input(label, min_value=0.0, value=float(original[key]["value"]), step=100.0)
        elif product == "GREEN_HOME":
            edits["scenario_grid_import"] = st.number_input("Scenario annual electricity imported, kWh", min_value=0.0,
                value=float(original["scenario_grid_import"]["value"]), step=100.0)
        elif product == "SOLAR_FINANCE":
            baseline = sum(float(i["baseline_grid_import"]["value"]) for i in original["intervals"])
            current = sum(float(i["self_consumed_solar"]["value"]) for i in original["intervals"])
            edits["solar_share"] = st.slider("Share of baseline grid imports displaced by self-consumed solar", 0.0, 1.0,
                min(current / baseline if baseline else 0.0, 1.0), step=0.01)
        else:
            st.info("Paperless is reported as an environmental action. A carbon scenario requires verified lifecycle factors.")
        run = st.form_submit_button("Calculate physical scenario", disabled=product == "PAPERLESS_BANKING")
    if run:
        inputs = deepcopy(original)
        changed = []
        if product == "SOLAR_FINANCE":
            for interval in inputs["intervals"]:
                fact = interval["self_consumed_solar"]
                fact["value"] = str(float(interval["baseline_grid_import"]["value"]) * edits["solar_share"])
                changed.append(fact)
        else:
            for field, value in edits.items():
                inputs[field]["value"] = str(value)
                changed.append(inputs[field])
        for fact in changed:
            fact["evidence"].update(basis="engineering_forecast", reference="user-scenario-assumption", freshness="current", conflicts=[])
        result = submit(save, path + "/simulate", {"product": product, "inputs": inputs})
        if result:
            st.metric("Scenario potential impact", impact_label(result["impact"]))
            impact_details(result["impact"])
    model_sensitivity_tools(customer_id, product, save)


def model_sensitivity_tools(customer_id, product, save):
    path = APIClient.customer_path(customer_id)
    with st.expander("Model sensitivity analysis"):
        st.caption("The model response to changed inputs is not causal advice. Mileage, energy use and app use are contextual. Paper statement choice is actionable.")
        fields = {"EV_FINANCE": ["annual_mileage_km", "fuel_spend_90d_avg"],
                  "GREEN_HOME": ["electricity_kwh_12m", "gas_kwh_12m"],
                  "SOLAR_FINANCE": ["electricity_kwh_12m"],
                  "PAPERLESS_BANKING": ["paper_statements_12m", "app_logins_3m_avg"]}[product]
        with st.form("sensitivity_" + customer_id + product):
            field = st.selectbox("Scenario input", fields)
            value = st.number_input("Scenario value", min_value=0.0, value=0.0)
            if st.form_submit_button("Evaluate model sensitivity"):
                result = submit(save, path + "/sensitivity", {"product": product, "changes": {field: value}})
                if result:
                    cols = st.columns(2)
                    cols[0].metric("Baseline propensity", percentage(result["baseline_probability"]))
                    cols[1].metric("Scenario propensity", percentage(result["scenario_probability"]))
        with st.form("counterfactual_" + customer_id + product):
            st.caption("Bounded search evaluates user-supplied feature combinations through trained inference. Protected fields are excluded. Contextual inputs are not recommended actions.")
            candidates = st.text_area("Candidate values as JSON", value=json.dumps({fields[0]: [0.0]}))
            target = st.slider("Target model propensity", 0.0, 1.0, 0.6, step=0.01)
            if st.form_submit_button("Search model scenarios"):
                try:
                    parsed = json.loads(candidates)
                except ValueError:
                    st.error("Candidate values must be valid JSON.")
                else:
                    result = submit(save, path + "/counterfactual-search", {"product": product, "candidates": parsed,
                                                                          "target_probability": target, "max_evaluations": 64})
                    if result:
                        st.caption(result["limitation"])
                        st.write("Feature classes", result["feature_classes"])
                        st.dataframe(result["results"], hide_index=True)
                        if result["truncated"]:
                            st.warning("The candidate grid exceeded the evaluation budget; results are a bounded partial search.")


def uk_scenario_tools(customer_id, product, template, save):
    st.caption(template.get("limitation", ""))
    observed = template.get("inputs") or {}
    intervention = st.selectbox("Proposed home intervention", ["INSULATION", "HEAT_PUMP"]) if product == "GREEN_HOME" else None
    with st.form("uk_physical_" + customer_id + product):
        inputs = {"geography": "UK"}
        def quantity(key, label, maximum, baseline=None, integer=False):
            source = observed.get(baseline) if baseline else None
            value = None if source is None else int(source) if integer else float(source)
            inputs[key] = st.number_input(label, min_value=0 if integer else 0.0,
                max_value=int(maximum) if integer else float(maximum), value=value,
                step=1 if integer else 0.01, key="uk_" + customer_id + product + key)
        if product == "EV_FINANCE":
            quantity("annual_mileage_km", "Annual scenario distance, km", 200000, "annual_mileage_km")
            fuels = ["PETROL", "DIESEL"]
            fuel = observed.get("fuel_type")
            inputs["fuel_type"] = st.selectbox("Baseline fuel", fuels, index=fuels.index(fuel) if fuel in fuels else None)
            quantity("ice_litres_per_100km", "Baseline fuel use, litres per 100 km", 50)
            quantity("ev_kwh_per_100km", "Proposed EV battery use, kWh per 100 km", 100)
            quantity("charging_efficiency", "Charging efficiency, fraction from 0 to 1", 1)
            inputs["mileage_evidence"] = "USER_SCENARIO"
        elif product == "SOLAR_FINANCE":
            quantity("annual_electricity_kwh", "Annual electricity demand, kWh", 200000, "annual_electricity_kwh")
            quantity("annual_generation_kwh", "Proposed annual solar generation, kWh", 200000)
            quantity("proposed_capacity_kw", "Proposed solar array capacity, kW", 1000)
            quantity("self_consumption_fraction", "Generation self-consumed, fraction from 0 to 1", 1)
            inputs["region"] = st.text_input("Property region", value=observed.get("region") or "")
            inputs["generation_evidence"] = st.text_input("Generation forecast source or assumption", max_chars=1000)
        elif product == "GREEN_HOME":
            inputs["intervention"] = intervention
            if intervention == "INSULATION":
                quantity("annual_electricity_kwh", "Annual electricity demand, kWh", 200000, "annual_electricity_kwh")
                quantity("annual_gas_kwh_gross", "Annual gas demand, gross kWh", 500000, "annual_gas_kwh")
                quantity("electricity_saving_fraction", "Proposed electricity savings, fraction from 0 to 1", 1)
                quantity("gas_saving_fraction", "Proposed gas savings, fraction from 0 to 1", 1)
                inputs["savings_evidence"] = st.text_input("Savings assessment source or assumption", max_chars=1000)
            else:
                quantity("annual_heating_gas_kwh_gross", "Annual gas used for heating only, gross kWh", 500000)
                quantity("boiler_efficiency_gross", "Baseline boiler efficiency, gross fraction from 0 to 1", 1)
                quantity("seasonal_performance_factor", "Proposed heat-pump seasonal performance factor", 10)
                inputs["performance_evidence"] = st.text_input("Performance assessment source or assumption", max_chars=1000)
        else:
            quantity("annual_statements", "Annual paper statements", 10000, "paper_statements_12m", integer=True)
            quantity("sheets_per_statement", "Sheets per statement", 100, integer=True)
            quantity("avoided_fraction", "Statements avoided, fraction from 0 to 1", 1)
        st.caption("Observed synthetic baseline values may be edited as scenario assumptions. Blank forecast fields stay unknown; no engineering defaults are invented.")
        run = st.form_submit_button("Calculate UK scenario")
    if run:
        missing = [key for key, value in inputs.items() if value is None or value == ""]
        if missing:
            st.error("Supply each physical scenario input and its assessment source before calculating.")
            return
        result = submit(save, APIClient.customer_path(customer_id, "/simulate"), {"product": product, "inputs": inputs})
        if result:
            impact = result["impact"]
            if impact["status"] == "UNAVAILABLE":
                st.warning("No defensible physical estimate is available for these scenario inputs.")
                for issue in impact.get("issues", []):
                    st.warning(str(issue))
            elif impact["status"] == "NOT_CLAIMED":
                cols = st.columns(2)
                cols[0].metric("Paper statements avoided", impact["paper_statements_avoided"])
                cols[1].metric("Paper sheets avoided", impact["paper_sheets_avoided"])
                st.caption(impact["limitation"])
            else:
                cols = st.columns(3)
                for col, key, label in zip(cols, ("baseline_emissions", "scenario_emissions", "potential_reduction"),
                                           ("Baseline emissions", "Scenario emissions", "Potential reduction"), strict=True):
                    col.metric(label, f'{float(impact[key]):,.2f} {impact["units"]}')
                st.caption(impact["boundary"])
                for limitation in impact.get("limitations", []):
                    st.caption(limitation)
                with st.expander("UK impact passport and factor sources", expanded=True):
                    st.caption(f'{impact["passport_id"]} · {impact["method_version"]} · {impact["factor_vintage"]}')
                    st.write(impact["formula"])
                    st.dataframe(pd.DataFrame(impact["factor_records"]).T)
                    st.link_button("Official factor source", impact["factor_source"])
                    st.text("Source SHA-256: " + impact["factor_source_sha256"])


def promo_preview(path, product, channel, load):
    try:
        banner, card = (load(path + "/promos/" + product, {"format": fmt, "channel": channel}) for fmt in ("one_liner", "short"))
    except APIError as error:
        st.error(str(error))
        return
    if banner["status"] == "WITHHELD":
        st.info(f"No message suggested: {banner['withheld_reason']}.")
        return
    for label, promo in (("Banner", banner), ("Card", card)):
        source = "AI-written, passed copy checks" if promo["source"] == "llm" else f"Template ({promo['fallback_reason']})"
        st.markdown(f"**{label}** · {source}")
        st.markdown("  \n".join(promo["lines"]) + f"  \n`{promo['cta_label']}`")
    st.caption(banner["disclaimer"] + " Copy is written only from the decision, its reason themes and the carbon estimate.")


def rm_view(customers, load, save):
    st.header("Relationship Manager", icon=":material/support_agent:")
    st.caption("Evidence before outreach. Review actions affect communication; customer scores and impact calculations stay governed by their source records.")
    customer_id = select_customer(customers, "rm_customer")
    path = APIClient.customer_path(customer_id)
    channel = st.selectbox("Contact channel", ["rm", "app", "email", "phone"], key="rm_channel")
    opportunities = load(path + "/next-actions", {"channel": channel})["opportunities"]
    st.dataframe([{"Product": PRODUCTS.get(r["product"], r["product"]), "State": r["state"],
                   "Propensity": percentage((r.get("propensity") or {}).get("probability")),
                   "Trust": percentage(r["trust"]["score"]), "Impact": impact_label(r["impact"]),
                   "Next action": r["next_action"]["action"], "Reason": r["next_action"]["reason"]} for r in opportunities], hide_index=True)
    product = safe_select("Review product", [r["product"] for r in opportunities], "rm_product", format_func=lambda v: PRODUCTS.get(v, v))
    row = next(r for r in opportunities if r["product"] == product)
    with st.form("review_" + customer_id + product):
        action = st.selectbox("Review action", ["REQUEST_REVIEW", "FLAG_DATA_ISSUE", "SUPPRESS", "ACCEPT"])
        reviewer = st.text_input("Reviewer name", max_chars=100)
        note = st.text_area("Review rationale", max_chars=2000)
        if st.form_submit_button("Record human review"):
            if not reviewer.strip() or not note.strip():
                st.error("A reviewer name and rationale are required.")
            else:
                submit(save, "/review", {"customer_id": customer_id, "product": product, "action": action,
                                          "reviewer": reviewer, "note": note})
    with st.expander("Suggested message", expanded=row["next_action"]["action"] in {"SHOW_EDUCATION", "RM_DISCUSSION"}):
        promo_preview(path, product, channel, load)
    graph = load(path + "/evidence-graph/" + product)
    with st.expander("Evidence provenance graph", expanded=True):
        lines = ["digraph evidence { rankdir=LR;"]
        for node in graph["nodes"]:
            lines.append(f'{json.dumps(node["id"])} [label={json.dumps(node["label"])}];')
        for edge in graph["edges"]:
            lines.append(f'{json.dumps(edge["from"])} -> {json.dumps(edge["to"])};')
        st.graphviz_chart("\n".join(lines) + "\n}")
        st.caption(graph["limitation"])
    with st.expander("Scored evidence and model trace"):
        st.json(row)
        customer = load(path)
        if customer.get("source_snapshot"):
            st.json(customer["source_snapshot"])
    journey_tools(customer_id, product, load, save)
    scenario_tools(customer_id, product, load, save)
    with st.expander("Inspect an audit event"):
        event_id = st.text_input("Audit event ID", key="audit_event_id")
        if st.button("Load audit event") and event_id.strip():
            try:
                st.json(load("/audit/recommendations/" + event_id.strip()))
            except APIError as error:
                st.error(str(error))


def planning_view(customers, load, save):
    st.header("Portfolio planning", icon=":material/tune:")
    st.caption("Explore product-specific opportunities and constrained campaign scenarios. Conversion is an explicit assumption; modelled impact is separate from propensity.")
    product = safe_select("Planning product", list(PRODUCTS), "plan_product", format_func=lambda v: PRODUCTS.get(v, v))
    cols = st.columns(2)
    with cols[0]:
        region = safe_select("Planning region", ["All"] + sorted({r["region"] for r in customers}), "plan_region")
    matching = [r for r in customers if region == "All" or r["region"] == region]
    with cols[1]:
        segment = safe_select("Planning segment", ["All"] + sorted({r["segment"] for r in matching}), "plan_segment")
    params = {"product": product, **({"region": region} if region != "All" else {}), **({"segment": segment} if segment != "All" else {})}
    with st.expander("Opportunity filters", expanded=True):
        state = safe_select("Decision state", ["All", *STATES], "plan_state")
        cols = st.columns(3)
        probability = cols[0].slider("Minimum propensity", 0.0, 1.0, 0.0, key="min_probability")
        trust = cols[1].slider("Minimum Trust", 0.0, 1.0, 0.0, key="min_trust")
        confidence = cols[2].slider("Minimum validated confidence", 0.0, 1.0, 0.0, key="min_confidence")
        quality = st.selectbox("Data quality", ["All", "TRUSTED", "LIMITED", "CONFLICT", "OOD"])
        impact = st.number_input("Minimum available annual impact, displayed units", min_value=0.0, value=0.0, key="min_impact")
        st.caption("A positive confidence filter excludes unvalidated confidence. A positive impact filter excludes unavailable estimates. These filters apply to the opportunity table and matrix.")
    if state != "All":
        params["status"] = state
    if quality != "All":
        params["data_quality"] = quality
    for key, value in (("min_propensity", probability), ("min_trust", trust), ("min_confidence", confidence), ("min_impact", impact)):
        if value > 0:
            params[key] = str(value)
    response = load("/portfolio/opportunities", params)
    st.caption(response["disclaimer"])
    rows = response["opportunities"]
    table = [{"Customer": r["customer_id"], "State": r["state"], "Propensity": percentage((r.get("propensity") or {}).get("probability")),
              "Trust": percentage(r["trust"]["score"]), "Impact": impact_label(r["impact"]),
              "Priority": percentage(r["priority"]["score"]),
              "Priority rank": str(r["priority"]["rank"]) if r["priority"]["score"] is not None and r["priority"]["rank"] is not None else "Unavailable",
              "Ordering basis": ("Composite priority" if r["priority"]["score"] is not None else
                                 "Calibrated propensity (not composite priority)" if (r.get("propensity") or {}).get("probability") is not None else
                                 "Deterministic tie-break (propensity unavailable)"),
              "Expected sustainability impact": ((r.get("expected_sustainability_impact") or {}).get("value") or "Unavailable") + " " + r["impact"]["units"]} for r in rows]
    st.dataframe(table, hide_index=True)
    points = [{"Customer": r["customer_id"], "Propensity": float(r["propensity"]["probability"]),
               "Impact": float(r["impact"]["value"]), "State": r["state"], "Units": r["impact"]["units"],
               "Compatibility": json.dumps((r.get("expected_sustainability_impact") or {}).get("compatibility_group") or
                                            [r["product"], r["impact"]["units"], r["impact"]["boundary"], r["impact"].get("period"),
                                             r["impact"]["method_version"], r["impact"]["factor_catalogue_version"]])}
              for r in rows if r.get("propensity") and r["propensity"].get("probability") is not None and r["impact"]["status"] == "AVAILABLE" and r["impact"].get("value") is not None]
    if points:
        data = pd.DataFrame(points)
        for group, compatible in data.groupby("Compatibility"):
            st.caption("Comparable impact group: " + group)
            st.plotly_chart(px.scatter(compatible, x="Propensity", y="Impact", color="State", hover_name="Customer",
                                      labels={"Impact": "Potential impact, " + compatible["Units"].iloc[0]}), key="scatter_" + group)
    else:
        st.info("No comparable propensity and physical-impact pairs are available for this product.")
    with st.form("campaign_planner"):
        st.subheader("Scenario assumptions")
        count = st.number_input("Target customers", 0, 100000, 100, step=10)
        conversion = st.slider("Assumed conversion rate", 0.0, 1.0, 0.05, step=0.01)
        capacity = st.number_input("Channel capacity", 0, 100000, 100, step=10)
        channel = st.selectbox("Campaign channel", ["app", "email", "phone", "rm"])
        objective = st.selectbox("Campaign objective", ["conversions", "impact", "balanced"])
        execute = st.checkbox("Record simulated contacts locally")
        st.caption("No messages are sent. Consent, suppression, contact limits, capacity and fatigue rules apply.")
        planning = st.form_submit_button("Calculate portfolio scenario")
        campaign = st.form_submit_button("Optimise simulated campaign")
    if planning or campaign:
        payload = {"product": product, "target_count": count, "conversion_rate": conversion,
                   "region": None if region == "All" else region, "segment": None if segment == "All" else segment,
                   "channel": channel}
        if campaign:
            payload.update(channel=channel, objective=objective, channel_capacity=capacity, execute=execute)
        result = submit(save, "/campaigns/optimise" if campaign else "/portfolio/scenarios", payload)
        if result:
            cols = st.columns(3)
            cols[0].metric("Selected customers", result["selected_count"])
            cols[1].metric("Scenario adopters", f'{result["scenario_adopters"]:,.1f}')
            cols[2].metric("Average propensity", percentage(result["average_propensity"]))
            st.caption(result["disclaimer"])
            st.caption("Impact totals are separated by product, boundary, period and factor version.")
            if result.get("impact_status") == "UNAVAILABLE":
                st.info("Physical impact is unavailable for this selection. No carbon total is inferred.")
            if result.get("capacity_budget"):
                st.write("Persistent channel capacity", result["capacity_budget"])
            st.dataframe(result["impact_groups"], hide_index=True)
            st.write("Exclusions", result["excluded"])
            st.dataframe(result["selected"], hide_index=True)
            if result.get("execution_note"):
                st.info(result["execution_note"])
            if result.get("campaign_event_id"):
                st.caption("Campaign event ID: " + result["campaign_event_id"])


def governance_view(load):
    st.header("Responsible AI console", icon=":material/policy:")
    result = load("/governance/diagnostics")
    st.caption("Model source: " + result["model_source"])
    for limitation in result["limitations"]:
        st.info(limitation)
    reports = result["reports"]
    models = reports.get("ml_evaluation", {}).get("products", {})
    if models:
        product = safe_select("Audit product", list(models), "audit_product", format_func=lambda v: PRODUCTS.get(v, v))
        model = models[product]
        st.subheader("Held-out model comparison")
        st.caption(f"Selected model: {model.get('selected_model', 'Unavailable')} · {model.get('model_version', 'Unavailable')}")
        test = model.get("test", {})
        if test:
            st.dataframe(pd.DataFrame(test).T, hide_index=False)
        subgroups = model.get("subgroups", {})
        if subgroups:
            st.subheader("Fairness across audit groups")
            group = safe_select("Audit group", list(subgroups), "audit_group")
            table = subgroups[group].get("table", [])
            st.caption("Group size and positive counts matter. Undefined subgroup metrics remain unavailable. Audit attributes are excluded from default model features.")
            st.dataframe(table, hide_index=True)
            if table:
                st.plotly_chart(px.bar(pd.DataFrame(table), x="group", y="selection_rate",
                    hover_data=["n", "positives"], labels={"selection_rate": "Selection rate", "group": group}), key="fairness_selection")
            st.write("Disparity diagnostics", subgroups[group].get("disparity", {}))
        with st.expander("Proxy ablation, missing evidence and generator shift"):
            for key in ("proxy_ablation", "missing_data", "generator_shift", "temporal_holdout"):
                st.write(key.replace("_", " ").capitalize())
                st.json(model.get(key, {"status": "NOT_RUN"}))
        confidence = reports.get("confidence_validation", {}).get(product, {})
        validation = confidence.get("validation", {})
        if validation:
            st.subheader("Confidence reliability")
            st.badge("Validated" if validation.get("passed") else "Suppressed", color="green" if validation.get("passed") else "orange")
            st.caption("Higher confidence must correspond to lower held-out error. A failed reliability test suppresses customer confidence.")
            for reason in validation.get("reasons", []):
                st.warning(reason)
            deciles = validation.get("deciles", [])
            if deciles:
                st.plotly_chart(px.line(pd.DataFrame(deciles), x="bin", y="error_rate", markers=True,
                    labels={"bin": "Confidence bucket, low to high", "error_rate": "Held-out error rate"}), key="confidence_error")
                st.dataframe(deciles, hide_index=True)
    names = {"ml_evaluation": "Model evaluation and fairness", "confidence_validation": "Confidence reliability",
             "feature_drift": "Feature drift monitoring",
             "leakage_checks": "Leakage audit", "explanation_evaluation": "Explanation grounding",
             "scenario_evaluation": "Scenario suite", "run_manifest": "Reproducibility", "system_performance": "System performance"}
    for key, title in names.items():
        with st.expander(title, expanded=key == "confidence_validation"):
            report = result["reports"].get(key, {"status": "NOT_RUN"})
            if report.get("status") in {"NOT_RUN", "INVALID_REPORT"}:
                st.warning("Report unavailable: " + report["status"])
            else:
                st.json(report)
