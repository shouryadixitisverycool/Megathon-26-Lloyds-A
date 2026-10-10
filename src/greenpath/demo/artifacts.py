"""Adapt trained, point-in-time ML evidence to the product/API contract."""

from datetime import datetime, time, timezone
from decimal import Decimal
from pathlib import Path
import os

from greenpath import config
from greenpath.contracts.enums import ConfidenceStatus, FuelType, Severity, TrustIssueCategory
from greenpath.contracts.impact_detail import ImpactIssue, IssueCode
from greenpath.contracts.product import (
    CustomerSnapshot, FeatureEvidence, HistoryRecord, PropensityResult, TrustAssessment, TrustIssue,
)
from greenpath.impact import Product, build_registry


class UnavailableGeographyCalculator:
    """Keep UK-source physical data out of the India-only factor catalogue."""

    def __init__(self, calculator):
        self.calculator = calculator
        self.product = calculator.product
        result = self.calculator.calculate(None)
        self._result = result.model_copy(update={
            "factors": (),
            "issues": (ImpactIssue(
                code=IssueCode.UNSUPPORTED_SCOPE, field="context.geography",
                message="Trained snapshots use UK physical data. The reviewed impact catalogue supports India only; no compatible calculation is available.",
            ),),
        })

    def calculate(self, payload):
        return self._result


def _adapt_trust(source):
    conflict = source.has_high_severity_conflict
    ood = any(i.category == TrustIssueCategory.OOD and i.severity == Severity.HIGH for i in source.issues)
    status = "CONFLICT" if conflict else "OOD" if ood else "TRUSTED" if source.status.value in {"HIGH", "ADEQUATE"} else "LIMITED"
    issues = []
    codes = {
        TrustIssueCategory.CONFLICT: "CONFLICTING_EVIDENCE",
        TrustIssueCategory.OOD: "OUT_OF_DISTRIBUTION",
        TrustIssueCategory.COMPLETENESS: "MISSING_EVIDENCE",
        TrustIssueCategory.CRITICAL_FIELD: "MISSING_EVIDENCE",
        TrustIssueCategory.FRESHNESS: "STALE_EVIDENCE",
    }
    for issue in source.issues:
        for field in issue.fields or ["features"]:
            issues.append(TrustIssue(
                code=codes[issue.category], field=field,
                severity={"LOW": "INFO", "MEDIUM": "WARNING", "HIGH": "HIGH"}[issue.severity.value],
                message=issue.message,
            ))
    return TrustAssessment(score=Decimal(str(source.score)), status=status, issues=tuple(issues),
                           version=source.method_version, source_assessment=source)


class ArtifactRepository:
    """Cache batch predictions and per-product Trust once for each real cutoff."""

    mode = "trained"

    def __init__(self, runtime=None):
        self._outcome_path = config.ARTIFACT_DIR / "portfolio_scores.parquet" if runtime is None else None
        if runtime is None:
            from greenpath.pipelines.runtime import load_runtime
            from greenpath.pipelines.snapshot_provider import customer360_path
            cutoffs = [c for c in config.TREND_CUTOFFS if customer360_path(c).is_file()]
            if config.FEATURE_CUTOFF not in cutoffs:
                cutoffs.append(config.FEATURE_CUTOFF)
            try:
                runtime = load_runtime(cutoffs=cutoffs)
            except Exception as exc:
                raise RuntimeError("Trained provider artifacts are missing, incomplete or corrupt. Run the full pipeline or select GREENPATH_PROVIDER=fixture.") from exc
        if set(runtime.bundles) != set(Product):
            raise ValueError("Trained provider requires a calibrated bundle for every product")
        self.runtime = runtime
        self.version = "trained:" + ",".join(runtime.bundles[p].model_version for p in Product)
        self.impact_calculators = {p: UnavailableGeographyCalculator(c) for p, c in build_registry().items()}
        self._cache = {}
        self._history = None

    def _at(self, cutoff):
        if cutoff not in self._cache:
            sources = self.runtime.snapshots.snapshots(cutoff)
            propensities, trusts = {}, {}
            for product in Product:
                results = self.runtime.propensity.score_many(sources, product)
                assessments = self.runtime.trust.assess_many(sources, product)
                for source, result, assessment in zip(sources, results, assessments, strict=True):
                    validated = result.confidence.status == ConfidenceStatus.VALIDATED
                    propensities[(source.customer_id, product)] = PropensityResult(
                        product=product, probability=Decimal(str(result.propensity)) if result.in_model_population else None,
                        model_version=result.model_version, calibration_version=result.calibration_version,
                        confidence=Decimal(str(result.confidence.value)) if validated else None,
                        confidence_validated=validated, in_model_population=result.in_model_population,
                        population_exclusion=result.population_exclusion.value if result.population_exclusion else None,
                        decision_threshold=Decimal(str(self.runtime.bundles[product].threshold)), source_result=result,
                    )
                    trusts[(source.customer_id, product)] = _adapt_trust(assessment)
            snapshots = {}
            for source in sources:
                observed = datetime.combine(cutoff, time.min, tzinfo=timezone.utc)
                fuel = source.vehicle.fuel_type
                values = {
                    "owns_vehicle": source.vehicle.has_vehicle,
                    "fuel_supported": fuel in {FuelType.PETROL, FuelType.DIESEL, FuelType.HYBRID} if fuel else None,
                    "already_has_ev": fuel == FuelType.EV if fuel else None,
                    "owns_home": source.home.home_owner,
                    "solar_installed": source.home.has_existing_solar,
                    "paperless_active": source.digital.is_paperless,
                    "paper_statements": source.digital.paper_statements_3m > 0 if source.digital.paper_statements_3m is not None else None,
                }
                per_product = {p: trusts[(source.customer_id, p)] for p in Product}
                snapshots[source.customer_id] = CustomerSnapshot(
                    customer_id=source.customer_id, display_name=f"Synthetic customer {source.customer_id}",
                    region=source.home.region or "Unknown", segment=source.segment or "Unknown",
                    feature_cutoff=observed, features={
                        key: FeatureEvidence(value=value, reference=f"customer360:{source.feature_version}:{cutoff}:{source.customer_id}:{key}",
                                             observed_at=observed, freshness="current")
                        for key, value in values.items()
                    }, trust=min(per_product.values(), key=lambda t: t.score), product_trust=per_product,
                    decision_profile="trained", source_snapshot=source,
                )
            self._cache[cutoff] = snapshots, propensities
        return self._cache[cutoff]

    def get_snapshot(self, customer_id):
        result = self._at(self.runtime.snapshots.default_cutoff)[0].get(customer_id)
        return result.model_copy(deep=True) if result else None

    def list_snapshots(self):
        return tuple(s.model_copy(deep=True) for s in self._at(self.runtime.snapshots.default_cutoff)[0].values())

    def get_propensity(self, customer_id, product):
        result = self._at(self.runtime.snapshots.default_cutoff)[1].get((customer_id, Product(product)))
        return result.model_copy(deep=True) if result else None

    def get_impact_input(self, customer_id, product):
        return None

    def list_history(self):
        if self._history is None:
            from greenpath.recommendation.service import RecommendationService
            records = []
            outcomes = {}
            outcome_path = self._outcome_path
            if outcome_path is not None and outcome_path.is_file():
                import pandas as pd
                frame = pd.read_parquet(outcome_path, columns=["cutoff", "customer_id", "product", "observed_adoption_90d"])
                outcomes = {(pd.Timestamp(row.cutoff).date(), row.customer_id, Product(row.product)): int(row.observed_adoption_90d)
                            for row in frame.itertuples(index=False) if pd.notna(row.observed_adoption_90d)}
            for cutoff in self.runtime.snapshots.cutoffs:
                snapshots, propensities = self._at(cutoff)
                class CutoffProvider:
                    impact_calculators = self.impact_calculators
                    def get_snapshot(self, customer_id):
                        return snapshots.get(customer_id)
                    def get_propensity(self, customer_id, product):
                        return propensities.get((customer_id, product))
                    def get_impact_input(self, customer_id, product):
                        return None
                provider = CutoffProvider()
                # Evaluate against that month's evidence, never copy current decisions.
                service = RecommendationService(provider, provider, provider,
                    clock=lambda c=cutoff: datetime.combine(c, time.max, tzinfo=timezone.utc))
                for customer_id in snapshots:
                    records.extend(HistoryRecord(customer_id=customer_id, month=cutoff.strftime("%Y-%m"),
                                                 product=r.product, state=r.state,
                                                 propensity=r.propensity.probability if r.propensity else None,
                                                 confidence=r.propensity.confidence if r.propensity and r.propensity.confidence_validated else None,
                                                 trust_score=r.trust.score,
                                                 observed_adoption_90d=outcomes.get((cutoff, customer_id, r.product)),
                                                 confidence_high=(r.propensity.source_result.confidence.bucket.value == "HIGH"
                                                     if r.propensity and r.propensity.confidence_validated and r.propensity.source_result
                                                     and r.propensity.source_result.confidence.bucket else None),
                                                 is_paperless=(snapshots[customer_id].source_snapshot.digital.is_paperless
                                                     if r.product == Product.PAPERLESS_BANKING else None))
                                   for r in service.recommendations(customer_id))
                if cutoff != self.runtime.snapshots.default_cutoff:
                    del self._cache[cutoff]
            self._history = tuple(records)
        return self._history


def default_repository(mode=None):
    from greenpath.demo.providers import DemoRepository
    selected = mode or os.environ.get("GREENPATH_PROVIDER", "auto")
    if selected not in {"auto", "fixture", "trained"}:
        raise ValueError("GREENPATH_PROVIDER must be auto, fixture or trained")
    if selected == "fixture":
        return DemoRepository()
    # Partial artifacts count as a trained installation and must fail visibly.
    has_artifacts = (Path(config.ARTIFACT_DIR) / "models").exists() or any(Path(config.PROCESSED_DIR).glob("customer360_*.parquet"))
    return ArtifactRepository() if selected == "trained" or has_artifacts else DemoRepository()
