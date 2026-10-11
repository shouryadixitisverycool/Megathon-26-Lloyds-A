"""Snapshot provider: contract validity, NaN -> None mapping, port conformance, persistence."""

from datetime import date

import pytest
from .fixtures_c360 import CUTOFF, make_tables

from greenr import config
from greenr.contracts import CustomerSnapshot, FuelType, HeatingType
from greenr.pipelines import feature_registry as fr
from greenr.pipelines.customer360 import build_customer360
from greenr.pipelines.snapshot_provider import Customer360SnapshotProvider, row_to_snapshot
from greenr.ports import CustomerSnapshotProvider


@pytest.fixture(scope="module")
def frames():
    tables, txns = make_tables()
    return {c: build_customer360(tables, txns, c) for c in (date(2026, 3, 31), CUTOFF)}


@pytest.fixture(scope="module")
def provider(frames):
    return Customer360SnapshotProvider(frames)


def test_implements_port(provider):
    assert isinstance(provider, CustomerSnapshotProvider)
    assert provider.list_customer_ids() == ["C001", "C002", "C003", "C005"]


def test_every_customer_validates_against_contract(provider, frames):
    snaps = provider.snapshots()
    assert [s.customer_id for s in snaps] == list(frames[CUTOFF].index)
    for s in snaps:
        # round trip through the strict (extra=forbid) contract
        assert CustomerSnapshot.model_validate(s.model_dump(mode="json")) == s
        assert s.feature_cutoff == CUTOFF
        assert s.generated_at == config.PREDICTION_TIMESTAMP
        assert s.feature_version == config.FEATURE_VERSION
        assert set(s.features) == set(fr.PROPENSITY_FEATURES) | set(fr.POPULATION_FLAGS)
        assert not set(fr.AUDIT_ONLY_COLUMNS) & set(s.features)
        assert all(v is None or type(v) is float for v in s.features.values())


def test_rich_customer_mapping(provider):
    s = provider.get_snapshot("C001")
    assert s.segment == "AFFLUENT"
    assert s.vehicle.fuel_type is FuelType.PETROL and s.vehicle.has_vehicle is True
    assert s.vehicle.annual_mileage_km == 12000 and s.vehicle.mileage_is_estimated is False
    assert s.vehicle.record_updated_at == date(2026, 3, 1)
    assert s.vehicle.has_vehicle_finance is True
    assert s.home.home_owner is True and s.home.has_mortgage is True
    assert s.home.mortgage_tenure_months == 24 and isinstance(s.home.mortgage_tenure_months, int)
    assert s.home.heating_type is HeatingType.GAS_BOILER and s.home.region == "London"
    assert s.energy.energy_months_present == 12 and s.energy.electricity_kwh_12m == pytest.approx(3900)
    assert s.digital.is_paperless is True and s.digital.paper_statements_12m == 18
    assert s.digital.digital_statement_ratio == pytest.approx(0.25)
    assert s.spend.fuel_spend_90d_monthly_avg == 60.0 and s.spend.fuel_txn_frequency_90d == 4
    assert s.spend.home_improvement_spend_12m == 0.0
    # (30 + 0 + 0) / (200/12 + 0 + 0) - 1
    assert s.spend.utility_spend_trend == pytest.approx(30 / (200 / 12) - 1)
    dq = s.data_quality
    assert dq.transaction_months_observed == 13 and dq.vehicle_record_age_days == 121
    assert dq.first_transaction_date == date(2025, 6, 30) and dq.last_transaction_date == date(2026, 6, 20)
    assert dq.missing_fields == [] and dq.invalid_product_records == 0
    assert s.features["fuel_spend_30d"] == 80.0 and s.features["is_ice"] == 1.0
    assert s.features["gas_days_since_last"] is None


def test_sparse_customer_nan_becomes_none(provider):
    s = provider.get_snapshot("C002")
    assert s.vehicle.has_vehicle is None and s.vehicle.fuel_type is None
    assert s.vehicle.mileage_is_estimated is False
    assert s.home.home_owner is None and s.home.region is None and s.home.mortgage_tenure_months is None
    assert s.energy.electricity_kwh_12m is None and s.energy.energy_months_present == 0
    assert s.digital.is_paperless is None and s.digital.paper_statements_12m is None
    assert s.spend.fuel_spend_90d_monthly_avg is None and s.spend.utility_spend_trend is None
    assert s.data_quality.transaction_months_observed == 0
    assert s.data_quality.first_transaction_date is None
    assert "vehicle" in s.data_quality.missing_fields
    assert s.features["fuel_spend_30d"] is None and s.features["has_mortgage"] == 0.0
    assert s.features["holds_ev_finance"] == 0.0


def test_estimated_and_invalid(provider):
    s = provider.get_snapshot("C003")
    assert s.vehicle.mileage_is_estimated is True and s.vehicle.fuel_type is FuelType.EV
    assert s.data_quality.estimated_fields == ["annual_mileage_km"]
    assert s.data_quality.invalid_product_records == 1
    assert s.features["holds_ev_finance"] == 1.0
    assert s.energy.gas_kwh_12m is None and s.energy.energy_months_present == 2


def test_get_snapshot_cutoffs_and_unknown(provider):
    assert provider.get_snapshot("NOPE") is None
    assert provider.get_snapshot("C002", date(2026, 3, 31)) is None   # not yet a customer
    early = provider.get_snapshot("C005", date(2026, 3, 31))
    assert early.feature_cutoff == date(2026, 3, 31) and early.vehicle.fuel_type is FuelType.PETROL
    with pytest.raises(KeyError):
        provider.get_snapshot("C001", date(2020, 1, 1))


def test_row_to_snapshot_matches_provider(frames, provider):
    row = frames[CUTOFF].loc["C003"]
    assert row_to_snapshot(row, CUTOFF) == provider.get_snapshot("C003")


def test_parquet_round_trip(frames, provider, tmp_path):
    paths = provider.save(tmp_path)
    assert {p.name for p in paths} == {"customer360_2026-03-31.parquet", "customer360_2026-06-30.parquet"}
    again = Customer360SnapshotProvider.from_parquet(*paths)
    assert again.list_customer_ids() == provider.list_customer_ids()
    for cid in provider.list_customer_ids():
        assert again.get_snapshot(cid) == provider.get_snapshot(cid)


def test_default_cutoff_must_exist(frames):
    with pytest.raises(ValueError):
        Customer360SnapshotProvider({date(2026, 3, 31): frames[date(2026, 3, 31)]})
