"""Count structured decisions and recorded historical states without carbon sums."""

from collections import defaultdict
from collections.abc import Iterable, Mapping

from greenpath._product_contract_mirror import (
    CustomerSnapshot,
    GroupSummary,
    HistoryRecord,
    PortfolioSummary,
    PortfolioTrends,
    ProductOpportunity,
    Recommendation,
    RecommendationState,
    TrendPoint,
)
from greenpath.impact import ImpactStatus, Product


def state_counts(recommendations: Iterable[Recommendation | HistoryRecord]) -> dict[str, int]:
    counts = {state.value: 0 for state in RecommendationState}
    for recommendation in recommendations:
        counts[recommendation.state.value] += 1
    return counts


def available_opportunities(recommendations: Iterable[Recommendation]) -> int:
    return sum(
        item.state == RecommendationState.RECOMMEND and item.impact.status == ImpactStatus.AVAILABLE
        for item in recommendations
    )


def summarize(
    snapshots: tuple[CustomerSnapshot, ...],
    recommendations: Mapping[str, tuple[Recommendation, ...]],
    product: Product | None = None,
) -> PortfolioSummary:
    selected = tuple(
        recommendation
        for snapshot in snapshots
        for recommendation in recommendations[snapshot.customer_id]
        if product is None or recommendation.product == product
    )
    counts = state_counts(selected)
    products = tuple(Product) if product is None else (product,)
    opportunities = []
    for selected_product in products:
        decisions = tuple(item for item in selected if item.product == selected_product)
        product_counts = state_counts(decisions)
        opportunities.append(ProductOpportunity(
            product=selected_product,
            total=len(decisions),
            recommended=product_counts[RecommendationState.RECOMMEND.value],
            state_counts=product_counts,
            available_impact_count=available_opportunities(decisions),
        ))

    def groups(field: str) -> tuple[GroupSummary, ...]:
        grouped: dict[str, list[CustomerSnapshot]] = defaultdict(list)
        for snapshot in snapshots:
            grouped[getattr(snapshot, field)].append(snapshot)
        return tuple(
            GroupSummary(
                name=name,
                customer_count=len(customers),
                recommended_count=sum(
                    item.state == RecommendationState.RECOMMEND
                    for customer in customers
                    for item in recommendations[customer.customer_id]
                    if product is None or item.product == product
                ),
            )
            for name, customers in sorted(grouped.items())
        )

    return PortfolioSummary(
        total_customers=len(snapshots),
        total_recommendations=len(selected),
        recommended_count=counts[RecommendationState.RECOMMEND.value],
        state_counts=counts,
        product_opportunities=tuple(opportunities),
        region_summaries=groups("region"),
        segment_summaries=groups("segment"),
        available_impact_count=available_opportunities(selected),
    )


def historical_trends(
    snapshots: tuple[CustomerSnapshot, ...],
    history: Iterable[HistoryRecord],
    product: Product | None = None,
) -> PortfolioTrends:
    customer_ids = {snapshot.customer_id for snapshot in snapshots}
    groups: dict[tuple[str, Product], dict[str, HistoryRecord]] = defaultdict(dict)
    for record in history:
        if record.customer_id not in customer_ids or (product is not None and record.product != product):
            continue
        group = groups[(record.month, record.product)]
        previous = group.get(record.customer_id)
        if previous is not None and previous.state != record.state:
            raise ValueError("Conflicting historical states for one customer, product and month")
        group[record.customer_id] = record

    return PortfolioTrends(observations=tuple(
        TrendPoint(
            month=month,
            product=selected_product,
            customer_count=len(records),
            recommended_count=sum(record.state == RecommendationState.RECOMMEND for record in records.values()),
            state_counts=state_counts(records.values()),
        )
        for (month, selected_product), records in sorted(groups.items())
    ))
