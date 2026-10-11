# Grounded explanations

`ExplanationService().explain(recommendation)` works offline with no credentials.
The six states and four products have deterministic text. Available carbon
retains its exact signed value and units. Unavailable carbon has no number.
Trust and model confidence stay separate, and every explanation includes the
synthetic relevance and eligibility disclaimer.

Public output follows spec section 38: `headline`, `explanation`,
`why_recommended` (array), `estimated_impact_text`, `confidence_text`,
`action_text`, `eligibility_disclaimer`, and `missing_information` (array).
Reasons explain the actual decision, including abstentions; the field name
`why_recommended` does not imply every state is a recommendation. Actions are
product-specific exploration/review, never credit approval or guaranteed savings.
The shipped `text` field remains populated for existing API/UI consumers.
The canonical `contracts/product.py::Explanation` owner added compatible optional
fields; `llm.schema.StructuredExplanation` requires them to be populated for service
output. Canonical API serialization retains them without stripping subclass fields.

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
This is an explicit spec deviation from unrestricted paraphrasing: approved
sentences only, not a second LLM judge or keyword-only claims of semantic safety.
All public fields are deterministic projections of the validated sentences.

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
wait and outstanding workers. All tests and checked-in reports use offline mock providers.

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
optional `GREENPATH_LLM_CACHED_INPUT_PRICE_PER_MILLION` prices provider-cached
input tokens separately; cost is null if cached tokens exist but that price is absent.
The API labels their basis as configured prices, not independently verified current
pricing. No measured live model quality or cost is claimed by offline tests.

Run the checks and generate an evaluation artifact:

```bash
uv run --locked pytest tests/llm
make evaluate-llm
```

The report uses 200 unique deterministic cases, preserving the original 18
adversarial cases. It covers all four products and six states, missing impact,
positive/negative/zero EV impact, changed claims, composition attacks, provider
failures and malicious fields that must never enter the provider prompt.
Each case records a stable unique identifier, product, state and impact variant.
See `LLM_EVAL.md` for the coverage breakdown and offline limitations.

## Promo copy (short ads)

`llm/promo.py::PromoService` drafts four ad sizes from a recommendation:
`push` (1 line, 50 chars), `one_liner` (banner, 80 chars), `short` (card,
2-4 lines) and `medium` (email block, 3-5 lines). `GET
/customers/{id}/promos/{product}?format=&channel=` returns `AVAILABLE` copy
only when `extensions.service.communication()` returns an engage action;
otherwise `WITHHELD` with the rule's reason. `preview=true` also returns
`PREVIEW` copy for a `RECOMMEND` decision blocked only by contact rules.

Unlike explanations, a provider writes the lines itself, under mechanical
checks (`validate_promo`): no digits or currency, only the `{impact}`
placeholder (short/medium, available positive annual impact; code renders the
rounded carbon-engine value labelled "(estimate)"), no eligibility, savings,
absolute-green or personal-data claims, no links, markup or other product names,
and per-format line/character limits. Product and format must be echoed. Any
failure, timeout or missing key returns a deterministic template with a
controlled `fallback_reason`. The call-to-action label and disclaimer are always
attached by code. The provider request contains closed reason themes and limits,
never customer values. `PROMO_PROMPT_VERSION` (default `promo-copy-v1`) versions
the prompt; `GET /promos/metrics` reports requests, cache hits and fallbacks.

## Selected provider and optional live evaluation

`provider_manifest.json` pins OpenAI `gpt-4.1-mini-2025-04-14`, the exact dated
model snapshot, endpoint, prompt version, sampling settings, and evaluator deadline.
It is **selected, not live evaluated**. This known structured-output snapshot is
chosen for a small bounded composition task, not because measured quality/cost
beat another model. No claim of current availability or access is made.
`config.env.example` gives the corresponding nonsecret application configuration.
Neither file contains credentials or a stale price disguised as current pricing.

After explicit authorization, existing credentials and user-configured current
input/output/cached-input prices are all required to use the optional evaluator:

```bash
uv run --locked python scripts/evaluate_llm_live.py --allow-paid-provider --cases 100 --output reports/llm_live_evaluation.json
```

The CLI does not run without the opt-in flag. Its fixed 100-200 inputs cover all
products/states, confidence, multiple opportunities and signed numerical scenarios;
they are distinct provider prompts, not repeated offline response mutations.
It makes at most 100-200 case calls
plus up to two cache-probe calls, with no retries. It stops early on a provider
error or timeout. The report separates final-output grounding (including safe
fallbacks) from provider acceptance, and records per-case measured token usage,
latency and cost plus aggregate cache metrics. Missing usage remains null.
Provider prefix-cache tokens and the application's in-memory cache are distinct.
Offline adversarial output mutations are not sent as live user instructions.
No real-provider run has been performed as part of this implementation.

The report measures rejection, groundedness, numeric consistency, unsupported
claims, fallback rate and local validator latency. Live provider
latency and cost are null because no live calls are measured. These results do
not establish live model quality or predictive performance.

Product and impact evidence use canonical `greenpath.contracts.product` and
`greenpath.contracts.impact_detail` models. Compatibility mirrors are reexports.
