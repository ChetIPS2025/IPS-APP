"""Page header components."""

from __future__ import annotations

import html
from collections.abc import Callable

import streamlit as st

_ActionFn = Callable[[], None]


def render_main_brand_bar(*, brand_actions: list[_ActionFn] | None = None, show_menu: bool = True) -> None:
    """Deprecated: gray in-content brand bar removed; blue nav rail is the app chrome."""
    _ = (brand_actions, show_menu)


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
    Compact page title row at the top of the content area.

    Set ``include_brand_bar=True`` only for standalone pages outside ``render_module``.
    """
    ot, ct = "d" + "iv", "/" + "d" + "iv"
    _ = (brand_actions, include_brand_bar)

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
    shell_marker = '<span class="ips-page-shell-marker" aria-hidden="true"></span>'
    page_header_open = (
        f'<{ot} class="ips-page-header">{shell_marker}<{ot} class="ips-page-title-row">'
    )
    page_header_close = f"</{ct}></{ct}>"

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
                f"{page_header_open}{title_block}{page_header_close}",
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
            f"{page_header_open}{title_block}{page_header_close}",
            unsafe_allow_html=True,
        )


def render_users_page_header(
    title: str,
    subtitle: str | None = None,
    *,
    actions: list[_ActionFn] | None = None,
) -> None:
    """Users page header card with icon, title, and subtitle."""
    _ = actions
    shell_marker = '<span class="ips-page-shell-marker" aria-hidden="true"></span>'
    sub_html = (
        f'<p class="users-page-header-subtitle">{html.escape(subtitle)}</p>'
        if subtitle
        else ""
    )
    st.markdown(
        f"""
{shell_marker}
<div class="users-page-header-card">
  <div class="users-page-header-inner">
    <div class="users-page-header-icon" aria-hidden="true">
      <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M20 21a8 8 0 0 0-16 0"/>
        <circle cx="12" cy="7" r="4"/>
      </svg>
    </div>
    <div class="users-page-header-text">
      <h1 class="users-page-header-title">{html.escape(title)}</h1>
      {sub_html}
    </div>
  </div>
</div>
        """,
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
        from app.auth import effective_role
        from app.navigation import normalize_nav_slug, set_nav_slug
        from app.utils.permissions import role_can_access_page
    except ImportError:
        from auth import effective_role  # type: ignore
        from navigation import normalize_nav_slug, set_nav_slug  # type: ignore
        from utils.permissions import role_can_access_page  # type: ignore

    if picked == "job_costing":
        if not role_can_access_page(effective_role(), "jobs"):
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
    if not role_can_access_page(effective_role(), target):
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
            f'<p class="ips-ops-quick-toolbar-title quick-actions-title">'
            f'{html.escape(title.upper())}</p>',
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
