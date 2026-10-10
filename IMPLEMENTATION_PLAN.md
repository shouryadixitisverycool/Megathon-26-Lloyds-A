# GreenPath Implementation Status

Basis: `GreenPath_PS1_Master_MVP_v2.md`. Updated and verified on 2026-10-10 on branch `finish-agent-a`. Agent A and Agent B are integrated in this repository. Historical independent-workstream instructions are not current runtime requirements.

## Implemented Core

| Area | Current implementation |
|---|---|
| Data / Customer 360 | Seeded UK synthetic tables, public aggregate energy anchors, stochastic adoption outcomes, point-in-time features, customer splits, temporal/leakage checks and merchant-group categorisation evaluation. |
| ML | Four product-specific heuristic/logistic/boosted comparisons, validation-only calibration and thresholds, held-out predictions, temporal/generator-shift/missingness/subgroup diagnostics. Saved report selects logistic for all four. |
| Reliability | Separate completeness/freshness/conflict/OOD Trust and validated-or-suppressed confidence; saved run suppresses Paperless confidence. |
| Contracts | Canonical `contracts/` and `ports.py`; numeric scoring view and explicit product/API adapters retain ML source evidence, probability and confidence gates. |
| Product rules | Six relevance states, adoption/population exclusions, abstention and conflict handling; eligibility is not assessed. Fixture and trained decision profiles have distinct thresholds/evidence requirements. |
| Impact | Versioned legacy India CO2 calculators; UK DESNZ 2025 CO2e physical scenarios and trained source adapter. Product contract exposes AVAILABLE `kg CO2e/year` only for complete explicit physical inputs, with unit-matched emissions and provenance; missing inputs remain UNAVAILABLE. Paper avoidance has no carbon claim. |
| Explanations | Deterministic templates, grounded approved-sentence selection, bounded optional HTTP provider, validation/fallback, cache and metrics. No live-provider evidence without credentials. |
| Experience | HTTP-only Streamlit Customer, Portfolio, Relationship Manager, Planning and Governance views; injectable FastAPI; mode/source health endpoint. |

## Optional Scope

Implemented as demo extensions: SQLite feedback/preferences/review/contact audit history; lifecycle and consent/cooling-off rules; impact passports and UK what-if scenarios; trained-model sensitivity; evidence graph; RM opportunity ranking; planning and constrained campaign simulation; governance/monitoring reports; Green Investments and Green Loans synthetic optional models. Priority is unavailable when validated confidence or comparable impact is missing. Campaign execution records simulated contacts only. Feedback/review never rewrites model probability, confidence, eligibility or physical impact.

Deferred or not demonstrated: real customer ingestion, production authentication/authorization and deployment controls, real campaign delivery, factual completion writeback and retraining, causal intervention advice, lifecycle/embodied carbon and carbon-credit eligibility, reviewed Paperless carbon, independently validated optional-product confidence, live LLM evaluation. Do not describe implemented RM/memory/planning tools as deferred.

## Reproducible Command

`make all` = `setup` -> `pipeline` -> `test` -> `evaluate-llm` -> `scenarios` -> `evaluate-system`. Pipeline runs environment capture, base/perturbed generation, training, evaluation and predictions. `make test` forces fixtures; runtime defaults to `auto`. See [REPRODUCIBILITY.md](REPRODUCIBILITY.md).

## Verification

1. `make all` completed with exit 0: locked setup, 4,010 base customers, 4,000 perturbed customers, six historical cutoffs, four calibrated models and 2,400 held-out predictions. Full suite: 1,119 passed; fixed explanation evaluation: 196/196; integrated scenarios: 24/24; system performance/fairness report regenerated.
2. Trained integration tests generate and train a fresh temporary population and verify API, no-key explanations, portfolio/trends, confidence suppression, abstention and explicit physical-scenario impact. Unit-matched CO2e passport rendering and explanation grounding are tested.
3. `make schemas build` passed. Real launcher HTTP smoke passed in both fixture and trained modes: API and Streamlit health, customer/recommendation/opportunity routes, portfolio summary/trends, graceful shutdown and port release. Trained startup was approximately 92 seconds. These are HTTP/AppTest checks, not a new browser walkthrough or an independently provisioned OS environment.
4. Live explanation-provider evaluation remains **not run without credentials**, with null live metrics. Physical inputs missing from generated snapshots remain unavailable by design; explicit what-if inputs are supported. Production controls and optional limitations remain outside MVP acceptance.

Architecture and safety boundaries remain: propensity is interest, Trust is evidence adequacy, confidence is validated model reliability, impact is a separate physical scenario and eligibility is not assessed. Raw merchant text never enters the explanation prompt. Missing inputs/factors produce unavailable output, not invented numbers. See [SUBMISSION.md](SUBMISSION.md) and [RESPONSIBLE_AI.md](RESPONSIBLE_AI.md).
