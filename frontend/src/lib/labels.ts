import type { Channel, DecisionState, GreenPurpose, OptionalProduct, Product, TrustStatus } from "../api/types";

export const PRODUCT_ORDER: Product[] = ["EV_FINANCE", "GREEN_HOME", "SOLAR_FINANCE", "PAPERLESS_BANKING"];

export const PRODUCTS: Record<Product, { name: string; short: string; blurb: string }> = {
  EV_FINANCE: { name: "EV Finance", short: "EV", blurb: "Finance to switch from a petrol or diesel car to an electric one." },
  GREEN_HOME: { name: "Green Home", short: "Home", blurb: "Finance for insulation, heat pumps and other home efficiency upgrades." },
  SOLAR_FINANCE: { name: "Solar Finance", short: "Solar", blurb: "Finance for rooftop solar panels." },
  PAPERLESS_BANKING: { name: "Paperless Banking", short: "Paperless", blurb: "Switching paper statements to digital delivery." },
};

export function productName(product: string): string {
  return PRODUCTS[product as Product]?.name ?? product;
}

export type Tone = "supported" | "info" | "conflict" | "neutral" | "muted" | "stopped";

/** Plain-language wording for the six relevance states. Order matches chart stacking. */
export const STATES: Record<DecisionState, { label: string; short: string; tone: Tone; help: string }> = {
  RECOMMEND: {
    label: "Supported opportunity", short: "Supported", tone: "supported",
    help: "Current evidence and the model's likelihood both support raising this product.",
  },
  INSUFFICIENT_INFORMATION: {
    label: "More evidence needed", short: "Needs evidence", tone: "info",
    help: "Key evidence is missing or unusual, so the system holds back. Abstaining is a valid result.",
  },
  CONFLICT_REQUIRES_REVIEW: {
    label: "Conflicting records", short: "Conflict", tone: "conflict",
    help: "Customer records disagree with each other. A person should review them before any outreach.",
  },
  DO_NOT_RECOMMEND: {
    label: "Not recommended", short: "Not recommended", tone: "neutral",
    help: "The model's likelihood is below this product's cut-off.",
  },
  NOT_APPLICABLE: {
    label: "Already adopted or not applicable", short: "Not applicable", tone: "muted",
    help: "The customer already has this, or a precondition (like owning a home) isn't met.",
  },
  SUPPRESSED: {
    label: "Contact suppressed", short: "Suppressed", tone: "stopped",
    help: "Contact isn't allowed, for example because marketing consent was withdrawn.",
  },
};

export const STATE_ORDER = Object.keys(STATES) as DecisionState[];

export function stateLabel(state: string): string {
  return STATES[state as DecisionState]?.label ?? state;
}

export const TRUST: Record<TrustStatus, { label: string; help: string }> = {
  TRUSTED: { label: "Trusted", help: "Evidence is complete, current and consistent." },
  LIMITED: { label: "Limited", help: "Some evidence is missing or out of date." },
  CONFLICT: { label: "Conflicting", help: "Sources disagree with each other." },
  OOD: { label: "Unusual profile", help: "This customer looks unlike the data the models were trained on (out of distribution)." },
};

export function trustLabel(status: string | undefined): string {
  return TRUST[status as TrustStatus]?.label ?? status ?? "Not available";
}

export const CHANNELS: Record<Channel, string> = {
  rm: "Relationship manager",
  app: "In-app",
  email: "Email",
  phone: "Phone",
};
export const CHANNEL_ORDER: Channel[] = ["rm", "app", "email", "phone"];

/** Next-action rule outputs, phrased as instructions for the person contacting the customer. */
export const NEXT_ACTIONS: Record<string, { label: string; tone: Tone }> = {
  RM_DISCUSSION: { label: "Discuss at the next contact", tone: "supported" },
  SHOW_EDUCATION: { label: "Show in the app", tone: "supported" },
  REQUEST_CONSENT: { label: "Ask for contact consent first", tone: "info" },
  REQUEST_INFORMATION: { label: "Collect the missing information", tone: "info" },
  REQUEST_REVIEW: { label: "Review before any contact", tone: "conflict" },
  DEFER: { label: "Hold off for now", tone: "neutral" },
  SUPPRESS: { label: "Don't contact about this", tone: "stopped" },
};

export function nextActionLabel(action: string | undefined): string {
  return (action && NEXT_ACTIONS[action]?.label) ?? action ?? "Not available";
}

export const RESPONSES: { value: string; label: string; help: string }[] = [
  { value: "INTERESTED", label: "Interested", help: "Moves the journey to engaged." },
  { value: "LATER", label: "Ask again later", help: "Pauses outreach for 30 days." },
  { value: "NOT_INTERESTED", label: "Not interested", help: "Starts a 60-day cooling-off period." },
  { value: "SHOWN", label: "Shown to customer", help: "Records that the customer saw it." },
  { value: "ACCEPTED", label: "Accepted", help: "Customer accepted the offer to proceed." },
  { value: "ALREADY_COMPLETED", label: "Already done", help: "Customer says they've already done this. Stops outreach." },
  { value: "DO_NOT_SHOW_AGAIN", label: "Don't show again", help: "Stops outreach for this product." },
  { value: "CLOSED", label: "Close the journey", help: "Only possible after the journey is completed." },
];

export const REVIEW_ACTIONS: { value: string; label: string; help: string }[] = [
  { value: "ACCEPT", label: "Accept", help: "The evidence looks right; outreach can follow the normal rules." },
  { value: "REQUEST_REVIEW", label: "Request a second review", help: "Holds outreach until someone else looks at it." },
  { value: "FLAG_DATA_ISSUE", label: "Flag a data issue", help: "Holds outreach and marks the records as needing a fix." },
  { value: "SUPPRESS", label: "Suppress outreach", help: "Stops contact about this product." },
];

export const LIFECYCLE: Record<string, string> = {
  RECOMMENDED: "Recommended",
  SHOWN: "Shown",
  ENGAGED: "Engaged",
  DECLINED: "Declined",
  WITHHELD: "Paused",
  COMPLETED: "Completed",
  SUPPRESSED: "Suppressed",
  ACCEPTED: "Accepted",
  CLOSED: "Closed",
  RESCORED: "Rescored",
};

/** Approved Boolean relevance evidence on the product snapshot. */
export const FEATURES: Record<string, string> = {
  marketing_consent: "Marketing consent given",
  owns_vehicle: "Owns a vehicle",
  ev_interest: "Interested in electric vehicles",
  fuel_supported: "Fuel spending supports the case",
  already_has_ev: "Already has an EV",
  owns_home: "Owns their home",
  retrofit_interest: "Interested in home upgrades",
  efficient_home: "Home already efficient",
  roof_available: "Suitable roof available",
  solar_interest: "Interested in solar",
  solar_installed: "Solar already installed",
  paper_statements: "Receives paper statements",
  paperless_consent: "Agreed to paperless",
  paperless_active: "Already paperless",
};

export function featureLabel(field: string): string {
  return FEATURES[field] ?? humanField(field);
}

const FIELD_WORDS: Record<string, string> = {
  kwh: "kWh", km: "km", "12m": "(12 months)", "90d": "(90 days)", "3m": "(3 months)", "30d": "(30 days)",
  avg: "average", txn: "transactions", ev: "EV", ice: "petrol/diesel", ood: "OOD", rm: "RM", co2: "CO₂", wtw: "WTW",
};

/** Turns model feature names like fuel_spend_90d_avg into "Fuel spend (90 days) average". */
export function humanField(field: string): string {
  const words = field.split(/[_.]+/).filter(Boolean).map((word) => FIELD_WORDS[word.toLowerCase()] ?? word.toLowerCase());
  const text = words.join(" ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** RM wording for the trained models' reason codes (from reason_codes.py). */
export const MODEL_REASONS: Record<string, string> = {
  ICE_VEHICLE_OWNER: "Drives a petrol or diesel car.",
  HIGH_FUEL_SPEND: "Monthly fuel spend over the last 90 days is in the top quarter of customers.",
  HIGH_ANNUAL_MILEAGE: "Annual mileage is in the top quarter of customers (may be estimated).",
  OLDER_VEHICLE: "Vehicle is older than most customers' vehicles.",
  EXISTING_VEHICLE_FINANCE: "Already has vehicle finance on record.",
  HOMEOWNER: "Recorded as a homeowner.",
  MORTGAGE_CUSTOMER: "Holds an active mortgage.",
  NO_EXISTING_SOLAR: "No existing solar installation on record.",
  HIGH_ELECTRICITY_USE: "Estimated electricity use is in the top quarter of customers.",
  HIGH_GAS_USE: "Estimated gas use is in the top quarter of customers.",
  RECENT_HOME_IMPROVEMENT_SPEND: "Recent home-improvement spending is above typical levels.",
  UTILITY_SPEND_RISING: "Utility spend in the last 90 days is over 10% above the 12-month average.",
  PAPER_STATEMENTS_ACTIVE: "Received at least one paper statement in the last 3 months.",
  HIGH_DIGITAL_ENGAGEMENT: "Uses the app more than most customers.",
  STATED_SUSTAINABILITY_PREFERENCE: "Said sustainability matters to them (4 or 5 out of 5).",
};

/** Sensitivity inputs approved by the API, per product, and whether they're actionable. */
export const SENSITIVITY_FIELDS: Record<Product, { field: string; label: string; max: number; kind: "contextual" | "actionable" }[]> = {
  EV_FINANCE: [
    { field: "annual_mileage_km", label: "Annual mileage, km", max: 200000, kind: "contextual" },
    { field: "fuel_spend_90d_avg", label: "Average monthly fuel spend (90 days), £", max: 10000, kind: "contextual" },
  ],
  GREEN_HOME: [
    { field: "electricity_kwh_12m", label: "Electricity use (12 months), kWh", max: 200000, kind: "contextual" },
    { field: "gas_kwh_12m", label: "Gas use (12 months), kWh", max: 500000, kind: "contextual" },
  ],
  SOLAR_FINANCE: [
    { field: "electricity_kwh_12m", label: "Electricity use (12 months), kWh", max: 200000, kind: "contextual" },
  ],
  PAPERLESS_BANKING: [
    { field: "paper_statements_12m", label: "Paper statements (12 months)", max: 1000, kind: "actionable" },
    { field: "app_logins_3m_avg", label: "Average monthly app logins (3 months)", max: 10000, kind: "contextual" },
  ],
};

/** Demo walkthrough personas, keyed by the IDs each provider mode ships with. */
export const PERSONAS: { id: string; title: string; note: string }[] = [
  { id: "C10001", title: "EV candidate", note: "Petrol driver with high fuel spend." },
  { id: "C10002", title: "Solar candidate", note: "Homeowner with Green Home and Solar signals." },
  { id: "C10003", title: "Paperless candidate", note: "Renter who still gets paper statements." },
  { id: "C10004", title: "Conflicting records", note: "EV records disagree; needs a review." },
  { id: "C10005", title: "Sparse evidence", note: "Shows responsible abstention." },
  { id: "C10006", title: "Already green", note: "Already holds most products." },
  { id: "GP-001", title: "Supported", note: "All four products are supported." },
  { id: "GP-002", title: "Missing evidence", note: "Shows responsible abstention." },
  { id: "GP-003", title: "Conflicting records", note: "Declarations disagree; needs a review." },
  { id: "GP-004", title: "Already adopted", note: "Has already taken up every product." },
  { id: "GP-005", title: "Contact suppressed", note: "Marketing consent withdrawn." },
  { id: "GP-006", title: "Low likelihood", note: "Below the cut-off for every product." },
];

export const FUNNEL: { key: string; label: string }[] = [
  { key: "analyzed_customers", label: "Customers analysed" },
  { key: "in_population_scored_opportunities", label: "Product decisions scored" },
  { key: "supported_opportunities", label: "Supported opportunities" },
  { key: "supported_with_validated_confidence", label: "With validated confidence" },
  { key: "supported_with_high_confidence", label: "With high confidence" },
];

export const QUALITY_ORDER: TrustStatus[] = ["TRUSTED", "LIMITED", "CONFLICT", "OOD"];

/** Customer wording for the same reason codes (customer_wording in reason_codes.py). */
export const CUSTOMER_REASONS: Record<string, string> = {
  ICE_VEHICLE_OWNER: "You drive a petrol or diesel car.",
  HIGH_FUEL_SPEND: "Your monthly fuel spend is higher than most customers'.",
  HIGH_ANNUAL_MILEAGE: "You drive more miles each year than most customers.",
  OLDER_VEHICLE: "Your car is older than most.",
  EXISTING_VEHICLE_FINANCE: "You already finance your car, so you are used to spreading the cost.",
  HOMEOWNER: "You own your home.",
  MORTGAGE_CUSTOMER: "You have a mortgage with us.",
  NO_EXISTING_SOLAR: "We have no record of solar panels at your home.",
  HIGH_ELECTRICITY_USE: "Your estimated annual electricity use is higher than most customers'.",
  HIGH_GAS_USE: "Your estimated annual gas use is higher than most customers'.",
  RECENT_HOME_IMPROVEMENT_SPEND: "You have recently spent money on improving your home.",
  UTILITY_SPEND_RISING: "Your utility bills have been rising recently.",
  PAPER_STATEMENTS_ACTIVE: "You are still receiving paper statements.",
  HIGH_DIGITAL_ENGAGEMENT: "You use our app more often than most customers.",
  STATED_SUSTAINABILITY_PREFERENCE: "You told us that sustainability matters to you.",
};

/** Customer-facing call to action per product. Targets are placeholders until built (UI_FEATURE_BACKLOG.md). */
export const PRODUCT_CTAS: Record<Product, { label: string; backlog: string }> = {
  EV_FINANCE: { label: "Explore EV options", backlog: "EV options explorer" },
  GREEN_HOME: { label: "Explore home upgrades", backlog: "Home upgrade explorer" },
  SOLAR_FINANCE: { label: "Explore solar for your home", backlog: "Solar explorer" },
  PAPERLESS_BANKING: { label: "Go paperless", backlog: "Paperless switch" },
};

export const OPTIONAL_PRODUCTS: Record<OptionalProduct, { name: string; blurb: string; cta: string; guardrail: string }> = {
  GREEN_INVESTMENTS: {
    name: "Green Investments",
    blurb: "Sustainable funds and investment options for customers who already invest.",
    cta: "Explore green investments",
    guardrail: "Not investment advice. It does not assess financial suitability or eligibility.",
  },
  GREEN_LOANS: {
    name: "Green Loans",
    blurb: "Lending for a declared green purpose, such as insulation, a heat pump or EV charging.",
    cta: "Start a green loan enquiry",
    guardrail: "Opportunity signal only. No credit approval or eligibility check.",
  },
};

export const OPTIONAL_STATUS: Record<string, { label: string; tone: Tone; help: string }> = {
  OPPORTUNITY_SIGNAL: { label: "Opportunity signal", tone: "supported", help: "The experimental model's likelihood meets its cut-off." },
  LOW_RELEVANCE: { label: "Low relevance", tone: "neutral", help: "The experimental model's likelihood is below its cut-off." },
  NOT_RELEVANT: { label: "Not relevant", tone: "muted", help: "A precondition isn't met, such as existing investments or borrowing." },
  INSUFFICIENT_INFORMATION: { label: "More information needed", tone: "info", help: "Evidence is missing or conflicting, so nothing is scored." },
  NOT_AVAILABLE: { label: "Not available", tone: "muted", help: "The experimental models aren't loaded for this customer." },
};

export const OPTIONAL_REASONS: Record<string, string> = {
  EXISTING_INVESTMENT_ACTIVITY: "Already holds investments.",
  STATED_SUSTAINABILITY_PREFERENCE: "Said sustainability matters to them.",
  HIGH_DIGITAL_ENGAGEMENT: "Uses the app more than most customers.",
  NO_EXISTING_INVESTMENT_ACTIVITY: "No existing investment activity on record.",
  INVESTMENT_HOLDING_OR_PREFERENCE_UNKNOWN: "Investment holdings or sustainability preference are unknown.",
  EXISTING_BORROWING_RELATIONSHIP: "Already borrows with us (mortgage or vehicle finance).",
  EXISTING_BORROWING_NOT_CONFIRMED: "No existing borrowing relationship is confirmed.",
  DOCUMENTED_GREEN_PURPOSE_REQUIRED: "Choose a declared green purpose to score a green loan.",
  DECLARED_GREEN_PURPOSE_INSULATION: "Declared purpose: insulation.",
  DECLARED_GREEN_PURPOSE_HEAT_PUMP: "Declared purpose: heat pump.",
  DECLARED_GREEN_PURPOSE_EV_CHARGING: "Declared purpose: EV charging.",
  RECENT_HOME_IMPROVEMENT_ACTIVITY: "Recent home-improvement spending is above typical levels.",
  HIGH_HEATING_ENERGY_USE: "Heating energy use is above typical levels.",
  TRUSTED_RECORD_CONFLICT: "Customer records conflict, so nothing is scored until they're reviewed.",
  TRAINED_SOURCE_REQUIRED: "Needs a trained Customer 360 record.",
  INVALID_PRODUCT_RECORDS: "Product records failed validation.",
  OPTIONAL_MODEL_CUTOFF_MISMATCH: "The experimental model was trained for a different data date.",
};

export const GREEN_PURPOSES: { value: GreenPurpose | ""; label: string }[] = [
  { value: "", label: "No purpose declared" },
  { value: "INSULATION", label: "Insulation" },
  { value: "HEAT_PUMP", label: "Heat pump" },
  { value: "EV_CHARGING", label: "EV charging" },
];
