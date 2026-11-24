"""Evidence-backed comparisons using the curated market catalog."""

from dataclasses import dataclass
from typing import Literal

from data_services.market_catalog import Development, MarketCatalog, Product, Source

CATEGORIES = {
    "distribution": "Hotel distribution",
    "pms": "Property management",
    "payments": "Payments",
    "booking": "Booking technology",
    "retailing": "Retailing and upselling",
    "ai": "AI and automation",
    "revenue": "Revenue management",
    "analytics": "Analytics and business intelligence",
    "segments": "Documented customer segments",
    "partnerships": "Strategic partnerships",
}

PRODUCT_CATEGORIES = {
    "opera-pms": ("pms",),
    "opera-distribution": ("distribution",),
    "opera-merchandising": ("retailing",),
    "oracle-payments": ("payments",),
    "mews-pms": ("pms",),
    "mews-pay": ("payments",),
    "mews-journey": ("booking", "retailing"),
    "mews-rms": ("revenue",),
    "ihotelier-booking": ("booking", "retailing"),
    "ihotelier-crs": ("distribution", "booking"),
    "demand360": ("analytics",),
    "sm-manager": ("distribution",),
    "sm-channels-plus": ("distribution",),
    "sm-booking": ("booking",),
    "sm-revenue": ("revenue",),
}


@dataclass(frozen=True)
class Evidence:
    text: str
    sources: tuple[Source, ...]
    stage: str | None = None


@dataclass(frozen=True)
class DocumentedClaim:
    company: str
    category: str
    text: str
    source_id: str
    stage: str = "Existing capability"


# Each claim covers only the stated fact. Planned releases retain that qualifier.
CLAIMS = (
    DocumentedClaim("oracle", "analytics", "OPERA Cloud Reporting and Analytics is listed in the hotel portfolio.", "oracle-portfolio"),
    DocumentedClaim("oracle", "ai", "Oracle announced OPERA Cloud Assistant, including AI-assisted room assignment.", "oracle-assistant", "Announced capability"),
    DocumentedClaim("mews", "analytics", "Mews lists business intelligence and reporting in its hospitality platform.", "mews-platform"),
    DocumentedClaim("mews", "ai", "Mews announced automated payment matching and task creation for upsells.", "mews-winter"),
    DocumentedClaim("mews", "distribution", "Mews lists direct Booking.com and Expedia connections as generally available.", "mews-marketplace-doc", "Existing integration"),
    DocumentedClaim("mews", "distribution", "The SiteMinder-powered native channel manager is documented as beta and rolling out.", "mews-marketplace-doc", "Beta rollout"),
    DocumentedClaim("mews", "distribution", "The May announcement described a planned native integration and future migrations.", "mews-siteminder", "Planned integration at announcement"),
    DocumentedClaim("mews", "partnerships", "Mews and SiteMinder announced an embedded distribution partnership.", "mews-siteminder", "Documented partnership"),
    DocumentedClaim("amadeus", "partnerships", "B2 Hotels announced plans to adopt iHotelier and related solutions.", "amadeus-b2", "Documented partnership"),
    DocumentedClaim("siteminder", "partnerships", "SiteMinder documents pricing recommendations developed with IDeaS.", "siteminder-products", "Documented partnership"),
    DocumentedClaim("siteminder", "partnerships", "SiteMinder and Mews announced an embedded distribution partnership.", "mews-siteminder", "Documented partnership"),
    DocumentedClaim("siteminder", "ai", "SiteMinder unveiled plans for AI-enabled pricing and distribution recommendations with hotel approval.", "siteminder-commerce", "Announced capability"),
    DocumentedClaim("siteminder", "analytics", "SiteMinder lists market, competitor and performance insights.", "siteminder-platform"),
    DocumentedClaim("siteminder", "payments", "SiteMinder lists hotel payments in its platform.", "siteminder-platform"),
)

# This snapshot has no source-backed scope exclusions.
ScopeExclusion = DocumentedClaim
SCOPE_EXCLUSIONS: tuple[ScopeExclusion, ...] = ()
EvidenceStatus = Literal["Documented capability", "Not verified in current research", "Not applicable", "Announced or limited availability"]


@dataclass(frozen=True)
class Cell:
    status: EvidenceStatus
    evidence: tuple[Evidence, ...] = ()


@dataclass(frozen=True)
class Contrast:
    companies: tuple[str, str]
    categories: tuple[str, str]
    source_ids: tuple[str, str]
    title: str
    significance: str
    investment: str
    expansion: str
    question: str


CONTRASTS = (
    Contrast(("oracle", "mews"), ("ai", "ai"), ("oracle-assistant", "mews-winter"), "Front-desk assistance and finance automation",
             "The examples target different hotel users and workflow problems.",
             "Validate staff adoption and exception handling before funding embedded automation.",
             "Explore packaging finance automation with property operations or vice versa.",
             "Which tasks consume staff time, and where do hotel teams require manual override?"),
    Contrast(("oracle", "amadeus"), ("pms", "booking"), ("oracle-hotels", "amadeus-booking"), "Property operations and reservation commerce",
             "Property operations and booking flows offer different points to integrate with hotel systems.",
             "Validate PMS and CRS interoperability and the migration effort for each workflow.",
             "Explore linking reservation merchandising to property operations.",
             "Which data can move between the systems, and who controls the integration?"),
    Contrast(("oracle", "siteminder"), ("pms", "distribution"), ("oracle-hotels", "siteminder-channels"), "Property operations and channel management",
             "Availability and rate updates cross the boundary between the front desk and distribution teams.",
             "Test reconciliation and failure recovery before investing in deeper synchronization.",
             "Explore a PMS-to-channel integration or joint implementation offer.",
             "How do oversell controls and exception handling work across connected systems?"),
    Contrast(("mews", "amadeus"), ("payments", "booking"), ("mews-payments", "amadeus-booking"), "Embedded payments and direct booking",
             "Booking conversion and payment collection create distinct integration requirements.",
             "Assess payment methods, settlement, and booking flow friction before prioritizing a combined workflow.",
             "Explore attaching embedded collection to direct booking workflows.",
             "Who owns checkout, payment failures, disputes, and the guest record?"),
    Contrast(("mews", "siteminder"), ("pms", "partnerships"), ("mews-operations", "mews-siteminder"), "Property operations and distribution partnerships",
             "The announced collaboration illustrates how a PMS can embed specialist distribution.",
             "Compare an embedded integration with building distribution connectivity directly.",
             "Explore bundling property operations with channel management and onboarding.",
             "Which channels and regions are live, and who owns support and commercial terms?"),
    Contrast(("amadeus", "siteminder"), ("analytics", "revenue"), ("amadeus-demand", "siteminder-products"), "Forward demand intelligence and daily pricing recommendations",
             "Market demand visibility and a recommendation to act can serve different revenue-team workflows.",
             "Test whether pairing forward indicators with controls improves the decision workflow.",
             "Explore a combined demand analytics and pricing offer with clear approval controls.",
             "How comparable are inputs, forecast horizons, market coverage and override controls?"),
)


@dataclass(frozen=True)
class Theme:
    name: str
    categories: tuple[str, ...]
    development_tags: tuple[str, ...]
    opportunity: str
    risk: str
    question: str


THEMES = (
    Theme("AI and automation", ("ai",), ("ai",), "Test automation in high-frequency workflows with human review.",
          "Availability, error rates and exception handling vary by workflow.", "Which tasks have a measurable baseline and a safe override?"),
    Theme("Payments", ("payments",), ("payments",), "Evaluate embedding payments and reconciliation into hotel workflows.",
          "Eligibility, payment costs and settlement vary by market.", "Which payment methods, currencies and settlement terms matter by segment?"),
    Theme("Hotel distribution", ("distribution",), ("distribution",), "Explore deeper synchronization between distribution, reservations and the PMS.",
          "Channel coverage and reliability depend on integrations and commercial agreements.", "Who owns failure recovery and onboarding?"),
    Theme("Retailing", ("retailing",), ("retailing",), "Test linking offers, checkout and fulfillment across the guest journey.",
          "Offer data and operational fulfillment can vary by property.", "Can teams measure take-up, refunds and fulfillment costs by offer?"),
    Theme("Guest experience", ("booking", "retailing"), ("guest",), "Explore consistent offers and guest handoffs from booking to arrival.",
          "Consent, identity matching and operational readiness may limit adoption.", "Which handoffs cause the most guest and staff friction?"),
    Theme("Analytics", ("analytics",), (), "Explore bringing market indicators and operational reporting into decision workflows.",
          "Inputs, coverage and update frequency differ across sources.", "Which datasets are representative and what decisions can they support?"),
)


def eligible_companies(catalog: MarketCatalog) -> tuple[str, ...]:
    return tuple(
        key for key, company in catalog.companies.items()
        if catalog.evidence_status(company.source_ids) == "verified"
    )


def verified_products(catalog: MarketCatalog, company: str) -> list[Product]:
    return [
        item for item in catalog.company_products(company)
        if catalog.evidence_status(item.source_ids) == "verified"
    ]


def classify(evidence: tuple[Evidence, ...], exclusions: tuple[Evidence, ...] = ()) -> Cell:
    if any(item.stage in {None, "Existing capability", "Existing integration", "Documented partnership"} for item in evidence):
        return Cell("Documented capability", evidence)
    if evidence:
        return Cell("Announced or limited availability", evidence)
    if exclusions:
        return Cell("Not applicable", exclusions)
    return Cell("Not verified in current research")


def statement_evidence(catalog: MarketCatalog, claim: DocumentedClaim) -> tuple[Evidence, ...]:
    source = catalog.sources.get(claim.source_id)
    if source and source.status == "verified":
        return (Evidence(claim.text, (source,), claim.stage),)
    return ()


@dataclass(frozen=True)
class Benchmark:
    catalog: MarketCatalog
    companies: tuple[str, ...]
    matrix: dict[str, dict[str, Cell]]

    @property
    def similarities(self) -> tuple[str, ...]:
        return tuple(
            key for key, row in self.matrix.items()
            if key != "segments" and all(cell.status == "Documented capability" for cell in row.values())
        )

    @property
    def contrasts(self) -> tuple[Contrast, ...]:
        return tuple(
            item for item in CONTRASTS
            if all(
                company in self.companies and self.contrast_evidence(item, index)
                for index, company in enumerate(item.companies)
            )
        )

    def contrast_evidence(self, contrast: Contrast, index: int) -> tuple[Evidence, ...]:
        company = contrast.companies[index]
        category = contrast.categories[index]
        return tuple(
            evidence for evidence in self.matrix[category][company].evidence
            if any(source.id == contrast.source_ids[index] for source in evidence.sources)
        )


def build_benchmark(catalog: MarketCatalog, selection: tuple[str, ...]) -> Benchmark:
    eligible = eligible_companies(catalog)
    if not 2 <= len(selection) <= 4 or len(set(selection)) != len(selection):
        raise ValueError("Select two to four distinct companies.")
    if any(company not in eligible for company in selection):
        raise ValueError("Select companies with verified profiles.")

    company_cells = {key: capability_cells(catalog, key) for key in selection}
    matrix = {
        category: {key: company_cells[key][category] for key in selection}
        for category in CATEGORIES
    }
    return Benchmark(catalog, selection, matrix)


def capability_cells(catalog: MarketCatalog, company_id: str) -> dict[str, Cell]:
    cells: dict[str, Cell] = {}
    company = catalog.companies[company_id]
    products = verified_products(catalog, company_id)
    for category in CATEGORIES:
        evidence = [
            Evidence(
                f"{product.name} · {product.description}",
                tuple(catalog.sources[key] for key in product.source_ids),
            )
            for product in products if category in PRODUCT_CATEGORIES.get(product.id, ())
        ]
        if category == "segments" and company.segments:
            evidence.append(Evidence(", ".join(company.segments), tuple(
                catalog.sources[key] for key in company.source_ids
            )))
        for claim in CLAIMS:
            if (claim.company, claim.category) == (company_id, category):
                evidence.extend(statement_evidence(catalog, claim))
        exclusions = tuple(
            item for claim in SCOPE_EXCLUSIONS
            if (claim.company, claim.category) == (company_id, category)
            for item in statement_evidence(catalog, claim)
        )
        cells[category] = classify(tuple(evidence), exclusions)
    return cells

def theme_developments(benchmark: Benchmark, theme: Theme) -> list[Development]:
    if not theme.development_tags:
        return []
    return benchmark.catalog.filter_developments(
        companies=set(benchmark.companies), themes=set(theme.development_tags), verified_only=True
    )


def theme_companies(benchmark: Benchmark, theme: Theme) -> tuple[str, ...]:
    developments = theme_developments(benchmark, theme)
    return tuple(
        company for company in benchmark.companies
        if any(benchmark.matrix[key][company].status == "Documented capability" for key in theme.categories)
        or any(company in item.company_ids for item in developments)
    )
