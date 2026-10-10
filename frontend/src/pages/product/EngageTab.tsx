import { useEffect, useState } from "react";
import { customerPath } from "../../api/client";
import { useHistory, usePreferences } from "../../api/hooks";
import type { AuditEvent, Channel, CustomerSnapshot, Preferences, Recommendation } from "../../api/types";
import { useSubmit } from "../../api/useSubmit";
import { DataTable } from "../../components/DataTable";
import { Callout, Disclosure, ErrorBox, JsonView, Loading } from "../../components/ui";
import { dateTime, humanize, month, percentage } from "../../lib/format";
import { CHANNEL_ORDER, CHANNELS, LIFECYCLE, productName, RESPONSES, REVIEW_ACTIONS, stateLabel } from "../../lib/labels";

export function EngageTab({ row, snapshot, channel }: { row: Recommendation; snapshot: CustomerSnapshot; channel: Channel }) {
  return (
    <div className="stack" style={{ gap: 32 }}>
      <ContactPreferences customerId={snapshot.customer_id} />
      <RecordResponse row={row} channel={channel} />
      <History row={row} />
    </div>
  );
}

function ContactPreferences({ customerId }: { customerId: string }) {
  const prefs = usePreferences(customerId);
  const [draft, setDraft] = useState<Preferences | null>(null);
  useEffect(() => { if (prefs.data) setDraft(prefs.data); }, [prefs.data]);
  const save = useSubmit(customerPath(customerId, "/preferences"), [["customer", customerId]], "Contact preferences saved");

  return (
    <section className="stack-sm">
      <h3 className="subhead">Contact preferences</h3>
      <p className="small muted">Applies to every product for this customer. Outreach needs consent for the channel you plan to use.</p>
      {prefs.isPending && <Loading />}
      {prefs.isError && <ErrorBox error={prefs.error} what="contact preferences" />}
      {draft && (
        <form className="panel stack-sm" onSubmit={(event) => {
          event.preventDefault();
          save.submit({ do_not_contact: draft.do_not_contact, channel_consent: draft.channel_consent });
        }}>
          <label className="check">
            <input type="checkbox" checked={draft.do_not_contact} onChange={(event) => setDraft({ ...draft, do_not_contact: event.target.checked })} />
            <span><b>Do not contact</b><small>Stops all outreach, whatever the channel consents say.</small></span>
          </label>
          <hr style={{ margin: "8px 0" }} />
          <span className="field-label">Customer has agreed to be contacted by</span>
          <div className="grid-2" style={{ gap: 10 }}>
            {CHANNEL_ORDER.map((value) => (
              <label key={value} className="check">
                <input type="checkbox" disabled={draft.do_not_contact} checked={draft.channel_consent[value] === true}
                  onChange={(event) => setDraft({ ...draft, channel_consent: { ...draft.channel_consent, [value]: event.target.checked } })} />
                <span>{CHANNELS[value]}</span>
              </label>
            ))}
          </div>
          <div className="form-actions">
            <button className="btn btn-primary" type="submit" disabled={save.isPending}>{save.isPending ? "Saving…" : "Save preferences"}</button>
          </div>
        </form>
      )}
    </section>
  );
}

function RecordResponse({ row, channel }: { row: Recommendation; channel: Channel }) {
  const [response, setResponse] = useState("INTERESTED");
  const [note, setNote] = useState("");
  const save = useSubmit("/feedback", [["customer", row.customer_id]], "Response recorded");
  return (
    <section className="stack-sm">
      <h3 className="subhead">Record the customer's response</h3>
      <p className="small muted">
        Responses change follow-up and the journey stage only. They never change scores. Completing an action must reach the source data before it counts.
      </p>
      <form className="panel stack-sm" onSubmit={(event) => {
        event.preventDefault();
        save.submit({ customer_id: row.customer_id, product: row.product, response, channel, note }, );
      }}>
        <fieldset style={{ border: 0, padding: 0, margin: 0 }}>
          <legend className="field-label" style={{ marginBottom: 8 }}>How did they respond to {productName(row.product)}?</legend>
          <div className="choice-grid">
            {RESPONSES.map((item) => (
              <label key={item.value} className="choice">
                <input type="radio" name="response" value={item.value} checked={response === item.value} onChange={() => setResponse(item.value)} />
                <span><b>{item.label}</b><small>{item.help}</small></span>
              </label>
            ))}
          </div>
        </fieldset>
        <div className="field">
          <label htmlFor="response-note">Note (optional)</label>
          <textarea id="response-note" className="textarea" maxLength={2000} value={note} onChange={(event) => setNote(event.target.value)}
            placeholder="What did the customer say?" />
          <span className="field-hint">Recorded against the {CHANNELS[channel].toLowerCase()} channel. {note.length}/2000</span>
        </div>
        <div className="form-actions">
          <button className="btn btn-primary" type="submit" disabled={save.isPending}>{save.isPending ? "Recording…" : "Record response"}</button>
        </div>
        {save.isError && <Callout kind="error" title="Response not recorded">{(save.error as Error).message}</Callout>}
      </form>
    </section>
  );
}

function describe(event: AuditEvent): { title: string; detail?: string } {
  switch (event.kind) {
    case "feedback": {
      const label = RESPONSES.find((item) => item.value === event.response)?.label ?? humanize(event.response);
      const stage = event.lifecycle_state ? `Journey: ${LIFECYCLE[event.previous_state ?? ""] ?? humanize(event.previous_state)} to ${LIFECYCLE[event.lifecycle_state] ?? humanize(event.lifecycle_state)}` : undefined;
      return { title: `Customer response: ${label}`, detail: [stage, event.note].filter(Boolean).join(". ") || undefined };
    }
    case "review": {
      const label = REVIEW_ACTIONS.find((item) => item.value === event.action)?.label ?? humanize(event.action);
      return { title: `Review: ${label}${event.reviewer ? ` by ${event.reviewer}` : ""}`, detail: event.note };
    }
    case "simulation": return { title: "Carbon scenario calculated", detail: event.method_version as string | undefined };
    case "sensitivity": return { title: "Model sensitivity checked", detail: Object.entries((event.changes as Record<string, number>) ?? {}).map(([key, value]) => `${humanize(key)} = ${value}`).join(", ") };
    case "contact": return { title: `Simulated contact (${event.channel ?? "unknown channel"})`, detail: "No message was sent." };
    case "source_completion": return { title: "Journey closed by a verified source update" };
    default: return { title: humanize(event.kind) };
  }
}

function History({ row }: { row: Recommendation }) {
  const history = useHistory(row.customer_id, row.product);
  const events = [...(history.data?.events ?? [])].reverse();
  return (
    <section className="stack-sm">
      <h3 className="subhead">History for {productName(row.product)}</h3>
      {history.isPending && <Loading />}
      {history.isError && <ErrorBox error={history.error} what="history" />}
      {history.data && (
        <>
          {events.length ? (
            <ol className="timeline">
              {events.map((event) => {
                const text = describe(event);
                return (
                  <li key={event.id}>
                    <span className="node" aria-hidden="true" />
                    <div>
                      <span className="when">{dateTime(event.timestamp)}</span>
                      <div><b>{text.title}</b></div>
                      {text.detail && <div className="small muted">{text.detail}</div>}
                      <div className="xsmall muted">Audit event <code>{event.id}</code></div>
                    </div>
                  </li>
                );
              })}
            </ol>
          ) : <p className="small muted">No responses, reviews or scenarios recorded yet.</p>}
          <p className="xsmall muted">{history.data.limitation}</p>
          <div>
            <Disclosure title="Monthly decision history" hint={`${history.data.source_history.length} months`}>
              {history.data.source_history.length ? (
                <DataTable rows={history.data.source_history as Record<string, any>[]} rowKey={(item, index) => `${item.month}-${index}`} pageSize={24}
                  caption="Historical monthly decisions" initialSort={{ key: "month", dir: "desc" }}
                  columns={[
                    { key: "month", header: "Month", sort: (item) => item.month, render: (item) => month(item.month) },
                    { key: "state", header: "Decision", render: (item) => stateLabel(item.state) },
                    { key: "p", header: "Likelihood", numeric: true, render: (item) => percentage(item.propensity) },
                    { key: "t", header: "Data trust", numeric: true, render: (item) => percentage(item.trust_score, 0) },
                    { key: "i", header: "Impact", render: (item) => item.impact_status === "AVAILABLE" ? `${item.impact_value} ${item.impact_units}` : "Not available" },
                    { key: "o", header: "Adopted within 90 days", render: (item) => item.observed_adoption_90d === null || item.observed_adoption_90d === undefined ? "Not observed" : item.observed_adoption_90d ? "Yes" : "No" },
                  ]} />
              ) : <p className="small muted">No monthly history for this customer and product.</p>}
              <p className="xsmall muted" style={{ marginTop: 8 }}>Synthetic history: the current model applied to each month's data, not observed behaviour.</p>
            </Disclosure>
            <Disclosure title="Decisions served" hint={`${history.data.recommendations.length} stored`}>
              <DataTable rows={history.data.recommendations as Record<string, any>[]} rowKey={(item) => item.decision_id} caption="Stored decisions"
                columns={[
                  { key: "when", header: "Decided", render: (item) => dateTime(item.timestamp) },
                  { key: "state", header: "Decision", render: (item) => stateLabel(item.state) },
                  { key: "p", header: "Likelihood", numeric: true, render: (item) => percentage(item.propensity?.probability) },
                  { key: "id", header: "Decision ID", render: (item) => <code className="xsmall">{String(item.decision_id).slice(0, 24)}…</code> },
                ]} />
            </Disclosure>
            <Disclosure title="Raw history JSON">
              <JsonView value={{ ...history.data, recommendations: `${history.data.recommendations.length} stored decisions` }} />
            </Disclosure>
          </div>
        </>
      )}
    </section>
  );
}
