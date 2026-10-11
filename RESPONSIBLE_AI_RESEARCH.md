# Responsible AI note: research basis and submission draft

Reviewed against the current `main` working tree (HEAD `6a971cd`), including its uncommitted evaluation reports, and both supplied Lloyds PS1 attachments. This is a writing draft and evidence map; it does not change runtime safeguards or certify deployment readiness. The supplied brief's submission item H requires privacy, bias, explainability, hallucination, human oversight and data limitations. Its core rule assigns prediction to ML, physical impact to a deterministic engine, and explanation to the LLM.

## Submission draft

GreenPath is a synthetic demonstration for identifying sustainability conversation opportunities. Propensity estimates simulated product take-up; evidence quality, reliability of a thresholded prediction and physical impact are separate quantities. Financial eligibility remains subject to the institution's authorised criteria and processes. The LLM cannot establish eligibility, change model scores or calculate emissions.

**Privacy.** We use generated customer records and public aggregate anchors, without real personal or confidential banking data. The explanation service excludes raw merchant descriptions and uncontrolled feature/reason text from prompts. Its optional provider receives approved structured claims and sentences. This reduces unnecessary disclosure but does not establish differential privacy or production data-transfer compliance. Deployment would require a lawful data basis, privacy assessment, appropriate retention/deletion controls and provider review.

**Bias and fairness.** Age band, income band and region are excluded from default propensity inputs and retained for subgroup audits. The pipeline reports selection rates, false-positive and false-negative rates, group calibration gaps and proxy-ablation comparisons. These diagnostics support an assessment using equality-of-opportunity and equalized-odds criteria [3]; they do not enforce those criteria. Spend, ownership and digital-use features can retain demographic or socioeconomic proxies. Synthetic labels and small groups limit interpretation. We report disparities and insufficient evidence rather than declaring the models unbiased.

**Reliability and abstention.** We assess propensity probabilities with Brier score, reliability tables and a binned calibration error [1, 2], alongside ranking and baseline metrics. A separate confidence model estimates correctness of the binary prediction at the chosen product threshold. Its release gate uses a reserved validation cohort and requires adequate sample size and decreasing empirical error as confidence rises. The saved report suppresses confidence for all four core products. The gate tests error ranking; it does not by itself validate the numeric confidence as a calibrated correctness probability. Missing critical evidence, conflicting signals, stale inputs, distribution anomalies and population exclusions can withhold a recommendation or request review. A complete selective risk/coverage evaluation remains future work [4].

**Explainability.** Decisions retain canonical reason codes, supporting evidence, cutoff timestamps and model/rule provenance. Auditor SHAP values explain the selected model's raw, uncalibrated log-odds, with an explicit background and numerical additivity check [5]. They do not explain the nonlinear calibrator, establish causation or substitute for product-rule explanations. Customers receive structured explanations that preserve the actual decision and its limitations.

**Hallucination control.** The optional provider selects from approved sentences; arbitrary generated prose cannot pass the output contract. Schema checks validate product, decision state, reasons, numerical values, units and required sentence coverage. Invalid, unsafe, failed or timed-out output falls back to deterministic templates. In a fresh local run, all 200 fixed offline cases passed, delivered outputs preserved their numbers and grounding, and 63% used fallback. These are validator and fallback results, not a live model hallucination benchmark. FActScore motivates a future claim-level factuality evaluation [6]; its published evaluator is not implemented here.

**Human oversight.** Reviewers can suppress engagement and flag data issues; communication policies respect recorded channel consent, contact fatigue and pauses. The demo stores decisions, explanation runs and subsequent events for audit. Feedback can suppress outreach but cannot prove a factual source change. Separately authorised source updates trigger fresh inference and preserve prior evidence. Campaign execution simulates contact audit records and sends no messages. Demo authorisation does not replace production identity/access controls, and the effectiveness of human review has not been measured in a user study.

**Data and environmental limitations.** Generated outcomes measure performance against the generator's assumptions, not observed banking behaviour. Customer splits, cutoff controls, baseline comparisons and stress tests help detect leakage and fragility, but cannot establish external validity. Physical estimates expose assumptions, factor sources, units, boundaries and time horizons. Missing inputs remain unavailable. Legacy India CO2 estimates and UK CO2e scenarios remain separate; UK scenarios use the reviewed 2025 factor subset and exclude manufacturing/embodied emissions. Paperless carbon is not claimed. Potential reductions are modelled scenarios, without causal, realised-impact or carbon-credit guarantees. Model cards document intended uses and limitations [7].

We assess responsibility through separate evidence and safeguards for each risk, with explicit failures and unavailable measurements. These research references support metric definitions and evaluation design; they do not provide a universal responsibility score or certify regulatory compliance.

## Research papers and the claims they support

| Paper and venue | Relevant measure or practice | Current implementation | Defensible wording |
| --- | --- | --- | --- |
| **[1] Guo et al., ICML 2017: On Calibration of Modern Neural Networks** | Reliability diagrams and expected calibration error (ECE). | `evaluation/metrics.py` uses 10 equal-width probability bins and compares mean take-up probability with observed take-up rate. This adapts the binned calibration calculation to binary event probabilities; the paper's primary presentation compares predicted-class confidence with correctness. | "We use binned calibration diagnostics consistent with the calibration literature, adapted to product take-up probabilities." Do not claim that we implement the paper's temperature-scaling method. |
| **[2] Gneiting & Raftery, JASA 2007: Strictly Proper Scoring Rules, Prediction, and Estimation** | Proper scoring rules, including the quadratic/Brier score. | Brier score is implemented for propensity probabilities, with baseline comparisons in saved reports. It evaluates probability quality, not fairness or all dimensions of responsibility. | "We assess probabilistic forecasts using Brier score, supported by the proper-scoring-rule literature." |
| **[3] Hardt, Price & Srebro, NeurIPS 2016: Equality of Opportunity in Supervised Learning** | Equality of opportunity: matching true-positive rates across groups. Equalized odds: matching both true-positive and false-positive rates. | Subgroup tables contain FPR and FNR; TPR equals `1 - FNR`. They support disparity calculations. Fairness post-processing, parity release gates and statistical uncertainty intervals are absent. | "We audit subgroup error rates using diagnostics relevant to equality of opportunity and equalized odds." Do not say the models satisfy either criterion. |
| **[4] Geifman & El-Yaniv, NeurIPS 2017: Selective Classification for Deep Neural Networks** | Selective risk and coverage: error among accepted predictions versus the proportion accepted. | The system has abstention states, confidence error buckets and Trust-status reports. It does not implement the paper's selection algorithm, finite-sample guarantee or a full risk/coverage curve. | "Our abstention design is consistent with selective prediction; evaluating the complete risk/coverage trade-off is proposed work." |
| **[5] Lundberg & Lee, NeurIPS 2017: A Unified Approach to Interpreting Model Predictions** | SHAP feature attribution and local accuracy/additivity. | Exact linear interventional contributions or XGBoost exact tree-path-dependent contributions, depending on the selected model. Additivity is checked in raw margin space. | "We use SHAP-based auditor explanations and verify raw-model additivity." This is one numerical consistency check, not proof of overall explanation quality. |
| **[6] Min et al., EMNLP 2023: FActScore** | Fraction of atomic factual claims supported by a reliable knowledge source. | Existing grounding checks operate on complete structured outputs and approved sentences. No atomic-fact extraction or FActScore evaluator is present. | "We propose FActScore-inspired claim-level evaluation against decision and impact records." Do not rename the existing `groundedness_rate` as FActScore. |
| **[7] Mitchell et al., FAT* 2019: Model Cards for Model Reporting** | Transparent documentation of intended use, evaluation conditions, subgroup performance and limitations. | The repository includes model cards and a data card; their presence alone does not prove complete adherence to the paper's framework. | "Our model documentation follows the model-card reporting approach." This is a reporting practice, not a numeric metric. |

An additional useful reference is **[8] Pleiss et al., NeurIPS 2017: On Fairness and Calibration**, which analyses tensions between calibration and error-based fairness constraints. Use it to explain why we report several diagnostics and specify the intended fairness objective, rather than collapsing them into one score. We do not implement its mitigation procedure.

## Metric definitions and limits

- **Propensity Brier score:** `mean((p - y)^2)`, where `y` is synthetic take-up. Lower is better. The repository uses the binary event convention; some multiclass scoring definitions sum errors over both classes and differ by a constant factor. Compare the same product and evaluation cohort against its baseline.
- **Binary event ECE:** `sum_b (n_b / N) * abs(mean(p in b) - mean(y in b))`. Lower is better; report binning and counts. A low value can conceal subgroup errors or result from concentrated low probabilities. It is not a standalone safety certificate.
- **Fairness gaps:** `max_g(TPR_g) - min_g(TPR_g)` for opportunity parity; report the FPR range alongside it for equalized-odds diagnostics. The FNR range equals the TPR range for defined groups. Also report selection-rate ranges and group calibration gaps, but do not treat those as interchangeable fairness definitions. Undefined class-denominator metrics remain unavailable. Include group and positive/negative counts; uncertainty intervals and intersectional audits are proposed additions.
- **Selective evaluation, proposed:** coverage is accepted predictions divided by all evaluated predictions; selective risk is wrong accepted predictions divided by accepted predictions. State the acceptance rule and evaluate the fixed operational classifier on a common cohort while varying the selection threshold. Zero accepted predictions yields undefined risk, not zero risk. Recommendation uptake precision is a different metric with a different denominator.
- **SHAP consistency:** `abs(raw_margin - (base_value + sum(feature_contributions)))`. The runtime requires residuals within absolute tolerance `2e-5`. This does not test causal validity, human comprehension or explanation of calibrated probabilities.
- **Claim factuality, proposed:** supported atomic factual claims divided by all factual claims, using versioned decision/impact evidence as the source. Keep the existing case-level grounding/numeric metrics separately. Also measure required-field completeness and invalid-output rejection: a short or empty explanation can otherwise look factually precise while omitting needed information.

## Current evidence snapshot

The following propensity results come from `reports/ml_evaluation.json`, for the selected deployed model. They are saved held-out **test** metrics, not validation metrics and not a new training run. The brief also requires a validation-set evaluation report; use the report's validation fields for that deliverable.

| Product | Test customers | Brier | Binary event ECE | Lift in top 10% | Confidence release |
| --- | ---: | ---: | ---: | ---: | --- |
| EV Finance | 346 | 0.0697 | 0.0135 | 2.8245 | Suppressed |
| Green Home | 279 | 0.0823 | 0.0113 | 1.9162 | Suppressed |
| Solar Finance | 354 | 0.0407 | 0.0312 | 6.9653 | Suppressed |
| Paperless Banking | 105 | 0.1501 | 0.0531 | 0.9545 | Suppressed |

These numbers should not support a claim that every model is strong: the selected Paperless model's top-10% lift is below 1 on this test cohort. A fitted calibrator also does not guarantee that every held-out metric improves; EV and Green Home Brier scores are slightly worse after calibration in the saved report.

The confidence release cohorts contain 128, 95, 115 and 39 rows respectively. All fall below the 200-row release minimum; Green Home and Paperless additionally lack sufficient confidence-fitting rows. EV and Solar passing some stress checks does not override the reserved release-cohort failure.

The confidence gate in `confidence/validation.py` requires at least 200 rows, Spearman correlation of confidence-bin rank with error at most `-0.6`, top-30% confidence error at most half the bottom-30% error, bottom-30% error at least `0.02`, and groups that do not overlap due to ties. **These are project policy choices, not cutoffs prescribed by the cited papers.** No numeric correctness-calibration tolerance is enforced by this gate.

Fairness is unresolved. For example, EV Finance's saved income-band table has an FNR range of approximately `0.6667`, an FPR range of `0.0694`, and a selection-rate range of `0.0907`. The smallest income group has 19 customers and three positives; other income groups have as few as three positives. These are noisy diagnostics, not evidence of achieved parity. Some Paperless regional groups contain only two customers. Attribute exclusion and proxy ablation provide checks, not a fairness guarantee.

All four saved SHAP audits contain 100 rows each; maximum absolute additivity residuals are below `3e-15`. This establishes raw-margin numerical consistency on those audited rows only.

The offline explanation evaluator was rerun directly without invoking a live provider or overwriting the saved report: **200/200 cases passed, case-level groundedness and numeric consistency were 100%, unsupported delivered claims were 0, and fallback was 63%**. The evaluator uses fixed adversarial responses and deterministic templates. Live provider quality, latency, token use and cost remain unmeasured. The 63% rate reflects the deliberately adversarial case mix and is not an estimate of production fallback frequency.

## Evidence map

| Requirement | Main code and retained evidence |
| --- | --- |
| Probability quality and subgroup audits | `src/greenpath/evaluation/metrics.py`; `reports/ml_evaluation.json` |
| Feature exclusions and population rules | `src/greenpath/models/propensity/features.py` |
| Confidence semantics and release gate | `src/greenpath/confidence/meta_model.py`; `src/greenpath/confidence/validation.py`; `src/greenpath/pipelines/run.py`; `reports/confidence_validation.json` |
| Abstention and evidence policy | `src/greenpath/recommendation/service.py`; `src/greenpath/trust/provider.py`; `src/greenpath/trust/selection.py` |
| Model attribution | `src/greenpath/models/propensity/shap_audit.py`; `reports/shap/*.json` |
| Prompt minimisation and output controls | `src/greenpath/llm/service.py`; `src/greenpath/llm/evaluation.py`; `reports/explanation_evaluation.json` |
| Review, consent, contact limits and audit | `src/greenpath/extensions/service.py`; `src/greenpath/extensions/store.py` |
| Environmental boundaries and data provenance | `CARBON_METHODS.md`; `DATA_CARD.md`; `MODEL_CARD_*.md`; `RESPONSIBLE_AI.md` |

## References

1. Guo, C., Pleiss, G., Sun, Y. & Weinberger, K. Q. (2017). [On Calibration of Modern Neural Networks](https://proceedings.mlr.press/v70/guo17a.html). ICML, PMLR 70, 1321-1330.
2. Gneiting, T. & Raftery, A. E. (2007). [Strictly Proper Scoring Rules, Prediction, and Estimation](https://doi.org/10.1198/016214506000001437). Journal of the American Statistical Association, 102(477), 359-378. [Author-hosted full text](https://sites.stat.washington.edu/people/raftery/Research/PDF/Gneiting2007jasa.pdf).
3. Hardt, M., Price, E. & Srebro, N. (2016). [Equality of Opportunity in Supervised Learning](https://papers.neurips.cc/paper_files/paper/2016/hash/6a9659feb1216f14f7384ba499518b38-Abstract.html). NeurIPS 29 (then NIPS).
4. Geifman, Y. & El-Yaniv, R. (2017). [Selective Classification for Deep Neural Networks](https://papers.nips.cc/paper_files/paper/2017/hash/4a8423d5e91fda00bb7e46540e2b0cf1-Abstract.html). NeurIPS 30 (then NIPS).
5. Lundberg, S. M. & Lee, S.-I. (2017). [A Unified Approach to Interpreting Model Predictions](https://papers.nips.cc/paper/2017/file/8a20a8621978632d76c43dfd28b67767-Paper.pdf). NeurIPS 30 (then NIPS).
6. Min, S. et al. (2023). [FActScore: Fine-grained Atomic Evaluation of Factual Precision in Long Form Text Generation](https://aclanthology.org/2023.emnlp-main.741/). EMNLP, 12076-12100.
7. Mitchell, M. et al. (2019). [Model Cards for Model Reporting](https://arxiv.org/abs/1810.03993). FAT* (the conference now called FAccT). DOI: `10.1145/3287560.3287596`.
8. Pleiss, G., Raghavan, M., Wu, F., Kleinberg, J. & Weinberger, K. Q. (2017). [On Fairness and Calibration](https://proceedings.neurips.cc/paper/2017/hash/b8b9c74ac526fffbeb2d39ab038d1cd7-Abstract.html). NeurIPS 30 (then NIPS).
