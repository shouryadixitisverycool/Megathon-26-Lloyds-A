"""Partner promotion catalogue models and loader.

Use :func:`load_catalogue` for the endpoint-ready, promoted-only catalogue.
"""

from .catalogue import (
    PartnerCatalogue,
    PartnerCategory,
    PartnerOption,
    PartnerSource,
    get_promoted_catalogue,
    load_catalogue,
)

__all__ = [
    "PartnerCatalogue",
    "PartnerCategory",
    "PartnerOption",
    "PartnerSource",
    "get_promoted_catalogue",
    "load_catalogue",
]
