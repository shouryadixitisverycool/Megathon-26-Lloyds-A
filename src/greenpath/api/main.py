"""FastAPI application factory with injected domain services and narrow providers."""

from contextlib import asynccontextmanager
from typing import Protocol

from fastapi import FastAPI, HTTPException

from greenpath.contracts.product import (
    CONTRACT_VERSION,
    CustomerSnapshot,
    Explanation,
    PortfolioSummary,
    PortfolioTrends,
    Recommendation,
    RecommendationsResponse,
)
from greenpath.ports import (
    ProductSnapshotProvider as CustomerSnapshotProvider,
    ImpactInputProvider,
    PortfolioHistoryProvider,
    ProductPropensityProvider as PropensityProvider,
)
from greenpath.impact import Product

from .portfolio import historical_trends, summarize


class RecommendationServicePort(Protocol):
    def recommendations(self, customer_id: str) -> tuple[Recommendation, ...]: ...


class ExplanationServicePort(Protocol):
    def explain(self, recommendation: Recommendation) -> Explanation: ...


def create_app(
    repository=None,
    *,
    provider_mode: str | None = None,
    snapshot_provider: CustomerSnapshotProvider | None = None,
    propensity_provider: PropensityProvider | None = None,
    impact_input_provider: ImpactInputProvider | None = None,
    history_provider: PortfolioHistoryProvider | None = None,
    recommendation_service: RecommendationServicePort | None = None,
    explanation_service: ExplanationServicePort | None = None,
) -> FastAPI:
    """Use explicit overrides first, repository ports second, demo defaults last."""
    needs_repository = (
        snapshot_provider is None
        or history_provider is None
        or (recommendation_service is None and (propensity_provider is None or impact_input_provider is None))
    )
    if repository is None and needs_repository:
        from greenpath.demo.artifacts import default_repository

        repository = default_repository(provider_mode)
    if snapshot_provider is None:
        snapshot_provider = repository
    if history_provider is None:
        history_provider = repository
    if recommendation_service is None:
        from greenpath.recommendation.service import RecommendationService

        recommendation_service = RecommendationService(
            snapshot_provider,
            propensity_provider if propensity_provider is not None else repository,
            impact_input_provider if impact_input_provider is not None else repository,
        )
    if explanation_service is None:
        from greenpath.llm.service import ExplanationService

        from greenpath.llm.http_provider import configured_provider

        explanation_service = ExplanationService(configured_provider())

    summary_cache = {}

    @asynccontextmanager
    async def lifespan(application):
        # Warm immutable trained evidence before accepting requests. A large first
        # trend calculation should not become a client timeout.
        if getattr(repository, "mode", None) == "trained":
            repository.list_history()
            for item in snapshot_provider.list_snapshots():
                recommendation_service.recommendations(item.customer_id)
            portfolio_summary()
        yield

    application = FastAPI(title="GreenPath decision platform", version=CONTRACT_VERSION, lifespan=lifespan)
    application.state.repository = repository
    application.state.snapshot_provider = snapshot_provider
    application.state.history_provider = history_provider
    application.state.recommendation_service = recommendation_service
    application.state.explanation_service = explanation_service

    def snapshot(customer_id: str) -> CustomerSnapshot:
        try:
            result = snapshot_provider.get_snapshot(customer_id)
        except KeyError:
            result = None
        if result is None:
            raise HTTPException(status_code=404, detail="Customer not found")
        return result

    def recommendations(customer_id: str) -> tuple[Recommendation, ...]:
        snapshot(customer_id)
        try:
            return recommendation_service.recommendations(customer_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Customer not found") from error

    def filtered_snapshots(region: str | None, segment: str | None) -> tuple[CustomerSnapshot, ...]:
        return tuple(
            item for item in snapshot_provider.list_snapshots()
            if (region is None or item.region == region) and (segment is None or item.segment == segment)
        )

    @application.get("/health")
    def health() -> dict[str, str | bool]:
        return {"status": "ok", "synthetic_demo": True, "contract_version": CONTRACT_VERSION,
                "provider_mode": getattr(snapshot_provider, "mode", "injected"),
                "source_version": getattr(snapshot_provider, "version", "injected-provider")}

    @application.get("/explanations/metrics")
    def explanation_metrics():
        if hasattr(explanation_service, "metrics"):
            return explanation_service.metrics()
        return {"provider": "injected", "measurements_available": False}

    @application.get("/customers", response_model=list[CustomerSnapshot])
    def customers():
        return snapshot_provider.list_snapshots()

    @application.get("/customers/{customer_id}", response_model=CustomerSnapshot)
    def customer(customer_id: str):
        return snapshot(customer_id)

    @application.get("/customers/{customer_id}/opportunities", response_model=RecommendationsResponse)
    @application.get("/customers/{customer_id}/recommendations", response_model=RecommendationsResponse)
    def customer_recommendations(customer_id: str):
        return RecommendationsResponse(customer_id=customer_id, recommendations=recommendations(customer_id))

    @application.get("/customers/{customer_id}/explanations/{product}", response_model=Explanation)
    def customer_explanation(customer_id: str, product: Product):
        for recommendation in recommendations(customer_id):
            if recommendation.product == product:
                return explanation_service.explain(recommendation)
        raise HTTPException(status_code=404, detail="Product recommendation not found")

    @application.get("/portfolio/summary", response_model=PortfolioSummary)
    def portfolio_summary(region: str | None = None, segment: str | None = None, product: Product | None = None):
        key = (region, segment, product)
        cacheable = getattr(repository, "mode", None) == "trained"
        if cacheable and key in summary_cache:
            return summary_cache[key]
        selected = filtered_snapshots(region, segment)
        decisions = {item.customer_id: recommendations(item.customer_id) for item in selected}
        result = summarize(selected, decisions, product)
        if cacheable:
            summary_cache[key] = result
        return result

    @application.get("/portfolio/trends", response_model=PortfolioTrends)
    def portfolio_trends(region: str | None = None, segment: str | None = None, product: Product | None = None):
        return historical_trends(filtered_snapshots(region, segment), history_provider.list_history(), product)

    from greenpath.extensions.api import attach_extensions

    attach_extensions(application)
    return application


app = create_app()
