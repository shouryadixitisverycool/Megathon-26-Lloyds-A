"""Per-product propensity feature lists, population rules and proxy ablation columns.

Feature names are the approved Customer 360 columns (DESIGN.md). Lists follow the
spec 11.3 families. A product's own population flag / post-adoption flag is never a
feature for that product (leakage rule), and proxy attributes (income_band, region,
age_band) are excluded by default (spec 12).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

import numpy as np
import pandas as pd

from greenpath.contracts import PopulationExclusion, Product

PRODUCTS: tuple[Product, ...] = (
    Product.EV_FINANCE,
    Product.GREEN_HOME,
    Product.SOLAR_FINANCE,
    Product.PAPERLESS_BANKING,
)


def product_slug(product: Product) -> str:
    return product.value.lower()


def _spend(cat: str, *suffixes: str) -> list[str]:
    return [f"{cat}_{s}" for s in suffixes]


_ALL_SPEND = ("spend_30d", "spend_90d_avg", "spend_12m_avg", "spend_trend", "txn_freq_90d",
              "spend_share_12m", "days_since_last")

PRODUCT_FEATURES: dict[Product, list[str]] = {
    # fuel level/trend, frequency, mileage, ICE ownership, vehicle age, finance,
    # automotive spend, digital engagement, sustainability preference
    Product.EV_FINANCE: [
        *_spend("fuel", *_ALL_SPEND),
        "annual_mileage_km", "mileage_is_estimated", "has_vehicle", "is_ice", "is_hybrid",
        "vehicle_age_years", "vehicle_record_age_days", "has_vehicle_finance",
        *_spend("automotive", "spend_90d_avg", "spend_12m_avg", "spend_trend"),
        *_spend("public_transport", "spend_90d_avg"),
        "app_logins_3m_avg", "digital_txn_3m_avg", "sustainability_preference",
        "total_spend_12m_avg", "tenure_months", "txn_months_observed",
    ],
    # homeowner/mortgage, utility spend/use, home improvement, mortgage tenure, energy trends
    Product.GREEN_HOME: [
        "home_owner", "has_mortgage", "mortgage_tenure_months", "property_is_house",
        "heating_is_gas", "heating_is_electric", "has_existing_solar", "has_investments",
        *_spend("utilities", "spend_90d_avg", "spend_12m_avg", "spend_trend"),
        *_spend("electricity", "spend_90d_avg", "spend_12m_avg", "spend_trend"),
        *_spend("gas", "spend_90d_avg", "spend_12m_avg", "spend_trend"),
        *_spend("home_improvement", "spend_30d", "spend_90d_avg", "spend_12m_avg", "spend_trend",
                "txn_freq_90d", "days_since_last"),
        "electricity_kwh_12m", "gas_kwh_12m", "electricity_trend", "energy_months_present",
        "sustainability_preference", "total_spend_12m_avg", "tenure_months", "txn_months_observed",
    ],
    # home ownership, electricity consumption/spend, home behaviour (existing solar is the
    # population flag, so it is not a feature)
    Product.SOLAR_FINANCE: [
        "home_owner", "has_mortgage", "mortgage_tenure_months", "property_is_house",
        "heating_is_electric", "has_investments",
        "electricity_kwh_12m", "electricity_trend", "energy_months_present",
        *_spend("electricity", "spend_90d_avg", "spend_12m_avg", "spend_trend"),
        *_spend("home_improvement", "spend_90d_avg", "spend_12m_avg", "txn_freq_90d", "days_since_last"),
        *_spend("utilities", "spend_90d_avg", "spend_trend"),
        "sustainability_preference", "total_spend_12m_avg", "tenure_months", "txn_months_observed",
    ],
    # paper statements, digital ratio, digital transactions, branch visits, digital history
    # (is_paperless is the population flag, so it is not a feature)
    Product.PAPERLESS_BANKING: [
        "paper_statements_3m", "paper_statements_12m", "digital_statement_ratio",
        "digital_txn_3m_avg", "app_logins_3m_avg", "app_logins_trend", "branch_visits_3m",
        "digital_months_present", "sustainability_preference", "total_spend_12m_avg",
        "txn_count_12m", "tenure_months", "txn_months_observed",
    ],
}

# Columns that must never be features for a product (own population / post-adoption flags).
FORBIDDEN_FEATURES: dict[Product, frozenset[str]] = {
    Product.EV_FINANCE: frozenset({"holds_ev_finance", "is_ev"}),
    Product.GREEN_HOME: frozenset({"holds_green_home_loan"}),
    Product.SOLAR_FINANCE: frozenset({"holds_solar_finance", "has_existing_solar"}),
    Product.PAPERLESS_BANKING: frozenset({"is_paperless"}),
}
_FORBIDDEN_FRAGMENTS = ("adopt", "label", "target", "take_up", "outcome")

for _p, _cols in PRODUCT_FEATURES.items():
    _bad = FORBIDDEN_FEATURES[_p].intersection(_cols)
    if _bad:  # import-time guard
        raise RuntimeError(f"{_p}: forbidden features in list: {sorted(_bad)}")


def check_features(product: Product, features: Iterable[str]) -> None:
    """Raise ValueError for leakage-prone or forbidden feature names."""
    for f in features:
        if f in FORBIDDEN_FEATURES[product] or f.startswith("holds_"):
            raise ValueError(f"{f!r} is a population/post-adoption flag and cannot be a {product} feature")
        if any(frag in f.lower() for frag in _FORBIDDEN_FRAGMENTS):
            raise ValueError(f"{f!r} looks like a label/target column")


def population_mask(frame: pd.DataFrame, product: Product) -> tuple[pd.Series, pd.Series]:
    """Model population (DESIGN.md Propensity): customers not already holding the product.

    Returns ``(mask, exclusion)``: ``mask`` is True for in-population rows;
    ``exclusion`` is an object Series of :class:`PopulationExclusion` (None when in population).
    Missing/NaN flags are treated as "not held" (the customer stays in population); a missing
    column is treated as all "not held".
    """

    def flag(col: str) -> pd.Series:
        if col not in frame.columns:
            return pd.Series(False, index=frame.index)
        return (pd.to_numeric(frame[col], errors="coerce") == 1).astype(bool)

    exclusion = pd.Series([None] * len(frame), index=frame.index, dtype=object)

    def mark(cond: pd.Series, reason: PopulationExclusion) -> None:
        sel = cond & exclusion.isna()
        exclusion.loc[sel] = reason

    if product is Product.EV_FINANCE:
        mark(flag("holds_ev_finance"), PopulationExclusion.ALREADY_HOLDS_PRODUCT)
    elif product is Product.GREEN_HOME:
        mark(flag("holds_green_home_loan"), PopulationExclusion.ALREADY_HOLDS_PRODUCT)
    elif product is Product.SOLAR_FINANCE:
        # Holding solar finance is the more specific reason; otherwise existing solar panels.
        mark(flag("holds_solar_finance"), PopulationExclusion.ALREADY_HOLDS_PRODUCT)
        mark(flag("has_existing_solar"), PopulationExclusion.EXISTING_SOLAR)
    elif product is Product.PAPERLESS_BANKING:
        mark(flag("is_paperless"), PopulationExclusion.ALREADY_PAPERLESS)
    else:  # pragma: no cover
        raise ValueError(product)
    return exclusion.isna(), exclusion


def prepare_matrix(frame: pd.DataFrame, features: Sequence[str]) -> pd.DataFrame:
    """Numeric float64 matrix with exactly ``features`` columns (absent columns -> NaN)."""
    cols = {}
    for c in features:
        if c in frame.columns:
            cols[c] = pd.to_numeric(frame[c], errors="coerce").astype("float64").to_numpy()
        else:
            cols[c] = np.full(len(frame), np.nan)
    return pd.DataFrame(cols, index=frame.index, columns=list(features))


# --- proxy ablation (spec 12.2) -------------------------------------------------------------
INCOME_BAND_ORDER: list[str] = ["<25k", "25-50k", "50-75k", "75-100k", "100k+"]
REGION_ORDER: list[str] = sorted({
    "North East", "North West", "Yorkshire", "East Midlands", "West Midlands",
    "East of England", "London", "South East", "South West", "Wales", "Scotland",
})
INCOME_PROXY_COLUMN = "income_band_ord"
REGION_PROXY_COLUMNS: list[str] = [f"region_{r.replace(' ', '_')}" for r in REGION_ORDER]
PROXY_ABLATION_FEATURES: list[str] = [INCOME_PROXY_COLUMN, *REGION_PROXY_COLUMNS]


def add_proxy_features(frame: pd.DataFrame, audit: pd.DataFrame | None = None) -> pd.DataFrame:
    """Return a copy of ``frame`` plus encoded proxy columns for the with-proxy ablation model.

    ``audit`` (index customer_id) supplies ``income_band`` and optionally ``region``; if it has
    no ``region`` the frame's own ``region`` column is used. Unknown/missing values become NaN
    (all region dummies NaN). Use ``PROXY_ABLATION_FEATURES`` as ``extra_features`` in
    ``train_product``. Proxy columns are NEVER part of the default feature lists.
    """
    out = frame.copy()
    src = audit.reindex(frame.index) if audit is not None else pd.DataFrame(index=frame.index)
    income = src["income_band"] if "income_band" in src.columns else pd.Series(np.nan, index=frame.index)
    ordinal = {b: float(i) for i, b in enumerate(INCOME_BAND_ORDER)}
    out[INCOME_PROXY_COLUMN] = income.astype(object).map(ordinal).astype("float64")
    if "region" in src.columns:
        region = src["region"]
    elif "region" in frame.columns:
        region = frame["region"]
    else:
        region = pd.Series(np.nan, index=frame.index)
    region = region.astype(object)
    known = region.isin(REGION_ORDER)
    for r, col in zip(REGION_ORDER, REGION_PROXY_COLUMNS, strict=True):
        vals = (region == r).astype("float64")
        vals[~known] = np.nan
        out[col] = vals
    return out
