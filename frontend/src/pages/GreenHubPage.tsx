import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Check, ChevronDown, Eye } from "lucide-react";
import { useCustomer, useNextActions, useOptionalOpportunities } from "../api/hooks";
import type { CustomerSnapshot, Recommendation } from "../api/types";
import { PRODUCT_COLORS } from "../components/charts/common";
import { PlaceholderButton, PlaceholderPanel } from "../components/Placeholder";
import { ErrorBox, Loading, Unavailable } from "../components/ui";
import { date, impactAvailable, impactLabel, percentage } from "../lib/format";
import { CUSTOMER_REASONS, OPTIONAL_PRODUCTS, PRODUCT_CTAS, PRODUCTS, productName } from "../lib/labels";

const DISCLAIMER = "Seeing a suggestion doesn't mean you're eligible for, or approved for, any product.";

/**
 * Customer Green Hub preview: what the customer would see in the app. It shows only supported
 * opportunities the in-app channel may show, in customer wording, with no model internals.
 */
export function GreenHubPage() {
  const { customerId = "" } = useParams();
  const customer = useCustomer(customerId);
  const actions = useNextActions(customerId, "app");
  const optional = useOptionalOpportunities(customerId, "");
  const snapshot = customer.data;

  const shown = (actions.data ?? []).filter((row) => row.state === "RECOMMEND" && row.next_action?.action !== "SUPPRESS");
  const extras = (optional.data?.opportunities ?? []).filter((row) => row.status === "OPPORTUNITY_SIGNAL");
  const firstName = snapshot && !snapshot.display_name.startsWith("Synthetic customer") ? snapshot.display_name.split(" ")[0] : null;

  return (
    <div className="page hub">
      <div className="hub-preview" role="note">
        <Eye size={16} aria-hidden="true" />
        <span>Customer view preview: what this customer would see in the app.</span>
        <Link to={`/customers/${encodeURIComponent(customerId)}`} className="btn btn-sm">
          <ArrowLeft size={14} aria-hidden="true" /> Back to RM view
        </Link>
      </div>

      {customer.isError && <ErrorBox error={customer.error} what={`customer ${customerId}`} />}
      {actions.isError && <ErrorBox error={actions.error} what="your opportunities" />}

      <header className="hub-head">
        <h1 className="page-title">{firstName ? `${firstName}, here are your green opportunities` : "Your green opportunities"}</h1>
        {snapshot && <p className="lede">Based on your account data as of {date(snapshot.feature_cutoff)}.</p>}
      </header>

      {actions.isPending && <Loading label="Finding your green opportunities…" />}
      {actions.data && shown.length === 0 && (
        <div className="panel">
          <h2 className="panel-title">No green suggestions right now</h2>
          <p className="small muted">We only suggest something when your data clearly supports it. We'll check again when your data changes.</p>
        </div>
      )}

      {snapshot && shown.length > 0 && (
        <div className="hub-grid">
          {shown.map((row) => <HubCard key={row.product} row={row} snapshot={snapshot} />)}
        </div>
      )}

      {extras.length > 0 && (
        <section className="section">
          <div className="section-head"><h2 className="section-title">You might also be interested in</h2></div>
          <div className="grid-2">
            {extras.map((row) => {
              const meta = OPTIONAL_PRODUCTS[row.product];
              return (
                <article className="panel" key={row.product}>
                  <h3 className="panel-title">{meta.name}</h3>
                  <p className="small muted">{meta.blurb}</p>
                  <p className="xsmall muted" style={{ marginTop: 8 }}>{meta.guardrail}</p>
                  <div style={{ marginTop: 12 }}><PlaceholderButton feature={meta.cta} small>{meta.cta}</PlaceholderButton></div>
                </article>
              );
            })}
          </div>
        </section>
      )}

      <section className="section grid-2">
        <PlaceholderPanel feature="Green spending insights" title="Your spending footprint">
          A monthly view of the estimated emissions behind your categorised spending (fuel, energy, travel), with tips to reduce it.
        </PlaceholderPanel>
        <PlaceholderPanel feature="Customer contact preferences" title="Choose what we suggest">
          Let you hide topics you're not interested in and choose how we contact you. Today only staff can record these choices for you.
        </PlaceholderPanel>
      </section>

      <p className="xsmall muted" style={{ marginTop: 24 }}>{DISCLAIMER} Impact figures are modelled estimates, not measured savings.</p>
    </div>
  );
}

function HubCard({ row, snapshot }: { row: Recommendation; snapshot: CustomerSnapshot }) {
  const [why, setWhy] = useState(false);
  const reasons = (row.propensity?.reason_codes ?? []).map((code) => CUSTOMER_REASONS[code]).filter(Boolean);
  const cta = PRODUCT_CTAS[row.product];
  return (
    <article className="hub-card">
      <div className="hub-card-top">
        <span className="swatch" style={{ background: PRODUCT_COLORS[row.product] }} aria-hidden="true" />
        <h2 className="hub-card-title">{productName(row.product)}</h2>
        <span className="badge" data-tone="supported"><span className="badge-dot" aria-hidden="true" />Relevant to you</span>
      </div>
      <p className="small muted">{PRODUCTS[row.product]?.blurb}</p>

      <div className="hub-impact">
        <span className="opp-metric-label">Potential annual impact</span>
        {impactAvailable(row.impact)
          ? <><b>{impactLabel(row.impact)}</b><span className="xsmall muted">Modelled estimate</span></>
          : <Unavailable>No reliable estimate yet</Unavailable>}
      </div>

      {reasons.length > 0 && (
        <div>
          <span className="opp-metric-label">Why you're seeing this</span>
          <ul className="tick-list small" style={{ marginTop: 6 }}>
            {reasons.slice(0, 2).map((text) => <li key={text}><Check size={14} aria-hidden="true" /><span>{text}</span></li>)}
          </ul>
        </div>
      )}

      <div className="row" style={{ marginTop: "auto" }}>
        <PlaceholderButton feature={cta.backlog} primary>{cta.label}</PlaceholderButton>
        <button type="button" className="btn btn-quiet" aria-expanded={why} onClick={() => setWhy((value) => !value)}>
          Why am I seeing this? <ChevronDown size={14} aria-hidden="true" style={{ transform: why ? "rotate(180deg)" : undefined }} />
        </button>
      </div>

      {why && (
        <div className="hub-why">
          <p className="small"><b>Based on:</b></p>
          {reasons.length
            ? <ul className="tick-list small">{reasons.map((text) => <li key={text}><Check size={14} aria-hidden="true" /><span>{text}</span></li>)}</ul>
            : <p className="small muted">Your account information supports this suggestion.</p>}
          <p className="small"><b>Model confidence:</b>{" "}
            {row.propensity?.confidence_validated && row.propensity.confidence !== null
              ? percentage(row.propensity.confidence, 0)
              : "not shown, because it hasn't passed our reliability checks yet."}
          </p>
          <p className="small"><b>Data as of:</b> {date(snapshot.feature_cutoff)}</p>
          <p className="xsmall muted">{DISCLAIMER}</p>
        </div>
      )}
    </article>
  );
}
