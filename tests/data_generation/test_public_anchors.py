from dataclasses import replace
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from greenpath.data_generation.config import BASE_CONFIG
from greenpath.data_generation.public_anchors import (
    ENERGY_ANCHOR, ENERGY_ANCHOR_SHA256, anchored_demand, anchor_manifest,
)


@pytest.mark.parametrize("fuel", ["electricity", "gas"])
def test_public_marginals_and_synthetic_associations(fuel):
    scores = np.random.default_rng(13).normal(size=100_000)
    demand = anchored_demand(scores, fuel, np.random.default_rng(37))
    ref = ENERGY_ANCHOR[fuel]
    assert np.mean(demand) == pytest.approx(ref["mean_kwh"], rel=0.015)
    assert np.median(demand) == pytest.approx(ref["median_kwh"], rel=0.015)
    assert np.all(np.diff(demand[np.argsort(scores)]) >= 0)


def test_anchor_is_pinned_in_config_hash():
    assert BASE_CONFIG.to_dict()["energy_anchor_sha256"] == ENERGY_ANCHOR_SHA256
    from greenpath.data_generation import public_anchors
    assert hashlib.sha256(Path(public_anchors.__file__).with_name("public_energy_anchor.json").read_bytes()).hexdigest() == ENERGY_ANCHOR_SHA256
    with pytest.raises(ValueError, match="anchor hash"):
        replace(BASE_CONFIG, energy_anchor_sha256="changed")


def test_diagnostics_exclude_incomplete_and_non_consuming_gas():
    full = pd.DataFrame({"customer_id": "full", "month": pd.date_range("2025-01-01", periods=12, freq="MS"),
                         "electricity_kwh": 100.0, "gas_kwh": 0.0})
    incomplete = full.iloc[:11].assign(customer_id="incomplete", electricity_kwh=9999.0, gas_kwh=9999.0)
    diagnostics = anchor_manifest(pd.concat([full, incomplete]))["energy_marginal_diagnostics"]
    assert diagnostics["electricity"]["n_complete_consumers"] == 1
    assert diagnostics["electricity"]["observed_mean_kwh"] == 1200
    assert diagnostics["gas"]["n_complete_consumers"] == 0
    assert diagnostics["gas"]["observed_mean_kwh"] is None
