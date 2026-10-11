# Core confidence: 50,000-customer experiment

2026-10-11. **Exploratory synthetic evidence, not production reliability certification.**

## Outcome and promotion decision

Increasing sample support resolves all four products' original support failures.
All four refitted `conf_meta_v2` models pass the **unchanged** reserved-cohort
ranking gate. However, every meta-model has worse correctness Brier loss than
the simple deployed-propensity baseline. Do not interpret a ranking-gate pass as
proof of incremental probability reliability or real-world validation.

**No promotion:** this experiment remains isolated. Existing deployment artifacts
and reports were not replaced; old confidence methods remain suppressed until
refit/revalidation. Missing confidence or comparable impact leaves both composite
priority score and rank unavailable, without weight renormalisation.

| Product | Fit rows | Reserved rows | Reserved errors | Spearman | Top / bottom error | Meta Brier | Constant Brier | Propensity-derived Brier |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| EV Finance | 2,945 | 1,478 | 319 | -1.000 | 0.041 / 0.453 | 0.1391 | 0.1693 | 0.0549 |
| Green Home | 2,421 | 1,186 | 282 | -0.979 | 0.104 / 0.348 | 0.1704 | 0.1813 | 0.0748 |
| Solar Finance | 3,042 | 1,579 | 134 | -0.994 | 0.015 / 0.192 | 0.0696 | 0.0777 | 0.0510 |
| Paperless Banking | 972 | 490 | 157 | -0.967 | 0.068 / 0.646 | 0.1516 | 0.2185 | 0.1150 |

Brier measures squared probability error; lower is better. The constant baseline
is estimated only on fitting validation. The propensity baseline is
`where(p >= operational_threshold, p, 1-p)`, not `max(p, 1-p)` when the operational
threshold differs from 0.5. Diagnostics do not alter release selection.

The preserved gate requires at least 200 reserved rows, Spearman <= -0.6,
top-30% error <= half bottom-30% error, and bottom-30% error >= 0.02; ties cannot
manufacture distinct groups. Reserved customers are excluded from propensity
tuning/calibration and confidence fitting. Final test/stress are reporting-only.

## Data, fixes and evidence

- Base: 50,010 customers including ten excluded demo personas; 11,029,170 transactions.
- Perturbed: 50,000 customers; 10,909,405 transactions.
- Compared with the existing generator manifests, **only `n_customers` changed**:
  rates, noise, missingness, interactions and seeds were preserved.
- Confidence masking is now deterministic by approved feature values, seed, draw
  and column, rather than batch position. Single/bulk/reorder/chunk and omitted
  versus explicit-missing feature tests cover equivalence. Method version is v2;
  old/unversioned joblib instances fail closed rather than silently inheriting v2.
- Reports now distinguish fitting support from release support and retain
  correctness counts, fixed baselines, Brier/ECE and split-selection provenance.
- Dataset integrity no longer builds huge Python transaction-ID sets. Unique
  primary keys, equal counts and membership still prove exact truth bijection.

Workspace: `/tmp/opencode/greenr-confidence-50k-20261011`.
Reviewable machine-readable results, configuration/source fingerprints and artifact
hashes are retained in `reports/confidence_50k_evidence.json` in this checkout.
See its `reports/CONFIDENCE_VALIDATION.md`, `reports/confidence_validation.json`,
`data/artifacts/confidence/decisions.json`, and `reports/leakage_checks.json`.
The completed evaluation stage adds `reports/confidence_experiment.json`,
`reports/experiment_source.json` and `reports/RUN_MANIFEST.json`, including
reporting-only stress/test results and actual-model runtime equivalence checks.
All four final-test diagnostics passed and all four actual trained models matched
single-row/batch confidence values and buckets (maximum difference <= 2.23e-16).
Generator-shift diagnostics passed for all four. **Green Home failed the 30% missing
data stress gate:** top error 0.326 versus bottom 0.532, exceeding the unchanged
0.5 ratio limit. The other products passed missingness stress. This is an additional
reason not to promote the experimental bundles; stress does not retune release.

## Verification scope and remaining work

Canonical-cutoff point-in-time rebuilding and product leakage guards passed.
Focused changed-path suite: **83 passed**, one dependency deprecation warning.
Separate split/leakage/outcome/source-history suite: **92 passed**.
Broader downstream checks: **185 passed, 2 failed** at unchanged warmed-cache
tuple-identity assertions in `tests/integration/test_trained_safety.py:84`.
Those assertions were subsequently fixed independently in upstream commit
`be3a45e` (PR #2). After basing this PR on that updated `finish-agent-a` branch,
the combined changed-path and downstream suite passed: **271 passed**, one
dependency deprecation warning. The earlier failure counts are historical, not
outstanding failures on this PR's base.
The fresh-training acceptance group exceeded its 90-second check budget; no full
suite, browser, historical-cutoff/proxy/SHAP or `make all` certification is claimed.

Next model-design work must use development data, not tune against these now-seen
reserved or final-test labels. Investigate decision-side-aware reliability features
and compare against the stronger propensity-derived baseline; predefine probability
calibration/uncertainty acceptance criteria and reserve new untouched release data
before promotion. Do not lower the existing gate or change simulated rates to pass.

## Reproduction

```bash
export GREENR_WORKSPACE=/tmp/opencode/greenr-confidence-50k-reproduction
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --locked python -m greenr.data_generation --customers 50000
uv run --locked python -m greenr.data_generation --perturbed --customers 50000
uv run --locked python scripts/confidence_experiment.py prepare --workspace "$GREENR_WORKSPACE"
uv run --locked python scripts/confidence_experiment.py train --workspace "$GREENR_WORKSPACE"
uv run --locked python scripts/confidence_experiment.py evaluate --workspace "$GREENR_WORKSPACE"
```

Use a fresh isolated workspace; this focused experiment intentionally does not
replace the full release pipeline or install its bundles into the existing demo.
