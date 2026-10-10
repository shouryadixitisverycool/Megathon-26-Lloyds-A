# Data card

**All data is synthetic.** No real customer, banking or confidential data is used.

| Kind | Content |
|---|---|
| Observed public data | Pinned DESNZ Great Britain domestic-meter electricity and gas annual mean/median; aggregate statistical anchors, with no public customer-level data bundled. |
| Synthetic features | customers, transactions, financial_products, vehicles (history), energy_usage, digital_usage |
| Synthetic labels | customer_outcomes: adoption dates simulated from latent stochastic drivers + noise (spec 8.2) |
| Simulator-derived evaluation truth | transaction_truth, merchants (categorisation evaluation only) |

Generator config hash: `5b189503ed5002a61e17e2f25cd384774a6d2455c5a218f2f6ffbbf1f4648a93`; seed 42; perturbed generator seed 45.

## Tables

| table | rows | sha256 |
|---|---|---|
| customers | 4010 | `ddd99568535e92dc` |
| transactions | 874498 | `fd04669e19c6c078` |
| financial_products | 13182 | `06feb0686caba491` |
| vehicles | 4744 | `aa23c6c01f1b95ba` |
| energy_usage | 72752 | `d0baf2f1b0f20ada` |
| digital_usage | 80119 | `9f935754ac884e37` |
| green_product_catalogue | 4 | `21c19a60e8e5438f` |
| transaction_truth | 874498 | `528550173d46d5ff` |
| merchants | 146 | `33520abe59bb2d33` |
| customer_outcomes | 6879 | `41dcf66dd9ecd779` |

## Public energy anchors

Source: [Subnational electricity and gas consumption summary report 2024](https://www.gov.uk/government/statistics/subnational-electricity-and-gas-consumption-summary-report-2024/subnational-electricity-and-gas-consumption-summary-report-2024--2). Publisher: Department for Energy Security and Net Zero; licence: Open Government Licence v3.0.
Pinned reference SHA256: `ee32eacd62c162d19ee0c674e05aa6b1209c19a0fff41ccb476acb7ea7f1a2cb`.
Annual household demand is sampled from a lognormal distribution matched to public mean and median, then ranked against synthetic household scores. Gas references apply to gas-consuming households.

Diagnostic calendar year: 2025. Complete calendar-year synthetic observations, including adoption effects and observation noise. Gas includes positive consumers only. Not a real-world predictive validation.

| fuel | n_complete_consumers | observed_mean_kwh | reference_mean_kwh | observed_median_kwh | reference_median_kwh |
|---|---|---|---|---|---|
| electricity | 2685 | 3379.591 | 3323 | 2644.800 | 2471 |
| gas | 2376 | 11438.419 | 11359 | 10036.400 | 9859 |


## Feature registry

Every feature is labelled with source, event time, prediction-time availability and policy (spec 7.3).

| name | family | source_table | event_time_column | available_at_prediction | allowed_in_propensity | proxy_risk | feature_version |
|---|---|---|---|---|---|---|---|
| fuel_spend_30d | transaction | transactions | date | True | True | False | feature_v1 |
| fuel_spend_90d_avg | transaction | transactions | date | True | True | False | feature_v1 |
| fuel_spend_12m_avg | transaction | transactions | date | True | True | False | feature_v1 |
| fuel_spend_trend | transaction | transactions | date | True | True | False | feature_v1 |
| fuel_txn_freq_90d | transaction | transactions | date | True | True | False | feature_v1 |
| fuel_spend_share_12m | transaction | transactions | date | True | True | False | feature_v1 |
| fuel_days_since_last | transaction | transactions | date | True | True | False | feature_v1 |
| electricity_spend_30d | transaction | transactions | date | True | True | False | feature_v1 |
| electricity_spend_90d_avg | transaction | transactions | date | True | True | False | feature_v1 |
| electricity_spend_12m_avg | transaction | transactions | date | True | True | False | feature_v1 |
| electricity_spend_trend | transaction | transactions | date | True | True | False | feature_v1 |
| electricity_txn_freq_90d | transaction | transactions | date | True | True | False | feature_v1 |
| electricity_spend_share_12m | transaction | transactions | date | True | True | False | feature_v1 |
| electricity_days_since_last | transaction | transactions | date | True | True | False | feature_v1 |
| gas_spend_30d | transaction | transactions | date | True | True | False | feature_v1 |
| gas_spend_90d_avg | transaction | transactions | date | True | True | False | feature_v1 |
| gas_spend_12m_avg | transaction | transactions | date | True | True | False | feature_v1 |
| gas_spend_trend | transaction | transactions | date | True | True | False | feature_v1 |
| gas_txn_freq_90d | transaction | transactions | date | True | True | False | feature_v1 |
| gas_spend_share_12m | transaction | transactions | date | True | True | False | feature_v1 |
| gas_days_since_last | transaction | transactions | date | True | True | False | feature_v1 |
| public_transport_spend_30d | transaction | transactions | date | True | True | False | feature_v1 |
| public_transport_spend_90d_avg | transaction | transactions | date | True | True | False | feature_v1 |
| public_transport_spend_12m_avg | transaction | transactions | date | True | True | False | feature_v1 |
| public_transport_spend_trend | transaction | transactions | date | True | True | False | feature_v1 |
| public_transport_txn_freq_90d | transaction | transactions | date | True | True | False | feature_v1 |
| public_transport_spend_share_12m | transaction | transactions | date | True | True | False | feature_v1 |
| public_transport_days_since_last | transaction | transactions | date | True | True | False | feature_v1 |
| home_improvement_spend_30d | transaction | transactions | date | True | True | False | feature_v1 |
| home_improvement_spend_90d_avg | transaction | transactions | date | True | True | False | feature_v1 |
| home_improvement_spend_12m_avg | transaction | transactions | date | True | True | False | feature_v1 |
| home_improvement_spend_trend | transaction | transactions | date | True | True | False | feature_v1 |
| home_improvement_txn_freq_90d | transaction | transactions | date | True | True | False | feature_v1 |
| home_improvement_spend_share_12m | transaction | transactions | date | True | True | False | feature_v1 |
| home_improvement_days_since_last | transaction | transactions | date | True | True | False | feature_v1 |
| automotive_spend_30d | transaction | transactions | date | True | True | False | feature_v1 |
| automotive_spend_90d_avg | transaction | transactions | date | True | True | False | feature_v1 |
| automotive_spend_12m_avg | transaction | transactions | date | True | True | False | feature_v1 |
| automotive_spend_trend | transaction | transactions | date | True | True | False | feature_v1 |
| automotive_txn_freq_90d | transaction | transactions | date | True | True | False | feature_v1 |
| automotive_spend_share_12m | transaction | transactions | date | True | True | False | feature_v1 |
| automotive_days_since_last | transaction | transactions | date | True | True | False | feature_v1 |
| utilities_spend_30d | transaction | transactions | date | True | True | False | feature_v1 |
| utilities_spend_90d_avg | transaction | transactions | date | True | True | False | feature_v1 |
| utilities_spend_12m_avg | transaction | transactions | date | True | True | False | feature_v1 |
| utilities_spend_trend | transaction | transactions | date | True | True | False | feature_v1 |
| utilities_txn_freq_90d | transaction | transactions | date | True | True | False | feature_v1 |
| utilities_spend_share_12m | transaction | transactions | date | True | True | False | feature_v1 |
| utilities_days_since_last | transaction | transactions | date | True | True | False | feature_v1 |
| txn_months_observed | transaction | transactions | date | True | True | False | feature_v1 |
| txn_count_12m | transaction | transactions | date | True | True | False | feature_v1 |
| total_spend_12m_avg | transaction | transactions | date | True | True | False | feature_v1 |
| tenure_months | banking_relationship | customers | customer_since | True | True | False | feature_v1 |
| has_vehicle | vehicle | vehicles | record_updated_at | True | True | False | feature_v1 |
| is_ice | vehicle | vehicles | record_updated_at | True | True | False | feature_v1 |
| is_ev | vehicle | vehicles | record_updated_at | True | True | False | feature_v1 |
| is_hybrid | vehicle | vehicles | record_updated_at | True | True | False | feature_v1 |
| vehicle_age_years | vehicle | vehicles | record_updated_at | True | True | False | feature_v1 |
| annual_mileage_km | vehicle | vehicles | record_updated_at | True | True | False | feature_v1 |
| mileage_is_estimated | vehicle | vehicles | record_updated_at | True | True | False | feature_v1 |
| vehicle_record_age_days | vehicle | vehicles | record_updated_at | True | True | False | feature_v1 |
| has_vehicle_finance | banking_relationship | financial_products | start_date | True | True | False | feature_v1 |
| home_owner | home | customers | record_updated_at | True | True | False | feature_v1 |
| has_mortgage | banking_relationship | financial_products | start_date | True | True | False | feature_v1 |
| mortgage_tenure_months | banking_relationship | financial_products | start_date | True | True | False | feature_v1 |
| has_existing_solar | home | customers | solar_installed_at | True | True | False | feature_v1 |
| has_investments | banking_relationship | financial_products | start_date | True | True | False | feature_v1 |
| heating_is_gas | home | customers | record_updated_at | True | True | False | feature_v1 |
| heating_is_electric | home | customers | record_updated_at | True | True | False | feature_v1 |
| property_is_house | home | customers | record_updated_at | True | True | False | feature_v1 |
| electricity_kwh_12m | energy | energy_usage | month | True | True | False | feature_v1 |
| gas_kwh_12m | energy | energy_usage | month | True | True | False | feature_v1 |
| electricity_trend | energy | energy_usage | month | True | True | False | feature_v1 |
| energy_months_present | energy | energy_usage | month | True | True | False | feature_v1 |
| is_paperless | digital | digital_usage | month | True | True | False | feature_v1 |
| paper_statements_3m | digital | digital_usage | month | True | True | False | feature_v1 |
| paper_statements_12m | digital | digital_usage | month | True | True | False | feature_v1 |
| digital_statement_ratio | digital | digital_usage | month | True | True | False | feature_v1 |
| digital_txn_3m_avg | digital | digital_usage | month | True | True | False | feature_v1 |
| app_logins_3m_avg | digital | digital_usage | month | True | True | False | feature_v1 |
| app_logins_trend | digital | digital_usage | month | True | True | False | feature_v1 |
| branch_visits_3m | digital | digital_usage | month | True | True | False | feature_v1 |
| digital_months_present | digital | digital_usage | month | True | True | False | feature_v1 |
| sustainability_preference | sustainability | customers | record_updated_at | True | True | False | feature_v1 |
| holds_ev_finance | banking_relationship | financial_products | start_date | True | False | False | feature_v1 |
| holds_green_home_loan | banking_relationship | financial_products | start_date | True | False | False | feature_v1 |
| holds_solar_finance | banking_relationship | financial_products | start_date | True | False | False | feature_v1 |
| region | context | customers | record_updated_at | True | False | True | feature_v1 |
| segment | context | customers | record_updated_at | True | False | False | feature_v1 |
| customer_since | context | customers | customer_since | True | False | False | feature_v1 |
| first_txn_date | data_quality | transactions | date | True | False | False | feature_v1 |
| last_txn_date | data_quality | transactions | date | True | False | False | feature_v1 |
| vehicle_record_updated_at | data_quality | vehicles | record_updated_at | True | False | False | feature_v1 |
| fuel_type | context | vehicles | record_updated_at | True | False | False | feature_v1 |
| heating_type | context | customers | record_updated_at | True | False | False | feature_v1 |
| property_type | context | customers | record_updated_at | True | False | False | feature_v1 |
| invalid_product_records | data_quality | financial_products | start_date | True | False | False | feature_v1 |
| missing_fields | data_quality | multiple | nan | True | False | False | feature_v1 |
| estimated_fields | data_quality | multiple | nan | True | False | False | feature_v1 |
| age_band | audit_only | customers | record_updated_at | True | False | True | feature_v1 |
| income_band | audit_only | customers | record_updated_at | True | False | True | feature_v1 |
| postcode_sector | audit_only | customers | record_updated_at | True | False | False | feature_v1 |

## Limitations

- Aggregate energy anchors constrain demand marginals; behavioural structure remains simulated.
- Synthetic relationships are designed, not observed; they cannot validate real-world performance.
