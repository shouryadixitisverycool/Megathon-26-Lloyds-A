import hashlib
from decimal import Decimal as D, localcontext
from pathlib import Path

import pytest
from pydantic import ValidationError

from greenpath.impact import ImpactResult, ImpactStatus
from greenpath.impact.catalogue import CATALOGUE_SHA256, FactorCatalogue


def test_catalogue_checksum_and_original_units_are_preserved():
    path = Path("src/greenpath/impact/factors/carbon_factors.v1.json")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == CATALOGUE_SHA256
    catalogue = FactorCatalogue.load()
    assert catalogue.error is None and len(catalogue.factors) == 5
    scales = {"t CO2/MWh": D(1), "kg CO2/TJ": D("0.000001"), "TJ/Gg": D(1)}
    for factor in catalogue.factors.values():
        assert factor.original_value * scales[factor.original_unit] == factor.value
        assert factor.source_publisher and factor.source_title


@pytest.mark.parametrize("changes", [
    {"value": "999"}, {"value": None}, {"status": "UNAVAILABLE"},
    {"units": "kg CO2e/year"}, {"factors": []}, {"feature_cutoff": None},
])
def test_result_mirror_refuses_inconsistent_available_claims(payload, calculator, changes):
    raw = calculator("ev").calculate(payload("ev")).model_dump()
    raw.update(changes)
    with pytest.raises(ValidationError):
        ImpactResult.model_validate(raw)


def test_unavailable_mirror_refuses_zero_as_a_substitute_for_missing(payload, calculator):
    raw = calculator("paperless").calculate(payload("paperless")).model_dump()
    raw["value"] = D(0)
    with pytest.raises(ValidationError):
        ImpactResult.model_validate(raw)


def test_paperless_count_validation_is_independent_of_decimal_context(payload, calculator):
    data = payload("paperless")
    data["avoided_sheets"]["value"] = "123456789012"
    with localcontext() as ctx:
        ctx.prec = 6
        result = calculator("paperless").calculate(data)
    assert result.status == ImpactStatus.UNAVAILABLE
    assert {issue.code for issue in result.issues} == {"FACTOR_NOT_ESTABLISHED"}


def test_unavailable_paperless_result_roundtrips_with_numeric_evidence(payload, calculator):
    result = calculator("paperless").calculate(payload("paperless"))
    assert ImpactResult.model_validate_json(result.model_dump_json()) == result
