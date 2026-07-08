"""
Centralized IPS operations platform CSS.

Call inject_global_css() on every Streamlit render (no session guard).
"""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

# Design tokens
APP_BG = "#f4f6f9"
MAIN_HEADER_BG = "#e8ecf1"
SIDEBAR_BG = "#ffffff"
CARD_BG = "#ffffff"
BORDER = "#e5eaf2"
PRIMARY = "#2563eb"
PRIMARY_HOVER = "#1d4ed8"
BRAND_NAV_BTN = "#4361EE"
BRAND_NAV_BTN_HOVER = "#3651D4"
TEXT = "#0f172a"
TEXT_MUTED = "#64748b"
SELECTED_BG = "#eff6ff"
SELECTED_BORDER = "#2563eb"


def inject_users_module_css() -> None:
    """Users list custom table styling — call at the top of the users page render."""
    st.markdown(
        f"""
<style id="ips-users-module-v31">
section[data-testid="stMain"]:has(.ips-users-page) {{
  background: #f9fafb !important;
}}
section[data-testid="stMain"]:has(.ips-users-page) [data-testid="stAppViewContainer"],
section[data-testid="stMain"]:has(.ips-users-page) .block-container {{
  background: #f9fafb !important;
}}
section[data-testid="stMain"]:has(.ips-users-page) [data-testid="stCaptionContainer"] {{
  margin: 0 0 10px 0 !important;
  padding: 0 !important;
}}
section[data-testid="stMain"]:has(.ips-users-page) [data-testid="stCaptionContainer"] p {{
  color: #64748b !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  margin: 0 !important;
}}
.users-page-header-card {{
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
  padding: 28px 32px;
  margin: 0 0 16px 0;
}}
.users-page-header-inner {{
  display: flex;
  align-items: center;
  gap: 18px;
}}
.users-page-header-icon {{
  flex: 0 0 auto;
  width: 56px;
  height: 56px;
  border-radius: 14px;
  background: #eff6ff;
  color: #2563eb;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}}
.users-page-header-text {{
  min-width: 0;
}}
.users-page-header-title {{
  margin: 0;
  font-size: 34px;
  line-height: 1.1;
  font-weight: 800;
  color: #0f172a;
  letter-spacing: -0.02em;
}}
.users-page-header-subtitle {{
  margin: 8px 0 0 0;
  font-size: 15px;
  line-height: 1.35;
  color: #64748b;
  font-weight: 400;
}}
.st-key-users_toolbar_wrap {{
  background: #ffffff !important;
  border: 1px solid #e5e7eb !important;
  border-radius: 14px !important;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06) !important;
  padding: 12px 16px !important;
  margin: 0 0 16px 0 !important;
}}
.users-toolbar-marker {{
  display: none !important;
}}
.st-key-users_toolbar_wrap [data-testid="stVerticalBlock"] {{
  gap: 0 !important;
}}
.st-key-users_toolbar_wrap [data-testid="stHorizontalBlock"] {{
  display: flex !important;
  flex-wrap: nowrap !important;
  align-items: center !important;
  gap: 14px !important;
  margin: 0 !important;
  padding: 0 !important;
  width: 100% !important;
}}
.st-key-users_toolbar_wrap [data-testid="stHorizontalBlock"] > [data-testid="column"] {{
  display: flex !important;
  align-items: center !important;
  align-self: stretch !important;
  min-width: 0 !important;
  padding: 0 !important;
  margin: 0 !important;
}}
.st-key-users_toolbar_wrap [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child {{
  flex: 1 1 auto !important;
  min-width: 280px !important;
}}
.st-key-users_toolbar_wrap [data-testid="stHorizontalBlock"] > [data-testid="column"]:not(:first-child) {{
  flex: 0 0 auto !important;
  width: auto !important;
  min-width: 0 !important;
}}
.st-key-users_toolbar_wrap [data-testid="stTextInput"] {{
  margin: 0 !important;
  width: 100% !important;
}}
.st-key-users_toolbar_wrap [data-testid="stTextInput"] > div,
.st-key-users_toolbar_wrap [data-testid="stTextInput"] > div > div {{
  width: 100% !important;
}}
.st-key-users_toolbar_wrap [data-testid="stTextInput"] input {{
  min-height: 46px !important;
  height: 46px !important;
  width: 100% !important;
  box-sizing: border-box !important;
  border-radius: 10px !important;
  border: 1px solid #d1d5db !important;
  background: #ffffff !important;
}}
.st-key-users_toolbar_wrap .stButton,
.st-key-users_toolbar_wrap [data-testid="stButton"] {{
  margin: 0 !important;
  width: 100% !important;
}}
.st-key-users_toolbar_wrap .stButton > button,
.st-key-users_toolbar_wrap [data-testid="stButton"] > button {{
  min-height: 46px !important;
  height: 46px !important;
  padding: 0 16px !important;
  white-space: nowrap !important;
  border-radius: 10px !important;
  font-weight: 600 !important;
}}
.st-key-users_toolbar_wrap [class*="st-key-users_export"] button,
.st-key-users_toolbar_wrap [class*="st-key-users_clear_filters"] button {{
  background: #ffffff !important;
  border: 1px solid #d1d5db !important;
  color: #334155 !important;
}}
.st-key-users_toolbar_wrap [class*="st-key-emp_add"] button {{
  background: #2563eb !important;
  border: 1px solid #2563eb !important;
  color: #ffffff !important;
  font-weight: 700 !important;
}}
.st-key-users_toolbar_wrap [data-testid="stElementContainer"] {{
  margin: 0 !important;
  padding: 0 !important;
}}
@media (max-width: 900px) {{
  .users-page-header-card {{
    padding: 20px 18px;
  }}
  .users-page-header-title {{
    font-size: 28px;
  }}
  .st-key-users_toolbar_wrap [data-testid="stHorizontalBlock"] {{
    flex-wrap: wrap !important;
    row-gap: 10px !important;
  }}
  .st-key-users_toolbar_wrap [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child {{
    flex: 1 1 100% !important;
    min-width: 0 !important;
  }}
}}
section[data-testid="stMain"]:has(.ips-users-page) .st-key-users_table_wrap {{
  margin-top: 0 !important;
  background: transparent !important;
  border: none !important;
  border-radius: 0 !important;
  overflow: visible !important;
  box-shadow: none !important;
}}
section[data-testid="stMain"]:has(.ips-users-page) .st-key-users_table_wrap [data-testid="stVerticalBlockBorderWrapper"],
section[data-testid="stMain"]:has(.ips-users-page) .st-key-users_table_wrap [data-testid="stVerticalBlock"] {{
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}}
.st-key-users_table_wrap {{
  overflow-x: auto;
  max-width: 100%;
  width: 100%;
  margin-top: 0 !important;
  background: transparent !important;
}}
.st-key-users_table_wrap [data-testid="stVerticalBlock"] {{
  gap: 9px !important;
  width: 100%;
  max-width: 100%;
  background: transparent !important;
}}
.st-key-users_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"],
.st-key-users_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] > [data-testid="stHorizontalBlock"] {{
  display: flex !important;
  flex-wrap: nowrap !important;
  align-items: center !important;
  gap: 0.5rem !important;
  border: 1px solid #e5e7eb !important;
  border-radius: 12px !important;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06) !important;
  padding: 14px 18px !important;
  margin: 0 !important;
  min-height: 60px;
  max-height: none;
  width: 100% !important;
  min-width: 0 !important;
  box-sizing: border-box !important;
  background: #ffffff !important;
}}
.st-key-users_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type,
.st-key-users_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] > [data-testid="stHorizontalBlock"]:first-of-type {{
  background: #ffffff !important;
  min-height: 44px !important;
  padding: 12px 18px !important;
  margin-bottom: 2px !important;
  border-bottom: 1px solid #e5e7eb !important;
}}
.st-key-users_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:has(.ips-users-table-row),
.st-key-users_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] > [data-testid="stHorizontalBlock"]:has(.ips-users-table-row) {{
  cursor: pointer;
  min-height: 60px;
}}
.st-key-users_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:has(.ips-users-table-row):hover,
.st-key-users_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] > [data-testid="stHorizontalBlock"]:has(.ips-users-table-row):hover {{
  background: #ffffff !important;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.08) !important;
}}
.st-key-users_table_wrap [data-testid="stHorizontalBlock"] > [data-testid="column"] {{
  display: flex !important;
  align-items: center !important;
  align-self: stretch !important;
  min-width: 0 !important;
  min-height: 0 !important;
  padding: 0 8px !important;
  overflow: visible !important;
  justify-content: flex-start !important;
  box-sizing: border-box !important;
}}
.st-key-users_table_wrap [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(6),
.st-key-users_table_wrap [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(7) {{
  justify-content: center !important;
}}
.st-key-users_table_wrap [data-testid="stHorizontalBlock"] > [data-testid="column"] > [data-testid="stVerticalBlock"],
.st-key-users_table_wrap [data-testid="stHorizontalBlock"] > [data-testid="column"] > [data-testid="stElementContainer"] {{
  width: 100% !important;
  min-width: 0 !important;
  justify-content: inherit !important;
  align-items: inherit !important;
  padding: 0 !important;
  margin: 0 !important;
  gap: 0 !important;
  overflow: visible !important;
}}
.st-key-users_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-users-table-row) > [data-testid="column"]:first-child {{
  justify-content: flex-start !important;
  align-items: center !important;
  padding-left: 4px !important;
}}
.st-key-users_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-users-table-row) .ips-users-cell,
.st-key-users_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-users-table-row) .ips-user-pill,
.st-key-users_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-users-table-row) .ips-users-pill-col {{
  pointer-events: none;
}}
.ips-users-header-row {{
  background: transparent;
  border: 0;
  padding: 0;
  font-size: 11px;
  font-weight: 800;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  min-height: 0;
  display: flex;
  align-items: center;
  width: 100%;
  min-width: 0;
}}
.st-key-users_table_wrap [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:nth-child(6) .ips-users-header-row,
.st-key-users_table_wrap [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:nth-child(7) .ips-users-header-row {{
  justify-content: center !important;
  text-align: center !important;
}}
.st-key-users_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-users-table-row) > [data-testid="column"]:first-child {{
  display: flex !important;
  align-items: center !important;
  justify-content: flex-start !important;
  text-align: left !important;
  width: 100% !important;
  min-width: 0 !important;
  overflow: visible !important;
}}
.ips-users-cell {{
  color: {TEXT};
  font-size: 0.875rem;
  line-height: 1.35;
  min-width: 0;
  padding: 0;
  text-align: left;
  overflow: visible;
  white-space: normal;
  word-break: break-word;
}}
.ips-users-cell-email {{
  color: #64748b;
  font-size: 0.875rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}}
.ips-users-pill-col {{
  display: flex;
  align-items: center;
  justify-content: flex-start;
  width: 100%;
  min-width: 0;
}}
.ips-users-pill-col-center {{
  justify-content: center !important;
}}
.ips-user-pill {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 26px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
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
.ips-user-status-deleted {{
  background: #fee2e2;
  color: #991b1b;
}}
.ips-user-status-locked {{
  background: #fee2e2;
  color: #991b1b;
}}
.ips-user-status-pending {{
  background: #fef3c7;
  color: #92400e;
}}
.ips-users-table-row {{
  display: none !important;
}}
.st-key-users_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-users-table-row) [class*="st-key-users_open_"] {{
  width: 100% !important;
  max-width: 100% !important;
  margin: 0 !important;
  padding: 0 !important;
  pointer-events: auto !important;
}}
.st-key-users_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-users-table-row) [class*="st-key-users_open_"] [data-testid="stButton"],
.st-key-users_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-users-table-row) [class*="st-key-users_open_"] .stButton {{
  width: 100% !important;
  max-width: 100% !important;
  margin: 0 !important;
  padding: 0 !important;
  display: flex !important;
  justify-content: flex-start !important;
  align-items: center !important;
}}
.st-key-users_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-users-table-row) [class*="st-key-users_open_"] button,
.st-key-users_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-users-table-row) [class*="st-key-users_open_"] [data-testid="stButton"] > button,
.st-key-users_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-users-table-row) [class*="st-key-users_open_"] button[data-testid="stBaseButton-tertiary"],
.users-name-link {{
  display: inline-flex !important;
  align-items: center !important;
  justify-content: flex-start !important;
  width: auto !important;
  max-width: 100% !important;
  min-height: 0 !important;
  height: auto !important;
  margin: 0 !important;
  padding: 0 !important;
  background: transparent !important;
  background-color: transparent !important;
  border: none !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  color: #2563eb !important;
  font-size: 15px !important;
  font-weight: 700 !important;
  line-height: 1.35 !important;
  text-align: left !important;
  cursor: pointer !important;
  overflow: visible !important;
  white-space: normal !important;
  word-break: break-word !important;
  text-overflow: clip !important;
}}
.st-key-users_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-users-table-row) [class*="st-key-users_open_"] button:hover,
.st-key-users_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-users-table-row) [class*="st-key-users_open_"] [data-testid="stButton"] > button:hover,
.users-name-link:hover {{
  color: #1d4ed8 !important;
  text-decoration: underline !important;
  background: transparent !important;
}}
.st-key-users_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-users-table-row) [class*="st-key-users_open_"] button > div,
.st-key-users_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-users-table-row) [class*="st-key-users_open_"] button p {{
  text-align: left !important;
  color: inherit !important;
  font-size: inherit !important;
  font-weight: inherit !important;
  white-space: normal !important;
  word-break: break-word !important;
  overflow: visible !important;
}}
.st-key-users_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:has(.ips-table-header-filter-marker) [data-testid="stHorizontalBlock"] {{
  display: flex !important;
  gap: 0 !important;
  width: 100% !important;
}}
.st-key-users_table_wrap [data-testid="stElementContainer"] {{
  margin: 0 !important;
  padding: 0 !important;
}}
.ips-admin-pw-reset-marker {{
  display: none !important;
}}
.ips-admin-pw-reset-title {{
  color: #1e3a8a !important;
}}
.ips-admin-auth-status {{
  margin: 0.15rem 0 0.55rem 0;
  font-size: 0.8125rem;
  line-height: 1.45;
  color: #334155;
}}
.ips-admin-auth-status-label {{
  font-weight: 700;
  color: #475569;
}}
.ips-admin-auth-status-value {{
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 8px;
  margin: 0 0.35rem 0 0.15rem;
  border-radius: 999px;
  font-size: 0.6875rem;
  font-weight: 800;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}}
.ips-admin-auth-status--connected .ips-admin-auth-status-value {{
  background: #dcfce7;
  color: #166534;
}}
.ips-admin-auth-status--missing .ips-admin-auth-status-value {{
  background: #fef3c7;
  color: #92400e;
}}
.ips-admin-auth-status--stale .ips-admin-auth-status-value {{
  background: #fee2e2;
  color: #991b1b;
}}
.ips-admin-auth-status-email {{
  color: #64748b;
  font-size: 0.75rem;
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
  min-height: 56px;
  padding: 5px 10px;
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
<style id="ips-customers-module-v7">
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
  font-size: 20px;
  font-weight: 700;
  color: #2563eb;
  line-height: 1.25;
  word-break: break-word;
}}
.ips-customers-name-cell {{
  display: flex;
  align-items: center;
  justify-content: flex-start;
  width: 100%;
  min-height: 46px;
  padding-left: 24px;
  padding-right: 24px;
  box-sizing: border-box;
  text-align: left;
  pointer-events: none;
}}
.ips-customers-name-label {{
  pointer-events: none;
  display: block;
  width: 100%;
  font-size: 20px;
  font-weight: 700;
  color: #2563eb;
  line-height: 1.25;
  text-align: left;
  word-break: break-word;
}}
.st-key-customers_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-customers-table-row) {{
  position: relative !important;
  cursor: pointer !important;
}}
.st-key-customers_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-customers-table-row) > [data-testid="column"]:first-child,
.st-key-customers_table_wrap [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:first-child {{
  padding-left: 0 !important;
  padding-right: 0 !important;
  align-items: flex-start !important;
  justify-content: flex-start !important;
  text-align: left !important;
}}
.st-key-customers_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-customers-table-row) > [data-testid="column"]:first-child [data-testid="stVerticalBlock"],
.st-key-customers_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-customers-table-row) > [data-testid="column"]:first-child [data-testid="stElementContainer"],
.st-key-customers_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-customers-table-row) > [data-testid="column"]:first-child [data-testid="stMarkdownContainer"] {{
  align-items: flex-start !important;
  justify-content: flex-start !important;
  text-align: left !important;
  width: 100% !important;
}}
.st-key-customers_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-customers-table-row) > [data-testid="column"]:first-child [data-testid="stElementContainer"]:has(.ips-customers-table-row) {{
  position: absolute !important;
  left: 0 !important;
  top: 0 !important;
  width: 0 !important;
  height: 0 !important;
  min-height: 0 !important;
  overflow: hidden !important;
  opacity: 0 !important;
  pointer-events: none !important;
  margin: 0 !important;
  padding: 0 !important;
  z-index: 0 !important;
}}
.st-key-customers_table_wrap .ips-customers-table-row {{
  display: block !important;
  min-height: 0 !important;
  max-height: 0 !important;
  height: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  overflow: hidden !important;
  border: none !important;
}}
.st-key-customers_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-customers-table-row) > [data-testid="column"]:first-child [class*="st-key-customers_open_"] {{
  position: relative !important;
  z-index: 2 !important;
  width: 100% !important;
  max-width: 100% !important;
  align-self: stretch !important;
  margin-left: 0 !important;
  margin-right: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
}}
.st-key-customers_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-customers-table-row) > [data-testid="column"]:first-child [class*="st-key-customers_open_"] [data-testid="stButton"],
.st-key-customers_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-customers-table-row) > [data-testid="column"]:first-child [class*="st-key-customers_open_"] .stButton {{
  width: 100% !important;
  max-width: 100% !important;
  min-height: 46px !important;
  margin: 0 !important;
  padding: 0 !important;
  display: flex !important;
  justify-content: flex-start !important;
  align-items: stretch !important;
}}
.st-key-customers_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-customers-table-row) > [data-testid="column"]:first-child [class*="st-key-customers_open_"] [data-testid="stButton"] > button,
.st-key-customers_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-customers-table-row) > [data-testid="column"]:first-child [class*="st-key-customers_open_"] .stButton > button,
.st-key-customers_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-customers-table-row) > [data-testid="column"]:first-child [class*="st-key-customers_open_"] button[data-testid="stBaseButton-tertiary"] {{
  display: flex !important;
  align-items: center !important;
  justify-content: flex-start !important;
  width: 100% !important;
  max-width: 100% !important;
  min-height: 46px !important;
  margin: 0 !important;
  padding: 0 14px 0 24px !important;
  background: transparent !important;
  background-color: transparent !important;
  border: none !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  color: #2563eb !important;
  font-size: 20px !important;
  font-weight: 700 !important;
  line-height: 1.25 !important;
  text-align: left !important;
  cursor: pointer !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  white-space: nowrap !important;
}}
.st-key-customers_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-customers-table-row) > [data-testid="column"]:first-child [class*="st-key-customers_open_"] [data-testid="stButton"] > button:hover,
.st-key-customers_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-customers-table-row) > [data-testid="column"]:first-child [class*="st-key-customers_open_"] .stButton > button:hover,
.st-key-customers_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-customers-table-row) > [data-testid="column"]:first-child [class*="st-key-customers_open_"] button[data-testid="stBaseButton-tertiary"]:hover {{
  color: #1d4ed8 !important;
  text-decoration: underline !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}}
.st-key-customers_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-customers-table-row) > [data-testid="column"]:first-child [class*="st-key-customers_open_"] [data-testid="stButton"] > button > div,
.st-key-customers_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-customers-table-row) > [data-testid="column"]:first-child [class*="st-key-customers_open_"] [data-testid="stButton"] > button p {{
  width: 100% !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  white-space: nowrap !important;
  text-align: left !important;
  color: inherit !important;
  font-size: inherit !important;
  font-weight: inherit !important;
}}
.st-key-customers_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-customers-table-row) .ips-customers-cell,
.st-key-customers_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-customers-table-row) .ips-customer-status-pill {{
  pointer-events: none;
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
<style id="ips-jobs-module-v28">
.st-key-jobs_table_wrap .ips-jobs-table-wrap,
.st-key-jobs_table_wrap .ips-jobs-table-wrap.jobs-table {{
  background: #ffffff !important;
  border: none !important;
  border-radius: 0 !important;
  overflow: visible !important;
  margin-bottom: 0 !important;
  box-shadow: none !important;
}}
.ips-jobs-table-wrap,
.ips-jobs-table-wrap.jobs-table {{
  background: #ffffff;
  border: none;
  border-radius: 0;
  overflow: visible;
  margin-bottom: 0;
}}
.ips-jobs-header-row {{
  background: transparent;
  border-bottom: none;
  padding: 0;
  font-size: 0.6875rem;
  font-weight: 800;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  min-height: 0;
  display: flex;
  align-items: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.2;
}}
.ips-jobs-row {{
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  padding: 2px 8px;
  min-height: 48px;
}}
.ips-jobs-row:hover {{
  background: #f8fbff;
}}
.ips-jobs-row-selected {{
  background: #eaf2ff !important;
}}
.ips-jobs-cell {{
  color: #0f172a;
  font-size: 0.78rem;
  font-weight: 600;
  line-height: 1.2;
  min-width: 0;
}}
.ips-jobs-number {{
  font-size: 0.78rem;
  font-weight: 700;
  color: #2563eb;
  line-height: 1.2;
  white-space: nowrap;
}}
.ips-jobs-title {{
  font-size: 0.8125rem;
  font-weight: 700;
  line-height: 1.2;
  word-break: normal;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}}
.ips-jobs-title-link,
.job-project-link {{
  display: flex !important;
  align-items: center !important;
  height: 100% !important;
  min-height: 0 !important;
  width: 100% !important;
  cursor: pointer !important;
}}
.ips-jobs-title-text,
.job-project-text {{
  font-weight: 800 !important;
  color: {PRIMARY} !important;
  font-size: 0.875rem;
  line-height: 1.3;
  cursor: pointer;
  word-break: normal !important;
  overflow-wrap: anywhere !important;
  white-space: normal !important;
}}
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row):hover .ips-jobs-title-text,
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row):hover .job-project-text {{
  color: {PRIMARY_HOVER} !important;
  text-decoration: underline !important;
}}
.ips-jobs-muted {{
  font-size: 13px;
  color: #64748b;
  word-break: break-word;
}}
.st-key-jobs_table_wrap .ips-jobs-table-row,
.st-key-jobs_table_wrap .ips-jobs-row-marker,
.st-key-jobs_table_wrap .job-row,
.st-key-jobs_table_wrap .jobs-table-row {{
  min-height: 0 !important;
  max-height: 0 !important;
  height: 0 !important;
  padding: 0 !important;
  margin: 0 !important;
  overflow: hidden !important;
  border: none !important;
  background: transparent !important;
}}
.ips-job-status-pill {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 22px;
  min-height: 22px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 800;
  white-space: nowrap;
  line-height: 1;
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
  background: #ffedd5;
  color: #c2410c;
}}
.ips-job-status-active {{
  background: #dcfce7;
  color: #14532d;
}}
.ips-job-status-awarded {{
  background: #dcfce7;
  color: #14532d;
}}
.ips-job-status-on-hold {{
  background: #fee2e2;
  color: #991b1b;
}}
.ips-job-status-completed {{
  background: #dbeafe;
  color: #1e40af;
}}
.ips-job-status-closed {{
  background: #f1f5f9;
  color: #64748b;
}}
.ips-job-status-cancelled {{
  background: #f1f5f9;
  color: #64748b;
}}
.ips-job-status-archived {{
  background: #f1f5f9;
  color: #64748b;
}}
.ips-job-status-deleted {{
  background: #f1f5f9;
  color: #64748b;
}}
.ips-job-status-estimate-pending {{
  background: #fef9c3;
  color: #854d0e;
}}
.ips-job-status-pending {{
  background: #fef9c3;
  color: #854d0e;
}}
.st-key-jobs_table_wrap [data-testid="stVerticalBlock"] {{
  gap: 0 !important;
}}
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"] {{
  gap: 0 !important;
  align-items: center !important;
  border-bottom: 1px solid #e5e7eb;
  margin: 0 !important;
}}
.st-key-jobs_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row),
.st-key-jobs_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] > [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row),
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row) {{
  background: #ffffff !important;
  background-color: #ffffff !important;
  cursor: pointer;
  min-height: 46px !important;
  max-height: 46px !important;
  height: 46px !important;
  padding: 0 !important;
}}
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row) > [data-testid="column"],
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row) > [data-testid="column"] > [data-testid="stVerticalBlock"],
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row) > [data-testid="column"] > [data-testid="stElementContainer"] {{
  background: #ffffff !important;
  background-color: #ffffff !important;
}}
.st-key-jobs_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type,
.st-key-jobs_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] > [data-testid="stHorizontalBlock"]:first-of-type,
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:first-of-type {{
  background: #eef2f7 !important;
  background-color: #eef2f7 !important;
  min-height: 44px !important;
  max-height: 44px !important;
  height: 44px !important;
  padding: 0 !important;
  position: sticky;
  top: 0;
  z-index: 12;
  box-shadow: 0 1px 0 #dbe3ef;
}}
.st-key-jobs_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row):hover,
.st-key-jobs_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] > [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row):hover,
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row):hover,
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row):hover > [data-testid="column"],
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row):hover > [data-testid="column"] > [data-testid="stVerticalBlock"],
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row):hover > [data-testid="column"] > [data-testid="stElementContainer"] {{
  background: #f8fbff !important;
  background-color: #f8fbff !important;
}}
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row),
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.job-row),
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.jobs-table-row) {{
  display: flex !important;
  align-items: center !important;
}}
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row) > [data-testid="column"],
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"] {{
  display: flex !important;
  align-items: center !important;
  align-self: stretch !important;
  justify-content: flex-start !important;
  min-height: 0 !important;
  height: auto !important;
  min-width: 0 !important;
  padding: 0 10px !important;
  box-sizing: border-box !important;
}}
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row) > [data-testid="column"] > [data-testid="stVerticalBlock"],
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row) > [data-testid="column"] > [data-testid="stElementContainer"],
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"] > [data-testid="stVerticalBlock"],
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"] > [data-testid="stElementContainer"] {{
  display: flex !important;
  flex-direction: column !important;
  justify-content: center !important;
  align-items: stretch !important;
  width: 100% !important;
  height: 100% !important;
  min-height: 100% !important;
  margin: 0 !important;
  padding: 0 !important;
  gap: 0 !important;
}}
.ips-jobs-cell,
.jobs-table-cell,
.job-cell {{
  display: flex !important;
  align-items: center !important;
  height: 100% !important;
  min-height: 0 !important;
  width: 100% !important;
}}
.ips-jobs-number-link,
.job-number-link {{
  display: flex !important;
  align-items: center !important;
  height: 100% !important;
  min-height: 0 !important;
}}
.ips-jobs-money {{
  display: flex !important;
  align-items: center !important;
  justify-content: flex-end !important;
  min-height: 0 !important;
  font-size: 0.8125rem !important;
  font-weight: 600 !important;
  color: #0f172a !important;
  font-variant-numeric: tabular-nums;
  text-align: right !important;
}}
.ips-jobs-money-empty {{
  color: #64748b !important;
  font-weight: 700 !important;
}}
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row) > [data-testid="column"]:not(:has(.ips-jobs-col-num)):not(:has(.ips-jobs-col-desc)) [data-testid="stMarkdown"] p,
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row) > [data-testid="column"]:not(:has(.ips-jobs-col-num)):not(:has(.ips-jobs-col-desc)) .ips-jobs-cell,
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row) > [data-testid="column"]:not(:has(.ips-jobs-col-num)):not(:has(.ips-jobs-col-desc)) .job-cell,
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row) > [data-testid="column"]:not(:has(.ips-jobs-col-num)):not(:has(.ips-jobs-col-desc)) .jobs-table-cell {{
  font-weight: 600 !important;
  color: #0f172a !important;
  font-size: 0.8125rem !important;
  line-height: 1.25 !important;
}}
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row) > [data-testid="column"]:has(.ips-job-status-pill),
.st-key-jobs_table_wrap [data-testid="column"]:has(.job-status-cell) {{
  align-items: center !important;
}}
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row) > [data-testid="column"]:has(.ips-job-status-pill) [data-testid="stMarkdown"],
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row) > [data-testid="column"]:has(.ips-job-status-pill) [data-testid="stElementContainer"],
.st-key-jobs_table_wrap [data-testid="column"]:has(.job-status-cell) [data-testid="stMarkdown"],
.st-key-jobs_table_wrap [data-testid="column"]:has(.job-status-cell) [data-testid="stElementContainer"] {{
  display: flex !important;
  align-items: center !important;
  flex-wrap: wrap !important;
  gap: 0.25rem !important;
  width: 100% !important;
  min-height: 0 !important;
}}
.st-key-jobs_table_wrap [data-testid="stElementContainer"] {{
  margin-bottom: 0 !important;
  padding-bottom: 0 !important;
}}
.st-key-jobs_table_wrap [data-testid="stCheckbox"] {{
  margin: 0 !important;
}}
.st-key-jobs_table_wrap [data-testid="stCheckbox"] label {{
  min-height: 0 !important;
  height: auto !important;
  margin: 0 !important;
  padding: 0 !important;
}}
.st-key-jobs_table_wrap .stButton > button {{
  height: 30px !important;
  min-height: 30px !important;
  padding: 0 10px !important;
  border-radius: 8px !important;
  font-size: 13px !important;
  width: auto !important;
}}
.st-key-jobs_table_wrap .ips-jobs-table-link [data-testid="stButton"],
.st-key-jobs_table_wrap .ips-jobs-table-link .stButton {{
  width: 100%;
  min-width: 0;
  margin: 0;
}}
.ips-jobs-list-link {{
  color: {PRIMARY} !important;
  font-weight: 800 !important;
  font-size: 0.8125rem !important;
  text-decoration: none !important;
  cursor: pointer !important;
  pointer-events: auto !important;
}}
.ips-jobs-list-link:hover,
.ips-jobs-list-link:focus {{
  color: {PRIMARY_HOVER} !important;
  text-decoration: underline !important;
}}
.st-key-jobs_table_wrap .ips-jobs-table-link button,
.st-key-jobs_table_wrap .job-number-link button,
.st-key-jobs_table_wrap .ips-jobs-number-link button,
.st-key-jobs_table_wrap .ips-jobs-title-link button,
.st-key-jobs_table_wrap .job-project-link button,
.st-key-jobs_table_wrap [class*="st-key-job_open_num_"] button,
.st-key-jobs_table_wrap [class*="st-key-job_open_title_"] button {{
  background: transparent !important;
  background-color: transparent !important;
  color: {PRIMARY} !important;
  font-weight: 800 !important;
  font-size: 0.8125rem !important;
  border: none !important;
  border-radius: 0 !important;
  padding: 0 !important;
  height: auto !important;
  min-height: 0 !important;
  max-height: none !important;
  width: auto !important;
  max-width: 100% !important;
  min-width: 0 !important;
  box-shadow: none !important;
  outline: none !important;
  text-align: left !important;
  justify-content: flex-start !important;
  display: inline-flex !important;
  align-items: center !important;
  cursor: pointer !important;
  transition: color 0.15s ease !important;
}}
.st-key-jobs_table_wrap .ips-jobs-number-link button,
.st-key-jobs_table_wrap .job-number-link button,
.st-key-jobs_table_wrap [class*="st-key-job_open_num_"] button {{
  white-space: nowrap !important;
  overflow: visible !important;
  text-overflow: clip !important;
  width: auto !important;
  max-width: none !important;
}}
.st-key-jobs_table_wrap .ips-jobs-number-link [data-testid="stButton"],
.st-key-jobs_table_wrap .job-number-link [data-testid="stButton"],
.st-key-jobs_table_wrap [class*="st-key-job_open_num_"] [data-testid="stButton"] {{
  width: auto !important;
  max-width: none !important;
}}
.st-key-jobs_table_wrap .ips-jobs-number-link button p,
.st-key-jobs_table_wrap .job-number-link button p,
.st-key-jobs_table_wrap [class*="st-key-job_open_num_"] button p {{
  overflow: visible !important;
  text-overflow: clip !important;
}}
.st-key-jobs_table_wrap .ips-jobs-title-link button,
.st-key-jobs_table_wrap .job-project-link button,
.st-key-jobs_table_wrap [class*="st-key-job_open_title_"] button {{
  white-space: nowrap !important;
  line-height: 1.2 !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}}
.st-key-jobs_table_wrap .ips-jobs-table-link button:hover,
.st-key-jobs_table_wrap .ips-jobs-table-link button:focus,
.st-key-jobs_table_wrap .job-number-link button:hover,
.st-key-jobs_table_wrap .job-number-link button:focus,
.st-key-jobs_table_wrap .ips-jobs-title-link button:hover,
.st-key-jobs_table_wrap .ips-jobs-title-link button:focus {{
  background: transparent !important;
  background-color: transparent !important;
  color: {PRIMARY_HOVER} !important;
  text-decoration: underline !important;
  border: none !important;
  box-shadow: none !important;
}}
.st-key-jobs_table_wrap .ips-jobs-table-link button > div,
.st-key-jobs_table_wrap .ips-jobs-table-link button p,
.st-key-jobs_table_wrap .ips-jobs-table-link button span {{
  color: inherit !important;
  font-weight: inherit !important;
  text-align: left !important;
}}
.ips-jobs-number-text {{
  font-weight: 800 !important;
  color: {PRIMARY} !important;
  font-size: 0.875rem;
  line-height: 1.25;
  cursor: pointer;
  white-space: nowrap;
}}
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row):hover .ips-jobs-number-text {{
  color: {PRIMARY_HOVER} !important;
  text-decoration: underline !important;
}}
.st-key-jobs_table_wrap [data-testid="column"]:has(.ips-jobs-actions-cell),
.st-key-jobs_table_wrap [data-testid="column"]:has(.job-actions-cell) {{
  overflow: visible !important;
  display: flex !important;
  flex-direction: column !important;
  align-items: flex-end !important;
  justify-content: center !important;
  flex: 0 0 44px !important;
  min-width: 44px !important;
  width: 44px !important;
  max-width: 44px !important;
  padding-right: 6px !important;
}}
.st-key-jobs_table_wrap [data-testid="column"]:has(.ips-jobs-actions-cell)
[data-testid="column"]:has(.job-row-actions-menu) {{
  flex: 0 0 auto !important;
  width: auto !important;
  min-width: 0 !important;
  max-width: none !important;
  display: flex !important;
  align-items: center !important;
  justify-content: flex-end !important;
}}
.st-key-jobs_table_wrap [data-testid="column"]:has(.job-actions-cell) button[data-testid="stBaseButton-popover"],
.st-key-jobs_table_wrap [data-testid="column"]:has(.job-actions-cell) [data-testid="column"]:has(.job-row-actions-menu) button[data-testid="stBaseButton-popover"],
.st-key-jobs_table_wrap [data-testid="column"]:has(.job-actions-button) button[data-testid="stBaseButton-popover"],
.st-key-jobs_table_wrap [data-testid="column"]:has(.job-actions-cell) [data-testid="column"]:has(.ips-jobs-row-menu-marker) button[data-testid="stBaseButton-popover"] {{
  display: inline-flex !important;
  flex-direction: row !important;
  flex-wrap: nowrap !important;
  align-items: center !important;
  justify-content: center !important;
  min-height: 28px !important;
  height: 28px !important;
  min-width: 28px !important;
  width: 28px !important;
  max-width: 28px !important;
  padding: 0 !important;
  border-radius: 6px !important;
  background: transparent !important;
  border: 1px solid transparent !important;
  box-shadow: none !important;
  color: #64748b !important;
  font-size: 1rem !important;
  font-weight: 700 !important;
  line-height: 1 !important;
  white-space: nowrap !important;
  overflow: visible !important;
}}
.st-key-jobs_table_wrap [data-testid="column"]:has(.job-actions-cell) button[data-testid="stBaseButton-popover"]:hover,
.st-key-jobs_table_wrap [data-testid="column"]:has(.job-actions-cell) [data-testid="column"]:has(.ips-jobs-row-menu-marker) button[data-testid="stBaseButton-popover"]:hover {{
  background: #f1f5f9 !important;
  border-color: #e2e8f0 !important;
  color: #0f172a !important;
}}
.st-key-jobs_table_wrap [data-testid="column"]:has(.job-actions-cell) button[data-testid="stBaseButton-primary"],
.st-key-jobs_table_wrap [data-testid="column"]:has(.job-actions-cell) [data-testid="column"]:has(.job-row-actions-menu) button[data-testid="stBaseButton-primary"] {{
  display: none !important;
}}
.st-key-jobs_table_wrap [data-testid="column"]:has(.job-actions-cell) button[data-testid="stBaseButton-popover"] > div,
.st-key-jobs_table_wrap [data-testid="column"]:has(.job-actions-cell) [data-testid="column"]:has(.job-row-actions-menu) button[data-testid="stBaseButton-popover"] > div,
.st-key-jobs_table_wrap [data-testid="column"]:has(.job-actions-cell) button[data-testid="stBaseButton-primary"] > div,
.st-key-jobs_table_wrap [data-testid="column"]:has(.job-actions-cell) [data-testid="column"]:has(.job-row-actions-menu) button[data-testid="stBaseButton-primary"] > div {{
  display: inline-flex !important;
  flex-direction: row !important;
  align-items: center !important;
  justify-content: center !important;
  white-space: nowrap !important;
}}
.st-key-jobs_table_wrap [data-testid="column"]:has(.job-actions-cell) button[data-testid="stBaseButton-popover"] p,
.st-key-jobs_table_wrap [data-testid="column"]:has(.job-actions-cell) button[data-testid="stBaseButton-popover"] span,
.st-key-jobs_table_wrap [data-testid="column"]:has(.job-actions-cell) [data-testid="column"]:has(.job-row-actions-menu) button[data-testid="stBaseButton-popover"] p,
.st-key-jobs_table_wrap [data-testid="column"]:has(.job-actions-cell) [data-testid="column"]:has(.job-row-actions-menu) button[data-testid="stBaseButton-popover"] span,
.st-key-jobs_table_wrap [data-testid="column"]:has(.job-actions-cell) button[data-testid="stBaseButton-primary"] p,
.st-key-jobs_table_wrap [data-testid="column"]:has(.job-actions-cell) button[data-testid="stBaseButton-primary"] span,
.st-key-jobs_table_wrap [data-testid="column"]:has(.job-actions-cell) [data-testid="column"]:has(.job-row-actions-menu) button[data-testid="stBaseButton-primary"] p,
.st-key-jobs_table_wrap [data-testid="column"]:has(.job-actions-cell) [data-testid="column"]:has(.job-row-actions-menu) button[data-testid="stBaseButton-primary"] span {{
  display: inline !important;
  white-space: nowrap !important;
  word-break: keep-all !important;
  color: #ffffff !important;
}}
.st-key-jobs_table_wrap [data-testid="column"]:has(.job-actions-cell) button[data-testid="stBaseButton-popover"]:hover,
.st-key-jobs_table_wrap [data-testid="column"]:has(.job-actions-cell) button[data-testid="stBaseButton-primary"]:hover {{
  background: {PRIMARY_HOVER} !important;
  border-color: {PRIMARY_HOVER} !important;
  color: #ffffff !important;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.28) !important;
}}
div[data-testid="stPopover"]:has(.job-row-actions-panel) {{
  background: #ffffff !important;
  border: 1px solid #dbe3ef !important;
  border-radius: 12px !important;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.12) !important;
  overflow: hidden !important;
}}
body:has(.job-row-actions-panel) div[data-baseweb="popover"],
div[data-baseweb="popover"]:has(.job-row-actions-panel) {{
  background: #ffffff !important;
  background-color: #ffffff !important;
  border: 1px solid #dbe3ef !important;
  border-radius: 12px !important;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.12) !important;
  overflow: hidden !important;
}}
div[data-testid="stPopoverBody"]:has(.job-row-actions-panel) {{
  padding: 0.5rem !important;
  min-width: 280px !important;
  max-width: 340px !important;
  width: 300px !important;
  background: #ffffff !important;
  background-color: #ffffff !important;
  border: none !important;
  border-radius: 12px !important;
  box-shadow: none !important;
  color: #0f172a !important;
}}
div[data-testid="stPopoverBody"]:has(.job-row-actions-panel) [data-testid="stVerticalBlock"],
div[data-testid="stPopoverBody"]:has(.job-row-actions-panel) [data-testid="stVerticalBlockBorderWrapper"],
div[data-testid="stPopoverBody"]:has(.job-row-actions-panel) [data-testid="stElementContainer"],
div[data-baseweb="popover"]:has(.job-row-actions-panel) [data-testid="stVerticalBlock"],
div[data-baseweb="popover"]:has(.job-row-actions-panel) [data-testid="stVerticalBlockBorderWrapper"],
div[data-baseweb="popover"]:has(.job-row-actions-panel) [data-testid="stElementContainer"] {{
  background: #ffffff !important;
  background-color: #ffffff !important;
  border-color: transparent !important;
}}
div[data-testid="stPopoverBody"]:has(.job-row-actions-panel) [data-testid="stVerticalBlock"] {{
  gap: 0.2rem !important;
}}
div[data-testid="stPopoverBody"]:has(.job-row-actions-panel) .job-row-actions-divider {{
  border: none !important;
  border-top: 1px solid #e8edf3 !important;
  margin: 0.45rem 0 !important;
  height: 0 !important;
  opacity: 1 !important;
}}
div[data-testid="stPopoverBody"]:has(.job-row-actions-panel) .job-row-actions-section {{
  margin: 0.15rem 0 0.25rem 0 !important;
  padding: 0 0.15rem !important;
}}
div[data-testid="stPopoverBody"]:has(.job-row-actions-panel) .job-row-actions-section-title {{
  margin: 0 !important;
  padding: 0.15rem 0.35rem 0.1rem 1.85rem !important;
  font-size: 0.8125rem !important;
  font-weight: 700 !important;
  color: #0f172a !important;
  line-height: 1.25 !important;
  position: relative !important;
}}
div[data-testid="stPopoverBody"]:has(.job-row-actions-panel) .job-row-actions-section-title::before {{
  content: "" !important;
  position: absolute !important;
  left: 0.35rem !important;
  top: 50% !important;
  transform: translateY(-50%) !important;
  width: 18px !important;
  height: 18px !important;
  background: center / contain no-repeat url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='%232563eb' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M7 16l-4-4 4-4'/%3E%3Cpath d='M3 12h14'/%3E%3Cpath d='M17 8l4 4-4 4'/%3E%3Cpath d='M21 12H7'/%3E%3C/svg%3E") !important;
}}
div[data-testid="stPopoverBody"]:has(.job-row-actions-panel) [data-testid="stSelectbox"] {{
  margin: 0 !important;
  padding: 0 0.15rem 0.35rem !important;
}}
div[data-testid="stPopoverBody"]:has(.job-row-actions-panel) [data-testid="stSelectbox"] label {{
  font-size: 0.75rem !important;
  font-weight: 500 !important;
  color: #64748b !important;
  margin-bottom: 0.35rem !important;
}}
div[data-testid="stPopoverBody"]:has(.job-row-actions-panel) [data-testid="stSelectbox"] [data-baseweb="select"] > div {{
  min-height: 42px !important;
  border-color: #dbe3ef !important;
  border-radius: 8px !important;
  background: #ffffff !important;
  box-shadow: none !important;
}}
div[data-testid="stPopoverBody"]:has(.job-row-actions-panel) [data-testid="stSelectbox"] [data-baseweb="select"] span {{
  color: #0f172a !important;
  font-weight: 600 !important;
  font-size: 0.875rem !important;
}}
div[data-testid="stPopoverBody"]:has(.job-row-actions-panel) .job-row-actions-status-select {{
  display: none !important;
}}
ul[role="listbox"] > li[aria-selected="true"] {{
  background: #eff6ff !important;
  color: #1e40af !important;
}}
ul[role="listbox"] > li[aria-selected="true"] svg {{
  color: {PRIMARY} !important;
  fill: {PRIMARY} !important;
}}
div[data-testid="stPopoverBody"]:has(.job-row-actions-panel) .stButton,
div[data-testid="stPopoverBody"]:has(.job-row-actions-panel) [data-testid="stButton"] {{
  margin: 0 !important;
  padding: 0 !important;
}}
div[data-testid="stPopoverBody"]:has(.job-row-actions-panel) .stButton > button,
div[data-testid="stPopoverBody"]:has(.job-row-actions-panel) [data-testid="stButton"] > button {{
  justify-content: flex-start !important;
  text-align: left !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  color: #0f172a !important;
  font-weight: 600 !important;
  font-size: 0.875rem !important;
  min-height: 44px !important;
  height: 44px !important;
  padding: 0 0.75rem 0 2.15rem !important;
  border-radius: 8px !important;
  white-space: nowrap !important;
  word-break: keep-all !important;
  overflow-wrap: normal !important;
  position: relative !important;
}}
div[data-testid="stPopoverBody"]:has(.job-row-actions-panel) .stButton > button:hover,
div[data-testid="stPopoverBody"]:has(.job-row-actions-panel) [data-testid="stButton"] > button:hover {{
  background: #f8fafc !important;
  color: #0f172a !important;
}}
div[data-testid="stPopoverBody"]:has(.job-row-actions-panel) .stButton > button:focus-visible,
div[data-testid="stPopoverBody"]:has(.job-row-actions-panel) [data-testid="stButton"] > button:focus-visible {{
  outline: 2px solid #2563eb !important;
  outline-offset: 1px !important;
}}
div[data-testid="stPopoverBody"]:has(.job-row-actions-panel) [data-testid="stElementContainer"]:has(.job-row-action-view) + [data-testid="stElementContainer"] [data-testid="stButton"] > button::before {{
  content: "" !important;
  position: absolute !important;
  left: 0.75rem !important;
  top: 50% !important;
  transform: translateY(-50%) !important;
  width: 18px !important;
  height: 18px !important;
  background: center / contain no-repeat url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='%232563eb' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z'/%3E%3Ccircle cx='12' cy='12' r='3'/%3E%3C/svg%3E") !important;
}}
div[data-testid="stPopoverBody"]:has(.job-row-actions-panel) [data-testid="stElementContainer"]:has(.job-row-action-edit) + [data-testid="stElementContainer"] [data-testid="stButton"] > button::before {{
  content: "" !important;
  position: absolute !important;
  left: 0.75rem !important;
  top: 50% !important;
  transform: translateY(-50%) !important;
  width: 18px !important;
  height: 18px !important;
  background: center / contain no-repeat url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='%232563eb' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M12 20h9'/%3E%3Cpath d='M16.5 3.5a2.121 2.121 0 013 3L7 19l-4 1 1-4L16.5 3.5z'/%3E%3C/svg%3E") !important;
}}
div[data-testid="stPopoverBody"]:has(.job-row-actions-panel) [data-testid="stElementContainer"]:has(.job-row-action-complete) + [data-testid="stElementContainer"] [data-testid="stButton"] > button,
div[data-testid="stPopoverBody"]:has(.job-row-actions-panel) [data-testid="stElementContainer"]:has(.job-row-action-complete) + [data-testid="stElementContainer"] [data-testid="stButton"] > button:hover {{
  color: #0f172a !important;
}}
div[data-testid="stPopoverBody"]:has(.job-row-actions-panel) [data-testid="stElementContainer"]:has(.job-row-action-complete) + [data-testid="stElementContainer"] [data-testid="stButton"] > button::before {{
  content: "✓" !important;
  position: absolute !important;
  left: 0.75rem !important;
  top: 50% !important;
  transform: translateY(-50%) !important;
  width: 18px !important;
  height: 18px !important;
  border-radius: 50% !important;
  background: #22c55e !important;
  color: #ffffff !important;
  font-size: 11px !important;
  font-weight: 800 !important;
  line-height: 18px !important;
  text-align: center !important;
}}
div[data-testid="stPopoverBody"]:has(.job-row-actions-panel) [data-testid="stElementContainer"]:has(.job-row-action-cancel) + [data-testid="stElementContainer"] [data-testid="stButton"] > button,
div[data-testid="stPopoverBody"]:has(.job-row-actions-panel) [data-testid="stElementContainer"]:has(.job-row-action-cancel) + [data-testid="stElementContainer"] [data-testid="stButton"] > button:hover {{
  color: #0f172a !important;
}}
div[data-testid="stPopoverBody"]:has(.job-row-actions-panel) [data-testid="stElementContainer"]:has(.job-row-action-cancel) + [data-testid="stElementContainer"] [data-testid="stButton"] > button::before {{
  content: "✕" !important;
  position: absolute !important;
  left: 0.75rem !important;
  top: 50% !important;
  transform: translateY(-50%) !important;
  width: 18px !important;
  height: 18px !important;
  border-radius: 50% !important;
  background: #f97316 !important;
  color: #ffffff !important;
  font-size: 10px !important;
  font-weight: 800 !important;
  line-height: 18px !important;
  text-align: center !important;
}}
div[data-testid="stPopoverBody"]:has(.job-row-actions-panel) [data-testid="stElementContainer"]:has(.job-row-action-delete) + [data-testid="stElementContainer"] [data-testid="stButton"] > button,
div[data-testid="stPopoverBody"]:has(.job-row-actions-panel) [data-testid="stElementContainer"]:has(.job-row-action-delete) + [data-testid="stElementContainer"] [data-testid="stButton"] > button:hover {{
  color: #0f172a !important;
}}
div[data-testid="stPopoverBody"]:has(.job-row-actions-panel) [data-testid="stElementContainer"]:has(.job-row-action-delete) + [data-testid="stElementContainer"] [data-testid="stButton"] > button::before {{
  content: "" !important;
  position: absolute !important;
  left: 0.75rem !important;
  top: 50% !important;
  transform: translateY(-50%) !important;
  width: 18px !important;
  height: 18px !important;
  background: center / contain no-repeat url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='%23dc2626' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='3 6 5 6 21 6'/%3E%3Cpath d='M19 6l-1 14H6L5 6'/%3E%3Cpath d='M10 11v6'/%3E%3Cpath d='M14 11v6'/%3E%3Cpath d='M9 6V4h6v2'/%3E%3C/svg%3E") !important;
}}
@media (max-width: 900px) {{
  div[data-testid="stPopoverBody"]:has(.job-row-actions-panel) {{
    min-width: 280px !important;
    max-width: min(340px, calc(100vw - 1.5rem)) !important;
    width: min(300px, calc(100vw - 1.5rem)) !important;
  }}
}}
.ips-jc-summary-card {{
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 12px 14px;
  min-height: 72px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}}
.ips-jc-summary-compact {{
  min-height: 58px;
  padding: 8px 10px;
}}
.ips-jc-summary-label {{
  font-size: 0.72rem;
  font-weight: 700;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 4px;
}}
.ips-jc-summary-value {{
  font-size: 1.05rem;
  font-weight: 800;
  color: #0f172a;
  line-height: 1.2;
}}
.ips-jc-card-profit .ips-jc-summary-value,
.ips-jc-card-margin .ips-jc-summary-value {{
  color: #15803d;
}}
.ips-jc-card-negative .ips-jc-summary-value {{
  color: #dc2626;
}}
.ips-jc-card-neutral .ips-jc-summary-value {{
  color: #94a3b8;
}}
.ips-jc-card-remaining .ips-jc-summary-value {{
  color: #0369a1;
}}
.ips-jc-metric-row {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #f1f5f9;
  margin-bottom: 4px;
}}
.ips-jc-metric-label {{
  font-size: 0.82rem;
  color: #64748b;
  font-weight: 600;
}}
.ips-jc-metric-value {{
  font-size: 0.92rem;
  color: #0f172a;
  font-weight: 700;
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
.st-key-job_tasks_table_wrap [class*="st-key-job_task_title_"] .stButton > button {{
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  color: #0f172a !important;
  font-size: 14px !important;
  font-weight: 600 !important;
  text-align: left !important;
  padding: 0 !important;
  height: auto !important;
  min-height: 28px !important;
  justify-content: flex-start !important;
}}
.st-key-job_tasks_table_wrap [class*="st-key-job_task_title_"] .stButton > button:hover {{
  color: #2563eb !important;
  text-decoration: underline !important;
}}
.st-key-job_tasks_table_wrap [data-testid="stHorizontalBlock"]:not(:has(.ips-subjob-delete-confirm-marker)) > [data-testid="column"]:last-child {{
  flex: 0 0 64px !important;
  width: 64px !important;
  min-width: 56px !important;
  max-width: 72px !important;
  display: flex !important;
  justify-content: center !important;
  align-items: center !important;
}}
.st-key-job_tasks_table_wrap [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:last-child .ips-job-tasks-header-row {{
  justify-content: center;
  width: 100%;
}}
.st-key-job_tasks_table_wrap [class*="st-key-job_task_delete_"] {{
  display: flex !important;
  justify-content: center !important;
  align-items: center !important;
  width: 100%;
}}
.st-key-job_tasks_table_wrap [class*="st-key-job_task_delete_"] .stButton {{
  display: flex !important;
  justify-content: center !important;
  width: 100%;
}}
.st-key-job_tasks_table_wrap [class*="st-key-job_task_delete_"] .stButton > button {{
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
  min-height: 28px !important;
  height: 28px !important;
  width: 28px !important;
  min-width: 28px !important;
  margin: 0 auto !important;
}}
.st-key-job_tasks_table_wrap [class*="st-key-job_task_delete_"] .stButton > button:hover {{
  background: #fef2f2 !important;
  border-radius: 6px !important;
}}
.st-key-job_tasks_table_wrap [class*="st-key-job_task_delete_confirm_"] {{
  background: #fef2f2 !important;
  border-bottom: 1px solid #fecaca !important;
  padding: 8px 12px !important;
  margin: 0 !important;
}}
.st-key-job_tasks_table_wrap [class*="st-key-job_task_delete_confirm_"] [data-testid="stHorizontalBlock"] {{
  border-bottom: none !important;
  background: transparent !important;
  min-height: 40px !important;
  padding: 0 !important;
}}
.ips-subjob-delete-confirm-message {{
  font-size: 13px;
  font-weight: 600;
  color: #991b1b;
  line-height: 1.35;
  margin: 0;
}}
.st-key-job_tasks_table_wrap [class*="st-key-job_task_delete_confirm_"] [class*="st-key-confirm_delete_subjob_"] .stButton > button {{
  background: #dc2626 !important;
  border: 1px solid #dc2626 !important;
  color: #ffffff !important;
  font-size: 12px !important;
  min-height: 30px !important;
  height: 30px !important;
  padding: 0 10px !important;
}}
.st-key-job_tasks_table_wrap [class*="st-key-job_task_delete_confirm_"] [class*="st-key-confirm_delete_subjob_"] .stButton > button:hover {{
  background: #b91c1c !important;
  border-color: #b91c1c !important;
}}
.st-key-job_tasks_table_wrap [class*="st-key-job_task_delete_confirm_"] [class*="st-key-cancel_delete_subjob_"] .stButton > button {{
  background: #ffffff !important;
  border: 1px solid #cbd5e1 !important;
  color: #334155 !important;
  font-size: 12px !important;
  min-height: 30px !important;
  height: 30px !important;
  padding: 0 10px !important;
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
.st-key-certifications_table_wrap [data-testid="stLinkButton"] > a,
.st-key-emp_certifications_table_wrap [data-testid="stLinkButton"] > a {{
  display: inline-flex !important;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: 28px;
  padding: 0 10px !important;
  border-radius: 999px !important;
  background: #dbeafe !important;
  color: #1d4ed8 !important;
  border: 1px solid #93c5fd !important;
  font-size: 11px !important;
  font-weight: 700 !important;
  text-decoration: none !important;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
.st-key-certifications_table_wrap [data-testid="stLinkButton"] > a:hover,
.st-key-emp_certifications_table_wrap [data-testid="stLinkButton"] > a:hover {{
  background: #bfdbfe !important;
  color: #1e3a8a !important;
  border-color: #60a5fa !important;
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
<style id="ips-estimates-module-v3">
.ips-estimates-table-wrap {{
  background: transparent;
  border: none;
  border-radius: 0;
  overflow: visible;
  margin-bottom: 0;
}}
.ips-estimates-header-row {{
  background: transparent;
  border: none;
  padding: 0;
  font-size: inherit;
  font-weight: inherit;
  color: inherit;
  text-transform: inherit;
  letter-spacing: inherit;
  min-height: 0;
  display: flex;
  align-items: center;
  white-space: nowrap;
  overflow: visible;
  text-overflow: clip;
  line-height: 1.2;
}}
.ips-estimates-row {{
  background: transparent;
  border: none;
  padding: 0;
  min-height: 0;
}}
.ips-estimates-row:hover {{
  background: transparent;
}}
.ips-estimates-row-selected {{
  background: transparent !important;
}}
.ips-estimates-cell {{
  color: {TEXT};
  font-size: 0.8125rem;
  line-height: 1.2;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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
  font-weight: 800;
  color: #2563eb;
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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
  padding: 5px 10px;
  text-align: left;
  border-bottom: 1px solid #e2e8f0;
  vertical-align: middle;
}}
.ips-est-li-td {{
  font-size: 12px;
  color: #0f172a;
  padding: 5px 10px;
  border-bottom: 1px solid #eef2f7;
  vertical-align: middle;
  min-height: 56px;
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


def _list_table_checkbox_column_css(table_wrap_key: str) -> str:
    """Full click target for row-selection checkbox in custom list tables."""
    sel = f".st-key-{table_wrap_key}"
    return f"""
{sel} [data-testid="stHorizontalBlock"]:not(:first-of-type) > [data-testid="column"]:first-child {{
  position: relative !important;
  z-index: 5 !important;
  overflow: visible !important;
  flex: 0 0 3rem !important;
  width: 3rem !important;
  min-width: 3rem !important;
  max-width: 3rem !important;
  pointer-events: auto !important;
}}
{sel} [data-testid="stHorizontalBlock"]:not(:first-of-type) > [data-testid="column"]:nth-child(2) {{
  position: relative !important;
  z-index: 1 !important;
  pointer-events: none !important;
}}
{sel} [data-testid="stHorizontalBlock"]:not(:first-of-type) > [data-testid="column"]:nth-child(2) * {{
  pointer-events: none !important;
}}
{sel} [data-testid="stHorizontalBlock"]:not(:first-of-type) > [data-testid="column"]:first-child [data-testid="stVerticalBlock"] {{
  width: 100% !important;
  min-height: 44px !important;
  position: relative !important;
}}
{sel} [data-testid="stHorizontalBlock"]:not(:first-of-type) > [data-testid="column"]:first-child [data-testid="stElementContainer"] {{
  width: 100% !important;
  min-height: 44px !important;
  position: relative !important;
  margin: 0 !important;
  padding: 0 !important;
}}
{sel} [data-testid="stHorizontalBlock"]:not(:first-of-type) > [data-testid="column"]:first-child [data-testid="stCheckbox"] {{
  position: absolute !important;
  inset: 0 !important;
  width: 100% !important;
  height: 100% !important;
  margin: 0 !important;
  pointer-events: auto !important;
}}
{sel} [data-testid="stHorizontalBlock"]:not(:first-of-type) > [data-testid="column"]:first-child [data-testid="stCheckbox"] label {{
  position: absolute !important;
  inset: 0 !important;
  width: 100% !important;
  height: 100% !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  cursor: pointer !important;
  padding: 0 !important;
  margin: 0 !important;
  box-sizing: border-box !important;
  pointer-events: auto !important;
}}
{sel} [data-testid="stHorizontalBlock"]:not(:first-of-type) > [data-testid="column"]:first-child [data-testid="stCheckbox"] label input {{
  position: absolute !important;
  inset: 0 !important;
  width: 100% !important;
  height: 100% !important;
  margin: 0 !important;
  opacity: 0 !important;
  cursor: pointer !important;
  z-index: 2 !important;
}}
{sel} [data-testid="stHorizontalBlock"]:not(:first-of-type) > [data-testid="column"]:first-child [data-testid="stCheckbox"] label > div,
{sel} [data-testid="stHorizontalBlock"]:not(:first-of-type) > [data-testid="column"]:first-child [data-testid="stCheckbox"] label > span {{
  position: relative !important;
  z-index: 1 !important;
  pointer-events: none !important;
  flex-shrink: 0 !important;
}}
"""


def inject_inventory_module_css() -> None:
    """Inventory module styling (detail views, thumbnails, transactions)."""
    st.markdown(
        f"""
<style id="ips-inventory-module-v8">
.ips-inventory-muted {{
  font-size: 0.8125rem;
  color: #64748b;
}}
.ips-inventory-qty {{
  text-align: right;
  font-variant-numeric: tabular-nums;
}}
.ips-inventory-status-pill {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 22px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 11px;
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
.image-cell,
.ips-inventory-image-cell {{
  text-align: center;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}}
.inventory-thumb,
.table-image-preview,
.ips-inventory-thumb-img,
.ips-inventory-thumb-placeholder {{
  width: 52px !important;
  height: 52px !important;
  min-width: 52px !important;
  max-width: 52px !important;
  min-height: 52px !important;
  max-height: 52px !important;
  object-fit: cover !important;
  border-radius: 8px !important;
  border: 1px solid #e2e8f0 !important;
  background: #f8fafc !important;
  display: block !important;
  margin: 0 auto !important;
  box-sizing: border-box !important;
}}
.ips-inventory-thumb-cell {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
}}
.ips-inventory-thumb-placeholder {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
  font-size: 1.1rem;
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
.ips-job-materials-head,
.ips-job-materials-row {{
  grid-template-columns: 0.45fr 0.85fr 1.15fr 0.5fr 0.7fr 0.7fr 0.85fr 0.85fr 0.65fr 1fr;
}}
.ips-job-mat-thumb {{
  width: 36px !important;
  height: 36px !important;
  object-fit: cover !important;
  border-radius: 6px !important;
}}
</style>
""",
        unsafe_allow_html=True,
    )


def inject_pricing_guide_module_css() -> None:
    """Pricing Guide list custom table styling (matches Inventory table)."""
    st.markdown(
        f"""
<style id="ips-pricing-guide-module-v5">
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
.st-key-pricing_guide_table_wrap [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(1) {{
  flex: 0 0 80px !important;
  min-width: 80px !important;
  max-width: 80px !important;
  width: 80px !important;
}}
.st-key-pricing_guide_table_wrap .stMarkdown p:has(.ips-pg-image-cell),
.st-key-pricing_guide_table_wrap .stMarkdown p:has(.ips-pg-thumb-cell-link) {{
  margin: 0 !important;
  line-height: normal !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
}}
.image-cell,
.ips-pg-image-cell {{
  width: 80px !important;
  min-width: 80px !important;
  max-width: 80px !important;
  text-align: center !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  vertical-align: middle !important;
  flex-shrink: 0 !important;
  height: auto !important;
}}
.ips-pg-thumb-cell-link {{
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  padding: 0 !important;
  margin: 0 auto !important;
  border: none !important;
  background: transparent !important;
  cursor: pointer !important;
  border-radius: 8px !important;
  line-height: 0 !important;
  flex-shrink: 0 !important;
  width: 52px !important;
  height: 52px !important;
  min-width: 52px !important;
  max-width: 52px !important;
  min-height: 52px !important;
  max-height: 52px !important;
  transition: box-shadow 0.15s ease;
}}
.ips-pg-thumb-cell-link:hover,
.ips-pg-thumb-cell-link:focus-visible {{
  outline: none !important;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15) !important;
}}
.ips-pg-thumb-cell-link:hover .ips-pg-thumb-img,
.ips-pg-thumb-cell-link:focus-visible .ips-pg-thumb-img,
.ips-pg-thumb-cell-link:hover .ips-pg-thumb-placeholder,
.ips-pg-thumb-cell-link:focus-visible .ips-pg-thumb-placeholder {{
  border-color: #93c5fd !important;
}}
.inventory-thumb,
.pricing-thumb,
.table-image-preview,
.ips-pg-thumb-img,
.ips-pg-thumb-placeholder {{
  width: 52px !important;
  height: 52px !important;
  min-width: 52px !important;
  max-width: 52px !important;
  min-height: 52px !important;
  max-height: 52px !important;
  object-fit: cover !important;
  border-radius: 8px !important;
  border: 1px solid #e2e8f0 !important;
  background: #f8fafc !important;
  display: block !important;
  margin: 0 auto !important;
  flex-shrink: 0 !important;
  box-sizing: border-box !important;
}}
.ips-pg-thumb-placeholder {{
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  object-fit: none !important;
  color: #94a3b8 !important;
  font-size: 0.8125rem !important;
  font-weight: 700 !important;
  line-height: 1 !important;
}}
.ips-pg-table-row {{
  display: none !important;
}}
.st-key-pricing_guide_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-pg-table-row) {{
  cursor: pointer;
}}
.st-key-pricing_guide_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-pg-table-row) [class*="st-key-pg_open_"] {{
  width: 100% !important;
  max-width: 100% !important;
  margin: 0 !important;
  padding: 0 !important;
  pointer-events: auto !important;
}}
.st-key-pricing_guide_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-pg-table-row) [class*="st-key-pg_open_"] [data-testid="stButton"],
.st-key-pricing_guide_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-pg-table-row) [class*="st-key-pg_open_"] .stButton {{
  width: 100% !important;
  max-width: 100% !important;
  margin: 0 !important;
  padding: 0 !important;
  display: flex !important;
  justify-content: flex-start !important;
  align-items: center !important;
}}
.st-key-pricing_guide_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-pg-table-row) [class*="st-key-pg_open_"] button,
.st-key-pricing_guide_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-pg-table-row) [class*="st-key-pg_open_"] [data-testid="stButton"] > button,
.st-key-pricing_guide_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-pg-table-row) [class*="st-key-pg_open_"] button[data-testid="stBaseButton-tertiary"] {{
  display: inline-flex !important;
  align-items: center !important;
  justify-content: flex-start !important;
  width: auto !important;
  max-width: 100% !important;
  min-height: 0 !important;
  height: auto !important;
  margin: 0 !important;
  padding: 0 !important;
  background: transparent !important;
  background-color: transparent !important;
  border: none !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  color: #2563eb !important;
  font-size: 14px !important;
  font-weight: 700 !important;
  line-height: 1.25 !important;
  text-align: left !important;
  cursor: pointer !important;
  overflow: visible !important;
  white-space: normal !important;
  word-break: break-word !important;
  text-overflow: clip !important;
}}
.st-key-pricing_guide_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-pg-table-row) [class*="st-key-pg_open_"] button:hover,
.st-key-pricing_guide_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-pg-table-row) [class*="st-key-pg_open_"] [data-testid="stButton"] > button:hover {{
  color: #1d4ed8 !important;
  text-decoration: underline !important;
  background: transparent !important;
  background-color: transparent !important;
}}
.st-key-pricing_guide_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-pg-table-row) [class*="st-key-pg_open_"] button > div,
.st-key-pricing_guide_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-pg-table-row) [class*="st-key-pg_open_"] button p {{
  margin: 0 !important;
  padding: 0 !important;
  text-align: left !important;
  white-space: normal !important;
  word-break: break-word !important;
}}
.ips-pg-detail-image {{
  width: 100%;
  max-width: 320px;
  max-height: 240px;
  object-fit: contain;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
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
.st-key-pricing_guide_table_wrap [data-testid="stHorizontalBlock"] > [data-testid="column"] {{
  display: flex !important;
  align-items: center !important;
  align-self: stretch !important;
}}
.st-key-pricing_guide_table_wrap [data-testid="stHorizontalBlock"] > [data-testid="column"] > [data-testid="stVerticalBlock"] {{
  width: 100%;
  justify-content: center !important;
}}
.st-key-pricing_guide_table_wrap [data-testid="stHorizontalBlock"] {{
  gap: 0.35rem !important;
  align-items: center !important;
  border-bottom: 1px solid #e2e8f0;
  padding: 6px 10px !important;
  margin: 0 !important;
  min-height: 56px;
  max-height: 64px;
}}
.st-key-pricing_guide_table_wrap [data-testid="stHorizontalBlock"]:first-of-type {{
  background: #f8fafc;
  min-height: 36px;
  max-height: none;
  padding: 5px 10px !important;
}}
.st-key-pricing_guide_table_wrap [data-testid="stHorizontalBlock"]:not(:first-of-type):hover {{
  background: #eef5ff;
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
</style>
""",
        unsafe_allow_html=True,
    )


def inject_inventory_qr_scan_css() -> None:
    """Mobile inventory QR scan / Use Inventory page."""
    st.markdown(
        f"""
<script>document.body.classList.add("ips-inv-qr-scan-page");</script>
<style id="ips-inventory-qr-scan-v3">
body.ips-inv-qr-scan-page section[data-testid="stSidebar"],
body.ips-inv-qr-scan-page [data-testid="stSidebarCollapsedControl"] {{
  display: none !important;
}}
body.ips-inv-qr-scan-page section[data-testid="stMain"]:has(.ips-inv-qr-scan-scope) .block-container {{
  max-width: 100% !important;
  padding: 0.75rem 1rem 2rem !important;
}}
.ips-inv-qr-mobile-header {{
  margin: 0 0 0.65rem 0;
  text-align: center;
}}
.ips-inv-qr-mobile-logo {{
  display: flex;
  justify-content: center;
  align-items: center;
}}
.ips-inv-qr-mobile-logo .ips-main-header-logo {{
  height: 52px !important;
  max-width: min(340px, 92vw) !important;
  width: auto !important;
}}
body.ips-inv-qr-scan-page section[data-testid="stMain"]:has(.ips-inv-qr-scan-scope) .ips-page-header {{
  margin-bottom: 0.85rem !important;
}}
body.ips-inv-qr-scan-page section[data-testid="stMain"]:has(.ips-inv-qr-scan-scope) .ips-page-title {{
  font-size: 1.65rem !important;
  font-weight: 800 !important;
  color: #0f172a !important;
}}
body.ips-inv-qr-scan-page section[data-testid="stMain"]:has(.ips-inv-qr-scan-scope) .ips-page-subtitle {{
  font-size: 0.88rem !important;
  color: #64748b !important;
  line-height: 1.45 !important;
}}
.ips-inv-qr-item-panel {{
  margin: 0 0 0.85rem 0;
}}
.ips-inv-qr-thumb-wrap {{
  margin: 0 0 0.5rem 0;
}}
.ips-inv-qr-thumb-cell {{
  display: inline-block;
}}
.ips-inv-qr-thumb-img,
.ips-inv-qr-thumb-cell img {{
  width: 72px;
  height: 72px;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  display: block;
  background: #ffffff;
}}
.ips-inv-qr-thumb-cell .ips-inventory-thumb-placeholder {{
  display: inline-flex;
  width: 72px;
  height: 72px;
  align-items: center;
  justify-content: center;
  font-size: 1.75rem;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
}}
.ips-inv-qr-item-card {{
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 12px 14px;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05);
}}
.ips-inv-qr-item-title {{
  font-size: 1rem;
  font-weight: 800;
  color: #0f172a;
  line-height: 1.35;
  margin-bottom: 2px;
}}
.ips-inv-qr-item-model {{
  font-size: 0.98rem;
  font-weight: 800;
  color: #0f172a;
  line-height: 1.3;
  margin-bottom: 6px;
}}
.ips-inv-qr-item-meta {{
  font-size: 0.82rem;
  color: #64748b;
  line-height: 1.45;
}}
.ips-inv-qr-item-onhand {{
  margin-top: 4px;
  color: #0f172a !important;
}}
.ips-inv-qr-field-label {{
  margin: 0 0 0.35rem 0;
  font-size: 0.92rem;
  font-weight: 700;
  color: #0f172a;
}}
.ips-inv-qr-field-label-spaced {{
  margin-top: 0.65rem !important;
}}
.ips-inv-qr-qty-hint {{
  margin: 0.25rem 0 0 0;
  font-size: 0.78rem;
  color: #94a3b8;
  text-align: center;
}}
body.ips-inv-qr-scan-page section[data-testid="stMain"]:has(.ips-inv-qr-scan-scope) [data-testid="stForm"] {{
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 14px 14px 12px;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05);
}}
body.ips-inv-qr-scan-page section[data-testid="stMain"]:has(.ips-inv-qr-scan-scope) [data-testid="stForm"] label {{
  display: none !important;
}}
body.ips-inv-qr-scan-page section[data-testid="stMain"]:has(.ips-inv-qr-scan-scope) [data-testid="stNumberInput"] input {{
  min-height: 52px !important;
  font-size: 1.35rem !important;
  font-weight: 700 !important;
  text-align: center !important;
  background: #ffffff !important;
  border-radius: 10px !important;
  border: 1px solid #e2e8f0 !important;
}}
body.ips-inv-qr-scan-page section[data-testid="stMain"]:has(.ips-inv-qr-scan-scope) [data-baseweb="select"] > div {{
  min-height: 48px !important;
  font-size: 0.95rem !important;
  background: #f8fafc !important;
  border-radius: 10px !important;
  border-color: #e2e8f0 !important;
}}
body.ips-inv-qr-scan-page section[data-testid="stMain"]:has(.ips-inv-qr-scan-scope) [data-testid="stForm"] button {{
  min-height: 52px !important;
  border-radius: 10px !important;
  font-weight: 700 !important;
}}
body.ips-inv-qr-scan-page section[data-testid="stMain"]:has(.ips-inv-qr-scan-scope) [data-testid="stForm"] button:not([kind="primary"]) {{
  background: #f1f5f9 !important;
  color: #334155 !important;
  border: 1px solid #e2e8f0 !important;
  font-size: 1.5rem !important;
  line-height: 1 !important;
}}
body.ips-inv-qr-scan-page section[data-testid="stMain"]:has(.ips-inv-qr-scan-scope) [data-testid="stForm"] button[kind="primary"] {{
  margin-top: 0.75rem !important;
  min-height: 50px !important;
  font-size: 1rem !important;
  background: {PRIMARY} !important;
  border-color: {PRIMARY} !important;
  color: #ffffff !important;
}}
</style>
""",
        unsafe_allow_html=True,
    )


def inject_table_header_filter_css() -> None:
    """Compact popover filters inside custom table headers."""
    st.markdown(
        """
<style id="ips-table-header-filter-v8">
.ips-table-header-filter-marker {
  display: none !important;
}
[class*="_table_wrap"] [data-testid="stHorizontalBlock"]:first-of-type {
  flex-wrap: nowrap !important;
}
[class*="_table_wrap"] [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"] {
  min-width: 0 !important;
  overflow: visible !important;
}
[class*="_table_wrap"] [data-testid="stHorizontalBlock"]:first-of-type .ips-table-header-filter-text,
[class*="_table_wrap"] [data-testid="stHorizontalBlock"]:first-of-type [class*="-header-row"] {
  font-size: 11px;
  font-weight: 800;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  white-space: nowrap !important;
  overflow: visible !important;
  text-overflow: clip !important;
  min-width: 0;
  line-height: 1.2;
  word-break: normal !important;
  writing-mode: horizontal-tb !important;
}
[class*="_table_wrap"] [data-testid="stHorizontalBlock"]:first-of-type .ips-table-header-filter-text {
  display: block;
}
.ips-table-header-filter-text.ips-table-header-filter-active {
  color: #2563eb !important;
}
[class*="_table_wrap"] [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:has(.ips-table-header-filter-marker) [data-testid="stElementContainer"] {
  margin: 0 !important;
  padding: 0 !important;
}
[class*="_table_wrap"] [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:has(.ips-table-header-filter-marker) [data-testid="stHorizontalBlock"] {
  align-items: center !important;
  flex-wrap: nowrap !important;
  gap: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  min-height: 0 !important;
  border: none !important;
  background: transparent !important;
}
[class*="_table_wrap"] [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:has(.ips-table-header-filter-marker) [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child {
  flex: 1 1 auto !important;
  min-width: 0 !important;
  overflow: visible !important;
}
[class*="_table_wrap"] [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:has(.ips-table-header-filter-marker) [data-testid="stHorizontalBlock"] > [data-testid="column"]:last-child {
  flex: 0 0 18px !important;
  width: 18px !important;
  min-width: 18px !important;
  max-width: 18px !important;
  overflow: visible !important;
}
[class*="_table_wrap"] [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:has(.ips-table-header-filter-marker) [data-testid="stHorizontalBlock"] > [data-testid="column"]:last-child [data-testid="stElementContainer"] {
  display: flex !important;
  justify-content: flex-end !important;
  align-items: center !important;
}
section[data-testid="stMain"] [class*="_table_wrap"] [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:has(.ips-table-header-filter-marker) [data-testid="stPopover"] > button,
section[data-testid="stMain"] [class*="_table_wrap"] [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:has(.ips-table-header-filter-marker) .stButton > button,
[class*="_table_wrap"] [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:has(.ips-table-header-filter-marker) [data-testid="stPopover"] > button,
[class*="_table_wrap"] [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:has(.ips-table-header-filter-marker) .stButton > button {
  background: transparent !important;
  background-color: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
  margin: 0 !important;
  min-height: 16px !important;
  max-height: 18px !important;
  height: 16px !important;
  min-width: 16px !important;
  width: auto !important;
  max-width: none !important;
  font-size: 12px !important;
  line-height: 1 !important;
  color: #64748b !important;
  justify-content: center !important;
  align-items: center !important;
}
section[data-testid="stMain"] [class*="_table_wrap"] [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:has(.ips-table-header-filter-marker) [data-testid="stPopover"] > button:hover,
section[data-testid="stMain"] [class*="_table_wrap"] [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:has(.ips-table-header-filter-marker) .stButton > button:hover,
[class*="_table_wrap"] [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:has(.ips-table-header-filter-marker) [data-testid="stPopover"] > button:hover,
[class*="_table_wrap"] [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:has(.ips-table-header-filter-marker) .stButton > button:hover {
  background: transparent !important;
  background-color: transparent !important;
  border: none !important;
  color: #2563eb !important;
}
[class*="_table_wrap"] [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:has(.ips-table-header-filter-marker) .stButton > button p {
  white-space: nowrap !important;
  margin: 0 !important;
  padding: 0 !important;
  line-height: 1 !important;
  font-size: 12px !important;
}
[class*="_table_wrap"] [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:has(.ips-table-header-filter-active) [data-testid="stPopover"] > button {
  color: #2563eb !important;
}
/* Icon-only filter trigger: one chevron, no duplicate icons or label text */
[class*="_table_wrap"] [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:has(.ips-table-header-filter-marker) [data-testid="stPopover"] > button {
  gap: 0 !important;
  font-size: 0 !important;
}
[class*="_table_wrap"] [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:has(.ips-table-header-filter-marker) [data-testid="stPopover"] > button p,
[class*="_table_wrap"] [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:has(.ips-table-header-filter-marker) [data-testid="stPopover"] > button span:not([data-testid="stIconMaterial"]),
[class*="_table_wrap"] [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:has(.ips-table-header-filter-marker) [data-testid="stPopover"] > button img {
  display: none !important;
  width: 0 !important;
  height: 0 !important;
  overflow: hidden !important;
  font-size: 0 !important;
  line-height: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
}
[class*="_table_wrap"] [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:has(.ips-table-header-filter-marker) [data-testid="stPopover"] > button > svg,
[class*="_table_wrap"] [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:has(.ips-table-header-filter-marker) [data-testid="stPopover"] > button [data-testid="stIconMaterial"] {
  display: none !important;
}
[class*="_table_wrap"] [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:has(.ips-table-header-filter-marker) [data-testid="stPopover"] > button:has([data-testid="stIconMaterial"]) [data-testid="stIconMaterial"]:first-of-type {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  width: 14px !important;
  height: 14px !important;
  min-width: 14px !important;
  max-width: 14px !important;
  margin: 0 !important;
  flex: 0 0 14px !important;
  font-size: 14px !important;
}
[class*="_table_wrap"] [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:has(.ips-table-header-filter-marker) [data-testid="stPopover"] > button:has([data-testid="stIconMaterial"]) [data-testid="stIconMaterial"]:first-of-type svg {
  display: inline-block !important;
  width: 14px !important;
  height: 14px !important;
  margin: 0 !important;
}
[class*="_table_wrap"] [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:has(.ips-table-header-filter-marker) [data-testid="stPopover"] > button:not(:has([data-testid="stIconMaterial"])) > svg:first-of-type {
  display: inline-block !important;
  width: 14px !important;
  height: 14px !important;
  margin: 0 !important;
}
[class*="_table_wrap"] [data-testid="stHorizontalBlock"]:first-of-type [data-testid="stPopoverBody"] [data-testid="stMultiSelect"] label,
[class*="_table_wrap"] [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:has(.ips-table-header-filter-marker) [data-testid="stMultiSelect"] > label {
  display: none !important;
}
.st-key-estimates_table_wrap [data-testid="stHorizontalBlock"]:first-of-type,
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:first-of-type,
.st-key-customers_table_wrap [data-testid="stHorizontalBlock"]:first-of-type,
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:first-of-type {
  min-height: 40px !important;
  height: auto !important;
  align-items: center !important;
}
.st-key-estimates_table_wrap [data-testid="stHorizontalBlock"]:first-of-type {
  min-height: 42px !important;
  max-height: 44px !important;
  height: 42px !important;
}
.ips-filter-dot {
  width: 6px;
  height: 6px;
  border-radius: 999px;
  background: #2563eb;
  display: inline-block;
  vertical-align: middle;
  margin-left: 3px;
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


def inject_table_viewport_fit() -> None:
    """Scale wide list tables to fit the main content area; full width when there is room."""
    st.markdown(
        """
<style id="ips-table-viewport-fit-v2">
section[data-testid="stMain"] [class*="_table_wrap"] {
  width: 100% !important;
  max-width: 100% !important;
  box-sizing: border-box !important;
}
section[data-testid="stMain"] .st-key-timekeeping_table_wrap {
  width: 100% !important;
  max-width: 100% !important;
  overflow-x: hidden !important;
  box-sizing: border-box !important;
}
section[data-testid="stMain"] .ips-data-table-scroll {
  width: 100% !important;
  max-width: 100% !important;
  box-sizing: border-box !important;
}
section[data-testid="stMain"] div[data-testid="stDataFrame"] {
  width: 100% !important;
  max-width: 100% !important;
  box-sizing: border-box !important;
}
[class*="_table_wrap"].ips-table-fit-host,
.ips-data-table-scroll.ips-table-fit-host,
div[data-testid="stDataFrame"].ips-table-fit-host {
  overflow-x: hidden !important;
}
[class*="_table_wrap"].ips-table-fit-scaled [data-testid="stHorizontalBlock"] > [data-testid="column"],
[class*="_table_wrap"].ips-table-fit-scaled .ips-users-ellipsis,
[class*="_table_wrap"].ips-table-fit-scaled .ips-timekeeping-employee,
[class*="_table_wrap"].ips-table-fit-scaled .employee-name,
[class*="_table_wrap"].ips-table-fit-scaled [class*="-ellipsis"] {
  overflow: visible !important;
  text-overflow: clip !important;
}
</style>
""",
        unsafe_allow_html=True,
    )
    html_doc = r"""
<script>
(function () {
  var w = window.parent || window;
  var doc = w.document;
  if (w.__ipsTableViewportFitBound) return;
  w.__ipsTableViewportFitBound = true;

  var WRAP_SEL =
    'section[data-testid="stMain"] [class*="_table_wrap"]:not(.ips-table-fit-opt-out)';
  var DATAFRAME_SEL =
    'section[data-testid="stMain"] div[data-testid="stDataFrame"]:not(.ips-table-fit-opt-out)';
  var SCROLL_SEL =
    'section[data-testid="stMain"] .ips-data-table-scroll:not(.ips-table-fit-opt-out)';
  var MIN_SCALE = 0.52;
  var SHELL_PAD = 56;

  function getAvailable(wrap) {
    var shell = wrap.closest('section[data-testid="stMain"]');
    if (shell && shell.clientWidth > 0) {
      return Math.max(240, shell.clientWidth - SHELL_PAD);
    }
    var p = wrap.parentElement;
    while (p) {
      if (p.clientWidth > 0) return p.clientWidth;
      p = p.parentElement;
    }
    return w.innerWidth || 1200;
  }

  function isTimekeepingWrap(wrap) {
    return !!(wrap && wrap.classList && wrap.classList.contains('st-key-timekeeping_table_wrap'));
  }

  function measureNeeded(scaler, wrap) {
    if (isTimekeepingWrap(wrap)) {
      var tkMax = 0;
      var tkRows = scaler.querySelectorAll(
        '[data-testid="stHorizontalBlock"]:has(.timekeeping-list-header-marker), ' +
          '[data-testid="stHorizontalBlock"]:has(.timekeeping-list-row-header-marker), ' +
          '[data-testid="stHorizontalBlock"]:has(.timesheet-list-row-marker)'
      );
      for (var t = 0; t < tkRows.length; t++) {
        var row = tkRows[t];
        if (row.closest('[class*="st-key-tk_expand_detail_"]')) continue;
        var rowW = row.scrollWidth || row.offsetWidth;
        if (rowW > tkMax) tkMax = rowW;
      }
      return tkMax;
    }
    var max = 0;
    var blocks = scaler.querySelectorAll('[data-testid="stHorizontalBlock"]');
    for (var i = 0; i < blocks.length; i++) {
      var b = blocks[i];
      if (b.closest('[class*="st-key-tk_expand_detail_"]')) continue;
      var sw = b.scrollWidth || b.offsetWidth;
      if (sw > max) max = sw;
    }
    var root = scaler.scrollWidth || scaler.offsetWidth;
    return Math.max(max, root);
  }

  function resetTkExpandInverse(wrap) {
    if (!wrap || !wrap.querySelectorAll) return;
    wrap.querySelectorAll('[class*="st-key-tk_expand_detail_"]').forEach(function (el) {
      el.style.transform = '';
      el.style.transformOrigin = '';
      el.style.width = '';
      el.style.maxWidth = '';
    });
  }

  function applyTkExpandInverse(wrap, scale) {
    if (!isTimekeepingWrap(wrap) || !scale || scale >= 0.995) return;
    var inv = 1 / scale;
    wrap.querySelectorAll('[class*="st-key-tk_expand_detail_"]').forEach(function (el) {
      el.style.transformOrigin = 'top left';
      el.style.transform = 'scale(' + inv + ')';
      el.style.width = 100 * scale + '%';
      el.style.maxWidth = 100 * scale + '%';
    });
  }

  function getScaler(wrap) {
    if (wrap.getAttribute && wrap.getAttribute('data-testid') === 'stDataFrame') {
      return (
        wrap.querySelector('[data-testid="stDataFrameResizable"]') ||
        wrap.querySelector('.dvn-scroller') ||
        wrap.firstElementChild ||
        wrap
      );
    }
    if (wrap.classList && wrap.classList.contains('ips-data-table-scroll')) {
      var inner = wrap.querySelector('.ips-data-table-stable, .ips-data-table-wrap, table');
      return inner || wrap;
    }
    return wrap.querySelector('[data-testid="stVerticalBlock"]') || wrap;
  }

  function resetWrap(wrap, scaler) {
    scaler.style.transform = '';
    scaler.style.transformOrigin = '';
    scaler.style.width = '';
    wrap.style.minHeight = '';
    wrap.classList.remove('ips-table-fit-host', 'ips-table-fit-scaled');
    wrap.dataset.ipsTableFitScale = '1';
    resetTkExpandInverse(wrap);
  }

  function applyOne(wrap) {
    if (!wrap || wrap.closest('.ips-proposal-preview-root, .ips-login-page-marker')) return;
    if (wrap.classList && wrap.classList.contains('st-key-users_table_wrap')) return;
    var scaler = getScaler(wrap);
    if (!scaler) return;
    resetWrap(wrap, scaler);
    var available = getAvailable(wrap);
    var needed = measureNeeded(scaler, wrap);
    if (!available || !needed || needed <= available + 2) return;
    var scale = Math.max(MIN_SCALE, available / needed);
    if (scale >= 0.995) return;
    wrap.classList.add('ips-table-fit-host', 'ips-table-fit-scaled');
    scaler.style.transformOrigin = 'top left';
    scaler.style.transform = 'scale(' + scale + ')';
    scaler.style.width = needed + 'px';
    var h = (scaler.offsetHeight || scaler.scrollHeight) * scale;
    wrap.style.minHeight = Math.ceil(h + 6) + 'px';
    wrap.dataset.ipsTableFitScale = String(scale);
    applyTkExpandInverse(wrap, scale);
  }

  function runAll() {
    var seen = new Set();
    function each(sel) {
      doc.querySelectorAll(sel).forEach(function (node) {
        if (seen.has(node)) return;
        seen.add(node);
        applyOne(node);
      });
    }
    each(WRAP_SEL);
    each(SCROLL_SEL);
    each(DATAFRAME_SEL);
  }

  var scheduled = false;
  function schedule() {
    if (scheduled) return;
    scheduled = true;
    w.requestAnimationFrame(function () {
      scheduled = false;
      runAll();
    });
  }

  schedule();
  w.addEventListener('resize', schedule);
  if (!w.__ipsTableViewportFitObserver) {
    w.__ipsTableViewportFitObserver = new MutationObserver(schedule);
    w.__ipsTableViewportFitObserver.observe(doc.body, { childList: true, subtree: true });
  }
})();
</script>
"""
    try:
        components.html(html_doc, height=0, key="ips_table_viewport_fit_v2")
    except TypeError:
        components.html(html_doc, height=0)


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


def inject_trailer_dashboard_css() -> None:
    """Mobile tool trailer dashboard (field supervisors, iPad/phone)."""
    st.markdown(
        """
<style id="ips-trailer-dashboard-v1">
.ips-trailer-dash-title {
  font-size: 1.4rem;
  font-weight: 800;
  color: #0f172a;
  text-align: center;
  margin-bottom: 2px;
}
.ips-trailer-dash-sub {
  font-size: 0.95rem;
  font-weight: 700;
  color: #2563eb;
  text-align: center;
  margin-bottom: 12px;
}
.ips-trailer-dash-hero {
  width: 100%;
  max-width: 420px;
  max-height: 220px;
  object-fit: cover;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  display: block;
  margin: 0 auto 12px;
}
.ips-trailer-dash-cards {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin: 12px 0 16px;
}
.ips-trailer-dash-card {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 10px 12px;
  background: #f8fafc;
}
.ips-trailer-dash-card-label {
  font-size: 0.72rem;
  font-weight: 700;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.ips-trailer-dash-card-value {
  font-size: 0.92rem;
  font-weight: 800;
  color: #0f172a;
  margin-top: 4px;
  line-height: 1.25;
}
.ips-trailer-inv-row,
.ips-trailer-history-row {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px 12px;
  margin-bottom: 8px;
  background: #fff;
}
.ips-trailer-muted {
  color: #64748b;
  font-size: 0.85rem;
}
.ips-trailer-history-kind {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  background: #e0f2fe;
  color: #0369a1;
  font-size: 0.72rem;
  font-weight: 800;
}
div[data-testid="stVerticalBlock"]:has(span.ips-trailer-dash-scope) button {
  min-height: 46px !important;
  font-size: 0.92rem !important;
  font-weight: 700 !important;
}
div[data-testid="stVerticalBlock"]:has(span.ips-trailer-dash-scope) input,
div[data-testid="stVerticalBlock"]:has(span.ips-trailer-dash-scope) textarea {
  min-height: 44px !important;
  font-size: 1rem !important;
}
@media (max-width: 640px) {
  .ips-trailer-dash-cards {
    grid-template-columns: 1fr;
  }
}
</style>
""",
        unsafe_allow_html=True,
    )


def inject_assets_module_css() -> None:
    """Assets list custom table styling."""
    checkbox_css = _list_table_checkbox_column_css("assets_table_wrap")
    checkbox_css_small = _list_table_checkbox_column_css("assets_small_tools_table_wrap")
    ast_list_wrap = ".st-key-assets_table_wrap, .st-key-assets_small_tools_table_wrap"
    assets_equipment_grid = (
        "40px 88px minmax(360px, 2fr) minmax(150px, 0.9fr) minmax(150px, 0.9fr) "
        "minmax(120px, 0.8fr) minmax(150px, 0.9fr) minmax(160px, 0.9fr)"
    )
    assets_serialized_grid = (
        "40px 52px minmax(160px, 1.8fr) minmax(100px, 0.9fr) minmax(110px, 1fr) "
        "minmax(100px, 0.95fr) minmax(110px, 1fr) minmax(90px, 0.8fr) minmax(90px, 0.8fr)"
    )
    ast_grid_rows = (
        ".st-key-assets_table_wrap [data-testid=\"stVerticalBlock\"] > [data-testid=\"stHorizontalBlock\"], "
        ".st-key-assets_table_wrap [data-testid=\"stVerticalBlock\"] > [data-testid=\"stElementContainer\"] > [data-testid=\"stHorizontalBlock\"], "
        ".st-key-assets_small_tools_table_wrap [data-testid=\"stVerticalBlock\"] > [data-testid=\"stHorizontalBlock\"], "
        ".st-key-assets_small_tools_table_wrap [data-testid=\"stVerticalBlock\"] > [data-testid=\"stElementContainer\"] > [data-testid=\"stHorizontalBlock\"]"
    )
    ast_grid_cols = (
        ".st-key-assets_table_wrap [data-testid=\"stVerticalBlock\"] > [data-testid=\"stHorizontalBlock\"] > [data-testid=\"column\"], "
        ".st-key-assets_table_wrap [data-testid=\"stVerticalBlock\"] > [data-testid=\"stElementContainer\"] > [data-testid=\"stHorizontalBlock\"] > [data-testid=\"column\"], "
        ".st-key-assets_small_tools_table_wrap [data-testid=\"stVerticalBlock\"] > [data-testid=\"stHorizontalBlock\"] > [data-testid=\"column\"], "
        ".st-key-assets_small_tools_table_wrap [data-testid=\"stVerticalBlock\"] > [data-testid=\"stElementContainer\"] > [data-testid=\"stHorizontalBlock\"] > [data-testid=\"column\"]"
    )
    st.markdown(
        f"""
<style id="ips-assets-module-v19">
.ips-assets-table-wrap,
.ips-assets-table-wrap.asset-table {{
  background: #ffffff;
  border: 1px solid #dbe3ef;
  border-radius: 12px;
  overflow: hidden;
  margin-bottom: 0.5rem;
  width: 100%;
  max-width: 100%;
}}
.ips-assets-value {{
  text-align: right;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}}
.st-key-assets_table_wrap .ips-assets-name-cell-wrap,
.st-key-assets_table_wrap .asset-name-cell {{
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.2rem;
  min-width: 0;
  width: 100%;
  max-width: 100%;
  overflow: hidden;
}}
.st-key-assets_table_wrap .ips-assets-name-cell-link {{
  cursor: pointer;
  min-height: 2.25rem;
  padding: 0.12rem 0;
  border-radius: 6px;
  box-sizing: border-box;
}}
.st-key-assets_table_wrap .ips-assets-name-cell-link .ips-assets-name-badges,
.st-key-assets_table_wrap .ips-assets-name-cell-link .ips-asset-rental-badge {{
  pointer-events: none;
  cursor: default;
}}
.st-key-assets_table_wrap a.asset-name-link,
.st-key-assets_table_wrap .ips-assets-name-text {{
  font-weight: 600 !important;
  color: {PRIMARY} !important;
  font-size: 0.875rem;
  line-height: 1.25;
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;
  width: 100%;
  max-width: 100%;
  text-decoration: none;
}}
.st-key-assets_table_wrap a.asset-name-link:hover,
.st-key-assets_table_wrap a.asset-name-link:focus,
.st-key-assets_table_wrap .ips-assets-name-cell-link:hover a.asset-name-link,
.st-key-assets_table_wrap .ips-assets-name-cell-link:focus-within a.asset-name-link {{
  color: {PRIMARY_HOVER} !important;
  text-decoration: underline;
}}
.st-key-assets_table_wrap .ips-assets-name-link,
.st-key-assets_table_wrap .asset-name-button {{
  flex: 0 1 auto;
  display: inline-flex;
  align-items: center;
  min-width: 0;
  max-width: 500px;
  width: 100%;
  overflow: hidden;
}}
.st-key-assets_table_wrap .ips-assets-name-link [data-testid="stButton"],
.st-key-assets_table_wrap .ips-assets-name-link .stButton,
.st-key-assets_table_wrap .asset-name-button [data-testid="stButton"],
.st-key-assets_table_wrap .asset-name-button .stButton,
.st-key-assets_table_wrap [class*="st-key-assets_open_"] [data-testid="stButton"],
.st-key-assets_table_wrap [class*="st-key-assets_open_"] .stButton {{
  width: 100%;
  max-width: 500px;
  min-width: 0;
  margin: 0;
}}
.st-key-assets_table_wrap .ips-assets-name-link button,
.st-key-assets_table_wrap .asset-name-link button,
.st-key-assets_table_wrap .asset-name-button button,
.st-key-assets_table_wrap [class*="st-key-assets_open_"] button {{
  background: transparent !important;
  background-color: transparent !important;
  color: {PRIMARY};
  font-weight: 600;
  font-size: 0.875rem;
  border: none !important;
  border-radius: 0;
  padding: 0;
  height: auto;
  min-height: 0;
  max-height: none;
  width: auto;
  max-width: 100%;
  min-width: 0;
  box-shadow: none !important;
  outline: none;
  text-align: left;
  justify-content: flex-start;
  display: inline-flex;
  align-items: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  word-break: normal;
  overflow-wrap: normal;
  cursor: pointer;
  transition: color 0.15s ease;
}}
.st-key-assets_table_wrap .ips-assets-name-link button:hover,
.st-key-assets_table_wrap .ips-assets-name-link button:focus,
.st-key-assets_table_wrap .asset-name-link button:hover,
.st-key-assets_table_wrap .asset-name-link button:focus,
.st-key-assets_table_wrap .asset-name-button button:hover,
.st-key-assets_table_wrap .asset-name-button button:focus,
.st-key-assets_table_wrap [class*="st-key-assets_open_"] button:hover,
.st-key-assets_table_wrap [class*="st-key-assets_open_"] button:focus {{
  background: transparent !important;
  background-color: transparent !important;
  color: {PRIMARY_HOVER};
  text-decoration: underline;
  border: none !important;
  box-shadow: none !important;
}}
.st-key-assets_table_wrap .ips-assets-name-link button > div,
.st-key-assets_table_wrap .ips-assets-name-link button p,
.st-key-assets_table_wrap .ips-assets-name-link button span,
.st-key-assets_table_wrap .asset-name-link button > div,
.st-key-assets_table_wrap .asset-name-link button p,
.st-key-assets_table_wrap .asset-name-link button span,
.st-key-assets_table_wrap .asset-name-button button > div,
.st-key-assets_table_wrap .asset-name-button button p,
.st-key-assets_table_wrap .asset-name-button button span {{
  display: inline;
  color: inherit;
  font-weight: 600;
  width: auto;
  max-width: 100%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  text-align: left;
}}
.st-key-assets_table_wrap .asset-name-cell,
.st-key-assets_table_wrap .asset-name-button,
.st-key-assets_table_wrap .asset-category-cell,
.st-key-assets_table_wrap .asset-actions-cell,
.st-key-assets_table_wrap .asset-actions-button {{
  white-space: nowrap;
}}
.st-key-assets_table_wrap .asset-category-cell {{
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 150px;
}}
.st-key-assets_table_wrap .asset-actions-button {{
  min-width: 96px;
  white-space: nowrap;
}}
.st-key-assets_table_wrap .ips-assets-name-badges {{
  flex: 0 0 auto;
}}
{ast_list_wrap} [data-testid="stVerticalBlock"] {{
  gap: 0 !important;
  width: 100% !important;
  max-width: 100% !important;
  background: #ffffff !important;
}}
{ast_grid_rows} {{
  display: grid !important;
  column-gap: 0 !important;
  row-gap: 0 !important;
  gap: 0 !important;
  align-items: center !important;
  border-bottom: 1px solid #e2e8f0;
  padding: 0 !important;
  margin: 0 !important;
  min-height: 60px;
  width: 100% !important;
  min-width: 0 !important;
  max-width: 100% !important;
  box-sizing: border-box !important;
  flex-wrap: nowrap !important;
  background: #ffffff !important;
}}
.st-key-assets_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"],
.st-key-assets_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] > [data-testid="stHorizontalBlock"] {{
  grid-template-columns: {assets_equipment_grid} !important;
  column-gap: 16px !important;
}}
.st-key-assets_small_tools_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"],
.st-key-assets_small_tools_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] > [data-testid="stHorizontalBlock"] {{
  grid-template-columns: {assets_serialized_grid} !important;
}}
{ast_grid_cols} {{
  flex: unset !important;
  flex-grow: 0 !important;
  flex-shrink: 0 !important;
  width: auto !important;
  min-width: 0 !important;
  max-width: none !important;
  margin: 0 !important;
  padding: 0 10px !important;
  display: flex !important;
  align-items: center !important;
  align-self: stretch !important;
  overflow: hidden !important;
  justify-content: flex-start !important;
  box-sizing: border-box !important;
}}
{ast_grid_cols}:nth-child(1) {{
  flex: 0 0 40px !important;
  width: 40px !important;
  min-width: 40px !important;
  max-width: 40px !important;
  padding: 0 !important;
  justify-content: center !important;
  overflow: visible !important;
}}
{ast_grid_cols}:nth-child(2) {{
  flex: 0 0 52px !important;
  width: 52px !important;
  min-width: 52px !important;
  max-width: 52px !important;
  padding: 0 6px !important;
  justify-content: center !important;
}}
.st-key-assets_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(2),
.st-key-assets_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] > [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(2) {{
  flex: 0 0 80px !important;
  width: 80px !important;
  min-width: 80px !important;
  max-width: 80px !important;
}}
.st-key-assets_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(3),
.st-key-assets_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] > [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(3) {{
  flex: 0 0 auto !important;
  min-width: 360px !important;
  max-width: none !important;
  overflow: hidden !important;
}}
.st-key-assets_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(3) > [data-testid="stVerticalBlock"],
.st-key-assets_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] > [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(3) > [data-testid="stVerticalBlock"] {{
  min-width: 360px !important;
  max-width: 100% !important;
  overflow: hidden !important;
}}
.st-key-assets_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(4),
.st-key-assets_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] > [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(4) {{
  flex: 0 0 auto !important;
  min-width: 150px !important;
  overflow: hidden !important;
}}
.st-key-assets_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(4) > [data-testid="stVerticalBlock"],
.st-key-assets_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] > [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(4) > [data-testid="stVerticalBlock"] {{
  min-width: 150px !important;
  max-width: 100% !important;
  overflow: hidden !important;
}}
.st-key-assets_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(9),
.st-key-assets_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] > [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(9),
.st-key-assets_table_wrap [data-testid="column"]:has(.ips-assets-actions-cell),
.st-key-assets_table_wrap [data-testid="column"]:has(.ips-assets-actions-header-cell) {{
  flex: 0 0 120px !important;
  width: 120px !important;
  min-width: 120px !important;
  max-width: 120px !important;
  padding: 0 8px !important;
  justify-content: flex-end !important;
  overflow: visible !important;
}}
.st-key-assets_table_wrap [data-testid="column"]:has(.ips-assets-actions-cell) > [data-testid="stVerticalBlock"] {{
  display: flex !important;
  flex-direction: row !important;
  flex-wrap: nowrap !important;
  align-items: center !important;
  justify-content: flex-end !important;
  gap: 8px !important;
  width: 120px !important;
  min-width: 120px !important;
  max-width: 120px !important;
  overflow: visible !important;
}}
.st-key-assets_table_wrap [data-testid="column"]:has(.ips-assets-actions-cell) > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:has(.ips-assets-actions-cell) {{
  flex: 0 0 0 !important;
  width: 0 !important;
  min-width: 0 !important;
  max-width: 0 !important;
  overflow: hidden !important;
  margin: 0 !important;
  padding: 0 !important;
}}
.st-key-assets_table_wrap [data-testid="column"]:has(.ips-assets-actions-cell) > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"],
.st-key-assets_table_wrap [data-testid="column"]:has(.ips-assets-actions-cell) > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] {{
  flex: 0 0 auto !important;
  width: auto !important;
  min-width: 0 !important;
  max-width: none !important;
  overflow: visible !important;
}}
.st-key-assets_table_wrap [data-testid="column"]:has(.ips-assets-actions-cell) > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] {{
  display: flex !important;
  flex-direction: row !important;
  flex-wrap: nowrap !important;
  align-items: center !important;
  justify-content: flex-end !important;
  gap: 8px !important;
  width: auto !important;
  min-width: 0 !important;
  max-width: none !important;
}}
.st-key-assets_table_wrap [data-testid="column"]:has(.ips-assets-actions-cell) > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] > [data-testid="column"] {{
  flex: 0 0 auto !important;
  width: auto !important;
  min-width: 88px !important;
  max-width: none !important;
  overflow: visible !important;
  padding: 0 !important;
}}
.st-key-assets_table_wrap [data-testid="column"]:has(.ips-assets-actions-cell) > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] > [data-testid="column"]:has(.asset-row-actions-menu) {{
  min-width: 108px !important;
}}
.st-key-assets_table_wrap [data-testid="column"]:has(.ips-assets-actions-cell) [class*="st-key-ast_open_"] [data-testid="stButton"],
.st-key-assets_table_wrap [data-testid="column"]:has(.ips-assets-actions-cell) [class*="st-key-ast_open_"] .stButton,
.st-key-assets_table_wrap [data-testid="column"]:has(.ips-assets-actions-cell) [data-testid="stPopover"] {{
  flex: 0 0 auto !important;
  width: auto !important;
  min-width: 0 !important;
  max-width: none !important;
  overflow: visible !important;
}}
.st-key-assets_table_wrap [data-testid="column"]:has(.ips-assets-actions-cell) [class*="st-key-ast_open_"] [data-testid="stButton"] > button,
.st-key-assets_table_wrap [data-testid="column"]:has(.ips-assets-actions-cell) [class*="st-key-ast_open_"] .stButton > button {{
  background: #2563eb !important;
  color: #ffffff !important;
  border: 1px solid #2563eb !important;
  border-radius: 8px !important;
  height: 36px !important;
  min-height: 36px !important;
  width: 88px !important;
  min-width: 88px !important;
  max-width: 88px !important;
  padding: 0 12px !important;
  white-space: nowrap !important;
  word-break: keep-all !important;
  overflow-wrap: normal !important;
  writing-mode: horizontal-tb !important;
  display: inline-flex !important;
  flex-direction: row !important;
  flex-wrap: nowrap !important;
  align-items: center !important;
  justify-content: center !important;
}}
.st-key-assets_table_wrap [data-testid="column"]:has(.asset-actions-cell) button[data-testid="stBaseButton-popover"],
.st-key-assets_table_wrap [data-testid="column"]:has(.asset-actions-cell) [data-testid="column"]:has(.asset-row-actions-menu) button[data-testid="stBaseButton-popover"],
.st-key-assets_table_wrap [data-testid="column"]:has(.asset-actions-cell) button[data-testid="stBaseButton-popover"],
.st-key-assets_table_wrap [data-testid="column"]:has(.asset-actions-button) button[data-testid="stBaseButton-popover"],
.st-key-assets_table_wrap [data-testid="column"]:has(.asset-actions-cell) button[data-testid="stBaseButton-primary"],
.st-key-assets_table_wrap [data-testid="column"]:has(.asset-actions-cell) [data-testid="column"]:has(.asset-row-actions-menu) button[data-testid="stBaseButton-primary"],
.st-key-assets_table_wrap [data-testid="column"]:has(.asset-actions-button) button[data-testid="stBaseButton-primary"] {{
  display: inline-flex !important;
  flex-direction: row !important;
  flex-wrap: nowrap !important;
  align-items: center !important;
  justify-content: center !important;
  min-height: 36px !important;
  height: 36px !important;
  min-width: 100px !important;
  width: auto !important;
  max-width: none !important;
  padding: 0 0.85rem !important;
  border-radius: 8px !important;
  background: {PRIMARY} !important;
  border: 1px solid {PRIMARY} !important;
  box-shadow: 0 1px 2px rgba(37, 99, 235, 0.24) !important;
  color: #ffffff !important;
  font-size: 0.8125rem !important;
  font-weight: 600 !important;
  line-height: 1.1 !important;
  white-space: nowrap !important;
  word-break: keep-all !important;
  overflow-wrap: normal !important;
  writing-mode: horizontal-tb !important;
}}
.st-key-assets_table_wrap [data-testid="column"]:has(.asset-actions-cell) button[data-testid="stBaseButton-popover"]:hover,
.st-key-assets_table_wrap [data-testid="column"]:has(.asset-actions-cell) [data-testid="column"]:has(.asset-row-actions-menu) button[data-testid="stBaseButton-popover"]:hover,
.st-key-assets_table_wrap [data-testid="column"]:has(.asset-actions-cell) button[data-testid="stBaseButton-primary"]:hover,
.st-key-assets_table_wrap [data-testid="column"]:has(.asset-actions-cell) [data-testid="column"]:has(.asset-row-actions-menu) button[data-testid="stBaseButton-primary"]:hover {{
  background: {PRIMARY_HOVER} !important;
  border-color: {PRIMARY_HOVER} !important;
  color: #ffffff !important;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.28) !important;
}}
.st-key-assets_table_wrap [data-testid="column"]:has(.ips-assets-actions-cell) button[data-testid="stBaseButton-popover"] > div,
.st-key-assets_table_wrap [data-testid="column"]:has(.ips-assets-actions-cell) button[data-testid="stBaseButton-primary"] > div,
.st-key-assets_table_wrap [data-testid="column"]:has(.ips-assets-actions-cell) [data-testid="column"]:has(.asset-row-actions-menu) button[data-testid="stBaseButton-popover"] > div,
.st-key-assets_table_wrap [data-testid="column"]:has(.ips-assets-actions-cell) [data-testid="column"]:has(.asset-row-actions-menu) button[data-testid="stBaseButton-primary"] > div,
.st-key-assets_table_wrap [data-testid="column"]:has(.ips-assets-actions-cell) [class*="st-key-ast_open_"] [data-testid="stButton"] > button > div,
.st-key-assets_table_wrap [data-testid="column"]:has(.ips-assets-actions-cell) [class*="st-key-ast_open_"] .stButton > button > div {{
  display: inline-flex !important;
  flex-direction: row !important;
  flex-wrap: nowrap !important;
  align-items: center !important;
  justify-content: center !important;
  width: auto !important;
  max-width: none !important;
  white-space: nowrap !important;
  word-break: keep-all !important;
  overflow-wrap: normal !important;
  writing-mode: horizontal-tb !important;
}}
.st-key-assets_table_wrap [data-testid="column"]:has(.ips-assets-actions-cell) button[data-testid="stBaseButton-popover"] p,
.st-key-assets_table_wrap [data-testid="column"]:has(.ips-assets-actions-cell) button[data-testid="stBaseButton-popover"] span,
.st-key-assets_table_wrap [data-testid="column"]:has(.ips-assets-actions-cell) button[data-testid="stBaseButton-primary"] p,
.st-key-assets_table_wrap [data-testid="column"]:has(.ips-assets-actions-cell) button[data-testid="stBaseButton-primary"] span,
.st-key-assets_table_wrap [data-testid="column"]:has(.ips-assets-actions-cell) button[data-testid="stBaseButton-popover"] div,
.st-key-assets_table_wrap [data-testid="column"]:has(.ips-assets-actions-cell) [data-testid="column"]:has(.asset-row-actions-menu) button[data-testid="stBaseButton-popover"] p,
.st-key-assets_table_wrap [data-testid="column"]:has(.ips-assets-actions-cell) [data-testid="column"]:has(.asset-row-actions-menu) button[data-testid="stBaseButton-popover"] span,
.st-key-assets_table_wrap [data-testid="column"]:has(.ips-assets-actions-cell) [data-testid="column"]:has(.asset-row-actions-menu) button[data-testid="stBaseButton-primary"] p,
.st-key-assets_table_wrap [data-testid="column"]:has(.ips-assets-actions-cell) [data-testid="column"]:has(.asset-row-actions-menu) button[data-testid="stBaseButton-primary"] span,
.st-key-assets_table_wrap [data-testid="column"]:has(.ips-assets-actions-cell) [data-testid="column"]:has(.asset-row-actions-menu) button[data-testid="stBaseButton-popover"] div,
.st-key-assets_table_wrap [data-testid="column"]:has(.ips-assets-actions-cell) [class*="st-key-ast_open_"] [data-testid="stButton"] > button p,
.st-key-assets_table_wrap [data-testid="column"]:has(.ips-assets-actions-cell) [class*="st-key-ast_open_"] [data-testid="stButton"] > button span,
.st-key-assets_table_wrap [data-testid="column"]:has(.ips-assets-actions-cell) [class*="st-key-ast_open_"] .stButton > button p,
.st-key-assets_table_wrap [data-testid="column"]:has(.ips-assets-actions-cell) [class*="st-key-ast_open_"] .stButton > button span {{
  display: inline !important;
  white-space: nowrap !important;
  word-break: keep-all !important;
  overflow-wrap: normal !important;
}}
{ast_grid_cols} > [data-testid="stVerticalBlock"] {{
  width: 100% !important;
  min-width: 0 !important;
  max-width: 100% !important;
  justify-content: inherit !important;
  align-items: center !important;
  padding: 0 !important;
  margin: 0 !important;
  gap: 0 !important;
}}
{ast_grid_cols}:nth-child(1) > [data-testid="stVerticalBlock"] {{
  width: 40px !important;
  min-width: 40px !important;
  max-width: 40px !important;
  justify-content: center !important;
  align-items: center !important;
}}
{ast_grid_cols}:nth-child(9) > [data-testid="stVerticalBlock"] {{
  width: 120px !important;
  min-width: 120px !important;
  max-width: 120px !important;
  overflow: visible !important;
  justify-content: flex-end !important;
  align-items: center !important;
  gap: 8px !important;
}}
{ast_list_wrap} [data-testid="stMarkdownContainer"],
{ast_list_wrap} .stMarkdown,
{ast_list_wrap} .stMarkdown p {{
  margin: 0 !important;
  padding: 0 !important;
}}
{ast_list_wrap} .stMarkdown p:has(.ips-asset-thumb-cell) {{
  line-height: 0 !important;
}}
{ast_list_wrap} [data-testid="stHorizontalBlock"]:has(.ips-assets-table-header-marker),
{ast_list_wrap} [data-testid="stHorizontalBlock"]:first-of-type {{
  background: #ffffff !important;
  min-height: 40px !important;
}}
{ast_list_wrap} [data-testid="stHorizontalBlock"]:not(:first-of-type):hover {{
  background: #f8fafc;
}}
{ast_list_wrap} [data-testid="stHorizontalBlock"]:has([data-testid="stCheckbox"] input:checked) {{
  background: #eaf2ff !important;
}}
{ast_list_wrap} [data-testid="stElementContainer"] {{
  margin-top: 0 !important;
  margin-bottom: 0 !important;
  padding-top: 0 !important;
  padding-bottom: 0 !important;
}}
{ast_list_wrap} [data-testid="stCheckbox"] {{
  margin: 0 !important;
}}
{checkbox_css_small}
.st-key-assets_small_tools_table_wrap [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(3) .ips-assets-title {{
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  white-space: nowrap !important;
}}
.st-key-assets_small_tools_table_wrap [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(4) .ips-assets-number,
.st-key-assets_small_tools_table_wrap [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(5) .ips-assets-number {{
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}}
.st-key-assets_small_tools_table_wrap [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(6) .ips-assets-muted {{
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  white-space: nowrap !important;
}}
.ips-assets-header-row {{
  background: transparent !important;
  border: none !important;
  padding: 0 !important;
  margin: 0 !important;
  font-size: 11px;
  font-weight: 800;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  min-height: 0 !important;
  width: 100%;
  display: flex;
  align-items: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
.ips-assets-table-header-marker {{
  display: none !important;
}}
.ips-assets-row {{
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  padding: 6px 10px;
  min-height: 52px;
}}
.ips-assets-row:hover {{
  background: #f8fafc;
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
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
.ips-asset-rentable-badge {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-left: 0.45rem;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  font-size: 0.65rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #ffffff;
  background: linear-gradient(135deg, #0d9488 0%, #0f766e 100%);
  border: 1px solid #0f766e;
  box-shadow: 0 1px 3px rgba(15, 118, 110, 0.35);
  vertical-align: middle;
  white-space: nowrap;
}}
.ips-assets-name-text {{
  font-weight: 700;
  color: {PRIMARY};
  font-size: 0.875rem;
  line-height: 1.25;
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: inline-block;
  max-width: 100%;
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
.ips-asset-thumb-cell {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  vertical-align: middle;
  flex-shrink: 0;
}}
.ips-asset-thumb-img {{
  display: block;
  width: 44px !important;
  height: 44px !important;
  object-fit: cover;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #ffffff;
}}
.ips-asset-thumb-placeholder {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
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
{checkbox_css}
.st-key-assets_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-assets-equipment-table-header) > [data-testid="column"]:first-child,
.st-key-assets_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-assets-equipment-table-row) > [data-testid="column"]:first-child {{
  flex: 0 0 72px !important;
  width: 72px !important;
  min-width: 72px !important;
  max-width: 72px !important;
}}
.st-key-assets_small_tools_table_wrap [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child {{
  flex: 0 0 40px !important;
  width: 40px !important;
  min-width: 40px !important;
  max-width: 40px !important;
}}
{ast_list_wrap} .stButton > button {{
  height: 32px !important;
  min-height: 32px !important;
  padding: 0 12px !important;
  border-radius: 9px !important;
  font-size: 14px !important;
  width: auto !important;
}}
.st-key-assets_table_wrap .ips-assets-name-link .stButton > button,
.st-key-assets_table_wrap .asset-name-button .stButton > button,
.st-key-assets_table_wrap .asset-name-link .stButton > button {{
  height: auto !important;
  min-height: 0 !important;
  padding: 0 !important;
  border: none !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  background: transparent !important;
  background-color: transparent !important;
  color: {PRIMARY} !important;
  font-weight: 600 !important;
}}
.st-key-assets_table_wrap .ips-assets-name-link .stButton > button:hover,
.st-key-assets_table_wrap .asset-name-button .stButton > button:hover,
.st-key-assets_table_wrap .asset-name-link .stButton > button:hover {{
  background: transparent !important;
  color: {PRIMARY_HOVER} !important;
  text-decoration: underline !important;
}}
.ips-asset-doc-upload-zone-marker + [data-testid="stFileUploader"] {{
  border: 2px dashed #cbd5e1;
  border-radius: 10px;
  padding: 12px;
  background: #f8fafc;
}}
.ips-asset-doc-table-head {{
  display: grid;
  grid-template-columns: 2.4fr 0.55fr 1fr 0.85fr 0.65fr 0.55fr;
  gap: 8px;
  padding: 8px 10px;
  margin-top: 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px 8px 0 0;
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  color: #64748b;
}}
.ips-asset-doc-name,
.ips-asset-doc-cell {{
  margin: 0;
  font-size: 0.84rem;
  color: #334155;
}}
.ips-asset-doc-name {{
  font-weight: 600;
}}
div[data-testid="stPopover"]:has(.asset-row-actions-panel) {{
  background: #ffffff !important;
  border: 1px solid #dbe3ef !important;
  border-radius: 12px !important;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.12) !important;
  overflow: hidden !important;
}}
body:has(.asset-row-actions-panel) div[data-baseweb="popover"],
div[data-baseweb="popover"]:has(.asset-row-actions-panel) {{
  background: #ffffff !important;
  background-color: #ffffff !important;
  border: 1px solid #dbe3ef !important;
  border-radius: 12px !important;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.12) !important;
  overflow: hidden !important;
}}
div[data-testid="stPopoverBody"]:has(.asset-row-actions-panel) {{
  padding: 0.5rem !important;
  min-width: 280px !important;
  max-width: 340px !important;
  width: 300px !important;
  background: #ffffff !important;
  background-color: #ffffff !important;
  border: none !important;
  border-radius: 12px !important;
  box-shadow: none !important;
  color: #0f172a !important;
}}
div[data-testid="stPopoverBody"]:has(.asset-row-actions-panel) [data-testid="stVerticalBlock"],
div[data-testid="stPopoverBody"]:has(.asset-row-actions-panel) [data-testid="stVerticalBlockBorderWrapper"],
div[data-testid="stPopoverBody"]:has(.asset-row-actions-panel) [data-testid="stElementContainer"],
div[data-baseweb="popover"]:has(.asset-row-actions-panel) [data-testid="stVerticalBlock"],
div[data-baseweb="popover"]:has(.asset-row-actions-panel) [data-testid="stVerticalBlockBorderWrapper"],
div[data-baseweb="popover"]:has(.asset-row-actions-panel) [data-testid="stElementContainer"] {{
  background: #ffffff !important;
  background-color: #ffffff !important;
  border-color: transparent !important;
}}
div[data-testid="stPopoverBody"]:has(.asset-row-actions-panel) [data-testid="stVerticalBlock"] {{
  gap: 0.2rem !important;
}}
div[data-testid="stPopoverBody"]:has(.asset-row-actions-panel) .asset-row-actions-divider {{
  border: none !important;
  border-top: 1px solid #e8edf3 !important;
  margin: 0.45rem 0 !important;
  height: 0 !important;
  opacity: 1 !important;
}}
div[data-testid="stPopoverBody"]:has(.asset-row-actions-panel) .asset-row-actions-section {{
  margin: 0.15rem 0 0.25rem 0 !important;
  padding: 0 0.15rem !important;
}}
div[data-testid="stPopoverBody"]:has(.asset-row-actions-panel) .asset-row-actions-section-title {{
  margin: 0 !important;
  padding: 0.15rem 0.35rem 0.1rem 1.85rem !important;
  font-size: 0.8125rem !important;
  font-weight: 700 !important;
  color: #0f172a !important;
  line-height: 1.25 !important;
  position: relative !important;
}}
div[data-testid="stPopoverBody"]:has(.asset-row-actions-panel) .asset-row-actions-section-title::before {{
  content: "" !important;
  position: absolute !important;
  left: 0.35rem !important;
  top: 50% !important;
  transform: translateY(-50%) !important;
  width: 18px !important;
  height: 18px !important;
  background: center / contain no-repeat url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='%232563eb' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M16.5 9.4l-9-5.19M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z'/%3E%3Cpath d='M3.27 6.96L12 12.01l8.73-5.05M12 22.08V12'/%3E%3C/svg%3E") !important;
}}
div[data-testid="stPopoverBody"]:has(.asset-row-actions-panel) [data-testid="stSelectbox"] {{
  margin: 0 !important;
  padding: 0 0.15rem 0.35rem !important;
}}
div[data-testid="stPopoverBody"]:has(.asset-row-actions-panel) [data-testid="stSelectbox"] label {{
  font-size: 0.75rem !important;
  font-weight: 500 !important;
  color: #64748b !important;
  margin-bottom: 0.35rem !important;
}}
div[data-testid="stPopoverBody"]:has(.asset-row-actions-panel) [data-testid="stSelectbox"] [data-baseweb="select"] > div {{
  min-height: 42px !important;
  border-color: #dbe3ef !important;
  border-radius: 8px !important;
  background: #ffffff !important;
  box-shadow: none !important;
}}
div[data-testid="stPopoverBody"]:has(.asset-row-actions-panel) [data-testid="stSelectbox"] [data-baseweb="select"] span {{
  color: #0f172a !important;
  font-weight: 600 !important;
  font-size: 0.875rem !important;
}}
div[data-testid="stPopoverBody"]:has(.asset-row-actions-panel) .asset-row-actions-trailer-select {{
  display: none !important;
}}
div[data-testid="stPopoverBody"]:has(.asset-row-actions-panel) .stButton,
div[data-testid="stPopoverBody"]:has(.asset-row-actions-panel) [data-testid="stButton"] {{
  margin: 0 !important;
  padding: 0 !important;
}}
div[data-testid="stPopoverBody"]:has(.asset-row-actions-panel) .stButton > button,
div[data-testid="stPopoverBody"]:has(.asset-row-actions-panel) [data-testid="stButton"] > button {{
  justify-content: flex-start !important;
  text-align: left !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  color: #0f172a !important;
  font-weight: 600 !important;
  font-size: 0.875rem !important;
  min-height: 44px !important;
  height: 44px !important;
  padding: 0 0.75rem 0 2.15rem !important;
  border-radius: 8px !important;
  white-space: nowrap !important;
  word-break: keep-all !important;
  overflow-wrap: normal !important;
  position: relative !important;
}}
div[data-testid="stPopoverBody"]:has(.asset-row-actions-panel) .stButton > button:hover,
div[data-testid="stPopoverBody"]:has(.asset-row-actions-panel) [data-testid="stButton"] > button:hover {{
  background: #f8fafc !important;
  color: #0f172a !important;
}}
div[data-testid="stPopoverBody"]:has(.asset-row-actions-panel) .stButton > button:focus-visible,
div[data-testid="stPopoverBody"]:has(.asset-row-actions-panel) [data-testid="stButton"] > button:focus-visible {{
  outline: 2px solid #2563eb !important;
  outline-offset: 1px !important;
}}
div[data-testid="stPopoverBody"]:has(.asset-row-actions-panel) [data-testid="stElementContainer"]:has(.asset-row-action-view) + [data-testid="stElementContainer"] [data-testid="stButton"] > button::before {{
  content: "" !important;
  position: absolute !important;
  left: 0.75rem !important;
  top: 50% !important;
  transform: translateY(-50%) !important;
  width: 18px !important;
  height: 18px !important;
  background: center / contain no-repeat url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='%232563eb' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z'/%3E%3Ccircle cx='12' cy='12' r='3'/%3E%3C/svg%3E") !important;
}}
div[data-testid="stPopoverBody"]:has(.asset-row-actions-panel) [data-testid="stElementContainer"]:has(.asset-row-action-edit) + [data-testid="stElementContainer"] [data-testid="stButton"] > button::before {{
  content: "" !important;
  position: absolute !important;
  left: 0.75rem !important;
  top: 50% !important;
  transform: translateY(-50%) !important;
  width: 18px !important;
  height: 18px !important;
  background: center / contain no-repeat url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='%232563eb' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M12 20h9'/%3E%3Cpath d='M16.5 3.5a2.121 2.121 0 013 3L7 19l-4 1 1-4L16.5 3.5z'/%3E%3C/svg%3E") !important;
}}
div[data-testid="stPopoverBody"]:has(.asset-row-actions-panel) [data-testid="stElementContainer"]:has(.asset-row-action-change-type) + [data-testid="stElementContainer"] [data-testid="stButton"] > button::before {{
  content: "" !important;
  position: absolute !important;
  left: 0.75rem !important;
  top: 50% !important;
  transform: translateY(-50%) !important;
  width: 18px !important;
  height: 18px !important;
  background: center / contain no-repeat url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='%232563eb' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M7 16l-4-4 4-4'/%3E%3Cpath d='M3 12h14'/%3E%3Cpath d='M17 8l4 4-4 4'/%3E%3Cpath d='M21 12H7'/%3E%3C/svg%3E") !important;
}}
div[data-testid="stPopoverBody"]:has(.asset-row-actions-panel) [data-testid="stElementContainer"]:has(.asset-row-action-assign) + [data-testid="stElementContainer"] [data-testid="stButton"] > button::before {{
  content: "" !important;
  position: absolute !important;
  left: 0.75rem !important;
  top: 50% !important;
  transform: translateY(-50%) !important;
  width: 18px !important;
  height: 18px !important;
  background: center / contain no-repeat url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='%232563eb' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M16.5 9.4l-9-5.19M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z'/%3E%3Cpath d='M3.27 6.96L12 12.01l8.73-5.05M12 22.08V12'/%3E%3C/svg%3E") !important;
}}
div[data-testid="stPopoverBody"]:has(.asset-row-actions-panel) [data-testid="stElementContainer"]:has(.asset-row-action-history) + [data-testid="stElementContainer"] [data-testid="stButton"] > button::before {{
  content: "" !important;
  position: absolute !important;
  left: 0.75rem !important;
  top: 50% !important;
  transform: translateY(-50%) !important;
  width: 18px !important;
  height: 18px !important;
  background: center / contain no-repeat url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='%232563eb' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='12' cy='12' r='10'/%3E%3Cpolyline points='12 6 12 12 16 14'/%3E%3C/svg%3E") !important;
}}
div[data-testid="stPopoverBody"]:has(.asset-row-actions-panel) [data-testid="stElementContainer"]:has(.asset-row-action-delete) + [data-testid="stElementContainer"] [data-testid="stButton"] > button,
div[data-testid="stPopoverBody"]:has(.asset-row-actions-panel) [data-testid="stElementContainer"]:has(.asset-row-action-delete) + [data-testid="stElementContainer"] [data-testid="stButton"] > button:hover {{
  color: #dc2626 !important;
}}
div[data-testid="stPopoverBody"]:has(.asset-row-actions-panel) [data-testid="stElementContainer"]:has(.asset-row-action-delete) + [data-testid="stElementContainer"] [data-testid="stButton"] > button::before {{
  content: "" !important;
  position: absolute !important;
  left: 0.75rem !important;
  top: 50% !important;
  transform: translateY(-50%) !important;
  width: 18px !important;
  height: 18px !important;
  background: center / contain no-repeat url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='%23dc2626' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='3 6 5 6 21 6'/%3E%3Cpath d='M19 6l-1 14H6L5 6'/%3E%3Cpath d='M10 11v6'/%3E%3Cpath d='M14 11v6'/%3E%3Cpath d='M9 6V4h6v2'/%3E%3C/svg%3E") !important;
}}
@media (max-width: 900px) {{
  div[data-testid="stPopoverBody"]:has(.asset-row-actions-panel) {{
    min-width: 280px !important;
    max-width: min(340px, calc(100vw - 1.5rem)) !important;
    width: min(300px, calc(100vw - 1.5rem)) !important;
  }}
}}
section[data-testid="stMain"]:has(.ips-assets-page)
[data-testid="stTabs"] [data-baseweb="tab-panel"][hidden],
section[data-testid="stMain"]:has(.ips-assets-page)
[data-testid="stTabs"] [role="tabpanel"][hidden] {{
  content-visibility: hidden !important;
  contain-intrinsic-size: 0 0 !important;
}}
</style>
""",
        unsafe_allow_html=True,
    )


def _inject_timekeeping_daily_hour_focus_script() -> None:
    """Select-all on focus for List view top-row daily hour inputs only."""
    html_doc = """
<script>
(function () {
  var w = window.parent || window;
  var doc = w.document;
  var WRAP = ".st-key-timekeeping_table_wrap";
  var SELECTOR =
    WRAP + " [class*=\\"st-key-tk_list_hour_spin_\\"] [data-testid=\\"stNumberInput\\"] input, "
    + WRAP + " [class*=\\"st-key-tk_row_\\"] [data-testid=\\"column\\"]:has(.timekeeping-list-daily-hour-marker) "
    + "[data-testid=\\"stNumberInput\\"] input";

  function isListTopRowHourInput(el) {
    if (!el || el.tagName !== "INPUT") return false;
    if (!el.closest(WRAP)) return false;
    if (!el.closest('[class*="st-key-tk_row_"]')) return false;
    if (el.closest('[class*="st-key-tk_expand_detail_"]')) return false;
    if (el.closest(".timekeeping-detail-row-marker, .timekeeping-detail-header-marker")) {
      return false;
    }
    if (el.closest('[class*="st-key-tk_list_hour_spin_"]')) return true;
    var col = el.closest('[data-testid="column"]');
    return !!(col && col.querySelector(".timekeeping-list-daily-hour-marker"));
  }

  function isDigitKey(e) {
    return e.key && e.key.length === 1 && /^[0-9.]$/.test(e.key) && !e.ctrlKey && !e.metaKey && !e.altKey;
  }

  function bindInput(el) {
    if (!isListTopRowHourInput(el)) return;
    if (el.dataset.ipsSelectOnFocus) return;
    el.dataset.ipsSelectOnFocus = "1";

    function rememberPrev() {
      el.dataset.ipsPrevHour = el.value;
    }

    function selectAll() {
      try {
        el.select();
      } catch (err) {}
    }

    function isFullySelected() {
      var val = String(el.value || "");
      var start = el.selectionStart == null ? 0 : el.selectionStart;
      var end = el.selectionEnd == null ? val.length : el.selectionEnd;
      return start === 0 && end >= val.length;
    }

    function formatOneDecimal() {
      var raw = String(el.value == null ? "" : el.value).trim();
      if (raw === "") return;
      var n = parseFloat(raw);
      if (isNaN(n)) return;
      var fmt = n.toFixed(1);
      if (el.value !== fmt) {
        el.value = fmt;
        el.dispatchEvent(new Event("input", { bubbles: true }));
      }
    }

    el.addEventListener("focus", function () {
      rememberPrev();
      delete el.dataset.ipsReplaceTyping;
      w.requestAnimationFrame(selectAll);
    });

    el.addEventListener("click", function () {
      if (doc.activeElement === el) {
        w.requestAnimationFrame(selectAll);
      }
    });

    el.addEventListener("mousedown", function (e) {
      if (doc.activeElement === el) return;
      e.preventDefault();
      rememberPrev();
      delete el.dataset.ipsReplaceTyping;
      w.requestAnimationFrame(function () {
        el.focus({ preventScroll: true });
        selectAll();
      });
    });

    el.addEventListener("keydown", function (e) {
      if (!isDigitKey(e)) return;
      if (isFullySelected()) return;
      if (el.dataset.ipsReplaceTyping === "1") return;
      e.preventDefault();
      el.dataset.ipsReplaceTyping = "1";
      el.value = e.key;
      try {
        el.setSelectionRange(el.value.length, el.value.length);
      } catch (err2) {}
      el.dispatchEvent(new Event("input", { bubbles: true }));
    });

    el.addEventListener("blur", function () {
      delete el.dataset.ipsReplaceTyping;
      var prev = el.dataset.ipsPrevHour;
      var raw = String(el.value == null ? "" : el.value).trim();
      if (raw === "" && prev != null && prev !== "") {
        el.value = prev;
        el.dispatchEvent(new Event("input", { bubbles: true }));
      } else {
        formatOneDecimal();
      }
    });
  }

  function bindAll(root) {
    root.querySelectorAll(SELECTOR).forEach(bindInput);
  }

  function onFocusIn(e) {
    var el = e.target;
    if (!isListTopRowHourInput(el)) return;
    bindInput(el);
    w.requestAnimationFrame(function () {
      try {
        el.select();
      } catch (err) {}
    });
  }

  bindAll(doc);
  if (!w.__ipsTkListHourFocusIn) {
    w.__ipsTkListHourFocusIn = true;
    doc.addEventListener("focusin", onFocusIn, true);
  }
  if (!w.__ipsTkListHourObserver) {
    w.__ipsTkListHourObserver = new MutationObserver(function () {
      bindAll(doc);
    });
    w.__ipsTkListHourObserver.observe(doc.body, { childList: true, subtree: true });
  }
})();
</script>
"""
    try:
        components.html(html_doc, height=0, key="ips_tk_list_daily_hour_focus_v3")
    except TypeError:
        components.html(html_doc, height=0)


def inject_timekeeping_module_css() -> None:
    """Timekeeping list custom table styling."""
    tk_expand = ".st-key-timekeeping_table_wrap [class*='st-key-tk_expand_detail_']"
    tk_list_detail_excl = (
        ":not(:has(.timekeeping-detail-header-marker)):not(:has(.timekeeping-detail-row-marker))"
    )
    tk_card = '.st-key-timekeeping_table_wrap [class*="st-key-tk_card_"]'
    tk_row_expand = (
        f'{tk_card} [class*="st-key-tk_expand_detail_"]'
    )
    tk_detail_row = (
        f"{tk_row_expand} [data-testid=\"stHorizontalBlock\"]:has(.timekeeping-detail-header-marker), "
        f"{tk_row_expand} [data-testid=\"stHorizontalBlock\"]:has(.timekeeping-detail-row-marker)"
    )
    tk_detail_grid_readonly = (
        "minmax(112px, 120px) minmax(132px, 145px) minmax(360px, 3fr) minmax(108px, 118px) "
        "minmax(108px, 118px) 92px minmax(100px, 116px) minmax(132px, 150px) minmax(180px, 1.5fr)"
    )
    tk_detail_grid_edit = (
        "minmax(112px, 120px) minmax(132px, 145px) minmax(360px, 3fr) minmax(108px, 118px) "
        "minmax(108px, 118px) 92px minmax(100px, 116px) minmax(132px, 150px) minmax(160px, 1.2fr) 48px"
    )
    tk_list_day_w = "116px"
    tk_list_day_inner_w = "108px"
    tk_list_outer_grid = (
        f"24px 32px 220px repeat(7, {tk_list_day_w}) 24px 76px 68px 78px 104px"
    )
    tk_list_spin_w = "104px"
    tk_list_spin_input_w = "74px"
    tk_list_spin_btn_w = "26px"
    tk_list_spin_h = "38px"
    tk_list_row_h = "68px"
    tk_list_summary_row = (
        f'{tk_card} [class*="st-key-tk_row_"] [data-testid="stHorizontalBlock"]'
        f':has(.timesheet-list-row-marker){tk_list_detail_excl}'
    )
    tk_list_data_row = (
        f'.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]'
        f':has(.timesheet-list-row-marker){tk_list_detail_excl}'
    )
    tk_list_spin_row = (
        '.st-key-timekeeping_table_wrap [class*="st-key-tk_list_hour_spin_"] '
        '[data-testid="stHorizontalBlock"]:has(.timekeeping-spinner-buttons-marker)'
    )
    tk_list_outer_row = (
        f'.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timekeeping-list-header-marker){tk_list_detail_excl}, '
        f'.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timekeeping-list-row-header-marker){tk_list_detail_excl}, '
        f'.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timesheet-list-row-marker){tk_list_detail_excl}'
    )
    tk_list_spacer_col = (
        f'{tk_list_outer_row} > [data-testid="column"]:has(.timekeeping-list-spacer-marker), '
        f'{tk_list_outer_row} > [data-testid="column"]:nth-child(11)'
    )
    tk_list_sun_col = (
        f'{tk_list_outer_row} > [data-testid="column"]:nth-child(10)'
    )
    tk_list_day_col = (
        f'{tk_list_outer_row} > [data-testid="column"]:nth-child(n+4):nth-child(-n+10)'
    )
    tk_list_summary_col = (
        f'{tk_list_outer_row} > [data-testid="column"]:nth-child(12), '
        f'{tk_list_outer_row} > [data-testid="column"]:nth-child(13), '
        f'{tk_list_outer_row} > [data-testid="column"]:nth-child(14), '
        f'{tk_list_outer_row} > [data-testid="column"]:nth-child(15)'
    )
    tk_alloc_type_col_w = "96px"
    tk_alloc_assign_col_min_w = "220px"
    tk_alloc_actions_col_min_w = "200px"
    tk_alloc_grid_cols = """
    minmax(240px, 2.4fr)
    96px
    108px
    minmax(180px, 1.5fr)"""
    tk_alloc_grid_min_w = "860px"
    tk_alloc_panel = (
        f'{tk_expand}:has(.timekeeping-allocation-panel-marker) '
        f'[class*="st-key-tk_alloc_panel_"]'
    )
    tk_alloc_day = (
        f'{tk_expand}:has(.timekeeping-allocation-panel-marker) '
        f'[class*="st-key-tk_alloc_day_"], '
        f'{tk_alloc_panel} [class*="st-key-tk_alloc_day_"]'
    )
    tk_alloc_line_host = f'{tk_alloc_day} [class*="st-key-tk_alloc_line_"]'
    tk_alloc_line_key = (
        f'{tk_alloc_line_host} [data-testid="stHorizontalBlock"]:has(.timekeeping-allocation-control-row-marker)'
    )
    tk_alloc_ctrl_row = tk_alloc_line_key
    tk_alloc_ctrl_row_alt = (
        f'{tk_alloc_day} [data-testid="stHorizontalBlock"]:has(.timekeeping-allocation-control-row-marker)'
        f':not(:has(.timekeeping-allocation-primary-row-marker))'
    )
    tk_alloc_type_col = (
        f'{tk_expand}:has(.timekeeping-allocation-panel-marker) '
        f'[data-testid="column"]:has(.timekeeping-hour-type-cell), '
        f'{tk_expand}:has(.timekeeping-allocation-panel-marker) '
        f'[data-testid="column"]:has(.timekeeping-allocation-type-marker)'
    )
    tk_alloc_type_widget = (
        f'{tk_expand}:has(.timekeeping-allocation-panel-marker) [class*="st-key-tk_alloc_type_"]'
    )
    st.markdown(
        f"""
<style id="ips-timekeeping-module-v98">
.ips-timekeeping-table-wrap,
.timekeeping-list-scroll {{
  background: #ffffff;
  border: none;
  border-radius: 0;
  overflow-x: hidden;
  overflow-y: visible;
  margin-bottom: 0.5rem;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
}}
.st-key-timekeeping_table_wrap > [data-testid="stVerticalBlock"] {{
  overflow-x: visible;
  min-width: 0;
  max-width: 100%;
  width: 100%;
}}
.ips-timekeeping-header-row {{
  background: transparent;
  border-bottom: none;
  padding: 4px 6px;
  font-size: 11px;
  font-weight: 800;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  min-height: 28px;
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
  color: #2563eb;
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
  text-align: center;
  font-variant-numeric: tabular-nums;
  font-weight: 700;
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
.ips-timekeeping-status-pill-day-box {{
  display: inline-flex !important;
  align-items: center;
  justify-content: center;
  height: 16px;
  padding: 0 6px;
  margin: 2px auto 0;
  border-radius: 999px;
  font-size: 8px;
  font-weight: 800;
  letter-spacing: 0.04em;
  line-height: 1;
  white-space: nowrap;
  background: #22c55e !important;
  color: #ffffff !important;
  box-shadow: 0 0 0 1px #16a34a;
}}
.ips-timekeeping-status-rejected {{
  background: #fee2e2;
  color: #991b1b;
}}
.ips-timekeeping-row-expand {{
  background: #f8fafc;
  border-top: 1px solid #dbeafe;
  border-bottom: 2px solid #cbd5e1;
  padding: 12px 14px 16px;
  margin: 0;
}}
.timesheet-employee-card-marker {{
  display: none !important;
}}
{tk_card} {{
  height: auto !important;
  min-height: 0 !important;
  max-height: none !important;
  overflow: visible !important;
  margin: 0 0 6px 0 !important;
  padding: 0 !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  box-sizing: border-box !important;
}}
{tk_card} > [data-testid="stVerticalBlock"] {{
  height: auto !important;
  min-height: 0 !important;
  max-height: none !important;
  overflow: visible !important;
  gap: 0 !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] {{
  background: transparent !important;
  border: none !important;
  border-radius: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  box-shadow: none !important;
  height: auto !important;
  min-height: 0 !important;
  max-height: none !important;
  overflow: visible !important;
  box-sizing: border-box !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] > [data-testid="stVerticalBlock"] {{
  height: auto !important;
  min-height: 0 !important;
  max-height: none !important;
  overflow: visible !important;
  gap: 0 !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_expand_detail_"] {{
  height: auto !important;
  min-height: 0 !important;
  max-height: none !important;
  overflow: visible !important;
  flex: 0 0 auto !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_expand_detail_"] > [data-testid="stVerticalBlock"] {{
  height: auto !important;
  min-height: 0 !important;
  max-height: none !important;
  overflow: visible !important;
  gap: 0.35rem !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="stVerticalBlock"] {{
  gap: 0 !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"]:hover {{
  background: #f8fbff !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="stHorizontalBlock"] {{
  border-bottom: none !important;
  background: transparent !important;
  min-height: 0 !important;
  padding: 0 2px !important;
  margin: 0 !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="stHorizontalBlock"]:first-of-type:not(:has(.timesheet-list-row-marker)) {{
  min-height: 34px !important;
  align-items: center !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="stHorizontalBlock"]:hover {{
  background: transparent !important;
}}
.timesheet-header-row {{
  display: flex;
  align-items: center;
  min-width: 0;
  width: 100%;
}}
.timesheet-header-row .employee-name {{
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.25;
  word-break: break-word;
}}
.employee-summary-value {{
  text-align: right;
  width: 100%;
}}
.timesheet-days-inline-grid {{
  width: 100%;
  max-width: 100%;
  margin: 2px 0 0 0;
  padding: 0;
}}
.timesheet-employee-expand-detail {{
  margin-top: 8px;
  padding-top: 10px;
  border-top: 1px solid #e2e8f0;
  background: transparent;
  overflow-x: auto;
  overflow-y: visible;
  -webkit-overflow-scrolling: touch;
  max-width: 100%;
}}
.timesheet-employee-expand-detail .ips-timekeeping-expand-title {{
  display: none;
}}
.timekeeping-detail-grid-marker,
.timekeeping-detail-header-marker,
.timekeeping-detail-row-marker {{
  display: none !important;
}}
.timekeeping-detail-head,
.timekeeping-detail-cell {{
  white-space: nowrap !important;
  word-break: normal !important;
  writing-mode: horizontal-tb !important;
  overflow: hidden;
  text-overflow: ellipsis;
}}
.timesheet-employee-expand-detail:has(.timekeeping-detail-grid-readonly)
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-header-marker),
.timesheet-employee-expand-detail:has(.timekeeping-detail-grid-readonly)
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker) {{
  display: grid !important;
  grid-template-columns:
    70px
    110px
    minmax(280px, 2fr)
    90px
    90px
    100px
    110px
    120px
    minmax(160px, 1fr) !important;
  gap: 12px !important;
  align-items: center !important;
  min-width: 1240px !important;
  width: 100% !important;
  max-width: none !important;
  padding: 6px 8px !important;
  margin: 0 !important;
  flex-wrap: nowrap !important;
}}
.timesheet-employee-expand-detail:has(.timekeeping-detail-grid-edit)
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-header-marker),
.timesheet-employee-expand-detail:has(.timekeeping-detail-grid-edit)
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker) {{
  display: grid !important;
  grid-template-columns:
    70px
    110px
    minmax(280px, 2fr)
    90px
    90px
    100px
    110px
    120px
    minmax(140px, 1fr)
    40px !important;
  gap: 12px !important;
  align-items: center !important;
  min-width: 1280px !important;
  width: 100% !important;
  max-width: none !important;
  padding: 6px 8px !important;
  margin: 0 !important;
  flex-wrap: nowrap !important;
}}
.timesheet-employee-expand-detail
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-header-marker)
  > [data-testid="column"],
.timesheet-employee-expand-detail
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker)
  > [data-testid="column"] {{
  flex: unset !important;
  width: auto !important;
  min-width: 0 !important;
  max-width: none !important;
  overflow: visible !important;
  padding-left: 0 !important;
  padding-right: 0 !important;
}}
.timesheet-employee-expand-detail
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-header-marker)
  > [data-testid="column"] [data-testid="stVerticalBlock"],
.timesheet-employee-expand-detail
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker)
  > [data-testid="column"] [data-testid="stVerticalBlock"],
.timesheet-employee-expand-detail
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker)
  > [data-testid="column"] [data-testid="stElementContainer"] {{
  width: 100% !important;
  min-width: 0 !important;
  overflow: visible !important;
}}
.timesheet-employee-expand-detail
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker)
  > [data-testid="column"]:nth-child(3),
.timesheet-employee-expand-detail
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker)
  > [data-testid="column"]:has(.timekeeping-detail-assignment-marker) {{
  min-width: 280px !important;
  overflow: visible !important;
}}
.timesheet-employee-expand-detail
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker)
  > [data-testid="column"]:nth-child(3) [data-testid="stSelectbox"],
.timesheet-employee-expand-detail
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker)
  > [data-testid="column"]:has(.timekeeping-detail-assignment-marker) [data-testid="stSelectbox"] {{
  width: 100% !important;
  min-width: 260px !important;
  max-width: none !important;
  display: block !important;
  visibility: visible !important;
}}
.timesheet-employee-expand-detail
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker)
  > [data-testid="column"]:nth-child(3) [data-testid="stSelectbox"] div[data-baseweb="select"],
.timesheet-employee-expand-detail
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker)
  > [data-testid="column"]:nth-child(3) [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
.timesheet-employee-expand-detail
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker)
  > [data-testid="column"]:has(.timekeeping-detail-assignment-marker) [data-testid="stSelectbox"] div[data-baseweb="select"],
.timesheet-employee-expand-detail
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker)
  > [data-testid="column"]:has(.timekeeping-detail-assignment-marker) [data-testid="stSelectbox"] div[data-baseweb="select"] > div {{
  width: 100% !important;
  min-width: 260px !important;
  max-width: none !important;
  background: #ffffff !important;
  border: 1px solid #d1d5db !important;
  border-radius: 8px !important;
  box-shadow: none !important;
  min-height: 38px !important;
}}
.timesheet-employee-expand-detail
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker)
  > [data-testid="column"]:nth-child(3) [data-testid="stSelectbox"] div[data-baseweb="select"] span {{
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}}
.timesheet-employee-expand-detail
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker)
  > [data-testid="column"]:nth-child(9) [data-testid="stTextInput"],
.timesheet-employee-expand-detail
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker)
  > [data-testid="column"]:nth-child(9) [data-testid="stTextInput"] > div,
.timesheet-employee-expand-detail
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker)
  > [data-testid="column"]:nth-child(9) [data-testid="stTextInput"] input {{
  width: 100% !important;
  min-width: 0 !important;
}}
.timesheet-employee-expand-detail .ips-time-day-head {{
  white-space: nowrap !important;
  word-break: normal !important;
  writing-mode: horizontal-tb !important;
  text-align: left;
  overflow: visible;
}}
.timesheet-employee-expand-detail .ips-time-day-row {{
  white-space: nowrap !important;
  word-break: normal !important;
  writing-mode: horizontal-tb !important;
}}
.timesheet-employee-expand-detail
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker)
  > [data-testid="column"]:nth-child(4) [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-stepper-marker),
.timesheet-employee-expand-detail
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker)
  > [data-testid="column"]:nth-child(5) [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-stepper-marker) {{
  display: grid !important;
  grid-template-columns: 28px minmax(28px, 1fr) 28px !important;
  width: 100% !important;
  max-width: 90px !important;
  min-width: 84px !important;
  height: 38px !important;
  border: 1px solid #d8dee8 !important;
  border-radius: 8px !important;
  overflow: hidden !important;
  background: #ffffff !important;
  margin: 0 auto !important;
}}
.timesheet-employee-expand-detail
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker)
  > [data-testid="column"]:nth-child(4) [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-stepper-marker) [data-testid="stNumberInput"] input,
.timesheet-employee-expand-detail
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker)
  > [data-testid="column"]:nth-child(5) [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-stepper-marker) [data-testid="stNumberInput"] input {{
  min-width: 0 !important;
  width: 100% !important;
  font-size: 12px !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] .timesheet-employee-expand-detail [data-testid="stHorizontalBlock"] {{
  min-height: unset !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_expand_detail_"]:has(.timesheet-employee-expand-detail)
  [data-testid="stHorizontalBlock"]:not(:has(.timekeeping-detail-header-marker)):not(:has(.timekeeping-detail-row-marker)):not(:has(.timekeeping-allocation-assignment-marker)):not(:has(.timekeeping-allocation-control-row-marker)):not(:has(.timekeeping-allocation-header-row-marker)) {{
  min-width: 0 !important;
  width: 100% !important;
  display: flex !important;
}}
{tk_expand}
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-header-marker):not(:has(.timesheet-list-row-marker))
  > [data-testid="column"],
{tk_expand}
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker)
  > [data-testid="column"] {{
  flex: unset !important;
  width: auto !important;
  min-width: 0 !important;
  max-width: none !important;
  overflow: visible !important;
  padding-left: 0 !important;
  padding-right: 0 !important;
}}
{tk_expand}
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker)
  > [data-testid="column"] [data-testid="stVerticalBlock"],
{tk_expand}
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker)
  > [data-testid="column"] [data-testid="stElementContainer"] {{
  width: 100% !important;
  min-width: 0 !important;
  overflow: visible !important;
}}
{tk_expand}
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker)
  > [data-testid="column"]:nth-child(3),
{tk_expand}
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker)
  > [data-testid="column"]:has(.timekeeping-detail-assignment-marker) {{
  min-width: 280px !important;
  overflow: visible !important;
}}
{tk_expand}
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker)
  > [data-testid="column"]:nth-child(3) [data-testid="stSelectbox"],
{tk_expand}
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker)
  > [data-testid="column"]:has(.timekeeping-detail-assignment-marker) [data-testid="stSelectbox"] {{
  width: 100% !important;
  min-width: 260px !important;
  max-width: none !important;
  display: block !important;
  visibility: visible !important;
}}
{tk_expand}
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker)
  > [data-testid="column"]:nth-child(3) [data-testid="stSelectbox"] div[data-baseweb="select"],
{tk_expand}
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker)
  > [data-testid="column"]:nth-child(3) [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
{tk_expand}
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker)
  > [data-testid="column"]:has(.timekeeping-detail-assignment-marker) [data-testid="stSelectbox"] div[data-baseweb="select"],
{tk_expand}
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker)
  > [data-testid="column"]:has(.timekeeping-detail-assignment-marker) [data-testid="stSelectbox"] div[data-baseweb="select"] > div {{
  width: 100% !important;
  min-width: 260px !important;
  max-width: none !important;
  background: #ffffff !important;
  border: 1px solid #d1d5db !important;
  border-radius: 8px !important;
  box-shadow: none !important;
  min-height: 38px !important;
}}
{tk_expand}
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker)
  > [data-testid="column"]:nth-child(3) [data-testid="stSelectbox"] div[data-baseweb="select"] span {{
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}}
{tk_expand}
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker)
  > [data-testid="column"]:nth-child(7) {{
  min-width: 100px !important;
}}
{tk_expand}
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker)
  > [data-testid="column"]:nth-child(7) .ips-timekeeping-status-pill {{
  display: inline-flex !important;
  min-width: 88px !important;
  justify-content: center !important;
}}
{tk_expand}
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker)
  > [data-testid="column"]:nth-child(9) [data-testid="stTextInput"],
{tk_expand}
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker)
  > [data-testid="column"]:nth-child(9) [data-testid="stTextInput"] > div,
{tk_expand}
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker)
  > [data-testid="column"]:nth-child(9) [data-testid="stTextInput"] input {{
  width: 100% !important;
  min-width: 0 !important;
}}
{tk_expand}
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker)
  > [data-testid="column"]:nth-child(4) [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-stepper-marker),
{tk_expand}
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker)
  > [data-testid="column"]:nth-child(5) [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-stepper-marker) {{
  display: grid !important;
  grid-template-columns: 28px minmax(28px, 1fr) 28px !important;
  width: 100% !important;
  max-width: 90px !important;
  min-width: 84px !important;
  height: 38px !important;
  border: 1px solid #d8dee8 !important;
  border-radius: 8px !important;
  overflow: hidden !important;
  background: #ffffff !important;
  margin: 0 auto !important;
}}
{tk_expand}:has(.ips-time-day-edit-marker)
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker):has(.ips-time-day-row-filled)
  > [data-testid="column"]:nth-child(3) {{
  background: #dcfce7 !important;
  border: 1px solid #22c55e !important;
  border-radius: 6px !important;
}}
{tk_expand}:has(.ips-time-day-edit-marker)
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker):has(.ips-time-day-row-filled)
  > [data-testid="column"]:nth-child(4),
{tk_expand}:has(.ips-time-day-edit-marker)
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker):has(.ips-time-day-row-filled)
  > [data-testid="column"]:nth-child(5),
{tk_expand}:has(.ips-time-day-edit-marker)
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker):has(.ips-time-day-row-filled)
  > [data-testid="column"]:nth-child(6) {{
  background: #ecfdf3 !important;
  border-radius: 6px !important;
}}
{tk_expand}:has(.ips-time-day-edit-marker)
  [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker):has(.ips-time-day-row-filled)
  > [data-testid="column"]:has(.ips-time-day-job-filled) {{
  background: #dcfce7 !important;
  border: 1px solid #22c55e !important;
  border-radius: 6px !important;
  box-shadow: none !important;
}}
{tk_expand} [data-testid="stHorizontalBlock"] {{
  min-height: unset !important;
}}
.ips-time-week-summary {{
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 0.35rem;
  margin: 0 0 0.75rem;
}}
.ips-time-week-inline {{
  margin: 0.05rem 0 0.15rem;
  padding: 0;
  border-bottom: 1px solid #e5e7eb;
}}
.timesheet-days-grid,
.timesheet-days-grid-wrap {{
  display: flex;
  justify-content: flex-start;
  width: 100%;
  max-width: 100%;
}}
.compact-hours-grid {{
  width: fit-content;
  max-width: 100%;
}}
.st-key-timekeeping_table_wrap .st-key-tk_row_ [data-testid="stHorizontalBlock"]:has(.timesheet-days-grid-marker),
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="column"] [data-testid="stHorizontalBlock"]:has(.timesheet-days-grid-marker),
.ips-time-week-inline.timesheet-days-grid-wrap [data-testid="stHorizontalBlock"]:has(.timesheet-days-grid-marker) {{
  display: grid !important;
  grid-template-columns: repeat(7, 52px) !important;
  gap: 0 !important;
  width: fit-content !important;
  max-width: 100% !important;
  margin: 0 !important;
  justify-content: flex-start !important;
  align-items: stretch !important;
  border-bottom: none !important;
  padding: 0 !important;
}}
.st-key-timekeeping_table_wrap .st-key-tk_row_ [data-testid="stHorizontalBlock"]:has(.timesheet-days-grid-marker) > [data-testid="column"],
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="column"] [data-testid="stHorizontalBlock"]:has(.timesheet-days-grid-marker) > [data-testid="column"],
.ips-time-week-inline.timesheet-days-grid-wrap [data-testid="stHorizontalBlock"]:has(.timesheet-days-grid-marker) > [data-testid="column"] {{
  flex: 0 0 52px !important;
  width: 52px !important;
  min-width: 52px !important;
  max-width: 52px !important;
  padding: 1px 0 !important;
  margin: 0 !important;
  overflow: visible !important;
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  justify-content: flex-start !important;
  border-right: 1px solid #e5e7eb;
  box-sizing: border-box !important;
  background: #ffffff;
}}
.st-key-timekeeping_table_wrap .st-key-tk_row_ [data-testid="stHorizontalBlock"]:has(.timesheet-days-grid-marker) > [data-testid="column"]:last-child,
.ips-time-week-inline.timesheet-days-grid-wrap [data-testid="stHorizontalBlock"]:has(.timesheet-days-grid-marker) > [data-testid="column"]:last-child {{
  border-right: none !important;
}}
.st-key-timekeeping_table_wrap .st-key-tk_row_ [data-testid="stHorizontalBlock"]:has(.timesheet-days-grid-marker) > [data-testid="column"]:has(.ips-time-week-day-filled),
.ips-time-week-inline.timesheet-days-grid-wrap [data-testid="stHorizontalBlock"]:has(.timesheet-days-grid-marker) > [data-testid="column"]:has(.ips-time-week-day-filled) {{
  background: #f0fdf4 !important;
}}
.day-block-marker,
.day-card-marker {{
  display: none !important;
}}
.day-block,
.day-card {{
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  gap: 2px;
}}
.day-date-line {{
  display: flex;
  flex-direction: row;
  align-items: baseline;
  justify-content: center;
  gap: 3px;
  width: 100%;
  white-space: nowrap;
  line-height: 1.1;
  margin: 0;
  padding: 0;
}}
.day-label,
.ips-time-week-day-label {{
  font-size: 10px;
  font-weight: 800;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  line-height: 1.1;
  text-align: center;
  width: auto;
  display: inline;
  margin: 0;
}}
.day-date,
.ips-time-week-day-date {{
  font-size: 10px;
  font-weight: 650;
  color: #64748b;
  line-height: 1.1;
  margin: 0;
  text-align: center;
  width: auto;
  display: inline;
}}
.hours-row,
.ips-day-hrs-row-ro {{
  display: inline-flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  gap: 2px;
  width: 100%;
  min-height: 32px;
  margin-top: 1px;
}}
.hrs-label,
.ips-day-hrs-label {{
  font-size: 10px;
  font-weight: 800;
  color: #64748b;
  letter-spacing: 0.04em;
  line-height: 1;
  text-align: right;
  white-space: nowrap;
  padding-right: 1px;
  flex: 0 0 auto;
}}
.ips-time-week-inline .compact-hours-grid [data-testid="stHorizontalBlock"],
.st-key-timekeeping_table_wrap .st-key-tk_row_ .compact-hours-grid [data-testid="stHorizontalBlock"] {{
  display: grid !important;
  grid-template-columns: repeat(7, 62px) !important;
  gap: 0 !important;
  width: fit-content !important;
  max-width: 100%;
  align-items: stretch !important;
  justify-content: start !important;
  border-bottom: none !important;
  padding: 0 !important;
  margin: 0 !important;
}}
.ips-time-week-inline .compact-hours-grid [data-testid="column"],
.st-key-timekeeping_table_wrap .st-key-tk_row_ .compact-hours-grid [data-testid="stHorizontalBlock"] > [data-testid="column"] {{
  flex: unset !important;
  width: auto !important;
  min-width: 0 !important;
  max-width: none !important;
  padding: 4px 0 !important;
  margin: 0 !important;
  overflow: visible !important;
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  justify-content: flex-start !important;
  border-right: 1px solid #e5e7eb;
  box-sizing: border-box !important;
  background: #ffffff;
}}
.ips-compact-hours-input-marker {{
  display: none !important;
}}
.st-key-timekeeping_table_wrap .st-key-tk_row_ [data-testid="stHorizontalBlock"]:has(.timesheet-days-grid-marker) [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInput"],
.ips-time-week-inline.timesheet-days-grid-wrap [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInput"],
.ips-time-week-inline .compact-hours-grid [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInput"],
.st-key-tk_hgrid_wrap [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInput"],
.st-key-tk_page_hgrid_wrap [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInput"] {{
  width: 54px !important;
  min-width: 54px !important;
  max-width: 54px !important;
  margin: 0 !important;
  overflow: visible !important;
}}
.st-key-timekeeping_table_wrap .st-key-tk_row_ [data-testid="stHorizontalBlock"]:has(.timesheet-days-grid-marker) [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInput"] > div,
.ips-time-week-inline.timesheet-days-grid-wrap [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInput"] > div,
.ips-time-week-inline .compact-hours-grid [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInput"] > div,
.st-key-tk_hgrid_wrap [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInput"] > div,
.st-key-tk_page_hgrid_wrap [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInput"] > div {{
  padding: 0 !important;
  min-height: 32px !important;
  height: 32px !important;
  align-items: center !important;
  display: flex !important;
  flex-direction: row !important;
  overflow: visible !important;
}}
.st-key-timekeeping_table_wrap .st-key-tk_row_ [data-testid="stHorizontalBlock"]:has(.timesheet-days-grid-marker) [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInput"] input,
.ips-time-week-inline.timesheet-days-grid-wrap [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInput"] input,
.ips-time-week-inline .compact-hours-grid input[type="number"],
.ips-time-week-inline .compact-hours-grid [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInput"] input,
.st-key-tk_hgrid_wrap [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInput"] input,
.st-key-tk_page_hgrid_wrap [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInput"] input {{
  width: 36px !important;
  min-width: 36px !important;
  max-width: 36px !important;
  height: 32px !important;
  min-height: 32px !important;
  padding: 2px 3px !important;
  font-size: 12px !important;
  font-weight: 700 !important;
  text-align: center !important;
  border: 1px solid #e5e7eb !important;
  border-radius: 6px 0 0 6px !important;
  background: #ffffff !important;
  box-shadow: none !important;
  font-variant-numeric: tabular-nums;
  -moz-appearance: textfield;
}}
.st-key-timekeeping_table_wrap .st-key-tk_row_ [data-testid="stHorizontalBlock"]:has(.timesheet-days-grid-marker) [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInput"] input::-webkit-outer-spin-button,
.st-key-timekeeping_table_wrap .st-key-tk_row_ [data-testid="stHorizontalBlock"]:has(.timesheet-days-grid-marker) [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInput"] input::-webkit-inner-spin-button,
.ips-time-week-inline.timesheet-days-grid-wrap [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInput"] input::-webkit-outer-spin-button,
.ips-time-week-inline.timesheet-days-grid-wrap [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInput"] input::-webkit-inner-spin-button,
.ips-time-week-inline .compact-hours-grid [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInput"] input::-webkit-outer-spin-button,
.ips-time-week-inline .compact-hours-grid [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInput"] input::-webkit-inner-spin-button {{
  -webkit-appearance: none;
  margin: 0;
}}
.st-key-timekeeping_table_wrap .st-key-tk_row_ [data-testid="stHorizontalBlock"]:has(.timesheet-days-grid-marker) [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInputStepUp"],
.st-key-timekeeping_table_wrap .st-key-tk_row_ [data-testid="stHorizontalBlock"]:has(.timesheet-days-grid-marker) [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInputStepDown"],
.ips-time-week-inline.timesheet-days-grid-wrap [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInputStepUp"],
.ips-time-week-inline.timesheet-days-grid-wrap [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInputStepDown"],
.ips-time-week-inline .compact-hours-grid [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInputStepUp"],
.ips-time-week-inline .compact-hours-grid [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInputStepDown"],
.st-key-tk_hgrid_wrap [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInputStepUp"],
.st-key-tk_hgrid_wrap [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInputStepDown"],
.st-key-tk_page_hgrid_wrap [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInputStepUp"],
.st-key-tk_page_hgrid_wrap [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInputStepDown"] {{
  display: flex !important;
  align-items: stretch !important;
  justify-content: center !important;
  width: 18px !important;
  min-width: 18px !important;
  max-width: 18px !important;
  opacity: 1 !important;
  visibility: visible !important;
  overflow: visible !important;
  flex: 0 0 18px !important;
}}
.st-key-timekeeping_table_wrap .st-key-tk_row_ [data-testid="stHorizontalBlock"]:has(.timesheet-days-grid-marker) [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInputStepUp"] button,
.st-key-timekeeping_table_wrap .st-key-tk_row_ [data-testid="stHorizontalBlock"]:has(.timesheet-days-grid-marker) [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInputStepDown"] button,
.ips-time-week-inline.timesheet-days-grid-wrap [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInputStepUp"] button,
.ips-time-week-inline.timesheet-days-grid-wrap [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInputStepDown"] button,
.ips-time-week-inline .compact-hours-grid [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInputStepUp"] button,
.ips-time-week-inline .compact-hours-grid [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInputStepDown"] button,
.st-key-tk_hgrid_wrap [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInputStepUp"] button,
.st-key-tk_hgrid_wrap [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInputStepDown"] button,
.st-key-tk_page_hgrid_wrap [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInputStepUp"] button,
.st-key-tk_page_hgrid_wrap [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInputStepDown"] button {{
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  min-width: 18px !important;
  min-height: 14px !important;
  width: 18px !important;
  padding: 0 !important;
  opacity: 1 !important;
  visibility: visible !important;
  border: 1px solid #e5e7eb !important;
  background: #f8fafc !important;
  color: #334155 !important;
}}
.st-key-timekeeping_table_wrap .st-key-tk_row_ [data-testid="stHorizontalBlock"]:has(.timesheet-days-grid-marker) [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInputStepDown"] button,
.ips-time-week-inline.timesheet-days-grid-wrap [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInputStepDown"] button,
.ips-time-week-inline .compact-hours-grid [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInputStepDown"] button {{
  border-radius: 0 0 6px 0 !important;
  border-top: none !important;
}}
.st-key-timekeeping_table_wrap .st-key-tk_row_ [data-testid="stHorizontalBlock"]:has(.timesheet-days-grid-marker) [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInputStepUp"] button,
.ips-time-week-inline.timesheet-days-grid-wrap [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInputStepUp"] button,
.ips-time-week-inline .compact-hours-grid [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInputStepUp"] button {{
  border-radius: 0 6px 0 0 !important;
  border-bottom: none !important;
}}
.st-key-timekeeping_table_wrap .st-key-tk_row_ [data-testid="stHorizontalBlock"]:has(.timesheet-days-grid-marker) [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInput"] [data-testid="stWidgetLabel"],
.ips-time-week-inline.timesheet-days-grid-wrap [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInput"] [data-testid="stWidgetLabel"],
.ips-time-week-inline .compact-hours-grid [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInput"] [data-testid="stWidgetLabel"],
.st-key-tk_hgrid_wrap [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInput"] [data-testid="stWidgetLabel"],
.st-key-tk_page_hgrid_wrap [data-testid="column"]:has(.ips-compact-hours-input-marker) [data-testid="stNumberInput"] [data-testid="stWidgetLabel"] {{
  display: none !important;
}}
.ips-day-hrs-value {{
  font-size: 12px;
  font-weight: 700;
  color: #0f172a;
  font-variant-numeric: tabular-nums;
  min-width: 34px;
  text-align: center;
}}
.ips-time-week-inline .compact-hours-grid [data-testid="column"]:has(.ips-day-hrs-row-marker),
.st-key-tk_hgrid_wrap [data-testid="column"]:has(.ips-day-hrs-row-marker),
.st-key-tk_page_hgrid_wrap [data-testid="column"]:has(.ips-day-hrs-row-marker) {{
  width: 100% !important;
  display: flex !important;
  justify-content: center !important;
  align-items: center !important;
  margin: 0 !important;
  padding: 0 !important;
}}
.ips-time-week-inline .compact-hours-grid [data-testid="column"]:has(.hours-row) [data-testid="stHorizontalBlock"],
.ips-time-week-inline .compact-hours-grid [data-testid="column"]:has(.ips-day-hrs-row-marker) [data-testid="stHorizontalBlock"],
.st-key-tk_hgrid_wrap [data-testid="column"]:has(.ips-day-hrs-row-marker) [data-testid="stHorizontalBlock"],
.st-key-tk_page_hgrid_wrap [data-testid="column"]:has(.ips-day-hrs-row-marker) [data-testid="stHorizontalBlock"] {{
  display: flex !important;
  width: 100% !important;
  max-width: 62px !important;
  margin: 0 auto !important;
  gap: 1px !important;
  align-items: center !important;
  justify-content: center !important;
}}
.ips-time-week-inline.timesheet-days-grid-wrap [data-testid="column"]:has(.hours-row) [data-testid="stHorizontalBlock"],
.ips-time-week-inline.timesheet-days-grid-wrap [data-testid="column"]:has(.ips-day-hrs-row-marker) [data-testid="stHorizontalBlock"],
.st-key-timekeeping_table_wrap .st-key-tk_row_ [data-testid="stHorizontalBlock"]:has(.timesheet-days-grid-marker) [data-testid="column"]:has(.hours-row) [data-testid="stHorizontalBlock"],
.st-key-timekeeping_table_wrap .st-key-tk_row_ [data-testid="stHorizontalBlock"]:has(.timesheet-days-grid-marker) [data-testid="column"]:has(.ips-day-hrs-row-marker) [data-testid="stHorizontalBlock"] {{
  display: flex !important;
  flex-direction: row !important;
  width: 100% !important;
  max-width: 54px !important;
  margin: 0 auto !important;
  gap: 1px !important;
  align-items: center !important;
  justify-content: center !important;
}}
.ips-time-week-inline .compact-hours-grid [data-testid="column"]:has(.ips-day-hrs-row-marker) [data-testid="column"],
.ips-time-week-inline.timesheet-days-grid-wrap [data-testid="column"]:has(.hours-row) [data-testid="column"],
.ips-time-week-inline.timesheet-days-grid-wrap [data-testid="column"]:has(.ips-day-hrs-row-marker) [data-testid="column"],
.st-key-tk_hgrid_wrap [data-testid="column"]:has(.ips-day-hrs-row-marker) [data-testid="column"],
.st-key-tk_page_hgrid_wrap [data-testid="column"]:has(.ips-day-hrs-row-marker) [data-testid="column"] {{
  padding: 0 !important;
  border: none !important;
  background: transparent !important;
  min-width: 0 !important;
}}
.ips-time-week-inline .compact-hours-grid [data-testid="column"]:has(.ips-day-hrs-row-marker) [data-testid="column"]:first-child,
.ips-time-week-inline.timesheet-days-grid-wrap [data-testid="column"]:has(.ips-day-hrs-row-marker) [data-testid="column"]:first-child,
.st-key-tk_hgrid_wrap [data-testid="column"]:has(.ips-day-hrs-row-marker) [data-testid="column"]:first-child,
.st-key-tk_page_hgrid_wrap [data-testid="column"]:has(.ips-day-hrs-row-marker) [data-testid="column"]:first-child {{
  flex: 0 0 auto !important;
  width: auto !important;
  max-width: 24px !important;
}}
.ips-time-week-inline .compact-hours-grid [data-testid="column"]:has(.ips-day-hrs-row-marker) [data-testid="column"]:last-child,
.st-key-tk_hgrid_wrap [data-testid="column"]:has(.ips-day-hrs-row-marker) [data-testid="column"]:last-child,
.st-key-tk_page_hgrid_wrap [data-testid="column"]:has(.ips-day-hrs-row-marker) [data-testid="column"]:last-child {{
  flex: 0 0 auto !important;
  width: auto !important;
}}
.ips-time-week-inline .compact-hours-grid [data-testid="column"]:has(.ips-time-week-day-filled),
.st-key-timekeeping_table_wrap .st-key-tk_row_ .compact-hours-grid [data-testid="stHorizontalBlock"] > [data-testid="column"]:has(.ips-time-week-day-filled) {{
  background: #f0fdf4 !important;
}}
.ips-time-day-job-marker {{
  display: none;
}}
.ips-time-day-row-marker {{
  display: none;
}}
.ips-timekeeping-row-expand:has(.ips-time-day-edit-marker) [data-testid="stHorizontalBlock"]:has(.ips-time-day-row-filled) > [data-testid="column"]:nth-child(3) {{
  background: #dcfce7 !important;
  border: 1px solid #22c55e !important;
  border-radius: 6px !important;
}}
.ips-timekeeping-row-expand:has(.ips-time-day-edit-marker) [data-testid="stHorizontalBlock"]:has(.ips-time-day-row-filled) > [data-testid="column"]:nth-child(4),
.ips-timekeeping-row-expand:has(.ips-time-day-edit-marker) [data-testid="stHorizontalBlock"]:has(.ips-time-day-row-filled) > [data-testid="column"]:nth-child(5),
.ips-timekeeping-row-expand:has(.ips-time-day-edit-marker) [data-testid="stHorizontalBlock"]:has(.ips-time-day-row-filled) > [data-testid="column"]:nth-child(6) {{
  background: #ecfdf3 !important;
  border-radius: 6px !important;
}}
.ips-timekeeping-row-expand:has(.ips-time-day-edit-marker) [data-testid="stHorizontalBlock"]:has(.ips-time-day-row-filled) > [data-testid="column"]:has(.ips-time-day-job-filled) {{
  background: #dcfce7 !important;
  border: 1px solid #22c55e !important;
  border-radius: 6px !important;
  box-shadow: none !important;
}}
.timesheet-employee-expand-detail:has(.ips-time-day-edit-marker) [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker):has(.ips-time-day-row-filled) > [data-testid="column"]:nth-child(3) {{
  background: #dcfce7 !important;
  border: 1px solid #22c55e !important;
  border-radius: 6px !important;
}}
.timesheet-employee-expand-detail:has(.ips-time-day-edit-marker) [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker):has(.ips-time-day-row-filled) > [data-testid="column"]:nth-child(4),
.timesheet-employee-expand-detail:has(.ips-time-day-edit-marker) [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker):has(.ips-time-day-row-filled) > [data-testid="column"]:nth-child(5),
.timesheet-employee-expand-detail:has(.ips-time-day-edit-marker) [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker):has(.ips-time-day-row-filled) > [data-testid="column"]:nth-child(6) {{
  background: #ecfdf3 !important;
  border-radius: 6px !important;
}}
.timesheet-employee-expand-detail:has(.ips-time-day-edit-marker) [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker):has(.ips-time-day-row-filled) > [data-testid="column"]:has(.ips-time-day-job-filled) {{
  background: #dcfce7 !important;
  border: 1px solid #22c55e !important;
  border-radius: 6px !important;
  box-shadow: none !important;
}}
.ips-timekeeping-row-expand:has(.ips-time-day-edit-marker) [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-header-marker),
.ips-timekeeping-row-expand:has(.ips-time-day-edit-marker) [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker),
.timesheet-employee-expand-detail:has(.ips-time-day-edit-marker) [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-header-marker),
.timesheet-employee-expand-detail:has(.ips-time-day-edit-marker) [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker) {{
  gap: 12px !important;
  padding: 6px 8px !important;
  margin: 0 !important;
  min-height: 0 !important;
  align-items: center !important;
}}
.ips-timekeeping-row-expand:has(.ips-time-day-edit-marker) [data-testid="stElementContainer"],
.timesheet-employee-expand-detail:has(.ips-time-day-edit-marker) [data-testid="stElementContainer"] {{
  margin-bottom: 0 !important;
  padding-bottom: 0 !important;
}}
.ips-timekeeping-row-expand:has(.ips-time-day-edit-marker) [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-header-marker) > [data-testid="column"],
.ips-timekeeping-row-expand:has(.ips-time-day-edit-marker) [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker) > [data-testid="column"],
.timesheet-employee-expand-detail:has(.ips-time-day-edit-marker) [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-header-marker) > [data-testid="column"],
.timesheet-employee-expand-detail:has(.ips-time-day-edit-marker) [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-row-marker) > [data-testid="column"] {{
  padding-left: 0 !important;
  padding-right: 0 !important;
}}
.ips-timekeeping-row-expand:has(.ips-time-day-edit-marker) [data-testid="stHorizontalBlock"]:not(:has(.timekeeping-detail-row-marker)) [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
.timesheet-employee-expand-detail:has(.ips-time-day-edit-marker) [data-testid="stHorizontalBlock"]:not(:has(.timekeeping-detail-row-marker)) [data-testid="stSelectbox"] div[data-baseweb="select"] > div {{
  background: transparent !important;
  border-color: transparent !important;
  box-shadow: none !important;
}}
.ips-timekeeping-row-expand {{
  padding: 8px 8px 10px;
}}
.ips-time-week-inline-spacer {{
  display: block;
  width: 100%;
}}
.ips-time-week-day-marker {{
  display: none;
}}
.ips-time-week-day {{
  background: #fff5f5;
  border: 1px solid #fca5a5;
  border-radius: 6px;
  padding: 0.12rem 0.15rem 0.1rem;
  text-align: center;
  min-height: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 0;
}}
.ips-time-week-day-filled {{
  background: #dcfce7;
  border-color: #22c55e;
}}
.ips-time-week-day-label {{
  font-size: 10px;
  font-weight: 800;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  line-height: 1.1;
  text-align: center;
  width: auto;
  display: inline;
}}
.ips-time-week-day-date {{
  font-size: 10px;
  font-weight: 650;
  color: #64748b;
  line-height: 1.1;
  margin: 0;
  text-align: center;
  width: auto;
  display: inline;
}}
.ips-time-week-day-hours {{
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
  font-variant-numeric: tabular-nums;
  line-height: 1;
}}
.ips-time-week-day-hours-ro {{
  font-size: 12px;
  font-weight: 700;
  color: #0f172a;
  font-variant-numeric: tabular-nums;
  line-height: 32px;
  min-height: 32px;
  padding: 0;
  text-align: center;
  width: auto;
  margin: 0 auto;
}}
.ips-time-week-inline.timesheet-days-grid-wrap [data-testid="column"]:has(.day-card) [data-testid="stElementContainer"]:has(.day-card),
.st-key-timekeeping_table_wrap .st-key-tk_row_ [data-testid="stHorizontalBlock"]:has(.timesheet-days-grid-marker) [data-testid="column"]:has(.day-card) [data-testid="stElementContainer"]:has(.day-card) {{
  margin-bottom: 0 !important;
  padding-bottom: 0 !important;
}}
.ips-time-week-inline.timesheet-days-grid-wrap [data-testid="stElementContainer"],
.st-key-timekeeping_table_wrap .st-key-tk_row_ [data-testid="stHorizontalBlock"]:has(.timesheet-days-grid-marker) [data-testid="stElementContainer"] {{
  margin-bottom: 0 !important;
  padding-bottom: 0 !important;
}}
.ips-time-hour-readonly {{
  text-align: center;
  font-size: 0.82rem;
  font-weight: 700;
  color: #0f172a;
  padding-top: 0.35rem;
  font-variant-numeric: tabular-nums;
}}
.ips-timekeeping-row-expand:has(.ips-time-day-edit-marker) [data-testid="stHorizontalBlock"] [data-testid="stButton"] > button {{
  min-height: 1.65rem !important;
  padding: 0.1rem 0.2rem !important;
  font-size: 0.72rem !important;
  line-height: 1 !important;
}}
.ips-timekeeping-row-expand:has(.ips-time-day-edit-marker) [data-testid="stNumberInput"] input {{
  min-height: 1.65rem !important;
  padding: 0.15rem 0.2rem !important;
  font-size: 0.78rem !important;
  text-align: center;
}}
.ips-timekeeping-expand-title {{
  margin: 0 0 0.65rem;
  color: #0f172a;
  font-size: 0.8125rem;
  font-weight: 700;
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
.ips-timekeeping-week-range-wrap {{
  width: 100%;
  text-align: right;
  padding: 0.15rem 0 0;
}}
.st-key-tk_week_nav > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] > [data-testid="column"]:last-child {{
  min-width: 220px !important;
  flex: 1.5 1 auto !important;
}}
.st-key-tk_week_nav .ips-timekeeping-week-range-wrap,
.st-key-tk_week_nav .ips-time-week-range,
.st-key-tk_week_nav .ips-time-week-sub {{
  display: block !important;
  visibility: visible !important;
  opacity: 1 !important;
}}
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timekeeping-list-header-marker) .ips-timekeeping-day-header,
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timekeeping-list-header-marker) .timekeeping-header-day-label,
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timekeeping-list-header-marker) .timekeeping-header-status-badge,
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timekeeping-list-row-header-marker) .ips-timekeeping-day-header,
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timekeeping-list-row-header-marker) .timekeeping-header-day-label,
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timekeeping-list-row-header-marker) .timekeeping-header-status-badge,
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timekeeping-list-row-header-marker) .timekeeping-header-summary-label {{
  display: flex !important;
  visibility: visible !important;
  opacity: 1 !important;
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
.ips-time-hgrid-scroll {{
  overflow-x: auto;
  overflow-y: visible;
  -webkit-overflow-scrolling: touch;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  margin-bottom: 0.45rem;
  max-width: 100%;
}}
.ips-time-hgrid-scroll .ips-time-hgrid-wrap {{
  min-width: 0;
  border: none;
  border-radius: 0;
  margin-bottom: 0;
}}
.ips-time-hgrid-wrap {{
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  overflow: hidden;
  margin-bottom: 0.45rem;
}}
.ips-time-hgrid-head {{
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  padding: 4px 2px;
  font-size: 0.62rem;
  font-weight: 800;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  text-align: center;
  min-height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1.1;
}}
.ips-time-hgrid-head:first-child {{
  text-align: left;
  justify-content: flex-start;
  padding-left: 6px;
}}
.ips-time-hgrid-head-sub {{
  margin-top: 0.05rem;
  font-size: 0.52rem;
  font-weight: 650;
  color: #94a3b8;
  text-transform: none;
  letter-spacing: 0;
  line-height: 1;
}}
.ips-time-hgrid-employee {{
  font-size: 0.75rem;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.15;
  padding: 2px 0 0 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
.ips-time-hgrid-total {{
  font-size: 0.78rem;
  font-weight: 700;
  color: #0f172a;
  text-align: center;
  padding-top: 0.15rem;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  min-width: 3.25rem;
}}
.ips-time-hgrid-day-total {{
  font-size: 0.72rem;
  font-weight: 800;
  color: #94a3b8;
  text-align: center;
  padding-top: 0.18rem;
  font-variant-numeric: tabular-nums;
  line-height: 1.45rem;
}}
.ips-time-hgrid-day-total-active {{
  color: #0f172a;
}}
.ips-time-hgrid-locked {{
  padding: 2px 0;
}}
.ips-time-hgrid-locked-job {{
  font-size: 0.62rem;
  font-weight: 650;
  color: #475569;
  line-height: 1.15;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 0.15rem;
}}
.ips-time-hgrid-locked-row {{
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.25rem;
}}
.ips-timekeeping-status-pill-compact {{
  height: 14px;
  padding: 0 5px;
  font-size: 0.55rem;
  font-weight: 700;
  margin-top: 4px;
}}
.weekly-timesheet-row-marker,
.weekly-timesheet-day-marker,
.weekly-timesheet-job-marker,
.weekly-timesheet-hrs-marker,
.weekly-timesheet-stepper-marker,
.weekly-timesheet-expand-marker,
.timesheet-list-row-marker,
.timesheet-list-day-marker,
.timesheet-list-days-marker,
.timekeeping-list-header-marker,
.timekeeping-list-row-marker,
.timekeeping-list-row-header-marker,
.timekeeping-list-row-header-pad,
.timekeeping-list-spacer-marker,
.timekeeping-expand-detail-panel {{
  display: none !important;
}}
.weekly-timesheet-employee {{
  min-width: 0;
}}
.st-key-tk_hgrid_wrap .weekly-timesheet-employee,
.st-key-tk_page_hgrid_wrap .weekly-timesheet-employee {{
  overflow: hidden;
}}
.weekly-timesheet-employee-name {{
  font-size: 12px;
  font-weight: 800;
  color: #111827;
  white-space: nowrap;
}}
.st-key-tk_hgrid_wrap .weekly-timesheet-employee-name,
.st-key-tk_page_hgrid_wrap .weekly-timesheet-employee-name {{
  overflow: hidden;
  text-overflow: ellipsis;
}}
.timesheet-list-drag-handle {{
  display: block;
  color: #94a3b8;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: -3px;
  line-height: 1;
  text-align: center;
  user-select: none;
  margin-bottom: 2px;
}}
.timesheet-list-name-input {{
  box-sizing: border-box;
  width: 220px;
  min-width: 220px;
  max-width: 220px;
  min-height: 58px;
  height: 58px;
  display: flex;
  align-items: center;
  padding: 0 14px;
  border: 1px solid #d1d5db;
  border-radius: 9px;
  background: #ffffff;
  font-size: 14px;
  font-weight: 600;
  color: #111827;
  white-space: nowrap;
  overflow: visible;
  text-overflow: clip;
  line-height: 1.2;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] .timesheet-list-employee-cell .weekly-timesheet-employee-name,
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] .timesheet-list-employee-cell .employee-name.ips-timekeeping-employee {{
  border: none !important;
  border-radius: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
  padding: 0 !important;
  margin: 0 !important;
  min-height: 0 !important;
  height: auto !important;
  width: auto !important;
  min-width: 0 !important;
  max-width: 100% !important;
  display: block !important;
  font-size: 14px !important;
  font-weight: 700 !important;
  color: #2563eb !important;
  cursor: pointer !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] .timesheet-list-employee-cell .weekly-timesheet-employee-name:hover,
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] .timesheet-list-employee-cell .employee-name.ips-timekeeping-employee:hover {{
  color: #1d4ed8 !important;
  text-decoration: underline !important;
}}
.timesheet-list-hour-box,
.timesheet-list-hour-box-ro {{
  box-sizing: border-box;
  width: 96px;
  min-width: 90px;
  height: 46px;
  min-height: 46px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 8px;
  border: 1px solid #d8dee8;
  border-radius: 8px;
  background: #ffffff;
  font-size: 14px;
  font-weight: 600;
  color: #111827;
  font-variant-numeric: tabular-nums;
  text-align: center;
  margin: 0 auto;
}}
.weekly-timesheet-day {{
  width: 100%;
  min-width: 0;
  max-width: 100%;
  overflow: hidden;
}}
{tk_list_outer_row} {{
  display: grid !important;
  flex-wrap: nowrap !important;
  align-items: center !important;
  gap: 8px !important;
  column-gap: 8px !important;
  grid-template-columns: {tk_list_outer_grid} !important;
  width: max-content !important;
  min-width: 1382px !important;
  max-width: none !important;
  box-sizing: border-box !important;
  padding: 10px 12px !important;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04) !important;
  overflow: visible !important;
}}
{tk_list_data_row},
{tk_list_summary_row} {{
  min-height: {tk_list_row_h} !important;
  height: auto !important;
  max-height: none !important;
  overflow: visible !important;
  align-items: center !important;
  padding: 6px 10px !important;
  box-sizing: border-box !important;
  flex: 0 0 auto !important;
}}
{tk_expand} {{
  margin: 6px 0 0 0 !important;
  padding: 10px 12px 8px !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: 10px !important;
  background: #fafbfc !important;
  height: auto !important;
  min-height: 0 !important;
  max-height: none !important;
  overflow-x: auto !important;
  overflow-y: visible !important;
  -webkit-overflow-scrolling: touch;
  width: 100% !important;
  max-width: 100% !important;
  box-sizing: border-box !important;
}}
{tk_expand}:has(.timekeeping-detail-grid-readonly) {tk_detail_row},
{tk_expand}:has(.timekeeping-detail-grid-edit) {tk_detail_row} {{
  display: grid !important;
  flex-wrap: nowrap !important;
  align-items: center !important;
  gap: 10px !important;
  column-gap: 10px !important;
  width: 100% !important;
  max-width: none !important;
  box-sizing: border-box !important;
  padding: 6px 4px !important;
  margin: 0 !important;
  min-height: 0 !important;
  overflow: visible !important;
  box-shadow: none !important;
  border: none !important;
  background: transparent !important;
}}
{tk_expand}:has(.timekeeping-detail-grid-readonly) {tk_detail_row} {{
  grid-template-columns: {tk_detail_grid_readonly} !important;
  min-width: 1580px !important;
  width: max-content !important;
}}
{tk_expand}:has(.timekeeping-detail-grid-edit) {tk_detail_row} {{
  grid-template-columns: {tk_detail_grid_edit} !important;
  min-width: 1620px !important;
  width: max-content !important;
}}
{tk_detail_row} > [data-testid="column"] {{
  flex: unset !important;
  width: auto !important;
  min-width: 0 !important;
  max-width: none !important;
  overflow: visible !important;
  padding: 0 !important;
  margin: 0 !important;
  align-self: center !important;
}}
{tk_detail_row} > [data-testid="column"] [data-testid="stVerticalBlock"],
{tk_detail_row} > [data-testid="column"] [data-testid="stElementContainer"] {{
  width: 100% !important;
  min-width: 0 !important;
  overflow: visible !important;
}}
{tk_detail_row} .timekeeping-detail-head,
{tk_detail_row} .timekeeping-detail-cell {{
  display: block !important;
  visibility: visible !important;
  opacity: 1 !important;
  width: 100% !important;
  max-width: 100% !important;
}}
{tk_detail_row} > [data-testid="column"]:nth-child(1),
{tk_detail_row} > [data-testid="column"]:nth-child(2) {{
  min-width: 0 !important;
  overflow: visible !important;
}}
{tk_detail_row} > [data-testid="column"]:nth-child(1) {{
  min-width: 112px !important;
}}
{tk_detail_row} > [data-testid="column"]:nth-child(2) {{
  min-width: 132px !important;
}}
{tk_detail_row} .timekeeping-detail-day-cell,
{tk_detail_row} .timekeeping-detail-date-cell,
{tk_detail_row} > [data-testid="column"]:nth-child(1) .timekeeping-detail-head,
{tk_detail_row} > [data-testid="column"]:nth-child(2) .timekeeping-detail-head {{
  overflow: visible !important;
  text-overflow: clip !important;
  white-space: nowrap !important;
}}
{tk_detail_row} .timekeeping-detail-day-cell {{
  font-weight: 600 !important;
}}
{tk_detail_row} > [data-testid="column"]:nth-child(3) {{
  min-width: 380px !important;
  max-width: none !important;
  overflow: visible !important;
}}
{tk_detail_row} > [data-testid="column"]:has(.timekeeping-detail-assignment-marker),
{tk_detail_row} > [data-testid="column"]:has(.ips-time-day-job-marker) {{
  min-width: 380px !important;
  overflow: visible !important;
}}
{tk_detail_row} > [data-testid="column"]:nth-child(3) [data-testid="stSelectbox"],
{tk_detail_row} > [data-testid="column"]:has(.timekeeping-detail-assignment-marker) [data-testid="stSelectbox"],
{tk_detail_row} > [data-testid="column"]:nth-child(3) [data-testid="stSelectbox"] div[data-baseweb="select"],
{tk_detail_row} > [data-testid="column"]:nth-child(3) [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
{tk_detail_row} > [data-testid="column"]:has(.timekeeping-detail-assignment-marker) [data-testid="stSelectbox"] div[data-baseweb="select"],
{tk_detail_row} > [data-testid="column"]:has(.timekeeping-detail-assignment-marker) [data-testid="stSelectbox"] div[data-baseweb="select"] > div {{
  width: 100% !important;
  min-width: 360px !important;
  max-width: none !important;
  display: block !important;
  visibility: visible !important;
  opacity: 1 !important;
  background: #ffffff !important;
  border: 1px solid #d1d5db !important;
  border-radius: 8px !important;
  min-height: 38px !important;
  box-shadow: none !important;
}}
{tk_detail_row} > [data-testid="column"]:nth-child(3) [data-testid="stSelectbox"] div[data-baseweb="select"] span,
{tk_detail_row} > [data-testid="column"]:has(.timekeeping-detail-assignment-marker) [data-testid="stSelectbox"] div[data-baseweb="select"] span {{
  white-space: nowrap !important;
  overflow: visible !important;
  text-overflow: clip !important;
  max-width: none !important;
}}
{tk_detail_row} > [data-testid="column"]:nth-child(4) [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-hour-stepper),
{tk_detail_row} > [data-testid="column"]:nth-child(5) [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-hour-stepper) {{
  display: grid !important;
  grid-template-columns: 32px minmax(52px, 1fr) 32px !important;
  width: 100% !important;
  max-width: 118px !important;
  min-width: 108px !important;
  height: 38px !important;
  border: 1px solid #d8dee8 !important;
  border-radius: 8px !important;
  overflow: hidden !important;
  background: #ffffff !important;
  margin: 0 !important;
}}
{tk_detail_row} > [data-testid="column"]:nth-child(4) [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-hour-stepper) [data-testid="stNumberInput"] input,
{tk_detail_row} > [data-testid="column"]:nth-child(5) [data-testid="stHorizontalBlock"]:has(.timekeeping-detail-hour-stepper) [data-testid="stNumberInput"] input {{
  font-size: 13px !important;
  font-weight: 700 !important;
  text-align: center !important;
}}
{tk_detail_row} > [data-testid="column"]:nth-child(7) {{
  min-width: 100px !important;
}}
{tk_detail_row} > [data-testid="column"]:nth-child(7) .ips-timekeeping-status-pill {{
  min-width: 92px !important;
}}
{tk_detail_row} > [data-testid="column"]:nth-child(8) {{
  min-width: 132px !important;
}}
{tk_detail_row} > [data-testid="column"]:nth-child(8) [data-testid="stButton"] {{
  width: 100% !important;
}}
{tk_detail_row} > [data-testid="column"]:nth-child(8) [data-testid="stButton"] button {{
  width: 100% !important;
  min-width: 0 !important;
  white-space: nowrap !important;
}}
{tk_detail_row} > [data-testid="column"]:nth-child(9) [data-testid="stTextInput"],
{tk_detail_row} > [data-testid="column"]:nth-child(9) [data-testid="stTextInput"] > div,
{tk_detail_row} > [data-testid="column"]:nth-child(9) [data-testid="stTextInput"] input {{
  width: 100% !important;
  min-width: 0 !important;
  max-width: 100% !important;
}}
.st-key-tk_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker),
.st-key-tk_page_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) {{
  display: grid !important;
  flex-wrap: nowrap !important;
  align-items: center !important;
  gap: 10px !important;
  column-gap: 10px !important;
  width: 100% !important;
  max-width: 100% !important;
  box-sizing: border-box !important;
  min-width: 0 !important;
  overflow: hidden !important;
}}
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timekeeping-list-header-marker) {{
  padding: 8px 12px !important;
}}
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timekeeping-list-row-header-marker) {{
  padding: 6px 4px 4px !important;
  margin: 0 !important;
  border-bottom: 1px solid #e8edf3 !important;
  background: #ffffff !important;
}}
.ips-timekeeping-row-column-header {{
  width: 100% !important;
  min-height: 44px !important;
  justify-content: center !important;
}}
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timekeeping-list-row-header-marker) .timekeeping-header-day-label,
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timekeeping-list-row-header-marker) .timekeeping-header-status-badge,
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timekeeping-list-row-header-marker) .timekeeping-header-draft-badge,
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timekeeping-list-row-header-marker) .timekeeping-header-summary-label {{
  display: block !important;
  visibility: visible !important;
  opacity: 1 !important;
}}
{tk_list_day_col} {{
  width: {tk_list_day_w} !important;
  min-width: {tk_list_day_w} !important;
  max-width: {tk_list_day_w} !important;
  flex: 0 0 {tk_list_day_w} !important;
  padding: 0 !important;
  margin: 0 !important;
  overflow: visible !important;
  position: static !important;
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  justify-content: flex-start !important;
  box-sizing: border-box !important;
}}
{tk_list_sun_col} {{
  overflow: hidden !important;
  box-sizing: border-box !important;
}}
{tk_list_sun_col} [class*="st-key-tk_list_hour_spin_"] {{
  width: {tk_list_spin_w} !important;
  max-width: {tk_list_spin_w} !important;
  margin-left: auto !important;
  margin-right: auto !important;
}}
{tk_list_spacer_col} {{
  width: 24px !important;
  min-width: 24px !important;
  max-width: 24px !important;
  flex: 0 0 24px !important;
  padding: 0 !important;
  margin: 0 !important;
  overflow: hidden !important;
  position: static !important;
  box-sizing: border-box !important;
}}
{tk_list_spacer_col} [data-testid="stVerticalBlock"],
{tk_list_spacer_col} [data-testid="stElementContainer"] {{
  width: 100% !important;
  min-height: 1px !important;
  padding: 0 !important;
  margin: 0 !important;
}}
{tk_list_summary_col} {{
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  justify-content: flex-start !important;
  overflow: visible !important;
  position: static !important;
  box-sizing: border-box !important;
}}
{tk_list_outer_row} > [data-testid="column"]:nth-child(12) {{
  width: 76px !important;
  min-width: 76px !important;
  max-width: 76px !important;
  flex: 0 0 76px !important;
  padding: 0 2px !important;
  margin: 0 !important;
  border-left: 1px solid #e2e8f0 !important;
  overflow: visible !important;
  position: static !important;
  box-sizing: border-box !important;
}}
{tk_list_outer_row} > [data-testid="column"]:nth-child(13) {{
  width: 68px !important;
  min-width: 68px !important;
  max-width: 68px !important;
  flex: 0 0 68px !important;
  padding: 0 2px !important;
  overflow: visible !important;
  position: static !important;
  box-sizing: border-box !important;
}}
{tk_list_outer_row} > [data-testid="column"]:nth-child(14) {{
  width: 78px !important;
  min-width: 78px !important;
  max-width: 78px !important;
  flex: 0 0 78px !important;
  padding: 0 2px !important;
  overflow: visible !important;
  position: static !important;
  box-sizing: border-box !important;
}}
{tk_list_outer_row} > [data-testid="column"]:nth-child(15) {{
  width: 104px !important;
  min-width: 104px !important;
  max-width: 104px !important;
  flex: 0 0 104px !important;
  padding: 0 4px !important;
  overflow: visible !important;
  position: static !important;
  box-sizing: border-box !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] .timekeeping-list-summary-wrap {{
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  width: 100%;
  max-width: 100%;
  margin: 0 auto;
  box-sizing: border-box;
}}
.timekeeping-summary-label {{
  font-size: 9px;
  font-weight: 800;
  color: #334155;
  text-transform: uppercase;
  letter-spacing: 0.01em;
  white-space: nowrap;
  text-align: center;
  line-height: 1.1;
  margin: 0 0 4px 0;
  width: 100%;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] .timekeeping-list-summary-wrap .timekeeping-status-cell,
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] .timekeeping-list-summary-wrap .timesheet-list-status-cell {{
  min-height: 34px !important;
  max-height: 34px !important;
}}
{tk_list_data_row} .timesheet-list-summary-cell {{
  height: 34px !important;
  min-height: 34px !important;
  max-height: 34px !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
}}
{tk_list_summary_col} .ips-timekeeping-header-row,
{tk_list_summary_col} .ips-table-header-filter-text {{
  font-size: 9px !important;
  letter-spacing: 0.01em !important;
  padding: 2px 4px !important;
  white-space: nowrap !important;
}}
{tk_list_summary_col} .timesheet-list-summary-cell {{
  font-size: 12px !important;
  padding: 0 2px !important;
}}
.timekeeping-total-cell,
.timekeeping-overtime-cell,
.timekeeping-billed-cell,
.timekeeping-status-cell,
{tk_list_summary_col} .timesheet-list-summary-cell,
{tk_list_summary_col} .timesheet-list-status-cell {{
  position: static !important;
  inset: auto !important;
  transform: none !important;
  float: none !important;
}}
.st-key-tk_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker),
.st-key-tk_page_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) {{
  grid-template-columns:
    minmax(0, 180px)
    repeat(7, minmax(130px, 140px))
    minmax(0, 70px) !important;
  padding: 8px 10px !important;
  gap: 6px !important;
}}
.st-key-tk_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) > [data-testid="column"],
.st-key-tk_page_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) > [data-testid="column"] {{
  flex: unset !important;
  width: auto !important;
  box-sizing: border-box !important;
}}
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timekeeping-list-header-marker) > [data-testid="column"],
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timekeeping-list-row-header-marker) > [data-testid="column"],
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timesheet-list-row-marker) > [data-testid="column"] {{
  flex: unset !important;
  overflow: visible !important;
  position: static !important;
  float: none !important;
  transform: none !important;
  box-sizing: border-box !important;
}}
.st-key-tk_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) > [data-testid="column"],
.st-key-tk_page_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) > [data-testid="column"] {{
  min-width: 0 !important;
  max-width: 100% !important;
  overflow: hidden !important;
}}
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timekeeping-list-header-marker) > [data-testid="column"],
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timekeeping-list-row-header-marker) > [data-testid="column"],
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timesheet-list-row-marker) > [data-testid="column"] {{
  align-self: center !important;
}}
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timesheet-list-row-marker) > [data-testid="column"]:first-child,
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timekeeping-list-header-marker) > [data-testid="column"]:first-child,
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timekeeping-list-row-header-marker) > [data-testid="column"]:first-child {{
  width: 24px !important;
  min-width: 24px !important;
  max-width: 24px !important;
  padding: 0 !important;
  overflow: visible !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
}}
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timesheet-list-row-marker) > [data-testid="column"]:nth-child(2),
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timekeeping-list-header-marker) > [data-testid="column"]:nth-child(2),
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timekeeping-list-row-header-marker) > [data-testid="column"]:nth-child(2) {{
  width: 32px !important;
  min-width: 32px !important;
  max-width: 32px !important;
  padding: 0 !important;
  overflow: visible !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
}}
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timesheet-list-row-marker) > [data-testid="column"]:nth-child(3),
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timekeeping-list-header-marker) > [data-testid="column"]:nth-child(3),
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timekeeping-list-row-header-marker) > [data-testid="column"]:nth-child(3) {{
  width: 220px !important;
  min-width: 220px !important;
  max-width: 220px !important;
  overflow: visible !important;
}}
.st-key-tk_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) > [data-testid="column"]:first-child,
.st-key-tk_page_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) > [data-testid="column"]:first-child,
.st-key-tk_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) > [data-testid="column"]:nth-child(n+2):nth-child(-n+8),
.st-key-tk_page_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) > [data-testid="column"]:nth-child(n+2):nth-child(-n+8),
.st-key-tk_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) > [data-testid="column"]:last-child,
.st-key-tk_page_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) > [data-testid="column"]:last-child {{
  min-width: 0 !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] .timesheet-list-employee-cell {{
  display: flex;
  align-items: center;
  min-width: 220px;
  min-height: 0;
  max-height: 100%;
  line-height: 1.2;
  overflow: visible;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] .timesheet-list-employee-cell .timesheet-list-name-input {{
  font-size: 14px;
  font-weight: 600;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] .timesheet-list-day-heading,
.timekeeping-day-label,
.timekeeping-day-date-label {{
  font-size: 10px;
  font-weight: 800;
  color: #0f172a;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  white-space: nowrap;
  text-align: center;
  line-height: 1.15;
  margin: 0 0 2px 0;
  width: 100%;
  max-width: {tk_list_day_w};
}}
.timekeeping-day-cell {{
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  width: {tk_list_day_w};
  max-width: {tk_list_day_w};
  min-width: {tk_list_day_w};
  margin: 0 auto;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}}
{tk_list_data_row} .timekeeping-day-cell,
{tk_list_data_row} .timekeeping-list-summary-wrap {{
  justify-content: center !important;
}}
{tk_list_data_row} .timekeeping-day-label,
{tk_list_data_row} .timekeeping-summary-label {{
  margin: 0 0 2px 0 !important;
  line-height: 1 !important;
}}
.timekeeping-hour-input,
.timekeeping-hour-input-ro,
.timekeeping-list-hour-value {{
  box-sizing: border-box;
  width: auto;
  min-width: 0;
  max-width: 100%;
  height: auto;
  min-height: 0;
  display: block;
  align-items: center;
  justify-content: center;
  padding: 2px 0 0;
  border: none !important;
  border-radius: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
  font-variant-numeric: tabular-nums;
  text-align: center;
  margin: 0 auto;
  line-height: 1.25;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_day_"] {{
  width: {tk_list_day_w} !important;
  max-width: {tk_list_day_w} !important;
  min-width: {tk_list_day_w} !important;
  margin: 0 auto !important;
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
  padding: 0 !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_day_"] > div {{
  width: {tk_list_day_w} !important;
  max-width: {tk_list_day_w} !important;
  min-width: {tk_list_day_w} !important;
  margin: 0 auto !important;
  padding: 0 !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_day_"] [data-testid="stVerticalBlock"] {{
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  justify-content: flex-start !important;
  width: {tk_list_day_w} !important;
  max-width: {tk_list_day_w} !important;
  min-width: {tk_list_day_w} !important;
  gap: 0 !important;
  margin: 0 auto !important;
}}
{tk_list_data_row} {tk_list_day_col} [data-testid="stVerticalBlock"],
{tk_list_data_row} {tk_list_day_col} [data-testid="stElementContainer"],
{tk_list_data_row} [class*="st-key-tk_list_day_"] [data-testid="stVerticalBlock"] {{
  justify-content: center !important;
  gap: 0 !important;
}}
{tk_list_day_col} .ips-timekeeping-header-row,
{tk_list_day_col} .ips-timekeeping-cell,
{tk_list_summary_col} .ips-timekeeping-header-row,
{tk_list_summary_col} .ips-timekeeping-cell {{
  text-align: center !important;
  justify-content: center !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] .timesheet-list-summary-cell {{
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  font-size: 13px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: #0f172a;
  line-height: 1.2;
  white-space: nowrap;
  overflow: visible;
  width: 100%;
  max-width: 100%;
  min-height: 36px;
  box-sizing: border-box;
}}
{tk_list_day_col} [data-testid="stElementContainer"],
{tk_list_day_col} [data-testid="stVerticalBlock"],
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_day_"] {{
  max-width: {tk_list_day_w} !important;
  overflow: hidden !important;
}}
{tk_list_outer_row} > [data-testid="column"]:nth-child(12) .timesheet-list-summary-cell,
{tk_list_outer_row} > [data-testid="column"]:nth-child(12) .timekeeping-total-cell {{
  padding-left: 0 !important;
  margin-left: 0 !important;
}}
{tk_list_summary_col} [data-testid="stVerticalBlock"],
{tk_list_summary_col} [data-testid="stElementContainer"] {{
  width: 100% !important;
  max-width: 100% !important;
  overflow: visible !important;
  position: static !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] .timesheet-list-status-cell,
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] .timekeeping-status-cell {{
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  min-height: 36px;
  width: 100% !important;
  max-width: 100% !important;
  overflow: visible !important;
  box-sizing: border-box !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] .timesheet-list-status-cell .ips-timekeeping-status-pill,
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] .timekeeping-status-cell .ips-timekeeping-status-pill {{
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  height: 26px !important;
  padding: 0 12px !important;
  font-size: 12px !important;
  font-weight: 800 !important;
  border-radius: 999px !important;
  white-space: nowrap !important;
  max-width: none !important;
  width: auto !important;
  flex-shrink: 0 !important;
  box-sizing: border-box !important;
  overflow: visible !important;
}}
{tk_list_outer_row} > [data-testid="column"]:nth-child(15) .ips-timekeeping-header-row,
{tk_list_outer_row} > [data-testid="column"]:nth-child(15) .ips-table-header-filter-text {{
  justify-content: center !important;
  text-align: center !important;
  width: 100% !important;
}}
{tk_list_day_col} {{
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  justify-content: flex-start !important;
  gap: 0 !important;
  padding: 2px 4px !important;
  box-sizing: border-box !important;
  overflow: visible !important;
  width: {tk_list_day_w} !important;
  min-width: {tk_list_day_w} !important;
  max-width: {tk_list_day_w} !important;
  flex: 0 0 {tk_list_day_w} !important;
}}
{tk_list_data_row} {tk_list_day_col} {{
  justify-content: center !important;
  padding: 0 2px !important;
  max-height: 100% !important;
  overflow: hidden !important;
}}
{tk_list_day_col}:has(.ips-time-week-day-filled):not(:has(.timekeeping-list-hour-spin-complete)) {{
  background: transparent !important;
  border-radius: 0 !important;
}}
{tk_list_day_col} [data-testid="stVerticalBlock"],
{tk_list_day_col} [data-testid="stElementContainer"] {{
  width: 100% !important;
  max-width: {tk_list_day_inner_w} !important;
  min-width: 0 !important;
  overflow: visible !important;
  align-items: center !important;
  justify-content: center !important;
  box-sizing: border-box !important;
}}
{tk_list_day_col}:has(.timekeeping-list-hour-spinner-marker) [data-testid="stVerticalBlock"],
{tk_list_day_col}:has(.timekeeping-list-hour-spinner-marker) [data-testid="stElementContainer"] {{
  overflow: visible !important;
}}
{tk_list_day_col}:not(:has(.timekeeping-list-hour-spinner-marker)) [data-testid="stNumberInput"] {{
  width: 96px !important;
  min-width: 90px !important;
  max-width: 96px !important;
  margin: 0 auto !important;
  overflow: visible !important;
  flex: 0 0 96px !important;
}}
{tk_list_day_col}:not(:has(.timekeeping-list-hour-spinner-marker)) [data-testid="stNumberInput"] > div {{
  padding: 0 !important;
  min-height: 46px !important;
  height: 46px !important;
  align-items: center !important;
  justify-content: center !important;
  display: flex !important;
  flex-direction: row !important;
  flex-wrap: nowrap !important;
  overflow: visible !important;
  width: 96px !important;
  min-width: 90px !important;
  max-width: 96px !important;
  gap: 0 !important;
}}
{tk_list_day_col}:not(:has(.timekeeping-list-hour-spinner-marker)) [data-testid="stNumberInput"] input {{
  box-sizing: border-box !important;
  width: 96px !important;
  min-width: 90px !important;
  max-width: 96px !important;
  height: 46px !important;
  min-height: 46px !important;
  padding: 0 8px !important;
  font-size: 14px !important;
  font-weight: 600 !important;
  text-align: center !important;
  border: 1px solid #d8dee8 !important;
  border-radius: 8px !important;
  background: #ffffff !important;
  box-shadow: none !important;
  font-variant-numeric: tabular-nums;
  writing-mode: horizontal-tb !important;
  -moz-appearance: textfield;
  flex: 1 1 auto !important;
}}
{tk_list_day_col}:not(:has(.timekeeping-list-hour-spinner-marker)) [data-testid="stNumberInputStepUp"],
{tk_list_day_col}:not(:has(.timekeeping-list-hour-spinner-marker)) [data-testid="stNumberInputStepDown"] {{
  display: none !important;
  width: 0 !important;
  min-width: 0 !important;
  max-width: 0 !important;
  height: 0 !important;
  overflow: hidden !important;
  opacity: 0 !important;
  pointer-events: none !important;
}}
{tk_list_day_col}:not(:has(.timekeeping-list-hour-spinner-marker)) [data-testid="stNumberInput"] [data-testid="stWidgetLabel"] {{
  display: none !important;
}}
{tk_list_day_col}:not(:has(.timekeeping-list-hour-spinner-marker)) [data-testid="stNumberInput"] input::-webkit-outer-spin-button,
{tk_list_day_col}:not(:has(.timekeeping-list-hour-spinner-marker)) [data-testid="stNumberInput"] input::-webkit-inner-spin-button {{
  -webkit-appearance: none;
  margin: 0;
}}
{tk_list_data_row} {tk_list_day_col}:not(:has(.timekeeping-list-hour-spinner-marker)) [data-testid="stNumberInput"] > div,
{tk_list_data_row} {tk_list_day_col}:not(:has(.timekeeping-list-hour-spinner-marker)) [data-testid="stNumberInput"] input,
{tk_list_data_row} .timekeeping-hour-input,
{tk_list_data_row} .timekeeping-hour-input-ro,
{tk_list_data_row} .timekeeping-list-hour-value,
{tk_list_data_row} .timesheet-list-hour-box,
{tk_list_data_row} .timesheet-list-hour-box-ro {{
  height: auto !important;
  min-height: 0 !important;
  max-height: none !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_hrs_"]:not([class*="st-key-tk_list_hour_spin_"]) [data-testid="stNumberInput"],
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_hrs_"]:not([class*="st-key-tk_list_hour_spin_"]) [data-testid="stNumberInput"] > div {{
  width: 96px !important;
  min-width: 90px !important;
  max-width: 96px !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_hrs_"]:not([class*="st-key-tk_list_hour_spin_"]) [data-testid="stNumberInput"] > div {{
  min-height: 46px !important;
  height: 46px !important;
  flex-direction: row !important;
  flex-wrap: nowrap !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_hrs_"]:not([class*="st-key-tk_list_hour_spin_"]) [data-testid="stNumberInput"] input {{
  box-sizing: border-box !important;
  width: auto !important;
  min-width: 0 !important;
  height: auto !important;
  border: none !important;
  border-radius: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
  text-align: center !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_hrs_"]:not([class*="st-key-tk_list_hour_spin_"]) [data-testid="stNumberInputStepUp"],
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_hrs_"]:not([class*="st-key-tk_list_hour_spin_"]) [data-testid="stNumberInputStepDown"] {{
  display: none !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_hour_spin_"] {{
  width: {tk_list_spin_w} !important;
  max-width: 100% !important;
  min-width: 0 !important;
  margin: 0 auto !important;
  padding: 0 !important;
  border: none !important;
  background: transparent !important;
  overflow: visible !important;
  box-sizing: border-box !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_hour_spin_"] > [data-testid="stVerticalBlock"] {{
  gap: 0 !important;
  align-items: center !important;
  width: 100% !important;
  min-width: 0 !important;
  max-width: {tk_list_spin_w} !important;
}}
.st-key-timekeeping_table_wrap .timekeeping-hour-spinner:not([data-testid]) {{
  display: none !important;
  height: 0 !important;
  overflow: hidden !important;
}}
{tk_list_spin_row} {{
  width: auto !important;
  min-width: 0 !important;
  max-width: 100% !important;
  height: auto !important;
  min-height: 0 !important;
  display: flex !important;
  flex-direction: row !important;
  align-items: center !important;
  justify-content: center !important;
  border: none !important;
  border-radius: 0 !important;
  background: transparent !important;
  overflow: visible !important;
  gap: 2px !important;
  padding: 2px 0 0 !important;
  margin: 0 auto !important;
  box-sizing: border-box !important;
}}
{tk_list_spin_row}:focus-within {{
  outline: none !important;
  border: none !important;
  box-shadow: none !important;
}}
{tk_list_spin_row} > [data-testid="column"] {{
  width: auto !important;
  flex: none !important;
  padding: 0 !important;
  margin: 0 !important;
  overflow: visible !important;
  display: block !important;
  visibility: visible !important;
}}
{tk_list_spin_row} > [data-testid="column"]:first-child,
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_hour_spin_"] [data-testid="column"]:has(.timekeeping-hour-input-marker) {{
  min-width: {tk_list_spin_input_w} !important;
  max-width: {tk_list_spin_input_w} !important;
  width: {tk_list_spin_input_w} !important;
  flex: 0 0 {tk_list_spin_input_w} !important;
  grid-column: 1 !important;
  grid-row: 1 !important;
  overflow: hidden !important;
}}
{tk_list_spin_row} > [data-testid="column"]:first-child [data-testid="stVerticalBlock"],
{tk_list_spin_row} > [data-testid="column"]:first-child [data-testid="stElementContainer"] {{
  width: 100% !important;
  min-width: 0 !important;
  max-width: 100% !important;
  padding: 0 !important;
  margin: 0 !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_hour_spin_"] [data-testid="stNumberInput"] {{
  width: 100% !important;
  min-width: 0 !important;
  max-width: 100% !important;
  margin: 0 !important;
  align-self: stretch !important;
  overflow: visible !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_hour_spin_"] [data-testid="stNumberInput"] > div {{
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
  min-height: 0 !important;
  height: 100% !important;
  width: 100% !important;
  max-width: 100% !important;
  display: flex !important;
  flex-direction: row !important;
  flex-wrap: nowrap !important;
  align-items: center !important;
  justify-content: center !important;
  padding: 0 !important;
  margin: 0 !important;
  gap: 0 !important;
  overflow: hidden !important;
  box-sizing: border-box !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_hour_spin_"] [data-testid="stNumberInput"] {{
  height: 100% !important;
  min-height: 0 !important;
}}
{tk_list_spin_row} > [data-testid="column"]:first-child [data-testid="stVerticalBlock"] {{
  height: 100% !important;
  min-height: 0 !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_hour_spin_"] [data-testid="column"]:has(.timekeeping-hour-input-marker) [data-testid="stNumberInput"] input {{
  box-sizing: border-box !important;
  width: auto !important;
  min-width: 0 !important;
  max-width: 100% !important;
  height: auto !important;
  min-height: 0 !important;
  flex: 0 1 auto !important;
  text-align: center !important;
  border: none !important;
  outline: none !important;
  box-shadow: none !important;
  background: transparent !important;
  font-size: 14px !important;
  font-weight: 600 !important;
  padding: 0 !important;
  margin: 0 !important;
  font-variant-numeric: tabular-nums;
  -moz-appearance: textfield;
  white-space: nowrap !important;
  overflow: visible !important;
  text-overflow: clip !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_hour_spin_"] [data-testid="stNumberInput"] input:focus {{
  outline: none !important;
  box-shadow: none !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_hour_spin_"] [data-testid="stNumberInput"] input::-webkit-outer-spin-button,
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_hour_spin_"] [data-testid="stNumberInput"] input::-webkit-inner-spin-button {{
  -webkit-appearance: none;
  margin: 0;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_hour_spin_"] [data-testid="stNumberInputStepUp"],
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_hour_spin_"] [data-testid="stNumberInputStepDown"] {{
  display: none !important;
  width: 0 !important;
  min-width: 0 !important;
  max-width: 0 !important;
  height: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  overflow: hidden !important;
  opacity: 0 !important;
  pointer-events: none !important;
  flex: 0 0 0 !important;
}}
{tk_list_spin_row} > [data-testid="column"]:last-child,
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_hour_spin_"] [data-testid="column"]:has(.timekeeping-spinner-buttons-marker) {{
  min-width: {tk_list_spin_btn_w} !important;
  max-width: {tk_list_spin_btn_w} !important;
  width: {tk_list_spin_btn_w} !important;
  flex: 0 0 {tk_list_spin_btn_w} !important;
  grid-column: 2 !important;
  grid-row: 1 !important;
  align-self: stretch !important;
  overflow: visible !important;
  padding: 0 !important;
  margin: 0 !important;
  visibility: visible !important;
}}
{tk_list_spin_row} > [data-testid="column"]:last-child [data-testid="stVerticalBlock"],
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_hour_spin_"] [data-testid="column"]:has(.timekeeping-spinner-buttons-marker) [data-testid="stVerticalBlock"] {{
  width: {tk_list_spin_btn_w} !important;
  min-width: {tk_list_spin_btn_w} !important;
  max-width: {tk_list_spin_btn_w} !important;
  display: flex !important;
  flex-direction: column !important;
  border-left: none !important;
  box-sizing: border-box !important;
  height: auto !important;
  min-height: 0 !important;
  gap: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  overflow: visible !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_hour_spin_"] [data-testid="column"]:has(.timekeeping-spinner-buttons-marker) [data-testid="stElementContainer"] {{
  width: {tk_list_spin_btn_w} !important;
  min-width: {tk_list_spin_btn_w} !important;
  max-width: {tk_list_spin_btn_w} !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_hour_spin_"] [data-testid="column"]:has(.timekeeping-spinner-buttons-marker) [data-testid="stButton"] {{
  display: block !important;
  visibility: visible !important;
  opacity: 1 !important;
  width: {tk_list_spin_btn_w} !important;
  min-width: {tk_list_spin_btn_w} !important;
  max-width: {tk_list_spin_btn_w} !important;
  margin: 0 !important;
  flex: 1 1 50% !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_hour_spin_"] [data-testid="column"]:has(.timekeeping-spinner-buttons-marker) [data-testid="stButton"] > button {{
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  visibility: visible !important;
  opacity: 1 !important;
  width: {tk_list_spin_btn_w} !important;
  min-width: {tk_list_spin_btn_w} !important;
  max-width: {tk_list_spin_btn_w} !important;
  height: 14px !important;
  min-height: 14px !important;
  padding: 0 !important;
  margin: 0 !important;
  border: none !important;
  border-radius: 0 !important;
  background: transparent !important;
  color: #64748b !important;
  font-size: 10px !important;
  font-weight: 700 !important;
  line-height: 1 !important;
  box-sizing: border-box !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_hour_spin_"] [data-testid="column"]:has(.timekeeping-spinner-buttons-marker) [data-testid="stButton"]:first-of-type > button {{
  border-bottom: none !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_hour_spin_"] [data-testid="column"]:has(.timekeeping-spinner-buttons-marker) [data-testid="stButton"] > button:hover {{
  background: transparent !important;
  color: #2563eb !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] {{
  min-width: 0;
}}
{tk_list_summary_row},
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="stHorizontalBlock"]:has(.timesheet-list-row-marker) {{
  background: #ffffff !important;
  border: 1px solid #e5e7eb !important;
  border-radius: 10px !important;
  margin-bottom: 0 !important;
  min-height: {tk_list_row_h} !important;
  height: auto !important;
  max-height: none !important;
  overflow: visible !important;
  align-items: center !important;
  box-sizing: border-box !important;
  flex: 0 0 auto !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="stHorizontalBlock"]:has(.timesheet-list-row-marker):hover {{
  background: #f8fbff !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="stHorizontalBlock"]:has(.timesheet-list-row-marker) > [data-testid="column"]:nth-child(2) [data-testid="stButton"],
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timekeeping-list-header-marker) > [data-testid="column"]:nth-child(2) [data-testid="stButton"] {{
  width: 22px !important;
  min-width: 22px !important;
  max-width: 22px !important;
  margin: 0 !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="stHorizontalBlock"]:has(.timesheet-list-row-marker) > [data-testid="column"]:nth-child(2) [data-testid="stButton"] button,
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timekeeping-list-header-marker) > [data-testid="column"]:nth-child(2) [data-testid="stButton"] button {{
  width: 22px !important;
  min-width: 22px !important;
  max-width: 22px !important;
  height: 22px !important;
  min-height: 22px !important;
  padding: 0 !important;
  font-size: 10px !important;
  white-space: nowrap !important;
  border-radius: 6px !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] .employee-name:not(.timesheet-list-name-input),
.st-key-tk_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) .employee-name,
.st-key-tk_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) .weekly-timesheet-employee-name,
.st-key-tk_page_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) .employee-name,
.st-key-tk_page_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) .weekly-timesheet-employee-name {{
  font-size: 12px;
  font-weight: 800;
  color: #111827;
  white-space: nowrap !important;
  overflow: hidden;
  text-overflow: ellipsis;
  word-break: normal !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] .timesheet-list-name-input {{
  overflow: visible !important;
  text-overflow: clip !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] .employee-name.ips-timekeeping-employee,
.st-key-tk_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) .employee-name.ips-timekeeping-employee {{
  word-break: normal !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] .employee-label,
.st-key-tk_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) .employee-label {{
  font-size: 10px;
  font-weight: 800;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 4px;
  display: block;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] .day-header,
.st-key-tk_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) .day-header,
.st-key-tk_page_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) .day-header {{
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 4px;
  margin-bottom: 4px;
  white-space: nowrap;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] .day-label,
.st-key-tk_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) .day-label,
.st-key-tk_page_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) .day-label,
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] .weekly-timesheet-day-label,
.st-key-tk_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) .weekly-timesheet-day-label,
.st-key-tk_page_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) .weekly-timesheet-day-label {{
  font-size: 9px;
  font-weight: 900;
  color: #111827;
  white-space: nowrap;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] .day-date,
.st-key-tk_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) .day-date,
.st-key-tk_page_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) .day-date,
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] .weekly-timesheet-day-date,
.st-key-tk_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) .weekly-timesheet-day-date,
.st-key-tk_page_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) .weekly-timesheet-day-date {{
  font-size: 9px;
  font-weight: 500;
  color: #64748b;
  white-space: nowrap;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] .week-total,
.st-key-tk_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) .week-total,
.st-key-tk_page_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) .week-total,
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] .weekly-timesheet-week-total,
.st-key-tk_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) .weekly-timesheet-week-total,
.st-key-tk_page_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) .weekly-timesheet-week-total {{
  font-size: 11px;
  font-weight: 800;
  text-align: center;
  white-space: nowrap;
  line-height: 1.1;
}}
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timekeeping-list-header-marker) .ips-timekeeping-header-row,
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timekeeping-list-header-marker) .ips-table-header-filter-text,
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timekeeping-list-row-header-marker) .ips-timekeeping-header-row,
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timekeeping-list-row-header-marker) .timekeeping-header-summary-label {{
  white-space: nowrap;
}}
.st-key-timekeeping_table_wrap {{
  overflow-x: hidden;
  max-width: 100%;
  width: 100%;
  box-sizing: border-box;
}}
.st-key-timekeeping_table_wrap > [data-testid="stVerticalBlock"] {{
  overflow-x: visible;
  min-width: 0;
  max-width: 100%;
  width: 100%;
}}
.st-key-timekeeping_table_wrap.ips-table-fit-host {{
  overflow-x: hidden !important;
}}
@media (max-width: 900px) {{
  .st-key-timekeeping_table_wrap,
  .st-key-timekeeping_table_wrap > [data-testid="stVerticalBlock"],
  .timekeeping-list-scroll {{
    overflow-x: hidden;
    max-width: 100%;
  }}
  {tk_list_outer_row} {{
    min-width: 1382px !important;
  }}
  .ips-time-hgrid-scroll {{
    overflow-x: auto;
  }}
  .ips-time-hgrid-scroll .ips-time-hgrid-wrap {{
    min-width: 1180px;
  }}
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="column"]:has(.weekly-timesheet-day-marker),
.st-key-tk_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-day-marker),
.st-key-tk_page_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-day-marker) {{
  width: 100% !important;
  min-width: 130px !important;
  max-width: 140px !important;
  padding: 0 !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="column"]:has(.weekly-timesheet-day-marker) [data-testid="stVerticalBlock"],
.st-key-tk_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-day-marker) [data-testid="stVerticalBlock"],
.st-key-tk_page_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-day-marker) [data-testid="stVerticalBlock"] {{
  align-items: flex-start !important;
  width: 100% !important;
  gap: 1px !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="column"]:has(.weekly-timesheet-day-marker) [data-testid="stElementContainer"],
.st-key-tk_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-day-marker) [data-testid="stElementContainer"],
.st-key-tk_page_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-day-marker) [data-testid="stElementContainer"] {{
  width: auto !important;
  max-width: 100% !important;
  margin: 0 !important;
  padding: 0 !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) [data-testid="stElementContainer"],
.st-key-tk_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) [data-testid="stElementContainer"],
.st-key-tk_page_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) [data-testid="stElementContainer"] {{
  margin: 0 !important;
  padding: 0 !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="column"]:has(.weekly-timesheet-job-marker) [data-testid="stSelectbox"],
.st-key-tk_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-job-marker) [data-testid="stSelectbox"],
.st-key-tk_page_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-job-marker) [data-testid="stSelectbox"] {{
  width: 100% !important;
  max-width: 120px !important;
  margin-bottom: 0 !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="column"]:has(.weekly-timesheet-job-marker) [data-testid="stSelectbox"] div[data-baseweb="select"],
.st-key-tk_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-job-marker) [data-testid="stSelectbox"] div[data-baseweb="select"],
.st-key-tk_page_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-job-marker) [data-testid="stSelectbox"] div[data-baseweb="select"] {{
  width: 100% !important;
  max-width: 120px !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="column"]:has(.weekly-timesheet-job-marker) [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
.st-key-tk_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-job-marker) [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
.st-key-tk_page_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-job-marker) [data-testid="stSelectbox"] div[data-baseweb="select"] > div {{
  width: 100% !important;
  max-width: 120px !important;
  height: 32px !important;
  min-height: 32px !important;
  font-size: 10px !important;
  border-radius: 7px !important;
  padding: 2px 4px !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="column"]:has(.weekly-timesheet-job-marker) [data-testid="stSelectbox"] div[data-baseweb="select"] span,
.st-key-tk_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-job-marker) [data-testid="stSelectbox"] div[data-baseweb="select"] span,
.st-key-tk_page_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-job-marker) [data-testid="stSelectbox"] div[data-baseweb="select"] span {{
  font-size: 10px !important;
}}
.timekeeping-hours-control-label {{
  width: 100%;
  text-align: center;
  margin: 2px 0 4px 0;
  line-height: 1;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="column"]:has(.weekly-timesheet-hrs-marker) .timekeeping-hours-control-label .hrs-label,
.st-key-tk_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-hrs-marker) .timekeeping-hours-control-label .hrs-label,
.st-key-tk_page_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-hrs-marker) .timekeeping-hours-control-label .hrs-label {{
  font-size: 9px;
  font-weight: 800;
  color: #334155;
  letter-spacing: 0.04em;
  display: inline-block;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="column"]:has(.weekly-timesheet-stepper-marker):not(:has(.timekeeping-detail-hour-stepper)) [data-testid="stHorizontalBlock"],
.st-key-tk_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-stepper-marker) [data-testid="stHorizontalBlock"],
.st-key-tk_page_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-stepper-marker) [data-testid="stHorizontalBlock"] {{
  display: grid !important;
  grid-template-columns: 34px minmax(64px, 72px) 34px !important;
  width: 100% !important;
  max-width: 146px !important;
  min-width: 130px !important;
  height: 38px !important;
  border: 1px solid #d8dee8 !important;
  border-radius: 8px !important;
  overflow: hidden !important;
  background: #ffffff !important;
  gap: 0 !important;
  padding: 0 !important;
  margin: 0 auto !important;
  border-bottom: none !important;
  align-items: stretch !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="column"]:has(.weekly-timesheet-stepper-marker):not(:has(.timekeeping-detail-hour-stepper)) [data-testid="stNumberInput"],
.st-key-tk_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-stepper-marker) [data-testid="stNumberInput"],
.st-key-tk_page_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-stepper-marker) [data-testid="stNumberInput"] {{
  width: 100% !important;
  min-width: 64px !important;
  max-width: 72px !important;
  margin: 0 !important;
  grid-column: 2 !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="column"]:has(.weekly-timesheet-stepper-marker):not(:has(.timekeeping-detail-hour-stepper)) [data-testid="stNumberInput"] > div,
.st-key-tk_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-stepper-marker) [data-testid="stNumberInput"] > div,
.st-key-tk_page_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-stepper-marker) [data-testid="stNumberInput"] > div {{
  border: none !important;
  background: #ffffff !important;
  box-shadow: none !important;
  min-height: 38px !important;
  height: 38px !important;
  width: 100% !important;
  display: flex !important;
  flex-direction: row !important;
  align-items: center !important;
  justify-content: center !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="column"]:has(.weekly-timesheet-stepper-marker):not(:has(.timekeeping-detail-hour-stepper)) [data-testid="stNumberInput"] input,
.st-key-tk_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-stepper-marker) [data-testid="stNumberInput"] input,
.st-key-tk_page_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-stepper-marker) [data-testid="stNumberInput"] input {{
  box-sizing: border-box !important;
  width: 100% !important;
  min-width: 64px !important;
  max-width: 72px !important;
  text-align: center !important;
  border: none !important;
  font-size: 12px !important;
  font-weight: 700 !important;
  padding: 0 4px !important;
  min-height: 38px !important;
  height: 38px !important;
  background: #ffffff !important;
  writing-mode: horizontal-tb !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="column"]:has(.weekly-timesheet-stepper-marker):not(:has(.timekeeping-detail-hour-stepper)) [data-testid="stNumberInputStepUp"],
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="column"]:has(.weekly-timesheet-stepper-marker):not(:has(.timekeeping-detail-hour-stepper)) [data-testid="stNumberInputStepDown"],
.st-key-tk_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-stepper-marker) [data-testid="stNumberInputStepUp"],
.st-key-tk_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-stepper-marker) [data-testid="stNumberInputStepDown"],
.st-key-tk_page_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-stepper-marker) [data-testid="stNumberInputStepUp"],
.st-key-tk_page_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-stepper-marker) [data-testid="stNumberInputStepDown"] {{
  display: none !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="column"]:has(.weekly-timesheet-stepper-marker):not(:has(.timekeeping-detail-hour-stepper)) [data-testid="stButton"],
.st-key-tk_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-stepper-marker) [data-testid="stButton"],
.st-key-tk_page_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-stepper-marker) [data-testid="stButton"] {{
  width: 100% !important;
  min-width: 0 !important;
  max-width: none !important;
  margin: 0 !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="column"]:has(.weekly-timesheet-stepper-marker):not(:has(.timekeeping-detail-hour-stepper)) [data-testid="stButton"] button,
.st-key-tk_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-stepper-marker) [data-testid="stButton"] button,
.st-key-tk_page_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-stepper-marker) [data-testid="stButton"] button {{
  width: 34px !important;
  min-width: 34px !important;
  max-width: 34px !important;
  height: 38px !important;
  min-height: 38px !important;
  padding: 0 !important;
  border: none !important;
  border-left: 1px solid #d8dee8 !important;
  border-radius: 0 !important;
  background: #f8fafc !important;
  font-size: 16px !important;
  font-weight: 700 !important;
  line-height: 1 !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="column"]:has(.weekly-timesheet-stepper-marker):not(:has(.timekeeping-detail-hour-stepper)) [data-testid="stHorizontalBlock"] > [data-testid="column"],
.st-key-tk_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-stepper-marker) [data-testid="stHorizontalBlock"] > [data-testid="column"],
.st-key-tk_page_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-stepper-marker) [data-testid="stHorizontalBlock"] > [data-testid="column"] {{
  padding: 0 !important;
  margin: 0 !important;
  min-width: 0 !important;
  overflow: visible !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="column"]:has(.weekly-timesheet-stepper-marker):not(:has(.timekeeping-detail-hour-stepper)) [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child,
.st-key-tk_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-stepper-marker) [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child,
.st-key-tk_page_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-stepper-marker) [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child {{
  width: 34px !important;
  min-width: 34px !important;
  max-width: 34px !important;
  grid-column: 1 !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="column"]:has(.weekly-timesheet-stepper-marker):not(:has(.timekeeping-detail-hour-stepper)) [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(2),
.st-key-tk_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-stepper-marker) [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(2),
.st-key-tk_page_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-stepper-marker) [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(2) {{
  width: auto !important;
  min-width: 64px !important;
  max-width: 72px !important;
  grid-column: 2 !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="column"]:has(.weekly-timesheet-stepper-marker):not(:has(.timekeeping-detail-hour-stepper)) [data-testid="stHorizontalBlock"] > [data-testid="column"]:last-child,
.st-key-tk_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-stepper-marker) [data-testid="stHorizontalBlock"] > [data-testid="column"]:last-child,
.st-key-tk_page_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-stepper-marker) [data-testid="stHorizontalBlock"] > [data-testid="column"]:last-child {{
  width: 34px !important;
  min-width: 34px !important;
  max-width: 34px !important;
  grid-column: 3 !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="column"]:has(.weekly-timesheet-stepper-marker):not(:has(.timekeeping-detail-hour-stepper)) [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child [data-testid="stButton"] button,
.st-key-tk_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-stepper-marker) [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child [data-testid="stButton"] button,
.st-key-tk_page_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-stepper-marker) [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child [data-testid="stButton"] button {{
  border-left: none !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker):not(:has(.timesheet-list-row-marker)) {{
  background: #ffffff !important;
  border: 1px solid #e5e7eb !important;
  border-radius: 8px !important;
  margin-bottom: 4px !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker):hover {{
  background: #f8fbff !important;
}}
.st-key-tk_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker),
.st-key-tk_page_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) {{
  background: #ffffff !important;
}}
.st-key-tk_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker):hover,
.st-key-tk_page_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker):hover {{
  background: #f8fbff !important;
}}
.st-key-tk_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) > [data-testid="column"]:first-child,
.st-key-tk_page_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) > [data-testid="column"]:first-child {{
  position: sticky;
  left: 0;
  z-index: 3;
  background: #ffffff;
  box-shadow: 4px 0 8px -4px rgba(15, 23, 42, 0.12);
}}
.st-key-tk_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker):hover > [data-testid="column"]:first-child,
.st-key-tk_page_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker):hover > [data-testid="column"]:first-child {{
  background: #f8fbff;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) [data-testid="stSelectbox"] [data-testid="stWidgetLabel"],
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) [data-testid="stNumberInput"] [data-testid="stWidgetLabel"],
.st-key-tk_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) [data-testid="stSelectbox"] [data-testid="stWidgetLabel"],
.st-key-tk_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) [data-testid="stNumberInput"] [data-testid="stWidgetLabel"],
.st-key-tk_page_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) [data-testid="stSelectbox"] [data-testid="stWidgetLabel"],
.st-key-tk_page_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) [data-testid="stNumberInput"] [data-testid="stWidgetLabel"] {{
  display: none !important;
}}
.st-key-tk_hgrid_wrap [data-testid="stVerticalBlock"],
.st-key-tk_page_hgrid_wrap [data-testid="stVerticalBlock"],
.st-key-ftp_wrap [data-testid="stVerticalBlock"] {{
  gap: 0 !important;
}}
.st-key-tk_hgrid_wrap [data-testid="stElementContainer"],
.st-key-tk_page_hgrid_wrap [data-testid="stElementContainer"],
.st-key-ftp_wrap [data-testid="stElementContainer"] {{
  margin: 0 !important;
  padding: 0 !important;
}}
.st-key-tk_hgrid_wrap [data-testid="column"] [data-testid="stVerticalBlock"],
.st-key-tk_page_hgrid_wrap [data-testid="column"] [data-testid="stVerticalBlock"],
.st-key-ftp_wrap [data-testid="column"] [data-testid="stVerticalBlock"] {{
  gap: 0 !important;
}}
.st-key-tk_hgrid_wrap [data-testid="stHorizontalBlock"]:not(:has(.weekly-timesheet-row-marker)),
.st-key-tk_page_hgrid_wrap [data-testid="stHorizontalBlock"]:not(:has(.weekly-timesheet-row-marker)),
.st-key-ftp_wrap [data-testid="stHorizontalBlock"]:not(:has(.weekly-timesheet-row-marker)) {{
  gap: 0.2rem !important;
  align-items: flex-start !important;
  border-bottom: 1px solid #e2e8f0;
  padding: 4px 6px !important;
  margin: 0 !important;
  min-height: 0 !important;
}}
.st-key-tk_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker),
.st-key-tk_page_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) {{
  border-bottom: 1px solid #e5e7eb !important;
  border-radius: 0 !important;
  margin: 0 !important;
  min-height: 0 !important;
}}
.st-key-tk_hgrid_wrap [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child:not(:has(.weekly-timesheet-row-marker)),
.st-key-tk_page_hgrid_wrap [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child:not(:has(.weekly-timesheet-row-marker)),
.st-key-ftp_wrap [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child {{
  position: sticky;
  left: 0;
  z-index: 3;
  background: #ffffff;
  box-shadow: 4px 0 8px -4px rgba(15, 23, 42, 0.12);
  min-width: 118px;
  max-width: 148px;
}}
.st-key-tk_hgrid_wrap [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:first-child,
.st-key-tk_page_hgrid_wrap [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:first-child,
.st-key-ftp_wrap [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:first-child {{
  background: #f8fafc;
  z-index: 4;
}}
.st-key-tk_hgrid_wrap [data-testid="stHorizontalBlock"]:not(:first-of-type):hover > [data-testid="column"]:first-child,
.st-key-tk_page_hgrid_wrap [data-testid="stHorizontalBlock"]:not(:first-of-type):hover > [data-testid="column"]:first-child,
.st-key-ftp_wrap [data-testid="stHorizontalBlock"]:not(:first-of-type):hover > [data-testid="column"]:first-child {{
  background: #eef5ff;
}}
.st-key-tk_hgrid_wrap [data-testid="stHorizontalBlock"]:first-of-type,
.st-key-tk_page_hgrid_wrap [data-testid="stHorizontalBlock"]:first-of-type {{
  grid-template-columns:
    minmax(0, 180px)
    repeat(7, minmax(130px, 140px))
    minmax(0, 70px) !important;
  display: grid !important;
  width: 100% !important;
  max-width: 100% !important;
  min-width: 0 !important;
  gap: 6px !important;
  padding: 6px 10px !important;
}}
.st-key-tk_hgrid_wrap [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"],
.st-key-tk_page_hgrid_wrap [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"] {{
  min-width: 0 !important;
  overflow: hidden !important;
}}
.st-key-tk_hgrid_wrap [data-testid="stHorizontalBlock"] > [data-testid="column"]:not(:first-child):not(:last-child):not(:has(.weekly-timesheet-day-marker)),
.st-key-tk_page_hgrid_wrap [data-testid="stHorizontalBlock"] > [data-testid="column"]:not(:first-child):not(:last-child):not(:has(.weekly-timesheet-day-marker)),
.st-key-ftp_wrap [data-testid="stHorizontalBlock"] > [data-testid="column"]:not(:first-child):not(:last-child) {{
  min-width: 130px;
}}
.st-key-tk_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-day-marker),
.st-key-tk_page_hgrid_wrap [data-testid="column"]:has(.weekly-timesheet-day-marker) {{
  min-width: 130px !important;
  max-width: 140px !important;
}}
.st-key-tk_hgrid_wrap [data-testid="stHorizontalBlock"]:not(:has(.weekly-timesheet-row-marker)) > [data-testid="column"]:last-child,
.st-key-tk_page_hgrid_wrap [data-testid="stHorizontalBlock"]:not(:has(.weekly-timesheet-row-marker)) > [data-testid="column"]:last-child {{
  min-width: 3.25rem;
}}
.st-key-tk_hgrid_wrap [data-testid="stHorizontalBlock"]:first-of-type,
.st-key-tk_page_hgrid_wrap [data-testid="stHorizontalBlock"]:first-of-type,
.st-key-ftp_wrap [data-testid="stHorizontalBlock"]:first-of-type {{
  background: #f8fafc;
  min-height: 24px;
  padding: 3px 4px !important;
}}
.st-key-tk_hgrid_wrap [data-testid="stHorizontalBlock"]:not(:first-of-type):hover,
.st-key-tk_page_hgrid_wrap [data-testid="stHorizontalBlock"]:not(:first-of-type):hover,
.st-key-ftp_wrap [data-testid="stHorizontalBlock"]:not(:first-of-type):hover {{
  background: #eef5ff;
}}
.st-key-tk_hgrid_wrap [data-testid="stSelectbox"],
.st-key-tk_page_hgrid_wrap [data-testid="stSelectbox"],
.st-key-ftp_wrap [data-testid="stSelectbox"],
.st-key-tk_hgrid_wrap [data-testid="stNumberInput"],
.st-key-tk_page_hgrid_wrap [data-testid="stNumberInput"],
.st-key-ftp_wrap [data-testid="stNumberInput"] {{
  margin-bottom: 0 !important;
}}
.st-key-tk_hgrid_wrap [data-testid="stNumberInput"] input,
.st-key-tk_page_hgrid_wrap [data-testid="stNumberInput"] input,
.st-key-ftp_wrap [data-testid="stNumberInput"] input {{
  text-align: center;
  padding: 0.25rem 0.35rem;
  min-height: 1.75rem;
  font-size: 0.8rem;
  font-weight: 700;
}}
.st-key-tk_hgrid_wrap [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
.st-key-tk_page_hgrid_wrap [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
.st-key-ftp_wrap [data-testid="stSelectbox"] div[data-baseweb="select"] > div {{
  min-height: 1.75rem;
  font-size: 0.68rem;
  padding-top: 0 !important;
  padding-bottom: 0 !important;
  max-width: 100%;
}}
.st-key-tk_hgrid_wrap [data-testid="stSelectbox"] div[data-baseweb="select"] span,
.st-key-tk_page_hgrid_wrap [data-testid="stSelectbox"] div[data-baseweb="select"] span,
.st-key-ftp_wrap [data-testid="stSelectbox"] div[data-baseweb="select"] span {{
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}}
.st-key-tk_hgrid_wrap [data-testid="stNumberInput"] [data-testid="stWidgetLabel"],
.st-key-tk_page_hgrid_wrap [data-testid="stNumberInput"] [data-testid="stWidgetLabel"],
.st-key-ftp_wrap [data-testid="stNumberInput"] [data-testid="stWidgetLabel"] {{
  display: none !important;
}}
.st-key-tk_hgrid_wrap [data-testid="stSelectbox"] [data-testid="stWidgetLabel"],
.st-key-tk_page_hgrid_wrap [data-testid="stSelectbox"] [data-testid="stWidgetLabel"],
.st-key-ftp_wrap [data-testid="stSelectbox"] [data-testid="stWidgetLabel"] {{
  display: none !important;
}}
.st-key-tk_hgrid_wrap [data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"],
.st-key-tk_page_hgrid_wrap [data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"],
.st-key-ftp_wrap [data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] {{
  border-bottom: none !important;
  padding: 0 !important;
  min-height: 0 !important;
  background: transparent !important;
  gap: 0.1rem !important;
}}
.st-key-tk_hgrid_wrap [data-testid="column"] [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:has([data-testid="stNumberInput"]),
.st-key-tk_page_hgrid_wrap [data-testid="column"] [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:has([data-testid="stNumberInput"]),
.st-key-ftp_wrap [data-testid="column"] [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:has([data-testid="stNumberInput"]) {{
  margin-top: 0.05rem !important;
}}
.st-key-timekeeping_table_wrap [data-testid="stVerticalBlock"] {{
  gap: 0 !important;
}}
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"] {{
  gap: 0.2rem !important;
  align-items: center !important;
  border-bottom: 1px solid #e2e8f0;
  padding: 5px 6px !important;
  margin: 0 !important;
  min-height: 52px;
}}
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:first-of-type {{
  background: #f8fafc;
  min-height: 40px;
  padding: 8px 10px !important;
}}
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:not(:first-of-type):not(:has(.timesheet-days-grid-marker)):not(:has(.timesheet-days-grid-marker-wrap)):hover {{
  background: #eef5ff;
}}
.st-key-timekeeping_table_wrap .st-key-tk_row_ [data-testid="stHorizontalBlock"]:hover {{
  background: #eef5ff;
}}
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has([data-testid="stCheckbox"] input:checked) {{
  background: #eaf2ff !important;
}}
.st-key-timekeeping_table_wrap [data-testid="stButton"] button {{
  min-height: 2rem;
  padding: 0.2rem 0.45rem;
  font-size: 0.85rem;
  line-height: 1;
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
.st-key-timekeeping_table_wrap .st-key-tk_row_ [data-testid="stHorizontalBlock"]:has(.timesheet-days-grid-marker) {{
  min-height: 0 !important;
  padding: 0 !important;
  border-bottom: none !important;
  background: transparent !important;
  justify-content: center !important;
}}
.st-key-timekeeping_table_wrap .st-key-tk_row_ [data-testid="stHorizontalBlock"]:has(.timesheet-days-grid-marker):hover {{
  background: transparent !important;
}}
{tk_row_expand}:has(.timekeeping-detail-grid-edit) {tk_detail_row} {{
  display: grid !important;
  grid-template-columns: {tk_detail_grid_edit} !important;
  min-width: 1620px !important;
  width: max-content !important;
  gap: 10px !important;
  align-items: center !important;
}}
{tk_row_expand}:has(.timekeeping-detail-grid-readonly) {tk_detail_row} {{
  display: grid !important;
  grid-template-columns: {tk_detail_grid_readonly} !important;
  min-width: 1580px !important;
  width: max-content !important;
  gap: 10px !important;
  align-items: center !important;
}}
{tk_detail_row} > [data-testid="column"]:has(.timekeeping-detail-hour-stepper) [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-stepper-marker) {{
  display: grid !important;
  grid-template-columns: 32px minmax(52px, 1fr) 32px !important;
  width: 100% !important;
  max-width: 118px !important;
  min-width: 108px !important;
  height: 38px !important;
  margin: 0 !important;
}}
{tk_detail_row} > [data-testid="column"]:has(.timekeeping-detail-hour-stepper) [data-testid="stNumberInput"],
{tk_detail_row} > [data-testid="column"]:has(.timekeeping-detail-hour-stepper) [data-testid="stNumberInput"] > div,
{tk_detail_row} > [data-testid="column"]:has(.timekeeping-detail-hour-stepper) [data-testid="stNumberInput"] input {{
  width: 100% !important;
  min-width: 52px !important;
  max-width: none !important;
}}
.timekeeping-alloc-intro {{
  font-size: 0.84rem;
  color: #475569;
  line-height: 1.35;
  margin: 0 0 0.5rem 0;
  max-width: 100%;
}}
.timekeeping-allocation-card,
.timekeeping-day-allocation-card {{
  width: 100% !important;
  box-sizing: border-box !important;
}}
.timekeeping-day-summary-inline {{
  display: flex !important;
  flex-wrap: nowrap !important;
  align-items: center !important;
  justify-content: space-between !important;
  gap: 0.75rem !important;
  width: 100% !important;
  min-height: 36px !important;
  margin: 0 !important;
  padding: 0.5rem 0.65rem !important;
  border-radius: 7px 7px 0 0 !important;
  line-height: 1.25 !important;
  box-sizing: border-box !important;
}}
.timekeeping-alloc-day-head-left {{
  display: flex !important;
  flex-wrap: wrap !important;
  align-items: center !important;
  gap: 0.35rem 0.65rem !important;
  min-width: 0 !important;
  flex: 1 1 auto !important;
}}
.timekeeping-alloc-day-head-right {{
  display: flex !important;
  align-items: center !important;
  justify-content: flex-end !important;
  flex: 0 1 auto !important;
  min-width: 0 !important;
  text-align: right !important;
}}
.timekeeping-day-summary-inline strong {{
  font-size: 0.9rem !important;
  font-weight: 700 !important;
  color: #0f172a !important;
  text-transform: none !important;
}}
.timekeeping-alloc-day-date {{
  font-size: 0.8rem !important;
  color: #64748b !important;
  text-transform: none !important;
}}
.timekeeping-allocation-status-text,
.timekeeping-alloc-day-split,
.timekeeping-alloc-remaining-text {{
  text-transform: none !important;
}}
.timekeeping-hours-badge,
.timekeeping-alloc-day-total {{
  font-size: 0.72rem !important;
  font-weight: 700 !important;
  color: #1d4ed8 !important;
  background: #eff6ff !important;
  border: 1px solid #bfdbfe !important;
  border-radius: 6px !important;
  padding: 2px 8px !important;
  white-space: nowrap !important;
  text-transform: uppercase !important;
  letter-spacing: 0.02em !important;
}}
.timekeeping-allocation-status-text,
.timekeeping-alloc-day-split {{
  font-size: 0.76rem !important;
  color: #92400e !important;
  font-weight: 600 !important;
  white-space: nowrap !important;
}}
.timekeeping-allocation-header-row {{
  display: grid !important;
  grid-template-columns: {tk_alloc_grid_cols} !important;
  column-gap: 10px !important;
  align-items: end !important;
  width: 100% !important;
  min-width: {tk_alloc_grid_min_w} !important;
  max-width: 100% !important;
  margin: 0 0 4px 0 !important;
  padding: 0 2px !important;
  box-sizing: border-box !important;
}}
.timekeeping-allocation-header-row > div {{
  font-size: 10px !important;
  font-weight: 700 !important;
  color: #667085 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.04em !important;
  line-height: 1.2 !important;
  white-space: nowrap !important;
}}
{tk_alloc_day} [data-testid="stHorizontalBlock"]:has(.timekeeping-allocation-day-actions-bar-marker) {{
  display: flex !important;
  flex-wrap: nowrap !important;
  align-items: center !important;
  justify-content: space-between !important;
  gap: 12px !important;
  width: 100% !important;
  max-width: 100% !important;
  margin: 10px 0 0 !important;
  padding: 10px 0 2px !important;
  border-top: 1px solid #e2e8f0 !important;
  overflow: visible !important;
}}
{tk_alloc_day} [data-testid="stHorizontalBlock"]:has(.timekeeping-allocation-day-actions-bar-marker)
  > [data-testid="column"]:first-child {{
  flex: 0 0 auto !important;
  width: auto !important;
  min-width: 0 !important;
  max-width: none !important;
}}
{tk_alloc_day} [data-testid="stHorizontalBlock"]:has(.timekeeping-allocation-day-actions-bar-marker)
  > [data-testid="column"]:last-child {{
  flex: 1 1 auto !important;
  width: auto !important;
  min-width: 0 !important;
  max-width: none !important;
  display: flex !important;
  justify-content: flex-end !important;
  overflow: visible !important;
}}
.timekeeping-alloc-day-actions-status {{
  display: inline-flex !important;
  align-items: center !important;
  gap: 8px !important;
  flex-wrap: nowrap !important;
  white-space: nowrap !important;
}}
.timekeeping-alloc-day-actions-status-label {{
  font-size: 0.78rem !important;
  font-weight: 700 !important;
  color: #64748b !important;
  text-transform: uppercase !important;
  letter-spacing: 0.04em !important;
}}
.timekeeping-alloc-row-autosave {{
  margin-top: 4px !important;
  min-height: 1.1rem !important;
}}
.timekeeping-alloc-autosave-status {{
  display: inline-block !important;
  font-size: 0.72rem !important;
  font-weight: 600 !important;
  letter-spacing: 0.02em !important;
  line-height: 1.2 !important;
}}
.timekeeping-alloc-autosave-saving {{
  color: #64748b !important;
}}
.timekeeping-alloc-autosave-saved {{
  color: #15803d !important;
}}
.timekeeping-alloc-autosave-unsaved {{
  color: #b45309 !important;
}}
{tk_alloc_day} [data-testid="column"]:has(.timekeeping-allocation-actions-marker) {{
  display: flex !important;
  flex-direction: row !important;
  flex-wrap: nowrap !important;
  align-items: center !important;
  justify-content: flex-end !important;
  gap: 8px !important;
  width: 100% !important;
  min-width: 0 !important;
  overflow: visible !important;
}}
{tk_alloc_day} [data-testid="column"]:has(.timekeeping-allocation-actions-marker)
  > [data-testid="stVerticalBlock"] {{
  display: flex !important;
  flex-direction: row !important;
  flex-wrap: nowrap !important;
  align-items: center !important;
  justify-content: flex-end !important;
  gap: 8px !important;
  width: 100% !important;
  min-width: 0 !important;
  overflow: visible !important;
}}
{tk_alloc_day} [data-testid="column"]:has(.timekeeping-allocation-actions-marker)
  [data-testid="stHorizontalBlock"] {{
  display: flex !important;
  flex-direction: row !important;
  flex-wrap: nowrap !important;
  align-items: center !important;
  justify-content: flex-end !important;
  gap: 8px !important;
  width: auto !important;
  min-width: 0 !important;
  max-width: none !important;
  margin-left: auto !important;
  overflow: visible !important;
}}
{tk_alloc_day} [data-testid="column"]:has(.timekeeping-allocation-actions-marker)
  [data-testid="stHorizontalBlock"] > [data-testid="column"] {{
  width: auto !important;
  min-width: max-content !important;
  flex: 0 0 auto !important;
  overflow: visible !important;
}}
{tk_alloc_day} [data-testid="column"]:has(.timekeeping-allocation-actions-marker)
  [data-testid="stButton"] {{
  width: auto !important;
  min-width: max-content !important;
  margin: 0 !important;
  flex: 0 0 auto !important;
}}
{tk_alloc_day} [data-testid="column"]:has(.timekeeping-allocation-actions-marker)
  [data-testid="stButton"] > button {{
  width: auto !important;
  min-width: max-content !important;
  max-width: none !important;
  min-height: 34px !important;
  height: 34px !important;
  padding: 0 12px !important;
  font-size: 0.78rem !important;
  font-weight: 700 !important;
  white-space: nowrap !important;
}}
{tk_alloc_day}:has(.timekeeping-alloc-day-state-complete) .timekeeping-alloc-remaining-text {{
  color: #15803d !important;
  font-weight: 700 !important;
}}
.timekeeping-alloc-day-unbalanced .timekeeping-allocation-status-text,
.timekeeping-alloc-day-unbalanced .timekeeping-alloc-day-split,
{tk_alloc_day}:has(.timekeeping-alloc-day-unbalanced) .timekeeping-allocation-status-text,
{tk_alloc_day}:has(.timekeeping-alloc-day-unbalanced) .timekeeping-alloc-day-split {{
  color: #b45309 !important;
  font-weight: 700 !important;
}}
.timekeeping-alloc-day-complete {{
  background: #f0fdf4 !important;
  border: 1px solid #bbf7d0 !important;
}}
.timekeeping-alloc-day-complete strong {{
  color: #166534 !important;
}}
.timekeeping-alloc-day-complete .timekeeping-hours-badge,
.timekeeping-alloc-day-complete .timekeeping-alloc-day-total {{
  background: #dcfce7 !important;
  color: #15803d !important;
  border-color: #86efac !important;
}}
.timekeeping-alloc-day-complete .timekeeping-allocation-status-text,
.timekeeping-alloc-day-complete .timekeeping-alloc-day-split {{
  color: #15803d !important;
  font-weight: 700 !important;
}}
.timekeeping-alloc-day-incomplete,
.timekeeping-alloc-day-needs-assignment {{
  background: #fffbeb !important;
  border: 1px solid #fde68a !important;
}}
.timekeeping-alloc-day-incomplete .timekeeping-allocation-status-text,
.timekeeping-alloc-day-incomplete .timekeeping-alloc-day-split,
.timekeeping-alloc-day-needs-assignment .timekeeping-allocation-status-text,
.timekeeping-alloc-day-needs-assignment .timekeeping-alloc-day-split {{
  color: #b45309 !important;
  font-weight: 700 !important;
}}
.timekeeping-alloc-day-overallocated {{
  background: #fef2f2 !important;
  border: 1px solid #fecaca !important;
}}
.timekeeping-alloc-day-overallocated .timekeeping-allocation-status-text,
.timekeeping-alloc-day-overallocated .timekeeping-alloc-day-split,
.timekeeping-alloc-day-overallocated .timekeeping-hours-badge,
.timekeeping-alloc-day-overallocated .timekeeping-alloc-day-total {{
  color: #b91c1c !important;
  font-weight: 700 !important;
}}
.timekeeping-alloc-day-overallocated .timekeeping-hours-badge,
.timekeeping-alloc-day-overallocated .timekeeping-alloc-day-total {{
  background: #fee2e2 !important;
  border-color: #fca5a5 !important;
}}
{tk_list_day_col}:has(.ips-time-week-day-alloc-complete) {{
  background: transparent !important;
  border: none !important;
  border-radius: 0 !important;
  padding: 0 2px !important;
  box-sizing: border-box !important;
  overflow: visible !important;
  box-shadow: none !important;
}}
{tk_list_day_col}:has(.ips-time-week-day-alloc-warn) {{
  background: transparent !important;
  border: none !important;
  border-radius: 0 !important;
  padding: 0 2px !important;
  box-sizing: border-box !important;
  overflow: visible !important;
  box-shadow: none !important;
}}
{tk_list_day_col}:has(.ips-time-week-day-alloc-over) {{
  background: transparent !important;
  border: none !important;
  border-radius: 0 !important;
  padding: 0 2px !important;
  box-sizing: border-box !important;
  overflow: visible !important;
  box-shadow: none !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_hour_spin_"]:has(.timekeeping-list-hour-spin-approved-complete)
  [data-testid="stHorizontalBlock"]:has(.timekeeping-spinner-buttons-marker) {{
  background: #f0fdf4 !important;
  border: 2px solid #22c55e !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_hour_spin_"]:has(.timekeeping-list-hour-spin-approved-complete)
  [data-testid="stNumberInput"] input {{
  background: #f0fdf4 !important;
  color: #166534 !important;
  font-weight: 700 !important;
}}
.timekeeping-list-hour-ro-approved-complete {{
  background: #f0fdf4 !important;
  border: 2px solid #22c55e !important;
  border-radius: 8px !important;
  color: #166534 !important;
  font-weight: 700 !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_hour_spin_"]:has(.timekeeping-list-hour-spin-complete)
  [data-testid="stHorizontalBlock"]:has(.timekeeping-spinner-buttons-marker) {{
  background: #ffffff !important;
  border: 1px solid #22c55e !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_hour_spin_"]:has(.timekeeping-list-hour-spin-complete)
  [data-testid="stNumberInput"] input {{
  background: #ffffff !important;
  color: #166534 !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_hour_spin_"]:has(.timekeeping-list-hour-spin-warn)
  [data-testid="stHorizontalBlock"]:has(.timekeeping-spinner-buttons-marker) {{
  background: #ffffff !important;
  border: 1px solid #fcd34d !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_hour_spin_"]:has(.timekeeping-list-hour-spin-warn)
  [data-testid="stNumberInput"] input {{
  background: #ffffff !important;
  color: #92400e !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_hour_spin_"]:has(.timekeeping-list-hour-spin-over)
  [data-testid="stHorizontalBlock"]:has(.timekeeping-spinner-buttons-marker) {{
  background: #ffffff !important;
  border: 1px solid #fca5a5 !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_hour_spin_"]:has(.timekeeping-list-hour-spin-over)
  [data-testid="stNumberInput"] input {{
  background: #ffffff !important;
  color: #b91c1c !important;
}}
.timekeeping-list-hour-ro-complete {{
  background: #ffffff !important;
  border: 1px solid #22c55e !important;
  border-radius: 8px !important;
  color: #166534 !important;
}}
.timekeeping-list-hour-ro-warn {{
  background: #ffffff !important;
  border: 1px solid #fcd34d !important;
  border-radius: 8px !important;
  color: #92400e !important;
}}
.timekeeping-list-hour-ro-over {{
  background: #ffffff !important;
  border: 1px solid #fca5a5 !important;
  border-radius: 8px !important;
  color: #b91c1c !important;
}}
/* Day-level approval states — list row hour boxes */
.timekeeping-day-status-badge {{
  display: block;
  margin: 0 0 4px 0;
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  text-align: center;
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
{tk_list_day_col}:has(.ips-tk-day-draft-empty) {{
  background: transparent !important;
  box-shadow: none !important;
  border-radius: 0 !important;
}}
{tk_list_day_col}:has(.ips-tk-day-draft-empty) .timekeeping-day-status-badge {{
  color: #94a3b8;
}}
{tk_list_day_col}:has(.ips-tk-day-draft):not(:has(.ips-tk-day-draft-empty)) {{
  background: transparent !important;
  box-shadow: none !important;
  border-radius: 0 !important;
}}
{tk_list_day_col}:has(.ips-tk-day-draft) .timekeeping-day-status-badge {{
  color: #475569;
}}
{tk_list_day_col}:has(.ips-tk-day-pending) {{
  background: #fffbeb !important;
  border: 1px solid #f59e0b !important;
  border-radius: 8px !important;
  box-shadow: none !important;
}}
{tk_list_day_col}:has(.ips-tk-day-pending) .timekeeping-day-status-badge {{
  color: #b45309;
}}
{tk_list_day_col}:has(.ips-tk-day-approved):not(:has(.ips-tk-day-approved-complete)) {{
  background: #f8fafc !important;
  border: 1px dashed #86efac !important;
  border-radius: 8px !important;
  box-shadow: none !important;
}}
{tk_list_day_col}:has(.ips-tk-day-approved):not(:has(.ips-tk-day-approved-complete)) .timekeeping-day-status-badge {{
  color: #15803d;
}}
{tk_list_day_col}:has(.ips-tk-day-approved-complete) {{
  background: #f0fdf4 !important;
  border: 2px solid #22c55e !important;
  border-radius: 8px !important;
  box-shadow: 0 0 0 1px #bbf7d0 !important;
  padding: 2px !important;
  box-sizing: border-box !important;
}}
{tk_list_day_col}:has(.ips-tk-day-approved-complete) .timekeeping-day-date-label {{
  color: #166534 !important;
}}
{tk_list_day_col}:has(.ips-tk-day-approved-complete) .timekeeping-day-status-badge {{
  margin-top: 2px !important;
  overflow: visible !important;
  text-overflow: clip !important;
}}
{tk_list_day_col}:has(.ips-tk-day-rejected) {{
  background: #fef2f2 !important;
  border: 1px solid #ef4444 !important;
  border-radius: 8px !important;
  box-shadow: none !important;
}}
{tk_list_day_col}:has(.ips-tk-day-rejected) .timekeeping-day-status-badge {{
  color: #b91c1c;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_hour_spin_"]:has(.timekeeping-list-hour-spin-draft)
  [data-testid="stHorizontalBlock"]:has(.timekeeping-spinner-buttons-marker),
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_hour_spin_"]:has(.timekeeping-list-hour-spin-pending)
  [data-testid="stHorizontalBlock"]:has(.timekeeping-spinner-buttons-marker),
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_hour_spin_"]:has(.timekeeping-list-hour-spin-approved)
  [data-testid="stHorizontalBlock"]:has(.timekeeping-spinner-buttons-marker),
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_hour_spin_"]:has(.timekeeping-list-hour-spin-rejected)
  [data-testid="stHorizontalBlock"]:has(.timekeeping-spinner-buttons-marker) {{
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}}
.timekeeping-list-hour-ro-draft,
.timekeeping-list-hour-ro-pending,
.timekeeping-list-hour-ro-approved,
.timekeeping-list-hour-ro-rejected {{
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}}
.timekeeping-list-hour-ro-draft {{
  color: #0f172a !important;
}}
.timekeeping-list-hour-ro-pending {{
  color: #92400e !important;
  font-weight: 700 !important;
}}
.timekeeping-list-hour-ro-approved {{
  color: #166534 !important;
  font-weight: 700 !important;
}}
.timekeeping-list-hour-ro-rejected {{
  color: #991b1b !important;
  font-weight: 700 !important;
}}
/* Allocation day cards — approval state borders */
[class*="st-key-tk_alloc_day_"]:has(.timekeeping-alloc-approval-draft) {{
  border-color: #cbd5e1 !important;
}}
[class*="st-key-tk_alloc_day_"]:has(.timekeeping-alloc-approval-pending) {{
  border-color: #f59e0b !important;
  background: #fffbeb !important;
}}
[class*="st-key-tk_alloc_day_"]:has(.timekeeping-alloc-approval-approved) {{
  border-color: #86efac !important;
  background: #f8fafc !important;
}}
[class*="st-key-tk_alloc_day_"]:has(.timekeeping-alloc-approval-approved-complete) {{
  border: 2px solid #22c55e !important;
  background: #f0fdf4 !important;
  box-shadow: 0 0 0 1px #bbf7d0 !important;
}}
[class*="st-key-tk_alloc_day_"]:has(.timekeeping-alloc-approval-rejected) {{
  border-color: #ef4444 !important;
  background: #fef2f2 !important;
}}
.timekeeping-alloc-approval-pending .timekeeping-alloc-day-actions-status .ips-timekeeping-status-pill {{
  box-shadow: 0 0 0 1px #f59e0b;
}}
.timekeeping-alloc-approval-approved .timekeeping-alloc-day-actions-status .ips-timekeeping-status-pill {{
  box-shadow: 0 0 0 1px #86efac;
}}
.timekeeping-alloc-approval-approved-complete .timekeeping-alloc-day-actions-status .ips-timekeeping-status-pill,
.timekeeping-alloc-day-actions-status-approved-complete .ips-timekeeping-status-pill {{
  background: #22c55e !important;
  color: #ffffff !important;
  box-shadow: 0 0 0 1px #16a34a !important;
  text-transform: uppercase !important;
  letter-spacing: 0.04em !important;
}}
.timekeeping-alloc-approval-rejected .timekeeping-alloc-day-actions-status .ips-timekeeping-status-pill {{
  box-shadow: 0 0 0 1px #ef4444;
}}
{tk_expand}:has(.timekeeping-allocation-panel-marker) {{
  max-width: 100% !important;
  width: 100% !important;
  height: auto !important;
  min-height: 0 !important;
  max-height: none !important;
  overflow-x: auto !important;
  overflow-y: visible !important;
  -webkit-overflow-scrolling: touch;
}}
{tk_expand}:has(.timekeeping-allocation-panel-marker) [class*="st-key-tk_alloc_panel_"],
{tk_expand}:has(.timekeeping-allocation-panel-marker) [class*="st-key-tk_alloc_day_"],
{tk_expand}:has(.timekeeping-allocation-panel-marker) [class*="st-key-tk_alloc_line_"],
{tk_expand}:has(.timekeeping-allocation-panel-marker) {tk_alloc_ctrl_row},
{tk_expand}:has(.timekeeping-allocation-panel-marker) [data-testid="stHorizontalBlock"],
{tk_expand}:has(.timekeeping-allocation-panel-marker) [data-testid="stVerticalBlock"],
{tk_expand}:has(.timekeeping-allocation-panel-marker) [data-testid="stElementContainer"] {{
  height: auto !important;
  min-height: 0 !important;
  max-height: none !important;
  overflow: visible !important;
}}
{tk_alloc_panel} {{
  width: 100% !important;
  max-width: 100% !important;
  min-width: 0 !important;
  display: block !important;
}}
{tk_alloc_panel} > [data-testid="stVerticalBlock"] {{
  display: flex !important;
  flex-direction: column !important;
  align-items: stretch !important;
  width: 100% !important;
  gap: 0.75rem !important;
  height: auto !important;
  max-height: none !important;
  overflow: visible !important;
}}
{tk_expand}:has(.timekeeping-allocation-panel-marker) [class*="st-key-tk_alloc_day_"],
{tk_alloc_panel} [class*="st-key-tk_alloc_day_"] {{
  width: 100% !important;
  max-width: 100% !important;
  min-width: 0 !important;
  display: block !important;
  visibility: visible !important;
}}
{tk_expand}:has(.timekeeping-allocation-panel-marker) [data-testid="stVerticalBlock"] {{
  gap: 0.35rem !important;
}}
{tk_expand}:has(.timekeeping-allocation-panel-marker) [data-testid="stElementContainer"] {{
  margin-bottom: 0.2rem !important;
  padding-top: 0 !important;
  padding-bottom: 0 !important;
}}
{tk_expand}:has(.timekeeping-allocation-panel-marker) [data-testid="stCaptionContainer"] {{
  margin-top: 0 !important;
  margin-bottom: 0.15rem !important;
  padding-top: 0 !important;
  padding-bottom: 0 !important;
}}
{tk_expand}:has(.timekeeping-allocation-panel-marker) [data-testid="stCaptionContainer"] p {{
  font-size: 0.76rem !important;
  line-height: 1.2 !important;
  margin: 0 !important;
}}
{tk_alloc_day} {{
  max-width: 100% !important;
  width: 100% !important;
  margin: 0 0 8px 0 !important;
  padding: 0 !important;
  background: transparent !important;
  border: none !important;
  border-radius: 0 !important;
  box-sizing: border-box !important;
  overflow: visible !important;
}}
{tk_alloc_day} [data-testid="stVerticalBlockBorderWrapper"],
{tk_alloc_day} > [data-testid="stVerticalBlock"] {{
  width: 100% !important;
  max-width: 100% !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: 8px !important;
  background: #ffffff !important;
  padding: 0 !important;
  box-sizing: border-box !important;
  overflow: visible !important;
}}
{tk_alloc_day} [data-testid="stHorizontalBlock"]:has(.timekeeping-alloc-day-grid-marker) {{
  padding: 10px 12px 12px !important;
  background: #ffffff !important;
  border-radius: 0 0 7px 7px !important;
}}
{tk_alloc_day}:has(.timekeeping-alloc-day-state-complete):not(:has(.timekeeping-alloc-approval-approved-complete)) [data-testid="stVerticalBlockBorderWrapper"],
{tk_alloc_day}:has(.timekeeping-alloc-day-state-complete):not(:has(.timekeeping-alloc-approval-approved-complete)) > [data-testid="stVerticalBlock"] {{
  border-color: #86efac !important;
}}
{tk_alloc_day}:has(.timekeeping-alloc-approval-approved-complete) [data-testid="stVerticalBlockBorderWrapper"],
{tk_alloc_day}:has(.timekeeping-alloc-approval-approved-complete) > [data-testid="stVerticalBlock"] {{
  border-color: #22c55e !important;
}}
{tk_alloc_day}:has(.timekeeping-alloc-day-state-incomplete) [data-testid="stVerticalBlockBorderWrapper"],
{tk_alloc_day}:has(.timekeeping-alloc-day-state-needs_assignment) [data-testid="stVerticalBlockBorderWrapper"],
{tk_alloc_day}:has(.timekeeping-alloc-day-state-incomplete) > [data-testid="stVerticalBlock"],
{tk_alloc_day}:has(.timekeeping-alloc-day-state-needs_assignment) > [data-testid="stVerticalBlock"] {{
  border-color: #fcd34d !important;
}}
{tk_alloc_day}:has(.timekeeping-alloc-day-state-overallocated) [data-testid="stVerticalBlockBorderWrapper"],
{tk_alloc_day}:has(.timekeeping-alloc-day-state-overallocated) > [data-testid="stVerticalBlock"] {{
  border-color: #fca5a5 !important;
}}
{tk_expand}:has(.timekeeping-allocation-panel-marker)
  [data-testid="stHorizontalBlock"]:has(.timekeeping-allocation-actions-footer-marker) {{
  display: flex !important;
  flex-wrap: wrap !important;
  width: 100% !important;
  max-width: 100% !important;
  justify-content: flex-start !important;
  align-items: center !important;
  gap: 10px !important;
  margin-top: 10px !important;
  padding-top: 8px !important;
  border-top: 1px solid #e2e8f0 !important;
  position: relative !important;
  z-index: 2 !important;
  clear: both !important;
}}
{tk_expand}:has(.timekeeping-allocation-panel-marker)
  [data-testid="stHorizontalBlock"]:has(.timekeeping-allocation-actions-footer-marker)
  > [data-testid="column"] {{
  flex: 0 0 auto !important;
  width: auto !important;
  min-width: 0 !important;
  max-width: none !important;
}}
{tk_alloc_day}:has(.timekeeping-alloc-day-state-complete):not(:has(.timekeeping-alloc-approval-approved-complete)) .timekeeping-day-summary-inline {{
  background: #fffbeb !important;
  border: none !important;
  border-bottom: 1px solid #fde68a !important;
}}
{tk_alloc_day}:has(.timekeeping-alloc-approval-approved-complete) .timekeeping-day-summary-inline {{
  background: #dcfce7 !important;
  border: none !important;
  border-bottom: 1px solid #22c55e !important;
}}
{tk_alloc_day}:has(.timekeeping-alloc-approval-approved-complete) .timekeeping-allocation-status-text,
{tk_alloc_day}:has(.timekeeping-alloc-approval-approved-complete) .timekeeping-alloc-day-split,
{tk_alloc_day}:has(.timekeeping-alloc-approval-approved-complete) .timekeeping-alloc-remaining-text {{
  color: #166534 !important;
  font-weight: 700 !important;
}}
{tk_alloc_day}:has(.timekeeping-alloc-day-state-incomplete) .timekeeping-day-summary-inline,
{tk_alloc_day}:has(.timekeeping-alloc-day-state-needs_assignment) .timekeeping-day-summary-inline {{
  background: #fffbeb !important;
  border: none !important;
  border-bottom: 1px solid #fde68a !important;
}}
{tk_alloc_day}:has(.timekeeping-alloc-day-state-incomplete) .timekeeping-allocation-status-text,
{tk_alloc_day}:has(.timekeeping-alloc-day-state-needs_assignment) .timekeeping-allocation-status-text,
{tk_alloc_day}:has(.timekeeping-alloc-day-state-incomplete) .timekeeping-alloc-day-split {{
  color: #92400e !important;
}}
{tk_alloc_day}:has(.timekeeping-alloc-day-state-overallocated) .timekeeping-day-summary-inline {{
  background: #fef2f2 !important;
  border: 1px solid #fecaca !important;
}}
{tk_alloc_day} [data-testid="stElementContainer"]:has(.timekeeping-day-summary-inline-marker),
{tk_alloc_day} [data-testid="stElementContainer"]:has(.timekeeping-allocation-card) {{
  width: 100% !important;
  max-width: 100% !important;
  margin: 0 !important;
  padding: 0 !important;
}}
{tk_alloc_day} [data-testid="stCaptionContainer"] {{
  margin: 0.15rem 0 0 !important;
  padding: 0 !important;
}}
{tk_alloc_day} > [data-testid="stVerticalBlock"] {{
  display: flex !important;
  flex-direction: column !important;
  align-items: stretch !important;
  width: 100% !important;
  max-width: 100% !important;
  gap: 0.5rem !important;
  height: auto !important;
  max-height: none !important;
  overflow: visible !important;
}}
{tk_alloc_day} [data-testid="stElementContainer"]:has(.timekeeping-allocation-header-row) {{
  width: 100% !important;
  max-width: 100% !important;
  overflow-x: auto !important;
}}
{tk_alloc_line_host} {{
  width: 100% !important;
  max-width: 100% !important;
  min-width: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  display: block !important;
  overflow: visible !important;
}}
{tk_alloc_line_key} {{
  max-width: 100% !important;
  width: 100% !important;
  min-width: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  background: transparent !important;
  border: none !important;
  border-radius: 0 !important;
  box-sizing: border-box !important;
  overflow: visible !important;
  height: auto !important;
  max-height: none !important;
}}
{tk_alloc_line_host} + {tk_alloc_line_host} {{
  margin-top: 2px !important;
  padding-top: 2px !important;
  border-top: 1px solid #f1f5f9 !important;
}}
{tk_alloc_ctrl_row}
  [data-testid="column"] [data-testid="stVerticalBlock"] {{
  gap: 0 !important;
}}
.timekeeping-alloc-field-label {{
  display: block !important;
  position: static !important;
  z-index: auto !important;
  font-size: 10px !important;
  font-weight: 700 !important;
  color: #667085 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.04em !important;
  margin: 0 !important;
  padding: 0 !important;
  line-height: 1.2 !important;
  white-space: nowrap !important;
  overflow: visible !important;
}}
.timekeeping-alloc-col-head,
.timekeeping-allocation-header-cell {{
  margin: 0 !important;
  font-size: 10px !important;
  line-height: 1.1 !important;
  padding: 0 !important;
  font-weight: 700 !important;
  letter-spacing: 0.04em !important;
  color: #667085 !important;
  text-transform: uppercase !important;
  white-space: nowrap !important;
  overflow: visible !important;
}}
{tk_alloc_ctrl_row},
{tk_alloc_ctrl_row_alt} {{
  display: flex !important;
  flex-direction: row !important;
  flex-wrap: nowrap !important;
  align-items: flex-start !important;
  justify-content: flex-start !important;
  column-gap: 10px !important;
  row-gap: 0 !important;
  width: 100% !important;
  min-width: 0 !important;
  max-width: 100% !important;
  margin: 0 !important;
  box-sizing: border-box !important;
  min-height: 58px !important;
  height: auto !important;
  max-height: none !important;
  padding: 0 !important;
  overflow: visible !important;
}}
{tk_alloc_ctrl_row} [data-testid="stWidgetLabel"],
{tk_alloc_ctrl_row_alt} [data-testid="stWidgetLabel"],
{tk_alloc_ctrl_row} [data-testid="stWidgetLabel"] p,
{tk_alloc_ctrl_row_alt} [data-testid="stWidgetLabel"] p {{
  font-size: 10px !important;
  font-weight: 700 !important;
  color: #667085 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.04em !important;
  line-height: 1.2 !important;
  margin: 0 0 4px 0 !important;
  padding: 0 !important;
  min-height: 0 !important;
}}
{tk_alloc_ctrl_row} > [data-testid="column"] [data-testid="stVerticalBlock"],
{tk_alloc_ctrl_row_alt} > [data-testid="column"] [data-testid="stVerticalBlock"] {{
  gap: 0 !important;
}}
{tk_alloc_ctrl_row} [data-testid="stNumberInput"] > div,
{tk_alloc_ctrl_row} [data-testid="stTextInput"] > div,
{tk_alloc_ctrl_row_alt} [data-testid="stNumberInput"] > div,
{tk_alloc_ctrl_row_alt} [data-testid="stTextInput"] > div {{
  min-height: 32px !important;
}}
{tk_alloc_ctrl_row} [data-testid="stNumberInput"] input,
{tk_alloc_ctrl_row} [data-testid="stTextInput"] input,
{tk_alloc_ctrl_row_alt} [data-testid="stNumberInput"] input,
{tk_alloc_ctrl_row_alt} [data-testid="stTextInput"] input {{
  min-height: 32px !important;
  height: 32px !important;
  font-size: 0.875rem !important;
  border-radius: 6px !important;
}}
.timekeeping-alloc-field-label-static {{
  margin: 0 0 4px 0 !important;
  text-transform: uppercase !important;
}}
{tk_expand}:has(.timekeeping-allocation-panel-marker) .timekeeping-allocation-header-row {{
  display: none !important;
  height: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  overflow: hidden !important;
}}
{tk_alloc_ctrl_row}
  > [data-testid="column"],
{tk_alloc_ctrl_row_alt}
  > [data-testid="column"] {{
  display: block !important;
  min-width: 0 !important;
  max-width: none !important;
  flex: 0 0 auto !important;
  padding: 0 !important;
  margin: 0 !important;
  overflow: visible !important;
  align-self: flex-start !important;
  height: auto !important;
  max-height: none !important;
}}
{tk_alloc_ctrl_row} > [data-testid="column"] [data-testid="stVerticalBlock"],
{tk_alloc_ctrl_row_alt} > [data-testid="column"] [data-testid="stVerticalBlock"] {{
  justify-content: flex-start !important;
}}
{tk_expand}:has(.timekeeping-allocation-panel-marker)
  {tk_alloc_line_key} [data-testid="column"]:has(.timekeeping-allocation-assignment-marker) {{
  min-width: {tk_alloc_assign_col_min_w} !important;
  width: auto !important;
  max-width: none !important;
  overflow: visible !important;
}}
{tk_alloc_ctrl_row}
  > [data-testid="column"]:nth-child(1),
{tk_alloc_ctrl_row_alt}
  > [data-testid="column"]:nth-child(1) {{
  flex: 1 1 240px !important;
  min-width: 200px !important;
  width: auto !important;
  max-width: none !important;
  overflow: visible !important;
}}
{tk_alloc_ctrl_row}
  > [data-testid="column"]:nth-child(2),
{tk_alloc_ctrl_row_alt}
  > [data-testid="column"]:nth-child(2) {{
  flex: 0 0 {tk_alloc_type_col_w} !important;
  min-width: {tk_alloc_type_col_w} !important;
  width: {tk_alloc_type_col_w} !important;
  max-width: {tk_alloc_type_col_w} !important;
  overflow: visible !important;
}}
{tk_expand}:has(.timekeeping-allocation-panel-marker)
  {tk_alloc_line_key} [data-testid="column"]:has(.timekeeping-allocation-hours-marker) {{
  min-width: 100px !important;
  width: 108px !important;
  max-width: 108px !important;
  overflow: visible !important;
}}
{tk_alloc_ctrl_row}
  > [data-testid="column"]:nth-child(3),
{tk_alloc_ctrl_row_alt}
  > [data-testid="column"]:nth-child(3) {{
  flex: 0 0 108px !important;
  min-width: 100px !important;
  width: 108px !important;
  max-width: 108px !important;
}}
{tk_alloc_ctrl_row}
  > [data-testid="column"]:nth-child(4),
{tk_alloc_ctrl_row_alt}
  > [data-testid="column"]:nth-child(4) {{
  flex: 1 1 180px !important;
  min-width: 140px !important;
  width: auto !important;
  max-width: none !important;
}}
{tk_alloc_ctrl_row} [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
{tk_alloc_ctrl_row_alt} [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
{tk_alloc_ctrl_row} [data-testid="stNumberInput"] > div,
{tk_alloc_ctrl_row} [data-testid="stNumberInput"] input,
{tk_alloc_ctrl_row} [data-testid="stTextInput"] > div,
{tk_alloc_ctrl_row} [data-testid="stTextInput"] input,
{tk_alloc_ctrl_row_alt} [data-testid="stNumberInput"] > div,
{tk_alloc_ctrl_row_alt} [data-testid="stNumberInput"] input,
{tk_alloc_ctrl_row_alt} [data-testid="stTextInput"] > div,
{tk_alloc_ctrl_row_alt} [data-testid="stTextInput"] input {{
  background: #f8fafc !important;
}}
{tk_alloc_ctrl_row} [data-testid="stSelectbox"] div[data-baseweb="select"] > div {{
  background: #f8fafc !important;
  border-color: #d8dee8 !important;
}}
{tk_alloc_type_col} {{
  min-width: {tk_alloc_type_col_w} !important;
  max-width: {tk_alloc_type_col_w} !important;
  overflow: visible !important;
}}
{tk_alloc_type_col} [data-testid="stVerticalBlock"],
{tk_alloc_type_col} [data-testid="stElementContainer"] {{
  min-width: {tk_alloc_type_col_w} !important;
  max-width: {tk_alloc_type_col_w} !important;
  overflow: visible !important;
}}
{tk_alloc_type_col} [data-testid="stSelectbox"],
{tk_alloc_type_col} [data-testid="stSelectbox"] > div {{
  width: {tk_alloc_type_col_w} !important;
  min-width: {tk_alloc_type_col_w} !important;
  max-width: {tk_alloc_type_col_w} !important;
  flex: 0 0 {tk_alloc_type_col_w} !important;
  overflow: visible !important;
}}
{tk_alloc_type_col} [data-testid="stSelectbox"] div[data-baseweb="select"],
{tk_alloc_type_col} [data-testid="stSelectbox"] div[data-baseweb="select"] > div {{
  width: {tk_alloc_type_col_w} !important;
  min-width: {tk_alloc_type_col_w} !important;
  max-width: {tk_alloc_type_col_w} !important;
  min-height: 32px !important;
  height: 32px !important;
  padding-left: 12px !important;
  padding-right: 32px !important;
  box-sizing: border-box !important;
  overflow: visible !important;
}}
{tk_alloc_type_col} [data-testid="stSelectbox"] div[data-baseweb="select"] [data-baseweb="select-value"],
{tk_alloc_type_col} [data-testid="stSelectbox"] div[data-baseweb="select"] [data-baseweb="select-value"] > div,
{tk_alloc_type_widget} [data-testid="stSelectbox"] div[data-baseweb="select"] [data-baseweb="select-value"],
{tk_alloc_type_widget} [data-testid="stSelectbox"] div[data-baseweb="select"] [data-baseweb="select-value"] > div {{
  flex: 1 1 auto !important;
  min-width: 2.75rem !important;
  overflow: visible !important;
  max-width: calc(100% - 1.75rem) !important;
}}
{tk_alloc_type_col} [data-testid="stSelectbox"] div[data-baseweb="select"] span,
{tk_alloc_type_col} [data-testid="stSelectbox"] div[data-baseweb="select"] > div > div,
{tk_alloc_type_widget} [data-testid="stSelectbox"] div[data-baseweb="select"] span,
{tk_alloc_type_widget} [data-testid="stSelectbox"] div[data-baseweb="select"] > div > div {{
  display: inline-block !important;
  width: auto !important;
  max-width: 100% !important;
  white-space: nowrap !important;
  writing-mode: horizontal-tb !important;
  text-orientation: mixed !important;
  word-break: keep-all !important;
  overflow: visible !important;
  text-overflow: clip !important;
  font-size: 0.875rem !important;
  font-weight: 700 !important;
  line-height: 1.25 !important;
  letter-spacing: 0 !important;
}}
{tk_alloc_type_widget} [data-testid="stSelectbox"],
{tk_alloc_type_widget} [data-testid="stSelectbox"] > div,
{tk_alloc_type_widget} [data-testid="stSelectbox"] div[data-baseweb="select"],
{tk_alloc_type_widget} [data-testid="stSelectbox"] div[data-baseweb="select"] > div {{
  width: {tk_alloc_type_col_w} !important;
  min-width: {tk_alloc_type_col_w} !important;
  max-width: {tk_alloc_type_col_w} !important;
  overflow: visible !important;
}}
body:has(.timekeeping-allocation-panel-marker) div[data-baseweb="popover"] {{
  min-width: min(460px, 92vw) !important;
}}
body:has(.timekeeping-allocation-panel-marker) div[data-baseweb="popover"] ul {{
  min-width: {tk_alloc_type_col_w} !important;
}}
body:has(.timekeeping-allocation-panel-marker) div[data-baseweb="popover"] li,
body:has(.timekeeping-allocation-panel-marker) div[data-baseweb="popover"] li span,
body:has(.timekeeping-allocation-panel-marker) div[data-baseweb="popover"] li div {{
  white-space: nowrap !important;
  writing-mode: horizontal-tb !important;
  word-break: keep-all !important;
  overflow: visible !important;
  font-size: 0.875rem !important;
  font-weight: 600 !important;
  line-height: 1.25 !important;
}}
.timekeeping-alloc-type-cell,
.timekeeping-hour-type-cell {{
  min-width: {tk_alloc_type_col_w} !important;
  max-width: {tk_alloc_type_col_w} !important;
  text-align: center !important;
  white-space: nowrap !important;
  writing-mode: horizontal-tb !important;
}}
.timekeeping-alloc-type-cell,
.timekeeping-alloc-remaining-cell {{
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  width: 100% !important;
  min-height: 32px !important;
  font-size: 0.8rem !important;
  font-weight: 700 !important;
  color: #0f172a !important;
}}
.timekeeping-alloc-remaining-cell {{
  background: #f8fafc !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: 6px !important;
  color: #475569 !important;
  font-weight: 600 !important;
}}
.timekeeping-alloc-day-unbalanced .timekeeping-alloc-remaining-cell,
{tk_alloc_day}:has(.timekeeping-alloc-day-unbalanced) .timekeeping-alloc-remaining-cell {{
  color: #b45309 !important;
  border-color: #fcd34d !important;
  background: #fffbeb !important;
}}
{tk_expand}:has(.timekeeping-allocation-panel-marker)
  {tk_alloc_line_key} [data-testid="column"]:has(.timekeeping-allocation-assignment-marker) [data-testid="stVerticalBlock"],
{tk_expand}:has(.timekeeping-allocation-panel-marker)
  {tk_alloc_line_key} [data-testid="column"]:has(.timekeeping-allocation-assignment-marker) [data-testid="stElementContainer"] {{
  width: 100% !important;
  min-width: {tk_alloc_assign_col_min_w} !important;
  max-width: 100% !important;
}}
{tk_expand}:has(.timekeeping-allocation-panel-marker)
  {tk_alloc_line_key} [data-testid="column"]:has(.timekeeping-allocation-assignment-marker) [data-testid="stSelectbox"],
{tk_expand}:has(.timekeeping-allocation-panel-marker)
  {tk_alloc_line_key} [data-testid="column"]:has(.timekeeping-allocation-assignment-marker) [data-testid="stSelectbox"] > div {{
  width: 100% !important;
  min-width: {tk_alloc_assign_col_min_w} !important;
  max-width: 100% !important;
  flex: 1 1 auto !important;
}}
{tk_expand}:has(.timekeeping-allocation-panel-marker)
  {tk_alloc_line_key} [data-testid="column"]:has(.timekeeping-allocation-assignment-marker) [data-testid="stSelectbox"] div[data-baseweb="select"],
{tk_expand}:has(.timekeeping-allocation-panel-marker)
  {tk_alloc_line_key} [data-testid="column"]:has(.timekeeping-allocation-assignment-marker) [data-testid="stSelectbox"] div[data-baseweb="select"] > div {{
  width: 100% !important;
  min-width: {tk_alloc_assign_col_min_w} !important;
  max-width: 100% !important;
  min-height: 32px !important;
  height: 32px !important;
  box-sizing: border-box !important;
}}
{tk_expand}:has(.timekeeping-allocation-panel-marker)
  {tk_alloc_line_key} [data-testid="column"]:has(.timekeeping-allocation-assignment-marker) [data-testid="stSelectbox"] div[data-baseweb="select"] [data-baseweb="select-value"],
{tk_expand}:has(.timekeeping-allocation-panel-marker)
  {tk_alloc_line_key} [data-testid="column"]:has(.timekeeping-allocation-assignment-marker) [data-testid="stSelectbox"] div[data-baseweb="select"] span {{
  overflow: visible !important;
  text-overflow: clip !important;
  white-space: nowrap !important;
  max-width: 100% !important;
}}
{tk_expand}:has(.timekeeping-allocation-panel-marker)
  {tk_alloc_line_key} [data-testid="column"]:has(.timekeeping-allocation-hours-marker) [data-testid="stNumberInput"],
{tk_expand}:has(.timekeeping-allocation-panel-marker)
  {tk_alloc_line_key} [data-testid="column"]:has(.timekeeping-allocation-hours-marker) [data-testid="stNumberInput"] > div {{
  width: 100% !important;
  min-width: 0 !important;
  max-width: 108px !important;
  border: 1px solid #d8dee8 !important;
  border-radius: 6px !important;
  background: #f8fafc !important;
  min-height: 32px !important;
  height: 32px !important;
}}
{tk_expand}:has(.timekeeping-allocation-panel-marker)
  {tk_alloc_line_key} [data-testid="column"]:has(.timekeeping-allocation-hours-marker) [data-testid="stNumberInput"] input {{
  width: 100% !important;
  min-width: 0 !important;
  text-align: center !important;
  font-size: 13px !important;
  font-weight: 700 !important;
  min-height: 30px !important;
  height: 30px !important;
  padding-top: 2px !important;
  padding-bottom: 2px !important;
}}
{tk_expand}:has(.timekeeping-allocation-panel-marker)
  {tk_alloc_line_key} [data-testid="column"]:nth-child(4) [data-testid="stTextInput"],
{tk_expand}:has(.timekeeping-allocation-panel-marker)
  {tk_alloc_line_key} [data-testid="column"]:has(.timekeeping-allocation-assignment-marker) ~ [data-testid="column"]
  [data-testid="stTextInput"],
{tk_expand}:has(.timekeeping-allocation-panel-marker)
  {tk_alloc_line_key} [data-testid="stTextInput"] {{
  width: 100% !important;
  min-width: 0 !important;
  max-width: 100% !important;
  margin-top: 0 !important;
  margin-bottom: 0 !important;
}}
{tk_expand}:has(.timekeeping-allocation-panel-marker)
  {tk_alloc_line_key} [data-testid="stTextInput"] > div,
{tk_expand}:has(.timekeeping-allocation-panel-marker)
  {tk_alloc_line_key} [data-testid="stTextInput"] input {{
  width: 100% !important;
  min-width: 0 !important;
  max-width: 100% !important;
  min-height: 30px !important;
  height: 30px !important;
  font-size: 0.8rem !important;
  padding-top: 4px !important;
  padding-bottom: 4px !important;
  box-sizing: border-box !important;
}}
{tk_expand}:has(.timekeeping-allocation-panel-marker)
  {tk_alloc_line_key} [data-testid="column"]:has(.timekeeping-allocation-hours-marker) [data-testid="stNumberInputStepUp"],
{tk_expand}:has(.timekeeping-allocation-panel-marker)
  {tk_alloc_line_key} [data-testid="column"]:has(.timekeeping-allocation-hours-marker) [data-testid="stNumberInputStepDown"] {{
  display: none !important;
}}
.timekeeping-alloc-status-cell {{
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  width: 100% !important;
  min-height: 32px !important;
}}
.timekeeping-alloc-status-cell .ips-timekeeping-status-pill {{
  margin: 0 auto !important;
  font-size: 0.68rem !important;
  padding: 2px 8px !important;
  line-height: 1.1 !important;
}}
.timekeeping-alloc-status-plain {{
  font-size: 0.82rem !important;
  font-weight: 600 !important;
  color: #334155 !important;
  line-height: 1.2 !important;
  white-space: nowrap !important;
}}
.timekeeping-alloc-hours-readonly {{
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  width: 100% !important;
  min-height: 32px !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: 6px !important;
  background: #f8fafc !important;
  font-size: 13px !important;
  font-weight: 700 !important;
  color: #0f172a !important;
}}
.timekeeping-alloc-cell {{
  font-size: 0.8rem !important;
  color: #0f172a !important;
  line-height: 1.2 !important;
  min-height: 32px !important;
  display: flex !important;
  align-items: center !important;
}}
{tk_expand}:has(.timekeeping-allocation-panel-marker)
  {tk_alloc_line_key} [data-testid="stButton"] > button {{
  min-height: 28px !important;
  height: 28px !important;
  font-size: 0.74rem !important;
  padding: 0 10px !important;
  white-space: nowrap !important;
  word-break: keep-all !important;
  overflow: visible !important;
  width: auto !important;
  min-width: max-content !important;
}}
{tk_expand}:has(.timekeeping-allocation-panel-marker)
  [data-testid="column"]:has(.timekeeping-allocation-actions-marker) {{
  min-width: {tk_alloc_actions_col_min_w} !important;
  width: auto !important;
  max-width: none !important;
  overflow: visible !important;
}}
{tk_expand}:has(.timekeeping-allocation-panel-marker)
  [data-testid="column"]:has(.timekeeping-allocation-actions-marker)
  > [data-testid="stVerticalBlock"] {{
  display: flex !important;
  flex-direction: row !important;
  flex-wrap: nowrap !important;
  justify-content: flex-start !important;
  align-items: center !important;
  gap: 8px !important;
  width: 100% !important;
  min-width: 0 !important;
  overflow: visible !important;
}}
{tk_expand}:has(.timekeeping-allocation-panel-marker)
  [data-testid="column"]:has(.timekeeping-allocation-actions-marker)
  [data-testid="stHorizontalBlock"] {{
  flex-wrap: nowrap !important;
  width: auto !important;
  min-width: 0 !important;
  gap: 8px !important;
}}
{tk_expand}:has(.timekeeping-allocation-panel-marker)
  [data-testid="column"]:has(.timekeeping-allocation-actions-marker)
  [data-testid="stHorizontalBlock"] > [data-testid="column"] {{
  width: auto !important;
  min-width: max-content !important;
  flex: 0 0 auto !important;
  overflow: visible !important;
}}
{tk_expand}:has(.timekeeping-allocation-panel-marker)
  [data-testid="column"]:has(.timekeeping-allocation-actions-marker)
  > [data-testid="stVerticalBlock"] > div {{
  width: auto !important;
  flex: 0 0 auto !important;
  min-width: max-content !important;
}}
{tk_expand}:has(.timekeeping-allocation-panel-marker)
  [data-testid="column"]:has(.timekeeping-allocation-actions-marker)
  [data-testid="stButton"] {{
  width: auto !important;
  min-width: max-content !important;
  margin: 0 !important;
  flex: 0 0 auto !important;
}}
{tk_expand}:has(.timekeeping-allocation-panel-marker)
  [data-testid="column"]:has(.timekeeping-allocation-actions-marker)
  [data-testid="stButton"] > button {{
  width: auto !important;
  min-width: max-content !important;
  max-width: none !important;
}}
{tk_expand}:has(.timekeeping-allocation-panel-marker)
  [data-testid="column"]:has(.timekeeping-allocation-actions-marker)
  [data-testid="stButton"] > button p,
{tk_expand}:has(.timekeeping-allocation-panel-marker)
  [data-testid="column"]:has(.timekeeping-allocation-actions-marker)
  [data-testid="stButton"] > button span,
{tk_expand}:has(.timekeeping-allocation-panel-marker)
  [data-testid="column"]:has(.timekeeping-allocation-actions-marker)
  [data-testid="stButton"] > button div {{
  white-space: nowrap !important;
  writing-mode: horizontal-tb !important;
  word-break: keep-all !important;
  overflow: visible !important;
  text-overflow: clip !important;
  display: inline !important;
  line-height: 1.2 !important;
}}
{tk_expand}:has(.timekeeping-allocation-panel-marker)
  {tk_alloc_line_key} [data-testid="stButton"] > button,
{tk_expand}:has(.timekeeping-allocation-panel-marker)
  {tk_alloc_line_key} [data-testid="stButton"] > button p,
{tk_expand}:has(.timekeeping-allocation-panel-marker)
  {tk_alloc_line_key} [data-testid="stButton"] > button span,
{tk_expand}:has(.timekeeping-allocation-panel-marker)
  {tk_alloc_line_key} [data-testid="stButton"] > button div,
{tk_expand}:has(.timekeeping-allocation-panel-marker)
  .timekeeping-alloc-col-head,
{tk_expand}:has(.timekeeping-allocation-panel-marker)
  .timekeeping-alloc-field-label,
{tk_expand}:has(.timekeeping-allocation-panel-marker)
  [data-testid="stSelectbox"] div[data-baseweb="select"] span {{
  writing-mode: horizontal-tb !important;
  text-orientation: mixed !important;
  white-space: nowrap !important;
  word-break: normal !important;
  overflow-wrap: normal !important;
  hyphens: none !important;
}}
{tk_expand}:has(.timekeeping-allocation-panel-marker)
  [data-testid="column"]:has(.timekeeping-allocation-actions-marker)
  [data-testid="stHorizontalBlock"] {{
  display: flex !important;
  flex-direction: row !important;
  flex-wrap: nowrap !important;
  align-items: center !important;
  justify-content: flex-start !important;
  width: max-content !important;
  min-width: 280px !important;
  max-width: none !important;
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


def inject_install_page_css() -> None:
    """Public Install IPS App page — centered card, mobile-friendly, no sidebar."""
    st.markdown(
        f"""
<script>document.body.classList.add("ips-auth-login", "ips-install-page");</script>
<style id="ips-install-page-v1">
body.ips-install-page section[data-testid="stSidebar"],
body.ips-install-page [data-testid="stSidebarCollapsedControl"] {{
  display: none !important;
}}
body.ips-install-page section[data-testid="stMain"]:has(.ips-install-page-marker) .block-container {{
  max-width: 100% !important;
  padding: 1.5rem 1rem 2.5rem !important;
}}
body.ips-install-page section[data-testid="stMain"]:has(.ips-install-page-marker) [data-testid="stHorizontalBlock"] {{
  width: 100% !important;
  max-width: min(520px, calc(100vw - 1.5rem)) !important;
  margin: 0 auto !important;
}}
.ips-install-card {{
  background: #ffffff;
  border: 1px solid {BORDER};
  border-radius: 16px;
  box-shadow: 0 10px 36px rgba(15, 23, 42, 0.08);
  padding: 1.75rem 1.35rem 1.5rem;
  text-align: center;
  color: {TEXT};
}}
.ips-install-icon {{
  width: 120px;
  height: 120px;
  border-radius: 22px;
  box-shadow: 0 8px 24px rgba(37, 99, 235, 0.18);
  margin: 0 auto 1rem;
  display: block;
}}
.ips-install-title {{
  margin: 0 0 0.45rem 0;
  font-size: 1.55rem;
  font-weight: 800;
  color: {TEXT};
}}
.ips-install-lead {{
  margin: 0 0 1.15rem 0;
  font-size: 0.95rem;
  line-height: 1.5;
  color: {TEXT_MUTED};
}}
.ips-install-actions {{
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  margin-bottom: 0.85rem;
}}
.ips-install-btn {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: 44px;
  padding: 0.65rem 1rem;
  border-radius: 10px;
  font-size: 0.95rem;
  font-weight: 700;
  text-decoration: none !important;
  box-sizing: border-box;
  cursor: pointer;
  font-family: inherit;
}}
.ips-install-btn-primary {{
  background: {PRIMARY};
  color: #ffffff !important;
  border: none;
}}
.ips-install-btn-secondary {{
  background: #ffffff;
  color: {PRIMARY} !important;
  border: 1px solid #93c5fd;
}}
.ips-install-btn-prompt-ready {{
  background: #eff6ff;
  border-color: {PRIMARY};
}}
.ips-install-btn-hint {{
  margin: 0.35rem 0 0 0;
  font-size: 0.78rem;
  line-height: 1.35;
  color: {TEXT_MUTED};
}}
.ips-install-btn-copy {{
  margin-top: 0.55rem;
  background: #f8fafc;
  color: {TEXT} !important;
  border: 1px solid {BORDER};
  font-size: 0.88rem;
  min-height: 40px;
}}
.ips-install-status {{
  margin: 0 0 0.75rem 0;
  padding: 0.5rem 0.65rem;
  border-radius: 8px;
  font-size: 0.82rem;
  line-height: 1.4;
  text-align: center;
  background: #f8fafc;
  color: #475569;
  border: 1px solid #e2e8f0;
}}
.ips-install-help {{
  margin: 0.5rem 0 0 0;
  text-align: center;
}}
.ips-install-help-label {{
  margin: 0 0 0.35rem 0;
  font-size: 0.84rem;
  color: {TEXT_MUTED};
}}
.ips-install-help-details {{
  text-align: left;
  margin: 0;
}}
.ips-install-help-summary {{
  display: inline-block;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 700;
  color: {PRIMARY};
  list-style: none;
  margin-bottom: 0.35rem;
}}
.ips-install-help-summary::-webkit-details-marker {{
  display: none;
}}
.ips-install-steps {{
  display: none;
  margin: 0.35rem 0 0 0;
  padding: 0.65rem 0.75rem;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
}}
.ips-install-steps ol {{
  margin: 0;
  padding-left: 1.15rem;
  font-size: 0.88rem;
  line-height: 1.5;
  color: #334155;
}}
.ips-install-card[data-device="ios"] .ips-install-steps-ios,
.ips-install-card[data-device="android"] .ips-install-steps-android,
.ips-install-card[data-device="desktop"] .ips-install-steps-desktop,
.ips-install-card[data-device="pending"] .ips-install-steps-desktop {{
  display: block;
}}
.ips-install-share {{
  margin-top: 1.15rem;
  padding-top: 1rem;
  border-top: 1px solid #e2e8f0;
  text-align: center;
}}
.ips-install-share-note {{
  margin: 0 0 0.35rem 0;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  color: #64748b;
}}
.ips-install-share-url {{
  margin: 0;
  font-size: 0.8rem;
  line-height: 1.45;
  word-break: break-all;
  color: {TEXT_MUTED};
}}
</style>
""",
        unsafe_allow_html=True,
    )


def inject_unauthenticated_shell_css() -> None:
    """Login-only layout: centered card, no sidebar navigation."""
    st.markdown(
        f"""
<script>document.body.classList.add("ips-auth-login");</script>
<style id="ips-login-layout-v2">
body.ips-auth-login section[data-testid="stSidebar"],
body.ips-auth-login [data-testid="stSidebarCollapsedControl"] {{
  display: none !important;
  visibility: hidden !important;
  width: 0 !important;
  min-width: 0 !important;
}}
body.ips-auth-login [data-testid="stAppViewContainer"],
body.ips-auth-login section[data-testid="stMain"] {{
  background: {APP_BG} !important;
}}
body.ips-auth-login section[data-testid="stMain"]:has(.ips-login-page-marker) > div {{
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  width: 100% !important;
}}
body.ips-auth-login section[data-testid="stMain"]:has(.ips-login-page-marker) .block-container {{
  max-width: 100% !important;
  width: 100% !important;
  margin-left: auto !important;
  margin-right: auto !important;
  padding: 2rem 1.25rem 2.5rem !important;
  box-sizing: border-box !important;
}}
body.ips-auth-login section[data-testid="stMain"]:has(.ips-login-page-marker) [data-testid="stVerticalBlock"] {{
  align-items: center !important;
  width: 100% !important;
}}
body.ips-auth-login section[data-testid="stMain"]:has(.ips-login-page-marker) [data-testid="stHorizontalBlock"]:has(.ips-login-center-marker) {{
  width: 100% !important;
  max-width: min(480px, calc(100vw - 2rem)) !important;
  margin-left: auto !important;
  margin-right: auto !important;
  justify-content: center !important;
  gap: 0 !important;
}}
body.ips-auth-login section[data-testid="stMain"]:has(.ips-login-page-marker) [data-testid="column"]:has(.ips-login-center-marker) {{
  flex: 0 1 480px !important;
  width: 100% !important;
  max-width: min(480px, calc(100vw - 2rem)) !important;
  min-width: 0 !important;
}}
body.ips-auth-login .st-key-ips_login_card,
body.ips-auth-login [data-testid="stVerticalBlockBorderWrapper"].st-key-ips_login_card {{
  max-width: min(480px, 100%) !important;
  width: 100% !important;
  margin: 0 auto !important;
  align-self: center !important;
  padding: 1.75rem 1.5rem 1.5rem !important;
  background: #ffffff !important;
  border: 1px solid {BORDER} !important;
  border-radius: 14px !important;
  box-shadow: 0 8px 32px rgba(15, 23, 42, 0.08) !important;
  box-sizing: border-box !important;
}}
body.ips-auth-login .st-key-ips_login_card [data-testid="stVerticalBlock"] {{
  width: 100% !important;
  max-width: 100% !important;
  gap: 0.65rem !important;
}}
body.ips-auth-login .st-key-ips_login_card [data-testid="stElementContainer"] {{
  width: 100% !important;
  max-width: 100% !important;
}}
body.ips-auth-login .st-key-ips_login_card .ips-login-brand {{
  text-align: center !important;
  margin-bottom: 0.35rem !important;
}}
body.ips-auth-login .st-key-ips_login_card .ips-page-title {{
  font-size: 1.65rem !important;
  font-weight: 800 !important;
  margin: 0 0 0.35rem 0 !important;
  color: {TEXT} !important;
}}
body.ips-auth-login .st-key-ips_login_card .ips-page-subtitle {{
  font-size: 0.92rem !important;
  color: {TEXT_MUTED} !important;
}}
body.ips-auth-login .ips-login-install-footer {{
  margin-top: 1.15rem;
  padding-top: 1rem;
  border-top: 1px solid {BORDER};
  text-align: center;
}}
body.ips-auth-login .ips-login-install-footer-title {{
  margin: 0 0 0.35rem 0;
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #475569;
}}
body.ips-auth-login .ips-login-install-footer-text {{
  margin: 0 0 0.65rem 0;
  font-size: 0.82rem;
  line-height: 1.45;
  color: {TEXT_MUTED};
}}
body.ips-auth-login .ips-login-install-footer-link {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 38px;
  padding: 0.45rem 0.9rem;
  border-radius: 8px;
  background: #f8fafc;
  border: 1px solid {BORDER};
  color: {PRIMARY} !important;
  font-size: 0.88rem;
  font-weight: 700;
  text-decoration: none !important;
  margin: 0 !important;
  line-height: 1.45 !important;
}}
body.ips-auth-login .st-key-ips_login_card [data-testid="stTextInput"],
body.ips-auth-login .st-key-ips_login_card [data-testid="stTextInput"] > div,
body.ips-auth-login .st-key-ips_login_card [data-testid="stTextInput"] input,
body.ips-auth-login .st-key-ips_login_card [data-testid="stButton"],
body.ips-auth-login .st-key-ips_login_card [data-testid="stButton"] > button,
body.ips-auth-login .st-key-ips_login_card [data-testid="stRadio"],
body.ips-auth-login .st-key-ips_login_card [data-testid="stRadio"] > div,
body.ips-auth-login .st-key-ips_login_card [data-testid="stCheckbox"],
body.ips-auth-login .st-key-ips_login_card [data-testid="stCheckbox"] label {{
  width: 100% !important;
  max-width: 100% !important;
  box-sizing: border-box !important;
}}
body.ips-auth-login .st-key-ips_login_card [data-testid="stHorizontalBlock"] {{
  width: 100% !important;
  max-width: 100% !important;
}}
body.ips-auth-login .st-key-ips_login_card [data-testid="stHorizontalBlock"] > [data-testid="column"] {{
  flex: 1 1 0 !important;
  min-width: 0 !important;
}}
</style>
""",
        unsafe_allow_html=True,
    )


def inject_authenticated_shell_css() -> None:
    """Full app layout after login."""
    st.markdown(
        '<script>document.body.classList.remove("ips-auth-login");document.body.classList.add("ips-authed-app");</script>',
        unsafe_allow_html=True,
    )
    try:
        from app.components.sidebar_shell import inject_desktop_nav_rail_css
    except ImportError:
        from components.sidebar_shell import inject_desktop_nav_rail_css  # type: ignore
    inject_desktop_nav_rail_css()


def inject_ips_dialog_styles() -> None:
    """Reusable IPS SaaS dialog / ``st.dialog`` styling (Jobs detail and future modals)."""
    st.markdown(
        f"""
<style id="ips-dialog-styles-v4">
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
  overflow-x: hidden !important;
  overflow-y: auto !important;
  padding-top: 14px !important;
}}
div[data-testid="stDialog"] [data-testid="stDateInput"],
div[data-testid="stDialog"] [data-testid="stDateInput"] > div,
div[data-testid="stDialog"] [data-testid="stElementContainer"]:has([data-testid="stDateInput"]),
div[data-testid="stDialog"] [data-testid="stVerticalBlock"]:has([data-testid="stDateInput"]),
div[data-testid="stDialog"] [data-testid="stTabContent"]:has([data-testid="stDateInput"]),
div[data-testid="stDialog"] [data-testid="column"]:has([data-testid="stDateInput"]) {{
  overflow: visible !important;
}}
body:has(div[data-testid="stDialog"]) div[data-baseweb="popover"]:has([data-baseweb="calendar"]),
body:has(div[data-testid="stDialog"]) .ips-dialog-date-popper,
body:has(div[data-testid="stDialog"]) .hire-date-popper {{
  z-index: 100000 !important;
  position: fixed !important;
  overflow: visible !important;
  pointer-events: auto !important;
}}
body:has(div[data-testid="stDialog"]) div[data-baseweb="popover"]:has([data-baseweb="calendar"]) [data-baseweb="calendar"],
body:has(div[data-testid="stDialog"]) .ips-dialog-date-popper [data-baseweb="calendar"],
body:has(div[data-testid="stDialog"]) .hire-date-popper [data-baseweb="calendar"] {{
  overflow: visible !important;
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
div[data-testid="stDialog"] [data-testid="stElementContainer"]:not([class*="st-key-ips_dng_o_"]):not([class*="st-key-ips_dng_s_"]):not([class*="st-key-ips_succ_s_"]):not([class*="st-key-ips_warn_s_"]) [data-testid="stButton"] > button,
div[data-testid="stDialog"] [data-testid="stElementContainer"]:not([class*="st-key-ips_dng_o_"]):not([class*="st-key-ips_dng_s_"]):not([class*="st-key-ips_succ_s_"]):not([class*="st-key-ips_warn_s_"]) .stButton > button {{
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
div[data-testid="stDialog"]:has(.ips-compact-detail-modal) [data-testid="stElementContainer"]:not([class*="st-key-ips_dng_o_"]):not([class*="st-key-ips_dng_s_"]):not([class*="st-key-ips_succ_s_"]):not([class*="st-key-ips_warn_s_"]) [data-testid="stButton"] > button,
div[data-testid="stDialog"]:has(.ips-compact-detail-modal) [data-testid="stElementContainer"]:not([class*="st-key-ips_dng_o_"]):not([class*="st-key-ips_dng_s_"]):not([class*="st-key-ips_succ_s_"]):not([class*="st-key-ips_warn_s_"]) .stButton > button {{
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
div[data-testid="stDialog"] [class*="st-key-ips_tabs_wrap_"] [data-testid="stRadio"] {{
  display: block !important;
}}
div[data-testid="stDialog"]:has(.ips-estimate-detail-modal) > div,
div[data-testid="stDialog"]:has(.ips-estimate-detail-modal) div[role="dialog"] {{
  overflow-x: hidden !important;
  overflow-y: auto !important;
  max-height: min(90vh, 920px) !important;
}}
div[data-testid="stDialog"]:has(.ips-estimate-detail-modal) [class*="st-key-ips_tabs_wrap_est_detail_active_tab"] {{
  position: sticky;
  top: 0;
  z-index: 5;
  background: #ffffff;
  padding-top: 0.15rem;
  padding-bottom: 0.35rem;
  margin-bottom: 0.65rem;
  border-bottom: 1px solid #e2e8f0;
  box-shadow: 0 1px 0 rgba(255, 255, 255, 0.9);
}}
div[data-testid="stDialog"]:has(.ips-estimate-detail-modal) [class*="st-key-ips_tabs_wrap_est_detail_active_tab"] [data-testid="stRadio"] {{
  display: block !important;
  width: 100%;
  max-width: 100%;
  overflow: visible !important;
}}
div[data-testid="stDialog"]:has(.ips-estimate-detail-modal) [class*="st-key-ips_tabs_wrap_est_detail_active_tab"] [data-testid="stRadio"] > div {{
  display: flex !important;
  flex-direction: row !important;
  flex-wrap: nowrap !important;
  overflow-x: auto !important;
  overflow-y: hidden !important;
  gap: 0.15rem !important;
  width: 100%;
  max-width: 100%;
  scrollbar-width: thin;
  -webkit-overflow-scrolling: touch;
}}
div[data-testid="stDialog"]:has(.ips-estimate-detail-modal) [class*="st-key-ips_tabs_wrap_est_detail_active_tab"] [data-testid="stRadio"] label {{
  flex: 0 0 auto !important;
  white-space: nowrap !important;
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
.job-detail-actions-row-marker {{
  display: none !important;
}}
div[data-testid="stElementContainer"]:has(.job-detail-actions-row-marker) {{
  margin-top: 16px !important;
  margin-bottom: 18px !important;
}}
div[data-testid="stElementContainer"]:has(.job-detail-actions-row-marker) [data-testid="stHorizontalBlock"],
div[data-testid="stDialog"] div[data-testid="stElementContainer"]:has(.job-detail-actions-row-marker) [data-testid="stHorizontalBlock"] {{
  display: flex !important;
  align-items: center !important;
  justify-content: flex-end !important;
  flex-wrap: wrap !important;
  gap: 14px !important;
  width: 100% !important;
}}
div[data-testid="stElementContainer"]:has(.job-detail-actions-row-marker) [data-testid="column"],
div[data-testid="stDialog"] div[data-testid="stElementContainer"]:has(.job-detail-actions-row-marker) [data-testid="column"] {{
  flex: 0 0 auto !important;
  width: auto !important;
  min-width: 0 !important;
}}
div[data-testid="stElementContainer"]:has(.job-detail-actions-row-marker) [data-testid="stButton"] > button,
div[data-testid="stDialog"] div[data-testid="stElementContainer"]:has(.job-detail-actions-row-marker) [data-testid="stButton"] > button {{
  height: 40px !important;
  min-height: 40px !important;
  min-width: 110px !important;
  border-radius: 8px !important;
  padding: 0 16px !important;
}}
div[data-testid="stElementContainer"]:has(.job-detail-actions-row-marker) [data-testid="column"]:has(.job-detail-edit-marker) [data-testid="stButton"] > button,
div[data-testid="stDialog"] div[data-testid="stElementContainer"]:has(.job-detail-actions-row-marker) [data-testid="column"]:has(.job-detail-edit-marker) [data-testid="stButton"] > button {{
  background: #ffffff !important;
  border: 1px solid #d1d5db !important;
  color: #111827 !important;
  box-shadow: none !important;
}}
.job-detail-edit-marker {{
  display: none !important;
}}

.ips-compact-detail-header {{
  padding: 2px 0 10px 0;
  border-bottom: 1px solid #e5eaf1;
  margin-bottom: 10px;
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
.ips-compact-detail-title-row {{
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}}
.ips-compact-detail-status {{
  display: flex;
  align-items: center;
  flex: 0 0 auto;
  min-height: 36px;
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
  padding-top: 0;
  min-height: 36px;
}}
.ips-compact-detail-actions-row-marker {{
  display: none !important;
}}
div[data-testid="stDialog"]:has(.ips-compact-detail-modal) .ips-compact-detail-header:has(.ips-compact-detail-actions-row-marker) [data-testid="column"]:last-child {{
  min-width: 0 !important;
  overflow: visible !important;
}}
div[data-testid="stDialog"]:has(.ips-compact-detail-modal) .ips-compact-detail-header:has(.ips-compact-detail-actions-row-marker) [data-testid="column"]:last-child [data-testid="stHorizontalBlock"] {{
  display: flex !important;
  flex-wrap: wrap !important;
  align-items: center !important;
  justify-content: flex-end !important;
  gap: 8px !important;
  row-gap: 8px !important;
}}
div[data-testid="stDialog"]:has(.ips-compact-detail-modal) .ips-compact-detail-header:has(.ips-compact-detail-actions-row-marker) [data-testid="column"]:last-child [data-testid="stHorizontalBlock"] > [data-testid="column"] {{
  flex: 0 0 auto !important;
  width: auto !important;
  min-width: 0 !important;
  max-width: none !important;
  display: flex !important;
  align-items: center !important;
  align-self: center !important;
  padding: 0 !important;
  margin: 0 !important;
}}
div[data-testid="stDialog"]:has(.ips-compact-detail-modal) .ips-compact-detail-header:has(.ips-compact-detail-actions-row-marker) [data-testid="stElementContainer"] {{
  margin: 0 !important;
  padding: 0 !important;
}}
div[data-testid="stDialog"]:has(.ips-compact-detail-modal) .ips-compact-detail-header:has(.ips-compact-detail-actions-row-marker) [data-testid="stElementContainer"] [data-testid="stHorizontalBlock"] {{
  gap: 8px !important;
  flex-wrap: wrap !important;
  align-items: center !important;
  justify-content: flex-end !important;
}}
div[data-testid="stDialog"]:has(.ips-compact-detail-modal) .ips-compact-detail-header:has(.ips-compact-detail-actions-row-marker) [data-testid="stButton"] > button {{
  height: 36px !important;
  min-height: 36px !important;
  white-space: nowrap !important;
  padding-left: 0.65rem !important;
  padding-right: 0.65rem !important;
  font-size: 0.8125rem !important;
}}
div[data-testid="stDialog"]:has(.ips-compact-detail-modal) .ips-compact-detail-header [data-testid="stHorizontalBlock"] {{
  align-items: center !important;
}}
div[data-testid="stDialog"]:has(.ips-compact-detail-modal) .ips-compact-detail-header [data-testid="column"] {{
  align-self: center !important;
}}
div[data-testid="stDialog"]:has(.ips-compact-detail-modal) .ips-compact-detail-header [data-testid="column"]:last-child [data-testid="stHorizontalBlock"] {{
  justify-content: flex-end !important;
}}
.ips-user-actions-header-marker,
.ips-asset-actions-header-marker {{
  display: none !important;
}}
div[data-testid="stElementContainer"]:has(.ips-user-actions-header-marker),
div[data-testid="stElementContainer"]:has(.ips-asset-actions-header-marker) {{
  margin: 0 !important;
  padding: 0 !important;
}}
div[data-testid="stElementContainer"]:has(.ips-user-actions-header-marker) [data-testid="stHorizontalBlock"],
div[data-testid="stElementContainer"]:has(.ips-asset-actions-header-marker) [data-testid="stHorizontalBlock"] {{
  gap: 8px !important;
  flex-wrap: wrap !important;
  align-items: center !important;
  justify-content: flex-end !important;
}}
div[data-testid="stDialog"]:has(.ips-compact-detail-modal) .ips-compact-detail-header [class*="st-key-ips_succ_s_"] [data-testid="stButton"] > button,
div[data-testid="stDialog"]:has(.ips-compact-detail-modal) .ips-compact-detail-header [class*="st-key-ips_warn_s_"] [data-testid="stButton"] > button,
div[data-testid="stDialog"]:has(.ips-compact-detail-modal) .ips-compact-detail-header [class*="st-key-ips_dng_s_"] [data-testid="stButton"] > button {{
  height: 36px !important;
  min-height: 36px !important;
}}
.ips-compact-meta-grid {{
  display: grid;
  grid-template-columns: repeat(4, minmax(130px, 1fr));
  gap: 8px;
  margin: 8px 0;
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
  padding: 9px 11px;
  min-height: 56px;
  max-height: 68px;
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
.ips-job-doc-delete-confirm-marker {{
  display: none !important;
}}
.ips-job-doc-delete-confirm-message {{
  font-size: 13px;
  font-weight: 600;
  color: #991b1b;
  line-height: 1.35;
  margin: 0;
}}
div[data-testid="stDialog"] [class*="st-key-job_doc_delete_confirm_"] [data-testid="stHorizontalBlock"],
div[data-testid="stDialog"] [class*="st-key-job_subjob_doc_"][class*="doc_delete_confirm_"] [data-testid="stHorizontalBlock"] {{
  border-bottom: none !important;
  background: transparent !important;
  min-height: 40px !important;
  padding: 0 !important;
}}
div[data-testid="stDialog"] [class*="st-key-confirm_delete_job_doc_"] .stButton > button,
div[data-testid="stDialog"] [class*="st-key-job_subjob_doc_"][class*="confirm_delete_doc_"] .stButton > button {{
  background: #dc2626 !important;
  border: 1px solid #dc2626 !important;
  color: #ffffff !important;
  font-size: 12px !important;
  min-height: 30px !important;
  height: 30px !important;
  padding: 0 10px !important;
}}
div[data-testid="stDialog"] [class*="st-key-confirm_delete_job_doc_"] .stButton > button:hover,
div[data-testid="stDialog"] [class*="st-key-job_subjob_doc_"][class*="confirm_delete_doc_"] .stButton > button:hover {{
  background: #b91c1c !important;
  border-color: #b91c1c !important;
}}
div[data-testid="stDialog"] [class*="st-key-cancel_delete_job_doc_"] .stButton > button,
div[data-testid="stDialog"] [class*="st-key-job_subjob_doc_"][class*="cancel_delete_doc_"] .stButton > button {{
  background: #ffffff !important;
  border: 1px solid #cbd5e1 !important;
  color: #334155 !important;
  font-size: 12px !important;
  min-height: 30px !important;
  height: 30px !important;
  padding: 0 10px !important;
}}
</style>
""",
        unsafe_allow_html=True,
    )
    st.markdown(
        """
<script>
(function () {
  var w = window.parent || window;
  var doc = w.document;
  if (w.__ipsDialogDatePopperBound) return;
  w.__ipsDialogDatePopperBound = true;

  var DIALOG_SEL = 'div[data-testid="stDialog"]';
  var DATE_INPUT_SEL = '[data-testid="stDateInput"]';
  var POPPER_SEL = 'div[data-baseweb="popover"]:has([data-baseweb="calendar"])';

  function dialogHasDateInput() {
    var dialog = doc.querySelector(DIALOG_SEL);
    return !!(dialog && dialog.querySelector(DATE_INPUT_SEL));
  }

  function elevatePopper(pop) {
    if (!pop || !dialogHasDateInput()) return;
    pop.classList.add('ips-dialog-date-popper', 'hire-date-popper');
    pop.style.zIndex = '100000';
    pop.style.position = 'fixed';
    pop.style.overflow = 'visible';
    if (pop.parentElement && pop.parentElement !== doc.body) {
      doc.body.appendChild(pop);
    }
  }

  function scan() {
    if (!dialogHasDateInput()) return;
    doc.querySelectorAll(POPPER_SEL).forEach(elevatePopper);
  }

  scan();
  if (!doc.__ipsDialogDatePopperObserver) {
    doc.__ipsDialogDatePopperObserver = new MutationObserver(scan);
    doc.__ipsDialogDatePopperObserver.observe(doc.body, {
      childList: true,
      subtree: true,
    });
  }
})();
</script>
        """,
        unsafe_allow_html=True,
    )


def inject_action_colors_css() -> None:
    """Shared destructive buttons and semantic status pill colors."""
    st.markdown(
        """
<style id="ips-action-colors-v6">
/* ----- Small red trash-can delete icon buttons ----- */
[class*="st-key-delete_subjob_"] [data-testid="stButton"] > button,
[class*="st-key-delete_subjob_"] .stButton > button,
[class*="st-key-delete_job_doc_"] [data-testid="stButton"] > button,
[class*="st-key-delete_job_doc_"] .stButton > button,
[class*="st-key-job_subjob_doc_"][class*="_doc_delete_"]:not([class*="confirm"]):not([class*="cancel"]) [data-testid="stButton"] > button,
[class*="st-key-job_subjob_doc_"][class*="_doc_delete_"]:not([class*="confirm"]):not([class*="cancel"]) .stButton > button,
[class*="st-key-tk_del_"] [data-testid="stButton"] > button,
[class*="st-key-tk_del_"] .stButton > button,
[class*="st-key-jrow_del_"] [data-testid="stButton"] > button,
[class*="st-key-jrow_del_"] .stButton > button,
[class*="st-key-est_row_del_"] [data-testid="stButton"] > button,
[class*="st-key-est_row_del_"] .stButton > button,
.st-key-job_tasks_table_wrap [class*="st-key-job_task_delete_"] [data-testid="stButton"] > button,
.st-key-job_tasks_table_wrap [class*="st-key-job_task_delete_"] .stButton > button {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  font-size: 0 !important;
  line-height: 0 !important;
  color: transparent !important;
  padding: 0 !important;
  min-height: 28px !important;
  height: 28px !important;
  width: 28px !important;
  min-width: 28px !important;
  margin: 0 auto !important;
  position: relative !important;
}
[class*="st-key-delete_subjob_"] [data-testid="stButton"] > button p,
[class*="st-key-delete_subjob_"] .stButton > button p,
[class*="st-key-delete_job_doc_"] [data-testid="stButton"] > button p,
[class*="st-key-delete_job_doc_"] .stButton > button p,
[class*="st-key-job_subjob_doc_"][class*="_doc_delete_"]:not([class*="confirm"]):not([class*="cancel"]) [data-testid="stButton"] > button p,
[class*="st-key-job_subjob_doc_"][class*="_doc_delete_"]:not([class*="confirm"]):not([class*="cancel"]) .stButton > button p,
[class*="st-key-tk_del_"] [data-testid="stButton"] > button p,
[class*="st-key-tk_del_"] .stButton > button p,
[class*="st-key-jrow_del_"] [data-testid="stButton"] > button p,
[class*="st-key-jrow_del_"] .stButton > button p,
[class*="st-key-est_row_del_"] [data-testid="stButton"] > button p,
[class*="st-key-est_row_del_"] .stButton > button p,
.st-key-job_tasks_table_wrap [class*="st-key-job_task_delete_"] [data-testid="stButton"] > button p,
.st-key-job_tasks_table_wrap [class*="st-key-job_task_delete_"] .stButton > button p {
  display: none !important;
}
[class*="st-key-delete_subjob_"] [data-testid="stButton"] > button::after,
[class*="st-key-delete_subjob_"] .stButton > button::after,
[class*="st-key-delete_job_doc_"] [data-testid="stButton"] > button::after,
[class*="st-key-delete_job_doc_"] .stButton > button::after,
[class*="st-key-job_subjob_doc_"][class*="_doc_delete_"]:not([class*="confirm"]):not([class*="cancel"]) [data-testid="stButton"] > button::after,
[class*="st-key-job_subjob_doc_"][class*="_doc_delete_"]:not([class*="confirm"]):not([class*="cancel"]) .stButton > button::after,
[class*="st-key-tk_del_"] [data-testid="stButton"] > button::after,
[class*="st-key-tk_del_"] .stButton > button::after,
[class*="st-key-jrow_del_"] [data-testid="stButton"] > button::after,
[class*="st-key-jrow_del_"] .stButton > button::after,
[class*="st-key-est_row_del_"] [data-testid="stButton"] > button::after,
[class*="st-key-est_row_del_"] .stButton > button::after,
.st-key-job_tasks_table_wrap [class*="st-key-job_task_delete_"] [data-testid="stButton"] > button::after,
.st-key-job_tasks_table_wrap [class*="st-key-job_task_delete_"] .stButton > button::after {
  content: "" !important;
  display: inline-block !important;
  width: 16px !important;
  height: 16px !important;
  background-color: #dc2626 !important;
  -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%23000'%3E%3Cpath d='M9 3h6l1 2h4v2H4V5h4l1-2zm1 6h2v9h-2V9zm4 0h2v9h-2V9zM6 9h2v9H6V9z'/%3E%3C/svg%3E") center / contain no-repeat !important;
  mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%23000'%3E%3Cpath d='M9 3h6l1 2h4v2H4V5h4l1-2zm1 6h2v9h-2V9zm4 0h2v9h-2V9zM6 9h2v9H6V9z'/%3E%3C/svg%3E") center / contain no-repeat !important;
}
[class*="st-key-delete_subjob_"] [data-testid="stButton"] > button:hover,
[class*="st-key-delete_subjob_"] .stButton > button:hover,
[class*="st-key-delete_job_doc_"] [data-testid="stButton"] > button:hover,
[class*="st-key-delete_job_doc_"] .stButton > button:hover,
[class*="st-key-job_subjob_doc_"][class*="_doc_delete_"]:not([class*="confirm"]):not([class*="cancel"]) [data-testid="stButton"] > button:hover,
[class*="st-key-job_subjob_doc_"][class*="_doc_delete_"]:not([class*="confirm"]):not([class*="cancel"]) .stButton > button:hover,
[class*="st-key-tk_del_"] [data-testid="stButton"] > button:hover,
[class*="st-key-tk_del_"] .stButton > button:hover,
[class*="st-key-jrow_del_"] [data-testid="stButton"] > button:hover,
[class*="st-key-jrow_del_"] .stButton > button:hover,
[class*="st-key-est_row_del_"] [data-testid="stButton"] > button:hover,
[class*="st-key-est_row_del_"] .stButton > button:hover,
.st-key-job_tasks_table_wrap [class*="st-key-job_task_delete_"] [data-testid="stButton"] > button:hover,
.st-key-job_tasks_table_wrap [class*="st-key-job_task_delete_"] .stButton > button:hover {
  background: #fef2f2 !important;
  border-radius: 6px !important;
}
[class*="st-key-delete_subjob_"] [data-testid="stButton"] > button:hover::after,
[class*="st-key-delete_subjob_"] .stButton > button:hover::after,
[class*="st-key-delete_job_doc_"] [data-testid="stButton"] > button:hover::after,
[class*="st-key-delete_job_doc_"] .stButton > button:hover::after,
[class*="st-key-job_subjob_doc_"][class*="_doc_delete_"]:not([class*="confirm"]):not([class*="cancel"]) [data-testid="stButton"] > button:hover::after,
[class*="st-key-job_subjob_doc_"][class*="_doc_delete_"]:not([class*="confirm"]):not([class*="cancel"]) .stButton > button:hover::after,
[class*="st-key-tk_del_"] [data-testid="stButton"] > button:hover::after,
[class*="st-key-tk_del_"] .stButton > button:hover::after,
[class*="st-key-jrow_del_"] [data-testid="stButton"] > button:hover::after,
[class*="st-key-jrow_del_"] .stButton > button:hover::after,
[class*="st-key-est_row_del_"] [data-testid="stButton"] > button:hover::after,
[class*="st-key-est_row_del_"] .stButton > button:hover::after,
.st-key-job_tasks_table_wrap [class*="st-key-job_task_delete_"] [data-testid="stButton"] > button:hover::after,
.st-key-job_tasks_table_wrap [class*="st-key-job_task_delete_"] .stButton > button:hover::after {
  background-color: #b91c1c !important;
}

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

[class*="st-key-ips_succ_s_"] [data-testid="stButton"] > button,
[class*="st-key-ips_succ_s_"] .stButton > button,
[class*="st-key-ips_succ_s_"][data-testid="stButton"] > button,
.stButton[class*="st-key-ips_succ_s_"] > button,
div[data-testid="stElementContainer"][class*="st-key-ips_succ_s_"] [data-testid="stButton"] > button {
    background: #16a34a !important;
    color: #ffffff !important;
    border: 1px solid #16a34a !important;
    border-radius: 10px !important;
    font-weight: 800 !important;
    height: 38px !important;
    padding: 0 16px !important;
    width: auto !important;
    max-width: none !important;
}
[class*="st-key-ips_succ_s_"] [data-testid="stButton"] > button:hover,
[class*="st-key-ips_succ_s_"] .stButton > button:hover,
[class*="st-key-ips_succ_s_"][data-testid="stButton"] > button:hover {
    background: #15803d !important;
    border-color: #15803d !important;
}

[class*="st-key-ips_warn_s_"] [data-testid="stButton"] > button,
[class*="st-key-ips_warn_s_"] .stButton > button,
[class*="st-key-ips_warn_s_"][data-testid="stButton"] > button,
.stButton[class*="st-key-ips_warn_s_"] > button,
div[data-testid="stElementContainer"][class*="st-key-ips_warn_s_"] [data-testid="stButton"] > button {
    background: #f59e0b !important;
    color: #ffffff !important;
    border: 1px solid #f59e0b !important;
    border-radius: 10px !important;
    font-weight: 800 !important;
    height: 38px !important;
    padding: 0 16px !important;
    width: auto !important;
    max-width: none !important;
}
[class*="st-key-ips_warn_s_"] [data-testid="stButton"] > button:hover,
[class*="st-key-ips_warn_s_"] .stButton > button:hover,
[class*="st-key-ips_warn_s_"][data-testid="stButton"] > button:hover {
    background: #d97706 !important;
    border-color: #d97706 !important;
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
div[data-testid="stDialog"] [class*="st-key-ips_succ_s_"] [data-testid="stButton"] > button,
div[data-testid="stDialog"] [class*="st-key-ips_succ_s_"] .stButton > button,
div[data-testid="stDialog"] [class*="st-key-ips_succ_s_"][data-testid="stButton"] > button {
    background: #16a34a !important;
    color: #ffffff !important;
    border: 1px solid #16a34a !important;
    width: auto !important;
    min-width: 0 !important;
    height: 38px !important;
}
div[data-testid="stDialog"] [class*="st-key-ips_warn_s_"] [data-testid="stButton"] > button,
div[data-testid="stDialog"] [class*="st-key-ips_warn_s_"] .stButton > button,
div[data-testid="stDialog"] [class*="st-key-ips_warn_s_"][data-testid="stButton"] > button {
    background: #f59e0b !important;
    color: #ffffff !important;
    border: 1px solid #f59e0b !important;
    width: auto !important;
    min-width: 0 !important;
    height: 38px !important;
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

.ips-action-row {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
    margin-top: 14px;
}
.ips-confirm-card {
    margin-top: 14px;
    padding: 14px;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    background: #ffffff;
}
.ips-confirm-title {
    font-size: 15px;
    font-weight: 800;
    color: #0f172a;
    margin-bottom: 6px;
}
.ips-confirm-text {
    font-size: 14px;
    color: #475569;
    margin-bottom: 12px;
}
div[data-testid="stElementContainer"]:has(.ips-job-actions-marker),
div[data-testid="stElementContainer"]:has(.ips-user-actions-marker),
div[data-testid="stElementContainer"]:has(.ips-estimate-actions-marker),
div[data-testid="stElementContainer"]:has(.ips-inventory-actions-marker),
div[data-testid="stElementContainer"]:has(.ips-asset-actions-marker),
div[data-testid="stElementContainer"]:has(.ips-catalog-presence-marker) {
    margin-top: 0.65rem !important;
    margin-bottom: 0.35rem !important;
}
.ips-job-actions-title,
.ips-user-actions-title,
.ips-estimate-actions-title,
.ips-inventory-actions-title,
.ips-asset-actions-title,
.ips-catalog-presence-title {
    margin: 0 0 0.45rem 0;
    font-size: 0.72rem;
    font-weight: 800;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: #475569;
}
.ips-inventory-pg-status {
    margin: 0 0 0.55rem 0;
    font-size: 0.8125rem;
    line-height: 1.45;
    color: #334155;
}
.ips-inventory-pg-status span {
    color: #64748b;
    font-size: 0.75rem;
}
div[data-testid="stElementContainer"]:has(.ips-job-actions-marker) [data-testid="stHorizontalBlock"],
div[data-testid="stElementContainer"]:has(.ips-user-actions-marker) [data-testid="stHorizontalBlock"],
div[data-testid="stElementContainer"]:has(.ips-estimate-actions-marker) [data-testid="stHorizontalBlock"],
div[data-testid="stElementContainer"]:has(.ips-inventory-actions-marker) [data-testid="stHorizontalBlock"],
div[data-testid="stElementContainer"]:has(.ips-asset-actions-marker) [data-testid="stHorizontalBlock"],
div[data-testid="stElementContainer"]:has(.ips-catalog-presence-marker) [data-testid="stHorizontalBlock"] {
    gap: 12px !important;
    flex-wrap: wrap !important;
    align-items: center !important;
}
div[data-testid="stElementContainer"]:has(.ips-user-actions-header-marker) [data-testid="stHorizontalBlock"],
div[data-testid="stElementContainer"]:has(.ips-asset-actions-header-marker) [data-testid="stHorizontalBlock"] {
    gap: 8px !important;
    flex-wrap: nowrap !important;
    align-items: center !important;
}
div[data-testid="stElementContainer"]:has(.ips-job-actions-marker) [data-testid="column"],
div[data-testid="stElementContainer"]:has(.ips-user-actions-marker) [data-testid="column"],
div[data-testid="stElementContainer"]:has(.ips-user-actions-header-marker) [data-testid="column"],
div[data-testid="stElementContainer"]:has(.ips-asset-actions-header-marker) [data-testid="column"],
div[data-testid="stElementContainer"]:has(.ips-estimate-actions-marker) [data-testid="column"],
div[data-testid="stElementContainer"]:has(.ips-inventory-actions-marker) [data-testid="column"],
div[data-testid="stElementContainer"]:has(.ips-asset-actions-marker) [data-testid="column"],
div[data-testid="stElementContainer"]:has(.ips-catalog-presence-marker) [data-testid="column"] {
    flex: 0 0 auto !important;
    width: auto !important;
    min-width: 0 !important;
}
div[data-testid="stElementContainer"]:has(.ips-job-actions-marker) [class*="st-key-ips_succ_s_"] [data-testid="stButton"] > button,
div[data-testid="stElementContainer"]:has(.ips-job-actions-marker) [class*="st-key-ips_warn_s_"] [data-testid="stButton"] > button,
div[data-testid="stElementContainer"]:has(.ips-job-actions-marker) [class*="st-key-ips_dng_s_"] [data-testid="stButton"] > button,
div[data-testid="stElementContainer"]:has(.ips-user-actions-marker) [class*="st-key-ips_succ_s_"] [data-testid="stButton"] > button,
div[data-testid="stElementContainer"]:has(.ips-user-actions-marker) [class*="st-key-ips_warn_s_"] [data-testid="stButton"] > button,
div[data-testid="stElementContainer"]:has(.ips-user-actions-marker) [class*="st-key-ips_dng_s_"] [data-testid="stButton"] > button,
div[data-testid="stElementContainer"]:has(.ips-user-actions-header-marker) [class*="st-key-ips_succ_s_"] [data-testid="stButton"] > button,
div[data-testid="stElementContainer"]:has(.ips-user-actions-header-marker) [class*="st-key-ips_warn_s_"] [data-testid="stButton"] > button,
div[data-testid="stElementContainer"]:has(.ips-user-actions-header-marker) [class*="st-key-ips_dng_s_"] [data-testid="stButton"] > button,
div[data-testid="stElementContainer"]:has(.ips-asset-actions-header-marker) [class*="st-key-ips_succ_s_"] [data-testid="stButton"] > button,
div[data-testid="stElementContainer"]:has(.ips-asset-actions-header-marker) [class*="st-key-ips_warn_s_"] [data-testid="stButton"] > button,
div[data-testid="stElementContainer"]:has(.ips-asset-actions-header-marker) [class*="st-key-ips_dng_s_"] [data-testid="stButton"] > button,
div[data-testid="stElementContainer"]:has(.ips-estimate-actions-marker) [class*="st-key-ips_succ_s_"] [data-testid="stButton"] > button,
div[data-testid="stElementContainer"]:has(.ips-estimate-actions-marker) [class*="st-key-ips_warn_s_"] [data-testid="stButton"] > button,
div[data-testid="stElementContainer"]:has(.ips-estimate-actions-marker) [class*="st-key-ips_dng_s_"] [data-testid="stButton"] > button,
div[data-testid="stElementContainer"]:has(.ips-inventory-actions-marker) [class*="st-key-ips_succ_s_"] [data-testid="stButton"] > button,
div[data-testid="stElementContainer"]:has(.ips-inventory-actions-marker) [class*="st-key-ips_warn_s_"] [data-testid="stButton"] > button,
div[data-testid="stElementContainer"]:has(.ips-inventory-actions-marker) [class*="st-key-ips_dng_s_"] [data-testid="stButton"] > button,
div[data-testid="stElementContainer"]:has(.ips-asset-actions-marker) [class*="st-key-ips_succ_s_"] [data-testid="stButton"] > button,
div[data-testid="stElementContainer"]:has(.ips-asset-actions-marker) [class*="st-key-ips_warn_s_"] [data-testid="stButton"] > button,
div[data-testid="stElementContainer"]:has(.ips-asset-actions-marker) [class*="st-key-ips_dng_s_"] [data-testid="stButton"] > button,
div[data-testid="stElementContainer"]:has(.ips-catalog-presence-marker) [class*="st-key-ips_succ_s_"] [data-testid="stButton"] > button,
div[data-testid="stElementContainer"]:has(.ips-catalog-presence-marker) [class*="st-key-ips_warn_s_"] [data-testid="stButton"] > button,
div[data-testid="stElementContainer"]:has(.ips-catalog-presence-marker) [class*="st-key-ips_dng_s_"] [data-testid="stButton"] > button {
    width: auto !important;
    min-width: 0 !important;
    max-width: none !important;
}
div[data-testid="stDialog"] div[data-testid="stElementContainer"]:has(.ips-job-actions-marker) [class*="st-key-ips_succ_s_"] [data-testid="stButton"] > button,
div[data-testid="stDialog"] div[data-testid="stElementContainer"]:has(.ips-job-actions-marker) [class*="st-key-ips_warn_s_"] [data-testid="stButton"] > button,
div[data-testid="stDialog"] div[data-testid="stElementContainer"]:has(.ips-job-actions-marker) [class*="st-key-ips_dng_s_"] [data-testid="stButton"] > button,
div[data-testid="stDialog"] div[data-testid="stElementContainer"]:has(.ips-user-actions-marker) [class*="st-key-ips_succ_s_"] [data-testid="stButton"] > button,
div[data-testid="stDialog"] div[data-testid="stElementContainer"]:has(.ips-user-actions-marker) [class*="st-key-ips_warn_s_"] [data-testid="stButton"] > button,
div[data-testid="stDialog"] div[data-testid="stElementContainer"]:has(.ips-user-actions-marker) [class*="st-key-ips_dng_s_"] [data-testid="stButton"] > button,
div[data-testid="stDialog"] div[data-testid="stElementContainer"]:has(.ips-user-actions-header-marker) [class*="st-key-ips_succ_s_"] [data-testid="stButton"] > button,
div[data-testid="stDialog"] div[data-testid="stElementContainer"]:has(.ips-user-actions-header-marker) [class*="st-key-ips_warn_s_"] [data-testid="stButton"] > button,
div[data-testid="stDialog"] div[data-testid="stElementContainer"]:has(.ips-user-actions-header-marker) [class*="st-key-ips_dng_s_"] [data-testid="stButton"] > button,
div[data-testid="stDialog"] div[data-testid="stElementContainer"]:has(.ips-asset-actions-header-marker) [class*="st-key-ips_succ_s_"] [data-testid="stButton"] > button,
div[data-testid="stDialog"] div[data-testid="stElementContainer"]:has(.ips-asset-actions-header-marker) [class*="st-key-ips_warn_s_"] [data-testid="stButton"] > button,
div[data-testid="stDialog"] div[data-testid="stElementContainer"]:has(.ips-asset-actions-header-marker) [class*="st-key-ips_dng_s_"] [data-testid="stButton"] > button,
div[data-testid="stDialog"] div[data-testid="stElementContainer"]:has(.ips-estimate-actions-marker) [class*="st-key-ips_succ_s_"] [data-testid="stButton"] > button,
div[data-testid="stDialog"] div[data-testid="stElementContainer"]:has(.ips-estimate-actions-marker) [class*="st-key-ips_warn_s_"] [data-testid="stButton"] > button,
div[data-testid="stDialog"] div[data-testid="stElementContainer"]:has(.ips-estimate-actions-marker) [class*="st-key-ips_dng_s_"] [data-testid="stButton"] > button,
div[data-testid="stDialog"] div[data-testid="stElementContainer"]:has(.ips-inventory-actions-marker) [class*="st-key-ips_succ_s_"] [data-testid="stButton"] > button,
div[data-testid="stDialog"] div[data-testid="stElementContainer"]:has(.ips-inventory-actions-marker) [class*="st-key-ips_warn_s_"] [data-testid="stButton"] > button,
div[data-testid="stDialog"] div[data-testid="stElementContainer"]:has(.ips-inventory-actions-marker) [class*="st-key-ips_dng_s_"] [data-testid="stButton"] > button,
div[data-testid="stDialog"] div[data-testid="stElementContainer"]:has(.ips-asset-actions-marker) [class*="st-key-ips_succ_s_"] [data-testid="stButton"] > button,
div[data-testid="stDialog"] div[data-testid="stElementContainer"]:has(.ips-asset-actions-marker) [class*="st-key-ips_warn_s_"] [data-testid="stButton"] > button,
div[data-testid="stDialog"] div[data-testid="stElementContainer"]:has(.ips-asset-actions-marker) [class*="st-key-ips_dng_s_"] [data-testid="stButton"] > button,
div[data-testid="stDialog"] div[data-testid="stElementContainer"]:has(.ips-catalog-presence-marker) [class*="st-key-ips_succ_s_"] [data-testid="stButton"] > button,
div[data-testid="stDialog"] div[data-testid="stElementContainer"]:has(.ips-catalog-presence-marker) [class*="st-key-ips_warn_s_"] [data-testid="stButton"] > button,
div[data-testid="stDialog"] div[data-testid="stElementContainer"]:has(.ips-catalog-presence-marker) [class*="st-key-ips_dng_s_"] [data-testid="stButton"] > button {
    width: auto !important;
    min-width: 0 !important;
    max-width: none !important;
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


def inject_global_button_css() -> None:
    """Single-line horizontal labels on every Streamlit and custom button app-wide."""
    st.markdown(
        """
<style id="ips-global-buttons-v2">
button,
.stButton > button,
[data-testid="stButton"] > button,
[data-testid="stBaseButton-secondary"],
[data-testid="stBaseButton-primary"],
[data-testid="stBaseButton-popover"],
[data-testid="baseButton-secondary"],
[data-testid="baseButton-primary"],
button[data-testid="baseButton-secondary"],
button[data-testid="baseButton-primary"],
button[data-testid="stBaseButton-popover"],
[data-testid="stFormSubmitButton"] > button,
[data-testid="stPopover"] > button,
.asset-actions-button,
.actions-button {
  white-space: nowrap !important;
  word-break: keep-all !important;
  overflow-wrap: normal !important;
  min-width: fit-content !important;
  width: auto !important;
  max-width: none !important;
  writing-mode: horizontal-tb !important;
  text-orientation: mixed !important;
  display: inline-flex !important;
  flex-direction: row !important;
  flex-wrap: nowrap !important;
  align-items: center !important;
  justify-content: center !important;
}
.stButton,
[data-testid="stButton"],
[data-testid="stPopover"],
[data-testid="stFormSubmitButton"] {
  width: auto !important;
  max-width: none !important;
  flex: 0 0 auto !important;
}
section[data-testid="stSidebar"] [class*="st-key-nav_"] .stButton,
section[data-testid="stSidebar"] [class*="st-key-nav_"] [data-testid="stButton"],
section[data-testid="stSidebar"] [class*="st-key-ips_logout"] .stButton,
section[data-testid="stSidebar"] [class*="st-key-ips_logout"] [data-testid="stButton"] {
  width: 100% !important;
  max-width: 100% !important;
  flex: 1 1 auto !important;
}
.stButton > button p,
.stButton > button span,
.stButton > button div,
[data-testid="stButton"] > button p,
[data-testid="stButton"] > button span,
[data-testid="stButton"] > button div,
button[data-testid="stBaseButton-popover"] p,
button[data-testid="stBaseButton-popover"] span,
button[data-testid="stBaseButton-popover"] div,
[data-testid="stPopover"] > button p,
[data-testid="stPopover"] > button span,
[data-testid="stFormSubmitButton"] > button p,
[data-testid="stFormSubmitButton"] > button span,
.asset-actions-button p,
.asset-actions-button span,
.actions-button p,
.actions-button span {
  white-space: nowrap !important;
  word-break: keep-all !important;
  overflow-wrap: normal !important;
  writing-mode: horizontal-tb !important;
  display: inline !important;
  width: auto !important;
  max-width: none !important;
}
button[data-testid="stBaseButton-popover"],
[data-testid="stPopover"] > button {
  min-width: max(4.75rem, fit-content) !important;
  padding-left: 0.8rem !important;
  padding-right: 0.8rem !important;
}
[data-testid="stNumberInputStepDown"] button,
[data-testid="stNumberInputStepUp"] button,
[data-testid="stNumberInput"] [data-testid="stNumberInputStepDown"] button,
[data-testid="stNumberInput"] [data-testid="stNumberInputStepUp"] button {
  min-width: 0 !important;
  width: 100% !important;
  max-width: none !important;
  padding-left: 0 !important;
  padding-right: 0 !important;
}
.asset-name-button [data-testid="stButton"] > button,
.ips-nav-name-button [data-testid="stButton"] > button,
.ips-assets-link-btn.asset-name-button [data-testid="stButton"] > button,
.ips-assets-link-btn.ips-nav-name-button [data-testid="stButton"] > button {
  background: #4361EE !important;
  color: #FFFFFF !important;
  font-weight: 700 !important;
  border: none !important;
  border-radius: 8px !important;
  padding: 0 16px !important;
  height: 38px !important;
  min-height: 38px !important;
  max-height: 38px !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  max-width: 500px !important;
  min-width: 0 !important;
  width: 100% !important;
  cursor: pointer !important;
  transition: background 0.2s ease, color 0.2s ease, box-shadow 0.2s ease !important;
  box-shadow: none !important;
  word-break: normal !important;
  overflow-wrap: normal !important;
  writing-mode: horizontal-tb !important;
}
.asset-name-button [data-testid="stButton"] > button:hover,
.asset-name-button [data-testid="stButton"] > button:focus,
.ips-nav-name-button [data-testid="stButton"] > button:hover,
.ips-nav-name-button [data-testid="stButton"] > button:focus,
.ips-assets-link-btn.asset-name-button [data-testid="stButton"] > button:hover,
.ips-assets-link-btn.ips-nav-name-button [data-testid="stButton"] > button:hover {
  background: #3651D4 !important;
  color: #FFFFFF !important;
  border: none !important;
  box-shadow: none !important;
}
.asset-name-button [data-testid="stButton"] > button p,
.asset-name-button [data-testid="stButton"] > button span,
.asset-name-button [data-testid="stButton"] > button div,
.ips-nav-name-button [data-testid="stButton"] > button p,
.ips-nav-name-button [data-testid="stButton"] > button span,
.ips-nav-name-button [data-testid="stButton"] > button div {
  color: #FFFFFF !important;
  font-weight: 700 !important;
  display: inline !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  max-width: 100% !important;
  width: auto !important;
  word-break: normal !important;
  overflow-wrap: normal !important;
}
.st-key-assets_table_wrap .asset-name-button [data-testid="stButton"] > button,
.st-key-assets_table_wrap .ips-assets-name-link [data-testid="stButton"] > button,
.st-key-assets_table_wrap .asset-name-link [data-testid="stButton"] > button {
  background: transparent !important;
  background-color: transparent !important;
  color: #2563eb !important;
  font-weight: 600 !important;
  border: none !important;
  border-radius: 0 !important;
  padding: 0 !important;
  height: auto !important;
  min-height: 0 !important;
  max-height: none !important;
  justify-content: flex-start !important;
  max-width: 100% !important;
  width: auto !important;
  box-shadow: none !important;
  transition: color 0.15s ease !important;
}
.st-key-assets_table_wrap .asset-name-button [data-testid="stButton"] > button:hover,
.st-key-assets_table_wrap .asset-name-button [data-testid="stButton"] > button:focus,
.st-key-assets_table_wrap .ips-assets-name-link [data-testid="stButton"] > button:hover,
.st-key-assets_table_wrap .asset-name-link [data-testid="stButton"] > button:hover {
  background: transparent !important;
  color: #1d4ed8 !important;
  text-decoration: underline !important;
}
.st-key-assets_table_wrap .asset-name-button [data-testid="stButton"] > button p,
.st-key-assets_table_wrap .asset-name-button [data-testid="stButton"] > button span,
.st-key-assets_table_wrap .asset-name-button [data-testid="stButton"] > button div,
.st-key-assets_table_wrap .ips-assets-name-link [data-testid="stButton"] > button p,
.st-key-assets_table_wrap .ips-assets-name-link [data-testid="stButton"] > button span,
.st-key-assets_table_wrap .asset-name-link [data-testid="stButton"] > button p,
.st-key-assets_table_wrap .asset-name-link [data-testid="stButton"] > button span {
  color: inherit !important;
  font-weight: 600 !important;
  text-align: left !important;
}
section[data-testid="stSidebar"] [class*="st-key-nav_"] button[data-testid="stBaseButton-secondary"],
section[data-testid="stSidebar"] [class*="st-key-nav_"] button[data-testid="stBaseButton-primary"],
section[data-testid="stSidebar"] [class*="st-key-nav_"] [data-testid="stBaseButton-secondary"],
section[data-testid="stSidebar"] [class*="st-key-nav_"] [data-testid="stBaseButton-primary"] {
  width: 100% !important;
  max-width: 100% !important;
  min-width: 0 !important;
  flex: 1 1 auto !important;
  display: flex !important;
  justify-content: flex-start !important;
  text-align: left !important;
}
section[data-testid="stSidebar"] [class*="st-key-nav_"] .stButton > button p,
section[data-testid="stSidebar"] [class*="st-key-nav_"] [data-testid="stButton"] > button p,
section[data-testid="stSidebar"] [class*="st-key-nav_"] button[data-testid="stBaseButton-secondary"] p,
section[data-testid="stSidebar"] [class*="st-key-nav_"] button[data-testid="stBaseButton-primary"] p {
  display: flex !important;
  width: 100% !important;
  justify-content: flex-start !important;
  text-align: left !important;
}
section[data-testid="stSidebar"] [class*="st-key-nav_"] .sidebar-nav-icon,
section[data-testid="stSidebar"] [class*="st-key-nav_"] .sidebar-nav-label {
  display: inline-flex !important;
  width: auto !important;
  max-width: none !important;
}
section[data-testid="stSidebar"] [class*="st-key-nav_"] .sidebar-nav-label {
  display: block !important;
  flex: 1 1 auto !important;
  text-align: left !important;
}
</style>
""",
        unsafe_allow_html=True,
    )


def inject_compact_table_rows_css() -> None:
    """Global compact row height and vertical centering for all list/data tables."""
    st.markdown(
        f"""
<style id="ips-compact-table-rows-v2">
/* ── Streamlit column-based list tables ── */
[class*="_table_wrap"]:not(.st-key-users_table_wrap) > [data-testid="stVerticalBlock"],
[class*="_table_wrap"]:not(.st-key-users_table_wrap) [data-testid="stVerticalBlock"]:first-child {{
  gap: 0 !important;
}}
[class*="_table_wrap"]:not(.st-key-users_table_wrap) > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"],
[class*="_table_wrap"]:not(.st-key-users_table_wrap) > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] > [data-testid="stHorizontalBlock"] {{
  display: flex !important;
  align-items: center !important;
  gap: 0.35rem !important;
  margin: 0 !important;
  box-sizing: border-box !important;
}}
[class*="_table_wrap"]:not(.st-key-users_table_wrap) > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type,
[class*="_table_wrap"]:not(.st-key-users_table_wrap) > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] > [data-testid="stHorizontalBlock"]:first-of-type {{
  min-height: 36px !important;
  height: auto !important;
  padding: 5px 10px !important;
  background: #f8fafc !important;
}}
[class*="_table_wrap"]:not(.st-key-users_table_wrap) > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:not(:first-of-type):not(:has(.ips-jobs-table-row)):not(:has(.timesheet-list-row-marker)):not(:has(.timekeeping-list-header-marker)):not(:has(.timekeeping-list-row-header-marker)):not(:has(.timekeeping-detail-row-marker)):not(:has(.timekeeping-detail-header-marker)):not(:has(.weekly-timesheet-row-marker)),
[class*="_table_wrap"]:not(.st-key-users_table_wrap) > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] > [data-testid="stHorizontalBlock"]:not(:first-of-type):not(:has(.ips-jobs-table-row)):not(:has(.timesheet-list-row-marker)):not(:has(.timekeeping-list-header-marker)):not(:has(.timekeeping-list-row-header-marker)):not(:has(.timekeeping-detail-row-marker)):not(:has(.timekeeping-detail-header-marker)):not(:has(.weekly-timesheet-row-marker)) {{
  min-height: 56px !important;
  height: auto !important;
  padding: 5px 10px !important;
}}
@media (min-width: 768px) and (max-width: 1024px) {{
  [class*="_table_wrap"]:not(.st-key-users_table_wrap) > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:not(:first-of-type):not(:has(.ips-jobs-table-row)):not(:has(.timesheet-list-row-marker)):not(:has(.timekeeping-list-header-marker)):not(:has(.timekeeping-list-row-header-marker)):not(:has(.timekeeping-detail-row-marker)):not(:has(.weekly-timesheet-row-marker)),
  [class*="_table_wrap"]:not(.st-key-users_table_wrap) > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] > [data-testid="stHorizontalBlock"]:not(:first-of-type):not(:has(.ips-jobs-table-row)):not(:has(.timesheet-list-row-marker)):not(:has(.timekeeping-list-header-marker)):not(:has(.timekeeping-list-row-header-marker)):not(:has(.timekeeping-detail-row-marker)):not(:has(.weekly-timesheet-row-marker)) {{
    min-height: 58px !important;
    padding: 6px 10px !important;
  }}
}}
[class*="_table_wrap"]:not(.st-key-users_table_wrap) [data-testid="stHorizontalBlock"] > [data-testid="column"] {{
  display: flex !important;
  align-items: center !important;
  align-self: stretch !important;
  min-height: 0 !important;
  height: auto !important;
}}
[class*="_table_wrap"]:not(.st-key-users_table_wrap) [data-testid="stHorizontalBlock"] > [data-testid="column"] > [data-testid="stVerticalBlock"],
[class*="_table_wrap"]:not(.st-key-users_table_wrap) [data-testid="stHorizontalBlock"] > [data-testid="column"] > [data-testid="stElementContainer"] {{
  display: flex !important;
  flex-direction: column !important;
  justify-content: center !important;
  align-items: stretch !important;
  width: 100% !important;
  height: 100% !important;
  min-height: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  gap: 0 !important;
}}
[class*="_table_wrap"]:not(.st-key-users_table_wrap) [data-testid="stElementContainer"] {{
  margin-top: 0 !important;
  margin-bottom: 0 !important;
  padding-top: 0 !important;
  padding-bottom: 0 !important;
}}
[class*="_table_wrap"]:not(.st-key-users_table_wrap) [data-testid="stCheckbox"] {{
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  margin: 0 !important;
}}
[class*="_table_wrap"]:not(.st-key-users_table_wrap) [data-testid="stCheckbox"] label {{
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  min-height: 0 !important;
  height: auto !important;
  margin: 0 !important;
  padding: 0 !important;
}}
[class*="_table_wrap"]:not(.st-key-users_table_wrap) [data-testid="stImage"],
[class*="_table_wrap"]:not(.st-key-users_table_wrap) [data-testid="stImage"] img {{
  margin: 0 !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
}}
[class*="_table_wrap"]:not(.st-key-users_table_wrap) .stButton > button,
[class*="_table_wrap"]:not(.st-key-users_table_wrap) button[data-testid="stBaseButton-secondary"],
[class*="_table_wrap"]:not(.st-key-users_table_wrap) button[data-testid="stBaseButton-primary"],
[class*="_table_wrap"]:not(.st-key-users_table_wrap) button[data-testid="stBaseButton-popover"] {{
  white-space: nowrap !important;
  word-break: keep-all !important;
  overflow-wrap: normal !important;
}}
[class*="_table_wrap"]:not(.st-key-users_table_wrap) [class*="-cell"],
[class*="_table_wrap"]:not(.st-key-users_table_wrap) .ips-data-cell,
[class*="_table_wrap"]:not(.st-key-users_table_wrap) .jobs-table-cell,
[class*="_table_wrap"]:not(.st-key-users_table_wrap) .job-cell {{
  display: flex !important;
  align-items: center !important;
  min-height: 0 !important;
  height: 100% !important;
}}
[class*="_table_wrap"]:not(.st-key-users_table_wrap) [class*="status-cell"],
[class*="_table_wrap"]:not(.st-key-users_table_wrap) [class*="actions-cell"],
[class*="_table_wrap"]:not(.st-key-users_table_wrap) [class*="checkbox-cell"],
[class*="_table_wrap"]:not(.st-key-users_table_wrap) [class*="thumb-cell"],
[class*="_table_wrap"]:not(.st-key-users_table_wrap) [class*="image-cell"],
[class*="_table_wrap"]:not(.st-key-users_table_wrap) [class*="-actcol"] {{
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
}}

/* ── HTML grid / stable data tables ── */
table tbody tr {{
  min-height: 56px;
}}
table td,
table th {{
  vertical-align: middle !important;
}}
.ips-data-table-stable .ips-data-table-header,
.ips-data-table-stable .ips-data-row,
.ips-data-table-header,
.ips-data-row {{
  align-items: center !important;
  min-height: 56px;
  padding: 5px 10px !important;
}}
.ips-data-table-stable .ips-data-table-header,
.ips-data-table-header {{
  min-height: 36px !important;
  padding: 5px 10px !important;
}}
.ips-data-cell,
.ips-clean-cell {{
  display: flex !important;
  align-items: center !important;
  min-height: 0 !important;
  height: 100% !important;
}}
.ips-clean-row,
.ips-table-row,
.ips-users-row,
.ips-customers-row,
.ips-estimates-row,
.ips-inventory-row,
.ips-assets-row,
.ips-timekeeping-row,
.ips-updates-row,
.ips-certifications-row,
.ips-contacts-row,
.ips-locations-row,
.ips-pg-row,
.ips-tasks-row,
.ips-est-list-row,
.usr-row {{
  min-height: 56px;
  display: grid;
  align-items: center;
}}
.ips-table-header-row,
.ips-users-header-row,
.ips-jobs-header-row,
.ips-customers-header-row,
.ips-estimates-header-row,
.ips-inventory-header-row,
.ips-assets-header-row,
.ips-timekeeping-header-row,
.ips-updates-header-row,
.ips-certifications-header-row,
.ips-contacts-header-row,
.ips-locations-header-row,
.ips-pg-header-row,
.ips-tasks-header-row {{
  min-height: 36px !important;
  padding: 5px 10px !important;
}}
.ips-table-row,
.ips-users-row,
.ips-customers-row,
.ips-estimates-row,
.ips-inventory-row,
.ips-assets-row,
.ips-timekeeping-row,
.ips-updates-row,
.ips-certifications-row,
.ips-contacts-row,
.ips-locations-row,
.ips-pg-row,
.ips-tasks-row {{
  min-height: 56px !important;
  padding: 5px 10px !important;
}}
.ips-documents-page .ips-data-table-html .ips-data-row {{
  min-height: 56px !important;
  padding: 5px 10px !important;
}}
@media (min-width: 768px) and (max-width: 1024px) {{
  .ips-data-table-stable .ips-data-row,
  .ips-data-row,
  .ips-table-row,
  .ips-users-row,
  .ips-customers-row,
  .ips-estimates-row,
  .ips-inventory-row,
  .ips-assets-row,
  .ips-timekeeping-row,
  .ips-updates-row,
  .ips-certifications-row,
  .ips-contacts-row,
  .ips-locations-row,
  .ips-pg-row,
  .ips-tasks-row {{
    min-height: 58px !important;
    padding: 6px 10px !important;
  }}
}}

/* Hidden row markers must not inflate row height */
[class*="_table_wrap"] .ips-jobs-table-row,
[class*="_table_wrap"] .ips-jobs-row-marker,
[class*="_table_wrap"] .job-row,
[class*="_table_wrap"] .jobs-table-row,
[class*="_table_wrap"] .ips-assets-equipment-table-row,
[class*="_table_wrap"] .ips-assets-row-marker,
[class*="_table_wrap"] .ips-users-checkbox-cell-marker,
[class*="_table_wrap"] .timesheet-list-row-marker,
[class*="_table_wrap"] .weekly-timesheet-row-marker,
[class*="_table_wrap"] .timekeeping-list-header-marker,
[class*="_table_wrap"] .timekeeping-list-row-header-marker {{
  min-height: 0 !important;
  max-height: 0 !important;
  height: 0 !important;
  padding: 0 !important;
  margin: 0 !important;
  overflow: hidden !important;
  border: none !important;
  background: transparent !important;
}}

/* Weekly timesheet horizontal grids */
.st-key-tk_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker),
.st-key-tk_page_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker) {{
  min-height: 56px !important;
  height: auto !important;
  align-items: center !important;
  padding: 5px 10px !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="stHorizontalBlock"]:has(.timesheet-list-row-marker) {{
  min-height: 58px !important;
  height: auto !important;
  max-height: none !important;
  padding: 6px 4px !important;
  align-items: center !important;
}}
@media (min-width: 768px) and (max-width: 1024px) {{
  .st-key-tk_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker),
  .st-key-tk_page_hgrid_wrap [data-testid="stHorizontalBlock"]:has(.weekly-timesheet-row-marker),
  .st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="stHorizontalBlock"]:has(.timesheet-list-row-marker) {{
    min-height: 58px !important;
    padding: 6px 10px !important;
  }}
}}
</style>
""",
        unsafe_allow_html=True,
    )


def inject_global_css() -> None:
    """Inject global IPS SaaS styles on every render."""
    st.markdown(
        f"""
<style id="ips-global-styles-v7">
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
section[data-testid="stMain"]:not(:has(.ips-login-page-marker)) .block-container {{
  max-width: 100% !important;
  padding-top: 0 !important;
  padding-left: 0 !important;
  padding-right: 0 !important;
  padding-bottom: 2rem !important;
}}
section[data-testid="stMain"]:has(.ips-login-page-marker) .block-container {{
  max-width: 100% !important;
  padding-top: 0 !important;
  padding-left: 0 !important;
  padding-right: 0 !important;
  padding-bottom: 2rem !important;
}}
section[data-testid="stMain"]:has(.ips-page-shell-marker) [data-testid="stVerticalBlock"] > div {{
  padding-left: 28px;
  padding-right: 28px;
}}
section[data-testid="stMain"]:has(.ips-page-shell-marker) [data-testid="stVerticalBlock"] {{
  gap: 0.4rem !important;
}}
section[data-testid="stMain"]:has(.ips-page-shell-marker) [data-testid="stElementContainer"] {{
  margin-bottom: 0.25rem !important;
}}
section[data-testid="stMain"]:has(.ips-page-shell-marker) [data-testid="stElementContainer"]:has(.ips-page-shell-marker),
section[data-testid="stMain"]:has(.ips-page-shell-marker) [data-testid="stElementContainer"]:has(.ips-main-header) {{
  padding-left: 0 !important;
  padding-right: 0 !important;
  background: {MAIN_HEADER_BG} !important;
  margin-bottom: 0 !important;
}}
section[data-testid="stMain"]:has(.ips-page-shell-marker) [data-testid="stElementContainer"]:has(.ips-page-actions-marker),
section[data-testid="stMain"]:has(.ips-page-shell-marker) [data-testid="stVerticalBlockBorderWrapper"]:has(.ips-filter-bar-marker) {{
  margin-bottom: 0 !important;
}}
section[data-testid="stMain"]:has(.ips-page-shell-marker) [data-testid="stElementContainer"]:has(.ips-page-actions-marker) {{
  margin-top: -0.15rem !important;
}}
section[data-testid="stMain"]:has(.ips-page-shell-marker) [data-testid="column"]:has(.ips-page-actions-marker) {{
  display: flex !important;
  flex-direction: column !important;
  align-items: flex-end !important;
  justify-content: flex-start !important;
}}
section[data-testid="stMain"]:has(.ips-page-shell-marker) [data-testid="column"]:has(.ips-page-actions-marker) [data-testid="stHorizontalBlock"] {{
  justify-content: flex-end !important;
  width: auto !important;
  max-width: 100% !important;
  flex-wrap: nowrap !important;
  gap: 0.55rem !important;
}}
section[data-testid="stMain"]:has(.ips-page-shell-marker) [data-testid="column"]:has(.ips-page-actions-marker) [data-testid="stHorizontalBlock"] > [data-testid="column"] {{
  flex: 0 0 auto !important;
  width: auto !important;
  min-width: 0 !important;
}}
section[data-testid="stMain"]:has(.ips-page-shell-marker) [data-testid="column"]:has(.ips-page-actions-marker) .stButton {{
  width: auto !important;
}}
section[data-testid="stMain"]:has(.ips-page-shell-marker) [data-testid="column"]:has(.ips-page-actions-marker) .stButton > button {{
  min-height: 38px !important;
  height: 38px !important;
  width: auto !important;
  min-width: fit-content !important;
  max-width: none !important;
  white-space: nowrap !important;
  padding-left: 0.95rem !important;
  padding-right: 0.95rem !important;
}}
section[data-testid="stMain"]:has(.ips-page-shell-marker) [data-testid="column"]:has(.ips-page-actions-marker) .stButton > button p,
section[data-testid="stMain"]:has(.ips-page-shell-marker) [data-testid="column"]:has(.ips-page-actions-marker) [data-testid="stButton"] > button p {{
  white-space: nowrap !important;
}}
section[data-testid="stMain"]:has(.ips-page-shell-marker) [data-testid="column"]:has(.ips-main-header-actions-marker) {{
  display: flex !important;
  align-items: center !important;
  justify-content: flex-end !important;
  gap: 12px !important;
}}
section[data-testid="stMain"]:has(.ips-page-shell-marker) [data-testid="column"]:has(.ips-main-header-actions-marker) [data-testid="stHorizontalBlock"] {{
  justify-content: flex-end !important;
  gap: 12px !important;
}}

/* Reclaim Streamlit default top chrome (Deploy bar, menu, decoration) */
header[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
#MainMenu,
footer {{
  visibility: hidden !important;
  height: 0 !important;
  min-height: 0 !important;
  max-height: 0 !important;
  overflow: hidden !important;
  padding: 0 !important;
  margin: 0 !important;
  border: none !important;
}}
[data-testid="stAppViewContainer"] > section.main > div {{
  padding-top: 0 !important;
}}
[data-testid="stAppViewContainer"] {{
  padding-top: 0 !important;
}}
section[data-testid="stMain"] [data-testid="stMainBlockContainer"] {{
  padding-top: 0 !important;
  margin-top: 0 !important;
}}
/* CSS/script injections are flex rows with zero height but still consume vertical gap */
section[data-testid="stMain"] [data-testid="stElementContainer"]:has(style):not(:has(.ips-desktop-nav-rail)),
section[data-testid="stMain"] [data-testid="stElementContainer"]:has(script):not(:has(.ips-desktop-nav-rail)) {{
  display: none !important;
  height: 0 !important;
  min-height: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  overflow: hidden !important;
}}
section[data-testid="stMain"] [data-testid="stElementContainer"]:has(.ips-main-header) {{
  margin-top: 0 !important;
}}

/* Sidebar */
section[data-testid="stSidebar"],
[data-testid="stSidebar"] {{
  background: {SIDEBAR_BG} !important;
  border-right: 1px solid {BORDER} !important;
}}
section[data-testid="stSidebar"] .block-container {{
  padding: 0.35rem 0.3rem 0.5rem !important;
  max-width: 100% !important;
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
  padding: 16px;
  margin-bottom: 0.5rem;
  box-shadow: 0 1px 2px rgba(15,23,42,0.04);
}}
.ips-metric-card {{
  background: {CARD_BG};
  border: 1px solid {BORDER};
  border-radius: 12px;
  padding: 14px 16px;
  min-height: 86px;
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

/* Page header — light-gray brand bar + title row */
.ips-page-shell-marker {{
  display: none !important;
  height: 0 !important;
  width: 0 !important;
  overflow: hidden !important;
  margin: 0 !important;
  padding: 0 !important;
}}
.ips-main-header {{
  background: {MAIN_HEADER_BG};
  border-bottom: 1px solid #cfd8e3;
  padding: 8px 28px;
  min-height: 58px;
  max-height: 68px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  width: 100%;
  box-sizing: border-box;
}}
.ips-main-header-brand {{
  display: flex;
  align-items: center;
  min-width: 0;
  flex: 1 1 auto;
}}
.ips-main-header-menu {{
  display: none;
  align-items: center;
  flex: 0 0 auto;
  margin-right: 0.65rem;
}}
@media (max-width: 899px) {{
  .ips-main-header-menu {{
    display: flex;
  }}
}}
.ips-main-header-logo {{
  height: 40px;
  width: auto;
  max-width: 420px;
  object-fit: contain;
  display: block;
  background: transparent;
}}
.ips-main-header-logo-fallback {{
  font-size: 1.05rem;
  font-weight: 800;
  color: #0f172a;
  letter-spacing: -0.02em;
}}
.ips-main-header-actions,
.ips-main-header-actions-slot {{
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 0 0 auto;
}}
.ips-page-content {{
  padding: 18px 28px 28px 28px;
}}
.ips-page-header {{
  margin: 0 0 14px 0;
}}
.ips-page-header-bar {{
  display: none !important;
}}
.ips-page-title-row {{
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 4px;
}}
.ips-page-title-block {{
  min-width: 0;
}}
.ips-page-header-logo-wrap {{
  display: none !important;
}}
.ips-page-header-text {{
  flex: 1 1 auto;
  min-width: 0;
}}
.ips-page-title {{
  margin: 0;
  font-size: 34px;
  line-height: 1.08;
  font-weight: 850;
  color: #0f172a;
  letter-spacing: -0.02em;
}}
.ips-page-subtitle {{
  margin-top: 6px;
  margin-bottom: 0;
  font-size: 15px;
  color: #64748b;
  line-height: 1.35;
}}
.ips-page-actions {{
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
  padding-top: 2px;
}}
@media (max-width: 900px) {{
  .ips-main-header {{
    min-height: 54px;
    padding: 8px 14px;
  }}
  .ips-main-header-logo {{
    height: 34px;
    max-width: 90%;
  }}
  .ips-page-content {{
    padding: 14px 14px 24px 14px;
  }}
  section[data-testid="stMain"]:has(.ips-page-shell-marker) [data-testid="stVerticalBlock"] > div {{
    padding-left: 14px;
    padding-right: 14px;
  }}
  .ips-page-title-row {{
    flex-direction: column;
    gap: 10px;
  }}
  .ips-page-title {{
    font-size: 28px;
  }}
  .ips-page-actions {{
    width: 100%;
    justify-content: flex-start;
  }}
}}

/* Filter bar */
.ips-filter-bar-marker {{
  display: none !important;
}}
section[data-testid="stMain"]:has(.ips-page-shell-marker) [data-testid="stVerticalBlockBorderWrapper"]:has(.ips-filter-bar-marker) {{
  margin: 12px 0 18px 0 !important;
  background: #ffffff !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: 12px !important;
  padding: 8px 10px !important;
}}
section[data-testid="stMain"]:has(.ips-filter-bar-marker) [data-testid="stTextInput"],
section[data-testid="stMain"]:has(.ips-filter-bar-marker) [data-testid="stSelectbox"],
section[data-testid="stMain"]:has(.ips-filter-bar-marker) [data-testid="stDateInput"],
section[data-testid="stMain"]:has(.ips-filter-bar-marker) [data-testid="stMultiSelect"] {{
  margin-bottom: 0 !important;
}}
section[data-testid="stMain"]:has(.ips-filter-bar-marker) [data-testid="stTextInput"] input,
section[data-testid="stMain"]:has(.ips-filter-bar-marker) [data-testid="stDateInput"] input,
section[data-testid="stMain"]:has(.ips-filter-bar-marker) [data-testid="stSelectbox"] [data-baseweb="select"] > div {{
  min-height: 40px !important;
}}
.ips-filter-bar {{
  background: {CARD_BG};
  border: 1px solid {BORDER};
  border-radius: 12px;
  padding: 0.55rem 0.65rem;
  margin: 12px 0 18px 0;
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
  padding: 5px 10px;
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
  padding: 5px 10px;
  font-size: 0.8125rem;
  min-height: 56px;
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
  border-radius: 10px !important;
  font-size: 0.8125rem !important;
  font-weight: 700 !important;
  min-height: 38px !important;
  height: 38px !important;
  padding: 0 14px !important;
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
  border-radius: 10px !important;
  border-color: {BORDER} !important;
  font-size: 0.8125rem !important;
}}
section[data-testid="stMain"] [data-testid="stTextInput"] input,
section[data-testid="stMain"] [data-testid="stNumberInput"] input,
section[data-testid="stMain"] [data-testid="stDateInput"] input {{
  min-height: 40px !important;
}}
section[data-testid="stMain"] [data-testid="stTextArea"] textarea {{
  min-height: 90px !important;
}}
section[data-testid="stMain"] [data-baseweb="select"] > div {{
  min-height: 40px !important;
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

/* Login — centered narrow panel (see inject_unauthenticated_shell_css for full rules) */
body.ips-auth-login section[data-testid="stMain"]:has(.ips-login-page-marker) [data-testid="column"]:has(.ips-login-center-marker) {{
  max-width: min(480px, calc(100vw - 2rem)) !important;
  margin-left: auto !important;
  margin-right: auto !important;
}}
body.ips-auth-login .st-key-ips_login_card,
body.ips-auth-login [data-testid="stVerticalBlockBorderWrapper"].st-key-ips_login_card {{
  max-width: min(480px, 100%) !important;
  margin-left: auto !important;
  margin-right: auto !important;
}}

/* Module list pages (Customers, Jobs, …) */
.ips-module-page {{
  width: 100%;
}}
.ips-module-page .ips-page-header,
.ips-module-page .ips-page-header-bar {{
  margin-bottom: 0.35rem;
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
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.55rem;
  margin-top: 12px;
  margin-bottom: 0.5rem;
}}
.ips-kpi-grid-jobs {{
  margin-top: 0.35rem;
}}
.ips-dashboard-metrics,
.ips-metric-grid {{
  margin-top: 12px;
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
  padding: 14px 16px;
  min-height: 86px;
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
  padding: 0.65rem 0.75rem;
  margin-bottom: 0.5rem;
  min-height: 9rem;
}}
.ips-panel-card-compact {{
  min-height: 0;
  height: auto;
  padding-bottom: 0.55rem;
}}
.ips-panel-card-compact .ips-panel-title {{
  margin-bottom: 0.15rem;
  padding-bottom: 0;
  border-bottom: none;
}}
.ips-panel-card-compact .ips-panel-subtitle {{
  margin: 0 0 0.45rem;
  padding-bottom: 0.4rem;
  border-bottom: 1px solid #e2e8f0;
}}
.ips-panel-subtitle {{
  margin: 0 0 0.45rem;
  font-size: 0.72rem;
  font-weight: 500;
  color: {TEXT_MUTED};
  line-height: 1.35;
}}
.ips-panel-card-compact .ips-qr-scan-dash-table {{
  margin-top: 0;
  border: none;
  border-radius: 0;
  overflow-x: auto;
}}
.ips-panel-card-compact .ips-dash-list-table {{
  margin-top: 0;
  border: none;
  box-shadow: none;
}}
.ips-panel-card-compact .ips-dash-list-table .ips-data-table-header,
.ips-panel-card-compact .ips-dash-list-table .ips-clean-row {{
  padding: 0.35rem 0;
  min-height: 0 !important;
}}
.ips-panel-card-compact .ips-dash-list-table .ips-data-table-header {{
  font-size: 0.68rem;
  font-weight: 800;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  border-bottom: 1px solid #e2e8f0;
}}
.ips-panel-card-compact .ips-dash-list-table .ips-clean-row {{
  font-size: 0.8125rem;
  border-bottom: 1px solid #f1f5f9;
}}
.ips-panel-card-compact .ips-dash-list-table .ips-clean-row:last-child {{
  border-bottom: none;
}}
.ips-dash-job-number {{
  color: #2563eb;
  font-weight: 600;
  white-space: nowrap;
}}
.ips-panel-empty {{
  margin: 0.15rem 0 0;
  font-size: 0.8rem;
  color: {TEXT_MUTED};
}}
.ips-dash-updates-feed {{
  display: flex;
  flex-direction: column;
  gap: 0;
}}
.ips-dash-update-item {{
  display: flex;
  gap: 0.55rem;
  padding: 0.5rem 0;
  border-bottom: 1px solid #f1f5f9;
}}
.ips-dash-update-item:last-child {{
  border-bottom: none;
  padding-bottom: 0;
}}
.ips-dash-update-icon {{
  width: 1.75rem;
  height: 1.75rem;
  border-radius: 8px;
  background: #eff6ff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.9rem;
  flex-shrink: 0;
}}
.ips-dash-update-head {{
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 0.35rem 0.5rem;
}}
.ips-dash-update-title {{
  font-size: 0.8125rem;
  font-weight: 700;
  color: {TEXT};
  flex: 1 1 auto;
}}
.ips-dash-update-date {{
  font-size: 0.72rem;
  color: {TEXT_MUTED};
  white-space: nowrap;
}}
.ips-dash-update-pinned {{
  font-size: 0.62rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #1d4ed8;
  background: #dbeafe;
  border-radius: 999px;
  padding: 0.08rem 0.4rem;
}}
.ips-dash-update-meta {{
  font-size: 0.7rem;
  color: {TEXT_MUTED};
  margin-top: 0.12rem;
}}
.ips-dash-update-body {{
  margin: 0.2rem 0 0;
  font-size: 0.75rem;
  color: #475569;
  line-height: 1.35;
}}
.st-key-dashboard_company_updates {{
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
  padding: 1.1rem 1.25rem 1.2rem;
  margin: 0 0 1.15rem;
}}
.st-key-dashboard_company_updates [data-testid="stHorizontalBlock"]:first-of-type {{
  margin-bottom: 0.65rem;
  padding-bottom: 0.65rem;
  border-bottom: 1px solid #f1f5f9;
}}
.ips-dash-cu-hero-title {{
  margin: 0;
  font-size: 1.15rem;
  font-weight: 800;
  color: {TEXT};
  letter-spacing: -0.01em;
}}
.ips-dash-cu-hero-subtitle {{
  margin: 0.2rem 0 0;
  font-size: 0.82rem;
  color: {TEXT_MUTED};
  line-height: 1.4;
}}
.ips-dash-cu-body {{
  display: flex;
  flex-direction: column;
  gap: 1rem;
}}
.ips-dash-cu-featured {{
  display: flex;
  gap: 1rem;
  align-items: flex-start;
  background: linear-gradient(135deg, #eff6ff 0%, #f8fafc 58%);
  border: 1px solid #dbeafe;
  border-left: 4px solid #2563eb;
  border-radius: 12px;
  padding: 1.1rem 1.15rem;
}}
.ips-dash-cu-featured-icon {{
  width: 2.75rem;
  height: 2.75rem;
  border-radius: 12px;
  background: #ffffff;
  border: 1px solid #dbeafe;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.35rem;
  flex-shrink: 0;
}}
.ips-dash-cu-featured-content {{
  flex: 1 1 auto;
  min-width: 0;
}}
.ips-dash-cu-featured-head {{
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.45rem 0.65rem;
}}
.ips-dash-cu-featured-title {{
  margin: 0;
  font-size: 1.2rem;
  font-weight: 800;
  color: {TEXT};
  line-height: 1.25;
}}
.ips-dash-cu-featured-badge {{
  font-size: 0.65rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #1d4ed8;
  background: #dbeafe;
  border-radius: 999px;
  padding: 0.12rem 0.5rem;
}}
.ips-dash-cu-featured-body {{
  margin: 0.55rem 0 0;
  font-size: 0.92rem;
  color: #334155;
  line-height: 1.5;
}}
.ips-dash-cu-featured-meta {{
  margin: 0.65rem 0 0;
  font-size: 0.78rem;
  color: {TEXT_MUTED};
}}
.ips-dash-cu-recent-heading {{
  margin: 0 0 0.45rem;
  font-size: 0.82rem;
  font-weight: 700;
  color: {TEXT};
}}
.ips-dash-cu-recent-list {{
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}}
.ips-dash-cu-recent-item {{
  display: flex;
  align-items: baseline;
  gap: 0.45rem;
  font-size: 0.84rem;
  color: #334155;
}}
.ips-dash-cu-recent-bullet {{
  color: #2563eb;
  font-weight: 700;
}}
.ips-dash-cu-recent-name {{
  font-weight: 600;
}}
.ips-dash-cu-empty {{
  margin: 0.35rem 0 0;
  font-size: 0.85rem;
  color: {TEXT_MUTED};
}}
.ips-ct-unread-badge {{
  display: inline-block;
  margin-left: 0.45rem;
  font-size: 0.68rem;
  font-weight: 700;
  color: #1d4ed8;
  background: #dbeafe;
  border-radius: 999px;
  padding: 0.1rem 0.45rem;
  vertical-align: middle;
}}
.ips-ct-feed-stack {{
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}}
.st-key-dashboard_company_updates .ips-ct-feed-card-wrap {{
  margin: 0.15rem 0 0.35rem;
}}
.ips-ct-feed-card {{
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 0.95rem 1rem 0.85rem;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}}
.ips-ct-feed-card-unread {{
  border-color: #bfdbfe;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 42%);
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.08);
}}
.ips-ct-feed-card-read {{
  opacity: 0.96;
}}
.ips-ct-feed-card-pinned {{
  border-left: 3px solid #2563eb;
}}
.ips-ct-feed-card-urgent {{
  border-left: 3px solid #dc2626;
  background: linear-gradient(180deg, #fff5f5 0%, #ffffff 48%);
}}
.ips-ct-feed-head {{
  display: flex;
  align-items: center;
  gap: 0.65rem;
  margin-bottom: 0.55rem;
}}
.ips-ct-avatar {{
  width: 2.35rem;
  height: 2.35rem;
  border-radius: 999px;
  background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
  color: #ffffff;
  font-size: 0.72rem;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  letter-spacing: 0.02em;
}}
.ips-ct-head-text {{
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.08rem;
}}
.ips-ct-author {{
  font-size: 0.84rem;
  font-weight: 700;
  color: {TEXT};
}}
.ips-ct-meta {{
  font-size: 0.72rem;
  color: {TEXT_MUTED};
}}
.ips-ct-status {{
  font-size: 0.68rem;
  font-weight: 700;
  flex-shrink: 0;
}}
.ips-ct-status-new {{
  color: #1d4ed8;
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
}}
.ips-ct-status-new .dot {{
  width: 0.42rem;
  height: 0.42rem;
  border-radius: 999px;
  background: #2563eb;
}}
.ips-ct-status-read {{
  color: #64748b;
}}
.ips-ct-title {{
  margin: 0 0 0.35rem;
  font-size: 0.98rem;
  font-weight: 800;
  color: {TEXT};
  line-height: 1.3;
}}
.ips-ct-body {{
  margin: 0;
  font-size: 0.82rem;
  color: #475569;
  line-height: 1.45;
}}
.ips-ct-foot {{
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-top: 0.65rem;
  padding-top: 0.55rem;
  border-top: 1px solid #f1f5f9;
}}
.ips-ct-cat-pill {{
  font-size: 0.65rem;
  font-weight: 700;
  border-radius: 999px;
  padding: 0.12rem 0.5rem;
}}
.ips-ct-pin {{
  font-size: 0.68rem;
  font-weight: 600;
  color: #64748b;
}}
.ips-ct-feed-hint {{
  font-size: 0.72rem;
  color: {TEXT_MUTED};
  line-height: 2.2;
}}
.st-key-dashboard_company_updates [data-testid="stHorizontalBlock"]:not(:first-of-type):not(:has(.stButton)) {{
  margin-top: -0.15rem;
  margin-bottom: 0.75rem;
}}
.st-key-dashboard_company_updates [data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ops-news-item-marker) [data-testid="stHorizontalBlock"] {{
  margin-top: 0 !important;
  margin-bottom: 0 !important;
}}
@media (max-width: 768px) {{
  .st-key-dashboard_company_updates {{
    padding: 0.95rem 0.9rem 1rem;
  }}
  .ips-dash-cu-featured {{
    flex-direction: column;
    gap: 0.75rem;
  }}
  .ips-dash-cu-featured-title {{
    font-size: 1.05rem;
  }}
}}
.ips-panel-title {{
  font-size: 0.9rem;
  font-weight: 700;
  color: {TEXT};
  margin: 0 0 0.45rem;
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

.st-key-dashboard_management_reminders {{
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
  padding: 1.1rem 1.25rem 1.15rem;
  margin: 0 0 1.15rem;
}}
.st-key-dashboard_management_reminders [data-testid="stHorizontalBlock"]:first-of-type {{
  margin-bottom: 0.65rem;
  padding-bottom: 0.65rem;
  border-bottom: 1px solid #f1f5f9;
}}
.ips-dash-mr-title-bar {{
  margin: 0;
  font-size: 1.05rem;
  font-weight: 800;
  color: {TEXT};
  letter-spacing: -0.01em;
}}
.ips-dash-mr-subtitle {{
  margin: 0.2rem 0 0;
  font-size: 0.82rem;
  color: {TEXT_MUTED};
  line-height: 1.4;
}}
.ips-dash-mr-empty {{
  margin: 0.35rem 0 0;
  font-size: 0.8125rem;
  color: {TEXT_MUTED};
}}
.ips-dash-mr-item-title {{
  margin: 0;
  font-size: 0.875rem;
  font-weight: 650;
  color: {TEXT};
  line-height: 1.35;
}}
.ips-dash-mr-item-meta {{
  margin: 0.12rem 0 0;
  font-size: 0.72rem;
  color: {TEXT_MUTED};
}}
.ips-dash-mr-item-text {{
  min-width: 0;
}}

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
  padding: 10px 12px 12px 12px !important;
  margin-bottom: 0.5rem !important;
}}
.st-key-dashboard_quick_actions [data-testid="stVerticalBlock"] {{
  gap: 8px !important;
}}
.st-key-dashboard_quick_actions .ips-quick-actions-header {{
  margin: 0 !important;
  padding: 0 0 4px 0 !important;
}}
.st-key-dashboard_quick_actions .ips-quick-actions-title {{
  margin: 0 !important;
  font-size: 0.9rem !important;
}}
.st-key-dashboard_quick_actions .stButton > button {{
  min-height: 46px !important;
  height: auto !important;
  padding: 8px 10px !important;
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
.ips-report-source {{
  font-size: 0.68rem;
  font-weight: 700;
  padding: 0.12rem 0.45rem;
  border-radius: 4px;
  margin-left: 0.45rem;
  vertical-align: middle;
  display: inline-block;
}}
.ips-report-source-live {{
  color: #166534;
  background: #dcfce7;
}}
.ips-report-source-sample {{
  color: #92400e;
  background: #fef3c7;
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

/* Page shell marker — hidden; used for :has() layout scoping only */
.ips-page-content-marker {{
  display: none !important;
  height: 0 !important;
  width: 0 !important;
  overflow: hidden !important;
  margin: 0 !important;
  padding: 0 !important;
}}
section[data-testid="stMain"]:has(.ips-page-content-marker) [data-testid="stMainBlockContainer"],
section[data-testid="stMain"]:has(.ips-page-content-marker) .block-container {{
  max-width: 100% !important;
  width: 100% !important;
}}
section[data-testid="stMain"]:has(.ips-page-content-marker) [data-testid="stElementContainer"] {{
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

/* Sidebar — modern ERP navigation (layout width in sidebar_shell.py) */
section[data-testid="stSidebar"] {{
  background: #ffffff !important;
  border-right: 1px solid {BORDER} !important;
  z-index: 99995 !important;
}}
section[data-testid="stSidebar"] > div {{
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  max-height: 100dvh;
  background: #ffffff !important;
}}
.sidebar-header {{
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 0.35rem 0.45rem 0.25rem;
  min-height: 150px;
}}
.sidebar-header--collapsed-rail {{
  min-height: 56px;
  height: 56px;
  max-height: 56px;
  padding: 0;
  margin: 0;
  overflow: hidden;
  background: transparent;
  border: none;
  box-shadow: none;
}}
.sidebar-header--collapsed-rail .sidebar-logo-wrap--collapsed {{
  width: 100%;
  height: 56px;
  min-height: 56px;
  max-height: 56px;
  padding: 0;
  margin: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}}
.sidebar-logo-icon {{
  width: 28px;
  height: 28px;
  min-width: 28px;
  min-height: 28px;
  max-width: 28px;
  max-height: 28px;
  object-fit: contain;
  display: block;
  margin: 0 auto;
  padding: 0;
}}
.sidebar-logo-icon-fallback {{
  font-size: 0.62rem;
  font-weight: 800;
  color: #2563eb;
  letter-spacing: 0.04em;
  line-height: 1;
}}
body.ips-sidebar-collapsed section[data-testid="stSidebar"]:not(:hover) .st-key-sidebar_expanded_header_wrap,
body.ips-sidebar-collapsed section[data-testid="stSidebar"]:not(:hover) [data-testid="stVerticalBlock"].st-key-sidebar_expanded_header_wrap,
body.ips-sidebar-collapsed section[data-testid="stSidebar"]:not(:hover) [data-testid="stHorizontalBlock"]:has(.sidebar-header-brand-marker),
body.ips-sidebar-collapsed section[data-testid="stSidebar"]:not(:hover) [data-testid="stElementContainer"]:has(.sidebar-header-expanded-rail-marker),
body.ips-sidebar-collapsed section[data-testid="stSidebar"]:not(:hover) [data-testid="stElementContainer"]:has(.sidebar-header-brand-marker),
body.ips-sidebar-collapsed section[data-testid="stSidebar"]:not(:hover) [data-testid="stElementContainer"]:has(.sidebar-logo-wrap--expanded),
body.ips-sidebar-collapsed section[data-testid="stSidebar"]:not(:hover) [data-testid="stElementContainer"]:has(.sidebar-divider--expanded-rail),
body.ips-sidebar-collapsed section[data-testid="stSidebar"]:not(:hover) [class*="st-key-ips_sidebar_collapse_toggle"],
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):not(:hover) .st-key-sidebar_expanded_header_wrap,
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):not(:hover) [data-testid="stVerticalBlock"].st-key-sidebar_expanded_header_wrap,
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):not(:hover) [data-testid="stHorizontalBlock"]:has(.sidebar-header-brand-marker),
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):not(:hover) [data-testid="stElementContainer"]:has(.sidebar-header-expanded-rail-marker),
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):not(:hover) [data-testid="stElementContainer"]:has(.sidebar-header-brand-marker),
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):not(:hover) [data-testid="stElementContainer"]:has(.sidebar-logo-wrap--expanded),
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):not(:hover) [data-testid="stElementContainer"]:has(.sidebar-divider--expanded-rail),
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):not(:hover) [class*="st-key-ips_sidebar_collapse_toggle"] {{
  display: none !important;
  height: 0 !important;
  min-height: 0 !important;
  max-height: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  overflow: hidden !important;
  visibility: hidden !important;
  border: none !important;
}}
body.ips-sidebar-collapsed section[data-testid="stSidebar"]:not(:hover) .sidebar-section-title,
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):not(:hover) .sidebar-section-title {{
  display: none !important;
  height: 0 !important;
  min-height: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  overflow: hidden !important;
}}
body.ips-sidebar-collapsed section[data-testid="stSidebar"]:not(:hover) [class*="st-key-nav_"] .stButton > button,
body.ips-sidebar-collapsed section[data-testid="stSidebar"]:not(:hover) [class*="st-key-nav_"] [data-testid="stButton"] > button,
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):not(:hover) [class*="st-key-nav_"] .stButton > button,
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):not(:hover) [class*="st-key-nav_"] [data-testid="stButton"] > button {{
  padding: 0 !important;
  overflow: visible !important;
}}
body.ips-sidebar-collapsed section[data-testid="stSidebar"]:not(:hover) [class*="st-key-nav_"] .sidebar-nav-icon,
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):not(:hover) [class*="st-key-nav_"] .sidebar-nav-icon {{
  display: inline-flex !important;
  opacity: 1 !important;
  visibility: visible !important;
}}
body.ips-sidebar-collapsed section[data-testid="stSidebar"]:not(:hover) [data-testid="stElementContainer"]:has(.sidebar-header--collapsed-rail),
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):not(:hover) [data-testid="stElementContainer"]:has(.sidebar-header--collapsed-rail) {{
  margin: 0 !important;
  padding: 0 !important;
  min-height: 0 !important;
  height: 56px !important;
  max-height: 56px !important;
  overflow: hidden !important;
}}
body.ips-sidebar-collapsed section[data-testid="stSidebar"]:hover .sidebar-header--collapsed-rail,
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):hover .sidebar-header--collapsed-rail,
body.ips-sidebar-collapsed section[data-testid="stSidebar"]:hover [data-testid="stElementContainer"]:has(.sidebar-header--collapsed-rail),
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):hover [data-testid="stElementContainer"]:has(.sidebar-header--collapsed-rail) {{
  display: none !important;
  height: 0 !important;
  min-height: 0 !important;
  max-height: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  overflow: hidden !important;
}}
.sidebar-header--collapsed {{
  min-height: 0;
  padding: 0;
}}
.sidebar-header-brand {{
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0;
  padding-right: 0;
  min-width: 0;
  width: 100%;
  text-align: center;
}}
.sidebar-header--collapsed .sidebar-header-brand {{
  align-items: center;
  padding-right: 0;
  padding-top: 0;
}}
.sidebar-logo-wrap,
.ips-sidebar-logo-wrap,
.sidebar-logo-wrap--collapsed {{
  flex: 0 0 auto;
  min-width: 0;
  padding: 0;
  margin: 0;
  border: none;
  background: transparent !important;
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
}}
.sidebar-header--collapsed .sidebar-logo-wrap,
.sidebar-header--collapsed .sidebar-logo-wrap--collapsed {{
  justify-content: center;
  width: 100%;
}}
.sidebar-logo-wrap img,
.sidebar-logo-wrap [data-testid="stImage"],
.sidebar-logo-wrap [data-testid="stImage"] img,
.ips-sidebar-logo-wrap img,
.ips-sidebar-logo-wrap [data-testid="stImage"],
.ips-sidebar-logo-wrap [data-testid="stImage"] img,
.sidebar-logo-wrap--collapsed img,
.sidebar-logo-wrap--collapsed [data-testid="stImage"] img {{
  max-width: 90%;
  max-height: 110px;
  width: auto;
  height: auto;
  display: block;
  margin: 0 auto;
  object-fit: contain;
  background: transparent !important;
}}
.sidebar-header--collapsed .sidebar-logo-wrap img,
.sidebar-header--collapsed .sidebar-logo-wrap [data-testid="stImage"] img,
.sidebar-header--collapsed .sidebar-logo-wrap--collapsed img,
.sidebar-header--collapsed .sidebar-logo-wrap--collapsed [data-testid="stImage"] img {{
  max-width: 28px;
  max-height: 28px;
}}
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):not(:hover) [data-testid="stHorizontalBlock"]:has(.sidebar-header-brand-marker),
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):not(:hover) [data-testid="stElementContainer"]:has(.sidebar-header-brand-marker),
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):not(:hover) [data-testid="stElementContainer"]:has(.sidebar-logo-wrap--expanded),
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):not(:hover) [data-testid="stElementContainer"]:has(.sidebar-divider--expanded-rail) {{
  display: none !important;
  height: 0 !important;
  min-height: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  overflow: hidden !important;
  visibility: hidden !important;
}}
section[data-testid="stSidebar"] .sidebar-logo-wrap [data-testid="stImage"],
section[data-testid="stSidebar"] .ips-sidebar-logo-wrap [data-testid="stImage"],
section[data-testid="stSidebar"] .sidebar-logo-wrap--collapsed [data-testid="stImage"] {{
  background: transparent !important;
  padding: 0 !important;
  margin: 0 auto !important;
  width: 100% !important;
  max-width: 100% !important;
  display: flex !important;
  justify-content: center !important;
  align-items: center !important;
}}
section[data-testid="stSidebar"] .sidebar-logo-wrap [data-testid="stImage"] > div,
section[data-testid="stSidebar"] .ips-sidebar-logo-wrap [data-testid="stImage"] > div,
section[data-testid="stSidebar"] .sidebar-logo-wrap--collapsed [data-testid="stImage"] > div {{
  background: transparent !important;
}}
.sidebar-logo-tagline,
.ips-sidebar-tagline {{
  font-size: 0.875rem;
  color: {TEXT_MUTED};
  margin: 8px 0 0;
  line-height: 1.25;
  font-weight: 500;
  max-width: 100%;
  text-align: center;
  width: 100%;
  white-space: normal;
}}
.sidebar-divider {{
  margin: 0.1rem 0.55rem 0.3rem !important;
  border: none !important;
  border-top: 1px solid {BORDER} !important;
  opacity: 1 !important;
}}
.sidebar-nav-group-divider {{
  display: none;
  margin: 0.45rem 0.75rem !important;
  border: none !important;
  border-top: 1px solid #e5eaf2 !important;
  height: 0 !important;
  opacity: 1 !important;
}}
.ips-sidebar-brand {{
  font-size: 0.875rem;
  font-weight: 700;
  color: {TEXT};
  margin: 0;
}}
.sidebar-section-title,
.ips-sidebar-nav-label,
.ips-sidebar-section-label {{
  font-size: 0.625rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: {TEXT_MUTED};
  text-align: left !important;
  padding: 0.55rem 0.65rem 0.15rem 20px;
  margin: 0;
}}
.sidebar-nav-scroll,
.ips-sidebar-nav-scroll {{
  padding: 0.15rem 0.35rem 0.2rem !important;
}}
section[data-testid="stSidebar"]:has(.ips-sidebar-nav-expanded) .sidebar-nav-scroll,
section[data-testid="stSidebar"]:has(.ips-sidebar-nav-expanded) .ips-sidebar-nav-scroll {{
  padding: 0.1rem 0.25rem 0.2rem !important;
}}
section[data-testid="stSidebar"]:has(.ips-sidebar-nav-expanded) [class*="st-key-nav_"] {{
  display: block !important;
  width: 100% !important;
  max-width: 100% !important;
  margin: 0 !important;
  padding: 0 !important;
}}
section[data-testid="stSidebar"]:has(.ips-sidebar-nav-expanded) [class*="st-key-nav_"] .stButton,
section[data-testid="stSidebar"]:has(.ips-sidebar-nav-expanded) [class*="st-key-nav_"] [data-testid="stButton"] {{
  width: 100% !important;
  max-width: 100% !important;
  margin: 0 !important;
}}
.sidebar-footer-label {{
  padding-top: 0.1rem !important;
}}
section[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.sidebar-nav-item) {{
  display: none !important;
  height: 0 !important;
  min-height: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  overflow: hidden !important;
}}
section[data-testid="stSidebar"] [class*="st-key-nav_"] {{
  width: 100% !important;
  max-width: 100% !important;
  margin: 0 !important;
  padding: 0 !important;
}}
section[data-testid="stSidebar"] [class*="st-key-nav_"] .stButton,
section[data-testid="stSidebar"] [class*="st-key-nav_"] [data-testid="stButton"] {{
  width: 100% !important;
  max-width: 100% !important;
}}
section[data-testid="stSidebar"] [class*="st-key-nav_"] .stButton > button,
section[data-testid="stSidebar"] [class*="st-key-nav_"] [data-testid="stButton"] > button,
section[data-testid="stSidebar"] [class*="st-key-nav_"] button[data-testid="stBaseButton-secondary"],
section[data-testid="stSidebar"] [class*="st-key-nav_"] button[data-testid="stBaseButton-primary"],
section[data-testid="stSidebar"] [class*="st-key-nav_"] [data-testid="stBaseButton-secondary"],
section[data-testid="stSidebar"] [class*="st-key-nav_"] [data-testid="stBaseButton-primary"] {{
  width: 100% !important;
  max-width: 100% !important;
  display: flex !important;
  align-items: center !important;
  justify-content: flex-start !important;
  text-align: left !important;
  background: transparent !important;
  background-color: transparent !important;
  border: none !important;
  border-color: transparent !important;
  box-shadow: none !important;
  outline: none !important;
  color: #334155 !important;
  font-weight: 500 !important;
  font-size: 0.8125rem !important;
  min-height: 2.25rem !important;
  padding: 10px 14px 10px 22px !important;
  margin: 0 !important;
  border-radius: 8px !important;
  transition: background 0.12s ease, color 0.12s ease !important;
}}
section[data-testid="stSidebar"]:has(.ips-sidebar-nav-expanded) [class*="st-key-nav_"] .stButton > button,
section[data-testid="stSidebar"]:has(.ips-sidebar-nav-expanded) [class*="st-key-nav_"] [data-testid="stButton"] > button,
section[data-testid="stSidebar"]:has(.ips-sidebar-nav-expanded) [class*="st-key-nav_"] button[data-testid="stBaseButton-secondary"],
section[data-testid="stSidebar"]:has(.ips-sidebar-nav-expanded) [class*="st-key-nav_"] button[data-testid="stBaseButton-primary"] {{
  padding: 10px 14px 10px 22px !important;
  margin: 0 !important;
  justify-content: flex-start !important;
  text-align: left !important;
}}
section[data-testid="stSidebar"] [class*="st-key-nav_"] .stButton > button p,
section[data-testid="stSidebar"] [class*="st-key-nav_"] [data-testid="stButton"] > button p,
section[data-testid="stSidebar"] [class*="st-key-nav_"] button[data-testid="stBaseButton-secondary"] p,
section[data-testid="stSidebar"] [class*="st-key-nav_"] button[data-testid="stBaseButton-primary"] p {{
  display: flex !important;
  align-items: center !important;
  justify-content: flex-start !important;
  gap: 10px !important;
  width: 100% !important;
  margin: 0 !important;
  text-align: left !important;
  font-weight: inherit !important;
  color: inherit !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}}
.sidebar-nav-icon {{
  width: 20px !important;
  min-width: 20px !important;
  max-width: 20px !important;
  flex: 0 0 20px !important;
  text-align: center !important;
  line-height: 1 !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
}}
.sidebar-nav-label {{
  flex: 1 1 auto !important;
  min-width: 0 !important;
  text-align: left !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}}
section[data-testid="stSidebar"] [class*="st-key-nav_"] .stButton > button[kind="secondary"],
section[data-testid="stSidebar"] [class*="st-key-nav_"] .stButton > button[data-testid="baseButton-secondary"],
section[data-testid="stSidebar"] [class*="st-key-nav_"] [data-testid="stButton"] > button[kind="secondary"],
section[data-testid="stSidebar"] [class*="st-key-nav_"] [data-testid="stButton"] > button[data-testid="baseButton-secondary"],
section[data-testid="stSidebar"] [class*="st-key-nav_"] button[data-testid="stBaseButton-secondary"] {{
  background: transparent !important;
  background-color: transparent !important;
  border: none !important;
  box-shadow: none !important;
}}
section[data-testid="stSidebar"] [class*="st-key-nav_"] .stButton > button:hover,
section[data-testid="stSidebar"] [class*="st-key-nav_"] [data-testid="stButton"] > button:hover,
section[data-testid="stSidebar"] [class*="st-key-nav_"] button[data-testid="stBaseButton-secondary"]:hover {{
  background: #f8fafc !important;
  color: #0f172a !important;
  border: none !important;
  box-shadow: none !important;
}}
section[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.sidebar-nav-item.active) + [class*="st-key-nav_"] .stButton > button,
section[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.sidebar-nav-item.active) + [class*="st-key-nav_"] [data-testid="stButton"] > button,
section[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.sidebar-nav-item.active) + [class*="st-key-nav_"] button[data-testid="stBaseButton-secondary"],
section[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.sidebar-nav-item.active) + [class*="st-key-nav_"] button[data-testid="stBaseButton-primary"],
section[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.sidebar-nav-item.active) + [class*="st-key-nav_"] .stButton > button:hover,
section[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.sidebar-nav-item.active) + [class*="st-key-nav_"] [data-testid="stButton"] > button:hover,
section[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.sidebar-nav-item.active) + [class*="st-key-nav_"] button[data-testid="stBaseButton-secondary"]:hover,
section[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.sidebar-nav-item.active) + [class*="st-key-nav_"] button[data-testid="stBaseButton-primary"]:hover {{
  background: {PRIMARY} !important;
  color: #ffffff !important;
  font-weight: 600 !important;
  border: none !important;
  box-shadow: none !important;
}}
section[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.sidebar-nav-item.active) + [class*="st-key-nav_"] .stButton > button p,
section[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.sidebar-nav-item.active) + [class*="st-key-nav_"] [data-testid="stButton"] > button p {{
  color: #ffffff !important;
  font-weight: 600 !important;
}}
body.ips-sidebar-collapsed .sidebar-nav-group-divider,
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed) .sidebar-nav-group-divider {{
  display: block !important;
}}
body.ips-sidebar-collapsed section[data-testid="stSidebar"] [class*="st-key-nav_"],
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed) [class*="st-key-nav_"] {{
  display: flex !important;
  justify-content: center !important;
  width: 100% !important;
}}
body.ips-sidebar-collapsed section[data-testid="stSidebar"] [class*="st-key-nav_"] .stButton,
body.ips-sidebar-collapsed section[data-testid="stSidebar"] [class*="st-key-nav_"] [data-testid="stButton"],
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed) [class*="st-key-nav_"] .stButton,
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed) [class*="st-key-nav_"] [data-testid="stButton"] {{
  width: auto !important;
  max-width: none !important;
}}
body.ips-sidebar-collapsed section[data-testid="stSidebar"] [class*="st-key-nav_"] .stButton > button,
body.ips-sidebar-collapsed section[data-testid="stSidebar"] [class*="st-key-nav_"] [data-testid="stButton"] > button,
body.ips-sidebar-collapsed section[data-testid="stSidebar"] [class*="st-key-nav_"] button[data-testid="stBaseButton-secondary"],
body.ips-sidebar-collapsed section[data-testid="stSidebar"] [class*="st-key-nav_"] button[data-testid="stBaseButton-primary"],
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed) [class*="st-key-nav_"] .stButton > button,
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed) [class*="st-key-nav_"] [data-testid="stButton"] > button,
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed) [class*="st-key-nav_"] button[data-testid="stBaseButton-secondary"],
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed) [class*="st-key-nav_"] button[data-testid="stBaseButton-primary"] {{
  width: 48px !important;
  min-width: 48px !important;
  max-width: 48px !important;
  height: 44px !important;
  min-height: 44px !important;
  padding: 0 !important;
  margin: 4px auto !important;
  border-radius: 10px !important;
  justify-content: center !important;
  align-items: center !important;
}}
body.ips-sidebar-collapsed section[data-testid="stSidebar"] [class*="st-key-nav_"] .stButton > button:hover,
body.ips-sidebar-collapsed section[data-testid="stSidebar"] [class*="st-key-nav_"] [data-testid="stButton"] > button:hover,
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed) [class*="st-key-nav_"] .stButton > button:hover,
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed) [class*="st-key-nav_"] [data-testid="stButton"] > button:hover {{
  background: #f1f5f9 !important;
  color: #334155 !important;
}}
body.ips-sidebar-collapsed section[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.sidebar-nav-item.active) + [class*="st-key-nav_"] .stButton > button,
body.ips-sidebar-collapsed section[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.sidebar-nav-item.active) + [class*="st-key-nav_"] [data-testid="stButton"] > button,
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed) [data-testid="stElementContainer"]:has(.sidebar-nav-item.active) + [class*="st-key-nav_"] .stButton > button,
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed) [data-testid="stElementContainer"]:has(.sidebar-nav-item.active) + [class*="st-key-nav_"] [data-testid="stButton"] > button,
body.ips-sidebar-collapsed section[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.sidebar-nav-item.active) + [class*="st-key-nav_"] .stButton > button:hover,
body.ips-sidebar-collapsed section[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.sidebar-nav-item.active) + [class*="st-key-nav_"] [data-testid="stButton"] > button:hover,
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed) [data-testid="stElementContainer"]:has(.sidebar-nav-item.active) + [class*="st-key-nav_"] .stButton > button:hover,
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed) [data-testid="stElementContainer"]:has(.sidebar-nav-item.active) + [class*="st-key-nav_"] [data-testid="stButton"] > button:hover {{
  background: {PRIMARY} !important;
  color: #ffffff !important;
}}
body.ips-sidebar-collapsed section[data-testid="stSidebar"] [class*="st-key-nav_"] .stButton > button p,
body.ips-sidebar-collapsed section[data-testid="stSidebar"] [class*="st-key-nav_"] [data-testid="stButton"] > button p,
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed) [class*="st-key-nav_"] .stButton > button p,
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed) [class*="st-key-nav_"] [data-testid="stButton"] > button p {{
  justify-content: center !important;
  text-align: center !important;
  font-size: 18px !important;
  line-height: 1 !important;
  width: auto !important;
  max-width: 100% !important;
  overflow: visible !important;
  gap: 0 !important;
}}
body.ips-sidebar-collapsed section[data-testid="stSidebar"] [class*="st-key-nav_"] .sidebar-nav-icon,
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed) [class*="st-key-nav_"] .sidebar-nav-icon {{
  width: 18px !important;
  min-width: 18px !important;
  max-width: 18px !important;
  flex: 0 0 18px !important;
  font-size: 18px !important;
}}
body.ips-sidebar-collapsed .sidebar-section-title,
body.ips-sidebar-collapsed .sidebar-logo-tagline,
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed) .sidebar-section-title,
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed) .sidebar-logo-tagline {{
  display: none !important;
}}
body.ips-sidebar-collapsed .ips-sidebar-nav-scroll,
body.ips-sidebar-collapsed .sidebar-nav-scroll,
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed) .ips-sidebar-nav-scroll,
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed) .sidebar-nav-scroll {{
  padding: 0 !important;
}}
body.ips-sidebar-collapsed section[data-testid="stSidebar"],
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed) {{
  padding-left: 0 !important;
  padding-right: 0 !important;
}}
body.ips-sidebar-collapsed section[data-testid="stSidebar"] [data-testid="stSidebarContent"],
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed) [data-testid="stSidebarContent"] {{
  padding-left: 0 !important;
  padding-right: 0 !important;
}}
.ips-sidebar-spacer {{
  flex: 1 1 auto;
  min-height: 0.75rem;
}}
.sidebar-version,
.ips-sidebar-version {{
  font-size: 0.68rem;
  color: {TEXT_MUTED};
  text-align: center;
  padding: 0.35rem 0.55rem 0.4rem;
  margin: 0;
  letter-spacing: 0.02em;
}}
.sidebar-user,
.ips-sidebar-user {{
  font-size: 0.75rem;
  color: {TEXT_MUTED};
  padding: 0.25rem 0.55rem 0.35rem;
  line-height: 1.35;
}}
.sidebar-user strong,
.ips-sidebar-user strong {{
  color: {TEXT};
  font-weight: 600;
}}
.sidebar-footer {{
  border-top: 1px solid {BORDER};
  padding-top: 0.25rem;
}}
section[data-testid="stSidebar"] [class*="st-key-ips_logout"] .stButton > button,
section[data-testid="stSidebar"] [class*="st-key-ips_logout"] [data-testid="stButton"] > button {{
  width: 100% !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  color: {TEXT_MUTED} !important;
  font-size: 0.8125rem !important;
  font-weight: 500 !important;
  min-height: 2rem !important;
  padding: 0.35rem 0.55rem !important;
  margin: 0.1rem 0 0 !important;
  border-radius: 8px !important;
}}
section[data-testid="stSidebar"] [class*="st-key-ips_logout"] .stButton > button:hover,
section[data-testid="stSidebar"] [class*="st-key-ips_logout"] [data-testid="stButton"] > button:hover {{
  background: #f8fafc !important;
  color: {TEXT} !important;
}}
body.ips-sidebar-collapsed section[data-testid="stSidebar"] [class*="st-key-ips_logout"],
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed) [class*="st-key-ips_logout"] {{
  display: flex !important;
  justify-content: center !important;
}}
body.ips-sidebar-collapsed section[data-testid="stSidebar"] [class*="st-key-ips_logout"] .stButton > button,
body.ips-sidebar-collapsed section[data-testid="stSidebar"] [class*="st-key-ips_logout"] [data-testid="stButton"] > button,
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed) [class*="st-key-ips_logout"] .stButton > button,
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed) [class*="st-key-ips_logout"] [data-testid="stButton"] > button {{
  width: 48px !important;
  min-width: 48px !important;
  max-width: 48px !important;
  height: 44px !important;
  min-height: 44px !important;
  padding: 0 !important;
  margin: 4px auto 0 !important;
  justify-content: center !important;
  border-radius: 10px !important;
}}
section[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.sidebar-footer-action) {{
  display: none !important;
  height: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  overflow: hidden !important;
}}
section[data-testid="stSidebar"] hr {{
  margin: 0.35rem 0.55rem !important;
  border-color: {BORDER} !important;
}}
.sidebar-header-top {{
  width: 100%;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}}
.sidebar-header-top [data-testid="column"]:first-child {{
  flex: 1 1 100% !important;
  width: 100% !important;
  max-width: 100% !important;
  display: flex !important;
  justify-content: center !important;
  align-items: center !important;
}}
.sidebar-header-top [data-testid="column"]:last-child {{
  position: absolute;
  top: 0.2rem;
  right: 0.2rem;
  display: flex !important;
  justify-content: flex-end !important;
  align-items: flex-start !important;
  width: auto !important;
  flex: 0 0 auto !important;
  z-index: 2;
}}
section[data-testid="stSidebar"] [class*="st-key-ips_sidebar_collapse_toggle"] {{
  position: static !important;
  top: auto !important;
  right: auto !important;
  width: auto !important;
  margin: 0 !important;
  padding: 0 !important;
}}
section[data-testid="stSidebar"] {{
  position: relative !important;
}}
section[data-testid="stSidebar"] > div,
section[data-testid="stSidebar"] [data-testid="stSidebarContent"],
section[data-testid="stSidebar"] .block-container {{
  position: relative !important;
}}

/* Tabs — underline style */
[class*="st-key-ips_tabs_wrap_"] {{
  margin-bottom: 0.65rem;
}}
[class*="st-key-ips_tabs_wrap_"] [data-testid="stRadio"] > div {{
  flex-direction: row !important;
  flex-wrap: wrap !important;
  gap: 0.15rem !important;
  border-bottom: 1px solid {BORDER};
  padding-bottom: 0.15rem;
}}
[class*="st-key-ips_tabs_wrap_"] [data-testid="stRadio"] label {{
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
[class*="st-key-ips_tabs_wrap_"] [data-testid="stRadio"] label[data-checked="true"],
[class*="st-key-ips_tabs_wrap_"] [data-testid="stRadio"] label:has(input:checked) {{
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
  padding: 0.85rem;
  text-align: center;
  color: {TEXT_MUTED};
  font-size: 0.8125rem;
  margin: 0.35rem 0;
}}

/* Compact table/list layouts */
.ips-table-count,
section[data-testid="stMain"]:has(.ips-page-shell-marker) [data-testid="stCaptionContainer"] {{
  margin: 8px 0 !important;
  padding: 0 !important;
}}
section[data-testid="stMain"]:has(.ips-page-shell-marker) [data-testid="stCaptionContainer"] p {{
  color: #64748b !important;
  font-size: 14px !important;
  line-height: 1.3 !important;
}}
.ips-table-wrap,
.ips-users-table-wrap,
.ips-jobs-table-wrap,
.ips-jobs-table-wrap.jobs-table,
.ips-customers-table-wrap,
.ips-estimates-table-wrap,
.ips-inventory-table-wrap,
.ips-assets-table-wrap,
.ips-timekeeping-table-wrap,
.ips-updates-table-wrap,
.ips-certifications-table-wrap,
.ips-contacts-table-wrap,
.ips-locations-table-wrap,
.ips-pg-table-wrap,
.ips-tasks-table-wrap,
.ips-documents-table-wrap {{
  margin-top: 10px !important;
}}
.st-key-jobs_table_wrap .ips-jobs-table-wrap,
.st-key-jobs_table_wrap .ips-jobs-table-wrap.jobs-table {{
  margin-top: 0 !important;
}}
.ips-table-header-row,
.ips-users-header-row,
.ips-customers-header-row,
.ips-estimates-header-row,
.ips-inventory-header-row,
.ips-assets-header-row,
.ips-timekeeping-header-row,
.ips-updates-header-row,
.ips-certifications-header-row,
.ips-contacts-header-row,
.ips-locations-header-row,
.ips-pg-header-row,
.ips-tasks-header-row {{
  padding: 5px 10px !important;
  min-height: 36px !important;
}}
.st-key-jobs_table_wrap .ips-jobs-header-row {{
  padding: 0 !important;
  min-height: 0 !important;
}}
.ips-table-row,
.ips-users-row,
.ips-customers-row,
.ips-estimates-row,
.ips-inventory-row,
.ips-assets-row,
.ips-timekeeping-row,
.ips-updates-row,
.ips-certifications-row,
.ips-contacts-row,
.ips-locations-row,
.ips-pg-row,
.ips-tasks-row {{
  padding: 5px 10px !important;
  min-height: 56px !important;
}}
.ips-card-title,
.ips-panel-title {{
  margin-bottom: 10px !important;
}}
.ips-detail-panel {{
  margin-top: 0.35rem !important;
}}
.ips-detail-header {{
  margin-bottom: 0.45rem !important;
}}
.st-key-dashboard_quick_actions [data-testid="stHorizontalBlock"] {{
  gap: 10px !important;
  align-items: stretch !important;
}}
.st-key-dashboard_quick_actions [data-testid="stElementContainer"] {{
  margin-bottom: 0 !important;
}}
.ips-weekly-timesheets-page ~ [data-testid="stElementContainer"],
section[data-testid="stMain"]:has(.ips-weekly-timesheets-page) [data-testid="stElementContainer"] {{
  margin-bottom: 0.2rem !important;
}}
section[data-testid="stMain"]:has(.ips-wjt-toolbar-marker) [data-testid="stElementContainer"]:has(.ips-wjt-toolbar-marker) {{
  margin-bottom: 0 !important;
}}
section[data-testid="stMain"]:has(.ips-wjt-toolbar-marker) [data-testid="stHorizontalBlock"] {{
  align-items: center !important;
  gap: 0.45rem !important;
  margin-bottom: 0 !important;
}}
section[data-testid="stMain"]:has(.ips-wjt-toolbar-marker) [data-testid="stElementContainer"] {{
  margin-bottom: 0.15rem !important;
}}
.ips-wjt-toolbar-marker {{
  display: none !important;
}}
.ips-wjt-week-end {{
  margin: 0 !important;
  padding-top: 0.35rem !important;
  font-size: 0.875rem !important;
  color: #64748b !important;
  line-height: 1.25 !important;
  text-align: right;
}}
.ips-wjt-week-end strong {{
  color: #0f172a;
  font-weight: 700;
}}
section[data-testid="stMain"]:has(.ips-weekly-timesheets-page) [data-testid="stSelectbox"] {{
  margin-top: 0 !important;
  margin-bottom: 0.25rem !important;
}}
section[data-testid="stMain"]:has(.ips-wt-preview-frame-marker) [data-testid="stHtml"] {{
  display: flex !important;
  justify-content: center !important;
}}
section[data-testid="stMain"]:has(.ips-wt-preview-frame-marker) [data-testid="stHtml"] iframe {{
  width: 100% !important;
  max-width: 9in !important;
  margin: 0 auto !important;
  display: block !important;
  background: #ececec !important;
  border: 1px solid #cbd5e1 !important;
  border-radius: 8px !important;
}}
.ips-time-week-range {{
  margin: 0 !important;
  font-size: 0.875rem !important;
  line-height: 1.25 !important;
  text-align: right !important;
  color: #0f172a !important;
  font-weight: 700 !important;
}}
.ips-time-week-sub {{
  margin: 0.15rem 0 0 !important;
  font-size: 0.75rem !important;
  line-height: 1.2 !important;
  text-align: right !important;
  color: #64748b !important;
  font-weight: 600 !important;
}}
.ips-timekeeping-week-range-wrap {{
  width: 100% !important;
  text-align: right !important;
}}
.st-key-tk_week_nav > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] > [data-testid="column"]:last-child {{
  min-width: 220px !important;
  flex: 1.5 1 auto !important;
}}
.st-key-tk_week_nav .ips-timekeeping-week-range-wrap,
.st-key-tk_week_nav .ips-time-week-range,
.st-key-tk_week_nav .ips-time-week-sub {{
  display: block !important;
  visibility: visible !important;
  opacity: 1 !important;
}}
.st-key-tk_week_nav {{
  margin: 0.35rem 0 0.75rem !important;
}}
.st-key-tk_week_nav [data-testid="stHorizontalBlock"] {{
  align-items: center !important;
}}
.st-key-tk_week_nav [data-testid="stButton"] > button {{
  background: #ffffff !important;
  color: #2563eb !important;
  border: 1px solid #cbd5e1 !important;
  border-radius: 8px !important;
  font-weight: 600 !important;
  font-size: 0.8125rem !important;
  min-height: 2.25rem !important;
  box-shadow: none !important;
}}
.st-key-tk_week_nav [data-testid="stButton"] > button:hover {{
  background: #f8fafc !important;
  border-color: #94a3b8 !important;
  color: #1d4ed8 !important;
}}
.ips-timekeeping-list-caption {{
  margin: 0 0 0.65rem !important;
  color: #64748b !important;
  font-size: 0.8125rem !important;
  line-height: 1.35 !important;
}}
.ips-timekeeping-day-header {{
  flex-direction: column !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 2px !important;
  padding: 8px 4px 6px !important;
  min-height: 44px !important;
  text-align: center !important;
}}
.timekeeping-header-day-label {{
  margin: 0 !important;
  font-size: 11px !important;
  font-weight: 800 !important;
  color: #0f172a !important;
  white-space: nowrap !important;
  letter-spacing: 0.02em !important;
  line-height: 1.15 !important;
  text-align: center !important;
}}
.timekeeping-header-status-badge,
.timekeeping-header-draft-badge {{
  margin: 0 !important;
  font-size: 10px !important;
  font-weight: 800 !important;
  letter-spacing: 0.03em !important;
  text-transform: uppercase !important;
  color: #0f172a !important;
  line-height: 1.1 !important;
  text-align: center !important;
}}
.timekeeping-header-summary-label {{
  margin: 0 !important;
  font-size: 11px !important;
  font-weight: 800 !important;
  color: #0f172a !important;
  text-align: center !important;
  white-space: nowrap !important;
  letter-spacing: 0.02em !important;
  line-height: 1.2 !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] .employee-name.ips-timekeeping-employee {{
  color: #2563eb !important;
}}
.timekeeping-status-text {{
  font-size: 13px !important;
  font-weight: 600 !important;
  color: #475569 !important;
  text-align: center !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_hour_spin_"] [data-testid="column"]:has(.timekeeping-spinner-buttons-marker) {{
  display: none !important;
  width: 0 !important;
  min-width: 0 !important;
  max-width: 0 !important;
  flex: 0 0 0 !important;
  overflow: hidden !important;
  opacity: 0 !important;
  pointer-events: none !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_list_hour_spin_"] [data-testid="column"]:has(.timekeeping-hour-input-marker) {{
  min-width: 100% !important;
  max-width: 100% !important;
  width: 100% !important;
  flex: 1 1 100% !important;
}}
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timekeeping-list-header-marker) {{
  background: transparent !important;
  border: none !important;
  border-bottom: 1px solid #e2e8f0 !important;
  border-radius: 0 !important;
  padding: 6px 4px 8px !important;
  margin-bottom: 0 !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="stHorizontalBlock"]:has(.timesheet-list-row-marker) {{
  background: #ffffff !important;
  border: none !important;
  border-bottom: 1px solid #e5e7eb !important;
  border-radius: 0 !important;
  min-height: 58px !important;
  height: auto !important;
  max-height: none !important;
  padding: 10px 4px !important;
  margin-bottom: 0 !important;
  overflow: visible !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="stHorizontalBlock"]:has(.timesheet-list-row-marker):hover {{
  background: #f8fbff !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] .timesheet-list-employee-cell .timesheet-list-name-input,
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] .timesheet-list-employee-cell .weekly-timesheet-employee-name,
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] .timesheet-list-employee-cell .employee-name.ips-timekeeping-employee {{
  font-size: 14px !important;
  font-weight: 700 !important;
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
  padding: 0 !important;
  min-height: 0 !important;
  height: auto !important;
  width: auto !important;
  min-width: 0 !important;
  max-width: 100% !important;
  color: #2563eb !important;
}}
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timekeeping-list-header-marker) .timekeeping-header-day-label,
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timekeeping-list-header-marker) .timekeeping-header-status-badge,
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timekeeping-list-header-marker) .timekeeping-header-draft-badge,
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timekeeping-list-row-header-marker) .timekeeping-header-day-label,
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timekeeping-list-row-header-marker) .timekeeping-header-status-badge,
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timekeeping-list-row-header-marker) .timekeeping-header-draft-badge,
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timekeeping-list-row-header-marker) .timekeeping-header-summary-label {{
  display: block !important;
  visibility: visible !important;
}}
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timekeeping-list-header-marker),
.st-key-timekeeping_table_wrap [data-testid="stHorizontalBlock"]:has(.timekeeping-list-row-header-marker) {{
  border-bottom: 1px solid #e8edf3 !important;
  padding: 6px 4px 4px !important;
  margin: 0 !important;
  background: #ffffff !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="stHorizontalBlock"]:has(.timesheet-list-row-marker) .timekeeping-day-date-label {{
  margin: 0 0 2px 0 !important;
  color: #0f172a !important;
  font-size: 10px !important;
  font-weight: 800 !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="stHorizontalBlock"]:has(.timesheet-list-row-marker) .timekeeping-day-status-badge {{
  margin: 0 0 4px 0 !important;
  font-size: 9px !important;
  font-weight: 800 !important;
  letter-spacing: 0.03em !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="stHorizontalBlock"]:has(.timesheet-list-row-marker) [class*="st-key-tk_list_hour_spin_"] [data-testid="stHorizontalBlock"]:has(.timekeeping-spinner-buttons-marker) {{
  border: none !important;
  border-radius: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
  height: auto !important;
  min-height: 0 !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [class*="st-key-tk_list_hour_spin_"] [data-testid="stNumberInput"] input,
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] .timekeeping-hour-input,
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] .timekeeping-hour-input-ro,
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] .timekeeping-list-hour-value {{
  background: transparent !important;
  border: none !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  height: auto !important;
  min-height: 0 !important;
  font-size: 14px !important;
  font-weight: 600 !important;
  color: #0f172a !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="stHorizontalBlock"]:has(.timesheet-list-row-marker) > [data-testid="column"]:nth-child(n+4):nth-child(-n+10):has(.ips-tk-day-draft),
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="stHorizontalBlock"]:has(.timesheet-list-row-marker) > [data-testid="column"]:nth-child(n+4):nth-child(-n+10):has(.ips-tk-day-draft-empty),
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="stHorizontalBlock"]:has(.timesheet-list-row-marker) > [data-testid="column"]:nth-child(n+4):nth-child(-n+10):has(.ips-tk-day-pending),
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="stHorizontalBlock"]:has(.timesheet-list-row-marker) > [data-testid="column"]:nth-child(n+4):nth-child(-n+10):has(.ips-tk-day-approved):not(:has(.ips-tk-day-approved-complete)),
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="stHorizontalBlock"]:has(.timesheet-list-row-marker) > [data-testid="column"]:nth-child(n+4):nth-child(-n+10):has(.ips-tk-day-rejected) {{
  background: transparent !important;
  box-shadow: none !important;
  border-radius: 0 !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="stHorizontalBlock"]:has(.timesheet-list-row-marker) > [data-testid="column"]:nth-child(n+4):nth-child(-n+10):has(.ips-tk-day-approved-complete) {{
  background: #f0fdf4 !important;
  border: 2px solid #22c55e !important;
  border-radius: 8px !important;
  box-shadow: 0 0 0 1px #bbf7d0 !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="stHorizontalBlock"]:has(.timesheet-list-row-marker) > [data-testid="column"]:nth-child(n+4):nth-child(-n+10):has(.ips-tk-day-pending) {{
  background: #fffbeb !important;
  border: 1px solid #f59e0b !important;
  border-radius: 8px !important;
}}
.st-key-timekeeping_table_wrap [class*="st-key-tk_row_"] [data-testid="stHorizontalBlock"]:has(.timesheet-list-row-marker) > [data-testid="column"]:nth-child(n+4):nth-child(-n+10):has(.ips-tk-day-rejected) {{
  background: #fef2f2 !important;
  border: 1px solid #ef4444 !important;
  border-radius: 8px !important;
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
    inject_compact_table_rows_css()
    inject_table_header_filter_css()
    inject_table_viewport_fit()
    inject_ips_dialog_styles()
    inject_action_colors_css()
    try:
        from app.ui.row_action_colors import inject_row_action_colors_css
    except ImportError:
        from ui.row_action_colors import inject_row_action_colors_css  # type: ignore
    inject_row_action_colors_css()
    inject_global_button_css()


def inject_ops_dashboard_css() -> None:
    """Compact operations dashboard layout — KPI row, news, quick actions, activity grid."""
    st.markdown(
        """
<style id="ips-ops-dashboard-v26">
/* ── App shell: flex main beside sidebar (desktop only) ── */
.stApp:has(.ips-ops-dashboard-marker) [data-testid="stAppViewContainer"] {
  width: 100% !important;
  max-width: 100% !important;
  overflow-x: clip !important;
  box-sizing: border-box !important;
}
.stApp:has(.ips-ops-dashboard-marker) section[data-testid="stMain"] {
  width: 100% !important;
  max-width: 100% !important;
  min-width: 0 !important;
  overflow-x: clip !important;
  box-sizing: border-box !important;
  background: #f1f5f9 !important;
}
@media (min-width: 900px) {
  .stApp:has(.ips-ops-dashboard-marker) [data-testid="stAppViewContainer"] {
    display: flex !important;
    flex-direction: row !important;
  }
  .stApp:has(.ips-ops-dashboard-marker) section[data-testid="stSidebar"] {
    flex: 0 0 230px !important;
    width: 230px !important;
    min-width: 230px !important;
    max-width: 230px !important;
  }
  .stApp:has(.ips-ops-dashboard-marker) section[data-testid="stMain"] {
    flex: 1 1 auto !important;
    min-width: 0 !important;
    width: auto !important;
    max-width: 100% !important;
  }
}
@media (max-width: 899px) {
  .stApp:has(.ips-ops-dashboard-marker) [data-testid="stAppViewContainer"] {
    margin-left: 0 !important;
    padding-left: 0 !important;
    width: 100% !important;
    max-width: 100% !important;
    display: block !important;
  }
  .stApp:has(.ips-ops-dashboard-marker) section[data-testid="stMain"] {
    flex: 1 1 100% !important;
    width: 100% !important;
    margin-left: 0 !important;
  }
}
section[data-testid="stMain"]:has(.ips-ops-dashboard-marker) .block-container {
  width: 100% !important;
  max-width: 100% !important;
  min-width: 0 !important;
  padding-left: 0 !important;
  padding-right: 0 !important;
  box-sizing: border-box !important;
}
section[data-testid="stMain"]:has(.ips-ops-dashboard-marker) [data-testid="stVerticalBlock"] {
  gap: 0 !important;
  width: 100% !important;
  max-width: 100% !important;
  min-width: 0 !important;
}
section[data-testid="stMain"]:has(.ips-ops-dashboard-marker) [data-testid="stVerticalBlock"] > div {
  padding-left: 20px !important;
  padding-right: 20px !important;
  box-sizing: border-box !important;
}
section[data-testid="stMain"]:has(.ips-ops-dashboard-marker) [data-testid="stElementContainer"] {
  margin-bottom: 0 !important;
  max-width: 100% !important;
  min-width: 0 !important;
  overflow: visible !important;
}

/* ── Dashboard shell ── */
.st-key-dashboard_ops_shell {
  width: 100% !important;
  max-width: 100% !important;
  min-width: 0 !important;
  box-sizing: border-box !important;
  overflow: visible !important;
}
.st-key-dashboard_ops_shell [data-testid="stVerticalBlock"] {
  gap: 20px !important;
  width: 100% !important;
  max-width: 100% !important;
  min-width: 0 !important;
  overflow: visible !important;
}
.st-key-dashboard_ops_kpis,
.st-key-dashboard_ops_row2,
.st-key-dashboard_estimates_waiting_table,
.st-key-dashboard_active_jobs_table {
  margin-bottom: 20px !important;
  width: 100% !important;
  max-width: 100% !important;
  min-width: 0 !important;
  overflow: visible !important;
}
.st-key-dashboard_active_jobs_table {
  margin-top: 0 !important;
}
.st-key-dashboard_estimates_waiting_table {
  background: #ffffff !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: 11px !important;
  padding: 0.75rem !important;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06) !important;
  box-sizing: border-box !important;
}
.st-key-dashboard_estimates_waiting_table [data-testid="stMarkdownContainer"],
.st-key-dashboard_estimates_waiting_table [data-testid="stMarkdownContainer"] p {
  margin: 0 !important;
  padding: 0 !important;
}
.ips-dash-est-waiting-head {
  margin: 0 0 4px 0 !important;
}
.ips-dash-est-waiting-title {
  margin: 0 !important;
}
.ips-dash-est-waiting-subtitle {
  margin: 4px 0 0 0 !important;
  font-size: 0.8125rem !important;
  font-weight: 500 !important;
  color: #64748b !important;
  line-height: 1.3 !important;
}
.ips-dash-est-waiting-empty {
  margin: 8px 0 0 0 !important;
  font-size: 0.8125rem !important;
  color: #94a3b8 !important;
  font-style: italic !important;
}
.ips-dash-est-table-scroll {
  width: 100% !important;
  overflow-x: auto !important;
  margin-top: 12px !important;
}
.ips-dash-est-html-table {
  width: 100% !important;
  border-collapse: separate !important;
  border-spacing: 0 !important;
  table-layout: fixed !important;
}
.ips-dash-est-html-table thead {
  display: table-header-group !important;
}
.ips-dash-est-html-table tbody {
  display: table-row-group !important;
}
.ips-dash-est-html-table tr {
  display: table-row !important;
  height: 46px !important;
}
.ips-dash-est-html-table thead tr {
  height: 44px !important;
}
.ips-dash-est-html-table th,
.ips-dash-est-html-table td {
  display: table-cell !important;
  vertical-align: middle !important;
  padding: 0 10px !important;
  border-bottom: 1px solid #e8edf4 !important;
  overflow: hidden !important;
  box-sizing: border-box !important;
}
.ips-dash-est-html-table thead th {
  background: #eef2f7 !important;
  color: #64748b !important;
  font-size: 0.68rem !important;
  font-weight: 800 !important;
  letter-spacing: 0.04em !important;
  text-transform: uppercase !important;
  white-space: nowrap !important;
}
.ips-dash-est-html-table tbody tr:hover {
  background: #f8fbff !important;
}
.ips-dash-est-html-table .cell-wrapper {
  display: flex !important;
  align-items: center !important;
  min-height: 46px !important;
  width: 100% !important;
  min-width: 0 !important;
}
.ips-dash-est-cell-right {
  justify-content: flex-end !important;
  text-align: right !important;
}
.ips-dash-est-cell-center {
  justify-content: center !important;
  text-align: center !important;
}
.ips-dash-est-link {
  color: #2563eb !important;
  font-weight: 800 !important;
  font-size: 0.8125rem !important;
  text-decoration: none !important;
  cursor: pointer !important;
  transition: color 0.15s ease !important;
  white-space: nowrap !important;
}
.ips-dash-est-desc-link {
  display: inline-block !important;
  max-width: 100% !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  white-space: nowrap !important;
}
.ips-dash-est-link:hover,
.ips-dash-est-link:focus {
  color: #1d4ed8 !important;
  text-decoration: underline !important;
}
.ips-dash-est-customer-cell,
.ips-dash-est-date-cell {
  font-size: 0.8125rem !important;
  font-weight: 600 !important;
  color: #0f172a !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}
.ips-dash-est-total-cell {
  font-size: 0.8125rem !important;
  font-weight: 800 !important;
  color: #2563eb !important;
  font-variant-numeric: tabular-nums !important;
}
.st-key-dashboard_estimates_waiting_table .ips-estimate-status-pill {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  height: 22px !important;
  min-height: 22px !important;
  max-height: 22px !important;
  padding: 0 10px !important;
  border-radius: 999px !important;
  font-size: 11px !important;
  font-weight: 800 !important;
  white-space: nowrap !important;
  line-height: 1 !important;
}
.st-key-dashboard_estimates_waiting_table .ips-estimate-status-draft {
  background: #f1f5f9 !important;
  color: #475569 !important;
}
.st-key-dashboard_estimates_waiting_table .ips-estimate-status-pending {
  background: #fef3c7 !important;
  color: #92400e !important;
}
.st-key-dashboard_estimates_waiting_table .ips-estimate-status-sent {
  background: #dbeafe !important;
  color: #1d4ed8 !important;
}
.ips-dash-est-actions {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: flex-end !important;
  gap: 6px !important;
  flex-wrap: nowrap !important;
}
.ips-dash-est-action {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  height: 30px !important;
  min-width: 58px !important;
  padding: 0 10px !important;
  border-radius: 8px !important;
  font-size: 0.75rem !important;
  font-weight: 700 !important;
  line-height: 1 !important;
  cursor: pointer !important;
  transition: all 0.15s ease !important;
  white-space: nowrap !important;
  box-sizing: border-box !important;
}
.ips-dash-est-approve {
  background: #ffffff !important;
  color: #2563eb !important;
  border: 1px solid #bfdbfe !important;
}
.ips-dash-est-approve:hover,
.ips-dash-est-approve:focus {
  background: #eff6ff !important;
  border-color: #93c5fd !important;
  color: #1d4ed8 !important;
}
.ips-dash-est-view {
  background: linear-gradient(180deg, #2563eb 0%, #1d4ed8 100%) !important;
  color: #ffffff !important;
  border: 1px solid #1e40af !important;
}
.ips-dash-est-view:hover,
.ips-dash-est-view:focus {
  filter: brightness(1.05) !important;
}
.st-key-dashboard_estimates_waiting_table .stButton > button {
  min-height: 34px !important;
  height: 34px !important;
  border-radius: 8px !important;
  font-size: 0.8125rem !important;
  font-weight: 600 !important;
  background: #ffffff !important;
  color: #2563eb !important;
  border: 1px solid #bfdbfe !important;
  box-shadow: none !important;
}
.st-key-dashboard_estimates_waiting_table .stButton > button:hover {
  background: #eff6ff !important;
  border-color: #93c5fd !important;
  color: #1d4ed8 !important;
}
section[data-testid="stMain"]:has(.ips-ops-dashboard-marker) [data-testid="stHorizontalBlock"]:has(.ips-page-title-block):has(.ips-page-actions-marker) {
  display: flex !important;
  justify-content: space-between !important;
  align-items: center !important;
  gap: 16px !important;
  width: 100% !important;
  flex-wrap: wrap !important;
}
section[data-testid="stMain"]:has(.ips-ops-dashboard-marker) [data-testid="stHorizontalBlock"]:has(.ips-page-actions-marker) {
  display: flex !important;
  align-items: center !important;
  justify-content: flex-end !important;
  gap: 0.5rem !important;
  flex-wrap: wrap !important;
}
section[data-testid="stMain"]:has(.ips-ops-dashboard-marker) .ips-page-header {
  margin-bottom: 12px !important;
  padding-bottom: 0 !important;
  width: 100% !important;
}
section[data-testid="stMain"]:has(.ips-ops-dashboard-marker) [data-testid="stHorizontalBlock"]:has(.ips-page-title-block) {
  align-items: center !important;
}
section[data-testid="stMain"]:has(.ips-ops-dashboard-marker) .ips-page-title {
  font-size: 2.125rem !important;
  font-weight: 800 !important;
  margin-bottom: 0 !important;
  color: #0f172a !important;
  letter-spacing: -0.02em;
}
section[data-testid="stMain"]:has(.ips-ops-dashboard-marker) .ips-page-subtitle {
  display: none !important;
}
.ips-ops-action-label {
  display: block;
  font-size: 0.68rem;
  font-weight: 700;
  color: #64748b;
  margin-bottom: 0.12rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  line-height: 1.2;
  min-height: 0.82rem;
}
.ips-ops-action-label-spacer {
  visibility: hidden;
}
section[data-testid="stMain"]:has(.ips-ops-dashboard-marker) [data-testid="stElementContainer"]:has(.ips-page-actions-marker) {
  margin-top: 0 !important;
}
section[data-testid="stMain"]:has(.ips-ops-dashboard-marker) [data-testid="column"]:has(.ips-page-actions-marker) {
  justify-content: flex-end !important;
}
section[data-testid="stMain"]:has(.ips-ops-dashboard-marker) [data-testid="column"]:has(.ips-page-actions-marker) > [data-testid="stHorizontalBlock"] {
  align-items: flex-end !important;
  width: 100% !important;
}
section[data-testid="stMain"]:has(.ips-ops-dashboard-marker) [data-testid="column"]:has(.ips-page-actions-marker) [data-testid="stDateInput"] {
  margin-top: 0 !important;
}
section[data-testid="stMain"]:has(.ips-ops-dashboard-marker) [data-testid="column"]:has(.ips-page-actions-marker) [data-testid="stDateInput"] > div {
  min-height: 38px !important;
}
section[data-testid="stMain"]:has(.ips-ops-dashboard-marker) [data-testid="column"]:has(.ips-page-actions-marker) [data-testid="stDateInput"] input {
  min-height: 38px !important;
}
.ips-ops-welcome {
  margin: 0 0 20px;
  padding: 0;
}
.ips-ops-welcome-greet {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.25;
}
.ips-ops-welcome-meta {
  margin: 0.12rem 0 0;
  font-size: 0.8125rem;
  color: #64748b;
  line-height: 1.35;
}

/* ── KPI row: pure HTML grid (no Streamlit columns) ── */
.st-key-dashboard_ops_kpis {
  width: 100% !important;
  max-width: 100% !important;
  min-width: 0 !important;
  overflow: visible !important;
}
.ips-ops-kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 16px;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  align-items: stretch;
}
.ips-ops-kpi-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 11px;
  padding: 0.65rem 0.75rem;
  min-height: 88px;
  height: 100%;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 0.55rem;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06);
  transition: box-shadow 0.15s ease, border-color 0.12s ease;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
}
.ips-ops-kpi-card:hover {
  box-shadow: 0 6px 16px rgba(37, 99, 235, 0.14);
  border-color: #bfdbfe;
}
.ips-ops-kpi-icon-ring {
  width: 2.25rem;
  height: 2.25rem;
  min-width: 2.25rem;
  border-radius: 999px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.95rem;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.65);
  flex-shrink: 0;
}
.ips-ops-kpi-text {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.ips-ops-kpi-value {
  font-size: 1.12rem;
  font-weight: 800;
  color: #0f172a;
  margin: 0;
  line-height: 1.15;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.ips-ops-kpi-label {
  font-size: 0.68rem;
  font-weight: 600;
  color: #64748b;
  margin: 0.1rem 0 0;
  line-height: 1.2;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}
.ips-ops-kpi-grid .ips-ops-kpi-card:nth-child(5) .ips-ops-kpi-value,
.ips-ops-kpi-grid .ips-ops-kpi-card:nth-child(6) .ips-ops-kpi-value {
  color: #15803d;
}
.ips-ops-kpi-grid .ips-ops-kpi-card:nth-child(4) .ips-ops-kpi-value {
  color: #ea580c;
}
@media (min-width: 1200px) {
  .ips-ops-kpi-grid {
    grid-template-columns: repeat(6, minmax(0, 1fr));
  }
}

/* ── Second row: news + quick actions ── */
.st-key-dashboard_ops_row2 {
  width: 100% !important;
  max-width: 100% !important;
  min-width: 0 !important;
}
.st-key-dashboard_ops_row2 [data-testid="stElementContainer"]:has(.ips-ops-row2-grid-marker) + [data-testid="stElementContainer"] [data-testid="stHorizontalBlock"] {
  display: flex !important;
  flex-direction: row !important;
  flex-wrap: wrap !important;
  gap: 16px !important;
  width: 100% !important;
  max-width: 100% !important;
  align-items: flex-start !important;
}
.st-key-dashboard_ops_row2 [data-testid="stElementContainer"]:has(.ips-ops-row2-grid-marker) + [data-testid="stElementContainer"] [data-testid="column"]:first-child {
  flex: 1 1 420px !important;
  min-width: 0 !important;
  width: auto !important;
  max-width: 100% !important;
  overflow: visible !important;
}
.st-key-dashboard_ops_row2 [data-testid="stElementContainer"]:has(.ips-ops-row2-grid-marker) + [data-testid="stElementContainer"] [data-testid="column"]:last-child {
  flex: 0 1 360px !important;
  min-width: min(320px, 100%) !important;
  width: auto !important;
  max-width: 100% !important;
  overflow: visible !important;
}

/* ── Company news ── */
.st-key-dashboard_company_updates {
  background: #ffffff !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: 11px !important;
  padding: 0.75rem !important;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05) !important;
  width: 100% !important;
  max-width: 100% !important;
  min-width: 0 !important;
  height: auto !important;
  overflow: visible !important;
  display: flex !important;
  flex-direction: column !important;
  box-sizing: border-box !important;
}
.st-key-dashboard_company_updates [data-testid="stVerticalBlock"] {
  gap: 0.5rem !important;
  width: 100% !important;
  overflow: visible !important;
}
.st-key-dashboard_company_updates [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:first-child [data-testid="stHorizontalBlock"] {
  display: flex !important;
  flex-wrap: nowrap !important;
  align-items: center !important;
  justify-content: space-between !important;
  gap: 0.75rem !important;
  width: 100% !important;
  margin-bottom: 0.25rem !important;
}
.st-key-dashboard_company_updates [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:first-child [data-testid="column"] {
  min-width: 0 !important;
  flex: 1 1 auto !important;
}
.st-key-dashboard_company_updates [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:first-child [data-testid="column"]:last-child {
  flex: 0 0 auto !important;
  width: auto !important;
  max-width: none !important;
}
.st-key-dashboard_company_updates [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:first-child [data-testid="column"]:last-child [data-testid="stHorizontalBlock"] {
  display: flex !important;
  justify-content: flex-end !important;
  align-items: center !important;
  gap: 0.5rem !important;
  width: auto !important;
}
.st-key-dashboard_company_updates [data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ops-news-item-marker) {
  display: flex !important;
  flex-direction: column !important;
  border: 1px solid #e8edf4 !important;
  border-radius: 10px !important;
  padding: 0 !important;
  margin-bottom: 0.5rem !important;
  background: #ffffff !important;
  height: auto !important;
  min-height: 140px !important;
  overflow: visible !important;
  width: 100% !important;
  max-width: 100% !important;
  box-sizing: border-box !important;
  position: relative !important;
}
.st-key-dashboard_company_updates [data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ops-news-item-marker) > [data-testid="stVerticalBlock"] {
  display: flex !important;
  flex-direction: column !important;
  flex: 1 1 auto !important;
  gap: 0 !important;
  height: auto !important;
  min-height: 100% !important;
  width: 100% !important;
}
.st-key-dashboard_company_updates [data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ops-news-item-marker) [data-testid="stElementContainer"]:has(.ips-ops-news-item-marker) {
  display: none !important;
  height: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
}
.st-key-dashboard_company_updates [data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ops-news-item-marker) [data-testid="stElementContainer"]:has(.ips-ct-feed-card-wrap),
.st-key-dashboard_company_updates [data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ops-news-item-marker) [data-testid="stElementContainer"]:has(.news-card) {
  flex: 0 0 auto !important;
  margin: 0 !important;
  padding: 0 !important;
  position: static !important;
  width: 100% !important;
}
.st-key-dashboard_company_updates [data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ops-news-item-marker) [data-testid="stElementContainer"]:has(.ips-ops-news-footer-marker) + [data-testid="stElementContainer"],
.st-key-dashboard_company_updates .news-footer {
  display: flex !important;
  flex-direction: column !important;
  margin-top: auto !important;
  padding: 10px 16px 16px !important;
  border-top: 1px solid #e2e8f0 !important;
  width: 100% !important;
  box-sizing: border-box !important;
  flex: 0 0 auto !important;
  position: static !important;
}
.st-key-dashboard_company_updates [data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ops-news-item-marker) [data-testid="stElementContainer"]:has(.ips-ops-news-footer-marker) {
  display: none !important;
  height: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  overflow: hidden !important;
}
.ips-ops-news-title {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 800;
  color: #0f172a;
}
.ips-cu-priority {
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  padding: 0.12rem 0.45rem;
  border-radius: 999px;
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.01em;
  border: 1px solid transparent;
  white-space: nowrap;
}
.ips-cu-priority-critical {
  background: #fee2e2;
  color: #b91c1c;
  border-color: #fecaca;
}
.ips-cu-priority-high {
  background: #ffedd5;
  color: #c2410c;
  border-color: #fed7aa;
}
.ips-cu-priority-normal {
  background: #dbeafe;
  color: #1d4ed8;
  border-color: #bfdbfe;
}
.ips-cu-priority-informational {
  background: #f8fafc;
  color: #64748b;
  border-color: #e2e8f0;
}
.ips-cu-new-badge {
  display: inline-flex;
  align-items: center;
  margin-left: 0.35rem;
  padding: 0.08rem 0.4rem;
  border-radius: 999px;
  background: #2563eb;
  color: #ffffff;
  font-size: 0.62rem;
  font-weight: 800;
  letter-spacing: 0.04em;
}
.ips-cu-card-headline {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.45rem;
}
.ips-cu-card-foot {
  margin-top: 0.15rem;
}
.ips-cu-attach {
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  font-size: 0.72rem;
  color: #475569;
}
.st-key-dashboard_ops_company_updates {
  margin-bottom: 0.35rem;
}
.ips-cu-banner {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 5;
  object-fit: cover;
  border-radius: 10px 10px 0 0;
}
.news-card.ips-cu-has-banner,
.st-key-dashboard_company_updates .news-card.ips-cu-has-banner {
  padding: 0 16px 0 !important;
  overflow: hidden;
}
.news-card.ips-cu-has-banner .ips-cu-card-content,
.st-key-dashboard_company_updates .news-card.ips-cu-has-banner .ips-cu-card-content {
  padding: 16px 0 0 !important;
}
.ips-cu-banner-figure {
  margin: 0 0 0.85rem;
}
.ips-cu-banner-link {
  display: block;
  text-decoration: none;
}
.ips-cu-banner-detail {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 5;
  object-fit: cover;
  border-radius: 12px;
  cursor: pointer;
}
.ips-cu-banner-caption {
  margin: 0.45rem 0 0;
  font-size: 0.82rem;
  color: #64748b;
  text-align: center;
}
.news-card,
.st-key-dashboard_company_updates .news-card {
  display: flex !important;
  flex-direction: column !important;
  gap: 10px !important;
  padding: 16px 16px 0 !important;
  height: auto !important;
  min-height: 0 !important;
  width: 100% !important;
  box-sizing: border-box !important;
  position: static !important;
  overflow: visible !important;
}
.news-card-head {
  display: flex !important;
  align-items: center !important;
  gap: 10px !important;
  width: 100% !important;
}
.news-card-meta {
  display: flex !important;
  flex-wrap: wrap !important;
  align-items: center !important;
  gap: 0.25rem 0.45rem !important;
  min-width: 0 !important;
  flex: 1 1 auto !important;
}
.news-card-title,
.st-key-dashboard_company_updates .news-card-title {
  margin: 0 !important;
  font-size: 0.875rem !important;
  font-weight: 800 !important;
  line-height: 1.3 !important;
  color: #0f172a !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  white-space: nowrap !important;
}
.news-card-preview,
.st-key-dashboard_company_updates .news-card-preview,
.st-key-dashboard_company_updates .ips-ct-body-compact {
  display: -webkit-box !important;
  -webkit-line-clamp: 2 !important;
  -webkit-box-orient: vertical !important;
  overflow: hidden !important;
  margin-top: 6px !important;
  margin-bottom: 12px !important;
  line-height: 1.45 !important;
  font-size: 0.8125rem !important;
  color: #475569 !important;
  width: 100% !important;
  position: static !important;
}
.st-key-dashboard_company_updates [data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ops-news-item-marker) [data-testid="stElementContainer"]:has(.ips-ops-news-footer-marker) + [data-testid="stElementContainer"] [data-testid="stHorizontalBlock"] {
  display: flex !important;
  flex-direction: row !important;
  justify-content: space-between !important;
  align-items: center !important;
  gap: 12px !important;
  margin: 0 !important;
  padding: 0 !important;
  border: none !important;
  width: 100% !important;
  position: static !important;
  transform: none !important;
  top: auto !important;
  bottom: auto !important;
}
.st-key-dashboard_company_updates [data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ops-news-item-marker) [data-testid="stElementContainer"]:has(.ips-ops-news-footer-marker) + [data-testid="stElementContainer"] [data-testid="column"] {
  flex: 0 0 auto !important;
  width: auto !important;
  min-width: 0 !important;
  max-width: none !important;
  display: flex !important;
  align-items: center !important;
  position: static !important;
}
.st-key-dashboard_company_updates [data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ops-news-item-marker) [data-testid="stElementContainer"]:has(.ips-ops-news-footer-marker) + [data-testid="stElementContainer"] [data-testid="column"]:first-child {
  justify-content: flex-start !important;
}
.st-key-dashboard_company_updates [data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ops-news-item-marker) [data-testid="stElementContainer"]:has(.ips-ops-news-footer-marker) + [data-testid="stElementContainer"] [data-testid="column"]:last-child {
  justify-content: flex-end !important;
  margin-left: auto !important;
}
.st-key-dashboard_company_updates [data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ops-news-item-marker) [data-testid="stElementContainer"]:has(.ips-ops-news-footer-marker) + [data-testid="stElementContainer"] .stButton,
.st-key-dashboard_company_updates [data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ops-news-item-marker) [data-testid="stElementContainer"]:has(.ips-ops-news-footer-marker) + [data-testid="stElementContainer"] [data-testid="stVerticalBlock"],
.st-key-dashboard_company_updates [data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ops-news-item-marker) [data-testid="stElementContainer"]:has(.ips-ops-news-footer-marker) + [data-testid="stElementContainer"] [data-testid="stElementContainer"] {
  position: static !important;
  margin: 0 !important;
  transform: none !important;
  top: auto !important;
  bottom: auto !important;
  width: auto !important;
}
.st-key-dashboard_company_updates [data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ops-news-item-marker) [data-testid="stElementContainer"]:has(.ips-ops-news-footer-marker) + [data-testid="stElementContainer"] .stButton > button {
  position: static !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  min-height: 32px !important;
  height: 32px !important;
  max-height: 32px !important;
  padding: 0 14px !important;
  margin: 0 !important;
  transform: none !important;
  top: auto !important;
  bottom: auto !important;
  font-size: 0.78rem !important;
  font-weight: 600 !important;
  border-radius: 8px !important;
  width: auto !important;
  min-width: 0 !important;
  max-width: none !important;
  white-space: nowrap !important;
  overflow: visible !important;
}
.ips-ct-feed-card-wrap-compact {
  margin: 0 !important;
  width: 100% !important;
  position: static !important;
}
.ips-ct-feed-card-compact,
.ips-ct-feed-card-ultra,
.st-key-dashboard_company_updates .ips-ct-feed-card-compact,
.st-key-dashboard_company_updates .ips-ct-feed-card-ultra {
  padding: 0 !important;
  border-radius: 0 !important;
  min-height: 0 !important;
  height: auto !important;
  max-height: none !important;
  overflow: visible !important;
  border: none !important;
  box-shadow: none !important;
  background: transparent !important;
  display: flex !important;
  flex-direction: column !important;
  position: static !important;
}
.ips-ct-avatar-sm {
  width: 1.75rem !important;
  height: 1.75rem !important;
  font-size: 0.62rem !important;
  flex-shrink: 0;
}
.ips-ct-compact-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem 0.45rem;
  align-items: center;
  font-size: 0.68rem;
}
.ips-ct-compact-meta .ips-ct-author {
  font-weight: 700;
  color: #0f172a;
}
.ips-ct-compact-meta .ips-ct-meta {
  color: #64748b;
}
.ips-ct-pin-badge {
  font-size: 0.58rem !important;
  font-weight: 700;
  color: #2563eb;
  background: #dbeafe;
  border-radius: 999px;
  padding: 0.04rem 0.35rem;
}
.ips-ct-title-compact {
  margin: 0 !important;
  font-size: 0.875rem !important;
  font-weight: 800 !important;
  line-height: 1.3 !important;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ips-ct-body-compact {
  margin: 0 !important;
}
.ips-ct-feed-card-unread.news-card {
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 72%) !important;
}
.ips-ct-feed-card-pinned.news-card {
  border-left: 3px solid #2563eb !important;
  padding-left: 13px !important;
}

/* ── Quick actions compact toolbar ── */
.st-key-dashboard_ops_quick_actions {
  width: 100% !important;
  max-width: 100% !important;
  min-width: 0 !important;
  background: transparent !important;
  border: none !important;
  padding: 0 !important;
  margin: 18px 0 8px !important;
  box-shadow: none !important;
  overflow: visible !important;
  box-sizing: border-box !important;
}
.st-key-dashboard_ops_quick_actions [data-testid="stVerticalBlockBorderWrapper"],
.st-key-dashboard_ops_quick_actions [data-testid="stVerticalBlock"],
.st-key-dashboard_ops_quick_actions [data-testid="stElementContainer"],
.st-key-dashboard_ops_quick_actions [data-testid="stMarkdownContainer"],
.st-key-dashboard_ops_quick_actions [data-testid="stMarkdownContainer"] p {
  margin: 0 !important;
  padding: 0 !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  position: static !important;
  transform: none !important;
}
.st-key-dashboard_ops_quick_actions [data-testid="stHorizontalBlock"] {
  flex-wrap: nowrap !important;
  gap: 10px !important;
  align-items: stretch !important;
}
.st-key-dashboard_ops_quick_actions [data-testid="stHorizontalBlock"] > [data-testid="column"] {
  min-width: 0 !important;
  flex: 1 1 0 !important;
  width: auto !important;
}
.st-key-dashboard_ops_quick_actions .stButton {
  width: 100% !important;
}
.st-key-dashboard_ops_quick_actions .stButton > button {
  min-height: 32px !important;
  height: 32px !important;
  padding: 0 12px !important;
  background: #ffffff !important;
  border: 1px solid #2563eb !important;
  border-radius: 6px !important;
  color: #0f172a !important;
  font-weight: 600 !important;
  font-size: 13px !important;
  line-height: 1 !important;
  box-shadow: none !important;
  white-space: nowrap !important;
  transition: background 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease, color 0.15s ease !important;
}
.st-key-dashboard_ops_quick_actions .stButton > button:hover {
  background: #2563eb !important;
  border-color: #2563eb !important;
  color: #ffffff !important;
  box-shadow: 0 4px 10px rgba(37, 99, 235, 0.22) !important;
}
.st-key-dashboard_ops_quick_actions .stButton > button p {
  font-size: 13px !important;
  font-weight: 600 !important;
  line-height: 1 !important;
  white-space: nowrap !important;
}
.ips-ops-quick-toolbar {
  width: 100%;
  box-sizing: border-box;
}
.ips-ops-quick-toolbar-title {
  margin: 0 0 10px;
  padding: 0;
  font-size: 0.82rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #64748b;
  line-height: 1.2;
}
.quick-actions-toolbar {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-start;
  gap: 10px;
  width: 100%;
  margin: 0;
  padding: 0;
}
.quick-actions-toolbar button,
.quick-actions-toolbar .quick-action-btn {
  width: auto;
  height: 32px;
  min-width: 130px;
  padding: 0 12px;
  margin: 0;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  box-sizing: border-box;
  white-space: nowrap;
  cursor: pointer;
  background: #ffffff;
  border: 1px solid #2563eb;
  color: #0f172a;
  font-weight: 600;
  font-size: 13px;
  line-height: 1;
  box-shadow: none;
  transition: background 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}
.quick-actions-toolbar .quick-action-icon {
  font-size: 14px;
  line-height: 1;
  flex-shrink: 0;
}
.quick-actions-toolbar .quick-action-label {
  font-size: 13px;
  font-weight: 600;
  line-height: 1;
}
.quick-actions-toolbar button:hover,
.quick-actions-toolbar .quick-action-btn:hover {
  background: #2563eb;
  border-color: #2563eb;
  color: #ffffff;
  box-shadow: 0 4px 10px rgba(37, 99, 235, 0.22);
}
.quick-actions-toolbar button:hover .quick-action-label,
.quick-actions-toolbar .quick-action-btn:hover .quick-action-label {
  color: #ffffff;
}
.ips-ops-section-title {
  margin: 0 0 12px;
  font-size: 1.25rem;
  font-weight: 800;
  color: #0f172a;
}

/* ── Dashboard preview cards (replaces expanders) ── */
.st-key-dashboard_preview_sections {
  width: 100% !important;
  max-width: 100% !important;
  margin-top: 20px !important;
  margin-bottom: 20px !important;
}
.st-key-dashboard_preview_sections [data-testid="stHorizontalBlock"] {
  align-items: stretch !important;
  gap: 16px !important;
}
.st-key-dashboard_preview_sections [data-testid="column"] {
  min-width: 0 !important;
}
.st-key-dashboard_preview_todos,
.st-key-dashboard_preview_qr,
.st-key-dashboard_preview_analytics,
.st-key-dashboard_preview_extra_qa {
  background: #ffffff !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: 11px !important;
  padding: 16px 18px 14px !important;
  margin-bottom: 16px !important;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05) !important;
  overflow: visible !important;
  box-sizing: border-box !important;
}
.st-key-dashboard_preview_todos [data-testid="stMarkdownContainer"],
.st-key-dashboard_preview_todos [data-testid="stMarkdownContainer"] p,
.st-key-dashboard_preview_qr [data-testid="stMarkdownContainer"],
.st-key-dashboard_preview_qr [data-testid="stMarkdownContainer"] p {
  width: 100% !important;
  max-width: 100% !important;
}
.ips-dash-preview-card,
.ips-dash-preview-card-body {
  width: 100% !important;
  max-width: 100% !important;
  box-sizing: border-box !important;
}
.ips-dash-preview-card-head {
  display: flex !important;
  align-items: center !important;
  gap: 10px !important;
  margin: 0 0 12px 0 !important;
}
.ips-dash-preview-card-icon {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  width: 30px !important;
  height: 30px !important;
  border-radius: 8px !important;
  background: #eff6ff !important;
  color: #2563eb !important;
  font-size: 16px !important;
  flex-shrink: 0 !important;
}
.ips-dash-preview-card-title {
  margin: 0 !important;
  font-size: 1rem !important;
  font-weight: 800 !important;
  color: #0f172a !important;
  line-height: 1.2 !important;
}
.ips-dash-preview-list {
  list-style: none !important;
  margin: 0 0 12px 0 !important;
  padding: 0 !important;
  width: 100% !important;
}
.ips-dash-preview-row {
  display: grid !important;
  grid-template-columns: minmax(0, 1fr) !important;
  align-items: center !important;
  gap: 12px !important;
  width: 100% !important;
  box-sizing: border-box !important;
  padding: 8px 10px !important;
  border-radius: 8px !important;
  border: 1px solid transparent !important;
  transition: background 0.15s ease, border-color 0.15s ease !important;
}
.ips-dash-preview-row:has(.ips-dash-preview-row-meta) {
  grid-template-columns: minmax(0, 1.35fr) minmax(0, 0.95fr) minmax(168px, auto) !important;
}
.ips-dash-preview-row:hover {
  background: #f8fbff !important;
  border-color: #dbeafe !important;
}
.ips-dash-preview-row-main {
  min-width: 0 !important;
}
.ips-dash-preview-row-title {
  margin: 0 !important;
  font-size: 0.8125rem !important;
  font-weight: 700 !important;
  color: #0f172a !important;
  line-height: 1.25 !important;
  display: -webkit-box !important;
  -webkit-line-clamp: 2 !important;
  -webkit-box-orient: vertical !important;
  overflow: hidden !important;
}
.ips-dash-preview-row-sub {
  margin: 2px 0 0 0 !important;
  font-size: 0.72rem !important;
  color: #64748b !important;
  line-height: 1.3 !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}
.ips-dash-preview-row-meta {
  min-width: 0 !important;
  display: flex !important;
  flex-direction: column !important;
  gap: 2px !important;
}
.ips-dash-preview-row-meta-line {
  margin: 0 !important;
  font-size: 0.72rem !important;
  color: #475569 !important;
  line-height: 1.3 !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}
.ips-dash-preview-row-meta-label {
  font-weight: 700 !important;
  color: #64748b !important;
  text-transform: uppercase !important;
  letter-spacing: 0.02em !important;
  font-size: 0.625rem !important;
  margin-right: 4px !important;
}
.ips-dash-preview-row-badges {
  display: flex !important;
  align-items: center !important;
  justify-content: flex-end !important;
  gap: 4px !important;
  flex-wrap: wrap !important;
  min-width: 168px !important;
}
.ips-dash-preview-badge {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  min-height: 20px !important;
  padding: 0 7px !important;
  border-radius: 999px !important;
  font-size: 0.625rem !important;
  font-weight: 700 !important;
  white-space: nowrap !important;
  line-height: 1 !important;
}
.ips-dash-preview-priority-urgent { background: #fee2e2 !important; color: #991b1b !important; }
.ips-dash-preview-priority-high { background: #ffedd5 !important; color: #9a3412 !important; }
.ips-dash-preview-priority-medium { background: #e0f2fe !important; color: #075985 !important; }
.ips-dash-preview-priority-low { background: #f1f5f9 !important; color: #475569 !important; }
.ips-dash-preview-status-open { background: #dbeafe !important; color: #1d4ed8 !important; }
.ips-dash-preview-status-active { background: #fef3c7 !important; color: #92400e !important; }
.ips-dash-preview-status-blocked { background: #fee2e2 !important; color: #991b1b !important; }
.ips-dash-preview-status-done { background: #dcfce7 !important; color: #166534 !important; }
.ips-dash-preview-empty {
  margin: 0 0 12px 0 !important;
  font-size: 0.8125rem !important;
  color: #94a3b8 !important;
  font-style: italic !important;
}
.st-key-dashboard_preview_todos .stButton > button,
.st-key-dashboard_preview_qr .stButton > button,
.st-key-dashboard_preview_analytics .stButton > button {
  min-height: 34px !important;
  height: 34px !important;
  border-radius: 8px !important;
  font-size: 0.8125rem !important;
  font-weight: 600 !important;
  background: #ffffff !important;
  color: #2563eb !important;
  border: 1px solid #bfdbfe !important;
  box-shadow: none !important;
}
.st-key-dashboard_preview_todos .stButton > button:hover,
.st-key-dashboard_preview_qr .stButton > button:hover,
.st-key-dashboard_preview_analytics .stButton > button:hover {
  background: #eff6ff !important;
  border-color: #93c5fd !important;
  color: #1d4ed8 !important;
}
.ips-dash-analytics-list {
  display: flex !important;
  flex-direction: column !important;
  gap: 8px !important;
  margin: 0 0 14px 0 !important;
  padding: 0 !important;
}
.ips-dash-analytics-row {
  display: flex !important;
  justify-content: space-between !important;
  align-items: center !important;
  width: 100% !important;
  box-sizing: border-box !important;
  padding: 14px 16px !important;
  margin: 0 !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: 8px !important;
  background: #ffffff !important;
  cursor: pointer !important;
  text-align: left !important;
  transition: all 0.15s ease !important;
  font: inherit !important;
  color: inherit !important;
  box-shadow: none !important;
}
.ips-dash-analytics-row:hover,
.ips-dash-analytics-row:focus {
  background: #f7f9fc !important;
  border-color: #2563eb !important;
  transform: translateX(2px) !important;
  outline: none !important;
}
.ips-dash-analytics-row-body {
  display: flex !important;
  align-items: center !important;
  gap: 12px !important;
  min-width: 0 !important;
  flex: 1 1 auto !important;
}
.ips-dash-analytics-row-icon {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  width: 28px !important;
  height: 28px !important;
  flex-shrink: 0 !important;
  font-size: 1rem !important;
  line-height: 1 !important;
}
.ips-dash-analytics-row-text {
  display: flex !important;
  flex-direction: column !important;
  gap: 2px !important;
  min-width: 0 !important;
}
.ips-dash-analytics-row-title {
  display: block !important;
  margin: 0 !important;
  font-size: 0.875rem !important;
  font-weight: 700 !important;
  color: #0f172a !important;
  line-height: 1.25 !important;
}
.ips-dash-analytics-row-sub {
  display: block !important;
  margin: 0 !important;
  font-size: 0.75rem !important;
  font-weight: 500 !important;
  color: #64748b !important;
  line-height: 1.3 !important;
}
.ips-dash-analytics-row-chevron {
  flex-shrink: 0 !important;
  margin-left: 12px !important;
  font-size: 1.125rem !important;
  font-weight: 700 !important;
  line-height: 1 !important;
  color: #94a3b8 !important;
  transition: color 0.15s ease, transform 0.15s ease !important;
}
.ips-dash-analytics-row:hover .ips-dash-analytics-row-chevron,
.ips-dash-analytics-row:focus .ips-dash-analytics-row-chevron {
  color: #2563eb !important;
}
.st-key-dashboard_preview_analytics [data-testid="stHorizontalBlock"]:has(.stButton) {
  gap: 8px !important;
  margin-bottom: 8px !important;
}
.st-key-dashboard_preview_extra_qa [data-testid="stHorizontalBlock"]:has(.stButton) {
  display: grid !important;
  grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
  gap: 10px !important;
  margin-bottom: 0 !important;
}
.st-key-dashboard_preview_extra_qa .stButton > button {
  min-height: 38px !important;
  height: 38px !important;
  border-radius: 8px !important;
  font-size: 0.78rem !important;
  font-weight: 600 !important;
  padding: 0 10px !important;
  background: linear-gradient(180deg, #2563eb 0%, #1d4ed8 100%) !important;
  border: 1px solid #1e40af !important;
  color: #ffffff !important;
  box-shadow: 0 1px 3px rgba(37, 99, 235, 0.22) !important;
  transition: all 0.15s ease !important;
}
.st-key-dashboard_preview_extra_qa .stButton > button:hover {
  transform: translateY(-1px) !important;
  box-shadow: 0 4px 10px rgba(37, 99, 235, 0.28) !important;
}
.ips-dash-preview-grid-marker,
.ips-dash-preview-qa-grid-marker {
  display: none !important;
}
@media (max-width: 992px) {
  .st-key-dashboard_preview_sections [data-testid="column"] {
    flex: 1 1 100% !important;
    min-width: 100% !important;
    max-width: 100% !important;
  }
  .ips-dash-preview-row {
    grid-template-columns: minmax(0, 1fr) !important;
    align-items: flex-start !important;
  }
  .ips-dash-preview-row-badges {
    justify-content: flex-start !important;
    min-width: 0 !important;
  }
}

/* ── Expanders (legacy) ── */
.st-key-dashboard_management_reminders {
  padding: 0.75rem !important;
  margin-bottom: 20px !important;
}
.ips-ops-expander .ips-panel-card {
  min-height: 0 !important;
  padding: 0.55rem 0.65rem !important;
  margin-bottom: 0.35rem !important;
}
section[data-testid="stMain"]:has(.ips-ops-dashboard-marker) [data-testid="stExpander"] {
  margin-bottom: 20px !important;
  max-width: 100% !important;
}
section[data-testid="stMain"]:has(.ips-ops-dashboard-marker) [data-testid="stExpander"] summary {
  font-size: 0.82rem !important;
  font-weight: 700 !important;
  padding: 0.35rem 0 !important;
}

/* ── Responsive breakpoints ── */
@media (max-width: 992px) {
  .st-key-dashboard_ops_row2 [data-testid="stElementContainer"]:has(.ips-ops-row2-grid-marker) + [data-testid="stElementContainer"] [data-testid="column"]:first-child,
  .st-key-dashboard_ops_row2 [data-testid="stElementContainer"]:has(.ips-ops-row2-grid-marker) + [data-testid="stElementContainer"] [data-testid="column"]:last-child {
    flex: 1 1 100% !important;
    min-width: 100% !important;
    max-width: 100% !important;
  }
}
@media (max-width: 768px) {
  section[data-testid="stMain"]:has(.ips-ops-dashboard-marker) [data-testid="stVerticalBlock"] > div {
    padding-left: 12px !important;
    padding-right: 12px !important;
  }
  section[data-testid="stMain"]:has(.ips-ops-dashboard-marker) .ips-page-title {
    font-size: 1.5rem !important;
  }
  section[data-testid="stMain"]:has(.ips-ops-dashboard-marker) [data-testid="stHorizontalBlock"]:has(.ips-page-title-block):has(.ips-page-actions-marker) {
    flex-direction: column !important;
    align-items: stretch !important;
    gap: 12px !important;
  }
  section[data-testid="stMain"]:has(.ips-ops-dashboard-marker) [data-testid="column"]:has(.ips-page-actions-marker) {
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
    justify-content: flex-start !important;
  }
  section[data-testid="stMain"]:has(.ips-ops-dashboard-marker) [data-testid="column"]:has(.ips-page-actions-marker) > [data-testid="stHorizontalBlock"] {
    flex-direction: column !important;
    align-items: stretch !important;
    width: 100% !important;
    gap: 0.5rem !important;
  }
  section[data-testid="stMain"]:has(.ips-ops-dashboard-marker) [data-testid="column"]:has(.ips-page-actions-marker) [data-testid="column"] {
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
    flex: 1 1 100% !important;
  }
  section[data-testid="stMain"]:has(.ips-ops-dashboard-marker) [data-testid="column"]:has(.ips-page-actions-marker) .stButton {
    width: 100% !important;
    max-width: 100% !important;
  }
  section[data-testid="stMain"]:has(.ips-ops-dashboard-marker) [data-testid="column"]:has(.ips-page-actions-marker) .stButton > button {
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
  }
  .ips-ops-kpi-grid {
    grid-template-columns: 1fr !important;
    gap: 12px !important;
  }
  .st-key-dashboard_ops_row2 [data-testid="stElementContainer"]:has(.ips-ops-row2-grid-marker) + [data-testid="stElementContainer"] [data-testid="column"]:first-child,
  .st-key-dashboard_ops_row2 [data-testid="stElementContainer"]:has(.ips-ops-row2-grid-marker) + [data-testid="stElementContainer"] [data-testid="column"]:last-child {
    flex: 1 1 100% !important;
    min-width: 0 !important;
    max-width: 100% !important;
    width: 100% !important;
  }
  .st-key-dashboard_ops_row2 [data-testid="stElementContainer"]:has(.ips-ops-row2-grid-marker) + [data-testid="stElementContainer"] [data-testid="stHorizontalBlock"] {
    flex-direction: column !important;
    gap: 12px !important;
  }
  .st-key-dashboard_active_jobs_table,
  .st-key-dashboard_estimates_waiting_table,
  .st-key-dashboard_ops_kpis,
  .st-key-dashboard_ops_row2,
  .st-key-dashboard_company_updates,
  .st-key-dashboard_ops_shell {
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
    overflow-x: hidden !important;
    box-sizing: border-box !important;
  }
  .ips-dash-jobs-table-scroll,
  .ips-dash-est-table-scroll {
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch;
  }
  .ips-ops-welcome-greet {
    font-size: 1rem !important;
    word-break: break-word !important;
  }
  .ips-ops-welcome-meta {
    word-break: break-word !important;
  }
}
@media (max-width: 480px) {
  .ips-ops-kpi-grid {
    grid-template-columns: 1fr !important;
  }
}
</style>
""",
        unsafe_allow_html=True,
    )


def inject_coupling_inspection_css() -> None:
    """Mobile/iPad-friendly coupling inspection V7 form styling."""
    st.markdown(
        """
<style id="ips-coupling-inspection-v7">
.ips-page-coupling_inspection [data-testid="stCheckbox"] label {
  min-height: 2.25rem !important;
  min-width: 2.25rem !important;
  padding: 0.35rem 0.5rem !important;
}
.ips-page-coupling_inspection [data-testid="stCheckbox"] label p {
  font-size: 1rem !important;
  font-weight: 600 !important;
}
.ips-page-coupling_inspection [data-testid="stButton"] > button {
  min-height: 2.85rem !important;
  font-weight: 700 !important;
  font-size: 0.95rem !important;
}
.ips-page-coupling_inspection [data-testid="stTextInput"] input,
.ips-page-coupling_inspection [data-testid="stNumberInput"] input {
  min-height: 2.5rem !important;
  font-size: 1rem !important;
}
.ips-page-coupling_inspection [data-testid="stFileUploader"] {
  padding: 0.5rem 0 !important;
}
.ips-page-coupling_inspection [data-testid="column"] {
  min-width: 0 !important;
}
.ips-coupling-v7-header {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 14px;
  background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  margin-bottom: 10px;
}
.ips-coupling-v7-title {
  font-size: 1.15rem;
  font-weight: 800;
  color: #0f172a;
  line-height: 1.25;
}
.ips-coupling-v7-meta {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}
.ips-coupling-v7-version {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  background: #2563eb;
  color: #fff;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.04em;
}
.ips-coupling-v7-status {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 800;
}
.ips-coupling-v7-status-draft { background: #f1f5f9; color: #475569; }
.ips-coupling-v7-status-completed { background: #dcfce7; color: #166534; }
.ips-coupling-v7-status-exported { background: #dbeafe; color: #1d4ed8; }
.ips-coupling-v7-job-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 18px;
  padding: 8px 12px;
  margin-bottom: 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 0.85rem;
  color: #334155;
}
.ips-coupling-v7-task-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
  padding: 6px 12px;
  margin: -4px 0 12px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  font-size: 0.84rem;
  color: #1e3a8a;
}
.ips-coupling-spec-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 8px;
  margin: 8px 0 12px;
}
.ips-coupling-spec-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px 12px;
}
.ips-coupling-spec-label {
  font-size: 0.68rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #64748b;
  margin-bottom: 4px;
}
.ips-coupling-spec-value {
  font-size: 0.92rem;
  font-weight: 650;
  color: #0f172a;
  line-height: 1.3;
}
.ips-coupling-torque-pattern {
  display: block;
  max-width: 220px;
  margin: 0 auto;
}
@media (max-width: 768px) {
  .ips-page-coupling_inspection [data-testid="stHorizontalBlock"] {
    flex-wrap: wrap !important;
  }
  .ips-coupling-v7-header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
""",
        unsafe_allow_html=True,
    )


def inject_employee_portal_css() -> None:
    """Mobile-first IPS Employee Portal styling."""
    st.markdown(
        """
<style id="ips-employee-portal">
.ips-employee-portal-page,
.ips-employee-resources-page,
.ips-employee-profile-page,
.ips-employee-qr-page {
  background: #ffffff;
}
.ips-ep-header {
  background: linear-gradient(135deg, #0b1f3a 0%, #12325c 100%);
  color: #ffffff;
  border-radius: 12px;
  padding: 14px 16px;
  margin-bottom: 12px;
}
.ips-ep-header-top {
  display: flex;
  align-items: center;
  gap: 12px;
}
.ips-ep-logo {
  width: 52px;
  height: 52px;
  object-fit: contain;
  border-radius: 8px;
  background: #ffffff;
  padding: 4px;
}
.ips-ep-greeting {
  font-size: 1.15rem;
  font-weight: 700;
  margin: 0;
}
.ips-ep-date,
.ips-ep-role {
  margin: 2px 0 0;
  font-size: 0.85rem;
  opacity: 0.92;
}
.ips-ep-section-title {
  font-size: 1rem;
  font-weight: 700;
  color: #0f172a;
  margin: 16px 0 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid #e2e8f0;
}
.ips-ep-page-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: #0b1f3a;
  margin: 0 0 12px;
}
.ips-ep-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 12px 14px;
  margin-bottom: 8px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
}
.ips-ep-card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.ips-ep-muted {
  color: #64748b;
  font-size: 0.88rem;
  margin: 0 0 6px;
}
.ips-ep-meta {
  color: #94a3b8;
  font-size: 0.78rem;
  margin: 0;
}
.ips-ep-empty {
  color: #64748b;
  font-size: 0.9rem;
  margin: 0 0 8px;
}
.ips-ep-status {
  display: inline-block;
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
}
.ips-ep-status-neutral { background: #f1f5f9; color: #475569; }
.ips-ep-status-warn { background: #fef3c7; color: #b45309; }
.ips-ep-status-info { background: #dbeafe; color: #1d4ed8; }
.ips-ep-tag {
  background: #eff6ff;
  color: #1d4ed8;
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 0.72rem;
  font-weight: 700;
}
.ips-ep-list-row {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px 12px;
  margin-bottom: 6px;
  background: #fafafa;
}
.ips-ep-list-main strong {
  display: block;
  color: #0f172a;
  margin-bottom: 2px;
}
.ips-ep-list-main span {
  display: block;
  color: #64748b;
  font-size: 0.84rem;
}
.ips-ep-list-meta {
  margin-top: 6px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px 10px;
  font-size: 0.78rem;
  color: #64748b;
}
.ips-ep-cert-btn {
  display: block;
  width: 100%;
  text-align: left;
  border: 1px solid #cbd5e1;
  border-radius: 12px;
  background: #f8fafc;
  padding: 12px 14px;
  margin-bottom: 6px;
}
.ips-ep-cert-name {
  display: block;
  font-weight: 700;
  color: #0f172a;
}
.ips-ep-cert-exp {
  display: block;
  color: #64748b;
  font-size: 0.84rem;
  margin-top: 2px;
}
.ips-page-employee_portal [data-testid="stButton"] > button[kind="primary"],
.ips-page-employee_qr_scan [data-testid="stButton"] > button[kind="primary"],
.ips-page-employee_resources [data-testid="stButton"] > button[kind="primary"] {
  background: #1d4ed8 !important;
  border-color: #1d4ed8 !important;
  min-height: 2.85rem !important;
  border-radius: 10px !important;
  font-weight: 700 !important;
}
.ips-page-employee_portal [data-testid="stButton"] > button,
.ips-page-employee_qr_scan [data-testid="stButton"] > button,
.ips-page-employee_resources [data-testid="stButton"] > button {
  min-height: 2.6rem !important;
  border-radius: 10px !important;
}
</style>
""",
        unsafe_allow_html=True,
    )
