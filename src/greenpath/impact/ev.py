"""EV comparison: fossil fuel combustion versus charger-input grid generation."""

from dataclasses import dataclass, field
from decimal import Context, localcontext
from typing import ClassVar

from ._contract_mirror import ImpactResult, IssueCode, Product
from .catalogue import FactorCatalogue
from .common import Clock, Method, Payload, prepare, utc_now
from .inputs import EVInput

METHOD = Method(
    Product.EV_FINANCE, "ev-operational-co2-v1",
    "vehicle_fuel_combustion_and_charging_generation_co2",
    "Baseline road-fuel combustion", "Battery EV charging electricity generation",
    ("Fuel extraction, refining and distribution", "Electricity upstream supply chains and T&D losses",
     "Vehicle and battery manufacture, maintenance and end of life", "Non-CO2 gases and urea additives"),
    ("Equal travel demand; a battery EV replaces the combustion vehicle.",
     "Charger-input electricity includes charging losses; no assumed density or mileage."),
)
FUEL_FACTORS = {
    "unblended_fossil_motor_gasoline": ("IPCC2006_GASOLINE_NCV", "IPCC2006_ROAD_GASOLINE_CO2"),
    "unblended_fossil_gas_diesel_oil": ("IPCC2006_DIESEL_NCV", "IPCC2006_ROAD_DIESEL_CO2"),
}


@dataclass(frozen=True)
class EVImpactCalculator:
    catalogue: FactorCatalogue = field(default_factory=FactorCatalogue.load)
    clock: Clock = utc_now
    product: ClassVar[Product] = Product.EV_FINANCE

    def calculate(self, payload: Payload) -> ImpactResult:
        p = prepare(payload, EVInput, METHOD, self.catalogue, self.clock)
        data = p.request
        if data is None:
            return p.finish()
        for name, unit in (("baseline_fuel_mass", "kg"), ("baseline_fuel_volume", "L"),
                           ("baseline_fuel_density", "kg/L"), ("baseline_distance", "km"),
                           ("scenario_distance", "km"), ("charging_electricity", "kWh")):
            p.unit(getattr(data, name), unit, name)
        for name, expected in (("baseline_powertrain", "internal_combustion"),
                               ("scenario_powertrain", "battery_electric"),
                               ("charging_measurement_point", "charger_input"),
                               ("replaces_baseline", True), ("charging_supply", "indian_grid")):
            p.expect(getattr(data, name), expected, name)
        if data.baseline_distance.value != data.scenario_distance.value:
            p.issue(IssueCode.INCOMPARABLE_BASELINE, "scenario_distance", "Match baseline travel demand")
        for distance, activity, name in (
            (data.baseline_distance.value, data.baseline_fuel_mass, "baseline_fuel_mass"),
            (data.baseline_distance.value, data.baseline_fuel_volume, "baseline_fuel_volume"),
            (data.scenario_distance.value, data.charging_electricity, "charging_electricity"),
        ):
            if activity is not None and ((distance == 0) != (activity.value == 0)):
                p.issue(IssueCode.CONFLICTING_INPUT, name, "Travel and energy activity must both be zero or both positive")
        fuel_ids = FUEL_FACTORS.get(data.baseline_fuel.value)
        ncv = fuel_factor = None
        if fuel_ids is None:
            p.issue(IssueCode.UNSUPPORTED_SCOPE, "baseline_fuel", "Document a supported unblended fossil fuel")
        else:
            ncv = p.factor(fuel_ids[0], "MJ/kg")
            fuel_factor = p.factor(fuel_ids[1], "kg CO2/MJ")
        mass = data.baseline_fuel_mass.value if data.baseline_fuel_mass is not None else None
        volume, density = data.baseline_fuel_volume, data.baseline_fuel_density
        if density is not None and density.value == 0:
            p.issue(IssueCode.INVALID_INPUT, "baseline_fuel_density", "Fuel density must be positive")
        if volume is not None and density is None:
            p.issue(IssueCode.MISSING_INPUT, "baseline_fuel_density", "Litres require a sourced fuel-specific density in kg/L")
        if density is not None and volume is None:
            p.issue(IssueCode.MISSING_INPUT, "baseline_fuel_volume", "Density requires a matching fuel volume")
        if mass is None and volume is None:
            p.issue(IssueCode.MISSING_INPUT, "baseline_fuel_mass", "Supply fuel mass, or volume with sourced density")
        if p.issues:
            return p.finish()
        assumptions = ()
        with localcontext(Context(prec=60)):
            if volume is not None:
                derived_mass = volume.value * density.value
                if mass is not None and mass != derived_mass:
                    p.issue(IssueCode.CONFLICTING_INPUT, "baseline_fuel_mass", "Fuel mass conflicts with volume times density")
                    return p.finish()
                mass = derived_mass
                assumptions = ("Fuel mass derived from supplied litres and evidenced fuel-specific density.",)
            baseline = mass * ncv * fuel_factor
            scenario = data.charging_electricity.value * p.grid_value
        return p.finish(baseline, scenario, assumptions)
