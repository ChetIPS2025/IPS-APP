"""Page header components."""

from __future__ import annotations

import html
from collections.abc import Callable

import streamlit as st

try:
    from app.branding import wording_logo_html
    from app.components.sidebar_shell import inject_sidebar_menu_wire
except ImportError:
    from branding import wording_logo_html  # type: ignore
    from components.sidebar_shell import inject_sidebar_menu_wire  # type: ignore

_ActionFn = Callable[[], None]


def render_main_brand_bar(*, brand_actions: list[_ActionFn] | None = None, show_menu: bool = True) -> None:
    """Light-gray IPS wording logo bar — call once per page (via phase2 shell)."""
    ot, ct = "d" + "iv", "/" + "d" + "iv"
    logo = wording_logo_html(height=40)
    menu_html = (
        '<button type="button" class="ips-header-menu-btn" aria-label="Open navigation menu">'
        '<span class="ips-header-menu-icon" aria-hidden="true">'
        '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" '
        'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">'
        '<line x1="4" y1="7" x2="20" y2="7"/>'
        '<line x1="4" y1="12" x2="20" y2="12"/>'
        '<line x1="4" y1="17" x2="20" y2="17"/>'
        "</svg></span></button>"
        if show_menu
        else ""
    )
    st.markdown(
        f'<{ot} class="ips-main-header">'
        f'<{ot} class="ips-main-header-menu">{menu_html}</{ct}>'
        f'<{ot} class="ips-main-header-brand">{logo}</{ct}>'
        f'<{ot} class="ips-main-header-actions-slot"></{ct}>'
        f"</{ct}>",
        unsafe_allow_html=True,
    )
    if show_menu:
        inject_sidebar_menu_wire()
    if brand_actions:
        ba_cols = st.columns([5, 1], gap="small")
        with ba_cols[1]:
            st.markdown(
                f'<span class="ips-main-header-actions-marker" aria-hidden="true"></span>',
                unsafe_allow_html=True,
            )
            for fn in brand_actions:
                fn()


def render_page_brand_header(
    title: str,
    subtitle: str | None = None,
    *,
    actions: list[_ActionFn] | None = None,
    actions_column_ratio: tuple[float, float] | None = None,
    brand_actions: list[_ActionFn] | None = None,
    include_brand_bar: bool = False,
) -> None:
    """
    Compact page title row below the global brand bar.

    Set ``include_brand_bar=True`` only for standalone pages outside ``render_module``.
    """
    ot, ct = "d" + "iv", "/" + "d" + "iv"
    st.markdown(f'<{ot} class="ips-page-shell-marker"></{ct}>', unsafe_allow_html=True)

    if include_brand_bar:
        render_main_brand_bar(brand_actions=brand_actions)

    sub_html = (
        f'<p class="ips-page-subtitle">{html.escape(subtitle)}</p>'
        if subtitle
        else ""
    )
    title_block = (
        f'<{ot} class="ips-page-title-block">'
        f'<h1 class="ips-page-title">{html.escape(title)}</h1>'
        f"{sub_html}"
        f"</{ct}>"
    )

    if actions:
        n = len(actions)
        if actions_column_ratio:
            title_w, actions_w = actions_column_ratio
        elif n >= 3:
            title_w, actions_w = 1.65, 2.35
        else:
            title_w, actions_w = 2.55, 1.45
        main_col, act_col = st.columns([title_w, actions_w], gap="small", vertical_alignment="top")
        with main_col:
            st.markdown(
                f'<{ot} class="ips-page-header"><{ot} class="ips-page-title-row">{title_block}</{ct}></{ct}>',
                unsafe_allow_html=True,
            )
        with act_col:
            st.markdown(
                '<span class="ips-page-actions-marker" aria-hidden="true"></span>',
                unsafe_allow_html=True,
            )
            if n == 1:
                actions[0]()
            elif n == 2:
                bc1, bc2 = st.columns([0.78, 1.22], gap="small")
                with bc1:
                    actions[0]()
                with bc2:
                    actions[1]()
            elif n == 3:
                bc1, bc2, bc3 = st.columns([0.95, 1.55, 1.1], gap="small")
                with bc1:
                    actions[0]()
                with bc2:
                    actions[1]()
                with bc3:
                    actions[2]()
            else:
                cols = st.columns(min(n, 4), gap="small")
                for i, widget in enumerate(actions):
                    with cols[i % len(cols)]:
                        widget()
    else:
        st.markdown(
            f'<{ot} class="ips-page-header"><{ot} class="ips-page-title-row">{title_block}</{ct}></{ct}>',
            unsafe_allow_html=True,
        )


def render_page_header(
    title: str,
    subtitle: str = "",
    *,
    actions_cols: list[_ActionFn] | None = None,
    actions: list[_ActionFn] | None = None,
    show_logo: bool = False,
) -> None:
    """Backward-compatible wrapper around ``render_page_brand_header``."""
    _ = show_logo  # sidebar logo only; never render page title icon
    merged = actions or actions_cols
    render_page_brand_header(title, subtitle or None, actions=merged)


def _initials(name: str) -> str:
    parts = [p for p in str(name or "").strip().split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def render_person_profile_header(
    name: str,
    *,
    role: str = "",
    department: str = "",
    status: str = "Active",
    email: str = "",
    phone: str = "",
    last_login: str = "",
    status_html: str = "",
) -> None:
    """Profile summary row matching Coastal/IPS Users detail header."""
    ot, ct = "d" + "iv", "/" + "d" + "iv"
    pill = status_html or ""
    if not pill and status:
        try:
            from app.components.status import status_pill_html
        except ImportError:
            from components.status import status_pill_html  # type: ignore
        pill = status_pill_html(status)
    sub_parts = [html.escape(x) for x in (role, department) if str(x or "").strip()]
    sub = " · ".join(sub_parts)
    contact_lines = []
    if email:
        contact_lines.append(html.escape(email))
    if phone:
        contact_lines.append(html.escape(phone))
    if last_login:
        contact_lines.append(f"Last login: {html.escape(last_login)}")
    contact = "<br>".join(contact_lines)
    st.markdown(
        f"""
<{ot} class="ips-profile-header">
  <{ot} class="ips-profile-avatar">{html.escape(_initials(name))}</{ct}>
  <{ot} class="ips-profile-main">
    <p class="ips-profile-name">{html.escape(name)} {pill}</p>
    <p class="ips-profile-sub">{sub}</p>
    <{ot} class="ips-profile-contact">{contact}</{ct}>
  </{ct}>
</{ct}>
""",
        unsafe_allow_html=True,
    )


def _navigate_ops_quick_action(slug: str) -> None:
    """Navigate from operations dashboard quick actions."""
    picked = str(slug or "").strip()
    if not picked:
        return
    try:
        from app.auth import current_role
        from app.navigation import normalize_nav_slug, set_nav_slug
        from app.utils.permissions import role_can_access_page
    except ImportError:
        from auth import current_role  # type: ignore
        from navigation import normalize_nav_slug, set_nav_slug  # type: ignore
        from utils.permissions import role_can_access_page  # type: ignore

    if picked == "job_costing":
        if not role_can_access_page(current_role(), "jobs"):
            st.warning("You do not have access to that page.")
            return
        try:
            from app.navigation import open_jobs_job_costing
        except ImportError:
            from navigation import open_jobs_job_costing  # type: ignore
        open_jobs_job_costing()
        st.rerun()
        return

    target = normalize_nav_slug(picked)
    if not role_can_access_page(current_role(), target):
        st.warning("You do not have access to that page.")
        return
    set_nav_slug(target)
    st.rerun()


def render_ops_quick_action_tiles(
    actions: list[tuple[str, str, str]],
    *,
    key_prefix: str = "ips_ops_qa",
    title: str = "Quick Actions",
) -> None:
    """Compact Quick Actions toolbar for the operations dashboard."""
    with st.container(key="dashboard_ops_quick_actions"):
        st.markdown(
            f'<p class="ips-ops-quick-toolbar-title">{html.escape(title)}</p>',
            unsafe_allow_html=True,
        )
        cols = st.columns(len(actions), gap="small")
        for idx, col in enumerate(cols):
            icon, label, slug = actions[idx]
            with col:
                if st.button(
                    f"{icon} {label}",
                    key=f"{key_prefix}_{idx}",
                    use_container_width=True,
                ):
                    _navigate_ops_quick_action(slug)


def render_dashboard_quick_actions(
    actions: list[tuple[str, str, str]],
    *,
    key_prefix: str = "ips_dash_qa",
    title: str = "Quick Actions",
) -> None:
    """
    Compact dashboard quick-action card with a 4-column button grid.

    Each item: (icon, label, nav_slug_or_empty).
    """
    with st.container(key="dashboard_quick_actions"):
        st.markdown(
            f'<div class="ips-quick-actions-header">'
            f'<p class="ips-quick-actions-title">{html.escape(title)}</p>'
            f"</div>",
            unsafe_allow_html=True,
        )
        row_size = 4
        for row_start in range(0, len(actions), row_size):
            cols = st.columns(row_size, gap="small")
            for j, col in enumerate(cols):
                idx = row_start + j
                if idx >= len(actions):
                    break
                icon, label, slug = actions[idx]
                with col:
                    if st.button(
                        f"{icon}\n{label}",
                        key=f"{key_prefix}_{idx}",
                        use_container_width=True,
                    ):
                        if slug:
                            _navigate_ops_quick_action(slug)


def render_quick_actions_grid(
    actions: list[tuple[str, str, str]],
    *,
    key_prefix: str = "ips_qa",
) -> None:
    """Backward-compatible alias for ``render_dashboard_quick_actions``."""
    render_dashboard_quick_actions(actions, key_prefix=key_prefix)
