"""HTTP boundaries for governed memory, oversight and scenario tools."""

import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import ValidationError

from greenpath import config
from greenpath.contracts.enums import Product
from greenpath.contracts.lifecycle import SourceUpdateRequest
from greenpath.contracts.product import Recommendation
from greenpath.extensions.contracts import (
    CampaignRequest, CounterfactualRequest, CustomerRequest, FeedbackRequest, PlanningRequest,
    PreferencesRequest, ReviewRequest, SensitivityRequest, SimulationRequest,
)
from greenpath.extensions.service import ExtensionService, communication, dump, prioritise
from greenpath.extensions.store import MemoryStore
from greenpath.extensions.optional_models import GreenPurpose, OPPORTUNITIES, OptionalModelLoader, unavailable

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
                               state.memory_store if memory_path is None else MemoryStore(memory_path))
    state.extension_service = service
    router = APIRouter()
    optional_loader = OptionalModelLoader()
    state.optional_model_loader = optional_loader

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

    @router.get("/customers/{customer_id}/optional-opportunities")
    def optional_opportunities(customer_id: str, purpose: GreenPurpose | None = None):
        with service.store.transaction():
            snap = customer(customer_id)
            if snap is None:
                raise HTTPException(404, "Customer not found")
            source = snap.source_snapshot
            provider, status = (None, "NOT_AVAILABLE") if source is None else optional_loader.load()
            conflict = snap.trust.status in {"CONFLICT", "OOD"} or any(
                evidence.conflicts for evidence in snap.features.values()) or any(
                issue.severity == "HIGH" for issue in snap.trust.issues)
            outputs = []
            for name in OPPORTUNITIES:
                declared = purpose.value if purpose is not None and name == "GREEN_LOANS" else None
                if provider is None:
                    result = unavailable(name, status, "TRAINED_SOURCE_REQUIRED" if source is None else "OPTIONAL_" + status, declared)
                elif conflict:
                    result = unavailable(name, "INSUFFICIENT_INFORMATION", "TRUSTED_RECORD_CONFLICT", declared)
                else:
                    result = provider.score(source, name, declared)
                outputs.append(result)
            return {"customer_id": customer_id, "experimental": True, "opportunities": outputs}

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
        if request.product == Product.PAPERLESS_BANKING and request.response == "CLOSED":
            snap = customer(request.customer_id)
            if snap.source_snapshot is None or snap.source_snapshot.digital.is_paperless is not True:
                raise HTTPException(409, "Paperless closure requires a factual source update, not a feedback claim")
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
                "recommendations": service.store.recommendation_history(customer_id, str(product) if product else None),
                "source_updates": service.store.source_updates(customer_id),
                "source_history": [dump(e) for e in state.history_provider.list_history() if e.customer_id == customer_id and (product is None or e.product == product)],
                 "limitation": "Feedback history is an audit trail. Factual completion must update source data before rescoring."}

    @router.post("/customers/{customer_id}/source-updates")
    def source_update(customer_id: str, request: SourceUpdateRequest,
                      x_demo_admin_token: str | None = Header(default=None)):
        token = os.environ.get("GREENPATH_DEMO_ADMIN_TOKEN")
        if not token or not x_demo_admin_token or not secrets.compare_digest(token, x_demo_admin_token):
            raise HTTPException(403, "Authorized local demo source update required")
        snap = customer(customer_id)
        provider = state.snapshot_provider
        if snap.source_snapshot is None or not hasattr(provider, "override_source_snapshot"):
            raise HTTPException(409, "Factual updates require a trained source snapshot override provider")
        data = request.model_dump(mode="json")
        try:
            with service.store.transaction():
                replay = service.store.replay(customer_id, "ALL", "source_update", data)
                if replay:
                    return replay
                snap = customer(customer_id)
                if request.feature_cutoff > datetime.now(timezone.utc) or request.feature_cutoff < snap.feature_cutoff:
                    raise HTTPException(422, "Cutoff cannot be future-dated or precede the current source snapshot")
                source = snap.source_snapshot
                payload = source.model_dump(mode="json")
                mappings = {
                    "vehicle": {"has_vehicle": "has_vehicle", "vehicle_age_years": "vehicle_age_years",
                                "annual_mileage_km": "annual_mileage_km", "mileage_is_estimated": "mileage_is_estimated"},
                    "digital": {"is_paperless": "is_paperless", "paper_statements_3m": "paper_statements_3m",
                                "paper_statements_12m": "paper_statements_12m", "digital_statement_ratio": "digital_statement_ratio",
                                "digital_transactions_3m_avg": "digital_txn_3m_avg", "branch_visits_3m": "branch_visits_3m"},
                    "ownership": {"home_owner": "home_owner", "has_existing_solar": "has_existing_solar"},
                }
                features = payload["features"]
                for group, changes in (("vehicle", request.vehicle), ("digital", request.digital), ("ownership", request.ownership)):
                    allowed = set(mappings[group]) | ({"fuel_type"} if group == "vehicle" else set())
                    if set(changes) - allowed:
                        raise ValueError(f"Unsupported factual {group} fields: {sorted(set(changes) - allowed)}")
                    for field, value in changes.items():
                        if value is None or field == "fuel_type":
                            continue
                        boolean_fields = {"has_vehicle", "mileage_is_estimated", "is_paperless", "home_owner", "has_existing_solar"}
                        if field in boolean_fields and type(value) is not bool:
                            raise ValueError(f"{field} requires a Boolean fact, not a claim or string")
                        if field not in boolean_fields and type(value) not in {int, float}:
                            raise ValueError(f"{field} requires a numeric fact")
                    target = "home" if group == "ownership" else group
                    payload[target].update(changes)
                    for field, value in changes.items():
                        if field in mappings[group]:
                            features[mappings[group][field]] = value
                if request.vehicle:
                    payload["vehicle"]["record_updated_at"] = request.event_at.date().isoformat()
                    age = (request.feature_cutoff.date() - request.event_at.date()).days
                    features["vehicle_record_age_days"] = age
                    payload["data_quality"]["vehicle_record_age_days"] = age
                if "fuel_type" in request.vehicle:
                    fuel = request.vehicle["fuel_type"]
                    features.update(is_ev=None if fuel is None else fuel == "EV",
                                    is_ice=None if fuel is None else fuel in {"PETROL", "DIESEL"},
                                    is_hybrid=None if fuel is None else fuel == "HYBRID")
                payload["feature_cutoff"] = request.feature_cutoff.date().isoformat()
                payload["generated_at"] = datetime.now(timezone.utc).isoformat()
                payload["source_events"] = [*payload.get("source_events", []), data]
                payload.setdefault("source_versions", {}).update({group: f"local-demo:{request.request_id}:{request.source_reference}"
                    for group in ("vehicle", "digital", "ownership") if getattr(request, group)})
                updated = source.__class__.model_validate(payload)
                payload = updated.model_dump(mode="python")
                resolved = set()
                for group, changes in (("vehicle", request.vehicle), ("digital", request.digital), ("ownership", request.ownership)):
                    facts = getattr(updated, "home" if group == "ownership" else group)
                    for field in changes:
                        if field in mappings[group]:
                            value = getattr(facts, field)
                            payload["features"][mappings[group][field]] = value
                            if value is not None:
                                resolved.update((field, mappings[group][field], f"{group}.{field}"))
                payload["data_quality"]["missing_fields"] = [f for f in payload["data_quality"]["missing_fields"] if f not in resolved]
                updated = source.__class__.model_validate(payload)
                # Keep historical monthly estimates unchanged by this later local update.
                provider.list_history()
                previous_decisions = service.rows(customer_id)
                provider.override_source_snapshot(updated)
                try:
                    decisions = service.rows(customer_id)
                    closed = [r["decision_id"] for r in decisions if r["product"] == "PAPERLESS_BANKING"
                              and request.digital.get("is_paperless") is True and source.digital.is_paperless is not True
                              and updated.digital.is_paperless is True and r["state"] == "NOT_APPLICABLE"]
                    event = service.store.append(customer_id, "ALL", "source_update", data, {
                        "actor": request.actor, "reason": request.reason, "source_reference": request.source_reference,
                        "event_at": data["event_at"], "available_at": data["available_at"], "feature_cutoff": data["feature_cutoff"],
                        "source_snapshot": updated.model_dump(mode="json"), "previous_source_snapshot": source.model_dump(mode="json"),
                        "recommendations": decisions, "automatically_closed_decisions": closed,
                        "lifecycle_state": "CLOSED" if closed else "RESCORED",
                        "limitation": "Local synthetic factual source update; genuine model inference, not a measured sustainability outcome.",
                    })
                    if closed:
                        service.store.append(customer_id, str(Product.PAPERLESS_BANKING), "source_completion",
                            {"request_id": request.request_id + ":paperless-close", "source_update_id": event["id"]},
                            {"lifecycle_state": "CLOSED", "automatic": True, "source_update_id": event["id"],
                             "closed_decision_ids": [r["decision_id"] for r in previous_decisions if r["product"] == "PAPERLESS_BANKING"],
                             "recommendation": next(r for r in decisions if r["product"] == "PAPERLESS_BANKING"),
                             "event_at": data["event_at"], "available_at": data["available_at"], "feature_cutoff": data["feature_cutoff"]})
                except Exception:
                    provider.restore_source_snapshot(source)
                    raise
                state.invalidate_summary()
                return event
        except ValidationError as error:
            raise HTTPException(422, str(error)) from error
        except ValueError as error:
            raise HTTPException(409, str(error)) from error

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

    @router.get("/customers/{customer_id}/promos/{product}")
    def promo(customer_id: str, product: Product,
              format: str = Query("one_liner", pattern="^(push|one_liner|short|medium)$"),
              channel: str = Query("app", pattern="^(app|email|phone|rm)$"), preview: bool = False):
        # Targeting stays with the communication rules; copy is only sendable for an engage action.
        # preview=true lets staff see copy for a supported decision that contact rules currently block.
        rec = row(customer_id, product)
        action, reason = communication(rec, service.store.history(customer_id), service.preferences(customer_id), channel)
        recommendation = Recommendation.model_validate(rec)
        promo = application.state.promo_service.generate(recommendation, action, reason, fmt=format,
                                                         channel=channel, preview=preview)
        return dump(promo)

    @router.get("/promos/metrics")
    def promo_metrics():
        return application.state.promo_service.metrics()

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

    @router.post("/customers/{customer_id}/counterfactual-search")
    def counterfactual_search(customer_id: str, request: CounterfactualRequest):
        customer(customer_id)
        try:
            return service.counterfactual_search(customer_id, request)
        except ValueError as error:
            raise HTTPException(409, str(error)) from error

    @router.get("/portfolio/opportunities")
    def opportunities(region: str | None = None, segment: str | None = None, product: Product | None = None,
                      status: str | None = None, min_propensity: float = Query(0, ge=0, le=1), min_trust: float = Query(0, ge=0, le=1),
                      min_confidence: float = Query(0, ge=0, le=1), min_impact: float = Query(0, ge=0), data_quality: str | None = None):
        # Zero defaults leave missing confidence/impact visible to shipped fixture consumers.
        kwargs = {"min_confidence": min_confidence if min_confidence > 0 else None,
                  "min_impact": min_impact if min_impact > 0 else None, "data_quality": data_quality}
        return {"opportunities": service.opportunities(region, segment, product, status, min_propensity, min_trust, **kwargs),
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

    @router.post("/campaigns/{campaign_id}/close")
    def close_campaign(campaign_id: str, x_demo_admin_token: str | None = Header(default=None)):
        token = os.environ.get("GREENPATH_DEMO_ADMIN_TOKEN")
        if not token or not x_demo_admin_token or not secrets.compare_digest(token, x_demo_admin_token):
            raise HTTPException(403, "Authorized local demo campaign closure required")
        with service.store.transaction():
            event = service.store.get_event(campaign_id)
            if event is None or event["kind"] != "campaign":
                raise HTTPException(404, "Campaign not found")
            for closure in service.store.history("PORTFOLIO"):
                if closure["kind"] == "campaign_closed" and closure.get("campaign_id") == campaign_id:
                    return closure
            return service.store.append("PORTFOLIO", event["product"], "campaign_closed", {},
                                        {"campaign_id": campaign_id,
                                         "limitation": "Releases simulated campaign capacity only; contact history and evidence remain unchanged."})

    @router.get("/audit/recommendations/{event_id}")
    def audit(event_id: str):
        event = service.store.get_recommendation(event_id) or service.store.get_event(event_id)
        if event is None:
            raise HTTPException(404, "Audit event not found")
        return event

    @router.get("/customers/{customer_id}/shap/{product}")
    def shap_audit(customer_id: str, product: Product):
        snap = customer(customer_id)
        runtime = getattr(service.repository, "runtime", None)
        provider = getattr(runtime, "propensity", None)
        audit = getattr(provider, "shap_audit", None)
        if snap.source_snapshot is None or runtime is None:
            return {"status": "NOT_AVAILABLE", "limitation": "No trained SHAP audit provider is available; reasons are not SHAP values."}
        if audit is not None:
            return audit(snap.source_snapshot, product)
        from greenpath.models.propensity.shap_audit import audit_shap
        import pandas as pd
        try:
            return audit_shap(runtime.bundles[product], pd.DataFrame(
                [snap.source_snapshot.features], index=[customer_id]))
        except (ValueError, AttributeError) as error:
            return {"status": "NOT_AVAILABLE", "limitation": str(error)}

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
