# Grounded explanations

`ExplanationService().explain(recommendation)` works offline with no credentials.
The six states and four products have deterministic text. Available carbon
retains its exact signed value and units. Unavailable carbon has no number.
Trust and model confidence stay separate, and every explanation includes the
synthetic relevance and eligibility disclaimer.

Inject an `ExplanationProvider` to enable an optional configured adapter. Its
`version` must identify the configured model or adapter, or pass an explicit
`provider_version`. `generate(request, timeout_seconds=...)` returns a
`ProviderExplanation`, a JSON object, or JSON text. An adapter must use the same
deadline in its SDK. The service also enforces the caller deadline and caps
outstanding calls; it cannot cancel a provider's SDK request.

The provider receives a closed vocabulary of approved decision reasons and
sentences, the product, state, exact carbon number and units, and the fixed
disclaimer. It chooses sentence order. Product, state, reason codes, numbers,
units and disclaimer must match exactly. Every required sentence appears once.
Extra fields and free-form prose are rejected. This conservative composition
contract guarantees grounding mechanically; it limits the optional provider's
stylistic freedom. A general prose validator cannot prove semantic grounding.

Raw evidence messages, merchant descriptions, customer identifiers, trust issue
text, free-form propensity reasons, and unvalidated confidence never enter the request.
Trained explanations use the canonical reason catalogue, calibrated probability,
and validated confidence or an explicit confidence-withheld sentence.
Unknown decision reasons disable the provider path. Errors, deadlines, invalid
schema, mismatched claims, omitted caveats, and extra sentences return the same
usable deterministic fallback with a controlled `fallback_reason`.

The API remains offline when `GREENPATH_LLM_API_KEY` is absent. To enable the
optional HTTP adapter, set that key plus `GREENPATH_LLM_ENDPOINT`, `LLM_MODEL`,
and `LLM_MODEL_VERSION`. The endpoint must accept the adapter's structured chat
completion protocol. `PROMPT_VERSION`, `TEMPERATURE`, and `MAX_OUTPUT_TOKENS`
freeze prompt and sampling settings. Keyed but incomplete configuration fails
clearly. The adapter applies an HTTP timeout; the service also bounds its caller
wait and outstanding workers. All tests and reports use offline mock providers.

A bounded in-memory cache hashes canonical recommendation evidence, prompt
version, exact provider/model version, and locale. Wall-clock decision and impact
generation timestamps are excluded so repeated identical evidence can reuse an
explanation. Changing evidence, rules, model, prompt or locale invalidates reuse.
Transient provider failures are retried and are not cached.

`GET /explanations/metrics` exposes cache hits/misses, hit rate, measured local and
provider latency, attempts, model/prompt versions and token usage. Offline cost
is zero; unmeasured live cost remains null. Optional explicit prices in
`GREENPATH_LLM_INPUT_PRICE_PER_MILLION` and
`GREENPATH_LLM_OUTPUT_PRICE_PER_MILLION` calculate cost from returned usage. The
API labels their basis as configured prices, not independently verified current
pricing. No measured live model quality or cost is claimed by offline tests.

Run the checks and generate an evaluation artifact:

```bash
uv run --locked pytest tests/llm
uv run --locked python -m greenpath.llm.evaluate
```

The report measures rejection, groundedness, numeric consistency, unsupported
claims, fallback rate and local validator latency on fixed cases. Live provider
latency and cost are null because no live calls are measured. These results do
not establish live model quality or predictive performance.

Product and impact evidence use canonical `greenpath.contracts.product` and
`greenpath.contracts.impact_detail` models. Compatibility mirrors are reexports.
