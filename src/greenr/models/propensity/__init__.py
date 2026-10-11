"""Product propensity models (T4): features, heuristics, training, calibration, reasons, provider."""

from greenr.models.propensity.artifacts import (
    bundle_manifest,
    load_all,
    load_bundle,
    save_all,
    save_bundle,
)
from greenr.models.propensity.calibration import Calibrator
from greenr.models.propensity.features import (
    PRODUCT_FEATURES,
    PROXY_ABLATION_FEATURES,
    add_proxy_features,
    population_mask,
)
from greenr.models.propensity.provider import ModelPropensityProvider
from greenr.models.propensity.reason_codes import (
    REASON_CODE_CATALOGUE,
    derive_reason_codes,
    fit_reason_thresholds,
)
from greenr.models.propensity.training import (
    ProductModelBundle,
    logistic_contributions,
    predict_calibrated,
    predict_raw,
    train_product,
)

__all__ = [
    "Calibrator", "ModelPropensityProvider", "PRODUCT_FEATURES", "PROXY_ABLATION_FEATURES",
    "ProductModelBundle", "REASON_CODE_CATALOGUE", "add_proxy_features", "bundle_manifest",
    "derive_reason_codes", "fit_reason_thresholds", "load_all", "load_bundle",
    "logistic_contributions", "population_mask", "predict_calibrated", "predict_raw", "save_all",
    "save_bundle", "train_product",
]
