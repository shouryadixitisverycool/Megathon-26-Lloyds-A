# Model card — SOLAR_FINANCE

> Synthetic demonstration model. Not for real customer decisions.

## Intended use

Estimate the probability that a customer adopts SOLAR_FINANCE within 90 days of the feature cutoff, to prioritise relevant sustainability conversations. **Not** an eligibility, credit or suitability decision.

## Inputs

22 approved Customer 360 features (point-in-time at the cutoff): `home_owner`, `has_mortgage`, `mortgage_tenure_months`, `property_is_house`, `heating_is_electric`, `has_investments`, `electricity_kwh_12m`, `electricity_trend`, `energy_months_present`, `electricity_spend_90d_avg`, `electricity_spend_12m_avg`, `electricity_spend_trend`, `home_improvement_spend_90d_avg`, `home_improvement_spend_12m_avg`, `home_improvement_txn_freq_90d`, `home_improvement_days_since_last`, `utilities_spend_90d_avg`, `utilities_spend_trend`, `sustainability_preference`, `total_spend_12m_avg`, `tenure_months`, `txn_months_observed`

Excluded by policy: exact postcode, income band, region, age band (proxy-risk policy, spec 12), the product's own holding flags, and any post-cutoff information.

## Training

Population: customers not already holding the product at the cutoff. Heuristic baseline, logistic regression and histogram gradient boosting trained on the train split; calibration (platt) and the operational threshold (max F1) fitted on validation only; deployed model chosen on validation.

## Evaluation

Selected model (by validation ROC-AUC, Brier tie-break): **LOGISTIC** `solar_finance_logreg_v1`; calibration **platt** `solar_finance_platt_v1` fitted on validation only.
Train 1791 (103 positive), validation 367 (27), held-out test 354 (24).

**Held-out test metrics** (calibrated probabilities; confusion metrics at each model's validation-chosen F1 threshold):

| model | ROC-AUC | PR-AUC | Brier | ECE | P@10% | R@10% | Lift@10% | precision | recall | F1 | threshold |
|---|---|---|---|---|---|---|---|---|---|---|---|
| HEURISTIC | 0.623 | 0.094 | 0.063 | 0.005 | 0.083 | 0.125 | 1.229 | 0.090 | 1.000 | 0.165 | 0.063 |
| LOGISTIC | 0.960 | 0.562 | 0.041 | 0.026 | 0.472 | 0.708 | 6.965 | 0.450 | 0.750 | 0.562 | 0.253 |
| GRADIENT_BOOSTING | 0.947 | 0.524 | 0.043 | 0.017 | 0.417 | 0.625 | 6.146 | 0.455 | 0.625 | 0.526 | 0.273 |

Calibration effect (selected model, test): Brier 0.043 → 0.041, ECE 0.041 → 0.026.

Baseline comparison: the selected model's ROC-AUC 0.960 is materially better than the heuristic baseline (0.623); logistic baseline 0.960.

**Generator shift** (models trained on generator A, scored on perturbed generator B):

| model | ROC-AUC A | ROC-AUC B | PR-AUC A | PR-AUC B | ΔBrier | ΔECE (calibration shift) | ΔLift@10% |
|---|---|---|---|---|---|---|---|
| HEURISTIC | 0.623 | 0.599 | 0.094 | 0.073 | -0.009 | 0.008 | -0.355 |
| LOGISTIC | 0.960 | 0.946 | 0.562 | 0.425 | 0.000 | -0.003 | -0.188 |
| GRADIENT_BOOSTING | 0.947 | 0.938 | 0.524 | 0.371 | 0.001 | 0.007 | -0.170 |

**Missing-data stress** (selected model, held-out test):

| scenario | ROC-AUC | PR-AUC | Brier | ECE | Lift@10% |
|---|---|---|---|---|---|
| mileage_missing | 0.960 | 0.562 | 0.041 | 0.026 | 6.965 |
| energy_missing | 0.962 | 0.562 | 0.039 | 0.037 | 7.785 |
| home_ownership_unknown | 0.958 | 0.556 | 0.042 | 0.034 | 6.965 |
| sustainability_preference_missing | 0.959 | 0.561 | 0.041 | 0.030 | 6.965 |
| digital_missing | 0.960 | 0.562 | 0.041 | 0.026 | 6.965 |
| random_30pct_cells | 0.942 | 0.448 | 0.046 | 0.027 | 6.146 |

**Temporal holdout:** retrained at 2026-03-31, tested at 2026-06-30 on held-out customers: ROC-AUC 0.954, Brier 0.049, ECE 0.036.

**Proxy ablation** (spec 12.2):

| variant | ROC-AUC | Brier | ECE | selection-rate range across income bands | max |calibration gap| across income bands |
|---|---|---|---|---|---|
| without proxies (default) | 0.960 | 0.041 | 0.026 | 0.310 | 0.015 |
| with income band + region | 0.955 | 0.042 | 0.029 | 0.286 | 0.039 |

Decision: default to the model **without** proxies (ΔROC-AUC with proxies = -0.005); proxies are not justified unless they add clear value without widening disparity.

**Subgroup diagnostics** (audit-only attributes, selected model):

*age_band*

| group | n | positives | roc_auc | mean_pred | observed_rate | calibration_gap | selection_rate | fpr | fnr |
|---|---|---|---|---|---|---|---|---|---|
| 18-24 | 44 | 2 | 0.881 | 0.080 | 0.045 | 0.035 | 0.136 | 0.119 | 0.500 |
| 25-34 | 62 | 6 | 0.973 | 0.082 | 0.097 | -0.015 | 0.113 | 0.036 | 0.167 |
| 35-44 | 79 | 9 | 0.967 | 0.099 | 0.114 | -0.015 | 0.139 | 0.057 | 0.222 |
| 45-54 | 88 | 3 | 0.937 | 0.050 | 0.034 | 0.016 | 0.080 | 0.071 | 0.667 |
| 55-64 | 51 | 4 | 0.963 | 0.102 | 0.078 | 0.024 | 0.157 | 0.085 | 0.000 |
| 65+ | 30 | 0 | n/a | 0.033 | 0.000 | 0.033 | 0.033 | 0.033 | n/a |

*income_band*

| group | n | positives | roc_auc | mean_pred | observed_rate | calibration_gap | selection_rate | fpr | fnr |
|---|---|---|---|---|---|---|---|---|---|
| 100k+ | 12 | 2 | 0.950 | 0.179 | 0.167 | 0.012 | 0.333 | 0.200 | 0.000 |
| 25-50k | 138 | 9 | 0.950 | 0.080 | 0.065 | 0.015 | 0.116 | 0.078 | 0.333 |
| 50-75k | 86 | 6 | 0.952 | 0.076 | 0.070 | 0.007 | 0.116 | 0.062 | 0.167 |
| 75-100k | 33 | 4 | 0.948 | 0.129 | 0.121 | 0.007 | 0.242 | 0.138 | 0.000 |
| <25k | 85 | 3 | 0.984 | 0.035 | 0.035 | -0.000 | 0.024 | 0.012 | 0.667 |

*region*

| group | n | positives | roc_auc | mean_pred | observed_rate | calibration_gap | selection_rate | fpr | fnr |
|---|---|---|---|---|---|---|---|---|---|
| East Midlands | 22 | 2 | 0.975 | 0.119 | 0.091 | 0.028 | 0.182 | 0.100 | 0.000 |
| East of England | 29 | 4 | 0.860 | 0.119 | 0.138 | -0.019 | 0.207 | 0.160 | 0.500 |
| London | 53 | 3 | 0.960 | 0.053 | 0.057 | -0.004 | 0.057 | 0.020 | 0.333 |
| North East | 15 | 1 | 1.000 | 0.040 | 0.067 | -0.027 | 0.067 | 0.000 | 0.000 |
| North West | 45 | 4 | 0.988 | 0.095 | 0.089 | 0.006 | 0.156 | 0.073 | 0.000 |
| Scotland | 31 | 2 | 0.966 | 0.111 | 0.065 | 0.046 | 0.194 | 0.138 | 0.000 |
| South East | 52 | 2 | 1.000 | 0.051 | 0.038 | 0.013 | 0.058 | 0.020 | 0.000 |
| South West | 32 | 0 | n/a | 0.013 | 0.000 | 0.013 | 0.000 | 0.000 | n/a |
| UNKNOWN | 6 | 1 | 1.000 | 0.105 | 0.167 | -0.062 | 0.167 | 0.000 | 0.000 |
| Wales | 16 | 0 | n/a | 0.092 | 0.000 | 0.092 | 0.188 | 0.188 | n/a |
| West Midlands | 24 | 1 | 0.826 | 0.111 | 0.042 | 0.069 | 0.167 | 0.174 | 1.000 |
| Yorkshire | 29 | 4 | 1.000 | 0.069 | 0.138 | -0.069 | 0.069 | 0.000 | 0.500 |

**Confidence:** SURFACED — Spearman(bin, error) -0.701, error top-30% 0.000 vs bottom-30% 0.264. See reports/CONFIDENCE_VALIDATION.md.

## Known limitations

- Synthetic labels; performance does not transfer to real data without re-validation.
- Reason codes summarise the transparent logistic surrogate's positive contributions and controlled thresholds; they are explanations of evidence, not causal claims.
