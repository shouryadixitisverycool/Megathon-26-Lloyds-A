"""Governed feature registry for the Customer 360 view (spec 7.3, 12).

Every column the Customer 360 frame can contain is described here: where it comes from,
which event-time column gates it against the cutoff, whether it is available at prediction
time, and whether it may be used by the propensity models.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

from greenpath.config import FEATURE_VERSION

__all__ = [
    "AUDIT_ONLY_COLUMNS", "CONTEXT_COLUMNS", "FEATURE_REGISTRY", "FEATURE_VERSION",
    "FeatureSpec", "POPULATION_FLAGS", "PROPENSITY_FEATURES", "PROXY_FEATURES",
    "SPEND_CATEGORIES", "registry_frame",
]

SPEND_CATEGORIES: tuple[str, ...] = (
    "fuel", "electricity", "gas", "public_transport", "home_improvement", "automotive", "utilities",
)


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    family: str
    source_table: str
    event_time_column: str | None
    available_at_prediction: bool
    allowed_in_propensity: bool
    description: str


# --- Column lists (order is the column order of the Customer 360 frame) ---------------------

_TXN_SUFFIXES = ("spend_30d", "spend_90d_avg", "spend_12m_avg", "spend_trend", "txn_freq_90d",
                 "spend_share_12m", "days_since_last")

PROPENSITY_FEATURES: list[str] = [
    *[f"{cat}_{suffix}" for cat in SPEND_CATEGORIES for suffix in _TXN_SUFFIXES],
    "txn_months_observed", "txn_count_12m", "total_spend_12m_avg", "tenure_months",
    "has_vehicle", "is_ice", "is_ev", "is_hybrid", "vehicle_age_years", "annual_mileage_km",
    "mileage_is_estimated", "vehicle_record_age_days", "has_vehicle_finance",
    "home_owner", "has_mortgage", "mortgage_tenure_months", "has_existing_solar",
    "has_investments", "heating_is_gas", "heating_is_electric", "property_is_house",
    "electricity_kwh_12m", "gas_kwh_12m", "electricity_trend", "energy_months_present",
    "is_paperless", "paper_statements_3m", "paper_statements_12m", "digital_statement_ratio",
    "digital_txn_3m_avg", "app_logins_3m_avg", "app_logins_trend", "branch_visits_3m",
    "digital_months_present",
    "sustainability_preference",
]

# Green holdings as of the cutoff: population filters, not features for their own product.
POPULATION_FLAGS: tuple[str, ...] = ("holds_ev_finance", "holds_green_home_loan", "holds_solar_finance")

CONTEXT_COLUMNS: tuple[str, ...] = (
    "region", "segment", "customer_since", "first_txn_date", "last_txn_date",
    "vehicle_record_updated_at", "fuel_type", "heating_type", "property_type",
    "invalid_product_records", "missing_fields", "estimated_fields",
)

# Joined from `customers` for fairness audits only; never present in the Customer 360 frame.
AUDIT_ONLY_COLUMNS: tuple[str, ...] = ("age_band", "income_band", "postcode_sector")

# Columns that can act as socioeconomic proxies (spec 12): excluded from default propensity features.
PROXY_FEATURES: tuple[str, ...] = ("income_band", "region", "age_band")


# --- Registry -------------------------------------------------------------------------------

def _spec(name, family, table, event_col, description, *, propensity=True, available=True):
    return FeatureSpec(name, family, table, event_col, available, propensity, description)


_TXN_DESC = {
    "spend_30d": "Debit spend in category over the 30 days ending at the cutoff (GBP)",
    "spend_90d_avg": "Debit spend in category over the 90 days ending at the cutoff, divided by 3 (GBP/month)",
    "spend_12m_avg": "Debit spend in category over the 365 days ending at the cutoff, divided by 12 (GBP/month)",
    "spend_trend": "spend_90d_avg / spend_12m_avg - 1 (NaN if 12m average is 0)",
    "txn_freq_90d": "Number of debit transactions in category over the 90 days ending at the cutoff",
    "spend_share_12m": "Category share of total 12m debit spend (NaN if no 12m debit spend)",
    "days_since_last": "Days from the last debit in category (any time <= cutoff) to the cutoff (NaN if never)",
}

_OTHER: dict[str, tuple[str, str, str | None, str]] = {
    # name: (family, table, event column, description)
    "txn_months_observed": ("transaction", "transactions", "date",
                            "Calendar months spanned from first transaction to the cutoff, inclusive (0 if none)"),
    "txn_count_12m": ("transaction", "transactions", "date",
                      "All transactions (debit and credit) in the 365 days ending at the cutoff"),
    "total_spend_12m_avg": ("transaction", "transactions", "date",
                            "Total debit spend over 365 days / 12 (GBP/month)"),
    "tenure_months": ("banking_relationship", "customers", "customer_since",
                      "Whole months from customer_since to the cutoff"),
    "has_vehicle": ("vehicle", "vehicles", "record_updated_at", "1 if a vehicle record exists as of the cutoff, NaN if not recorded"),
    "is_ice": ("vehicle", "vehicles", "record_updated_at", "Latest vehicle fuel type is PETROL or DIESEL"),
    "is_ev": ("vehicle", "vehicles", "record_updated_at", "Latest vehicle fuel type is EV"),
    "is_hybrid": ("vehicle", "vehicles", "record_updated_at", "Latest vehicle fuel type is HYBRID"),
    "vehicle_age_years": ("vehicle", "vehicles", "record_updated_at",
                          "vehicle_age at the record date plus time elapsed to the cutoff (years)"),
    "annual_mileage_km": ("vehicle", "vehicles", "record_updated_at", "Annual mileage of the latest vehicle record (km)"),
    "mileage_is_estimated": ("vehicle", "vehicles", "record_updated_at", "1 if mileage_source is ESTIMATED"),
    "vehicle_record_age_days": ("vehicle", "vehicles", "record_updated_at", "Days from the latest vehicle record to the cutoff"),
    "has_vehicle_finance": ("banking_relationship", "financial_products", "start_date",
                            "Active VEHICLE_FINANCE product as of the cutoff"),
    "home_owner": ("home", "customers", "record_updated_at", "Stated home ownership (NaN if unknown)"),
    "has_mortgage": ("banking_relationship", "financial_products", "start_date", "Active MORTGAGE product as of the cutoff"),
    "mortgage_tenure_months": ("banking_relationship", "financial_products", "start_date",
                               "Whole months since the earliest active mortgage started (NaN if none)"),
    "has_existing_solar": ("home", "customers", "solar_installed_at",
                           "Solar PV installed on or before the cutoff (NaN if unknown)"),
    "has_investments": ("banking_relationship", "financial_products", "start_date", "Active INVESTMENT product as of the cutoff"),
    "heating_is_gas": ("home", "customers", "record_updated_at", "Heating type is GAS_BOILER"),
    "heating_is_electric": ("home", "customers", "record_updated_at", "Heating type is ELECTRIC (heat pumps are not counted)"),
    "property_is_house": ("home", "customers", "record_updated_at", "Property type is not FLAT"),
    "electricity_kwh_12m": ("energy", "energy_usage", "month",
                            "Annualised electricity use: mean of observed months in the last 12 complete months x 12"),
    "gas_kwh_12m": ("energy", "energy_usage", "month", "Annualised gas use (as electricity_kwh_12m)"),
    "electricity_trend": ("energy", "energy_usage", "month", "Last-3-complete-month electricity average / 12m average - 1"),
    "energy_months_present": ("energy", "energy_usage", "month", "Months with an energy record among the last 12 complete months"),
    "is_paperless": ("digital", "digital_usage", "month", "digital_statements flag of the latest complete month <= cutoff"),
    "paper_statements_3m": ("digital", "digital_usage", "month", "Paper statements over the last 3 complete months"),
    "paper_statements_12m": ("digital", "digital_usage", "month", "Paper statements over the last 12 complete months"),
    "digital_statement_ratio": ("digital", "digital_usage", "month",
                                "Share of observed months in the last 12 with the paperless flag set"),
    "digital_txn_3m_avg": ("digital", "digital_usage", "month", "Mean monthly digital transactions, last 3 complete months"),
    "app_logins_3m_avg": ("digital", "digital_usage", "month", "Mean monthly app logins, last 3 complete months"),
    "app_logins_trend": ("digital", "digital_usage", "month", "app_logins_3m_avg / 12m average - 1"),
    "branch_visits_3m": ("digital", "digital_usage", "month", "Branch visits over the last 3 complete months"),
    "digital_months_present": ("digital", "digital_usage", "month", "Months with a digital record among the last 12 complete months"),
    "sustainability_preference": ("sustainability", "customers", "record_updated_at", "Stated sustainability preference 1-5 (NaN if unknown)"),
}

_POP_DESC = {
    "holds_ev_finance": "Active EV_FINANCE product as of the cutoff (population filter)",
    "holds_green_home_loan": "Active GREEN_HOME_LOAN product as of the cutoff (population filter)",
    "holds_solar_finance": "Active SOLAR_FINANCE product as of the cutoff (population filter)",
}

_CONTEXT_META: dict[str, tuple[str, str, str | None, str]] = {
    "region": ("context", "customers", "record_updated_at", "Region (aggregates and physical impact only; proxy-risk)"),
    "segment": ("context", "customers", "record_updated_at", "Customer segment as recorded before cutoff"),
    "customer_since": ("context", "customers", "customer_since", "Date the customer joined"),
    "first_txn_date": ("data_quality", "transactions", "date", "First transaction date <= cutoff"),
    "last_txn_date": ("data_quality", "transactions", "date", "Last transaction date <= cutoff"),
    "vehicle_record_updated_at": ("data_quality", "vehicles", "record_updated_at", "Date of the latest vehicle record <= cutoff"),
    "fuel_type": ("context", "vehicles", "record_updated_at", "Latest vehicle fuel type"),
    "heating_type": ("context", "customers", "record_updated_at", "Heating type"),
    "property_type": ("context", "customers", "record_updated_at", "Property type"),
    "invalid_product_records": ("data_quality", "financial_products", "start_date", "Count of INVALID product rows started <= cutoff"),
    "missing_fields": ("data_quality", "multiple", None, "Names of absent fields/groups (list)"),
    "estimated_fields": ("data_quality", "multiple", None, "Names of fields whose value is an estimate (list)"),
}

_AUDIT_META = {
    "age_band": "Age band (fairness audit only)",
    "income_band": "Income band (fairness audit only; excluded by proxy-risk policy)",
    "postcode_sector": "Postcode sector (fairness audit only; never a feature)",
}


def _build_registry() -> dict[str, FeatureSpec]:
    reg: dict[str, FeatureSpec] = {}
    for cat in SPEND_CATEGORIES:
        for suffix in _TXN_SUFFIXES:
            name = f"{cat}_{suffix}"
            reg[name] = _spec(name, "transaction", "transactions", "date", f"[{cat}] {_TXN_DESC[suffix]}")
    for name, (fam, table, ev, desc) in _OTHER.items():
        reg[name] = _spec(name, fam, table, ev, desc)
    for name in POPULATION_FLAGS:
        reg[name] = _spec(name, "banking_relationship", "financial_products", "start_date",
                          _POP_DESC[name], propensity=False)
    for name, (fam, table, ev, desc) in _CONTEXT_META.items():
        reg[name] = _spec(name, fam, table, ev, desc, propensity=False)
    for name, desc in _AUDIT_META.items():
        reg[name] = _spec(name, "audit_only", "customers", "record_updated_at", desc, propensity=False)
    return reg


FEATURE_REGISTRY: dict[str, FeatureSpec] = _build_registry()

assert set(PROPENSITY_FEATURES) <= set(FEATURE_REGISTRY)
assert set(CONTEXT_COLUMNS) <= set(FEATURE_REGISTRY)
assert len(PROPENSITY_FEATURES) == len(set(PROPENSITY_FEATURES))


def registry_frame() -> pd.DataFrame:
    """The registry as a DataFrame (one row per column) for the data card."""
    df = pd.DataFrame([asdict(s) for s in FEATURE_REGISTRY.values()])
    df["proxy_risk"] = df["name"].isin(PROXY_FEATURES)
    df["feature_version"] = FEATURE_VERSION
    return df
