import { useMemo } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Search } from "lucide-react";
import { useCustomerIndex } from "../api/hooks";
import type { CustomerIndexEntry } from "../api/types";
import { DataTable } from "../components/DataTable";
import { Empty, ErrorBox, SelectField, SlowLoading, ToneBadge } from "../components/ui";
import { date, humanize, percentage, toNumber } from "../lib/format";
import { PERSONAS, QUALITY_ORDER, TRUST, trustLabel } from "../lib/labels";

export function trustTone(status: string | undefined) {
  return status === "TRUSTED" ? "supported" : status === "LIMITED" ? "info" : status === "CONFLICT" ? "conflict" : "stopped";
}

export function CustomersPage() {
  const customers = useCustomerIndex();
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const q = params.get("q") ?? "";
  const region = params.get("region") ?? "";
  const segment = params.get("segment") ?? "";
  const trust = params.get("trust") ?? "";

  const set = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value); else next.delete(key);
    // A region change can make the chosen segment impossible; reset it.
    if (key === "region") next.delete("segment");
    setParams(next, { replace: true });
  };

  const rows = customers.data ?? [];
  const regions = useMemo(() => [...new Set(rows.map((row) => row.region))].sort(), [rows]);
  const segments = useMemo(
    () => [...new Set(rows.filter((row) => !region || row.region === region).map((row) => row.segment))].sort(),
    [rows, region],
  );
  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return rows.filter((row) =>
      (!needle || row.customer_id.toLowerCase().includes(needle) || row.display_name.toLowerCase().includes(needle)) &&
      (!region || row.region === region) && (!segment || row.segment === segment) && (!trust || row.trust_status === trust));
  }, [rows, q, region, segment, trust]);
  const personas = PERSONAS.filter((persona) => rows.some((row) => row.customer_id === persona.id));

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="page-title">Customers</h1>
          <p className="lede">Open a customer to see which sustainable products are worth raising with them, why, and what to do next.</p>
        </div>
      </div>

      {customers.isPending && (
        <SlowLoading label="Loading customers…"
          detail="With trained models the API returns every synthetic customer's full snapshot, so the first load can take a few seconds." />
      )}
      {customers.isError && <ErrorBox error={customers.error} what="the customer list" />}

      {customers.data && (
        <>
          {personas.length > 0 && (
            <section className="section">
              <div className="section-head">
                <h2 className="section-title">Start with a walkthrough customer</h2>
                <p className="section-note">Each one shows a different outcome, including cases where the right answer is to hold back.</p>
              </div>
              <div className="persona-grid">
                {personas.map((persona) => {
                  const row = rows.find((item) => item.customer_id === persona.id)!;
                  return (
                    <Link key={persona.id} className="persona" to={`/customers/${encodeURIComponent(persona.id)}`}>
                      <b>{persona.title}</b>
                      <span>{persona.note}</span>
                      <span><code>{persona.id}</code> {row.display_name.startsWith("Synthetic") ? "" : row.display_name}</span>
                    </Link>
                  );
                })}
              </div>
            </section>
          )}

          <section className="section">
            <div className="section-head">
              <h2 className="section-title">All customers</h2>
              <p className="section-note">{rows.length.toLocaleString("en-GB")} synthetic customers</p>
            </div>
            <div className="filters" role="search">
              <div className="field is-wide">
                <label htmlFor="customer-search">Search</label>
                <div className="search-wrap">
                  <Search size={16} aria-hidden="true" />
                  <input id="customer-search" className="input input-search" type="search" placeholder="Customer ID or name"
                    value={q} onChange={(event) => set("q", event.target.value)} autoComplete="off" />
                </div>
              </div>
              <SelectField label="Region" value={region} onChange={(value) => set("region", value)}
                options={[{ value: "", label: "All regions" }, ...regions.map((value) => ({ value, label: value }))]} />
              <SelectField label="Segment" value={segment} onChange={(value) => set("segment", value)}
                options={[{ value: "", label: "All segments" }, ...segments.map((value) => ({ value, label: humanize(value) }))]} />
              <SelectField label="Data trust" value={trust} onChange={(value) => set("trust", value)}
                options={[{ value: "", label: "Any" }, ...QUALITY_ORDER.map((value) => ({ value, label: TRUST[value].label }))]} />
              {(q || region || segment || trust) && (
                <button type="button" className="btn btn-quiet" onClick={() => setParams({}, { replace: true })}>Clear filters</button>
              )}
            </div>
            <DataTable<CustomerIndexEntry>
              rows={filtered}
              rowKey={(row) => row.customer_id}
              caption="Customers"
              onRowClick={(row) => navigate(`/customers/${encodeURIComponent(row.customer_id)}`)}
              empty={<Empty title="No customers match">Try a different search, or clear the filters.</Empty>}
              columns={[
                { key: "id", header: "Customer", sort: (row) => row.customer_id, render: (row) => (
                  <Link to={`/customers/${encodeURIComponent(row.customer_id)}`} onClick={(event) => event.stopPropagation()}>
                    <b>{row.customer_id}</b>
                  </Link>
                ) },
                { key: "name", header: "Name", sort: (row) => row.display_name, render: (row) => row.display_name },
                { key: "region", header: "Region", sort: (row) => row.region, render: (row) => row.region },
                { key: "segment", header: "Segment", sort: (row) => row.segment, render: (row) => humanize(row.segment) },
                { key: "trust", header: "Data trust", info: "How complete, current and consistent this customer's evidence is. Separate from model confidence.",
                  sort: (row) => toNumber(row.trust_score), render: (row) => (
                    <span className="row" style={{ gap: 8 }}>
                      <ToneBadge tone={trustTone(row.trust_status)}>{trustLabel(row.trust_status)}</ToneBadge>
                      <span className="num muted">{percentage(row.trust_score, 0)}</span>
                    </span>
                  ) },
                { key: "cutoff", header: "Data as of", sort: (row) => row.feature_cutoff, render: (row) => date(row.feature_cutoff) },
              ]}
            />
          </section>
        </>
      )}
    </div>
  );
}
