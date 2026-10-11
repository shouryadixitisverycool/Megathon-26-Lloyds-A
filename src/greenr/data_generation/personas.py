"""Deterministic demo personas C10001..C10010 (spec 58).

Each persona is written explicitly (no latent model) so the demo shows the same story every run:

C10001 EV candidate        petrol, ~15,200 km/yr, ~£310/month fuel, 9-year-old car, vehicle finance
C10002 Solar candidate     homeowner + mortgage, ~5,200 kWh/yr, no solar, South West
C10003 Paperless candidate paper statements, very high digital engagement
C10004 Conflict            EV record updated 2025-09 but recurring high fuel spend
C10005 Insufficient data   joined 2026-05, ~2 months of transactions, ownership unknown, nothing else
C10006 Already green       EV + EV finance, solar + solar finance, green home loan, paperless, no fuel
C10007 Multi-opportunity   high mileage petrol, homeowner, high electricity, renovating, paper statements
C10008 Changed circumstances paper statements until April 2026, goes paperless in May 2026
C10009 OOD / noisy         ~95,000 km van, ~£2,400/month fuel, 40,000 kWh, 30 branch visits/month
C10010 Sensitivity example petrol ~15,200 km, moderate fuel spend

Regular generated customers use IDs ``C2xxxxx`` so persona IDs never collide.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

import numpy as np
import pandas as pd

from greenr.data_generation.merchants import MerchantCatalogue
from greenr.data_generation.source_history import customer_history

D = date.fromisoformat


@dataclass
class Persona:
    customer_id: str
    since: str
    region: str | None
    postcode: str | None
    age_band: str
    income_band: str
    segment: str
    home_owner: bool | None
    property_type: str | None
    heating_type: str | None
    has_solar_pv: bool | None
    solar_installed_at: str | None
    pref: int | None
    products: list[tuple] = field(default_factory=list)  # (product, start, end, balance, status)
    vehicles: list[tuple] = field(default_factory=list)  # (type, fuel, age, mileage, source, date)
    energy: tuple | None = None  # (elec kWh/yr, gas kWh/yr, source_quality)
    digital: dict | None = None  # logins, dtx, branch, paper, paperless_from ("always"|date|None)
    fuel: tuple | None = None  # (brands, every_days, amount, until)
    elec_dd: tuple | None = None  # (brand, amount)
    gas_dd: tuple | None = None
    dual_dd: tuple | None = None
    water: tuple | None = ("THAMES WATER", 38.0)
    pt: tuple | None = None  # (brands, per_month, amount)
    hi: tuple | None = None  # (brands, per_month, amount)
    auto: tuple | None = (("HALFORDS", "KWIK FIT", "RINGGO PARKING"), 0.6, 35.0)
    other: tuple = (6.0, 28.0)  # per month, amount
    salary: tuple | None = ("ACME LTD SALARY", 2600.0)
    outcomes: list[tuple] = field(default_factory=list)  # (product, date)
    txn_start: str | None = None


def persona_specs() -> list[Persona]:
    return [
        Persona(
            "C10001", "2018-03-12", "South East", "RG4 7", "35-44", "50-75k", "MASS_AFFLUENT",
            True, "SEMI_DETACHED", "GAS_BOILER", False, None, 4,
            products=[("MORTGAGE", "2018-06-30", None, 182_000.0, "ACTIVE"),
                      ("VEHICLE_FINANCE", "2022-09-01", None, 6_400.0, "ACTIVE")],
            vehicles=[("CAR", "PETROL", 5.9, 14_800.0, "OBSERVED", "2023-04-02"),
                      ("CAR", "PETROL", 8.9, 15_200.0, "OBSERVED", "2026-05-15")],
            energy=(3_600.0, 11_800.0, "SMART_METER"),
            digital=dict(logins=14, dtx=42, branch=0.0, paper=1, paperless_from=None),
            fuel=(("SHELL", "TESCO PFS"), 10, 103.0, None),
            elec_dd=("OCTOPUS ENERGY ELEC", 95.0), gas_dd=("BRITISH GAS", 70.0),
            pt=(("TRAINLINE", "SOUTHERN RAIL"), 2.0, 11.0), hi=(("B&Q", "SCREWFIX"), 0.25, 107.0),
            salary=("ACME LTD SALARY", 3_400.0),
        ),
        Persona(
            "C10002", "2015-09-01", "South West", "EX2 4", "45-54", "75-100k", "MASS_AFFLUENT",
            True, "DETACHED", "GAS_BOILER", False, None, 4,
            products=[("MORTGAGE", "2016-02-01", None, 210_000.0, "ACTIVE"),
                      ("INVESTMENT", "2019-04-01", None, 26_000.0, "ACTIVE")],
            vehicles=[("CAR", "HYBRID", 3.0, 7_000.0, "OBSERVED", "2025-11-03")],
            energy=(5_200.0, 13_000.0, "SMART_METER"),
            digital=dict(logins=20, dtx=50, branch=0.2, paper=0, paperless_from="always"),
            fuel=(("BP",), 30, 48.0, None),
            elec_dd=("EDF ENERGY ELEC", 128.0), gas_dd=("EDF ENERGY GAS", 76.0),
            water=("SOUTH WEST WATER", 46.0),
            hi=(("WICKES", "TOOLSTATION"), 0.5, 85.0), salary=("NHS PAYROLL", 4_100.0),
        ),
        Persona(
            "C10003", "2020-01-15", "London", "E14 3", "25-34", "25-50k", "MASS",
            False, "FLAT", "ELECTRIC", False, None, 3,
            products=[],
            energy=(4_100.0, 0.0, "SMART_METER"),
            digital=dict(logins=46, dtx=88, branch=0.0, paper=1, paperless_from=None),
            elec_dd=("OCTOPUS ENERGY ELEC", 105.0), water=None,
            pt=(("TFL TRAVEL",), 22.0, 3.4), auto=None, other=(9.0, 21.0),
            salary=("NORTHWIND LOGISTICS PAY", 2_350.0),
        ),
        Persona(
            "C10004", "2012-05-20", "North West", "M20 2", "45-54", "50-75k", "MASS_AFFLUENT",
            True, "SEMI_DETACHED", "GAS_BOILER", False, None, 3,
            products=[("MORTGAGE", "2013-01-10", None, 140_000.0, "ACTIVE")],
            vehicles=[("CAR", "PETROL", 6.0, 16_000.0, "OBSERVED", "2023-02-10"),
                      ("CAR", "EV", 0.5, 16_000.0, "OBSERVED", "2025-09-14")],
            energy=(3_300.0, 12_500.0, "SMART_METER"),
            digital=dict(logins=10, dtx=35, branch=0.3, paper=1, paperless_from=None),
            fuel=(("ESSO", "SHELL"), 8, 70.0, None),
            dual_dd=("OVO ENERGY", 165.0), water=("UNITED UTILITIES", 41.0),
            salary=("ACME LTD SALARY", 3_000.0),
        ),
        Persona(
            "C10005", "2026-05-01", "East Midlands", "NG7 1", "25-34", "25-50k", "MASS",
            None, None, None, None, None, None,
            products=[], vehicles=[], energy=None,
            digital=dict(logins=8, dtx=20, branch=0.5, paper=1, paperless_from=None),
            water=None, auto=None, other=(7.0, 24.0), salary=("ACME LTD SALARY", 2_100.0),
        ),
        Persona(
            "C10006", "2010-04-01", "South East", "GU1 3", "45-54", "100k+", "AFFLUENT",
            True, "DETACHED", "HEAT_PUMP", True, "2022-06-15", 5,
            products=[("MORTGAGE", "2011-01-01", None, 240_000.0, "ACTIVE"),
                      ("SOLAR_FINANCE", "2022-06-01", None, 5_200.0, "ACTIVE"),
                      ("EV_FINANCE", "2023-03-01", None, 19_500.0, "ACTIVE"),
                      ("GREEN_HOME_LOAN", "2024-02-01", None, 11_000.0, "ACTIVE"),
                      ("INVESTMENT", "2015-05-01", None, 85_000.0, "ACTIVE")],
            vehicles=[("CAR", "EV", 1.0, 12_000.0, "OBSERVED", "2024-03-10")],
            energy=(4_500.0, 0.0, "SMART_METER"),
            digital=dict(logins=30, dtx=60, branch=0.0, paper=0, paperless_from="always"),
            elec_dd=("GOOD ENERGY", 110.0), pt=(("TRAINLINE",), 1.0, 45.0),
            auto=(("HALFORDS AUTOCENTRE", "JUSTPARK"), 0.4, 40.0), salary=("ACME LTD SALARY", 7_800.0),
        ),
        Persona(
            "C10007", "2016-08-01", "East of England", "CB4 2", "35-44", "75-100k", "MASS_AFFLUENT",
            True, "SEMI_DETACHED", "GAS_BOILER", False, None, 5,
            products=[("MORTGAGE", "2016-10-01", None, 230_000.0, "ACTIVE")],
            vehicles=[("CAR", "PETROL", 9.3, 18_000.0, "OBSERVED", "2026-03-20")],
            energy=(4_800.0, 14_000.0, "SMART_METER"),
            digital=dict(logins=25, dtx=55, branch=0.1, paper=1, paperless_from=None),
            fuel=(("BP", "SAINSBURYS PETROL"), 9, 80.0, None),
            elec_dd=("SSE ELECTRICITY", 118.0), gas_dd=("SSE GAS SUPPLY", 84.0),
            water=("ANGLIAN WATER", 44.0),
            hi=(("B&Q", "WICKES", "SCREWFIX", "LOFT INSULATION SERVICES"), 2.5, 75.0),
            salary=("ACME LTD SALARY", 4_600.0),
        ),
        Persona(
            "C10008", "2019-02-11", "Yorkshire", "LS6 2", "25-34", "25-50k", "MASS",
            False, "TERRACED", "GAS_BOILER", False, None, 3,
            products=[],
            energy=(2_600.0, 9_500.0, "SMART_METER"),
            digital=dict(logins=24, dtx=60, branch=0.1, paper=1, paperless_from="2026-05-14"),
            dual_dd=("OCTOPUS ENERGY", 118.0), water=("YORKSHIRE WATER", 36.0),
            pt=(("NORTHERN RAIL TICKETS", "FIRST BUS"), 10.0, 6.0), auto=None,
            salary=("NORTHWIND LOGISTICS PAY", 2_250.0),
            outcomes=[("PAPERLESS_BANKING", "2026-05-14")],
        ),
        Persona(
            "C10009", "2014-01-01", "Scotland", "AB1 5", "55-64", "50-75k", "MASS_AFFLUENT",
            True, "DETACHED", "OIL", False, None, 2,
            products=[("VEHICLE_FINANCE", "2023-01-15", None, 21_000.0, "ACTIVE")],
            vehicles=[("VAN", "DIESEL", 4.0, 95_000.0, "OBSERVED", "2026-02-02")],
            energy=(40_000.0, 0.0, "ESTIMATED_BILL"),
            digital=dict(logins=0.5, dtx=4, branch=30.0, paper=3, paperless_from=None),
            fuel=(("SHELL", "BP", "ESSO", "MOTO SERVICES FUEL"), 2, 160.0, None),
            elec_dd=("SSE ELECTRICITY", 850.0), water=None,
            auto=(("HALFORDS", "NATIONAL TYRES", "EURO CAR PARTS"), 3.0, 90.0),
            other=(12.0, 35.0), salary=("ACME LTD SALARY", 5_200.0),
        ),
        Persona(
            "C10010", "2017-07-01", "West Midlands", "B15 2", "35-44", "50-75k", "MASS",
            True, "TERRACED", "GAS_BOILER", False, None, 3,
            products=[("MORTGAGE", "2017-09-01", None, 150_000.0, "ACTIVE")],
            vehicles=[("CAR", "PETROL", 4.6, 15_200.0, "OBSERVED", "2025-12-01")],
            energy=(3_000.0, 10_500.0, "SMART_METER"),
            digital=dict(logins=12, dtx=38, branch=0.3, paper=1, paperless_from=None),
            fuel=(("TESCO PFS", "ASDA PETROL"), 12, 60.0, None),
            elec_dd=("EON NEXT ELEC", 78.0), gas_dd=("EON NEXT GAS", 64.0),
            water=("SEVERN TRENT WATER", 37.0), salary=("ACME LTD SALARY", 2_900.0),
        ),
    ]


class _Txns:
    def __init__(self, cat: MerchantCatalogue, rng: np.random.Generator, end: date):
        self.cat, self.rng, self.end = cat, rng, end
        self.by_brand = {b: i for i, b in enumerate(cat.table["brand"])}
        self.rows: list[dict] = []

    def add(self, cid: str, day: date, brand: str, amount: float, credit=False, variant: int | None = None):
        if day > self.end:
            return
        i = self.by_brand[brand]
        k = int(self.rng.integers(0, self.cat.variants.shape[1])) if variant is None else variant
        self.rows.append({"customer_id": cid, "date": pd.Timestamp(day),
                          "merchant_description": self.cat.variants[i, k], "amount": round(float(amount), 2),
                          "debit_credit": "CREDIT" if credit else "DEBIT",
                          "merchant_id": self.cat.table["merchant_id"].iat[i],
                          "true_category": self.cat.table["true_category"].iat[i]})

    def every(self, cid, start: date, brands, every_days: float, amount: float, until: date | None = None):
        d = start + timedelta(days=int(self.rng.integers(0, max(int(every_days), 1))))
        stop = min(until or self.end, self.end)
        while d <= stop:
            self.add(cid, d, brands[int(self.rng.integers(0, len(brands)))],
                     amount * float(np.exp(self.rng.normal(0, 0.06))))
            d += timedelta(days=max(1, int(round(every_days + self.rng.normal(0, 1.0)))))

    def monthly(self, cid, start: date, brand: str, amount: float, dom: int, credit=False):
        k = int(self.rng.integers(0, self.cat.variants.shape[1]))
        for m in pd.date_range(pd.Timestamp(start).replace(day=1), pd.Timestamp(self.end), freq="MS"):
            day = m.date().replace(day=dom)
            if day >= start:
                self.add(cid, day, brand, amount, credit=credit, variant=k)

    def poisson(self, cid, start: date, brands, per_month: float, amount: float, sigma=0.6):
        for m in pd.date_range(pd.Timestamp(start).replace(day=1), pd.Timestamp(self.end), freq="MS"):
            for _ in range(int(self.rng.poisson(per_month))):
                day = m.date() + timedelta(days=int(self.rng.integers(0, 28)))
                if day >= start:
                    self.add(cid, day, brands[int(self.rng.integers(0, len(brands)))],
                             amount * float(np.exp(self.rng.normal(0, sigma) - sigma**2 / 2)))


_OTHER_BRANDS = ("TESCO STORES", "SAINSBURYS", "ALDI", "AMAZON MKTPLACE", "COSTA COFFEE", "GREGGS",
                 "BOOTS", "DELIVEROO", "CO-OP GROUP FOOD", "ARGOS")


def build_personas(cat: MerchantCatalogue, rng: np.random.Generator, tg) -> dict[str, pd.DataFrame]:
    end = pd.Timestamp(tg.end_day.astype("datetime64[D]")).date()
    hist_start = pd.Timestamp(tg.start_day.astype("datetime64[D]")).date()
    months = [pd.Timestamp(m).date() for m in tg.month_start.astype("datetime64[D]")]
    tx = _Txns(cat, rng, end)
    cust, prods, vehs, energy, digital, outcomes, ownership = [], [], [], [], [], [], []
    for ps in persona_specs():
        cid = ps.customer_id
        since = D(ps.since)
        upd = max(since + timedelta(days=10), D("2026-04-02"))
        cust.append({"customer_id": cid, "customer_since": pd.Timestamp(since), "age_band": ps.age_band,
                     "income_band": ps.income_band, "region": ps.region, "postcode_sector": ps.postcode,
                     "segment": ps.segment, "home_owner": ps.home_owner, "property_type": ps.property_type,
                     "heating_type": ps.heating_type, "has_solar_pv": ps.has_solar_pv,
                     "solar_installed_at": pd.Timestamp(ps.solar_installed_at) if ps.solar_installed_at else pd.NaT,
                     "sustainability_preference": ps.pref, "record_updated_at": pd.Timestamp(upd)})
        ownership.append({"customer_id": cid,
                          "has_vehicle": None if cid == "C10005" else bool(ps.vehicles),
                          "record_updated_at": pd.Timestamp(max(since, hist_start))})
        prods.append({"customer_id": cid, "product": "CURRENT_ACCOUNT", "start_date": pd.Timestamp(since),
                      "end_date": pd.NaT, "balance": 2_400.0, "status": "ACTIVE"})
        for product, start, stop, bal, status in ps.products:
            prods.append({"customer_id": cid, "product": product, "start_date": pd.Timestamp(start),
                          "end_date": pd.Timestamp(stop) if stop else pd.NaT, "balance": bal, "status": status})
        for vtype, fuel, age, mil, src, day in ps.vehicles:
            vehs.append({"customer_id": cid, "vehicle_type": vtype, "fuel_type": fuel, "vehicle_age": age,
                         "annual_mileage": mil, "mileage_source": src, "record_updated_at": pd.Timestamp(day)})
        for product, day in ps.outcomes:
            outcomes.append({"customer_id": cid, "product": product, "adoption_date": pd.Timestamp(day)})

        first_month = since.replace(day=1)
        if ps.energy is not None:
            elec, gas, quality = ps.energy
            for m in months:
                if m < first_month:
                    continue
                s_e = 1 + 0.18 * np.cos(2 * np.pi * (m.month - 1) / 12)
                s_g = 1 + 0.70 * np.cos(2 * np.pi * (m.month - 1) / 12)
                energy.append({"customer_id": cid, "month": pd.Timestamp(m),
                               "electricity_kwh": round(elec / 12 * s_e * float(np.exp(rng.normal(0, 0.03))), 1),
                               "gas_kwh": round(gas / 12 * s_g * float(np.exp(rng.normal(0, 0.03))), 1),
                               "source_quality": quality})
        if ps.digital is not None:
            dg = ps.digital
            pf = dg["paperless_from"]
            pf_month = None if pf in (None, "always") else D(pf).replace(day=1)
            for m in months:
                if m < first_month:
                    continue
                paperless = pf == "always" or (pf_month is not None and m >= pf_month)
                digital.append({"customer_id": cid, "month": pd.Timestamp(m), "digital_statements": paperless,
                                "paperless_effective_at": (pd.Timestamp(max(since, hist_start)) if pf == "always"
                                                          else pd.Timestamp(pf) if paperless else pd.NaT),
                                "paper_statements": 0 if paperless else int(dg["paper"]),
                                "digital_transactions": int(rng.poisson(dg["dtx"])),
                                "app_logins": int(rng.poisson(dg["logins"])),
                                "branch_visits": int(rng.poisson(dg["branch"]))})

        start = max(since, hist_start)
        if ps.fuel:
            brands, every, amount, until = ps.fuel
            tx.every(cid, start, brands, every, amount, D(until) if until else None)
        for dd, dom in ((ps.elec_dd, 3), (ps.gas_dd, 5), (ps.dual_dd, 4), (ps.water, 12)):
            if dd:
                tx.monthly(cid, start, dd[0], dd[1], dom)
        if ps.pt:
            tx.poisson(cid, start, ps.pt[0], ps.pt[1], ps.pt[2])
        if ps.hi:
            tx.poisson(cid, start, ps.hi[0], ps.hi[1], ps.hi[2], sigma=0.4)
        if ps.auto:
            tx.poisson(cid, start, ps.auto[0], ps.auto[1], ps.auto[2])
        tx.poisson(cid, start, _OTHER_BRANDS, ps.other[0], ps.other[1])
        tx.monthly(cid, start, "NETFLIX.COM", 10.99, 15)
        if ps.salary:
            tx.monthly(cid, start, ps.salary[0], ps.salary[1], 25, credit=True)

    customers, history = customer_history(pd.DataFrame(cust), np.full(len(cust), np.datetime64("NaT", "ns")),
                                         pd.Timestamp(hist_start))
    return {
        "customers": customers,
        "customer_history": history,
        "vehicle_ownership": pd.DataFrame(ownership),
        "financial_products": pd.DataFrame(prods),
        "vehicles": pd.DataFrame(vehs),
        "energy_usage": pd.DataFrame(energy),
        "digital_usage": pd.DataFrame(digital),
        "customer_outcomes": pd.DataFrame(outcomes, columns=["customer_id", "product", "adoption_date"]),
        "transactions": pd.DataFrame(tx.rows),
    }
