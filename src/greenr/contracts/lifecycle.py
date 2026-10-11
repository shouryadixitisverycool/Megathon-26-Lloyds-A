"""Authorized factual source updates, separate from feedback and scenarios."""

from typing import Any

from pydantic import AwareDatetime, Field, model_validator

from greenr.contracts.base import Contract


class SourceUpdateRequest(Contract):
    request_id: str = Field(min_length=1, max_length=100)
    actor: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=1, max_length=2000)
    source_reference: str = Field(min_length=1, max_length=500)
    event_at: AwareDatetime
    available_at: AwareDatetime
    feature_cutoff: AwareDatetime
    vehicle: dict[str, Any] = Field(default_factory=dict)
    digital: dict[str, Any] = Field(default_factory=dict)
    ownership: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def governed_times(self):
        if not self.event_at <= self.available_at <= self.feature_cutoff:
            raise ValueError("Source event and availability must be at or before the cutoff")
        if not (self.vehicle or self.digital or self.ownership):
            raise ValueError("At least one factual source field must change")
        return self
