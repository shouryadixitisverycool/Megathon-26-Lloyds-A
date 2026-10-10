import { useState } from "react";
import type { TrustIssue } from "../api/types";
import { humanize, plural } from "../lib/format";
import { Callout } from "./ui";

/** One summary callout per issue list; identical messages are merged and the rest open on demand. */
export function TrustIssues({ issues, preview = 1 }: { issues: TrustIssue[]; preview?: number }) {
  const [open, setOpen] = useState(false);
  if (!issues.length) return null;
  const grouped = new Map<string, { issue: TrustIssue; fields: string[] }>();
  for (const issue of issues) {
    const entry = grouped.get(issue.message) ?? { issue, fields: [] };
    entry.fields.push(issue.field);
    grouped.set(issue.message, entry);
  }
  const groups = [...grouped.values()];
  const high = issues.some((issue) => issue.severity === "HIGH");
  const shown = open ? groups : groups.slice(0, preview);
  const title = high ? "Check these records before any outreach" : "Some evidence is incomplete";
  return (
    <Callout kind={high ? "error" : "warn"} title={groups.length > 1 ? `${title} (${plural(groups.length, "issue")})` : title}>
      <ul style={{ paddingLeft: 0, listStyle: "none", display: "grid", gap: 8, marginTop: 4 }}>
        {shown.map(({ issue, fields }) => (
          <li key={issue.message} style={{ margin: 0 }}>
            <span>{issue.message}</span>
            <span className="xsmall" style={{ display: "block", opacity: 0.8 }}>
              {humanize(issue.code)}: {fields.map((field) => field.replace(/[_.]/g, " ")).join(", ")}
            </span>
          </li>
        ))}
      </ul>
      {groups.length > preview && (
        <button type="button" className="btn btn-quiet btn-sm" style={{ marginTop: 6, marginLeft: -8, color: "inherit" }} onClick={() => setOpen(!open)}>
          {open ? "Show fewer" : `Show ${plural(groups.length - preview, "more issue")}`}
        </button>
      )}
    </Callout>
  );
}
