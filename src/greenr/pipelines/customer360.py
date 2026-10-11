"""Customer 360 feature view (spec 7; DESIGN.md "Customer 360 feature view").

``build_customer360`` is a pure, vectorised, strictly point-in-time function: it only uses
events whose event time is <= the cutoff and never reads truth/outcome tables.

Semantics (see DESIGN.md plus the decisions below)
--------------------------------------------------
* Transactions: debits only for spend. Windows end at the cutoff (inclusive):
  30d = the 30 days ``cutoff-29 .. cutoff``; 90d = 90 days; 12m = 365 days.
  ``*_spend_90d_avg`` = 90d spend / 3, ``*_spend_12m_avg`` = 12m spend / 12 (fixed
  denominators; ``txn_months_observed`` tells consumers how much history exists).
* Spend features are 0 when the customer has transaction history (any transaction <= cutoff)
  but no spend in the category, and NaN when there is no history at all. Ratios with an
  undefined denominator, and ``*_days_since_last`` when the category was never seen, are NaN.
* Monthly energy/digital rows count only if the whole month ended on/before the cutoff.
  "Last 12 months" = the 12 most recent complete months; "3m" = the 3 most recent.
* Vehicle = latest record with ``record_updated_at <= cutoff``; no record -> all vehicle
  features NaN (a missing record cannot be told apart from "no vehicle").
* Optional customer_history supplies as-of profiles; without it, profile fields whose latest update is after
  the cutoff, or whose update date is missing, are unknown at that cutoff. Relationship
  tenure remains available from the separately dated account-opening record.
* Products = ledger semantics: a flag is 1 if an active, non-INVALID row exists as of the
  cutoff, else 0 (absence of a row means not held).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date, datetime

import numpy as np
import pandas as pd

from greenr.contracts import TransactionCategory
from greenr.pipelines.feature_registry import (
    CONTEXT_COLUMNS,
    POPULATION_FLAGS,
    PROPENSITY_FEATURES,
    SPEND_CATEGORIES,
)
from greenr.pipelines.schemas import TRUTH_TABLES

__all__ = ["build_customer360", "build_customer360_many", "REQUIRED_TABLES"]

REQUIRED_TABLES = ("customers", "financial_products", "vehicles", "energy_usage", "digital_usage")

_CATS = [c.value for c in TransactionCategory]  # includes OTHER; used for totals / shares
_CAT_POS = {c: i for i, c in enumerate(_CATS)}
_NAN = np.nan


def _as_date(d: date | datetime | pd.Timestamp) -> date:
    return d.date() if isinstance(d, datetime) else d


def _days(s: pd.Series) -> np.ndarray:
    """Datetime series -> int64 days since epoch (NaT -> iinfo.min)."""
    return s.to_numpy().astype("datetime64[D]").astype(np.int64)


def _float01(s: pd.Series) -> np.ndarray:
    """bool / nullable bool / object -> float array of 1.0 / 0.0 / NaN."""
    return s.astype("boolean").astype("Float64").to_numpy(dtype=float, na_value=np.nan)


def _whole_months(start: pd.Series, cutoff: date) -> pd.Series:
    """Whole months from ``start`` to the cutoff (floor, never below 0; NaN for NaT)."""
    m = ((cutoff.year - start.dt.year) * 12 + (cutoff.month - start.dt.month)
         - (cutoff.day < start.dt.day).astype(int))
    return m.clip(lower=0).astype(float)


def _month_index(s: pd.Series) -> pd.Series:
    return s.dt.year * 12 + s.dt.month - 1


def _last_complete_month_index(cutoff: date) -> int:
    ci = cutoff.year * 12 + cutoff.month - 1
    is_month_end = (pd.Timestamp(cutoff) + pd.Timedelta(days=1)).month != cutoff.month
    return ci if is_month_end else ci - 1


def _per_customer(values: pd.Series | pd.DataFrame, idx: pd.Index):
    return values.reindex(idx).astype(float)


# --------------------------------------------------------------------------------------------
# Transactions
# --------------------------------------------------------------------------------------------

def _transaction_features(idx: pd.Index, txns: pd.DataFrame, cutoff: date) -> pd.DataFrame:
    n = len(idx)
    ncat = len(_CATS)
    cut_day = int(np.datetime64(cutoff, "D").astype(np.int64))

    ci = idx.get_indexer(txns["customer_id"])
    day = _days(txns["date"])
    keep = (ci >= 0) & (day <= cut_day)
    ci, day = ci[keep], day[keep]
    sub = txns.loc[keep]
    ago = cut_day - day

    cat_codes = pd.Index(_CATS).get_indexer(sub["category"].astype(object)).astype(np.int64)
    if (cat_codes < 0).any():
        bad = sub["category"].to_numpy()[cat_codes < 0][:5]
        raise ValueError(f"transactions carry null/unknown categories: {list(bad)}")
    debit = (sub["debit_credit"] == "DEBIT").to_numpy()
    amount = sub["amount"].to_numpy(dtype=float)

    # Generic history
    first = np.full(n, _NAN)
    last = np.full(n, _NAN)
    if len(ci):
        g = pd.Series(day).groupby(ci)
        first[g.min().index.to_numpy()] = g.min().to_numpy()
        last[g.max().index.to_numpy()] = g.max().to_numpy()
    has_hist = ~np.isnan(first)
    cnt12 = np.bincount(ci[ago < 365], minlength=n).astype(float)

    # Debit spend by (customer, category)
    cd, agod, amtd = ci[debit], ago[debit], amount[debit]
    key = cd * ncat + cat_codes[debit]
    size = n * ncat

    def wsum(mask: np.ndarray) -> np.ndarray:
        return np.bincount(key[mask], weights=amtd[mask], minlength=size).reshape(n, ncat)

    s30, s90, s12 = wsum(agod < 30), wsum(agod < 90), wsum(agod < 365)
    f90 = np.bincount(key[agod < 90], minlength=size).reshape(n, ncat).astype(float)
    last_ago = np.full(size, _NAN)
    if len(key):
        mn = pd.Series(agod).groupby(key).min()
        last_ago[mn.index.to_numpy()] = mn.to_numpy()
    last_ago = last_ago.reshape(n, ncat)
    total12 = s12.sum(axis=1)

    out: dict[str, np.ndarray] = {}
    with np.errstate(divide="ignore", invalid="ignore"):
        for cname in SPEND_CATEGORIES:
            j = _CAT_POS[cname.upper()]
            a30 = np.where(has_hist, s30[:, j], _NAN)
            a90 = np.where(has_hist, s90[:, j] / 3.0, _NAN)
            a12 = np.where(has_hist, s12[:, j] / 12.0, _NAN)
            out[f"{cname}_spend_30d"] = a30
            out[f"{cname}_spend_90d_avg"] = a90
            out[f"{cname}_spend_12m_avg"] = a12
            out[f"{cname}_spend_trend"] = np.where(a12 > 0, a90 / a12 - 1.0, _NAN)
            out[f"{cname}_txn_freq_90d"] = np.where(has_hist, f90[:, j], _NAN)
            out[f"{cname}_spend_share_12m"] = np.where(has_hist & (total12 > 0), s12[:, j] / total12, _NAN)
            out[f"{cname}_days_since_last"] = last_ago[:, j]

    months_obs = np.zeros(n)
    if has_hist.any():
        fi = pd.to_datetime(first[has_hist], unit="D")
        months_obs[has_hist] = (cutoff.year * 12 + cutoff.month) - (fi.year * 12 + fi.month) + 1
    out["txn_months_observed"] = months_obs
    out["txn_count_12m"] = cnt12
    out["total_spend_12m_avg"] = np.where(has_hist, total12 / 12.0, _NAN)
    out["first_txn_date"] = pd.to_datetime(first, unit="D").astype("datetime64[ns]")
    out["last_txn_date"] = pd.to_datetime(last, unit="D").astype("datetime64[ns]")
    return pd.DataFrame(out, index=idx)


# --------------------------------------------------------------------------------------------
# Products, vehicle, home
# --------------------------------------------------------------------------------------------

def _product_features(idx: pd.Index, fp: pd.DataFrame, cutoff: date) -> pd.DataFrame:
    ts = pd.Timestamp(cutoff)
    fp = fp[fp["customer_id"].isin(idx)]
    started = fp["start_date"] <= ts
    is_invalid = fp["status"].astype(str) == "INVALID"
    invalid_cnt = fp.loc[started & is_invalid].groupby("customer_id").size()
    active = fp.loc[started & ~is_invalid & (fp["end_date"].isna() | (fp["end_date"] > ts))]

    def holds(product: str) -> np.ndarray:
        ids = active.loc[active["product"].astype(str) == product, "customer_id"]
        return idx.isin(ids).astype(float)

    mort = active.loc[active["product"].astype(str) == "MORTGAGE"]
    mort_start = mort.groupby("customer_id")["start_date"].min().reindex(idx)
    return pd.DataFrame({
        "has_vehicle_finance": holds("VEHICLE_FINANCE"),
        "has_mortgage": holds("MORTGAGE"),
        "mortgage_tenure_months": _whole_months(mort_start, cutoff).to_numpy(),
        "has_investments": holds("INVESTMENT"),
        "holds_ev_finance": holds("EV_FINANCE"),
        "holds_green_home_loan": holds("GREEN_HOME_LOAN"),
        "holds_solar_finance": holds("SOLAR_FINANCE"),
        "invalid_product_records": invalid_cnt.reindex(idx).fillna(0).astype(int).to_numpy(),
    }, index=idx)


def _vehicle_features(idx: pd.Index, veh: pd.DataFrame, cutoff: date,
                      ownership: pd.DataFrame | None = None) -> pd.DataFrame:
    ts = pd.Timestamp(cutoff)
    v = veh[veh["customer_id"].isin(idx) & (veh["record_updated_at"] <= ts)]
    v = v.sort_values(["customer_id", "record_updated_at"]).copy()
    changed = v["customer_id"].ne(v["customer_id"].shift()) | v["fuel_type"].ne(v["fuel_type"].shift())
    v["vehicle_state_effective_at"] = v["record_updated_at"].where(changed).ffill()
    v = (v.sort_values(["customer_id", "record_updated_at"])
         .drop_duplicates("customer_id", keep="last").set_index("customer_id").reindex(idx))
    has = v["record_updated_at"].notna().to_numpy()
    fuel = v["fuel_type"].astype(object)
    age_days = (ts - v["record_updated_at"]).dt.days.astype(float)
    mileage = v["annual_mileage"].astype(float)

    def flag(mask: pd.Series) -> np.ndarray:
        return np.where(has, mask.to_numpy(dtype=bool).astype(float), _NAN)

    out = pd.DataFrame({
        "has_vehicle": np.where(has, 1.0, _NAN),
        "is_ice": flag(fuel.isin(["PETROL", "DIESEL"])),
        "is_ev": flag(fuel == "EV"),
        "is_hybrid": flag(fuel == "HYBRID"),
        "vehicle_age_years": v["vehicle_age"].astype(float) + age_days / 365.25,
        "annual_mileage_km": mileage,
        "mileage_is_estimated": flag(v["mileage_source"].astype(object) == "ESTIMATED"),
        "vehicle_record_age_days": age_days,
        "vehicle_record_updated_at": v["record_updated_at"],
        "fuel_type": v["fuel_type"],
        "vehicle_state_effective_at": v["vehicle_state_effective_at"],
    }, index=idx)
    if ownership is not None:
        own = ownership.loc[ownership["record_updated_at"] <= ts].sort_values(
            ["customer_id", "record_updated_at"]).drop_duplicates("customer_id", keep="last").set_index("customer_id")
        known = idx.isin(own.index)
        out.loc[known, "has_vehicle"] = _float01(own.reindex(idx)["has_vehicle"])[known]
        absent = out["has_vehicle"] == 0
        out.loc[absent, :] = np.nan
        out.loc[absent, "has_vehicle"] = 0.0
    return out


def _home_features(base: pd.DataFrame, cutoff: date) -> pd.DataFrame:
    ts = pd.Timestamp(cutoff)
    base = base.copy()
    unavailable = base["record_updated_at"].isna() | (base["record_updated_at"] > ts)
    for column in ("home_owner", "heating_type", "property_type", "has_solar_pv",
                   "solar_installed_at", "sustainability_preference", "region", "segment"):
        base.loc[unavailable, column] = pd.NaT if column == "solar_installed_at" else None
    heating = base["heating_type"].astype(object)
    prop = base["property_type"].astype(object)
    h_known, p_known = heating.notna().to_numpy(), prop.notna().to_numpy()

    solar = _float01(base["has_solar_pv"])
    inst = base["solar_installed_at"]
    solar = np.where((inst.notna() & (inst <= ts)).to_numpy(), 1.0, solar)
    solar = np.where((inst.notna() & (inst > ts)).to_numpy(), 0.0, solar)

    return pd.DataFrame({
        "home_owner": _float01(base["home_owner"]),
        "has_existing_solar": solar,
        "heating_is_gas": np.where(h_known, (heating == "GAS_BOILER").to_numpy(dtype=bool).astype(float), _NAN),
        "heating_is_electric": np.where(h_known, (heating == "ELECTRIC").to_numpy(dtype=bool).astype(float), _NAN),
        "property_is_house": np.where(p_known, (prop != "FLAT").to_numpy(dtype=bool).astype(float), _NAN),
        "sustainability_preference": pd.to_numeric(base["sustainability_preference"], errors="coerce")
            .to_numpy(dtype=float, na_value=np.nan),
        "tenure_months": _whole_months(base["customer_since"], cutoff).to_numpy(),
        "region": base["region"],
        "segment": base["segment"],
        "customer_since": base["customer_since"],
        "heating_type": base["heating_type"],
        "property_type": base["property_type"],
    }, index=base.index)


# --------------------------------------------------------------------------------------------
# Energy and digital (monthly tables)
# --------------------------------------------------------------------------------------------

def _energy_features(idx: pd.Index, en: pd.DataFrame, cutoff: date) -> pd.DataFrame:
    last_mi = _last_complete_month_index(cutoff)
    e = en[en["customer_id"].isin(idx)].copy()
    e["mi"] = _month_index(e["month"])
    e = e[(e["mi"] <= last_mi) & (e["mi"] > last_mi - 12)]
    e3 = e[e["mi"] > last_mi - 3]
    g, g3 = e.groupby("customer_id"), e3.groupby("customer_id")

    elec_mean = _per_customer(g["electricity_kwh"].mean(), idx)
    gas_mean = _per_customer(g["gas_kwh"].mean(), idx)
    elec3 = _per_customer(g3["electricity_kwh"].mean(), idx)
    present = (e["electricity_kwh"].notna() | e["gas_kwh"].notna()).groupby(e["customer_id"]).sum()
    with np.errstate(divide="ignore", invalid="ignore"):
        trend = np.where(elec_mean > 0, elec3 / elec_mean - 1.0, _NAN)
    out = pd.DataFrame({
        "electricity_kwh_12m": elec_mean * 12.0,
        "gas_kwh_12m": gas_mean * 12.0,
        "electricity_trend": trend,
        "energy_months_present": present.reindex(idx).fillna(0).clip(0, 12).astype(float),
    }, index=idx)
    for fuel in ("electricity", "gas"):
        count = _per_customer(g[f"{fuel}_kwh"].count(), idx).fillna(0)
        out[f"{fuel}_months_present"] = count
        out[f"{fuel}_kwh_observed"] = _per_customer(g[f"{fuel}_kwh"].sum(min_count=1), idx)
        out[f"{fuel}_annualisation_factor"] = 12.0 / count.replace(0, np.nan)
        estimated = e[f"{fuel}_kwh"].notna() & e["source_quality"].ne("SMART_METER")
        out[f"{fuel}_is_estimated"] = ((count > 0) & ((count < 12) | estimated.groupby(
            e["customer_id"]).any().reindex(idx).fillna(False))).astype(float).where(count > 0)
    return out


def _digital_features(idx: pd.Index, dg: pd.DataFrame, cutoff: date) -> pd.DataFrame:
    last_mi = _last_complete_month_index(cutoff)
    d = dg[dg["customer_id"].isin(idx)].copy()
    d["mi"] = _month_index(d["month"])
    d = d[d["mi"] <= last_mi].sort_values(["customer_id", "mi"])
    latest = d.drop_duplicates("customer_id", keep="last").set_index("customer_id")
    d["digital_statements"] = pd.Series(_float01(d["digital_statements"]), index=d.index)
    contiguous_true = (d["customer_id"].eq(d["customer_id"].shift()) &
                       d["mi"].eq(d["mi"].shift() + 1) &
                       d["digital_statements"].eq(1) & d["digital_statements"].shift().eq(1))
    run = (~contiguous_true).fillna(True).astype(np.int64).cumsum()
    inferred = d.groupby(run)["month"].transform("min").where(d["digital_statements"].eq(1))
    d["paperless_effective_at"] = (pd.to_datetime(d["paperless_effective_at"]).fillna(inferred)
                                  if "paperless_effective_at" in d else inferred)
    d["paperless_effective_at"] = d["paperless_effective_at"].where(d["digital_statements"].eq(1))
    effective = d.drop_duplicates("customer_id", keep="last").set_index("customer_id")["paperless_effective_at"]
    w12 = d[d["mi"] > last_mi - 12]
    w3 = d[d["mi"] > last_mi - 3]
    g12, g3 = w12.groupby("customer_id"), w3.groupby("customer_id")

    logins12 = _per_customer(g12["app_logins"].mean(), idx)
    logins3 = _per_customer(g3["app_logins"].mean(), idx)
    with np.errstate(divide="ignore", invalid="ignore"):
        logins_trend = np.where(logins12 > 0, logins3 / logins12 - 1.0, _NAN)
    return pd.DataFrame({
        "is_paperless": pd.Series(_float01(latest["digital_statements"]), index=latest.index).reindex(idx),
        "paper_statements_3m": _per_customer(g3["paper_statements"].sum(min_count=1), idx),
        "paper_statements_12m": _per_customer(g12["paper_statements"].sum(min_count=1), idx),
        "digital_statement_ratio": _per_customer(g12["digital_statements"].mean(), idx),
        "digital_txn_3m_avg": _per_customer(g3["digital_transactions"].mean(), idx),
        "app_logins_3m_avg": logins3,
        "app_logins_trend": logins_trend,
        "branch_visits_3m": _per_customer(g3["branch_visits"].sum(min_count=1), idx),
        "digital_months_present": _per_customer(g12.size(), idx).fillna(0).clip(0, 12),
        "paperless_effective_at": effective.reindex(idx),
        "paper_statements_post_paperless_3m": _per_customer(
            w3.loc[w3["month"] >= effective.reindex(w3["customer_id"]).set_axis(w3.index)].groupby("customer_id")[
                "paper_statements"].sum(min_count=1), idx),
    }, index=idx)


# --------------------------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------------------------

def _name_lists(mask: pd.DataFrame) -> list[list[str]]:
    names = np.array(mask.columns, dtype=object)
    return [list(names[row]) for row in mask.to_numpy(dtype=bool)]


def build_customer360(tables: Mapping[str, pd.DataFrame], categorised_txns: pd.DataFrame,
                      cutoff: date) -> pd.DataFrame:
    """One row per customer with ``customer_since <= cutoff``, indexed by ``customer_id``.

    ``categorised_txns`` = transactions columns + ``category`` (TransactionCategory value).
    Truth tables must not be passed (ValueError).
    """
    cutoff = _as_date(cutoff)
    # Older caller-supplied frames without ingestion metadata retain event-time semantics;
    # persisted generated tables require available_at through schema validation.
    tables = dict(tables)
    for name in ("financial_products", "vehicles", "energy_usage", "digital_usage",
                 "customer_history", "vehicle_ownership"):
        if name in tables and "available_at" in tables[name]:
            tables[name] = tables[name].loc[tables[name]["available_at"] <= pd.Timestamp(cutoff)]
    if "available_at" in categorised_txns:
        categorised_txns = categorised_txns.loc[categorised_txns["available_at"] <= pd.Timestamp(cutoff)]
    leaked = sorted(set(tables) & set(TRUTH_TABLES))
    if leaked:
        raise ValueError(f"truth/evaluation tables must not reach the feature pipeline: {leaked}")
    missing_tables = [t for t in REQUIRED_TABLES if t not in tables]
    if missing_tables:
        raise ValueError(f"missing raw tables: {missing_tables}")
    if "category" not in categorised_txns.columns:
        raise ValueError("categorised_txns needs a `category` column")

    cust = tables["customers"]
    base = cust.loc[cust["customer_since"] <= pd.Timestamp(cutoff)].set_index("customer_id")
    if "available_at" in base:
        base = base.copy()
        base.loc[base["available_at"].isna() | (base["available_at"] > pd.Timestamp(cutoff)), "record_updated_at"] = pd.NaT
    if "customer_history" in tables:
        history = tables["customer_history"]
        history = history.loc[history["record_updated_at"] <= pd.Timestamp(cutoff)].sort_values(
            ["customer_id", "record_updated_at"]).drop_duplicates("customer_id", keep="last").set_index("customer_id")
        profile_columns = [c for c in base.columns if c != "customer_since"]
        base[profile_columns] = history.reindex(base.index)[profile_columns]
    idx = base.index

    txn = _transaction_features(idx, categorised_txns, cutoff)
    prod = _product_features(idx, tables["financial_products"], cutoff)
    veh = _vehicle_features(idx, tables["vehicles"], cutoff, tables.get("vehicle_ownership"))
    home = _home_features(base, cutoff)
    energy = _energy_features(idx, tables["energy_usage"], cutoff)
    digital = _digital_features(idx, tables["digital_usage"], cutoff)

    df = pd.concat([txn, prod, veh, home, energy, digital], axis=1)
    # A post-state zero requires observable transaction activity in that window.
    post = categorised_txns.loc[categorised_txns["date"] <= pd.Timestamp(cutoff)].copy()
    effective = post["customer_id"].map(df["vehicle_state_effective_at"])
    post = post.loc[(post["date"] >= effective) &
                    (post["date"] > pd.Timestamp(cutoff) - pd.Timedelta(days=90))]
    observed = idx.isin(post["customer_id"])
    fuel = post.loc[post["category"].eq("FUEL") & post["debit_credit"].eq("DEBIT")]
    counts = fuel.groupby("customer_id").size().reindex(idx).fillna(0)
    sums = fuel.groupby("customer_id")["amount"].sum(min_count=1).reindex(idx)
    df["fuel_txn_count_post_vehicle_state_90d"] = counts.where(observed)
    df["fuel_spend_post_vehicle_state_90d"] = sums.where(counts > 0, 0.0).where(observed)

    # Data-quality lists
    has_vehicle = df["has_vehicle"] == 1
    missing = pd.DataFrame({
        "home_owner": df["home_owner"].isna(),
        "region": df["region"].isna(),
        "sustainability_preference": df["sustainability_preference"].isna(),
        "heating_type": df["heating_type"].isna(),
        "property_type": df["property_type"].isna(),
        "has_existing_solar": df["has_existing_solar"].isna(),
        "vehicle": df["has_vehicle"].isna(),
        "annual_mileage_km": has_vehicle & df["annual_mileage_km"].isna(),
        "vehicle_age_years": has_vehicle & df["vehicle_age_years"].isna(),
        "energy": df["energy_months_present"] == 0,
        "digital": df["digital_months_present"] == 0,
        "transactions": df["first_txn_date"].isna(),
    }, index=idx)
    estimated = pd.DataFrame({
        "annual_mileage_km": (df["mileage_is_estimated"] == 1.0) & df["annual_mileage_km"].notna(),
    }, index=idx)
    df["missing_fields"] = pd.Series(_name_lists(missing), index=idx, dtype=object)
    df["estimated_fields"] = pd.Series(_name_lists(estimated), index=idx, dtype=object)

    columns = [*PROPENSITY_FEATURES, *POPULATION_FLAGS, *CONTEXT_COLUMNS]
    df = df[columns].copy()
    df.index.name = "customer_id"
    return df


def build_customer360_many(tables: Mapping[str, pd.DataFrame], categorised_txns: pd.DataFrame,
                           cutoffs: Iterable[date]) -> dict[date, pd.DataFrame]:
    """Customer 360 frames for several cutoffs (e.g. config.TREND_CUTOFFS)."""
    return {c: build_customer360(tables, categorised_txns, c) for c in map(_as_date, cutoffs)}
