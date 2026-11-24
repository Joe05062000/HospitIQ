"""Build a focused 90-day plan from current segment and product priorities."""

from dataclasses import dataclass
from html import escape

from brand import PRODUCT_DESCRIPTOR, PRODUCT_NAME
from strategy_models.growth_engine import ATTRACTIVENESS_QUALIFIER, Priority
from strategy_models.growth_research import CATEGORY_LABELS, PRODUCT_CLASS, SEGMENTS


@dataclass(frozen=True)
class Milestone:
    window: str
    title: str
    activities: tuple[str, ...]
    decision: str


def segment_label(key: str | None) -> str:
    return SEGMENTS[key].label if key else "Unclassified segment"


def playbook_steps(priorities: list[Priority]) -> tuple[Milestone, ...]:
    if not priorities:
        return ()
    lead = priorities[0]
    focus = f"{lead.product.name} for {segment_label(lead.segment)}"
    return (
        Milestone("Days 1–30", "Validate the problem", (
            f"Start discovery with {focus}. Interview an operations lead, a buyer and a technical owner.",
            "Check current ownership, local eligibility and the workflow baseline before outreach.",
            f"Confirm the use case. {lead.benefit} {lead.execution}",
        ), "Proceed only if the buyer confirms the problem and the team can test a supported workflow."),
        Milestone("Days 31–60", "Run a bounded pilot", (
            "Select a small opt-in cohort with confirmed ownership and eligibility. Keep discovery-only cases out of pilot outreach.",
            "Agree the offer, onboarding effort, baseline, measurement window and stop conditions with each pilot sponsor.",
            f"Measure {pilot_metric(PRODUCT_CLASS[lead.product.id])}, time to activation, support incidents and qualitative feedback.",
        ), "Continue if the workflow is usable and operational, privacy and support risks are acceptable."),
        Milestone("Days 61–90", "Decide whether to expand", (
            "Review pilot evidence against the agreed baseline and record confounding factors.",
            "Validate buyer willingness to pay, implementation capacity and the support model.",
            "Document the segment, qualification checklist, pilot learnings and handoff owner.",
        ), "Choose to expand, revise the offer, or stop. Record the evidence required to revisit the decision."),
    )


def pilot_metric(category: str) -> str:
    return {
        "pms": "manual handoffs per reservation",
        "distribution": "rate and inventory synchronization exceptions",
        "booking": "booking-flow completion and abandonment",
        "payments": "payment and reconciliation exceptions",
        "guest": "offer take-up and successful fulfillment",
        "revenue": "time from reviewed recommendation to approved rate update",
        "analytics": "report preparation time and data-quality exceptions",
    }[category]


def playbook_html(company: str, priorities: list[Priority], mode: str) -> str:
    focus = []
    for item in priorities[:3]:
        category = CATEGORY_LABELS[PRODUCT_CLASS[item.product.id]]
        sources = " · ".join(
            f'<a href="{escape(source.url, quote=True)}">{escape(source.title)}</a>'
            for source in item.sources
        )
        focus.append(
            f"<li><strong>{escape(item.product.name)}</strong> · {escape(segment_label(item.segment))}"
            f" · {escape(category)} · Attractiveness {item.score:.0f}/100."
            f"<br>{escape(item.benefit)}<br><strong>Execution</strong> {escape(item.execution)}"
            f"<br><strong>Evidence</strong> {sources}</li>"
        )
    milestones = "".join(
        f"<section><h2>{escape(step.window)} · {escape(step.title)}</h2><ul>"
        + "".join(f"<li>{escape(activity)}</li>" for activity in step.activities)
        + f"</ul><p><strong>Decision checkpoint</strong> {escape(step.decision)}</p></section>"
        for step in playbook_steps(priorities)
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>90-day commercial growth playbook · {escape(PRODUCT_NAME)}</title>
<style>
body {{ max-width: 54rem; margin: 2rem auto; padding: 0 1rem; color: #17324d;
font: 16px/1.55 system-ui, sans-serif; }} section {{ border: 1px solid #dce7ef;
border-radius: .65rem; padding: 0 1rem; margin: 1rem 0; }} li {{ margin: .45rem 0; }}
a {{ color: #176f9b; overflow-wrap: anywhere; }}
</style></head><body>
<main><p><strong>{escape(PRODUCT_NAME)}</strong> · {escape(PRODUCT_DESCRIPTOR)}</p><h1>90-day commercial growth playbook</h1><p>{escape(company)} · {escape(mode)}</p>
<p>Research priorities are hypotheses. Confirm eligibility, ownership, technical fit and buyer
interest before contacting a customer. No customer identifiers or uploaded fields are included.</p>
<h2>Priority segments and products</h2><p>{escape(ATTRACTIVENESS_QUALIFIER)}</p><ol>{"".join(focus)}</ol>
{milestones}<h2>Key risks</h2>
<p>Unconfirmed ownership or eligibility, unsupported configurations, onboarding effort,
and pilot results that may depend on the selected properties or measurement period.</p>
</main></body></html>"""
