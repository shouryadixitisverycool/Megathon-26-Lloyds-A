"""Probability calibration (spec 14), fit on VALIDATION predictions only.

Method choice (documented): with >= 50 positives and >= 50 negatives in validation, 2-fold
stratified CV on the validation set compares isotonic vs Platt by Brier and the lower wins
(ties go to Platt, the smoother method). With fewer, Platt is used because isotonic overfits.
Output probabilities are clipped to [1e-3, 1 - 1e-3] so no customer is shown as 0% / 100%.

Reliability bins (for the confidence layer's "local calibration error") are computed on the
out-of-fold calibrated validation predictions when CV is possible, otherwise in-sample.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import joblib

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss
from sklearn.model_selection import StratifiedKFold

MIN_CLASS_COUNT_FOR_CV = 50
P_FLOOR = 1e-3
_EPS = 1e-6


def _logit(raw: np.ndarray) -> np.ndarray:
    r = np.clip(np.asarray(raw, dtype="float64"), _EPS, 1 - _EPS)
    return np.log(r / (1 - r))


def _fit_method(method: str, raw: np.ndarray, y: np.ndarray):
    if method == "isotonic":
        return IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip").fit(raw, y)
    if method == "platt":
        return LogisticRegression(C=1e6, max_iter=1000).fit(_logit(raw).reshape(-1, 1), y)
    raise ValueError(f"unknown calibration method {method!r}")


def _apply(method: str, model, raw: np.ndarray) -> np.ndarray:
    raw = np.asarray(raw, dtype="float64")
    if method == "isotonic":
        out = model.predict(raw)
    else:
        out = model.predict_proba(_logit(raw).reshape(-1, 1))[:, 1]
    return np.clip(out, P_FLOOR, 1 - P_FLOOR)


def _reliability_bins(p: np.ndarray, y: np.ndarray, n_bins: int = 10) -> pd.DataFrame:
    edges = np.unique(np.quantile(p, np.linspace(0, 1, n_bins + 1)))
    if len(edges) < 2:
        edges = np.array([p.min(), p.max() + 1e-12])
    idx = np.clip(np.searchsorted(edges[1:-1], p, side="right"), 0, len(edges) - 2)
    rows = []
    for b in range(len(edges) - 1):
        sel = idx == b
        if not sel.any():
            continue
        rows.append({"bin_lower": edges[b], "bin_upper": edges[b + 1], "n": int(sel.sum()),
                     "mean_predicted": float(p[sel].mean()), "observed_rate": float(y[sel].mean())})
    return pd.DataFrame(rows)


@dataclass
class Calibrator:
    method: str  # "isotonic" | "platt"
    version: str  # e.g. "ev_finance_iso_v1"
    model: object
    reliability_bins: pd.DataFrame
    n_fit: int
    n_positive: int
    cv_brier: dict[str, float] = field(default_factory=dict)  # method -> OOF Brier (empty if no CV)

    @classmethod
    def fit(cls, raw_val: np.ndarray, y_val: np.ndarray, name: str, method: str = "auto",
            seed: int = 44, n_bins: int = 10) -> "Calibrator":
        """Fit on validation raw scores / labels. ``name`` is the version prefix (e.g. ev_finance)."""
        raw = np.asarray(raw_val, dtype="float64")
        y = np.asarray(y_val).astype(int)
        if len(raw) != len(y) or len(raw) == 0:
            raise ValueError("calibration needs equally long, non-empty raw scores and labels")
        n_pos, n_neg = int(y.sum()), int((1 - y).sum())
        if n_pos == 0 or n_neg == 0:
            raise ValueError("calibration needs both classes in the validation set")
        oof: dict[str, np.ndarray] = {}
        cv_brier: dict[str, float] = {}
        if min(n_pos, n_neg) >= 2:
            skf = StratifiedKFold(n_splits=2, shuffle=True, random_state=seed)
            for m in ("isotonic", "platt"):
                pred = np.empty(len(raw))
                for tr, te in skf.split(raw, y):
                    pred[te] = _apply(m, _fit_method(m, raw[tr], y[tr]), raw[te])
                oof[m] = pred
                cv_brier[m] = float(brier_score_loss(y, pred))
        if method == "auto":
            if min(n_pos, n_neg) < MIN_CLASS_COUNT_FOR_CV or not cv_brier:
                method = "platt"
            else:
                method = "isotonic" if cv_brier["isotonic"] < cv_brier["platt"] else "platt"
        model = _fit_method(method, raw, y)
        p_for_bins = oof[method] if method in oof else _apply(method, model, raw)
        short = "iso" if method == "isotonic" else "platt"
        identity = hashlib.sha256((joblib.hash(model) + joblib.hash((raw, y, seed, n_bins))).encode()).hexdigest()[:16]
        return cls(method, f"{name}_{short}_v2_{identity}", model, _reliability_bins(p_for_bins, y, n_bins),
                   len(raw), n_pos, cv_brier)

    def transform(self, raw: np.ndarray) -> np.ndarray:
        """Calibrated probabilities in [0, 1], non-decreasing in ``raw``."""
        return _apply(self.method, self.model, np.asarray(raw, dtype="float64"))

    __call__ = transform

    def local_calibration_error(self, p: np.ndarray | float) -> np.ndarray:
        """|mean predicted - observed rate| of the validation reliability bin containing ``p``."""
        p = np.atleast_1d(np.asarray(p, dtype="float64"))
        b = self.reliability_bins
        if b.empty:
            return np.full(p.shape, np.nan)
        edges = b["bin_upper"].to_numpy()[:-1]
        idx = np.clip(np.searchsorted(edges, p, side="right"), 0, len(b) - 1)
        gap = (b["mean_predicted"] - b["observed_rate"]).abs().to_numpy()
        return gap[idx]
