"""Controlled decision vocabulary. Provider prose never becomes a decision reason."""

from types import MappingProxyType

REASON_MESSAGES = MappingProxyType({
    "MARKETING_CONSENT_WITHDRAWN": "Current evidence records no marketing consent; contact is suppressed.",
    "EVIDENCE_CONFLICT": "Relevant evidence has an unresolved conflict and requires review.",
    "OUT_OF_DISTRIBUTION": "The snapshot is outside the supported model population; relevance is not determined.",
    "FUTURE_FEATURE_CUTOFF": "The feature cutoff is after the decision time; relevance is not determined.",
    "MISSING_EVIDENCE": "A required relevance or consent field has no usable evidence.",
    "STALE_EVIDENCE": "A required relevance or consent field is not current.",
    "FUTURE_EVIDENCE": "A required evidence observation is after the feature cutoff.",
    "TRUST_LIMITATION": "A high-severity data-quality limitation prevents determining relevance.",
    "ALREADY_ADOPTED": "Current evidence records that the customer already uses this product or improvement.",
    "VEHICLE_REQUIRED": "Current evidence does not support vehicle ownership for this opportunity.",
    "FUEL_UNSUPPORTED": "Current evidence records fuel outside the supported EV comparison.",
    "HOME_REQUIRED": "Current evidence does not support home ownership for this opportunity.",
    "ROOF_UNAVAILABLE": "Current evidence records no available roof for this solar opportunity.",
    "NO_PAPER_STATEMENTS": "Current evidence records no paper statements to replace.",
    "PAPERLESS_CONSENT_WITHDRAWN": "Current evidence records no consent to switch to paperless statements.",
    "INTEREST_NOT_SUPPORTED": "Current evidence does not support interest in this opportunity.",
    "PROPENSITY_UNAVAILABLE": "A matching propensity probability and model version are unavailable.",
    "PROPENSITY_BELOW_THRESHOLD": "The synthetic propensity probability is below the demo relevance threshold.",
    "RELEVANCE_SUPPORTED": "Current product-specific evidence supports the relevance of this opportunity.",
    "PROPENSITY_THRESHOLD_MET": "The synthetic propensity probability meets the demo relevance threshold.",
})
