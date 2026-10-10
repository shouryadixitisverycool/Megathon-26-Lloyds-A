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

Selected model (by validation ROC-AUC, Brier tie-break): **LOGISTIC** `paperless_banking_logreg_v1`; calibration **platt** `paperless_banking_logreg_platt_v2_7ab04ddfcfcb17a4` fitted on validation only.
Train 530 (67 positive), validation 60 (10), held-out test 105 (20).

**Held-out test metrics** (calibrated probabilities; confusion metrics at each model's validation-chosen F1 threshold):

| model | ROC-AUC | PR-AUC | Brier | ECE | P@10% | R@10% | Lift@10% | precision | recall | F1 | threshold |
|---|---|---|---|---|---|---|---|---|---|---|---|
| HEURISTIC | 0.534 | 0.209 | 0.173 | 0.046 | 0.091 | 0.050 | 0.477 | 0.192 | 0.950 | 0.319 | 0.151 |
| LOGISTIC | 0.612 | 0.313 | 0.150 | 0.053 | 0.182 | 0.100 | 0.955 | 0.214 | 0.150 | 0.176 | 0.198 |
| GRADIENT_BOOSTING | 0.681 | 0.437 | 0.149 | 0.043 | 0.545 | 0.300 | 2.864 | 0.239 | 0.850 | 0.374 | 0.153 |

Calibration effect (selected model, test): Brier 0.155 → 0.150, ECE 0.083 → 0.053.

Baseline comparison: the selected model's ROC-AUC 0.612 is materially better than the heuristic baseline (0.534); logistic baseline 0.612.

**Generator shift** (models trained on generator A, scored on perturbed generator B):

| model | ROC-AUC A | ROC-AUC B | PR-AUC A | PR-AUC B | ΔBrier | ΔECE (calibration shift) | ΔLift@10% |
|---|---|---|---|---|---|---|---|
| HEURISTIC | 0.534 | 0.707 | 0.209 | 0.228 | -0.066 | 0.000 | 2.092 |
| LOGISTIC | 0.612 | 0.692 | 0.313 | 0.209 | -0.045 | 0.004 | 1.003 |
| GRADIENT_BOOSTING | 0.681 | 0.627 | 0.437 | 0.176 | -0.042 | 0.005 | -1.273 |

**Missing-data stress** (selected model, held-out test):

| scenario | ROC-AUC | PR-AUC | Brier | ECE | Lift@10% |
|---|---|---|---|---|---|
| mileage_missing | 0.612 | 0.313 | 0.150 | 0.053 | 0.955 |
| energy_missing | 0.612 | 0.313 | 0.150 | 0.053 | 0.955 |
| home_ownership_unknown | 0.612 | 0.313 | 0.150 | 0.053 | 0.955 |
| sustainability_preference_missing | 0.622 | 0.312 | 0.150 | 0.054 | 0.955 |
| digital_missing | 0.601 | 0.361 | 0.158 | 0.088 | 1.432 |
| random_30pct_cells | 0.582 | 0.312 | 0.153 | 0.052 | 1.432 |

**Temporal holdout:** retrained at 2026-03-31, tested at 2026-06-30 on held-out customers: ROC-AUC 0.582, Brier 0.154, ECE 0.053.

**Proxy ablation** (spec 12.2):

| variant | ROC-AUC | Brier | ECE | selection-rate range across income bands | max |calibration gap| across income bands |
|---|---|---|---|---|---|
| without proxies (default) | 0.612 | 0.150 | 0.053 | 0.235 | 0.274 |
| with income band + region | 0.618 | 0.154 | 0.055 | 0.283 | 0.252 |

Decision: default to the model **without** proxies (ΔROC-AUC with proxies = 0.005); proxies are not justified unless they add clear value without widening disparity.

**Subgroup diagnostics** (audit-only attributes, selected model):

*age_band*

| group | n | positives | roc_auc | mean_pred | observed_rate | calibration_gap | selection_rate | fpr | fnr |
|---|---|---|---|---|---|---|---|---|---|
| 18-24 | 3 | 0 | n/a | 0.199 | 0.000 | 0.199 | 0.333 | 0.333 | n/a |
| 25-34 | 7 | 1 | 1.000 | 0.191 | 0.143 | 0.048 | 0.429 | 0.333 | 0.000 |
| 35-44 | 23 | 4 | 0.539 | 0.163 | 0.174 | -0.011 | 0.130 | 0.158 | 1.000 |
| 45-54 | 28 | 6 | 0.841 | 0.150 | 0.214 | -0.064 | 0.036 | 0.000 | 0.833 |
| 55-64 | 24 | 7 | 0.689 | 0.156 | 0.292 | -0.136 | 0.083 | 0.059 | 0.857 |
| 65+ | 20 | 2 | 0.417 | 0.167 | 0.100 | 0.067 | 0.200 | 0.222 | 1.000 |

*income_band*

| group | n | positives | roc_auc | mean_pred | observed_rate | calibration_gap | selection_rate | fpr | fnr |
|---|---|---|---|---|---|---|---|---|---|
| 100k+ | 7 | 3 | 0.250 | 0.154 | 0.429 | -0.274 | 0.000 | 0.000 | 1.000 |
| 25-50k | 35 | 5 | 0.600 | 0.161 | 0.143 | 0.018 | 0.171 | 0.167 | 0.800 |
| 50-75k | 34 | 7 | 0.725 | 0.172 | 0.206 | -0.034 | 0.235 | 0.222 | 0.714 |
| 75-100k | 9 | 2 | 0.643 | 0.153 | 0.222 | -0.069 | 0.000 | 0.000 | 1.000 |
| <25k | 20 | 3 | 0.627 | 0.151 | 0.150 | 0.001 | 0.000 | 0.000 | 1.000 |

*region*

| group | n | positives | roc_auc | mean_pred | observed_rate | calibration_gap | selection_rate | fpr | fnr |
|---|---|---|---|---|---|---|---|---|---|
| East Midlands | 10 | 2 | 0.812 | 0.141 | 0.200 | -0.059 | 0.000 | 0.000 | 1.000 |
| East of England | 11 | 2 | 0.778 | 0.164 | 0.182 | -0.018 | 0.091 | 0.111 | 1.000 |
| London | 12 | 1 | 0.818 | 0.161 | 0.083 | 0.078 | 0.250 | 0.182 | 0.000 |
| North East | 5 | 0 | n/a | 0.172 | 0.000 | 0.172 | 0.200 | 0.200 | n/a |
| North West | 13 | 3 | 0.400 | 0.173 | 0.231 | -0.058 | 0.154 | 0.200 | 1.000 |
| Scotland | 8 | 1 | 0.286 | 0.157 | 0.125 | 0.032 | 0.000 | 0.000 | 1.000 |
| South East | 12 | 3 | 0.704 | 0.159 | 0.250 | -0.091 | 0.167 | 0.222 | 1.000 |
| South West | 5 | 1 | 0.250 | 0.185 | 0.200 | -0.015 | 0.400 | 0.500 | 1.000 |
| UNKNOWN | 2 | 0 | n/a | 0.151 | 0.000 | 0.151 | 0.000 | 0.000 | n/a |
| Wales | 7 | 4 | 0.500 | 0.207 | 0.571 | -0.364 | 0.429 | 0.333 | 0.500 |
| West Midlands | 11 | 1 | 0.700 | 0.141 | 0.091 | 0.050 | 0.000 | 0.000 | 1.000 |
| Yorkshire | 9 | 2 | 0.429 | 0.145 | 0.222 | -0.077 | 0.000 | 0.000 | 1.000 |

**Confidence:** SUPPRESSED — Spearman(bin, error) n/a, error top-30% n/a vs bottom-30% n/a. See reports/CONFIDENCE_VALIDATION.md.

## Known limitations

- Synthetic labels; performance does not transfer to real data without re-validation.
- Reason codes summarise the transparent logistic surrogate's positive contributions and controlled thresholds; they are explanations of evidence, not causal claims.
