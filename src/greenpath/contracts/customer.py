"""CustomerSnapshot: the governed Customer 360 view at a feature cutoff."""

from datetime import date, datetime

from pydantic import Field, model_serializer

from greenpath.contracts.base import CONTRACT_VERSION, Contract, Probability
from greenpath.contracts.enums import FuelType, HeatingType
from greenpath.contracts.lifecycle import SourceUpdateRequest

FeatureScalar = float | int | bool | str | None


class VehicleFacts(Contract):
    has_vehicle: bool | None = None
    fuel_type: FuelType | None = None
    vehicle_age_years: float | None = Field(default=None, ge=0)
    annual_mileage_km: float | None = Field(default=None, ge=0)
    mileage_is_estimated: bool = False
    record_updated_at: date | None = None
    has_vehicle_finance: bool | None = None
    state_effective_at: date | None = None


class HomeFacts(Contract):
    home_owner: bool | None = None
    has_mortgage: bool | None = None
    mortgage_tenure_months: int | None = Field(default=None, ge=0)
    has_existing_solar: bool | None = None
    heating_type: HeatingType | None = None
    property_type: str | None = None
    region: str | None = None


class EnergyFacts(Contract):
    """Annualised household energy from observed months, not necessarily metered 12m totals."""

    electricity_kwh_12m: float | None = Field(default=None, ge=0)
    gas_kwh_12m: float | None = Field(default=None, ge=0)
    energy_months_present: int = Field(default=0, ge=0, le=12)
    electricity_trend: float | None = None  # last-3m avg / 12m avg - 1
    electricity_months_present: int | None = Field(default=None, ge=0, le=12)
    gas_months_present: int | None = Field(default=None, ge=0, le=12)
    electricity_kwh_observed: float | None = Field(default=None, ge=0)
    gas_kwh_observed: float | None = Field(default=None, ge=0)
    electricity_annualisation_factor: float | None = Field(default=None, ge=1)
    gas_annualisation_factor: float | None = Field(default=None, ge=1)
    electricity_is_estimated: bool | None = None
    gas_is_estimated: bool | None = None


class DigitalFacts(Contract):
    is_paperless: bool | None = None
    paper_statements_3m: int | None = Field(default=None, ge=0)
    paper_statements_12m: int | None = Field(default=None, ge=0)
    digital_statement_ratio: Probability | None = None
    digital_transactions_3m_avg: float | None = Field(default=None, ge=0)
    branch_visits_3m: int | None = Field(default=None, ge=0)
    paperless_effective_at: date | None = None
    paper_statements_post_paperless_3m: int | None = Field(default=None, ge=0)


class SpendFacts(Contract):
    """Aggregated categorised transaction spend in GBP (debits only).

    ``None`` means no transaction history at the cutoff (unknown), never zero spend.
    """

    fuel_spend_90d_monthly_avg: float | None = Field(default=None, ge=0)
    fuel_txn_frequency_90d: int | None = Field(default=None, ge=0)
    electricity_spend_90d_monthly_avg: float | None = Field(default=None, ge=0)
    gas_spend_90d_monthly_avg: float | None = Field(default=None, ge=0)
    utilities_spend_90d_monthly_avg: float | None = Field(default=None, ge=0)
    home_improvement_spend_12m: float | None = Field(default=None, ge=0)
    utility_spend_trend: float | None = None  # combined energy/utility 90d vs 12m ratio - 1
    fuel_txn_count_post_vehicle_state_90d: int | None = Field(default=None, ge=0)
    fuel_spend_post_vehicle_state_90d: float | None = Field(default=None, ge=0)


class DataQualityEvidence(Contract):
    transaction_months_observed: int = Field(ge=0)
    first_transaction_date: date | None = None
    last_transaction_date: date | None = None
    vehicle_record_age_days: int | None = Field(default=None, ge=0)
    energy_months_present: int = Field(default=0, ge=0, le=12)
    digital_months_present: int = Field(default=0, ge=0, le=12)
    missing_fields: list[str] = Field(default_factory=list)
    estimated_fields: list[str] = Field(default_factory=list)
    invalid_product_records: int = Field(default=0, ge=0)


class CustomerSnapshot(Contract):
    """Point-in-time customer view.

    ``features`` is the approved propensity feature view and is the single input
    used for model scoring. The typed fact groups are display/impact/guardrail
    views of the same data. Audit-only attributes (age band, income band) are never
    present here.
    """

    contract_version: str = CONTRACT_VERSION
    customer_id: str
    feature_cutoff: date
    generated_at: datetime
    feature_version: str
    segment: str | None = None
    vehicle: VehicleFacts
    home: HomeFacts
    energy: EnergyFacts
    digital: DigitalFacts
    spend: SpendFacts
    features: dict[str, FeatureScalar]
    data_quality: DataQualityEvidence
    source_versions: dict[str, str] = Field(default_factory=dict)
    source_events: tuple[SourceUpdateRequest, ...] = ()

    @model_serializer(mode="wrap")
    def preserve_shipped_source_payload(self, handler):
        payload = handler(self)
        for field in ("source_versions", "source_events"):
            if not payload.get(field):
                payload.pop(field, None)
        # These optional facts were absent from shipped snapshots; retain their wire shape.
        for group, fields in {
            "vehicle": ("state_effective_at",),
            "digital": ("paperless_effective_at", "paper_statements_post_paperless_3m"),
            "spend": ("fuel_txn_count_post_vehicle_state_90d", "fuel_spend_post_vehicle_state_90d"),
            "energy": tuple(f"{fuel}_{suffix}" for fuel in ("electricity", "gas") for suffix in
                            ("months_present", "kwh_observed", "annualisation_factor", "is_estimated")),
        }.items():
            for field in fields:
                if payload[group].get(field) is None:
                    payload[group].pop(field, None)
        return payload
