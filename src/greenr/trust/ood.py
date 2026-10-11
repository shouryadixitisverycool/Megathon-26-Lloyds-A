"""Out-of-distribution score for customer feature vectors (spec 15.1, 16.2, 57).

The detector is fitted on the TRAINING feature matrix only:

1. keep numeric columns; drop columns that are all-missing or constant (recorded in
   ``dropped_columns`` with the reason);
2. median-impute missing values (training medians);
3. ``QuantileTransformer(output_distribution="normal")`` with ``n_quantiles <= n_rows``,
   then clip to +/- ``CLIP_NORMAL``;
4. squared Mahalanobis distance with a Ledoit-Wolf shrunk covariance.

``ood_score`` is the empirical CDF of the training distances: the fraction of training
rows whose distance is less than or equal to this row's distance. It is therefore a
percentile in 0..1, approximately uniform on the training data (0.5 is a median-distance
row, not a "perfectly typical" one), and 0.99 means "further out than 99% of training
rows".

Extreme-value guard: for each non-degenerate column, the raw training range is widened
by ``EXTREME_SPREAD_MULTIPLIER`` times its 0.5%-99.5% spread on each side. A row with any
value outside that widened range gets a score of at least ``EXTREME_SCORE_FLOOR``. The
quantile transform saturates beyond the training range, so this guard is what keeps
far-out values from looking ordinary. Infinite values count as out of range.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import joblib
import numpy as np
import pandas as pd
from sklearn.covariance import LedoitWolf
from sklearn.preprocessing import QuantileTransformer

from greenr.config import SEED_MODEL

OOD_VERSION: Final = "ood_v1"
#: Default operating threshold: ``is_ood`` is True at or above this score.
DEFAULT_OOD_THRESHOLD: Final = 0.99
#: Score floor for rows outside the widened raw training range.
EXTREME_SCORE_FLOOR: Final = 0.995
#: Half-width of the extreme-value guard, in units of the 0.5%-99.5% spread.
EXTREME_SPREAD_MULTIPLIER: Final = 3.0
#: Quantile transform output is clipped to +/- this many standard deviations.
CLIP_NORMAL: Final = 5.0
#: Upper bound on QuantileTransformer quantiles (also capped at the number of rows).
MAX_QUANTILES: Final = 1000


def _to_numeric_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Coerce every column to float64; non-numeric and None values become NaN."""
    return pd.DataFrame(
        {column: pd.to_numeric(frame[column], errors="coerce") for column in frame.columns},
        index=frame.index,
    ).astype("float64")


class OODDetector:
    """Mahalanobis-based OOD scorer; fit on training features, score any frame."""

    version: str = OOD_VERSION

    def __init__(self) -> None:
        self.feature_names: list[str] = []
        self.dropped_columns: dict[str, str] = {}
        self.training_rows: int = 0
        self._medians: np.ndarray | None = None
        self._extreme_lo: np.ndarray | None = None
        self._extreme_hi: np.ndarray | None = None
        self._guarded: np.ndarray | None = None
        self._quantile: QuantileTransformer | None = None
        self._location: np.ndarray | None = None
        self._precision: np.ndarray | None = None
        self._train_distances: np.ndarray | None = None

    # ------------------------------------------------------------------ fit
    def fit(self, features: pd.DataFrame) -> OODDetector:
        """Fit on the training feature matrix (numeric columns, NaN allowed)."""
        numeric = _to_numeric_frame(features)
        kept: list[str] = []
        dropped: dict[str, str] = {}
        for column in numeric.columns:
            observed = numeric[column].dropna()
            if observed.empty:
                dropped[column] = "all_missing"
            elif observed.nunique() <= 1:
                dropped[column] = "constant"
            else:
                kept.append(column)
        if not kept:
            raise ValueError("no usable OOD features: every column is all-missing or constant")
        if len(numeric) < 2:
            raise ValueError("at least two training rows are required")

        raw = numeric[kept].to_numpy(dtype=float)
        self.feature_names = kept
        self.dropped_columns = dropped
        self.training_rows = len(raw)

        self._medians = np.nanmedian(raw, axis=0)
        q_lo = np.nanquantile(raw, 0.005, axis=0)
        q_hi = np.nanquantile(raw, 0.995, axis=0)
        spread = q_hi - q_lo
        self._extreme_lo = q_lo - EXTREME_SPREAD_MULTIPLIER * spread
        self._extreme_hi = q_hi + EXTREME_SPREAD_MULTIPLIER * spread
        self._guarded = spread > 0

        self._quantile = QuantileTransformer(
            output_distribution="normal",
            n_quantiles=min(MAX_QUANTILES, len(raw)),
            random_state=SEED_MODEL,
        )
        z = np.clip(self._quantile.fit_transform(self._impute(raw)), -CLIP_NORMAL, CLIP_NORMAL)
        covariance = LedoitWolf().fit(z)
        self._location = np.asarray(covariance.location_, dtype=float)
        self._precision = np.asarray(covariance.precision_, dtype=float)
        self._train_distances = np.sort(self._distances(z))
        return self

    # ---------------------------------------------------------------- score
    def score(self, frame: pd.DataFrame) -> np.ndarray:
        """OOD score in 0..1 for each row of ``frame`` (columns matched by name)."""
        self._check_fitted()
        raw = _to_numeric_frame(frame).reindex(columns=self.feature_names).to_numpy(dtype=float)
        if raw.shape[0] == 0:
            return np.empty(0, dtype=float)

        infinite = np.isinf(raw)
        extreme = infinite.any(axis=1) | self._outside_widened_range(raw)
        raw = np.where(infinite, np.nan, raw)

        z = np.clip(self._quantile.transform(self._impute(raw)), -CLIP_NORMAL, CLIP_NORMAL)
        distances = self._distances(z)
        percentile = np.searchsorted(self._train_distances, distances, side="right") / len(self._train_distances)
        scores = np.where(extreme, np.maximum(percentile, EXTREME_SCORE_FLOOR), percentile)
        return np.clip(scores, 0.0, 1.0)

    def is_ood(self, score: float | np.ndarray, threshold: float = DEFAULT_OOD_THRESHOLD) -> bool | np.ndarray:
        """True where ``score`` is at or above ``threshold`` (scalar in, bool out)."""
        flags = np.asarray(score, dtype=float) >= threshold
        return bool(flags) if flags.ndim == 0 else flags

    # ------------------------------------------------------------ persist
    def save(self, path: str | Path) -> Path:
        """Write the fitted detector with joblib."""
        self._check_fitted()
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, target)
        return target

    @classmethod
    def load(cls, path: str | Path) -> OODDetector:
        """Read a detector written by ``save``; rejects other objects and versions."""
        loaded = joblib.load(path)
        if not isinstance(loaded, cls):
            raise TypeError(f"{path} does not contain an OODDetector")
        if loaded.version != OOD_VERSION:
            raise ValueError(f"OOD detector version {loaded.version!r} is not {OOD_VERSION!r}")
        return loaded

    # ---------------------------------------------------------- internals
    def _check_fitted(self) -> None:
        if self._quantile is None:
            raise RuntimeError("OODDetector is not fitted")

    def _impute(self, raw: np.ndarray) -> np.ndarray:
        return np.where(np.isnan(raw), self._medians[np.newaxis, :], raw)

    def _outside_widened_range(self, raw: np.ndarray) -> np.ndarray:
        with np.errstate(invalid="ignore"):
            outside = (raw > self._extreme_hi) | (raw < self._extreme_lo)
        return (outside & self._guarded).any(axis=1)

    def _distances(self, z: np.ndarray) -> np.ndarray:
        centred = z - self._location
        squared = np.einsum("ij,jk,ik->i", centred, self._precision, centred)
        return np.sqrt(np.maximum(squared, 0.0))
