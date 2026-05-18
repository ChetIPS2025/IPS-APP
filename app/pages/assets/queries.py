"""Database read helpers for the Assets module.

The underlying db.py layer already caches reads with @st.cache_data(ttl=30)
and clears after writes via clear_streamlit_db_read_cache().  These wrappers
provide a clean API surface and a module-level @st.cache_data layer for the
prepared DataFrame used across the Assets pages.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

try:
    from app.db import fetch_one, fetch_table
    from app.services.job_service import job_row_select_label, sort_jobs_by_number_then_name
except ImportError:
    from db import fetch_one, fetch_table  # type: ignore
    from services.job_service import job_row_select_label, sort_jobs_by_number_then_name  # type: ignore


# ---------------------------------------------------------------------------
# Raw row fetchers (delegate to db.py cache)
# ---------------------------------------------------------------------------

def get_assets(limit: int = 5000) -> list[dict]:
    """Return all asset rows ordered by name."""
    return fetch_table("assets", limit=limit, order_by="asset_name")


def get_jobs(limit: int = 5000) -> list[dict]:
    """Return all job rows sorted by number then name."""
    raw = fetch_table("jobs", limit=limit, order_by="job_number")
    return sort_jobs_by_number_then_name(raw)


def get_employees(limit: int = 4000) -> list[dict]:
    """Return id + name for all employees."""
    try:
        return fetch_table("employees", columns="id,name", limit=limit, order_by="name")
    except Exception:
        return []


def get_asset_by_id(row_id: str) -> dict | None:
    """Fetch a single asset row by its UUID primary key."""
    return fetch_one("assets", {"id": str(row_id)})


# ---------------------------------------------------------------------------
# Derived helpers
# ---------------------------------------------------------------------------

def build_job_label_by_id(jobs: list[dict]) -> dict[str, str]:
    """Map job UUID → display label string."""
    return {
        str(j.get("id")): job_row_select_label(j)
        for j in jobs
        if j.get("id")
    }


def build_job_options(jobs: list[dict]) -> dict[str, str | None]:
    """Map display label → job UUID (for selectbox → DB save round-trip)."""
    return {
        job_row_select_label(j): j.get("id")
        for j in jobs
        if job_row_select_label(j) and job_row_select_label(j) != "—"
    }


def build_emp_by_id(employees: list[dict]) -> dict[str, str]:
    """Map employee UUID → name string."""
    return {
        str(e["id"]): str(e.get("name") or "").strip()
        for e in employees
        if e.get("id")
    }


# ---------------------------------------------------------------------------
# Prepared DataFrame
# ---------------------------------------------------------------------------

_ASSET_TABLE_COLS = [
    "asset_id",
    "asset_name",
    "manufacturer",
    "model",
    "serial_number",
    "status",
    "category",
    "qr_code_value",
]


def prepare_assets_dataframe(rows: list[dict]) -> pd.DataFrame:
    """Normalise columns; ensure boolean flag columns exist."""
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    for col in _ASSET_TABLE_COLS:
        if col not in df.columns:
            df[col] = pd.NA
    for col in ("photo_path", "is_rental", "is_checkout_item",
                "current_holder_employee_id", "last_checkout_at",
                "last_checkin_at", "assigned_job_id", "assigned_employee"):
        if col not in df.columns:
            df[col] = pd.NA if col not in ("is_rental", "is_checkout_item") else False
    return df
