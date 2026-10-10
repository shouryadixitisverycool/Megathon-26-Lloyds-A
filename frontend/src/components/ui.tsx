import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { AlertTriangle, ChevronDown, CircleAlert, Info as InfoIcon, LoaderCircle, OctagonX, CheckCircle2 } from "lucide-react";
import type { DecisionState } from "../api/types";
import { STATES, type Tone } from "../lib/labels";

export function StateBadge({ state, short = false }: { state: DecisionState | string; short?: boolean }) {
  const meta = STATES[state as DecisionState];
  return (
    <span className="badge" data-tone={meta?.tone ?? "neutral"} title={meta?.help}>
      <span className="badge-dot" aria-hidden="true" />
      {meta ? (short ? meta.short : meta.label) : state}
    </span>
  );
}

export function ToneBadge({ tone, children, title }: { tone: Tone; children: ReactNode; title?: string }) {
  return (
    <span className="badge" data-tone={tone} title={title}>
      <span className="badge-dot" aria-hidden="true" />
      {children}
    </span>
  );
}

/** A small "i" that reveals a definition on hover, focus or tap. */
export function Info({ children, label = "More information" }: { children: ReactNode; label?: string }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const ref = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    if (!open) return;
    const close = (event: MouseEvent | KeyboardEvent) => {
      if (event instanceof KeyboardEvent ? event.key === "Escape" : !ref.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", close);
    };
  }, [open]);
  return (
    <span className="info" ref={ref} onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
      <button type="button" aria-label={label} aria-describedby={open ? id : undefined} aria-expanded={open}
        onClick={(event) => { event.stopPropagation(); setOpen((value) => !value); }}
        onFocus={() => setOpen(true)} onBlur={() => setOpen(false)}>
        <InfoIcon size={14} aria-hidden="true" />
      </button>
      {open && <span role="tooltip" id={id} className="info-pop">{children}</span>}
    </span>
  );
}

type CalloutKind = "info" | "warn" | "error" | "success" | "note";
const CALLOUT_ICONS = { info: InfoIcon, warn: AlertTriangle, error: OctagonX, success: CheckCircle2, note: CircleAlert };

export function Callout({ kind = "note", title, children }: { kind?: CalloutKind; title?: ReactNode; children?: ReactNode }) {
  const Icon = CALLOUT_ICONS[kind];
  return (
    <div className="callout" data-kind={kind} role={kind === "error" ? "alert" : undefined}>
      <Icon size={16} aria-hidden="true" />
      <div>
        {title && <b>{title}</b>}
        {children && <div>{children}</div>}
      </div>
    </div>
  );
}

/** Native details/summary keeps disclosure accessible and keyboard-friendly. */
export function Disclosure({ title, hint, children, defaultOpen = false, onToggle }: {
  title: ReactNode; hint?: ReactNode; children: ReactNode; defaultOpen?: boolean; onToggle?: (open: boolean) => void;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <details className="disclosure" open={open} onToggle={(event) => {
      const next = (event.currentTarget as HTMLDetailsElement).open;
      setOpen(next);
      onToggle?.(next);
    }}>
      <summary>
        <span>{title}</span>
        {hint && <small>{hint}</small>}
        <ChevronDown className="chev" size={18} aria-hidden="true" />
      </summary>
      {/* Children mount only when opened, so heavy details load on demand. */}
      {open && <div className="disclosure-body">{children}</div>}
    </details>
  );
}

export function Stat({ label, value, note, info, small }: { label: ReactNode; value: ReactNode; note?: ReactNode; info?: ReactNode; small?: boolean }) {
  return (
    <div className="stat">
      <span className="stat-label">{label}{info && <Info>{info}</Info>}</span>
      <span className={"stat-value" + (small ? " is-small" : "")}>{value}</span>
      {note && <span className="stat-note">{note}</span>}
    </div>
  );
}

export function KV({ items }: { items: [ReactNode, ReactNode][] }) {
  return (
    <dl className="kv">
      {items.map(([key, value], index) => (
        <div key={index} style={{ display: "contents" }}>
          <dt>{key}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function JsonView({ value, label }: { value: unknown; label?: string }) {
  return <pre className="json" aria-label={label ?? "Raw JSON"} tabIndex={0}>{JSON.stringify(value, null, 2)}</pre>;
}

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="loading-line" role="status">
      <LoaderCircle size={16} className="spin" aria-hidden="true" /> {label}
    </div>
  );
}

/** Long-running requests show elapsed time so a slow trained scoring pass doesn't look stuck. */
export function SlowLoading({ label, detail, onCancel }: { label: string; detail?: ReactNode; onCancel?: () => void }) {
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    const started = Date.now();
    const timer = window.setInterval(() => setSeconds(Math.floor((Date.now() - started) / 1000)), 1000);
    return () => window.clearInterval(timer);
  }, []);
  return (
    <div className="panel" role="status" aria-live="polite">
      <div className="row-between">
        <Loading label={`${label} ${seconds > 0 ? `(${seconds}s)` : ""}`} />
        {onCancel && <button className="btn btn-sm" type="button" onClick={onCancel}>Cancel</button>}
      </div>
      {detail && seconds >= 3 && <p className="small muted" style={{ marginTop: 8 }}>{detail}</p>}
    </div>
  );
}

export function Skeleton({ height = 16, width = "100%" }: { height?: number; width?: number | string }) {
  return <div className="skeleton" style={{ height, width }} aria-hidden="true" />;
}

export function ErrorBox({ error, what }: { error: unknown; what?: string }) {
  const message = error instanceof Error ? error.message : String(error);
  return (
    <Callout kind="error" title={what ? `Couldn't load ${what}` : "Something went wrong"}>
      {message}
    </Callout>
  );
}

export function Empty({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="empty">
      <h3>{title}</h3>
      {children && <p className="small">{children}</p>}
      {action}
    </div>
  );
}

export function Unavailable({ children = "Not available" }: { children?: ReactNode }) {
  return <span className="unavailable">{children}</span>;
}

export function Segmented<T extends string>({ value, options, onChange, label, name }: {
  value: T; options: { value: T; label: ReactNode }[]; onChange: (value: T) => void; label: string; name?: string;
}) {
  const fallback = useId();
  return (
    <div className="segmented" role="radiogroup" aria-label={label}>
      {options.map((option) => (
        <label key={option.value}>
          <input type="radio" name={name ?? fallback} value={option.value} checked={value === option.value}
            onChange={() => onChange(option.value)} />
          <span>{option.label}</span>
        </label>
      ))}
    </div>
  );
}

export function Tabs<T extends string>({ tabs, value, onChange, label }: {
  tabs: { id: T; label: ReactNode }[]; value: T; onChange: (id: T) => void; label: string;
}) {
  const refs = useRef<Record<string, HTMLButtonElement | null>>({});
  const move = (index: number) => {
    const next = tabs[(index + tabs.length) % tabs.length];
    onChange(next.id);
    refs.current[next.id]?.focus();
  };
  return (
    <div className="tabs" role="tablist" aria-label={label}>
      {tabs.map((tab, index) => (
        <button key={tab.id} ref={(node) => { refs.current[tab.id] = node; }} role="tab" type="button" className="tab"
          id={`tab-${tab.id}`} aria-controls={`panel-${tab.id}`} aria-selected={value === tab.id} tabIndex={value === tab.id ? 0 : -1}
          onClick={() => onChange(tab.id)}
          onKeyDown={(event) => {
            if (event.key === "ArrowRight") move(index + 1);
            if (event.key === "ArrowLeft") move(index - 1);
          }}>
          {tab.label}
        </button>
      ))}
    </div>
  );
}

export function SelectField({ label, value, onChange, options, hint, id }: {
  label: string; value: string; onChange: (value: string) => void;
  options: { value: string; label: string }[]; hint?: ReactNode; id?: string;
}) {
  const auto = useId();
  const fieldId = id ?? auto;
  return (
    <div className="field">
      <label htmlFor={fieldId}>{label}</label>
      <select id={fieldId} className="select" value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
      </select>
      {hint && <span className="field-hint">{hint}</span>}
    </div>
  );
}

export function RangeField({ label, value, onChange, min = 0, max = 1, step = 0.01, format, hint }: {
  label: string; value: number; onChange: (value: number) => void; min?: number; max?: number; step?: number;
  format?: (value: number) => string; hint?: ReactNode;
}) {
  const id = useId();
  return (
    <div className="range-field">
      <div className="row-between">
        <label htmlFor={id}><b>{label}</b></label>
        <output htmlFor={id}>{format ? format(value) : value}</output>
      </div>
      <input id={id} type="range" min={min} max={max} step={step} value={value} onChange={(event) => onChange(Number(event.target.value))} />
      {hint && <span className="field-hint">{hint}</span>}
    </div>
  );
}
