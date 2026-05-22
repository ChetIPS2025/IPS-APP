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
    """Users/Employees list table stability — call at the top of the users page render."""
    st.markdown(
        f"""
<style id="ips-users-module-v2">
.ips-users-page .ips-data-table-wrap,
.ips-users-page .ips-data-table-stable .ips-data-table-header,
.ips-users-page .ips-data-table-stable .ips-data-row {{
  display: grid !important;
  box-sizing: border-box !important;
}}
.ips-users-page .ips-data-table-html .ips-data-row {{
  display: grid !important;
  min-height: 2.75rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
.ips-users-page .ips-data-table-html .ips-data-cell {{
  overflow: hidden;
  text-overflow: ellipsis;
}}
.ips-users-page .ips-employees-summary-table .ips-data-row {{
  display: grid !important;
  min-height: 2.75rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
.ips-users-page div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-click-table-employees_list)
div[data-testid="stVerticalBlock"]:has(.ips-clean-row-wrap) .ips-data-row {{
  display: grid !important;
  min-height: 2.75rem;
  width: 100%;
  min-width: 48rem;
  box-sizing: border-box;
}}
.ips-users-page div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-click-table-employees_list)
div[data-testid="stVerticalBlock"]:has(.ips-clean-row-wrap) .ips-data-row:hover {{
  background: #eef5ff;
}}
.ips-users-page div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-click-table-employees_list)
div[data-testid="stVerticalBlock"]:has(.ips-clean-row-wrap) .ips-data-row.selected {{
  background: #eef5ff;
  border-left: 4px solid #2563eb;
}}
/* Users list: invisible full-row select button layered under HTML row */
section[data-testid="stMain"]:has(.ips-users-page)
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-click-table-employees_list)
div[data-testid="stVerticalBlock"]:has(.ips-clean-row-wrap) {{
  position: relative !important;
  min-height: 2.75rem !important;
  margin: 0 !important;
  padding: 0 !important;
}}
section[data-testid="stMain"]:has(.ips-users-page)
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-click-table-employees_list)
div[data-testid="stVerticalBlock"]:has(.ips-clean-row-wrap)
> [data-testid="stElementContainer"]:has(.ips-clean-row-select-btn)
+ [data-testid="stElementContainer"] {{
  position: absolute !important;
  inset: 0 !important;
  z-index: 1 !important;
  height: auto !important;
  min-height: 2.75rem !important;
  margin: 0 !important;
  padding: 0 !important;
  overflow: visible !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  pointer-events: auto !important;
}}
section[data-testid="stMain"]:has(.ips-users-page)
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-click-table-employees_list)
div[data-testid="stVerticalBlock"]:has(.ips-clean-row-wrap)
> [data-testid="stElementContainer"]:has(.ips-clean-row-select-btn)
+ [data-testid="stElementContainer"] [data-testid="stButton"] > button,
section[data-testid="stMain"]:has(.ips-users-page)
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-click-table-employees_list)
div[data-testid="stVerticalBlock"]:has(.ips-clean-row-wrap)
> [data-testid="stElementContainer"]:has(.ips-clean-row-select-btn)
+ [data-testid="stElementContainer"] .stButton > button {{
  width: 100% !important;
  height: 100% !important;
  min-height: 2.75rem !important;
  margin: 0 !important;
  padding: 0 !important;
  opacity: 0 !important;
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
  color: transparent !important;
  cursor: pointer !important;
}}
section[data-testid="stMain"]:has(.ips-users-page)
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-click-table-employees_list)
div[data-testid="stVerticalBlock"]:has(.ips-clean-row-wrap)
> [data-testid="stElementContainer"]:has(.ips-data-row) {{
  position: absolute !important;
  inset: 0 !important;
  z-index: 2 !important;
  pointer-events: none !important;
  margin: 0 !important;
  padding: 0 !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
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
    """Customers list table stability — call at the top of the customers page render."""
    st.markdown(
        f"""
<style id="ips-customers-module-v1">
.ips-customers-page .ips-data-table-wrap,
.ips-customers-page .ips-data-table-stable .ips-data-table-header,
.ips-customers-page .ips-data-table-stable .ips-data-row {{
  display: grid !important;
  box-sizing: border-box !important;
}}
.ips-customers-page .ips-data-table-html .ips-data-row {{
  display: grid !important;
  min-height: 2.75rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
.ips-customers-page .ips-data-table-html .ips-data-cell {{
  overflow: hidden;
  text-overflow: ellipsis;
}}
</style>
""",
        unsafe_allow_html=True,
    )


def inject_jobs_module_css() -> None:
    """Jobs list table stability — call at the top of the jobs page render."""
    st.markdown(
        f"""
<style id="ips-jobs-module-v5">
.ips-jobs-page .ips-data-table-wrap,
.ips-jobs-page .ips-data-table-stable .ips-data-table-header,
.ips-jobs-page .ips-data-table-stable .ips-data-row {{
  display: grid !important;
  box-sizing: border-box !important;
}}
.ips-jobs-page .ips-data-table-html .ips-data-row {{
  display: grid !important;
  min-height: 2.75rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
.ips-jobs-page .ips-data-table-html .ips-data-cell {{
  overflow: hidden;
  text-overflow: ellipsis;
}}
.ips-jobs-page div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-click-table-jobs_list)
div[data-testid="stVerticalBlock"]:has(.ips-clean-row-wrap) .ips-data-row {{
  display: grid !important;
  min-height: 2.75rem;
  width: 100%;
  min-width: 48rem;
  box-sizing: border-box;
}}
.ips-jobs-page div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-click-table-jobs_list)
div[data-testid="stVerticalBlock"]:has(.ips-clean-row-wrap) .ips-data-row:hover {{
  background: #eef5ff;
}}
.ips-jobs-page div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-click-table-jobs_list)
div[data-testid="stVerticalBlock"]:has(.ips-clean-row-wrap) .ips-data-row.selected {{
  background: #eef5ff;
  border-left: 4px solid #2563eb;
}}
/* Jobs list: invisible full-row select button layered under HTML row */
section[data-testid="stMain"]:has(.ips-jobs-page)
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-click-table-jobs_list)
div[data-testid="stVerticalBlock"]:has(.ips-clean-row-wrap) {{
  position: relative !important;
  min-height: 2.75rem !important;
  margin: 0 !important;
  padding: 0 !important;
}}
section[data-testid="stMain"]:has(.ips-jobs-page)
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-click-table-jobs_list)
div[data-testid="stVerticalBlock"]:has(.ips-clean-row-wrap)
> [data-testid="stElementContainer"]:has(.ips-clean-row-select-btn)
+ [data-testid="stElementContainer"] {{
  position: absolute !important;
  inset: 0 !important;
  z-index: 1 !important;
  height: auto !important;
  min-height: 2.75rem !important;
  margin: 0 !important;
  padding: 0 !important;
  overflow: visible !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  pointer-events: auto !important;
}}
section[data-testid="stMain"]:has(.ips-jobs-page)
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-click-table-jobs_list)
div[data-testid="stVerticalBlock"]:has(.ips-clean-row-wrap)
> [data-testid="stElementContainer"]:has(.ips-clean-row-select-btn)
+ [data-testid="stElementContainer"] [data-testid="stButton"] > button,
section[data-testid="stMain"]:has(.ips-jobs-page)
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-click-table-jobs_list)
div[data-testid="stVerticalBlock"]:has(.ips-clean-row-wrap)
> [data-testid="stElementContainer"]:has(.ips-clean-row-select-btn)
+ [data-testid="stElementContainer"] .stButton > button {{
  width: 100% !important;
  height: 100% !important;
  min-height: 2.75rem !important;
  margin: 0 !important;
  padding: 0 !important;
  opacity: 0 !important;
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
  color: transparent !important;
  cursor: pointer !important;
}}
section[data-testid="stMain"]:has(.ips-jobs-page)
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-click-table-jobs_list)
div[data-testid="stVerticalBlock"]:has(.ips-clean-row-wrap)
> [data-testid="stElementContainer"]:has(.ips-data-row) {{
  position: absolute !important;
  inset: 0 !important;
  z-index: 2 !important;
  pointer-events: none !important;
  margin: 0 !important;
  padding: 0 !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}}
</style>
""",
        unsafe_allow_html=True,
    )


def inject_estimates_module_css() -> None:
    """
    Estimate list/detail table stability — always call at the top of the estimates page render.

    Uses unique class names so other pages cannot affect estimate layout on navigation.
    """
    st.markdown(
        f"""
<style id="ips-estimates-module-v1">
.ips-estimates-page .ips-data-table-wrap,
.ips-estimates-page .ips-data-table-stable .ips-data-table-header,
.ips-estimates-page .ips-data-table-stable .ips-data-row {{
  display: grid !important;
  box-sizing: border-box !important;
}}
.ips-estimates-page .ips-data-table-stable .ips-data-row {{
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
.ips-estimates-page .ips-detail-panel {{
  border-left: 3px solid {PRIMARY};
}}
.ips-estimates-page section[data-testid="stMain"] .stButton > button {{
  min-height: 2.1rem !important;
  max-height: 2.35rem !important;
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

/* Native dataframe list — pointer + selection hint */
[data-testid="stDataFrame"] {{
  border: 1px solid {BORDER} !important;
  border-radius: 12px !important;
  overflow: hidden;
}}
[data-testid="stDataFrame"] [role="grid"] {{
  cursor: pointer;
}}
.ips-data-table-nested .ips-data-row {{
  cursor: default;
}}

/* Modal dialog */
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
