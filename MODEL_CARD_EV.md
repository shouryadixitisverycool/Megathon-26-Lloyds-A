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

Selected model (by validation ROC-AUC, Brier tie-break): **GRADIENT_BOOSTING** `ev_finance_gbm_v1`; calibration **platt** `ev_finance_gbm_platt_v2_e5f58c62d216b11e` fitted on validation only.
Train 1714 (104 positive), validation 230 (16), held-out test 345 (28).

**Held-out test metrics** (calibrated probabilities; confusion metrics at each model's validation-chosen F1 threshold):

| model | ROC-AUC | PR-AUC | Brier | ECE | P@10% | R@10% | Lift@10% | precision | recall | F1 | threshold |
|---|---|---|---|---|---|---|---|---|---|---|---|
| HEURISTIC | 0.714 | 0.150 | 0.074 | 0.011 | 0.143 | 0.179 | 1.760 | 0.123 | 0.250 | 0.165 | 0.080 |
| LOGISTIC | 0.711 | 0.199 | 0.071 | 0.012 | 0.171 | 0.214 | 2.112 | 0.132 | 0.321 | 0.188 | 0.102 |
| GRADIENT_BOOSTING | 0.693 | 0.181 | 0.072 | 0.011 | 0.114 | 0.143 | 1.408 | 0.143 | 0.357 | 0.204 | 0.100 |

Calibration effect (selected model, test): Brier 0.073 → 0.072, ECE 0.034 → 0.011.

Baseline comparison: the selected model's ROC-AUC 0.693 is lower than the heuristic baseline (0.714); logistic baseline 0.711.

**Generator shift** (models trained on generator A, scored on perturbed generator B):

| model | ROC-AUC A | ROC-AUC B | PR-AUC A | PR-AUC B | ΔBrier | ΔECE (calibration shift) | ΔLift@10% |
|---|---|---|---|---|---|---|---|
| HEURISTIC | 0.714 | 0.656 | 0.150 | 0.098 | -0.015 | -0.005 | 0.106 |
| LOGISTIC | 0.711 | 0.658 | 0.199 | 0.122 | -0.014 | -0.005 | -0.102 |
| GRADIENT_BOOSTING | 0.693 | 0.645 | 0.181 | 0.119 | -0.015 | -0.007 | 0.673 |

**Missing-data stress** (selected model, held-out test):

| scenario | ROC-AUC | PR-AUC | Brier | ECE | Lift@10% |
|---|---|---|---|---|---|
| mileage_missing | 0.711 | 0.138 | 0.072 | 0.015 | 1.056 |
| energy_missing | 0.693 | 0.181 | 0.072 | 0.011 | 1.408 |
| home_ownership_unknown | 0.693 | 0.181 | 0.072 | 0.011 | 1.408 |
| sustainability_preference_missing | 0.709 | 0.163 | 0.072 | 0.008 | 1.760 |
| digital_missing | 0.719 | 0.205 | 0.071 | 0.009 | 2.816 |
| random_30pct_cells | 0.649 | 0.111 | 0.075 | 0.036 | 0.352 |

**Temporal holdout:** retrained at 2026-03-31, tested at 2026-06-30 on held-out customers: ROC-AUC 0.733, Brier 0.071, ECE 0.029.

**Proxy ablation** (spec 12.2):

| variant | ROC-AUC | Brier | ECE | selection-rate range across income bands | max |calibration gap| across income bands |
|---|---|---|---|---|---|
| without proxies (default) | 0.693 | 0.072 | 0.011 | 0.203 | 0.069 |
| with income band + region | 0.717 | 0.071 | 0.008 | 0.316 | 0.062 |

Decision: default to the model **without** proxies (ΔROC-AUC with proxies = 0.024); proxies are not justified unless they add clear value without widening disparity.

**Subgroup diagnostics** (audit-only attributes, selected model):

*age_band*

| group | n | positives | roc_auc | mean_pred | observed_rate | calibration_gap | selection_rate | fpr | fnr |
|---|---|---|---|---|---|---|---|---|---|
| 18-24 | 32 | 0 | n/a | 0.071 | 0.000 | 0.071 | 0.219 | 0.219 | n/a |
| 25-34 | 62 | 7 | 0.704 | 0.066 | 0.113 | -0.047 | 0.161 | 0.145 | 0.714 |
| 35-44 | 75 | 4 | 0.585 | 0.073 | 0.053 | 0.019 | 0.240 | 0.239 | 0.750 |
| 45-54 | 94 | 10 | 0.651 | 0.070 | 0.106 | -0.036 | 0.160 | 0.155 | 0.800 |
| 55-64 | 46 | 3 | 0.992 | 0.072 | 0.065 | 0.007 | 0.217 | 0.163 | 0.000 |
| 65+ | 36 | 4 | 0.688 | 0.073 | 0.111 | -0.038 | 0.278 | 0.250 | 0.500 |

*income_band*

| group | n | positives | roc_auc | mean_pred | observed_rate | calibration_gap | selection_rate | fpr | fnr |
|---|---|---|---|---|---|---|---|---|---|
| 100k+ | 19 | 3 | 0.833 | 0.089 | 0.158 | -0.069 | 0.316 | 0.250 | 0.333 |
| 25-50k | 134 | 8 | 0.643 | 0.067 | 0.060 | 0.007 | 0.149 | 0.143 | 0.750 |
| 50-75k | 89 | 10 | 0.691 | 0.078 | 0.112 | -0.035 | 0.258 | 0.253 | 0.700 |
| 75-100k | 32 | 3 | 0.759 | 0.083 | 0.094 | -0.010 | 0.344 | 0.310 | 0.333 |
| <25k | 71 | 4 | 0.586 | 0.057 | 0.056 | 0.001 | 0.141 | 0.134 | 0.750 |

*region*

| group | n | positives | roc_auc | mean_pred | observed_rate | calibration_gap | selection_rate | fpr | fnr |
|---|---|---|---|---|---|---|---|---|---|
| East Midlands | 23 | 2 | 0.476 | 0.075 | 0.087 | -0.012 | 0.261 | 0.286 | 1.000 |
| East of England | 33 | 3 | 0.456 | 0.063 | 0.091 | -0.028 | 0.152 | 0.167 | 1.000 |
| London | 49 | 1 | 0.875 | 0.063 | 0.020 | 0.043 | 0.184 | 0.167 | 0.000 |
| North East | 17 | 0 | n/a | 0.077 | 0.000 | 0.077 | 0.235 | 0.235 | n/a |
| North West | 41 | 4 | 0.568 | 0.073 | 0.098 | -0.025 | 0.244 | 0.243 | 0.750 |
| Scotland | 34 | 2 | 0.750 | 0.071 | 0.059 | 0.012 | 0.176 | 0.156 | 0.500 |
| South East | 47 | 4 | 0.948 | 0.064 | 0.085 | -0.021 | 0.128 | 0.070 | 0.250 |
| South West | 30 | 4 | 0.510 | 0.071 | 0.133 | -0.063 | 0.133 | 0.115 | 0.750 |
| UNKNOWN | 4 | 0 | n/a | 0.079 | 0.000 | 0.079 | 0.500 | 0.500 | n/a |
| Wales | 18 | 3 | 0.844 | 0.089 | 0.167 | -0.077 | 0.389 | 0.333 | 0.333 |
| West Midlands | 21 | 1 | 0.700 | 0.065 | 0.048 | 0.018 | 0.143 | 0.150 | 1.000 |
| Yorkshire | 28 | 4 | 0.750 | 0.083 | 0.143 | -0.060 | 0.286 | 0.292 | 0.750 |

**Confidence:** SUPPRESSED — Spearman(bin, error) n/a, error top-30% n/a vs bottom-30% n/a. See reports/CONFIDENCE_VALIDATION.md.

## Known limitations

- Synthetic labels; performance does not transfer to real data without re-validation.
- Reason codes summarise the transparent logistic surrogate's positive contributions and controlled thresholds; they are explanations of evidence, not causal claims.
