# Greenr frontend

A React workspace for the Greenr API. It covers everything the Streamlit app does, in a layout built for the people who act on it: relationship managers, campaign planners and reviewers. Each page leads with the decision and the next step. Evidence, methods and raw records open only when you ask for them.

It talks to the existing FastAPI service over HTTP and never computes a decision, score or carbon figure itself.

## Run it

```bash
# 1. Start the API from the repository root (fixture or trained, see the root README)
make api                       # or: GREENR_PROVIDER=fixture make api

# 2. Start the frontend
cd frontend
npm install
npm run dev                    # http://127.0.0.1:5173
```

The dev server proxies `/api/*` to the API, because the API has no CORS policy. Point it somewhere else with `GREENR_API_URL`:

```bash
GREENR_API_URL=http://127.0.0.1:8001 npm run dev
```

| Script | What it does |
|---|---|
| `npm run dev` | Dev server with hot reload and the API proxy |
| `npm run build` | Typecheck, then a production build in `dist/` |
| `npm run preview` | Serve `dist/` on :4173 with the same proxy |
| `npm run typecheck` | TypeScript only |
| `npm test` | Vitest unit tests for formatting and chart rules |

If you host the build behind your own reverse proxy, set `VITE_API_BASE` at build time to the path that forwards to the API (default `/api`).

## Where everything from Streamlit went

| Streamlit | Here |
|---|---|
| Customer workspace: customer picker, persona captions, abstention shortcut | **Customers**: searchable, filterable directory with walkthrough cards for each demo persona |
| Data Trust metric, feature cutoff, trust issues | Customer header, plus one grouped callout for trust issues (extra issues expand on request) |
| Product cards: state, propensity, confidence, impact | Ranked opportunity list, with each product's likelihood shown against its cut-off |
| Why this result: explanation, evidence, reason codes, versions, exclusions | Product drawer, **Why** and **Audit trail** tabs |
| Impact method, factors and assumptions | **Impact** tab: headline figure, baseline vs scenario, then assumptions, exclusions, inputs, factors and method behind disclosures |
| Customer evidence and data quality, source snapshot JSON | **Customer data** section: approved facts, grouped source record, per-product trust, raw JSON |
| Contact preferences, record a response, history | **Contact & history** tab, with a timeline instead of a table |
| What-if lab (India fixture and UK scenarios), model sensitivity, counterfactual search | **What-if** tab. Search values are typed as plain lists, so no JSON is needed |
| Relationship Manager: channel, next-action table, human review, evidence graph, scored trace, audit lookup | Merged into the customer page: the planned contact channel drives each product's next step; **Review** tab holds the review form and an interactive evidence graph |
| Portfolio: filters, KPIs, physical potential, quality and missingness, state chart, region/segment charts, monthly trend and tables | **Portfolio**: every chart has a table view; physical totals stay grouped by product, unit and method |
| Planning: filters, opportunity table, propensity vs impact matrix, scenario and campaign forms | **Campaign planning**: filters apply on request, the table is sortable and paginated, and rows open the customer |
| Governance: model comparison, fairness, confidence reliability, robustness, all reports | **Governance**: release status at a glance, then per-product audit and readable report summaries with raw JSON on request |

Also added (all on demand): the trained-model SHAP attribution (`/customers/{id}/shap/{product}`), explanation-service counters (`/explanations/metrics`), the full stored audit record for each decision, and audit lookup from Governance.

Still API-only (not in Streamlit either): factual source updates and campaign closure. Both need the local admin token, which should stay server-side, so they need a backend route or session design before a browser can use them.

## AI-written explanations

The backend can have an LLM write each product's plain-language explanation (`src/greenr/llm/`). The model only chooses the order of pre-approved sentences, and every fact, number and disclaimer is checked. Anything that fails falls back to the standard template wording, which states the same facts.

It's off unless the API process has a key:

```bash
OPENAI_API_KEY=... make api    # or GREENR_LLM_API_KEY; model and settings come from llm/provider_manifest.json
```

That makes paid provider calls. Add `GREENR_LLM_INPUT_PRICE_PER_MILLION` and `GREENR_LLM_OUTPUT_PRICE_PER_MILLION` to have cost measured.

Where it appears in the UI:

- **Why tab:** a badge says who wrote the explanation: "Written by AI", "Standard wording" (AI off), or "Standard wording, AI draft not used". In the last case a note explains why (timeout, busy, error, wrong format, changed a fact, dropped a sentence). Timeouts, busy and error failures get an "Ask the AI again" button.
- **Sidebar:** shows whether explanations are AI-written or standard wording.
- **Governance:** an "AI-written explanations" section with on/off status, model, live call counts, latency, tokens and cost, how grounding works, and the offline evaluation results.

## Design notes

- **Verdict first.** Each customer gets a one-line briefing ("Two supported opportunities…" or "No supported opportunity right now"), and each product shows its next step for the planned channel. The briefing only restates the API's decisions.
- **Threshold rail.** Likelihood is a dot on a 0–100% line with the product's cut-off marked, so "supported" vs "not recommended" can be seen at a glance even when trained cut-offs are near 10%.
- **Unavailable is never zero.** Missing impact, confidence or priority is labelled as such, styled differently from numbers, and never filled in.
- **Honest colour.** Product and decision-state colours were checked for colour-blind separation. The "nothing to do" states stay neutral on purpose. Every chart has a legend and a table view.
- Type: Bricolage Grotesque for headings, Public Sans for UI and tables (self-hosted via Fontsource, so it works offline). Light and dark themes follow the system, with a manual toggle in the sidebar.

## Things to know

- **Trained mode is slow on some routes.** `/portfolio/opportunities`, `/portfolio/scenarios` and `/campaigns/optimise` re-score all 4,010 customers on every call (1–2+ minutes locally), and the first filtered `/portfolio/summary` per filter combination takes about as long before the API caches it. The UI shows elapsed time, keeps previous results visible and caches responses, but the fix belongs in the API.
- `/customers` returns about 38 MB in trained mode. The directory fetches it once and keeps only a slim index in memory.
- Two API processes must not share one `data/greenr.sqlite3`: long trained transactions will fail with `database is locked`. Use `GREENR_WORKSPACE` to give a second instance its own store.

## Layout

```
src/
  api/          HTTP client, response types, React Query hooks, save-with-toast helper
  components/   UI primitives, drawer, tables, threshold rail, report renderer, SVG charts
  lib/          formatting (Decimal strings, units, dates) and plain-language labels
  pages/        Customers, Customer, Portfolio, Planning, Governance
  pages/product the six product-drawer tabs
  styles/       design tokens (light and dark) and the stylesheet
```
