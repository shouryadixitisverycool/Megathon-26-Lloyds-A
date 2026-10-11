"""Customer 360: point-in-time correctness, window arithmetic, NaN/0 semantics, as-of logic."""

from datetime import date

import numpy as np
import pandas as pd
import pytest
from .fixtures_c360 import CUTOFF, add_post_cutoff_events, make_tables
from pandas.testing import assert_frame_equal

from greenr.pipelines import feature_registry as fr
from greenr.pipelines.customer360 import build_customer360, build_customer360_many

LIST_COLS = ["missing_fields", "estimated_fields"]


@pytest.fixture(scope="module")
def raw():
    return make_tables()


@pytest.fixture(scope="module")
def c360(raw):
    tables, txns = raw
    return build_customer360(tables, txns, CUTOFF)


def _assert_same(a: pd.DataFrame, b: pd.DataFrame) -> None:
    assert_frame_equal(a.drop(columns=LIST_COLS), b.drop(columns=LIST_COLS))
    for col in LIST_COLS:
        assert a[col].tolist() == b[col].tolist()


# --- shape / schema ---------------------------------------------------------------------------

def test_population_and_columns(c360):
    assert list(c360.index) == ["C001", "C002", "C003", "C005"]  # C004 joins after the cutoff
    assert c360.index.name == "customer_id"
    assert list(c360.columns) == [*fr.PROPENSITY_FEATURES, *fr.POPULATION_FLAGS, *fr.CONTEXT_COLUMNS]
    for col in [*fr.PROPENSITY_FEATURES, *fr.POPULATION_FLAGS]:
        assert c360[col].dtype == np.float64, col


def test_audit_only_columns_absent(c360):
    assert not set(fr.AUDIT_ONLY_COLUMNS) & set(c360.columns)
    assert not set(fr.AUDIT_ONLY_COLUMNS) & set(fr.PROPENSITY_FEATURES)
    assert not set(fr.PROXY_FEATURES) & set(fr.PROPENSITY_FEATURES)


def test_truth_tables_are_rejected(raw):
    tables, txns = raw
    with pytest.raises(ValueError, match="truth"):
        build_customer360({**tables, "customer_outcomes": pd.DataFrame()}, txns, CUTOFF)


@pytest.mark.parametrize("updated", ["2026-07-01", None])
def test_unavailable_profile_does_not_reach_historical_features(raw, updated):
    tables, txns = raw
    changed = {name: frame.copy() for name, frame in tables.items()}
    changed["customers"].loc[changed["customers"].customer_id == "C001", "record_updated_at"] = (
        pd.Timestamp(updated) if updated else pd.NaT)
    snapshot = build_customer360(changed, txns, CUTOFF).loc["C001"]
    for field in ("home_owner", "has_existing_solar", "heating_is_gas", "heating_is_electric",
                  "property_is_house", "sustainability_preference", "region", "segment"):
        assert pd.isna(snapshot[field]), field
    # Dated product, transaction and relationship records remain usable.
    assert snapshot.has_mortgage == 1
    assert snapshot.fuel_spend_90d_avg == 60
    assert snapshot.tenure_months == 29
    assert "home_owner" in snapshot.missing_fields


def test_unknown_category_rejected(raw):
    tables, txns = raw
    bad = txns.copy()
    bad.loc[bad.index[0], "category"] = "NOT_A_CATEGORY"
    with pytest.raises(ValueError, match="categories"):
        build_customer360(tables, bad, CUTOFF)


@pytest.mark.parametrize("name", ["financial_products", "vehicles", "energy_usage", "digital_usage", "transactions"])
def test_delayed_records_excluded_even_when_event_before_cutoff(raw, name):
    tables, txns = raw
    changed = {key: value.copy() for key, value in tables.items()}
    txns = txns.copy()
    source = txns if name == "transactions" else changed[name]
    source["available_at"] = pd.Timestamp(CUTOFF) + pd.Timedelta(days=1)
    delayed = build_customer360(changed, txns, CUTOFF)
    if name == "transactions":
        expected = build_customer360(changed, txns.iloc[:0], CUTOFF)
    else:
        changed[name] = changed[name].iloc[:0]
        expected = build_customer360(changed, txns, CUTOFF)
    _assert_same(delayed, expected)


def test_delayed_profile_is_masked(raw):
    tables, txns = raw
    changed = {key: value.copy() for key, value in tables.items()}
    changed["customers"]["available_at"] = pd.Timestamp(CUTOFF) + pd.Timedelta(days=1)
    row = build_customer360(changed, txns, CUTOFF).loc["C001"]
    assert pd.isna(row.home_owner)
    assert row.tenure_months == 29


# --- window arithmetic (hand computed, see fixtures_c360) -------------------------------------

def test_fuel_windows_hand_computed(c360):
    r = c360.loc["C001"]
    assert r["fuel_spend_30d"] == 80.0            # 50 + 30 (credit and 05-31 excluded)
    assert r["fuel_spend_90d_avg"] == 60.0        # (50+30+40+60)/3
    assert r["fuel_spend_12m_avg"] == 25.0        # (180+100+20)/12
    assert r["fuel_spend_trend"] == pytest.approx(1.4)
    assert r["fuel_txn_freq_90d"] == 4
    assert r["fuel_spend_share_12m"] == pytest.approx(300 / 700)
    assert r["fuel_days_since_last"] == 15


def test_window_boundaries(c360):
    # 2025-06-30 (ago 365) and 2026-04-01 (ago 90) are outside 12m / 90d respectively
    r = c360.loc["C001"]
    assert r["fuel_spend_12m_avg"] * 12 == 300.0
    assert r["fuel_spend_90d_avg"] * 3 == 180.0
    # transaction on the cutoff date itself counts (ago 0)
    assert c360.loc["C005", "gas_spend_30d"] == 40.0
    assert c360.loc["C005", "gas_days_since_last"] == 0


def test_totals_and_history(c360):
    r = c360.loc["C001"]
    assert r["total_spend_12m_avg"] == pytest.approx(700 / 12)
    assert r["txn_count_12m"] == 10                # 9 debits-credits inside 365d + the credit
    assert r["txn_months_observed"] == 13          # Jun-2025 .. Jun-2026 inclusive
    assert r["first_txn_date"] == pd.Timestamp("2025-06-30")
    assert r["last_txn_date"] == pd.Timestamp("2026-06-20")
    assert r["electricity_spend_trend"] == pytest.approx(30 / (200 / 12) - 1)


def test_debits_only(c360):
    # a 999 credit on C001 never shows in spend; C003 has only a credit in FUEL
    assert c360.loc["C003", "fuel_spend_12m_avg"] == 0.0


def test_tenure_and_mortgage_months(c360):
    assert c360.loc["C001", "tenure_months"] == 29   # 2024-01-15 -> 2026-06-30
    assert c360.loc["C001", "mortgage_tenure_months"] == 24  # 2024-06-10 -> 2026-06-30


def test_energy_hand_computed(c360):
    r = c360.loc["C001"]
    assert r["energy_months_present"] == 12
    assert r["electricity_kwh_12m"] == pytest.approx(3900.0)   # mean(9x300, 3x400) x 12
    assert r["gas_kwh_12m"] == pytest.approx(6000.0)
    assert r["electricity_trend"] == pytest.approx(400 / 325 - 1)


def test_digital_hand_computed(c360):
    r = c360.loc["C001"]
    assert r["is_paperless"] == 1.0
    assert r["paper_statements_3m"] == 0
    assert r["paper_statements_12m"] == 18
    assert r["digital_statement_ratio"] == pytest.approx(0.25)
    assert r["digital_txn_3m_avg"] == 20
    assert r["app_logins_3m_avg"] == 30
    assert r["app_logins_trend"] == pytest.approx(1.0)   # 30 / mean(9x10, 3x30)=15 - 1
    assert r["branch_visits_3m"] == 3
    assert r["digital_months_present"] == 12


def test_vehicle_hand_computed(c360):
    r = c360.loc["C001"]
    assert (r["has_vehicle"], r["is_ice"], r["is_ev"], r["is_hybrid"]) == (1, 1, 0, 0)
    assert r["vehicle_record_age_days"] == 121
    assert r["vehicle_age_years"] == pytest.approx(5.0 + 121 / 365.25)
    assert r["annual_mileage_km"] == 12000
    assert r["mileage_is_estimated"] == 0
    assert r["has_vehicle_finance"] == 1
    assert r["fuel_type"] == "PETROL"


# --- NaN vs 0 semantics -----------------------------------------------------------------------

def test_no_history_is_nan_not_zero(c360):
    r = c360.loc["C002"]
    for cat in fr.SPEND_CATEGORIES:
        for suffix in ("spend_30d", "spend_90d_avg", "spend_12m_avg", "spend_trend", "txn_freq_90d",
                       "spend_share_12m", "days_since_last"):
            assert np.isnan(r[f"{cat}_{suffix}"]), f"{cat}_{suffix}"
    assert np.isnan(r["total_spend_12m_avg"])
    assert r["txn_months_observed"] == 0 and r["txn_count_12m"] == 0
    assert pd.isna(r["first_txn_date"]) and pd.isna(r["last_txn_date"])
    for col in ("home_owner", "has_vehicle", "is_ice", "annual_mileage_km", "electricity_kwh_12m",
                "is_paperless", "paper_statements_12m", "digital_statement_ratio",
                "sustainability_preference", "has_existing_solar", "heating_is_gas", "property_is_house"):
        assert np.isnan(r[col]), col
    assert r["energy_months_present"] == 0 and r["digital_months_present"] == 0


def test_history_without_category_spend_is_zero(c360):
    r = c360.loc["C003"]   # one OTHER debit (20) and a FUEL credit
    assert r["fuel_spend_30d"] == 0 and r["fuel_spend_90d_avg"] == 0 and r["fuel_txn_freq_90d"] == 0
    assert r["fuel_spend_share_12m"] == 0
    assert np.isnan(r["fuel_spend_trend"])          # 12m average is 0
    assert np.isnan(r["fuel_days_since_last"])      # never seen
    assert r["total_spend_12m_avg"] == pytest.approx(20 / 12)


def test_products_are_zero_when_absent(c360):
    r = c360.loc["C002"]
    assert r["has_mortgage"] == 0 and r["has_investments"] == 0 and r["holds_ev_finance"] == 0
    assert np.isnan(r["mortgage_tenure_months"])


def test_missing_and_estimated_fields(c360):
    assert c360.loc["C001", "missing_fields"] == []
    assert c360.loc["C002", "missing_fields"] == [
        "home_owner", "region", "sustainability_preference", "heating_type", "property_type",
        "has_existing_solar", "vehicle", "energy", "digital", "transactions"]
    assert c360.loc["C003", "estimated_fields"] == ["annual_mileage_km"]
    assert c360.loc["C005", "missing_fields"] == ["annual_mileage_km", "energy", "digital"]
    assert c360.loc["C001", "estimated_fields"] == []


# --- as-of logic ------------------------------------------------------------------------------

def test_products_as_of_cutoff_ignoring_invalid(c360):
    assert c360.loc["C003", "holds_ev_finance"] == 1
    assert c360.loc["C003", "has_investments"] == 0           # INVALID row never counts
    assert c360.loc["C003", "invalid_product_records"] == 1
    assert c360.loc["C005", "has_mortgage"] == 0               # closed 2026-01-01
    assert c360.loc["C005", "holds_solar_finance"] == 0        # starts after the cutoff
    assert c360.loc["C001", "has_mortgage"] == 1


def test_mortgage_active_at_earlier_cutoff(raw):
    tables, txns = raw
    early = build_customer360(tables, txns, date(2025, 12, 31))
    assert early.loc["C005", "has_mortgage"] == 1             # open until 2026-01-01
    assert early.loc["C005", "mortgage_tenure_months"] == 17  # 2024-07-01 -> 2025-12-31
    assert "C003" in early.index and "C002" not in early.index


def test_solar_as_of(c360, raw):
    assert c360.loc["C003", "has_existing_solar"] == 1   # installed 2026-02-01
    assert c360.loc["C005", "has_existing_solar"] == 0   # installed 2026-09-01 (after cutoff)
    assert c360.loc["C001", "has_existing_solar"] == 0
    tables, txns = raw
    # The current profile was recorded after this historical cutoff. Neither its
    # solar flag nor its installation date was available to the prediction.
    assert np.isnan(build_customer360(tables, txns, date(2026, 1, 31)).loc["C003", "has_existing_solar"])


def test_vehicle_latest_as_of_cutoff(raw):
    tables, txns = raw
    now = build_customer360(tables, txns, CUTOFF)
    assert now.loc["C005", "fuel_type"] == "HYBRID" and now.loc["C005", "is_hybrid"] == 1
    assert np.isnan(now.loc["C005", "annual_mileage_km"])
    before = build_customer360(tables, txns, date(2026, 3, 31))
    assert before.loc["C005", "fuel_type"] == "PETROL" and before.loc["C005", "is_ice"] == 1
    assert before.loc["C005", "annual_mileage_km"] == 15000
    assert before.loc["C005", "vehicle_record_age_days"] == 445   # 2025-01-10 -> 2026-03-31


def test_paperless_from_latest_month_at_or_before_cutoff(raw):
    tables, txns = raw
    assert build_customer360(tables, txns, CUTOFF).loc["C001", "is_paperless"] == 1
    assert build_customer360(tables, txns, date(2026, 3, 31)).loc["C001", "is_paperless"] == 0
    # June is not yet complete on 2026-06-29: latest complete month is May (still paperless)
    mid = build_customer360(tables, txns, date(2026, 6, 29))
    assert mid.loc["C001", "is_paperless"] == 1
    assert mid.loc["C001", "digital_months_present"] == 12


def test_incomplete_month_not_used(raw):
    tables, txns = raw
    t = {k: v.copy() for k, v in tables.items()}
    en = t["energy_usage"]
    june = (en["customer_id"] == "C001") & (en["month"] == pd.Timestamp("2026-06-01"))
    assert june.sum() == 1
    base29 = build_customer360(t, txns, date(2026, 6, 29))
    t["energy_usage"].loc[june, "electricity_kwh"] = 1e6
    assert_frame_equal(base29[["electricity_kwh_12m", "electricity_trend"]],
                       build_customer360(t, txns, date(2026, 6, 29))[["electricity_kwh_12m", "electricity_trend"]])
    assert build_customer360(t, txns, CUTOFF).loc["C001", "electricity_kwh_12m"] > 1e5  # month ended


# --- point-in-time: post-cutoff events must not change anything -------------------------------

def test_post_cutoff_events_do_not_change_features(raw, c360):
    tables, txns = raw
    tables2, txns2 = add_post_cutoff_events(tables, txns)
    after = build_customer360(tables2, txns2, CUTOFF)
    _assert_same(c360, after)


@pytest.mark.parametrize("table", ["vehicles", "financial_products", "energy_usage", "digital_usage"])
def test_each_table_post_cutoff_isolated(raw, c360, table):
    tables, txns = raw
    tables2, txns2 = add_post_cutoff_events(tables, txns)
    mixed = {**tables, table: tables2[table]}
    _assert_same(c360, build_customer360(mixed, txns, CUTOFF))


def test_post_cutoff_transactions_isolated(raw, c360):
    tables, txns = raw
    _, txns2 = add_post_cutoff_events(tables, txns)
    _assert_same(c360, build_customer360(tables, txns2, CUTOFF))


def test_post_cutoff_events_do_change_later_cutoff(raw):
    tables, txns = raw
    tables2, txns2 = add_post_cutoff_events(tables, txns)
    later = build_customer360(tables2, txns2, date(2026, 9, 30))
    assert later.loc["C001", "is_ev"] == 1 and later.loc["C001", "has_investments"] == 1
    assert "C006" in later.index
    assert later.loc["C002", "txn_months_observed"] == 3


def test_build_many_matches_single(raw):
    tables, txns = raw
    cutoffs = [date(2026, 3, 31), CUTOFF]
    many = build_customer360_many(tables, txns, cutoffs)
    assert list(many) == cutoffs
    _assert_same(many[CUTOFF], build_customer360(tables, txns, CUTOFF))


def test_feature_registry_consistency():
    assert set(fr.PROPENSITY_FEATURES) | set(fr.POPULATION_FLAGS) | set(fr.CONTEXT_COLUMNS) <= set(fr.FEATURE_REGISTRY)
    assert not set(fr.POPULATION_FLAGS) & set(fr.PROPENSITY_FEATURES)
    assert all(fr.FEATURE_REGISTRY[f].allowed_in_propensity for f in fr.PROPENSITY_FEATURES)
    assert not any(fr.FEATURE_REGISTRY[f].allowed_in_propensity
                   for f in [*fr.POPULATION_FLAGS, *fr.CONTEXT_COLUMNS, *fr.AUDIT_ONLY_COLUMNS])
    assert all(s.available_at_prediction for s in fr.FEATURE_REGISTRY.values())
    reg = fr.registry_frame()
    assert set(reg["name"]) == set(fr.FEATURE_REGISTRY)
    assert reg.loc[reg["name"] == "income_band", "proxy_risk"].item()
    assert fr.FEATURE_VERSION == "feature_v1"
