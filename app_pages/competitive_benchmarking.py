"""Competitive benchmarking workspace."""

import streamlit as st

from data_services.market_catalog import load_catalog
from strategy_models.benchmark import build_benchmark, eligible_companies
from ui.benchmark import (
    capability_matrix,
    contrast_cards,
    executive_summary,
    opportunity_explorer,
    portfolios,
)
from ui.provenance import research_snapshot

st.title("Competitive Benchmarking", anchor=False)
st.markdown("Compare documented capabilities, identify product differences, and explore investment questions.")

try:
    catalog = load_catalog()
except (OSError, ValueError):
    st.error("The research snapshot could not be loaded. Validate the local catalog and reload this page.")
    st.stop()

research_snapshot(catalog)

eligible = eligible_companies(catalog)
if len(eligible) < 2:
    st.info("Benchmarking becomes available when the catalog has two verified company profiles.")
    st.stop()

selection = st.multiselect(
    "Companies to compare", eligible, default=eligible[:4], max_selections=4,
    format_func=lambda key: catalog.companies[key].name, key="benchmark_companies",
    help="Choose two to four companies with verified profiles.",
)
if len(selection) < 2:
    st.info("Select at least two companies to build a comparison.")
    st.stop()

benchmark = build_benchmark(catalog, tuple(selection))
comparison, differentiation, opportunities, summary = st.tabs(
    ["Company comparison", "Strategic differentiation", "Opportunity explorer", "Executive summary"]
)
with comparison:
    portfolios(benchmark)
    capability_matrix(benchmark)
with differentiation:
    contrast_cards(benchmark)
with opportunities:
    opportunity_explorer(benchmark)
with summary:
    executive_summary(benchmark)
