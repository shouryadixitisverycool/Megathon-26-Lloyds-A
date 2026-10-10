import { Check, Circle, RefreshCw } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { useExplanation } from "../../api/hooks";
import type { CustomerSnapshot, Recommendation } from "../../api/types";
import { TrustIssues } from "../../components/TrustIssues";
import { Callout, Disclosure, ErrorBox, Info, KV, Loading, ToneBadge } from "../../components/ui";
import { explanationOrigin } from "../../lib/ai";
import { humanize } from "../../lib/format";
import { featureLabel, MODEL_REASONS } from "../../lib/labels";

export function WhyTab({ row, snapshot }: { row: Recommendation; snapshot: CustomerSnapshot }) {
  const explanation = useExplanation(row.customer_id, row.product);
  const modelReasons = row.propensity?.reason_codes ?? [];
  const data = explanation.data;
  const origin = data ? explanationOrigin(data) : null;
  const client = useQueryClient();
  // Transient AI failures aren't cached by the API, so asking again makes a fresh attempt.
  const retry = async () => {
    await explanation.refetch();
    client.invalidateQueries({ queryKey: ["explanation-metrics"] });
  };

  return (
    <div className="stack" style={{ gap: 28 }}>
      <section className="stack-sm">
        <div className="row-between">
          <h3 className="subhead" style={{ margin: 0 }}>In plain words</h3>
          {origin && (
            <span className="row" style={{ gap: 4 }}>
              <ToneBadge tone={origin.tone}>{origin.badge}</ToneBadge>
              <Info label="About who wrote this">
                {origin.title ? <><b>{origin.title}.</b> </> : null}{origin.detail}
              </Info>
            </span>
          )}
        </div>
        {explanation.isPending && <Loading label="Writing a grounded explanation…" />}
        {origin && origin.tone === "info" && (
          <Callout kind="info" title={origin.title}>
            {origin.detail} The standard wording below has the same approved facts.
            {origin.retry && (
              <div style={{ marginTop: 8 }}>
                <button type="button" className="btn btn-sm" onClick={retry} disabled={explanation.isFetching}>
                  <RefreshCw size={12} className={explanation.isFetching ? "spin" : undefined} aria-hidden="true" />
                  {explanation.isFetching ? "Asking the AI again…" : "Ask the AI again"}
                </button>
              </div>
            )}
          </Callout>
        )}
        {data && !data.validation_passed && (
          <Callout kind="warn" title="This explanation didn't pass its grounding check">Rely on the evidence below rather than the wording.</Callout>
        )}
        {explanation.isError && (
          <>
            <ErrorBox error={explanation.error} what="the explanation" />
            <p className="small muted">The decision and its evidence below are unaffected.</p>
          </>
        )}
        {data && (data.explanation ? (
          <div className="prose">
            <p>{data.explanation}</p>
            {data.why_recommended.length > 0 && (
              <ul className="tick-list">
                {data.why_recommended.map((item) => <li key={item}><Check size={14} aria-hidden="true" /><span>{item}</span></li>)}
              </ul>
            )}
            {data.estimated_impact_text && <p className="small"><b>Impact.</b> {data.estimated_impact_text}</p>}
            {data.confidence_text && <p className="small muted">{data.confidence_text}</p>}
            {data.action_text && <Callout kind="success" title="Suggested next step">{data.action_text}</Callout>}
            {data.missing_information.length > 0 && (
              <Callout kind="info" title="Missing information">
                <ul>{data.missing_information.map((item) => <li key={item}>{item}</li>)}</ul>
              </Callout>
            )}
          </div>
        ) : (
          <p className="prose">{data.text}</p>
        ))}
      </section>

      <section className="stack-sm">
        <h3 className="subhead">Evidence behind the decision</h3>
        {row.evidence.length ? (
          <ul className="evidence-list">
            {row.evidence.map((item) => (
              <li key={item.code}>
                <div>{item.message}</div>
                {item.fields.length > 0 && (
                  <div className="chips">
                    {item.fields.map((field) => {
                      const value = snapshot.features[field]?.value;
                      return (
                        <span key={field} className="chip" title={snapshot.features[field]?.reference}>
                          {featureLabel(field)}: <b>{value === undefined || value === null ? "unknown" : value ? "yes" : "no"}</b>
                        </span>
                      );
                    })}
                  </div>
                )}
              </li>
            ))}
          </ul>
        ) : <p className="muted small">The API supplied no decision evidence.</p>}
        <TrustIssues issues={row.trust.issues} preview={3} />
      </section>

      {modelReasons.length > 0 && (
        <section className="stack-sm">
          <h3 className="subhead">What the model picked up on</h3>
          <ul className="tick-list is-plain">
            {modelReasons.map((code) => <li key={code}><Circle size={10} aria-hidden="true" /><span>{MODEL_REASONS[code] ?? humanize(code)}</span></li>)}
          </ul>
          <p className="xsmall muted">Rule-based reason codes checked against the customer's data. They aren't causal and aren't SHAP values (see Audit trail).</p>
        </section>
      )}

      <section className="stack-sm">
        <h3 className="subhead">What this doesn't cover</h3>
        <ul className="small">{row.exclusions.map((item) => <li key={item}>{item}</li>)}</ul>
        <p className="small muted">{row.eligibility_disclaimer}</p>
      </section>

      <div>
        <Disclosure title="About this explanation" hint="Source, validation and reason codes">
          <KV items={[
            ["Reason codes", row.reason_codes.join(", ") || "None"],
            ...(data ? [
              ["Written by", data.source === "llm" ? "AI, limited to approved sentences and checked" : "Standard wording (grounded template)"],
              ["Writer version", data.provider_version],
              ["Grounding check", data.validation_passed ? "Passed" : "Failed"],
              ["Why the AI wasn't used", data.source === "llm" ? "Not applicable" : `${origin?.title ?? "Unknown"} (${data.fallback_reason ?? "no reason given"})`],
              ["Headline", data.headline ?? "Not provided"],
            ] as [string, string][] : []),
          ]} />
          {data?.text && (
            <div style={{ marginTop: 12 }}>
              <p className="small muted" style={{ marginBottom: 6 }}>Full generated text</p>
              <p className="small prose">{data.text}</p>
            </div>
          )}
          <div style={{ marginTop: 12 }}>
            <p className="small muted" style={{ marginBottom: 6 }}>Evidence references</p>
            {row.evidence.some((item) => item.references.length) ? (
              <ul className="xsmall">
                {row.evidence.flatMap((item) => item.references).map((ref) => <li key={ref}><code>{ref}</code></li>)}
              </ul>
            ) : <p className="xsmall muted">None supplied.</p>}
          </div>
        </Disclosure>
      </div>
    </div>
  );
}
