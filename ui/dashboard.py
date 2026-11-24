"""Executive dashboard populated from the existing research snapshot."""

import streamlit as st

from data_services.market_catalog import MarketCatalog
from strategy_models.benchmark import (
    CATEGORIES,
    build_benchmark,
    capability_cells,
    eligible_companies,
    verified_products,
)
from ui.components import dashboard_card
from ui.market_intelligence import display_date
from ui.provenance import research_snapshot


def coverage_chart(label: str, counts: dict[str, int]) -> None:
    with dashboard_card(label.lower().replace(" ", "-")):
        st.subheader(label, anchor=False)
        if not any(counts.values()):
            st.caption("No verified evidence recorded for this view.")
            return
        st.bar_chart(
            {"Category": list(counts), "Count": list(counts.values())},
            x="Category", y="Count", x_label="", y_label="",
            horizontal=True, sort=False, color="#176F9B", alt=label,
            height=max(200, len(counts) * 27 + 44),
        )


def executive_dashboard(catalog: MarketCatalog) -> None:
    verified = catalog.filter_developments(verified_only=True)
    eligible = eligible_companies(catalog)
    portfolios = sum(len(verified_products(catalog, key)) for key in catalog.companies)
    metrics = (
        ("Verified companies", len(eligible)), ("Documented products", portfolios),
        ("Verified announcements", len(verified)),
        ("Sources reviewed", sum(source.reviewed_at is not None for source in catalog.sources.values())),
    )
    st.header("Strategic intelligence highlights", anchor=False)
    left, right = st.columns(2)
    with left, dashboard_card("executive-signals", stretch=True):
        st.subheader("Signals to investigate", anchor=False)
        for item in verified[:2]:
            st.markdown(f"**{item.title}**")
            st.markdown(item.interpretation)
        if not verified:
            st.caption("Highlights appear when verified developments are available.")
    with right, dashboard_card("executive-findings", stretch=True):
        st.subheader("Competitive research findings", anchor=False)
        featured = build_benchmark(catalog, eligible[:4]).contrasts[:2] if len(eligible) >= 2 else ()
        for finding in featured:
            st.markdown(f"**{finding.title}**")
            st.markdown(finding.significance)
            st.caption(finding.question)
        if not featured:
            st.caption("Comparative findings appear when sufficient evidence is available.")

    st.header("Research coverage", anchor=False)
    research_snapshot(catalog)
    with st.container(key="hgi-executive-metrics"):
        for column, (label, count) in zip(st.columns(4), metrics, strict=True):
            column.metric(label, count, border=True)
    st.caption("Counts reflect the curated research snapshot and its evidence coverage.")

    company_cells = [capability_cells(catalog, key) for key in eligible]
    cap_counts = {
        label: sum(cells[key].status == "Documented capability" for cells in company_cells)
        for key, label in CATEGORIES.items() if key not in {"segments", "partnerships"}
    }
    theme_counts = {catalog.themes[key]: count for key, count in catalog.theme_coverage().items()}
    company_counts = {
        company.name: sum(company.id in item.company_ids for item in verified)
        for company in catalog.companies.values()
    }
    left, right = st.columns(2)
    with left:
        coverage_chart("Companies by documented capability", cap_counts)
    with right:
        coverage_chart("Verified developments by theme", theme_counts)
    st.caption("A single announcement can appear under several themes or companies.")

    left, right = st.columns(2)
    with left:
        coverage_chart("Verified developments by company", company_counts)
    with right, dashboard_card("latest-developments", stretch=True):
        st.subheader("Latest sourced developments", anchor=False)
        if not verified:
            st.caption("No verified announcements in the research snapshot.")
        for item in verified[:3]:
            source = catalog.sources[item.source_id]
            st.markdown(f"[{item.title}](<{source.url}>)")
            st.caption(display_date(source.publication_date))
