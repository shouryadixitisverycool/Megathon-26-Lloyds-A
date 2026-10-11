import type { Channel, CustomerSnapshot, Recommendation } from "../../api/types";
import { ThresholdRail } from "../../components/ThresholdRail";
import { Info, StateBadge, Tabs, ToneBadge, Unavailable } from "../../components/ui";
import { impactAvailable, impactLabel, percentage } from "../../lib/format";
import { PRODUCTS, STATES, trustLabel } from "../../lib/labels";
import { trustTone } from "../CustomersPage";
import { AuditTab } from "./AuditTab";
import { EngageTab } from "./EngageTab";
import { ExploreTab } from "./ExploreTab";
import { ImpactDetails } from "./ImpactDetails";
import { ReviewTab } from "./ReviewTab";
import { WhatIfTab } from "./WhatIfTab";
import { WhyTab } from "./WhyTab";

export type DetailTab = "why" | "impact" | "explore" | "whatif" | "engage" | "review" | "audit";

const TABS: { id: DetailTab; label: string }[] = [
  { id: "why", label: "Why" },
  { id: "impact", label: "Impact" },
  { id: "explore", label: "Explore partners" },
  { id: "whatif", label: "What-if" },
  { id: "engage", label: "Contact & history" },
  { id: "review", label: "Review" },
  { id: "audit", label: "Audit trail" },
];

export function ProductDetailHeader({ row, snapshot, tab, onTab }: {
  row: Recommendation; snapshot: CustomerSnapshot; tab: DetailTab; onTab: (tab: DetailTab) => void;
}) {
  const product = PRODUCTS[row.product];
  const tabs = row.product === "PAPERLESS_BANKING" ? TABS.filter((item) => item.id !== "explore") : TABS;
  const confidence = row.propensity?.confidence_validated ? percentage(row.propensity.confidence) : null;
  return (
    <>
      <p className="small muted">{snapshot.customer_id}</p>
      <h2 className="drawer-title">{product?.name ?? row.product}</h2>
      <div className="row" style={{ marginTop: 8, gap: 10 }}>
        <StateBadge state={row.state} />
        <span className="small muted">{STATES[row.state]?.help}</span>
      </div>
      {tab !== "explore" && <div className="stats detail-stats" style={{ marginTop: 20 }}>
        <div className="stat"><ThresholdRail propensity={row.propensity} /></div>
        <div className="stat">
          <span className="stat-label">Model confidence
            <Info>How reliable the model is for this specific case. It's shown only after its held-out reliability check passes; otherwise it stays hidden rather than guessed.</Info>
          </span>
          <span className="stat-value is-small">{confidence ?? <Unavailable>Not validated</Unavailable>}</span>
          <span className="stat-note">{confidence ? "Validated on held-out data" : "Hidden until reliability is proven"}</span>
        </div>
        <div className="stat">
          <span className="stat-label">Data trust
            <Info>Quality of the evidence behind this product decision: completeness, freshness and consistency. Separate from model confidence.</Info>
          </span>
          <span className="stat-value is-small">{percentage(row.trust.score, 0)}</span>
          <span className="stat-note"><ToneBadge tone={trustTone(row.trust.status)}>{trustLabel(row.trust.status)}</ToneBadge></span>
        </div>
        <div className="stat">
          <span className="stat-label">Potential impact
            <Info>Baseline emissions minus scenario emissions under a stated method. A modelled opportunity, not a realised reduction. Unavailable never means zero.</Info>
          </span>
          <span className="stat-value is-small">{impactAvailable(row.impact) ? impactLabel(row.impact) : <Unavailable />}</span>
          <span className="stat-note">{impactAvailable(row.impact) ? "Modelled, per year" : "No defensible estimate"}</span>
        </div>
      </div>}
      <div style={{ marginTop: 16 }}>
        <Tabs label="Product details" tabs={tabs} value={tab} onChange={onTab} />
      </div>
    </>
  );
}

export function ProductDetail({ row, snapshot, tab, channel }: {
  row: Recommendation; snapshot: CustomerSnapshot; tab: DetailTab; channel: Channel;
}) {
  return (
    <div className="tab-panel" role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
      {tab === "why" && <WhyTab row={row} snapshot={snapshot} />}
      {tab === "impact" && <ImpactDetails impact={row.impact} />}
      {tab === "explore" && row.product !== "PAPERLESS_BANKING" && <ExploreTab product={row.product} state={row.state} />}
      {tab === "whatif" && <WhatIfTab row={row} snapshot={snapshot} />}
      {tab === "engage" && <EngageTab row={row} snapshot={snapshot} channel={channel} />}
      {tab === "review" && <ReviewTab row={row} snapshot={snapshot} />}
      {tab === "audit" && <AuditTab row={row} snapshot={snapshot} />}
    </div>
  );
}
