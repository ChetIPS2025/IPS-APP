from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st
from auth import current_profile, current_role
from branding import render_header
from data_cache import fetch_table_for_session

try:
    from app.services.job_service import job_number_display
except ImportError:
    from services.job_service import job_number_display  # type: ignore


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
    # Job Database lifecycle (pre-award / in-flight work) — title-cased in DB, matched case-insensitively
    "draft",
    "submitted",
    "approved",
    "scheduled",
    "in progress",
    "on hold",
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


def _row_ts(row: dict) -> str:
    for k in ("updated_at", "modified_at", "created_at"):
        v = row.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""


def _recent_jobs_rows(jobs: list[dict], *, limit: int = 12) -> list[dict]:
    if not jobs:
        return []
    rows = sorted(jobs, key=_row_ts, reverse=True)
    return rows[:limit]


def _recent_estimates_rows(estimates: list[dict], *, limit: int = 12) -> list[dict]:
    if not estimates:
        return []
    rows = sorted(estimates, key=_row_ts, reverse=True)
    return rows[:limit]


def _jobs_display_df(rows: list[dict]) -> pd.DataFrame:
    out: list[dict] = []
    for j in rows:
        if not isinstance(j, dict):
            continue
        jn = job_number_display(j.get("job_number"))
        out.append(
            {
                "Job #": jn or "—",
                "Name": str(j.get("job_name") or "").strip() or "—",
                "Status": str(j.get("status") or "").strip() or "—",
            }
        )
    return pd.DataFrame(out)


def _estimates_display_df(rows: list[dict]) -> pd.DataFrame:
    out: list[dict] = []
    for e in rows:
        if not isinstance(e, dict):
            continue
        ts = _row_ts(e)
        ts_disp = ts[:19].replace("T", " ") if ts else "—"
        try:
            if "T" in ts and len(ts) >= 10:
                ts_disp = datetime.fromisoformat(ts.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
        except Exception:
            ts_disp = ts[:16] if ts else "—"
        out.append(
            {
                "Quote": str(e.get("quote_number") or "").strip() or "—",
                "Status": str(e.get("status") or "").strip() or "—",
                "Updated": ts_disp,
            }
        )
    return pd.DataFrame(out)


def render() -> None:
    render_header(
        "IPS Dashboard",
        subtitle="Industrial Plant Solutions, LLC",
        help_text="Pipeline snapshot, customers on file, and recent jobs and estimates — use the sidebar for every module.",
    )

    sk = str(current_profile().get("id") or "anonymous")
    use_admin = current_role() in {"admin", "estimator"}
    _lim = 5000
    try:
        customers = fetch_table_for_session(
            "customers", session_key=sk, limit=_lim, order_by="customer_name", use_admin=use_admin
        )
    except Exception:
        customers = []
    try:
        jobs = fetch_table_for_session(
            "jobs", session_key=sk, limit=_lim, order_by="job_number", use_admin=use_admin
        )
    except Exception:
        jobs = []
    try:
        estimates = fetch_table_for_session(
            "estimates", session_key=sk, limit=_lim, order_by="quote_number", use_admin=use_admin
        )
    except Exception:
        estimates = []
    try:
        employees = fetch_table_for_session(
            "employees", session_key=sk, limit=_lim, order_by="name", use_admin=use_admin
        )
    except Exception:
        employees = []

    with st.container(border=True):
        st.markdown('<span class="ips-dash-metrics"></span>', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4, gap="small")
        c1.metric("Customers", len(customers or []))
        c2.metric("Jobs awarded", count_awarded_jobs(jobs))
        c3.metric("Jobs bidding", count_bidding_jobs(jobs))
        c4.metric("Active employees", count_active_employees(employees))

    left, right = st.columns(2, gap="medium")
    with left:
        st.markdown("##### Recent jobs")
        rj = _recent_jobs_rows(list(jobs or []))
        if not rj:
            st.caption("No jobs loaded yet.")
        else:
            st.dataframe(_jobs_display_df(rj), use_container_width=True, hide_index=True, height=320)

    with right:
        st.markdown("##### Recent estimates")
        re = _recent_estimates_rows(list(estimates or []))
        if not re:
            st.caption("No estimates loaded yet.")
        else:
            st.dataframe(_estimates_display_df(re), use_container_width=True, hide_index=True, height=320)
