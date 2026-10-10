"""Source-pinned regional PVGIS generation, never a self-consumption estimate.

Review/archive a response before supplying its SHA-256. An API outage, changed
response or incompatible metadata raises ValueError; there is no fallback yield.
"""

from decimal import Decimal
import hashlib
import json
from typing import Literal
from urllib.parse import urlencode

import httpx
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


API_URL = "https://re.jrc.ec.europa.eu/api/v5_3/PVcalc"
EVIDENCE_VERSION = "greenpath-pvgis-5.3-fixed-v1"
DOCUMENTATION_URL = (
    "https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/"
    "using-pvgis-5/api-non-interactive-service_en"
)


class GenerationInputs(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False, frozen=True)

    region: str = Field(min_length=1, max_length=100)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    proposed_capacity_kw: float = Field(gt=0, le=1000)
    system_loss_percent: float = Field(ge=0, lt=100)
    tilt_degrees: float = Field(ge=0, le=90)
    azimuth_degrees: float = Field(ge=-180, le=180)
    technology: Literal["crystSi", "crystSi2025", "CIS", "CdTe", "Unknown"]
    mounting: Literal["free", "building"]
    radiation_database: Literal["PVGIS-SARAH3", "PVGIS-ERA5"]
    use_horizon: bool

    def source_url(self) -> str:
        return API_URL + "?" + urlencode({
            "lat": self.latitude, "lon": self.longitude,
            "peakpower": self.proposed_capacity_kw, "loss": self.system_loss_percent,
            "angle": self.tilt_degrees, "aspect": self.azimuth_degrees,
            "pvtechchoice": self.technology, "mountingplace": self.mounting,
            "raddatabase": self.radiation_database, "usehorizon": int(self.use_horizon),
            "fixed": 1, "optimalinclination": 0, "optimalangles": 0,
            "inclined_axis": 0, "vertical_axis": 0, "twoaxis": 0,
            "pvprice": 0, "outputformat": "json", "browser": 0,
        })


class GenerationEstimate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)

    annual_generation_kwh: Decimal = Field(ge=0)
    annual_yield_kwh_per_kw: Decimal = Field(ge=0)
    generation_evidence_version: Literal["greenpath-pvgis-5.3-fixed-v1"]
    source_url: str
    source_sha256: str
    retrieved_at: AwareDatetime
    radiation_year_start: int
    radiation_year_end: int
    inputs: GenerationInputs

    def scenario_fields(self) -> dict:
        """Scalar Customer360 features; demand and self-consumption remain required."""
        reference = (f"{self.generation_evidence_version}; {self.source_url}; "
                     f"sha256={self.source_sha256}; retrieved={self.retrieved_at.isoformat()}; "
                     f"radiation_years={self.radiation_year_start}-{self.radiation_year_end}; "
                     "modelled annual AC generation, not metered or guaranteed")
        return {"annual_generation_kwh": float(self.annual_generation_kwh),
                "proposed_capacity_kw": self.inputs.proposed_capacity_kw,
                "generation_evidence": reference}


def estimate_generation(inputs: GenerationInputs, *, source_sha256: str,
                        retrieved_at: AwareDatetime, response_bytes: bytes | None = None,
                        client: httpx.Client | None = None) -> GenerationEstimate:
    """Consume archived bytes or fetch the exact reviewed versioned request.

    The caller's hash pins actual response bytes, not invented regional yields.
    All physical inputs are mandatory; region is a label, never a geocoder.
    """
    if len(source_sha256) != 64 or any(c not in "0123456789abcdef" for c in source_sha256):
        raise ValueError("A reviewed source response SHA-256 is required")
    url = inputs.source_url()
    if response_bytes is None:
        try:
            if client is None:
                with httpx.Client(timeout=30, follow_redirects=False) as connection:
                    response = connection.get(url)
            else:
                response = client.get(url)
            response.raise_for_status()
            response_bytes = response.content
        except httpx.HTTPError as exc:
            raise ValueError("PVGIS generation source unavailable; no fallback yield") from exc
    if hashlib.sha256(response_bytes).hexdigest() != source_sha256:
        raise ValueError("Pinned generation source checksum mismatch")
    try:
        source = json.loads(response_bytes)
        echoed = source["inputs"]
        checks = ((echoed["location"]["latitude"], inputs.latitude),
                  (echoed["location"]["longitude"], inputs.longitude),
                  (echoed["pv_module"]["peak_power"], inputs.proposed_capacity_kw),
                  (echoed["pv_module"]["system_loss"], inputs.system_loss_percent),
                  (echoed["pv_module"]["technology"], inputs.technology),
                  (echoed["meteo_data"]["radiation_db"], inputs.radiation_database),
                  (echoed["mounting_system"]["fixed"]["slope"]["value"], inputs.tilt_degrees),
                  (echoed["mounting_system"]["fixed"]["azimuth"]["value"], inputs.azimuth_degrees),
                  (echoed["mounting_system"]["fixed"]["type"], inputs.mounting))
        if any(actual != expected or isinstance(actual, bool) for actual, expected in checks):
            raise ValueError("Generation source inputs do not match the requested installation")
        if echoed["meteo_data"]["use_horizon"] is not inputs.use_horizon:
            raise ValueError("Generation source horizon treatment does not match the request")
        units = source["meta"]["outputs"]["totals"]["fixed"]["variables"]["E_y"]["units"]
        if units != "kWh/y":
            raise ValueError("PVGIS E_y must have annual energy units kWh/y, not power or irradiation")
        value = source["outputs"]["totals"]["fixed"]["E_y"]
        generation = Decimal(str(value))
        if isinstance(value, bool) or not generation.is_finite() or generation < 0:
            raise ValueError("Generation must be finite non-negative annual energy")
        first, last = echoed["meteo_data"]["year_min"], echoed["meteo_data"]["year_max"]
        if type(first) is not int or type(last) is not int or not 1900 <= first <= last <= retrieved_at.year:
            raise ValueError("Generation source must identify valid historical radiation years")
        return GenerationEstimate(
            annual_generation_kwh=generation,
            annual_yield_kwh_per_kw=generation / Decimal(str(inputs.proposed_capacity_kw)),
            generation_evidence_version=EVIDENCE_VERSION, source_url=url,
            source_sha256=source_sha256, retrieved_at=retrieved_at,
            radiation_year_start=first, radiation_year_end=last, inputs=inputs,
        )
    except (KeyError, TypeError, ArithmeticError, json.JSONDecodeError) as exc:
        raise ValueError("Generation source lacks compatible PVGIS evidence") from exc
