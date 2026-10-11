"""Metric tests: hand-computed values, sklearn agreement and undefined-case behaviour."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest
from sklearn.calibration import calibration_curve as sk_calibration_curve
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from greenr.evaluation import metrics as m


def _random_problem(seed: int = 7, n: int = 500) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    p = rng.uniform(0.0, 1.0, size=n)
    y = (rng.uniform(0.0, 1.0, size=n) < p).astype(int)
    return y, p


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------


def test_perfect_ranking_gives_unit_roc_auc_and_average_precision() -> None:
    y = [0, 0, 1, 1]
    p = [0.1, 0.2, 0.8, 0.9]
    assert m.roc_auc(y, p) == pytest.approx(1.0)
    assert m.pr_auc(y, p) == pytest.approx(1.0)


def test_roc_auc_and_pr_auc_match_sklearn() -> None:
    y, p = _random_problem()
    assert m.roc_auc(y, p) == pytest.approx(roc_auc_score(y, p))
    assert m.pr_auc(y, p) == pytest.approx(average_precision_score(y, p))


def test_lift_at_ten_percent_on_known_example() -> None:
    # 100 rows, 10 positives; the top 10 rows (by score) contain 6 of them.
    y = [1] * 6 + [0] * 4 + [1] * 4 + [0] * 86
    scores = np.linspace(1.0, 0.0, 100)
    assert m.precision_at_k(y, scores, 0.1) == pytest.approx(0.6)
    assert m.recall_at_k(y, scores, 0.1) == pytest.approx(0.6)
    assert m.lift_at_k(y, scores) == pytest.approx(6.0)
    assert m.lift_at_k(y, scores, frac=0.1) == pytest.approx(6.0)


def test_precision_and_recall_at_k_small_example() -> None:
    y = [1, 0, 1, 0]
    scores = [0.9, 0.8, 0.7, 0.1]
    # frac 0.5 of 4 rows -> k = 2 -> top rows are indices 0 and 1 (one positive).
    assert m.precision_at_k(y, scores, 0.5) == pytest.approx(0.5)
    assert m.recall_at_k(y, scores, 0.5) == pytest.approx(0.5)
    assert m.lift_at_k(y, scores, 0.5) == pytest.approx(1.0)


def test_k_count_is_not_inflated_by_float_noise() -> None:
    # 0.07 * 100 == 7.000000000000001 in floating point; a naive ceil would pick 8 rows.
    y = [1] * 7 + [0] * 93
    scores = np.arange(100, 0, -1, dtype=float)
    assert m.precision_at_k(y, scores, 0.07) == pytest.approx(1.0)
    assert m.recall_at_k(y, scores, 0.07) == pytest.approx(1.0)


def test_ties_are_broken_by_input_order() -> None:
    scores = [0.5, 0.5, 0.5, 0.5]
    assert m.precision_at_k([1, 0, 0, 0], scores, 0.25) == pytest.approx(1.0)
    assert m.precision_at_k([0, 0, 0, 1], scores, 0.25) == pytest.approx(0.0)


def test_ranking_metrics_accept_pandas_and_bool_inputs() -> None:
    y = pd.Series([False, True, True])
    p = pd.Series([0.1, 0.8, 0.9])
    assert m.roc_auc(y, p) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Calibration
# ---------------------------------------------------------------------------


def test_brier_matches_hand_value_and_sklearn() -> None:
    assert m.brier([1, 0], [0.8, 0.3]) == pytest.approx((0.2**2 + 0.3**2) / 2)
    y, p = _random_problem()
    assert m.brier(y, p) == pytest.approx(brier_score_loss(y, p))


def test_ece_matches_hand_computed_value() -> None:
    # Bin (0.1, 0.2]: mean prediction 0.2, observed 0.5, weight 1/2 -> 0.3 * 0.5
    # Bin (0.7, 0.8]: mean prediction 0.8, observed 1.0, weight 1/2 -> 0.2 * 0.5
    assert m.ece([0, 1, 1, 1], [0.2, 0.2, 0.8, 0.8]) == pytest.approx(0.25)


def test_ece_is_zero_for_perfectly_calibrated_bins() -> None:
    # Bin (0, 0.1] at 0.05 with 1 positive in 20 rows, bin (0.5, 0.6] at 0.55 with 11 in 20.
    y = [1] + [0] * 19 + [1] * 11 + [0] * 9
    p = [0.05] * 20 + [0.55] * 20
    assert m.ece(y, p) == pytest.approx(0.0, abs=1e-12)


def test_ece_with_one_bin_is_absolute_mean_gap() -> None:
    assert m.ece([0, 1], [0.2, 0.6], n_bins=1) == pytest.approx(0.1)


def test_calibration_curve_table() -> None:
    table = m.calibration_curve([0, 1, 1, 1], [0.2, 0.2, 0.8, 0.8], n_bins=10)
    assert list(table.columns) == ["bin", "n", "mean_predicted", "observed_rate"]
    assert len(table) == 10
    filled = table[table["n"] > 0].set_index("bin")
    assert list(filled.index) == [1, 7]
    assert filled.loc[1, "n"] == 2
    assert filled.loc[1, "mean_predicted"] == pytest.approx(0.2)
    assert filled.loc[1, "observed_rate"] == pytest.approx(0.5)
    assert filled.loc[7, "observed_rate"] == pytest.approx(1.0)
    empty = table[table["n"] == 0]
    assert empty["mean_predicted"].isna().all()


def test_calibration_curve_agrees_with_sklearn_on_non_empty_bins() -> None:
    y, p = _random_problem(seed=11, n=2000)
    table = m.calibration_curve(y, p, n_bins=10)
    observed, predicted = sk_calibration_curve(y, p, n_bins=10, strategy="uniform")
    filled = table[table["n"] > 0]
    np.testing.assert_allclose(filled["observed_rate"].to_numpy(), observed, rtol=1e-9)
    np.testing.assert_allclose(filled["mean_predicted"].to_numpy(), predicted, rtol=1e-9)


# ---------------------------------------------------------------------------
# Thresholded decisions
# ---------------------------------------------------------------------------


def test_confusion_at_threshold_hand_computed() -> None:
    y = [1, 0, 1, 0, 1]
    p = [0.9, 0.6, 0.4, 0.2, 0.7]
    out = m.confusion_at_threshold(y, p, 0.5)
    assert (out["tp"], out["fp"], out["tn"], out["fn"]) == (2, 1, 1, 1)
    assert out["precision"] == pytest.approx(2 / 3)
    assert out["recall"] == pytest.approx(2 / 3)
    assert out["f1"] == pytest.approx(2 / 3)
    assert out["fpr"] == pytest.approx(0.5)
    assert out["fnr"] == pytest.approx(1 / 3)


def test_confusion_threshold_is_inclusive() -> None:
    out = m.confusion_at_threshold([1], [0.5], 0.5)
    assert out["tp"] == 1


def test_confusion_rates_are_nan_when_undefined() -> None:
    out = m.confusion_at_threshold([0, 1], [0.1, 0.2], 0.5)
    assert math.isnan(out["precision"])
    assert out["recall"] == pytest.approx(0.0)
    assert out["fpr"] == pytest.approx(0.0)
    assert out["fnr"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Undefined (single-class) behaviour
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("label", [0, 1])
def test_single_class_gives_nan_for_ranking_metrics(label: int) -> None:
    y = [label] * 4
    p = [0.1, 0.4, 0.6, 0.9]
    assert math.isnan(m.roc_auc(y, p))
    assert math.isnan(m.pr_auc(y, p))
    assert math.isnan(m.recall_at_k(y, p, 0.5))
    assert math.isnan(m.lift_at_k(y, p, 0.5))


def test_single_class_keeps_precision_and_calibration_defined() -> None:
    assert m.precision_at_k([0, 0], [0.1, 0.2], 0.5) == pytest.approx(0.0)
    assert m.brier([0, 0], [0.2, 0.4]) == pytest.approx((0.04 + 0.16) / 2)


def test_empty_input_returns_nan_for_scalar_metrics() -> None:
    assert math.isnan(m.brier([], []))
    assert math.isnan(m.ece([], []))
    assert math.isnan(m.precision_at_k([], [], 0.1))


# ---------------------------------------------------------------------------
# Summary and reporting helpers
# ---------------------------------------------------------------------------


def test_summary_returns_floats_with_expected_keys() -> None:
    y, p = _random_problem()
    out = m.summary(y, p)
    assert set(out) == set(m.SUMMARY_KEYS)
    assert all(isinstance(value, float) for value in out.values())
    assert out["threshold"] == pytest.approx(0.5)
    assert out["k_frac"] == pytest.approx(0.1)
    assert out["n"] == float(len(y))


def test_summary_agrees_with_component_functions() -> None:
    y, p = _random_problem(seed=3, n=300)
    out = m.summary(y, p, threshold=0.3, k_frac=0.2)
    assert out["roc_auc"] == pytest.approx(m.roc_auc(y, p))
    assert out["pr_auc"] == pytest.approx(m.pr_auc(y, p))
    assert out["brier"] == pytest.approx(m.brier(y, p))
    assert out["ece"] == pytest.approx(m.ece(y, p))
    assert out["lift_at_k"] == pytest.approx(m.lift_at_k(y, p, 0.2))
    assert out["precision_at_k"] == pytest.approx(m.precision_at_k(y, p, 0.2))
    assert out["recall_at_k"] == pytest.approx(m.recall_at_k(y, p, 0.2))
    assert out["fn"] + out["tp"] == pytest.approx(sum(y))


def test_summary_single_class_is_nan_where_undefined() -> None:
    out = m.summary([0, 0, 0], [0.1, 0.2, 0.3])
    assert math.isnan(out["roc_auc"])
    assert math.isnan(out["pr_auc"])
    assert math.isnan(out["recall_at_k"])
    assert math.isnan(out["lift_at_k"])
    assert math.isnan(out["precision"])
    assert out["precision_at_k"] == pytest.approx(0.0)
    assert out["tn"] == pytest.approx(3.0)


def test_subgroup_metrics_hand_computed() -> None:
    y = [1, 0, 1, 1, 0, 0, 1, 0]
    p = [0.9, 0.4, 0.7, 0.6, 0.2, 0.3, 0.8, 0.1]
    groups = ["a", "a", "b", "b", "a", "b", "a", "b"]
    table = m.subgroup_metrics(y, p, groups, threshold=0.65)
    assert list(table.columns) == list(m.SUBGROUP_COLUMNS)
    assert list(table["group"]) == ["a", "b"]
    a, b = table.iloc[0], table.iloc[1]
    assert (a["n"], a["positives"]) == (4, 2)
    assert a["mean_pred"] == pytest.approx(0.575)
    assert a["observed_rate"] == pytest.approx(0.5)
    assert a["calibration_gap"] == pytest.approx(0.075)
    assert a["selection_rate"] == pytest.approx(0.5)
    assert a["roc_auc"] == pytest.approx(1.0)
    assert a["fpr"] == pytest.approx(0.0)
    assert a["fnr"] == pytest.approx(0.0)
    assert b["mean_pred"] == pytest.approx(0.425)
    assert b["calibration_gap"] == pytest.approx(-0.075)
    assert b["selection_rate"] == pytest.approx(0.25)
    assert b["fnr"] == pytest.approx(0.5)
    assert b["fpr"] == pytest.approx(0.0)


def test_subgroup_metrics_labels_missing_groups() -> None:
    table = m.subgroup_metrics([0, 1], [0.2, 0.8], [None, "x"], threshold=0.5)
    assert set(table["group"]) == {m.MISSING_GROUP, "x"}


def test_subgroup_metrics_rejects_misaligned_groups() -> None:
    with pytest.raises(ValueError, match="aligned"):
        m.subgroup_metrics([0, 1], [0.2, 0.8], ["x"], threshold=0.5)


def test_shift_table_reports_perturbed_minus_in_distribution() -> None:
    in_dist = {"roc_auc": 0.9, "brier": 0.10, "name": "x", "n": 10.0}
    perturbed = {"roc_auc": 0.8, "brier": 0.15, "extra": 1.0}
    deltas = m.shift_table(in_dist, perturbed)
    assert set(deltas) == {"roc_auc", "brier"}
    assert deltas["roc_auc"] == pytest.approx(-0.1)
    assert deltas["brier"] == pytest.approx(0.05)


def test_shift_table_propagates_nan() -> None:
    deltas = m.shift_table({"roc_auc": math.nan}, {"roc_auc": 0.7})
    assert math.isnan(deltas["roc_auc"])


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "call",
    [
        lambda: m.roc_auc([0, 2], [0.1, 0.2]),
        lambda: m.brier([0, 1], [0.5, 1.2]),
        lambda: m.brier([0, 1], [0.5]),
        lambda: m.precision_at_k([0, 1], [0.1, math.nan], 0.5),
        lambda: m.lift_at_k([0, 1], [0.1, 0.2], 0.0),
        lambda: m.confusion_at_threshold([0, 1], [0.1, 0.2], math.nan),
        lambda: m.calibration_curve([0, 1], [0.1, 0.2], n_bins=0),
    ],
)
def test_invalid_inputs_raise_value_error(call) -> None:  # noqa: ANN001 - parametrised lambdas
    with pytest.raises(ValueError):
        call()
