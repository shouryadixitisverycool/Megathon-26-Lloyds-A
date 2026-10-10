import type { Propensity } from "../api/types";
import { percentValue, toNumber } from "../lib/format";
import { Info } from "./ui";

/**
 * The model's adoption likelihood on a 0–100% line, with this product's cut-off marked.
 * It shows why a product is or isn't supported without needing to read a number.
 */
export function ThresholdRail({ propensity, compact = false, label = "Adoption likelihood" }: {
  propensity: Propensity | null | undefined; compact?: boolean; label?: string;
}) {
  const probability = percentValue(propensity?.probability);
  const threshold = percentValue(propensity?.decision_threshold);
  const help = (
    <>
      The model's calibrated estimate of how likely this customer is to take up the product, trained on synthetic data.
      The tick marks the cut-off chosen on validation data. This is product relevance, not credit eligibility.
    </>
  );

  if (probability === null) {
    const reason = propensity?.population_exclusion
      ? `Not scored: ${propensity.population_exclusion.replace(/_/g, " ").toLowerCase()}`
      : "No likelihood available";
    return (
      <div className={"rail" + (compact ? " is-compact" : "")}>
        <span className="opp-metric-label">{label}</span>
        <span className="rail-empty">{reason}</span>
      </div>
    );
  }
  const above = threshold !== null ? probability >= threshold : undefined;
  const clamp = (value: number) => Math.min(100, Math.max(0, value));
  return (
    <div className={"rail" + (compact ? " is-compact" : "")}>
      <div className="rail-top">
        <span className="opp-metric-label">{label} {!compact && <Info>{help}</Info>}</span>
        <span className="rail-value">{probability.toFixed(1)}%</span>
      </div>
      <div className="rail-track" role="img"
        aria-label={`${probability.toFixed(1)}% likelihood${threshold !== null ? `, cut-off ${threshold.toFixed(1)}%` : ""}`}>
        {threshold !== null && <span className="rail-pass" style={{ left: `${clamp(threshold)}%`, right: 0 }} />}
        {threshold !== null && <span className="rail-tick" style={{ left: `${clamp(threshold)}%` }} />}
        <span className="rail-dot" data-above={above === undefined ? undefined : String(above)} style={{ left: `${clamp(probability)}%` }} />
      </div>
      {threshold !== null && (
        <span className="rail-caption">
          {above ? "Above" : "Below"} the {threshold.toFixed(1)}% cut-off
          {!compact && toNumber(propensity?.probability) !== null && above && threshold > 0 && ` (${(probability / threshold).toFixed(1)}×)`}
        </span>
      )}
    </div>
  );
}
