import { useId, useState } from "react";
import { ArrowUpRight, Check, ExternalLink, Leaf, ShieldCheck } from "lucide-react";
import type { DecisionState } from "../../api/types";
import { usePartnerCatalogue, type PartnerOption, type PartnerProduct, type PartnerCatalogue } from "../../api/partners";
import { Callout, Empty, ErrorBox, Loading } from "../../components/ui";
import { STATES } from "../../lib/labels";
import { PartnerIllustration } from "./PartnerIllustration";

export function ExploreTab({ product, state }: { product: PartnerProduct; state: DecisionState }) {
  const catalogue = usePartnerCatalogue();

  if (catalogue.isPending) return <Loading label="Loading illustrative partner routes…" />;
  if (catalogue.isError) return <ErrorBox error={catalogue.error} what="partner catalogue" />;
  if (!catalogue.data) return <Empty title="Partner options aren't available yet." />;

  return <ExploreCatalogueView catalogue={catalogue.data} product={product} state={state} />;
}

/** Pure catalogue view is separate from fetching so its promotion/link rules can be verified. */
export function ExploreCatalogueView({ catalogue, product, state }: {
  catalogue: PartnerCatalogue; product: PartnerProduct; state: DecisionState;
}) {
  const category = catalogue.products.find((item) => item.product === product);
  const options = category?.options.filter((option) => option.promoted) ?? [];
  const headingId = `partner-journey-${product.toLowerCase()}`;

  if (!category || options.length === 0) {
    return <Empty title="No partner journeys are being shown for this product yet.">
      Lloyds can choose which partner options to promote here. No application or referral has been started.
    </Empty>;
  }

  const stateLabel = STATES[state]?.label ?? state;
  const illustrativeOnly = options.every((option) => option.placeholder);

  return (
    <section className="partner-explore" aria-labelledby={headingId}>
      <div className="partner-disclosure" role="note">
        <div className="partner-disclosure-mark"><ShieldCheck size={19} aria-hidden="true" /></div>
        <div>
          <p className="partner-disclosure-title">General research only — not a personalized offer</p>
          <p>{illustrativeOnly ? "Illustrative partner concepts, not live offers or eligibility decisions." : "Curated partner information, not an eligibility decision."}</p>
          <p className="partner-safety-line">Browsing doesn't contact a partner, submit an application, or share customer details. SUPPRESSED is never contact permission.</p>
        </div>
      </div>

      {state !== "RECOMMEND" && (
        <Callout kind="warn" title={`Decision context: ${stateLabel}`}>
          These options are general research and do not override the current decision or make this a personalized offer.
        </Callout>
      )}

      <header className="partner-explore-hero">
        <div className="partner-explore-copy">
          <span className="partner-eyebrow"><Leaf size={14} aria-hidden="true" /> {category.hero_tag}</span>
          <h3 id={headingId}>{category.title}</h3>
          <p>{category.subtitle}</p>
          <span className="partner-research-note">Explore at your own pace · No eligibility check</span>
        </div>
        <PartnerIllustration product={product} />
      </header>

      <div className="partner-options-heading">
        <div>
          <h4>Partner routes to explore</h4>
          <p>{options.length} {illustrativeOnly ? "illustrative" : "partner"} {options.length === 1 ? "route" : "routes"} in this shortlist</p>
        </div>
        <span className="partner-tag"><Leaf size={13} aria-hidden="true" /> {illustrativeOnly ? "Illustrative only" : "Curated partner options"}</span>
      </div>

      <div className="partner-option-grid">
        {options.map((option) => <PartnerOptionCard key={option.id} option={option} />)}
      </div>
      <details className="partner-catalogue-notes">
        <summary tabIndex={0}>About the catalogue &amp; proposed commercial model</summary>
        <div><p>{catalogue.disclaimer}</p><p>{catalogue.commercial_disclaimer}</p></div>
      </details>
      <p className="partner-version">Catalogue {catalogue.version} · reviewed {catalogue.reviewed_on}</p>
    </section>
  );
}

function PartnerOptionCard({ option }: { option: PartnerOption }) {
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const detailId = `partner-route-${useId()}`;
  const destination = !option.placeholder ? safeHttpsUrl(option.destination_url) : null;
  const sourceUrl = !option.placeholder ? safeHttpsUrl(option.source?.url ?? null) : null;

  return (
    <article className="partner-option">
      <div className="partner-option-ribbon">
        <span>{option.placeholder ? "Illustrative offer" : "Partner option"}</span>
        {option.placeholder && <span>Demo partner</span>}
      </div>
      <div className="partner-option-head">
        <div>
          <p className="partner-relationship">{option.relationship}</p>
          <p className="partner-name">{option.partner}</p>
        </div>
        <span className="partner-option-mark" aria-hidden="true"><Leaf size={17} /></span>
      </div>
      <h5 className="partner-option-title">{option.title}</h5>
      <p className="partner-option-summary">{option.summary}</p>
      <ul className="partner-highlights">
        {option.highlights.map((highlight, index) => (
          <li key={`${index}-${highlight}`}><Check size={15} aria-hidden="true" />{highlight}</li>
        ))}
      </ul>
      <div className="partner-suitability"><b>May suit</b><p>{option.suitability}</p></div>
      <p className="partner-option-disclosure">{option.disclosure}</p>

      <div className="partner-option-actions">
        <button className="btn btn-quiet" type="button" aria-expanded={detailsOpen} aria-controls={detailId}
          onClick={() => setDetailsOpen((open) => !open)}>
          {detailsOpen ? "Hide route details" : "View details"}
        </button>
        {option.placeholder ? (
          <button className="btn btn-primary" type="button" aria-expanded={previewOpen}
            aria-controls={`${detailId}-preview`} onClick={() => setPreviewOpen((open) => !open)}>
            Preview partner handoff <ArrowUpRight size={15} aria-hidden="true" />
          </button>
        ) : destination ? (
          <a className="btn btn-primary" href={destination} target="_blank" rel="noopener noreferrer" referrerPolicy="no-referrer">
            Open partner site: {option.cta_label} <ExternalLink size={14} aria-hidden="true" />
          </a>
        ) : (
          <span className="partner-handoff-unavailable">Partner handoff link unavailable</span>
        )}
      </div>

      <div className="partner-route-detail" id={detailId} hidden={!detailsOpen}>
        <div>
          <span className="partner-detail-label">Proposed revenue path</span>
          <p>{option.revenue_path || "No revenue path configured."}</p>
          <p className="partner-route-caveat">Proposal only — not an approved commercial offer or referral.</p>
        </div>
        {sourceUrl && option.source ? (
          <a className="partner-source-link" href={sourceUrl} target="_blank" rel="noopener noreferrer" referrerPolicy="no-referrer">
            Official source: {option.source.label} <ExternalLink size={13} aria-hidden="true" />
          </a>
        ) : (
          <p className="partner-no-source">{option.placeholder ? "Demo concept. An approved partner product and its source can be configured later." : "No valid official source link is available for this option."}</p>
        )}
      </div>

      {option.placeholder && (
        <div className="partner-preview" id={`${detailId}-preview`} role="status" aria-live="polite" hidden={!previewOpen}>
          <ShieldCheck size={17} aria-hidden="true" />
          <div>
            <b>Demo handoff preview</b>
            <p>No application submitted / No details shared. This is a local preview only.</p>
          </div>
        </div>
      )}
    </article>
  );
}

function safeHttpsUrl(value: string | null): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    if (url.protocol !== "https:" || !url.hostname || url.username || url.password) return null;
    return url.href;
  } catch {
    return null;
  }
}
