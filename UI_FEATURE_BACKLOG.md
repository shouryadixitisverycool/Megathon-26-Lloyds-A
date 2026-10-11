# UI feature backlog

What the React frontend (`frontend/`) shows that has no backend yet, plus what was wired up on 2026-10-11. Sources: the PS1 spec (`Greenr_PS1_Master_MVP_v2.md` §1.1, §3, §42–45, §60–61) and an audit of FastAPI routes against what the frontend calls.

Every placeholder in the UI uses `PlaceholderButton`, `PlaceholderBadge` or `PlaceholderPanel` from `frontend/src/components/Placeholder.tsx`. Each one has a `data-placeholder="<feature>"` attribute named as in the tables below, so `grep -rn 'feature="' frontend/src` finds them all. Clicking a placeholder shows a "coming soon" toast and calls no API.

## Placeholders waiting for a backend

| Feature (`data-placeholder`) | Where in the UI | What it should do | Backend needed |
|---|---|---|---|
| EV options explorer | Customer view, EV Finance card: **Explore EV options** | Compare EVs against the customer's current car: running cost, CO₂e and finance illustration (spec §42) | New route, e.g. `GET /customers/{id}/ev-options`. Reuse the UK EV scenario inputs (`/simulation-inputs/EV_FINANCE`). Needs a vehicle catalogue |
| Home upgrade explorer | Customer view, Green Home card: **Explore home upgrades** | Insulation and heat-pump options with modelled savings | New route over the existing insulation/heat-pump UK scenarios |
| Solar explorer | Customer view, Solar Finance card: **Explore solar for your home** | Roof and system-size illustration with generation estimate | Needs PVGIS-backed generation evidence (`impact/solar_generation.py` requires reviewed inputs) |
| Paperless switch | Customer view, Paperless card: **Go paperless** | Customer switches statements to digital | A customer-authorised version of `POST /customers/{id}/source-updates` (`digital.is_paperless`), which then closes the journey |
| Explore green investments | Customer view ("You might also be interested in") and RM page Green Investments card | Show sustainable fund options | Product catalogue route. Must keep the "not investment advice" guardrail (spec §60) |
| Start a green loan enquiry | RM page Green Loans card (shown when a purpose is declared and the signal fires) | Capture a green-loan enquiry for the declared purpose | Enquiry route that records purpose and consent. No credit decision (spec §61) |
| Green spending insights | Customer view panel **Your spending footprint** | Monthly estimated emissions from categorised transactions, with tips | Route over the transaction categoriser plus DESNZ spend factors. Categoriser generalisation is weak on unseen merchants (M2 report) |
| Customer contact preferences | Customer view panel **Choose what we suggest** | Customer hides topics and chooses channels | Customer-authorised write to preferences. Today only staff record responses via `POST /feedback` (`DO_NOT_SHOW_AGAIN`) |
| Factual source updates | RM page, Customer data → **Record a factual update** | Correct a fact and re-run decisions without rewriting history | Route exists: `POST /customers/{id}/source-updates`. It needs the admin token, which must stay server-side, so a session or proxy design is needed first |
| Campaign closure | Campaign planning, after recording a simulated campaign: **Close this campaign** | Close a campaign and free channel capacity | Route exists: `POST /campaigns/{id}/close`. Same admin-token constraint as above |

## Wired up in this pass (backend already existed)

| Feature | Route | Where |
|---|---|---|
| Green Investments and Green Loans (experimental, spec §60–61) | `GET /customers/{id}/optional-opportunities?purpose=` | RM customer page → **More green opportunities**, with a declared-purpose picker for loans. Also shown in the customer view when the signal fires |
| Customer Green Hub (spec §3.1, §42–43) | `GET /customers/{id}/next-actions?channel=app`, plus optional opportunities | New page `/customers/{id}/hub`, opened from **Preview customer view** on the customer page. Shows supported opportunities in customer wording, "Why am I seeing this?", impact, data date and the eligibility disclaimer |
| Demo readiness check | `GET /demo/readiness` | Governance → **Demo readiness** (loads on request) |

Routes still not called by the UI, on purpose:

- `GET /portfolio/segments`: duplicates the region and segment summaries already returned by `/portfolio/summary`.
- `GET /customers/{id}/impact/{product}`: the Impact Passport fields (passport ID, method, factors) already arrive on each recommendation and are shown in the Impact and What-if tabs.
- `POST /recommend`, `POST /explain`: generic POST twins of the GET routes the UI already uses.

## Fixture mode realism (demo without trained models)

Changes so a fixture-mode demo (`GREENPATH_PROVIDER=fixture`) shows the same kinds of evidence as trained mode:

- **Model reason codes.** Each persona has synthetic model inputs (fuel spend, mileage, vehicle age, energy use, statements, app logins, sustainability preference) in `src/greenpath/demo/providers.py`. Reason codes are derived from them by the real catalogue (`derive_reason_codes`, default thresholds), never hand-written. They appear in "What the model picked up on", the opportunity list, the grounded explanation and the customer view.
- **Varied probabilities.** Each persona and product has its own fixed probability. GP-001 still clears 0.60 for every product and GP-006 still misses it for every product.
- **Optional opportunities.** Fixture Green Investments and Green Loans follow the trained rule order in `extensions/optional_models.py`, with fixed probabilities and a 0.50 cut-off. Confidence stays suppressed.

Still fixture-only gaps:

- No Customer 360 source record, so no SHAP attribution and no "Source record" panel.
- Confidence is always suppressed.
- GP-001 has no recorded channel consent, so its next step is "Ask for contact consent first".

## Spec items not yet represented in the UI

These are from spec §1.1 SHOULD/COULD and have neither a UI nor a backend:

- Interactive fairness console. Governance shows subgroup tables, but they aren't interactive.
- Drift monitoring over time. Only static robustness reports exist.
- Customer-facing push or nudge notifications.
