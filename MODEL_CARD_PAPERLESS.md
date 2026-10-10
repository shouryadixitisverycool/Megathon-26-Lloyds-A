# Model card — PAPERLESS_BANKING

> Synthetic demonstration model. Not for real customer decisions.

## Intended use

Estimate the probability that a customer adopts PAPERLESS_BANKING within 90 days of the feature cutoff, to prioritise relevant sustainability conversations. **Not** an eligibility, credit or suitability decision.

## Inputs

13 approved Customer 360 features (point-in-time at the cutoff): `paper_statements_3m`, `paper_statements_12m`, `digital_statement_ratio`, `digital_txn_3m_avg`, `app_logins_3m_avg`, `app_logins_trend`, `branch_visits_3m`, `digital_months_present`, `sustainability_preference`, `total_spend_12m_avg`, `txn_count_12m`, `tenure_months`, `txn_months_observed`

Excluded by policy: exact postcode, income band, region, age band (proxy-risk policy, spec 12), the product's own holding flags, and any post-cutoff information.

## Training

Population: customers not already holding the product at the cutoff. Heuristic baseline, logistic regression and histogram gradient boosting trained on the train split; calibration (platt) and the operational threshold (max F1) fitted on validation only; deployed model chosen on validation.

## Evaluation

Selected model (by validation ROC-AUC, Brier tie-break): **LOGISTIC** `paperless_banking_logreg_v1`; calibration **platt** `paperless_banking_platt_v1` fitted on validation only.
Train 497 (67 positive), validation 93 (14), held-out test 99 (20).

**Held-out test metrics** (calibrated probabilities; confusion metrics at each model's validation-chosen F1 threshold):

| model | ROC-AUC | PR-AUC | Brier | ECE | P@10% | R@10% | Lift@10% | precision | recall | F1 | threshold |
|---|---|---|---|---|---|---|---|---|---|---|---|
| HEURISTIC | 0.642 | 0.316 | 0.160 | 0.052 | 0.500 | 0.250 | 2.475 | 0.271 | 0.650 | 0.382 | 0.161 |
| LOGISTIC | 0.640 | 0.385 | 0.152 | 0.084 | 0.300 | 0.150 | 1.485 | 0.243 | 0.850 | 0.378 | 0.116 |
| GRADIENT_BOOSTING | 0.658 | 0.383 | 0.162 | 0.054 | 0.300 | 0.150 | 1.485 | 0.283 | 0.750 | 0.411 | 0.146 |

Calibration effect (selected model, test): Brier 0.157 → 0.152, ECE 0.101 → 0.084.

Baseline comparison: the selected model's ROC-AUC 0.640 is only marginally different from the heuristic baseline (0.642); logistic baseline 0.640.

**Generator shift** (models trained on generator A, scored on perturbed generator B):

| model | ROC-AUC A | ROC-AUC B | PR-AUC A | PR-AUC B | ΔBrier | ΔECE (calibration shift) | ΔLift@10% |
|---|---|---|---|---|---|---|---|
| HEURISTIC | 0.642 | 0.735 | 0.316 | 0.267 | -0.054 | -0.026 | 0.474 |
| LOGISTIC | 0.640 | 0.716 | 0.385 | 0.258 | -0.046 | -0.058 | 1.095 |
| GRADIENT_BOOSTING | 0.658 | 0.647 | 0.383 | 0.239 | -0.050 | -0.033 | 0.604 |

**Missing-data stress** (selected model, held-out test):

| scenario | ROC-AUC | PR-AUC | Brier | ECE | Lift@10% |
|---|---|---|---|---|---|
| mileage_missing | 0.640 | 0.385 | 0.152 | 0.084 | 1.485 |
| energy_missing | 0.640 | 0.385 | 0.152 | 0.084 | 1.485 |
| home_ownership_unknown | 0.640 | 0.385 | 0.152 | 0.084 | 1.485 |
| sustainability_preference_missing | 0.629 | 0.380 | 0.152 | 0.062 | 1.485 |
| digital_missing | 0.615 | 0.372 | 0.176 | 0.140 | 1.485 |
| random_30pct_cells | 0.596 | 0.345 | 0.163 | 0.085 | 1.485 |

**Temporal holdout:** retrained at 2026-03-31, tested at 2026-06-30 on held-out customers: ROC-AUC 0.633, Brier 0.152, ECE 0.030.

**Proxy ablation** (spec 12.2):

| variant | ROC-AUC | Brier | ECE | selection-rate range across income bands | max |calibration gap| across income bands |
|---|---|---|---|---|---|
| without proxies (default) | 0.640 | 0.152 | 0.084 | 0.247 | 0.293 |
| with income band + region | 0.639 | 0.159 | 0.064 | 0.519 | 0.237 |

Decision: default to the model **without** proxies (ΔROC-AUC with proxies = -0.001); proxies are not justified unless they add clear value without widening disparity.

**Subgroup diagnostics** (audit-only attributes, selected model):

*age_band*

| group | n | positives | roc_auc | mean_pred | observed_rate | calibration_gap | selection_rate | fpr | fnr |
|---|---|---|---|---|---|---|---|---|---|
| 18-24 | 3 | 0 | n/a | 0.185 | 0.000 | 0.185 | 1.000 | 1.000 | n/a |
| 25-34 | 6 | 1 | 1.000 | 0.208 | 0.167 | 0.042 | 0.833 | 0.800 | 0.000 |
| 35-44 | 21 | 4 | 0.588 | 0.140 | 0.190 | -0.051 | 0.810 | 0.765 | 0.000 |
| 45-54 | 27 | 6 | 0.921 | 0.140 | 0.222 | -0.082 | 0.741 | 0.667 | 0.000 |
| 55-64 | 23 | 7 | 0.679 | 0.143 | 0.304 | -0.162 | 0.565 | 0.500 | 0.286 |
| 65+ | 19 | 2 | 0.382 | 0.146 | 0.105 | 0.041 | 0.632 | 0.647 | 0.500 |

*income_band*

| group | n | positives | roc_auc | mean_pred | observed_rate | calibration_gap | selection_rate | fpr | fnr |
|---|---|---|---|---|---|---|---|---|---|
| 100k+ | 7 | 3 | 0.333 | 0.135 | 0.429 | -0.293 | 0.571 | 0.750 | 0.667 |
| 25-50k | 33 | 5 | 0.557 | 0.143 | 0.152 | -0.008 | 0.818 | 0.786 | 0.000 |
| 50-75k | 31 | 7 | 0.738 | 0.168 | 0.226 | -0.058 | 0.645 | 0.583 | 0.143 |
| 75-100k | 9 | 2 | 0.714 | 0.128 | 0.222 | -0.094 | 0.667 | 0.571 | 0.000 |
| <25k | 19 | 3 | 0.667 | 0.133 | 0.158 | -0.025 | 0.684 | 0.625 | 0.000 |

*region*

| group | n | positives | roc_auc | mean_pred | observed_rate | calibration_gap | selection_rate | fpr | fnr |
|---|---|---|---|---|---|---|---|---|---|
| East Midlands | 10 | 2 | 0.812 | 0.118 | 0.200 | -0.082 | 0.600 | 0.500 | 0.000 |
| East of England | 11 | 2 | 0.833 | 0.145 | 0.182 | -0.037 | 0.818 | 0.778 | 0.000 |
| London | 12 | 1 | 1.000 | 0.163 | 0.083 | 0.079 | 0.750 | 0.727 | 0.000 |
| North East | 5 | 0 | n/a | 0.156 | 0.000 | 0.156 | 0.800 | 0.800 | n/a |
| North West | 10 | 3 | 0.238 | 0.144 | 0.300 | -0.156 | 1.000 | 1.000 | 0.000 |
| Scotland | 8 | 1 | 0.000 | 0.135 | 0.125 | 0.010 | 0.500 | 0.571 | 1.000 |
| South East | 12 | 3 | 0.556 | 0.148 | 0.250 | -0.102 | 0.583 | 0.556 | 0.333 |
| South West | 4 | 1 | 0.667 | 0.167 | 0.250 | -0.083 | 0.750 | 0.667 | 0.000 |
| UNKNOWN | 2 | 0 | n/a | 0.129 | 0.000 | 0.129 | 0.500 | 0.500 | n/a |
| Wales | 7 | 4 | 0.667 | 0.244 | 0.571 | -0.328 | 0.857 | 0.667 | 0.000 |
| West Midlands | 9 | 1 | 0.500 | 0.114 | 0.111 | 0.003 | 0.444 | 0.500 | 1.000 |
| Yorkshire | 9 | 2 | 1.000 | 0.125 | 0.222 | -0.098 | 0.778 | 0.714 | 0.000 |

**Confidence:** SUPPRESSED — Spearman(bin, error) n/a, error top-30% n/a vs bottom-30% n/a. See reports/CONFIDENCE_VALIDATION.md.

## Known limitations

- Synthetic labels; performance does not transfer to real data without re-validation.
- Reason codes summarise the transparent logistic surrogate's positive contributions and controlled thresholds; they are explanations of evidence, not causal claims.
