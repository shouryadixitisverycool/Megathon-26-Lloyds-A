import type { Decimalish, Impact } from "../api/types";

/** Pydantic encodes Decimal as strings. Reject booleans and non-finite values. */
export function toNumber(value: Decimalish | boolean): number | null {
  if (value === null || value === undefined || typeof value === "boolean" || value === "") return null;
  const number = typeof value === "number" ? value : Number(value);
  return Number.isFinite(number) ? number : null;
}

/** A probability-like value as a percentage, or null when it is missing or out of range. */
export function percentValue(value: Decimalish): number | null {
  const number = toNumber(value);
  return number !== null && number >= 0 && number <= 1 ? number * 100 : null;
}

export function percentage(value: Decimalish, digits = 1): string {
  const number = percentValue(value);
  return number === null ? "Not available" : `${number.toFixed(digits)}%`;
}

const compact = new Intl.NumberFormat("en-GB", { notation: "compact", maximumFractionDigits: 1 });
const grouped = new Intl.NumberFormat("en-GB");

export function count(value: number | null | undefined): string {
  return value === null || value === undefined ? "Not available" : grouped.format(value);
}

export function compactCount(value: number): string {
  return Math.abs(value) >= 10_000 ? compact.format(value) : grouped.format(value);
}

export function decimal(value: Decimalish, digits = 1): string {
  const number = toNumber(value);
  if (number === null) return "Not available";
  return number.toLocaleString("en-GB", { minimumFractionDigits: 0, maximumFractionDigits: digits });
}

/** "kg CO2e/year" -> "kg CO₂e/yr" for display. The raw unit stays available in details. */
export function prettyUnit(unit: string | null | undefined): string {
  if (!unit) return "";
  return unit.replace(/CO2/g, "CO₂").replace(/\/year\b/, "/yr");
}

export function impactAvailable(impact: Pick<Impact, "status" | "value">): boolean {
  return impact.status === "AVAILABLE" && toNumber(impact.value) !== null;
}

/** Unavailable impact is never zero. Zero and negative values are preserved. */
export function impactLabel(impact: Pick<Impact, "status" | "value" | "units">): string {
  if (!impactAvailable(impact)) return "Not available";
  return `${decimal(impact.value, 1)} ${prettyUnit(impact.units)}`;
}

export function emissionsField(units: string): "emissions_kg_co2e" | "emissions_kg_co2" {
  return units.includes("CO2e") ? "emissions_kg_co2e" : "emissions_kg_co2";
}

const dateFormat = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
const dateTimeFormat = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
const monthFormat = new Intl.DateTimeFormat("en-GB", { month: "short", year: "2-digit", timeZone: "UTC" });

export function date(value: string | null | undefined): string {
  if (!value) return "Not available";
  const parsed = new Date(value.length === 10 ? value + "T00:00:00Z" : value);
  return Number.isNaN(parsed.getTime()) ? value : dateFormat.format(parsed);
}

export function dateTime(value: string | null | undefined): string {
  if (!value) return "Not available";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : dateTimeFormat.format(parsed);
}

export function month(value: string): string {
  const parsed = new Date(value + "-01T00:00:00Z");
  return Number.isNaN(parsed.getTime()) ? value : monthFormat.format(parsed);
}

/** "MASS_AFFLUENT" -> "Mass affluent", "annual_mileage_km" -> "Annual mileage km". */
export function humanize(value: string | null | undefined): string {
  if (!value) return "";
  const text = value.replace(/[_-]+/g, " ").trim().toLowerCase()
    .replace(/\bco2e\b/g, "CO₂e").replace(/\bco2\b/g, "CO₂").replace(/\b(ev|uk|ood|rm|api|llm|shap|wtw|kwh|auc|roc|pr|ece|ks|id|sha256)\b/g, (word) => word === "kwh" ? "kWh" : word.toUpperCase());
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** Python dict-repr periods ("{'start': ..., 'end': ...}") from aggregate groups. */
export function periodLabel(value: unknown): string {
  if (!value) return "Not available";
  if (typeof value === "object" && value !== null && "start" in value && "end" in value) {
    const period = value as { start: string; end: string };
    return `${date(period.start)} to ${date(period.end)}`;
  }
  const text = String(value);
  const match = text.match(/'start':\s*'([^']+)'.*'end':\s*'([^']+)'/);
  return match ? `${date(match[1])} to ${date(match[2])}` : text;
}

export function plural(n: number, one: string, many = one + "s"): string {
  return `${grouped.format(n)} ${n === 1 ? one : many}`;
}

export function listSentence(items: string[]): string {
  if (items.length <= 1) return items[0] ?? "";
  return `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;
}

export function shortHash(value: string | null | undefined, size = 12): string {
  if (!value) return "Not available";
  return value.length > size ? `${value.slice(0, size)}…` : value;
}

export function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "Not available";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") return Number.isInteger(value) ? grouped.format(value) : value.toLocaleString("en-GB", { maximumFractionDigits: 2 });
  if (typeof value === "string" && /^-?\d+(\.\d+)?$/.test(value)) return decimal(value, 2);
  if (Array.isArray(value)) return value.length ? value.map(displayValue).join(", ") : "None";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
