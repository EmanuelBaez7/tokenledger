"""Session-scoped caching; credential values never participate in cache hashing."""

from datetime import date

import streamlit as st

from dashboard.analytics import Period
from dashboard.snapshots import ReportSnapshot, Source, SourceConfig, load_report


@st.cache_data(ttl=60, max_entries=8, show_spinner=False, scope="session")
def cached_report(
    source: Source, period: Period, today: date, base_url: str, *, _api_key: str
) -> ReportSnapshot:
    return load_report(source, period, today=today, base_url=base_url, api_key=_api_key)


def load_cached_report(
    source: Source, period: Period, *, today: date, config: SourceConfig
) -> ReportSnapshot:
    previous = st.session_state.get("_tl_credentials")
    if previous != config:
        cached_report.clear()
        st.session_state["_tl_credentials"] = config
    return cached_report(
        source, period, today, config.base_url, _api_key=config.api_key
    )


def clear_report_cache() -> None:
    cached_report.clear()
