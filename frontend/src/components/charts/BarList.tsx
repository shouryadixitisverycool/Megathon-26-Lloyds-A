import { useState } from "react";
import { barPath, TipRow, Tooltip, useWidth } from "./common";

export interface BarItem { label: string; value: number | null; note?: string; detail?: { label: string; value: string }[] }

/** One-series horizontal bars with the value at the tip. Missing values are labelled, not drawn as zero. */
export function BarList({ items, ariaLabel, color = "var(--tone-supported-mark)", format = (value) => value.toLocaleString("en-GB"), labelWidth = 150, max: fixedMax }: {
  items: BarItem[]; ariaLabel: string; color?: string; format?: (value: number) => string; labelWidth?: number; max?: number;
}) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const [hover, setHover] = useState<{ index: number; x: number; y: number } | null>(null);
  const barHeight = 16;
  const rowHeight = 30;
  const valueWidth = 72;
  const plot = Math.max(60, width - labelWidth - valueWidth);
  const max = fixedMax ?? Math.max(1e-9, ...items.map((item) => item.value ?? 0));
  const height = items.length * rowHeight;
  const hovered = hover ? items[hover.index] : null;

  return (
    <div className="chart-wrap" ref={ref} onMouseLeave={() => setHover(null)}>
      <svg className="chart" width={width} height={height} role="img" aria-label={ariaLabel}>
        {items.map((item, index) => {
          const y = index * rowHeight + (rowHeight - barHeight) / 2;
          const w = item.value === null ? 0 : (Math.max(0, item.value) / max) * plot;
          return (
            <g key={item.label + index} data-dim={hover && hover.index !== index ? "true" : undefined}
              onMouseMove={(event) => {
                const box = (event.currentTarget.ownerSVGElement as SVGSVGElement).getBoundingClientRect();
                setHover({ index, x: event.clientX - box.left, y: event.clientY - box.top });
              }}>
              <rect className="hit" x={0} y={index * rowHeight} width={width} height={rowHeight} />
              <text x={0} y={y + barHeight / 2 + 4} className="label-ink">
                {item.label.length > 22 && labelWidth < 180 ? item.label.slice(0, 21) + "…" : item.label}
              </text>
              {item.value !== null && w > 0 && <path d={barPath(labelWidth, y, Math.max(2, w), barHeight)} fill={color} />}
              <text x={labelWidth + w + 8} y={y + barHeight / 2 + 4} className={item.value === null ? undefined : "label-ink"}>
                {item.value === null ? "Not available" : format(item.value)}
              </text>
            </g>
          );
        })}
      </svg>
      {hover && hovered && (
        <Tooltip x={hover.x} y={hover.y} width={width}>
          <b>{hovered.label}</b>
          <TipRow color={color} label="Value" value={hovered.value === null ? "Not available" : format(hovered.value)} />
          {hovered.detail?.map((row) => <TipRow key={row.label} label={row.label} value={row.value} />)}
          {hovered.note && <div className="muted" style={{ marginTop: 4 }}>{hovered.note}</div>}
        </Tooltip>
      )}
    </div>
  );
}
