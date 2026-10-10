"""Measured local API/cache performance and decision-level fairness evidence."""

import json
from pathlib import Path
import tempfile
import time

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from greenpath import config
from greenpath.api.main import create_app
from greenpath.extensions.store import MemoryStore


def benchmark(mode, memory_path):
    application = create_app(provider_mode=mode)
    application.state.extension_service.store = MemoryStore(memory_path)
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
                ranking[product] = {"held_out_n": len(part), "top_decile_n": n,
                                    "propensity_only_observed_rate": float(by_probability.outcome.mean()) if n else None,
                                    "propensity_plus_trust_observed_rate": float(by_trust.outcome.mean()) if n else None,
                                    "full_priority_observed_rate": None,
                                    "limitation": "Full p40/c25/i20/t15 priority unavailable because proposed physical impact is absent. The second ranking is an explicitly separate two-component ablation, not the full priority formula."}
        return {"provider_mode": mode, "startup_seconds": startup, "api": measurements,
                "explanation_cache": metrics, "fairness": fairness, "ranking_ablation": ranking,
                "measurement_boundary": "Local in-process FastAPI TestClient; excludes network transport, Streamlit render and live LLM latency."}


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
