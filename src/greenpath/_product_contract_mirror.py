"""Agent B handoff mirrors, not Agent A's canonical contracts. Replace at integration."""

from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import AwareDatetime, Field, StrictBool, model_validator

from greenpath.impact._contract_mirror import ImpactResult, Model, Product

CONTRACT_VERSION = "agent-b-product-mirror-v0.1"
ELIGIBILITY_DISCLAIMER = "This is a synthetic demonstration of product relevance, not a credit eligibility or approval decision."
APPROVED_FEATURES = frozenset({
    "marketing_consent", "owns_vehicle", "ev_interest", "fuel_supported", "already_has_ev",
    "owns_home", "retrofit_interest", "efficient_home", "roof_available", "solar_interest",
    "solar_installed", "paper_statements", "paperless_consent", "paperless_active",
})


class RecommendationState(StrEnum):
    RECOMMEND = "RECOMMEND"
    DO_NOT_RECOMMEND = "DO_NOT_RECOMMEND"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"
    CONFLICT_REQUIRES_REVIEW = "CONFLICT_REQUIRES_REVIEW"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    SUPPRESSED = "SUPPRESSED"


class FeatureEvidence(Model):
    value: StrictBool | None = None
    reference: str = Field(min_length=1)
    observed_at: AwareDatetime
    freshness: Literal["current", "stale", "unknown"]
    conflicts: tuple[str, ...] = ()


class TrustIssue(Model):
    code: str
    field: str
    severity: Literal["INFO", "WARNING", "HIGH"]
    message: str


class TrustAssessment(Model):
    score: Decimal = Field(ge=0, le=1)
    status: Literal["TRUSTED", "LIMITED", "CONFLICT", "OOD"]
    issues: tuple[TrustIssue, ...] = ()
    version: str = "demo-trust-fixture-v1"


class CustomerSnapshot(Model):
    customer_id: str
    display_name: str
    region: str
    segment: str
    feature_cutoff: AwareDatetime
    features: dict[str, FeatureEvidence]
    trust: TrustAssessment
    synthetic_demo: Literal[True] = True
    contract_version: str = CONTRACT_VERSION

    @model_validator(mode="after")
    def approved_features_only(self):
        if set(self.features) - APPROVED_FEATURES:
            raise ValueError("Only approved relevance features belong in the demo snapshot")
        return self


class PropensityResult(Model):
    product: Product
    probability: Decimal | None = Field(default=None, ge=0, le=1)
    model_version: str
    calibration_version: str | None = None
    reason_codes: tuple[str, ...] = ()
    confidence: Decimal | None = Field(default=None, ge=0, le=1)
    confidence_validated: StrictBool = False
    synthetic_demo: Literal[True] = True


class DecisionEvidence(Model):
    code: str
    message: str
    fields: tuple[str, ...] = ()
    references: tuple[str, ...] = ()


class Recommendation(Model):
    customer_id: str
    product: Product
    propensity: PropensityResult | None
    state: RecommendationState
    reason_codes: tuple[str, ...]
    evidence: tuple[DecisionEvidence, ...]
    exclusions: tuple[str, ...] = ()
    impact: ImpactResult
    trust: TrustAssessment
    feature_cutoff: AwareDatetime
    rules_version: str
    timestamp: AwareDatetime
    eligibility_disclaimer: str = ELIGIBILITY_DISCLAIMER
    synthetic_demo: Literal[True] = True
    contract_version: str = CONTRACT_VERSION


class Explanation(Model):
    customer_id: str
    product: Product
    state: RecommendationState
    text: str
    reason_codes: tuple[str, ...]
    impact_value: Decimal | None = None
    units: str
    source: Literal["template", "llm"]
    provider_version: str
    validation_passed: StrictBool
    fallback_reason: str | None = None
    eligibility_disclaimer: str = ELIGIBILITY_DISCLAIMER
    contract_version: str = CONTRACT_VERSION


class RecommendationsResponse(Model):
    customer_id: str
    recommendations: tuple[Recommendation, ...]


class ProductOpportunity(Model):
    product: Product
    total: int
    recommended: int
    state_counts: dict[str, int]
    available_impact_count: int


class GroupSummary(Model):
    name: str
    customer_count: int
    recommended_count: int


class PortfolioSummary(Model):
    total_customers: int
    total_recommendations: int
    recommended_count: int
    state_counts: dict[str, int]
    product_opportunities: tuple[ProductOpportunity, ...]
    region_summaries: tuple[GroupSummary, ...]
    segment_summaries: tuple[GroupSummary, ...]
    available_impact_count: int
    synthetic_demo: Literal[True] = True
    disclaimer: str = "Synthetic fixture counts; potential opportunities are not realized reductions. No cross-product carbon total is calculated."


class HistoryRecord(Model):
    customer_id: str
    month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    product: Product
    state: RecommendationState


class TrendPoint(Model):
    month: str
    product: Product
    customer_count: int
    recommended_count: int
    state_counts: dict[str, int]


class PortfolioTrends(Model):
    observations: tuple[TrendPoint, ...]
    synthetic_demo: Literal[True] = True
    disclaimer: str = "Historical states are synthetic fixtures, not predictions of real customer behavior."
