"""Canonical deterministic impact evidence and provenance for the product API."""

from datetime import date, datetime
from decimal import Context, Decimal, InvalidOperation, localcontext
from enum import StrEnum
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from greenpath.contracts.base import CONTRACT_VERSION
from greenpath.contracts.enums import ImpactStatus, Product


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class IssueCode(StrEnum):
    MISSING_INPUT = "MISSING_INPUT"
    INVALID_INPUT = "INVALID_INPUT"
    CONFLICTING_INPUT = "CONFLICTING_INPUT"
    STALE_INPUT = "STALE_INPUT"
    UNSUPPORTED_SCOPE = "UNSUPPORTED_SCOPE"
    FACTOR_NOT_ESTABLISHED = "FACTOR_NOT_ESTABLISHED"
    INCOMPARABLE_BASELINE = "INCOMPARABLE_BASELINE"


class ImpactIssue(Model):
    code: IssueCode
    field: str
    message: str


class Period(Model):
    """Inclusive start, exclusive end. Dates are explicit, not epoch numbers."""

    start: date
    end: date

    @field_validator("start", "end", mode="before")
    @classmethod
    def explicit_dates(cls, value):
        if isinstance(value, datetime) or not isinstance(value, (date, str)):
            raise ValueError("Use an ISO date or a date object, not a timestamp")
        if isinstance(value, str):
            parsed = date.fromisoformat(value)
            if parsed.isoformat() != value:
                raise ValueError("Use an explicit YYYY-MM-DD date")
            return parsed
        return value

    @model_validator(mode="after")
    def ordered(self):
        if self.end <= self.start:
            raise ValueError("Period end must be after start")
        return self


class FactorReference(Model):
    factor_id: str
    value: Decimal
    unit: str
    original_value: Decimal
    original_unit: str
    geography: str
    fuel: str | None = None
    activity_period: str | None = None
    boundary: str
    applicability: str
    source_id: str
    source_url: str
    source_title: str
    source_publisher: str
    source_edition: str
    source_locator: str
    source_sha256: str | None
    verification_basis: str
    source_limitation: str | None = None


class ActivityEvidence(Model):
    field: str
    value: Decimal | str | bool
    unit: str | None = None
    reference: str
    basis: str
    observed_at: AwareDatetime
    period: Period
    freshness: str
    conflicts: tuple[str, ...] = ()

    @model_validator(mode="before")
    @classmethod
    def restore_quantity_decimal(cls, data):
        # JSON encodes decimals as strings; the unit identifies numeric activity.
        if isinstance(data, dict) and data.get("unit") is not None:
            data = dict(data)
            if isinstance(data.get("value"), bool):
                raise ValueError("Quantity evidence cannot contain a boolean value")
            try:
                data["value"] = Decimal(str(data["value"]))
            except (InvalidOperation, KeyError) as exc:
                raise ValueError("Quantity evidence requires a valid decimal value") from exc
        return data


class EmissionsScenario(Model):
    description: str
    emissions_kg_co2: Decimal | None = Field(default=None, ge=0)
    emissions_kg_co2e: Decimal | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def exclusive_emissions(self):
        if self.emissions_kg_co2 is not None and self.emissions_kg_co2e is not None:
            raise ValueError("Scenario emissions must be CO2 or CO2e, not both")
        return self


ImpactUnit = Literal["kg CO2", "kg CO2/year", "kg CO2e/year"]


class ImpactResult(Model):
    contract_version: str = CONTRACT_VERSION
    product: Product
    status: ImpactStatus
    value: Decimal | None = None
    units: ImpactUnit = "kg CO2"
    baseline: EmissionsScenario
    scenario: EmissionsScenario
    period: Period | None = None
    feature_cutoff: AwareDatetime | None = None
    synthetic_demo: bool | None = None
    factors: tuple[FactorReference, ...] = ()
    factor_catalogue_version: str
    factor_catalogue_sha256: str
    boundary: str
    assumptions: tuple[str, ...]
    exclusions: tuple[str, ...]
    method_version: str
    method_release: str
    timestamp: AwareDatetime
    evidence: tuple[ActivityEvidence, ...] = ()
    issues: tuple[ImpactIssue, ...] = ()

    @model_validator(mode="after")
    def consistent_status(self):
        co2e = self.units == "kg CO2e/year"
        for item in (self.baseline, self.scenario):
            mismatched = item.emissions_kg_co2 if co2e else item.emissions_kg_co2e
            if mismatched is not None:
                raise ValueError("Scenario emissions must match impact units")
        baseline = self.baseline.emissions_kg_co2e if co2e else self.baseline.emissions_kg_co2
        scenario = self.scenario.emissions_kg_co2e if co2e else self.scenario.emissions_kg_co2
        if self.status == ImpactStatus.AVAILABLE:
            if any(v is None for v in (self.value, baseline, scenario)):
                raise ValueError("Available impact requires value and both emissions")
            if (self.issues or not self.factors or self.period is None
                    or self.feature_cutoff is None or self.synthetic_demo is not True):
                raise ValueError("Available impact requires factors, context and no issues")
            with localcontext(Context(prec=60)):
                if self.value != baseline - scenario:
                    raise ValueError("Impact must equal baseline minus scenario")
        elif any(v is not None for v in (self.value, baseline, scenario)) or not self.issues:
            raise ValueError("Unavailable impact requires null numbers and specific issues")
        return self
