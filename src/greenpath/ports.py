"""Narrow cross-workstream ports (spec: Interface Segregation / Dependency Inversion).

Use cases depend on these protocols; concrete models, storage, LLM clients and UI
frameworks are injected at the application boundary.
"""

from collections.abc import Mapping, Sequence
from datetime import date
from typing import Protocol, runtime_checkable

from greenpath.contracts import (
    CustomerSnapshot,
    Explanation,
    ImpactResult,
    Product,
    PropensityResult,
    Recommendation,
    TrustAssessment,
)


@runtime_checkable
class CustomerSnapshotProvider(Protocol):
    """Implemented by Agent A (pipelines.snapshot_provider)."""

    def list_customer_ids(self) -> list[str]: ...

    def get_snapshot(self, customer_id: str, cutoff: date | None = None) -> CustomerSnapshot | None:
        """Return the snapshot at ``cutoff`` (default: canonical cutoff) or None if unknown."""
        ...


@runtime_checkable
class PropensityProvider(Protocol):
    """Implemented by Agent A (models.propensity.provider).

    Scoring reads only ``snapshot.features``; edit that mapping for sensitivity analysis.
    """

    def score(self, snapshot: CustomerSnapshot, product: Product) -> PropensityResult: ...

    def score_many(self, snapshots: Sequence[CustomerSnapshot], product: Product) -> list[PropensityResult]: ...


@runtime_checkable
class TrustProvider(Protocol):
    """Implemented by Agent A (trust.provider)."""

    def assess(self, snapshot: CustomerSnapshot, product: Product) -> TrustAssessment: ...


@runtime_checkable
class ImpactCalculator(Protocol):
    """Implemented by Agent B, one calculator per product."""

    product: Product

    def calculate(self, snapshot: CustomerSnapshot) -> ImpactResult: ...


@runtime_checkable
class ExplanationProvider(Protocol):
    """Implemented by Agent B (LLM adapter or deterministic template)."""

    def explain(self, recommendation: Recommendation, locale: str = "en-GB") -> Explanation: ...


# The product/API view is an explicit adapter boundary, rather than a second
# scoring contract. These ports retain A's numeric feature view above and B's
# independently validated impact input below.
from greenpath.contracts.product import (
    CustomerSnapshot as ProductSnapshot,
    HistoryRecord,
    PropensityResult as ProductPropensityResult,
)
from greenpath.contracts.impact_detail import ImpactResult as DetailedImpactResult


class ProductSnapshotProvider(Protocol):
    def get_snapshot(self, customer_id: str) -> ProductSnapshot | None: ...

    def list_snapshots(self) -> tuple[ProductSnapshot, ...]: ...


class ProductPropensityProvider(Protocol):
    def get_propensity(self, customer_id: str, product: Product) -> ProductPropensityResult | None: ...


class ImpactInputProvider(Protocol):
    def get_impact_input(self, customer_id: str, product: Product) -> Mapping[str, object] | None: ...


class PortfolioHistoryProvider(Protocol):
    def list_history(self) -> tuple[HistoryRecord, ...]: ...


class ProductImpactCalculator(Protocol):
    product: Product

    def calculate(self, payload: Mapping[str, object] | object | None) -> DetailedImpactResult: ...
