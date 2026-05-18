"""Jobs module entry point — ``render()`` is called from ``main.py`` via ``job_database.render``."""
from __future__ import annotations

import html
import logging
from typing import Any

import pandas as pd
import streamlit as st

from auth import current_role

try:
    from app.ui.page_shell import render_page_header
except ImportError:
    from ui.page_shell import render_page_header  # type: ignore

try:
    from app.ips_crud_list_styles import inject_ips_crud_list_styles
except ImportError:
    from ips_crud_list_styles import inject_ips_crud_list_styles  # type: ignore

try:
    from app.ui.field_light_theme import inject_field_light_theme
except ImportError:
    from ui.field_light_theme import inject_field_light_theme  # type: ignore

try:
    from app.table_actions import TABLE_KEY_JOBS, clear_selected_ids, inject_table_action_styles
except ImportError:
    from table_actions import TABLE_KEY_JOBS, clear_selected_ids, inject_table_action_styles  # type: ignore

try:
    from services.job_schema import fetch_jobs_for_job_database
    from services.job_service import job_row_select_label, sort_jobs_by_name, sort_jobs_by_number_then_name
except ImportError:
    from app.services.job_schema import fetch_jobs_for_job_database  # type: ignore
    from app.services.job_service import job_row_select_label, sort_jobs_by_name, sort_jobs_by_number_then_name  # type: ignore

try:
    from app.db import fetch_jobs_with_order_fallback, fetch_table, fetch_table_admin
except ImportError:
    from db import fetch_jobs_with_order_fallback, fetch_table, fetch_table_admin  # type: ignore

try:
    from app.services.customer_contacts import contact_option_label
except ImportError:
    from services.customer_contacts import contact_option_label  # type: ignore

from .components import (
    render_delete_confirmation,
    render_jobs_list_section,
    render_jobs_top_bar,
)
from .dialogs import render_job_form_panel
from .queries import (
    admin_read,
    fetch_all_contact_labels,
    fetch_customers,
    fetch_estimate_by_id,
    fetch_estimates,
    jobs_has_customer_location_column,
)
from .styles import inject_job_database_responsive_styles, inject_job_detail_view_page_css
from .utils import (
    clear_job_mode,
    job_detail_display_number,
    migrate_legacy_session,
    sync_job_mode_from_view_state,
)
from .constants import KEY_EDIT_ID, KEY_JOB_MODE, KEY_SELECTED_ID, KEY_VIEW_MODE

_LOG = logging.getLogger(__name__)


def render() -> None:
    st.markdown('<span class="ips-job-db-page" aria-hidden="true"></span>', unsafe_allow_html=True)
    render_page_header("Job Database", "Manage jobs, customers, contacts, and linked estimates.", logo_width=180)

    inject_ips_crud_list_styles()
    inject_table_action_styles()
    inject_job_database_responsive_styles()

    can_edit = current_role() in {"admin", "manager"}
    is_admin = admin_read()

    st.session_state.setdefault("job_db_bypass_filters", True)
    st.session_state.setdefault("job_db_fetch_limit", 500)
    fetch_limit = max(100, min(int(st.session_state.get("job_db_fetch_limit") or 500), 8000))

    # --- Show "loading" placeholder while fetching ---
    _list_shell = st.empty()
    with _list_shell.container():
        st.caption("Loading job data…")

    # --- Load supporting data (customers, estimates, contacts, locations) ---
    customers: list[dict[str, Any]] = []
    estimates: list[dict[str, Any]] = []
    try:
        customers = list(fetch_customers() or [])
    except Exception as exc:
        _LOG.exception("Job Database: could not load customers")
        st.error(f"Database error (customers): {exc}")
    try:
        estimates = list(fetch_estimates() or [])
    except Exception as exc:
        _LOG.exception("Job Database: could not load estimates")
        st.error(f"Database error (estimates): {exc}")

    customer_name_by_id: dict[str, str] = {
        str(c.get("id") or "").strip(): str(c.get("customer_name") or "").strip()
        for c in customers
        if str(c.get("id") or "").strip()
    }

    estimate_label_map: dict[str, str] = {}
    for e in estimates:
        eid = str(e.get("id") or "").strip()
        if not eid:
            continue
        ecust = str(e.get("customer_id") or "").strip()
        cn = customer_name_by_id.get(ecust, "")
        estimate_label_map[eid] = f"{e.get('quote_number', '')} | {cn} | {e.get('status', '')}"

    estimate_quote_by_id: dict[str, str] = {
        str(e.get("id")): str(e.get("quote_number") or "").strip()
        for e in estimates
        if e.get("id") is not None
    }

    contact_label_by_id = fetch_all_contact_labels(is_admin=is_admin)

    has_customer_location_column = jobs_has_customer_location_column()
    location_by_id: dict[str, dict[str, Any]] = {}
    if has_customer_location_column:
        try:
            from services.customer_locations import fetch_all_locations_indexed
        except ImportError:
            from app.services.customer_locations import fetch_all_locations_indexed  # type: ignore
        location_by_id = fetch_all_locations_indexed(admin_read=is_admin)

    # --- Load jobs ---
    jobs: list[dict[str, Any]] = []
    has_job_number_column = False
    try:
        jobs, has_job_number_column = fetch_jobs_for_job_database(limit=fetch_limit, admin_read=is_admin)
    except Exception as exc:
        _LOG.exception("Job Database: fetch_jobs_for_job_database failed")
        st.error(f"Database error (jobs): {exc}")
        try:
            jobs = list(fetch_jobs_with_order_fallback(limit=fetch_limit, use_admin=is_admin) or [])
            has_job_number_column = bool(jobs) and any("job_number" in (r or {}) for r in jobs)
            if jobs:
                st.info("Loaded jobs using a relaxed query (typed column list failed).")
        except Exception as exc2:
            _LOG.exception("Job Database: fallback fetch failed")
            st.error(f"Database error (jobs fallback): {exc2}")
            jobs = []

    if has_job_number_column:
        jobs = sort_jobs_by_number_then_name(jobs)
    else:
        jobs = sort_jobs_by_name(jobs)

    jobs_df = pd.DataFrame(jobs)
    _list_shell.empty()

    # --- Initialise routing state ---
    if KEY_VIEW_MODE not in st.session_state:
        st.session_state[KEY_VIEW_MODE] = "list"
    if KEY_SELECTED_ID not in st.session_state:
        st.session_state[KEY_SELECTED_ID] = None
    migrate_legacy_session()

    jvm = str(st.session_state.get(KEY_VIEW_MODE) or "list").strip().lower()
    sid = str(st.session_state.get(KEY_SELECTED_ID) or "").strip()

    # Guard: edit requires a selected job ID
    if jvm == "edit" and not sid:
        clear_job_mode()
        st.rerun()

    # --- Read-only detail view ---
    if jvm == "view" and sid:
        job_row = next((j for j in jobs if str(j.get("id")) == sid), None)
        if not job_row:
            st.error("That job could not be found.")
            clear_job_mode()
            st.rerun()
        est_row: dict[str, Any] | None = None
        if job_row.get("estimate_id"):
            eid_str = str(job_row["estimate_id"])
            est_row = next((e for e in estimates if str(e.get("id")) == eid_str), None)
            if not est_row:
                est_row = fetch_estimate_by_id(eid_str)
        inject_job_detail_view_page_css()
        try:
            from app.pages.job_database_detail_view import render_job_database_detail_view_page as _detail
        except ImportError:
            from pages.job_database_detail_view import render_job_database_detail_view_page as _detail  # type: ignore

        def _clear_detail() -> None:
            st.session_state[KEY_VIEW_MODE] = "list"
            st.session_state[KEY_SELECTED_ID] = None
            st.session_state.pop(KEY_JOB_MODE, None)
            st.session_state.pop(KEY_EDIT_ID, None)

        def _goto_edit(jid: str) -> None:
            st.session_state[KEY_VIEW_MODE] = "edit"
            st.session_state[KEY_SELECTED_ID] = str(jid)
            st.session_state[KEY_JOB_MODE] = "edit"
            st.session_state[KEY_EDIT_ID] = str(jid)
            st.session_state.pop("job_number_manual_input", None)

        _detail(
            job_row=job_row,
            has_job_number_column=has_job_number_column,
            has_customer_location_column=has_customer_location_column,
            customers=customers,
            customer_name_by_id=customer_name_by_id,
            estimate_label_map=estimate_label_map,
            estimate_quote_by_id=estimate_quote_by_id,
            estimate_detail=est_row,
            location_by_id=location_by_id,
            contact_label_by_id=contact_label_by_id,
            can_edit=can_edit,
            admin_read=is_admin,
            on_clear_view=_clear_detail,
            on_sync_edit=_goto_edit,
        )
        st.stop()

    # --- Sync legacy keys before rendering the panel ---
    sync_job_mode_from_view_state()

    jvm_panel = str(st.session_state.get(KEY_VIEW_MODE) or "list").strip().lower()
    sid_panel = str(
        st.session_state.get(KEY_SELECTED_ID) or st.session_state.get(KEY_EDIT_ID) or ""
    ).strip()
    panel_open = bool(
        (jvm_panel == "create" and can_edit)
        or (jvm_panel == "edit" and (can_edit or current_role() == "employee") and sid_panel)
    )

    # --- Create / Edit panel ---
    if panel_open:
        st.markdown('<span class="ips-job-detail-view-anchor"></span>', unsafe_allow_html=True)
        mode = "add" if jvm_panel == "create" else "edit"
        selected_job: dict[str, Any] | None = None
        estimate_detail: dict[str, Any] | None = None

        if mode == "edit":
            edit_id = st.session_state.get(KEY_SELECTED_ID) or st.session_state.get(KEY_EDIT_ID)
            if edit_id:
                selected_job = next((j for j in jobs if str(j.get("id")) == str(edit_id)), None)
            if not selected_job:
                st.error("Selected job could not be loaded. It may have been deleted.")
                clear_job_mode()
                st.rerun()
            if selected_job and selected_job.get("estimate_id"):
                eid_str = str(selected_job["estimate_id"])
                estimate_detail = next((e for e in estimates if str(e.get("id")) == eid_str), None)
                if not estimate_detail:
                    estimate_detail = fetch_estimate_by_id(eid_str)

        if st.button("← Back to Jobs", type="secondary", key="job_db_back_to_list"):
            clear_job_mode()
            st.rerun()

        if mode == "add":
            st.markdown("## Add job", unsafe_allow_html=True)
            st.caption("Standalone or estimate-linked — use the form below.")
        elif selected_job:
            jt = str(selected_job.get("job_name") or "").strip() or "Untitled job"
            jn = job_detail_display_number(selected_job, has_job_number_column=has_job_number_column)
            st.markdown(f"<h2 style='margin:0 0 0.25rem 0;color:#111827;'>{html.escape(jt)}</h2>", unsafe_allow_html=True)
            if jn:
                st.caption(f"Job # {jn}")

        render_job_form_panel(
            mode=mode,
            can_edit=can_edit,
            selected_job=selected_job,
            jobs=jobs,
            has_job_number_column=has_job_number_column,
            has_customer_location_column=has_customer_location_column,
            customers=customers,
            estimates=estimates,
            customer_name_by_id=customer_name_by_id,
            estimate_label_map=estimate_label_map,
            estimate_quote_by_id=estimate_quote_by_id,
            estimate_detail=estimate_detail,
            show_main_heading=False,
        )
        return

    # --- List view ---
    render_jobs_top_bar(can_edit=can_edit, estimates=estimates, estimate_label_map=estimate_label_map)

    render_jobs_list_section(
        jobs_df=jobs_df,
        jobs=jobs,
        has_job_number_column=has_job_number_column,
        customer_name_by_id=customer_name_by_id,
        estimate_label_map=estimate_label_map,
        estimate_quote_by_id=estimate_quote_by_id,
        contact_label_by_id=contact_label_by_id,
        location_by_id=location_by_id,
        customers=customers,
        can_edit=can_edit,
        is_admin=is_admin,
        fetch_limit=fetch_limit,
    )
