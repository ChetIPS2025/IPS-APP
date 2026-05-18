"""Database fetch functions for the Jobs module.

All heavy reads go here, with ``@st.cache_data`` where safe.
UI layers call these wrappers; they do not query the DB directly.
"""
from __future__ import annotations

import streamlit as st
from typing import Any

try:
    from app.db import (
        fetch_by_match,
        fetch_by_match_admin,
        fetch_table,
        fetch_table_admin,
    )
except ImportError:
    from db import fetch_by_match, fetch_by_match_admin, fetch_table, fetch_table_admin  # type: ignore

from .constants import KEY_DATA_VERSION


# ---------------------------------------------------------------------------
# Role helper (local to avoid circular import)
# ---------------------------------------------------------------------------

def admin_read() -> bool:
    """Admin / manager use service-role reads so RLS doesn't hide linked rows."""
    from auth import current_role  # deferred import

    return current_role() in {"admin", "manager"}


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60, show_spinner=False)
def _fetch_customers_cached(_is_admin: bool, _v: int) -> list[dict[str, Any]]:
    if _is_admin:
        try:
            return fetch_table_admin("customers", limit=5000, order_by="customer_name")
        except Exception:
            return fetch_table("customers", limit=5000, order_by="customer_name")
    return fetch_table("customers", limit=5000, order_by="customer_name")


def fetch_customers() -> list[dict[str, Any]]:
    v = int(st.session_state.get(KEY_DATA_VERSION, 0))
    return _fetch_customers_cached(admin_read(), v)


# ---------------------------------------------------------------------------
# Estimates
# ---------------------------------------------------------------------------

_ESTIMATE_COLUMN_SETS = (
    "id,quote_number,customer_id,customer_contact_id,proposal_total,final_bid,status,job_id,scope_of_work,po_amount,po_number,estimate_description",
    "id,quote_number,customer_id,proposal_total,final_bid,status,job_id,scope_of_work,po_amount",
    "id,quote_number,customer_id,proposal_total,status,job_id,scope_of_work",
    "id,quote_number,customer_id,proposal_total,status,job_id",
)


@st.cache_data(ttl=60, show_spinner=False)
def _fetch_estimates_cached(_is_admin: bool, _v: int) -> list[dict[str, Any]]:
    fetch_fn = fetch_table_admin if _is_admin else fetch_table
    fallback = fetch_table
    for cols in _ESTIMATE_COLUMN_SETS:
        try:
            return fetch_fn("estimates", columns=cols, limit=5000, order_by="quote_number")
        except Exception:
            continue
    try:
        return fetch_fn("estimates", limit=5000, order_by="quote_number")
    except Exception:
        return fallback("estimates", limit=5000, order_by="quote_number")


def fetch_estimates() -> list[dict[str, Any]]:
    v = int(st.session_state.get(KEY_DATA_VERSION, 0))
    return _fetch_estimates_cached(admin_read(), v)


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------

def fetch_contacts_for_job_database(
    customer_id: str,
    customer_location_id: str | None = None,
) -> list[dict[str, Any]]:
    """Contacts scoped to a customer (and optionally a job site)."""
    try:
        from app.services.customer_contacts import fetch_contacts_for_customer_scope
    except ImportError:
        from services.customer_contacts import fetch_contacts_for_customer_scope  # type: ignore

    cid = str(customer_id or "").strip()
    if not cid:
        return []
    loc = str(customer_location_id or "").strip() or None
    return fetch_contacts_for_customer_scope(cid, loc, admin_read=admin_read(), include_inactive=False)


def fetch_estimate_by_id(estimate_id: str) -> dict[str, Any] | None:
    eid = str(estimate_id or "").strip()
    if not eid:
        return None
    fn = fetch_by_match_admin if admin_read() else fetch_by_match
    try:
        rows = fn("estimates", {"id": eid}, limit=1)
        return rows[0] if rows else None
    except Exception:
        return None


def fetch_contact_by_id(contact_id: str) -> dict[str, Any] | None:
    cid = str(contact_id or "").strip()
    if not cid:
        return None
    fn = fetch_by_match_admin if admin_read() else fetch_by_match
    try:
        rows = fn("customer_contacts", {"id": cid}, limit=1)
        return rows[0] if rows else None
    except Exception:
        return None


@st.cache_data(ttl=120, show_spinner=False)
def _has_customer_location_column_cached() -> bool:
    try:
        fetch_table("jobs", columns="id,customer_location_id", limit=1)
        return True
    except Exception:
        return False


def jobs_has_customer_location_column() -> bool:
    return _has_customer_location_column_cached()


# ---------------------------------------------------------------------------
# Contact labels (all contacts for the job list display)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60, show_spinner=False)
def _fetch_contact_labels_cached(_is_admin: bool, _v: int) -> dict[str, str]:
    try:
        from app.services.customer_contacts import contact_option_label
    except ImportError:
        from services.customer_contacts import contact_option_label  # type: ignore

    fn = fetch_table_admin if _is_admin else fetch_table
    try:
        rows = fn("customer_contacts", limit=10000, order_by=None)
    except Exception:
        return {}
    return {
        str(cr.get("id") or "").strip(): contact_option_label(cr)
        for cr in (rows or [])
        if str(cr.get("id") or "").strip()
    }


def fetch_all_contact_labels(*, is_admin: bool) -> dict[str, str]:
    """Return {contact_id: display_label} for the overview grid (cached 60 s)."""
    v = int(st.session_state.get(KEY_DATA_VERSION, 0))
    return _fetch_contact_labels_cached(is_admin, v)


# ---------------------------------------------------------------------------
# Cache invalidation
# ---------------------------------------------------------------------------

def bump_data_version() -> None:
    """Increment the version key so all @st.cache_data functions reload on next run."""
    st.session_state[KEY_DATA_VERSION] = int(st.session_state.get(KEY_DATA_VERSION, 0)) + 1
    # Explicitly clear Streamlit's in-process cache for our cached functions.
    _fetch_customers_cached.clear()
    _fetch_estimates_cached.clear()
    _fetch_contact_labels_cached.clear()
    _has_customer_location_column_cached.clear()
