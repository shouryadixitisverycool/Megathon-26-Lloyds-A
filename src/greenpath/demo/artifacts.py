"""Adapt trained, point-in-time ML evidence to the product/API contract."""

from datetime import datetime, time, timezone
from decimal import Decimal
from pathlib import Path
import os
import json

from greenpath import config
from greenpath.contracts.enums import ConfidenceStatus, FuelType, Severity, TrustIssueCategory
from greenpath.contracts.product import (
    CustomerSnapshot, FeatureEvidence, HistoryRecord, PropensityResult, TrustAssessment, TrustIssue,
)
from greenpath.impact import Product
from greenpath.impact.uk_adapter import build_uk_registry


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

    def __init__(self, runtime=None, scenario_provider=None):
        injected_runtime = runtime is not None
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
        if scenario_provider is None and not injected_runtime:
            import pandas as pd
            from greenpath.pipelines.scenario_provider import ScenarioProvider
            path = config.RAW_DIR / "scenario_evidence.parquet"
            if path.is_file():
                scenario_provider = ScenarioProvider(pd.read_parquet(path))
        self.scenario_provider = scenario_provider
        self.version = "trained:" + ",".join(runtime.bundles[p].model_version for p in Product)
        self.impact_calculators = build_uk_registry()
        self._cache = {}
        self._history = None
        self._overrides = {}
        self._source_history = {}
        manifest = config.REPORTS_DIR / "RUN_MANIFEST.json"
        self.run_identity = (getattr(runtime, "run_identity", None) if injected_runtime else
                             json.loads(manifest.read_text()) if manifest.is_file() else None)

    def bind_store(self, store):
        from greenpath.contracts.customer import CustomerSnapshot as SourceSnapshot
        for event in store.source_updates():
            self.override_source_snapshot(SourceSnapshot.model_validate(event["source_snapshot"]))

    def override_source_snapshot(self, snapshot):
        from greenpath.contracts.customer import CustomerSnapshot as SourceSnapshot
        snapshot = SourceSnapshot.model_validate(snapshot.model_dump(mode="python"))
        previous = self.get_snapshot(snapshot.customer_id)
        if previous is None:
            raise KeyError(snapshot.customer_id)
        self.list_history()
        if snapshot.customer_id not in self._source_history:
            self._source_history[snapshot.customer_id] = [previous.source_snapshot.model_copy(deep=True)]
        self._overrides[snapshot.customer_id] = snapshot.model_copy(deep=True)
        self._source_history.setdefault(snapshot.customer_id, []).append(snapshot.model_copy(deep=True))
        self._cache.pop(self.runtime.snapshots.default_cutoff, None)

    def source_snapshot_history(self, customer_id):
        return tuple(s.model_copy(deep=True) for s in self._source_history.get(customer_id, ()))

    def restore_source_snapshot(self, snapshot):
        """Undo an uncommitted local override without invoking the failed scorer again."""
        self._overrides[snapshot.customer_id] = snapshot.model_copy(deep=True)
        history = self._source_history.get(snapshot.customer_id, [])
        if len(history) > 1:
            history.pop()
        self._cache.pop(self.runtime.snapshots.default_cutoff, None)

    def _at(self, cutoff):
        if cutoff not in self._cache:
            sources = self.runtime.snapshots.snapshots(cutoff)
            if cutoff == self.runtime.snapshots.default_cutoff:
                sources = [self._overrides.get(s.customer_id, s) for s in sources]
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
                observed = (source.source_events[-1].feature_cutoff if source.source_events
                            else datetime.combine(source.feature_cutoff, time.min, tzinfo=timezone.utc))
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
                         key: FeatureEvidence(value=value, reference=f"customer360:{source.feature_version}:{source.feature_cutoff}:{source.customer_id}:{key}" +
                                              (f":source-update:{source.source_events[-1].request_id}" if source.source_events else ""),
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
        Product(product)
        snapshot = self.get_snapshot(customer_id)
        if snapshot is None:
            return None
        return (self.scenario_provider.attach(snapshot.source_snapshot, product)
                if self.scenario_provider is not None else snapshot.source_snapshot)

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
                        Product(product)
                        snapshot = snapshots.get(customer_id)
                        if snapshot is None:
                            return None
                        source = snapshot.source_snapshot.model_copy(deep=True)
                        return (self.scenario_provider.attach(source, product)
                                if self.scenario_provider is not None else source)
                    scenario_provider = self.scenario_provider
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
                                                  impact_value=r.impact.value, impact_status=r.impact.status.value,
                                                  impact_units=str(r.impact.units),
                                                  impact=r.impact, data_quality=r.trust.status,
                                                  missing_fields=tuple(snapshots[customer_id].source_snapshot.data_quality.missing_fields),
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
