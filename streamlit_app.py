"""Application entry point and shared navigation."""

import streamlit as st

from brand import CASE_STUDY_TITLE, PRODUCT_NAME
from ui.catalog import WORKSPACES
from ui.components import OVERVIEW_SCRIPT
from ui.shell import enterprise_header

st.set_page_config(
    page_title=PRODUCT_NAME,
    page_icon=":material/domain:",
    layout="wide",
    initial_sidebar_state="auto",
)

current_page = st.navigation(
    {
        "Strategy workspace": [
            st.Page(
                OVERVIEW_SCRIPT,
                title="Executive Overview",
                icon=":material/dashboard:",
                default=True,
            ),
            *[
                st.Page(
                    workspace.script,
                    title=workspace.title,
                    icon=workspace.icon,
                    url_path=workspace.slug,
                )
                for workspace in WORKSPACES
            ],
        ],
        "Practical demonstration": [
            st.Page(
                "app_pages/executive_case_study.py",
                title=CASE_STUDY_TITLE,
                icon=":material/route:",
                url_path="executive-case-study",
            ),
        ],
    },
    expanded=True,
)

st.set_page_config(page_title=f"{current_page.title} · {PRODUCT_NAME}")

with st.sidebar:
    st.markdown(f"**{PRODUCT_NAME}**")

enterprise_header(current_page.title)
current_page.run()
