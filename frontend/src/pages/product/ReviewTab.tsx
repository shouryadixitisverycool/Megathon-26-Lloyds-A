import { useLayoutEffect, useRef, useState } from "react";
import { useEvidenceGraph } from "../../api/hooks";
import type { CustomerSnapshot, EvidenceGraph, Recommendation } from "../../api/types";
import { useSubmit } from "../../api/useSubmit";
import { Callout, ErrorBox, Loading } from "../../components/ui";
import { humanize } from "../../lib/format";
import { featureLabel, REVIEW_ACTIONS, stateLabel } from "../../lib/labels";

export function ReviewTab({ row, snapshot }: { row: Recommendation; snapshot: CustomerSnapshot }) {
  return (
    <div className="stack" style={{ gap: 32 }}>
      <ReviewForm row={row} />
      <section className="stack-sm">
        <h3 className="subhead">How the evidence connects</h3>
        <p className="small muted">Customer facts feed the rule reasons, which produce the decision. The carbon estimate is calculated separately. Hover or focus a box to trace it.</p>
        <Graph row={row} snapshot={snapshot} />
      </section>
    </div>
  );
}

function ReviewForm({ row }: { row: Recommendation }) {
  const [action, setAction] = useState("ACCEPT");
  const [reviewer, setReviewer] = useState("");
  const [note, setNote] = useState("");
  const [touched, setTouched] = useState(false);
  const save = useSubmit("/review", [["customer", row.customer_id]], "Review recorded");
  const missing = !reviewer.trim() || !note.trim();

  return (
    <section className="stack-sm">
      <h3 className="subhead">Record a human review</h3>
      <p className="small muted">Reviews control outreach only. Scores, confidence, eligibility and impact stay as calculated.</p>
      <form className="panel stack-sm" noValidate onSubmit={(event) => {
        event.preventDefault();
        setTouched(true);
        if (missing) return;
        save.submit({ customer_id: row.customer_id, product: row.product, action, reviewer: reviewer.trim(), note: note.trim() });
      }}>
        <fieldset style={{ border: 0, padding: 0, margin: 0 }}>
          <legend className="field-label" style={{ marginBottom: 8 }}>Your decision</legend>
          <div className="choice-grid">
            {REVIEW_ACTIONS.map((item) => (
              <label key={item.value} className="choice">
                <input type="radio" name="review-action" value={item.value} checked={action === item.value} onChange={() => setAction(item.value)} />
                <span><b>{item.label}</b><small>{item.help}</small></span>
              </label>
            ))}
          </div>
        </fieldset>
        <div className="form-grid">
          <div className="field">
            <label htmlFor="reviewer">Your name</label>
            <input id="reviewer" className="input" maxLength={100} value={reviewer} aria-invalid={touched && !reviewer.trim()}
              onChange={(event) => setReviewer(event.target.value)} autoComplete="name" />
          </div>
        </div>
        <div className="field">
          <label htmlFor="review-note">Reason for this decision</label>
          <textarea id="review-note" className="textarea" maxLength={2000} value={note} aria-invalid={touched && !note.trim()}
            onChange={(event) => setNote(event.target.value)} placeholder="What did you check, and what did you find?" />
        </div>
        {touched && missing && <Callout kind="warn" title="Add your name and a reason before recording the review." />}
        <div className="form-actions">
          <button className="btn btn-primary" type="submit" disabled={save.isPending}>{save.isPending ? "Recording…" : "Record review"}</button>
        </div>
        {save.isError && <Callout kind="error" title="Review not recorded">{(save.error as Error).message}</Callout>}
      </form>
    </section>
  );
}

function nodeTitle(node: EvidenceGraph["nodes"][number], snapshot: CustomerSnapshot) {
  if (node.type === "decision") return { title: stateLabel(node.label), sub: "Decision" };
  if (node.type === "impact") return { title: node.label === "AVAILABLE" ? "Estimate available" : "No estimate", sub: node.method_version };
  if (node.type === "feature") {
    const value = snapshot.features[node.label]?.value;
    return { title: featureLabel(node.label), sub: value === undefined || value === null ? "Unknown" : value ? "Yes" : "No" };
  }
  return { title: humanize(node.label), sub: node.detail?.message };
}

function Graph({ row, snapshot }: { row: Recommendation; snapshot: CustomerSnapshot }) {
  const graph = useEvidenceGraph(row.customer_id, row.product);
  const box = useRef<HTMLDivElement>(null);
  const nodes = useRef<Record<string, HTMLDivElement | null>>({});
  const [paths, setPaths] = useState<{ from: string; to: string; d: string }[]>([]);
  const [active, setActive] = useState<string | null>(null);

  useLayoutEffect(() => {
    const measure = () => {
      if (!box.current || !graph.data) return;
      const origin = box.current.getBoundingClientRect();
      setPaths(graph.data.edges.flatMap((edge) => {
        const a = nodes.current[edge.from]?.getBoundingClientRect();
        const b = nodes.current[edge.to]?.getBoundingClientRect();
        if (!a || !b) return [];
        const x1 = a.right - origin.left, y1 = a.top + a.height / 2 - origin.top;
        const x2 = b.left - origin.left, y2 = b.top + b.height / 2 - origin.top;
        const mid = (x1 + x2) / 2;
        return [{ from: edge.from, to: edge.to, d: `M${x1},${y1} C${mid},${y1} ${mid},${y2} ${x2},${y2}` }];
      }));
    };
    measure();
    const observer = new ResizeObserver(measure);
    if (box.current) observer.observe(box.current);
    return () => observer.disconnect();
  }, [graph.data]);

  if (graph.isPending) return <Loading />;
  if (graph.isError) return <ErrorBox error={graph.error} what="the evidence graph" />;
  const data = graph.data!;
  const linked = new Set<string>();
  if (active) {
    linked.add(active);
    // Walk both directions so a fact lights its reason, decision and impact.
    let frontier = [active];
    for (let i = 0; i < 3; i++) {
      frontier = frontier.flatMap((id) => data.edges.filter((edge) => edge.from === id).map((edge) => edge.to));
      frontier.forEach((id) => linked.add(id));
    }
    frontier = [active];
    for (let i = 0; i < 3; i++) {
      frontier = frontier.flatMap((id) => data.edges.filter((edge) => edge.to === id).map((edge) => edge.from));
      frontier.forEach((id) => linked.add(id));
    }
  }
  const columns: [string, typeof data.nodes][] = [
    ["Customer facts", data.nodes.filter((node) => node.type === "feature")],
    ["Rule reasons", data.nodes.filter((node) => node.type === "reason")],
    ["Decision", data.nodes.filter((node) => node.type === "decision")],
    ["Carbon estimate", data.nodes.filter((node) => node.type === "impact")],
  ];

  return (
    <div className="panel">
      <div className="graph" ref={box} onMouseLeave={() => setActive(null)}>
        <svg className="graph-edges" aria-hidden="true">
          {paths.map((path) => (
            <path key={path.from + path.to} d={path.d} data-active={active ? String(linked.has(path.from) && linked.has(path.to)) : undefined} />
          ))}
        </svg>
        {columns.map(([title, list]) => (
          <div className="graph-col" key={title}>
            <h5>{title}</h5>
            {list.length === 0 && <span className="xsmall muted">None</span>}
            {list.map((node) => {
              const text = nodeTitle(node, snapshot);
              return (
                <div key={node.id} ref={(element) => { nodes.current[node.id] = element; }} className="graph-node" tabIndex={0}
                  data-active={active ? String(linked.has(node.id)) : undefined}
                  onMouseEnter={() => setActive(node.id)} onFocus={() => setActive(node.id)} onBlur={() => setActive(null)}>
                  <b>{text.title}</b>
                  {text.sub && <span className="muted">{text.sub}</span>}
                </div>
              );
            })}
          </div>
        ))}
      </div>
      <p className="xsmall muted" style={{ marginTop: 12 }}>{data.limitation}</p>
    </div>
  );
}
