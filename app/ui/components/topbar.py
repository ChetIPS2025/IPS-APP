"""Slim top navigation bar."""

from __future__ import annotations

import html

import streamlit as st

try:
    from app.auth import current_profile, current_role
    from app.ui import IPS_NAV_PENDING_KEY, role_can_open_page
    from app.ui.theme import DENSITY_CHOICES, get_density, set_density
except ImportError:
    from auth import current_profile, current_role  # type: ignore
    from ui import IPS_NAV_PENDING_KEY, role_can_open_page  # type: ignore
    from ui.theme import DENSITY_CHOICES, get_density, set_density  # type: ignore


def _unread_updates_count() -> int:
    """Unread company updates for current user; never raises."""
    try:
        if not role_can_open_page(current_role(), "Company Updates"):
            return 0
        try:
            from app.data_cache import fetch_table_for_session
        except ImportError:
            from data_cache import fetch_table_for_session  # type: ignore

        sk = str(current_profile().get("id") or "anonymous")
        use_admin = current_role() in {"admin", "manager"}
        cu_rows = fetch_table_for_session(
            "company_updates",
            session_key=sk,
            limit=300,
            order_by="created_at",
            use_admin=use_admin,
        )
        read_rows = fetch_table_for_session(
            "company_update_reads",
            session_key=sk,
            limit=5000,
            order_by=None,
            use_admin=use_admin,
        )
        uid = str(current_profile().get("id") or "")
        read_uids = {
            str(r.get("update_id") or "")
            for r in (read_rows or [])
            if str(r.get("user_id") or "") == uid
        }
        return sum(
            1
            for u in cu_rows or []
            if str((u or {}).get("id") or "").strip()
            and str((u or {}).get("id") or "") not in read_uids
            and bool((u or {}).get("is_active", True))
        )
    except Exception:
        return 0


def render_top_bar(*, page_label: str | None = None) -> None:
    """Compact top bar: breadcrumb, search, notifications, quick add, density, user."""
    page_name = str(page_label or st.session_state.get("ips_nav_page") or "Dashboard")
    if page_name == "Dashboard":
        return

    prof = current_profile()
    display_name = str(prof.get("full_name") or prof.get("email") or "User").strip()
    role = str(current_role() or "").strip()
    unread = _unread_updates_count()
    page = html.escape(str(page_label or st.session_state.get("ips_nav_page") or "Dashboard"))

    st.markdown(
        f'<p class="ips-topbar-crumb">IPS / <strong>{page}</strong></p>',
        unsafe_allow_html=True,
    )

    c_search, c_notif, c_add, c_den, c_user = st.columns([2.4, 0.65, 0.65, 0.75, 1.2], gap="small")

    with c_search:
        q = st.text_input(
            "Global search",
            key="ips_global_search_q",
            placeholder="Search jobs, inventory…",
            label_visibility="collapsed",
        )
    with c_notif:
        pill_cls = "ips-topbar-pill ips-has-alert" if unread else "ips-topbar-pill"
        st.markdown(
            f'<span class="{pill_cls}"><span class="ips-dot"></span> {unread}</span>',
            unsafe_allow_html=True,
        )
        if st.button("Updates", key="ips_topbar_updates", use_container_width=True):
            st.session_state[IPS_NAV_PENDING_KEY] = "Company Updates"
            st.rerun()
    with c_add:
        if st.button("+ Add", key="ips_topbar_quick_add", use_container_width=True):
            st.session_state["ips_quick_add_open"] = True
    with c_den:
        idx = DENSITY_CHOICES.index(get_density()) if get_density() in DENSITY_CHOICES else 0
        picked = st.selectbox(
            "Density",
            DENSITY_CHOICES,
            index=idx,
            key="ips_topbar_density",
            label_visibility="collapsed",
        )
        if picked != get_density():
            set_density(picked)
            st.rerun()
    with c_user:
        st.caption(f"{display_name[:20]} · {role}")

    qs = str(q or "").strip()
    if qs and st.button("Search", key="ips_global_search_btn", type="primary"):
        st.session_state["job_filt_search"] = qs
        st.session_state[IPS_NAV_PENDING_KEY] = "Job Database"
        st.rerun()

    if st.session_state.pop("ips_quick_add_open", False):
        with st.popover("Quick add", use_container_width=True):
            if st.button("New job", key="ips_qa_job", use_container_width=True):
                st.session_state[IPS_NAV_PENDING_KEY] = "Job Database"
                st.session_state["job_view_mode"] = "create"
                st.rerun()
            if st.button("New estimate", key="ips_qa_est", use_container_width=True):
                st.session_state[IPS_NAV_PENDING_KEY] = "Estimates"
                st.rerun()
            if role_can_open_page(current_role(), "Inventory") and st.button(
                "Add inventory", key="ips_qa_inv", use_container_width=True
            ):
                st.session_state[IPS_NAV_PENDING_KEY] = "Inventory"
                st.session_state["inventory_panel_mode"] = "add"
                st.rerun()
            if role_can_open_page(current_role(), "Company Updates") and st.button(
                "Post update", key="ips_qa_cu", use_container_width=True
            ):
                st.session_state[IPS_NAV_PENDING_KEY] = "Company Updates"
                st.session_state["cu_open_post"] = True
                st.rerun()
