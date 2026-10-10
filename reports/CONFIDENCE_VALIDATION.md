# Confidence validation report

Confidence = validated probability that the displayed propensity yields a correct decision at the operational threshold (spec 16.3). Not eligibility, not a second propensity.

## EV_FINANCE

**Decision: SURFACED**  (n=344)

- Spearman(bin, error): -0.818 (need <= -0.6)
- Error top 30% confidence: 0.039; bottom 30%: 0.495 (need top <= 0.5 x bottom, bottom >= 0.02)

| bin | n | mean confidence | error rate | calibration gap |
|---|---|---|---|---|
| 1 | 35 | 0.323 | 0.486 | -0.191 |
| 2 | 34 | 0.548 | 0.529 | +0.078 |
| 3 | 35 | 0.606 | 0.457 | +0.063 |
| 4 | 34 | 0.711 | 0.382 | +0.093 |
| 5 | 34 | 0.857 | 0.118 | -0.025 |
| 6 | 35 | 0.883 | 0.029 | -0.088 |
| 7 | 34 | 0.901 | 0.029 | -0.069 |
| 8 | 35 | 0.921 | 0.057 | -0.022 |
| 9 | 34 | 0.964 | 0.000 | -0.036 |
| 10 | 34 | 0.979 | 0.059 | +0.038 |

Standardised coefficients: margin=+0.465, local_cal_error=+0.898, ood_score=-0.111, instability=-0.709, recency_days=+0.175, intercept=+1.817

### Ablation

| variant | test AUC | passed |
|---|---|---|
| full | 0.817 | True |
| drop_margin | 0.801 | True |
| drop_local_cal_error | 0.817 | True |
| drop_ood_score | 0.823 | True |
| drop_instability | 0.797 | True |
| drop_recency_days | 0.820 | True |

### Stress scenarios

| scenario | n | passed | Spearman | top30 err | bottom30 err |
|---|---|---|---|---|---|
| perturbed_generator | 2222 | True | -0.867 | 0.036 | 0.574 |
| missing_data_30pct | 344 | True | -0.604 | 0.068 | 0.311 |

## GREEN_HOME

**Decision: SURFACED**  (n=277)

- Spearman(bin, error): -0.964 (need <= -0.6)
- Error top 30% confidence: 0.060; bottom 30%: 0.735 (need top <= 0.5 x bottom, bottom >= 0.02)

| bin | n | mean confidence | error rate | calibration gap |
|---|---|---|---|---|
| 1 | 28 | 0.149 | 0.750 | -0.101 |
| 2 | 28 | 0.358 | 0.786 | +0.144 |
| 3 | 28 | 0.589 | 0.679 | +0.268 |
| 4 | 27 | 0.689 | 0.556 | +0.244 |
| 5 | 28 | 0.736 | 0.286 | +0.022 |
| 6 | 28 | 0.782 | 0.393 | +0.175 |
| 7 | 27 | 0.825 | 0.148 | -0.026 |
| 8 | 28 | 0.869 | 0.107 | -0.023 |
| 9 | 28 | 0.903 | 0.036 | -0.061 |
| 10 | 27 | 0.927 | 0.037 | -0.036 |

Standardised coefficients: margin=+0.352, local_cal_error=-0.105, ood_score=-0.439, instability=-1.525, recency_days=-0.044, intercept=+0.975

### Ablation

| variant | test AUC | passed |
|---|---|---|
| full | 0.835 | True |
| drop_margin | 0.825 | True |
| drop_local_cal_error | 0.834 | True |
| drop_ood_score | 0.823 | True |
| drop_instability | 0.737 | True |
| drop_recency_days | 0.834 | True |

### Stress scenarios

| scenario | n | passed | Spearman | top30 err | bottom30 err |
|---|---|---|---|---|---|
| perturbed_generator | 1787 | True | -0.988 | 0.108 | 0.757 |
| missing_data_30pct | 277 | True | -0.855 | 0.145 | 0.723 |

## SOLAR_FINANCE

**Decision: SURFACED**  (n=354)

- Spearman(bin, error): -0.701 (need <= -0.6)
- Error top 30% confidence: 0.000; bottom 30%: 0.264 (need top <= 0.5 x bottom, bottom >= 0.02)

| bin | n | mean confidence | error rate | calibration gap |
|---|---|---|---|---|
| 1 | 36 | 0.536 | 0.528 | +0.064 |
| 2 | 35 | 0.827 | 0.257 | +0.085 |
| 3 | 36 | 0.978 | 0.000 | -0.022 |
| 4 | 35 | 0.989 | 0.000 | -0.011 |
| 5 | 35 | 0.991 | 0.000 | -0.009 |
| 6 | 36 | 0.992 | 0.000 | -0.008 |
| 7 | 35 | 0.993 | 0.000 | -0.007 |
| 8 | 36 | 0.993 | 0.000 | -0.007 |
| 9 | 35 | 0.994 | 0.000 | -0.006 |
| 10 | 35 | 0.995 | 0.000 | -0.005 |

Standardised coefficients: margin=+0.070, local_cal_error=-1.690, ood_score=-0.155, instability=+0.080, recency_days=+0.263, intercept=+4.068

### Ablation

| variant | test AUC | passed |
|---|---|---|
| full | 0.951 | True |
| drop_margin | 0.945 | True |
| drop_local_cal_error | 0.930 | True |
| drop_ood_score | 0.948 | True |
| drop_instability | 0.953 | True |
| drop_recency_days | 0.955 | True |

### Stress scenarios

| scenario | n | passed | Spearman | top30 err | bottom30 err |
|---|---|---|---|---|---|
| perturbed_generator | 2396 | True | -0.888 | 0.000 | 0.284 |
| missing_data_30pct | 354 | True | -0.634 | 0.000 | 0.283 |

## PAPERLESS_BANKING

**Decision: SUPPRESSED**  (n=99)

Reasons:
- Confidence suppressed: validation has 93 rows and 2 correctness classes; at least 200 rows and both correct and incorrect decisions are required.

- Spearman(bin, error): n/a (need <= -0.6)
- Error top 30% confidence: n/a; bottom 30%: n/a (need top <= 0.5 x bottom, bottom >= 0.02)

### Ablation

| variant | test AUC | passed |
|---|---|---|

### Stress scenarios

| scenario | n | passed | Spearman | top30 err | bottom30 err |
|---|---|---|---|---|---|
| perturbed_generator | 627 | False | n/a | n/a | n/a |
| missing_data_30pct | 99 | False | n/a | n/a | n/a |
