# Greenr Submission Narrative

## Outcome

Greenr integrates synthetic Customer 360 and calibrated opportunity models for EV Finance, Green Home, Solar Finance and Paperless Banking with evidence-aware relevance rules, transparent impact and grounded explanations. The demonstration includes successful abstention, not only positive recommendations. See [README.md](README.md) for the mode-specific five-minute walkthrough and [ARCHITECTURE.md](ARCHITECTURE.md) for the diagram.

## Evaluation Evidence

[EVALUATION_REPORT.md](EVALUATION_REPORT.md) consolidates all 30 evaluation topics required by specification section 62. Numeric evidence belongs to regenerated reports and their matching manifest/predictions, not earlier copied values. This pass does not certify final gate outcomes or counts. All ML results are synthetic; demo personas are excluded from training and model selection.

| Evidence | Authoritative artifact after regeneration |
|---|---|
| Product models, baselines, calibration and shift | `reports/ml_evaluation.json`, `EVALUATION_REPORT_AGENT_A.md`, `reports/predictions/` |
| Merchant generalisation | `reports/transaction_eval.json` |
| Confidence release and stress | `reports/confidence_validation.json`, `reports/CONFIDENCE_VALIDATION.md`, persisted model decisions |
| Offline grounding and scenarios | `reports/explanation_evaluation.json`, `reports/scenario_evaluation.json` |
| Local performance and fairness | `reports/system_performance.json`, `reports/pipeline_timings.json` |

Model selection, calibration and thresholds use validation data. `confidence_release` customers are reserved before tuning/calibration/meta fitting; final-test labels do not select release. The inspected confidence report suppresses all four core products, not only Paperless. Older surfaced-confidence narratives and system confidence coverage are stale. Interpret every product against heuristic/logistic baselines, pre/post calibration, shift/missingness and subgroup uncertainty. Strong Solar discrimination can reflect generator structure, not real-world predictability; synthetic disparities are not fairness certification.

Transaction categorisation uses deterministic rules then TF-IDF/logistic fallback. Merchant-group unseen evaluation is more informative than a random transaction split; use its report for the actual generalisation gap and rule coverage.

Offline adversarial explanations test validators and final safe output, not natural-traffic fallback frequency or live provider quality. Fixture scenarios cover six states, not trained cohort accuracy. Local TestClient/cache measurements exclude network, UI rendering and paid-provider latency, and may predate the latest changes until main regenerates them.

**No paid live provider run has been performed.** The selected manifest pins OpenAI Chat Completions and `gpt-4.1-mini-2025-04-14`; selection is not live evidence. An opt-in 100-200-case evaluator exists with explicit payment authorization, credentials, pricing, per-case measurements and a separate cache experiment. Live cost, tokens, latency, availability and quality remain unmeasured; null metrics are not zero.

## Scope And Limits

Implemented extensions include RM workspace, governance/evidence graph, SQLite memory and feedback lifecycle, consent-aware next actions, UK physical what-if passports, trained sensitivity, planning/campaign simulation, priority ranking with missing-component handling, and two optional synthetic products. Optional model limitations are in [MODEL_CARD_OPTIONAL.md](MODEL_CARD_OPTIONAL.md). Durable served decisions retain evidence-stable IDs and linked explanation runs. Admin-authorized local source updates rescore deployed models, Trust and impact and can verify Paperless closure without rewriting prior decisions or monthly history. Feedback alone is not factual completion. SHAP explains raw uncalibrated log-odds, not calibrated probability or causal effects. Real bank writeback, retraining, real messaging, production controls, causal advice, lifecycle carbon, credit eligibility and paid live-provider evidence remain external/deferred.

UK annual WTW CO2e scenarios are separate from legacy India operational CO2 fixture methods. The trained source adapter requires explicit physical scenario inputs and retains cutoff evidence. Complete scenarios expose AVAILABLE calculated impact in `kg CO2e/year` through the product API, UI and grounded explanations; missing inputs remain UNAVAILABLE. The detailed contract supports mutually exclusive, unit-matched CO2/CO2e emissions and preserves shipped CO2 fixtures. Complete paperless scenarios remain NOT_CLAIMED with null carbon numbers; secondary avoided activity is supported only by the scoring view and scenario passport. Do not claim automatic trained carbon estimates for snapshots missing physical assumptions.

## Submission Checklist

Reviewed DESNZ 2025 rows remain frozen although the official 2026 edition is available; this is a disclosed current-vintage specification gap, not a claim that 2025 is latest. PVGIS 5.3 needs explicit installation inputs and a reviewed source response/hash; demand and self-consumption remain separately required. No generic yield fallback or live regional-source verification is claimed. Portfolio physical totals preserve compatible groups and missing coverage; conversion rates use recorded synthetic outcomes, not realised bank conversions.

| Output | Evidence |
|---|---|
| Architecture | `ARCHITECTURE.md` Mermaid diagram and contract boundaries |
| Responsible AI | `RESPONSIBLE_AI.md` |
| Reproduction | `REPRODUCIBILITY.md`, `Makefile`, `uv.lock`, `reports/RUN_MANIFEST.json` |
| Data/model cards | `DATA_CARD.md`, four core `MODEL_CARD_*.md`, `MODEL_CARD_OPTIONAL.md` |
| Evaluation | `EVALUATION_REPORT.md`, detailed Agent A report and scoped JSON artifacts in `reports/` |
| Final gates | In progress with main owner: final `make all`, `make schemas`, build and fixture/trained runtime smoke outcomes/counts are not certified here |

Source/report inspection on 2026-10-10 is not a new full verification. Earlier counts and launcher measurements remain explicitly historical in `IMPLEMENTATION_PLAN.md`. Main must record final revision, manifest/hashes, dataset size, counts and outcomes after regeneration. No new browser walkthrough, independently provisioned OS environment or paid live evaluation was performed here. The original specification and design history are preserved.
