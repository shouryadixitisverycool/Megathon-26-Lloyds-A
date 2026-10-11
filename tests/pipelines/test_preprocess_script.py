"""Standalone preprocessing entrypoint regression tests."""

from datetime import date

import numpy as np
import pandas as pd
import pytest

from greenpath.contracts import Product
from greenpath.models.propensity import PRODUCT_FEATURES
from scripts import preprocess_data


def test_model_inputs_have_exact_order_and_float_dtype(tmp_path):
    frame = pd.DataFrame(
        {
            "fuel_spend_30d": ["12.5", "invalid"],
            "home_owner": [True, False],
            "paper_statements_3m": [2, None],
        },
        index=pd.Index(["C1", "C2"], name="customer_id"),
    )

    paths = preprocess_data.write_model_inputs(frame, tmp_path, date(2026, 6, 30))

    assert set(paths) == {product.value for product in Product}
    for product in Product:
        matrix = pd.read_parquet(paths[product.value])
        assert matrix.columns.tolist() == PRODUCT_FEATURES[product]
        assert matrix.dtypes.eq("float64").all()
        assert matrix.index.tolist() == ["C1", "C2"]
    ev = pd.read_parquet(paths[Product.EV_FINANCE.value])
    assert ev.loc["C1", "fuel_spend_30d"] == 12.5
    assert np.isnan(ev.loc["C2", "fuel_spend_30d"])
    assert ev.drop(columns="fuel_spend_30d").isna().all().all()


def test_main_parses_paths_and_cutoff(monkeypatch, tmp_path):
    observed = {}

    def capture(input_dir, output_dir, cutoff, categorizer_artifact):
        observed.update(input_dir=input_dir, output_dir=output_dir, cutoff=cutoff,
                        categorizer_artifact=categorizer_artifact)

    monkeypatch.setattr(preprocess_data, "preprocess", capture)
    preprocess_data.main([
        "--input-dir", str(tmp_path / "raw"),
        "--output-dir", str(tmp_path / "processed"),
        "--cutoff", "2026-05-31",
        "--categorizer-artifact", str(tmp_path / "categorizer.joblib"),
    ])

    assert observed == {
        "input_dir": tmp_path / "raw",
        "output_dir": tmp_path / "processed",
        "cutoff": date(2026, 5, 31),
        "categorizer_artifact": tmp_path / "categorizer.joblib",
    }


def test_main_rejects_invalid_cutoff():
    with pytest.raises(SystemExit) as exc:
        preprocess_data.main(["--cutoff", "31-05-2026"])
    assert exc.value.code == 2
