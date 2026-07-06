"""My Profile — read-only workforce profile for the signed-in employee."""

from __future__ import annotations

import html

import streamlit as st

try:
    from app.auth import current_profile, current_role
    from app.pages._core._access import begin_module
    from app.pages._core._data import get_employee
    from app.services.certification_helpers import resolve_logged_in_employee_id
    from app.styles import inject_employee_portal_css, inject_global_css
    from app.utils.formatting import fmt_date
except ImportError:
    from auth import current_profile, current_role  # type: ignore
    from pages._core._access import begin_module  # type: ignore
    from pages._core._data import get_employee  # type: ignore
    from services.certification_helpers import resolve_logged_in_employee_id  # type: ignore
    from styles import inject_employee_portal_css, inject_global_css  # type: ignore
    from utils.formatting import fmt_date  # type: ignore


def render() -> None:
    if not begin_module("employee_profile"):
        return
    inject_global_css()
    inject_employee_portal_css()
    st.markdown(
        '<span class="ips-employee-profile-page ips-page-shell-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    st.markdown('<h2 class="ips-ep-page-title">My Profile</h2>', unsafe_allow_html=True)

    profile = current_profile() or {}
    employee_id = resolve_logged_in_employee_id(profile)
    emp = get_employee(employee_id) if employee_id else None

    name = html.escape(str((emp or profile).get("full_name") or (emp or profile).get("name") or "—"))
    email = html.escape(str((emp or profile).get("email") or "—"))
    phone = html.escape(str((emp or profile).get("phone") or "—"))
    department = html.escape(str((emp or profile).get("department") or "—"))
    role = html.escape(str(current_role() or "Employee").replace("_", " ").title())
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
