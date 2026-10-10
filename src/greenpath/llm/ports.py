"""Structured provider boundary. Providers choose approved sentences, never prose."""

from decimal import Decimal
from typing import Literal, Protocol

from pydantic import Field

from greenpath._product_contract_mirror import RecommendationState
from greenpath.impact._contract_mirror import Model, Product


class ApprovedSentence(Model):
    sentence_id: str
    text: str


class ExplanationRequest(Model):
    schema_version: Literal["grounded-explanation-v1"] = "grounded-explanation-v1"
    product: Product
    state: RecommendationState
    reason_codes: tuple[str, ...]
    impact_value: Decimal | None
    units: Literal["kg CO2", "kg CO2/year"]
    eligibility_disclaimer: str
    approved_sentences: tuple[ApprovedSentence, ...]
    required_sentence_ids: tuple[str, ...]


class ProviderExplanation(Model):
    """Return every required sentence once, in a provider-selected order."""

    product: Product
    state: RecommendationState
    reason_codes: tuple[str, ...]
    impact_value: Decimal | None
    units: Literal["kg CO2", "kg CO2/year"]
    eligibility_disclaimer: str
    sentence_ids: tuple[str, ...] = Field(min_length=1)


class ExplanationProvider(Protocol):
    version: str

    def generate(self, request: ExplanationRequest, *, timeout_seconds: float) -> object:
        """Return a ProviderExplanation, its JSON string, or a JSON-compatible dict.

        Network adapters must also configure their SDK's request timeout. The
        service enforces a caller deadline; it cannot cancel an SDK operation.
        No live provider or credential discovery is included in the default app.
        """
        ...
