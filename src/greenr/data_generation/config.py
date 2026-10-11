"""Generator configuration (spec 8.2/8.3): one frozen, JSON-serialisable object per dataset.

``BASE_CONFIG`` drives the training data (noise 1.0, coefficient set A, missingness A).
``perturbation.PERTURBED_CONFIG`` is the stress-test generator (noise 1.35, coefficient set B,
different interactions, missingness B, merchant distribution shift).

Coefficients act on *hidden* per-customer traits (standardised where continuous) and are never
written to any output table. Intercepts are not configured: they are calibrated per dataset so that
the 90-day adoption rate among not-yet-adopters at the feature cutoff is close to
``target_90d_rate``.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any

from greenr import config as gp_config
from greenr.data_generation.public_anchors import ENERGY_ANCHOR_SHA256

PRODUCTS = ("EV_FINANCE", "GREEN_HOME", "SOLAR_FINANCE", "PAPERLESS_BANKING")

# Trait vocabulary available to the latent outcome model (see generator._traits):
#   continuous (standardised): mileage, fuel_intensity, vehicle_age, elec_demand, gas_demand,
#       home_improvement, digital, green, wealth, age
#   indicators (0/1): owner, mortgage, house, vehicle_finance, no_ice_car, ev_owner,
#       sunny_region, electric_heating
#   latent_pref: unobserved per-product preference (N(0,1)); never observable in any table.

COEFFICIENTS_A: dict[str, dict[str, float]] = {
    "EV_FINANCE": {
        "mileage": 0.65, "fuel_intensity": 0.40, "vehicle_age": 0.40, "green": 0.50,
        "wealth": 0.30, "vehicle_finance": 0.55, "digital": 0.10, "no_ice_car": -2.6,
        "ev_owner": -1.5, "latent_pref": 0.85,
    },
    "GREEN_HOME": {
        "home_improvement": 0.75, "owner": 1.6, "mortgage": 0.45, "gas_demand": 0.30,
        "green": 0.45, "wealth": 0.25, "house": 0.30, "latent_pref": 0.85,
    },
    "SOLAR_FINANCE": {
        "owner": 2.0, "house": 0.9, "elec_demand": 0.65, "green": 0.55, "wealth": 0.35,
        "mortgage": 0.30, "home_improvement": 0.20, "sunny_region": 0.30, "latent_pref": 0.85,
    },
    "PAPERLESS_BANKING": {
        "digital": 1.05, "age": -0.25, "green": 0.30, "wealth": 0.10, "latent_pref": 0.75,
    },
}

INTERACTIONS_A: dict[str, dict[str, float]] = {
    "EV_FINANCE": {"mileage*green": 0.25, "vehicle_age*vehicle_finance": 0.25},
    "GREEN_HOME": {"home_improvement*green": 0.25, "owner*home_improvement": 0.30},
    "SOLAR_FINANCE": {"elec_demand*green": 0.25, "owner*wealth": 0.15},
    "PAPERLESS_BANKING": {"digital*green": 0.20},
}

TARGET_RATES_A: dict[str, float] = {
    "EV_FINANCE": 0.065, "GREEN_HOME": 0.080, "SOLAR_FINANCE": 0.055, "PAPERLESS_BANKING": 0.150,
}

MISSINGNESS_A: dict[str, float] = {
    "home_owner": 0.08,  # customers.home_owner null
    "sustainability_preference": 0.10,
    "region": 0.015,
    "property_type": 0.03,
    "heating_type": 0.03,
    "has_solar_pv": 0.04,
    "vehicle_record_missing": 0.05,  # car owners with no vehicle record at all
    "mileage_missing": 0.10,
    "mileage_estimated": 0.20,
    "vehicle_age_missing": 0.03,
    "vehicle_stale": 0.12,  # last record more than two years before the cutoff
    "energy_absent": 0.08,  # customers with no energy rows at all
    "energy_gappy": 0.12,  # customers with random missing months
    "energy_gap_month": 0.20,  # per-month drop probability for gappy customers
    "digital_absent": 0.02,
    "fuel_capture_zero": 0.08,  # car owners who buy fuel with another bank's card
}

MERCHANT_SHIFT_BASE: dict[str, Any] = {
    "include_shift_only": False,
    "shift_only_share": 0.0,  # share of each category's card volume going to shift-only brands
    "zipf_exponent": 1.1,
    "rank_permutation_seed": None,  # None = catalogue order is popularity order
    "variants_per_merchant": 40,
    "description_noise": 1.0,  # >1 = more decorated / truncated descriptions
    "adversarial_rate": 0.0002,  # share of OTHER card transactions with adversarial text
}


@dataclass(frozen=True)
class GeneratorConfig:
    name: str = "base"
    n_customers: int = gp_config.DEFAULT_CUSTOMERS
    seed: int = gp_config.SEED_DATA
    noise_scale: float = 1.0
    monthly_noise: float = 0.35  # extra month-to-month latent noise (times noise_scale)
    energy_anchor_sha256: str = ENERGY_ANCHOR_SHA256
    coefficients: dict[str, dict[str, float]] = field(default_factory=lambda: deepcopy(COEFFICIENTS_A))
    interactions: dict[str, dict[str, float]] = field(default_factory=lambda: deepcopy(INTERACTIONS_A))
    target_90d_rate: dict[str, float] = field(default_factory=lambda: dict(TARGET_RATES_A))
    missingness: dict[str, float] = field(default_factory=lambda: dict(MISSINGNESS_A))
    merchant_shift: dict[str, Any] = field(default_factory=lambda: dict(MERCHANT_SHIFT_BASE))
    preexisting_rates: dict[str, float] = field(default_factory=lambda: {
        "ev_owner": 0.05, "ev_finance_given_ev": 0.6, "green_home_given_owner": 0.025,
        "solar_given_owner_house": 0.05, "solar_finance_given_solar": 0.45,
        "paperless_intercept": -0.2,
    })
    late_joiner_rate: float = 0.03  # customers joining in 2026 (short history)
    stale_ev_conflict_rate: float = 0.15  # EV adopters with stale ICE record or ongoing fuel spend
    include_personas: bool = True
    vehicle_declaration_missing_rate: float = 0.03  # unknown declaration, not a non-owner
    history_start: str = gp_config.HISTORY_START.isoformat()
    history_end: str = gp_config.HISTORY_END.isoformat()
    adoption_start: str = "2025-07-01"
    calibration_cutoff: str = gp_config.FEATURE_CUTOFF.isoformat()

    def __post_init__(self) -> None:
        if self.energy_anchor_sha256 != ENERGY_ANCHOR_SHA256:
            raise ValueError("energy anchor hash does not match the pinned public statistics")
        if not isinstance(self.n_customers, int) or isinstance(self.n_customers, bool) or self.n_customers < 1:
            raise ValueError("n_customers must be a positive integer")
        if self.seed < 0:
            raise ValueError("seed must be non-negative")
        if self.noise_scale <= 0 or self.monthly_noise < 0:
            raise ValueError("noise_scale must be positive and monthly_noise non-negative")
        if not 0 <= self.vehicle_declaration_missing_rate <= 1:
            raise ValueError("vehicle_declaration_missing_rate must be in [0, 1]")
        for name, probabilities in (("target_90d_rate", self.target_90d_rate),
                                    ("missingness", self.missingness)):
            if any(not 0 <= value <= 1 for value in probabilities.values()):
                raise ValueError(f"{name} entries must be probabilities in [0, 1]")
        if set(self.coefficients) != set(PRODUCTS) or set(self.target_90d_rate) != set(PRODUCTS):
            raise ValueError("coefficients and target_90d_rate must define all four products")
        start, end, adoption, cutoff = map(date.fromisoformat, (
            self.history_start, self.history_end, self.adoption_start, self.calibration_cutoff))
        if start.day != 1 or adoption.day != 1 or not start <= adoption <= cutoff < end:
            raise ValueError("history/adoption must start at month boundaries before the cutoff and history end")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    def config_hash(self) -> str:
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "GeneratorConfig":
        return cls(**d)


BASE_CONFIG = GeneratorConfig()
