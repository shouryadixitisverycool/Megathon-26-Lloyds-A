# Recommendation rules

`RecommendationService` takes the snapshot, propensity and impact-input ports in
`greenr._product_port_mirror`. It returns four decisions in enum order and
raises `KeyError` for an unknown customer. These mirrors must be replaced by
Agent A's canonical contracts during integration.

Rules version `synthetic-relevance-rules-v1` uses a fixed demo probability
threshold of 0.60, inclusive. This is a synthetic presentation policy, not a
learned optimal threshold or evidence of model performance. A missing probability,
wrong-product score, or blank model version cannot support a recommendation.
Calibration versions are retained as metadata; their presence does not establish
real-world reliability. Confidence is null unless the provider explicitly records
`confidence_validated=True`; Trust is preserved separately.

Decision precedence is deterministic:

1. Verified current withdrawal of marketing consent suppresses contact.
2. Relevant feature conflicts, HIGH Trust conflict codes, or CONFLICT Trust
   status require review. A HIGH issue about marketing consent prevents treating
   that consent as verified. Lower-severity Trust prose does not create reasons.
3. OOD Trust status or HIGH OOD issues, a future snapshot cutoff, or other HIGH
   Trust issues cause abstention. HIGH completeness/freshness/future issues use
   the corresponding controlled reason. Unrecognized HIGH issue codes use
   TRUST_LIMITATION and cannot be downgraded to recommendations.
4. Missing, stale/unknown, or future marketing-consent/adoption evidence causes
   abstention. Verified existing adoption yields NOT_APPLICABLE.
5. Other required product evidence must be present, current and no later than
   cutoff. Missing evidence takes precedence over stale evidence, which takes
   precedence over future evidence. A false applicability prerequisite yields
   NOT_APPLICABLE. Paperless requires consent, otherwise SUPPRESSED; false
   declared interest yields DO_NOT_RECOMMEND.
6. Missing usable propensity causes abstention. Probabilities below 0.60 yield
   DO_NOT_RECOMMEND; meeting the threshold with supported relevance yields
   RECOMMEND.

EV checks vehicle ownership, supported fuel and EV interest. Green Home checks
home ownership and retrofit interest. Solar checks home ownership, roof
availability and solar interest. Paperless checks paper statements and switching
consent. Existing adoption flags are product-specific. Irrelevant fields do not
cause product-specific abstention, but HIGH Trust issues apply to every product.
Already adopted products do not require a complete interest profile. Typed
snapshot and propensity objects are revalidated at the provider boundary, even
if a provider constructed them through Pydantic's validation bypass methods.
Malformed snapshots raise a validation error and produce no decision. Malformed
propensity objects become unavailable scores and cause abstention when needed.

`REASON_MESSAGES` is the controlled vocabulary. The rules attach approved field
names and evidence references; injected propensity reason strings are discarded.
Calculators receive only the supplied impact-input mapping. They never receive
propensity or inferred activity. Missing or unavailable impact is reported
independently and cannot veto supported relevance. Impact with a cutoff after
the snapshot cutoff is discarded through the calculator's unavailable path.
Rules make no credit eligibility or approval decision.

Run `uv run --locked pytest tests/recommendation` for scoped verification.
