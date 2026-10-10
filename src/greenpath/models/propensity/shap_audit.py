"""Exact deployed-model SHAP in raw, uncalibrated log-odds space, not probability space."""

from pathlib import Path
import json

import numpy as np
import pandas as pd
from xgboost import DMatrix

from greenpath.contracts import ModelType
from greenpath.models.propensity.features import prepare_matrix
from greenpath.models.propensity.training import ProductModelBundle


def audit_shap(bundle: ProductModelBundle, frame: pd.DataFrame,
               output_path: str | Path | None = None) -> dict:
    """Explain the selected model; optionally persist the JSON-safe result.

    Linear SHAP uses the independent/interventional game on the transformed training
    background, including missing indicators. Tree SHAP uses XGBoost's exact
    tree-path-dependent game with training cover as background. Neither explains the
    nonlinear calibrator, and neither is a causal attribution.
    """
    x = prepare_matrix(frame, bundle.features)
    if bundle.selected_model_type is ModelType.LOGISTIC:
        if bundle.shap_background_mean is None:
            raise ValueError("missing fitted SHAP background; retrain the model")
        pre, clf = bundle.logistic[:-1], bundle.logistic[-1]
        names = list(pre.get_feature_names_out(bundle.features))
        values = (pre.transform(x) - bundle.shap_background_mean) * clf.coef_[0]
        base = np.full(len(frame), float(clf.intercept_[0] + bundle.shap_background_mean @ clf.coef_[0]))
        margin = bundle.logistic.decision_function(x)
        method = "exact_linear_interventional"
        background = {"source": "transformed_training_population", "rows": bundle.shap_background_rows}
    elif bundle.selected_model_type is ModelType.GRADIENT_BOOSTING:
        booster = bundle.gbm.get_booster()
        matrix = DMatrix(x)
        contributions = booster.predict(matrix, pred_contribs=True, approx_contribs=False)
        values, base = contributions[:, :-1], contributions[:, -1]
        margin = booster.predict(matrix, output_margin=True)
        names = bundle.features
        method = "exact_tree_path_dependent"
        background = {"source": "fitted_tree_training_cover", "rows": bundle.n_train}
    else:
        raise ValueError("SHAP auditor requires a deployed logistic or XGBoost model")
    residual = margin - (base + values.sum(axis=1))
    if not np.allclose(residual, 0, atol=2e-5, rtol=0):
        raise AssertionError("SHAP raw-margin additivity failed")
    result = {
        "product": bundle.product.value, "model_version": bundle.model_version,
        "model_type": bundle.selected_model_type.value, "method": method,
        "output_space": "raw_uncalibrated_log_odds", "explains_calibrated_probability": False,
        "background": background, "feature_names": names,
        "rows": [{"customer_id": str(cid), "base_value": float(b), "raw_margin": float(m),
                  "shap_values": dict(zip(names, map(float, v), strict=True)),
                  "additivity_residual": float(r)}
                 for cid, b, m, v, r in zip(frame.index, base, margin, values, residual, strict=True)],
    }
    if output_path is not None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    return result
