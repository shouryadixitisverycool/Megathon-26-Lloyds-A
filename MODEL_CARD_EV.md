# Model card — EV_FINANCE

> Synthetic demonstration model. Not for real customer decisions.

## Intended use

Estimate the probability that a customer adopts EV_FINANCE within 90 days of the feature cutoff, to prioritise relevant sustainability conversations. **Not** an eligibility, credit or suitability decision.

## Inputs

25 approved Customer 360 features (point-in-time at the cutoff): `fuel_spend_30d`, `fuel_spend_90d_avg`, `fuel_spend_12m_avg`, `fuel_spend_trend`, `fuel_txn_freq_90d`, `fuel_spend_share_12m`, `fuel_days_since_last`, `annual_mileage_km`, `mileage_is_estimated`, `has_vehicle`, `is_ice`, `is_hybrid`, `vehicle_age_years`, `vehicle_record_age_days`, `has_vehicle_finance`, `automotive_spend_90d_avg`, `automotive_spend_12m_avg`, `automotive_spend_trend`, `public_transport_spend_90d_avg`, `app_logins_3m_avg`, `digital_txn_3m_avg`, `sustainability_preference`, `total_spend_12m_avg`, `tenure_months`, `txn_months_observed`

Excluded by policy: exact postcode, income band, region, age band (proxy-risk policy, spec 12), the product's own holding flags, and any post-cutoff information.

## Training

Population: customers not already holding the product at the cutoff. Heuristic baseline, logistic regression and histogram gradient boosting trained on the train split; calibration (platt) and the operational threshold (max F1) fitted on validation only; deployed model chosen on validation.

## Evaluation

Selected model (by validation ROC-AUC, Brier tie-break): **LOGISTIC** `ev_finance_logreg_v1`; calibration **platt** `ev_finance_logreg_platt_v2_2583bf6eda9d1b1b` fitted on validation only.
Train 1715 (104 positive), validation 230 (16), held-out test 346 (28).

**Held-out test metrics** (calibrated probabilities; confusion metrics at each model's validation-chosen F1 threshold):

| model | ROC-AUC | PR-AUC | Brier | ECE | P@10% | R@10% | Lift@10% | precision | recall | F1 | threshold |
|---|---|---|---|---|---|---|---|---|---|---|---|
| HEURISTIC | 0.704 | 0.140 | 0.073 | 0.011 | 0.143 | 0.179 | 1.765 | 0.000 | 0.000 | 0.000 | 0.086 |
| LOGISTIC | 0.767 | 0.309 | 0.070 | 0.014 | 0.229 | 0.286 | 2.824 | 0.267 | 0.286 | 0.276 | 0.118 |
| GRADIENT_BOOSTING | 0.739 | 0.233 | 0.073 | 0.012 | 0.314 | 0.393 | 3.884 | 0.310 | 0.321 | 0.316 | 0.092 |

Calibration effect (selected model, test): Brier 0.068 → 0.070, ECE 0.020 → 0.014.

Baseline comparison: the selected model's ROC-AUC 0.767 is materially better than the heuristic baseline (0.704); logistic baseline 0.767.

**Generator shift** (models trained on generator A, scored on perturbed generator B):

| model | ROC-AUC A | ROC-AUC B | PR-AUC A | PR-AUC B | ΔBrier | ΔECE (calibration shift) | ΔLift@10% |
|---|---|---|---|---|---|---|---|
| HEURISTIC | 0.704 | 0.652 | 0.140 | 0.099 | -0.015 | -0.004 | 0.389 |
| LOGISTIC | 0.767 | 0.635 | 0.309 | 0.117 | -0.012 | -0.001 | -0.670 |
| GRADIENT_BOOSTING | 0.739 | 0.630 | 0.233 | 0.096 | -0.015 | -0.005 | -2.017 |

**Missing-data stress** (selected model, held-out test):

| scenario | ROC-AUC | PR-AUC | Brier | ECE | Lift@10% |
|---|---|---|---|---|---|
| mileage_missing | 0.784 | 0.264 | 0.070 | 0.032 | 2.824 |
| energy_missing | 0.767 | 0.309 | 0.070 | 0.014 | 2.824 |
| home_ownership_unknown | 0.767 | 0.309 | 0.070 | 0.014 | 2.824 |
| sustainability_preference_missing | 0.758 | 0.261 | 0.071 | 0.023 | 3.178 |
| digital_missing | 0.766 | 0.313 | 0.070 | 0.049 | 2.824 |
| random_30pct_cells | 0.731 | 0.190 | 0.074 | 0.027 | 2.471 |

**Temporal holdout:** retrained at 2026-03-31, tested at 2026-06-30 on held-out customers: ROC-AUC 0.717, Brier 0.071, ECE 0.017.

**Proxy ablation** (spec 12.2):

| variant | ROC-AUC | Brier | ECE | selection-rate range across income bands | max |calibration gap| across income bands |
|---|---|---|---|---|---|
| without proxies (default) | 0.767 | 0.070 | 0.014 | 0.091 | 0.074 |
| with income band + region | 0.757 | 0.069 | 0.015 | 0.293 | 0.068 |

Decision: default to the model **without** proxies (ΔROC-AUC with proxies = -0.010); proxies are not justified unless they add clear value without widening disparity.

**Subgroup diagnostics** (audit-only attributes, selected model):

*age_band*

| group | n | positives | roc_auc | mean_pred | observed_rate | calibration_gap | selection_rate | fpr | fnr |
|---|---|---|---|---|---|---|---|---|---|
| 18-24 | 32 | 0 | n/a | 0.061 | 0.000 | 0.061 | 0.094 | 0.094 | n/a |
| 25-34 | 62 | 7 | 0.779 | 0.064 | 0.113 | -0.049 | 0.048 | 0.036 | 0.857 |
| 35-44 | 76 | 4 | 0.812 | 0.075 | 0.053 | 0.023 | 0.145 | 0.125 | 0.500 |
| 45-54 | 94 | 10 | 0.760 | 0.071 | 0.106 | -0.035 | 0.085 | 0.071 | 0.800 |
| 55-64 | 46 | 3 | 0.853 | 0.075 | 0.065 | 0.009 | 0.087 | 0.047 | 0.333 |
| 65+ | 36 | 4 | 0.703 | 0.073 | 0.111 | -0.039 | 0.028 | 0.000 | 0.750 |

*income_band*

| group | n | positives | roc_auc | mean_pred | observed_rate | calibration_gap | selection_rate | fpr | fnr |
|---|---|---|---|---|---|---|---|---|---|
| 100k+ | 19 | 3 | 0.708 | 0.084 | 0.158 | -0.074 | 0.158 | 0.125 | 0.667 |
| 25-50k | 134 | 8 | 0.805 | 0.068 | 0.060 | 0.008 | 0.067 | 0.056 | 0.750 |
| 50-75k | 89 | 10 | 0.778 | 0.072 | 0.112 | -0.040 | 0.101 | 0.076 | 0.700 |
| 75-100k | 33 | 3 | 0.811 | 0.089 | 0.091 | -0.001 | 0.121 | 0.067 | 0.333 |
| <25k | 71 | 4 | 0.627 | 0.060 | 0.056 | 0.003 | 0.070 | 0.075 | 1.000 |

*region*

| group | n | positives | roc_auc | mean_pred | observed_rate | calibration_gap | selection_rate | fpr | fnr |
|---|---|---|---|---|---|---|---|---|---|
| East Midlands | 23 | 2 | 0.619 | 0.066 | 0.087 | -0.021 | 0.043 | 0.048 | 1.000 |
| East of England | 33 | 3 | 0.578 | 0.073 | 0.091 | -0.018 | 0.121 | 0.100 | 0.667 |
| London | 49 | 1 | 0.979 | 0.060 | 0.020 | 0.040 | 0.082 | 0.062 | 0.000 |
| North East | 17 | 0 | n/a | 0.068 | 0.000 | 0.068 | 0.000 | 0.000 | n/a |
| North West | 41 | 4 | 0.777 | 0.072 | 0.098 | -0.026 | 0.122 | 0.108 | 0.750 |
| Scotland | 34 | 2 | 0.922 | 0.073 | 0.059 | 0.015 | 0.088 | 0.062 | 0.500 |
| South East | 47 | 4 | 0.767 | 0.060 | 0.085 | -0.025 | 0.021 | 0.023 | 1.000 |
| South West | 30 | 4 | 0.490 | 0.080 | 0.133 | -0.054 | 0.100 | 0.115 | 1.000 |
| UNKNOWN | 4 | 0 | n/a | 0.085 | 0.000 | 0.085 | 0.250 | 0.250 | n/a |
| Wales | 18 | 3 | 0.933 | 0.089 | 0.167 | -0.078 | 0.167 | 0.067 | 0.333 |
| West Midlands | 21 | 1 | 0.800 | 0.068 | 0.048 | 0.020 | 0.048 | 0.050 | 1.000 |
| Yorkshire | 29 | 4 | 0.860 | 0.078 | 0.138 | -0.059 | 0.138 | 0.080 | 0.500 |

**Confidence:** SUPPRESSED — Spearman(bin, error) n/a, error top-30% n/a vs bottom-30% n/a. See reports/CONFIDENCE_VALIDATION.md.

## Known limitations

- Synthetic labels; performance does not transfer to real data without re-validation.
- Reason codes summarise the transparent logistic surrogate's positive contributions and controlled thresholds; they are explanations of evidence, not causal claims.
