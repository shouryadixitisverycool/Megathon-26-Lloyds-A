# Responsible AI Note

GreenPath helps identify sustainability opportunities using synthetic banking data. The project team has selected jagruti-1.5b to explain results. Product rules, prediction models and the impact calculator produce those results. The LLM does not decide credit eligibility or calculate carbon savings.

Our approach follows the trustworthiness principles discussed in [TrustLLM (Huang et al., ICML 2024)](https://proceedings.mlr.press/v235/huang24x.html). We use these principles to guide our safeguards and responsible AI practices.

## How we use AI responsibly

- **Privacy:** We use synthetic customer records. Raw merchant descriptions do not enter explanation prompts. The explanation service shares only approved claims and sentences, reducing exposure of sensitive information.

- **Bias:** Age band, income band and region are excluded from the default prediction inputs. We check errors and selection rates across groups to assess differences in model behaviour.

- **Explainability:** Our SHAP files show how input features contribute to product take-up predictions. They follow [Lundberg and Lee's SHAP framework (NeurIPS 2017)](https://papers.nips.cc/paper/2017/file/8a20a8621978632d76c43dfd28b67767-Paper.pdf). They explain the prediction model's raw score, rather than jagruti's reasoning or causal effects.

- **Hallucinations:** The explanation service accepts only approved sentences and checks product names, reasons, numbers and units. Invalid responses use fixed templates. The LLM cannot invent or change impact estimates.

- **Human oversight:** Reviewers can stop outreach, flag data problems and request review. Consent and contact limits are checked, and decisions are logged.

- **Data limitations:** Synthetic data provides a controlled environment for evaluating the system. Missing, conflicting or outdated evidence can block recommendations. Confidence display is currently withheld for all four core products. Environmental estimates depend on stated assumptions and represent potential savings rather than guaranteed outcomes.

## jagruti benchmark context

A later study, [Benchmarking Trustworthiness of SLMs: Pre-trained vs. Compressed (Lin et al., 2026), Table IV](https://arxiv.org/html/2608.11981v1), uses four TrustLLM dimensions and reports these results:

| Model | Ethics | Privacy | Robustness | Fairness | Study average |
|---|---:|---:|---:|---:|---:|
| jagruti-1.5b-Instruct | 77.52% | 40.89% | 69.38% | 71.82% | 64.90% |

These are published research results for the Instruct model under the study's settings. They provide external benchmark context for model trustworthiness. The average represents the reported benchmark result, not a universal measure of responsible AI, and the study's four dimensions do not include a separate hallucination or human oversight score.

## What we have tested

Our saved [offline explanation tests](reports/explanation_evaluation.json) passed 200 of 200 cases, with consistent numbers, no unsupported delivered claims and 63% template fallback.

These results document the behaviour of our explanation safeguards under the evaluated test cases.

This note records GreenPath's responsible AI safeguards, evaluation evidence and approach to trustworthy sustainability insights. It is intended to support transparent, evidence-based recommendations for green financial products.
