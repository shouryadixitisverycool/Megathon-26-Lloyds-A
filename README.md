# GreenPath Agent B

The synthetic demo implements all six Agent B points in `IMPLEMENTATION_PLAN.md`: impact methods and calculators, relevance rules, grounded explanations, a FastAPI service, and Streamlit customer and portfolio views.

Requires Python 3.12 and `uv`. No API credentials are needed.

```bash
make setup
make all
make app
```

Open http://127.0.0.1:8501. The launcher starts the API on port 8000 and stops both owned processes on Ctrl+C or termination. API documentation is at http://127.0.0.1:8000/docs. For different ports, run `uv run --locked python -m greenpath.demo.run --api-port 8001 --ui-port 8502`.

`make all` runs Agent B's tests and writes `reports/explanation_evaluation.json` and `reports/scenario_evaluation.json`. It does not run Agent A's data generation, training, calibration, or held-out evaluation, which are not present in this repository.

For separate processes, use `make api` and `uv run --locked streamlit run src/greenpath/app/main.py`. `GREENPATH_API_URL` selects the API address for Streamlit and defaults to `http://127.0.0.1:8000`. The UI imports HTTP and presentation code only. Its read cache expires after 15 seconds; the refresh button clears it, and an uncached health check prevents an API outage from displaying cached results.

## Five-minute demo

1. Open Customer and inspect GP-001, Asha Rao. Compare the four relevance decisions. Paperless has an explicit unavailable impact even when relevance is supported.
2. In Why this result?, select a product and inspect its decision evidence, cutoff, versions, impact method, factor sources, assumptions, and exclusions.
3. Click See responsible abstention to open GP-002. Missing evidence causes abstention despite its high synthetic propensity. GP-003 shows conflicts; GP-004 has already adopted the products; GP-005 suppresses contact; GP-006 has low propensity.
4. Open Portfolio. The six personas yield 24 product decisions across all six states, four supported opportunities, and three available impact estimates attached to supported opportunities. These are counts; no carbon total is calculated.
5. Filter region, segment, and product. Inspect the recorded synthetic monthly history and clear filters to restore the full cohort.

## Integration limits

The fixture probabilities and Trust assessments are demonstrations, not trained model outputs. Confidence remains unavailable. Replace the explicitly named contract and port mirrors with Agent A's canonical contracts and inject its providers during manual integration. [AGENT_B_HANDOFF.md](AGENT_B_HANDOFF.md) lists the owned modules and proposed mappings.

Default explanations use deterministic templates. The optional provider port accepts only schema-validated claims and approved sentence IDs. Its version must be configured; no live provider SDK or credential discovery is bundled. [The explanation module](src/greenpath/llm/README.md) describes timeout handling, fallback, and offline adversarial evaluation.

Impact uses the frozen methods in [CARBON_METHODS.md](CARBON_METHODS.md), including the historical CEA source-access limitation. Paperless carbon remains unavailable. Available values describe signed scenario differences in operational CO2, with their recorded comparison period and boundaries; they do not establish realized reductions or credit eligibility.
