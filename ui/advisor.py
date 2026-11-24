"""Source-linked decision agenda and workspace findings."""

import streamlit as st

from data_services.market_catalog import MarketCatalog
from strategy_models.advisor import (
    FINANCIAL_BRIEF_KEY,
    SECTION_NAMES,
    FinancialSnapshot,
    PublicBrief,
)
from strategy_models.advisor_report import (
    EVIDENCE_LIMITS,
    FINANCIAL_HEADERS,
    financial_rows,
)
from strategy_models.financial import LIMITATIONS
from strategy_models.growth_engine import ATTRACTIVENESS_QUALIFIER
from ui.components import dashboard_card

WORKSPACE_LINKS = {
    "market": ("app_pages/market_intelligence.py", "Open Market Intelligence"),
    "competition": ("app_pages/competitive_benchmarking.py", "Open Competitive Benchmarking"),
    "growth": ("app_pages/product_growth_intelligence.py", "Open Product Growth Intelligence"),
}


def executive_agenda(brief: PublicBrief, priorities: tuple[str, ...], method: str) -> None:
    lookup = {item.id: item for item in brief.findings}
    with dashboard_card("advisor-decision-agenda"):
        st.header("Decision agenda", anchor=False)
        st.caption(method)
        if brief.question == "growth":
            st.info(ATTRACTIVENESS_QUALIFIER)
        for rank, key in enumerate(priorities, start=1):
            finding = lookup[key]
            st.subheader(f"{rank}. {finding.title}", anchor=False)
            st.caption(f"Segment · {brief.segment}")
            st.markdown(f"**Evidence** · {finding.evidence}")
            if finding.assumption:
                st.markdown(f"**Assumptions and limits** · {finding.assumption}")
            st.markdown(f"**Strategic interpretation** · {finding.interpretation}")
            st.markdown(f"**Validate** · {finding.metric}")
            st.markdown(f"**Next action** · {finding.action}")
            st.caption(" · ".join(f"[{source.title}](<{source.url}>)" for source in finding.sources))


def findings_view(brief: PublicBrief) -> None:
    section = brief.focus_section()
    with st.expander(SECTION_NAMES[section]):
        if section == "growth":
            st.info(ATTRACTIVENESS_QUALIFIER)
        items = [item for item in brief.findings if item.section == section]
        if not items:
            st.caption("No reviewed findings match the current selection in this area.")
        for item in items:
            with dashboard_card(f"advisor-{item.id}"):
                st.subheader(item.title, anchor=False)
                st.markdown(f"**Verified evidence**  \n{item.evidence}")
                st.markdown(f"**Strategic interpretation**  \n{item.interpretation}")
                st.markdown(f"**Validation step**  \n{item.action}")
                st.caption(" · ".join(f"[{source.title}](<{source.url}>)" for source in item.sources))
        if section in WORKSPACE_LINKS:
            path, action = WORKSPACE_LINKS[section]
            st.page_link(path, label=action, icon=":material/arrow_forward:")

def local_financial_view(catalog: MarketCatalog, snapshot: FinancialSnapshot | None) -> None:
    with st.expander("Local financial scenario results", expanded=snapshot is not None):
        if snapshot is None:
            st.caption(
                "Save results from the Financial Scenario Simulator and match the company and segment "
                "selection to include those calculated figures in this briefing."
            )
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
