"""Shared provenance for the bundled research snapshot."""

from datetime import UTC

import streamlit as st

from data_services.market_catalog import MarketCatalog
from strategy_models.benchmark import eligible_companies


def research_snapshot(catalog: MarketCatalog) -> None:
    reviews = [source.verified_at for source in catalog.sources.values() if source.verified_at]
    formatted = max(reviews).astimezone(UTC).strftime("%B %d, %Y").replace(" 0", " ") if reviews else None
    label = f"Research snapshot as of {formatted}" if formatted else "Research snapshot · Review date unavailable"
    vendors = len(eligible_companies(catalog))
    announcements = len(catalog.filter_developments(verified_only=True))
    st.markdown(f"**{label} · {vendors} verified vendors · {announcements} verified announcements**")
    st.caption(
        "Date reflects the latest verified source review (UTC). Coverage is curated and refreshed manually. "
        "Source gaps and reported rollout status may limit comparisons."
    )
