"""Dashboard panel for shared office to-do reminders (job-less todos)."""

from __future__ import annotations

import html
from datetime import date
from typing import Any

import streamlit as st

try:
    from app.auth import current_profile, current_role, effective_role
    from app.pages._core._crud import apply_persist_feedback, is_demo_id
    from app.pages._core._data import load_tasks, task_assignee_options
    from app.services.management_reminders_service import (
        can_create_office_reminder,
        complete_management_reminder,
        create_management_reminder,
        due_date_badge,
        filter_dashboard_reminders,
    )
    from app.utils.formatting import fmt_date
except ImportError:
    from auth import current_profile, current_role, effective_role  # type: ignore
    from pages._core._crud import apply_persist_feedback, is_demo_id  # type: ignore
    from pages._core._data import load_tasks, task_assignee_options  # type: ignore
    from services.management_reminders_service import (  # type: ignore
        can_create_office_reminder,
        complete_management_reminder,
        create_management_reminder,
        due_date_badge,
        filter_dashboard_reminders,
    )
    from utils.formatting import fmt_date  # type: ignore


def _default_assignee(profile: dict[str, Any], options: list[str]) -> str:
    full = str(profile.get("full_name") or "").strip()
    if full and full in options:
        return full
    for opt in options:
        if full and full.casefold() in opt.casefold():
            return opt
    return options[0] if options else "— Select —"


def render_dashboard_management_reminders_section(*, limit: int = 8) -> None:
    """Shared office to-dos: managers see all open items; others see assigned work."""
    profile = current_profile() or {}
    role = effective_role()
    reminders = filter_dashboard_reminders(
        load_tasks(),
        profile=profile,
        role=role,
        limit=limit,
    )
    can_create = can_create_office_reminder(role)
    assignee_options = [o for o in task_assignee_options() if o]
    if can_create and assignee_options and "ips_dash_mr_assignee" not in st.session_state:
        st.session_state["ips_dash_mr_assignee"] = _default_assignee(profile, assignee_options)

    ot = "d" + "iv"

    def _go_tasks() -> None:
        try:
            from app.navigation import set_nav_slug
        except ImportError:
            from navigation import set_nav_slug  # type: ignore
        set_nav_slug("tasks")
        st.rerun()

    with st.container(key="dashboard_management_reminders"):
        hdr_l, hdr_r = st.columns([2.35, 1.65], gap="small", vertical_alignment="center")
        with hdr_l:
            st.markdown(
                f'<{ot} class="ips-dash-mr-head">'
                f'<p class="ips-dash-mr-title-bar">Office To-Do List</p>'
                f'<p class="ips-dash-mr-subtitle">Shared follow-ups and office tasks — not job subjobs</p>'
                f"</{ot}>",
                unsafe_allow_html=True,
            )
        with hdr_r:
            b_add, b_all = st.columns(2, gap="small")
            with b_add:
                if can_create and st.button(
                    "+ Add To-Do",
                    key="ips_dash_mr_toggle_form",
                    type="primary",
                    use_container_width=True,
                ):
                    st.session_state["ips_dash_mr_form"] = not st.session_state.get("ips_dash_mr_form")
                    st.rerun()
            with b_all:
                if st.button("View Tasks", key="ips_dash_mr_tasks", use_container_width=True):
                    _go_tasks()

        if can_create and st.session_state.get("ips_dash_mr_form"):
            with st.form("ips_dash_mr_new_form", clear_on_submit=True):
                st.text_input("To-do", placeholder="Follow up on vendor quote…", key="ips_dash_mr_title")
                c1, c2 = st.columns(2)
                with c1:
                    st.checkbox("Due date", key="ips_dash_mr_has_due")
                    st.date_input("Due", value=date.today(), key="ips_dash_mr_due")
                with c2:
                    st.selectbox("Assign to", assignee_options, key="ips_dash_mr_assignee")
                if st.form_submit_button("Save to-do", type="primary"):
                    due: date | None = None
                    if st.session_state.get("ips_dash_mr_has_due"):
                        due_val = st.session_state.get("ips_dash_mr_due")
                        if isinstance(due_val, date):
                            due = due_val
                    ok, msg = create_management_reminder(
                        title=str(st.session_state.get("ips_dash_mr_title") or ""),
                        assignee_name=str(st.session_state.get("ips_dash_mr_assignee") or ""),
                        due_date=due,
                    )
                    if apply_persist_feedback(ok, msg):
                        st.session_state["ips_dash_mr_form"] = False
                        st.rerun()

        if not reminders:
            st.markdown(
                '<p class="ips-dash-mr-empty">No open office to-dos.</p>',
                unsafe_allow_html=True,
            )
        else:
            for row in reminders:
                rid = str(row.get("id") or "").strip()
                title = html.escape(str(row.get("title") or "Untitled"))
                assignee = html.escape(str(row.get("assigned_to") or "—"))
                due_label, level = due_date_badge(row.get("due_date"))
                due_date = str(row.get("due_date") or "")[:10]
                meta_date = html.escape(fmt_date(due_date) if due_date else "")
                meta = f"Assigned to {assignee}"
                if meta_date:
                    meta += f" · Due {meta_date}"

                main_col, badge_col, done_col = st.columns([3.2, 1.1, 0.9], gap="small", vertical_alignment="center")
                with main_col:
                    st.markdown(
                        f'<{ot} class="ips-dash-mr-item-text">'
                        f'<p class="ips-dash-mr-item-title">{title}</p>'
                        f'<p class="ips-dash-mr-item-meta">{meta}</p>'
                        f"</{ot}>",
                        unsafe_allow_html=True,
                    )
                with badge_col:
                    st.markdown(
                        f'<span class="ips-deadline-badge {html.escape(level)}">{html.escape(due_label)}</span>',
                        unsafe_allow_html=True,
                    )
                with done_col:
                    if rid and st.button(
                        "Done",
                        key=f"ips_dash_mr_done_{rid}",
                        type="primary",
                        disabled=is_demo_id(rid),
                        use_container_width=True,
                    ):
                        ok, msg = complete_management_reminder(rid)
                        if apply_persist_feedback(ok, msg):
                            st.rerun()
