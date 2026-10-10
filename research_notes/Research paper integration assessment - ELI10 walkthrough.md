# GreenPath's research assessment, explained simply

## Start here: what the final report is actually saying

**GreenPath has several sensible building blocks. It does not yet implement every important idea from all ten papers, and the saved results do not prove it works on real bank customers.**

That is not the same as saying the project is bad. It means we should separate:

1. **What we built.** There is code for a mechanism.
2. **What we measured.** There is evidence from a particular experiment.
3. **What we hope to improve.** There is a plan, but no measured benefit yet.

The final report is an audit of those three things, not a new experiment and not a list of ten features you must build before submitting.

This walkthrough follows the same ten-paper order as the [original assessment](Research%20paper%20integration%20assessment.md). That copy is identical to the committed report originally located in `reports/`. All project-specific findings below come from that assessment; this document adds explanations, not new runtime verification.

> **Reading suggestion:** Read sections A–D first. Then read the ten papers one at a time. You do not need to memorize every algorithm name.

## A. Picture GreenPath as several helpers, not one giant AI

Imagine a bank employee, called a **relationship manager (RM)**, deciding which sustainable-product opportunities are worth discussing with customers.

GreenPath has several jobs:

```text
Bank transaction descriptions
    -> transaction categoriser
    -> categories and spending summaries
                                     \
Other customer information ----------> customer snapshot
                                          |
                                          v
                                 product-adoption model
                                          |
                                          v
                                scores / opportunity support

Physical activity + scenario assumptions + emissions factors
    -> separate physical impact calculation

Approved reasons + product state + validated impact information
    -> explanation service
    -> approved sentences, optionally reordered by an LLM
```

This is a simplified map, not a complete call graph. The important point is that **different parts answer different questions**.

| Part | Question it answers | What it does not establish |
|---|---|---|
| Transaction categoriser | “What kind of payment is this?” | The customer's carbon footprint |
| Customer snapshot, or Customer360 | “What information was available about this customer at this time?” | That missing information is zero |
| Adoption model | “How likely is adoption of this product over the defined future period?” | Loan approval or a guaranteed purchase |
| SHAP explanation | “Which inputs pushed this model's score up or down?” | What causes adoption or carbon savings |
| Physical impact calculator | “Under these assumptions, how would operational emissions differ?” | Actual savings already achieved |
| Language component | “How should approved information be presented?” | Independent proof that the information is true |

**Why this matters:** A good answer to one question does not automatically give you a good answer to the next. Correctly recognizing a fuel payment does not tell us how many litres were bought, whether the customer will buy an EV, or how much carbon an EV would save.

### One customer, three separate questions

Suppose Maya has a transaction reading `ROADSTOP FUEL`.

1. **Transaction question:** Is this a fuel purchase? The categoriser tries to decide.
2. **Adoption question:** Does Maya's overall information suggest EV Finance might be relevant? A different model estimates adoption propensity.
3. **Impact question:** If Maya changes vehicles, what would emissions look like under specified mileage, efficiency, and energy assumptions? A separate calculator handles that.

These are related, but none is a shortcut to the others.

## B. The report's status words are not pass/fail grades

| Report phrase | Plain-English meaning |
|---|---|
| Implemented | “We found this mechanism in the code.” Not “we just ran it successfully.” |
| Saved evidence | “A previous result file records this.” Not “we reproduced it today.” |
| Partial integration | “Some pieces overlap with the paper, but important pieces are absent.” |
| Practical alignment | “We follow the useful lesson, without copying the whole experiment.” |
| Not implemented | “The paper's defining mechanism is not present.” |
| Proposed / prospective payoff | “This could help, but we have not measured that benefit.” |
| Acceptance criteria | “Checks future work must satisfy before we call it successful.” |
| Static inspection | “Reading source and saved files without running the application.” |

An analogy: reading a cake recipe shows that it includes baking instructions. Seeing a photo suggests someone baked a cake before. Neither proves that today's ingredients and oven produce the same cake.

The assessment inspected source, test code, papers, and saved evidence. It did **not** run application tests, train models, replay the pipeline, or evaluate a live language-model provider.

## C. Four distinctions unlock most of the report

### 1. A carbon footprint is not a potential carbon saving

- **Footprint:** an estimate of emissions associated with consumption over a period.
- **Potential saving:** a difference between a baseline and a proposed scenario.

**Made-up arithmetic, not GreenPath measurements:**

```text
Spending-based footprint:
    £100 spending × 0.5 kg CO2e/£ = 50 kg CO2e

Physical scenario difference:
    baseline 200 kg CO2e − alternative 120 kg CO2e = 80 kg CO2e potential saving
```

`CO2e` means carbon-dioxide equivalent: different greenhouse gases expressed using a common comparison unit.

The first calculation estimates a level. The second estimates a change. **Do not add them together or call them the same thing.** Also, a negative scenario saving means the alternative produces more emissions under those assumptions; we should not hide that.

GreenPath currently has evidence-bound physical scenario calculations. It does not yet have the full spending-based consumption-footprint method discussed in Paper 1.

### 2. Adoption probability, correctness confidence, Trust, and eligibility are different

| Concept | Simple interpretation |
|---|---|
| Adoption probability / propensity | “The model estimates how likely adoption is over its defined horizon.” |
| Decision threshold | “The score above which we classify the case as positive.” |
| Correctness confidence | “A separate attempt to estimate/rank how likely that yes/no model decision is to be correct.” |
| Trust | “A separate project signal; do not interpret it as adoption probability or guaranteed correctness.” |
| Eligibility | “Does the customer actually meet the product's requirements?” |

For example, a model might estimate an adoption probability of 0.30. With a hypothetical threshold of 0.20, it predicts positive. **The 0.30 is not automatically the probability that this positive decision is correct.** It is also not a loan-approval probability.

The assessment says **all four saved core correctness-confidence outputs are suppressed**. In everyday language: the saved release checks did not provide enough evidence to show those confidence outputs. This does not mean every prediction is wrong or that all adoption scores are suppressed.

### 3. An explanation describes model behavior, not cause and effect

“Higher fuel spending pushed the model's score upward” is different from:

> “Increasing fuel spending will cause this customer to adopt an EV.”

The first describes a computation. The second makes a causal claim requiring different evidence.

Similarly, SHAP explaining an adoption model does not explain a transaction classifier or a carbon calculator. **Always ask: which model, which output, and which question is being explained?**

### 4. A nice saved score is not a reproducible current release

A **trained artifact** is a saved fitted model or other learned object needed to use the trained system. A **manifest** is a packing list recording the files and identities associated with an experiment.

A file **hash** is like a digital fingerprint. Matching fingerprints mean the bytes match, not that the method is correct.

The earlier audit reported:

- 39 missing fitted-artifact paths;
- 10 missing processed files;
- 22 missing input files;
- a missing split CSV;
- four listed output files whose hashes did not match the manifest;
- 43 matching factor-file hashes after resolving their paths.

These are **reported audit observations**, not new checks executed for this walkthrough. Missing files could have various causes; mismatches do not prove cheating or leakage.

**The practical issue:** the saved evidence does not currently establish one complete experiment that someone else can replay against the current source.

## D. The basic ML workflow, without the jargon wall

### Features and labels

- A **feature** is an input clue: for example, past fuel spending.
- A **label** is the answer used to teach or evaluate a model: for example, whether adoption happened in a later window.
- **Training** adjusts the model using examples with known answers.
- **Inference** uses the fitted model to score a new example.

In GreenPath's synthetic demonstration, many examples and outcomes come from a simulator. Learning those examples is useful for testing the pipeline, but is not proof of learning real customer behavior.

### Train, validation, test, and release data

Think of a student preparing for an exam:

| Data group | Analogy | Purpose |
|---|---|---|
| Training | Practice problems | Fit the model |
| Validation | Mock exams | Choose models, settings, and score adjustments |
| Test | Final exam | Evaluate the frozen choices |
| Confidence release | A separate check for publishing confidence | Decide whether confidence outputs may be shown |

Repeatedly changing the model after looking at the final exam means it stops being a truly independent final exam.

GreenPath reserves a confidence-release group before fitting the relevant stages. But the remaining validation group is reused for several choices. That can make validation results look somewhat better than truly fresh results. It is a limitation to manage, not proof that test labels were used for training.

### Point-in-time features and leakage

**Leakage** is information sneaking into an experiment that would not legitimately be available when making the prediction.

Suppose the prediction date is March 31:

- A February transaction available in February can be a legitimate input.
- An April purchase cannot be a March input.
- A February record that only arrives in April is also unavailable on March 31.
- A field saying “customer adopted in April” would hand the model the answer.

This explains why GreenPath checks both **when something happened** and **when it became available**.

### Why missing is not zero

`0` electricity usage can mean “we observed it and it was zero.” Missing electricity usage means “we do not know.” Treating them as the same invents information.

This matters for both prediction and carbon arithmetic. Unknown evidence should not silently turn into a confident impact number.

---

## 1. Trendl: estimating emissions from spending

**Report section:** [Paper 1](Research%20paper%20integration%20assessment.md#1-trendl-et-al-transaction-spending-does-not-yet-yield-a-consumption-footprint).

### The paper's idea

Sort spending into consumption categories, then multiply each category's spending by a suitable emissions-per-pound estimate.

Imagine a price list with an extra column: “estimated emissions associated with each pound spent in this type of activity.” The paper builds a much more careful version of that idea.

Two intimidating terms:

- **COICOP:** a standard way of organizing household consumption categories.
- **MRIO:** multi-regional input-output accounting, which connects economic activity and supply chains across regions to estimate emissions associated with consumption.

You do not need to learn MRIO mathematics to understand the gap: **a physical factor measured in kg per kWh is not a monetary factor measured in kg per pound.**

### What GreenPath has, and what it lacks

**Has:** transaction categories, past-spending windows, and point-in-time customer summaries. These help prepare the inputs.

**Lacks:** the reviewed monetary factors, detailed consumption mappings, and accounting needed to turn those inputs into a defensible consumption footprint.

Why isn't debit spending enough? A debit might be a transfer, debt repayment, or purchase. A refund may reverse a purchase. Cash may not reveal what was bought. One account may cover only part of a household's spending.

### What implementing it would involve

Start with a separate footprint output. Obtain compatible, versioned factors. Map a narrow set of reviewed categories. Account for refunds, transfers, unmapped spending, and incomplete coverage. Test the totals by hand before expanding.

**Why it could help:** show where estimated consumption emissions are concentrated, not just where spending is high.

**Why it is deferred:** trustworthy factors, mappings, and coverage are substantial dependencies. Multiplication is the easy part.

**Remember:** we have ingredients for categorizing spending, not a completed spending-to-footprint engine.

## 2. Manokhin and Grønhaug: making probability numbers more honest

**Report section:** [Paper 2](Research%20paper%20integration%20assessment.md#2-manokhin-and-grønhaug-calibration-exists-but-its-benefits-are-mixed).

### The paper's idea

A model can rank people reasonably well while its probability numbers are misleading. **Calibration** adjusts those numbers after model fitting.

Imagine a weather app saying “70% chance of rain” on many days. If it rains on roughly 70% of comparable days with that prediction, the forecasts are well calibrated. You cannot establish calibration from one day or one customer.

GreenPath has four separate yes/no adoption tasks. They are not a single choice where exactly one product must win. A customer could adopt more than one product.

### What GreenPath has

- **Platt/sigmoid calibration:** learns a smooth adjustment to model scores.
- **Isotonic calibration:** learns a flexible, non-decreasing adjustment.
- A small-sample policy: automatic isotonic needs at least 50 examples in **each** class; otherwise Platt is used.

All four saved core models use logistic regression plus Platt. The saved validation sets have only 10–17 positives, so there is limited information for learning a flexible adjustment.

### Why “improved calibration” is not one simple yes/no

The report compares two measurements:

- **Brier score:** average squared error of the predicted probabilities against 0/1 outcomes. Lower is better; it captures more than calibration alone.
- **ECE:** groups predictions into bins and compares average predicted probability with observed frequency. Lower is better, but the result depends on the bins and sample size.

The saved results show lower ECE for every product, but slightly worse Brier for EV and Green Home. Solar and Paperless improve on both listed measures.

So the honest conclusion is **“the measured benefits are mixed,”** not “calibration made every probability better.”

### What should happen next

Compare the same model with no adjustment and with candidate adjustments. Add **log-loss**, which strongly penalizes confidently wrong probabilities. Improve independence between tuning and calibration without splitting already small groups into unusable pieces.

Beta and Venn–Abers are additional methods to investigate, not magic upgrades you need to memorize or install now.

**Why it could help:** judges can see that probability quality is checked rather than assumed.

**Remember:** calibration tries to make score numbers honest. It does not prove eligibility, cause adoption, or automatically unlock suppressed correctness confidence.

## 3. Lundberg: explaining one prediction versus understanding the whole model

**Report section:** [Paper 3](Research%20paper%20integration%20assessment.md#3-lundberg-et-al-local-shap-is-real-global-understanding-is-still-missing).

### The paper's idea

**SHAP** assigns portions of a model's output to its input features, relative to a defined baseline. Think of a score receipt: “start here; these clues pushed the score up; these others pushed it down.”

- **Local explanation:** one customer's score receipt.
- **Global explanation:** patterns across many customers' receipts.

The paper develops exact Tree SHAP and shows how local explanations support broader understanding of tree models.

### What GreenPath has

There is an exact tree-attribution path for an XGBoost model, and a linear-attribution path for logistic regression. **All four saved selected models are logistic**, so their saved explanations demonstrate the linear path, not four deployed tree models.

The code checks that:

```text
baseline + all feature contributions = raw model score
```

The output being explained is **raw, uncalibrated log-odds**. Log-odds are a score scale that converts nonlinearly to probabilities. You do not need the conversion formula here; you do need to know that adding 1 on this scale is not adding 1 percentage point.

**Made-up score receipt:**

```text
Baseline:              -1.0
Fuel-spending clue:    +0.4
Another clue:          -0.2
Final raw score:        -0.8
```

Those contributions add up on the raw scale. They do not mean “fuel spending adds 40 percentage points of adoption probability.” Calibration adds another transformation afterward.

### What is missing, and what would help

GreenPath lacks global SHAP summaries and the paper's broader analyses. A bounded next step is to aggregate explanations for a clearly identified cohort and show which features usually matter most.

For example, **mean absolute SHAP** averages contribution magnitudes: a feature can matter a lot whether it pushes scores up or down. Signed views are still needed to see direction.

Also, the report says the existing user-facing reason ordering is not the full SHAP audit. Finding SHAP in the code does not mean every displayed reason is already a complete SHAP explanation.

**Why it could help:** make the selected model's behavior visible and checkable across customers.

**Remember:** SHAP explains the chosen model on a specified scale. “Exact” does not mean causal, fair, or a perfect picture of reality.

## 4. González-González: explaining why a payment received its category

**Report section:** [Paper 4](Research%20paper%20integration%20assessment.md#4-gonzález-gonzález-et-al-transaction-explanations-require-a-separate-attribution-path).

### The paper's idea

This paper asks a different explanation question: **“Which words made the system classify this transaction this way?”** It also explores estimating physical activity from payment amounts and prices.

Its explanation method includes **LIME**: change parts of the input, observe how predictions change, and fit a simple nearby approximation. That approximation must be checked for how faithfully it represents the actual prediction behavior.

### What GreenPath has, and what it lacks

**Has:** normalized transaction text, routing rules, and a supervised text classifier.

**Lacks:** a dedicated output showing the actual matched rule or token contributions, merchant-enriched explanations, and the paper's transaction-price-based activity estimator.

For `ROADSTOP FUEL`, a useful explanation would say whether a fuel rule fired or which text features influenced the fallback model. An adoption-model SHAP explanation cannot answer that transaction question.

Important detail: a rule's displayed confidence of `1.0` is currently a deterministic convention. It does **not** mean “verified 100% correct in real life.”

### What implementing it would involve

Expose the actual route and matched rule first. Then explain the real fallback model's text features, including whether evidence favors one category over another. Evaluate on independently reviewed unfamiliar merchants.

The report favors this small audit before a larger carbon extension.

For a price-based activity estimate, the basic idea is:

```text
payment / unit price = estimated quantity
estimated quantity × physical factor = estimated emissions
```

But a bill may include taxes, standing charges, several services, or changing prices. Unknown quantity should not become a confident litre or kWh estimate. Water litres are also not automatically carbon emissions.

**Why it could help:** trace an error from transaction wording to category to the spending feature used downstream.

**Remember:** explaining a category is a separate job from explaining product adoption. A plausible explanation can still accompany a wrong category.

## 5. Zytek / Explingo: turning model explanations into readable language

**Report section:** [Paper 5](Research%20paper%20integration%20assessment.md#5-zytek-et-al-grounded-sentence-ordering-is-not-deployed-explingo-narration).

### The paper's idea

Give a language model structured prediction explanations, including SHAP contributions, and ask it to explain them in ordinary language. Evaluate the explanation separately for correctness, completeness, and readability.

This is like asking a storyteller to explain a score receipt, then asking a checker whether the story accurately covers the receipt.

### What GreenPath actually does

GreenPath is more constrained:

1. The server creates approved sentences.
2. The optional LLM can propose their ordering.
3. The service validates the complete set and reconstructs accepted text locally.
4. Bad, missing, invented, or timed-out responses trigger deterministic fallback.

Think of **rearranging approved index cards**, not writing a new essay.

That is a sensible safety choice. However, it is not full Explingo-style SHAP narration, and there is no established independent narrative grader or live-provider quality study in the assessment.

### How to read the saved evaluation

The report describes 200 passing offline fixture cases, including deliberately invalid responses. The saved fallback rate is 0.63: 63% of those cases used fallback.

This tests whether the final system preserves approved claims under those fixtures. It does not show that a live LLM produces great explanations or “never hallucinates.” Safe final text can result from rejecting a bad provider response.

### What should happen next

First connect explanations to faithful selected-model attribution. Then compare template-only explanations with optional ordering using independent reviewers and held-out cases.

Ask: did users understand the message better without losing correctness? If not, the simpler template may be enough.

**Why it could help:** establish whether the language component adds understandable value rather than merely adding an “AI” label.

**Remember:** a safety guard working is not the same result as a narrator being useful. Both require their own evidence.

## 6. Assefa: fake data can be useful without being real-world proof

**Report section:** [Paper 6](Research%20paper%20integration%20assessment.md#6-assefa-et-al-mechanistic-simulation-already-meets-the-proportionate-lesson).

### The paper's idea

This is a review of synthetic financial data: why people generate it, how to evaluate it, and what can go wrong. It does not say every project needs a GAN or another particular generator.

Imagine a toy town with invented people, bills, and purchase decisions. It is useful for testing a delivery system. But success in the toy town does not prove success in a real city.

### What GreenPath has

GreenPath uses a **mechanistic simulator**: authored rules, coefficients, randomness, and relationships generate linked customer data and outcomes.

Some public energy statistics anchor selected quantities. A **seed** helps reproduce the random experiment. The declared provenance says no real confidential customer rows are used.

This is useful for a shareable demonstration. It is not a GAN trained on bank records, and there is no requirement to replace it with one.

### What remains unproven

Matching a few public averages does not establish realistic joint behavior. Two datasets can have the same average electricity use but very different relationships between income, housing, and adoption.

Also, the simulator authors the outcome mechanism. A model performing well on it may have learned the toy world's rules, not actual bank behavior.

**Differential privacy (DP)** is a formal protection limiting how much a released result reveals about an individual's participation. “Synthetic” alone does not provide that protection. The declared no-private-row simulator does not establish a DP guarantee, nor does it need a cosmetic DP claim.

### What should happen next

Document what is authored, what is publicly anchored, and what the simulator is suitable for. Check logical consistency and stress cases. Only claim real-world fidelity after comparison with appropriately sourced independent real data.

**Why it could help:** make the demo honest, reproducible, and easier to inspect.

**Remember:** synthetic data is a useful testing environment, not a certificate of realism, privacy, fairness, or business success.

## 7. Busson: categories arranged like a family tree

**Report section:** [Paper 7](Research%20paper%20integration%20assessment.md#7-busson-et-al-flat-routing-does-not-implement-a-hierarchy).

### The paper's idea

A **hierarchy** has broad categories and narrower child categories. For example, an illustrative taxonomy might be:

```text
Transport
    Fuel
    Public transport

Home
    Utilities
    Home improvement
```

These are illustrative labels, not GreenPath's approved taxonomy. A hierarchy-aware system should not emit `Home -> Fuel` when Fuel belongs under Transport.

The paper combines merchant-name and business-activity text, predicts broad and narrow categories, and blocks incompatible child predictions.

### What GreenPath has, and what it lacks

GreenPath currently outputs one of eight flat categories. It does not have approved parent-child relationships or the paper's two-input context-fusion model.

Rules followed by a classifier are multiple processing steps, **not automatically a category hierarchy**.

### What implementing it would involve

Agree the category tree first. Obtain legitimate activity descriptions and independently reviewed labels. Then compare a constrained parent-child challenger against the current flat system while preserving existing spending-feature meanings.

Do not generate activity text from the true category and then feed it to the model. That would be like handing a student a description containing the exam answer.

**Why it could help:** support coherent broad spending totals and prevent impossible category combinations.

**The catch:** a valid pair can still be wrong. `Transport -> Fuel` is consistent, but not correct if the payment was actually for groceries.

**Remember:** hierarchy improves the structure of predictions; accuracy still needs independent labels and evaluation.

## 8. Kapoor and Narayanan: do not accidentally peek at the answers

**Report section:** [Paper 8](Research%20paper%20integration%20assessment.md#8-kapoor-and-narayanan-strong-leakage-controls-need-a-complete-evidence-argument).

### The paper's idea

ML results can look impressive because of accidental answer-sharing or an unrealistic test setup. The paper organizes these problems and asks teams to explain why their experiment is legitimate.

This goes beyond “the code ran” or “we used a seed.”

### The eight leakage concerns, translated

| Concern in the report | Everyday explanation |
|---|---|
| No test set | Only checking practice exercises |
| Contaminated preprocessing | Letting final-exam examples influence how inputs are prepared |
| Contaminated selection | Choosing settings by looking at final-exam answers |
| Duplicates | The same or almost identical case appears in practice and the exam |
| Illegitimate features | Giving the model an answer clue it should not have |
| Temporal leakage | Using information from the future or unavailable at prediction time |
| Dependent samples | Closely related cases on both sides make the exam easier than deployment |
| Biased test distribution | Testing on a population unlike the one you claim to serve |

### What GreenPath does well

The assessment found customer-level separation, train-fitted preprocessing, input allowlists, point-in-time controls, later outcome windows, merchant-group benchmarks, and stress diagnostics.

These are meaningful controls. But a source-level control is not a guarantee against every possible leakage route.

### What is still needed

A model info sheet should explain where each input comes from, why it is available and legitimate, which data fitted each stage, and which population the test supports.

The evidence bundle should preserve the actual inputs, split identities, fitted models, environment, and final reports. The manifest needs to reflect the final outputs, not earlier versions subsequently rewritten by evaluators.

Testing should also check **noninterference**: changing test answers must not change a fitted model. Changing release-check data may change whether confidence is shown, but must not change the fitted artifacts.

**Why it could help:** let judges follow the experiment rather than accept impressive numbers on faith.

**Remember:** the assessment did not establish direct training on test labels. Missing evidence and validation reuse are limitations, not proof of cheating.

## 9. Toran: learning from several imperfect labeling helpers

**Report section:** [Paper 9](Research%20paper%20integration%20assessment.md#9-toran-et-al-deterministic-rules-do-not-generate-probabilistic-weak-labels).

### The paper's idea

Labeling every transaction by hand is expensive. **Weak supervision** combines imperfect labeling clues to create training targets.

Imagine several helpers:

- Helper A: “The description mentions fuel, so I vote FUEL.”
- Helper B: “The merchant pattern suggests UTILITIES.”
- Helper C: “I have no useful clue, so I abstain.”

A **labeling function (LF)** is one such helper. A probabilistic label model handles their votes and uncertainty. A learner then trains using the resulting weak targets.

```text
Several imperfect labeling functions
    -> votes / abstentions / conflicts
    -> probabilistic label model
    -> weak training targets
    -> transaction learner
```

### Why GreenPath's current rules are not this

GreenPath's rules assign final categories; cases without a rule hit go to a supervised classifier. Training labels come from a synthetic labeled reference.

That is a useful hybrid, but it has no probabilistic LF aggregation stage. “A rule followed by a learner” is not the same pipeline as “several rule votes combined into training labels.”

### What the saved results warn us about

The saved synthetic categorisation results show macro F1 of about **0.992 for known merchants** versus **0.529 for unseen merchants**. Some unseen categories have weak or absent support.

**Macro F1** gives each category equal weight when averaging its F1 score. F1 combines how often positive predictions are correct (**precision**) with how many true cases are found (**recall**).

These numbers are not accuracy percentages. Their main lesson is that familiar merchants are much easier in this saved experiment. They do not measure performance on real bank data.

### What should happen next

Create a **gold set**: independently reviewed realistic labels. Keep its test portion out of rule writing and training. Measure LF coverage, conflicts, and correlations, then compare a simple weak-label learner with the current baseline on the same untouched merchants.

Two helpers copying the same clue are not two independent witnesses. A label model must not blindly count duplicated evidence twice.

**Why it could help:** potentially reduce manual labeling effort and improve unfamiliar-merchant coverage, if the clues and data actually support that.

**Remember:** a real gold set comes first. Renaming simulator truth “weak labels” would not demonstrate weak supervision.

## 10. Grinsztajn and colleagues: choose the model for the job, not the buzzword

**Report section:** [Paper 10](Research%20paper%20integration%20assessment.md#10-grinsztajn-oyallon-and-varoquaux-use-fair-local-comparisons-not-novelty).

### The paper's idea

For many medium-sized datasets arranged in rows and columns, tree models can outperform the neural networks studied in the benchmark. Bigger and more fashionable is not automatically better.

The claim is not “trees always win.” Different datasets, inputs, and evaluation setups can change the result.

### GreenPath's model choices

- **Heuristic:** an authored scoring rule used as a baseline.
- **Logistic regression:** combines weighted input clues and converts the result to a binary-task probability.
- **XGBoost:** combines many trees, with later trees correcting errors in the accumulated model.

All four saved core selections are logistic. The comparison tests four logistic settings but only one XGBoost setting, so it is not an equal-tuning-budget contest.

Also, `XGBoost` with histogram-based tree construction is not scikit-learn's separate `HistGradientBoosting` learner. The report identifies documentation naming mismatches, not a newly observed training failure.

### Why the “best model” depends on the goal

Suppose an RM can contact only the highest-ranked 10% of customers.

- **ROC-AUC:** summarizes ordering across thresholds, rather than just the top contact list.
- **Precision@10%:** the fraction of actual positives in that top 10% list.
- **Lift@10%:** how that fraction compares with the overall positive rate.

For saved EV test results, logistic has higher ROC-AUC, while XGBoost has higher Precision@10%. That suggests asking which objective matters for future validation.

It does **not** justify switching now based on the test results. That would turn the final exam into another model-selection tool.

**Toy illustration:** if the overall adoption rate is 10%, and 30% of the top contact list adopted, lift is 3. This describes concentration of recorded positives, not proof that contacting them caused adoption.

### What should happen next

Choose the primary objective before evaluation. Run a bounded, fairly documented challenger comparison on train/validation, freeze choices, then use an untouched test set.

Keep logistic if it earns the role. Add a neural model only when there is a concrete reason and a suitable evaluation budget.

**Why it could help:** align model choice with the RM's limited contact capacity rather than a generic headline metric.

**Remember:** higher ranking scores in a synthetic experiment do not prove more sales, revenue, or real carbon savings.

---

## E. What the roadmap means in ordinary language

**You do not need to build everything.** Priority reflects readiness, usefulness, and risk, not the importance of the paper's authors.

| Priority | Plain meaning | Typical work |
|---|---|---|
| P0 | “Make the demo's evidence and claims trustworthy first.” | Recover replay files, reconcile final hashes, identify actual models, explain what is and is not demonstrated |
| P1 | “Add useful visibility using the parts we already have.” | Show transaction rule evidence, global SHAP summaries, calibration comparisons, and uncertainty in ranking results |
| P2 | “Try bounded alternatives when the data and experiment are ready.” | Additional calibrators, fair XGBoost tuning, independent explanation reviews, early hierarchy or weak-supervision challengers |
| P3 | “Do not rush large research extensions.” | Full monetary footprint accounting, faithful deep architectures, free-form narration, or private-data synthesis studies |

### Why evidence comes before another model

If the current score cannot be traced to a preserved dataset and fitted model, a new higher score does not solve the main problem. It just adds another number with uncertain provenance.

Think **“label the ingredients and preserve the recipe before claiming a better cake.”**

### Why several papers share the same next step

| Shared foundation | What it unlocks |
|---|---|
| Independently reviewed merchant examples | Meaningful transaction explanations, hierarchy, and weak-supervision evaluation |
| Stable category definitions | Consistent spending summaries and future footprint mappings |
| Preserved selected-model identity and explanation scale | SHAP summaries and faithful language explanations |
| Independent data boundaries | Honest calibration, model comparisons, and confidence-release decisions |
| Clear physical evidence and coverage | Defensible scenario arithmetic without inventing missing activity |

These are not ten unrelated to-do lists. One good foundation can support several paper-inspired improvements.

### A non-ML detail that still matters: annual energy coverage

The report flags a static concern: a month can count as covered if either gas or electricity exists, while each fuel is annualized separately.

Imagine having 12 months of gas but only one month of electricity. A shared “12 months covered” indicator does not prove 12 observed electricity months. Scaling one electricity month into a year also needs to be clearly described as extrapolation, not measured annual use.

The proposal is to track each fuel's coverage separately and test such cases. **This is an inspection concern, not a newly reproduced runtime bug.** It matters because fancy ML cannot repair unsupported physical inputs.

### Probability times potential saving is only a planning score

The roadmap also warns about multiplying propensity by physical potential.

**Toy arithmetic:** `0.4 estimated adoption probability × 100 kg potential saving = 40 kg` as a planning quantity.

That is not 40 kg already saved. The calculation does not establish that the bank caused adoption, that the scenario will occur, or that all factor uncertainty is accounted for. It is not a transaction footprint either.

## F. How to read the dense sections without getting lost

For each paper in the original, follow this order:

1. **Actual contribution:** What exact problem did the paper solve?
2. **Verdict:** Does GreenPath solve that same problem using its defining mechanism?
3. **Implemented aspects:** Which real building blocks are present?
4. **Missing mechanisms:** What prevents the stronger claim?
5. **Staged plan:** What is the smallest sensible step, and what depends on data or review?
6. **Acceptance:** What would count as evidence that the step works?
7. **Payoff and limits:** Why might it help, and what still cannot be claimed?

You can skip proposed filenames on your first read. They identify where future work might live; they are not files this assessment created or features already completed.

Whenever you see a metric, ask:

> **On which data? For which task? From which saved run? Compared with what? Was the difference independently tested?**

### A few remaining terms translated

| Term | Meaning |
|---|---|
| TF-IDF | Converts words or character chunks into numeric features, weighting how informative they are across documents |
| Binary / multiclass | Two possible outcomes / several possible category labels |
| Cross-fitting / OOF | Producing predictions for rows using a model fitted without those rows; the whole relevant selection procedure must respect the boundary |
| Holdout / cohort | Reserved evaluation examples / a defined group of examples |
| Ablation | Remove or replace one component to see what difference it makes |
| Identity calibration | Leave the probabilities unchanged; an important comparison baseline |
| Support | How many examples a reported category or result is based on |
| Bootstrap | Repeatedly resample evaluation units to estimate uncertainty; resample customers or merchants appropriately, not blindly every row |
| Paired comparison | Evaluate alternatives on the same cases, so case difficulty is shared |
| Distribution shift / OOD | Inputs differ from training conditions / a case appears outside the modeled training pattern |
| Contract | A precise agreement about fields, meanings, units, and allowed unavailable states |
| Provenance | The record of where data and results came from and how they were produced |
| Frozen comparison | Choices are locked before the final evaluation |
| Lifecycle / additionality | Emissions across broader stages of an activity / whether an intervention caused a change beyond what would have happened anyway |

## G. The safest way to describe GreenPath to judges

Here is a plain-language version of the report's defensible wording:

> GreenPath is a synthetic demonstration that helps identify sustainable-product opportunities. It includes time-aware customer information, transaction categorisation, adoption models, probability calibration, and local model explanations. A separate calculator estimates physical emissions differences for explicit scenarios. The optional LLM arranges approved sentences rather than freely inventing explanations. Saved results have limitations, correctness-confidence outputs remain suppressed, and a complete current-run replay has not been established. The papers guide improvements; we have not fully reproduced all ten methods or demonstrated real-bank outcomes.

### Common statements to catch yourself making

| Tempting statement | More accurate version |
|---|---|
| “We implemented all the papers.” | “We assessed all ten and identified existing alignment and specific gaps.” |
| “Our SHAP shows why someone will adopt.” | “It shows which inputs influenced this model's raw score.” |
| “Our confidence is 100% because a rule matched.” | “A deterministic route matched; real correctness is not guaranteed.” |
| “Our carbon number is the customer's footprint.” | “This is a potential physical scenario difference, not a consumption inventory.” |
| “The LLM passed, so it never hallucinates.” | “Offline fixtures tested safe final output, including fallback.” |
| “Synthetic accuracy means it will work at a bank.” | “It demonstrates performance under the simulator's conditions.” |
| “The new approach will improve results.” | “It is a candidate benefit that still needs an independent comparison.” |

## H. Check your understanding

1. **A fuel payment was correctly categorized. Do we now know litres bought?** No. We need activity evidence or a justified price-based estimate.
2. **An adoption probability is 0.8. Is the customer eligible?** Not established; eligibility is a separate question.
3. **SHAP adds up exactly. Does that prove the model is correct?** No. It shows the attribution adds up for that model and defined output.
4. **Every parent-child pair is valid. Are all transaction labels right?** No. Structural consistency is not accuracy.
5. **A model does well on a new simulator seed. Is that real-world validation?** No. It is another test within simulated conditions.
6. **A saved report and its manifest hash differ. Has leakage been proven?** No. Evidence consistency needs investigation; the cause is not established.
7. **Calibration is implemented. Should every product's probabilities improve?** No. The saved comparison is mixed; measure each case against no calibration.
8. **What should we prioritize before adding a deep network?** A coherent evidence bundle, independent evaluation inputs, and clear claims.

## Final takeaway

**The report is asking us to make the project easier to trust, not more complicated for its own sake.**

Know which question each component answers. Separate source code, saved evidence, and future plans. Keep explanations faithful, data boundaries independent, and carbon units clear. Then add complexity only when a fair comparison shows it helps.
