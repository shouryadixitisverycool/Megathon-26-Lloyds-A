"""Performance measurement boundaries, without trained allocation tracing."""

import json
from types import SimpleNamespace
import tracemalloc

import pytest

from greenpath.extensions import evaluate


@pytest.mark.parametrize(("platform", "scale"), [("darwin", 1), ("linux", 1024)])
def test_benchmark_memory_units_and_full_fixture_coverage(tmp_path, monkeypatch, platform, scale):
    monkeypatch.setattr(evaluate.sys, "platform", platform)
    monkeypatch.setattr(evaluate.resource, "getrusage", lambda who: SimpleNamespace(ru_maxrss=12345))
    create_app = evaluate.create_app
    applications = []

    def build(**kwargs):
        assert not tracemalloc.is_tracing()
        app = create_app(**kwargs)
        applications.append(app)
        return app

    def forbidden_trace(*args, **kwargs):
        pytest.fail("System evaluation must not enable allocation tracing")

    monkeypatch.setattr(evaluate, "create_app", build)
    monkeypatch.setattr(tracemalloc, "start", forbidden_trace)
    report = evaluate.benchmark("fixture", tmp_path / "performance.sqlite3")
    assert report["memory"]["process_peak_rss_bytes"] == 12345 * scale
    assert report["memory"]["process_peak_rss_before_bytes"] == 12345 * scale
    assert "process lifetime" in report["memory"]["boundary"]
    assert "python_peak_bytes" not in report["memory"]
    assert all(result["n"] == 5 for result in report["api"].values())
    assert report["explanation_cache"]["requests"] == 5
    assert report["explanation_cache"]["cache_hits"] == 4
    opportunities = applications[0].state.extension_service.opportunities()
    assert applications[0].state.memory_store.path == tmp_path / "performance.sqlite3"
    assert applications[0].state.extension_service.store is applications[0].state.memory_store
    snapshots = applications[0].state.snapshot_provider.list_snapshots()
    assert report["evaluation_cohort"]["opportunity_customers"] == len(snapshots)
    assert report["evaluation_cohort"]["opportunity_rows"] == len(opportunities)
    for product, distributions in report["distributions"].items():
        product_n = sum(row["product"] == product for row in opportunities)
        for distribution in distributions.values():
            assert distribution["n"] + distribution["missing_count"] == product_n
            assert sum(distribution["counts"]) == distribution["n"]
        for name, field in [("propensity", "probability"), ("validated_confidence", "confidence")]:
            values = [float(row["propensity"][field]) for row in opportunities
                      if row["product"] == product and row.get("propensity")
                      and row["propensity"].get(field) is not None
                      and (name != "validated_confidence" or row["propensity"].get("confidence_validated"))]
            if values:
                assert distributions[name]["mean"] == pytest.approx(sum(values) / len(values))
            else:
                assert distributions[name]["mean"] is None
    assert report["fairness"] == []
    assert report["ranking_ablation"] == {}
    assert all(seconds >= 0 for seconds in report["stage_seconds"].values())
    assert report["stage_seconds"]["total"] >= sum(
        seconds for stage, seconds in report["stage_seconds"].items() if stage != "total"
    )
    json.dumps(report, allow_nan=False)


@pytest.mark.parametrize("corruption", ["missing", "duplicate"])
def test_benchmark_rejects_incomplete_or_duplicate_cohorts(tmp_path, monkeypatch, corruption):
    class CorruptingClient(evaluate.TestClient):
        def get(self, path, **kwargs):
            response = super().get(path, **kwargs)
            if path == "/explanations/metrics":
                with self.app.state.memory_store.connect() as db:
                    if corruption == "missing":
                        db.execute("DELETE FROM decisions WHERE rowid = (SELECT MIN(rowid) FROM decisions)")
                    else:
                        db.execute("""INSERT INTO decisions SELECT id || '-duplicate',
                                      customer_id, product, timestamp, payload FROM decisions LIMIT 1""")
            return response

    monkeypatch.setattr(evaluate, "TestClient", CorruptingClient)
    with pytest.raises(ValueError, match="every snapshot/product exactly once"):
        evaluate.benchmark("fixture", tmp_path / "performance.sqlite3")
