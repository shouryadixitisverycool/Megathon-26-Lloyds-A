import { useQuery } from "@tanstack/react-query";
import { api } from "./client";

export type PartnerProduct = "EV_FINANCE" | "SOLAR_FINANCE" | "GREEN_HOME";

export interface PartnerCatalogue {
  version: string;
  reviewed_on: string;
  disclaimer: string;
  commercial_disclaimer: string;
  products: PartnerCategory[];
}

export interface PartnerCategory {
  product: PartnerProduct;
  title: string;
  subtitle: string;
  hero_tag: string;
  options: PartnerOption[];
}

export interface PartnerOption {
  id: string;
  partner: string;
  relationship: string;
  title: string;
  summary: string;
  highlights: string[];
  suitability: string;
  disclosure: string;
  revenue_path: string;
  source: { label: string; url: string } | null;
  destination_url: string | null;
  cta_label: string;
  placeholder: boolean;
  promoted: boolean;
}

/** Shared, customer-independent catalogue; reading it never creates an application or referral. */
export function usePartnerCatalogue() {
  return useQuery({
    queryKey: ["partners", "catalogue"],
    staleTime: 5 * 60_000,
    queryFn: async ({ signal }): Promise<PartnerCatalogue> => {
      const catalogue = await api.get<PartnerCatalogue>("/partners/catalogue", undefined, signal);
      if (!Array.isArray(catalogue.products)) {
        throw new Error("The partner catalogue has an unexpected shape.");
      }
      return catalogue;
    },
  });
}
