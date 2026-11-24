"""Interactive three-year financial scenario workspace."""

import streamlit as st

from data_services.market_catalog import load_catalog
from strategy_models.advisor import FINANCIAL_BRIEF_KEY, FinancialSnapshot
from strategy_models.executive_case import BUSINESS_RANGES, case_opportunity
from strategy_models.financial import (
    SCENARIOS,
    AssumptionError,
    aligned_launch,
    business_uncertainty,
    compare_scenarios,
    sensitivity,
    simulate,
)
from strategy_models.financial_report import briefing_html, money, rollout_payback
from strategy_models.financial_transfer import HANDOFF_KEY, validated_handoff
from strategy_models.growth_research import PRODUCT_CLASS
from ui.components import dashboard_card
from ui.financial import (
    assumption_view,
    impact_view,
    investment_view,
    opportunity_selector,
    scenario_view,
    sensitivity_chart,
)

st.title("Financial Scenario Simulator", anchor=False)
st.markdown("Model a cross-sell opportunity, compare investment alternatives, and test the assumptions that drive cash recovery.")

try:
    catalog = load_catalog()
except (OSError, ValueError):
    st.error("The research snapshot could not be loaded. Validate the catalog and reload this page.")
    st.stop()

products = {
    key: product for key, product in catalog.products.items()
    if key in PRODUCT_CLASS and catalog.evidence_status(product.source_ids) == "verified"
}
if not products:
    st.info("The simulator requires at least one verified product in the research catalog.")
    st.stop()
opportunity = opportunity_selector(
    catalog, products, validated_handoff(catalog, st.session_state.get(HANDOFF_KEY)),
    case_opportunity(catalog) if st.session_state.get("financial_case_requested") else None,
)

assumptions_tab, impact_tab, compare_tab, sensitivity_tab, brief_tab = st.tabs([
    "Assumptions", "Financial impact", "Compare scenarios", "Sensitivity", "Executive brief",
])
with assumptions_tab:
    assumptions, currency, origin = assumption_view(opportunity)
try:
    results = compare_scenarios(assumptions) if len(assumptions) == len(SCENARIOS) else {
        name: simulate(value) for name, value in assumptions.items()
    }
except AssumptionError as exc:
    st.error(str(exc))
    results = {}

with impact_tab:
    st.header("Review financial impact", anchor=False)
    if not results:
        st.info("Complete at least one scenario to see its three-year projection.")
    else:
        focus = st.selectbox(
            "Scenario to review", tuple(results), index=tuple(results).index("Base") if "Base" in results else 0,
            key="financial_focus",
        )
        st.caption(origin)
        impact_view(results[focus], currency)

aligned_results = {}
with compare_tab:
    st.header("Compare scenarios", anchor=False)
    scenario_view(results, currency)
    if len(assumptions) == len(SCENARIOS):
        common_year = max(item.rollout_year for item in assumptions.values())
        with st.expander(f"Compare a common Year {common_year} launch"):
            st.caption("All cases use the latest selected launch year and keep their own calendar-year commercial inputs.")
            aligned_results = aligned_launch(assumptions, common_year)
            scenario_view(aligned_results, currency, prefix="aligned")
    investment_view(products, opportunity, results.get("Base"), currency)

with sensitivity_tab:
    st.header("Evaluate sensitivities", anchor=False)
    if results:
        selected_case = st.selectbox(
            "Sensitivity scenario", tuple(results), index=tuple(results).index("Base") if "Base" in results else 0,
            key="financial_sensitivity_case",
        )
        step = st.slider("Sensitivity variation", 5, 50, 10, step=5, key="financial_sensitivity_step") / 100
        st.caption(
            f"Normalized analysis · Each driver changes ±{step:.0%} relative, one at a time. Rates stay within 0% to 100%."
        )
        sensitivities = sensitivity(results[selected_case].assumptions, step)
        with dashboard_card("financial-sensitivity-chart"):
            sensitivity_chart(sensitivities, currency)
        with st.expander("Separate business uncertainty analysis"):
            st.caption("Enter assumed relative bounds. Practical risk also depends on uncertainty and controllability.")
            ranges = {}
            for driver, (lo, hi) in BUSINESS_RANGES.items():
                lower, upper = st.slider(
                    driver, -100, 100, (int(lo * 100), int(hi * 100)), key=f"financial_risk_{driver}",
                )
                if lower > 0 or upper < 0:
                    st.warning(f"{driver} range must include the Base input (0%).")
                else:
                    ranges[driver] = (lower / 100, upper / 100)
            uncertainty = business_uncertainty(results[selected_case].assumptions, ranges)
            if uncertainty:
                sensitivity_chart(uncertainty, currency, key="simulator-uncertainty")
        with st.expander("Sensitivity values"):
            for item in sensitivities:
                st.markdown(
                    f"**{item.driver}**  \n"
                    f"Lower input {money(item.low_change, currency)} · Higher input {money(item.high_change, currency)}"
                )
    else:
        st.info("Complete a scenario to test how individual assumptions affect cash contribution.")

with brief_tab:
    st.header("Generate executive brief", anchor=False)
    if results and st.button("Open results in Strategy Advisor", key="financial_share_advisor"):
        st.session_state[FINANCIAL_BRIEF_KEY] = FinancialSnapshot(
            opportunity.product_id, opportunity.segment, currency, origin, tuple(results.items()),
            opportunity.fictional_label,
        )
        st.session_state["advisor_companies"] = [products[opportunity.product_id].company_id]
        if opportunity.segment is not None:
            st.session_state["advisor_segment"] = opportunity.segment
        st.switch_page("app_pages/ai_strategy_advisor.py")
    if len(results) == len(SCENARIOS):
        with dashboard_card("financial-brief-summary"):
            label = opportunity.fictional_label or products[opportunity.product_id].name
            st.subheader(f"{label} · {selected_case}", anchor=False)
            st.markdown(
                f"Three-year revenue of **{money(results[selected_case].total_revenue, currency)}** "
                f"and cumulative net cash of **{money(results[selected_case].ending_cash, currency)}**."
            )
            st.caption(f"Approximate payback from rollout · {rollout_payback(results[selected_case])}")
            st.markdown(
                "Validate the eligible population, unit economics, rollout readiness, and retention "
                "with a qualified pilot before committing further investment."
            )
        st.caption("The brief uses the scenario selected under Sensitivity and includes all three cases.")
        st.download_button(
            "Download executive financial brief",
            briefing_html(
                catalog, opportunity, results, selected_case, sensitivities, currency, origin, step,
                uncertainty=uncertainty, ranges=ranges, aligned=aligned_results,
            ),
            "hospitiq-executive-financial-brief.html", "text/html", icon=":material/download:", on_click="ignore",
        )
    else:
        st.info("Complete Conservative, Base, and Ambitious assumptions to generate the full briefing.")
