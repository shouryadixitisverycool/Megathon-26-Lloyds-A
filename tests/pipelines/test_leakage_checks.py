"""Leakage guards: each deliberately invalid example must fail; valid examples must pass (spec Gate 1)."""

from datetime import date

import pandas as pd
import pytest

from greenpath.contracts import Product
from greenpath.pipelines.leakage_checks import (
    DEFAULT_AUDIT_COLUMNS,
    EventSource,
    LeakageError,
    check_customer_split_disjoint,
    check_event_times,
    check_no_audit_features,
    check_no_post_adoption_features,
    check_no_target_features,
    run_all_checks,
)

CUTOFF = date(2026, 6, 30)
VALID_FEATURES = [
    "fuel_spend_30d", "fuel_spend_90d_avg", "electricity_kwh_12m", "has_vehicle", "is_ice",
    "home_owner", "tenure_months", "sustainability_preference", "digital_statement_ratio",
]


def test_leakage_error_is_an_assertion_error():
    assert issubclass(LeakageError, AssertionError)


# --- customer split integrity -------------------------------------------------------------

def test_customer_in_two_splits_fails_for_series_and_mapping():
    overlapping = pd.Series(["train", "test", "test"], index=["C1", "C2", "C1"])  # C1 is train and test
    with pytest.raises(LeakageError, match="more than one split"):
        check_customer_split_disjoint(overlapping)
    with pytest.raises(LeakageError, match="C1"):
        check_customer_split_disjoint({"train": ["C1", "C2"], "test": ["C1", "C3"]})


def test_disjoint_splits_pass_for_frames_and_series():
    series = pd.Series(["train", "validation", "test", "demo"], index=["C1", "C2", "C3", "C4"])
    assert "no customer" in check_customer_split_disjoint(series)
    frames = {
        "train": pd.DataFrame({"customer_id": ["C1", "C2"]}),
        "test": pd.DataFrame({"customer_id": ["C3"]}),
    }
    assert "2 splits" in check_customer_split_disjoint(frames)


# --- event times ---------------------------------------------------------------------------

def test_event_after_cutoff_fails():
    frame = pd.DataFrame({"date": pd.to_datetime(["2026-06-29", "2026-07-01"])})
    with pytest.raises(LeakageError, match="after cutoff 2026-06-30"):
        check_event_times(frame, "date", CUTOFF, "transactions")


def test_event_on_cutoff_day_and_before_passes():
    frame = pd.DataFrame({"date": pd.to_datetime(["2025-01-01", "2026-06-30"])})
    assert "2 rows" in check_event_times(frame, "date", CUTOFF, "transactions")


def test_monthly_rows_are_available_at_month_end():
    june = pd.DataFrame({"month": pd.to_datetime(["2026-06-01"])})
    check_event_times(june, "month", CUTOFF, "energy_usage", monthly=True)  # available 2026-06-30: ok
    july = pd.DataFrame({"month": pd.to_datetime(["2026-07-01"])})
    with pytest.raises(LeakageError, match="energy_usage"):
        check_event_times(july, "month", CUTOFF, "energy_usage", monthly=True)  # available 2026-07-31
    with pytest.raises(LeakageError, match="energy_usage"):
        check_event_times(july, "month", CUTOFF, "energy_usage")  # plain comparison also fails


def test_missing_time_column_fails_closed():
    frame = pd.DataFrame({"when": pd.to_datetime(["2025-01-01"])})
    with pytest.raises(LeakageError, match="cannot verify"):
        check_event_times(frame, "date", CUTOFF, "transactions")


# --- target and outcome features -------------------------------------------------------------

@pytest.mark.parametrize("bad_name", ["adopted_ev", "label", "target_flag", "take_up_30d", "outcome_90d", "Adoption_Flag"])
def test_target_like_feature_names_fail(bad_name):
    with pytest.raises(LeakageError, match="target-like"):
        check_no_target_features(VALID_FEATURES + [bad_name])


def test_valid_feature_names_pass_target_check():
    assert "none target-like" in check_no_target_features(VALID_FEATURES)


# --- post-adoption flags ---------------------------------------------------------------------

@pytest.mark.parametrize(
    ("product", "bad_feature"),
    [
        (Product.EV_FINANCE, "holds_ev_finance"),
        (Product.EV_FINANCE, "is_ev"),
        (Product.GREEN_HOME, "holds_green_home_loan"),
        (Product.SOLAR_FINANCE, "holds_solar_finance"),
        (Product.SOLAR_FINANCE, "has_existing_solar"),
        (Product.PAPERLESS_BANKING, "is_paperless"),
    ],
)
def test_own_post_adoption_flag_fails(product, bad_feature):
    with pytest.raises(LeakageError, match="post-adoption"):
        check_no_post_adoption_features(product, VALID_FEATURES + [bad_feature])


def test_other_products_flags_and_valid_features_pass():
    check_no_post_adoption_features(Product.GREEN_HOME, VALID_FEATURES + ["holds_ev_finance"])
    check_no_post_adoption_features(Product.EV_FINANCE, VALID_FEATURES)


def test_product_accepts_string_values_and_rejects_unknown_ones():
    with pytest.raises(LeakageError, match="post-adoption"):
        check_no_post_adoption_features("PAPERLESS_BANKING", ["is_paperless"])
    with pytest.raises(LeakageError, match="unknown product"):
        check_no_post_adoption_features("MORTGAGE", VALID_FEATURES)


# --- audit-only and proxy columns ------------------------------------------------------------

@pytest.mark.parametrize("bad_column", ["age_band", "income_band", "postcode_sector", "region"])
def test_audit_or_proxy_column_in_features_fails(bad_column):
    with pytest.raises(LeakageError, match="audit-only or proxy"):
        check_no_audit_features(VALID_FEATURES + [bad_column])


def test_audit_check_uses_supplied_columns_and_default_set():
    assert DEFAULT_AUDIT_COLUMNS == {"age_band", "income_band", "postcode_sector", "region"}
    check_no_audit_features(VALID_FEATURES + ["region"], audit_columns={"age_band"})
    with pytest.raises(LeakageError):
        check_no_audit_features(VALID_FEATURES + ["age_band"], audit_columns={"age_band"})


# --- run_all_checks ---------------------------------------------------------------------------

def _valid_inputs():
    split = pd.Series(["train", "test"], index=["C1", "C2"])
    energy = pd.DataFrame({"month": pd.to_datetime(["2026-05-01", "2026-06-01"])})
    return {
        "cutoff": CUTOFF,
        "split": split,
        "event_sources": [EventSource("energy_usage", energy, "month", monthly=True)],
        "feature_names": VALID_FEATURES,
        "products": [Product.EV_FINANCE, Product.PAPERLESS_BANKING],
    }


def test_run_all_checks_summary_for_valid_inputs():
    summary = run_all_checks(**_valid_inputs())
    assert summary["passed"] is True
    assert summary["n_failed"] == 0
    assert summary["n_not_run"] == 0
    assert summary["cutoff"] == "2026-06-30"
    assert {c["check"] for c in summary["checks"]} == {
        "customer_split_disjoint", "event_times_within_cutoff", "no_target_features",
        "no_audit_features", "no_post_adoption_features",
    }
    assert all(c["status"] == "PASS" for c in summary["checks"])


def test_run_all_checks_raises_and_lists_every_failure():
    inputs = _valid_inputs()
    inputs["split"] = pd.Series(["train", "test"], index=["C1", "C1"])
    inputs["feature_names"] = VALID_FEATURES + ["holds_ev_finance", "age_band", "adopted_flag"]
    with pytest.raises(LeakageError) as excinfo:
        run_all_checks(**inputs)
    message = str(excinfo.value)
    assert "customer_split_disjoint[split]" in message
    assert "no_target_features[features]" in message
    assert "no_audit_features[features]" in message
    assert "no_post_adoption_features[EV_FINANCE]" in message  # holds_ev_finance is EV's own flag
    assert "no_post_adoption_features[PAPERLESS_BANKING]" not in message  # passes: is_paperless absent


def test_run_all_checks_summary_reports_failures_without_raising():
    inputs = _valid_inputs()
    inputs["feature_names"] = VALID_FEATURES + ["holds_ev_finance"]
    summary = run_all_checks(**inputs, raise_on_failure=False)
    assert summary["passed"] is False
    assert summary["n_failed"] == 1
    failed = [c for c in summary["checks"] if c["status"] == "FAIL"]
    assert failed[0]["check"] == "no_post_adoption_features"
    assert failed[0]["target"] == "EV_FINANCE"


def test_run_all_checks_marks_absent_inputs_as_not_run():
    summary = run_all_checks(cutoff=CUTOFF, raise_on_failure=False)
    assert summary["passed"] is True
    assert summary["n_checks"] == 0
    assert summary["n_not_run"] == len(summary["checks"]) > 0


def test_unknown_product_is_recorded_as_a_failure():
    summary = run_all_checks(cutoff=CUTOFF, feature_names=VALID_FEATURES, products=["MORTGAGE"],
                             raise_on_failure=False)
    assert summary["passed"] is False
    last = summary["checks"][-1]
    assert (last["check"], last["target"], last["status"]) == ("no_post_adoption_features", "MORTGAGE", "FAIL")
    assert "unknown product" in last["detail"]


def test_missing_event_times_are_not_treated_as_late():
    frame = pd.DataFrame({"date": pd.to_datetime(["2026-06-01", None])})
    assert "1 rows" in check_event_times(frame, "date", CUTOFF, "transactions")
    monthly = pd.DataFrame({"month": pd.to_datetime(["2026-06-01", None])})
    check_event_times(monthly, "month", CUTOFF, "energy_usage", monthly=True)
def test_source_availability_after_cutoff_fails():
    import pandas as pd
    import pytest
    from datetime import date
    from greenpath.pipelines.leakage_checks import EventSource, LeakageError, run_all_checks
    frame = pd.DataFrame({"date": pd.to_datetime(["2026-06-01"]),
                          "available_at": pd.to_datetime(["2026-07-01"])})
    with pytest.raises(LeakageError, match="source_available_within_cutoff"):
        run_all_checks(cutoff=date(2026, 6, 30), event_sources=[
            EventSource("late", frame, "date", availability_col="available_at")])
