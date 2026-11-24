"""Deterministic prioritization with ownership and eligibility gates."""

from collections import defaultdict
from dataclasses import dataclass
from statistics import mean

from data_services.customer_portfolio import Customer
from data_services.market_catalog import MarketCatalog, Product, Source
from strategy_models.growth_research import (
    CATEGORY_LABELS,
    CATEGORY_VALUE,
    PRODUCT_CLASS,
    SEGMENT_PRIORITIES,
    Dimension,
    complement,
    documented_integration,
    product_sources,
)

FACTORS = {
    "relevance": "Workflow relevance",
    "fit": "Segment fit",
    "value": "Commercial value hypothesis",
    "feasibility": "Ease of implementation",
}
DIAGNOSTICS = {"compatibility": "Documented compatibility", "evidence": "Evidence confidence"}
DEFAULT_WEIGHTS = dict(zip(FACTORS, (25, 35, 20, 20), strict=True))
ATTRACTIVENESS_QUALIFIER = "Attractiveness scores are heuristics for strategic discovery, not validated probabilities, forecasts or predictions of commercial success."
METHODOLOGY = (
    "Commercial attractiveness is a weighted 0–100 decision-support heuristic. "
    "Evidence confidence and documented compatibility are displayed separately. Owned and explicitly "
    "ineligible products are excluded. Unknown ownership or eligibility routes a case to discovery."
)
RUBRIC = (
    "Workflow relevance: 4 for a complementary anchor, 2 without a known anchor, 1 for a known anchor "
    "with no mapped complement. Segment fit: 4 for primary priorities, 3 for secondary priorities, "
    "2 for an unknown segment, 1 otherwise. Commercial value: 3 for a direct booking, payments or "
    "guest monetization hypothesis, 2 for enabling workflows. Feasibility: category planning "
    "baseline of 2 for more systems-intensive work or 3 for a narrower workflow. "
    "Evidence confidence: one point each for product documentation, known ownership, affirmative eligibility "
    "and a documented integration with an anchor. Compatibility and confidence do not change attractiveness."
)


@dataclass(frozen=True)
class Candidate:
    row: int
    segment: str | None
    product: Product
    score: float
    factors: dict[str, int]
    ownership_known: bool
    eligibility_known: bool
    readiness: str
    rationale: str
    benefit: str
    execution: str
    compatibility: str
    sources: tuple[Source, ...]


@dataclass(frozen=True)
class Priority:
    segment: str | None
    product: Product
    score: float
    evidence: float
    fit: float
    count: int
    pilot_count: int
    benefit: str
    execution: str
    sources: tuple[Source, ...]


def weighted_score(factors: dict[str, int], weights: dict[str, int]) -> float:
    if not FACTORS.keys() <= weights.keys() or any(value < 0 or value > 100 for value in weights.values()):
        raise ValueError("Provide one weight from 0 to 100 for each scoring criterion.")
    total = sum(weights[key] for key in FACTORS)
    if not total:
        raise ValueError("Set at least one strategic priority weight above zero.")
    return 25 * sum(weights[key] * factors[key] for key in FACTORS) / total


def evaluate(
    catalog: MarketCatalog, customer: Customer, product: Product, dimension: Dimension,
    weights: dict[str, int], *, row: int, hypothetical_anchor: str | None = None,
) -> Candidate | None:
    owned = customer.owned
    if product.id in (owned or ()) or product.id in customer.ineligible:
        return None
    sources = product_sources(catalog, product)
    if not sources or catalog.evidence_status(product.source_ids) != "verified":
        return None

    category = PRODUCT_CLASS[product.id]
    segment = customer.segment(dimension)
    priorities = SEGMENT_PRIORITIES.get(segment, ()) if segment else ()
    fit = 4 if category in priorities[:2] else 3 if category in priorities else 1 if segment else 2
    eligible = product.id in customer.eligible
    owned_ids = owned or frozenset()
    anchors = (
        (hypothetical_anchor,) if hypothetical_anchor else
        tuple(sorted({PRODUCT_CLASS[key] for key in owned_ids if key in PRODUCT_CLASS}))
    )
    paired = next(
        (rule for anchor in anchors if (rule := complement(anchor, category)) is not None), None
    )
    anchor_products = owned_ids if not hypothetical_anchor else frozenset(
        item.id for item in catalog.company_products(product.company_id)
        if PRODUCT_CLASS.get(item.id) == hypothetical_anchor
    )
    verified = documented_integration(catalog, product.id, anchor_products)
    benefit, effort = CATEGORY_VALUE[category]
    factors = {
        "relevance": 4 if paired else 1 if anchors else 2,
        "fit": fit,
        "compatibility": 4 if verified else 2,
        "value": 3 if category in {"booking", "payments", "guest"} else 2,
        "feasibility": effort,
        "evidence": 1 + int(owned is not None) + int(eligible) + int(verified is not None),
    }
    if verified:
        integration, source = verified
        compatibility = (
            f"Hypothetical anchor · {integration.detail}" if hypothetical_anchor else integration.detail
        )
        if source not in sources:
            sources += (source,)
    else:
        compatibility = "Technical compatibility is unverified for this scenario."
    readiness = "Pilot candidate" if owned is not None and eligible else "Discovery only"
    return Candidate(
        row=row, segment=segment, product=product, score=weighted_score(factors, weights),
        factors=factors, ownership_known=owned is not None, eligibility_known=eligible,
        readiness=readiness, rationale=paired.rationale if paired else (
            f"Evaluate {CATEGORY_LABELS[category].lower()} against the segment’s workflow priorities."
        ),
        benefit=benefit, execution=paired.execution if paired else (
            "Confirm buyer, existing systems, rollout effort and commercial terms."
        ),
        compatibility=compatibility, sources=sources,
    )


def rank_candidates(
    catalog: MarketCatalog, customers: tuple[Customer, ...], products: tuple[Product, ...],
    dimension: Dimension, weights: dict[str, int], *, hypothetical_anchor: str | None = None,
) -> list[Candidate]:
    weighted_score(dict.fromkeys(FACTORS, 0), weights)
    candidates = [
        candidate
        for row, customer in enumerate(customers, start=1)
        for product in products
        if (candidate := evaluate(
            catalog, customer, product, dimension, weights, row=row, hypothetical_anchor=hypothetical_anchor
        )) is not None
    ]
    return sorted(candidates, key=lambda item: (-item.score, item.product.id, item.row))


def prioritize(candidates: list[Candidate]) -> list[Priority]:
    groups: dict[tuple[str | None, str], list[Candidate]] = defaultdict(list)
    for item in candidates:
        groups[item.segment, item.product.id].append(item)
    priorities = [
        Priority(
            segment=items[0].segment, product=items[0].product,
            score=mean(item.score for item in items),
            evidence=mean(item.factors["evidence"] for item in items),
            fit=mean(item.factors["fit"] for item in items),
            count=len(items),
            pilot_count=sum(item.readiness == "Pilot candidate" for item in items),
            benefit=items[0].benefit,
            execution=" ".join(dict.fromkeys(item.execution for item in items)),
            sources=tuple({source.id: source for item in items for source in item.sources}.values()),
        )
        for items in groups.values()
    ]
    return sorted(priorities, key=lambda item: (-item.score, item.product.id, item.segment or ""))
