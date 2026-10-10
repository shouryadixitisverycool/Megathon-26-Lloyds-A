"""Product registration; no product branching in calling code."""

from ._contract_mirror import Product
from ._port_mirror import ImpactCalculator
from .catalogue import FactorCatalogue
from .common import Clock, utc_now
from .ev import EVImpactCalculator
from .green_home import GreenHomeImpactCalculator
from .paperless import PaperlessImpactCalculator
from .solar import SolarImpactCalculator

CALCULATOR_TYPES = (EVImpactCalculator, GreenHomeImpactCalculator,
                    SolarImpactCalculator, PaperlessImpactCalculator)


def build_registry(*, catalogue: FactorCatalogue | None = None,
                   clock: Clock = utc_now) -> dict[Product, ImpactCalculator]:
    catalogue = catalogue if catalogue is not None else FactorCatalogue.load()
    return {cls.product: cls(catalogue=catalogue, clock=clock) for cls in CALCULATOR_TYPES}
