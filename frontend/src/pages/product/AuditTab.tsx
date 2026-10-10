import { useState } from "react";
import { useAuditEvent, useShap } from "../../api/hooks";
import type { CustomerSnapshot, Recommendation } from "../../api/types";
import { Callout, Disclosure, ErrorBox, JsonView, KV, Loading, Unavailable } from "../../components/ui";
import { date, dateTime, percentage } from "../../lib/format";
import { humanField } from "../../lib/labels";

export function AuditTab({ row, snapshot }: { row: Recommendation; snapshot: CustomerSnapshot }) {
  const propensity = row.propensity;
  return (
    <div className="stack" style={{ gap: 28 }}>
      <section className="stack-sm">
        <h3 className="subhead">Versions behind this decision</h3>
        <KV items={[
          ["Decision ID", row.decision_id ? <code key="d" className="xsmall">{row.decision_id}</code> : <Unavailable key="d" />],
          ["Data cut-off", date(row.feature_cutoff)],
          ["Decided at", dateTime(row.timestamp)],
          ["Decision rules", <code key="r">{row.rules_version}</code>],
          ["Model", propensity ? <code key="m">{propensity.model_version}</code> : <Unavailable key="m" />],
          ["Calibration", propensity?.calibration_version ? <code key="c">{propensity.calibration_version}</code> : <Unavailable key="c" />],
          ["Likelihood cut-off", percentage(propensity?.decision_threshold)],
          ["In model population", propensity ? (propensity.in_model_population ? "Yes" : `No (${propensity.population_exclusion ?? "excluded"})`) : <Unavailable key="p" />],
          ["Data trust method", row.trust.version ?? "Not available"],
          ["API contract", row.contract_version],
        ]} />
      </section>

      <section className="stack-sm">
        <h3 className="subhead">Decision exclusions</h3>
        <ul className="small">{row.exclusions.map((item) => <li key={item}>{item}</li>)}</ul>
      </section>

      <div>
        <Disclosure title="Feature attribution (SHAP)" hint="Trained models only">
          <Shap row={row} enabled={snapshot.source_snapshot !== null} />
        </Disclosure>
        <Disclosure title="Full stored audit record" hint="Decision plus every explanation run">
          {row.decision_id ? <StoredRecord id={row.decision_id} /> : <p className="small muted">This decision has no stored ID.</p>}
        </Disclosure>
        <Disclosure title="Scored decision JSON" hint="As served by the API">
          <JsonView value={{ ...row, provenance: row.provenance ? "(see Provenance)" : undefined }} />
        </Disclosure>
        {row.provenance && (
          <Disclosure title="Provenance JSON" hint="Snapshot and versions captured with the decision">
            <JsonView value={row.provenance} />
          </Disclosure>
        )}
        <Disclosure title="Look up another audit event" hint="By event or decision ID">
          <AuditLookup />
        </Disclosure>
      </div>
    </div>
  );
}

function Shap({ row, enabled }: { row: Recommendation; enabled: boolean }) {
  const shap = useShap(row.customer_id, row.product, enabled);
  if (!enabled) return <Callout kind="info" title="Not available for demo personas">SHAP attribution needs the trained models. Fixture probabilities have nothing to attribute.</Callout>;
  if (shap.isPending) return <Loading label="Computing attribution…" />;
  if (shap.isError) return <ErrorBox error={shap.error} what="SHAP attribution" />;
  const data = shap.data!;
  const entry = data.rows?.[0];
  if (!entry) return <Callout kind="info" title="SHAP attribution unavailable">{data.limitation ?? "The API returned no attribution for this decision."}</Callout>;
  const values = Object.entries(entry.shap_values).filter(([, value]) => value !== 0).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));
  const top = values.slice(0, 12);
  const max = Math.max(...top.map(([, value]) => Math.abs(value)), 1e-9);
  return (
    <div className="stack-sm">
      <Callout kind="warn" title="Read with care">
        These values explain the model's raw, uncalibrated log-odds score, not the calibrated likelihood shown elsewhere, and they aren't causal effects.
        The rule-based reasons on the Why tab are separate.
      </Callout>
      <div className="legend">
        <span><i className="key" style={{ background: "var(--p-ev)" }} />Pushes the score up</span>
        <span><i className="key" style={{ background: "var(--p-solar)" }} />Pushes the score down</span>
      </div>
      <div className="stack-sm" role="list" aria-label="Largest feature contributions">
        {top.map(([feature, value]) => (
          <div key={feature} className="shap-row" role="listitem">
            <span title={feature}>{humanField(feature)}</span>
            <span className="shap-bar" aria-hidden="true">
              <span className={value >= 0 ? "pos" : "neg"} style={{ width: `${(Math.abs(value) / max) * 50}%` }} />
            </span>
            <span className="num" style={{ textAlign: "right" }}>{value >= 0 ? "+" : ""}{value.toFixed(3)}</span>
          </div>
        ))}
      </div>
      {values.length > top.length && <p className="xsmall muted">Showing the 12 largest of {values.length} non-zero contributions.</p>}
      <KV items={[
        ["Model", `${data.model_version ?? ""} (${data.model_type ?? "unknown type"})`],
        ["Method", data.method ?? "Not available"],
        ["Output explained", data.output_space ?? "Not available"],
        ["Base value", entry.base_value.toFixed(4)],
        ["Raw score", entry.raw_margin.toFixed(4)],
        ["Additivity residual", entry.additivity_residual.toExponential(2)],
        ["Background", data.background ? `${data.background.source}, ${data.background.rows.toLocaleString("en-GB")} rows` : "Not available"],
      ]} />
    </div>
  );
}

function StoredRecord({ id }: { id: string }) {
  const record = useAuditEvent(id);
  if (record.isPending) return <Loading />;
  if (record.isError) return <ErrorBox error={record.error} what="the stored record" />;
  return <JsonView value={record.data} />;
}

export function AuditLookup() {
  const [input, setInput] = useState("");
  const [id, setId] = useState<string | null>(null);
  const record = useAuditEvent(id);
  return (
    <div className="stack-sm">
      <form className="row" onSubmit={(event) => { event.preventDefault(); setId(input.trim() || null); }}>
        <div className="field" style={{ flex: "1 1 280px" }}>
          <label htmlFor="audit-id">Audit event or decision ID</label>
          <input id="audit-id" className="input" value={input} onChange={(event) => setInput(event.target.value)} placeholder="Paste an ID from a confirmation or history entry" />
        </div>
        <button className="btn" type="submit" style={{ alignSelf: "flex-end" }} disabled={!input.trim()}>Look up</button>
      </form>
      {id && record.isPending && <Loading />}
      {id && record.isError && <ErrorBox error={record.error} what="that audit event" />}
      {id && record.data && <JsonView value={record.data} />}
    </div>
  );
}
