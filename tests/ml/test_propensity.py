"""Tests for the product propensity models (T4) on synthetic Customer 360-like data."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from greenpath import config
from greenpath.contracts import (
    ConfidenceBucket,
    ConfidenceResult,
    ConfidenceStatus,
    CustomerSnapshot,
    DataQualityEvidence,
    DigitalFacts,
    EnergyFacts,
    FuelType,
    HomeFacts,
    ModelType,
    PopulationExclusion,
    Product,
    PropensityResult,
    ReasonCode,
    SpendFacts,
    VehicleFacts,
)
from greenpath.models.propensity import (
    PRODUCT_FEATURES,
    PROXY_ABLATION_FEATURES,
    REASON_CODE_CATALOGUE,
    Calibrator,
    ModelPropensityProvider,
    add_proxy_features,
    derive_reason_codes,
    fit_reason_thresholds,
    load_all,
    population_mask,
    predict_raw,
    save_all,
    train_product,
)
from greenpath.models.propensity.features import FORBIDDEN_FEATURES, check_features
from greenpath.models.propensity.heuristics import HeuristicModel
from greenpath.models.propensity.training import logistic_contributions

PRODUCTS = list(Product)
N = 3000


def _sig(x):
    return 1 / (1 + np.exp(-x))


def make_frame(n: int = N, seed: int = 7) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    rng = np.random.default_rng(seed)
    ids = [f"C{i:05d}" for i in range(n)]
    f = pd.DataFrame(index=pd.Index(ids, name="customer_id"))
    f["is_ice"] = (rng.random(n) < 0.7).astype(float)
    f["is_ev"] = (rng.random(n) < 0.05).astype(float)
    f["is_hybrid"] = (rng.random(n) < 0.1).astype(float)
    f["has_vehicle"] = 1.0
    f["fuel_spend_90d_avg"] = rng.gamma(4, 30, n) * f["is_ice"]
    f["annual_mileage_km"] = rng.gamma(5, 2500, n)
    f["vehicle_age_years"] = rng.gamma(3, 3, n)
    f["has_vehicle_finance"] = (rng.random(n) < 0.3).astype(float)
    f["home_owner"] = (rng.random(n) < 0.6).astype(float)
    f["has_mortgage"] = f["home_owner"] * (rng.random(n) < 0.6)
    f["electricity_kwh_12m"] = rng.gamma(6, 650, n)
    f["gas_kwh_12m"] = rng.gamma(5, 2500, n)
    f["utilities_spend_90d_avg"] = rng.gamma(3, 40, n)
    f["utilities_spend_trend"] = rng.normal(0.05, 0.2, n)
    f["home_improvement_spend_90d_avg"] = rng.gamma(1, 60, n) * (rng.random(n) < 0.5)
    f["paper_statements_3m"] = rng.poisson(1.5, n).astype(float)
    f["digital_txn_3m_avg"] = rng.gamma(4, 8, n)
    f["app_logins_3m_avg"] = rng.gamma(3, 4, n)
    f["branch_visits_3m"] = rng.poisson(0.5, n).astype(float)
    f["sustainability_preference"] = rng.integers(1, 6, n).astype(float)
    f["tenure_months"] = rng.integers(3, 200, n).astype(float)
    f["has_existing_solar"] = (rng.random(n) < 0.08).astype(float)
    f["is_paperless"] = (rng.random(n) < 0.35).astype(float)
    f["holds_ev_finance"] = (rng.random(n) < 0.04).astype(float)
    f["holds_green_home_loan"] = (rng.random(n) < 0.05).astype(float)
    f["holds_solar_finance"] = (rng.random(n) < 0.03).astype(float)
    # realistic missingness
    for col in ("annual_mileage_km", "electricity_kwh_12m", "sustainability_preference", "home_owner"):
        f.loc[rng.random(n) < 0.1, col] = np.nan
    z = {
        Product.EV_FINANCE: -3.2 + 1.6 * f["is_ice"] + 0.012 * f["fuel_spend_90d_avg"]
        + 0.00015 * f["annual_mileage_km"].fillna(12000) + 0.3 * f["sustainability_preference"].fillna(3),
        Product.GREEN_HOME: -3.5 + 1.2 * f["home_owner"].fillna(0) + 0.0003 * f["gas_kwh_12m"]
        + 0.5 * f["has_mortgage"],
        Product.SOLAR_FINANCE: -4.5 + 1.5 * f["home_owner"].fillna(0) + 0.0004 * f["electricity_kwh_12m"].fillna(4000),
        Product.PAPERLESS_BANKING: -2.5 + 0.5 * f["paper_statements_3m"] + 0.03 * f["app_logins_3m_avg"],
    }
    labels = pd.DataFrame({p.value: (rng.random(n) < _sig(z[p])).astype(int) for p in PRODUCTS}, index=f.index)
    split = pd.Series(rng.choice(["train", "validation", "test"], n, p=[0.6, 0.2, 0.2]), index=f.index)
    return f, labels, split


@pytest.fixture(scope="module")
def data():
    return make_frame()


@pytest.fixture(scope="module")
def bundles(data):
    f, y, s = data
    return {p: train_product(f, y, s, p) for p in PRODUCTS}


def snapshot_from_row(cid: str, row: pd.Series, fuel_type: FuelType | None = FuelType.PETROL) -> CustomerSnapshot:
    feats = {k: (None if pd.isna(v) else float(v)) for k, v in row.items()}
    return CustomerSnapshot(
        customer_id=cid, feature_cutoff=config.FEATURE_CUTOFF, generated_at=datetime(2026, 7, 1),
        feature_version=config.FEATURE_VERSION,
        vehicle=VehicleFacts(fuel_type=fuel_type), home=HomeFacts(), energy=EnergyFacts(),
        digital=DigitalFacts(), spend=SpendFacts(), features=feats,
        data_quality=DataQualityEvidence(transaction_months_observed=12))


def snapshots(frame: pd.DataFrame, k: int = 60) -> list[CustomerSnapshot]:
    return [snapshot_from_row(cid, frame.loc[cid]) for cid in frame.index[:k]]


# ---- features / population -------------------------------------------------------------------
def test_feature_lists_have_no_own_flags_or_proxies():
    for p, cols in PRODUCT_FEATURES.items():
        assert not set(cols) & FORBIDDEN_FEATURES[p]
        assert not any(c.startswith("holds_") for c in cols)
        assert not {"income_band", "region", "age_band", "postcode_sector"} & set(cols)
        check_features(p, cols)
    with pytest.raises(ValueError):
        check_features(Product.EV_FINANCE, ["holds_ev_finance"])


def test_population_mask_exclusions():
    f = pd.DataFrame({"holds_ev_finance": [1, 0, np.nan], "holds_green_home_loan": [0, 1, 0],
                      "has_existing_solar": [0, 0, 1], "holds_solar_finance": [0, 1, 0],
                      "is_paperless": [1, 0, np.nan]}, index=["a", "b", "c"])
    m, e = population_mask(f, Product.EV_FINANCE)
    assert m.tolist() == [False, True, True]
    assert e["a"] is PopulationExclusion.ALREADY_HOLDS_PRODUCT and e["b"] is None
    m, e = population_mask(f, Product.GREEN_HOME)
    assert m.tolist() == [True, False, True]
    m, e = population_mask(f, Product.SOLAR_FINANCE)
    assert m.tolist() == [True, False, False]
    assert e["b"] is PopulationExclusion.ALREADY_HOLDS_PRODUCT and e["c"] is PopulationExclusion.EXISTING_SOLAR
    m, e = population_mask(f, Product.PAPERLESS_BANKING)
    assert m.tolist() == [False, True, True] and e["a"] is PopulationExclusion.ALREADY_PAPERLESS
    m, _ = population_mask(f.drop(columns=["is_paperless"]), Product.PAPERLESS_BANKING)
    assert m.all()


def test_proxy_features_encoding():
    f = pd.DataFrame(index=pd.Index(["a", "b", "c"], name="customer_id"))
    audit = pd.DataFrame({"income_band": ["<25k", "100k+", None], "region": ["London", "Wales", None]},
                         index=f.index)
    out = add_proxy_features(f, audit)
    assert out["income_band_ord"].tolist()[:2] == [0.0, 4.0] and np.isnan(out["income_band_ord"].iloc[2])
    assert out["region_London"].tolist()[:2] == [1.0, 0.0] and np.isnan(out["region_London"].iloc[2])
    assert set(PROXY_ABLATION_FEATURES) <= set(out.columns)
    assert not set(PROXY_ABLATION_FEATURES) & {c for cols in PRODUCT_FEATURES.values() for c in cols}


def test_proxy_ablation_model_trains(data):
    f, y, s = data
    audit = pd.DataFrame({"income_band": np.random.default_rng(1).choice(["<25k", "25-50k", "100k+"], len(f)),
                          "region": np.random.default_rng(2).choice(["London", "Wales"], len(f))}, index=f.index)
    b = train_product(add_proxy_features(f, audit), y, s, Product.EV_FINANCE,
                      extra_features=PROXY_ABLATION_FEATURES, variant="proxy")
    assert "income_band_ord" in b.features and b.model_version.startswith("ev_finance_proxy_")


@pytest.mark.parametrize("feature", ["is_ev", "holds_ev_finance", "future_adoption", "income_band_ord", "age_band"])
def test_extra_features_cannot_bypass_default_policy(data, feature):
    f, y, s = data
    with pytest.raises(ValueError):
        train_product(f, y, s, Product.EV_FINANCE, extra_features=[feature])


@pytest.mark.parametrize("feature", ["is_ev", "holds_ev_finance", "future_adoption", "age_band"])
def test_proxy_variant_still_rejects_leakage(data, feature):
    f, y, s = data
    with pytest.raises(ValueError):
        train_product(f, y, s, Product.EV_FINANCE, extra_features=[feature], variant="proxy")


# ---- heuristics ------------------------------------------------------------------------------
def test_heuristic_scores_in_unit_interval_and_thresholds_from_train(data):
    f, y, s = data
    from greenpath.models.propensity.features import prepare_matrix
    X = prepare_matrix(f, PRODUCT_FEATURES[Product.EV_FINANCE])
    h = HeuristicModel.fit(Product.EV_FINANCE, X[(s == "train").to_numpy()])
    sc = h.score(X)
    assert sc.min() >= 0 and sc.max() <= 1 and len(np.unique(sc)) > 3
    fuel = next(r for r in h.rules if r.feature == "fuel_spend_90d_avg")
    assert fuel.threshold == pytest.approx(X.loc[(s == "train").to_numpy(), "fuel_spend_90d_avg"].quantile(0.6))
    # rule never fires on NaN evidence
    nan_row = pd.DataFrame({c: [np.nan] for c in X.columns})
    assert h.score(nan_row)[0] == 0.0


# ---- training / calibration ------------------------------------------------------------------
@pytest.mark.parametrize("product", PRODUCTS)
def test_training_runs_and_bundle_is_sane(bundles, data, product):
    f, y, s = data
    b = bundles[product]
    assert b.selected_model_type in (ModelType.LOGISTIC, ModelType.GRADIENT_BOOSTING)
    assert b.model_version.startswith(product.value.lower())
    assert b.calibration_version.startswith(product.value.lower())
    assert 0 < b.threshold < 1
    in_pop, _ = population_mask(f, product)
    assert b.n_train == int(((s == "train") & in_pop).sum())
    assert b.n_validation == int(((s == "validation") & in_pop).sum())
    assert not set(b.features) & FORBIDDEN_FEATURES[product]
    assert b.validation_metrics[b.selected_model_type]["roc_auc"] > 0.6


def test_calibrated_probabilities_valid_and_monotone(bundles, data):
    f, _, _ = data
    for p, b in bundles.items():
        for mt in ModelType:
            raw = predict_raw(b, f, mt)
            cal = b.calibrators[mt].transform(raw)
            assert cal.min() >= 0 and cal.max() <= 1
            order = np.argsort(raw, kind="stable")
            assert np.all(np.diff(cal[order]) >= -1e-9), (p, mt)


def test_calibrator_uses_only_validation_rows(data, monkeypatch):
    f, y, s = data
    seen = []
    orig = Calibrator.fit.__func__

    def spy(cls, raw, yv, *a, **k):
        seen.append(len(raw))
        return orig(cls, raw, yv, *a, **k)

    monkeypatch.setattr(Calibrator, "fit", classmethod(spy))
    b = train_product(f, y, s, Product.PAPERLESS_BANKING)
    in_pop, _ = population_mask(f, Product.PAPERLESS_BANKING)
    n_val = int(((s == "validation") & in_pop).sum())
    assert seen and set(seen) == {n_val} == {b.n_validation}


def test_calibrator_method_choice_and_local_error():
    rng = np.random.default_rng(0)
    raw = rng.random(2000)
    yv = (rng.random(2000) < raw**2).astype(int)  # miscalibrated raw score
    cal = Calibrator.fit(raw, yv, name="x")
    assert cal.method in ("isotonic", "platt") and cal.version in ("x_iso_v1", "x_platt_v1")
    assert set(cal.cv_brier) == {"isotonic", "platt"}
    assert {"mean_predicted", "observed_rate", "n"} <= set(cal.reliability_bins.columns)
    err = cal.local_calibration_error(np.array([0.01, 0.5, 0.99]))
    assert err.shape == (3,) and np.all(err >= 0) and not np.isnan(err).any()
    small = Calibrator.fit(raw[:60], (raw[:60] > 0.8).astype(int), name="y")
    assert small.method == "platt"  # too few positives for isotonic
    with pytest.raises(ValueError):
        Calibrator.fit(raw[:10], np.zeros(10), name="z")


def test_selection_and_threshold_never_touch_test_rows(data):
    f, y, s = data
    y_flip = y.copy()
    y_flip.loc[(s == "test").to_numpy()] = 1 - y_flip.loc[(s == "test").to_numpy()]
    for p in (Product.EV_FINANCE, Product.PAPERLESS_BANKING):
        a, b = train_product(f, y, s, p), train_product(f, y_flip, s, p)
        assert a.selected_model_type == b.selected_model_type
        assert a.thresholds == b.thresholds
        assert repr(a.validation_metrics) == repr(b.validation_metrics)
        assert a.calibrator.version == b.calibrator.version
        np.testing.assert_allclose(predict_raw(a, f), predict_raw(b, f))
    # also: test features cannot influence training
    f2 = f.copy()
    f2.loc[(s == "test").to_numpy(), "fuel_spend_90d_avg"] = 1e6
    c = train_product(f2, y, s, Product.EV_FINANCE)
    assert c.thresholds == train_product(f, y, s, Product.EV_FINANCE).thresholds


def test_training_is_deterministic(data):
    f, y, s = data
    a, b = train_product(f, y, s, Product.GREEN_HOME), train_product(f, y, s, Product.GREEN_HOME)
    np.testing.assert_allclose(predict_raw(a, f), predict_raw(b, f))


def test_excluded_rows_not_used_in_training(data):
    f, y, s = data
    y2 = y.copy()
    held = (f["holds_ev_finance"] == 1).to_numpy()
    y2.loc[held, Product.EV_FINANCE.value] = 1  # label noise only on excluded rows
    a = train_product(f, y, s, Product.EV_FINANCE)
    b = train_product(f, y2, s, Product.EV_FINANCE)
    np.testing.assert_allclose(predict_raw(a, f), predict_raw(b, f))


# ---- reason codes ----------------------------------------------------------------------------
def test_catalogue_complete_and_consistent():
    assert set(REASON_CODE_CATALOGUE) == set(ReasonCode)
    for code, d in REASON_CODE_CATALOGUE.items():
        assert d.code is code and d.version == "reasons_v1"
        assert d.customer_wording and d.rm_wording and d.derivation
        assert d.evidence_fields and d.applicable_products


def test_reason_codes_missing_evidence_and_applicability():
    th = fit_reason_thresholds(make_frame()[0])
    empty = {k: None for k in ("is_ice", "fuel_spend_90d_avg", "annual_mileage_km", "home_owner",
                               "electricity_kwh_12m", "paper_statements_3m", "sustainability_preference")}
    for p in PRODUCTS:
        assert derive_reason_codes(empty, p, th) == ([], {})
        assert derive_reason_codes({k: np.nan for k in empty}, p, th) == ([], {})
    feats = {"is_ice": 1.0, "fuel_spend_90d_avg": 400.0, "annual_mileage_km": 30000.0,
             "has_vehicle_finance": 1.0, "home_owner": 1.0, "fuel_type": "PETROL"}
    codes, ev = derive_reason_codes(feats, Product.EV_FINANCE, th)
    assert {ReasonCode.ICE_VEHICLE_OWNER, ReasonCode.HIGH_FUEL_SPEND, ReasonCode.HIGH_ANNUAL_MILEAGE} <= set(codes)
    assert ReasonCode.HOMEOWNER not in codes  # not applicable to EV
    assert ev["monthly_fuel_spend"] == 400.0 and ev["annual_mileage_km"] == 30000.0
    assert ev["vehicle_fuel_type"] == "PETROL" and ev["has_vehicle_finance"] is True
    for p in PRODUCTS:
        c, _ = derive_reason_codes(feats, p, th)
        assert all(p in REASON_CODE_CATALOGUE[x].applicable_products for x in c)
    # missing mileage -> no mileage code even if others fire
    codes, ev = derive_reason_codes({**feats, "annual_mileage_km": None}, Product.EV_FINANCE, th)
    assert ReasonCode.HIGH_ANNUAL_MILEAGE not in codes and "annual_mileage_km" not in ev
    # NO_EXISTING_SOLAR needs an explicit 0, not missing
    assert ReasonCode.NO_EXISTING_SOLAR not in derive_reason_codes(
        {"has_existing_solar": None}, Product.SOLAR_FINANCE, th)[0]
    assert ReasonCode.NO_EXISTING_SOLAR in derive_reason_codes(
        {"has_existing_solar": 0.0}, Product.SOLAR_FINANCE, th)[0]


def test_reason_ordering_dropping_and_cap():
    th = fit_reason_thresholds(make_frame()[0])
    feats = {"is_ice": 1.0, "fuel_spend_90d_avg": 400.0, "annual_mileage_km": 30000.0,
             "vehicle_age_years": 20.0, "has_vehicle_finance": 1.0, "app_logins_3m_avg": 100.0,
             "sustainability_preference": 5.0}
    codes, _ = derive_reason_codes(feats, Product.EV_FINANCE, th)
    assert len(codes) == 4  # capped
    contrib = {"is_ice": 0.1, "fuel_spend_90d_avg": 0.9, "annual_mileage_km": -0.5, "vehicle_age_years": 0.4}
    codes, ev = derive_reason_codes(feats, Product.EV_FINANCE, th, contrib)
    assert ReasonCode.HIGH_ANNUAL_MILEAGE not in codes and "annual_mileage_km" not in ev
    assert codes[0] is ReasonCode.HIGH_FUEL_SPEND and codes[1] is ReasonCode.OLDER_VEHICLE


def test_fit_reason_thresholds_from_training_quantiles(data):
    f, _, _ = data
    th = fit_reason_thresholds(f)
    assert th["fuel_spend_90d_avg"] == pytest.approx(f["fuel_spend_90d_avg"].quantile(0.75))
    assert fit_reason_thresholds(pd.DataFrame())["fuel_spend_90d_avg"] == 120.0  # default


def test_logistic_contributions_shape(bundles, data):
    f, _, _ = data
    b = bundles[Product.EV_FINANCE]
    c = logistic_contributions(b, f.iloc[:20])
    assert list(c.columns) == b.features and len(c) == 20 and np.isfinite(c.to_numpy()).all()


# ---- provider --------------------------------------------------------------------------------
def test_provider_results_validate_and_are_consistent(bundles, data):
    f, _, _ = data
    prov = ModelPropensityProvider(bundles)
    snaps = snapshots(f)
    for p in PRODUCTS:
        res = prov.score_many(snaps, p)
        assert len(res) == len(snaps)
        for r, snap in zip(res, snaps, strict=True):
            PropensityResult.model_validate(r.model_dump())
            assert r.customer_id == snap.customer_id and r.product is p
            assert r.outcome_window_end == snap.feature_cutoff + timedelta(days=90)
            assert r.prediction_timestamp == config.PREDICTION_TIMESTAMP
            assert r.feature_version == snap.feature_version
            assert r.model_type is bundles[p].selected_model_type
            assert r.confidence.status is ConfidenceStatus.SUPPRESSED
            if r.in_model_population:
                assert r.confidence.limitation == "Confidence not validated"
                assert r.confidence.method_version == "none"
            else:
                assert r.propensity == 0.0 and r.reason_codes == [] and r.population_exclusion is not None
            assert all(p in REASON_CODE_CATALOGUE[c].applicable_products for c in r.reason_codes)
        assert any(not r.in_model_population for r in prov.score_many(snapshots(f, 400), p)) or p is Product.PAPERLESS_BANKING


def test_score_many_equals_score_rowwise(bundles, data):
    f, _, _ = data
    prov = ModelPropensityProvider(bundles)
    snaps = snapshots(f, 40)
    for p in PRODUCTS:
        many = prov.score_many(snaps, p)
        single = [prov.score(s, p) for s in snaps]
        for a, b in zip(many, single, strict=True):
            assert a.propensity == pytest.approx(b.propensity, abs=1e-12)
            assert a.raw_score == pytest.approx(b.raw_score, abs=1e-12)
            assert a.reason_codes == b.reason_codes and a.evidence == b.evidence
            assert a.in_model_population == b.in_model_population
    assert prov.score_many([], Product.EV_FINANCE) == []


def test_provider_confidence_injection_and_population_exclusion(bundles, data):
    f, _, _ = data
    calls = []

    def scorer(product, frame, p):
        calls.append((product, len(frame)))
        return [ConfidenceResult(status=ConfidenceStatus.VALIDATED, value=0.8, bucket=ConfidenceBucket.HIGH,
                                 method_version="conf_test") for _ in range(len(frame))]

    prov = ModelPropensityProvider(bundles, confidence_scorer=scorer)
    held = f.index[(f["holds_ev_finance"] == 1).to_numpy()][:3]
    free = f.index[(f["holds_ev_finance"] == 0).to_numpy()][:3]
    res = prov.score_many([snapshot_from_row(c, f.loc[c]) for c in [*held, *free]], Product.EV_FINANCE)
    assert calls == [(Product.EV_FINANCE, 3)]  # only in-population rows are sent to the scorer
    for r in res[:3]:
        assert not r.in_model_population
        assert r.population_exclusion is PopulationExclusion.ALREADY_HOLDS_PRODUCT
        assert r.confidence.status is ConfidenceStatus.SUPPRESSED
    for r in res[3:]:
        assert r.in_model_population and r.confidence.value == 0.8


def test_provider_reason_codes_never_on_missing_evidence(bundles, data):
    f, _, _ = data
    prov = ModelPropensityProvider(bundles)
    row = f.iloc[0].copy()
    row[:] = np.nan
    row["holds_ev_finance"] = 0.0
    r = prov.score(snapshot_from_row("X", row, fuel_type=None), Product.EV_FINANCE)
    assert r.reason_codes == [] and r.evidence == {} and 0 <= r.propensity <= 1


def test_portfolio_scoring_frame(bundles, data):
    f, _, _ = data
    prov = ModelPropensityProvider(bundles)
    out = prov.score_portfolio(f)
    assert list(out.columns) == ["customer_id", "product", "propensity", "raw_score", "in_population",
                                 "threshold", "reason_codes"]
    assert len(out) == len(f) * 4
    ev = out[out["product"] == "EV_FINANCE"].set_index("customer_id")
    assert ev["propensity"].isna().sum() == int((f["holds_ev_finance"] == 1).sum())
    ids = f.index[:30]
    res = prov.score_many([snapshot_from_row(c, f.loc[c]) for c in ids], Product.EV_FINANCE)
    for r in res:
        if r.in_model_population:
            assert ev.loc[r.customer_id, "propensity"] == pytest.approx(r.propensity)
    assert out["propensity"].dropna().between(0, 1).all()


def test_sensitivity(bundles, data):
    f, _, _ = data
    prov = ModelPropensityProvider(bundles)
    snap = snapshot_from_row(f.index[0], f.iloc[0])
    out = prov.sensitivity(snap, Product.EV_FINANCE, "annual_mileage_km", [5000, 15200, 40000])
    assert [v for v, _ in out] == [5000, 15200, 40000] and all(0 <= p <= 1 for _, p in out)
    base = prov.score(snap, Product.EV_FINANCE).propensity
    same = prov.sensitivity(snap, Product.EV_FINANCE, "annual_mileage_km", [snap.features["annual_mileage_km"] or 12000])
    assert len(same) == 1 and isinstance(base, float)
    with pytest.raises(ValueError):
        prov.sensitivity(snap, Product.EV_FINANCE, "holds_ev_finance", [0])


def test_missing_bundle_raises(bundles):
    prov = ModelPropensityProvider({Product.EV_FINANCE: bundles[Product.EV_FINANCE]})
    with pytest.raises(KeyError):
        prov.score(snapshot_from_row("a", pd.Series({"x": 1.0})), Product.GREEN_HOME)


# ---- artifacts -------------------------------------------------------------------------------
def test_save_load_roundtrip(bundles, data, tmp_path):
    import json
    f, _, _ = data
    manifest = save_all(bundles, tmp_path)
    loaded = load_all(root=tmp_path)
    m = json.loads(manifest.read_text())
    assert set(m) == {p.value for p in PRODUCTS}
    for p in PRODUCTS:
        assert (tmp_path / "models" / p.value.lower() / "bundle.joblib").exists()
        a, b = bundles[p], loaded[p]
        assert b.model_version == a.model_version and b.features == a.features and b.threshold == a.threshold
        np.testing.assert_allclose(predict_raw(a, f), predict_raw(b, f))
        np.testing.assert_allclose(a.calibrator.transform(predict_raw(a, f)), b.calibrator.transform(predict_raw(b, f)))
        assert m[p.value]["training_rows"] == a.n_train and m[p.value]["selected_model_type"] == a.selected_model_type.value
    s1 = ModelPropensityProvider(bundles).score(snapshot_from_row("a", f.iloc[0]), Product.GREEN_HOME)
    s2 = ModelPropensityProvider(loaded).score(snapshot_from_row("a", f.iloc[0]), Product.GREEN_HOME)
    assert s1 == s2
