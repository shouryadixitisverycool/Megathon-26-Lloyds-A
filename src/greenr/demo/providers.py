"""Versioned synthetic fixtures, never a substitute for Agent A's ML evidence."""

import json
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from importlib.resources import files

from greenr.contracts.product import (
    APPROVED_FEATURES, CustomerSnapshot, FeatureEvidence, HistoryRecord,
    PropensityResult, RecommendationState, TrustAssessment, TrustIssue,
)
from greenr.impact import Product

FIXTURE_VERSION = "agent-b-synthetic-personas-v1"
CUTOFF = datetime(2026, 1, 3, tzinfo=timezone.utc)
OBSERVED = datetime(2026, 1, 2, tzinfo=timezone.utc)
ADOPTION_FLAGS = {"already_has_ev", "efficient_home", "solar_installed", "paperless_active"}
PRODUCT_FILES = {
    Product.EV_FINANCE: "ev.json", Product.GREEN_HOME: "green_home.json",
    Product.SOLAR_FINANCE: "solar.json", Product.PAPERLESS_BANKING: "paperless.json",
}
PERSONAS = (
    ("GP-001", "Asha Rao", "South", "Salaried", RecommendationState.RECOMMEND),
    ("GP-002", "Ravi Shah", "West", "Self-employed", RecommendationState.INSUFFICIENT_INFORMATION),
    ("GP-003", "Meera Sen", "East", "Salaried", RecommendationState.CONFLICT_REQUIRES_REVIEW),
    ("GP-004", "Kabir Malik", "North", "Retired", RecommendationState.NOT_APPLICABLE),
    ("GP-005", "Nila Das", "East", "Self-employed", RecommendationState.SUPPRESSED),
    ("GP-006", "Dev Iyer", "South", "Retired", RecommendationState.DO_NOT_RECOMMEND),
)


class DemoRepository:
    """Implements the four provider mirrors with independent copies on reads."""

    mode = "fixture"
    version = FIXTURE_VERSION

    def __init__(self):
        self._snapshots = {}
        self._propensities = {}
        self._inputs = {}
        self._history = []
        for customer_id, name, region, segment, state in PERSONAS:
            features = {
                feature: FeatureEvidence(
                    value=feature not in ADOPTION_FLAGS,
                    reference=f"synthetic:{FIXTURE_VERSION}:{customer_id}:{feature}",
                    observed_at=OBSERVED, freshness="current",
                )
                for feature in sorted(APPROVED_FEATURES)
            }
            trust = TrustAssessment(score=Decimal("0.95"), status="TRUSTED")
            if customer_id == "GP-002":
                for key in ("owns_vehicle", "owns_home", "paper_statements"):
                    features.pop(key)
                trust = TrustAssessment(score=Decimal("0.45"), status="LIMITED", issues=(
                    TrustIssue(code="MISSING_EVIDENCE", field="features", severity="WARNING",
                               message="Synthetic persona has missing ownership and statement evidence."),
                ))
            elif customer_id == "GP-003":
                for key in ("ev_interest", "owns_home", "paper_statements"):
                    features[key] = features[key].model_copy(update={"conflicts": ("Synthetic conflicting declarations",)})
                trust = TrustAssessment(score=Decimal("0.30"), status="CONFLICT", issues=(
                    TrustIssue(code="CONFLICTING_EVIDENCE", field="features", severity="HIGH",
                               message="Synthetic declarations conflict and require review."),
                ))
            elif customer_id == "GP-004":
                for key in ADOPTION_FLAGS:
                    features[key] = features[key].model_copy(update={"value": True})
            elif customer_id == "GP-005":
                features["marketing_consent"] = features["marketing_consent"].model_copy(update={"value": False})
            self._snapshots[customer_id] = CustomerSnapshot(
                customer_id=customer_id, display_name=name, region=region, segment=segment,
                feature_cutoff=CUTOFF, features=features, trust=trust,
            )
            for product in Product:
                probability = Decimal("0.25") if customer_id == "GP-006" else Decimal("0.82")
                self._propensities[(customer_id, product)] = PropensityResult(
                    product=product, probability=probability,
                    model_version="synthetic-probability-fixture-v1",
                    calibration_version="synthetic-calibration-fixture-v1",
                )
                raw = json.loads(files("greenr.demo").joinpath("fixtures", PRODUCT_FILES[product]).read_text())
                self._inputs[(customer_id, product)] = None if customer_id == "GP-002" else raw
                # Explicit historical fixture states; not reconstructed from scores.
                for month, historical_state in (
                    ("2025-10", RecommendationState.DO_NOT_RECOMMEND if customer_id == "GP-001" else state),
                    ("2025-11", RecommendationState.INSUFFICIENT_INFORMATION if customer_id == "GP-001" else state),
                    ("2025-12", state),
                ):
                    self._history.append(HistoryRecord(
                        customer_id=customer_id, month=month, product=product, state=historical_state,
                    ))

    def get_snapshot(self, customer_id):
        snapshot = self._snapshots.get(customer_id)
        return snapshot.model_copy(deep=True) if snapshot is not None else None

    def list_snapshots(self):
        return tuple(snapshot.model_copy(deep=True) for snapshot in self._snapshots.values())

    def get_propensity(self, customer_id, product):
        result = self._propensities.get((customer_id, Product(product)))
        return result.model_copy(deep=True) if result is not None else None

    def get_impact_input(self, customer_id, product):
        return deepcopy(self._inputs.get((customer_id, Product(product))))

    def list_history(self):
        return tuple(self._history)
