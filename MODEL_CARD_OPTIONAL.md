# Optional Model Cards

Green Investments and Green Loans are implemented synthetic opportunity signals in `extensions/optional_models.py`, not additional validated banking eligibility or suitability systems. Saved evidence: `reports/optional_evaluation.json`. Optional confidence is suppressed for both because independent reliability validation is not implemented.

| Field | Green Investments | Green Loans |
|---|---|---|
| Intended use | Synthetic sustainability/investment conversation signal, not investment advice | Synthetic general green-loan conversation signal, not credit approval |
| Inputs | Preference, digital activity/history, tenure and transaction coverage | Home-improvement activity, vehicle/mileage, energy, preference, digital activity and coverage |
| Model | Logistic, optional validation-fitted Platt calibration | Logistic, optional validation-fitted Platt calibration |
| Saved train / validation / test customers | 336 / 70 / 78 | 1,564 / 325 / 355 |
| Test AUC / heuristic AUC | 0.730 / 0.706 | 0.544 / 0.552 |
| Test Brier / ECE | 0.152 / 0.088 | 0.135 / 0.028 |
| Shifted AUC | 0.579 | 0.527 |
| 30% missingness AUC | 0.626 | 0.483 |
| Confidence | Suppressed | Suppressed |

Data/outcomes: engineered 90-day Bernoulli adoption scenarios with smooth feature signals, independent Gaussian latent drivers and interactions; seed 6044. Latent values are not exported as features. Customer split and Customer 360 hashes, generator parameters and model/output artifact hashes are in the saved report. Calibration and decision thresholds use validation only; thresholds are not eligibility cutoffs. Shift tests change activity, missingness, coefficients/intercept and latent/outcome draws.

Limitations: simulated labels rather than observed adoption, small investment test sample, weak general-loan discrimination below its heuristic, generator shift and missingness degradation, and no independently validated optional confidence. Neither model should be described as outperforming all baselines or demonstrating real-world reliability. No carbon claim is attached to these optional propensity signals. Reproduce with the full pipeline followed by `uv run --locked python -m greenpath.extensions.optional_models`; saved values depend on dataset size and artifact hashes. Optional training is not part of `make all`.
