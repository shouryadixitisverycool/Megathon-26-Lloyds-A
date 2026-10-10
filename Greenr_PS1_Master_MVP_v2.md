# Greenr Intelligence — PS1 Master MVP Specification

**Problem Statement:** Lloyds — Green Customer Insights Platform  
**Document purpose:** Build specification, scope-control document, evaluation plan, demo plan, and submission checklist  
**Status:** MVP v2 — revised to preserve the complete original concept while explicitly addressing scope, synthetic-data circularity, confidence validation, carbon-methodology rigor, LLM safety, trend analytics, proxy-risk features, and reproducibility.

---

## 0. Executive summary

Greenr Intelligence is an explainable green-finance decision platform that identifies relevant sustainability opportunities for each customer, estimates the potential impact using auditable deterministic calculations, explains why the opportunity exists, knows when *not* to recommend, and helps Lloyds decide the next best action across both individual customers and the wider portfolio.

The platform must answer four questions reliably:

1. **Who should we engage?**
2. **Why this customer and this product?**
3. **What sustainability impact could plausibly result, under documented assumptions?**
4. **What should the customer or bank do next?**

The core operating principle is non-negotiable:

- **ML models predict propensity.**
- **A deterministic rules-based sustainability/carbon engine computes impact.**
- **The LLM explains structured outputs; it never predicts propensity, calculates impact, or determines financial eligibility.**
- **Financial eligibility remains outside Greenr and follows Lloyds' authorised product-specific processes.**

The project deliberately optimises for **depth before breadth**. Features are tiered into Must / Should / Could, and a feature may not be demoed unless it meets its Definition of Done.

---

# 1. Scope control and delivery tiers

## 1.1 Why scope control is part of the product strategy

The platform has a large design surface. A shallow implementation across dozens of features is worse than a smaller, fully validated product. Every feature therefore belongs to one of three tiers.

### MUST — required for a submission we consider complete

- Four required opportunities:
  - EV Finance
  - Green Home
  - Solar Finance
  - Paperless Banking
- Customer 360
- Transaction categorisation
- Product-specific propensity models
- Simple heuristic baseline **and** statistical baseline
- Probability calibration
- Structured recommendation object
- Reason-code framework
- Data-quality / Trust layer
- Validated confidence method
- Guardrails, rule-outs, conflicts and abstention
- Deterministic sustainability/carbon engine
- Named methodology, system boundaries, factors, factor versions and assumptions
- Impact Passport
- Grounded LLM explanation layer
- Programmatic LLM grounding checks
- Deterministic template fallback
- LLM evaluation set including adversarial tests
- Customer-facing recommendation experience
- Business / portfolio dashboard
- FR6 regional, segment **and time-trend** insights
- Evaluation report
- Responsible AI note
- Test-set predictions
- Reproducible pipeline with fixed seeds and one-command execution
- Unit tests for guardrails and impact formulas
- Full source and model version traceability

### SHOULD — build after all MUST items pass

- What-if sustainability simulator
- Counterfactual / sensitivity explanations
- Relationship Manager workspace
- Propensity-vs-impact opportunity matrix
- Expected Sustainability Impact planning metric
- Customer memory
- Dynamic customer journey / recommendation lifecycle
- Portfolio scenario planner
- Recommendation evidence graph
- Model governance / Responsible AI console
- Drift and confidence diagnostics

### COULD — only if MUST and SHOULD are stable

- Multi-objective campaign ranking
- Campaign optimiser with contact-fatigue constraints
- Next Best Green Action / channel optimisation
- Optional Green Investments opportunity
- Optional Green Loans opportunity
- Interactive fairness console
- Advanced counterfactual search
- Advanced evidence graph
- More sophisticated portfolio optimisation

## 1.2 Scope freeze rule

A COULD feature cannot consume engineering time if any MUST feature lacks:

- tests,
- documented assumptions,
- held-out evaluation,
- reproducibility,
- a fallback path,
- or a working demo state.

No half-working feature appears in the final demo.

---

# 2. Original problem coverage

Greenr must support the complete required brief and preserve the optional extensions.

## 2.1 Required product opportunities

| Opportunity | Status | Example signals | Primary output |
|---|---|---|---|
| EV Finance | Required | recurring fuel spend, ICE vehicle, mileage, existing vehicle finance | EV Finance opportunity |
| Green Home | Required | mortgage/home ownership, high utility use, home-improvement activity | Green Home opportunity |
| Solar Finance | Required | home ownership, high electricity use, no existing solar | Solar Finance opportunity |
| Paperless Banking | Required | paper statements, high digital engagement | Paperless transition opportunity |
| Green Investments | Optional | investments, sustainability preference | green-investment opportunity |
| Green Loans | Optional | existing borrowing, suitable green use case | green-purpose lending opportunity |

## 2.2 Functional requirements traceability

| Requirement | Greenr implementation |
|---|---|
| FR1 Customer 360 | governed customer feature view built from all source tables |
| FR2 Transaction categorisation | exactly one mutually exclusive sustainability category per transaction |
| FR3 Opportunity detection | propensity, confidence and reason codes for each required product |
| FR4 Sustainability impact | deterministic documented impact engine with named factors and assumptions |
| FR5 Customer insight | grounded customer-friendly explanation from structured output only |
| FR6 Business insights | portfolio, segment, regional, conversion, impact and monthly trend views |
| FR7 Explainability | evidence, reason codes, confidence, timestamps, exclusions and audit metadata |

## 2.3 Required submission outputs

Greenr must ship:

A. Working prototype  
B. Source code + run instructions  
C. Trained models + inference code  
D. Preprocessing pipeline  
E. LLM implementation + prompts + evaluation  
F. Architecture diagram  
G. Evaluation report  
H. Responsible AI note  
I. Held-out / test predictions

Additional voluntary artefacts:

- `DATA_CARD.md`
- `MODEL_CARD_EV.md`
- `MODEL_CARD_GREEN_HOME.md`
- `MODEL_CARD_SOLAR.md`
- `MODEL_CARD_PAPERLESS.md`
- `CARBON_METHODS.md`
- `LLM_EVAL.md`
- `SCENARIO_TESTS.md`
- `LEAKAGE_AUDIT.md`
- `REPRODUCIBILITY.md`

---

# 3. Product surfaces

Greenr has three user-facing surfaces.

## 3.1 Customer Green Hub

Primary question:

> What sustainable actions are relevant to me, why am I seeing them, and what could the estimated impact be?

The customer sees:

- opportunity name,
- relevance,
- simple reason wording,
- estimated impact if available,
- method indicator,
- data timestamp,
- clear action,
- explicit disclaimer that relevance/propensity is not financial eligibility.

The customer does **not** see raw SHAP plots, calibration diagnostics, or internal model controls.

## 3.2 Relationship Manager Workspace

Primary question:

> What should I discuss with this customer, and why?

The RM sees:

- all customer opportunities,
- propensity,
- confidence,
- Trust / data-quality status,
- reason codes and evidence,
- exclusions,
- impact estimate and Impact Passport,
- scenario/sensitivity tools,
- recommendation history,
- human-review actions.

## 3.3 Green Portfolio Command Centre

Primary question:

> Where are the largest commercial and sustainability opportunities across the portfolio?

It includes:

- customers analysed,
- opportunities by product,
- high-confidence opportunities,
- opportunity funnel,
- propensity vs impact matrix,
- regional and segment views,
- **month-over-month trend views**,
- conversion opportunity,
- estimated portfolio impact,
- scenario planning,
- optional campaign optimisation.

---

# 4. Governed end-to-end architecture

```text
Raw / Public / Synthetic Data
            ↓
Schema Validation + Data Quality Checks
            ↓
Transaction Normalisation / Categorisation
            ↓
Customer 360 + Feature Store
            ↓
Product-Specific Propensity Models
            ↓
Probability Calibration
            ↓
Confidence Meta-Model / Reliability Layer
            ↓
Trust Score + OOD / Data Adequacy
            ↓
Recommendation Guardrails / Conflicts / Abstention
            ↓
Deterministic Sustainability Engine
            ↓
Opportunity Priority Layer
            ↓
Reason / Evidence Engine
            ↓
Structured Recommendation Object
            ↓
LLM Explanation Layer
        ↙           ↘
Grounding checks   Template fallback
            ↓
Customer / RM / Portfolio Experiences
            ↓
Feedback / Outcome / Memory
```

### Architecture responsibility rule

| Component | Allowed to do | Forbidden to do |
|---|---|---|
| ML propensity model | estimate take-up probability | determine eligibility |
| confidence layer | estimate reliability of model output | change propensity |
| trust layer | assess data adequacy | claim product eligibility |
| guardrails | suppress irrelevant/contradicted recommendations | alter model score invisibly |
| carbon engine | deterministic calculations | behavioural prediction |
| LLM | explain structured outputs | invent numbers, predict, calculate, approve |
| eligibility process | institution-authorised decision | be replaced by Greenr |

---

# 5. Canonical structured recommendation object

Every downstream surface consumes a single controlled object.

```json
{
  "customer_id": "C10001",
  "opportunity_id": "EV_FINANCE",
  "product_id": "GP01",

  "propensity": 0.84,
  "propensity_model_version": "ev_propensity_v3.1",
  "calibration_version": "ev_iso_v1",

  "confidence": 0.87,
  "confidence_method_version": "conf_meta_v2",
  "confidence_bucket": "HIGH",

  "trust": {
    "score": 0.91,
    "completeness": 0.96,
    "freshness": 0.89,
    "cross_source_consistency": 0.92,
    "critical_fields_present": true,
    "ood_score": 0.08
  },

  "recommendation_status": "RECOMMEND",
  "guardrail_codes": [],
  "conflict_codes": [],

  "priority": {
    "rank": 1,
    "score": 0.81,
    "version": "priority_v2"
  },

  "reason_codes": [
    "HIGH_FUEL_SPEND",
    "HIGH_ANNUAL_MILEAGE",
    "ICE_VEHICLE_OWNER"
  ],

  "evidence": {
    "monthly_fuel_spend": 310,
    "annual_mileage": 15200,
    "vehicle_fuel_type": "petrol"
  },

  "impact": {
    "status": "AVAILABLE",
    "metric": "kg_co2e_per_year",
    "baseline": 2850,
    "scenario": 1180,
    "estimated_reduction": 1670,
    "methodology_id": "EV_OPERATIONAL_WTW_V1",
    "factor_source": "UK Government GHG Conversion Factors",
    "factor_vintage": "PINNED_AT_BUILD",
    "boundary": "operational well-to-wheel where matched factors are available; manufacturing excluded",
    "grid_scenario": "current-year factor for headline annual estimate",
    "assumptions": ["..."],
    "calculation_timestamp": "2026-10-10"
  },

  "eligibility": {
    "status": "NOT_ASSESSED",
    "message": "Propensity does not establish financial eligibility."
  },

  "data_cutoff": "2026-06-30",
  "outcome_window_end": "2026-09-28",
  "prediction_timestamp": "2026-10-10",
  "feature_version": "feature_v5",
  "carbon_engine_version": "carbon_v2",
  "prompt_version": "prompt_v4",
  "llm_model_version": "PINNED_AT_BUILD"
}
```

### Date coherence rule

The project uses one coherent timeline:

- **Feature/data cutoff:** 2026-06-30
- **Outcome window:** 90 days, ending 2026-09-28
- **Evaluation/demo prediction timestamp:** 2026-10-10

Historical experiments may use earlier cutoffs, but every displayed recommendation must show the exact cutoff and prediction timestamp that produced it.

---

# 6. Data strategy

## 6.1 Hybrid data principle

Use a mixture of:

1. synthetic customer / banking relationship data,
2. suitable public behavioural or energy datasets,
3. documented emissions factors,
4. generated labels only where no realistic public label exists.

The data card must clearly distinguish:

- observed public data,
- transformed public data,
- synthetic features,
- synthetic labels,
- simulator-derived targets.

## 6.2 Public-data anchors

Use public data to reduce the circularity of a purely synthetic system.

Candidate anchors already suggested by the problem statement:

- London Smart Meter Energy Consumption — energy-use profile features
- UCI Online Retail II — transaction-like behavioural and customer-level feature engineering patterns

Where a public dataset is not directly representative of banking transactions, it is used only as a **behavioural structure anchor**, not misrepresented as real bank data.

## 6.3 Core entities

```text
customers
transactions
financial_products
vehicles
energy_usage
digital_usage
green_product_catalogue
emission_factors
customer_outcomes
recommendations
customer_memory
model_predictions
data_quality_events
```

## 6.4 Suggested fields

### customers

- `customer_id`
- `age_band`
- `income_band`
- `postcode_sector` or coarse region
- `home_owner`
- `digital_usage`
- `sustainability_preference`

### transactions

- `transaction_id`
- `customer_id`
- `date`
- `merchant_description`
- `amount`
- `debit_credit`
- `sustainability_category`

### financial products

- `customer_id`
- `product`
- `start_date`
- `balance`
- `status`

### vehicles

- `customer_id`
- `vehicle_type`
- `fuel_type`
- `vehicle_age`
- `annual_mileage`
- `record_updated_at`

### energy usage

- `customer_id`
- `month`
- `electricity_kwh`
- `gas_kwh`
- `source_quality`

### digital usage

- `customer_id`
- `month`
- `digital_statements`
- `paper_statements`
- `digital_transactions`
- `branch_visits`

### green product catalogue

- `product_id`
- `product`
- `category`
- `intended_use_case`
- `eligibility_reference`
- `sustainability_metric`

### emissions factors

- `activity`
- `fuel_or_energy_type`
- `unit`
- `kg_co2e_per_unit`
- `source`
- `source_url`
- `source_version`
- `publication_date`
- `boundary`
- `valid_from`

---

# 7. Customer 360

Customer 360 is a governed feature view, not merely a join.

## 7.1 Feature families

| Family | Example features |
|---|---|
| banking relationship | mortgage status, vehicle loan, tenure, investments |
| transaction behaviour | monthly fuel/electricity/gas/public transport/home-improvement spend |
| vehicle | fuel type, vehicle age, mileage, finance status |
| home | homeowner, mortgage, energy indicators |
| digital behaviour | statement mode, digital transactions, branch visits |
| sustainability | stated preference, prior green actions |
| temporal behaviour | 30/90/365-day averages, trends, recency |
| data-quality metadata | missingness, staleness, conflicts |
| outcome history | prior engagement, adoption, declines |

## 7.2 Temporal feature examples

Instead of:

```text
fuel_spend = 250
```

derive:

```text
fuel_spend_30d
fuel_spend_90d_avg
fuel_spend_12m_avg
fuel_spend_trend
fuel_txn_frequency_90d
fuel_spend_share_12m
days_since_last_fuel_txn
```

## 7.3 Prediction-time validity

Every feature must be labelled with:

- source,
- event date,
- availability date,
- whether it is available at prediction time.

No post-cutoff data may leak into features.

---

# 8. Synthetic data generation and circularity controls

Synthetic-label circularity is the single largest ML credibility risk. Greenr therefore treats synthetic-data validation as a first-class deliverable.

## 8.1 Prohibited generator design

Do **not** create labels using direct deterministic rules such as:

```python
if fuel_spend > 300:
    ev_takeup = 1
```

and then train a model on the same feature.

## 8.2 Latent stochastic generator

For each opportunity, generate outcomes through multiple correlated latent drivers plus noise.

Example conceptual EV generator:

```text
latent_EV_interest =
    β1 * fuel_spend_signal
  + β2 * vehicle_age_signal
  + β3 * mileage_signal
  + β4 * sustainability_preference
  + β5 * financing_relationship
  + β6 * latent_customer_preference
  + β7 * relevant_interactions
  + random_noise
```

Then:

```text
p = sigmoid(latent_EV_interest)
take_up ~ Bernoulli(p)
```

## 8.3 Generator perturbation / domain-shift test

Train and test under different generator conditions.

Example:

- Train generator:
  - base noise = 1.0
  - coefficient set A
  - missingness pattern A
- Stress-test generator:
  - base noise = 1.35
  - coefficient set B
  - different interaction strengths
  - different missingness pattern B
  - merchant distribution shift

Report performance degradation.

This is mandatory in the evaluation report.

## 8.4 Generator-shift metrics

For each propensity model report:

- ROC-AUC in-distribution
- ROC-AUC perturbed-generator
- PR-AUC in-distribution
- PR-AUC perturbed-generator
- Brier score shift
- calibration shift
- Lift@10% shift

The goal is not to preserve perfect performance. The goal is to show honest behaviour under distribution change.

## 8.5 Leakage audit

Create `LEAKAGE_AUDIT.md` covering:

- feature provenance,
- cutoff timing,
- customer split integrity,
- label construction,
- latent-variable leakage,
- target-derived feature checks,
- merchant duplication,
- future-information leakage.

Automated tests should fail if:

- the same `customer_id` appears across train and test,
- any feature event time is after cutoff,
- target labels appear as features,
- a post-adoption product flag is included in pre-adoption features.

---

# 9. Time-based train / validation / test design

## 9.1 Canonical design

```text
Feature window                     Outcome window
2025-07-01 ───── 2026-06-30 | 2026-07-01 ───── 2026-09-28
                               ↑
                            cutoff
```

Take-up is defined as product adoption within **90 days after cutoff**.

## 9.2 Split policy

Split by **customer**, not rows.

Suggested:

- Train: 70%
- Validation: 15%
- Test: 15%

No customer appears in more than one split.

## 9.3 Optional stronger test

Use a second time cutoff to create a temporal holdout, if data volume allows.

---

# 10. Transaction categorisation

Each transaction receives exactly one category:

- Fuel
- Electricity
- Gas
- Public Transport
- Home Improvement
- Automotive
- Utilities
- Other

## 10.1 Hybrid classifier

```text
raw merchant text
      ↓
normalise / strip noise
      ↓
high-confidence deterministic merchant dictionary
      ↓
ML classifier for unresolved records
      ↓
category confidence
      ↓
exactly one final category
```

## 10.2 Baseline and main model

Baseline:

- TF-IDF + Logistic Regression

Main:

- TF-IDF + linear classifier, or
- embeddings + simple classifier if useful

Avoid unnecessary complexity.

## 10.3 Boundary rules

Examples:

- Shell petrol purchase → Fuel
- Halfords service → Automotive
- electricity-only provider → Electricity
- gas-only provider → Gas
- bundled provider with no fuel-specific evidence → Utilities

All boundary rules must be documented.

## 10.4 Unseen-merchant evaluation

Do **not** randomly split rows only.

Create a merchant-group split so that test merchants are not present in training.

Report:

- macro F1
- weighted F1
- per-category precision/recall
- confusion matrix
- deterministic-rule coverage
- F1 on unseen merchants
- F1 on known merchants

This tests generalisation rather than memorisation.

---

# 11. Propensity modelling

One model per required product.

## 11.1 Output

For each `customer × product`:

- propensity in [0,1]
- model version
- calibration version
- confidence
- reason codes
- recommendation status

## 11.2 Baselines

Every model must beat or honestly compare against **two** baselines:

### Baseline A — heuristic rule

Example EV rule:

```text
IF
  ICE owner
  AND recurring fuel spend > threshold
  AND mileage > threshold
THEN
  high EV-opportunity score
```

### Baseline B — logistic regression

This provides a transparent statistical baseline.

### Main model

- LightGBM or XGBoost

If the main model only marginally beats the heuristic baseline, report that honestly.

## 11.3 Product feature families

### EV Finance

- fuel spend level/trend
- fuel transaction frequency
- annual mileage
- ICE ownership
- vehicle age
- existing vehicle finance
- automotive spend
- digital engagement
- sustainability preference

### Green Home

- homeowner/mortgage status
- utility spend/use
- home-improvement activity
- mortgage tenure
- energy usage trends
- existing green-home features if available

### Solar Finance

- home ownership
- electricity consumption/spend
- existing solar indicator
- regional solar-generation proxy if sourced
- home-related behaviour

### Paperless Banking

- current paper statements
- digital statement ratio
- digital transactions
- branch visits
- historical digital engagement
- previous paperless response

---

# 12. Proxy-risk feature policy

Postcode and income can function as socioeconomic proxies. They require explicit governance.

## 12.1 Default modelling policy

For the MVP:

- exact postcode is **not** used as a propensity feature;
- postcode sector / region may be used only where necessary for physical impact modelling or aggregate insights;
- income band is excluded from the default propensity model unless a documented ablation shows a compelling, non-discriminatory need;
- age is used only if justified and audited;
- protected attributes are not used for customer-level propensity decisioning.

## 12.2 Dual-model ablation

Where practical, compare:

- model without income/postcode proxies,
- model with controlled proxy features.

Report:

- performance delta,
- calibration delta,
- group disparity delta.

Default to the lower-risk model unless the value of the additional feature is clearly justified.

## 12.3 Fairness auditing

Protected or sensitive grouping attributes may be used **only for evaluation/audit**, kept separate from the production feature view.

---

# 13. Model evaluation

Do not lead with accuracy.

For every propensity model report:

- ROC-AUC
- PR-AUC
- Brier score
- expected calibration error
- calibration curve
- Precision@K
- Recall@K
- Lift@10%
- confusion matrix at chosen threshold
- heuristic-baseline comparison
- logistic-baseline comparison
- perturbed-generator performance
- subgroup diagnostics
- performance under missing-data scenarios

---

# 14. Probability calibration

Use:

- Platt scaling, or
- isotonic regression.

Calibration is fit on validation data only.

Report:

- reliability diagram,
- Brier score before/after,
- expected calibration error before/after.

Propensity displayed to users is the **calibrated** probability.

---

# 15. Trust Score

Trust is about the quality of the input evidence, not model confidence.

## 15.1 Trust components

- completeness,
- freshness,
- cross-source consistency,
- critical-field presence,
- out-of-distribution score.

## 15.2 Example

```text
Trust: 91/100

✓ 18 months of transactions
✓ vehicle record updated 2 months ago
✓ energy records complete
✓ no cross-source conflict
```

or:

```text
Trust: 44/100

✗ home ownership unknown
✗ vehicle record stale
✗ only 2 months of transactions
→ recommendation suspended
```

The Trust Score is not reused inside confidence in a way that double-counts the same factor.

---

# 16. Confidence — validated, not hand-waved

The original hand-weighted confidence formula is replaced by a validated reliability method.

## 16.1 Definition

Confidence is:

> The system's empirically validated estimate of how reliable the displayed propensity is under the available evidence.

It is **not** eligibility and **not** a second propensity.

## 16.2 Confidence features

A simple meta-model may use:

- calibrated probability margin,
- local calibration error,
- out-of-distribution score,
- signal stability across time windows,
- prediction stability under plausible missing-value perturbations,
- data recency summary.

Raw completeness belongs primarily to Trust and is not duplicated unless an ablation proves incremental value.

## 16.3 Meta-model

Train a simple, interpretable logistic meta-model or monotonic model on validation predictions to estimate prediction reliability.

Possible target:

- whether the prediction is correct at the operational threshold, or
- whether the prediction remains stable across bootstrap/model perturbations.

Document the chosen definition.

## 16.4 Confidence validation

Report:

- error rate by confidence decile,
- calibration gap by confidence decile,
- monotonic relationship between confidence and observed error,
- ablation of confidence components,
- confidence under generator perturbation,
- confidence under missing-data stress.

Acceptance criterion:

> Higher-confidence buckets must exhibit materially lower empirical error than lower-confidence buckets.

If this is not true, confidence is not surfaced.

---

# 17. Guardrails, exclusions, conflict detection and abstention

## 17.1 Recommendation states

```text
RECOMMEND
DO_NOT_RECOMMEND
INSUFFICIENT_INFORMATION
CONFLICT_REQUIRES_REVIEW
NOT_APPLICABLE
SUPPRESSED
```

## 17.2 Deterministic guardrails

Examples:

- already paperless → block Paperless Banking
- existing EV + no replacement use case → block EV Finance
- no reliable home-ownership evidence → withhold Solar Finance
- missing impact inputs → recommendation may exist, but `impact_status = UNAVAILABLE`
- closed/invalid product record → human review

These are **recommendation relevance rules**, not financial eligibility rules.

## 17.3 Conflict examples

### Vehicle conflict

```text
vehicle record = EV
fuel spend = high recurring
```

Possible causes:

- second vehicle,
- stale record,
- merchant misclassification.

Result:

```text
CONFLICT_REQUIRES_REVIEW
```

### Solar conflict

```text
home_owner = false
mortgage product = active
```

Result:

- flag source conflict,
- do not recommend Solar until resolved.

## 17.4 Abstention thresholds

Abstain if any of the following is true:

- critical field missing,
- high-severity conflict,
- Trust below threshold,
- OOD above threshold,
- confidence below minimum,
- product relevance guardrail fails.

Thresholds are selected on validation/scenario tests, not guessed at demo time.

---

# 18. Reason-code framework

The LLM never invents reasons.

Controlled reason codes include:

```text
HIGH_FUEL_SPEND
HIGH_ANNUAL_MILEAGE
ICE_VEHICLE_OWNER
OLDER_VEHICLE
HIGH_ELECTRICITY_USE
HOMEOWNER
MORTGAGE_CUSTOMER
NO_EXISTING_SOLAR
PAPER_STATEMENTS_ACTIVE
HIGH_DIGITAL_ENGAGEMENT
RECENT_HOME_IMPROVEMENT_SPEND
UTILITY_SPEND_RISING
```

Each code has:

- ID,
- customer wording,
- RM wording,
- derivation,
- threshold,
- evidence fields,
- applicable products,
- effective version.

---

# 19. Explainability levels

## 19.1 Customer

Simple, actionable and non-technical.

> You may benefit from exploring electric-vehicle options because your recent activity shows frequent fuel spending and high estimated annual mileage.

## 19.2 Relationship Manager

Shows:

- propensity,
- confidence,
- Trust,
- primary evidence,
- exclusions,
- model timestamp.

## 19.3 Auditor / model view

Shows:

- feature list,
- model version,
- calibration object,
- SHAP values,
- reason-code mapping,
- cutoff date,
- excluded features,
- impact-method version,
- guardrail log.

---

# 20. Counterfactuals and sensitivity analysis

Counterfactuals must not be presented as behavioural advice when they involve non-actionable variables.

## 20.1 Three feature classes

### Actionable

Examples:

- statement preference,
- choice to explore product,
- optional data sharing,
- potential vehicle replacement scenario.

### Contextual but not directly actionable

Examples:

- current annual mileage,
- current fuel spend,
- current electricity use.

### Non-actionable / protected / historical

Examples:

- age,
- historic tenure,
- immutable past behaviour.

## 20.2 UI labelling

For contextual/non-actionable variables, use:

> **Sensitivity analysis:** This shows how the model's estimate changes under a different scenario. It is not advice to change this behaviour.

Do **not** say:

> Drive less to become eligible.

## 20.3 Example

```text
Current EV propensity: 84%

Sensitivity:
If the observed annual mileage were 5,000 km rather than 15,200 km,
the model estimate would be 41%.

This is an explanation of model sensitivity, not a recommendation to alter driving behaviour.
```

---

# 21. Sustainability / carbon engine

The engine is deterministic, versioned and separately testable.

Suggested package:

```text
impact/
  ev.py
  solar.py
  green_home.py
  paperless.py
  factors.py
  assumptions.py
  provenance.py
  tests/
```

Every calculation returns:

- result,
- units,
- baseline,
- scenario,
- factor IDs,
- factor source,
- factor version,
- boundary,
- assumptions,
- method version,
- timestamp,
- completeness status.

---

# 22. Carbon methodology and source policy

## 22.1 Named factor source

Primary planned source:

- **UK Government GHG Conversion Factors for Company Reporting (DESNZ/DEFRA)**, exact annual edition pinned at build/submission time.

The exact factor edition and publication date must be frozen in `CARBON_METHODS.md`.

## 22.2 Methodology reference

Use and cite a documented methodology consistent with the brief, such as:

- GHG Protocol project / avoided-emissions accounting guidance,
- relevant PCAF guidance where financed-emissions accounting is actually applicable.

Do not invent a bespoke emissions methodology and label it standard.

## 22.3 Headline system boundary

For EV comparisons, use a **consistent operational boundary** for both baseline and scenario.

Preferred MVP boundary:

> Operational well-to-wheel emissions where matched UK Government factors are available for both liquid fuel and electricity. Vehicle manufacturing and battery manufacturing are excluded.

If matched well-to-wheel factors cannot be implemented consistently, downgrade to a clearly labelled operational-use boundary and document the limitation. Never compare mismatched boundaries without disclosure.

## 22.4 Manufacturing emissions

Excluded from the headline MVP estimate.

UI wording:

> Estimate covers operational energy/fuel emissions only; vehicle and battery manufacturing emissions are not included.

## 22.5 Grid-factor treatment

Headline annual estimate:

- use the pinned current factor vintage,
- no automatic future grid decarbonisation assumption.

Optional multi-year scenario:

- allow separate grid-decarbonisation scenarios,
- clearly label them as scenario assumptions,
- never mix them into the headline annual estimate silently.

---

# 23. EV impact model

Conceptual calculation:

```text
ICE baseline emissions =
  annual mileage
× matched ICE operational emission factor

EV scenario emissions =
  annual mileage
× EV kWh/km
× matched electricity operational factor

Potential annual reduction =
  ICE baseline - EV scenario
```

Assumptions shown to user/auditor:

- annual mileage,
- vehicle/fuel type,
- ICE factor,
- EV energy intensity,
- grid factor,
- boundary,
- time horizon,
- manufacturing excluded.

If mileage is estimated rather than observed, mark it as estimated and reduce Trust/confidence appropriately.

---

# 24. Solar impact model

Solar is only calculated when the system has sufficient physical inputs.

## 24.1 Required minimum inputs

At least:

- location/region sufficient for irradiance estimate,
- proposed system size,
- generation model or specific-yield assumption,
- electricity consumption,
- self-consumption/export assumption.

## 24.2 Generation approach

Use a documented source/model such as:

- a regional irradiance dataset / PV generation estimator,
- or a published UK specific-yield assumption with source and region.

The chosen method must be frozen in `CARBON_METHODS.md`.

## 24.3 Default safety behaviour

If the physical generation estimate is not supportable:

```text
impact_status = UNAVAILABLE
reason = INSUFFICIENT_SOLAR_GENERATION_INPUTS
```

Do not invent a generic carbon number.

---

# 25. Green Home impact model

Define the product catalogue so Green Home and Solar do not overlap ambiguously.

### Green Home

Possible uses:

- insulation,
- efficient heating,
- glazing,
- broader energy-efficiency renovation.

### Solar Finance

- solar PV,
- optionally battery if explicitly supported.

Each intervention has:

- documented impact method,
- units,
- baseline,
- assumptions,
- source.

---

# 26. Paperless Banking impact

Paperless must not be equated to carbon reduction without a defensible method.

Report:

- paper statements avoided,
- digital adoption rate,
- completion status.

Default:

```text
carbon_impact = NOT_CLAIMED
```

If a documented lifecycle method is later added, it must be separately reviewed and sourced.

---

# 27. Impact Passport

Every sustainability estimate has an auditable Passport.

```text
IMPACT PASSPORT
────────────────────────────────
ID: IMP-003921
Opportunity: EV Finance

Estimated reduction:
1,670 kg CO₂e/year

Baseline:
2,850 kg CO₂e/year

Scenario:
1,180 kg CO₂e/year

Method:
EV_OPERATIONAL_WTW_V1

Boundary:
Operational well-to-wheel
Manufacturing excluded

Factor source:
UK Government GHG Conversion Factors

Factor vintage:
[pinned exact release]

Grid treatment:
Current-vintage annual factor

Data cutoff:
2026-06-30

Calculation date:
2026-10-10

Assumptions:
- annual mileage = 15,200 km
- EV efficiency = X kWh/km
- ...

Status:
MODELLED ESTIMATE
NOT MEASURED OUTCOME
```

---

# 28. What-if simulator

The simulator reruns deterministic calculations; the LLM only explains the new structured output.

## 28.1 EV

Adjust:

- mileage scenario,
- EV efficiency,
- fuel type,
- grid factor scenario.

## 28.2 Solar

Adjust:

- system size,
- specific yield / generation scenario,
- self-consumption,
- electricity use.

## 28.3 Green Home

Adjust:

- selected retrofit,
- estimated energy reduction,
- electricity/gas split.

Every simulation stores:

- scenario inputs,
- output,
- method version,
- timestamp.

---

# 29. Propensity is not impact

Always display these as separate dimensions.

Example:

```text
Customer A
Propensity: 91%
Potential impact: 100 kg/year

Customer B
Propensity: 62%
Potential impact: 2,400 kg/year
```

Portfolio users can view a 2D matrix:

```text
               HIGH IMPACT
                   ↑
   Investigate     |     PRIORITISE
                   |
-------------------+--------------------→ HIGH PROPENSITY
                   |
   Low priority    |     Easy wins
```

---

# 30. Expected Sustainability Impact

Optional planning metric:

```text
Expected Sustainability Impact
= propensity × potential physical impact
```

Example:

```text
0.62 × 2,400 kg = 1,488 kg
```

Label:

> Portfolio planning estimate — not an observed outcome and not a guaranteed reduction.

Never replace propensity or physical impact with this derived measure.

---

# 31. Opportunity priority score

The original “customer relevance” term is removed unless explicitly defined.

MVP priority score:

```text
Priority =
  40% calibrated propensity
+ 25% validated confidence
+ 20% normalised potential impact
+ 15% Trust
```

Rules:

- all components are defined,
- normalisation method documented,
- weights versioned,
- score is **priority**, not eligibility,
- portfolio users may inspect each component.

Ablate the ranking formula and show whether it changes campaign quality.

---

# 32. Next Best Green Action

SHOULD / COULD depending time.

The action engine is rules/model-driven, not generated by the LLM.

Possible outputs:

- show educational card in mobile app,
- include in next RM conversation,
- defer,
- suppress,
- request more information.

Action selection may use:

- channel engagement,
- recent contacts,
- prior response,
- product priority,
- customer preference.

---

# 33. Campaign optimiser

COULD only.

## 33.1 Objectives

- maximise likely conversions,
- maximise estimated sustainability impact,
- balanced objective.

## 33.2 Mandatory constraints

A realistic optimiser must include:

- do-not-contact status,
- channel consent,
- contact-frequency cap,
- cooling-off / fatigue window,
- maximum simultaneous product campaigns,
- suppression after recent decline,
- channel capacity,
- campaign capacity,
- no duplicated/conflicting offers.

Example:

```text
No customer receives:
- more than 2 campaign contacts in 30 days,
- the same product within 60 days after decline,
- multiple conflicting green-product contacts in the same week.
```

Without these constraints the optimiser is not considered complete and must stay out of the demo.

---

# 34. Customer memory

Optional extension, but recommended after core stability.

Memory stores:

- prior insights,
- customer response,
- action,
- channel,
- status,
- completion.

Example response values:

```text
INTERESTED
NOT_INTERESTED
LATER
ALREADY_COMPLETED
DO_NOT_SHOW_AGAIN
```

Memory may influence:

- communication timing,
- duplicate suppression,
- message selection,
- channel/action selection.

Memory may **not** directly override:

- propensity,
- financial eligibility,
- impact calculation.

If memory reveals a new factual state, that fact enters the proper source data and the model is rerun.

---

# 35. Recommendation lifecycle

```text
DETECTED
  ↓
RECOMMENDED
  ↓
SHOWN
  ↓
ENGAGED
  ↓
ACCEPTED / DECLINED
  ↓
COMPLETED
  ↓
CLOSED
```

Alternate states:

```text
WITHHELD
SUPPRESSED
INSUFFICIENT_DATA
CONFLICT
```

Example lifecycle:

```text
January: Paperless recommendation shown
March: Customer selects "Later"
May: Digital engagement increases
June: Recommendation re-evaluated
July: Customer goes paperless
August: Paperless opportunity closes
```

---

# 36. Dynamic customer journey

The dashboard should demonstrate recommendation evolution.

Example:

```text
EV recommendation active
      ↓
customer buys EV
      ↓
vehicle record updates
      ↓
EV recommendation is suppressed/closed
```

This proves the system does not repeatedly recommend already-completed actions.

---

# 37. LLM architecture

## 37.1 Prompt input policy

The LLM receives only validated structured facts.

It must **never receive raw merchant descriptions**.

Reason:

- raw merchant text can contain untrusted content,
- it is unnecessary for explanation,
- it creates prompt-injection risk.

Instead pass:

- category,
- aggregated evidence,
- reason codes,
- propensity,
- confidence,
- impact object,
- guardrail state.

## 37.2 Prompt contract

The LLM may:

- paraphrase,
- explain,
- summarise evidence,
- explain missing information,
- explain what-if outputs already calculated elsewhere.

The LLM may not:

- invent numbers,
- recalculate impact,
- change propensity,
- determine eligibility,
- add unsupported reasons,
- promise savings,
- guarantee carbon outcomes,
- promise product approval.

## 37.3 Model choice and freeze requirement

The exact model must be pinned before implementation freeze.

Configuration:

```text
LLM_PROVIDER
LLM_MODEL
LLM_MODEL_VERSION
PROMPT_VERSION
TEMPERATURE
MAX_OUTPUT_TOKENS
```

The project is not considered complete until the final report states:

- exact model name/version,
- exact API/provider,
- average input/output tokens per explanation,
- measured latency,
- measured cost per 1,000 explanations using current provider pricing,
- cache hit rate.

Do not leave the submission with “OpenAI/Gemini/etc.” as a generic placeholder.

## 37.4 Cost target

Engineering target:

> Keep the explanation layer cheap enough that 1,000 explanations are operationally negligible relative to campaign value.

The actual numeric cost is measured and reported from the pinned model at submission time rather than guessed months in advance.

## 37.5 Caching

Cache key:

```text
SHA256(
  recommendation_object_canonical_json
  + prompt_version
  + llm_model_version
  + locale
)
```

If the recommendation object has not changed, reuse the explanation.

---

# 38. LLM structured output

```json
{
  "headline": "...",
  "explanation": "...",
  "why_recommended": ["...", "..."],
  "estimated_impact_text": "...",
  "confidence_text": "...",
  "action_text": "...",
  "eligibility_disclaimer": "...",
  "missing_information": []
}
```

Schema validation is mandatory.

---

# 39. LLM grounding checker

Programmatic checks run after generation.

## 39.1 Deterministic checks

- every numeric value appears in approved structured input,
- every reason maps to an approved reason code,
- product mapping is correct,
- no “eligible/approved/guaranteed” wording,
- no unsupported carbon number,
- no unsupported savings claim,
- no mention of products not in the object.

## 39.2 Result

```text
PASS
FAIL_NUMERIC
FAIL_REASON_CODE
FAIL_ELIGIBILITY
FAIL_UNSUPPORTED_CLAIM
```

---

# 40. Deterministic template fallback

If:

- LLM API fails,
- schema validation fails,
- grounding check fails,
- latency exceeds threshold,

render a deterministic template.

Example:

> EV Finance may be relevant because your recent data shows high recurring fuel expenditure and an existing petrol vehicle. The model estimates a propensity of 84% with high confidence. The estimated annual operational emissions reduction is 1.67 t CO₂e under the documented assumptions shown in the Impact Passport. This does not determine financial eligibility.

The product remains fully usable without the LLM.

---

# 41. LLM evaluation

Create 100–200 fixed test cases.

## 41.1 Categories

- normal recommendation,
- missing data,
- conflicting signals,
- low confidence,
- no impact available,
- product excluded,
- multiple opportunities,
- paperless case,
- negative or zero impact,
- adversarial user request,
- prompt injection attempt through a user-controlled field,
- request to guarantee savings,
- request to claim eligibility,
- request to alter model score.

## 41.2 Metrics

- groundedness,
- factual accuracy,
- unsupported-claim rate,
- numerical consistency,
- product-mapping accuracy,
- reason-code coverage,
- abstention correctness,
- eligibility-language violations,
- fallback rate,
- average latency,
- cost per 1,000 explanations.

## 41.3 Evaluation method

Do not rely only on LLM-as-judge.

Use:

1. deterministic/programmatic checks,
2. manually labelled reference set,
3. optional LLM judge as a secondary measure.

---

# 42. Customer-facing dashboard

Example card:

```text
YOUR GREEN OPPORTUNITIES

Electric Vehicle
High relevance

Potential annual impact
~1.7 t CO₂e reduction
(modelled estimate)

Why you're seeing this
• high recurring fuel spend
• high annual mileage

Data as of
30 Jun 2026

[Explore EV options]
[Why am I seeing this?]
```

No claim of eligibility.

---

# 43. Customer “Why?” screen

```text
WHY AM I SEEING THIS?

Based on:
✓ recurring fuel purchases
✓ estimated high annual mileage
✓ existing petrol vehicle

Model confidence:
High

Data cutoff:
30 Jun 2026

This recommendation does not mean you are financially eligible.
```

---

# 44. Relationship Manager workspace

Example:

```text
CUSTOMER C10001

Top Green Opportunity
EV Finance

Propensity        84%
Confidence        87%
Trust             91/100
Priority          86/100

Evidence
Fuel spend        £310/month
Mileage           15,200 km/year
Vehicle           Petrol

Potential impact
1.67 t CO₂e/year

Status
RECOMMEND

Next action
Discuss EV options at the next suitable contact
```

Tabs:

- Evidence
- Impact Passport
- Sensitivity
- History
- Audit

---

# 45. Portfolio command centre

## 45.1 KPIs

- customers analysed,
- customers with ≥1 opportunity,
- opportunities by product,
- actionable opportunities,
- high-confidence opportunities,
- high-Trust opportunities,
- estimated portfolio impact,
- paperless conversion opportunity.

## 45.2 Funnel

```text
100,000 customers analysed
        ↓
43,000 candidates
        ↓
28,000 pass Trust/guardrails
        ↓
14,000 high-priority opportunities
        ↓
expected conversions / scenario estimate
```

## 45.3 Filters

- product,
- region,
- segment,
- propensity,
- confidence,
- Trust,
- impact,
- recommendation status,
- data quality.

---

# 46. FR6 trend insights

Trend analytics is mandatory.

Show monthly:

- number of opportunities by product,
- average propensity,
- high-confidence opportunity share,
- estimated portfolio impact,
- paperless adoption rate,
- observed conversion rate where labels/outcomes exist,
- suppression/conflict rate,
- data-quality trend.

Example:

```text
EV high-priority opportunities
Jul   8,210
Aug   8,730
Sep   9,050
Oct   9,420
MoM   +4.1%
```

Do not claim causality from trends.

---

# 47. Geographic / segment views

Examples:

- EV opportunities by region,
- Solar opportunities by region,
- Paperless adoption by age band,
- Green Home opportunities by homeownership segment,
- opportunity/impact by digital-engagement segment.

Proxy-risk warning:

- region is shown for analysis and physical impact context,
- exact postcode is not used for customer propensity in the default model.

---

# 48. Portfolio scenario planner

Business user enters:

```text
Campaign: EV Finance
Target population: top 10,000 eligible-to-contact recommendations
Assumed conversion: 5%
```

Output:

```text
Scenario adopters: 500
Estimated potential annual CO₂e reduction: X
High-confidence share: Y%
Average propensity: Z%
```

All outputs labelled as **scenario estimates**.

Conversion rate can be varied:

```text
5% → 10% → 20%
```

---

# 49. Responsible AI console

SHOULD.

Displays:

- model status,
- calibration,
- confidence validation,
- Trust distribution,
- feature drift,
- missingness drift,
- fairness indicators,
- recommendation suppression,
- data conflicts,
- LLM grounding,
- carbon-method version,
- factor version.

---

# 50. Fairness analysis

Audit:

- recommendation rate by group,
- false-positive / false-negative rates,
- propensity calibration by group,
- confidence distribution,
- abstention rate,
- Trust distribution.

Key rule:

> Do not “fix” fairness by hiding diagnostics. Document any disparity, investigate its source, and state limitations.

Protected/sensitive attributes used for fairness auditing are separated from the production model features.

---

# 51. Human oversight

Relationship managers / reviewers may:

- accept recommendation,
- suppress recommendation,
- flag data issue,
- request review.

They may not manually edit:

- propensity,
- confidence,
- impact result,
- model version.

Manual actions are logged.

---

# 52. Model and version traceability

Every recommendation stores:

- model version,
- calibration version,
- feature version,
- confidence method version,
- data cutoff,
- prediction timestamp,
- carbon-engine version,
- emission-factor version,
- recommendation rule version,
- prompt version,
- LLM model version.

A recommendation must be reproducible later.

---

# 53. API layer

Suggested FastAPI endpoints:

```text
GET  /customers/{id}
GET  /customers/{id}/opportunities
GET  /customers/{id}/recommendations
GET  /customers/{id}/impact/{product}
POST /customers/{id}/simulate

GET  /portfolio/summary
GET  /portfolio/segments
GET  /portfolio/trends
GET  /portfolio/opportunities

POST /recommend
POST /explain
POST /feedback

GET  /audit/recommendations/{id}
GET  /health
```

---

# 54. Service architecture

Hackathon-friendly stack:

```text
Frontend
  Streamlit or React

Backend
  FastAPI

Storage
  PostgreSQL or SQLite

ML
  scikit-learn / LightGBM / XGBoost

Impact engine
  Python deterministic modules

LLM
  structured-output wrapper

Visualisation
  Plotly
```

Do not split into unnecessary microservices.

---

# 55. Repository structure

```text
greenpath/
│
├── app/
│   ├── customer_ui/
│   ├── rm_ui/
│   └── business_ui/
│
├── api/
│   └── main.py
│
├── data/
│   ├── raw/
│   ├── public/
│   ├── synthetic/
│   ├── processed/
│   └── factors/
│
├── data_generation/
│   ├── generator.py
│   ├── perturbation.py
│   └── configs/
│
├── pipelines/
│   ├── preprocess.py
│   ├── customer360.py
│   ├── feature_pipeline.py
│   └── leakage_checks.py
│
├── models/
│   ├── transaction_classifier/
│   ├── ev_propensity/
│   ├── green_home_propensity/
│   ├── solar_propensity/
│   └── paperless_propensity/
│
├── trust/
│   ├── quality.py
│   ├── ood.py
│   └── conflicts.py
│
├── confidence/
│   ├── meta_model.py
│   └── validation.py
│
├── impact/
│   ├── ev.py
│   ├── solar.py
│   ├── green_home.py
│   ├── paperless.py
│   ├── factors.py
│   ├── assumptions.py
│   └── provenance.py
│
├── recommendation/
│   ├── guardrails.py
│   ├── ranking.py
│   ├── reasons.py
│   ├── lifecycle.py
│   └── actions.py
│
├── llm/
│   ├── prompts/
│   ├── explain.py
│   ├── validate.py
│   ├── fallback.py
│   └── grounding_eval.py
│
├── evaluation/
│   ├── ml/
│   ├── transaction/
│   ├── confidence/
│   ├── carbon/
│   ├── llm/
│   ├── fairness/
│   └── scenarios/
│
├── tests/
│   ├── test_guardrails.py
│   ├── test_carbon_ev.py
│   ├── test_carbon_solar.py
│   ├── test_recommendation_schema.py
│   ├── test_leakage.py
│   └── test_llm_grounding.py
│
├── reports/
├── Dockerfile
├── Makefile
├── requirements.lock
├── .env.example
└── README.md
```

---

# 56. Reproducibility mechanics

Reproducibility is a MUST, not documentation polish.

## 56.1 Fixed seeds

Store seeds centrally:

```yaml
SEED_DATA: 42
SEED_SPLIT: 43
SEED_MODEL: 44
SEED_PERTURBATION: 45
```

## 56.2 One-command pipeline

Required command:

```bash
make all
```

It must:

1. validate environment,
2. prepare / generate data,
3. split customers,
4. categorise transactions,
5. build Customer 360,
6. train baselines,
7. train main models,
8. calibrate,
9. train confidence layer,
10. run impact tests,
11. generate evaluation artefacts,
12. create held-out predictions,
13. run scenario tests.

Additional commands:

```bash
make test
make train
make evaluate
make app
```

## 56.3 Dependency pinning

Use:

- locked dependency file,
- or Docker image with pinned versions.

## 56.4 Data versioning

At minimum record:

- input file hashes,
- generator config hash,
- emissions-factor file hash,
- split manifest hash.

DVC is optional; reproducible hashes are mandatory.

## 56.5 Test coverage priorities

Critical unit tests:

- EV formula,
- Solar formula,
- Paperless no-carbon rule,
- guardrail suppression,
- conflict detection,
- abstention,
- recommendation schema,
- LLM numeric grounding,
- customer split leakage.

---

# 57. Edge-case scenario suite

| Scenario | Expected behaviour |
|---|---|
| existing EV, no replacement use case | EV suppressed |
| no home-ownership evidence | Solar withheld |
| high fuel spend + EV record | conflict/review |
| missing mileage | lower Trust/confidence; impact unavailable or assumption-labelled |
| already paperless | Paperless suppressed |
| no electricity data | Solar impact unavailable |
| low propensity, high impact | visible in portfolio, not necessarily customer recommendation |
| high propensity, poor Trust | abstain or withhold |
| stale vehicle record | Trust reduced |
| conflicting product records | human review |
| OOD customer | low confidence / abstain |
| LLM told to promise savings | refuse / template |
| LLM told to claim eligibility | refuse / template |
| malicious merchant text | never enters LLM prompt |
| carbon factor file missing | impact engine fails closed |
| factor vintage mismatch | validation error |
| missing methodology metadata | Impact Passport unavailable |

---

# 58. Demo personas

| Persona | Demonstrates |
|---|---|
| C10001 EV candidate | strong positive case |
| C10002 Solar candidate | home/electricity signal |
| C10003 Paperless candidate | digital engagement |
| C10004 conflict customer | EV record + fuel spend |
| C10005 insufficient data | abstention |
| C10006 already green | suppression |
| C10007 multi-opportunity | prioritisation |
| C10008 changed circumstances | memory/lifecycle |
| C10009 OOD/noisy customer | confidence/Trust |
| C10010 sensitivity example | counterfactual labelling |

---

# 59. Five-minute demo flow

## Minute 0–1: Portfolio

Show:

```text
100,000 customers analysed
28,400 actionable opportunities
9,700 high-confidence opportunities
X estimated annual portfolio impact
```

Show one monthly trend chart.

## Minute 1–2: Customer C10001

Show:

```text
EV Finance
Propensity: 84%
Confidence: 87%
Trust: 91/100
```

Click **Why?**

Show reason codes and evidence.

## Minute 2–3: Impact Passport + what-if

Open Impact Passport.

Show:

- exact factor source,
- boundary,
- assumptions,
- current factor vintage.

Change mileage or EV efficiency.

Impact recalculates in deterministic engine.

## Minute 3–4: Responsible abstention

Open C10004.

Show:

```text
CONFLICT_REQUIRES_REVIEW
Vehicle record indicates EV
Transaction history indicates recurring fuel spend
```

Open C10005.

Show insufficient-data abstention.

## Minute 4–5: Business value + memory

Show:

- propensity-vs-impact matrix,
- month-over-month opportunity trend,
- portfolio scenario planner.

End with C10008:

```text
customer goes paperless
→ recommendation lifecycle closes automatically
```

---

# 60. Optional Green Investments

COULD only.

Potential features:

- existing investment activity,
- investment balance band,
- sustainability preference,
- existing sustainable holdings.

Outputs:

- propensity,
- confidence,
- reasons,
- opportunity signal.

Guardrail:

> This is not investment advice and does not determine financial suitability or eligibility.

---

# 61. Optional Green Loans

COULD only.

Potential use cases:

- EV charging,
- heat pump,
- home retrofit,
- documented green-purpose expenditure.

Outputs:

- relevance/propensity,
- confidence,
- reason codes.

Guardrail:

> Opportunity signal only; no credit approval.

---

# 62. Evaluation report structure

1. Executive summary
2. Dataset and provenance
3. Public-data anchors
4. Synthetic-data generation
5. Generator perturbation
6. Leakage audit
7. Train/validation/test methodology
8. Transaction categorisation
9. Heuristic baselines
10. Statistical baselines
11. Propensity models
12. Probability calibration
13. Trust methodology
14. Confidence methodology and validation
15. Guardrails / abstention
16. Recommendation ranking
17. Sustainability calculations
18. Carbon methodology and boundaries
19. Impact Passport
20. LLM architecture
21. LLM programmatic checks
22. LLM adversarial evaluation
23. Scenario tests
24. Trend analytics
25. Fairness / proxy-risk analysis
26. System performance
27. Cost analysis
28. Limitations
29. Reproducibility
30. Future work

---

# 63. System performance evaluation

Record:

- Customer 360 latency,
- transaction categorisation latency,
- propensity inference latency,
- calibration latency,
- confidence latency,
- carbon-engine latency,
- guardrail latency,
- LLM latency,
- end-to-end latency,
- cost per 1,000 explanations,
- LLM cache hit rate,
- memory footprint.

Target:

> Structured recommendation generation should remain fast enough that the LLM is the dominant latency component, not the data/model pipeline.

---

# 64. Responsible AI note

Must cover:

## Privacy

- no real confidential banking data,
- synthetic/public data only,
- data minimisation,
- no raw merchant text in LLM,
- no unnecessary sensitive attributes.

## Bias

- proxy-risk policy,
- fairness metrics,
- subgroup calibration,
- documented limitations.

## Explainability

- reason codes,
- evidence,
- confidence validation,
- sensitivity analysis,
- Impact Passport.

## Hallucination

- structured inputs only,
- programmatic checks,
- deterministic fallback,
- adversarial tests.

## Human oversight

- review states,
- manual suppression,
- immutable model outputs,
- audit logs.

## Data limitations

- synthetic labels,
- public-data mismatch,
- sparse physical inputs,
- non-causal relationships,
- estimated rather than measured sustainability outcomes.

---

# 65. Risk register

| Risk | Severity | Mitigation |
|---|---:|---|
| scope explosion | Critical | Must/Should/Could freeze |
| synthetic circularity | Critical | generator perturbation, rule baseline, public anchors |
| leakage | Critical | temporal/customer splits + automated audit |
| arbitrary confidence | High | meta-model + empirical validation |
| carbon inconsistency | Critical | named source, boundary, versioning, tests |
| solar overclaim | High | physical input minimum; fail closed |
| LLM hallucination | Critical | structured input, programmatic checker, template fallback |
| prompt injection | High | no raw merchant text in prompt |
| fairness/proxy risk | High | restricted features + ablation |
| demo inconsistency | Medium | single coherent dates + scripted personas |
| unreproducible run | Critical | fixed seeds, Docker/lockfile, `make all` |
| campaign over-contact | Medium | fatigue/cooldown constraints |
| partial optional features | High | keep out of demo until DoD met |

---

# 66. Definitions of Done

## 66.1 Required opportunity

Complete when:

- model trained,
- heuristic + logistic baseline evaluated,
- calibrated,
- confidence validated,
- reason codes mapped,
- guardrails tested,
- impact method implemented or explicitly unavailable,
- customer output works,
- test predictions exported.

## 66.2 Impact engine

Complete when:

- formula documented,
- source named,
- factor version pinned,
- boundary documented,
- assumptions visible,
- unit tests pass,
- Impact Passport generated.

## 66.3 LLM layer

Complete when:

- exact model pinned,
- structured output enforced,
- programmatic grounding checker passes,
- fallback works,
- adversarial suite run,
- cost/1,000 measured,
- cache works.

## 66.4 Optional feature

Complete only if:

- core logic works,
- tests exist,
- demo state is stable,
- no core feature is degraded by its inclusion.

---

# 67. Build order

## Gate 1 — foundations

- repo,
- schemas,
- data generation,
- public anchors,
- splits,
- transaction categorisation,
- Customer 360.

## Gate 2 — four product models

- heuristic baselines,
- logistic baselines,
- LightGBM/XGBoost,
- calibration,
- held-out evaluation.

## Gate 3 — trust and safety

- Trust,
- confidence,
- OOD,
- conflicts,
- abstention,
- guardrails.

## Gate 4 — sustainability engine

- EV,
- Solar,
- Green Home,
- Paperless,
- source versioning,
- Impact Passport,
- unit tests.

## Gate 5 — LLM

- prompt contract,
- exact model freeze,
- structured output,
- grounding checks,
- fallback,
- eval suite,
- cost/caching.

## Gate 6 — UX

- customer,
- portfolio,
- trend views,
- RM if time.

## Gate 7 — standout SHOULD features

- what-if,
- sensitivity,
- memory/lifecycle,
- scenario planner,
- evidence graph.

## Gate 8 — COULD only

- optimiser,
- next-best-action,
- optional products,
- advanced fairness console.

---

# 68. Scoring strategy

Use effort roughly in proportion to the judging rubric:

| Area | Suggested engineering focus |
|---|---:|
| Data + ML + evaluation | 25% |
| Sustainability methodology | 15% |
| Architecture + reproducibility | 15% |
| GenAI + evaluation | 15% |
| Explainability + Responsible AI | 10% |
| Business relevance / analytics | 10% |
| UX polish | 10% |

The dashboard is important, but not at the expense of validation.

---

# 69. What makes this version genuinely different

A basic implementation is:

```text
customer data
→ model
→ recommendation
→ carbon estimate
→ explanation
→ dashboard
```

Greenr becomes:

```text
customer data
      ↓
Data Trust + Leakage Controls
      ↓
Customer 360
      ↓
Calibrated Propensity
      ↓
Validated Confidence
      ↓
OOD / Conflict / Abstention
      ↓
Recommendation Guardrails
      ↓
Auditable Sustainability Engine
      ↓
Impact Passport
      ↓
Priority / Portfolio Planning
      ↓
Grounded LLM + Deterministic Fallback
      ↓
Customer / RM / Portfolio Experiences
      ↓
Trend Analytics + Outcome Tracking + Memory
```

The seven strongest differentiators remain:

1. **Validated confidence rather than an arbitrary second score**
2. **Abstention, conflict detection and fail-closed behaviour**
3. **Impact Passport with named sources, boundaries and factor versions**
4. **Sensitivity / what-if analysis with correct actionable-vs-contextual labelling**
5. **Propensity × sustainability-impact portfolio intelligence**
6. **Grounded LLM with programmatic checks, fallback, caching and cost reporting**
7. **Dynamic customer memory and recommendation lifecycle**

---

# 70. Final pitch

### One sentence

> **Greenr is an explainable green-finance decision platform that identifies the right sustainability opportunity for each customer, quantifies potential impact with auditable calculations, knows when not to recommend, and helps Lloyds choose the next best action across both individual customers and the wider portfolio.**

### Judge-demo version

> **We don't just predict who might want a green product. We show why, how reliable the prediction is, what impact it could plausibly have, what Lloyds should do next, and when the responsible answer is to make no recommendation at all.**

---

# 71. Final submission checklist

## Core functionality

- [ ] EV Finance
- [ ] Green Home
- [ ] Solar Finance
- [ ] Paperless Banking
- [ ] Customer 360
- [ ] Transaction categorisation
- [ ] Propensity + calibration
- [ ] Heuristic baseline
- [ ] Logistic baseline
- [ ] Trust
- [ ] Validated confidence
- [ ] Guardrails
- [ ] Conflict detection
- [ ] Abstention
- [ ] Impact engine
- [ ] Impact Passport
- [ ] Reason codes
- [ ] Customer view
- [ ] Portfolio view
- [ ] Trend view
- [ ] Grounded LLM
- [ ] Programmatic LLM checker
- [ ] Deterministic fallback

## Evaluation

- [ ] customer-level split verified
- [ ] temporal cutoff verified
- [ ] unseen-merchant test
- [ ] generator-perturbation test
- [ ] leakage audit
- [ ] calibration evaluation
- [ ] confidence decile evaluation
- [ ] carbon unit tests
- [ ] scenario suite
- [ ] LLM adversarial suite
- [ ] fairness/proxy audit
- [ ] system latency
- [ ] LLM cost/1,000
- [ ] cache hit rate

## Reproducibility

- [ ] fixed seeds
- [ ] `make all`
- [ ] dependency lock / Docker
- [ ] data hashes
- [ ] factor-file hash
- [ ] model versions
- [ ] test suite passes

## Submission

- [ ] A working prototype
- [ ] B source + run instructions
- [ ] C trained models + inference
- [ ] D preprocessing pipeline
- [ ] E LLM prompts/model/eval
- [ ] F architecture diagram
- [ ] G evaluation report
- [ ] H Responsible AI note
- [ ] I test predictions
- [ ] data card
- [ ] model cards
- [ ] carbon methods
- [ ] LLM eval
- [ ] scenario tests
- [ ] leakage audit
- [ ] reproducibility note

## Optional only after core completion

- [ ] what-if simulator
- [ ] sensitivity/counterfactual explanations
- [ ] RM workspace
- [ ] customer memory
- [ ] lifecycle timeline
- [ ] portfolio scenario planner
- [ ] evidence graph
- [ ] campaign optimiser
- [ ] Next Best Green Action
- [ ] Green Investments
- [ ] Green Loans
- [ ] advanced fairness console

---

## Final implementation principle

When forced to choose between:

- one more feature, or
- stronger evidence that an existing feature is correct,

choose the stronger evidence.

That is the operating principle for the entire MVP.
