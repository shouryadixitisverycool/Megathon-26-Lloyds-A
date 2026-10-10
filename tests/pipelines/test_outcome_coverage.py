"""Unknown follow-up is never silently converted to a negative outcome."""

from datetime import date

import pandas as pd
import pytest

from greenpath.data_generation.outcome_coverage import generate_outcome_coverage
from greenpath.pipelines.schemas import SchemaError
from greenpath.pipelines.split import make_labels

CUTOFF = date(2026, 6, 30)


def outcomes(rows=()):
    frame = pd.DataFrame(rows, columns=["customer_id", "product", "adoption_date"])
    frame["adoption_date"] = pd.to_datetime(frame["adoption_date"])
    return frame


def coverage(ids=("C1", "C2"), end="2026-09-30"):
    return generate_outcome_coverage(pd.DataFrame({"customer_id": ids}), end)


def test_complete_simulation_fallback_remains_binary():
    labels = make_labels(outcomes(), ["C1"], CUTOFF)
    assert labels.loc["C1"].tolist() == [0, 0, 0, 0]
    assert labels.dtypes.map(str).eq("int64").all()


def test_complete_explicit_coverage_matches_simulation_fallback():
    events = outcomes([("C1", "EV_FINANCE", "2026-09-28")])
    implicit = make_labels(events, ["C1", "C2"], CUTOFF)
    explicit = make_labels(events, ["C1", "C2"], CUTOFF, coverage=coverage())
    pd.testing.assert_frame_equal(implicit.astype("Int64"), explicit)


def test_missing_customer_product_coverage_is_null_not_zero():
    evidence = coverage()
    evidence = evidence[~((evidence.customer_id == "C2") & (evidence["product"] == "EV_FINANCE"))]
    labels = make_labels(outcomes(), ["C1", "C2", "C3"], CUTOFF, coverage=evidence)
    assert labels.loc["C1", "EV_FINANCE"] == 0
    assert pd.isna(labels.loc["C2", "EV_FINANCE"])
    assert labels.loc["C3"].isna().all()


@pytest.mark.parametrize("end,complete", [("2026-09-27", True), ("2026-09-30", False)])
def test_incomplete_or_short_followup_cannot_establish_negative(end, complete):
    evidence = coverage(end=end)
    evidence["complete_followup"] = complete
    labels = make_labels(outcomes(), ["C1", "C2"], CUTOFF, coverage=evidence)
    assert labels.isna().all().all()


def test_observed_positive_survives_partial_followup_but_unobserved_event_does_not():
    evidence = coverage(end="2026-08-01")
    evidence["complete_followup"] = False
    events = outcomes([("C1", "EV_FINANCE", "2026-07-15"), ("C2", "EV_FINANCE", "2026-09-01")])
    labels = make_labels(events, ["C1", "C2"], CUTOFF, coverage=evidence)
    assert labels.loc["C1", "EV_FINANCE"] == 1
    assert pd.isna(labels.loc["C2", "EV_FINANCE"])
    assert pd.isna(labels.loc["C1", "GREEN_HOME"])


def test_outcome_availability_is_independent_of_feature_cutoff():
    events = outcomes([("C1", "EV_FINANCE", "2026-07-15")])
    labels = make_labels(events, ["C1"], CUTOFF, coverage=coverage(), outcome_as_of=date(2026, 9, 29))
    assert labels.isna().all().all()
    available = make_labels(events, ["C1"], CUTOFF, coverage=coverage(), outcome_as_of=date(2026, 9, 30))
    assert available.loc["C1", "EV_FINANCE"] == 1
    assert available.loc["C1", "GREEN_HOME"] == 0


def test_empty_coverage_does_not_mean_complete_simulation():
    labels = make_labels(outcomes(), ["C1"], CUTOFF, coverage=coverage().iloc[:0])
    assert labels.isna().all().all()


def test_coverage_is_deterministic_complete_and_product_specific():
    first = coverage()
    pd.testing.assert_frame_equal(first, coverage())
    assert len(first) == 8
    assert first.complete_followup.all()
    assert first.observation_end.eq(pd.Timestamp("2026-09-30")).all()


def test_duplicate_coverage_is_rejected():
    evidence = coverage()
    with pytest.raises(SchemaError, match="duplicate primary key"):
        make_labels(outcomes(), ["C1"], CUTOFF, coverage=pd.concat([evidence, evidence]))


def test_outcome_asof_without_evidence_is_rejected():
    with pytest.raises(ValueError, match="requires coverage"):
        make_labels(outcomes(), ["C1"], CUTOFF, outcome_as_of=CUTOFF)
