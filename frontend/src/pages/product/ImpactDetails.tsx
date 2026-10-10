import { ExternalLink } from "lucide-react";
import type { Impact } from "../../api/types";
import { DataTable } from "../../components/DataTable";
import { Callout, Disclosure, KV, Unavailable } from "../../components/ui";
import { date, dateTime, decimal, displayValue, emissionsField, humanize, impactAvailable, prettyUnit, toNumber } from "../../lib/format";

/** Snake_case boundaries become sentences; prose boundaries pass through. */
function boundaryText(boundary: string): string {
  return /\s/.test(boundary) ? boundary : humanize(boundary);
}

function isHttp(url: string | undefined | null): url is string {
  try { return !!url && ["http:", "https:"].includes(new URL(url).protocol); } catch { return false; }
}

export function ImpactDetails({ impact, compact = false }: { impact: Impact; compact?: boolean }) {
  const available = impactAvailable(impact);
  const field = emissionsField(impact.units);
  const baseline = toNumber(impact.baseline?.[field]);
  const scenario = toNumber(impact.scenario?.[field]);
  const scale = Math.max(baseline ?? 0, scenario ?? 0, 1e-9);
  const value = toNumber(impact.value);

  return (
    <div className="stack" style={{ gap: 24 }}>
      {available && value !== null ? (
        <section className="stack-sm">
          <div className="impact-hero">
            <strong className="num">{decimal(value, 1)}</strong>
            <span>{prettyUnit(impact.units)} {value >= 0 ? "potential reduction" : "potential increase"}</span>
          </div>
          <p className="small muted">Baseline minus scenario under the method below. This is a modelled opportunity, not a measured or guaranteed saving.</p>
          {(baseline !== null || scenario !== null) && (
            <div className="impact-bars" style={{ marginTop: 12 }} role="img"
              aria-label={`Baseline ${baseline ?? "unavailable"} versus scenario ${scenario ?? "unavailable"} ${impact.units}`}>
              {([["Today (baseline)", baseline, impact.baseline?.description, false], ["With the change", scenario, impact.scenario?.description, true]] as const).map(([label, amount, description, isScenario]) => (
                <div key={label}>
                  <div className="impact-bar">
                    <span><b>{label}</b></span>
                    <div className="impact-bar-track">
                      {amount !== null && <div className={"impact-bar-fill" + (isScenario ? " is-scenario" : "")} style={{ width: `${(Math.max(0, amount) / scale) * 100}%` }} />}
                    </div>
                    <span className="num nowrap">{amount === null ? "Not available" : `${decimal(amount, 1)} ${prettyUnit(impact.units)}`}</span>
                  </div>
                  {!compact && description && <p className="xsmall muted" style={{ marginLeft: 124 }}>{description}</p>}
                </div>
              ))}
            </div>
          )}
        </section>
      ) : (
        <Callout kind="info" title="No defensible carbon estimate is available">
          An unavailable estimate never means zero impact.
          {impact.issues.length > 0 && (
            <ul style={{ marginTop: 6 }}>
              {impact.issues.map((issue, index) => (
                <li key={index}>{issue.message}{issue.field ? <span className="muted"> ({humanize(issue.field.split(".").pop())})</span> : null}</li>
              ))}
            </ul>
          )}
        </Callout>
      )}

      {available && impact.issues.length > 0 && impact.issues.map((issue, index) => (
        <Callout key={index} kind="warn" title={issue.message}>{humanize(issue.code)} on {issue.field}</Callout>
      ))}

      {impact.secondary_metrics.length > 0 && (
        <section className="stack-sm">
          <h3 className="subhead">Physical actions</h3>
          <DataTable rows={impact.secondary_metrics} rowKey={(row) => row.name} caption="Physical action metrics"
            columns={[
              { key: "name", header: "Metric", render: (row) => humanize(row.name) },
              { key: "value", header: "Value", numeric: true, render: (row) => `${decimal(row.value, 1)} ${row.unit}` },
              { key: "method", header: "Method", render: (row) => <code className="xsmall">{row.method_version}</code> },
            ]} />
          <p className="xsmall muted">Physical actions aren't carbon savings; no lifecycle carbon impact is inferred from them.</p>
        </section>
      )}

      <section>
        <KV items={[
          ["What's counted", boundaryText(impact.boundary)],
          ["Period", impact.period ? `${date(impact.period.start)} to ${date(impact.period.end)} (end exclusive)` : "Not available"],
          ["Units", prettyUnit(impact.units)],
        ]} />
      </section>

      <div>
        <Disclosure title="Assumptions" hint={`${impact.assumptions.length}`}>
          <ul className="small">{impact.assumptions.map((item) => <li key={item}>{item}</li>)}</ul>
        </Disclosure>
        <Disclosure title="Not included" hint={`${impact.exclusions.length}`}>
          <ul className="small">{impact.exclusions.map((item) => <li key={item}>{item}</li>)}</ul>
        </Disclosure>
        {impact.evidence.length > 0 && (
          <Disclosure title="Inputs used" hint={`${impact.evidence.length} activity inputs`}>
            <DataTable rows={impact.evidence} rowKey={(row) => row.field} caption="Activity inputs used by the impact calculator"
              columns={[
                { key: "field", header: "Input", render: (row) => humanize(row.field) },
                { key: "value", header: "Value", render: (row) => `${displayValue(row.value)}${row.unit ? ` ${row.unit}` : ""}` },
                { key: "basis", header: "Basis", render: (row) => humanize(row.basis) },
                { key: "fresh", header: "Freshness", render: (row) => humanize(row.freshness) },
                { key: "obs", header: "Observed", render: (row) => date(row.observed_at) },
                { key: "ref", header: "Reference", render: (row) => <code className="xsmall muted">{row.reference}</code> },
              ]} />
          </Disclosure>
        )}
        {impact.factors.length > 0 && (
          <Disclosure title="Emission factors and sources" hint={`${impact.factors.length} factors`}>
            <div className="stack">
              {impact.factors.map((factor) => (
                <div key={factor.factor_id} className="panel" style={{ padding: 16 }}>
                  <div className="row-between">
                    <b>{factor.source_title}</b>
                    <span className="num">{factor.value} {prettyUnit(factor.unit)}</span>
                  </div>
                  <p className="xsmall muted" style={{ margin: "4px 0 10px" }}>{factor.applicability}</p>
                  <KV items={[
                    ["Factor", <code key="id">{factor.factor_id}</code>],
                    ["Publisher", factor.source_publisher],
                    ["Edition", factor.source_edition],
                    ["Where in the source", factor.source_locator],
                    ["Geography", factor.geography],
                    ["Activity period", factor.activity_period ?? "Not available"],
                    ["Boundary", factor.boundary],
                    ["How it was verified", factor.verification_basis],
                    ["Source SHA-256", factor.source_sha256 ? <code key="sha" className="xsmall">{factor.source_sha256}</code> : <Unavailable key="sha" />],
                  ]} />
                  {factor.source_limitation && <div style={{ marginTop: 10 }}><Callout kind="warn" title="Source limitation">{factor.source_limitation}</Callout></div>}
                  {isHttp(factor.source_url) && (
                    <a className="btn btn-sm" style={{ marginTop: 10 }} href={factor.source_url} target="_blank" rel="noreferrer noopener">
                      Open source <ExternalLink size={12} aria-hidden="true" />
                    </a>
                  )}
                </div>
              ))}
            </div>
          </Disclosure>
        )}
        <Disclosure title="Method and versions">
          <KV items={[
            ["Method", <code key="m">{impact.method_version}</code>],
            ["Method release", impact.method_release],
            ["Factor catalogue", impact.factor_catalogue_version],
            ["Catalogue SHA-256", <code key="sha" className="xsmall">{impact.factor_catalogue_sha256}</code>],
            ["Calculated at", dateTime(impact.timestamp)],
            ["Impact data cut-off", impact.feature_cutoff ? date(impact.feature_cutoff) : "Not available"],
            ["Impact passport", impact.passport_id ? <code key="p" className="xsmall">{impact.passport_id}</code> : "Not available"],
          ]} />
        </Disclosure>
      </div>
    </div>
  );
}
