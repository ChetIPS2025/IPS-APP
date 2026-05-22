"""Admin / Settings — lookup tables and application settings (Phase 2D)."""

from __future__ import annotations

import streamlit as st

try:
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
        render_modal_edit_button,
        render_modal_header,
        render_modal_shell,
        render_missing_record,
        set_view_mode,
        show_modal_if_pending,
    )
    from app.components.tabs import render_tabs
    from app.pages._core._data import persist_lookup_table
    from app.pages._core._crud import apply_persist_feedback
    from app.pages._core._session import nav_slug, select_key
    from app.utils.constants import LOOKUP_TABLES
except ImportError:
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
        render_modal_edit_button,
        render_modal_header,
        render_modal_shell,
        render_missing_record,
        set_view_mode,
        show_modal_if_pending,
    )
    from components.tabs import render_tabs  # type: ignore
    from pages._core._data import persist_lookup_table  # type: ignore
    from pages._core._crud import apply_persist_feedback  # type: ignore
    from pages._core._session import nav_slug, select_key  # type: ignore
    from utils.constants import LOOKUP_TABLES  # type: ignore

_ADMIN_TAB = "ips_admin_main_tab"
_LOOKUP_TAB = "ips_admin_lookup_table"
_SEL = select_key("admin_lookup")
_MODULE = "admin_lookup"
_TABLE_KEY = "admin_lookup_list"
_MODAL_KEY = "ips_admin_lookup_modal_id"
_CACHE_KEY = "_ips_admin_lookup_modal_by_id"
_LOOKUP_TABLE_CTX = "ips_admin_lookup_table_ctx"


def _lookup_session_key(table_name: str) -> str:
    return f"ips_lookup_{table_name.lower().replace(' ', '_')}"


def _get_lookup_items(table_name: str) -> list[str]:
    key = _lookup_session_key(table_name)
    if key not in st.session_state:
        try:
            from app.services.lookup_service import (
                constants_fallback_for_label,
                load_lookup_for_label,
            )
        except ImportError:
            from services.lookup_service import (  # type: ignore
                constants_fallback_for_label,
                load_lookup_for_label,
            )
        try:
            db_vals = load_lookup_for_label(table_name)
        except Exception:
            db_vals = []
        if not db_vals:
            db_vals = constants_fallback_for_label(table_name)
        st.session_state[key] = list(db_vals)
    return list(st.session_state[key])


def _lookup_rows(table_name: str, items: list[str]) -> list[dict]:
    return [{"id": str(i), "value": val, "table": table_name} for i, val in enumerate(items)]


def _clear_lookup_modal() -> None:
    clear_record_modal(
        table_key=_TABLE_KEY,
        session_select_key=_SEL,
        modal_key=_MODAL_KEY,
        module=_MODULE,
    )


def _open_lookup_modal(row_id: str, row: dict | None = None) -> None:
    open_record_modal(
        row_id,
        row,
        session_select_key=_SEL,
        modal_key=_MODAL_KEY,
        module=_MODULE,
        id_fields=("id",),
    )


def _render_lookup_view(row: dict) -> None:
    tab_overview = st.tabs(["Overview"])[0]
    with tab_overview:
        overview_html = (
            f'<div class="ips-detail-grid">'
            f"{detail_field_html('Lookup Table', row.get('table'))}"
            f"{detail_field_html('Value', row.get('value'))}"
            f"</div>"
        )
        st.markdown(dialog_card_html("Lookup Value", overview_html), unsafe_allow_html=True)


def _render_lookup_edit(row: dict) -> None:
    table_name = str(row.get("table") or "")
    idx = int(str(row.get("id") or "0"))
    rk = record_session_key(row, "id")
    items_key = _lookup_session_key(table_name)
    edit_key = f"lookup_edit_val_{rk}"

    render_edit_form_header("Edit Lookup Value")
    st.text_input("Value", key=edit_key, value=str(row.get("value") or ""))

    btn_remove, btn_spacer, btn_save = st.columns([1, 3, 1], gap="small")
    removed = False
    with btn_remove:
        if st.button("Remove", key=f"lookup_edit_remove_{rk}"):
            items = _get_lookup_items(table_name)
            if 0 <= idx < len(items):
                items.pop(idx)
                st.session_state[items_key] = items
            removed = True
    with btn_save:
        saved = st.button("Save Changes", key=f"lookup_edit_save_{rk}", type="primary")

    if removed:
        _clear_lookup_modal()
        st.rerun()
    if saved:
        new_val = str(st.session_state.get(edit_key) or "").strip()
        items = _get_lookup_items(table_name)
        if new_val and 0 <= idx < len(items):
            items[idx] = new_val
            st.session_state[items_key] = items
        set_view_mode(_MODULE, rk)
        st.success("Lookup value updated (session).")
        st.rerun()


def render_lookup_detail_dialog(row: dict) -> None:
    rk = record_session_key(row, "id")
    st.session_state.setdefault(edit_mode_key(_MODULE, rk), False)
    edit_mode = is_edit_mode(_MODULE, rk)

    render_modal_shell(wide=False)
    render_modal_header(
        title=str(row.get("value") or "Lookup Value"),
        subtitle=str(row.get("table") or ""),
    )
    render_modal_edit_button(
        module=_MODULE,
        record_key=rk,
        key_prefix=f"lookup_modal_{rk}",
    )

    if edit_mode:
        _render_lookup_edit(row)
    else:
        _render_lookup_view(row)


@st.dialog("Lookup Value", width="small", on_dismiss=_clear_lookup_modal)
def _show_lookup_detail_modal() -> None:
    row = get_modal_record(
        cache_key=_CACHE_KEY,
        modal_key=_MODAL_KEY,
        session_select_key=_SEL,
    )
    if not row:
        render_missing_record(_clear_lookup_modal, close_key="lookup_modal_missing_close")
        return
    render_lookup_detail_dialog(row)


def _render_lookup_editor() -> None:
    table = st.selectbox("Lookup table", LOOKUP_TABLES, key=_LOOKUP_TAB)
    items = _get_lookup_items(table)
    key = _lookup_session_key(table)
    st.session_state[_LOOKUP_TABLE_CTX] = table

    ot = "d" + "iv"
    st.markdown(f'<{ot} class="ips-lookup-panel">', unsafe_allow_html=True)
    st.markdown(f"**{table}** — {len(items)} value(s)")
    st.caption("Values load from Supabase `ips_lookup_*` when available; otherwise from app constants.")
    st.caption("Click a row to view or edit a lookup value.")

    rows = _lookup_rows(table, items)
    build_modal_cache(rows, cache_key=_CACHE_KEY)
    render_clickable_table(
        rows,
        [("value", "VALUE")],
        _TABLE_KEY,
        row_id_key="id",
        session_select_key=_SEL,
        click_caption="Click a row to open the lookup value editor.",
        on_row_selected=_open_lookup_modal,
    )
    show_modal_if_pending(_MODAL_KEY, _show_lookup_detail_modal)

    nc1, nc2 = st.columns([3, 1])
    with nc1:
        new_val = st.text_input("Add value", key=f"{key}_new", placeholder="New entry…", label_visibility="collapsed")
    with nc2:
        if st.button("Add", key=f"{key}_add", use_container_width=True) and new_val.strip():
            st.session_state[key] = _get_lookup_items(table) + [new_val.strip()]
            st.session_state[f"{key}_new"] = ""
            st.rerun()

    if st.button("Save lookup table", key=f"{key}_save", type="primary"):
        ok, msg = persist_lookup_table(table, st.session_state[key])
        apply_persist_feedback(ok, msg)
    st.markdown(f"</{ot}>", unsafe_allow_html=True)


def _render_app_settings(*, key_prefix: str) -> None:
    st.markdown("**Application Settings**")
    c1, c2 = st.columns(2)
    with c1:
        st.selectbox(
            "Default landing page",
            ["Dashboard", "Jobs", "Timekeeping"],
            key=f"{key_prefix}_landing",
        )
        st.selectbox(
            "Date format",
            ["MM/DD/YYYY", "DD/MM/YYYY", "ISO"],
            key=f"{key_prefix}_date_fmt",
        )
    with c2:
        st.selectbox(
            "Time zone",
            ["America/Chicago", "America/New_York", "UTC"],
            key=f"{key_prefix}_tz",
        )
        st.toggle("Email notifications", value=True, key=f"{key_prefix}_email")
    st.selectbox(
        "Theme",
        ["Light", "Dark (coming soon)"],
        key=f"{key_prefix}_theme",
        disabled=True,
    )
    if st.button("Save settings", key=f"{key_prefix}_save", type="primary"):
        st.success("Settings saved (session preferences — company_settings table in a later phase).")


def render() -> None:
    slug = nav_slug()
    try:
        from app.pages._core._access import begin_module
    except ImportError:
        from pages._core._access import begin_module  # type: ignore
    if not begin_module(slug):
        return
    is_settings = slug == "settings"
    title = "Settings" if is_settings else "Admin"
    subtitle = (
        "Application preferences and notifications."
        if is_settings
        else "Manage lookup tables, roles, and system configuration."
    )
    render_page_header(title, subtitle)

    if is_settings:
        st.caption("Lookup tables are managed under **Admin**.")

    main_tab = render_tabs(
        ["Lookup Tables", "Application Settings"] if not is_settings else ["Application Settings", "Lookup Tables"],
        session_key=_ADMIN_TAB,
        default="Application Settings" if is_settings else "Lookup Tables",
    )

    settings_key = f"ips_app_settings_{slug or 'admin'}"
    if main_tab == "Lookup Tables":
        _render_lookup_editor()
    else:
        _render_app_settings(key_prefix=settings_key)
