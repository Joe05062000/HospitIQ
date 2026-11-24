"""Session-only handoff containing public evidence and validated aggregate counts."""

from dataclasses import dataclass

from data_services.customer_portfolio import Customer
from data_services.market_catalog import MarketCatalog
from strategy_models.growth_engine import Priority
from strategy_models.growth_research import PRODUCT_CLASS, SEGMENTS, Dimension

HANDOFF_KEY = "financial_opportunity_handoff"


@dataclass(frozen=True)
class Opportunity:
    product_id: str
    category: str
    segment: str | None
    source_ids: tuple[str, ...]
    known_eligible: int | None = None
    eligibility_status: str = "Eligibility requires validation"
    uncounted_qualifying_rows: int = 0
    fictional_label: str | None = None

    @property
    def identifier(self) -> str:
        if self.fictional_label:
            return "fictional-payments-case"
        return f"{self.product_id}:{self.segment or 'unclassified'}"


def opportunity_from_growth(
    priority: Priority, customers: tuple[Customer, ...], dimension: Dimension, *,
    real_portfolio: bool,
) -> Opportunity:
    product = priority.product.id
    matching = (
        customer for customer in customers
        if customer.segment(dimension) == priority.segment
        and customer.owned is not None and product not in customer.owned
        and product in customer.eligible and product not in customer.ineligible
    )
    confirmed_ids: set[str] = set()
    uncounted = 0
    if real_portfolio:
        qualifying = tuple(matching)
        id_counts: dict[str, int] = {}
        for customer in customers:
            if customer.id:
                key = customer.id.strip().casefold()
                id_counts[key] = id_counts.get(key, 0) + 1
        for customer in qualifying:
            if customer.id and id_counts.get(customer.id.strip().casefold()) == 1:
                confirmed_ids.add(customer.id.strip().casefold())
            else:
                uncounted += 1

    # Zero validated IDs leaves population unknown rather than asserting there are zero opportunities.
    known = len(confirmed_ids) or None
    return Opportunity(
        product_id=product, category=PRODUCT_CLASS[product], segment=priority.segment,
        source_ids=tuple(dict.fromkeys(source.id for source in priority.sources)),
        known_eligible=known,
        eligibility_status="Confirmed within uploaded inputs" if known is not None else "Eligibility requires validation",
        uncounted_qualifying_rows=uncounted,
    )


def validated_handoff(catalog: MarketCatalog, candidate: object) -> Opportunity | None:
    if not isinstance(candidate, Opportunity):
        return None
    product = catalog.products.get(candidate.product_id)
    if (
        product is None or PRODUCT_CLASS.get(product.id) != candidate.category
        or (candidate.segment is not None and candidate.segment not in SEGMENTS)
        or catalog.evidence_status(product.source_ids) != "verified"
    ):
        return None
    return candidate
