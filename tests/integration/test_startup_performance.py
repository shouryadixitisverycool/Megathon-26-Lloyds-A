"""Durable startup batching, immutable cache boundaries and real launcher smoke."""

import json
import os
import signal
import socket
import subprocess
import sys
import time
from datetime import timedelta
from urllib.error import URLError
from urllib.request import urlopen

import pytest
from fastapi.testclient import TestClient

from greenr import config
from greenr.api.main import create_app
from greenr.demo.providers import DemoRepository
from greenr.demo import run
from greenr.extensions.store import MemoryStore
from greenr.recommendation.service import RecommendationService


def decision():
    repo = DemoRepository()
    return RecommendationService(repo, repo, repo).recommendations("GP-001")[0]


def test_persisted_cache_checks_collisions_and_defends_nested_evidence(tmp_path, monkeypatch):
    store = MemoryStore(tmp_path / "memory.sqlite3")
    original = decision()
    first = store.save_recommendation(original)
    first.provenance["snapshot"]["features"].clear()
    with monkeypatch.context() as patch:
        def forbidden():
            pytest.fail("Known persisted evidence must not reconnect or reparse")
        patch.setattr(store, "connect", forbidden)
        patch.setattr(type(original), "model_validate_json", forbidden)
        repeated = store.save_recommendation(original.model_copy(update={
            "timestamp": original.timestamp + timedelta(seconds=1),
        }))
        assert repeated.timestamp == original.timestamp
        assert repeated.provenance["snapshot"]["features"]
        for changes in ({"reason_codes": ("CHANGED",)}, {"customer_id": "other"},
                        {"provenance": {"snapshot": {"features": {}}}}):
            with pytest.raises(ValueError, match="immutable evidence"):
                store.save_recommendation(original.model_copy(update=changes))
    fresh = MemoryStore(store.path)
    assert fresh.save_recommendation(original) == repeated
    with pytest.raises(ValueError, match="immutable evidence"):
        fresh.save_recommendation(original.model_copy(update={"reason_codes": ("CHANGED",)}))


def test_cache_entries_publish_only_after_commit(tmp_path):
    store = MemoryStore(tmp_path / "memory.sqlite3")
    original = decision()
    with pytest.raises(RuntimeError):
        with store.transaction():
            with store.transaction():
                store.save_recommendation(original)
            assert store.save_recommendation(original) == original
            raise RuntimeError("rollback")
    assert store.get_recommendation(original.decision_id) is None
    assert not store._recommendations
    with store.transaction():
        store.save_recommendation(original)
    assert MemoryStore(store.path).get_recommendation(original.decision_id)


def test_launcher_default_explicitly_allows_full_trained_warmup(monkeypatch):
    assert run._wait_for_api.__defaults__ == (300,)
    monkeypatch.setattr(run, "_require_free_port", lambda port: None)
    processes = []

    class Process:
        def __init__(self, *args, **kwargs):
            self.stopped = False
            processes.append(self)

        def poll(self):
            return 0 if self.stopped else None

        def terminate(self):
            self.stopped = True

        def wait(self, **kwargs):
            return 0

    def wait(process, base_url, timeout):
        assert timeout == 300
        raise KeyboardInterrupt

    monkeypatch.setattr(run.subprocess, "Popen", Process)
    monkeypatch.setattr(run, "_wait_for_api", wait)
    assert run.main([]) == 0
    assert len(processes) == 1 and processes[0].stopped


def test_trained_warmup_persists_cohort_in_one_transaction(tmp_path, monkeypatch):
    repo = DemoRepository()
    repo.mode = "trained"
    service = RecommendationService(repo, repo, repo)
    calls = []
    original = service.recommendations

    def counted(customer_id):
        calls.append(customer_id)
        return original(customer_id)

    monkeypatch.setattr(service, "recommendations", counted)
    app = create_app(repo, recommendation_service=service, memory_path=tmp_path / "memory.sqlite3")
    statements = []
    connect = app.state.memory_store.connect
    from contextlib import contextmanager

    @contextmanager
    def traced():
        with connect() as db:
            db.set_trace_callback(statements.append)
            yield db

    monkeypatch.setattr(app.state.memory_store, "connect", traced)
    with TestClient(app) as client:
        assert calls == [s.customer_id for s in repo.list_snapshots()]
        assert statements.count("BEGIN IMMEDIATE") == 1
        assert statements.count("COMMIT") == 1
        assert client.get("/portfolio/summary").status_code == 200
        assert len(calls) == len(repo.list_snapshots())
        with app.state.memory_store.connect() as db:
            assert db.execute("SELECT COUNT(*) FROM decisions").fetchone()[0] == 4 * len(calls)


def test_summary_scoring_failure_rolls_back_the_cohort(tmp_path, monkeypatch):
    repo = DemoRepository()
    service = RecommendationService(repo, repo, repo)
    calls = []
    original = service.recommendations

    def fail_on_second_customer(customer_id):
        calls.append(customer_id)
        if len(calls) == 2:
            raise RuntimeError("Injected scoring failure")
        return original(customer_id)

    monkeypatch.setattr(service, "recommendations", fail_on_second_customer)
    app = create_app(repo, recommendation_service=service, memory_path=tmp_path / "memory.sqlite3")
    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get("/portfolio/summary").status_code == 500

    assert len(calls) == 2
    assert not app.state.memory_store._recommendations
    with app.state.memory_store.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM decisions").fetchone()[0] == 0


@pytest.mark.parametrize("mode", ["fixture", "trained"])
def test_real_launcher_startup_and_owned_cleanup(tmp_path, mode):
    if mode == "trained" and os.environ.get("GREENR_TEST_REAL_TRAINED") != "1":
        pytest.skip("Set GREENR_TEST_REAL_TRAINED=1 for full deployed artifact warmup")
    data = tmp_path / "data"
    data.mkdir()
    if mode == "trained":
        for name in ("processed", "artifacts", "synthetic"):
            (data / name).symlink_to(config.DATA_DIR / name, target_is_directory=True)
        (tmp_path / "reports").symlink_to(config.REPORTS_DIR, target_is_directory=True)
    ports = []
    for _ in range(2):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            ports.append(listener.getsockname()[1])
    environment = dict(os.environ, GREENR_PROVIDER=mode, GREENR_WORKSPACE=str(tmp_path))
    started = time.monotonic()
    process = subprocess.Popen([sys.executable, "-m", "greenr.demo.run",
                                "--api-port", str(ports[0]), "--ui-port", str(ports[1])], env=environment)
    try:
        deadline = started + 310
        api_seconds = None
        while time.monotonic() < deadline:
            assert process.poll() is None, "Launcher exited before API/UI readiness"
            try:
                with urlopen(f"http://127.0.0.1:{ports[0]}/health", timeout=1) as response:
                    assert json.load(response)["provider_mode"] == mode
                if api_seconds is None:
                    api_seconds = time.monotonic() - started
                with urlopen(f"http://127.0.0.1:{ports[1]}/_stcore/health", timeout=1) as response:
                    assert response.status == 200
                break
            except (URLError, OSError):
                time.sleep(.2)
        else:
            pytest.fail("Launcher readiness deadline exceeded")
        print(f"{mode} launcher: API {api_seconds:.2f}s, UI {time.monotonic() - started:.2f}s", flush=True)
        with urlopen(f"http://127.0.0.1:{ports[0]}/customers/{'C10001' if mode == 'trained' else 'GP-001'}/recommendations", timeout=30) as response:
            recommendations = json.load(response)["recommendations"]
        assert len(recommendations) == 4
        store = MemoryStore(data / "greenr.sqlite3")
        assert all(store.get_recommendation(row["decision_id"]) for row in recommendations)
    finally:
        process.send_signal(signal.SIGTERM)
        try:
            process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
    assert process.returncode == 0
    for port in ports:
        with socket.socket() as connection:
            assert connection.connect_ex(("127.0.0.1", port)) != 0
