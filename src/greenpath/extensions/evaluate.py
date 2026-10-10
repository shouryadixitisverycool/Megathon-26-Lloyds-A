"""Measured local API/cache performance and decision-level fairness evidence."""

import json
from pathlib import Path
import tempfile
import time
import tracemalloc

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from greenpath import config
from greenpath.api.main import create_app
from greenpath.extensions.store import MemoryStore


def benchmark(mode, memory_path):
    tracing_started = not tracemalloc.is_tracing()
    if tracing_started:
        tracemalloc.start()
    try:
        return _benchmark(mode, memory_path, tracing_started)
    finally:
        if tracing_started:
            tracemalloc.stop()


def _benchmark(mode, memory_path, tracing_started):
    build_started = time.perf_counter()
    application = create_app(provider_mode=mode)
    application.state.extension_service.store = MemoryStore(memory_path)
    build_seconds = time.perf_counter() - build_started
    started = time.perf_counter()
    with TestClient(application) as client:
        startup = time.perf_counter() - started
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
        metrics = client.get("/explanations/metrics").json()
        fairness = []
        ranking = {}
        scoring_started = time.perf_counter()
        opportunities = application.state.extension_service.opportunities()
        scoring_seconds = time.perf_counter() - scoring_started
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
        audit_started = time.perf_counter()
        if mode == "trained":
            source = pd.read_parquet(config.RAW_DIR / "customers.parquet").set_index("customer_id")
            labels = pd.read_parquet(config.PROCESSED_DIR / "labels.parquet")
            split = pd.read_csv(config.PROCESSED_DIR / "split_manifest.csv", dtype=str).set_index("customer_id")["split"]
            records = []
            for snapshot in application.state.snapshot_provider.list_snapshots():
                for row in application.state.recommendation_service.recommendations(snapshot.customer_id):
                    records.append({"customer_id": snapshot.customer_id, "product": row.product.value,
                                    "recommended": row.state.value == "RECOMMEND",
                                    "abstained": row.state.value in {"INSUFFICIENT_INFORMATION", "CONFLICT_REQUIRES_REVIEW"},
                                    "trust": float(row.trust.score),
                                    "confidence": float(row.propensity.confidence) if row.propensity and row.propensity.confidence_validated else np.nan,
                                    "probability": float(row.propensity.probability) if row.propensity and row.propensity.probability is not None else np.nan})
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
        current_bytes, peak_bytes = tracemalloc.get_traced_memory()
        return {"provider_mode": mode, "startup_seconds": startup, "api": measurements,
                 "explanation_cache": metrics, "fairness": fairness, "ranking_ablation": ranking,
                "distributions": distributions,
                "stage_seconds": {"application_build": build_seconds, "lifespan_startup": startup,
                                  "portfolio_scoring_and_ranking": scoring_seconds, "fairness_and_ablation": time.perf_counter() - audit_started},
                "memory": {"python_current_bytes": current_bytes, "python_peak_bytes": peak_bytes,
                           "boundary": "tracemalloc Python allocations; excludes native model buffers and process RSS",
                           "isolated_trace": tracing_started},
                "measurement_boundary": "Local in-process FastAPI TestClient with Python allocation tracing enabled; excludes network transport, Streamlit render and live LLM latency."}


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
