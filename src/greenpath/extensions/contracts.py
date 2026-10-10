"""Closed requests keep user actions separate from immutable scored evidence."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool

from greenpath.contracts.enums import Product


class Request(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    request_id: str | None = Field(default=None, min_length=1, max_length=100)


class CustomerRequest(Request):
    customer_id: str = Field(min_length=1, max_length=100)
    product: Product


class FeedbackRequest(CustomerRequest):
    response: Literal["SHOWN", "INTERESTED", "NOT_INTERESTED", "LATER", "ALREADY_COMPLETED", "DO_NOT_SHOW_AGAIN", "ACCEPTED", "CLOSED"]
    channel: Literal["app", "email", "phone", "rm"] = "app"
    note: str = Field(default="", max_length=2000)


class ReviewRequest(CustomerRequest):
    action: Literal["ACCEPT", "SUPPRESS", "FLAG_DATA_ISSUE", "REQUEST_REVIEW"]
    reviewer: str = Field(min_length=1, max_length=100)
    note: str = Field(min_length=1, max_length=2000)


class PreferencesRequest(Request):
    do_not_contact: StrictBool = False
    channel_consent: dict[Literal["app", "email", "phone", "rm"], StrictBool] = Field(default_factory=dict)


class SimulationRequest(Request):
    product: Product
    inputs: dict[str, Any]


class SensitivityRequest(Request):
    product: Product
    changes: dict[str, float | None] = Field(min_length=1, max_length=6)


class PlanningRequest(Request):
    product: Product
    target_count: int = Field(default=100, ge=0, le=100000)
    conversion_rate: float = Field(default=0.05, ge=0, le=1)
    region: str | None = None
    segment: str | None = None


class CampaignRequest(PlanningRequest):
    objective: Literal["conversions", "impact", "balanced"] = "conversions"
    channel: Literal["app", "email", "phone", "rm"] = "app"
    channel_capacity: int = Field(default=100, ge=0, le=100000)
    execute: StrictBool = False
