"""ImpactResult: output of a deterministic sustainability calculator (Agent B implements)."""

from datetime import date, datetime

from pydantic import Field, model_validator

from greenpath.contracts.base import CONTRACT_VERSION, Contract
from greenpath.contracts.enums import ImpactStatus, Product


class ImpactAssumption(Contract):
    name: str
    value: float | str | bool
    unit: str | None = None
    source: str | None = None
    is_estimated: bool = False


class ImpactMetric(Contract):
    """Non-carbon outcome measure, e.g. paper statements avoided per year."""

    name: str
    value: float
    unit: str


class ImpactResult(Contract):
    contract_version: str = CONTRACT_VERSION
    customer_id: str
    product: Product
    status: ImpactStatus
    metric: str | None = None  # e.g. "kg_co2e_per_year"
    unit: str | None = None
    baseline: float | None = None
    scenario: float | None = None
    estimated_reduction: float | None = None
    secondary_metrics: list[ImpactMetric] = Field(default_factory=list)
    methodology_id: str | None = None
    method_version: str
    factor_ids: list[str] = Field(default_factory=list)
    factor_source: str | None = None
    factor_version: str | None = None
    boundary: str | None = None
    grid_scenario: str | None = None
    assumptions: list[ImpactAssumption] = Field(default_factory=list)
    unavailable_reason: str | None = None
    data_cutoff: date
    calculation_timestamp: datetime
    carbon_engine_version: str

    @model_validator(mode="after")
    def _status_consistency(self) -> "ImpactResult":
        carbon = (self.baseline, self.scenario, self.estimated_reduction)
        if self.status is ImpactStatus.AVAILABLE:
            if any(v is None for v in carbon) or not all(
                (self.metric, self.unit, self.methodology_id, self.factor_source,
                 self.factor_version, self.boundary)
            ):
                raise ValueError("AVAILABLE impact requires values, units, method, factor source/version and boundary")
            if not self.factor_ids:
                raise ValueError("AVAILABLE impact requires factor_ids (spec 21)")
            if abs(self.baseline - self.scenario - self.estimated_reduction) > 1e-6 * max(1.0, abs(self.baseline)):
                raise ValueError("estimated_reduction must equal baseline - scenario")
        else:
            if any(v is not None for v in carbon):
                raise ValueError(f"{self.status} impact must not carry carbon numbers")
            if self.status is ImpactStatus.UNAVAILABLE and not self.unavailable_reason:
                raise ValueError("UNAVAILABLE impact requires unavailable_reason")
        return self
