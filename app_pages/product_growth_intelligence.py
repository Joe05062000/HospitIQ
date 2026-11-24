"""Evidence-aware product growth and cross-sell workspace."""

import streamlit as st

from data_services.customer_portfolio import Customer
from data_services.market_catalog import load_catalog
from strategy_models.advisor import GROWTH_BRIEF_KEY, GrowthContext
from strategy_models.benchmark import eligible_companies
from strategy_models.growth_engine import prioritize, rank_candidates
from strategy_models.growth_research import DIMENSIONS, SEGMENTS, growth_products
from ui.growth import (
    opportunity_explorer,
    playbook_view,
    portfolio_input,
    priority_view,
    recommendation_view,
    segment_explorer,
    weight_controls,
)

st.title("Product Growth Intelligence", anchor=False)
st.markdown("Explore product combinations, qualify cross-sell opportunities, and build a 90-day commercial plan.")
try:
    catalog = load_catalog()
except (OSError, ValueError):
    st.error("The research snapshot could not be loaded. Validate the catalog and reload this page.")
    st.stop()

companies = eligible_companies(catalog)
if not companies:
    st.info("Product growth analysis requires a verified company profile.")
    st.stop()

company_column, mode_column = st.columns(2)
company_id = company_column.selectbox(
    "Company", companies, format_func=lambda key: catalog.companies[key].name, key="growth_company",
    index=companies.index("mews") if "mews" in companies else 0,
)
mode = mode_column.radio(
    "Evidence mode", ["Public Research Mode", "Customer Portfolio Mode"],
    horizontal=True, key="growth_mode",
)
products = growth_products(catalog, company_id)
if not products:
    st.info("No verified catalog products are mapped to growth categories for this company.")
    st.stop()
public = mode == "Public Research Mode"
dimension = st.radio(
    "Segmentation dimension", tuple(DIMENSIONS), format_func=DIMENSIONS.__getitem__,
    horizontal=True, key="growth_dimension",
)
segments = {key: item for key, item in SEGMENTS.items() if item.dimension == dimension}

if public:
    customers = tuple(
        Customer(organization=key) if dimension == "organization" else Customer(property_type=key)
        for key in segments
    )
    st.caption("Public research uses hypothetical segment profiles. Ownership and eligibility are unknown.")
else:
    customers, mode = portfolio_input(catalog)

explorer, segment_tab, recommendations, priority_tab, playbook = st.tabs([
    "Product explorer", "Customer segments", "Next-best product", "Cross-sell priorities", "Growth playbook",
])
with explorer:
    anchor = opportunity_explorer(catalog, products)
with segment_tab:
    segment_explorer(dimension)

with priority_tab:
    st.header("Cross-Sell Prioritization", anchor=False)
    left, right = st.columns(2)
    selected_segments = left.multiselect(
        "Segments", tuple(segments), format_func=lambda key: segments[key].label,
        key=f"growth_segment_filter_{dimension}",
    )
    selected_products = right.multiselect(
        "Available products", tuple(products), default=tuple(products),
        format_func=lambda key: products[key].name, key=f"growth_product_filter_{company_id}",
    )
    if selected_segments:
        st.caption("Filtering to named segments excludes rows with unknown segment membership.")
    weights = weight_controls()
    candidates = []
    if sum(weights.values()) == 0:
        st.warning("Set at least one strategic priority weight above zero.")
    elif customers and selected_products:
        candidates = rank_candidates(
            catalog, customers, tuple(products[key] for key in selected_products),
            dimension, weights, hypothetical_anchor=anchor if public else None,
        )
        if selected_segments:
            candidates = [item for item in candidates if item.segment in selected_segments]
    priorities = prioritize(candidates)
    public_segments = tuple(selected_segments or segments)
    if public and priorities:
        segment_for_advisor = st.selectbox(
            "Segment to send to Advisor", public_segments,
            format_func=lambda key: SEGMENTS[key].label, key="growth_advisor_segment",
        )
        if st.button("Review this ranking in Strategy Advisor", key="growth_open_advisor"):
            st.session_state[GROWTH_BRIEF_KEY] = GrowthContext(
                company_id, segment_for_advisor, anchor, tuple(selected_products), tuple(weights.items())
            )
            st.session_state["advisor_companies"] = [company_id]
            st.session_state["advisor_segment"] = segment_for_advisor
            st.session_state["advisor_question"] = "growth"
            st.switch_page("app_pages/ai_strategy_advisor.py")
    priority_view(
        priorities, public, customers, dimension, real_portfolio=mode == "Customer Portfolio Mode"
    )

with recommendations:
    recommendation_view(customers, candidates, dimension, public)
with playbook:
    playbook_view(catalog.companies[company_id].name, priorities, mode)
