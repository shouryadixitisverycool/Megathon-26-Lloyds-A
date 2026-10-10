"""Adapt reviewed UK scenarios without defaults or CO2e-to-CO2 relabelling.

Scenario fields are supplied separately through UKImpactInput. They are explicit
engineering assumptions, never model predictors inferred from spend. Missing fields remain missing. The
source snapshot must be the one at the requested cutoff, including in history.
"""

from calendar import monthrange
from datetime import date, datetime, time, timezone
from decimal import Context, Decimal, InvalidOperation, localcontext

from pydantic import ValidationError

from greenpath.contracts.customer import CustomerSnapshot
from greenpath.contracts.enums import ImpactStatus, Product
from greenpath.contracts.impact import ImpactAssumption, ImpactMetric, ImpactResult as ScoringImpactResult
from greenpath.contracts.impact_detail import (
    ActivityEvidence, EmissionsScenario, FactorReference, ImpactIssue, ImpactResult,
    IssueCode, Period, SecondaryActivityMetric,
)
from greenpath.extensions import uk_impact
from greenpath.impact.common import utc_now
from greenpath.pipelines.scenario_provider import UKImpactInput


INPUT_MODELS = {
    Product.EV_FINANCE: uk_impact.EVInputs,
    Product.SOLAR_FINANCE: uk_impact.SolarInputs,
    Product.GREEN_HOME: uk_impact.InsulationInputs,
    Product.PAPERLESS_BANKING: uk_impact.PaperlessInputs,
}
UNITS = {
    "annual_mileage_km": "km/year", "ice_litres_per_100km": "litres/100km",
    "ev_kwh_per_100km": "kWh/100km", "charging_efficiency": "fraction",
    "annual_electricity_kwh": "kWh/year", "annual_generation_kwh": "kWh/year",
    "self_consumption_fraction": "fraction", "proposed_capacity_kw": "kW",
    "annual_gas_kwh_gross": "kWh/year (Gross CV)",
    "annual_heating_gas_kwh_gross": "kWh/year (Gross CV)",
    "electricity_saving_fraction": "fraction", "gas_saving_fraction": "fraction",
    "boiler_efficiency_gross": "fraction", "seasonal_performance_factor": "ratio",
    "annual_statements": "statements/year", "sheets_per_statement": "sheets/statement",
    "avoided_fraction": "fraction",
}


class UKImpactCalculator:
    """Reviewed CO2e scenarios for the detailed product and numeric scoring ports."""

    def __init__(self, product, *, clock=utc_now):
        self.product = Product(product)
        self.clock = clock

    def _prepare(self, payload):
        issues, evidence, inputs = [], [], {}
        scenario_rows = payload.scenario if isinstance(payload, UKImpactInput) else ()
        if isinstance(payload, UKImpactInput):
            payload = payload.snapshot
        scenario_fields = {row.field: row for row in scenario_rows}
        if len(scenario_fields) != len(scenario_rows):
            issues.append(ImpactIssue(code=IssueCode.CONFLICTING_INPUT, field="scenario",
                message="Supply one point-in-time scenario row per field."))
        source, cutoff, period = None, None, None
        if payload is None:
            issues.append(ImpactIssue(code=IssueCode.MISSING_INPUT, field="snapshot",
                                      message="Supply a point-in-time UK synthetic Customer360 snapshot."))
        else:
            try:
                raw = payload.model_dump(mode="python") if isinstance(payload, CustomerSnapshot) else payload
                source = CustomerSnapshot.model_validate(raw)
            except ValidationError as exc:
                issues.extend(ImpactIssue(code=IssueCode.INVALID_INPUT,
                    field="snapshot." + ".".join(map(str, error["loc"])), message=error["msg"])
                    for error in exc.errors(include_input=False, include_context=False))
        if source:
            day = source.feature_cutoff
            for row in scenario_rows:
                if (row.customer_id != source.customer_id or row.product != self.product
                        or row.effective_on > day or row.available_on > day):
                    issues.append(ImpactIssue(code=IssueCode.INVALID_INPUT, field=row.field,
                        message="Scenario evidence must match customer/product and be effective and available at cutoff."))
                if row.unit != UNITS.get(row.field):
                    issues.append(ImpactIssue(code=IssueCode.INVALID_INPUT, field=row.field,
                        message="Scenario evidence unit does not match the physical input."))
                if row.field == "annual_generation_kwh" and row.basis != "REVIEWED_PVGIS":
                    issues.append(ImpactIssue(code=IssueCode.INVALID_INPUT, field=row.field,
                        message="Solar generation requires caller-reviewed PVGIS evidence; synthetic generation is not accepted."))
            cutoff = datetime.combine(day, time.min, tzinfo=timezone.utc)
            period = Period(start=day, end=date(day.year + 1, day.month,
                min(day.day, monthrange(day.year + 1, day.month)[1])))
            model = INPUT_MODELS[self.product]
            if self.product == Product.GREEN_HOME and scenario_fields.get("intervention") and scenario_fields["intervention"].value == "HEAT_PUMP":
                model = uk_impact.HeatPumpInputs
            # Only typed source activities override scenario features. None must
            # not be replaced by a forecast disguised as an observed baseline.
            activities = {}
            if self.product == Product.EV_FINANCE:
                activities = {
                    "annual_mileage_km": (source.vehicle.annual_mileage_km, "vehicle.annual_mileage_km"),
                    "fuel_type": (source.vehicle.fuel_type.value if source.vehicle.fuel_type else None, "vehicle.fuel_type"),
                    "mileage_evidence": ("ESTIMATED" if source.vehicle.mileage_is_estimated else "OBSERVED", "vehicle.mileage_is_estimated"),
                }
                if source.vehicle.record_updated_at and source.vehicle.record_updated_at > day:
                    issues.append(ImpactIssue(code=IssueCode.INVALID_INPUT, field="vehicle.record_updated_at",
                                              message="Vehicle evidence was recorded after the feature cutoff."))
            elif self.product in {Product.SOLAR_FINANCE, Product.GREEN_HOME}:
                if "annual_electricity_kwh" in model.model_fields:
                    activities["annual_electricity_kwh"] = (source.energy.electricity_kwh_12m, "energy.electricity_kwh_12m")
                if self.product == Product.SOLAR_FINANCE:
                    activities["region"] = (source.home.region, "home.region")
                # Customer360 gas does not establish gross/net calorific basis.
                # Require a separately declared gross-CV scenario quantity.
                forecast = scenario_fields.get("annual_electricity_kwh")
                electricity_months = source.energy.electricity_months_present
                coverage = electricity_months if electricity_months is not None else source.energy.energy_months_present
                annualised = (source.energy.electricity_is_estimated is True and coverage > 0
                    and source.energy.electricity_kwh_observed is not None
                    and source.energy.electricity_annualisation_factor is not None
                    and source.energy.electricity_annualisation_factor == 12 / coverage)
                if coverage != 12 and forecast and forecast.basis == "EXPLICIT_FORECAST":
                    activities.pop("annual_electricity_kwh", None)
                elif coverage != 12 and not annualised:
                    issues.append(ImpactIssue(code=IssueCode.INCOMPARABLE_BASELINE, field="energy.energy_months_present",
                                              message="Annual metered baseline requires all 12 months."))
            else:
                activities["annual_statements"] = (source.digital.paper_statements_12m, "digital.paper_statements_12m")
                forecast = scenario_fields.get("annual_statements")
                if source.data_quality.digital_months_present != 12 and forecast and forecast.basis == "EXPLICIT_FORECAST":
                    activities.pop("annual_statements", None)
                elif source.data_quality.digital_months_present != 12:
                    issues.append(ImpactIssue(code=IssueCode.INCOMPARABLE_BASELINE, field="data_quality.digital_months_present",
                                              message="Annual statement baseline requires all 12 months."))
            for field in model.model_fields:
                row = scenario_fields.get(field)
                value, path = activities.get(field, (row.value if row else None, "scenario." + field))
                if value is None:
                    continue
                inputs[field] = value
                is_scenario = path.startswith("scenario.")
                evidence_value = value
                if field in UNITS:
                    try:
                        evidence_value = Decimal(str(value))
                    except InvalidOperation:
                        continue
                    if not evidence_value.is_finite():
                        continue
                observed_at = cutoff
                evidence_period = period
                if is_scenario:
                    observed_at = datetime.combine(row.available_on, time.min, tzinfo=timezone.utc)
                if path.startswith("vehicle.") and source.vehicle.record_updated_at:
                    observed_at = datetime.combine(source.vehicle.record_updated_at, time.min, tzinfo=timezone.utc)
                if path.startswith(("energy.", "digital.")):
                    end = day.replace(day=1)
                    evidence_period = Period(start=end.replace(year=end.year - 1), end=end)
                evidence.append(ActivityEvidence(field=field,
                    value=evidence_value, unit=UNITS.get(field),
                    reference=f"{row.source_id}:{row.assumption_id}:effective={row.effective_on}:available={row.available_on}:{row.description}" if is_scenario else f"customer360:{source.feature_version}:{day}:{source.customer_id}:{path}",
                    basis=row.basis if is_scenario else "SYNTHETIC_SOURCE_ESTIMATED" if (
                        field == "annual_mileage_km" and source.vehicle.mileage_is_estimated
                        or field == "annual_electricity_kwh" and source.energy.electricity_is_estimated
                    ) else "SYNTHETIC_SOURCE_ACTIVITY",
                    observed_at=observed_at, period=evidence_period, freshness="point-in-time",
                ))
            try:
                model.model_validate(inputs)
            except ValidationError as exc:
                issues.extend(ImpactIssue(
                    code=IssueCode.MISSING_INPUT if error["type"] == "missing" else IssueCode.INVALID_INPUT,
                    field=".".join(map(str, error["loc"])), message=error["msg"])
                    for error in exc.errors(include_input=False, include_context=False))
        passport = None
        catalogue = None
        try:
            catalogue = uk_impact.factor_catalogue()
            if not issues:
                passport = uk_impact.calculate(self.product, inputs)
        except (OSError, ValueError, KeyError) as exc:
            issues.append(ImpactIssue(code=IssueCode.FACTOR_NOT_ESTABLISHED if catalogue is None else IssueCode.INVALID_INPUT,
                field="factor_catalogue" if catalogue is None else "scenario", message=str(exc)))
        return source, cutoff, period, inputs, tuple(evidence), tuple(issues), passport, catalogue

    def calculate(self, payload) -> ImpactResult:
        source, cutoff, period, inputs, evidence, issues, passport, catalogue = self._prepare(payload)
        factors = ()
        if passport and passport["status"] != "NOT_CLAIMED":
            factors = tuple(FactorReference(
                factor_id=key, value=Decimal(record["value"]), unit=record["units"],
                original_value=Decimal(record["value"]), original_unit=record["units"],
                geography=catalogue["geography"], activity_period=catalogue["selected_edition"],
                boundary=record["scope"] + ": " + record["category"],
                applicability=record["activity"], source_id=record["source_id"],
                source_url=catalogue["source_url"], source_title=f"Greenhouse gas reporting conversion factors {catalogue['selected_edition']}",
                source_publisher="DESNZ", source_edition=catalogue["selected_edition"],
                source_locator=f"{catalogue['source_sheet']} row {record['source_row']}",
                source_sha256=catalogue["source_sha256"],
                verification_basis=catalogue["verification_basis"] + " Subset SHA-256: " + uk_impact.FACTOR_SUBSET_SHA256,
                 source_limitation=catalogue["current_vintage_limitation"],
                 source_published_on=catalogue["published_on"],
                 source_checked_on=catalogue["source_checked_on"],
                 current_edition=catalogue["current_edition"],
                 current_edition_url=catalogue["current_edition_url"],
            ) for key, record in passport["factor_records"].items())
        available = passport is not None and passport["status"] != "NOT_CLAIMED" and not issues
        not_claimed = passport is not None and passport["status"] == "NOT_CLAIMED" and not issues
        baseline = Decimal(passport["baseline_emissions"]) if available else None
        scenario = Decimal(passport["scenario_emissions"]) if available else None
        # Preserve exact subtraction of the published Decimal emissions, even
        # when a repeating physical ratio rounded the scenario calculation.
        with localcontext(Context(prec=60)):
            reduction = baseline - scenario if available else None
        if not_claimed and not issues:
            issues = (ImpactIssue(code=IssueCode.FACTOR_NOT_ESTABLISHED, field="carbon",
                message="Paper avoidance is activity only; no reviewed lifecycle carbon method is implemented."),)
        return ImpactResult(
            product=self.product,
            status=ImpactStatus.AVAILABLE if available else ImpactStatus.NOT_CLAIMED if not_claimed else ImpactStatus.UNAVAILABLE,
            value=reduction,
            units="kg CO2e/year",
            baseline=EmissionsScenario(description="UK annual forecast baseline; " +
                ("explicit estimated activity" if any(e.basis in {"EXPLICIT_FORECAST", "SYNTHETIC_SOURCE_ESTIMATED"} for e in evidence)
                 else "full source coverage where required; synthetic scenario quantities are not measured"),
                emissions_kg_co2e=baseline),
            scenario=EmissionsScenario(description="Explicit UK annual physical scenario",
                emissions_kg_co2e=scenario),
            period=period, feature_cutoff=cutoff, synthetic_demo=True if source else None,
            factors=factors, factor_catalogue_version=catalogue["version"] if catalogue else "unverified",
            factor_catalogue_sha256=uk_impact.FACTOR_SUBSET_SHA256,
             boundary="paper_statement_and_digital_delivery_comparison_not_established"
                 if self.product == Product.PAPERLESS_BANKING else "CO2e: " + uk_impact.BOUNDARY,
            assumptions=("Synthetic Customer360 data; forecast assumptions must be explicit.",
                         "2026 UK factors held constant; this is not a measured historical reduction.",
                         "Source annual activities are held constant for the annual forecast comparison.",
                         *((f"Electricity baseline is an estimated annual forecast from {source.energy.electricity_months_present} completed available months; annualisation factor {source.energy.electricity_annualisation_factor}; not measured annual consumption.",)
                           if source and source.energy.electricity_is_estimated else ()),
                         *((f"Source snapshot generated at {source.generated_at.isoformat()}; feature version {source.feature_version}.",)
                           if source else ())),
             exclusions=("No conversion of CO2e to CO2 or inferred physical efficiencies.",
                         *(passport.get("limitations", ()) if passport else ()),
                         *((passport["limitation"],) if not_claimed else ())),
            method_version=passport["method_version"] if passport else uk_impact.METHOD_VERSION,
            method_release="reviewed-desnz-2026-subset", timestamp=self.clock(),
            evidence=evidence, issues=issues,
            secondary_metrics=tuple(SecondaryActivityMetric(
                name=key, value=Decimal(passport[key]), unit=unit,
                method_version=passport["method_version"],
                evidence_references=tuple(item.reference for item in evidence),
            ) for key, unit in (("paper_statements_avoided", "statements/year"),
                               ("paper_sheets_avoided", "sheets/year"))) if not_claimed else (),
        )

    def calculate_scoring(self, payload) -> ScoringImpactResult:
        """Numeric scoring view of the same explicit UK physical scenario."""
        source, cutoff, period, inputs, evidence, issues, passport, catalogue = self._prepare(payload)
        if source is None:
            raise ValueError("Scoring impact requires a valid customer snapshot and cutoff")
        available = passport is not None and passport["status"] != "NOT_CLAIMED" and not issues
        not_claimed = self.product == Product.PAPERLESS_BANKING and passport is not None and not issues
        return ScoringImpactResult(
            customer_id=source.customer_id, product=self.product,
            status=ImpactStatus.AVAILABLE if available else ImpactStatus.NOT_CLAIMED if not_claimed else ImpactStatus.UNAVAILABLE,
            metric="kg_co2e_per_year" if available else None, unit="kg CO2e/year" if available else None,
            baseline=float(passport["baseline_emissions"]) if available else None,
            scenario=float(passport["scenario_emissions"]) if available else None,
            estimated_reduction=float(passport["potential_reduction"]) if available else None,
            secondary_metrics=[ImpactMetric(name=key, value=float(passport[key]), unit=unit)
                for key, unit in (("paper_statements_avoided", "statements/year"), ("paper_sheets_avoided", "sheets/year"))] if not_claimed else [],
            methodology_id=passport.get("method", passport["method_version"]) if passport else None,
            method_version=passport["method_version"] if passport else uk_impact.METHOD_VERSION,
            factor_ids=list(passport["factor_records"]) if available else [],
            factor_source=catalogue["source_url"] if catalogue else None,
            factor_version=catalogue["version"] if catalogue else None,
            boundary=uk_impact.BOUNDARY if available else None,
            grid_scenario="2026 UK factors held constant" if available else None,
            assumptions=[ImpactAssumption(name=item.field, value=float(item.value) if isinstance(item.value, Decimal) else item.value,
                unit=item.unit, source=item.reference, is_estimated=True) for item in evidence],
            unavailable_reason="; ".join(f"{issue.code}: {issue.field}: {issue.message}" for issue in issues) or None,
            data_cutoff=source.feature_cutoff, calculation_timestamp=self.clock(),
            carbon_engine_version="reviewed-desnz-2026-subset:" + uk_impact.FACTOR_SUBSET_SHA256,
        )


def build_uk_registry(*, clock=utc_now):
    return {product: UKImpactCalculator(product, clock=clock) for product in Product}
