"""Optional HTTP outputs use verified trained evidence, not the core registry."""

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from greenr import config
from greenr.api.main import create_app
from greenr.extensions.optional_models import OPPORTUNITIES, OptionalModelLoader, train
from tests.ml.test_optional_models import frame, trained, snapshot


@pytest.fixture
def optional_api(trained, frame, tmp_path):
    root, _, _ = trained
    app = create_app(provider_mode="fixture", memory_path=tmp_path / "memory.sqlite3")
    source = snapshot({**frame.iloc[0].to_dict(), "has_investments": 1, "has_mortgage": 1})
    source.data_quality = SimpleNamespace(invalid_product_records=0)
    customer = SimpleNamespace(source_snapshot=source, features={},
                               trust=SimpleNamespace(status="TRUSTED", issues=[]))
    app.state.extension_service.snapshot = lambda customer_id: customer
    app.state.optional_model_loader.root = root / "artifacts"
    app.state.optional_model_loader.frame_path = root / "processed" / f"customer360_{config.FEATURE_CUTOFF}.parquet"
    app.state.optional_model_loader.report_path = root / "reports" / "optional_evaluation.json"
    return TestClient(app), customer


def test_optional_http_structure_and_explicit_purpose(optional_api):
    client, _ = optional_api
    rows = client.get("/customers/OPT0001/optional-opportunities").json()["opportunities"]
    assert [r["product"] for r in rows] == list(OPPORTUNITIES)
    assert rows[0]["probability"] is not None
    assert rows[1]["status"] == "INSUFFICIENT_INFORMATION"
    assert rows[1]["probability"] is None
    for purpose in ("INSULATION", "HEAT_PUMP", "EV_CHARGING"):
        response = client.get("/customers/OPT0001/optional-opportunities", params={"purpose": purpose})
        assert response.status_code == 200
        investment, loan = response.json()["opportunities"]
        assert investment["purpose"] is None
        assert loan["purpose"] == purpose and loan["probability"] is not None
        for row in (investment, loan):
            assert row["experimental"] is True
            assert row["confidence"] is None and row["confidence_status"] == "SUPPRESSED"
            assert row["eligibility"] == "NOT_ASSESSED"
            assert row["impact"] == {"status": "NOT_CLAIMED", "value": None}
            assert row["reason_evidence"] and row["model_version"] and row["calibration_version"]
    assert client.get("/customers/OPT0001/optional-opportunities?purpose=HOLIDAY").status_code == 422


def test_fixture_and_unknown_customer_do_not_load_models(tmp_path):
    app = create_app(provider_mode="fixture", memory_path=tmp_path / "memory.sqlite3")
    app.state.optional_model_loader.load = lambda: pytest.fail("Fixture must not load models")
    client = TestClient(app)
    rows = {row["product"]: row for row in client.get("/customers/GP-001/optional-opportunities").json()["opportunities"]}
    assert rows["GREEN_INVESTMENTS"]["status"] == "OPPORTUNITY_SIGNAL"
    assert rows["GREEN_INVESTMENTS"]["model_version"] == "synthetic-optional-fixture-v1"
    assert rows["GREEN_LOANS"]["status"] == "INSUFFICIENT_INFORMATION" and rows["GREEN_LOANS"]["probability"] is None
    assert rows["GREEN_LOANS"]["reason_codes"] == ["DOCUMENTED_GREEN_PURPOSE_REQUIRED"]
    loans = client.get("/customers/GP-001/optional-opportunities", params={"purpose": "HEAT_PUMP"}).json()["opportunities"][1]
    assert loans["status"] == "OPPORTUNITY_SIGNAL" and "DECLARED_GREEN_PURPOSE_HEAT_PUMP" in loans["reason_codes"]
    assert all(row["confidence"] is None and row["eligibility"] == "NOT_ASSESSED" for row in rows.values())
    conflict = client.get("/customers/GP-003/optional-opportunities").json()["opportunities"]
    assert all(row["reason_codes"] == ["TRUSTED_RECORD_CONFLICT"] for row in conflict)
    assert client.get("/customers/unknown/optional-opportunities").status_code == 404


@pytest.mark.parametrize("issue", ["conflict", "ood", "high", "invalid_records"])
def test_untrusted_records_are_withheld(optional_api, issue):
    client, customer = optional_api
    if issue == "conflict":
        customer.features = {"owns_home": SimpleNamespace(conflicts=["contradictory record"])}
    elif issue == "ood":
        customer.trust.status = "OOD"
    elif issue == "high":
        customer.trust.issues = [SimpleNamespace(severity="HIGH")]
    else:
        customer.source_snapshot.data_quality.invalid_product_records = 1
    rows = client.get("/customers/OPT0001/optional-opportunities?purpose=INSULATION").json()["opportunities"]
    assert all(row["probability"] is None for row in rows)


def test_loader_validates_hashes_and_invalidates_cached_models(trained, tmp_path):
    root, _, _ = trained
    import shutil
    shutil.copytree(root, tmp_path / "copy")
    copied = tmp_path / "copy"
    loader = OptionalModelLoader(copied / "artifacts", copied / "processed", copied / "reports")
    provider, status = loader.load()
    assert status == "AVAILABLE" and loader.load()[0] is provider
    loader.frame_path.write_bytes(loader.frame_path.read_bytes() + b"changed")
    assert loader.load() == (None, "MODEL_STALE")
    loader = OptionalModelLoader(root / "artifacts", root / "processed", copied / "reports")
    artifact = copied / "artifacts" / "green_loans.joblib"
    artifact.write_bytes(b"not a model")
    loader.root = copied / "artifacts"
    assert loader.load() == (None, "MODEL_STALE")
    artifact.unlink()
    assert loader.load() == (None, "NOT_AVAILABLE")


@pytest.mark.parametrize("release_name", ["confidence_release", "labelconfidence_release"])
def test_release_customers_are_excluded_from_fitting_calibration_and_test(trained, frame, tmp_path, release_name):
    root, _, original = trained
    processed = tmp_path / "processed"
    processed.mkdir()
    split = pd.read_csv(root / "processed" / "split_manifest.csv", dtype=str)
    split.loc[split.customer_id.isin(frame.index[-100:]), "split"] = release_name
    split.to_csv(processed / "split_manifest.csv", index=False)
    changed = frame.copy()
    changed.iloc[-100:] = 99999.0
    changed.to_parquet(processed / f"customer360_{config.FEATURE_CUTOFF}.parquet")
    report = train(processed, tmp_path / "artifacts", tmp_path / "reports")
    provider, status = OptionalModelLoader(tmp_path / "artifacts", processed, tmp_path / "reports").load()
    assert status == "AVAILABLE"
    for name in OPPORTUNITIES:
        assert set(report["products"][name]["counts"]) == {"train", "validation", "test"}
        assert report["products"][name]["counts"]["test"]["customers"] <= 100
        np.testing.assert_allclose(original.bundles[name].estimator["logistic"].coef_,
                                   provider.bundles[name].estimator["logistic"].coef_)
        np.testing.assert_allclose(original.bundles[name].predict(frame.iloc[:10]),
                                   provider.bundles[name].predict(frame.iloc[:10]))


def test_sparse_real_splits_raise_instead_of_fabricating_models(frame, tmp_path):
    processed = tmp_path / "processed"
    processed.mkdir()
    tiny = frame.iloc[:3].copy()
    tiny["has_investments"] = 1
    tiny.to_parquet(processed / f"customer360_{config.FEATURE_CUTOFF}.parquet")
    pd.Series(["train", "validation", "test"], index=tiny.index, name="split").to_csv(processed / "split_manifest.csv")
    with pytest.raises(ValueError, match="need both classes"):
        train(processed, tmp_path / "artifacts", tmp_path / "reports")
    assert not list((tmp_path / "artifacts").glob("*.joblib"))
    assert not (tmp_path / "reports" / "optional_evaluation.json").exists()
