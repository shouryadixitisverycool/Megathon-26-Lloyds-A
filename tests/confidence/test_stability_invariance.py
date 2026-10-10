import json
from types import SimpleNamespace

import numpy as np
import pandas as pd

from greenpath.confidence.meta_model import (
    METHOD_VERSION,
    ConfidenceModel,
    perturbation_stability,
)
from greenpath.contracts import Product
from greenpath.pipelines import runtime


def feature_frame(n=200):
    rng = np.random.default_rng(123)
    return pd.DataFrame({"a": rng.random(n), "b": rng.random(n), "customer_id": np.arange(n)})


def predict(frame):
    return (0.5 * frame["a"].fillna(0) + 0.2 * frame["b"].fillna(0)).to_numpy()


def stability(frame, seed=7, columns=("a", "b")):
    return perturbation_stability(predict, frame, columns, seed)


def test_bulk_single_reordered_chunked_and_metadata_invariance():
    frame = feature_frame()
    original = frame.copy(deep=True)
    bulk = stability(frame)
    np.testing.assert_array_equal(bulk, np.concatenate([stability(frame.iloc[[i]]) for i in range(len(frame))]))
    order = np.random.default_rng(42).permutation(len(frame))
    np.testing.assert_array_equal(bulk[order], stability(frame.iloc[order]))
    np.testing.assert_array_equal(bulk, np.concatenate([stability(frame.iloc[i:i + 17]) for i in range(0, len(frame), 17)]))
    changed = frame.set_axis(["same-index"] * len(frame))
    changed["customer_id"] = "unapproved metadata"
    np.testing.assert_array_equal(bulk, stability(changed))
    np.testing.assert_array_equal(bulk, stability(frame[["b", "customer_id", "a"]], columns=("b", "a")))
    assert not np.array_equal(bulk, stability(frame, seed=8))
    pd.testing.assert_frame_equal(frame, original)


def test_canonical_numeric_values_and_duplicate_rows():
    frame = pd.DataFrame({"a": [0.0, -0.0, 1.0, 1.0], "b": [np.nan, np.nan, 2.0, 2.0]})
    result = stability(frame)
    assert result[0] == result[1]
    assert result[2] == result[3]
    np.testing.assert_array_equal(stability(frame.iloc[2:]), stability(frame.iloc[2:].astype(int)))


def test_absent_approved_columns_match_explicit_missing_values():
    frame = feature_frame().drop(columns=["customer_id", "b"])

    def predict_optional(frame):
        b = frame["b"] if "b" in frame else pd.Series(np.nan, index=frame.index)
        return (0.5 * frame["a"].fillna(0) + 0.2 * b.fillna(0)).to_numpy()

    absent = perturbation_stability(predict_optional, frame, ["a", "b"], 7)
    explicit = perturbation_stability(predict_optional, frame.assign(b=np.nan), ["a", "b"], 7)
    np.testing.assert_array_equal(absent, explicit)


def test_five_draws_preserve_seeded_thirty_percent_mask_distribution():
    frame = feature_frame(5000).drop(columns="customer_id")
    calls = []

    def record(frame):
        calls.append(frame.isna().to_numpy())
        return predict(frame)

    perturbation_stability(record, frame, ["a", "b"], seed=7)
    assert len(calls) == 6  # one unchanged prediction plus five masking draws
    masks = np.stack(calls[1:])
    assert np.all(np.abs(masks.mean(axis=1) - 0.3) < 0.03)
    assert not np.array_equal(masks[0], masks[1])


def test_runtime_confidence_features_and_scores_match_single_row(monkeypatch):
    frame = feature_frame()
    bundle = SimpleNamespace(
        features=["a", "b"], threshold=0.3,
        calibrator=SimpleNamespace(local_calibration_error=lambda p: np.full(len(p), 0.02)),
    )
    monkeypatch.setattr(runtime, "predict_calibrated", lambda bundle, frame: predict(frame))
    propensity = predict(frame)
    bulk = runtime.confidence_features(bundle, frame, propensity, None)
    single = pd.concat([
        runtime.confidence_features(bundle, frame.iloc[[i]], propensity[i:i + 1], None)
        for i in range(len(frame))
    ], ignore_index=True)
    pd.testing.assert_frame_equal(bulk, single)
    assert "completeness" not in bulk.columns
    np.testing.assert_array_equal(predict(frame), propensity)
    model = ConfidenceModel().fit(bulk, np.arange(len(frame)) % 3 != 0)
    scorer = runtime.ConfidenceScorer({Product.EV_FINANCE: bundle}, {Product.EV_FINANCE: model}, {Product.EV_FINANCE: True})
    bulk_results = scorer(Product.EV_FINANCE, frame, propensity)
    single_results = [scorer(Product.EV_FINANCE, frame.iloc[[i]], propensity[i:i + 1])[0] for i in range(len(frame))]
    np.testing.assert_allclose([r.value for r in bulk_results], [r.value for r in single_results], atol=1e-15, rtol=0)
    assert [r.bucket for r in bulk_results] == [r.bucket for r in single_results]
    assert all(r.method_version == "conf_meta_v2" for r in bulk_results)


def test_old_confidence_artifact_is_suppressed_until_revalidated(tmp_path):
    root = tmp_path / runtime.CONFIDENCE_DIR
    root.mkdir()
    product = Product.EV_FINANCE
    old_model = ConfidenceModel()
    del old_model.method_version  # v1 artifacts only had a class-level version
    old_model.save(root / f"{product.value.lower()}.joblib")
    (root / "decisions.json").write_text(json.dumps({product.value: {"surfaced": True}}))
    scorer = runtime.load_confidence({}, {}, tmp_path)
    assert not scorer.validated[product]
    assert "revalidate" in scorer.limitations[product]
    new_model = ConfidenceModel()
    assert new_model.method_version == METHOD_VERSION
