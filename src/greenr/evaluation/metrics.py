"""Evaluation metrics for propensity models (DESIGN.md "Metrics (T7)"; spec sections 8.4, 13, 14).

Conventions shared by every function:

- ``y`` holds binary labels (0/1 or bool). Anything else raises ``ValueError``.
- ``p`` holds calibrated probabilities in [0, 1]. Ranking scores ``s`` may be any finite values.
- Undefined results are NaN: empty input, and single-class ``y`` for the ranking metrics
  ``roc_auc``, ``pr_auc``, ``recall_at_k`` and ``lift_at_k``. ``precision_at_k``, ``brier``,
  ``ece`` and the confusion counts remain defined for single-class ``y``.
- Thresholds are inclusive: a row is predicted positive when ``score >= t``.
- Top-k selection keeps ``k = max(1, ceil(frac * n))`` rows by descending score. Ties keep
  input order (stable sort on ``-score``), so results are deterministic.
- Calibration bins are equal width and right-closed: bin ``i`` covers ``(i/n, (i+1)/n]``,
  with ``[0, 1/n]`` in bin 0.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

import numpy as np
import numpy.typing as npt
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

__all__ = [
    "SUMMARY_KEYS",
    "brier",
    "calibration_curve",
    "confusion_at_threshold",
    "ece",
    "lift_at_k",
    "pr_auc",
    "precision_at_k",
    "recall_at_k",
    "roc_auc",
    "shift_table",
    "subgroup_metrics",
    "summary",
]

ArrayLike = npt.ArrayLike

MISSING_GROUP = "(missing)"

SUBGROUP_COLUMNS = (
    "group",
    "n",
    "positives",
    "roc_auc",
    "mean_pred",
    "observed_rate",
    "calibration_gap",
    "selection_rate",
    "fpr",
    "fnr",
)

SUMMARY_KEYS = (
    "n",
    "base_rate",
    "threshold",
    "k_frac",
    "k",
    "roc_auc",
    "pr_auc",
    "brier",
    "ece",
    "precision_at_k",
    "recall_at_k",
    "lift_at_k",
    "tp",
    "fp",
    "tn",
    "fn",
    "precision",
    "recall",
    "f1",
    "fpr",
    "fnr",
)


# ---------------------------------------------------------------------------
# Input handling
# ---------------------------------------------------------------------------


def _as_binary(y: ArrayLike) -> np.ndarray:
    arr = np.asarray(y)
    if arr.ndim != 1:
        raise ValueError("y must be one-dimensional")
    if arr.dtype == bool:
        return arr.astype(np.int64)
    try:
        values = arr.astype(np.float64)
    except (TypeError, ValueError) as exc:
        raise ValueError("y must be numeric 0/1 labels") from exc
    if not np.isin(values, (0.0, 1.0)).all():
        raise ValueError("y must contain only 0/1 labels")
    return values.astype(np.int64)


def _as_scores(x: ArrayLike, name: str) -> np.ndarray:
    arr = np.asarray(x, dtype=np.float64)
    if arr.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional")
    if not np.isfinite(arr).all():
        raise ValueError(f"{name} must be finite")
    return arr


def _as_probabilities(x: ArrayLike, name: str) -> np.ndarray:
    arr = _as_scores(x, name)
    if arr.size and (arr.min() < 0.0 or arr.max() > 1.0):
        raise ValueError(f"{name} must lie in [0, 1]")
    return arr


def _pair(y: ArrayLike, values: ArrayLike, *, probabilities: bool) -> tuple[np.ndarray, np.ndarray]:
    labels = _as_binary(y)
    scores = _as_probabilities(values, "p") if probabilities else _as_scores(values, "s")
    if labels.shape != scores.shape:
        raise ValueError("y and p/s must have the same length")
    return labels, scores


def _check_frac(frac: float) -> float:
    value = float(frac)
    if not 0.0 < value <= 1.0:
        raise ValueError("frac must be in (0, 1]")
    return value


def _single_class(labels: np.ndarray) -> bool:
    return labels.size == 0 or labels.min() == labels.max()


def _ratio(numerator: float, denominator: float) -> float:
    return float(numerator) / float(denominator) if denominator else math.nan


# ---------------------------------------------------------------------------
# Ranking metrics
# ---------------------------------------------------------------------------


def _k_for(n: int, frac: float) -> int:
    # round() removes float noise such as 0.07 * 100 = 7.000000000000001 before ceil.
    return max(1, math.ceil(round(frac * n, 9)))


def _top_indices(scores: np.ndarray, k: int) -> np.ndarray:
    return np.argsort(-scores, kind="stable")[:k]


def roc_auc(y: ArrayLike, p: ArrayLike) -> float:
    """ROC AUC. NaN when ``y`` has a single class."""
    labels, scores = _pair(y, p, probabilities=False)
    if _single_class(labels):
        return math.nan
    return float(roc_auc_score(labels, scores))


def pr_auc(y: ArrayLike, p: ArrayLike) -> float:
    """PR AUC, computed as average precision. NaN when ``y`` has a single class."""
    labels, scores = _pair(y, p, probabilities=False)
    if _single_class(labels):
        return math.nan
    return float(average_precision_score(labels, scores))


def precision_at_k(y: ArrayLike, s: ArrayLike, frac: float) -> float:
    """Share of positives among the top ``frac`` of rows ranked by score ``s``."""
    labels, scores = _pair(y, s, probabilities=False)
    top_frac = _check_frac(frac)
    if labels.size == 0:
        return math.nan
    k = _k_for(labels.size, top_frac)
    return float(labels[_top_indices(scores, k)].sum()) / k


def recall_at_k(y: ArrayLike, s: ArrayLike, frac: float) -> float:
    """Share of all positives captured in the top ``frac`` of rows. NaN when single-class."""
    labels, scores = _pair(y, s, probabilities=False)
    top_frac = _check_frac(frac)
    if _single_class(labels):
        return math.nan
    k = _k_for(labels.size, top_frac)
    return float(labels[_top_indices(scores, k)].sum()) / float(labels.sum())


def lift_at_k(y: ArrayLike, s: ArrayLike, frac: float = 0.1) -> float:
    """Precision@k divided by the base rate (Lift@10% by default). NaN when single-class."""
    labels, scores = _pair(y, s, probabilities=False)
    top_frac = _check_frac(frac)
    if _single_class(labels):
        return math.nan
    k = _k_for(labels.size, top_frac)
    precision = float(labels[_top_indices(scores, k)].sum()) / k
    return precision / float(labels.mean())


# ---------------------------------------------------------------------------
# Calibration
# ---------------------------------------------------------------------------


def brier(y: ArrayLike, p: ArrayLike) -> float:
    """Mean squared error between probabilities and 0/1 outcomes."""
    labels, probs = _pair(y, p, probabilities=True)
    if labels.size == 0:
        return math.nan
    return float(np.mean((probs - labels) ** 2))


def _bin_stats(
    labels: np.ndarray, probs: np.ndarray, n_bins: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if n_bins < 1:
        raise ValueError("n_bins must be >= 1")
    interior_edges = np.arange(1, n_bins) / n_bins
    index = np.searchsorted(interior_edges, probs, side="left")
    counts = np.bincount(index, minlength=n_bins)
    positives = np.bincount(index, weights=labels, minlength=n_bins)
    predicted = np.bincount(index, weights=probs, minlength=n_bins)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean_predicted = predicted / counts
        observed = positives / counts
    return counts.astype(np.int64), mean_predicted, observed


def calibration_curve(y: ArrayLike, p: ArrayLike, n_bins: int = 10) -> pd.DataFrame:
    """Reliability table with one row per equal-width bin (empty bins have NaN means)."""
    labels, probs = _pair(y, p, probabilities=True)
    counts, mean_predicted, observed = _bin_stats(labels, probs, n_bins)
    return pd.DataFrame(
        {
            "bin": np.arange(n_bins),
            "n": counts,
            "mean_predicted": mean_predicted,
            "observed_rate": observed,
        }
    )


def ece(y: ArrayLike, p: ArrayLike, n_bins: int = 10) -> float:
    """Expected calibration error: bin-weighted mean of |observed rate - mean prediction|."""
    labels, probs = _pair(y, p, probabilities=True)
    counts, mean_predicted, observed = _bin_stats(labels, probs, n_bins)
    filled = counts > 0
    if not filled.any():
        return math.nan
    weights = counts[filled] / counts.sum()
    return float(np.sum(weights * np.abs(observed[filled] - mean_predicted[filled])))


# ---------------------------------------------------------------------------
# Thresholded decisions
# ---------------------------------------------------------------------------


def confusion_at_threshold(y: ArrayLike, p: ArrayLike, t: float) -> dict[str, int | float]:
    """Confusion counts and rates for predictions ``score >= t``. Undefined rates are NaN."""
    labels, scores = _pair(y, p, probabilities=False)
    threshold = float(t)
    if not math.isfinite(threshold):
        raise ValueError("t must be finite")
    predicted = scores >= threshold
    positive = labels == 1
    tp = int(np.count_nonzero(predicted & positive))
    fp = int(np.count_nonzero(predicted & ~positive))
    fn = int(np.count_nonzero(~predicted & positive))
    tn = int(np.count_nonzero(~predicted & ~positive))
    return {
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": _ratio(tp, tp + fp),
        "recall": _ratio(tp, tp + fn),
        "f1": _ratio(2 * tp, 2 * tp + fp + fn),
        "fpr": _ratio(fp, fp + tn),
        "fnr": _ratio(fn, fn + tp),
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def summary(
    y: ArrayLike,
    p: ArrayLike,
    threshold: float | None = None,
    k_frac: float = 0.1,
) -> dict[str, float]:
    """All scalar metrics as floats. ``threshold`` defaults to 0.5 and is echoed back."""
    labels, probs = _pair(y, p, probabilities=True)
    frac = _check_frac(k_frac)
    cut = 0.5 if threshold is None else float(threshold)
    confusion = confusion_at_threshold(labels, probs, cut)
    out: dict[str, float] = {
        "n": float(labels.size),
        "base_rate": _ratio(labels.sum(), labels.size),
        "threshold": cut,
        "k_frac": frac,
        "k": float(_k_for(labels.size, frac)) if labels.size else math.nan,
        "roc_auc": roc_auc(labels, probs),
        "pr_auc": pr_auc(labels, probs),
        "brier": brier(labels, probs),
        "ece": ece(labels, probs),
        "precision_at_k": precision_at_k(labels, probs, frac),
        "recall_at_k": recall_at_k(labels, probs, frac),
        "lift_at_k": lift_at_k(labels, probs, frac),
    }
    out.update({name: float(value) for name, value in confusion.items()})
    return out


def _group_labels(groups: ArrayLike, n: int) -> np.ndarray:
    values = np.asarray(groups, dtype=object)
    if values.ndim != 1 or values.size != n:
        raise ValueError("groups must be one-dimensional and aligned with y")
    labels = values.copy()
    labels[pd.isna(values)] = MISSING_GROUP
    return labels


def subgroup_metrics(y: ArrayLike, p: ArrayLike, groups: ArrayLike, threshold: float) -> pd.DataFrame:
    """Per-group diagnostics, one row per group sorted by label.

    ``calibration_gap`` is ``mean_pred - observed_rate`` (positive means over-prediction).
    ``selection_rate`` is the share predicted positive at ``threshold``.
    """
    labels, probs = _pair(y, p, probabilities=True)
    group_values = _group_labels(groups, labels.size)
    codes, uniques = pd.factorize(group_values)
    order = sorted(range(len(uniques)), key=lambda i: str(uniques[i]))
    rows: list[dict[str, Any]] = []
    for code in order:
        mask = codes == code
        group_y = labels[mask]
        group_p = probs[mask]
        mean_pred = float(group_p.mean())
        observed = float(group_y.mean())
        confusion = confusion_at_threshold(group_y, group_p, threshold)
        rows.append(
            {
                "group": uniques[code],
                "n": int(group_y.size),
                "positives": int(group_y.sum()),
                "roc_auc": roc_auc(group_y, group_p),
                "mean_pred": mean_pred,
                "observed_rate": observed,
                "calibration_gap": mean_pred - observed,
                "selection_rate": float(np.mean(group_p >= float(threshold))),
                "fpr": confusion["fpr"],
                "fnr": confusion["fnr"],
            }
        )
    return pd.DataFrame(rows, columns=list(SUBGROUP_COLUMNS))


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float, np.integer, np.floating)) and not isinstance(value, bool)


def shift_table(metrics_a: Mapping[str, Any], metrics_b: Mapping[str, Any]) -> dict[str, float]:
    """Deltas ``b - a`` for every numeric key present in both summaries.

    Use ``a`` for the in-distribution run and ``b`` for the perturbed-generator run.
    """
    deltas: dict[str, float] = {}
    for key, value_a in metrics_a.items():
        if key not in metrics_b:
            continue
        value_b = metrics_b[key]
        if _is_number(value_a) and _is_number(value_b):
            deltas[key] = float(value_b) - float(value_a)
    return deltas
