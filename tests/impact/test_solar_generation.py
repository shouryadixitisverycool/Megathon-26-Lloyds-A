"""Synthetic PVGIS-shaped responses test validation, not real regional yields."""

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json

import httpx
import pytest
from pydantic import ValidationError

from greenpath.impact.solar_generation import GenerationInputs, estimate_generation


NOW = datetime(2026, 10, 10, tzinfo=timezone.utc)
INPUTS = dict(region="London test site", latitude=51.5, longitude=-0.12,
              proposed_capacity_kw=2.0, system_loss_percent=14.0,
              tilt_degrees=35.0, azimuth_degrees=0.0, technology="crystSi",
              mounting="building", radiation_database="PVGIS-SARAH3", use_horizon=True)


def response():
    return {"inputs": {"location": {"latitude": 51.5, "longitude": -0.12},
                       "pv_module": {"peak_power": 2.0, "system_loss": 14.0, "technology": "crystSi"},
                       "meteo_data": {"radiation_db": "PVGIS-SARAH3", "year_min": 2005,
                                      "year_max": 2023, "use_horizon": True},
                       "mounting_system": {"fixed": {"slope": {"value": 35.0},
                                                     "azimuth": {"value": 0.0}, "type": "building"}}},
            "outputs": {"totals": {"fixed": {"E_y": 1800.0}}},
            "meta": {"outputs": {"totals": {"fixed": {"variables": {"E_y": {"units": "kWh/y"}}}}}}}


def estimate(record):
    raw = json.dumps(record).encode()
    return estimate_generation(GenerationInputs(**INPUTS), response_bytes=raw,
                               source_sha256=hashlib.sha256(raw).hexdigest(), retrieved_at=NOW)


def test_generation_and_yield_dimensions_and_pinned_provenance():
    result = estimate(response())
    assert result.annual_generation_kwh == Decimal("1800")
    assert result.annual_yield_kwh_per_kw == Decimal("900")
    assert result.generation_evidence_version == "greenpath-pvgis-5.3-fixed-v1"
    assert "/v5_3/PVcalc?" in result.source_url
    fields = result.scenario_fields()
    assert fields["annual_generation_kwh"] == 1800.0
    assert result.source_sha256 in fields["generation_evidence"]
    assert len(fields["generation_evidence"]) <= 1000
    assert "self_consumption_fraction" not in fields


@pytest.mark.parametrize("field", list(INPUTS))
def test_no_physical_or_location_defaults(field):
    with pytest.raises(ValidationError):
        GenerationInputs(**{k: v for k, v in INPUTS.items() if k != field})


@pytest.mark.parametrize("units", ["kW", "Wh/y", "kWh/m2/y", "kWh", None])
def test_rejects_incompatible_energy_dimensions(units):
    record = response()
    record["meta"]["outputs"]["totals"]["fixed"]["variables"]["E_y"]["units"] = units
    with pytest.raises(ValueError, match="units"):
        estimate(record)


@pytest.mark.parametrize("value", [-1, True, float("nan"), float("inf")])
def test_rejects_invalid_energy(value):
    record = response()
    record["outputs"]["totals"]["fixed"]["E_y"] = value
    with pytest.raises(ValueError):
        estimate(record)


def test_missing_source_and_mismatched_capacity_fail_closed():
    with pytest.raises(ValueError):
        estimate({})
    record = response()
    record["inputs"]["pv_module"]["peak_power"] = 3.0
    with pytest.raises(ValueError, match="inputs"):
        estimate(record)
    with pytest.raises(ValueError, match="SHA-256"):
        estimate_generation(GenerationInputs(**INPUTS), source_sha256="", retrieved_at=NOW)
    with pytest.raises(ValueError, match="checksum"):
        estimate_generation(GenerationInputs(**INPUTS), source_sha256="0" * 64,
                            retrieved_at=NOW, response_bytes=json.dumps(response()).encode())


def test_api_unavailable_has_no_fallback_and_exact_request_is_versioned():
    def unavailable(request):
        assert str(request.url) == GenerationInputs(**INPUTS).source_url()
        return httpx.Response(503)
    with httpx.Client(transport=httpx.MockTransport(unavailable)) as client:
        with pytest.raises(ValueError, match="no fallback"):
            estimate_generation(GenerationInputs(**INPUTS), source_sha256="0" * 64,
                                retrieved_at=NOW, client=client)
