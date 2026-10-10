from copy import deepcopy
from decimal import Decimal as D, Inexact, localcontext

import pytest

from greenpath.impact import ImpactResult, ImpactStatus, Product, build_registry, display_value
from greenpath.impact.inputs import EVInput, GreenHomeInput, PaperlessInput, SolarInput

from .conftest import NOW


@pytest.mark.parametrize("name,baseline,scenario,change", [
    ("ev", "1841.994", "1288.8", "553.194"),
    ("green_home", "2864", "2148", "716"),
    ("solar", "2864", "1074", "1790"),
])
def test_frozen_examples(payload, calculator, name, baseline, scenario, change):
    result = calculator(name).calculate(payload(name))
    assert result.status == ImpactStatus.AVAILABLE, result.issues
    assert result.value == D(change)
    assert result.baseline.emissions_kg_co2 == D(baseline)
    assert result.scenario.emissions_kg_co2 == D(scenario)
    assert result.units == "kg CO2/year"
    assert result.timestamp == NOW
    assert not result.issues
    assert ImpactResult.model_validate_json(result.model_dump_json()) == result


def test_ev_diesel_uses_matching_energy_and_combustion_factors(payload, calculator):
    data = payload("ev")
    data["baseline_fuel"]["value"] = "unblended_fossil_gas_diesel_oil"
    result = calculator("ev").calculate(data)
    assert result.status == ImpactStatus.AVAILABLE
    assert result.baseline.emissions_kg_co2 == D("1911.78")
    assert result.value == D("622.98")
    assert {f.factor_id for f in result.factors} == {
        "CEA_GRID_IN_FY2022_23_V19", "IPCC2006_DIESEL_NCV", "IPCC2006_ROAD_DIESEL_CO2",
    }


def test_ev_volume_requires_evidenced_density_and_has_same_formula(payload, calculator):
    data = payload("ev")
    mass = data.pop("baseline_fuel_mass")
    data["baseline_fuel_volume"] = deepcopy(mass)
    data["baseline_fuel_volume"].update(value="800", unit="L")
    data["baseline_fuel_density"] = deepcopy(mass)
    data["baseline_fuel_density"].update(value="0.75", unit="kg/L")
    data["baseline_fuel_density"]["evidence"]["reference"] = "synthetic-fixture:fuel-specific-density"
    result = calculator("ev").calculate(data)
    assert result.status == ImpactStatus.AVAILABLE
    assert result.value == D("553.194")
    assert any("derived" in assumption for assumption in result.assumptions)
    assert any(e.unit == "kg/L" and e.reference.endswith("fuel-specific-density") for e in result.evidence)


@pytest.mark.parametrize("name,field,value,expected", [
    ("ev", "charging_electricity", "3000", "-306.006"),
    ("green_home", "scenario_grid_import", "5000", "-716"),
    ("green_home", "scenario_grid_import", "4000", "0"),
])
def test_negative_and_zero_changes_are_preserved(payload, calculator, name, field, value, expected):
    data = payload(name)
    data[field]["value"] = value
    result = calculator(name).calculate(data)
    assert result.status == ImpactStatus.AVAILABLE
    assert result.value == D(expected)


@pytest.mark.parametrize("name,fields", [
    ("ev", ("baseline_fuel_mass", "baseline_distance", "scenario_distance", "charging_electricity")),
    ("green_home", ("baseline_grid_import", "scenario_grid_import")),
])
def test_known_zero_activity_is_available(payload, calculator, name, fields):
    data = payload(name)
    for field in fields:
        data[field]["value"] = "0"
    result = calculator(name).calculate(data)
    assert result.status == ImpactStatus.AVAILABLE
    assert result.value == 0


def test_zero_solar_is_available_and_exports_do_not_receive_credit(payload, calculator):
    data = payload("solar")
    interval = data["intervals"][0]
    interval["self_consumed_solar"]["value"] = "0"
    interval["exported_solar"]["value"] = "20000"
    result = calculator("solar").calculate(data)
    assert result.status == ImpactStatus.AVAILABLE
    assert result.value == 0


def test_solar_sums_matched_intervals_and_ignores_exports(payload, calculator):
    data = payload("solar")
    first, second = deepcopy(data["intervals"][0]), deepcopy(data["intervals"][0])
    first["period"]["end"] = "2025-07-01"
    second["period"]["start"] = "2025-07-01"
    for interval, imports, solar in [(first, "1500", "1000"), (second, "2500", "1500")]:
        interval["baseline_grid_import"]["value"] = imports
        interval["self_consumed_solar"]["value"] = solar
        interval["exported_solar"]["value"] = "10000"
        for name in ("baseline_grid_import", "self_consumed_solar", "exported_solar"):
            interval[name]["evidence"]["period"] = deepcopy(interval["period"])
    data["intervals"] = [first, second]
    result = calculator("solar").calculate(data)
    assert result.status == ImpactStatus.AVAILABLE
    assert result.value == D("1790")


def change_period(data, period):
    if isinstance(data, dict):
        for key, value in data.items():
            if key == "period":
                data[key] = deepcopy(period)
            else:
                change_period(value, period)
    elif isinstance(data, list):
        for value in data:
            change_period(value, period)


@pytest.mark.parametrize("period,units", [
    ({"start": "2025-01-01", "end": "2025-02-01"}, "kg CO2"),
    ({"start": "2024-01-01", "end": "2025-01-01"}, "kg CO2/year"),
    ({"start": "2025-01-01", "end": "2026-01-02"}, "kg CO2"),
])
def test_period_units_never_silently_annualize(payload, calculator, period, units):
    data = payload("green_home")
    change_period(data, period)
    result = calculator("green_home").calculate(data)
    assert result.status == ImpactStatus.AVAILABLE
    assert result.units == units
    assert result.value == D("716")


def test_future_forecast_is_labeled_and_not_treated_as_observed(payload, calculator):
    data = payload("green_home")
    change_period(data, {"start": "2027-01-01", "end": "2028-01-01"})
    data["scenario_grid_import"]["evidence"]["basis"] = "engineering_forecast"
    result = calculator("green_home").calculate(data)
    assert result.status == ImpactStatus.AVAILABLE
    assert any(e.basis == "engineering_forecast" for e in result.evidence)
    assert any("forecast" in assumption for assumption in result.assumptions)


def test_decimal_precision_is_independent_of_callers_context(payload, calculator):
    data = payload("ev")
    data["baseline_fuel_mass"]["value"] = "600.123456789012"
    data["charging_electricity"]["value"] = 1800.1
    with localcontext() as context:
        context.prec = 6
        context.traps[Inexact] = True
        result = calculator("ev").calculate(data)
        rounded = display_value(result)
    assert result.status == ImpactStatus.AVAILABLE
    with localcontext() as context:
        context.prec = 60
        expected = D("600.123456789012") * D("44.3") * D("0.0693") - D("1800.1") * D("0.716")
    assert result.value == expected
    assert display_value(result) == D("553.5")
    assert rounded == D("553.5")
    assert result.value != display_value(result)


@pytest.mark.parametrize("name,input_type", [
    ("ev", EVInput), ("green_home", GreenHomeInput), ("solar", SolarInput), ("paperless", PaperlessInput),
])
def test_mapping_and_typed_input_produce_identical_results(payload, calculator, name, input_type):
    raw = payload(name)
    assert calculator(name).calculate(raw) == calculator(name).calculate(input_type.model_validate(raw))


def test_all_four_products_share_result_and_registry_contract(payload, calculator):
    assert set(build_registry()) == set(Product)
    for name in ("ev", "green_home", "solar", "paperless"):
        result = calculator(name).calculate(payload(name))
        assert isinstance(result, ImpactResult)
        assert result.product == calculator(name).product
        assert result.boundary and result.exclusions and result.method_version


def test_ev_provenance_and_boundary_are_complete(payload, calculator):
    result = calculator("ev").calculate(payload("ev"))
    assert len(result.factors) == 3
    assert result.boundary == "vehicle_fuel_combustion_and_charging_generation_co2"
    assert result.scenario.emissions_kg_co2 > 0
    assert result.factor_catalogue_version == "greenpath-carbon-factors-v1.0.0"
    assert len(result.factor_catalogue_sha256) == 64
    for factor in result.factors:
        assert factor.source_url.startswith("https://")
        assert factor.source_edition and factor.source_locator and factor.boundary
        assert factor.verification_basis and factor.unit
    grid = next(f for f in result.factors if f.factor_id.startswith("CEA_"))
    assert grid.source_sha256 is None
    assert "not archived" in grid.source_limitation
    assert all(e.reference and e.period and e.basis for e in result.evidence)
    assert any("charging losses" in a for a in result.assumptions)


def test_paperless_has_no_fabricated_carbon_or_tree_equivalence(payload, calculator):
    result = calculator("paperless").calculate(payload("paperless"))
    assert result.status == ImpactStatus.UNAVAILABLE
    assert result.value is None
    assert result.baseline.emissions_kg_co2 is None
    assert result.scenario.emissions_kg_co2 is None
    assert not result.factors
    assert any(i.code == "FACTOR_NOT_ESTABLISHED" for i in result.issues)
    assert result.evidence[0].unit == "sheets"
    assert display_value(result) is None
