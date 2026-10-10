# GreenPath carbon methods

Method release: `greenpath-carbon-v1.0.0`  
Factor catalogue: `src/greenpath/impact/factors/carbon_factors.v1.json`  
Frozen on: 2026-10-10  
Owner: Agent B, implementation sequence point 1

This document freezes the method choices for the next implementation step. It does not implement the calculators or define Agent A's canonical contracts. Input names below describe required evidence; their eventual mapping into `CustomerSnapshot` must be agreed at integration.

The referenced `GreenPath_PS1_Master_MVP_v2.md` and frozen contract packet are absent from this workspace. India is the explicit working geography for this demo, subject to reconciliation with that specification. Other countries and off-grid electricity are unsupported in this release.

## Shared accounting rules

- Calculate a signed change as baseline emissions minus scenario emissions over the same stated period and service demand. A negative result means higher scenario emissions; never clamp it to zero or describe it as a saving.
- Report `kg CO2` for the stated period. Only label a result `kg CO2/year` when the supplied baseline and scenario both cover a full year or a documented annual forecast. Do not automatically annualize a partial month.
- These methods cover selected operational CO2 sources. They omit other greenhouse gases and lifecycle stages, so the UI must not relabel their output as CO2e, lifecycle savings, carbon neutrality, carbon credits, or verified avoided emissions.
- Keep scenario estimates distinct from measured results. Synthetic inputs must say `synthetic_demo`; customer declarations, meter readings, and engineering forecasts must carry their own evidence references and observation periods.
- Merchant spend, propensity, ownership, salary, and product adoption are not energy measurements. Never convert rupees to litres or kWh using an assumed tariff or fuel price.
- Use only the frozen factor IDs with compatible geography, fuel, unit, and accounting boundary. Missing or incompatible factors return `UNAVAILABLE`. There is no runtime web lookup or automatic switch to a newer edition.
- All quantities must be finite numbers with explicit units. Reject booleans, NaN, infinity, negative activity, impossible physical combinations, conflicting evidence, and observations after the feature cutoff. Known zero activity is valid and distinct from missing activity.
- Preserve full arithmetic precision. Round only the display value to one decimal kg CO2; retain unrounded values for aggregation. Do not invent a confidence interval from propensity confidence or Trust.

Freshness has no agreed numeric limit yet. The caller must supply an approved observation period and a freshness assessment. Evidence marked stale or with unresolved freshness returns `UNAVAILABLE`; this document does not invent a shared Trust threshold.

## Frozen factors and evidence

The machine-readable catalogue stores original units, normalized units, source edition, table locator, verification basis, and applicability. Numeric values are decimal strings to preserve the published precision; calculators should parse them as decimals. It is a method artifact, not a second contract authority.

### Indian grid electricity

`CEA_GRID_IN_FY2022_23_V19` is **0.716 kg CO2/kWh**, converted from 0.716 t CO2/MWh. It is the Indian-grid weighted average including renewable generation, captive injection, and cross-border transfers for FY 2022-23. The source is CEA's [CO2 Baseline Database, version 19.0, table 5, printed page 13](https://cea.nic.in/wp-content/uploads/baseline/2024/04/User_Guide__Version_19.0.pdf).

This is a pinned historical national average for a demo comparison. It is not a current local, marginal, hourly, supplier-specific, or transmission-loss-adjusted factor. CEA lists newer editions; they do not replace this release automatically. Using the historical factor for a future scenario is an explicit constant-grid assumption, not a forecast of grid decarbonization.

Verification on 2026-10-10 used indexed text of CEA's official guide. Direct PDF requests redirected to a login page, so there is no verified PDF checksum. The catalogue records that limitation and the selected row. Do not claim that the complete CEA PDF was archived or downloaded. Before any use beyond the synthetic demo, retrieve the edition from CEA, archive and hash it, and review its temporal and geographic suitability.

Use this average consistently across EV, Green Home, and Solar. Do not substitute an operating-margin or combined-margin factor to make solar look better. Solar results here are an accounting comparison of electricity imports, not a causal estimate of displaced power-plant generation.

### Fossil road fuels

The [IPCC 2006 Guidelines, volume 2, chapter 3, table 3.2.1, printed page 3.16](https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/2_Volume2/V2_3_Ch3_Mobile_Combustion.pdf) supply these default combustion factors:

- `IPCC2006_ROAD_GASOLINE_CO2`: 69,300 kg CO2/TJ, or 0.0693 kg CO2/MJ.
- `IPCC2006_ROAD_DIESEL_CO2`: 74,100 kg CO2/TJ, or 0.0741 kg CO2/MJ.

The [same guidelines, chapter 1, table 1.2, printed page 1.18](https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/2_Volume2/V2_1_Ch1_Introduction.pdf) supply net calorific values:

- `IPCC2006_GASOLINE_NCV`: 44.3 TJ/Gg, or 44.3 MJ/kg.
- `IPCC2006_DIESEL_NCV`: 43.0 TJ/Gg, or 43.0 MJ/kg.

Both PDFs were downloaded, their tables checked with `pdftotext`, and their SHA-256 digests recorded in the catalogue. IPCC defaults are estimates, not locally measured fuel properties. Use them only for documented unblended fossil motor gasoline or gas/diesel oil. Unknown blends, ethanol-blended petrol, biodiesel, CNG, LPG, and hybrid baselines are unsupported. Do not apply a US per-gallon gasoline factor to Indian fuel without a composition basis. No fuel density is assumed or frozen here.

## EV Finance

Method ID: `ev-operational-co2-v1`  
Boundary: `vehicle_fuel_combustion_and_charging_generation_co2`

Required evidence:

- Baseline fossil fuel type and composition, plus mass consumed in kg over the comparison period.
- Scenario charging electricity in kWh measured or estimated **at the charger input**, including charging losses, for the same travel distance and period.
- India grid location, comparison-period bounds, baseline and scenario travel distance, and evidence basis for each input.
- Battery-electric replacement with all charging covered by the frozen grid factor. Plug-in hybrids, mixed charging supplies, and an EV that supplements rather than replaces the baseline are unsupported.

Formula, where `m` is fuel mass, `NCV` is MJ/kg, `f` is kg CO2/MJ, `q` is charger-input kWh, and `g` is kg CO2/kWh:

```text
baseline_kg_co2 = m * NCV * f
scenario_kg_co2 = q * g
change_kg_co2 = baseline_kg_co2 - scenario_kg_co2
```

Litres may be converted to kg only with separately sourced fuel-specific density and units supplied as evidence. A future distance/intensity adapter must document the vehicle, fuel intensity, and whether electricity intensity includes charging losses. No typical mileage, density, annual distance, or charging-loss percentage is a default.

Excluded: fuel extraction/refining/distribution, electricity upstream supply chains and transmission/distribution losses, vehicle and battery manufacture, maintenance, end of life, non-CO2 gases, and urea additives. The headline must always include both fuel combustion and charging generation. Zero EV tailpipe CO2 alone is not the headline impact.

Return `UNAVAILABLE` for missing fuel composition, unknown density when only litres are supplied, battery-output-only kWh, differing travel demand, unsupported charging mix, or missing period/evidence/factor.

## Green Home

Method ID: `home-electricity-operational-co2-v1`  
Boundary: `home_grid_electricity_generation_co2`

Require baseline and scenario grid-import kWh for the same home, service demand, and comparison period. A scenario forecast must be supported by a documented retrofit/efficiency assessment. Observed before/after readings need a documented adjustment for weather, occupancy, and service changes, or evidence that these are comparable. A green building label, mortgage, appliance purchase, or rupee bill alone is insufficient.

```text
baseline_kg_co2 = baseline_grid_import_kwh * g
scenario_kg_co2 = scenario_grid_import_kwh * g
change_kg_co2 = baseline_kg_co2 - scenario_kg_co2
```

Limit v1 to electricity efficiency with unchanged fuel use. Exclude construction and retrofit embodied emissions, refrigerants, water, and non-electric fuels. Fuel-switching, changes in on-site generation, or unaccounted heating/cooking fuel changes return `UNAVAILABLE`. Solar import reductions belong to Solar Finance and must not also be counted as Green Home efficiency savings.

## Solar Finance

Method ID: `solar-self-consumption-operational-co2-v1`  
Boundary: `solar_reduction_in_grid_import_generation_co2`

Require baseline grid-import kWh and scenario solar self-consumed AC kWh for matched load intervals over the comparison period. Self-consumption must come from metering or a documented generation/load forecast and be net of inverter losses and auxiliaries. Establish that solar replaces grid imports at those intervals. Require unchanged demand, no storage, and no displaced diesel or other fuel in v1.

```text
scenario_grid_import_kwh = baseline_grid_import_kwh - self_consumed_solar_kwh
baseline_kg_co2 = baseline_grid_import_kwh * g
scenario_kg_co2 = scenario_grid_import_kwh * g
change_kg_co2 = baseline_kg_co2 - scenario_kg_co2
```

Validate `0 <= self_consumed_solar_kwh <= baseline_grid_import_kwh` at each matched interval. Never assume all annual generation is self-consumed. Exports receive no credit in this method. Array capacity in kWp, roof area, or a monthly rupee bill alone cannot establish generation or self-consumption. There is no default yield, sunshine duration, capacity factor, or degradation rate.

Excluded: panel/inverter manufacture, installation, maintenance, end of life, upstream electricity emissions, and grid transmission/distribution losses. Zero on-site combustion does not mean zero lifecycle emissions. Return `UNAVAILABLE` for missing load overlap, only nameplate capacity, storage, unsupported fuel displacement, or physically inconsistent self-consumption.

## Paperless Banking

Method ID: `paperless-carbon-unavailable-v1`  
Boundary: `paper_statement_and_digital_delivery_comparison_not_established`

**Carbon impact is `UNAVAILABLE` in v1.** No generic kg CO2-per-page, tree equivalence, postage factor, or zero-carbon digital assumption is frozen. Paper factors vary by paper specification and lifecycle treatment; digital delivery also needs a basis. A partial material figure must not be displayed as the net carbon benefit of paperless banking.

A separate non-carbon metric may report avoided physical sheets when statement frequency, sheets per statement, delivery preference, and actual displacement are known. Pages and sheets differ for duplex printing. Label the count separately; it does not populate the carbon value.

To enable carbon later, review and version a matched paper/digital boundary with paper mass/type/recycled content, printing, envelopes, delivery, disposal, incremental digital activity, and compatible sourced factors. Until then, return `UNAVAILABLE` with `FACTOR_NOT_ESTABLISHED`; do not insert a synthetic factor even for the demo.

## Result provenance and unavailable behavior

Every calculator must return the plan's common `ImpactResult`, including product, status, units, baseline/scenario, factor IDs with source/edition, boundary, assumptions, method version, and timezone-aware calculation timestamp. Also preserve comparison-period and activity evidence references. If the canonical contract has no place for these, propose a field mapping to Agent A before coding a private extension.

`UNAVAILABLE` must have a null numeric impact, never zero, and specific missing/invalid evidence codes. Proposed impact codes are `MISSING_INPUT`, `INVALID_INPUT`, `CONFLICTING_INPUT`, `STALE_INPUT`, `UNSUPPORTED_SCOPE`, `FACTOR_NOT_ESTABLISHED`, and `INCOMPARABLE_BASELINE`. These are local method requirements pending mapping into the canonical contract, not changes to the six recommendation states. The successful impact status enum is also pending that contract.

Store all issues when multiple checks fail. Preserve the attempted method version, boundary, relevant factor references, and calculation timestamp even when no number can be produced. Explain what evidence would permit a calculation. An impact being unavailable does not itself establish product irrelevance or financial ineligibility.

Portfolio estimates must distinguish potential from realized reductions, count only available impacts with compatible periods/boundaries, and disclose unavailable coverage. Do not add overlapping home, solar, or EV charging changes without a separate allocation method. This release freezes no cross-product total.

## Numeric examples for step 2

These inputs are synthetic illustrations, not typical customer values or defaults. All examples assume valid, comparable full-year evidence in India and the frozen grid factor.

- EV: 600 kg unblended fossil gasoline and 1,800 charger-input kWh. Baseline `600 * 44.3 * 0.0693 = 1841.994`; scenario `1800 * 0.716 = 1288.8`; change **553.194 kg CO2/year**. Record both fuel factors and the grid factor.
- EV with the same fuel mass and 3,000 charger-input kWh: change **-306.006 kg CO2/year**. Display the increase honestly.
- Green Home: 4,000 baseline and 3,000 scenario import kWh. Change **716 kg CO2/year**.
- Solar: 4,000 baseline import kWh and 2,500 documented self-consumed solar kWh with valid interval overlap. Scenario imports 1,500 kWh; change **1,790 kg CO2/year**.
- Known zero matched activity: **0 kg CO2**, if all required evidence is present. Missing activity: `UNAVAILABLE` and null value.
- Paperless: `UNAVAILABLE` and null value even when a physical sheet count is known.

Step 2 must add formula/unit tests and the invalid/missing/conflict cases above when implementing the four calculators. No application scaffold, canonical contracts, or calculator code is part of point 1.

Step 2 is now implemented in `src/greenpath/impact/` with scoped tests and synthetic input fixtures in `tests/impact/`. The original factor/method release is unchanged. See [`AGENT_B_HANDOFF.md`](AGENT_B_HANDOFF.md) for setup, the replaceable contract mirrors, proposed integration mappings, and supported input precision.
