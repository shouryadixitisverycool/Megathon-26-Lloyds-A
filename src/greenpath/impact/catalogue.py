"""Load the bundled, checksum-pinned catalogue without runtime network access."""

import hashlib
import json
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from greenpath.contracts.impact_detail import FactorReference, ImpactIssue, IssueCode

CATALOGUE_VERSION = "greenpath-carbon-factors-v1.0.0"
METHOD_RELEASE = "greenpath-carbon-v1.0.0"
CATALOGUE_SHA256 = "ed367c475920a66d1d7903cc6349b9580f07beb60e8440f61ebcc54607ebbd3c"
GRID_FACTOR = "CEA_GRID_IN_FY2022_23_V19"


@dataclass(frozen=True)
class FactorCatalogue:
    factors: Mapping[str, FactorReference]
    error: str | None = None

    @classmethod
    def load(cls, path: Path | None = None) -> "FactorCatalogue":
        try:
            resource = path or files("greenpath.impact").joinpath(
                "factors/carbon_factors.v1.json"
            )
            content = resource.read_bytes()
            if hashlib.sha256(content).hexdigest() != CATALOGUE_SHA256:
                raise ValueError("Factor catalogue differs from the frozen checksum")
            document = json.loads(content)
            sources = {source["source_id"]: source for source in document["sources"]}
            factors = {}
            for entry in document["factors"]:
                source = sources[entry["source_id"]]
                factors[entry["factor_id"]] = FactorReference(
                    **{key: value for key, value in entry.items()
                       if key not in {"source_locator", "source_id"}},
                    source_id=source["source_id"],
                    source_locator=entry["source_locator"],
                    source_url=source["url"],
                    source_title=source["title"],
                    source_publisher=source["publisher"],
                    source_edition=source["edition"],
                    source_sha256=source["sha256"],
                    verification_basis=source["verification_basis"],
                    source_limitation=source.get("limitation"),
                )
            return cls(MappingProxyType(factors))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            return cls(MappingProxyType({}), str(exc))

    def require(self, factor_id: str, unit: str):
        factor = self.factors.get(factor_id)
        if self.error or factor is None or factor.unit != unit:
            return None, ImpactIssue(
                code=IssueCode.FACTOR_NOT_ESTABLISHED,
                field=f"factors.{factor_id}",
                message=self.error or f"Required factor {factor_id} with unit {unit} is missing",
            )
        return factor, None
