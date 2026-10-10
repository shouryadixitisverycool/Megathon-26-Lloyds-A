"""Input-evidence quality per product: completeness, freshness and quality issues.

Trust measures how adequate the INPUT EVIDENCE is for a product decision, never model
confidence. Every function here reads one ``CustomerSnapshot``. Numeric and boolean
inputs come from ``snapshot.features`` (DESIGN.md names, None when missing); context
columns that are not features (fuel type, region, heating, property type) and evidence
counts come from the typed fact groups (``vehicle``, ``home``, ``data_quality``).

Presence rules, applied uniformly:

* a value is present when it is not None (False and 0 are present values);
* evidence month counts (energy, digital) are present when > 0;
* vehicle-only fields do not apply when ``vehicle.has_vehicle is False``: a customer
  with no car owes no fuel type or mileage, so those fields are excluded from both
  completeness and critical-field checks.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

from greenpath.contracts import (
    CustomerSnapshot,
    Product,
    Severity,
    TrustIssue,
    TrustIssueCategory,
    TrustIssueCode,
)

# ---------------------------------------------------------------------------
# Thresholds. Module constants so the orchestrator can tune them on validation.
# ---------------------------------------------------------------------------

#: Below this many transaction months the history is poor: SHORT_TRANSACTION_HISTORY, HIGH.
POOR_HISTORY_MONTHS: Final = 3
#: Below this many transaction months (and not poor) the history is short: MEDIUM.
SHORT_HISTORY_MONTHS: Final = 6
#: Transaction months at which the history component reaches 1.0 (spec: 12+ is good).
GOOD_HISTORY_MONTHS: Final = 12
#: A last transaction within this many days of the cutoff scores full recency.
FRESH_TXN_DAYS: Final = 30
#: A last transaction this many days (or more) before the cutoff scores zero recency.
STALE_TXN_DAYS: Final = 180
#: A vehicle record at most this many days old scores full freshness.
VEHICLE_FRESH_DAYS: Final = 365
#: A vehicle record older than this is stale (VEHICLE_RECORD_STALE) and scores zero.
VEHICLE_RECORD_STALE_DAYS: Final = 730
#: Months in a full observation year (energy and digital records).
FULL_YEAR_MONTHS: Final = 12
#: Freshness deducted when EV annual mileage is estimated rather than observed.
ESTIMATED_MILEAGE_PENALTY: Final = 0.15

Predicate = Callable[[CustomerSnapshot], bool]
Component = Callable[[CustomerSnapshot], float | None]


def _always(snapshot: CustomerSnapshot) -> bool:
    return True


def _has_vehicle_applies(snapshot: CustomerSnapshot) -> bool:
    """Vehicle-only fields are owed unless the customer is known to have no vehicle."""
    return snapshot.vehicle.has_vehicle is not False


def _feature_present(name: str) -> Predicate:
    return lambda snapshot: snapshot.features.get(name) is not None


@dataclass(frozen=True)
class FieldSpec:
    """One field a product uses. ``is_present`` and ``applies`` read the snapshot."""

    name: str
    critical: bool
    is_present: Predicate
    applies: Predicate = _always


# Field requirements per product (DESIGN.md feature names; context columns from typed facts).
PRODUCT_FIELDS: Final[dict[Product, tuple[FieldSpec, ...]]] = {
    Product.EV_FINANCE: (
        FieldSpec("has_vehicle", True, lambda s: s.vehicle.has_vehicle is not None),
        FieldSpec("fuel_type", True, lambda s: s.vehicle.fuel_type is not None, _has_vehicle_applies),
        FieldSpec("annual_mileage_km", False, _feature_present("annual_mileage_km"), _has_vehicle_applies),
        FieldSpec("fuel_spend_90d_avg", False, _feature_present("fuel_spend_90d_avg")),
        FieldSpec("vehicle_age_years", False, _feature_present("vehicle_age_years"), _has_vehicle_applies),
    ),
    Product.GREEN_HOME: (
        FieldSpec("home_owner", True, lambda s: s.home.home_owner is not None),
        FieldSpec("energy_months_present", True, lambda s: s.data_quality.energy_months_present > 0),
        FieldSpec("electricity_kwh_12m", False, _feature_present("electricity_kwh_12m")),
        FieldSpec("gas_kwh_12m", False, _feature_present("gas_kwh_12m")),
        FieldSpec("heating_type", False, lambda s: s.home.heating_type is not None),
        FieldSpec("has_mortgage", False, _feature_present("has_mortgage")),
    ),
    Product.SOLAR_FINANCE: (
        FieldSpec("home_owner", True, lambda s: s.home.home_owner is not None),
        FieldSpec("electricity_kwh_12m", True, _feature_present("electricity_kwh_12m")),
        FieldSpec("region", True, lambda s: s.home.region is not None),
        FieldSpec("has_existing_solar", False, _feature_present("has_existing_solar")),
        FieldSpec("property_type", False, lambda s: s.home.property_type is not None),
    ),
    Product.PAPERLESS_BANKING: (
        FieldSpec("digital_months_present", True, lambda s: s.data_quality.digital_months_present > 0),
        FieldSpec("paper_statements_3m", False, _feature_present("paper_statements_3m")),
        FieldSpec("digital_txn_3m_avg", False, _feature_present("digital_txn_3m_avg")),
    ),
}


# ---------------------------------------------------------------------------
# Completeness and critical-field presence
# ---------------------------------------------------------------------------


def completeness(snapshot: CustomerSnapshot, product: Product) -> float:
    """Fraction (0..1) of the product's applicable relevant + critical fields that are present."""
    applicable = [f for f in PRODUCT_FIELDS[product] if f.applies(snapshot)]
    if not applicable:
        return 1.0
    return sum(1 for f in applicable if f.is_present(snapshot)) / len(applicable)


def critical_fields_present(snapshot: CustomerSnapshot, product: Product) -> bool:
    """True when every applicable critical field for the product is present."""
    return all(
        f.is_present(snapshot)
        for f in PRODUCT_FIELDS[product]
        if f.critical and f.applies(snapshot)
    )


# ---------------------------------------------------------------------------
# Freshness
# ---------------------------------------------------------------------------


def _linear(value: float, full_at: float, zero_at: float) -> float:
    """1.0 up to ``full_at``, 0.0 from ``zero_at`` onwards, linear in between."""
    if value <= full_at:
        return 1.0
    if value >= zero_at:
        return 0.0
    return (zero_at - value) / (zero_at - full_at)


def _days_since_last_transaction(snapshot: CustomerSnapshot) -> int | None:
    last = snapshot.data_quality.last_transaction_date
    if last is None:
        return None
    return max((snapshot.feature_cutoff - last).days, 0)


def _vehicle_record_age_days(snapshot: CustomerSnapshot) -> int | None:
    recorded = snapshot.data_quality.vehicle_record_age_days
    if recorded is not None:
        return recorded
    if snapshot.vehicle.record_updated_at is not None:
        return max((snapshot.feature_cutoff - snapshot.vehicle.record_updated_at).days, 0)
    return None


def _mileage_estimated(snapshot: CustomerSnapshot) -> bool:
    return snapshot.vehicle.mileage_is_estimated or (
        "annual_mileage_km" in snapshot.data_quality.estimated_fields
    )


def _history_component(snapshot: CustomerSnapshot) -> float:
    months = snapshot.data_quality.transaction_months_observed
    return min(months, GOOD_HISTORY_MONTHS) / GOOD_HISTORY_MONTHS


def _recency_component(snapshot: CustomerSnapshot) -> float:
    days = _days_since_last_transaction(snapshot)
    return 0.0 if days is None else _linear(days, FRESH_TXN_DAYS, STALE_TXN_DAYS)


def _vehicle_component(snapshot: CustomerSnapshot) -> float | None:
    if not _has_vehicle_applies(snapshot):
        return None  # known no-vehicle customer: the record's age is not evidence we need
    age = _vehicle_record_age_days(snapshot)
    return 0.0 if age is None else _linear(age, VEHICLE_FRESH_DAYS, VEHICLE_RECORD_STALE_DAYS)


def _energy_component(snapshot: CustomerSnapshot) -> float:
    months = snapshot.data_quality.energy_months_present
    return min(months, FULL_YEAR_MONTHS) / FULL_YEAR_MONTHS


def _digital_component(snapshot: CustomerSnapshot) -> float:
    months = snapshot.data_quality.digital_months_present
    return min(months, FULL_YEAR_MONTHS) / FULL_YEAR_MONTHS


# Freshness components per product; the score is the mean of the non-None components.
FRESHNESS_COMPONENTS: Final[dict[Product, tuple[Component, ...]]] = {
    Product.EV_FINANCE: (_history_component, _recency_component, _vehicle_component),
    Product.GREEN_HOME: (_history_component, _recency_component, _energy_component),
    Product.SOLAR_FINANCE: (_energy_component,),
    Product.PAPERLESS_BANKING: (_digital_component,),
}


def freshness(snapshot: CustomerSnapshot, product: Product) -> float:
    """Recency and length of the evidence for the product, in 0..1.

    Mean of the product's applicable components (see ``FRESHNESS_COMPONENTS``), minus
    ``ESTIMATED_MILEAGE_PENALTY`` for EV when mileage is estimated rather than observed.
    """
    values: list[float] = []
    for component in FRESHNESS_COMPONENTS[product]:
        value = component(snapshot)
        if value is not None:
            values.append(value)
    score = sum(values) / len(values) if values else 0.0
    if product is Product.EV_FINANCE and _has_vehicle_applies(snapshot) and _mileage_estimated(snapshot):
        score -= ESTIMATED_MILEAGE_PENALTY
    return min(max(score, 0.0), 1.0)


# ---------------------------------------------------------------------------
# Quality issues
# ---------------------------------------------------------------------------


def _issue(
    code: TrustIssueCode,
    category: TrustIssueCategory,
    severity: Severity,
    message: str,
    fields: list[str],
) -> TrustIssue:
    return TrustIssue(code=code, category=category, severity=severity, message=message, fields=fields)


def _history_issues(snapshot: CustomerSnapshot) -> list[TrustIssue]:
    months = snapshot.data_quality.transaction_months_observed
    if months < POOR_HISTORY_MONTHS:
        return [_issue(
            TrustIssueCode.SHORT_TRANSACTION_HISTORY, TrustIssueCategory.FRESHNESS, Severity.HIGH,
            f"Only {months} month(s) of transaction history; under {POOR_HISTORY_MONTHS} months is poor evidence.",
            ["transaction_months_observed"],
        )]
    if months < SHORT_HISTORY_MONTHS:
        return [_issue(
            TrustIssueCode.SHORT_TRANSACTION_HISTORY, TrustIssueCategory.FRESHNESS, Severity.MEDIUM,
            f"Short transaction history: {months} months (under {SHORT_HISTORY_MONTHS}).",
            ["transaction_months_observed"],
        )]
    return []


def _ev_issues(snapshot: CustomerSnapshot) -> list[TrustIssue]:
    issues: list[TrustIssue] = []
    has_vehicle = snapshot.vehicle.has_vehicle
    if has_vehicle is None:
        issues.append(_issue(
            TrustIssueCode.VEHICLE_RECORD_MISSING, TrustIssueCategory.CRITICAL_FIELD, Severity.HIGH,
            "No vehicle record: vehicle ownership is unknown, so EV Finance cannot be assessed.",
            ["has_vehicle"],
        ))
    elif has_vehicle and snapshot.vehicle.fuel_type is None:
        issues.append(_issue(
            TrustIssueCode.VEHICLE_RECORD_MISSING, TrustIssueCategory.CRITICAL_FIELD, Severity.HIGH,
            "Vehicle record has no fuel type.",
            ["fuel_type"],
        ))
    if has_vehicle:
        if snapshot.features.get("annual_mileage_km") is None:
            issues.append(_issue(
                TrustIssueCode.MILEAGE_MISSING, TrustIssueCategory.COMPLETENESS, Severity.MEDIUM,
                "Annual mileage is missing; EV impact cannot be quantified from observed use.",
                ["annual_mileage_km"],
            ))
        elif _mileage_estimated(snapshot):
            issues.append(_issue(
                TrustIssueCode.MILEAGE_ESTIMATED, TrustIssueCategory.FRESHNESS, Severity.LOW,
                "Annual mileage is estimated, not observed; evidence is modestly downgraded.",
                ["annual_mileage_km"],
            ))
    age = _vehicle_record_age_days(snapshot)
    if _has_vehicle_applies(snapshot) and age is not None and age > VEHICLE_RECORD_STALE_DAYS:
        issues.append(_issue(
            TrustIssueCode.VEHICLE_RECORD_STALE, TrustIssueCategory.FRESHNESS, Severity.MEDIUM,
            f"Vehicle record is {age} days old (stale after {VEHICLE_RECORD_STALE_DAYS} days).",
            ["record_updated_at"],
        ))
    issues.extend(_history_issues(snapshot))
    return issues


def _green_home_issues(snapshot: CustomerSnapshot) -> list[TrustIssue]:
    issues: list[TrustIssue] = []
    if snapshot.home.home_owner is None:
        issues.append(_issue(
            TrustIssueCode.HOME_OWNERSHIP_UNKNOWN, TrustIssueCategory.CRITICAL_FIELD, Severity.HIGH,
            "Home ownership is unknown; Green Home cannot be assessed without it.",
            ["home_owner"],
        ))
    months = snapshot.data_quality.energy_months_present
    if months == 0:
        issues.append(_issue(
            TrustIssueCode.ENERGY_RECORDS_MISSING, TrustIssueCategory.CRITICAL_FIELD, Severity.HIGH,
            "No energy records in the 12 months before cutoff.",
            ["energy_months_present"],
        ))
    elif months < FULL_YEAR_MONTHS:
        issues.append(_issue(
            TrustIssueCode.ENERGY_RECORDS_INCOMPLETE, TrustIssueCategory.COMPLETENESS, Severity.MEDIUM,
            f"Energy records cover {months} of 12 months.",
            ["energy_months_present"],
        ))
    issues.extend(_history_issues(snapshot))
    return issues


def _solar_issues(snapshot: CustomerSnapshot) -> list[TrustIssue]:
    issues: list[TrustIssue] = []
    if snapshot.home.home_owner is None:
        issues.append(_issue(
            TrustIssueCode.HOME_OWNERSHIP_UNKNOWN, TrustIssueCategory.CRITICAL_FIELD, Severity.HIGH,
            "Home ownership is unknown; Solar Finance is withheld until it is evidenced.",
            ["home_owner"],
        ))
    if snapshot.features.get("electricity_kwh_12m") is None:
        issues.append(_issue(
            TrustIssueCode.ENERGY_RECORDS_MISSING, TrustIssueCategory.CRITICAL_FIELD, Severity.HIGH,
            "No electricity consumption record; Solar impact and eligibility signal are unavailable.",
            ["electricity_kwh_12m"],
        ))
    months = snapshot.data_quality.energy_months_present
    if 0 < months < FULL_YEAR_MONTHS:
        issues.append(_issue(
            TrustIssueCode.ENERGY_RECORDS_INCOMPLETE, TrustIssueCategory.COMPLETENESS, Severity.MEDIUM,
            f"Energy records cover {months} of 12 months.",
            ["energy_months_present"],
        ))
    if snapshot.home.region is None:
        issues.append(_issue(
            TrustIssueCode.REGION_MISSING, TrustIssueCategory.CRITICAL_FIELD, Severity.HIGH,
            "Region is missing; regional solar context cannot be applied.",
            ["region"],
        ))
    return issues


def _paperless_issues(snapshot: CustomerSnapshot) -> list[TrustIssue]:
    if snapshot.data_quality.digital_months_present == 0:
        return [_issue(
            TrustIssueCode.DIGITAL_RECORDS_MISSING, TrustIssueCategory.CRITICAL_FIELD, Severity.HIGH,
            "No digital banking records in the 12 months before cutoff.",
            ["digital_months_present"],
        )]
    return []


_ISSUE_RULES: Final[dict[Product, Callable[[CustomerSnapshot], list[TrustIssue]]]] = {
    Product.EV_FINANCE: _ev_issues,
    Product.GREEN_HOME: _green_home_issues,
    Product.SOLAR_FINANCE: _solar_issues,
    Product.PAPERLESS_BANKING: _paperless_issues,
}


def quality_issues(snapshot: CustomerSnapshot, product: Product) -> list[TrustIssue]:
    """Completeness, freshness and critical-field issues for one customer and product."""
    return _ISSUE_RULES[product](snapshot)


@dataclass(frozen=True)
class QualityReport:
    """Everything the trust provider needs from the evidence-quality checks."""

    completeness: float
    freshness: float
    critical_fields_present: bool
    issues: list[TrustIssue]


def assess_quality(snapshot: CustomerSnapshot, product: Product) -> QualityReport:
    """Run all evidence-quality checks for one customer and product."""
    return QualityReport(
        completeness=completeness(snapshot, product),
        freshness=freshness(snapshot, product),
        critical_fields_present=critical_fields_present(snapshot, product),
        issues=quality_issues(snapshot, product),
    )
