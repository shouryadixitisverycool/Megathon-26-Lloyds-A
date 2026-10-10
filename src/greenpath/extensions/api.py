"""HTTP boundaries for governed memory, oversight and scenario tools."""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from greenpath import config
from greenpath.contracts.enums import Product
from greenpath.extensions.contracts import (
    CampaignRequest, CustomerRequest, FeedbackRequest, PlanningRequest,
    PreferencesRequest, ReviewRequest, SensitivityRequest, SimulationRequest,
)
from greenpath.extensions.service import ExtensionService, communication, dump, prioritise
from greenpath.extensions.store import MemoryStore

SENSITIVITY_FIELDS = {
    "annual_mileage_km": (0, 200000, "contextual"),
    "fuel_spend_90d_avg": (0, 10000, "contextual"),
    "electricity_kwh_12m": (0, 200000, "contextual"),
    "gas_kwh_12m": (0, 500000, "contextual"),
    "paper_statements_12m": (0, 1000, "actionable"),
    "app_logins_3m_avg": (0, 10000, "contextual"),
}


def attach_extensions(application, memory_path: Path | None = None):
    state = application.state
    service = ExtensionService(state.snapshot_provider, state.recommendation_service,
                               state.explanation_service, state.repository,
                               MemoryStore(memory_path or config.DATA_DIR / "greenpath.sqlite3"))
    state.extension_service = service
    router = APIRouter()

    def row(customer_id, product):
        try:
            return service.row(customer_id, product)
        except (KeyError, StopIteration):
            raise HTTPException(404, "Customer or product not found") from None

    def customer(customer_id):
        try:
            return service.snapshot(customer_id)
        except KeyError:
            raise HTTPException(404, "Customer not found") from None

    @router.post("/recommend")
    def recommend(request: CustomerRequest):
        return row(request.customer_id, request.product)

    @router.post("/explain")
    def explain(request: CustomerRequest):
        row(request.customer_id, request.product)
        rec = next(r for r in service.recommendations.recommendations(request.customer_id) if r.product == request.product)
        return service.explanations.explain(rec)

    @router.get("/customers/{customer_id}/impact/{product}")
    def passport(customer_id: str, product: Product):
        rec = row(customer_id, product)
        return {"passport_id": f"{customer_id}:{product}:{rec['impact']['method_version']}",
                "status_label": "MODELLED ESTIMATE, NOT MEASURED OUTCOME", **rec["impact"]}

    @router.post("/feedback")
    def feedback(request: FeedbackRequest):
        row(request.customer_id, request.product)
        try:
            return service.feedback(request)
        except ValueError as error:
            raise HTTPException(409, str(error)) from error

    @router.post("/review")
    def review(request: ReviewRequest):
        rec = row(request.customer_id, request.product)
        try:
            return service.store.append(request.customer_id, str(request.product), "review", request.model_dump(mode="json"),
                {"action": request.action, "reviewer": request.reviewer, "note": request.note, "recommendation": rec,
                 "limitation": "Review actions affect outreach only; scores, confidence, eligibility and impact remain immutable."})
        except ValueError as error:
            raise HTTPException(409, str(error)) from error

    @router.get("/customers/{customer_id}/history")
    def history(customer_id: str, product: Product | None = None):
        customer(customer_id)
        return {"events": service.store.history(customer_id, str(product) if product else None),
                "source_history": [dump(e) for e in state.history_provider.list_history() if e.customer_id == customer_id and (product is None or e.product == product)],
                "limitation": "Feedback history is an audit trail. Factual completion must update source data before rescoring."}

    @router.get("/customers/{customer_id}/preferences")
    def preferences(customer_id: str):
        customer(customer_id)
        return service.preferences(customer_id)

    @router.post("/customers/{customer_id}/preferences")
    def set_preferences(customer_id: str, request: PreferencesRequest):
        customer(customer_id)
        try:
            return service.store.append(customer_id, "ALL", "preferences", request.model_dump(mode="json"),
                                        {"preferences": request.model_dump(exclude={"request_id"})})
        except ValueError as error:
            raise HTTPException(409, str(error)) from error

    @router.get("/customers/{customer_id}/next-actions")
    def actions(customer_id: str, channel: str = Query("app", pattern="^(app|email|phone|rm)$")):
        rows = prioritise(service.rows(customer_id))
        for rec in rows:
            action, reason = communication(rec, service.store.history(customer_id), service.preferences(customer_id), channel)
            rec["next_action"] = {"action": action, "reason": reason, "channel": channel, "version": "next-action-rules-v1"}
        return {"opportunities": rows}

    @router.get("/customers/{customer_id}/evidence-graph/{product}")
    def graph(customer_id: str, product: Product):
        rec = row(customer_id, product)
        nodes = [{"id": "decision", "type": "decision", "label": rec["state"]}]
        edges = []
        for index, evidence in enumerate(rec["evidence"]):
            node_id = f"evidence-{index}"
            nodes.append({"id": node_id, "type": "reason", "label": evidence["code"], "detail": evidence})
            edges.append({"from": node_id, "to": "decision", "relation": "supports_or_excludes"})
            for field in evidence["fields"]:
                field_id = "field-" + field
                if not any(n["id"] == field_id for n in nodes):
                    nodes.append({"id": field_id, "type": "feature", "label": field})
                edges.append({"from": field_id, "to": node_id, "relation": "evidence"})
        nodes.append({"id": "impact", "type": "impact", "label": rec["impact"]["status"], "method_version": rec["impact"]["method_version"]})
        edges.append({"from": "decision", "to": "impact", "relation": "separate_physical_estimate"})
        return {"nodes": nodes, "edges": edges, "limitation": "Reason associations are evidence provenance, not causal effects."}

    @router.post("/customers/{customer_id}/simulate")
    def simulate(customer_id: str, request: SimulationRequest):
        snap = customer(customer_id)
        if request.inputs.get("geography") == "UK":
            from greenpath.extensions.uk_impact import METHOD_VERSION, calculate
            try:
                impact = calculate(request.product, {k: v for k, v in request.inputs.items() if k != "geography"})
            except (ValueError, OSError, KeyError) as error:
                impact = {"status": "UNAVAILABLE", "potential_reduction": None,
                          "method_version": METHOD_VERSION, "issues": [str(error)]}
            impact["feature_cutoff"] = snap.feature_cutoff.isoformat()
            method_version = impact["method_version"]
        else:
            from greenpath.impact import build_registry
            result = build_registry()[request.product].calculate(request.inputs)
            impact, method_version = dump(result), result.method_version
        payload = {"scenario_inputs": request.inputs, "impact": impact,
                   "method_version": method_version, "limitation": "User scenario assumptions; not measured activity, eligibility or a change to model propensity."}
        try:
            return service.store.append(customer_id, str(request.product), "simulation", request.model_dump(mode="json"), payload)
        except ValueError as error:
            raise HTTPException(409, str(error)) from error

    @router.get("/customers/{customer_id}/simulation-inputs/{product}")
    def simulation_inputs(customer_id: str, product: Product):
        snap = customer(customer_id)
        if snap.source_snapshot is not None:
            source = snap.source_snapshot
            return {"profile": "uk", "inputs": {
                "geography": "UK", "annual_mileage_km": source.vehicle.annual_mileage_km,
                "fuel_type": source.vehicle.fuel_type.value if source.vehicle.fuel_type else None,
                "annual_electricity_kwh": source.energy.electricity_kwh_12m,
                "annual_gas_kwh": source.energy.gas_kwh_12m,
                "paper_statements_12m": source.digital.paper_statements_12m,
                "region": snap.region,
            }, "limitation": "Observed synthetic baseline only. Supply and review proposed physical scenario inputs before any impact estimate."}
        payload = service.repository.get_impact_input(customer_id, product)
        return {"profile": "fixture", "inputs": payload,
                "limitation": "Synthetic India fixture. Edited quantities are user forecast assumptions, not measured outcomes."}

    @router.post("/customers/{customer_id}/sensitivity")
    def sensitivity(customer_id: str, request: SensitivityRequest):
        snap = customer(customer_id)
        runtime = getattr(service.repository, "runtime", None)
        if runtime is None or snap.source_snapshot is None:
            raise HTTPException(409, "Sensitivity requires trained model artifacts, not fixture probabilities")
        bundle = runtime.bundles[request.product]
        for field, value in request.changes.items():
            if field not in SENSITIVITY_FIELDS or field not in bundle.features:
                raise HTTPException(422, f"{field} is not an approved sensitivity input for this product")
            lo, hi, _ = SENSITIVITY_FIELDS[field]
            if value is not None and not lo <= value <= hi:
                raise HTTPException(422, f"{field} must be between {lo} and {hi}")
        source = snap.source_snapshot
        changed = source.model_copy(update={"features": {**source.features, **request.changes}})
        baseline = runtime.propensity.score(source, request.product)
        scenario = runtime.propensity.score(changed, request.product)
        payload = {"changes": request.changes, "feature_classes": {k: SENSITIVITY_FIELDS[k][2] for k in request.changes},
                   "baseline_probability": baseline.propensity, "scenario_probability": scenario.propensity,
                   "model_version": scenario.model_version, "calibration_version": scenario.calibration_version,
                   "limitation": "Sensitivity analysis shows the model response to scenario inputs. It is not causal advice, eligibility or a factual source-data update."}
        try:
            return service.store.append(customer_id, str(request.product), "sensitivity", request.model_dump(mode="json"), payload)
        except ValueError as error:
            raise HTTPException(409, str(error)) from error

    @router.get("/portfolio/opportunities")
    def opportunities(region: str | None = None, segment: str | None = None, product: Product | None = None,
                      status: str | None = None, min_propensity: float = Query(0, ge=0, le=1), min_trust: float = Query(0, ge=0, le=1)):
        return {"opportunities": service.opportunities(region, segment, product, status, min_propensity, min_trust),
                "disclaimer": "Propensity, validated confidence, Trust and physical impact are separate dimensions. Missing priority components are never invented."}

    @router.get("/portfolio/segments")
    def segments():
        from greenpath.api.portfolio import summarize
        snaps = tuple(state.snapshot_provider.list_snapshots())
        result = summarize(snaps, {s.customer_id: state.recommendation_service.recommendations(s.customer_id) for s in snaps})
        return {"regions": result.region_summaries, "segments": result.segment_summaries}

    @router.post("/portfolio/scenarios")
    def plan(request: PlanningRequest):
        return service.plan(request)

    @router.post("/campaigns/optimise")
    def campaign(request: CampaignRequest):
        if request.execute and not request.request_id:
            raise HTTPException(422, "Simulated campaign execution requires an idempotent request_id")
        try:
            return service.plan(request, campaign=True)
        except ValueError as error:
            raise HTTPException(409, str(error)) from error

    @router.get("/audit/recommendations/{event_id}")
    def audit(event_id: str):
        event = service.store.get_event(event_id)
        if event is None:
            raise HTTPException(404, "Audit event not found")
        return event

    @router.get("/governance/diagnostics")
    def governance():
        report_names = ("ml_evaluation", "confidence_validation", "leakage_checks", "feature_drift", "explanation_evaluation", "scenario_evaluation", "run_manifest", "system_performance")
        reports = {}
        for name in report_names:
            filename = "RUN_MANIFEST.json" if name == "run_manifest" else name + ".json"
            path = config.REPORTS_DIR / filename
            if path.is_file():
                try:
                    reports[name] = json.loads(path.read_text())
                except (ValueError, OSError):
                    reports[name] = {"status": "INVALID_REPORT"}
            else:
                reports[name] = {"status": "NOT_RUN"}
        return {"reports": reports, "model_source": getattr(service.repository, "version", "fixture"),
                "limitations": ["Synthetic labels do not establish real-world model performance.", "Confidence is suppressed unless its held-out reliability validation passes.", "Audit groups never enter default propensity features.", "No financial eligibility is assessed."]}

    application.include_router(router)
    return service
