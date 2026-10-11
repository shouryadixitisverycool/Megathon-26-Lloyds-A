import { useState } from "react";
import { useDemoReadiness, useExplanationMetrics, useGovernance } from "../api/hooks";
import type { Product } from "../api/types";
import { BarList } from "../components/charts/BarList";
import { LineChart } from "../components/charts/LineChart";
import { ChartFrame } from "../components/ChartFrame";
import { DataTable } from "../components/DataTable";
import { formatScalar, METRIC_LABELS, ReportView } from "../components/ReportView";
import { Callout, Disclosure, ErrorBox, JsonView, KV, Segmented, SelectField, SlowLoading, Stat, ToneBadge } from "../components/ui";
import { humanize, percentage } from "../lib/format";
import { PRODUCT_ORDER, PRODUCTS, productName } from "../lib/labels";
import { AuditLookup } from "./product/AuditTab";

const KEY_METRICS = ["roc_auc", "pr_auc", "brier", "ece", "precision_at_k", "lift_at_k", "threshold"];
const METRIC_HELP: Record<string, string> = {
  roc_auc: "How well the model ranks adopters above non-adopters. 0.5 is chance, 1 is perfect.",
  pr_auc: "Ranking quality focused on the rare adopters. Compare against the base rate.",
  brier: "Average squared error of the probabilities. Lower is better.",
  ece: "Expected calibration error: how far stated probabilities are from observed rates. Lower is better.",
  precision_at_k: "Share of the top 10% of customers who actually adopted.",
  lift_at_k: "How many times better than random the top 10% is.",
  threshold: "The cut-off chosen on validation data.",
};

const REPORTS: [string, string, string][] = [
  ["leakage_checks", "Leakage audit", "Checks that no information from after the cut-off date reached training."],
  ["feature_drift", "Feature drift", "How far model inputs shift between the base and perturbed data generators."],
  ["explanation_evaluation", "Explanation grounding", "Whether generated explanations only state approved facts and numbers."],
  ["scenario_evaluation", "Scenario suite", "Scripted personas covering all six decision states."],
  ["run_manifest", "Reproducibility", "Seeds, timeline, package versions and artifact hashes for this run."],
  ["system_performance", "System performance", "Measured API latency and start-up time on this machine."],
];

export function GovernancePage() {
  const governance = useGovernance();
  const [product, setProduct] = useState<Product>("EV_FINANCE");
  const data = governance.data;
  const reports = data?.reports ?? {};
  const models = reports.ml_evaluation?.products ?? {};
  const model = models[product];
  const confidence = reports.confidence_validation?.[product];

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="page-title">Governance</h1>
          <p className="lede">How the models perform on held-out synthetic data, whether they treat groups consistently, and the audit evidence behind each release.</p>
        </div>
      </div>

      {governance.isPending && <SlowLoading label="Loading diagnostics…" />}
      {governance.isError && <ErrorBox error={governance.error} what="governance diagnostics" />}

      {data && (
        <>
          <section className="panel">
            <h2 className="panel-title">Read these first</h2>
            <ul className="small" style={{ marginTop: 8 }}>{data.limitations.map((item) => <li key={item}>{item}</li>)}</ul>
            <p className="xsmall muted" style={{ marginTop: 10 }}>Model source: <code>{data.model_source}</code></p>
          </section>

          <ReleaseStatus reports={reports} />
          <DemoReadinessPanel />

          <div className="section">
            <div className="section-head">
              <h2 className="section-title">Model audit by product</h2>
              <Segmented label="Product" value={product} onChange={setProduct}
                options={PRODUCT_ORDER.filter((item) => models[item] || reports.confidence_validation?.[item]).map((value) => ({ value, label: PRODUCTS[value].name }))} />
            </div>
            {!model ? <Callout kind="warn" title="Model evaluation report not available">Run <code>make pipeline</code> to generate it.</Callout> : (
              <div className="stack">
                <ModelComparison model={model} />
                {model.subgroups && <Fairness subgroups={model.subgroups} />}
                {confidence && <Confidence report={confidence} />}
                <section className="panel">
                  <h3 className="panel-title">Robustness checks</h3>
                  <p className="panel-sub">How the model holds up without proxy features, with missing data, on a shifted generator and on a later time period.</p>
                  {(["proxy_ablation", "missing_data", "generator_shift", "temporal_holdout"] as const).map((key) => (
                    <Disclosure key={key} title={humanize(key)} hint={model[key] ? undefined : "Not run"}>
                      {model[key] ? <ReportView value={model[key]} /> : <p className="small muted">Not run.</p>}
                    </Disclosure>
                  ))}
                  <Disclosure title="Features, calibration and training counts">
                    <ReportView value={{ counts: model.counts, calibration: model.calibration, thresholds: model.thresholds, validation_metrics: model.validation_metrics, notes: model.notes, features: model.features }} />
                  </Disclosure>
                </section>
              </div>
            )}
          </div>

          <section className="section">
            <div className="section-head">
              <h2 className="section-title">Release evidence</h2>
              <p className="section-note">Saved reports from the last pipeline run. Open one to see its details.</p>
            </div>
            <div className="panel">
              {REPORTS.map(([key, title, help]) => {
                const report = reports[key] ?? { status: "NOT_RUN" };
                const missing = report.status === "NOT_RUN" || report.status === "INVALID_REPORT";
                return (
                  <Disclosure key={key} title={title} hint={missing ? humanize(report.status) : help}>
                    {missing ? <Callout kind="warn" title={`Report unavailable: ${humanize(report.status)}`} /> : <ReportSummary name={key} report={report} />}
                    {!missing && (
                      <div style={{ marginTop: 12 }}>
                        <Disclosure title="Raw report"><JsonView value={report} /></Disclosure>
                      </div>
                    )}
                  </Disclosure>
                );
              })}
              <Disclosure title="Explanation service" hint="Live counters since the API started">
                <ExplanationMetrics />
              </Disclosure>
            </div>
          </section>

          <section className="section">
            <div className="section-head"><h2 className="section-title">Look up an audit event</h2></div>
            <div className="panel"><AuditLookup /></div>
          </section>
        </>
      )}
    </div>
  );
}

function ReleaseStatus({ reports }: { reports: Record<string, any> }) {
  const leakage = reports.leakage_checks;
  const products = PRODUCT_ORDER.filter((product) => leakage?.[product]);
  const leakagePassed = products.length > 0 && products.every((product) => leakage[product].passed) && leakage.point_in_time_rebuild?.status === "PASS";
  const confidence = PRODUCT_ORDER.filter((product) => reports.confidence_validation?.[product]?.validation?.passed).length;
  const explanation = reports.explanation_evaluation?.summary;
  const scenarios = reports.scenario_evaluation?.summary;
  return (
    <section className="section">
      <div className="stats">
        <Stat label="Leakage audit" value={leakage?.status === "NOT_RUN" || !products.length ? "Not run" : leakagePassed ? "Passed" : "Failed"}
          note={products.length ? `${products.reduce((sum, product) => sum + (leakage[product].n_checks ?? 0), 0)} checks across ${products.length} products` : undefined} small />
        <Stat label="Confidence released" value={`${confidence} of 4`} note="Products whose confidence passed reliability checks" small />
        <Stat label="Grounded explanations" value={explanation ? `${explanation.passed} of ${explanation.total}` : "Not run"}
          note={explanation ? `Template fallback in ${percentage(explanation.fallback_rate, 0)}` : undefined} small />
        <Stat label="Scenario suite" value={scenarios ? `${scenarios.passed} of ${scenarios.total}` : "Not run"}
          note={scenarios ? `${scenarios.states_covered?.length ?? 0} decision states covered` : undefined} small />
      </div>
    </section>
  );
}

function ModelComparison({ model }: { model: any }) {
  const test: Record<string, Record<string, number>> = model.test ?? {};
  const names = Object.keys(test);
  return (
    <section className="panel">
      <div className="row-between">
        <div>
          <h3 className="panel-title">Held-out model comparison</h3>
          <p className="panel-sub">Test-set results for each candidate. The deployed model was chosen on validation data, not on these numbers.</p>
        </div>
        <ToneBadge tone="supported">Deployed: {humanize(model.selected_model)}</ToneBadge>
      </div>
      {names.length ? (
        <DataTable rows={names} rowKey={(name) => name} selectedKey={model.selected_model} caption="Model comparison on held-out test data"
          columns={[
            { key: "model", header: "Model", render: (name) => <b>{humanize(name)}{name === model.selected_model ? " (deployed)" : ""}</b> },
            ...KEY_METRICS.map((metric) => ({
              key: metric, numeric: true,
              header: <span title={METRIC_HELP[metric]}>{METRIC_LABELS[metric]}</span>,
              render: (name: string) => formatScalar(test[name][metric]),
            })),
          ]} />
      ) : <p className="small muted">No test metrics in this report.</p>}
      <p className="xsmall muted" style={{ marginTop: 8 }}>
        Hover a column heading for what it measures. Version <code>{model.model_version}</code>.
        {model.counts && ` Test set: ${model.counts.n_test?.toLocaleString("en-GB")} customers, ${model.counts.n_test_positive} adopters.`}
      </p>
      <div style={{ marginTop: 8 }}>
        <Disclosure title="All test metrics">
          <ReportView value={test} />
        </Disclosure>
      </div>
    </section>
  );
}

function Fairness({ subgroups }: { subgroups: Record<string, any> }) {
  const groups = Object.keys(subgroups);
  const [group, setGroup] = useState(groups[0]);
  const current = subgroups[group] ?? subgroups[groups[0]];
  const table: Record<string, any>[] = current?.table ?? [];
  return (
    <ChartFrame title="Consistency across groups"
      note="Selection rate is the share of each group the model would flag. Small groups and groups with few adopters are noisy, and metrics that can't be computed stay blank. Audit groups never enter the default model features."
      actions={<SelectField label="Audit group" value={group} onChange={setGroup} options={groups.map((value) => ({ value, label: humanize(value) }))} />}
      chart={
        <div className="stack-sm">
          <BarList ariaLabel={`Selection rate by ${humanize(group)}`} labelWidth={140} max={1}
            format={(value) => `${(value * 100).toFixed(1)}%`} color="var(--p-ev)"
            items={table.map((row) => ({ label: String(row.group), value: row.selection_rate ?? null,
              detail: [{ label: "Customers", value: String(row.n) }, { label: "Adopters", value: String(row.positives) }, { label: "ROC AUC", value: row.roc_auc === null ? "Not available" : row.roc_auc.toFixed(3) }] }))} />
          {current?.disparity && (
            <KV items={Object.entries(current.disparity).map(([key, value]) => [humanize(key), formatScalar(value)])} />
          )}
        </div>
      }
      table={<ReportView value={table} />} />
  );
}

function Confidence({ report }: { report: any }) {
  const validation = report.validation ?? {};
  const deciles: { bin: number; error_rate: number }[] = validation.deciles ?? [];
  const passed = validation.passed === true;
  return (
    <section className="panel">
      <div className="row-between">
        <div>
          <h3 className="panel-title">Confidence reliability</h3>
          <p className="panel-sub">Higher confidence has to mean fewer mistakes on held-out data. If that test fails, confidence is hidden from customers and staff.</p>
        </div>
        <ToneBadge tone={passed ? "supported" : "info"}>{passed ? "Validated" : "Suppressed"}</ToneBadge>
      </div>
      {(validation.reasons ?? []).map((reason: string) => <Callout key={reason} kind="warn" title={reason} />)}
      {deciles.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <LineChart ariaLabel="Held-out error rate by confidence bucket" categories={deciles.map((row) => String(row.bin))}
            formatX={(value) => `Bucket ${value}`} formatY={(value) => `${Math.round(value * 100)}%`}
            series={[{ key: "error", label: "Held-out error rate", color: "var(--p-ev)", points: deciles.map((row) => row.error_rate) }]} height={220} />
        </div>
      )}
      <div style={{ marginTop: 8 }}>
        {validation.criteria && (
          <Disclosure title="Release criteria">
            <ReportView value={validation.criteria} />
          </Disclosure>
        )}
        {report.stress && (
          <Disclosure title="Stress tests">
            <ReportView value={report.stress} />
          </Disclosure>
        )}
        {report.ablation && (
          <Disclosure title="Confidence ablation">
            <ReportView value={report.ablation} />
          </Disclosure>
        )}
      </div>
    </section>
  );
}

function ReportSummary({ name, report }: { name: string; report: any }) {
  if (name === "leakage_checks") {
    const rows = PRODUCT_ORDER.filter((product) => report[product]).map((product) => ({ product, ...report[product] }));
    return (
      <div className="stack-sm">
        <p className="small">Point-in-time rebuild: <b>{report.point_in_time_rebuild?.status ?? "Not run"}</b>. {report.point_in_time_rebuild?.detail}</p>
        <DataTable rows={rows} rowKey={(row) => row.product} caption="Leakage checks by product"
          columns={[
            { key: "product", header: "Product", render: (row) => productName(row.product) },
            { key: "status", header: "Result", render: (row) => <ToneBadge tone={row.passed ? "supported" : "conflict"}>{row.passed ? "Passed" : "Failed"}</ToneBadge> },
            { key: "n", header: "Checks", numeric: true, render: (row) => row.n_checks },
            { key: "f", header: "Failed", numeric: true, render: (row) => row.n_failed },
            { key: "nr", header: "Not run", numeric: true, render: (row) => row.n_not_run },
          ]} />
        <Disclosure title="Every check">
          <ReportView value={rows.flatMap((row) => (row.checks ?? []).map((check: any) => ({ product: productName(row.product), ...check })))} />
        </Disclosure>
      </div>
    );
  }
  if (name === "feature_drift") {
    const features = [...(report.features ?? [])].sort((a: any, b: any) => (b.ks_statistic ?? 0) - (a.ks_statistic ?? 0));
    return (
      <div className="stack-sm">
        <p className="small">{humanize(report.reference)} ({report.reference_customers?.toLocaleString("en-GB")}) compared with {report.comparison} ({report.comparison_customers?.toLocaleString("en-GB")}).</p>
        <p className="small muted">Largest shifts by Kolmogorov–Smirnov statistic (0 is identical, 1 is completely different):</p>
        <BarList ariaLabel="Largest feature drifts" labelWidth={200} max={1} color="var(--p-solar)" format={(value) => value.toFixed(3)}
          items={features.slice(0, 10).map((row: any) => ({ label: humanize(row.feature), value: row.ks_statistic }))} />
        <p className="xsmall muted">{report.limitation}</p>
        <Disclosure title={`All ${features.length} features`}><ReportView value={features} /></Disclosure>
      </div>
    );
  }
  if (name === "system_performance") {
    return (
      <div className="stack-sm">
        {(report.runs ?? []).map((run: any) => (
          <div key={run.provider_mode} className="stack-sm">
            <p className="small"><b>{humanize(run.provider_mode)} mode</b>: started in {run.startup_seconds?.toFixed(1)}s.</p>
            <DataTable rows={Object.entries(run.api ?? {}) as [string, any][]} rowKey={([route]) => route} caption="API latency"
              columns={[
                { key: "route", header: "Route", render: ([route]) => <code className="xsmall">{route}</code> },
                { key: "p50", header: "Median", numeric: true, render: ([, value]) => `${value.p50_ms.toFixed(1)} ms` },
                { key: "p95", header: "95th percentile", numeric: true, render: ([, value]) => `${value.p95_ms.toFixed(1)} ms` },
                { key: "n", header: "Requests", numeric: true, render: ([, value]) => value.n },
              ]} />
          </div>
        ))}
        <ul className="xsmall muted">{(report.limitations ?? []).map((item: string) => <li key={item}>{item}</li>)}</ul>
      </div>
    );
  }
  if (name === "run_manifest") {
    return <ReportView value={{ seeds: report.seeds, timeline: report.timeline, feature_version: report.feature_version, environment: report.environment, split_manifest_sha256: report.split_manifest_sha256 }} />;
  }
  if (report.summary) {
    return (
      <div className="stack-sm">
        <ReportView value={report.summary} />
        {report.limitations && <ul className="xsmall muted">{report.limitations.map((item: string) => <li key={item}>{item}</li>)}</ul>}
        {report.cases && <Disclosure title={`All ${report.cases.length} cases`}><ReportView value={report.cases} /></Disclosure>}
      </div>
    );
  }
  return <ReportView value={report} />;
}

function ExplanationMetrics() {
  const metrics = useExplanationMetrics();
  if (metrics.isPending) return <SlowLoading label="Loading…" />;
  if (metrics.isError) return <ErrorBox error={metrics.error} what="explanation metrics" />;
  return <ReportView value={metrics.data} />;
}

/** /demo/readiness: whether each product has a live, defensible example to demo. Loaded on request. */
function DemoReadinessPanel() {
  const [open, setOpen] = useState(false);
  const readiness = useDemoReadiness(open);
  const data = readiness.data;
  const tone = (status: string) => (status === "READY" ? "supported" : status === "BLOCKED" ? "conflict" : "neutral");
  return (
    <section className="panel" style={{ marginTop: 16 }}>
      <h2 className="panel-title">Demo readiness</h2>
      <p className="panel-sub">
        Checks the served models and evidence for a live example per product. A product is blocked until it has a supported
        decision with validated confidence, so fixture mode and suppressed confidence always show as blocked.
      </p>
      <Disclosure title="Run the readiness check" hint="Can take a while in trained mode" onToggle={setOpen}>
        {readiness.isPending && <SlowLoading label="Checking demo readiness…" />}
        {readiness.isError && <ErrorBox error={readiness.error} what="demo readiness" />}
        {data && (
          <div className="stack">
            <div className="row">
              <ToneBadge tone={tone(data.status)}>Overall: {humanize(data.status)}</ToneBadge>
              <span className="small muted">
                {humanize(data.provider_mode)} mode
                {data.live_checked_customers !== undefined && <>, {data.live_checked_customers} customers checked live</>}
              </span>
            </div>
            <DataTable rows={PRODUCT_ORDER.filter((product) => data.products[product])} rowKey={(product) => product} caption="Readiness by product"
              columns={[
                { key: "product", header: "Product", render: (product) => productName(product) },
                { key: "status", header: "Status", render: (product) => <ToneBadge tone={tone(data.products[product]!.status)}>{humanize(data.products[product]!.status)}</ToneBadge> },
                { key: "scored", header: "Scored", numeric: true, render: (product) => data.products[product]!.coverage?.scored_customers ?? "–" },
                { key: "above", header: "Above cut-off", numeric: true, render: (product) => data.products[product]!.coverage?.above_threshold ?? "–" },
                { key: "validated", header: "Validated confidence", numeric: true, render: (product) => data.products[product]!.coverage?.validated_confidence ?? "–" },
                { key: "example", header: "Example customer", render: (product) => data.products[product]!.candidate?.customer_id ?? "None" },
              ]} />
            {data.missing_features.length > 0 && (
              <Callout kind="warn" title="Missing"><ul>{data.missing_features.map((item) => <li key={item}>{item}</li>)}</ul></Callout>
            )}
            {data.limitation && <p className="xsmall muted">{data.limitation}</p>}
            <Disclosure title="Raw readiness report"><JsonView value={data} /></Disclosure>
          </div>
        )}
      </Disclosure>
    </section>
  );
}
