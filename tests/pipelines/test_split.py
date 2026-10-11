"""Labels (window boundaries), population flags, customer splits and the split manifest."""

import hashlib
from datetime import date, timedelta

import pandas as pd
import pytest

from greenr.config import (
    DEMO_PERSONA_IDS,
    FEATURE_CUTOFF,
    OUTCOME_WINDOW_END,
    SEED_SPLIT,
)
from greenr.contracts import Product
from greenr.pipelines.split import (
    adopted_before,
    make_labels,
    split_customers,
    split_pipeline_customers,
    write_split_manifest,
)

PRODUCT_COLUMNS = [p.value for p in Product]
CUTOFF = date(2026, 6, 30)


def _outcomes(rows: list[tuple[str, str, date]]) -> pd.DataFrame:
    return pd.DataFrame({
        "customer_id": [r[0] for r in rows],
        "product": [r[1] for r in rows],
        "adoption_date": pd.to_datetime([r[2] for r in rows]),
    })


def test_label_window_boundaries_follow_spec():
    cases = {
        "C_ON_CUTOFF": date(2026, 6, 30),        # already adopted: not a label
        "C_DAY_AFTER": date(2026, 7, 1),         # first day of the window: label
        "C_WINDOW_END": date(2026, 9, 28),       # cutoff + 90 days: label
        "C_AFTER_WINDOW": date(2026, 9, 29),     # cutoff + 91 days: not a label
        "C_BEFORE": date(2026, 6, 1),            # adopted before the cutoff: not a label
    }
    outcomes = _outcomes([(cid, "EV_FINANCE", day) for cid, day in cases.items()])
    labels = make_labels(outcomes, list(cases), CUTOFF)
    adopted = adopted_before(outcomes, list(cases), CUTOFF)

    assert labels["EV_FINANCE"].to_dict() == {
        "C_ON_CUTOFF": 0, "C_DAY_AFTER": 1, "C_WINDOW_END": 1, "C_AFTER_WINDOW": 0, "C_BEFORE": 0,
    }
    assert adopted["EV_FINANCE"].to_dict() == {
        "C_ON_CUTOFF": True, "C_DAY_AFTER": False, "C_WINDOW_END": False,
        "C_AFTER_WINDOW": False, "C_BEFORE": True,
    }


def test_window_end_matches_config():
    assert FEATURE_CUTOFF + timedelta(days=90) == OUTCOME_WINDOW_END


def test_labels_have_one_binary_column_per_product_and_zero_for_missing_customers():
    outcomes = _outcomes([("C1", "GREEN_HOME", date(2026, 7, 15)), ("C1", "PAPERLESS_BANKING", date(2026, 8, 1))])
    labels = make_labels(outcomes, ["C1", "C2"], CUTOFF)
    assert list(labels.columns) == PRODUCT_COLUMNS
    assert labels.index.tolist() == ["C1", "C2"]
    assert labels.loc["C1", "GREEN_HOME"] == 1 and labels.loc["C1", "PAPERLESS_BANKING"] == 1
    assert labels.loc["C2"].sum() == 0
    assert set(labels.to_numpy().ravel().tolist()) <= {0, 1}


def test_adopted_before_is_boolean_and_ignores_unrequested_customers():
    outcomes = _outcomes([("C1", "EV_FINANCE", date(2026, 1, 5)), ("OTHER", "EV_FINANCE", date(2026, 1, 5))])
    adopted = adopted_before(outcomes, ["C1", "C2"], CUTOFF)
    assert adopted.dtypes.map(str).unique().tolist() == ["bool"]
    assert adopted.index.tolist() == ["C1", "C2"]
    assert adopted.loc["C1", "EV_FINANCE"] and not adopted.loc["C2", "EV_FINANCE"]


def test_split_covers_every_customer_exactly_once():
    ids = [f"C{i:05d}" for i in range(500)]
    split = split_customers(ids, seed=SEED_SPLIT)
    assert split.index.tolist() == ids
    assert set(split.unique()) <= {"train", "validation", "test", "demo"}
    assert split.isin(["train", "validation", "test"]).all()


def test_split_is_deterministic_for_seed_and_independent_of_order():
    ids = [f"C{i:05d}" for i in range(300)]
    first = split_customers(ids, seed=7)
    again = split_customers(ids, seed=7)
    shuffled = split_customers(list(reversed(ids)), seed=7)
    other_seed = split_customers(ids, seed=8)
    pd.testing.assert_series_equal(first, again)
    assert first.to_dict() == shuffled.to_dict()
    assert first.to_dict() != other_seed.to_dict()


def test_split_fractions_are_respected():
    ids = [f"C{i:05d}" for i in range(2000)]
    counts = split_customers(ids, seed=SEED_SPLIT).value_counts()
    assert counts["train"] == 1400
    assert counts["validation"] == 300
    assert counts["test"] == 300


def test_pipeline_reserves_independent_release_cohort_without_changing_default_split(tmp_path):
    ids = [f"S{i:05d}" for i in range(20_000)] + list(DEMO_PERSONA_IDS)
    split = split_pipeline_customers(ids)
    assert split.value_counts().to_dict() == {
        "train": 11_000, "validation": 3_000, "confidence_release": 3_000,
        "test": 3_000, "demo": len(DEMO_PERSONA_IDS),
    }
    assert split.index.is_unique and set(split.index) == set(ids)
    assert split.loc[DEMO_PERSONA_IDS].eq("demo").all()
    assert split.to_dict() == split_pipeline_customers(reversed(ids)).to_dict()
    assert split.to_dict() != split_pipeline_customers(ids, seed=SEED_SPLIT + 1).to_dict()
    assert write_split_manifest(split, tmp_path / "split.csv")


def test_demo_personas_present_are_labelled_demo_and_absent_ones_are_ignored():
    present = list(DEMO_PERSONA_IDS[:3])
    ids = present + [f"C{i:05d}" for i in range(200)]
    split = split_customers(ids, seed=SEED_SPLIT)
    assert split.loc[present].tolist() == ["demo"] * 3
    assert "demo" not in set(split.drop(index=present))
    assert set(split.index) == set(ids)  # absent personas are not invented


def test_demo_personas_are_never_in_train_validation_or_test():
    ids = list(DEMO_PERSONA_IDS) + [f"C{i:05d}" for i in range(400)]
    split = split_customers(ids, seed=SEED_SPLIT)
    assert split.loc[list(DEMO_PERSONA_IDS)].eq("demo").all()
    assert (split.drop(index=list(DEMO_PERSONA_IDS)) != "demo").all()


@pytest.mark.parametrize("fractions", [(0.7, 0.15, 0.2), (0.8, -0.1, 0.3), (0.5, 0.5)])
def test_invalid_fractions_are_rejected(fractions):
    with pytest.raises(ValueError):
        split_customers(["C1", "C2", "C3"], fractions=fractions)


def test_duplicate_customer_ids_are_rejected():
    with pytest.raises(ValueError, match="unique"):
        split_customers(["C1", "C1"])


def test_manifest_digest_matches_written_bytes(tmp_path):
    split = split_customers([f"C{i:05d}" for i in range(50)], seed=SEED_SPLIT)
    path = tmp_path / "split_manifest.csv"
    digest = write_split_manifest(split, path)

    data = path.read_bytes()
    assert digest == hashlib.sha256(data).hexdigest()
    assert data.decode("utf-8").splitlines()[0] == "customer_id,split"
    sidecar = (tmp_path / "split_manifest.csv.sha256").read_text(encoding="utf-8")
    assert sidecar.startswith(digest)

    rows = [line.split(",") for line in data.decode("utf-8").splitlines()[1:]]
    assert [r[0] for r in rows] == sorted(split.index)
    assert write_split_manifest(split, tmp_path / "again.csv") == digest  # deterministic bytes


def test_manifest_rejects_unknown_labels(tmp_path):
    split = pd.Series(["train", "holdout"], index=["C1", "C2"])
    with pytest.raises(ValueError, match="unknown split labels"):
        write_split_manifest(split, tmp_path / "bad.csv")
