import { usePromo } from "../../api/hooks";
import type { Channel, PromoCopy, PromoFormat, Recommendation } from "../../api/types";
import { Callout, Disclosure, ErrorBox, KV, Loading, ToneBadge } from "../../components/ui";
import { dateTime, humanize } from "../../lib/format";
import { CHANNELS, productName } from "../../lib/labels";

const STYLES: { format: PromoFormat; name: string; placement: string; limit: string }[] = [
  { format: "push", name: "Push notification", placement: "Phone lock screen", limit: "1 line · up to 50 characters" },
  { format: "one_liner", name: "One-liner banner", placement: "App home or web banner", limit: "1 line · up to 80 characters" },
  { format: "short", name: "Short card", placement: "In-app card", limit: "2–4 lines · up to 320 characters" },
  { format: "medium", name: "Medium email block", placement: "Email or message centre", limit: "3–5 lines · up to 480 characters" },
];

/** Bank-facing gallery: the same governed opportunity rendered in every ad size. */
export function AdStylesTab({ row, channel }: { row: Recommendation; channel: Channel }) {
  const promos = STYLES.map((style) => ({ style, query: usePromo(row.customer_id, row.product, style.format, channel, true) }));
  const first = promos[0].query.data;
  return (
    <div className="stack" style={{ gap: 24 }}>
      <section className="stack-sm">
        <h3 className="subhead">Targeted ad styles for {productName(row.product)}</h3>
        <p className="small muted">
          Every size of message this customer could be shown. The copy is written from this decision, its reason themes and the carbon estimate only. The button text and disclaimer are fixed, and every AI-written line passes the copy checks or is replaced by a template.
        </p>
        {first && <SendStatus promo={first} channel={channel} />}
      </section>
      <div className="ad-grid">
        {promos.map(({ style, query }) => (
          <section key={style.format} className="ad-style">
            <header className="row-between" style={{ gap: 8 }}>
              <div>
                <div className="panel-title" style={{ marginBottom: 0 }}>{style.name}</div>
                <span className="small muted">{style.placement} · {style.limit}</span>
              </div>
              {query.data && query.data.status !== "WITHHELD" && <SourceBadge promo={query.data} />}
            </header>
            {query.isPending && <Loading />}
            {query.isError && <ErrorBox error={query.error} what={style.name.toLowerCase()} />}
            {query.data && query.data.status !== "WITHHELD" && <Mock promo={query.data} />}
            {query.data && query.data.status !== "WITHHELD" && (
              <span className="small muted">{query.data.text?.length ?? 0} characters</span>
            )}
          </section>
        ))}
      </div>
      {first && first.status !== "WITHHELD" && (
        <Disclosure title="What this targeting is based on">
          <KV items={[
            ["Themes", first.angles.length ? first.angles.join(", ") : "None beyond the product itself"],
            ["Reason codes", row.reason_codes.join(", ") || "None"],
            ["Carbon figure", promos.some(({ query }) => query.data?.impact_value != null) ? "From the carbon engine, rounded and labelled as an estimate" : "Not used"],
            ["Data as of", dateTime(first.data_timestamp)],
          ]} />
        </Disclosure>
      )}
    </div>
  );
}

function SendStatus({ promo, channel }: { promo: PromoCopy; channel: Channel }) {
  if (promo.status === "AVAILABLE") {
    return <Callout kind="success" title={`Ready to use on ${CHANNELS[channel].toLowerCase()}`}>The contact rules allow outreach on this channel.</Callout>;
  }
  if (promo.status === "PREVIEW") {
    return (
      <Callout kind="warn" title="Preview only, not sendable yet">
        {promo.withheld_reason}. The decision supports this product, but these messages can't be used until the contact rules allow it.
      </Callout>
    );
  }
  return (
    <Callout kind="note" title="No ad styles for this product">
      {promo.withheld_reason}. Messages are only drafted when the decision supports the product.
    </Callout>
  );
}

function SourceBadge({ promo }: { promo: PromoCopy }) {
  const written = promo.source === "llm";
  return (
    <ToneBadge tone={written ? "supported" : "neutral"}
      title={written ? `Written by ${promo.provider_version} and passed every copy check` : promo.fallback_reason ? `Template used: ${humanize(promo.fallback_reason)}` : undefined}>
      {written ? "AI-written · checked" : "Template"}
    </ToneBadge>
  );
}

function Mock({ promo }: { promo: PromoCopy }) {
  const [first, ...rest] = promo.lines;
  switch (promo.format) {
    case "push":
      return (
        <div className="ad-push">
          <span className="ad-push-icon" aria-hidden="true" />
          <div>
            <div className="ad-push-meta"><b>Your bank</b><span>now</span></div>
            <p>{first}</p>
          </div>
        </div>
      );
    case "one_liner":
      return (
        <div className="promo-preview" data-format="one_liner">
          <div className="promo-body"><p>{first}</p><span className="promo-cta">{promo.cta_label}</span></div>
          <p className="promo-disclaimer">{promo.disclaimer}</p>
        </div>
      );
    case "short":
      return (
        <div className="promo-preview" data-format="short">
          <div className="promo-body">
            {promo.lines.map((line, index) => <p key={index}>{line}</p>)}
            <span className="promo-cta">{promo.cta_label}</span>
          </div>
          <p className="promo-disclaimer">{promo.disclaimer}</p>
        </div>
      );
    default:
      return (
        <div className="ad-email">
          <div className="ad-email-head"><span className="small muted">Subject</span><b>{first}</b></div>
          <div className="ad-email-body">
            {rest.map((line, index) => <p key={index}>{line}</p>)}
            <span className="promo-cta">{promo.cta_label}</span>
            <p className="promo-disclaimer">{promo.disclaimer}</p>
          </div>
        </div>
      );
  }
}
