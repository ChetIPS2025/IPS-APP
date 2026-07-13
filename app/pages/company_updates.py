"""Company Updates module (Phase 2C)."""

from __future__ import annotations

import html

import streamlit as st

from app.components.headers import render_page_brand_header
from app.components.layout import render_filter_bar as layout_filter_bar
from app.components.table_filters import (
    apply_column_filters,
    build_filter_options,
    clear_table_filters,
    render_table_header_cell,
)
from app.components.record_modal import (
    build_modal_cache,
    clear_edit_modes,
    clear_record_modal,
    detail_field_html,
    dialog_card_html,
    edit_mode_key,
    get_modal_record,
    is_edit_mode,
    open_record_modal,
    placeholder_html,
    record_session_key,
    render_edit_form_header,
    render_modal_edit_button,
    render_modal_header,
    render_modal_meta_grid,
    render_modal_shell,
    render_missing_record,
    render_save_cancel_actions,
    set_edit_mode,
    set_view_mode,
)
from app.pages._core._data import (
    delete_company_update,
    load_company_updates,
    load_employees,
    persist_company_update,
    persist_company_update_banner,
    persist_company_update_record,
    remove_company_update_banner_row,
)
from app.pages._core._crud import apply_persist_feedback, is_demo_id
from app.pages._core._session import select_key
from app.styles import inject_updates_module_css
from app.utils.formatting import fmt_date, fmt_datetime
from app.utils.permissions import can_manage_company_updates
from app.components.company_updates_feed import PRIORITY_EDIT_OPTS, priority_for_form
from app.services.updates_service import BANNER_UPLOAD_TYPES, resolve_company_update_banner_url
from app.auth import current_role, effective_role
_SEL = select_key("company_updates")
_MODULE = "company_updates"
_TABLE_KEY = "company_updates_list"
_MODAL_KEY = "ips_cu_detail_modal_id"
_CACHE_KEY = "_ips_cu_modal_by_id"
SELECTED_UPDATE_KEY = "selected_update_id"
SHOW_UPDATE_MODAL_KEY = "show_update_detail_modal"
_ALL_UPDATE_IDS_KEY = "_ips_updates_visible_ids"
_UPD_COLS = [0.35, 3.2, 1.5, 1.6, 1.2, 1.4, 1.7, 1.3]
_UPD_HEADER_SPECS: list[tuple[str, str | None]] = [
    ("", None),
    ("TITLE", None),
    ("CATEGORY", "category"),
    ("AUDIENCE", "audience"),
    ("STATUS", "status"),
    ("EVENT DATE", None),
    ("CREATED BY", None),
    ("CREATED", None),
]
_FILTER_FIELDS = ["category", "audience", "status"]
_COLUMN_FILTER_SPECS: list[tuple[str, object]] = [
    ("category", lambda r: _normalize_update_category(r.get("category"))),
    ("audience", lambda r: _normalize_audience(r.get("audience") or r.get("visibility"))),
    ("status", lambda r: _normalize_update_status(r.get("status"), is_active=r.get("is_active"))),
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


def _can_manage_company_updates() -> bool:
    return can_manage_company_updates(effective_role())


def _update_banner_url(update: dict) -> str:
    return str(update.get("banner_view_url") or resolve_company_update_banner_url(update) or "").strip()


@st.dialog("Banner image", width="large")
def _show_banner_preview_dialog(url: str, caption: str = "") -> None:
    st.image(url, use_container_width=True)
    if caption:
        st.caption(caption)


def _render_cu_banner_view(update: dict) -> None:
    url = _update_banner_url(update)
    if not url:
        return
    caption = str(update.get("banner_caption") or "").strip()
    rk = record_session_key(update, "id")
    alt = html.escape(caption or str(update.get("title") or "Update banner"))
    figcaption = (
        f"<figcaption class=\"ips-cu-banner-caption\">{html.escape(caption)}</figcaption>"
        if caption
        else ""
    )
    st.markdown(
        f'<figure class="ips-cu-banner-figure">'
        f'<a href="{html.escape(url)}" target="_blank" rel="noopener" class="ips-cu-banner-link">'
        f'<img class="ips-cu-banner-detail" src="{html.escape(url)}" alt="{alt}" />'
        f"</a>"
        f"{figcaption}"
        f"</figure>",
        unsafe_allow_html=True,
    )
    if st.button("View full size", key=f"cu_banner_full_{rk}"):
        _show_banner_preview_dialog(url, caption)


def _render_cu_banner_admin_controls(update: dict, *, rk: str, prefix: str) -> None:
    url = _update_banner_url(update)
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
            ok, msg = remove_company_update_banner_row(row_id, existing_row=update)
            if ok:
                st.success(msg or "Banner removed.")
                st.rerun()
            else:
                st.error(msg or "Could not remove banner.")


def _user_name_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for emp in load_employees():
        eid = str(emp.get("id") or "").strip()
        name = str(emp.get("name") or "").strip()
        if eid and name:
            lookup[eid] = name
        email = str(emp.get("email") or "").strip().lower()
        if email and name:
            lookup[email] = name
    return lookup


def _normalize_update_category(raw: object) -> str:
    s = str(raw or "").strip().lower()
    if s in ("", "general"):
        return "General"
    if "announcement" in s:
        return "Announcement"
    if "safety" in s:
        return "Safety Alert"
    if "event" in s:
        return "Event"
    if "hr" in s:
        return "HR Update"
    if "project" in s:
        return "Project Update"
    return "General"


def _normalize_update_status(raw: object, *, is_active: object = None) -> str:
    s = str(raw or "").strip().lower()
    if s in ("published", "active"):
        return "Published"
    if s == "draft":
        return "Draft"
    if s == "scheduled":
        return "Scheduled"
    if s in ("archived", "inactive"):
        return "Archived"
    if is_active is False:
        return "Archived"
    return "Published"


def _normalize_audience(raw: object) -> str:
    s = str(raw or "").strip()
    if not s:
        return "All"
    known = {
        "all": "All",
        "admin": "Admin",
        "supervisors": "Supervisors",
        "supervisor": "Supervisors",
        "employees": "Employees",
        "employee": "Employees",
        "field crew": "Field Crew",
        "field": "Field Crew",
        "office": "Office",
        "management": "Management",
    }
    return known.get(s.lower(), s)


def _resolve_created_by(row: dict, lookup: dict[str, str]) -> str:
    raw = row.get("created_by_name") or row.get("created_by") or row.get("author") or row.get("author_name")
    if raw is None:
        return "—"
    text = str(raw).strip()
    if not text:
        return "—"
    if text in lookup:
        return lookup[text]
    if len(text) >= 32 and text.count("-") >= 4:
        return lookup.get(text, "—")
    return text


def _fmt_event_date(row: dict) -> str:
    raw = row.get("event_date") or row.get("event_at") or row.get("event_datetime")
    if not raw and _normalize_update_category(row.get("category")) == "Event":
        raw = row.get("date")
    if not raw:
        return "—"
    text = str(raw).strip()
    if "T" in text or " " in text:
        return fmt_datetime(text)
    return fmt_date(text)


def _fmt_created_date(row: dict) -> str:
    return fmt_date(row.get("created_at") or row.get("created_date") or row.get("date"))


def _build_update_row(row: dict, lookup: dict[str, str]) -> dict:
    category = _normalize_update_category(row.get("category"))
    status = _normalize_update_status(row.get("status"), is_active=row.get("is_active"))
    audience = _normalize_audience(row.get("audience") or row.get("visibility"))
    is_pinned = bool(row.get("pinned") or row.get("is_pinned"))
    return {
        **row,
        "title": str(row.get("title") or row.get("subject") or "Untitled Update"),
        "category": category,
        "audience": audience,
        "status": status,
        "event_date_display": _fmt_event_date(row),
        "created_by_display": _resolve_created_by(row, lookup),
        "created_display": _fmt_created_date(row),
        "is_pinned": is_pinned,
    }


def _category_pill_html(category: str) -> str:
    cls_map = {
        "Announcement": "ips-update-category-announcement",
        "Safety Alert": "ips-update-category-safety-alert",
        "Event": "ips-update-category-event",
        "HR Update": "ips-update-category-hr-update",
        "Project Update": "ips-update-category-project-update",
        "General": "ips-update-category-general",
    }
    cls = cls_map.get(category, "ips-update-category-general")
    return f'<span class="ips-update-pill {cls}">{html.escape(category)}</span>'


def _status_pill_html(status: str) -> str:
    cls_map = {
        "Published": "ips-update-status-published",
        "Draft": "ips-update-status-draft",
        "Scheduled": "ips-update-status-scheduled",
        "Archived": "ips-update-status-archived",
    }
    cls = cls_map.get(status, "ips-update-status-published")
    return f'<span class="ips-update-pill {cls}">{html.escape(status)}</span>'


def _title_cell_html(title: str, is_pinned: bool) -> str:
    pinned = '<span class="ips-update-pinned">Pinned</span>' if is_pinned else ""
    return f'<div class="ips-updates-title">{html.escape(title)}{pinned}</div>'


def _sort_updates(rows: list[dict], sort: str) -> list[dict]:
    out = list(rows)
    if sort == "Oldest First":
        return sorted(out, key=lambda u: str(u.get("created_display") or u.get("date") or ""))
    if sort == "Title A–Z":
        return sorted(out, key=lambda u: str(u.get("title") or "").lower())
    return sorted(
        out,
        key=lambda u: str(u.get("created_display") or u.get("date") or ""),
        reverse=True,
    )


def _update_select_key(update_id: str) -> str:
    return f"update_select_{update_id}"


def _clear_update_selection(update_ids: list[str] | None = None) -> None:
    st.session_state[SELECTED_UPDATE_KEY] = None
    st.session_state[SHOW_UPDATE_MODAL_KEY] = False
    ids = list(update_ids or [])
    for uid in ids:
        st.session_state[_update_select_key(uid)] = False
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and key.startswith("update_select_"):
            st.session_state[key] = False


def _on_update_checkbox_change(update_id: str, all_update_ids: list[str]) -> None:
    key = _update_select_key(update_id)
    if st.session_state.get(key):
        for uid in all_update_ids:
            if uid != update_id:
                st.session_state[_update_select_key(uid)] = False
        st.session_state[SELECTED_UPDATE_KEY] = update_id
        st.session_state[SHOW_UPDATE_MODAL_KEY] = True
        st.session_state[_MODAL_KEY] = update_id
        cache = st.session_state.get(_CACHE_KEY) or {}
        update = cache.get(update_id) if isinstance(cache, dict) else None
        open_record_modal(
            update_id,
            update if isinstance(update, dict) else None,
            session_select_key=_SEL,
            modal_key=_MODAL_KEY,
            module=_MODULE,
            id_fields=("id",),
        )
    elif st.session_state.get(SELECTED_UPDATE_KEY) == update_id:
        st.session_state[SELECTED_UPDATE_KEY] = None
        st.session_state[SHOW_UPDATE_MODAL_KEY] = False


def _clear_update_modal() -> None:
    update_ids = st.session_state.get(_ALL_UPDATE_IDS_KEY) or []
    _clear_update_selection([str(uid) for uid in update_ids])
    clear_edit_modes(_MODULE)
    clear_record_modal(
        table_key=_TABLE_KEY,
        session_select_key=_SEL,
        modal_key=_MODAL_KEY,
        module=_MODULE,
    )


def _status_to_active(status: str) -> bool:
    return status not in ("Archived", "Draft")


def _seed_cu_edit_form(update: dict) -> None:
    rk = record_session_key(update, "id")
    st.session_state[f"cu_edit_title_{rk}"] = str(update.get("title") or "")
    st.session_state[f"cu_edit_body_{rk}"] = str(update.get("body") or "")
    st.session_state[f"cu_edit_cat_{rk}"] = _normalize_update_category(update.get("category"))
    st.session_state[f"cu_edit_status_{rk}"] = _normalize_update_status(
        update.get("status"),
        is_active=update.get("is_active"),
    )
    st.session_state[f"cu_edit_audience_{rk}"] = _normalize_audience(
        update.get("audience") or update.get("visibility")
    )
    st.session_state[f"cu_edit_event_date_{rk}"] = str(
        update.get("event_date") or update.get("date") or ""
    )[:10]
    st.session_state[f"cu_edit_pinned_{rk}"] = bool(update.get("pinned") or update.get("is_pinned"))
    st.session_state[f"cu_edit_notes_{rk}"] = str(update.get("notes") or "")
    st.session_state[f"cu_edit_priority_{rk}"] = priority_for_form(update.get("priority"))
    st.session_state[f"cu_edit_attachment_url_{rk}"] = str(update.get("attachment_url") or "")
    st.session_state[f"cu_edit_attachment_name_{rk}"] = str(update.get("attachment_file_name") or "")
    st.session_state[f"cu_edit_banner_caption_{rk}"] = str(update.get("banner_caption") or "")


def _render_cu_view_tabs(update: dict) -> None:
    category = _normalize_update_category(update.get("category"))
    status = _normalize_update_status(update.get("status"), is_active=update.get("is_active"))
    audience = _normalize_audience(update.get("audience") or update.get("visibility"))
    is_pinned = bool(update.get("pinned") or update.get("is_pinned"))
    body = str(update.get("body") or "").strip() or "No message body."
    attachment_url = str(update.get("attachment_url") or "").strip()
    attachment_name = str(update.get("attachment_file_name") or "").strip()
    body_html = (
        '<p style="margin:0;font-size:0.875rem;color:#0f172a;line-height:1.5;white-space:pre-wrap;">'
        f"{html.escape(body)}"
        "</p>"
    )

    tab_overview, tab_audience, tab_attachments, tab_event, tab_read, tab_notes, tab_activity = st.tabs(
        ["Overview", "Audience", "Attachments", "Event Details", "Read Status", "Notes", "Activity"]
    )

    with tab_overview:
        _render_cu_banner_view(update)
        overview_html = (
            '<div class="ips-detail-grid">'
            f"{detail_field_html('Title', update.get('title'))}"
            f'{detail_field_html("Category", category, html_value=_category_pill_html(category))}'
            f'{detail_field_html("Status", status, html_value=_status_pill_html(status))}'
            f"{detail_field_html('Created By', update.get('created_by_display'))}"
            f"{detail_field_html('Created', update.get('created_display'))}"
            f"{detail_field_html('Priority', priority_for_form(update.get('priority')))}"
            f"{detail_field_html('Pinned', 'Yes' if is_pinned else 'No')}"
            "</div>"
        )
        st.markdown(dialog_card_html("Overview", overview_html), unsafe_allow_html=True)
        st.markdown(dialog_card_html("Content", body_html), unsafe_allow_html=True)

    with tab_audience:
        audience_html = (
            '<div class="ips-detail-grid">'
            f"{detail_field_html('Audience', audience)}"
            f"{detail_field_html('Departments / Roles', update.get('departments') or '—')}"
            "</div>"
        )
        st.markdown(dialog_card_html("Audience", audience_html), unsafe_allow_html=True)

    with tab_attachments:
        if attachment_url:
            label = attachment_name or "Download attachment"
            st.markdown(
                dialog_card_html(
                    "Attachments",
                    f'<a href="{html.escape(attachment_url)}" target="_blank" rel="noopener">'
                    f"{html.escape(label)}</a>",
                ),
                unsafe_allow_html=True,
            )
        else:
            placeholder_html("No attachments for this update.")

    with tab_event:
        if category == "Event" or update.get("event_date") or update.get("event_at"):
            event_html = (
                '<div class="ips-detail-grid">'
                f"{detail_field_html('Event Date', update.get('event_date_display'))}"
                f"{detail_field_html('Location', update.get('event_location') or update.get('location') or '—')}"
                "</div>"
            )
            st.markdown(dialog_card_html("Event Details", event_html), unsafe_allow_html=True)
        else:
            st.caption("No event details for this update.")

    with tab_read:
        read_flag = "Unread" if update.get("is_new") else "Read"
        st.markdown(
            dialog_card_html(
                "Read Status",
                f'<div class="ips-detail-grid">{detail_field_html("Your Status", read_flag)}</div>',
            ),
            unsafe_allow_html=True,
        )
        placeholder_html("Read receipts and viewer history will appear here when connected to Supabase.")

    with tab_notes:
        notes = str(update.get("notes") or "").strip()
        if notes:
            st.markdown(
                dialog_card_html(
                    "Notes",
                    f'<p style="margin:0;white-space:pre-wrap;">{html.escape(notes)}</p>',
                ),
                unsafe_allow_html=True,
            )
        else:
            placeholder_html("Notes will appear here when added.")

    with tab_activity:
        placeholder_html("Created and updated activity will appear here when connected to Supabase.")


def _render_cu_edit_form(update: dict) -> None:
    rk = record_session_key(update, "id")
    uid = str(update.get("id") or "")
    if f"cu_edit_title_{rk}" not in st.session_state:
        _seed_cu_edit_form(update)

    render_edit_form_header("Edit Update")
    st.text_input("Title", key=f"cu_edit_title_{rk}")
    ec1, ec2 = st.columns(2)
    with ec1:
        st.selectbox("Category", _CATEGORY_EDIT_OPTS, key=f"cu_edit_cat_{rk}")
        st.selectbox("Status", _STATUS_EDIT_OPTS, key=f"cu_edit_status_{rk}")
    with ec2:
        st.selectbox("Audience", _AUDIENCE_EDIT_OPTS, key=f"cu_edit_audience_{rk}")
        st.text_input("Event date", key=f"cu_edit_event_date_{rk}", placeholder="YYYY-MM-DD")
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
        st.rerun()
    if saved:
        status = str(st.session_state.get(f"cu_edit_status_{rk}") or "Published")
        ui = {
            "title": st.session_state.get(f"cu_edit_title_{rk}"),
            "body": st.session_state.get(f"cu_edit_body_{rk}"),
            "category": st.session_state.get(f"cu_edit_cat_{rk}"),
            "pinned": st.session_state.get(f"cu_edit_pinned_{rk}"),
            "status": status,
            "audience": st.session_state.get(f"cu_edit_audience_{rk}"),
            "event_date": st.session_state.get(f"cu_edit_event_date_{rk}"),
            "notes": st.session_state.get(f"cu_edit_notes_{rk}"),
            "priority": st.session_state.get(f"cu_edit_priority_{rk}"),
            "attachment_url": st.session_state.get(f"cu_edit_attachment_url_{rk}"),
            "attachment_file_name": st.session_state.get(f"cu_edit_attachment_name_{rk}"),
            "banner_caption": st.session_state.get(f"cu_edit_banner_caption_{rk}"),
            "is_active": _status_to_active(status),
        }
        row_id = None if is_demo_id(uid) else uid
        ok, msg = persist_company_update(ui, row_id=row_id)
        if ok:
            uploaded = st.session_state.get(f"cu_edit_banner_upload_{rk}")
            if uploaded is not None and row_id:
                ok_banner, msg_banner = persist_company_update_banner(
                    row_id,
                    uploaded,
                    caption=str(st.session_state.get(f"cu_edit_banner_caption_{rk}") or ""),
                    existing_row=update,
                )
                if not ok_banner:
                    st.warning(msg_banner or "Update saved, but banner upload failed.")
            set_view_mode(_MODULE, rk)
            st.success(msg or "Update saved.")
            st.rerun()
        else:
            st.error(msg or "Could not save update.")

    if uid and st.button("Delete update", key=f"cu_edit_delete_{rk}", type="secondary"):
        row_id = None if is_demo_id(uid) else uid
        if row_id:
            ok, msg = delete_company_update(row_id)
            if ok:
                _clear_update_modal()
                st.success(msg or "Update deleted.")
                st.rerun()
            else:
                st.error(msg or "Could not delete update.")
        else:
            st.warning("Sample updates cannot be deleted.")


def render_company_update_detail_dialog(update: dict) -> None:
    rk = record_session_key(update, "id")
    st.session_state.setdefault(edit_mode_key(_MODULE, rk), False)
    edit_mode = is_edit_mode(_MODULE, rk)

    category = _normalize_update_category(update.get("category"))
    status = _normalize_update_status(update.get("status"), is_active=update.get("is_active"))

    render_modal_shell()
    render_modal_header(
        title=str(update.get("title") or "Update"),
        subtitle=category,
        status=status,
    )
    if _can_manage_company_updates():
        render_modal_edit_button(
            module=_MODULE,
            record_key=rk,
            key_prefix=f"cu_modal_{rk}",
        )
    render_modal_meta_grid(
        [
            ("Category", category),
            ("Audience", _normalize_audience(update.get("audience") or update.get("visibility"))),
            ("Created", update.get("created_display")),
            ("Event Date", update.get("event_date_display")),
        ]
    )

    if edit_mode and _can_manage_company_updates():
        _render_cu_edit_form(update)
    else:
        _render_cu_view_tabs(update)


@st.dialog("Company Update Details", width="large", on_dismiss=_clear_update_modal)
def _show_update_detail_modal() -> None:
    update = get_modal_record(
        cache_key=_CACHE_KEY,
        modal_key=_MODAL_KEY,
        session_select_key=_SEL,
    )
    if not update:
        render_missing_record(_clear_update_modal, close_key="cu_modal_missing_close")
        return
    render_company_update_detail_dialog(update)


def _filter_updates(
    updates: list[dict],
    *,
    q: str,
    sort: str,
) -> list[dict]:
    rows = updates
    if q:
        ql = q.lower()
        rows = [
            r
            for r in rows
            if ql in str(r.get("title") or "").lower()
            or ql in str(r.get("body") or "").lower()
            or ql in str(r.get("category") or "").lower()
            or ql in str(r.get("audience") or "").lower()
            or ql in str(r.get("created_by_display") or "").lower()
            or ql in str(r.get("status") or "").lower()
        ]
    rows = apply_column_filters(rows, _TABLE_KEY, _COLUMN_FILTER_SPECS)
    return _sort_updates(rows, sort)


def _render_custom_updates_table(
    filtered: list[dict],
    *,
    filter_options: dict[str, list[str]],
) -> list[str]:
    if not filtered:
        st.info("No updates match your filters.")
        st.session_state[_ALL_UPDATE_IDS_KEY] = []
        return []

    all_update_ids = [
        str(u.get("id") or "").strip() for u in filtered if str(u.get("id") or "").strip()
    ]
    st.session_state[_ALL_UPDATE_IDS_KEY] = all_update_ids

    with st.container(key="updates_table_wrap"):
        st.markdown('<div class="ips-updates-table-wrap">', unsafe_allow_html=True)

        header_cols = st.columns(_UPD_COLS, gap="small", vertical_alignment="center")
        for col, (label, field) in zip(header_cols, _UPD_HEADER_SPECS):
            with col:
                if field:
                    render_table_header_cell(
                        label,
                        table_key=_TABLE_KEY,
                        filter_field=field,
                        filter_options=filter_options.get(field, []),
                        base_class="ips-updates-header-row ips-updates-cell",
                    )
                else:
                    render_table_header_cell(
                        label,
                        base_class="ips-updates-header-row ips-updates-cell",
                    )

        for update in filtered:
            uid = str(update.get("id") or "").strip()
            if not uid:
                continue

            title = str(update.get("title") or "Untitled Update")
            category = _normalize_update_category(update.get("category"))
            audience = _normalize_audience(update.get("audience") or update.get("visibility"))
            status = _normalize_update_status(update.get("status"), is_active=update.get("is_active"))
            is_pinned = bool(update.get("pinned") or update.get("is_pinned"))

            cols = st.columns(_UPD_COLS, gap="small", vertical_alignment="center")

            with cols[0]:
                st.checkbox(
                    "",
                    key=_update_select_key(uid),
                    label_visibility="collapsed",
                    on_change=_on_update_checkbox_change,
                    args=(uid, all_update_ids),
                )

            with cols[1]:
                st.markdown(_title_cell_html(title, is_pinned), unsafe_allow_html=True)

            with cols[2]:
                st.markdown(_category_pill_html(category), unsafe_allow_html=True)

            with cols[3]:
                st.markdown(
                    f'<div class="ips-updates-muted ips-updates-cell">{html.escape(audience)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[4]:
                st.markdown(_status_pill_html(status), unsafe_allow_html=True)

            with cols[5]:
                st.markdown(
                    f'<div class="ips-updates-cell">{html.escape(str(update.get("event_date_display") or "—"))}</div>',
                    unsafe_allow_html=True,
                )

            with cols[6]:
                st.markdown(
                    f'<div class="ips-updates-cell">{html.escape(str(update.get("created_by_display") or "—"))}</div>',
                    unsafe_allow_html=True,
                )

            with cols[7]:
                st.markdown(
                    f'<div class="ips-updates-muted ips-updates-cell">'
                    f"{html.escape(str(update.get('created_display') or '—'))}</div>",
                    unsafe_allow_html=True,
                )

        st.markdown("</div>", unsafe_allow_html=True)

    return all_update_ids


def render() -> None:
    from app.pages._core._access import begin_module
    if not begin_module("company_updates"):
        return

    inject_updates_module_css()
    st.markdown(
        '<span class="ips-updates-page ips-page-shell-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )

    lookup = _user_name_lookup()

    def _cu_new() -> None:
        if st.button("+ New Update", key="cu_new", type="primary", use_container_width=True):
            st.session_state["ips_cu_form"] = True

    render_page_brand_header(
        "Company Updates",
        "Share announcements, safety alerts, events, and company news.",
        actions=[_cu_new] if _can_manage_company_updates() else [],
    )

    if _can_manage_company_updates() and st.session_state.get("ips_cu_form"):
        with st.expander("New company update", expanded=True):
            st.text_input("Title", key="cu_new_title")
            nc1, nc2 = st.columns(2)
            with nc1:
                st.selectbox("Category", _CATEGORY_EDIT_OPTS, key="cu_new_cat")
                st.selectbox("Status", _STATUS_EDIT_OPTS, key="cu_new_status")
            with nc2:
                st.selectbox("Audience", _AUDIENCE_EDIT_OPTS, key="cu_new_audience")
                st.text_input("Event date", key="cu_new_event_date", placeholder="YYYY-MM-DD")
                st.selectbox("Priority", PRIORITY_EDIT_OPTS, key="cu_new_priority", index=2)
            st.text_area("Body / content", key="cu_new_body", height=100)
            st.text_area("Notes", key="cu_new_notes", height=60)
            st.checkbox("Pinned", key="cu_new_pinned")
            na1, na2 = st.columns(2)
            with na1:
                st.text_input("Attachment URL", key="cu_new_attachment_url", placeholder="https://…")
            with na2:
                st.text_input("Attachment label", key="cu_new_attachment_name", placeholder="File name")
            st.text_input("Banner caption (optional)", key="cu_new_banner_caption", placeholder="Short caption shown below the banner")
            st.file_uploader(
                "Upload banner image",
                type=list(BANNER_UPLOAD_TYPES),
                key="cu_new_banner_upload",
                help="JPG, PNG, or WEBP — max 5 MB.",
            )
            if st.button("Publish", key="cu_save_new", type="primary"):
                status = str(st.session_state.get("cu_new_status") or "Published")
                ui = {
                    "title": st.session_state.get("cu_new_title"),
                    "body": st.session_state.get("cu_new_body"),
                    "category": st.session_state.get("cu_new_cat"),
                    "pinned": st.session_state.get("cu_new_pinned"),
                    "status": status,
                    "audience": st.session_state.get("cu_new_audience"),
                    "event_date": st.session_state.get("cu_new_event_date"),
                    "notes": st.session_state.get("cu_new_notes"),
                    "priority": st.session_state.get("cu_new_priority"),
                    "attachment_url": st.session_state.get("cu_new_attachment_url"),
                    "attachment_file_name": st.session_state.get("cu_new_attachment_name"),
                    "banner_caption": st.session_state.get("cu_new_banner_caption"),
                    "is_active": _status_to_active(status),
                }
                ok, msg, saved = persist_company_update_record(ui)
                if not ok:
                    st.error(msg or "Could not publish update.")
                else:
                    saved_id = str(saved.get("id") or "")
                    uploaded = st.session_state.get("cu_new_banner_upload")
                    if uploaded is not None and saved_id and not is_demo_id(saved_id):
                        ok_banner, msg_banner = persist_company_update_banner(
                            saved_id,
                            uploaded,
                            caption=str(st.session_state.get("cu_new_banner_caption") or ""),
                        )
                        if not ok_banner:
                            st.warning(msg_banner or "Update published, but banner upload failed.")
                    if apply_persist_feedback(True, msg, clear_keys=("ips_cu_form",)):
                        st.rerun()

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
                _clear_update_selection(st.session_state.get(_ALL_UPDATE_IDS_KEY))
                st.session_state["cu_sort"] = "Newest First"
                st.rerun()
        with c3:
            st.selectbox(
                "Sort",
                _SORT_OPTS,
                key="cu_sort",
                label_visibility="collapsed",
            )

    layout_filter_bar(_filters)

    updates = load_company_updates(category="All Updates")
    all_rows = [_build_update_row(u, lookup) for u in updates]
    filter_options = build_filter_options(all_rows, _COLUMN_FILTER_SPECS)
    filtered = _filter_updates(
        all_rows,
        q=str(st.session_state.get("cu_search") or "").strip(),
        sort=str(st.session_state.get("cu_sort") or "Newest First"),
    )

    st.caption(f"{len(filtered)} update(s)")

    build_modal_cache(filtered, cache_key=_CACHE_KEY)
    _render_custom_updates_table(filtered, filter_options=filter_options)

    if st.session_state.get(SELECTED_UPDATE_KEY) and st.session_state.get(SHOW_UPDATE_MODAL_KEY):
        _show_update_detail_modal()
