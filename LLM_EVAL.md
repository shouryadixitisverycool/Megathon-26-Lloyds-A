# Fixed Offline LLM Evaluation

Run `make evaluate-llm` to write `reports/explanation_evaluation.json`.
Run `uv run --locked pytest tests/llm` for the focused checks. Neither command
requires credentials or calls a live provider.

The version `fixed-adversarial-explanations-v2` suite contains **196 unique,
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

Available impact comes from the deterministic EV fixture; zero uses equal
baseline/scenario emissions. Other products retain the registry's unavailable
impact rather than inventing estimates, particularly for Paperless Banking.
State-specific approved reasons exercise withholding, conflict, suppression,
already-adopted and supported/unsupported relevance wording.

Each record has a stable unique `case` identifier plus explicit `product`,
`state`, `attack`, `variant`, impact kind/status/value/units and `prompt_safe`.
Pass requires the expected accept/fallback decision, grounded facts, exact
signed numbers/units, supported sentences and a safe prompt. The existing
summary keys remain unchanged. Local latency is measured and varies by run;
the fixtures, identifiers and expected outcomes are fixed.

These are offline validator and fallback checks, **not live model quality
measurements**. Live provider latency and cost remain `null`; no live provider
performance, token usage or predictive-quality claim follows from this report.
