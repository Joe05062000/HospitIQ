"""Reusable Streamlit components for workspace content."""

import streamlit as st

from ui.catalog import Workspace

OVERVIEW_SCRIPT = "app_pages/executive_overview.py"


def dashboard_card(key: str, *, stretch: bool = False):
    return st.container(key=f"hgi-card-{key}", border=True, height="stretch" if stretch else "content")


def workspace_card(workspace: Workspace) -> None:
    with dashboard_card(workspace.slug, stretch=True):
        st.markdown(f":primary[{workspace.icon}]")
        st.subheader(workspace.title, anchor=False)
        st.markdown(workspace.summary)
        st.page_link(
            workspace.script,
            label=f"Explore {workspace.title}",
            icon=":material/arrow_forward:",
        )


def planned_workspace(workspace: Workspace) -> None:
    st.title(workspace.title, anchor=False)
    st.markdown(workspace.summary)
    st.space("small")

    with dashboard_card(f"preview-{workspace.slug}"):
        st.badge("Planned for a later phase", icon=":material/schedule:")
        st.subheader(workspace.question, anchor=False)
        st.markdown("This workspace is currently a preview of its planned capabilities.")
        st.markdown("\n".join(f"- {capability}" for capability in workspace.capabilities))

    st.page_link(
        OVERVIEW_SCRIPT,
        label="Back to Executive Overview",
        icon=":material/arrow_back:",
    )
