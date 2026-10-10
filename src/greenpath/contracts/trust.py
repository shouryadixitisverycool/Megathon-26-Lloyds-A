"""Trust: adequacy of the input evidence. Distinct from model confidence (spec 15)."""

from datetime import datetime

from pydantic import Field, model_validator

from greenpath.contracts.base import CONTRACT_VERSION, Contract, Probability
from greenpath.contracts.enums import (
    Product,
    Severity,
    TrustIssueCategory,
    TrustIssueCode,
    TrustStatus,
)


class TrustIssue(Contract):
    code: TrustIssueCode
    category: TrustIssueCategory
    severity: Severity
    message: str
    fields: list[str] = Field(default_factory=list)


class TrustAssessment(Contract):
    contract_version: str = CONTRACT_VERSION
    customer_id: str
    product: Product
    score: Probability
    status: TrustStatus
    completeness: Probability
    freshness: Probability
    cross_source_consistency: Probability
    critical_fields_present: bool
    ood_score: Probability  # 0 = typical of training data, 1 = beyond all training data
    issues: list[TrustIssue] = Field(default_factory=list)
    method_version: str
    assessed_at: datetime

    @model_validator(mode="after")
    def _critical_fields_fail_closed(self) -> "TrustAssessment":
        if not self.critical_fields_present and self.status is not TrustStatus.INSUFFICIENT:
            raise ValueError("missing critical fields require status INSUFFICIENT (spec 17.4)")
        return self

    @property
    def has_high_severity_conflict(self) -> bool:
        return any(
            i.category is TrustIssueCategory.CONFLICT and i.severity is Severity.HIGH
            for i in self.issues
        )
