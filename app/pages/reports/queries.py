"""
Cached database query functions for the Reports module.
All functions are read-only and safe to cache with @st.cache_data.
Cache is keyed by relevant filter parameters to avoid stale data.
"""
from __future__ import annotations

from datetime import date
from typing import Any

import streamlit as st


def _db():
    try:
        from app.db import fetch_table, fetch_table_admin
    except ImportError:
        from db import fetch_table, fetch_table_admin  # type: ignore
    return fetch_table, fetch_table_admin


@st.cache_data(ttl=120, show_spinner=False)
def fetch_jobs(*, admin: bool = True) -> list[dict[str, Any]]:
    _, fetch_admin = _db()
    fetch, _ = _db()
    try:
        rows = fetch_admin("jobs", limit=5000, order_by="job_number") if admin else fetch("jobs", limit=5000, order_by="job_number")
        return [r for r in (rows or []) if r.get("id")]
    except Exception:
        try:
            fetch_fn, _ = _db()
            rows = fetch_fn("jobs", limit=5000, order_by="job_number")
            return [r for r in (rows or []) if r.get("id")]
        except Exception:
            return []


@st.cache_data(ttl=120, show_spinner=False)
def fetch_estimates(*, admin: bool = True) -> list[dict[str, Any]]:
    fetch, fetch_admin = _db()
    try:
        rows = fetch_admin("estimates", limit=5000, order_by="quote_number") if admin else fetch("estimates", limit=5000, order_by="quote_number")
        return list(rows or [])
    except Exception:
        return []


@st.cache_data(ttl=120, show_spinner=False)
def fetch_employees(*, admin: bool = False) -> list[dict[str, Any]]:
    fetch, fetch_admin = _db()
    try:
        rows = fetch("employees", limit=5000, order_by="name")
        return [r for r in (rows or []) if r.get("id")]
    except Exception:
        return []


@st.cache_data(ttl=60, show_spinner=False)
def fetch_time_entries(*, date_start: date | None = None, date_end: date | None = None, admin: bool = True) -> list[dict[str, Any]]:
    """Fetch time_entries with optional date filter applied in-Python (Supabase free tier has limited query params)."""
    fetch, fetch_admin = _db()
    try:
        fn = fetch_admin if admin else fetch
        for ob in ("work_date", None):
            try:
                rows = fn("time_entries", limit=50000, order_by=ob) if ob else fn("time_entries", limit=50000)
                rows = list(rows or [])
                break
            except Exception:
                rows = []
    except Exception:
        rows = []
    if not rows:
        return []
    if date_start is not None:
        rows = [r for r in rows if str(r.get("work_date", ""))[:10] >= date_start.isoformat()]
    if date_end is not None:
        rows = [r for r in rows if str(r.get("work_date", ""))[:10] <= date_end.isoformat()]
    return rows


@st.cache_data(ttl=120, show_spinner=False)
def fetch_job_materials(*, admin: bool = True) -> list[dict[str, Any]]:
    fetch, fetch_admin = _db()
    try:
        fn = fetch_admin if admin else fetch
        rows = fn("job_materials", limit=50000, order_by="created_at")
        return list(rows or [])
    except Exception:
        return []


@st.cache_data(ttl=120, show_spinner=False)
def fetch_job_equipment(*, admin: bool = True) -> list[dict[str, Any]]:
    fetch, fetch_admin = _db()
    try:
        fn = fetch_admin if admin else fetch
        rows = fn("job_equipment", limit=50000, order_by="created_at")
        return list(rows or [])
    except Exception:
        return []


@st.cache_data(ttl=120, show_spinner=False)
def fetch_inventory_items(*, admin: bool = True) -> list[dict[str, Any]]:
    fetch, fetch_admin = _db()
    try:
        fn = fetch_admin if admin else fetch
        rows = fn("inventory_items", limit=8000, order_by="item_name")
        return [r for r in (rows or []) if r.get("id")]
    except Exception:
        return []


@st.cache_data(ttl=60, show_spinner=False)
def fetch_inventory_transactions(*, date_start: date | None = None, date_end: date | None = None, admin: bool = True) -> list[dict[str, Any]]:
    fetch, fetch_admin = _db()
    try:
        fn = fetch_admin if admin else fetch
        rows = fn("inventory_transactions", limit=15000, order_by="created_at")
        rows = list(rows or [])
    except Exception:
        rows = []
    if not rows:
        return []
    if date_start is not None:
        rows = [r for r in rows if str(r.get("created_at", ""))[:10] >= date_start.isoformat()]
    if date_end is not None:
        rows = [r for r in rows if str(r.get("created_at", ""))[:10] <= date_end.isoformat()]
    return rows


@st.cache_data(ttl=120, show_spinner=False)
def fetch_assets(*, admin: bool = True) -> list[dict[str, Any]]:
    fetch, fetch_admin = _db()
    try:
        fn = fetch_admin if admin else fetch
        rows = fn("assets", limit=5000, order_by="asset_name")
        return [r for r in (rows or []) if r.get("id")]
    except Exception:
        return []


@st.cache_data(ttl=120, show_spinner=False)
def fetch_asset_assignments(*, admin: bool = True) -> list[dict[str, Any]]:
    fetch, fetch_admin = _db()
    try:
        fn = fetch_admin if admin else fetch
        rows = fn("asset_assignments", limit=10000, order_by="assigned_date")
        return list(rows or [])
    except Exception:
        return []


@st.cache_data(ttl=120, show_spinner=False)
def fetch_labor_rates(*, admin: bool = False) -> list[dict[str, Any]]:
    fetch, _ = _db()
    try:
        rows = fetch("labor_rates", limit=5000, order_by="classification")
        return [r for r in (rows or []) if r.get("id")]
    except Exception:
        return []
