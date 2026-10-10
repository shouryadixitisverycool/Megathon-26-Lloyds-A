# Confidence validation report

Confidence = validated probability that the displayed propensity yields a correct decision at the operational threshold (spec 16.3). Not eligibility, not a second propensity.

## EV_FINANCE

**Decision: SUPPRESSED**  (n=128)

Reasons:
- insufficient data: 128 rows < 200

- Spearman(bin, error): n/a (need <= -0.6)
- Error top 30% confidence: n/a; bottom 30%: n/a (need top <= 0.5 x bottom, bottom >= 0.02)

Standardised coefficients: margin=+0.262, local_cal_error=+0.860, ood_score=+0.362, instability=-0.547, recency_days=+0.182, intercept=+2.393

### Ablation

| variant | held-out AUC | passed |
|---|---|---|
| full | 0.851 | False |
| drop_margin | 0.857 | False |
| drop_local_cal_error | 0.742 | False |
| drop_ood_score | 0.890 | False |
| drop_instability | 0.853 | False |
| drop_recency_days | 0.840 | False |

### Stress scenarios

| scenario | n | passed | Spearman | top30 err | bottom30 err |
|---|---|---|---|---|---|
| perturbed_generator | 2226 | True | -0.942 | 0.030 | 0.350 |
| missing_data_30pct | 346 | True | -0.671 | 0.048 | 0.327 |

## GREEN_HOME

**Decision: SUPPRESSED**  (n=95)

Reasons:
- Confidence suppressed: validation has 197 rows and 2 correctness classes; at least 200 rows and both correct and incorrect decisions are required.

- Spearman(bin, error): n/a (need <= -0.6)
- Error top 30% confidence: n/a; bottom 30%: n/a (need top <= 0.5 x bottom, bottom >= 0.02)

### Ablation

| variant | held-out AUC | passed |
|---|---|---|

### Stress scenarios

| scenario | n | passed | Spearman | top30 err | bottom30 err |
|---|---|---|---|---|---|
| perturbed_generator | 1790 | False | n/a | n/a | n/a |
| missing_data_30pct | 279 | False | n/a | n/a | n/a |

## SOLAR_FINANCE

**Decision: SUPPRESSED**  (n=115)

Reasons:
- insufficient data: 115 rows < 200

- Spearman(bin, error): n/a (need <= -0.6)
- Error top 30% confidence: n/a; bottom 30%: n/a (need top <= 0.5 x bottom, bottom >= 0.02)

Standardised coefficients: margin=-0.017, local_cal_error=-1.493, ood_score=-0.108, instability=-0.359, recency_days=-0.290, intercept=+4.110

### Ablation

| variant | held-out AUC | passed |
|---|---|---|
| full | 0.869 | False |
| drop_margin | 0.871 | False |
| drop_local_cal_error | 0.921 | False |
| drop_ood_score | 0.875 | False |
| drop_instability | 0.858 | False |
| drop_recency_days | 0.863 | False |

### Stress scenarios

| scenario | n | passed | Spearman | top30 err | bottom30 err |
|---|---|---|---|---|---|
| perturbed_generator | 2398 | False | -0.511 | 0.004 | 0.306 |
| missing_data_30pct | 354 | False | -0.567 | 0.009 | 0.283 |

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
