"""Leakage guards (spec 8.5, 9.2, 12; DESIGN "Labels and splits").

Each ``check_*`` function raises ``LeakageError`` on a violation. It also raises when it cannot
verify a rule, for example because a required column is missing; the guards fail closed. On
success each check returns a short detail string for the leakage report. ``run_all_checks``
runs every applicable check and returns a summary dict.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import pandas as pd

from greenpath.contracts import Product


class LeakageError(AssertionError):
    """A leakage rule was violated, or it could not be verified."""


TARGET_NAME_PATTERN = re.compile(r"adopt|label|target|take_up|outcome", re.IGNORECASE)
DEFAULT_AUDIT_COLUMNS: frozenset[str] = frozenset({"age_band", "income_band", "postcode_sector", "region"})
POST_ADOPTION_FLAGS: dict[Product, frozenset[str]] = {
    Product.EV_FINANCE: frozenset({"holds_ev_finance", "is_ev"}),
    Product.GREEN_HOME: frozenset({"holds_green_home_loan"}),
    Product.SOLAR_FINANCE: frozenset({"holds_solar_finance", "has_existing_solar"}),
    Product.PAPERLESS_BANKING: frozenset({"is_paperless"}),
}


@dataclass(frozen=True)
class EventSource:
    """A feature source frame whose event times must not be after the cutoff.

    ``monthly=True`` means ``time_col`` holds the first day of a month. Such a row becomes
    available at month end, so it is compared using its month-end date.
    """

    name: str
    frame: pd.DataFrame
    time_col: str
    monthly: bool = False
    availability_col: str | None = None


def check_customer_split_disjoint(split_or_frames: Any) -> str:
    """No customer may appear in more than one split.

    Accepts a Series indexed by ``customer_id`` whose values are split labels, or a mapping of
    split name to an iterable of IDs or to a DataFrame (``customer_id`` column, else the index).
    """
    membership = _split_membership(split_or_frames)
    names = list(membership)
    problems: list[str] = []
    for i, left in enumerate(names):
        for right in names[i + 1:]:
            overlap = membership[left] & membership[right]
            if overlap:
                sample = sorted(overlap)[:3]
                problems.append(f"{left} & {right}: {len(overlap)} customers (e.g. {sample})")
    if problems:
        raise LeakageError("customer appears in more than one split: " + "; ".join(problems))
    total = sum(len(ids) for ids in membership.values())
    return f"{len(names)} splits, {total} customers, no customer in more than one split"


def check_event_times(
    frame: pd.DataFrame,
    time_col: str,
    cutoff: date | datetime,
    name: str,
    *,
    monthly: bool = False,
) -> str:
    """Every non-null event time in ``frame[time_col]`` must fall on or before the cutoff date.

    The cutoff is a calendar date, so events dated on the cutoff day are allowed.
    """
    cutoff_day = pd.Timestamp(cutoff).normalize()
    if not isinstance(frame, pd.DataFrame) or time_col not in frame.columns:
        raise LeakageError(f"{name}: cannot verify event times without column {time_col!r}")
    times = pd.to_datetime(frame[time_col])
    if monthly:
        times = times + pd.offsets.MonthEnd(0)  # a monthly row is available at month end
    days = times.dt.normalize()
    late = days > cutoff_day
    if bool(late.any()):
        latest = days.max()
        raise LeakageError(
            f"{name}: {int(late.sum())} rows have event time after cutoff {cutoff_day.date()} "
            f"(latest {latest.date()})")
    checked = int(days.notna().sum())
    basis = "month-end availability" if monthly else "event time"
    return f"{name}: {checked} rows with {basis} on or before cutoff {cutoff_day.date()}"


def check_no_target_features(feature_names: Iterable[str]) -> str:
    """No feature name may look like a label or outcome (adopt, label, target, take_up, outcome)."""
    names = list(feature_names)
    hits = sorted(n for n in names if TARGET_NAME_PATTERN.search(n))
    if hits:
        raise LeakageError(f"target-like feature names: {hits}")
    return f"{len(names)} feature names, none target-like"


def check_no_post_adoption_features(product: Product | str, feature_names: Iterable[str]) -> str:
    """The modelled product's own post-adoption flags must not be features for that product."""
    resolved = _as_product(product)
    forbidden = POST_ADOPTION_FLAGS[resolved]
    names = list(feature_names)
    hits = sorted(set(names) & forbidden)
    if hits:
        raise LeakageError(f"{resolved.value} features include post-adoption flags {hits}")
    return f"{resolved.value}: none of {sorted(forbidden)} used as features"


def check_no_audit_features(
    feature_names: Iterable[str],
    audit_columns: Iterable[str] = DEFAULT_AUDIT_COLUMNS,
) -> str:
    """Audit-only and proxy columns (age, income, postcode sector, region) must stay out of features."""
    names = list(feature_names)
    audit = set(audit_columns)
    hits = sorted(set(names) & audit)
    if hits:
        raise LeakageError(f"audit-only or proxy columns in features: {hits}")
    return f"{len(names)} feature names, none audit-only or proxy"


def run_all_checks(
    *,
    cutoff: date | datetime,
    split: Any = None,
    event_sources: Sequence[EventSource] = (),
    feature_names: Sequence[str] | None = None,
    products: Sequence[Product | str] = (),
    audit_columns: Iterable[str] = DEFAULT_AUDIT_COLUMNS,
    raise_on_failure: bool = True,
) -> dict[str, Any]:
    """Run every check whose inputs are supplied and return a summary for the leakage report.

    Each entry in ``checks`` has ``check``, ``target``, ``status`` (``PASS``, ``FAIL`` or
    ``NOT_RUN``) and ``detail``. With ``raise_on_failure`` (the default), any failure raises
    one ``LeakageError`` that lists them all.
    """
    results: list[dict[str, Any]] = []
    sources = list(event_sources)
    product_list = list(products)

    def record(check: str, target: str, fn: Any, *args: Any, **kwargs: Any) -> None:
        try:
            detail = fn(*args, **kwargs)
            status = "PASS"
        except LeakageError as exc:
            detail = str(exc)
            status = "FAIL"
        results.append({"check": check, "target": target, "status": status, "detail": detail})

    def not_run(check: str, target: str, reason: str) -> None:
        results.append({"check": check, "target": target, "status": "NOT_RUN", "detail": reason})

    if split is None:
        not_run("customer_split_disjoint", "split", "no split supplied")
    else:
        record("customer_split_disjoint", "split", check_customer_split_disjoint, split)

    if not sources:
        not_run("event_times_within_cutoff", "event_sources", "no event sources supplied")
    for source in sources:
        record("event_times_within_cutoff", source.name, check_event_times,
               source.frame, source.time_col, cutoff, source.name, monthly=source.monthly)
        if source.availability_col is not None:
            record("source_available_within_cutoff", source.name, check_availability,
                   source.frame, source.availability_col, cutoff, source.name)

    if feature_names is None:
        not_run("no_target_features", "features", "no feature names supplied")
        not_run("no_audit_features", "features", "no feature names supplied")
    else:
        names = list(feature_names)
        record("no_target_features", "features", check_no_target_features, names)
        record("no_audit_features", "features", check_no_audit_features, names, audit_columns)

    if not product_list:
        not_run("no_post_adoption_features", "products", "no products supplied")
    for product in product_list:
        target = str(getattr(product, "value", product))
        if feature_names is None:
            not_run("no_post_adoption_features", target, "no feature names supplied")
        else:
            record("no_post_adoption_features", target, check_no_post_adoption_features,
                   product, list(feature_names))

    failures = [r for r in results if r["status"] == "FAIL"]
    summary = {
        "cutoff": str(pd.Timestamp(cutoff).date()),
        "passed": not failures,
        "n_checks": sum(1 for r in results if r["status"] != "NOT_RUN"),
        "n_failed": len(failures),
        "n_not_run": sum(1 for r in results if r["status"] == "NOT_RUN"),
        "checks": results,
    }
    if failures and raise_on_failure:
        message = "; ".join(f"{r['check']}[{r['target']}]: {r['detail']}" for r in failures)
        raise LeakageError(message)
    return summary


def check_availability(frame, time_col, cutoff, name):
    if time_col not in frame or frame[time_col].isna().any():
        raise LeakageError(f"{name}: missing source availability timestamps")
    if (pd.to_datetime(frame[time_col]) > pd.Timestamp(cutoff)).any():
        raise LeakageError(f"{name}: source availability after cutoff {cutoff}")
    return check_event_times(frame, time_col, cutoff, name)


def _as_product(product: Product | str) -> Product:
    try:
        return Product(product)
    except ValueError as exc:
        raise LeakageError(f"unknown product {product!r}: cannot verify post-adoption features") from exc


def _split_membership(split_or_frames: Any) -> dict[str, set[str]]:
    if isinstance(split_or_frames, pd.Series):
        labels = split_or_frames.to_numpy(dtype=object)
        ids = split_or_frames.index.astype(str).to_numpy(dtype=object)
        return {str(label): set(ids[labels == label].tolist()) for label in pd.unique(labels)}
    if isinstance(split_or_frames, Mapping):
        membership: dict[str, set[str]] = {}
        for name, value in split_or_frames.items():
            if isinstance(value, pd.DataFrame):
                column = value["customer_id"] if "customer_id" in value.columns else value.index
                membership[str(name)] = {str(c) for c in column}
            else:
                membership[str(name)] = {str(c) for c in value}
        return membership
    raise LeakageError(f"cannot verify split: unsupported type {type(split_or_frames).__name__}")
