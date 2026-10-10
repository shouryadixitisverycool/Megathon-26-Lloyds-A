"""Export JSON Schemas for every top-level contract (``make schemas``).

Writes ``<snake_case_name>.schema.json`` per contract plus a ``CONTRACT_VERSION`` file into
``contracts/schemas/``. Run with::

    uv run --frozen python -m greenpath.contracts.export_schemas
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from greenpath.contracts.base import CONTRACT_VERSION, Contract
from greenpath.contracts.customer import CustomerSnapshot
from greenpath.contracts.impact import ImpactResult
from greenpath.contracts.propensity import PropensityResult, ReasonCodeDefinition
from greenpath.contracts.recommendation import (
    Explanation,
    PortfolioSummary,
    PortfolioTrends,
    Recommendation,
    SegmentRow,
)
from greenpath.contracts.trust import TrustAssessment
from greenpath.contracts import product
from greenpath.contracts.lifecycle import SourceUpdateRequest

__all__ = ["SCHEMA_DIR", "TOP_LEVEL_CONTRACTS", "build_schemas", "render_schema", "write_schemas"]

SCHEMA_DIR: Path = Path(__file__).resolve().parent / "schemas"
VERSION_FILE_NAME = "CONTRACT_VERSION"

TOP_LEVEL_CONTRACTS: dict[str, type[Contract]] = {
    "customer_snapshot": CustomerSnapshot,
    "propensity_result": PropensityResult,
    "reason_code_definition": ReasonCodeDefinition,
    "trust_assessment": TrustAssessment,
    "impact_result": ImpactResult,
    "recommendation": Recommendation,
    "explanation": Explanation,
    "portfolio_summary": PortfolioSummary,
    "segment_row": SegmentRow,
    "portfolio_trends": PortfolioTrends,
    "product_customer_snapshot": product.CustomerSnapshot,
    "product_recommendation": product.Recommendation,
    "product_explanation": product.Explanation,
    "product_history_record": product.HistoryRecord,
    "source_update_request": SourceUpdateRequest,
}


def build_schemas() -> dict[str, dict[str, Any]]:
    """JSON Schema per file name, generated in memory (no disk access)."""
    return {
        f"{name}.schema.json": model.model_json_schema()
        for name, model in TOP_LEVEL_CONTRACTS.items()
    }


def render_schema(schema: dict[str, Any]) -> str:
    """Deterministic on-disk text: sorted keys, two-space indent, trailing newline."""
    return json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def write_schemas(directory: Path | str = SCHEMA_DIR) -> list[Path]:
    """Write every schema file and the CONTRACT_VERSION marker into ``directory``."""
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for file_name, schema in build_schemas().items():
        path = target / file_name
        path.write_text(render_schema(schema), encoding="utf-8")
        written.append(path)
    version_path = target / VERSION_FILE_NAME
    version_path.write_text(f"{CONTRACT_VERSION}\n", encoding="utf-8")
    written.append(version_path)
    return written


if __name__ == "__main__":
    for path in write_schemas():
        print(path)
