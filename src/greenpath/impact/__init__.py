"""Agent B's standalone impact package. Canonical contract integration is pending."""

from ._contract_mirror import ImpactResult, ImpactStatus, IssueCode, Product
from .common import display_value
from .ev import EVImpactCalculator
from .green_home import GreenHomeImpactCalculator
from .inputs import EVInput, GreenHomeInput, PaperlessInput, SolarInput
from .paperless import PaperlessImpactCalculator
from .registry import build_registry
from .solar import SolarImpactCalculator

__all__ = [
    "EVImpactCalculator", "GreenHomeImpactCalculator", "SolarImpactCalculator",
    "PaperlessImpactCalculator", "EVInput", "GreenHomeInput", "SolarInput",
    "PaperlessInput", "ImpactResult", "ImpactStatus", "IssueCode", "Product",
    "build_registry", "display_value",
]
