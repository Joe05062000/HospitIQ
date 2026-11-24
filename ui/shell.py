"""Shared enterprise header and visual system."""

from html import escape
from pathlib import Path

import streamlit as st

from brand import PRODUCT_DESCRIPTOR, PRODUCT_NAME

ASSETS = Path(__file__).parent / "assets"


def enterprise_header(page_title: str) -> None:
    st.html(ASSETS / "dashboard.css")
    st.html(ASSETS / "matrix.css")
    st.html(
        '<div class="hgi-header" role="banner">'
        f'<strong>{escape(PRODUCT_NAME)}</strong>'
        f'<span class="hgi-descriptor">{escape(PRODUCT_DESCRIPTOR)}</span>'
        f'<span class="hgi-page-context">{escape(page_title)}</span>'
        '</div>'
    )
