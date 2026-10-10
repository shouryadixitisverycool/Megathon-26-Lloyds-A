import { useEffect, useRef, useState, type ReactNode } from "react";
import type { DecisionState, Product } from "../../api/types";

export const PRODUCT_COLORS: Record<Product, string> = {
  EV_FINANCE: "var(--p-ev)",
  GREEN_HOME: "var(--p-home)",
  SOLAR_FINANCE: "var(--p-solar)",
  PAPERLESS_BANKING: "var(--p-paper)",
};

/** Hues only for states needing action; "nothing to do" states stay neutral on purpose. */
export const STATE_COLORS: Record<DecisionState, string> = {
  RECOMMEND: "var(--tone-supported-mark)",
  INSUFFICIENT_INFORMATION: "var(--tone-info-mark)",
  CONFLICT_REQUIRES_REVIEW: "var(--tone-conflict-mark)",
  DO_NOT_RECOMMEND: "var(--tone-neutral-mark)",
  NOT_APPLICABLE: "var(--tone-muted-mark)",
  SUPPRESSED: "var(--tone-stopped-mark)",
};

export function useWidth<T extends HTMLElement>(fallback = 640) {
  const ref = useRef<T>(null);
  const [width, setWidth] = useState(fallback);
  useEffect(() => {
    if (!ref.current) return;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.max(240, Math.floor(entry.contentRect.width))));
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);
  return [ref, width] as const;
}

/** Clean axis ticks (1/2/5 × 10^n) covering 0..max. */
export function niceTicks(max: number, count = 4, integer = false): number[] {
  if (!(max > 0)) return [0, 1];
  const raw = max / count;
  const magnitude = 10 ** Math.floor(Math.log10(raw));
  let step = [1, 2, 2.5, 5, 10].map((m) => m * magnitude).find((s) => s >= raw) ?? raw;
  if (integer) step = Math.max(1, Math.ceil(step));
  const ticks: number[] = [];
  for (let value = 0; value <= max + step * 0.001; value += step) ticks.push(Number(value.toFixed(10)));
  if (ticks[ticks.length - 1] < max) ticks.push(ticks[ticks.length - 1] + step);
  return ticks;
}

export function tickLabel(value: number): string {
  if (Math.abs(value) >= 1000) return `${Number((value / 1000).toFixed(1))}K`;
  return Number.isInteger(value) ? String(value) : value.toFixed(value < 1 ? 2 : 1);
}

/** Rounded data-end, square at the baseline (horizontal bars grow left→right). */
export function barPath(x: number, y: number, width: number, height: number, radius = 4, roundEnd = true): string {
  const w = Math.max(0, width);
  const r = roundEnd ? Math.min(radius, w, height / 2) : 0;
  return `M${x},${y} H${x + w - r} Q${x + w},${y} ${x + w},${y + r} V${y + height - r} Q${x + w},${y + height} ${x + w - r},${y + height} H${x} Z`;
}

/** Rounded top, square at the baseline (vertical columns grow bottom→top). */
export function columnPath(x: number, y: number, width: number, height: number, radius = 4): string {
  const h = Math.max(0, height);
  const r = Math.min(radius, width / 2, h);
  return `M${x},${y + h} V${y + r} Q${x},${y} ${x + r},${y} H${x + width - r} Q${x + width},${y} ${x + width},${y + r} V${y + h} Z`;
}

export function Legend({ items }: { items: { label: string; color: string; line?: boolean }[] }) {
  return (
    <div className="legend" aria-hidden="true">
      {items.map((item) => (
        <span key={item.label}><i className={"key" + (item.line ? " is-line" : "")} style={{ background: item.color }} />{item.label}</span>
      ))}
    </div>
  );
}

export function Tooltip({ x, y, width, children }: { x: number; y: number; width: number; children: ReactNode }) {
  // Flip to the left of the pointer near the right edge so it never overflows.
  const left = x > width - 190 ? Math.max(0, x - 190) : x + 14;
  return <div className="chart-tip" style={{ left, top: Math.max(0, y - 10) }}>{children}</div>;
}

export function TipRow({ color, label, value }: { color?: string; label: string; value: ReactNode }) {
  return (
    <div className="tip-row">
      <span>{color && <i className="key" style={{ background: color }} />}{label}</span>
      <b>{value}</b>
    </div>
  );
}
