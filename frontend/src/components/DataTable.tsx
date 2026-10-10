import { useMemo, useState, type ReactNode } from "react";
import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import { Info } from "./ui";

export interface Column<T> {
  key: string;
  header: ReactNode;
  render: (row: T) => ReactNode;
  /** Return a sortable primitive; omit to make the column unsortable. */
  sort?: (row: T) => string | number | null | undefined;
  numeric?: boolean;
  /** Definition shown in an info tip beside the header (kept outside the sort button). */
  info?: ReactNode;
}

/** Sortable, paginated table. Values in cells are already formatted for reading. */
export function DataTable<T>({ rows, columns, pageSize = 25, rowKey, caption, initialSort, onRowClick, selectedKey, empty }: {
  rows: T[]; columns: Column<T>[]; pageSize?: number; rowKey: (row: T, index: number) => string; caption?: string;
  initialSort?: { key: string; dir: "asc" | "desc" }; onRowClick?: (row: T) => void; selectedKey?: string; empty?: ReactNode;
}) {
  const [sort, setSort] = useState(initialSort);
  const [page, setPage] = useState(0);

  const sorted = useMemo(() => {
    const column = columns.find((item) => item.key === sort?.key);
    if (!sort || !column?.sort) return rows;
    const value = column.sort;
    return [...rows].sort((a, b) => {
      const left = value(a);
      const right = value(b);
      // Missing values always sink to the bottom, whichever direction is chosen.
      if (left === null || left === undefined) return 1;
      if (right === null || right === undefined) return -1;
      const result = typeof left === "number" && typeof right === "number" ? left - right : String(left).localeCompare(String(right));
      return sort.dir === "asc" ? result : -result;
    });
  }, [rows, columns, sort]);

  const pages = Math.max(1, Math.ceil(sorted.length / pageSize));
  const current = Math.min(page, pages - 1);
  const visible = sorted.slice(current * pageSize, current * pageSize + pageSize);

  if (!rows.length) return <>{empty ?? <p className="muted small">No rows to show.</p>}</>;

  return (
    <div>
      <div className="table-wrap">
        <table className="table">
          {caption && <caption className="visually-hidden">{caption}</caption>}
          <thead>
            <tr>
              {columns.map((column) => {
                const active = sort?.key === column.key;
                const Icon = !active ? ArrowUpDown : sort!.dir === "asc" ? ArrowUp : ArrowDown;
                return (
                  <th key={column.key} className={column.numeric ? "num" : undefined}
                    aria-sort={active ? (sort!.dir === "asc" ? "ascending" : "descending") : undefined}>
                    {column.sort ? (
                      <button type="button" className="sort" onClick={() => {
                        setPage(0);
                        setSort(active && sort!.dir === "desc" ? { key: column.key, dir: "asc" } : { key: column.key, dir: "desc" });
                      }}>
                        {column.header} <Icon size={12} aria-hidden="true" />
                      </button>
                    ) : column.header}
                    {column.info && <Info>{column.info}</Info>}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {visible.map((row, index) => {
              const key = rowKey(row, index);
              return (
                <tr key={key} className={selectedKey === key ? "is-selected" : undefined}
                  onClick={onRowClick ? () => onRowClick(row) : undefined} style={onRowClick ? { cursor: "pointer" } : undefined}>
                  {columns.map((column) => (
                    <td key={column.key} className={column.numeric ? "num" : undefined}>{column.render(row)}</td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {sorted.length > pageSize && (
        <div className="table-foot">
          <span>
            Showing {current * pageSize + 1}–{Math.min(sorted.length, (current + 1) * pageSize)} of {sorted.length.toLocaleString("en-GB")}
          </span>
          <span className="row">
            <button type="button" className="btn btn-sm" disabled={current === 0} onClick={() => setPage(current - 1)}>Previous</button>
            <span>Page {current + 1} of {pages}</span>
            <button type="button" className="btn btn-sm" disabled={current >= pages - 1} onClick={() => setPage(current + 1)}>Next</button>
          </span>
        </div>
      )}
    </div>
  );
}
