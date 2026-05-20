"""Admin / Settings — lookup tables and application settings (Phase 2D)."""

from __future__ import annotations

import streamlit as st

try:
    from app.components.headers import render_page_header
    from app.components.tabs import render_tabs
    from app.pages.modules._data import persist_lookup_table
    from app.pages.modules._crud import apply_persist_feedback
    from app.pages.modules._session import nav_slug
    from app.utils.constants import LOOKUP_TABLES
except ImportError:
    from components.headers import render_page_header  # type: ignore
    from components.tabs import render_tabs  # type: ignore
    from pages.modules._data import persist_lookup_table  # type: ignore
    from pages.modules._crud import apply_persist_feedback  # type: ignore
    from pages.modules._session import nav_slug  # type: ignore
    from utils.constants import LOOKUP_TABLES  # type: ignore

_ADMIN_TAB = "ips_admin_main_tab"
_LOOKUP_TAB = "ips_admin_lookup_table"


def _lookup_session_key(table_name: str) -> str:
    return f"ips_lookup_{table_name.lower().replace(' ', '_')}"


def _get_lookup_items(table_name: str) -> list[str]:
    key = _lookup_session_key(table_name)
    if key not in st.session_state:
        try:
            from app.services.lookup_service import load_lookup_for_label
        except ImportError:
            from services.lookup_service import load_lookup_for_label  # type: ignore
        db_vals = load_lookup_for_label(table_name)
        st.session_state[key] = list(db_vals) if db_vals else []
    return list(st.session_state[key])


def _render_lookup_editor() -> None:
    table = st.selectbox("Lookup table", LOOKUP_TABLES, key=_LOOKUP_TAB)
    items = _get_lookup_items(table)
    key = _lookup_session_key(table)

    ot = "d" + "iv"
    st.markdown(f'<{ot} class="ips-lookup-panel">', unsafe_allow_html=True)
    st.markdown(f"**{table}** — {len(items)} value(s)")
    st.caption("Values load from Supabase `ips_lookup_*` when available; otherwise from app constants.")

    for i, val in enumerate(items):
        c1, c2 = st.columns([4, 1])
        with c1:
            st.text_input(f"item_{i}", value=val, key=f"{key}_row_{i}", label_visibility="collapsed")
        with c2:
            if st.button("Remove", key=f"{key}_rm_{i}", use_container_width=True):
                items.pop(i)
                st.session_state[key] = items
                st.rerun()

    for i, val in enumerate(items):
        items[i] = str(st.session_state.get(f"{key}_row_{i}") or val).strip()
    st.session_state[key] = [v for v in items if v]

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
        from app.pages.modules._access import begin_module
    except ImportError:
        from pages.modules._access import begin_module  # type: ignore
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
