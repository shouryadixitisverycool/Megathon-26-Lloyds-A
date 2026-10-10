# Dataset Engineering Verification

Updated 2026-10-10 after the focused Lloyds briefing dataset audit.

## Correctness Changes

- Energy direct-debit resets depend on completed past usage or an initial known baseline forecast, not future adoption-adjusted consumption. Regression tests change future adoption and require earlier transactions to remain identical.
- Vehicle renewals follow the adopted vehicle state unless an explicitly configured stale-record case applies.
- `customer_history` retains effective-dated profiles; Customer 360 selects only records effective and available at its cutoff.
- `vehicle_ownership` distinguishes a known non-owner from an unknown declaration. The default simulator still models one primary vehicle per customer, not arbitrary household fleets.
- Digital records retain `paperless_effective_at`. Conflict checks distinguish earlier behavior from activity after an effective state change.
- Energy features retain separate electricity/gas observation counts, observed sums, annualisation factors and estimated flags. Annualised partial history is not labelled a measured annual total.
- `outcome_observation` declares follow-up coverage and availability. Coverage-aware labels do not turn unsupported negative outcomes into zero. The default simulator explicitly has complete follow-up; incomplete coverage is exercised by tests.
- Historical score context uses cutoff-available profiles instead of current raw region/segment values.
- Bare `GOOD ENERGY` is classified as bundled/unspecified Utilities; electricity-specific descriptions remain Electricity. EV charging and refund boundary cases have explicit tests.

## Scenario Evidence

`scenario_evidence` is separate from propensity features. The ten demo personas have 100 assumption records, available at the main cutoff. EV efficiency, insulation savings and paper avoidance are explicitly chosen hypothetical engineering assumptions, not observed facts, verified product performance, or estimates inferred from banking spend.

Current and historical impact inputs select scenario evidence by customer, product, effective date and availability date. Earlier cutoffs cannot use later assumptions. Solar remains unavailable without reviewed generation evidence; no generic regional yield is invented. Carbon is not claimed for Paperless Banking.

## Verification

| Check | Result |
|---|---|
| Pipeline | `make pipeline CUSTOMERS=4000` passed in approximately 54 seconds |
| Base population | 4,010 customers; 877,757 transactions |
| Source history | 9,550 customer profiles; 5,660 ownership declarations |
| Outcome coverage | 16,040 complete customer/product pairs |
| Held-out predictions | 2,400 rows |
| Dataset invariants | Schemas, primary keys, foreign keys, transaction/truth bijection and merchant truth passed |
| Temporal checks | Point-in-time rebuild and leakage gates passed |
| Full tests | 1,292 passed; 2 explicitly skipped |
| Offline explanations | 200/200 passed |
| Fixture decision scenarios | 24/24 passed |

See `reports/dataset_quality.json`, `reports/leakage_checks.json`, regenerated model/data cards and `reports/RUN_MANIFEST.json` for detailed evidence. `make all` now refreshes its manifest after evaluation outputs; `make manifest` also supports standalone refresh.

## Remaining Boundaries

- These checks establish synthetic consistency and tested behavior, not real-world predictive validity or universal case coverage.
- Missingness, natural adoption imbalance and deliberately contradictory records are retained; uniformity means consistent contracts and interpretation, not identical customers.
- Household multi-vehicle modeling, linked purchase/refund accounting and broad real-bank ingestion remain outside this focused repair.
- Scenario assumptions cover a declared demo subset, not the entire portfolio. Missing physical evidence still returns unavailable.
- Confidence is suppressed for all four products in this run; no thresholds were relaxed to force display.
- Expensive system benchmarking was deliberately not rerun. Its retained report is explicitly stale and inconsistent with this dataset release; hashing its bytes does not certify its measurements.
- Live-provider evaluation and observed customer outcomes were not fabricated or measured.
