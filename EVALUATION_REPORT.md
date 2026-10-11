# Greenr Evaluation Report

> **Evidence status:** draft assembled from checked-in artifacts without rerunning the pipeline. All data, outcomes and personas are synthetic. The reported values do not establish real-world predictive performance, financial eligibility, realised adoption, or verified carbon reduction.

## 1. Executive summary

Greenr evaluates a synthetic sustainability-opportunity system across seven areas: data quality, propensity models and recommendation policy, transaction categorisation, sustainability impact, explanation grounding, system performance, and scenario behavior. The design uses customer-level train/validation/test separation, point-in-time features, explicit heuristic baselines, calibrated probabilities, abstention states, deterministic impact calculations, and grounded explanation validation.

The strongest checked-in evidence is the explicit leakage control, baseline comparison, unseen-merchant categorisation evaluation, scenario coverage, and offline explanation validation. The principal limitations are synthetic labels, relatively small product-positive test cohorts, weak unseen-merchant performance for several transaction classes, no live-LLM evaluation, and slow trained startup/trend responses.

The checked-in evidence is **not currently one coherent release set**:

| Artifact | Reported cohort |
|---|---:|
| `DATA_CARD.md` | 4,010 customers |
| `LEAKAGE_AUDIT.md` | 4,010 customers |
| `reports/system_performance.json` | 4,010 trained customers |
| Core model cards | product-specific subsets of the 4,010-customer run |
| `reports/RUN_MANIFEST.json` | 20,010 customers |

Therefore, the numerical results below are an inventory of checked-in evidence, not certification of the current worktree. Before submission, regenerate data, models, reports, cards and the run manifest together and replace this warning with the final commit, cohort size and successful gate result.

## 2. Evaluation design

### 2.1 Timeline and labels

| Item | Definition |
|---|---|
| Feature cutoff | 2026-06-30 |
| Outcome window | `(2026-06-30, 2026-09-28]`, 90 days |
| Prediction timestamp | 2026-10-10 09:00 |
| Label | Product adoption recorded inside the outcome window |
| Negative label | Complete follow-up with no adoption in the window |
| Unsupported label | Incomplete outcome observation; retained as null rather than forced negative |
| Population | Product-specific customers not already holding/adopting that product at cutoff |

Outcomes are synthetically generated from documented coefficients, interactions, latent stochastic drivers and noise. Generator latent variables are not written to model input tables. This makes labels reproducible but does not make them representative of real customer behavior.

### 2.2 Splits and model selection

Splits are deterministic, seeded and assigned by customer, never by transaction or prediction row. Demo personas are excluded. The current split implementation reserves independent train, validation, confidence-release and final-test cohorts. Model type, calibration and operational threshold are selected without consulting final-test labels. The final test set is used for reporting only.

| Purpose | Data use |
|---|---|
| Train | Fit heuristic support, logistic/boosted propensity candidates and preprocessing |
| Validation | Select model, calibration method and F1 operating threshold |
| Confidence release | Independently decide whether model-confidence values may be displayed |
| Test | Report held-out discrimination, ranking, calibration and confusion metrics |
| Perturbed generator | Diagnose synthetic distribution shift |
| Historical cutoff | Diagnose temporal generalisation and point-in-time correctness |

Seeds recorded in `reports/RUN_MANIFEST.json` are data `42`, split `43`, model `44`, and perturbation `45`.

### 2.3 Metrics

| Metric | Interpretation |
|---|---|
| ROC-AUC | Ranking discrimination across thresholds; insensitive to a chosen operating threshold |
| PR-AUC | Precision-recall discrimination; more informative under class imbalance |
| Brier score | Mean squared probability error; lower is better |
| ECE | Expected calibration error; lower is better |
| Precision / recall / F1 | Thresholded recommendation performance at a validation-selected threshold |
| Precision@10% / Recall@10% | Quality and coverage in the highest-scored 10% |
| Lift@10% | Top-decile positive rate divided by the cohort base rate |
| Macro F1 | Equal-weight mean transaction-category F1 |
| Weighted F1 | Support-weighted transaction-category F1 |
| Groundedness | Explanation contains only approved evidence-backed claims |
| Numeric consistency | Explanation numbers and units match structured evidence |
| p50 / p95 latency | Median and 95th-percentile latency over the documented sample |

## 3. Data quality and leakage prevention

### 3.1 Sources and assumptions

No real customer or confidential banking data is used. Synthetic source tables include customers, transactions, financial products, vehicle history, energy usage and digital usage. Transaction truth and merchant metadata are evaluation-only tables and are excluded from the feature pipeline.

Synthetic energy distributions are anchored to the DESNZ Great Britain 2024 subnational domestic-meter summary. In the 4,010-customer data-card run:

| Fuel | Complete consumers | Synthetic mean kWh | Reference mean kWh | Synthetic median kWh | Reference median kWh |
|---|---:|---:|---:|---:|---:|
| Electricity | 2,685 | 3,379.591 | 3,323 | 2,644.800 | 2,471 |
| Gas | 2,376 | 11,438.419 | 11,359 | 10,036.400 | 9,859 |

These aggregate similarities are plausibility checks, not proof that the synthetic population represents banking customers.

### 3.2 Point-in-time controls

The feature registry records source, event time, availability time, model-use policy and proxy risk. Customer 360 uses only evidence whose event and availability timestamps are visible at the cutoff. Outcomes and transaction truth cannot enter the feature builder.

Checked-in leakage evidence reports:

| Check | Result |
|---|---|
| Canonical Customer 360 rebuild | PASS: 84 features x 4,010 customers, no differences |
| Historical rebuilds | PASS at all six monthly cutoffs from 2026-01-31 through 2026-06-30 |
| Customer split disjointness | PASS: five cohorts, no overlap |
| Target-like feature names | PASS for all products |
| Product post-adoption flags | PASS; used only for population exclusion |
| Audit/proxy fields | PASS; age, income, postcode and region excluded from default propensity inputs |
| Source event and availability cutoffs | PASS for transactions, products, vehicles, energy, digital, customer history and ownership history |

The approved feature counts are EV Finance `25`, Green Home `31`, Solar Finance `22`, and Paperless Banking `13`.

## 4. ML propensity and recommendation evaluation

### 4.1 Approach

Each product compares a simple heuristic baseline, logistic regression, and gradient boosting. Logistic models use numeric features with missing-value handling and scaling; boosted models use the same approved point-in-time feature policy. Validation ROC-AUC with Brier tie-breaking determines deployment. Platt or isotonic calibration is selected on validation evidence, and the operating threshold maximises validation F1.

The recommendation layer is stricter than the propensity model. It can return `RECOMMEND`, `DO_NOT_RECOMMEND`, `INSUFFICIENT_INFORMATION`, `CONFLICT_REQUIRES_REVIEW`, `NOT_APPLICABLE`, or `SUPPRESSED`. Propensity does not establish credit eligibility, marketing permission, suitability, or impact availability.

### 4.2 Cohort sizes

Product exclusions and unsupported labels produce different cohorts.

| Product | Train (positive) | Validation (positive) | Test (positive) | Selected model |
|---|---:|---:|---:|---|
| EV Finance | 1,714 (104) | 230 (16) | 345 (28) | Gradient boosting |
| Green Home | 1,422 (113) | 198 (17) | 277 (26) | Logistic |
| Solar Finance | 1,783 (103) | 249 (17) | 354 (24) | Logistic |
| Paperless Banking | 530 (67) | 60 (10) | 105 (20) | Logistic |

### 4.3 Held-out test metrics and baselines

All confusion metrics use each candidate's validation-selected threshold. These values come from the checked-in 4,010-customer model-card run.

| Product | Model | ROC-AUC | PR-AUC | Brier | ECE | P@10% | R@10% | Lift@10% | Precision | Recall | F1 | Threshold |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| EV | Heuristic baseline | 0.714 | 0.150 | 0.074 | 0.011 | 0.143 | 0.179 | 1.760 | 0.123 | 0.250 | 0.165 | 0.080 |
| EV | Logistic | 0.711 | 0.199 | 0.071 | 0.012 | 0.171 | 0.214 | 2.112 | 0.132 | 0.321 | 0.188 | 0.102 |
| EV | Gradient boosting, selected | 0.693 | 0.181 | 0.072 | 0.011 | 0.114 | 0.143 | 1.408 | 0.143 | 0.357 | 0.204 | 0.100 |
| Green Home | Heuristic baseline | 0.689 | 0.164 | 0.089 | 0.021 | 0.250 | 0.269 | 2.663 | 0.154 | 0.462 | 0.231 | 0.120 |
| Green Home | Logistic, selected | 0.675 | 0.163 | 0.084 | 0.019 | 0.179 | 0.192 | 1.902 | 0.157 | 0.308 | 0.208 | 0.122 |
| Green Home | Gradient boosting | 0.658 | 0.188 | 0.083 | 0.010 | 0.179 | 0.192 | 1.902 | 0.177 | 0.423 | 0.250 | 0.109 |
| Solar | Heuristic baseline | 0.733 | 0.131 | 0.078 | 0.039 | 0.139 | 0.208 | 2.049 | 0.142 | 0.708 | 0.236 | 0.086 |
| Solar | Logistic, selected | 0.750 | 0.170 | 0.060 | 0.007 | 0.194 | 0.292 | 2.868 | 0.154 | 0.333 | 0.211 | 0.134 |
| Solar | Gradient boosting | 0.707 | 0.130 | 0.062 | 0.012 | 0.139 | 0.208 | 2.049 | 0.135 | 0.542 | 0.217 | 0.089 |
| Paperless | Heuristic baseline | 0.527 | 0.206 | 0.175 | 0.056 | 0.091 | 0.050 | 0.477 | 0.222 | 0.400 | 0.286 | 0.184 |
| Paperless | Logistic, selected | 0.617 | 0.328 | 0.148 | 0.053 | 0.273 | 0.150 | 1.432 | 0.232 | 0.800 | 0.360 | 0.150 |
| Paperless | Gradient boosting | 0.655 | 0.368 | 0.150 | 0.032 | 0.273 | 0.150 | 1.432 | 0.200 | 0.900 | 0.327 | 0.136 |

The selected EV and Green Home models do not outperform the heuristic baseline on held-out ROC-AUC. This is reported rather than hidden because selection occurred on validation data; switching after inspecting test performance would leak test information. Solar shows a modest selected-model improvement, while Paperless shows the clearest improvement over its heuristic baseline.

### 4.4 Calibration, shift and missingness

| Product | Selected-model Brier raw -> calibrated | ECE raw -> calibrated | Perturbed ROC-AUC | Temporal ROC-AUC | Random 30% missing ROC-AUC |
|---|---|---|---:|---:|---:|
| EV | 0.073 -> 0.072 | 0.034 -> 0.011 | 0.645 | 0.733 | 0.649 |
| Green Home | 0.087 -> 0.084 | 0.029 -> 0.019 | 0.651 | 0.714 | 0.559 |
| Solar | 0.060 -> 0.060 | 0.016 -> 0.007 | 0.743 | 0.714 | 0.714 |
| Paperless | 0.154 -> 0.148 | 0.074 -> 0.053 | 0.708 | 0.585 | 0.661 |

Perturbed results describe a second synthetic generator, not external validation. Missingness sensitivity is material, especially for Green Home. Temporal tests use an earlier cutoff and remain synthetic.

### 4.5 Confidence release

Runtime confidence is intended to estimate whether the thresholded propensity decision is correct; it is not propensity or eligibility. Release requires at least 200 independent rows plus monotonic error separation. Checked-in decisions suppress all four products:

| Product | Release rows | Decision | Reason |
|---|---:|---|---|
| EV Finance | 128 | SUPPRESSED | Below 200-row minimum |
| Green Home | 95 reported release rows | SUPPRESSED | Insufficient validation/release evidence |
| Solar Finance | 114 | SUPPRESSED | Below 200-row minimum |
| Paperless Banking | 39 reported release rows | SUPPRESSED | Insufficient validation/release evidence |

Suppressing unsupported confidence is the intended safe behavior.

## 5. Transaction categorisation

Transactions are classified using deterministic high-purity brand/boundary rules followed by word/character TF-IDF logistic regression. Evaluation groups by merchant so the unseen split contains merchant identities absent from fitting.

| Model | Unseen macro F1 | Unseen weighted F1 | Known macro F1 | Known weighted F1 | Unseen rule coverage |
|---|---:|---:|---:|---:|---:|
| Hybrid rules + TF-IDF/LR | 0.543 | 0.524 | 0.998 | 0.999 | 14.2% |
| Normalised TF-IDF/LR | 0.511 | 0.494 | 0.998 | 0.999 | 0.0% |
| Plain raw-text TF-IDF/LR baseline | 0.453 | 0.440 | 0.992 | 0.997 | 0.0% |

The hybrid improves unseen macro F1 by `0.089` over the plain baseline. The evaluation includes 127 merchants: 88 train and 39 unseen; 172,023 fit rows, 43,006 known-merchant holdout rows, and 84,971 unseen-merchant rows. Rules achieve 100% measured accuracy at 14.2% unseen coverage; the model accuracy on remaining unseen rows is 50.9%.

Key failure cases are Fuel recall `0.133`, Home Improvement F1 `0.005`, and Automotive recall `0.200`. Electricity, Public Transport and Utilities are much stronger. No unseen GAS merchant appears, so GAS unseen precision/recall/F1 is undefined. These results only measure the synthetic merchant catalogue's naming conventions.

## 6. Sustainability impact

Impact calculations are deterministic physical scenarios, separate from propensity. Inputs, units, baseline, scenario, factor identifiers, source metadata, accounting boundary, assumptions, issues, method version and calculation timestamp are retained. Missing or incompatible evidence produces a null impact with an explicit unavailable status rather than zero.

### 6.1 Methods and examples

| Product | Implemented boundary | Checked numeric illustration |
|---|---|---:|
| EV Finance | Fossil fuel combustion versus charging-generation emissions | 553.194 kg CO2/year for the documented legacy example |
| Green Home | Baseline versus scenario grid import | 716 kg CO2/year |
| Solar Finance | Reduction in grid import from documented self-consumption | 1,790 kg CO2/year |
| Paperless Banking | Carbon comparison not established | Carbon unavailable; activity-only statements/sheets metrics allowed |

The UK method uses frozen DESNZ operational CO2e factors and explicit physical assumptions. The current methods document `0.18436 kg CO2e/kWh` for UK electricity, `0.21252 kg CO2e/kWh` gross-CV gas, `2.65594 kg CO2e/litre` petrol, and `3.19455 kg CO2e/litre` diesel. Manufacturing, embodied emissions, maintenance, end-of-life effects and causal attribution are excluded.

`CARBON_METHODS.md` describes the reviewed 2026 catalogue as current, while `REPRODUCIBILITY.md` still describes the 2025 subset as the reviewed source. The final release documentation and generated passports must be reconciled to the actual runtime catalogue before these factor values are cited as release evidence.

### 6.2 Evaluation evidence

The 24 fixture recommendation scenarios all pass and include expected impact availability/unavailability. Portfolio evidence keeps EV, home and solar values in separate compatible groups and reports one unavailable impact rather than silently summing incompatible values. Paperless reports no carbon value.

There is no empirical carbon-accuracy metric because no measured counterfactual outcomes exist. Correctness evidence is formula/unit validation, deterministic examples, fail-closed invalid-input behavior, factor provenance and reproducibility. Potential scenario differences must not be described as realised savings, financed emissions, offsets or carbon credits.

## 7. LLM and explanation evaluation

The optional provider is constrained to approved structured claims and sentence identifiers. Final explanations are validated for product, state, reasons, numbers, units, disclaimers, missing information and unsupported claims. Provider errors, malformed responses, timeouts and grounding failures fall back to deterministic templates.

| Offline metric | Result |
|---|---:|
| Cases | 200 |
| Passed | 200 |
| Groundedness rate | 1.000 |
| Numeric consistency rate | 1.000 |
| Unsupported claims | 0 |
| Fallback rate | 0.630 |
| Mean local latency | 11.465 ms |
| Live-provider latency | Not measured |
| Live-provider cost | Not measured |

The high fallback rate is expected because adversarial and invalid responses are deliberately included. These fixed offline cases evaluate validators and safe final output, not natural live-provider quality. No paid provider run, token usage, live latency or cost evidence is checked in.

## 8. Scenario-based evaluation

The fixture suite contains six personas across four products, producing 24 decisions. All 24 pass their expected state and impact behavior.

| State | Count | Covered condition |
|---|---:|---|
| RECOMMEND | 4 | Supported relevant opportunity |
| DO_NOT_RECOMMEND | 4 | Evidence does not meet relevance rules |
| INSUFFICIENT_INFORMATION | 4 | Required evidence missing, stale, future or OOD |
| CONFLICT_REQUIRES_REVIEW | 4 | Material evidence conflict |
| NOT_APPLICABLE | 4 | Product already adopted or applicability rule fails |
| SUPPRESSED | 4 | Consent or policy suppression |

Portfolio scenario output contains 24 decisions, four recommendations, 16 trusted decisions, four limited decisions and four conflicts. Validated confidence is absent for all 24 fixture decisions, while physical impact is missing for nine. This demonstrates that propensity, Trust, confidence, recommendation state and impact availability are handled independently.

## 9. System performance and reliability

Measurements use five local in-process FastAPI `TestClient` requests per endpoint. They include provider startup and SQLite decision persistence but exclude external network transport, browser rendering and live LLM latency. Five samples are illustrative, not production tail-latency evidence. `DATASET_ENGINEERING.md` explicitly identifies this retained benchmark as stale and inconsistent with the latest dataset release, so the values below are historical diagnostics that must be regenerated.

### 9.1 API latency

| Endpoint | Fixture p50 / p95 ms | Trained p50 / p95 ms |
|---|---:|---:|
| Health | 0.674 / 1.886 | 0.798 / 40.449 |
| Customer | 0.836 / 1.136 | 1.874 / 7.848 |
| Recommendations | 7.647 / 12.066 | 10.886 / 56.374 |
| Explanation | 9.643 / 10.497 | 12.827 / 22.962 |
| Portfolio summary | 38.550 / 52.464 | 1.090 / 1.690 |
| Portfolio trends | 1.960 / 2.313 | 2,233.352 / 14,553.799 |

### 9.2 Startup, memory and pipeline cost

| Metric | Checked-in value |
|---|---:|
| Fixture startup | 0.012 s |
| Trained startup | 302.844 s |
| Trained benchmark total | 352.612 s |
| Trained portfolio scoring/ranking stage | 21.879 s |
| Trained peak process RSS | 1,791,541,248 bytes |
| Pipeline train stage | 263.670 s |
| Pipeline peak process RSS | 1,300,660,224 bytes |
| Explanation cache hit rate | 80% over five measured requests |
| Offline template provider cost | 0 direct provider cost |
| Live LLM cost | Not measured |

The trained startup and trend endpoint are the primary performance concerns. Offline cost `0` means no paid provider call; it does not mean infrastructure is free.

## 10. Reproducibility

The intended clean-run entrypoint is:

```bash
make all
GREENR_PROVIDER=trained make app
```

Python 3.12 and `uv.lock` constrain the environment. Generated manifests retain seeds, timeline, package versions, artifact hashes, input hashes, processed hashes and split-manifest hashes. Individual reports preserve model, calibration, rule, factor and prompt versions.

### 10.1 Current release gate

| Gate | Status in this document |
|---|---|
| Locked environment | Documented; not rerun for this report |
| End-to-end `make all` | TBD: no new execution performed |
| Final coherent customer count | TBD: checked-in artifacts disagree |
| Data/model/report hash coherence | TBD: regenerate together |
| Fixture API/UI smoke | Historical evidence only |
| Trained API/UI smoke | TBD for final release |
| Live LLM evaluation | Not run |
| Schema/build parity | TBD for final release |

## 11. Limitations and interpretation

- All customer behavior, labels and outcomes are synthetic; aggregate public anchors do not validate individual-level relationships.
- Product-positive test counts are small, especially Paperless, so metric uncertainty is substantial.
- Validation-based selection can legitimately produce a model that loses to a heuristic on final test, as seen for EV and Green Home.
- Transaction categorisation generalises poorly for several unseen merchant classes and has no unseen GAS example.
- Distribution-shift and temporal tests remain simulations generated by related code, not independent external datasets.
- Confidence is suppressed for all core products because independent release evidence is insufficient.
- Default propensity features exclude explicit age, income, postcode and region, but this does not eliminate all proxy effects.
- Impact estimates are operational scenarios with incomplete lifecycle boundaries and no measured counterfactual outcomes.
- Carbon-method documentation currently disagrees about whether the release catalogue is the reviewed 2025 or 2026 subset.
- Paperless carbon is intentionally not claimed.
- Offline explanation validation does not establish live LLM quality, cost, latency or provider availability.
- Performance measurements are local, low-sample and not production load tests.
- Current checked-in reports represent multiple cohort generations and must be regenerated before final submission.

## 12. Evidence index

| Area | Primary evidence |
|---|---|
| Data and assumptions | `DATA_CARD.md`, `DATASET_ENGINEERING.md`, `reports/dataset_quality.json` |
| Splits and leakage | `LEAKAGE_AUDIT.md`, `reports/leakage_checks.json`, `src/greenr/pipelines/split.py` |
| ML metrics and baselines | `MODEL_CARD_*.md`, `reports/ml_evaluation.json`, `reports/predictions/` |
| Confidence release | `reports/CONFIDENCE_VALIDATION.md`, `reports/confidence_validation.json` |
| Transaction categorisation | `reports/TRANSACTION_CATEGORISATION.md`, `reports/transaction_eval.json` |
| Sustainability impact | `CARBON_METHODS.md`, `src/greenr/impact/`, `tests/impact/` |
| Explanations | `LLM_EVAL.md`, `reports/explanation_evaluation.json`, `tests/llm/` |
| Scenarios | `reports/scenario_evaluation.json`, `tests/recommendation/` |
| System performance | `reports/system_performance.json`, `reports/pipeline_timings.json` |
| Reproducibility | `REPRODUCIBILITY.md`, `reports/RUN_MANIFEST.json`, `uv.lock`, `Makefile` |
