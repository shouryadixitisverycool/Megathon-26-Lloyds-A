import { useState } from "react";
import { FlaskConical } from "lucide-react";
import { useOptionalOpportunities } from "../api/hooks";
import type { GreenPurpose, OptionalOpportunity, Propensity } from "../api/types";
import { ThresholdRail } from "../components/ThresholdRail";
import { PlaceholderButton } from "../components/Placeholder";
import { ErrorBox, Info, Loading, SelectField, ToneBadge } from "../components/ui";
import { humanize } from "../lib/format";
import { GREEN_PURPOSES, OPTIONAL_PRODUCTS, OPTIONAL_REASONS, OPTIONAL_STATUS } from "../lib/labels";

/** Green Investments and Green Loans: experimental COULD-tier signals from /optional-opportunities. */
export function OptionalOpportunities({ customerId }: { customerId: string }) {
  const [purpose, setPurpose] = useState<GreenPurpose | "">("");
  const query = useOptionalOpportunities(customerId, purpose);
  return (
    <section className="section">
      <div className="section-head">
        <h2 className="section-title">More green opportunities</h2>
        <p className="section-note">
          Experimental signals for Green Investments and Green Loans. They sit outside the four core products, confidence is
          always withheld, and nothing here is advice, suitability or credit approval.
        </p>
      </div>
      {query.isPending && <Loading label="Checking experimental opportunities…" />}
      {query.isError && <ErrorBox error={query.error} what="experimental opportunities" />}
      {query.data && (
        <div className="grid-2">
          {query.data.opportunities.map((row) => (
            <OptionalCard key={row.product} row={row}
              purposeControl={row.product === "GREEN_LOANS" ? (
                <SelectField label="Declared green purpose" value={purpose} onChange={(value) => setPurpose(value as GreenPurpose | "")}
                  options={GREEN_PURPOSES} hint="A loan is scored only for a purpose the customer has declared." />
              ) : null} />
          ))}
        </div>
      )}
    </section>
  );
}

function OptionalCard({ row, purposeControl }: { row: OptionalOpportunity; purposeControl: React.ReactNode }) {
  const meta = OPTIONAL_PRODUCTS[row.product];
  const status = OPTIONAL_STATUS[row.status] ?? { label: humanize(row.status), tone: "neutral" as const, help: "" };
  // The rail only needs probability and cut-off; optional results have no population exclusion.
  const rail = row.probability !== null && row.threshold !== undefined
    ? ({ probability: String(row.probability), decision_threshold: String(row.threshold), in_model_population: true,
         population_exclusion: null } as unknown as Propensity)
    : null;
  return (
    <article className="panel optional-card" data-tone={status.tone}>
      <div className="row-between">
        <div className="row" style={{ gap: 8 }}>
          <h3 className="panel-title" style={{ margin: 0 }}>{meta?.name ?? row.product}</h3>
          <ToneBadge tone={status.tone} title={status.help}>{status.label}</ToneBadge>
        </div>
        <span className="xsmall muted row" style={{ gap: 4 }}>
          <FlaskConical size={12} aria-hidden="true" /> Experimental
          <Info>{row.confidence_limitation}</Info>
        </span>
      </div>
      <p className="small muted" style={{ marginTop: 6 }}>{meta?.blurb}</p>
      {purposeControl && <div style={{ marginTop: 12 }}>{purposeControl}</div>}
      {rail && <div style={{ marginTop: 12 }}><ThresholdRail propensity={rail} label="Experimental likelihood" /></div>}
      {row.reason_codes.length > 0 && (
        <ul className="small" style={{ marginTop: 12 }}>
          {row.reason_codes.map((code) => <li key={code}>{OPTIONAL_REASONS[code] ?? humanize(code)}</li>)}
        </ul>
      )}
      <p className="xsmall muted" style={{ marginTop: 12 }}>{meta?.guardrail} {row.model_version && <>Model <code>{row.model_version}</code>.</>}</p>
      {row.status === "OPPORTUNITY_SIGNAL" && (
        <div style={{ marginTop: 12 }}><PlaceholderButton feature={meta?.cta ?? row.product} small>{meta?.cta}</PlaceholderButton></div>
      )}
    </article>
  );
}
