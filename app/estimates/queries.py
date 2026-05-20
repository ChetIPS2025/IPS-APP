"""Read-only DB queries for the Estimating module.

All public functions are import-path-agnostic (work from app/ root or package root).
Heavy read-only fetches are wrapped in @st.cache_data so repeated calls within
the same session rerun do not hit the database.

Cache invalidation
------------------
The estimates-list cache key includes ``est_data_version`` from session state.
Call ``services.bump_estimates_cache()`` after any create / edit / delete / approve
action to ensure the next list render picks up fresh data.

Single-row reads (fetch_estimate_by_id) use a short TTL (30 s) so the activity
panel in the editor does not stale-read an old row but also does not DB-hit on
every widget interaction rerun.
"""
from __future__ import annotations

from typing import Any

import streamlit as st

try:
    from auth import current_role
    from db import (
        fetch_by_match_admin,
        fetch_one,
        fetch_table,
        fetch_table_admin,
    )
except ImportError:
    from app.auth import current_role  # type: ignore
    from app.db import (  # type: ignore
        fetch_by_match_admin,
        fetch_one,
        fetch_table,
        fetch_table_admin,
    )


# ---------------------------------------------------------------------------
# Role helper
# ---------------------------------------------------------------------------

def is_admin_reader() -> bool:
    """True for roles that use service-role DB reads (bypasses RLS)."""
    return current_role() in {"admin", "pm"}


# ---------------------------------------------------------------------------
# Estimates list
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60, show_spinner=False)
def _fetch_estimates_list_cached(*, admin: bool, version: int) -> list[dict[str, Any]]:
    if admin:
        return fetch_table_admin("estimates", limit=1000, order_by="updated_at")
    return fetch_table("estimates", limit=1000, order_by="updated_at")


def fetch_estimates_list() -> list[dict[str, Any]]:
    """Fetch the estimates list using a version-keyed cache (60 s TTL).

    Call ``services.bump_estimates_cache()`` after any write to invalidate.
    """
    v = int(st.session_state.get("est_data_version", 0))
    return _fetch_estimates_list_cached(admin=is_admin_reader(), version=v)


# ---------------------------------------------------------------------------
# Single estimate row  (short TTL — activity panel / editor top bar)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=30, show_spinner=False)
def _fetch_estimate_by_id_cached(*, estimate_id: str, admin: bool) -> dict[str, Any] | None:
    if not estimate_id:
        return None
    if admin:
        rows = fetch_by_match_admin("estimates", {"id": estimate_id}, limit=1)
        return rows[0] if rows else None
    return fetch_one("estimates", {"id": estimate_id})


def fetch_estimate_by_id(estimate_id: str) -> dict[str, Any] | None:
    """Fetch a single estimate row by primary key (30 s cache).

    Returns None if not found or estimate_id is blank.
    """
    eid = str(estimate_id or "").strip()
    if not eid:
        return None
    return _fetch_estimate_by_id_cached(estimate_id=eid, admin=is_admin_reader())


# ---------------------------------------------------------------------------
# Customers (for import matching)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300, show_spinner=False)
def _fetch_customers_cached(*, admin: bool) -> list[dict[str, Any]]:
    cols = "id,customer_name"
    if admin:
        return fetch_table_admin("customers", columns=cols, limit=3000, order_by="customer_name")
    return fetch_table("customers", columns=cols, limit=3000, order_by="customer_name")


def fetch_customers_for_estimates() -> list[dict[str, Any]]:
    """Fetch customer directory rows (300 s cache, used for import customer matching)."""
    return _fetch_customers_cached(admin=is_admin_reader())


# ---------------------------------------------------------------------------
# Jobs (for list linkage display)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=120, show_spinner=False)
def _fetch_jobs_for_estimates_cached(*, admin: bool) -> list[dict[str, Any]]:
    cols = "id,job_number,estimate_id,job_name"
    if admin:
        return fetch_table_admin("jobs", columns=cols, limit=5000, order_by="job_number")
    return fetch_table("jobs", columns=cols, limit=5000, order_by="job_number")


def fetch_jobs_for_estimates() -> list[dict[str, Any]]:
    """Fetch jobs for the estimates list link-column (120 s cache)."""
    return _fetch_jobs_for_estimates_cached(admin=is_admin_reader())


# ---------------------------------------------------------------------------
# Customer locations (for list site-line display)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300, show_spinner=False)
def _fetch_locations_index_cached(*, admin: bool) -> dict[str, dict[str, Any]]:
    """Return {location_id: row} for all customer locations."""
    try:
        try:
            from services.customer_locations import fetch_all_locations_indexed
        except ImportError:
            from app.services.customer_locations import fetch_all_locations_indexed  # type: ignore
        return fetch_all_locations_indexed(admin_read=admin)
    except Exception:
        return {}


def fetch_locations_index() -> dict[str, dict[str, Any]]:
    """Cached {location_id: row} map used for the 'Site:' caption in the estimates list."""
    return _fetch_locations_index_cached(admin=is_admin_reader())
