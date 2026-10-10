# Leakage audit

Automated checks run in `make train`; the run fails on any violation (implementation: `greenpath.pipelines.leakage_checks`, tests: `tests/pipelines/test_leakage_checks.py` include deliberately invalid examples that must fail).

| Area | Control | Result |
|---|---|---|
| Feature provenance | Feature registry records source table, event-time column and availability for each feature (DATA_CARD.md) | documented |
| Cutoff timing | Customer 360 rebuilt from inputs truncated at 2026-06-30 equals production build (84 features × 4010 customers) | **PASS** |
| Customer split integrity | No customer in more than one of train/validation/test/demo | see below |
| Label construction | Labels = adoption in (cutoff, cutoff+90d] from `customer_outcomes`, a truth table never read by the feature pipeline | by construction + tests |
| Latent-variable leakage | Generator latent traits are never written to any raw table | by construction |
| Target-derived features | No feature name matching adopt/label/target/take_up/outcome | see below |
| Post-adoption flags | Product's own holding flags (holds_*, is_ev, has_existing_solar, is_paperless) excluded from that product's features; used only as population filters | see below |
| Merchant duplication | Categoriser evaluated on a merchant-group split (unseen merchants) | reports/TRANSACTION_CATEGORISATION.md |
| Future information | Vehicle history as-of cutoff; products as-of start/end dates; monthly data only once the month has ended | point-in-time rebuild |
| Proxy / audit attributes | age band, income band, region, postcode excluded from propensity features | see below |

## Check results

### EV_FINANCE

| check | target | status | detail |
|---|---|---|---|
| customer_split_disjoint | split | PASS | 5 splits, 4010 customers, no customer in more than one split |
| event_times_within_cutoff | transactions | PASS | transactions: 745317 rows with event time on or before cutoff 2026-06-30 |
| source_available_within_cutoff | transactions | PASS | transactions: 745317 rows with event time on or before cutoff 2026-06-30 |
| event_times_within_cutoff | financial_products | PASS | financial_products: 12698 rows with event time on or before cutoff 2026-06-30 |
| source_available_within_cutoff | financial_products | PASS | financial_products: 12698 rows with event time on or before cutoff 2026-06-30 |
| event_times_within_cutoff | vehicles | PASS | vehicles: 4526 rows with event time on or before cutoff 2026-06-30 |
| source_available_within_cutoff | vehicles | PASS | vehicles: 4526 rows with event time on or before cutoff 2026-06-30 |
| event_times_within_cutoff | energy_usage | PASS | energy_usage: 58436 rows with month-end availability on or before cutoff 2026-06-30 |
| source_available_within_cutoff | energy_usage | PASS | energy_usage: 58436 rows with event time on or before cutoff 2026-06-30 |
| event_times_within_cutoff | digital_usage | PASS | digital_usage: 64339 rows with month-end availability on or before cutoff 2026-06-30 |
| source_available_within_cutoff | digital_usage | PASS | digital_usage: 64339 rows with event time on or before cutoff 2026-06-30 |
| event_times_within_cutoff | customers_available_profiles | PASS | customers_available_profiles: 3061 rows with event time on or before cutoff 2026-06-30 |
| source_available_within_cutoff | customers_available_profiles | PASS | customers_available_profiles: 3061 rows with event time on or before cutoff 2026-06-30 |
| no_target_features | features | PASS | 25 feature names, none target-like |
| no_audit_features | features | PASS | 25 feature names, none audit-only or proxy |
| no_post_adoption_features | EV_FINANCE | PASS | EV_FINANCE: none of ['holds_ev_finance', 'is_ev'] used as features |

### GREEN_HOME

| check | target | status | detail |
|---|---|---|---|
| customer_split_disjoint | split | PASS | 5 splits, 4010 customers, no customer in more than one split |
| event_times_within_cutoff | transactions | PASS | transactions: 745317 rows with event time on or before cutoff 2026-06-30 |
| source_available_within_cutoff | transactions | PASS | transactions: 745317 rows with event time on or before cutoff 2026-06-30 |
| event_times_within_cutoff | financial_products | PASS | financial_products: 12698 rows with event time on or before cutoff 2026-06-30 |
| source_available_within_cutoff | financial_products | PASS | financial_products: 12698 rows with event time on or before cutoff 2026-06-30 |
| event_times_within_cutoff | vehicles | PASS | vehicles: 4526 rows with event time on or before cutoff 2026-06-30 |
| source_available_within_cutoff | vehicles | PASS | vehicles: 4526 rows with event time on or before cutoff 2026-06-30 |
| event_times_within_cutoff | energy_usage | PASS | energy_usage: 58436 rows with month-end availability on or before cutoff 2026-06-30 |
| source_available_within_cutoff | energy_usage | PASS | energy_usage: 58436 rows with event time on or before cutoff 2026-06-30 |
| event_times_within_cutoff | digital_usage | PASS | digital_usage: 64339 rows with month-end availability on or before cutoff 2026-06-30 |
| source_available_within_cutoff | digital_usage | PASS | digital_usage: 64339 rows with event time on or before cutoff 2026-06-30 |
| event_times_within_cutoff | customers_available_profiles | PASS | customers_available_profiles: 3061 rows with event time on or before cutoff 2026-06-30 |
| source_available_within_cutoff | customers_available_profiles | PASS | customers_available_profiles: 3061 rows with event time on or before cutoff 2026-06-30 |
| no_target_features | features | PASS | 31 feature names, none target-like |
| no_audit_features | features | PASS | 31 feature names, none audit-only or proxy |
| no_post_adoption_features | GREEN_HOME | PASS | GREEN_HOME: none of ['holds_green_home_loan'] used as features |

### SOLAR_FINANCE

| check | target | status | detail |
|---|---|---|---|
| customer_split_disjoint | split | PASS | 5 splits, 4010 customers, no customer in more than one split |
| event_times_within_cutoff | transactions | PASS | transactions: 745317 rows with event time on or before cutoff 2026-06-30 |
| source_available_within_cutoff | transactions | PASS | transactions: 745317 rows with event time on or before cutoff 2026-06-30 |
| event_times_within_cutoff | financial_products | PASS | financial_products: 12698 rows with event time on or before cutoff 2026-06-30 |
| source_available_within_cutoff | financial_products | PASS | financial_products: 12698 rows with event time on or before cutoff 2026-06-30 |
| event_times_within_cutoff | vehicles | PASS | vehicles: 4526 rows with event time on or before cutoff 2026-06-30 |
| source_available_within_cutoff | vehicles | PASS | vehicles: 4526 rows with event time on or before cutoff 2026-06-30 |
| event_times_within_cutoff | energy_usage | PASS | energy_usage: 58436 rows with month-end availability on or before cutoff 2026-06-30 |
| source_available_within_cutoff | energy_usage | PASS | energy_usage: 58436 rows with event time on or before cutoff 2026-06-30 |
| event_times_within_cutoff | digital_usage | PASS | digital_usage: 64339 rows with month-end availability on or before cutoff 2026-06-30 |
| source_available_within_cutoff | digital_usage | PASS | digital_usage: 64339 rows with event time on or before cutoff 2026-06-30 |
| event_times_within_cutoff | customers_available_profiles | PASS | customers_available_profiles: 3061 rows with event time on or before cutoff 2026-06-30 |
| source_available_within_cutoff | customers_available_profiles | PASS | customers_available_profiles: 3061 rows with event time on or before cutoff 2026-06-30 |
| no_target_features | features | PASS | 22 feature names, none target-like |
| no_audit_features | features | PASS | 22 feature names, none audit-only or proxy |
| no_post_adoption_features | SOLAR_FINANCE | PASS | SOLAR_FINANCE: none of ['has_existing_solar', 'holds_solar_finance'] used as features |

### PAPERLESS_BANKING

| check | target | status | detail |
|---|---|---|---|
| customer_split_disjoint | split | PASS | 5 splits, 4010 customers, no customer in more than one split |
| event_times_within_cutoff | transactions | PASS | transactions: 745317 rows with event time on or before cutoff 2026-06-30 |
| source_available_within_cutoff | transactions | PASS | transactions: 745317 rows with event time on or before cutoff 2026-06-30 |
| event_times_within_cutoff | financial_products | PASS | financial_products: 12698 rows with event time on or before cutoff 2026-06-30 |
| source_available_within_cutoff | financial_products | PASS | financial_products: 12698 rows with event time on or before cutoff 2026-06-30 |
| event_times_within_cutoff | vehicles | PASS | vehicles: 4526 rows with event time on or before cutoff 2026-06-30 |
| source_available_within_cutoff | vehicles | PASS | vehicles: 4526 rows with event time on or before cutoff 2026-06-30 |
| event_times_within_cutoff | energy_usage | PASS | energy_usage: 58436 rows with month-end availability on or before cutoff 2026-06-30 |
| source_available_within_cutoff | energy_usage | PASS | energy_usage: 58436 rows with event time on or before cutoff 2026-06-30 |
| event_times_within_cutoff | digital_usage | PASS | digital_usage: 64339 rows with month-end availability on or before cutoff 2026-06-30 |
| source_available_within_cutoff | digital_usage | PASS | digital_usage: 64339 rows with event time on or before cutoff 2026-06-30 |
| event_times_within_cutoff | customers_available_profiles | PASS | customers_available_profiles: 3061 rows with event time on or before cutoff 2026-06-30 |
| source_available_within_cutoff | customers_available_profiles | PASS | customers_available_profiles: 3061 rows with event time on or before cutoff 2026-06-30 |
| no_target_features | features | PASS | 13 feature names, none target-like |
| no_audit_features | features | PASS | 13 feature names, none audit-only or proxy |
| no_post_adoption_features | PAPERLESS_BANKING | PASS | PAPERLESS_BANKING: none of ['is_paperless'] used as features |

## Historical cutoff rebuilds

| cutoff | status | features_compared | customers_compared | differences |
|---|---|---|---|---|
| 2026-01-31 | PASS | 84 | 3919 | [] |
| 2026-02-28 | PASS | 84 | 3938 | [] |
| 2026-03-31 | PASS | 84 | 3957 | [] |
| 2026-04-30 | PASS | 84 | 3976 | [] |
| 2026-05-31 | PASS | 84 | 4002 | [] |
| 2026-06-30 | PASS | 84 | 4010 | [] |
