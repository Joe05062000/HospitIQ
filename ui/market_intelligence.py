"""Presentation components for the market intelligence workspace."""

from datetime import date
from itertools import batched

import streamlit as st

from data_services.market_catalog import Development, MarketCatalog, Source, Status
from strategy_models.benchmark import capability_cells
from ui.components import dashboard_card
from ui.siteminder_research import siteminder_research

STATUS_LABELS: dict[Status, str] = {
    "verified": "Verified source",
    "unverified": "Unverified",
    "unavailable": "Unavailable",
}


def display_date(value: date | None) -> str:
    return value.strftime("%b %d, %Y").replace(" 0", " ") if value else "Not documented"


def evidence_badge(status: Status) -> None:
    st.badge(STATUS_LABELS[status], color="green" if status == "verified" else "gray")


def source_link(source: Source, *, publication: bool = False) -> None:
    st.markdown(f"[{source.title}](<{source.url}>)")
    verified = source.verified_at
    details = [STATUS_LABELS[source.status]]
    if publication:
        details.append(f"Published {display_date(source.publication_date)}")
    if verified:
        details.append(f"Verified {display_date(verified.date())} UTC")
    elif source.reviewed_at:
        details.append(f"Review recorded {source.reviewed_at}")
    st.caption(" · ".join(details))
    if source.review_note:
        st.caption(source.review_note)


def industry_overview(catalog: MarketCatalog) -> None:
    st.header("Industry Overview", anchor=False)
    st.caption("This is a selective snapshot of vendor disclosures. Its coverage cannot establish industry-wide prevalence.")
    verified = catalog.filter_developments(verified_only=True)
    company_count = sum(
        catalog.evidence_status(company.source_ids) == "verified"
        for company in catalog.companies.values()
    )
    latest = catalog.sources[verified[0].source_id].publication_date if verified else None
    coverage = catalog.theme_coverage()
    cards = (
        ("Verified company profiles", f"{company_count} / {len(catalog.companies)}"),
        ("Verified developments", str(len(verified))),
        ("Themes with verified evidence", f"{sum(bool(n) for n in coverage.values())} / {len(coverage)}"),
        ("Latest verified publication", display_date(latest) if latest else "None yet"),
    )
    for row in batched(cards, 2):
        for column, (label, value) in zip(st.columns(2), row, strict=True):
            column.metric(label, value, border=True)

    themes = (
        (
            "Platform integration and consolidation", "amadeus-b2",
            "Combining reservation, website and guest tools may reduce handoffs, with migration and vendor dependency to assess.",
            "Which interfaces and operational handoffs would a combined rollout actually remove?",
        ),
        (
            "Embedded payments and monetization", "mews-finance",
            "Collections and multicurrency can extend a platform into finance workflows. Adoption and realised margins remain unknown.",
            "Which hotels would pay for these workflows, and how would settlement and support affect contribution?",
        ),
        (
            "Strategic partnerships", "mews-siteminder",
            "Embedded distribution can extend a platform through a partner. Integration ownership and commercial terms affect the value.",
            "Who owns onboarding, support and channel exceptions once distribution is embedded?",
        ),
        (
            "AI and automation", "oracle-assistant",
            "In-workflow assistance could reduce staff effort, with exception handling and override quality to validate.",
            "Which front-desk tasks deliver measurable time savings with acceptable errors and overrides?",
        ),
        (
            "Distribution and revenue management", "siteminder-commerce",
            "Joining pricing and distribution recommendations could shorten the time to act while keeping approval with hotel staff.",
            "How often do hotels approve and implement a recommendation, and what changes after implementation?",
        ),
    )
    for title, development_id, implication, question in themes:
        item = next((entry for entry in verified if entry.id == development_id), None)
        if item is None:
            continue
        with dashboard_card(f"industry-theme-{development_id}"):
            st.subheader(title, anchor=False)
            st.markdown(f"**What the evidence shows** · {item.summary}")
            st.markdown(f"**Commercial implication** · {implication}")
            st.markdown(f"**Strategic question** · {question}")
            source = catalog.sources[item.source_id]
            st.caption(f"[{source.title}](<{source.url}>)")

    st.subheader("Coverage by strategic theme", anchor=False)
    st.caption("A development can appear under more than one theme.")
    if not coverage:
        st.info("No strategic themes have been added to this snapshot.")
        return
    with st.container(horizontal=True, gap="small"):
        for key, count in coverage.items():
            st.badge(f"{catalog.themes[key]} · {count}", color="gray")


def company_explorer(catalog: MarketCatalog) -> None:
    st.header("Company Explorer", anchor=False)
    if not catalog.companies:
        st.info("Company profiles will appear here once they are added to the research catalog.")
        return

    company_id = st.selectbox(
        "Company",
        tuple(catalog.companies),
        format_func=lambda key: catalog.companies[key].name,
        key="market_company",
    )
    company = catalog.companies[company_id]
    products = catalog.company_products(company_id)
    verified_products = [
        product for product in products if catalog.evidence_status(product.source_ids) == "verified"
    ]
    verified_categories = list(dict.fromkeys(product.category for product in verified_products))

    with dashboard_card("market-company-profile"):
        evidence_badge(catalog.evidence_status(company.source_ids))
        st.subheader(company.name, anchor=False)
        st.caption(company.official_name)
        st.markdown(company.description)
        st.markdown(f"[Official website](<{company.website}>)")
        st.markdown(f"**Customer segments**  \n{', '.join(company.segments) or 'Not documented'}")
        st.markdown(f"**Verified product categories**  \n{', '.join(verified_categories) or 'None yet'}")

    with st.expander("Company profile sources"):
        if not company.source_ids:
            st.info("No supporting sources have been added for this profile.")
        for source_id in company.source_ids:
            source_link(catalog.sources[source_id])

    if company_id == "siteminder":
        siteminder_research()

    distribution = capability_cells(catalog, company_id)["distribution"]
    if any(item.stage for item in distribution.evidence):
        with st.expander("Distribution evidence and rollout status"):
            for evidence in distribution.evidence:
                st.markdown(f"**{evidence.stage or 'Documented product'}** · {evidence.text}")
                for source in evidence.sources:
                    source_link(source)

    st.subheader("Documented product portfolio", anchor=False)
    if not products:
        st.info("No products have been added for this company.")
    for product in products:
        with st.expander(f"{product.name} · {product.category}"):
            evidence_badge(catalog.evidence_status(product.source_ids))
            st.markdown(product.description)
            if not product.source_ids:
                st.caption("No supporting source recorded.")
            for source_id in product.source_ids:
                source_link(catalog.sources[source_id])

    st.subheader("Public announcements", anchor=False)
    announcements = catalog.filter_developments(companies={company_id})
    if not announcements:
        st.info("No announcements have been added for this company.")
    for item in announcements:
        development_card(catalog, item, "company")


def development_details(catalog: MarketCatalog, item: Development) -> None:
    source = catalog.sources[item.source_id]
    evidence_badge(source.status)
    if source.status == "verified":
        st.markdown(f"**What happened**  \n{item.summary}")
        st.markdown(f"**Why it matters commercially · Interpretation**  \n{item.interpretation}")
        if item.questions:
            st.markdown(f"**What to investigate next**  \n{item.questions[0]}")
        with st.expander("More implications and questions"):
            st.markdown(f"**Possible revenue or product implications**  \n{item.implication}")
            st.markdown("**Questions to investigate**")
            st.markdown("\n".join(f"- {question}" for question in item.questions))
    else:
        st.info("This announcement is awaiting source verification. Its summary and analysis are withheld.")
    source_link(source, publication=True)
    st.caption(f"Source limitations · {item.limitations}")


def industry_developments(catalog: MarketCatalog) -> None:
    st.header("Industry Developments", anchor=False)
    st.caption("Filter the curated announcements by company, theme, or publication date.")
    company_col, theme_col = st.columns(2)
    companies = company_col.multiselect(
        "Companies",
        tuple(catalog.companies),
        format_func=lambda key: catalog.companies[key].name,
        key="market_filter_companies",
    )
    themes = theme_col.multiselect(
        "Strategic themes",
        tuple(catalog.themes),
        format_func=catalog.themes.__getitem__,
        key="market_filter_themes",
    )
    start_col, end_col = st.columns(2)
    dated_sources = [
        published
        for item in catalog.developments.values()
        if (published := catalog.sources[item.source_id].publication_date) is not None
    ]
    earliest = min(dated_sources, default=None)
    latest = max(dated_sources, default=None)
    start = start_col.date_input(
        "Published on or after", value=None, min_value=earliest, max_value=latest, key="market_start"
    )
    end = end_col.date_input(
        "Published on or before", value=None, min_value=earliest, max_value=latest, key="market_end"
    )
    if start and end and start > end:
        st.warning("Choose a start date on or before the end date.")
        return
    matches = catalog.filter_developments(
        companies=set(companies), themes=set(themes), start=start, end=end
    )
    st.caption(f"{len(matches)} of {len(catalog.developments)} announcements")
    if not matches:
        st.info("No announcements match. Clear a company, theme, or date filter to broaden the search.")
        return
    for item in matches:
        development_card(catalog, item, "feed")


def development_card(catalog: MarketCatalog, item: Development, section: str) -> None:
    with dashboard_card(f"market-{section}-{item.id}"):
        names = ", ".join(catalog.companies[key].name for key in item.company_ids)
        labels = " · ".join(catalog.themes[key] for key in item.theme_ids)
        st.caption(f"{names}  |  {labels}")
        st.subheader(item.title, anchor=False)
        development_details(catalog, item)


def methodology(catalog: MarketCatalog) -> None:
    with st.expander("Methodology and limitations"):
        reviewed = [time.date() for source in catalog.sources.values() if (time := source.verified_at)]
        if reviewed:
            st.caption(f"Latest source verification · {display_date(max(reviewed))} UTC")
        st.markdown(
            "The catalog is a manually maintained snapshot of selected vendor product pages, "
            "documentation and dated announcements. Verified means the cited page was "
            "inspected for the recorded claim. Vendor statements establish what was publicly "
            "documented or announced. Adoption, rollout status and outcomes may require "
            "independent evidence."
        )
        st.markdown(
            "Publication dates come from the original announcements. Verification dates record "
            "when source contents were inspected. Joint announcements are counted once, and "
            "theme totals can overlap. The snapshot has no automatic refresh."
        )
        st.markdown(
            "Coverage is selective across vendors, periods and products. Strategic implications "
            "are hypotheses for further investigation. Market share, vendor performance and "
            "financial forecasts are outside the coverage of this dataset."
        )
