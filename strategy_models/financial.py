"""Three-year cohort-based investment model for explicitly assumed inputs."""

from collections.abc import Mapping
from dataclasses import dataclass, replace
from math import isfinite
from typing import Literal

SCENARIOS = ("Conservative", "Base", "Ambitious")
METHODOLOGY = (
    "The starting population is unique eligible non-adopters. At each active year's start, "
    "existing modeled adopters are retained at the annual retention rate, and the adoption rate "
    "is applied to the remaining never-adopted population. Churned adopters do not re-enter the pool. "
    "Retained customers generate a full year of revenue. New adopters generate a full or half year according to the activation convention. "
    "Retention is applied at each year boundary, including after a partial first year. Fractional customer counts are expected values."
)
FORMULAS = (
    "Variable costs = incremental revenue × (1 − contribution margin). Contribution profit = "
    "revenue − variable costs. Estimated operating contribution = contribution profit − recurring "
    "fixed operating costs. Net cash contribution = operating contribution − one-time investment. "
    "The investment is paid at the start of the rollout year. Fixed costs begin in that year. "
    "Simple payback is the first recovery of the investment, interpolated assuming operating "
    "cash accrues evenly within each half-year. Under mid-year activation, cash from new adopters begins in the second half; fixed costs and retained revenue accrue throughout the operating year. Payback is shown in months after rollout."
)
LIMITATIONS = (
    "The model uses annual cohorts and undiscounted cash contribution. Taxes, working capital, "
    "financing, depreciation, accounting adjustments, and effects outside the three-year horizon "
    "are outside its scope. Operating contribution is an estimate. Scenario outputs are illustrative "
    "and do not represent company forecasts or EBITDA."
)


class AssumptionError(ValueError):
    """A scenario cannot be calculated with the provided assumptions."""


@dataclass(frozen=True)
class Assumptions:
    eligible: int
    adoption: tuple[float, float, float]
    revenue_per_adopter: float
    margin: float
    fixed_cost: float
    investment: float
    rollout_year: int
    retention: float
    activation: Literal["Beginning of year", "Mid-year"] = "Beginning of year"

    @property
    def active_adoption(self) -> tuple[float | None, ...]:
        return tuple(rate if year >= self.rollout_year else None for year, rate in enumerate(self.adoption, 1))

    def validate(self) -> None:
        if type(self.eligible) is not int or self.eligible < 0:
            raise AssumptionError("Enter a nonnegative whole number of eligible non-adopters.")
        if type(self.rollout_year) is not int or self.rollout_year not in (1, 2, 3):
            raise AssumptionError("Select rollout year 1, 2, or 3.")
        if self.activation not in {"Beginning of year", "Mid-year"}:
            raise AssumptionError("Choose a supported customer activation convention.")
        if len(self.adoption) != 3 or any(
            not isfinite(rate) or not 0 <= rate <= 1 for rate in (*self.adoption, self.margin, self.retention)
        ):
            raise AssumptionError("Adoption rates, contribution margin, and retention must be between 0% and 100%.")
        if any(not isfinite(value) or value < 0 for value in (
            self.revenue_per_adopter, self.fixed_cost, self.investment
        )):
            raise AssumptionError("Revenue and cost inputs must be finite, nonnegative amounts.")


@dataclass(frozen=True)
class YearResult:
    year: int
    new_adopters: float
    retained_adopters: float
    churned_adopters: float
    active_adopters: float
    remaining: float
    revenue: float
    variable_cost: float
    contribution_profit: float
    fixed_cost: float
    investment: float
    operating_contribution: float
    cash_contribution: float
    cumulative_cash: float


@dataclass(frozen=True)
class Projection:
    assumptions: Assumptions
    years: tuple[YearResult, ...]
    payback_months: float | None

    @property
    def total_revenue(self) -> float:
        return sum(year.revenue for year in self.years)

    @property
    def total_operating(self) -> float:
        return sum(year.operating_contribution for year in self.years)

    @property
    def ending_cash(self) -> float:
        return self.years[-1].cumulative_cash


def simulate(assumptions: Assumptions) -> Projection:
    assumptions.validate()
    remaining = float(assumptions.eligible)
    active = cumulative = 0.0
    payback = None
    rows: list[YearResult] = []
    for year, rate in enumerate(assumptions.adoption, start=1):
        launched = year >= assumptions.rollout_year
        retained = active * assumptions.retention if launched else 0.0
        churned = active - retained
        adopters = remaining * rate if launched else 0.0
        remaining = max(0.0, remaining - adopters)
        active = retained + adopters

        midyear = assumptions.activation == "Mid-year"
        revenue = (retained + adopters * (0.5 if midyear else 1)) * assumptions.revenue_per_adopter
        profit = revenue * assumptions.margin
        variable = revenue - profit
        fixed = assumptions.fixed_cost if launched else 0.0
        investment = assumptions.investment if year == assumptions.rollout_year else 0.0
        operating = profit - fixed
        opening_after_investment = cumulative - investment
        cash = operating - investment
        cumulative = opening_after_investment + operating
        if assumptions.investment > 0 and payback is None and launched:
            early = (retained * assumptions.revenue_per_adopter * assumptions.margin - fixed) / 2
            if not midyear:
                early = operating / 2
            balance = opening_after_investment
            for half, flow in enumerate((early, operating - early)):
                if balance < 0 <= balance + flow and flow > 0:
                    payback = 12 * (year - assumptions.rollout_year) + 6 * (half - balance / flow)
                    break
                balance += flow

        rows.append(YearResult(
            year, adopters, retained, churned, active, remaining, revenue, variable, profit,
            fixed, investment, operating, cash, cumulative,
        ))
    return Projection(assumptions, tuple(rows), payback)


def compare_scenarios(assumptions: Mapping[str, Assumptions]) -> dict[str, Projection]:
    if assumptions.keys() != set(SCENARIOS):
        raise AssumptionError("Provide Conservative, Base, and Ambitious assumptions.")
    if len({assumption.eligible for assumption in assumptions.values()}) != 1:
        raise AssumptionError("Use a shared eligible population for comparison scenarios.")
    return {name: simulate(assumptions[name]) for name in SCENARIOS}


@dataclass(frozen=True)
class Sensitivity:
    driver: str
    low: float
    high: float
    low_change: float
    high_change: float

    @property
    def swing(self) -> float:
        return abs(self.high_change - self.low_change)

    @property
    def absolute_impact(self) -> float:
        return max(abs(self.low_change), abs(self.high_change))


DRIVERS = {
    "Adoption rates": "adoption",
    "Revenue per adopter": "revenue_per_adopter",
    "Contribution margin": "margin",
    "Retention": "retention",
    "Fixed operating costs": "fixed_cost",
    "One-time investment": "investment",
}


def sensitivity(assumptions: Assumptions, step: float) -> tuple[Sensitivity, ...]:
    if not isfinite(step) or not 0 < step <= 1:
        raise AssumptionError("Sensitivity step must be greater than zero and at most 100%.")
    return business_uncertainty(assumptions, dict.fromkeys(DRIVERS, (-step, step)))


def business_uncertainty(
    assumptions: Assumptions, ranges: Mapping[str, tuple[float, float]],
) -> tuple[Sensitivity, ...]:
    """Vary one driver at a time using explicitly assumed relative endpoints."""
    baseline = simulate(assumptions).ending_cash
    results = []
    for label, (lower, upper) in ranges.items():
        if label not in DRIVERS or not all(isfinite(value) for value in (lower, upper)) or not -1 <= lower <= 0 <= upper:
            raise AssumptionError("Provide valid lower and upper relative bounds for each driver.")
        field = DRIVERS[label]
        cases = []
        for change in (lower, upper):
            factor = 1 + change
            if field == "adoption":
                y1, y2, y3 = assumptions.adoption
                trial = replace(assumptions, adoption=(min(1, y1 * factor), min(1, y2 * factor), min(1, y3 * factor)))
            elif field == "margin":
                trial = replace(assumptions, margin=min(1, assumptions.margin * factor))
            elif field == "retention":
                trial = replace(assumptions, retention=min(1, assumptions.retention * factor))
            else:
                trial = replace(assumptions, **{field: getattr(assumptions, field) * factor})
            cases.append(simulate(trial).ending_cash)
        low, high = cases
        results.append(Sensitivity(label, low, high, low - baseline, high - baseline))
    return tuple(sorted(results, key=lambda item: (-round(item.absolute_impact, 2), item.driver)))


def aligned_launch(assumptions: Mapping[str, Assumptions], year: int) -> dict[str, Projection]:
    return compare_scenarios({name: replace(value, rollout_year=year) for name, value in assumptions.items()})


def payback_label(projection: Projection) -> str:
    if projection.assumptions.investment == 0:
        return "No upfront investment"
    if projection.payback_months is None:
        return "Not reached within 3 years"
    return f"Approx. {projection.payback_months:.0f} months"
