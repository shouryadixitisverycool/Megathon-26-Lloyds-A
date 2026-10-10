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

Selected model (by validation ROC-AUC, Brier tie-break): **LOGISTIC** `paperless_banking_logreg_v1`; calibration **platt** `paperless_banking_logreg_platt_v2_0096b0e8b327dad0` fitted on validation only.
Train 530 (67 positive), validation 60 (10), held-out test 105 (20).

**Held-out test metrics** (calibrated probabilities; confusion metrics at each model's validation-chosen F1 threshold):

| model | ROC-AUC | PR-AUC | Brier | ECE | P@10% | R@10% | Lift@10% | precision | recall | F1 | threshold |
|---|---|---|---|---|---|---|---|---|---|---|---|
| HEURISTIC | 0.527 | 0.206 | 0.175 | 0.056 | 0.091 | 0.050 | 0.477 | 0.222 | 0.400 | 0.286 | 0.184 |
| LOGISTIC | 0.617 | 0.328 | 0.148 | 0.053 | 0.273 | 0.150 | 1.432 | 0.232 | 0.800 | 0.360 | 0.150 |
| GRADIENT_BOOSTING | 0.655 | 0.368 | 0.150 | 0.032 | 0.273 | 0.150 | 1.432 | 0.200 | 0.900 | 0.327 | 0.136 |

Calibration effect (selected model, test): Brier 0.154 → 0.148, ECE 0.074 → 0.053.

Baseline comparison: the selected model's ROC-AUC 0.617 is materially better than the heuristic baseline (0.527); logistic baseline 0.617.

**Generator shift** (models trained on generator A, scored on perturbed generator B):

| model | ROC-AUC A | ROC-AUC B | PR-AUC A | PR-AUC B | ΔBrier | ΔECE (calibration shift) | ΔLift@10% |
|---|---|---|---|---|---|---|---|
| HEURISTIC | 0.527 | 0.706 | 0.206 | 0.228 | -0.066 | -0.013 | 1.970 |
| LOGISTIC | 0.617 | 0.708 | 0.328 | 0.226 | -0.044 | -0.011 | 0.648 |
| GRADIENT_BOOSTING | 0.655 | 0.673 | 0.368 | 0.210 | -0.044 | 0.016 | 0.281 |

**Missing-data stress** (selected model, held-out test):

| scenario | ROC-AUC | PR-AUC | Brier | ECE | Lift@10% |
|---|---|---|---|---|---|
| mileage_missing | 0.617 | 0.328 | 0.148 | 0.053 | 1.432 |
| energy_missing | 0.617 | 0.328 | 0.148 | 0.053 | 1.432 |
| home_ownership_unknown | 0.617 | 0.328 | 0.148 | 0.053 | 1.432 |
| sustainability_preference_missing | 0.627 | 0.327 | 0.147 | 0.057 | 1.432 |
| digital_missing | 0.584 | 0.369 | 0.160 | 0.096 | 1.909 |
| random_30pct_cells | 0.661 | 0.322 | 0.152 | 0.054 | 1.432 |

**Temporal holdout:** retrained at 2026-03-31, tested at 2026-06-30 on held-out customers: ROC-AUC 0.585, Brier 0.150, ECE 0.037.

**Proxy ablation** (spec 12.2):

| variant | ROC-AUC | Brier | ECE | selection-rate range across income bands | max |calibration gap| across income bands |
|---|---|---|---|---|---|
| without proxies (default) | 0.617 | 0.148 | 0.053 | 0.178 | 0.264 |
| with income band + region | 0.596 | 0.154 | 0.032 | 0.471 | 0.247 |

Decision: default to the model **without** proxies (ΔROC-AUC with proxies = -0.021); proxies are not justified unless they add clear value without widening disparity.

**Subgroup diagnostics** (audit-only attributes, selected model):

*age_band*

| group | n | positives | roc_auc | mean_pred | observed_rate | calibration_gap | selection_rate | fpr | fnr |
|---|---|---|---|---|---|---|---|---|---|
| 18-24 | 3 | 0 | n/a | 0.192 | 0.000 | 0.192 | 1.000 | 1.000 | n/a |
| 25-34 | 7 | 1 | 1.000 | 0.200 | 0.143 | 0.057 | 0.714 | 0.667 | 0.000 |
| 35-44 | 23 | 4 | 0.566 | 0.163 | 0.174 | -0.011 | 0.783 | 0.737 | 0.000 |
| 45-54 | 28 | 6 | 0.773 | 0.153 | 0.214 | -0.062 | 0.643 | 0.591 | 0.167 |
| 55-64 | 24 | 7 | 0.639 | 0.167 | 0.292 | -0.125 | 0.583 | 0.529 | 0.286 |
| 65+ | 20 | 2 | 0.389 | 0.158 | 0.100 | 0.058 | 0.550 | 0.556 | 0.500 |

*income_band*

| group | n | positives | roc_auc | mean_pred | observed_rate | calibration_gap | selection_rate | fpr | fnr |
|---|---|---|---|---|---|---|---|---|---|
| 100k+ | 7 | 3 | 0.250 | 0.164 | 0.429 | -0.264 | 0.714 | 0.750 | 0.333 |
| 25-50k | 35 | 5 | 0.467 | 0.161 | 0.143 | 0.018 | 0.629 | 0.633 | 0.400 |
| 50-75k | 34 | 7 | 0.762 | 0.171 | 0.206 | -0.034 | 0.676 | 0.630 | 0.143 |
| 75-100k | 9 | 2 | 0.714 | 0.154 | 0.222 | -0.068 | 0.778 | 0.714 | 0.000 |
| <25k | 20 | 3 | 0.686 | 0.158 | 0.150 | 0.008 | 0.600 | 0.529 | 0.000 |

*region*

| group | n | positives | roc_auc | mean_pred | observed_rate | calibration_gap | selection_rate | fpr | fnr |
|---|---|---|---|---|---|---|---|---|---|
| East Midlands | 10 | 2 | 0.750 | 0.150 | 0.200 | -0.050 | 0.600 | 0.500 | 0.000 |
| East of England | 11 | 2 | 0.833 | 0.168 | 0.182 | -0.013 | 0.818 | 0.778 | 0.000 |
| London | 12 | 1 | 0.909 | 0.145 | 0.083 | 0.061 | 0.500 | 0.455 | 0.000 |
| North East | 5 | 0 | n/a | 0.168 | 0.000 | 0.168 | 0.800 | 0.800 | n/a |
| North West | 13 | 3 | 0.200 | 0.172 | 0.231 | -0.059 | 0.769 | 0.900 | 0.667 |
| Scotland | 8 | 1 | 0.429 | 0.154 | 0.125 | 0.029 | 0.375 | 0.429 | 1.000 |
| South East | 12 | 3 | 0.519 | 0.162 | 0.250 | -0.088 | 0.583 | 0.556 | 0.333 |
| South West | 5 | 1 | 0.250 | 0.186 | 0.200 | -0.014 | 1.000 | 1.000 | 0.000 |
| UNKNOWN | 2 | 0 | n/a | 0.153 | 0.000 | 0.153 | 0.500 | 0.500 | n/a |
| Wales | 7 | 4 | 0.833 | 0.221 | 0.571 | -0.350 | 1.000 | 1.000 | 0.000 |
| West Midlands | 11 | 1 | 0.700 | 0.152 | 0.091 | 0.061 | 0.545 | 0.500 | 0.000 |
| Yorkshire | 9 | 2 | 0.786 | 0.152 | 0.222 | -0.070 | 0.556 | 0.429 | 0.000 |

**Confidence:** SUPPRESSED — Spearman(bin, error) n/a, error top-30% n/a vs bottom-30% n/a. See reports/CONFIDENCE_VALIDATION.md.

## Known limitations

- Synthetic labels; performance does not transfer to real data without re-validation.
- Reason codes summarise the transparent logistic surrogate's positive contributions and controlled thresholds; they are explanations of evidence, not causal claims.
