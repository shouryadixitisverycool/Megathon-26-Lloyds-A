import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, customerPath, requestId } from "./client";
import type {
  Channel, CounterfactualResult, CustomerIndexEntry, CustomerSnapshot, EvidenceGraph, Explanation,
  GovernanceDiagnostics, Health, HistoryResponse, PlanResult, PortfolioSummary, PortfolioTrends,
  Preferences, Product, Recommendation, SensitivityResult, ShapAudit, SimulationResult, SimulationTemplate,
} from "./types";

// Mirrors the Streamlit cache: responses are reused for 15 seconds unless refreshed.
export const STALE_MS = 15_000;

export function useHealth() {
  // Never trust a cached health result to hide an unreachable service.
  return useQuery({
    queryKey: ["health"],
    queryFn: ({ signal }) => api.get<Health>("/health", undefined, signal),
    staleTime: 0,
    refetchInterval: 30_000,
    retry: 1,
  });
}

/** The trained list is ~38 MB, so keep only what the directory needs. */
export function useCustomerIndex(enabled = true) {
  return useQuery({
    queryKey: ["customers"],
    enabled,
    staleTime: 5 * 60_000,
    queryFn: async ({ signal }): Promise<CustomerIndexEntry[]> => {
      const rows = await api.get<CustomerSnapshot[]>("/customers", undefined, signal);
      if (!Array.isArray(rows)) throw new Error("The customer list has an unexpected shape.");
      return rows.map((row) => ({
        customer_id: row.customer_id,
        display_name: row.display_name,
        region: row.region,
        segment: row.segment,
        trust_score: row.trust?.score,
        trust_status: row.trust?.status,
        feature_cutoff: row.feature_cutoff,
        decision_profile: row.decision_profile,
      }));
    },
  });
}

export function useCustomer(customerId: string | undefined) {
  return useQuery({
    queryKey: ["customer", customerId],
    enabled: !!customerId,
    staleTime: STALE_MS,
    queryFn: ({ signal }) => api.get<CustomerSnapshot>(customerPath(customerId!), undefined, signal),
  });
}

/** Next actions return every decision plus priority and the per-channel next step. */
export function useNextActions(customerId: string | undefined, channel: Channel) {
  return useQuery({
    queryKey: ["customer", customerId, "next-actions", channel],
    enabled: !!customerId,
    staleTime: STALE_MS,
    placeholderData: keepPreviousData,
    queryFn: async ({ signal }) =>
      (await api.get<{ opportunities: Recommendation[] }>(customerPath(customerId!, "/next-actions"), { channel }, signal)).opportunities,
  });
}

export function useExplanation(customerId: string, product: Product | undefined) {
  return useQuery({
    queryKey: ["customer", customerId, "explanation", product],
    enabled: !!product,
    staleTime: STALE_MS,
    queryFn: ({ signal }) => api.get<Explanation>(customerPath(customerId, `/explanations/${product}`), undefined, signal),
  });
}

export function usePreferences(customerId: string) {
  return useQuery({
    queryKey: ["customer", customerId, "preferences"],
    staleTime: STALE_MS,
    queryFn: ({ signal }) => api.get<Preferences>(customerPath(customerId, "/preferences"), undefined, signal),
  });
}

export function useHistory(customerId: string, product?: Product) {
  return useQuery({
    queryKey: ["customer", customerId, "history", product ?? "ALL"],
    staleTime: STALE_MS,
    queryFn: ({ signal }) => api.get<HistoryResponse>(customerPath(customerId, "/history"), product ? { product } : undefined, signal),
  });
}

export function useEvidenceGraph(customerId: string, product: Product) {
  return useQuery({
    queryKey: ["customer", customerId, "graph", product],
    staleTime: STALE_MS,
    queryFn: ({ signal }) => api.get<EvidenceGraph>(customerPath(customerId, `/evidence-graph/${product}`), undefined, signal),
  });
}

export function useSimulationTemplate(customerId: string, product: Product) {
  return useQuery({
    queryKey: ["customer", customerId, "simulation-inputs", product],
    staleTime: STALE_MS,
    retry: false,
    queryFn: ({ signal }) => api.get<SimulationTemplate>(customerPath(customerId, `/simulation-inputs/${product}`), undefined, signal),
  });
}

export function useShap(customerId: string, product: Product, enabled: boolean) {
  return useQuery({
    queryKey: ["customer", customerId, "shap", product],
    enabled,
    staleTime: 5 * 60_000,
    queryFn: ({ signal }) => api.get<ShapAudit>(customerPath(customerId, `/shap/${product}`), undefined, signal),
  });
}

export type PortfolioFilters = { region?: string; segment?: string; product?: Product };

export function usePortfolioSummary(filters: PortfolioFilters) {
  return useQuery({
    queryKey: ["portfolio", "summary", filters],
    staleTime: STALE_MS,
    placeholderData: keepPreviousData,
    queryFn: ({ signal }) => api.get<PortfolioSummary>("/portfolio/summary", filters, signal),
  });
}

export function usePortfolioTrends(filters: PortfolioFilters) {
  return useQuery({
    queryKey: ["portfolio", "trends", filters],
    staleTime: STALE_MS,
    placeholderData: keepPreviousData,
    queryFn: ({ signal }) => api.get<PortfolioTrends>("/portfolio/trends", filters, signal),
  });
}

export type OpportunityParams = PortfolioFilters & {
  status?: string; data_quality?: string;
  min_propensity?: string; min_trust?: string; min_confidence?: string; min_impact?: string;
};

/** Trained scoring re-runs every customer, so results stay cached until refreshed. */
export function useOpportunities(params: OpportunityParams | null) {
  return useQuery({
    queryKey: ["portfolio", "opportunities", params],
    enabled: params !== null,
    staleTime: 10 * 60_000,
    gcTime: 15 * 60_000,
    retry: false,
    queryFn: async ({ signal }) => {
      const result = await api.get<{ opportunities: Recommendation[]; disclaimer: string }>("/portfolio/opportunities", params!, signal);
      // Drop the heavy provenance copies; the table and matrix only need decision fields.
      return {
        disclaimer: result.disclaimer,
        opportunities: result.opportunities.map(({ provenance: _provenance, ...row }) => ({
          ...row,
          impact: { ...row.impact, factors: [], evidence: [] },
        })) as Recommendation[],
      };
    },
  });
}

export function useGovernance() {
  return useQuery({
    queryKey: ["governance"],
    staleTime: 60_000,
    queryFn: ({ signal }) => api.get<GovernanceDiagnostics>("/governance/diagnostics", undefined, signal),
  });
}

export function useExplanationMetrics() {
  return useQuery({
    queryKey: ["explanation-metrics"],
    staleTime: STALE_MS,
    queryFn: ({ signal }) => api.get<Record<string, unknown>>("/explanations/metrics", undefined, signal),
  });
}

export function useAuditEvent(eventId: string | null) {
  return useQuery({
    queryKey: ["audit", eventId],
    enabled: !!eventId,
    retry: false,
    queryFn: ({ signal }) => api.get<Record<string, unknown>>(`/audit/recommendations/${encodeURIComponent(eventId!)}`, undefined, signal),
  });
}

/** Every write carries a fresh idempotency key and refreshes cached reads afterwards. */
export function useSave<TResult = Record<string, unknown>>(path: string, invalidate: unknown[][] = []) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (payload: Record<string, unknown>) => api.post<TResult>(path, { ...payload, request_id: requestId() }),
    onSuccess: () => {
      for (const key of invalidate) client.invalidateQueries({ queryKey: key });
    },
  });
}

export type {
  SimulationResult, SensitivityResult, CounterfactualResult, PlanResult,
};
