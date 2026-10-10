# Greenr Consolidated Evaluation Report

This report follows all 30 topics in section 62 of [the original specification](Greenr_PS1_Master_MVP_v2.md). It consolidates implemented behaviour, evidence locations and limitations as inspected on 2026-10-10; it does not replace that specification, the design/handoff history, or the generated [Agent A evaluation](EVALUATION_REPORT_AGENT_A.md).

**Gate status:** the main owner is running full `make all`. Final exit status, revision, dataset size, counts, schema/build parity and runtime smoke outcomes remain that owner's responsibility. This docs-only pass did not run gates or a paid provider. Reports may be regenerated during integration; compare their manifests/hashes before quoting metrics. Older surfaced-confidence and system confidence-coverage values are not valid evidence for the new release methodology. No numeric performance result is invented here.

## 1. Executive Summary

Greenr implements four synthetic opportunity models, point-in-time Customer 360, evidence-aware relevance/abstention, deterministic physical impact, grounded explanations and customer/RM/portfolio workspaces. Propensity, Trust, validated confidence, physical impact and financial eligibility remain separate; eligibility is NOT_ASSESSED. Durable decisions and linked explanations, authorized local source-driven rescoring, SHAP audits and portfolio missingness/history analytics are now implemented. The inspected confidence report suppresses all four core products. No paid live LLM evidence, production readiness or observed bank conversion is claimed. See [SUBMISSION.md](SUBMISSION.md) and [ARCHITECTURE.md](ARCHITECTURE.md).

## 2. Dataset And Provenance

Customer profiles, transactions, banking products, vehicles, energy/digital observations and adoption labels are synthetic. Public aggregates and published factor catalogues are separately sourced inputs, not real banking/customer observations. Generation records configuration, seeds and provenance in `reports/RUN_MANIFEST.json`; `DATA_CARD.md` describes entities and synthetic limitations. `pipelines/schemas.py`, `contracts/customer.py` and Customer 360 retain source event/availability evidence. New source schema fields require full regeneration rather than reuse of old processed data.

## 3. Public-Data Anchors

`data_generation/public_energy_anchor.json` pins DESNZ's 2024 subnational electricity/gas summary, updated 2025-12-19, with source URL, licence and scope. `public_anchors.py` uses published domestic-meter mean/median to shape synthetic lognormal energy marginals. Gas includes positive-consuming meters and a different reporting-year convention; GB scope excludes Northern Ireland. Seasonal patterns, customer correlations, noise and outcomes remain synthetic. This is not public microdata ingestion or predictive validation; the London Smart Meter/UCI examples in the specification are not claimed as implemented datasets. Diagnostics belong to the manifest/data card.

## 4. Synthetic-Data Generation

`data_generation/generator.py` uses stochastic latent drivers, interactions and noise for adoption, not a deterministic feature threshold copied into labels. Latent values do not enter approved propensity features. Demo personas are labelled separately and excluded from fitting/selection/evaluation. The outcome target is adoption in the 90 days after cutoff, not approval or causal response to outreach. See `DATA_CARD.md`, `AGENT_A_DESIGN.md` and manifest generator configuration. Stochastic generation reduces simple rule circularity but cannot remove simulator dependence.

## 5. Generator Perturbation

The pipeline generates a separate perturbed population with changed generator conditions. `evaluation/ml.py` reports shifted discrimination, calibration/ranking diagnostics and missing-data stress alongside canonical results in `reports/ml_evaluation.json` and `EVALUATION_REPORT_AGENT_A.md`; confidence stress is in `reports/confidence_validation.json`. These diagnostics expose sensitivity to simulated distribution change, not guaranteed real-world robustness. Do not substitute a stress pass for the reserved confidence release decision.

## 6. Leakage Audit

`pipelines/leakage_checks.py` checks customer split integrity, forbidden/target features, source event/availability timing and adoption boundaries. `pipelines/run.py` rebuilds snapshots from independently cutoff-filtered inputs at canonical and historical cutoffs and fails on differences. Current customer profiles unavailable at earlier cutoffs are masked rather than silently used historically. Evidence is `reports/leakage_checks.json`, `LEAKAGE_AUDIT.md` and `tests/pipelines/`. These tests concern the synthetic pipeline, not unknown real-source availability semantics.

## 7. Train/Validation/Test Methodology

`pipelines/split.py` creates seeded customer-level splits and hashes the sorted manifest, with demo customers separate. `pipelines/run.py` reserves one third of the initial validation customer IDs as `confidence_release` before propensity tuning/calibration and confidence meta fitting. Remaining validation selects models, calibration and thresholds; the reserved cohort selects confidence display; final test labels do not gate release. Product population exclusions reduce usable counts in each cohort. The canonical cutoff is 2026-06-30, outcome end 2026-09-28 and prediction date 2026-10-10; historical/temporal diagnostics retain their own cutoffs. Read actual cohort sizes from regenerated artifacts, not the specification's suggested fractions or earlier runs.

## 8. Transaction Categorisation

`models/transaction_classifier.py` normalises merchant text, applies deterministic boundary rules and TF-IDF/logistic fallback, producing exactly one of the eight categories. Known/unseen merchant-group metrics, per-category diagnostics, confusion matrix and rule coverage are recorded in `reports/transaction_eval.json` and `reports/TRANSACTION_CATEGORISATION.md`. Merchant-group holdout tests generalisation better than random transaction rows. Synthetic merchant coverage does not establish bank-wide taxonomy accuracy; raw merchant text never reaches the explanation prompt.

## 9. Heuristic Baselines

Each core product has an explicit heuristic comparison in `models/propensity/heuristics.py` and `reports/ml_evaluation.json`. Report baseline discrimination/ranking alongside the selected model, including products that do not improve. Heuristics are not labels, eligibility rules or calibrated customer probabilities. Earlier copied baseline values are intentionally not restated against the new cohort split.

## 10. Statistical Baselines

`models/propensity/training.py` fits logistic regression as a transparent statistical candidate and XGBoost as the boosted candidate, selecting on validation evidence. Logistic can legitimately be deployed rather than forcing the complex model. Compare candidate metrics and calibrated held-out behaviour in `reports/ml_evaluation.json` and the generated core model cards. Synthetic selection does not establish a universal winner.

## 11. Propensity Models

Four product-specific bundles retain approved features, population exclusions, model/calibration versions and validation-selected operational thresholds. `models/propensity/provider.py` and `demo/artifacts.py` preserve calibrated inference and provenance into the product API. Held-out predictions are written under `reports/predictions/`; temporal, shift, missingness and subgroup diagnostics are in the ML report. Strong scores may reflect generator structure rather than independent observed adoption.

Auditor SHAP is implemented in `models/propensity/shap_audit.py`: exact independent/interventional linear attribution against transformed training background for logistic, or exact tree-path-dependent XGBoost attribution using training cover. Additivity is checked against raw uncalibrated log-odds. It does not explain the nonlinear calibrator or causality. Evaluation writes `reports/shap/` when regenerated; `/customers/{customer_id}/shap/{product}` returns NOT_AVAILABLE for unavailable trained evidence, not reason codes relabelled as SHAP.

## 12. Probability Calibration

`models/propensity/calibration.py` fits validation-only calibration and the API displays calibrated probability. The ML report contains calibration evidence, before/after Brier/ECE and reliability/ranking diagnostics; plots are under `reports/plots/`. Calibration can worsen held-out metrics and is not proof of future reliability. It does not change the meaning of propensity to eligibility. Regenerate bundles after the release-cohort split change.

## 13. Trust Methodology

`trust/` measures completeness, freshness, consistency, critical fields and OOD independently of confidence. OOD detectors fit training population rows; `trust/selection.py` selects evidence thresholds using validation/scenario constraints and retains an artifact. `pipelines/runtime.py` consumes the selected policy. Contract assessments expose issues and support fail-closed rules. See `tests/trust/`, leakage/feature-drift reports and retained runtime assessment evidence. Trust is not a second propensity, credit decision or independently certified data-quality standard.

## 14. Confidence Methodology And Validation

`confidence/meta_model.py` estimates decision correctness at the deployed operational threshold using validation predictions. `confidence/validation.py` preserves tied scores and requires minimum sample size, decreasing error by confidence-bin rank and material top-versus-bottom error separation. The independent `confidence_release` cohort gates display, with decisions persisted for runtime; test/stress/ablations are diagnostics, not release selection. The inspected `reports/CONFIDENCE_VALIDATION.md` suppresses all four core products, including insufficient usable cohort evidence. Consult `reports/confidence_validation.json` and persisted decisions for final regenerated reasons. Suppression is the required safe result, not a reason to reuse older values or treat confidence as zero.

## 15. Guardrails / Abstention

`recommendation/service.py` implements RECOMMEND, DO_NOT_RECOMMEND, INSUFFICIENT_INFORMATION, CONFLICT_REQUIRES_REVIEW, NOT_APPLICABLE and SUPPRESSED, with trained/fixture evidence policies. Missing critical facts, contradictions, OOD/staleness, adoption exclusions and consent constraints are handled without secretly editing model probability. Missing impact can remain UNAVAILABLE independently of relevance. Evidence includes `tests/recommendation/`, `tests/integration/` and `reports/scenario_evaluation.json`; fixture scenarios are not estimates of held-out decision accuracy.

## 16. Recommendation Ranking

`extensions/service.py` implements versioned priority components: calibrated propensity, validated confidence, within-compatible-group normalised impact and Trust. If validated confidence or comparable impact is absent, composite priority is unavailable and ordering falls back explicitly to calibrated propensity. Current core confidence suppression therefore constrains priority and balanced planning; it must not be filled with old values. Ranking ablation is recorded by `extensions/evaluate.py` in `reports/system_performance.json`, not proof of causal campaign quality. Constraints include consent, decline/cooling-off, fatigue, duplicate/conflicting offers and active campaign/channel capacity. Persisted campaign closure releases simulated capacity; execution sends no messages.

## 17. Sustainability Calculations

`impact/uk_adapter.py` and `extensions/uk_impact.py` calculate UK annual operational WTW CO2e only from explicit physical inputs and reviewed factors. EV compares matched fuel/electricity boundaries; Green Home supports explicit insulation/heating assumptions; Solar requires generation, demand and self-consumption. Missing inputs remain UNAVAILABLE, never inferred from propensity or spend. Complete Paperless scenarios are NOT_CLAIMED for carbon and can expose avoided statements/sheets in the scoring/scenario passport. Legacy India CO2 fixtures remain a separately labelled method. See `tests/impact/`, `CARBON_METHODS.md` and impact contract validators, not unsupported aggregate savings claims.

## 18. Carbon Methodology And Boundaries

`extensions/uk_factors_2025.json` records reviewed DESNZ 2025 rows, workbook URL/hash, publication date, scopes and source identifiers. The official 2026 edition is available and its publication/update metadata is recorded, but 2026 numeric rows have not been reviewed/substituted. Frozen 2025 comparisons are reproducible but do not satisfy an undisclosed current-vintage claim. GHG Protocol Project Protocol is referenced as guidance; the scenario engine is not certified project/PCAF accounting, a lifecycle analysis or carbon-credit method. Manufacturing/embodied emissions and automatic future-grid changes are excluded.

`impact/solar_generation.py` supports JRC PVGIS 5.3 with complete installation parameters, reviewed response SHA-256, retrieval time, radiation years, matching echoed inputs and annual-energy units. Archived bytes or a matching fetched response are required; source mismatch/outage fails without fallback yield. Region is a label, not a geocoder; demand/self-consumption are not derived. Tests validate the adapter, not independently sourced live site forecasts. Method-owner details and historical India source-access limitations remain in `CARBON_METHODS.md`, which this pass does not edit.

## 19. Impact Passport

Detailed impact contracts retain baseline/scenario, signed difference, units, assumptions, factors, versions, boundary, cutoff, calculation timestamp and completeness issues. AVAILABLE requires unit-matched carbon fields; legacy CO2 and UK CO2e cannot be silently converted or combined. `/simulate` stores scenario inputs/results with method provenance; UI exposes the passport without claiming a measured outcome. Trained recommendations require source-supported physical assumptions. Evidence is `contracts/impact_detail.py`, `impact/uk_adapter.py`, `extensions/api.py`, UI tests and `CONTRACTS.md`.

## 20. LLM Architecture

`llm/service.py`, `schema.py` and `http_provider.py` restrict optional generation to approved structured claims/sentence selection, with bounded HTTP calls, validation, fallback, cache and measurements. The API preserves headline, explanation, reasons, impact/confidence/action text and missing information. Raw merchant text and uncontrolled model features are not prompt input; the LLM cannot score, calculate or approve.

`llm/provider_manifest.json` pins OpenAI Chat Completions, `gpt-4.1-mini-2025-04-14`, `grounded-selection-v1`, temperature 0 and 1600 output tokens. Status is selected, not live evaluated. `llm/live_evaluation.py` is implemented outside default gates and requires explicit paid authorization. See LLM-owner `LLM_EVAL.md` and `src/greenpath/llm/README.md`; no paid provider run is claimed.

## 21. LLM Programmatic Checks

Schema and grounding checks enforce approved numeric/unit/reason/product mappings, eligibility disclaimer, supported claims and missing-information handling. Provider/schema/grounding/timeout failures use deterministic templates. Final output safety can include fallback; it is not raw-provider accuracy. `tests/llm/` and `reports/explanation_evaluation.json` are the evidence sources. A narrow approved-sentence surface reduces exposure but does not certify all future prompts/models against injection.

## 22. LLM Adversarial Evaluation

`llm/evaluation.py` supplies fixed offline validator cases across states, missing/conflicting/low-confidence evidence, Paperless, missing/zero/negative impact, multiple products and unsupported/adversarial claims. `reports/explanation_evaluation.json` records scoped metrics and fallback reasons. These response mutations test the system's validators and safe display, not natural-traffic fallback rates or a live model's jailbreak resistance.

The optional live evaluator uses 100-200 distinct synthetic input cases, first-pass cache disabled, per-case acceptance/fallback/usage/latency/cost and a separate cache experiment. It stops on provider failures and records incomplete runs. Grounded final output includes safe fallbacks; prices are configured, not independently verified. No live evaluation report or measured live metrics are claimed in this pass.

## 23. Scenario Tests

`demo/evaluate.py` and `reports/scenario_evaluation.json` cover six deterministic fixture personas and the relevance states. Trained integration tests build fresh temporary models and exercise adapters, unavailable/explicit physical impact, inference and API safety. `tests/integration/test_traceability_lifecycle.py` covers immutable persisted decisions, linked explanations, restart durability, factual rescoring, source completion, idempotency, authorization/timing failures, rollback, SHAP and capacity helpers. `test_optional_analytics.py` covers additional analytics. Test presence/source inspection is not a newly executed full-suite pass; final counts belong to main.

## 24. Trend Analytics

`api/portfolio.py` distinguishes current funnel/opportunity counts from historical monthly observations. It exposes propensity, validated-confidence coverage, Trust, abstention, Paperless activity and recorded synthetic outcome evidence. Physical totals group compatible product/units/boundary/period/method/factor version; no universal cross-product total is produced. Conversion denominators include recorded outcomes only; missing historical quality/impact remains unavailable. Current scores/facts are never copied backwards to fill gaps. API/extension filters include region, segment, product, validated confidence, impact and data quality. See history contracts, trained adapter, UI workspaces and analytics integration tests; historical modelled potential is not realised savings.

## 25. Fairness / Proxy-Risk Analysis

Default propensity feature views exclude audit-only age/income/location fields. Controlled proxy ablations and subgroup discrimination/calibration/ranking diagnostics are in `reports/ml_evaluation.json`; system recommendations, abstention, Trust and confidence coverage are audited in `reports/system_performance.json`. Group attributes are for audit/aggregate analysis, not financial decisions. Removing explicit fields does not remove proxies, and small synthetic subgroups/outcome counts cannot certify fairness. Earlier system coverage may predate confidence suppression; use regenerated matching evidence and `RESPONSIBLE_AI.md`.

## 26. System Performance

`reports/pipeline_timings.json` records pipeline stages/process memory; `reports/system_performance.json` records local fixture/trained startup, API samples, cache experiments, fairness and ranking ablation. Its boundary is in-process FastAPI TestClient, excluding network transport, Streamlit/browser rendering and live LLM calls. Tiny repeated samples/cache warm-up do not establish production throughput, tail latency or an independently instrumented latency for every specification stage. Historical launcher smoke is preserved in `IMPLEMENTATION_PLAN.md`, not certified for the new source version. Final runtime/gate evidence belongs to main.

## 27. Cost Analysis

Default templates require no paid LLM request, but that is not zero infrastructure cost or a measured zero-cost live provider. Live input/output/cached usage, latency, current pricing and cost per 1,000 remain unmeasured. The evaluator requires explicit current pricing for all three token classes and leaves missing usage/cost null; cache experiment calls enter provider totals. Provider availability/pricing must be checked externally before authorized spending. Offline cache rates and adversarial fallback rates are not live cost forecasts. Reproduction/configuration details are in `REPRODUCIBILITY.md` and LLM-owner docs.

## 28. Limitations

Synthetic outcomes/generator correlations dominate ML credibility; aggregate energy anchors do not establish representative banking behaviour. Merchant generalisation, small product/cohort samples, shift, calibration uncertainty and proxy disparities remain risks. All inspected core confidence is suppressed; optional signals also lack independent reliability validation. Missing physical inputs can make impact and confidence-dependent ranking unavailable. Reviewed factors are 2025 despite 2026 availability, and PVGIS requires actual reviewed response evidence. No reviewed Paperless lifecycle carbon, guaranteed reduction, financial eligibility or carbon-credit claim is implemented.

Local source updates are bounded vehicle/digital/ownership overrides with event/availability/cutoff provenance and deployed inference, not arbitrary source ETL, unchanged rolling-evidence recomputation, model retraining or bank writeback. Feedback completion is not factual closure. SQLite decisions/explanations persist with evidence-stable IDs, but local demo audit storage is not production tamper-proof governance. Campaign delivery, production IAM, secure hosting, privacy/retention controls, independently observed outcomes and paid live-provider measurement are not demonstrated. Final gates are still owned by main.

## 29. Reproducibility

Python 3.12, `uv.lock` and `make all` provide the serial core pipeline/test/offline-evaluation entrypoint. `reports/RUN_MANIFEST.json` captures seed/configuration/environment and artifact hashes; prediction and split manifests support comparison. Source/schema changes require regeneration of data/snapshots/models/reports together plus separate `make schemas` and build checks. Optional model training is a separate command, not part of `make all`. New SHAP audits require newly trained background artifacts. Local SQLite state can affect journey/campaign outcomes; use isolated fresh state while preserving existing data. No paid live evaluator runs by default. See `REPRODUCIBILITY.md` for commands, modes and source controls.

## 30. Future Work

Known external requirements and unverified acceptance items are explicit:

- Main must finish full gates and record revision, manifest/hashes, final counts, regenerated schema parity, build and fixture/trained runtime smoke evidence. This report does not assert their outcome.
- Authorized provider evaluation needs credentials, exact dated-model availability, current verified pricing, paid-run permission and privacy/data-transfer review; report measured usage, latency, cost and quality, not selected-manifest metadata alone.
- Current-vintage reporting needs review of official 2026 factor rows and versioned regeneration; physical Solar forecasts need reviewed site-specific PVGIS source responses plus demand/self-consumption evidence. No generic defaults should fill these gaps.
- Real validation needs lawful representative banking data, observed adoption/outcomes, stronger unseen-merchant performance assessment, sufficiently sized confidence-release cohorts, independent optional-product confidence and fairness review.
- Deployment needs bank-authorized eligibility/suitability processes, production IAM/security, privacy/retention/deletion policy, monitoring, source ingestion/writeback, real campaign controls/delivery and governed retraining. The implemented local factual lifecycle is not a substitute.
- Lifecycle/embodied carbon, reviewed Paperless carbon and any project/financed-emissions or credit methodology require separate sourced review. Sensitivity and planning remain non-causal modelled scenarios.
