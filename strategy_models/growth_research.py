"""Editable product taxonomy, segment profiles, and commercial hypotheses."""

from dataclasses import dataclass
from typing import Literal

from data_services.market_catalog import MarketCatalog, Product, Source
from strategy_models.benchmark import verified_products

Dimension = Literal["organization", "property"]
DIMENSIONS: dict[Dimension, str] = {"organization": "Organization size", "property": "Primary property type"}
CATEGORY_LABELS = {
    "pms": "Property management",
    "distribution": "Hotel distribution",
    "booking": "Direct booking",
    "payments": "Payments",
    "guest": "Guest experience and merchandising",
    "revenue": "Revenue management",
    "analytics": "Analytics and data",
}
PRODUCT_CLASS = {
    "opera-pms": "pms", "opera-distribution": "distribution", "opera-merchandising": "guest",
    "oracle-payments": "payments", "mews-pms": "pms", "mews-pay": "payments",
    "mews-journey": "guest", "mews-rms": "revenue", "ihotelier-booking": "booking",
    "ihotelier-crs": "distribution", "demand360": "analytics", "amadeus-gms": "guest",
    "sm-manager": "distribution", "sm-channels-plus": "distribution", "sm-booking": "booking",
    "sm-revenue": "revenue",
}


@dataclass(frozen=True)
class Segment:
    id: str
    label: str
    dimension: Dimension
    definition: str
    needs: tuple[str, ...]


NEED_LABELS = (
    "Operations and property characteristics", "Distribution", "Payments",
    "Guest experience", "Revenue management", "Data and analytics",
)

SEGMENTS = {
    item.id: item for item in (
        Segment("independent", "Independent hotels", "organization", "One hotel under common operating control.", (
            "Small teams may need fewer manual handoffs.", "Balance direct and third-party bookings.",
            "Reconcile deposits and refunds with limited back-office capacity.", "Offer self-service where it reduces desk workload.",
            "Use manageable pricing rules and alerts.", "Track performance without a dedicated analyst.",
        )),
        Segment("small-group", "Small hotel groups", "organization", "Two to nine hotels under common operating control.", (
            "Standardize processes while allowing local exceptions.", "Coordinate availability across properties and channels.",
            "Unify settlement review and property-level reporting.", "Keep communications consistent across properties.",
            "Share pricing practices across a small portfolio.", "Compare performance using common definitions.",
        )),
        Segment("large-chain", "Large hotel chains", "organization", "Ten or more hotels under common operating control.", (
            "Coordinate brand standards, roles, and exception handling.", "Support centralized rules and regional connectivity.",
            "Accommodate local tenders, entities, and settlement requirements.", "Coordinate guest profiles and brand standards.",
            "Balance central guidance and property control.", "Prioritize governance, integration, and data access.",
        )),
        Segment("luxury", "Luxury hotels", "property", "Primary positioning is luxury service, excluding destination resorts in this taxonomy.", (
            "Preserve high-touch service while coordinating complex requests.", "Control presentation of premium offers and packages.",
            "Manage deposits, authorization and service exceptions.", "Personalize offers and handoffs with staff oversight.",
            "Protect rate and package integrity.", "Understand guest preferences within consent boundaries.",
        )),
        Segment("limited-service", "Limited-service hotels", "property", "Primary positioning is limited service, excluding resorts and luxury hotels.", (
            "Reduce repetitive tasks with lean staffing.", "Keep rates and availability consistent with minimal manual work.",
            "Simplify checkout, refunds and reconciliation.", "Prioritize reliable self-service and clear communications.",
            "Use simple pricing recommendations and guardrails.", "Track conversion, exceptions and channel contribution.",
        )),
        Segment("resort", "Resorts", "property", "Primary positioning is destination resort, regardless of service tier.", (
            "Coordinate rooms, amenities and seasonal staffing.", "Represent packages and restrictions consistently by channel.",
            "Handle advance deposits and charges for add-ons.", "Merchandise activities and coordinate fulfillment.",
            "Plan for seasonality and package constraints.", "Review booking pace and purchases across activities.",
        )),
    )
}

# Primary priorities first. These are hypotheses, independent of vendor evidence.
SEGMENT_PRIORITIES = {
    "independent": ("pms", "distribution", "payments", "booking"),
    "small-group": ("distribution", "payments", "analytics", "pms"),
    "large-chain": ("analytics", "distribution", "pms", "revenue"),
    "luxury": ("guest", "booking", "payments", "analytics"),
    "limited-service": ("pms", "payments", "distribution", "booking"),
    "resort": ("guest", "revenue", "payments", "booking"),
}


@dataclass(frozen=True)
class Complement:
    categories: tuple[str, str]
    rationale: str
    execution: str


COMPLEMENTS = (
    Complement(("pms", "payments"), "Connect reservations and folios to collection and reconciliation workflows.",
               "Confirm supported payment methods, settlement, refunds and reconciliation ownership."),
    Complement(("pms", "guest"), "Use reservation context to support guest communications and fulfillment.",
               "Confirm data permissions, staff handoffs and the supported reservation workflow."),
    Complement(("pms", "distribution"), "Coordinate room availability and rate changes across hotel operations and channels.",
               "Check room/rate mapping, inventory recovery and which system controls availability."),
    Complement(("pms", "revenue"), "Use operational and reservation context to inform rate decisions.",
               "Confirm how rates move into operational systems and who can override changes."),
    Complement(("distribution", "booking"), "Manage direct demand alongside channel reach and availability.",
               "Validate inventory synchronization and the direct booking journey."),
    Complement(("distribution", "revenue"), "Apply pricing decisions across the channels that sell hotel inventory.",
               "Test rate restrictions, approval rules and channel synchronization."),
    Complement(("analytics", "revenue"), "Use demand signals to assess pricing decisions and their context.",
               "Validate data coverage, refresh cadence and how analysts translate signals into actions."),
    Complement(("analytics", "distribution"), "Review demand and channel performance before changing distribution priorities.",
               "Confirm attribution, channel dimensions and whether data is comparable across properties."),
    Complement(("booking", "guest"), "Carry guest context and relevant offers from booking into the stay.",
               "Confirm identity matching, offer fulfillment and consent boundaries."),
    Complement(("booking", "payments"), "Connect direct reservations to deposits and changes in payment status.",
               "Test payment failure recovery, refund policy and supported currencies."),
    Complement(("guest", "payments"), "Connect the purchase of an add-on with collection, refund and reconciliation.",
               "Check transaction references, charge ownership and exception handling."),
)

CATEGORY_VALUE = {
    "pms": ("Reduce manual handoffs between reservations, front desk and operations.", 2),
    "distribution": ("Improve consistency of rates and inventory across sales channels.", 2),
    "booking": ("Simplify direct booking and identify gaps in the purchase flow.", 3),
    "payments": ("Reduce avoidable collection and reconciliation work.", 2),
    "guest": ("Improve guest handoffs and test take-up of relevant services.", 3),
    "revenue": ("Support timelier pricing decisions with defined controls.", 2),
    "analytics": ("Give commercial teams a more consistent view of demand and performance.", 3),
}


@dataclass(frozen=True)
class Integration:
    products: tuple[str, str]
    source_id: str
    detail: str


INTEGRATIONS = (
    Integration(("mews-pms", "mews-pay"), "mews-payments",
                "Mews documents Payments as embedded in its property management and point-of-sale products."),
    Integration(("mews-pms", "mews-journey"), "mews-guest",
                "Mews documents Guest Journey configuring booking and arrival workflows in Mews Operations."),
)


def complement(left: str, right: str) -> Complement | None:
    return next((item for item in COMPLEMENTS if set(item.categories) == {left, right}), None)


def product_sources(catalog: MarketCatalog, product: Product) -> tuple[Source, ...]:
    return tuple(catalog.sources[key] for key in product.source_ids if catalog.sources[key].status == "verified")


def growth_products(catalog: MarketCatalog, company_id: str) -> dict[str, Product]:
    return {item.id: item for item in verified_products(catalog, company_id) if item.id in PRODUCT_CLASS}


def documented_integration(
    catalog: MarketCatalog, product_id: str, anchor_ids: frozenset[str]
) -> tuple[Integration, Source] | None:
    for entry in INTEGRATIONS:
        source = catalog.sources.get(entry.source_id)
        if product_id not in entry.products or source is None or source.status != "verified":
            continue
        other = next(key for key in entry.products if key != product_id)
        if other in anchor_ids and all(
            key in catalog.products and catalog.evidence_status(catalog.products[key].source_ids) == "verified"
            for key in entry.products
        ):
            return entry, source
    return None
