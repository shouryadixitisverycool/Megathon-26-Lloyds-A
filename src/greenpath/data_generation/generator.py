"""Latent stochastic synthetic data generator (spec 6, 8.2).

Design
------
1. Hidden per-customer *traits* are drawn first (true mileage, fuel intensity, vehicle age,
   electricity / gas demand, home-improvement intent, digital affinity, sustainability attitude,
   wealth, age, home ownership, ...). One unobserved latent preference per product is drawn too.
2. Every observed table is a noisy, partially missing *view* of those traits (vehicle records with
   estimated / missing / stale mileage, transactions with Poisson counts and partial capture,
   energy readings with gaps, a 1..5 stated preference, ...).
3. Per product ``latent = Σ β·trait + Σ γ·trait_i·trait_j + β_pref·pref + noise``. Monthly adoption
   from 2025-07 to 2026-09 is simulated with hazard ``sigmoid(latent + intercept + ε_month)``; the
   intercept is calibrated so the 90-day rate among not-yet-adopters at the cutoff matches the
   config target. There is no deterministic ``if feature > x: adopt`` rule anywhere.
4. Adoption has consequences in the observed data after the adoption date (EV -> EV_FINANCE + EV
   vehicle record + fuel spend stops, solar -> SOLAR_FINANCE + has_solar_pv, ...), including a
   share of deliberately inconsistent records (stale ICE record, continued fuel spend).

Everything is vectorised over customers / customer-months; the only Python loops are over
products, categories and months-of-history constants.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from greenpath.contracts import PRODUCT_IDS, Product
from greenpath.data_generation.config import PRODUCTS, GeneratorConfig
from greenpath.data_generation.merchants import MerchantCatalogue, build_catalogue, category_weights
from greenpath.data_generation.public_anchors import anchored_demand, anchor_manifest
from greenpath.pipelines.schemas import ALL_TABLES, validate_table

__all__ = ["generate", "write_dataset", "TimeGrid"]

NONE_DAY = np.int64(10**9)  # sentinel "never" day
REGIONS = ("London", "South East", "North West", "East of England", "West Midlands", "South West",
           "Yorkshire", "Scotland", "East Midlands", "Wales", "North East")
REGION_WEIGHTS = np.array([0.13, 0.14, 0.11, 0.09, 0.09, 0.085, 0.08, 0.08, 0.07, 0.045, 0.04])
REGION_AREAS = {
    "London": ("SW", "SE", "E", "N", "NW", "W"), "South East": ("RG", "GU", "BN", "ME", "OX"),
    "North West": ("M", "L", "PR", "WA", "BL"), "East of England": ("CB", "NR", "IP", "CO", "LU"),
    "West Midlands": ("B", "CV", "WV", "ST", "WS"), "South West": ("BS", "EX", "PL", "TR", "BA"),
    "Yorkshire": ("LS", "S", "YO", "HU", "BD"), "Scotland": ("G", "EH", "AB", "DD", "KY"),
    "East Midlands": ("NG", "LE", "DE", "LN", "NN"), "Wales": ("CF", "SA", "LL", "NP"),
    "North East": ("NE", "SR", "DH", "TS"),
}
SUNNY = {"South West", "South East", "London", "East of England"}
AGE_EDGES = (25, 35, 45, 55, 65)
AGE_BANDS = ("18-24", "25-34", "35-44", "45-54", "55-64", "65+")
INCOME_BANDS = ("<25k", "25-50k", "50-75k", "75-100k", "100k+")


def _day(d: str | date) -> np.int64:
    return np.datetime64(d, "D").astype(np.int64)


def _to_dt(days: np.ndarray) -> np.ndarray:
    """int days since epoch (NONE_DAY / negative sentinel -> NaT) -> datetime64[ns] array."""
    days = np.asarray(days, dtype=np.int64)
    bad = (days >= NONE_DAY) | (days < -50_000)
    out = np.where(bad, 0, days).astype("datetime64[D]").astype("datetime64[ns]")
    out[bad] = np.datetime64("NaT")
    return out


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def _z(x: np.ndarray, mask: np.ndarray | None = None) -> np.ndarray:
    """Standardise (over ``mask`` if given; 0 outside it)."""
    m = np.ones(len(x), bool) if mask is None else mask
    if m.sum() < 2:
        return np.zeros(len(x))
    mu, sd = x[m].mean(), x[m].std() or 1.0
    return np.where(m, (x - mu) / sd, 0.0)


class TimeGrid:
    """Monthly grid over the simulated history (2025-01 .. 2026-09)."""

    def __init__(self, cfg: GeneratorConfig):
        start, end = pd.Timestamp(cfg.history_start), pd.Timestamp(cfg.history_end)
        months = pd.date_range(start, end, freq="MS")
        self.month_start = months.to_numpy().astype("datetime64[D]").astype(np.int64)
        nxt = np.append(self.month_start[1:], _day(end.date()) + 1)
        self.month_len = nxt - self.month_start
        self.M = len(months)
        self.year = months.year.to_numpy()
        self.month = months.month.to_numpy()
        self.start_day = _day(start.date())
        self.end_day = _day(end.date())
        self.cutoff_day = _day(cfg.calibration_cutoff)
        adopt0 = _day(cfg.adoption_start)
        self.adopt_months = np.flatnonzero(self.month_start >= adopt0)
        self.cutoff_month = int(np.flatnonzero(self.month_start <= self.cutoff_day)[-1])
        self.pre_cols = np.flatnonzero(self.month_start[self.adopt_months] <= self.cutoff_day)
        self.win_cols = np.flatnonzero(self.month_start[self.adopt_months] > self.cutoff_day)

    def month_of(self, day: np.ndarray) -> np.ndarray:
        return np.searchsorted(self.month_start, day, side="right") - 1


# ------------------------------------------------------------------------------------------------
# Population and traits
# ------------------------------------------------------------------------------------------------

def _population(cfg: GeneratorConfig, rng: np.random.Generator, tg: TimeGrid) -> dict[str, np.ndarray]:
    n = cfg.n_customers
    p: dict[str, np.ndarray] = {}
    p["customer_id"] = np.array([f"C{200001 + i}" for i in range(n)], dtype=object)

    # Tenure: most long-standing; ~5% joined in 2025, ~late_joiner_rate in 2026.
    u = rng.random(n)
    late = u < cfg.late_joiner_rate
    mid = (u >= cfg.late_joiner_rate) & (u < cfg.late_joiner_rate + 0.05)
    join = _day("2024-12-31") - (rng.exponential(7.0 * 365, n)).astype(np.int64)
    join = np.maximum(join, _day("1995-01-01"))
    join[mid] = _day("2025-01-05") + rng.integers(0, 350, mid.sum())
    join[late] = _day("2026-01-02") + rng.integers(0, 165, late.sum())
    p["join_day"] = join

    age = np.clip(rng.normal(46, 15, n), 18, 90)
    wealth = rng.normal(0, 1, n) + 0.012 * (np.clip(age, 18, 60) - 40)
    region = rng.choice(len(REGIONS), size=n, p=REGION_WEIGHTS / REGION_WEIGHTS.sum())
    london = region == 0
    green = 0.75 * rng.normal(0, 1, n) + 0.2 * wealth - 0.008 * (age - 46) + 0.25 * london
    digital = rng.normal(0, 1, n) - 0.035 * (age - 46) + 0.15 * wealth
    p.update(age=age, wealth=wealth, region=region, london=london.astype(float), green=green,
             digital=digital, sunny=np.isin(np.array(REGIONS)[region], list(SUNNY)).astype(float))

    owner = rng.random(n) < _sigmoid(0.6 + 0.95 * wealth + 0.05 * (age - 45) - 0.7 * london)
    mortgage = owner & (rng.random(n) < _sigmoid(1.6 - 0.09 * (age - 45)))
    house = rng.random(n) < np.where(owner, 0.86, 0.45) - 0.25 * london
    ptype = np.where(~house, 0, 1 + (rng.random(n) < _sigmoid(0.2 + 0.8 * wealth)).astype(int)
                     + (rng.random(n) < _sigmoid(-1.0 + 0.9 * wealth)).astype(int))  # 0 flat .. 3 detached
    rural = np.isin(np.array(REGIONS)[region], ["Scotland", "Wales", "South West"])
    r = rng.random(n)
    heat = np.full(n, 0)  # 0 gas, 1 electric, 2 oil, 3 heat pump
    flat = ptype == 0
    heat[flat & (r < 0.30)] = 1
    heat[flat & (r >= 0.30) & (r < 0.32)] = 3
    heat[~flat & (r < 0.05)] = 1
    heat[~flat & (r >= 0.05) & (r < 0.05 + np.where(rural, 0.12, 0.03))] = 2
    hp = ~flat & (heat == 0) & (rng.random(n) < _sigmoid(-3.4 + 0.7 * green))
    heat[hp] = 3
    p.update(owner=owner, mortgage=mortgage, house=house, ptype=ptype, heat=heat)

    hi = rng.normal(0, 1, n) + 0.35 * owner + 0.15 * wealth
    p["hi"] = hi

    # Vehicles
    has_car = rng.random(n) < _sigmoid(1.45 + 0.6 * wealth - 1.4 * london + 0.01 * (age - 45))
    vt = np.where(rng.random(n) < 0.90, 0, np.where(rng.random(n) < 0.7, 1, 2))  # CAR VAN MOTO
    ev_owner = has_car & (vt == 0) & (rng.random(n) < _sigmoid(np.log(cfg.preexisting_rates["ev_owner"] / 0.95)
                                                            + 0.7 * green + 0.4 * wealth - 0.3))
    r = rng.random(n)
    fuel = np.where(r < _sigmoid(-2.3 + 0.6 * green), 2, np.where(r < 0.42, 1, 0))  # 0 petrol 1 diesel 2 hybrid
    fuel = np.where(ev_owner, 3, fuel)
    mileage = np.exp(rng.normal(np.log(11500) + 0.15 * wealth, 0.5, n)) * np.select(
        [vt == 1, vt == 2], [1.6, 0.4], 1.0)
    intensity = np.exp(rng.normal(0, 0.3, n))
    vage = np.clip(rng.gamma(2.2, 3.4, n), 0.4, 25)
    vage = np.where(ev_owner, np.clip(rng.gamma(2.0, 1.4, n), 0.3, 8), vage)
    vfin = has_car & (rng.random(n) < _sigmoid(-1.0 - 0.18 * (vage - 7) + 0.3 * wealth))
    p.update(has_car=has_car, vtype=vt, ev_owner=ev_owner, fuel=fuel, mileage=np.where(has_car, mileage, 0.0),
             intensity=intensity, vage=np.where(has_car, vage, np.nan), vfin=vfin)
    ice = has_car & ~ev_owner
    per_km = 0.105 * np.where(fuel == 2, 0.6, np.where(fuel == 1, 0.92, 1.0))
    p["fuel_spend"] = np.where(ice, mileage / 12 * per_km * intensity, 0.0)  # true monthly £

    # Energy demand (annual kWh)
    elec_score = rng.normal(0.2 * wealth + 0.25 * house + 0.65 * (heat == 1)
                            + 0.35 * (heat == 3) + 0.35 * ev_owner, 0.33, n)
    elec = anchored_demand(elec_score, "electricity", rng)
    has_gas = heat == 0
    gas_score = rng.normal(0.15 * wealth + 0.25 * house - 0.25 * flat, 0.3, n)
    gas = np.zeros(n)
    gas[has_gas] = anchored_demand(gas_score[has_gas], "gas", rng)
    p.update(elec=elec, gas=gas, has_gas=has_gas)

    # Pre-existing green holdings (before the simulated adoption period)
    pr = cfg.preexisting_rates
    p["ev_fin_pre"] = ev_owner & (rng.random(n) < pr["ev_finance_given_ev"])
    p["gh_pre"] = owner & (rng.random(n) < pr["green_home_given_owner"] * np.exp(0.5 * green - 0.1))
    p["solar_pre"] = owner & house & (rng.random(n) < pr["solar_given_owner_house"] * np.exp(0.5 * green + 0.3 * wealth - 0.2))
    p["solar_fin_pre"] = p["solar_pre"] & (rng.random(n) < pr["solar_finance_given_solar"])
    p["paperless_pre"] = rng.random(n) < _sigmoid(pr["paperless_intercept"] + 1.4 * digital + 0.35 * green)
    return p


def _traits(p: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    car = p["has_car"]
    ice = car & ~p["ev_owner"]
    return {
        "mileage": _z(np.log(np.maximum(p["mileage"], 1.0)), car),
        "fuel_intensity": _z(np.log(p["intensity"]), ice),
        "vehicle_age": _z(np.nan_to_num(p["vage"]), car),
        "elec_demand": _z(np.log(p["elec"])),
        "gas_demand": _z(np.log(np.maximum(p["gas"], 1.0)), p["has_gas"]),
        "home_improvement": _z(p["hi"]),
        "digital": _z(p["digital"]),
        "green": _z(p["green"]),
        "wealth": _z(p["wealth"]),
        "age": _z(p["age"]),
        "owner": p["owner"].astype(float),
        "mortgage": p["mortgage"].astype(float),
        "house": p["house"].astype(float),
        "vehicle_finance": p["vfin"].astype(float),
        "no_ice_car": (~ice | (p["vtype"] == 2)).astype(float),
        "ev_owner": p["ev_owner"].astype(float),
        "sunny_region": p["sunny"],
        "electric_heating": (p["heat"] == 1).astype(float),
    }


# ------------------------------------------------------------------------------------------------
# Latent outcomes
# ------------------------------------------------------------------------------------------------

def _latent(cfg: GeneratorConfig, product: str, traits: dict[str, np.ndarray],
            rng: np.random.Generator) -> np.ndarray:
    n = len(traits["green"])
    pref = rng.normal(0, 1, n)
    noise = rng.normal(0, 1, n) * cfg.noise_scale
    lat = noise.copy()
    for name, w in cfg.coefficients[product].items():
        lat += w * (pref if name == "latent_pref" else traits[name])
    for pair, s in cfg.interactions.get(product, {}).items():
        a, b = pair.split("*")
        lat += s * traits[a] * traits[b]
    return lat


def _calibrate(lat: np.ndarray, eps: np.ndarray, elig: np.ndarray, at_cutoff: np.ndarray,
               tg: TimeGrid, target: float) -> float:
    pre, win = tg.pre_cols, tg.win_cols

    def rate(b: float) -> float:
        h = _sigmoid(lat[:, None] + b + eps) * elig
        s_pre = np.prod(1 - h[:, pre], axis=1)
        w = 1 - np.prod(1 - h[:, win], axis=1)
        s = s_pre[at_cutoff]
        return float((s * w[at_cutoff]).sum() / max(s.sum(), 1e-9))

    lo, hi = -15.0, 5.0
    for _ in range(50):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if rate(mid) < target else (lo, mid)
    return (lo + hi) / 2


def _simulate_adoption(cfg: GeneratorConfig, p: dict, traits: dict, rng: np.random.Generator,
                       tg: TimeGrid) -> dict[str, np.ndarray]:
    """Adoption day per customer and product (NONE_DAY if never adopted in the window)."""
    n = len(p["join_day"])
    months = tg.adopt_months
    mstart = tg.month_start[months]
    joined = mstart[None, :] >= (p["join_day"][:, None] + 30)
    not_holding = {
        "EV_FINANCE": ~p["ev_fin_pre"],
        "GREEN_HOME": ~p["gh_pre"],
        "SOLAR_FINANCE": ~p["solar_pre"],
        "PAPERLESS_BANKING": ~p["paperless_pre"],
    }
    at_cutoff = p["join_day"] <= tg.cutoff_day
    out: dict[str, np.ndarray] = {}
    for product in PRODUCTS:
        lat = _latent(cfg, product, traits, rng)
        eps = rng.normal(0, cfg.monthly_noise * cfg.noise_scale, (n, len(months)))
        elig = joined & not_holding[product][:, None]
        b = _calibrate(lat, eps, elig, at_cutoff & not_holding[product], tg, cfg.target_90d_rate[product])
        h = _sigmoid(lat[:, None] + b + eps) * elig
        hit = rng.random((n, len(months))) < h
        any_hit = hit.any(axis=1)
        first = np.argmax(hit, axis=1)
        mlen = np.minimum(tg.month_len[months], 28)
        day = mstart[first] + (rng.random(n) * mlen[first]).astype(np.int64)
        out[product] = np.where(any_hit, day, NONE_DAY)
    return out


# ------------------------------------------------------------------------------------------------
# Observed tables (except transactions)
# ------------------------------------------------------------------------------------------------

def _customers(cfg, p, adopt, rng, tg) -> pd.DataFrame:
    n = len(p["join_day"])
    miss = cfg.missingness
    regions = np.array(REGIONS, dtype=object)[p["region"]]
    area = np.array([REGION_AREAS[r][i % len(REGION_AREAS[r])] for r, i in
                     zip(regions, rng.integers(0, 6, n), strict=True)], dtype=object)
    sector = np.char.add(np.char.add(area.astype(str), rng.integers(1, 30, n).astype(str)),
                         np.char.add(" ", rng.integers(1, 10, n).astype(str))).astype(object)
    reg_null = rng.random(n) < miss["region"]
    regions = np.where(reg_null, None, regions)
    sector = np.where(reg_null | (rng.random(n) < 0.01), None, sector)

    age_band = np.array(AGE_BANDS, dtype=object)[np.searchsorted(AGE_EDGES, p["age"], side="right")]
    inc = p["wealth"] + rng.normal(0, 0.6, n) + 0.01 * (np.clip(p["age"], 18, 60) - 40)
    income_band = np.array(INCOME_BANDS, dtype=object)[np.searchsorted([-0.9, 0.3, 1.1, 1.7], inc)]
    seg_score = p["wealth"] + rng.normal(0, 0.3, n)
    segment = np.where(seg_score > 1.25, "AFFLUENT", np.where(seg_score > 0.3, "MASS_AFFLUENT", "MASS")).astype(object)

    # Home ownership: noisy, partly missing; a few mortgaged owners recorded as non-owners (conflict).
    owner_obs = p["owner"].copy()
    owner_obs[p["mortgage"] & (rng.random(n) < 0.0075)] = False
    owner_obs = pd.array(owner_obs, dtype="boolean")
    owner_obs[rng.random(n) < miss["home_owner"]] = pd.NA

    ptype = np.array(["FLAT", "TERRACED", "SEMI_DETACHED", "DETACHED"], dtype=object)[p["ptype"]]
    ptype = np.where(rng.random(n) < miss["property_type"], None, ptype)
    heat = np.array(["GAS_BOILER", "ELECTRIC", "OIL", "HEAT_PUMP"], dtype=object)[p["heat"]]
    heat = np.where(rng.random(n) < miss["heating_type"], None, heat)

    solar_day = np.full(n, NONE_DAY)
    pre = p["solar_pre"]
    solar_day[pre] = _day("2013-01-01") + rng.integers(0, 12 * 365, pre.sum())
    solar_day[pre & (rng.random(n) < 0.3)] = NONE_DAY  # installed at unknown date
    adopted = adopt["SOLAR_FINANCE"] < NONE_DAY
    solar_day[adopted] = adopt["SOLAR_FINANCE"][adopted]
    has_solar = pd.array(pre | adopted, dtype="boolean")
    has_solar[~(pre | adopted) & (rng.random(n) < miss["has_solar_pv"])] = pd.NA

    pref = np.clip(np.round(3 + 1.1 * _z(p["green"]) + rng.normal(0, 0.75, n)), 1, 5).astype(int)
    pref = pd.array(pref, dtype="Int64")
    pref[rng.random(n) < miss["sustainability_preference"]] = pd.NA

    upd = np.maximum(p["join_day"] + rng.integers(0, 60, n),
                     _day("2025-06-01") + rng.integers(0, 480, n))
    upd = np.where(adopted, np.maximum(upd, solar_day + rng.integers(1, 30, n)), upd)
    upd = np.minimum(upd, tg.end_day)
    return pd.DataFrame({
        "customer_id": p["customer_id"],
        "customer_since": _to_dt(p["join_day"]),
        "age_band": age_band,
        "income_band": income_band,
        "region": regions,
        "postcode_sector": sector,
        "segment": segment,
        "home_owner": owner_obs,
        "property_type": ptype,
        "heating_type": heat,
        "has_solar_pv": has_solar,
        "solar_installed_at": _to_dt(solar_day),
        "sustainability_preference": pref,
        "record_updated_at": _to_dt(upd),
    })


def _uniform_days(rng, lo: np.ndarray, hi: np.ndarray) -> np.ndarray:
    span = np.maximum(hi - lo, 0)
    return lo + (rng.random(len(lo)) * (span + 1)).astype(np.int64)


def _financial_products(cfg, p, adopt, rng, tg, owner_obs: pd.Series) -> pd.DataFrame:
    n = len(p["join_day"])
    ids = p["customer_id"]
    join = p["join_day"]
    w = p["wealth"]
    frames = []

    def add(mask, product, start, end=None, balance=None, status="ACTIVE"):
        k = int(mask.sum())
        if k == 0:
            return
        frames.append(pd.DataFrame({
            "customer_id": ids[mask], "product": product,
            "start_date": _to_dt(np.asarray(start)[mask] if np.ndim(start) else np.full(k, start)),
            "end_date": _to_dt(np.full(k, NONE_DAY) if end is None else np.asarray(end)[mask]),
            "balance": np.full(k, np.nan) if balance is None else np.round(np.asarray(balance)[mask], 2),
            "status": status if np.ndim(status) == 0 else np.asarray(status)[mask],
        }))

    everyone = np.ones(n, bool)
    add(everyone, "CURRENT_ACCOUNT", join, balance=np.exp(rng.normal(np.log(2500) + 0.6 * w, 0.9)))

    mort_start = np.maximum(join, _uniform_days(rng, np.full(n, _day("2002-01-01")), np.full(n, _day("2026-05-01"))))
    mort_start = np.minimum(mort_start, np.maximum(join + 20, mort_start))
    add(p["mortgage"], "MORTGAGE", mort_start,
        balance=np.exp(rng.normal(np.log(165_000) + 0.3 * w, 0.5)))
    # Owners recorded False who still have an active mortgage are kept as a conflict.
    # Some closed mortgages (outright owners who paid off).
    closed = p["owner"] & ~p["mortgage"] & (rng.random(n) < 0.25)
    cl_start = np.maximum(join, _day("2000-01-01") + rng.integers(0, 20 * 365, n))
    cl_end = np.minimum(cl_start + rng.integers(365, 25 * 365, n), _day("2026-08-30"))
    cl_end = np.maximum(cl_end, cl_start + 30)
    add(closed, "MORTGAGE", cl_start, end=cl_end, balance=np.zeros(n), status="CLOSED")

    vf_start = np.maximum(join, _uniform_days(rng, np.full(n, _day("2021-03-01")), np.full(n, _day("2026-04-30"))))
    add(p["vfin"], "VEHICLE_FINANCE", vf_start, balance=np.exp(rng.normal(np.log(9_000), 0.6, n)))
    vf_closed = p["has_car"] & ~p["vfin"] & (rng.random(n) < 0.10)
    vfc_start = np.maximum(join, _uniform_days(rng, np.full(n, _day("2018-01-01")), np.full(n, _day("2023-06-01"))))
    vfc_end = np.minimum(vfc_start + rng.integers(700, 1500, n), _day("2026-05-31"))
    vfc_end = np.maximum(vfc_end, vfc_start + 30)
    add(vf_closed, "VEHICLE_FINANCE", vfc_start, end=vfc_end, balance=np.zeros(n), status="CLOSED")

    inv = rng.random(n) < _sigmoid(-1.9 + 1.0 * w + 0.02 * (p["age"] - 45))
    inv_start = np.maximum(join, _uniform_days(rng, np.full(n, _day("2010-01-01")), np.full(n, _day("2026-05-01"))))
    add(inv, "INVESTMENT", inv_start, balance=np.exp(rng.normal(np.log(18_000) + 0.5 * w, 0.9)))

    # Pre-existing green products
    pre_day = np.maximum(join, _uniform_days(rng, np.full(n, _day("2021-06-01")), np.full(n, _day("2025-05-31"))))
    add(p["ev_fin_pre"], "EV_FINANCE", pre_day, balance=np.exp(rng.normal(np.log(22_000), 0.4, n)))
    gh_day = np.maximum(join, _uniform_days(rng, np.full(n, _day("2020-01-01")), np.full(n, _day("2025-05-31"))))
    add(p["gh_pre"], "GREEN_HOME_LOAN", gh_day, balance=np.exp(rng.normal(np.log(12_000), 0.5, n)))
    sf_day = np.maximum(join, _uniform_days(rng, np.full(n, _day("2018-01-01")), np.full(n, _day("2025-05-31"))))
    add(p["solar_fin_pre"], "SOLAR_FINANCE", sf_day, balance=np.exp(rng.normal(np.log(7_000), 0.4, n)))

    # Adoption-driven green products (start_date = adoption)
    for product, ptype, bal in (("EV_FINANCE", "EV_FINANCE", 28_000), ("GREEN_HOME", "GREEN_HOME_LOAN", 15_000),
                                ("SOLAR_FINANCE", "SOLAR_FINANCE", 9_000)):
        d = adopt[product]
        add(d < NONE_DAY, ptype, d, balance=np.exp(rng.normal(np.log(bal), 0.35, n)))

    # A few INVALID records (data-quality noise)
    inv_rec = rng.random(n) < 0.006
    inv_prod = np.array(["MORTGAGE", "VEHICLE_FINANCE", "INVESTMENT", "EV_FINANCE", "SOLAR_FINANCE"],
                        dtype=object)[rng.integers(0, 5, n)]
    inv_day = np.maximum(join + 1, _uniform_days(rng, np.full(n, _day("2023-01-01")), np.full(n, _day("2026-05-31"))))
    if inv_rec.any():
        frames.append(pd.DataFrame({
            "customer_id": ids[inv_rec], "product": inv_prod[inv_rec], "start_date": _to_dt(inv_day[inv_rec]),
            "end_date": _to_dt(np.full(inv_rec.sum(), NONE_DAY)), "balance": np.nan, "status": "INVALID"}))
    fp = pd.concat(frames, ignore_index=True)
    return fp.drop_duplicates(["customer_id", "product", "start_date"], keep="first").reset_index(drop=True)


def _vehicles(cfg, p, adopt, rng, tg, ev_conflict: np.ndarray) -> pd.DataFrame:
    n = len(p["join_day"])
    miss = cfg.missingness
    cutoff = tg.cutoff_day
    has_rec = p["has_car"] & (rng.random(n) >= miss["vehicle_record_missing"])
    stale = rng.random(n) < miss["vehicle_stale"]
    first = np.where(stale, _uniform_days(rng, np.full(n, _day("2020-06-01")), np.full(n, _day("2024-05-31"))),
                     _uniform_days(rng, np.full(n, _day("2024-07-01")), np.full(n, _day("2026-06-10"))))
    first = np.maximum(first, p["join_day"] + rng.integers(0, 25, n))
    renew = has_rec & ~stale & (first < _day("2025-06-01")) & (rng.random(n) < 0.3)
    second = _uniform_days(rng, first + 180, np.full(n, tg.end_day - 5))
    vtypes = np.array(["CAR", "VAN", "MOTORCYCLE"], dtype=object)
    fuels = np.array(["PETROL", "DIESEL", "HYBRID", "EV"], dtype=object)

    def obs(mask, rec_day, fuel_idx, vage_at_cutoff, mileage):
        k = int(mask.sum())
        idx = np.flatnonzero(mask)
        r = rng.random(k)
        missing = r < miss["mileage_missing"]
        est = (r >= miss["mileage_missing"]) & (r < miss["mileage_missing"] + miss["mileage_estimated"])
        m_obs = mileage[idx] * np.exp(rng.normal(0, 0.08, k))
        m_est = np.round(mileage[idx] * np.exp(rng.normal(0, 0.35, k)), -3)
        mil = np.where(est, np.maximum(m_est, 1000.0), np.round(m_obs, -1))
        mil = np.where(missing, np.nan, mil)
        src = np.where(missing, None, np.where(est, "ESTIMATED", "OBSERVED")).astype(object)
        age = vage_at_cutoff[idx] - (cutoff - rec_day[idx]) / 365.25
        age = np.round(np.maximum(age, 0.0), 1)
        age = np.where(rng.random(k) < miss["vehicle_age_missing"], np.nan, age)
        return pd.DataFrame({
            "customer_id": p["customer_id"][idx], "vehicle_type": vtypes[p["vtype"][idx]],
            "fuel_type": fuels[fuel_idx[idx]], "vehicle_age": age, "annual_mileage": mil,
            "mileage_source": src, "record_updated_at": _to_dt(rec_day[idx])})

    vage = np.nan_to_num(p["vage"], nan=5.0)
    frames = [obs(has_rec, first, p["fuel"], vage, p["mileage"]),
              obs(renew, second, p["fuel"], vage, p["mileage"])]
    # EV adoption -> new EV record (unless the record is left stale: conflict type 1)
    ev_day = adopt["EV_FINANCE"]
    new_rec_day = ev_day + rng.integers(3, 26, n)
    ev_rec = (ev_day < NONE_DAY) & (ev_conflict != 1) & (new_rec_day <= tg.end_day)
    new_age = rng.uniform(0.0, 1.5, n) + (cutoff - new_rec_day) / 365.25  # age as of the cutoff
    frames.append(obs(ev_rec, new_rec_day, np.full(n, 3), new_age, p["mileage"] * 1.05))
    veh = pd.concat(frames, ignore_index=True)
    veh = veh.sort_values(["customer_id", "record_updated_at"], kind="stable")
    return veh.drop_duplicates(["customer_id", "record_updated_at"], keep="last").reset_index(drop=True)


def _season(tg: TimeGrid, amp: float) -> np.ndarray:
    return 1 + amp * np.cos(2 * np.pi * (tg.month - 1) / 12)


def _energy_monthly(p, adopt, tg) -> tuple[np.ndarray, np.ndarray]:
    """True monthly electricity and gas kWh (n, M) incl. adoption effects."""
    n = len(p["join_day"])
    m_idx = np.arange(tg.M)[None, :]
    ev_m = tg.month_of(np.minimum(adopt["EV_FINANCE"], tg.end_day))
    ev_m = np.where(adopt["EV_FINANCE"] < NONE_DAY, ev_m, 10**6)
    sol_m = tg.month_of(np.minimum(adopt["SOLAR_FINANCE"], tg.end_day))
    sol_m = np.where(adopt["SOLAR_FINANCE"] < NONE_DAY, sol_m, 10**6)
    elec_annual = p["elec"][:, None] + 2200.0 * (m_idx > ev_m[:, None])
    elec_annual = elec_annual * np.where(m_idx > sol_m[:, None], 0.70, 1.0)
    elec_annual = elec_annual * np.where(p["solar_pre"][:, None], 0.75, 1.0) * np.ones((n, 1))
    elec = elec_annual / 12 * _season(tg, 0.18)[None, :]
    gas = p["gas"][:, None] / 12 * _season(tg, 0.70)[None, :]
    return elec, gas


def _energy_usage(cfg, p, adopt, rng, tg) -> pd.DataFrame:
    n = len(p["join_day"])
    miss = cfg.missingness
    elec, gas = _energy_monthly(p, adopt, tg)
    smart = rng.random(n) < 0.72
    sd = np.where(smart, 0.05, 0.15)[:, None]
    e_obs = elec * np.exp(rng.normal(0, 1, elec.shape) * sd)
    g_obs = gas * np.exp(rng.normal(0, 1, gas.shape) * sd)
    e_obs = np.where(smart[:, None], np.round(e_obs, 1), np.round(e_obs, -1))
    g_obs = np.where(smart[:, None], np.round(g_obs, 1), np.round(g_obs, -1))
    present = (tg.month_start[None, :] + tg.month_len[None, :] > p["join_day"][:, None])
    present &= (rng.random(n) >= miss["energy_absent"])[:, None]
    gappy = rng.random(n) < miss["energy_gappy"]
    present &= ~(gappy[:, None] & (rng.random(elec.shape) < miss["energy_gap_month"]))
    ci, mi = np.nonzero(present)
    e = e_obs[ci, mi]
    e[rng.random(len(e)) < 0.01] = np.nan
    return pd.DataFrame({
        "customer_id": p["customer_id"][ci],
        "month": _to_dt(tg.month_start[mi]),
        "electricity_kwh": e,
        "gas_kwh": g_obs[ci, mi],
        "source_quality": np.where(smart[ci], "SMART_METER", "ESTIMATED_BILL").astype(object),
    })


def _digital_usage(cfg, p, adopt, rng, tg) -> pd.DataFrame:
    n = len(p["join_day"])
    shape = (n, tg.M)
    dz = _z(p["digital"])
    present = (tg.month_start[None, :] + tg.month_len[None, :] > p["join_day"][:, None])
    present &= (rng.random(n) >= cfg.missingness["digital_absent"])[:, None]
    trend = np.linspace(0, 0.12, tg.M)[None, :]
    logins = rng.poisson(np.exp(1.9 + 0.75 * dz[:, None] + trend + rng.normal(0, 0.15, shape)))
    dtx = rng.poisson(np.exp(2.9 + 0.55 * dz[:, None] + 0.1 * _z(p["wealth"])[:, None] + rng.normal(0, 0.12, shape)))
    branch = rng.poisson(np.exp(-1.3 - 0.9 * dz[:, None] + 0.015 * (p["age"][:, None] - 45)), size=shape)
    adopt_m = np.where(adopt["PAPERLESS_BANKING"] < NONE_DAY,
                       tg.month_of(np.minimum(adopt["PAPERLESS_BANKING"], tg.end_day)), 10**6)
    paperless = p["paperless_pre"][:, None] | (np.arange(tg.M)[None, :] >= adopt_m[:, None])
    paper = np.where(paperless, 0, 1 + rng.poisson(0.25, shape))
    conflict = p["paperless_pre"] & (rng.random(n) < 0.015)
    paper = np.where(conflict[:, None] & (rng.random(shape) < 0.5), 1, paper)
    ci, mi = np.nonzero(present)
    return pd.DataFrame({
        "customer_id": p["customer_id"][ci],
        "month": _to_dt(tg.month_start[mi]),
        "digital_statements": paperless[ci, mi].astype(bool),
        "paper_statements": paper[ci, mi].astype(np.int64),
        "digital_transactions": dtx[ci, mi].astype(np.int64),
        "app_logins": logins[ci, mi].astype(np.int64),
        "branch_visits": branch[ci, mi].astype(np.int64),
    })


# ------------------------------------------------------------------------------------------------
# Transactions (vectorised)
# ------------------------------------------------------------------------------------------------

class _TxnBuilder:
    def __init__(self, cat: MerchantCatalogue, shift: dict, rng: np.random.Generator, n: int):
        self.cat, self.shift, self.rng, self.n = cat, shift, rng, n
        self.K = cat.variants.shape[1]
        self.parts: list[tuple[np.ndarray, ...]] = []
        self._weights: dict[tuple, tuple[np.ndarray, np.ndarray]] = {}

    def weights(self, category: str, kinds: tuple[str, ...]):
        key = (category, kinds)
        if key not in self._weights:
            self._weights[key] = category_weights(self.cat.table, category, kinds, self.shift)
        return self._weights[key]

    def pick(self, category: str, kinds: tuple[str, ...], size: int) -> np.ndarray:
        idx, w = self.weights(category, kinds)
        return idx[self.rng.choice(len(idx), size=size, p=w)]

    def add(self, ci, day, merch, amount, credit=False, variant=None):
        k = len(ci)
        if variant is None:
            variant = self.rng.integers(0, self.K, k)
        self.parts.append((ci.astype(np.int64), day.astype(np.int64), merch.astype(np.int64),
                           variant.astype(np.int64), np.round(amount, 2),
                           np.full(k, bool(credit))))

    def card_stream(self, category, rate: np.ndarray, amount_mean: np.ndarray, sigma: float,
                    tg: TimeGrid, loyalty: float, keep_fn=None):
        """Poisson counts per customer-month -> transactions on random days."""
        rng = self.rng
        frac = (tg.month_len / 30.4)[None, :]
        counts = rng.poisson(rate * frac)
        flat = np.repeat(np.arange(counts.size), counts.ravel())
        ci, mi = flat // tg.M, flat % tg.M
        day = tg.month_start[mi] + (rng.random(len(ci)) * tg.month_len[mi]).astype(np.int64)
        pref = self.pick(category, ("card",), self.n)
        merch = np.where(rng.random(len(ci)) < loyalty, pref[ci], self.pick(category, ("card",), len(ci)))
        amt = amount_mean[ci] * np.exp(rng.normal(0, sigma, len(ci)) - sigma**2 / 2)
        if keep_fn is not None:
            keep = keep_fn(ci, day)
            ci, day, merch, amt = ci[keep], day[keep], merch[keep], amt[keep]
        self.add(ci, day, merch, np.maximum(amt, 0.5))

    def monthly_stream(self, mask: np.ndarray, merch_per_cust: np.ndarray, amount_cm: np.ndarray,
                       tg: TimeGrid, credit=False, day_of_month=None):
        """One transaction per active customer-month (direct debits, salaries)."""
        rng = self.rng
        ci, mi = np.nonzero(mask)
        dom = rng.integers(1, 28, self.n) if day_of_month is None else day_of_month
        day = tg.month_start[mi] + np.minimum(dom[ci], tg.month_len[mi]) - 1
        var = rng.integers(0, self.K, self.n)[ci]  # a customer's DD reads the same each month
        self.add(ci, day, merch_per_cust[ci], amount_cm[ci, mi], credit=credit, variant=var)

    def frame(self) -> dict[str, np.ndarray]:
        cols = list(zip(*self.parts, strict=True))
        return dict(zip(("ci", "day", "merch", "variant", "amount", "credit"),
                        (np.concatenate(c) for c in cols), strict=True))


def _transactions(cfg, p, adopt, rng, tg, cat: MerchantCatalogue, ev_conflict) -> dict[str, np.ndarray]:
    n = len(p["join_day"])
    shift = cfg.merchant_shift
    tb = _TxnBuilder(cat, shift, rng, n)
    M = tg.M
    ones = np.ones((n, M))
    w = p["wealth"]

    # FUEL: partial capture (some fuel bought on other cards), stops after EV adoption.
    capture = np.where(rng.random(n) < cfg.missingness["fuel_capture_zero"], 0.0, rng.beta(8, 2, n))
    fill = np.clip(26 + 0.22 * p["fuel_spend"], 28, 110)
    rate = (p["fuel_spend"] * capture / fill)[:, None] * np.exp(rng.normal(0, 0.15, (n, M)))
    occasional = ~p["has_car"] & (rng.random(n) < 0.05)
    rate = rate + (occasional * 0.25)[:, None]
    ev_day = adopt["EV_FINANCE"]

    def fuel_keep(ci, day):
        after = day > ev_day[ci] + 5
        keeps = (ev_conflict[ci] == 2) & (rng.random(len(ci)) < 0.75)
        return ~after | keeps

    tb.card_stream("FUEL", rate, np.where(occasional, 35.0, fill), 0.22, tg, loyalty=0.6, keep_fn=fuel_keep)

    # Energy direct debits from true usage.
    elec_m, gas_m = _energy_monthly(p, adopt, tg)
    q = (tg.year - 2025) * 4 + (tg.month - 1) // 3
    tariff = np.array([1.0, 0.98, 0.95, 0.97, 1.02, 0.99, 1.03, 1.04])[np.clip(q, 0, 7)]
    # DD amounts are smoothed (annual estimate) and re-set every 6 months
    half = np.arange(M) // 6
    elec_sm = np.stack([elec_m[:, half == h].mean(axis=1) for h in half], axis=1)
    gas_sm = np.stack([gas_m[:, half == h].mean(axis=1) for h in half], axis=1)
    e_cost = np.round(elec_sm * 0.245 * tariff + 16.0)
    g_cost = np.round(gas_sm * 0.063 * tariff + 9.0)
    supply = np.where(rng.random(n) < 0.10, 3,  # pays energy elsewhere / in rent
                      np.where(~p["has_gas"], 2, np.where(rng.random(n) < 0.45, 1, 0)))
    active = (tg.month_start[None, :] + tg.month_len[None, :] > p["join_day"][:, None] + 10)
    elec_sup = tb.pick("ELECTRICITY", ("dd",), n)
    gas_sup = tb.pick("GAS", ("dd",), n)
    dual_idx, dual_w = tb.weights("UTILITIES", ("dd",))
    dual_mask = np.char.find(cat.table.loc[dual_idx, "brand"].to_numpy().astype(str), "WATER") < 0
    dual_mask &= ~cat.table.loc[dual_idx, "brand"].isin(["UNITED UTILITIES"]).to_numpy()
    d_i, d_w = dual_idx[dual_mask], dual_w[dual_mask] / dual_w[dual_mask].sum()
    w_i, w_w = dual_idx[~dual_mask], dual_w[~dual_mask] / dual_w[~dual_mask].sum()
    dual_sup = d_i[rng.choice(len(d_i), size=n, p=d_w)]
    water_sup = w_i[rng.choice(len(w_i), size=n, p=w_w)]
    tb.monthly_stream(active & np.isin(supply, [0, 2])[:, None], elec_sup, e_cost, tg)
    tb.monthly_stream(active & (supply == 0)[:, None], gas_sup, g_cost, tg)
    tb.monthly_stream(active & (supply == 1)[:, None], dual_sup, e_cost + g_cost, tg)
    water = rng.random(n) < np.where(p["owner"], 0.92, 0.6)
    water_amt = np.round(np.exp(rng.normal(np.log(38), 0.25, n)))[:, None] * ones
    tb.monthly_stream(active & water[:, None], water_sup, water_amt, tg)

    # PUBLIC_TRANSPORT
    pt_rate = np.exp(rng.normal(-0.4 + 1.3 * ~p["has_car"] + 1.1 * p["london"] - 0.2 * w, 0.8, n))
    pt_rate = np.where(rng.random(n) < 0.25, 0.0, pt_rate)
    tb.card_stream("PUBLIC_TRANSPORT", pt_rate[:, None] * ones, np.exp(rng.normal(np.log(9), 0.4, n)),
                   0.9, tg, loyalty=0.55)

    # HOME_IMPROVEMENT: intent-driven, owners far more active; project bursts.
    hz = _z(p["hi"])
    burst = np.where(rng.random((n, M)) < 0.08 * np.exp(0.6 * hz)[:, None], 3.0, 1.0)
    hi_rate = 0.30 * np.exp(0.85 * hz) * np.where(p["owner"], 1.0, 0.35)
    tb.card_stream("HOME_IMPROVEMENT", hi_rate[:, None] * burst,
                   np.exp(np.log(40) + 0.3 * hz + 0.2 * w), 0.9, tg, loyalty=0.5)

    # AUTOMOTIVE: card (servicing, tyres, parking) + DD (vehicle tax, breakdown)
    auto_rate = np.where(p["has_car"], 0.55 * np.exp(rng.normal(0, 0.5, n)), 0.03)
    tb.card_stream("AUTOMOTIVE", auto_rate[:, None] * ones,
                   np.exp(rng.normal(np.log(30) + 0.05 * _z(np.nan_to_num(p["vage"])), 0.3, n)),
                   1.0, tg, loyalty=0.4)
    auto_dd = p["has_car"] & (rng.random(n) < 0.55)
    tb.monthly_stream(active & auto_dd[:, None], tb.pick("AUTOMOTIVE", ("dd",), n),
                      np.round(np.exp(rng.normal(np.log(14), 0.3, n)))[:, None] * ones, tg)

    # OTHER: everyday card spend, subscriptions, salary credits, rare adversarial text.
    oth_rate = np.exp(rng.normal(np.log(2.6) + 0.15 * w, 0.4, n))
    tb.card_stream("OTHER", oth_rate[:, None] * ones, np.exp(np.log(24) + 0.25 * w), 0.9, tg, loyalty=0.3)
    for _ in range(2):
        has_sub = rng.random(n) < 0.6
        tb.monthly_stream(active & has_sub[:, None], tb.pick("OTHER", ("dd",), n),
                          np.round(np.exp(rng.normal(np.log(22), 0.6, n)), 2)[:, None] * ones, tg)
    salaried = rng.random(n) < 0.92
    salary = np.round(np.exp(np.log(2300) + 0.45 * w + rng.normal(0, 0.15, n)), -1)
    tb.monthly_stream(active & salaried[:, None], tb.pick("OTHER", ("credit",), n),
                      salary[:, None] * np.exp(rng.normal(0, 0.03, (n, M))), tg, credit=True,
                      day_of_month=rng.integers(20, 29, n))
    adv_idx = cat.table.index[cat.table["kind"] == "adv"].to_numpy()
    n_adv = rng.binomial(int(n * M * oth_rate.mean()), float(shift["adversarial_rate"]))
    if n_adv and len(adv_idx):
        ci = rng.integers(0, n, n_adv)
        mi = rng.integers(0, M, n_adv)
        day = tg.month_start[mi] + (rng.random(n_adv) * tg.month_len[mi]).astype(np.int64)
        tb.add(ci, day, adv_idx[rng.integers(0, len(adv_idx), n_adv)], np.exp(rng.normal(np.log(15), 0.8, n_adv)))

    t = tb.frame()
    keep = (t["day"] >= p["join_day"][t["ci"]]) & (t["day"] >= tg.start_day) & (t["day"] <= tg.end_day)
    return {k: v[keep] for k, v in t.items()}


# ------------------------------------------------------------------------------------------------
# Assembly
# ------------------------------------------------------------------------------------------------

def _catalogue_table() -> pd.DataFrame:
    rows = []
    specs = {
        Product.EV_FINANCE: ("EV Finance", "Transport", "Finance the purchase of a new or used battery electric vehicle",
                             "Vehicle and affordability checks performed by the lending process", "tCO2e avoided per year (fuel vs. grid electricity)"),
        Product.GREEN_HOME: ("Green Home Improvement Loan", "Home", "Fund insulation, glazing, heat pumps or other efficiency upgrades",
                             "Homeowner; improvement plan; lending assessment", "kWh saved per year / tCO2e avoided"),
        Product.SOLAR_FINANCE: ("Solar Panel Finance", "Home energy", "Finance rooftop solar PV installation",
                                "Homeowner with suitable roof; installer quote; lending assessment", "kWh generated per year / tCO2e avoided"),
        Product.PAPERLESS_BANKING: ("Paperless Banking", "Digital", "Switch statements and letters to digital delivery",
                                    "Any customer with digital banking access", "Paper statements avoided (no carbon claim)"),
    }
    for product, (name, category, use, elig, metric) in specs.items():
        rows.append({"product_id": PRODUCT_IDS[product], "product": name, "category": category,
                     "intended_use_case": use, "eligibility_reference": elig, "sustainability_metric": metric})
    return pd.DataFrame(rows)


def _finalise_transactions(t: dict[str, np.ndarray], ids: np.ndarray, cat: MerchantCatalogue,
                           extra: pd.DataFrame | None) -> tuple[pd.DataFrame, pd.DataFrame]:
    order = np.lexsort((t["merch"], t["ci"], t["day"]))
    t = {k: v[order] for k, v in t.items()}
    mt = cat.table
    df = pd.DataFrame({
        "customer_id": ids[t["ci"]],
        "date": _to_dt(t["day"]),
        "merchant_description": cat.variants[t["merch"], t["variant"]],
        "amount": t["amount"],
        "debit_credit": np.where(t["credit"], "CREDIT", "DEBIT").astype(object),
        "merchant_id": mt["merchant_id"].to_numpy()[t["merch"]],
        "true_category": mt["true_category"].to_numpy()[t["merch"]],
    })
    if extra is not None and len(extra):
        df = pd.concat([df, extra[df.columns]], ignore_index=True)
        df = df.sort_values(["date", "customer_id", "merchant_id"], kind="stable", ignore_index=True)
    df["transaction_id"] = [f"T{i:09d}" for i in range(1, len(df) + 1)]
    txns = df[["transaction_id", "customer_id", "date", "merchant_description", "amount", "debit_credit"]]
    truth = df[["transaction_id", "merchant_id", "true_category"]]
    return txns.reset_index(drop=True), truth.reset_index(drop=True)


def _ensure_dtypes(tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    out = {}
    for name, df in tables.items():
        schema = ALL_TABLES[name]
        df = df[list(schema.columns)].copy()
        for col, kind in schema.columns.items():
            if kind == "date":
                df[col] = pd.to_datetime(df[col]).astype("datetime64[ns]")
            elif kind == "float":
                df[col] = df[col].astype(float)
            elif kind == "int":
                if df[col].isna().any() or col in schema.nullable:
                    df[col] = df[col].astype("Int64")
                else:
                    df[col] = df[col].astype(np.int64)
            elif kind == "bool":
                if col in schema.nullable:
                    df[col] = df[col].astype("boolean")
                else:
                    df[col] = df[col].astype(bool)
            else:  # str / category
                df[col] = df[col].astype("string")
        out[name] = df.reset_index(drop=True)
    return out


def generate(cfg: GeneratorConfig, verbose: bool = False) -> dict[str, pd.DataFrame]:
    """Generate every table in ``schemas.ALL_TABLES`` for one generator configuration."""
    t0 = time.time()
    names = ("population", "adoption", "customers", "products", "vehicles", "energy", "digital",
             "transactions", "conflict", "personas")
    rngs = dict(zip(names, (np.random.default_rng(s) for s in np.random.SeedSequence(cfg.seed).spawn(len(names))),
                    strict=True))
    tg = TimeGrid(cfg)
    shift = cfg.merchant_shift
    cat = build_catalogue(cfg.seed, shift["variants_per_merchant"], shift["description_noise"])
    p = _population(cfg, rngs["population"], tg)
    traits = _traits(p)
    adopt = _simulate_adoption(cfg, p, traits, rngs["adoption"], tg)
    n = len(p["join_day"])
    # EV adopters with deliberately inconsistent records: 1 = stale ICE record, 2 = keeps buying fuel
    rc = rngs["conflict"]
    is_conf = (adopt["EV_FINANCE"] < NONE_DAY) & (rc.random(n) < cfg.stale_ev_conflict_rate)
    ev_conflict = np.where(is_conf, np.where(rc.random(n) < 0.5, 1, 2), 0)
    if verbose:
        print(f"  population + adoption: {time.time() - t0:.1f}s")

    customers = _customers(cfg, p, adopt, rngs["customers"], tg)
    tables: dict[str, pd.DataFrame] = {
        "customers": customers,
        "financial_products": _financial_products(cfg, p, adopt, rngs["products"], tg, customers["home_owner"]),
        "vehicles": _vehicles(cfg, p, adopt, rngs["vehicles"], tg, ev_conflict),
        "energy_usage": _energy_usage(cfg, p, adopt, rngs["energy"], tg),
        "digital_usage": _digital_usage(cfg, p, adopt, rngs["digital"], tg),
        "green_product_catalogue": _catalogue_table(),
    }
    outcome_rows = [pd.DataFrame({"customer_id": p["customer_id"][adopt[prod] < NONE_DAY], "product": prod,
                                  "adoption_date": _to_dt(adopt[prod][adopt[prod] < NONE_DAY])})
                    for prod in PRODUCTS]
    tables["customer_outcomes"] = pd.concat(outcome_rows, ignore_index=True)
    if verbose:
        print(f"  non-transaction tables: {time.time() - t0:.1f}s")

    t = _transactions(cfg, p, adopt, rngs["transactions"], tg, cat, ev_conflict)
    if verbose:
        print(f"  transactions simulated ({len(t['ci'])} rows): {time.time() - t0:.1f}s")

    persona_txns = None
    if cfg.include_personas:
        from greenpath.data_generation.personas import build_personas
        ptables = build_personas(cat, rngs["personas"], tg)
        persona_txns = ptables.pop("transactions")
        for name, df in ptables.items():
            tables[name] = pd.concat([df, tables[name]], ignore_index=True)

    txns, truth = _finalise_transactions(t, p["customer_id"], cat, persona_txns)
    tables["transactions"] = txns
    tables["transaction_truth"] = truth
    tables["merchants"] = cat.table.drop(columns=["kind"])
    tables["customers"] = tables["customers"].sort_values("customer_id", ignore_index=True)
    availability_rng = np.random.default_rng(np.random.SeedSequence([cfg.seed, 917]))
    for name in ("customers", "transactions", "financial_products", "vehicles", "energy_usage", "digital_usage"):
        schema = ALL_TABLES[name]
        event = tables[name][schema.event_time_column or "record_updated_at"]
        monthly = name in {"energy_usage", "digital_usage"}
        completed = event + pd.offsets.MonthEnd(0) if monthly else event
        # Explicitly synthetic ingestion delays, never represented as public-source observations.
        delay = availability_rng.integers(1 if monthly else 0, 15 if monthly else 8, len(event))
        tables[name]["available_at"] = completed + pd.to_timedelta(delay, unit="D")
    tables = _ensure_dtypes(tables)
    for name, df in tables.items():
        validate_table(df, ALL_TABLES[name])
    if verbose:
        print(f"  finalised + validated: {time.time() - t0:.1f}s")
    return tables


def _file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_dataset(tables: dict[str, pd.DataFrame], out_dir: Path, cfg: GeneratorConfig) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    shas = {}
    for name in ALL_TABLES:
        path = out_dir / f"{name}.parquet"
        tables[name].to_parquet(path, index=False)
        shas[path.name] = _file_sha(path)
    meta = {"config": cfg.to_dict(), "config_hash": cfg.config_hash(), "file_sha256": shas,
            "row_counts": {n: int(len(tables[n])) for n in ALL_TABLES},
            "public_anchors": anchor_manifest(tables["energy_usage"])}
    (out_dir / "generator_config.json").write_text(json.dumps(meta, indent=2, sort_keys=True))
    return meta
