"""CustomerSnapshot provider backed by Customer 360 frames (implements ports.CustomerSnapshotProvider)."""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from greenpath import config
from greenpath.contracts import (
    CustomerSnapshot,
    DataQualityEvidence,
    DigitalFacts,
    EnergyFacts,
    FuelType,
    HeatingType,
    HomeFacts,
    SpendFacts,
    VehicleFacts,
)
from greenpath.pipelines.feature_registry import POPULATION_FLAGS, PROPENSITY_FEATURES

__all__ = ["Customer360SnapshotProvider", "customer360_path", "row_to_snapshot"]

_FILE_RE = re.compile(r"customer360_(\d{4}-\d{2}-\d{2})\.parquet$")


def customer360_path(cutoff: date, directory: Path | str | None = None) -> Path:
    return Path(directory or config.PROCESSED_DIR) / f"customer360_{cutoff.isoformat()}.parquet"


# --- scalar helpers -------------------------------------------------------------------------

def _is_null(v: Any) -> bool:
    if v is None or v is pd.NaT:
        return True
    try:
        return bool(pd.isna(v))
    except (TypeError, ValueError):
        return False


def _f(v: Any) -> float | None:
    return None if _is_null(v) else float(v)


def _i(v: Any) -> int | None:
    return None if _is_null(v) else int(round(float(v)))


def _b(v: Any) -> bool | None:
    return None if _is_null(v) else bool(v)


def _s(v: Any) -> str | None:
    return None if _is_null(v) else str(v)


def _d(v: Any) -> date | None:
    if _is_null(v):
        return None
    return v.date() if isinstance(v, (pd.Timestamp, datetime)) else v


def _enum(cls, v: Any):
    return None if _is_null(v) else cls(str(v))


def _nonneg(v: float | None) -> float | None:
    return None if v is None else max(v, 0.0)


def _names(v: Any) -> list[str]:
    if isinstance(v, (list, tuple, np.ndarray)):
        return [str(x) for x in v]
    return []


# --- conversion -----------------------------------------------------------------------------

def _snapshot_from_mapping(customer_id: str, r: Mapping[str, Any], cutoff: date,
                           generated_at: datetime) -> CustomerSnapshot:
    g = r.get
    txn_months = _i(g("txn_months_observed")) or 0
    energy_months = min(max(_i(g("energy_months_present")) or 0, 0), 12)
    digital_months = min(max(_i(g("digital_months_present")) or 0, 0), 12)

    def avg(name: str) -> float | None:
        return _nonneg(_f(g(name)))

    util_90 = [_f(g(f"{c}_spend_90d_avg")) for c in ("electricity", "gas", "utilities")]
    util_12 = [_f(g(f"{c}_spend_12m_avg")) for c in ("electricity", "gas", "utilities")]
    utility_trend = None
    if all(x is not None for x in util_90 + util_12) and sum(util_12) > 0:
        utility_trend = sum(util_90) / sum(util_12) - 1.0
    home_impr_12m_avg = _f(g("home_improvement_spend_12m_avg"))

    ratio = _f(g("digital_statement_ratio"))
    features = {name: _f(g(name)) for name in (*PROPENSITY_FEATURES, *POPULATION_FLAGS)}

    return CustomerSnapshot(
        customer_id=str(customer_id),
        feature_cutoff=cutoff,
        generated_at=generated_at,
        feature_version=config.FEATURE_VERSION,
        segment=_s(g("segment")),
        vehicle=VehicleFacts(
            has_vehicle=_b(g("has_vehicle")),
            fuel_type=_enum(FuelType, g("fuel_type")),
            vehicle_age_years=_nonneg(_f(g("vehicle_age_years"))),
            annual_mileage_km=_nonneg(_f(g("annual_mileage_km"))),
            mileage_is_estimated=bool(_b(g("mileage_is_estimated"))),
            record_updated_at=_d(g("vehicle_record_updated_at")),
            has_vehicle_finance=_b(g("has_vehicle_finance")),
            state_effective_at=_d(g("vehicle_state_effective_at")),
        ),
        home=HomeFacts(
            home_owner=_b(g("home_owner")),
            has_mortgage=_b(g("has_mortgage")),
            mortgage_tenure_months=_i(g("mortgage_tenure_months")),
            has_existing_solar=_b(g("has_existing_solar")),
            heating_type=_enum(HeatingType, g("heating_type")),
            property_type=_s(g("property_type")),
            region=_s(g("region")),
        ),
        energy=EnergyFacts(
            electricity_kwh_12m=_nonneg(_f(g("electricity_kwh_12m"))),
            gas_kwh_12m=_nonneg(_f(g("gas_kwh_12m"))),
            energy_months_present=energy_months,
            electricity_trend=_f(g("electricity_trend")),
            electricity_months_present=_i(g("electricity_months_present")),
            gas_months_present=_i(g("gas_months_present")),
            electricity_kwh_observed=_f(g("electricity_kwh_observed")),
            gas_kwh_observed=_f(g("gas_kwh_observed")),
            electricity_annualisation_factor=_f(g("electricity_annualisation_factor")),
            gas_annualisation_factor=_f(g("gas_annualisation_factor")),
            electricity_is_estimated=_b(g("electricity_is_estimated")),
            gas_is_estimated=_b(g("gas_is_estimated")),
        ),
        digital=DigitalFacts(
            is_paperless=_b(g("is_paperless")),
            paper_statements_3m=_i(g("paper_statements_3m")),
            paper_statements_12m=_i(g("paper_statements_12m")),
            digital_statement_ratio=None if ratio is None else min(max(ratio, 0.0), 1.0),
            digital_transactions_3m_avg=_nonneg(_f(g("digital_txn_3m_avg"))),
            branch_visits_3m=_i(g("branch_visits_3m")),
            paperless_effective_at=_d(g("paperless_effective_at")),
            paper_statements_post_paperless_3m=_i(g("paper_statements_post_paperless_3m")),
        ),
        spend=SpendFacts(
            fuel_spend_90d_monthly_avg=avg("fuel_spend_90d_avg"),
            fuel_txn_frequency_90d=_i(g("fuel_txn_freq_90d")),
            electricity_spend_90d_monthly_avg=avg("electricity_spend_90d_avg"),
            gas_spend_90d_monthly_avg=avg("gas_spend_90d_avg"),
            utilities_spend_90d_monthly_avg=avg("utilities_spend_90d_avg"),
            home_improvement_spend_12m=None if home_impr_12m_avg is None else max(home_impr_12m_avg * 12.0, 0.0),
            utility_spend_trend=utility_trend,
            fuel_txn_count_post_vehicle_state_90d=_i(g("fuel_txn_count_post_vehicle_state_90d")),
            fuel_spend_post_vehicle_state_90d=_f(g("fuel_spend_post_vehicle_state_90d")),
        ),
        features=features,
        data_quality=DataQualityEvidence(
            transaction_months_observed=txn_months,
            first_transaction_date=_d(g("first_txn_date")),
            last_transaction_date=_d(g("last_txn_date")),
            vehicle_record_age_days=_i(g("vehicle_record_age_days")),
            energy_months_present=energy_months,
            digital_months_present=digital_months,
            missing_fields=_names(g("missing_fields")),
            estimated_fields=_names(g("estimated_fields")),
            invalid_product_records=_i(g("invalid_product_records")) or 0,
        ),
    )


def row_to_snapshot(row: pd.Series | Mapping[str, Any], cutoff: date,
                    generated_at: datetime = config.PREDICTION_TIMESTAMP) -> CustomerSnapshot:
    """Map one Customer 360 row (index = customer_id, i.e. ``row.name``) to a CustomerSnapshot."""
    if isinstance(row, pd.Series):
        customer_id = row.name if row.name is not None else row.get("customer_id")
        mapping: Mapping[str, Any] = row.to_dict()
    else:
        mapping = row
        customer_id = row.get("customer_id")
    if customer_id is None:
        raise ValueError("row has no customer_id (use the frame index as Series.name)")
    return _snapshot_from_mapping(str(customer_id), mapping, cutoff, generated_at)


# --- provider -------------------------------------------------------------------------------

class Customer360SnapshotProvider:
    """Serves snapshots from precomputed Customer 360 frames keyed by feature cutoff."""

    def __init__(self, frames: Mapping[date, pd.DataFrame], default_cutoff: date = config.FEATURE_CUTOFF,
                 generated_at: datetime = config.PREDICTION_TIMESTAMP):
        if not frames:
            raise ValueError("at least one Customer 360 frame is required")
        self.frames: dict[date, pd.DataFrame] = dict(frames)
        self.default_cutoff = default_cutoff
        self.generated_at = generated_at
        if default_cutoff not in self.frames:
            raise ValueError(f"no frame for default cutoff {default_cutoff}; have {sorted(self.frames)}")

    def _frame(self, cutoff: date | None) -> tuple[date, pd.DataFrame]:
        c = self.default_cutoff if cutoff is None else (cutoff.date() if isinstance(cutoff, datetime) else cutoff)
        if c not in self.frames:
            raise KeyError(f"no Customer 360 frame loaded for cutoff {c}; have {sorted(self.frames)}")
        return c, self.frames[c]

    @property
    def cutoffs(self) -> list[date]:
        return sorted(self.frames)

    def list_customer_ids(self) -> list[str]:
        return [str(i) for i in self.frames[self.default_cutoff].index]

    def get_snapshot(self, customer_id: str, cutoff: date | None = None) -> CustomerSnapshot | None:
        c, frame = self._frame(cutoff)
        if customer_id not in frame.index:
            return None
        rec = frame.loc[[customer_id]].to_dict("records")[0]
        return _snapshot_from_mapping(customer_id, rec, c, self.generated_at)

    def snapshots(self, cutoff: date | None = None) -> list[CustomerSnapshot]:
        """All snapshots at ``cutoff`` (default cutoff if omitted), in frame order."""
        c, frame = self._frame(cutoff)
        return [_snapshot_from_mapping(str(cid), rec, c, self.generated_at)
                for cid, rec in frame.to_dict("index").items()]

    # persistence
    def save(self, directory: Path | str | None = None) -> list[Path]:
        paths = []
        for c, frame in self.frames.items():
            p = customer360_path(c, directory)
            p.parent.mkdir(parents=True, exist_ok=True)
            frame.to_parquet(p)
            paths.append(p)
        return paths

    @classmethod
    def from_parquet(cls, *paths: Path | str, default_cutoff: date = config.FEATURE_CUTOFF,
                     generated_at: datetime = config.PREDICTION_TIMESTAMP) -> Customer360SnapshotProvider:
        frames: dict[date, pd.DataFrame] = {}
        for p in map(Path, paths):
            m = _FILE_RE.search(p.name)
            if not m:
                raise ValueError(f"cannot infer cutoff from file name {p.name!r} (customer360_<YYYY-MM-DD>.parquet)")
            frames[date.fromisoformat(m.group(1))] = pd.read_parquet(p)
        return cls(frames, default_cutoff=default_cutoff, generated_at=generated_at)
