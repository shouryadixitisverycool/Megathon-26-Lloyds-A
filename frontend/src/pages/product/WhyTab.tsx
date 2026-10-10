import { Check, Circle } from "lucide-react";
import { useExplanation } from "../../api/hooks";
import type { CustomerSnapshot, Recommendation } from "../../api/types";
import { TrustIssues } from "../../components/TrustIssues";
import { Callout, Disclosure, ErrorBox, KV, Loading } from "../../components/ui";
import { humanize } from "../../lib/format";
import { featureLabel, MODEL_REASONS } from "../../lib/labels";

export function WhyTab({ row, snapshot }: { row: Recommendation; snapshot: CustomerSnapshot }) {
  const explanation = useExplanation(row.customer_id, row.product);
  const modelReasons = row.propensity?.reason_codes ?? [];
  const data = explanation.data;

  return (
    <div className="stack" style={{ gap: 28 }}>
      <section className="stack-sm">
        <h3 className="subhead">In plain words</h3>
        {explanation.isPending && <Loading label="Writing a grounded explanation…" />}
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
              ["Written by", data.source === "llm" ? "Language model, validated against approved facts" : "Grounded template"],
              ["Provider version", data.provider_version],
              ["Grounding check", data.validation_passed ? "Passed" : "Failed"],
              ["Template fallback", data.fallback_reason ? humanize(data.fallback_reason) : "Not used"],
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
