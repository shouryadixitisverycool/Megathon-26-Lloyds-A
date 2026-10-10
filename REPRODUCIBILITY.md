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

`GREENPATH_PROVIDER=fixture` gives deterministic GP personas; `trained` requires complete artifacts; `auto` defaults to trained when artifact evidence exists and otherwise fixtures. Incomplete trained artifacts raise errors rather than quietly changing the evidence source. `make test` explicitly sets fixture mode; this does not prove trained UI flows.

Without `GREENPATH_LLM_API_KEY`, explanations are templates. A keyed HTTP configuration additionally requires `GREENPATH_LLM_ENDPOINT`, `LLM_MODEL` and `LLM_MODEL_VERSION`. Optional settings: `PROMPT_VERSION`, `TEMPERATURE`, `MAX_OUTPUT_TOKENS`, `GREENPATH_LLM_INPUT_PRICE_PER_MILLION`, `GREENPATH_LLM_OUTPUT_PRICE_PER_MILLION`. Keep keys outside committed files. Cost requires actual returned token usage and explicit pricing; absent data remains null.

Live-provider evidence: **not run without credentials**. Offline adversaries test validators/fallback, not a provider's quality or cost. System timings are local in-process FastAPI TestClient measurements excluding network, Streamlit rendering and live LLM latency.

## Verification Status

This documentation-only pass inspected source and saved reports; it did not rerun the pipeline or certify gates. Main owner must record final `make all` exit status, revision, customer count, trained/fixture API/UI smoke results and safe trained-impact behaviour after integration fixes. Persistent local memory can affect outreach/planning scenarios; reproducible comparisons should use a fresh checkout/environment with no prior SQLite journey events, while preserving existing user data.
