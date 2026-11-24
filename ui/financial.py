"""Streamlit views for assumptions, cohort projections, and financial comparisons."""

from dataclasses import replace
from itertools import batched

import plotly.graph_objects as go  # type: ignore[import-untyped]
import streamlit as st

from brand import CASE_STUDY_TITLE
from data_services.market_catalog import MarketCatalog, Product
from strategy_models.executive_case import ASSUMPTIONS as CASE_ASSUMPTIONS
from strategy_models.executive_case import ORIGIN as CASE_ORIGIN
from strategy_models.executive_case import POPULATION as CASE_POPULATION
from strategy_models.financial import (
    FORMULAS,
    LIMITATIONS,
    METHODOLOGY,
    SCENARIOS,
    Assumptions,
    Projection,
    Sensitivity,
    simulate,
)
from strategy_models.financial_report import (
    ROUNDED_COUNTS,
    annual_rows,
    assumption_lines,
    money,
    rollout_payback,
)
from strategy_models.financial_transfer import Opportunity
from strategy_models.growth_research import CATEGORY_LABELS, PRODUCT_CLASS, SEGMENTS
from ui.components import dashboard_card

DEMO = {
    "Conservative": ((8.0, 10.0, 12.0), 2_000.0, 55.0, 55_000.0, 150_000.0, 2, 85.0),
    "Base": ((15.0, 18.0, 20.0), 2_500.0, 65.0, 60_000.0, 150_000.0, 1, 90.0),
    "Ambitious": ((23.0, 26.0, 28.0), 3_000.0, 72.0, 75_000.0, 180_000.0, 1, 94.0),
}


def opportunity_selector(
    catalog: MarketCatalog, products: dict[str, Product], transferred: Opportunity | None,
    case: Opportunity | None = None,
) -> Opportunity:
    st.header("Choose opportunity", anchor=False)
    options = ["Independent model"]
    if transferred:
        options.insert(0, "Product Growth handoff")
    if case:
        options.insert(0, CASE_STUDY_TITLE)
    mode = st.radio("Opportunity source", options, horizontal=True, key="financial_opportunity_mode")
    if mode == CASE_STUDY_TITLE and case is not None:
        opportunity = case
    elif mode == "Product Growth handoff" and transferred is not None:
        opportunity = transferred
    else:
        left, right = st.columns(2)
        product = left.selectbox(
            "Product opportunity", tuple(products), format_func=lambda key: products[key].name,
            key="financial_product"
        )
        segment = right.selectbox(
            "Customer segment", (None, *SEGMENTS), key="financial_segment",
            format_func=lambda key: SEGMENTS[key].label if key else "Unspecified or mixed",
        )
        opportunity = Opportunity(product, PRODUCT_CLASS[product], segment, tuple(products[product].source_ids))

    item = products[opportunity.product_id]
    with dashboard_card("financial-opportunity"):
        st.subheader(opportunity.fictional_label or item.name, anchor=False)
        if not opportunity.fictional_label and st.session_state.get("financial_input_mode") != "Enter assumptions":
            st.caption("**Illustrative financial inputs** · Planning examples only.")
        segment_name = SEGMENTS[opportunity.segment].label if opportunity.segment else "Unspecified or mixed"
        st.caption(f"{CATEGORY_LABELS[opportunity.category]} · {segment_name}")
        st.markdown(
            "Fictional embedded payments offer for existing hotel customers. Links provide industry context."
            if opportunity.fictional_label else item.description
        )
        st.markdown(f"**Eligibility** · {opportunity.eligibility_status}")
        if opportunity.known_eligible is not None:
            st.caption(f"{opportunity.known_eligible:,} eligible non-adopters with unique IDs in the supplied portfolio.")
        if opportunity.uncounted_qualifying_rows:
            st.caption(
                f"{opportunity.uncounted_qualifying_rows:,} otherwise qualifying rows were excluded "
                "from the count because a unique customer ID could not be established."
            )
        sources = [
            catalog.sources[key] for key in opportunity.source_ids
            if key in catalog.sources and catalog.sources[key].status == "verified"
        ]
        if sources:
            st.caption(" · ".join(f"[{source.title}](<{source.url}>)" for source in sources))
    return opportunity


def scenario_inputs(
    name: str, opportunity: Opportunity, population: int | None, demo: bool, currency: str,
) -> Assumptions | None:
    rates, price, margin, fixed, investment, rollout, retention = DEMO[name]
    if opportunity.fictional_label:
        defaults = CASE_ASSUMPTIONS[name]
        y1, y2, y3 = defaults.adoption
        rates = (round(y1 * 100, 8), round(y2 * 100, 8), round(y3 * 100, 8))
        price = float(defaults.revenue_per_adopter)
        fixed = float(defaults.fixed_cost)
        investment = float(defaults.investment)
        margin, retention = round(defaults.margin * 100, 8), round(defaults.retention * 100, 8)
        rollout = defaults.rollout_year
    key = f"financial_{opportunity.identifier}_{name}_{'demo' if demo else 'manual'}"
    st.caption("Adoption rates apply only in active rollout years and to the remaining eligible population.")
    timing, convention = st.columns(2)
    timing_year = timing.selectbox(
        "Launch year", (1, 2, 3), index=rollout - 1 if demo else None, key=f"{key}_rollout",
    )
    activation_key = f"{key}_activation"
    saved_activation_key = f"{activation_key}_saved"
    activation_options = ("Beginning of year", "Mid-year")
    default_activation = CASE_ASSUMPTIONS[name].activation if opportunity.fictional_label else "Mid-year"
    saved_activation = st.session_state.get(saved_activation_key, default_activation)
    activation = convention.selectbox(
        "Customer activation timing", activation_options,
        index=activation_options.index(saved_activation), key=activation_key,
        on_change=lambda: st.session_state.update({saved_activation_key: st.session_state[activation_key]}),
        help="With mid-year activation, new adopters contribute approximately half a year of revenue during their activation year.",
    )
    adoption = []
    for year, (column, rate) in enumerate(zip(st.columns(3), rates, strict=True), start=1):
        if timing_year is not None and year < timing_year:
            column.caption(f"Year {year} · Pre-launch")
            adoption.append(rate if demo else None)
            continue
        adoption.append(column.number_input(
            f"Year {year} adoption (%)", min_value=0.0, max_value=100.0, value=rate if demo else None,
            step=1.0, key=f"{key}_adopt_{year}",
        ))

    pricing, margin_col = st.columns(2)
    revenue = pricing.number_input(
        f"Annual revenue per adopter ({currency})", min_value=0.0, max_value=1e12,
        value=price if demo else None, step=100.0, key=f"{key}_price",
    )
    method = margin_col.selectbox(
        "Variable cost input", ["Contribution margin", "Variable cost share"], key=f"{key}_method"
    )
    using_margin = method == "Contribution margin"
    unit_rate = margin_col.number_input(
        f"{method} (%)", min_value=0.0, max_value=100.0,
        value=(margin if using_margin else 100 - margin) if demo else None,
        step=1.0, key=f"{key}_{'margin' if using_margin else 'variable'}",
    )
    recurring, upfront = st.columns(2)
    recurring_cost = recurring.number_input(
        f"Annual fixed operating costs ({currency})", min_value=0.0, max_value=1e12,
        value=fixed if demo else None, step=1_000.0, key=f"{key}_fixed",
    )
    upfront_cost = upfront.number_input(
        f"One-time investment ({currency})", min_value=0.0, max_value=1e12,
        value=investment if demo else None, step=1_000.0, key=f"{key}_investment",
    )
    annual_retention = st.number_input(
        "Annual retention (%)", min_value=0.0, max_value=100.0, value=retention if demo else None,
        step=1.0, key=f"{key}_retention",
    )
    first, second, third = (value if timing_year is None or year >= timing_year else value or 0.0
                            for year, value in enumerate(adoption, 1))
    if (
        population is None or first is None or second is None or third is None or revenue is None
        or unit_rate is None or recurring_cost is None or upfront_cost is None
        or timing_year is None or annual_retention is None
    ):
        return None
    return Assumptions(
        population, (first / 100, second / 100, third / 100), float(revenue),
        unit_rate / 100 if using_margin else 1 - unit_rate / 100,
        float(recurring_cost), float(upfront_cost), timing_year, annual_retention / 100, "Mid-year" if activation == "Mid-year" else "Beginning of year",
    )


def assumption_view(opportunity: Opportunity) -> tuple[dict[str, Assumptions], str, str]:
    st.header("Define assumptions", anchor=False)
    left, right = st.columns(2)
    method = left.radio(
        "Assumption entry", ["Illustrative defaults", "Enter assumptions"],
        horizontal=True, key="financial_input_mode",
    )
    currency = right.selectbox("Currency for all inputs", ("USD", "EUR", "GBP"), key="financial_currency")
    demo = method == "Illustrative defaults"
    origin = (
        "Illustrative financial inputs were offered and may have been edited."
        if demo else "Financial inputs were entered manually."
    )
    if demo and opportunity.fictional_label:
        origin = CASE_ORIGIN + " Inputs may have been edited."
        st.info(origin)
    elif demo:
        st.warning("Illustrative starting values are enabled. They are planning examples, not vendor or customer financial data.")
    else:
        st.caption("Enter all assumptions for each scenario. Use 0 for an intentional zero.")
    st.caption("Currency is a display label. Use the same currency across all scenarios and alternatives.")

    default_population = opportunity.known_eligible if opportunity.known_eligible is not None else (
        (CASE_POPULATION if opportunity.fictional_label else 1_000) if demo else None
    )
    population = st.number_input(
        "Eligible non-adopters", min_value=0, max_value=1_000_000_000, value=default_population,
        step=1, key=f"financial_population_{opportunity.identifier}_{method}_{default_population}",
        help="Count unique customers who are eligible and do not already own the selected product.",
    )
    if opportunity.known_eligible is not None and population == opportunity.known_eligible:
        st.caption("Population matches the validated aggregate from the uploaded portfolio.")
    else:
        st.caption("Population is a modeling assumption. Validate it with a qualified account list.")
    inputs = {}
    tabs = st.tabs(list(SCENARIOS))
    for tab, name in zip(tabs, SCENARIOS, strict=True):
        with tab:
            if (scenario := scenario_inputs(name, opportunity, population, demo, currency)) is not None:
                inputs[name] = scenario
            else:
                st.caption("Complete this scenario and the shared eligible population to calculate results.")
    return inputs, currency, origin


def impact_view(result: Projection, currency: str) -> None:
    headline = (
        ("Eligible non-adopters", f"{result.assumptions.eligible:,}"),
        ("Three-year revenue", money(result.total_revenue, currency)),
        ("Three-year operating contribution", money(result.total_operating, currency)),
        ("Three-year net cash", money(result.ending_cash, currency)),
    )
    for row in batched(headline, 2):
        for column, (label, value) in zip(st.columns(2), row, strict=True):
            column.metric(label, value, border=True)
    st.markdown(f"**Approximate payback from rollout** · {rollout_payback(result)}")
    if result.ending_cash < 0:
        gap = money(abs(result.ending_cash), currency)
        st.markdown(
            f"**Decision implication** · This case ends {gap} short of recovering its costs within three years. "
            "Use the sensitivity comparison to identify which assumptions would need to improve before expanding."
        )
    elif result.payback_months is not None:
        st.markdown(
            f"**Decision implication** · This case recovers its upfront investment and ends with "
            f"{money(result.ending_cash, currency)} in modeled net cash. Validate the cash drivers with pilot evidence "
            "before committing to a wider rollout."
        )
    st.caption("Modeled operating cash excludes taxes, financing, and working capital.")
    st.caption(ROUNDED_COUNTS)
    by_year = annual_rows(result, currency)
    columns = st.columns(3)
    for year, column in enumerate(columns, start=1):
        with column, dashboard_card(f"financial-year-{year}"):
            st.subheader(f"Year {year}", anchor=False)
            for label, *values in by_year:
                st.markdown(f"**{label}**  \n{values[year - 1]}")
    with st.expander("Methodology and formulas"):
        st.markdown(METHODOLOGY)
        st.markdown(FORMULAS)
        st.caption(LIMITATIONS)


def scenario_view(results: dict[str, Projection], currency: str, *, prefix: str = "financial") -> None:
    st.caption("Scenario names identify planning cases. The model assigns no likelihood to any case.")
    for column, name in zip(st.columns(3), SCENARIOS, strict=True):
        with column, dashboard_card(f"{prefix}-scenario-{name}"):
            st.subheader(name, anchor=False)
            result = results.get(name)
            if result is None:
                st.caption("Complete the assumptions for this scenario.")
                continue
            for year in result.years:
                if year.year < result.assumptions.rollout_year:
                    st.caption(f"Year {year.year} · Pre-launch. No revenue, recurring costs, or investment are modeled. Investment is booked at launch.")
                    continue
                st.markdown(
                    f"**Year {year.year}**  \nRevenue {money(year.revenue, currency)}  \n"
                    f"Operating contribution {money(year.operating_contribution, currency)}  \n"
                    f"Cumulative cash {money(year.cumulative_cash, currency)}"
                )
            st.markdown(f"**Approximate payback from rollout**  \n{rollout_payback(result)}")
            with st.expander("Scenario assumptions"):
                for label, value in assumption_lines(result, currency):
                    st.caption(f"{label} · {value}")


def investment_view(
    products: dict[str, Product], opportunity: Opportunity, base: Projection | None, currency: str,
) -> None:
    st.subheader("Investment alternatives", anchor=False)
    if base is None:
        st.info("Complete the Base case to compare product alternatives on a shared three-year basis.")
        return
    st.caption(
        "Alternatives use the Base adoption schedule, rollout year and retention. "
        "Enter each alternative's eligible population. Financial inputs start from Base and can be overridden. "
        "Cases are standalone and should not be added together because customer populations may overlap."
    )
    selected = st.multiselect(
        "Products to compare", tuple(products), default=[opportunity.product_id], max_selections=4,
        format_func=lambda key: (opportunity.fictional_label or products[key].name) if key == opportunity.product_id else products[key].name, key=f"financial_alts_{opportunity.product_id}",
    )
    if len(selected) < 2:
        st.info("Select at least two products to compare investment alternatives.")
        return
    inputs = base.assumptions
    alternatives: dict[str, Projection] = {}
    for row in batched(selected, 2):
        for column, key in zip(st.columns(len(row)), row, strict=True):
            with column, dashboard_card(f"financial-alternative-{key}"):
                label = opportunity.fictional_label if key == opportunity.product_id else None
                st.subheader(label or products[key].name, anchor=False)
                if key == opportunity.product_id:
                    projection = base
                else:
                    eligible = st.number_input(
                        "Assumed eligible non-adopters", min_value=0, max_value=1_000_000_000,
                        value=None, step=1, key=f"financial_alt_pop_{opportunity.identifier}_{key}",
                    )
                    with st.expander("Alternative financial inputs"):
                        revenue = st.number_input(
                            f"Revenue per adopter ({currency})", min_value=0.0, max_value=1e12,
                            value=inputs.revenue_per_adopter, key=f"financial_alt_price_{opportunity.identifier}_{key}",
                        )
                        margin = st.number_input(
                            "Contribution margin (%)", min_value=0.0, max_value=100.0,
                            value=round(inputs.margin * 100, 8), key=f"financial_alt_margin_{opportunity.identifier}_{key}",
                        )
                        fixed = st.number_input(
                            f"Annual fixed costs ({currency})", min_value=0.0, max_value=1e12,
                            value=inputs.fixed_cost, key=f"financial_alt_fixed_{opportunity.identifier}_{key}",
                        )
                        investment = st.number_input(
                            f"One-time investment ({currency})", min_value=0.0, max_value=1e12,
                            value=inputs.investment, key=f"financial_alt_invest_{opportunity.identifier}_{key}",
                        )
                    if eligible is None or revenue is None or margin is None or fixed is None or investment is None:
                        st.caption("Complete the eligible population and financial inputs for this alternative.")
                        continue
                    projection = simulate(replace(
                        inputs, eligible=eligible, revenue_per_adopter=revenue,
                        margin=margin / 100, fixed_cost=fixed, investment=investment,
                    ))
                alternatives[key] = projection
                for label, value in (
                    ("Three-year revenue", money(projection.total_revenue, currency)),
                    ("Contribution margin", f"{projection.assumptions.margin:.1%}"),
                    ("One-time investment", money(projection.assumptions.investment, currency)),
                    ("Three-year net cash", money(projection.ending_cash, currency)),
                    ("Approximate payback from rollout", rollout_payback(projection)),
                ):
                    st.markdown(f"**{label}**  \n{value}")
                fit = CATEGORY_LABELS[PRODUCT_CLASS[key]].lower()
                st.caption(
                    f"Validate {fit} deployment effort, qualified demand, and ongoing support. "
                    "Review cash recovery and investment exposure alongside revenue."
                )

    if len(alternatives) >= 2:
        highest_cash = max(alternatives, key=lambda key: alternatives[key].ending_cash)
        least_capital = min(alternatives, key=lambda key: alternatives[key].assumptions.investment)
        recovered = {
            key: result.payback_months
            for key, result in alternatives.items() if result.payback_months is not None
        }
        with dashboard_card("financial-alternative-tradeoffs"):
            st.subheader("Investment tradeoffs", anchor=False)
            cash = alternatives[highest_cash].ending_cash
            capital = alternatives[least_capital].assumptions.investment
            display_names = {key: (
                (opportunity.fictional_label or products[key].name) if key == opportunity.product_id else products[key].name
            ) for key in alternatives}
            cash_names = ", ".join(display_names[key] for key, result in alternatives.items() if result.ending_cash == cash)
            capital_names = ", ".join(
                display_names[key] for key, result in alternatives.items() if result.assumptions.investment == capital
            )
            st.markdown(f"**Highest modeled three-year net cash** · {cash_names} · {money(cash, currency)}")
            st.markdown(f"**Lowest upfront capital requirement** · {capital_names} · {money(capital, currency)}")
            if recovered:
                fastest = min(recovered.values())
                names = ", ".join(
                    f"{display_names[key]} (Year {alternatives[key].assumptions.rollout_year} launch)"
                    for key, months in recovered.items() if months == fastest
                )
                st.markdown(f"**Shortest approximate payback from rollout** · {names} · {fastest:.0f} months")
            st.caption("Check that each case's commercial inputs and rollout effort are credible before prioritizing capital.")


def sensitivity_chart(items: tuple[Sensitivity, ...], currency: str, *, key: str | None = None) -> None:
    fig = go.Figure()
    labels = [item.driver for item in items]
    for name, changes, color in (
        ("Lower input", [item.low_change for item in items], "#176F9B"),
        ("Higher input", [item.high_change for item in items], "#0D9488"),
    ):
        fig.add_bar(name=name, x=changes, y=labels, orientation="h", marker_color=color,
                    hovertemplate=f"%{{y}} · {currency} %{{x:,.0f}}<extra>{name}</extra>")
    fig.update_layout(
        height=370, barmode="group", margin={"l": 2, "r": 4, "t": 8, "b": 38},
        yaxis={"autorange": "reversed", "automargin": True},
        xaxis={"title": f"Change in three-year net cash ({currency})", "zeroline": True},
        legend={"orientation": "h", "y": -0.25},
    )
    st.plotly_chart(
        fig, width="stretch", key=key, config={"displayModeBar": False},
        alt="Change in three-year net cash as each financial assumption varies",
    )
    if items:
        maximum = round(items[0].absolute_impact, 2)
        leaders = ", ".join(item.driver for item in items if round(item.absolute_impact, 2) == maximum)
        st.caption(f"Largest absolute tested cash impact · {leaders} · {money(maximum, currency)}")
