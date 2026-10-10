import { useState } from "react";
import { barPath, Legend, TipRow, Tooltip, useWidth } from "./common";

export interface StackRow { label: string; segments: { key: string; value: number }[] }

/** Horizontal 100%-width stacked bars, one row per category, 2px surface gaps between segments. */
export function StackedBars({ rows, series, ariaLabel, labelWidth = 140 }: {
  rows: StackRow[]; series: { key: string; label: string; color: string }[]; ariaLabel: string; labelWidth?: number;
}) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const [hover, setHover] = useState<{ row: number; key: string; x: number; y: number } | null>(null);
  const barHeight = 20;
  const rowHeight = 40;
  const totalWidth = 64;
  const plot = Math.max(80, width - labelWidth - totalWidth);
  const max = Math.max(1, ...rows.map((row) => row.segments.reduce((sum, item) => sum + item.value, 0)));
  const height = rows.length * rowHeight;
  const color = Object.fromEntries(series.map((item) => [item.key, item.color]));
  const name = Object.fromEntries(series.map((item) => [item.key, item.label]));
  const hovered = hover ? rows[hover.row] : null;
  const hoveredTotal = hovered ? hovered.segments.reduce((sum, item) => sum + item.value, 0) : 0;

  return (
    <div>
      <Legend items={series} />
      <div className="chart-wrap" ref={ref} onMouseLeave={() => setHover(null)}>
        <svg className="chart" width={width} height={height} role="img" aria-label={ariaLabel}>
          {rows.map((row, rowIndex) => {
            const y = rowIndex * rowHeight + (rowHeight - barHeight) / 2;
            const total = row.segments.reduce((sum, item) => sum + item.value, 0);
            const visible = row.segments.filter((item) => item.value > 0);
            let x = labelWidth;
            return (
              <g key={row.label}>
                <text x={0} y={y + barHeight / 2 + 4} className="label-strong">{row.label}</text>
                {visible.map((segment, index) => {
                  const w = (segment.value / max) * plot;
                  const gap = index < visible.length - 1 ? 2 : 0;
                  const start = x;
                  x += w;
                  const dim = hover && (hover.row !== rowIndex || hover.key !== segment.key);
                  return (
                    <path key={segment.key} d={barPath(start, y, Math.max(1, w - gap), barHeight, 4, index === visible.length - 1)}
                      fill={color[segment.key]} data-dim={dim ? "true" : undefined}
                      onMouseMove={(event) => {
                        const box = (event.currentTarget.ownerSVGElement as SVGSVGElement).getBoundingClientRect();
                        setHover({ row: rowIndex, key: segment.key, x: event.clientX - box.left, y: event.clientY - box.top });
                      }} />
                  );
                })}
                <text x={labelWidth + (total / max) * plot + 8} y={y + barHeight / 2 + 4} className="label-ink">{total.toLocaleString("en-GB")}</text>
              </g>
            );
          })}
        </svg>
        {hover && hovered && (
          <Tooltip x={hover.x} y={hover.y} width={width}>
            <b>{hovered.label}</b>
            <TipRow color={color[hover.key]} label={name[hover.key]}
              value={`${(hovered.segments.find((item) => item.key === hover.key)?.value ?? 0).toLocaleString("en-GB")} (${hoveredTotal ? Math.round(((hovered.segments.find((item) => item.key === hover.key)?.value ?? 0) / hoveredTotal) * 100) : 0}%)`} />
          </Tooltip>
        )}
      </div>
    </div>
  );
}
