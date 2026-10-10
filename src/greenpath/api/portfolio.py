"""Count structured decisions and recorded historical states without carbon sums."""

from collections import defaultdict
from collections.abc import Iterable, Mapping
from decimal import Decimal

from greenpath.contracts.product import (
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


def high_confidence(item: Recommendation) -> bool:
    propensity = item.propensity
    return bool(propensity and propensity.confidence_validated and propensity.source_result
                and propensity.source_result.confidence.bucket
                and propensity.source_result.confidence.bucket.value == "HIGH")


def high_trust(item: Recommendation) -> bool:
    trust = item.trust
    return (trust.source_assessment.status.value == "HIGH" if trust.source_assessment is not None
            else trust.status == "TRUSTED")


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

    recommended = tuple(item for item in selected if item.state == RecommendationState.RECOMMEND)
    validated_recommended = sum(bool(item.propensity and item.propensity.confidence_validated) for item in recommended)
    return PortfolioSummary(
        total_customers=len(snapshots),
        total_recommendations=len(selected),
        recommended_count=counts[RecommendationState.RECOMMEND.value],
        state_counts=counts,
        product_opportunities=tuple(opportunities),
        region_summaries=groups("region"),
        segment_summaries=groups("segment"),
        available_impact_count=available_opportunities(selected),
        customers_with_opportunity=len({item.customer_id for item in recommended}),
        high_confidence_opportunities=sum(high_confidence(item) for item in recommended),
        validated_confidence_opportunities=validated_recommended,
        high_trust_opportunities=sum(high_trust(item) for item in recommended),
        funnel_counts={
            "analyzed_customers": len(snapshots),
            "in_population_scored_opportunities": sum(bool(item.propensity and item.propensity.in_model_population
                and item.propensity.probability is not None) for item in selected),
            "supported_opportunities": len(recommended),
            "supported_with_validated_confidence": validated_recommended,
            "supported_with_high_confidence": sum(high_confidence(item) for item in recommended),
        },
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

    def average(records, field):
        values = [getattr(record, field) for record in records.values() if getattr(record, field) is not None]
        return sum(values) / len(values) if values else None

    def opportunity_confidence(records):
        supported = [record for record in records.values() if record.state == RecommendationState.RECOMMEND]
        validated = [record for record in supported if record.confidence_high is not None]
        # Suppressed confidence never enters the numerator. Coverage is explicit;
        # the share denominator includes every supported opportunity.
        high = sum(record.confidence_high for record in validated)
        return high, len(validated), Decimal(high) / len(supported) if supported and validated else None

    def paperless(records):
        observed = [record.is_paperless for record in records.values() if record.is_paperless is not None]
        return len(observed), sum(observed) if observed else None, Decimal(sum(observed)) / len(observed) if observed else None

    return PortfolioTrends(observations=tuple(
        TrendPoint(
            month=month,
            product=selected_product,
            customer_count=len(records),
            recommended_count=sum(record.state == RecommendationState.RECOMMEND for record in records.values()),
            state_counts=state_counts(records.values()),
            high_confidence_opportunity_count=opportunity_confidence(records)[0],
            validated_confidence_opportunity_count=opportunity_confidence(records)[1],
            high_confidence_opportunity_share=opportunity_confidence(records)[2],
            paperless_observed_count=paperless(records)[0] if selected_product == Product.PAPERLESS_BANKING else 0,
            paperless_active_count=paperless(records)[1] if selected_product == Product.PAPERLESS_BANKING else None,
            paperless_adoption_rate=paperless(records)[2] if selected_product == Product.PAPERLESS_BANKING else None,
            average_propensity=average(records, "propensity"),
            average_validated_confidence=average(records, "confidence"),
            validated_confidence_count=sum(r.confidence is not None for r in records.values()),
            average_trust=average(records, "trust_score"),
            abstained_count=sum(r.state in {RecommendationState.INSUFFICIENT_INFORMATION,
                RecommendationState.CONFLICT_REQUIRES_REVIEW, RecommendationState.SUPPRESSED} for r in records.values()),
            observed_outcome_count=sum(r.observed_adoption_90d is not None for r in records.values()),
            observed_adoptions_90d=(sum(r.observed_adoption_90d for r in records.values() if r.observed_adoption_90d is not None)
                if any(r.observed_adoption_90d is not None for r in records.values()) else None),
        )
        for (month, selected_product), records in sorted(groups.items())
    ))
