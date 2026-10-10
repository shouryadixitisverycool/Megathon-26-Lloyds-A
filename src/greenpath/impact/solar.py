"""Solar self-consumption comparison with matched, complete load intervals."""

from dataclasses import dataclass, field
from decimal import Context, Decimal, localcontext
from typing import ClassVar

from greenpath.contracts.impact_detail import ImpactResult, IssueCode, Product
from .catalogue import FactorCatalogue
from .common import Clock, Method, Payload, prepare, utc_now
from .inputs import SolarInput

METHOD = Method(
    Product.SOLAR_FINANCE, "solar-self-consumption-operational-co2-v1",
    "solar_reduction_in_grid_import_generation_co2",
    "Grid imports before solar", "Grid imports after matched net AC solar self-consumption",
    ("Exported generation", "Panel and inverter manufacture, installation, maintenance and end of life",
     "Electricity upstream supply chains and T&D losses"),
    ("Demand unchanged; no storage or displacement of non-grid fuels.",
     "Self-consumption is net of inverter losses and auxiliaries; exports receive no credit.",
     "National-average import accounting comparison, not marginal generation displacement."),
)


@dataclass(frozen=True)
class SolarImpactCalculator:
    catalogue: FactorCatalogue = field(default_factory=FactorCatalogue.load)
    clock: Clock = utc_now
    product: ClassVar[Product] = Product.SOLAR_FINANCE

    def calculate(self, payload: Payload) -> ImpactResult:
        p = prepare(payload, SolarInput, METHOD, self.catalogue, self.clock)
        data = p.request
        if data is None:
            return p.finish()
        for name, expected in (("demand_unchanged", True), ("storage_used", False),
                               ("displaces_grid_only", True),
                               ("measurement_point", "net_ac_self_consumption")):
            p.expect(getattr(data, name), expected, name)
        previous_end = data.context.period.start
        for index, interval in enumerate(data.intervals):
            prefix = f"intervals.{index}"
            for name in ("baseline_grid_import", "self_consumed_solar", "exported_solar"):
                p.unit(getattr(interval, name), "kWh", f"{prefix}.{name}")
            if interval.period.start != previous_end or interval.period.end > data.context.period.end:
                p.issue(IssueCode.INCOMPARABLE_BASELINE, prefix + ".period",
                        "Intervals must be ordered, contiguous and within the comparison period")
            previous_end = interval.period.end
            if interval.self_consumed_solar.value > interval.baseline_grid_import.value:
                p.issue(IssueCode.CONFLICTING_INPUT, prefix + ".self_consumed_solar",
                        "Self-consumed solar cannot exceed matching baseline grid imports")
        if previous_end != data.context.period.end:
            p.issue(IssueCode.INCOMPARABLE_BASELINE, "intervals", "Cover the complete comparison period, including zero intervals")
        if p.issues:
            return p.finish()
        with localcontext(Context(prec=60)):
            imports = sum((i.baseline_grid_import.value for i in data.intervals), Decimal(0))
            solar = sum((i.self_consumed_solar.value for i in data.intervals), Decimal(0))
            grid = p.grid_value
            baseline = imports * grid
            scenario = (imports - solar) * grid
        return p.finish(baseline, scenario)
