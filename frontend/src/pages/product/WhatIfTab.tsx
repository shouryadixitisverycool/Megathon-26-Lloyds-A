import { useMemo, useState, type FormEvent } from "react";
import { ExternalLink } from "lucide-react";
import { customerPath } from "../../api/client";
import { useSimulationTemplate } from "../../api/hooks";
import type {
  CounterfactualResult, CustomerSnapshot, Impact, Product, Recommendation, SensitivityResult, SimulationResult, UkImpact,
} from "../../api/types";
import { useSubmit } from "../../api/useSubmit";
import { DataTable } from "../../components/DataTable";
import { Callout, Disclosure, KV, Loading, RangeField, Stat } from "../../components/ui";
import { decimal, humanize, percentage, prettyUnit, toNumber } from "../../lib/format";
import { SENSITIVITY_FIELDS } from "../../lib/labels";
import { ImpactDetails } from "./ImpactDetails";

export function WhatIfTab({ row, snapshot }: { row: Recommendation; snapshot: CustomerSnapshot }) {
  const template = useSimulationTemplate(row.customer_id, row.product);
  const trained = snapshot.source_snapshot !== null;
  return (
    <div className="stack" style={{ gap: 32 }}>
      <Callout kind="note" title="Scenarios don't change the customer's record">
        Assumptions here change the physical estimate only. They don't update the customer's data, the model's likelihood, or eligibility.
        Each run is saved to the local audit trail.
      </Callout>

      <section className="stack-sm">
        <h3 className="subhead">Carbon scenario</h3>
        {template.isPending && <Loading label="Loading the customer's baseline…" />}
        {template.isError && <Callout kind="info" title="No scenario inputs for this product">{(template.error as Error).message}</Callout>}
        {template.data?.profile === "uk" && <UkScenario row={row} observed={template.data.inputs ?? {}} limitation={template.data.limitation} />}
        {template.data?.profile === "fixture" && (template.data.inputs
          ? <FixtureScenario row={row} original={template.data.inputs} limitation={template.data.limitation} />
          : <Callout kind="info" title={template.data.limitation || "No complete input evidence is available for this scenario."} />)}
      </section>

      <section className="stack-sm">
        <h3 className="subhead">How would the model respond?</h3>
        <p className="small muted">
          Change one input and see how the model's likelihood moves. This shows model behaviour, not advice: mileage and energy use are
          context, not actions to recommend. Paper statement choice is the one directly actionable input.
        </p>
        {trained ? (
          <>
            <Sensitivity row={row} snapshot={snapshot} />
            <Disclosure title="Search several values at once" hint="Bounded scenario search">
              <CounterfactualSearch row={row} snapshot={snapshot} />
            </Disclosure>
          </>
        ) : (
          <Callout kind="info" title="Needs the trained models">
            These demo personas use fixed synthetic probabilities, so there's no model to probe. Start the API with
            <code> GREENR_PROVIDER=trained</code> to use sensitivity analysis.
          </Callout>
        )}
      </section>
    </div>
  );
}

/* ---------------------------------------------------- India fixture profile */

function FixtureScenario({ row, original, limitation }: { row: Recommendation; original: Record<string, any>; limitation: string }) {
  const product = row.product;
  const path = customerPath(row.customer_id, "/simulate");
  const save = useSubmit<SimulationResult>(path, [["customer", row.customer_id, "history"]], "Scenario calculated and saved");
  const baselineImport = product === "SOLAR_FINANCE"
    ? (original.intervals ?? []).reduce((sum: number, item: any) => sum + Number(item.baseline_grid_import.value), 0) : 0;
  const currentSolar = product === "SOLAR_FINANCE"
    ? (original.intervals ?? []).reduce((sum: number, item: any) => sum + Number(item.self_consumed_solar.value), 0) : 0;
  const [edits, setEdits] = useState<Record<string, number>>(() => ({
    scenario_distance: Number(original.scenario_distance?.value ?? 0),
    charging_electricity: Number(original.charging_electricity?.value ?? 0),
    scenario_grid_import: Number(original.scenario_grid_import?.value ?? 0),
    solar_share: baselineImport ? Math.min(currentSolar / baselineImport, 1) : 0,
  }));

  if (product === "PAPERLESS_BANKING") {
    return <Callout kind="info" title="Paperless is reported as an action, not a carbon saving">A carbon scenario needs verified paper and digital lifecycle factors, which aren't available.</Callout>;
  }

  const run = (event: FormEvent) => {
    event.preventDefault();
    const inputs = structuredClone(original);
    const changed: any[] = [];
    if (product === "SOLAR_FINANCE") {
      for (const interval of inputs.intervals) {
        interval.self_consumed_solar.value = String(Number(interval.baseline_grid_import.value) * edits.solar_share);
        changed.push(interval.self_consumed_solar);
      }
    } else {
      const fields = product === "EV_FINANCE" ? ["scenario_distance", "charging_electricity"] : ["scenario_grid_import"];
      for (const field of fields) {
        inputs[field].value = String(edits[field]);
        changed.push(inputs[field]);
      }
    }
    for (const fact of changed) Object.assign(fact.evidence, { basis: "engineering_forecast", reference: "user-scenario-assumption", freshness: "current", conflicts: [] });
    save.submit({ product, inputs });
  };

  const number = (key: string, label: string) => (
    <div className="field">
      <label htmlFor={`fx-${key}`}>{label}</label>
      <input id={`fx-${key}`} className="input" type="number" min={0} step={100} value={edits[key]}
        onChange={(event) => setEdits({ ...edits, [key]: Number(event.target.value) })} />
    </div>
  );

  return (
    <form onSubmit={run} className="stack-sm">
      <p className="small muted">{limitation}</p>
      <div className="form-grid">
        {product === "EV_FINANCE" && <>{number("scenario_distance", "Annual distance in the EV, km")}{number("charging_electricity", "Annual charging electricity, kWh")}</>}
        {product === "GREEN_HOME" && number("scenario_grid_import", "Annual electricity imported after the upgrade, kWh")}
        {product === "SOLAR_FINANCE" && (
          <RangeField label="Share of grid electricity replaced by self-used solar" value={edits.solar_share}
            onChange={(value) => setEdits({ ...edits, solar_share: value })} format={(value) => `${Math.round(value * 100)}%`} />
        )}
      </div>
      <div className="form-actions">
        <button className="btn btn-primary" type="submit" disabled={save.isPending}>{save.isPending ? "Calculating…" : "Calculate scenario"}</button>
      </div>
      {save.isError && <Callout kind="error" title="Scenario not calculated">{(save.error as Error).message}</Callout>}
      {save.data && (
        <div className="panel" style={{ marginTop: 8 }}>
          <h4 className="panel-title">Scenario result</h4>
          <p className="panel-sub">{save.data.limitation as string}</p>
          <ImpactDetails impact={save.data.impact as Impact} compact />
        </div>
      )}
    </form>
  );
}

/* ---------------------------------------------------------- UK profile */

interface UkField { key: string; label: string; max: number; from?: string; integer?: boolean; percent?: boolean; text?: boolean }

const UK_FIELDS: Record<string, UkField[]> = {
  EV_FINANCE: [
    { key: "annual_mileage_km", label: "Annual distance, km", max: 200000, from: "annual_mileage_km" },
    { key: "ice_litres_per_100km", label: "Current car's fuel use, litres per 100 km", max: 50 },
    { key: "ev_kwh_per_100km", label: "Proposed EV's energy use, kWh per 100 km", max: 100 },
    { key: "charging_efficiency", label: "Charging efficiency, %", max: 1, percent: true },
  ],
  SOLAR_FINANCE: [
    { key: "annual_electricity_kwh", label: "Annual electricity demand, kWh", max: 200000, from: "annual_electricity_kwh" },
    { key: "annual_generation_kwh", label: "Proposed annual solar generation, kWh", max: 200000 },
    { key: "proposed_capacity_kw", label: "Proposed array size, kW", max: 1000 },
    { key: "self_consumption_fraction", label: "Generation used at home, %", max: 1, percent: true },
    { key: "region", label: "Property region", max: 0, from: "region", text: true },
    { key: "generation_evidence", label: "Where the generation forecast comes from", max: 0, text: true },
  ],
  INSULATION: [
    { key: "annual_electricity_kwh", label: "Annual electricity demand, kWh", max: 200000, from: "annual_electricity_kwh" },
    { key: "annual_gas_kwh_gross", label: "Annual gas demand, gross kWh", max: 500000, from: "annual_gas_kwh" },
    { key: "electricity_saving_fraction", label: "Expected electricity saving, %", max: 1, percent: true },
    { key: "gas_saving_fraction", label: "Expected gas saving, %", max: 1, percent: true },
    { key: "savings_evidence", label: "Where the savings estimate comes from", max: 0, text: true },
  ],
  HEAT_PUMP: [
    { key: "annual_heating_gas_kwh_gross", label: "Annual gas used for heating only, gross kWh", max: 500000 },
    { key: "boiler_efficiency_gross", label: "Current boiler efficiency, %", max: 1, percent: true },
    { key: "seasonal_performance_factor", label: "Proposed heat pump seasonal performance factor", max: 10 },
    { key: "performance_evidence", label: "Where the performance estimate comes from", max: 0, text: true },
  ],
  PAPERLESS_BANKING: [
    { key: "annual_statements", label: "Paper statements per year", max: 10000, from: "paper_statements_12m", integer: true },
    { key: "sheets_per_statement", label: "Sheets per statement", max: 100, integer: true },
    { key: "avoided_fraction", label: "Statements avoided, %", max: 1, percent: true },
  ],
};

function UkScenario({ row, observed, limitation }: { row: Recommendation; observed: Record<string, any>; limitation: string }) {
  const product = row.product;
  const [intervention, setIntervention] = useState<"INSULATION" | "HEAT_PUMP">("INSULATION");
  const fields = UK_FIELDS[product === "GREEN_HOME" ? intervention : product] ?? [];
  const initial = () => Object.fromEntries(fields.map((field) => {
    const source = field.from ? observed[field.from] : undefined;
    if (source === undefined || source === null) return [field.key, ""];
    if (field.text) return [field.key, String(source)];
    return [field.key, String(field.integer ? Math.round(Number(source)) : Number(Number(source).toFixed(2)))];
  }));
  const [values, setValues] = useState<Record<string, string>>(initial);
  const [fuel, setFuel] = useState<string>(observed.fuel_type === "PETROL" || observed.fuel_type === "DIESEL" ? observed.fuel_type : "");
  const [touched, setTouched] = useState(false);
  const save = useSubmit<SimulationResult>(customerPath(row.customer_id, "/simulate"), [["customer", row.customer_id, "history"]], "UK scenario calculated and saved");

  const switchIntervention = (next: "INSULATION" | "HEAT_PUMP") => {
    setIntervention(next);
    const nextFields = UK_FIELDS[next];
    setValues(Object.fromEntries(nextFields.map((field) => {
      const source = field.from ? observed[field.from] : undefined;
      return [field.key, source === undefined || source === null ? "" : String(Number(Number(source).toFixed(2)))];
    })));
    setTouched(false);
  };

  const missing = fields.filter((field) => !values[field.key]?.trim()).map((field) => field.key);
  if (product === "EV_FINANCE" && !fuel) missing.push("fuel_type");

  const run = (event: FormEvent) => {
    event.preventDefault();
    setTouched(true);
    if (missing.length) return;
    const inputs: Record<string, unknown> = { geography: "UK" };
    for (const field of fields) {
      const raw = values[field.key].trim();
      inputs[field.key] = field.text ? raw : field.percent ? Number(raw) / 100 : field.integer ? Math.round(Number(raw)) : Number(raw);
    }
    if (product === "EV_FINANCE") Object.assign(inputs, { fuel_type: fuel, mileage_evidence: "USER_SCENARIO" });
    if (product === "GREEN_HOME") inputs.intervention = intervention;
    save.submit({ product, inputs });
  };

  return (
    <form onSubmit={run} className="stack-sm" noValidate>
      <p className="small muted">{limitation} Observed values are pre-filled and can be edited. Blank fields stay blank; nothing is assumed for you.</p>
      {product === "GREEN_HOME" && (
        <div className="field" style={{ maxWidth: 320 }}>
          <label htmlFor="uk-intervention">Proposed home upgrade</label>
          <select id="uk-intervention" className="select" value={intervention} onChange={(event) => switchIntervention(event.target.value as "INSULATION" | "HEAT_PUMP")}>
            <option value="INSULATION">Insulation</option>
            <option value="HEAT_PUMP">Heat pump</option>
          </select>
        </div>
      )}
      <div className="form-grid">
        {product === "EV_FINANCE" && (
          <div className="field">
            <label htmlFor="uk-fuel">Current fuel</label>
            <select id="uk-fuel" className="select" value={fuel} onChange={(event) => setFuel(event.target.value)} aria-invalid={touched && !fuel}>
              <option value="">Choose…</option>
              <option value="PETROL">Petrol</option>
              <option value="DIESEL">Diesel</option>
            </select>
          </div>
        )}
        {fields.map((field) => {
          const invalid = touched && missing.includes(field.key);
          return (
            <div className="field" key={field.key} style={field.text && field.key.endsWith("evidence") ? { gridColumn: "1 / -1" } : undefined}>
              <label htmlFor={`uk-${field.key}`}>{field.label}</label>
              <input id={`uk-${field.key}`} className="input" aria-invalid={invalid}
                type={field.text ? "text" : "number"} min={0} max={field.text ? undefined : field.percent ? 100 : field.max}
                step={field.integer ? 1 : field.percent ? 1 : 0.01} maxLength={field.text ? 1000 : undefined}
                value={values[field.key] ?? ""} onChange={(event) => setValues({ ...values, [field.key]: event.target.value })} />
              {field.from && <span className="field-hint">Pre-filled from the customer's record</span>}
              {invalid && <span className="field-hint" style={{ color: "var(--error-ink)" }}>Required</span>}
            </div>
          );
        })}
      </div>
      {touched && missing.length > 0 && <Callout kind="warn" title="Fill in every input, including where the estimate comes from, before calculating." />}
      <div className="form-actions">
        <button className="btn btn-primary" type="submit" disabled={save.isPending}>{save.isPending ? "Calculating…" : "Calculate UK scenario"}</button>
      </div>
      {save.isError && <Callout kind="error" title="Scenario not calculated">{(save.error as Error).message}</Callout>}
      {save.data && <UkResult impact={save.data.impact as UkImpact} />}
    </form>
  );
}

function UkResult({ impact }: { impact: UkImpact }) {
  if (impact.status === "UNAVAILABLE") {
    return (
      <Callout kind="warn" title="No defensible estimate for these inputs">
        <ul>{(impact.issues ?? []).map((issue, index) => <li key={index}>{String(issue)}</li>)}</ul>
      </Callout>
    );
  }
  if (impact.status === "NOT_CLAIMED") {
    return (
      <div className="panel">
        <div className="stats">
          <Stat label="Paper statements avoided" value={decimal(impact.paper_statements_avoided, 1)} />
          <Stat label="Paper sheets avoided" value={decimal(impact.paper_sheets_avoided, 1)} />
        </div>
        <p className="small muted" style={{ marginTop: 10 }}>{impact.limitation}</p>
      </div>
    );
  }
  const unit = prettyUnit(impact.units);
  const records = Object.entries(impact.factor_records ?? {});
  return (
    <div className="panel stack-sm">
      <div className="stats">
        <Stat label="Today (baseline)" value={decimal(impact.baseline_emissions, 1)} note={unit} />
        <Stat label="With the change" value={decimal(impact.scenario_emissions, 1)} note={unit} />
        <Stat label="Potential reduction" value={decimal(impact.potential_reduction, 1)} note={`${unit}, modelled`} />
      </div>
      <p className="small">{impact.boundary}</p>
      {(impact.limitations ?? []).length > 0 && <ul className="xsmall muted">{impact.limitations!.map((item) => <li key={item}>{item}</li>)}</ul>}
      <Disclosure title="Impact passport and factor sources" hint={impact.passport_id}>
        <KV items={[
          ["Passport", <code key="p">{impact.passport_id}</code>],
          ["Method", <code key="m">{impact.method_version}</code>],
          ["Factor vintage", impact.factor_vintage ?? "Not available"],
          ["Formula", impact.formula ?? "Not available"],
          ["Source SHA-256", <code key="s" className="xsmall">{impact.factor_source_sha256}</code>],
        ]} />
        {records.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <DataTable rows={records} rowKey={([key]) => key} caption="Emission factors used"
              columns={[
                { key: "factor", header: "Factor", render: ([key]) => humanize(key) },
                { key: "value", header: "Value", numeric: true, render: ([, record]) => `${record.value} ${prettyUnit(String(record.units))}` },
                { key: "scope", header: "Scope", render: ([, record]) => String(record.scope ?? "") },
                { key: "activity", header: "Activity", render: ([, record]) => String(record.activity ?? "") },
                { key: "row", header: "Source row", numeric: true, render: ([, record]) => String(record.source_row ?? "") },
              ]} />
          </div>
        )}
        {impact.factor_source && (
          <a className="btn btn-sm" style={{ marginTop: 12 }} href={impact.factor_source} target="_blank" rel="noreferrer noopener">
            Official factor source <ExternalLink size={12} aria-hidden="true" />
          </a>
        )}
      </Disclosure>
    </div>
  );
}

/* ------------------------------------------------------ model sensitivity */

function currentFeature(snapshot: CustomerSnapshot, field: string): number | null {
  return toNumber(snapshot.source_snapshot?.features?.[field] as number | undefined);
}

function Sensitivity({ row, snapshot }: { row: Recommendation; snapshot: CustomerSnapshot }) {
  const options = SENSITIVITY_FIELDS[row.product as Product];
  const [field, setField] = useState(options[0].field);
  const meta = options.find((item) => item.field === field)!;
  const current = currentFeature(snapshot, field);
  const [value, setValue] = useState<string>(current === null ? "" : String(Math.round(current * 100) / 100));
  const save = useSubmit<SensitivityResult>(customerPath(row.customer_id, "/sensitivity"), [["customer", row.customer_id, "history"]], "Sensitivity check saved");
  const result = save.data;
  const delta = result && result.baseline_probability !== null && result.scenario_probability !== null
    ? (result.scenario_probability - result.baseline_probability) * 100 : null;

  return (
    <form className="panel stack-sm" onSubmit={(event) => {
      event.preventDefault();
      if (value.trim() === "") return;
      save.submit({ product: row.product, changes: { [field]: Number(value) } });
    }}>
      <div className="form-grid">
        <div className="field">
          <label htmlFor="sens-field">Input to change</label>
          <select id="sens-field" className="select" value={field} onChange={(event) => {
            setField(event.target.value);
            const next = currentFeature(snapshot, event.target.value);
            setValue(next === null ? "" : String(Math.round(next * 100) / 100));
          }}>
            {options.map((item) => <option key={item.field} value={item.field}>{item.label}</option>)}
          </select>
          <span className="field-hint">{meta.kind === "actionable" ? "Actionable: the customer controls this." : "Context only: not something to recommend changing."}</span>
        </div>
        <div className="field">
          <label htmlFor="sens-value">New value</label>
          <input id="sens-value" className="input" type="number" min={0} max={meta.max} step="any" value={value} onChange={(event) => setValue(event.target.value)} />
          <span className="field-hint">Currently {current === null ? "unknown" : decimal(current, 2)}. Allowed 0 to {meta.max.toLocaleString("en-GB")}.</span>
        </div>
      </div>
      <div className="form-actions">
        <button className="btn btn-primary" type="submit" disabled={save.isPending || value.trim() === ""}>{save.isPending ? "Checking…" : "Check the model's response"}</button>
      </div>
      {save.isError && <Callout kind="error" title="Couldn't run the check">{(save.error as Error).message}</Callout>}
      {result && (
        <>
          <div className="stats">
            <Stat label="Likelihood now" value={percentage(result.baseline_probability)} />
            <Stat label="With the new value" value={percentage(result.scenario_probability)} />
            <Stat label="Change" value={delta === null ? "Not available" : `${delta >= 0 ? "+" : ""}${delta.toFixed(1)} pts`} />
          </div>
          <p className="xsmall muted">{result.limitation}</p>
        </>
      )}
    </form>
  );
}

function CounterfactualSearch({ row, snapshot }: { row: Recommendation; snapshot: CustomerSnapshot }) {
  const options = SENSITIVITY_FIELDS[row.product as Product];
  const [lists, setLists] = useState<Record<string, string>>(() => Object.fromEntries(options.map((item, index) => [item.field, index === 0 ? "0" : ""])));
  // Default to this product's cut-off: the question is usually "what would cross it?"
  const cutoff = toNumber(row.propensity?.decision_threshold);
  const [target, setTarget] = useState(cutoff !== null ? Math.round(cutoff * 100) / 100 : 0.6);
  const save = useSubmit<CounterfactualResult>(customerPath(row.customer_id, "/counterfactual-search"), [], "Scenario search finished");

  const parsed = useMemo(() => {
    const candidates: Record<string, number[]> = {};
    const errors: string[] = [];
    for (const item of options) {
      const text = lists[item.field]?.trim();
      if (!text) continue;
      const values = text.split(/[,\s]+/).filter(Boolean).map(Number);
      if (values.some((value) => !Number.isFinite(value) || value < 0 || value > item.max)) errors.push(`${item.label}: use numbers from 0 to ${item.max.toLocaleString("en-GB")}.`);
      else if (values.length > 16) errors.push(`${item.label}: try at most 16 values.`);
      else candidates[item.field] = values;
    }
    if (!Object.keys(candidates).length && !errors.length) errors.push("Enter at least one value to try.");
    return { candidates, errors };
  }, [lists, options]);

  const combos = Object.values(parsed.candidates).reduce((product, values) => product * values.length, 1);
  const result = save.data;

  return (
    <form className="stack-sm" onSubmit={(event) => {
      event.preventDefault();
      if (parsed.errors.length) return;
      save.submit({ product: row.product, candidates: parsed.candidates, target_probability: target, max_evaluations: 64 });
    }}>
      <p className="small muted">List values to try for one or more inputs, separated by commas. Every combination is scored by the trained model (up to 64). Protected attributes are never searched.</p>
      <div className="form-grid">
        {options.map((item) => {
          const current = currentFeature(snapshot, item.field);
          return (
            <div className="field" key={item.field}>
              <label htmlFor={`cf-${item.field}`}>{item.label}</label>
              <input id={`cf-${item.field}`} className="input" placeholder="e.g. 5000, 10000, 20000" value={lists[item.field] ?? ""}
                onChange={(event) => setLists({ ...lists, [item.field]: event.target.value })} />
              <span className="field-hint">Currently {current === null ? "unknown" : decimal(current, 2)}</span>
            </div>
          );
        })}
      </div>
      <RangeField label="Target likelihood" value={target} onChange={setTarget} format={(value) => `${Math.round(value * 100)}%`}
        hint={cutoff !== null ? `Starts at this product's ${percentage(cutoff)} cut-off.` : undefined} />
      {parsed.errors.length > 0 && parsed.errors[0] !== "Enter at least one value to try." && <Callout kind="warn" title={parsed.errors.join(" ")} />}
      <div className="form-actions">
        <button className="btn btn-primary" type="submit" disabled={save.isPending || parsed.errors.length > 0}>
          {save.isPending ? "Searching…" : `Search ${combos > 64 ? "64 of " : ""}${combos.toLocaleString("en-GB")} combination${combos === 1 ? "" : "s"}`}
        </button>
      </div>
      {save.isError && <Callout kind="error" title="Search failed">{(save.error as Error).message}</Callout>}
      {result && (
        <div className="stack-sm">
          {result.truncated && <Callout kind="warn" title="Partial search">There were more combinations than the 64-evaluation budget, so only some were scored.</Callout>}
          <p className="small">Likelihood now: <b>{percentage(result.baseline_probability)}</b>. {result.results.some((item) => item.target_met) ? "Some combinations reach the target." : "No combination reaches the target."}</p>
          <DataTable rows={result.results} rowKey={(_, index) => String(index)} caption="Scenario search results"
            columns={[
              { key: "changes", header: "Values tried", render: (item) => Object.entries(item.changes).map(([key, value]) => `${options.find((option) => option.field === key)?.label ?? key}: ${decimal(value, 2)}`).join("; ") },
              { key: "p", header: "Likelihood", numeric: true, sort: (item) => item.probability, render: (item) => percentage(item.probability) },
              { key: "d", header: "Distance from today", numeric: true, sort: (item) => item.normalised_distance, render: (item) => item.normalised_distance.toFixed(3) },
              { key: "t", header: "Meets target", render: (item) => item.target_met ? "Yes" : "No" },
            ]} />
          <p className="xsmall muted">{result.limitation}</p>
        </div>
      )}
    </form>
  );
}
