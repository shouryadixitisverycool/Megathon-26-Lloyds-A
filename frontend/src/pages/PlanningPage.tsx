import { useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { useOpportunities, usePortfolioSummary, type OpportunityParams } from "../api/hooks";
import type { Channel, PlanResult, Product, Recommendation } from "../api/types";
import { useSubmit } from "../api/useSubmit";
import { BarList } from "../components/charts/BarList";
import { STATE_COLORS } from "../components/charts/common";
import { Scatter } from "../components/charts/Scatter";
import { DataTable } from "../components/DataTable";
import { Callout, Disclosure, Empty, ErrorBox, KV, RangeField, Segmented, SelectField, SlowLoading, Stat, StateBadge, Unavailable } from "../components/ui";
import { count, decimal, humanize, plural, impactAvailable, impactLabel, percentage, periodLabel, prettyUnit, toNumber } from "../lib/format";
import { CHANNEL_ORDER, CHANNELS, PRODUCT_ORDER, PRODUCTS, productName, QUALITY_ORDER, STATE_ORDER, STATES, TRUST } from "../lib/labels";

interface Draft {
  product: Product; region: string; segment: string; status: string; data_quality: string;
  min_propensity: number; min_trust: number; min_confidence: number; min_impact: number;
}

const DEFAULT: Draft = {
  product: "EV_FINANCE", region: "", segment: "", status: "RECOMMEND", data_quality: "",
  min_propensity: 0, min_trust: 0, min_confidence: 0, min_impact: 0,
};

function toParams(draft: Draft): OpportunityParams {
  const params: OpportunityParams = { product: draft.product };
  if (draft.region) params.region = draft.region;
  if (draft.segment) params.segment = draft.segment;
  if (draft.status) params.status = draft.status;
  if (draft.data_quality) params.data_quality = draft.data_quality;
  // Zero means "no filter", so missing confidence and impact stay visible.
  for (const key of ["min_propensity", "min_trust", "min_confidence", "min_impact"] as const) {
    if (draft[key] > 0) params[key] = String(draft[key]);
  }
  return params;
}

export function PlanningPage() {
  const [draft, setDraft] = useState<Draft>(DEFAULT);
  const [applied, setApplied] = useState<Draft>(DEFAULT);
  const params = useMemo(() => toParams(applied), [applied]);
  const opportunities = useOpportunities(params);
  const all = usePortfolioSummary({});
  const client = useQueryClient();
  const dirty = JSON.stringify(draft) !== JSON.stringify(applied);
  const activeFilters = [
    applied.status && STATES[applied.status as keyof typeof STATES]?.short,
    applied.data_quality && `${TRUST[applied.data_quality as keyof typeof TRUST]?.label} data`,
    applied.min_propensity > 0 && `likelihood ≥ ${Math.round(applied.min_propensity * 100)}%`,
    applied.min_trust > 0 && `trust ≥ ${Math.round(applied.min_trust * 100)}%`,
    applied.min_confidence > 0 && `confidence ≥ ${Math.round(applied.min_confidence * 100)}%`,
    applied.min_impact > 0 && `impact ≥ ${applied.min_impact}`,
  ].filter(Boolean) as string[];

  const apply = (event?: FormEvent) => {
    event?.preventDefault();
    setApplied(draft);
  };

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="page-title">Campaign planning</h1>
          <p className="lede">Find the customers a product is relevant to, then size a campaign under assumptions you set. Nothing here sends a message.</p>
        </div>
      </div>

      <form className="panel" onSubmit={apply}>
        <div className="stack">
          <div className="field">
            <span className="field-label">Product</span>
            <Segmented label="Product" value={draft.product} onChange={(product) => setDraft({ ...draft, product })}
              options={PRODUCT_ORDER.map((value) => ({ value, label: PRODUCTS[value].name }))} />
          </div>
          <div className="filters" style={{ marginBottom: 0 }}>
            <SelectField label="Region" value={draft.region} onChange={(region) => setDraft({ ...draft, region })}
              options={[{ value: "", label: "All regions" }, ...(all.data?.region_summaries ?? []).map((row) => ({ value: row.name, label: row.name }))]} />
            <SelectField label="Segment" value={draft.segment} onChange={(segment) => setDraft({ ...draft, segment })}
              options={[{ value: "", label: "All segments" }, ...(all.data?.segment_summaries ?? []).map((row) => ({ value: row.name, label: humanize(row.name) }))]} />
            <SelectField label="Decision" value={draft.status} onChange={(status) => setDraft({ ...draft, status })}
              options={[{ value: "", label: "Any decision" }, ...STATE_ORDER.map((value) => ({ value, label: STATES[value].label }))]} />
            <SelectField label="Data trust" value={draft.data_quality} onChange={(data_quality) => setDraft({ ...draft, data_quality })}
              options={[{ value: "", label: "Any" }, ...QUALITY_ORDER.map((value) => ({ value, label: TRUST[value].label }))]} />
          </div>
          <Disclosure title="More filters" hint="Minimum likelihood, trust, confidence and impact">
            <div className="grid-2">
              <RangeField label="Minimum likelihood" value={draft.min_propensity} onChange={(value) => setDraft({ ...draft, min_propensity: value })} format={(value) => `${Math.round(value * 100)}%`} />
              <RangeField label="Minimum data trust" value={draft.min_trust} onChange={(value) => setDraft({ ...draft, min_trust: value })} format={(value) => `${Math.round(value * 100)}%`} />
              <RangeField label="Minimum validated confidence" value={draft.min_confidence} onChange={(value) => setDraft({ ...draft, min_confidence: value })}
                format={(value) => value === 0 ? "Off" : `${Math.round(value * 100)}%`} hint="Any value above zero excludes customers whose confidence isn't validated." />
              <div className="field">
                <label htmlFor="min-impact">Minimum carbon impact (per year, in the product's units)</label>
                <input id="min-impact" className="input" type="number" min={0} step="any" value={draft.min_impact}
                  onChange={(event) => setDraft({ ...draft, min_impact: Math.max(0, Number(event.target.value) || 0) })} />
                <span className="field-hint">Any value above zero excludes customers without an estimate.</span>
              </div>
            </div>
          </Disclosure>
          <div className="form-actions" style={{ marginTop: 0 }}>
            <button className="btn btn-primary" type="submit" disabled={!dirty && !opportunities.isError}>Find opportunities</button>
            {!dirty && !opportunities.isError && <span className="small muted">Results below match these filters.</span>}
            {dirty && <button className="btn btn-quiet" type="button" onClick={() => setDraft(applied)}>Undo changes</button>}
            {JSON.stringify(applied) !== JSON.stringify(DEFAULT) && (
              <button className="btn btn-quiet" type="button" onClick={() => { setDraft(DEFAULT); setApplied(DEFAULT); }}>Reset</button>
            )}
          </div>
        </div>
      </form>

      <section className="section">
        <div className="section-head">
          <h2 className="section-title">{productName(applied.product)} opportunities</h2>
          <p className="section-note">
            {[applied.region || "All regions", applied.segment ? humanize(applied.segment) : "all segments", ...activeFilters].join(", ")}
          </p>
        </div>
        {opportunities.isFetching && (
          <SlowLoading label={`Scoring customers for ${productName(applied.product)}…`}
            detail="With trained models, the API re-scores every customer for this search. Expect about a minute; results are kept for 10 minutes."
            onCancel={() => client.cancelQueries({ queryKey: ["portfolio", "opportunities"] })} />
        )}
        {opportunities.isError && !opportunities.isFetching && (
          (opportunities.error as Error).name === "CancelledError"
            ? <Callout kind="info" title="Search cancelled">Choose filters and select Find opportunities to try again.</Callout>
            : <ErrorBox error={opportunities.error} what="opportunities" />
        )}
        {opportunities.data && !opportunities.isFetching && <Opportunities rows={opportunities.data.opportunities} disclaimer={opportunities.data.disclaimer} />}
      </section>

      <CampaignPlanner product={applied.product} region={applied.region} segment={applied.segment} />
    </div>
  );
}

function Opportunities({ rows, disclaimer }: { rows: Recommendation[]; disclaimer: string }) {
  const navigate = useNavigate();
  const ranked = rows.every((row) => row.priority?.score === null || row.priority?.score === undefined);
  const supported = rows.filter((row) => row.state === "RECOMMEND").length;
  if (!rows.length) return <Empty title="No customers match">Loosen the filters, or try another product or region.</Empty>;

  // Only plot points that share one impact compatibility group; units and boundaries never mix.
  const groups = new Map<string, { units: string; points: { id: string; x: number; y: number; group: string }[] }>();
  for (const row of rows) {
    const probability = toNumber(row.propensity?.probability);
    if (probability === null || !impactAvailable(row.impact)) continue;
    const key = JSON.stringify(row.expected_sustainability_impact?.compatibility_group ?? [row.product, row.impact.units, row.impact.boundary, row.impact.method_version]);
    const entry = groups.get(key) ?? { units: row.impact.units, points: [] };
    entry.points.push({ id: row.customer_id, x: probability, y: toNumber(row.impact.value)!, group: row.state });
    groups.set(key, entry);
  }
  const states = [...new Set(rows.map((row) => row.state))];

  return (
    <div className="stack">
      <div className="stats">
        <Stat label="Matching decisions" value={count(rows.length)} />
        <Stat label="Supported" value={count(supported)} />
        <Stat label="With a carbon estimate" value={count(rows.filter((row) => impactAvailable(row.impact)).length)} />
      </div>
      {ranked && (
        <Callout kind="info" title="Ranked by likelihood">
          The priority score needs validated confidence and a comparable impact estimate. Where either is missing it isn't invented,
          so customers are ranked by calibrated likelihood instead.
        </Callout>
      )}
      <DataTable rows={rows} rowKey={(row) => `${row.customer_id}-${row.product}`} pageSize={20} caption="Opportunities"
        onRowClick={(row) => navigate(`/customers/${encodeURIComponent(row.customer_id)}?product=${row.product}`)}
        initialSort={{ key: "rank", dir: "asc" }}
        columns={[
          { key: "rank", header: "Rank", numeric: true, sort: (row) => row.priority?.rank, render: (row) => row.priority?.rank ?? "" },
          { key: "customer", header: "Customer", sort: (row) => row.customer_id, render: (row) => (
            <Link to={`/customers/${encodeURIComponent(row.customer_id)}?product=${row.product}`} onClick={(event) => event.stopPropagation()}><b>{row.customer_id}</b></Link>
          ) },
          { key: "where", header: "Region and segment", sort: (row) => row.region, render: (row) => <span>{row.region}<div className="xsmall muted">{humanize(row.segment)}</div></span> },
          { key: "state", header: "Decision", sort: (row) => row.state, render: (row) => <StateBadge state={row.state} short /> },
          { key: "p", header: "Likelihood", numeric: true, sort: (row) => toNumber(row.propensity?.probability), render: (row) => percentage(row.propensity?.probability) },
          { key: "t", header: "Data trust", numeric: true, sort: (row) => toNumber(row.trust.score), render: (row) => percentage(row.trust.score, 0) },
          { key: "i", header: "Carbon impact", numeric: true, sort: (row) => impactAvailable(row.impact) ? toNumber(row.impact.value) : null, render: (row) => impactAvailable(row.impact) ? impactLabel(row.impact) : <Unavailable /> },
          { key: "e", header: "Expected impact", numeric: true, sort: (row) => toNumber(row.expected_sustainability_impact?.value),
            render: (row) => row.expected_sustainability_impact?.value ? `${decimal(row.expected_sustainability_impact.value, 1)} ${prettyUnit(row.impact.units)}` : <Unavailable /> },
          { key: "score", header: "Priority", numeric: true, sort: (row) => row.priority?.score, render: (row) => row.priority?.score === null || row.priority?.score === undefined ? <Unavailable /> : percentage(row.priority.score) },
        ]} />
      <p className="xsmall muted">{disclaimer} Expected impact is likelihood times modelled impact; it isn't an observed reduction.</p>

      {groups.size > 0 ? (
        [...groups.entries()].map(([key, group]) => (
          <section key={key} className="panel">
            <h3 className="panel-title">Likelihood against carbon impact</h3>
            <p className="panel-sub">{plural(group.points.length, "customer")} with a comparable estimate in {prettyUnit(group.units)}. Select a point to open the customer.</p>
            <Scatter points={group.points} yLabel={prettyUnit(group.units)} ariaLabel="Scatter of likelihood against modelled impact"
              groups={states.filter((state) => group.points.some((point) => point.group === state)).map((state) => ({ key: state, label: STATES[state].short, color: STATE_COLORS[state] }))}
              onSelect={(id) => navigate(`/customers/${encodeURIComponent(id)}`)} />
          </section>
        ))
      ) : (
        <Callout kind="note" title="No likelihood and impact pairs to compare">None of these customers has both a likelihood and an available carbon estimate.</Callout>
      )}
    </div>
  );
}

function CampaignPlanner({ product, region, segment }: { product: Product; region: string; segment: string }) {
  const [target, setTarget] = useState(100);
  const [conversion, setConversion] = useState(0.05);
  const [capacity, setCapacity] = useState(100);
  const [channel, setChannel] = useState<Channel>("app");
  const [objective, setObjective] = useState("conversions");
  const [execute, setExecute] = useState(false);
  const estimate = useSubmit<PlanResult>("/portfolio/scenarios", [], "Scenario estimated");
  const campaign = useSubmit<PlanResult>("/campaigns/optimise", [["customer"], ["portfolio", "summary"]], execute ? "Simulated campaign recorded" : "Campaign plan built");
  const [last, setLast] = useState<"estimate" | "campaign" | null>(null);
  const busy = estimate.isPending || campaign.isPending;
  const result = last === "campaign" ? campaign.data : last === "estimate" ? estimate.data : undefined;
  const error = last === "campaign" ? campaign.error : last === "estimate" ? estimate.error : null;

  const base = { product, target_count: target, conversion_rate: conversion, region: region || null, segment: segment || null, channel };

  return (
    <section className="section">
      <div className="section-head">
        <h2 className="section-title">Size a campaign</h2>
        <p className="section-note">
          Uses supported {productName(product)} opportunities in {region || "all regions"}{segment ? `, ${humanize(segment)}` : ""}. The extra filters above don't apply here.
        </p>
      </div>
      <div className="panel stack">
        <div className="form-grid">
          <div className="field">
            <label htmlFor="target">Customers to target</label>
            <input id="target" className="input" type="number" min={0} max={100000} step={10} value={target} onChange={(event) => setTarget(Math.max(0, Number(event.target.value) || 0))} />
          </div>
          <RangeField label="Assumed conversion rate" value={conversion} onChange={setConversion} format={(value) => `${Math.round(value * 100)}%`}
            hint="Your assumption, not a prediction." />
          <SelectField label="Channel" value={channel} onChange={(value) => setChannel(value as Channel)}
            options={CHANNEL_ORDER.map((value) => ({ value, label: CHANNELS[value] }))} />
        </div>
        <Disclosure title="Campaign settings" hint="Objective, capacity and simulated contacts">
          <div className="form-grid">
            <SelectField label="Optimise for" value={objective} onChange={setObjective} options={[
              { value: "conversions", label: "Most likely to convert" },
              { value: "impact", label: "Largest carbon impact" },
              { value: "balanced", label: "Balanced priority score" },
            ]} hint="Impact and balanced need comparable estimates; customers without them are excluded." />
            <div className="field">
              <label htmlFor="capacity">Channel capacity</label>
              <input id="capacity" className="input" type="number" min={0} max={100000} step={10} value={capacity} onChange={(event) => setCapacity(Math.max(0, Number(event.target.value) || 0))} />
              <span className="field-hint">Shared across active simulated campaigns until they're closed.</span>
            </div>
          </div>
          <label className="check" style={{ marginTop: 16 }}>
            <input type="checkbox" checked={execute} onChange={(event) => setExecute(event.target.checked)} />
            <span><b>Record simulated contacts</b><small>Saves a contact record for each selected customer in the local audit trail. No message is sent.</small></span>
          </label>
        </Disclosure>
        <p className="small muted">Consent, suppression, contact limits, capacity and fatigue rules are applied for you.</p>
        <div className="form-actions" style={{ marginTop: 0 }}>
          <button className="btn" type="button" disabled={busy} onClick={() => { setLast("estimate"); estimate.submit(base); }}>Estimate outcome</button>
          <button className="btn btn-primary" type="button" disabled={busy} onClick={() => {
            setLast("campaign");
            campaign.submit({ ...base, objective, channel_capacity: capacity, execute });
          }}>{execute ? "Build and record simulated campaign" : "Build campaign plan"}</button>
        </div>
      </div>
      {busy && <div style={{ marginTop: 16 }}><SlowLoading label="Applying contact rules to every opportunity…" detail="With trained models this re-scores the portfolio and can take about a minute." /></div>}
      {error && !busy && <div style={{ marginTop: 16 }}><ErrorBox error={error} what="the plan" /></div>}
      {result && !busy && <PlanOutcome result={result} />}
    </section>
  );
}

function PlanOutcome({ result }: { result: PlanResult }) {
  const excluded = Object.entries(result.excluded).sort((a, b) => b[1] - a[1]);
  return (
    <div className="stack" style={{ marginTop: 16 }}>
      <div className="stats">
        <Stat label="Customers selected" value={count(result.selected_count)} />
        <Stat label="Expected adopters" value={decimal(result.scenario_adopters, 1)} note={`At your ${percentage(result.conversion_rate_assumption, 0)} assumption`} />
        <Stat label="Average likelihood" value={percentage(result.average_propensity)} />
        <Stat label="With validated confidence" value={percentage(result.validated_confidence_share, 0)} />
      </div>
      <p className="xsmall muted">{result.disclaimer}</p>
      {result.execution_note && <Callout kind="success" title={result.execution_note}>{result.campaign_event_id && <>Campaign event <code>{result.campaign_event_id}</code></>}</Callout>}

      <div className="grid-2">
        <section className="panel">
          <h3 className="panel-title">Modelled carbon impact</h3>
          <p className="panel-sub">Selected customers' impact times your conversion assumption, grouped so units never mix.</p>
          {result.impact_groups.length ? result.impact_groups.map((group, index) => (
            <div key={index} style={{ marginBottom: 12 }}>
              <div className="impact-hero"><strong className="num" style={{ fontSize: "var(--t-2xl)" }}>{decimal(group.scenario_impact, 1)}</strong><span className="small">{prettyUnit(group.units)}</span></div>
              <p className="xsmall muted">{productName(group.product)}; {periodLabel(group.period)}; method {group.method_version}</p>
            </div>
          )) : <Callout kind="info" title="Not available for this selection">No carbon total is inferred.</Callout>}
          {result.impact_unavailable_count > 0 && <p className="xsmall muted">{count(result.impact_unavailable_count)} selected customers have no estimate.</p>}
        </section>
        <section className="panel">
          <h3 className="panel-title">Why customers were left out</h3>
          <p className="panel-sub">Supported opportunities the contact rules excluded.</p>
          {excluded.length ? (
            <BarList ariaLabel="Exclusion reasons" labelWidth={200} color="var(--tone-neutral-mark)"
              items={excluded.map(([reason, n]) => ({ label: reason, value: n }))} />
          ) : <p className="small muted">Nobody was excluded.</p>}
        </section>
      </div>

      {result.capacity_budget && (
        <section className="panel">
          <h3 className="panel-title">Channel capacity</h3>
          <KV items={[
            ["Capacity limit", count(result.capacity_budget.limit)],
            ["Already used by active campaigns", count(result.capacity_budget.used)],
            ["Remaining before this plan", count(result.capacity_budget.remaining_before)],
            ["Active campaigns", `${result.capacity_budget.active_campaign_count} of ${result.capacity_budget.max_active_campaigns} allowed`],
            ["Applies until", result.capacity_budget.boundary],
          ]} />
        </section>
      )}

      <div className="panel">
        <Disclosure title="Selected customers" hint={count(result.selected.length)}>
          <DataTable rows={result.selected} rowKey={(row) => row.customer_id} caption="Selected customers"
            columns={[
              { key: "rank", header: "Rank", numeric: true, sort: (row) => row.priority.rank, render: (row) => row.priority.rank },
              { key: "id", header: "Customer", render: (row) => <Link to={`/customers/${encodeURIComponent(row.customer_id)}?product=${row.product}`}>{row.customer_id}</Link> },
              { key: "p", header: "Likelihood", numeric: true, sort: (row) => row.priority.components.calibrated_propensity, render: (row) => percentage(row.priority.components.calibrated_propensity) },
              { key: "t", header: "Data trust", numeric: true, render: (row) => percentage(row.priority.components.trust, 0) },
              { key: "s", header: "Priority", numeric: true, render: (row) => row.priority.score === null ? <Unavailable /> : percentage(row.priority.score) },
            ]} />
        </Disclosure>
        <Disclosure title="Rules and versions">
          <KV items={[
            ["Constraint rules", <code key="c">{result.constraint_version}</code>],
            ["Channel", CHANNELS[result.channel] ?? result.channel],
            ["Contacts recorded", result.executed ? "Yes (simulated)" : "No"],
            ["Impact ranking", result.impact_ranking_limitation],
          ]} />
        </Disclosure>
      </div>
    </div>
  );
}
