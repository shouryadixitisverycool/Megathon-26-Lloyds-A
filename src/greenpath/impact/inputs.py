"""Impact-owned evidence inputs; adapter mapping to CustomerSnapshot is pending."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Generic, TypeVar

from pydantic import AwareDatetime, Field, StrictBool, field_validator

from ._contract_mirror import Model, Period

NonBlank = Annotated[str, Field(min_length=1, pattern=r"\S")]
T = TypeVar("T")


class EvidenceBasis(StrEnum):
    SYNTHETIC_DEMO = "synthetic_demo"
    METER_READING = "meter_reading"
    CUSTOMER_DECLARATION = "customer_declaration"
    ENGINEERING_FORECAST = "engineering_forecast"


class Freshness(StrEnum):
    CURRENT = "current"
    STALE = "stale"
    UNKNOWN = "unknown"


ComparisonPeriod = Period


class Evidence(Model):
    reference: NonBlank
    basis: EvidenceBasis
    observed_at: AwareDatetime
    period: ComparisonPeriod
    freshness: Freshness
    conflicts: tuple[NonBlank, ...] = ()

    @field_validator("observed_at", mode="before")
    @classmethod
    def explicit_timestamp(cls, value):
        if not isinstance(value, (datetime, str)):
            raise ValueError("Use a timezone-aware timestamp, not an epoch number")
        return value


class Fact(Model, Generic[T]):
    value: T
    evidence: Evidence


class Quantity(Fact[Decimal]):
    value: Decimal = Field(ge=0, max_digits=24, decimal_places=12)
    unit: NonBlank

    @field_validator("value", mode="before")
    @classmethod
    def numeric_value(cls, value):
        if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
            raise ValueError("Quantity must be a number or decimal string, never a boolean")
        # Decimal(str(float)) avoids importing binary float error into the formula.
        return str(value) if isinstance(value, float) else value


class ImpactContext(Model):
    period: ComparisonPeriod
    feature_cutoff: AwareDatetime
    geography: NonBlank
    synthetic_demo: StrictBool

    _explicit_cutoff = field_validator("feature_cutoff", mode="before")(
        Evidence.explicit_timestamp.__func__
    )


class ImpactInput(Model):
    context: ImpactContext


class EVInput(ImpactInput):
    baseline_fuel: Fact[NonBlank]
    baseline_fuel_mass: Quantity | None = None
    baseline_fuel_volume: Quantity | None = None
    baseline_fuel_density: Quantity | None = None
    baseline_distance: Quantity
    scenario_distance: Quantity
    charging_electricity: Quantity
    charging_measurement_point: Fact[NonBlank]
    baseline_powertrain: Fact[NonBlank]
    scenario_powertrain: Fact[NonBlank]
    replaces_baseline: Fact[StrictBool]
    charging_supply: Fact[NonBlank]


class GreenHomeInput(ImpactInput):
    baseline_grid_import: Quantity
    scenario_grid_import: Quantity
    same_home: Fact[StrictBool]
    comparable_service: Fact[StrictBool]
    comparability_basis: Fact[NonBlank]
    efficiency_assessment: Fact[NonBlank]
    fuel_use_unchanged: Fact[StrictBool]
    onsite_generation_unchanged: Fact[StrictBool]


class SolarInterval(Model):
    period: ComparisonPeriod
    baseline_grid_import: Quantity
    self_consumed_solar: Quantity
    exported_solar: Quantity | None = None


class SolarInput(ImpactInput):
    intervals: Annotated[tuple[SolarInterval, ...], Field(min_length=1, max_length=10000)]
    demand_unchanged: Fact[StrictBool]
    storage_used: Fact[StrictBool]
    displaces_grid_only: Fact[StrictBool]
    measurement_point: Fact[NonBlank]


class PaperlessInput(ImpactInput):
    avoided_sheets: Quantity | None = None
