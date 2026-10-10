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

Selected model (by validation ROC-AUC, Brier tie-break): **LOGISTIC** `green_home_logreg_v1`; calibration **platt** `green_home_platt_v1` fitted on validation only.
Train 1419 (113 positive), validation 291 (26), held-out test 277 (26).

**Held-out test metrics** (calibrated probabilities; confusion metrics at each model's validation-chosen F1 threshold):

| model | ROC-AUC | PR-AUC | Brier | ECE | P@10% | R@10% | Lift@10% | precision | recall | F1 | threshold |
|---|---|---|---|---|---|---|---|---|---|---|---|
| HEURISTIC | 0.669 | 0.152 | 0.085 | 0.043 | 0.143 | 0.154 | 1.522 | 0.000 | 0.000 | 0.000 | 0.137 |
| LOGISTIC | 0.675 | 0.199 | 0.082 | 0.013 | 0.214 | 0.231 | 2.283 | 0.144 | 0.615 | 0.234 | 0.087 |
| GRADIENT_BOOSTING | 0.272 | 0.071 | 0.085 | 0.005 | 0.036 | 0.038 | 0.380 | 0.038 | 0.038 | 0.038 | 0.090 |

Calibration effect (selected model, test): Brier 0.082 → 0.082, ECE 0.016 → 0.013.

Baseline comparison: the selected model's ROC-AUC 0.675 is only marginally different from the heuristic baseline (0.669); logistic baseline 0.675.

**Generator shift** (models trained on generator A, scored on perturbed generator B):

| model | ROC-AUC A | ROC-AUC B | PR-AUC A | PR-AUC B | ΔBrier | ΔECE (calibration shift) | ΔLift@10% |
|---|---|---|---|---|---|---|---|
| HEURISTIC | 0.669 | 0.643 | 0.152 | 0.142 | -0.004 | -0.018 | 0.350 |
| LOGISTIC | 0.675 | 0.656 | 0.199 | 0.184 | -0.003 | 0.000 | 0.026 |
| GRADIENT_BOOSTING | 0.272 | 0.384 | 0.071 | 0.073 | -0.004 | -0.004 | 0.368 |

**Missing-data stress** (selected model, held-out test):

| scenario | ROC-AUC | PR-AUC | Brier | ECE | Lift@10% |
|---|---|---|---|---|---|
| mileage_missing | 0.675 | 0.199 | 0.082 | 0.013 | 2.283 |
| energy_missing | 0.677 | 0.200 | 0.083 | 0.022 | 2.283 |
| home_ownership_unknown | 0.669 | 0.197 | 0.082 | 0.017 | 2.283 |
| sustainability_preference_missing | 0.665 | 0.187 | 0.082 | 0.016 | 1.902 |
| digital_missing | 0.675 | 0.199 | 0.082 | 0.013 | 2.283 |
| random_30pct_cells | 0.650 | 0.202 | 0.083 | 0.012 | 1.902 |

**Temporal holdout:** retrained at 2026-03-31, tested at 2026-06-30 on held-out customers: ROC-AUC 0.707, Brier 0.081, ECE 0.020.

**Proxy ablation** (spec 12.2):

| variant | ROC-AUC | Brier | ECE | selection-rate range across income bands | max |calibration gap| across income bands |
|---|---|---|---|---|---|
| without proxies (default) | 0.675 | 0.082 | 0.013 | 0.327 | 0.138 |
| with income band + region | 0.687 | 0.081 | 0.013 | 0.296 | 0.134 |

Decision: default to the model **without** proxies (ΔROC-AUC with proxies = 0.012); proxies are not justified unless they add clear value without widening disparity.

**Subgroup diagnostics** (audit-only attributes, selected model):

*age_band*

| group | n | positives | roc_auc | mean_pred | observed_rate | calibration_gap | selection_rate | fpr | fnr |
|---|---|---|---|---|---|---|---|---|---|
| 18-24 | 39 | 1 | 0.868 | 0.080 | 0.026 | 0.054 | 0.308 | 0.289 | 0.000 |
| 25-34 | 50 | 7 | 0.831 | 0.085 | 0.140 | -0.055 | 0.320 | 0.256 | 0.286 |
| 35-44 | 57 | 6 | 0.526 | 0.093 | 0.105 | -0.012 | 0.368 | 0.353 | 0.500 |
| 45-54 | 58 | 2 | 0.366 | 0.087 | 0.034 | 0.052 | 0.397 | 0.411 | 1.000 |
| 55-64 | 44 | 7 | 0.672 | 0.118 | 0.159 | -0.041 | 0.568 | 0.541 | 0.286 |
| 65+ | 29 | 3 | 0.744 | 0.104 | 0.103 | 0.000 | 0.483 | 0.462 | 0.333 |

*income_band*

| group | n | positives | roc_auc | mean_pred | observed_rate | calibration_gap | selection_rate | fpr | fnr |
|---|---|---|---|---|---|---|---|---|---|
| 100k+ | 17 | 4 | 0.538 | 0.098 | 0.235 | -0.138 | 0.588 | 0.615 | 0.500 |
| 25-50k | 109 | 8 | 0.619 | 0.095 | 0.073 | 0.021 | 0.394 | 0.386 | 0.500 |
| 50-75k | 63 | 8 | 0.677 | 0.100 | 0.127 | -0.027 | 0.460 | 0.436 | 0.375 |
| 75-100k | 19 | 2 | 0.676 | 0.111 | 0.105 | 0.006 | 0.579 | 0.529 | 0.000 |
| <25k | 69 | 4 | 0.850 | 0.080 | 0.058 | 0.022 | 0.261 | 0.231 | 0.250 |

*region*

| group | n | positives | roc_auc | mean_pred | observed_rate | calibration_gap | selection_rate | fpr | fnr |
|---|---|---|---|---|---|---|---|---|---|
| East Midlands | 16 | 0 | n/a | 0.099 | 0.000 | 0.099 | 0.562 | 0.562 | n/a |
| East of England | 22 | 4 | 0.333 | 0.104 | 0.182 | -0.078 | 0.455 | 0.500 | 0.750 |
| London | 48 | 2 | 0.902 | 0.081 | 0.042 | 0.040 | 0.375 | 0.348 | 0.000 |
| North East | 13 | 1 | 0.833 | 0.083 | 0.077 | 0.006 | 0.385 | 0.333 | 0.000 |
| North West | 33 | 4 | 0.707 | 0.100 | 0.121 | -0.022 | 0.485 | 0.448 | 0.250 |
| Scotland | 28 | 3 | 0.720 | 0.082 | 0.107 | -0.025 | 0.286 | 0.240 | 0.333 |
| South East | 34 | 5 | 0.476 | 0.106 | 0.147 | -0.041 | 0.441 | 0.448 | 0.600 |
| South West | 28 | 1 | 1.000 | 0.100 | 0.036 | 0.064 | 0.393 | 0.370 | 0.000 |
| UNKNOWN | 5 | 0 | n/a | 0.059 | 0.000 | 0.059 | 0.200 | 0.200 | n/a |
| Wales | 14 | 3 | 1.000 | 0.113 | 0.214 | -0.101 | 0.429 | 0.273 | 0.000 |
| West Midlands | 15 | 0 | n/a | 0.099 | 0.000 | 0.099 | 0.400 | 0.400 | n/a |
| Yorkshire | 21 | 3 | 0.667 | 0.080 | 0.143 | -0.063 | 0.286 | 0.278 | 0.667 |

**Confidence:** SURFACED — Spearman(bin, error) -0.964, error top-30% 0.060 vs bottom-30% 0.735. See reports/CONFIDENCE_VALIDATION.md.

## Known limitations

- Synthetic labels; performance does not transfer to real data without re-validation.
- Reason codes summarise the transparent logistic surrogate's positive contributions and controlled thresholds; they are explanations of evidence, not causal claims.
