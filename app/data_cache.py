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


@st.cache_data(ttl=_ttl, show_spinner="Loading…")
def _fetch_table_cached_admin(
    table_name: str,
    columns: str,
    limit: int,
    order_by: str | None,
    _session_key: str,
) -> list[dict[str, Any]]:
    """Service-role read for internal roles (Dashboard, etc.); falls back to anon if admin key missing."""
    from db import fetch_table, fetch_table_admin

    try:
        return fetch_table_admin(table_name, columns=columns, limit=limit, order_by=order_by)
    except Exception:
        return fetch_table(table_name, columns=columns, limit=limit, order_by=order_by)


def clear_session_table_cache() -> None:
    """Clear cached list reads (e.g. after **jobs** create/update so dropdowns refresh)."""
    try:
        _fetch_table_cached.clear()
        _fetch_table_cached_admin.clear()
        fetch_table_admin_cached.clear()
        fetch_table_cached.clear()
    except Exception:
        pass


@st.cache_data(ttl=_ttl, show_spinner=False)
def fetch_table_admin_cached(
    table_name: str,
    *,
    columns: str = "*",
    limit: int = 1000,
    order_by: str | None = None,
    cache_version: int = 0,
) -> list[dict[str, Any]]:
    """Cached service-role list read; bump ``cache_version`` after writes."""
    from db import fetch_table_admin

    return fetch_table_admin(table_name, columns=columns, limit=limit, order_by=order_by)


@st.cache_data(ttl=_ttl, show_spinner=False)
def fetch_table_cached(
    table_name: str,
    *,
    columns: str = "*",
    limit: int = 1000,
    order_by: str | None = None,
    cache_version: int = 0,
) -> list[dict[str, Any]]:
    """Cached anon/RLS list read; bump ``cache_version`` after writes."""
    from db import fetch_table

    return fetch_table(table_name, columns=columns, limit=limit, order_by=order_by)


def fetch_table_for_session(
    table_name: str,
    *,
    session_key: str,
    columns: str = "*",
    limit: int = 1000,
    order_by: str | None = None,
    use_admin: bool = False,
) -> list[dict[str, Any]]:
    """
    Read-through cache for list reads; pass ``session_key=`` current user id (str).

    Set ``use_admin=True`` for admin/estimator so rows hidden by RLS (e.g. ``jobs``, ``estimates``)
    still appear on the Dashboard.
    """
    cache_key = f"{session_key}:svc" if use_admin else session_key
    if use_admin:
        return _fetch_table_cached_admin(table_name, columns, limit, order_by, cache_key)
    return _fetch_table_cached(table_name, columns, limit, order_by, cache_key)
