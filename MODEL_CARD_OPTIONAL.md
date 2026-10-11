# Optional Model Cards

Green Investments and Green Loans are implemented synthetic opportunity signals in `extensions/optional_models.py`, not additional validated banking eligibility or suitability systems. Saved evidence: `reports/optional_evaluation.json`. Optional confidence is suppressed for both because independent reliability validation is not implemented.

| Field | Green Investments | Green Loans |
|---|---|---|
| Intended use | Synthetic sustainability/investment conversation signal, not investment advice | Synthetic general green-loan conversation signal, not credit approval |
| Inputs | Preference, digital activity/history, tenure and transaction coverage | Home-improvement activity, vehicle/mileage, energy, preference, digital activity and coverage |
| Model | Logistic, optional validation-fitted Platt calibration | Logistic, optional validation-fitted Platt calibration |
| Evaluation | `reports/optional_evaluation.json`, separately regenerated against matching core artifacts | Same report; old metrics/sample sizes are not current after core regeneration |
| Confidence | Suppressed | Suppressed |

Data/outcomes: engineered 90-day Bernoulli adoption scenarios with smooth feature signals, independent Gaussian latent drivers and interactions; seed 6044. Latent values are not exported as features. Customer split and Customer 360 hashes, generator parameters and model/output artifact hashes are in the saved report. Calibration and decision thresholds use validation only; thresholds are not eligibility cutoffs. Shift tests change activity, missingness, coefficients/intercept and latent/outcome draws.

Limitations: simulated labels rather than observed adoption, potentially small product test samples, generator shift and missingness risk, and no independently validated optional confidence. Earlier optional evidence showed weak general-loan discrimination below its heuristic; that is historical, not a new measurement after core regeneration. Neither model should be described as outperforming all baselines or demonstrating real-world reliability. No carbon claim is attached to these signals. Reproduce with the full pipeline followed by `uv run --locked python -m greenr.extensions.optional_models`; values depend on dataset size and artifact hashes. Optional training is not part of `make all`.

The core `confidence_release` methodology does not validate these optional products. They remain optional analytic signals, not additional four-product recommendation contracts. Core SHAP and factual source-update support must not be described as independently validated optional equivalents. Regenerate the optional report after core source/split changes before quoting numerical evidence. See `EVALUATION_REPORT.md` for consolidated limits and gate ownership.
