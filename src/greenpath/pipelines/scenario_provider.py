"""Point-in-time engineering assumptions, separate from propensity features.

ArtifactRepository can optionally inject this provider and pass
``provider.attach(source_snapshot, product)`` to the UK calculator, including
historical cutoffs. No matching rows means no scenario, not fallback defaults.
"""

from datetime import date
import json
from typing import Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt, StrictStr, field_validator

from greenpath.contracts.customer import CustomerSnapshot
from greenpath.contracts.enums import Product


class ScenarioEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)
    customer_id: str
    product: Product
    field: str
    value: StrictFloat | StrictInt | StrictStr
    unit: str | None
    assumption_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    effective_on: date
    available_on: date
    basis: Literal["SYNTHETIC_SCENARIO", "REVIEWED_PVGIS", "EXPLICIT_FORECAST"]
    description: str = Field(min_length=1)

    @field_validator("value", mode="before")
    @classmethod
    def explicit_value(cls, value):
        if isinstance(value, bool):
            raise ValueError("Scenario quantities and labels cannot be booleans")
        return value


class UKImpactInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    snapshot: CustomerSnapshot
    scenario: tuple[ScenarioEvidence, ...] = ()


class ScenarioProvider:
    def __init__(self, table: pd.DataFrame):
        rows = table.to_dict("records")
        for row in rows:
            row["value"] = json.loads(row["value"])
            if pd.isna(row.get("unit")):
                row["unit"] = None
        self.rows = tuple(ScenarioEvidence.model_validate(row) for row in rows)

    def get_scenario(self, customer_id: str, product: Product, cutoff: date):
        selected = {}
        for row in self.rows:
            if (row.customer_id == customer_id and row.product == Product(product)
                    and row.effective_on <= cutoff and row.available_on <= cutoff):
                previous = selected.get(row.field)
                if previous is None or (row.effective_on, row.available_on) > (previous.effective_on, previous.available_on):
                    selected[row.field] = row
                elif (row.effective_on, row.available_on) == (previous.effective_on, previous.available_on):
                    raise ValueError(f"Conflicting scenario rows for {row.field}")
        return tuple(selected.values())

    def attach(self, snapshot: CustomerSnapshot, product: Product) -> UKImpactInput:
        return UKImpactInput(snapshot=snapshot, scenario=self.get_scenario(
            snapshot.customer_id, product, snapshot.feature_cutoff))
