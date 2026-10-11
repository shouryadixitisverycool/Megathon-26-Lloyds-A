import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import type { PartnerCatalogue, PartnerOption } from "../../api/partners";
import { ExploreCatalogueView } from "./ExploreTab";

const placeholder: PartnerOption = {
  id: "demo-route",
  partner: "Green finance partner (demo)",
  relationship: "Illustrative partner relationship",
  title: "A more considered way to upgrade",
  summary: "Explore a sample financing route for a lower-carbon home project.",
  highlights: ["Flexible project scope", "Independent research first"],
  suitability: "People comparing home energy improvements.",
  disclosure: "Illustrative information only; no price or eligibility decision is shown.",
  revenue_path: "A proposed referral fee if a customer independently completes an eligible partner journey.",
  source: null,
  destination_url: null,
  cta_label: "Continue to partner",
  placeholder: true,
  promoted: true,
};

const catalogue: PartnerCatalogue = {
  version: "demo-v1",
  reviewed_on: "2026-10-11",
  disclaimer: "Placeholder partner routes for demonstration only.",
  commercial_disclaimer: "No current offer, rate, or commercial arrangement is represented.",
  products: [{
    product: "GREEN_HOME",
    title: "Make room for a greener home",
    subtitle: "Explore example ways to plan an energy-minded home project.",
    hero_tag: "Your home, your pace",
    options: [placeholder, { ...placeholder, id: "not-promoted", partner: "Hidden demo partner", promoted: false }],
  }],
};

describe("Explore partner catalogue view", () => {
  it("shows only promoted placeholder options as illustrative demo routes, with no active external link", () => {
    const html = renderToStaticMarkup(<ExploreCatalogueView catalogue={catalogue} product="GREEN_HOME" state="RECOMMEND" />);

    expect(html).toContain("Illustrative offer");
    expect(html).toContain("Demo partner");
    expect(html).toContain("Green finance partner (demo)");
    expect(html).not.toContain("Hidden demo partner");
    expect(html).toContain("View details");
    expect(html).toContain("Preview partner handoff");
    expect(html).not.toMatch(/<a[^>]+href=/);
    expect(html).toContain("SUPPRESSED is never contact permission");
    expect(html).toContain("No current offer, rate, or commercial arrangement is represented.");
    expect(html).toContain("About the catalogue &amp; proposed commercial model");
  });

  it("warns that a non-recommendation remains research rather than a personalized offer", () => {
    const html = renderToStaticMarkup(<ExploreCatalogueView catalogue={catalogue} product="GREEN_HOME" state="SUPPRESSED" />);

    expect(html).toContain("Decision context: Contact suppressed");
    expect(html).toContain("do not override the current decision");
  });

  it("allows an active partner destination only when it is HTTPS and never adds customer information", () => {
    const activeCatalogue: PartnerCatalogue = {
      ...catalogue,
      products: [{
        ...catalogue.products[0],
        options: [{ ...placeholder, placeholder: false, destination_url: "https://partner.example/route", source: { label: "Official terms", url: "http://example.test/terms" } }],
      }],
    };
    const html = renderToStaticMarkup(<ExploreCatalogueView catalogue={activeCatalogue} product="GREEN_HOME" state="RECOMMEND" />);

    expect(html).toContain('href="https://partner.example/route"');
    expect(html).toContain('rel="noopener noreferrer"');
    expect(html).toContain('referrerPolicy="no-referrer"');
    expect(html).not.toContain("http://example.test/terms");
    expect(html).not.toContain("customer_id");
  });

  it("does not activate an HTTP destination even when an option is not a placeholder", () => {
    const unsafeCatalogue: PartnerCatalogue = {
      ...catalogue,
      products: [{
        ...catalogue.products[0],
        options: [{ ...placeholder, placeholder: false, destination_url: "http://partner.example/route" }],
      }],
    };
    const html = renderToStaticMarkup(<ExploreCatalogueView catalogue={unsafeCatalogue} product="GREEN_HOME" state="RECOMMEND" />);

    expect(html).not.toContain('href="http://partner.example/route"');
    expect(html).toContain("Partner handoff link unavailable");
    expect(html).not.toContain("Preview partner handoff");
  });

  it("keeps the placeholder handoff as a hidden local demo confirmation, not a link", () => {
    const html = renderToStaticMarkup(<ExploreCatalogueView catalogue={catalogue} product="GREEN_HOME" state="RECOMMEND" />);

    expect(html).toContain("Preview partner handoff");
    expect(html).toContain('class="partner-preview"');
    expect(html).toContain('role="status" aria-live="polite" hidden=""');
    expect(html).toContain("No application submitted / No details shared.");
    expect(html).not.toMatch(/<a[^>]+href=/);
  });

  it("renders a useful empty state when no catalogue route is promoted", () => {
    const emptyCatalogue: PartnerCatalogue = {
      ...catalogue,
      products: [{ ...catalogue.products[0], options: [{ ...placeholder, promoted: false }] }],
    };
    const html = renderToStaticMarkup(<ExploreCatalogueView catalogue={emptyCatalogue} product="GREEN_HOME" state="DO_NOT_RECOMMEND" />);

    expect(html).toContain("No partner journeys are being shown");
    expect(html).not.toContain("Preview partner handoff");
  });

  it("keeps disclosure control IDs unique for arbitrary configured option IDs", () => {
    const configured: PartnerCatalogue = {
      ...catalogue,
      products: [{ ...catalogue.products[0], options: [
        { ...placeholder, id: "demo/route" },
        { ...placeholder, id: "demo?route" },
      ] }],
    };
    const html = renderToStaticMarkup(<ExploreCatalogueView catalogue={configured} product="GREEN_HOME" state="RECOMMEND" />);
    const ids = [...html.matchAll(/id="(partner-route-[^"]+)"/g)].map((match) => match[1]);
    expect(ids).toHaveLength(4);
    expect(new Set(ids).size).toBe(ids.length);
  });
});
