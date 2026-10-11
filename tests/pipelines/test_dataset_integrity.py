"""Dataset-wide relational checks and point-in-time cohort context."""

from datetime import date

import pandas as pd
import pytest

from greenr.pipelines import schemas
from greenr.pipelines.predict import _context
from greenr.pipelines.run import cutoff_context, raw_only
from tests.pipelines.fixtures_c360 import make_tables


def dataset():
    dtypes = {"str": "string", "category": "string", "date": "datetime64[ns]",
              "float": "float64", "int": "Int64", "bool": "boolean"}
    tables = {name: pd.DataFrame({col: pd.Series(dtype=dtypes[kind]) for col, kind in schema.columns.items()})
              for name, schema in schemas.ALL_TABLES.items() if name not in schemas.OPTIONAL_TABLES}
    raw, _ = make_tables()
    tables["customers"] = raw["customers"].iloc[:1].copy()
    tables["customers"]["sustainability_preference"] = tables["customers"]["sustainability_preference"].astype("Int64")
    for col in ("home_owner", "has_solar_pv"):
        tables["customers"][col] = tables["customers"][col].astype("boolean")
    tables["transactions"] = pd.DataFrame({
        "transaction_id": ["T1"], "customer_id": ["C001"], "date": pd.to_datetime(["2026-06-15"]),
        "merchant_description": ["FUEL"], "amount": [10.0], "debit_credit": ["DEBIT"],
        "available_at": pd.to_datetime(["2026-06-15"]),
    })
    tables["merchants"] = pd.DataFrame({"merchant_id": ["M1"], "brand": ["Fuel"],
                                        "true_category": ["FUEL"], "is_shift_only": [False]})
    tables["transaction_truth"] = pd.DataFrame({"transaction_id": ["T1"], "merchant_id": ["M1"],
                                               "true_category": ["FUEL"]})
    return tables


def test_valid_dataset_separates_integrity_from_unsupported_outcomes():
    quality = schemas.validate_dataset(dataset())
    assert quality["integrity"]["status"] == "PASS"
    assert quality["outcome_coverage"]["status"] == "UNSUPPORTED"
    assert quality["optional_sources"]["vehicle_ownership"] == "UNSUPPORTED"


@pytest.mark.parametrize("table", ["transactions", "financial_products", "vehicles", "energy_usage", "digital_usage",
                                  "customer_outcomes", "customer_history", "vehicle_ownership", "outcome_observation",
                                  "scenario_evidence"])
def test_every_customer_foreign_key_is_checked(table):
    tables = dataset()
    schema = schemas.ALL_TABLES[table]
    row = {}
    for col, kind in schema.columns.items():
        row[col] = (pd.Timestamp("2026-01-01") if kind == "date" else
                    False if kind == "bool" else 1 if kind in {"int", "float"} else
                    sorted(schema.allowed_values[col])[0] if col in schema.allowed_values else "X")
    row["customer_id"] = "ORPHAN"
    if table == "scenario_evidence":
        row["value"] = "2"
    if table in {"customer_history", "customers"}:
        row["solar_installed_at"] = pd.NaT
    if table == "financial_products":
        row["end_date"] = pd.NaT
    if table in {"energy_usage", "digital_usage"}:
        row["available_at"] = pd.Timestamp("2026-01-31")
    tables[table] = pd.DataFrame([row])
    with pytest.raises(schemas.SchemaError, match="orphan customer_id"):
        schemas.validate_dataset(tables)


def test_truth_requires_exact_bijection_not_only_foreign_key():
    tables = dataset()
    tables["transaction_truth"] = tables["transaction_truth"].iloc[:0]
    with pytest.raises(schemas.SchemaError, match="bijective"):
        schemas.validate_dataset(tables)


@pytest.mark.parametrize("field,value,message", [("merchant_id", "OTHER", "orphan merchant_id"),
                                                 ("true_category", "OTHER", "disagrees")])
def test_merchant_truth_relationship(field, value, message):
    tables = dataset()
    tables["transaction_truth"].loc[0, field] = value
    with pytest.raises(schemas.SchemaError, match=message):
        schemas.validate_dataset(tables)


def test_missingness_per_fuel_is_explicit():
    tables = dataset()
    raw, _ = make_tables()
    vehicles = raw["vehicles"].copy()
    vehicles["customer_id"] = "C001"
    tables["vehicles"] = vehicles
    quality = schemas.validate_dataset(tables)
    assert quality["vehicle_missingness_per_fuel"]["HYBRID"]["missingness"]["annual_mileage"] == 1.0
    assert quality["vehicle_missingness_per_fuel"]["PETROL"]["missingness"]["annual_mileage"] == 0.0


def test_new_source_schemas_preserve_keys_and_nullable_ownership():
    assert schemas.CUSTOMER_HISTORY.columns == schemas.CUSTOMERS.columns
    assert schemas.CUSTOMER_HISTORY.primary_key == ("customer_id", "record_updated_at")
    frame = pd.DataFrame({"customer_id": ["C001"], "has_vehicle": pd.Series([pd.NA], dtype="boolean"),
                          "record_updated_at": pd.to_datetime(["2026-01-01"]),
                          "available_at": pd.to_datetime(["2026-01-01"])})
    schemas.validate_table(frame, schemas.VEHICLE_OWNERSHIP)


def test_cutoff_context_uses_available_history_and_excludes_future_joiners():
    tables, _ = make_tables()
    old = tables["customers"].copy()
    old["record_updated_at"] = pd.Timestamp("2025-01-01")
    old["available_at"] = pd.Timestamp("2025-01-01")
    old.loc[old.customer_id == "C001", "region"] = "Wales"
    latest = tables["customers"].copy()
    latest["available_at"] = pd.Timestamp("2026-07-01")
    tables["customer_history"] = pd.concat([old, latest], ignore_index=True)
    cutoff = date(2026, 6, 30)
    ctx = _context(tables, cutoff)
    assert ctx.loc["C001", "region"] == "Wales"
    assert "C004" not in ctx.index
    assert cutoff_context(tables, date(2026, 7, 31)).loc["C001", "region"] == "London"


def test_current_profile_fallback_masks_unavailable_context():
    tables, _ = make_tables()
    tables["customers"].loc[tables["customers"].customer_id == "C001", "available_at"] = pd.Timestamp("2026-07-01")
    ctx = cutoff_context(tables, date(2026, 6, 30))
    assert ctx.loc["C001"].isna().all()
    assert "C004" not in ctx.index


def test_raw_only_never_exposes_outcome_coverage():
    tables = dataset()
    tables["outcome_observation"] = pd.DataFrame()
    assert "outcome_observation" not in raw_only(tables)
    assert "scenario_evidence" not in raw_only(tables)


def test_schema_type_errors_are_reported_before_availability_comparison():
    tables = dataset()
    tables["transactions"]["available_at"] = "not a date"
    with pytest.raises(schemas.SchemaError, match="expected datetime64"):
        schemas.validate_dataset(tables)


def test_manifest_refresh_hashes_current_2026_factor_bytes(monkeypatch, tmp_path):
    import json

    from greenr import config
    from greenr.pipelines import run

    monkeypatch.setattr(config, "REPO_ROOT", tmp_path)
    for setting, folder in [("RAW_DIR", "raw"), ("PERTURBED_DIR", "perturbed"),
                            ("ARTIFACT_DIR", "artifacts"), ("PROCESSED_DIR", "processed"),
                            ("REPORTS_DIR", "reports")]:
        directory = tmp_path / folder
        directory.mkdir()
        monkeypatch.setattr(config, setting, directory)
    factor_dir = tmp_path / "data" / "factors"
    factor_dir.mkdir(parents=True)
    factor = factor_dir / "desnz_2026.json"
    factor.write_text('{"edition": 2026, "value": 1}')
    run.write_json(config.RAW_DIR / "generator_config.json", {})
    monkeypatch.setattr(run, "stage_env", lambda: {})
    run.write_run_manifest(split_hash="split")
    manifest_path = config.REPORTS_DIR / "RUN_MANIFEST.json"
    first = json.loads(manifest_path.read_text())
    key = "data/factors/desnz_2026.json"
    assert first["factor_files_sha256"][key] == run.sha256_file(factor)
    factor.write_text('{"edition": 2026, "value": 2}')
    run.write_json(config.REPORTS_DIR / "late_evaluation.json", {"status": "complete"})
    run.write_run_manifest(split_hash="split")
    refreshed = json.loads(manifest_path.read_text())
    assert refreshed["factor_files_sha256"][key] != first["factor_files_sha256"][key]
    assert "reports/late_evaluation.json" in refreshed["outputs_sha256"]
    assert "reports/RUN_MANIFEST.json" not in refreshed["outputs_sha256"]
