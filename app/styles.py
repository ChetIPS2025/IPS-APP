"""
Centralized IPS operations platform CSS.

Call inject_global_css() on every Streamlit render (no session guard).
"""

from __future__ import annotations

import streamlit as st

# Design tokens
APP_BG = "#f4f6f9"
SIDEBAR_BG = "#ffffff"
CARD_BG = "#ffffff"
BORDER = "#e5eaf2"
PRIMARY = "#2563eb"
PRIMARY_HOVER = "#1d4ed8"
TEXT = "#0f172a"
TEXT_MUTED = "#64748b"
SELECTED_BG = "#eff6ff"
SELECTED_BORDER = "#2563eb"


def inject_users_module_css() -> None:
    """Users list custom table styling — call at the top of the users page render."""
    st.markdown(
        f"""
<style id="ips-users-module-v5">
.ips-users-table-wrap {{
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  overflow: hidden;
  margin-bottom: 0.5rem;
}}
.ips-users-header-row {{
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  padding: 8px 10px;
  font-size: 12px;
  font-weight: 800;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  min-height: 38px;
  display: flex;
  align-items: center;
}}
.ips-users-row {{
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  padding: 6px 10px;
  min-height: 52px;
}}
.ips-users-row:hover {{
  background: #eef5ff;
}}
.ips-users-row-selected {{
  background: #eaf2ff !important;
}}
.ips-users-cell {{
  color: {TEXT};
  font-size: 0.8125rem;
  line-height: 1.25;
  min-width: 0;
}}
.ips-users-name {{
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.25;
  word-break: break-word;
}}
.ips-users-muted {{
  font-size: 13px;
  color: #64748b;
  word-break: break-word;
}}
.ips-users-phone {{
  font-size: 0.78rem;
  white-space: nowrap;
  color: #334155;
}}
.ips-user-pill {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 26px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}}
.ips-user-employee {{
  background: #dbeafe;
  color: #1d4ed8;
}}
.ips-user-system {{
  background: #f1f5f9;
  color: #475569;
}}
.ips-user-status-active {{
  background: #dcfce7;
  color: #166534;
}}
.ips-user-status-inactive {{
  background: #f1f5f9;
  color: #475569;
}}
.ips-user-status-locked {{
  background: #fee2e2;
  color: #991b1b;
}}
.ips-user-status-pending {{
  background: #fef3c7;
  color: #92400e;
}}
.st-key-users_table_wrap [data-testid="stVerticalBlock"] {{
  gap: 0 !important;
}}
.st-key-users_table_wrap [data-testid="stHorizontalBlock"] {{
  gap: 0.35rem !important;
  align-items: center !important;
  border-bottom: 1px solid #e2e8f0;
  padding: 6px 10px !important;
  margin: 0 !important;
  min-height: 52px;
}}
.st-key-users_table_wrap [data-testid="stHorizontalBlock"]:first-of-type {{
  background: #f8fafc;
  min-height: 40px;
  padding: 8px 10px !important;
}}
.st-key-users_table_wrap [data-testid="stHorizontalBlock"]:not(:first-of-type):hover {{
  background: #eef5ff;
}}
.st-key-users_table_wrap [data-testid="stHorizontalBlock"]:has([data-testid="stCheckbox"] input:checked) {{
  background: #eaf2ff !important;
}}
.st-key-users_table_wrap [data-testid="stElementContainer"] {{
  margin-bottom: 0 !important;
  padding-bottom: 0 !important;
}}
.st-key-users_table_wrap [data-testid="stCheckbox"] {{
  margin: 0 !important;
}}
.st-key-users_table_wrap [data-testid="stCheckbox"] label {{
  min-height: 24px !important;
  margin: 0 !important;
}}
.st-key-users_table_wrap .stButton > button {{
  height: 32px !important;
  min-height: 32px !important;
  padding: 0 12px !important;
  border-radius: 9px !important;
  font-size: 14px !important;
  width: auto !important;
}}
.ips-user-delete-actions {{
  margin: 0.35rem 0 0.75rem;
  display: flex;
  justify-content: flex-end;
}}
.ips-user-delete-warning {{
  background: #fff7ed;
  border: 1px solid #fed7aa;
  border-radius: 12px;
  padding: 12px 14px;
  margin: 0.35rem 0 0.75rem;
  font-size: 0.8125rem;
  color: #7c2d12;
}}
.ips-user-delete-warning ul {{
  margin: 0.5rem 0 0.35rem;
  padding-left: 0;
  list-style: none;
}}
.ips-user-delete-warning ul li {{
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 3px 0;
  border-bottom: 1px solid #ffedd5;
}}
.ips-user-delete-warning ul li span {{
  color: #9a3412;
  font-weight: 600;
}}
.ips-user-delete-warning ul li strong {{
  color: #431407;
  font-weight: 700;
  text-align: right;
}}
.ips-user-delete-warning p {{
  margin: 0.5rem 0 0.25rem;
  font-weight: 600;
}}
.ips-user-delete-consequences {{
  margin: 0.25rem 0 0 !important;
  padding-left: 1.1rem !important;
  list-style: disc !important;
}}
.ips-user-delete-consequences li {{
  display: list-item !important;
  border: none !important;
  padding: 2px 0 !important;
  color: #9a3412;
}}
</style>
""",
        unsafe_allow_html=True,
    )


def inject_documents_module_css() -> None:
    """Documents hub table stability — call at the top of documents page render."""
    st.markdown(
        f"""
<style id="ips-documents-module-v1">
.ips-documents-page .ips-data-table-wrap,
.ips-documents-page .ips-data-table-stable .ips-data-table-header,
.ips-documents-page .ips-data-table-stable .ips-data-row {{
  display: grid !important;
  box-sizing: border-box !important;
}}
.ips-documents-page .ips-data-table-html .ips-data-row {{
  display: grid !important;
  min-height: 2.75rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
.ips-documents-page .ips-data-table-html .ips-data-cell {{
  overflow: hidden;
  text-overflow: ellipsis;
}}
</style>
""",
        unsafe_allow_html=True,
    )


def inject_customers_module_css() -> None:
    """Customers list custom table styling."""
    st.markdown(
        f"""
<style id="ips-customers-module-v2">
.ips-customers-table-wrap {{
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  overflow: hidden;
  margin-bottom: 0.5rem;
}}
.ips-customers-header-row {{
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  padding: 8px 10px;
  font-size: 12px;
  font-weight: 800;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  min-height: 38px;
  display: flex;
  align-items: center;
}}
.ips-customers-row {{
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  padding: 6px 10px;
  min-height: 52px;
}}
.ips-customers-row:hover {{
  background: #eef5ff;
}}
.ips-customers-row-selected {{
  background: #eaf2ff !important;
}}
.ips-customers-cell {{
  color: {TEXT};
  font-size: 0.8125rem;
  line-height: 1.25;
  min-width: 0;
}}
.ips-customers-name {{
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.25;
  word-break: break-word;
}}
.ips-customers-count-cell {{
  text-align: center;
  font-weight: 600;
}}
.ips-customer-status-pill {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 26px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}}
.ips-customer-status-active {{
  background: #dcfce7;
  color: #166534;
}}
.ips-customer-status-inactive {{
  background: #f1f5f9;
  color: #475569;
}}
.ips-customer-status-prospect {{
  background: #dbeafe;
  color: #1d4ed8;
}}
.ips-customer-status-on-hold {{
  background: #fef3c7;
  color: #92400e;
}}
.st-key-customers_table_wrap [data-testid="stVerticalBlock"] {{
  gap: 0 !important;
}}
.st-key-customers_table_wrap [data-testid="stHorizontalBlock"] {{
  gap: 0.35rem !important;
  align-items: center !important;
  border-bottom: 1px solid #e2e8f0;
  padding: 6px 10px !important;
  margin: 0 !important;
  min-height: 52px;
}}
.st-key-customers_table_wrap [data-testid="stHorizontalBlock"]:first-of-type {{
  background: #f8fafc;
  min-height: 40px;
  padding: 8px 10px !important;
}}
.st-key-customers_table_wrap [data-testid="stHorizontalBlock"]:not(:first-of-type):hover {{
  background: #eef5ff;
}}
.st-key-customers_table_wrap [data-testid="stHorizontalBlock"]:has([data-testid="stCheckbox"] input:checked) {{
  background: #eaf2ff !important;
}}
.st-key-customers_table_wrap [data-testid="stElementContainer"] {{
  margin-bottom: 0 !important;
  padding-bottom: 0 !important;
}}
.st-key-customers_table_wrap [data-testid="stCheckbox"] {{
  margin: 0 !important;
}}
.st-key-customers_table_wrap [data-testid="stCheckbox"] label {{
  min-height: 24px !important;
  margin: 0 !important;
}}
.ips-contacts-table-wrap {{
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  overflow: hidden;
  margin-bottom: 0.5rem;
}}
.ips-contacts-header-row {{
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  padding: 8px 10px;
  font-size: 12px;
  font-weight: 800;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  min-height: 38px;
  display: flex;
  align-items: center;
}}
.ips-contacts-row {{
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  padding: 6px 10px;
  min-height: 52px;
}}
.ips-contacts-row:hover {{
  background: #eef5ff;
}}
.ips-contacts-row-selected {{
  background: #eaf2ff !important;
}}
.ips-contacts-cell {{
  color: {TEXT};
  font-size: 0.8125rem;
  line-height: 1.25;
  min-width: 0;
  word-break: break-word;
}}
.ips-contacts-name {{
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.25;
  word-break: break-word;
}}
.ips-contacts-muted {{
  font-size: 13px;
  color: #64748b;
  word-break: break-word;
}}
.ips-contacts-email {{
  font-size: 13px;
  color: #0f172a;
  word-break: break-word;
  overflow-wrap: anywhere;
}}
.ips-contact-role-pill {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 26px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}}
.ips-contact-role-primary {{
  background: #dbeafe;
  color: #1d4ed8;
}}
.ips-contact-role-project {{
  background: #e0e7ff;
  color: #4338ca;
}}
.ips-contact-role-site {{
  background: #dcfce7;
  color: #166534;
}}
.ips-contact-role-safety {{
  background: #fee2e2;
  color: #991b1b;
}}
.ips-contact-role-billing {{
  background: #fef3c7;
  color: #92400e;
}}
.ips-contact-role-estimating {{
  background: #ede9fe;
  color: #6d28d9;
}}
.ips-contact-role-other {{
  background: #f1f5f9;
  color: #475569;
}}
.st-key-contacts_table_wrap_main [data-testid="stVerticalBlock"],
[class*="st-key-contacts_table_wrap_"] [data-testid="stVerticalBlock"] {{
  gap: 0 !important;
}}
.st-key-contacts_table_wrap_main [data-testid="stHorizontalBlock"],
[class*="st-key-contacts_table_wrap_"] [data-testid="stHorizontalBlock"] {{
  gap: 0.35rem !important;
  align-items: center !important;
  border-bottom: 1px solid #e2e8f0;
  padding: 6px 10px !important;
  margin: 0 !important;
  min-height: 52px;
}}
.st-key-contacts_table_wrap_main [data-testid="stHorizontalBlock"]:first-of-type,
[class*="st-key-contacts_table_wrap_"] [data-testid="stHorizontalBlock"]:first-of-type {{
  background: #f8fafc;
  min-height: 40px;
  padding: 8px 10px !important;
}}
.st-key-contacts_table_wrap_main [data-testid="stHorizontalBlock"]:not(:first-of-type):hover,
[class*="st-key-contacts_table_wrap_"] [data-testid="stHorizontalBlock"]:not(:first-of-type):hover {{
  background: #eef5ff;
}}
.st-key-contacts_table_wrap_main [data-testid="stHorizontalBlock"]:has([data-testid="stCheckbox"] input:checked),
[class*="st-key-contacts_table_wrap_"] [data-testid="stHorizontalBlock"]:has([data-testid="stCheckbox"] input:checked) {{
  background: #eaf2ff !important;
}}
.st-key-contacts_table_wrap_main [data-testid="stElementContainer"],
[class*="st-key-contacts_table_wrap_"] [data-testid="stElementContainer"] {{
  margin-bottom: 0 !important;
  padding-bottom: 0 !important;
}}
.st-key-contacts_table_wrap_main [data-testid="stCheckbox"],
[class*="st-key-contacts_table_wrap_"] [data-testid="stCheckbox"] {{
  margin: 0 !important;
}}
.st-key-contacts_table_wrap_main [data-testid="stCheckbox"] label,
[class*="st-key-contacts_table_wrap_"] [data-testid="stCheckbox"] label {{
  min-height: 24px !important;
  margin: 0 !important;
}}
.ips-inline-detail-card {{
  margin-top: 14px;
  background: #ffffff;
  border: 1px solid #dbe3ee;
  border-radius: 14px;
  padding: 14px;
}}
.ips-inline-detail-header {{
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}}
.ips-inline-detail-title {{
  font-size: 18px;
  font-weight: 800;
  color: #0f172a;
  line-height: 1.2;
}}
.ips-inline-detail-subtitle {{
  font-size: 13px;
  color: #64748b;
  margin-top: 3px;
}}
.ips-inline-detail-actions {{
  display: flex;
  justify-content: flex-end;
}}
.ips-inline-meta-grid {{
  display: grid;
  grid-template-columns: repeat(4, minmax(120px, 1fr));
  gap: 10px;
  margin-top: 10px;
}}
.ips-inline-meta-card {{
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 10px 12px;
}}
.ips-inline-meta-label {{
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #64748b;
  margin-bottom: 0.2rem;
}}
.ips-inline-meta-value {{
  font-size: 0.8125rem;
  color: #0f172a;
  line-height: 1.25;
  word-break: break-word;
}}
.ips-locations-table-wrap {{
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  overflow: hidden;
  margin-bottom: 0.5rem;
}}
.ips-locations-add-form {{
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 0.75rem 0.85rem;
  margin-bottom: 0.65rem;
}}
.ips-locations-header-row {{
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  padding: 8px 10px;
  font-size: 12px;
  font-weight: 800;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  min-height: 38px;
  display: flex;
  align-items: center;
}}
.ips-locations-row {{
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  padding: 6px 10px;
  min-height: 52px;
}}
.ips-locations-row:hover {{
  background: #eef5ff;
}}
.ips-locations-row-selected {{
  background: #eaf2ff !important;
}}
.ips-locations-cell {{
  color: {TEXT};
  font-size: 0.8125rem;
  line-height: 1.25;
  min-width: 0;
}}
.ips-locations-name {{
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.25;
  word-break: break-word;
}}
.ips-locations-muted {{
  font-size: 13px;
  color: #64748b;
  white-space: nowrap;
}}
.ips-location-pill {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}}
.ips-location-status-active {{
  background: #dcfce7;
  color: #166534;
}}
.ips-location-status-inactive {{
  background: #f1f5f9;
  color: #475569;
}}
.ips-location-status-on-hold {{
  background: #fef3c7;
  color: #92400e;
}}
.ips-location-flag-yes {{
  background: #dbeafe;
  color: #1d4ed8;
}}
.ips-location-flag-no {{
  background: #f1f5f9;
  color: #64748b;
}}
.st-key-locations_table_wrap [data-testid="stVerticalBlock"] {{
  gap: 0 !important;
}}
.st-key-locations_table_wrap [data-testid="stHorizontalBlock"] {{
  gap: 0.35rem !important;
  align-items: center !important;
  border-bottom: 1px solid #e2e8f0;
  padding: 6px 10px !important;
  margin: 0 !important;
  min-height: 52px;
}}
.st-key-locations_table_wrap [data-testid="stHorizontalBlock"]:first-of-type {{
  background: #f8fafc;
  min-height: 40px;
  padding: 8px 10px !important;
}}
.st-key-locations_table_wrap [data-testid="stHorizontalBlock"]:not(:first-of-type):hover {{
  background: #eef5ff;
}}
.st-key-locations_table_wrap [data-testid="stHorizontalBlock"]:has([data-testid="stCheckbox"] input:checked) {{
  background: #eaf2ff !important;
}}
.st-key-locations_table_wrap [data-testid="stElementContainer"] {{
  margin-bottom: 0 !important;
  padding-bottom: 0 !important;
}}
.st-key-locations_table_wrap [data-testid="stCheckbox"] {{
  margin: 0 !important;
}}
.st-key-locations_table_wrap [data-testid="stCheckbox"] label {{
  min-height: 24px !important;
  margin: 0 !important;
}}
</style>
""",
        unsafe_allow_html=True,
    )


def inject_jobs_module_css() -> None:
    """Jobs list custom table styling."""
    st.markdown(
        f"""
<style id="ips-jobs-module-v11">
.ips-jobs-table-wrap {{
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  overflow: hidden;
  margin-bottom: 0.5rem;
}}
.ips-jobs-header-row {{
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  padding: 8px 10px;
  font-size: 12px;
  font-weight: 800;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  min-height: 38px;
  display: flex;
  align-items: center;
}}
.ips-jobs-row {{
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  padding: 6px 10px;
  min-height: 52px;
}}
.ips-jobs-row:hover {{
  background: #eef5ff;
}}
.ips-jobs-row-selected {{
  background: #eaf2ff !important;
}}
.ips-jobs-cell {{
  color: {TEXT};
  font-size: 0.8125rem;
  line-height: 1.25;
  min-width: 0;
}}
.ips-jobs-number {{
  font-size: 14px;
  font-weight: 800;
  color: #2563eb;
  line-height: 1.25;
  white-space: nowrap;
}}
.ips-jobs-title {{
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.25;
  word-break: break-word;
}}
.ips-jobs-muted {{
  font-size: 13px;
  color: #64748b;
  word-break: break-word;
}}
.ips-job-status-pill {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 26px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}}
.ips-job-status-draft {{
  background: #f1f5f9;
  color: #475569;
}}
.ips-job-status-planning {{
  background: #dbeafe;
  color: #1d4ed8;
}}
.ips-job-status-scheduled {{
  background: #e0e7ff;
  color: #4338ca;
}}
.ips-job-status-active {{
  background: #dcfce7;
  color: #166534;
}}
.ips-job-status-awarded {{
  background: #dcfce7;
  color: #166534;
}}
.ips-job-status-on-hold {{
  background: #fef3c7;
  color: #92400e;
}}
.ips-job-status-completed {{
  background: #dcfce7;
  color: #166534;
}}
.ips-job-status-closed {{
  background: #f1f5f9;
  color: #475569;
}}
.ips-job-status-cancelled {{
  background: #fee2e2;
  color: #991b1b;
}}
.ips-job-status-archived {{
  background: #f1f5f9;
  color: #475569;
}}
.ips-job-status-estimate-pending {{
  background: #fef3c7;
  color: #92400e;
}}
.st-key-jobs_table_wrap [data-testid="stVerticalBlock"] {{
  gap: 0 !important;
}}
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"] {{
  gap: 0.35rem !important;
  align-items: center !important;
  border-bottom: 1px solid #e2e8f0;
  padding: 6px 10px !important;
  margin: 0 !important;
  min-height: 52px;
}}
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:first-of-type {{
  background: #f8fafc;
  min-height: 40px;
  padding: 8px 10px !important;
}}
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:not(:first-of-type):hover {{
  background: #eef5ff;
}}
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has([data-testid="stCheckbox"] input:checked) {{
  background: #eaf2ff !important;
}}
.st-key-jobs_table_wrap [data-testid="stElementContainer"] {{
  margin-bottom: 0 !important;
  padding-bottom: 0 !important;
}}
.st-key-jobs_table_wrap [data-testid="stCheckbox"] {{
  margin: 0 !important;
}}
.st-key-jobs_table_wrap [data-testid="stCheckbox"] label {{
  min-height: 24px !important;
  margin: 0 !important;
}}
.st-key-jobs_table_wrap .stButton > button {{
  height: 32px !important;
  min-height: 32px !important;
  padding: 0 12px !important;
  border-radius: 9px !important;
  font-size: 14px !important;
  width: auto !important;
}}
</style>
""",
        unsafe_allow_html=True,
    )


def inject_tasks_module_css() -> None:
    """Tasks custom interactive table styling."""
    st.markdown(
        f"""
<style id="ips-tasks-module-v3">
.ips-task-table-wrap {{
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  overflow: hidden;
  margin-bottom: 0.5rem;
}}
.ips-task-header-row {{
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  padding: 8px 10px;
  font-size: 12px;
  font-weight: 800;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  min-height: 38px;
  display: flex;
  align-items: center;
}}
.ips-task-row {{
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  padding: 6px 10px;
  min-height: 52px;
}}
.ips-task-row:hover {{
  background: #eef5ff;
}}
.ips-task-cell {{
  color: {TEXT};
  font-size: 0.8125rem;
  line-height: 1.25;
  min-width: 0;
}}
.ips-task-title {{
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
  line-height: 1.25;
  word-break: break-word;
}}
.ips-task-due {{
  white-space: nowrap;
  font-size: 0.8125rem;
}}
.ips-priority-pill {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 26px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}}
.ips-priority-high {{
  background: #fee2e2;
  color: #991b1b;
}}
.ips-priority-medium {{
  background: #ffedd5;
  color: #c2410c;
}}
.ips-priority-low {{
  background: #f1f5f9;
  color: #475569;
}}
.st-key-tasks_table_wrap [data-testid="stVerticalBlock"] {{
  gap: 0 !important;
}}
.st-key-tasks_table_wrap [data-testid="stHorizontalBlock"] {{
  gap: 0.35rem !important;
  align-items: center !important;
  border-bottom: 1px solid #e2e8f0;
  padding: 6px 10px !important;
  margin: 0 !important;
  min-height: 52px;
}}
.st-key-tasks_table_wrap [data-testid="stHorizontalBlock"]:first-of-type {{
  background: #f8fafc;
  min-height: 40px;
  padding: 8px 10px !important;
}}
.st-key-tasks_table_wrap [data-testid="stHorizontalBlock"]:not(:first-of-type):hover {{
  background: #eef5ff;
}}
.st-key-tasks_table_wrap [data-testid="stHorizontalBlock"]:has([data-testid="stCheckbox"] input:checked) {{
  background: #eaf2ff !important;
}}
.st-key-tasks_table_wrap [data-testid="stElementContainer"] {{
  margin-bottom: 0 !important;
  padding-bottom: 0 !important;
}}
.st-key-tasks_table_wrap .stButton > button {{
  height: 32px !important;
  min-height: 32px !important;
  padding: 0 12px !important;
  border-radius: 9px !important;
  font-size: 14px !important;
  width: auto !important;
}}
.st-key-tasks_table_wrap [class*="st-key-task_status_open_"] .stButton > button {{
  background: #dbeafe !important;
  color: #1d4ed8 !important;
  border: 1px solid #bfdbfe !important;
}}
.st-key-tasks_table_wrap [class*="st-key-task_status_closed_"] .stButton > button {{
  background: #f1f5f9 !important;
  color: #475569 !important;
  border: 1px solid #e2e8f0 !important;
}}
.st-key-tasks_table_wrap [data-testid="stSelectbox"] {{
  margin: 0 !important;
}}
.st-key-tasks_table_wrap [data-testid="stSelectbox"] > div {{
  min-height: 34px !important;
}}
.st-key-tasks_table_wrap [data-testid="stSelectbox"] div[data-baseweb="select"] {{
  min-height: 34px !important;
}}
.st-key-tasks_table_wrap [data-testid="stSelectbox"] div[data-baseweb="select"] > div {{
  min-height: 34px !important;
  font-size: 0.78rem !important;
}}
.st-key-tasks_table_wrap [data-testid="stCheckbox"] {{
  margin: 0 !important;
}}
.st-key-tasks_table_wrap [data-testid="stCheckbox"] label {{
  min-height: 0 !important;
  margin: 0 !important;
}}
.ips-task-view-toggle {{
  margin-bottom: 0.35rem;
}}
.ips-task-view-toggle [data-testid="stRadio"] {{
  margin: 0 !important;
}}
.ips-task-view-toggle [data-testid="stRadio"] > div {{
  gap: 0.35rem !important;
}}
.ips-task-view-toggle [data-testid="stRadio"] label {{
  background: #f8fafc !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: 999px !important;
  padding: 0.35rem 0.85rem !important;
  font-size: 0.8125rem !important;
  font-weight: 700 !important;
}}
.ips-job-tasks-view {{
  margin-bottom: 0.5rem;
}}
.ips-job-tasks-table {{
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  overflow: hidden;
  margin-top: 0.5rem;
}}
.ips-job-tasks-header-row {{
  background: #f8fafc;
  font-size: 11px;
  font-weight: 800;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 6px 8px;
  min-height: 34px;
  display: flex;
  align-items: center;
}}
.ips-job-tasks-row {{
  background: #ffffff;
  padding: 4px 8px;
  min-height: 42px;
  display: flex;
  align-items: center;
}}
.ips-job-tasks-empty {{
  margin: 0.75rem 0 0;
  color: #64748b;
  font-size: 0.875rem;
}}
.st-key-job_tasks_table_wrap [data-testid="stVerticalBlock"] {{
  gap: 0 !important;
}}
.st-key-job_tasks_table_wrap [data-testid="stHorizontalBlock"] {{
  gap: 0.3rem !important;
  align-items: center !important;
  border-bottom: 1px solid #e2e8f0;
  padding: 4px 8px !important;
  margin: 0 !important;
  min-height: 44px;
}}
.st-key-job_tasks_table_wrap [data-testid="stHorizontalBlock"]:first-of-type {{
  background: #f8fafc;
  min-height: 36px;
  padding: 6px 8px !important;
}}
.st-key-job_tasks_table_wrap [data-testid="stHorizontalBlock"]:not(:first-of-type):hover {{
  background: #f8fbff;
}}
.st-key-job_tasks_table_wrap [class*="st-key-job_task_status_open_"] .stButton > button {{
  background: #dcfce7 !important;
  color: #166534 !important;
  border: 1px solid #86efac !important;
  height: 28px !important;
  min-height: 28px !important;
  padding: 0 10px !important;
  font-size: 12px !important;
}}
.st-key-job_tasks_table_wrap [class*="st-key-job_task_status_closed_"] .stButton > button {{
  background: #fee2e2 !important;
  color: #991b1b !important;
  border: 1px solid #fca5a5 !important;
  height: 28px !important;
  min-height: 28px !important;
  padding: 0 10px !important;
  font-size: 12px !important;
}}
</style>
""",
        unsafe_allow_html=True,
    )


def inject_certifications_module_css() -> None:
    """Employee certifications custom table styling."""
    st.markdown(
        f"""
<style id="ips-certifications-module-v1">
.ips-certifications-table-wrap {{
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  overflow: hidden;
  margin-bottom: 0.5rem;
}}
.ips-certifications-header-row {{
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  padding: 8px 10px;
  font-size: 12px;
  font-weight: 800;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  min-height: 38px;
  display: flex;
  align-items: center;
}}
.ips-certifications-row {{
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  padding: 6px 10px;
  min-height: 52px;
}}
.ips-certifications-row:hover {{
  background: #eef5ff;
}}
.ips-certifications-row-selected {{
  background: #eaf2ff !important;
}}
.ips-certifications-cell {{
  color: {TEXT};
  font-size: 0.8125rem;
  line-height: 1.25;
  min-width: 0;
}}
.ips-certifications-type {{
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.25;
  word-break: break-word;
}}
.ips-certifications-muted {{
  font-size: 13px;
  color: #64748b;
}}
.ips-cert-status-pill {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 26px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}}
.ips-cert-status-active {{
  background: #dcfce7;
  color: #166534;
}}
.ips-cert-status-expiring-soon {{
  background: #fef3c7;
  color: #92400e;
}}
.ips-cert-status-expired {{
  background: #fee2e2;
  color: #991b1b;
}}
.ips-cert-status-missing {{
  background: #fee2e2;
  color: #991b1b;
}}
.ips-cert-status-not-required {{
  background: #f1f5f9;
  color: #475569;
}}
.st-key-certifications_table_wrap [data-testid="stVerticalBlock"] {{
  gap: 0 !important;
}}
.st-key-certifications_table_wrap [data-testid="stHorizontalBlock"] {{
  gap: 0.35rem !important;
  align-items: center !important;
  border-bottom: 1px solid #e2e8f0;
  padding: 6px 10px !important;
  margin: 0 !important;
  min-height: 52px;
}}
.st-key-certifications_table_wrap [data-testid="stHorizontalBlock"]:first-of-type {{
  background: #f8fafc;
  min-height: 40px;
  padding: 8px 10px !important;
}}
.st-key-certifications_table_wrap [data-testid="stHorizontalBlock"]:not(:first-of-type):hover {{
  background: #eef5ff;
}}
.st-key-certifications_table_wrap [data-testid="stHorizontalBlock"]:has([data-testid="stCheckbox"] input:checked) {{
  background: #eaf2ff !important;
}}
.st-key-certifications_table_wrap [data-testid="stElementContainer"] {{
  margin-bottom: 0 !important;
  padding-bottom: 0 !important;
}}
.st-key-certifications_table_wrap [data-testid="stCheckbox"] {{
  margin: 0 !important;
}}
.st-key-certifications_table_wrap [data-testid="stCheckbox"] label {{
  min-height: 24px !important;
  margin: 0 !important;
}}
.st-key-emp_certifications_table_wrap [data-testid="stVerticalBlock"] {{
  gap: 0 !important;
}}
.st-key-emp_certifications_table_wrap [data-testid="stHorizontalBlock"] {{
  gap: 0.35rem !important;
  align-items: center !important;
  border-bottom: 1px solid #e2e8f0;
  padding: 6px 10px !important;
  margin: 0 !important;
  min-height: 52px;
}}
.st-key-emp_certifications_table_wrap [data-testid="stHorizontalBlock"]:first-of-type {{
  background: #f8fafc;
  min-height: 40px;
  padding: 8px 10px !important;
}}
.st-key-emp_certifications_table_wrap [data-testid="stHorizontalBlock"]:not(:first-of-type):hover {{
  background: #eef5ff;
}}
.st-key-emp_certifications_table_wrap [data-testid="stHorizontalBlock"]:has([data-testid="stCheckbox"] input:checked) {{
  background: #eaf2ff !important;
}}
.st-key-emp_certifications_table_wrap [data-testid="stCheckbox"] {{
  margin: 0 !important;
}}
.st-key-emp_certifications_table_wrap [data-testid="stCheckbox"] label {{
  min-height: 24px !important;
  margin: 0 !important;
}}
.ips-cert-doc-pill {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
  white-space: nowrap;
}}
.ips-cert-doc-attached {{
  background: #e0f2fe;
  color: #0369a1;
}}
.ips-cert-doc-empty {{
  color: #94a3b8;
  font-size: 13px;
}}
.ips-attachment-card {{
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 0.75rem 0.85rem;
  margin-top: 0.35rem;
}}
.ips-attachment-file-name {{
  font-size: 0.8125rem;
  color: #475569;
  margin: 0.35rem 0 0;
}}
.ips-attachment-actions {{
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-top: 0.5rem;
}}
.ips-attachment-preview {{
  margin-top: 0.65rem;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  overflow: hidden;
  background: #f8fafc;
  max-height: 600px;
}}
.ips-attachment-preview iframe {{
  width: 100%;
  height: 560px;
  border: 0;
  background: #ffffff;
}}
.ips-attachment-preview img {{
  display: block;
  width: 100%;
  max-height: 600px;
  object-fit: contain;
}}
</style>
""",
        unsafe_allow_html=True,
    )


def inject_estimates_module_css() -> None:
    """Estimates list custom table styling."""
    st.markdown(
        f"""
<style id="ips-estimates-module-v2">
.ips-estimates-table-wrap {{
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  overflow: hidden;
  margin-bottom: 0.5rem;
}}
.ips-estimates-header-row {{
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  padding: 8px 10px;
  font-size: 12px;
  font-weight: 800;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  min-height: 38px;
  display: flex;
  align-items: center;
}}
.ips-estimates-row {{
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  padding: 6px 10px;
  min-height: 52px;
}}
.ips-estimates-row:hover {{
  background: #eef5ff;
}}
.ips-estimates-row-selected {{
  background: #eaf2ff !important;
}}
.ips-estimates-cell {{
  color: {TEXT};
  font-size: 0.8125rem;
  line-height: 1.25;
  min-width: 0;
}}
.ips-estimates-number {{
  font-size: 14px;
  font-weight: 800;
  color: #2563eb;
  line-height: 1.25;
  white-space: nowrap;
}}
.ips-estimates-title {{
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.25;
  word-break: break-word;
}}
.ips-estimates-muted {{
  font-size: 13px;
  color: #64748b;
}}
.ips-est-approve-panel {{
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 0.85rem 1rem;
  margin: 0.5rem 0 0.75rem;
}}
.st-key-estimates_table_wrap button[kind="secondary"] {{
  font-size: 0.72rem !important;
  font-weight: 700 !important;
  min-height: 28px !important;
  padding: 0.15rem 0.45rem !important;
}}
.ips-est-approve-done {{
  display: inline-flex;
  align-items: center;
  font-size: 0.72rem;
  font-weight: 700;
  color: #15803d;
  white-space: nowrap;
}}
.ips-estimate-status-pill {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 26px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}}
.ips-estimate-status-draft {{
  background: #f1f5f9;
  color: #475569;
}}
.ips-estimate-status-pending {{
  background: #fef3c7;
  color: #92400e;
}}
.ips-estimate-status-sent {{
  background: #dbeafe;
  color: #1d4ed8;
}}
.ips-estimate-status-approved {{
  background: #dcfce7;
  color: #166534;
}}
.ips-estimate-status-awarded {{
  background: #dcfce7;
  color: #166534;
}}
.ips-estimate-status-rejected {{
  background: #fee2e2;
  color: #991b1b;
}}
.ips-estimate-status-expired {{
  background: #f1f5f9;
  color: #64748b;
}}
.ips-estimate-status-cancelled {{
  background: #fee2e2;
  color: #991b1b;
}}
.st-key-estimates_table_wrap [data-testid="stVerticalBlock"] {{
  gap: 0 !important;
}}
.st-key-estimates_table_wrap [data-testid="stHorizontalBlock"] {{
  gap: 0.35rem !important;
  align-items: center !important;
  border-bottom: 1px solid #e2e8f0;
  padding: 6px 10px !important;
  margin: 0 !important;
  min-height: 52px;
}}
.st-key-estimates_table_wrap [data-testid="stHorizontalBlock"]:first-of-type {{
  background: #f8fafc;
  min-height: 40px;
  padding: 8px 10px !important;
}}
.st-key-estimates_table_wrap [data-testid="stHorizontalBlock"]:not(:first-of-type):hover {{
  background: #eef5ff;
}}
.st-key-estimates_table_wrap [data-testid="stHorizontalBlock"]:has([data-testid="stCheckbox"] input:checked) {{
  background: #eaf2ff !important;
}}
.st-key-estimates_table_wrap [data-testid="stElementContainer"] {{
  margin-bottom: 0 !important;
  padding-bottom: 0 !important;
}}
.st-key-estimates_table_wrap [data-testid="stCheckbox"] {{
  margin: 0 !important;
}}
.st-key-estimates_table_wrap [data-testid="stCheckbox"] label {{
  min-height: 24px !important;
  margin: 0 !important;
}}
.st-key-estimates_table_wrap .stButton > button {{
  height: 32px !important;
  min-height: 32px !important;
  padding: 0 12px !important;
  border-radius: 9px !important;
  font-size: 14px !important;
  width: auto !important;
}}
.ips-est-summary-card {{
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 12px 14px;
  min-height: 72px;
}}
.ips-est-summary-label {{
  font-size: 11px;
  font-weight: 700;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 4px;
}}
.ips-est-summary-value {{
  font-size: 18px;
  font-weight: 800;
  color: #0f172a;
}}
.ips-est-line-table-wrap {{
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  overflow: hidden;
  margin: 6px 0 10px;
}}
.ips-est-line-table {{
  width: 100%;
  border-collapse: collapse;
  background: #ffffff;
}}
.ips-est-li-th {{
  background: #f8fafc;
  color: #475569;
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 8px 10px;
  text-align: left;
  border-bottom: 1px solid #e2e8f0;
}}
.ips-est-li-td {{
  font-size: 12px;
  color: #0f172a;
  padding: 8px 10px;
  border-bottom: 1px solid #eef2f7;
}}
.ips-estimate-builder-actions {{
  margin: 6px 0 12px;
}}
.ips-estimate-builder-actions [data-testid="stButton"] > button {{
  min-height: 38px !important;
  max-height: 40px !important;
  padding: 0 10px !important;
  font-size: 13px !important;
  border-radius: 10px !important;
}}
.ips-estimate-add-card {{
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 12px 14px;
  margin: 8px 0 12px;
}}
.ips-estimate-compact-form [data-testid="stNumberInput"] input,
.ips-estimate-compact-form [data-testid="stTextInput"] input,
.ips-estimate-compact-form [data-testid="stSelectbox"] > div > div,
.ips-estimate-compact-form textarea {{
  min-height: 38px !important;
  background: #ffffff !important;
  border: 1px solid #dbe3ee !important;
  border-radius: 10px !important;
}}
.ips-estimate-compact-form [data-testid="stNumberInput"] > div {{
  background: transparent !important;
}}
.ips-estimate-live-total-card {{
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px 12px;
  margin-top: 4px;
}}
.ips-estimate-field-muted {{
  font-size: 11px;
  font-weight: 700;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}}
.ips-estimate-advanced-details {{
  padding-top: 4px;
}}
</style>
""",
        unsafe_allow_html=True,
    )


def inject_inventory_module_css() -> None:
    """Inventory list custom table styling."""
    st.markdown(
        f"""
<style id="ips-inventory-module-v2">
.ips-inventory-table-wrap {{
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  overflow: hidden;
  margin-bottom: 0.5rem;
}}
.ips-inventory-header-row {{
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  padding: 8px 10px;
  font-size: 12px;
  font-weight: 800;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  min-height: 38px;
  display: flex;
  align-items: center;
}}
.ips-inventory-row {{
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  padding: 6px 10px;
  min-height: 52px;
}}
.ips-inventory-row:hover {{
  background: #eef5ff;
}}
.ips-inventory-cell {{
  color: {TEXT};
  font-size: 0.8125rem;
  line-height: 1.25;
  min-width: 0;
}}
.ips-inventory-number {{
  font-size: 14px;
  font-weight: 800;
  color: #2563eb;
  line-height: 1.25;
  white-space: nowrap;
}}
.ips-inventory-sku-cell {{
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}}
.ips-inventory-sku {{
  font-size: 12px;
  font-weight: 800;
  color: #1d4ed8;
  line-height: 1.2;
  word-break: break-word;
}}
.ips-inventory-title {{
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.25;
  word-break: break-word;
}}
.ips-inventory-muted {{
  font-size: 13px;
  color: #64748b;
}}
.ips-inventory-qty {{
  text-align: right;
}}
.ips-inventory-status-pill {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 26px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}}
.ips-inventory-status-in-stock {{
  background: #dcfce7;
  color: #166534;
}}
.ips-inventory-status-low-stock {{
  background: #fef3c7;
  color: #92400e;
}}
.ips-inventory-status-out-of-stock {{
  background: #ffedd5;
  color: #c2410c;
}}
.ips-inventory-status-on-order {{
  background: #dbeafe;
  color: #1d4ed8;
}}
.ips-inventory-status-discontinued {{
  background: #f1f5f9;
  color: #475569;
}}
.st-key-inventory_table_wrap [data-testid="stVerticalBlock"] {{
  gap: 0 !important;
}}
.st-key-inventory_table_wrap [data-testid="stHorizontalBlock"] > [data-testid="column"] {{
  display: flex !important;
  align-items: center !important;
  align-self: stretch !important;
}}
.st-key-inventory_table_wrap [data-testid="stHorizontalBlock"] > [data-testid="column"] > [data-testid="stVerticalBlock"] {{
  width: 100%;
  justify-content: center !important;
}}
.st-key-inventory_table_wrap [data-testid="stMarkdownContainer"],
.st-key-inventory_table_wrap .stMarkdown,
.st-key-inventory_table_wrap .stMarkdown p {{
  margin: 0 !important;
  padding: 0 !important;
}}
.st-key-inventory_table_wrap .stMarkdown p:has(.ips-inventory-thumb-cell) {{
  line-height: 0 !important;
}}
.st-key-inventory_table_wrap [data-testid="stHorizontalBlock"] {{
  gap: 0.35rem !important;
  align-items: center !important;
  border-bottom: 1px solid #e2e8f0;
  padding: 6px 10px !important;
  margin: 0 !important;
  min-height: 62px;
}}
.st-key-inventory_table_wrap [data-testid="stHorizontalBlock"]:first-of-type {{
  background: #f8fafc;
  min-height: 40px;
  padding: 8px 10px !important;
}}
.st-key-inventory_table_wrap [data-testid="stHorizontalBlock"]:not(:first-of-type):hover {{
  background: #eef5ff;
}}
.st-key-inventory_table_wrap [data-testid="stHorizontalBlock"]:has([data-testid="stCheckbox"] input:checked) {{
  background: #eaf2ff !important;
}}
.st-key-inventory_table_wrap [data-testid="stElementContainer"] {{
  margin-top: 0 !important;
  margin-bottom: 0 !important;
  padding-top: 0 !important;
  padding-bottom: 0 !important;
}}
.st-key-inventory_table_wrap [data-testid="stCheckbox"] {{
  margin: 0 !important;
}}
.st-key-inventory_table_wrap [data-testid="stCheckbox"] label {{
  min-height: 24px !important;
  margin: 0 !important;
}}
.st-key-inventory_table_wrap [data-testid="stImage"] {{
  margin: 0 !important;
  display: flex;
  align-items: center;
  justify-content: center;
}}
.st-key-inventory_table_wrap [data-testid="stImage"] img {{
  width: 40px !important;
  height: 40px !important;
  max-width: 40px !important;
  max-height: 40px !important;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: #ffffff;
  object-fit: contain;
}}
.ips-inventory-qr-cell {{
  width: 40px;
  height: 40px;
}}
.ips-inventory-thumb-cell {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  vertical-align: middle;
  flex-shrink: 0;
}}
.ips-inventory-thumb-img {{
  display: block;
  width: 42px !important;
  height: 42px !important;
  object-fit: cover;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #ffffff;
}}
.ips-inventory-thumb-placeholder {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  background: #f8fafc;
  color: #94a3b8;
  font-size: 13px;
  font-weight: 700;
  line-height: 1;
}}
.ips-inventory-detail-image {{
  max-width: 260px;
  max-height: 220px;
  object-fit: contain;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #ffffff;
  padding: 4px;
}}
.ips-inventory-txn-table {{
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  overflow: hidden;
  margin-top: 8px;
}}
.ips-inventory-txn-head,
.ips-inventory-txn-row {{
  display: grid;
  grid-template-columns: 1.1fr 1fr 0.6fr 1.4fr 1fr 0.9fr 1.2fr;
  gap: 8px;
  padding: 8px 10px;
  font-size: 12px;
  align-items: center;
}}
.ips-inventory-txn-head {{
  background: #f8fafc;
  font-weight: 800;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  border-bottom: 1px solid #e2e8f0;
}}
.ips-inventory-txn-row {{
  border-bottom: 1px solid #eef2f7;
  color: #0f172a;
}}
.ips-inventory-txn-row:last-child {{
  border-bottom: none;
}}
.ips-job-inventory-txn-row {{
  grid-template-columns: 1fr 1.1fr 0.8fr 0.9fr 0.5fr 0.5fr 0.9fr 0.8fr 1fr;
}}
</style>
""",
        unsafe_allow_html=True,
    )


def inject_pricing_guide_module_css() -> None:
    """Pricing Guide list custom table styling (matches Inventory table)."""
    st.markdown(
        f"""
<style id="ips-pricing-guide-module-v1">
.ips-pg-table-wrap {{
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  overflow: hidden;
  margin-bottom: 0.5rem;
}}
.ips-pg-header-row {{
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  padding: 8px 10px;
  font-size: 12px;
  font-weight: 800;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  min-height: 38px;
  display: flex;
  align-items: center;
}}
.ips-pg-cell {{
  color: {TEXT};
  font-size: 0.8125rem;
  line-height: 1.25;
  min-width: 0;
}}
.ips-pg-title {{
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.25;
  word-break: break-word;
}}
.ips-pg-muted {{
  font-size: 13px;
  color: #64748b;
  word-break: break-word;
}}
.ips-pg-money {{
  text-align: right;
  white-space: nowrap;
}}
.ips-pg-status-pill {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 26px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}}
.ips-pg-status-active {{
  background: #dcfce7;
  color: #166534;
}}
.ips-pg-status-inactive {{
  background: #f1f5f9;
  color: #475569;
}}
.ips-pg-type-pill {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
  white-space: nowrap;
}}
.ips-pg-type-inventory {{ background: #dbeafe; color: #1d4ed8; }}
.ips-pg-type-material {{ background: #e2e8f0; color: #334155; }}
.ips-pg-type-labor {{ background: #ede9fe; color: #6d28d9; }}
.ips-pg-type-equipment {{ background: #ffedd5; color: #c2410c; }}
.ips-pg-type-travel {{ background: #ccfbf1; color: #0f766e; }}
.ips-pg-type-subcontractor {{ background: #fef9c3; color: #a16207; }}
.ips-pg-type-service {{ background: #dcfce7; color: #15803d; }}
.ips-pg-type-rental {{ background: #e0e7ff; color: #4338ca; }}
.ips-pg-type-consumable {{ background: #f1f5f9; color: #475569; }}
.ips-pg-type-assembly {{ background: #1e3a8a; color: #eff6ff; }}
.ips-pg-summary-grid {{
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.75rem;
  margin: 0.5rem 0 1rem;
}}
@media (max-width: 1100px) {{
  .ips-pg-summary-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
}}
.ips-pg-summary-card {{
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 0.75rem 0.9rem;
}}
.ips-pg-summary-card .lbl {{
  font-size: 11px;
  font-weight: 700;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}}
.ips-pg-summary-card .val {{
  font-size: 1.25rem;
  font-weight: 800;
  color: #0f172a;
  margin-top: 0.15rem;
}}
.st-key-pricing_guide_table_wrap [data-testid="stVerticalBlock"] {{
  gap: 0 !important;
}}
.st-key-pricing_guide_table_wrap [data-testid="stHorizontalBlock"] {{
  gap: 0.35rem !important;
  align-items: center !important;
  border-bottom: 1px solid #e2e8f0;
  padding: 6px 10px !important;
  margin: 0 !important;
  min-height: 62px;
}}
.st-key-pricing_guide_table_wrap [data-testid="stHorizontalBlock"]:first-of-type {{
  background: #f8fafc;
  min-height: 40px;
  padding: 8px 10px !important;
}}
.st-key-pricing_guide_table_wrap [data-testid="stHorizontalBlock"]:not(:first-of-type):hover {{
  background: #eef5ff;
}}
.st-key-pricing_guide_table_wrap [data-testid="stHorizontalBlock"]:has([data-testid="stCheckbox"] input:checked) {{
  background: #eaf2ff !important;
}}
.st-key-pricing_guide_table_wrap [data-testid="stElementContainer"] {{
  margin-top: 0 !important;
  margin-bottom: 0 !important;
  padding-top: 0 !important;
  padding-bottom: 0 !important;
}}
.st-key-pricing_guide_table_wrap [data-testid="stMarkdownContainer"],
.st-key-pricing_guide_table_wrap .stMarkdown,
.st-key-pricing_guide_table_wrap .stMarkdown p {{
  margin: 0 !important;
  padding: 0 !important;
}}
.st-key-pricing_guide_table_wrap [data-testid="stCheckbox"] {{
  margin: 0 !important;
}}
.st-key-pricing_guide_table_wrap [data-testid="stCheckbox"] label {{
  min-height: 24px !important;
  margin: 0 !important;
}}
</style>
""",
        unsafe_allow_html=True,
    )


def inject_inventory_qr_scan_css() -> None:
    """Mobile inventory QR scan page."""
    st.markdown(
        """
<style id="ips-inventory-qr-scan-v1">
.ips-inv-qr-item-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 12px 14px;
  margin: 8px 0 12px;
}
.ips-inv-qr-item-title {
  font-size: 1.1rem;
  font-weight: 800;
  color: #0f172a;
  margin-bottom: 4px;
}
.ips-inv-qr-item-meta {
  font-size: 0.85rem;
  color: #64748b;
}
div[data-testid="stVerticalBlock"]:has(span.ips-inv-qr-scan-scope) label {
  font-size: 1rem !important;
}
div[data-testid="stVerticalBlock"]:has(span.ips-inv-qr-scan-scope) input,
div[data-testid="stVerticalBlock"]:has(span.ips-inv-qr-scan-scope) textarea {
  min-height: 44px !important;
  font-size: 1rem !important;
  background: #ffffff !important;
  border-radius: 10px !important;
}
div[data-testid="stVerticalBlock"]:has(span.ips-inv-qr-scan-scope) button[kind="primary"] {
  min-height: 48px !important;
  font-size: 1rem !important;
  font-weight: 700 !important;
}
</style>
""",
        unsafe_allow_html=True,
    )


def inject_table_header_filter_css() -> None:
    """Compact popover filters inside custom table headers."""
    st.markdown(
        """
<style id="ips-table-header-filter-v1">
.ips-table-header-filter-wrap [data-testid="stPopover"] > button {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
  min-height: 32px !important;
  height: auto !important;
  font-size: 12px !important;
  font-weight: 800 !important;
  color: #475569 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.04em !important;
  justify-content: flex-start !important;
}
.ips-table-header-filter-active-wrap [data-testid="stPopover"] > button {
  color: #2563eb !important;
}
.ips-table-header-filter-wrap [data-testid="stPopover"] > button:hover {
  color: #1d4ed8 !important;
}
.ips-table-header-filter {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  font-weight: 800;
  color: #0f172a;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.ips-table-header-filter-active {
  color: #2563eb;
}
.ips-filter-dot {
  width: 6px;
  height: 6px;
  border-radius: 999px;
  background: #2563eb;
  display: inline-block;
}
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:first-of-type [data-testid="stPopover"],
.st-key-users_table_wrap [data-testid="stHorizontalBlock"]:first-of-type [data-testid="stPopover"],
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:first-of-type [data-testid="stPopover"],
.st-key-customers_table_wrap [data-testid="stHorizontalBlock"]:first-of-type [data-testid="stPopover"],
.st-key-estimates_table_wrap [data-testid="stHorizontalBlock"]:first-of-type [data-testid="stPopover"],
.st-key-inventory_table_wrap [data-testid="stHorizontalBlock"]:first-of-type [data-testid="stPopover"],
.st-key-pricing_guide_table_wrap [data-testid="stHorizontalBlock"]:first-of-type [data-testid="stPopover"],
.st-key-assets_table_wrap [data-testid="stHorizontalBlock"]:first-of-type [data-testid="stPopover"],
.st-key-tasks_table_wrap [data-testid="stHorizontalBlock"]:first-of-type [data-testid="stPopover"],
.st-key-company_updates_table_wrap [data-testid="stHorizontalBlock"]:first-of-type [data-testid="stPopover"],
.st-key-certifications_table_wrap [data-testid="stHorizontalBlock"]:first-of-type [data-testid="stPopover"] {
  margin: 0 !important;
}
</style>
""",
        unsafe_allow_html=True,
    )


def inject_asset_qr_scan_css() -> None:
    """Mobile asset QR scan page."""
    st.markdown(
        """
<style id="ips-asset-qr-scan-v1">
.ips-asset-scan-hero-img {
  width: 100%;
  max-width: 360px;
  max-height: 260px;
  object-fit: cover;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  display: block;
  margin: 0 auto 12px;
}
.ips-asset-scan-hero-placeholder {
  width: 100%;
  max-width: 360px;
  height: 200px;
  margin: 0 auto 12px;
  border: 1px dashed #cbd5e1;
  border-radius: 14px;
  background: #f8fafc;
  color: #94a3b8;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
}
.ips-asset-scan-title {
  font-size: 1.35rem;
  font-weight: 800;
  color: #0f172a;
  text-align: center;
  margin-bottom: 4px;
}
.ips-asset-scan-tag {
  font-size: 0.95rem;
  font-weight: 700;
  color: #2563eb;
  text-align: center;
  margin-bottom: 8px;
}
.ips-asset-scan-status {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 12px;
  border-radius: 999px;
  background: #dcfce7;
  color: #166534;
  font-size: 12px;
  font-weight: 800;
  margin: 0 auto 12px;
}
.ips-asset-scan-info {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  overflow: hidden;
  margin-top: 8px;
}
.ips-asset-scan-info-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-bottom: 1px solid #eef2f7;
  font-size: 0.875rem;
}
.ips-asset-scan-info-row:last-child {
  border-bottom: none;
}
.ips-asset-scan-info-label {
  color: #64748b;
  font-weight: 600;
}
.ips-asset-scan-info-value {
  color: #0f172a;
  font-weight: 700;
  text-align: right;
}
div[data-testid="stVerticalBlock"]:has(span.ips-asset-qr-scan-scope) label {
  font-size: 1rem !important;
}
div[data-testid="stVerticalBlock"]:has(span.ips-asset-qr-scan-scope) input,
div[data-testid="stVerticalBlock"]:has(span.ips-asset-qr-scan-scope) textarea {
  min-height: 44px !important;
  font-size: 1rem !important;
  background: #ffffff !important;
  border-radius: 10px !important;
}
div[data-testid="stVerticalBlock"]:has(span.ips-asset-qr-scan-scope) button[kind="primary"] {
  min-height: 48px !important;
  font-size: 1rem !important;
  font-weight: 700 !important;
}
</style>
""",
        unsafe_allow_html=True,
    )


def inject_assets_module_css() -> None:
    """Assets list custom table styling."""
    st.markdown(
        f"""
<style id="ips-assets-module-v2">
.ips-assets-table-wrap {{
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  overflow: hidden;
  margin-bottom: 0.5rem;
}}
.ips-assets-header-row {{
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  padding: 8px 10px;
  font-size: 12px;
  font-weight: 800;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  min-height: 38px;
  display: flex;
  align-items: center;
}}
.ips-assets-row {{
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  padding: 6px 10px;
  min-height: 52px;
}}
.ips-assets-row:hover {{
  background: #eef5ff;
}}
.ips-assets-cell {{
  color: {TEXT};
  font-size: 0.8125rem;
  line-height: 1.25;
  min-width: 0;
}}
.ips-assets-number {{
  font-size: 14px;
  font-weight: 800;
  color: #2563eb;
  line-height: 1.25;
  white-space: nowrap;
}}
.ips-assets-title {{
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.25;
  word-break: break-word;
}}
.ips-assets-muted {{
  font-size: 13px;
  color: #64748b;
  word-break: break-word;
}}
.ips-asset-status-pill {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 26px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}}
.ips-asset-status-available {{
  background: #dcfce7;
  color: #166534;
}}
.ips-asset-status-in-service {{
  background: #dcfce7;
  color: #166534;
}}
.ips-asset-status-assigned {{
  background: #dbeafe;
  color: #1d4ed8;
}}
.ips-asset-status-out-for-repair {{
  background: #ffedd5;
  color: #c2410c;
}}
.ips-asset-status-maintenance-due {{
  background: #fef3c7;
  color: #92400e;
}}
.ips-asset-status-retired {{
  background: #f1f5f9;
  color: #475569;
}}
.ips-asset-status-sold {{
  background: #f1f5f9;
  color: #64748b;
}}
.ips-asset-status-lost {{
  background: #fee2e2;
  color: #991b1b;
}}
.st-key-assets_table_wrap [data-testid="stVerticalBlock"] {{
  gap: 0 !important;
}}
.st-key-assets_table_wrap [data-testid="stHorizontalBlock"] > [data-testid="column"] {{
  display: flex !important;
  align-items: center !important;
  align-self: stretch !important;
}}
.st-key-assets_table_wrap [data-testid="stHorizontalBlock"] > [data-testid="column"] > [data-testid="stVerticalBlock"] {{
  width: 100%;
  justify-content: center !important;
}}
.st-key-assets_table_wrap [data-testid="stMarkdownContainer"],
.st-key-assets_table_wrap .stMarkdown,
.st-key-assets_table_wrap .stMarkdown p {{
  margin: 0 !important;
  padding: 0 !important;
}}
.st-key-assets_table_wrap .stMarkdown p:has(.ips-asset-thumb-cell) {{
  line-height: 0 !important;
}}
.ips-asset-thumb-cell {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  vertical-align: middle;
  flex-shrink: 0;
}}
.ips-asset-thumb-img {{
  display: block;
  width: 42px !important;
  height: 42px !important;
  object-fit: cover;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #ffffff;
}}
.ips-asset-thumb-placeholder {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  background: #f8fafc;
  color: #94a3b8;
  font-size: 13px;
  font-weight: 700;
  line-height: 1;
}}
.ips-asset-detail-image {{
  max-width: 300px;
  max-height: 240px;
  object-fit: contain;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #ffffff;
  padding: 4px;
}}
.st-key-assets_table_wrap [data-testid="stHorizontalBlock"] {{
  gap: 0.35rem !important;
  align-items: center !important;
  border-bottom: 1px solid #e2e8f0;
  padding: 6px 10px !important;
  margin: 0 !important;
  min-height: 58px;
}}
.st-key-assets_table_wrap [data-testid="stHorizontalBlock"]:first-of-type {{
  background: #f8fafc;
  min-height: 40px;
  padding: 8px 10px !important;
}}
.st-key-assets_table_wrap [data-testid="stHorizontalBlock"]:not(:first-of-type):hover {{
  background: #eef5ff;
}}
.st-key-assets_table_wrap [data-testid="stHorizontalBlock"]:has([data-testid="stCheckbox"] input:checked) {{
  background: #eaf2ff !important;
}}
.st-key-assets_table_wrap [data-testid="stElementContainer"] {{
  margin-top: 0 !important;
  margin-bottom: 0 !important;
  padding-top: 0 !important;
  padding-bottom: 0 !important;
}}
.st-key-assets_table_wrap [data-testid="stCheckbox"] {{
  margin: 0 !important;
}}
.st-key-assets_table_wrap [data-testid="stCheckbox"] label {{
  min-height: 24px !important;
  margin: 0 !important;
}}
.st-key-assets_table_wrap .stButton > button {{
  height: 32px !important;
  min-height: 32px !important;
  padding: 0 12px !important;
  border-radius: 9px !important;
  font-size: 14px !important;
  width: auto !important;
}}
</style>
""",
        unsafe_allow_html=True,
    )


def inject_timekeeping_module_css() -> None:
    """Timekeeping list custom table styling."""
    st.markdown(
        f"""
<style id="ips-timekeeping-module-v1">
.ips-timekeeping-table-wrap {{
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  overflow: hidden;
  margin-bottom: 0.5rem;
}}
.ips-timekeeping-header-row {{
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  padding: 8px 10px;
  font-size: 12px;
  font-weight: 800;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  min-height: 38px;
  display: flex;
  align-items: center;
}}
.ips-timekeeping-row {{
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  padding: 6px 10px;
  min-height: 52px;
}}
.ips-timekeeping-row:hover {{
  background: #eef5ff;
}}
.ips-timekeeping-row-selected {{
  background: #eaf2ff !important;
}}
.ips-timekeeping-cell {{
  color: {TEXT};
  font-size: 0.8125rem;
  line-height: 1.25;
  min-width: 0;
}}
.ips-timekeeping-employee {{
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.25;
  word-break: break-word;
}}
.ips-timekeeping-muted {{
  font-size: 13px;
  color: #64748b;
  word-break: break-word;
}}
.ips-timekeeping-hours {{
  font-size: 13px;
  color: #0f172a;
  text-align: right;
  font-variant-numeric: tabular-nums;
}}
.ips-timekeeping-status-pill {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 26px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}}
.ips-timekeeping-status-draft {{
  background: #f1f5f9;
  color: #475569;
}}
.ips-timekeeping-status-pending {{
  background: #fef3c7;
  color: #92400e;
}}
.ips-timekeeping-status-approved {{
  background: #dcfce7;
  color: #166534;
}}
.ips-timekeeping-status-rejected {{
  background: #fee2e2;
  color: #991b1b;
}}
.ips-time-week-range {{
  margin: 0;
  text-align: right;
  color: #0f172a;
  font-size: 0.875rem;
  font-weight: 700;
  line-height: 1.25;
}}
.ips-time-week-sub {{
  margin: 0.15rem 0 0;
  text-align: right;
  color: #64748b;
  font-size: 0.75rem;
  font-weight: 600;
}}
.ips-time-day-head {{
  color: #9ca3af;
  font-size: 0.66rem;
  font-weight: 750;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid #e5eaf2;
  padding: 0.45rem 0;
}}
.ips-time-day-row {{
  border-bottom: 1px solid #f1f5f9;
  padding: 0.22rem 0;
  color: #111827;
  font-size: 0.82rem;
}}
.st-key-timekeeping_table_wrap [data-testid="stVerticalBlock"] {{
  gap: 0 !important;
}}
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"] {{
  gap: 0.35rem !important;
  align-items: center !important;
  border-bottom: 1px solid #e2e8f0;
  padding: 6px 10px !important;
  margin: 0 !important;
  min-height: 52px;
}}
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:first-of-type {{
  background: #f8fafc;
  min-height: 40px;
  padding: 8px 10px !important;
}}
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:not(:first-of-type):hover {{
  background: #eef5ff;
}}
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has([data-testid="stCheckbox"] input:checked) {{
  background: #eaf2ff !important;
}}
.st-key-timekeeping_table_wrap [data-testid="stElementContainer"] {{
  margin-bottom: 0 !important;
  padding-bottom: 0 !important;
}}
.st-key-timekeeping_table_wrap [data-testid="stCheckbox"] {{
  margin: 0 !important;
}}
.st-key-timekeeping_table_wrap [data-testid="stCheckbox"] label {{
  min-height: 24px !important;
  margin: 0 !important;
}}
</style>
""",
        unsafe_allow_html=True,
    )


def inject_updates_module_css() -> None:
    """Company Updates list custom table styling."""
    st.markdown(
        f"""
<style id="ips-updates-module-v1">
.ips-updates-table-wrap {{
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  overflow: hidden;
  margin-bottom: 0.5rem;
}}
.ips-updates-header-row {{
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  padding: 8px 10px;
  font-size: 12px;
  font-weight: 800;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  min-height: 38px;
  display: flex;
  align-items: center;
}}
.ips-updates-row {{
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  padding: 6px 10px;
  min-height: 52px;
}}
.ips-updates-row:hover {{
  background: #eef5ff;
}}
.ips-updates-row-selected {{
  background: #eaf2ff !important;
}}
.ips-updates-cell {{
  color: {TEXT};
  font-size: 0.8125rem;
  line-height: 1.25;
  min-width: 0;
}}
.ips-updates-title {{
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.25;
  word-break: break-word;
}}
.ips-updates-muted {{
  font-size: 13px;
  color: #64748b;
  word-break: break-word;
}}
.ips-update-pill {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 26px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}}
.ips-update-category-announcement {{
  background: #dbeafe;
  color: #1d4ed8;
}}
.ips-update-category-safety-alert {{
  background: #fee2e2;
  color: #991b1b;
}}
.ips-update-category-event {{
  background: #ede9fe;
  color: #6d28d9;
}}
.ips-update-category-hr-update {{
  background: #fef3c7;
  color: #92400e;
}}
.ips-update-category-project-update {{
  background: #dcfce7;
  color: #166534;
}}
.ips-update-category-general {{
  background: #f1f5f9;
  color: #475569;
}}
.ips-update-status-published {{
  background: #dcfce7;
  color: #166534;
}}
.ips-update-status-draft {{
  background: #f1f5f9;
  color: #475569;
}}
.ips-update-status-scheduled {{
  background: #dbeafe;
  color: #1d4ed8;
}}
.ips-update-status-archived {{
  background: #e5e7eb;
  color: #374151;
}}
.ips-update-pinned {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
  background: #fef3c7;
  color: #92400e;
  margin-left: 8px;
  white-space: nowrap;
  vertical-align: middle;
}}
.st-key-updates_table_wrap [data-testid="stVerticalBlock"] {{
  gap: 0 !important;
}}
.st-key-updates_table_wrap [data-testid="stHorizontalBlock"] {{
  gap: 0.35rem !important;
  align-items: center !important;
  border-bottom: 1px solid #e2e8f0;
  padding: 6px 10px !important;
  margin: 0 !important;
  min-height: 52px;
}}
.st-key-updates_table_wrap [data-testid="stHorizontalBlock"]:first-of-type {{
  background: #f8fafc;
  min-height: 40px;
  padding: 8px 10px !important;
}}
.st-key-updates_table_wrap [data-testid="stHorizontalBlock"]:not(:first-of-type):hover {{
  background: #eef5ff;
}}
.st-key-updates_table_wrap [data-testid="stHorizontalBlock"]:has([data-testid="stCheckbox"] input:checked) {{
  background: #eaf2ff !important;
}}
.st-key-updates_table_wrap [data-testid="stElementContainer"] {{
  margin-bottom: 0 !important;
  padding-bottom: 0 !important;
}}
.st-key-updates_table_wrap [data-testid="stCheckbox"] {{
  margin: 0 !important;
}}
.st-key-updates_table_wrap [data-testid="stCheckbox"] label {{
  min-height: 24px !important;
  margin: 0 !important;
}}
</style>
""",
        unsafe_allow_html=True,
    )


def inject_unauthenticated_shell_css() -> None:
    """Login-only layout: centered card, no sidebar navigation."""
    st.markdown(
        '<script>document.body.classList.add("ips-auth-login");</script>',
        unsafe_allow_html=True,
    )


def inject_authenticated_shell_css() -> None:
    """Full app layout after login."""
    st.markdown(
        '<script>document.body.classList.remove("ips-auth-login");</script>',
        unsafe_allow_html=True,
    )


def inject_ips_dialog_styles() -> None:
    """Reusable IPS SaaS dialog / ``st.dialog`` styling (Jobs detail and future modals)."""
    st.markdown(
        f"""
<style id="ips-dialog-styles-v2">
div[data-testid="stBackdrop"] {{
  background: rgba(15, 23, 42, 0.42) !important;
  backdrop-filter: blur(3px) !important;
}}
div[data-testid="stDialog"] {{
  max-width: min(1180px, 96vw) !important;
  width: min(1180px, 96vw) !important;
}}
div[data-testid="stDialog"]:has(.ips-modal-wide),
div[data-testid="stDialog"]:has(.ips-dialog-shell) {{
  max-width: min(1180px, 96vw) !important;
  width: min(1180px, 96vw) !important;
}}
div[data-testid="stDialog"] > div,
div[data-testid="stDialog"] div[role="dialog"] {{
  background: #ffffff !important;
  border: 1px solid #d8e0ea !important;
  border-radius: 18px !important;
  box-shadow: 0 24px 64px rgba(15, 23, 42, 0.22) !important;
  overflow: hidden !important;
  padding-top: 14px !important;
}}
div[data-testid="stDialog"] [data-testid="stModalHeader"] {{
  padding-bottom: 0.15rem !important;
  margin-bottom: 0 !important;
}}
div[data-testid="stDialog"]:has(.ips-compact-detail-modal) [data-testid="stModalHeader"] h1 {{
  font-size: 0.95rem !important;
  line-height: 1.2 !important;
}}
div[data-testid="stDialog"] [data-testid="stVerticalBlock"] {{
  gap: 0.65rem !important;
}}
div[data-testid="stDialog"] h1,
div[data-testid="stDialog"] [data-testid="stModalHeader"] h1 {{
  color: {TEXT} !important;
  font-size: 1.05rem !important;
  font-weight: 700 !important;
  letter-spacing: -0.02em;
  margin: 0 !important;
  padding: 0 !important;
  border: none !important;
}}
div[data-testid="stDialog"] [data-testid="stElementContainer"]:not([class*="st-key-ips_dng_o_"]):not([class*="st-key-ips_dng_s_"]) [data-testid="stButton"] > button,
div[data-testid="stDialog"] [data-testid="stElementContainer"]:not([class*="st-key-ips_dng_o_"]):not([class*="st-key-ips_dng_s_"]) .stButton > button {{
  width: auto !important;
  min-width: 4.75rem !important;
  max-width: none !important;
  min-height: 38px !important;
  height: 38px !important;
  padding: 0 1rem !important;
  border-radius: 9px !important;
  font-size: 0.8125rem !important;
  font-weight: 600 !important;
  border: 1px solid #d8e0ea !important;
  background: #ffffff !important;
  color: {TEXT} !important;
  box-shadow: none !important;
  white-space: nowrap !important;
}}
div[data-testid="stDialog"] .stButton > button p,
div[data-testid="stDialog"] [data-testid="stButton"] > button p {{
  white-space: nowrap !important;
  margin: 0 !important;
}}
div[data-testid="stDialog"] .stButton > button[kind="primary"],
div[data-testid="stDialog"] [data-testid="stButton"] > button[data-testid="baseButton-primary"] {{
  background: {PRIMARY} !important;
  border-color: {PRIMARY} !important;
  color: #ffffff !important;
}}
div[data-testid="stDialog"] .ips-dialog-actions + div [data-testid="stHorizontalBlock"],
div[data-testid="stDialog"] [data-testid="stVerticalBlock"]:has(.ips-dialog-actions) [data-testid="stHorizontalBlock"] {{
  flex-wrap: nowrap !important;
  gap: 0.5rem !important;
  justify-content: flex-end !important;
  margin-bottom: 0.85rem !important;
}}
div[data-testid="stDialog"] .ips-dialog-actions + div [data-testid="column"],
div[data-testid="stDialog"] [data-testid="stVerticalBlock"]:has(.ips-dialog-actions) [data-testid="column"] {{
  flex: 0 0 auto !important;
  width: auto !important;
  min-width: 0 !important;
}}
div[data-testid="stDialog"] .ips-dialog-actions + div .stButton > button,
div[data-testid="stDialog"] [data-testid="stVerticalBlock"]:has(.ips-dialog-actions) .stButton > button {{
  width: auto !important;
  min-width: 4.75rem !important;
}}
div[data-testid="stDialog"] .ips-dialog-actions {{
  display: none !important;
}}
div[data-testid="stDialog"] div[data-testid="stTabs"] {{
  margin-top: 4px !important;
}}
div[data-testid="stDialog"]:has(.ips-compact-detail-modal) div[data-testid="stTabs"] {{
  margin-top: 2px !important;
}}
div[data-testid="stDialog"]:has(.ips-compact-detail-modal) [data-testid="stTabContent"] {{
  padding-top: 0.55rem !important;
}}
div[data-testid="stDialog"]:has(.ips-compact-detail-modal) [data-testid="stElementContainer"]:not([class*="st-key-ips_dng_o_"]):not([class*="st-key-ips_dng_s_"]) [data-testid="stButton"] > button,
div[data-testid="stDialog"]:has(.ips-compact-detail-modal) [data-testid="stElementContainer"]:not([class*="st-key-ips_dng_o_"]):not([class*="st-key-ips_dng_s_"]) .stButton > button {{
  height: 36px !important;
  min-height: 36px !important;
  padding: 0 16px !important;
  border-radius: 10px !important;
}}
div[data-testid="stDialog"] div[data-testid="stTabs"] [data-baseweb="tab-list"] {{
  gap: 0.15rem !important;
  border-bottom: 1px solid #d8e0ea !important;
  background: transparent !important;
}}
div[data-testid="stDialog"] div[data-testid="stTabs"] button[data-baseweb="tab"] {{
  background: transparent !important;
  border: none !important;
  border-bottom: 2px solid transparent !important;
  border-radius: 0 !important;
  color: {TEXT_MUTED} !important;
  font-size: 0.8125rem !important;
  font-weight: 500 !important;
  padding: 0.55rem 0.85rem !important;
  min-height: 2.35rem !important;
  box-shadow: none !important;
}}
div[data-testid="stDialog"] div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {{
  color: {PRIMARY} !important;
  font-weight: 600 !important;
  border-bottom-color: {PRIMARY} !important;
  background: transparent !important;
}}
div[data-testid="stDialog"] [data-testid="stTabContent"] {{
  padding-top: 0.85rem !important;
}}
div[data-testid="stDialog"] [data-testid="stRadio"] {{
  display: none !important;
}}

.ips-dialog-header {{
  margin: 0 0 0.85rem 0;
  padding: 0 0 0.85rem 0;
  border-bottom: 1px solid #e8edf3;
}}
.ips-dialog-title-row {{
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.85rem;
  flex-wrap: wrap;
}}
.ips-dialog-title {{
  font-size: 1.35rem;
  font-weight: 700;
  color: {TEXT};
  margin: 0;
  line-height: 1.25;
  letter-spacing: -0.02em;
}}
.ips-dialog-subtitle {{
  font-size: 0.875rem;
  color: {TEXT_MUTED};
  margin: 0.25rem 0 0;
  line-height: 1.45;
}}
.ips-dialog-actions {{
  margin: 0 0 0.85rem 0;
}}
.ips-dialog-meta-grid {{
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.65rem;
  margin: 0 0 0.85rem 0;
}}
@media (max-width: 900px) {{
  .ips-dialog-meta-grid {{
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }}
}}
.ips-dialog-meta-card {{
  background: #f8fafc;
  border: 1px solid #e8edf3;
  border-radius: 12px;
  padding: 0.65rem 0.75rem;
  min-height: 4.25rem;
}}
.ips-dialog-meta-label {{
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: {TEXT_MUTED};
  margin: 0 0 0.25rem 0;
}}
.ips-dialog-meta-value {{
  font-size: 0.875rem;
  font-weight: 600;
  color: {TEXT};
  line-height: 1.35;
  word-break: break-word;
}}

.ips-compact-detail-header {{
  padding: 4px 0 12px 0;
  border-bottom: 1px solid #e5eaf1;
  margin-bottom: 12px;
}}
.ips-compact-detail-main {{
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}}
.ips-compact-detail-title {{
  font-size: 24px;
  font-weight: 800;
  color: {TEXT};
  margin: 0;
  line-height: 1.15;
}}
.ips-compact-detail-subtitle {{
  font-size: 14px;
  color: {TEXT_MUTED};
  margin-top: 4px;
}}
.ips-compact-detail-actions {{
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 2px;
  min-height: 36px;
}}
div[data-testid="stDialog"]:has(.ips-compact-detail-modal) .ips-compact-detail-header [data-testid="stHorizontalBlock"] {{
  align-items: flex-start !important;
}}
div[data-testid="stDialog"]:has(.ips-compact-detail-modal) .ips-compact-detail-header [data-testid="column"]:last-child [data-testid="stHorizontalBlock"] {{
  justify-content: flex-end !important;
}}
.ips-compact-meta-grid {{
  display: grid;
  grid-template-columns: repeat(4, minmax(130px, 1fr));
  gap: 10px;
  margin: 10px 0 8px 0;
}}
@media (max-width: 900px) {{
  .ips-compact-meta-grid {{
    grid-template-columns: repeat(2, minmax(130px, 1fr));
  }}
}}
.ips-compact-meta-card {{
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 10px 12px;
  min-height: 58px;
  max-height: 70px;
  overflow: hidden;
}}
.ips-compact-meta-label {{
  font-size: 11px;
  color: {TEXT_MUTED};
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 5px;
}}
.ips-compact-meta-value {{
  font-size: 14px;
  color: {TEXT};
  font-weight: 700;
  line-height: 1.25;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}}

.ips-dialog-card {{
  background: #ffffff;
  border: 1px solid #e8edf3;
  border-radius: 14px;
  padding: 0.85rem 0.95rem;
  margin: 0 0 0.75rem 0;
}}
.ips-dialog-card-title {{
  font-size: 0.78rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: {TEXT_MUTED};
  margin: 0 0 0.65rem 0;
}}
.ips-detail-grid {{
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.55rem 1.25rem;
}}
@media (max-width: 760px) {{
  .ips-detail-grid {{
    grid-template-columns: 1fr;
  }}
}}
.ips-detail-label {{
  display: block;
  font-size: 0.72rem;
  font-weight: 600;
  color: {TEXT_MUTED};
  margin: 0 0 0.15rem 0;
}}
.ips-detail-value {{
  display: block;
  font-size: 0.875rem;
  font-weight: 600;
  color: {TEXT};
  line-height: 1.35;
}}
.ips-pill {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.18rem 0.55rem;
  border-radius: 999px;
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  border: 1px solid transparent;
  white-space: nowrap;
}}
.ips-pill-draft {{ background: #f1f5f9; color: #475569; border-color: #e2e8f0; }}
.ips-pill-active {{ background: #dcfce7; color: #166534; border-color: #bbf7d0; }}
.ips-pill-awarded {{ background: #dbeafe; color: #1e40af; border-color: #bfdbfe; }}
.ips-pill-approved {{ background: #e0e7ff; color: #3730a3; border-color: #c7d2fe; }}
.ips-pill-completed {{ background: #ecfdf5; color: #047857; border-color: #a7f3d0; }}
.ips-pill-pending {{ background: #fef3c7; color: #92400e; border-color: #fde68a; }}
.ips-pill-scheduled {{ background: #e0f2fe; color: #0369a1; border-color: #bae6fd; }}
.ips-pill-danger {{ background: #fee2e2; color: #b91c1c; border-color: #fecaca; }}
.ips-dialog-placeholder {{
  background: #f8fafc;
  border: 1px dashed #d8e0ea;
  border-radius: 12px;
  padding: 1.35rem 1rem;
  text-align: center;
  color: {TEXT_MUTED};
  font-size: 0.8125rem;
  line-height: 1.45;
}}
.ips-edit-form-card {{
  background: #ffffff;
  border: 1px solid #e8edf3;
  border-radius: 14px;
  padding: 0.85rem 0.95rem 0.25rem;
  margin: 0 0 0.75rem 0;
}}
.ips-form-section-title {{
  font-size: 0.95rem;
  font-weight: 700;
  color: {TEXT};
  margin: 0 0 0.65rem 0;
  letter-spacing: -0.01em;
}}
div[data-testid="stDialog"] .ips-edit-form-card ~ div [data-baseweb="input"],
div[data-testid="stDialog"] .ips-edit-form-card ~ div input:not([type="checkbox"]):not([type="radio"]),
div[data-testid="stDialog"] .ips-edit-form-card ~ div textarea,
div[data-testid="stDialog"] .ips-edit-form-card ~ div [data-baseweb="select"] > div,
div[data-testid="stDialog"] [data-testid="stTextInput"] input,
div[data-testid="stDialog"] [data-testid="stTextArea"] textarea,
div[data-testid="stDialog"] [data-testid="stSelectbox"] [data-baseweb="select"] > div,
div[data-testid="stDialog"] [data-testid="stDateInput"] input {{
  background: #ffffff !important;
  border: 1px solid #d8e0ea !important;
  border-radius: 10px !important;
  min-height: 40px !important;
  height: auto !important;
  font-size: 0.8125rem !important;
  color: {TEXT} !important;
  box-shadow: none !important;
}}
div[data-testid="stDialog"] [data-testid="stTextArea"] textarea {{
  min-height: 96px !important;
}}
div[data-testid="stDialog"] [data-testid="stWidgetLabel"] p,
div[data-testid="stDialog"] [data-testid="stWidgetLabel"] label {{
  font-size: 0.75rem !important;
  font-weight: 600 !important;
  color: {TEXT_MUTED} !important;
}}
div[data-testid="stDialog"] [data-testid="stSlider"] {{
  padding-top: 0.15rem !important;
}}
</style>
""",
        unsafe_allow_html=True,
    )


def inject_action_colors_css() -> None:
    """Shared destructive buttons and semantic status pill colors."""
    st.markdown(
        """
<style id="ips-action-colors-v4">
/* ----- Destructive buttons (st-key on widget wrapper) ----- */
[class*="st-key-ips_dng_o_"] [data-testid="stButton"] > button,
[class*="st-key-ips_dng_o_"] .stButton > button,
[class*="st-key-ips_dng_o_"][data-testid="stButton"] > button,
.stButton[class*="st-key-ips_dng_o_"] > button,
div[data-testid="stElementContainer"][class*="st-key-ips_dng_o_"] [data-testid="stButton"] > button,
div[data-testid="stElementContainer"][class*="st-key-ips_dng_o_"] > .stButton > button {
    background: #ffffff !important;
    color: #dc2626 !important;
    border: 1px solid #dc2626 !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    transition: all 0.15s ease;
    width: 100% !important;
    max-width: none !important;
}
[class*="st-key-ips_dng_o_"] [data-testid="stButton"] > button:hover,
[class*="st-key-ips_dng_o_"] .stButton > button:hover,
[class*="st-key-ips_dng_o_"][data-testid="stButton"] > button:hover,
.stButton[class*="st-key-ips_dng_o_"] > button:hover,
div[data-testid="stElementContainer"][class*="st-key-ips_dng_o_"] [data-testid="stButton"] > button:hover {
    background: #fee2e2 !important;
    color: #b91c1c !important;
    border-color: #b91c1c !important;
}
[class*="st-key-ips_dng_o_"] [data-testid="stButton"] > button:disabled,
[class*="st-key-ips_dng_o_"] .stButton > button:disabled,
[class*="st-key-ips_dng_o_"][data-testid="stButton"] > button:disabled {
    opacity: 0.55 !important;
    cursor: not-allowed !important;
}

[class*="st-key-ips_dng_s_"] [data-testid="stButton"] > button,
[class*="st-key-ips_dng_s_"] .stButton > button,
[class*="st-key-ips_dng_s_"][data-testid="stButton"] > button,
.stButton[class*="st-key-ips_dng_s_"] > button,
div[data-testid="stElementContainer"][class*="st-key-ips_dng_s_"] [data-testid="stButton"] > button,
div[data-testid="stElementContainer"][class*="st-key-ips_dng_s_"] > .stButton > button {
    background: #dc2626 !important;
    color: #ffffff !important;
    border: 1px solid #dc2626 !important;
    border-radius: 10px !important;
    font-weight: 800 !important;
    transition: all 0.15s ease;
    width: 100% !important;
    max-width: none !important;
}
[class*="st-key-ips_dng_s_"] [data-testid="stButton"] > button:hover,
[class*="st-key-ips_dng_s_"] .stButton > button:hover,
[class*="st-key-ips_dng_s_"][data-testid="stButton"] > button:hover,
.stButton[class*="st-key-ips_dng_s_"] > button:hover,
div[data-testid="stElementContainer"][class*="st-key-ips_dng_s_"] [data-testid="stButton"] > button:hover {
    background: #b91c1c !important;
    border-color: #b91c1c !important;
    color: #ffffff !important;
}

/* Legacy container-key wrappers */
[class*="st-key-ips_danger_outline_"] [data-testid="stButton"] > button,
[class*="st-key-ips_danger_solid_"] [data-testid="stButton"] > button {
    background: #ffffff !important;
    color: #dc2626 !important;
    border: 1px solid #dc2626 !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
}
[class*="st-key-ips_danger_solid_"] [data-testid="stButton"] > button {
    background: #dc2626 !important;
    color: #ffffff !important;
    font-weight: 800 !important;
}

/* st.dialog — full-width red destructive buttons */
div[data-testid="stDialog"] [class*="st-key-ips_dng_o_"] [data-testid="stButton"] > button,
div[data-testid="stDialog"] [class*="st-key-ips_dng_o_"] .stButton > button,
div[data-testid="stDialog"] [class*="st-key-ips_dng_o_"][data-testid="stButton"] > button,
div[data-testid="stDialog"] .stButton[class*="st-key-ips_dng_o_"] > button,
div[data-testid="stDialog"] div[data-testid="stElementContainer"][class*="st-key-ips_dng_o_"] [data-testid="stButton"] > button,
div[data-testid="stDialog"] div[data-testid="stElementContainer"][class*="st-key-ips_dng_o_"] > .stButton > button {
    background: #ffffff !important;
    color: #dc2626 !important;
    border: 1px solid #dc2626 !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    width: 100% !important;
    max-width: none !important;
    min-width: 0 !important;
    height: 38px !important;
    min-height: 38px !important;
}
div[data-testid="stDialog"] [class*="st-key-ips_dng_o_"] [data-testid="stButton"] > button:hover,
div[data-testid="stDialog"] [class*="st-key-ips_dng_o_"] .stButton > button:hover,
div[data-testid="stDialog"] [class*="st-key-ips_dng_o_"][data-testid="stButton"] > button:hover,
div[data-testid="stDialog"] .stButton[class*="st-key-ips_dng_o_"] > button:hover {
    background: #fee2e2 !important;
    color: #b91c1c !important;
    border-color: #b91c1c !important;
}
div[data-testid="stDialog"] [class*="st-key-ips_dng_s_"] [data-testid="stButton"] > button,
div[data-testid="stDialog"] [class*="st-key-ips_dng_s_"] .stButton > button,
div[data-testid="stDialog"] [class*="st-key-ips_dng_s_"][data-testid="stButton"] > button,
div[data-testid="stDialog"] .stButton[class*="st-key-ips_dng_s_"] > button,
div[data-testid="stDialog"] div[data-testid="stElementContainer"][class*="st-key-ips_dng_s_"] [data-testid="stButton"] > button,
div[data-testid="stDialog"] div[data-testid="stElementContainer"][class*="st-key-ips_dng_s_"] > .stButton > button {
    background: #dc2626 !important;
    color: #ffffff !important;
    border: 1px solid #dc2626 !important;
    border-radius: 10px !important;
    font-weight: 800 !important;
    width: 100% !important;
    max-width: none !important;
    min-width: 0 !important;
    height: 38px !important;
    min-height: 38px !important;
}
div[data-testid="stDialog"] [class*="st-key-ips_dng_s_"] [data-testid="stButton"] > button:hover,
div[data-testid="stDialog"] [class*="st-key-ips_dng_s_"] .stButton > button:hover,
div[data-testid="stDialog"] [class*="st-key-ips_dng_s_"][data-testid="stButton"] > button:hover,
div[data-testid="stDialog"] .stButton[class*="st-key-ips_dng_s_"] > button:hover {
    background: #b91c1c !important;
    border-color: #b91c1c !important;
    color: #ffffff !important;
}

/* Danger zone card in modals */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-modal-danger-zone-marker) {
    border-color: #fecaca !important;
    background: #fffbfb !important;
    border-radius: 12px !important;
    padding: 0.65rem 0.75rem 0.75rem !important;
    margin: 0.65rem 0 0.75rem !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-modal-danger-zone-marker) [data-testid="stVerticalBlock"] {
    gap: 0.45rem !important;
}
.ips-modal-danger-zone-marker {
    display: none !important;
}
.ips-modal-danger-zone-title {
    margin: 0 0 0.55rem 0;
    font-size: 0.72rem;
    font-weight: 800;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: #991b1b;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-modal-danger-zone-marker) [class*="st-key-ips_dng_o_"] [data-testid="stElementContainer"],
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-modal-danger-zone-marker) [class*="st-key-ips_dng_o_"],
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-modal-danger-zone-marker) div[data-testid="stElementContainer"][class*="st-key-ips_dng_o_"],
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-modal-danger-zone-marker) div[data-testid="stElementContainer"][class*="st-key-ips_dng_s_"] {
    margin-bottom: 0 !important;
    width: 100% !important;
    max-width: none !important;
}
div[data-testid="stDialog"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-modal-danger-zone-marker) [data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"] {
    width: 100% !important;
    max-width: none !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-modal-danger-zone-marker) hr {
    display: none !important;
}

/* ----- Semantic status pills ----- */
.ips-status-warning {
    background: #fef3c7;
    color: #92400e;
    border-color: #fde68a;
}
.ips-status-attention {
    background: #fed7aa;
    color: #9a3412;
    border-color: #fdba74;
}
.ips-status-success {
    background: #dcfce7;
    color: #166534;
    border-color: #bbf7d0;
}
.ips-status-neutral {
    background: #f1f5f9;
    color: #475569;
    border-color: #e2e8f0;
}
.ips-status-primary {
    background: #dbeafe;
    color: #1d4ed8;
    border-color: #bfdbfe;
}
.ips-status-danger {
    background: #fee2e2;
    color: #dc2626;
    border-color: #fecaca;
}

/* Kit / tool trailer item statuses */
.ips-kit-status-pill {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.12rem 0.45rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 600;
    white-space: nowrap;
    border: 1px solid transparent;
}
.ips-kit-status-present { background: #dcfce7; color: #166534; border-color: #bbf7d0; }
.ips-kit-status-missing { background: #fee2e2; color: #b91c1c; border-color: #fecaca; }
.ips-kit-status-damaged { background: #ffedd5; color: #c2410c; border-color: #fed7aa; }
.ips-kit-status-checked-out { background: #dbeafe; color: #1d4ed8; border-color: #bfdbfe; }
.ips-kit-status-needs-repair,
.ips-kit-status-needs-replacement { background: #fef3c7; color: #92400e; border-color: #fde68a; }
.ips-kit-status-retired { background: #f1f5f9; color: #475569; border-color: #e2e8f0; }
.ips-kit-status-neutral { background: #f1f5f9; color: #475569; border-color: #e2e8f0; }

/* Documents restricted access */
.ips-doc-restricted-pill {
    display: inline-flex;
    align-items: center;
    padding: 0.12rem 0.5rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 700;
    background: #fed7aa;
    color: #9a3412;
    border: 1px solid #fdba74;
}
</style>
""",
        unsafe_allow_html=True,
    )


def inject_global_css() -> None:
    """Inject global IPS SaaS styles on every render."""
    st.markdown(
        f"""
<style id="ips-global-styles-v4">
:root {{
  --ips-bg: {APP_BG};
  --ips-sidebar: {SIDEBAR_BG};
  --ips-card: {CARD_BG};
  --ips-border: {BORDER};
  --ips-primary: {PRIMARY};
  --ips-text: {TEXT};
  --ips-muted: {TEXT_MUTED};
  --ips-selected-bg: {SELECTED_BG};
  --ips-selected-border: {SELECTED_BORDER};
}}

html, body, .stApp {{
  background: {APP_BG} !important;
}}
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
section[data-testid="stMain"] > div,
.block-container {{
  background: {APP_BG} !important;
}}
section[data-testid="stMain"] .block-container {{
  max-width: 1680px !important;
  padding-top: 0.5rem !important;
  padding-bottom: 1rem !important;
}}

/* Sidebar */
section[data-testid="stSidebar"],
[data-testid="stSidebar"] {{
  background: {SIDEBAR_BG} !important;
  border-right: 1px solid {BORDER} !important;
}}
section[data-testid="stSidebar"] .block-container {{
  padding-top: 0.75rem !important;
}}
.ips-sidebar-logo {{
  padding: 0.5rem 0.75rem 1rem;
  border-bottom: 1px solid {BORDER};
  margin-bottom: 0.5rem;
}}
.ips-sidebar-logo img {{
  max-height: 48px;
  width: auto;
}}
.ips-nav-item {{
  display: flex;
  align-items: center;
  gap: 0.55rem;
  padding: 0.45rem 0.75rem;
  margin: 0.1rem 0.5rem;
  border-radius: 8px;
  color: {TEXT};
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  text-decoration: none;
}}
.ips-nav-item:hover {{
  background: #f1f5f9;
}}
.ips-nav-item.active {{
  background: {SELECTED_BG};
  color: {PRIMARY};
  font-weight: 600;
  border-left: 3px solid {PRIMARY};
  margin-left: 0.35rem;
  padding-left: 0.55rem;
}}
.ips-sidebar-user {{
  margin-top: auto;
  padding: 0.75rem;
  border-top: 1px solid {BORDER};
  font-size: 0.8rem;
  color: {TEXT_MUTED};
}}

/* Cards */
.ips-card {{
  background: {CARD_BG};
  border: 1px solid {BORDER};
  border-radius: 12px;
  padding: 0.85rem 1rem;
  margin-bottom: 0.65rem;
  box-shadow: 0 1px 2px rgba(15,23,42,0.04);
}}
.ips-metric-card {{
  background: {CARD_BG};
  border: 1px solid {BORDER};
  border-radius: 12px;
  padding: 0.75rem 0.9rem;
  min-height: 4.5rem;
}}
.ips-metric-label {{
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: {TEXT_MUTED};
  margin: 0;
}}
.ips-metric-value {{
  font-size: 1.35rem;
  font-weight: 700;
  color: {TEXT};
  margin: 0.15rem 0 0;
  line-height: 1.2;
}}

/* Page header */
.ips-page-header {{
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.75rem;
}}
.ips-page-title {{
  font-size: 1.35rem;
  font-weight: 700;
  color: {TEXT};
  margin: 0;
  letter-spacing: -0.02em;
}}
.ips-page-subtitle {{
  font-size: 0.8125rem;
  color: {TEXT_MUTED};
  margin: 0.2rem 0 0;
}}

/* Filter bar */
.ips-filter-bar {{
  background: {CARD_BG};
  border: 1px solid {BORDER};
  border-radius: 12px;
  padding: 0.65rem 0.75rem;
  margin-bottom: 0.65rem;
}}

/* Status pills */
.ips-status-pill {{
  display: inline-block;
  padding: 0.15rem 0.55rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 600;
  border: 1px solid transparent;
}}
.ips-status-active {{ background:#dcfce7; color:#166534; border-color:#bbf7d0; }}
.ips-status-pending {{ background:#ffedd5; color:#c2410c; border-color:#fed7aa; }}
.ips-status-draft {{ background:#f1f5f9; color:#475569; border-color:#e2e8f0; }}
.ips-status-sent {{ background:#dbeafe; color:#1d4ed8; border-color:#bfdbfe; }}
.ips-status-danger {{ background:#fee2e2; color:#dc2626; border-color:#fecaca; }}
.ips-status-warning {{ background:#fef3c7; color:#92400e; border-color:#fde68a; }}
.ips-status-attention {{ background:#fed7aa; color:#9a3412; border-color:#fdba74; }}
.ips-status-success {{ background:#dcfce7; color:#166534; border-color:#bbf7d0; }}
.ips-status-neutral {{ background:#f1f5f9; color:#475569; border-color:#e2e8f0; }}
.ips-status-primary {{ background:#dbeafe; color:#1d4ed8; border-color:#bfdbfe; }}

/* Data table — stable grid (survives Streamlit reruns) */
.ips-data-table-wrap {{
  background: {CARD_BG};
  border: 1px solid {BORDER};
  border-radius: 12px;
  overflow: hidden;
  margin-bottom: 0.65rem;
  width: 100%;
}}
.ips-data-table-scroll {{
  overflow-x: auto;
  width: 100%;
}}
.ips-data-table-stable .ips-data-table-header,
.ips-data-table-stable .ips-data-row {{
  display: grid !important;
  align-items: center;
  column-gap: 12px;
  padding: 0.45rem 0.75rem;
  font-size: 0.8125rem;
  width: 100%;
  min-width: 48rem;
  box-sizing: border-box;
}}
.ips-data-table-header,
.ips-data-row {{
  display: grid;
  align-items: center;
  column-gap: 12px;
  padding: 0.45rem 0.75rem;
  font-size: 0.8125rem;
}}
.ips-data-table-header {{
  background: #fafbfc;
  border-bottom: 1px solid {BORDER};
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: {TEXT_MUTED};
}}
.ips-data-row {{
  border-bottom: 1px solid #f1f5f9;
  cursor: pointer;
  transition: background 0.12s;
}}
.ips-data-row:hover {{
  background: #eef5ff;
}}
.ips-data-row.selected {{
  background: #eef5ff;
  border-left: 4px solid #2563eb;
  padding-left: calc(0.75rem - 4px);
}}

/* Overlay-button rows: HTML row + invisible Streamlit button per row host */
section[data-testid="stMain"]
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-clean-table)
div[data-testid="stVerticalBlock"]:has(.ips-clean-row-wrap) .ips-data-row {{
  display: grid !important;
  align-items: center;
  min-height: 2.75rem;
  width: 100%;
  min-width: 48rem;
  box-sizing: border-box;
  border-bottom: 1px solid #f1f5f9;
  background: #ffffff;
  cursor: pointer;
}}
section[data-testid="stMain"]
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-clean-table)
div[data-testid="stVerticalBlock"]:has(.ips-clean-row-wrap) .ips-data-cell {{
  overflow: hidden;
  text-overflow: ellipsis;
}}

/* Detail panel */
.ips-detail-panel {{
  background: {CARD_BG};
  border: 1px solid {BORDER};
  border-left: 3px solid {PRIMARY};
  border-radius: 12px;
  padding: 0.85rem 1rem;
  margin: 0.5rem 0 0.75rem;
}}
.ips-detail-header {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.65rem;
  flex-wrap: wrap;
}}
.ips-detail-title {{
  font-size: 1.05rem;
  font-weight: 700;
  margin: 0;
  color: {TEXT};
}}

/* Links */
a.ips-link, .ips-data-row a {{
  color: {PRIMARY} !important;
  text-decoration: underline !important;
}}

/* Compact Streamlit controls */
section[data-testid="stMain"] .stButton > button,
section[data-testid="stMain"] [data-testid="stButton"] > button {{
  border-radius: 8px !important;
  font-size: 0.8125rem !important;
  font-weight: 600 !important;
  min-height: 2.1rem !important;
  padding: 0.25rem 0.75rem !important;
  border: 1px solid {BORDER} !important;
  background: #fff !important;
  color: {TEXT} !important;
  white-space: nowrap !important;
}}
section[data-testid="stMain"] .stButton > button p,
section[data-testid="stMain"] [data-testid="stButton"] > button p,
section[data-testid="stMain"] .stButton > button span,
section[data-testid="stMain"] [data-testid="stButton"] > button span {{
  white-space: nowrap !important;
}}
section[data-testid="stMain"] .stButton > button[kind="primary"],
section[data-testid="stMain"] .stButton > button[data-testid="baseButton-primary"] {{
  background: {PRIMARY} !important;
  border-color: {PRIMARY} !important;
  color: #fff !important;
}}
section[data-testid="stMain"] .stButton > button:hover {{
  border-color: #cbd5e1 !important;
}}
section[data-testid="stMain"] input,
section[data-testid="stMain"] textarea,
section[data-testid="stMain"] [data-baseweb="select"] > div {{
  border-radius: 8px !important;
  border-color: {BORDER} !important;
  min-height: 2.1rem !important;
  font-size: 0.8125rem !important;
}}

/* Hide legacy Select buttons (removed from list tables) */
.ips-row-select-btn,
.ips-click-bridge {{
  display: none !important;
  height: 0 !important;
  overflow: hidden !important;
}}

/* Native selectable list tables — visible checkbox + clean white grid */
section[data-testid="stMain"]:has(.ips-selectable-table) [data-testid="stDataFrame"],
section[data-testid="stMain"]:has(.ips-native-click-table) [data-testid="stDataFrame"] {{
  border: 1px solid #e2e8f0 !important;
  border-radius: 12px !important;
  overflow: hidden !important;
  background: #ffffff !important;
}}
section[data-testid="stMain"]:has(.ips-selectable-table) [data-testid="stDataFrame"] [role="columnheader"],
section[data-testid="stMain"]:has(.ips-native-click-table) [data-testid="stDataFrame"] [role="columnheader"] {{
  background: #f8fafc !important;
  color: {TEXT_MUTED} !important;
  border-bottom: 1px solid #e2e8f0 !important;
  font-size: 0.68rem !important;
  font-weight: 700 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.04em !important;
}}
section[data-testid="stMain"]:has(.ips-selectable-table) [data-testid="stDataFrame"] [role="gridcell"],
section[data-testid="stMain"]:has(.ips-native-click-table) [data-testid="stDataFrame"] [role="gridcell"] {{
  background: #ffffff !important;
  color: {TEXT} !important;
  border-color: #e2e8f0 !important;
}}
section[data-testid="stMain"]:has(.ips-selectable-table) [data-testid="stDataFrame"] [role="grid"],
section[data-testid="stMain"]:has(.ips-native-click-table) [data-testid="stDataFrame"] [role="grid"] {{
  cursor: pointer;
}}
section[data-testid="stMain"]:has(.ips-selectable-table) [data-testid="stDataFrame"] [role="row"]:hover [role="gridcell"],
section[data-testid="stMain"]:has(.ips-native-click-table) [data-testid="stDataFrame"] [role="row"]:hover [role="gridcell"] {{
  background-color: #eef5ff !important;
}}
section[data-testid="stMain"]:has(.ips-selectable-table) [data-testid="stDataFrame"] [role="row"][aria-selected="true"] [role="gridcell"],
section[data-testid="stMain"]:has(.ips-native-click-table) [data-testid="stDataFrame"] [role="row"][aria-selected="true"] [role="gridcell"],
section[data-testid="stMain"]:has(.ips-selectable-table) [data-testid="stDataFrame"] [data-testid="stTable"] [aria-selected="true"],
section[data-testid="stMain"]:has(.ips-native-click-table) [data-testid="stDataFrame"] [data-testid="stTable"] [aria-selected="true"] {{
  background-color: #eaf2ff !important;
}}
section[data-testid="stMain"]:has(.ips-selectable-table) [data-testid="stDataFrame"] [data-testid="stCheckbox"],
section[data-testid="stMain"]:has(.ips-native-click-table) [data-testid="stDataFrame"] [data-testid="stCheckbox"] {{
  opacity: 1 !important;
  width: auto !important;
  min-width: 1.25rem !important;
  max-width: none !important;
  overflow: visible !important;
  pointer-events: auto !important;
}}

/* Legacy non-selectable dataframe containers */
.ips-data-table-nested [data-testid="stDataFrame"],
.ips-data-table-html [data-testid="stDataFrame"] {{
  border: 1px solid {BORDER} !important;
  border-radius: 12px !important;
}}
.ips-data-table-nested [data-testid="stCheckbox"],
.ips-data-table-html [data-testid="stCheckbox"] {{
  display: none !important;
}}
.ips-data-table-nested .ips-data-row {{
  cursor: default;
}}

/* Modal dialog — legacy aliases + dialog shell hooks */
.ips-modal-header {{
  margin-bottom: 0.5rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid {BORDER};
}}
.ips-modal-fallback {{
  background: {CARD_BG};
  border: 1px solid {BORDER};
  border-radius: 12px;
  padding: 1rem 1.1rem;
  margin-top: 0.75rem;
  box-shadow: 0 8px 32px rgba(15, 23, 42, 0.12);
}}
div[data-testid="stDialog"] .ips-detail-title {{
  font-size: 1.15rem;
  font-weight: 700;
  color: {TEXT};
  margin: 0;
}}

/* Login — hide app chrome until authenticated */
body.ips-auth-login section[data-testid="stSidebar"],
body.ips-auth-login [data-testid="stSidebarCollapsedControl"] {{
  display: none !important;
  visibility: hidden !important;
  width: 0 !important;
  min-width: 0 !important;
}}
body.ips-auth-login section[data-testid="stMain"] .block-container {{
  max-width: 440px !important;
  margin-left: auto !important;
  margin-right: auto !important;
  padding-top: 1.5rem !important;
}}
.ips-login-wrap {{
  max-width: 420px;
  margin: 0 auto;
  padding: 1.5rem;
  background: #fff;
  border: 1px solid {BORDER};
  border-radius: 14px;
  box-shadow: 0 4px 24px rgba(15, 23, 42, 0.06);
}}

/* Module list pages (Customers, Jobs, …) */
.ips-module-page {{
  width: 100%;
}}
.ips-module-page .ips-page-header {{
  margin-bottom: 0.85rem;
}}
.ips-form-card {{
  margin-bottom: 0.75rem;
}}

/* Empty state */
.ips-empty-state {{
  text-align: center;
  padding: 2.5rem 1rem;
  color: {TEXT_MUTED};
}}
.ips-empty-state h3 {{
  color: {TEXT};
  font-size: 1rem;
  margin: 0.5rem 0 0.25rem;
}}

/* Tabs */
.ips-tab-bar {{
  border-bottom: 1px solid {BORDER};
  margin-bottom: 0.75rem;
  display: flex;
  gap: 0.25rem;
  flex-wrap: wrap;
}}

/* Field mode */
.ips-field-mode .block-container {{
  max-width: 100% !important;
}}

/* Module layout */
.ips-kpi-grid {{
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0.65rem;
  margin-bottom: 0.75rem;
}}
@media (max-width: 1200px) {{
  .ips-kpi-grid {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
}}
@media (max-width: 768px) {{
  .ips-kpi-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
}}
.ips-kpi-card {{
  background: {CARD_BG};
  border: 1px solid {BORDER};
  border-radius: 12px;
  padding: 0.75rem 0.85rem;
  min-height: 5.5rem;
}}
.ips-kpi-top {{
  display: flex;
  gap: 0.55rem;
  align-items: flex-start;
}}
.ips-kpi-icon {{
  width: 2.1rem;
  height: 2.1rem;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
  flex-shrink: 0;
}}
.ips-kpi-label {{
  font-size: 0.72rem;
  color: {TEXT_MUTED};
  margin: 0;
  font-weight: 600;
}}
.ips-kpi-value {{
  font-size: 1.15rem;
  font-weight: 700;
  color: {TEXT};
  margin: 0.1rem 0 0;
  line-height: 1.2;
}}
.ips-kpi-trend {{
  font-size: 0.72rem;
  margin: 0.35rem 0 0;
}}
.ips-kpi-trend.up {{ color: #16a34a; }}
.ips-kpi-trend.down {{ color: #dc2626; }}
.ips-kpi-trend.flat {{ color: {TEXT_MUTED}; }}

.ips-panel-card {{
  background: {CARD_BG};
  border: 1px solid {BORDER};
  border-radius: 12px;
  padding: 0.75rem 0.85rem;
  margin-bottom: 0.65rem;
  min-height: 12rem;
}}
.ips-panel-title {{
  font-size: 0.9rem;
  font-weight: 700;
  color: {TEXT};
  margin: 0 0 0.55rem;
}}
.ips-chart-legend {{
  display: flex;
  gap: 1rem;
  font-size: 0.72rem;
  color: {TEXT_MUTED};
  margin-bottom: 0.35rem;
}}
.ips-legend-dot {{
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-right: 0.35rem;
  vertical-align: middle;
}}
.ips-activity-item {{
  display: flex;
  gap: 0.55rem;
  padding: 0.45rem 0;
  border-bottom: 1px solid #f1f5f9;
  font-size: 0.8125rem;
}}
.ips-activity-item:last-child {{ border-bottom: none; }}
.ips-activity-icon {{
  width: 1.75rem;
  height: 1.75rem;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.85rem;
  flex-shrink: 0;
}}
.ips-activity-meta {{
  font-size: 0.72rem;
  color: {TEXT_MUTED};
  margin-top: 0.1rem;
}}
.ips-deadline-row {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.4rem 0;
  border-bottom: 1px solid #f1f5f9;
  font-size: 0.8125rem;
}}
.ips-deadline-badge {{
  font-size: 0.68rem;
  font-weight: 700;
  padding: 0.12rem 0.45rem;
  border-radius: 999px;
}}
.ips-deadline-badge.danger {{ background: #fee2e2; color: #dc2626; }}
.ips-deadline-badge.warn {{ background: #ffedd5; color: #c2410c; }}
.ips-deadline-badge.ok {{ background: #dcfce7; color: #166534; }}

.ips-quick-actions-card {{
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 14px 16px 16px 16px;
  margin-bottom: 0.65rem;
}}
.ips-quick-actions-header {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}}
.ips-quick-actions-title {{
  font-size: 16px;
  font-weight: 800;
  color: #0f172a;
  margin: 0;
}}
.ips-quick-actions-grid {{
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}}
.ips-quick-action-tile {{
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 52px;
  padding: 10px 12px;
  background: #ffffff;
  border: 1px solid #dbe3ee;
  border-radius: 12px;
  color: #0f172a;
  font-weight: 600;
  text-align: center;
  transition: all 0.15s ease;
}}
.ips-quick-action-tile:hover {{
  background: #f8fbff;
  border-color: #bfd3f2;
}}
.ips-quick-action-icon {{
  font-size: 16px;
  line-height: 1;
}}
.ips-quick-action-label {{
  font-size: 14px;
  line-height: 1.2;
}}
.st-key-dashboard_quick_actions {{
  background: #ffffff !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: 14px !important;
  padding: 14px 16px 16px 16px !important;
  margin-bottom: 0.65rem !important;
}}
.st-key-dashboard_quick_actions [data-testid="stVerticalBlock"] {{
  gap: 12px !important;
}}
.st-key-dashboard_quick_actions [data-testid="stHorizontalBlock"] {{
  gap: 12px !important;
  align-items: stretch !important;
}}
.st-key-dashboard_quick_actions [data-testid="stElementContainer"] {{
  margin-bottom: 0 !important;
}}
.st-key-dashboard_quick_actions .stButton > button {{
  min-height: 52px !important;
  height: auto !important;
  padding: 10px 12px !important;
  background: #ffffff !important;
  border: 1px solid #dbe3ee !important;
  border-radius: 12px !important;
  color: #0f172a !important;
  font-weight: 600 !important;
  font-size: 14px !important;
  line-height: 1.2 !important;
  box-shadow: none !important;
  transition: background 0.15s ease, border-color 0.15s ease !important;
}}
.st-key-dashboard_quick_actions .stButton > button:hover {{
  background: #f8fbff !important;
  border-color: #bfd3f2 !important;
  color: #0f172a !important;
}}
.st-key-dashboard_quick_actions .stButton > button p {{
  white-space: pre-line !important;
  line-height: 1.25 !important;
  font-size: 14px !important;
  font-weight: 600 !important;
}}
@media (max-width: 1200px) {{
  .ips-quick-actions-grid {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
}}
@media (max-width: 900px) {{
  .ips-quick-actions-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
}}
@media (max-width: 560px) {{
  .ips-quick-actions-grid {{ grid-template-columns: 1fr; }}
}}
.ips-quick-actions {{
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.5rem;
}}
.ips-quick-action {{
  background: #fff;
  border: 1px solid {BORDER};
  border-radius: 10px;
  padding: 0.55rem 0.4rem;
  text-align: center;
  font-size: 0.75rem;
  font-weight: 600;
  color: {TEXT};
}}
.ips-progress-bar {{
  height: 6px;
  background: #e2e8f0;
  border-radius: 999px;
  overflow: hidden;
  margin-top: 0.25rem;
}}
.ips-progress-fill {{
  height: 100%;
  background: {PRIMARY};
  border-radius: 999px;
}}
.ips-donut-legend {{
  font-size: 0.75rem;
  color: {TEXT};
  padding: 0.25rem 0;
  border-bottom: 1px solid #f1f5f9;
}}
.ips-donut-legend span {{
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
}}
.ips-detail-meta-row {{
  display: flex;
  flex-wrap: wrap;
  gap: 1.25rem;
  font-size: 0.8125rem;
  margin: 0.35rem 0 0.65rem;
}}
.ips-detail-meta-row span {{
  color: {TEXT_MUTED};
}}
.ips-detail-meta-row strong {{
  color: {TEXT};
  display: block;
  font-size: 0.875rem;
}}
.ips-info-grid {{
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.5rem 1rem;
  font-size: 0.8125rem;
}}
.ips-info-grid dt {{
  color: {TEXT_MUTED};
  margin: 0;
  font-weight: 500;
}}
.ips-info-grid dd {{
  margin: 0.1rem 0 0.5rem;
  color: {TEXT};
  font-weight: 600;
}}
.ips-module-placeholder {{
  text-align: center;
  padding: 3rem 1rem;
  color: {TEXT_MUTED};
}}
.ips-summary-card {{
  background: {CARD_BG};
  border: 1px solid {BORDER};
  border-radius: 12px;
  padding: 0.85rem 1rem;
  margin-bottom: 0.65rem;
}}
.ips-summary-grid {{
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 0.75rem 1rem;
  font-size: 0.8125rem;
}}
@media (max-width: 1100px) {{
  .ips-summary-grid {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
}}
.ips-summary-grid .lbl {{
  color: {TEXT_MUTED};
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  margin: 0;
}}
.ips-summary-grid .val {{
  color: {TEXT};
  font-weight: 600;
  margin: 0.15rem 0 0;
}}
.ips-summary-grid .val-lg {{
  font-size: 1.25rem;
  font-weight: 700;
  color: {TEXT};
}}
.ips-side-panel {{
  background: {CARD_BG};
  border: 1px solid {BORDER};
  border-radius: 12px;
  padding: 0.75rem 0.85rem;
}}
.ips-side-panel h4 {{
  margin: 0 0 0.5rem;
  font-size: 0.875rem;
  font-weight: 700;
}}
.ips-side-line {{
  display: flex;
  justify-content: space-between;
  font-size: 0.8125rem;
  padding: 0.3rem 0;
  border-bottom: 1px solid #f1f5f9;
}}
.ips-side-line:last-child {{ border-bottom: none; font-weight: 700; }}
.ips-photo-card {{
  background: #f8fafc;
  border: 1px dashed {BORDER};
  border-radius: 12px;
  min-height: 10rem;
  display: flex;
  align-items: center;
  justify-content: center;
  color: {TEXT_MUTED};
  font-size: 0.8125rem;
  text-align: center;
  padding: 1rem;
}}

/* Person / user profile header (Users, Employees detail) */
.ips-profile-header {{
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 0.75rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid {BORDER};
}}
.ips-profile-avatar {{
  width: 3.25rem;
  height: 3.25rem;
  border-radius: 999px;
  background: #dbeafe;
  color: {PRIMARY};
  font-weight: 700;
  font-size: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}}
.ips-profile-main {{
  flex: 1;
  min-width: 12rem;
}}
.ips-profile-name {{
  font-size: 1.05rem;
  font-weight: 700;
  margin: 0;
  color: {TEXT};
}}
.ips-profile-sub {{
  font-size: 0.8125rem;
  color: {TEXT_MUTED};
  margin: 0.2rem 0 0;
}}
.ips-profile-contact {{
  font-size: 0.8125rem;
  color: {TEXT_MUTED};
  margin-top: 0.35rem;
  line-height: 1.5;
}}
.ips-profile-actions {{
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  align-items: center;
  margin-left: auto;
}}

.ips-nested-table-wrap {{
  margin-top: 0.75rem;
}}
.ips-status-in-service {{ background:#dcfce7; color:#166534; border-color:#bbf7d0; }}
.ips-status-out-of-service {{ background:#fee2e2; color:#dc2626; border-color:#fecaca; }}
.ips-status-scheduled {{ background:#dbeafe; color:#1d4ed8; border-color:#bfdbfe; }}

.ips-week-nav {{
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  margin-bottom: 0.65rem;
}}
.ips-week-label {{
  font-size: 0.875rem;
  font-weight: 600;
  color: {TEXT};
  min-width: 12rem;
  text-align: center;
}}
.ips-time-detail-header {{
  background: {CARD_BG};
  border: 1px solid {BORDER};
  border-left: 3px solid {PRIMARY};
  border-radius: 12px;
  padding: 0.75rem 1rem;
  margin: 0.65rem 0;
}}
.ips-time-grid-table {{
  background: {CARD_BG};
  border: 1px solid {BORDER};
  border-radius: 12px;
  padding: 0.65rem 0.75rem;
  margin-bottom: 0.65rem;
}}
.ips-update-card {{
  background: {CARD_BG};
  border: 1px solid {BORDER};
  border-radius: 12px;
  padding: 0.75rem 0.85rem;
  margin-bottom: 0.5rem;
}}
.ips-update-card.pinned {{
  border-left: 3px solid {PRIMARY};
}}
.ips-update-card-title {{
  font-weight: 700;
  font-size: 0.9rem;
  color: {TEXT};
  margin: 0 0 0.25rem;
}}
.ips-update-card-meta {{
  font-size: 0.72rem;
  color: {TEXT_MUTED};
  margin-top: 0.35rem;
}}
.ips-event-block {{
  display: flex;
  gap: 0.65rem;
  padding: 0.5rem 0;
  border-bottom: 1px solid #f1f5f9;
  font-size: 0.8125rem;
}}
.ips-event-date {{
  background: #eff6ff;
  color: {PRIMARY};
  border-radius: 8px;
  padding: 0.35rem 0.45rem;
  font-size: 0.68rem;
  font-weight: 700;
  text-align: center;
  min-width: 2.75rem;
  line-height: 1.2;
}}
.ips-quick-link {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.45rem 0;
  border-bottom: 1px solid #f1f5f9;
  font-size: 0.8125rem;
  color: {TEXT};
}}
.ips-alert-banner {{
  background: #fff7ed;
  border: 1px solid #fed7aa;
  border-radius: 10px;
  padding: 0.5rem 0.75rem;
  font-size: 0.8125rem;
  color: #c2410c;
  margin-bottom: 0.65rem;
}}
.ips-restricted-tag {{
  font-size: 0.68rem;
  font-weight: 700;
  color: #dc2626;
  background: #fee2e2;
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
  margin-left: 0.35rem;
}}
.ips-report-section {{
  background: {CARD_BG};
  border: 1px solid {BORDER};
  border-radius: 12px;
  padding: 0.75rem 0.85rem;
  margin-bottom: 0.65rem;
}}
.ips-report-section-title {{
  font-size: 0.9rem;
  font-weight: 700;
  color: {TEXT};
  margin: 0 0 0.5rem;
}}
.ips-lookup-panel {{
  background: {CARD_BG};
  border: 1px solid {BORDER};
  border-radius: 12px;
  padding: 0.75rem 0.85rem;
  margin-top: 0.5rem;
}}
.ips-activity-item {{
  font-size: 0.8125rem;
  color: {TEXT_MUTED};
  padding: 0.35rem 0;
  border-bottom: 1px solid #f1f5f9;
}}

/* Page shell — marker class; Streamlit main area scoped via :has() */
.ips-page-content {{
  display: none !important;
  height: 0 !important;
  width: 0 !important;
  overflow: hidden !important;
  margin: 0 !important;
  padding: 0 !important;
}}
section[data-testid="stMain"]:has(.ips-page-content) [data-testid="stMainBlockContainer"],
section[data-testid="stMain"]:has(.ips-page-content) .block-container {{
  max-width: 1680px !important;
  width: 100% !important;
}}
section[data-testid="stMain"]:has(.ips-page-content) [data-testid="stElementContainer"] {{
  margin-bottom: 0.1rem !important;
}}

/* Strip default Streamlit chrome in main area */
section[data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"] {{
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
  padding: 0 !important;
}}
section[data-testid="stMain"] [data-testid="element-container"] {{
  background: transparent !important;
}}
section[data-testid="stMain"] [data-testid="stExpander"] {{
  background: {CARD_BG} !important;
  border: 1px solid {BORDER} !important;
  border-radius: 12px !important;
}}
section[data-testid="stMain"] [data-testid="stExpander"] summary {{
  font-size: 0.875rem !important;
  font-weight: 600 !important;
}}

/* Sidebar — fixed nav SaaS layout */
section[data-testid="stSidebar"] {{
  min-width: 15.5rem !important;
  max-width: 15.5rem !important;
}}
section[data-testid="stSidebar"] > div {{
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}}
.ips-sidebar-logo-wrap {{
  padding: 0.65rem 0.75rem 0.85rem;
  border-bottom: 1px solid {BORDER};
  margin-bottom: 0.35rem;
}}
.ips-sidebar-logo-wrap img {{
  max-height: 44px;
  width: auto;
  display: block;
}}
.ips-sidebar-brand {{
  font-size: 0.95rem;
  font-weight: 700;
  color: {TEXT};
  margin: 0;
}}
.ips-sidebar-tagline {{
  font-size: 0.7rem;
  color: {TEXT_MUTED};
  margin: 0.15rem 0 0;
}}
.ips-sidebar-nav-label {{
  font-size: 0.65rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: {TEXT_MUTED};
  padding: 0.5rem 0.85rem 0.25rem;
  margin: 0;
}}
.ips-sidebar-spacer {{
  flex: 1 1 auto;
  min-height: 1.5rem;
}}
.ips-sidebar-version {{
  font-size: 0.68rem;
  color: {TEXT_MUTED};
  text-align: center;
  padding: 0.5rem 0.75rem 0.75rem;
  margin: 0;
  border-top: 1px solid {BORDER};
  letter-spacing: 0.02em;
}}
section[data-testid="stSidebar"] .stButton > button {{
  width: 100% !important;
  justify-content: flex-start !important;
  text-align: left !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  color: {TEXT} !important;
  font-weight: 500 !important;
  font-size: 0.8125rem !important;
  min-height: 2.15rem !important;
  padding: 0.4rem 0.75rem !important;
  margin: 0.05rem 0.4rem !important;
  border-radius: 8px !important;
}}
section[data-testid="stSidebar"] .stButton > button:hover {{
  background: #f1f5f9 !important;
}}
section[data-testid="stSidebar"] .stButton > button[kind="primary"],
section[data-testid="stSidebar"] .stButton > button[data-testid="baseButton-primary"] {{
  background: {SELECTED_BG} !important;
  color: {PRIMARY} !important;
  font-weight: 600 !important;
  border-left: 3px solid {PRIMARY} !important;
  padding-left: calc(0.75rem - 3px) !important;
}}
section[data-testid="stSidebar"] .stButton > button[kind="secondary"] {{
  background: transparent !important;
  color: {TEXT} !important;
}}
section[data-testid="stSidebar"] hr {{
  margin: 0.5rem 0.65rem !important;
  border-color: {BORDER} !important;
}}

/* Tabs — underline style */
.ips-tabs-wrap {{
  margin-bottom: 0.65rem;
}}
.ips-tabs-wrap [data-testid="stRadio"] > div {{
  flex-direction: row !important;
  flex-wrap: wrap !important;
  gap: 0.15rem !important;
  border-bottom: 1px solid {BORDER};
  padding-bottom: 0.15rem;
}}
.ips-tabs-wrap [data-testid="stRadio"] label {{
  background: transparent !important;
  border: none !important;
  border-radius: 0 !important;
  padding: 0.45rem 0.75rem !important;
  margin: 0 !important;
  font-size: 0.8125rem !important;
  font-weight: 500 !important;
  color: {TEXT_MUTED} !important;
  box-shadow: none !important;
}}
.ips-tabs-wrap [data-testid="stRadio"] label[data-checked="true"],
.ips-tabs-wrap [data-testid="stRadio"] label:has(input:checked) {{
  color: {PRIMARY} !important;
  font-weight: 600 !important;
  border-bottom: 2px solid {PRIMARY} !important;
  margin-bottom: -1px !important;
}}

/* Detail panel actions */
.ips-detail-panel [data-testid="stHorizontalBlock"] {{
  flex-wrap: nowrap !important;
  gap: 0.5rem !important;
}}
.ips-detail-panel [data-testid="stHorizontalBlock"] [data-testid="column"] {{
  min-width: 0 !important;
  flex: 1 1 auto !important;
}}
.ips-detail-actions .stButton > button,
.ips-detail-panel [data-testid="stHorizontalBlock"] .stButton > button {{
  min-height: 2rem !important;
  max-height: 2.15rem !important;
  font-size: 0.75rem !important;
  padding: 0.2rem 0.55rem !important;
  white-space: nowrap !important;
}}
.ips-detail-actions .stButton > button p,
.ips-detail-panel [data-testid="stHorizontalBlock"] .stButton > button p {{
  white-space: nowrap !important;
}}
.ips-detail-actions .stButton > button[kind="primary"],
.ips-detail-panel [data-testid="stHorizontalBlock"] .stButton > button[kind="primary"] {{
  background: {PRIMARY} !important;
  border-color: {PRIMARY} !important;
  color: #fff !important;
}}

/* Table cells — prevent broken stacked text */
.ips-data-table-stable .ips-data-row > div,
.ips-data-table-header > div {{
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}}
.ips-data-table-stable .ips-data-row > div .ips-status-pill {{
  white-space: nowrap;
}}

/* Header action column */
.ips-header-actions .stButton > button {{
  min-height: 2.1rem !important;
  font-size: 0.8125rem !important;
  white-space: nowrap !important;
}}
.ips-header-actions .stButton > button p {{
  white-space: nowrap !important;
}}

.ips-tab-placeholder {{
  background: #f8fafc;
  border: 1px dashed {BORDER};
  border-radius: 10px;
  padding: 1.25rem;
  text-align: center;
  color: {TEXT_MUTED};
  font-size: 0.8125rem;
  margin: 0.5rem 0;
}}
</style>
""",
        unsafe_allow_html=True,
    )
    try:
        from app.ui.clean_table import inject_clean_table_css
    except ImportError:
        from ui.clean_table import inject_clean_table_css  # type: ignore
    inject_clean_table_css()
    inject_ips_dialog_styles()
    inject_action_colors_css()
