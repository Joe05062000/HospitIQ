"""Competitive benchmarking and opportunity exploration views."""

from itertools import batched

import streamlit as st

from strategy_models.benchmark import (
    CATEGORIES,
    THEMES,
    Benchmark,
    Evidence,
    theme_companies,
    theme_developments,
    verified_products,
)
from strategy_models.benchmark_report import LIMITATIONS, executive_report, matrix_html
from ui.components import dashboard_card
from ui.market_intelligence import source_link


def show_evidence(item: Evidence) -> None:
    if item.stage:
        st.caption(item.stage)
    st.markdown(item.text)
    st.caption(" · ".join(f"[{source.title}](<{source.url}>)" for source in item.sources))


def portfolios(benchmark: Benchmark) -> None:
    st.header("Product portfolios", anchor=False)
    for row in batched(benchmark.companies, 2):
        for column, key in zip(st.columns(len(row)), row, strict=True):
            company = benchmark.catalog.companies[key]
            products = verified_products(benchmark.catalog, key)
            with column, dashboard_card(f"benchmark-portfolio-{key}", stretch=True):
                st.subheader(company.name, anchor=False)
                st.markdown(company.description)
                if products:
                    st.markdown("\n".join(f"- {product.name}" for product in products))
                else:
                    st.caption("No verified products recorded.")
                st.markdown(f"[Official company website](<{company.website}>)")


def capability_matrix(benchmark: Benchmark) -> None:
    st.header("Product capability matrix", anchor=False)
    st.caption(
        "Each documented cell links to its evidence. An unverified cell marks a research gap. "
        "Not applicable is reserved for an explicitly documented scope exclusion."
    )
    st.html(matrix_html(benchmark))


def contrast_cards(benchmark: Benchmark) -> None:
    st.header("Strategic differentiation", anchor=False)
    if not benchmark.contrasts:
        st.info("This selection has insufficient verified evidence for a curated contrast.")
    for contrast in benchmark.contrasts:
        with dashboard_card(f"benchmark-contrast-{contrast.companies[0]}-{contrast.companies[1]}"):
            st.subheader(contrast.title, anchor=False)
            for index, key in enumerate(contrast.companies):
                st.markdown(f"**{benchmark.catalog.companies[key].name} · Verified evidence**")
                for item in benchmark.contrast_evidence(contrast, index):
                    show_evidence(item)
            st.markdown(f"**Why it matters commercially**  \n{contrast.significance}")
            st.markdown(f"**Question for management**  \n{contrast.question}")
            with st.expander("Investment and cross-sell options"):
                st.markdown(f"**Product investment**  \n{contrast.investment}")
                st.markdown(f"**Cross-selling or portfolio expansion**  \n{contrast.expansion}")


def opportunity_explorer(benchmark: Benchmark) -> None:
    st.header("Strategic Opportunity Explorer", anchor=False)
    theme = st.selectbox(
        "Strategic theme", THEMES, format_func=lambda item: item.name, key="benchmark_theme"
    )
    active = theme_companies(benchmark, theme)
    if active:
        st.markdown("**Companies with evidence in this theme**")
        st.write(", ".join(benchmark.catalog.companies[key].name for key in active))
    else:
        st.info("No verified capabilities or developments match this theme for the selected companies.")
    for key in active:
        entries = [
            item
            for category in theme.categories
            if benchmark.matrix[category][key].evidence
            for item in benchmark.matrix[category][key].evidence
        ]
        if entries:
            with dashboard_card(f"benchmark-theme-{key}"):
                st.subheader(benchmark.catalog.companies[key].name, anchor=False)
                seen = set()
                for item in entries:
                    if item.text not in seen:
                        show_evidence(item)
                        seen.add(item.text)

    st.subheader("Verified developments", anchor=False)
    developments = theme_developments(benchmark, theme)
    if not developments:
        st.caption("No verified announcements in this theme for the selection.")
    for development in developments:
        with st.expander(development.title):
            st.markdown(development.summary)
            source_link(benchmark.catalog.sources[development.source_id], publication=True)

    if active:
        with dashboard_card("benchmark-opportunity"):
            st.subheader("Opportunity hypothesis", anchor=False)
            st.markdown(theme.opportunity)
            st.markdown(f"**Risks and uncertainties**  \n{theme.risk}")
            st.markdown(f"**Leadership question**  \n{theme.question}")


def executive_summary(benchmark: Benchmark) -> None:
    st.header("Executive comparison", anchor=False)
    with dashboard_card("benchmark-summary"):
        st.markdown(", ".join(benchmark.catalog.companies[key].name for key in benchmark.companies))
        st.subheader("Documented similarities", anchor=False)
        similarities = ", ".join(CATEGORIES[key] for key in benchmark.similarities)
        st.markdown(similarities or "No shared category is verified across the full selection.")
        st.subheader("Documented differences and implications", anchor=False)
        for contrast in benchmark.contrasts:
            st.markdown(f"- **{contrast.title}** · {contrast.significance}")
            for index in range(len(contrast.companies)):
                for item in benchmark.contrast_evidence(contrast, index):
                    show_evidence(item)
        if not benchmark.contrasts:
            st.caption("No curated contrast has sufficient verified evidence.")
        st.caption(LIMITATIONS)
    st.download_button(
        "Download executive comparison",
        data=executive_report(benchmark),
        file_name="hospitiq-executive-comparison.html",
        mime="text/html",
        icon=":material/download:",
        on_click="ignore",
    )
