import { useState, type ReactNode } from "react";
import { BarChart3, Table2 } from "lucide-react";
import { Segmented } from "./ui";

/** Every chart has a table view so no value depends on colour or hover alone. */
export function ChartFrame({ title, note, chart, table, actions }: {
  title: ReactNode; note?: ReactNode; chart: ReactNode; table: ReactNode; actions?: ReactNode;
}) {
  const [view, setView] = useState<"chart" | "table">("chart");
  return (
    <section className="panel">
      <div className="chart-card-head">
        <div>
          <h3 className="panel-title">{title}</h3>
          {note && <p className="small muted" style={{ maxWidth: "70ch" }}>{note}</p>}
        </div>
        <div className="row">
          {actions}
          <Segmented label="View as" value={view} onChange={setView} options={[
            { value: "chart", label: <span className="row" style={{ gap: 6 }}><BarChart3 size={14} aria-hidden="true" />Chart</span> },
            { value: "table", label: <span className="row" style={{ gap: 6 }}><Table2 size={14} aria-hidden="true" />Table</span> },
          ]} />
        </div>
      </div>
      {view === "chart" ? chart : table}
    </section>
  );
}
