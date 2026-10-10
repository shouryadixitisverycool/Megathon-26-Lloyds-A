# Fixed Offline LLM Evaluation

Run `make evaluate-llm` to write `reports/explanation_evaluation.json`.
Run `uv run --locked pytest tests/llm` for the focused checks. Neither command
requires credentials or calls a live provider.

The version `fixed-adversarial-explanations-v3` suite contains **200 unique,
deterministic cases**, not repeated samples:

- The original 18 cases retain valid/reversed composition, changed product,
  state, reason, number, units and disclaimer, extra prose, missing/duplicate/
  invented sentences, malformed JSON, provider error, timeout, lost numeric
  value, negative sign removal and fabricated unavailable impact.
- 96 missing-impact combinations cover all four products and six states with
  valid output and product/state/units attacks. Each attack changes the actual
  requested claim, including Solar Finance and `NOT_APPLICABLE`.
- 72 signed-impact combinations cover positive, negative and zero EV impact
  across six states with valid/reversed composition, null substitution and
  changed units. Four overlap the original cases and are stored only once.
- Ten field-specific injection cases exercise customer ID, rules version,
  disclaimer, exclusions, decision evidence, Trust, propensity and impact
  boundary/assumptions/exclusions. The evaluator verifies the merchant attack
  marker never enters a provider request or explanation text. Unvalidated
  propensity/confidence are also checked in focused tests.
- Four unknown-decision-reason cases, one per product, verify fallback without
  a provider request or copying the malicious reason into explanation prose.
- Two explicit confidence cases cover a synthetic validated low value and
  suppressed confidence. Both withhold the relevance decision; suppressed
  confidence never leaks a numeric value into the prompt or public text.
- Two recommendations for the same customer cover multiple EV/Green Home
  opportunities without merging product reasons, actions or impact estimates.

Every case now records category tags for all spec section 41 categories, including
requests to guarantee savings, claim eligibility and alter a model score.
The free-text attack explicitly attempts all three unsupported claims and is
rejected by the closed schema. These are authored synthetic reference fixtures,
not an independently reviewed human-labelled model-quality benchmark.

Available impact comes from the deterministic EV fixture; zero uses equal
baseline/scenario emissions. Other products retain the registry's unavailable
impact rather than inventing estimates, particularly for Paperless Banking.
State-specific approved reasons exercise withholding, conflict, suppression,
already-adopted and supported/unsupported relevance wording.

Each record has a stable unique `case` identifier plus explicit `product`,
`state`, `attack`, `variant`, impact kind/status/value/units and `prompt_safe`.
Pass requires the expected accept/fallback decision, grounded facts, exact
signed numbers/units, supported sentences and a safe prompt. The existing
summary keys remain unchanged; `structured_consistency` additionally checks the
seven public fields against the deterministic reference, with order-independent
reason matching. Local latency is measured and varies by run;
the fixtures, identifiers and expected outcomes are fixed.

These are offline validator and fallback checks, **not live model quality
measurements**. Live provider latency and cost remain `null`; no live provider
performance, token usage or predictive-quality claim follows from this report.

## Public Contract and Safety

Spec section 38 fields are populated: `headline`, `explanation`,
`why_recommended`, `estimated_impact_text`, `confidence_text`, `action_text`,
`eligibility_disclaimer`, and `missing_information`. `text` remains for concrete
shipped API and Streamlit consumers. `greenpath.llm.schema.StructuredExplanation`
requires populated fields in service output. The other agent integrated the same
five string and two string-array fields into canonical product Explanation as
optional/defaulted fields for shipped constructors. The contract file was not
edited by this agent; canonical API serialization retains the populated fields.

CO2 and CO2e remain distinct according to the calculator's units, including the
impact limitation sentence. Positive/negative/zero values retain their exact sign
and unit. Confidence requires an attached, validated source; Trust is not confidence.
Unavailable impact is never interpreted as zero. Paperless has no invented carbon.

**Documented contract deviation:** the provider selects all approved sentence IDs
exactly once, rather than freely paraphrasing rationale. Identity, reason codes,
signed impact, units and disclaimer must match the input schema exactly. Public
fields are deterministic sentence projections. This is intentionally conservative:
unrestricted paraphrases cannot be proven safe by numeric/keyword checks alone.
Errors and rejected output still use the same approved deterministic fallback.

## Selected Versus Evaluated

`src/greenpath/llm/provider_manifest.json` selects OpenAI's known dated snapshot
`gpt-4.1-mini-2025-04-14`, with the exact endpoint, model/version, prompt version,
temperature, output cap and live-evaluator timeout. It supports structured output
and is selected for the bounded sentence-composition task. No current access,
availability, best-model comparison or live quality claim has been verified.
`src/greenpath/llm/config.env.example` contains matching nonsecret settings.

## Optional Live Run

No paid provider was called for this implementation. The optional command is:

```bash
uv run --locked python scripts/evaluate_llm_live.py --allow-paid-provider --cases 100 --output reports/llm_live_evaluation.json
```

Requirements: explicit paid-call opt-in, existing `GREENPATH_LLM_API_KEY`, and
current user-configured `GREENPATH_LLM_INPUT_PRICE_PER_MILLION`,
`GREENPATH_LLM_OUTPUT_PRICE_PER_MILLION`, and
`GREENPATH_LLM_CACHED_INPUT_PRICE_PER_MILLION`. Prices must use one currency per
run; the report records them as configured, not independently verified prices.
Use `--cases 100` through `--cases 200`. The evaluator freezes case order and
covers all product/state combinations, signed/zero impact, confidence and multiple
opportunities before filling with distinct synthetic numerical scenarios. These
are distinct provider inputs, not repeated offline response mutations. It disables application cache
for case measurements, then probes a separate cache twice. It stops on the first
provider/network error or timeout; incomplete runs are marked and exit nonzero.

Records include provider acceptance/fallback, final-output grounding, measured
input/output/provider-cached tokens, end-to-end latency and token-derived cost.
Aggregate provider measurements include the cache probe, total tokens, total cost
and cost per 1,000 completed calls. Application cache hits/misses and hit rate are
reported separately. A 100-case successful run normally makes 101 provider calls;
at most 102 if the first cache probe is rejected. Missing token usage or required
pricing leaves cost null, never fabricated. Mock transport tests verify accounting
but are not live model evidence. Offline response-mutation attacks describe case
provenance, not attacks actually presented to the live model; acceptance on this
live suite is not a jailbreak-resistance score.

## Local Verification

`uv run --locked pytest tests/llm`: **196 passed**, including all **200** offline
evaluation cases and mock-only live evaluator accounting/authorization checks.
Focused `tests/app/test_app.py` and `tests/app/test_client_and_formatting.py`:
**40 passed**. These measurements are local tests, not real-provider results.
`GREENPATH_PROVIDER=fixture uv run --locked pytest tests/api/test_api.py`:
**20 passed**. Fixture mode avoids unrelated incomplete trained artifacts during
API module initialization; it is not a trained-artifact integration run.
