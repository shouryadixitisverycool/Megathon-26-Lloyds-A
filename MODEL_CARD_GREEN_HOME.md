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

Selected model (by validation ROC-AUC, Brier tie-break): **LOGISTIC** `green_home_logreg_v1`; calibration **platt** `green_home_logreg_platt_v2_bd70c12346380a73` fitted on validation only.
Train 1422 (113 positive), validation 198 (17), held-out test 277 (26).

**Held-out test metrics** (calibrated probabilities; confusion metrics at each model's validation-chosen F1 threshold):

| model | ROC-AUC | PR-AUC | Brier | ECE | P@10% | R@10% | Lift@10% | precision | recall | F1 | threshold |
|---|---|---|---|---|---|---|---|---|---|---|---|
| HEURISTIC | 0.689 | 0.164 | 0.089 | 0.021 | 0.250 | 0.269 | 2.663 | 0.154 | 0.462 | 0.231 | 0.120 |
| LOGISTIC | 0.675 | 0.163 | 0.084 | 0.019 | 0.179 | 0.192 | 1.902 | 0.157 | 0.308 | 0.208 | 0.122 |
| GRADIENT_BOOSTING | 0.658 | 0.188 | 0.083 | 0.010 | 0.179 | 0.192 | 1.902 | 0.177 | 0.423 | 0.250 | 0.109 |

Calibration effect (selected model, test): Brier 0.087 → 0.084, ECE 0.029 → 0.019.

Baseline comparison: the selected model's ROC-AUC 0.675 is only marginally different from the heuristic baseline (0.689); logistic baseline 0.675.

**Generator shift** (models trained on generator A, scored on perturbed generator B):

| model | ROC-AUC A | ROC-AUC B | PR-AUC A | PR-AUC B | ΔBrier | ΔECE (calibration shift) | ΔLift@10% |
|---|---|---|---|---|---|---|---|
| HEURISTIC | 0.689 | 0.646 | 0.164 | 0.146 | -0.004 | -0.006 | -0.671 |
| LOGISTIC | 0.675 | 0.651 | 0.163 | 0.146 | -0.004 | -0.008 | -0.159 |
| GRADIENT_BOOSTING | 0.658 | 0.631 | 0.188 | 0.159 | -0.003 | 0.009 | 0.339 |

**Missing-data stress** (selected model, held-out test):

| scenario | ROC-AUC | PR-AUC | Brier | ECE | Lift@10% |
|---|---|---|---|---|---|
| mileage_missing | 0.675 | 0.163 | 0.084 | 0.019 | 1.902 |
| energy_missing | 0.696 | 0.181 | 0.094 | 0.091 | 2.283 |
| home_ownership_unknown | 0.671 | 0.160 | 0.085 | 0.015 | 1.522 |
| sustainability_preference_missing | 0.679 | 0.160 | 0.085 | 0.011 | 1.522 |
| digital_missing | 0.675 | 0.163 | 0.084 | 0.019 | 1.902 |
| random_30pct_cells | 0.559 | 0.148 | 0.102 | 0.092 | 1.902 |

**Temporal holdout:** retrained at 2026-03-31, tested at 2026-06-30 on held-out customers: ROC-AUC 0.714, Brier 0.082, ECE 0.016.

**Proxy ablation** (spec 12.2):

| variant | ROC-AUC | Brier | ECE | selection-rate range across income bands | max |calibration gap| across income bands |
|---|---|---|---|---|---|
| without proxies (default) | 0.675 | 0.084 | 0.019 | 0.296 | 0.142 |
| with income band + region | 0.671 | 0.083 | 0.017 | 0.301 | 0.137 |

Decision: default to the model **without** proxies (ΔROC-AUC with proxies = -0.003); proxies are not justified unless they add clear value without widening disparity.

**Subgroup diagnostics** (audit-only attributes, selected model):

*age_band*

| group | n | positives | roc_auc | mean_pred | observed_rate | calibration_gap | selection_rate | fpr | fnr |
|---|---|---|---|---|---|---|---|---|---|
| 18-24 | 39 | 1 | 0.868 | 0.067 | 0.026 | 0.042 | 0.077 | 0.079 | 1.000 |
| 25-34 | 50 | 7 | 0.767 | 0.081 | 0.140 | -0.059 | 0.180 | 0.140 | 0.571 |
| 35-44 | 57 | 6 | 0.569 | 0.083 | 0.105 | -0.022 | 0.175 | 0.176 | 0.833 |
| 45-54 | 58 | 2 | 0.420 | 0.079 | 0.034 | 0.045 | 0.172 | 0.179 | 1.000 |
| 55-64 | 44 | 7 | 0.660 | 0.109 | 0.159 | -0.050 | 0.227 | 0.216 | 0.714 |
| 65+ | 29 | 3 | 0.718 | 0.090 | 0.103 | -0.014 | 0.310 | 0.269 | 0.333 |

*income_band*

| group | n | positives | roc_auc | mean_pred | observed_rate | calibration_gap | selection_rate | fpr | fnr |
|---|---|---|---|---|---|---|---|---|---|
| 100k+ | 17 | 4 | 0.442 | 0.094 | 0.235 | -0.142 | 0.294 | 0.308 | 0.750 |
| 25-50k | 109 | 8 | 0.652 | 0.084 | 0.073 | 0.011 | 0.202 | 0.198 | 0.750 |
| 50-75k | 63 | 8 | 0.702 | 0.091 | 0.127 | -0.036 | 0.190 | 0.164 | 0.625 |
| 75-100k | 19 | 2 | 0.706 | 0.111 | 0.105 | 0.006 | 0.368 | 0.353 | 0.500 |
| <25k | 69 | 4 | 0.692 | 0.069 | 0.058 | 0.011 | 0.072 | 0.062 | 0.750 |

*region*

| group | n | positives | roc_auc | mean_pred | observed_rate | calibration_gap | selection_rate | fpr | fnr |
|---|---|---|---|---|---|---|---|---|---|
| East Midlands | 16 | 0 | n/a | 0.069 | 0.000 | 0.069 | 0.125 | 0.125 | n/a |
| East of England | 22 | 4 | 0.403 | 0.120 | 0.182 | -0.062 | 0.273 | 0.333 | 1.000 |
| London | 48 | 2 | 0.728 | 0.066 | 0.042 | 0.025 | 0.104 | 0.109 | 1.000 |
| North East | 13 | 1 | 0.333 | 0.092 | 0.077 | 0.015 | 0.231 | 0.250 | 1.000 |
| North West | 33 | 4 | 0.819 | 0.087 | 0.121 | -0.034 | 0.273 | 0.207 | 0.250 |
| Scotland | 28 | 3 | 0.813 | 0.080 | 0.107 | -0.027 | 0.179 | 0.120 | 0.333 |
| South East | 34 | 5 | 0.317 | 0.098 | 0.147 | -0.049 | 0.206 | 0.241 | 1.000 |
| South West | 28 | 1 | 0.963 | 0.083 | 0.036 | 0.047 | 0.214 | 0.185 | 0.000 |
| UNKNOWN | 5 | 0 | n/a | 0.055 | 0.000 | 0.055 | 0.200 | 0.200 | n/a |
| Wales | 14 | 3 | 0.909 | 0.085 | 0.214 | -0.130 | 0.071 | 0.000 | 0.667 |
| West Midlands | 15 | 0 | n/a | 0.092 | 0.000 | 0.092 | 0.133 | 0.133 | n/a |
| Yorkshire | 21 | 3 | 0.741 | 0.080 | 0.143 | -0.063 | 0.190 | 0.167 | 0.667 |

**Confidence:** SUPPRESSED — Spearman(bin, error) n/a, error top-30% n/a vs bottom-30% n/a. See reports/CONFIDENCE_VALIDATION.md.

## Known limitations

- Synthetic labels; performance does not transfer to real data without re-validation.
- Reason codes summarise the transparent logistic surrogate's positive contributions and controlled thresholds; they are explanations of evidence, not causal claims.
