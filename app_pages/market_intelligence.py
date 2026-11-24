"""Curated market intelligence for hospitality technology."""

import streamlit as st

from data_services.market_catalog import CatalogError, load_catalog
from ui.market_intelligence import (
    company_explorer,
    industry_developments,
    industry_overview,
    methodology,
)
from ui.provenance import research_snapshot

st.title("Market Intelligence", anchor=False)
st.markdown(
    "Explore documented hospitality technology products, announcements, "
    "and their possible implications for strategy."
)

try:
    catalog = load_catalog()
except (CatalogError, OSError, ValueError):
    st.error("The research snapshot could not be loaded. Validate the local catalog and reload this page.")
    st.stop()

research_snapshot(catalog)

overview, companies, developments = st.tabs(
    ["Industry Overview", "Company Explorer", "Industry Developments"]
)
with overview:
    industry_overview(catalog)
with companies:
    company_explorer(catalog)
with developments:
    industry_developments(catalog)

methodology(catalog)
