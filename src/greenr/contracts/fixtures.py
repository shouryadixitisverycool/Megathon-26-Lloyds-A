"""Frozen example payloads for the Agent A -> Agent B handoff (see CONTRACTS.md).

``build_fixtures()`` is the generator. Each file under ``fixtures/`` is the
``model_dump_json`` of one object built here, so the committed JSON always validates
against the current contract classes. Regenerate with::

    uv run --frozen python -m greenr.contracts.fixtures

Content follows spec section 5 (headline recommendation), section 58 (demo personas) and
config.py (cutoff 2026-06-30, outcome window end 2026-09-28, prediction timestamp
2026-10-10 09:00). Money is GBP, distances km, energy kWh, emissions kg CO2e.

Caveats for consumers:

- Carbon factors in the EV impact fixture are placeholders back-solved from the spec's
  headline numbers (2850 / 15200 km; 1180 kg). They are not a sourced factor set; the pinned
  values belong in CARBON_METHODS.md.
- Trend points use the config's trend cutoffs (month-ends Jan-Jun 2026). Jul-Oct month-ends
  would fall after the 2026-06-30 cutoff and, for October, after the 2026-10-10 prediction
  timestamp, and their 90-day outcome windows would not be observed by 2026-09-28.
- Version strings (model, calibration, confidence, carbon) are placeholders to be replaced by
  the versions the pipelines actually emit.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from datetime import date
from pathlib import Path
from typing import Any, TypeVar

from greenr.config import (
    FEATURE_CUTOFF,
    FEATURE_VERSION,
    OUTCOME_WINDOW_END,
    PREDICTION_TIMESTAMP,
    TREND_CUTOFFS,
)
from greenr.contracts.base import Contract
from greenr.contracts.customer import (
    CustomerSnapshot,
    DataQualityEvidence,
    DigitalFacts,
    EnergyFacts,
    HomeFacts,
    SpendFacts,
    VehicleFacts,
)
from greenr.contracts.enums import (
    PRODUCT_IDS,
    ConfidenceBucket,
    ConfidenceStatus,
    ExplanationSource,
    FuelType,
    GroundingResult,
    HeatingType,
    ImpactStatus,
    ModelType,
    PopulationExclusion,
    Product,
    ReasonCode,
    RecommendationState,
    Severity,
    TrustIssueCategory,
    TrustIssueCode,
    TrustStatus,
)
from greenr.contracts.impact import ImpactAssumption, ImpactMetric, ImpactResult
from greenr.contracts.propensity import ConfidenceResult, PropensityResult
from greenr.contracts.recommendation import (
    ELIGIBILITY_MESSAGE,
    Explanation,
    PortfolioSummary,
    PortfolioTrends,
    Priority,
    PriorityComponents,
    ProductSummary,
    Recommendation,
    TrendPoint,
)
from greenr.contracts.trust import TrustAssessment, TrustIssue
from greenr.ports import (
    CustomerSnapshotProvider,
    PropensityProvider,
    TrustProvider,
)

__all__ = [
    "APPROVED_FEATURES",
    "FIXTURE_DIR",
    "FixturePropensityProvider",
    "FixtureSnapshotProvider",
    "FixtureTrustProvider",
    "build_fixtures",
    "load_fixture",
    "load_model",
    "write_fixtures",
]

FIXTURE_DIR: Path = Path(__file__).resolve().parent / "fixtures"

CUTOFF: date = FEATURE_CUTOFF
WINDOW_END: date = OUTCOME_WINDOW_END
PREDICTED_AT = PREDICTION_TIMESTAMP

CONFIDENCE_METHOD_VERSION = "conf_meta_v2"
TRUST_METHOD_VERSION = "trust_v1"
CARBON_ENGINE_VERSION = "carbon_v2"
EMISSION_FACTOR_VERSION = "PINNED_AT_BUILD"
LLM_MODEL_VERSION = "PINNED_AT_BUILD"
PROMPT_VERSION = "prompt_v4"
TEMPLATE_PROMPT_VERSION = "template_v1"
RECOMMENDATION_RULE_VERSION = "rules_v1"
PRIORITY_VERSION = "priority_v2"
EV_METHOD_ID = "EV_OPERATIONAL_WTW_V1"
EV_METHOD_VERSION = "ev_impact_v1"
SOLAR_METHOD_ID = "SOLAR_PV_GENERATION_V1"
SOLAR_METHOD_VERSION = "solar_impact_v1"
PAPERLESS_METHOD_VERSION = "paperless_impact_v1"

# Spec section 31: Priority = 40% propensity + 25% confidence + 20% normalised impact + 15% Trust.
PRIORITY_WEIGHTS: dict[str, float] = {
    "propensity": 0.40,
    "confidence": 0.25,
    "normalised_impact": 0.20,
    "trust": 0.15,
}

MODEL_VERSIONS: dict[Product, str] = {
    Product.EV_FINANCE: "ev_propensity_v3.1",
    Product.GREEN_HOME: "green_home_propensity_v1",
    Product.SOLAR_FINANCE: "solar_propensity_v1",
    Product.PAPERLESS_BANKING: "paperless_propensity_v1",
}
CALIBRATION_VERSIONS: dict[Product, str] = {
    Product.EV_FINANCE: "ev_iso_v1",
    Product.GREEN_HOME: "green_home_platt_v1",
    Product.SOLAR_FINANCE: "solar_platt_v1",
    Product.PAPERLESS_BANKING: "paperless_iso_v1",
}

PRODUCT_ORDER: tuple[Product, ...] = (
    Product.EV_FINANCE,
    Product.GREEN_HOME,
    Product.SOLAR_FINANCE,
    Product.PAPERLESS_BANKING,
)

# ---------------------------------------------------------------------------
# Approved propensity feature view (DESIGN.md, "Approved propensity feature columns")
# ---------------------------------------------------------------------------

TXN_CATEGORIES: tuple[str, ...] = (
    "fuel",
    "electricity",
    "gas",
    "public_transport",
    "home_improvement",
    "automotive",
    "utilities",
)
TXN_SUFFIXES: tuple[str, ...] = (
    "spend_30d",
    "spend_90d_avg",
    "spend_12m_avg",
    "spend_trend",
    "txn_freq_90d",
    "spend_share_12m",
    "days_since_last",
)
_OTHER_FEATURES: tuple[str, ...] = (
    "txn_months_observed",
    "txn_count_12m",
    "total_spend_12m_avg",
    "tenure_months",
    "has_vehicle",
    "is_ice",
    "is_ev",
    "is_hybrid",
    "vehicle_age_years",
    "annual_mileage_km",
    "mileage_is_estimated",
    "vehicle_record_age_days",
    "has_vehicle_finance",
    "home_owner",
    "has_mortgage",
    "mortgage_tenure_months",
    "has_existing_solar",
    "has_investments",
    "heating_is_gas",
    "heating_is_electric",
    "property_is_house",
    "electricity_kwh_12m",
    "gas_kwh_12m",
    "electricity_trend",
    "energy_months_present",
    "is_paperless",
    "paper_statements_3m",
    "paper_statements_12m",
    "digital_statement_ratio",
    "digital_txn_3m_avg",
    "app_logins_3m_avg",
    "app_logins_trend",
    "branch_visits_3m",
    "digital_months_present",
    "sustainability_preference",
    "holds_ev_finance",
    "holds_green_home_loan",
    "holds_solar_finance",
)
APPROVED_FEATURES: tuple[str, ...] = (
    tuple(f"{cat}_{suffix}" for cat in TXN_CATEGORIES for suffix in TXN_SUFFIXES) + _OTHER_FEATURES
)


def _num(value: float | int | bool | None) -> float | None:
    return None if value is None else float(value)


def _round(value: float) -> float:
    return round(value, 4)


def _feature_vector(values: Mapping[str, float | int | bool | None]) -> dict[str, float | None]:
    """Typed, ordered feature view. Booleans become 0.0/1.0; unknown values stay None."""
    unknown = sorted(set(values) - set(APPROVED_FEATURES))
    missing = [name for name in APPROVED_FEATURES if name not in values]
    if unknown or missing:
        raise ValueError(f"feature vector mismatch: unknown={unknown} missing={missing}")
    return {name: _num(values[name]) for name in APPROVED_FEATURES}


def _txn_features(
    block: Mapping[str, Mapping[str, float | None]],
    total_12m: float | None,
) -> dict[str, float | None]:
    """Spend features per category, with the derived trend and share computed here."""
    out: dict[str, float | None] = {}
    for cat in TXN_CATEGORIES:
        row = block[cat]
        spend_90d = row["spend_90d_avg"]
        spend_12m = row["spend_12m_avg"]
        out[f"{cat}_spend_30d"] = row["spend_30d"]
        out[f"{cat}_spend_90d_avg"] = spend_90d
        out[f"{cat}_spend_12m_avg"] = spend_12m
        out[f"{cat}_spend_trend"] = (
            _round(spend_90d / spend_12m - 1.0)
            if spend_90d is not None and spend_12m not in (None, 0.0)
            else None
        )
        out[f"{cat}_txn_freq_90d"] = row["txn_freq_90d"]
        out[f"{cat}_spend_share_12m"] = (
            _round(spend_12m / total_12m) if spend_12m is not None and total_12m else None
        )
        out[f"{cat}_days_since_last"] = row["days_since_last"]
    return out


# ---------------------------------------------------------------------------
# Customer snapshots (persona C10001: strong EV case; C10005: insufficient data)
# ---------------------------------------------------------------------------

_C10001_TXN: dict[str, dict[str, float | None]] = {
    "fuel": {"spend_30d": 305.0, "spend_90d_avg": 310.0, "spend_12m_avg": 280.0,
             "txn_freq_90d": 9.0, "days_since_last": 3.0},
    "electricity": {"spend_30d": 96.0, "spend_90d_avg": 95.0, "spend_12m_avg": 92.0,
                    "txn_freq_90d": 3.0, "days_since_last": 12.0},
    "gas": {"spend_30d": 62.0, "spend_90d_avg": 70.0, "spend_12m_avg": 84.0,
            "txn_freq_90d": 3.0, "days_since_last": 20.0},
    "public_transport": {"spend_30d": 18.0, "spend_90d_avg": 22.0, "spend_12m_avg": 24.0,
                         "txn_freq_90d": 6.0, "days_since_last": 4.0},
    "home_improvement": {"spend_30d": 0.0, "spend_90d_avg": 0.0, "spend_12m_avg": round(320.0 / 12, 2),
                         "txn_freq_90d": 0.0, "days_since_last": 62.0},
    "automotive": {"spend_30d": 45.0, "spend_90d_avg": 40.0, "spend_12m_avg": 36.0,
                   "txn_freq_90d": 4.0, "days_since_last": 9.0},
    "utilities": {"spend_30d": 82.0, "spend_90d_avg": 80.0, "spend_12m_avg": 78.0,
                  "txn_freq_90d": 3.0, "days_since_last": 15.0},
}
_C10001_TOTAL_12M = 2350.0

_C10005_TXN: dict[str, dict[str, float | None]] = {
    "fuel": {"spend_30d": 96.0, "spend_90d_avg": 88.0, "spend_12m_avg": None,
             "txn_freq_90d": 4.0, "days_since_last": 5.0},
    "electricity": {"spend_30d": 52.0, "spend_90d_avg": 50.0, "spend_12m_avg": None,
                    "txn_freq_90d": 2.0, "days_since_last": 14.0},
    "gas": {"spend_30d": 0.0, "spend_90d_avg": 0.0, "spend_12m_avg": None,
            "txn_freq_90d": 0.0, "days_since_last": None},
    "public_transport": {"spend_30d": 24.0, "spend_90d_avg": 21.0, "spend_12m_avg": None,
                         "txn_freq_90d": 5.0, "days_since_last": 3.0},
    "home_improvement": {"spend_30d": 0.0, "spend_90d_avg": 0.0, "spend_12m_avg": None,
                         "txn_freq_90d": 0.0, "days_since_last": None},
    "automotive": {"spend_30d": 0.0, "spend_90d_avg": 0.0, "spend_12m_avg": None,
                   "txn_freq_90d": 0.0, "days_since_last": None},
    "utilities": {"spend_30d": 41.0, "spend_90d_avg": 40.0, "spend_12m_avg": None,
                  "txn_freq_90d": 2.0, "days_since_last": 11.0},
}


def _customer_snapshot_c10001() -> CustomerSnapshot:
    features = _feature_vector({
        **_txn_features(_C10001_TXN, _C10001_TOTAL_12M),
        "txn_months_observed": 18,
        "txn_count_12m": 164,
        "total_spend_12m_avg": _C10001_TOTAL_12M,
        "tenure_months": 61,
        "has_vehicle": True,
        "is_ice": True,
        "is_ev": False,
        "is_hybrid": False,
        "vehicle_age_years": 6.0,
        "annual_mileage_km": 15200.0,
        "mileage_is_estimated": False,
        "vehicle_record_age_days": 46,
        "has_vehicle_finance": False,
        "home_owner": True,
        "has_mortgage": True,
        "mortgage_tenure_months": 96,
        "has_existing_solar": False,
        "has_investments": False,
        "heating_is_gas": True,
        "heating_is_electric": False,
        "property_is_house": True,
        "electricity_kwh_12m": 3600.0,
        "gas_kwh_12m": 11800.0,
        "electricity_trend": 0.04,
        "energy_months_present": 12,
        "is_paperless": False,
        "paper_statements_3m": 3,
        "paper_statements_12m": 12,
        "digital_statement_ratio": 0.0,
        "digital_txn_3m_avg": 42.0,
        "app_logins_3m_avg": 14.0,
        "app_logins_trend": 0.05,
        "branch_visits_3m": 0,
        "digital_months_present": 12,
        "sustainability_preference": 4,
        "holds_ev_finance": False,
        "holds_green_home_loan": False,
        "holds_solar_finance": False,
    })
    electricity = _C10001_TXN["electricity"]["spend_90d_avg"]
    gas = _C10001_TXN["gas"]["spend_90d_avg"]
    utilities = _C10001_TXN["utilities"]["spend_90d_avg"]
    electricity_12m = _C10001_TXN["electricity"]["spend_12m_avg"]
    gas_12m = _C10001_TXN["gas"]["spend_12m_avg"]
    utilities_12m = _C10001_TXN["utilities"]["spend_12m_avg"]
    assert electricity is not None and gas is not None and utilities is not None
    assert electricity_12m is not None and gas_12m is not None and utilities_12m is not None
    return CustomerSnapshot(
        customer_id="C10001",
        feature_cutoff=CUTOFF,
        generated_at=PREDICTED_AT,
        feature_version=FEATURE_VERSION,
        segment="MASS_AFFLUENT",
        vehicle=VehicleFacts(
            has_vehicle=True,
            fuel_type=FuelType.PETROL,
            vehicle_age_years=6.0,
            annual_mileage_km=15200.0,
            mileage_is_estimated=False,
            record_updated_at=date(2026, 5, 15),
            has_vehicle_finance=False,
        ),
        home=HomeFacts(
            home_owner=True,
            has_mortgage=True,
            mortgage_tenure_months=96,
            has_existing_solar=False,
            heating_type=HeatingType.GAS_BOILER,
            property_type="SEMI_DETACHED",
            region="South East",
        ),
        energy=EnergyFacts(
            electricity_kwh_12m=3600.0,
            gas_kwh_12m=11800.0,
            energy_months_present=12,
            electricity_trend=0.04,
        ),
        digital=DigitalFacts(
            is_paperless=False,
            paper_statements_3m=3,
            paper_statements_12m=12,
            digital_statement_ratio=0.0,
            digital_transactions_3m_avg=42.0,
            branch_visits_3m=0,
        ),
        spend=SpendFacts(
            fuel_spend_90d_monthly_avg=310.0,
            fuel_txn_frequency_90d=9,
            electricity_spend_90d_monthly_avg=electricity,
            gas_spend_90d_monthly_avg=gas,
            utilities_spend_90d_monthly_avg=utilities,
            home_improvement_spend_12m=320.0,
            utility_spend_trend=_round(
                (electricity + gas + utilities) / (electricity_12m + gas_12m + utilities_12m) - 1.0
            ),
        ),
        features=features,
        data_quality=DataQualityEvidence(
            transaction_months_observed=18,
            first_transaction_date=date(2025, 1, 3),
            last_transaction_date=date(2026, 6, 29),
            vehicle_record_age_days=46,
            energy_months_present=12,
            digital_months_present=12,
            missing_fields=[],
            estimated_fields=[],
            invalid_product_records=0,
        ),
    )


def _customer_snapshot_c10005() -> CustomerSnapshot:
    features = _feature_vector({
        **_txn_features(_C10005_TXN, None),
        "txn_months_observed": 2,
        "txn_count_12m": 27,
        "total_spend_12m_avg": None,
        "tenure_months": 14,
        "has_vehicle": None,
        "is_ice": None,
        "is_ev": None,
        "is_hybrid": None,
        "vehicle_age_years": None,
        "annual_mileage_km": None,
        "mileage_is_estimated": None,
        "vehicle_record_age_days": None,
        "has_vehicle_finance": None,
        "home_owner": None,
        "has_mortgage": None,
        "mortgage_tenure_months": None,
        "has_existing_solar": None,
        "has_investments": None,
        "heating_is_gas": None,
        "heating_is_electric": None,
        "property_is_house": None,
        "electricity_kwh_12m": None,
        "gas_kwh_12m": None,
        "electricity_trend": None,
        "energy_months_present": 3,
        "is_paperless": False,
        "paper_statements_3m": 3,
        "paper_statements_12m": None,
        "digital_statement_ratio": None,
        "digital_txn_3m_avg": None,
        "app_logins_3m_avg": None,
        "app_logins_trend": None,
        "branch_visits_3m": None,
        "digital_months_present": 2,
        "sustainability_preference": None,
        "holds_ev_finance": False,
        "holds_green_home_loan": False,
        "holds_solar_finance": False,
    })
    return CustomerSnapshot(
        customer_id="C10005",
        feature_cutoff=CUTOFF,
        generated_at=PREDICTED_AT,
        feature_version=FEATURE_VERSION,
        segment="MASS",
        vehicle=VehicleFacts(),
        home=HomeFacts(region="Wales"),
        energy=EnergyFacts(energy_months_present=3),
        digital=DigitalFacts(is_paperless=False, paper_statements_3m=3),
        spend=SpendFacts(
            fuel_spend_90d_monthly_avg=88.0,
            fuel_txn_frequency_90d=4,
            electricity_spend_90d_monthly_avg=50.0,
            gas_spend_90d_monthly_avg=0.0,
            utilities_spend_90d_monthly_avg=40.0,
            home_improvement_spend_12m=0.0,
            utility_spend_trend=None,
        ),
        features=features,
        data_quality=DataQualityEvidence(
            transaction_months_observed=2,
            first_transaction_date=date(2026, 5, 2),
            last_transaction_date=date(2026, 6, 27),
            vehicle_record_age_days=None,
            energy_months_present=3,
            digital_months_present=2,
            missing_fields=["home_owner", "has_mortgage", "vehicle_record",
                            "electricity_kwh_12m", "gas_kwh_12m"],
            estimated_fields=[],
            invalid_product_records=0,
        ),
    )


# ---------------------------------------------------------------------------
# Propensity results
# ---------------------------------------------------------------------------


def _propensity_c10001_ev() -> PropensityResult:
    return PropensityResult(
        customer_id="C10001",
        product=Product.EV_FINANCE,
        propensity=0.84,
        raw_score=0.79,
        model_type=ModelType.GRADIENT_BOOSTING,
        model_version=MODEL_VERSIONS[Product.EV_FINANCE],
        calibration_method="isotonic",
        calibration_version=CALIBRATION_VERSIONS[Product.EV_FINANCE],
        feature_version=FEATURE_VERSION,
        feature_cutoff=CUTOFF,
        outcome_window_end=WINDOW_END,
        prediction_timestamp=PREDICTED_AT,
        in_model_population=True,
        population_exclusion=None,
        reason_codes=[
            ReasonCode.HIGH_FUEL_SPEND,
            ReasonCode.HIGH_ANNUAL_MILEAGE,
            ReasonCode.ICE_VEHICLE_OWNER,
        ],
        evidence={
            "fuel_spend_90d_avg": 310.0,
            "annual_mileage_km": 15200.0,
            "is_ice": 1.0,
            "vehicle_age_years": 6.0,
            "sustainability_preference": 4.0,
        },
        confidence=ConfidenceResult(
            status=ConfidenceStatus.VALIDATED,
            value=0.87,
            bucket=ConfidenceBucket.HIGH,
            method_version=CONFIDENCE_METHOD_VERSION,
        ),
    )


def _propensity_c10005_solar() -> PropensityResult:
    return PropensityResult(
        customer_id="C10005",
        product=Product.SOLAR_FINANCE,
        propensity=0.38,
        raw_score=0.44,
        model_type=ModelType.LOGISTIC,
        model_version=MODEL_VERSIONS[Product.SOLAR_FINANCE],
        calibration_method="platt",
        calibration_version=CALIBRATION_VERSIONS[Product.SOLAR_FINANCE],
        feature_version=FEATURE_VERSION,
        feature_cutoff=CUTOFF,
        outcome_window_end=WINDOW_END,
        prediction_timestamp=PREDICTED_AT,
        in_model_population=True,
        population_exclusion=None,
        reason_codes=[],
        evidence={
            "home_owner": None,
            "has_existing_solar": None,
            "electricity_kwh_12m": None,
            "energy_months_present": 3.0,
        },
        confidence=ConfidenceResult(
            status=ConfidenceStatus.SUPPRESSED,
            method_version=CONFIDENCE_METHOD_VERSION,
            limitation=(
                "Suppressed: critical fields (home ownership, existing solar status) are missing, "
                "so reliability cannot be validated for this customer."
            ),
        ),
    )


# ---------------------------------------------------------------------------
# Trust assessments
# ---------------------------------------------------------------------------


def _trust(
    customer_id: str,
    product: Product,
    *,
    score: float,
    status: TrustStatus,
    completeness: float,
    freshness: float,
    cross_source_consistency: float,
    critical_fields_present: bool,
    ood_score: float,
    issues: Iterable[TrustIssue] = (),
) -> TrustAssessment:
    return TrustAssessment(
        customer_id=customer_id,
        product=product,
        score=score,
        status=status,
        completeness=completeness,
        freshness=freshness,
        cross_source_consistency=cross_source_consistency,
        critical_fields_present=critical_fields_present,
        ood_score=ood_score,
        issues=list(issues),
        method_version=TRUST_METHOD_VERSION,
        assessed_at=PREDICTED_AT,
    )


def _trust_c10001_ev() -> TrustAssessment:
    return _trust(
        "C10001",
        Product.EV_FINANCE,
        score=0.91,
        status=TrustStatus.HIGH,
        completeness=0.96,
        freshness=0.89,
        cross_source_consistency=0.92,
        critical_fields_present=True,
        ood_score=0.08,
    )


def _trust_c10004_ev() -> TrustAssessment:
    return _trust(
        "C10004",
        Product.EV_FINANCE,
        score=0.46,
        status=TrustStatus.LOW,
        completeness=0.93,
        freshness=0.78,
        cross_source_consistency=0.20,
        critical_fields_present=True,
        ood_score=0.10,
        issues=[
            TrustIssue(
                code=TrustIssueCode.EV_RECORD_WITH_RECURRING_FUEL_SPEND,
                category=TrustIssueCategory.CONFLICT,
                severity=Severity.HIGH,
                message=(
                    "Vehicle record shows an EV, but categorised fuel spend is high and recurring. "
                    "Possible causes: second vehicle, stale record or merchant misclassification."
                ),
                fields=["vehicle.fuel_type", "spend.fuel_spend_90d_monthly_avg"],
            ),
        ],
    )


def _trust_c10005_solar() -> TrustAssessment:
    return _trust(
        "C10005",
        Product.SOLAR_FINANCE,
        score=0.44,
        status=TrustStatus.INSUFFICIENT,
        completeness=0.31,
        freshness=0.70,
        cross_source_consistency=1.0,
        critical_fields_present=False,
        ood_score=0.12,
        issues=[
            TrustIssue(
                code=TrustIssueCode.HOME_OWNERSHIP_UNKNOWN,
                category=TrustIssueCategory.CRITICAL_FIELD,
                severity=Severity.HIGH,
                message="Home ownership is unknown, so Solar Finance cannot be assessed.",
                fields=["home.home_owner"],
            ),
            TrustIssue(
                code=TrustIssueCode.SHORT_TRANSACTION_HISTORY,
                category=TrustIssueCategory.COMPLETENESS,
                severity=Severity.MEDIUM,
                message="Only 2 months of transaction history are available up to the cutoff.",
                fields=["data_quality.transaction_months_observed"],
            ),
            TrustIssue(
                code=TrustIssueCode.ENERGY_RECORDS_INCOMPLETE,
                category=TrustIssueCategory.COMPLETENESS,
                severity=Severity.LOW,
                message="Energy usage covers 3 of the last 12 months.",
                fields=["energy.energy_months_present"],
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Impact results
# ---------------------------------------------------------------------------

EV_BASELINE_KG = 2850.0
EV_SCENARIO_KG = 1180.0
EV_ANNUAL_KM = 15200.0


def _impact_ev_available() -> ImpactResult:
    # Factors back-solved from the headline numbers: 2850 / 15200 km = 0.1875 kg/km;
    # 15200 km x 0.2 kWh/km x 0.388 kg/kWh = 1179.5 kg, shown rounded as 1180.
    return ImpactResult(
        customer_id="C10001",
        product=Product.EV_FINANCE,
        status=ImpactStatus.AVAILABLE,
        metric="kg_co2e_per_year",
        unit="kg CO2e",
        baseline=EV_BASELINE_KG,
        scenario=EV_SCENARIO_KG,
        estimated_reduction=EV_BASELINE_KG - EV_SCENARIO_KG,
        secondary_metrics=[],
        methodology_id=EV_METHOD_ID,
        method_version=EV_METHOD_VERSION,
        factor_ids=["UKGHG_PETROL_CAR_OPERATIONAL", "UKGHG_GRID_ELECTRICITY_OPERATIONAL"],
        factor_source="UK Government GHG Conversion Factors",
        factor_version=EMISSION_FACTOR_VERSION,
        boundary=(
            "operational well-to-wheel where matched factors are available; manufacturing excluded"
        ),
        grid_scenario="current-year factor for headline annual estimate",
        assumptions=[
            ImpactAssumption(
                name="annual_mileage_km",
                value=EV_ANNUAL_KM,
                unit="km/year",
                source="customer_snapshot C10001 vehicle.annual_mileage_km",
                is_estimated=False,
            ),
            ImpactAssumption(
                name="vehicle_fuel_type",
                value=FuelType.PETROL.value,
                source="customer_snapshot C10001 vehicle.fuel_type",
            ),
            ImpactAssumption(
                name="ice_operational_factor",
                value=0.1875,
                unit="kg CO2e/km",
                source="placeholder back-solved from spec section 5 baseline; replace with pinned factor",
                is_estimated=True,
            ),
            ImpactAssumption(
                name="ev_energy_intensity",
                value=0.2,
                unit="kWh/km",
                source="placeholder back-solved from spec section 5 scenario; replace with pinned value",
                is_estimated=True,
            ),
            ImpactAssumption(
                name="grid_operational_factor",
                value=0.388,
                unit="kg CO2e/kWh",
                source="placeholder back-solved from spec section 5 scenario; replace with pinned factor",
                is_estimated=True,
            ),
            ImpactAssumption(name="time_horizon", value="1 year"),
            ImpactAssumption(name="manufacturing_emissions_included", value=False),
        ],
        data_cutoff=CUTOFF,
        calculation_timestamp=PREDICTED_AT,
        carbon_engine_version=CARBON_ENGINE_VERSION,
    )


def _impact_solar_unavailable() -> ImpactResult:
    return ImpactResult(
        customer_id="C10005",
        product=Product.SOLAR_FINANCE,
        status=ImpactStatus.UNAVAILABLE,
        methodology_id=SOLAR_METHOD_ID,
        method_version=SOLAR_METHOD_VERSION,
        unavailable_reason="INSUFFICIENT_SOLAR_GENERATION_INPUTS",
        data_cutoff=CUTOFF,
        calculation_timestamp=PREDICTED_AT,
        carbon_engine_version=CARBON_ENGINE_VERSION,
    )


def _impact_paperless_not_claimed() -> ImpactResult:
    return ImpactResult(
        customer_id="C10003",
        product=Product.PAPERLESS_BANKING,
        status=ImpactStatus.NOT_CLAIMED,
        secondary_metrics=[
            ImpactMetric(name="paper_statements_avoided_per_year", value=12.0, unit="statements"),
        ],
        method_version=PAPERLESS_METHOD_VERSION,
        assumptions=[
            ImpactAssumption(
                name="carbon_impact_claim",
                value=(
                    "not claimed: no defensible lifecycle method is documented (spec section 26)"
                ),
            ),
            ImpactAssumption(name="completion_status", value="NOT_STARTED"),
        ],
        data_cutoff=CUTOFF,
        calculation_timestamp=PREDICTED_AT,
        carbon_engine_version=CARBON_ENGINE_VERSION,
    )


# ---------------------------------------------------------------------------
# Recommendations (one per RecommendationState)
# ---------------------------------------------------------------------------


def _priority(
    *,
    rank: int,
    propensity: float,
    confidence: float,
    normalised_impact: float,
    trust: float,
) -> Priority:
    score = (
        PRIORITY_WEIGHTS["propensity"] * propensity
        + PRIORITY_WEIGHTS["confidence"] * confidence
        + PRIORITY_WEIGHTS["normalised_impact"] * normalised_impact
        + PRIORITY_WEIGHTS["trust"] * trust
    )
    return Priority(
        rank=rank,
        score=round(score, 2),
        version=PRIORITY_VERSION,
        components=PriorityComponents(
            propensity=propensity,
            confidence=confidence,
            normalised_impact=normalised_impact,
            trust=trust,
        ),
    )


def _recommendation(
    *,
    customer_id: str,
    product: Product,
    propensity: float,
    confidence: ConfidenceResult,
    trust: TrustAssessment,
    status: RecommendationState,
    guardrail_codes: Iterable[str] = (),
    conflict_codes: Iterable[str] = (),
    exclusions: Iterable[str] = (),
    priority: Priority | None = None,
    reason_codes: Iterable[ReasonCode] = (),
    evidence: Mapping[str, float | str | bool | None] | None = None,
    impact: ImpactResult | None = None,
) -> Recommendation:
    return Recommendation(
        recommendation_id=f"REC-{customer_id}-{PRODUCT_IDS[product]}-{CUTOFF.isoformat()}",
        customer_id=customer_id,
        opportunity_id=product,
        product_id=PRODUCT_IDS[product],
        propensity=propensity,
        propensity_model_version=MODEL_VERSIONS[product],
        calibration_version=CALIBRATION_VERSIONS[product],
        confidence=confidence,
        trust=trust,
        recommendation_status=status,
        guardrail_codes=list(guardrail_codes),
        conflict_codes=list(conflict_codes),
        exclusions=list(exclusions),
        priority=priority,
        reason_codes=list(reason_codes),
        evidence=dict(evidence or {}),
        impact=impact,
        data_cutoff=CUTOFF,
        outcome_window_end=WINDOW_END,
        prediction_timestamp=PREDICTED_AT,
        feature_version=FEATURE_VERSION,
        confidence_method_version=CONFIDENCE_METHOD_VERSION,
        trust_method_version=TRUST_METHOD_VERSION,
        carbon_engine_version=CARBON_ENGINE_VERSION,
        emission_factor_version=EMISSION_FACTOR_VERSION,
        recommendation_rule_version=RECOMMENDATION_RULE_VERSION,
        prompt_version=PROMPT_VERSION,
        llm_model_version=LLM_MODEL_VERSION,
    )


def _suppressed_confidence(limitation: str) -> ConfidenceResult:
    return ConfidenceResult(
        status=ConfidenceStatus.SUPPRESSED,
        method_version=CONFIDENCE_METHOD_VERSION,
        limitation=limitation,
    )


def _rec_recommend() -> Recommendation:
    impact = _impact_ev_available()
    trust = _trust_c10001_ev()
    normalised = round((EV_BASELINE_KG - EV_SCENARIO_KG) / EV_BASELINE_KG, 4)
    return _recommendation(
        customer_id="C10001",
        product=Product.EV_FINANCE,
        propensity=0.84,
        confidence=ConfidenceResult(
            status=ConfidenceStatus.VALIDATED,
            value=0.87,
            bucket=ConfidenceBucket.HIGH,
            method_version=CONFIDENCE_METHOD_VERSION,
        ),
        trust=trust,
        status=RecommendationState.RECOMMEND,
        priority=_priority(
            rank=1,
            propensity=0.84,
            confidence=0.87,
            normalised_impact=normalised,
            trust=trust.score,
        ),
        reason_codes=[
            ReasonCode.HIGH_FUEL_SPEND,
            ReasonCode.HIGH_ANNUAL_MILEAGE,
            ReasonCode.ICE_VEHICLE_OWNER,
        ],
        evidence={
            "monthly_fuel_spend": 310.0,
            "annual_mileage": 15200.0,
            "vehicle_fuel_type": FuelType.PETROL.value,
        },
        impact=impact,
    )


def _rec_conflict() -> Recommendation:
    return _recommendation(
        customer_id="C10004",
        product=Product.EV_FINANCE,
        propensity=0.71,
        confidence=_suppressed_confidence(
            "Suppressed while a high-severity conflict is unresolved."
        ),
        trust=_trust_c10004_ev(),
        status=RecommendationState.CONFLICT_REQUIRES_REVIEW,
        conflict_codes=[TrustIssueCode.EV_RECORD_WITH_RECURRING_FUEL_SPEND.value],
    )


def _rec_insufficient() -> Recommendation:
    return _recommendation(
        customer_id="C10005",
        product=Product.SOLAR_FINANCE,
        propensity=0.38,
        confidence=_suppressed_confidence(
            "Suppressed: critical field home ownership is missing."
        ),
        trust=_trust_c10005_solar(),
        status=RecommendationState.INSUFFICIENT_INFORMATION,
        guardrail_codes=[TrustIssueCode.HOME_OWNERSHIP_UNKNOWN.value],
        impact=_impact_solar_unavailable(),
    )


def _rec_suppressed() -> Recommendation:
    return _recommendation(
        customer_id="C10006",
        product=Product.EV_FINANCE,
        propensity=0.91,
        confidence=_suppressed_confidence(
            "Not displayed: customer already holds EV_FINANCE, so is outside the model population."
        ),
        trust=_trust(
            "C10006",
            Product.EV_FINANCE,
            score=0.90,
            status=TrustStatus.HIGH,
            completeness=0.95,
            freshness=0.92,
            cross_source_consistency=0.95,
            critical_fields_present=True,
            ood_score=0.07,
        ),
        status=RecommendationState.SUPPRESSED,
        exclusions=[PopulationExclusion.ALREADY_HOLDS_PRODUCT.value],
    )


def _rec_not_applicable() -> Recommendation:
    return _recommendation(
        customer_id="C10006",
        product=Product.PAPERLESS_BANKING,
        propensity=0.96,
        confidence=_suppressed_confidence(
            "Not displayed: customer is already paperless, so is outside the model population."
        ),
        trust=_trust(
            "C10006",
            Product.PAPERLESS_BANKING,
            score=0.88,
            status=TrustStatus.HIGH,
            completeness=0.94,
            freshness=0.90,
            cross_source_consistency=0.93,
            critical_fields_present=True,
            ood_score=0.06,
        ),
        status=RecommendationState.NOT_APPLICABLE,
        exclusions=[PopulationExclusion.ALREADY_PAPERLESS.value],
    )


def _rec_do_not_recommend() -> Recommendation:
    return _recommendation(
        customer_id="C10007",
        product=Product.GREEN_HOME,
        propensity=0.06,
        confidence=ConfidenceResult(
            status=ConfidenceStatus.VALIDATED,
            value=0.72,
            bucket=ConfidenceBucket.MEDIUM,
            method_version=CONFIDENCE_METHOD_VERSION,
        ),
        trust=_trust(
            "C10007",
            Product.GREEN_HOME,
            score=0.71,
            status=TrustStatus.ADEQUATE,
            completeness=0.84,
            freshness=0.80,
            cross_source_consistency=0.95,
            critical_fields_present=True,
            ood_score=0.15,
            issues=[
                TrustIssue(
                    code=TrustIssueCode.ENERGY_RECORDS_INCOMPLETE,
                    category=TrustIssueCategory.COMPLETENESS,
                    severity=Severity.LOW,
                    message="Energy usage covers 9 of the last 12 months.",
                    fields=["energy.energy_months_present"],
                ),
            ],
        ),
        status=RecommendationState.DO_NOT_RECOMMEND,
    )


# ---------------------------------------------------------------------------
# Explanation, portfolio summary and trends
# ---------------------------------------------------------------------------


def _explanation_template(recommendation: Recommendation) -> Explanation:
    assert recommendation.impact is not None
    impact = recommendation.impact
    assert impact.baseline is not None and impact.scenario is not None
    assert impact.estimated_reduction is not None
    return Explanation(
        recommendation_id=recommendation.recommendation_id,
        headline="Electric vehicle finance may suit your driving",
        explanation=(
            "Your fuel spending and annual mileage are high for a petrol car. An electric vehicle "
            "could reduce operational emissions for the miles you drive. This is an interest "
            "signal, not a finance decision."
        ),
        why_recommended=[
            "Fuel spending averaged £310 a month over the last 90 days.",
            "Your vehicle is a petrol car driven about 15,200 km a year.",
            "You currently own a petrol vehicle.",
        ],
        estimated_impact_text=(
            f"Estimated operational reduction of about {impact.estimated_reduction:,.0f} kg CO2e a "
            f"year, from a baseline of {impact.baseline:,.0f} to {impact.scenario:,.0f} kg CO2e. "
            "Manufacturing emissions are excluded."
        ),
        confidence_text=(
            f"Confidence is high ({recommendation.confidence.value:.2f}) for the data available "
            "at 30 June 2026."
        ),
        action_text="Discuss electric vehicle finance options with an adviser at your next review.",
        eligibility_disclaimer=(
            f"{ELIGIBILITY_MESSAGE} Any finance decision follows the bank's authorised product processes."
        ),
        missing_information=[],
        source=ExplanationSource.TEMPLATE,
        grounding_result=GroundingResult.NOT_RUN,
        prompt_version=TEMPLATE_PROMPT_VERSION,
        llm_model_version=None,
        cache_key=None,
        generated_at=PREDICTED_AT,
    )


# June-end figures per product; earlier months ramp towards them.
_SUMMARY_ROWS: dict[Product, dict[str, int]] = {
    Product.EV_FINANCE: {"candidates": 18200, "actionable": 9400, "high_confidence": 6100,
                         "high_trust": 7600, "suppressed_or_abstained": 3100},
    Product.GREEN_HOME: {"candidates": 12400, "actionable": 5200, "high_confidence": 3100,
                         "high_trust": 4400, "suppressed_or_abstained": 2600},
    Product.SOLAR_FINANCE: {"candidates": 6100, "actionable": 1100, "high_confidence": 700,
                            "high_trust": 900, "suppressed_or_abstained": 2100},
    Product.PAPERLESS_BANKING: {"candidates": 21000, "actionable": 8800, "high_confidence": 5200,
                                "high_trust": 9100, "suppressed_or_abstained": 1800},
}
EV_IMPACT_PER_CUSTOMER_KG = EV_BASELINE_KG - EV_SCENARIO_KG


def _portfolio_summary() -> PortfolioSummary:
    rows = []
    for product in PRODUCT_ORDER:
        row = _SUMMARY_ROWS[product]
        impact = (
            float(row["actionable"] * EV_IMPACT_PER_CUSTOMER_KG)
            if product is Product.EV_FINANCE
            else None
        )
        rows.append(
            ProductSummary(
                product=product,
                candidates=row["candidates"],
                actionable=row["actionable"],
                high_confidence=row["high_confidence"],
                high_trust=row["high_trust"],
                suppressed_or_abstained=row["suppressed_or_abstained"],
                estimated_impact_kg_co2e=impact,
            )
        )
    return PortfolioSummary(
        data_cutoff=CUTOFF,
        generated_at=PREDICTED_AT,
        customers_analysed=100000,
        customers_with_opportunity=43000,
        by_product=rows,
    )


_TREND_END: dict[Product, dict[str, float]] = {
    Product.EV_FINANCE: {"avg_propensity": 0.43, "avg_trust": 0.84, "observed_conversion_rate": 0.12},
    Product.GREEN_HOME: {"avg_propensity": 0.31, "avg_trust": 0.79, "observed_conversion_rate": 0.07},
    Product.SOLAR_FINANCE: {"avg_propensity": 0.22, "avg_trust": 0.66, "observed_conversion_rate": 0.03},
    Product.PAPERLESS_BANKING: {"avg_propensity": 0.47, "avg_trust": 0.86,
                                "observed_conversion_rate": 0.21},
}
_TREND_STEP: dict[str, float] = {"avg_propensity": 0.004, "avg_trust": 0.003,
                                 "observed_conversion_rate": 0.004}
_OPPORTUNITY_RAMP = (0.84, 0.87, 0.90, 0.93, 0.96, 1.0)


def _ramp(end: float, step: float) -> list[float]:
    """Six monthly values ending at ``end``; a negative step rises towards the past."""
    last = len(TREND_CUTOFFS) - 1
    return [_round(end - step * (last - i)) for i in range(len(TREND_CUTOFFS))]


def _portfolio_trends() -> PortfolioTrends:
    series: dict[Product, dict[str, list[float | None]]] = {}
    for product in PRODUCT_ORDER:
        row = _SUMMARY_ROWS[product]
        end = _TREND_END[product]
        june_high_conf = _round(row["high_confidence"] / row["actionable"])
        june_suppressed = _round(row["suppressed_or_abstained"] / row["candidates"])
        values: dict[str, list[float | None]] = {
            "opportunities": [float(round(row["actionable"] * f)) for f in _OPPORTUNITY_RAMP],
            "avg_propensity": _ramp(end["avg_propensity"], _TREND_STEP["avg_propensity"]),
            "high_confidence_share": _ramp(june_high_conf, 0.01),
            "suppression_or_conflict_rate": _ramp(june_suppressed, -0.004),
            "avg_trust": _ramp(end["avg_trust"], _TREND_STEP["avg_trust"]),
            "observed_conversion_rate": _ramp(
                end["observed_conversion_rate"], _TREND_STEP["observed_conversion_rate"]
            ),
            "paperless_adoption_rate": (
                _ramp(0.19, 0.01) if product is Product.PAPERLESS_BANKING else [None] * 6
            ),
            "estimated_impact_kg_co2e": (
                [float(round(row["actionable"] * f) * EV_IMPACT_PER_CUSTOMER_KG)
                 for f in _OPPORTUNITY_RAMP]
                if product is Product.EV_FINANCE
                else [None] * 6
            ),
        }
        series[product] = values
    points: list[TrendPoint] = []
    for index, month in enumerate(TREND_CUTOFFS):
        for product in PRODUCT_ORDER:
            values = series[product]
            points.append(
                TrendPoint(
                    month=month,
                    product=product,
                    opportunities=int(values["opportunities"][index] or 0),
                    avg_propensity=values["avg_propensity"][index],
                    high_confidence_share=values["high_confidence_share"][index],
                    estimated_impact_kg_co2e=values["estimated_impact_kg_co2e"][index],
                    suppression_or_conflict_rate=values["suppression_or_conflict_rate"][index],
                    avg_trust=values["avg_trust"][index],
                    observed_conversion_rate=values["observed_conversion_rate"][index],
                    paperless_adoption_rate=values["paperless_adoption_rate"][index],
                )
            )
    return PortfolioTrends(points=points)


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------


def build_fixtures() -> dict[str, Contract]:
    """Return every committed fixture keyed by file stem, in a fixed order."""
    impact_ev = _impact_ev_available()
    impact_solar = _impact_solar_unavailable()
    impact_paperless = _impact_paperless_not_claimed()
    recommend = _rec_recommend()
    assert recommend.impact == impact_ev
    insufficient = _rec_insufficient()
    assert insufficient.impact == impact_solar
    fixtures: dict[str, Contract] = {
        "customer_snapshot_C10001": _customer_snapshot_c10001(),
        "customer_snapshot_C10005": _customer_snapshot_c10005(),
        "propensity_result_C10001_EV": _propensity_c10001_ev(),
        "propensity_result_C10005_SOLAR": _propensity_c10005_solar(),
        "trust_assessment_C10001_EV": _trust_c10001_ev(),
        "trust_assessment_C10004_EV": _trust_c10004_ev(),
        "trust_assessment_C10005_SOLAR": _trust_c10005_solar(),
        "impact_result_ev_available": impact_ev,
        "impact_result_solar_unavailable": impact_solar,
        "impact_result_paperless_not_claimed": impact_paperless,
        f"recommendation_{RecommendationState.RECOMMEND.value}": recommend,
        f"recommendation_{RecommendationState.CONFLICT_REQUIRES_REVIEW.value}": _rec_conflict(),
        f"recommendation_{RecommendationState.INSUFFICIENT_INFORMATION.value}": insufficient,
        f"recommendation_{RecommendationState.SUPPRESSED.value}": _rec_suppressed(),
        f"recommendation_{RecommendationState.NOT_APPLICABLE.value}": _rec_not_applicable(),
        f"recommendation_{RecommendationState.DO_NOT_RECOMMEND.value}": _rec_do_not_recommend(),
        "explanation_template": _explanation_template(recommend),
        "portfolio_summary": _portfolio_summary(),
        "portfolio_trends": _portfolio_trends(),
    }
    return fixtures


def render_fixture(model: Contract) -> str:
    """Canonical on-disk text for one fixture (indented JSON with a trailing newline)."""
    return model.model_dump_json(indent=2) + "\n"


def write_fixtures(directory: Path | str = FIXTURE_DIR) -> list[Path]:
    """Write every fixture as ``<name>.json`` into ``directory``."""
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, model in build_fixtures().items():
        path = target / f"{name}.json"
        path.write_text(render_fixture(model), encoding="utf-8")
        written.append(path)
    return written


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

ModelT = TypeVar("ModelT", bound=Contract)


def load_fixture(name: str) -> dict[str, Any]:
    """Parsed JSON of one committed fixture, e.g. ``load_fixture("recommendation_RECOMMEND")``."""
    stem = name.removesuffix(".json")
    path = FIXTURE_DIR / f"{stem}.json"
    if not path.is_file():
        raise FileNotFoundError(f"unknown fixture: {name}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_model(name: str, cls: type[ModelT]) -> ModelT:
    """Validate one committed fixture as ``cls``."""
    return cls.model_validate(load_fixture(name))


# ---------------------------------------------------------------------------
# Fake providers (ports.py protocols backed by the fixtures)
# ---------------------------------------------------------------------------


def _default_snapshots() -> list[CustomerSnapshot]:
    return [
        load_model("customer_snapshot_C10001", CustomerSnapshot),
        load_model("customer_snapshot_C10005", CustomerSnapshot),
    ]


def _default_propensity() -> list[PropensityResult]:
    return [
        load_model("propensity_result_C10001_EV", PropensityResult),
        load_model("propensity_result_C10005_SOLAR", PropensityResult),
    ]


def _default_trust() -> list[TrustAssessment]:
    return [
        load_model("trust_assessment_C10001_EV", TrustAssessment),
        load_model("trust_assessment_C10004_EV", TrustAssessment),
        load_model("trust_assessment_C10005_SOLAR", TrustAssessment),
    ]


class FixtureSnapshotProvider(CustomerSnapshotProvider):
    """``CustomerSnapshotProvider`` serving fixture snapshots (or injected ones)."""

    def __init__(self, snapshots: Iterable[CustomerSnapshot] | None = None) -> None:
        items = _default_snapshots() if snapshots is None else list(snapshots)
        self._by_id: dict[str, CustomerSnapshot] = {s.customer_id: s for s in items}

    def list_customer_ids(self) -> list[str]:
        return sorted(self._by_id)

    def get_snapshot(self, customer_id: str, cutoff: date | None = None) -> CustomerSnapshot | None:
        snapshot = self._by_id.get(customer_id)
        if snapshot is None:
            return None
        if cutoff is not None and cutoff != snapshot.feature_cutoff:
            return None
        return snapshot


class FixturePropensityProvider(PropensityProvider):
    """``PropensityProvider`` returning fixture results keyed by customer and product."""

    def __init__(self, results: Iterable[PropensityResult] | None = None) -> None:
        items = _default_propensity() if results is None else list(results)
        self._by_key: dict[tuple[str, Product], PropensityResult] = {
            (r.customer_id, r.product): r for r in items
        }

    def score(self, snapshot: CustomerSnapshot, product: Product) -> PropensityResult:
        try:
            return self._by_key[(snapshot.customer_id, product)]
        except KeyError as exc:
            raise LookupError(
                f"no fixture propensity for {snapshot.customer_id} / {product.value}"
            ) from exc

    def score_many(self, snapshots: Iterable[CustomerSnapshot], product: Product) -> list[PropensityResult]:
        return [self.score(snapshot, product) for snapshot in snapshots]


class FixtureTrustProvider(TrustProvider):
    """``TrustProvider`` returning fixture assessments keyed by customer and product."""

    def __init__(self, assessments: Iterable[TrustAssessment] | None = None) -> None:
        items = _default_trust() if assessments is None else list(assessments)
        self._by_key: dict[tuple[str, Product], TrustAssessment] = {
            (a.customer_id, a.product): a for a in items
        }

    def assess(self, snapshot: CustomerSnapshot, product: Product) -> TrustAssessment:
        try:
            return self._by_key[(snapshot.customer_id, product)]
        except KeyError as exc:
            raise LookupError(
                f"no fixture trust assessment for {snapshot.customer_id} / {product.value}"
            ) from exc


if __name__ == "__main__":
    for path in write_fixtures():
        print(path)
