"""Relevance rules using Agent B's replaceable contract and provider mirrors."""

from .reasons import REASON_MESSAGES
from .service import DEMO_PROPENSITY_THRESHOLD, PRODUCT_RULES, RULES_VERSION, RecommendationService

__all__ = ["RecommendationService", "REASON_MESSAGES", "DEMO_PROPENSITY_THRESHOLD", "PRODUCT_RULES", "RULES_VERSION"]
