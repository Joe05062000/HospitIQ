"""Local decision policy over reviewed findings and existing simulator outputs."""

from dataclasses import dataclass
from math import isfinite
from typing import Literal

from data_services.market_catalog import Source
from strategy_models.advisor import FinancialSnapshot, Finding, PublicBrief
from strategy_models.financial import SCENARIOS, Projection
from strategy_models.financial_report import money

GateResult = Literal["Pass", "Fail", "Pending", "Not applicable"]
Recommendation = Literal[
    "Prioritize", "Investigate further", "Conduct a controlled pilot",
    "Redesign the opportunity", "Defer investment", "Insufficient evidence to recommend a commitment",
]
Qualification = Literal["Unknown", "Confirmed for this scope", "Conflicting evidence", "Confirmed blocker"]
Objective = Literal["Discovery", "Investment screening"]


@dataclass(frozen=True)
class Criteria:
    objective: Objective = "Investment screening"
    investment_cap: float | None = None
    downside_cap: float | None = None
    payback_months: float | None = None
    qualification: Qualification = "Unknown"


@dataclass(frozen=True)
class Check:
    name: str
    result: GateResult
    detail: str


@dataclass(frozen=True)
class Decision:
    recommendation: Recommendation
    action: str
    rationale: str
    evidence: tuple[str, ...]
    sources: tuple[Source, ...]
    alternatives: tuple[str, ...]
    risks: tuple[str, ...]
    next_actions: tuple[str, ...]
    gates: tuple[str, ...]
    reversal: str
    checks: tuple[Check, ...] = ()


INSUFFICIENT: Recommendation = "Insufficient evidence to recommend a commitment"
DISCOVERY: dict[str, tuple[str, str, str]] = {
    "competition": (
        "Ask target buyers which documented workflow difference matters to them.",
        "Product documentation shows where workflows differ. Buyer preference and vendor performance still need testing.",
        "Confirm that the same buyer values the proposed difference and can verify it on the intended configuration.",
    ),
    "market": (
        "Check which reported changes affect a workflow on your product roadmap.",
        "These announcements match your selections. They are listed alphabetically because the available evidence does not establish their relative impact.",
        "Escalate a signal only after confirming availability and a concrete impact on a target segment or workflow.",
    ),
    "tradeoff": (
        "Compare payments and front-desk automation against the same business goal.",
        "Payments affect collection and reconciliation. Front-desk automation affects staff time and exceptions. Agree which outcome matters before choosing a test.",
        "Agree a comparable baseline, supported configuration, and measures of cost, adoption and benefit for both options.",
    ),
    "cross-sell": (
        "Qualify the customer pool before starting cross-sell outreach.",
        "Accounts that already own the product or cannot deploy it overstate the potential customer pool.",
        "Confirm unique eligible non-adopters, buyer need, and a supported workflow before outreach or a priced test.",
    ),
}


def relevant_evidence(brief: PublicBrief, items: tuple[Finding, ...]) -> tuple[tuple[str, ...], tuple[Source, ...]]:
    lead: Finding | None
    if brief.question == "growth" and items:
        lead = items[0]
    else:
        lead = brief.opportunity if brief.question in {"investment", "cross-sell"} else None
    selected = (lead,) if lead and lead.sources else items
    evidence = [f"{item.title} · {item.evidence}" for item in selected]
    sources = {source.id: source for item in selected for source in item.sources}
    if lead and lead.evidence_confidence is not None:
        evidence.append(
            f"Growth evidence coverage is {lead.evidence_confidence}/4. This counts documented product, "
            "ownership, eligibility and integration signals. It is separate from attractiveness."
        )
    if brief.question == "investment":
        # Market and competitive context only where a source already overlaps the focused opportunity.
        for section in ("market", "competition"):
            match = next((
                item for item in brief.findings if item.section == section
                and any(source.id in sources for source in item.sources)
            ), None)
            if match:
                evidence.append(f"{match.title} · {match.interpretation}")
                sources.update((source.id, source) for source in match.sources)
    return tuple(evidence), tuple(sources.values())


def discovery_decision(brief: PublicBrief, items: tuple[Finding, ...]) -> Decision:
    evidence, sources = relevant_evidence(brief, items)
    if brief.question == "growth":
        lead = items[0]
        return Decision(
            "Prioritize", f"Validate {lead.title} first as a discovery opportunity.",
            lead.interpretation + " This score guides what to test first.",
            evidence, sources,
            tuple(
                f"{item.title} · {item.interpretation.split('. ', 1)[0]}."
                for item in brief.findings if item.section == "growth" and item.id != lead.id
            ),
            ("A good workflow fit can still yield few eligible buyers or an expensive deployment.",),
            (lead.action,),
            ("Confirm buyer demand, identify eligible non-adopters and verify the setup before proposing a pilot.",),
            "A change in segment, weights or verified product fit could change the discovery order.",
        )
    if brief.question == "investment":
        action, reason, gate = (
            "Qualify the opportunity before evaluating a financial commitment.",
            "Management selected discovery. The priority is confirming the buyer, the eligible cohort and workflow fit.",
            "Record who would pay and confirm that the cohort can deploy before bringing a budget request.",
        )
    else:
        action, reason, gate = DISCOVERY[brief.question]
    alternatives = {
        "competition": tuple(
            f"{item.title} · {item.interpretation}" for item in items
        ),
        "tradeoff": (
            "Payments · measure reconciliation exceptions and incremental contribution.",
            "Front-desk automation · measure task time and staff overrides.",
        ),
    }.get(brief.question, ())
    risks = tuple(dict.fromkeys(item.assumption for item in items if item.assumption))
    return Decision(
        "Investigate further", action, reason, evidence, sources, alternatives,
        risks or ("Availability, demand and implementation effort still need checking for the selected companies and segment.",),
        tuple(dict.fromkeys(item.action for item in items)), (gate,),
        "New evidence on buyer demand, rollout availability, or performance against the agreed baseline could change the next step.",
    )


def financial_checks(
    snapshot: FinancialSnapshot, scenarios: dict[str, Projection], criteria: Criteria,
) -> tuple[tuple[Check, ...], tuple[str, ...], tuple[str, ...]]:
    currency = snapshot.currency
    base = scenarios["Base"]
    worst_name, worst = min(scenarios.items(), key=lambda case: case[1].ending_cash)
    capex_name, capex = max(scenarios.items(), key=lambda case: case[1].assumptions.investment)
    cash_floor, floor_label = worst.ending_cash, f"{worst_name} three-year cash"
    risks = [
        f"Worst modeled scenario cash is {money(cash_floor, currency)} in {worst_name}.",
        "The scenarios are assumption-based three-year cash projections, with no probabilities assigned.",
    ]
    if snapshot.normalized_sensitivity:
        impact = max(item.absolute_impact for item in snapshot.normalized_sensitivity)
        drivers = ", ".join(
            item.driver for item in snapshot.normalized_sensitivity if round(item.absolute_impact, 2) == round(impact, 2)
        )
        risks.append(f"Largest equal-shock exposure in {snapshot.sensitivity_case} · {drivers} ({money(impact, currency)}).")
    if snapshot.business_sensitivity and snapshot.sensitivity_case in scenarios:
        item = min(snapshot.business_sensitivity, key=lambda case: min(case.low, case.high))
        stress = min(item.low, item.high)
        risks.append(
            f"Lowest saved one-driver business stress · {snapshot.sensitivity_case}, {item.driver}, "
            f"{money(stress, currency)} three-year cash. The bounds are assumptions and are not combined."
        )
        if stress < cash_floor:
            cash_floor, floor_label = stress, f"{snapshot.sensitivity_case} {item.driver} stress"
    else:
        risks.append("No matching business uncertainty ranges were saved. The downside gate uses scenario cash only.")
    exposure = max(0.0, -cash_floor)

    def cap_check(name: str, actual: float, limit: float | None, detail: str) -> Check:
        if limit is None or not isfinite(limit) or limit < 0:
            return Check(name, "Pending", f"{detail}. Enter a valid management limit.")
        result: GateResult = "Pass" if actual <= limit else "Fail"
        return Check(name, result, f"{detail} against a limit of {money(limit, currency)}.")

    funding = cap_check(
        "Investment cap", capex.assumptions.investment, criteria.investment_cap,
        f"Highest modeled upfront investment is {money(capex.assumptions.investment, currency)} in {capex_name}",
    )
    downside = cap_check(
        "Downside tolerance", exposure, criteria.downside_cap,
        f"Downside exposure is {money(exposure, currency)} from {floor_label}",
    )
    if base.assumptions.investment == 0:
        payback = Check("Base payback", "Not applicable", "The Base case has no upfront investment.")
    else:
        months = base.payback_months
        target = criteria.payback_months
        observed = (
            f"Base recovers in approximately {months:.1f} months from rollout" if months is not None
            else "Base does not recover the investment within the modeled horizon"
        )
        if target is None or not isfinite(target) or target <= 0:
            payback = Check("Base payback", "Pending", f"{observed}. Enter a management payback target.")
        else:
            payback = Check(
                "Base payback", "Pass" if months is not None and months <= target else "Fail",
                f"{observed} against a {target:g}-month target from rollout.",
            )
    economics = Check(
        "Base cash", "Pass" if base.ending_cash > 0 else "Fail",
        f"Base three-year cash is {money(base.ending_cash, currency)}. Pilot screening requires positive Base cash.",
    )
    figures = tuple(
        f"{name} · {money(scenarios[name].ending_cash, currency)} three-year net cash and "
        f"{money(scenarios[name].assumptions.investment, currency)} upfront investment."
        for name in SCENARIOS
    )
    return (economics, funding, downside, payback), figures, tuple(risks)


def evaluate_decision(
    brief: PublicBrief, snapshot: FinancialSnapshot | None = None, criteria: Criteria = Criteria(),
) -> Decision:
    items = tuple(
        item for item in brief.findings if item.section == brief.focus_section()
        and item.sources and all(source.status == "verified" for source in item.sources)
    )
    if not items or criteria.qualification == "Conflicting evidence":
        return Decision(
            INSUFFICIENT, "Resolve the evidence gap before committing resources.",
            "The selected scope lacks supporting evidence or the qualification evidence conflicts.",
            (), (), (), ("A commitment would rely on unresolved eligibility or evidence.",),
            ("Review the original sources and reconcile disputed eligibility, demand or implementation evidence.",),
            ("Confirm the decision scope and document reliable supporting evidence.",),
            "A verified source or reconciled qualification evidence would allow a new assessment.",
        )
    if brief.question != "investment" or criteria.objective == "Discovery":
        return discovery_decision(brief, items)

    evidence, sources = relevant_evidence(brief, items)
    qualification_action = items[0].action
    alternatives = (
        "Use a discovery-only test to resolve buyer and workflow uncertainty before taking on rollout costs.",
        "Model a narrower rollout or revised offer using the same currency, horizon and cohort assumptions.",
    )
    gates: tuple[str, ...] = (
        "Confirm eligible non-adopters, paid demand and implementation feasibility for the modeled scope.",
        "Before pilot spend, agree a separate spending cap, success measures, owners and stop conditions.",
        "Before scaling, update the scenarios with observed activation, retention, contribution and delivery costs.",
    )
    if criteria.qualification == "Confirmed blocker":
        return Decision(
            "Defer investment", "Pause the current proposal until the confirmed blocker is removed.",
            "Management recorded a qualification blocker for this opportunity.", evidence, sources, alternatives,
            ("The current cohort, buyer demand or implementation cannot support the proposal.",),
            ("Identify who owns the blocker and what evidence would show that it has been resolved.",),
            ("Keep funding on hold until the blocker is cleared and the scenarios have been reviewed again.",),
            "Evidence that the blocker has been removed would reopen the decision.",
        )

    if snapshot and (not brief.opportunity or brief.opportunity.id != f"growth-{snapshot.product_id}"):
        snapshot = None
    scenarios = dict(snapshot.scenarios) if snapshot else {}
    if not snapshot or len(snapshot.scenarios) != len(SCENARIOS) or set(scenarios) != set(SCENARIOS):
        absent = ", ".join(name for name in SCENARIOS if name not in scenarios) or "a unique result for each named case"
        return Decision(
            INSUFFICIENT, "Complete and share the matching financial cases before considering investment.",
            f"Missing scenario results · {absent}.", evidence, sources, alternatives,
            ("Without all three cases, management cannot assess the cash downside or recovery time.",),
            ("In the Simulator, use Executive brief → Open results in Strategy Advisor for the selected opportunity.",),
            ("Complete all three cases and supply management limits and customer qualification evidence.",),
            "A complete set of matching scenarios and management limits would let the Advisor screen the proposal.",
        )

    checks, figures, risks = financial_checks(snapshot, scenarios, criteria)
    qualification = Check(
        "Customer and execution evidence",
        "Pass" if criteria.qualification == "Confirmed for this scope" else "Pending",
        "Management confirmed eligible customers, priced demand and supported implementation for the modeled scope."
        if criteria.qualification == "Confirmed for this scope"
        else "Confirm eligibility, priced demand and supported implementation for the modeled scope.",
    )
    checks += (qualification,)
    failed = tuple(check.name for check in checks if check.result == "Fail")
    pending = tuple(check.name for check in checks if check.result == "Pending")
    next_actions: tuple[str, ...]
    if all(result.ending_cash < 0 for result in scenarios.values()):
        recommendation: Recommendation = "Defer investment"
        action = "Pause the current rollout proposal and test a materially different case."
        reason = "Conservative, Base and Ambitious all end with negative three-year cash under the supplied assumptions."
        next_actions = ("Identify whether a smaller rollout, lower costs or better unit economics could justify a new case.",)
        gates = ("Revisit investment only after a revised case clears management’s financial limits.",)
    elif failed:
        recommendation = "Redesign the opportunity"
        action = "Revise the rollout or commercial terms before planning a pilot."
        reason = "The proposal misses the following limits or requirements · " + ", ".join(failed) + "."
        next_actions = tuple(
            guidance for gate, guidance in (
                ("Base cash", "Test a smaller rollout or a revised offer that improves Base cash."),
                ("Investment cap", "Identify which upfront costs can be removed, deferred or reduced."),
                ("Downside tolerance", "Test whether a staged rollout or tighter cost limits reduce the potential cash loss."),
                ("Base payback", "Test a lower upfront cost or changes to price, margin or adoption that could shorten recovery."),
            ) if gate in failed
        )
        gates = ("Rerun all three cases and clear the failed checks before planning a pilot.",)
    elif any(name != qualification.name for name in pending):
        recommendation = INSUFFICIENT
        action = "Set the missing management limits before deciding whether to fund a pilot."
        reason = "Management still needs to settle these items · " + ", ".join(pending) + "."
        next_actions = ("Enter management’s investment cap, downside limit and Base payback target where applicable.",)
        gates = ("Check the scenarios against those limits and confirm customer and implementation evidence before pilot spend.",)
    elif pending:
        recommendation = "Investigate further"
        action = "Validate the cohort, paid demand and delivery feasibility before pilot spend."
        reason = "The model meets the stated limits. The proposed customers and implementation still need validation."
        next_actions = (qualification_action, "Confirm the required integrations and get an implementation estimate.")
        gates = ("Confirm eligible non-adopters, willingness to pay and a supported setup before planning a pilot.",)
    else:
        recommendation = "Conduct a controlled pilot"
        action = "Consider a time-boxed pilot under a separately approved cap."
        reason = "The model meets management’s limits, and management has confirmed customer and implementation evidence."
        next_actions = tuple(item.action for item in items[1:])
        gates = gates[1:]
    review = ", ".join(failed + pending)
    if review:
        reversal = f"Reassess when there is new evidence or a revised model for these items · {review}."
    else:
        reversal = "Reassess if pilot evidence lowers expected adoption, retention or contribution, or raises delivery cost."
    if snapshot.fictional_label:
        reason += " This is a fictional case with illustrative financial inputs."
    return Decision(
        recommendation, action, reason, evidence + figures, sources, alternatives, risks,
        next_actions, gates, reversal, checks,
    )
