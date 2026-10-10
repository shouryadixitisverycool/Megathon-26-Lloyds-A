"""Separate synthetic engineering inputs and taxonomy boundaries."""

from datetime import date

import pytest
import pandas as pd

from greenpath.contracts.customer import CustomerSnapshot
from greenpath.contracts.enums import Product
from greenpath.contracts.fixtures import load_model
from greenpath.data_generation.scenarios import generate_scenario_table
from greenpath.impact.uk_adapter import UKImpactCalculator
from greenpath.models.transaction_classifier import _rule_category, normalise_description
from greenpath.pipelines.scenario_provider import ScenarioProvider, UKImpactInput


def source():
    return load_model("customer_snapshot_C10001", CustomerSnapshot)


def provider(snapshot):
    return ScenarioProvider(generate_scenario_table([snapshot.customer_id],
        effective_on=snapshot.feature_cutoff, available_on=snapshot.feature_cutoff))


@pytest.mark.parametrize("product,status", [
    (Product.EV_FINANCE, "AVAILABLE"), (Product.GREEN_HOME, "AVAILABLE"),
    (Product.PAPERLESS_BANKING, "NOT_CLAIMED"), (Product.SOLAR_FINANCE, "UNAVAILABLE"),
])
def test_demo_subset_is_explicit_and_solar_intentionally_unavailable(product, status):
    snapshot = source()
    result = UKImpactCalculator(product).calculate(provider(snapshot).attach(snapshot, product))
    assert result.status == status
    scenarios = [e for e in result.evidence if e.basis == "SYNTHETIC_SCENARIO"]
    if product != Product.SOLAR_FINANCE:
        assert scenarios and all("effective=" in e.reference and "available=" in e.reference for e in scenarios)
    if product == Product.GREEN_HOME:
        assert next(e for e in scenarios if e.field == "annual_gas_kwh_gross").value == 10000
    if product == Product.PAPERLESS_BANKING:
        assert result.secondary_metrics[1].value == snapshot.digital.paper_statements_12m * 2


def test_features_never_supply_efficiencies():
    snapshot = source()
    snapshot.features.update(ice_litres_per_100km=6.5, ev_kwh_per_100km=18.0, charging_efficiency=0.9)
    assert UKImpactCalculator(Product.EV_FINANCE).calculate(snapshot).status == "UNAVAILABLE"


def test_future_available_rows_and_unselected_customers_are_not_used():
    snapshot = source()
    table = generate_scenario_table([snapshot.customer_id], effective_on=snapshot.feature_cutoff,
        available_on=date(2099, 1, 1))
    p = ScenarioProvider(table)
    assert not p.attach(snapshot, Product.EV_FINANCE).scenario
    assert not p.get_scenario("not-selected", Product.EV_FINANCE, date(2099, 1, 1))


def test_partial_coverage_is_not_measured_and_explicit_forecast_is_labelled():
    snapshot = source()
    snapshot = snapshot.model_copy(update={"energy": snapshot.energy.model_copy(update={"energy_months_present": 6})})
    product = Product.GREEN_HOME
    payload = provider(snapshot).attach(snapshot, product)
    assert UKImpactCalculator(product).calculate(payload).status == "UNAVAILABLE"
    forecast = payload.scenario[0].model_copy(update={"field": "annual_electricity_kwh",
        "value": 3000.0, "unit": "kWh/year", "basis": "EXPLICIT_FORECAST",
        "description": "Caller-chosen annual forecast, not extrapolated by the calculator"})
    result = UKImpactCalculator(product).calculate(UKImpactInput(snapshot=snapshot,
        scenario=(*payload.scenario, forecast)))
    assert result.status == "AVAILABLE"
    assert "estimated" in result.baseline.description
    assert next(e for e in result.evidence if e.field == "annual_electricity_kwh").basis == "EXPLICIT_FORECAST"


def test_source_activity_window_uses_prior_twelve_completed_months():
    snapshot = source().model_copy(update={"feature_cutoff": date(2026, 10, 10)})
    result = UKImpactCalculator(Product.PAPERLESS_BANKING).calculate(
        provider(snapshot).attach(snapshot, Product.PAPERLESS_BANKING))
    evidence = next(e for e in result.evidence if e.field == "annual_statements")
    assert evidence.period.start == date(2025, 10, 1)
    assert evidence.period.end == date(2026, 10, 1)


def test_typed_annualised_energy_is_a_forecast_not_full_observation():
    snapshot = source()
    snapshot = snapshot.model_copy(update={"energy": snapshot.energy.model_copy(update={
        "electricity_months_present": 6, "electricity_kwh_observed": 1500.0,
        "electricity_kwh_12m": 3000.0, "electricity_annualisation_factor": 2.0,
        "electricity_is_estimated": True})})
    result = UKImpactCalculator(Product.GREEN_HOME).calculate(provider(snapshot).attach(snapshot, Product.GREEN_HOME))
    assert result.status == "AVAILABLE"
    assert "estimated" in result.baseline.description
    assert any("not measured annual consumption" in a for a in result.assumptions)


def test_synthetic_solar_generation_is_rejected():
    snapshot = source()
    row = provider(snapshot).attach(snapshot, Product.GREEN_HOME).scenario[0].model_copy(update={
        "product": Product.SOLAR_FINANCE, "field": "annual_generation_kwh", "value": 1000.0,
        "unit": "kWh/year"})
    result = UKImpactCalculator(Product.SOLAR_FINANCE).calculate(UKImpactInput(snapshot=snapshot, scenario=(row,)))
    assert any("PVGIS" in i.message for i in result.issues)


@pytest.mark.parametrize("description,category", [
    ("GOOD ENERGY DD", "UTILITIES"), ("GOOD ENERGY ELEC DD", "ELECTRICITY"),
    ("SHELL EV CHARGING", "AUTOMOTIVE"), ("SHELL EV CHARGING REFUND", "AUTOMOTIVE"),
    ("SHELL PETROL REFUND", "FUEL"), ("TESCO PFS", "FUEL"),
])
def test_taxonomy_refunds_keep_activity_category_not_positive_consumption(description, category):
    # Classification is sign-independent. Spend aggregation owns refund netting;
    # a refund descriptor is never evidence of litres or kWh consumed.
    assert _rule_category(normalise_description(description).split(), {"SHELL": "FUEL"}) == category


def test_good_energy_catalogue_has_unspecified_utility_truth():
    from greenpath.data_generation.merchants import _CATALOGUE
    assert [row[1] for row in _CATALOGUE if row[0] == "GOOD ENERGY"] == ["UTILITIES"]


def test_mixed_scenario_values_roundtrip_parquet_with_strict_types(tmp_path):
    snapshot = source()
    table = generate_scenario_table([snapshot.customer_id], effective_on=snapshot.feature_cutoff,
                                    available_on=snapshot.feature_cutoff)
    assert table.value.map(type).eq(str).all()
    path = tmp_path / "scenario_evidence.parquet"
    table.to_parquet(path, index=False)
    rows = ScenarioProvider(pd.read_parquet(path)).rows
    values = {row.field: row.value for row in rows}
    assert values["intervention"] == "INSULATION"
    assert type(values["sheets_per_statement"]) is int
    assert values["sheets_per_statement"] == 2
    assert type(values["ice_litres_per_100km"]) is float
    assert values["ice_litres_per_100km"] == 6.5


@pytest.mark.parametrize("encoded", ["true", "null", "[]", "{}", "NaN", "Infinity", "not-json"])
def test_scenario_storage_rejects_invalid_quantities(encoded):
    snapshot = source()
    table = generate_scenario_table([snapshot.customer_id], effective_on=snapshot.feature_cutoff,
                                    available_on=snapshot.feature_cutoff)
    table.loc[0, "value"] = encoded
    with pytest.raises(ValueError):
        ScenarioProvider(table)
