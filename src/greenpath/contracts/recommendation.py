"""Canonical structured recommendation object (spec 5), plus explanation and portfolio payloads."""

from datetime import date, datetime
from typing import Literal

from pydantic import Field, model_validator

from greenpath.contracts.base import CONTRACT_VERSION, Contract, Probability
from greenpath.contracts.customer import FeatureScalar
from greenpath.contracts.enums import (
    PRODUCT_IDS,
    EligibilityStatus,
    ExplanationSource,
    GroundingResult,
    Product,
    ReasonCode,
    RecommendationState,
)
from greenpath.contracts.impact import ImpactResult
from greenpath.contracts.propensity import ConfidenceResult
from greenpath.contracts.trust import TrustAssessment

ELIGIBILITY_MESSAGE = "Propensity does not establish financial eligibility."


class Eligibility(Contract):
    status: Literal[EligibilityStatus.NOT_ASSESSED] = EligibilityStatus.NOT_ASSESSED
    message: str = ELIGIBILITY_MESSAGE


class PriorityComponents(Contract):
    propensity: Probability
    confidence: Probability | None
    normalised_impact: Probability | None
    trust: Probability


class Priority(Contract):
    rank: int = Field(ge=1)
    score: Probability
    version: str
    components: PriorityComponents


class Recommendation(Contract):
    contract_version: str = CONTRACT_VERSION
    recommendation_id: str
    customer_id: str
    opportunity_id: Product
    product_id: str
    propensity: Probability
    propensity_model_version: str
    calibration_version: str
    confidence: ConfidenceResult
    trust: TrustAssessment
    recommendation_status: RecommendationState
    guardrail_codes: list[str] = Field(default_factory=list)
    conflict_codes: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    priority: Priority | None = None
    reason_codes: list[ReasonCode] = Field(default_factory=list)
    evidence: dict[str, FeatureScalar] = Field(default_factory=dict)
    impact: ImpactResult | None = None
    eligibility: Eligibility = Field(default_factory=Eligibility)
    data_cutoff: date
    outcome_window_end: date
    prediction_timestamp: datetime
    feature_version: str
    confidence_method_version: str
    trust_method_version: str
    carbon_engine_version: str | None = None
    emission_factor_version: str | None = None
    recommendation_rule_version: str
    prompt_version: str | None = None
    llm_model_version: str | None = None

    @model_validator(mode="after")
    def _product_mapping(self) -> "Recommendation":
        if PRODUCT_IDS[self.opportunity_id] != self.product_id:
            raise ValueError("product_id does not match opportunity_id")
        if self.trust.product is not self.opportunity_id:
            raise ValueError("trust assessment is for a different product")
        if self.impact is not None and self.impact.product is not self.opportunity_id:
            raise ValueError("impact result is for a different product")
        return self

    @model_validator(mode="after")
    def _fail_closed(self) -> "Recommendation":
        state = self.recommendation_status
        if state is RecommendationState.RECOMMEND and (
            not self.trust.critical_fields_present or self.trust.has_high_severity_conflict
        ):
            raise ValueError("RECOMMEND is not allowed with missing critical fields or a high-severity conflict")
        if state is RecommendationState.CONFLICT_REQUIRES_REVIEW and not self.conflict_codes:
            raise ValueError("CONFLICT_REQUIRES_REVIEW requires conflict_codes")
        return self


class Explanation(Contract):
    """LLM structured output (spec 38) plus provenance of how it was produced."""

    contract_version: str = CONTRACT_VERSION
    recommendation_id: str
    headline: str
    explanation: str
    why_recommended: list[str] = Field(default_factory=list)
    estimated_impact_text: str | None = None
    confidence_text: str | None = None
    action_text: str
    eligibility_disclaimer: str
    missing_information: list[str] = Field(default_factory=list)
    source: ExplanationSource
    grounding_result: GroundingResult
    prompt_version: str
    llm_model_version: str | None = None
    cache_key: str | None = None
    generated_at: datetime


class ProductSummary(Contract):
    product: Product
    candidates: int = Field(ge=0)
    actionable: int = Field(ge=0)
    high_confidence: int = Field(ge=0)
    high_trust: int = Field(ge=0)
    suppressed_or_abstained: int = Field(ge=0)
    estimated_impact_kg_co2e: float | None = None


class PortfolioSummary(Contract):
    contract_version: str = CONTRACT_VERSION
    data_cutoff: date
    generated_at: datetime
    customers_analysed: int = Field(ge=0)
    customers_with_opportunity: int = Field(ge=0)
    by_product: list[ProductSummary]
    synthetic_data_notice: str = "Synthetic demonstration data; not evidence of real-world performance."


class SegmentRow(Contract):
    dimension: str  # e.g. "region", "segment", "home_owner"
    segment: str
    product: Product
    customers: int = Field(ge=0)
    opportunities: int = Field(ge=0)
    avg_propensity: Probability | None = None
    estimated_impact_kg_co2e: float | None = None


class TrendPoint(Contract):
    month: date  # month-end feature cutoff
    product: Product
    opportunities: int = Field(ge=0)
    avg_propensity: Probability | None = None
    high_confidence_share: Probability | None = None
    estimated_impact_kg_co2e: float | None = None
    suppression_or_conflict_rate: Probability | None = None
    avg_trust: Probability | None = None
    observed_conversion_rate: Probability | None = None
    paperless_adoption_rate: Probability | None = None


class PortfolioTrends(Contract):
    contract_version: str = CONTRACT_VERSION
    points: list[TrendPoint]
    causality_disclaimer: str = "Trends are descriptive; they do not establish causality."
