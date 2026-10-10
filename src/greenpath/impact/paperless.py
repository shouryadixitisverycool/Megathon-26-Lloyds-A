"""Fail closed until a defensible paper/digital carbon method is reviewed."""

from dataclasses import dataclass, field
from decimal import Context, localcontext
from typing import ClassVar

from ._contract_mirror import ImpactResult, IssueCode, Product
from .catalogue import FactorCatalogue
from .common import Clock, Method, Payload, prepare, utc_now
from .inputs import PaperlessInput

METHOD = Method(
    Product.PAPERLESS_BANKING, "paperless-carbon-unavailable-v1",
    "paper_statement_and_digital_delivery_comparison_not_established",
    "Paper statements; carbon boundary not established",
    "Digital delivery; carbon boundary not established",
    ("No carbon claim or tree equivalence derived from a physical sheet count",),
    ("A sheet count is a separate non-carbon metric; digital delivery is not assumed carbon-free.",),
)


@dataclass(frozen=True)
class PaperlessImpactCalculator:
    catalogue: FactorCatalogue = field(default_factory=FactorCatalogue.load)
    clock: Clock = utc_now
    product: ClassVar[Product] = Product.PAPERLESS_BANKING

    def calculate(self, payload: Payload) -> ImpactResult:
        p = prepare(payload, PaperlessInput, METHOD, self.catalogue, self.clock, needs_grid=False)
        if p.request and p.request.avoided_sheets is not None:
            p.unit(p.request.avoided_sheets, "sheets", "avoided_sheets")
            with localcontext(Context(prec=60)):
                if p.request.avoided_sheets.value % 1:
                    p.issue(IssueCode.INVALID_INPUT, "avoided_sheets", "Physical sheets must be a whole count")
        p.issue(IssueCode.FACTOR_NOT_ESTABLISHED, "paperless_carbon",
                "Supply a reviewed, versioned paper/digital boundary and compatible factors before calculating carbon")
        return p.finish()
