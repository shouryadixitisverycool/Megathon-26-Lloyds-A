"""Baseline A (spec 11.2): transparent points-based rule score per product.

Each rule awards fixed points when a condition on one feature holds; the score is
``points earned / maximum points`` in [0, 1]. Missing evidence earns nothing (a rule never
fires on a NaN). Quantile thresholds are resolved from the TRAINING population at fit time and
stored, so the baseline is reproducible and carries no information from validation/test.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from greenr.contracts import Product


@dataclass(frozen=True)
class Rule:
    name: str
    feature: str
    op: str  # ">=", "<=", ">" or "flag" (feature == 1)
    points: float
    quantile: float | None = None  # resolve the threshold from the train population at fit
    threshold: float | None = None  # fixed threshold (or resolved value after fit)
    description: str = ""

    def resolved(self, series: pd.Series | None) -> "Rule":
        if self.quantile is None or series is None:
            return self
        vals = series.dropna()
        thr = float(vals.quantile(self.quantile)) if len(vals) else float("nan")
        return Rule(self.name, self.feature, self.op, self.points, self.quantile, thr, self.description)

    def holds(self, x: pd.DataFrame) -> np.ndarray:
        if self.feature not in x.columns:
            return np.zeros(len(x), dtype=bool)
        v = x[self.feature].to_numpy(dtype="float64")
        with np.errstate(invalid="ignore"):
            if self.op == "flag":
                return v == 1.0
            thr = self.threshold
            if thr is None or np.isnan(thr):
                return np.zeros(len(x), dtype=bool)
            if self.op == ">=":
                return v >= thr
            if self.op == ">":
                return v > thr
            if self.op == "<=":
                return v <= thr
        raise ValueError(f"unknown op {self.op}")


# Rule templates (spec 11.2 example: EV = ICE owner AND recurring fuel spend AND mileage).
HEURISTIC_RULES: dict[Product, list[Rule]] = {
    Product.EV_FINANCE: [
        Rule("ice_owner", "is_ice", "flag", 3, description="owns a petrol/diesel vehicle"),
        Rule("high_fuel_spend", "fuel_spend_90d_avg", ">=", 3, quantile=0.6,
             description="monthly fuel spend at/above the training 60th percentile"),
        Rule("high_mileage", "annual_mileage_km", ">=", 2, quantile=0.6,
             description="annual mileage at/above the training 60th percentile"),
        Rule("frequent_fuel_stops", "fuel_txn_freq_90d", ">=", 1, quantile=0.6,
             description="fuel transaction frequency at/above the training 60th percentile"),
        Rule("older_vehicle", "vehicle_age_years", ">=", 1, quantile=0.6,
             description="vehicle age at/above the training 60th percentile"),
        Rule("existing_vehicle_finance", "has_vehicle_finance", "flag", 1,
             description="already finances the vehicle"),
        Rule("sustainability_pref", "sustainability_preference", ">=", 1, threshold=4.0,
             description="stated sustainability preference 4 or 5"),
    ],
    Product.GREEN_HOME: [
        Rule("homeowner", "home_owner", "flag", 3, description="homeowner"),
        Rule("mortgage", "has_mortgage", "flag", 2, description="has a mortgage"),
        Rule("high_utility_spend", "utilities_spend_90d_avg", ">=", 2, quantile=0.6,
             description="utility spend at/above the training 60th percentile"),
        Rule("high_gas_use", "gas_kwh_12m", ">=", 2, quantile=0.6,
             description="gas use at/above the training 60th percentile"),
        Rule("home_improvement_spend", "home_improvement_spend_90d_avg", ">", 2, threshold=0.0,
             description="any home-improvement spend in the last 90 days"),
        Rule("sustainability_pref", "sustainability_preference", ">=", 1, threshold=4.0,
             description="stated sustainability preference 4 or 5"),
    ],
    Product.SOLAR_FINANCE: [
        Rule("homeowner", "home_owner", "flag", 3, description="homeowner"),
        Rule("high_electricity_use", "electricity_kwh_12m", ">=", 3, quantile=0.6,
             description="electricity use at/above the training 60th percentile"),
        Rule("detached_or_house", "property_is_house", "flag", 1, description="lives in a house"),
        Rule("home_improvement_spend", "home_improvement_spend_90d_avg", ">", 1, threshold=0.0,
             description="any home-improvement spend in the last 90 days"),
        Rule("sustainability_pref", "sustainability_preference", ">=", 1, threshold=4.0,
             description="stated sustainability preference 4 or 5"),
    ],
    Product.PAPERLESS_BANKING: [
        Rule("paper_statements", "paper_statements_3m", ">", 3, threshold=0.0,
             description="received paper statements in the last 3 months"),
        Rule("high_digital_activity", "digital_txn_3m_avg", ">=", 2, quantile=0.6,
             description="digital transactions at/above the training 60th percentile"),
        Rule("high_app_use", "app_logins_3m_avg", ">=", 2, quantile=0.6,
             description="app logins at/above the training 60th percentile"),
        Rule("few_branch_visits", "branch_visits_3m", "<=", 1, threshold=0.0,
             description="no branch visits in the last 3 months"),
        Rule("sustainability_pref", "sustainability_preference", ">=", 1, threshold=4.0,
             description="stated sustainability preference 4 or 5"),
    ],
}


@dataclass
class HeuristicModel:
    product: Product
    rules: list[Rule] = field(default_factory=list)

    @classmethod
    def fit(cls, product: Product, train_matrix: pd.DataFrame) -> "HeuristicModel":
        """Resolve quantile thresholds on the training-population feature matrix."""
        rules = [r.resolved(train_matrix[r.feature] if r.feature in train_matrix.columns else None)
                 for r in HEURISTIC_RULES[product]]
        return cls(product, rules)

    @property
    def max_points(self) -> float:
        return float(sum(r.points for r in self.rules))

    def score(self, x: pd.DataFrame) -> np.ndarray:
        """Points earned / max points, in [0, 1]."""
        total = np.zeros(len(x))
        for r in self.rules:
            total += r.points * r.holds(x)
        return total / self.max_points

    def describe(self) -> list[dict]:
        return [{"rule": r.name, "feature": r.feature, "op": r.op, "threshold": r.threshold,
                 "points": r.points, "description": r.description} for r in self.rules]
