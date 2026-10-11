# Greenr — Agent A evaluation report (data, ML, reliability)

> All results are computed on synthetic data generated for this demonstration; they do not establish real-world predictive performance or eligibility.

Feature cutoff 2026-06-30; outcome = adoption within 90 days (to 2026-09-28); prediction timestamp 2026-10-10. Customer-level 70/15/15 split; one third of validation reserved for confidence release selection before tuning/calibration; demo personas excluded from training.

## Summary

| product | selected | ROC-AUC | heuristic AUC | logistic AUC | Brier | ECE | Lift@10% | ROC-AUC perturbed | confidence |
|---|---|---|---|---|---|---|---|---|---|
| EV_FINANCE | LOGISTIC | 0.767 | 0.704 | 0.767 | 0.070 | 0.014 | 2.824 | 0.635 | SUPPRESSED |
| GREEN_HOME | LOGISTIC | 0.670 | 0.668 | 0.670 | 0.082 | 0.011 | 1.916 | 0.647 | SUPPRESSED |
| SOLAR_FINANCE | LOGISTIC | 0.959 | 0.626 | 0.959 | 0.041 | 0.031 | 6.965 | 0.943 | SUPPRESSED |
| PAPERLESS_BANKING | LOGISTIC | 0.612 | 0.534 | 0.612 | 0.150 | 0.053 | 0.955 | 0.692 | SUPPRESSED |

## Transaction categorisation

Hybrid categoriser (deterministic merchant rules, then TF-IDF + logistic regression). Merchant-group split: test merchants never seen in training. Full details: reports/TRANSACTION_CATEGORISATION.md.

- unseen merchants: macro F1 0.529, weighted F1 0.511, rule coverage 0.153
- known merchants: macro F1 0.992, weighted F1 0.995, rule coverage 0.969
- perturbed-generator transactions (frozen categoriser): accuracy 0.820

## Trust diagnostics (held-out test)

Trust measures evidence adequacy and is separate from confidence. Model quality by Trust status:

*EV_FINANCE* — mean score 0.739, critical-field missing 0.373, high-severity conflict 0.003, OOD flag 0.000

| status | n | share | roc_auc | brier | calibration_gap |
|---|---|---|---|---|---|
| ADEQUATE | 9 | 0.026 | n/a | 0.003 | 0.041 |
| HIGH | 203 | 0.587 | 0.636 | 0.098 | -0.021 |
| INSUFFICIENT | 129 | 0.373 | 0.843 | 0.015 | 0.020 |
| LOW | 5 | 0.014 | 0.500 | 0.457 | -0.471 |

*GREEN_HOME* — mean score 0.799, critical-field missing 0.305, high-severity conflict 0.007, OOD flag 0.011

| status | n | share | roc_auc | brier | calibration_gap |
|---|---|---|---|---|---|
| ADEQUATE | 1 | 0.004 | n/a | 0.072 | 0.269 |
| HIGH | 190 | 0.681 | 0.671 | 0.071 | 0.006 |
| INSUFFICIENT | 85 | 0.305 | 0.631 | 0.102 | -0.015 |
| LOW | 3 | 0.011 | 1.000 | 0.214 | -0.177 |

*SOLAR_FINANCE* — mean score 0.762, critical-field missing 0.345, high-severity conflict 0.008, OOD flag 0.006

| status | n | share | roc_auc | brier | calibration_gap |
|---|---|---|---|---|---|
| ADEQUATE | 6 | 0.017 | n/a | 0.000 | 0.008 |
| HIGH | 222 | 0.627 | n/a | 0.000 | 0.007 |
| INSUFFICIENT | 122 | 0.345 | 0.862 | 0.118 | 0.007 |
| LOW | 4 | 0.011 | n/a | 0.000 | 0.011 |

*PAPERLESS_BANKING* — mean score 0.937, critical-field missing 0.057, high-severity conflict 0.000, OOD flag 0.010

| status | n | share | roc_auc | brier | calibration_gap |
|---|---|---|---|---|---|
| ADEQUATE | 3 | 0.029 | 1.000 | 0.316 | -0.412 |
| HIGH | 96 | 0.914 | 0.517 | 0.147 | -0.015 |
| INSUFFICIENT | 6 | 0.057 | 1.000 | 0.110 | -0.060 |

## Per-product detail

### EV_FINANCE

Selected model (by validation ROC-AUC, Brier tie-break): **LOGISTIC** `ev_finance_logreg_v1`; calibration **platt** `ev_finance_logreg_platt_v2_52becc99c8f964f6` fitted on validation only.
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

### GREEN_HOME

Selected model (by validation ROC-AUC, Brier tie-break): **LOGISTIC** `green_home_logreg_v1`; calibration **platt** `green_home_logreg_platt_v2_8338481d1c7441e0` fitted on validation only.
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

### SOLAR_FINANCE

Selected model (by validation ROC-AUC, Brier tie-break): **LOGISTIC** `solar_finance_logreg_v1`; calibration **platt** `solar_finance_logreg_platt_v2_bbb04b654d277d42` fitted on validation only.
Train 1793 (103 positive), validation 252 (17), held-out test 354 (24).

**Held-out test metrics** (calibrated probabilities; confusion metrics at each model's validation-chosen F1 threshold):

| model | ROC-AUC | PR-AUC | Brier | ECE | P@10% | R@10% | Lift@10% | precision | recall | F1 | threshold |
|---|---|---|---|---|---|---|---|---|---|---|---|
| HEURISTIC | 0.626 | 0.095 | 0.063 | 0.001 | 0.083 | 0.125 | 1.229 | 0.081 | 0.667 | 0.144 | 0.062 |
| LOGISTIC | 0.959 | 0.560 | 0.041 | 0.031 | 0.472 | 0.708 | 6.965 | 0.475 | 0.792 | 0.594 | 0.234 |
| GRADIENT_BOOSTING | 0.936 | 0.480 | 0.045 | 0.027 | 0.444 | 0.667 | 6.556 | 0.365 | 0.792 | 0.500 | 0.136 |

Calibration effect (selected model, test): Brier 0.044 → 0.041, ECE 0.042 → 0.031.

Baseline comparison: the selected model's ROC-AUC 0.959 is materially better than the heuristic baseline (0.626); logistic baseline 0.959.

**Generator shift** (models trained on generator A, scored on perturbed generator B):

| model | ROC-AUC A | ROC-AUC B | PR-AUC A | PR-AUC B | ΔBrier | ΔECE (calibration shift) | ΔLift@10% |
|---|---|---|---|---|---|---|---|
| HEURISTIC | 0.626 | 0.603 | 0.095 | 0.073 | -0.009 | 0.007 | -0.281 |
| LOGISTIC | 0.959 | 0.943 | 0.560 | 0.408 | 0.001 | -0.007 | -0.256 |
| GRADIENT_BOOSTING | 0.936 | 0.935 | 0.480 | 0.368 | -0.000 | 0.004 | -0.721 |

**Missing-data stress** (selected model, held-out test):

| scenario | ROC-AUC | PR-AUC | Brier | ECE | Lift@10% |
|---|---|---|---|---|---|
| mileage_missing | 0.959 | 0.560 | 0.041 | 0.031 | 6.965 |
| energy_missing | 0.962 | 0.579 | 0.040 | 0.034 | 7.785 |
| home_ownership_unknown | 0.957 | 0.555 | 0.042 | 0.043 | 6.965 |
| sustainability_preference_missing | 0.959 | 0.559 | 0.041 | 0.038 | 6.965 |
| digital_missing | 0.959 | 0.560 | 0.041 | 0.031 | 6.965 |
| random_30pct_cells | 0.939 | 0.485 | 0.046 | 0.030 | 6.146 |

**Temporal holdout:** retrained at 2026-03-31, tested at 2026-06-30 on held-out customers: ROC-AUC 0.955, Brier 0.051, ECE 0.040.

**Proxy ablation** (spec 12.2):

| variant | ROC-AUC | Brier | ECE | selection-rate range across income bands | max |calibration gap| across income bands |
|---|---|---|---|---|---|
| without proxies (default) | 0.959 | 0.041 | 0.031 | 0.310 | 0.014 |
| with income band + region | 0.954 | 0.041 | 0.033 | 0.286 | 0.028 |

Decision: default to the model **without** proxies (ΔROC-AUC with proxies = -0.005); proxies are not justified unless they add clear value without widening disparity.

**Subgroup diagnostics** (audit-only attributes, selected model):

*age_band*

| group | n | positives | roc_auc | mean_pred | observed_rate | calibration_gap | selection_rate | fpr | fnr |
|---|---|---|---|---|---|---|---|---|---|
| 18-24 | 44 | 2 | 0.869 | 0.087 | 0.045 | 0.041 | 0.136 | 0.119 | 0.500 |
| 25-34 | 62 | 6 | 0.973 | 0.078 | 0.097 | -0.019 | 0.113 | 0.036 | 0.167 |
| 35-44 | 79 | 9 | 0.967 | 0.095 | 0.114 | -0.019 | 0.152 | 0.057 | 0.111 |
| 45-54 | 88 | 3 | 0.937 | 0.050 | 0.034 | 0.016 | 0.068 | 0.059 | 0.667 |
| 55-64 | 51 | 4 | 0.957 | 0.097 | 0.078 | 0.019 | 0.157 | 0.085 | 0.000 |
| 65+ | 30 | 0 | n/a | 0.034 | 0.000 | 0.034 | 0.033 | 0.033 | n/a |

*income_band*

| group | n | positives | roc_auc | mean_pred | observed_rate | calibration_gap | selection_rate | fpr | fnr |
|---|---|---|---|---|---|---|---|---|---|
| 100k+ | 12 | 2 | 0.900 | 0.169 | 0.167 | 0.002 | 0.333 | 0.200 | 0.000 |
| 25-50k | 138 | 9 | 0.947 | 0.079 | 0.065 | 0.014 | 0.123 | 0.078 | 0.222 |
| 50-75k | 86 | 6 | 0.958 | 0.074 | 0.070 | 0.004 | 0.105 | 0.050 | 0.167 |
| 75-100k | 33 | 4 | 0.957 | 0.121 | 0.121 | -0.000 | 0.242 | 0.138 | 0.000 |
| <25k | 85 | 3 | 0.976 | 0.038 | 0.035 | 0.003 | 0.024 | 0.012 | 0.667 |

*region*

| group | n | positives | roc_auc | mean_pred | observed_rate | calibration_gap | selection_rate | fpr | fnr |
|---|---|---|---|---|---|---|---|---|---|
| East Midlands | 22 | 2 | 0.975 | 0.117 | 0.091 | 0.027 | 0.136 | 0.050 | 0.000 |
| East of England | 29 | 4 | 0.860 | 0.111 | 0.138 | -0.027 | 0.241 | 0.160 | 0.250 |
| London | 53 | 3 | 0.960 | 0.056 | 0.057 | -0.001 | 0.057 | 0.020 | 0.333 |
| North East | 15 | 1 | 1.000 | 0.042 | 0.067 | -0.025 | 0.067 | 0.000 | 0.000 |
| North West | 45 | 4 | 0.988 | 0.092 | 0.089 | 0.004 | 0.156 | 0.073 | 0.000 |
| Scotland | 31 | 2 | 0.966 | 0.103 | 0.065 | 0.039 | 0.194 | 0.138 | 0.000 |
| South East | 52 | 2 | 1.000 | 0.053 | 0.038 | 0.015 | 0.058 | 0.020 | 0.000 |
| South West | 32 | 0 | n/a | 0.016 | 0.000 | 0.016 | 0.000 | 0.000 | n/a |
| UNKNOWN | 6 | 1 | 1.000 | 0.096 | 0.167 | -0.071 | 0.167 | 0.000 | 0.000 |
| Wales | 16 | 0 | n/a | 0.089 | 0.000 | 0.089 | 0.188 | 0.188 | n/a |
| West Midlands | 24 | 1 | 0.826 | 0.105 | 0.042 | 0.064 | 0.167 | 0.174 | 1.000 |
| Yorkshire | 29 | 4 | 1.000 | 0.068 | 0.138 | -0.070 | 0.069 | 0.000 | 0.500 |

**Confidence:** SUPPRESSED — Spearman(bin, error) n/a, error top-30% n/a vs bottom-30% n/a. See reports/CONFIDENCE_VALIDATION.md.

### PAPERLESS_BANKING

Selected model (by validation ROC-AUC, Brier tie-break): **LOGISTIC** `paperless_banking_logreg_v1`; calibration **platt** `paperless_banking_logreg_platt_v2_2e978e136a858e89` fitted on validation only.
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

## Feature and missingness drift

Descriptive synthetic distribution changes. KS statistics are not causal effects, real-world drift alerts or eligibility checks.

Reference uses held-out base customers; comparison uses independent perturbed-generator customers. Complete per-feature diagnostics are in reports/feature_drift.json.

| feature | ks_statistic | reference_median | comparison_median | reference_missing_rate | comparison_missing_rate | missingness_delta |
|---|---|---|---|---|---|---|
| electricity_spend_12m_avg | 0.255 | 40.500 | 0.000 | 0.000 | 0.000 | 0.000 |
| electricity_spend_share_12m | 0.254 | 0.117 | 0.000 | 0.000 | 0.000 | 0.000 |
| electricity_spend_90d_avg | 0.254 | 42.500 | 0.000 | 0.000 | 0.000 | 0.000 |
| electricity_txn_freq_90d | 0.254 | 3.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| electricity_spend_30d | 0.244 | 38.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| utilities_txn_freq_90d | 0.232 | 3.000 | 4.000 | 0.000 | 0.000 | 0.000 |
| utilities_spend_share_12m | 0.230 | 0.136 | 0.276 | 0.000 | 0.000 | 0.000 |
| utilities_spend_90d_avg | 0.229 | 43.500 | 89.000 | 0.000 | 0.000 | 0.000 |
| utilities_spend_12m_avg | 0.226 | 43.847 | 85.495 | 0.000 | 0.000 | 0.000 |
| utilities_spend_30d | 0.218 | 43.000 | 85.000 | 0.000 | 0.000 | 0.000 |
| home_improvement_spend_share_12m | 0.201 | 0.023 | 0.039 | 0.000 | 0.000 | 0.000 |
| home_improvement_spend_90d_avg | 0.194 | 2.195 | 8.460 | 0.000 | 0.000 | 0.000 |

## Limitations

- Labels are simulated from latent stochastic drivers; relationships are not causal and the generator's structure bounds what any model can learn.
- Generator-shift and temporal results quantify robustness to *simulated* change only.
- Subgroup diagnostics use synthetic audit attributes; disparities are reported, not hidden or 'fixed'.
- Propensity is interest, not eligibility; confidence is reliability of the propensity decision; Trust is evidence adequacy. None of these determine financial eligibility.
