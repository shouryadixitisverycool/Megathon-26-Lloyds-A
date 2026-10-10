# Transaction categorisation evaluation

> Synthetic data only. These figures describe generalisation within the GreenPath generator's merchant catalogue. They do not establish categorisation accuracy on real bank transactions.

Categoriser `txn_cat_v1` · seed 43 · 300,000 of 877,757 transactions evaluated (seeded sample).

## Headline

| Model | Unseen macro F1 | Unseen weighted F1 | Known macro F1 | Known weighted F1 | Rule coverage (unseen) |
|---|---|---|---|---|---|
| Hybrid: brand rules and boundary rules, then TF-IDF + LR | 0.543 | 0.524 | 0.998 | 0.999 | 14.2% |
| TF-IDF + LR on normalised text (no rules) | 0.511 | 0.494 | 0.998 | 0.999 | 0.0% |
| Plain TF-IDF + LR on raw text (baseline) | 0.453 | 0.440 | 0.992 | 0.997 | 0.0% |

Hybrid minus plain baseline: macro F1 +0.089 on unseen merchants and +0.006 on known merchants.

## Split

- Method: GroupShuffleSplit on merchant_id; seeded row holdout of training merchants for known-merchant test.
- Merchants: 127 total, 88 in training, 39 held out as unseen.
- Rows: 172,023 fit, 43,006 known-merchant holdout, 84,971 unseen-merchant test.
- Merchants per category (train / unseen): FUEL 5/11, ELECTRICITY 5/2, GAS 7/0, PUBLIC_TRANSPORT 14/3, HOME_IMPROVEMENT 12/3, AUTOMOTIVE 9/7, UTILITIES 11/4, OTHER 25/9.

## Per-category results (hybrid)

| Category | Unseen precision | Unseen recall | Unseen F1 | Unseen support | Known precision | Known recall | Known F1 | Known support |
|---|---|---|---|---|---|---|---|---|
| FUEL | 0.974 | 0.133 | 0.235 | 17,436 | 1.000 | 0.979 | 0.989 | 951 |
| ELECTRICITY | 1.000 | 1.000 | 1.000 | 1,733 | 1.000 | 1.000 | 1.000 | 2,852 |
| GAS | n/a | n/a | n/a | 0 | 1.000 | 1.000 | 1.000 | 2,199 |
| PUBLIC_TRANSPORT | 0.705 | 0.792 | 0.746 | 16,410 | 1.000 | 0.999 | 1.000 | 5,568 |
| HOME_IMPROVEMENT | 0.011 | 0.003 | 0.005 | 2,938 | 1.000 | 1.000 | 1.000 | 1,931 |
| AUTOMOTIVE | 0.898 | 0.200 | 0.327 | 11,436 | 0.999 | 1.000 | 0.999 | 2,754 |
| UTILITIES | 0.841 | 1.000 | 0.914 | 7,873 | 1.000 | 1.000 | 1.000 | 4,588 |
| OTHER | 0.442 | 0.808 | 0.572 | 27,145 | 0.999 | 1.000 | 1.000 | 22,163 |

## Confusion matrix (hybrid, unseen merchants)

Rows are the true category and columns the predicted category. Codes: FUEL = FUEL, ELEC = ELECTRICITY, GAS = GAS, PT = PUBLIC_TRANSPORT, HOME = HOME_IMPROVEMENT, AUTO = AUTOMOTIVE, UTIL = UTILITIES, OTHER = OTHER.

| True \ predicted | FUEL | ELEC | GAS | PT | HOME | AUTO | UTIL | OTHER |
|---|---|---|---|---|---|---|---|---|
| FUEL | 2,327 | 0 | 0 | 168 | 384 | 260 | 0 | 14,297 |
| ELEC | 0 | 1,733 | 0 | 0 | 0 | 0 | 0 | 0 |
| GAS | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| PT | 0 | 0 | 0 | 12,989 | 0 | 0 | 0 | 3,421 |
| HOME | 0 | 0 | 0 | 1,855 | 10 | 0 | 0 | 1,073 |
| AUTO | 63 | 0 | 0 | 171 | 21 | 2,286 | 0 | 8,895 |
| UTIL | 0 | 0 | 0 | 0 | 0 | 0 | 7,873 | 0 |
| OTHER | 0 | 0 | 0 | 3,244 | 467 | 0 | 1,488 | 21,946 |

## Deterministic rules

- Brand dictionary: 874 leading-token keys (1 to 3 tokens, longest match wins). A key is used only when it has at least 20 training rows and at least 98% share one category.
- Boundary rules run before the dictionary, in this order:
  - `ev_charging` -> AUTOMOTIVE: EV CHARGING / EV CHARGE / EV CHARGER is automotive activity, not liquid fuel or household supply.
  - `fuel_marker` -> FUEL: PFS, PETROL or UNLEADED token anywhere in the text (e.g. 'TESCO PFS', 'SHELL PETROL').
  - `automotive_service` -> AUTOMOTIVE: TYRES, TYRE, MOT, AUTOCENTRE, AUTOCARE, or CAR SERVICE / CAR SERVICING / CAR WASH / CAR REPAIR / AUTO CENTRE phrases (e.g. 'KWIK FIT TYRES').
  - `dual_fuel` -> UTILITIES: Electricity and gas markers both present (dual-fuel supplier).
  - `electricity_only` -> ELECTRICITY: ELECTRICITY / ELECTRIC / ELEC with no gas marker and no non-supply word (EV charging, electric bikes, appliances).
  - `gas_only` -> GAS: GAS with no electricity marker (e.g. 'CADENT GAS').
  - `bundled_utility` -> UTILITIES: ENERGY / UTILITIES / UTILITY / WATER, or the phrase DUAL FUEL, with no fuel-specific evidence (e.g. 'OCTOPUS ENERGY').

| Rule accuracy and coverage | Unseen merchants | Known merchants |
|---|---|---|
| Rule coverage | 14.2% | 97.0% |
| Rule accuracy | 100.0% | 100.0% |
| Model accuracy on non-rule rows | 50.9% | 98.1% |

## Limitations

- Training labels come from the generator's merchant catalogue, so the classifier learns that catalogue's naming conventions.
- Single-token brand keys are the main collision risk: a token that is pure in training can start an unseen merchant name. The rule-accuracy row above measures this.
- Macro and weighted F1 average only over categories present in the true or predicted labels of the split.
