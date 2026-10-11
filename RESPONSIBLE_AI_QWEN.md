# Responsible AI Note — Greenr and Qwen2.5-1.5B

## Purpose and scope

Greenr is a synthetic banking demonstration for identifying sustainability conversation opportunities. Product relevance rules, propensity models and a deterministic impact engine produce the underlying decisions and estimates. The language model explains approved outputs; it does not determine credit approval, affordability, investment suitability or environmental calculations.

The project team identifies **Qwen2.5-1.5B** as its LLM. The reviewed repository evidence does not establish the exact deployed Hugging Face checkpoint, revision, quantization or a live Qwen evaluation. Published scores below concern **Qwen2.5-1.5B-Instruct**. The [Instruct checkpoint](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct) and [base checkpoint](https://huggingface.co/Qwen/Qwen2.5-1.5B) are distinct; scores must be matched to the deployed variant before being presented as relevant model evidence.

## Research basis

We use **Position: TrustLLM: Trustworthiness in Large Language Models** (Huang et al., ICML 2024) as our trustworthiness framework. It discusses truthfulness, safety, fairness, robustness, privacy, machine ethics, transparency and accountability, with empirical benchmarking of the first six dimensions. Human oversight and data limitations are addressed here through application evidence rather than attributed a TrustLLM benchmark score. [TrustLLM paper](https://proceedings.mlr.press/v235/huang24x.html).

For propensity-model explanations, we use the SHAP feature-attribution framework introduced by Lundberg and Lee in **A Unified Approach to Interpreting Model Predictions** (NeurIPS 2017). Its additive explanations support inspection of individual predictions. This research basis does not establish fairness, causal effects or customer comprehension. [SHAP paper](https://papers.nips.cc/paper/2017/file/8a20a8621978632d76c43dfd28b67767-Paper.pdf).

## Published Qwen benchmark reference

The original TrustLLM study does not report Qwen2.5 results. **Benchmarking Trustworthiness of SLMs: Pre-trained vs. Compressed** (Lin et al., 2026) applies a four-dimension TrustLLM evaluation and reports the following in Table IV. These are external research results, not Greenr measurements. [Source: Table IV and Section IV-A](https://arxiv.org/html/2608.11981v1).

| Evaluated model variant | Machine ethics | Privacy | Robustness | Fairness | Authors' overall average |
|---|---:|---:|---:|---:|---:|
| Qwen2.5-1.5B-Instruct | 77.52% | 40.89% | 69.38% | 71.82% | 64.90% |
| Qwen2.5-1.5B-INT4-AWQ | 73.83% | 38.97% | 68.64% | 71.89% | 63.33% |
| Qwen2.5-1.5B-INT4-GPTQ | 78.63% | 40.38% | 67.34% | 69.07% | 63.86% |
| Qwen2.5-1.5B-INT8-GPTQ | 77.68% | 41.08% | 69.13% | 71.85% | 64.93% |

The study averages subtask accuracy within dimensions. Ethics uses ETHICS, Social-Chem-101 and MoralChoice; privacy uses information-usage agreement and scenario tasks; robustness uses AdvGLUE, AdvInstruction and distribution-shift tasks; fairness covers disparagement, representation and preference bias.

**64.90% is this study's aggregate, not a universal responsible-usage score.** Privacy 40.89% is not a leakage probability. This evaluation supplies no truthfulness, hallucination, safety, explainability or human-oversight score. Its quantization results do not establish performance for other variants, including GGUF. [Study](https://arxiv.org/html/2608.11981v1).

## Controls and evidence in this branch

### Privacy

The demonstration uses generated customer data and public aggregate anchors, rather than real confidential banking records. Explanation prompts exclude raw merchant descriptions and uncontrolled feature or reason text. The provider receives approved structured claims and sentences.

These controls minimise disclosure; they do not establish differential privacy or resistance to extraction attacks. The published privacy score provides a reason to retain strict prompt minimisation, not permission to share sensitive data. Project-specific privacy attack testing remains unmeasured. Evidence: [data card](DATA_CARD.md) and [explanation service](src/greenr/llm/service.py).

### Bias and fairness

Default propensity features exclude age band, income band and region. Subgroup audits examine selection rates, false-positive and false-negative rates, calibration gaps and proxy-feature comparisons. These application diagnostics assess a different object from the published Qwen language-model fairness tasks.

Spending, ownership and digital activity can retain demographic proxies. Saved evaluations contain disparities, and small synthetic groups limit interpretation. We do not infer unbiased recommendations from demographic exclusion or the Qwen fairness score. Evidence: [feature policy](src/greenr/models/propensity/features.py) and [ML evaluation](reports/ml_evaluation.json).

### Explainability and SHAP

The four saved product attribution files use exact linear interventional SHAP for the selected logistic propensity models, with a transformed training-population background. Each audited record retains a baseline, feature contributions, raw model output and additivity residual. The implementation checks:

```text
baseline + sum(SHAP feature contributions) = raw model output
```

The absolute residual tolerance is `2e-5`. The files explain **raw, uncalibrated log-odds**, not percentage-point changes in calibrated probability. They do not explain Qwen's internal reasoning, the nonlinear probability calibrator or causal customer behaviour. Recommendation reason codes and source provenance provide additional traceability. Evidence: [SHAP implementation](src/greenr/models/propensity/shap_audit.py) and [saved SHAP files](reports/shap/).

### Hallucination, truthfulness and safety

The explanation service constrains the provider to selecting approved sentences. It validates the product, decision state, reason codes, numerical values, units and required sentence coverage. Invalid, unsafe, failed or timed-out responses trigger deterministic template fallback. The LLM cannot replace calculated impact values or strengthen unavailable evidence into a supported claim.

The saved evaluation reports the following results for **offline fixed responses; no live LLM was called**:

| Application check | Saved result |
|---|---:|
| Fixed cases passing | 200 / 200 |
| Case-level groundedness | 100% |
| Numeric consistency | 100% |
| Unsupported delivered claims | 0 |
| Template fallback | 63% |

These figures evaluate the validator and fallback mechanism against a fixed adversarial test mix. They are neither Qwen benchmark results nor a production hallucination or fallback rate. Live Qwen quality and latency remain unmeasured in this evidence set. Evidence: [explanation service](src/greenr/llm/service.py) and [offline evaluation](reports/explanation_evaluation.json).

### Human oversight and accountability

Reviewers can suppress engagement, flag data issues and request review. Communication policies check consent, do-not-contact preferences, cooling-off periods and contact fatigue. Decision and explanation events are retained for audit. Campaign execution simulates contact records and sends no messages.

Feedback can suppress outreach; factual source changes require separately authorised updates and rerun the dependent calculations while retaining earlier evidence. These mechanisms support review and traceability, but effective oversight and reviewer overreliance have not been measured. Demo authorisation does not establish production access controls. Evidence: [review and communication policies](src/greenr/extensions/service.py) and [audit storage](src/greenr/extensions/store.py).

### Data limitations and robustness

Synthetic take-up labels encode generator assumptions rather than observed banking outcomes. Public aggregate energy data does not validate individual predictions. Customer-level splits, feature cutoffs, baseline comparisons and missing-data or shifted-generator scenarios provide scoped checks, with limited evidence of real-world generalisation.

The current confidence validation suppresses confidence display for all four core products. Its gate checks whether confidence ranks empirical decision error; it does not establish calibrated probabilities of correctness. Thresholds are local policy choices, not TrustLLM requirements. Missing, conflicting, stale or anomalous evidence can withhold recommendations or trigger review. Evidence: [confidence report](reports/confidence_validation.json) and [recommendation service](src/greenr/recommendation/service.py).

Impact calculations retain assumptions, units, factor versions, boundaries and time horizons. Missing inputs remain unavailable. India operational CO2 and UK CO2e estimates remain separate; aggregation preserves compatible groups. Paperless carbon savings are not claimed. Scenario estimates do not establish realised savings or carbon-credit eligibility. See [carbon methods](CARBON_METHODS.md).

## Responsible-usage statement

> Greenr's responsible AI approach is guided by TrustLLM's trustworthiness framework. Published TrustLLM-based Qwen2.5-1.5B-Instruct results provide external model context, while our repository documents application safeguards and scoped offline evaluations. Our propensity-model SHAP artifacts follow Lundberg and Lee's feature-attribution framework. We constrain explanations to approved evidence, preserve uncertainty and support reviewer intervention. These measures do not constitute TrustLLM certification or a completed evaluation of our deployed Qwen model.

Before making deployment-specific performance claims, record the exact checkpoint, revision, quantization, prompts and inference settings; run the relevant benchmarks on that configuration; and retain dataset versions, scoring methods, sample counts and failure examples. Separate model benchmark results from application tests. Real deployment also requires observed-outcome validation, privacy and subgroup assessments, secure access controls and evidence that human review works in practice.

## References

1. Huang, Y. et al. (2024). **Position: TrustLLM: Trustworthiness in Large Language Models.** ICML, PMLR 235, 20166–20270. [Paper](https://proceedings.mlr.press/v235/huang24x.html) · [Toolkit](https://github.com/HowieHwong/TrustLLM).
2. Lundberg, S. M. and Lee, S.-I. (2017). **A Unified Approach to Interpreting Model Predictions.** Advances in Neural Information Processing Systems 30. [Paper](https://papers.nips.cc/paper/2017/file/8a20a8621978632d76c43dfd28b67767-Paper.pdf).
3. Lin, H. et al. (2026). **Benchmarking Trustworthiness of SLMs: Pre-trained vs. Compressed.** arXiv:2608.11981v1; benchmark setup in Section IV-A and model scores in Table IV. [Paper](https://arxiv.org/abs/2608.11981).
