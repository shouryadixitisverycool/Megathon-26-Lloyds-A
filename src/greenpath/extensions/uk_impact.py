"""UK annual physical scenario passports, using matched DESNZ 2025 CO2e factors.

Separate from the legacy CO2 calculators. No banking spend or propensity enters a
physical calculation. Every forecast activity must be supplied explicitly.
"""

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from greenpath.contracts.enums import Product


class PhysicalInputs(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)


class EVInputs(PhysicalInputs):
    annual_mileage_km: float = Field(ge=0, le=200000)
    fuel_type: Literal["PETROL", "DIESEL"]
    ice_litres_per_100km: float = Field(gt=0, le=50)
    ev_kwh_per_100km: float = Field(gt=0, le=100)
    charging_efficiency: float = Field(gt=0, le=1)
    mileage_evidence: Literal["OBSERVED", "ESTIMATED", "USER_SCENARIO"]


class SolarInputs(PhysicalInputs):
    annual_electricity_kwh: float = Field(ge=0, le=200000)
    annual_generation_kwh: float = Field(ge=0, le=200000)
    self_consumption_fraction: float = Field(ge=0, le=1)
    region: str = Field(min_length=1, max_length=100)
    generation_evidence: str = Field(min_length=1, max_length=1000)
    proposed_capacity_kw: float = Field(gt=0, le=1000)


class InsulationInputs(PhysicalInputs):
    intervention: Literal["INSULATION"]
    annual_electricity_kwh: float = Field(ge=0, le=200000)
    annual_gas_kwh_gross: float = Field(ge=0, le=500000)
    electricity_saving_fraction: float = Field(ge=0, le=1)
    gas_saving_fraction: float = Field(ge=0, le=1)
    savings_evidence: str = Field(min_length=1, max_length=1000)


class HeatPumpInputs(PhysicalInputs):
    intervention: Literal["HEAT_PUMP"]
    annual_heating_gas_kwh_gross: float = Field(ge=0, le=500000)
    boiler_efficiency_gross: float = Field(gt=0, le=1)
    seasonal_performance_factor: float = Field(gt=0, le=10)
    performance_evidence: str = Field(min_length=1, max_length=1000)


class PaperlessInputs(PhysicalInputs):
    annual_statements: int = Field(ge=0, le=10000)
    sheets_per_statement: int = Field(ge=1, le=100)
    avoided_fraction: float = Field(ge=0, le=1)


FACTOR_PATH = Path(__file__).with_name("uk_factors_2025.json")
FACTOR_SUBSET_SHA256 = "d4fcc4996c54a286a5c66c6c952f69894392a46f682a3eb206c6f9562d03d2cd"
BOUNDARY = "Operational well-to-wheel energy emissions; manufacturing and embodied emissions excluded"
METHOD_VERSION = "uk-physical-scenarios-v1"


def factor_catalogue() -> dict:
    if hashlib.sha256(FACTOR_PATH.read_bytes()).hexdigest() != FACTOR_SUBSET_SHA256:
        raise ValueError("Pinned UK factor subset checksum mismatch")
    return json.loads(FACTOR_PATH.read_text())


def calculate(product: Product | str, inputs: dict) -> dict:
    """Explicit UK annual forecast; validation failures raise ValueError, no invented defaults."""
    product = Product(product)
    catalogue = factor_catalogue()
    factors = catalogue["factors"]
    def factor(name):
        return Decimal(factors[name]["value"])
    def number(value):
        return Decimal(str(value))
    grid_keys = ("electricity_kwh", "electricity_td_kwh", "electricity_wtt_generation_kwh", "electricity_wtt_td_kwh")
    grid = sum((factor(k) for k in grid_keys), Decimal(0))
    gas_keys = ("gas_gross_kwh", "gas_wtt_gross_kwh")
    gas = sum((factor(k) for k in gas_keys), Decimal(0))
    used = list(grid_keys)
    limitations = ["Modelled annual scenario, not a measured outcome or a guarantee.",
                  "Physical assumptions are supplied by the caller; their accuracy is not independently verified.",
                  "Current 2025 factors are held constant; no future grid decarbonisation is assumed.",
                  "Official reporting convention excludes outside-of-scopes biogenic combustion CO2."]
    if product == Product.EV_FINANCE:
        request = EVInputs.model_validate(inputs)
        prefix = request.fuel_type.lower()
        used += [prefix + "_litre", prefix + "_wtt_litre"]
        baseline_activity = number(request.annual_mileage_km) * number(request.ice_litres_per_100km) / 100
        scenario_activity = (number(request.annual_mileage_km) * number(request.ev_kwh_per_100km)
                             / 100 / number(request.charging_efficiency))
        baseline = baseline_activity * (factor(prefix + "_litre") + factor(prefix + "_wtt_litre"))
        scenario = scenario_activity * grid
        formula = "km × litres/100km ÷ 100 × fuel WTW; km × EV kWh/100km ÷ 100 ÷ charging efficiency × electricity WTW"
        method = "UK_EV_OPERATIONAL_WTW_V1"
    elif product == Product.SOLAR_FINANCE:
        request = SolarInputs.model_validate(inputs)
        displacement = number(request.annual_generation_kwh) * number(request.self_consumption_fraction)
        if displacement > number(request.annual_electricity_kwh):
            raise ValueError("Self-consumed generation cannot exceed annual electricity demand")
        baseline = number(request.annual_electricity_kwh) * grid
        scenario = (number(request.annual_electricity_kwh) - displacement) * grid
        formula = "baseline demand × electricity WTW; (baseline demand − generation × self-consumption fraction) × electricity WTW"
        method = "UK_SOLAR_SELF_CONSUMPTION_WTW_V1"
        limitations += ["Export receives no avoided-emission credit. PV manufacturing, battery storage and embodied emissions are excluded.",
                        "Generation is an explicit scenario input, not inferred from region, utility spend or roof eligibility."]
    elif product == Product.GREEN_HOME:
        used += list(gas_keys)
        if inputs.get("intervention") == "HEAT_PUMP":
            request = HeatPumpInputs.model_validate(inputs)
            demand = number(request.annual_heating_gas_kwh_gross)
            baseline = demand * gas
            scenario = demand * number(request.boiler_efficiency_gross) / number(request.seasonal_performance_factor) * grid
            formula = "heating gas × gas WTW; heating gas × gross boiler efficiency ÷ seasonal performance × electricity WTW"
            method = "UK_HEAT_PUMP_OPERATIONAL_WTW_V1"
            limitations += ["Only the explicitly supplied gas heating load is replaced; other household energy uses are excluded."]
        else:
            request = InsulationInputs.model_validate(inputs)
            electricity, gas_demand = number(request.annual_electricity_kwh), number(request.annual_gas_kwh_gross)
            baseline = electricity * grid + gas_demand * gas
            scenario = (electricity * (1 - number(request.electricity_saving_fraction)) * grid
                        + gas_demand * (1 - number(request.gas_saving_fraction)) * gas)
            formula = "electricity × electricity WTW + gross gas × gas WTW, before and after supplied energy-saving fractions"
            method = "UK_INSULATION_OPERATIONAL_WTW_V1"
    else:
        request = PaperlessInputs.model_validate(inputs)
        avoided_statements = number(request.annual_statements) * number(request.avoided_fraction)
        return {"product": product.value, "status": "NOT_CLAIMED", "carbon_status": "NOT_CLAIMED",
                "paper_statements_avoided": str(avoided_statements),
                "paper_sheets_avoided": str(avoided_statements * request.sheets_per_statement),
                "method_version": "PAPERLESS_ACTIVITY_V1", "inputs": request.model_dump(mode="json"),
                "limitation": "Paper avoidance is an activity scenario. No reviewed lifecycle carbon method is implemented."}
    passport = {"product": product.value, "status": "MODELLED_ESTIMATE", "units": "kg CO2e/year",
                "baseline_emissions": str(baseline), "scenario_emissions": str(scenario),
                "potential_reduction": str(baseline - scenario), "method": method,
                "method_version": METHOD_VERSION, "boundary": BOUNDARY,
                "time_horizon": "annual", "factor_vintage": catalogue["version"],
                "factor_source": catalogue["source_url"], "factor_source_sha256": catalogue["source_sha256"],
                "factor_subset_sha256": hashlib.sha256(FACTOR_PATH.read_bytes()).hexdigest(),
                "factor_records": {key: factors[key] for key in used},
                "inputs": request.model_dump(mode="json"), "formula": formula,
                "calculated_at": datetime.now(timezone.utc).isoformat(),
                "limitations": limitations}
    identity = json.dumps({k: v for k, v in passport.items() if k != "calculated_at"}, sort_keys=True).encode()
    passport["passport_id"] = "UK-" + hashlib.sha256(identity).hexdigest()[:24]
    return passport
