import type { Explanation } from "../api/types";
import type { Tone } from "./labels";

/** Live counters from GET /explanations/metrics. provider_measurements exists only when a provider is configured. */
export interface ExplanationMetrics {
  requests: number;
  cache_hits: number;
  cache_misses: number;
  cache_hit_rate: number;
  average_latency_ms: number | null;
  provider_attempts: number;
  provider_completed: number;
  live_provider_latency_ms: number | null;
  prompt_version: string;
  model_version: string;
  locale: string;
  offline_cost: number | null;
  live_provider_cost: number | null;
  provider_measurements?: {
    model?: string;
    model_version?: string;
    completed_calls?: number;
    attempted_calls?: number;
    average_input_tokens?: number | null;
    average_output_tokens?: number | null;
    total_input_tokens?: number | null;
    total_output_tokens?: number | null;
    measured_cost?: number | null;
    cost_per_1000_explanations?: number | null;
    pricing_basis?: string;
  };
}

/** The service reports zero offline cost only when no AI provider is attached. */
export function aiEnabled(metrics: ExplanationMetrics | undefined): boolean | undefined {
  if (!metrics) return undefined;
  return metrics.offline_cost !== 0;
}

export function aiModel(metrics: ExplanationMetrics | undefined): string | undefined {
  return metrics?.provider_measurements?.model_version ?? metrics?.provider_measurements?.model ?? (aiEnabled(metrics) ? metrics?.model_version : undefined);
}

/** Every reason the explanation service can fall back to its standard wording. */
const FALLBACKS: Record<string, { title: string; detail: string; retry?: boolean }> = {
  PROVIDER_NOT_CONFIGURED: {
    title: "AI writing is switched off",
    detail: "No AI key is set on the server, so the standard wording is used. It contains the same approved facts.",
  },
  PROVIDER_VERSION_NOT_CONFIGURED: {
    title: "AI writing isn't fully configured",
    detail: "The AI provider has no model version set, so the system won't use it.",
  },
  UNRECOGNIZED_REASON_CODE: {
    title: "Standard wording for this decision",
    detail: "This decision uses a reason the AI isn't approved to describe, so it wasn't asked.",
  },
  PROVIDER_BUSY: { title: "The AI service was busy", detail: "Too many explanations were being written at once.", retry: true },
  PROVIDER_TIMEOUT: { title: "The AI service took too long", detail: "It didn't answer within the time limit.", retry: true },
  PROVIDER_ERROR: { title: "The AI service returned an error", detail: "The request failed before a draft came back.", retry: true },
  SCHEMA_REJECTED: { title: "The AI draft was rejected", detail: "It wasn't in the required structured format." },
  CLAIMS_REJECTED: { title: "The AI draft was rejected", detail: "It changed a product, decision, number, unit or disclaimer." },
  SENTENCES_REJECTED: { title: "The AI draft was rejected", detail: "It added, repeated or dropped one of the approved sentences." },
};

export interface ExplanationOrigin {
  badge: string;
  tone: Tone;
  title?: string;
  detail: string;
  retry: boolean;
}

/** Plain-language account of who wrote an explanation and, if the AI wasn't used, why. */
export function explanationOrigin(explanation: Explanation): ExplanationOrigin {
  if (explanation.source === "llm") {
    return {
      badge: "Written by AI",
      tone: "supported",
      detail: "The AI chose and ordered pre-approved sentences. Every fact, number and disclaimer was checked before it was shown.",
      retry: false,
    };
  }
  const reason = explanation.fallback_reason ?? "PROVIDER_NOT_CONFIGURED";
  const fallback = FALLBACKS[reason] ?? { title: "The AI draft wasn't used", detail: `Reason: ${reason.toLowerCase().replace(/_/g, " ")}.` };
  const off = reason === "PROVIDER_NOT_CONFIGURED" || reason === "PROVIDER_VERSION_NOT_CONFIGURED";
  return {
    badge: off ? "Standard wording" : "Standard wording, AI draft not used",
    tone: off ? "muted" : "info",
    title: fallback.title,
    detail: fallback.detail,
    retry: fallback.retry ?? false,
  };
}
