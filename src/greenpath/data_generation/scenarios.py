"""Explicit synthetic engineering table for a caller-selected demo subset.

EV: chosen 6.5 litres/100km, 18 kWh/100km, 90% charging efficiency.
Insulation: hypothetical 10,000 kWh/year gross-CV gas baseline, 10% electricity
and 20% gas savings. This is NOT a reinterpretation of Customer360 raw gas.
Paperless: hypothetical two sheets per statement and complete avoidance.
Solar is intentionally absent; callers must supply reviewed PVGIS evidence.
No physical activity is inferred from spend, and mileage stays in the source.
"""

from datetime import date
import json

import pandas as pd

from greenpath.contracts.enums import Product
from greenpath.pipelines.scenario_provider import ScenarioEvidence


def generate_scenario_table(customer_ids, *, effective_on: date, available_on: date) -> pd.DataFrame:
    specs = {
        Product.EV_FINANCE: {
            "ice_litres_per_100km": (6.5, "litres/100km"),
            "ev_kwh_per_100km": (18.0, "kWh/100km"),
            "charging_efficiency": (0.9, "fraction"),
        },
        Product.GREEN_HOME: {
            "intervention": ("INSULATION", None),
            "annual_gas_kwh_gross": (10000.0, "kWh/year (Gross CV)"),
            "electricity_saving_fraction": (0.1, "fraction"),
            "gas_saving_fraction": (0.2, "fraction"),
            "savings_evidence": ("Chosen hypothetical insulation savings, not measured", None),
        },
        Product.PAPERLESS_BANKING: {
            "sheets_per_statement": (2, "sheets/statement"),
            "avoided_fraction": (1.0, "fraction"),
        },
    }
    rows = []
    for customer_id in customer_ids:
        for product, fields in specs.items():
            for field, (value, unit) in fields.items():
                rows.append(ScenarioEvidence(customer_id=customer_id, product=product,
                    field=field, value=value, unit=unit,
                    assumption_id=f"engineering-demo-v1:{product.value}:{field}",
                    source_id="synthetic-engineering-design-v1", effective_on=effective_on,
                    available_on=available_on, basis="SYNTHETIC_SCENARIO",
                    description="Explicit chosen hypothetical engineering assumption; not measured or inferred from spend."
                ).model_dump(mode="python"))
    table = pd.DataFrame(rows, columns=list(ScenarioEvidence.model_fields))
    table["value"] = table["value"].map(lambda value: json.dumps(value, allow_nan=False))
    return table
