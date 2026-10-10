"""Independent, documented generator shift used only for evaluation."""

from dataclasses import replace

from greenpath import config
from greenpath.data_generation.config import BASE_CONFIG


PERTURBED_CONFIG = replace(
    BASE_CONFIG,
    name="perturbed",
    seed=config.SEED_PERTURBATION,
    noise_scale=1.35,
    monthly_noise=0.5,
    coefficients={
        product: {name: value * (0.65 if name in {"green", "wealth"} else 1.2)
                  for name, value in coefficients.items()}
        for product, coefficients in BASE_CONFIG.coefficients.items()
    },
    interactions={
        product: {name: value * 0.5 for name, value in interactions.items()}
        for product, interactions in BASE_CONFIG.interactions.items()
    },
    missingness={name: min(0.6, value * 1.6) for name, value in BASE_CONFIG.missingness.items()},
    merchant_shift={
        **BASE_CONFIG.merchant_shift,
        "include_shift_only": True,
        "shift_only_share": 0.25,
        "zipf_exponent": 0.7,
        "rank_permutation_seed": config.SEED_PERTURBATION,
        "description_noise": 1.35,
    },
    stale_ev_conflict_rate=0.25,
    include_personas=False,
)
