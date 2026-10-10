# Transaction categorisation evaluation

> Synthetic data only. These figures describe generalisation within the GreenPath generator's merchant catalogue. They do not establish categorisation accuracy on real bank transactions.

Categoriser `txn_cat_v1` · seed 43 · 300,000 of 874,498 transactions evaluated (seeded sample).

## Headline

| Model | Unseen macro F1 | Unseen weighted F1 | Known macro F1 | Known weighted F1 | Rule coverage (unseen) |
|---|---|---|---|---|---|
| Hybrid: brand rules and boundary rules, then TF-IDF + LR | 0.529 | 0.511 | 0.992 | 0.995 | 15.3% |
| TF-IDF + LR on normalised text (no rules) | 0.464 | 0.471 | 0.999 | 0.999 | 0.0% |
| Plain TF-IDF + LR on raw text (baseline) | 0.452 | 0.439 | 0.991 | 0.997 | 0.0% |

Hybrid minus plain baseline: macro F1 +0.077 on unseen merchants and +0.001 on known merchants.

## Split

- Method: GroupShuffleSplit on merchant_id; seeded row holdout of training merchants for known-merchant test.
- Merchants: 127 total, 88 in training, 39 held out as unseen.
- Rows: 172,675 fit, 43,169 known-merchant holdout, 84,156 unseen-merchant test.
- Merchants per category (train / unseen): FUEL 5/11, ELECTRICITY 6/2, GAS 7/0, PUBLIC_TRANSPORT 14/3, HOME_IMPROVEMENT 12/3, AUTOMOTIVE 9/7, UTILITIES 10/4, OTHER 25/9.

## Per-category results (hybrid)

| Category | Unseen precision | Unseen recall | Unseen F1 | Unseen support | Known precision | Known recall | Known F1 | Known support |
|---|---|---|---|---|---|---|---|---|
| FUEL | 0.978 | 0.135 | 0.236 | 17,501 | 1.000 | 0.987 | 0.994 | 957 |
| ELECTRICITY | 1.000 | 1.000 | 1.000 | 2,173 | 1.000 | 0.937 | 0.968 | 2,810 |
| GAS | n/a | n/a | n/a | 0 | 1.000 | 1.000 | 1.000 | 2,289 |
| PUBLIC_TRANSPORT | 0.705 | 0.741 | 0.722 | 16,175 | 1.000 | 0.998 | 0.999 | 5,518 |
| HOME_IMPROVEMENT | 0.000 | 0.000 | 0.000 | 2,795 | 1.000 | 1.000 | 1.000 | 1,988 |
| AUTOMOTIVE | 0.932 | 0.196 | 0.324 | 11,254 | 0.996 | 1.000 | 0.998 | 2,730 |
| UTILITIES | 0.782 | 1.000 | 0.878 | 8,265 | 0.963 | 1.000 | 0.981 | 4,519 |
| OTHER | 0.416 | 0.780 | 0.542 | 25,993 | 0.999 | 1.000 | 1.000 | 22,358 |

## Confusion matrix (hybrid, unseen merchants)

Rows are the true category and columns the predicted category. Codes: FUEL = FUEL, ELEC = ELECTRICITY, GAS = GAS, PT = PUBLIC_TRANSPORT, HOME = HOME_IMPROVEMENT, AUTO = AUTOMOTIVE, UTIL = UTILITIES, OTHER = OTHER.

| True \ predicted | FUEL | ELEC | GAS | PT | HOME | AUTO | UTIL | OTHER |
|---|---|---|---|---|---|---|---|---|
| FUEL | 2,354 | 0 | 0 | 152 | 454 | 162 | 0 | 14,379 |
| ELEC | 0 | 2,173 | 0 | 0 | 0 | 0 | 0 | 0 |
| GAS | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| PT | 0 | 0 | 0 | 11,980 | 0 | 0 | 0 | 4,195 |
| HOME | 0 | 0 | 0 | 1,684 | 0 | 0 | 0 | 1,111 |
| AUTO | 53 | 0 | 0 | 148 | 19 | 2,205 | 27 | 8,802 |
| UTIL | 0 | 0 | 0 | 0 | 0 | 0 | 8,265 | 0 |
| OTHER | 0 | 0 | 0 | 3,027 | 412 | 0 | 2,277 | 20,277 |

## Deterministic rules

- Brand dictionary: 844 leading-token keys (1 to 3 tokens, longest match wins). A key is used only when it has at least 20 training rows and at least 98% share one category.
- Boundary rules run before the dictionary, in this order:
  - `fuel_marker` -> FUEL: PFS, PETROL or UNLEADED token anywhere in the text (e.g. 'TESCO PFS', 'SHELL PETROL').
  - `automotive_service` -> AUTOMOTIVE: TYRES, TYRE, MOT, AUTOCENTRE, AUTOCARE, or CAR SERVICE / CAR SERVICING / CAR WASH / CAR REPAIR / AUTO CENTRE phrases (e.g. 'KWIK FIT TYRES').
  - `dual_fuel` -> UTILITIES: Electricity and gas markers both present (dual-fuel supplier).
  - `electricity_only` -> ELECTRICITY: ELECTRICITY / ELECTRIC / ELEC with no gas marker and no non-supply word (EV charging, electric bikes, appliances).
  - `gas_only` -> GAS: GAS with no electricity marker (e.g. 'CADENT GAS').
  - `bundled_utility` -> UTILITIES: ENERGY / UTILITIES / UTILITY / WATER, or the phrase DUAL FUEL, with no fuel-specific evidence (e.g. 'OCTOPUS ENERGY').

| Rule accuracy and coverage | Unseen merchants | Known merchants |
|---|---|---|
| Rule coverage | 15.3% | 96.9% |
| Rule accuracy | 100.0% | 99.6% |
| Model accuracy on non-rule rows | 48.2% | 98.3% |

## Limitations

- Training labels come from the generator's merchant catalogue, so the classifier learns that catalogue's naming conventions.
- Single-token brand keys are the main collision risk: a token that is pure in training can start an unseen merchant name. The rule-accuracy row above measures this.
- Macro and weighted F1 average only over categories present in the true or predicted labels of the split.
