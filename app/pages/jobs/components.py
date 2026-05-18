"""Reusable UI components for the Jobs list / overview page."""
from __future__ import annotations

import html
import logging
from typing import Any

import pandas as pd
import streamlit as st

from auth import current_role

try:
    from app.ui.compact_forms import field_marker
    from app.ui.components.empty_states import render_empty_state
    from app.ui.page_shell import action_bar_card, render_card, render_section_header
except ImportError:
    from ui.compact_forms import field_marker  # type: ignore
    from ui.components.empty_states import render_empty_state  # type: ignore
    from ui.page_shell import action_bar_card, render_card, render_section_header  # type: ignore

try:
    from table_actions import (
        IPS_PENDING_DELETE,
        TABLE_KEY_JOBS,
        clear_selected_ids,
        get_selected_ids,
        inject_table_action_styles,
        set_selected_ids,
    )
except ImportError:
    from app.table_actions import (  # type: ignore
        IPS_PENDING_DELETE,
        TABLE_KEY_JOBS,
        clear_selected_ids,
        get_selected_ids,
        inject_table_action_styles,
        set_selected_ids,
    )

try:
    from app.mobile_ui import IPS_VIEWPORT_NARROW_KEY, ensure_narrow_viewport_detected
except ImportError:
    from mobile_ui import IPS_VIEWPORT_NARROW_KEY, ensure_narrow_viewport_detected  # type: ignore

try:
    from services.job_schema import JOBS_JOB_DATABASE_OVERVIEW_DISPLAY_ORDER
except ImportError:
    from app.services.job_schema import JOBS_JOB_DATABASE_OVERVIEW_DISPLAY_ORDER  # type: ignore

from .constants import JOB_STATUSES, KEY_EDIT_ID, KEY_JOB_MODE, KEY_SELECTED_ID, KEY_VIEW_MODE
from .services import convert_estimate_to_job, delete_jobs
from .utils import (
    card_text,
    clear_job_mode,
    money_cell,
    render_cell_with_tooltip,
    render_job_name_cell,
    render_money_cell_html,
    status_badge_html,
    visible_columns,
)

_LOG = logging.getLogger(__name__)

# Columns kept for logic / search but hidden from the rendered table.
_HIDDEN_COLS = frozenset({"customer_id", "estimate_label", "Source", "source_type", "project_manager",
                          "supervisor", "start_date", "target_completion_date", "completed_date", "notes"})


# ---------------------------------------------------------------------------
# DataFrame enrichment
# ---------------------------------------------------------------------------

def build_jobs_overview_dataframe(
    jobs_df: pd.DataFrame,
    *,
    customer_name_by_id: dict[str, str],
    estimate_label_map: dict[str, str],
    estimate_quote_by_id: dict[str, str],
    contact_label_by_id: dict[str, str],
    location_by_id: dict[str, dict[str, Any]],
) -> pd.DataFrame:
    """Augment raw jobs rows with display columns (customer name, estimate labels, location, contact)."""
    if jobs_df.empty:
        return jobs_df
    out = jobs_df.copy()

    def _str(v: Any) -> str:
        if v is None:
            return ""
        try:
            if pd.isna(v):
                return ""
        except Exception:
            pass
        return str(v).strip()

    if "customer_id" in out.columns:
        out["customer_name"] = out["customer_id"].map(lambda v: customer_name_by_id.get(_str(v), ""))
    else:
        out["customer_name"] = ""

    if "estimate_id" in out.columns:
        out["estimate_label"] = out["estimate_id"].map(lambda v: estimate_label_map.get(_str(v), ""))
        out["Quote (estimate)"] = out["estimate_id"].map(
            lambda v: (f"Estimate {q}" if (q := estimate_quote_by_id.get(_str(v), "")) else "") if _str(v) else ""
        )
        out["Source"] = out["estimate_id"].map(
            lambda v: (f"From estimate: {q}" if (q := estimate_quote_by_id.get(_str(v), "")) else "From estimate") if _str(v) else "—"
        )
    else:
        out["estimate_label"] = ""
        out["Quote (estimate)"] = ""
        out["Source"] = "—"

    if "customer_contact_id" in out.columns:
        out["Contact"] = out["customer_contact_id"].map(lambda v: contact_label_by_id.get(_str(v), ""))
    else:
        out["Contact"] = ""

    try:
        from services.customer_locations import location_display_name_city_state
    except ImportError:
        from app.services.customer_locations import location_display_name_city_state  # type: ignore

    if "customer_location_id" in out.columns:
        def _loc(v: Any) -> str:
            lid = _str(v)
            if not lid:
                return ""
            row = location_by_id.get(lid)
            return location_display_name_city_state(row) if row else ""
        out["Location"] = out["customer_location_id"].map(_loc)
    else:
        out["Location"] = ""

    out["Linked estimate"] = out["Source"].astype(str) if "Source" in out.columns else "—"
    return out


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

def filter_jobs_dataframe(
    df: pd.DataFrame,
    *,
    selected_customer: str,
    selected_status: str,
    selected_source: str,
    search: str,
    bypass: bool,
) -> pd.DataFrame:
    out = df.copy()
    if not bypass:
        if selected_customer != "All" and "customer_name" in out.columns:
            out = out[out["customer_name"].astype(str) == selected_customer]
        if selected_status != "All" and "status" in out.columns:
            out = out[out["status"].astype(str) == selected_status]
        if selected_source != "All" and "Source" in out.columns:
            is_estimate = out["Source"].astype(str).str.contains("From estimate", case=False, na=False)
            if selected_source == "Estimate":
                out = out[is_estimate]
            elif selected_source == "Other":
                out = out[~is_estimate]
    if search.strip():
        s = search.strip().lower()
        mask = out.astype(str).apply(lambda col: col.str.lower().str.contains(s, na=False))
        out = out[mask.any(axis=1)]
    return out


# ---------------------------------------------------------------------------
# Top action bar (Create / Convert / Refresh)
# ---------------------------------------------------------------------------

def render_jobs_top_bar(
    *,
    can_edit: bool,
    estimates: list[dict[str, Any]],
    estimate_label_map: dict[str, str],
) -> None:
    ecandidates = [e for e in estimates if e.get("id") is not None and not str(e.get("job_id") or "").strip()]

    with action_bar_card(title="Quick Actions"):
        st.markdown('<span class="ips-job-db-quick-actions" aria-hidden="true"></span>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3, gap="small")
        with c1:
            if st.button("Create New Job", type="primary", use_container_width=True, disabled=not can_edit, key="job_top_create"):
                st.session_state[KEY_VIEW_MODE] = "create"
                st.session_state[KEY_SELECTED_ID] = None
                st.session_state[KEY_JOB_MODE] = "add"
                st.session_state.pop(KEY_EDIT_ID, None)
                st.session_state.pop("job_number_manual_input", None)
                st.session_state.pop("job_db_show_convert", None)
                st.rerun()
        with c2:
            if st.button("Convert Estimate to Job", type="secondary", use_container_width=True, disabled=not can_edit or not ecandidates, key="job_top_convert"):
                st.session_state["job_db_show_convert"] = True
                st.rerun()
        with c3:
            if st.button("Refresh", type="secondary", use_container_width=True, key="job_top_refresh"):
                st.session_state.pop("job_db_show_convert", None)
                st.rerun()

        if not can_edit:
            pass
        elif not ecandidates:
            st.markdown('<p class="ips-jdb-muted">No approved estimates ready to convert.</p>', unsafe_allow_html=True)
        elif st.session_state.get("job_db_show_convert"):
            labels = [estimate_label_map.get(str(e.get("id")), str(e.get("id"))) for e in ecandidates]
            idx_opts = list(range(len(ecandidates)))
            conv_a, conv_b = st.columns([4, 1], gap="small")
            with conv_a:
                pick = st.selectbox("Estimate to convert", idx_opts, format_func=lambda i: labels[int(i)], key="job_conv_est", label_visibility="collapsed")
            with conv_b:
                if st.button("Convert", type="primary", use_container_width=True, key="job_conv_go"):
                    eid = str(ecandidates[int(pick)].get("id") or "")
                    res = convert_estimate_to_job(eid)
                    if res.ok:
                        st.session_state.pop("job_db_show_convert", None)
                        st.success(res.message)
                        st.rerun()
                    else:
                        st.error(res.message)


# ---------------------------------------------------------------------------
# Job card list (mobile / tablet view)
# ---------------------------------------------------------------------------

def render_job_card_list(
    *,
    df_display: pd.DataFrame,
    job_num_col: str,
    can_edit: bool,
) -> None:
    st.markdown('<span class="ips-job-card-list-anchor"></span>', unsafe_allow_html=True)
    if df_display.empty:
        render_empty_state("No jobs match filters", "Clear search or adjust customer, status, or source filters.", icon="🔍")
        return
    allow_open = can_edit or (current_role() == "employee")
    for _, row in df_display.iterrows():
        jid = str(row.get("id") or "").strip()
        if not jid:
            continue
        with st.container(border=True):
            st.markdown('<span class="ips-job-card-anchor"></span>', unsafe_allow_html=True)
            job_num = card_text(row.get(job_num_col), "No job #")
            job_name = card_text(row.get("job_name"), "Untitled job")
            customer = card_text(row.get("customer_name"))
            status = card_text(row.get("status"))
            quote = card_text(row.get("Quote (estimate)"), "")
            awarded = money_cell(row.get("awarded_amount"))
            amount = quote or awarded
            amount_html = f'<span class="ips-job-card-pill">Quote / PO: {html.escape(amount)}</span>' if amount else ""
            st.markdown(
                f'<p class="ips-job-card-title">{html.escape(job_name)}</p>'
                f'<p class="ips-job-card-meta"><strong>Job #</strong> {html.escape(job_num)} &nbsp; <strong>Customer</strong> {html.escape(customer)}</p>'
                f"{status_badge_html(status)}{amount_html}",
                unsafe_allow_html=True,
            )
            b1, b2, b3 = st.columns([2.2, 1.0, 1.0], gap="small")
            with b1:
                if st.button("👁 View", key=f"job_card_view_{jid}", use_container_width=True):
                    clear_selected_ids(TABLE_KEY_JOBS)
                    st.session_state[KEY_VIEW_MODE] = "view"
                    st.session_state[KEY_SELECTED_ID] = jid
                    st.session_state.pop(KEY_JOB_MODE, None)
                    st.session_state.pop(KEY_EDIT_ID, None)
                    st.rerun()
            with b2:
                if st.button("Open", key=f"job_card_open_{jid}", type="primary", use_container_width=True, disabled=not allow_open, help=None if allow_open else "You do not have access to open this job."):
                    clear_selected_ids(TABLE_KEY_JOBS)
                    st.session_state[KEY_VIEW_MODE] = "edit"
                    st.session_state[KEY_SELECTED_ID] = jid
                    st.session_state[KEY_JOB_MODE] = "edit"
                    st.session_state[KEY_EDIT_ID] = jid
                    st.session_state.pop("job_number_manual_input", None)
                    st.rerun()
            with b3:
                del_help = "Only admin or pm can delete jobs." if not can_edit else "Delete this job (blocked if costing data exists)."
                if st.button("🗑", key=f"job_card_del_{jid}", disabled=not can_edit, use_container_width=True, help=del_help):
                    pending = st.session_state.get(IPS_PENDING_DELETE)
                    if not isinstance(pending, dict):
                        pending = {}
                        st.session_state[IPS_PENDING_DELETE] = pending
                    pending[TABLE_KEY_JOBS] = [jid]
                    st.rerun()


# ---------------------------------------------------------------------------
# Desktop table
# ---------------------------------------------------------------------------

_TABLE_WEIGHTS = [0.40, 1.00, 2.30, 1.70, 1.25, 1.25, 0.95, 1.10, 1.00, 1.05, 0.48, 0.50]
_TABLE_HEADERS = ["", "Job #", "Job Name", "Customer", "Location", "Contact", "Status", "Linked Estimate", "Quote / PO", "Awarded", "View", "Del"]


def render_jobs_table(
    *,
    df_display: pd.DataFrame,
    job_num_col: str,
    can_edit: bool,
    has_job_number_column: bool,
) -> list[str]:
    """Render the desktop table. Returns list of selected job IDs."""
    inject_table_action_styles()
    picked: list[str] = []
    st.markdown('<span class="ips-job-desktop-table-anchor"></span>', unsafe_allow_html=True)
    with st.container():
        st.markdown('<span class="ips-job-table-scroll-anchor"></span>', unsafe_allow_html=True)
        head = st.columns(_TABLE_WEIGHTS, gap="medium")
        for col, label in zip(head, _TABLE_HEADERS):
            col.caption(label)

        for _, row in df_display.iterrows():
            jid = str(row.get("id") or "").strip()
            if not jid:
                continue
            rc = st.columns(_TABLE_WEIGHTS, gap="medium")
            with rc[0]:
                ck = f"job_list_pick_{jid}"
                if ck not in st.session_state:
                    st.session_state[ck] = jid in get_selected_ids(TABLE_KEY_JOBS)
                if st.checkbox("", key=ck, label_visibility="collapsed"):
                    picked.append(jid)
            with rc[1]:
                render_cell_with_tooltip(rc[1], row.get(job_num_col), max_len=14)
            with rc[2]:
                render_job_name_cell(rc[2], row.get("job_name"))
            with rc[3]:
                render_cell_with_tooltip(rc[3], row.get("customer_name"), max_len=28)
            with rc[4]:
                render_cell_with_tooltip(rc[4], row.get("Location"), max_len=24)
            with rc[5]:
                render_cell_with_tooltip(rc[5], row.get("Contact"), max_len=24)
            with rc[6]:
                render_cell_with_tooltip(rc[6], row.get("status"), max_len=18)
            with rc[7]:
                render_cell_with_tooltip(rc[7], row.get("Linked estimate"), max_len=18)
            with rc[8]:
                render_cell_with_tooltip(rc[8], row.get("Quote (estimate)"), max_len=18)
            with rc[9]:
                render_money_cell_html(rc[9], row.get("awarded_amount"))
            with rc[10]:
                if st.button("👁", key=f"job_row_view_{jid}", use_container_width=True, help="View job details"):
                    clear_selected_ids(TABLE_KEY_JOBS)
                    st.session_state[KEY_VIEW_MODE] = "view"
                    st.session_state[KEY_SELECTED_ID] = jid
                    st.session_state.pop(KEY_JOB_MODE, None)
                    st.session_state.pop(KEY_EDIT_ID, None)
                    st.rerun()
            del_help = "Only admin or pm can delete jobs." if not can_edit else "Delete this job (blocked if costing data exists)."
            with rc[11]:
                if st.button("🗑", key=f"job_row_del_{jid}", disabled=not can_edit, use_container_width=True, help=del_help):
                    pending = st.session_state.get(IPS_PENDING_DELETE)
                    if not isinstance(pending, dict):
                        pending = {}
                        st.session_state[IPS_PENDING_DELETE] = pending
                    pending[TABLE_KEY_JOBS] = [jid]
                    st.rerun()

    set_selected_ids(TABLE_KEY_JOBS, picked)
    return picked


# ---------------------------------------------------------------------------
# Selection action bar (edit / delete selected rows)
# ---------------------------------------------------------------------------

def render_jobs_action_bar(
    *,
    sel_ids: list[str],
    can_edit: bool,
    filtered: pd.DataFrame,
    use_table: bool,
) -> None:
    if "id" not in filtered.columns or not use_table:
        return
    st.markdown('<span class="ips-ta-bar-anchor ips-job-action-bar-anchor ips-flat-section"></span>', unsafe_allow_html=True)
    n_sel = len(sel_ids)
    one = n_sel == 1
    none = n_sel == 0
    left, b1, b2 = st.columns([1.35, 1, 1], gap="small")
    with left:
        st.markdown(f'<span class="ips-ta-summary"><span class="ips-ta-num">{n_sel}</span> selected</span>', unsafe_allow_html=True)
    with b1:
        if st.button("Edit", key="job_edit_btn", type="secondary", use_container_width=True, disabled=not (can_edit or current_role() == "employee")):
            if none:
                st.warning("Please select a job first.")
            elif not one:
                st.warning("Please select exactly one job to edit.")
            else:
                st.session_state[KEY_VIEW_MODE] = "edit"
                st.session_state[KEY_SELECTED_ID] = str(sel_ids[0])
                st.session_state[KEY_JOB_MODE] = "edit"
                st.session_state[KEY_EDIT_ID] = str(sel_ids[0])
                st.session_state.pop("job_number_manual_input", None)
                st.rerun()
    with b2:
        if st.button("Delete", key="job_delete_btn", type="secondary", use_container_width=True, disabled=not can_edit):
            if none:
                st.warning("Please select a job first.")
            else:
                pending = st.session_state.get(IPS_PENDING_DELETE)
                if not isinstance(pending, dict):
                    pending = {}
                    st.session_state[IPS_PENDING_DELETE] = pending
                pending[TABLE_KEY_JOBS] = list(sel_ids)
                st.rerun()


# ---------------------------------------------------------------------------
# Pending-delete confirmation
# ---------------------------------------------------------------------------

def render_delete_confirmation(*, can_edit: bool, is_admin: bool) -> None:
    pend = st.session_state.get(IPS_PENDING_DELETE) or {}
    if not (isinstance(pend, dict) and pend.get(TABLE_KEY_JOBS)):
        return
    pend_ids = [str(x) for x in (pend.get(TABLE_KEY_JOBS) or []) if str(x).strip()]
    if not pend_ids:
        return
    with st.container(border=True):
        st.warning(
            f"Delete **{len(pend_ids)}** job(s)? This cannot be undone. "
            "Jobs with **costing data** (time, materials, equipment, or PO expenses) cannot be deleted."
        )
        dc1, dc2 = st.columns(2, gap="small")
        with dc1:
            if st.button("Confirm delete", type="primary", use_container_width=True, key="job_db_confirm_delete"):
                n_ok, errors = delete_jobs(pend_ids, is_admin=is_admin)
                for err in errors:
                    st.error(err)
                pend.pop(TABLE_KEY_JOBS, None)
                clear_selected_ids(TABLE_KEY_JOBS)
                clear_job_mode()
                if n_ok:
                    st.success(f"Deleted {n_ok} job(s).")
                st.rerun()
        with dc2:
            if st.button("Cancel", use_container_width=True, key="job_db_cancel_delete"):
                pend.pop(TABLE_KEY_JOBS, None)
                st.rerun()


# ---------------------------------------------------------------------------
# Full job list section (filters + table/cards)
# ---------------------------------------------------------------------------

def render_jobs_list_section(
    *,
    jobs_df: pd.DataFrame,
    jobs: list[dict[str, Any]],
    has_job_number_column: bool,
    customer_name_by_id: dict[str, str],
    estimate_label_map: dict[str, str],
    estimate_quote_by_id: dict[str, str],
    contact_label_by_id: dict[str, str],
    location_by_id: dict[str, dict[str, Any]],
    customers: list[dict[str, Any]],
    can_edit: bool,
    is_admin: bool,
    fetch_limit: int,
) -> None:
    """Render the full list view: filters, table/cards, action bar, delete confirm."""
    if jobs_df.empty:
        if render_empty_state(
            "No jobs found",
            "Create a job or convert an approved estimate to get started.",
            icon="📋",
            action_label="Create New Job",
            action_key="job_db_empty_create",
        ):
            st.session_state[KEY_VIEW_MODE] = "create"
            st.session_state[KEY_SELECTED_ID] = None
            st.session_state[KEY_JOB_MODE] = "add"
            st.session_state.pop(KEY_EDIT_ID, None)
            st.rerun()
        return

    render_section_header("Jobs Overview", "Search, filter, and manage active job records.")

    enriched = build_jobs_overview_dataframe(
        jobs_df,
        customer_name_by_id=customer_name_by_id,
        estimate_label_map=estimate_label_map,
        estimate_quote_by_id=estimate_quote_by_id,
        contact_label_by_id=contact_label_by_id,
        location_by_id=location_by_id,
    )

    customer_names = sorted(c.get("customer_name", "") for c in customers if str(c.get("customer_name", "")).strip())
    ensure_narrow_viewport_detected()
    if "job_db_view_mode_radio" not in st.session_state:
        st.session_state["job_db_view_mode_radio"] = "Cards" if st.session_state.get(IPS_VIEWPORT_NARROW_KEY) else "Table"

    picked: list[str] = []

    with render_card():
        st.markdown('<span class="ips-list-top-anchor ips-job-filter-anchor ips-job-joblist-section-anchor ips-compact-form"></span>', unsafe_allow_html=True)
        st.markdown('<p class="ips-jdb-section-title">Job list</p>', unsafe_allow_html=True)

        f1, f2, f3, f4 = st.columns([1.0, 1.0, 1.45, 0.95], gap="small")
        with f1:
            field_marker("medium")
            selected_customer = st.selectbox("Filter Customer", ["All"] + customer_names, disabled="customer_id" not in enriched.columns, key="job_filt_customer")
        with f2:
            field_marker("medium")
            selected_status = st.selectbox("Filter Status", ["All"] + JOB_STATUSES, disabled="status" not in enriched.columns, key="job_filt_status")
        with f3:
            field_marker("search")
            _hint = ("Source, quote, contact, location, job_number, job_name, customer, status, …" if has_job_number_column else "Source, quote, contact, location, job_name, customer, status, …")
            search = st.text_input("Search Jobs", placeholder=_hint, key="job_filt_search")
        with f4:
            field_marker("medium")
            selected_source = st.selectbox("Source", ["All", "Estimate", "Other"], disabled="Source" not in enriched.columns, key="job_filt_source", help="Estimate = rows linked to an estimate.")

        if len(jobs) >= fetch_limit and fetch_limit < 8000:
            _lm_l, _lm_r = st.columns([2.2, 1], gap="small")
            with _lm_l:
                st.caption(f"Showing up to **{fetch_limit}** jobs — use **Search** or load more.")
            with _lm_r:
                if st.button("Load more (+500)", key="job_db_load_more_jobs"):
                    st.session_state["job_db_fetch_limit"] = fetch_limit + 500
                    st.rerun()

        _vm_lbl, _vm_ctrl = st.columns([0.42, 5], gap="small", vertical_alignment="center")
        with _vm_lbl:
            st.markdown('<p class="ips-job-list-view-label">View</p>', unsafe_allow_html=True)
        with _vm_ctrl:
            st.radio("View mode", ["Table", "Cards"], horizontal=True, key="job_db_view_mode_radio", label_visibility="collapsed", help="**Table** — checkboxes and row delete. **Cards** — tap Open on a job (better on tablet/phone).")

        use_table = st.session_state.get("job_db_view_mode_radio", "Table") == "Table"
        bypass = st.session_state.get("job_db_bypass_filters", True)

        filtered = filter_jobs_dataframe(
            enriched,
            selected_customer=selected_customer,
            selected_status=selected_status,
            selected_source=selected_source,
            search=search,
            bypass=bypass,
        )

        show_cols: list[str] = []
        if has_job_number_column and "job_number" in filtered.columns:
            show_cols.append("job_number")
        for c in ("Linked estimate", "job_name", "customer_name", "Location", "source_type", "Quote (estimate)", "Contact", "status"):
            if c in filtered.columns and c not in show_cols:
                show_cols.append(c)
        show_cols.extend([c for c in JOBS_JOB_DATABASE_OVERVIEW_DISPLAY_ORDER if c in filtered.columns and c not in show_cols])

        df_display = filtered.copy()
        df_display = df_display.drop(columns=[c for c in _HIDDEN_COLS if c in df_display.columns], errors="ignore")
        vis_cols = visible_columns([c for c in show_cols if c in df_display.columns])

        job_num_col = "job_number" if (has_job_number_column and "job_number" in df_display.columns) else ("job_id" if "job_id" in df_display.columns else "id")

        if "id" not in df_display.columns:
            st.dataframe(df_display[vis_cols], use_container_width=True, hide_index=True)
        elif use_table:
            picked = render_jobs_table(df_display=df_display, job_num_col=job_num_col, can_edit=can_edit, has_job_number_column=has_job_number_column)
        else:
            clear_selected_ids(TABLE_KEY_JOBS)
            render_job_card_list(df_display=df_display, job_num_col=job_num_col, can_edit=can_edit)

    sel_ids = picked if ("id" in filtered.columns and use_table) else []
    render_jobs_action_bar(sel_ids=sel_ids, can_edit=can_edit, filtered=filtered, use_table=use_table)
    render_delete_confirmation(can_edit=can_edit, is_admin=is_admin)
