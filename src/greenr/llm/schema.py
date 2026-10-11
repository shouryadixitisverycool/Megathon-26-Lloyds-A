"""Require populated public fields while the canonical contract retains old consumers."""

from greenr.contracts.product import Explanation


class StructuredExplanation(Explanation):
    headline: str
    explanation: str
    why_recommended: tuple[str, ...]
    estimated_impact_text: str
    confidence_text: str
    action_text: str
    missing_information: tuple[str, ...]
