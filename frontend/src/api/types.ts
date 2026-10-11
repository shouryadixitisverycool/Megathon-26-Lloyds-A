// Shapes returned by the GreenPath FastAPI service. Decimals arrive as JSON strings.

export type Product = "EV_FINANCE" | "GREEN_HOME" | "SOLAR_FINANCE" | "PAPERLESS_BANKING";
export type DecisionState =
  | "RECOMMEND"
  | "DO_NOT_RECOMMEND"
  | "INSUFFICIENT_INFORMATION"
  | "CONFLICT_REQUIRES_REVIEW"
  | "NOT_APPLICABLE"
  | "SUPPRESSED";
export type TrustStatus = "TRUSTED" | "LIMITED" | "CONFLICT" | "OOD";
export type Channel = "app" | "email" | "phone" | "rm";
export type Decimalish = string | number | null | undefined;

export interface Health {
  status: string;
  synthetic_demo: boolean;
  contract_version: string;
  provider_mode?: string;
  source_version?: string;
}

export interface TrustIssue {
  code: string;
  field: string;
  severity: "INFO" | "WARNING" | "HIGH";
  message: string;
}

export interface Trust {
  score: Decimalish;
  status: TrustStatus;
  issues: TrustIssue[];
  version?: string;
  source_assessment?: Record<string, unknown> | null;
}

export interface FeatureEvidence {
  value: boolean | null;
  reference: string;
  observed_at: string;
  freshness: string;
  conflicts: string[];
}

export interface SourceSnapshot {
  customer_id: string;
  feature_cutoff: string;
  generated_at?: string;
  feature_version?: string;
  segment?: string;
  vehicle?: Record<string, unknown>;
  home?: Record<string, unknown>;
  energy?: Record<string, unknown>;
  digital?: Record<string, unknown>;
  spend?: Record<string, unknown>;
  data_quality?: Record<string, unknown>;
  features?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface CustomerSnapshot {
  customer_id: string;
  display_name: string;
  region: string;
  segment: string;
  feature_cutoff: string;
  features: Record<string, FeatureEvidence>;
  trust: Trust;
  decision_profile: "fixture" | "trained";
  product_trust: Partial<Record<Product, Trust>>;
  source_snapshot: SourceSnapshot | null;
  contract_version: string;
}

/** Slim directory entry kept in memory instead of the full trained snapshot list. */
export interface CustomerIndexEntry {
  customer_id: string;
  display_name: string;
  region: string;
  segment: string;
  trust_score: Decimalish;
  trust_status: TrustStatus;
  feature_cutoff: string;
  decision_profile: "fixture" | "trained";
}

export interface Propensity {
  product: Product;
  probability: Decimalish;
  model_version: string;
  calibration_version: string | null;
  reason_codes: string[];
  confidence: Decimalish;
  confidence_validated: boolean;
  in_model_population: boolean;
  population_exclusion: string | null;
  decision_threshold: Decimalish;
  source_result?: Record<string, unknown> | null;
}

export interface DecisionEvidence {
  code: string;
  message: string;
  fields: string[];
  references: string[];
}

export interface Period {
  start: string;
  end: string;
}

export interface ImpactEvidence {
  field: string;
  value: unknown;
  unit: string | null;
  reference: string;
  basis: string;
  observed_at: string;
  period?: Period;
  freshness: string;
  conflicts: string[];
}

export interface CarbonFactor {
  factor_id: string;
  value: string;
  unit: string;
  geography: string;
  fuel?: string | null;
  activity_period?: string | null;
  boundary: string;
  applicability: string;
  source_id?: string;
  source_url?: string;
  source_title: string;
  source_publisher: string;
  source_edition: string;
  source_locator: string;
  source_sha256?: string | null;
  verification_basis: string;
  source_limitation?: string | null;
  source_published_on?: string | null;
  source_checked_on?: string | null;
}

export interface SecondaryMetric {
  name: string;
  value: Decimalish;
  unit: string;
  method_version: string;
  evidence_references: string[] | string;
}

export interface ImpactScenarioSide {
  description: string;
  emissions_kg_co2: Decimalish;
  emissions_kg_co2e: Decimalish;
}

export interface Impact {
  product: Product;
  status: "AVAILABLE" | "UNAVAILABLE" | string;
  value: Decimalish;
  units: string;
  baseline: ImpactScenarioSide;
  scenario: ImpactScenarioSide;
  period?: Period | null;
  feature_cutoff?: string | null;
  factor_catalogue_version: string;
  factor_catalogue_sha256: string;
  boundary: string;
  assumptions: string[];
  exclusions: string[];
  method_version: string;
  method_release: string;
  timestamp: string;
  evidence: ImpactEvidence[];
  issues: { code: string; field: string; message: string }[];
  secondary_metrics: SecondaryMetric[];
  factors: CarbonFactor[];
  passport_id?: string;
}

export interface Priority {
  score: number | null;
  components: Record<string, number | null>;
  weights: Record<string, number>;
  version: string;
  normalisation: string;
  limitation: string | null;
  rank: number;
}

export interface ExpectedImpact {
  status: string;
  value: string | null;
  units: string;
  compatibility_group: string[] | null;
  limitation: string;
}

export interface NextAction {
  action: string;
  reason: string;
  channel: Channel;
  version: string;
}

export interface Recommendation {
  decision_id?: string | null;
  provenance?: Record<string, unknown>;
  customer_id: string;
  product: Product;
  propensity: Propensity | null;
  state: DecisionState;
  reason_codes: string[];
  evidence: DecisionEvidence[];
  exclusions: string[];
  impact: Impact;
  trust: Trust;
  feature_cutoff: string;
  rules_version: string;
  timestamp: string;
  eligibility_disclaimer: string;
  contract_version: string;
  // Present on /next-actions and /portfolio/opportunities rows.
  priority?: Priority;
  expected_sustainability_impact?: ExpectedImpact;
  next_action?: NextAction;
  region?: string;
  segment?: string;
}

export interface Explanation {
  customer_id: string;
  product: Product;
  state: DecisionState;
  text: string;
  reason_codes: string[];
  impact_value: Decimalish;
  units: string;
  source: "template" | "llm";
  provider_version: string;
  validation_passed: boolean;
  fallback_reason: string | null;
  eligibility_disclaimer: string;
  headline: string | null;
  explanation: string | null;
  why_recommended: string[];
  estimated_impact_text: string | null;
  confidence_text: string | null;
  action_text: string | null;
  missing_information: string[];
}

export type PromoFormat = "push" | "one_liner" | "short" | "medium";

/** Promo copy; AVAILABLE when contact rules allow engagement, PREVIEW when only staff may view it. */
export interface PromoCopy {
  status: "AVAILABLE" | "PREVIEW" | "WITHHELD";
  withheld_reason: string | null;
  customer_id: string;
  product: Product;
  format: PromoFormat;
  channel: Channel;
  next_action: string;
  lines: string[];
  text: string | null;
  cta_label: string | null;
  disclaimer: string | null;
  angles: string[];
  source: "llm" | "template" | null;
  template_id: string | null;
  provider_version: string | null;
  prompt_version: string | null;
  fallback_reason: string | null;
  reason_codes: string[];
  impact_value: Decimalish;
  units: string | null;
  decision_id: string | null;
  data_timestamp: string;
}

export interface ProductOpportunity {
  product: Product;
  total: number;
  recommended: number;
  state_counts: Record<string, number>;
  available_impact_count: number;
}

export interface GroupSummary {
  name: string;
  customer_count: number;
  recommended_count: number;
}

export interface PhysicalGroup {
  product: Product;
  units: string;
  boundary: string;
  period: string;
  method_version: string;
  factor_catalogue_version: string;
  value: string;
}

export interface PortfolioSummary {
  analytics: {
    physical_impact?: { status: string; unavailable_count: number; groups: PhysicalGroup[]; limitation: string };
    quality_counts?: Record<string, number>;
    missingness?: Record<string, number>;
    decision_count?: number;
  };
  total_customers: number;
  total_recommendations: number;
  recommended_count: number;
  state_counts: Record<string, number>;
  product_opportunities: ProductOpportunity[];
  region_summaries: GroupSummary[];
  segment_summaries: GroupSummary[];
  available_impact_count: number;
  customers_with_opportunity: number;
  high_confidence_opportunities: number;
  validated_confidence_opportunities: number;
  high_trust_opportunities: number;
  funnel_counts: Record<string, number>;
  funnel_limitation: string;
  disclaimer: string;
}

export interface TrendPoint {
  month: string;
  product: Product;
  customer_count: number;
  recommended_count: number;
  state_counts: Record<string, number>;
  [key: string]: unknown;
}

export interface TrendAnalytics {
  month: string;
  product: Product;
  customer_count: number;
  observed_conversion_rate: Decimalish;
  observed_outcome_count: number;
  physical_impact_groups: Record<string, unknown>[];
  [key: string]: unknown;
}

export interface PortfolioTrends {
  analytics: { observations?: TrendAnalytics[]; limitation?: string };
  observations: TrendPoint[];
  disclaimer: string;
}

export interface Preferences {
  do_not_contact: boolean;
  channel_consent: Partial<Record<Channel, boolean>>;
}

export interface AuditEvent {
  id: string;
  customer_id: string;
  product: string;
  kind: string;
  timestamp: string;
  limitation?: string;
  lifecycle_state?: string;
  previous_state?: string;
  action?: string;
  response?: string;
  reviewer?: string;
  note?: string;
  channel?: string;
  [key: string]: unknown;
}

export interface HistoryResponse {
  events: AuditEvent[];
  recommendations: Record<string, unknown>[];
  source_updates: Record<string, unknown>[];
  source_history: Record<string, unknown>[];
  limitation: string;
}

export interface EvidenceGraph {
  nodes: { id: string; type: "decision" | "reason" | "feature" | "impact"; label: string; detail?: DecisionEvidence; method_version?: string }[];
  edges: { from: string; to: string; relation: string }[];
  limitation: string;
}

export interface SimulationTemplate {
  profile: "uk" | "fixture";
  inputs: Record<string, any> | null;
  limitation: string;
}

export interface UkImpact {
  status: "MODELLED_ESTIMATE" | "UNAVAILABLE" | "NOT_CLAIMED" | string;
  units?: string;
  baseline_emissions?: string;
  scenario_emissions?: string;
  potential_reduction?: string | null;
  method?: string;
  method_version: string;
  boundary?: string;
  factor_vintage?: string;
  factor_source?: string;
  factor_source_sha256?: string;
  factor_records?: Record<string, Record<string, unknown>>;
  formula?: string;
  limitations?: string[];
  limitation?: string;
  passport_id?: string;
  paper_statements_avoided?: string;
  paper_sheets_avoided?: string;
  issues?: unknown[];
}

export interface SimulationResult extends AuditEvent {
  scenario_inputs: Record<string, unknown>;
  impact: Impact | UkImpact;
  method_version: string;
}

export interface SensitivityResult extends AuditEvent {
  changes: Record<string, number | null>;
  feature_classes: Record<string, string>;
  baseline_probability: number | null;
  scenario_probability: number | null;
  model_version: string;
  calibration_version: string | null;
}

export interface CounterfactualResult {
  baseline_probability: number | null;
  model_version: string;
  calibration_version: string | null;
  feature_classes: Record<string, string>;
  evaluated_count: number;
  candidate_count: number;
  truncated: boolean;
  results: { changes: Record<string, number>; probability: number | null; normalised_distance: number; target_met: boolean }[];
  best: unknown;
  limitation: string;
}

export interface PlanResult {
  selected_count: number;
  scenario_adopters: number;
  conversion_rate_assumption: number;
  average_propensity: number | null;
  high_confidence_share: number | null;
  validated_confidence_share: number | null;
  impact_groups: { product: Product; units: string; boundary: string; period: string; method_version: string; factor_version: string; scenario_impact: string }[];
  impact_status: string;
  impact_unavailable_count: number;
  selected: { customer_id: string; product: Product; priority: Priority }[];
  excluded: Record<string, number>;
  disclaimer: string;
  constraint_version: string;
  executed: boolean;
  channel: Channel;
  capacity_budget: null | {
    boundary: string;
    limit: number;
    used: number;
    remaining_before: number;
    active_campaign_count: number;
    max_active_campaigns: number;
  };
  impact_ranking_limitation: string;
  execution_note?: string;
  campaign_event_id?: string;
}

export interface ShapAudit {
  status?: string;
  limitation?: string;
  product?: Product;
  model_version?: string;
  model_type?: string;
  method?: string;
  output_space?: string;
  explains_calibrated_probability?: boolean;
  background?: { source: string; rows: number };
  feature_names?: string[];
  rows?: { customer_id: string; base_value: number; raw_margin: number; shap_values: Record<string, number>; additivity_residual: number }[];
}

export interface GovernanceDiagnostics {
  reports: Record<string, any>;
  model_source: string;
  limitations: string[];
}
