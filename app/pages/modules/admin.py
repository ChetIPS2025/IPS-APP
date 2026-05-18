"""Admin / Settings — lookup tables and application settings (Phase 2D)."""

from __future__ import annotations

import streamlit as st

try:
    from app.components.headers import render_page_header
    from app.components.tabs import render_tabs
    from app.pages.modules._session import nav_slug
    from app.styles import inject_global_css
    from app.utils.constants import (
        ASSET_CATEGORIES,
        CERTIFICATION_TYPES,
        CREWS,
        CUSTOMERS,
        DEPARTMENTS,
        DOCUMENT_TYPES,
        ESTIMATE_STATUSES,
        INVENTORY_CATEGORIES,
        JOB_STATUSES,
        LOCATIONS,
        LOOKUP_TABLES,
        PERMISSION_GROUPS,
        ROLES,
        VENDORS,
    )
except ImportError:
    from components.headers import render_page_header  # type: ignore
    from components.tabs import render_tabs  # type: ignore
    from pages.modules._session import nav_slug  # type: ignore
    from styles import inject_global_css  # type: ignore
    from utils.constants import (  # type: ignore
        ASSET_CATEGORIES,
        CERTIFICATION_TYPES,
        CREWS,
        CUSTOMERS,
        DEPARTMENTS,
        DOCUMENT_TYPES,
        ESTIMATE_STATUSES,
        INVENTORY_CATEGORIES,
        JOB_STATUSES,
        LOCATIONS,
        LOOKUP_TABLES,
        PERMISSION_GROUPS,
        ROLES,
        VENDORS,
    )

_ADMIN_TAB = "ips_admin_main_tab"
_LOOKUP_TAB = "ips_admin_lookup_table"

_LOOKUP_SOURCES: dict[str, tuple[str, ...]] = {
    "Customers": CUSTOMERS,
    "Vendors": VENDORS,
    "Departments": DEPARTMENTS,
    "Locations": LOCATIONS,
    "Crews": CREWS,
    "Job Statuses": JOB_STATUSES,
    "Estimate Statuses": ESTIMATE_STATUSES,
    "Inventory Categories": INVENTORY_CATEGORIES,
    "Asset Categories": ASSET_CATEGORIES,
    "Certification Types": CERTIFICATION_TYPES,
    "Document Types": DOCUMENT_TYPES,
    "User Roles": ROLES,
    "Permission Groups": PERMISSION_GROUPS,
}


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
        st.session_state[key] = db_vals if db_vals else list(_LOOKUP_SOURCES.get(table_name, ()))
    return list(st.session_state[key])


def _render_lookup_editor() -> None:
    table = st.selectbox("Lookup table", LOOKUP_TABLES, key=_LOOKUP_TAB)
    items = _get_lookup_items(table)
    key = _lookup_session_key(table)

    ot = "d" + "iv"
    st.markdown(f'<{ot} class="ips-lookup-panel">', unsafe_allow_html=True)
    st.markdown(f"**{table}** — {len(items)} value(s)")
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
        st.success(f"{table} saved (demo — session only).")
    st.markdown(f"</{ot}>", unsafe_allow_html=True)


def _render_app_settings() -> None:
    st.markdown("**Application Settings**")
    c1, c2 = st.columns(2)
    with c1:
        st.selectbox("Default landing page", ["Dashboard", "Jobs", "Timekeeping"], key="set_landing")
        st.selectbox("Date format", ["MM/DD/YYYY", "DD/MM/YYYY", "ISO"], key="set_date_fmt")
    with c2:
        st.selectbox("Time zone", ["America/Chicago", "America/New_York", "UTC"], key="set_tz")
        st.toggle("Email notifications", value=True, key="set_email")
    st.selectbox("Theme", ["Light", "Dark (coming soon)"], key="set_theme", disabled=True)
    if st.button("Save settings", key="set_save", type="primary"):
        st.success("Settings saved (demo).")


def render() -> None:
    inject_global_css()
    slug = nav_slug()
    is_settings = slug == "settings"
    title = "Settings" if is_settings else "Admin"
    subtitle = (
        "Application preferences and notifications."
        if is_settings
        else "Manage lookup tables, roles, and system configuration."
    )
    render_page_header(title, subtitle)

    if is_settings:
        _render_app_settings()
        st.markdown("---")
        st.caption("Lookup tables are managed under **Admin**.")

    main_tab = render_tabs(
        ["Lookup Tables", "Application Settings"] if not is_settings else ["Application Settings", "Lookup Tables"],
        session_key=_ADMIN_TAB,
        default="Application Settings" if is_settings else "Lookup Tables",
    )

    if main_tab == "Lookup Tables":
        _render_lookup_editor()
    else:
        _render_app_settings()
