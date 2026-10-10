# GreenPath contracts — v1.0.0 (canonical, owned by Agent A)

Source of truth: `src/greenpath/contracts/` (Pydantic v2, frozen, `extra="forbid"`) and `src/greenpath/ports.py`.
JSON Schemas: `src/greenpath/contracts/schemas/*.json` (regenerate with `make schemas`).
Valid example payloads: `src/greenpath/contracts/fixtures/*.json` (one Recommendation per state).

The integrated repository uses this package as canonical. Mirror-named modules are compatibility imports, not separate schema authorities.

## Integrated product adapter

The payload table below describes the numeric scoring contracts. The API/recommendation service uses an explicit evidence view in `contracts/product.py`, detailed calculator provenance in `contracts/impact_detail.py`, and product ports in `ports.py` (`ProductSnapshotProvider`, `ProductPropensityProvider`, `ImpactInputProvider`, `PortfolioHistoryProvider`, `ProductImpactCalculator`). These are distinct views, not interchangeable serialized payloads.

`demo/artifacts.py` adapts calibrated scoring results to Decimal `probability`, retains validation-selected `decision_threshold`, population exclusions and `source_result`, and attaches `source_snapshot` and per-product `source_assessment`. Validators check customer/cutoff, product, model/calibration/population, exact calibrated probability and validated-or-suppressed confidence. Fixture probabilities have no trained source and confidence is suppressed. Raw model features are not explanation inputs.

The detailed product impact unit enum supports `kg CO2`, `kg CO2/year` and `kg CO2e/year`. `EmissionsScenario.emissions_kg_co2` preserves shipped legacy CO2 calculators/fixtures; `emissions_kg_co2e` represents reviewed UK annual CO2e scenarios. These fields are mutually exclusive and must match the result units in both baseline and scenario. AVAILABLE requires both emissions, their exact signed Decimal difference, factors, period, cutoff, synthetic context and no issues. UNAVAILABLE/NOT_CLAIMED require null carbon numbers and specific issues. UI and structured explanation schemas preserve these units; grounding rejects relabelling between supported units.

`impact/uk_adapter.py` exposes AVAILABLE UK WTW CO2e through trained product recommendations only when the cutoff snapshot supplies complete physical inputs. Source activities and explicit scenario assumptions retain distinct evidence references; missing/invalid inputs remain UNAVAILABLE with no numbers, never defaults inferred from spend or propensity. Complete paperless scenarios are NOT_CLAIMED with a carbon-method issue and null carbon numbers; incomplete scenarios are UNAVAILABLE. This detailed view has no secondary activity metrics. The separate numeric scoring view supports paper statements/sheets avoided as secondary metrics, and `/simulate` exposes the activity passport. No cross-method carbon total or CO2e-to-CO2 conversion is established.

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
