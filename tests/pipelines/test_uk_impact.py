"""Independent physical arithmetic, missing evidence and boundary regressions."""

from decimal import Decimal
import hashlib
from pathlib import Path

import pytest
from pydantic import ValidationError

from greenpath.extensions.uk_impact import calculate, factor_catalogue


EV = {"annual_mileage_km": 10000.0, "fuel_type": "PETROL", "ice_litres_per_100km": 6.0,
      "ev_kwh_per_100km": 20.0, "charging_efficiency": 0.8, "mileage_evidence": "USER_SCENARIO"}


def test_uk_ev_matched_wtw_and_charging_losses():
    result = calculate("EV_FINANCE", EV)
    assert Decimal(result["baseline_emissions"]) == Decimal("600") * Decimal("2.65010")
    assert Decimal(result["scenario_emissions"]) == Decimal("2500") * Decimal("0.24540")
    assert result["units"] == "kg CO2e/year" and "well-to-wheel" in result["boundary"]
    assert len(result["factor_records"]) == 6


def test_negative_uk_reduction_is_preserved():
    result = calculate("EV_FINANCE", {**EV, "ev_kwh_per_100km": 100.0, "charging_efficiency": 0.5})
    assert Decimal(result["potential_reduction"]) < 0


def test_uk_passport_identity_reproduces_with_identical_inputs():
    assert calculate("EV_FINANCE", EV)["passport_id"] == calculate("EV_FINANCE", EV)["passport_id"]


@pytest.mark.parametrize("change", [{"charging_efficiency": 0.0}, {"annual_mileage_km": True},
                                    {"annual_mileage_km": float("nan")}, {"unexpected": 1}])
def test_uk_inputs_reject_invalid_or_unapproved_values(change):
    with pytest.raises(ValidationError):
        calculate("EV_FINANCE", {**EV, **change})


def test_uk_requires_forecast_efficiency_evidence():
    with pytest.raises(ValidationError):
        calculate("EV_FINANCE", {"annual_mileage_km": 10000.0, "fuel_type": "PETROL"})


def test_uk_solar_displaces_only_explicit_self_consumption():
    inputs = {"annual_electricity_kwh": 4000.0, "annual_generation_kwh": 3000.0,
              "self_consumption_fraction": 0.5, "region": "London", "proposed_capacity_kw": 3.0,
              "generation_evidence": "User installer generation scenario, unverified"}
    result = calculate("SOLAR_FINANCE", inputs)
    assert Decimal(result["potential_reduction"]) == Decimal("1500") * Decimal("0.24540")
    with pytest.raises(ValueError, match="exceed"):
        calculate("SOLAR_FINANCE", {**inputs, "annual_electricity_kwh": 100.0})


def test_uk_heat_pump_preserves_gross_gas_and_delivered_heat_units():
    result = calculate("GREEN_HOME", {"intervention": "HEAT_PUMP", "annual_heating_gas_kwh_gross": 10000.0,
                       "boiler_efficiency_gross": 0.9, "seasonal_performance_factor": 3.0,
                       "performance_evidence": "User seasonal performance scenario"})
    assert Decimal(result["baseline_emissions"]) == Decimal("10000") * Decimal("0.21317")
    assert Decimal(result["scenario_emissions"]) == Decimal("3000") * Decimal("0.24540")


def test_uk_insulation_has_separate_fuel_savings():
    result = calculate("GREEN_HOME", {"intervention": "INSULATION", "annual_electricity_kwh": 4000.0,
                       "annual_gas_kwh_gross": 10000.0, "electricity_saving_fraction": 0.1,
                       "gas_saving_fraction": 0.2, "savings_evidence": "User retrofit estimate"})
    assert Decimal(result["potential_reduction"]) == Decimal("400") * Decimal("0.24540") + Decimal("2000") * Decimal("0.21317")


def test_uk_paperless_never_claims_carbon():
    result = calculate("PAPERLESS_BANKING", {"annual_statements": 12, "sheets_per_statement": 2, "avoided_fraction": 0.5})
    assert result["status"] == "NOT_CLAIMED"
    assert Decimal(result["paper_sheets_avoided"]) == 12
    assert "potential_reduction" not in result


def test_downloaded_official_source_checksum_matches_catalogue():
    path = Path("data/factors/ghg-conversion-factors-2025-flat-format.xlsx")
    if not path.exists():
        pytest.skip("Original optional source download is not included in this checkout")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == factor_catalogue()["source_sha256"]
