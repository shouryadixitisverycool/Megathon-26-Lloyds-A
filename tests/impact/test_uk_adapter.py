"""Reviewed UK integration, explicit inputs, contract units and provenance."""

from datetime import date, datetime, timezone

import pytest

from greenpath.contracts.customer import CustomerSnapshot
from greenpath.contracts.enums import ImpactStatus, Product
from greenpath.contracts.fixtures import load_model
from greenpath.contracts.impact import ImpactResult as ScoringImpactResult
from greenpath.contracts.impact_detail import ImpactResult
from greenpath.extensions import uk_impact
from greenpath.impact.uk_adapter import UKImpactCalculator


NOW = datetime(2026, 10, 10, tzinfo=timezone.utc)


def source():
    return load_model("customer_snapshot_C10001", CustomerSnapshot)


def ev_source():
    snapshot = source()
    # Explicit test-only synthetic scenario. No runtime default efficiencies.
    return snapshot.model_copy(update={"features": {**snapshot.features,
        "ice_litres_per_100km": 6.5, "ev_kwh_per_100km": 18.0,
        "charging_efficiency": 0.9}})


def test_ev_co2e_contract_matches_reviewed_formula_and_preserves_provenance():
    snapshot = ev_source()
    calculator = UKImpactCalculator(Product.EV_FINANCE, clock=lambda: NOW)
    result = calculator.calculate_scoring(snapshot)
    reviewed = uk_impact.calculate(Product.EV_FINANCE, {
        "annual_mileage_km": snapshot.vehicle.annual_mileage_km,
        "fuel_type": snapshot.vehicle.fuel_type.value,
        "mileage_evidence": "ESTIMATED" if snapshot.vehicle.mileage_is_estimated else "OBSERVED",
        "ice_litres_per_100km": 6.5, "ev_kwh_per_100km": 18.0, "charging_efficiency": 0.9,
    })
    assert result.status == ImpactStatus.AVAILABLE
    assert result.unit == "kg CO2e/year"
    assert result.baseline == float(reviewed["baseline_emissions"])
    assert result.scenario == float(reviewed["scenario_emissions"])
    assert result.estimated_reduction == float(reviewed["potential_reduction"])
    assert result.data_cutoff == snapshot.feature_cutoff
    assert result.calculation_timestamp == NOW
    assert len(result.factor_ids) == 6
    assert all(a.source.startswith(f"customer360:{snapshot.feature_version}:{snapshot.feature_cutoff}:")
               for a in result.assumptions)
    assert ScoringImpactResult.model_validate_json(result.model_dump_json()) == result


def test_product_contract_exposes_co2e_without_relabelling_as_co2():
    result = UKImpactCalculator(Product.EV_FINANCE, clock=lambda: NOW).calculate(ev_source())
    assert result.status == ImpactStatus.AVAILABLE
    assert result.units == "kg CO2e/year"
    assert result.baseline.emissions_kg_co2 is None and result.scenario.emissions_kg_co2 is None
    assert result.value == result.baseline.emissions_kg_co2e - result.scenario.emissions_kg_co2e
    scoring = UKImpactCalculator(Product.EV_FINANCE).calculate_scoring(ev_source())
    assert float(result.value) == scoring.estimated_reduction
    assert float(result.baseline.emissions_kg_co2e) == scoring.baseline
    assert float(result.scenario.emissions_kg_co2e) == scoring.scenario
    assert not result.issues
    assert len(result.factors) == 6
    assert all(f.geography == "United Kingdom" and "CO2e" in f.unit for f in result.factors)
    assert all(f.source_sha256 == uk_impact.factor_catalogue()["source_sha256"] for f in result.factors)
    assert result.timestamp == NOW
    assert result.period.start == ev_source().feature_cutoff
    assert any(e.basis == "SYNTHETIC_SCENARIO" for e in result.evidence)
    assert ImpactResult.model_validate_json(result.model_dump_json()) == result


def test_missing_efficiencies_are_not_inferred_from_mileage_or_spend():
    calculator = UKImpactCalculator(Product.EV_FINANCE)
    result = calculator.calculate(source())
    assert {i.field for i in result.issues} == {
        "ice_litres_per_100km", "ev_kwh_per_100km", "charging_efficiency"}
    assert all(i.code == "MISSING_INPUT" for i in result.issues)
    assert not result.factors and result.value is None
    assert calculator.calculate_scoring(source()).status == ImpactStatus.UNAVAILABLE


@pytest.mark.parametrize("value", [0.0, 1.1, "unknown", True, float("nan")])
def test_invalid_scenario_fails_closed(value):
    snapshot = ev_source()
    snapshot.features["charging_efficiency"] = value
    result = UKImpactCalculator(Product.EV_FINANCE).calculate(snapshot)
    assert result.value is None
    assert any(i.code == "INVALID_INPUT" for i in result.issues)


def test_unsupported_hybrid_is_not_treated_as_petrol():
    snapshot = ev_source()
    from greenpath.contracts.enums import FuelType
    snapshot = snapshot.model_copy(update={"vehicle": snapshot.vehicle.model_copy(update={"fuel_type": FuelType.HYBRID})})
    # Validate the source so its enum is restored before passing to the adapter.
    snapshot = CustomerSnapshot.model_validate(snapshot.model_dump())
    result = UKImpactCalculator(Product.EV_FINANCE).calculate(snapshot)
    assert any(i.field == "fuel_type" and i.code == "INVALID_INPUT" for i in result.issues)


def test_factor_checksum_failure_has_no_numbers_or_factors(tmp_path, monkeypatch):
    corrupted = tmp_path / "factors.json"
    corrupted.write_text("{}")
    monkeypatch.setattr(uk_impact, "FACTOR_PATH", corrupted)
    calculator = UKImpactCalculator(Product.EV_FINANCE)
    result = calculator.calculate(ev_source())
    assert result.value is None and not result.factors
    assert result.factor_catalogue_version == "unverified"
    assert result.issues[0].code == "FACTOR_NOT_ESTABLISHED"
    assert calculator.calculate_scoring(ev_source()).status == ImpactStatus.UNAVAILABLE


def test_future_vehicle_record_is_rejected():
    snapshot = ev_source()
    snapshot = snapshot.model_copy(update={"vehicle": snapshot.vehicle.model_copy(update={
        "record_updated_at": date(2027, 1, 1)})})
    result = UKImpactCalculator(Product.EV_FINANCE).calculate(snapshot)
    assert any(i.field == "vehicle.record_updated_at" for i in result.issues)


def test_solar_and_home_do_not_invent_generation_or_savings():
    for product, missing in ((Product.SOLAR_FINANCE, "annual_generation_kwh"),
                             (Product.GREEN_HOME, "gas_saving_fraction")):
        result = UKImpactCalculator(product).calculate(source())
        assert any(i.field == missing and i.code == "MISSING_INPUT" for i in result.issues)
        assert not result.factors and result.value is None


@pytest.mark.parametrize("product,scenario", [
    (Product.SOLAR_FINANCE, {"annual_generation_kwh": 1000.0, "self_consumption_fraction": 0.5,
        "proposed_capacity_kw": 1.0, "generation_evidence": "Explicit test-only synthetic generation"}),
    (Product.GREEN_HOME, {"intervention": "INSULATION", "annual_gas_kwh_gross": 10000.0,
        "electricity_saving_fraction": 0.1, "gas_saving_fraction": 0.2,
        "savings_evidence": "Explicit test-only synthetic savings"}),
    (Product.GREEN_HOME, {"intervention": "HEAT_PUMP", "annual_heating_gas_kwh_gross": 8000.0,
        "boiler_efficiency_gross": 0.85, "seasonal_performance_factor": 3.0,
        "performance_evidence": "Explicit test-only synthetic performance"}),
])
def test_other_explicit_scenarios_use_reviewed_formula(product, scenario):
    snapshot = source()
    snapshot = snapshot.model_copy(update={"features": {**snapshot.features, **scenario}})
    result = UKImpactCalculator(product).calculate_scoring(snapshot)
    inputs = dict(scenario)
    if scenario.get("intervention") != "HEAT_PUMP":
        inputs["annual_electricity_kwh"] = snapshot.energy.electricity_kwh_12m
    if product == Product.SOLAR_FINANCE:
        inputs["region"] = snapshot.home.region
    reviewed = uk_impact.calculate(product, inputs)
    assert result.status == ImpactStatus.AVAILABLE
    assert result.estimated_reduction == float(reviewed["potential_reduction"])
    detail = UKImpactCalculator(product).calculate(snapshot)
    assert detail.status == ImpactStatus.AVAILABLE
    assert float(detail.value) == result.estimated_reduction


def test_original_vehicle_observation_time_is_retained():
    snapshot = ev_source()
    result = UKImpactCalculator(Product.EV_FINANCE).calculate(snapshot)
    mileage = next(e for e in result.evidence if e.field == "annual_mileage_km")
    assert mileage.observed_at.date() == snapshot.vehicle.record_updated_at
    assert result.feature_cutoff.date() == snapshot.feature_cutoff


def test_paperless_activity_is_not_a_carbon_claim():
    snapshot = source()
    snapshot = snapshot.model_copy(update={"features": {**snapshot.features,
        "sheets_per_statement": 2, "avoided_fraction": 1.0}})
    calculator = UKImpactCalculator(Product.PAPERLESS_BANKING)
    result = calculator.calculate_scoring(snapshot)
    assert result.status == ImpactStatus.NOT_CLAIMED
    assert result.baseline is None and not result.factor_ids
    assert result.secondary_metrics[0].value == snapshot.digital.paper_statements_12m
    detail = calculator.calculate(snapshot)
    assert detail.status == ImpactStatus.NOT_CLAIMED
    assert detail.value is None and detail.issues


def test_missing_snapshot_is_explicit():
    result = UKImpactCalculator(Product.EV_FINANCE).calculate(None)
    assert result.feature_cutoff is None and result.value is None
    assert result.issues[0].field == "snapshot"


def test_missing_paperless_inputs_are_unavailable_not_supported_activity():
    result = UKImpactCalculator(Product.PAPERLESS_BANKING).calculate(source())
    assert result.status == ImpactStatus.UNAVAILABLE
    assert result.value is None
    assert all(i.code == "MISSING_INPUT" for i in result.issues)
