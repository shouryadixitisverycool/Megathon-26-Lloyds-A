"""Controlled reason-code catalogue and derivation (spec 18, version ``reasons_v1``).

Reason codes are deterministic functions of evidence fields; the LLM never invents reasons.
A code never fires on missing evidence. When per-feature contributions from the logistic model
(coefficient x standardised value) are supplied, codes are ordered by positive contribution and
codes whose driving feature contributes negatively are dropped.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

import pandas as pd

from greenpath.contracts import Product, ReasonCode, ReasonCodeDefinition

REASON_VERSION = "reasons_v1"
MAX_REASON_CODES = 4
EV, GH, SF, PB = (Product.EV_FINANCE, Product.GREEN_HOME, Product.SOLAR_FINANCE,
                  Product.PAPERLESS_BANKING)


@dataclass(frozen=True)
class _Spec:
    code: ReasonCode
    feature: str  # driving feature (also the key looked up in contributions)
    op: str  # ">=", ">", "==1", "==0"
    threshold_key: str | None  # key into the thresholds mapping
    default_threshold: float | None
    fit: tuple[float, bool] | None  # (quantile, positive_only) to derive threshold at fit, or None
    unit: str | None
    products: tuple[Product, ...]
    evidence: tuple[tuple[str, str], ...]  # (evidence key, source field)
    customer: str
    rm: str
    derivation: str


_SPECS: tuple[_Spec, ...] = (
    _Spec(ReasonCode.ICE_VEHICLE_OWNER, "is_ice", "==1", None, None, None, None, (EV,),
          (("vehicle_fuel_type", "fuel_type"),),
          "You drive a petrol or diesel car.",
          "Customer holds a petrol/diesel (ICE) vehicle record.",
          "is_ice == 1 (vehicle record at cutoff)"),
    _Spec(ReasonCode.HIGH_FUEL_SPEND, "fuel_spend_90d_avg", ">=", "fuel_spend_90d_avg", 120.0,
          (0.75, False), "GBP per month", (EV,), (("monthly_fuel_spend", "fuel_spend_90d_avg"),),
          "Your monthly fuel spend is higher than most customers'.",
          "Average monthly fuel spend over the last 90 days is in the top quartile of the training population.",
          "fuel_spend_90d_avg >= threshold (training 75th percentile)"),
    _Spec(ReasonCode.HIGH_ANNUAL_MILEAGE, "annual_mileage_km", ">=", "annual_mileage_km", 12000.0,
          (0.75, False), "km per year", (EV,), (("annual_mileage_km", "annual_mileage_km"),),
          "You drive more miles each year than most customers.",
          "Annual mileage is in the top quartile of the training population (may be estimated).",
          "annual_mileage_km >= threshold (training 75th percentile)"),
    _Spec(ReasonCode.OLDER_VEHICLE, "vehicle_age_years", ">=", "vehicle_age_years", 8.0,
          (0.75, False), "years", (EV,), (("vehicle_age_years", "vehicle_age_years"),),
          "Your car is older than most.",
          "Vehicle age is in the top quartile of the training population.",
          "vehicle_age_years >= threshold (training 75th percentile)"),
    _Spec(ReasonCode.EXISTING_VEHICLE_FINANCE, "has_vehicle_finance", "==1", None, None, None, None,
          (EV,), (("has_vehicle_finance", "has_vehicle_finance"),),
          "You already finance your car, so you are used to spreading the cost.",
          "Customer has existing vehicle finance on record.",
          "has_vehicle_finance == 1"),
    _Spec(ReasonCode.HOMEOWNER, "home_owner", "==1", None, None, None, None, (GH, SF),
          (("home_owner", "home_owner"),),
          "You own your home.",
          "Home ownership is recorded as owner.",
          "home_owner == 1"),
    _Spec(ReasonCode.MORTGAGE_CUSTOMER, "has_mortgage", "==1", None, None, None, None, (GH,),
          (("has_mortgage", "has_mortgage"),),
          "You have a mortgage with us.",
          "Customer holds an active mortgage.",
          "has_mortgage == 1"),
    _Spec(ReasonCode.NO_EXISTING_SOLAR, "has_existing_solar", "==0", None, None, None, None, (SF, GH),
          (("has_existing_solar", "has_existing_solar"),),
          "We have no record of solar panels at your home.",
          "No existing solar installation recorded (explicit negative, not missing).",
          "has_existing_solar == 0"),
    _Spec(ReasonCode.HIGH_ELECTRICITY_USE, "electricity_kwh_12m", ">=", "electricity_kwh_12m", 4000.0,
          (0.75, False), "kWh per year", (SF, GH), (("electricity_kwh_12m", "electricity_kwh_12m"),),
          "Your home uses more electricity than most.",
          "Metered electricity use over 12 months is in the top quartile of the training population.",
          "electricity_kwh_12m >= threshold (training 75th percentile)"),
    _Spec(ReasonCode.HIGH_GAS_USE, "gas_kwh_12m", ">=", "gas_kwh_12m", 12000.0,
          (0.75, False), "kWh per year", (GH,), (("gas_kwh_12m", "gas_kwh_12m"),),
          "Your home uses more gas than most.",
          "Metered gas use over 12 months is in the top quartile of the training population.",
          "gas_kwh_12m >= threshold (training 75th percentile)"),
    _Spec(ReasonCode.RECENT_HOME_IMPROVEMENT_SPEND, "home_improvement_spend_90d_avg", ">=",
          "home_improvement_spend_90d_avg", 50.0, (0.5, True), "GBP per month", (GH, SF),
          (("monthly_home_improvement_spend", "home_improvement_spend_90d_avg"),),
          "You have recently spent money on improving your home.",
          "Home-improvement spend over the last 90 days is above the training median of customers with such spend.",
          "home_improvement_spend_90d_avg >= threshold (training median of positive values)"),
    _Spec(ReasonCode.UTILITY_SPEND_RISING, "utilities_spend_trend", ">", "utilities_spend_trend", 0.10,
          None, "ratio vs 12-month average", (GH,), (("utilities_spend_trend", "utilities_spend_trend"),),
          "Your utility bills have been rising recently.",
          "90-day average utility spend is more than 10% above the 12-month average.",
          "utilities_spend_trend > threshold (fixed 0.10)"),
    _Spec(ReasonCode.PAPER_STATEMENTS_ACTIVE, "paper_statements_3m", ">=", "paper_statements_3m", 1.0,
          None, "statements in 3 months", (PB,), (("paper_statements_3m", "paper_statements_3m"),),
          "You are still receiving paper statements.",
          "At least one paper statement was issued in the last 3 months.",
          "paper_statements_3m >= threshold (fixed 1)"),
    _Spec(ReasonCode.HIGH_DIGITAL_ENGAGEMENT, "app_logins_3m_avg", ">=", "app_logins_3m_avg", 10.0,
          (0.75, False), "logins per month", (PB, EV), (("app_logins_3m_avg", "app_logins_3m_avg"),),
          "You use our app more often than most customers.",
          "Average monthly app logins over 3 months are in the top quartile of the training population.",
          "app_logins_3m_avg >= threshold (training 75th percentile)"),
    _Spec(ReasonCode.STATED_SUSTAINABILITY_PREFERENCE, "sustainability_preference", ">=",
          "sustainability_preference", 4.0, None, "score (1-5)", (EV, GH, SF, PB),
          (("sustainability_preference", "sustainability_preference"),),
          "You told us that sustainability matters to you.",
          "Customer-stated sustainability preference of 4 or 5 (self-reported).",
          "sustainability_preference >= threshold (fixed 4)"),
)
_SPEC_BY_CODE = {s.code: s for s in _SPECS}
_ORDER = {s.code: i for i, s in enumerate(_SPECS)}

REASON_CODE_CATALOGUE: dict[ReasonCode, ReasonCodeDefinition] = {
    s.code: ReasonCodeDefinition(
        code=s.code, customer_wording=s.customer, rm_wording=s.rm, derivation=s.derivation,
        threshold=s.default_threshold, threshold_unit=s.unit,
        evidence_fields=[k for k, _ in s.evidence], applicable_products=list(s.products),
        version=REASON_VERSION)
    for s in _SPECS
}

# Fields a caller must provide (besides the model features) to evaluate every code.
REASON_INPUT_FIELDS: list[str] = sorted({s.feature for s in _SPECS}
                                        | {src for s in _SPECS for _, src in s.evidence})
_BOOLEAN_EVIDENCE = {"has_vehicle_finance", "home_owner", "has_mortgage", "has_existing_solar"}


def _missing(v: object) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v)) or v is pd.NA


def _num(v: object) -> float | None:
    if _missing(v):
        return None
    try:
        f = float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def fit_reason_thresholds(train_frame: pd.DataFrame) -> dict[str, float]:
    """Spend/usage thresholds from TRAINING-population quantiles (defaults where unavailable)."""
    out: dict[str, float] = {}
    for s in _SPECS:
        if s.threshold_key is None:
            continue
        thr = float(s.default_threshold)  # type: ignore[arg-type]
        if s.fit is not None and s.feature in train_frame.columns:
            q, positive_only = s.fit
            vals = pd.to_numeric(train_frame[s.feature], errors="coerce").dropna()
            if positive_only:
                vals = vals[vals > 0]
            if len(vals) >= 20:
                thr = float(vals.quantile(q))
        out[s.threshold_key] = thr
    return out


def _holds(s: _Spec, value: float, thresholds: Mapping[str, float]) -> bool:
    if s.op == "==1":
        return value == 1.0
    if s.op == "==0":
        return value == 0.0
    thr = thresholds.get(s.threshold_key, s.default_threshold)  # type: ignore[arg-type]
    if thr is None or _missing(thr):
        return False
    return value >= thr if s.op == ">=" else value > thr


def derive_reason_codes(
    features: Mapping[str, object],
    product: Product,
    thresholds: Mapping[str, float] | None = None,
    contributions: Mapping[str, float] | None = None,
    max_codes: int = MAX_REASON_CODES,
) -> tuple[list[ReasonCode], dict[str, float | int | bool | str]]:
    """Fire the reason codes that hold for ``features`` and apply to ``product``.

    ``features`` may also hold ``fuel_type`` (used only as evidence). ``contributions`` maps a
    feature name to its logistic contribution; codes are ordered by it (descending), codes with a
    negative contribution are dropped and features without a contribution rank as neutral (0).
    Returns ``(codes, evidence)`` with evidence keyed by the catalogue ``evidence_fields``.
    """
    thresholds = thresholds or {}
    fired: list[tuple[float, int, _Spec]] = []
    for s in _SPECS:
        if product not in s.products:
            continue
        value = _num(features.get(s.feature))
        if value is None or not _holds(s, value, thresholds):
            continue
        contrib = 0.0
        if contributions is not None and (c := _num(contributions.get(s.feature))) is not None:
            if c < 0:
                continue
            contrib = c
        fired.append((-contrib, _ORDER[s.code], s))
    fired.sort(key=lambda t: (t[0], t[1]))
    fired = fired[:max_codes]

    codes: list[ReasonCode] = []
    evidence: dict[str, float | int | bool | str] = {}
    for _, _, s in fired:
        codes.append(s.code)
        for key, src in s.evidence:
            raw = features.get(src)
            if _missing(raw):
                continue
            if isinstance(raw, str):
                evidence[key] = raw
            elif hasattr(raw, "value") and isinstance(raw.value, str):  # enum members
                evidence[key] = raw.value
            elif (f := _num(raw)) is not None:
                evidence[key] = bool(f) if src in _BOOLEAN_EVIDENCE else f
    return codes, evidence
