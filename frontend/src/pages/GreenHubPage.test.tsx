import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import type { CustomerSnapshot, Product, Recommendation } from "../api/types";

const hooks = vi.hoisted(() => ({
  useCustomer: vi.fn(),
  useNextActions: vi.fn(),
  useOptionalOpportunities: vi.fn(),
}));

vi.mock("../api/hooks", () => hooks);

import { GreenHubPage } from "./GreenHubPage";

const customerId = "customer-1";
const snapshot = {
  customer_id: customerId,
  display_name: "Alex Example",
  feature_cutoff: "2026-10-01",
} as CustomerSnapshot;

function recommendation(product: Product, id = customerId, state: Recommendation["state"] = "RECOMMEND", action = "SHOW"): Recommendation {
  return {
    customer_id: id,
    product,
    state,
    propensity: null,
    impact: { product, status: "UNAVAILABLE", value: null, units: "" },
    next_action: { action, reason: "Supported", channel: "app", version: "test" },
  } as Recommendation;
}

function markup(id = customerId) {
  return renderToStaticMarkup(
    <MemoryRouter initialEntries={[`/customers/${id}/hub`]}>
      <Routes><Route path="/customers/:customerId/hub" element={<GreenHubPage />} /></Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  hooks.useCustomer.mockReturnValue({ data: snapshot, isError: false });
  hooks.useNextActions.mockReturnValue({
    data: [recommendation("EV_FINANCE"), recommendation("SOLAR_FINANCE"), recommendation("GREEN_HOME")],
    isError: false,
    isPending: false,
    isPlaceholderData: false,
  });
  hooks.useOptionalOpportunities.mockReturnValue({
    data: { customer_id: customerId, opportunities: [] },
    isError: false,
    isPlaceholderData: false,
  });
});

describe("Green Hub partner journeys", () => {
  it("renders real catalogue buttons for EV, solar, and green home while leaving paperless as a placeholder", () => {
    const html = markup();

    expect(html).toContain("Explore EV options");
    expect(html).toContain("Explore solar for your home");
    expect(html).toContain("Explore home upgrades");
    expect(html).not.toContain('data-placeholder="EV options explorer"');
    expect(html).not.toContain('data-placeholder="Solar explorer"');
    expect(html).not.toContain('data-placeholder="Home upgrade explorer"');
  });

  it("does not use cached placeholder action rows for another customer", () => {
    const otherCustomer = { ...snapshot, customer_id: "customer-2", display_name: "Casey Example" } as CustomerSnapshot;
    hooks.useCustomer.mockReturnValue({ data: otherCustomer, isError: false });
    hooks.useNextActions.mockReturnValue({
      data: [recommendation("EV_FINANCE")],
      isError: false,
      isPending: true,
      isPlaceholderData: true,
    });

    const html = markup("customer-2");

    expect(html).toContain("Casey, here are your green opportunities");
    expect(html).not.toContain("Explore EV options");
  });

  it("does not surface partner buttons for decisions outside the supported hub filter", () => {
    hooks.useNextActions.mockReturnValue({
      data: [
        recommendation("EV_FINANCE", customerId, "SUPPRESSED"),
        recommendation("SOLAR_FINANCE", customerId, "RECOMMEND", "SUPPRESS"),
      ],
      isError: false,
      isPending: false,
      isPlaceholderData: false,
    });

    const html = markup();

    expect(html).toContain("No green suggestions right now");
    expect(html).not.toContain("Explore EV options");
    expect(html).not.toContain("Explore solar for your home");
  });
});
