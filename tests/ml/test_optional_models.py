"""Optional signals keep stochastic labels, validation and guardrails separate."""

from datetime import date, timedelta
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from greenr import config
from greenr.extensions.optional_models import (
    FEATURES, OPPORTUNITIES, OptionalOpportunityProvider, matrix, optional_outcomes, train,
)


@pytest.fixture(scope="module")
def frame():
    rng = np.random.default_rng(417)
    n = 1200
    return pd.DataFrame({
        "has_investments": rng.binomial(1, .7, n), "has_mortgage": rng.binomial(1, .6, n),
        "has_vehicle_finance": rng.binomial(1, .4, n), "has_vehicle": rng.binomial(1, .7, n),
        "sustainability_preference": rng.integers(1, 6, n).astype(float),
        "digital_txn_3m_avg": rng.gamma(3, 10, n), "app_logins_3m_avg": rng.gamma(2, 5, n),
        "digital_months_present": np.full(n, 12.0), "tenure_months": rng.uniform(1, 150, n),
        "txn_months_observed": np.full(n, 12.0), "home_improvement_spend_12m_avg": rng.gamma(1, 100, n),
        "home_improvement_spend_trend": rng.normal(0, .3, n), "vehicle_age_years": rng.uniform(0, 15, n),
        "annual_mileage_km": rng.uniform(0, 30000, n), "electricity_kwh_12m": rng.uniform(1000, 9000, n),
        "gas_kwh_12m": rng.uniform(0, 24000, n), "electricity_trend": rng.normal(0, .2, n),
        "energy_months_present": np.full(n, 12.0),
    }, index=pd.Index([f"OPT{i:04}" for i in range(n)], name="customer_id"))


@pytest.fixture(scope="module")
def trained(tmp_path_factory, frame):
    root = tmp_path_factory.mktemp("optional")
    processed = root / "processed"
    processed.mkdir()
    frame.to_parquet(processed / f"customer360_{config.FEATURE_CUTOFF.isoformat()}.parquet")
    split = pd.Series(["train"] * 800 + ["validation"] * 200 + ["test"] * 200,
                      index=frame.index, name="split")
    split.to_csv(processed / "split_manifest.csv")
    report = train(processed, root / "artifacts", root / "reports")
    provider = OptionalOpportunityProvider(root / "artifacts")
    return root, report, provider


def snapshot(features, cutoff=config.FEATURE_CUTOFF):
    return SimpleNamespace(customer_id="OPT0001", features=features, feature_version="feature_v1", feature_cutoff=cutoff)


def test_optional_outcomes_are_customer_keyed_stochastic_draws(frame):
    first = optional_outcomes(frame, config.FEATURE_CUTOFF).sort_values(["customer_id", "opportunity"]).reset_index(drop=True)
    reordered = optional_outcomes(frame.iloc[::-1], config.FEATURE_CUTOFF).sort_values(["customer_id", "opportunity"]).reset_index(drop=True)
    pd.testing.assert_frame_equal(first, reordered)
    assert set(first.adopted_90d) == {0, 1}
    assert not set(first.columns) & {"latent", "motivation", "budget", "probability"}
    adopted = first.loc[first.adopted_90d.eq(1), "adoption_date"]
    assert adopted.between(config.FEATURE_CUTOFF + timedelta(days=1), config.FEATURE_CUTOFF + timedelta(days=90)).all()
    # Identical observed features still produce both outcomes through latent/noise draws.
    identical = pd.concat([frame.iloc[[0]]] * 500, ignore_index=True)
    identical.index = [f"SAME{i}" for i in range(500)]
    assert optional_outcomes(identical, config.FEATURE_CUTOFF).groupby("opportunity").adopted_90d.nunique().eq(2).all()


def test_shift_has_independent_outcomes(frame):
    base = optional_outcomes(frame, config.FEATURE_CUTOFF)
    shifted = optional_outcomes(frame, config.FEATURE_CUTOFF, shifted=True)
    assert np.mean(base.adopted_90d.to_numpy() != shifted.adopted_90d.to_numpy()) > .1


def test_model_matrix_excludes_truth_audit_and_holding_filters(frame):
    poisoned = frame.assign(adopted_90d=1, income_band=1, age_band=1, region=1, outcome_date=1)
    for opportunity in OPPORTUNITIES:
        result = matrix(poisoned, opportunity)
        assert list(result.columns) == list(FEATURES[opportunity])
        assert not set(result.columns) & {"adopted_90d", "income_band", "age_band", "region", "has_investments", "has_mortgage"}


def test_training_calibrates_validation_only_and_evaluates_real_holdouts(trained):
    root, report, provider = trained
    for name in OPPORTUNITIES:
        result = report["products"][name]
        assert result["calibration_fitted_split"] == "validation"
        assert result["calibration_fitted_n"] == result["counts"]["validation"]["customers"]
        assert provider.bundles[name].calibrator.n_fit == result["calibration_fitted_n"]
        assert "heuristic" in result["test"] and "logistic" in result["test"]
        assert result["test"]["logistic"]["roc_auc"] is not None
        assert result["shifted_heuristic_test"] and result["missingness_30pct_test"]
        assert result["confidence_status"] == "SUPPRESSED" and result["confidence"] is None
    assert (root / "reports" / "optional_evaluation.json").is_file()


def test_investment_requires_existing_activity_and_known_preference(trained, frame):
    provider = trained[2]
    features = frame.iloc[0].to_dict()
    result = provider.score(snapshot({**features, "has_investments": 1, "sustainability_preference": None}), "GREEN_INVESTMENTS")
    assert result["probability"] is None and result["status"] == "INSUFFICIENT_INFORMATION"
    result = provider.score(snapshot({**features, "has_investments": 0}), "GREEN_INVESTMENTS")
    assert result["status"] == "NOT_RELEVANT" and result["probability"] is None
    result = provider.score(snapshot({**features, "has_investments": 1}), "GREEN_INVESTMENTS")
    assert 0 < result["probability"] < 1 and result["confidence"] is None
    assert "not investment advice" in result["disclaimer"]


def test_loan_requires_borrowing_and_documented_purpose(trained, frame):
    provider = trained[2]
    features = {**frame.iloc[0].to_dict(), "has_mortgage": 1}
    missing = provider.score(snapshot(features), "GREEN_LOANS")
    assert missing["status"] == "INSUFFICIENT_INFORMATION" and missing["probability"] is None
    valid = provider.score(snapshot(features), "GREEN_LOANS", purpose="INSULATION")
    assert valid["probability"] is not None and valid["confidence_status"] == "SUPPRESSED"
    assert "credit approval" in valid["disclaimer"]
    none = provider.score(snapshot({**features, "has_mortgage": 0, "has_vehicle_finance": 0}), "GREEN_LOANS", purpose="INSULATION")
    assert none["status"] == "NOT_RELEVANT"
    with pytest.raises(ValueError):
        provider.score(snapshot(features), "GREEN_LOANS", purpose="HOLIDAY")


def test_wrong_cutoff_is_withheld(trained, frame):
    result = trained[2].score(snapshot(frame.iloc[0].to_dict(), date(2026, 3, 31)), "GREEN_INVESTMENTS")
    assert result["probability"] is None and result["reason_codes"] == ["OPTIONAL_MODEL_CUTOFF_MISMATCH"]


def test_heldout_feature_changes_cannot_change_fitted_model_or_calibration(trained, frame, tmp_path):
    original = trained[2]
    changed = frame.copy()
    columns = sorted(set(column for features in FEATURES.values() for column in features))
    changed.loc[changed.index[1000:], columns] = 99999.0
    processed = tmp_path / "processed"
    processed.mkdir()
    changed.to_parquet(processed / f"customer360_{config.FEATURE_CUTOFF.isoformat()}.parquet")
    (processed / "split_manifest.csv").write_bytes((trained[0] / "processed" / "split_manifest.csv").read_bytes())
    train(processed, tmp_path / "artifacts", tmp_path / "reports")
    refit = OptionalOpportunityProvider(tmp_path / "artifacts")
    for opportunity in OPPORTUNITIES:
        np.testing.assert_allclose(original.bundles[opportunity].estimator["logistic"].coef_,
                                   refit.bundles[opportunity].estimator["logistic"].coef_)
        np.testing.assert_allclose(original.bundles[opportunity].predict(frame.iloc[:10]),
                                   refit.bundles[opportunity].predict(frame.iloc[:10]))


def test_optional_opportunities_do_not_extend_the_core_product_contract():
    from greenr.contracts import Product
    assert len(list(Product)) == 4
    assert not set(OPPORTUNITIES) & {product.value for product in Product}
