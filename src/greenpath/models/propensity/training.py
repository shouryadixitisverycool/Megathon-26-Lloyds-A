"""Per-product propensity training: heuristic, logistic regression and boosted trees.

Protocol (spec 9, 11-14):
* fit on ``split == "train"`` rows inside the product population;
* tune the logistic C (small grid) and select the deployed model on VALIDATION only
  (ROC-AUC; Brier tie-break within ``AUC_TIE``); test/demo rows are never read;
* fit one calibrator per candidate on validation raw scores; choose the F1-optimal
  operational threshold on validation calibrated probabilities (in-sample, documented).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from xgboost import XGBClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from greenpath.config import SEED_MODEL
from greenpath.contracts import ModelType, Product
from greenpath.models.propensity.calibration import Calibrator
from greenpath.models.propensity.features import (
    PRODUCT_FEATURES,
    PROXY_ABLATION_FEATURES,
    check_features,
    population_mask,
    prepare_matrix,
    product_slug,
)
from greenpath.models.propensity.heuristics import HeuristicModel
from greenpath.models.propensity.reason_codes import fit_reason_thresholds

AUC_TIE = 0.002
LOGISTIC_C_GRID = (0.01, 0.1, 1.0, 10.0)
CANDIDATES = (ModelType.LOGISTIC, ModelType.GRADIENT_BOOSTING)  # eligible for deployment
_MODEL_SLUG = {ModelType.HEURISTIC: "heuristic", ModelType.LOGISTIC: "logreg",
               ModelType.GRADIENT_BOOSTING: "gbm"}
_IND = "missingindicator_"


@dataclass
class ProductModelBundle:
    product: Product
    variant: str  # "" (default, no proxies) or e.g. "proxy"
    features: list[str]
    seed: int
    heuristic: HeuristicModel
    logistic: Pipeline
    gbm: XGBClassifier
    logistic_c: float
    selected_model_type: ModelType
    model_versions: dict[ModelType, str]
    calibrators: dict[ModelType, Calibrator]
    thresholds: dict[ModelType, float]
    reason_thresholds: dict[str, float]
    validation_metrics: dict[ModelType, dict[str, float]]
    n_train: int
    n_train_positive: int
    n_validation: int
    n_validation_positive: int
    notes: list[str] = field(default_factory=list)
    shap_background_mean: np.ndarray | None = None
    shap_background_rows: int = 0

    @property
    def model_version(self) -> str:
        return self.model_versions[self.selected_model_type]

    @property
    def calibrator(self) -> Calibrator:
        return self.calibrators[self.selected_model_type]

    @property
    def threshold(self) -> float:
        return self.thresholds[self.selected_model_type]

    @property
    def calibration_version(self) -> str:
        return self.calibrator.version


def _logistic_pipeline(c: float, seed: int) -> Pipeline:
    return Pipeline([
        ("impute", SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)),
        ("scale", StandardScaler()),
        ("clf", LogisticRegression(C=c, max_iter=5000, random_state=seed)),
    ])


def _gbm(seed: int) -> XGBClassifier:
    return XGBClassifier(
        learning_rate=0.05, n_estimators=200, max_depth=4, min_child_weight=10,
        reg_lambda=1.0, subsample=1.0, colsample_bytree=1.0,
        tree_method="hist", device="cpu", n_jobs=1, random_state=seed,
        objective="binary:logistic", eval_metric="logloss")


def _safe_auc(y: np.ndarray, s: np.ndarray) -> float:
    return float(roc_auc_score(y, s)) if len(np.unique(y)) == 2 else float("nan")


def best_f1_threshold(y: np.ndarray, p: np.ndarray, max_candidates: int = 400) -> float:
    """Threshold maximising F1 over candidate calibrated probabilities (ties -> higher)."""
    y = np.asarray(y).astype(int)
    if y.sum() == 0:
        return 0.5
    cands = np.unique(p)
    if len(cands) > max_candidates:
        cands = np.unique(np.quantile(p, np.linspace(0, 1, max_candidates)))
    best_t, best_f1 = 0.5, -1.0
    for t in cands:
        pred = p >= t
        tp = float((pred & (y == 1)).sum())
        denom = 2 * tp + float((pred & (y == 0)).sum()) + float((~pred & (y == 1)).sum())
        f1 = 2 * tp / denom if denom else 0.0
        if f1 >= best_f1:
            best_t, best_f1 = float(t), f1
    return best_t


def select_model_type(metrics: dict[ModelType, dict[str, float]]) -> ModelType:
    """Highest validation ROC-AUC among candidates; Brier breaks ties within AUC_TIE."""
    scored = [(m, metrics[m]["roc_auc"], metrics[m]["brier_raw"]) for m in CANDIDATES]
    scored = [t for t in scored if not np.isnan(t[1])]
    if not scored:
        return ModelType.LOGISTIC
    top = max(t[1] for t in scored)
    tied = [t for t in scored if top - t[1] < AUC_TIE]
    # prefer lowest Brier; stable order (logistic first) on exact ties
    return min(tied, key=lambda t: (t[2], CANDIDATES.index(t[0])))[0]


def train_product(
    frame: pd.DataFrame,
    labels: pd.DataFrame,
    split: pd.Series,
    product: Product,
    seed: int = SEED_MODEL,
    extra_features: Sequence[str] = (),
    variant: str = "",
) -> ProductModelBundle:
    """Train, select, calibrate and threshold the models for one product.

    ``frame``: Customer 360 (index customer_id). ``labels``: index customer_id, one 0/1 column
    per Product value. ``split``: Series customer_id -> train|validation|test|demo.
    ``extra_features`` (e.g. ``PROXY_ABLATION_FEATURES`` after ``add_proxy_features``) with
    ``variant="proxy"`` trains the with-proxy ablation model.
    """
    features = [f for f in PRODUCT_FEATURES[product] if f in frame.columns]
    features += [f for f in extra_features if f not in features]
    # An ablation may admit only the explicitly approved proxy encodings. It must
    # still reject target columns and post-adoption flags on every entry path.
    check_features(product, features)
    allowed = set(PRODUCT_FEATURES[product])
    if variant == "proxy":
        allowed.update(PROXY_ABLATION_FEATURES)
    unapproved = sorted(set(features) - allowed)
    if unapproved:
        raise ValueError(f"unapproved features for {product}: {unapproved}")
    if not features:
        raise ValueError(f"no usable features for {product}")

    ids = frame.index.intersection(labels.index).intersection(split.index)
    sub = frame.loc[ids]
    in_pop, _ = population_mask(sub, product)
    sp = split.loc[ids]
    y_all = labels.loc[ids, product.value].to_numpy().astype(int)
    X_all = prepare_matrix(sub, features)

    tr = (in_pop & (sp == "train")).to_numpy()
    va = (in_pop & (sp == "validation")).to_numpy()
    X_tr, y_tr, X_va, y_va = X_all[tr], y_all[tr], X_all[va], y_all[va]
    if len(np.unique(y_tr)) < 2:
        raise ValueError(f"{product}: training population has a single class")
    if len(np.unique(y_va)) < 2:
        raise ValueError(f"{product}: validation population has a single class; cannot calibrate")

    slug = product_slug(product) + (f"_{variant}" if variant else "")
    heuristic = HeuristicModel.fit(product, X_tr)

    # Logistic: light tuning of C on validation AUC (Brier tie-break).
    best_c, best_key, logit = 1.0, None, None
    for c in LOGISTIC_C_GRID:
        pipe = _logistic_pipeline(c, seed).fit(X_tr, y_tr)
        p = pipe.predict_proba(X_va)[:, 1]
        key = (-round(_safe_auc(y_va, p), 6), brier_score_loss(y_va, p))
        if best_key is None or key < best_key:
            best_c, best_key, logit = c, key, pipe
    gbm = _gbm(seed).fit(X_tr, y_tr)

    raw_val = {
        ModelType.HEURISTIC: heuristic.score(X_va),
        ModelType.LOGISTIC: logit.predict_proba(X_va)[:, 1],
        ModelType.GRADIENT_BOOSTING: gbm.predict_proba(X_va)[:, 1],
    }
    metrics: dict[ModelType, dict[str, float]] = {}
    calibrators: dict[ModelType, Calibrator] = {}
    thresholds: dict[ModelType, float] = {}
    for mt, raw in raw_val.items():
        brier_raw = float(brier_score_loss(y_va, raw)) if mt is not ModelType.HEURISTIC else float("nan")
        cal = Calibrator.fit(raw, y_va, name=f"{slug}_{_MODEL_SLUG[mt]}", seed=seed)
        p_cal = cal.transform(raw)
        calibrators[mt] = cal
        thresholds[mt] = best_f1_threshold(y_va, p_cal)
        metrics[mt] = {"roc_auc": _safe_auc(y_va, raw), "brier_raw": brier_raw,
                       "brier_calibrated_insample": float(brier_score_loss(y_va, p_cal))}

    selected = select_model_type(metrics)
    return ProductModelBundle(
        product=product, variant=variant, features=features, seed=seed, heuristic=heuristic,
        logistic=logit, gbm=gbm, logistic_c=best_c, selected_model_type=selected,
        model_versions={mt: f"{slug}_{_MODEL_SLUG[mt]}_v1" for mt in raw_val},
        calibrators=calibrators, thresholds=thresholds,
        reason_thresholds=fit_reason_thresholds(sub.loc[tr]),
        validation_metrics=metrics, n_train=int(tr.sum()), n_train_positive=int(y_tr.sum()),
        n_validation=int(va.sum()), n_validation_positive=int(y_va.sum()),
        shap_background_mean=logit[:-1].transform(X_tr).mean(axis=0),
        shap_background_rows=len(X_tr),
        notes=["Gradient boosting candidate: XGBoost CPU hist, one thread, fixed seed. "
               "Deployment selected against logistic baseline on validation raw AUC/Brier; "
               "heuristic is a ranking benchmark, not a probabilistic deployment candidate."],
    )


def predict_raw(bundle: ProductModelBundle, frame: pd.DataFrame,
                model_type: ModelType | None = None) -> np.ndarray:
    """Uncalibrated score of ``model_type`` (default: the selected model) for every row."""
    mt = model_type or bundle.selected_model_type
    X = prepare_matrix(frame, bundle.features)
    if mt is ModelType.HEURISTIC:
        return bundle.heuristic.score(X)
    if mt is ModelType.LOGISTIC:
        return bundle.logistic.predict_proba(X)[:, 1]
    return bundle.gbm.predict_proba(X)[:, 1]


def predict_calibrated(bundle: ProductModelBundle, frame: pd.DataFrame,
                       model_type: ModelType | None = None) -> np.ndarray:
    mt = model_type or bundle.selected_model_type
    return bundle.calibrators[mt].transform(predict_raw(bundle, frame, mt))


def logistic_contributions(bundle: ProductModelBundle, frame: pd.DataFrame) -> pd.DataFrame:
    """Per-row, per-feature logistic contributions (coefficient x standardised, imputed value).

    Columns are ``bundle.features``; missing-indicator terms are not attributed to a feature.
    This logistic surrogate explains every deployed model (reason-code ordering only).
    """
    X = prepare_matrix(frame, bundle.features)
    pre = bundle.logistic[:-1]
    names = list(pre.get_feature_names_out(bundle.features))
    contrib = pre.transform(X) * bundle.logistic[-1].coef_[0]
    keep = [i for i, n in enumerate(names) if not n.startswith(_IND)]
    return pd.DataFrame(contrib[:, keep], index=frame.index, columns=[names[i] for i in keep])
