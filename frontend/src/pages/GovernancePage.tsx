import { useState } from "react";
import { useExplanationMetrics, useGovernance } from "../api/hooks";
import type { Product } from "../api/types";
import { BarList } from "../components/charts/BarList";
import { LineChart } from "../components/charts/LineChart";
import { ChartFrame } from "../components/ChartFrame";
import { DataTable } from "../components/DataTable";
import { formatScalar, METRIC_LABELS, ReportView } from "../components/ReportView";
import { Callout, Disclosure, ErrorBox, JsonView, KV, Segmented, SelectField, SlowLoading, Stat, ToneBadge } from "../components/ui";
import { Check } from "lucide-react";
import { aiEnabled, aiModel } from "../lib/ai";
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
            </div>
          </section>

          <AiExplanations evaluation={reports.explanation_evaluation} />

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

function AiExplanations({ evaluation }: { evaluation?: any }) {
  const metrics = useExplanationMetrics();
  const data = metrics.data;
  const enabled = aiEnabled(data);
  const measured = data?.provider_measurements;
  const summary = evaluation?.summary;
  const ms = (value: number | null | undefined) => (value === null || value === undefined ? "Not measured" : `${value.toFixed(1)} ms`);
  return (
    <section className="section">
      <div className="section-head">
        <h2 className="section-title">AI-written explanations</h2>
        <p className="section-note">How the plain-language explanations on each product are produced, and how they're kept to the facts.</p>
      </div>
      <div className="stack">
        {metrics.isPending && <SlowLoading label="Checking the explanation service…" />}
        {metrics.isError && <ErrorBox error={metrics.error} what="explanation service status" />}
        {data && (
          <>
            <div className="stats">
              <Stat label="AI writing" value={enabled ? "On" : "Off"} small
                note={enabled ? `Model ${aiModel(data) ?? "configured"}` : "Standard wording is used everywhere"} />
              <Stat label="Explanations served" value={data.requests.toLocaleString("en-GB")} small
                note={`${percentage(data.cache_hit_rate, 0)} reused from cache`} />
              <Stat label="AI calls completed" value={enabled ? `${data.provider_completed} of ${data.provider_attempts}` : "None"} small
                note={enabled ? `Average AI response ${ms(data.live_provider_latency_ms)}` : `Average local time ${ms(data.average_latency_ms)}`} />
              <Stat label="AI cost so far" small
                value={data.live_provider_cost !== null && data.live_provider_cost !== undefined ? data.live_provider_cost.toFixed(4) : enabled ? "Not measured" : "None"}
                note={enabled ? (measured?.pricing_basis === "explicit configured token prices" ? "From configured token prices" : "Set token prices on the API to measure") : "No paid calls are made"} />
            </div>
            {!enabled && (
              <Callout kind="info" title="AI writing is switched off">
                Every explanation uses the standard wording, which states the same approved facts. To switch the AI on, start the API with
                <code> OPENAI_API_KEY</code> (or <code>GREENR_LLM_API_KEY</code>) set. This makes paid calls to the provider; the model and
                settings come from <code>src/greenr/llm/provider_manifest.json</code>, which is selected but not yet live-evaluated.
              </Callout>
            )}
          </>
        )}
        <div className="grid-2">
          <section className="panel">
            <h3 className="panel-title">How it stays grounded</h3>
            <ul className="tick-list" style={{ marginTop: 12 }}>
              {[
                "The AI only sees approved reasons, the product, the decision, the exact carbon figure and the disclaimer. Raw transaction text and customer identifiers are never sent.",
                "It can only choose the order of pre-approved sentences. It can't write new claims.",
                "Every fact, number, unit and disclaimer is checked before display. Any mismatch, timeout or error falls back to the standard wording.",
                "It can't change a score, an impact estimate or eligibility.",
              ].map((item) => <li key={item}><Check size={14} aria-hidden="true" /><span className="small">{item}</span></li>)}
            </ul>
          </section>
          <section className="panel">
            <h3 className="panel-title">Offline evaluation</h3>
            <p className="panel-sub">{evaluation?.provider ? `Run with ${evaluation.provider}.` : "Saved from the last pipeline run."}</p>
            {summary ? (
              <KV items={[
                ["Cases passed", `${summary.passed} of ${summary.total}`],
                ["Grounded", percentage(summary.groundedness_rate, 0)],
                ["Numbers consistent", percentage(summary.numeric_consistency_rate, 0)],
                ["Unsupported claims", String(summary.unsupported_claims)],
                ["Fell back to standard wording", percentage(summary.fallback_rate, 0)],
                ["Live AI latency and cost", summary.live_provider_latency_ms === null ? "Not measured (no live run)" : ms(summary.live_provider_latency_ms)],
              ]} />
            ) : <p className="small muted">The explanation evaluation report hasn't been generated. Run <code>make evaluate-llm</code>.</p>}
          </section>
        </div>
        {data && (
          <div className="panel">
            <Disclosure title="All service counters" hint="Live since the API started">
              <ReportView value={data} />
            </Disclosure>
          </div>
        )}
      </div>
    </section>
  );
}
