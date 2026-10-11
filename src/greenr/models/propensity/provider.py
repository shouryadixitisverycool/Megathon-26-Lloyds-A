"""ModelPropensityProvider: implements ``ports.PropensityProvider`` from trained bundles.

Scoring reads only ``snapshot.features`` (plus ``snapshot.vehicle.fuel_type`` as display
evidence). Customers outside the model population get ``propensity = 0.0``, ``raw_score = 0.0``,
no reason codes and SUPPRESSED confidence; consumers must check ``in_model_population``.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import timedelta

import numpy as np
import pandas as pd

from greenr import config
from greenr.contracts import (
    ConfidenceResult,
    ConfidenceStatus,
    CustomerSnapshot,
    Product,
    PropensityResult,
)
from greenr.models.propensity.features import population_mask
from greenr.models.propensity.reason_codes import REASON_INPUT_FIELDS, derive_reason_codes
from greenr.models.propensity.training import (
    ProductModelBundle,
    logistic_contributions,
    predict_raw,
)

ConfidenceScorer = Callable[[Product, pd.DataFrame, np.ndarray], list[ConfidenceResult]]

NOT_VALIDATED = ConfidenceResult(status=ConfidenceStatus.SUPPRESSED, method_version="none",
                                 limitation="Confidence not validated")
OUT_OF_POPULATION = ConfidenceResult(status=ConfidenceStatus.SUPPRESSED, method_version="none",
                                     limitation="Customer is outside the model population")


class ModelPropensityProvider:
    def __init__(self, bundles: Mapping[Product, ProductModelBundle],
                 confidence_scorer: ConfidenceScorer | None = None) -> None:
        self.bundles = dict(bundles)
        self.confidence_scorer = confidence_scorer

    # ---- internals -----------------------------------------------------------------------
    def _bundle(self, product: Product) -> ProductModelBundle:
        try:
            return self.bundles[product]
        except KeyError:
            raise KeyError(f"no trained propensity model for {product}") from None

    def _run(self, frame: pd.DataFrame, product: Product):
        """Vectorised scoring of a feature frame -> (in_pop, exclusion, raw, calibrated)."""
        b = self._bundle(product)
        in_pop, exclusion = population_mask(frame, product)
        raw = np.zeros(len(frame))
        cal = np.zeros(len(frame))
        mask = in_pop.to_numpy()
        if mask.any():
            sub = frame[mask]
            r = predict_raw(b, sub)
            raw[mask] = r
            cal[mask] = b.calibrator.transform(r)
        return in_pop, exclusion, raw, cal

    @staticmethod
    def _frame(snapshots: Sequence[CustomerSnapshot]) -> pd.DataFrame:
        return pd.DataFrame([dict(s.features) for s in snapshots], index=pd.RangeIndex(len(snapshots)))

    # ---- PropensityProvider ----------------------------------------------------------------
    def score(self, snapshot: CustomerSnapshot, product: Product) -> PropensityResult:
        return self.score_many([snapshot], product)[0]

    def score_many(self, snapshots: Sequence[CustomerSnapshot], product: Product) -> list[PropensityResult]:
        if not snapshots:
            return []
        b = self._bundle(product)
        frame = self._frame(snapshots)
        in_pop, exclusion, raw, cal = self._run(frame, product)
        mask = in_pop.to_numpy()

        conf: dict[int, ConfidenceResult] = {}
        contribs: dict[int, dict[str, float]] = {}
        if mask.any():
            sub = frame[mask]
            pos = np.flatnonzero(mask)
            c_df = logistic_contributions(b, sub)
            for i, rec in zip(pos, c_df.to_dict("records"), strict=True):
                contribs[int(i)] = rec
            if self.confidence_scorer is not None:
                out = self.confidence_scorer(product, sub, cal[mask])
                if len(out) != len(pos):
                    raise ValueError("confidence_scorer must return one ConfidenceResult per row")
                conf = {int(i): c for i, c in zip(pos, out, strict=True)}

        results: list[PropensityResult] = []
        for i, snap in enumerate(snapshots):
            in_p = bool(mask[i])
            codes, evidence = [], {}
            if in_p:
                feats: dict[str, object] = dict(snap.features)
                if snap.vehicle.fuel_type is not None:
                    feats["fuel_type"] = snap.vehicle.fuel_type.value
                codes, evidence = derive_reason_codes(feats, product, b.reason_thresholds, contribs[i])
            results.append(PropensityResult(
                customer_id=snap.customer_id, product=product,
                propensity=float(cal[i]), raw_score=float(raw[i]),
                model_type=b.selected_model_type, model_version=b.model_version,
                calibration_method=b.calibrator.method, calibration_version=b.calibration_version,
                feature_version=snap.feature_version, feature_cutoff=snap.feature_cutoff,
                outcome_window_end=snap.feature_cutoff + timedelta(days=config.OUTCOME_WINDOW_DAYS),
                prediction_timestamp=config.PREDICTION_TIMESTAMP,
                in_model_population=in_p,
                population_exclusion=None if in_p else exclusion.iloc[i],
                reason_codes=codes, evidence=evidence,
                confidence=(conf.get(i, NOT_VALIDATED) if in_p else OUT_OF_POPULATION),
            ))
        return results

    # ---- extras ----------------------------------------------------------------------------
    def score_portfolio(self, frame: pd.DataFrame, products: Sequence[Product] | None = None,
                        with_reasons: bool = True) -> pd.DataFrame:
        """Tidy scoring of a Customer 360 frame (index customer_id).

        Columns: customer_id, product, propensity (NaN outside population), raw_score (NaN
        outside), in_population, threshold (operational, calibrated scale), reason_codes (list).
        """
        parts = []
        for product in (products or list(self.bundles)):
            b = self._bundle(product)
            in_pop, _, raw, cal = self._run(frame, product)
            mask = in_pop.to_numpy()
            codes: list[list] = [[] for _ in range(len(frame))]
            if with_reasons and mask.any():
                sub = frame[mask]
                cols = [c for c in REASON_INPUT_FIELDS if c in sub.columns]
                recs = sub[cols].to_dict("records")
                c_recs = logistic_contributions(b, sub).to_dict("records")
                for i, rec, cr in zip(np.flatnonzero(mask), recs, c_recs, strict=True):
                    codes[int(i)] = derive_reason_codes(rec, product, b.reason_thresholds, cr)[0]
            parts.append(pd.DataFrame({
                "customer_id": frame.index.to_numpy(),
                "product": product.value,
                "propensity": np.where(mask, cal, np.nan),
                "raw_score": np.where(mask, raw, np.nan),
                "in_population": mask,
                "threshold": b.threshold,
                "reason_codes": codes,
            }))
        return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()

    def sensitivity(self, snapshot: CustomerSnapshot, product: Product, feature: str,
                    values: Sequence[float]) -> list[tuple[float, float]]:
        """Model sensitivity (spec 20): calibrated propensity with ``feature`` set to each value.

        Not advice to change the behaviour. Raises ValueError if ``feature`` is not a model input.
        """
        b = self._bundle(product)
        if feature not in b.features:
            raise ValueError(f"{feature!r} is not an input of the {product} model")
        if not values:
            return []
        base = dict(snapshot.features)
        frame = pd.DataFrame([{**base, feature: v} for v in values])
        p = b.calibrator.transform(predict_raw(b, frame))
        return [(v, float(x)) for v, x in zip(values, p, strict=True)]
