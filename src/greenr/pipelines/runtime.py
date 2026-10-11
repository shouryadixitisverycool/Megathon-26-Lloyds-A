"""Composition root for Agent A's providers.

Loads trained artifacts and wires the concrete adapters behind the ports:
``CustomerSnapshotProvider`` (Customer 360), ``PropensityProvider`` (calibrated models with
validated-or-suppressed confidence) and ``TrustProvider`` (data quality, conflicts, OOD).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from greenr import config
from greenr.confidence.meta_model import (
    METHOD_VERSION,
    ConfidenceModel,
    build_confidence_features,
    perturbation_stability,
    to_results,
)
from greenr.contracts import ConfidenceResult, Product
from greenr.models.propensity import (
    ModelPropensityProvider,
    ProductModelBundle,
    load_all,
    predict_calibrated,
)
from greenr.pipelines.feature_registry import SPEND_CATEGORIES
from greenr.pipelines.snapshot_provider import Customer360SnapshotProvider
from greenr.trust.ood import OODDetector
from greenr.trust.provider import TrustScorer

PRODUCTS = list(Product)
RECENCY_COLUMNS = [f"{c}_days_since_last" for c in SPEND_CATEGORIES]
STABILITY_DRAWS = 5
STABILITY_MASK_RATE = 0.3
CONFIDENCE_DIR = "confidence"
OOD_DIR = "ood"


def recency_days(frame: pd.DataFrame) -> np.ndarray:
    """Days since the freshest categorised transaction (NaN when there is no history)."""
    cols = [c for c in RECENCY_COLUMNS if c in frame.columns]
    if not cols:
        return np.full(len(frame), np.nan)
    return frame[cols].astype("float64").min(axis=1, skipna=True).to_numpy()


def confidence_features(bundle: ProductModelBundle, frame: pd.DataFrame, calibrated_p: np.ndarray,
                        detector: OODDetector | None) -> pd.DataFrame:
    """Meta-model inputs for in-population rows of ``frame`` (spec 16.2)."""
    p = np.asarray(calibrated_p, dtype="float64")
    if not len(frame):
        return build_confidence_features(p, bundle.threshold, p, p, p, p)
    ood = detector.score(frame) if detector is not None else np.zeros(len(frame))
    stability = perturbation_stability(
        lambda f: predict_calibrated(bundle, f), frame,
        perturb_columns=bundle.features,
        seed=config.SEED_MODEL, n_draws=STABILITY_DRAWS, mask_rate=STABILITY_MASK_RATE,
    )
    return build_confidence_features(
        p, bundle.threshold, bundle.calibrator.local_calibration_error(p), ood, stability,
        recency_days(frame),
    )


@dataclass
class ConfidenceScorer:
    """Callable injected into ModelPropensityProvider; surfaces confidence only if validated."""

    bundles: dict[Product, ProductModelBundle]
    models: dict[Product, ConfidenceModel]
    validated: dict[Product, bool]
    limitations: dict[Product, str] = field(default_factory=dict)
    detectors: dict[Product, OODDetector] = field(default_factory=dict)

    def __call__(self, product: Product, frame: pd.DataFrame, calibrated_p: np.ndarray) -> list[ConfidenceResult]:
        n = len(frame)
        if product not in self.models or not self.validated.get(product, False):
            reason = self.limitations.get(product, "Confidence failed held-out reliability validation")
            return to_results(np.full(n, np.nan), None, validated=False, limitation=reason)
        model = self.models[product]
        feats = confidence_features(self.bundles[product], frame, calibrated_p, self.detectors.get(product))
        values = model.predict(feats)
        return to_results(values, model.bucket(values), validated=True)


@dataclass
class Runtime:
    snapshots: Customer360SnapshotProvider
    propensity: ModelPropensityProvider
    trust: TrustScorer
    bundles: dict[Product, ProductModelBundle]
    detectors: dict[Product, OODDetector]
    confidence: ConfidenceScorer


def load_detectors(root: Path | None = None) -> dict[Product, OODDetector]:
    root = (root or config.ARTIFACT_DIR) / OOD_DIR
    return {p: OODDetector.load(root / f"{p.value.lower()}.joblib") for p in PRODUCTS
            if (root / f"{p.value.lower()}.joblib").exists()}


def load_confidence(bundles: dict[Product, ProductModelBundle], detectors: dict[Product, OODDetector],
                    root: Path | None = None) -> ConfidenceScorer:
    root = (root or config.ARTIFACT_DIR) / CONFIDENCE_DIR
    decisions = json.loads((root / "decisions.json").read_text()) if (root / "decisions.json").exists() else {}
    models, validated, limitations = {}, {}, {}
    for p in PRODUCTS:
        path = root / f"{p.value.lower()}.joblib"
        if path.exists():
            models[p] = ConfidenceModel.load(path)
        d = decisions.get(p.value, {})
        validated[p] = bool(d.get("surfaced", False))
        if d.get("limitation"):
            limitations[p] = d["limitation"]
        # Older artifacts were validated with batch-position-dependent masks. They
        # must be refit/revalidated, not surfaced under the changed feature method.
        if p in models and vars(models[p]).get("method_version") != METHOD_VERSION:
            validated[p] = False
            limitations[p] = "Confidence method changed; refit and revalidate confidence artifacts"
    return ConfidenceScorer(bundles, models, validated, limitations, detectors)


def load_runtime(cutoffs: list[date] | None = None, root: Path | None = None) -> Runtime:
    root = root or config.ARTIFACT_DIR
    cutoffs = cutoffs or [config.FEATURE_CUTOFF]
    from greenr.pipelines.snapshot_provider import customer360_path

    snapshots = Customer360SnapshotProvider.from_parquet(
        *[customer360_path(c, config.PROCESSED_DIR) for c in cutoffs])
    bundles = load_all(root=root)
    detectors = load_detectors(root)
    decisions_path = root / CONFIDENCE_DIR / "decisions.json"
    if not decisions_path.is_file():
        raise FileNotFoundError(f"Incomplete trained artifacts: {decisions_path} is missing; rerun train")
    decisions = json.loads(decisions_path.read_text())
    missing = [f"propensity model for {p.value}" for p in PRODUCTS if p not in bundles]
    missing += [f"OOD detector for {p.value}" for p in PRODUCTS if p not in detectors]
    missing += [f"confidence decision for {p.value}" for p in PRODUCTS if p.value not in decisions]
    missing += [f"validated confidence model for {p.value}" for p in PRODUCTS
                if decisions.get(p.value, {}).get("surfaced")
                and not (root / CONFIDENCE_DIR / f"{p.value.lower()}.joblib").is_file()]
    if missing:
        raise FileNotFoundError("Incomplete trained artifacts: " + "; ".join(missing) + "; rerun train")
    confidence = load_confidence(bundles, detectors, root)
    from greenr.trust.selection import load_thresholds
    thresholds = load_thresholds(root / "trust_thresholds.json")
    return Runtime(
        snapshots=snapshots,
        propensity=ModelPropensityProvider(bundles, confidence_scorer=confidence),
        trust=TrustScorer(ood_detectors=detectors, thresholds=thresholds),
        bundles=bundles,
        detectors=detectors,
        confidence=confidence,
    )
