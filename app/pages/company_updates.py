"""Company Updates module (Phase 2C)."""

from __future__ import annotations

from datetime import date, datetime
from urllib.parse import urlparse

import streamlit as st

from app.components.company_update_detail_tabs import (
    _COMPANY_UPDATE_DETAIL_TAB_KEY,
    render_company_update_detail_tabs,
)
from app.components.company_updates_directory_table import (
    build_company_updates_html_table,
    company_update_detail_query_key,
    company_update_tab_query_key,
)
from app.components.company_updates_feed import PRIORITY_EDIT_OPTS, priority_for_form
from app.components.company_updates_permissions import (
    CompanyUpdatesPermissions,
    load_company_updates_permissions,
)
from app.components.headers import render_page_brand_header
from app.components.layout import render_filter_bar as layout_filter_bar
from app.components.record_modal import (
    clear_edit_modes,
    clear_record_modal,
    edit_mode_key,
    get_modal_record,
    is_edit_mode,
    open_record_modal,
    record_session_key,
    render_edit_form_header,
    render_missing_record,
    render_modal_edit_button,
    render_modal_header,
    render_modal_meta_grid,
    render_modal_shell,
    render_save_cancel_actions,
    set_view_mode,
    show_modal_if_pending,
)
from app.components.table_filters import (
    clear_table_filters,
    get_column_filter_values,
    render_table_header_cell,
)
from app.components.table_pagination import (
    pagination_meta,
    page_size_key,
    render_table_pagination_footer,
    render_table_pagination_header,
    reset_table_page,
)
from app.pages._core._crud import apply_persist_feedback, is_demo_id
from app.pages._core._session import select_key
from app.services.company_update_detail_service import (
    get_company_update_banner_preview,
    get_company_update_detail,
    put_update_in_modal_cache,
)
from app.services.company_updates_cache import invalidate_company_updates_cache
from app.services.company_updates_directory_service import (
    COMPANY_UPDATES_DEFAULT_PAGE_SIZE,
    list_company_updates_page,
    normalize_update_audience,
    normalize_update_category,
    normalize_update_status,
)
from app.services.updates_service import BANNER_UPLOAD_TYPES
from app.styles import inject_updates_module_css
from app.ui.streamlit_perf import fragment, fragment_rerun, ips_app_rerun

_SEL = select_key("company_updates")
_MODULE = "company_updates"
_TABLE_KEY = "company_updates_list"
_MODAL_KEY = "ips_cu_detail_modal_id"
_CACHE_KEY = "_ips_cu_modal_by_id"
SELECTED_UPDATE_KEY = "selected_update_id"
SHOW_UPDATE_MODAL_KEY = "show_update_detail_modal"
_DETAIL_QUERY_ERROR_KEY = "_ips_cu_detail_query_error"
_NEW_UPDATE_DIALOG_KEY = "ips_cu_new_dialog_open"
_FILTER_SNAPSHOT_KEY = "_cu_filter_snapshot"
_FILTER_FIELDS = ["category", "audience", "status"]
_COLUMN_FILTER_SPECS: list[tuple[str, str]] = [
    ("CATEGORY", "category"),
    ("AUDIENCE", "audience"),
    ("STATUS", "status"),
]
_CATEGORY_EDIT_OPTS = [
    "Announcement",
    "Safety Alert",
    "Event",
    "HR Update",
    "Project Update",
    "General",
]
_STATUS_EDIT_OPTS = ["Draft", "Published", "Scheduled", "Archived"]
_AUDIENCE_EDIT_OPTS = [
    "All",
    "Admin",
    "Supervisors",
    "Employees",
    "Field Crew",
    "Office",
    "Management",
]
_SORT_OPTS = ("Newest First", "Oldest First", "Title A–Z")
_DETAIL_TABS = (
    "Overview",
    "Audience",
    "Attachments",
    "Event Details",
    "Read Status",
    "Notes",
    "Activity",
)


def _status_to_active(status: str) -> bool:
    return status not in ("Archived", "Draft")


def _safe_attachment_url(url: str) -> bool:
    text = str(url or "").strip()
    if not text:
        return True
    parsed = urlparse(text)
    return parsed.scheme in ("http", "https")


def _parse_event_date(raw: object) -> date | None:
    text = str(raw or "").strip()
    if not text:
        return None
    for fmt, length in (("%Y-%m-%d", 10), ("%Y-%m-%dT%H:%M:%S", 19), ("%Y-%m-%d %H:%M:%S", 19)):
        try:
            return datetime.strptime(text[:length], fmt).date()
        except ValueError:
            continue
    return None


def _format_event_date_for_save(value: object) -> str:
    if isinstance(value, date):
        return value.isoformat()
    return str(value or "").strip()


def _company_updates_detail_pending() -> bool:
    return bool(
        st.session_state.get(SHOW_UPDATE_MODAL_KEY)
        or str(st.session_state.get(_MODAL_KEY) or "").strip()
    )


def _set_company_update_detail_tab_from_query(tab: str) -> None:
    raw = str(tab or "").strip()
    if not raw:
        return
    alias = {
        "overview": "Overview",
        "audience": "Audience",
        "attachments": "Attachments",
        "event": "Event Details",
        "event details": "Event Details",
        "read": "Read Status",
        "read status": "Read Status",
        "notes": "Notes",
        "activity": "Activity",
    }
    resolved = alias.get(raw.lower(), raw)
    if resolved in _DETAIL_TABS:
        st.session_state[_COMPANY_UPDATE_DETAIL_TAB_KEY] = resolved


def _open_company_update_modal(update_id: str, update: dict | None) -> None:
    uid = str(update_id or "").strip()
    if not uid:
        return
    st.session_state[SELECTED_UPDATE_KEY] = uid
    st.session_state[SHOW_UPDATE_MODAL_KEY] = True
    open_record_modal(
        uid,
        update if isinstance(update, dict) else None,
        session_select_key=_SEL,
        modal_key=_MODAL_KEY,
        module=_MODULE,
        id_fields=("id",),
    )


def _capture_company_update_detail_query(permissions: CompanyUpdatesPermissions) -> None:
    from app.perf_debug import perf_span

    detail_key = company_update_detail_query_key()
    tab_key = company_update_tab_query_key()
    with perf_span("company_updates.detail_lookup"):
        requested_id = str(st.query_params.get(detail_key) or "").strip()
        if not requested_id:
            return
        current_id = str(st.session_state.get(_MODAL_KEY) or st.session_state.get(SELECTED_UPDATE_KEY) or "").strip()
        if requested_id == current_id and st.session_state.get(SHOW_UPDATE_MODAL_KEY):
            tab_focus = str(st.query_params.get(tab_key) or "").strip()
            if tab_focus:
                _set_company_update_detail_tab_from_query(tab_focus)
            return
        detail = get_company_update_detail(
            requested_id,
            role=permissions.role,
            user_id=permissions.user_id,
        )
        if not detail:
            st.session_state[_DETAIL_QUERY_ERROR_KEY] = requested_id
            if detail_key in st.query_params:
                del st.query_params[detail_key]
            if tab_key in st.query_params:
                del st.query_params[tab_key]
            return
        put_update_in_modal_cache(requested_id, detail)
        _open_company_update_modal(requested_id, detail)
        st.session_state[_COMPANY_UPDATE_DETAIL_TAB_KEY] = "Overview"
        tab_focus = str(st.query_params.get(tab_key) or "").strip()
        if tab_focus:
            _set_company_update_detail_tab_from_query(tab_focus)


def _show_company_update_detail_query_error_if_any() -> None:
    if st.session_state.pop(_DETAIL_QUERY_ERROR_KEY, None):
        st.warning("The selected company update could not be found.")


def _clear_update_modal() -> None:
    st.session_state[SELECTED_UPDATE_KEY] = None
    st.session_state[SHOW_UPDATE_MODAL_KEY] = False
    clear_edit_modes(_MODULE)
    clear_record_modal(
        table_key=_TABLE_KEY,
        session_select_key=_SEL,
        modal_key=_MODAL_KEY,
        module=_MODULE,
    )
    detail_key = company_update_detail_query_key()
    tab_key = company_update_tab_query_key()
    if detail_key in st.query_params:
        del st.query_params[detail_key]
    if tab_key in st.query_params:
        del st.query_params[tab_key]


def _render_cu_banner_admin_controls(update: dict, *, rk: str, prefix: str) -> None:
    url = get_company_update_banner_preview(update)
    st.markdown("##### Banner image (optional)")
    if url:
        st.image(url, caption=str(update.get("banner_caption") or "") or None, use_container_width=True)
    st.text_input(
        "Banner caption (optional)",
        key=f"{prefix}_banner_caption_{rk}",
        placeholder="Short caption shown below the banner",
    )
    st.file_uploader(
        "Upload banner image",
        type=list(BANNER_UPLOAD_TYPES),
        key=f"{prefix}_banner_upload_{rk}",
        help="JPG, PNG, or WEBP — max 5 MB. Upload replaces any existing banner.",
    )
    if url and st.button("Remove banner", key=f"{prefix}_banner_remove_{rk}"):
        uid = str(update.get("id") or "")
        row_id = None if is_demo_id(uid) else uid
        if not row_id:
            st.warning("Sample updates cannot change banner storage.")
        else:
            from app.pages._core._data import remove_company_update_banner_row

            ok, msg = remove_company_update_banner_row(row_id, existing_row=update)
            if ok:
                invalidate_company_updates_cache(row_id)
                st.success(msg or "Banner removed.")
                ips_app_rerun()
            else:
                st.error(msg or "Could not remove banner.")


def _seed_cu_edit_form(update: dict) -> None:
    rk = record_session_key(update, "id")
    st.session_state[f"cu_edit_title_{rk}"] = str(update.get("title") or "")
    st.session_state[f"cu_edit_body_{rk}"] = str(update.get("body") or "")
    st.session_state[f"cu_edit_cat_{rk}"] = normalize_update_category(update.get("category"))
    st.session_state[f"cu_edit_status_{rk}"] = normalize_update_status(
        update.get("status"),
        is_active=update.get("is_active"),
    )
    st.session_state[f"cu_edit_audience_{rk}"] = normalize_update_audience(
        update.get("audience") or update.get("visibility")
    )
    event_date = _parse_event_date(update.get("event_date") or update.get("date"))
    st.session_state[f"cu_edit_event_date_{rk}"] = event_date
    st.session_state[f"cu_edit_pinned_{rk}"] = bool(update.get("pinned") or update.get("is_pinned"))
    st.session_state[f"cu_edit_notes_{rk}"] = str(update.get("notes") or "")
    st.session_state[f"cu_edit_priority_{rk}"] = priority_for_form(update.get("priority"))
    st.session_state[f"cu_edit_attachment_url_{rk}"] = str(update.get("attachment_url") or "")
    st.session_state[f"cu_edit_attachment_name_{rk}"] = str(update.get("attachment_file_name") or "")
    st.session_state[f"cu_edit_banner_caption_{rk}"] = str(update.get("banner_caption") or "")


def _render_cu_edit_form(update: dict, *, permissions: CompanyUpdatesPermissions) -> None:
    from app.pages._core._data import (
        delete_company_update,
        persist_company_update,
        persist_company_update_banner,
    )

    rk = record_session_key(update, "id")
    uid = str(update.get("id") or "")
    seed_key = f"_cu_edit_seeded_{rk}"
    detail_version = f"{uid}:{update.get('updated_at') or update.get('created_at') or ''}"
    if st.session_state.get(seed_key) != detail_version:
        _seed_cu_edit_form(update)
        st.session_state[seed_key] = detail_version

    render_edit_form_header("Edit Update")
    st.text_input("Title", key=f"cu_edit_title_{rk}")
    ec1, ec2 = st.columns(2)
    with ec1:
        st.selectbox("Category", _CATEGORY_EDIT_OPTS, key=f"cu_edit_cat_{rk}")
        st.selectbox("Status", _STATUS_EDIT_OPTS, key=f"cu_edit_status_{rk}")
    with ec2:
        st.selectbox("Audience", _AUDIENCE_EDIT_OPTS, key=f"cu_edit_audience_{rk}")
        st.date_input("Event date", key=f"cu_edit_event_date_{rk}", value=None)
        st.selectbox("Priority", PRIORITY_EDIT_OPTS, key=f"cu_edit_priority_{rk}")
    st.text_area("Body / content", key=f"cu_edit_body_{rk}", height=120)
    st.text_area("Notes", key=f"cu_edit_notes_{rk}", height=80)
    st.checkbox("Pinned", key=f"cu_edit_pinned_{rk}")
    ac1, ac2 = st.columns(2)
    with ac1:
        st.text_input("Attachment URL", key=f"cu_edit_attachment_url_{rk}", placeholder="https://…")
    with ac2:
        st.text_input("Attachment label", key=f"cu_edit_attachment_name_{rk}", placeholder="File name")
    _render_cu_banner_admin_controls(update, rk=rk, prefix="cu_edit")

    cancelled, saved = render_save_cancel_actions(
        module=_MODULE,
        record_key=rk,
        cancel_key=f"cu_edit_cancel_{rk}",
        save_key=f"cu_edit_save_{rk}",
    )
    if cancelled:
        ips_app_rerun()
    if saved:
        title = str(st.session_state.get(f"cu_edit_title_{rk}") or "").strip()
        if not title:
            st.error("Title is required.")
            return
        attachment_url = str(st.session_state.get(f"cu_edit_attachment_url_{rk}") or "").strip()
        if attachment_url and not _safe_attachment_url(attachment_url):
            st.error("Attachment URL must use http or https.")
            return
        status = str(st.session_state.get(f"cu_edit_status_{rk}") or "Published")
        ui = {
            "title": title,
            "body": st.session_state.get(f"cu_edit_body_{rk}"),
            "category": st.session_state.get(f"cu_edit_cat_{rk}"),
            "pinned": st.session_state.get(f"cu_edit_pinned_{rk}"),
            "status": status,
            "audience": st.session_state.get(f"cu_edit_audience_{rk}"),
            "event_date": _format_event_date_for_save(st.session_state.get(f"cu_edit_event_date_{rk}")),
            "notes": st.session_state.get(f"cu_edit_notes_{rk}"),
            "priority": st.session_state.get(f"cu_edit_priority_{rk}"),
            "attachment_url": attachment_url,
            "attachment_file_name": st.session_state.get(f"cu_edit_attachment_name_{rk}"),
            "banner_caption": st.session_state.get(f"cu_edit_banner_caption_{rk}"),
            "is_active": _status_to_active(status),
        }
        row_id = None if is_demo_id(uid) else uid
        from app.perf_debug import perf_span

        with perf_span("company_updates.save"):
            ok, msg = persist_company_update(ui, row_id=row_id)
        if ok:
            uploaded = st.session_state.get(f"cu_edit_banner_upload_{rk}")
            if uploaded is not None and row_id:
                with perf_span("company_updates.banner_upload"):
                    ok_banner, msg_banner = persist_company_update_banner(
                        row_id,
                        uploaded,
                        caption=str(st.session_state.get(f"cu_edit_banner_caption_{rk}") or ""),
                        existing_row=update,
                    )
                if not ok_banner:
                    st.warning(msg_banner or "Update saved, but banner upload failed.")
            invalidate_company_updates_cache(row_id)
            if row_id:
                fresh = get_company_update_detail(row_id, role=permissions.role, user_id=permissions.user_id)
                if fresh:
                    put_update_in_modal_cache(row_id, fresh)
            set_view_mode(_MODULE, rk)
            st.success(msg or "Update saved.")
            ips_app_rerun()
        else:
            st.error(msg or "Could not save update.")

    if not permissions.can_delete:
        return

    confirm_key = f"cu_delete_confirm_{rk}"
    if st.session_state.get(confirm_key):
        st.warning("Delete this update? This cannot be undone.")
        dc1, dc2 = st.columns(2)
        with dc1:
            if st.button("Confirm Delete", key=f"cu_edit_delete_confirm_{rk}", type="primary"):
                row_id = None if is_demo_id(uid) else uid
                if row_id:
                    from app.perf_debug import perf_span

                    with perf_span("company_updates.delete"):
                        ok, msg = delete_company_update(row_id)
                    if ok:
                        invalidate_company_updates_cache(row_id)
                        _clear_update_modal()
                        st.success(msg or "Update deleted.")
                        ips_app_rerun()
                    else:
                        st.error(msg or "Could not delete update.")
                else:
                    st.warning("Sample updates cannot be deleted.")
        with dc2:
            if st.button("Cancel", key=f"cu_edit_delete_cancel_{rk}"):
                st.session_state[confirm_key] = False
                ips_app_rerun()
    elif st.button("Delete update", key=f"cu_edit_delete_{rk}", type="secondary"):
        st.session_state[confirm_key] = True
        ips_app_rerun()


def render_company_update_detail_dialog(
    update: dict,
    *,
    permissions: CompanyUpdatesPermissions | None = None,
) -> None:
    perms = permissions or load_company_updates_permissions()
    rk = record_session_key(update, "id")
    st.session_state.setdefault(edit_mode_key(_MODULE, rk), False)
    edit_mode = is_edit_mode(_MODULE, rk)

    category = normalize_update_category(update.get("category"))
    status = normalize_update_status(update.get("status"), is_active=update.get("is_active"))

    render_modal_shell()
    render_modal_header(
        title=str(update.get("title") or "Update"),
        subtitle=category,
        status=status,
    )
    if perms.can_manage:
        render_modal_edit_button(
            module=_MODULE,
            record_key=rk,
            key_prefix=f"cu_modal_{rk}",
        )
    render_modal_meta_grid(
        [
            ("Category", category),
            ("Audience", normalize_update_audience(update.get("audience") or update.get("visibility"))),
            ("Created", update.get("created_display")),
            ("Event Date", update.get("event_date_display")),
        ]
    )

    if edit_mode and perms.can_edit:
        _render_cu_edit_form(update, permissions=perms)
    else:
        default_tab = str(st.session_state.get(_COMPANY_UPDATE_DETAIL_TAB_KEY) or "Overview")
        render_company_update_detail_tabs(update, permissions=perms, default_tab=default_tab)


@st.dialog("Company Update Details", width="large", on_dismiss=_clear_update_modal)
def _show_update_detail_modal() -> None:
    permissions = load_company_updates_permissions()
    update = get_modal_record(
        cache_key=_CACHE_KEY,
        modal_key=_MODAL_KEY,
        session_select_key=_SEL,
    )
    if not update:
        render_missing_record(_clear_update_modal, close_key="cu_modal_missing_close")
        return
    render_company_update_detail_dialog(update, permissions=permissions)


@st.dialog("New Company Update", width="large")
def _show_new_company_update_dialog() -> None:
    from app.pages._core._data import persist_company_update_banner, persist_company_update_record

    st.text_input("Title", key="cu_new_title")
    nc1, nc2 = st.columns(2)
    with nc1:
        st.selectbox("Category", _CATEGORY_EDIT_OPTS, key="cu_new_cat")
        st.selectbox("Status", _STATUS_EDIT_OPTS, key="cu_new_status")
    with nc2:
        st.selectbox("Audience", _AUDIENCE_EDIT_OPTS, key="cu_new_audience")
        st.date_input("Event date", key="cu_new_event_date", value=None)
        st.selectbox("Priority", PRIORITY_EDIT_OPTS, key="cu_new_priority", index=2)
    st.text_area("Body / content", key="cu_new_body", height=100)
    st.text_area("Notes", key="cu_new_notes", height=60)
    st.checkbox("Pinned", key="cu_new_pinned")
    na1, na2 = st.columns(2)
    with na1:
        st.text_input("Attachment URL", key="cu_new_attachment_url", placeholder="https://…")
    with na2:
        st.text_input("Attachment label", key="cu_new_attachment_name", placeholder="File name")
    st.text_input(
        "Banner caption (optional)",
        key="cu_new_banner_caption",
        placeholder="Short caption shown below the banner",
    )
    st.file_uploader(
        "Upload banner image",
        type=list(BANNER_UPLOAD_TYPES),
        key="cu_new_banner_upload",
        help="JPG, PNG, or WEBP — max 5 MB.",
    )
    btn1, btn2 = st.columns(2)
    with btn1:
        publish = st.button("Save / Publish", key="cu_save_new", type="primary", use_container_width=True)
    with btn2:
        cancel = st.button("Cancel", key="cu_new_cancel", use_container_width=True)
    if cancel:
        st.session_state[_NEW_UPDATE_DIALOG_KEY] = False
        ips_app_rerun()
    if publish:
        title = str(st.session_state.get("cu_new_title") or "").strip()
        if not title:
            st.error("Title is required.")
            return
        attachment_url = str(st.session_state.get("cu_new_attachment_url") or "").strip()
        if attachment_url and not _safe_attachment_url(attachment_url):
            st.error("Attachment URL must use http or https.")
            return
        status = str(st.session_state.get("cu_new_status") or "Published")
        ui = {
            "title": title,
            "body": st.session_state.get("cu_new_body"),
            "category": st.session_state.get("cu_new_cat"),
            "pinned": st.session_state.get("cu_new_pinned"),
            "status": status,
            "audience": st.session_state.get("cu_new_audience"),
            "event_date": _format_event_date_for_save(st.session_state.get("cu_new_event_date")),
            "notes": st.session_state.get("cu_new_notes"),
            "priority": st.session_state.get("cu_new_priority"),
            "attachment_url": attachment_url,
            "attachment_file_name": st.session_state.get("cu_new_attachment_name"),
            "banner_caption": st.session_state.get("cu_new_banner_caption"),
            "is_active": _status_to_active(status),
        }
        from app.perf_debug import perf_span

        with perf_span("company_updates.save"):
            ok, msg, saved = persist_company_update_record(ui)
        if not ok:
            st.error(msg or "Could not publish update.")
            return
        saved_id = str(saved.get("id") or "")
        uploaded = st.session_state.get("cu_new_banner_upload")
        if uploaded is not None and saved_id and not is_demo_id(saved_id):
            with perf_span("company_updates.banner_upload"):
                ok_banner, msg_banner = persist_company_update_banner(
                    saved_id,
                    uploaded,
                    caption=str(st.session_state.get("cu_new_banner_caption") or ""),
                )
            if not ok_banner:
                st.warning(msg_banner or "Update published, but banner upload failed.")
        invalidate_company_updates_cache(saved_id or None)
        st.session_state[_NEW_UPDATE_DIALOG_KEY] = False
        if apply_persist_feedback(True, msg):
            ips_app_rerun()


def _maybe_reset_cu_page_on_filter_change() -> None:
    current = (
        str(st.session_state.get("cu_search") or ""),
        str(st.session_state.get("cu_sort") or "Newest First"),
        tuple(get_column_filter_values(_TABLE_KEY, field) for field in _FILTER_FIELDS),
    )
    prev = st.session_state.get(_FILTER_SNAPSHOT_KEY)
    if prev is not None and prev != current:
        reset_table_page(_TABLE_KEY)
    st.session_state[_FILTER_SNAPSHOT_KEY] = current


def _render_company_updates_table_column_filters(*, filter_options: dict[str, list[str]]) -> None:
    st.markdown('<div class="ips-updates-table-filter-toolbar">', unsafe_allow_html=True)
    cols = st.columns(len(_COLUMN_FILTER_SPECS), gap="small")
    for col, (label, field) in zip(cols, _COLUMN_FILTER_SPECS):
        with col:
            render_table_header_cell(
                label,
                table_key=_TABLE_KEY,
                filter_field=field,
                filter_options=filter_options.get(field, []),
                base_class="ips-updates-filter-toolbar-cell",
            )
    st.markdown("</div>", unsafe_allow_html=True)


@fragment
def _render_company_updates_directory_fragment(permissions: CompanyUpdatesPermissions) -> None:
    from app.perf_debug import perf_span

    def _filters() -> None:
        c1, c2, c3 = st.columns([5, 0.6, 1])
        with c1:
            st.text_input(
                "Search",
                placeholder="Search updates...",
                key="cu_search",
                label_visibility="collapsed",
            )
        with c2:
            if st.button("Clear", key="cu_clear", use_container_width=True):
                clear_table_filters(
                    _TABLE_KEY,
                    _FILTER_FIELDS,
                    extra_keys=["cu_search", "cu_sort"],
                )
                st.session_state["cu_sort"] = "Newest First"
                reset_table_page(_TABLE_KEY)
                fragment_rerun()
        with c3:
            st.selectbox(
                "Sort",
                _SORT_OPTS,
                key="cu_sort",
                label_visibility="collapsed",
            )

    _maybe_reset_cu_page_on_filter_change()
    layout_filter_bar(_filters)

    if page_size_key(_TABLE_KEY) not in st.session_state:
        st.session_state[page_size_key(_TABLE_KEY)] = COMPANY_UPDATES_DEFAULT_PAGE_SIZE

    search = str(st.session_state.get("cu_search") or "").strip()
    sort = str(st.session_state.get("cu_sort") or "Newest First")
    categories = get_column_filter_values(_TABLE_KEY, "category")
    audiences = get_column_filter_values(_TABLE_KEY, "audience")
    statuses = get_column_filter_values(_TABLE_KEY, "status")
    page_num, page_size, _ = pagination_meta(
        0,
        _TABLE_KEY,
        default_page_size=COMPANY_UPDATES_DEFAULT_PAGE_SIZE,
    )

    with perf_span("company_updates.list_query"):
        cu_page = list_company_updates_page(
            search=search,
            categories=categories,
            audiences=audiences,
            statuses=statuses,
            sort=sort,
            page=page_num,
            page_size=page_size,
        )

    page_num, page_size, _ = pagination_meta(
        cu_page.total_count,
        _TABLE_KEY,
        default_page_size=COMPANY_UPDATES_DEFAULT_PAGE_SIZE,
    )
    if page_num != cu_page.page or page_size != cu_page.page_size:
        with perf_span("company_updates.list_query"):
            cu_page = list_company_updates_page(
                search=search,
                categories=categories,
                audiences=audiences,
                statuses=statuses,
                sort=sort,
                page=page_num,
                page_size=page_size,
            )

    if cu_page.warning:
        st.caption(cu_page.warning)

    with perf_span("company_updates.pagination"):
        render_table_pagination_header(
            cu_page.total_count,
            _TABLE_KEY,
            item_label="update",
        )

    page_rows = cu_page.rows
    for row in page_rows:
        put_update_in_modal_cache(str(row.get("id") or "").strip(), row)

    with st.container(key="company_updates_table_wrap"):
        if not page_rows:
            st.info("No updates match your filters.")
        else:
            _render_company_updates_table_column_filters(filter_options=cu_page.filter_options)
            with perf_span("company_updates.table_html"):
                st.markdown(build_company_updates_html_table(page_rows), unsafe_allow_html=True)

    render_table_pagination_footer(cu_page.total_count, _TABLE_KEY)


def render() -> None:
    from app.pages._core._access import begin_module
    from app.perf_debug import perf_span

    if not begin_module("company_updates"):
        return

    with perf_span("company_updates.page_shell"):
        inject_updates_module_css()
        st.markdown(
            '<span class="ips-updates-page ips-page-shell-marker" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )

    with perf_span("company_updates.permissions"):
        permissions = load_company_updates_permissions()

    def _cu_new() -> None:
        if st.button("+ New Update", key="cu_new", type="primary", use_container_width=True):
            st.session_state[_NEW_UPDATE_DIALOG_KEY] = True
            ips_app_rerun()

    render_page_brand_header(
        "Company Updates",
        "Share announcements, safety alerts, events, and company news.",
        actions=[_cu_new] if permissions.can_create else [],
    )

    _capture_company_update_detail_query(permissions)
    _show_company_update_detail_query_error_if_any()

    if _company_updates_detail_pending():
        if st.session_state.get(_NEW_UPDATE_DIALOG_KEY):
            _show_new_company_update_dialog()
        show_modal_if_pending(_MODAL_KEY, _show_update_detail_modal)
        return

    if st.session_state.get(_NEW_UPDATE_DIALOG_KEY):
        _show_new_company_update_dialog()

    _render_company_updates_directory_fragment(permissions)

    if _company_updates_detail_pending():
        show_modal_if_pending(_MODAL_KEY, _show_update_detail_modal)
