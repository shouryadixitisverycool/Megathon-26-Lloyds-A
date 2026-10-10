"""Electricity-efficiency comparison for the same home and service demand."""

from dataclasses import dataclass, field
from decimal import Context, localcontext
from typing import ClassVar

from ._contract_mirror import ImpactResult, IssueCode, Product
from .catalogue import FactorCatalogue
from .common import Clock, Method, Payload, prepare, utc_now
from .inputs import GreenHomeInput

METHOD = Method(
    Product.GREEN_HOME, "home-electricity-operational-co2-v1",
    "home_grid_electricity_generation_co2",
    "Baseline home grid imports", "Home grid imports after the efficiency intervention",
    ("Construction and retrofit embodied emissions", "Refrigerants, water and non-electric fuels",
     "Electricity upstream supply chains and T&D losses"),
    ("Same home and comparable weather, occupancy and service demand.",
     "Fuel use and on-site generation remain unchanged; solar reductions are excluded."),
)


@dataclass(frozen=True)
class GreenHomeImpactCalculator:
    catalogue: FactorCatalogue = field(default_factory=FactorCatalogue.load)
    clock: Clock = utc_now
    product: ClassVar[Product] = Product.GREEN_HOME

    def calculate(self, payload: Payload) -> ImpactResult:
        p = prepare(payload, GreenHomeInput, METHOD, self.catalogue, self.clock)
        data = p.request
        if data is None:
            return p.finish()
        for name in ("baseline_grid_import", "scenario_grid_import"):
            p.unit(getattr(data, name), "kWh", name)
        for name in ("same_home", "comparable_service"):
            p.expect(getattr(data, name), True, name, IssueCode.INCOMPARABLE_BASELINE)
        for name in ("fuel_use_unchanged", "onsite_generation_unchanged"):
            p.expect(getattr(data, name), True, name)
        if p.issues:
            return p.finish()
        with localcontext(Context(prec=60)):
            grid = p.grid_value
            baseline = data.baseline_grid_import.value * grid
            scenario = data.scenario_grid_import.value * grid
        return p.finish(baseline, scenario)
