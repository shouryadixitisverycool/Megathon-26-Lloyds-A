"""Trust tests: evidence quality, cross-source conflicts and the TrustScorer provider."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from greenr import config


from greenr.contracts import (
    CustomerSnapshot,
    DataQualityEvidence,
    DigitalFacts,
    EnergyFacts,
    FuelType,
    HeatingType,
    HomeFacts,
    Product,
    Severity,
    SpendFacts,
    TrustAssessment,
    TrustIssueCategory,
    TrustIssueCode,
    TrustStatus,
    VehicleFacts,
)
from greenr.ports import TrustProvider
from greenr.trust.conflicts import (
    RECURRING_FUEL_MONTHLY_GBP,
    RECURRING_FUEL_TXN_MIN,
    cross_source_consistency,
    detect_conflicts,
    has_high_conflict,
)
from greenr.trust.ood import OODDetector
from greenr.trust.provider import (
    TRUST_FRAME_COLUMNS,
    TrustScorer,
    TrustThresholds,
    TrustWeights,
    trust_frame,
)
from greenr.trust.quality import (
    completeness,
    critical_fields_present,
    freshness,
    quality_issues,
)

CUTOFF = date(2026, 6, 30)
GENERATED = datetime(2026, 10, 10, 9, 0)

ALL_PRODUCTS = list(Product)


def make_snapshot(
    customer_id: str = "C10001",
    *,
    months_observed: int = 24,
    last_txn_days_before_cutoff: int | None = 5,
    has_vehicle: bool | None = True,
    fuel_type: FuelType | None = FuelType.PETROL,
    vehicle_record_age_days: int | None = 120,
    mileage_km: float | None = 12000.0,
    mileage_estimated: bool = False,
    vehicle_age_years: float | None = 4.0,
    fuel_txn_freq_90d: int | None = 4,
    fuel_spend_90d_avg: float | None = 110.0,
    home_owner: bool | None = True,
    has_mortgage: bool | None = True,
    energy_months: int = 12,
    electricity_kwh_12m: float | None = 3200.0,
    gas_kwh_12m: float | None = 9000.0,
    heating_type: HeatingType | None = HeatingType.GAS_BOILER,
    region: str | None = "London",
    property_type: str | None = "SEMI_DETACHED",
    has_existing_solar: bool | None = False,
    is_paperless: bool | None = False,
    digital_months: int = 12,
    paper_statements_3m: int | None = 0,
    digital_txn_3m_avg: float | None = 20.0,
    invalid_product_records: int = 0,
    estimated_fields: list[str] | None = None,
) -> CustomerSnapshot:
    """A customer snapshot at the canonical cutoff. Defaults describe a rich, clean customer."""

    def flag(value: bool | None) -> float | None:
        return None if value is None else float(value)

    last_txn = None if last_txn_days_before_cutoff is None else CUTOFF - timedelta(days=last_txn_days_before_cutoff)
    record_updated = None if vehicle_record_age_days is None else CUTOFF - timedelta(days=vehicle_record_age_days)
    features = {
        "has_vehicle": flag(has_vehicle),
        "txn_months_observed": float(months_observed),
        "annual_mileage_km": mileage_km,
        "vehicle_age_years": vehicle_age_years,
        "fuel_txn_freq_90d": None if fuel_txn_freq_90d is None else float(fuel_txn_freq_90d),
        "fuel_spend_90d_avg": fuel_spend_90d_avg,
        "home_owner": flag(home_owner),
        "has_mortgage": flag(has_mortgage),
        "has_existing_solar": flag(has_existing_solar),
        "electricity_kwh_12m": electricity_kwh_12m,
        "gas_kwh_12m": gas_kwh_12m,
        "energy_months_present": float(energy_months),
        "is_paperless": flag(is_paperless),
        "paper_statements_3m": None if paper_statements_3m is None else float(paper_statements_3m),
        "digital_txn_3m_avg": digital_txn_3m_avg,
        "digital_months_present": float(digital_months),
    }
    return CustomerSnapshot(
        customer_id=customer_id,
        feature_cutoff=CUTOFF,
        generated_at=GENERATED,
        feature_version="feature_v1",
        segment="MASS",
        vehicle=VehicleFacts(
            has_vehicle=has_vehicle,
            fuel_type=fuel_type,
            vehicle_age_years=vehicle_age_years,
            annual_mileage_km=mileage_km,
            mileage_is_estimated=mileage_estimated,
            record_updated_at=record_updated,
        ),
        home=HomeFacts(
            home_owner=home_owner,
            has_mortgage=has_mortgage,
            has_existing_solar=has_existing_solar,
            heating_type=heating_type,
            property_type=property_type,
            region=region,
        ),
        energy=EnergyFacts(
            electricity_kwh_12m=electricity_kwh_12m,
            gas_kwh_12m=gas_kwh_12m,
            energy_months_present=energy_months,
        ),
        digital=DigitalFacts(
            is_paperless=is_paperless,
            paper_statements_3m=paper_statements_3m,
            digital_transactions_3m_avg=digital_txn_3m_avg,
        ),
        spend=SpendFacts(
            fuel_spend_90d_monthly_avg=fuel_spend_90d_avg or 0.0,
            fuel_txn_frequency_90d=int(fuel_txn_freq_90d or 0),
        ),
        features=features,
        data_quality=DataQualityEvidence(
            transaction_months_observed=months_observed,
            last_transaction_date=last_txn,
            vehicle_record_age_days=vehicle_record_age_days,
            energy_months_present=energy_months,
            digital_months_present=digital_months,
            estimated_fields=estimated_fields or [],
            invalid_product_records=invalid_product_records,
        ),
    )


OOD_FEATURES = [
    "annual_mileage_km",
    "vehicle_age_years",
    "fuel_spend_90d_avg",
    "fuel_txn_freq_90d",
    "electricity_kwh_12m",
    "gas_kwh_12m",
    "digital_txn_3m_avg",
    "paper_statements_3m",
    "txn_months_observed",
]


def make_population(n: int, seed: int) -> list[CustomerSnapshot]:
    """Random but plausible customers spanning the OOD feature ranges (some values missing)."""
    rng = np.random.default_rng(seed)
    snapshots = []
    for i in range(n):
        mileage = float(max(rng.normal(12000, 3000), 500))
        snapshots.append(make_snapshot(
            f"P{i:05d}",
            months_observed=int(rng.integers(6, 25)),
            last_txn_days_before_cutoff=int(rng.integers(0, 60)),
            vehicle_record_age_days=int(rng.integers(0, 700)),
            mileage_km=None if rng.random() < 0.05 else mileage,
            vehicle_age_years=float(rng.uniform(0, 12)),
            fuel_txn_freq_90d=int(rng.poisson(4)),
            fuel_spend_90d_avg=float(max(rng.normal(100, 30), 0.0)),
            electricity_kwh_12m=float(max(rng.normal(3200, 800), 0.0)),
            gas_kwh_12m=float(max(rng.normal(9000, 2500), 0.0)),
            digital_txn_3m_avg=float(max(rng.normal(20, 6), 0.0)),
            paper_statements_3m=int(rng.poisson(0.5)),
        ))
    return snapshots


def ood_frame(snapshots: list[CustomerSnapshot]) -> pd.DataFrame:
    return pd.DataFrame(
        [[s.features[name] for name in OOD_FEATURES] for s in snapshots],
        columns=OOD_FEATURES,
    ).astype("float64")


@pytest.fixture(scope="module")
def ev_detector() -> OODDetector:
    return OODDetector().fit(ood_frame(make_population(1500, seed=7)))


def codes(assessment: TrustAssessment) -> set[TrustIssueCode]:
    return {issue.code for issue in assessment.issues}


def issue_for(issues, code: TrustIssueCode):
    matches = [issue for issue in issues if issue.code is code]
    assert len(matches) == 1, f"expected exactly one {code}, got {len(matches)}"
    return matches[0]


# ---------------------------------------------------------------------------
# Quality: completeness, critical fields, freshness
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("product", ALL_PRODUCTS)
def test_rich_customer_is_complete_and_fresh(product: Product) -> None:
    snapshot = make_snapshot()
    assert completeness(snapshot, product) == 1.0
    assert critical_fields_present(snapshot, product)
    assert quality_issues(snapshot, product) == []
    assert freshness(snapshot, product) >= 0.9


def test_completeness_counts_missing_fields() -> None:
    # GREEN_HOME has 6 applicable fields; heating_type and has_mortgage missing -> 4/6.
    snapshot = make_snapshot(heating_type=None, has_mortgage=None)
    assert completeness(snapshot, Product.GREEN_HOME) == pytest.approx(4 / 6)
    assert critical_fields_present(snapshot, Product.GREEN_HOME)


def test_missing_home_ownership_is_critical_for_solar_and_green_home() -> None:
    snapshot = make_snapshot(home_owner=None)
    for product in (Product.SOLAR_FINANCE, Product.GREEN_HOME):
        assert not critical_fields_present(snapshot, product)
        issue = issue_for(quality_issues(snapshot, product), TrustIssueCode.HOME_OWNERSHIP_UNKNOWN)
        assert issue.category is TrustIssueCategory.CRITICAL_FIELD
        assert issue.severity is Severity.HIGH
    # Home ownership is irrelevant to EV Finance and Paperless Banking.
    assert critical_fields_present(snapshot, Product.EV_FINANCE)
    assert critical_fields_present(snapshot, Product.PAPERLESS_BANKING)


def test_short_history_severity_bands() -> None:
    poor = issue_for(quality_issues(make_snapshot(months_observed=2), Product.EV_FINANCE),
                     TrustIssueCode.SHORT_TRANSACTION_HISTORY)
    assert poor.severity is Severity.HIGH
    assert poor.category is TrustIssueCategory.FRESHNESS
    short = issue_for(quality_issues(make_snapshot(months_observed=4), Product.GREEN_HOME),
                      TrustIssueCode.SHORT_TRANSACTION_HISTORY)
    assert short.severity is Severity.MEDIUM
    assert not any(
        i.code is TrustIssueCode.SHORT_TRANSACTION_HISTORY
        for i in quality_issues(make_snapshot(months_observed=6), Product.EV_FINANCE)
    )


def test_stale_vehicle_record_is_flagged_only_for_ev() -> None:
    snapshot = make_snapshot(vehicle_record_age_days=800)
    issue = issue_for(quality_issues(snapshot, Product.EV_FINANCE), TrustIssueCode.VEHICLE_RECORD_STALE)
    assert issue.severity is Severity.MEDIUM
    assert issue.category is TrustIssueCategory.FRESHNESS
    assert TrustIssueCode.VEHICLE_RECORD_STALE not in {
        i.code for i in quality_issues(snapshot, Product.GREEN_HOME)
    }
    assert freshness(snapshot, Product.EV_FINANCE) < freshness(make_snapshot(), Product.EV_FINANCE)


def test_estimated_mileage_is_low_severity_and_lowers_freshness() -> None:
    observed = make_snapshot()
    estimated = make_snapshot(mileage_estimated=True)
    issue = issue_for(quality_issues(estimated, Product.EV_FINANCE), TrustIssueCode.MILEAGE_ESTIMATED)
    assert issue.severity is Severity.LOW
    assert freshness(estimated, Product.EV_FINANCE) == pytest.approx(
        freshness(observed, Product.EV_FINANCE) - 0.15
    )


def test_missing_mileage_is_reported_and_reduces_completeness() -> None:
    snapshot = make_snapshot(mileage_km=None)
    issue = issue_for(quality_issues(snapshot, Product.EV_FINANCE), TrustIssueCode.MILEAGE_MISSING)
    assert issue.category is TrustIssueCategory.COMPLETENESS
    assert completeness(snapshot, Product.EV_FINANCE) == pytest.approx(4 / 5)


def test_missing_vehicle_record_is_critical_for_ev() -> None:
    snapshot = make_snapshot(has_vehicle=None, fuel_type=None, mileage_km=None, vehicle_record_age_days=None)
    assert not critical_fields_present(snapshot, Product.EV_FINANCE)
    issue = issue_for(quality_issues(snapshot, Product.EV_FINANCE), TrustIssueCode.VEHICLE_RECORD_MISSING)
    assert issue.category is TrustIssueCategory.CRITICAL_FIELD
    assert issue.severity is Severity.HIGH


def test_known_non_vehicle_owner_is_not_penalised_for_vehicle_fields() -> None:
    snapshot = make_snapshot(has_vehicle=False, fuel_type=None, mileage_km=None,
                             vehicle_age_years=None, vehicle_record_age_days=None)
    assert critical_fields_present(snapshot, Product.EV_FINANCE)
    assert completeness(snapshot, Product.EV_FINANCE) == 1.0
    assert quality_issues(snapshot, Product.EV_FINANCE) == []


def test_partial_energy_history_is_incomplete_not_missing() -> None:
    issues = quality_issues(make_snapshot(energy_months=6), Product.GREEN_HOME)
    issue = issue_for(issues, TrustIssueCode.ENERGY_RECORDS_INCOMPLETE)
    assert issue.severity is Severity.MEDIUM
    assert critical_fields_present(make_snapshot(energy_months=6), Product.GREEN_HOME)


def test_no_energy_records_is_critical_for_green_home() -> None:
    snapshot = make_snapshot(energy_months=0, electricity_kwh_12m=None, gas_kwh_12m=None)
    assert not critical_fields_present(snapshot, Product.GREEN_HOME)
    issue = issue_for(quality_issues(snapshot, Product.GREEN_HOME), TrustIssueCode.ENERGY_RECORDS_MISSING)
    assert issue.category is TrustIssueCategory.CRITICAL_FIELD


def test_solar_needs_electricity_and_region() -> None:
    no_electricity = make_snapshot(electricity_kwh_12m=None)
    issue = issue_for(quality_issues(no_electricity, Product.SOLAR_FINANCE), TrustIssueCode.ENERGY_RECORDS_MISSING)
    assert issue.severity is Severity.HIGH
    assert not critical_fields_present(no_electricity, Product.SOLAR_FINANCE)

    no_region = make_snapshot(region=None)
    issue = issue_for(quality_issues(no_region, Product.SOLAR_FINANCE), TrustIssueCode.REGION_MISSING)
    assert issue.category is TrustIssueCategory.CRITICAL_FIELD
    assert not critical_fields_present(no_region, Product.SOLAR_FINANCE)


def test_no_digital_records_is_critical_for_paperless() -> None:
    snapshot = make_snapshot(digital_months=0, paper_statements_3m=None, digital_txn_3m_avg=None)
    assert not critical_fields_present(snapshot, Product.PAPERLESS_BANKING)
    issue = issue_for(quality_issues(snapshot, Product.PAPERLESS_BANKING), TrustIssueCode.DIGITAL_RECORDS_MISSING)
    assert issue.severity is Severity.HIGH


# ---------------------------------------------------------------------------
# Conflicts (spec 17.3)
# ---------------------------------------------------------------------------


def test_ev_recurring_fuel_conflict_fires_for_ev_only() -> None:
    snapshot = make_snapshot(fuel_type=FuelType.EV, fuel_txn_freq_90d=RECURRING_FUEL_TXN_MIN + 2,
                             fuel_spend_90d_avg=RECURRING_FUEL_MONTHLY_GBP + 90)
    found = detect_conflicts(snapshot, Product.EV_FINANCE)
    assert [i.code for i in found] == [TrustIssueCode.EV_RECORD_WITH_RECURRING_FUEL_SPEND]
    assert found[0].severity is Severity.HIGH
    assert found[0].category is TrustIssueCategory.CONFLICT
    assert detect_conflicts(snapshot, Product.GREEN_HOME) == []


@pytest.mark.parametrize("snapshot", [
    make_snapshot(fuel_type=FuelType.EV, fuel_txn_freq_90d=RECURRING_FUEL_TXN_MIN - 1, fuel_spend_90d_avg=150.0),
    make_snapshot(fuel_type=FuelType.EV, fuel_txn_freq_90d=5, fuel_spend_90d_avg=RECURRING_FUEL_MONTHLY_GBP),
    make_snapshot(fuel_type=FuelType.EV, fuel_txn_freq_90d=None, fuel_spend_90d_avg=None),
    make_snapshot(fuel_type=FuelType.PETROL, fuel_txn_freq_90d=6, fuel_spend_90d_avg=300.0),
    make_snapshot(has_vehicle=None, fuel_type=None, fuel_txn_freq_90d=6, fuel_spend_90d_avg=300.0),
])
def test_ev_recurring_fuel_conflict_does_not_fire_on_clean_data(snapshot: CustomerSnapshot) -> None:
    assert detect_conflicts(snapshot, Product.EV_FINANCE) == []


@pytest.mark.parametrize("product", [Product.SOLAR_FINANCE, Product.GREEN_HOME])
def test_non_owner_with_mortgage_conflict(product: Product) -> None:
    found = detect_conflicts(make_snapshot(home_owner=False, has_mortgage=True), product)
    assert [i.code for i in found] == [TrustIssueCode.NON_OWNER_WITH_ACTIVE_MORTGAGE]
    assert found[0].severity is Severity.HIGH


@pytest.mark.parametrize("snapshot", [
    make_snapshot(home_owner=True, has_mortgage=True),
    make_snapshot(home_owner=False, has_mortgage=False),
    make_snapshot(home_owner=None, has_mortgage=True),
])
def test_non_owner_with_mortgage_conflict_does_not_fire_on_clean_data(snapshot: CustomerSnapshot) -> None:
    assert detect_conflicts(snapshot, Product.SOLAR_FINANCE) == []
    assert detect_conflicts(snapshot, Product.GREEN_HOME) == []


def test_paperless_flag_with_paper_statements_conflict() -> None:
    snapshot = make_snapshot(is_paperless=True, paper_statements_3m=2)
    found = detect_conflicts(snapshot, Product.PAPERLESS_BANKING)
    assert [i.code for i in found] == [TrustIssueCode.PAPERLESS_FLAG_WITH_PAPER_STATEMENTS]
    assert found[0].severity is Severity.HIGH


@pytest.mark.parametrize("snapshot", [
    make_snapshot(is_paperless=True, paper_statements_3m=0),
    make_snapshot(is_paperless=False, paper_statements_3m=3),
    make_snapshot(is_paperless=None, paper_statements_3m=3),
])
def test_paperless_conflict_does_not_fire_on_clean_data(snapshot: CustomerSnapshot) -> None:
    assert detect_conflicts(snapshot, Product.PAPERLESS_BANKING) == []


@pytest.mark.parametrize("product", ALL_PRODUCTS)
def test_invalid_product_record_conflict_applies_to_every_product(product: Product) -> None:
    found = detect_conflicts(make_snapshot(invalid_product_records=1), product)
    assert [i.code for i in found] == [TrustIssueCode.INVALID_PRODUCT_RECORD]
    assert found[0].severity is Severity.HIGH
    assert detect_conflicts(make_snapshot(), product) == []


def test_consistency_is_one_minus_severity_weighted_penalty() -> None:
    def conflict(severity: Severity):
        return detect_conflicts(make_snapshot(invalid_product_records=1), Product.EV_FINANCE)[0].model_copy(
            update={"severity": severity})

    assert cross_source_consistency([]) == 1.0
    assert cross_source_consistency([conflict(Severity.HIGH)]) == pytest.approx(0.5)
    assert cross_source_consistency([conflict(Severity.HIGH), conflict(Severity.MEDIUM)]) == pytest.approx(0.25)
    assert cross_source_consistency([conflict(Severity.LOW)]) == pytest.approx(0.9)
    assert cross_source_consistency([conflict(Severity.HIGH)] * 3) == 0.0
    assert has_high_conflict([conflict(Severity.HIGH)])
    assert not has_high_conflict([conflict(Severity.LOW)])


# ---------------------------------------------------------------------------
# TrustScorer
# ---------------------------------------------------------------------------


def test_scorer_satisfies_trust_provider_protocol() -> None:
    assert isinstance(TrustScorer(), TrustProvider)


def test_rich_customer_gets_high_trust() -> None:
    assessment = TrustScorer().assess(make_snapshot(), Product.EV_FINANCE)
    assert assessment.status is TrustStatus.HIGH
    assert assessment.score >= 0.8
    assert assessment.issues == []
    assert assessment.critical_fields_present
    assert assessment.cross_source_consistency == 1.0
    assert assessment.ood_score == 0.0


def test_short_history_and_stale_vehicle_give_low_trust() -> None:
    # Spec 15.2 second example: two months of transactions and a stale vehicle record.
    snapshot = make_snapshot(months_observed=2, last_txn_days_before_cutoff=10, vehicle_record_age_days=800)
    assessment = TrustScorer().assess(snapshot, Product.EV_FINANCE)
    assert assessment.status is TrustStatus.LOW
    assert assessment.score <= 0.5
    assert {TrustIssueCode.SHORT_TRANSACTION_HISTORY, TrustIssueCode.VEHICLE_RECORD_STALE} <= codes(assessment)
    assert assessment.critical_fields_present


def test_unknown_home_ownership_makes_solar_insufficient() -> None:
    # Spec 15.2 second example: home ownership unknown -> recommendation suspended.
    snapshot = make_snapshot(home_owner=None, months_observed=2, vehicle_record_age_days=800)
    assessment = TrustScorer().assess(snapshot, Product.SOLAR_FINANCE)
    assert assessment.status is TrustStatus.INSUFFICIENT
    assert assessment.score <= 0.4
    assert not assessment.critical_fields_present
    assert TrustIssueCode.HOME_OWNERSHIP_UNKNOWN in codes(assessment)


def test_critical_missing_forces_insufficient_even_with_high_other_components() -> None:
    # Only region is missing: completeness 0.8, freshness/consistency/OOD are all high, so the
    # raw score would be about 0.94. The critical-field gate must still force INSUFFICIENT at 0.4.
    snapshot = make_snapshot(region=None)
    assessment = TrustScorer().assess(snapshot, Product.SOLAR_FINANCE)
    assert assessment.completeness == pytest.approx(0.8)
    assert assessment.freshness == pytest.approx(1.0)
    assert assessment.status is TrustStatus.INSUFFICIENT
    assert assessment.score == pytest.approx(0.4)
    assert TrustIssueCode.REGION_MISSING in codes(assessment)


def test_high_conflict_caps_status_at_low() -> None:
    snapshot = make_snapshot(fuel_type=FuelType.EV, fuel_txn_freq_90d=6, fuel_spend_90d_avg=250.0)
    assessment = TrustScorer().assess(snapshot, Product.EV_FINANCE)
    assert assessment.has_high_severity_conflict
    assert assessment.status is TrustStatus.LOW
    assert assessment.score <= 0.5
    assert TrustIssueCode.EV_RECORD_WITH_RECURRING_FUEL_SPEND in codes(assessment)


def test_high_severity_evidence_issue_caps_status_at_low() -> None:
    assessment = TrustScorer().assess(make_snapshot(months_observed=1), Product.GREEN_HOME)
    assert assessment.status is TrustStatus.LOW
    assert assessment.score <= 0.5


def test_no_detector_gives_zero_ood_score_and_no_ood_issue() -> None:
    assessment = TrustScorer().assess(make_snapshot(), Product.SOLAR_FINANCE)
    assert assessment.ood_score == 0.0
    assert TrustIssueCode.OUT_OF_DISTRIBUTION not in codes(assessment)


def test_extreme_customer_is_out_of_distribution_and_capped(ev_detector: OODDetector) -> None:
    scorer = TrustScorer({Product.EV_FINANCE: ev_detector})
    extreme = make_snapshot(mileage_km=95000.0, fuel_spend_90d_avg=2400.0)
    assessment = scorer.assess(extreme, Product.EV_FINANCE)
    issue = issue_for(assessment.issues, TrustIssueCode.OUT_OF_DISTRIBUTION)
    assert issue.category is TrustIssueCategory.OOD
    assert issue.severity is Severity.HIGH
    assert assessment.ood_score >= 0.99
    assert assessment.score <= 0.4
    assert assessment.status in (TrustStatus.LOW, TrustStatus.INSUFFICIENT)


def test_typical_customer_is_not_out_of_distribution(ev_detector: OODDetector) -> None:
    scorer = TrustScorer({Product.EV_FINANCE: ev_detector})
    assessment = scorer.assess(make_snapshot(), Product.EV_FINANCE)
    assert TrustIssueCode.OUT_OF_DISTRIBUTION not in codes(assessment)
    assert assessment.ood_score < 0.99
    assert assessment.status is TrustStatus.HIGH


def test_assess_many_matches_assess(ev_detector: OODDetector) -> None:
    scorer = TrustScorer({Product.EV_FINANCE: ev_detector})
    snapshots = [
        make_snapshot("A1"),
        make_snapshot("A2", months_observed=2, vehicle_record_age_days=800),
        make_snapshot("A3", fuel_type=FuelType.EV, fuel_txn_freq_90d=6, fuel_spend_90d_avg=250.0),
        make_snapshot("A4", mileage_km=95000.0, fuel_spend_90d_avg=2400.0),
        make_snapshot("A5", has_vehicle=None, fuel_type=None, mileage_km=None),
    ]
    batch = scorer.assess_many(snapshots, Product.EV_FINANCE)
    assert len(batch) == len(snapshots)
    for snapshot, from_batch in zip(snapshots, batch, strict=True):
        single = scorer.assess(snapshot, Product.EV_FINANCE)
        assert from_batch.model_dump(exclude={"ood_score"}) == single.model_dump(exclude={"ood_score"})
        assert from_batch.ood_score == pytest.approx(single.ood_score, abs=1e-12)


def test_assess_many_empty_input() -> None:
    assert TrustScorer().assess_many([], Product.EV_FINANCE) == []


@pytest.mark.parametrize("product", ALL_PRODUCTS)
def test_outputs_validate_as_trust_assessment(product: Product) -> None:
    scorer = TrustScorer()
    snapshots = [make_snapshot("V1"), make_snapshot("V2", invalid_product_records=2, home_owner=None, region=None)]
    for assessment in scorer.assess_many(snapshots, product):
        assert isinstance(assessment, TrustAssessment)
        revalidated = TrustAssessment.model_validate(assessment.model_dump())
        assert revalidated == assessment
        for value in (assessment.score, assessment.completeness, assessment.freshness,
                      assessment.cross_source_consistency, assessment.ood_score):
            assert 0.0 <= value <= 1.0
        assert assessment.method_version == "trust_v1"
        assert assessment.assessed_at == config.PREDICTION_TIMESTAMP
        assert assessment.product is product


def test_assessed_at_follows_config_timestamp(monkeypatch: pytest.MonkeyPatch) -> None:
    stamp = datetime(2030, 1, 2, 3, 4)
    monkeypatch.setattr(config, "PREDICTION_TIMESTAMP", stamp)
    assert TrustScorer().assess(make_snapshot(), Product.GREEN_HOME).assessed_at == stamp


def test_trust_frame_summarises_assessments() -> None:
    scorer = TrustScorer()
    assessments = [
        scorer.assess(make_snapshot("T1"), Product.EV_FINANCE),
        scorer.assess(make_snapshot("T2", home_owner=None), Product.SOLAR_FINANCE),
    ]
    frame = trust_frame(assessments)
    assert list(frame.columns) == TRUST_FRAME_COLUMNS
    assert frame["customer_id"].tolist() == ["T1", "T2"]
    assert frame["product"].tolist() == ["EV_FINANCE", "SOLAR_FINANCE"]
    assert frame["status"].tolist() == ["HIGH", "INSUFFICIENT"]
    assert frame["critical_fields_present"].tolist() == [True, False]
    assert frame.loc[1, "issue_codes"] == "HOME_OWNERSHIP_UNKNOWN"
    assert frame["has_high_conflict"].tolist() == [False, False]


def test_trust_frame_empty() -> None:
    frame = trust_frame([])
    assert frame.empty
    assert list(frame.columns) == TRUST_FRAME_COLUMNS


def test_weights_must_sum_to_one() -> None:
    with pytest.raises(ValueError, match="sum to 1"):
        TrustWeights(completeness=0.5, freshness=0.5, consistency=0.5, ood=0.0)
    with pytest.raises(ValueError, match="non-negative"):
        TrustWeights(completeness=1.2, freshness=-0.2, consistency=0.0, ood=0.0)


def test_thresholds_must_be_ordered() -> None:
    with pytest.raises(ValueError):
        TrustThresholds(high=0.5, adequate=0.6, low=0.4)
    with pytest.raises(ValueError):
        TrustThresholds(ood=0.0)


def test_spec_15_2_combined_story_surfaces_all_three_problems() -> None:
    # Spec 15.2 second example: home ownership unknown, stale vehicle record, two months of
    # transactions. Each problem applies to different products, so check them together.
    story = {
        product: TrustScorer().assess(
            make_snapshot(home_owner=None, months_observed=2, vehicle_record_age_days=800), product)
        for product in (Product.SOLAR_FINANCE, Product.GREEN_HOME, Product.EV_FINANCE)
    }
    assert TrustIssueCode.HOME_OWNERSHIP_UNKNOWN in codes(story[Product.SOLAR_FINANCE])
    assert TrustIssueCode.HOME_OWNERSHIP_UNKNOWN in codes(story[Product.GREEN_HOME])
    assert TrustIssueCode.SHORT_TRANSACTION_HISTORY in codes(story[Product.GREEN_HOME])
    assert TrustIssueCode.SHORT_TRANSACTION_HISTORY in codes(story[Product.EV_FINANCE])
    assert TrustIssueCode.VEHICLE_RECORD_STALE in codes(story[Product.EV_FINANCE])
    assert story[Product.SOLAR_FINANCE].status is TrustStatus.INSUFFICIENT
    assert story[Product.GREEN_HOME].status is TrustStatus.INSUFFICIENT
    assert story[Product.EV_FINANCE].status is TrustStatus.LOW


def test_critical_gate_agrees_with_critical_field_issues() -> None:
    # Invariant: a product is critical-complete exactly when no CRITICAL_FIELD issue is raised.
    population = make_population(200, seed=3) + [
        make_snapshot("E1", has_vehicle=None, fuel_type=None, mileage_km=None, vehicle_record_age_days=None),
        make_snapshot("E2", has_vehicle=False, fuel_type=None, mileage_km=None),
        make_snapshot("E3", energy_months=0, electricity_kwh_12m=None, gas_kwh_12m=None),
        make_snapshot("E4", region=None, electricity_kwh_12m=None),
        make_snapshot("E5", digital_months=0, paper_statements_3m=None, digital_txn_3m_avg=None),
        make_snapshot("E6", home_owner=None, energy_months=0),
    ]
    for snapshot in population:
        for product in ALL_PRODUCTS:
            has_critical_issue = any(
                issue.category is TrustIssueCategory.CRITICAL_FIELD
                for issue in quality_issues(snapshot, product)
            )
            assert critical_fields_present(snapshot, product) is not has_critical_issue, (
                snapshot.customer_id, product)

@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), -0.1])
def test_trust_weights_reject_nonfinite_or_negative_values(invalid):
    with pytest.raises(ValueError):
        TrustWeights(completeness=invalid)


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), -0.1, 1.1])
@pytest.mark.parametrize("field", ["critical_cap", "high_issue_cap", "ood_cap"])
def test_trust_caps_are_probabilities(field, invalid):
    with pytest.raises(ValueError):
        TrustThresholds(**{field: invalid})

