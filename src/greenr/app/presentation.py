"""Formatting and chart transforms for JSON responses; no business decisions."""

from decimal import Decimal, InvalidOperation
from typing import Any

import plotly.graph_objects as go

PRODUCTS = {
    "EV_FINANCE": "EV Finance", "GREEN_HOME": "Green Home",
    "SOLAR_FINANCE": "Solar Finance", "PAPERLESS_BANKING": "Paperless Banking",
}
STATES = {
    "RECOMMEND": ("Supported opportunity", "green"),
    "DO_NOT_RECOMMEND": ("No recommendation", "gray"),
    "INSUFFICIENT_INFORMATION": ("More evidence needed", "orange"),
    "CONFLICT_REQUIRES_REVIEW": ("Review conflicting evidence", "red"),
    "NOT_APPLICABLE": ("Already adopted or not applicable", "gray"),
    "SUPPRESSED": ("Contact suppressed", "gray"),
}
COLORS = ["#275943", "#876f40", "#456c7a", "#934d40"]


def decimal_number(value: Any) -> Decimal | None:
    """Pydantic encodes Decimal as JSON strings. Reject bools and non-finite values."""
    if value is None or isinstance(value, bool):
        return None
    try:
        result = Decimal(str(value))
        return result if result.is_finite() else None
    except (InvalidOperation, ValueError):
        return None


def percentage(value: Any) -> str:
    number = decimal_number(value)
    return f"{number * 100:.1f}%" if number is not None and 0 <= number <= 1 else "Unavailable"


def impact_label(impact: dict) -> str:
    number = decimal_number(impact.get("value"))
    if impact.get("status") != "AVAILABLE" or number is None:
        return "UNAVAILABLE"
    return f"{number:,.2f} {impact.get('units', '')}".strip()


def finish_chart(figure: go.Figure, y_title: str) -> go.Figure:
    figure.update_layout(
        height=340, margin=dict(l=12, r=12, t=24, b=20),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#20362d"), colorway=COLORS,
        yaxis=dict(title=y_title, rangemode="tozero", dtick=1),
        legend=dict(orientation="h", y=-0.25), hovermode="x unified",
    )
    return figure


def opportunities_chart(rows: list[dict]) -> go.Figure:
    names = [PRODUCTS.get(row["product"], row["product"]) for row in rows]
    figure = go.Figure()
    for index, (state, (label, _)) in enumerate(STATES.items()):
        values = [row.get("state_counts", {}).get(state, 0) for row in rows]
        figure.add_bar(name=label, x=names, y=values,
                       marker_color=["#275943", "#a2aea4", "#b69042", "#934d40", "#6c7e86", "#767064"][index])
    figure.update_layout(barmode="stack")
    return finish_chart(figure, "Product decisions")


def groups_chart(rows: list[dict]) -> go.Figure:
    figure = go.Figure(go.Bar(x=[row["name"] for row in rows],
                             y=[row["recommended_count"] for row in rows], marker_color=COLORS[0]))
    return finish_chart(figure, "Supported opportunities")


def trends_chart(rows: list[dict]) -> go.Figure:
    figure = go.Figure()
    for product, name in PRODUCTS.items():
        selected = sorted((row for row in rows if row["product"] == product), key=lambda row: row["month"])
        if selected:
            figure.add_scatter(x=[row["month"] for row in selected],
                               y=[row["recommended_count"] for row in selected],
                               mode="lines+markers", name=name)
    figure.update_xaxes(type="category", title="Month", categoryorder="array",
                        categoryarray=sorted({row["month"] for row in rows}))
    return finish_chart(figure, "Supported opportunities")
