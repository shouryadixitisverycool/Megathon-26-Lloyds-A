"""Strict partner catalogue schema and packaged JSON loader.

Edit ``catalogue.json`` to change the illustrative concepts or, after partner
selection, add real products. Keep the documented fields and exact product
category names. Set ``promoted`` to control endpoint visibility; valid but
unpromoted candidates are checked on load and then omitted from the returned
catalogue. Set ``GREENPATH_PARTNER_CATALOGUE`` to a UTF-8 JSON file for an
operator-managed catalogue, or pass a ``Path`` directly to ``load_catalogue``
(``path`` takes precedence over the environment variable).

Placeholder concepts must have ``source`` and ``destination_url`` set to null.
For a real product, set ``placeholder`` to false and provide both an HTTPS
``destination_url`` and a provenance ``source`` with a descriptive label and
HTTPS URL. Update the disclosure and revenue path to the actual, reviewed
terms; do not imply an agreed relationship, guaranteed outcome, or revenue
that does not exist. The loader performs no network requests or writes.

Field guide: ``version`` identifies the editable revision and ``reviewed_on``
is its ISO review date. Each category's ``product`` is one of the three
supported codes; its ``title``, ``subtitle`` and ``hero_tag`` are Explore copy.
Each option's ``id`` is unique catalogue-wide; ``partner`` and ``relationship``
identify the proposed or actual counterparty status; ``summary``, ``highlights``
and ``cta_label`` are display copy; ``suitability`` and ``disclosure`` carry
non-guaranteed context; and ``revenue_path`` describes only the actual or
proposed commercial route. ``placeholder`` marks an illustrative concept and
``promoted`` controls visibility. ``source`` records provenance, while
``destination_url`` is the provider action link; both are null for placeholders
and required for real products. Top-level ``disclaimer`` and
``commercial_disclaimer`` are shown with the catalogue.
"""

from __future__ import annotations

import json
import os
from datetime import date
from importlib.resources import files
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictStr,
    field_validator,
    model_validator,
)

Product = Literal["EV_FINANCE", "SOLAR_FINANCE", "GREEN_HOME"]
NonEmptyString = Annotated[StrictStr, Field(min_length=1)]


class _CatalogueModel(BaseModel):
    """Shared strict JSON contract; rejects misspelled or coerced fields."""

    model_config = ConfigDict(extra="forbid", strict=True)

    @field_validator("*", mode="after")
    @classmethod
    def reject_blank_text(cls, value):
        if isinstance(value, str) and not value.strip():
            raise ValueError("must not be blank")
        if isinstance(value, list) and any(
            isinstance(item, str) and not item.strip() for item in value
        ):
            raise ValueError("items must not be blank")
        return value


def _validate_https_url(value: str) -> str:
    """Accept absolute HTTPS links only, never credential-bearing URLs."""
    if value != value.strip() or any(
        char.isspace() or ord(char) < 32 for char in value
    ):
        raise ValueError("URL must not contain whitespace or control characters")
    try:
        parts = urlsplit(value)
        hostname = parts.hostname
        # Accessing .port also rejects malformed and out-of-range port numbers.
        port = parts.port
    except ValueError as exc:
        raise ValueError("URL must be a valid absolute HTTPS URL") from exc
    if (
        parts.scheme.lower() != "https"
        or not parts.netloc
        or not hostname
        or parts.username is not None
        or parts.password is not None
        or (port is not None and not 1 <= port <= 65535)
    ):
        raise ValueError(
            "URL must use HTTPS, include a hostname, and contain no credentials"
        )
    return value


class PartnerSource(_CatalogueModel):
    """Auditable provenance for a real partner product."""

    label: NonEmptyString = Field(
        description="Human-readable name of the source document or page."
    )
    url: NonEmptyString = Field(
        description="HTTPS URL for the source used to verify this product."
    )

    @field_validator("url")
    @classmethod
    def url_must_be_safe_https(cls, value: str) -> str:
        return _validate_https_url(value)


class PartnerOption(_CatalogueModel):
    """One candidate or promoted partner concept, not a credit decision."""

    id: NonEmptyString = Field(
        description="Unique stable option identifier across the full catalogue."
    )
    partner: NonEmptyString = Field(
        description=(
            "Generic demo partner for concepts, or selected provider "
            "for a real product."
        )
    )
    relationship: NonEmptyString = Field(
        description="Plain-language status of the commercial relationship."
    )
    title: NonEmptyString = Field(
        description="Short option heading shown to customers."
    )
    summary: NonEmptyString = Field(
        description="Concise aspirational description without unsubstantiated claims."
    )
    highlights: list[NonEmptyString] = Field(
        min_length=1, description="Short supporting points shown for this option."
    )
    suitability: NonEmptyString = Field(
        description=(
            "Indicative context only; never a personal recommendation "
            "or eligibility decision."
        )
    )
    disclosure: NonEmptyString = Field(
        description="Customer-facing limitations and relevant product/offer caveats."
    )
    revenue_path: NonEmptyString = Field(
        description=(
            "Actual or proposed commercial route; do not imply "
            "unagreed or guaranteed revenue."
        )
    )
    source: PartnerSource | None = Field(
        description="Provenance for a real product; null for placeholders."
    )
    destination_url: NonEmptyString | None = Field(
        description="Provider action URL for a real product; null for placeholders."
    )
    cta_label: NonEmptyString = Field(
        description=(
            "Short action label; does not imply a working link for placeholders."
        )
    )
    placeholder: StrictBool = Field(
        description="True for an illustrative concept that is not a live partner offer."
    )
    promoted: StrictBool = Field(
        description="Whether this option is exposed by the promoted catalogue loader."
    )

    @field_validator("destination_url")
    @classmethod
    def destination_must_be_safe_https(cls, value: str | None) -> str | None:
        if value is not None:
            return _validate_https_url(value)
        return value

    @model_validator(mode="after")
    def links_match_placeholder_status(self) -> PartnerOption:
        if self.placeholder and (
            self.source is not None or self.destination_url is not None
        ):
            raise ValueError(
                "placeholder options must not include source or destination links"
            )
        if not self.placeholder and (
            self.source is None or self.destination_url is None
        ):
            raise ValueError(
                "real options require HTTPS source provenance and destination URLs"
            )
        return self


class PartnerCategory(_CatalogueModel):
    """Promotions grouped under one supported Explore category."""

    product: Product = Field(
        description=(
            "Supported product category: EV_FINANCE, SOLAR_FINANCE, or GREEN_HOME."
        )
    )
    title: NonEmptyString = Field(description="Category heading shown in Explore.")
    subtitle: NonEmptyString = Field(
        description="Brief category explanation shown in Explore."
    )
    hero_tag: NonEmptyString = Field(
        description="Short visual tag or eyebrow for the category."
    )
    options: list[PartnerOption] = Field(
        description="Candidate options; loader output contains promoted entries only."
    )


class PartnerCatalogue(_CatalogueModel):
    """Catalogue envelope returned to the partner promotions endpoint."""

    version: NonEmptyString = Field(
        description="Editable catalogue revision identifier."
    )
    reviewed_on: NonEmptyString = Field(
        description="Date reviewed in ISO YYYY-MM-DD format."
    )
    disclaimer: NonEmptyString = Field(
        description=(
            "Customer-facing disclaimer for illustrative and real product content."
        )
    )
    commercial_disclaimer: NonEmptyString = Field(
        description="Status of any commercial relationship and revenue arrangements."
    )
    products: list[PartnerCategory] = Field(
        description="Categories available to the Explore experience."
    )

    @field_validator("reviewed_on")
    @classmethod
    def reviewed_on_is_iso_date(cls, value: str) -> str:
        try:
            parsed = date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(
                "reviewed_on must be an ISO-8601 date (YYYY-MM-DD)"
            ) from exc
        if parsed.isoformat() != value:
            raise ValueError("reviewed_on must use the YYYY-MM-DD format")
        return value

    @model_validator(mode="after")
    def keys_are_unique(self) -> PartnerCatalogue:
        products = [category.product for category in self.products]
        if len(products) != len(set(products)):
            raise ValueError("product categories must be unique")

        option_ids = [
            option.id for category in self.products for option in category.options
        ]
        if len(option_ids) != len(set(option_ids)):
            raise ValueError("option ids must be unique across the catalogue")
        return self


def _read_source(path: Path | None) -> str:
    if path is not None:
        source = path
    else:
        configured_path = os.getenv("GREENPATH_PARTNER_CATALOGUE")
        source = (
            Path(configured_path)
            if configured_path
            else files(__package__).joinpath("catalogue.json")
        )
    return source.read_text(encoding="utf-8")


def load_catalogue(path: Path | None = None) -> PartnerCatalogue:
    """Load, validate, and return a fresh promoted-only catalogue.

    ``path`` overrides ``GREENPATH_PARTNER_CATALOGUE``; otherwise the packaged
    JSON is used. The full document is validated before unpublished candidates
    are filtered so duplicate IDs and invalid URLs cannot hide in that source.
    """
    payload = json.loads(_read_source(path))
    catalogue = PartnerCatalogue.model_validate(payload)
    promoted_products = [
        category.model_copy(
            deep=True,
            update={
                "options": [option for option in category.options if option.promoted]
            },
        )
        for category in catalogue.products
    ]
    return catalogue.model_copy(deep=True, update={"products": promoted_products})


def get_promoted_catalogue(path: Path | None = None) -> PartnerCatalogue:
    """Return the same promoted-only response model as :func:`load_catalogue`."""
    return load_catalogue(path)
