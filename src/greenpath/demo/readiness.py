"""Evidence-backed showcase selection, independent of persistence and explanations.

Run after train/predict: python -m greenpath.demo.readiness
Pipeline callers may pass their scored DataFrame to generate_readiness.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import joblib
import pandas as pd

from greenpath import config
from greenpath.contracts.enums import Product

SCHEMA_VERSION = "demo-readiness-v1"
SEARCH_LIMIT = 8
REPORT_PATH = config.REPORTS_DIR / "demo_readiness.json"


def artifact_signature(repository) -> str:
    """Fingerprint loaded objects, not just mutable on-disk model version labels."""
    rt = getattr(repository, "runtime", None)
    if rt is None:
        return joblib.hash((SCHEMA_VERSION, repository.mode, repository.version))
    cutoff = rt.snapshots.default_cutoff
    from greenpath.recommendation.service import TRAINED_PRODUCT_RULES

    return joblib.hash((SCHEMA_VERSION, cutoff, rt.snapshots.frames[cutoff],
                        rt.bundles, rt.confidence, rt.trust,
                        getattr(repository.scenario_provider, "rows", None),
                        repository.impact_calculators, dict(TRAINED_PRODUCT_RULES)))


def report_hash(report: dict) -> str:
    payload = {key: value for key, value in report.items() if key != "report_sha256"}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def read_report(path: Path, signature: str) -> dict | None:
    try:
        report = json.loads(path.read_text())
        if (report.get("schema_version") == SCHEMA_VERSION
                and report.get("artifact_signature") == signature
                and report.get("confidence_decisions_sha256") == confidence_decisions_hash()
                and report.get("report_sha256") == report_hash(report)):
            return report
    except (OSError, ValueError, TypeError):
        pass
    return None


def confidence_decisions_hash() -> str | None:
    path = config.ARTIFACT_DIR / "confidence" / "decisions.json"
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def generate_readiness(repository, *, scored: pd.DataFrame | None = None,
                       service=None, signature: str | None = None) -> dict:
    """Scan cached scores once, then validate only deterministic shortlist customers.

    Missing candidates mean not found in a bounded search, not population-wide
    proof of absence. Fixtures never qualify as trained/validated showcases.
    """
    from greenpath.recommendation.service import RecommendationService

    signature = signature or artifact_signature(repository)
    trained = getattr(repository, "mode", None) == "trained"
    rt = getattr(repository, "runtime", None)
    cutoff = rt.snapshots.default_cutoff if rt else None
    coverage_source = "pipeline scored artifact (shortlist only; selected customers live-checked)" if scored is not None else "served current score cache"
    release_path = config.ARTIFACT_DIR / "confidence" / "decisions.json"
    release = json.loads(release_path.read_text()) if trained and release_path.is_file() else {}
    if scored is None and trained:
        snapshots, propensities = repository._at(cutoff)
        rows = []
        for (cid, product), result in propensities.items():
            trust = snapshots[cid].product_trust[product]
            rows.append({"customer_id": cid, "product": product.value,
                         "in_model_population": result.in_model_population,
                         "above_threshold": result.probability is not None and result.probability >= result.decision_threshold,
                         "confidence_status": "VALIDATED" if result.confidence_validated else "SUPPRESSED",
                         "trust_status": trust.status})
        scored = pd.DataFrame(rows)
    elif scored is not None:
        scored = scored[pd.to_datetime(scored["cutoff"]).dt.date == cutoff].copy()
    else:
        snapshots = {s.customer_id: s for s in repository.list_snapshots()}
        scored = pd.DataFrame([{"customer_id": cid, "product": p.value,
                                "in_model_population": True, "above_threshold": True,
                                "confidence_status": "SUPPRESSED", "trust_status": s.trust.status}
                               for cid, s in snapshots.items() for p in Product])

    selected_ids = set()
    shortlists = {}
    coverage = {}
    for product in Product:
        frame = scored[scored["product"] == product.value].sort_values("customer_id", kind="stable")
        in_pop = frame["in_model_population"].fillna(False).astype(bool)
        validated = frame["confidence_status"] == "VALIDATED"
        above = frame["above_threshold"].fillna(False).astype(bool)
        support = frame[in_pop & above].sort_values("confidence_status", kind="stable", ascending=False)
        ids = list(support["customer_id"].iloc[:SEARCH_LIMIT])
        for mask in (~in_pop, ~above, frame["trust_status"].isin(["CONFLICT", "LOW", "INSUFFICIENT", "LIMITED", "OOD"])):
            ids.extend(frame.loc[mask, "customer_id"].iloc[:SEARCH_LIMIT])
        # Personas are source rows, not asserted outcomes or validated fixtures.
        ids.extend(cid for cid in config.DEMO_PERSONA_IDS if cid in set(frame["customer_id"]))
        shortlists[product] = list(dict.fromkeys(ids))
        selected_ids.update(ids)
        coverage[product.value] = {"scored_customers": len(frame), "in_model_population": int(in_pop.sum()),
                                   "validated_confidence": int((in_pop & validated).sum()),
                                   "above_threshold": int((in_pop & above).sum())}

    if service is None and trained and scored is not None and not repository._cache:
        # Offline generation uses the pipeline's full-cohort scored artifact for
        # coverage and a narrow runtime for live decision/evidence/impact checks.
        from dataclasses import replace
        from greenpath.demo.artifacts import ArtifactRepository
        from greenpath.pipelines.snapshot_provider import Customer360SnapshotProvider

        frame = rt.snapshots.frames[cutoff]
        narrow = Customer360SnapshotProvider({cutoff: frame.loc[frame.index.intersection(sorted(selected_ids))]},
                                             default_cutoff=cutoff)
        repository = ArtifactRepository(replace(rt, snapshots=narrow), repository.scenario_provider)
    service = service or RecommendationService(repository, repository, repository, include_provenance=False)
    decisions = {cid: service.recommendations(cid) for cid in sorted(selected_ids)}
    products = {}
    examples = {}
    for product in Product:
        checked = [r for cid in shortlists[product] for r in decisions[cid] if r.product == product]
        supported = [r for r in checked if r.state.value == "RECOMMEND"]
        ready = [r for r in supported if trained and r.propensity and r.propensity.source_result
                 and r.propensity.confidence_validated and r.propensity.confidence is not None
                 and r.evidence and r.impact.status.value == "AVAILABLE" and r.impact.evidence]
        chosen = ready[0] if ready else supported[0] if supported else None
        limitation = rt.confidence.limitations.get(product) if rt else "Fixture mode is not trained model evidence."
        missing = []
        if not trained:
            missing.append("Trained model evidence is absent; fixture probabilities are not validation.")
        if not ready:
            if not coverage[product.value]["validated_confidence"]:
                missing.append(limitation or "No in-population customer has validated confidence.")
            if chosen is None:
                missing.append("No supported customer found in the bounded live search.")
            elif chosen.impact.status.value != "AVAILABLE":
                missing.extend(i.message for i in chosen.impact.issues)
                if not chosen.impact.issues:
                    missing.append("Supported customer has no available defensible impact estimate.")
            else:
                missing.append("No live-checked customer meets all trained confidence, evidence and impact gates.")
        products[product.value] = {"status": "READY" if ready else "BLOCKED", "coverage": coverage[product.value],
                                   "candidate": _candidate(chosen) if chosen else None,
                                   "missing_features": missing, "confidence_limitation": limitation,
                                   "live_checked_customers": len(checked)}
        decision = release.get(product.value, {})
        matches_loaded = bool(rt and decision
                              and bool(decision.get("surfaced")) == rt.confidence.validated.get(product, False)
                              and decision.get("limitation") == rt.confidence.limitations.get(product))
        products[product.value]["confidence_release_evidence"] = decision if matches_loaded else None
        for state, label in (("INSUFFICIENT_INFORMATION", "abstention"),
                             ("CONFLICT_REQUIRES_REVIEW", "conflict"),
                             ("NOT_APPLICABLE", "already_adopted"),
                             ("SUPPRESSED", "suppressed"), ("DO_NOT_RECOMMEND", "below_threshold")):
            matches = [r for r in checked if r.state.value == state
                       and (label != "already_adopted" or "ALREADY_ADOPTED" in r.reason_codes)]
            if matches and label not in examples:
                examples[label] = _candidate(matches[0])
    report = {"schema_version": SCHEMA_VERSION, "artifact_signature": signature,
              "provider_mode": getattr(repository, "mode", "injected"),
              "source_version": repository.version, "feature_cutoff": str(cutoff) if cutoff else None,
              "population_customers": int(scored["customer_id"].nunique()),
              "coverage_source": coverage_source,
              "confidence_decisions_sha256": confidence_decisions_hash() if trained else None,
              "confidence_source": "Loaded confidence release decisions and live source_result.confidence; never trust or propensity.",
              "selection": "Stable customer-ID order, validated scores first; bounded live search per product/category.",
              "live_checked_customers": len(decisions), "products": products, "examples": examples,
              "missing_features": [f"No live-checked {label} example found." for label in
                                   ("abstention", "conflict", "already_adopted", "suppressed", "below_threshold") if label not in examples],
              "limitation": "Synthetic model evidence only. No credit eligibility, approval, marketing permission or realized carbon saving is established."}
    report["status"] = "READY" if all(p["status"] == "READY" for p in products.values()) and not report["missing_features"] else "BLOCKED"
    report["report_sha256"] = report_hash(report)
    return report


def _candidate(decision) -> dict:
    from greenpath.recommendation.service import decision_evidence

    return decision_evidence({"customer_id": decision.customer_id, "product": decision.product.value,
            "state": decision.state.value, "feature_cutoff": decision.feature_cutoff.isoformat(),
            "propensity": decision.propensity.model_dump(mode="json") if decision.propensity else None,
            "reason_codes": list(decision.reason_codes),
            "evidence": [e.model_dump(mode="json") for e in decision.evidence],
            "impact": decision.impact.model_dump(mode="json"), "rules_version": decision.rules_version})


def main() -> None:
    from greenpath.demo.artifacts import ArtifactRepository
    from greenpath.pipelines.runtime import load_runtime
    from greenpath.pipelines.scenario_provider import ScenarioProvider

    rt = load_runtime(cutoffs=[config.FEATURE_CUTOFF])
    scenario_path = config.RAW_DIR / "scenario_evidence.parquet"
    scenarios = ScenarioProvider(pd.read_parquet(scenario_path)) if scenario_path.is_file() else None
    repository = ArtifactRepository(rt, scenarios)
    scores_path = config.ARTIFACT_DIR / "portfolio_scores.parquet"
    scores = pd.read_parquet(scores_path) if scores_path.is_file() else None
    if scores is not None:
        current = scores[pd.to_datetime(scores["cutoff"]).dt.date == config.FEATURE_CUTOFF]
        # A scored artifact is a shortlist, never proof that current models pass.
        expected = {(p.value, b.model_version, b.calibration_version) for p, b in rt.bundles.items()}
        actual = set(current[["product", "model_version", "calibration_version"]].itertuples(index=False, name=None))
        if actual != expected or set(current["customer_id"]) != set(rt.snapshots.list_customer_ids()):
            scores = None
        else:
            for product, bundle in rt.bundles.items():
                rows = current[current["product"] == product.value]
                expected_validated = rows["in_model_population"] & rt.confidence.validated.get(product, False)
                if (not (rows["threshold"] == bundle.threshold).all()
                        or not ((rows["confidence_status"] == "VALIDATED") == expected_validated).all()):
                    scores = None
                    break
    report = generate_readiness(repository, scored=scores)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(f"Showcase readiness: {report['status']}; population={report['population_customers']}; live checks={report['live_checked_customers']}")
    print(REPORT_PATH)


if __name__ == "__main__":
    main()
