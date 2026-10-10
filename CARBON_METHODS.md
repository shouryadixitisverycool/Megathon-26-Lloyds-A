# GreenPath carbon methods

Legacy India method release: `greenpath-carbon-v1.0.0`
Factor catalogue: `src/greenpath/impact/factors/carbon_factors.v1.json`  
Frozen on: 2026-10-10  
UK method release: `uk-physical-scenarios-v1`; reviewed factor edition: DESNZ 2025

This document freezes two distinct implemented methods: legacy India operational CO2 and UK operational energy CO2e. They are not interchangeable and must not be added into a cross-product or cross-country total. The India sections below remain the historical method specification; the UK section defines the current UK adapter. Detailed results use `contracts/impact_detail.py`.

India calculators accept only their documented India evidence. The UK adapter accepts explicit synthetic UK Customer360 scenarios; it does not apply India factors. Off-grid electricity is unsupported. Geography must be established by the caller/registry, not inferred from banking spend.

## Shared accounting rules

The following CO2-only boundary and factor choices describe the legacy India release. UK results instead use the CO2e units and wider operational energy boundary documented below. Common rules on signed changes, explicit physical evidence, missing activity, display precision and no invented runtime defaults apply to both.

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

## UK Frozen Method and Source Review

Source URL checks performed on **2026-10-10** using webfetch:

- **Selected reviewed edition: DESNZ 2025**, [official publication](https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2025), published **10 June 2025**. The publication confirms the pinned [flat-format workbook](https://assets.publishing.service.gov.uk/media/6846b6ea57f3515d9611f0dd/ghg-conversion-factors-2025-flat-format.xlsx). The existing workbook SHA-256 and all numeric factor values remain unchanged. `extensions/uk_factors_2025.json` records workbook row/source IDs, units, scopes, publication date and review limitations; its separate subset checksum changes when metadata changes.
- **Current available edition: DESNZ 2026**, [official publication](https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2026), published **11 June 2026**, updated **31 July 2026**. The update corrected flat-file zero values which should have been blank; the full set was not revised. The official page links the [revised 2026 flat file](https://assets.publishing.service.gov.uk/media/6a6c9748862aaf18d9c62ac9/ghg-conversion-factors-2026-flat-format-revised.xlsx). Publication availability is verified, **2026 numeric rows are not reviewed or adopted**. 2025 is a deliberate frozen demo comparison, not the latest edition or current-vintage 2026 reporting. Adoption requires a separate reviewed, hashed factor release and matching tests.
- CEA's [database landing page](https://cea.nic.in/cdm-co2-baseline-database/?lang=en) returned a login page on this review. No new CEA edition or numeric value was verified. The legacy FY2022-23 version 19 factor remains historical, with the existing PDF-verification limitation above. A URL path containing 2024/04 is not a verified publication date.
- IPCC's 2006 Guidelines retain their explicitly dated 2006 edition; the earlier recorded PDF table checks/checksums are retained, not represented as a new 2026 numeric review.

UK output is **kg CO2e/year**, using the frozen matched Scope 1/2 operational factors plus relevant Scope 3 well-to-tank and electricity transmission/distribution components. Electricity total is `0.177 + 0.01853 + 0.0459 + 0.00397 = 0.24540 kg CO2e/kWh`; gross-CV gas total is `0.18296 + 0.03021 = 0.21317 kg CO2e/kWh`. Petrol and diesel use the documented UK average biofuel blends, not the India unblended-fuel assumptions. Outside-of-scopes biogenic combustion CO2 is excluded under the source reporting convention. Manufacturing, embodied emissions, storage and end of life remain excluded: this is not a complete lifecycle footprint.

All model inputs are explicit. EV compares equal supplied annual mileage with litres/100km and EV battery-side kWh/100km divided by charging efficiency. Insulation applies separate caller-sourced electricity/gross-gas saving fractions. Heat pump compares supplied gross gas heating demand with delivered heat (`gas * gross boiler efficiency`) divided by seasonal performance. No mileage, fuel density, thermal performance, efficiency, capacity, generation, self-consumption or saving fraction is a runtime physical default.

UK Solar compares baseline grid demand with demand minus annual AC generation times explicitly supplied self-consumption fraction. Self-consumption exceeding baseline demand is rejected; exports receive no credit. Annual arithmetic alone does not prove interval overlap. The caller must establish matched load/generation overlap, unchanged service demand and absence of storage before interpreting this as a defensible import-reduction forecast. A free-text installer/synthetic generation declaration remains an **unverified explicit scenario**, not a source-reviewed regional estimator output.

## Regional Solar Generation

`impact/solar_generation.py` implements the public JRC **PVGIS 5.3 fixed, grid-connected PVcalc** interface, evidence version `greenpath-pvgis-5.3-fixed-v1`. The [official API documentation](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/using-pvgis-5/api-non-interactive-service_en) was accessible on 2026-10-10 and documents versioned endpoints, mandatory kW peak power and percent system losses. A direct sample API request was rejected by the upstream access policy; **no real regional yield was obtained, pinned or fabricated in this release**.

The estimator requires the caller's regional/site label, coordinates, kW peak capacity, loss percent, tilt, azimuth (0=south), PV technology, mounting, radiation database and horizon treatment. There is no invented region-to-coordinate mapping or representative regional yield. Fixed mounting/no tracking/no optimization are method boundaries sent explicitly, not guessed physical inputs. PVGIS source radiation years are retained; its long-term annual generation is not a 2026 weather forecast.

Review and archive the exact API response and pin its byte SHA-256 before calculation. `estimate_generation` consumes those bytes or fetches the exact versioned request and verifies that hash. It verifies response installation/location/database/horizon metadata, source radiation years, and `E_y` units `kWh/y`. Missing source, changed hash, rejected HTTP request, invalid/non-finite activity or incompatible energy dimensions raises `ValueError`: callers must return unavailable, never substitute a yield. The hash establishes integrity, not independent certification of caller-provided evidence.

Generation is the source's modelled annual AC output after its specified system losses. Yield is `annual_generation_kwh / proposed_capacity_kw`, in kWh/kW/year, not power or irradiation. `GenerationEstimate.scenario_fields()` produces scalar UK scenario features with the source URL, response hash, evidence version, retrieval time and radiation years in `generation_evidence`. Demand and self-consumption are still mandatory separate evidence. A site forecast must not be relabelled as a measured customer outcome. All response values in estimator unit tests are labelled synthetic, not published regional inputs.

## Avoided Emissions Guidance

Reference: WRI/WBCSD [GHG Protocol for Project Accounting](https://ghgprotocol.org/project-protocol), copyright **2005**, and [Guidelines for Grid-Connected Electricity Projects](https://ghgprotocol.org/sites/default/files/2022-12/Guidelines%20for%20Grid-Connected%20Electricity%20Projects.pdf), **August 2007**. The official project page was checked on 2026-10-10: it explicitly says the 2005 Project Protocol remains in force until the revised ISO-GHG Protocol Project Standard is published. These are project-accounting references, **not claims that GreenPath implements or is certified against those standards**.

The result is a potential operational scenario difference using constant average inventory factors. It is not verified avoided emissions, a marginal displaced-generation estimate, financed-emissions attribution, an offset/credit, or an inventory deduction. Project claims require a justified counterfactual baseline, assessment of primary and secondary effects/leakage, appropriate grid displacement method, monitoring, uncertainty and attribution/additionality review. Report scenario comparisons separately from corporate inventories; do not claim product adoption or finance caused the full difference. Do not sum overlapping EV/home/solar reductions without a separately reviewed allocation method.

## Detailed Contract and UI Handoff

UK paperless carbon status is `NOT_CLAIMED` with null carbon/baseline/scenario values and `FACTOR_NOT_ESTABLISHED`; legacy India retains `UNAVAILABLE` for carbon. Supported UK paperless scenarios expose **`secondary_metrics`** in both detailed and scoring contracts: `paper_statements_avoided` in `statements/year` and `paper_sheets_avoided` in `sheets/year`. Their values are `annual_statements * avoided_fraction` and that count times `sheets_per_statement`. These are expected activity quantities, possibly fractional, not pages, trees, mass or carbon equivalents. Actual displacement must be established for realized claims.

The detailed metric also carries `method_version` and `evidence_references`. UI consumers should render these even when carbon is `NOT_CLAIMED`, with an activity-only label and the carbon limitation. Missing/invalid paperless inputs produce `UNAVAILABLE` and no secondary metrics. No UI files are changed in this ownership scope.

Detailed **`passport_id`** is `GP-` plus the SHA-256 of canonical JSON of the result excluding calculation `timestamp` and the ID itself. It includes product, method, boundary, factors/source metadata, snapshot references, cutoff, periods, evidence, assumptions, issues and secondary metrics. A repeated calculation with identical provenance retains its ID; a different customer/evidence/method does not. Supplied IDs are validated against the content. This is deterministic provenance integrity, not a signature or certification. The lower-level UK scenario `UK-` ID intentionally identifies inputs/factors only; the detailed `GP-` ID additionally binds customer evidence and period.

UI source fields are `factors[].source_url`, `source_title`, `source_publisher`, `source_edition`, `source_published_on`, `source_checked_on`, `source_locator`, `source_sha256`, `verification_basis`, `source_limitation`, `current_edition` and `current_edition_url`. Publication dates are nullable when not verified; they are never inferred from retrieval dates or URL paths. Show the selected 2025 edition and current-vintage limitation rather than presenting it as current 2026 data.
