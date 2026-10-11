# Product And Integration Handoff

Updated 2026-10-10 from integrated source. Agent A data/ML/reliability is present; this is no longer an Agent B-only repository. Full integration verification passed, including safe trained-impact changes. See `IMPLEMENTATION_PLAN.md` for results and external-evidence limitations.

## Boundaries

- Canonical schemas: `src/greenr/contracts/`; canonical protocols: `src/greenr/ports.py`. `contracts/product.py` is the explicit product/API evidence view; `contracts/impact_detail.py` holds detailed calculator provenance. Mirror-named modules are import shims, not schema authorities.
- `pipelines/runtime.py` loads Customer 360, calibrated bundles, OOD and confidence decisions. `demo/artifacts.py` adapts numeric scoring inputs/results and per-product Trust without changing calibrated probability or surfacing suppressed confidence; source objects remain attached.
- `recommendation/`, `impact/`, `llm/`, `api/`, `app/` and `demo/` implement product decisioning, provenance, grounded explanation, HTTP boundaries and fixture/trained composition. `extensions/` implements UK scenarios, memory, oversight, planning and optional products.
- Fixture mode retains six GP personas, fixed probabilities and threshold 0.60. Trained mode uses validation-selected model thresholds, product population exclusions and source Trust. `auto` selects artifacts when present and fails visibly on incomplete artifacts.
- History is recorded fixture history or separately scored trained cutoff evidence, not backwards extrapolation of current recommendations. SQLite feedback/reviews affect communication and lifecycle only.

## Commands And Evidence

`make all` now runs setup, full data/ML pipeline, fixture tests, offline explanation cases, fixture scenarios and extension/system evaluation. It produces data/models/predictions and reports, not only Agent B's two reports. [REPRODUCIBILITY.md](REPRODUCIBILITY.md) maps outputs; [README.md](README.md) gives startup and mode-specific demo steps.

Saved offline reports contain 18 explanation cases and 24 fixture product decisions. These are scoped saved evidence, not a claim that the current full suite or clean integration gates pass. Historical browser/wheel checks from the independent build must be repeated for the integrated application.

## Impact And Provider Limits

Legacy India calculators accept validated evidence mappings and return signed Decimal CO2 differences with factor/version/boundary/period provenance. `CARBON_METHODS.md` remains the frozen legacy methodology, including the historical CEA original-source access caveat. Separate UK scenarios use DESNZ 2025 operational WTW CO2e factors, explicit caller assumptions and their own passport shape; never substitute units or sum across these methods. Paperless carbon is not claimed.

`impact/uk_adapter.py` is wired into trained recommendations and cutoff history. It reads source activities and explicit scenario fields, retaining evidence and missing-input diagnostics. The detailed product contract now supports `kg CO2e/year` and unit-matched `emissions_kg_co2e`, mutually exclusive with legacy `emissions_kg_co2`. Complete physical scenarios expose AVAILABLE calculated CO2e in the API, UI and grounded explanations; missing inputs remain UNAVAILABLE, without runtime defaults. Complete paperless scenarios return NOT_CLAIMED with null carbon numbers and an explicit carbon-method issue; incomplete ones return UNAVAILABLE. Secondary avoided activity remains in `calculate_scoring` and UK `/simulate` passports, not the detailed product view. Do not claim automatic carbon estimates for snapshots lacking physical assumptions.

`llm/http_provider.py` provides an optional explicitly configured HTTP adapter. No key selects deterministic templates; partial keyed configuration fails clearly. Approved sentence IDs and exact structured claims are validated; timeout/error/unsafe output falls back. Live-provider quality, token use, latency and cost were **not run without credentials**. Local validator/TestClient timings are not live LLM performance.
