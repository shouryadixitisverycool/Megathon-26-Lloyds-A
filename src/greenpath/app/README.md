# Greenr presentation layer

Run the API and UI together with `make app`. To run only the UI against an existing API:

```bash
uv run --locked streamlit run src/greenpath/app/main.py
```

`GREENPATH_API_URL` defaults to `http://127.0.0.1:8000`. It accepts HTTP/HTTPS URLs without embedded credentials. The entrypoint uses absolute package imports and also works from an installed wheel. No domain services, calculators, demo providers, models, or contract mirrors are imported by the UI.

The customer view requests customer, recommendation, and one selected product explanation through HTTP. It shows all six states, independent Trust and validated confidence, evidence, cutoff and versions, factor sources and boundaries, assumptions and exclusions. Decimal strings are parsed explicitly; unavailable impact stays unavailable, and zero or negative impact is preserved. GP-002 has a sidebar shortcut for responsible abstention. The portfolio view requests server-filtered summaries and historical observations, with product, region, segment and monthly charts. It never computes a carbon total across products or invents historical scores.

Responses cache for 15 seconds with a maximum of 128 entries, keyed by API URL, route and query filters. Refresh data clears that cache. An uncached health request precedes each view, so an unreachable service cannot show prior cached results as current results. Region changes reset incompatible segment filters; Clear filters restores the full portfolio. Only the selected workspace and explanation request run.

`uv run --locked pytest tests/app` covers JSON/Decimal handling, API errors, all recommendation states, customer switching, selected Why details, validated confidence, portfolio charts and filters, refresh, and removal of prior results after failures with Streamlit AppTest and mocked HTTP responses. UI tests do not exercise browser rendering; the main thread owns browser smoke verification.

The design uses native Streamlit components and the project theme, with restrained forest/cream charts. It follows the installed Streamlit 1.65.0 bundled `developing-with-streamlit` skill, discovered through `streamlit skills --help` and read directly from the package. Relevant design, layout, session-state, dashboard and testing references were read. No third-party skill was installed, no upload code ran, and local `streamlit docs` verified current widget and chart APIs. Greenr retains Plotly as specified in the implementation plan.

During the later manual transfer, replace the local mirrors with Agent A's canonical contracts. The HTTP route and JSON fields are those frozen in `PARALLEL_HANDOFF.md`.
