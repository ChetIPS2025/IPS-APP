from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

import pandas as pd
import streamlit as st

try:
    from app.auth import current_role
    from app.branding import render_header
    from app.db import fetch_jobs_with_order_fallback, fetch_table, fetch_table_admin
    from app.services.asset_maintenance_service import maintenance_due_status
    from app.services.job_service import job_number_display
except ImportError:
    from auth import current_role  # type: ignore
    from branding import render_header  # type: ignore
    from db import fetch_jobs_with_order_fallback, fetch_table, fetch_table_admin  # type: ignore
    from services.asset_maintenance_service import maintenance_due_status  # type: ignore
    from services.job_service import job_number_display  # type: ignore

_RECENT_LIMIT = 12
_METRIC_FETCH_LIMIT = 5000


def _ips_nav_pending_key() -> str:
    try:
        from app.ui import IPS_NAV_PENDING_KEY
    except ImportError:
        from ui import IPS_NAV_PENDING_KEY  # type: ignore
    return IPS_NAV_PENDING_KEY


def _new_estimate_and_navigate() -> None:
    """Match Estimates page « New estimate » — blank editor + Estimates route."""
    try:
        from app.pages.estimate_editor import blank_estimate, ensure_state
        from app.pages.estimates import _reset_estimate_editor_transients
    except ImportError:
        from pages.estimate_editor import blank_estimate, ensure_state  # type: ignore
        from pages.estimates import _reset_estimate_editor_transients  # type: ignore
    _reset_estimate_editor_transients(clear_import_hints=True)
    st.session_state["estimate_editor_state"] = blank_estimate()
    st.session_state["loaded_estimate_id"] = None
    st.session_state["estimate_editor_quote_ready"] = False
    ensure_state()
    st.session_state["estimates_view"] = "edit"
    st.session_state[_ips_nav_pending_key()] = "Estimates"
    st.rerun()


def _navigate_to_sidebar_page(page: str) -> None:
    st.session_state[_ips_nav_pending_key()] = page
    st.rerun()


def _open_job_in_database(job_id: str) -> None:
    """Job Database edit mode for this job id (same keys as job_database)."""
    st.session_state["job_mode"] = "edit"
    st.session_state["job_edit_id"] = str(job_id)
    st.session_state[_ips_nav_pending_key()] = "Job Database"
    st.rerun()


def _open_estimate_in_editor(estimate_id: str) -> None:
    """Load row into session and open Estimates editor (same as list open)."""
    try:
        from app.pages.estimates import _load_estimate_into_session
    except ImportError:
        from pages.estimates import _load_estimate_into_session  # type: ignore
    _load_estimate_into_session(estimate_id)
    if not str(st.session_state.get("loaded_estimate_id") or "").strip():
        st.warning("Could not load that estimate — it may have been removed.")
        return
    st.session_state["estimates_view"] = "edit"
    st.session_state[_ips_nav_pending_key()] = "Estimates"
    st.rerun()


def _dashboard_admin_read() -> bool:
    """Service-role reads when RLS would hide rows from the anon client."""
    try:
        return current_role() in {"admin", "pm"}
    except Exception:
        return False


def _row_timestamp(row: dict[str, Any]) -> float:
    for key in ("updated_at", "created_at", "modified_at"):
        v = row.get(key)
        if v is None:
            continue
        s = str(v).strip()
        if not s:
            continue
        try:
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            dt = datetime.fromisoformat(s)
            return dt.timestamp()
        except Exception:
            continue
    return 0.0


def _format_datetime_cell(val: Any) -> str:
    if val is None:
        return "—"
    s = str(val).strip()
    if not s:
        return "—"
    if "T" in s:
        return s.replace("T", " ")[:19]
    return s[:10] if len(s) >= 10 else s


def _estimate_money_display(val: Any) -> str:
    if val is None:
        return "—"
    try:
        if pd.isna(val):
            return "—"
    except Exception:
        pass
    try:
        d = Decimal(str(val).replace(",", "").strip()).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return f"${d:,.2f}"
    except Exception:
        s = str(val).strip()
        return s[:32] + ("…" if len(s) > 32 else "")


def _fetch_jobs_dashboard() -> list[dict[str, Any]]:
    admin = _dashboard_admin_read()
    fn = fetch_table_admin if admin else fetch_table
    for cols in (
        "id,job_number,job_name,customer_id,status,updated_at,created_at",
        "id,job_number,job_name,customer_id,status,created_at",
        "id,job_name,customer_id,status,updated_at,created_at",
    ):
        try:
            return list(fn("jobs", columns=cols, limit=_METRIC_FETCH_LIMIT, order_by=None))
        except Exception:
            continue
    try:
        return list(fetch_jobs_with_order_fallback(limit=_METRIC_FETCH_LIMIT, use_admin=admin))
    except Exception:
        return []


def _fetch_estimates_dashboard() -> list[dict[str, Any]]:
    admin = _dashboard_admin_read()
    fn = fetch_table_admin if admin else fetch_table
    for cols in (
        "id,quote_number,customer_id,proposal_total,status,updated_at,created_at",
        "id,quote_number,customer_id,status,updated_at,created_at",
        "id,quote_number,customer_id,proposal_total,status",
    ):
        try:
            return list(fn("estimates", columns=cols, limit=_METRIC_FETCH_LIMIT, order_by=None))
        except Exception:
            continue
    try:
        return list(fn("estimates", columns="*", limit=_METRIC_FETCH_LIMIT, order_by=None))
    except Exception:
        return []


def _fetch_customers_map() -> dict[str, str]:
    admin = _dashboard_admin_read()
    fn = fetch_table_admin if admin else fetch_table
    try:
        rows = fn(
            "customers",
            columns="id,customer_name",
            limit=_METRIC_FETCH_LIMIT,
            order_by="customer_name",
        )
    except Exception:
        try:
            rows = fn("customers", columns="id,customer_name", limit=_METRIC_FETCH_LIMIT, order_by=None)
        except Exception:
            return {}
    out: dict[str, str] = {}
    for r in rows or []:
        cid = str(r.get("id") or "").strip()
        if cid:
            out[cid] = str(r.get("customer_name") or "").strip() or cid
    return out


def render() -> None:
    render_header("Asset Dashboard")
    st.caption("Business overview — activity, maintenance, and fleet status.")

    jobs_all: list[dict[str, Any]] = []
    estimates_all: list[dict[str, Any]] = []
    customer_map: dict[str, str] = {}

    try:
        jobs_all = _fetch_jobs_dashboard()
    except Exception:
        jobs_all = []
    try:
        estimates_all = _fetch_estimates_dashboard()
    except Exception:
        estimates_all = []
    try:
        customer_map = _fetch_customers_map()
    except Exception:
        customer_map = {}

    try:
        assets = fetch_table("assets", limit=5000, order_by="asset_name")
    except Exception:
        assets = []
        st.warning("Could not load assets. Check database connectivity.")

    try:
        maintenance = fetch_table("asset_maintenance", limit=5000, order_by="service_date")
    except Exception:
        maintenance = []

    # --- Summary metrics (business) ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Jobs", len(jobs_all))
    m2.metric("Estimates", len(estimates_all))
    m3.metric("Customers", len(customer_map))
    m4.metric("Assets", len(assets))

    # --- Quick actions (sidebar routing) ---
    st.markdown("##### Quick actions")
    qa1, qa2, qa3, qa4 = st.columns(4)
    with qa1:
        if st.button("New Estimate", type="primary", use_container_width=True, key="adash_qa_new_est"):
            _new_estimate_and_navigate()
    with qa2:
        if st.button("Open Job Database", use_container_width=True, key="adash_qa_jobs"):
            _navigate_to_sidebar_page("Job Database")
    with qa3:
        if st.button("Open Customers", use_container_width=True, key="adash_qa_cust"):
            _navigate_to_sidebar_page("Customers")
    with qa4:
        if st.button("Open Asset Database", use_container_width=True, key="adash_qa_assets"):
            _navigate_to_sidebar_page("Asset Database")
    st.caption("Shortcuts switch the main workspace to that section (same as the sidebar).")

    st.divider()

    # --- Recent jobs (compact rows + Open) ---
    st.subheader("Recent jobs")
    jobs_sorted = sorted(jobs_all, key=_row_timestamp, reverse=True)[:_RECENT_LIMIT]
    if jobs_sorted:
        st.caption("Each row opens that job in **Job Database** (edit form).")
        for j in jobs_sorted:
            jid = str(j.get("id") or "").strip()
            if not jid:
                continue
            cid = str(j.get("customer_id") or "").strip()
            cust = customer_map.get(cid, "—") if cid else "—"
            jn = job_number_display(j.get("job_number")) or "—"
            jname = str(j.get("job_name") or "").strip() or "—"
            if len(jname) > 52:
                jname = jname[:49] + "…"
            stc = str(j.get("status") or "").strip() or "—"
            upd = _format_datetime_cell(j.get("updated_at") or j.get("created_at"))
            c1, c2 = st.columns([5, 1])
            with c1:
                st.markdown(f"**{jn}** · {jname} · {cust} · _{stc}_ · {upd}")
            with c2:
                if st.button("Open", key=f"adash_job_{jid}", use_container_width=True):
                    _open_job_in_database(jid)
    else:
        st.caption("No job records loaded (or jobs table unavailable).")

    # --- Recent estimates (compact rows + Open) ---
    st.subheader("Recent estimates")
    est_sorted = sorted(estimates_all, key=_row_timestamp, reverse=True)[:_RECENT_LIMIT]
    if est_sorted:
        st.caption("Each row loads that quote in **Estimates** (editor).")
        for e in est_sorted:
            eid = str(e.get("id") or "").strip()
            if not eid:
                continue
            cid = str(e.get("customer_id") or "").strip()
            cust = customer_map.get(cid, "—") if cid else "—"
            qn = str(e.get("quote_number") or "").strip() or "—"
            stc = str(e.get("status") or "").strip() or "—"
            tot = _estimate_money_display(e.get("proposal_total"))
            upd = _format_datetime_cell(e.get("updated_at") or e.get("created_at"))
            c1, c2 = st.columns([5, 1])
            with c1:
                st.markdown(f"**{qn}** · {cust} · {tot} · _{stc}_ · {upd}")
            with c2:
                if st.button("Open", key=f"adash_est_{eid}", use_container_width=True):
                    _open_estimate_in_editor(eid)
    else:
        st.caption("No estimate records loaded (or estimates table unavailable).")

    st.divider()

    # --- Asset maintenance overview (preserved) ---
    st.subheader("Asset fleet & maintenance")
    latest_maintenance_by_asset: dict[Any, dict] = {}
    for record in maintenance:
        asset_id = record.get("asset_id")
        if asset_id not in latest_maintenance_by_asset:
            latest_maintenance_by_asset[asset_id] = record

    overdue = 0
    due_soon = 0
    assigned = 0
    in_shop = 0
    available = 0

    rows = []
    for asset in assets:
        status = str(asset.get("status", ""))
        if status == "Assigned":
            assigned += 1
        elif status == "In Shop":
            in_shop += 1
        elif status == "Available":
            available += 1

        due_status = maintenance_due_status(asset, latest_maintenance_by_asset.get(asset.get("id")))
        if due_status == "Overdue":
            overdue += 1
        elif due_status == "Due Soon":
            due_soon += 1

        rows.append(
            {
                "Asset ID": asset.get("asset_id"),
                "Asset Name": asset.get("asset_name"),
                "Type": asset.get("asset_type"),
                "Status": status,
                "Location": asset.get("location"),
                "Assigned Employee": asset.get("assigned_employee"),
                "Maintenance": due_status,
            }
        )

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Assets", len(assets))
    c2.metric("Available", available)
    c3.metric("Assigned", assigned)
    c4.metric("In Shop", in_shop)
    c5.metric("Overdue PM", overdue)

    st.caption(f"Due Soon: {due_soon}")

    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No asset records found.")
