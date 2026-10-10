"""Canonical product decision/API view, with explicit ML-source evidence adapters.

The scoring view in customer.py retains numeric model features. This view contains
validated Boolean relevance evidence and deterministic impact provenance.
"""

from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, Field, StrictBool, model_validator

from greenpath.contracts.base import CONTRACT_VERSION
from greenpath.contracts.customer import CustomerSnapshot as ScoringSnapshot
from greenpath.contracts.enums import Product, RecommendationState
from greenpath.contracts.impact_detail import ImpactResult, Model
from greenpath.contracts.propensity import PropensityResult as ScoringResult
from greenpath.contracts.trust import TrustAssessment as ScoringTrust

ELIGIBILITY_DISCLAIMER = "This is a synthetic demonstration of product relevance, not a credit eligibility or approval decision."
APPROVED_FEATURES = frozenset({
    "marketing_consent", "owns_vehicle", "ev_interest", "fuel_supported", "already_has_ev",
    "owns_home", "retrofit_interest", "efficient_home", "roof_available", "solar_interest",
    "solar_installed", "paper_statements", "paperless_consent", "paperless_active",
})


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
    source_assessment: ScoringTrust | None = None


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
    decision_profile: Literal["fixture", "trained"] = "fixture"
    product_trust: dict[Product, TrustAssessment] = Field(default_factory=dict)
    source_snapshot: ScoringSnapshot | None = None

    @model_validator(mode="after")
    def approved_features_only(self):
        if self.source_snapshot is not None and (self.source_snapshot.customer_id != self.customer_id
                or self.source_snapshot.feature_cutoff != self.feature_cutoff.date()):
            raise ValueError("ML source snapshot must match customer and cutoff")
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
    in_model_population: StrictBool = True
    population_exclusion: str | None = None
    decision_threshold: Decimal = Field(default=Decimal("0.60"), ge=0, le=1)
    source_result: ScoringResult | None = None

    @model_validator(mode="after")
    def matching_scoring_evidence(self):
        source = self.source_result
        if source is not None:
            if (source.product != self.product or source.model_version != self.model_version
                    or source.calibration_version != self.calibration_version
                    or source.in_model_population != self.in_model_population):
                raise ValueError("Propensity adapter must retain matching model/calibration/population evidence")
            if self.probability != (Decimal(str(source.propensity)) if source.in_model_population else None):
                raise ValueError("Displayed propensity must be the calibrated source probability")
            validated = source.confidence.status.value == "VALIDATED"
            if self.confidence_validated != validated or self.confidence != (Decimal(str(source.confidence.value)) if validated else None):
                raise ValueError("Displayed confidence must retain the source validation gate")
        return self


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
    customers_with_opportunity: int = 0
    high_confidence_opportunities: int = 0
    validated_confidence_opportunities: int = 0
    high_trust_opportunities: int = 0
    funnel_counts: dict[str, int] = Field(default_factory=dict)
    funnel_limitation: str = "Counts refer to synthetic evidence; unavailable priority or impact components are not inferred."
    synthetic_demo: Literal[True] = True
    disclaimer: str = "Synthetic-data decision counts; potential opportunities are not realized reductions. No cross-product carbon total is calculated."


class HistoryRecord(Model):
    customer_id: str
    month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    product: Product
    state: RecommendationState
    propensity: Decimal | None = Field(default=None, ge=0, le=1)
    confidence: Decimal | None = Field(default=None, ge=0, le=1)
    trust_score: Decimal | None = Field(default=None, ge=0, le=1)
    observed_adoption_90d: int | None = Field(default=None, ge=0, le=1)
    confidence_high: StrictBool | None = None
    is_paperless: StrictBool | None = None


class TrendPoint(Model):
    month: str
    product: Product
    customer_count: int
    recommended_count: int
    state_counts: dict[str, int]


    high_confidence_opportunity_share: Decimal | None = None
    high_confidence_opportunity_count: int = 0
    validated_confidence_opportunity_count: int = 0
    paperless_observed_count: int = 0
    paperless_active_count: int | None = None
    paperless_adoption_rate: Decimal | None = None
    average_propensity: Decimal | None = None
    average_validated_confidence: Decimal | None = None
    validated_confidence_count: int = 0
    average_trust: Decimal | None = None
    abstained_count: int = 0
    observed_outcome_count: int = 0
    observed_adoptions_90d: int | None = None


class PortfolioTrends(Model):
    observations: tuple[TrendPoint, ...]
    synthetic_demo: Literal[True] = True
    disclaimer: str = "Historical states use synthetic evidence. Trained trends retrospectively apply the current model to each monthly feature cutoff; they are not observed customer behavior."
