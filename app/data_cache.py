from __future__ import annotations

from typing import Any

import streamlit as st

try:
    from config import settings
except ImportError:
    from app.config import settings  # type: ignore

_ttl = max(30, int(settings.reference_cache_ttl_seconds))


@st.cache_data(ttl=_ttl, show_spinner="Loading…")
def _fetch_table_cached(
    table_name: str,
    columns: str,
    limit: int,
    order_by: str | None,
    _session_key: str,
) -> list[dict[str, Any]]:
    """Cache key includes _session_key so RLS-scoped reads are not shared across users."""
    from db import fetch_table

    return fetch_table(table_name, columns=columns, limit=limit, order_by=order_by)


def fetch_table_for_session(
    table_name: str,
    *,
    session_key: str,
    columns: str = "*",
    limit: int = 1000,
    order_by: str | None = None,
) -> list[dict[str, Any]]:
    """Read-through cache for list reads; pass session_key=current user id (str)."""
    return _fetch_table_cached(table_name, columns, limit, order_by, session_key)
