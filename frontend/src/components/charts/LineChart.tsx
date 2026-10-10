import { useState } from "react";
import { Legend, niceTicks, tickLabel, TipRow, Tooltip, useWidth } from "./common";

export interface LineSeries { key: string; label: string; color: string; points: (number | null)[] }

/** Categorical-x line chart with a crosshair tooltip and end labels. Gaps stay gaps. */
export function LineChart({ categories, series, ariaLabel, formatX = (value) => value, formatY = tickLabel, yMax, height = 260 }: {
  categories: string[]; series: LineSeries[]; ariaLabel: string; formatX?: (value: string) => string;
  formatY?: (value: number) => string; yMax?: number; height?: number;
}) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const [hover, setHover] = useState<number | null>(null);
  const vertical = { top: 12, bottom: 28 };
  const plotH = height - vertical.top - vertical.bottom;
  const values = series.flatMap((item) => item.points.filter((value): value is number => value !== null));
  const integer = values.every((value) => Number.isInteger(value));
  const ticks = niceTicks(yMax ?? Math.max(1, ...values), 4, integer && !yMax);
  const top = ticks[ticks.length - 1];
  const y = (value: number) => vertical.top + plotH - (value / top) * plotH;

  // End labels only when every series ends clear of its neighbours.
  const ends = series
    .map((item) => {
      const last = [...item.points].reverse().findIndex((value) => value !== null);
      if (last < 0) return null;
      const index = item.points.length - 1 - last;
      return { item, index, y: y(item.points[index] as number) };
    })
    .filter((item): item is NonNullable<typeof item> => item !== null)
    .sort((a, b) => a.y - b.y);
  // Converging lines: nudged labels would detach from their lines, so rely on the legend.
  const showEnds = series.length > 1 && ends.every((end, i) => i === 0 || end.y - ends[i - 1].y >= 14);
  const margin = { ...vertical, right: showEnds ? 112 : 24, left: 44 };
  const plotW = Math.max(60, width - margin.left - margin.right);
  const x = (index: number) => margin.left + (categories.length === 1 ? plotW / 2 : (index / (categories.length - 1)) * plotW);
  const every = Math.max(1, Math.ceil(categories.length / Math.max(2, Math.floor(plotW / 70))));
  const path = (points: (number | null)[]) => {
    let d = "";
    let pen = false;
    points.forEach((value, index) => {
      if (value === null) { pen = false; return; }
      d += `${pen ? "L" : "M"}${x(index)},${y(value)} `;
      pen = true;
    });
    return d;
  };


  return (
    <div>
      {series.length > 1 && <Legend items={series.map((item) => ({ label: item.label, color: item.color, line: true }))} />}
      <div className="chart-wrap" ref={ref} onMouseLeave={() => setHover(null)}>
        <svg className="chart" width={width} height={height} role="img" aria-label={ariaLabel}
          onMouseMove={(event) => {
            const box = event.currentTarget.getBoundingClientRect();
            const px = event.clientX - box.left - margin.left;
            const index = categories.length === 1 ? 0 : Math.round((px / plotW) * (categories.length - 1));
            setHover(Math.min(categories.length - 1, Math.max(0, index)));
          }}>
          {ticks.map((tick) => (
            <g key={tick}>
              <line className={tick === 0 ? "baseline" : "gridline"} x1={margin.left} x2={margin.left + plotW} y1={y(tick)} y2={y(tick)} />
              <text x={margin.left - 8} y={y(tick) + 4} textAnchor="end">{formatY(tick)}</text>
            </g>
          ))}
          {categories.map((category, index) => index % every === 0 || index === categories.length - 1 ? (
            <text key={category} x={x(index)} y={height - 8} textAnchor="middle">{formatX(category)}</text>
          ) : null)}
          {hover !== null && <line className="baseline" x1={x(hover)} x2={x(hover)} y1={margin.top} y2={margin.top + plotH} />}
          {series.map((item) => (
            <g key={item.key}>
              <path d={path(item.points)} fill="none" stroke={item.color} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
              {item.points.map((value, index) => value === null ? null : (
                <circle key={index} cx={x(index)} cy={y(value)} r={hover === index ? 5 : 3.5} fill={item.color} stroke="var(--surface)" strokeWidth={2} />
              ))}
            </g>
          ))}
          {showEnds && ends.map((end) => (
            <text key={end.item.key} x={x(end.index) + 10} y={end.y + 4} className="label-ink">{end.item.label}</text>
          ))}
        </svg>
        {hover !== null && (
          <Tooltip x={x(hover)} y={margin.top} width={width}>
            <b>{formatX(categories[hover])}</b>
            {series.map((item) => (
              <TipRow key={item.key} color={item.color} label={item.label}
                value={item.points[hover] === null ? "Not available" : formatY(item.points[hover] as number)} />
            ))}
          </Tooltip>
        )}
      </div>
    </div>
  );
}
