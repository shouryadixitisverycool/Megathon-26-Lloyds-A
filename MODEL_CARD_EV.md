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

Selected model (by validation ROC-AUC, Brier tie-break): **LOGISTIC** `ev_finance_logreg_v1`; calibration **platt** `ev_finance_platt_v1` fitted on validation only.
Train 1711 (104 positive), validation 358 (19), held-out test 344 (28).

**Held-out test metrics** (calibrated probabilities; confusion metrics at each model's validation-chosen F1 threshold):

| model | ROC-AUC | PR-AUC | Brier | ECE | P@10% | R@10% | Lift@10% | precision | recall | F1 | threshold |
|---|---|---|---|---|---|---|---|---|---|---|---|
| HEURISTIC | 0.701 | 0.138 | 0.074 | 0.027 | 0.143 | 0.179 | 1.755 | 0.000 | 0.000 | 0.000 | 0.067 |
| LOGISTIC | 0.755 | 0.283 | 0.073 | 0.027 | 0.229 | 0.286 | 2.808 | 0.197 | 0.536 | 0.288 | 0.071 |
| GRADIENT_BOOSTING | 0.729 | 0.188 | 0.074 | 0.028 | 0.171 | 0.214 | 2.106 | 0.211 | 0.286 | 0.242 | 0.073 |

Calibration effect (selected model, test): Brier 0.069 → 0.073, ECE 0.020 → 0.027.

Baseline comparison: the selected model's ROC-AUC 0.755 is materially better than the heuristic baseline (0.701); logistic baseline 0.755.

**Generator shift** (models trained on generator A, scored on perturbed generator B):

| model | ROC-AUC A | ROC-AUC B | PR-AUC A | PR-AUC B | ΔBrier | ΔECE (calibration shift) | ΔLift@10% |
|---|---|---|---|---|---|---|---|
| HEURISTIC | 0.701 | 0.659 | 0.138 | 0.101 | -0.016 | -0.017 | 0.467 |
| LOGISTIC | 0.755 | 0.640 | 0.283 | 0.118 | -0.015 | -0.013 | -0.658 |
| GRADIENT_BOOSTING | 0.729 | 0.635 | 0.188 | 0.114 | -0.016 | -0.016 | -0.314 |

**Missing-data stress** (selected model, held-out test):

| scenario | ROC-AUC | PR-AUC | Brier | ECE | Lift@10% |
|---|---|---|---|---|---|
| mileage_missing | 0.775 | 0.251 | 0.073 | 0.028 | 2.808 |
| energy_missing | 0.755 | 0.283 | 0.073 | 0.027 | 2.808 |
| home_ownership_unknown | 0.755 | 0.283 | 0.073 | 0.027 | 2.808 |
| sustainability_preference_missing | 0.748 | 0.249 | 0.074 | 0.033 | 3.510 |
| digital_missing | 0.754 | 0.289 | 0.072 | 0.015 | 3.159 |
| random_30pct_cells | 0.671 | 0.189 | 0.074 | 0.031 | 3.159 |

**Temporal holdout:** retrained at 2026-03-31, tested at 2026-06-30 on held-out customers: ROC-AUC 0.713, Brier 0.072, ECE 0.023.

**Proxy ablation** (spec 12.2):

| variant | ROC-AUC | Brier | ECE | selection-rate range across income bands | max |calibration gap| across income bands |
|---|---|---|---|---|---|
| without proxies (default) | 0.755 | 0.073 | 0.027 | 0.339 | 0.098 |
| with income band + region | 0.743 | 0.072 | 0.026 | 0.173 | 0.094 |

Decision: default to the model **without** proxies (ΔROC-AUC with proxies = -0.012); proxies are not justified unless they add clear value without widening disparity.

**Subgroup diagnostics** (audit-only attributes, selected model):

*age_band*

| group | n | positives | roc_auc | mean_pred | observed_rate | calibration_gap | selection_rate | fpr | fnr |
|---|---|---|---|---|---|---|---|---|---|
| 18-24 | 32 | 0 | n/a | 0.049 | 0.000 | 0.049 | 0.156 | 0.156 | n/a |
| 25-34 | 62 | 7 | 0.779 | 0.052 | 0.113 | -0.061 | 0.145 | 0.091 | 0.429 |
| 35-44 | 75 | 4 | 0.803 | 0.056 | 0.053 | 0.003 | 0.333 | 0.324 | 0.500 |
| 45-54 | 93 | 10 | 0.743 | 0.054 | 0.108 | -0.053 | 0.204 | 0.169 | 0.500 |
| 55-64 | 46 | 3 | 0.829 | 0.057 | 0.065 | -0.009 | 0.239 | 0.209 | 0.333 |
| 65+ | 36 | 4 | 0.680 | 0.056 | 0.111 | -0.055 | 0.194 | 0.156 | 0.500 |

*income_band*

| group | n | positives | roc_auc | mean_pred | observed_rate | calibration_gap | selection_rate | fpr | fnr |
|---|---|---|---|---|---|---|---|---|---|
| 100k+ | 19 | 3 | 0.688 | 0.060 | 0.158 | -0.098 | 0.316 | 0.250 | 0.333 |
| 25-50k | 133 | 8 | 0.797 | 0.054 | 0.060 | -0.006 | 0.226 | 0.200 | 0.375 |
| 50-75k | 89 | 10 | 0.754 | 0.055 | 0.112 | -0.057 | 0.213 | 0.177 | 0.500 |
| 75-100k | 32 | 3 | 0.862 | 0.063 | 0.094 | -0.030 | 0.438 | 0.379 | 0.000 |
| <25k | 71 | 4 | 0.627 | 0.048 | 0.056 | -0.008 | 0.099 | 0.104 | 1.000 |

*region*

| group | n | positives | roc_auc | mean_pred | observed_rate | calibration_gap | selection_rate | fpr | fnr |
|---|---|---|---|---|---|---|---|---|---|
| East Midlands | 22 | 2 | 0.550 | 0.051 | 0.091 | -0.040 | 0.227 | 0.250 | 1.000 |
| East of England | 33 | 3 | 0.589 | 0.055 | 0.091 | -0.036 | 0.152 | 0.133 | 0.667 |
| London | 49 | 1 | 0.938 | 0.049 | 0.020 | 0.028 | 0.163 | 0.146 | 0.000 |
| North East | 17 | 0 | n/a | 0.054 | 0.000 | 0.054 | 0.176 | 0.176 | n/a |
| North West | 41 | 4 | 0.777 | 0.055 | 0.098 | -0.042 | 0.220 | 0.189 | 0.500 |
| Scotland | 34 | 2 | 0.922 | 0.056 | 0.059 | -0.003 | 0.235 | 0.188 | 0.000 |
| South East | 47 | 4 | 0.762 | 0.049 | 0.085 | -0.037 | 0.213 | 0.186 | 0.500 |
| South West | 30 | 4 | 0.462 | 0.060 | 0.133 | -0.073 | 0.200 | 0.231 | 1.000 |
| UNKNOWN | 4 | 0 | n/a | 0.064 | 0.000 | 0.064 | 0.500 | 0.500 | n/a |
| Wales | 18 | 3 | 0.933 | 0.063 | 0.167 | -0.104 | 0.444 | 0.333 | 0.000 |
| West Midlands | 21 | 1 | 0.800 | 0.053 | 0.048 | 0.005 | 0.238 | 0.200 | 0.000 |
| Yorkshire | 28 | 4 | 0.865 | 0.060 | 0.143 | -0.083 | 0.250 | 0.167 | 0.250 |

**Confidence:** SURFACED — Spearman(bin, error) -0.818, error top-30% 0.039 vs bottom-30% 0.495. See reports/CONFIDENCE_VALIDATION.md.

## Known limitations

- Synthetic labels; performance does not transfer to real data without re-validation.
- Reason codes summarise the transparent logistic surrogate's positive contributions and controlled thresholds; they are explanations of evidence, not causal claims.
