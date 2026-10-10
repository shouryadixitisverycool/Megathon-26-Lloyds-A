# Greenr — Agent A evaluation report (data, ML, reliability)

> All results are computed on synthetic data generated for this demonstration; they do not establish real-world predictive performance or eligibility.

Feature cutoff 2026-06-30; outcome = adoption within 90 days (to 2026-09-28); prediction timestamp 2026-10-10. Customer-level 70/15/15 split; one third of validation reserved for confidence release selection before tuning/calibration; demo personas excluded from training.

## Summary

| product | selected | ROC-AUC | heuristic AUC | logistic AUC | Brier | ECE | Lift@10% | ROC-AUC perturbed | confidence |
|---|---|---|---|---|---|---|---|---|---|
| EV_FINANCE | GRADIENT_BOOSTING | 0.693 | 0.714 | 0.711 | 0.072 | 0.011 | 1.408 | 0.645 | SUPPRESSED |
| GREEN_HOME | LOGISTIC | 0.675 | 0.689 | 0.675 | 0.084 | 0.019 | 1.902 | 0.651 | SUPPRESSED |
| SOLAR_FINANCE | LOGISTIC | 0.750 | 0.733 | 0.750 | 0.060 | 0.007 | 2.868 | 0.743 | SUPPRESSED |
| PAPERLESS_BANKING | LOGISTIC | 0.617 | 0.527 | 0.617 | 0.148 | 0.053 | 1.432 | 0.708 | SUPPRESSED |

## Transaction categorisation

Hybrid categoriser (deterministic merchant rules, then TF-IDF + logistic regression). Merchant-group split: test merchants never seen in training. Full details: reports/TRANSACTION_CATEGORISATION.md.

- unseen merchants: macro F1 0.543, weighted F1 0.524, rule coverage 0.142
- known merchants: macro F1 0.998, weighted F1 0.999, rule coverage 0.970
- perturbed-generator transactions (frozen categoriser): accuracy 0.835

## Trust diagnostics (held-out test)

Trust measures evidence adequacy and is separate from confidence. Model quality by Trust status:

*EV_FINANCE* — mean score 0.934, critical-field missing 0.046, high-severity conflict 0.003, OOD flag 0.012

| status | n | share | roc_auc | brier | calibration_gap |
|---|---|---|---|---|---|
| ADEQUATE | 11 | 0.032 | n/a | 0.006 | 0.073 |
| HIGH | 313 | 0.907 | 0.668 | 0.072 | -0.010 |
| INSUFFICIENT | 16 | 0.046 | n/a | 0.003 | 0.054 |
| LOW | 5 | 0.014 | 0.333 | 0.464 | -0.464 |

*GREEN_HOME* — mean score 0.907, critical-field missing 0.112, high-severity conflict 0.007, OOD flag 0.007

| status | n | share | roc_auc | brier | calibration_gap |
|---|---|---|---|---|---|
| ADEQUATE | 2 | 0.007 | 1.000 | 0.309 | -0.298 |
| HIGH | 238 | 0.859 | 0.629 | 0.075 | -0.001 |
| INSUFFICIENT | 31 | 0.112 | 0.738 | 0.132 | -0.045 |
| LOW | 6 | 0.022 | 0.800 | 0.146 | -0.049 |

*SOLAR_FINANCE* — mean score 0.874, critical-field missing 0.138, high-severity conflict 0.008, OOD flag 0.011

| status | n | share | roc_auc | brier | calibration_gap |
|---|---|---|---|---|---|
| ADEQUATE | 12 | 0.034 | 0.852 | 0.177 | -0.124 |
| HIGH | 290 | 0.819 | 0.707 | 0.055 | 0.014 |
| INSUFFICIENT | 49 | 0.138 | 0.839 | 0.068 | -0.006 |
| LOW | 3 | 0.008 | n/a | 0.001 | 0.032 |

*PAPERLESS_BANKING* — mean score 0.937, critical-field missing 0.057, high-severity conflict 0.000, OOD flag 0.019

| status | n | share | roc_auc | brier | calibration_gap |
|---|---|---|---|---|---|
| ADEQUATE | 3 | 0.029 | 1.000 | 0.278 | -0.385 |
| HIGH | 96 | 0.914 | 0.525 | 0.146 | -0.014 |
| INSUFFICIENT | 6 | 0.057 | 1.000 | 0.117 | -0.058 |

## Per-product detail

### EV_FINANCE

Selected model (by validation ROC-AUC, Brier tie-break): **GRADIENT_BOOSTING** `ev_finance_gbm_v1`; calibration **platt** `ev_finance_gbm_platt_v2_6c65431d4157428a` fitted on validation only.
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

### GREEN_HOME

Selected model (by validation ROC-AUC, Brier tie-break): **LOGISTIC** `green_home_logreg_v1`; calibration **platt** `green_home_logreg_platt_v2_499192a15c57436c` fitted on validation only.
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

### SOLAR_FINANCE

Selected model (by validation ROC-AUC, Brier tie-break): **LOGISTIC** `solar_finance_logreg_v1`; calibration **platt** `solar_finance_logreg_platt_v2_f629e13f268d1f5d` fitted on validation only.
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

### PAPERLESS_BANKING

Selected model (by validation ROC-AUC, Brier tie-break): **LOGISTIC** `paperless_banking_logreg_v1`; calibration **platt** `paperless_banking_logreg_platt_v2_0096b0e8b327dad0` fitted on validation only.
Train 530 (67 positive), validation 60 (10), held-out test 105 (20).

**Held-out test metrics** (calibrated probabilities; confusion metrics at each model's validation-chosen F1 threshold):

| model | ROC-AUC | PR-AUC | Brier | ECE | P@10% | R@10% | Lift@10% | precision | recall | F1 | threshold |
|---|---|---|---|---|---|---|---|---|---|---|---|
| HEURISTIC | 0.527 | 0.206 | 0.175 | 0.056 | 0.091 | 0.050 | 0.477 | 0.222 | 0.400 | 0.286 | 0.184 |
| LOGISTIC | 0.617 | 0.328 | 0.148 | 0.053 | 0.273 | 0.150 | 1.432 | 0.232 | 0.800 | 0.360 | 0.150 |
| GRADIENT_BOOSTING | 0.655 | 0.368 | 0.150 | 0.032 | 0.273 | 0.150 | 1.432 | 0.200 | 0.900 | 0.327 | 0.136 |

Calibration effect (selected model, test): Brier 0.154 → 0.148, ECE 0.074 → 0.053.

Baseline comparison: the selected model's ROC-AUC 0.617 is materially better than the heuristic baseline (0.527); logistic baseline 0.617.

**Generator shift** (models trained on generator A, scored on perturbed generator B):

| model | ROC-AUC A | ROC-AUC B | PR-AUC A | PR-AUC B | ΔBrier | ΔECE (calibration shift) | ΔLift@10% |
|---|---|---|---|---|---|---|---|
| HEURISTIC | 0.527 | 0.706 | 0.206 | 0.228 | -0.066 | -0.013 | 1.970 |
| LOGISTIC | 0.617 | 0.708 | 0.328 | 0.226 | -0.044 | -0.011 | 0.648 |
| GRADIENT_BOOSTING | 0.655 | 0.673 | 0.368 | 0.210 | -0.044 | 0.016 | 0.281 |

**Missing-data stress** (selected model, held-out test):

| scenario | ROC-AUC | PR-AUC | Brier | ECE | Lift@10% |
|---|---|---|---|---|---|
| mileage_missing | 0.617 | 0.328 | 0.148 | 0.053 | 1.432 |
| energy_missing | 0.617 | 0.328 | 0.148 | 0.053 | 1.432 |
| home_ownership_unknown | 0.617 | 0.328 | 0.148 | 0.053 | 1.432 |
| sustainability_preference_missing | 0.627 | 0.327 | 0.147 | 0.057 | 1.432 |
| digital_missing | 0.584 | 0.369 | 0.160 | 0.096 | 1.909 |
| random_30pct_cells | 0.661 | 0.322 | 0.152 | 0.054 | 1.432 |

**Temporal holdout:** retrained at 2026-03-31, tested at 2026-06-30 on held-out customers: ROC-AUC 0.585, Brier 0.150, ECE 0.037.

**Proxy ablation** (spec 12.2):

| variant | ROC-AUC | Brier | ECE | selection-rate range across income bands | max |calibration gap| across income bands |
|---|---|---|---|---|---|
| without proxies (default) | 0.617 | 0.148 | 0.053 | 0.178 | 0.264 |
| with income band + region | 0.596 | 0.154 | 0.032 | 0.471 | 0.247 |

Decision: default to the model **without** proxies (ΔROC-AUC with proxies = -0.021); proxies are not justified unless they add clear value without widening disparity.

**Subgroup diagnostics** (audit-only attributes, selected model):

*age_band*

| group | n | positives | roc_auc | mean_pred | observed_rate | calibration_gap | selection_rate | fpr | fnr |
|---|---|---|---|---|---|---|---|---|---|
| 18-24 | 3 | 0 | n/a | 0.192 | 0.000 | 0.192 | 1.000 | 1.000 | n/a |
| 25-34 | 7 | 1 | 1.000 | 0.200 | 0.143 | 0.057 | 0.714 | 0.667 | 0.000 |
| 35-44 | 23 | 4 | 0.566 | 0.163 | 0.174 | -0.011 | 0.783 | 0.737 | 0.000 |
| 45-54 | 28 | 6 | 0.773 | 0.153 | 0.214 | -0.062 | 0.643 | 0.591 | 0.167 |
| 55-64 | 24 | 7 | 0.639 | 0.167 | 0.292 | -0.125 | 0.583 | 0.529 | 0.286 |
| 65+ | 20 | 2 | 0.389 | 0.158 | 0.100 | 0.058 | 0.550 | 0.556 | 0.500 |

*income_band*

| group | n | positives | roc_auc | mean_pred | observed_rate | calibration_gap | selection_rate | fpr | fnr |
|---|---|---|---|---|---|---|---|---|---|
| 100k+ | 7 | 3 | 0.250 | 0.164 | 0.429 | -0.264 | 0.714 | 0.750 | 0.333 |
| 25-50k | 35 | 5 | 0.467 | 0.161 | 0.143 | 0.018 | 0.629 | 0.633 | 0.400 |
| 50-75k | 34 | 7 | 0.762 | 0.171 | 0.206 | -0.034 | 0.676 | 0.630 | 0.143 |
| 75-100k | 9 | 2 | 0.714 | 0.154 | 0.222 | -0.068 | 0.778 | 0.714 | 0.000 |
| <25k | 20 | 3 | 0.686 | 0.158 | 0.150 | 0.008 | 0.600 | 0.529 | 0.000 |

*region*

| group | n | positives | roc_auc | mean_pred | observed_rate | calibration_gap | selection_rate | fpr | fnr |
|---|---|---|---|---|---|---|---|---|---|
| East Midlands | 10 | 2 | 0.750 | 0.150 | 0.200 | -0.050 | 0.600 | 0.500 | 0.000 |
| East of England | 11 | 2 | 0.833 | 0.168 | 0.182 | -0.013 | 0.818 | 0.778 | 0.000 |
| London | 12 | 1 | 0.909 | 0.145 | 0.083 | 0.061 | 0.500 | 0.455 | 0.000 |
| North East | 5 | 0 | n/a | 0.168 | 0.000 | 0.168 | 0.800 | 0.800 | n/a |
| North West | 13 | 3 | 0.200 | 0.172 | 0.231 | -0.059 | 0.769 | 0.900 | 0.667 |
| Scotland | 8 | 1 | 0.429 | 0.154 | 0.125 | 0.029 | 0.375 | 0.429 | 1.000 |
| South East | 12 | 3 | 0.519 | 0.162 | 0.250 | -0.088 | 0.583 | 0.556 | 0.333 |
| South West | 5 | 1 | 0.250 | 0.186 | 0.200 | -0.014 | 1.000 | 1.000 | 0.000 |
| UNKNOWN | 2 | 0 | n/a | 0.153 | 0.000 | 0.153 | 0.500 | 0.500 | n/a |
| Wales | 7 | 4 | 0.833 | 0.221 | 0.571 | -0.350 | 1.000 | 1.000 | 0.000 |
| West Midlands | 11 | 1 | 0.700 | 0.152 | 0.091 | 0.061 | 0.545 | 0.500 | 0.000 |
| Yorkshire | 9 | 2 | 0.786 | 0.152 | 0.222 | -0.070 | 0.556 | 0.429 | 0.000 |

**Confidence:** SUPPRESSED — Spearman(bin, error) n/a, error top-30% n/a vs bottom-30% n/a. See reports/CONFIDENCE_VALIDATION.md.

## Feature and missingness drift

Descriptive synthetic distribution changes. KS statistics are not causal effects, real-world drift alerts or eligibility checks.

Reference uses held-out base customers; comparison uses independent perturbed-generator customers. Complete per-feature diagnostics are in reports/feature_drift.json.

| feature | ks_statistic | reference_median | comparison_median | reference_missing_rate | comparison_missing_rate | missingness_delta |
|---|---|---|---|---|---|---|
| home_improvement_spend_90d_avg | 0.227 | 0.000 | 7.713 | 0.000 | 0.000 | 0.000 |
| home_improvement_txn_freq_90d | 0.227 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| home_improvement_spend_share_12m | 0.198 | 0.021 | 0.039 | 0.000 | 0.000 | 0.000 |
| home_improvement_days_since_last | 0.192 | 82.000 | 45.000 | 0.113 | 0.021 | -0.092 |
| home_improvement_spend_12m_avg | 0.175 | 7.557 | 11.945 | 0.000 | 0.000 | 0.000 |
| utilities_txn_freq_90d | 0.170 | 3.000 | 3.000 | 0.000 | 0.000 | 0.000 |
| home_improvement_spend_trend | 0.169 | -0.675 | -0.348 | 0.155 | 0.039 | -0.116 |
| utilities_spend_share_12m | 0.156 | 0.131 | 0.194 | 0.000 | 0.000 | 0.000 |
| public_transport_spend_share_12m | 0.155 | 0.009 | 0.018 | 0.000 | 0.000 | 0.000 |
| utilities_spend_12m_avg | 0.151 | 42.000 | 53.429 | 0.000 | 0.000 | 0.000 |
| mileage_is_estimated | 0.150 | 0.000 | 0.000 | 0.217 | 0.258 | 0.042 |
| utilities_spend_90d_avg | 0.145 | 42.000 | 54.000 | 0.000 | 0.000 | 0.000 |

## Limitations

- Labels are simulated from latent stochastic drivers; relationships are not causal and the generator's structure bounds what any model can learn.
- Generator-shift and temporal results quantify robustness to *simulated* change only.
- Subgroup diagnostics use synthetic audit attributes; disparities are reported, not hidden or 'fixed'.
- Propensity is interest, not eligibility; confidence is reliability of the propensity decision; Trust is evidence adequacy. None of these determine financial eligibility.
