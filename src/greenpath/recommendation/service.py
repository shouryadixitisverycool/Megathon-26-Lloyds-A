"""Deterministic relevance and abstention rules, independent of credit eligibility."""

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from types import MappingProxyType

from pydantic import ValidationError

from greenpath.contracts.product import (
    CustomerSnapshot, DecisionEvidence, PropensityResult, Recommendation,
    RecommendationState as State,
)
from greenpath.ports import (
    ProductSnapshotProvider as CustomerSnapshotProvider, ImpactInputProvider, ProductPropensityProvider as PropensityProvider,
)
from greenpath.impact import Product, build_registry
from greenpath.ports import ProductImpactCalculator as ImpactCalculator
from greenpath.impact.common import Clock, utc_now

from .reasons import REASON_MESSAGES

RULES_VERSION = "synthetic-relevance-rules-v1"
DEMO_PROPENSITY_THRESHOLD = Decimal("0.60")
CONFLICT_CODES = frozenset({"CONFLICT", "CONFLICTING_EVIDENCE", "EVIDENCE_CONFLICT", "CONFLICTING_INPUT", "HIGH_CONFLICT"})
OOD_CODES = frozenset({"OOD", "OUT_OF_DISTRIBUTION", "OOD_DETECTED"})
MISSING_CODES = frozenset({"MISSING_EVIDENCE", "MISSING_INPUT", "COMPLETENESS", "INCOMPLETE_EVIDENCE"})
STALE_CODES = frozenset({"STALE_EVIDENCE", "STALE_INPUT", "FRESHNESS", "UNKNOWN_FRESHNESS"})
FUTURE_CODES = frozenset({"FUTURE_EVIDENCE", "FUTURE_INPUT", "FUTURE_FEATURE_CUTOFF"})


@dataclass(frozen=True)
class ProductRule:
    adoption_field: str | None
    applicability: tuple[tuple[str, str], ...]
    interest_field: str | None = None
    consent_field: str | None = None
    require_marketing_consent: bool = True

    @property
    def required_fields(self) -> tuple[str, ...]:
        return (
            *(("marketing_consent",) if self.require_marketing_consent else ()),
            *((self.adoption_field,) if self.adoption_field else ()),
            *(field for field, _ in self.applicability),
            *((self.interest_field,) if self.interest_field else ()),
            *((self.consent_field,) if self.consent_field else ()),
        )


PRODUCT_RULES = MappingProxyType({
    Product.EV_FINANCE: ProductRule(
        "already_has_ev", (("owns_vehicle", "VEHICLE_REQUIRED"),
                           ("fuel_supported", "FUEL_UNSUPPORTED")), "ev_interest"),
    Product.GREEN_HOME: ProductRule(
        "efficient_home", (("owns_home", "HOME_REQUIRED"),), "retrofit_interest"),
    Product.SOLAR_FINANCE: ProductRule(
        "solar_installed", (("owns_home", "HOME_REQUIRED"),
                            ("roof_available", "ROOF_UNAVAILABLE")), "solar_interest"),
    Product.PAPERLESS_BANKING: ProductRule(
        "paperless_active", (("paper_statements", "NO_PAPER_STATEMENTS"),),
        consent_field="paperless_consent"),
})

# The trained source records ownership/adoption and calibrated interest, but it
# has no marketing permissions, roof survey or explicit upgrade-interest record.
# These rules establish product relevance only. They authorize no contact or
# physical-installation/credit eligibility claim.
TRAINED_PRODUCT_RULES = MappingProxyType({
    Product.EV_FINANCE: ProductRule(
        "already_has_ev", (("owns_vehicle", "VEHICLE_REQUIRED"),
                           ("fuel_supported", "FUEL_UNSUPPORTED")), require_marketing_consent=False),
    Product.GREEN_HOME: ProductRule(
        None, (("owns_home", "HOME_REQUIRED"),), require_marketing_consent=False),
    Product.SOLAR_FINANCE: ProductRule(
        "solar_installed", (("owns_home", "HOME_REQUIRED"),), require_marketing_consent=False),
    Product.PAPERLESS_BANKING: ProductRule(
        "paperless_active", (("paper_statements", "NO_PAPER_STATEMENTS"),), require_marketing_consent=False),
})


class RecommendationService:
    """Return one decision per product without estimating impact or eligibility.

    Provider exceptions propagate; a missing snapshot is the only unknown-ID case.
    Dependencies implement canonical product-view ports.
    """

    def __init__(
        self, snapshot_provider: CustomerSnapshotProvider,
        propensity_provider: PropensityProvider,
        impact_input_provider: ImpactInputProvider, *,
        calculators: Mapping[Product, ImpactCalculator] | None = None,
        clock: Clock = utc_now,
    ):
        self.snapshot_provider = snapshot_provider
        self.propensity_provider = propensity_provider
        self.impact_input_provider = impact_input_provider
        self.clock = clock
        self._decision_cache = {} if getattr(snapshot_provider, "mode", None) == "trained" else None
        selected_calculators = calculators if calculators is not None else getattr(snapshot_provider, "impact_calculators", None)
        self.calculators = dict(selected_calculators) if selected_calculators is not None else build_registry(clock=clock)
        if set(self.calculators) != set(Product):
            raise ValueError("Register exactly one calculator for each supported product")
        if any(calculator.product != product for product, calculator in self.calculators.items()):
            raise ValueError("Calculator registration must match its product")

    def recommendations(self, customer_id: str) -> tuple[Recommendation, ...]:
        snapshot = self.snapshot_provider.get_snapshot(customer_id)
        if snapshot is None:
            raise KeyError(customer_id)
        # Frozen models can still be constructed/copied without validation by a
        # provider. Revalidate the payload rather than trusting its Python type.
        snapshot = CustomerSnapshot.model_validate(snapshot.model_dump(mode="python", warnings=False))
        if snapshot.customer_id != customer_id:
            raise KeyError(customer_id)
        # Re-read evidence even in trained mode so an available withdrawal cannot
        # be hidden by decisions warmed before the permission changed.
        if self._decision_cache is not None and customer_id in self._decision_cache:
            cached_snapshot, decisions = self._decision_cache[customer_id]
            if cached_snapshot == snapshot:
                return decisions
        now = self.clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("Decision clock must return a timezone-aware datetime")
        decisions = tuple(self._recommendation(snapshot, product, now) for product in Product)
        if self._decision_cache is not None:
            self._decision_cache[customer_id] = (snapshot.model_copy(deep=True), decisions)
        return decisions

    def _recommendation(self, snapshot: CustomerSnapshot, product: Product, now: datetime) -> Recommendation:
        if product in snapshot.product_trust:
            snapshot = snapshot.model_copy(update={"trust": snapshot.product_trust[product]})
        raw_propensity = self.propensity_provider.get_propensity(snapshot.customer_id, product)
        propensity = self._clean_propensity(raw_propensity, product)
        if propensity is not None and propensity.source_result is not None:
            source = propensity.source_result
            if source.customer_id != snapshot.customer_id or source.feature_cutoff != snapshot.feature_cutoff.date():
                propensity = None
        rules = TRAINED_PRODUCT_RULES if snapshot.decision_profile == "trained" else PRODUCT_RULES
        rule = rules[product]
        if snapshot.decision_profile == "trained" and product == Product.GREEN_HOME and "efficient_home" in snapshot.features:
            rule = replace(rule, adoption_field="efficient_home")
        state, evidence = self._decide(snapshot, rule, propensity, now, product)
        calculator = self.calculators[product]
        payload = self.impact_input_provider.get_impact_input(snapshot.customer_id, product)
        impact = calculator.calculate(payload)
        if impact.product != product:
            raise ValueError("Calculator returned a different product")
        # A provider cannot supply impact observations from beyond this snapshot.
        if impact.feature_cutoff is not None and impact.feature_cutoff > snapshot.feature_cutoff:
            impact = calculator.calculate(None)
        exclusions = [
            "Credit eligibility and approval assessment are excluded.",
            "Synthetic-data probabilities do not establish real-world predictive performance.",
        ]
        if snapshot.decision_profile == "trained":
            exclusions.append("Product relevance does not authorize marketing contact or a service change; absent permissions are not consent. Installation suitability is not assessed.")
        if raw_propensity is not None and raw_propensity.confidence is not None and not raw_propensity.confidence_validated:
            exclusions.append("Model confidence is suppressed because its reliability has not been validated.")
        if impact.value is None:
            exclusions.append("Sustainability impact is unavailable; it does not determine product relevance.")
        return Recommendation(
            customer_id=snapshot.customer_id, product=product, propensity=propensity,
            state=state, reason_codes=tuple(item.code for item in evidence),
            evidence=evidence, exclusions=tuple(exclusions), impact=impact,
            trust=snapshot.trust, feature_cutoff=snapshot.feature_cutoff,
            rules_version="trained-relevance-rules-v1" if snapshot.decision_profile == "trained" else RULES_VERSION,
            timestamp=now,
        )

    @staticmethod
    def _clean_propensity(result: PropensityResult | None, product: Product) -> PropensityResult | None:
        if result is None:
            return None
        try:
            result = PropensityResult.model_validate(result.model_dump(mode="python", warnings=False))
        except ValidationError:
            return None
        if result.product != product:
            return None
        # A model's free-form reason vocabulary cannot authorize relevance reasons.
        # The rules derive reasons directly from approved snapshot evidence.
        return result.model_copy(update={
            "reason_codes": tuple(code.value for code in result.source_result.reason_codes) if result.source_result else (),
            "confidence": result.confidence if result.confidence_validated else None,
        })

    @staticmethod
    def _evidence(snapshot: CustomerSnapshot, code: str, fields: tuple[str, ...] = ()) -> DecisionEvidence:
        references = tuple(dict.fromkeys(
            snapshot.features[field].reference for field in fields if field in snapshot.features
        ))
        return DecisionEvidence(code=code, message=REASON_MESSAGES[code], fields=fields, references=references)

    def _decide(
        self, snapshot: CustomerSnapshot, rule: ProductRule,
        propensity: PropensityResult | None, now: datetime, product: Product,
    ) -> tuple[State, tuple[DecisionEvidence, ...]]:
        def decision(state: State, code: str, fields: tuple[str, ...] = ()):
            return state, (self._evidence(snapshot, code, fields),)

        def usable(field: str) -> bool:
            item = snapshot.features.get(field)
            return bool(item is not None and item.value is not None and item.freshness == "current"
                        and not item.conflicts and item.observed_at <= snapshot.feature_cutoff <= now)

        consent_fields = ("marketing_consent",) + (("paperless_consent",) if product == Product.PAPERLESS_BANKING else ())
        for field in consent_fields:
            consent = snapshot.features.get(field)
            consent_conflict = any(issue.severity == "HIGH" and issue.field in (field, "", "*")
                                   for issue in snapshot.trust.issues)
            if usable(field) and consent.value is False and not consent_conflict:
                code = "MARKETING_CONSENT_WITHDRAWN" if field == "marketing_consent" else "PAPERLESS_CONSENT_WITHDRAWN"
                return decision(State.SUPPRESSED, code, (field,))

        checked_fields = tuple(dict.fromkeys((*rule.required_fields, *consent_fields)))
        conflict_fields = tuple(field for field in checked_fields
                                if field in snapshot.features and snapshot.features[field].conflicts)
        high_issues = tuple(issue for issue in snapshot.trust.issues if issue.severity == "HIGH")
        high_conflicts = tuple(issue for issue in high_issues if issue.code in CONFLICT_CODES)
        if snapshot.trust.status == "CONFLICT" or conflict_fields or high_conflicts:
            fields = tuple(dict.fromkeys((*conflict_fields, *(issue.field for issue in high_issues
                                                              if issue.field in checked_fields))))
            return decision(State.CONFLICT_REQUIRES_REVIEW, "EVIDENCE_CONFLICT", fields)
        if snapshot.trust.status == "OOD" or any(issue.code in OOD_CODES for issue in high_issues):
            return decision(State.INSUFFICIENT_INFORMATION, "OUT_OF_DISTRIBUTION")
        if snapshot.feature_cutoff > now:
            return decision(State.INSUFFICIENT_INFORMATION, "FUTURE_FEATURE_CUTOFF")
        available_consent = tuple(field for field in consent_fields
                                  if field in snapshot.features and snapshot.features[field].value is not None)
        missing = self._unusable(snapshot, available_consent)
        if missing:
            code, affected = missing
            return decision(State.INSUFFICIENT_INFORMATION, code, affected)
        if high_issues:
            for codes, reason in ((MISSING_CODES, "MISSING_EVIDENCE"), (STALE_CODES, "STALE_EVIDENCE"),
                                  (FUTURE_CODES, "FUTURE_EVIDENCE")):
                matched = tuple(issue for issue in high_issues if issue.code in codes)
                if matched:
                    fields = tuple(dict.fromkeys(issue.field for issue in matched if issue.field in rule.required_fields))
                    return decision(State.INSUFFICIENT_INFORMATION, reason, fields)
            return decision(State.INSUFFICIENT_INFORMATION, "TRUST_LIMITATION")

        if snapshot.trust.source_assessment is not None and not snapshot.trust.source_assessment.critical_fields_present:
            return decision(State.INSUFFICIENT_INFORMATION, "MISSING_EVIDENCE")
        if snapshot.trust.source_assessment is not None and snapshot.trust.source_assessment.status.value in {"LOW", "INSUFFICIENT"}:
            return decision(State.INSUFFICIENT_INFORMATION, "TRUST_LIMITATION")
        if propensity is not None and not propensity.in_model_population:
            return decision(State.NOT_APPLICABLE, "ALREADY_ADOPTED")

        # Existing adoption is enough to stop, after consent and safety checks.
        fields = (
            *(("marketing_consent",) if rule.require_marketing_consent else ()),
            *((rule.adoption_field,) if rule.adoption_field else ()),
        )
        missing = self._unusable(snapshot, fields)
        if missing:
            code, affected = missing
            return decision(State.INSUFFICIENT_INFORMATION, code, affected)
        if rule.adoption_field and snapshot.features[rule.adoption_field].value:
            return decision(State.NOT_APPLICABLE, "ALREADY_ADOPTED", (rule.adoption_field,))

        missing = self._unusable(snapshot, rule.required_fields)
        if missing:
            code, affected = missing
            return decision(State.INSUFFICIENT_INFORMATION, code, affected)
        for field, code in rule.applicability:
            if not snapshot.features[field].value:
                return decision(State.NOT_APPLICABLE, code, (field,))
        if rule.consent_field and not snapshot.features[rule.consent_field].value:
            return decision(State.SUPPRESSED, "PAPERLESS_CONSENT_WITHDRAWN", (rule.consent_field,))
        if rule.interest_field and not snapshot.features[rule.interest_field].value:
            return decision(State.DO_NOT_RECOMMEND, "INTEREST_NOT_SUPPORTED", (rule.interest_field,))
        if propensity is None or propensity.probability is None or not propensity.model_version.strip():
            return decision(State.INSUFFICIENT_INFORMATION, "PROPENSITY_UNAVAILABLE")
        if (snapshot.decision_profile == "trained" and propensity.confidence_validated
                and propensity.source_result is not None
                and propensity.source_result.confidence.bucket is not None
                and propensity.source_result.confidence.bucket.value == "LOW"):
            return decision(State.INSUFFICIENT_INFORMATION, "CONFIDENCE_BELOW_MINIMUM")
        if propensity.probability < propensity.decision_threshold:
            return decision(State.DO_NOT_RECOMMEND, "PROPENSITY_BELOW_THRESHOLD")
        return State.RECOMMEND, (
            self._evidence(snapshot, "RELEVANCE_SUPPORTED", rule.required_fields),
            self._evidence(snapshot, "PROPENSITY_THRESHOLD_MET"),
        )

    @staticmethod
    def _unusable(snapshot: CustomerSnapshot, fields: tuple[str, ...]):
        checks = (
            ("MISSING_EVIDENCE", lambda item: item is None or item.value is None),
            ("STALE_EVIDENCE", lambda item: item is not None and item.freshness != "current"),
            ("FUTURE_EVIDENCE", lambda item: item is not None and item.observed_at > snapshot.feature_cutoff),
        )
        for code, invalid in checks:
            affected = tuple(field for field in fields if invalid(snapshot.features.get(field)))
            if affected:
                return code, affected
        return None
