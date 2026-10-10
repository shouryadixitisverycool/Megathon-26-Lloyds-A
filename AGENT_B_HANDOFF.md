# Agent B handoff, points 1–6

All six Agent B points are implemented. EV, Green Home, and Solar use the frozen deterministic formulas. Paperless returns `UNAVAILABLE` with a null carbon value until a reviewed paper/digital method exists. Recommendation rules, grounded explanations, FastAPI routes, and HTTP-only Streamlit views run against six versioned synthetic personas. Agent A's data and ML modules remain absent.

## Setup and use

Requires Python 3.12 and `uv`. Run from this repository:

```bash
make setup
make all
make app
```

`make test` runs all implemented tests. `make all` also writes the offline explanation and integrated scenario reports under `reports/`. It is an Agent B gate; Agent A training and held-out prediction generation are pending. `make app` starts the API at `http://127.0.0.1:8000` and UI at `http://127.0.0.1:8501`, and stops its owned processes on Ctrl+C or termination. `GREENPATH_API_URL` is optional for a separately launched UI. See `README.md` for the five-minute walkthrough and alternate ports.

`uv.lock` pins the complete dependency resolution. Verified versions are Python 3.12.13, Pydantic 2.14.0, pydantic-core 2.50.0, pytest 9.1.1, FastAPI 0.143.0, Uvicorn 0.54.0, HTTPX 0.28.1, Streamlit 1.65.0, and Plotly 6.9.0. The wheel build backend is pinned to hatchling 1.27.0. No credentials are required. Calculation and default explanations perform no network calls; Streamlit calls the local API through HTTP.

Verification on 2026-10-10: 447 tests passed, including 152 impact, 170 recommendation, 65 explanation, 20 API, 37 UI, and 3 provider tests. `uv lock --check` passed and `uv build --wheel` succeeded. Offline reports passed 18/18 adversarial explanation cases and 24/24 integrated persona/product scenarios. Browser smoke checks used the real API and UI for supported and abstaining customers and portfolio charts, with no horizontal overflow. API tests and Streamlit AppTests verified filters and reset behavior; preview dropdown automation timed out. Available values preserve Decimal strings, unavailable values remain null, and confidence stays suppressed in the default fixtures. An upstream Starlette TestClient deprecation warning does not affect the checks.

The final wheel was installed with locked runtime dependencies in an isolated environment outside the repository. Packaged fixtures and UI entrypoint were present, 24 persona/product explanation HTTP routes matched the expected six states, the 18 adversaries passed, and portfolio summary/trends passed. Launcher termination stopped both owned child processes without leaving the demo ports occupied.

The final UI additionally passed Streamlit AppTest against the running HTTP API, including customer/Why details, responsible abstention, portfolio charts, chronological month labels, intersecting region/segment/product filters, dependent segment reset, and clearing filters.

Example using the synthetic EV fixture:

```bash
uv run --locked python - <<'PY'
import json
from pathlib import Path
from greenpath.impact import EVImpactCalculator, display_value

payload = json.loads(Path('tests/impact/fixtures/ev.json').read_text())
result = EVImpactCalculator().calculate(payload)
print(result.model_dump_json(indent=2))
print('Display:', display_value(result), result.units)
PY
```

Calculators accept an input mapping, their Pydantic input model, or `None`, and always return the same result shape for validated or unavailable customer evidence. Direct construction of an invalid Pydantic input raises `ValidationError`; pass a raw mapping to `calculate` to obtain an unavailable result instead. A registry is available through `build_registry()` and maps the four product enums to the narrow calculator port.

The default timestamp is the current timezone-aware UTC time. Inject a `clock` into a calculator or the registry for reproducible result fixtures. Values are `Decimal`; JSON retains them as decimal strings. `display_value` rounds to one decimal using half-up rounding without changing the result.

## Owned files

- `CARBON_METHODS.md` and `src/greenpath/impact/factors/carbon_factors.v1.json`: frozen methods and factor provenance.
- `src/greenpath/impact/ev.py`, `green_home.py`, `solar.py`, and `paperless.py`: product-specific calculators.
- `src/greenpath/impact/inputs.py`: impact-specific evidence, quantity, context, and product input models.
- `src/greenpath/impact/common.py`: shared evidence checks, decimal arithmetic context, result construction, and display rounding.
- `src/greenpath/impact/catalogue.py`: bundled-factor loader and integrity checks. The SHA-256 pins the exact catalogue bytes; modifications fail closed until explicitly versioned and reviewed.
- `src/greenpath/impact/registry.py` and `__init__.py`: calculator registration and public imports.
- `src/greenpath/impact/_contract_mirror.py` and `_port_mirror.py`: provisional, replaceable local mirrors.
- `src/greenpath/_product_contract_mirror.py` and `_product_port_mirror.py`: provisional customer, Trust, propensity, recommendation, explanation, portfolio, history, and provider contracts.
- `src/greenpath/recommendation/`: six-state decision engine, product relevance rules, closed reason vocabulary, and versioned policy documentation.
- `src/greenpath/llm/`: bounded optional provider port, structured grounding validator, deterministic templates, offline adversarial evaluator, and provider limitations.
- `src/greenpath/api/`: injectable application factory, documented customer/recommendation/explanation/health routes, filtered portfolio counts, and explicit historical trends.
- `src/greenpath/app/`: Streamlit entrypoint, HTTP client, customer/Why/provenance views, Plotly portfolio views, and display-only formatting. No domain or calculator imports.
- `src/greenpath/demo/`: stable synthetic providers, packaged impact JSON fixtures, two-process launcher, and integrated scenario report generator.
- `.streamlit/config.toml`: native forest/cream theme without injected CSS.
- `tests/impact/`: formula, evidence, boundary, unit, serialization, and unavailable-case tests, plus four standalone synthetic JSON input fixtures.
- `tests/recommendation/`, `tests/llm/`, `tests/api/`, `tests/app/`, and `tests/integration/`: rules, adversarial validation, HTTP contracts, AppTest behavior, and provider checks.
- `pyproject.toml`, `uv.lock`, `.python-version`, `Makefile`, and `.gitignore`: independent Agent B setup. Reconcile these with destination configuration during manual transfer.

Generated artifacts are `reports/explanation_evaluation.json` and `reports/scenario_evaluation.json`. These record fixed offline cases and local validator latency; live provider cost and latency remain null. No trained model or held-out predictive artifacts are produced. Wheel builds are disposable and excluded by `.gitignore`.

## Contract proposals for manual integration

Agent A's canonical contracts and the master MVP specification remain absent. The local mirrors implement the written plan's meanings and are **not a canonical shared schema**. `PARALLEL_HANDOFF.md` froze their interfaces for points 3–6 within this repository only. Replace all four mirror files with Agent A's canonical contracts/ports and reconcile the following fields before manual integration:

- Proposed product enum values: `EV_FINANCE`, `GREEN_HOME`, `SOLAR_FINANCE`, `PAPERLESS_BANKING`.
- Proposed impact statuses: `AVAILABLE`, `UNAVAILABLE`. These are independent of the six recommendation states.
- Proposed issue codes are the seven codes recorded in `CARBON_METHODS.md`. Each issue includes a field path and an actionable message.
- `ImpactResult` contains value/units, baseline/scenario descriptions and emissions, comparison period, feature cutoff, synthetic-demo flag, factor references with original/normalized values and source provenance, catalogue version/checksum, boundary, assumptions, exclusions, method version/release, timestamp, evidence, and issues.
- Unavailable numeric fields are null. Available values equal baseline minus scenario, including zero and negative changes. Units are `kg CO2` for a stated period or `kg CO2/year` for a complete calendar anniversary; partial periods are never annualized.
- The input adapter needs evidence references, basis, observation timestamp, exact comparison period, freshness assessment, and conflicts for each quantity and scope claim. Raw merchant descriptions and propensity scores have no role in these inputs. The provisional `CustomerSnapshot` has only approved Boolean relevance evidence, cutoff, region/segment, and a separate Trust assessment.
- Each calculator port has `product` and `calculate(payload) -> ImpactResult`. Catalogue and clock injection are local implementation details.
- Product providers expose `get_snapshot`, `list_snapshots`, `get_propensity`, `get_impact_input`, and `list_history` as narrow protocols. The default fixtures are independent copies on reads. Region and segment are portfolio metadata, not propensity inputs.
- Rules use a synthetic demonstration threshold of 0.60. They suppress withdrawn contact consent and fail closed on conflicts, OOD, missing/stale/future critical evidence, high-severity Trust limitations, and unusable propensity. Reasons come from a closed vocabulary. Impact availability is independent of relevance. Confidence requires the provider's explicit validation flag.
- Optional explanations accept approved sentence ordering only; all claims, values, units, reasons, and the disclaimer must match exactly. No live SDK or automatic credential discovery is bundled. A provider version and SDK deadline must be configured when injecting an adapter. Worker deadlines cannot cancel an underlying SDK call; outstanding calls are bounded.
- Portfolio responses count decisions and supported opportunities by product, region, and segment. Monthly history is explicitly recorded synthetic fixture data. No cross-product carbon sum is computed.

## Method limits

All available values are restricted to the synthetic India demo. The historical CEA factor is not approved for live customer estimates; its original PDF access limitation is carried into every result that uses it. Factors and source editions remain those frozen in point 1.

Dates use inclusive start and exclusive end. Numeric quantities support up to 24 significant decimal digits and 12 decimal places; excess precision returns `INVALID_INPUT`. Formula arithmetic uses a local precision of 60 to retain all supported input precision and remain independent of the caller's decimal context.

Evidence after the feature cutoff, stale/unknown freshness, unresolved conflicts, wrong units, missing scope declarations, and unsupported fuel/geography/boundaries fail closed. Meter readings and declarations cannot describe future activity as already observed. Forecasts and synthetic inputs are explicitly listed as such in the result assumptions.

EV supports evidenced fuel mass, or litres plus supplied fuel-specific density. No density, travel, or charging-loss default is introduced. Green Home requires documented comparable service and unchanged fuel/on-site generation. Solar requires complete, ordered, contiguous matched intervals and validates physical self-consumption within each interval. Interval resolution must support the claimed load overlap; an annual generation total alone is insufficient evidence. Exports are retained as evidence when provided and receive no credit.

Paperless may retain a supplied whole physical-sheet count as input evidence, but its carbon result remains unavailable. Carbon allocation, lifecycle accounting, non-CO2 gases, empirical confidence validation, and credit eligibility remain outside Agent B's implemented scope.
