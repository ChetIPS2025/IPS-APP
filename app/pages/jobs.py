"""Jobs module (Phase 2) — list + detail panel."""

from __future__ import annotations

import html
from datetime import date

import streamlit as st

try:
    from app.components.job_actions import render_job_action_buttons
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
        render_table_pagination_footer,
        render_table_pagination_header,
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
    from app.pages.tasks import render_job_linked_tasks_tab
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
        render_table_pagination_footer,
        render_table_pagination_header,
        reset_table_page,
    )
    from pages._core._data import (  # type: ignore
        customer_filter_options,
        employee_options,
        load_estimates,
        load_jobs,
        lookup_options,
        persist_job,
    )
    from pages._core._crud import apply_persist_feedback, is_demo_id  # type: ignore
    from pages._core._session import select_key  # type: ignore
    from pages.tasks import render_job_linked_tasks_tab  # type: ignore
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
_JOB_TABS = [
    "Overview",
    "Scope",
    "Estimates",
    "Inventory",
    "Equipment",
    "Schedule",
    "Subjobs",
    "Weekly Timesheets",
    "Documents",
    "Photos",
    "Daily Updates",
    "Notes",
]
_FIELD_JOB_TABS = ["Overview", "Subjobs", "Photos", "Daily Report"]
SELECTED_JOB_KEY = "selected_job_id"
SHOW_MODAL_KEY = "show_job_detail_modal"
_ALL_JOB_IDS_KEY = "_ips_jobs_visible_ids"
CACHE_KEY = "_ips_jobs_modal_by_id"
_JOB_COLS = [0.35, 0.95, 2.35, 1.85, 1.85, 1.35, 1.25, 1.25]
_JOB_HEADER_SPECS: list[tuple[str, str | None]] = [
    ("", None),
    ("JOB #", None),
    ("PROJECT / DESCRIPTION", None),
    ("CUSTOMER", "customer"),
    ("SUPERVISOR", "supervisor"),
    ("STATUS", "status"),
    ("START DATE", None),
    ("END DATE", None),
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
    s = str(raw or "").strip().lower().replace("_", " ")
    mapping = {
        "": "Draft",
        "draft": "Draft",
        "planning": "Planning",
        "scheduled": "Scheduled",
        "active": "Active",
        "awarded": "Awarded",
        "on hold": "On Hold",
        "completed": "Completed",
        "closed": "Closed",
        "cancelled": "Cancelled",
        "canceled": "Cancelled",
        "archived": "Archived",
        "deleted": "Deleted",
        "estimate pending": "Estimate Pending",
    }
    if s in mapping:
        return mapping[s]
    label = str(raw or "").strip()
    return label if label else "Draft"


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


def _job_location(job: dict) -> str:
    for key in ("location_name", "location"):
        val = str(job.get(key) or "").strip()
        if val:
            return val
    return "—"


_JOB_COLUMN_FILTER_SPECS: list[tuple[str, object]] = [
    ("customer", _job_customer),
    ("supervisor", _job_supervisor),
    ("status", lambda r: _normalize_job_status(r.get("status"))),
]


def _job_status_pill_html(status: str) -> str:
    cls_map = {
        "Draft": "ips-job-status-draft",
        "Planning": "ips-job-status-planning",
        "Scheduled": "ips-job-status-scheduled",
        "Active": "ips-job-status-active",
        "Awarded": "ips-job-status-awarded",
        "On Hold": "ips-job-status-on-hold",
        "Completed": "ips-job-status-completed",
        "Closed": "ips-job-status-closed",
        "Cancelled": "ips-job-status-cancelled",
        "Deleted": "ips-job-status-deleted",
        "Archived": "ips-job-status-archived",
        "Estimate Pending": "ips-job-status-estimate-pending",
    }
    cls = cls_map.get(status, "ips-job-status-draft")
    return f'<span class="ips-job-status-pill {cls}">{html.escape(status)}</span>'


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
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and key.startswith("job_edit_mode_"):
            st.session_state.pop(key, None)


def _render_custom_jobs_table(
    filtered: list[dict],
    *,
    filter_options: dict[str, list[str]],
) -> list[str]:
    if not filtered:
        st.info("No jobs match your filters.")
        st.session_state[_ALL_JOB_IDS_KEY] = []
        return []

    all_job_ids = [str(j.get("id") or "").strip() for j in filtered if str(j.get("id") or "").strip()]
    st.session_state[_ALL_JOB_IDS_KEY] = all_job_ids

    with st.container(key="jobs_table_wrap"):
        st.markdown('<div class="ips-jobs-table-wrap">', unsafe_allow_html=True)

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
            supervisor = _job_supervisor(job)
            status = _normalize_job_status(job.get("status"))
            start = fmt_date(job.get("start_date"))
            end = fmt_date(job.get("end_date"))
            field_mode = is_field_context()
            expanded = field_mode and field_expanded_id(FIELD_EXPANDED_JOB_KEY) == jid

            cols = st.columns(_JOB_COLS, gap="small", vertical_alignment="center")

            with cols[0]:
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
                st.markdown(
                    f'<div class="ips-jobs-number">{html.escape(job_no)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[2]:
                st.markdown(
                    f'<div class="ips-jobs-title">{html.escape(project)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[3]:
                st.markdown(
                    f'<div class="ips-jobs-cell">{html.escape(customer)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[4]:
                st.markdown(
                    f'<div class="ips-jobs-muted ips-jobs-cell">{html.escape(supervisor)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[5]:
                st.markdown(_job_status_pill_html(status), unsafe_allow_html=True)

            with cols[6]:
                st.markdown(
                    f'<div class="ips-jobs-muted ips-jobs-cell">{html.escape(start)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[7]:
                st.markdown(
                    f'<div class="ips-jobs-muted ips-jobs-cell">{html.escape(end)}</div>',
                    unsafe_allow_html=True,
                )

            if expanded:
                st.markdown('<div class="ips-field-row-expand">', unsafe_allow_html=True)
                _render_field_job_detail_tabs(job)
                if st.button("All job details", key=f"job_full_modal_{jid}", use_container_width=True):
                    _open_jobs_detail_modal(jid, job)
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

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


def _render_job_documents_tab(job: dict) -> None:
    """Job-linked documents from documents_hub and approved weekly timesheets."""
    jid = str(job.get("id") or "")
    if not jid:
        _render_dialog_placeholder("Save this job before attaching documents.")
        return
    try:
        from app.db import fetch_by_match_admin, fetch_table_admin
        from app.services.weekly_job_timesheet_service import list_timesheets_for_job, signed_url_for_timesheet
    except ImportError:
        from db import fetch_by_match_admin, fetch_table_admin  # type: ignore
        from services.weekly_job_timesheet_service import list_timesheets_for_job, signed_url_for_timesheet  # type: ignore

    docs: list[dict] = []
    try:
        hub = fetch_table_admin("documents_hub", limit=500, order_by="upload_date")
        docs = [d for d in hub if str(d.get("linked_record_id") or "") == jid]
    except Exception:
        docs = []

    ts_rows = [
        r
        for r in list_timesheets_for_job(jid)
        if str(r.get("status") or "") in {"Approved", "Signed", "Sent", "Generated"}
    ]

    if not docs and not ts_rows:
        _render_dialog_placeholder(
            "No documents yet. Approved weekly timesheets and uploaded job documents will appear here."
        )
        return

    if docs:
        st.markdown("**Documents hub**")
        for doc in sorted(docs, key=lambda d: str(d.get("upload_date") or ""), reverse=True):
            name = str(doc.get("file_name") or doc.get("name") or "Document")
            dtype = str(doc.get("doc_type") or "")
            path = str(doc.get("storage_path") or "")
            url = signed_url_for_timesheet(path) if path else ""
            when = str(doc.get("upload_date") or "")[:10]
            line = f"- **{html.escape(name)}** · {html.escape(dtype)} · {when}"
            if url:
                line += f' · <a href="{html.escape(url)}" target="_blank">Open</a>'
            st.markdown(line, unsafe_allow_html=True)

    if ts_rows:
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
    """Read-only daily field updates for the current job."""
    jid = str(job.get("id") or "").strip()
    if not jid:
        _render_dialog_placeholder("Save this job before adding daily updates.")
        return

    entries: list[tuple[str, str, str]] = []

    try:
        from app.services.job_updates_service import get_job_daily_updates
    except ImportError:
        from services.job_updates_service import get_job_daily_updates  # type: ignore

    for row in get_job_daily_updates(jid):
        if not isinstance(row, dict):
            continue
        text = _daily_update_entry_text(row, source="job").strip()
        if not text:
            continue
        dt = str(row.get("update_date") or "")[:10]
        author = str(row.get("supervisor_name") or row.get("employee_name") or "").strip()
        entries.append((dt, author, text))

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
        entries.append((dt, author, text))

    entries.sort(key=lambda item: item[0], reverse=True)

    if not entries:
        _render_dialog_placeholder(
            "No daily updates yet. Field updates added for this job will appear here."
        )
        return

    blocks: list[str] = []
    for dt, author, text in entries:
        meta = html.escape(dt)
        if author:
            meta += f" · {html.escape(author)}"
        blocks.append(
            f'<div style="margin-bottom:1rem;padding-bottom:1rem;border-bottom:1px solid #e2e8f0;">'
            f'<div style="font-size:0.75rem;font-weight:700;color:#64748b;text-transform:uppercase;'
            f'letter-spacing:0.04em;">{meta}</div>'
            f'<p style="margin:0.35rem 0 0;font-size:0.875rem;color:#0f172a;line-height:1.5;'
            f'white-space:pre-wrap;">{html.escape(text)}</p>'
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
    )


def _job_inventory_action_label(txn_type: str) -> str:
    labels = {
        "check_out": "Check Out",
        "check_in": "Check In",
        "issue_to_job": "Issue to Job",
        "return_from_job": "Return From Job",
        "consume_on_job": "Consume On Job",
        "TO_JOB": "Issue to Job",
        "OUT": "Check Out",
        "IN": "Check In",
        "CONSUME": "Consume On Job",
        "RETURN": "Return From Job",
    }
    return labels.get(str(txn_type or "").strip(), str(txn_type or "—"))


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
        from app.db import get_client
    except ImportError:
        from db import get_client  # type: ignore

    try:
        client = get_client()
        query = client.table("inventory_transactions").select("*")
        if job_id:
            query = query.eq("job_id", str(job_id).strip())
        result = (
            query
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
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

    tab_overview, tab_tasks, tab_photos, tab_daily = st.tabs(_FIELD_JOB_TABS)

    with tab_overview:
        overview_html = (
            f'<div class="ips-detail-grid">'
            f"{_detail_field('Job Number', jn)}"
            f"{_detail_field('Project', jname)}"
            f"{_detail_field('Customer', customer)}"
            f'{_detail_field("Status", status, html_value=_status_pill(status))}'
            f"{_detail_field('Supervisor', supervisor)}"
            f"{_detail_field('Location', job.get('location'))}"
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
        tab_scope,
        tab_estimates,
        tab_inventory,
        tab_equipment,
        tab_schedule,
        tab_tasks,
        tab_weekly_ts,
        tab_documents,
        tab_photos,
        tab_daily,
        tab_notes,
    ) = st.tabs(_JOB_TABS)

    with tab_overview:
        overview_html = (
            f'<div class="ips-detail-grid">'
            f"{_detail_field('Job Number', jn)}"
            f"{_detail_field('Project', jname)}"
            f"{_detail_field('Customer', customer)}"
            f'{_detail_field("Status", status, html_value=_status_pill(status))}'
            f"{_detail_field('Supervisor', supervisor)}"
            f"{_detail_field('Project Manager', job.get('project_manager'))}"
            f"{_detail_field('Location', job.get('location'))}"
            f"{_detail_field('Estimate #', estimate_no)}"
            f"</div>"
        )
        st.markdown(_dialog_card("Overview", overview_html), unsafe_allow_html=True)

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

    with tab_inventory:
        _render_job_inventory_tab(job)

    with tab_equipment:
        _render_job_equipment_tab(job)

    with tab_schedule:
        sched_html = (
            f'<div class="ips-detail-grid">'
            f"{_detail_field('Start Date', fmt_date(job.get('start_date')))}"
            f"{_detail_field('End Date', fmt_date(job.get('end_date')))}"
            f"{_detail_field('Location', job.get('location'))}"
            f"</div>"
        )
        st.markdown(_dialog_card("Schedule", sched_html), unsafe_allow_html=True)

    with tab_tasks:
        inject_tasks_module_css()
        render_job_linked_tasks_tab(job)

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
    status_opts = lookup_options("job_statuses")
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
            initial_location_id=str(job.get("customer_location_id") or ""),
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
    estimate_no = _safe_value(job.get("estimate_number"))
    schedule = _schedule_summary(job)

    st.markdown(
        '<span class="ips-dialog-shell ips-modal-wide" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="ips-dialog-header">'
        f'<div class="ips-dialog-title-row">'
        f"<div>"
        f'<h2 class="ips-dialog-title">{html.escape(jn)}</h2>'
        f'<p class="ips-dialog-subtitle">{html.escape(jname)}</p>'
        f"</div>"
        f"<div>{_status_pill(status)}</div>"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="ips-dialog-meta-grid">'
        f"{_dialog_meta_card('Customer', customer)}"
        f"{_dialog_meta_card('Supervisor', supervisor)}"
        f"{_dialog_meta_card('Estimate #', estimate_no)}"
        f"{_dialog_meta_card('Schedule', schedule)}"
        f"</div>",
        unsafe_allow_html=True,
    )

    if edit_mode:
        _render_job_edit_form(job)
    else:
        _render_job_actions_panel(job)
        if is_field_context():
            _render_field_job_detail_tabs(job)
        else:
            _render_job_detail_tabs(job)


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
    if is_field_context():
        inject_field_row_expand_css()
    all_jobs = load_jobs()
    filter_options = build_filter_options(all_jobs, _JOB_COLUMN_FILTER_SPECS)

    def _jobs_export() -> None:
        st.button("Export", key="jobs_export", use_container_width=True)

    def _jobs_new() -> None:
        if st.button("+ New Job", key="jobs_new", type="primary", use_container_width=True):
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
            with nc1:
                st.text_input("Job number", key="job_new_num")
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
                st.selectbox("Status", lookup_options("job_statuses"), key="job_new_status")
            with nc2:
                st.text_input("Supervisor", key="job_new_sup")
                st.date_input("Start date", key="job_new_start", value=None)
                st.date_input("End date", key="job_new_end", value=None)
            st.text_area("Description", key="job_new_desc")
            sb1, sb2 = st.columns(2)
            with sb1:
                if st.button("Save job", key="job_save_new", type="primary"):
                    ok, msg = persist_job(
                        {
                            "job_number": st.session_state.get("job_new_num"),
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
                        st.rerun()
            with sb2:
                if st.button("Cancel", key="job_cancel_new"):
                    st.session_state.pop("ips_job_form", None)
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

    layout_filter_bar(_filters)

    filtered = _filter_jobs(
        all_jobs,
        q=str(st.session_state.get("jobs_search") or "").strip(),
        view=str(st.session_state.get("jobs_view") or _JOBS_DEFAULT_VIEW),
    )

    render_table_pagination_header(len(filtered), _TABLE_KEY, item_label="job")
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

    _render_custom_jobs_table(page_rows, filter_options=filter_options)
    render_table_pagination_footer(len(filtered), _TABLE_KEY)

    if selected_job_id and st.session_state.get(SHOW_MODAL_KEY):
        _show_jobs_detail_modal()
