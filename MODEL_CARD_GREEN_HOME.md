# Model card — GREEN_HOME

> Synthetic demonstration model. Not for real customer decisions.

## Intended use

Estimate the probability that a customer adopts GREEN_HOME within 90 days of the feature cutoff, to prioritise relevant sustainability conversations. **Not** an eligibility, credit or suitability decision.

## Inputs

31 approved Customer 360 features (point-in-time at the cutoff): `home_owner`, `has_mortgage`, `mortgage_tenure_months`, `property_is_house`, `heating_is_gas`, `heating_is_electric`, `has_existing_solar`, `has_investments`, `utilities_spend_90d_avg`, `utilities_spend_12m_avg`, `utilities_spend_trend`, `electricity_spend_90d_avg`, `electricity_spend_12m_avg`, `electricity_spend_trend`, `gas_spend_90d_avg`, `gas_spend_12m_avg`, `gas_spend_trend`, `home_improvement_spend_30d`, `home_improvement_spend_90d_avg`, `home_improvement_spend_12m_avg`, `home_improvement_spend_trend`, `home_improvement_txn_freq_90d`, `home_improvement_days_since_last`, `electricity_kwh_12m`, `gas_kwh_12m`, `electricity_trend`, `energy_months_present`, `sustainability_preference`, `total_spend_12m_avg`, `tenure_months`, `txn_months_observed`

Excluded by policy: exact postcode, income band, region, age band (proxy-risk policy, spec 12), the product's own holding flags, and any post-cutoff information.

## Training

Population: customers not already holding the product at the cutoff. Heuristic baseline, logistic regression and histogram gradient boosting trained on the train split; calibration (platt) and the operational threshold (max F1) fitted on validation only; deployed model chosen on validation.

## Evaluation

Selected model (by validation ROC-AUC, Brier tie-break): **LOGISTIC** `green_home_logreg_v1`; calibration **platt** `green_home_logreg_platt_v2_2148edc4018ec513` fitted on validation only.
Train 1423 (113 positive), validation 197 (17), held-out test 279 (26).

**Held-out test metrics** (calibrated probabilities; confusion metrics at each model's validation-chosen F1 threshold):

| model | ROC-AUC | PR-AUC | Brier | ECE | P@10% | R@10% | Lift@10% | precision | recall | F1 | threshold |
|---|---|---|---|---|---|---|---|---|---|---|---|
| HEURISTIC | 0.668 | 0.153 | 0.084 | 0.037 | 0.143 | 0.154 | 1.533 | 0.175 | 0.385 | 0.241 | 0.104 |
| LOGISTIC | 0.670 | 0.191 | 0.082 | 0.011 | 0.179 | 0.192 | 1.916 | 0.179 | 0.538 | 0.269 | 0.109 |
| GRADIENT_BOOSTING | 0.691 | 0.173 | 0.084 | 0.007 | 0.214 | 0.231 | 2.299 | 0.134 | 0.808 | 0.230 | 0.085 |

Calibration effect (selected model, test): Brier 0.082 → 0.082, ECE 0.019 → 0.011.

Baseline comparison: the selected model's ROC-AUC 0.670 is only marginally different from the heuristic baseline (0.668); logistic baseline 0.670.

**Generator shift** (models trained on generator A, scored on perturbed generator B):

| model | ROC-AUC A | ROC-AUC B | PR-AUC A | PR-AUC B | ΔBrier | ΔECE (calibration shift) | ΔLift@10% |
|---|---|---|---|---|---|---|---|
| HEURISTIC | 0.668 | 0.641 | 0.153 | 0.144 | -0.004 | -0.018 | 0.342 |
| LOGISTIC | 0.670 | 0.647 | 0.191 | 0.171 | -0.003 | -0.003 | 0.209 |
| GRADIENT_BOOSTING | 0.691 | 0.630 | 0.173 | 0.153 | -0.003 | -0.004 | 0.076 |

**Missing-data stress** (selected model, held-out test):

| scenario | ROC-AUC | PR-AUC | Brier | ECE | Lift@10% |
|---|---|---|---|---|---|
| mileage_missing | 0.670 | 0.191 | 0.082 | 0.011 | 1.916 |
| energy_missing | 0.667 | 0.181 | 0.085 | 0.042 | 1.916 |
| home_ownership_unknown | 0.665 | 0.189 | 0.082 | 0.013 | 1.916 |
| sustainability_preference_missing | 0.663 | 0.194 | 0.083 | 0.007 | 1.916 |
| digital_missing | 0.670 | 0.191 | 0.082 | 0.011 | 1.916 |
| random_30pct_cells | 0.635 | 0.238 | 0.082 | 0.027 | 1.533 |

**Temporal holdout:** retrained at 2026-03-31, tested at 2026-06-30 on held-out customers: ROC-AUC 0.699, Brier 0.084, ECE 0.034.

**Proxy ablation** (spec 12.2):

| variant | ROC-AUC | Brier | ECE | selection-rate range across income bands | max |calibration gap| across income bands |
|---|---|---|---|---|---|
| without proxies (default) | 0.670 | 0.082 | 0.011 | 0.233 | 0.142 |
| with income band + region | 0.689 | 0.081 | 0.024 | 0.334 | 0.135 |

Decision: default to the model **without** proxies (ΔROC-AUC with proxies = 0.018); proxies are not justified unless they add clear value without widening disparity.

**Subgroup diagnostics** (audit-only attributes, selected model):

*age_band*

| group | n | positives | roc_auc | mean_pred | observed_rate | calibration_gap | selection_rate | fpr | fnr |
|---|---|---|---|---|---|---|---|---|---|
| 18-24 | 39 | 1 | 0.842 | 0.074 | 0.026 | 0.049 | 0.179 | 0.158 | 0.000 |
| 25-34 | 50 | 7 | 0.841 | 0.077 | 0.140 | -0.063 | 0.180 | 0.116 | 0.429 |
| 35-44 | 58 | 6 | 0.519 | 0.092 | 0.103 | -0.011 | 0.328 | 0.308 | 0.500 |
| 45-54 | 59 | 2 | 0.342 | 0.083 | 0.034 | 0.050 | 0.254 | 0.263 | 1.000 |
| 55-64 | 44 | 7 | 0.676 | 0.123 | 0.159 | -0.036 | 0.409 | 0.378 | 0.429 |
| 65+ | 29 | 3 | 0.731 | 0.105 | 0.103 | 0.002 | 0.345 | 0.308 | 0.333 |

*income_band*

| group | n | positives | roc_auc | mean_pred | observed_rate | calibration_gap | selection_rate | fpr | fnr |
|---|---|---|---|---|---|---|---|---|---|
| 100k+ | 17 | 4 | 0.577 | 0.093 | 0.235 | -0.142 | 0.353 | 0.308 | 0.500 |
| 25-50k | 110 | 8 | 0.600 | 0.094 | 0.073 | 0.021 | 0.291 | 0.275 | 0.500 |
| 50-75k | 64 | 8 | 0.676 | 0.101 | 0.125 | -0.024 | 0.297 | 0.268 | 0.500 |
| 75-100k | 19 | 2 | 0.676 | 0.106 | 0.105 | 0.001 | 0.421 | 0.412 | 0.500 |
| <25k | 69 | 4 | 0.842 | 0.074 | 0.058 | 0.016 | 0.188 | 0.154 | 0.250 |

*region*

| group | n | positives | roc_auc | mean_pred | observed_rate | calibration_gap | selection_rate | fpr | fnr |
|---|---|---|---|---|---|---|---|---|---|
| East Midlands | 16 | 0 | n/a | 0.100 | 0.000 | 0.100 | 0.312 | 0.312 | n/a |
| East of England | 22 | 4 | 0.361 | 0.107 | 0.182 | -0.075 | 0.409 | 0.444 | 0.750 |
| London | 48 | 2 | 0.913 | 0.076 | 0.042 | 0.034 | 0.188 | 0.152 | 0.000 |
| North East | 13 | 1 | 0.833 | 0.075 | 0.077 | -0.002 | 0.308 | 0.250 | 0.000 |
| North West | 33 | 4 | 0.733 | 0.097 | 0.121 | -0.025 | 0.333 | 0.310 | 0.500 |
| Scotland | 28 | 3 | 0.720 | 0.075 | 0.107 | -0.032 | 0.214 | 0.160 | 0.333 |
| South East | 34 | 5 | 0.469 | 0.107 | 0.147 | -0.040 | 0.324 | 0.310 | 0.600 |
| South West | 28 | 1 | 1.000 | 0.099 | 0.036 | 0.063 | 0.214 | 0.185 | 0.000 |
| UNKNOWN | 6 | 0 | n/a | 0.089 | 0.000 | 0.089 | 0.333 | 0.333 | n/a |
| Wales | 14 | 3 | 1.000 | 0.112 | 0.214 | -0.103 | 0.429 | 0.273 | 0.000 |
| West Midlands | 16 | 0 | n/a | 0.101 | 0.000 | 0.101 | 0.375 | 0.375 | n/a |
| Yorkshire | 21 | 3 | 0.685 | 0.073 | 0.143 | -0.070 | 0.143 | 0.167 | 1.000 |

**Confidence:** SUPPRESSED — Spearman(bin, error) n/a, error top-30% n/a vs bottom-30% n/a. See reports/CONFIDENCE_VALIDATION.md.

## Known limitations

- Synthetic labels; performance does not transfer to real data without re-validation.
- Reason codes summarise the transparent logistic surrogate's positive contributions and controlled thresholds; they are explanations of evidence, not causal claims.
