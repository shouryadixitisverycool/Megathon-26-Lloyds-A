# GreenPath — Agent A evaluation report (data, ML, reliability)

> All results are computed on synthetic data generated for this demonstration; they do not establish real-world predictive performance or eligibility.

Feature cutoff 2026-06-30; outcome = adoption within 90 days (to 2026-09-28); prediction timestamp 2026-10-10. Customer-level 70/15/15 split; demo personas excluded from training.

## Summary

| product | selected | ROC-AUC | heuristic AUC | logistic AUC | Brier | ECE | Lift@10% | ROC-AUC perturbed | confidence |
|---|---|---|---|---|---|---|---|---|---|
| EV_FINANCE | LOGISTIC | 0.755 | 0.701 | 0.755 | 0.073 | 0.027 | 2.808 | 0.640 | SURFACED |
| GREEN_HOME | LOGISTIC | 0.675 | 0.669 | 0.675 | 0.082 | 0.013 | 2.283 | 0.656 | SURFACED |
| SOLAR_FINANCE | LOGISTIC | 0.960 | 0.623 | 0.960 | 0.041 | 0.026 | 6.965 | 0.946 | SURFACED |
| PAPERLESS_BANKING | LOGISTIC | 0.640 | 0.642 | 0.640 | 0.152 | 0.084 | 1.485 | 0.716 | SUPPRESSED |

## Transaction categorisation

Hybrid categoriser (deterministic merchant rules, then TF-IDF + logistic regression). Merchant-group split: test merchants never seen in training. Full details: reports/TRANSACTION_CATEGORISATION.md.

- unseen merchants: macro F1 0.529, weighted F1 0.511, rule coverage 0.153
- known merchants: macro F1 0.992, weighted F1 0.995, rule coverage 0.969
- perturbed-generator transactions (frozen categoriser): accuracy 0.825

## Trust diagnostics (held-out test)

Trust measures evidence adequacy and is separate from confidence. Model quality by Trust status:

*EV_FINANCE* — mean score 0.734, critical-field missing 0.375, high-severity conflict 0.003, OOD flag 0.003

| status | n | share | roc_auc | brier | calibration_gap |
|---|---|---|---|---|---|
| ADEQUATE | 2 | 0.006 | n/a | 0.001 | 0.033 |
| HIGH | 207 | 0.602 | 0.613 | 0.099 | -0.045 |
| INSUFFICIENT | 129 | 0.375 | 0.823 | 0.015 | 0.019 |
| LOW | 6 | 0.017 | 0.556 | 0.419 | -0.427 |

*GREEN_HOME* — mean score 0.805, critical-field missing 0.292, high-severity conflict 0.007, OOD flag 0.011

| status | n | share | roc_auc | brier | calibration_gap |
|---|---|---|---|---|---|
| HIGH | 190 | 0.686 | 0.673 | 0.071 | 0.011 |
| INSUFFICIENT | 81 | 0.292 | 0.646 | 0.105 | -0.024 |
| LOW | 6 | 0.022 | 1.000 | 0.116 | -0.032 |

*SOLAR_FINANCE* — mean score 0.776, critical-field missing 0.339, high-severity conflict 0.008, OOD flag 0.014

| status | n | share | roc_auc | brier | calibration_gap |
|---|---|---|---|---|---|
| ADEQUATE | 3 | 0.008 | n/a | 0.000 | 0.008 |
| HIGH | 227 | 0.641 | n/a | 0.000 | 0.004 |
| INSUFFICIENT | 120 | 0.339 | 0.862 | 0.120 | 0.017 |
| LOW | 4 | 0.011 | n/a | 0.000 | 0.006 |

*PAPERLESS_BANKING* — mean score 0.945, critical-field missing 0.051, high-severity conflict 0.000, OOD flag 0.030

| status | n | share | roc_auc | brier | calibration_gap |
|---|---|---|---|---|---|
| ADEQUATE | 1 | 0.010 | n/a | 0.175 | -0.418 |
| HIGH | 90 | 0.909 | 0.571 | 0.160 | -0.054 |
| INSUFFICIENT | 5 | 0.051 | n/a | 0.002 | 0.047 |
| LOW | 3 | 0.030 | 1.000 | 0.148 | -0.124 |

## Per-product detail

### EV_FINANCE

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

### GREEN_HOME

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

### SOLAR_FINANCE

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

### PAPERLESS_BANKING

Selected model (by validation ROC-AUC, Brier tie-break): **LOGISTIC** `paperless_banking_logreg_v1`; calibration **platt** `paperless_banking_platt_v1` fitted on validation only.
Train 497 (67 positive), validation 93 (14), held-out test 99 (20).

**Held-out test metrics** (calibrated probabilities; confusion metrics at each model's validation-chosen F1 threshold):

| model | ROC-AUC | PR-AUC | Brier | ECE | P@10% | R@10% | Lift@10% | precision | recall | F1 | threshold |
|---|---|---|---|---|---|---|---|---|---|---|---|
| HEURISTIC | 0.642 | 0.316 | 0.160 | 0.052 | 0.500 | 0.250 | 2.475 | 0.271 | 0.650 | 0.382 | 0.161 |
| LOGISTIC | 0.640 | 0.385 | 0.152 | 0.084 | 0.300 | 0.150 | 1.485 | 0.243 | 0.850 | 0.378 | 0.116 |
| GRADIENT_BOOSTING | 0.658 | 0.383 | 0.162 | 0.054 | 0.300 | 0.150 | 1.485 | 0.283 | 0.750 | 0.411 | 0.146 |

Calibration effect (selected model, test): Brier 0.157 → 0.152, ECE 0.101 → 0.084.

Baseline comparison: the selected model's ROC-AUC 0.640 is only marginally different from the heuristic baseline (0.642); logistic baseline 0.640.

**Generator shift** (models trained on generator A, scored on perturbed generator B):

| model | ROC-AUC A | ROC-AUC B | PR-AUC A | PR-AUC B | ΔBrier | ΔECE (calibration shift) | ΔLift@10% |
|---|---|---|---|---|---|---|---|
| HEURISTIC | 0.642 | 0.735 | 0.316 | 0.267 | -0.054 | -0.026 | 0.474 |
| LOGISTIC | 0.640 | 0.716 | 0.385 | 0.258 | -0.046 | -0.058 | 1.095 |
| GRADIENT_BOOSTING | 0.658 | 0.647 | 0.383 | 0.239 | -0.050 | -0.033 | 0.604 |

**Missing-data stress** (selected model, held-out test):

| scenario | ROC-AUC | PR-AUC | Brier | ECE | Lift@10% |
|---|---|---|---|---|---|
| mileage_missing | 0.640 | 0.385 | 0.152 | 0.084 | 1.485 |
| energy_missing | 0.640 | 0.385 | 0.152 | 0.084 | 1.485 |
| home_ownership_unknown | 0.640 | 0.385 | 0.152 | 0.084 | 1.485 |
| sustainability_preference_missing | 0.629 | 0.380 | 0.152 | 0.062 | 1.485 |
| digital_missing | 0.615 | 0.372 | 0.176 | 0.140 | 1.485 |
| random_30pct_cells | 0.596 | 0.345 | 0.163 | 0.085 | 1.485 |

**Temporal holdout:** retrained at 2026-03-31, tested at 2026-06-30 on held-out customers: ROC-AUC 0.633, Brier 0.152, ECE 0.030.

**Proxy ablation** (spec 12.2):

| variant | ROC-AUC | Brier | ECE | selection-rate range across income bands | max |calibration gap| across income bands |
|---|---|---|---|---|---|
| without proxies (default) | 0.640 | 0.152 | 0.084 | 0.247 | 0.293 |
| with income band + region | 0.639 | 0.159 | 0.064 | 0.519 | 0.237 |

Decision: default to the model **without** proxies (ΔROC-AUC with proxies = -0.001); proxies are not justified unless they add clear value without widening disparity.

**Subgroup diagnostics** (audit-only attributes, selected model):

*age_band*

| group | n | positives | roc_auc | mean_pred | observed_rate | calibration_gap | selection_rate | fpr | fnr |
|---|---|---|---|---|---|---|---|---|---|
| 18-24 | 3 | 0 | n/a | 0.185 | 0.000 | 0.185 | 1.000 | 1.000 | n/a |
| 25-34 | 6 | 1 | 1.000 | 0.208 | 0.167 | 0.042 | 0.833 | 0.800 | 0.000 |
| 35-44 | 21 | 4 | 0.588 | 0.140 | 0.190 | -0.051 | 0.810 | 0.765 | 0.000 |
| 45-54 | 27 | 6 | 0.921 | 0.140 | 0.222 | -0.082 | 0.741 | 0.667 | 0.000 |
| 55-64 | 23 | 7 | 0.679 | 0.143 | 0.304 | -0.162 | 0.565 | 0.500 | 0.286 |
| 65+ | 19 | 2 | 0.382 | 0.146 | 0.105 | 0.041 | 0.632 | 0.647 | 0.500 |

*income_band*

| group | n | positives | roc_auc | mean_pred | observed_rate | calibration_gap | selection_rate | fpr | fnr |
|---|---|---|---|---|---|---|---|---|---|
| 100k+ | 7 | 3 | 0.333 | 0.135 | 0.429 | -0.293 | 0.571 | 0.750 | 0.667 |
| 25-50k | 33 | 5 | 0.557 | 0.143 | 0.152 | -0.008 | 0.818 | 0.786 | 0.000 |
| 50-75k | 31 | 7 | 0.738 | 0.168 | 0.226 | -0.058 | 0.645 | 0.583 | 0.143 |
| 75-100k | 9 | 2 | 0.714 | 0.128 | 0.222 | -0.094 | 0.667 | 0.571 | 0.000 |
| <25k | 19 | 3 | 0.667 | 0.133 | 0.158 | -0.025 | 0.684 | 0.625 | 0.000 |

*region*

| group | n | positives | roc_auc | mean_pred | observed_rate | calibration_gap | selection_rate | fpr | fnr |
|---|---|---|---|---|---|---|---|---|---|
| East Midlands | 10 | 2 | 0.812 | 0.118 | 0.200 | -0.082 | 0.600 | 0.500 | 0.000 |
| East of England | 11 | 2 | 0.833 | 0.145 | 0.182 | -0.037 | 0.818 | 0.778 | 0.000 |
| London | 12 | 1 | 1.000 | 0.163 | 0.083 | 0.079 | 0.750 | 0.727 | 0.000 |
| North East | 5 | 0 | n/a | 0.156 | 0.000 | 0.156 | 0.800 | 0.800 | n/a |
| North West | 10 | 3 | 0.238 | 0.144 | 0.300 | -0.156 | 1.000 | 1.000 | 0.000 |
| Scotland | 8 | 1 | 0.000 | 0.135 | 0.125 | 0.010 | 0.500 | 0.571 | 1.000 |
| South East | 12 | 3 | 0.556 | 0.148 | 0.250 | -0.102 | 0.583 | 0.556 | 0.333 |
| South West | 4 | 1 | 0.667 | 0.167 | 0.250 | -0.083 | 0.750 | 0.667 | 0.000 |
| UNKNOWN | 2 | 0 | n/a | 0.129 | 0.000 | 0.129 | 0.500 | 0.500 | n/a |
| Wales | 7 | 4 | 0.667 | 0.244 | 0.571 | -0.328 | 0.857 | 0.667 | 0.000 |
| West Midlands | 9 | 1 | 0.500 | 0.114 | 0.111 | 0.003 | 0.444 | 0.500 | 1.000 |
| Yorkshire | 9 | 2 | 1.000 | 0.125 | 0.222 | -0.098 | 0.778 | 0.714 | 0.000 |

**Confidence:** SUPPRESSED — Spearman(bin, error) n/a, error top-30% n/a vs bottom-30% n/a. See reports/CONFIDENCE_VALIDATION.md.

## Feature and missingness drift

Descriptive synthetic distribution changes. KS statistics are not causal effects, real-world drift alerts or eligibility checks.

Reference uses held-out base customers; comparison uses independent perturbed-generator customers. Complete per-feature diagnostics are in reports/feature_drift.json.

| feature | ks_statistic | reference_median | comparison_median | reference_missing_rate | comparison_missing_rate | missingness_delta |
|---|---|---|---|---|---|---|
| electricity_spend_30d | 0.256 | 44.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| electricity_spend_12m_avg | 0.255 | 40.625 | 0.000 | 0.000 | 0.000 | 0.000 |
| electricity_spend_90d_avg | 0.255 | 44.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| electricity_spend_share_12m | 0.254 | 0.118 | 0.000 | 0.000 | 0.000 | 0.000 |
| electricity_txn_freq_90d | 0.254 | 3.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| utilities_spend_30d | 0.233 | 44.000 | 94.000 | 0.000 | 0.000 | 0.000 |
| utilities_spend_90d_avg | 0.232 | 44.000 | 90.462 | 0.000 | 0.000 | 0.000 |
| utilities_spend_share_12m | 0.231 | 0.135 | 0.276 | 0.000 | 0.000 | 0.000 |
| utilities_txn_freq_90d | 0.231 | 3.000 | 4.000 | 0.000 | 0.000 | 0.000 |
| utilities_spend_12m_avg | 0.227 | 44.000 | 85.749 | 0.000 | 0.000 | 0.000 |
| home_improvement_spend_share_12m | 0.201 | 0.023 | 0.038 | 0.000 | 0.000 | 0.000 |
| home_improvement_spend_90d_avg | 0.201 | 2.535 | 8.867 | 0.000 | 0.000 | 0.000 |

## Limitations

- Labels are simulated from latent stochastic drivers; relationships are not causal and the generator's structure bounds what any model can learn.
- Generator-shift and temporal results quantify robustness to *simulated* change only.
- Subgroup diagnostics use synthetic audit attributes; disparities are reported, not hidden or 'fixed'.
- Propensity is interest, not eligibility; confidence is reliability of the propensity decision; Trust is evidence adequacy. None of these determine financial eligibility.
