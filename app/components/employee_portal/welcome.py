"""Employee Portal welcome card."""

from __future__ import annotations

import html

import streamlit as st

from app.services.employee_portal_service import (
    EmployeePortalContext,
    portal_employee_avatar_html,
    portal_employee_title,
    portal_greeting_name,
    portal_greeting_period,
)
from app.utils.formatting import fmt_date


def render_welcome_card(ctx: EmployeePortalContext) -> None:
    name = portal_greeting_name(ctx.profile)
    period = portal_greeting_period()
    today = fmt_date(ctx.today.isoformat())
    title = html.escape(portal_employee_title(ctx.profile, ctx.employee, role=ctx.role))
    role_label = html.escape(str(ctx.role or "Employee").replace("_", " ").title())
    avatar_html = portal_employee_avatar_html(ctx.profile, ctx.employee)
    st.markdown(
        f"""
<div class="ips-ep-welcome-card">
  <div class="ips-ep-welcome-top">
    {avatar_html}
    <div class="ips-ep-welcome-text">
      <p class="ips-ep-greeting">{html.escape(period)}, {html.escape(name)}</p>
      <p class="ips-ep-date">{html.escape(today)}</p>
      <p class="ips-ep-role">{title}</p>
      <p class="ips-ep-role-sub">{role_label}</p>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
