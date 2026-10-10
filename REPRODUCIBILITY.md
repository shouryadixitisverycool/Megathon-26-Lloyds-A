# Reproducibility

## Clean Run

Python 3.12, `uv`, local disk and initial dependency-download access are required. `uv.lock` pins dependencies; no LLM credentials are required. From a clean checkout:

```bash
make all
GREENPATH_PROVIDER=trained make app
```

The Makefile serializes `all`: locked setup, full pipeline, fixture-mode pytest, offline LLM evaluation, fixture scenario evaluation, extension/system evaluation. Default `CUSTOMERS=4000`; customer count changes results. Small smoke runs are not comparable to the submission's 4,000-customer evidence.

Individual targets: `make setup`, `make data`, `make perturbed`, `make train`, `make evaluate`, `make test`, `make test-trained`, `make evaluate-llm`, `make scenarios`, `make evaluate-system`, `make schemas`, `make build`. Train/evaluate require prior stage inputs; `make all` is the core end-to-end entrypoint. Optional product training/report regeneration is separate: `uv run --locked python -m greenpath.extensions.optional_models` after the core pipeline. `evaluate-system` benchmarks API/cache/fairness; it does not train the optional models.

## Artifact Map

| Output | Purpose |
|---|---|
| `data/` | Generated base/perturbed tables, processed cutoff snapshots, trained models and local SQLite memory; inspect `config.py` for paths. |
| `reports/RUN_MANIFEST.json` | Seeds, timeline, generator configuration, dependency/environment metadata and artifact hashes. |
| `reports/ml_evaluation.json`, `reports/predictions/` | Held-out metrics and prediction evidence. |
| `DATA_CARD.md`, `MODEL_CARD_*.md`, `EVALUATION_REPORT_AGENT_A.md` | Pipeline-generated data/model descriptions and synthetic evaluation narrative; regeneration may replace these. |
| `reports/leakage_checks.json`, `transaction_eval.json`, `feature_drift.json`, `confidence_validation.json` | Cutoff/leakage, merchant holdout, drift and confidence diagnostics. |
| `reports/explanation_evaluation.json`, `scenario_evaluation.json` | Fixed offline adversaries and six-persona product scenarios. |
| `reports/optional_evaluation.json`, `system_performance.json`, `pipeline_timings.json` | Optional model evidence and scoped local performance measurements. |

Recorded main seeds are data 42, split 43, model 44, perturbation 45. Saved timeline: feature cutoff 2026-06-30, 90-day outcome end 2026-09-28, prediction timestamp 2026-10-10. Demo personas are excluded from training. Compare manifests/hashes and deterministic predictions, not wall-clock timings or runtime calculation timestamps. Trust is independent from confidence; runtime consumes stored confidence decisions.

## Modes And Live Provider

The pipeline reserves one third of initial validation customers as `confidence_release` before propensity tuning/calibration and meta fitting. Confidence display is selected on this reserved cohort, not final test. The inspected report suppresses all four core products; prior surfaced-confidence metrics and system coverage are not comparable. Retrain/evaluate rather than reusing older bundles. SHAP requires the fitted background from new training and explains raw log-odds only; evaluation writes `reports/shap/` audits.

Source changes add event/availability provenance, source-update requests and product decision/explanation/history fields. Run `make schemas` after final integration and inspect generated diffs; this is separate from `make all`. Regenerate source data, processed snapshots, models, predictions, reports and manifest together after source-table/schema changes. Do not mix new schemas with old snapshots or partially regenerated reports. This docs-only pass does not write generated schemas.

`GREENPATH_PROVIDER=fixture` gives deterministic GP personas; `trained` requires complete artifacts; `auto` defaults to trained when artifact evidence exists and otherwise fixtures. Incomplete trained artifacts raise errors rather than quietly changing the evidence source. `make test` explicitly sets fixture mode; this does not prove trained UI flows.

Without `GREENPATH_LLM_API_KEY`, explanations are templates. A keyed HTTP configuration additionally requires `GREENPATH_LLM_ENDPOINT`, `LLM_MODEL` and `LLM_MODEL_VERSION`. Optional settings: `PROMPT_VERSION`, `TEMPERATURE`, `MAX_OUTPUT_TOKENS`, `GREENPATH_LLM_INPUT_PRICE_PER_MILLION`, `GREENPATH_LLM_OUTPUT_PRICE_PER_MILLION`. Keep keys outside committed files. Cost requires actual returned token usage and explicit pricing; absent data remains null.

Live-provider evidence: **not run without credentials**. Offline adversaries test validators/fallback, not a provider's quality or cost. System timings are local in-process FastAPI TestClient measurements excluding network, Streamlit rendering and live LLM latency.

## Authorized Live Evaluation

`src/greenpath/llm/provider_manifest.json` selects OpenAI `https://api.openai.com/v1/chat/completions`, dated snapshot `gpt-4.1-mini-2025-04-14`, prompt `grounded-selection-v1`, temperature 0 and output bound 1600 tokens. Status is `selected_not_live_evaluated`. No paid run is included in `make all` or performed here. Only after explicit authorization, credentials and independently checked current pricing, run:

```bash
uv run --locked python -m greenpath.llm.live_evaluation --allow-paid-provider --cases 100 --output reports/live_explanation_evaluation.json
```

The evaluator requires `GREENPATH_LLM_API_KEY` and `GREENPATH_LLM_INPUT_PRICE_PER_MILLION`, `GREENPATH_LLM_OUTPUT_PRICE_PER_MILLION`, `GREENPATH_LLM_CACHED_INPUT_PRICE_PER_MILLION`. It stops on provider failure, records partial completion, and measures final grounded output including fallbacks rather than raw-model quality. Its separate cache experiment adds calls included in provider totals. Missing usage/cost remains null. See the LLM-owner docs for adapter details.

## Source And State

DESNZ 2025 is the reviewed hashed subset in `extensions/uk_factors_2025.json`; official 2026 availability is recorded but its numeric rows have not been reviewed/substituted. Updating vintage requires review, versioning and report/passport regeneration. PVGIS 5.3 consumes archived bytes or a matching fetched response with a reviewed SHA-256, retrieval time, explicit installation parameters, echoed metadata and annual energy units. There is no fallback regional yield; demand/self-consumption must still be supplied. The pipeline does not automatically fetch or review site-specific PVGIS evidence.

Local factual updates require trained mode and `GREENPATH_DEMO_ADMIN_TOKEN` matched by `X-Demo-Admin-Token`. Keep the token outside committed files. Updates require actor/reason/source reference, idempotent request ID and coherent event/availability/cutoff timestamps. SQLite retains decisions, explanation runs, source overrides, feedback and active simulated campaigns across restarts. Preserve user state and use isolated memory paths for repeatable tests. Updates rescore deployed inference; they do not retrain or replace unchanged rolling evidence.

## Verification Ownership

This documentation-only pass inspected source and saved reports; it did not rerun the pipeline or certify gates. Main owner must record final `make all` exit status, revision, customer count, trained/fixture API/UI smoke results and safe trained-impact behaviour after integration fixes. Persistent local memory can affect outreach/planning scenarios; reproducible comparisons should use a fresh checkout/environment with no prior SQLite journey events, while preserving existing user data.
