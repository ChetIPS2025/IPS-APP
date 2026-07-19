"""Employee Portal quick actions."""

from __future__ import annotations

import streamlit as st

from app.navigation import set_nav_slug
from app.services.employee_portal_service import EmployeePortalContext

_SHOW_ALL_JOBS_KEY = "ips_ep_show_all_jobs"
_PORTAL_VIEW_QUERY = "portal_view"


def quick_action_button_key(action_id: str, *, employee_id: str, view_mode: str) -> str:
    eid = str(employee_id or "none").strip() or "none"
    return f"ep_quick_{action_id}_{view_mode}_{eid}"


def build_employee_portal_quick_actions(ctx: EmployeePortalContext) -> list[dict[str, object]]:
    upload_slug = "scan_asset" if ctx.can_scan_assets else "employee_qr_scan"
    return [
        {
            "icon": "📷",
            "label": "Scan QR Code",
            "nav_slug": "employee_qr_scan",
            "enabled": True,
            "action_id": "qr_scan",
            "primary": True,
        },
        {
            "icon": "💼",
            "label": "My Jobs",
            "nav_slug": "__my_jobs__",
            "enabled": True,
            "action_id": "my_jobs",
            "primary": False,
        },
        {
            "icon": "⏱",
            "label": "Timekeeping",
            "nav_slug": "timekeeping",
            "enabled": ctx.can_view_timekeeping,
            "action_id": "timekeeping",
            "primary": False,
        },
        {
            "icon": "📸",
            "label": "Upload Photo",
            "nav_slug": upload_slug,
            "enabled": True,
            "action_id": "upload_photo",
            "primary": False,
        },
        {
            "icon": "📄",
            "label": "Documents",
            "nav_slug": "employee_resources",
            "enabled": ctx.can_view_resources,
            "action_id": "documents",
            "primary": False,
        },
    ]


def render_quick_actions(ctx: EmployeePortalContext) -> None:
    st.markdown('<h3 class="ips-ep-section-title">Quick Actions</h3>', unsafe_allow_html=True)
    actions = [a for a in build_employee_portal_quick_actions(ctx) if a.get("enabled")]
    if not actions:
        return
    cols = st.columns(min(len(actions), 3))
    for idx, action in enumerate(actions):
        icon = str(action.get("icon") or "")
        label = str(action.get("label") or "")
        slug = str(action.get("nav_slug") or "")
        action_id = str(action.get("action_id") or f"action_{idx}")
        with cols[idx % len(cols)]:
            if st.button(
                f"{icon}  {label}",
                key=quick_action_button_key(action_id, employee_id=ctx.employee_id, view_mode=ctx.view_as_mode),
                use_container_width=True,
                type="primary" if action.get("primary") else "secondary",
            ):
                if slug == "__my_jobs__":
                    st.session_state[_SHOW_ALL_JOBS_KEY] = True
                    if _PORTAL_VIEW_QUERY in st.query_params:
                        st.query_params[_PORTAL_VIEW_QUERY] = "jobs"
                else:
                    set_nav_slug(slug)
                st.rerun()
