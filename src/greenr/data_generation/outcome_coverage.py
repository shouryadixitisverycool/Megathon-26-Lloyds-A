"""Explicit follow-up evidence for the complete synthetic outcome simulation."""

from datetime import date

import pandas as pd

from greenr.contracts import Product
from greenr.pipelines.schemas import OUTCOME_OBSERVATION, validate_table


def generate_outcome_coverage(customers: pd.DataFrame, history_end: str | date) -> pd.DataFrame:
    """Cover every simulated customer/product through the deterministic simulation end.

    No synthetic outcome dropouts are introduced here. Stress callers can explicitly
    shorten coverage or mark follow-up incomplete without changing adoption events.
    """
    ids = customers["customer_id"].astype("string")
    coverage = pd.MultiIndex.from_product(
        [ids, [product.value for product in Product]], names=["customer_id", "product"]
    ).to_frame(index=False)
    coverage["customer_id"] = coverage["customer_id"].astype("string")
    coverage["product"] = coverage["product"].astype("string")
    coverage["observation_end"] = pd.Timestamp(history_end)
    coverage["outcome_available_at"] = pd.Timestamp(history_end)
    coverage["complete_followup"] = True
    validate_table(coverage, OUTCOME_OBSERVATION)
    return coverage
