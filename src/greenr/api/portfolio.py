"""Count structured decisions and recorded historical states without carbon sums."""

from collections import defaultdict
from collections.abc import Iterable, Mapping
from decimal import Decimal

from greenr.contracts.product import (
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
from greenr.impact import ImpactStatus, Product


def impact_totals(recommendations: Iterable[Recommendation]) -> dict:
    """Physical totals retain the complete compatibility boundary, including units."""
    from greenr.extensions.service import dump, impact_group

    totals = defaultdict(lambda: Decimal(0))
    unavailable = 0
    for recommendation in recommendations:
        row = dump(recommendation)
        key = impact_group(row)
        if key is None:
            unavailable += 1
        else:
            totals[key] += recommendation.impact.value
    return {"status": "AVAILABLE" if totals else "UNAVAILABLE", "unavailable_count": unavailable,
            "groups": [{"product": key[0], "units": key[1], "boundary": key[2], "period": key[3],
                        "method_version": key[4], "factor_catalogue_version": key[5], "value": str(value)}
                       for key, value in sorted(totals.items())],
            "limitation": "Modelled physical potential, not realised carbon savings. Incompatible units and boundaries are never summed."}


def portfolio_analytics(recommendations: Iterable[Recommendation]) -> dict:
    selected = tuple(recommendations)
    quality = defaultdict(int)
    for item in selected:
        quality[item.trust.status] += 1
    return {"physical_impact": impact_totals(item for item in selected if item.state == RecommendationState.RECOMMEND),
            "quality_counts": dict(quality),
            "missingness": {"propensity": sum(item.propensity is None or item.propensity.probability is None for item in selected),
                            "validated_confidence": sum(not item.propensity or not item.propensity.confidence_validated or item.propensity.confidence is None for item in selected),
                            "physical_impact": sum(item.impact.status != ImpactStatus.AVAILABLE or item.impact.value is None for item in selected)},
            "decision_count": len(selected)}


def historical_analytics(history: Iterable[HistoryRecord]) -> dict:
    """Optional historical evidence stays unavailable rather than using today's values."""
    groups = defaultdict(dict)
    for record in history:
        key = (record.month, record.product)
        previous = groups[key].get(record.customer_id)
        if previous is not None and previous != record:
            raise ValueError("Conflicting historical evidence for one customer, product and month")
        groups[key][record.customer_id] = record
    observations = []
    for (month, product), records in sorted(groups.items()):
        rows = list(records.values())
        observed = [r.observed_adoption_90d for r in rows if r.observed_adoption_90d is not None]
        impacts = [getattr(r, "impact", None) for r in rows]
        quality = [getattr(r, "data_quality", None) for r in rows]
        totals = defaultdict(lambda: Decimal(0))
        for impact in impacts:
            if impact is not None and impact.status == ImpactStatus.AVAILABLE and impact.value is not None:
                key = (impact.units, impact.boundary, str(impact.period), impact.method_version, impact.factor_catalogue_version)
                totals[key] += impact.value
        observations.append({"month": month, "product": str(product), "customer_count": len(rows),
                             "observed_conversion_rate": str(Decimal(sum(observed)) / len(observed)) if observed else None,
                             "observed_outcome_count": len(observed), "outcome_missing_count": len(rows) - len(observed),
                             "quality_counts": {value: quality.count(value) for value in sorted(set(quality) - {None})},
                             "quality_missing_count": quality.count(None),
                             "propensity_missing_count": sum(r.propensity is None for r in rows),
                             "confidence_missing_count": sum(r.confidence is None for r in rows),
                             "trust_missing_count": sum(r.trust_score is None for r in rows),
                             "physical_impact_status": "AVAILABLE" if totals else "UNAVAILABLE",
                             "physical_impact_missing_count": sum(i is None or i.status != ImpactStatus.AVAILABLE or i.value is None for i in impacts),
                             "physical_impact_groups": [{"units": k[0], "boundary": k[1], "period": k[2], "method_version": k[3],
                                                         "factor_catalogue_version": k[4], "value": str(v)} for k, v in sorted(totals.items())]})
    return {"observations": observations, "limitation": "Conversion denominators include recorded outcomes only. Missing historical quality and physical impact are unavailable; current evidence is never substituted."}


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
        analytics=portfolio_analytics(selected),
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
    selected_history = tuple(record for record in history
                             if record.customer_id in customer_ids and (product is None or record.product == product))
    groups: dict[tuple[str, Product], dict[str, HistoryRecord]] = defaultdict(dict)
    for record in selected_history:
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

    return PortfolioTrends(analytics=historical_analytics(selected_history), observations=tuple(
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
