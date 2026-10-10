# GreenPath contracts — v1.0.0 (canonical, owned by Agent A)

Source of truth: `src/greenpath/contracts/` (Pydantic v2, frozen, `extra="forbid"`) and `src/greenpath/ports.py`.
JSON Schemas: `src/greenpath/contracts/schemas/*.json` (regenerate with `make schemas`).
Valid example payloads: `src/greenpath/contracts/fixtures/*.json` (one Recommendation per state).

Agent B mirrors these locally and marks the mirrors as replaceable; at manual integration they are replaced by this package.

## Payloads
| Contract | Produced by | Notes |
|---|---|---|
| `CustomerSnapshot` | A (`pipelines.snapshot_provider`) | `features` is the approved propensity feature view and the only scoring input; typed fact groups (`vehicle`, `home`, `energy`, `digital`, `spend`) are the display/impact/guardrail view. Audit-only attributes (age band, income band, postcode) never appear. Units: GBP, km, kWh. |
| `PropensityResult` | A (`models.propensity.provider`) | `propensity` is the **calibrated** probability. `in_model_population=False` + `population_exclusion` when the customer already holds/adopted the product (B maps this to `NOT_APPLICABLE`/`SUPPRESSED`). `confidence` is always present; when `status=SUPPRESSED` it has no value/bucket and must not be displayed. |
| `ReasonCodeDefinition` | A (`models.propensity.reason_codes`) | Catalogue with customer + RM wording, derivation, thresholds, evidence fields, applicable products. |
| `TrustAssessment` | A (`trust.provider`) | Per customer × product. Evidence adequacy only — separate from confidence. `has_high_severity_conflict` property for fail-closed `CONFLICT_REQUIRES_REVIEW`. |
| `ImpactResult` | B | Validator enforces: AVAILABLE ⇒ numbers + unit + method + factor source/version + boundary; UNAVAILABLE ⇒ reason and no numbers; NOT_CLAIMED ⇒ no carbon numbers. |
| `Recommendation` | B | Spec §5 object. `product_id` must match `opportunity_id` (GP01–GP04); trust/impact must be for the same product; `eligibility.status` is always `NOT_ASSESSED`. |
| `Explanation`, `PortfolioSummary`, `SegmentRow`, `TrendPoint`, `PortfolioTrends` | B | API/UI payloads. |

## Enums
`Product`, `RecommendationState` (six states), `ReasonCode`, `TransactionCategory`, `TrustIssueCode`, `TrustStatus`, `ConfidenceStatus`, `ConfidenceBucket`, `ImpactStatus`, `GroundingResult` — see `contracts/enums.py`.

## Additions beyond the specification's examples (v1.0.0)
- Reason codes `EXISTING_VEHICLE_FINANCE`, `HIGH_GAS_USE`, `STATED_SUSTAINABILITY_PREFERENCE` (spec §11.3 feature families).
- `PropensityResult.in_model_population` / `population_exclusion`.
- `ConfidenceResult.status` (`VALIDATED` | `SUPPRESSED`) implementing spec §16.4 "if this is not true, confidence is not surfaced".
- `GroundingResult.NOT_RUN` for template output that never passed through an LLM.
- `TrustProvider` port (A implements) and batch `PropensityProvider.score_many`.

## Change process
Propose changes in writing; bump `CONTRACT_VERSION`; regenerate schemas and fixtures; give the same version to both agents.
