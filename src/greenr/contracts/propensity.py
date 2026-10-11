"""Propensity, confidence and reason-code contracts (Agent A outputs)."""

from datetime import date, datetime

from pydantic import Field, model_validator

from greenr.contracts.base import CONTRACT_VERSION, Contract, Probability
from greenr.contracts.customer import FeatureScalar
from greenr.contracts.enums import (
    ConfidenceBucket,
    ConfidenceStatus,
    ModelType,
    PopulationExclusion,
    Product,
    ReasonCode,
)


class ConfidenceResult(Contract):
    """Validated reliability of a displayed propensity (spec 16). Not eligibility."""

    status: ConfidenceStatus
    value: Probability | None = None
    bucket: ConfidenceBucket | None = None
    method_version: str
    limitation: str | None = None

    @model_validator(mode="after")
    def _suppressed_has_no_value(self) -> "ConfidenceResult":
        if self.status is ConfidenceStatus.SUPPRESSED:
            if self.value is not None or self.bucket is not None:
                raise ValueError("suppressed confidence must not carry a value or bucket")
            if not self.limitation:
                raise ValueError("suppressed confidence must state its limitation")
        elif self.value is None or self.bucket is None:
            raise ValueError("validated confidence requires value and bucket")
        return self


class PropensityResult(Contract):
    """Calibrated take-up probability for one customer x product.

    Propensity estimates interest only. It does not estimate impact or eligibility.
    """

    contract_version: str = CONTRACT_VERSION
    customer_id: str
    product: Product
    propensity: Probability  # calibrated probability; the only value shown to users
    raw_score: float  # uncalibrated model output, audit only
    model_type: ModelType
    model_version: str
    calibration_method: str
    calibration_version: str
    feature_version: str
    feature_cutoff: date
    outcome_window_end: date
    prediction_timestamp: datetime
    in_model_population: bool
    population_exclusion: PopulationExclusion | None = None
    reason_codes: list[ReasonCode] = Field(default_factory=list)
    evidence: dict[str, FeatureScalar] = Field(default_factory=dict)
    confidence: ConfidenceResult

    @model_validator(mode="after")
    def _population_consistency(self) -> "PropensityResult":
        if self.in_model_population == (self.population_exclusion is not None):
            raise ValueError("population_exclusion must be set iff in_model_population is False")
        return self


class ReasonCodeDefinition(Contract):
    """Catalogue entry for a controlled reason code (spec 18)."""

    code: ReasonCode
    customer_wording: str
    rm_wording: str
    derivation: str
    threshold: float | None = None
    threshold_unit: str | None = None
    evidence_fields: list[str]
    applicable_products: list[Product]
    version: str
