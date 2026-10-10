import json

import numpy as np
import pandas as pd
import pytest

from greenpath.confidence.meta_model import (
    FEATURE_COLUMNS,
    ConfidenceModel,
    build_confidence_features,
    perturbation_stability,
    to_results,
)
from greenpath.confidence.validation import (
    ablation,
    stress_report,
    validate_confidence,
    write_confidence_report,
)
from greenpath.contracts.enums import ConfidenceBucket, ConfidenceStatus
from greenpath.contracts.propensity import ConfidenceResult

T = 0.3


def make_signal(n, seed):
    rng = np.random.default_rng(seed)
    p_true = rng.beta(0.8, 6, n)
    ood = rng.random(n)
    y = rng.random(n) < p_true
    p = np.clip(p_true + rng.normal(0, 0.03 * (1 + 4 * ood)), 0.001, 0.999)
    correct = (p >= T) == y
    feats = build_confidence_features(
        p, T, local_calibration_error=rng.random(n) * 0.05, ood_score=ood,
        stability=rng.random(n) * 0.1, recency_days=rng.integers(1, 200, n),
    )
    return feats, correct


def make_noise(n, seed):
    rng = np.random.default_rng(seed)
    feats = pd.DataFrame({c: rng.random(n) for c in FEATURE_COLUMNS})
    return feats, rng.random(n) < 0.7


def test_features_columns_no_completeness():
    f = build_confidence_features([0.1, 0.5], 0.3, 0.01, [0.2, 0.3], 0.0, 10)
    assert list(f.columns) == FEATURE_COLUMNS
    assert not any("complete" in c for c in f.columns)
    assert f["margin"].tolist() == pytest.approx([0.2 / 0.3, 0.2 / 0.3])


def test_signal_passes_on_test_and_results_validate(tmp_path):
    fv, cv = make_signal(4000, 1)
    ft, ct = make_signal(4000, 2)
    model = ConfidenceModel().fit(fv, cv)
    conf = model.predict(ft)
    assert conf.min() >= 0 and conf.max() <= 1
    v = validate_confidence(conf, ct)
    assert v.passed, v.reasons
    assert v.spearman <= -0.6 and v.top30_error <= 0.5 * v.bottom30_error
    assert len(v.deciles) == 10
    json.dumps(v.to_dict())
    res = to_results(conf, model.bucket(conf), True)
    assert all(isinstance(r, ConfidenceResult) and r.status is ConfidenceStatus.VALIDATED for r in res)
    assert {r.bucket for r in res} == set(ConfidenceBucket)
    assert res[0].method_version == "conf_meta_v2"
    # save/load round trip
    model.save(tmp_path / "m.joblib")
    m2 = ConfidenceModel.load(tmp_path / "m.joblib")
    np.testing.assert_allclose(m2.predict(ft), conf)
    assert "margin" in model.coefficients()
    # report
    ab = ablation(fv, cv, ft, ct)
    stress = stress_report(model, {"missing_data": (ft, ct)})
    write_confidence_report(
        {"EV_FINANCE": {"validation": v, "ablation": ab, "stress": stress, "coefficients": model.coefficients()}},
        tmp_path / "r.md", tmp_path / "r.json",
    )
    assert "SURFACED" in (tmp_path / "r.md").read_text()
    assert json.loads((tmp_path / "r.json").read_text())["EV_FINANCE"]["decision"] == "SURFACED"


def test_noise_fails_and_is_suppressed(tmp_path):
    fv, cv = make_noise(4000, 3)
    ft, ct = make_noise(4000, 4)
    model = ConfidenceModel().fit(fv, cv)
    v = validate_confidence(model.predict(ft), ct)
    assert not v.passed and v.reasons
    res = to_results(model.predict(ft), None, False, "failed validation")
    assert len(res) == 4000
    assert all(r.status is ConfidenceStatus.SUPPRESSED and r.value is None and r.bucket is None for r in res)
    assert res[0].limitation == "failed validation"
    write_confidence_report({"SOLAR_FINANCE": v}, tmp_path / "r.md", tmp_path / "r.json")
    assert "SUPPRESSED" in (tmp_path / "r.md").read_text()


def test_insufficient_data():
    v = validate_confidence(np.linspace(0, 1, 100), np.ones(100, bool))
    assert not v.passed and "insufficient" in v.reasons[0]


def test_constant_confidence_fails():
    rng = np.random.default_rng(0)
    v = validate_confidence(np.full(1000, 0.5), rng.random(1000) < 0.7)
    assert not v.passed


def test_tied_confidence_cannot_pass_by_ordering_correctness():
    correct = np.concatenate([np.zeros(300, bool), np.ones(700, bool)])
    forward = validate_confidence(np.full(1000, 0.5), correct)
    backward = validate_confidence(np.full(1000, 0.5), correct[::-1])
    assert not forward.passed and not backward.passed
    assert forward.top30_error == backward.top30_error == 0.3
    assert len(forward.deciles) == 1


@pytest.mark.parametrize("invalid", [np.inf, -np.inf, np.nan, -0.01, 1.01])
def test_invalid_confidence_fails_closed(invalid):
    confidence = np.linspace(0.1, 0.9, 1000)
    confidence[0] = invalid
    result = validate_confidence(confidence, np.arange(1000) >= 300)
    assert not result.passed
    assert "finite probabilities" in result.reasons[0]


def test_perturbation_stability():
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"a": rng.random(200), "b": rng.random(200), "c": rng.random(200)})

    def fn(f):
        return (0.5 * f["a"].fillna(0) + 0.1 * f["b"].fillna(0)).to_numpy()

    s1 = perturbation_stability(fn, df, ["a", "b"], seed=7)
    s2 = perturbation_stability(fn, df, ["a", "b"], seed=7)
    s3 = perturbation_stability(fn, df, ["a", "b"], seed=8)
    np.testing.assert_array_equal(s1, s2)
    assert not np.array_equal(s1, s3)
    assert s1.max() > 0
    assert np.all(perturbation_stability(fn, df, ["c"], seed=7) == 0)
    assert np.all(perturbation_stability(fn, df, [], seed=7) == 0)
    assert df["a"].notna().all()  # input untouched


def test_ablation_runs():
    fv, cv = make_signal(3000, 5)
    ft, ct = make_signal(3000, 6)
    ab = ablation(fv, cv, ft, ct)
    assert len(ab) == 1 + len(FEATURE_COLUMNS)
    assert set(["variant", "test_auc", "passed"]) <= set(ab.columns)
    assert ab.loc[ab.variant == "drop_margin", "test_auc"].iloc[0] < ab.loc[ab.variant == "full", "test_auc"].iloc[0]


def test_bucket_thresholds_monotone():
    fv, cv = make_signal(3000, 7)
    model = ConfidenceModel().fit(fv, cv)
    th = model.bucket_thresholds
    assert th["low_below"] <= th["high_at_or_above"]
    vals = np.linspace(0, 1, 101)
    order = {ConfidenceBucket.LOW: 0, ConfidenceBucket.MEDIUM: 1, ConfidenceBucket.HIGH: 2}
    ranks = [order[b] for b in model.bucket(vals)]
    assert ranks == sorted(ranks)
    conf = model.predict(fv)
    b = pd.Series(model.bucket(conf)).value_counts(normalize=True)
    assert b[ConfidenceBucket.HIGH] == pytest.approx(0.4, abs=0.02)
    assert b[ConfidenceBucket.LOW] == pytest.approx(0.3, abs=0.02)


def test_suppressed_default_limitation_and_validated_requires_buckets():
    assert to_results([0.5], None, False)[0].limitation
    with pytest.raises(ValueError):
        to_results([0.5], None, True)
