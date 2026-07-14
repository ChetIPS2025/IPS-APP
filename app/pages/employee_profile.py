"""My Profile — read-only workforce profile for the signed-in employee."""

from __future__ import annotations

import html

import streamlit as st

from app.auth import current_profile, current_role, effective_role
from app.components.headers import render_page_header
from app.pages._core._access import begin_module
from app.pages._core._data import get_employee
from app.services.certification_helpers import resolve_logged_in_employee_id
from app.styles import inject_employee_portal_css
from app.utils.formatting import fmt_date
def render() -> None:
    if not begin_module("employee_profile"):
        return
    inject_employee_portal_css()
    st.markdown(
        '<span class="ips-employee-profile-page" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    render_page_header("My Profile", "View your employee profile information.", icon="👤")

    profile = current_profile() or {}
    employee_id = resolve_logged_in_employee_id(profile)
    emp = get_employee(employee_id) if employee_id else None

    name = html.escape(str((emp or profile).get("full_name") or (emp or profile).get("name") or "—"))
    email = html.escape(str((emp or profile).get("email") or "—"))
    phone = html.escape(str((emp or profile).get("phone") or "—"))
    department = html.escape(str((emp or profile).get("department") or "—"))
    role = html.escape(str(effective_role() or "Employee").replace("_", " ").title())
    hire = ""
    if emp and emp.get("hire_date"):
        hire = fmt_date(str(emp.get("hire_date") or "")[:10])

    st.markdown(
        f"""
<div class="ips-ep-card">
  <p><strong>Name</strong><br>{name}</p>
  <p><strong>Email</strong><br>{email}</p>
  <p><strong>Phone</strong><br>{phone}</p>
  <p><strong>Department</strong><br>{department}</p>
  <p><strong>Role</strong><br>{role}</p>
  <p><strong>Hire date</strong><br>{html.escape(hire or "—")}</p>
</div>
""",
        unsafe_allow_html=True,
    )

    st.caption("Contact HR or your supervisor to update profile information.")
