# Greenr API

Start the default synthetic demo with `uv run --locked uvicorn greenpath.api.main:app --host 127.0.0.1 --port 8000`.

`create_app(repository=None, *, snapshot_provider=None, propensity_provider=None, impact_input_provider=None, history_provider=None, recommendation_service=None, explanation_service=None)` accepts narrow providers or complete services. Explicit overrides take precedence over repository ports. Missing ports use `DemoRepository`; missing services use `RecommendationService` and the no-key `ExplanationService`.

| GET route | Response |
| --- | --- |
| `/health` | `status`, `synthetic_demo`, `contract_version` |
| `/customers` | CustomerSnapshot array |
| `/customers/{customer_id}` | CustomerSnapshot |
| `/customers/{customer_id}/recommendations` | RecommendationsResponse |
| `/customers/{customer_id}/opportunities` | Alias of recommendations |
| `/customers/{customer_id}/explanations/{product}` | Explanation |
| `/portfolio/summary` | PortfolioSummary |
| `/portfolio/trends` | PortfolioTrends |

Both portfolio routes accept optional `region`, `segment`, and `product` query parameters. Region and segment match exact fixture values. Combine them to intersect filters. An unknown region or segment returns an empty result. Product values are `EV_FINANCE`, `GREEN_HOME`, `SOLAR_FINANCE`, and `PAPERLESS_BANKING`. Invalid product filters and explanation product paths return HTTP 422. Unknown customers return HTTP 404 with `{"detail":"Customer not found"}`.

All Decimal fields serialize as JSON strings. Recommendation and explanation responses preserve the versioned contracts, synthetic flags, provenance, and eligibility disclaimer. The contracts are Agent B mirrors awaiting canonical Agent A integration.

Summary state counts include all six states, even when a count is zero. Totals count selected product decisions, and recommended counts include only `RECOMMEND`. Customer counts describe the filtered cohort, including customers with no recommended product. Impact availability counts include only selected `RECOMMEND` decisions with `AVAILABLE` impacts. Suppressed or conflicting decisions cannot inflate that opportunity coverage. The API calculates no carbon total.

Trends read `list_history()` rather than current recommendations. Each point represents one observed month and product, with distinct customer counts and all six state keys. Missing historical months remain absent. Identical customer/product/month rows count once; conflicting rows raise a data-integrity error. Region and segment filtering uses the current fixture customer cohort, not an invented historical demographic record. Records outside that cohort do not enter the result.
