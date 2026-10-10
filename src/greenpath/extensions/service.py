"""Rules for communication and planning; never modify propensity or eligibility."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from itertools import islice, product as combinations
import math

PLANNING_DISCLAIMER = "Synthetic portfolio planning scenario, not an observed outcome or guaranteed reduction. Relevance does not establish eligibility."
PRIORITY_VERSION = "priority-v1-p40-c25-i20-t15"
FEEDBACK_STATES = {
    "SHOWN": "SHOWN", "INTERESTED": "ENGAGED", "NOT_INTERESTED": "DECLINED",
    "LATER": "WITHHELD", "ALREADY_COMPLETED": "COMPLETED",
    "DO_NOT_SHOW_AGAIN": "SUPPRESSED", "ACCEPTED": "ACCEPTED", "CLOSED": "CLOSED",
}

SEARCH_FIELDS = {
    "annual_mileage_km": (0, 200000, "contextual"),
    "fuel_spend_90d_avg": (0, 10000, "contextual"),
    "electricity_kwh_12m": (0, 200000, "contextual"),
    "gas_kwh_12m": (0, 500000, "contextual"),
    "paper_statements_12m": (0, 1000, "actionable"),
    "app_logins_3m_avg": (0, 10000, "contextual"),
}


def dump(value):
    return value.model_dump(mode="json")


def communication(row, history, preferences, channel="app", now=None):
    now = now or datetime.now(timezone.utc)
    if preferences.get("do_not_contact"):
        return "SUPPRESS", "Do not contact preference"
    events = [event for event in history if event.get("product") == row["product"]]
    for event in reversed(events):
        if event.get("product") != row["product"]:
            continue
        if event["kind"] == "review" and event.get("action") == "SUPPRESS":
            return "SUPPRESS", "Human reviewer suppression"
        if event["kind"] == "feedback":
            response = event.get("response")
            elapsed = now - datetime.fromisoformat(event["timestamp"])
            if response in {"DO_NOT_SHOW_AGAIN", "ALREADY_COMPLETED", "CLOSED"}:
                return "SUPPRESS", "Customer recorded suppression or completion"
            if response == "NOT_INTERESTED" and elapsed < timedelta(days=60):
                return "DEFER", "60-day cooling-off after decline"
            if response == "LATER" and elapsed < timedelta(days=30):
                return "DEFER", "30-day pause requested by customer"
    reviews = [event for event in events if event["kind"] == "review"]
    if reviews and reviews[-1].get("action") in {"FLAG_DATA_ISSUE", "REQUEST_REVIEW"}:
        return "REQUEST_REVIEW", "Unresolved human review request"
    if row["state"] == "CONFLICT_REQUIRES_REVIEW":
        return "REQUEST_REVIEW", "Unresolved evidence conflict"
    if row["state"] == "INSUFFICIENT_INFORMATION":
        return "REQUEST_INFORMATION", "Critical evidence is missing"
    if row["state"] != "RECOMMEND":
        return "SUPPRESS", "Decision does not support engagement"
    if preferences.get("channel_consent", {}).get(channel) is not True:
        return "REQUEST_CONSENT", "No recorded consent for the selected channel"
    contacts = [event for event in history if event["kind"] == "contact"]
    recent = [event for event in contacts if now - datetime.fromisoformat(event["timestamp"]) < timedelta(days=30)]
    if len(recent) >= 2:
        return "DEFER", "Two contacts in the last 30 days"
    if any(now - datetime.fromisoformat(event["timestamp"]) < timedelta(days=7) for event in contacts):
        return "DEFER", "Seven-day contact fatigue window"
    return ("SHOW_EDUCATION" if channel == "app" else "RM_DISCUSSION"), "Supported relevance and recorded channel consent"


def impact_group(row):
    impact = row["impact"]
    if impact["status"] != "AVAILABLE" or impact.get("value") is None:
        return None
    # Sum only identical product, units, time horizon, boundaries and factor vintage.
    return (
        row["product"], impact["units"], impact["boundary"],
        str(impact.get("period")), impact["method_version"], impact["factor_catalogue_version"],
    )


def expected_impact(row):
    key = impact_group(row)
    probability = (row.get("propensity") or {}).get("probability")
    return {
        "status": "AVAILABLE" if key and probability is not None else "UNAVAILABLE",
        "value": str(Decimal(str(probability)) * Decimal(str(row["impact"]["value"]))) if key and probability is not None else None,
        "units": row["impact"].get("units"),
        "compatibility_group": list(key) if key else None,
        "limitation": "Calibrated propensity times modelled physical impact; not an observed reduction or a causal estimate.",
    }


def prioritise(rows):
    maxima = {}
    for row in rows:
        key = impact_group(row)
        if key:
            maxima[key] = max(maxima.get(key, Decimal(0)), max(Decimal(0), Decimal(row["impact"]["value"])))
    result = []
    for row in rows:
        propensity = row.get("propensity") or {}
        probability = propensity.get("probability")
        confidence = propensity.get("confidence") if propensity.get("confidence_validated") else None
        key = impact_group(row)
        impact = float(max(Decimal(0), Decimal(row["impact"]["value"])) / maxima[key]) if key and maxima[key] > 0 else None
        components = {
            "calibrated_propensity": float(probability) if probability is not None else None,
            "validated_confidence": float(confidence) if confidence is not None else None,
            "normalised_impact": impact, "trust": float(row["trust"]["score"]),
        }
        weights = dict(zip(components, (0.40, 0.25, 0.20, 0.15)))
        score = sum(components[k] * weights[k] for k in components) if all(v is not None for v in components.values()) else None
        result.append({**row, "priority": {
            "score": score, "components": components, "weights": weights, "version": PRIORITY_VERSION,
            "normalisation": "Nonnegative impact divided by maximum in the same product/method/boundary/period/factor group",
            "limitation": None if score is not None else "Priority unavailable because validated confidence or comparable impact is missing. Ranked by calibrated propensity instead.",
        }})
        result[-1]["expected_sustainability_impact"] = expected_impact(row)
    result.sort(key=lambda r: (r["priority"]["score"] is not None, r["priority"]["score"] or 0,
                               float((r.get("propensity") or {}).get("probability") or 0), r["customer_id"]), reverse=True)
    for rank, row in enumerate(result, 1):
        row["priority"]["rank"] = rank
    return result


class ExtensionService:
    def __init__(self, snapshots, recommendations, explanations, repository, store):
        self.snapshots = snapshots
        self.recommendations = recommendations
        self.explanations = explanations
        self.repository = repository
        self.store = store

    def snapshot(self, customer_id):
        result = self.snapshots.get_snapshot(customer_id)
        if result is None:
            raise KeyError(customer_id)
        return result

    def rows(self, customer_id):
        self.snapshot(customer_id)
        return [dump(row) for row in self.recommendations.recommendations(customer_id)]

    def row(self, customer_id, product):
        return next(row for row in self.rows(customer_id) if row["product"] == str(product))

    def preferences(self, customer_id):
        events = [e for e in self.store.history(customer_id) if e["kind"] == "preferences"]
        return events[-1]["preferences"] if events else {"do_not_contact": False, "channel_consent": {}}

    def opportunities(self, region=None, segment=None, product=None, state=None, min_propensity=0, min_trust=0,
                      *, min_confidence=None, min_impact=None, data_quality=None):
        rows = []
        for snap in self.snapshots.list_snapshots():
            if (region and snap.region != region) or (segment and snap.segment != segment):
                continue
            for row in self.rows(snap.customer_id):
                probability = (row.get("propensity") or {}).get("probability")
                if product and row["product"] != str(product) or state and row["state"] != state:
                    continue
                if float(probability or 0) < min_propensity or float(row["trust"]["score"]) < min_trust:
                    continue
                propensity = row.get("propensity") or {}
                if min_confidence is not None and (not propensity.get("confidence_validated")
                        or propensity.get("confidence") is None or float(propensity["confidence"]) < min_confidence):
                    continue
                if min_impact is not None and (impact_group(row) is None or Decimal(str(row["impact"]["value"])) < Decimal(str(min_impact))):
                    continue
                if data_quality is not None and row["trust"]["status"] != data_quality:
                    continue
                row.update(region=snap.region, segment=snap.segment)
                rows.append(row)
        return prioritise(rows)

    def counterfactual_search(self, customer_id, request):
        snapshot = self.snapshot(customer_id)
        runtime = getattr(self.repository, "runtime", None)
        if runtime is None or snapshot.source_snapshot is None:
            raise ValueError("Counterfactual search requires trained inference, not fixture probabilities")
        bundle = runtime.bundles[request.product]
        candidates = request.candidates
        for field, values in candidates.items():
            if field not in SEARCH_FIELDS or field not in bundle.features:
                raise ValueError(f"{field} is not an approved search feature")
            lo, hi, _ = SEARCH_FIELDS[field]
            if not values or len(values) > 16 or any(not math.isfinite(v) or not lo <= v <= hi for v in values):
                raise ValueError(f"{field} requires 1 to 16 finite values between {lo} and {hi}")
        source = snapshot.source_snapshot
        baseline = runtime.propensity.score(source, request.product)
        fields = list(candidates)
        evaluated = []
        total = math.prod(len(values) for values in candidates.values())
        for values in islice(combinations(*(candidates[field] for field in fields)), request.max_evaluations):
            changes = dict(zip(fields, values))
            changed = source.model_copy(update={"features": {**source.features, **changes}})
            score = runtime.propensity.score(changed, request.product)
            probability = score.propensity if score.in_model_population else None
            distance = sum(abs(value - source.features[field]) / (SEARCH_FIELDS[field][1] - SEARCH_FIELDS[field][0])
                           for field, value in changes.items() if source.features.get(field) is not None)
            evaluated.append({"changes": changes, "probability": probability, "normalised_distance": distance,
                              "target_met": probability is not None and probability >= request.target_probability})
        evaluated.sort(key=lambda row: (not row["target_met"], row["normalised_distance"], -(row["probability"] or 0)))
        return {"baseline_probability": baseline.propensity if baseline.in_model_population else None,
                "model_version": baseline.model_version, "calibration_version": baseline.calibration_version,
                "feature_classes": {field: SEARCH_FIELDS[field][2] for field in fields},
                "evaluated_count": len(evaluated), "candidate_count": total, "truncated": total > len(evaluated),
                "results": evaluated, "best": next((row for row in evaluated if row["target_met"]), None),
                "limitation": "Bounded model sensitivity search, not causal advice or eligibility. Contextual changes are not recommended actions; distance excludes unknown baselines."}

    def feedback(self, request):
        with self.store.transaction():
            replay = self.store.replay(request.customer_id, str(request.product), "feedback", request.model_dump(mode="json"))
            if replay:
                return replay
            return self._feedback(request)

    def _feedback(self, request):
        row = self.row(request.customer_id, request.product)
        history = self.store.history(request.customer_id, str(request.product))
        statuses = [e.get("lifecycle_state") for e in history if e["kind"] == "feedback"]
        previous = statuses[-1] if statuses else "RECOMMENDED" if row["state"] == "RECOMMEND" else row["state"]
        desired = FEEDBACK_STATES[request.response]
        if previous in {"COMPLETED", "CLOSED", "SUPPRESSED"} and desired != "CLOSED" and desired != previous:
            raise ValueError("Completed, closed or suppressed journeys cannot be reopened by feedback")
        if desired == "CLOSED" and previous not in {"COMPLETED", "CLOSED"}:
            raise ValueError("Only a completed journey can be closed")
        return self.store.append(request.customer_id, str(request.product), "feedback", request.model_dump(mode="json"), {
            "response": request.response, "channel": request.channel, "note": request.note,
            "previous_state": previous, "lifecycle_state": desired, "recommendation": row,
            "limitation": "Feedback changes communication and lifecycle only. Completion must enter source data before model scores change.",
        })

    def plan(self, request, campaign=False):
        if campaign and request.execute:
            with self.store.transaction():
                replay = self.store.replay("PORTFOLIO", str(request.product), "campaign", request.model_dump(mode="json"))
                if replay:
                    return {**replay["result"], "campaign_event_id": replay["id"]}
                result = self._plan(request, campaign)
                event = self.store.append("PORTFOLIO", str(request.product), "campaign", request.model_dump(mode="json"), {"result": result})
                return {**result, "campaign_event_id": event["id"]}
        return self._plan(request, campaign)

    def _plan(self, request, campaign=False):
        rows = self.opportunities(request.region, request.segment, request.product, "RECOMMEND")
        channel = request.channel
        active_campaigns = self.store.active_campaigns() if campaign else []
        remaining_capacity = self.store.remaining_campaign_capacity(channel, request.channel_capacity,
                                                                    request.max_active_campaigns) if campaign else None
        used_capacity = request.channel_capacity - self.store.remaining_campaign_capacity(channel, request.channel_capacity) if campaign else 0
        active_customers = {selection["customer_id"] for event in active_campaigns
                            for selection in event.get("result", {}).get("selected", [])}
        selected, excluded = [], {}
        for row in rows:
            history = self.store.history(row["customer_id"])
            action, reason = communication(row, history, self.preferences(row["customer_id"]), channel)
            if campaign and row["customer_id"] in active_customers:
                action, reason = "DEFER", "Customer already selected in an active campaign"
            if action not in {"SHOW_EDUCATION", "RM_DISCUSSION"}:
                excluded[reason] = excluded.get(reason, 0) + 1
            else:
                selected.append(row)
        if campaign:
            if request.objective in {"impact", "balanced"}:
                eligible = []
                for row in selected:
                    if impact_group(row) is None or (request.objective == "balanced" and row["priority"]["score"] is None):
                        reason = "Comparable impact or validated priority unavailable"
                        excluded[reason] = excluded.get(reason, 0) + 1
                    else:
                        eligible.append(row)
                selected = eligible
                selected.sort(key=lambda row: row["priority"]["score"] if request.objective == "balanced" else row["priority"]["components"]["normalised_impact"], reverse=True)
            else:
                selected.sort(key=lambda row: Decimal(row["propensity"]["probability"]), reverse=True)
        limit = min(request.target_count, remaining_capacity) if campaign else request.target_count
        if len(selected) > limit:
            excluded["Target or remaining channel capacity limit"] = len(selected) - limit
        selected = selected[:limit]
        groups = {}
        for row in selected:
            key = impact_group(row)
            if key:
                groups.setdefault(key, Decimal(0))
                groups[key] += Decimal(row["impact"]["value"]) * Decimal(str(request.conversion_rate))
        result = {
            "selected_count": len(selected), "scenario_adopters": len(selected) * request.conversion_rate,
            "conversion_rate_assumption": request.conversion_rate,
            "average_propensity": sum(float(r["propensity"]["probability"]) for r in selected) / len(selected) if selected else None,
            "high_confidence_share": sum((r["propensity"].get("source_result") or {}).get("confidence", {}).get("bucket") == "HIGH" and r["propensity"].get("confidence_validated") is True for r in selected) / len(selected) if selected else None,
            "validated_confidence_share": sum(r["propensity"].get("confidence_validated") is True for r in selected) / len(selected) if selected else None,
            "impact_groups": [{"product": key[0], "units": key[1], "boundary": key[2], "period": key[3], "method_version": key[4], "factor_version": key[5], "scenario_impact": str(value)} for key, value in groups.items()],
            "impact_status": "AVAILABLE" if groups else "UNAVAILABLE",
            "impact_unavailable_count": sum(impact_group(row) is None for row in selected),
            "selected": [{"customer_id": r["customer_id"], "product": r["product"], "priority": r["priority"]} for r in selected],
            "excluded": excluded, "disclaimer": PLANNING_DISCLAIMER,
            "constraint_version": "campaign-v2-channel-consent-active-budget-single-offer",
            "executed": False,
            "channel": channel,
            "capacity_budget": {"boundary": "Active campaigns until explicitly closed", "limit": request.channel_capacity,
                                "used": used_capacity, "remaining_before": remaining_capacity,
                                "active_campaign_count": len(active_campaigns), "max_active_campaigns": request.max_active_campaigns} if campaign else None,
            "impact_ranking_limitation": "Impact ranking uses within-compatible-group normalisation, never compares raw incompatible units.",
        }
        if campaign and request.execute:
            # Local demo contact records only; this service never sends messages.
            for row in selected:
                event_request = {**request.model_dump(mode="json"), "request_id": f"{request.request_id}:{row['customer_id']}" if request.request_id else None}
                self.store.append(row["customer_id"], row["product"], "contact", event_request,
                                  {"channel": channel, "recommendation": row, "action": "SIMULATED_CONTACT", "sent": False})
            result["executed"] = bool(selected)
            result["execution_note"] = "Simulated contact audit records only; no messages sent."
        return result
