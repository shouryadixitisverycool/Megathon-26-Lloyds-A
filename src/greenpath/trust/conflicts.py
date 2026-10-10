"""Deterministic cross-source conflict detection (spec 17.3) and consistency scoring.

A conflict means two sources in the same snapshot disagree about the customer, so the
evidence for a product cannot be trusted until a human resolves it. Every rule is a
plain predicate over typed facts and named features; nothing here is learned.

Rules and scope:

* ``EV_RECORD_WITH_RECURRING_FUEL_SPEND`` (HIGH, EV_FINANCE only): vehicle record says EV
  while fuel is bought recurrently. Possible causes: second vehicle, stale record,
  merchant misclassification. Omitted for other products, since the vehicle record is
  evidence only for EV Finance.
* ``NON_OWNER_WITH_ACTIVE_MORTGAGE`` (HIGH, SOLAR_FINANCE and GREEN_HOME): home ownership
  recorded as no while a mortgage is active.
* ``PAPERLESS_FLAG_WITH_PAPER_STATEMENTS`` (HIGH, PAPERLESS_BANKING): flagged paperless
  but paper statements still issued in the last three months.
* ``INVALID_PRODUCT_RECORD`` (HIGH, every product): at least one product record is
  invalid, so product records conflict and need human review (spec 17.2, 57).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from greenpath.contracts import (
    CustomerSnapshot,
    FuelType,
    Product,
    Severity,
    TrustIssue,
    TrustIssueCategory,
    TrustIssueCode,
)

# ---------------------------------------------------------------------------
# Thresholds. Module constants so the orchestrator can tune them on validation.
# ---------------------------------------------------------------------------

#: Fuel transactions in the last 90 days at or above which fuel buying is "recurring".
RECURRING_FUEL_TXN_MIN: Final = 3
#: Average monthly fuel spend (GBP, 90-day window) above which fuel use is "high".
RECURRING_FUEL_MONTHLY_GBP: Final = 60.0

#: Consistency penalty per conflict, by severity. Consistency = 1 - min(1, sum of penalties).
SEVERITY_PENALTY: Final[dict[Severity, float]] = {
    Severity.HIGH: 0.5,
    Severity.MEDIUM: 0.25,
    Severity.LOW: 0.1,
}


def _conflict(
    code: TrustIssueCode,
    severity: Severity,
    message: str,
    fields: list[str],
) -> TrustIssue:
    return TrustIssue(
        code=code,
        category=TrustIssueCategory.CONFLICT,
        severity=severity,
        message=message,
        fields=fields,
    )


def _ev_recurring_fuel_conflict(snapshot: CustomerSnapshot) -> TrustIssue | None:
    if snapshot.vehicle.fuel_type is not FuelType.EV:
        return None
    txn_count = snapshot.features.get("fuel_txn_freq_90d")
    monthly_spend = snapshot.features.get("fuel_spend_90d_avg")
    if txn_count is None or monthly_spend is None:
        return None
    if txn_count < RECURRING_FUEL_TXN_MIN or monthly_spend <= RECURRING_FUEL_MONTHLY_GBP:
        return None
    return _conflict(
        TrustIssueCode.EV_RECORD_WITH_RECURRING_FUEL_SPEND,
        Severity.HIGH,
        f"Vehicle record is EV but fuel is bought recurrently ({int(txn_count)} fuel transactions "
        f"in 90 days, GBP {monthly_spend:.0f}/month). Possible second vehicle, stale record or "
        "merchant misclassification: review before recommending EV Finance.",
        ["fuel_type", "fuel_txn_freq_90d", "fuel_spend_90d_avg"],
    )


def _non_owner_mortgage_conflict(snapshot: CustomerSnapshot) -> TrustIssue | None:
    if snapshot.home.home_owner is not False or snapshot.home.has_mortgage is not True:
        return None
    return _conflict(
        TrustIssueCode.NON_OWNER_WITH_ACTIVE_MORTGAGE,
        Severity.HIGH,
        "Home ownership is recorded as no, but an active mortgage is held. Source conflict: "
        "do not recommend home-based products until it is resolved.",
        ["home_owner", "has_mortgage"],
    )


def _paperless_conflict(snapshot: CustomerSnapshot) -> TrustIssue | None:
    digital = snapshot.digital
    if digital.is_paperless is not True or not digital.paper_statements_3m:
        return None
    return _conflict(
        TrustIssueCode.PAPERLESS_FLAG_WITH_PAPER_STATEMENTS,
        Severity.HIGH,
        f"Flagged paperless but {digital.paper_statements_3m} paper statement(s) were issued in the "
        "last three months. Paperless status needs confirming.",
        ["is_paperless", "paper_statements_3m"],
    )


def _invalid_product_conflict(snapshot: CustomerSnapshot) -> TrustIssue | None:
    count = snapshot.data_quality.invalid_product_records
    if count <= 0:
        return None
    return _conflict(
        TrustIssueCode.INVALID_PRODUCT_RECORD,
        Severity.HIGH,
        f"{count} product record(s) are invalid or inconsistent. Human review is required before "
        "any recommendation.",
        ["invalid_product_records"],
    )


def detect_conflicts(snapshot: CustomerSnapshot, product: Product) -> list[TrustIssue]:
    """All cross-source conflicts that apply to ``product`` for this snapshot."""
    candidates: list[TrustIssue | None] = [_invalid_product_conflict(snapshot)]
    if product is Product.EV_FINANCE:
        candidates.append(_ev_recurring_fuel_conflict(snapshot))
    elif product in (Product.SOLAR_FINANCE, Product.GREEN_HOME):
        candidates.append(_non_owner_mortgage_conflict(snapshot))
    elif product is Product.PAPERLESS_BANKING:
        candidates.append(_paperless_conflict(snapshot))
    return [issue for issue in candidates if issue is not None]


def cross_source_consistency(conflicts: Sequence[TrustIssue]) -> float:
    """1 minus the severity-weighted conflict penalty, clipped to 0..1."""
    penalty = sum(SEVERITY_PENALTY[issue.severity] for issue in conflicts)
    return min(max(1.0 - penalty, 0.0), 1.0)


def has_high_conflict(conflicts: Sequence[TrustIssue]) -> bool:
    """True when any conflict is HIGH severity (fail-closed CONFLICT_REQUIRES_REVIEW)."""
    return any(issue.severity is Severity.HIGH for issue in conflicts)
