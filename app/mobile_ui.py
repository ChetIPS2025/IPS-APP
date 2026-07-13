"""App-wide responsive CSS for phones and narrow viewports (IPS field theme)."""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

IPS_GLOBAL_MOBILE_CSS_KEY = "ips_global_mobile_css_injected"
IPS_VIEWPORT_NARROW_KEY = "ips_viewport_narrow"
_VP_SCRIPT_SENT_KEY = "_ips_viewport_detect_script_sent"


def ensure_narrow_viewport_detected() -> None:
    """
    One-time client width hint via ?ips_vp=0|1 so Python can branch layout.

    Call from pages that need true mobile vs desktop defaults (e.g. Asset Database).
    Safe to call multiple times; redirects at most once per session before narrow is known.
    """
    if IPS_VIEWPORT_NARROW_KEY in st.session_state:
        return
    try:
        if "ips_vp" in st.query_params:
            raw = st.query_params.get("ips_vp", "0")
            if isinstance(raw, list):
                raw = raw[0] if raw else "0"
            st.session_state[IPS_VIEWPORT_NARROW_KEY] = str(raw).strip() == "1"
            try:
                del st.query_params["ips_vp"]
            except Exception:
                pass
            return
    except Exception:
        pass

    if st.session_state.get(_VP_SCRIPT_SENT_KEY):
        return
    st.session_state[_VP_SCRIPT_SENT_KEY] = True
    components.html(
        """
<script>
(function () {
  try {
    var top = window.top || window;
    var u = new URL(top.location.href);
    if (u.searchParams.get("ips_vp") != null) return;
    var w = top.innerWidth || window.innerWidth || 1200;
    u.searchParams.set("ips_vp", w <= 900 ? "1" : "0");
    top.location.replace(u.toString());
  } catch (e) {}
})();
</script>
        """,
        height=0,
    )

# Main content only — sidebar nav styling stays in sidebar_shell.py
_IPS_GLOBAL_MOBILE_CSS = """
<style>
/* Sidebar chrome only; width tokens live in sidebar_shell (232 expanded / 48 collapsed) */
[data-testid="stSidebar"],
section[data-testid="stSidebar"],
.stSidebar {
  background-color: #ffffff !important;
  background: #ffffff !important;
  border-right: 1px solid #E5EAF2 !important;
  color: #111827 !important;
}
@media (min-width: 900px) {
  body:not(.ips-sidebar-collapsed) [data-testid="stSidebar"],
  body:not(.ips-sidebar-collapsed) section[data-testid="stSidebar"],
  body:not(.ips-sidebar-collapsed) .stSidebar {
    width: 232px !important;
    min-width: 232px !important;
    max-width: 232px !important;
  }
  body.ips-sidebar-collapsed [data-testid="stSidebar"],
  body.ips-sidebar-collapsed section[data-testid="stSidebar"],
  body.ips-sidebar-collapsed .stSidebar {
    width: 48px !important;
    min-width: 48px !important;
    max-width: 48px !important;
  }
}

@media (max-width: 900px) {
  [data-testid="stMain"] div[data-testid="stHorizontalBlock"],
  [data-testid="stMain"] main div[data-testid="stHorizontalBlock"] {
    flex-direction: column !important;
    flex-wrap: nowrap !important;
    align-items: stretch !important;
    gap: 0.55rem !important;
  }
  [data-testid="stMain"] div[data-testid="stHorizontalBlock"] > div[data-testid="column"],
  [data-testid="stMain"] main div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
    width: 100% !important;
    min-width: 0 !important;
    max-width: 100% !important;
  }
  [data-testid="stMain"] .block-container,
  [data-testid="stMain"] main .block-container {
    padding-left: max(0.75rem, env(safe-area-inset-left)) !important;
    padding-right: max(0.75rem, env(safe-area-inset-right)) !important;
    padding-top: 0.15rem !important;
  }
  /* Main buttons: match IPS shell tokens (slightly taller touch target, same rhythm) */
  [data-testid="stMain"] .stButton > button,
  [data-testid="stMain"] main .stButton > button,
  [data-testid="stMain"] [data-testid="stDownloadButton"] button,
  [data-testid="stMain"] [data-testid="stFormSubmitButton"] button {
    min-height: 3rem !important;
    padding: 0.45rem 0.85rem !important;
    font-size: 0.875rem !important;
    font-weight: 600 !important;
    border-radius: 10px !important;
    line-height: 1.25 !important;
    box-sizing: border-box !important;
  }
  [data-testid="stMain"] .stButton > button p,
  [data-testid="stMain"] main .stButton > button p,
  [data-testid="stMain"] [data-testid="stDownloadButton"] button p,
  [data-testid="stMain"] [data-testid="stFormSubmitButton"] button p {
    white-space: nowrap !important;
    overflow: visible !important;
    text-overflow: clip !important;
    margin: 0 !important;
  }
  [data-testid="stMain"] .stLinkButton > a,
  [data-testid="stMain"] main .stLinkButton > a {
    min-height: 3rem !important;
    padding: 0.45rem 0.85rem !important;
    font-size: 0.875rem !important;
    font-weight: 600 !important;
    border-radius: 10px !important;
    white-space: nowrap !important;
    box-sizing: border-box !important;
  }
  [data-testid="stMain"] [data-testid="stDataFrame"],
  [data-testid="stMain"] main [data-testid="stDataFrame"] {
    max-width: 100%;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }
  [data-testid="stMain"] [data-testid="stDataFrame"] [data-testid="stTable"] {
    font-size: 0.88rem;
  }
  /* Align with ips_app_shell control rhythm; slightly taller for touch */
  [data-testid="stMain"] div[data-testid="stTextInput"] input,
  [data-testid="stMain"] div[data-testid="stNumberInput"] input,
  [data-testid="stMain"] div[data-testid="stTextArea"] textarea {
    min-height: 2.1rem !important;
    font-size: 0.875rem !important;
    padding: 0.28rem 0.5rem !important;
  }
  [data-testid="stMain"] div[data-testid="stSelectbox"] [data-baseweb="select"] > div,
  [data-testid="stMain"] [data-testid="stMultiSelect"] [data-baseweb="select"] > div {
    min-height: 2.2rem !important;
    font-size: 0.875rem !important;
  }
  [data-testid="stMain"] [data-testid="stTabs"] [role="tablist"] {
    flex-wrap: wrap !important;
    gap: 0.35rem !important;
    row-gap: 0.4rem !important;
  }
  [data-testid="stMain"] [data-testid="stTabs"] [role="tab"] {
    font-size: 0.88rem !important;
    padding: 0.45rem 0.65rem !important;
    min-height: 2.6rem !important;
    white-space: normal !important;
    line-height: 1.25 !important;
  }
  [data-testid="stMain"] [data-testid="stExpander"] summary {
    min-height: 2.75rem !important;
    padding: 0.5rem 0.65rem !important;
    font-size: 0.95rem !important;
  }
  /* Primary actions: full width when stacked */
  [data-testid="stMain"] div[data-testid="column"] .stButton > button[kind="primary"],
  [data-testid="stMain"] div[data-testid="column"] .stButton > button[data-testid="baseButton-primary"] {
    width: 100% !important;
  }
  /* CRUD toolbars (Customers, etc.): stack and full-width buttons */
  div[data-testid="stHorizontalBlock"]:has(.ips-crud-toolbar-root) {
    flex-direction: column !important;
    align-items: stretch !important;
    gap: 0.5rem !important;
  }
  div[data-testid="stHorizontalBlock"]:has(.ips-crud-toolbar-root) > div[data-testid="column"] {
    width: 100% !important;
    max-width: 100% !important;
  }
  div[data-testid="stHorizontalBlock"]:has(.ips-crud-toolbar-root) .stButton > button {
    width: 100% !important;
    min-height: 2.5rem !important;
  }
  /* Asset Database: filter rows stack */
  div[data-testid="stHorizontalBlock"]:has(.ips-adb-filter-row) {
    flex-direction: column !important;
    gap: 0.5rem !important;
  }
  div[data-testid="stHorizontalBlock"]:has(.ips-adb-filter-row2) {
    flex-direction: column !important;
    gap: 0.45rem !important;
  }
  /* Estimates: top action rows */
  div[data-testid="stHorizontalBlock"]:has(.ips-estimate-topbar) {
    flex-direction: column !important;
    gap: 0.5rem !important;
  }
  div[data-testid="stHorizontalBlock"]:has(.ips-estimate-topbar) .stButton > button {
    width: 100% !important;
  }
  /* Table action bars (selectable grids) */
  div[data-testid="stHorizontalBlock"]:has(.ips-ta-bar-root) {
    flex-direction: column !important;
    align-items: stretch !important;
    gap: 0.45rem !important;
  }
  div[data-testid="stHorizontalBlock"]:has(.ips-ta-bar-root) .stButton > button {
    width: 100% !important;
    min-height: 2.45rem !important;
  }
  [data-testid="stMain"] [data-testid="stMetricValue"] {
    font-size: 1.1rem !important;
  }
  /* Sidebar toggle: thumb-friendly on phones */
  button[data-testid="stSidebarCollapseButton"],
  button[data-testid="collapsedControl"] {
    min-width: 2.75rem !important;
    min-height: 2.75rem !important;
    border-radius: 10px !important;
  }
  [data-testid="stMain"] iframe[title="stMarkdown"],
  [data-testid="stMain"] iframe[src*="data:application/pdf"] {
    max-height: min(70vh, 560px) !important;
    min-height: 240px !important;
  }
}

/* Phones: overlay sidebar handled by sidebar_shell.py (<=899px). */
@media (max-width: 768px) {
  html, body, [data-testid="stAppViewContainer"] {
    max-width: 100vw;
    overflow-x: hidden;
  }
  .main, .block-container, section.main > div {
    width: 100% !important;
    max-width: 100% !important;
    margin-left: 0 !important;
    padding-left: 12px !important;
    padding-right: 12px !important;
    box-sizing: border-box !important;
  }
  .dashboard-container,
  .content-container,
  .page-container,
  .card,
  .metric-card,
  .dashboard-card {
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
    box-sizing: border-box;
  }
  .stColumns,
  [data-testid="column"] {
    width: 100% !important;
    min-width: 0 !important;
    max-width: 100% !important;
    flex: 1 1 100% !important;
  }
  .responsive-table,
  .table-wrapper,
  div[data-testid="stDataFrame"],
  div[data-testid="stTable"] {
    width: 100% !important;
    max-width: 100% !important;
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch;
  }
  img, svg {
    max-width: 100%;
    height: auto;
  }
  button {
    max-width: 100%;
  }

  body.ips-authed-app [data-testid="stAppViewContainer"],
  .stApp [data-testid="stAppViewContainer"] {
    margin-left: 0 !important;
    padding-left: 0 !important;
    width: 100% !important;
    max-width: 100vw !important;
    display: block !important;
    overflow-x: hidden !important;
    box-sizing: border-box !important;
  }
  body.ips-authed-app [data-testid="stHeader"],
  .stApp [data-testid="stHeader"] {
    margin-left: 0 !important;
    width: 100% !important;
    max-width: 100vw !important;
  }
  section[data-testid="stMain"] {
    margin-left: 0 !important;
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
    flex: 1 1 100% !important;
    overflow-x: hidden !important;
  }
  section[data-testid="stMain"] > div {
    max-width: 100% !important;
    margin-left: 0 !important;
    margin-right: 0 !important;
    min-width: 0 !important;
  }
  section[data-testid="stMain"] .block-container,
  [data-testid="stMain"] .block-container {
    padding-left: max(12px, env(safe-area-inset-left)) !important;
    padding-right: max(12px, env(safe-area-inset-right)) !important;
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
    box-sizing: border-box !important;
  }
  section[data-testid="stMain"]:has(.ips-page-shell-marker) [data-testid="stVerticalBlock"] > div {
    padding-left: 12px !important;
    padding-right: 12px !important;
  }
  .ips-main-header {
    padding-left: 12px !important;
    padding-right: 12px !important;
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
    box-sizing: border-box !important;
  }
  .ips-main-header-logo {
    max-width: min(240px, 72vw) !important;
    height: auto !important;
    max-height: 34px !important;
  }
  .ips-page-content {
    padding: 12px !important;
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
    box-sizing: border-box !important;
  }
  .ips-dash-jobs-table-scroll,
  .ips-dash-est-table-scroll,
  .st-key-pricing_guide_table_wrap,
  .st-key-users_table_wrap,
  .st-key-jobs_table_wrap,
  .st-key-inventory_table_wrap,
  .st-key-assets_table_wrap,
  .st-key-dashboard_active_jobs_table,
  .st-key-dashboard_estimates_waiting_table {
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch;
    box-sizing: border-box !important;
  }
  [data-testid="stMain"] div[data-testid="stHorizontalBlock"] {
    max-width: 100% !important;
    min-width: 0 !important;
    flex-wrap: wrap !important;
  }
  [data-testid="stMain"] div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
    flex: 1 1 100% !important;
  }

  .stApp .stButton > button,
  .stApp [data-testid="stDownloadButton"] button,
  .stApp [data-testid="stFormSubmitButton"] button {
    padding: 14px 16px !important;
    font-size: 16px !important;
    font-weight: 600 !important;
    border-radius: 10px !important;
    min-height: 48px !important;
    box-sizing: border-box !important;
  }

  .ips-resource-grid,
  [data-testid="stMain"] div[data-testid="stHorizontalBlock"]:has(.ips-resource-tile-grid-marker) {
    display: flex !important;
    flex-direction: column !important;
    align-items: stretch !important;
    gap: 0.5rem !important;
  }
  .ips-resource-grid > div,
  [data-testid="stMain"] div[data-testid="stHorizontalBlock"]:has(.ips-resource-tile-grid-marker) > div[data-testid="column"] {
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
  }

  [data-testid="stMain"] div[data-testid="stTextInput"],
  [data-testid="stMain"] div[data-testid="stNumberInput"],
  [data-testid="stMain"] div[data-testid="stTextArea"],
  [data-testid="stMain"] div[data-testid="stSelectbox"],
  [data-testid="stMain"] div[data-testid="stMultiSelect"] {
    width: 100% !important;
    max-width: 100% !important;
  }
  [data-testid="stMain"] div[data-testid="stTextInput"] input,
  [data-testid="stMain"] div[data-testid="stNumberInput"] input,
  [data-testid="stMain"] div[data-testid="stTextArea"] textarea {
    width: 100% !important;
    box-sizing: border-box !important;
  }
}
</style>
"""

IPS_SIDEBAR_MOBILE_COLLAPSE_KEY = "_ips_sidebar_mobile_collapse_script"


def inject_sidebar_mobile_auto_collapse_once() -> None:
    """
    First load on narrow viewports: collapse the Streamlit sidebar so main content is visible.
    User can still open it via the header control (stSidebarCollapseButton).
    """
    if st.session_state.get(IPS_SIDEBAR_MOBILE_COLLAPSE_KEY):
        return
    st.session_state[IPS_SIDEBAR_MOBILE_COLLAPSE_KEY] = True
    components.html(
        """
<script>
(function () {
  function rootDoc() {
    try {
      return window.parent && window.parent.document ? window.parent.document : document;
    } catch (e) {
      return document;
    }
  }
  function vpW() {
    try {
      var t = window.top || window.parent || window;
      return t.innerWidth || 1200;
    } catch (e2) {
      return window.innerWidth || 1200;
    }
  }
  function run() {
    if (vpW() >= 900) return;
    if (sessionStorage.getItem("ips_mobile_sidebar_init") === "1") return;
    var d = rootDoc();
    var side = d.querySelector('[data-testid="stSidebar"]');
    if (!side) {
      sessionStorage.setItem("ips_mobile_sidebar_init", "1");
      return;
    }
    if (side.getAttribute("aria-expanded") !== "true") {
      sessionStorage.setItem("ips_mobile_sidebar_init", "1");
      return;
    }
    var btn = d.querySelector('button[data-testid="stSidebarCollapseButton"]')
      || d.querySelector('[data-testid="stSidebarCollapseButton"] button')
      || d.querySelector('button[data-testid="collapsedControl"]');
    if (btn) {
      try {
        btn.click();
      } catch (e3) {}
    }
    side = d.querySelector('[data-testid="stSidebar"]');
    if (side && side.getAttribute("aria-expanded") === "true") {
      side.setAttribute("aria-expanded", "false");
      side.style.setProperty("transform", "translateX(-100%)", "important");
      var bd = d.getElementById("ips-sidebar-backdrop");
      if (bd) bd.classList.remove("is-open");
    }
    try {
      d.body.classList.remove("ips-sidebar-collapsed");
    } catch (e4) {}
    sessionStorage.setItem("ips_mobile_sidebar_init", "1");
  }
  setTimeout(run, 60);
  setTimeout(run, 320);
  setTimeout(run, 800);
})();
</script>
        """,
        height=0,
    )


def inject_ips_global_mobile_css() -> None:
    """Inject once per session; safe to call from multiple pages."""
    if st.session_state.get(IPS_GLOBAL_MOBILE_CSS_KEY):
        return
    st.session_state[IPS_GLOBAL_MOBILE_CSS_KEY] = True
    st.markdown(_IPS_GLOBAL_MOBILE_CSS, unsafe_allow_html=True)
