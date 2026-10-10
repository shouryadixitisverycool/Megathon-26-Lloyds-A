"""Held-out predictions, demo persona payloads and portfolio/trend scores (spec 46, 56.2 step 12).

Outputs
- ``reports/predictions/test_predictions.csv``: one row per held-out test customer x product.
- ``data/artifacts/demo/<customer_id>.json``: CustomerSnapshot, PropensityResult and
  TrustAssessment payloads for each demo persona (contract-valid; Agent B fixtures).
- ``data/artifacts/portfolio_scores.parquet``: every customer x product at each trend cutoff,
  with propensity, confidence, trust and observed 90-day outcome, for portfolio/trend views.
- ``data/artifacts/greenpath.db``: the same tables in SQLite for demo persistence.
"""

from __future__ import annotations

import json
import sqlite3
import time
from datetime import date

import numpy as np
import pandas as pd

from greenpath import config
from greenpath.contracts import ConfidenceStatus, CustomerSnapshot, Product
from greenpath.pipelines.run import cutoff_context, load_tables, log, write_json
from greenpath.pipelines.runtime import PRODUCTS, Runtime, load_runtime
from greenpath.pipelines.split import make_labels
from greenpath.trust.provider import trust_frame

DEMO_DIR = config.ARTIFACT_DIR / "demo"
PORTFOLIO_PATH = config.ARTIFACT_DIR / "portfolio_scores.parquet"
PREDICTIONS_PATH = config.REPORTS_DIR / "predictions" / "test_predictions.csv"
DB_PATH = config.ARTIFACT_DIR / "greenpath.db"


def score_snapshots(rt: Runtime, snaps: list[CustomerSnapshot], cutoff: date) -> pd.DataFrame:
    """Flatten propensity + confidence + trust for a batch of snapshots into one tidy frame."""
    parts = []
    for product in PRODUCTS:
        results = rt.propensity.score_many(snaps, product)
        trust = trust_frame(rt.trust.assess_many(snaps, product)).drop(columns=["product"], errors="ignore")
        df = pd.DataFrame({
            "cutoff": pd.Timestamp(cutoff),
            "customer_id": [r.customer_id for r in results],
            "product": product.value,
            "in_model_population": [r.in_model_population for r in results],
            "population_exclusion": [r.population_exclusion.value if r.population_exclusion else None for r in results],
            "propensity": [r.propensity if r.in_model_population else np.nan for r in results],
            "threshold": rt.bundles[product].threshold,
            "model_version": [r.model_version for r in results],
            "calibration_version": [r.calibration_version for r in results],
            "confidence_status": [r.confidence.status.value for r in results],
            "confidence": [r.confidence.value if r.confidence.value is not None else np.nan for r in results],
            "confidence_bucket": [r.confidence.bucket.value if r.confidence.bucket else None for r in results],
            "reason_codes": [";".join(c.value for c in r.reason_codes) for r in results],
        })
        df["above_threshold"] = df["propensity"] >= df["threshold"]
        trust = trust.rename(columns={c: f"trust_{c}" for c in trust.columns if c != "customer_id"})
        parts.append(df.merge(trust, on="customer_id", how="left"))
    return pd.concat(parts, ignore_index=True)


def _context(tables: dict[str, pd.DataFrame], cutoff: date) -> pd.DataFrame:
    """Aggregate-only context. age_band is used for portfolio aggregates/fairness audit, never as a feature."""
    return cutoff_context(tables, cutoff)[["region", "segment", "age_band", "home_owner"]]


def stage_predict() -> None:
    t0 = time.time()
    tables = load_tables(config.RAW_DIR)
    rt = load_runtime(cutoffs=sorted(set(config.TREND_CUTOFFS) | {config.FEATURE_CUTOFF}))
    split = pd.read_csv(config.PROCESSED_DIR / "split_manifest.csv", dtype=str).set_index("customer_id")["split"]

    # 1. portfolio + monthly trend scores (every customer, each month-end cutoff)
    frames = []
    for cutoff in config.TREND_CUTOFFS:
        ctx = _context(tables, cutoff)
        snaps = [s for s in rt.snapshots.snapshots(cutoff) if s.customer_id in ctx.index]
        scored = score_snapshots(rt, snaps, cutoff)
        labels = make_labels(tables["customer_outcomes"], [s.customer_id for s in snaps], cutoff,
                             coverage=tables.get("outcome_observation"))
        long = labels.reset_index().melt(id_vars="customer_id", var_name="product", value_name="observed_adoption_90d")
        cohort = scored.merge(long, on=["customer_id", "product"], how="left")
        cohort["outcome_observed"] = cohort["observed_adoption_90d"].notna()
        cohort["outcome_coverage_mode"] = ("EXPLICIT" if "outcome_observation" in tables
                                           else "COMPLETE_SIMULATION_ASSUMPTION")
        frames.append(cohort.merge(ctx, left_on="customer_id", right_index=True, how="left"))
        log(f"scored {len(snaps)} customers at {cutoff}")
    portfolio = pd.concat(frames, ignore_index=True)
    portfolio["split"] = portfolio["customer_id"].map(split)
    portfolio.to_parquet(PORTFOLIO_PATH)
    canonical = portfolio[portfolio["cutoff"] == pd.Timestamp(config.FEATURE_CUTOFF)]
    availability = {}
    for cohort, rows in (("population", canonical), ("demo", canonical[canonical["split"] == "demo"])):
        availability[cohort] = {}
        for product, group in [("ALL", rows), *list(rows.groupby("product"))]:
            eligible = group[group["in_model_population"]]
            validated = int((eligible["confidence_status"] == ConfidenceStatus.VALIDATED.value).sum())
            availability[cohort][product] = {
                "n_total": len(group), "n_eligible": len(eligible), "n_validated": validated,
                "validated_share_eligible": validated / len(eligible) if len(eligible) else None,
                "validated_share_total": validated / len(group) if len(group) else None,
                "status_counts": group["confidence_status"].value_counts().to_dict(),
            }
    write_json(config.REPORTS_DIR / "confidence_availability.json", availability)

    # 2. held-out test predictions at the canonical cutoff
    current = portfolio[(portfolio["cutoff"] == pd.Timestamp(config.FEATURE_CUTOFF)) & (portfolio["split"] == "test")]
    PREDICTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    current.drop(columns=["age_band"]).assign(
        data_cutoff=config.FEATURE_CUTOFF, outcome_window_end=config.OUTCOME_WINDOW_END,
        prediction_timestamp=config.PREDICTION_TIMESTAMP,
        synthetic_data_notice="Synthetic demonstration data; not evidence of real-world performance.",
    ).to_csv(PREDICTIONS_PATH, index=False)
    log(f"wrote {len(current)} held-out predictions -> {PREDICTIONS_PATH.relative_to(config.REPO_ROOT)}")

    # 3. demo persona payloads (contract JSON)
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    index = {}
    for cid in config.DEMO_PERSONA_IDS:
        snap = rt.snapshots.get_snapshot(cid)
        if snap is None:
            continue
        payload = {"snapshot": json.loads(snap.model_dump_json()), "propensity": {}, "trust": {}}
        for p in PRODUCTS:
            payload["propensity"][p.value] = json.loads(rt.propensity.score(snap, p).model_dump_json())
            payload["trust"][p.value] = json.loads(rt.trust.assess(snap, p).model_dump_json())
        (DEMO_DIR / f"{cid}.json").write_text(json.dumps(payload, indent=2))
        index[cid] = f"{cid}.json"
    write_json(DEMO_DIR / "index.json", index)

    # 4. SQLite demo store
    with sqlite3.connect(DB_PATH) as con:
        _to_sql(portfolio, "portfolio_scores", con)
        _to_sql(current, "test_predictions", con)
    log(f"predict finished in {time.time() - t0:.0f}s")


def _to_sql(df: pd.DataFrame, name: str, con) -> None:
    out = df.copy()
    for c in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[c]):
            out[c] = out[c].dt.strftime("%Y-%m-%d")
    out.to_sql(name, con, if_exists="replace", index=False)


def stage_demo() -> None:
    """Terminal walk-through of the demo personas (Agent A has no UI; Agent B owns the app)."""
    rt = load_runtime()
    print("Greenr - Agent A structured outputs for demo personas (synthetic data)\n")
    print(f"Data cutoff {config.FEATURE_CUTOFF} | outcome window to {config.OUTCOME_WINDOW_END} | "
          f"prediction {config.PREDICTION_TIMESTAMP:%Y-%m-%d}\n")
    for cid in config.DEMO_PERSONA_IDS:
        snap = rt.snapshots.get_snapshot(cid)
        if snap is None:
            print(f"{cid}: not present")
            continue
        print(f"== {cid}  (segment {snap.segment}, region {snap.home.region}, "
              f"{snap.data_quality.transaction_months_observed} months of transactions)")
        for p in PRODUCTS:
            r = rt.propensity.score(snap, p)
            t = rt.trust.assess(snap, p)
            if not r.in_model_population:
                head = f"not in population ({r.population_exclusion.value})"
            else:
                conf = (f"{r.confidence.value:.0%} {r.confidence.bucket.value}"
                        if r.confidence.status is ConfidenceStatus.VALIDATED else "suppressed")
                head = f"propensity {r.propensity:.0%} (threshold {rt.bundles[p].threshold:.0%}), confidence {conf}"
            issues = ",".join(i.code.value for i in t.issues) or "-"
            reasons = ",".join(c.value for c in r.reason_codes) or "-"
            print(f"   {p.value:<18} {head}; trust {t.score:.2f} {t.status.value}; issues {issues}; reasons {reasons}")
        print()
