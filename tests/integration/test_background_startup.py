"""History latency must not block a ready customer API."""

from threading import Event
from time import monotonic, sleep

from fastapi.testclient import TestClient

from greenpath.api.main import create_app
from greenpath.demo.providers import DemoRepository


def test_background_history_does_not_block_health_or_customer(tmp_path):
    entered, release = Event(), Event()

    class Repository(DemoRepository):
        mode = "trained"
        background_warmup = True

        def prepare_current(self):
            self.current_ready = True

        def list_history(self):
            entered.set()
            assert release.wait(10)
            return super().list_history()

    repository = Repository()
    app = create_app(repository, memory_path=tmp_path / "memory.sqlite3")
    with TestClient(app) as client:
        try:
            assert entered.wait(2)
            assert repository.current_ready
            assert client.get("/health").json()["status"] == "ok"
            assert client.get("/customers/GP-001/recommendations").status_code == 200
            for path in ("/portfolio/summary", "/portfolio/trends"):
                response = client.get(path)
                assert response.status_code == 503
                assert response.json()["detail"]["code"] == "PORTFOLIO_PREPARING"
                assert response.headers["Retry-After"] == "2"
        finally:
            release.set()
        deadline = monotonic() + 5
        while app.state.portfolio_warmup["summary"] == "pending" and monotonic() < deadline:
            sleep(0.01)
        assert app.state.portfolio_warmup == {"history": "ready", "summary": "ready"}
        assert client.get("/portfolio/summary").status_code == 200
        assert client.get("/portfolio/trends").status_code == 200


def test_failed_background_history_is_explicit_not_empty_success(tmp_path):
    class Repository(DemoRepository):
        mode = "trained"
        background_warmup = True

        def prepare_current(self):
            pass

        def list_history(self):
            raise ValueError("corrupt history")

    app = create_app(Repository(), memory_path=tmp_path / "memory.sqlite3")
    with TestClient(app) as client:
        deadline = monotonic() + 2
        while app.state.portfolio_warmup["history"] == "pending" and monotonic() < deadline:
            sleep(0.01)
        assert client.get("/health").json()["status"] == "ok"
        response = client.get("/portfolio/trends")
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "PORTFOLIO_FAILED"
