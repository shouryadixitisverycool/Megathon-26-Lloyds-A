"""Versioned synthetic fixtures, never a substitute for Agent A's ML evidence."""

import json
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from importlib.resources import files

from greenr.contracts.product import (
    APPROVED_FEATURES, CustomerSnapshot, FeatureEvidence, HistoryRecord,
    PropensityResult, RecommendationState, TrustAssessment, TrustIssue,
)
from greenr.impact import Product
from greenr.models.propensity.reason_codes import derive_reason_codes

FIXTURE_VERSION = "agent-b-synthetic-personas-v1"
CUTOFF = datetime(2026, 1, 3, tzinfo=timezone.utc)
OBSERVED = datetime(2026, 1, 2, tzinfo=timezone.utc)
ADOPTION_FLAGS = {"already_has_ev", "efficient_home", "solar_installed", "paperless_active"}
PRODUCT_FILES = {
    Product.EV_FINANCE: "ev.json", Product.GREEN_HOME: "green_home.json",
    Product.SOLAR_FINANCE: "solar.json", Product.PAPERLESS_BANKING: "paperless.json",
}
PERSONAS = (
    ("GP-001", "Asha Rao", "South", "Salaried", RecommendationState.RECOMMEND),
    ("GP-002", "Ravi Shah", "West", "Self-employed", RecommendationState.INSUFFICIENT_INFORMATION),
    ("GP-003", "Meera Sen", "East", "Salaried", RecommendationState.CONFLICT_REQUIRES_REVIEW),
    ("GP-004", "Kabir Malik", "North", "Retired", RecommendationState.NOT_APPLICABLE),
    ("GP-005", "Nila Das", "East", "Self-employed", RecommendationState.SUPPRESSED),
    ("GP-006", "Dev Iyer", "South", "Retired", RecommendationState.DO_NOT_RECOMMEND),
)
EV, GH, SF, PB = (Product.EV_FINANCE, Product.GREEN_HOME, Product.SOLAR_FINANCE, Product.PAPERLESS_BANKING)
# Fixed synthetic probabilities. GP-001 clears the 0.60 threshold for every product and
# GP-006 misses it for every product; other personas are decided before propensity.
PROBABILITIES = {
    "GP-001": {EV: "0.84", GH: "0.71", SF: "0.66", PB: "0.79"},
    "GP-002": {EV: "0.52", GH: "0.47", SF: "0.41", PB: "0.63"},
    "GP-003": {EV: "0.69", GH: "0.58", SF: "0.49", PB: "0.74"},
    "GP-004": {EV: "0.31", GH: "0.27", SF: "0.22", PB: "0.18"},
    "GP-005": {EV: "0.76", GH: "0.68", SF: "0.61", PB: "0.72"},
    "GP-006": {EV: "0.24", GH: "0.19", SF: "0.15", PB: "0.33"},
}
# Synthetic model inputs. Reason codes are derived from these by the controlled catalogue
# (default thresholds), never written by hand. None means the input is not on record.
MODEL_INPUTS = {
    "GP-001": dict(has_investments=1, is_ice=1, fuel_type="PETROL", fuel_spend_90d_avg=165.0, annual_mileage_km=15800.0,
                   vehicle_age_years=9.0, has_vehicle_finance=0, home_owner=1, has_mortgage=1,
                   has_existing_solar=0, electricity_kwh_12m=4650.0, gas_kwh_12m=9800.0,
                   home_improvement_spend_90d_avg=85.0, utilities_spend_trend=0.14,
                   paper_statements_3m=3, app_logins_3m_avg=14.0, sustainability_preference=5),
    "GP-002": dict(has_investments=None, is_ice=None, fuel_spend_90d_avg=None, annual_mileage_km=None, vehicle_age_years=None,
                   has_vehicle_finance=0, home_owner=None, has_mortgage=None, has_existing_solar=None,
                   electricity_kwh_12m=None, gas_kwh_12m=None, home_improvement_spend_90d_avg=0.0,
                   utilities_spend_trend=None, paper_statements_3m=None, app_logins_3m_avg=6.0,
                   sustainability_preference=3),
    "GP-003": dict(has_investments=0, is_ice=1, fuel_type="DIESEL", fuel_spend_90d_avg=130.0, annual_mileage_km=11000.0,
                   vehicle_age_years=6.0, has_vehicle_finance=0, home_owner=1, has_mortgage=0,
                   has_existing_solar=0, electricity_kwh_12m=3600.0, gas_kwh_12m=13500.0,
                   home_improvement_spend_90d_avg=20.0, utilities_spend_trend=0.12,
                   paper_statements_3m=2, app_logins_3m_avg=11.0, sustainability_preference=4),
    "GP-004": dict(has_investments=1, is_ice=0, fuel_type="EV", fuel_spend_90d_avg=0.0, annual_mileage_km=9000.0,
                   vehicle_age_years=2.0, has_vehicle_finance=0, home_owner=1, has_mortgage=0,
                   has_existing_solar=1, electricity_kwh_12m=2900.0, gas_kwh_12m=0.0,
                   home_improvement_spend_90d_avg=0.0, utilities_spend_trend=-0.04,
                   paper_statements_3m=0, app_logins_3m_avg=4.0, sustainability_preference=5),
    "GP-005": dict(has_investments=0, is_ice=1, fuel_type="PETROL", fuel_spend_90d_avg=150.0, annual_mileage_km=13000.0,
                   vehicle_age_years=10.0, has_vehicle_finance=1, home_owner=1, has_mortgage=1,
                   has_existing_solar=0, electricity_kwh_12m=4200.0, gas_kwh_12m=12500.0,
                   home_improvement_spend_90d_avg=60.0, utilities_spend_trend=0.05,
                   paper_statements_3m=2, app_logins_3m_avg=9.0, sustainability_preference=3),
    "GP-006": dict(has_investments=1, is_ice=1, fuel_type="PETROL", fuel_spend_90d_avg=45.0, annual_mileage_km=4000.0,
                   vehicle_age_years=5.0, has_vehicle_finance=0, home_owner=1, has_mortgage=0,
                   has_existing_solar=0, electricity_kwh_12m=2400.0, gas_kwh_12m=8000.0,
                   home_improvement_spend_90d_avg=0.0, utilities_spend_trend=-0.02,
                   paper_statements_3m=1, app_logins_3m_avg=1.0, sustainability_preference=2),
}

# Optional opportunities (Green Investments, Green Loans) mirror the trained rules in
# extensions/optional_models.py; only the probabilities are fixed fixture values.
OPTIONAL_THRESHOLD = 0.50
OPTIONAL_PROBABILITIES = {
    "GP-001": {"GREEN_INVESTMENTS": 0.64, "GREEN_LOANS": 0.71},
    "GP-002": {"GREEN_INVESTMENTS": 0.38, "GREEN_LOANS": 0.44},
    "GP-003": {"GREEN_INVESTMENTS": 0.52, "GREEN_LOANS": 0.57},
    "GP-004": {"GREEN_INVESTMENTS": 0.58, "GREEN_LOANS": 0.12},
    "GP-005": {"GREEN_INVESTMENTS": 0.33, "GREEN_LOANS": 0.62},
    "GP-006": {"GREEN_INVESTMENTS": 0.21, "GREEN_LOANS": 0.09},
}
# Descriptive references use the catalogue defaults, not fitted training medians.
OPTIONAL_DESCRIPTIVE = {
    "GREEN_INVESTMENTS": (("app_logins_3m_avg", "HIGH_DIGITAL_ENGAGEMENT", 10.0),),
    "GREEN_LOANS": (("home_improvement_spend_90d_avg", "RECENT_HOME_IMPROVEMENT_ACTIVITY", 50.0),
                    ("gas_kwh_12m", "HIGH_HEATING_ENERGY_USE", 12000.0)),
}


class DemoRepository:
    """Implements the four provider mirrors with independent copies on reads."""

    mode = "fixture"
    version = FIXTURE_VERSION

    def __init__(self):
        self._snapshots = {}
        self._propensities = {}
        self._inputs = {}
        self._history = []
        for customer_id, name, region, segment, state in PERSONAS:
            features = {
                feature: FeatureEvidence(
                    value=feature not in ADOPTION_FLAGS,
                    reference=f"synthetic:{FIXTURE_VERSION}:{customer_id}:{feature}",
                    observed_at=OBSERVED, freshness="current",
                )
                for feature in sorted(APPROVED_FEATURES)
            }
            trust = TrustAssessment(score=Decimal("0.95"), status="TRUSTED")
            if customer_id == "GP-002":
                for key in ("owns_vehicle", "owns_home", "paper_statements"):
                    features.pop(key)
                trust = TrustAssessment(score=Decimal("0.45"), status="LIMITED", issues=(
                    TrustIssue(code="MISSING_EVIDENCE", field="features", severity="WARNING",
                               message="Synthetic persona has missing ownership and statement evidence."),
                ))
            elif customer_id == "GP-003":
                for key in ("ev_interest", "owns_home", "paper_statements"):
                    features[key] = features[key].model_copy(update={"conflicts": ("Synthetic conflicting declarations",)})
                trust = TrustAssessment(score=Decimal("0.30"), status="CONFLICT", issues=(
                    TrustIssue(code="CONFLICTING_EVIDENCE", field="features", severity="HIGH",
                               message="Synthetic declarations conflict and require review."),
                ))
            elif customer_id == "GP-004":
                for key in ADOPTION_FLAGS:
                    features[key] = features[key].model_copy(update={"value": True})
            elif customer_id == "GP-005":
                features["marketing_consent"] = features["marketing_consent"].model_copy(update={"value": False})
            self._snapshots[customer_id] = CustomerSnapshot(
                customer_id=customer_id, display_name=name, region=region, segment=segment,
                feature_cutoff=CUTOFF, features=features, trust=trust,
            )
            for product in Product:
                codes, _ = derive_reason_codes(MODEL_INPUTS[customer_id], product)
                self._propensities[(customer_id, product)] = PropensityResult(
                    product=product, probability=Decimal(PROBABILITIES[customer_id][product]),
                    reason_codes=tuple(code.value for code in codes),
                    model_version="synthetic-probability-fixture-v1",
                    calibration_version="synthetic-calibration-fixture-v1",
                )
                raw = json.loads(files("greenr.demo").joinpath("fixtures", PRODUCT_FILES[product]).read_text())
                self._inputs[(customer_id, product)] = None if customer_id == "GP-002" else raw
                # Explicit historical fixture states; not reconstructed from scores.
                for month, historical_state in (
                    ("2025-10", RecommendationState.DO_NOT_RECOMMEND if customer_id == "GP-001" else state),
                    ("2025-11", RecommendationState.INSUFFICIENT_INFORMATION if customer_id == "GP-001" else state),
                    ("2025-12", state),
                ):
                    self._history.append(HistoryRecord(
                        customer_id=customer_id, month=month, product=product, state=historical_state,
                    ))

    def get_snapshot(self, customer_id):
        snapshot = self._snapshots.get(customer_id)
        return snapshot.model_copy(deep=True) if snapshot is not None else None

    def list_snapshots(self):
        return tuple(snapshot.model_copy(deep=True) for snapshot in self._snapshots.values())

    def get_propensity(self, customer_id, product):
        result = self._propensities.get((customer_id, Product(product)))
        return result.model_copy(deep=True) if result is not None else None

    def get_impact_input(self, customer_id, product):
        return deepcopy(self._inputs.get((customer_id, Product(product))))

    def list_history(self):
        return tuple(self._history)

    def optional_opportunity(self, customer_id, opportunity, purpose=None):
        """Fixture Green Investments / Green Loans signal, using the trained rule order."""
        from greenr.extensions.optional_models import unavailable

        inputs = MODEL_INPUTS[customer_id]
        result = unavailable(opportunity, "INSUFFICIENT_INFORMATION", "", purpose)
        result.update(model_version="synthetic-optional-fixture-v1", calibration_version="synthetic-calibration-fixture-v1",
                      feature_version=FIXTURE_VERSION, cutoff=CUTOFF.date().isoformat(), reason_codes=[])

        def evidence(code, field, value):
            return {"code": code, "field": field, "value": value,
                    "reference": f"synthetic:{FIXTURE_VERSION}:{customer_id}:{field}"}

        if opportunity == "GREEN_INVESTMENTS":
            holding, preference = inputs.get("has_investments"), inputs.get("sustainability_preference")
            if holding is None or preference is None:
                result["reason_codes"] = ["INVESTMENT_HOLDING_OR_PREFERENCE_UNKNOWN"]
                return result
            if holding != 1:
                result.update(status="NOT_RELEVANT", reason_codes=["NO_EXISTING_INVESTMENT_ACTIVITY"])
                return result
            result["reason_codes"] = ["EXISTING_INVESTMENT_ACTIVITY", "STATED_SUSTAINABILITY_PREFERENCE"]
            result["reason_evidence"] = [evidence("EXISTING_INVESTMENT_ACTIVITY", "has_investments", holding),
                                         evidence("STATED_SUSTAINABILITY_PREFERENCE", "sustainability_preference", preference)]
        else:
            borrowing = [inputs.get("has_mortgage"), inputs.get("has_vehicle_finance")]
            if 1 not in borrowing:
                result.update(status="INSUFFICIENT_INFORMATION" if None in borrowing else "NOT_RELEVANT",
                              reason_codes=["EXISTING_BORROWING_NOT_CONFIRMED"])
                return result
            if purpose is None:
                result["reason_codes"] = ["DOCUMENTED_GREEN_PURPOSE_REQUIRED"]
                return result
            result["reason_codes"] = ["EXISTING_BORROWING_RELATIONSHIP", "DECLARED_GREEN_PURPOSE_" + purpose]
            result["reason_evidence"] = [evidence("EXISTING_BORROWING_RELATIONSHIP", field, 1)
                                         for field in ("has_mortgage", "has_vehicle_finance") if inputs.get(field) == 1]
            result["reason_evidence"].append({"code": "DECLARED_GREEN_PURPOSE_" + purpose, "field": "purpose",
                                              "value": purpose, "reference": "customer declaration"})
        probability = OPTIONAL_PROBABILITIES[customer_id][opportunity]
        result.update(probability=probability, threshold=OPTIONAL_THRESHOLD,
                      status="OPPORTUNITY_SIGNAL" if probability >= OPTIONAL_THRESHOLD else "LOW_RELEVANCE")
        for field, code, reference in OPTIONAL_DESCRIPTIVE[opportunity]:
            value = inputs.get(field)
            if value is not None and value > reference:
                result["reason_codes"].append(code)
                result["reason_evidence"].append({**evidence(code, field, value), "fixture_reference": reference,
                                                  "limitation": "Descriptive association, not a causal driver or eligibility finding."})
        return result
