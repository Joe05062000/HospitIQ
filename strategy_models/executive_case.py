"""Fictional payments case built from the public catalog and financial engine."""

from dataclasses import dataclass

from data_services.market_catalog import Development, MarketCatalog
from strategy_models.benchmark import Evidence, build_benchmark, eligible_companies
from strategy_models.financial import (
    Assumptions,
    Projection,
    Sensitivity,
    aligned_launch,
    business_uncertainty,
    compare_scenarios,
    sensitivity,
)
from strategy_models.financial_transfer import Opportunity
from strategy_models.growth_research import Complement, complement

COMPANY = "Harborlight Hotel Systems"
PRODUCT = "Harborlight Payments (fictional)"
CUSTOMER_BASE = 5_000
POPULATION = 2_000
CURRENCY = "USD"
STRESS = 0.10
BUSINESS_RANGES = {
    "Adoption rates": (-0.35, 0.25), "Revenue per adopter": (-0.20, 0.10),
    "Contribution margin": (-0.25, 0.15), "Retention": (-0.15, 0.05),
    "Fixed operating costs": (-0.10, 0.35), "One-time investment": (-0.10, 0.25),
}
CONSERVATIVE_TIMING = (
    "Conservative assumes no Year 1 pre-launch spending. The one-time USD 1,000,000 investment "
    "and fixed operating costs begin in Year 2 at launch. Validate that assumption before budgeting."
)
RISK_CONTEXT = (
    "The ranges are fictional planning assumptions. Practical risk depends on uncertainty and "
    "controllability, as well as modeled cash impact."
)
CASE_LIMIT = "Planning model · Mid-year activation and undiscounted cash. Excludes taxes, working capital and financing."
QUESTION = "Should a hospitality software vendor pilot embedded payments with existing hotel customers?"
ORIGIN = "Fictional Harborlight case assumptions. Vendor sources provide industry context only."
ASSUMPTIONS = {
    "Conservative": Assumptions(POPULATION, (0.12, 0.14, 0.15), 2_500, 0.50, 420_000, 1_000_000, 2, 0.85, "Mid-year"),
    "Base": Assumptions(POPULATION, (0.20, 0.22, 0.24), 3_000, 0.60, 400_000, 900_000, 1, 0.90, "Mid-year"),
    "Ambitious": Assumptions(POPULATION, (0.26, 0.28, 0.30), 3_250, 0.65, 450_000, 1_000_000, 1, 0.94, "Mid-year"),
}
RECOMMENDATION = (
    "Approve a bounded pilot with a spending cap set by Finance. Test willingness to pay, realized margin and "
    "cost to serve alongside adoption, retention and implementation feasibility. Re-run the downside case before scaling."
)
RISKS = (
    "Incomplete ownership or eligibility records can overstate the addressable base.",
    "Payments pricing, merchant eligibility, dispute handling, and settlement vary by market.",
    "Integration and reconciliation workload could reduce the modeled contribution margin.",
    "Slow rollout, low activation, or early churn can delay or eliminate cash recovery.",
)
MILESTONES = (
    (
        "Days 1–30 · Qualify",
        ("Reconcile eligible non-adopters by customer ID. Interview hotel Finance and Operations, "
        "confirm settlement and integration requirements, and validate pricing and delivery costs."),
        "Advance only when eligibility, operating ownership, and the pilot budget are documented.",
    ),
    (
        "Days 31–60 · Pilot",
        ("Recruit a small opt-in cohort. Track onboarding completion, active usage, incremental net revenue, "
        "reconciliation exceptions, support effort, and early retention signals."),
        "Pause if merchant onboarding, settlement accuracy, or support capacity misses agreed tolerances.",
    ),
    (
        "Days 61–90 · Decide",
        ("Re-run the three scenarios using pilot evidence. Compare cash recovery with the approved risk "
        "tolerance and document what would change the rollout decision."),
        "Expand in stages only if contribution and retention support a credible cash recovery path.",
    ),
)
MARKET_IDS = {"mews-finance", "mews-winter", "oracle-assistant"}


@dataclass(frozen=True)
class ExecutiveCase:
    developments: tuple[Development, ...]
    payments_evidence: tuple[tuple[str, tuple[Evidence, ...]], ...]
    complementarity: Complement | None
    results: dict[str, Projection]
    sensitivities: tuple[Sensitivity, ...]
    uncertainty: tuple[Sensitivity, ...]
    aligned: dict[str, Projection]


def build_case(catalog: MarketCatalog) -> ExecutiveCase:
    developments = tuple(
        item for item in catalog.filter_developments(verified_only=True) if item.id in MARKET_IDS
    )
    companies = tuple(key for key in ("oracle", "mews") if key in eligible_companies(catalog))
    evidence: tuple[tuple[str, tuple[Evidence, ...]], ...] = ()
    if len(companies) == 2:
        benchmark = build_benchmark(catalog, companies)
        evidence = tuple(
            (catalog.companies[key].name, benchmark.matrix["payments"][key].evidence) for key in companies
        )
    results = compare_scenarios(ASSUMPTIONS)
    return ExecutiveCase(
        developments, evidence, complement("pms", "payments"), results,
        sensitivity(ASSUMPTIONS["Base"], STRESS), business_uncertainty(ASSUMPTIONS["Base"], BUSINESS_RANGES),
        aligned_launch(ASSUMPTIONS, 1),
    )


def sensitivity_takeaways(case: ExecutiveCase) -> tuple[str, str]:
    maximum = round(case.sensitivities[0].absolute_impact, 2)
    leaders = " and ".join(
        item.driver.lower() for item in case.sensitivities if round(item.absolute_impact, 2) == maximum
    )
    exposure = case.uncertainty[0].driver.lower()
    return (
        f"The largest tested cash impact comes from {leaders}. Each input moves by the same relative percentage.",
        f"{exposure.capitalize()} is the largest modeled exposure under the case’s assumed ranges.",
    )


def case_opportunity(catalog: MarketCatalog) -> Opportunity | None:
    product = catalog.products.get("mews-pay")
    if product is None or catalog.evidence_status(product.source_ids) != "verified":
        return None
    return Opportunity(
        "mews-pay", "payments", "independent", tuple(product.source_ids),
        eligibility_status="Eligible population is a fictional case assumption",
        fictional_label=PRODUCT,
    )
