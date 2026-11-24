"""Executive strategy advisor with offline and NVIDIA-assisted modes."""

from time import monotonic

import streamlit as st

from data_services.market_catalog import load_catalog
from data_services.nvidia_advisor import (
    NvidiaError,
    load_settings,
    request_priorities,
    trial_enabled,
)
from strategy_models.advisor import (
    FINANCIAL_BRIEF_KEY,
    GROWTH_BRIEF_KEY,
    QUESTIONS,
    GrowthContext,
    build_public_brief,
    matching_snapshot,
)
from strategy_models.advisor_report import executive_html
from strategy_models.benchmark import eligible_companies
from strategy_models.decision_policy import Criteria, evaluate_decision
from strategy_models.growth_research import SEGMENTS
from ui.advisor import (
    decision_details,
    decision_view,
    evidence_limitations,
    executive_agenda,
    local_financial_view,
    management_criteria,
)

st.title("Strategy Advisor", anchor=False)
st.markdown("Choose a question and the companies you want to assess. The Advisor explains what to do next and what evidence could change that advice.")

try:
    catalog = load_catalog()
except (OSError, ValueError):
    st.error("The research snapshot could not be loaded. Validate the catalog and reload this page.")
    st.stop()

companies = eligible_companies(catalog)
if not companies:
    st.info("The advisor requires a verified company profile.")
    st.stop()

enabled = trial_enabled()
left, right = st.columns(2)
question = left.selectbox(
    "Decision question", tuple(QUESTIONS), format_func=QUESTIONS.__getitem__, key="advisor_question",
    help="Use the investment question to screen a modeled opportunity against management’s limits.",
)
mode = right.radio(
    "Advisor mode", ["Evidence-Based Mode", "NVIDIA-assisted"] if enabled else ["Evidence-Based Mode"],
    horizontal=True, key="advisor_mode"
)
chosen = st.multiselect(
    "Companies", companies, default=None if "advisor_companies" in st.session_state else companies[:2], max_selections=4,
    format_func=lambda key: catalog.companies[key].name, key="advisor_companies",
    help="Select at least one company. Differentiation requires a documented comparison between two or more.",

)
left, right = st.columns(2)
segment = left.selectbox(
    "Hypothetical customer segment", tuple(SEGMENTS), format_func=lambda key: SEGMENTS[key].label,
    key="advisor_segment",
)
theme = right.selectbox(
    "Market announcement theme (optional)", (None, *catalog.themes),
    format_func=lambda key: catalog.themes[key] if key else "All verified themes", key="advisor_theme",
    help="Filter market announcements by theme. Other analysis uses the selected vendors and customer segment.",
)
if not chosen:
    st.info("Select at least one company to assemble a brief.")
    st.stop()

context = st.session_state.get(GROWTH_BRIEF_KEY)
if not isinstance(context, GrowthContext) or context.company_id not in chosen or context.segment != segment:
    context = None
snapshot = matching_snapshot(catalog, st.session_state.get(FINANCIAL_BRIEF_KEY), tuple(chosen), segment)
case_focus = snapshot.product_id if snapshot and snapshot.fictional_label else None
# A real saved opportunity can focus a local evidence agenda. It stays out of external requests.
local_focus = snapshot.product_id if snapshot and question == "investment" else None
brief = build_public_brief(catalog, question, tuple(chosen), segment, theme, context, case_focus or local_focus)
if context:
    st.caption("Using the product selection and scoring weights carried over from Product Growth.")
elif case_focus and question == "investment":
    st.caption("Harborlight is fictional. Vendor research provides context for the payments decision.")
if question in {"growth", "cross-sell"} and len(chosen) > 1:
    st.caption(
        "The Advisor compares the selected vendors. To match a single-vendor Product Growth view, select that vendor here."
    )

recommendation = st.container()
if question == "investment":
    criteria = management_criteria(snapshot, brief.opportunity.title if brief.opportunity else "Unspecified opportunity")
else:
    criteria = Criteria(objective="Discovery")
decision = evaluate_decision(brief, snapshot, criteria)
with recommendation:
    decision_view(decision)
decision_details(decision)

if not brief.priority_order():
    limitation = {
        "competition": "Select two or more vendors with a documented comparison. A capability gap alone cannot establish differentiation.",
        "tradeoff": "Select Oracle Hospitality and Mews to compare the documented payments and front-desk automation examples.",
        "market": "No verified developments match these filters. Change the companies or broaden the market theme.",
    }.get(question, "The selected products and companies do not provide enough verified evidence for this decision.")
    st.info(limitation)
    if snapshot or question != "investment":
        local_financial_view(catalog, snapshot)
    st.stop()

ranking = brief.priority_order()
method = "Evidence-Based Mode · Local ranking rules"
if enabled and mode == "NVIDIA-assisted" and (not local_focus or case_focus):
    st.caption("Optional ordering of public diligence findings. The local recommendation and gates remain authoritative.")
    st.caption(
        "NVIDIA receives the selected research filters and curated public findings. "
        "Financial assumptions, simulator results, portfolio uploads, and customer information stay local."
    )
    requested = st.button("Prioritize with NVIDIA", key="advisor_nvidia_run", type="primary")
    attempts = st.session_state.get("advisor_trial_attempts", 0)
    if requested and attempts >= 5:
        st.warning("The private trial limit for this session has been reached. The local agenda is available.")
    elif requested and monotonic() - st.session_state.get("advisor_trial_last_request", -60) < 3:
        st.info("Wait a few seconds between NVIDIA requests. The local agenda is available.")
    elif requested:
        st.session_state.pop("advisor_nvidia_result", None)
        try:
            config = load_settings()
            st.session_state["advisor_trial_attempts"] = attempts + 1
            st.session_state["advisor_trial_last_request"] = monotonic()
            with st.spinner("Reviewing the public decision agenda with NVIDIA…"):
                ranked = brief.align_priorities(request_priorities(brief, config))
            st.session_state["advisor_nvidia_result"] = (brief, ranked)
        except NvidiaError as exc:
            st.warning(f"{exc} Showing the local Evidence-Based agenda.")
    response = st.session_state.get("advisor_nvidia_result")
    if response and response[0] == brief:
        ranking = response[1]
        method = "NVIDIA-assisted · Nemotron 3 Ultra 550B ranked public diligence findings."
    else:
        st.caption("The local agenda is available whenever NVIDIA prioritization has not run for this selection.")

elif enabled and mode == "NVIDIA-assisted":
    st.caption("This opportunity uses the local simulator handoff. Its decision and supporting agenda stay local.")

with st.expander("Detailed research and sources"):
    executive_agenda(brief, ranking, method)
if snapshot or question != "investment":
    local_financial_view(catalog, snapshot)
evidence_limitations()
st.download_button(
    "Download executive strategy brief", executive_html(catalog, brief, ranking, method, snapshot, decision),
    "hospitiq-executive-strategy-brief.html", "text/html", icon=":material/download:", on_click="ignore",
)
