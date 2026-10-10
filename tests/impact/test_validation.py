import json
from copy import deepcopy
from pathlib import Path

import pytest

from greenpath.impact import ImpactStatus, IssueCode, build_registry
from greenpath.impact.catalogue import CATALOGUE_SHA256, GRID_FACTOR, FactorCatalogue
from greenpath.impact.inputs import EVInput

from conftest import CASES, NOW
from test_formulas import change_period


def unavailable(result, code=None):
    assert result.status == ImpactStatus.UNAVAILABLE
    assert result.value is None
    assert result.baseline.emissions_kg_co2 is None
    assert result.scenario.emissions_kg_co2 is None
    assert result.issues
    assert result.timestamp == NOW
    assert result.method_version and result.boundary
    if code:
        assert any(issue.code == code for issue in result.issues), result.issues


@pytest.mark.parametrize("name", list(CASES))
@pytest.mark.parametrize("data", [None, {}, [], "invalid", 42])
def test_empty_and_malformed_requests_fail_closed(calculator, name, data):
    unavailable(calculator(name).calculate(data))


@pytest.mark.parametrize("name,field", [
    ("ev", "baseline_fuel"), ("ev", "baseline_fuel_mass"),
    ("ev", "charging_electricity"), ("ev", "charging_supply"),
    ("green_home", "efficiency_assessment"), ("green_home", "comparability_basis"),
    ("solar", "intervals"), ("solar", "measurement_point"),
])
def test_missing_critical_inputs_fail_closed(payload, calculator, name, field):
    data = payload(name)
    del data[field]
    unavailable(calculator(name).calculate(data), IssueCode.MISSING_INPUT)


@pytest.mark.parametrize("value", [True, False, "NaN", "Infinity", "-Infinity", float("nan"),
                                   float("inf"), "-1", [], {}, "abc", None,
                                   "0.0000000000001", "1000000000000000000000000"])
@pytest.mark.parametrize("name,field", [("ev", "charging_electricity"),
                                       ("green_home", "baseline_grid_import")])
def test_quantities_reject_invalid_numbers(payload, calculator, name, field, value):
    data = payload(name)
    data[field]["value"] = value
    unavailable(calculator(name).calculate(data), IssueCode.INVALID_INPUT)


@pytest.mark.parametrize("name,field,unit", [
    ("ev", "baseline_fuel_mass", "L"), ("ev", "baseline_distance", "miles"),
    ("ev", "charging_electricity", "MWh"), ("green_home", "baseline_grid_import", "INR"),
])
def test_units_are_explicit_and_not_guessed(payload, calculator, name, field, unit):
    data = payload(name)
    data[field]["unit"] = unit
    unavailable(calculator(name).calculate(data), IssueCode.INVALID_INPUT)


@pytest.mark.parametrize("field", ["reference", "basis", "observed_at", "period", "freshness"])
def test_missing_evidence_components_are_not_defaulted(payload, calculator, field):
    data = payload("ev")
    del data["charging_electricity"]["evidence"][field]
    unavailable(calculator("ev").calculate(data), IssueCode.MISSING_INPUT)


@pytest.mark.parametrize("freshness", ["stale", "unknown"])
def test_unapproved_freshness_abstains(payload, calculator, freshness):
    data = payload("green_home")
    data["scenario_grid_import"]["evidence"]["freshness"] = freshness
    result = calculator("green_home").calculate(data)
    unavailable(result, IssueCode.STALE_INPUT)
    assert result.evidence and result.factors


def test_conflicts_cutoff_and_stale_issues_are_all_preserved(payload, calculator):
    data = payload("ev")
    evidence = data["charging_electricity"]["evidence"]
    evidence.update(observed_at="2026-01-04T00:00:00Z", freshness="stale", conflicts=["Meter and declaration differ"])
    result = calculator("ev").calculate(data)
    unavailable(result)
    assert {issue.code for issue in result.issues} >= {
        IssueCode.INVALID_INPUT, IssueCode.STALE_INPUT, IssueCode.CONFLICTING_INPUT,
    }
    assert any(e.conflicts for e in result.evidence)


@pytest.mark.parametrize("time", ["2026-01-04T00:00:00Z", "2026-01-03T03:00:00+02:00"])
def test_observation_cutoff_compares_timezone_aware_instants(payload, calculator, time):
    data = payload("ev")
    data["charging_electricity"]["evidence"]["observed_at"] = time
    unavailable(calculator("ev").calculate(data), IssueCode.INVALID_INPUT)


@pytest.mark.parametrize("time", ["2026-01-02T00:00:00", 1767312000, True])
def test_evidence_timestamp_requires_explicit_timezone(payload, calculator, time):
    data = payload("ev")
    data["charging_electricity"]["evidence"]["observed_at"] = time
    unavailable(calculator("ev").calculate(data), IssueCode.INVALID_INPUT)


def test_evidence_period_must_match(payload, calculator):
    data = payload("green_home")
    data["scenario_grid_import"]["evidence"]["period"]["end"] = "2025-12-01"
    unavailable(calculator("green_home").calculate(data), IssueCode.INCOMPARABLE_BASELINE)


@pytest.mark.parametrize("period", [
    {"start":"2025-01-01", "end":"2025-01-01"},
    {"start":"2026-01-01", "end":"2025-01-01"},
    {"start":True, "end":"2026-01-01"},
    {"start":"2025-01-01T00:00:00Z", "end":"2026-01-01"},
])
def test_bad_periods_are_invalid(payload, calculator, period):
    data = payload("green_home")
    data["context"]["period"] = period
    unavailable(calculator("green_home").calculate(data), IssueCode.INVALID_INPUT)


@pytest.mark.parametrize("name", ["ev", "green_home", "solar"])
@pytest.mark.parametrize("field,value", [("geography", "US"), ("synthetic_demo", False)])
def test_factor_geography_and_demo_scope_are_enforced(payload, calculator, name, field, value):
    data = payload(name)
    data["context"][field] = value
    unavailable(calculator(name).calculate(data), IssueCode.UNSUPPORTED_SCOPE)


def test_future_meter_readings_are_not_accepted_as_forecasts(payload, calculator):
    data = payload("green_home")
    change_period(data, {"start":"2027-01-01", "end":"2028-01-01"})
    data["scenario_grid_import"]["evidence"]["basis"] = "meter_reading"
    unavailable(calculator("green_home").calculate(data), IssueCode.INVALID_INPUT)


@pytest.mark.parametrize("field,value", [
    ("baseline_fuel", "E20"), ("baseline_fuel", "unknown"), ("baseline_fuel", "CNG"),
    ("baseline_powertrain", "hybrid"), ("scenario_powertrain", "plug_in_hybrid"),
    ("charging_measurement_point", "battery_output"), ("charging_supply", "mixed_grid_and_solar"),
    ("replaces_baseline", False),
])
def test_ev_unsupported_boundaries_abstain(payload, calculator, field, value):
    data = payload("ev")
    data[field]["value"] = value
    result = calculator("ev").calculate(data)
    unavailable(result, IssueCode.UNSUPPORTED_SCOPE)
    assert result.boundary == "vehicle_fuel_combustion_and_charging_generation_co2"


def test_ev_travel_demand_must_match(payload, calculator):
    data = payload("ev")
    data["scenario_distance"]["value"] = "14000"
    unavailable(calculator("ev").calculate(data), IssueCode.INCOMPARABLE_BASELINE)


@pytest.mark.parametrize("field", ["baseline_fuel_mass", "charging_electricity"])
def test_ev_positive_travel_requires_positive_energy(payload, calculator, field):
    data = payload("ev")
    data[field]["value"] = "0"
    unavailable(calculator("ev").calculate(data), IssueCode.CONFLICTING_INPUT)


def test_ev_litres_without_density_do_not_get_a_default(payload, calculator):
    data = payload("ev")
    data["baseline_fuel_volume"] = data.pop("baseline_fuel_mass")
    data["baseline_fuel_volume"].update(value="800", unit="L")
    result = calculator("ev").calculate(data)
    unavailable(result, IssueCode.MISSING_INPUT)
    assert any(i.field == "baseline_fuel_density" for i in result.issues)


def test_ev_mass_and_volume_conflict_fails_closed(payload, calculator):
    data = payload("ev")
    data["baseline_fuel_volume"] = deepcopy(data["baseline_fuel_mass"])
    data["baseline_fuel_volume"].update(value="800", unit="L")
    data["baseline_fuel_density"] = deepcopy(data["baseline_fuel_mass"])
    data["baseline_fuel_density"].update(value="0.8", unit="kg/L")
    unavailable(calculator("ev").calculate(data), IssueCode.CONFLICTING_INPUT)


@pytest.mark.parametrize("field,code", [
    ("same_home", IssueCode.INCOMPARABLE_BASELINE), ("comparable_service", IssueCode.INCOMPARABLE_BASELINE),
    ("fuel_use_unchanged", IssueCode.UNSUPPORTED_SCOPE), ("onsite_generation_unchanged", IssueCode.UNSUPPORTED_SCOPE),
])
def test_home_comparability_and_solar_overlap_guards(payload, calculator, field, code):
    data = payload("green_home")
    data[field]["value"] = False
    unavailable(calculator("green_home").calculate(data), code)


def test_solar_checks_physics_per_interval_not_only_annual_sum(payload, calculator):
    data = payload("solar")
    first, second = deepcopy(data["intervals"][0]), deepcopy(data["intervals"][0])
    first["period"]["end"] = "2025-07-01"
    second["period"]["start"] = "2025-07-01"
    for interval, imports, solar in [(first, "500", "1000"), (second, "3500", "1500")]:
        interval["baseline_grid_import"]["value"] = imports
        interval["self_consumed_solar"]["value"] = solar
        for name in ("baseline_grid_import", "self_consumed_solar", "exported_solar"):
            interval[name]["evidence"]["period"] = deepcopy(interval["period"])
    data["intervals"] = [first, second]
    unavailable(calculator("solar").calculate(data), IssueCode.CONFLICTING_INPUT)


@pytest.mark.parametrize("start,end", [("2025-02-01", "2026-01-01"),
                                      ("2025-01-01", "2025-12-01"),
                                      ("2025-01-01", "2026-02-01")])
def test_solar_intervals_cover_exact_comparison_period(payload, calculator, start, end):
    data = payload("solar")
    interval = data["intervals"][0]
    interval["period"] = {"start": start, "end": end}
    for name in ("baseline_grid_import", "self_consumed_solar", "exported_solar"):
        interval[name]["evidence"]["period"] = deepcopy(interval["period"])
    unavailable(calculator("solar").calculate(data), IssueCode.INCOMPARABLE_BASELINE)


def test_duplicate_solar_intervals_are_rejected(payload, calculator):
    data = payload("solar")
    data["intervals"].append(deepcopy(data["intervals"][0]))
    unavailable(calculator("solar").calculate(data), IssueCode.INCOMPARABLE_BASELINE)


@pytest.mark.parametrize("field,value", [("storage_used", True), ("demand_unchanged", False),
                                       ("displaces_grid_only", False), ("measurement_point", "dc_generation")])
def test_solar_unsupported_scope_abstains(payload, calculator, field, value):
    data = payload("solar")
    data[field]["value"] = value
    unavailable(calculator("solar").calculate(data), IssueCode.UNSUPPORTED_SCOPE)


def test_missing_and_tampered_catalogues_abstain_without_network(payload, tmp_path):
    missing = FactorCatalogue.load(tmp_path / "missing.json")
    source = Path("src/greenpath/impact/factors/carbon_factors.v1.json")
    changed = json.loads(source.read_text())
    changed["factors"][0]["value"] = "0.999"
    target = tmp_path / "tampered.json"
    target.write_text(json.dumps(changed))
    for catalogue in (missing, FactorCatalogue.load(target)):
        for name in ("ev", "green_home", "solar"):
            result = build_registry(catalogue=catalogue, clock=lambda: NOW)[CASES[name]].calculate(payload(name))
            unavailable(result, IssueCode.FACTOR_NOT_ESTABLISHED)
            assert result.factor_catalogue_sha256 == CATALOGUE_SHA256


def test_catalogue_refuses_missing_ids_and_wrong_units():
    catalogue = FactorCatalogue.load()
    for factor_id, unit in [("invented", "kg CO2/kWh"), (GRID_FACTOR, "kg CO2e/kWh")]:
        factor, issue = catalogue.require(factor_id, unit)
        assert factor is None and issue.code == IssueCode.FACTOR_NOT_ESTABLISHED


def test_model_construct_does_not_bypass_numeric_validation(payload, calculator):
    data = payload("ev")
    data["charging_electricity"]["value"] = True
    unsafe = EVInput.model_construct(**data)
    unavailable(calculator("ev").calculate(unsafe), IssueCode.INVALID_INPUT)


def test_paperless_invalid_sheet_count_still_has_no_carbon(payload, calculator):
    data = payload("paperless")
    data["avoided_sheets"]["value"] = "0.5"
    result = calculator("paperless").calculate(data)
    unavailable(result, IssueCode.INVALID_INPUT)
    assert any(i.code == IssueCode.FACTOR_NOT_ESTABLISHED for i in result.issues)


def test_claim_booleans_are_strict(payload, calculator):
    data = payload("green_home")
    data["fuel_use_unchanged"]["value"] = "true"
    unavailable(calculator("green_home").calculate(data), IssueCode.INVALID_INPUT)


def test_unknown_inputs_are_not_silently_used(payload, calculator):
    data = payload("green_home")
    data["assumed_savings_percent"] = 30
    unavailable(calculator("green_home").calculate(data), IssueCode.INVALID_INPUT)


def test_input_errors_preserve_valid_context_and_method_metadata(payload, calculator):
    data = payload("ev")
    data["charging_electricity"]["value"] = "NaN"
    result = calculator("ev").calculate(data)
    unavailable(result, IssueCode.INVALID_INPUT)
    assert result.period.start.isoformat() == "2025-01-01"
    assert result.feature_cutoff.isoformat() == "2026-01-03T00:00:00+00:00"
    assert result.synthetic_demo is True
    assert result.factors and result.factors[0].factor_id == GRID_FACTOR
