from __future__ import annotations

import streamlit as st
from auth import current_profile
from branding import render_header
from data_cache import fetch_table_for_session


def _norm_status(v) -> str:
    return " ".join(str(v or "").strip().split()).casefold()


_AWARDED_STATUS_TOKENS = {
    "awarded",
    "won",
    "active",
}

_BIDDING_STATUS_TOKENS = {
    "bidding",
    "estimating",
    "proposal",
    "quoted",
}


def _job_status_bucket(status_value) -> str | None:
    """
    Centralized job status normalization + classification.

    - trims whitespace and compares case-insensitively
    - treats substring matches as valid (handles inconsistent status text)
    - returns: "awarded" | "bidding" | None
    """
    s = _norm_status(status_value)
    if not s:
        return None
    if s in _AWARDED_STATUS_TOKENS or any(tok in s for tok in _AWARDED_STATUS_TOKENS):
        return "awarded"
    if s in _BIDDING_STATUS_TOKENS or any(tok in s for tok in _BIDDING_STATUS_TOKENS):
        return "bidding"
    return None


def count_awarded_jobs(jobs: list[dict]) -> int:
    return sum(1 for j in (jobs or []) if _job_status_bucket((j or {}).get("status")) == "awarded")


def count_bidding_jobs(jobs: list[dict]) -> int:
    return sum(1 for j in (jobs or []) if _job_status_bucket((j or {}).get("status")) == "bidding")


def count_active_employees(employees: list[dict]) -> int:
    rows = employees or []
    if not rows:
        return 0
    has_is_active = any(isinstance(r, dict) and "is_active" in r for r in rows)
    if not has_is_active:
        return len(rows)
    return sum(1 for r in rows if bool((r or {}).get("is_active", False)))


def render() -> None:
    render_header("IPS Dashboard")
    st.caption("Shared multi-user estimating dashboard")

    sk = str(current_profile().get("id") or "anonymous")
    try:
        customers = fetch_table_for_session("customers", session_key=sk)
    except Exception:
        customers = []
    try:
        jobs = fetch_table_for_session("jobs", session_key=sk, order_by="job_number")
    except Exception:
        jobs = []
    try:
        estimates = fetch_table_for_session("estimates", session_key=sk)
    except Exception:
        estimates = []
    try:
        employees = fetch_table_for_session("employees", session_key=sk, order_by="name")
    except Exception:
        employees = []

    c1, c2, c3 = st.columns(3)
    c1.metric("Jobs Awarded", count_awarded_jobs(jobs))
    c2.metric("Jobs Bidding", count_bidding_jobs(jobs))
    c3.metric("Employees", count_active_employees(employees))

    st.markdown("### Recent Estimates")
    st.dataframe(estimates[:25], use_container_width=True, hide_index=True)
