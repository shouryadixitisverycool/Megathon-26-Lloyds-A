from datetime import date

import pandas as pd
import pytest

from greenr.contracts import Product, ReasonCode
from greenr.models.propensity.reason_codes import REASON_CODE_CATALOGUE
from greenr.pipelines.customer360 import build_customer360
from greenr.pipelines.feature_registry import CONTEXT_COLUMNS, FEATURE_REGISTRY
from greenr.pipelines.snapshot_provider import row_to_snapshot
from greenr.trust.conflicts import detect_conflicts
from .fixtures_c360 import CUTOFF, make_tables


@pytest.mark.parametrize("delayed", [False, True])
def test_history_retains_prior_profile(delayed):
    tables, txns = make_tables()
    old = tables["customers"].copy()
    new = old.copy()
    new["record_updated_at"] = pd.Timestamp("2026-06-20" if delayed else "2026-07-01")
    new["available_at"] = pd.Timestamp("2026-07-01")
    new["home_owner"] = False
    tables["customers"] = new
    tables["customer_history"] = pd.concat([old, new], ignore_index=True)
    row = build_customer360(tables, txns, CUTOFF).loc["C001"]
    assert row.home_owner == 1
    assert row.region == "London"


@pytest.mark.parametrize("ownership", [False, True, None])
def test_optional_ownership_as_of(ownership):
    tables, txns = make_tables()
    tables["vehicle_ownership"] = pd.DataFrame([
        dict(customer_id="C002", has_vehicle=ownership, record_updated_at=pd.Timestamp("2026-06-01"),
             available_at=pd.Timestamp("2026-06-01")),
        dict(customer_id="C002", has_vehicle=True, record_updated_at=pd.Timestamp("2026-07-01"),
             available_at=pd.Timestamp("2026-07-01")),
    ])
    snap = row_to_snapshot(build_customer360(tables, txns, CUTOFF).loc["C002"], CUTOFF)
    assert snap.vehicle.has_vehicle is ownership
    assert snap.vehicle.fuel_type is None


@pytest.mark.parametrize("mode", ["clean", "continuing", "missing", "delayed"])
def test_ev_transition_uses_only_post_state_rows(mode):
    tables, txns = make_tables()
    prior_fuel = txns.customer_id.eq("C001") & txns.category.eq("FUEL") & txns.debit_credit.eq("DEBIT")
    txns.loc[prior_fuel, "amount"] *= 10
    ev = tables["vehicles"].loc[tables["vehicles"].customer_id == "C001"].copy()
    ev["fuel_type"] = "EV"
    ev["record_updated_at"] = pd.Timestamp("2026-06-16")
    ev["available_at"] = ev["record_updated_at"]
    refresh = ev.copy()
    refresh["record_updated_at"] = pd.Timestamp("2026-06-25")
    refresh["available_at"] = refresh["record_updated_at"]
    tables["vehicles"] = pd.concat([tables["vehicles"], ev, refresh], ignore_index=True)
    if mode in ("continuing", "delayed"):
        extra = txns.iloc[:3].copy()
        extra["customer_id"] = "C001"
        extra["date"] = pd.to_datetime(["2026-06-17", "2026-06-18", "2026-06-19"])
        extra["amount"] = 100.0
        extra["available_at"] = pd.Timestamp("2026-07-01") if mode == "delayed" else extra["date"]
        txns = pd.concat([txns, extra], ignore_index=True)
    if mode == "missing":
        txns = txns.loc[txns.date < pd.Timestamp("2026-06-16")]
    snap = row_to_snapshot(build_customer360(tables, txns, CUTOFF).loc["C001"], CUTOFF)
    assert snap.vehicle.state_effective_at == date(2026, 6, 16)
    assert snap.features["fuel_spend_90d_avg"] > 60
    count = snap.spend.fuel_txn_count_post_vehicle_state_90d
    assert count == (3 if mode == "continuing" else None if mode == "missing" else 0)
    assert bool(detect_conflicts(snap, Product.EV_FINANCE)) == (mode == "continuing")
    assert "fuel_txn_count_post_vehicle_state_90d" not in snap.features


@pytest.mark.parametrize("mode", ["clean", "continuing", "missing", "gap"])
def test_paperless_transition_uses_current_contiguous_run(mode):
    tables, txns = make_tables()
    d = tables["digital_usage"]
    customer = d.customer_id.eq("C001")
    d.loc[customer & d.month.lt(pd.Timestamp("2026-06-01")), "digital_statements"] = False
    d.loc[customer & d.month.lt(pd.Timestamp("2026-06-01")), "paper_statements"] = 2
    june = customer & d.month.eq(pd.Timestamp("2026-06-01"))
    if mode == "continuing":
        d.loc[june, "paper_statements"] = 1
    elif mode == "missing":
        d.loc[june, "paper_statements"] = float("nan")
    elif mode == "gap":
        d.loc[customer, "digital_statements"] = True
        tables["digital_usage"] = d.loc[~(customer & d.month.eq(pd.Timestamp("2026-05-01")))]
    snap = row_to_snapshot(build_customer360(tables, txns, CUTOFF).loc["C001"], CUTOFF)
    assert snap.digital.paperless_effective_at == date(2026, 6, 1)
    assert snap.digital.paper_statements_post_paperless_3m == (
        1 if mode == "continuing" else None if mode == "missing" else 0)
    assert bool(detect_conflicts(snap, Product.PAPERLESS_BANKING)) == (mode == "continuing")


def test_per_fuel_observation_and_annualisation_metadata():
    tables, txns = make_tables()
    frame = build_customer360(tables, txns, CUTOFF)
    snap = row_to_snapshot(frame.loc["C003"], CUTOFF)
    assert snap.energy.electricity_months_present == 2
    assert snap.energy.electricity_kwh_observed == 500
    assert snap.energy.electricity_annualisation_factor == 6
    assert snap.energy.electricity_kwh_12m == 3000
    assert snap.energy.electricity_is_estimated is True
    assert snap.energy.gas_months_present == 0
    assert snap.energy.gas_kwh_observed is None
    assert snap.energy.gas_annualisation_factor is None
    assert snap.energy.gas_is_estimated is None
    full = row_to_snapshot(frame.loc["C001"], CUTOFF)
    assert full.energy.electricity_annualisation_factor == 1
    assert full.energy.electricity_is_estimated is False
    assert all(not FEATURE_REGISTRY[c].allowed_in_propensity for c in CONTEXT_COLUMNS)
    for code in (ReasonCode.HIGH_ELECTRICITY_USE, ReasonCode.HIGH_GAS_USE):
        assert "Estimated annual" in REASON_CODE_CATALOGUE[code].rm_wording


def test_missing_history_does_not_fall_back_to_future_profile():
    tables, txns = make_tables()
    tables["customer_history"] = tables["customers"].copy()
    tables["customer_history"]["available_at"] = pd.Timestamp("2026-07-01")
    row = build_customer360(tables, txns, CUTOFF).loc["C001"]
    assert pd.isna(row.home_owner)
    assert row.tenure_months == 29


def test_delayed_ownership_retains_prior_negative():
    tables, txns = make_tables()
    tables["vehicle_ownership"] = pd.DataFrame([
        dict(customer_id="C002", has_vehicle=False, record_updated_at=pd.Timestamp("2026-05-01"),
             available_at=pd.Timestamp("2026-05-01")),
        dict(customer_id="C002", has_vehicle=True, record_updated_at=pd.Timestamp("2026-06-01"),
             available_at=pd.Timestamp("2026-07-01")),
    ])
    assert build_customer360(tables, txns, CUTOFF).loc["C002", "has_vehicle"] == 0


def test_unknown_digital_flag_breaks_paperless_run():
    tables, txns = make_tables()
    d = tables["digital_usage"]
    d["digital_statements"] = d["digital_statements"].astype("boolean")
    d.loc[d.customer_id.eq("C001") & d.month.eq(pd.Timestamp("2026-05-01")), "digital_statements"] = pd.NA
    row = build_customer360(tables, txns, CUTOFF).loc["C001"]
    assert row.paperless_effective_at == pd.Timestamp("2026-06-01")


def test_explicit_paperless_effective_date_survives_arrow_input():
    tables, txns = make_tables()
    d = tables["digital_usage"]
    selected = d.customer_id.eq("C001")
    d.loc[selected, "digital_statements"] = True
    d.loc[selected, "paperless_effective_at"] = pd.Timestamp("2026-05-15")
    tables["digital_usage"] = d.convert_dtypes(dtype_backend="pyarrow")
    row = build_customer360(tables, txns, CUTOFF).loc["C001"]
    assert row.paperless_effective_at == pd.Timestamp("2026-05-15")
