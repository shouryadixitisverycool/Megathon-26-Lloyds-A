# Agent A design — data, ML and reliability

Repository: `greenr-agent-a/` (Agent A's own repository; Agent B works elsewhere).
Python 3.12, `uv` (lock: `uv.lock`). Run everything with `uv run ...`. pandas is **3.x** (copy-on-write, default string dtype): never rely on chained assignment.

Canonical, already written — **do not edit without the orchestrator**:
`src/greenr/contracts/*`, `src/greenr/ports.py`, `src/greenr/config.py`, `src/greenr/pipelines/schemas.py`.

## Timeline (config.py)
Feature cutoff 2026-06-30; label = adoption in (cutoff, cutoff+90d] → window end 2026-09-28; prediction timestamp 2026-10-10.
Simulated history 2025-01-01 → 2026-09-28. Trend cutoffs: month-ends Jan–Jun 2026. Temporal-holdout cutoff 2026-03-31.
Seeds: data 42, split 43, model 44, perturbation 45.

## Raw data (pipelines/schemas.py)
Generator writes parquet files `data/synthetic/<table>.parquet` (one per table in `ALL_TABLES`) + `generator_config.json`.
Truth tables (`transaction_truth`, `merchants`, `customer_outcomes`) are evaluation-only and must never be read by the feature pipeline.
Dates are pandas `datetime64[ns]` columns.

## Module ownership (one owner per file; tests in matching `tests/<area>/`)
| Module | Owner task |
|---|---|
| `data_generation/{config,merchants,generator,perturbation,personas}.py` | T1 |
| `models/transaction_classifier.py`, `evaluation/transaction.py`, `pipelines/split.py`, `pipelines/leakage_checks.py` | T2 |
| `pipelines/customer360.py`, `pipelines/feature_registry.py`, `pipelines/snapshot_provider.py` | T3 |
| `models/propensity/*` (features, heuristics, training, calibration, reason codes, provider) | T4 |
| `trust/{quality,conflicts,ood,provider}.py` | T5 |
| `confidence/{meta_model,validation}.py` | T6 |
| `evaluation/metrics.py`, `contracts/fixtures/*`, `contracts/schemas/*`, `contracts/fixtures.py`, `tests/contracts/*` | T7 |
| `pipelines/run.py`, `Makefile`, docs, reports | orchestrator |

## Categorised transactions (T2 → T3 interface)
`models/transaction_classifier.py` exposes:
```python
def normalise_description(text: str) -> str
class TransactionCategoriser:          # rules first, TF-IDF + LogisticRegression for the rest
    version: str                       # "txn_cat_v1"
    def fit(self, descriptions: Sequence[str], categories: Sequence[str]) -> "TransactionCategoriser"
    def predict(self, descriptions: Sequence[str]) -> pd.DataFrame  # columns: category, category_confidence, method ("RULE"|"MODEL")
    def save(self, path) / @classmethod load(cls, path)
```
Categories are `TransactionCategory` values. Exactly one category per transaction. Predict works on unique normalised strings (fast on ~2M rows).
The pipeline adds columns `category`, `category_confidence`, `category_method` to the transactions frame → `data/processed/transactions_categorised.parquet`.

## Customer 360 feature view (T3 produces; T4/T5/T6 consume)
`pipelines/customer360.py`:
```python
def build_customer360(tables: dict[str, pd.DataFrame], categorised_txns: pd.DataFrame, cutoff: date) -> pd.DataFrame
```
One row per customer existing at cutoff (`customer_since <= cutoff`), index `customer_id`. Uses only events with event time <= cutoff
(energy/digital rows count only if `month` end <= cutoff; vehicle = latest record with `record_updated_at <= cutoff`;
products active as of cutoff = `start_date <= cutoff and (end_date is null or end_date > cutoff)` and status != INVALID).
Missing values are NaN (never silently 0) where data is absent rather than zero.

**Approved propensity feature columns** (all numeric float; booleans as 0/1/NaN):
- Transaction, for cat in `fuel, electricity, gas, public_transport, home_improvement, automotive, utilities`:
  `{cat}_spend_30d`, `{cat}_spend_90d_avg` (monthly avg over 90d), `{cat}_spend_12m_avg` (monthly avg),
  `{cat}_spend_trend` (90d_avg / 12m_avg − 1; NaN if 12m_avg == 0), `{cat}_txn_freq_90d`, `{cat}_spend_share_12m`,
  `{cat}_days_since_last` (NaN if never).
- `txn_months_observed`, `txn_count_12m`, `total_spend_12m_avg`, `tenure_months`
- Vehicle: `has_vehicle`, `is_ice`, `is_ev`, `is_hybrid`, `vehicle_age_years`, `annual_mileage_km`, `mileage_is_estimated`, `vehicle_record_age_days`, `has_vehicle_finance`
- Home/products: `home_owner`, `has_mortgage`, `mortgage_tenure_months`, `has_existing_solar`, `has_investments`, `heating_is_gas`, `heating_is_electric`, `property_is_house`
- Energy: `electricity_kwh_12m`, `gas_kwh_12m`, `electricity_trend`, `energy_months_present`
- Digital: `is_paperless`, `paper_statements_3m`, `paper_statements_12m`, `digital_statement_ratio`, `digital_txn_3m_avg`, `app_logins_3m_avg`, `app_logins_trend`, `branch_visits_3m`, `digital_months_present`
- `sustainability_preference` (1–5 or NaN)
- Green holdings as of cutoff (population filters, **not** model features for their own product): `holds_ev_finance`, `holds_green_home_loan`, `holds_solar_finance`

**Non-feature context columns** (in the frame, never in `features`): `region`, `segment`, `customer_since`, `first_txn_date`, `last_txn_date`,
`vehicle_record_updated_at`, `fuel_type`, `heating_type`, `property_type`, `invalid_product_records`, `missing_fields` (list), `estimated_fields` (list).
**Audit-only columns** are NOT in the frame: `age_band`, `income_band`, `postcode_sector` — join from `customers` for fairness audits only.

`pipelines/feature_registry.py`: `FEATURE_REGISTRY: dict[str, FeatureSpec]` with source table, family, event-time column,
`available_at_prediction`, `allowed_in_propensity`; plus `PROPENSITY_FEATURES`, `AUDIT_ONLY_COLUMNS`, `PROXY_FEATURES` (income_band, region, age_band).

`pipelines/snapshot_provider.py`: `Customer360SnapshotProvider` implements `ports.CustomerSnapshotProvider` from a Customer 360 frame
(`row_to_snapshot(row, cutoff) -> CustomerSnapshot`; `features` = the approved feature columns with NaN → None).

## Labels and splits (T2)
`pipelines/split.py`:
```python
def make_labels(outcomes: pd.DataFrame, customer_ids, cutoff: date, window_days=90) -> pd.DataFrame  # index customer_id, one 0/1 column per Product value
def adopted_before(outcomes, customer_ids, cutoff) -> pd.DataFrame  # bool per Product: adoption_date <= cutoff
def split_customers(customer_ids, seed=SEED_SPLIT, fractions=(0.7, 0.15, 0.15), force_test=DEMO_PERSONA_IDS) -> pd.Series  # values "train"|"validation"|"test"|"demo"
```
Demo personas get split `"demo"` (never trained on). Write `data/processed/split_manifest.csv` + its sha256.

`pipelines/leakage_checks.py` raises `LeakageError` on: customer overlap across splits; any source event time > cutoff in the frames
used for features; label/target-like column names in a feature list (`adopt|label|target|take_up|outcome`); post-adoption product flags
for the product being modelled (`holds_*` for that product) in that product's features; audit-only/proxy columns in default features.

## Propensity (T4)
Model population per product = customers not already holding/adopted it at cutoff (`PopulationExclusion`): EV → `holds_ev_finance`;
Green Home → `holds_green_home_loan`; Solar → `has_existing_solar` or `holds_solar_finance`; Paperless → `is_paperless`.
Per product: heuristic baseline, logistic regression (median impute + missing indicators + scaling), HistGradientBoosting main model.
Calibration (isotonic and Platt; choose by validation Brier) fit on **validation only**. Model selection by validation, never test.
Artifacts in `data/artifacts/models/<product>/`. Provider implements `ports.PropensityProvider`.

## Trust (T5), Confidence (T6) — see task prompts. Trust ≠ confidence; no double counting of completeness.

## Metrics (T7) — `evaluation/metrics.py`
`roc_auc, pr_auc, brier, ece(y, p, n_bins=10), calibration_curve(y, p, n_bins=10) -> DataFrame, precision_at_k(y, s, frac), recall_at_k(y, s, frac), lift_at_k(y, s, frac=0.1), confusion_at_threshold(y, p, t) -> dict, summary(y, p) -> dict`
All accept array-likes and handle a single-class `y` by returning NaN for undefined ranking metrics.
