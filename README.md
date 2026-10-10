# GreenPath Intelligence

Synthetic sustainability opportunity demo integrating Agent A's data, calibrated ML and reliability pipeline with Agent B's product rules, deterministic impact, grounded explanations, FastAPI and Streamlit. Relevance is not credit eligibility, approval or investment suitability.

## Run

Requires Python 3.12 and `uv`; default explanations need no credentials.

```bash
make all
make app
```

`make all` runs, in order, `setup`, `pipeline`, `test`, `evaluate-llm`, `scenarios`, and `evaluate-system`. The pipeline generates base and perturbed data, builds point-in-time Customer 360, trains/calibrates/evaluates models and writes predictions and manifests. The test command sets fixture mode; integration tests also train fresh temporary models and explicitly exercise trained mode. Default dataset size is 4,000 generated customers plus base personas; override with `make all CUSTOMERS=4000`. The main owner is running final integration gates; this documentation pass does not certify their outcome or counts. Earlier verification is historical, not evidence for the changed implementation. See `IMPLEMENTATION_PLAN.md`.

Open http://127.0.0.1:8501; API docs: http://127.0.0.1:8000/docs. The launcher stops its owned API/UI processes on termination. Alternate ports: `uv run --locked python -m greenpath.demo.run --api-port 8001 --ui-port 8502`. Separate API: `make api`; separate UI: `uv run --locked streamlit run src/greenpath/app/main.py`. `GREENPATH_API_URL` defaults to `http://127.0.0.1:8000`.

## Provider Modes

| `GREENPATH_PROVIDER` | Behaviour |
|---|---|
| `auto` (default) | Uses trained artifacts when models or Customer 360 artifacts exist; otherwise fixtures. Partial/corrupt trained installations fail visibly, not silently back to fixtures. |
| `trained` | Requires complete local models, snapshots, OOD detectors and confidence decisions. Uses calibrated probabilities and per-model validation-selected thresholds. |
| `fixture` | Six stable GP-001 to GP-006 personas, synthetic fixed probabilities, threshold 0.60 and suppressed confidence. Independent of trained artifacts. |

After `make all`, `auto` normally selects trained mode. Use `GREENPATH_PROVIDER=fixture make app` for the scripted six-state demo, or `GREENPATH_PROVIDER=trained make app` to inspect model-backed UK synthetic customers. `/health` identifies mode and source version.

## Five-Minute Demo

1. In fixture mode, inspect GP-001's four product decisions and Why details: evidence, cutoff, model/rules, Trust, factors and exclusions. Paperless carbon is unavailable.
2. Use responsible abstention for GP-002; GP-003 has conflicts, GP-004 adoption exclusions, GP-005 contact suppression and GP-006 low propensity.
3. Open Portfolio and filter region, segment, product, validated confidence, impact and data quality. Inspect funnel, Trust/quality and missingness coverage. Monthly records are historical synthetic evidence, not current scores copied backwards; physical totals are grouped by compatible product, units, boundary, period and method/factor version, never one cross-product carbon total.
4. In trained mode inspect retained ML evidence and confidence gating. Customer scenario tools offer explicit UK EV, solar, insulation/heat-pump and paper-avoidance assumptions separately from propensity sensitivity.
5. Inspect Relationship Manager, Planning and Governance for review, consent, durable decision/explanation audit and simulated campaign controls. Trained SHAP explains raw uncalibrated log-odds, not calibrated probability or causality. No campaign sends messages. Admin-authorized source updates can rerun deployed inference; feedback alone cannot close a factual Paperless journey.

## Contracts And Impact

`contracts/` and `ports.py` are canonical. Numeric scoring snapshots/results remain distinct from the Boolean-evidence product/API view in `contracts/product.py`; `demo/artifacts.py` adapts them with source snapshot, result and Trust provenance. Adapter validation preserves calibrated probability, model/calibration versions, population exclusions and validated-or-suppressed confidence. Legacy mirror-named modules are compatibility imports, not independent schema authorities. See [CONTRACTS.md](CONTRACTS.md).

Legacy India calculators return signed operational CO2 differences under [CARBON_METHODS.md](CARBON_METHODS.md), including the historical CEA source-access caveat. UK scenarios use pinned DESNZ 2025 operational well-to-wheel CO2e factors and explicit physical assumptions. These boundaries and units are not interchangeable. The trained UK adapter in `impact/uk_adapter.py` retains source/scenario evidence and exposes AVAILABLE product API impact in `kg CO2e/year` when physical inputs are complete; missing inputs remain UNAVAILABLE, without fabricated efficiencies or runtime defaults. The detailed contract retains legacy CO2 fields and adds mutually exclusive, unit-matched CO2e emissions fields. UI and grounded explanations preserve the calculated numbers and units. Complete paperless scenarios are NOT_CLAIMED with null carbon numbers; avoided activity is available only in the scoring view and scenario passport, not as secondary metrics in the detailed product contract. Incomplete paperless scenarios are UNAVAILABLE.

## Submission Evidence

The inspected confidence report suppresses all four core products after reserving `confidence_release` customers before tuning/calibration/meta fitting. Final test labels do not select release. Runtime uses persisted release decisions, not old saved surfaced values; optional-product and fixture confidence are also suppressed. Confidence-dependent priority may therefore be unavailable, with an explicitly labelled propensity ordering instead.

Source policy: DESNZ 2025 is the reviewed frozen factor subset, although the official 2026 edition is available; this is not current-vintage reporting. `impact/solar_generation.py` supports PVGIS 5.3 only with explicit installation inputs and a reviewed response SHA-256, metadata and retrieval provenance. It has no generic regional yield fallback and does not infer self-consumption. See [CARBON_METHODS.md](CARBON_METHODS.md) for method-owner details.

- [Submission narrative and evaluation](SUBMISSION.md)
- [Architecture diagram](ARCHITECTURE.md)
- [Reproducibility and artifact map](REPRODUCIBILITY.md)
- [Responsible AI note](RESPONSIBLE_AI.md)
- [Data card](DATA_CARD.md), [EV](MODEL_CARD_EV.md), [Green Home](MODEL_CARD_GREEN_HOME.md), [Solar](MODEL_CARD_SOLAR.md), [Paperless](MODEL_CARD_PAPERLESS.md), [optional model cards](MODEL_CARD_OPTIONAL.md)
- [Consolidated 30-topic evaluation](EVALUATION_REPORT.md), [detailed synthetic ML evaluation](EVALUATION_REPORT_AGENT_A.md), [implementation status](IMPLEMENTATION_PLAN.md), [integration handoff](AGENT_B_HANDOFF.md)

An optional HTTP explanation adapter and explicitly authorized live evaluator exist. The selection manifest pins OpenAI `gpt-4.1-mini-2025-04-14`, selected but not live evaluated. Without a key, templates are used. No paid live provider run was performed in this pass: live quality, latency, token usage and cost remain unmeasured, not zero. Saved offline adversarial and local TestClient measurements do not establish live LLM or production performance.
