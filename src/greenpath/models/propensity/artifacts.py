"""Save / load propensity bundles (joblib) and the JSON model manifest.

Layout: ``<root>/models/<product_slug>[_<variant>]/bundle.joblib`` + ``manifest.json`` and an
aggregate ``<root>/models/manifest.json``; ``root`` defaults to ``config.ARTIFACT_DIR``.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path

import joblib

from greenpath import config
from greenpath.contracts import Product
from greenpath.models.propensity.features import product_slug
from greenpath.models.propensity.heuristics import HeuristicModel  # noqa: F401  (pickle dependency)
from greenpath.models.propensity.training import ProductModelBundle


def _models_dir(root: Path | None) -> Path:
    return Path(root if root is not None else config.ARTIFACT_DIR) / "models"


def bundle_dir(product: Product, variant: str = "", root: Path | None = None) -> Path:
    name = product_slug(product) + (f"_{variant}" if variant else "")
    return _models_dir(root) / name


def bundle_manifest(b: ProductModelBundle) -> dict:
    return {
        "product": b.product.value,
        "variant": b.variant,
        "seed": b.seed,
        "selected_model_type": b.selected_model_type.value,
        "model_version": b.model_version,
        "model_versions": {k.value: v for k, v in b.model_versions.items()},
        "calibration_method": b.calibrator.method,
        "calibration_version": b.calibration_version,
        "calibration_cv_brier": b.calibrator.cv_brier,
        "operational_threshold": b.threshold,
        "thresholds": {k.value: v for k, v in b.thresholds.items()},
        "threshold_rule": "max F1 on validation calibrated probabilities (in-sample)",
        "features": b.features,
        "logistic_c": b.logistic_c,
        "heuristic_rules": b.heuristic.describe(),
        "reason_thresholds": b.reason_thresholds,
        "reason_version": "reasons_v1",
        "validation_metrics": {k.value: v for k, v in b.validation_metrics.items()},
        "training_rows": b.n_train,
        "training_positives": b.n_train_positive,
        "validation_rows": b.n_validation,
        "validation_positives": b.n_validation_positive,
        "notes": b.notes,
    }


def save_bundle(b: ProductModelBundle, root: Path | None = None) -> Path:
    d = bundle_dir(b.product, b.variant, root)
    d.mkdir(parents=True, exist_ok=True)
    joblib.dump(b, d / "bundle.joblib")
    (d / "manifest.json").write_text(json.dumps(bundle_manifest(b), indent=2, default=str))
    return d


def load_bundle(product: Product, variant: str = "", root: Path | None = None) -> ProductModelBundle:
    path = bundle_dir(product, variant, root) / "bundle.joblib"
    if not path.exists():
        raise FileNotFoundError(path)
    return joblib.load(path)


def save_all(bundles: Mapping[Product, ProductModelBundle] | Iterable[ProductModelBundle],
             root: Path | None = None) -> Path:
    items = list(bundles.values()) if isinstance(bundles, Mapping) else list(bundles)
    for b in items:
        save_bundle(b, root)
    manifest = _models_dir(root) / "manifest.json"
    manifest.write_text(json.dumps({b.product.value: bundle_manifest(b) for b in items}, indent=2, default=str))
    return manifest


def load_all(products: Iterable[Product] | None = None, variant: str = "",
             root: Path | None = None) -> dict[Product, ProductModelBundle]:
    products = list(products) if products is not None else list(Product)
    return {p: load_bundle(p, variant, root) for p in products}
