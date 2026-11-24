"""Product growth workspace components. Portfolio inputs stay session-local."""

from itertools import batched

import streamlit as st

from data_services.customer_portfolio import (
    SYNTHETIC_CSV,
    TEMPLATE,
    Customer,
    PortfolioError,
    parse_portfolio,
)
from data_services.deployment_mode import private_demo
from data_services.market_catalog import MarketCatalog, Product, Source
from strategy_models.benchmark import capability_cells
from strategy_models.financial_transfer import HANDOFF_KEY, opportunity_from_growth
from strategy_models.growth_engine import (
    ATTRACTIVENESS_QUALIFIER,
    DEFAULT_WEIGHTS,
    DIAGNOSTICS,
    FACTORS,
    METHODOLOGY,
    RUBRIC,
    Candidate,
    Priority,
)
from strategy_models.growth_playbook import playbook_html, playbook_steps, segment_label
from strategy_models.growth_research import (
    CATEGORY_LABELS,
    COMPLEMENTS,
    DIMENSIONS,
    NEED_LABELS,
    PRODUCT_CLASS,
    SEGMENTS,
    Dimension,
    documented_integration,
    product_sources,
)
from ui.components import dashboard_card


def source_refs(sources: tuple[Source, ...]) -> None:
    if sources:
        st.caption(" · ".join(f"[{source.title}](<{source.url}>)" for source in sources))


def opportunity_explorer(catalog: MarketCatalog, products: dict[str, Product]) -> str:
    st.header("Product Opportunity Explorer", anchor=False)
    category_ids = tuple(dict.fromkeys(PRODUCT_CLASS[key] for key in products))
    category = st.selectbox(
        "Anchor product category", category_ids, format_func=CATEGORY_LABELS.__getitem__,
        key="growth_anchor",
    )
    anchors = frozenset(key for key in products if PRODUCT_CLASS[key] == category)
    with dashboard_card("growth-portfolio"):
        st.subheader("Verified product portfolio", anchor=False)
        for product in products.values():
            with st.expander(product.name, expanded=product.id in anchors):
                st.markdown(f"**{CATEGORY_LABELS[PRODUCT_CLASS[product.id]]}**")
                st.markdown(product.description)
                source_refs(product_sources(catalog, product))

    distribution = capability_cells(catalog, next(iter(products.values())).company_id)["distribution"]
    if any(item.stage for item in distribution.evidence):
        with st.expander("Distribution evidence and rollout status"):
            for item in distribution.evidence:
                st.markdown(f"**{item.stage or 'Documented product'}** · {item.text}")
                source_refs(item.sources)
            st.caption("Product rankings require a mapped catalog product. Integration evidence alone does not enter the product list.")
    st.subheader("Complementary product categories", anchor=False)
    st.caption("Commercial fit is a hypothesis. Documented integration is specific to the cited product pair.")
    for rule in COMPLEMENTS:
        if category not in rule.categories:
            continue
        target = next(key for key in rule.categories if key != category)
        options = [product for product in products.values() if PRODUCT_CLASS[product.id] == target]
        with dashboard_card(f"growth-complement-{target}"):
            st.subheader(CATEGORY_LABELS[target], anchor=False)
            st.markdown(rule.rationale)
            if not options:
                st.badge("Portfolio research gap", color="gray")
                st.caption("No standalone product in this category is mapped for scoring. Review any integration or rollout evidence separately.")
            for product in options:
                st.markdown(f"**{product.name}**")
                source_refs(product_sources(catalog, product))
                verified = documented_integration(catalog, product.id, anchors)
                if verified:
                    integration, source = verified
                    st.badge("Documented product-pair integration", color="green")
                    st.caption(integration.detail)
                    source_refs((source,))
                else:
                    st.caption("Potential combination · Technical integration unverified")
            st.caption(f"Implementation check · {rule.execution}")
    return category


def segment_explorer(dimension: Dimension) -> None:
    st.header("Customer Segment Intelligence", anchor=False)
    st.caption(
        "Organization size and primary property type are separate dimensions. Each portfolio "
        "row belongs to one segment per dimension. Priorities use one dimension at a time."
    )
    key = st.selectbox(
        "Segment to explore", tuple(SEGMENTS), format_func=segment_label, key="growth_segment_profile",
        index=0 if dimension == "organization" else 3,
    )
    segment = SEGMENTS[key]
    with dashboard_card("growth-segment-profile"):
        st.subheader(segment.label, anchor=False)
        st.caption(f"{DIMENSIONS[segment.dimension]} · {segment.definition}")
        st.markdown("**Hypothetical customer needs**")
        for label, description in zip(NEED_LABELS, segment.needs, strict=True):
            st.markdown(f"**{label}**  \n{description}")
        st.caption(
            "These are discovery prompts. Actual needs depend on operating model, markets, "
            "existing systems, and customer interviews."
        )


def portfolio_input(catalog: MarketCatalog) -> tuple[tuple[Customer, ...], str]:
    allow_upload = private_demo()
    if allow_upload:
        st.info(
            "This demo is intended for synthetic or appropriately de-identified business data. "
            "Do not upload confidential or personal customer information. Raw CSV data stays "
            "in the Streamlit session. Exports include segment-level conclusions and public sources."
        )
    with st.expander("CSV format and sample"):
        st.markdown(
            "Use UTF-8 CSV, up to 1 MB and 500 customer rows. Headers may appear in any order. "
            "Only include columns you have information for. A populated row is required."
        )
        st.code(TEMPLATE.strip(), language="text", wrap_lines=True)
        st.markdown(
            "- Use one row per customer. Supplied customer IDs must be unique.\n"
            "- Enter documented segment IDs or labels. Use `organization_segment` and "
            "`property_type` to provide both dimensions, or `hotel_segment` to supply one.\n"
            "- Use room count for `property_size`. Geography and notes are optional context.\n"
            "- Enter catalog product IDs separated by `|`. Leave ownership blank when unknown. "
            "Use `-` to confirm no owned products, or supply a complete list of owned products.\n"
            "- List confirmed eligible and ineligible products in their respective fields. "
            "Unlisted products have unknown eligibility."
        )
        st.code(", ".join(SEGMENTS), language="text", wrap_lines=True)
        with st.expander("Catalog product IDs"):
            for product in catalog.products.values():
                st.text(f"{product.id} · {product.name}")
        left, right = st.columns(2)
        left.download_button("Download CSV template", TEMPLATE, "portfolio-template.csv", "text/csv", on_click="ignore")
        right.download_button("Download synthetic sample", SYNTHETIC_CSV, "synthetic-portfolio.csv", "text/csv", on_click="ignore")
    input_kind = st.radio(
        "Portfolio input", ["Upload CSV", "Synthetic demonstration"] if allow_upload else ["Synthetic demonstration"],
        horizontal=True, key="growth_input_kind"
    )
    if not allow_upload:
        st.caption("The public demo uses the built-in synthetic portfolio. Customer CSV uploads are unavailable in public mode.")
    if not allow_upload or input_kind == "Synthetic demonstration":
        st.caption("Four fictional Mews scenarios demonstrate the workflow. They represent no actual customers.")
        try:
            return parse_portfolio(SYNTHETIC_CSV.encode(), catalog.products), "Synthetic portfolio demo"
        except PortfolioError:
            st.warning("The synthetic sample references products missing from the current catalog.")
            return (), "Synthetic portfolio demo"

    uploaded = st.file_uploader("Customer portfolio CSV", type=["csv"], max_upload_size=1, key="growth_portfolio_file")
    if uploaded is None:
        st.caption("Upload a CSV or switch to the synthetic demonstration to evaluate portfolio cases.")
        return (), "Customer Portfolio Mode"
    try:
        customers = parse_portfolio(uploaded.getvalue(), catalog.products)
    except PortfolioError as exc:
        st.error(str(exc))
        return (), "Customer Portfolio Mode"
    st.success(f"Validated {len(customers)} customer rows.")
    return customers, "Customer Portfolio Mode"


def weight_controls() -> dict[str, int]:
    weights = {}
    with st.expander("Strategic priority weights"):
        st.caption(METHODOLOGY)
        for row in batched(FACTORS, 2):
            for column, key in zip(st.columns(len(row)), row, strict=True):
                weights[key] = column.slider(
                    FACTORS[key], 0, 100, DEFAULT_WEIGHTS[key], step=5, key=f"growth_weight_{key}"
                )
        st.caption(RUBRIC)
    return weights


def recommendation_view(
    customers: tuple[Customer, ...], candidates: list[Candidate], dimension: Dimension, public: bool,
) -> None:
    st.header("Next-Best-Product Recommendations", anchor=False)
    if not customers:
        st.info("Add portfolio inputs or select a segment profile to review product candidates.")
        return
    row = st.selectbox(
        "Scenario to review", tuple(range(1, len(customers) + 1)), key="growth_focus_case",
        format_func=lambda index: segment_label(customers[index - 1].segment(dimension)) if public else (
            f"Portfolio row {index} · {segment_label(customers[index - 1].segment(dimension))}"
        ),
    )
    customer = customers[row - 1]
    if not public:
        for label, value in (
            ("Customer ID", customer.id), ("Room count", customer.size),
            ("Geography", customer.geography), ("Opportunity notes", customer.notes),
        ):
            if value is not None:
                st.text(f"{label} · {value}")
    matches = [item for item in candidates if item.row == row]
    if not matches:
        st.info("No verified products match this scenario and the current filters. Owned and ineligible products are excluded.")
        return
    st.info(ATTRACTIVENESS_QUALIFIER)
    for candidate in matches:
        with dashboard_card(f"growth-recommendation-{candidate.product.id}"):
            st.subheader(candidate.product.name, anchor=False)
            st.badge(candidate.readiness, color="green" if candidate.readiness == "Pilot candidate" else "gray")
            st.caption(
                f"Attractiveness {candidate.score:.0f}/100 "
                f"· Segment fit {candidate.factors['fit']}/4 "
                f"· Evidence confidence {candidate.factors['evidence']}/4"
            )
            st.markdown(f"**Product evidence**  \n{candidate.product.description}")
            st.markdown(f"**Commercial hypothesis**  \n{candidate.rationale}")
            st.markdown(f"**Potential benefit**  \n{candidate.benefit}")
            st.markdown(f"**Ownership and eligibility**  \n"
                        f"{'Current ownership list supplied' if candidate.ownership_known else 'Ownership unknown'} · "
                        f"{'Eligibility confirmed in input' if candidate.eligibility_known else 'Eligibility unknown'}")
            st.markdown(f"**Compatibility**  \n{candidate.compatibility}")
            source_refs(candidate.sources)
            st.markdown(f"**Next validation step**  \n{candidate.execution}")
            with st.expander("Score details and due diligence"):
                st.markdown(" · ".join(f"{(FACTORS | DIAGNOSTICS)[key]} {value}/4" for key, value in candidate.factors.items()))
                st.markdown(
                    "**Assumptions to validate**  \n"
                    "Segment fit, business value and implementation effort use planning rules. "
                    "Confirm buyer need, deployment, ownership and eligibility before outreach."
                )
    with st.expander("Ranking methodology"):
        st.markdown(METHODOLOGY)
        st.markdown(RUBRIC)


def priority_view(
    priorities: list[Priority], public: bool, customers: tuple[Customer, ...],
    dimension: Dimension, *, real_portfolio: bool,
) -> None:
    if not priorities:
        st.info("No opportunities match the current filters and portfolio checks.")
        return
    if public:
        st.caption("Each result is a hypothetical segment scenario. All public results are discovery hypotheses.")
    else:
        st.caption("Ranks use mean case scores per segment and product. Counts describe evaluated cases in this session.")
    st.info(ATTRACTIVENESS_QUALIFIER)
    limit = st.selectbox("Priorities to show", [5, 10, 20, 50], key="growth_priority_limit")
    for rank, item in enumerate(priorities[:limit], start=1):
        with dashboard_card(f"growth-priority-{rank}"):
            st.subheader(f"{rank}. {item.product.name}", anchor=False)
            detail = (
                f"{segment_label(item.segment)} · Attractiveness {item.score:.0f}/100 "
                f"· Mean fit {item.fit:.0f}/4 · Mean evidence confidence {item.evidence:.0f}/4"
            )
            if not public:
                detail += f" · {item.pilot_count} pilot candidates / {item.count} evaluated"
            st.caption(detail)
            st.markdown(item.benefit)
            st.caption(f"Execution and unknowns · {item.execution} Confirm readiness at account level.")
            source_refs(item.sources)
            if st.button(
                "Open in Financial Simulator", key=f"growth_financial_{item.product.id}_{item.segment}",
                icon=":material/calculate:",
            ):
                st.session_state[HANDOFF_KEY] = opportunity_from_growth(
                    item, customers, dimension, real_portfolio=real_portfolio
                )
                st.session_state["financial_opportunity_mode"] = "Product Growth handoff"
                st.switch_page("app_pages/financial_scenario_simulator.py")
    st.caption(f"Showing {min(limit, len(priorities))} of {len(priorities)} ranked priorities.")


def playbook_view(company: str, priorities: list[Priority], mode: str) -> None:
    st.header("Commercial Growth Playbook", anchor=False)
    if not priorities:
        st.info("Rank at least one opportunity to generate a 90-day playbook.")
        return
    st.caption("The plan follows the current ranking. Portfolio exports contain segment-level findings only.")
    with dashboard_card("growth-playbook-focus"):
        st.info(ATTRACTIVENESS_QUALIFIER)
        st.subheader("Priority segments and products", anchor=False)
        for item in priorities[:3]:
            st.markdown(
                f"- {segment_label(item.segment)} · {item.product.name} · "
                f"Attractiveness {item.score:.0f}/100"
            )
            source_refs(item.sources)
    for index, step in enumerate(playbook_steps(priorities)):
        with dashboard_card(f"growth-playbook-{index}"):
            st.subheader(f"{step.window} · {step.title}", anchor=False)
            st.markdown("\n".join(f"- {activity}" for activity in step.activities))
            st.markdown(f"**Decision checkpoint**  \n{step.decision}")
    st.caption("Key risks · Unsupported configurations, onboarding effort, and unconfirmed ownership or eligibility.")
    st.download_button(
        "Download 90-day playbook", playbook_html(company, priorities, mode),
        "hospitiq-commercial-growth-playbook.html", "text/html", icon=":material/download:", on_click="ignore",
    )
