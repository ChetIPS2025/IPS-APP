"""Page header components."""

from __future__ import annotations

import html

import streamlit as st

try:
    from app.branding import header_logo_html
except ImportError:
    from branding import header_logo_html  # type: ignore


def render_page_header(
    title: str,
    subtitle: str = "",
    *,
    actions_cols: list | None = None,
    show_logo: bool = True,
) -> None:
    """Compact page header row with optional logo, title, subtitle, and actions."""
    ot, ct = "d" + "iv", "/" + "d" + "iv"
    st.markdown(f'<{ot} class="ips-page-shell-marker"></{ct}>', unsafe_allow_html=True)

    logo = header_logo_html(height=40) if show_logo else ""
    sub = (
        f'<p class="ips-page-subtitle">{html.escape(subtitle)}</p>'
        if subtitle
        else ""
    )
    header_html = (
        f'<{ot} class="ips-page-header-bar">'
        f"{logo}"
        f'<{ot} class="ips-page-header-text">'
        f'<h1 class="ips-page-title">{html.escape(title)}</h1>'
        f"{sub}"
        f"</{ct}>"
        f"</{ct}>"
    )

    if actions_cols:
        main_col, act_col = st.columns([4, 1], gap="small", vertical_alignment="center")
        with main_col:
            st.markdown(header_html, unsafe_allow_html=True)
        with act_col:
            st.markdown(f'<{ot} class="ips-header-actions">', unsafe_allow_html=True)
            ac1, ac2 = st.columns(2, gap="small")
            for i, widget in enumerate(actions_cols):
                with ac1 if i % 2 == 0 else ac2:
                    widget()
            st.markdown(f"</{ct}>", unsafe_allow_html=True)
    else:
        st.markdown(header_html, unsafe_allow_html=True)


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
                            st.session_state["ips_nav_page"] = slug
                            st.rerun()


def render_quick_actions_grid(
    actions: list[tuple[str, str, str]],
    *,
    key_prefix: str = "ips_qa",
) -> None:
    """Backward-compatible alias for ``render_dashboard_quick_actions``."""
    render_dashboard_quick_actions(actions, key_prefix=key_prefix)
