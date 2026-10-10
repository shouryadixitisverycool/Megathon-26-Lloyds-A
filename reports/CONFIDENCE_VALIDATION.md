# Confidence validation report

Confidence = validated probability that the displayed propensity yields a correct decision at the operational threshold (spec 16.3). Not eligibility, not a second propensity.

## EV_FINANCE

**Decision: SUPPRESSED**  (n=128)

Reasons:
- insufficient data: 128 rows < 200

- Spearman(bin, error): n/a (need <= -0.6)
- Error top 30% confidence: n/a; bottom 30%: n/a (need top <= 0.5 x bottom, bottom >= 0.02)

Standardised coefficients: margin=+0.148, local_cal_error=-0.284, ood_score=+0.032, instability=-1.143, recency_days=-0.193, intercept=+1.954

### Ablation

| variant | held-out AUC | passed |
|---|---|---|
| full | 0.899 | False |
| drop_margin | 0.895 | False |
| drop_local_cal_error | 0.885 | False |
| drop_ood_score | 0.899 | False |
| drop_instability | 0.843 | False |
| drop_recency_days | 0.899 | False |

### Stress scenarios

| scenario | n | passed | Spearman | top30 err | bottom30 err |
|---|---|---|---|---|---|
| perturbed_generator | 2225 | True | -0.891 | 0.034 | 0.512 |
| missing_data_30pct | 345 | True | -0.915 | 0.010 | 0.529 |

## GREEN_HOME

**Decision: SUPPRESSED**  (n=95)

Reasons:
- Confidence suppressed: validation has 198 rows and 2 correctness classes; at least 200 rows and both correct and incorrect decisions are required.

- Spearman(bin, error): n/a (need <= -0.6)
- Error top 30% confidence: n/a; bottom 30%: n/a (need top <= 0.5 x bottom, bottom >= 0.02)

### Ablation

| variant | held-out AUC | passed |
|---|---|---|

### Stress scenarios

| scenario | n | passed | Spearman | top30 err | bottom30 err |
|---|---|---|---|---|---|
| perturbed_generator | 1793 | False | n/a | n/a | n/a |
| missing_data_30pct | 277 | False | n/a | n/a | n/a |

## SOLAR_FINANCE

**Decision: SUPPRESSED**  (n=114)

Reasons:
- insufficient data: 114 rows < 200

- Spearman(bin, error): n/a (need <= -0.6)
- Error top 30% confidence: n/a; bottom 30%: n/a (need top <= 0.5 x bottom, bottom >= 0.02)

Standardised coefficients: margin=+0.335, local_cal_error=-0.442, ood_score=-0.059, instability=-1.352, recency_days=+0.126, intercept=+2.638

### Ablation

| variant | held-out AUC | passed |
|---|---|---|
| full | 0.864 | False |
| drop_margin | 0.856 | False |
| drop_local_cal_error | 0.865 | False |
| drop_ood_score | 0.860 | False |
| drop_instability | 0.784 | False |
| drop_recency_days | 0.869 | False |

### Stress scenarios

| scenario | n | passed | Spearman | top30 err | bottom30 err |
|---|---|---|---|---|---|
| perturbed_generator | 2394 | True | -0.976 | 0.013 | 0.538 |
| missing_data_30pct | 354 | True | -0.791 | 0.028 | 0.264 |

## PAPERLESS_BANKING

**Decision: SUPPRESSED**  (n=39)

Reasons:
- Confidence suppressed: validation has 60 rows and 2 correctness classes; at least 200 rows and both correct and incorrect decisions are required.

- Spearman(bin, error): n/a (need <= -0.6)
- Error top 30% confidence: n/a; bottom 30%: n/a (need top <= 0.5 x bottom, bottom >= 0.02)

### Ablation

| variant | held-out AUC | passed |
|---|---|---|

### Stress scenarios

| scenario | n | passed | Spearman | top30 err | bottom30 err |
|---|---|---|---|---|---|
| perturbed_generator | 664 | False | n/a | n/a | n/a |
| missing_data_30pct | 105 | False | n/a | n/a | n/a |
