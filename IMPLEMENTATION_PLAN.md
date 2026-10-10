# GreenPath Intelligence — MVP Implementation Plan

**Status:** Proposed plan  
**Basis:** `GreenPath_PS1_Master_MVP_v2.md`  
**Workspace state:** Greenfield; the specification is present, but no application code or project scaffold exists yet.

## 1. MVP outcome

Deliver a reproducible, five-minute demo of GreenPath that:

1. Builds a customer view from seeded synthetic data and categorized transactions.
2. Scores the four required opportunities: EV Finance, Green Home, Solar Finance, and Paperless Banking.
3. Explains each result with evidence, data quality, version information, and a clear recommendation state—including abstention when evidence is missing or conflicting.
4. Computes sustainability impact only through versioned, deterministic formulas with named sources and assumptions.
5. Shows a customer recommendation/“Why?” view and a business portfolio view with regional, segment, and time-trend summaries.
6. Works without an LLM key; a grounded LLM explanation is an optional adapter behind a deterministic template fallback.

The prototype uses synthetic data and must be presented as a demonstration, not evidence of real-world predictive performance or financial eligibility.

## 2. Architecture and non-negotiable boundaries

Build a **modular monolith**, not microservices. Proposed fast-demo stack:

- Python 3.12, Pydantic contracts, and FastAPI for the service/API boundary (also compatible with the shortlisted SHAP skill’s declared Python minimum).
- Streamlit and Plotly for customer and portfolio screens.
- pandas and scikit-learn for data processing and baseline models; add a boosted-tree implementation only when it is easy to reproduce and earns its complexity.
- SQLite plus versioned local data/model artifacts for demo persistence.
- A pinned dependency lockfile and `make` targets for setup, tests, training/evaluation, and app startup.

Keep these responsibilities separate:

- **Propensity models** estimate customer interest; they do not estimate impact or eligibility.
- **Impact calculators** are deterministic, independently testable, and return provenance with every result.
- **Recommendation rules** decide relevance, conflicts, and abstention; they do not make credit decisions.
- **LLM explanations** receive only validated structured recommendation data. They cannot create reasons/numbers, alter scores, calculate impact, or claim eligibility. Validate output and fall back to a deterministic template on any failure.
- Raw merchant descriptions never enter the LLM prompt.

## 3. SOLID design rules

Apply SOLID at the seams where the hackathon is likely to iterate; avoid adding abstractions that have no second implementation or variation point.

- **Single Responsibility:** keep data preparation, each product’s impact calculation, recommendation rules, explanation, API transport, and UI rendering in separate modules.
- **Open/Closed:** register product-specific predictors and impact calculators behind small protocols; adding a product should not require extending a large `if product == ...` block.
- **Liskov Substitution:** every product calculator returns the same `ImpactResult` contract, including an explicit unavailable state when inputs are insufficient.
- **Interface Segregation:** use narrow ports such as `CustomerSnapshotProvider`, `PropensityProvider`, `ImpactCalculator`, and `ExplanationProvider`, rather than one all-purpose service interface.
- **Dependency Inversion:** use cases depend on those contracts; concrete models, storage, LLM clients, and UI frameworks are injected at the application boundary. Keep Streamlit/FastAPI imports out of the domain and ML modules.

Use functions and data classes/Pydantic models where they make the boundary clearer; SOLID does not require a class hierarchy for every function.

## 4. Contract-first handoff (before parallel work)

There is no destination project repository yet, so do not create a shared scaffold or ask either agent to merge branches. Before assigning the work, freeze the contracts and representative JSON fixtures below as the common handoff specification. Both agents work in their own repositories, using the same package paths, Python version, and contract definitions. This keeps their code independently runnable while making later manual transfer predictable.

Suggested structure:

```text
src/greenpath/
  contracts/       # shared, versioned Pydantic input/output schemas
  ports.py         # narrow protocols for cross-workstream dependencies
  data_generation/
  pipelines/
  models/
  trust/
  confidence/
  impact/
  recommendation/
  llm/
  api/
  app/
tests/
  contracts/ data/ ml/ impact/ recommendation/ api/ scenarios/
data/              # generated demo data; no real customer data
reports/
```

Freeze at least these contracts:

- `CustomerSnapshot`: customer ID, feature cutoff, approved feature values, and data-quality evidence.
- `PropensityResult`: product, calibrated probability, model/calibration versions, reason codes, and optional validated confidence.
- `TrustAssessment`: score/status plus specific completeness, freshness, conflict, and OOD issues; keep Trust distinct from model confidence.
- `ImpactResult`: status, value and units, baseline/scenario, factor IDs/source/version, boundary, assumptions, method version, and timestamp.
- `Recommendation`: product, propensity, state (`RECOMMEND`, `DO_NOT_RECOMMEND`, `INSUFFICIENT_INFORMATION`, `CONFLICT_REQUIRES_REVIEW`, `NOT_APPLICABLE`, or `SUPPRESSED`), evidence/reason codes, exclusions, impact, and provenance.
- `Explanation` and portfolio summary/trend responses for the API/UI.

Each agent should include the fixtures and the fake providers needed to run its own tests. Agent A owns the canonical `contracts/` and `ports.py` implementations. Agent B may use local contract-compatible test stubs to keep its repository runnable, but must label them as mirrors and list them as replaceable at manual integration; do not treat the two copies as separate contract authorities.

## 5. Parallel workstreams and ownership

Both agents build independently in their own repositories. Keep source ownership disjoint and follow the frozen contract handoff; do not assume access to the other agent’s files or repository.

| Workstream | Owns | Deliverables / acceptance |
|---|---|---|
| **Agent A — Data, ML, and reliability** | `data_generation/`, `pipelines/`, `models/`, `trust/`, `confidence/`, ML/data evaluation modules and their tests/reports | Seeded stochastic synthetic-data generator; schema and leakage checks; customer-level and temporal splits; Customer 360; merchant normalization/rules plus TF-IDF classifier; heuristic and logistic baselines for all four products; calibrated probabilities; optional main model comparison; trust/confidence/OOD diagnostics; held-out predictions and reproducible evaluation artifacts. Implements `CustomerSnapshotProvider` and `PropensityProvider` ports. |
| **Agent B — Product decisioning and demo experience** | `impact/`, `recommendation/`, `llm/`, `api/`, `app/`, carbon/LLM/scenario evaluation modules and their tests | Four product-specific deterministic impact calculators and provenance; relevance rules, conflicts, reason mapping, and fail-closed abstention; structured explanation adapter with grounding checks and template fallback; FastAPI routes; Streamlit customer/“Why?” and portfolio/trend screens. Uses the frozen contracts and local fake providers in its own repository. |
| **You — later manual integration** | Destination repository (when available) | Manually move the owned modules from both repositories, retain Agent A’s canonical contracts, replace Agent B’s local contract mirrors, reconcile project configuration/dependencies, and run the full end-to-end gate. No agent is asked to merge repositories or branches. |

### Agent A implementation sequence

1. Generate synthetic outcomes from multiple latent drivers, interactions, and random noise. Do not encode labels as direct thresholds on the same features used for training. Save fixed seeds and generator configuration.
2. Validate schemas, event-time cutoffs, customer split integrity, target leakage, and post-adoption features. Keep audit-only/protected attributes out of the propensity feature view.
3. Build Customer 360 and transaction categorization: deterministic high-confidence merchant rules first, then TF-IDF + logistic classification for unresolved merchants. Evaluate with a merchant-group holdout, not only a random row split.
4. Train one product-specific heuristic baseline and logistic regression baseline per opportunity. Compare a simple boosted model only if the result is reproducible and useful; report honestly when a baseline is as good or better.
5. Fit probability calibration on validation data only. Evaluate on held-out customers and a perturbed generator; report the specification’s ranking, calibration, lift, missingness, and subgroup metrics.
6. Assess trust and OOD separately from confidence. Surface confidence only if its held-out reliability checks show higher-confidence buckets have materially lower empirical error; otherwise suppress the confidence display and record the limitation.

### Agent B implementation sequence

**Progress, 2026-10-10:** Point 1 is complete in [`CARBON_METHODS.md`](CARBON_METHODS.md) and the versioned [factor catalogue](src/greenpath/impact/factors/carbon_factors.v1.json). These freeze the synthetic India demo methods, source editions, boundaries, assumptions, and unavailable conditions. CEA's original PDF currently redirects to login; its official indexed table and that access limitation are recorded. Paperless carbon impact remains unavailable. Calculator implementation and contract reconciliation remain subsequent work.

1. Freeze carbon-method sources, factor edition, system boundaries, and assumptions in `CARBON_METHODS.md`. Do not invent factors. If required inputs or a defensible factor are missing, return `UNAVAILABLE` rather than a fabricated estimate.
2. Implement EV, Green Home, Solar, and Paperless impact calculators as separate modules with the common `ImpactResult` contract and formula/unit tests. Keep the headline EV boundary consistent; label exclusions and estimated inputs.
3. Implement recommendation state transitions and product-specific relevance guardrails. Add deterministic conflict and abstention tests; never turn a relevance signal into an eligibility decision.
4. Implement explanation generation behind a port. Validate structured output and numeric/reason/product claims against approved fields; include adversarial cases. The app must remain fully usable with the template fallback and no API credentials.
5. Implement API endpoints for customer, opportunities/recommendations, portfolio summary/trends, explanation, and health. UI calls the API rather than importing model/impact internals.
6. Build the customer card and “Why?” details plus portfolio product/segment/region/monthly-trend views. Use stable fixture IDs and demo personas, including one responsible abstention case. RM workspace and optional features are deferred.

## 6. Independent build and later manual integration

1. **Before dispatch:** freeze this plan’s shared schemas, field meanings, enum values, package paths, and example fixtures. Send the same contract version to both agents.
2. **Independent builds:** each agent creates and tests its own repository. Agent A owns the canonical contract implementation; Agent B uses the written contract and clearly marked local mirrors/fakes where needed. Neither agent needs the other’s repository.
3. **Handoff from each agent:** request a concise manifest of owned source files, tests, generated artifacts, setup/run commands, dependency versions, environment variables, known limitations, and any deviations from the contract. Require scoped tests to pass in that agent’s repository.
4. **Manual transfer by you:** when the destination repository exists and both builds are complete, copy Agent A’s data/ML/reliability modules and canonical contracts, then copy Agent B’s impact/recommendation/LLM/API/UI modules. Replace Agent B’s contract mirrors with Agent A’s canonical contracts and reconcile imports, dependency pins, configuration, and entry points. Agents are not asked to merge anything.
5. **Post-transfer integration:** run the one-command pipeline, full test suite, API smoke tests, and five-minute demo from a clean environment. Add/fix integration tests in the destination repository after transfer.
6. **Freeze:** do not move optional features into the destination app unless all MVP acceptance criteria pass after manual integration.

**Contract-change exception:** if an agent discovers a necessary contract gap, have them document the proposed field/enum/interface change instead of silently changing the shared contract. Agree on the revised contract and give the same version to both agents; update local implementations as needed. Record deviations in each handoff manifest so you can reconcile them during manual transfer.

## 7. Delivery gates and MVP acceptance

### Gate 0 — runnable foundation

- Clean setup and pinned dependencies.
- Contract and fixture tests pass.
- `make test` and `make app` exist; no secrets required for the default path.

### Gate 1 — data and model evidence

- One reproducible command generates/prepares data, creates customer-level splits, trains/calibrates, evaluates, and writes held-out predictions.
- Leakage and temporal-cutoff tests fail on deliberately invalid examples.
- Transaction categorization has known/unseen merchant evaluation.
- Each of the four opportunity models is compared with both heuristic and logistic baselines, with generator-shift and missing-data diagnostics.
- Synthetic-data results are clearly labeled; no claim that they establish real-world performance.

### Gate 2 — safe recommendation and impact

- All six recommendation states are represented by tests or scenario fixtures.
- Missing critical evidence and high-severity conflicts fail closed.
- Impact formulas have units/boundary/source/version and deterministic unit tests; unavailable inputs return an explicit unavailable result.
- Propensity, impact, confidence, Trust, and eligibility are not conflated.

### Gate 3 — complete customer and portfolio experience

- A demo customer can inspect the recommendation, evidence, cutoff, uncertainty/limitations, impact assumptions, and eligibility disclaimer.
- Portfolio page shows product opportunities and regional, segment, and monthly trend summaries.
- A no-recommendation/abstention persona is demoable; a recommendation is never the only successful state.

### Gate 4 — explanation and reproducibility

- LLM path is version-pinned/configured and receives only validated structured facts; output schema and grounding checks run before display.
- Failure, unsupported numbers/reasons, or unsafe eligibility language selects the deterministic fallback.
- Fixed adversarial evaluation cases are included; report groundedness, numeric consistency, unsupported claims, fallback rate, latency, and cost if a live provider is enabled.
- `make all` runs data preparation, training/evaluation, impact and scenario tests, and held-out artifact generation from a clean environment.

### Scope protection

Complete the specification’s MUST items before relationship-manager workspace, what-if/sensitivity tools, memory/lifecycle, optimizer, optional products, or advanced governance UI. Do not expose confidence if validation fails. Do not show an impact number when the input/factor basis is inadequate.

## 8. Agent-skill recommendations

An inspect-only scout checked current public skill repositories. These are contributor instructions, not runtime ML libraries. The best fit is a **small audited subset**, not a general-purpose “ML agent” bundle.

| Priority | Skill and source | GreenPath use | Maintenance evidence and caveat |
|---|---|---|---|
| **Adopt for Agent A** | [K-Dense `scikit-learn`](https://github.com/K-Dense-AI/scientific-agent-skills/tree/main/skills/scikit-learn) | Preprocessing, TF-IDF categorization, logistic baselines, pipelines, grouped evaluation. | Skill v1.5; reviewed 2026-10-01; includes tests for training-only preprocessing statistics, text pipelines, and unseen categories. Third-party rather than sklearn-maintained. Adapt examples to customer/merchant/time splits and GreenPath’s proxy-feature policy; do not copy conflicting demo feature choices or unneeded citation instructions. |
| **Adopt for Agent A’s audit path** | [K-Dense `shap`](https://github.com/K-Dense-AI/scientific-agent-skills/tree/main/skills/shap) | Auditor/model-view feature explanations and SHAP correctness. | Skill v2.3; reviewed 2026-10-01; contract tests check additivity and output semantics. Declares SHAP 0.52.0 / Python ≥3.12. SHAP on raw model output does not automatically explain calibrated probabilities; keep customer-facing controlled reason codes separate. |
| **Adopt for Agent B** | [Official Streamlit `developing-with-streamlit`](https://github.com/streamlit/streamlit/tree/develop/lib/streamlit/.agents/meta-skill/developing-with-streamlit) | UI layout, caching, session state, multipage patterns, and AppTest guidance. | Ships with Streamlit and loads version-matched guidance. Use the installed package’s `streamlit skills` flow (documented self-contained route: Streamlit 1.60+). Do not use the archived `streamlit/agent-skills` repository; retain GreenPath’s Plotly choice where the skill suggests alternatives. |
| **Optional UI smoke-test aid** | [Anthropic `webapp-testing`](https://github.com/anthropics/skills/tree/main/skills/webapp-testing) | Selective browser smoke tests/screenshots once the UI exists. | Official Anthropic repository updated 2026-10-09, but that is repository—not confirmed skill-specific—recency. The skill is a demo aid, not a full testing strategy. Inspect helper source before running; use Streamlit AppTest for most widget coverage. |
| **Defer** | [Hugging Face `huggingface-trackio`](https://github.com/huggingface/skills/tree/main/skills/huggingface-trackio) | Experiment tracking across products, baselines, and stress tests. | Official repository updated 2026-10-08; adds a library/service workflow unnecessary for the MVP’s local reports. The skill warns that created Spaces are public by default; do not upload GreenPath data or artifacts. |

The scout also found K-Dense publisher-level maintenance evidence (collection release 2.72.0, tests/workflows, and a security report updated 2026-10-05), but notes that popularity and automated scan results are **not** a security guarantee. No skills were installed or executed during inspection.

### Adoption checks

Before adding a skill to the project, inspect its exact `SKILL.md`, scripts, license, network destinations, and revision; pin a commit and install project-scoped. Keep skill use optional and review-generated code. The sklearn skill does not replace GreenPath’s leakage, calibration, synthetic-generator-shift, fairness, or confidence validation. The SHAP skill does not replace the reason-code contract. Never permit skills to upload customer evidence, secrets, predictions, or audit artifacts. If the selected Streamlit version/Python dependencies do not match, defer the skill rather than bending the app stack to it.

## 9. Main risks and mitigations

| Risk | Mitigation |
|---|---|
| Synthetic labels make scores look deceptively good | Stochastic latent outcomes, customer/merchant separation, generator perturbation, explicit synthetic-data caveat. |
| Agents implement against different contracts or duplicate shared code | Send both the same frozen contract packet; designate Agent A’s contracts as canonical; require Agent B to mark local mirrors for replacement; reconcile only during your later manual transfer. |
| Carbon factors/boundaries are incomplete | Pin source and edition; return unavailable rather than inventing a number; disclose boundaries in the UI. |
| Scope overwhelms hackathon time | Gate work in MUST-first order; defer RM and SHOULD/COULD features until clean-demo acceptance passes. |
| LLM adds unsupported claims or becomes a runtime blocker | Structured input/output, deterministic validator, adversarial tests, cached/optional provider, always-available template. |
| Modules become tightly coupled during iteration | Domain/API/UI dependency direction, narrow ports, versioned contracts, unit tests at module boundaries. |
