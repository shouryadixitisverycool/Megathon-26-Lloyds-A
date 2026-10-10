"""Hand-made raw tables for Customer 360 tests (5 customers, cutoff 2026-06-30).

C001 rich history (hand-computed values in test_customer360.py)
C002 joined 2026-05-01, nothing else known (NaN semantics)
C003 history but no spend in tracked categories; EV with estimated mileage; solar; INVALID product
C004 joins after the cutoff (must be excluded)
C005 vehicle history (PETROL -> HYBRID), closed mortgage, solar/finance only after the cutoff
"""

from __future__ import annotations

import copy
from datetime import date

import numpy as np
import pandas as pd

from greenpath.pipelines import schemas

CUTOFF = date(2026, 6, 30)
D = pd.Timestamp


def _df(rows: list[dict], schema: schemas.TableSchema) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=list(schema.columns))
    for col, kind in schema.columns.items():
        if kind == "date":
            df[col] = pd.to_datetime(df[col]).astype("datetime64[ns]")
        elif kind == "float":
            df[col] = df[col].astype(float)
    return df


def _customer(cid, since, **kw) -> dict:
    row = dict(customer_id=cid, customer_since=D(since), age_band="35-44", income_band="50-75k",
               region=None, postcode_sector=None, segment="MASS", home_owner=None,
               property_type=None, heating_type=None, has_solar_pv=None, solar_installed_at=pd.NaT,
               sustainability_preference=None, record_updated_at=D("2026-06-01"))
    row.update(kw)
    return row


def _months(start: str, end: str) -> list[pd.Timestamp]:
    return list(pd.date_range(start, end, freq="MS"))


def make_tables() -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    customers = [
        _customer("C001", "2024-01-15", region="London", segment="AFFLUENT", home_owner=True,
                  property_type="DETACHED", heating_type="GAS_BOILER", has_solar_pv=False,
                  sustainability_preference=4),
        _customer("C002", "2026-05-01"),
        _customer("C003", "2025-03-10", region="Wales", home_owner=True, property_type="TERRACED",
                  heating_type="HEAT_PUMP", has_solar_pv=True, solar_installed_at=D("2026-02-01"),
                  sustainability_preference=5),
        _customer("C004", "2026-08-01", region="Scotland", home_owner=True),
        _customer("C005", "2024-06-01", region="Yorkshire", home_owner=False, property_type="FLAT",
                  heating_type="ELECTRIC", has_solar_pv=True, solar_installed_at=D("2026-09-01"),
                  sustainability_preference=2),
    ]

    vehicles = [
        dict(customer_id="C001", vehicle_type="CAR", fuel_type="PETROL", vehicle_age=5.0,
             annual_mileage=12000.0, mileage_source="OBSERVED", record_updated_at=D("2026-03-01")),
        dict(customer_id="C003", vehicle_type="CAR", fuel_type="EV", vehicle_age=1.0,
             annual_mileage=8000.0, mileage_source="ESTIMATED", record_updated_at=D("2025-12-01")),
        dict(customer_id="C005", vehicle_type="CAR", fuel_type="PETROL", vehicle_age=8.0,
             annual_mileage=15000.0, mileage_source="OBSERVED", record_updated_at=D("2025-01-10")),
        dict(customer_id="C005", vehicle_type="CAR", fuel_type="HYBRID", vehicle_age=0.1,
             annual_mileage=np.nan, mileage_source=None, record_updated_at=D("2026-05-01")),
    ]

    def prod(cid, product, start, end=None, status="ACTIVE", balance=1000.0):
        return dict(customer_id=cid, product=product, start_date=D(start),
                    end_date=D(end) if end else pd.NaT, balance=balance, status=status)

    products = [
        prod("C001", "CURRENT_ACCOUNT", "2024-01-15"),
        prod("C001", "MORTGAGE", "2024-06-10"),
        prod("C001", "VEHICLE_FINANCE", "2025-01-01"),
        prod("C003", "EV_FINANCE", "2025-12-01"),
        prod("C003", "INVESTMENT", "2026-01-01", status="INVALID"),
        prod("C005", "MORTGAGE", "2024-07-01", end="2026-01-01", status="CLOSED"),
        prod("C005", "SOLAR_FINANCE", "2026-08-01"),
    ]

    energy = []
    for m in _months("2025-01-01", "2026-06-01"):
        recent = m >= D("2026-04-01")
        energy.append(dict(customer_id="C001", month=m, electricity_kwh=400.0 if recent else 300.0,
                           gas_kwh=500.0, source_quality="SMART_METER"))
    for m in _months("2026-05-01", "2026-06-01"):
        energy.append(dict(customer_id="C003", month=m, electricity_kwh=250.0, gas_kwh=np.nan,
                           source_quality="ESTIMATED_BILL"))

    digital = []
    for m in _months("2025-01-01", "2026-06-01"):
        recent = m >= D("2026-04-01")
        digital.append(dict(customer_id="C001", month=m, digital_statements=bool(recent),
                            paper_statements=0 if recent else 2,
                            digital_transactions=20 if recent else 10,
                            app_logins=30 if recent else 10, branch_visits=1))
    for m in _months("2026-04-01", "2026-06-01"):
        digital.append(dict(customer_id="C003", month=m, digital_statements=False,
                            paper_statements=1, digital_transactions=5, app_logins=2, branch_visits=0))

    txns = []

    def t(cid, day, amount, cat, dc="DEBIT"):
        txns.append(dict(transaction_id=f"T{len(txns):04d}", customer_id=cid, date=D(day),
                         merchant_description=f"{cat} merchant", amount=float(amount),
                         debit_credit=dc, category=cat, category_confidence=1.0,
                         category_method="RULE"))

    # C001: fuel
    t("C001", "2026-06-15", 50, "FUEL")
    t("C001", "2026-06-01", 30, "FUEL")          # ago 29 -> inside 30d
    t("C001", "2026-05-31", 40, "FUEL")          # ago 30 -> outside 30d, inside 90d
    t("C001", "2026-04-15", 60, "FUEL")
    t("C001", "2026-04-01", 100, "FUEL")         # ago 90 -> outside 90d, inside 12m
    t("C001", "2025-07-02", 20, "FUEL")          # ago 363 -> inside 12m
    t("C001", "2025-06-30", 500, "FUEL")         # ago 365 -> outside 12m (first transaction)
    t("C001", "2026-06-10", 999, "FUEL", "CREDIT")   # credits never count as spend
    # C001: electricity and other
    t("C001", "2026-06-20", 90, "ELECTRICITY")
    t("C001", "2025-12-01", 110, "ELECTRICITY")
    t("C001", "2026-06-05", 200, "OTHER")
    # C003: history but no spend in any tracked category
    t("C003", "2026-06-01", 20, "OTHER")
    t("C003", "2026-05-01", 15, "FUEL", "CREDIT")
    # C005: gas
    t("C005", "2026-06-30", 40, "GAS")           # ago 0 (on the cutoff itself)
    t("C005", "2026-03-31", 80, "GAS")

    tables = {
        "customers": _df(customers, schemas.CUSTOMERS),
        "financial_products": _df(products, schemas.FINANCIAL_PRODUCTS),
        "vehicles": _df(vehicles, schemas.VEHICLES),
        "energy_usage": _df(energy, schemas.ENERGY_USAGE),
        "digital_usage": _df(digital, schemas.DIGITAL_USAGE),
        "green_product_catalogue": pd.DataFrame([dict(
            product_id="GP01", product="EV Finance", category="mobility", intended_use_case="x",
            eligibility_reference="x", sustainability_metric="x")]),
    }
    txn_df = pd.DataFrame(txns)
    txn_df["date"] = txn_df["date"].astype("datetime64[ns]")
    tables["transactions"] = txn_df[list(schemas.TRANSACTIONS.columns)].copy()
    for name, schema in schemas.RAW_TABLES.items():
        schemas.validate_table(tables[name], schema)
    return tables, txn_df


def add_post_cutoff_events(tables: dict[str, pd.DataFrame], txns: pd.DataFrame
                           ) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    """Copies of the fixtures with events strictly after CUTOFF (2026-06-30) added."""
    tb = {k: v.copy() for k, v in tables.items()}
    tx = txns.copy()

    extra_tx = []
    for i, (cid, day, amt, cat, dc) in enumerate([
        ("C001", "2026-07-01", 300, "FUEL", "DEBIT"),
        ("C001", "2026-07-20", 80, "ELECTRICITY", "DEBIT"),
        ("C002", "2026-07-05", 60, "GAS", "DEBIT"),      # first-ever transaction is post-cutoff
        ("C003", "2026-08-10", 45, "FUEL", "DEBIT"),
        ("C005", "2026-09-01", 25, "UTILITIES", "CREDIT"),
    ]):
        extra_tx.append(dict(transaction_id=f"X{i:04d}", customer_id=cid, date=pd.Timestamp(day),
                             merchant_description="post", amount=float(amt), debit_credit=dc,
                             category=cat, category_confidence=1.0, category_method="RULE"))
    tx = pd.concat([tx, pd.DataFrame(extra_tx).astype({"date": "datetime64[ns]"})], ignore_index=True)

    D_ = pd.Timestamp
    tb["vehicles"] = pd.concat([tb["vehicles"], pd.DataFrame([
        dict(customer_id="C001", vehicle_type="CAR", fuel_type="EV", vehicle_age=0.0,
             annual_mileage=20000.0, mileage_source="OBSERVED", record_updated_at=D_("2026-07-15")),
        dict(customer_id="C002", vehicle_type="CAR", fuel_type="DIESEL", vehicle_age=3.0,
             annual_mileage=9000.0, mileage_source="OBSERVED", record_updated_at=D_("2026-07-02")),
    ]).astype({"record_updated_at": "datetime64[ns]"})], ignore_index=True)

    fp = tb["financial_products"].copy()
    fp.loc[(fp.customer_id == "C001") & (fp["product"] == "VEHICLE_FINANCE"), "end_date"] = D_("2026-08-15")
    new_products = pd.DataFrame([
        dict(customer_id="C001", product="INVESTMENT", start_date=D_("2026-07-01"), end_date=pd.NaT,
             balance=5.0, status="ACTIVE"),
        dict(customer_id="C002", product="EV_FINANCE", start_date=D_("2026-09-01"), end_date=pd.NaT,
             balance=5.0, status="ACTIVE"),
        dict(customer_id="C003", product="MORTGAGE", start_date=D_("2026-07-03"), end_date=pd.NaT,
             balance=5.0, status="INVALID"),
    ]).astype({"start_date": "datetime64[ns]", "end_date": "datetime64[ns]"})
    tb["financial_products"] = pd.concat([fp, new_products], ignore_index=True)

    en = [dict(customer_id="C001", month=D_("2026-07-01"), electricity_kwh=9999.0, gas_kwh=9999.0,
               source_quality="SMART_METER"),
          dict(customer_id="C002", month=D_("2026-07-01"), electricity_kwh=100.0, gas_kwh=100.0,
               source_quality="SMART_METER")]
    tb["energy_usage"] = pd.concat([tb["energy_usage"], pd.DataFrame(en).astype({"month": "datetime64[ns]"})],
                                   ignore_index=True)
    dg = [dict(customer_id="C001", month=D_("2026-07-01"), digital_statements=False, paper_statements=50,
               digital_transactions=0, app_logins=0, branch_visits=9),
          dict(customer_id="C002", month=D_("2026-07-01"), digital_statements=True, paper_statements=0,
               digital_transactions=3, app_logins=3, branch_visits=0)]
    tb["digital_usage"] = pd.concat([tb["digital_usage"], pd.DataFrame(dg).astype({"month": "datetime64[ns]"})],
                                    ignore_index=True)

    cust = tb["customers"]
    late = pd.DataFrame([dict(
        customer_id="C006", customer_since=D_("2026-07-10"), age_band="25-34", income_band="<25k",
        region="London", postcode_sector=None, segment="MASS", home_owner=True, property_type="FLAT",
        heating_type="GAS_BOILER", has_solar_pv=False, solar_installed_at=pd.NaT,
        sustainability_preference=3, record_updated_at=D_("2026-07-10"))]).astype(
        {"customer_since": "datetime64[ns]", "solar_installed_at": "datetime64[ns]",
         "record_updated_at": "datetime64[ns]"})
    tb["customers"] = pd.concat([cust, late], ignore_index=True)
    # customer-level solar installed after the cutoff must not change the 2026-06-30 view
    tb = copy.copy(tb)
    return tb, tx
