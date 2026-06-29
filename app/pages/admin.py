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
_ENTRIES_SUFFIX = "_entries"
_SOURCE_SUFFIX = "_source"


def _lookup_session_key(table_name: str) -> str:
    return f"ips_lookup_{table_name.lower().replace(' ', '_')}"


def _lookup_entries_key(table_name: str) -> str:
    return f"{_lookup_session_key(table_name)}{_ENTRIES_SUFFIX}"


def _lookup_source_key(table_name: str) -> str:
    return f"{_lookup_session_key(table_name)}{_SOURCE_SUFFIX}"


def _load_lookup_entries_from_service(table_name: str) -> tuple[list[dict], str]:
    try:
        from app.services.lookup_service import load_lookup_entries_for_label
    except ImportError:
        from services.lookup_service import load_lookup_entries_for_label  # type: ignore
    try:
        return load_lookup_entries_for_label(table_name)
    except Exception:
        try:
            from app.services.lookup_service import (
                constants_fallback_for_label,
                supabase_is_configured,
            )
        except ImportError:
            from services.lookup_service import (  # type: ignore
                constants_fallback_for_label,
                supabase_is_configured,
            )
        if not supabase_is_configured():
            vals = constants_fallback_for_label(table_name)
            return [{"id": f"local-{i}", "value": v, "from_db": False} for i, v in enumerate(vals)], "constants"
        return [], "empty"


def _get_lookup_entries(table_name: str) -> list[dict]:
    key = _lookup_entries_key(table_name)
    if key not in st.session_state:
        entries, source = _load_lookup_entries_from_service(table_name)
        st.session_state[key] = list(entries)
        st.session_state[_lookup_source_key(table_name)] = source
    return list(st.session_state[key])


def _lookup_source_label(table_name: str) -> str:
    source = str(st.session_state.get(_lookup_source_key(table_name)) or "unknown")
    if source == "database":
        return "Loaded from Supabase"
    if source == "constants":
        return "Using app constants — save to create DB records"
    if source == "empty":
        return "No Supabase values — seed from defaults or add manually"
    return "No values configured"


def _get_lookup_items(table_name: str) -> list[str]:
    return [str(e.get("value") or "") for e in _get_lookup_entries(table_name)]


def _set_lookup_entries(table_name: str, entries: list[dict]) -> None:
    st.session_state[_lookup_entries_key(table_name)] = list(entries)


def _clear_lookup_session(table_name: str) -> None:
    base = _lookup_session_key(table_name)
    for suffix in ("", _ENTRIES_SUFFIX, _SOURCE_SUFFIX):
        st.session_state.pop(f"{base}{suffix}", None)
    st.session_state.pop(f"{base}_new", None)


def _lookup_rows(table_name: str, entries: list[dict]) -> list[dict]:
    return [
        {"id": str(ent.get("id") or i), "value": str(ent.get("value") or ""), "table": table_name}
        for i, ent in enumerate(entries)
    ]


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
    row_id = str(row.get("id") or "")
    rk = record_session_key(row, "id")
    edit_key = f"lookup_edit_val_{rk}"

    render_edit_form_header("Edit Lookup Value")
    st.text_input("Value", key=edit_key, value=str(row.get("value") or ""))

    btn_remove, btn_spacer, btn_save = st.columns([1, 3, 1], gap="small")
    removed = False
    with btn_remove:
        if st.button("Remove", key=f"lookup_edit_remove_{rk}"):
            entries = _get_lookup_entries(table_name)
            _set_lookup_entries(
                table_name,
                [e for e in entries if str(e.get("id") or "") != row_id],
            )
            removed = True
    with btn_save:
        saved = st.button("Save Changes", key=f"lookup_edit_save_{rk}", type="primary")

    if removed:
        _clear_lookup_modal()
        st.rerun()
    if saved:
        new_val = str(st.session_state.get(edit_key) or "").strip()
        entries = _get_lookup_entries(table_name)
        updated: list[dict] = []
        for ent in entries:
            if str(ent.get("id") or "") == row_id:
                if new_val:
                    updated.append({**ent, "value": new_val})
            else:
                updated.append(ent)
        _set_lookup_entries(table_name, updated)
        set_view_mode(_MODULE, rk)
        st.success("Updated — click **Save lookup table** to persist to Supabase.")
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
    entries = _get_lookup_entries(table)
    key = _lookup_session_key(table)
    st.session_state[_LOOKUP_TABLE_CTX] = table

    ot = "d" + "iv"
    st.markdown(f'<{ot} class="ips-lookup-panel">', unsafe_allow_html=True)
    st.markdown(f"**{table}** — {len(entries)} value(s)")
    st.caption(_lookup_source_label(table))
    st.caption("Click a row to view or edit. Changes persist after **Save lookup table**.")

    source = str(st.session_state.get(_lookup_source_key(table)) or "unknown")
    if source == "empty":
        if st.button("Seed from app defaults", key=f"{key}_seed"):
            try:
                from app.services.lookup_service import seed_lookup_from_constants
            except ImportError:
                from services.lookup_service import seed_lookup_from_constants  # type: ignore
            ok, msg = seed_lookup_from_constants(table)
            if apply_persist_feedback(ok, msg):
                _clear_lookup_session(table)
                st.rerun()

    rows = _lookup_rows(table, entries)
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
            entries = _get_lookup_entries(table)
            try:
                from app.services.lookup_service import _new_local_id
            except ImportError:
                from services.lookup_service import _new_local_id  # type: ignore
            entries.append({"id": _new_local_id(), "value": new_val.strip(), "from_db": False})
            _set_lookup_entries(table, entries)
            st.session_state[f"{key}_new"] = ""
            st.rerun()

    if st.button("Save lookup table", key=f"{key}_save", type="primary"):
        try:
            from app.services.lookup_service import sync_lookup_for_label
        except ImportError:
            from services.lookup_service import sync_lookup_for_label  # type: ignore
        ok, msg = sync_lookup_for_label(table, _get_lookup_entries(table))
        if apply_persist_feedback(ok, msg):
            _clear_lookup_session(table)
            st.rerun()
    st.markdown(f"</{ot}>", unsafe_allow_html=True)


def _hydrate_app_settings_widgets(key_prefix: str) -> None:
    flag = f"{key_prefix}_hydrated"
    if st.session_state.get(flag):
        return
    try:
        from app.services.company_settings_service import load_app_settings
    except ImportError:
        from services.company_settings_service import load_app_settings  # type: ignore
    row = load_app_settings()
    st.session_state[f"{key_prefix}_landing"] = str(row.get("default_landing_page") or "Dashboard")
    st.session_state[f"{key_prefix}_date_fmt"] = str(row.get("date_format") or "MM/DD/YYYY")
    st.session_state[f"{key_prefix}_tz"] = str(row.get("timezone") or "America/Chicago")
    st.session_state[f"{key_prefix}_email"] = bool(row.get("email_notifications_enabled", True))
    st.session_state[flag] = True


def _render_app_settings(*, key_prefix: str) -> None:
    _hydrate_app_settings_widgets(key_prefix)
    st.markdown("**Application Settings**")
    if not st.session_state.get(f"{key_prefix}_from_db_notified"):
        try:
            from app.services.company_settings_service import load_app_settings
        except ImportError:
            from services.company_settings_service import load_app_settings  # type: ignore
        if load_app_settings().get("from_db"):
            st.caption("Loaded from **company_settings** in Supabase.")
        else:
            st.caption("Using defaults — save to persist to **company_settings**.")
        st.session_state[f"{key_prefix}_from_db_notified"] = True
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
        try:
            from app.services.company_settings_service import save_app_settings
        except ImportError:
            from services.company_settings_service import save_app_settings  # type: ignore
        ok, msg = save_app_settings(
            default_landing_page=str(st.session_state.get(f"{key_prefix}_landing") or "Dashboard"),
            date_format=str(st.session_state.get(f"{key_prefix}_date_fmt") or "MM/DD/YYYY"),
            timezone_name=str(st.session_state.get(f"{key_prefix}_tz") or "America/Chicago"),
            email_notifications_enabled=bool(st.session_state.get(f"{key_prefix}_email", True)),
        )
        apply_persist_feedback(ok, msg)
    st.markdown("---")
    try:
        from app.components.install_share import render_install_share_settings
    except ImportError:
        from components.install_share import render_install_share_settings  # type: ignore
    render_install_share_settings()


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
