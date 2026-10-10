import type { ReactNode } from "react";
import { humanize } from "../lib/format";
import { DataTable } from "./DataTable";
import { Disclosure, KV } from "./ui";

const METRIC_ORDER = ["n", "base_rate", "roc_auc", "pr_auc", "brier", "ece", "precision_at_k", "recall_at_k", "lift_at_k", "precision", "recall", "f1", "fpr", "fnr", "threshold"];
export const METRIC_LABELS: Record<string, string> = {
  n: "Rows", base_rate: "Base rate", roc_auc: "ROC AUC", pr_auc: "PR AUC", brier: "Brier", ece: "ECE",
  precision_at_k: "Precision@k", recall_at_k: "Recall@k", lift_at_k: "Lift@k", precision: "Precision", recall: "Recall",
  f1: "F1", fpr: "False positive rate", fnr: "False negative rate", threshold: "Threshold",
};

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function formatScalar(value: unknown): ReactNode {
  if (value === null || value === undefined) return <span className="unavailable">Not available</span>;
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") return Number.isInteger(value) ? value.toLocaleString("en-GB") : value.toFixed(Math.abs(value) < 10 ? 3 : 1);
  if (typeof value === "string") return value === "PASS" || value === "FAIL" ? <b>{value}</b> : value.length > 80 && /^[0-9a-f]+$/.test(value) ? <code className="xsmall">{value}</code> : value;
  return <code className="xsmall">{JSON.stringify(value)}</code>;
}

/** Objects whose values are all flat number maps render as one comparison table. */
function metricTable(value: Record<string, unknown>): { rows: [string, Record<string, unknown>][]; columns: string[] } | null {
  const entries = Object.entries(value);
  if (!entries.length || !entries.every(([, item]) => isObject(item) && Object.values(item).every((v) => v === null || typeof v !== "object"))) return null;
  const keys = new Set<string>();
  for (const [, item] of entries) Object.keys(item as object).forEach((key) => keys.add(key));
  const ordered = [...METRIC_ORDER.filter((key) => keys.has(key)), ...[...keys].filter((key) => !METRIC_ORDER.includes(key))];
  return { rows: entries as [string, Record<string, unknown>][], columns: ordered.slice(0, 12) };
}

export function ReportView({ value, depth = 0 }: { value: unknown; depth?: number }): ReactNode {
  if (!isObject(value)) {
    if (Array.isArray(value)) {
      if (value.length && value.every(isObject) && value.every((row) => Object.values(row).every((v) => v === null || typeof v !== "object"))) {
        const columns = [...new Set(value.flatMap((row) => Object.keys(row)))].slice(0, 10);
        return (
          <DataTable<Record<string, unknown>> rows={value as Record<string, unknown>[]} rowKey={(_, index) => String(index)} pageSize={15}
            columns={columns.map((key) => ({ key, header: METRIC_LABELS[key] ?? humanize(key), render: (row) => formatScalar(row[key]),
              sort: (row) => (typeof row[key] === "number" || typeof row[key] === "string" ? (row[key] as number | string) : null) }))} />
        );
      }
      return value.length ? <ul className="small">{value.map((item, index) => <li key={index}>{typeof item === "object" ? JSON.stringify(item) : String(item)}</li>)}</ul> : <span className="muted small">None</span>;
    }
    return formatScalar(value);
  }
  const table = metricTable(value);
  if (table) {
    return (
      <DataTable rows={table.rows} rowKey={([key]) => key}
        columns={[
          { key: "name", header: "", render: ([key]) => <b>{humanize(key)}</b> },
          ...table.columns.map((column) => ({
            key: column, header: METRIC_LABELS[column] ?? humanize(column), numeric: true,
            render: ([, row]: [string, Record<string, unknown>]) => formatScalar(row[column]),
          })),
        ]} />
    );
  }
  const scalars = Object.entries(value).filter(([, item]) => !isObject(item) && !(Array.isArray(item) && item.some(isObject)));
  const nested = Object.entries(value).filter(([, item]) => isObject(item) || (Array.isArray(item) && item.some(isObject)));
  return (
    <div className="stack-sm">
      {scalars.length > 0 && <KV items={scalars.map(([key, item]) => [METRIC_LABELS[key] ?? humanize(key), Array.isArray(item) ? item.map(String).join(", ") || "None" : formatScalar(item)])} />}
      {nested.map(([key, item]) => depth >= 3 ? (
        <Disclosure key={key} title={humanize(key)}><pre className="json">{JSON.stringify(item, null, 2)}</pre></Disclosure>
      ) : (
        <Disclosure key={key} title={humanize(key)}>
          <ReportView value={item} depth={depth + 1} />
        </Disclosure>
      ))}
    </div>
  );
}
