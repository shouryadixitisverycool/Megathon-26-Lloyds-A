from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from greenpath.data_generation.config import BASE_CONFIG, PRODUCTS
from greenpath.data_generation.generator import (
    NONE_DAY, TimeGrid, _customers, _day, _digital_usage, _population,
    _to_dt, _transactions, _vehicles, generate, write_dataset,
)
from greenpath.data_generation.merchants import build_catalogue
from greenpath.data_generation.personas import build_personas
from greenpath.data_generation.source_history import customer_history, vehicle_ownership


def setup_population(n=1000):
    cfg = replace(BASE_CONFIG, n_customers=n, include_personas=False)
    tg = TimeGrid(cfg)
    p = _population(cfg, np.random.default_rng(1), tg)
    adopt = {product: np.full(n, NONE_DAY) for product in PRODUCTS}
    return cfg, tg, p, adopt


@pytest.mark.parametrize("product", ["EV_FINANCE", "SOLAR_FINANCE"])
@pytest.mark.parametrize("future_day", ["2025-05-15", "2026-05-15", "2026-08-15"])
def test_future_adoption_cannot_change_earlier_transactions(product, future_day):
    cfg, tg, p, adopt = setup_population(40)
    cat = build_catalogue(cfg.seed, 4, 1.0)
    conflict = np.zeros(cfg.n_customers, dtype=int)
    before = _transactions(cfg, p, adopt, np.random.default_rng(2), tg, cat, conflict)
    adopt[product][:] = _day(future_day)
    after = _transactions(cfg, p, adopt, np.random.default_rng(2), tg, cat, conflict)
    # Compare source values, not transaction IDs allocated after the full stream is sorted.
    for key in before:
        np.testing.assert_array_equal(before[key][before["day"] < _day(future_day)],
                                      after[key][after["day"] < _day(future_day)])


def test_vehicle_baseline_and_renewals_are_conditioned_on_adoption():
    cfg, tg, p, adopt = setup_population(3000)
    p["has_car"][:] = True
    p["fuel"][:] = 0
    adopt["EV_FINANCE"][:] = _day("2025-01-01")
    vehicles = _vehicles(cfg, p, adopt, np.random.default_rng(3), tg, np.zeros(cfg.n_customers, dtype=int))
    later = vehicles[vehicles["record_updated_at"] >= pd.Timestamp("2025-01-01")]
    assert len(later) > cfg.n_customers  # includes later baseline records, not just adoption rows
    assert later["fuel_type"].eq("EV").all()
    stale = _vehicles(cfg, p, adopt, np.random.default_rng(3), tg, np.ones(cfg.n_customers, dtype=int))
    assert stale["fuel_type"].eq("PETROL").all()


def test_initial_profiles_preserve_unknowns_and_preexisting_solar():
    cfg, tg, p, adopt = setup_population()
    baseline = _customers(cfg, p, adopt, np.random.default_rng(4), tg)
    adopt["SOLAR_FINANCE"][~p["solar_pre"]] = _day("2026-08-15")
    current, history = customer_history(baseline, _to_dt(adopt["SOLAR_FINANCE"]), pd.Timestamp(cfg.history_start))
    initial = history.drop_duplicates("customer_id", keep="first").reset_index(drop=True)
    for col in baseline.columns.drop("record_updated_at"):
        pd.testing.assert_series_equal(initial[col], baseline[col], check_dtype=False)
    assert initial.loc[p["solar_pre"], "has_solar_pv"].all()
    assert initial["home_owner"].isna().any()
    assert initial["has_solar_pv"].isna().any()
    assert initial["record_updated_at"].le(pd.Timestamp(cfg.calibration_cutoff)).all()
    assert current["has_solar_pv"].all()
    assert not history.duplicated(["customer_id", "record_updated_at"]).any()


def test_vehicle_declarations_distinguish_nonowners_missing_records_and_unknowns():
    cfg, tg, p, adopt = setup_population()
    declarations = vehicle_ownership(p, _to_dt(adopt["EV_FINANCE"]), np.random.default_rng(5),
                                     pd.Timestamp(cfg.history_start), 0.03)
    known = declarations["has_vehicle"].notna().to_numpy()
    np.testing.assert_array_equal(declarations.loc[known, "has_vehicle"].to_numpy(dtype=bool), p["has_car"][known])
    assert declarations["has_vehicle"].isna().any()
    assert declarations["has_vehicle"].eq(False).any()


def test_paperless_has_exact_effective_date_and_personas_have_initial_history():
    cfg, tg, p, adopt = setup_population(10)
    p["paperless_pre"][:] = False
    adopt["PAPERLESS_BANKING"][:] = _day("2026-05-14")
    digital = _digital_usage(cfg, p, adopt, np.random.default_rng(6), tg)
    assert digital.loc[digital["digital_statements"], "paperless_effective_at"].eq(pd.Timestamp("2026-05-14")).all()
    assert digital.loc[~digital["digital_statements"], "paperless_effective_at"].isna().all()
    cat = build_catalogue(cfg.seed, 4, 1.0)
    personas = build_personas(cat, np.random.default_rng(7), tg)
    initial = personas["customer_history"].drop_duplicates("customer_id").set_index("customer_id")
    assert initial.loc["C10006", "has_solar_pv"] == True
    assert pd.isna(initial.loc["C10005", "home_owner"])
    ownership = personas["vehicle_ownership"].set_index("customer_id")
    assert ownership.loc["C10003", "has_vehicle"] == False
    assert pd.isna(ownership.loc["C10005", "has_vehicle"])


def test_generated_history_round_trips_with_current_profiles(tmp_path):
    cfg = replace(BASE_CONFIG, n_customers=100)
    tables = generate(cfg)
    history = tables["customer_history"]
    latest = history.sort_values(["customer_id", "record_updated_at"], kind="stable").drop_duplicates(
        "customer_id", keep="last"
    ).sort_values("customer_id", ignore_index=True)
    pd.testing.assert_frame_equal(tables["customers"], latest)
    assert len(history.drop_duplicates("customer_id")) == 110
    assert (history["available_at"] >= history["record_updated_at"]).all()
    metadata = write_dataset(tables, tmp_path, cfg)
    assert metadata["row_counts"]["customer_history"] == len(history)
    pd.testing.assert_frame_equal(pd.read_parquet(tmp_path / "customer_history.parquet"), history)
