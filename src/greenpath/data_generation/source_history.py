"""Simulated source declarations, not verified customer or public-source observations."""

import numpy as np
import pandas as pd


def customer_history(baseline: pd.DataFrame, solar_dates: np.ndarray,
                     history_start: pd.Timestamp) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Keep the initial observed profile (including unknowns) and effective-dated updates."""
    initial = baseline.copy()
    initial["record_updated_at"] = initial["customer_since"].clip(lower=history_start)
    refresh = baseline.copy()
    solar_dates = pd.Series(pd.to_datetime(solar_dates), index=baseline.index)
    changed = solar_dates.notna()
    already_changed = changed & (solar_dates <= refresh["record_updated_at"])
    refresh.loc[already_changed, "has_solar_pv"] = True
    refresh.loc[already_changed, "solar_installed_at"] = solar_dates[already_changed]
    solar = baseline.loc[changed].copy()
    solar["record_updated_at"] = solar_dates[changed]
    solar["has_solar_pv"] = True
    solar["solar_installed_at"] = solar_dates[changed]
    history = pd.concat([initial, refresh, solar], ignore_index=True)
    history = history.sort_values(["customer_id", "record_updated_at"], kind="stable")
    history = history.drop_duplicates(["customer_id", "record_updated_at"], keep="last").reset_index(drop=True)
    current = history.drop_duplicates("customer_id", keep="last").reset_index(drop=True)
    return current, history


def vehicle_ownership(p, adoption_dates, rng, history_start, missing_rate) -> pd.DataFrame:
    """Single-vehicle scope: exact simulated declarations, with a small unknown subset."""
    observed = pd.array(p["has_car"], dtype="boolean")
    observed[rng.random(len(observed)) < missing_rate] = pd.NA
    initial = pd.DataFrame({
        "customer_id": p["customer_id"], "has_vehicle": observed,
        "record_updated_at": pd.to_datetime(p["join_day"].astype("datetime64[D]")).to_numpy(),
    })
    initial["record_updated_at"] = initial["record_updated_at"].clip(lower=history_start)
    dates = pd.Series(pd.to_datetime(adoption_dates))
    update = initial.loc[dates.notna()].copy()
    update["has_vehicle"] = True
    update["record_updated_at"] = dates[dates.notna()].to_numpy()
    return pd.concat([initial, update], ignore_index=True).sort_values(
        ["customer_id", "record_updated_at"], kind="stable"
    ).drop_duplicates(["customer_id", "record_updated_at"], keep="last").reset_index(drop=True)
