"""Trained relevance is neither contact authorization nor a safety bypass."""

from datetime import datetime, timedelta, timezone

import pytest

from greenr.contracts.product import (
    CustomerSnapshot, FeatureEvidence, PropensityResult, RecommendationState as State,
    TrustAssessment, TrustIssue,
)
from greenr.impact import Product
from greenr.recommendation.service import RecommendationService

NOW = datetime(2026, 7, 1, tzinfo=timezone.utc)


class TrainedProvider:
    mode = "trained"

    def __init__(self):
        self.snapshot = CustomerSnapshot(
            customer_id="test-1", display_name="Synthetic customer", region="South", segment="Demo",
            feature_cutoff=NOW - timedelta(days=1), decision_profile="trained",
            trust=TrustAssessment(score="0.95", status="TRUSTED"),
            features={field: FeatureEvidence(
                value=value, reference=f"synthetic:{field}", observed_at=NOW - timedelta(days=2),
                freshness="current",
            ) for field, value in {
                "owns_vehicle": True, "fuel_supported": True, "already_has_ev": False,
                "owns_home": True, "solar_installed": False, "paperless_active": False,
                "paper_statements": True,
            }.items()},
        )

    def get_snapshot(self, customer_id):
        return self.snapshot if customer_id == self.snapshot.customer_id else None

    def get_propensity(self, customer_id, product):
        return PropensityResult(product=product, probability="0.8", model_version="safety-test-v1")

    def get_impact_input(self, customer_id, product):
        return None


@pytest.fixture
def trained():
    provider = TrainedProvider()
    return provider, RecommendationService(provider, provider, provider, clock=lambda: NOW)


def test_absent_permissions_allow_only_relevance(trained):
    _, service = trained
    decisions = service.recommendations("test-1")
    assert all(r.state == State.RECOMMEND for r in decisions)
    assert all(any("absent permissions are not consent" in e for e in r.exclusions) for r in decisions)
    assert all("not a credit eligibility" in r.eligibility_disclaimer for r in decisions)
    assert all(r.impact.value is None for r in decisions)
    assert all(not {"marketing_consent", "paperless_consent", "roof_available"}
               & set(e.fields) for r in decisions for e in r.evidence)


def test_null_permission_records_are_not_invented_authorization(trained):
    provider, service = trained
    for field in ("marketing_consent", "paperless_consent"):
        provider.snapshot.features[field] = provider.snapshot.features["owns_home"].model_copy(update={"value": None})
    assert all(r.state == State.RECOMMEND for r in service.recommendations("test-1"))


def test_unknown_customer_is_not_hidden_by_warmed_cache(trained):
    provider, service = trained
    service.recommendations("test-1")
    provider.snapshot = provider.snapshot.model_copy(update={"customer_id": "replacement"})
    with pytest.raises(KeyError):
        service.recommendations("test-1")


@pytest.mark.parametrize("field,products,code", [
    ("marketing_consent", tuple(Product), "MARKETING_CONSENT_WITHDRAWN"),
    ("paperless_consent", (Product.PAPERLESS_BANKING,), "PAPERLESS_CONSENT_WITHDRAWN"),
])
def test_available_withdrawal_invalidates_warmed_decisions(trained, monkeypatch, field, products, code):
    provider, service = trained
    previous = service.recommendations("test-1")
    with monkeypatch.context() as patch:
        def unexpected_inference(*args):
            pytest.fail("Unchanged evidence must reuse cached decisions")

        patch.setattr(provider, "get_propensity", unexpected_inference)
        assert service.recommendations("test-1") == previous
    evidence = provider.snapshot.features["owns_home"].model_copy(update={
        "value": False, "reference": f"permission:{field}",
    })
    # Mutate in place too: cache keys must not alias the provider's evidence.
    provider.snapshot.features[field] = evidence
    decisions = service.recommendations("test-1")
    for result in decisions:
        if result.product in products:
            assert result.state == State.SUPPRESSED
            assert result.reason_codes == (code,)
            assert result.evidence[0].fields == (field,)
            assert result.evidence[0].references == (f"permission:{field}",)
        else:
            assert result.state == State.RECOMMEND
    assert all(r.state == State.RECOMMEND for r in previous)


def test_returned_decisions_cannot_mutate_warmed_cache(trained):
    _, service = trained
    previous = service.recommendations("test-1")
    expected = tuple(result.model_dump(mode="python") for result in previous)
    previous[0].provenance["snapshot"]["features"].clear()
    repeated = service.recommendations("test-1")
    assert tuple(result.model_dump(mode="python") for result in repeated) == expected
    repeated[0].provenance["snapshot"]["features"].clear()
    assert tuple(result.model_dump(mode="python") for result in service.recommendations("test-1")) == expected


@pytest.mark.parametrize("field", ["marketing_consent", "paperless_consent"])
@pytest.mark.parametrize("fault,state,code", [
    ("stale", State.INSUFFICIENT_INFORMATION, "STALE_EVIDENCE"),
    ("future", State.INSUFFICIENT_INFORMATION, "FUTURE_EVIDENCE"),
    ("conflict", State.CONFLICT_REQUIRES_REVIEW, "EVIDENCE_CONFLICT"),
])
def test_unusable_available_permission_fails_closed(trained, field, fault, state, code):
    provider, service = trained
    updates = {"value": False}
    if fault == "stale":
        updates["freshness"] = "stale"
    elif fault == "future":
        updates["observed_at"] = provider.snapshot.feature_cutoff + timedelta(seconds=1)
    else:
        updates["conflicts"] = ("Contradictory permission records",)
    provider.snapshot.features[field] = provider.snapshot.features["owns_home"].model_copy(update=updates)
    decisions = service.recommendations("test-1")
    for result in decisions:
        if field == "marketing_consent" or result.product == Product.PAPERLESS_BANKING:
            assert result.state == state
            assert result.reason_codes == (code,)
        else:
            assert result.state == State.RECOMMEND


def test_verified_withdrawal_wins_over_unrelated_quality_failures(trained):
    provider, service = trained
    provider.snapshot.features["marketing_consent"] = provider.snapshot.features["owns_home"].model_copy(
        update={"value": False})
    provider.snapshot.features.pop("owns_home")
    provider.snapshot = provider.snapshot.model_copy(update={
        "trust": TrustAssessment(score="0.1", status="OOD"),
    })
    assert all(r.state == State.SUPPRESSED for r in service.recommendations("test-1"))


def test_permission_conflict_is_not_overridden_by_withdrawal(trained):
    provider, service = trained
    provider.snapshot.features["marketing_consent"] = provider.snapshot.features["owns_home"].model_copy(
        update={"value": False})
    provider.snapshot = provider.snapshot.model_copy(update={"trust": TrustAssessment(
        score="0.4", status="CONFLICT", issues=(TrustIssue(
            code="CONFLICTING_EVIDENCE", field="marketing_consent", severity="HIGH",
            message="Conflicting permission records",
        ),),
    )})
    assert all(r.state == State.CONFLICT_REQUIRES_REVIEW for r in service.recommendations("test-1"))


def test_product_trust_and_available_adoption_remain_independent(trained):
    provider, service = trained
    provider.snapshot = provider.snapshot.model_copy(update={"product_trust": {
        Product.SOLAR_FINANCE: TrustAssessment(score="0.1", status="OOD"),
    }})
    provider.snapshot.features["efficient_home"] = provider.snapshot.features["owns_home"]
    decisions = {r.product: r for r in service.recommendations("test-1")}
    assert decisions[Product.SOLAR_FINANCE].reason_codes == ("OUT_OF_DISTRIBUTION",)
    assert decisions[Product.GREEN_HOME].state == State.NOT_APPLICABLE
    assert decisions[Product.EV_FINANCE].state == State.RECOMMEND
    assert decisions[Product.PAPERLESS_BANKING].state == State.RECOMMEND
