"""Shared evidence validation and construction of the common impact result."""

from calendar import monthrange
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Context, Decimal, ROUND_HALF_UP, localcontext
from typing import Callable, Mapping

from pydantic import BaseModel, ValidationError

from greenr.contracts.impact_detail import (
    ActivityEvidence, EmissionsScenario, FactorReference, ImpactIssue, ImpactResult,
    ImpactStatus, IssueCode, Product,
)
from .catalogue import CATALOGUE_SHA256, CATALOGUE_VERSION, GRID_FACTOR, METHOD_RELEASE, FactorCatalogue
from .inputs import EvidenceBasis, Fact, Freshness, ImpactContext, ImpactInput, Quantity, SolarInterval

Payload = Mapping[str, object] | BaseModel | None
Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class Method:
    product: Product
    version: str
    boundary: str
    baseline_description: str
    scenario_description: str
    exclusions: tuple[str, ...]
    assumptions: tuple[str, ...] = ()


def display_value(result: ImpactResult) -> Decimal | None:
    """Round for presentation only; the result always keeps unrounded values."""
    if result.value is None:
        return None
    with localcontext(Context(prec=60)):
        return result.value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


@dataclass
class Preparation:
    method: Method
    catalogue: FactorCatalogue
    timestamp: datetime
    request: ImpactInput | None = None
    context: ImpactContext | None = None
    grid_value: Decimal | None = None
    issues: list[ImpactIssue] = field(default_factory=list)
    factors: list[FactorReference] = field(default_factory=list)
    evidence: list[ActivityEvidence] = field(default_factory=list)

    def issue(self, code: IssueCode, field: str, message: str):
        self.issues.append(ImpactIssue(code=code, field=field, message=message))

    def factor(self, factor_id: str, unit: str) -> Decimal | None:
        factor, issue = self.catalogue.require(factor_id, unit)
        if issue:
            self.issues.append(issue)
            return None
        if factor not in self.factors:
            self.factors.append(factor)
        return factor.value

    def unit(self, quantity: Quantity | None, unit: str, name: str):
        if quantity is not None and quantity.unit != unit:
            self.issue(IssueCode.INVALID_INPUT, name + ".unit", f"Required unit is {unit}")

    def expect(self, fact: Fact, value: object, name: str,
               code: IssueCode = IssueCode.UNSUPPORTED_SCOPE):
        if fact.value != value:
            self.issue(code, name, f"This method requires {name} to be {value!r}")

    def finish(self, baseline: Decimal | None = None, scenario: Decimal | None = None,
               assumptions: tuple[str, ...] = ()) -> ImpactResult:
        available = not self.issues and baseline is not None and scenario is not None
        if not available and not self.issues:
            self.issue(IssueCode.MISSING_INPUT, "activity", "Supply the required activity evidence")
        context = self.context
        units = "kg CO2"
        if context:
            start, end = context.period.start, context.period.end
            if start.year < 9999:
                anniversary = date(start.year + 1, start.month,
                                   min(start.day, monthrange(start.year + 1, start.month)[1]))
                if end == anniversary:
                    units = "kg CO2/year"
        with localcontext(Context(prec=60)):
            value = baseline - scenario if available else None
        estimates = tuple(e.field for e in self.evidence if e.basis != EvidenceBasis.METER_READING)
        common_assumptions = (
            "Synthetic demo; this is a scenario comparison, not a verified reduction.",
            "Historical FY2022-23 national grid average held constant across both scenarios.",
            "Operational CO2 only; not a lifecycle or CO2e estimate.",
        ) if self.factors else ()
        if estimates:
            common_assumptions += ("Declared, forecast or synthetic inputs: " + ", ".join(estimates),)
        return ImpactResult(
            product=self.method.product,
            status=ImpactStatus.AVAILABLE if available else ImpactStatus.UNAVAILABLE,
            value=value, units=units,
            baseline=EmissionsScenario(description=self.method.baseline_description,
                                       emissions_kg_co2=baseline if available else None),
            scenario=EmissionsScenario(description=self.method.scenario_description,
                                       emissions_kg_co2=scenario if available else None),
            period=context.period if context else None,
            feature_cutoff=context.feature_cutoff if context else None,
            synthetic_demo=context.synthetic_demo if context else None,
            factors=tuple(self.factors),
            factor_catalogue_version=CATALOGUE_VERSION,
            factor_catalogue_sha256=CATALOGUE_SHA256,
            boundary=self.method.boundary,
            assumptions=common_assumptions + self.method.assumptions + assumptions,
            exclusions=self.method.exclusions,
            method_version=self.method.version,
            method_release=METHOD_RELEASE,
            timestamp=self.timestamp,
            evidence=tuple(self.evidence), issues=tuple(self.issues),
        )


def _validation_issues(prepared: Preparation, errors: ValidationError):
    for error in errors.errors(include_input=False, include_context=False, include_url=False):
        location = ".".join(str(part) for part in error["loc"]) or "input"
        code = IssueCode.MISSING_INPUT if error["type"] == "missing" else IssueCode.INVALID_INPUT
        prepared.issue(code, location, error["msg"])


def prepare(payload: Payload, input_type: type[ImpactInput], method: Method,
            catalogue: FactorCatalogue, clock: Clock, *, needs_grid: bool = True) -> Preparation:
    prepared = Preparation(method, catalogue, clock())
    if needs_grid:
        prepared.grid_value = prepared.factor(GRID_FACTOR, "kg CO2/kWh")
    raw = payload.model_dump(warnings=False) if isinstance(payload, BaseModel) else payload
    try:
        # Revalidate typed inputs too, including objects built with model_construct.
        prepared.request = input_type.model_validate(raw if raw is not None else {})
        prepared.context = prepared.request.context
    except ValidationError as exc:
        _validation_issues(prepared, exc)
        # Keep valid context even when an independent activity field is malformed.
        if isinstance(raw, Mapping):
            try:
                prepared.context = ImpactContext.model_validate(raw.get("context"))
            except ValidationError:
                pass
    context = prepared.context
    if context:
        if context.geography != "IN":
            prepared.issue(IssueCode.UNSUPPORTED_SCOPE, "context.geography", "Only the Indian grid is supported")
        if not context.synthetic_demo:
            prepared.issue(IssueCode.UNSUPPORTED_SCOPE, "context.synthetic_demo",
                           "The historical CEA factor is approved for the synthetic demo only")
    if prepared.request:
        _collect_evidence(prepared.request, "", context.period, prepared)
    return prepared


def _collect_evidence(node, path, expected_period, prepared):
    if isinstance(node, Fact):
        evidence = node.evidence
        prepared.evidence.append(ActivityEvidence(
            field=path, value=node.value,
            unit=node.unit if isinstance(node, Quantity) else None,
            reference=evidence.reference, basis=evidence.basis,
            observed_at=evidence.observed_at, period=evidence.period,
            freshness=evidence.freshness, conflicts=evidence.conflicts,
        ))
        if evidence.period != expected_period:
            prepared.issue(IssueCode.INCOMPARABLE_BASELINE, path + ".evidence.period",
                           "Evidence must cover its exact comparison period or solar interval")
        if evidence.observed_at > prepared.context.feature_cutoff:
            prepared.issue(IssueCode.INVALID_INPUT, path + ".evidence.observed_at",
                           "Evidence was observed after the feature cutoff")
        if evidence.freshness != Freshness.CURRENT:
            prepared.issue(IssueCode.STALE_INPUT, path + ".evidence.freshness",
                           "Supply an approved current freshness assessment")
        if evidence.conflicts:
            prepared.issue(IssueCode.CONFLICTING_INPUT, path + ".evidence.conflicts",
                           "Resolve conflicting evidence: " + "; ".join(evidence.conflicts))
        if (evidence.basis in {EvidenceBasis.METER_READING, EvidenceBasis.CUSTOMER_DECLARATION}
                and evidence.period.end > evidence.observed_at.date()):
            prepared.issue(IssueCode.INVALID_INPUT, path + ".evidence.basis",
                           "Future activity requires a forecast or synthetic basis")
        return
    if isinstance(node, SolarInterval):
        expected_period = node.period
    if isinstance(node, BaseModel):
        for name in type(node).model_fields:
            child = getattr(node, name)
            _collect_evidence(child, f"{path}.{name}" if path else name, expected_period, prepared)
    elif isinstance(node, tuple):
        for index, child in enumerate(node):
            _collect_evidence(child, f"{path}.{index}", expected_period, prepared)
