"""Replaceable local mirror of the proposed ImpactCalculator port."""

from typing import Protocol

from ._contract_mirror import ImpactResult, Product
from .common import Payload


class ImpactCalculator(Protocol):
    product: Product

    def calculate(self, payload: Payload) -> ImpactResult: ...
