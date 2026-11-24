"""Source-linked decision agenda and workspace findings."""

import streamlit as st

from data_services.market_catalog import MarketCatalog
from strategy_models.advisor import (
    FINANCIAL_BRIEF_KEY,
    FinancialSnapshot,
    PublicBrief,
)
from strategy_models.advisor_report import (
    EVIDENCE_LIMITS,
    FINANCIAL_HEADERS,
    financial_rows,
)
from strategy_models.decision_policy import Criteria, Decision, Objective, Qualification
from strategy_models.financial import LIMITATIONS
from strategy_models.growth_engine import ATTRACTIVENESS_QUALIFIER
from ui.components import dashboard_card

WORKSPACE_LINKS = {
    "market": ("app_pages/market_intelligence.py", "Open Market Intelligence"),
    "competition": ("app_pages/competitive_benchmarking.py", "Open Competitive Benchmarking"),
    "growth": ("app_pages/product_growth_intelligence.py", "Open Product Growth Intelligence"),
}


def simulator_handoff() -> None:
    st.markdown(
        "In the Simulator, complete **Conservative, Base and Ambitious** for the same opportunity. "
        "Then choose **Executive brief → Open results in Strategy Advisor**."
    )
    st.page_link(
        "app_pages/financial_scenario_simulator.py", label="Open Financial Scenario Simulator",
        icon=":material/calculate:",
    )


def management_criteria(snapshot: FinancialSnapshot | None, opportunity: str) -> Criteria:
    currency = snapshot.currency if snapshot else "USD"
    # Separate fields by product, customer segment, currency and fictional/ordinary context.
    scope = (
        f"{snapshot.product_id}:{snapshot.segment}:{currency}:{bool(snapshot.fictional_label)}"
        if snapshot else opportunity
    )
    with st.expander("Management decision criteria", expanded=True):
        if snapshot:
            label = snapshot.fictional_label or opportunity
            st.caption(f"Simulator results loaded · {label} · {currency}")
            st.caption(
                "A pilot recommendation needs your applicable financial limits and confirmed customer evidence. "
                "Choose Discovery to review what to verify first."
            )
        else:
            simulator_handoff()
        objective_options: tuple[Objective, ...] = ("Investment screening", "Discovery")
        qualification_options: tuple[Qualification, ...] = (
            "Unknown", "Confirmed for this scope", "Conflicting evidence", "Confirmed blocker",
        )
        objective = st.radio(
            "Strategic objective", objective_options, horizontal=True, key=f"decision_objective_{scope}",
            help="Choose Discovery to identify what to verify next without screening a financial commitment.",
        )
        qualification = st.selectbox(
            "Customer and execution evidence", qualification_options, key=f"decision_evidence_{scope}",
            help="Leave Unknown until you have verified eligible customers, willingness to pay and a supported setup.",
        )
        if objective == "Discovery" or snapshot is None:
            return Criteria(objective=objective, qualification=qualification)
        left, middle, right = st.columns(3)
        investment = left.number_input(
            f"Maximum upfront investment ({currency})", min_value=0.0, value=None, step=10_000.0,
            key=f"decision_cap_{scope}",
            help="The most you would spend upfront on rollout. A pilot needs its own budget.",
        )
        downside = middle.number_input(
            f"Maximum downside exposure ({currency})", min_value=0.0, value=None, step=10_000.0,
            key=f"decision_downside_{scope}",
            help="The largest three-year cash loss you would accept. The Advisor checks the worst case, including saved stress tests.",
        )
        payback = right.number_input(
            "Target Base payback (months)", min_value=0.1, value=None, step=1.0,
            key=f"decision_payback_{scope}",
            help="How soon the Base case should recover upfront investment, measured from rollout.",
        )
    return Criteria(objective, investment, downside, payback, qualification)


def decision_view(decision: Decision) -> None:
    with dashboard_card("advisor-executive-recommendation"):
        st.header("Executive recommendation", anchor=False)
        st.subheader(decision.recommendation, anchor=False)
        st.markdown(f"**{decision.action}**")
        st.markdown(decision.rationale)
        if decision.risks:
            st.markdown(f"**Main risk** · {decision.risks[0]}")
        st.markdown(f"**What could change the recommendation** · {decision.reversal}")


def decision_details(decision: Decision) -> None:
    with dashboard_card("advisor-decision-details"):
        if decision.checks:
            with st.expander("Decision checks", expanded=any(check.result == "Fail" for check in decision.checks)):
                for check in decision.checks:
                    st.markdown(f"- **{check.result} · {check.name}** {check.detail}")
        st.markdown("**Recommended actions**")
        for action in decision.next_actions:
            st.markdown(f"- {action}")
        st.markdown("**Decision gates**")
        for gate in decision.gates:
            st.markdown(f"- {gate}")
    with st.expander("Supporting evidence and alternatives"):
        for heading, entries in (
            ("Supporting evidence", decision.evidence),
            ("Strategic alternatives", decision.alternatives),
            ("Other risks and limitations", decision.risks[1:]),
        ):
            if entries:
                st.markdown(f"**{heading}**")
                for entry in entries:
                    st.markdown(f"- {entry}")
        if decision.sources:
            st.caption(" · ".join(f"[{source.title}](<{source.url}>)" for source in decision.sources))


def executive_agenda(brief: PublicBrief, priorities: tuple[str, ...], method: str) -> None:
    lookup = {item.id: item for item in brief.findings}
    with dashboard_card("advisor-decision-agenda"):
        st.header("Research notes", anchor=False)
        st.caption(method)
        if brief.question == "growth":
            st.info(ATTRACTIVENESS_QUALIFIER)
        for rank, key in enumerate(priorities, start=1):
            finding = lookup[key]
            heading = finding.title if brief.question == "market" else f"{rank}. {finding.title}"
            st.subheader(heading, anchor=False)
            st.caption(f"Segment · {brief.segment}")
            st.markdown(f"**Evidence** · {finding.evidence}")
            if finding.assumption:
                st.markdown(f"**Assumptions and limits** · {finding.assumption}")
            st.markdown(f"**Strategic interpretation** · {finding.interpretation}")
            st.markdown(f"**Validate** · {finding.metric}")
            st.caption(" · ".join(f"[{source.title}](<{source.url}>)" for source in finding.sources))

        if brief.question in WORKSPACE_LINKS:
            path, action = WORKSPACE_LINKS[brief.question]
            st.page_link(path, label=action, icon=":material/arrow_forward:")

def local_financial_view(catalog: MarketCatalog, snapshot: FinancialSnapshot | None) -> None:
    with st.expander("Local financial scenario results", expanded=snapshot is not None):
        if snapshot is None:
            st.caption("No matching results are attached. Keep the company and segment selected when you transfer results.")
            simulator_handoff()
        else:
            st.markdown(f"**{snapshot.fictional_label or catalog.products[snapshot.product_id].name}**")
            st.caption(snapshot.origin)
            if snapshot.segment is None:
                st.caption("The saved financial scenario has an unspecified or mixed segment.")
            for row in financial_rows(snapshot):
                with dashboard_card(f"advisor-finance-{row[0]}"):
                    st.subheader(row[0], anchor=False)
                    for label, value in zip(FINANCIAL_HEADERS[1:], row[1:], strict=True):
                        st.markdown(f"**{label}** · {value}")
            st.caption(LIMITATIONS)
            if st.button("Remove financial results from advisor", key="advisor_remove_finance"):
                st.session_state.pop(FINANCIAL_BRIEF_KEY, None)
                st.rerun()
        if snapshot is not None:
            st.page_link(
                "app_pages/financial_scenario_simulator.py", label="Open Financial Scenario Simulator",
                icon=":material/calculate:",
            )


def evidence_limitations() -> None:
    with st.expander("Methodology and evidence limitations"):
        st.markdown(EVIDENCE_LIMITS)
        st.caption(
            "The market theme filters announcements. Competitive and product findings use their "
            "workspace methodology and the selected companies or hypothetical segment. Financial "
            "figures come only from the saved Financial Scenario Simulator output."
        )
