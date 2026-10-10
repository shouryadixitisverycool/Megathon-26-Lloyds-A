"""Measured local API/cache performance and decision-level fairness evidence."""

import json
from pathlib import Path
import resource
import sys
import tempfile
import time

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from greenpath import config
from greenpath.api.main import create_app
from greenpath.extensions.service import prioritise
from greenpath.impact import Product
from greenpath.llm.service import ExplanationService


def benchmark(mode, memory_path):
    # ru_maxrss is bytes on macOS and KiB on Linux; it is a process lifetime peak.
    rss_scale = 1 if sys.platform == "darwin" else 1024
    peak_rss_before = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * rss_scale)
    benchmark_started = time.perf_counter()
    build_started = time.perf_counter()
    # This benchmark measures the offline path. Paid evaluation is a separate opt-in.
    application = create_app(provider_mode=mode, memory_path=memory_path,
                             explanation_service=ExplanationService(), background_warmup=False)
    build_seconds = time.perf_counter() - build_started
    print(f"{mode}: application build {build_seconds:.2f}s", flush=True)
    started = time.perf_counter()
    with TestClient(application) as client:
        startup = time.perf_counter() - started
        print(f"{mode}: lifespan startup {startup:.2f}s", flush=True)
        customer_id = "C10001" if mode == "trained" else "GP-001"
        paths = ["/health", f"/customers/{customer_id}", f"/customers/{customer_id}/recommendations",
                 f"/customers/{customer_id}/explanations/EV_FINANCE", "/portfolio/summary", "/portfolio/trends"]
        measurements = {}
        for path in paths:
            latencies = []
            for _ in range(5):
                started = time.perf_counter()
                response = client.get(path)
                response.raise_for_status()
                latencies.append((time.perf_counter() - started) * 1000)
            measurements[path] = {"n": len(latencies), "p50_ms": float(np.median(latencies)),
                                  "p95_ms": float(np.percentile(latencies, 95)), "max_ms": max(latencies)}
            print(f"{mode}: {path} five requests {sum(latencies) / 1000:.2f}s", flush=True)
        metrics = client.get("/explanations/metrics").json()
        fairness = []
        ranking = {}
        scoring_started = time.perf_counter()
        # Startup/summary already persisted every decision. Do not serialize and
        # validate the large provenance snapshots again just to aggregate scores.
        with application.state.memory_store.connect() as db:
            rows = [json.loads(row[0]) for row in db.execute(
                "SELECT json_remove(payload, '$.provenance') FROM decisions"
            )]
        expected = {(snapshot.customer_id, product.value)
                    for snapshot in application.state.snapshot_provider.list_snapshots()
                    for product in Product}
        observed = {(row["customer_id"], row["product"]) for row in rows}
        if observed != expected or len(rows) != len(expected):
            raise ValueError("Persisted evaluation decisions must cover every snapshot/product exactly once")
        opportunities = prioritise(rows)
        scoring_seconds = time.perf_counter() - scoring_started
        print(f"{mode}: full portfolio scoring {scoring_seconds:.2f}s ({len(opportunities)} rows)", flush=True)
        distributions_started = time.perf_counter()
        distributions = {}
        for product in sorted({row["product"] for row in opportunities}):
            rows = [row for row in opportunities if row["product"] == product]
            distributions[product] = {}
            for name, values in {
                "propensity": [(row.get("propensity") or {}).get("probability") for row in rows],
                "validated_confidence": [(row.get("propensity") or {}).get("confidence") if (row.get("propensity") or {}).get("confidence_validated") else None for row in rows],
                "trust": [row["trust"]["score"] for row in rows],
                "priority": [row["priority"]["score"] for row in rows],
            }.items():
                observed = [float(value) for value in values if value is not None]
                counts, edges = np.histogram(observed, bins=np.linspace(0, 1, 11))
                distributions[product][name] = {"n": len(observed), "missing_count": len(values) - len(observed),
                                               "counts": counts.tolist(), "bin_edges": edges.tolist(),
                                               "mean": float(np.mean(observed)) if observed else None}
        distributions_seconds = time.perf_counter() - distributions_started
        audit_started = time.perf_counter()
        if mode == "trained":
            source = pd.read_parquet(config.RAW_DIR / "customers.parquet").set_index("customer_id")
            labels = pd.read_parquet(config.PROCESSED_DIR / "labels.parquet")
            split = pd.read_csv(config.PROCESSED_DIR / "split_manifest.csv", dtype=str).set_index("customer_id")["split"]
            records = []
            # Unfiltered opportunities contain the same full-cohort decisions, already persisted.
            for row in opportunities:
                propensity = row.get("propensity") or {}
                records.append({"customer_id": row["customer_id"], "product": row["product"],
                                "recommended": row["state"] == "RECOMMEND",
                                "abstained": row["state"] in {"INSUFFICIENT_INFORMATION", "CONFLICT_REQUIRES_REVIEW"},
                                "trust": float(row["trust"]["score"]),
                                "confidence": float(propensity["confidence"]) if propensity.get("confidence_validated") else np.nan,
                                "probability": float(propensity["probability"]) if propensity.get("probability") is not None else np.nan})
            frame = pd.DataFrame(records)
            priority_lookup = {(row["customer_id"], row["product"]): row["priority"]["score"] for row in opportunities}
            frame["priority"] = [priority_lookup.get((row.customer_id, row.product)) for row in frame.itertuples()]
            for dimension in ("age_band", "income_band", "region"):
                audit = frame.join(source[[dimension]], on="customer_id")
                for (product, group), part in audit.groupby(["product", dimension], dropna=False):
                    fairness.append({"product": product, "dimension": dimension, "group": str(group),
                                     "n": len(part), "recommendation_rate": float(part.recommended.mean()),
                                     "abstention_rate": float(part.abstained.mean()), "mean_trust": float(part.trust.mean()),
                                     "validated_confidence_coverage": float(part.confidence.notna().mean()),
                                     "mean_validated_confidence": float(part.confidence.mean()) if part.confidence.notna().any() else None})
            for product, part in frame.groupby("product"):
                part = part[part.customer_id.map(split).eq("test") & part.probability.notna()].copy()
                part["outcome"] = part.customer_id.map(labels[product])
                n = max(1, int(np.ceil(len(part) * .1))) if len(part) else 0
                by_probability = part.sort_values(["probability", "customer_id"], ascending=[False, True]).head(n)
                by_trust = part.assign(score=.4 * part.probability + .15 * part.trust).sort_values(["score", "customer_id"], ascending=[False, True]).head(n)
                complete = part[part.priority.notna()]
                common_n = max(1, int(np.ceil(len(complete) * .1))) if len(complete) else 0
                full = complete.sort_values(["priority", "customer_id"], ascending=[False, True]).head(common_n)
                common_probability = complete.sort_values(["probability", "customer_id"], ascending=[False, True]).head(common_n)
                common_trust = complete.assign(score=.4 * complete.probability + .15 * complete.trust).sort_values(["score", "customer_id"], ascending=[False, True]).head(common_n)
                ranking[product] = {"held_out_n": len(part), "top_decile_n": n,
                                    "propensity_only_observed_rate": float(by_probability.outcome.mean()) if n else None,
                                    "propensity_plus_trust_observed_rate": float(by_trust.outcome.mean()) if n else None,
                                    "full_priority_observed_rate": float(full.outcome.mean()) if common_n else None,
                                    "complete_priority_n": len(complete), "common_cohort_top_decile_n": common_n,
                                    "common_cohort_propensity_only_observed_rate": float(common_probability.outcome.mean()) if common_n else None,
                                    "common_cohort_propensity_plus_trust_observed_rate": float(common_trust.outcome.mean()) if common_n else None,
                                    "limitation": "Full priority and common-cohort ablations use only rows with all validated components. If physical impact or confidence is absent, full priority remains unavailable. Synthetic outcomes do not establish causal impact."}
        audit_seconds = time.perf_counter() - audit_started
        print(f"{mode}: fairness and ablation {audit_seconds:.2f}s", flush=True)
        peak_rss_bytes = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * rss_scale)
        return {"provider_mode": mode, "startup_seconds": startup, "api": measurements,
                 "explanation_cache": metrics, "fairness": fairness, "ranking_ablation": ranking,
                 "distributions": distributions,
                 "evaluation_cohort": {"opportunity_rows": len(opportunities),
                                       "opportunity_customers": len({row["customer_id"] for row in opportunities}),
                                       "fairness_rows": len(records) if mode == "trained" else 0,
                                       "boundary": "All provider snapshots and products; no customer subsampling. Ranking uses the reported held-out and complete-priority cohorts."},
                 "portfolio_measurement_boundary": "Full-cohort scoring/ranking and audits read startup/summary-persisted decisions from isolated SQLite, omitting unused provenance snapshots. Includes cohort validation and the normal priority formula; excludes redundant inference/persistence. Not a fresh opportunities API latency measurement.",
                 "stage_seconds": {"application_build": build_seconds, "lifespan_startup": startup,
                                  "portfolio_scoring_and_ranking": scoring_seconds,
                                  "distributions": distributions_seconds, "fairness_and_ablation": audit_seconds,
                                  "total": time.perf_counter() - benchmark_started},
                 "memory": {"process_peak_rss_bytes": peak_rss_bytes,
                            "process_peak_rss_before_bytes": peak_rss_before,
                            "boundary": "resource.getrusage(RUSAGE_SELF).ru_maxrss in bytes; process lifetime high-water RSS including native buffers, not current RSS or an isolated per-mode peak. Fixture and trained runs share a process."},
                 "measurement_boundary": "Local in-process FastAPI TestClient without evaluator allocation tracing; includes full provider startup and normal SQLite decision persistence; excludes network transport, Streamlit render and live LLM latency."}


def main():
    with tempfile.TemporaryDirectory(prefix="greenpath-evaluation-") as folder:
        runs = [benchmark("fixture", Path(folder) / "fixture.sqlite3")]
        if (config.ARTIFACT_DIR / "models").is_dir():
            runs.append(benchmark("trained", Path(folder) / "trained.sqlite3"))
    report = {"version": "system-performance-v1", "synthetic_demo": True, "runs": runs,
              "live_llm_cost_per_1000": None, "offline_explanation_cost_per_1000": 0,
              "limitations": ["Synthetic labels and optional simulated outcomes do not establish real-world predictive accuracy.",
                              "No credentials or live provider were used; live cost and latency remain unmeasured.",
                              "Memory evaluations use isolated temporary databases; no demo customer history is changed."]}
    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (config.REPORTS_DIR / "system_performance.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print("Measured system performance and fairness: reports/system_performance.json")


if __name__ == "__main__":
    main()
