"""Jobs module (Phase 2) — list + detail panel."""

from __future__ import annotations

import html
from datetime import date

import streamlit as st

try:
    from app.components.job_actions import render_job_action_buttons
    from app.components.job_row_actions_ui import render_job_row_actions
    from app.components.job_status_ui import job_status_pill_html, render_job_status_badge_editor
    from app.components.jobs_page_layout import (
        close_jobs_filter_bar_shell,
        inject_jobs_page_layout_css,
        job_health_badge_html,
        render_jobs_filter_bar_shell,
        render_jobs_pagination_footer,
        render_jobs_row_click_bridge,
        render_jobs_summary_cards,
        render_jobs_table_pagination_header,
    )
    from app.components.job_ips_forms import render_job_ips_forms_tab
    from app.components.job_materials_ui import render_job_materials_tab
    from app.components.job_costing_tab import render_job_costing_tab
    from app.components.job_cost_summary_cards import render_job_cost_summary_cards
    from app.components.job_detail_layout import (
        close_job_detail_footer_shell,
        gather_job_detail_stats,
        inject_job_detail_layout_css,
        render_job_detail_activity_sidebar,
        render_job_detail_footer_shell,
        render_job_detail_header,
        render_job_detail_header_actions,
        render_job_detail_health_section,
        render_job_detail_metadata_row,
        render_job_detail_quick_stats,
    )
    from app.services.job_cost_transaction_service import (
        build_job_cost_summary,
        sync_all_sources_for_job,
    )
    from app.components.weekly_timesheet_builder import render_weekly_timesheet_builder
    from app.components.headers import render_page_brand_header
    from app.components.layout import render_filter_bar as layout_filter_bar
    from app.components.table_filters import (
        apply_column_filters,
        build_filter_options,
        clear_table_filters,
        render_table_header_cell,
    )
    from app.components.table_pagination import (
        paginate_rows,
        reset_table_page,
    )
    from app.pages._core._data import (
        customer_contact_select_options,
        customer_filter_options,
        customer_id_for_name,
        customer_location_select_options,
        employee_options,
        load_estimates,
        load_jobs,
        lookup_options,
        persist_job,
    )
    from app.pages._core._crud import apply_persist_feedback, is_demo_id
    from app.pages._core._session import select_key
    from app.pages.tasks import (
        clear_job_subjob_selection,
        on_job_detail_modal_open,
        render_job_linked_tasks_tab,
    )
    from app.components.quote_job_number_autofill import (
        clear_new_job_number_state,
        sync_new_job_number,
    )
    from app.styles import inject_jobs_module_css, inject_tasks_module_css
    from app.utils.formatting import fmt_date
    from app.utils.phone_helpers import format_phone_display
    from app.utils.field_context import (
        FIELD_EXPANDED_JOB_KEY,
        clear_field_expanded,
        field_expanded_id,
        inject_field_row_expand_css,
        is_field_context,
        is_field_mode,
        render_field_job_bar,
        set_field_job_id,
        toggle_field_expanded,
    )
except ImportError:
    from components.job_ips_forms import render_job_ips_forms_tab  # type: ignore
    from components.job_materials_ui import render_job_materials_tab  # type: ignore
    from components.job_costing_tab import render_job_costing_tab  # type: ignore
    from components.job_detail_layout import (  # type: ignore
        close_job_detail_footer_shell,
        gather_job_detail_stats,
        inject_job_detail_layout_css,
        render_job_detail_activity_sidebar,
        render_job_detail_footer_shell,
        render_job_detail_header,
        render_job_detail_header_actions,
        render_job_detail_health_section,
        render_job_detail_metadata_row,
        render_job_detail_quick_stats,
    )
    from components.job_cost_summary_cards import render_job_cost_summary_cards  # type: ignore
    from services.job_cost_transaction_service import (  # type: ignore
        build_job_cost_summary,
        sync_all_sources_for_job,
    )
    from components.job_row_actions_ui import render_job_row_actions  # type: ignore
    from components.job_status_ui import job_status_pill_html, render_job_status_badge_editor  # type: ignore
    from components.jobs_page_layout import (  # type: ignore
        close_jobs_filter_bar_shell,
        inject_jobs_page_layout_css,
        job_health_badge_html,
        render_jobs_filter_bar_shell,
        render_jobs_pagination_footer,
        render_jobs_row_click_bridge,
        render_jobs_summary_cards,
        render_jobs_table_pagination_header,
    )
    from components.job_actions import render_job_action_buttons  # type: ignore
    from components.weekly_timesheet_builder import render_weekly_timesheet_builder  # type: ignore
    from components.headers import render_page_brand_header  # type: ignore
    from components.layout import render_filter_bar as layout_filter_bar  # type: ignore
    from components.table_filters import (  # type: ignore
        apply_column_filters,
        build_filter_options,
        clear_table_filters,
        render_table_header_cell,
    )
    from components.table_pagination import (  # type: ignore
        paginate_rows,
        reset_table_page,
    )
    from pages._core._data import (  # type: ignore
        customer_contact_select_options,
        customer_filter_options,
        customer_id_for_name,
        customer_location_select_options,
        employee_options,
        load_estimates,
        load_jobs,
        lookup_options,
        persist_job,
    )
    from pages._core._crud import apply_persist_feedback, is_demo_id  # type: ignore
    from pages._core._session import select_key  # type: ignore
    from pages.tasks import (  # type: ignore
        clear_job_subjob_selection,
        on_job_detail_modal_open,
        render_job_linked_tasks_tab,
    )
    from components.quote_job_number_autofill import (  # type: ignore
        clear_new_job_number_state,
        sync_new_job_number,
    )
    from styles import inject_jobs_module_css, inject_tasks_module_css  # type: ignore
    from utils.formatting import fmt_date  # type: ignore
    from utils.field_context import (  # type: ignore
        FIELD_EXPANDED_JOB_KEY,
        clear_field_expanded,
        field_expanded_id,
        inject_field_row_expand_css,
        is_field_context,
        is_field_mode,
        render_field_job_bar,
        set_field_job_id,
        toggle_field_expanded,
    )

_SEL = select_key("jobs")
_TABLE_KEY = "jobs_list"
_JOBS_MODAL_KEY = "ips_jobs_detail_modal_id"


def _job_new_num_edited() -> None:
    st.session_state["job_new_num_manual"] = True


_JOB_TABS = [
    "Overview",
    "Scope",
    "Estimates",
    "Materials",
    "Equipment",
    "Job Costing",
    "Schedule",
    "Subjobs",
    "IPS Forms",
    "Weekly Timesheets",
    "Documents",
    "Photos",
    "Daily Updates",
    "Notes",
]
_FIELD_JOB_TABS = ["Overview", "Materials", "Subjobs", "Photos", "Daily Report"]


def _job_detail_tab_labels(job: dict) -> list[str]:
    """Dynamic tab labels with counts where existing data is available."""
    jid = str(job.get("id") or "").strip()
    open_subjobs = 0
    document_count = 0
    photo_count = 0
    weekly_ts_count = 0
    form_count = 0

    if jid:
        try:
            from app.services.tasks_service import get_tasks_by_job
        except ImportError:
            from services.tasks_service import get_tasks_by_job  # type: ignore
        try:
            closed = {"complete", "completed", "closed", "cancelled", "canceled", "duplicate"}
            open_subjobs = sum(
                1
                for task in get_tasks_by_job(jid, include_closed=True)
                if str(task.get("status") or "").strip().lower() not in closed
            )
        except Exception:
            open_subjobs = 0

        try:
            from app.services.job_documents import fetch_job_documents
        except ImportError:
            from services.job_documents import fetch_job_documents  # type: ignore
        try:
            document_count = len(fetch_job_documents(jid, admin=False, limit=500) or [])
        except Exception:
            document_count = 0

        try:
            from app.services.job_photos import fetch_job_photos
        except ImportError:
            from services.job_photos import fetch_job_photos  # type: ignore
        try:
            photo_count = len(fetch_job_photos(jid, admin=False, limit=500) or [])
        except Exception:
            photo_count = 0

        try:
            from app.services.weekly_job_timesheet_service import list_timesheets_for_job
        except ImportError:
            from services.weekly_job_timesheet_service import list_timesheets_for_job  # type: ignore
        try:
            weekly_ts_count = len(list_timesheets_for_job(jid) or [])
        except Exception:
            weekly_ts_count = 0

    def _count_label(name: str, count: int) -> str:
        return f"{name} ({count})" if count > 0 else name

    return [
        "Overview",
        _count_label("Subjobs", open_subjobs),
        "Schedule",
        _count_label("Weekly Timesheets", weekly_ts_count),
        "Job Costing",
        "Materials",
        "Equipment",
        _count_label("Documents", document_count),
        _count_label("Photos", photo_count),
        "IPS Forms" if form_count <= 0 else _count_label("IPS Forms", form_count),
        "Scope",
        "Estimates",
        "Daily Updates",
        "Notes",
    ]


def _enrich_job_cost_summary(job: dict, cost_summary: dict) -> dict:
    """Merge rollup fields; contract/estimate come from approved estimate helpers in build_job_cost_summary."""
    return dict(cost_summary)

SELECTED_JOB_KEY = "selected_job_id"
SHOW_MODAL_KEY = "show_job_detail_modal"
_ALL_JOB_IDS_KEY = "_ips_jobs_visible_ids"
CACHE_KEY = "_ips_jobs_modal_by_id"
JOB_DOC_UPLOAD_MODE_KEY = "job_detail_doc_upload_job_id"
JOB_DOC_PENDING_DELETE_ID_KEY = "job_detail_doc_pending_delete_id"
JOB_DOC_PENDING_DELETE_JOB_KEY = "job_detail_doc_pending_delete_job_id"
JOB_DAILY_UPDATE_ADD_MODE_KEY = "job_detail_daily_update_add_job_id"
_DAILY_UPDATE_STATUS_OPTS = ["Draft", "Open", "Submitted", "Closed"]
_JOB_DOC_UPLOAD_TYPES = ["pdf", "doc", "docx", "xls", "xlsx", "csv", "png", "jpg", "jpeg"]
_JOB_COLS = [0.32, 0.9, 2.05, 1.35, 1.05, 1.05, 1.05, 0.9, 0.8, 0.95, 1.05]
_JOB_HEADER_SPECS: list[tuple[str, str | None]] = [
    ("", None),
    ("JOB #", None),
    ("PROJECT / DESCRIPTION", None),
    ("CUSTOMER", "customer"),
    ("STATUS", "status"),
    ("CONTRACT VALUE", None),
    ("ACTUAL COST", None),
    ("PROFIT", None),
    ("MARGIN %", None),
    ("OPEN TASKS / SUBJOBS", None),
    ("ACTIONS", None),
]
_JOBS_DEFAULT_VIEW = "Active Jobs"
_JOBS_VIEW_OPTIONS = [
    "Active Jobs",
    "All Jobs",
    "Completed Jobs",
    "Cancelled Jobs",
    "Deleted/Archived Jobs",
]
_JOB_BAR_FILTER_FIELDS = ["customer", "supervisor", "status"]


def _normalize_job_status(raw: object) -> str:
    try:
        from app.services.jobs_service import normalize_job_status
    except ImportError:
        from services.jobs_service import normalize_job_status  # type: ignore
    return normalize_job_status(raw)


def _job_number(job: dict) -> str:
    for key in ("job_number", "number"):
        val = str(job.get(key) or "").strip()
        if val:
            return val
    return "—"


def _job_project(job: dict) -> str:
    for key in ("job_name", "project_name", "project_description", "description"):
        val = str(job.get(key) or "").strip()
        if val:
            return val
    return "—"


def _job_customer(job: dict) -> str:
    for key in ("customer_name", "customer"):
        val = str(job.get(key) or "").strip()
        if val:
            return val
    return "—"


def _job_supervisor(job: dict) -> str:
    for key in ("supervisor_name", "supervisor"):
        val = str(job.get(key) or "").strip()
        if val:
            return val
    return "—"


def _job_customer_location_id(job: dict) -> str:
    return str(job.get("customer_location_id") or job.get("location_id") or "").strip()


def _job_location(job: dict) -> str:
    for key in ("location_name", "location"):
        val = str(job.get(key) or "").strip()
        if val:
            return val
    loc_id = _job_customer_location_id(job)
    if loc_id:
        try:
            from app.services.job_from_estimate import _location_text_from_customer_location
        except ImportError:
            from services.job_from_estimate import _location_text_from_customer_location  # type: ignore
        label = _location_text_from_customer_location(loc_id)
        if label:
            return label
    return "—"


_JOB_COLUMN_FILTER_SPECS: list[tuple[str, object]] = [
    ("customer", _job_customer),
    ("supervisor", _job_supervisor),
    ("status", lambda r: _normalize_job_status(r.get("status"))),
]


def _job_status_pill_html(status: str) -> str:
    return job_status_pill_html(status)


def _money_cell(value: float, *, available: bool = True) -> str:
    if not available:
        return "—"
    if abs(float(value or 0)) < 0.005:
        return "—"
    return f"${float(value):,.2f}"


def _money_cell_class(value: float, *, available: bool = True) -> str:
    display = _money_cell(value, available=available)
    return " ips-jobs-money-empty" if display == "—" else ""


def _pct_cell(value: float) -> str:
    return f"{float(value or 0):,.1f}%"


def _load_open_subjob_counts() -> dict[str, int]:
    try:
        from app.services.tasks_service import count_open_subjobs_by_job_id
    except ImportError:
        from services.tasks_service import count_open_subjobs_by_job_id  # type: ignore
    try:
        return count_open_subjobs_by_job_id()
    except Exception:
        return {}


def _job_open_subjobs_count(job: dict, *, subjob_counts: dict[str, int] | None = None) -> int:
    jid = str(job.get("id") or "").strip()
    if not jid:
        return 0
    if subjob_counts is not None:
        return int(subjob_counts.get(jid, 0))
    try:
        from app.services.tasks_service import get_tasks_by_job
    except ImportError:
        from services.tasks_service import get_tasks_by_job  # type: ignore
    try:
        closed = {"complete", "completed", "closed", "cancelled", "canceled", "duplicate"}
        return sum(
            1
            for task in get_tasks_by_job(jid, include_closed=True)
            if str(task.get("status") or "").strip().lower() not in closed
        )
    except Exception:
        return 0


def _compute_job_list_cost_fields(job: dict, *, sync_if_empty: bool = False) -> dict[str, float | dict | bool]:
    """Costing snapshot for list/detail; ledger backfill only when ``sync_if_empty``."""
    defaults: dict[str, float | dict | bool] = {
        "contract_value": 0.0,
        "actual_cost": 0.0,
        "profit": 0.0,
        "margin_pct": 0.0,
        "raw_summary": {},
        "has_contract": False,
        "has_actual": False,
    }
    jid = str(job.get("id") or "").strip()
    summary: dict = {}
    try:
        summary = build_job_cost_summary(job)
        if sync_if_empty and jid and int(summary.get("transaction_count") or 0) == 0:
            sync_all_sources_for_job(jid)
            summary = build_job_cost_summary(job)
        summary = _enrich_job_cost_summary(job, summary)
        defaults["contract_value"] = float(summary.get("contract_value") or 0)
        defaults["actual_cost"] = float(summary.get("actual_cost") or 0)
        defaults["profit"] = float(summary.get("profit") or 0)
        defaults["margin_pct"] = float(summary.get("margin_pct") or 0)
        defaults["raw_summary"] = summary
    except Exception:
        try:
            defaults["contract_value"] = float(job.get("awarded_amount") or job.get("contract_value") or 0)
        except (TypeError, ValueError):
            defaults["contract_value"] = 0.0
    txn_count = int(summary.get("transaction_count") or 0) if isinstance(summary, dict) else 0
    defaults["has_contract"] = bool(summary.get("has_contract_value")) if isinstance(summary, dict) else False
    defaults["has_actual"] = txn_count > 0 or float(defaults["actual_cost"]) > 0
    return defaults


def _build_jobs_list_cost_cache(jobs: list[dict]) -> dict[str, dict[str, float | dict | bool]]:
    cache: dict[str, dict[str, float | dict | bool]] = {}
    for job in jobs:
        jid = str(job.get("id") or "").strip()
        if not jid or jid in cache:
            continue
        cache[jid] = _compute_job_list_cost_fields(job, sync_if_empty=False)
    return cache


def _job_list_cost_fields(
    job: dict,
    *,
    cost_cache: dict[str, dict[str, float | dict | bool]] | None = None,
) -> dict[str, float | dict | bool]:
    jid = str(job.get("id") or "").strip()
    if cost_cache is not None and jid and jid in cost_cache:
        return cost_cache[jid]
    return _compute_job_list_cost_fields(job, sync_if_empty=False)


def _jobs_summary_counts(
    rows: list[dict],
    cost_cache: dict[str, dict[str, float | dict | bool]],
    subjob_counts: dict[str, int],
) -> dict[str, float | int]:
    counts: dict[str, float | int] = {
        "total": len(rows),
        "active": 0,
        "awarded": 0,
        "pending": 0,
        "draft": 0,
        "open_subjobs": 0,
        "total_contract": 0.0,
        "total_actual": 0.0,
        "has_any_contract": False,
        "has_any_actual": False,
    }
    for job in rows:
        status = _normalize_job_status(job.get("status"))
        if status == "Active":
            counts["active"] += 1
        elif status == "Awarded":
            counts["awarded"] += 1
        elif status == "Pending":
            counts["pending"] += 1
        elif status == "Draft":
            counts["draft"] += 1
        jid = str(job.get("id") or "").strip()
        counts["open_subjobs"] += _job_open_subjobs_count(job, subjob_counts=subjob_counts)
        costs = cost_cache.get(jid) if jid else None
        if not isinstance(costs, dict):
            continue
        counts["total_contract"] = float(counts["total_contract"]) + float(costs["contract_value"])
        counts["total_actual"] = float(counts["total_actual"]) + float(costs["actual_cost"])
        if costs.get("has_contract"):
            counts["has_any_contract"] = True
        if costs.get("has_actual"):
            counts["has_any_actual"] = True
    return counts


def _patch_job_cache_status(job_id: str, new_status: str) -> None:
    jid = str(job_id or "").strip()
    if not jid:
        return
    cache = st.session_state.get(CACHE_KEY)
    if isinstance(cache, dict) and jid in cache and isinstance(cache[jid], dict):
        cache[jid] = {**cache[jid], "status": new_status}
        st.session_state[CACHE_KEY] = cache


def _open_job_edit_from_list(job: dict) -> None:
    _set_job_edit_mode(job)


def _on_job_status_updated(job_id: str, new_status: str) -> None:
    _patch_job_cache_status(job_id, new_status)


def _apply_jobs_view_filter(rows: list[dict], view: str) -> list[dict]:
    view_norm = str(view or "Active Jobs").strip()
    if view_norm == "All Jobs":
        return rows
    if view_norm == "Deleted/Archived Jobs":
        return [
            r
            for r in rows
            if bool(r.get("is_deleted"))
            or _normalize_job_status(r.get("status")) in {"Deleted", "Archived"}
        ]
    alive = [
        r
        for r in rows
        if not bool(r.get("is_deleted"))
        and _normalize_job_status(r.get("status")) not in {"Deleted", "Archived"}
    ]
    if view_norm == "Completed Jobs":
        return [r for r in alive if _normalize_job_status(r.get("status")) in {"Completed", "Closed"}]
    if view_norm == "Cancelled Jobs":
        return [r for r in alive if _normalize_job_status(r.get("status")) == "Cancelled"]
    return [
        r
        for r in alive
        if _normalize_job_status(r.get("status")) not in {"Completed", "Closed", "Cancelled"}
    ]


def _apply_jobs_search_filter(rows: list[dict], q: str) -> list[dict]:
    query = str(q or "").strip()
    if not query:
        return rows
    ql = query.lower()
    return [
        r
        for r in rows
        if ql in _job_number(r).lower()
        or ql in _job_project(r).lower()
        or ql in _job_customer(r).lower()
        or ql in _job_supervisor(r).lower()
    ]


def _filter_jobs(
    rows: list[dict],
    *,
    view: str | None = None,
    q: str = "",
) -> list[dict]:
    view_val = str(view or st.session_state.get("jobs_view") or _JOBS_DEFAULT_VIEW).strip()
    out = _apply_jobs_view_filter(rows, view_val)
    out = _apply_jobs_search_filter(out, q)
    return apply_column_filters(out, _TABLE_KEY, _JOB_COLUMN_FILTER_SPECS)


def _job_select_key(job_id: str) -> str:
    return f"job_select_{job_id}"


def _clear_job_selection(job_ids: list[str] | None = None) -> None:
    st.session_state[SELECTED_JOB_KEY] = None
    st.session_state[SHOW_MODAL_KEY] = False
    ids = list(job_ids or [])
    for jid in ids:
        st.session_state[_job_select_key(jid)] = False
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and key.startswith("job_select_"):
            st.session_state[key] = False
    st.session_state.pop(_SEL, None)
    st.session_state.pop(_JOBS_MODAL_KEY, None)


def _on_job_checkbox_change(job_id: str, all_job_ids: list[str]) -> None:
    key = _job_select_key(job_id)
    if st.session_state.get(key):
        for jid in all_job_ids:
            if jid != job_id:
                st.session_state[_job_select_key(jid)] = False
        st.session_state[SELECTED_JOB_KEY] = job_id
        st.session_state[SHOW_MODAL_KEY] = True
        cache = st.session_state.get(CACHE_KEY) or {}
        job = cache.get(job_id) if isinstance(cache, dict) else None
        _open_jobs_detail_modal(job_id, job)
    elif st.session_state.get(SELECTED_JOB_KEY) == job_id:
        st.session_state[SELECTED_JOB_KEY] = None
        st.session_state[SHOW_MODAL_KEY] = False


def _clear_jobs_detail_modal() -> None:
    job_ids = st.session_state.get(_ALL_JOB_IDS_KEY) or []
    _clear_job_selection([str(jid) for jid in job_ids])
    clear_job_subjob_selection()
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and key.startswith("job_edit_mode_"):
            st.session_state.pop(key, None)
    st.session_state.pop(JOB_DOC_UPLOAD_MODE_KEY, None)
    st.session_state.pop(JOB_DOC_PENDING_DELETE_ID_KEY, None)
    st.session_state.pop(JOB_DOC_PENDING_DELETE_JOB_KEY, None)


def _render_custom_jobs_table(
    filtered: list[dict],
    *,
    filter_options: dict[str, list[str]],
    cost_cache: dict[str, dict[str, float | dict | bool]],
    subjob_counts: dict[str, int],
) -> list[str]:
    if not filtered:
        st.info("No jobs match your filters.")
        st.session_state[_ALL_JOB_IDS_KEY] = []
        return []

    all_job_ids = [str(j.get("id") or "").strip() for j in filtered if str(j.get("id") or "").strip()]
    st.session_state[_ALL_JOB_IDS_KEY] = all_job_ids

    with st.container(key="jobs_table_wrap"):
        st.markdown('<div class="ips-jobs-table-wrap jobs-table">', unsafe_allow_html=True)

        header_cols = st.columns(_JOB_COLS, gap="small", vertical_alignment="center")
        for col, (label, field) in zip(header_cols, _JOB_HEADER_SPECS):
            with col:
                if field:
                    render_table_header_cell(
                        label,
                        table_key=_TABLE_KEY,
                        filter_field=field,
                        filter_options=filter_options.get(field, []),
                        base_class="ips-jobs-header-row ips-jobs-cell",
                    )
                else:
                    render_table_header_cell(
                        label,
                        base_class="ips-jobs-header-row ips-jobs-cell",
                    )

        for job in filtered:
            jid = str(job.get("id") or "").strip()
            if not jid:
                continue

            job_no = _job_number(job)
            project = _job_project(job)
            customer = _job_customer(job)
            status = _normalize_job_status(job.get("status"))
            costs = _job_list_cost_fields(job, cost_cache=cost_cache)
            contract_val = float(costs["contract_value"])
            actual_val = float(costs["actual_cost"])
            profit_val = float(costs["profit"])
            margin_val = float(costs["margin_pct"])
            open_subjobs = _job_open_subjobs_count(job, subjob_counts=subjob_counts)
            raw_summary = costs.get("raw_summary")
            health_html = ""
            if isinstance(raw_summary, dict) and raw_summary:
                health_html = job_health_badge_html(raw_summary)
            field_mode = is_field_context()
            expanded = field_mode and field_expanded_id(FIELD_EXPANDED_JOB_KEY) == jid

            cols = st.columns(_JOB_COLS, gap="small", vertical_alignment="center")

            with cols[0]:
                st.markdown(
                    f'<span class="ips-jobs-row-marker ips-jobs-table-row" data-row-id="{html.escape(jid, quote=True)}" aria-hidden="true"></span>',
                    unsafe_allow_html=True,
                )
                if field_mode:
                    if st.button(
                        "▾" if expanded else "▸",
                        key=f"job_expand_{jid}",
                        help="Expand job details",
                    ):
                        toggle_field_expanded(FIELD_EXPANDED_JOB_KEY, jid)
                        set_field_job_id(jid)
                        st.rerun()
                else:
                    st.checkbox(
                        "",
                        key=_job_select_key(jid),
                        label_visibility="collapsed",
                        on_change=_on_job_checkbox_change,
                        args=(jid, all_job_ids),
                    )

            with cols[1]:
                num_label = job_no if job_no and job_no != "—" else "View job"
                st.markdown(
                    f'<div class="ips-jobs-number-link job-number-link">'
                    f'<span class="ips-jobs-number-text" title="{html.escape(num_label, quote=True)}">'
                    f"{html.escape(num_label)}</span></div>",
                    unsafe_allow_html=True,
                )

            with cols[2]:
                st.markdown(
                    f'<div class="ips-jobs-title ips-jobs-cell">{html.escape(project)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[3]:
                st.markdown(
                    f'<div class="ips-jobs-cell">{html.escape(customer)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[4]:
                status_html = _job_status_pill_html(status)
                if health_html:
                    status_html = f'{status_html}{health_html}'
                st.markdown(status_html, unsafe_allow_html=True)

            profit_cls = ""
            has_contract = bool(costs.get("has_contract"))
            has_actual = bool(costs.get("has_actual"))
            has_profit_data = has_contract
            if has_profit_data:
                if profit_val > 0:
                    profit_cls = " ips-jobs-money-positive"
                elif profit_val < 0:
                    profit_cls = " ips-jobs-money-negative"
            with cols[5]:
                contract_cls = _money_cell_class(contract_val, available=has_contract)
                st.markdown(
                    f'<div class="ips-jobs-money ips-jobs-cell{contract_cls}">{html.escape(_money_cell(contract_val, available=has_contract))}</div>',
                    unsafe_allow_html=True,
                )
            with cols[6]:
                actual_cls = _money_cell_class(actual_val, available=has_actual)
                st.markdown(
                    f'<div class="ips-jobs-money ips-jobs-cell{actual_cls}">{html.escape(_money_cell(actual_val, available=has_actual))}</div>',
                    unsafe_allow_html=True,
                )
            with cols[7]:
                profit_display_cls = _money_cell_class(profit_val, available=has_profit_data)
                st.markdown(
                    f'<div class="ips-jobs-money ips-jobs-cell{profit_cls}{profit_display_cls}">{html.escape(_money_cell(profit_val, available=has_profit_data))}</div>',
                    unsafe_allow_html=True,
                )
            with cols[8]:
                margin_display = _pct_cell(margin_val) if has_contract else "—"
                margin_cls = profit_cls if has_contract else " ips-jobs-money-empty"
                st.markdown(
                    f'<div class="ips-jobs-money ips-jobs-cell{margin_cls}">{html.escape(margin_display)}</div>',
                    unsafe_allow_html=True,
                )
            with cols[9]:
                st.markdown(
                    f'<div class="ips-jobs-cell">{open_subjobs:,}</div>',
                    unsafe_allow_html=True,
                )
            with cols[10]:
                st.markdown(
                    '<span class="ips-jobs-actions-cell ips-jobs-actions-toolbar job-actions-cell" aria-hidden="true"></span>',
                    unsafe_allow_html=True,
                )
                render_job_row_actions(
                    job,
                    on_open=_open_jobs_detail_modal,
                    on_edit=_open_job_edit_from_list,
                    on_status_updated=_on_job_status_updated,
                )

            if expanded:
                st.markdown('<div class="ips-field-row-expand">', unsafe_allow_html=True)
                _render_field_job_detail_tabs(job)
                if st.button("All job details", key=f"job_full_modal_{jid}", use_container_width=True):
                    _open_jobs_detail_modal(jid, job)
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    if not is_field_context():
        jobs_by_id = {
            str(j.get("id") or "").strip(): j
            for j in filtered
            if str(j.get("id") or "").strip()
        }
        picked = render_jobs_row_click_bridge()
        if picked:
            open_id = str(picked).strip()
            open_job = jobs_by_id.get(open_id)
            if open_job:
                _open_jobs_detail_modal(open_id, open_job)
                st.rerun()

    return all_job_ids


def _job_session_key(job: dict) -> str:
    raw = str(job.get("id") or job.get("job_number") or "job").strip()
    safe = "".join(ch if ch.isalnum() else "_" for ch in raw)
    return safe or "job"


def _job_edit_mode_key(job: dict) -> str:
    return f"job_edit_mode_{_job_session_key(job)}"


def _set_job_view_mode(job: dict) -> None:
    st.session_state[_job_edit_mode_key(job)] = False


def _set_job_edit_mode(job: dict) -> None:
    st.session_state[_job_edit_mode_key(job)] = True
    _seed_job_edit_form(job)


def _as_date(value: object) -> date | None:
    if isinstance(value, date):
        return value
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _supervisor_options(job: dict) -> list[str]:
    opts = employee_options(include_blank=True)
    cur = str(job.get("supervisor") or "").strip()
    if cur and cur not in opts:
        opts = [cur, *opts]
    return opts


def _location_options(job: dict) -> list[str]:
    """Legacy free-text location fallback when customer site FK is unavailable."""
    opts = lookup_options("locations")
    cur = str(job.get("location") or "").strip()
    if cur and cur not in opts:
        opts = [cur, *opts]
    return opts or ([cur] if cur else ["—"])


def _customer_location_select(
    *,
    customer_name: str,
    session_key: str,
    prev_customer_key: str,
    initial_location_id: str = "",
) -> str:
    cust = str(customer_name or "").strip()
    if st.session_state.get(prev_customer_key) != cust:
        st.session_state.pop(session_key, None)
        st.session_state[prev_customer_key] = cust
    cid = customer_id_for_name(cust)
    if not cust or not cid:
        st.selectbox("Location", ["— Select customer first —"], disabled=True, key=session_key)
        return ""
    pairs = customer_location_select_options(cid)
    if not pairs:
        st.warning("Add a customer location before assigning contacts/jobs.")
        st.selectbox("Location", ["— No locations —"], disabled=True, key=session_key)
        return ""
    labels = ["— Select location —", *[label for label, _ in pairs]]
    ids = ["", *[loc_id for _, loc_id in pairs]]
    if session_key not in st.session_state and initial_location_id:
        try:
            st.session_state[session_key] = ids.index(initial_location_id)
        except ValueError:
            st.session_state[session_key] = 0
    idx = st.selectbox("Location", range(len(labels)), format_func=lambda i: labels[i], key=session_key)
    return str(ids[int(idx)])


def _customer_contact_select(
    *,
    customer_name: str,
    location_id: str,
    session_key: str,
    prev_customer_key: str,
    prev_location_key: str,
    initial_contact_id: str = "",
) -> str:
    cust = str(customer_name or "").strip()
    loc_id = str(location_id or "").strip()
    if st.session_state.get(prev_customer_key) != cust:
        st.session_state.pop(session_key, None)
        st.session_state[prev_customer_key] = cust
    if st.session_state.get(prev_location_key) != loc_id:
        st.session_state.pop(session_key, None)
        st.session_state[prev_location_key] = loc_id
    cid = customer_id_for_name(cust)
    if not cust or not cid:
        st.selectbox("Contact", ["— Select customer first —"], disabled=True, key=session_key)
        return ""
    if not loc_id:
        st.selectbox("Contact", ["— Select location first —"], disabled=True, key=session_key)
        return ""
    pairs = customer_contact_select_options(cid, loc_id)
    if not pairs:
        st.selectbox("Contact", ["— No contacts for this location —"], disabled=True, key=session_key)
        return ""
    labels = ["— Select contact —", *[label for label, _ in pairs]]
    ids = ["", *[contact_id for _, contact_id in pairs]]
    if session_key not in st.session_state and initial_contact_id:
        try:
            st.session_state[session_key] = ids.index(initial_contact_id)
        except ValueError:
            st.session_state[session_key] = 0
    idx = st.selectbox("Contact", range(len(labels)), format_func=lambda i: labels[i], key=session_key)
    return str(ids[int(idx)])


def _seed_job_edit_form(job: dict) -> None:
    job_key = _job_session_key(job)
    st.session_state[f"job_edit_num_{job_key}"] = str(job.get("job_number") or "")
    st.session_state[f"job_edit_name_{job_key}"] = str(job.get("job_name") or "")
    st.session_state[f"job_edit_cust_{job_key}"] = str(job.get("customer") or "")
    st.session_state.pop(f"job_edit_location_{job_key}", None)
    st.session_state.pop(f"job_edit_contact_{job_key}", None)
    st.session_state.pop(f"job_edit_cust_prev_{job_key}", None)
    st.session_state.pop(f"job_edit_loc_prev_{job_key}", None)
    st.session_state[f"job_edit_status_{job_key}"] = str(job.get("status") or "Draft")
    st.session_state[f"job_edit_sup_{job_key}"] = str(job.get("supervisor") or "")
    st.session_state[f"job_edit_loc_{job_key}"] = str(job.get("location") or "")
    st.session_state[f"job_edit_start_{job_key}"] = _as_date(job.get("start_date"))
    st.session_state[f"job_edit_end_{job_key}"] = _as_date(job.get("end_date"))
    st.session_state[f"job_edit_prog_{job_key}"] = int(job.get("progress") or 0)
    st.session_state[f"job_edit_scope_{job_key}"] = str(job.get("scope") or job.get("description") or "")
    st.session_state[f"job_edit_notes_{job_key}"] = str(job.get("notes") or "")


def _open_jobs_detail_modal(job_id: str, _job: dict | None = None) -> None:
    jid = str(job_id or "").strip()
    if not jid:
        return
    on_job_detail_modal_open(jid)
    st.session_state[SELECTED_JOB_KEY] = jid
    st.session_state[SHOW_MODAL_KEY] = True
    st.session_state[_SEL] = jid
    st.session_state[_JOBS_MODAL_KEY] = jid
    if isinstance(_job, dict):
        st.session_state[_job_edit_mode_key(_job)] = False
    else:
        st.session_state[f"job_edit_mode_{''.join(ch if ch.isalnum() else '_' for ch in jid) or 'job'}"] = False


def _safe_value(value: object, fallback: str = "—") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback


def _safe_key(value: object) -> str:
    return html.escape(_safe_value(value, ""))


def _status_class(status: object) -> str:
    raw = _safe_value(status, "").lower()
    aliases = {
        "draft": "draft",
        "active": "active",
        "awarded": "awarded",
        "approved": "approved",
        "completed": "completed",
        "complete": "completed",
        "pending": "pending",
        "scheduled": "scheduled",
        "on hold": "pending",
        "cancelled": "danger",
        "canceled": "danger",
        "archived": "draft",
        "estimate pending": "pending",
        "closed": "completed",
    }
    slug = aliases.get(raw, "draft")
    return f"ips-pill ips-pill-{slug}"


def _status_pill(status: object) -> str:
    label = _safe_value(status)
    return f'<span class="{_status_class(status)}">{html.escape(label)}</span>'


def _detail_field(label: str, value: object, *, html_value: str | None = None) -> str:
    rendered = html_value if html_value is not None else html.escape(_safe_value(value))
    return (
        f'<div class="ips-detail-field">'
        f'<span class="ips-detail-label">{html.escape(label)}</span>'
        f'<span class="ips-detail-value">{rendered}</span>'
        f"</div>"
    )


def _dialog_meta_card(label: str, value: object) -> str:
    return (
        f'<div class="ips-dialog-meta-card">'
        f'<div class="ips-dialog-meta-label">{html.escape(label)}</div>'
        f'<div class="ips-dialog-meta-value">{html.escape(_safe_value(value))}</div>'
        f"</div>"
    )


def _dialog_card(title: str, body_html: str) -> str:
    return (
        f'<div class="ips-dialog-card">'
        f'<div class="ips-dialog-card-title">{html.escape(title)}</div>'
        f"{body_html}"
        f"</div>"
    )


def _schedule_summary(job: dict) -> str:
    start = fmt_date(job.get("start_date"))
    end = fmt_date(job.get("end_date"))
    if start == "—" and end == "—":
        return "—"
    if end == "—":
        return start
    if start == "—":
        return end
    return f"{start} – {end}"


def _job_subjob_select_options(job_id: str) -> tuple[list[str], dict[str, str]]:
    """Return subjob labels and label→task id map for optional daily update linking."""
    labels = ["— None —"]
    label_to_id: dict[str, str] = {}
    jid = str(job_id or "").strip()
    if not jid:
        return labels, label_to_id
    try:
        from app.services.tasks_service import get_tasks_by_job
    except ImportError:
        from services.tasks_service import get_tasks_by_job  # type: ignore
    try:
        for task in get_tasks_by_job(jid, include_closed=True):
            tid = str(task.get("id") or "").strip()
            if not tid:
                continue
            title = str(task.get("title") or "").strip() or "Subjob"
            task_no = str(task.get("task_number") or task.get("hazard_number") or "").strip()
            label = f"{task_no} — {title}" if task_no else title
            if label in label_to_id:
                continue
            labels.append(label)
            label_to_id[label] = tid
    except Exception:
        pass
    return labels, label_to_id


def _job_daily_update_add_active(job_id: str) -> bool:
    return str(st.session_state.get(JOB_DAILY_UPDATE_ADD_MODE_KEY) or "") == str(job_id or "").strip()


def _set_job_daily_update_add(job_id: str, active: bool) -> None:
    jid = str(job_id or "").strip()
    if active and jid:
        st.session_state[JOB_DAILY_UPDATE_ADD_MODE_KEY] = jid
    elif st.session_state.get(JOB_DAILY_UPDATE_ADD_MODE_KEY) == jid:
        st.session_state.pop(JOB_DAILY_UPDATE_ADD_MODE_KEY, None)


def _render_job_daily_update_add_form(job: dict) -> None:
    jid = str(job.get("id") or "").strip()
    if not jid:
        return
    job_key = _job_session_key(job)
    pk = f"job_daily_upd_{job_key}"
    subjob_labels, _ = _job_subjob_select_options(jid)
    author_name = _current_document_uploader_name()

    st.markdown(
        _dialog_card(
            "Add Daily Update",
            '<p style="margin:0;font-size:0.875rem;color:#64748b;">'
            "Record field work performed for this job.</p>",
        ),
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        st.date_input("Date", value=date.today(), key=f"{pk}_date", format="MM/DD/YYYY")
    with c2:
        st.selectbox("Status", _DAILY_UPDATE_STATUS_OPTS, index=0, key=f"{pk}_status")

    st.text_input("Summary", key=f"{pk}_summary", placeholder="Brief title for this update")
    st.text_area(
        "Daily Update",
        key=f"{pk}_details",
        height=140,
        placeholder="Describe work performed, progress, issues, and next steps…",
    )
    st.selectbox("Linked Subjob", subjob_labels, key=f"{pk}_subjob")

    if author_name:
        st.caption(f"Created by: {author_name}")

    btn_save, btn_cancel = st.columns(2, gap="small")
    with btn_save:
        if st.button("Save Daily Update", type="primary", key=f"{pk}_save", use_container_width=True):
            summary = str(st.session_state.get(f"{pk}_summary") or "").strip()
            details = str(st.session_state.get(f"{pk}_details") or "").strip()
            if not summary and not details:
                st.warning("Enter a summary or daily update details before saving.")
            else:
                try:
                    from app.services.job_updates_service import (
                        create_job_daily_update,
                        daily_updates_table_available,
                    )
                except ImportError:
                    from services.job_updates_service import (  # type: ignore
                        create_job_daily_update,
                        daily_updates_table_available,
                    )
                if not daily_updates_table_available(force=True):
                    st.error(
                        "Daily updates are not available yet. Run the job_daily_updates database migration."
                    )
                else:
                    update_day = st.session_state.get(f"{pk}_date")
                    if not isinstance(update_day, date):
                        update_day = date.today()
                    status = str(st.session_state.get(f"{pk}_status") or "Draft").strip()
                    subjob = str(st.session_state.get(f"{pk}_subjob") or "").strip()
                    note_lines: list[str] = []
                    if status:
                        note_lines.append(f"Status: {status}")
                    if subjob and subjob != "— None —":
                        note_lines.append(f"Linked subjob: {subjob}")
                    try:
                        from app.auth import current_profile
                    except ImportError:
                        from auth import current_profile  # type: ignore
                    profile = current_profile() or {}
                    payload: dict[str, object] = {
                        "job_id": jid,
                        "update_date": update_day.isoformat(),
                        "summary": summary,
                        "work_performed": details,
                        "notes": "\n".join(note_lines),
                        "supervisor_name": author_name or None,
                        "employee_name": author_name or None,
                        "created_by": profile.get("id"),
                    }
                    emp_id = str(profile.get("employee_id") or "").strip()
                    if emp_id:
                        payload["employee_id"] = emp_id
                    try:
                        create_job_daily_update(payload)
                        _set_job_daily_update_add(jid, False)
                        st.success("Daily update saved.")
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))
    with btn_cancel:
        if st.button("Cancel", key=f"{pk}_cancel", use_container_width=True):
            _set_job_daily_update_add(jid, False)
            st.rerun()


def _job_subjob_label_map(job_id: str) -> dict[str, str]:
    """Map IPS subjob/task ids to display titles for job-level media tabs."""
    jid = str(job_id or "").strip()
    if not jid:
        return {}
    try:
        from app.services.tasks_service import get_tasks_by_job
    except ImportError:
        from services.tasks_service import get_tasks_by_job  # type: ignore
    try:
        return {
            str(t.get("id") or "").strip(): str(t.get("title") or "").strip()
            for t in get_tasks_by_job(jid, include_closed=True)
            if str(t.get("id") or "").strip()
        }
    except Exception:
        return {}


def _job_doc_upload_active(job_id: str) -> bool:
    return str(st.session_state.get(JOB_DOC_UPLOAD_MODE_KEY) or "") == str(job_id or "").strip()


def _set_job_doc_upload(job_id: str, active: bool) -> None:
    jid = str(job_id or "").strip()
    if active and jid:
        st.session_state[JOB_DOC_UPLOAD_MODE_KEY] = jid
    elif st.session_state.get(JOB_DOC_UPLOAD_MODE_KEY) == jid:
        st.session_state.pop(JOB_DOC_UPLOAD_MODE_KEY, None)


def _current_document_uploader_name() -> str:
    try:
        from app.auth import current_profile
    except ImportError:
        from auth import current_profile  # type: ignore
    prof = current_profile() or {}
    return str(prof.get("full_name") or prof.get("name") or prof.get("email") or "").strip()


def _render_job_document_upload_form(job: dict) -> None:
    jid = str(job.get("id") or "").strip()
    if not jid:
        return
    job_key = _job_session_key(job)
    pk = f"job_doc_upload_{job_key}"
    admin = _field_admin_read()

    st.markdown(
        _dialog_card(
            "Upload Documents",
            '<p style="margin:0;font-size:0.875rem;color:#64748b;">'
            "Attach one or more files to this job. Supported: PDF, Word, Excel, CSV, and common images.</p>",
        ),
        unsafe_allow_html=True,
    )
    st.file_uploader(
        "Choose documents",
        type=_JOB_DOC_UPLOAD_TYPES,
        accept_multiple_files=True,
        key=f"{pk}_file",
        label_visibility="collapsed",
    )
    st.text_input(
        "Document title (optional, single file only)",
        key=f"{pk}_title",
        placeholder="Defaults to file name when uploading one file",
    )
    st.text_input("Document type / category", value="Job Document", key=f"{pk}_type")
    st.text_area("Notes (optional)", key=f"{pk}_notes", height=80)
    btn_upload, btn_cancel = st.columns(2, gap="small")
    with btn_upload:
        if st.button("Upload", type="primary", key=f"{pk}_save", use_container_width=True):
            raw = st.session_state.get(f"{pk}_file")
            files = raw if isinstance(raw, list) else ([raw] if raw else [])
            if not files:
                st.warning("Choose at least one document to upload.")
            else:
                try:
                    from app.services.asset_document_util import guess_document_content_type
                    from app.services.job_documents import upload_job_document
                except ImportError:
                    from services.asset_document_util import guess_document_content_type  # type: ignore
                    from services.job_documents import upload_job_document  # type: ignore
                title_override = str(st.session_state.get(f"{pk}_title") or "").strip()
                doc_type = str(st.session_state.get(f"{pk}_type") or "Job Document")
                notes = str(st.session_state.get(f"{pk}_notes") or "")
                uploaded = 0
                errors: list[str] = []
                for i, up in enumerate(files):
                    if up is None:
                        continue
                    data = up.getvalue()
                    raw_name = str(getattr(up, "name", "") or f"document_{i + 1}")
                    if not data:
                        errors.append(f"{raw_name}: empty file")
                        continue
                    file_name = title_override if len(files) == 1 and title_override else raw_name
                    ctype = guess_document_content_type(raw_name, str(getattr(up, "type", "") or ""))
                    try:
                        upload_job_document(
                            job_id=jid,
                            file_data=data,
                            file_name=file_name,
                            content_type=ctype,
                            uploaded_by=_current_document_uploader_name(),
                            doc_type=doc_type,
                            notes=notes,
                            admin=admin,
                        )
                        uploaded += 1
                    except Exception as exc:
                        errors.append(f"{raw_name}: {exc}")
                for err in errors:
                    st.error(err)
                if uploaded:
                    _set_job_doc_upload(jid, False)
                    st.success(f"Uploaded {uploaded} document(s).")
                    st.rerun()
    with btn_cancel:
        if st.button("Cancel", key=f"{pk}_cancel", use_container_width=True):
            _set_job_doc_upload(jid, False)
            st.rerun()


def _clear_job_doc_pending_delete() -> None:
    st.session_state.pop(JOB_DOC_PENDING_DELETE_ID_KEY, None)
    st.session_state.pop(JOB_DOC_PENDING_DELETE_JOB_KEY, None)


def _handle_delete_job_document(*, doc_id: str, job_id: str, admin: bool) -> None:
    did = str(doc_id or "").strip()
    jid = str(job_id or "").strip()
    if not did or not jid:
        return
    try:
        from app.services.job_documents import delete_job_document
    except ImportError:
        from services.job_documents import delete_job_document  # type: ignore
    try:
        delete_job_document(did, job_id=jid, admin=admin)
    except Exception as exc:
        st.error(str(exc))
        return
    _clear_job_doc_pending_delete()
    st.success("Document deleted.")
    st.rerun()


def _render_job_document_delete_confirm(*, doc: dict, job_id: str, admin: bool) -> None:
    did = str(doc.get("id") or "").strip()
    name = str(doc.get("file_name") or doc.get("name") or "Document").strip() or "Document"
    safe_name = html.escape(name)
    with st.container(key=f"job_doc_delete_confirm_{job_id}_{did}"):
        st.markdown(
            '<span class="ips-job-doc-delete-confirm-marker" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        msg_col, action_col = st.columns([5.5, 1.5], gap="small", vertical_alignment="center")
        with msg_col:
            st.markdown(
                f'<div class="ips-job-doc-delete-confirm-message">Delete document “{safe_name}”?</div>',
                unsafe_allow_html=True,
            )
        with action_col:
            delete_col, cancel_col = st.columns(2, gap="small")
            with delete_col:
                if st.button(
                    "Delete",
                    key=f"confirm_delete_job_doc_{job_id}_{did}",
                    type="primary",
                    use_container_width=True,
                ):
                    _handle_delete_job_document(doc_id=did, job_id=job_id, admin=admin)
            with cancel_col:
                if st.button(
                    "Cancel",
                    key=f"cancel_delete_job_doc_{job_id}_{did}",
                    use_container_width=True,
                ):
                    _clear_job_doc_pending_delete()
                    st.rerun()


def _render_job_document_row(
    doc: dict,
    *,
    job_id: str,
    task_labels: dict[str, str],
    admin: bool,
    signed_url_for_timesheet,
) -> None:
    did = str(doc.get("id") or "").strip()
    if not did:
        return
    pending_id = str(st.session_state.get(JOB_DOC_PENDING_DELETE_ID_KEY) or "").strip()
    pending_jid = str(st.session_state.get(JOB_DOC_PENDING_DELETE_JOB_KEY) or "").strip()
    if pending_id == did and pending_jid == job_id:
        _render_job_document_delete_confirm(doc=doc, job_id=job_id, admin=admin)
        return

    name = str(doc.get("file_name") or doc.get("name") or "Document")
    dtype = str(doc.get("doc_type") or "")
    path = str(doc.get("storage_path") or "")
    url = signed_url_for_timesheet(path) if path else ""
    when = str(doc.get("upload_date") or doc.get("created_at") or "")[:10]
    notes = str(doc.get("notes") or "").strip()
    subjob_tid = str(doc.get("task_id") or "").strip()
    subjob = task_labels.get(subjob_tid, "") if subjob_tid else ""

    meta_parts = [f"**{html.escape(name)}**"]
    if dtype:
        meta_parts.append(html.escape(dtype))
    if when:
        meta_parts.append(when)
    if subjob:
        meta_parts.append(f"Subjob: {html.escape(subjob)}")
    if notes:
        meta_parts.append(html.escape(notes[:120]))
    meta_line = " · ".join(meta_parts)

    open_width = 0.9 if url else 0.0
    meta_width = 6.0 - open_width
    meta_col, open_col, del_col = st.columns([meta_width, open_width, 0.35], gap="small", vertical_alignment="center")
    with meta_col:
        st.markdown(meta_line, unsafe_allow_html=True)
    with open_col:
        if url:
            st.link_button("Open", url, use_container_width=True, key=f"job_doc_open_{job_id}_{did}")
    with del_col:
        if st.button(
            "🗑️",
            key=f"delete_job_doc_{job_id}_{did}",
            help="Delete document",
            type="tertiary",
        ):
            st.session_state[JOB_DOC_PENDING_DELETE_ID_KEY] = did
            st.session_state[JOB_DOC_PENDING_DELETE_JOB_KEY] = job_id
            st.rerun()


def _render_job_documents_tab(job: dict) -> None:
    """Job-linked documents from documents_hub and approved weekly timesheets."""
    jid = str(job.get("id") or "")
    if not jid:
        _render_dialog_placeholder("Save this job before attaching documents.")
        return
    try:
        from app.services.job_documents import fetch_job_documents
        from app.services.weekly_job_timesheet_service import list_timesheets_for_job, signed_url_for_timesheet
    except ImportError:
        from services.job_documents import fetch_job_documents  # type: ignore
        from services.weekly_job_timesheet_service import list_timesheets_for_job, signed_url_for_timesheet  # type: ignore

    admin = _field_admin_read()
    upload_active = _job_doc_upload_active(jid)

    head_l, head_r = st.columns([3, 1], gap="small")
    with head_l:
        st.markdown("**Job documents**")
    with head_r:
        if not upload_active and st.button(
            "+ Upload Documents",
            key=f"job_doc_upload_btn_{_job_session_key(job)}",
            use_container_width=True,
        ):
            _set_job_doc_upload(jid, True)
            st.rerun()

    if upload_active:
        _render_job_document_upload_form(job)
        st.divider()

    docs = fetch_job_documents(jid, admin=admin, limit=500)
    ts_rows = [
        r
        for r in list_timesheets_for_job(jid)
        if str(r.get("status") or "") in {"Approved", "Signed", "Sent", "Generated"}
    ]
    task_labels = _job_subjob_label_map(jid)

    if docs:
        for doc in docs:
            _render_job_document_row(
                doc,
                job_id=jid,
                task_labels=task_labels,
                admin=admin,
                signed_url_for_timesheet=signed_url_for_timesheet,
            )
    elif not ts_rows and not upload_active:
        _render_dialog_placeholder(
            "No documents yet. Approved weekly timesheets and uploaded job documents will appear here."
        )

    if ts_rows:
        if docs:
            st.divider()
        st.markdown("**Weekly timesheets**")
        for row in sorted(ts_rows, key=lambda r: str(r.get("week_start") or ""), reverse=True):
            ws = str(row.get("week_start") or "")[:10]
            status = str(row.get("status") or "")
            pdf = str(row.get("pdf_path") or row.get("pdf_file_url") or "")
            xls = str(row.get("excel_path") or row.get("excel_url") or "")
            links: list[str] = []
            if pdf:
                u = signed_url_for_timesheet(pdf)
                if u:
                    links.append(f'<a href="{html.escape(u)}" target="_blank">PDF</a>')
            if xls:
                u = signed_url_for_timesheet(xls)
                if u:
                    links.append(f'<a href="{html.escape(u)}" target="_blank">Excel</a>')
            link_html = " · ".join(links) if links else ""
            st.markdown(
                f"- Week **{ws}** · **{html.escape(status)}**" + (f" · {link_html}" if link_html else ""),
                unsafe_allow_html=True,
            )


def _daily_update_entry_text(row: dict, *, source: str) -> str:
    """Build display text from a job_daily_updates or supervisor_daily_reports row."""
    if source == "supervisor":
        keys = ("completed_today", "main_goal", "not_completed", "tomorrows_plan", "midday_reason")
    else:
        keys = ("work_performed", "notes", "summary", "delays", "safety_notes")
    parts = [str(row.get(key) or "").strip() for key in keys]
    parts = [p for p in parts if p]
    if source != "supervisor":
        weather = str(row.get("weather") or "").strip()
        if weather:
            parts.append(f"Weather: {weather}")
    return "\n\n".join(parts)


def _render_job_daily_updates_tab(job: dict) -> None:
    """Daily field updates for the current job with add form and history."""
    jid = str(job.get("id") or "").strip()
    if not jid:
        _render_dialog_placeholder("Save this job before adding daily updates.")
        return

    add_active = _job_daily_update_add_active(jid)
    head_l, head_r = st.columns([3, 1], gap="small")
    with head_l:
        st.markdown("**Daily updates**")
    with head_r:
        if not add_active and st.button(
            "+ Add Daily Update",
            key=f"job_daily_upd_btn_{_job_session_key(job)}",
            use_container_width=True,
        ):
            _set_job_daily_update_add(jid, True)
            st.rerun()

    if add_active:
        _render_job_daily_update_add_form(job)
        st.divider()

    entries: list[tuple[str, str, str, str]] = []

    try:
        from app.services.job_updates_service import get_job_daily_updates
    except ImportError:
        from services.job_updates_service import get_job_daily_updates  # type: ignore

    for row in get_job_daily_updates(jid):
        if not isinstance(row, dict):
            continue
        summary = str(row.get("summary") or "").strip()
        text = _daily_update_entry_text(row, source="job").strip()
        if not text and not summary:
            continue
        dt = str(row.get("update_date") or "")[:10]
        author = str(row.get("supervisor_name") or row.get("employee_name") or "").strip()
        headline = summary or (text.split("\n\n", 1)[0] if text else "")
        body = text if not summary else text
        if summary and body.startswith(summary):
            body = body[len(summary) :].lstrip("\n").strip()
        entries.append((dt, author, headline, body or text))

    try:
        from app.services.supervisor_daily_reports import fetch_reports_for_job
    except ImportError:
        from services.supervisor_daily_reports import fetch_reports_for_job  # type: ignore

    for row in fetch_reports_for_job(jid, admin=_field_admin_read()):
        if not isinstance(row, dict):
            continue
        text = _daily_update_entry_text(row, source="supervisor").strip()
        if not text:
            continue
        dt = str(row.get("report_date") or "")[:10]
        author = str(row.get("supervisor_name") or "").strip()
        headline = text.split("\n\n", 1)[0]
        body = text.split("\n\n", 1)[1] if "\n\n" in text else ""
        entries.append((dt, author, headline, body or text))

    entries.sort(key=lambda item: item[0], reverse=True)

    if not entries:
        _render_dialog_placeholder(
            "No daily updates yet. Field updates added for this job will appear here."
        )
        return

    blocks: list[str] = []
    for dt, author, headline, body in entries:
        meta = html.escape(dt)
        if author:
            meta += f" · {html.escape(author)}"
        title_html = ""
        if headline and headline != body:
            title_html = (
                f'<div style="font-size:0.9375rem;font-weight:700;color:#0f172a;'
                f'margin:0.35rem 0 0.2rem;">{html.escape(headline)}</div>'
            )
        body_text = body or headline
        blocks.append(
            f'<div style="margin-bottom:1rem;padding-bottom:1rem;border-bottom:1px solid #e2e8f0;">'
            f'<div style="font-size:0.75rem;font-weight:700;color:#64748b;text-transform:uppercase;'
            f'letter-spacing:0.04em;">{meta}</div>'
            f"{title_html}"
            f'<p style="margin:0.35rem 0 0;font-size:0.875rem;color:#0f172a;line-height:1.5;'
            f'white-space:pre-wrap;">{html.escape(body_text)}</p>'
            f"</div>"
        )
    body = "".join(blocks)
    st.markdown(_dialog_card("Daily updates", body), unsafe_allow_html=True)


def _render_dialog_placeholder(message: str) -> None:
    st.markdown(
        f'<div class="ips-dialog-placeholder">{html.escape(message)}</div>',
        unsafe_allow_html=True,
    )


def _render_job_photos_tab(job: dict) -> None:
    """Photos tab: gallery + upload when job_photos is available; friendly empty state otherwise."""
    jid = str(job.get("id") or "").strip()
    if not jid:
        _render_dialog_placeholder("Save this job before uploading photos.")
        return
    try:
        from app.ui.field_components import render_job_photos_panel
    except ImportError:
        from ui.field_components import render_job_photos_panel  # type: ignore
    render_job_photos_panel(
        job_id=jid,
        admin_read=_field_admin_read(),
        compact=True,
        task_labels=_job_subjob_label_map(jid),
    )


def _job_inventory_action_label(txn_type: str) -> str:
    try:
        from app.services.inventory_service import inventory_action_label
    except ImportError:
        from services.inventory_service import inventory_action_label  # type: ignore
    return inventory_action_label(txn_type)


def get_inventory_transactions(job_id=None, limit=200):
    """
    Safe inventory transaction fetcher for Job Detail Inventory tab.
    Prevents Job Details modal/page from crashing if inventory transaction data is missing.
    """
    try:
        from app.services.inventory_service import get_inventory_transactions as _fetch_txns

        return _fetch_txns(job_id=str(job_id).strip() or None, limit=limit)
    except ImportError:
        try:
            from services.inventory_service import get_inventory_transactions as _fetch_txns  # type: ignore

            return _fetch_txns(job_id=str(job_id).strip() or None, limit=limit)
        except Exception:
            pass
    except Exception:
        pass

    try:
        from app.db import get_client, run_user_supabase_operation
    except ImportError:
        from db import get_client, run_user_supabase_operation  # type: ignore

    try:
        jid = str(job_id).strip() if job_id else ""

        def _run():
            query = get_client().table("inventory_transactions").select("*")
            if jid:
                query = query.eq("job_id", jid)
            return query.order("created_at", desc=True).limit(limit).execute()

        result = run_user_supabase_operation(
            "read inventory_transactions",
            _run,
            friendly_on_failure=False,
        )
        return result.data or []
    except Exception:
        return []


def _render_job_inventory_tab(job: dict) -> None:
    jid = str(job.get("id") or "")
    txns = get_inventory_transactions(job_id=jid, limit=200)
    if not txns:
        _render_dialog_placeholder("No inventory scan transactions linked to this job yet.")
        return
    head = (
        '<div class="ips-inventory-txn-head">'
        '<span>Date</span><span>Item</span><span>SKU</span><span>Action</span>'
        '<span>Qty</span><span>Unit</span><span>Scanned By</span><span>Phone</span><span>Notes</span>'
        "</div>"
    )
    rows_html = ""
    for row in txns:
        rows_html += (
            '<div class="ips-inventory-txn-row ips-job-inventory-txn-row">'
            f'<span>{html.escape(fmt_date(row.get("created_at")))}</span>'
            f'<span>{html.escape(str(row.get("item_name") or "—"))}</span>'
            f'<span>{html.escape(str(row.get("sku") or "—"))}</span>'
            f'<span>{html.escape(_job_inventory_action_label(row.get("transaction_type")))}</span>'
            f'<span>{html.escape(str(row.get("quantity_display") or ""))}</span>'
            f'<span>{html.escape(str(row.get("unit") or "—"))}</span>'
            f'<span>{html.escape(str(row.get("scanned_by_name") or "—"))}</span>'
            f'<span>{html.escape(format_phone_display(str(row.get("scanned_by_phone") or "")))}</span>'
            f'<span>{html.escape(str(row.get("notes") or ""))}</span>'
            "</div>"
        )
    st.markdown(f'<div class="ips-inventory-txn-table">{head}{rows_html}</div>', unsafe_allow_html=True)


def _render_job_ips_forms_tab(job: dict) -> None:
    """Dedicated IPS Forms tab in Job Details."""
    render_job_ips_forms_tab(job)


def _render_job_equipment_tab(job: dict) -> None:
    """Job equipment list and inspection form launchers."""
    jid = str(job.get("id") or "").strip()
    if not jid:
        _render_dialog_placeholder("Save this job before linking equipment inspections.")
        return

    try:
        from app.components.coupling_inspection_launcher import render_coupling_inspection_launcher
        from app.db import fetch_table
        from app.pages._core._data import load_assets
    except ImportError:
        from components.coupling_inspection_launcher import render_coupling_inspection_launcher  # type: ignore
        from db import fetch_table  # type: ignore
        from pages._core._data import load_assets  # type: ignore

    equip_rows: list[dict] = []
    try:
        equip_rows = fetch_table("job_equipment", limit=500, order_by="created_at") or []
    except Exception:
        equip_rows = []
    equip_rows = [r for r in equip_rows if str(r.get("job_id") or "") == jid]

    assets_by_id = {str(a.get("id") or ""): a for a in load_assets()}
    st.markdown(_dialog_card("Equipment on Job", ""), unsafe_allow_html=True)
    if equip_rows:
        for row in equip_rows:
            asset_id = str(row.get("asset_id") or "").strip()
            asset = assets_by_id.get(asset_id) or {}
            label = str(row.get("asset_label") or asset.get("asset_name") or "Equipment")
            asset_no = str(asset.get("asset_number") or asset.get("asset_id") or "—")
            st.markdown(
                f"**{html.escape(label)}** · Asset #{html.escape(asset_no)}",
            )
            render_coupling_inspection_launcher(
                job_id=jid,
                equipment_id=asset_id or None,
                key_prefix=f"job_eq_ci_{jid}_{asset_id or row.get('id')}",
            )
            st.divider()
    else:
        st.caption("No equipment lines on this job yet. You can still start a coupling inspection for the job.")

    render_coupling_inspection_launcher(
        job_id=jid,
        equipment_id=None,
        key_prefix=f"job_ci_{jid}",
    )


def _field_admin_read() -> bool:
    try:
        from auth import current_role
    except ImportError:
        from app.auth import current_role  # type: ignore
    return current_role() in {"admin", "manager"}


def _render_field_job_detail_tabs(job: dict) -> None:
    """Compact job detail for field mode (4 tabs)."""
    jn = _safe_value(job.get("job_number"))
    jname = _safe_value(job.get("job_name"))
    status = _safe_value(job.get("status"))
    customer = _safe_value(job.get("customer"))
    supervisor = _safe_value(job.get("supervisor"))
    jid = str(job.get("id") or "").strip()

    try:
        from app.pages.supervisor_daily_reports import render_daily_reports_for_job
        from app.services.job_service import job_row_select_label
    except ImportError:
        from pages.supervisor_daily_reports import render_daily_reports_for_job  # type: ignore
        from services.job_service import job_row_select_label  # type: ignore

    tab_overview, tab_materials, tab_tasks, tab_photos, tab_daily = st.tabs(_FIELD_JOB_TABS)

    with tab_overview:
        overview_html = (
            f'<div class="ips-detail-grid">'
            f"{_detail_field('Job Number', jn)}"
            f"{_detail_field('Project', jname)}"
            f"{_detail_field('Customer', customer)}"
            f'{_detail_field("Status", status, html_value=_status_pill(status))}'
            f"{_detail_field('Supervisor', supervisor)}"
            f"{_detail_field('Location', _job_location(job))}"
            f"{_detail_field('Start Date', fmt_date(job.get('start_date')))}"
            f"{_detail_field('End Date', fmt_date(job.get('end_date')))}"
            f"</div>"
        )
        st.markdown(_dialog_card("Overview", overview_html), unsafe_allow_html=True)
        scope_text = _safe_value(job.get("scope") or job.get("description"), "No scope defined.")
        scope_html = (
            f'<p style="margin:0;font-size:0.875rem;color:#0f172a;line-height:1.5;white-space:pre-wrap;">'
            f"{html.escape(scope_text)}"
            f"</p>"
        )
        st.markdown(_dialog_card("Scope", scope_html), unsafe_allow_html=True)

    with tab_materials:
        render_job_materials_tab(job, key_prefix=f"field_job_mat_{jid}")

    with tab_tasks:
        inject_tasks_module_css()
        render_job_linked_tasks_tab(job)

    with tab_photos:
        _render_job_photos_tab(job)

    with tab_daily:
        if jid:
            render_daily_reports_for_job(
                job_id=jid,
                job_label=job_row_select_label(job),
                admin_read=_field_admin_read(),
                show_title=False,
                inline=True,
                expand_sections=True,
            )
        else:
            _render_dialog_placeholder("Save this job before filing daily reports.")


def _render_job_detail_tabs(job: dict) -> None:
    jn = _safe_value(job.get("job_number"))
    jname = _safe_value(job.get("job_name"))
    status = _safe_value(job.get("status"))
    customer = _safe_value(job.get("customer"))
    supervisor = _safe_value(job.get("supervisor"))
    estimate_no = _safe_value(job.get("estimate_number"))

    (
        tab_overview,
        tab_tasks,
        tab_schedule,
        tab_weekly_ts,
        tab_costing,
        tab_materials,
        tab_equipment,
        tab_documents,
        tab_photos,
        tab_ips_forms,
        tab_scope,
        tab_estimates,
        tab_daily,
        tab_notes,
    ) = st.tabs(_job_detail_tab_labels(job))

    with tab_overview:
        left_html = (
            f'<div class="ips-detail-grid">'
            f"{_detail_field('Job Number', jn)}"
            f"{_detail_field('Project', jname)}"
            f"{_detail_field('Customer', customer)}"
            f'{_detail_field("Status", status, html_value=_status_pill(status))}'
            f"</div>"
        )
        right_html = (
            f'<div class="ips-detail-grid">'
            f"{_detail_field('Supervisor', supervisor)}"
            f"{_detail_field('Project Manager', job.get('project_manager'))}"
            f"{_detail_field('Location', _job_location(job))}"
            f"{_detail_field('Estimate #', estimate_no)}"
            f"{_detail_field('Start Date', fmt_date(job.get('start_date')))}"
            f"{_detail_field('End Date', fmt_date(job.get('end_date')))}"
            f"</div>"
        )
        st.markdown(
            f'<div class="ips-job-detail-overview-grid">'
            f'{_dialog_card("Overview", left_html)}'
            f'{_dialog_card("Schedule & Links", right_html)}'
            f"</div>",
            unsafe_allow_html=True,
        )
        if st.button(
            "Edit Overview",
            key=f"jobs_overview_edit_{_job_session_key(job)}",
            type="secondary",
        ):
            _set_job_edit_mode(job)
            st.rerun()

    with tab_scope:
        scope_text = _safe_value(job.get("scope") or job.get("description"), "No scope defined.")
        scope_html = (
            f'<p style="margin:0;font-size:0.875rem;color:#0f172a;line-height:1.5;white-space:pre-wrap;">'
            f"{html.escape(scope_text)}"
            f"</p>"
        )
        st.markdown(_dialog_card("Scope of Work", scope_html), unsafe_allow_html=True)

    with tab_estimates:
        jid = str(job.get("id") or "")
        job_est_id = str(job.get("estimate_id") or "").strip()
        linked = [
            e
            for e in load_estimates()
            if str(e.get("job_id") or "") == jid or (job_est_id and str(e.get("id") or "") == job_est_id)
        ]
        if not linked:
            _render_dialog_placeholder("No estimates linked to this job yet.")
        else:
            for est in linked:
                est_no = str(est.get("estimate_number") or "—")
                project = str(est.get("project_name") or "—")
                status_lbl = str(est.get("status") or "Draft")
                total = est.get("customer_price") or est.get("total") or 0
                approved_at = fmt_date(est.get("approved_at")) if est.get("approved_at") else "—"
                try:
                    from app.utils.formatting import fmt_currency
                except ImportError:
                    from utils.formatting import fmt_currency  # type: ignore
                st.markdown(
                    f'<div class="ips-detail-grid">'
                    f"{_detail_field('Estimate #', est_no)}"
                    f"{_detail_field('Project', project)}"
                    f"{_detail_field('Status', status_lbl)}"
                    f"{_detail_field('Estimate Date', fmt_date(est.get('estimate_date')))}"
                    f"{_detail_field('Approved Date', approved_at)}"
                    f"{_detail_field('Customer Price', fmt_currency(total))}"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                bc1, bc2 = st.columns(2, gap="small")
                with bc1:
                    if st.button("View Estimate", key=f"job_est_view_{jid}_{est.get('id')}", use_container_width=True):
                        st.session_state["selected_estimate_id"] = str(est.get("id") or "")
                        st.session_state["show_estimate_detail_modal"] = True
                        st.info("Open the **Estimates** page to view full estimate details.")
                with bc2:
                    if st.button("Proposal PDF", key=f"job_est_pdf_{jid}_{est.get('id')}", use_container_width=True):
                        try:
                            from app.services.proposal_pdf_service import generate_estimate_proposal_pdf_by_id
                        except ImportError:
                            from services.proposal_pdf_service import generate_estimate_proposal_pdf_by_id  # type: ignore
                        pdf_bytes = generate_estimate_proposal_pdf_by_id(str(est.get("id") or ""), est)
                        if pdf_bytes:
                            st.download_button(
                                "Download PDF",
                                data=pdf_bytes,
                                file_name=f"{est_no}_proposal.pdf",
                                mime="application/pdf",
                                key=f"job_est_pdf_dl_{jid}_{est.get('id')}",
                                use_container_width=True,
                            )
                        else:
                            st.caption("Proposal PDF is not available for this estimate yet.")

    with tab_materials:
        render_job_materials_tab(job, key_prefix=f"job_mat_{str(job.get('id') or '')}")

    with tab_equipment:
        _render_job_equipment_tab(job)

    with tab_costing:
        render_job_costing_tab(job, key_prefix=f"job_cost_{str(job.get('id') or '')}")

    with tab_schedule:
        sched_html = (
            f'<div class="ips-detail-grid">'
            f"{_detail_field('Start Date', fmt_date(job.get('start_date')))}"
            f"{_detail_field('End Date', fmt_date(job.get('end_date')))}"
            f"{_detail_field('Location', _job_location(job))}"
            f"</div>"
        )
        st.markdown(_dialog_card("Schedule", sched_html), unsafe_allow_html=True)

    with tab_tasks:
        inject_tasks_module_css()
        render_job_linked_tasks_tab(job)

    with tab_ips_forms:
        _render_job_ips_forms_tab(job)

    with tab_weekly_ts:
        jid = str(job.get("id") or "").strip()
        if jid:
            render_weekly_timesheet_builder(
                fixed_job_id=jid,
                embedded=True,
                key_prefix=f"job_wjt_{_job_session_key(job)}",
            )
        else:
            _render_dialog_placeholder("Save this job before generating weekly timesheets.")

    with tab_documents:
        _render_job_documents_tab(job)

    with tab_photos:
        _render_job_photos_tab(job)

    with tab_daily:
        _render_job_daily_updates_tab(job)

    with tab_notes:
        notes_text = _safe_value(job.get("notes") or job.get("description"), "No notes entered.")
        notes_html = (
            f'<p style="margin:0;font-size:0.875rem;color:#0f172a;line-height:1.5;white-space:pre-wrap;">'
            f"{html.escape(notes_text)}"
            f"</p>"
        )
        st.markdown(_dialog_card("Notes", notes_html), unsafe_allow_html=True)


def _render_job_edit_form(job: dict) -> None:
    job_key = _job_session_key(job)
    jid = str(job.get("id") or "")
    edit_mode_key = _job_edit_mode_key(job)
    pk = f"job_edit_{job_key}"

    if f"job_edit_num_{job_key}" not in st.session_state:
        _seed_job_edit_form(job)

    st.markdown(
        '<div class="ips-edit-form-card"><div class="ips-form-section-title">Edit Job</div></div>',
        unsafe_allow_html=True,
    )

    cust_opts = customer_filter_options(include_names={str(job.get("customer") or "")})
    try:
        from app.services.jobs_service import MANUAL_JOB_STATUSES, normalize_job_status
    except ImportError:
        from services.jobs_service import MANUAL_JOB_STATUSES, normalize_job_status  # type: ignore
    cur_status = normalize_job_status(job.get("status"))
    status_opts = list(MANUAL_JOB_STATUSES)
    if cur_status not in status_opts:
        status_opts = [cur_status, *status_opts]
    sup_opts = _supervisor_options(job)

    ec1, ec2 = st.columns(2, gap="medium")
    with ec1:
        st.text_input("Job number", key=f"job_edit_num_{job_key}")
        st.text_input("Job name / project description", key=f"job_edit_name_{job_key}")
        st.selectbox("Customer", cust_opts, key=f"job_edit_cust_{job_key}")
        cust_name = str(st.session_state.get(f"job_edit_cust_{job_key}") or job.get("customer") or "")
        location_id = _customer_location_select(
            customer_name=cust_name,
            session_key=f"job_edit_location_{job_key}",
            prev_customer_key=f"job_edit_cust_prev_{job_key}",
            initial_location_id=_job_customer_location_id(job),
        )
        contact_id = _customer_contact_select(
            customer_name=cust_name,
            location_id=location_id,
            session_key=f"job_edit_contact_{job_key}",
            prev_customer_key=f"job_edit_cust_prev_{job_key}",
            prev_location_key=f"job_edit_loc_prev_{job_key}",
            initial_contact_id=str(job.get("customer_contact_id") or ""),
        )
        st.selectbox("Status", status_opts, key=f"job_edit_status_{job_key}")
        st.selectbox("Supervisor", sup_opts, key=f"job_edit_sup_{job_key}")
    with ec2:
        st.date_input("Start date", key=f"job_edit_start_{job_key}")
        st.date_input("End date", key=f"job_edit_end_{job_key}")
        st.slider("Progress %", 0, 100, key=f"job_edit_prog_{job_key}")

    st.text_area("Scope of work", key=f"job_edit_scope_{job_key}", height=120)
    st.text_area("Notes", key=f"job_edit_notes_{job_key}", height=100)

    btn_cancel, btn_spacer, btn_save = st.columns([1, 4, 1], gap="small")
    with btn_cancel:
        if st.button("Cancel", key=f"{pk}_cancel"):
            _set_job_view_mode(job)
            st.rerun()
    with btn_save:
        if st.button("Save Changes", key=f"{pk}_save", type="primary"):
            scope_text = str(st.session_state.get(f"job_edit_scope_{job_key}") or "").strip()
            notes_text = str(st.session_state.get(f"job_edit_notes_{job_key}") or "").strip()
            ui = {
                "job_number": st.session_state.get(f"job_edit_num_{job_key}"),
                "job_name": st.session_state.get(f"job_edit_name_{job_key}"),
                "customer": st.session_state.get(f"job_edit_cust_{job_key}"),
                "customer_location_id": location_id or None,
                "customer_contact_id": contact_id or None,
                "status": st.session_state.get(f"job_edit_status_{job_key}"),
                "supervisor": st.session_state.get(f"job_edit_sup_{job_key}"),
                "start_date": st.session_state.get(f"job_edit_start_{job_key}"),
                "end_date": st.session_state.get(f"job_edit_end_{job_key}"),
                "progress": st.session_state.get(f"job_edit_prog_{job_key}"),
                "description": scope_text,
                "notes": notes_text or scope_text,
            }
            ok, msg = persist_job(ui, row_id=jid or None)
            if ok:
                st.session_state[edit_mode_key] = False
                st.success(msg or "Job saved.")
                st.rerun()
            else:
                st.error(msg or "Could not save job.")


def _render_job_actions_panel(job: dict) -> None:
    """Complete, cancel, or archive a job from the detail modal."""
    if bool(st.session_state.get(_job_edit_mode_key(job))):
        return
    jid = str(job.get("id") or "").strip()
    if not jid or is_demo_id(jid):
        return

    def _after_complete_or_delete() -> None:
        _clear_jobs_detail_modal()

    render_job_action_buttons(
        job,
        on_edit=_set_job_edit_mode,
        edit_key=f"jobs_modal_edit_{_job_session_key(job)}",
        on_complete=_after_complete_or_delete,
        on_delete=_after_complete_or_delete,
    )


def render_job_detail_dialog(job: dict) -> None:
    """Professional Job Details modal body (opened via row selection)."""
    job_key = _job_session_key(job)
    edit_mode_key = _job_edit_mode_key(job)
    st.session_state.setdefault(edit_mode_key, False)
    edit_mode = bool(st.session_state.get(edit_mode_key))

    jn = _safe_value(job.get("job_number"))
    jname = _safe_value(job.get("job_name"))
    status = _safe_value(job.get("status"))
    customer = _safe_value(job.get("customer"))
    supervisor = _safe_value(job.get("supervisor"))
    project_manager = _safe_value(job.get("project_manager"))
    estimate_no = _safe_value(job.get("estimate_number"))
    schedule = _schedule_summary(job)

    inject_job_detail_layout_css()
    st.markdown(
        '<span class="ips-dialog-shell ips-modal-wide ips-job-detail-control-page" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )

    header_cols = st.columns([1, 0.28], gap="small")
    with header_cols[0]:
        render_job_detail_header(
            job_number=jn,
            job_name=jname,
            customer=customer,
        )
    with header_cols[1]:
        if not edit_mode:
            render_job_status_badge_editor(
                job,
                key_prefix="jobs_modal",
                on_updated=_on_job_status_updated,
            )
        else:
            st.markdown(
                f'<div class="ips-job-detail-header-actions">{_status_pill(status)}</div>',
                unsafe_allow_html=True,
            )
        if not edit_mode:
            render_job_detail_header_actions(
                job,
                on_edit=_set_job_edit_mode,
                edit_key=f"jobs_modal_edit_{job_key}",
            )

    render_job_detail_metadata_row(
        customer=customer,
        project_manager=project_manager,
        supervisor=supervisor,
        estimate_no=estimate_no,
        schedule=schedule,
    )

    jid = str(job.get("id") or "").strip()
    cost_summary: dict = {}
    detail_stats: dict = {}
    if jid and not edit_mode:
        sync_all_sources_for_job(jid)
        cost_summary = _enrich_job_cost_summary(job, build_job_cost_summary(job))
        detail_stats = gather_job_detail_stats(job, cost_summary)
        render_job_cost_summary_cards(cost_summary, compact=True)
        render_job_detail_health_section(job, cost_summary, detail_stats)
        render_job_detail_quick_stats(detail_stats)

    if edit_mode:
        _render_job_edit_form(job)
    else:
        body_left, body_right = st.columns([2.35, 1], gap="medium")
        with body_left:
            if is_field_context():
                _render_field_job_detail_tabs(job)
            else:
                _render_job_detail_tabs(job)
        with body_right:
            render_job_detail_activity_sidebar(job)

        render_job_detail_footer_shell()
        _render_job_actions_panel(job)
        close_job_detail_footer_shell()

    _focus_job_costing_tab_if_requested()


def _focus_job_costing_tab_if_requested() -> None:
    """Select the Job Costing tab when opened via Jobs deep-link (no layout change)."""
    try:
        from app.navigation import JOBS_DETAIL_FOCUS_TAB_KEY
    except ImportError:
        from navigation import JOBS_DETAIL_FOCUS_TAB_KEY  # type: ignore
    focus = str(st.session_state.pop(JOBS_DETAIL_FOCUS_TAB_KEY, "") or "").strip()
    if focus != "Job Costing":
        return
    try:
        from app.ui.clean_table import _components_html
    except ImportError:
        from ui.clean_table import _components_html  # type: ignore
    _components_html(
        """
<script>
(function () {
  const w = window.parent || window;
  const doc = w.document;
  const dialog = doc.querySelector('[data-testid="stDialog"]');
  if (!dialog) return;
  const tabs = dialog.querySelectorAll('[data-testid="stTabs"] button[role="tab"]');
  if (tabs && tabs[4]) tabs[4].click();
})();
</script>
        """,
        component_key="ips_jobs_focus_costing_tab",
        height=1,
    )


@st.dialog("Job Details", width="large", on_dismiss=_clear_jobs_detail_modal)
def _show_jobs_detail_modal() -> None:
    sel = str(st.session_state.get(_JOBS_MODAL_KEY) or st.session_state.get(_SEL) or "").strip()
    jobs_by_id = st.session_state.get("_ips_jobs_modal_by_id")
    job = jobs_by_id.get(sel) if isinstance(jobs_by_id, dict) and sel else None
    if not job:
        st.warning("That job could not be loaded.")
        return

    render_job_detail_dialog(job)


def render() -> None:
    try:
        from app.pages._core._access import begin_module
    except ImportError:
        from pages._core._access import begin_module  # type: ignore
    if not begin_module("jobs"):
        return
    st.markdown(
        '<span class="ips-jobs-page ips-page-shell-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    inject_jobs_module_css()
    inject_jobs_page_layout_css()
    if is_field_context():
        inject_field_row_expand_css()
    all_jobs = load_jobs()
    filter_options = build_filter_options(all_jobs, _JOB_COLUMN_FILTER_SPECS)

    def _jobs_export() -> None:
        st.button("Export", key="jobs_export", use_container_width=True)

    def _jobs_new() -> None:
        if st.button("+ New Job", key="jobs_new", type="primary", use_container_width=True):
            clear_new_job_number_state()
            st.session_state["ips_job_form"] = True

    render_page_brand_header(
        "Jobs",
        "Track and manage all company jobs, assignments, and costing.",
        actions=[_jobs_export, _jobs_new],
    )

    if is_field_mode():
        try:
            from app.services.job_service import sort_jobs_by_number_then_name
        except ImportError:
            from services.job_service import sort_jobs_by_number_then_name  # type: ignore
        field_jobs = sort_jobs_by_number_then_name(all_jobs)
        if field_jobs:
            render_field_job_bar(field_jobs, key_prefix="jobs")

    if st.session_state.get("ips_job_form"):
        with st.expander("New Job", expanded=True):
            nc1, nc2 = st.columns(2)
            with nc2:
                st.text_input("Supervisor", key="job_new_sup")
                st.date_input("Start date", key="job_new_start", value=date.today())
                st.date_input("End date", key="job_new_end", value=None)
            with nc1:
                sync_new_job_number()
                st.text_input(
                    "Job number",
                    key="job_new_num",
                    on_change=_job_new_num_edited,
                )
                st.text_input("Job name", key="job_new_name")
                st.selectbox("Customer", customer_filter_options(), key="job_new_cust")
                new_cust = str(st.session_state.get("job_new_cust") or "")
                new_location_id = _customer_location_select(
                    customer_name=new_cust,
                    session_key="job_new_location",
                    prev_customer_key="job_new_cust_prev",
                )
                new_contact_id = _customer_contact_select(
                    customer_name=new_cust,
                    location_id=new_location_id,
                    session_key="job_new_contact",
                    prev_customer_key="job_new_cust_prev",
                    prev_location_key="job_new_loc_prev",
                )
                try:
                    from app.services.jobs_service import MANUAL_JOB_STATUSES
                except ImportError:
                    from services.jobs_service import MANUAL_JOB_STATUSES  # type: ignore
                st.selectbox("Status", list(MANUAL_JOB_STATUSES), key="job_new_status")
            st.text_area("Description", key="job_new_desc")
            sb1, sb2 = st.columns(2)
            with sb1:
                if st.button("Save job", key="job_save_new", type="primary"):
                    ok, msg = persist_job(
                        {
                            "job_number": str(st.session_state.get("job_new_num") or "").strip(),
                            "job_name": st.session_state.get("job_new_name"),
                            "customer": st.session_state.get("job_new_cust"),
                            "customer_id": customer_id_for_name(new_cust) or None,
                            "customer_location_id": new_location_id or None,
                            "customer_contact_id": new_contact_id or None,
                            "status": st.session_state.get("job_new_status"),
                            "supervisor": st.session_state.get("job_new_sup"),
                            "start_date": st.session_state.get("job_new_start"),
                            "end_date": st.session_state.get("job_new_end"),
                            "description": st.session_state.get("job_new_desc"),
                        }
                    )
                    if apply_persist_feedback(ok, msg, clear_keys=("ips_job_form",)):
                        clear_new_job_number_state()
                        st.rerun()
            with sb2:
                if st.button("Cancel", key="job_cancel_new"):
                    st.session_state.pop("ips_job_form", None)
                    clear_new_job_number_state()
                    st.rerun()

    def _filters() -> None:
        c1, c2, c3 = st.columns([3.2, 2.2, 0.6])
        with c1:
            st.text_input(
                "Search",
                placeholder="Search job #, project, customer, supervisor…",
                key="jobs_search",
                label_visibility="collapsed",
            )
        with c2:
            st.selectbox(
                "View",
                _JOBS_VIEW_OPTIONS,
                key="jobs_view",
                label_visibility="collapsed",
            )
        with c3:
            if st.button("Clear", key="jobs_clear", use_container_width=True):
                clear_table_filters(
                    _TABLE_KEY,
                    _JOB_BAR_FILTER_FIELDS,
                    extra_keys=["jobs_search", "jobs_view"],
                )
                st.session_state["jobs_view"] = _JOBS_DEFAULT_VIEW
                reset_table_page(_TABLE_KEY)
                _clear_job_selection(st.session_state.get(_ALL_JOB_IDS_KEY))
                clear_field_expanded(FIELD_EXPANDED_JOB_KEY)
                st.rerun()

    render_jobs_filter_bar_shell()
    layout_filter_bar(_filters)
    close_jobs_filter_bar_shell()

    filtered = _filter_jobs(
        all_jobs,
        q=str(st.session_state.get("jobs_search") or "").strip(),
        view=str(st.session_state.get("jobs_view") or _JOBS_DEFAULT_VIEW),
    )

    subjob_counts = _load_open_subjob_counts()
    cost_cache = _build_jobs_list_cost_cache(filtered)
    summary = _jobs_summary_counts(filtered, cost_cache, subjob_counts)
    render_jobs_summary_cards(
        total=int(summary["total"]),
        active=int(summary["active"]),
        awarded=int(summary["awarded"]),
        pending=int(summary["pending"]),
        draft=int(summary["draft"]),
        open_subjobs=int(summary["open_subjobs"]),
        total_contract=float(summary["total_contract"]),
        total_actual=float(summary["total_actual"]),
        has_contract_data=bool(summary.get("has_any_contract")),
        has_actual_data=bool(summary.get("has_any_actual")),
    )
    render_jobs_table_pagination_header(len(filtered), _TABLE_KEY)
    page_rows, _, _, _ = paginate_rows(filtered, _TABLE_KEY)

    modal_cache = {
        str(job.get("id") or "").strip(): job
        for job in filtered
        if str(job.get("id") or "").strip()
    }
    selected_job_id = str(st.session_state.get(SELECTED_JOB_KEY) or "").strip()
    if selected_job_id and st.session_state.get(SHOW_MODAL_KEY):
        for job in all_jobs:
            if str(job.get("id") or "").strip() == selected_job_id:
                modal_cache[selected_job_id] = job
                break
    st.session_state[CACHE_KEY] = modal_cache

    _render_custom_jobs_table(
        page_rows,
        filter_options=filter_options,
        cost_cache=cost_cache,
        subjob_counts=subjob_counts,
    )
    render_jobs_pagination_footer(len(filtered), _TABLE_KEY, item_label="job")

    if selected_job_id and st.session_state.get(SHOW_MODAL_KEY):
        _show_jobs_detail_modal()
