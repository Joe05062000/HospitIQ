"""Guided three-minute strategy demonstration with a downloadable briefing."""

import streamlit as st

from brand import CASE_STUDY_TITLE
from data_services.market_catalog import load_catalog
from strategy_models.advisor import (
    FINANCIAL_BRIEF_KEY,
    GROWTH_BRIEF_KEY,
    FinancialSnapshot,
)
from strategy_models.executive_case import (
    BUSINESS_RANGES,
    CASE_LIMIT,
    COMPANY,
    CONSERVATIVE_TIMING,
    CURRENCY,
    CUSTOMER_BASE,
    MILESTONES,
    ORIGIN,
    POPULATION,
    QUESTION,
    RECOMMENDATION,
    RISK_CONTEXT,
    RISKS,
    STRESS,
    build_case,
    case_opportunity,
    sensitivity_takeaways,
)
from strategy_models.executive_case_report import case_report
from strategy_models.financial_report import money, rollout_payback
from ui.components import dashboard_card
from ui.financial import scenario_view, sensitivity_chart
from ui.market_intelligence import source_link

st.title(CASE_STUDY_TITLE, anchor=False)
st.markdown(f"**{COMPANY}** · A fictional hospitality technology vendor evaluating embedded payments.")
try:
    catalog = load_catalog()
except (OSError, ValueError):
    st.error("The research snapshot is unavailable. Validate the local catalog and reload the case.")
    st.stop()

case = build_case(catalog)
with dashboard_card("case-summary"):
    st.subheader("Decision · Pilot payments before scaling", anchor=False)
    st.markdown(RECOMMENDATION)
    st.caption("Fictional model inputs and outcomes. Verified vendor evidence appears in the research section.")
    for column, (name, projection) in zip(st.columns(3), case.results.items(), strict=True):
        with column:
            sign = "−" if projection.ending_cash < 0 else ""
            st.metric(f"{name} · 3-year net cash", f"{sign}{CURRENCY} {abs(projection.ending_cash) / 1e6:.2f}M")
            st.caption(f"Approximate payback from rollout · {rollout_payback(projection)}")
    st.caption(CASE_LIMIT)
    st.caption("Key uncertainties · Adoption, willingness to pay, margin and rollout readiness.")
    st.download_button(
        "Download Harborlight Case Study briefing", case_report(catalog, case),
        "hospitiq-executive-case-briefing.html", "text/html", icon=":material/download:", on_click="ignore",
    )

challenge, evidence, financial, delivery = st.tabs(
    ["Business challenge", "Evidence and growth", "Financial scenarios", "Recommendation and plan"]
)
with challenge:
    st.header("Business challenge", anchor=False)
    with dashboard_card("case-challenge"):
        st.markdown(QUESTION)
        st.markdown(
            f"Harborlight has **{CUSTOMER_BASE:,} fictional customers** and assumes **{POPULATION:,} distinct "
            "eligible non-adopters**. The case tests whether an embedded payments offer can generate enough "
            "incremental contribution to recover the investment."
        )
        st.caption("Read Evidence and growth next to compare the case hypothesis with documented industry activity.")

with evidence:
    st.header("Verified market evidence", anchor=False)
    if not case.developments:
        st.info("There are no reviewed announcements matching the case evidence selection.")
    for item in case.developments:
        with st.expander(item.title):
            st.markdown(item.summary)
            source_link(catalog.sources[item.source_id], publication=True)
            st.caption(item.limitations)
    st.page_link("app_pages/market_intelligence.py", label="Explore verified market announcements")
    st.header("Competitive considerations", anchor=False)
    st.caption("Real companies are industry evidence. They have no stated relationship to fictional Harborlight.")
    if not case.payments_evidence:
        st.info("The reviewed catalog has insufficient evidence for the selected comparison.")
    for vendor, items in case.payments_evidence:
        with dashboard_card(f"case-vendor-{vendor.replace(' ', '-')}"):
            st.subheader(vendor, anchor=False)
            for entry in items:
                st.markdown(entry.text)
                st.caption(" · ".join(f"[{source.title}](<{source.url}>)" for source in entry.sources))
    st.page_link("app_pages/competitive_benchmarking.py", label="Compare documented vendor capabilities")
    st.header("Product growth opportunity", anchor=False)
    if case.complementarity:
        st.markdown(case.complementarity.rationale)
        st.markdown(f"**Validate first** · {case.complementarity.execution}")
    st.caption("This is a commercial hypothesis for the fictional company. Vendor evidence does not establish its technical integration.")
    st.page_link("app_pages/product_growth_intelligence.py", label="Explore product combinations and eligibility")

with financial:
    st.header("Financial scenarios and sensitivities", anchor=False)
    st.caption(ORIGIN)
    st.caption(CONSERVATIVE_TIMING)
    scenario_view(case.results, CURRENCY)
    st.subheader("What could change the pilot decision?", anchor=False)
    normalized_takeaway, uncertainty_takeaway = sensitivity_takeaways(case)
    st.markdown(f"**Equal relative shocks** · {normalized_takeaway}")
    st.markdown(f"**Assumed business ranges** · {uncertainty_takeaway}")
    st.caption(
        f"Normalized comparison · All six assumptions move ±{STRESS:.0%} relative, one at a time."
    )
    with dashboard_card("case-sensitivity"):
        sensitivity_chart(case.sensitivities, CURRENCY, key="case-normalized")
    with st.expander("Assumed business uncertainty"):
        st.caption(RISK_CONTEXT)
        for label, (lower, upper) in BUSINESS_RANGES.items():
            st.caption(f"{label} · {lower:+.0%} to {upper:+.0%} relative")
        sensitivity_chart(case.uncertainty, CURRENCY, key="case-uncertainty")
    with st.expander("Compare all scenarios with Year 1 launch"):
        st.caption(
            "Commercial assumptions are held fixed within each case. Conservative adds an explicitly assumed "
            "12% Year 1 adoption rate when launched in Year 1. Weaker pricing and margin are a separate downside."
        )
        for name, projection in case.aligned.items():
            st.markdown(f"**{name}** · {money(projection.ending_cash, CURRENCY)} three-year cash")
    if case_opportunity(catalog) and st.button("Open case in Financial Scenario Simulator", icon=":material/calculate:"):
        st.session_state["financial_case_requested"] = True
        st.session_state["financial_input_mode"] = "Illustrative defaults"
        st.session_state["financial_currency"] = CURRENCY
        st.session_state["financial_opportunity_mode"] = CASE_STUDY_TITLE
        st.switch_page("app_pages/financial_scenario_simulator.py")

with delivery:
    st.header("Recommendation and 90-day action plan", anchor=False)
    st.markdown(RECOMMENDATION)
    st.caption("Use the pilot to measure economics and implementation before committing to rollout.")
    with st.expander("Key risks", expanded=True):
        st.markdown("\n".join(f"- {risk}" for risk in RISKS))
    for index, (title, action, gate) in enumerate(MILESTONES):
        with dashboard_card(f"case-milestone-{index}"):
            st.subheader(title, anchor=False)
            st.markdown(action)
            st.caption(f"Decision checkpoint · {gate}")
    if st.button("Discuss the decision in Strategy Advisor", icon=":material/assignment:"):
        if opportunity := case_opportunity(catalog):
            st.session_state[FINANCIAL_BRIEF_KEY] = FinancialSnapshot(
                opportunity.product_id, opportunity.segment, CURRENCY, ORIGIN,
                tuple(case.results.items()), opportunity.fictional_label,
            )
            st.session_state["advisor_segment"] = opportunity.segment
        st.session_state.pop(GROWTH_BRIEF_KEY, None)
        st.session_state["advisor_question"] = "investment"
        st.session_state["advisor_companies"] = [key for key in ("oracle", "mews") if key in catalog.companies]
        st.session_state["advisor_theme"] = "payments"
        st.session_state["advisor_mode"] = "Evidence-Based Mode"
        st.switch_page("app_pages/ai_strategy_advisor.py")
