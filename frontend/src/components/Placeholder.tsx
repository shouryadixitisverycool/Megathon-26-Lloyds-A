import type { ReactNode } from "react";
import { Hammer } from "lucide-react";
import { useToast } from "./Toast";

/**
 * Marks UI whose backend isn't built yet. Every placeholder is listed in UI_FEATURE_BACKLOG.md
 * under the same `feature` name, so it can be found and wired up later.
 */
export function PlaceholderBadge({ title = "Placeholder: not built yet" }: { title?: string }) {
  return (
    <span className="badge placeholder-badge" data-tone="muted" title={title}>
      <Hammer size={11} aria-hidden="true" /> Coming soon
    </span>
  );
}

export function PlaceholderButton({ feature, children, primary = false, small = false }: {
  feature: string; children: ReactNode; primary?: boolean; small?: boolean;
}) {
  const toast = useToast();
  return (
    <button type="button" className={"btn" + (primary ? " btn-primary" : "") + (small ? " btn-sm" : "")}
      data-placeholder={feature}
      onClick={(event) => {
        event.stopPropagation();
        toast({ kind: "info", title: `${feature} is coming soon`, detail: "This action is a placeholder. Its backend isn't built yet." });
      }}>
      {children}
    </button>
  );
}

/** A whole panel reserved for a planned feature. */
export function PlaceholderPanel({ feature, title, children }: { feature: string; title: string; children: ReactNode }) {
  return (
    <section className="panel placeholder-panel" data-placeholder={feature}>
      <div className="row" style={{ gap: 8 }}>
        <h3 className="panel-title" style={{ margin: 0 }}>{title}</h3>
        <PlaceholderBadge />
      </div>
      <div className="small muted" style={{ marginTop: 6 }}>{children}</div>
    </section>
  );
}
