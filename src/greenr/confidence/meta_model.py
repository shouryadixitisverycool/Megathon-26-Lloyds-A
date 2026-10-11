"""Validated confidence meta-model (spec 16, 17.4).

Definition (spec 16.3, option 1)
--------------------------------
Confidence is the *empirically validated probability that the displayed calibrated
propensity yields a CORRECT decision at the product's operational threshold*:

    correct = ((calibrated_p >= threshold) == observed_outcome)

It is NOT eligibility, NOT a second propensity, and it never changes the propensity.
It is model-agnostic: it only receives arrays (calibrated probabilities, per-row
diagnostics, observed outcomes), so it can be built and tested without the models.

Features (spec 16.2)
--------------------
``margin``          |p - threshold| / threshold. Scaling by the threshold makes products
                    with low base rates (low thresholds) comparable.
``local_cal_error`` calibration error in the neighbourhood of the prediction (caller).
``ood_score``       out-of-distribution score from the Trust layer (caller).
``instability``     prediction spread under plausible missing-value perturbations
                    (see :func:`perturbation_stability`).
``recency_days``    data recency summary (days since the freshest relevant record).

Raw completeness is deliberately NOT a feature: it belongs to the Trust Score (spec 15,
16.2) and including it would double-count the same factor. Only an ablation showing
incremental value could justify adding it.

Meta-model
----------
Interpretable ``LogisticRegression`` on median-imputed, standardised, clipped (+-5 sd)
features, trained on VALIDATION predictions only. Release selection uses reserved validation
data (see ``validation.validate_confidence``); if validation fails, confidence is
SUPPRESSED (``to_results``) and never shown.

Buckets are learned from the validation confidence distribution: top 40% of validation
rows are HIGH (value >= 60th percentile), bottom 30% LOW (value < 30th percentile), the
rest MEDIUM. Cut-offs are stored and re-applied to new data.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

from greenr.contracts.enums import ConfidenceBucket, ConfidenceStatus
from greenr.contracts.propensity import ConfidenceResult

METHOD_VERSION = "conf_meta_v2"
FEATURE_COLUMNS = ["margin", "local_cal_error", "ood_score", "instability", "recency_days"]
HIGH_QUANTILE = 0.60  # rows at/above this validation quantile -> HIGH (top 40%)
LOW_QUANTILE = 0.30  # rows below this validation quantile -> LOW (bottom 30%)
_CLIP_SD = 5.0


# --------------------------------------------------------------------------- features
def _as_column(x, n: int, name: str) -> np.ndarray:
    arr = np.asarray(x, dtype=float)
    if arr.ndim == 0:
        return np.full(n, float(arr))
    arr = arr.reshape(-1)
    if len(arr) != n:
        raise ValueError(f"{name} has length {len(arr)}, expected {n}")
    return arr


def build_confidence_features(
    calibrated_p, threshold: float, local_calibration_error, ood_score, stability, recency_days
) -> pd.DataFrame:
    """Assemble the confidence feature frame (columns ``FEATURE_COLUMNS``).

    ``margin = |p - threshold| / threshold`` (threshold-scaled so low-base-rate products
    are comparable). Scalars are broadcast; NaN is allowed (imputed by the model).
    No completeness column is produced (owned by Trust).
    """
    if not threshold or threshold <= 0:
        raise ValueError("threshold must be > 0")
    p = np.asarray(calibrated_p, dtype=float).reshape(-1)
    n = len(p)
    return pd.DataFrame(
        {
            "margin": np.abs(p - threshold) / threshold,
            "local_cal_error": _as_column(local_calibration_error, n, "local_calibration_error"),
            "ood_score": _as_column(ood_score, n, "ood_score"),
            "instability": _as_column(stability, n, "stability"),
            "recency_days": _as_column(recency_days, n, "recency_days"),
        }
    )


def local_calibration_gap(
    calibrated_p, reference_p, reference_y, n_bins: int = 10
) -> np.ndarray:
    """Per-row local calibration error: |mean(y) - mean(p)| of the reference bin holding p.

    Bins are quantile bins of ``reference_p`` (use calibration/train-side data, not the
    rows the meta-model is later evaluated on).
    """
    rp = np.asarray(reference_p, dtype=float)
    ry = np.asarray(reference_y, dtype=float)
    edges = np.unique(np.quantile(rp, np.linspace(0, 1, n_bins + 1)))
    if len(edges) < 2:
        return np.full(len(np.asarray(calibrated_p)), abs(ry.mean() - rp.mean()))
    ref_bin = np.clip(np.searchsorted(edges, rp, side="right") - 1, 0, len(edges) - 2)
    gaps = np.array(
        [abs(ry[ref_bin == b].mean() - rp[ref_bin == b].mean()) if (ref_bin == b).any() else 0.0
         for b in range(len(edges) - 1)]
    )
    new_bin = np.clip(
        np.searchsorted(edges, np.asarray(calibrated_p, dtype=float), side="right") - 1,
        0, len(edges) - 2,
    )
    return gaps[new_bin]


def perturbation_stability(
    predict_fn: Callable[[pd.DataFrame], np.ndarray],
    frame: pd.DataFrame,
    perturb_columns: Sequence[str],
    seed: int,
    n_draws: int = 5,
    mask_rate: float = 0.3,
) -> np.ndarray:
    """Max absolute change of predicted probability under random missing-value masking.

    Each draw sets every (row, column) cell of ``perturb_columns`` to NaN independently
    with probability ``mask_rate`` (seeded), re-predicts, and records |p_perturbed - p|.
    Returns the max over draws per row (the "instability" feature). Masks depend only on
    canonical numeric values of the approved ``perturb_columns`` and seed/draw/column,
    never on row index, batch composition, order, or unapproved metadata.
    """
    base = np.asarray(predict_fn(frame), dtype=float).reshape(-1)
    out = np.zeros(len(frame))
    cols = sorted(set(perturb_columns))
    if not cols:
        return out
    # Fixed-endian float64 makes integer/float representations equivalent; normalise
    # signed zero and NaN payloads before hashing. Hash no customer IDs or index values.
    values = frame.reindex(columns=cols).to_numpy(dtype="<f8", copy=True)
    values[values == 0] = 0.0
    values[np.isnan(values)] = np.nan
    row_keys = np.fromiter(
        (int.from_bytes(hashlib.blake2b(row.tobytes(), digest_size=8).digest(), "little")
         for row in values), dtype=np.uint64, count=len(frame),
    )
    for draw in range(n_draws):
        pert = frame.copy()
        for c in cols:
            context = json.dumps([int(seed), draw, c, cols], separators=(",", ":")).encode()
            key = int.from_bytes(hashlib.blake2b(context, digest_size=8).digest(), "little")
            # SplitMix64 avalanches each row/context key into uniform 53-bit draws.
            # All arithmetic is vectorised uint64, with intentional modular overflow.
            bits = (row_keys ^ np.uint64(key)) + np.uint64(0x9E3779B97F4A7C15)
            bits = (bits ^ (bits >> 30)) * np.uint64(0xBF58476D1CE4E5B9)
            bits = (bits ^ (bits >> 27)) * np.uint64(0x94D049BB133111EB)
            bits ^= bits >> 31
            mask = (bits >> 11).astype(float) / (1 << 53) < mask_rate
            values_to_mask = pert[c] if c in pert else pd.Series(np.nan, index=pert.index)
            pert[c] = values_to_mask.astype(float).mask(mask)
        pred = np.asarray(predict_fn(pert), dtype=float).reshape(-1)
        out = np.maximum(out, np.abs(pred - base))
    return out


# --------------------------------------------------------------------------- model
def _clip(x):
    return np.clip(x, -_CLIP_SD, _CLIP_SD)


class ConfidenceModel:
    """Logistic meta-model of P(decision correct | confidence features)."""

    method_version = METHOD_VERSION

    def __init__(self, feature_columns: Sequence[str] | None = None, C: float = 1.0):
        self.method_version = METHOD_VERSION
        self.feature_columns = list(feature_columns) if feature_columns else list(FEATURE_COLUMNS)
        self.C = C
        self.pipeline_: Pipeline | None = None
        self.high_threshold_: float | None = None
        self.low_threshold_: float | None = None

    # -- fitting
    def fit(self, features_df: pd.DataFrame, correct) -> "ConfidenceModel":
        """Fit on VALIDATION predictions; ``correct`` is a bool array of decision correctness."""
        y = np.asarray(correct).astype(int)
        if len(y) != len(features_df):
            raise ValueError("features_df and correct differ in length")
        if len(np.unique(y)) < 2:
            raise ValueError("correct must contain both correct and incorrect decisions")
        X = features_df[self.feature_columns]
        self.pipeline_ = Pipeline(
            [
                ("impute", SimpleImputer(strategy="median", keep_empty_features=True)),
                ("scale", StandardScaler()),
                ("clip", FunctionTransformer(_clip)),
                ("lr", LogisticRegression(C=self.C, max_iter=1000)),
            ]
        )
        self.pipeline_.fit(X, y)
        conf = self.predict(features_df)
        self.high_threshold_ = float(np.quantile(conf, HIGH_QUANTILE))
        self.low_threshold_ = float(np.quantile(conf, LOW_QUANTILE))
        return self

    def _check(self) -> Pipeline:
        if self.pipeline_ is None:
            raise RuntimeError("ConfidenceModel is not fitted")
        return self.pipeline_

    def predict(self, features_df: pd.DataFrame) -> np.ndarray:
        """Confidence values in [0, 1]."""
        pipe = self._check()
        return pipe.predict_proba(features_df[self.feature_columns])[:, 1]

    def bucket(self, values) -> list[ConfidenceBucket]:
        """HIGH >= high cut-off; LOW < low cut-off; otherwise MEDIUM (cut-offs from validation)."""
        self._check()
        out = []
        for v in np.asarray(values, dtype=float):
            if v >= self.high_threshold_:
                out.append(ConfidenceBucket.HIGH)
            elif v < self.low_threshold_:
                out.append(ConfidenceBucket.LOW)
            else:
                out.append(ConfidenceBucket.MEDIUM)
        return out

    @property
    def bucket_thresholds(self) -> dict[str, float]:
        self._check()
        return {"low_below": self.low_threshold_, "high_at_or_above": self.high_threshold_}

    def coefficients(self) -> dict[str, float]:
        """Standardised logistic coefficients (+ ``intercept``) for the report."""
        lr = self._check().named_steps["lr"]
        coefs = {c: float(w) for c, w in zip(self.feature_columns, lr.coef_[0])}
        coefs["intercept"] = float(lr.intercept_[0])
        return coefs

    # -- persistence
    def save(self, path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)

    @classmethod
    def load(cls, path) -> "ConfidenceModel":
        obj = joblib.load(path)
        if not isinstance(obj, cls):
            raise TypeError(f"{path} does not contain a ConfidenceModel")
        return obj


# --------------------------------------------------------------------------- contract
def to_results(
    values, buckets, validated: bool, limitation: str | None = None
) -> list[ConfidenceResult]:
    """Convert arrays to ``ConfidenceResult`` objects.

    ``validated=False`` -> every result is SUPPRESSED with no value/bucket and a
    limitation (a default is supplied if none is given). ``validated=True`` -> VALIDATED
    results carrying value and bucket (``limitation`` optional note).
    """
    vals = [] if values is None else list(np.asarray(values, dtype=float))
    n = len(vals) if len(vals) else (0 if buckets is None else len(buckets))
    if not validated:
        text = limitation or (
            "Confidence did not pass held-out validation; it is not shown to users."
        )
        return [
            ConfidenceResult(
                status=ConfidenceStatus.SUPPRESSED, method_version=METHOD_VERSION, limitation=text
            )
            for _ in range(n)
        ]
    if buckets is None or len(buckets) != len(vals):
        raise ValueError("validated results need one bucket per value")
    return [
        ConfidenceResult(
            status=ConfidenceStatus.VALIDATED,
            value=float(np.clip(v, 0.0, 1.0)),
            bucket=ConfidenceBucket(b),
            method_version=METHOD_VERSION,
            limitation=limitation,
        )
        for v, b in zip(vals, buckets)
    ]
