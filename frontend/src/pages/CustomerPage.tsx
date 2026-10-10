import { useCallback, useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { CalendarDays, ChevronRight, CornerDownRight, MapPin, Users } from "lucide-react";
import { useCustomer, useCustomerIndex, useNextActions } from "../api/hooks";
import type { Channel, CustomerSnapshot, DecisionState, Product, Recommendation } from "../api/types";
import { Drawer } from "../components/Drawer";
import { ThresholdRail } from "../components/ThresholdRail";
import { PRODUCT_COLORS } from "../components/charts/common";
import { Callout, Disclosure, ErrorBox, Info, KV, Loading, Skeleton, StateBadge, ToneBadge, Unavailable } from "../components/ui";
import { DataTable } from "../components/DataTable";
import { TrustIssues } from "../components/TrustIssues";
import { JsonView } from "../components/ui";
import { date, displayValue, humanize, impactAvailable, impactLabel, listSentence, percentage } from "../lib/format";
import {
  CHANNEL_ORDER, CHANNELS, featureLabel, MODEL_REASONS, NEXT_ACTIONS, nextActionLabel, PRODUCTS, productName, STATES, trustLabel,
} from "../lib/labels";
import { trustTone } from "./CustomersPage";
import { ProductDetail, ProductDetailHeader, type DetailTab } from "./product/ProductDetail";

const GROUP: Record<DecisionState, number> = {
  RECOMMEND: 0, CONFLICT_REQUIRES_REVIEW: 1, INSUFFICIENT_INFORMATION: 1,
  DO_NOT_RECOMMEND: 2, NOT_APPLICABLE: 3, SUPPRESSED: 3,
};

const ABSTAIN_PHRASES: Record<DecisionState, [string, string]> = {
  INSUFFICIENT_INFORMATION: ["needs more evidence", "need more evidence"],
  CONFLICT_REQUIRES_REVIEW: ["has conflicting records", "have conflicting records"],
  DO_NOT_RECOMMEND: ["is below the likelihood cut-off", "are below the likelihood cut-off"],
  NOT_APPLICABLE: ["is already adopted or not applicable", "are already adopted or not applicable"],
  SUPPRESSED: ["is suppressed from contact", "are suppressed from contact"],
  RECOMMEND: ["is supported", "are supported"],
};

function numberWord(n: number): string {
  return ["No", "One", "Two", "Three", "Four"][n] ?? String(n);
}

/** Presentation-only summary of the API's decisions. It never changes a decision. */
function briefing(rows: Recommendation[]) {
  const supported = rows.filter((row) => row.state === "RECOMMEND");
  if (supported.length) {
    const first = supported[0];
    const action = first.next_action;
    return {
      line: `${numberWord(supported.length)} supported ${supported.length === 1 ? "opportunity" : "opportunities"}: ${listSentence(supported.map((row) => productName(row.product)))}.`,
      sub: action
        ? `Start with ${productName(first.product)}. Next step: ${nextActionLabel(action.action).toLowerCase()} (${action.reason.toLowerCase()}).`
        : `Start with ${productName(first.product)}.`,
    };
  }
  const counts = new Map<DecisionState, number>();
  for (const row of rows) counts.set(row.state, (counts.get(row.state) ?? 0) + 1);
  const parts = [...counts.entries()].map(([state, n]) => `${n === 1 ? "one product" : `${n} products`} ${ABSTAIN_PHRASES[state][n === 1 ? 0 : 1]}`);
  return {
    line: "No supported opportunity right now.",
    sub: `${listSentence(parts).replace(/^./, (c) => c.toUpperCase())}. Holding back is a valid result; review the evidence before any outreach.`,
  };
}

function whyLine(row: Recommendation): string {
  const reasons = (row.propensity?.reason_codes ?? []).map((code) => MODEL_REASONS[code]).filter(Boolean);
  if (row.state === "RECOMMEND" && reasons.length) return reasons.slice(0, 2).join(" ");
  return row.evidence[0]?.message ?? STATES[row.state]?.help ?? "";
}

export function CustomerPage() {
  const { customerId = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const channel = (params.get("channel") as Channel) || "rm";
  const openProduct = params.get("product") as Product | null;
  const tab = (params.get("tab") as DetailTab) || "why";
  const customer = useCustomer(customerId);
  const actions = useNextActions(customerId, CHANNELS[channel] ? channel : "rm");

  const setParam = useCallback((changes: Record<string, string | null>) => {
    setParams((current) => {
      const next = new URLSearchParams(current);
      for (const [key, value] of Object.entries(changes)) value === null ? next.delete(key) : next.set(key, value);
      return next;
    }, { replace: true });
  }, [setParams]);
  const close = useCallback(() => setParam({ product: null, tab: null }), [setParam]);

  const rows = useMemo(() => {
    const list = [...(actions.data ?? [])];
    return list.sort((a, b) => GROUP[a.state] - GROUP[b.state]);
  }, [actions.data]);
  const selected = rows.find((row) => row.product === openProduct);

  if (customer.isError) {
    return (
      <div className="page">
        <Crumbs id={customerId} />
        <ErrorBox error={customer.error} what={`customer ${customerId}`} />
        <p style={{ marginTop: 16 }}><Link to="/customers" className="btn">Back to customers</Link></p>
      </div>
    );
  }

  const snapshot = customer.data;
  const summary = rows.length ? briefing(rows) : null;

  return (
    <div className="page">
      <Crumbs id={customerId} />
      {!snapshot ? (
        <div className="stack"><Skeleton height={40} width="40%" /><Skeleton height={18} width="60%" /></div>
      ) : (
        <CustomerHeader snapshot={snapshot} />
      )}

      {snapshot && snapshot.trust.issues.length > 0 && (
        <div style={{ marginTop: 16 }}><TrustIssues issues={snapshot.trust.issues} /></div>
      )}

      <section className="briefing" aria-live="polite">
        <div>
          {summary ? (
            <>
              <p className="briefing-line">{summary.line}</p>
              <p className="briefing-sub">{summary.sub}</p>
            </>
          ) : actions.isError ? (
            <p className="briefing-line">Decisions couldn't be loaded.</p>
          ) : (
            <p className="briefing-line">Reviewing this customer's evidence…</p>
          )}
        </div>
        <div className="field">
          <label htmlFor="channel">Planned contact channel</label>
          <select id="channel" className="select" value={channel} onChange={(event) => setParam({ channel: event.target.value })}>
            {CHANNEL_ORDER.map((value) => <option key={value} value={value}>{CHANNELS[value]}</option>)}
          </select>
        </div>
      </section>

      {actions.isError && <div style={{ marginTop: 16 }}><ErrorBox error={actions.error} what="product decisions" /></div>}
      {actions.isPending && <div className="opp-list" style={{ padding: 24 }}><Loading label="Scoring products for this customer…" /></div>}
      {actions.data && rows.length === 0 && (
        <div style={{ marginTop: 16 }}><Callout kind="info" title="The API returned no product decisions for this customer." /></div>
      )}

      {rows.length > 0 && (
        <>
          <div className="opp-list" aria-label="Product opportunities">
            {rows.map((row) => <OpportunityRow key={row.product} row={row} onOpen={() => setParam({ product: row.product, tab: "why" })} />)}
          </div>
          <p className="xsmall muted" style={{ marginTop: 8 }}>
            Supported opportunities first, then cases that need a person, then the rest. Within each group, highest likelihood first.
            Next steps follow consent, contact history and review rules for the {CHANNELS[channel].toLowerCase()} channel.
          </p>
        </>
      )}

      {snapshot && <CustomerData snapshot={snapshot} />}

      <Drawer open={!!selected} onClose={close} label={selected ? `${productName(selected.product)} details` : "Details"}
        header={selected && snapshot ? <ProductDetailHeader row={selected} snapshot={snapshot} tab={tab} onTab={(value) => setParam({ tab: value })} /> : null}>
        {selected && snapshot && <ProductDetail row={selected} snapshot={snapshot} tab={tab} channel={channel} />}
      </Drawer>
    </div>
  );
}

function Crumbs({ id }: { id: string }) {
  return (
    <nav className="crumbs" aria-label="Breadcrumb">
      <Link to="/customers">Customers</Link>
      <ChevronRight size={14} aria-hidden="true" />
      <span aria-current="page">{id}</span>
    </nav>
  );
}

function CustomerHeader({ snapshot }: { snapshot: CustomerSnapshot }) {
  const navigate = useNavigate();
  const index = useCustomerIndex(false);
  const [jump, setJump] = useState("");
  const synthetic = snapshot.display_name.startsWith("Synthetic customer");
  return (
    <header className="customer-head">
      <div>
        <h1 className="customer-name">{synthetic ? snapshot.customer_id : snapshot.display_name}</h1>
        <div className="customer-facts">
          {!synthetic && <span><b>{snapshot.customer_id}</b></span>}
          {synthetic && <span>{snapshot.display_name}</span>}
          <span><MapPin size={14} aria-hidden="true" />{snapshot.region}</span>
          <span><Users size={14} aria-hidden="true" />{humanize(snapshot.segment)}</span>
          <span><CalendarDays size={14} aria-hidden="true" />Data as of {date(snapshot.feature_cutoff)}</span>
          <span>
            <ToneBadge tone={trustTone(snapshot.trust.status)}>Data trust: {trustLabel(snapshot.trust.status)} {percentage(snapshot.trust.score, 0)}</ToneBadge>
            <Info>Data trust describes how complete, current and consistent this customer's evidence is. It is separate from model confidence.</Info>
          </span>
        </div>
      </div>
      <form className="field" style={{ minWidth: 220 }} onSubmit={(event) => {
        event.preventDefault();
        if (jump.trim()) navigate(`/customers/${encodeURIComponent(jump.trim())}`);
        setJump("");
      }}>
        <label htmlFor="jump">Open another customer</label>
        <div className="row" style={{ gap: 6, flexWrap: "nowrap" }}>
          <input id="jump" className="input" list="customer-ids" placeholder="Customer ID" value={jump} onChange={(event) => setJump(event.target.value)} />
          <button className="btn" type="submit">Open</button>
        </div>
        {index.data && (
          <datalist id="customer-ids">
            {index.data.slice(0, 5000).map((row) => <option key={row.customer_id} value={row.customer_id}>{row.display_name}</option>)}
          </datalist>
        )}
      </form>
    </header>
  );
}

function OpportunityRow({ row, onOpen }: { row: Recommendation; onOpen: () => void }) {
  const meta = STATES[row.state];
  const action = row.next_action;
  return (
    <div className="opp" data-tone={meta?.tone} role="button" tabIndex={0} onClick={onOpen}
      onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onOpen(); } }}
      aria-label={`${productName(row.product)}: ${meta?.label ?? row.state}. Open details`}>
      <div>
        <div className="opp-name">
          <span className="swatch" style={{ background: PRODUCT_COLORS[row.product] }} aria-hidden="true" />
          <span>{PRODUCTS[row.product]?.name ?? row.product}</span>
          <StateBadge state={row.state} />
        </div>
        <p className="opp-why">{whyLine(row)}</p>
        {action && (
          <p className="opp-next">
            <CornerDownRight size={14} aria-hidden="true" />
            {NEXT_ACTIONS[action.action]?.label ?? action.action}{" "}
            <span className="muted">({action.reason.charAt(0).toLowerCase() + action.reason.slice(1)})</span>
          </p>
        )}
      </div>
      <ThresholdRail propensity={row.propensity} compact />
      <div>
        <span className="opp-metric-label">Potential impact</span>
        <div className="opp-metric">{impactAvailable(row.impact) ? impactLabel(row.impact) : <Unavailable />}</div>
        <span className="rail-caption">{impactAvailable(row.impact) ? "Modelled estimate, not a measured saving" : "No defensible estimate; not zero"}</span>
      </div>
      <span className="opp-open">Details <ChevronRight size={16} aria-hidden="true" /></span>
    </div>
  );
}

const SOURCE_GROUPS: [string, string][] = [
  ["vehicle", "Vehicle"], ["home", "Home"], ["energy", "Energy use"], ["digital", "Digital banking"],
  ["spend", "Spending"], ["data_quality", "Data quality"],
];

function CustomerData({ snapshot }: { snapshot: CustomerSnapshot }) {
  const features = Object.entries(snapshot.features).map(([field, evidence]) => ({ field, ...evidence }));
  const source = snapshot.source_snapshot;
  const productTrust = Object.entries(snapshot.product_trust ?? {});
  return (
    <section className="section">
      <div className="section-head">
        <h2 className="section-title">Customer data</h2>
        <p className="section-note">The evidence these decisions are based on. Open a section to see it.</p>
      </div>
      <div className="panel">
        <Disclosure title="Evidence on file" hint={`${features.length} approved facts`}>
          <DataTable rows={features} rowKey={(row) => row.field} pageSize={50} caption="Approved customer evidence"
            columns={[
              { key: "field", header: "Fact", sort: (row) => featureLabel(row.field), render: (row) => featureLabel(row.field) },
              { key: "value", header: "Value", sort: (row) => String(row.value), render: (row) => row.value === null ? <Unavailable>Unknown</Unavailable> : row.value ? "Yes" : "No" },
              { key: "freshness", header: "Freshness", sort: (row) => row.freshness, render: (row) => humanize(row.freshness) },
              { key: "observed", header: "Observed", sort: (row) => row.observed_at, render: (row) => date(row.observed_at) },
              { key: "conflicts", header: "Conflicts", render: (row) => row.conflicts.length ? row.conflicts.join("; ") : <span className="muted">None</span> },
              { key: "ref", header: "Reference", render: (row) => <code className="xsmall muted">{row.reference}</code> },
            ]} />
        </Disclosure>
        {source && (
          <Disclosure title="Source record" hint="Customer 360 snapshot used by the trained models">
            <div className="kv-groups">
              {SOURCE_GROUPS.filter(([key]) => source[key]).map(([key, title]) => (
                <div className="kv-group" key={key}>
                  <h4>{title}</h4>
                  <KV items={Object.entries(source[key] as Record<string, unknown>).map(([field, value]) => [humanize(field), displayValue(value)])} />
                </div>
              ))}
            </div>
            <div style={{ marginTop: 16 }}>
              <Disclosure title="All model features and raw JSON" hint={`${Object.keys(source.features ?? {}).length} features`}>
                <JsonView value={source} label="Source snapshot JSON" />
              </Disclosure>
            </div>
          </Disclosure>
        )}
        {productTrust.length > 0 && (
          <Disclosure title="Data trust by product" hint="Completeness, freshness and consistency per product">
            <DataTable rows={productTrust} rowKey={([product]) => product} caption="Data trust by product"
              columns={[
                { key: "product", header: "Product", render: ([product]) => productName(product) },
                { key: "status", header: "Status", render: ([, trust]) => <ToneBadge tone={trustTone(trust!.status)}>{trustLabel(trust!.status)}</ToneBadge> },
                { key: "score", header: "Score", numeric: true, render: ([, trust]) => percentage(trust!.score, 0) },
                { key: "parts", header: "Completeness / freshness / consistency", render: ([, trust]) => {
                  const a = trust!.source_assessment as Record<string, number> | null | undefined;
                  return a ? `${percentage(a.completeness, 0)} / ${percentage(a.freshness, 0)} / ${percentage(a.cross_source_consistency, 0)}` : <Unavailable />;
                } },
                { key: "issues", header: "Issues", render: ([, trust]) => trust!.issues.length ? trust!.issues.map((issue) => issue.message).join(" ") : <span className="muted">None</span> },
              ]} />
          </Disclosure>
        )}
        <Disclosure title="Raw customer snapshot" hint="Exactly as returned by the API">
          <JsonView value={{ ...snapshot, source_snapshot: source ? "(shown under Source record)" : null }} />
        </Disclosure>
      </div>
    </section>
  );
}
