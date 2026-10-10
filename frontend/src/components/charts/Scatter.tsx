import { useState } from "react";
import { Legend, niceTicks, tickLabel, TipRow, Tooltip, useWidth } from "./common";

export interface ScatterPoint { id: string; x: number; y: number; group: string }

/** Propensity (x, 0–100%) against modelled impact (y) for one comparable impact group. */
export function Scatter({ points, groups, ariaLabel, yLabel, onSelect, height = 300 }: {
  points: ScatterPoint[]; groups: { key: string; label: string; color: string }[]; ariaLabel: string; yLabel: string;
  onSelect?: (id: string) => void; height?: number;
}) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const [hover, setHover] = useState<ScatterPoint | null>(null);
  const margin = { top: 12, right: 16, bottom: 40, left: 56 };
  const plotW = Math.max(60, width - margin.left - margin.right);
  const plotH = height - margin.top - margin.bottom;
  const minY = Math.min(0, ...points.map((point) => point.y));
  const ticks = niceTicks(Math.max(1, ...points.map((point) => point.y)));
  const top = ticks[ticks.length - 1];
  const x = (value: number) => margin.left + value * plotW;
  const y = (value: number) => margin.top + plotH - ((value - minY) / (top - minY)) * plotH;
  const color = Object.fromEntries(groups.map((group) => [group.key, group.color]));
  const label = Object.fromEntries(groups.map((group) => [group.key, group.label]));

  return (
    <div>
      {groups.length > 1 && <Legend items={groups} />}
      <div className="chart-wrap" ref={ref} onMouseLeave={() => setHover(null)}>
        <svg className="chart" width={width} height={height} role="img" aria-label={ariaLabel}>
          {ticks.map((tick) => (
            <g key={tick}>
              <line className={tick === 0 ? "baseline" : "gridline"} x1={margin.left} x2={margin.left + plotW} y1={y(tick)} y2={y(tick)} />
              <text x={margin.left - 8} y={y(tick) + 4} textAnchor="end">{tickLabel(tick)}</text>
            </g>
          ))}
          {[0, 0.25, 0.5, 0.75, 1].map((tick) => (
            <text key={tick} x={x(tick)} y={margin.top + plotH + 16} textAnchor="middle">{tick * 100}%</text>
          ))}
          <text x={margin.left + plotW / 2} y={height - 4} textAnchor="middle">Adoption likelihood</text>
          <text x={12} y={margin.top + plotH / 2} textAnchor="middle" transform={`rotate(-90 12 ${margin.top + plotH / 2})`}>{yLabel}</text>
          {points.map((point) => (
            <circle key={point.id} cx={x(point.x)} cy={y(point.y)} r={hover?.id === point.id ? 7 : 5}
              fill={color[point.group] ?? "var(--ink-3)"} stroke="var(--surface)" strokeWidth={2}
              style={{ cursor: onSelect ? "pointer" : "default" }}
              onMouseEnter={() => setHover(point)} onClick={() => onSelect?.(point.id)}>
              <title>{point.id}</title>
            </circle>
          ))}
        </svg>
        {hover && (
          <Tooltip x={x(hover.x)} y={y(hover.y)} width={width}>
            <b>{hover.id}</b>
            <TipRow color={color[hover.group]} label={label[hover.group] ?? hover.group} value="" />
            <TipRow label="Likelihood" value={`${(hover.x * 100).toFixed(1)}%`} />
            <TipRow label="Impact" value={hover.y.toLocaleString("en-GB", { maximumFractionDigits: 1 })} />
          </Tooltip>
        )}
      </div>
    </div>
  );
}
