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
text, propensity reason text, and unvalidated confidence never enter the request.
Unknown decision reasons disable the provider path. Errors, deadlines, invalid
schema, mismatched claims, omitted caveats, and extra sentences return the same
usable deterministic fallback with a controlled `fallback_reason`.

No live network adapter is included or discovered from environment variables.
Live credentials and an explicit configured provider are needed before making
any live calls. All tests and the report use fixed offline providers.

Run the checks and generate an evaluation artifact:

```bash
uv run --locked pytest tests/llm
uv run --locked python -m greenpath.llm.evaluate
```

The report measures rejection, groundedness, numeric consistency, unsupported
claims, fallback rate and local validator latency on fixed cases. Live provider
latency and cost are null because no live calls are measured. These results do
not establish live model quality or predictive performance.

The imports use the documented replaceable Agent B product contract mirror.
Replace it with Agent A's canonical contracts during manual integration.
