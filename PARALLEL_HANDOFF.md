# Shared packet for Agent B points 3–6

> Historical independent-build packet, superseded for integrated runtime by `AGENT_B_HANDOFF.md`, `CONTRACTS.md` and `README.md`. Agent A is now present. Canonical product/API contracts live in `contracts/product.py`, ports in `ports.py`; mirror-named modules are import shims. The API now composes fixture or trained providers and includes implemented extensions. Original instructions below are retained as design history, not current integration status. Main verification passed; see `IMPLEMENTATION_PLAN.md` for results and limitations.

Read `IMPLEMENTATION_PLAN.md`, `CARBON_METHODS.md`, and `AGENT_B_HANDOFF.md`. Work in the existing shared workspace. Do not commit, merge, reset, or edit other subagents' owned files. Main thread owns project configuration, dependency installation/lock, demo providers, shared mirrors, and final documentation. All contract mirrors remain replaceable by Agent A's canonical versions.

The immutable handoff schema is `src/greenpath/_product_contract_mirror.py`; narrow ports are in `_product_port_mirror.py`. Impact calculators remain those implemented in point 2. Do not alter frozen factors or invent impact inputs.

## Point 3 interface

Implement `greenpath.recommendation.service.RecommendationService(snapshot_provider, propensity_provider, impact_input_provider, *, calculators=None, clock=utc_now)`. Method `recommendations(customer_id)` returns `tuple[Recommendation, ...]` for all four products and raises `KeyError` for unknown customers. Rules only decide relevance and abstention, never eligibility. Map evidence into controlled codes/messages; confidence must remain suppressed unless validated. Cover all six states.

Frozen feature names and Boolean evidence live in `APPROVED_FEATURES`. Suggested product signals: EV owns_vehicle/ev_interest/fuel_supported, Home owns_home/retrofit_interest, Solar owns_home/roof_available/solar_interest, Paperless paper_statements/paperless_consent. Existing adoption flags are already_has_ev, efficient_home, solar_installed, paperless_active. marketing_consent controls suppression. Fail closed on missing/stale/future evidence, high conflicts, and OOD. Document precedence and the demo propensity threshold. An unavailable impact alone need not prevent an otherwise supported relevance decision.

## Point 4 interface

Implement `greenpath.llm.service.ExplanationService(provider=None)` with `.explain(recommendation) -> Explanation`. Default no-key path must be fully usable. Define a narrow optional provider port and validate schema, product/state/reasons/numbers/eligibility language against approved structured fields before accepting output. Never pass raw snapshot features or merchant descriptions. All failures choose the deterministic template. Avoid uncontrolled strings from injected trust/propensity reasons in the prompt. Add fixed adversarial evaluations and an executable report module; live metrics/cost are unavailable unless measured.

## Point 5 interface

Implement `greenpath.api.main.create_app(...)` with a default app exported as `app`. Inject providers/services for tests; default uses `greenpath.demo.providers.DemoRepository`. This repository will implement the four provider ports above. Instantiate recommendation and explanation services using the frozen interfaces.

Routes consumed by UI:

- GET `/health`: status, synthetic_demo and contract_version.
- GET `/customers`: a list of CustomerSnapshot JSON objects.
- GET `/customers/{customer_id}`: CustomerSnapshot.
- GET `/customers/{customer_id}/recommendations`: RecommendationsResponse. Provide `/opportunities` alias.
- GET `/customers/{customer_id}/explanations/{product}`: Explanation.
- GET `/portfolio/summary`: PortfolioSummary.
- GET `/portfolio/trends`: PortfolioTrends.

Both portfolio routes support optional `region`, `segment`, and `product` query parameters. Unknown IDs return 404, invalid product filters return 422. Count recommendations consistently, keep all six states represented, and avoid cross-product carbon sums. History comes from `repository.list_history()`, never fabricated from current scores. Decimal fields are serialized as strings by the contracts. Document routes in your owned `api/README.md`.

## Point 6 interface

Implement a Streamlit entrypoint `src/greenpath/app/main.py`, HTTP-only API client and customer/Why/portfolio UI with Plotly. The UI must not import recommendation/model/impact internals. Main thread supplies dependencies and `make app` launching API plus Streamlit. Use `GREENPATH_API_URL`, default `http://127.0.0.1:8000`; validate/reset filters coherently and handle API errors visibly. Read the route/response definitions above and shared mirrors without editing them.

Stable synthetic personas are `GP-001` through `GP-006`: supported opportunities, missing evidence, conflict, already adopted, contact suppressed, and low propensity. Default to GP-001; GP-002 must demo responsible abstention. All views visibly say synthetic demo; show cutoff, evidence, model/calibration/rule versions, Trust distinct from confidence, impact units/boundary/factors/assumptions/exclusions, and eligibility disclaimer. Do not claim synthetic fixture probabilities establish predictive performance. Test main flows with Streamlit AppTest and mocked HTTP API responses, never domain-internal UI imports.

## Ownership and run checks

- Point 3: `recommendation/`, `tests/recommendation/`, optional `tests/scenarios/`.
- Point 4: `llm/`, `tests/llm/`, explanation evaluation code/report source under `llm/`.
- Point 5: `api/`, `tests/api/`.
- Point 6: `app/`, `tests/app/`.

Use `uv run --locked pytest <owned test directory>` once dependencies are available. Main thread adds FastAPI, uvicorn, httpx, Streamlit, Plotly to the shared project; do not edit pyproject.toml, uv.lock, Makefile, shared mirrors, demo/, or top-level documents. Report files, tests, deviations, and limitations concisely. Coordinate interface questions with the main agent. Do not spawn further agents.
