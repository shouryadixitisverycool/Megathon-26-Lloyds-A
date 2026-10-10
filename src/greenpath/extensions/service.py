"""Rules for communication and planning; never modify propensity or eligibility."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from greenpath.contracts.enums import Product

PLANNING_DISCLAIMER = "Synthetic portfolio planning scenario, not an observed outcome or guaranteed reduction. Relevance does not establish eligibility."
PRIORITY_VERSION = "priority-v1-p40-c25-i20-t15"
FEEDBACK_STATES = {
    "SHOWN": "SHOWN", "INTERESTED": "ENGAGED", "NOT_INTERESTED": "DECLINED",
    "LATER": "WITHHELD", "ALREADY_COMPLETED": "COMPLETED",
    "DO_NOT_SHOW_AGAIN": "SUPPRESSED", "ACCEPTED": "ACCEPTED", "CLOSED": "CLOSED",
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

    def opportunities(self, region=None, segment=None, product=None, state=None, min_propensity=0, min_trust=0):
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
                row.update(region=snap.region, segment=snap.segment)
                rows.append(row)
        return prioritise(rows)

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
                    return replay["result"]
                result = self._plan(request, campaign)
                self.store.append("PORTFOLIO", str(request.product), "campaign", request.model_dump(mode="json"), {"result": result})
                return result
        return self._plan(request, campaign)

    def _plan(self, request, campaign=False):
        rows = self.opportunities(request.region, request.segment, request.product, "RECOMMEND")
        channel = request.channel if campaign else "app"
        selected, excluded = [], {}
        for row in rows:
            action, reason = communication(row, self.store.history(row["customer_id"]), self.preferences(row["customer_id"]), channel)
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
                selected.sort(key=lambda row: row["priority"]["score"] if request.objective == "balanced" else Decimal(row["impact"]["value"]), reverse=True)
            else:
                selected.sort(key=lambda row: Decimal(row["propensity"]["probability"]), reverse=True)
        selected = selected[:min(request.target_count, request.channel_capacity) if campaign else request.target_count]
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
            "selected": [{"customer_id": r["customer_id"], "product": r["product"], "priority": r["priority"]} for r in selected],
            "excluded": excluded, "disclaimer": PLANNING_DISCLAIMER,
            "constraint_version": "campaign-v1-consent-cap2-30d-fatigue7d-decline60d-single-offer",
            "executed": False,
        }
        if campaign and request.execute:
            # Local demo contact records only; this service never sends messages.
            for row in selected:
                event_request = {**request.model_dump(mode="json"), "request_id": f"{request.request_id}:{row['customer_id']}" if request.request_id else None}
                self.store.append(row["customer_id"], row["product"], "contact", event_request,
                                  {"channel": channel, "recommendation": row, "action": "SIMULATED_CONTACT", "sent": False})
            result["executed"] = True
            result["execution_note"] = "Simulated contact audit records only; no messages sent."
        return result
