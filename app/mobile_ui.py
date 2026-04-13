"""App-wide responsive CSS for phones and narrow viewports (IPS dark theme preserved)."""

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

# Main content only — sidebar nav styling stays in ui.py
_IPS_GLOBAL_MOBILE_CSS = """
<style>
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
    padding-top: 0.35rem !important;
  }
  [data-testid="stMain"] .stButton > button,
  [data-testid="stMain"] main .stButton > button {
    min-height: 2.85rem !important;
    padding: 0.55rem 0.9rem !important;
    font-size: 1rem !important;
    border-radius: 10px !important;
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
  [data-testid="stMain"] div[data-testid="stTextInput"] input,
  [data-testid="stMain"] div[data-testid="stNumberInput"] input,
  [data-testid="stMain"] div[data-testid="stTextArea"] textarea {
    min-height: 2.75rem !important;
    font-size: 1rem !important;
    padding: 0.45rem 0.65rem !important;
  }
  [data-testid="stMain"] [data-baseweb="select"] > div,
  [data-testid="stMain"] div[data-testid="stSelectbox"] [data-baseweb="select"] > div {
    min-height: 2.75rem !important;
    font-size: 1rem !important;
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
    min-height: 2.85rem !important;
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
    min-height: 2.8rem !important;
  }
  [data-testid="stMain"] [data-testid="stMetricValue"] {
    font-size: 1.1rem !important;
  }
  [data-testid="stMain"] iframe[title="stMarkdown"],
  [data-testid="stMain"] iframe[src*="data:application/pdf"] {
    max-height: min(70vh, 560px) !important;
    min-height: 240px !important;
  }
}
</style>
"""


def inject_ips_global_mobile_css() -> None:
    """Inject once per session; safe to call from multiple pages."""
    if st.session_state.get(IPS_GLOBAL_MOBILE_CSS_KEY):
        return
    st.session_state[IPS_GLOBAL_MOBILE_CSS_KEY] = True
    st.markdown(_IPS_GLOBAL_MOBILE_CSS, unsafe_allow_html=True)
