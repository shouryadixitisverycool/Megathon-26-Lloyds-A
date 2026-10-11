"""OOD detector tests: training calibration, extreme-value guard, degenerate columns, persistence."""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest

from greenr.trust.ood import (
    DEFAULT_OOD_THRESHOLD,
    EXTREME_SCORE_FLOOR,
    OOD_VERSION,
    OODDetector,
)


def training_frame(n: int = 2000, seed: int = 11, nan_rate: float = 0.03) -> pd.DataFrame:
    """Plausible customer feature matrix with a few missing values and one skewed column."""
    rng = np.random.default_rng(seed)
    frame = pd.DataFrame({
        "annual_mileage_km": rng.normal(12000, 3000, n).clip(500),
        "fuel_spend_90d_avg": rng.normal(100, 30, n).clip(0),
        "electricity_kwh_12m": rng.normal(3200, 800, n).clip(0),
        "gas_kwh_12m": rng.gamma(shape=9.0, scale=1000.0, size=n),
        "vehicle_age_years": rng.uniform(0, 12, n),
        "fuel_txn_freq_90d": rng.poisson(4, n).astype(float),
    })
    return frame.mask(rng.random(frame.shape) < nan_rate)


@pytest.fixture(scope="module")
def frame() -> pd.DataFrame:
    return training_frame()


@pytest.fixture(scope="module")
def detector(frame: pd.DataFrame) -> OODDetector:
    return OODDetector().fit(frame)


def median_row(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.median().to_frame().T


def test_training_rows_score_roughly_uniform(detector: OODDetector, frame: pd.DataFrame) -> None:
    scores = detector.score(frame)
    assert scores.shape == (len(frame),)
    assert scores.min() > 0.0
    assert scores.max() <= 1.0
    deciles = np.histogram(scores, bins=10, range=(0.0, 1.0))[0] / len(scores)
    assert np.all(np.abs(deciles - 0.1) < 0.01), deciles
    assert scores.mean() == pytest.approx(0.5, abs=0.02)
    assert np.mean(detector.is_ood(scores)) == pytest.approx(0.01, abs=0.005)


def test_score_rises_with_distance_from_the_centre(detector: OODDetector, frame: pd.DataFrame) -> None:
    rows = pd.concat([median_row(frame).assign(annual_mileage_km=km) for km in (12000.0, 16000.0, 20000.0, 24000.0)],
                     ignore_index=True)
    scores = detector.score(rows)
    assert np.all(np.diff(scores) >= 0.0), scores
    assert scores[-1] > scores[0]


def test_extreme_row_scores_at_least_099(detector: OODDetector, frame: pd.DataFrame) -> None:
    row = median_row(frame)
    row["annual_mileage_km"] = 95000.0
    row["fuel_spend_90d_avg"] = 2400.0
    score = detector.score(row)[0]
    assert score >= 0.99
    assert score >= EXTREME_SCORE_FLOOR  # the extreme-value guard, not only the distance, decides this
    assert detector.is_ood(score)


def test_single_extreme_value_triggers_guard(detector: OODDetector, frame: pd.DataFrame) -> None:
    row = median_row(frame)
    row["electricity_kwh_12m"] = 1e7
    assert detector.score(row)[0] >= EXTREME_SCORE_FLOOR


def test_infinite_value_counts_as_extreme(detector: OODDetector, frame: pd.DataFrame) -> None:
    row = median_row(frame)
    row["gas_kwh_12m"] = np.inf
    assert detector.score(row)[0] >= EXTREME_SCORE_FLOOR


def test_values_inside_the_training_range_are_not_forced_up(detector: OODDetector, frame: pd.DataFrame) -> None:
    row = median_row(frame)
    row["annual_mileage_km"] = float(frame["annual_mileage_km"].quantile(0.99))
    assert detector.score(row)[0] < EXTREME_SCORE_FLOOR


def test_missing_values_are_median_imputed(detector: OODDetector, frame: pd.DataFrame) -> None:
    all_missing = pd.DataFrame([{name: np.nan for name in frame.columns}])
    assert detector.score(all_missing)[0] == detector.score(median_row(frame))[0]


def test_missing_feature_columns_are_treated_as_missing(detector: OODDetector, frame: pd.DataFrame) -> None:
    trimmed = frame.drop(columns=["gas_kwh_12m"]).head(50)
    scores = detector.score(trimmed)
    assert scores.shape == (50,)
    assert np.all(np.isfinite(scores))


def test_constant_and_all_missing_columns_are_dropped_and_recorded(frame: pd.DataFrame) -> None:
    augmented = frame.copy()
    augmented["constant_flag"] = 1.0
    augmented["all_missing"] = np.nan
    detector = OODDetector().fit(augmented)
    assert detector.dropped_columns == {"constant_flag": "constant", "all_missing": "all_missing"}
    assert "constant_flag" not in detector.feature_names
    assert "all_missing" not in detector.feature_names
    assert detector.feature_names == list(frame.columns)
    assert detector.training_rows == len(frame)
    # Scoring ignores the dropped columns whether or not they are present.
    np.testing.assert_array_equal(detector.score(augmented), detector.score(frame))


def test_fit_rejects_frames_with_no_usable_column() -> None:
    frame = pd.DataFrame({"a": [1.0] * 10, "b": [np.nan] * 10})
    with pytest.raises(ValueError, match="no usable OOD features"):
        OODDetector().fit(frame)


def test_fit_rejects_a_single_row() -> None:
    with pytest.raises(ValueError):
        OODDetector().fit(pd.DataFrame({"a": [1.0, 2.0], "b": [3.0, 4.0]}).head(1))


def test_non_numeric_values_are_coerced_to_missing(detector: OODDetector, frame: pd.DataFrame) -> None:
    as_objects = frame.head(100).astype(object)
    as_objects["annual_mileage_km"] = "not a number"
    expected = detector.score(frame.head(100).assign(annual_mileage_km=np.nan))
    np.testing.assert_array_equal(detector.score(as_objects), expected)


def test_scores_are_bounded_float_arrays(detector: OODDetector, frame: pd.DataFrame) -> None:
    scores = detector.score(frame.head(200))
    assert scores.dtype == np.float64
    assert np.all((scores >= 0.0) & (scores <= 1.0))
    assert detector.score(frame.iloc[:0]).shape == (0,)


def test_fit_is_deterministic(frame: pd.DataFrame) -> None:
    first = OODDetector().fit(frame).score(frame.head(300))
    second = OODDetector().fit(frame).score(frame.head(300))
    np.testing.assert_array_equal(first, second)


def test_is_ood_threshold_semantics(detector: OODDetector) -> None:
    assert DEFAULT_OOD_THRESHOLD == 0.99
    assert detector.is_ood(0.995) is True
    assert detector.is_ood(0.5) is False
    assert detector.is_ood(0.99) is True  # at the threshold counts as OOD
    assert detector.is_ood(0.98, threshold=0.97) is True
    np.testing.assert_array_equal(detector.is_ood(np.array([0.2, 0.99, 1.0])), [False, True, True])


def test_save_and_load_round_trip(tmp_path: Path, detector: OODDetector, frame: pd.DataFrame) -> None:
    path = detector.save(tmp_path / "models" / "ev_ood.joblib")
    loaded = OODDetector.load(path)
    assert loaded.version == OOD_VERSION == detector.version
    assert loaded.feature_names == detector.feature_names
    np.testing.assert_array_equal(loaded.score(frame.head(100)), detector.score(frame.head(100)))


def test_load_rejects_other_objects(tmp_path: Path) -> None:
    path = tmp_path / "not_a_detector.joblib"
    joblib.dump({"not": "a detector"}, path)
    with pytest.raises(TypeError):
        OODDetector.load(path)


def test_unfitted_detector_refuses_to_score_or_save(tmp_path: Path, frame: pd.DataFrame) -> None:
    with pytest.raises(RuntimeError):
        OODDetector().score(frame)
    with pytest.raises(RuntimeError):
        OODDetector().save(tmp_path / "unfitted.joblib")
