"""Opt-in current-artifact UI smoke, bounded to the demo personas."""

import os
import socket
import threading
import time

import httpx
import pandas as pd
import pytest
import streamlit as st
import uvicorn

from test_app import APP, displayed
from streamlit.testing.v1 import AppTest


@pytest.mark.skipif(os.getenv("GREENR_APP_TRAINED_SMOKE") != "1", reason="Opt-in trained artifact HTTP smoke")
def test_current_trained_demo_over_http(tmp_path, monkeypatch):
    monkeypatch.setenv("GREENR_PROVIDER", "fixture")
    monkeypatch.setenv("GREENR_LLM_API_KEY", "")
    from greenr import config
    from greenr.api.main import create_app
    from greenr.demo.artifacts import ArtifactRepository
    from greenr.pipelines.runtime import load_runtime
    from greenr.pipelines.scenario_provider import ScenarioProvider
    from greenr.pipelines.snapshot_provider import customer360_path

    cutoffs = [c for c in config.TREND_CUTOFFS if customer360_path(c).is_file()]
    runtime = load_runtime(cutoffs=cutoffs)
    for cutoff, frame in runtime.snapshots.frames.items():
        runtime.snapshots.frames[cutoff] = frame.loc[frame.index.isin(config.DEMO_PERSONA_IDS)]
    repository = ArtifactRepository(runtime, scenario_provider=ScenarioProvider(
        pd.read_parquet(config.RAW_DIR / "scenario_evidence.parquet")))
    repository._outcome_path = config.ARTIFACT_DIR / "portfolio_scores.parquet"
    api = create_app(repository, memory_path=tmp_path / "ui-smoke.sqlite3")
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(api, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    monkeypatch.setenv("GREENR_API_URL", f"http://127.0.0.1:{port}")
    st.cache_data.clear()
    thread.start()
    try:
        deadline = time.monotonic() + 60
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.1)
        assert server.started, "Bounded trained API failed to warm"
        app = AppTest.from_file(str(APP), default_timeout=40).run()
        assert not app.exception
        assert not app.error
        assert app.selectbox(key="customer_id").value == "C10001"
        assert "Data source: trained" in displayed(app.sidebar)
        assert len([m for m in app.metric if m.label == "Calibrated propensity · synthetic model"]) == 4
        assert any("References" in frame.value for frame in app.dataframe)
        assert app.json
        for product in ("EV_FINANCE", "GREEN_HOME", "SOLAR_FINANCE", "PAPERLESS_BANKING"):
            app.selectbox(key="why_product").select(product).run()
            assert not app.exception
            assert not app.error
            assert "Explanation source: template" in displayed(app)
        app.toggle(key="scenario_open").set_value(True).run()
        assert not app.exception
        assert not app.error
        for label, value in (("Annual paper statements", 12), ("Sheets per statement", 2),
                             ("Statements avoided, fraction from 0 to 1", 1.0)):
            next(widget for widget in app.number_input if widget.label == label).set_value(value)
        next(button for button in app.button if button.label == "Calculate UK scenario").click().run()
        assert not app.exception
        assert not app.error
        assert next(metric for metric in app.metric if metric.label == "Paper statements avoided").value == "12.0"
        assert next(metric for metric in app.metric if metric.label == "Paper sheets avoided").value == "24.0"
        app.button(key="abstention").click().run()
        assert app.selectbox(key="customer_id").value == "C10005"
        assert not app.exception
        assert not app.error
        app.radio(key="workspace").set_value("Portfolio").run()
        assert not app.exception
        assert not app.error
        assert len(app.get("plotly_chart")) == 4
        assert "Physical potential and evidence quality" in [s.value for s in app.subheader]
        frames = [frame.value for frame in app.dataframe]
        assert any("observed_conversion_rate" in frame for frame in frames)
        region = next(value for value in app.selectbox(key="region").options if value != "All")
        app.selectbox(key="region").select(region).run()
        assert not app.exception
        assert not app.error
        assert len(app.get("plotly_chart")) == 4
        for workspace in ("Planning", "Governance", "Relationship Manager"):
            app.radio(key="workspace").set_value(workspace).run()
            assert not app.exception
            assert not app.error
        metrics = httpx.get(os.environ["GREENR_API_URL"] + "/explanations/metrics").json()
        assert metrics["provider_attempts"] == 0
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        st.cache_data.clear()
