# GreenPath Submission Narrative

## Outcome

GreenPath integrates synthetic Customer 360 and calibrated opportunity models for EV Finance, Green Home, Solar Finance and Paperless Banking with evidence-aware relevance rules, transparent impact and grounded explanations. The demonstration includes successful abstention, not only positive recommendations. See [README.md](README.md) for the mode-specific five-minute walkthrough and [ARCHITECTURE.md](ARCHITECTURE.md) for the diagram.

## Saved Evaluation Evidence

The values below are from the saved `EVALUATION_REPORT_AGENT_A.md`, not newly measured in this documentation pass. All are synthetic held-out results; model selection, calibration and operational thresholds use validation data. Customer-level splits exclude demo personas. Temporal, generator-shift, missingness and subgroup diagnostics are included in the detailed report.

| Product | Selected | Test ROC-AUC | Heuristic AUC | Brier | ECE | Lift@10% | Perturbed AUC | Confidence |
|---|---|---|---|---|---|---|---|---|
| EV Finance | Logistic | 0.755 | 0.701 | 0.073 | 0.027 | 2.808 | 0.640 | Surfaced |
| Green Home | Logistic | 0.675 | 0.669 | 0.082 | 0.013 | 2.283 | 0.656 | Surfaced |
| Solar Finance | Logistic | 0.960 | 0.623 | 0.041 | 0.026 | 6.965 | 0.946 | Surfaced |
| Paperless | Logistic | 0.640 | 0.642 | 0.152 | 0.084 | 1.485 | 0.716 | Suppressed |

Interpretation: EV ranking improves over its heuristic but drops under generator shift; Green Home is only marginally above its heuristic; Paperless is not above its heuristic on AUC and confidence is suppressed. Solar's strong result reflects simulated generator structure, not established real-world predictability. Calibration does not uniformly improve held-out metrics: EV Brier/ECE worsen after calibration. Synthetic subgroup disparities and small positive counts are limitations, not fairness certification.

Transaction categorisation uses deterministic rules then TF-IDF/logistic fallback. Saved known-merchant macro F1 is 0.992 versus unseen-merchant 0.529, with unseen rule coverage 0.153; this gap is material and requires further work before real ingestion. Merchant-group holdout is more informative than a random transaction split.

Current explanation evidence: 196/196 fixed offline validator cases pass, groundedness/numeric consistency 1.0, unsupported displayed claims 0, fallback rate 0.643. This deliberately adversarial set is not a natural-traffic fallback estimate or live model evaluation. Fixture scenarios cover 24 decisions across six states; they do not establish trained cohort accuracy. `system_performance.json` measures local in-process TestClient samples and cache behaviour, excluding network/UI/live-provider latency; it is not a production load test.

**Live-provider evidence: not run without credentials.** No measured live LLM cost, token usage, latency or quality is claimed. Null live metrics must not be presented as zero-cost live service.

## Scope And Limits

Implemented extensions include RM workspace, governance/evidence graph, SQLite memory and feedback lifecycle, consent-aware next actions, UK physical what-if passports, trained sensitivity, planning/campaign simulation, priority ranking with missing-component handling, and two optional synthetic products. Optional model limitations are in [MODEL_CARD_OPTIONAL.md](MODEL_CARD_OPTIONAL.md). Real messaging, production controls, factual completion writeback/retraining, causal advice, lifecycle carbon, credit eligibility and live-provider evaluation are deferred.

UK annual WTW CO2e scenarios are separate from legacy India operational CO2 fixture methods. The trained source adapter requires explicit physical scenario inputs and retains cutoff evidence. Complete scenarios expose AVAILABLE calculated impact in `kg CO2e/year` through the product API, UI and grounded explanations; missing inputs remain UNAVAILABLE. The detailed contract supports mutually exclusive, unit-matched CO2/CO2e emissions and preserves shipped CO2 fixtures. Complete paperless scenarios remain NOT_CLAIMED with null carbon numbers; secondary avoided activity is supported only by the scoring view and scenario passport. Do not claim automatic trained carbon estimates for snapshots missing physical assumptions.

## Submission Checklist

| Output | Evidence |
|---|---|
| Architecture | `ARCHITECTURE.md` Mermaid diagram and contract boundaries |
| Responsible AI | `RESPONSIBLE_AI.md` |
| Reproduction | `REPRODUCIBILITY.md`, `Makefile`, `uv.lock`, `reports/RUN_MANIFEST.json` |
| Data/model cards | `DATA_CARD.md`, four core `MODEL_CARD_*.md`, `MODEL_CARD_OPTIONAL.md` |
| Evaluation | Detailed Agent A report and scoped JSON artifacts in `reports/` |
| Final gates | `make all` exit 0, 1,119 tests passed, 196 explanation cases, 24 scenarios; `make schemas build` passed; fixture/trained real launcher HTTP and shutdown smoke passed |

Verified on branch `finish-agent-a` on 2026-10-10, with uncommitted integration changes. The pipeline regenerated 4,010 base customers, 4,000 perturbed customers and 2,400 held-out predictions. Fresh temporary trained-runtime integration tests pass. Real fixture/trained launchers returned healthy API/Streamlit responses and released owned child processes and ports on termination. Trained startup took approximately 92 seconds. No new browser walkthrough or independently provisioned OS environment was used; live-provider metrics remain unavailable.
