# Responsible AI Note — Greenr

## Purpose and research basis

Greenr is a synthetic demonstration that identifies opportunities for sustainability conversations. It estimates simulated product take-up and potential physical impact; its outputs do not establish affordability, financial eligibility, approval or investment suitability. No real personal or confidential banking records are used.

This note uses **TrustLLM: Trustworthiness in Large Language Models** (Huang et al., ICML 2024) [1] as a framework for assessing LLM usage. TrustLLM discusses eight dimensions: truthfulness, safety, fairness, robustness, privacy, machine ethics, transparency and accountability. Its empirical benchmark covers the first six; transparency and accountability are discussed without equivalent benchmark evaluations. We map these principles to our system's controls, while treating human oversight and data limitations as additional application-level concerns.

Our SHAP audit files use the additive feature-attribution framework introduced in **A Unified Approach to Interpreting Model Predictions** (Lundberg and Lee, NeurIPS 2017) [2]. SHAP supports inspection of the propensity models; TrustLLM guides the assessment of the explanation layer. These references provide a methodological basis, not a certification that the system is responsible or that it has passed either paper's evaluations.

## Separation of responsibilities

The propensity models estimate product take-up. Deterministic product rules establish relevance and exclusions. The carbon engine computes physical scenario estimates from documented inputs and factors. The LLM explains approved structured outputs and cannot change predictions, calculate emissions or decide financial eligibility. Financial eligibility remains subject to the institution's authorised criteria and processes.

Propensity, evidence quality, confidence and impact remain separate quantities. A high propensity does not establish reliable evidence, suitability or a guaranteed environmental benefit.

## Privacy

The demonstration uses generated customer data and public aggregate anchors. Raw merchant descriptions and uncontrolled feature or reason text do not enter explanation prompts. The optional provider receives approved structured claims and sentences rather than unrestricted source records. These controls align with TrustLLM's concern for privacy protection [1].

Prompt minimisation reduces unnecessary disclosure but does not prove differential privacy or complete protection against training-data extraction. TrustLLM privacy-leakage benchmarks and membership-inference attacks have not been run for this project. Real deployment would require a lawful data basis, privacy assessment, provider/data-transfer review and retention/deletion controls.

## Bias and fairness

Age band, income band and region are excluded from default propensity features and retained for subgroup audits. Saved evaluations include selection rates, false-positive and false-negative rates, calibration gaps and comparisons with proxy features included. These diagnostics support the fairness dimension of TrustLLM [1], but do not constitute its LLM fairness benchmark.

Removing demographic attributes does not remove all proxies. Spending, ownership and digital activity can retain socioeconomic associations. Saved reports show subgroup disparities, and some synthetic groups are too small for reliable conclusions. We therefore report fairness diagnostics and limitations rather than claiming that the models or LLM are unbiased. Validation on independently observed outcomes and relevant groups remains necessary before deployment.

## Explainability and SHAP

Recommendations retain fixed reason codes, supporting evidence, data cutoff timestamps and model/rule provenance. The saved SHAP files for EV Finance, Green Home, Solar Finance and Paperless Banking use **exact linear interventional SHAP** for their selected logistic models. The reference background is the transformed training population.

Each audited customer record contains a baseline, per-feature contributions, the raw model output and an additivity residual. The implementation verifies that:

```text
baseline + sum(feature contributions) = raw model output
```

This numerical check implements the local-accuracy principle of the SHAP framework [2], with an absolute residual tolerance of `2e-5`. The implementation can also produce exact tree-path-dependent contributions for a selected XGBoost model; the current four saved audits use the linear method.

These contributions explain **raw, uncalibrated log-odds**, not percentage-point changes in the displayed calibrated probability. They do not explain the nonlinear calibrator, establish causal effects or validate product rules. SHAP files provide auditor evidence; they do not by themselves demonstrate that customers understand the explanations. Missing attribution artifacts remain unavailable.

## Hallucination, truthfulness and safety

The explanation service restricts the optional provider to selecting from approved sentences. Output validation checks the product, decision state, reason codes, numerical values, units and required sentence coverage. Arbitrary generated prose cannot pass the output contract. Invalid, unsafe, failed or timed-out outputs fall back to deterministic templates.

These controls address truthfulness, safety and robustness concerns identified in TrustLLM [1]. They also preserve missing information, unavailable impact and eligibility disclaimers rather than allowing the explanation layer to invent a stronger claim.

The retained offline explanation report records **200/200 fixed cases passing**, **100% case-level groundedness and numeric consistency**, **zero unsupported delivered claims**, and **63% template fallback**. These results assess fixed adversarial responses and the validator/fallback mechanism. They are not live LLM performance, a production hallucination rate or results from the TrustLLM benchmark. Live-provider quality, latency, token usage and cost remain unmeasured in this evidence set.

## Human oversight and accountability

Reviewers can suppress engagement, flag data issues and request review. Communication policies check recorded channel consent, do-not-contact preferences, cooling-off periods and contact fatigue. Decisions, linked explanation runs and subsequent events are retained in SQLite for traceability.

Customer feedback can suppress outreach but cannot establish a factual source update. Separately authorised source changes rerun inference, evidence assessment and impact calculations while retaining earlier evidence. Campaign execution simulates contact audit records and sends no messages.

These mechanisms support transparency and accountability in our application. They do not demonstrate effective human oversight in practice: no controlled reviewer study has measured error detection or overreliance. Demo authorisation is not production identity and access management.

## Data limitations, robustness and environmental claims

Synthetic take-up labels encode generator assumptions rather than observed banking behaviour. Public household-energy aggregates anchor distributions; they do not validate individual predictions. Customer-level splits, feature cutoffs, baseline comparisons, missing-data scenarios and shifted-generator evaluations provide scoped checks against leakage and fragility.

Confidence release uses a reserved validation cohort rather than the final test set. The current confidence report suppresses display for all four core products. Its release gate tests whether higher confidence ranks lower empirical decision error; it does not by itself establish calibrated probabilities of correctness. Gate thresholds are project policy choices, not requirements prescribed by TrustLLM.

Missing critical evidence, conflicts, stale inputs, distribution anomalies and population exclusions can withhold recommendations or request review. These policies address robustness concerns, but synthetic stress tests do not establish real-world generalisation or reproduce TrustLLM's robustness benchmark.

Physical impact estimates retain documented assumptions, baselines, factor versions, units, boundaries and time horizons. Missing inputs remain unavailable rather than becoming invented or zero estimates. Legacy India operational CO2 and UK CO2e calculations remain separate; portfolio totals preserve compatible groups. Paperless carbon is not claimed. What-if tools describe model responses and physical scenarios, without causal, realised-impact or carbon-credit guarantees. See [CARBON_METHODS.md](CARBON_METHODS.md) for the current factor catalogues and calculation boundaries.

## Scope of the claim

**Our responsible AI approach is guided by TrustLLM's trustworthiness framework, and our propensity-model attribution files use the SHAP framework introduced by Lundberg and Lee.** We document implemented safeguards, retained evidence and unresolved limitations. We have not run the complete TrustLLM benchmark and do not claim TrustLLM certification, achieved fairness, comprehensive privacy protection or production readiness.

Before real deployment, the system requires independently observed outcome validation, appropriate fairness and privacy testing, secure role-based access, operational monitoring, human-review evaluation and institutional governance approval. Saved synthetic and offline reports do not establish that these requirements have been satisfied.

## References

1. Huang, Y. et al. (2024). **Position: TrustLLM: Trustworthiness in Large Language Models.** Proceedings of the 41st International Conference on Machine Learning, PMLR 235, 20166–20270. [Paper](https://proceedings.mlr.press/v235/huang24x.html) · [Benchmark and toolkit](https://github.com/HowieHwong/TrustLLM).
2. Lundberg, S. M. and Lee, S.-I. (2017). **A Unified Approach to Interpreting Model Predictions.** Advances in Neural Information Processing Systems 30 (NeurIPS, then NIPS). [Paper](https://papers.nips.cc/paper/2017/file/8a20a8621978632d76c43dfd28b67767-Paper.pdf).

## Implementation and evidence

- [SHAP audit implementation](src/greenr/models/propensity/shap_audit.py) and [saved audit files](reports/shap/).
- [Explanation controls](src/greenr/llm/service.py) and [offline explanation evaluation](reports/explanation_evaluation.json).
- [Feature policy](src/greenr/models/propensity/features.py) and [ML/subgroup evaluations](reports/ml_evaluation.json).
- [Confidence validation](src/greenr/confidence/validation.py) and [saved release report](reports/confidence_validation.json).
- [Recommendation rules](src/greenr/recommendation/service.py), [review and communication policies](src/greenr/extensions/service.py), and [audit storage](src/greenr/extensions/store.py).
- [Data card](DATA_CARD.md) and [evaluation report](EVALUATION_REPORT.md).
