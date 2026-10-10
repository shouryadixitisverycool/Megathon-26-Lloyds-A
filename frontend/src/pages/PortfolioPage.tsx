import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { usePortfolioSummary, usePortfolioTrends, type PortfolioFilters } from "../api/hooks";
import type { PortfolioSummary, PortfolioTrends, Product } from "../api/types";
import { BarList } from "../components/charts/BarList";
import { LineChart } from "../components/charts/LineChart";
import { PRODUCT_COLORS, STATE_COLORS } from "../components/charts/common";
import { StackedBars } from "../components/charts/StackedBars";
import { ChartFrame } from "../components/ChartFrame";
import { DataTable } from "../components/DataTable";
import { Callout, Disclosure, Empty, ErrorBox, SelectField, SlowLoading, Stat } from "../components/ui";
import { count, decimal, humanize, month, percentage, periodLabel, prettyUnit } from "../lib/format";
import { FUNNEL, PRODUCT_ORDER, PRODUCTS, productName, QUALITY_ORDER, STATE_ORDER, STATES, TRUST } from "../lib/labels";

const SLOW = "The first request for a filter combination re-scores every matching customer, which can take a minute or two with trained models. Results are then cached.";

export function PortfolioPage() {
  const [params, setParams] = useSearchParams();
  const filters: PortfolioFilters = {
    region: params.get("region") || undefined,
    segment: params.get("segment") || undefined,
    product: (params.get("product") as Product) || undefined,
  };
  const summary = usePortfolioSummary(filters);
  const trends = usePortfolioTrends(filters);
  // The unfiltered summary is warmed at API start-up, so it is a cheap source of filter options.
  const all = usePortfolioSummary({});

  const set = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value); else next.delete(key);
    setParams(next, { replace: true });
  };
  const filtered = !!(filters.region || filters.segment || filters.product);
  const data = summary.data;
  const stale = summary.isPlaceholderData || (summary.isFetching && !summary.isPending);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="page-title">Portfolio</h1>
          <p className="lede">Where the sustainable-product opportunities are across the synthetic customer book, and how much the evidence can be trusted.</p>
        </div>
      </div>

      <div className="filters" role="search" aria-label="Portfolio filters">
        <SelectField label="Region" value={filters.region ?? ""} onChange={(value) => set("region", value)}
          options={[{ value: "", label: "All regions" }, ...(all.data?.region_summaries ?? []).map((row) => ({ value: row.name, label: row.name }))]} />
        <SelectField label="Segment" value={filters.segment ?? ""} onChange={(value) => set("segment", value)}
          options={[{ value: "", label: "All segments" }, ...(all.data?.segment_summaries ?? []).map((row) => ({ value: row.name, label: humanize(row.name) }))]} />
        <SelectField label="Product" value={filters.product ?? ""} onChange={(value) => set("product", value)}
          options={[{ value: "", label: "All products" }, ...PRODUCT_ORDER.map((value) => ({ value, label: PRODUCTS[value].name }))]} />
        {filtered && <button type="button" className="btn btn-quiet" onClick={() => setParams({}, { replace: true })}>Clear filters</button>}
      </div>

      {summary.isPending && <SlowLoading label="Summarising the portfolio…" detail={SLOW} />}
      {summary.isError && <ErrorBox error={summary.error} what="the portfolio summary" />}
      {stale && <div style={{ marginBottom: 16 }}><SlowLoading label="Updating for the new filters…" detail={SLOW} /></div>}

      {data && (
        <div style={{ opacity: stale ? 0.55 : 1, transition: "opacity 160ms" }} aria-busy={stale}>
          {data.total_customers === 0 ? (
            <Empty title="No customers match these filters" action={<button className="btn" onClick={() => setParams({}, { replace: true })}>Clear filters</button>}>
              Clear the filters to return to the full synthetic portfolio.
            </Empty>
          ) : (
            <PortfolioBody summary={data} trends={trends.data} trendsError={trends.error} trendsPending={trends.isPending} />
          )}
        </div>
      )}
    </div>
  );
}

function PortfolioBody({ summary, trends, trendsError, trendsPending }: {
  summary: PortfolioSummary; trends?: PortfolioTrends; trendsError: unknown; trendsPending: boolean;
}) {
  const analytics = summary.analytics ?? {};
  const decisions = analytics.decision_count ?? summary.total_recommendations;
  return (
    <>
      <section className="stats" aria-label="Key figures">
        <Stat label="Customers analysed" value={count(summary.total_customers)} />
        <Stat label="Customers with an opportunity" value={count(summary.customers_with_opportunity)}
          note={summary.total_customers ? `${Math.round((summary.customers_with_opportunity / summary.total_customers) * 100)}% of customers` : undefined}
          info="Customers with at least one supported product." />
        <Stat label="Supported opportunities" value={count(summary.recommended_count)} note={`of ${count(summary.total_recommendations)} product decisions`} />
        <Stat label="With a carbon estimate" value={count(summary.available_impact_count)} note="Decisions with an available impact"
          info="Decisions where a defensible physical impact could be calculated. The rest are unavailable, not zero." />
        <Stat label="Supported with trusted data" value={count(summary.high_trust_opportunities)} />
        <Stat label="Supported with validated confidence" value={count(summary.validated_confidence_opportunities)}
          info="Confidence is shown only when its held-out reliability check passes; see Governance for each product's status." />
      </section>
      <p className="xsmall muted" style={{ marginTop: 8 }}>{summary.disclaimer}</p>

      <section className="section">
        <div className="section-head"><h2 className="section-title">Where decisions stand</h2></div>
        <div className="stack">
          <ChartFrame title="Decisions by product"
            note="Every product decision falls into one of six states. Holding back (needs evidence, conflict) is a deliberate outcome, not a failure."
            chart={
              <StackedBars ariaLabel="Count of decisions in each state, by product"
                series={STATE_ORDER.map((state) => ({ key: state, label: STATES[state].short, color: STATE_COLORS[state] }))}
                rows={summary.product_opportunities.map((row) => ({
                  label: productName(row.product),
                  segments: STATE_ORDER.map((state) => ({ key: state, value: row.state_counts[state] ?? 0 })),
                }))} />
            }
            table={
              <DataTable rows={summary.product_opportunities} rowKey={(row) => row.product} caption="Decisions by product and state"
                columns={[
                  { key: "product", header: "Product", render: (row) => productName(row.product) },
                  ...STATE_ORDER.map((state) => ({ key: state, header: STATES[state].short, numeric: true, sort: (row: typeof summary.product_opportunities[number]) => row.state_counts[state] ?? 0, render: (row: typeof summary.product_opportunities[number]) => count(row.state_counts[state] ?? 0) })),
                  { key: "total", header: "Total", numeric: true, sort: (row) => row.total, render: (row) => count(row.total) },
                  { key: "impact", header: "With estimate", numeric: true, sort: (row) => row.available_impact_count, render: (row) => count(row.available_impact_count) },
                ]} />
            } />

          {Object.keys(summary.funnel_counts).length > 0 && (
            <ChartFrame title="From customers to confident opportunities" note={summary.funnel_limitation}
              chart={
                <BarList ariaLabel="Opportunity funnel" labelWidth={210} color="var(--leaf)"
                  items={FUNNEL.filter((stage) => stage.key in summary.funnel_counts).map((stage) => ({ label: stage.label, value: summary.funnel_counts[stage.key] }))} />
              }
              table={
                <DataTable rows={FUNNEL.filter((stage) => stage.key in summary.funnel_counts)} rowKey={(row) => row.key} caption="Opportunity funnel"
                  columns={[
                    { key: "stage", header: "Stage", render: (row) => row.label },
                    { key: "n", header: "Count", numeric: true, render: (row) => count(summary.funnel_counts[row.key]) },
                  ]} />
              } />
          )}

          <div className="grid-2">
            {([["By region", summary.region_summaries], ["By segment", summary.segment_summaries]] as const).map(([title, rows]) => (
              <ChartFrame key={title} title={title} note="Supported opportunities"
                chart={
                  <BarList ariaLabel={`Supported opportunities ${title.toLowerCase()}`} labelWidth={130}
                    items={[...rows].sort((a, b) => b.recommended_count - a.recommended_count).map((row) => ({
                      label: title === "By segment" ? humanize(row.name) : row.name, value: row.recommended_count,
                      detail: [{ label: "Customers", value: count(row.customer_count) }],
                    }))} />
                }
                table={
                  <DataTable rows={[...rows]} rowKey={(row) => row.name} caption={title}
                    initialSort={{ key: "rec", dir: "desc" }}
                    columns={[
                      { key: "name", header: title.replace("By ", "").replace(/^./, (c) => c.toUpperCase()), sort: (row) => row.name, render: (row) => title === "By segment" ? humanize(row.name) : row.name },
                      { key: "cust", header: "Customers", numeric: true, sort: (row) => row.customer_count, render: (row) => count(row.customer_count) },
                      { key: "rec", header: "Supported", numeric: true, sort: (row) => row.recommended_count, render: (row) => count(row.recommended_count) },
                    ]} />
                } />
            ))}
          </div>
        </div>
      </section>

      {(analytics.quality_counts || analytics.missingness) && (
        <section className="section">
          <div className="section-head">
            <h2 className="section-title">How much the evidence can be trusted</h2>
            <p className="section-note">Across {count(decisions)} product decisions.</p>
          </div>
          <div className="grid-2">
            {analytics.quality_counts && <QualityPanel counts={analytics.quality_counts} total={decisions} />}
            {analytics.missingness && (
              <section className="panel">
                <h3 className="panel-title">What's missing</h3>
                <p className="panel-sub">Decisions where each component isn't available. Missing values are never filled in.</p>
                <BarList ariaLabel="Missing evidence counts" labelWidth={160} color="var(--tone-neutral-mark)" max={decisions}
                  format={(value) => `${count(value)} (${decisions ? Math.round((value / decisions) * 100) : 0}%)`}
                  items={Object.entries(analytics.missingness).map(([key, value]) => ({ label: humanize(key), value }))} />
              </section>
            )}
          </div>
        </section>
      )}

      {analytics.physical_impact && <PhysicalPotential physical={analytics.physical_impact} />}

      <section className="section">
        <div className="section-head"><h2 className="section-title">Month by month</h2></div>
        {trendsPending && <SlowLoading label="Loading monthly history…" />}
        {Boolean(trendsError) && <ErrorBox error={trendsError} what="monthly trends" />}
        {trends && <Trends trends={trends} />}
      </section>
    </>
  );
}

function QualityPanel({ counts, total }: { counts: Record<string, number>; total: number }) {
  const colors: Record<string, string> = { TRUSTED: "var(--tone-supported-mark)", LIMITED: "var(--tone-info-mark)", CONFLICT: "var(--tone-conflict-mark)", OOD: "var(--tone-stopped-mark)" };
  const sum = Object.values(counts).reduce((a, b) => a + b, 0) || total || 1;
  return (
    <section className="panel">
      <h3 className="panel-title">Data trust</h3>
      <p className="panel-sub">Share of decisions by evidence quality.</p>
      <div className="meter">
        <div className="meter-track" role="img" aria-label={QUALITY_ORDER.map((key) => `${TRUST[key].label} ${counts[key] ?? 0}`).join(", ")}>
          {QUALITY_ORDER.filter((key) => counts[key]).map((key) => (
            <span key={key} style={{ width: `${((counts[key] ?? 0) / sum) * 100}%`, background: colors[key] }} title={`${TRUST[key].label}: ${counts[key]}`} />
          ))}
        </div>
      </div>
      <table className="table" style={{ marginTop: 12 }}>
        <tbody>
          {QUALITY_ORDER.map((key) => (
            <tr key={key}>
              <td><span className="row" style={{ gap: 8 }}><i className="key" style={{ background: colors[key] }} />{TRUST[key].label}</span><div className="xsmall muted">{TRUST[key].help}</div></td>
              <td className="num">{count(counts[key] ?? 0)}</td>
              <td className="num muted">{Math.round(((counts[key] ?? 0) / sum) * 100)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function PhysicalPotential({ physical }: { physical: NonNullable<PortfolioSummary["analytics"]["physical_impact"]> }) {
  return (
    <section className="section">
      <div className="section-head">
        <h2 className="section-title">Modelled physical potential</h2>
        <p className="section-note">{physical.limitation}</p>
      </div>
      {physical.groups.length ? (
        <div className="grid-3">
          {physical.groups.map((group, index) => (
            <div key={index} className="panel">
              <div className="row" style={{ gap: 8 }}>
                <i className="key" style={{ background: PRODUCT_COLORS[group.product] }} />
                <b>{productName(group.product)}</b>
              </div>
              <div className="impact-hero" style={{ marginTop: 10 }}>
                <strong className="num" style={{ fontSize: "var(--t-2xl)" }}>{decimal(group.value, 0)}</strong>
                <span className="small">{prettyUnit(group.units)}</span>
              </div>
              <Disclosure title="How it's calculated">
                <dl className="kv">
                  <dt>Boundary</dt><dd>{/\s/.test(group.boundary) ? group.boundary : humanize(group.boundary)}</dd>
                  <dt>Period</dt><dd>{periodLabel(group.period)}</dd>
                  <dt>Method</dt><dd><code>{group.method_version}</code></dd>
                  <dt>Factors</dt><dd><code>{group.factor_catalogue_version}</code></dd>
                </dl>
              </Disclosure>
            </div>
          ))}
        </div>
      ) : (
        <Callout kind="info" title="Physical potential isn't available for this selection" />
      )}
      <p className="xsmall muted" style={{ marginTop: 8 }}>
        Each total only adds up decisions that share a product, unit, boundary, period and factor version. There is deliberately no cross-product carbon total.
        {physical.unavailable_count ? ` ${count(physical.unavailable_count)} supported decisions have no estimate.` : ""}
      </p>
    </section>
  );
}

function Trends({ trends }: { trends: PortfolioTrends }) {
  const months = useMemo(() => [...new Set(trends.observations.map((row) => row.month))].sort(), [trends]);
  const products = PRODUCT_ORDER.filter((product) => trends.observations.some((row) => row.product === product));
  const lookup = new Map(trends.observations.map((row) => [`${row.month}|${row.product}`, row]));
  const analytics = trends.analytics?.observations ?? [];
  if (!trends.observations.length) return <Callout kind="info" title="No monthly history for these filters" />;
  return (
    <div className="stack">
      <ChartFrame title="Supported opportunities each month" note={trends.disclaimer}
        chart={
          <LineChart ariaLabel="Supported opportunities per month, by product" categories={months} formatX={month}
            series={products.map((product) => ({
              key: product, label: PRODUCTS[product].name, color: PRODUCT_COLORS[product],
              points: months.map((value) => lookup.get(`${value}|${product}`)?.recommended_count ?? null),
            }))} />
        }
        table={
          <DataTable rows={trends.observations} rowKey={(row) => `${row.month}|${row.product}`} pageSize={24} caption="Monthly observations"
            initialSort={{ key: "month", dir: "desc" }}
            columns={[
              { key: "month", header: "Month", sort: (row) => row.month, render: (row) => month(row.month) },
              { key: "product", header: "Product", sort: (row) => row.product, render: (row) => productName(row.product) },
              { key: "cust", header: "Customers", numeric: true, render: (row) => count(row.customer_count) },
              { key: "rec", header: "Supported", numeric: true, sort: (row) => row.recommended_count, render: (row) => count(row.recommended_count) },
              { key: "abs", header: "Held back", numeric: true, render: (row) => count(row.abstained_count as number) },
              { key: "p", header: "Avg likelihood", numeric: true, render: (row) => percentage(row.average_propensity as string) },
              { key: "t", header: "Avg data trust", numeric: true, render: (row) => percentage(row.average_trust as string, 0) },
            ]} />
        } />
      {analytics.length > 0 && (
        <div className="panel">
          <Disclosure title="Observed outcomes and evidence by month" hint={trends.analytics.limitation}>
            <DataTable rows={analytics} rowKey={(row) => `${row.month}|${row.product}`} pageSize={24} caption="Historical evidence by month"
              initialSort={{ key: "month", dir: "desc" }}
              columns={[
                { key: "month", header: "Month", sort: (row) => row.month, render: (row) => month(row.month) },
                { key: "product", header: "Product", render: (row) => productName(row.product) },
                { key: "conv", header: "Observed conversion", numeric: true, render: (row) => percentage(row.observed_conversion_rate) },
                { key: "out", header: "Outcomes recorded", numeric: true, render: (row) => count(row.observed_outcome_count) },
                { key: "miss", header: "Outcome missing", numeric: true, render: (row) => count(row.outcome_missing_count as number) },
                { key: "imp", header: "Impact status", render: (row) => humanize(row.physical_impact_status as string) },
              ]} />
          </Disclosure>
          {analytics.some((row) => row.physical_impact_groups.length) && (
            <Disclosure title="Physical impact by month">
              <DataTable rows={analytics.flatMap((row) => row.physical_impact_groups.map((group, index) => ({ month: row.month, product: row.product, index, ...group })))}
                rowKey={(row) => `${row.month}|${row.product}|${row.index}`} caption="Physical impact by month"
                columns={[
                  { key: "month", header: "Month", render: (row) => month(row.month) },
                  { key: "product", header: "Product", render: (row) => productName(row.product) },
                  { key: "value", header: "Value", numeric: true, render: (row) => `${decimal((row as any).value, 1)} ${prettyUnit((row as any).units)}` },
                  { key: "method", header: "Method", render: (row) => <code className="xsmall">{String((row as any).method_version ?? "")}</code> },
                ]} />
            </Disclosure>
          )}
        </div>
      )}
    </div>
  );
}
