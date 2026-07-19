"""Conditional User Details tab rendering (lazy-loaded sections)."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

from app.components.record_modal import detail_field_html, dialog_card_html, placeholder_html, safe_value, status_pill_html
from app.components.tabs import render_tabs
from app.components.tables import render_data_table
from app.pages._core._data import ACTIVE_EMPLOYEE_KEY, load_employee_documents
from app.services.people_directory_service import PeoplePermissions
from app.utils.constants import DEPARTMENTS, SESSION_NAV_KEY
from app.utils.formatting import fmt_date

_EMPLOYEE_DETAIL_TAB_KEY = "ips_employee_detail_active_tab"
_EMPLOYEE_TABS = [
    "Overview",
    "Role & Permissions",
    "Departments",
    "Assigned Jobs",
    "Certifications",
    "Documents",
    "Time History",
    "Notes",
    "Activity Log",
]


def reset_employee_detail_tab() -> None:
    st.session_state[_EMPLOYEE_DETAIL_TAB_KEY] = "Overview"


def render_employee_detail_tabs(
    emp: dict[str, Any],
    *,
    permissions: PeoplePermissions,
    format_phone_fn,
    display_phone_fn,
    display_employee_number_fn,
) -> None:
    from app.perf_debug import perf_span

    eid = str(emp.get("id") or "")
    name = safe_value(emp.get("name"))
    email = safe_value(emp.get("email"))
    billing_class = safe_value(emp.get("billing_class") or emp.get("trade"))
    permission_role = safe_value(emp.get("permission_role") or emp.get("role"))
    dept = safe_value(emp.get("department"))
    status = safe_value(emp.get("status"))

    active_tab = render_tabs(
        _EMPLOYEE_TABS,
        session_key=_EMPLOYEE_DETAIL_TAB_KEY,
        default="Overview",
    )

    if active_tab == "Overview":
        with perf_span("people.detail.overview"):
            overview_html = (
                f'<div class="ips-detail-grid">'
                f"{detail_field_html('Full Name', name)}"
                f"{detail_field_html('Employee #', emp.get('employee_number'))}"
                f"{detail_field_html('Email', email)}"
                f"{detail_field_html('Phone', format_phone_fn(display_phone_fn(emp)))}"
                f"{detail_field_html('Position', emp.get('position'))}"
                f"{detail_field_html('Trade', emp.get('trade'))}"
                f"{detail_field_html('Hire Date', fmt_date(emp.get('hire_date')))}"
                f"{detail_field_html('Username', emp.get('username'))}"
                f"{detail_field_html('Member Since', fmt_date(emp.get('member_since')))}"
                f'{detail_field_html("Status", status, html_value=status_pill_html(status))}'
                f"</div>"
            )
            st.markdown(dialog_card_html("User Information", overview_html), unsafe_allow_html=True)
            security_html = (
                f'<div class="ips-detail-grid">'
                f"{detail_field_html('Last Login', emp.get('last_login'))}"
                f"{detail_field_html('Two-Factor Auth', 'Enabled')}"
                f"{detail_field_html('Failed Attempts', '0')}"
                f"{detail_field_html('Account Locked', 'No')}"
                f"</div>"
            )
            st.markdown(dialog_card_html("Security", security_html), unsafe_allow_html=True)

    elif active_tab == "Role & Permissions":
        with perf_span("people.detail.role"):
            role_html = (
                f'<div class="ips-detail-grid">'
                f"{detail_field_html('Billing classification', billing_class)}"
                f"{detail_field_html('Permission role', permission_role)}"
                f"{detail_field_html('Department', dept)}"
                f"</div>"
                f'<p style="margin:0.75rem 0 0;font-size:0.8125rem;color:#64748b;">'
                f"View Dashboard · Create &amp; Edit Jobs · Manage Inventory"
                f"</p>"
            )
            st.markdown(dialog_card_html("Role & Permissions", role_html), unsafe_allow_html=True)

    elif active_tab == "Departments":
        dept_html = (
            f'<div class="ips-detail-grid">'
            f"{detail_field_html('Primary Department', dept)}"
            f"</div>"
        )
        st.markdown(dialog_card_html("Departments", dept_html), unsafe_allow_html=True)
        st.caption(f"Available departments: {', '.join(DEPARTMENTS)}")

    elif active_tab == "Assigned Jobs":
        placeholder_html("Assigned jobs will load from Supabase in a later phase.")

    elif active_tab == "Certifications":
        with perf_span("people.detail.certifications"):
            from app.pages.employee_certifications import render_employee_detail_certifications_tab

            render_employee_detail_certifications_tab(eid, employee=emp, session_prefix="emp_cert_")

    elif active_tab == "Documents":
        with perf_span("people.detail.documents"):
            docs = _load_employee_documents_cached(eid, role=permissions.role)
            if not permissions.can_view_hr_documents:
                st.caption("Restricted HR documents are visible to administrators only.")
            _doc_table(docs)
            if st.button("Open Documents Module", key=f"emp_open_docs_{eid}"):
                st.session_state[ACTIVE_EMPLOYEE_KEY] = eid
                st.session_state[SESSION_NAV_KEY] = "employee_documents"
                st.rerun()

    elif active_tab == "Time History":
        placeholder_html("Time history will load from Supabase in a later phase.")

    elif active_tab == "Notes":
        notes_text = safe_value(emp.get("notes"), "No notes entered.")
        notes_html = (
            f'<p style="margin:0;font-size:0.875rem;color:#0f172a;line-height:1.5;white-space:pre-wrap;">'
            f"{html.escape(notes_text)}"
            f"</p>"
        )
        st.markdown(dialog_card_html("Notes", notes_html), unsafe_allow_html=True)

    elif active_tab == "Activity Log":
        with perf_span("people.detail.activity"):
            placeholder_html("Activity log will load from Supabase in a later phase.")


def _load_employee_documents_cached(employee_id: str, *, role: str) -> list[dict[str, Any]]:
    from app.pages._core._data import employees_catalog_data_version
    from app.pages._core.page_data_cache import page_data_cache_get

    eid = str(employee_id or "").strip()
    role_key = str(role or "").strip().casefold()
    cache_key = f"people_employee_docs:{eid}:{role_key}:{employees_catalog_data_version()}"

    return page_data_cache_get(
        cache_key,
        lambda: load_employee_documents(eid, role=role),
    )


def _doc_table(docs: list[dict]) -> None:
    if not docs:
        st.caption("No documents on file.")
        return

    def _cell(field: str, row: dict) -> str:
        if field == "access":
            if row.get("is_restricted"):
                return '<span class="ips-restricted-tag">RESTRICTED</span>'
            return '<span style="color:#64748b;font-size:0.75rem;">Standard</span>'
        return html.escape(str(row.get(field) or "—"))

    render_data_table(
        docs,
        [
            ("doc_type", "TYPE"),
            ("filename", "FILE"),
            ("upload_date", "UPLOADED"),
            ("access", "ACCESS"),
        ],
        cell_html=_cell,
    )


__all__ = ["render_employee_detail_tabs", "reset_employee_detail_tab"]
