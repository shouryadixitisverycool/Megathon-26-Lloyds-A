"""Customer-level take-up labels and train / validation / test split (spec 9; DESIGN "Labels and splits").

Labels: a customer is positive for a product when the product is adopted in the window
(cutoff, cutoff + window_days]. Adoption exactly on the cutoff is not a label (it is already
adopted, see ``adopted_before``). Adoption on cutoff + window_days is a label; one day later is not.

Splits are by customer, never by row. Personas listed in ``force_test`` (the demo personas by
default) are labelled ``"demo"``: they are never trained on and never used for model selection.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from greenpath.config import DEMO_PERSONA_IDS, OUTCOME_WINDOW_DAYS, SEED_SPLIT
from greenpath.contracts import Product

SPLIT_LABELS: tuple[str, ...] = ("train", "validation", "test", "demo")
PRODUCT_COLUMNS: tuple[str, ...] = tuple(p.value for p in Product)
_OUTCOME_COLUMNS = ("customer_id", "product", "adoption_date")


def make_labels(
    outcomes: pd.DataFrame,
    customer_ids: Iterable[str],
    cutoff: date | datetime,
    window_days: int = OUTCOME_WINDOW_DAYS,
) -> pd.DataFrame:
    """Return 0/1 take-up labels per customer and product.

    The index is ``customer_id`` (in the order given). Columns are the ``Product`` values. A label is 1
    when the adoption date satisfies ``cutoff < adoption_date <= cutoff + window_days``.
    """
    ids = _customer_index(customer_ids)
    start = pd.Timestamp(cutoff)
    end = start + pd.Timedelta(days=window_days)
    adoptions = _adoptions(outcomes, ids)
    in_window = adoptions[(adoptions["adoption_date"] > start) & (adoptions["adoption_date"] <= end)]
    return _indicator_frame(in_window, ids)


def adopted_before(
    outcomes: pd.DataFrame,
    customer_ids: Iterable[str],
    cutoff: date | datetime,
) -> pd.DataFrame:
    """Return booleans per customer and product: adopted on or before ``cutoff``.

    Used for population exclusion (customers who already hold the product at the cutoff).
    """
    ids = _customer_index(customer_ids)
    adoptions = _adoptions(outcomes, ids)
    adopted = adoptions[adoptions["adoption_date"] <= pd.Timestamp(cutoff)]
    return _indicator_frame(adopted, ids).astype(bool)


def split_customers(
    customer_ids: Iterable[str],
    seed: int = SEED_SPLIT,
    fractions: tuple[float, float, float] = (0.7, 0.15, 0.15),
    force_test: Iterable[str] = DEMO_PERSONA_IDS,
) -> pd.Series:
    """Assign each customer to ``train``, ``validation``, ``test`` or ``demo``.

    ``force_test`` names customers that are labelled ``"demo"`` instead of entering the random
    split. Listed IDs that are absent from ``customer_ids`` are ignored. The random part is a
    seeded permutation of the sorted IDs, so the result depends on the seed and the set of IDs,
    not on their order. The returned Series is indexed by ``customer_id`` in input order.
    """
    f_train, f_val, _ = _validate_fractions(fractions)
    ids = _customer_index(customer_ids)
    demo = set(force_test) & set(ids)
    pool = sorted(c for c in ids if c not in demo)
    rng = np.random.default_rng(seed)
    shuffled = [pool[i] for i in rng.permutation(len(pool))]

    # Cumulative cut points; the test split takes the remainder so every customer is assigned.
    n = len(shuffled)
    first_cut = round(f_train * n)
    second_cut = round((f_train + f_val) * n)
    assigned: dict[str, str] = {}
    for position, customer in enumerate(shuffled):
        if position < first_cut:
            assigned[customer] = "train"
        elif position < second_cut:
            assigned[customer] = "validation"
        else:
            assigned[customer] = "test"
    for customer in demo:
        assigned[customer] = "demo"
    values = [assigned[c] for c in ids]
    return pd.Series(values, index=ids, name="split", dtype=object)


def write_split_manifest(split: pd.Series, path: str | Path) -> str:
    """Write ``customer_id,split`` rows (sorted by customer) to ``path`` and return the sha256 hex digest.

    A ``<name>.sha256`` sidecar file in ``sha256sum`` format is written next to it.
    """
    labels = pd.Series(split.to_numpy(dtype=object), index=split.index.astype(str))
    if labels.index.has_duplicates:
        raise ValueError("split manifest requires one row per customer_id")
    unknown = sorted(set(labels.unique().tolist()) - set(SPLIT_LABELS))
    if unknown:
        raise ValueError(f"unknown split labels: {unknown}")
    frame = pd.DataFrame({"customer_id": labels.index.to_numpy(dtype=object),
                          "split": labels.to_numpy(dtype=object)})
    frame = frame.sort_values("customer_id", kind="stable").reset_index(drop=True)
    data = frame.to_csv(index=False, lineterminator="\n").encode("utf-8")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    target.with_name(target.name + ".sha256").write_text(f"{digest}  {target.name}\n", encoding="utf-8")
    return digest


def _customer_index(customer_ids: Iterable[str]) -> pd.Index:
    ids = pd.Index([str(c) for c in customer_ids], dtype=object, name="customer_id")
    if ids.has_duplicates:
        raise ValueError("customer_ids must be unique")
    return ids


def _validate_fractions(fractions: tuple[float, float, float]) -> tuple[float, float, float]:
    if len(fractions) != 3:
        raise ValueError("fractions must be (train, validation, test)")
    f_train, f_val, f_test = (float(f) for f in fractions)
    if min(f_train, f_val, f_test) < 0:
        raise ValueError("fractions must be non-negative")
    if abs(f_train + f_val + f_test - 1.0) > 1e-9:
        raise ValueError("fractions must sum to 1")
    return f_train, f_val, f_test


def _adoptions(outcomes: pd.DataFrame, ids: pd.Index) -> pd.DataFrame:
    """Rows of ``outcomes`` for the requested customers with a valid product and adoption date."""
    missing = [c for c in _OUTCOME_COLUMNS if c not in outcomes.columns]
    if missing:
        raise ValueError(f"outcomes is missing columns {missing}")
    frame = pd.DataFrame({
        "customer_id": outcomes["customer_id"].astype(str).to_numpy(dtype=object),
        "product": outcomes["product"].astype(str).to_numpy(dtype=object),
        "adoption_date": pd.to_datetime(outcomes["adoption_date"]).to_numpy(),
    })
    unknown = sorted(set(frame["product"].tolist()) - set(PRODUCT_COLUMNS))
    if unknown:
        raise ValueError(f"unknown outcome products: {unknown[:5]}")
    keep = frame["adoption_date"].notna() & frame["customer_id"].isin(ids)
    return frame[keep].reset_index(drop=True)


def _indicator_frame(events: pd.DataFrame, ids: pd.Index) -> pd.DataFrame:
    matrix = np.zeros((len(ids), len(PRODUCT_COLUMNS)), dtype=np.int64)
    if len(events):
        rows = ids.get_indexer(events["customer_id"])
        cols = pd.Index(PRODUCT_COLUMNS).get_indexer(events["product"])
        matrix[rows, cols] = 1
    return pd.DataFrame(matrix, index=ids, columns=list(PRODUCT_COLUMNS))
