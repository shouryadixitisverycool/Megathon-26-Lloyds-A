"""Separately engineered optional signals. Never investment advice or credit approval.

Run ``python -m greenr.extensions.optional_models`` after the main pipeline.
These outcomes are synthetic Bernoulli draws from smooth multi-signal relationships,
independent latent noise and interactions. They are not observed adoption evidence.
"""

from dataclasses import dataclass
from datetime import date, timedelta
import hashlib
import json
import io
from pathlib import Path
from enum import StrEnum
from threading import RLock

import joblib
import numpy as np
import pandas as pd
from scipy.special import expit
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from greenr import config
from greenr.evaluation import metrics
from greenr.models.propensity.calibration import Calibrator
from greenr.models.propensity.training import best_f1_threshold
from greenr.pipelines.run import write_json, sha256_file

OPPORTUNITIES = ("GREEN_INVESTMENTS", "GREEN_LOANS")
PURPOSES = ("INSULATION", "HEAT_PUMP", "EV_CHARGING")


class GreenPurpose(StrEnum):
    INSULATION = "INSULATION"
    HEAT_PUMP = "HEAT_PUMP"
    EV_CHARGING = "EV_CHARGING"


SEED = 6044
FEATURES = {
    "GREEN_INVESTMENTS": ("sustainability_preference", "digital_txn_3m_avg", "app_logins_3m_avg",
                          "digital_months_present", "tenure_months", "txn_months_observed"),
    "GREEN_LOANS": ("home_improvement_spend_12m_avg", "home_improvement_spend_trend", "has_vehicle",
                    "vehicle_age_years", "annual_mileage_km", "electricity_kwh_12m", "gas_kwh_12m",
                    "electricity_trend", "sustainability_preference", "digital_txn_3m_avg",
                    "energy_months_present", "txn_months_observed"),
}
NOTICE = ("Optional 90-day outcomes are engineered synthetic scenarios, not public or observed adoption data. "
          "This is an opportunity signal only, not investment advice, financial suitability, eligibility or credit approval.")
CONFIDENCE_LIMITATION = "No independent optional confidence reliability validation implemented; confidence is suppressed."


def matrix(frame: pd.DataFrame, opportunity: str) -> pd.DataFrame:
    if opportunity not in FEATURES:
        raise ValueError(f"Unknown optional opportunity: {opportunity}")
    return frame.reindex(columns=FEATURES[opportunity]).astype(float).replace([np.inf, -np.inf], np.nan)


def population(frame: pd.DataFrame, opportunity: str) -> pd.Series:
    if opportunity == "GREEN_INVESTMENTS":
        return frame["has_investments"].eq(1) & frame["sustainability_preference"].notna()
    if opportunity == "GREEN_LOANS":
        return frame[["has_mortgage", "has_vehicle_finance"]].eq(1).any(axis=1)
    raise ValueError(f"Unknown optional opportunity: {opportunity}")


def _signals(frame: pd.DataFrame, opportunity: str) -> np.ndarray:
    def values(name, scale=1):
        v = pd.to_numeric(frame[name], errors="coerce").fillna(0).to_numpy(dtype=float)
        return np.tanh(np.maximum(v, 0) / scale)
    green = values("sustainability_preference", 4)
    digital = values("digital_txn_3m_avg", 25)
    if opportunity == "GREEN_INVESTMENTS":
        return np.column_stack([green, digital, values("app_logins_3m_avg", 10),
                                values("tenure_months", 80), green * digital])
    project = values("home_improvement_spend_12m_avg", 120)
    energy = values("gas_kwh_12m", 15000)
    vehicle = values("annual_mileage_km", 15000)
    return np.column_stack([green, project, energy, vehicle, project * green, energy * digital])


def optional_outcomes(frame: pd.DataFrame, cutoff: date, *, shifted=False, seed=SEED) -> pd.DataFrame:
    """Customer-keyed draws remain reproducible when input order changes; latent draws are discarded."""
    rows = []
    for opportunity in OPPORTUNITIES:
        signals = _signals(frame, opportunity)
        coefficients = (np.array([1.5, 0.55, 0.5, 0.35, 0.9]) if opportunity == "GREEN_INVESTMENTS"
                        else np.array([0.7, 1.15, 0.6, 0.4, 0.85, 0.65]))
        if shifted:
            coefficients *= np.linspace(0.55, 1.3, len(coefficients))
        for position, customer_id in enumerate(frame.index):
            key = f"{seed}:{shifted}:{opportunity}:{customer_id}".encode()
            customer_seed = int.from_bytes(hashlib.sha256(key).digest()[:8], "little")
            rng = np.random.default_rng(customer_seed)
            # Independent unobserved readiness, environmental motivation and budget noise.
            readiness, motivation, budget = rng.normal(size=3)
            latent = 0.65 * readiness + 0.45 * motivation + 0.4 * budget + 0.25 * readiness * motivation
            logit = (-3.3 if not shifted else -3.65) + signals[position] @ coefficients + latent
            adopted = int(rng.binomial(1, expit(logit)))
            adoption_date = cutoff + timedelta(days=int(rng.integers(1, 91))) if adopted else None
            rows.append({"customer_id": customer_id, "opportunity": opportunity,
                         "adopted_90d": adopted, "adoption_date": adoption_date})
    return pd.DataFrame(rows)


def heuristic(frame: pd.DataFrame, opportunity: str) -> np.ndarray:
    signals = _signals(frame, opportunity)
    weights = np.full(signals.shape[1], 0.6)
    weights[0] = 1.0
    return expit(-2.6 + signals @ weights)


@dataclass
class OptionalBundle:
    opportunity: str
    estimator: Pipeline
    calibrator: Calibrator
    threshold: float
    feature_cutoff: date
    model_version: str
    reason_reference: dict

    def predict(self, frame):
        return self.calibrator.transform(self.estimator.predict_proba(matrix(frame, self.opportunity))[:, 1])


def train(processed_dir: Path | None = None, artifact_dir: Path | None = None,
          reports_dir: Path | None = None) -> dict:
    processed_dir = Path(processed_dir or config.PROCESSED_DIR)
    artifact_dir = Path(artifact_dir or config.ARTIFACT_DIR / "optional")
    reports_dir = Path(reports_dir or config.REPORTS_DIR)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    frame_path = processed_dir / f"customer360_{config.FEATURE_CUTOFF.isoformat()}.parquet"
    split_path = processed_dir / "split_manifest.csv"
    frame = pd.read_parquet(frame_path)
    split = pd.read_csv(split_path, dtype=str).set_index("customer_id")["split"].reindex(frame.index)
    if split.isna().any() or not split.index.is_unique or not split.isin(["train", "validation", "test", "demo", "labelconfidence_release", "confidence_release"]).all():
        raise ValueError("Optional training requires one valid customer split assignment for every customer")
    outcomes = optional_outcomes(frame, config.FEATURE_CUTOFF)
    outcomes.to_parquet(artifact_dir / "optional_outcomes.parquet", index=False)
    # Independent shifted parameter/noise draws on a changed physical-feature distribution.
    shifted = frame.copy()
    for name in ("digital_txn_3m_avg", "gas_kwh_12m", "home_improvement_spend_12m_avg"):
        shifted[name] *= 1.25
    rng = np.random.default_rng(SEED + 1)
    shift_columns = sorted(set(c for cols in FEATURES.values() for c in cols))
    shifted[shift_columns] = shifted[shift_columns].mask(rng.random((len(frame), len(shift_columns))) < 0.15)
    shifted_outcomes = optional_outcomes(shifted, config.FEATURE_CUTOFF, shifted=True)
    shifted_outcomes.to_parquet(artifact_dir / "optional_shifted_outcomes.parquet", index=False)
    result = {"notice": NOTICE, "outcome_window_days": 90, "seed": SEED,
              "label_method": "Smooth feature signals + independent Gaussian latent drivers and interaction + Bernoulli draw; no deterministic feature thresholds.",
              "shift_protocol": "Held-out customers with scaled activity, 15% feature missingness, changed coefficients/intercept and independent latent/adoption draws.",
              "generator_parameters": {
                  "base_intercept": -3.3, "shift_intercept": -3.65,
                  "investment_coefficients": [1.5, 0.55, 0.5, 0.35, 0.9],
                  "loan_coefficients": [0.7, 1.15, 0.6, 0.4, 0.85, 0.65],
                  "shift_coefficient_multiplier": "linspace(0.55, 1.3, n_signals)",
                  "latent_standard_normal_weights": {"readiness": .65, "motivation": .45, "budget": .4,
                                                      "readiness_motivation_interaction": .25},
                  "customer_seed": "first 8 bytes SHA256(seed:shifted:opportunity:customer_id), little-endian",
                  "latent_exported": False},
              "split_sha256": sha256_file(split_path), "customer360_sha256": sha256_file(frame_path),
              "products": {}}
    for opportunity in OPPORTUNITIES:
        mask = population(frame, opportunity)
        ids = {part: frame.index[mask & split.eq(part)] for part in ("train", "validation", "test")}
        labels = outcomes.loc[outcomes.opportunity.eq(opportunity)].set_index("customer_id")["adopted_90d"]
        y = {part: labels.loc[index].to_numpy(dtype=int) for part, index in ids.items()}
        if any(len(np.unique(y[part])) < 2 for part in ("train", "validation", "test")):
            raise ValueError(f"{opportunity}: need both classes in train/validation/test; generate more customers")
        model = Pipeline([("impute", SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)),
                          ("scale", StandardScaler()),
                          ("logistic", LogisticRegression(C=1, max_iter=2500, random_state=SEED))])
        model.fit(matrix(frame.loc[ids["train"]], opportunity), y["train"])
        val_raw = model.predict_proba(matrix(frame.loc[ids["validation"]], opportunity))[:, 1]
        calibrator = Calibrator.fit(val_raw, y["validation"], opportunity.lower() + "_optional", seed=SEED)
        p_val = calibrator.transform(val_raw)
        threshold = best_f1_threshold(y["validation"], p_val)
        refs = {name: float(frame.loc[ids["train"], name].median())
                for name in FEATURES[opportunity] if frame.loc[ids["train"], name].notna().any()}
        fingerprint = hashlib.sha256((result["customer360_sha256"] + result["split_sha256"] + opportunity + str(SEED)).encode()).hexdigest()[:12]
        bundle = OptionalBundle(opportunity, model, calibrator, threshold, config.FEATURE_CUTOFF,
                                f"{opportunity.lower()}_logistic_v1_{fingerprint}", refs)
        artifact = artifact_dir / f"{opportunity.lower()}.joblib"
        temporary = artifact.with_suffix(".joblib.tmp")
        joblib.dump(bundle, temporary)
        temporary.replace(artifact)
        test = frame.loc[ids["test"]]
        raw = model.predict_proba(matrix(test, opportunity))[:, 1]
        hp_val = heuristic(frame.loc[ids["validation"]], opportunity)
        hp_calibrator = Calibrator.fit(hp_val, y["validation"], opportunity.lower() + "_heuristic", seed=SEED)
        hp_threshold = best_f1_threshold(y["validation"], hp_calibrator.transform(hp_val))
        shift_labels = shifted_outcomes.loc[shifted_outcomes.opportunity.eq(opportunity)].set_index("customer_id")["adopted_90d"]
        stress = test.copy()
        cols = list(FEATURES[opportunity])
        stress[cols] = stress[cols].mask(np.random.default_rng(SEED + 2).random((len(test), len(cols))) < 0.3)
        result["products"][opportunity] = {
            "features": cols, "model_version": bundle.model_version, "calibration_version": calibrator.version,
            "calibration_fitted_split": "validation", "threshold_fitted_split": "validation", "threshold": threshold,
            "calibration_fitted_n": calibrator.n_fit,
            "counts": {part: {"customers": len(ids[part]), "positive": int(y[part].sum())} for part in ids},
            "test": {"logistic": metrics.summary(y["test"], bundle.predict(test), threshold=threshold),
                     "heuristic": metrics.summary(y["test"], hp_calibrator.transform(heuristic(test, opportunity)), threshold=hp_threshold)},
            "uncalibrated_test": metrics.summary(y["test"], raw, threshold=threshold),
            "shifted_test": metrics.summary(shift_labels.loc[ids["test"]].to_numpy(), bundle.predict(shifted.loc[ids["test"]]), threshold=threshold),
            "shifted_heuristic_test": metrics.summary(shift_labels.loc[ids["test"]].to_numpy(), hp_calibrator.transform(heuristic(shifted.loc[ids["test"]], opportunity)), threshold=hp_threshold),
            "missingness_30pct_test": metrics.summary(y["test"], bundle.predict(stress), threshold=threshold),
            "missingness_30pct_heuristic_test": metrics.summary(y["test"], hp_calibrator.transform(heuristic(stress, opportunity)), threshold=hp_threshold),
            "confidence_status": "SUPPRESSED", "confidence": None, "confidence_limitation": CONFIDENCE_LIMITATION}
    result["artifact_sha256"] = {path.name: sha256_file(path) for path in sorted(artifact_dir.glob("*")) if path.is_file()}
    report_path = reports_dir / "optional_evaluation.json"
    temporary_report = report_path.with_suffix(".json.tmp")
    write_json(temporary_report, result)
    temporary_report.replace(report_path)
    return result


class OptionalOpportunityProvider:
    def __init__(self, root: Path | None = None):
        self.root = Path(root or config.ARTIFACT_DIR / "optional")
        self.bundles = {name: joblib.load(self.root / f"{name.lower()}.joblib") for name in OPPORTUNITIES}

    def score(self, snapshot, opportunity: str, purpose: str | None = None) -> dict:
        if opportunity not in OPPORTUNITIES or purpose is not None and purpose not in PURPOSES:
            raise ValueError("Unknown optional opportunity or unsupported green purpose")
        bundle = self.bundles[opportunity]
        features = snapshot.features
        def observed(name):
            value = features.get(name)
            return float(value) if value is not None and np.isfinite(value) else None
        result = {"product": opportunity, "probability": None, "confidence": None,
                  "confidence_status": "SUPPRESSED", "confidence_limitation": CONFIDENCE_LIMITATION,
                  "confidence_method_version": "optional-confidence-not-validated-v1",
                  "model_version": bundle.model_version, "calibration_version": bundle.calibrator.version,
                  "feature_version": snapshot.feature_version, "cutoff": snapshot.feature_cutoff.isoformat(),
                   "status": "INSUFFICIENT_INFORMATION", "reason_codes": [], "disclaimer": NOTICE,
                  "reason_evidence": [], "experimental": True,
                  "eligibility": "NOT_ASSESSED", "impact": {"status": "NOT_CLAIMED", "value": None},
                  "purpose": purpose, "outcome_window_days": 90}
        if snapshot.feature_cutoff != bundle.feature_cutoff:
            result["reason_codes"] = ["OPTIONAL_MODEL_CUTOFF_MISMATCH"]
            return result
        quality = getattr(snapshot, "data_quality", None)
        if quality is not None and quality.invalid_product_records:
            result["reason_codes"] = ["INVALID_PRODUCT_RECORDS"]
            return result
        if opportunity == "GREEN_INVESTMENTS":
            holding, preference = observed("has_investments"), observed("sustainability_preference")
            if holding is None or preference is None:
                result["reason_codes"] = ["INVESTMENT_HOLDING_OR_PREFERENCE_UNKNOWN"]
                return result
            if holding != 1:
                result.update(status="NOT_RELEVANT", reason_codes=["NO_EXISTING_INVESTMENT_ACTIVITY"])
                return result
            result["reason_codes"] = ["EXISTING_INVESTMENT_ACTIVITY", "STATED_SUSTAINABILITY_PREFERENCE"]
            result["reason_evidence"] = [
                {"code": "EXISTING_INVESTMENT_ACTIVITY", "field": "has_investments", "value": holding},
                {"code": "STATED_SUSTAINABILITY_PREFERENCE", "field": "sustainability_preference", "value": preference}]
        else:
            borrowing = [observed("has_mortgage"), observed("has_vehicle_finance")]
            if 1 not in borrowing:
                result.update(status="INSUFFICIENT_INFORMATION" if None in borrowing else "NOT_RELEVANT",
                              reason_codes=["EXISTING_BORROWING_NOT_CONFIRMED"])
                return result
            if purpose is None:
                result["reason_codes"] = ["DOCUMENTED_GREEN_PURPOSE_REQUIRED"]
                return result
            result["reason_codes"] = ["EXISTING_BORROWING_RELATIONSHIP", "DECLARED_GREEN_PURPOSE_" + purpose]
            result["reason_evidence"] = [
                {"code": "EXISTING_BORROWING_RELATIONSHIP", "field": field, "value": 1}
                for field in ("has_mortgage", "has_vehicle_finance") if observed(field) == 1]
            result["reason_evidence"].append({"code": "DECLARED_GREEN_PURPOSE_" + purpose,
                                              "field": "purpose", "value": purpose, "reference": "customer declaration"})
        rows = pd.DataFrame([features], index=[snapshot.customer_id])
        probability = float(bundle.predict(rows)[0])
        result.update(probability=probability, threshold=bundle.threshold,
                      status="OPPORTUNITY_SIGNAL" if probability >= bundle.threshold else "LOW_RELEVANCE")
        descriptive = ({"digital_txn_3m_avg": "HIGH_DIGITAL_ENGAGEMENT"} if opportunity == "GREEN_INVESTMENTS"
                       else {"home_improvement_spend_12m_avg": "RECENT_HOME_IMPROVEMENT_ACTIVITY",
                             "gas_kwh_12m": "HIGH_HEATING_ENERGY_USE"})
        for name, code in descriptive.items():
            value, reference = observed(name), bundle.reason_reference.get(name)
            if value is not None and reference is not None and value > reference:
                result["reason_codes"].append(code)
                result["reason_evidence"].append({"code": code, "field": name, "value": value,
                                                  "training_median_reference": reference,
                                                  "limitation": "Descriptive association, not a causal driver or eligibility finding."})
        for evidence in result["reason_evidence"]:
            evidence.setdefault("reference", f"customer360:{snapshot.feature_version}:{snapshot.feature_cutoff}:{snapshot.customer_id}:{evidence['field']}")
        return result


def unavailable(opportunity, status, reason, purpose=None):
    return {"product": opportunity, "status": status, "experimental": True,
            "probability": None, "confidence": None, "confidence_status": "SUPPRESSED",
            "confidence_limitation": CONFIDENCE_LIMITATION,
            "confidence_method_version": "optional-confidence-not-validated-v1",
            "model_version": None, "calibration_version": None, "feature_version": None,
            "cutoff": None, "reason_codes": [reason], "reason_evidence": [],
            "eligibility": "NOT_ASSESSED", "impact": {"status": "NOT_CLAIMED", "value": None},
            "purpose": purpose, "outcome_window_days": 90, "disclaimer": NOTICE}


class OptionalModelLoader:
    """Load verified bytes lazily; never fit models or fall back to heuristic scores."""

    def __init__(self, root=None, processed_dir=None, reports_dir=None):
        self.root = Path(root or config.ARTIFACT_DIR / "optional")
        self.frame_path = Path(processed_dir or config.PROCESSED_DIR) / f"customer360_{config.FEATURE_CUTOFF.isoformat()}.parquet"
        self.report_path = Path(reports_dir or config.REPORTS_DIR) / "optional_evaluation.json"
        self.lock = RLock()
        self.signature = None
        self.provider = None

    def load(self):
        with self.lock:
            paths = [self.report_path, self.frame_path, *[self.root / f"{name.lower()}.joblib" for name in OPPORTUNITIES]]
            try:
                signature = tuple((p.stat().st_mtime_ns, p.stat().st_size, p.stat().st_ino) for p in paths)
                if signature == self.signature:
                    return self.provider, "AVAILABLE"
                report_bytes = self.report_path.read_bytes()
                report = json.loads(report_bytes)
                if report["customer360_sha256"] != sha256_file(self.frame_path):
                    return None, "MODEL_STALE"
                bundles = {}
                for name, path in zip(OPPORTUNITIES, paths[2:]):
                    payload = path.read_bytes()
                    if hashlib.sha256(payload).hexdigest() != report["artifact_sha256"][path.name]:
                        return None, "MODEL_STALE"
                    bundle = joblib.load(io.BytesIO(payload))
                    if not isinstance(bundle, OptionalBundle) or bundle.opportunity != name or bundle.model_version != report["products"][name]["model_version"]:
                        return None, "MODEL_STALE"
                    bundles[name] = bundle
                if report_bytes != self.report_path.read_bytes() or signature != tuple((p.stat().st_mtime_ns, p.stat().st_size, p.stat().st_ino) for p in paths):
                    return None, "MODEL_STALE"
                provider = OptionalOpportunityProvider.__new__(OptionalOpportunityProvider)
                provider.root, provider.bundles = self.root, bundles
                self.provider, self.signature = provider, signature
                return provider, "AVAILABLE"
            except FileNotFoundError:
                return None, "NOT_AVAILABLE"
            except (OSError, ValueError, KeyError, TypeError, EOFError):
                return None, "MODEL_STALE"


if __name__ == "__main__":
    # Persist the importable class path rather than __main__.OptionalBundle.
    from greenr.extensions.optional_models import train as canonical_train
    print(json.dumps({name: report["test"] for name, report in canonical_train()["products"].items()}, indent=2))
