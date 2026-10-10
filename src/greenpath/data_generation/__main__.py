"""Generate reproducible base or perturbed synthetic tables."""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

from greenpath import config
from greenpath.data_generation.config import BASE_CONFIG
from greenpath.data_generation.generator import generate, write_dataset
from greenpath.data_generation.perturbation import PERTURBED_CONFIG

DEFAULT_CUSTOMERS = 4_000


def generate_dataset(*, customers: int = DEFAULT_CUSTOMERS, perturbed: bool = False,
                     output: Path | None = None, seed: int | None = None) -> dict:
    if customers < 1:
        raise ValueError("customers must be positive")
    template = PERTURBED_CONFIG if perturbed else BASE_CONFIG
    cfg = replace(template, n_customers=customers, seed=template.seed if seed is None else seed)
    target = output or (config.PERTURBED_DIR if perturbed else config.RAW_DIR)
    tables = generate(cfg, verbose=True)
    manifest = write_dataset(tables, target, cfg)
    print(f"Wrote {cfg.name} data ({len(tables['customers'])} customers) to {target}", flush=True)
    return manifest


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--customers", type=int, default=DEFAULT_CUSTOMERS)
    parser.add_argument("--perturbed", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--seed", type=int)
    args = parser.parse_args(argv)
    generate_dataset(customers=args.customers, perturbed=args.perturbed, output=args.output, seed=args.seed)


if __name__ == "__main__":
    main()
