"""Evidence-based strategic briefs assembled from existing workspace engines."""

from dataclasses import dataclass

from data_services.customer_portfolio import Customer
from data_services.market_catalog import MarketCatalog, Source
from strategy_models.benchmark import build_benchmark
from strategy_models.financial import Projection, Sensitivity
from strategy_models.growth_engine import (
    DEFAULT_WEIGHTS,
    Candidate,
    rank_candidates,
)
from strategy_models.growth_playbook import pilot_metric
from strategy_models.growth_research import PRODUCT_CLASS, SEGMENTS, growth_products

FINANCIAL_BRIEF_KEY = "advisor_financial_snapshot"
GROWTH_BRIEF_KEY = "advisor_growth_context"


@dataclass(frozen=True)
class GrowthContext:
    company_id: str
    segment: str
    anchor: str
    products: tuple[str, ...]
    weights: tuple[tuple[str, int], ...]

QUESTIONS = {
    "growth": "Which product opportunity should we validate first?",
    "competition": "Where could vendors differentiate?",
    "market": "Which market developments warrant action?",
    "investment": "What evidence is needed before investing?",
    "tradeoff": "What should leadership compare in payments and AI-enabled operations?",
    "cross-sell": "What could derail a cross-sell to existing hotel customers?",
}
SECTION_NAMES = {
    "market": "Market Intelligence",
    "competition": "Competitive Benchmarking",
    "growth": "Product Growth Intelligence",
    "investment": "Investment due diligence",
    "cross-sell": "Cross-sell risk",
    "tradeoff": "Investment tradeoffs",
}


@dataclass(frozen=True)
class FinancialSnapshot:
    product_id: str
    segment: str | None
    currency: str
    origin: str
    scenarios: tuple[tuple[str, Projection], ...]
    fictional_label: str | None = None
    normalized_sensitivity: tuple[Sensitivity, ...] = ()
    business_sensitivity: tuple[Sensitivity, ...] = ()
    sensitivity_case: str | None = None


@dataclass(frozen=True)
class Finding:
    id: str
    section: str
    title: str
    evidence: str
    interpretation: str
    action: str
    sources: tuple[Source, ...]
    metric: str = "Validate what has shipped and obtain comparable operating evidence."
    assumption: str = ""
    evidence_confidence: int | None = None


@dataclass(frozen=True)
class PublicBrief:
    question: str
    companies: tuple[str, ...]
    segment: str
    theme: str | None
    findings: tuple[Finding, ...]
    opportunity: Finding | None = None

    def focus_section(self) -> str:
        return self.question

    def priority_order(self) -> tuple[str, ...]:
        eligible = tuple(item.id for item in self.findings if item.section == self.focus_section())
        if self.question == "growth":
            return eligible[:1]
        return eligible if self.question == "market" else eligible[:3]

    def align_priorities(self, model_choices: tuple[str, ...]) -> tuple[str, ...]:
        local = self.priority_order()
        if self.question == "growth":
            return local
        eligible = {item.id for item in self.findings if item.section == self.focus_section()}
        return tuple(key for key in model_choices if key in eligible)[:3] or local


def market_findings(
    catalog: MarketCatalog, company_ids: tuple[str, ...], theme: str | None
) -> list[Finding]:
    return [
        Finding(
            f"market-{item.id}", "market", item.title,
            f"{catalog.sources[item.source_id].published_on} · {item.summary}",
            f"{item.interpretation} {item.limitations}",
            item.questions[0], (catalog.sources[item.source_id],), item.implication,
        )
        for item in sorted(
            catalog.filter_developments(
                companies=set(company_ids), themes={theme} if theme else None, verified_only=True,
            ),
            key=lambda entry: entry.title.casefold(),
        )
    ]


def competitive_findings(catalog: MarketCatalog, company_ids: tuple[str, ...]) -> list[Finding]:
    if len(company_ids) < 2:
        return []
    benchmark = build_benchmark(catalog, company_ids)
    findings = []
    for contrast in benchmark.contrasts[:3]:
        evidence = [
            item for index in range(len(contrast.companies))
            for item in benchmark.contrast_evidence(contrast, index)
        ]
        findings.append(Finding(
            f"competition-{'-'.join(contrast.companies)}", "competition", contrast.title,
            " ".join(item.text for item in evidence),
            f"{contrast.significance} Opportunity to test: {contrast.expansion}", contrast.question,
            tuple({source.id: source for item in evidence for source in item.sources}.values()),
            contrast.investment, "The documented differences suggest testable positioning options. They do not establish vendor superiority.",
        ))
    return findings


def growth_findings(
    catalog: MarketCatalog, company_ids: tuple[str, ...], segment_id: str, context: GrowthContext | None = None,
) -> list[Finding]:
    segment = SEGMENTS[segment_id]
    profile = Customer(organization=segment_id) if segment.dimension == "organization" else Customer(
        property_type=segment_id
    )
    ranked: list[Candidate] = []
    for company_id in company_ids:
        products = growth_products(catalog, company_id)
        if not products:
            continue
        scoped = context if context and context.company_id == company_id and context.segment == segment_id else None
        anchor = scoped.anchor if scoped else PRODUCT_CLASS[next(iter(products))]
        weights = dict(scoped.weights) if scoped else DEFAULT_WEIGHTS
        ranked.extend(rank_candidates(
            catalog, (profile,), tuple(value for key, value in products.items() if not scoped or key in scoped.products),
            segment.dimension, weights, hypothetical_anchor=anchor,
        ))
    ranked.sort(key=lambda item: (-item.score, item.product.id))
    return [
        Finding(
            f"growth-{item.product.id}", "growth", item.product.name, item.product.description,
            f"{segment.label} · Attractiveness {item.score:.0f}/100. {item.rationale}",
            item.execution,
            item.sources, pilot_metric(PRODUCT_CLASS[item.product.id]),
            evidence_confidence=item.factors["evidence"],
        )
        for item in ranked[:4]
    ]


def risk_findings(product: Finding) -> list[Finding]:
    return [
        Finding(
            "cross-sell-qualification", "cross-sell", f"Wrong accounts for {product.title}",
            product.evidence,
            "Selling to existing owners or accounts that cannot deploy would overstate the qualified pool and frustrate customers.",
            "Reconcile product ownership and explicit eligibility by customer ID. Keep unknowns in discovery before outreach.",
            product.sources, "Count distinct eligible non-adopters and unresolved accounts separately.",
            "The selected segment is hypothetical. The public catalog has no account-level ownership, eligibility, or buyer intent.",
        ),
        Finding(
            "cross-sell-execution", "cross-sell", f"Deployment friction for {product.title}",
            product.evidence, "Deployment depends on whether the workflow fits the hotel’s existing systems and processes.",
            product.action + " Rehearse the workflow and define a rollback before expanding.",
            product.sources, product.metric,
            "Matching a workflow need does not confirm that a given property has a supported configuration.",
        ),
        Finding(
            "cross-sell-economics", "cross-sell", f"Weak economics for {product.title}",
            product.evidence,
            "Conversion can mask weak retention or an offer whose payment, onboarding, or support costs erase contribution.",
            "Pilot a priced offer. Review actual activation, first renewals, and implementation and support effort before scaling.",
            product.sources, "Measure willingness to pay, realized contribution margin and retained usage.",
            "Price, adoption, retention and cost to serve are unverified for this customer segment.",
        ),
    ]


def investment_findings(product: Finding) -> list[Finding]:
    category = PRODUCT_CLASS.get(product.id.removeprefix("growth-"))
    if category is None:
        return []
    name = product.title
    metric = pilot_metric(category)
    demand = {
        "payments": "Ask hotel Finance teams to compare settlement, reconciliation and fees with their incumbent processor.",
        "distribution": "Ask revenue teams which channels they would connect and what they would pay to reduce manual rate and inventory work.",
        "booking": "Ask hotel commercial teams which booking-flow friction they would pay to remove.",
        "pms": "Ask hotel operations teams which reservation and billing handoffs justify a migration budget.",
        "guest": "Ask hotel operations teams which guest offer and fulfillment workflows merit a paid trial.",
        "revenue": "Ask revenue managers which pricing decisions they would delegate and what controls justify a paid trial.",
        "analytics": "Ask revenue teams which decisions require the data and what they currently pay for comparable coverage.",
    }[category]
    return [
        Finding(
            "investment-qualification", "investment", f"Qualify {name}",
            product.evidence, "Documented functionality leaves buyer demand and eligibility to validate.",
            f"Identify distinct eligible hotels. {demand} Test a priced offer with budget owners.",
            product.sources, "Record price acceptance and reasons for declining.",
        ),
        Finding(
            "investment-rollout", "investment", f"Prove deployment and repeat use of {name}",
            product.evidence, "Product fit depends on how it works with hotel systems and daily workflows.",
            f"Run a time-boxed pilot on supported configurations. Track {metric}, activation time and repeat usage.",
            product.sources, "Record integration effort and operational exceptions before expanding the cohort.",
        ),
        Finding(
            "investment-contribution", "investment", f"Validate incremental contribution from {name}",
            product.evidence, "A successful deployment still needs sustainable economics.",
            "Compare paid usage against the pre-pilot baseline. Reconcile realized incremental revenue, "
            "variable delivery and support costs, and retained usage with Finance before updating the downside case.",
            product.sources, "Measure contribution after incremental costs and track whether paid usage persists.",
        ),
    ]


def tradeoff_findings(catalog: MarketCatalog, company_ids: tuple[str, ...]) -> list[Finding]:
    if not {"oracle", "mews"} <= set(company_ids):
        return []
    ai = catalog.sources.get("oracle-assistant")
    payments = catalog.sources.get("mews-payments")
    if ai is None or payments is None or ai.status != "verified" or payments.status != "verified":
        return []
    return [Finding(
        "tradeoff-payments-ai", "tradeoff", "Embedded payments or front-desk automation",
        "Mews documents embedded payments. Oracle announced OPERA Cloud Assistant with room-assignment and in-workflow assistance.",
        "Payments address collection and reconciliation work. Front-desk automation targets staff effort and exceptions. "
        "These are different jobs with different evidence and rollout requirements.",
        "Compare a payment reconciliation pilot against an assisted room-assignment test with staff overrides. "
        "Qualify regional payment support and current AI availability before selecting properties.",
        (payments, ai), "Track reconciliation exceptions and contribution for payments; track task time and override rates for AI.",
        "Customer demand, adoption, rollout coverage and returns are unverified for both alternatives.",
    )]


def build_public_brief(
    catalog: MarketCatalog, question: str, company_ids: tuple[str, ...], segment: str, theme: str | None,
    context: GrowthContext | None = None,
    focus_product: str | None = None,
) -> PublicBrief:
    companies = tuple(catalog.companies[key].name for key in company_ids)
    findings = (
        market_findings(catalog, company_ids, theme)
        + competitive_findings(catalog, company_ids)
        + growth_findings(catalog, company_ids, segment, context)
    )
    growth = next((item for item in findings if item.id == f"growth-{focus_product}"), None)
    if growth is None and focus_product:
        product = catalog.products.get(focus_product)
        if product and product.company_id in company_ids and catalog.evidence_status(product.source_ids) == "verified":
            growth = Finding(
                f"growth-{product.id}", "growth", product.name, product.description,
                "Explicit product focus for the selected investment decision.", "Validate customer eligibility.",
                tuple(catalog.sources[key] for key in product.source_ids),
            )
    if growth is None:
        growth = next((item for item in findings if item.section == "growth"), None)
    if growth:
        findings.extend(investment_findings(growth))
        findings.extend(risk_findings(growth))
    findings.extend(tradeoff_findings(catalog, company_ids))
    return PublicBrief(question, companies, SEGMENTS[segment].label, catalog.themes.get(theme) if theme else None, tuple(findings), growth)


def matching_snapshot(
    catalog: MarketCatalog, snapshot: object, companies: tuple[str, ...], segment: str
) -> FinancialSnapshot | None:
    if not isinstance(snapshot, FinancialSnapshot):
        return None
    product = catalog.products.get(snapshot.product_id)
    if not product or product.company_id not in companies or not snapshot.scenarios:
        return None
    if snapshot.segment is not None and snapshot.segment != segment:
        return None
    if product.id not in PRODUCT_CLASS or catalog.evidence_status(product.source_ids) != "verified":
        return None
    return snapshot
