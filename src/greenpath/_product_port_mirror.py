"""Replaceable narrow ports for the Agent B demo; canonical integration pending."""

from typing import Mapping, Protocol

from ._product_contract_mirror import CustomerSnapshot, HistoryRecord, PropensityResult
from .impact import Product


class CustomerSnapshotProvider(Protocol):
    def get_snapshot(self, customer_id: str) -> CustomerSnapshot | None: ...

    def list_snapshots(self) -> tuple[CustomerSnapshot, ...]: ...


class PropensityProvider(Protocol):
    def get_propensity(self, customer_id: str, product: Product) -> PropensityResult | None: ...


class ImpactInputProvider(Protocol):
    def get_impact_input(self, customer_id: str, product: Product) -> Mapping[str, object] | None: ...


class PortfolioHistoryProvider(Protocol):
    def list_history(self) -> tuple[HistoryRecord, ...]: ...
