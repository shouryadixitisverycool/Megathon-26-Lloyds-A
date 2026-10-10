"""TrustScorer: the ``ports.TrustProvider`` implementation for Agent A (spec 15, 17.4).

Trust measures the adequacy of the input evidence for one customer and one product. It
is not model confidence and it does not re-use the propensity model.

Components (each in 0..1):

* completeness: share of the product's applicable fields that are present (``quality``);
* freshness: recency and length of the evidence (``quality``);
* cross-source consistency: 1 minus the severity-weighted conflict penalty (``conflicts``);
* OOD component: 1 minus ``ood_excess``, the part of the OOD percentile above
  ``ood_excess_start`` rescaled to 0..1 (``ood``).

``score = sum(weight_i * component_i)`` with default weights 0.30 / 0.25 / 0.30 / 0.15.

Hard caps are applied to the score afterwards (the minimum of all that apply):

* a critical field is missing: cap 0.40 and status INSUFFICIENT;
* any HIGH-severity issue or conflict: cap 0.50, so status is LOW at best;
* OOD score at or above the threshold (0.99): OUT_OF_DISTRIBUTION issue, cap 0.40.

Status bands on the capped score: HIGH >= 0.80, ADEQUATE >= 0.60, LOW >= 0.40,
otherwise INSUFFICIENT. These are defaults; the orchestrator tunes them on validation.

Without an OOD detector for a product, ``ood_score`` is 0.0 and no OOD issue is raised.
That means "not assessed", not "typical", and it is documented as such.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import math
from typing import Final

import numpy as np
import pandas as pd

from greenpath import config
from greenpath.contracts import (
    CustomerSnapshot,
    Product,
    Severity,
    TrustAssessment,
    TrustIssue,
    TrustIssueCategory,
    TrustIssueCode,
    TrustStatus,
)
from greenpath.trust.conflicts import cross_source_consistency, detect_conflicts
from greenpath.trust.ood import DEFAULT_OOD_THRESHOLD, OODDetector
from greenpath.trust.quality import QualityReport, assess_quality

TRUST_METHOD_VERSION: Final = "trust_v1"


def _clip01(value: float) -> float:
    return min(max(value, 0.0), 1.0)


@dataclass(frozen=True)
class TrustWeights:
    """Component weights for the trust score. Must be non-negative and sum to 1."""

    completeness: float = 0.30
    freshness: float = 0.25
    consistency: float = 0.30
    ood: float = 0.15

    def __post_init__(self) -> None:
        values = (self.completeness, self.freshness, self.consistency, self.ood)
        if any(not math.isfinite(v) or v < 0 for v in values):
            raise ValueError("trust weights must be finite and non-negative")
        if abs(sum(values) - 1.0) > 1e-9:
            raise ValueError(f"trust weights must sum to 1, got {sum(values):.6f}")


@dataclass(frozen=True)
class TrustThresholds:
    """Status bands, OOD trigger and hard-cap levels. Defaults are pre-validation picks."""

    high: float = 0.80
    adequate: float = 0.60
    low: float = 0.40
    #: OUT_OF_DISTRIBUTION is raised, and the OOD cap applied, at or above this OOD score.
    ood: float = DEFAULT_OOD_THRESHOLD
    #: The OOD component loses credit only above this percentile (linear to 1.0).
    ood_excess_start: float = 0.90
    #: Score cap when a critical field is missing (status is forced to INSUFFICIENT).
    critical_cap: float = 0.40
    #: Score cap when any HIGH-severity issue or conflict exists (status LOW at best).
    high_issue_cap: float = 0.50
    #: Score cap when the OOD score is at or above ``ood``.
    ood_cap: float = 0.40

    def __post_init__(self) -> None:
        for cap in (self.critical_cap, self.high_issue_cap, self.ood_cap):
            if not math.isfinite(cap) or not 0 <= cap <= 1:
                raise ValueError("trust score caps must be finite values in [0, 1]")
        if not 0.0 < self.low < self.adequate < self.high <= 1.0:
            raise ValueError("trust status thresholds must satisfy 0 < low < adequate < high <= 1")
        if not 0.0 < self.ood <= 1.0:
            raise ValueError("OOD threshold must be in (0, 1]")
        if not 0.0 <= self.ood_excess_start < 1.0:
            raise ValueError("ood_excess_start must be in [0, 1)")


DEFAULT_WEIGHTS: Final = TrustWeights()
DEFAULT_THRESHOLDS: Final = TrustThresholds()


def _band(score: float, thresholds: TrustThresholds) -> TrustStatus:
    if score >= thresholds.high:
        return TrustStatus.HIGH
    if score >= thresholds.adequate:
        return TrustStatus.ADEQUATE
    if score >= thresholds.low:
        return TrustStatus.LOW
    return TrustStatus.INSUFFICIENT


def _as_float(value: object) -> float:
    """Feature value as float; None and strings become NaN (imputed by the detector)."""
    if value is None or isinstance(value, str):
        return float("nan")
    return float(value)  # bool, int or float


class TrustScorer:
    """Evidence-adequacy trust for each customer and product (``ports.TrustProvider``).

    ``ood_detectors`` maps a product to the detector fitted on that product's training
    feature matrix. ``assess`` and ``assess_many`` share one code path, so a single
    snapshot and a batch of one give the same assessment.
    """

    method_version: Final = TRUST_METHOD_VERSION

    def __init__(
        self,
        ood_detectors: Mapping[Product, OODDetector] | None = None,
        weights: TrustWeights = DEFAULT_WEIGHTS,
        thresholds: TrustThresholds = DEFAULT_THRESHOLDS,
    ) -> None:
        self._detectors: dict[Product, OODDetector] = dict(ood_detectors or {})
        self._weights = weights
        self._thresholds = thresholds

    def assess(self, snapshot: CustomerSnapshot, product: Product) -> TrustAssessment:
        """Trust assessment for one customer and product."""
        return self.assess_many([snapshot], product)[0]

    def assess_many(self, snapshots: Sequence[CustomerSnapshot], product: Product) -> list[TrustAssessment]:
        """Trust assessments for many customers; the OOD score is computed in one batch."""
        snapshots = list(snapshots)
        if not snapshots:
            return []
        qualities = [assess_quality(s, product) for s in snapshots]
        conflicts = [detect_conflicts(s, product) for s in snapshots]
        oods = self._ood_scores(snapshots, product)
        return [
            self._combine(snapshot, product, quality, found, float(ood))
            for snapshot, quality, found, ood in zip(snapshots, qualities, conflicts, oods, strict=True)
        ]

    # ------------------------------------------------------------ internals
    def _ood_scores(self, snapshots: Sequence[CustomerSnapshot], product: Product) -> np.ndarray:
        detector = self._detectors.get(product)
        if detector is None:
            return np.zeros(len(snapshots), dtype=float)
        rows = [[_as_float(s.features.get(name)) for name in detector.feature_names] for s in snapshots]
        frame = pd.DataFrame(rows, columns=detector.feature_names, dtype="float64")
        return detector.score(frame)

    def _combine(
        self,
        snapshot: CustomerSnapshot,
        product: Product,
        quality: QualityReport,
        conflicts: list[TrustIssue],
        ood: float,
    ) -> TrustAssessment:
        w = self._weights
        t = self._thresholds
        consistency = cross_source_consistency(conflicts)
        excess = _clip01((ood - t.ood_excess_start) / (1.0 - t.ood_excess_start))
        raw = (
            w.completeness * quality.completeness
            + w.freshness * quality.freshness
            + w.consistency * consistency
            + w.ood * (1.0 - excess)
        )

        issues = [*quality.issues, *conflicts]
        caps: list[float] = []
        if not quality.critical_fields_present:
            caps.append(t.critical_cap)
        if any(issue.severity is Severity.HIGH for issue in issues):
            caps.append(t.high_issue_cap)
        if ood >= t.ood:
            issues.append(TrustIssue(
                code=TrustIssueCode.OUT_OF_DISTRIBUTION,
                category=TrustIssueCategory.OOD,
                severity=Severity.HIGH,
                message=(
                    f"Feature profile is out of distribution (OOD score {ood:.3f} >= {t.ood}); "
                    "the customer resembles little of the training population."
                ),
            ))
            caps.append(t.ood_cap)

        score = min([_clip01(raw), *caps])
        if not quality.critical_fields_present:
            status = TrustStatus.INSUFFICIENT
        else:
            status = _band(score, t)
        return TrustAssessment(
            customer_id=snapshot.customer_id,
            product=product,
            score=score,
            status=status,
            completeness=quality.completeness,
            freshness=quality.freshness,
            cross_source_consistency=consistency,
            critical_fields_present=quality.critical_fields_present,
            ood_score=ood,
            issues=issues,
            method_version=TRUST_METHOD_VERSION,
            assessed_at=config.PREDICTION_TIMESTAMP,
        )


TRUST_FRAME_COLUMNS: Final = [
    "customer_id",
    "product",
    "score",
    "status",
    "completeness",
    "freshness",
    "consistency",
    "critical_fields_present",
    "ood_score",
    "has_high_conflict",
    "issue_codes",
]


def trust_frame(assessments: Sequence[TrustAssessment]) -> pd.DataFrame:
    """Tidy summary with one row per assessment; ``issue_codes`` is ';'-joined in issue order."""
    rows = [
        {
            "customer_id": a.customer_id,
            "product": a.product.value,
            "score": a.score,
            "status": a.status.value,
            "completeness": a.completeness,
            "freshness": a.freshness,
            "consistency": a.cross_source_consistency,
            "critical_fields_present": a.critical_fields_present,
            "ood_score": a.ood_score,
            "has_high_conflict": a.has_high_severity_conflict,
            "issue_codes": ";".join(dict.fromkeys(issue.code.value for issue in a.issues)),
        }
        for a in assessments
    ]
    return pd.DataFrame(rows, columns=TRUST_FRAME_COLUMNS)
