"""Canonical Greenr contracts (Agent A is the contract authority).

Import from here, not from submodules, so the public surface stays stable.
"""

from greenr.contracts.base import CONTRACT_VERSION, Contract, Probability
from greenr.contracts.customer import (
    CustomerSnapshot,
    DataQualityEvidence,
    DigitalFacts,
    EnergyFacts,
    FeatureScalar,
    HomeFacts,
    SpendFacts,
    VehicleFacts,
)
from greenr.contracts.enums import (
    PRODUCT_IDS,
    ConfidenceBucket,
    ConfidenceStatus,
    EligibilityStatus,
    ExplanationSource,
    FuelType,
    GroundingResult,
    HeatingType,
    ImpactStatus,
    ModelType,
    PopulationExclusion,
    Product,
    ReasonCode,
    RecommendationState,
    Severity,
    TransactionCategory,
    TrustIssueCategory,
    TrustIssueCode,
    TrustStatus,
)
from greenr.contracts.impact import ImpactAssumption, ImpactMetric, ImpactResult
from greenr.contracts.propensity import ConfidenceResult, PropensityResult, ReasonCodeDefinition
from greenr.contracts.recommendation import (
    ELIGIBILITY_MESSAGE,
    Eligibility,
    Explanation,
    PortfolioSummary,
    PortfolioTrends,
    Priority,
    PriorityComponents,
    ProductSummary,
    Recommendation,
    SegmentRow,
    TrendPoint,
)
from greenr.contracts.trust import TrustAssessment, TrustIssue
from greenr.contracts.lifecycle import SourceUpdateRequest

from types import ModuleType as _ModuleType

__all__ = [n for n, v in list(globals().items()) if not n.startswith("_") and not isinstance(v, _ModuleType)]
