"""Executive introduction and research coverage dashboard."""

from itertools import batched

import streamlit as st

from brand import CASE_STUDY_TITLE, PRODUCT_NAME, TAGLINE
from data_services.market_catalog import load_catalog
from ui.catalog import WORKSPACES
from ui.components import dashboard_card
from ui.dashboard import executive_dashboard

CAPABILITY_DESCRIPTIONS = (
    "Explore hotel technology vendors, products, and documented market developments.",
    "Compare vendors’ documented capabilities and positioning.",
    "Assess customer portfolio opportunities, cross-selling, and product expansion.",
    "Compare financial scenarios using explicit assumptions.",
    "Ask focused questions and review answers grounded in research and models.",
)

st.title(PRODUCT_NAME, anchor=False)
st.markdown(f"**{TAGLINE}**")
st.markdown(
    "HospitIQ is an independent strategy and analytics project exploring how hospitality "
    "technology companies can identify growth opportunities, evaluate competitive positioning, "
    "and make informed strategic decisions."
)

with dashboard_card("executive-demo-entry"):
    st.caption(f"FEATURED STRATEGY CASE STUDY · {CASE_STUDY_TITLE}")
    st.subheader("Should Harborlight pilot embedded payments?", anchor=False)
    st.markdown(
        "Explore how market evidence, competitive intelligence and financial scenario analysis "
        "inform a strategic investment decision."
    )
    st.caption("Fictional company · Illustrative financial assumptions")
    if st.button("Explore the case study →", type="primary"):
        st.switch_page("app_pages/executive_case_study.py")

with dashboard_card("executive-introduction"):
    st.header("What is HospitIQ?", anchor=False)
    st.markdown(
        "**How the analysis connects**\n\n"
        "Market research informs competitive positioning. Positioning and customer fit guide "
        "growth priorities. Financial scenarios test those priorities, and the Strategy Advisor "
        "turns the evidence and trade-offs into actions to investigate."
    )

st.header("Explore HospitIQ", anchor=False)
st.caption(
    "Start with any workspace. Market research is a curated snapshot. The public portfolio demo uses "
    "synthetic customer data, and the case study uses fictional assumptions."
)
for row in batched(zip(WORKSPACES, CAPABILITY_DESCRIPTIONS, strict=True), 2):
    for column, (workspace, description) in zip(st.columns(len(row)), row, strict=True):
        with column, dashboard_card(f"overview-explore-{workspace.slug}", stretch=True):
            st.page_link(workspace.script, label=workspace.title, icon=workspace.icon)
            st.markdown(description)

try:
    catalog = load_catalog()
except (OSError, ValueError):
    st.error("The research snapshot could not be loaded. Validate the local catalog and reload this page.")
    st.stop()

executive_dashboard(catalog)
