"""Company Updates module (Phase 2C)."""

from __future__ import annotations

import html
from datetime import datetime

import streamlit as st

try:
    from app.components.cards import render_metric_card
    from app.components.clickable_table import render_clickable_table
    from app.components.headers import render_page_header
    from app.components.record_modal import (
        build_modal_cache,
        clear_record_modal,
        detail_field_html,
        dialog_card_html,
        edit_mode_key,
        get_modal_record,
        is_edit_mode,
        open_record_modal,
        record_session_key,
        render_edit_form_header,
        render_modal_actions,
        render_modal_header,
        render_modal_meta_grid,
        render_modal_shell,
        render_missing_record,
        render_save_cancel_actions,
        set_view_mode,
        show_modal_if_pending,
    )
    from app.components.tabs import render_tabs
    from app.pages._core._data import (
        demo_update_metrics,
        load_company_updates,
        load_upcoming_events,
        lookup_options,
        persist_company_update,
    )
    from app.pages._core._crud import apply_persist_feedback, is_demo_id
    from app.pages._core._session import select_key
except ImportError:
    from components.cards import render_metric_card  # type: ignore
    from components.clickable_table import render_clickable_table  # type: ignore
    from components.headers import render_page_header  # type: ignore
    from components.record_modal import (  # type: ignore
        build_modal_cache,
        clear_record_modal,
        detail_field_html,
        dialog_card_html,
        edit_mode_key,
        get_modal_record,
        is_edit_mode,
        open_record_modal,
        record_session_key,
        render_edit_form_header,
        render_modal_actions,
        render_modal_header,
        render_modal_meta_grid,
        render_modal_shell,
        render_missing_record,
        render_save_cancel_actions,
        set_view_mode,
        show_modal_if_pending,
    )
    from components.tabs import render_tabs  # type: ignore
    from pages._core._data import (  # type: ignore
        demo_update_metrics,
        load_company_updates,
        load_upcoming_events,
        lookup_options,
        persist_company_update,
    )
    from pages._core._crud import apply_persist_feedback, is_demo_id  # type: ignore
    from pages._core._session import select_key  # type: ignore

_TAB_KEY = "ips_company_updates_cat"
_SORT_OPTS = ("Newest First", "Oldest First", "Title A–Z")
_SEL = select_key("company_updates")
_MODULE = "company_updates"
_TABLE_KEY = "company_updates_list"
_MODAL_KEY = "ips_cu_detail_modal_id"
_CACHE_KEY = "_ips_cu_modal_by_id"

_QUICK_LINKS = [
    ("📘", "Company Handbook"),
    ("🦺", "Safety Procedures"),
    ("👥", "HR Policies"),
    ("🎓", "Training Portal"),
]


def _sort_updates(rows: list[dict], sort: str) -> list[dict]:
    out = list(rows)
    if sort == "Oldest First":
        return sorted(out, key=lambda u: str(u.get("date") or ""))
    if sort == "Title A–Z":
        return sorted(out, key=lambda u: str(u.get("title") or "").lower())
    return sorted(out, key=lambda u: str(u.get("date") or ""), reverse=True)


def _event_date_block(iso: str) -> str:
    try:
        d = datetime.strptime(str(iso)[:10], "%Y-%m-%d")
        return f"{d.strftime('%b').upper()}<br>{d.day}"
    except ValueError:
        return "—"


def _clear_cu_modal() -> None:
    clear_record_modal(
        table_key=_TABLE_KEY,
        session_select_key=_SEL,
        modal_key=_MODAL_KEY,
        module=_MODULE,
    )


def _open_cu_modal(update_id: str, update: dict | None = None) -> None:
    open_record_modal(
        update_id,
        update,
        session_select_key=_SEL,
        modal_key=_MODAL_KEY,
        module=_MODULE,
        id_fields=("id",),
    )


def _seed_cu_edit_form(update: dict) -> None:
    rk = record_session_key(update, "id")
    st.session_state[f"cu_edit_title_{rk}"] = str(update.get("title") or "")
    st.session_state[f"cu_edit_body_{rk}"] = str(update.get("body") or "")
    st.session_state[f"cu_edit_cat_{rk}"] = str(update.get("category") or lookup_options("update_categories")[0])
    st.session_state[f"cu_edit_pinned_{rk}"] = bool(update.get("pinned"))


def _render_cu_view_tabs(update: dict) -> None:
    tab_message, tab_details = st.tabs(["Message", "Details"])
    with tab_message:
        body = str(update.get("body") or "").strip() or "No message body."
        body_html = (
            f'<p style="margin:0;font-size:0.875rem;color:#0f172a;line-height:1.5;white-space:pre-wrap;">'
            f"{html.escape(body)}"
            f"</p>"
        )
        st.markdown(dialog_card_html("Announcement", body_html), unsafe_allow_html=True)
    with tab_details:
        pinned = "Yes" if update.get("pinned") else "No"
        new_flag = "Yes" if update.get("is_new") else "No"
        details_html = (
            f'<div class="ips-detail-grid">'
            f"{detail_field_html('Category', update.get('category'))}"
            f"{detail_field_html('Date', update.get('date'))}"
            f"{detail_field_html('Pinned', pinned)}"
            f"{detail_field_html('Unread', new_flag)}"
            f"</div>"
        )
        st.markdown(dialog_card_html("Details", details_html), unsafe_allow_html=True)


def _render_cu_edit_form(update: dict) -> None:
    rk = record_session_key(update, "id")
    uid = str(update.get("id") or "")
    if f"cu_edit_title_{rk}" not in st.session_state:
        _seed_cu_edit_form(update)

    render_edit_form_header("Edit Update")
    st.text_input("Title", key=f"cu_edit_title_{rk}")
    st.text_area("Message", key=f"cu_edit_body_{rk}", height=120)
    st.selectbox("Category", lookup_options("update_categories"), key=f"cu_edit_cat_{rk}")
    st.checkbox("Pin to top", key=f"cu_edit_pinned_{rk}")

    cancelled, saved = render_save_cancel_actions(
        module=_MODULE,
        record_key=rk,
        cancel_key=f"cu_edit_cancel_{rk}",
        save_key=f"cu_edit_save_{rk}",
    )
    if cancelled:
        st.rerun()
    if saved:
        ui = {
            "title": st.session_state.get(f"cu_edit_title_{rk}"),
            "body": st.session_state.get(f"cu_edit_body_{rk}"),
            "category": st.session_state.get(f"cu_edit_cat_{rk}"),
            "pinned": st.session_state.get(f"cu_edit_pinned_{rk}"),
        }
        row_id = None if is_demo_id(uid) else uid
        ok, msg = persist_company_update(ui, row_id=row_id)
        if ok:
            set_view_mode(_MODULE, rk)
            st.success(msg or "Update saved.")
            st.rerun()
        else:
            st.error(msg or "Could not save update.")


def render_cu_detail_dialog(update: dict) -> None:
    rk = record_session_key(update, "id")
    st.session_state.setdefault(edit_mode_key(_MODULE, rk), False)
    edit_mode = is_edit_mode(_MODULE, rk)

    render_modal_shell()
    render_modal_header(
        title=str(update.get("title") or "Update"),
        subtitle=str(update.get("category") or ""),
    )
    render_modal_actions(
        module=_MODULE,
        record_key=rk,
        record=update,
        on_close=_clear_cu_modal,
        key_prefix=f"cu_modal_{rk}",
    )
    render_modal_meta_grid(
        [
            ("Date", update.get("date")),
            ("Category", update.get("category")),
            ("Pinned", "Yes" if update.get("pinned") else "No"),
            ("Status", "New" if update.get("is_new") else "Read"),
        ]
    )

    if edit_mode:
        _render_cu_edit_form(update)
    else:
        _render_cu_view_tabs(update)


@st.dialog("Company Update", width="large", on_dismiss=_clear_cu_modal)
def _show_cu_detail_modal() -> None:
    update = get_modal_record(
        cache_key=_CACHE_KEY,
        modal_key=_MODAL_KEY,
        session_select_key=_SEL,
    )
    if not update:
        render_missing_record(_clear_cu_modal, close_key="cu_modal_missing_close")
        return
    render_cu_detail_dialog(update)


def _cu_display_cell(field: str, row: dict) -> str:
    if field == "pinned":
        return "Pinned" if row.get("pinned") else "—"
    if field == "is_new":
        return "New" if row.get("is_new") else "—"
    val = row.get(field)
    return str(val).strip() if val is not None and str(val).strip() else "—"


def render() -> None:
    try:
        from app.pages._core._access import begin_module
    except ImportError:
        from pages._core._access import begin_module  # type: ignore
    if not begin_module("company_updates"):
        return
    metrics = demo_update_metrics()

    hdr_l, hdr_r = st.columns([3, 1])
    with hdr_l:
        render_page_header(
            "Company Updates",
            "Stay informed with the latest company news, announcements, and important updates.",
        )
    with hdr_r:
        if st.button("+ New Update", key="cu_new", type="primary", use_container_width=True):
            st.session_state["ips_cu_form"] = True

    if st.session_state.get("ips_cu_form"):
        with st.expander("New company update", expanded=True):
            st.text_input("Title", key="cu_new_title")
            st.text_area("Message", key="cu_new_body", height=100)
            st.selectbox("Category", lookup_options("update_categories"), key="cu_new_cat")
            st.checkbox("Pin to top", key="cu_new_pinned")
            if st.button("Publish", key="cu_save_new", type="primary"):
                ok, msg = persist_company_update(
                    {
                        "title": st.session_state.get("cu_new_title"),
                        "body": st.session_state.get("cu_new_body"),
                        "category": st.session_state.get("cu_new_cat"),
                        "pinned": st.session_state.get("cu_new_pinned"),
                    }
                )
                if apply_persist_feedback(ok, msg, clear_keys=("ips_cu_form",)):
                    st.rerun()

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        render_metric_card("Unread Updates", str(metrics.get("unread", 0)), delta="View all")
    with m2:
        render_metric_card("Pinned Updates", str(metrics.get("pinned", 0)), delta="View all")
    with m3:
        render_metric_card("Upcoming Events", str(metrics.get("events", 0)), delta="View calendar")
    with m4:
        render_metric_card("All Updates", str(metrics.get("all", 0)), delta="View all")

    main, side = st.columns([2.1, 1])

    with main:
        cats = ["All Updates", *lookup_options("update_categories")]
        cat = render_tabs(cats, session_key=_TAB_KEY, default="All Updates")
        ctrl_l, ctrl_r = st.columns([1, 1.2])
        with ctrl_l:
            sort = st.selectbox("Sort by", _SORT_OPTS, key="cu_sort", label_visibility="collapsed")
        with ctrl_r:
            st.text_input("Search updates", placeholder="Search updates…", key="cu_search", label_visibility="collapsed")

        updates = load_company_updates(category=cat)
        q = str(st.session_state.get("cu_search") or "").strip().lower()
        if q:
            updates = [
                u
                for u in updates
                if q in str(u.get("title", "")).lower() or q in str(u.get("body", "")).lower()
            ]
        updates = _sort_updates(updates, sort)

        display_updates = updates[:50]
        build_modal_cache(display_updates, cache_key=_CACHE_KEY)
        render_clickable_table(
            display_updates,
            [
                ("title", "TITLE"),
                ("category", "CATEGORY"),
                ("date", "DATE"),
                ("pinned", "PINNED"),
                ("is_new", "STATUS"),
            ],
            _TABLE_KEY,
            row_id_key="id",
            session_select_key=_SEL,
            format_cell=_cu_display_cell,
            click_caption=f"Showing {len(display_updates)} update(s) · Click a row to open details.",
            on_row_selected=_open_cu_modal,
        )
        show_modal_if_pending(_MODAL_KEY, _show_cu_detail_modal)

        st.caption(f"Showing 1 to {min(len(display_updates), 50)} of {metrics.get('all', len(updates))} updates")

    with side:
        st.markdown("**Upcoming Events**")
        events = load_upcoming_events()
        ot = "d" + "iv"
        for ev in events:
            st.markdown(
                f'<{ot} class="ips-event-block">'
                f'<{ot} class="ips-event-date">{_event_date_block(str(ev.get("date") or ""))}</{ot}>'
                f"<{ot}><strong>{html.escape(str(ev.get('title') or ''))}</strong><br>"
                f"{html.escape(str(ev.get('time') or ''))} · {html.escape(str(ev.get('location') or ''))}</{ot}>"
                f"</{ot}>",
                unsafe_allow_html=True,
            )

        st.markdown("---")
        st.markdown("**Quick Links**")
        for icon, label in _QUICK_LINKS:
            st.markdown(
                f'<p class="ips-quick-link"><span>{icon} {html.escape(label)}</span><span>›</span></p>',
                unsafe_allow_html=True,
            )

        st.markdown("---")
        st.markdown("**Recent Updates**")
        recent = _sort_updates(load_company_updates(), "Newest First")[:4]
        for u in recent:
            st.caption(f"• {u.get('title')} — {u.get('date')}")
