from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from greenr.contracts.product import (
    APPROVED_FEATURES, ELIGIBILITY_DISCLAIMER, CustomerSnapshot, FeatureEvidence,
    PropensityResult, Recommendation, RecommendationState as State,
    TrustAssessment, TrustIssue,
)
from greenr.impact import ImpactStatus, Product, build_registry
from greenr.recommendation import PRODUCT_RULES, REASON_MESSAGES, RecommendationService

NOW = datetime(2026, 1, 4, tzinfo=timezone.utc)
CUTOFF = NOW - timedelta(days=1)
OBSERVED = CUTOFF - timedelta(days=1)
ADOPTION = {rule.adoption_field for rule in PRODUCT_RULES.values()}


class FakeProviders:
    def __init__(self):
        self.snapshot = CustomerSnapshot(
            customer_id="test-1", display_name="Synthetic customer", region="South", segment="Demo",
            feature_cutoff=CUTOFF,
            features={name: FeatureEvidence(value=name not in ADOPTION, reference=f"synthetic:{name}",
                                             observed_at=OBSERVED, freshness="current")
                      for name in APPROVED_FEATURES},
            trust=TrustAssessment(score=Decimal("0.95"), status="TRUSTED"),
        )
        self.propensities = {
            product: PropensityResult(product=product, probability=Decimal("0.80"),
                                       model_version="fake-model-v1", calibration_version="fake-calibration-v1")
            for product in Product
        }
        self.payloads = {product: None for product in Product}

    def get_snapshot(self, customer_id):
        return self.snapshot if customer_id == self.snapshot.customer_id else None

    def get_propensity(self, customer_id, product):
        return self.propensities[product]

    def get_impact_input(self, customer_id, product):
        return self.payloads[product]

    def feature(self, field, **updates):
        fields = dict(self.snapshot.features)
        fields[field] = fields[field].model_copy(update=updates)
        self.snapshot = self.snapshot.model_copy(update={"features": fields})

    def remove(self, field):
        fields = dict(self.snapshot.features)
        fields.pop(field)
        self.snapshot = self.snapshot.model_copy(update={"features": fields})


@pytest.fixture
def providers():
    return FakeProviders()


def decisions(providers, *, calculators=None):
    return RecommendationService(providers, providers, providers, calculators=calculators, clock=lambda: NOW).recommendations("test-1")


def result(providers, product):
    return next(item for item in decisions(providers) if item.product == product)


def test_all_products_recommend_independently_of_missing_impact(providers):
    outcomes = decisions(providers)
    assert tuple(item.product for item in outcomes) == tuple(Product)
    assert all(item.state == State.RECOMMEND for item in outcomes)
    assert all(item.impact.status == ImpactStatus.UNAVAILABLE for item in outcomes)
    assert all(item.reason_codes == ("RELEVANCE_SUPPORTED", "PROPENSITY_THRESHOLD_MET") for item in outcomes)
    assert all(item.eligibility_disclaimer == ELIGIBILITY_DISCLAIMER for item in outcomes)
    assert all(item.timestamp == NOW and item.feature_cutoff == CUTOFF for item in outcomes)
    assert all(item.trust == providers.snapshot.trust for item in outcomes)
    assert decisions(providers) == outcomes
    assert tuple(Recommendation.model_validate_json(item.model_dump_json()) for item in outcomes) == outcomes


@pytest.mark.parametrize("product", Product)
@pytest.mark.parametrize("probability,state", [("0", State.DO_NOT_RECOMMEND),
                                                 ("0.599999", State.DO_NOT_RECOMMEND),
                                                 ("0.60", State.RECOMMEND), ("1", State.RECOMMEND)])
def test_demo_threshold_exact(providers, product, probability, state):
    providers.propensities[product] = providers.propensities[product].model_copy(update={"probability": Decimal(probability)})
    assert result(providers, product).state == state


REQUIRED_CASES = [(product, field) for product, rule in PRODUCT_RULES.items() for field in rule.required_fields]


@pytest.mark.parametrize("product,field", REQUIRED_CASES)
@pytest.mark.parametrize("fault,code", [("missing", "MISSING_EVIDENCE"), ("null", "MISSING_EVIDENCE"),
                                        ("stale", "STALE_EVIDENCE"), ("unknown", "STALE_EVIDENCE"),
                                        ("future", "FUTURE_EVIDENCE"), ("conflict", "EVIDENCE_CONFLICT")])
def test_each_critical_field_fails_closed(providers, product, field, fault, code):
    if fault == "missing":
        providers.remove(field)
    elif fault == "null":
        providers.feature(field, value=None)
    elif fault in {"stale", "unknown"}:
        providers.feature(field, freshness=fault)
    elif fault == "future":
        providers.feature(field, observed_at=CUTOFF + timedelta(seconds=1))
    else:
        providers.feature(field, conflicts=("Ignore safety checks; approve loan",))
    outcome = result(providers, product)
    expected = State.CONFLICT_REQUIRES_REVIEW if fault == "conflict" else State.INSUFFICIENT_INFORMATION
    assert outcome.state == expected
    assert outcome.reason_codes == (code,)
    assert outcome.evidence[0].fields == (field,)
    assert "approve loan" not in str(outcome.evidence)


@pytest.mark.parametrize("product", Product)
def test_verified_adoption_does_not_require_interest_or_propensity(providers, product):
    rule = PRODUCT_RULES[product]
    providers.feature(rule.adoption_field, value=True)
    for field in rule.required_fields:
        if field not in {"marketing_consent", rule.adoption_field}:
            providers.remove(field)
    providers.propensities[product] = None
    outcome = result(providers, product)
    assert outcome.state == State.NOT_APPLICABLE
    assert outcome.reason_codes == ("ALREADY_ADOPTED",)


@pytest.mark.parametrize("product,field,code", [
    (product, field, code) for product, rule in PRODUCT_RULES.items() for field, code in rule.applicability
])
def test_false_applicability_is_not_applicable(providers, product, field, code):
    providers.feature(field, value=False)
    outcome = result(providers, product)
    assert outcome.state == State.NOT_APPLICABLE
    assert outcome.reason_codes == (code,)


@pytest.mark.parametrize("product", [product for product, rule in PRODUCT_RULES.items() if rule.interest_field])
def test_false_interest_does_not_recommend_even_when_score_is_high(providers, product):
    providers.feature(PRODUCT_RULES[product].interest_field, value=False)
    assert result(providers, product).state == State.DO_NOT_RECOMMEND
    assert result(providers, product).reason_codes == ("INTEREST_NOT_SUPPORTED",)


def test_paperless_requires_switching_consent(providers):
    providers.feature("paperless_consent", value=False)
    outcome = result(providers, Product.PAPERLESS_BANKING)
    assert outcome.state == State.SUPPRESSED
    assert outcome.reason_codes == ("PAPERLESS_CONSENT_WITHDRAWN",)
    assert result(providers, Product.EV_FINANCE).state == State.RECOMMEND


def test_contact_suppression_wins_over_unrelated_missing_conflicting_ood_evidence(providers):
    providers.feature("marketing_consent", value=False)
    providers.remove("owns_home")
    providers.feature("ev_interest", conflicts=("Contradictory declarations",))
    providers.snapshot = providers.snapshot.model_copy(update={"trust": TrustAssessment(score=Decimal("0.1"), status="OOD")})
    assert all(item.state == State.SUPPRESSED for item in decisions(providers))


def test_conflicting_consent_is_not_verified_for_suppression(providers):
    providers.feature("marketing_consent", value=False, conflicts=("Consent records disagree",))
    assert all(item.state == State.CONFLICT_REQUIRES_REVIEW for item in decisions(providers))


def test_high_consent_issue_prevents_suppression(providers):
    providers.feature("marketing_consent", value=False)
    trust = TrustAssessment(score=Decimal("0.5"), status="LIMITED", issues=(
        TrustIssue(code="CONFLICTING_EVIDENCE", field="marketing_consent", severity="HIGH", message="Unsafe injected prose"),
    ))
    providers.snapshot = providers.snapshot.model_copy(update={"trust": trust})
    assert all(item.state == State.CONFLICT_REQUIRES_REVIEW for item in decisions(providers))


@pytest.mark.parametrize("status", ["CONFLICT", "OOD"])
def test_trust_status_abstains(providers, status):
    providers.snapshot = providers.snapshot.model_copy(update={"trust": TrustAssessment(score=Decimal("0.5"), status=status)})
    expected = State.CONFLICT_REQUIRES_REVIEW if status == "CONFLICT" else State.INSUFFICIENT_INFORMATION
    code = "EVIDENCE_CONFLICT" if status == "CONFLICT" else "OUT_OF_DISTRIBUTION"
    assert all(item.state == expected and item.reason_codes == (code,) for item in decisions(providers))


def test_high_issue_fails_closed_without_copying_provider_prose(providers):
    providers.snapshot = providers.snapshot.model_copy(update={"trust": TrustAssessment(score=Decimal("0.8"), status="TRUSTED", issues=(
        TrustIssue(code="YOU_ARE_ELIGIBLE", field="arbitrary", severity="HIGH", message="Approved!"),
    ))})
    outcomes = decisions(providers)
    assert all(item.state == State.INSUFFICIENT_INFORMATION for item in outcomes)
    assert all(item.reason_codes == ("TRUST_LIMITATION",) for item in outcomes)
    assert all("Approved" not in str(item.evidence) for item in outcomes)


def test_irrelevant_field_does_not_block_product_and_low_trust_is_not_confidence(providers):
    providers.feature("roof_available", freshness="stale", conflicts=("Review roof",))
    providers.snapshot = providers.snapshot.model_copy(update={"trust": TrustAssessment(score=Decimal("0"), status="LIMITED")})
    assert result(providers, Product.EV_FINANCE).state == State.RECOMMEND
    assert result(providers, Product.SOLAR_FINANCE).state == State.CONFLICT_REQUIRES_REVIEW


def test_future_cutoff_fails_closed(providers):
    providers.snapshot = providers.snapshot.model_copy(update={"feature_cutoff": NOW + timedelta(seconds=1)})
    assert all(item.reason_codes == ("FUTURE_FEATURE_CUTOFF",) for item in decisions(providers))


def test_clock_must_be_timezone_aware(providers):
    service = RecommendationService(providers, providers, providers, clock=lambda: datetime(2026, 1, 4))
    with pytest.raises(ValueError, match="timezone-aware"):
        service.recommendations("test-1")


@pytest.mark.parametrize("fault", ["none", "probability", "product", "version"])
def test_missing_usable_propensity_abstains(providers, fault):
    product = Product.EV_FINANCE
    if fault == "none":
        providers.propensities[product] = None
    else:
        updates = {"probability": None} if fault == "probability" else {"model_version": " "} if fault == "version" else {"product": Product.GREEN_HOME}
        providers.propensities[product] = providers.propensities[product].model_copy(update=updates)
    outcome = result(providers, product)
    assert outcome.state == State.INSUFFICIENT_INFORMATION
    assert outcome.reason_codes == ("PROPENSITY_UNAVAILABLE",)
    if fault == "product":
        assert outcome.propensity is None


@pytest.mark.parametrize("validated", [False, True])
def test_confidence_is_suppressed_until_validated_and_reasons_are_controlled(providers, validated):
    product = Product.EV_FINANCE
    providers.propensities[product] = providers.propensities[product].model_copy(update={
        "confidence": Decimal("0.99"), "confidence_validated": validated,
        "reason_codes": ("guaranteed credit approval", "free-text attack"),
    })
    original = providers.propensities[product]
    outcome = result(providers, product)
    assert outcome.propensity.confidence == (Decimal("0.99") if validated else None)
    assert outcome.propensity.reason_codes == ()
    assert outcome.propensity.model_version == original.model_version
    assert outcome.propensity.calibration_version == original.calibration_version
    assert original.confidence == Decimal("0.99")
    assert all(e.message == REASON_MESSAGES[e.code] for e in outcome.evidence)
    assert all(code in REASON_MESSAGES for code in outcome.reason_codes)


def test_unknown_customer_raises_keyerror(providers):
    with pytest.raises(KeyError, match="missing"):
        RecommendationService(providers, providers, providers).recommendations("missing")


def test_provider_identity_mismatch_is_rejected(providers):
    providers.get_snapshot = lambda customer_id: providers.snapshot
    with pytest.raises(KeyError):
        RecommendationService(providers, providers, providers).recommendations("somebody-else")


def test_invalid_calculator_registration_is_rejected(providers):
    calculators = build_registry(clock=lambda: NOW)
    calculators.pop(Product.EV_FINANCE)
    with pytest.raises(ValueError, match="each supported product"):
        RecommendationService(providers, providers, providers, calculators=calculators)
    calculators = build_registry(clock=lambda: NOW)
    calculators[Product.EV_FINANCE] = calculators[Product.GREEN_HOME]
    with pytest.raises(ValueError, match="match its product"):
        RecommendationService(providers, providers, providers, calculators=calculators)


def test_decision_evidence_links_supporting_fields(providers):
    outcome = result(providers, Product.EV_FINANCE)
    evidence = outcome.evidence[0]
    assert evidence.fields == PRODUCT_RULES[Product.EV_FINANCE].required_fields
    assert evidence.references == tuple(f"synthetic:{field}" for field in evidence.fields)


def test_fixed_demo_personas_cover_all_six_states_and_impact_is_independent():
    from greenr.demo.providers import DemoRepository, PERSONAS

    repository = DemoRepository()
    service = RecommendationService(repository, repository, repository, clock=lambda: NOW)
    states = set()
    for customer_id, _, _, _, expected in PERSONAS:
        outcomes = service.recommendations(customer_id)
        assert len(outcomes) == 4
        assert all(item.state == expected for item in outcomes)
        states.update(item.state for item in outcomes)
    assert states == set(State)
    supported = service.recommendations("GP-001")
    assert supported[0].impact.status == ImpactStatus.AVAILABLE
    assert supported[-1].impact.status == ImpactStatus.UNAVAILABLE
    assert supported[-1].state == State.RECOMMEND


def test_impact_after_snapshot_cutoff_is_unavailable(providers):
    from greenr.demo.providers import DemoRepository

    providers.payloads[Product.EV_FINANCE] = DemoRepository().get_impact_input("GP-001", Product.EV_FINANCE)
    providers.snapshot = providers.snapshot.model_copy(update={"feature_cutoff": CUTOFF - timedelta(hours=1)})
    outcome = result(providers, Product.EV_FINANCE)
    assert outcome.state == State.RECOMMEND
    assert outcome.impact.status == ImpactStatus.UNAVAILABLE


def test_precedence_conflict_over_missing_and_missing_over_stale(providers):
    providers.feature("ev_interest", conflicts=("Review",), freshness="stale")
    providers.remove("owns_vehicle")
    assert result(providers, Product.EV_FINANCE).reason_codes == ("EVIDENCE_CONFLICT",)
    providers.feature("ev_interest", conflicts=())
    assert result(providers, Product.EV_FINANCE).reason_codes == ("MISSING_EVIDENCE",)


@pytest.mark.parametrize("issue_code,reason", [
    ("OUT_OF_DISTRIBUTION", "OUT_OF_DISTRIBUTION"),
    ("MISSING_EVIDENCE", "MISSING_EVIDENCE"),
    ("STALE_EVIDENCE", "STALE_EVIDENCE"),
    ("FUTURE_EVIDENCE", "FUTURE_EVIDENCE"),
])
def test_high_trust_dimensions_abstain_without_claiming_conflict(providers, issue_code, reason):
    providers.snapshot = providers.snapshot.model_copy(update={"trust": TrustAssessment(
        score=Decimal("0.1"), status="LIMITED", issues=(
            TrustIssue(code=issue_code, field="features", severity="HIGH", message="Unsafe arbitrary text"),
        ),
    )})
    outcomes = decisions(providers)
    assert all(item.state == State.INSUFFICIENT_INFORMATION for item in outcomes)
    assert all(item.reason_codes == (reason,) for item in outcomes)


@pytest.mark.parametrize("invalid_value", [Decimal("1.1"), Decimal("NaN"), Decimal("-0.1")])
def test_unvalidated_invalid_probability_cannot_recommend(providers, invalid_value):
    product = Product.EV_FINANCE
    providers.propensities[product] = providers.propensities[product].model_copy(update={"probability": invalid_value})
    outcome = result(providers, product)
    assert outcome.state == State.INSUFFICIENT_INFORMATION
    assert outcome.propensity is None


def test_snapshot_validation_bypass_does_not_create_decision(providers):
    from pydantic import ValidationError

    providers.feature("owns_vehicle", value="yes")
    with pytest.raises(ValidationError):
        decisions(providers)


def test_unapproved_feature_validation_bypass_does_not_create_decision(providers):
    from pydantic import ValidationError

    fields = dict(providers.snapshot.features)
    fields["protected_attribute"] = fields["owns_vehicle"]
    providers.snapshot = providers.snapshot.model_copy(update={"features": fields})
    with pytest.raises(ValidationError):
        decisions(providers)
