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

Selected model (by validation ROC-AUC, Brier tie-break): **LOGISTIC** `solar_finance_logreg_v1`; calibration **platt** `solar_finance_logreg_platt_v2_cebcd49fd52a6c5f` fitted on validation only.
Train 1783 (103 positive), validation 249 (17), held-out test 354 (24).

**Held-out test metrics** (calibrated probabilities; confusion metrics at each model's validation-chosen F1 threshold):

| model | ROC-AUC | PR-AUC | Brier | ECE | P@10% | R@10% | Lift@10% | precision | recall | F1 | threshold |
|---|---|---|---|---|---|---|---|---|---|---|---|
| HEURISTIC | 0.733 | 0.131 | 0.078 | 0.039 | 0.139 | 0.208 | 2.049 | 0.142 | 0.708 | 0.236 | 0.086 |
| LOGISTIC | 0.750 | 0.170 | 0.060 | 0.007 | 0.194 | 0.292 | 2.868 | 0.154 | 0.333 | 0.211 | 0.134 |
| GRADIENT_BOOSTING | 0.707 | 0.130 | 0.062 | 0.012 | 0.139 | 0.208 | 2.049 | 0.135 | 0.542 | 0.217 | 0.089 |

Calibration effect (selected model, test): Brier 0.060 → 0.060, ECE 0.016 → 0.007.

Baseline comparison: the selected model's ROC-AUC 0.750 is only marginally different from the heuristic baseline (0.733); logistic baseline 0.750.

**Generator shift** (models trained on generator A, scored on perturbed generator B):

| model | ROC-AUC A | ROC-AUC B | PR-AUC A | PR-AUC B | ΔBrier | ΔECE (calibration shift) | ΔLift@10% |
|---|---|---|---|---|---|---|---|
| HEURISTIC | 0.733 | 0.734 | 0.131 | 0.127 | -0.012 | -0.007 | 0.937 |
| LOGISTIC | 0.750 | 0.743 | 0.170 | 0.133 | -0.007 | 0.018 | -0.393 |
| GRADIENT_BOOSTING | 0.707 | 0.722 | 0.130 | 0.132 | -0.009 | 0.017 | 0.573 |

**Missing-data stress** (selected model, held-out test):

| scenario | ROC-AUC | PR-AUC | Brier | ECE | Lift@10% |
|---|---|---|---|---|---|
| mileage_missing | 0.750 | 0.170 | 0.060 | 0.007 | 2.868 |
| energy_missing | 0.753 | 0.175 | 0.060 | 0.005 | 2.868 |
| home_ownership_unknown | 0.730 | 0.162 | 0.061 | 0.012 | 2.868 |
| sustainability_preference_missing | 0.744 | 0.174 | 0.060 | 0.011 | 2.868 |
| digital_missing | 0.750 | 0.170 | 0.060 | 0.007 | 2.868 |
| random_30pct_cells | 0.714 | 0.169 | 0.061 | 0.018 | 2.049 |

**Temporal holdout:** retrained at 2026-03-31, tested at 2026-06-30 on held-out customers: ROC-AUC 0.714, Brier 0.063, ECE 0.031.

**Proxy ablation** (spec 12.2):

| variant | ROC-AUC | Brier | ECE | selection-rate range across income bands | max |calibration gap| across income bands |
|---|---|---|---|---|---|
| without proxies (default) | 0.750 | 0.060 | 0.007 | 0.340 | 0.069 |
| with income band + region | 0.761 | 0.060 | 0.012 | 0.273 | 0.044 |

Decision: default to the model **without** proxies (ΔROC-AUC with proxies = 0.010); proxies are not justified unless they add clear value without widening disparity.

**Subgroup diagnostics** (audit-only attributes, selected model):

*age_band*

| group | n | positives | roc_auc | mean_pred | observed_rate | calibration_gap | selection_rate | fpr | fnr |
|---|---|---|---|---|---|---|---|---|---|
| 18-24 | 44 | 2 | 0.548 | 0.049 | 0.045 | 0.003 | 0.068 | 0.071 | 1.000 |
| 25-34 | 62 | 6 | 0.887 | 0.062 | 0.097 | -0.035 | 0.081 | 0.071 | 0.833 |
| 35-44 | 79 | 9 | 0.798 | 0.078 | 0.114 | -0.036 | 0.177 | 0.143 | 0.556 |
| 45-54 | 88 | 3 | 0.569 | 0.078 | 0.034 | 0.044 | 0.148 | 0.153 | 1.000 |
| 55-64 | 51 | 4 | 0.777 | 0.098 | 0.078 | 0.020 | 0.255 | 0.213 | 0.250 |
| 65+ | 30 | 0 | n/a | 0.078 | 0.000 | 0.078 | 0.133 | 0.133 | n/a |

*income_band*

| group | n | positives | roc_auc | mean_pred | observed_rate | calibration_gap | selection_rate | fpr | fnr |
|---|---|---|---|---|---|---|---|---|---|
| 100k+ | 12 | 2 | 0.800 | 0.097 | 0.167 | -0.069 | 0.167 | 0.100 | 0.500 |
| 25-50k | 138 | 9 | 0.729 | 0.072 | 0.065 | 0.007 | 0.159 | 0.147 | 0.667 |
| 50-75k | 86 | 6 | 0.621 | 0.080 | 0.070 | 0.010 | 0.163 | 0.163 | 0.833 |
| 75-100k | 33 | 4 | 0.724 | 0.134 | 0.121 | 0.013 | 0.364 | 0.310 | 0.250 |
| <25k | 85 | 3 | 0.927 | 0.046 | 0.035 | 0.011 | 0.024 | 0.024 | 1.000 |

*region*

| group | n | positives | roc_auc | mean_pred | observed_rate | calibration_gap | selection_rate | fpr | fnr |
|---|---|---|---|---|---|---|---|---|---|
| East Midlands | 22 | 2 | 0.800 | 0.090 | 0.091 | -0.001 | 0.273 | 0.250 | 0.500 |
| East of England | 29 | 4 | 0.580 | 0.091 | 0.138 | -0.046 | 0.207 | 0.240 | 1.000 |
| London | 53 | 3 | 0.600 | 0.052 | 0.057 | -0.005 | 0.038 | 0.040 | 1.000 |
| North East | 15 | 1 | 0.786 | 0.048 | 0.067 | -0.019 | 0.000 | 0.000 | 1.000 |
| North West | 45 | 4 | 0.744 | 0.082 | 0.089 | -0.007 | 0.222 | 0.220 | 0.750 |
| Scotland | 31 | 2 | 0.810 | 0.083 | 0.065 | 0.018 | 0.226 | 0.207 | 0.500 |
| South East | 52 | 2 | 0.980 | 0.079 | 0.038 | 0.040 | 0.115 | 0.080 | 0.000 |
| South West | 32 | 0 | n/a | 0.063 | 0.000 | 0.063 | 0.125 | 0.125 | n/a |
| UNKNOWN | 6 | 1 | 1.000 | 0.056 | 0.167 | -0.110 | 0.167 | 0.000 | 0.000 |
| Wales | 16 | 0 | n/a | 0.084 | 0.000 | 0.084 | 0.125 | 0.125 | n/a |
| West Midlands | 24 | 1 | 0.739 | 0.081 | 0.042 | 0.040 | 0.125 | 0.130 | 1.000 |
| Yorkshire | 29 | 4 | 0.720 | 0.079 | 0.138 | -0.059 | 0.172 | 0.120 | 0.500 |

**Confidence:** SUPPRESSED — Spearman(bin, error) n/a, error top-30% n/a vs bottom-30% n/a. See reports/CONFIDENCE_VALIDATION.md.

## Known limitations

- Synthetic labels; performance does not transfer to real data without re-validation.
- Reason codes summarise the transparent logistic surrogate's positive contributions and controlled thresholds; they are explanations of evidence, not causal claims.
