"""Raw synthetic table schemas (spec 6.3/6.4) and a fail-fast validator.

The generator writes exactly these columns; every pipeline reads only these columns.
Ground-truth columns used only for evaluation live in separate *truth* tables so that
they can never enter the feature pipeline by accident.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from greenpath.contracts import FuelType, HeatingType, TransactionCategory


@dataclass(frozen=True)
class TableSchema:
    name: str
    columns: dict[str, str]  # column -> logical type: str|int|float|bool|date|category
    primary_key: tuple[str, ...]
    nullable: frozenset[str] = field(default_factory=frozenset)
    allowed_values: dict[str, frozenset[str]] = field(default_factory=dict)
    event_time_column: str | None = None  # column compared against the feature cutoff


def _vals(enum) -> frozenset[str]:
    return frozenset(m.value for m in enum)


REGIONS = frozenset({
    "North East", "North West", "Yorkshire", "East Midlands", "West Midlands",
    "East of England", "London", "South East", "South West", "Wales", "Scotland",
})
AGE_BANDS = frozenset({"18-24", "25-34", "35-44", "45-54", "55-64", "65+"})
INCOME_BANDS = frozenset({"<25k", "25-50k", "50-75k", "75-100k", "100k+"})
SEGMENTS = frozenset({"MASS", "MASS_AFFLUENT", "AFFLUENT"})
PRODUCT_TYPES = frozenset({
    "CURRENT_ACCOUNT", "MORTGAGE", "VEHICLE_FINANCE", "INVESTMENT",
    # Green products (adoption outcomes):
    "EV_FINANCE", "GREEN_HOME_LOAN", "SOLAR_FINANCE",
})
PRODUCT_STATUSES = frozenset({"ACTIVE", "CLOSED", "INVALID"})

CUSTOMERS = TableSchema(
    name="customers",
    columns={
        "customer_id": "str",
        "customer_since": "date",
        "age_band": "category",  # AUDIT ONLY - never a propensity feature
        "income_band": "category",  # AUDIT ONLY - excluded by proxy-risk policy (spec 12)
        "region": "category",  # aggregates / physical impact only
        "postcode_sector": "str",  # never a feature
        "segment": "category",
        "home_owner": "bool",
        "property_type": "category",
        "heating_type": "category",
        "has_solar_pv": "bool",
        "solar_installed_at": "date",
        "sustainability_preference": "int",  # 1..5 stated preference
        "record_updated_at": "date",
    },
    primary_key=("customer_id",),
    nullable=frozenset({"home_owner", "sustainability_preference", "region", "postcode_sector",
                        "property_type", "heating_type", "has_solar_pv", "solar_installed_at"}),
    allowed_values={
        "age_band": AGE_BANDS, "income_band": INCOME_BANDS, "region": REGIONS,
        "segment": SEGMENTS, "heating_type": _vals(HeatingType),
        "property_type": frozenset({"FLAT", "TERRACED", "SEMI_DETACHED", "DETACHED"}),
    },
)

TRANSACTIONS = TableSchema(
    name="transactions",
    columns={
        "transaction_id": "str",
        "customer_id": "str",
        "date": "date",
        "merchant_description": "str",  # raw, untrusted text; never sent to an LLM
        "amount": "float",  # positive GBP
        "debit_credit": "category",
    },
    primary_key=("transaction_id",),
    allowed_values={"debit_credit": frozenset({"DEBIT", "CREDIT"})},
    event_time_column="date",
)

# Evaluation-only ground truth for transaction categorisation.
TRANSACTION_TRUTH = TableSchema(
    name="transaction_truth",
    columns={"transaction_id": "str", "merchant_id": "str", "true_category": "category"},
    primary_key=("transaction_id",),
    allowed_values={"true_category": _vals(TransactionCategory)},
)

# Merchant catalogue used by the generator (evaluation / merchant-group split only).
MERCHANTS = TableSchema(
    name="merchants",
    columns={"merchant_id": "str", "brand": "str", "true_category": "category",
             "is_shift_only": "bool"},
    primary_key=("merchant_id",),
    allowed_values={"true_category": _vals(TransactionCategory)},
)

FINANCIAL_PRODUCTS = TableSchema(
    name="financial_products",
    columns={
        "customer_id": "str",
        "product": "category",
        "start_date": "date",
        "end_date": "date",
        "balance": "float",
        "status": "category",  # status as last recorded; derive as-of status from dates
    },
    primary_key=("customer_id", "product", "start_date"),
    nullable=frozenset({"end_date", "balance"}),
    allowed_values={"product": PRODUCT_TYPES, "status": PRODUCT_STATUSES},
    event_time_column="start_date",
)

# Vehicle records are a history: a new row is appended whenever the record changes.
VEHICLES = TableSchema(
    name="vehicles",
    columns={
        "customer_id": "str",
        "vehicle_type": "category",
        "fuel_type": "category",
        "vehicle_age": "float",  # years at record_updated_at
        "annual_mileage": "float",  # km/year
        "mileage_source": "category",
        "record_updated_at": "date",
    },
    primary_key=("customer_id", "record_updated_at"),
    nullable=frozenset({"annual_mileage", "mileage_source", "vehicle_age"}),
    allowed_values={
        "vehicle_type": frozenset({"CAR", "VAN", "MOTORCYCLE"}),
        "fuel_type": _vals(FuelType),
        "mileage_source": frozenset({"OBSERVED", "ESTIMATED"}),
    },
    event_time_column="record_updated_at",
)

ENERGY_USAGE = TableSchema(
    name="energy_usage",
    columns={
        "customer_id": "str",
        "month": "date",  # first day of month; available after month end
        "electricity_kwh": "float",
        "gas_kwh": "float",
        "source_quality": "category",
    },
    primary_key=("customer_id", "month"),
    nullable=frozenset({"electricity_kwh", "gas_kwh"}),
    allowed_values={"source_quality": frozenset({"SMART_METER", "ESTIMATED_BILL"})},
    event_time_column="month",
)

DIGITAL_USAGE = TableSchema(
    name="digital_usage",
    columns={
        "customer_id": "str",
        "month": "date",
        "digital_statements": "bool",  # paperless preference set during this month
        "paper_statements": "int",
        "digital_transactions": "int",
        "app_logins": "int",
        "branch_visits": "int",
    },
    primary_key=("customer_id", "month"),
    event_time_column="month",
)

# Adoption events for the four required opportunities. Labels are derived from these
# for any cutoff: adopted within (cutoff, cutoff + 90 days]. Never a feature source.
CUSTOMER_OUTCOMES = TableSchema(
    name="customer_outcomes",
    columns={"customer_id": "str", "product": "category", "adoption_date": "date"},
    primary_key=("customer_id", "product"),
    allowed_values={"product": frozenset({
        "EV_FINANCE", "GREEN_HOME", "SOLAR_FINANCE", "PAPERLESS_BANKING"})},
)

GREEN_PRODUCT_CATALOGUE = TableSchema(
    name="green_product_catalogue",
    columns={"product_id": "str", "product": "str", "category": "str",
             "intended_use_case": "str", "eligibility_reference": "str",
             "sustainability_metric": "str"},
    primary_key=("product_id",),
)

RAW_TABLES: dict[str, TableSchema] = {s.name: s for s in (
    CUSTOMERS, TRANSACTIONS, FINANCIAL_PRODUCTS, VEHICLES, ENERGY_USAGE, DIGITAL_USAGE,
    GREEN_PRODUCT_CATALOGUE,
)}
TRUTH_TABLES: dict[str, TableSchema] = {s.name: s for s in (
    TRANSACTION_TRUTH, MERCHANTS, CUSTOMER_OUTCOMES,
)}
ALL_TABLES = RAW_TABLES | TRUTH_TABLES


class SchemaError(ValueError):
    pass


def validate_table(df: pd.DataFrame, schema: TableSchema) -> None:
    """Raise SchemaError on malformed columns, logical types, keys or enum values."""
    cols = set(df.columns)
    expected = set(schema.columns)
    if cols != expected:
        raise SchemaError(f"{schema.name}: missing={sorted(expected - cols)} extra={sorted(cols - expected)}")
    for col in expected - schema.nullable:
        if df[col].isna().any():
            raise SchemaError(f"{schema.name}.{col}: unexpected nulls")
    if df.duplicated(list(schema.primary_key)).any():
        raise SchemaError(f"{schema.name}: duplicate primary key {schema.primary_key}")
    for col, allowed in schema.allowed_values.items():
        bad = set(df[col].dropna().astype(str).unique()) - allowed
        if bad:
            raise SchemaError(f"{schema.name}.{col}: unexpected values {sorted(bad)[:5]}")
    for col, kind in schema.columns.items():
        observed = df[col].dropna()
        if observed.empty:
            continue
        if kind == "date" and df[col].notna().any() and not pd.api.types.is_datetime64_any_dtype(df[col]):
            raise SchemaError(f"{schema.name}.{col}: expected datetime64 dtype")
        if kind in {"float", "int"}:
            if (not pd.api.types.is_numeric_dtype(observed)
                    or pd.api.types.is_bool_dtype(observed)):
                raise SchemaError(f"{schema.name}.{col}: expected numeric values")
            values = observed.to_numpy(dtype=float)
            if not np.isfinite(values).all():
                raise SchemaError(f"{schema.name}.{col}: numeric values must be finite")
            if kind == "int" and (values != np.floor(values)).any():
                raise SchemaError(f"{schema.name}.{col}: expected integer values")
        if kind == "bool" and not observed.map(lambda value: isinstance(value, (bool, np.bool_))).all():
            raise SchemaError(f"{schema.name}.{col}: expected boolean values")
        if kind in {"str", "category"} and not observed.map(lambda value: isinstance(value, str)).all():
            raise SchemaError(f"{schema.name}.{col}: expected string values")
    if schema.name == "transactions" and (df["amount"] <= 0).any():
        raise SchemaError("transactions.amount: must be positive")
    nonnegative = {
        "vehicles": ("vehicle_age", "annual_mileage"),
        "energy_usage": ("electricity_kwh", "gas_kwh"),
        "digital_usage": ("paper_statements", "digital_transactions", "app_logins", "branch_visits"),
    }
    for col in nonnegative.get(schema.name, ()):
        if (df[col].dropna() < 0).any():
            raise SchemaError(f"{schema.name}.{col}: must be non-negative")
    if schema.name == "financial_products" and (df["end_date"] < df["start_date"]).any():
        raise SchemaError("financial_products: end_date precedes start_date")
    if schema.name == "customers" and not df["sustainability_preference"].dropna().between(1, 5).all():
        raise SchemaError("customers.sustainability_preference: must be in 1..5")
