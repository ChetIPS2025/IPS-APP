"""Sidebar availability shell — menu toggle, responsive layout, fallback nav."""

from __future__ import annotations

import json
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

IPS_SIDEBAR_SHELL_KEY = "_ips_sidebar_shell_injected"
IPS_SIDEBAR_NAV_FALLBACK_KEY = "_ips_sidebar_nav_fallback_items"
IPS_SIDEBAR_TOGGLE_REQUEST_KEY = "ips_sidebar_toggle_request"
IPS_SIDEBAR_OPEN_SESSION_KEY = "ips_sidebar_prefer_open"
IPS_SIDEBAR_COLLAPSED_SESSION_KEY = "ips_sidebar_collapsed"
IPS_SIDEBAR_COLLAPSE_AFTER_NAV_KEY = "ips_sidebar_collapse_after_nav"
IPS_SIDEBAR_COLLAPSED_STORAGE_KEY = "ips_sidebar_collapsed"
IPS_SIDEBAR_COLLAPSED_HYDRATED_KEY = "_ips_sidebar_collapsed_hydrated"
IPS_SIDEBAR_DESKTOP_MIN_PX = 900
IPS_SIDEBAR_EXPANDED_WIDTH_PX = 232
IPS_SIDEBAR_COLLAPSED_WIDTH_PX = 48
IPS_SIDEBAR_COLLAPSED_NAV_HEIGHT_PX = 44
IPS_SIDEBAR_COLLAPSED_ICON_PX = 18
IPS_SIDEBAR_COLLAPSED_HEADER_HEIGHT_PX = 56
IPS_SIDEBAR_COLLAPSED_LOGO_PX = 28


def _collapsed_sidebar_selectors() -> str:
    """Match collapsed layout via body class or in-sidebar shell marker."""
    return (
        'body.ips-sidebar-collapsed section[data-testid="stSidebar"], '
        'body.ips-sidebar-collapsed [data-testid="stSidebar"], '
        'section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed), '
        '[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed)'
    )


def is_sidebar_collapsed() -> bool:
    return bool(st.session_state.get(IPS_SIDEBAR_COLLAPSED_SESSION_KEY, False))


def set_sidebar_collapsed(collapsed: bool) -> None:
    st.session_state[IPS_SIDEBAR_COLLAPSED_SESSION_KEY] = bool(collapsed)


def request_sidebar_collapse_after_nav() -> None:
    st.session_state[IPS_SIDEBAR_COLLAPSE_AFTER_NAV_KEY] = True


def apply_pending_sidebar_collapse() -> None:
    """Close the mobile drawer after navigation; desktop collapse state is unchanged."""
    if not st.session_state.pop(IPS_SIDEBAR_COLLAPSE_AFTER_NAV_KEY, False):
        return
    st.session_state[IPS_SIDEBAR_TOGGLE_REQUEST_KEY] = True


def store_sidebar_nav_fallback(items: list[tuple[str, ...]]) -> None:
    """Persist current nav labels for client-side fallback menu."""
    try:
        from app.components.sidebar_nav_icons import nav_icon_for_slug
    except ImportError:
        from components.sidebar_nav_icons import nav_icon_for_slug  # type: ignore
    rows: list[dict[str, str]] = []
    for item in items:
        if len(item) >= 2:
            slug = str(item[0])
            label = str(item[1])
            icon = str(item[2]) if len(item) >= 3 else nav_icon_for_slug(slug)
            rows.append({"slug": slug, "label": label, "icon": icon})
    st.session_state[IPS_SIDEBAR_NAV_FALLBACK_KEY] = rows


def capture_sidebar_collapsed_from_query() -> None:
    """Hydrate collapsed preference from ``?ips_sb=c|e`` (set once by sidebar shell JS)."""
    try:
        raw = st.query_params.get("ips_sb")
    except Exception:
        return
    if not raw:
        return
    if isinstance(raw, list):
        raw = raw[0] if raw else ""
    flag = str(raw or "").strip().lower()
    if flag == "c":
        set_sidebar_collapsed(True)
    elif flag == "e":
        set_sidebar_collapsed(False)
    try:
        del st.query_params["ips_sb"]
    except Exception:
        pass


def ensure_sidebar_collapsed_hydrated() -> None:
    """Load collapsed preference from localStorage into session on fresh Streamlit sessions."""
    capture_sidebar_collapsed_from_query()
    if st.session_state.get(IPS_SIDEBAR_COLLAPSED_HYDRATED_KEY):
        return
    st.session_state[IPS_SIDEBAR_COLLAPSED_HYDRATED_KEY] = True
    if IPS_SIDEBAR_COLLAPSED_SESSION_KEY in st.session_state:
        return
    components.html(
        f"""
<script>
(function () {{
  try {{
    var url = new URL(window.location.href);
    if (url.searchParams.has('ips_sb')) return;
    var collapsed = localStorage.getItem('{IPS_SIDEBAR_COLLAPSED_STORAGE_KEY}') === '1';
    url.searchParams.set('ips_sb', 'c');
    window.location.replace(url.toString());
  }} catch (e) {{}}
}})();
</script>
        """,
        height=0,
    )


def capture_nav_slug_from_query() -> None:
    """Support ``?ips_nav=jobs`` deep links when sidebar navigation is unavailable."""
    try:
        raw = st.query_params.get("ips_nav")
    except Exception:
        return
    if not raw:
        return
    if isinstance(raw, list):
        raw = raw[0] if raw else ""
    slug = str(raw or "").strip()
    if not slug:
        return
    try:
        from app.navigation import set_nav_slug
    except ImportError:
        from navigation import set_nav_slug  # type: ignore
    set_nav_slug(slug)
    try:
        del st.query_params["ips_nav"]
    except Exception:
        pass


def _fallback_nav_json() -> str:
    raw = st.session_state.get(IPS_SIDEBAR_NAV_FALLBACK_KEY)
    rows = raw if isinstance(raw, list) else []
    safe: list[dict[str, str]] = []
    for row in rows:
        if isinstance(row, dict):
            slug = str(row.get("slug") or "").strip()
            label = str(row.get("label") or "").strip()
            icon = str(row.get("icon") or "").strip()
            if slug and label:
                safe.append({"slug": slug, "label": label, "icon": icon or "•"})
    return json.dumps(safe)


def inject_sidebar_shell() -> None:
    """Inject sidebar layout CSS/JS once per authenticated session."""
    collapsed = True
    inject_sidebar_nav_override_css()
    if st.session_state.get(IPS_SIDEBAR_SHELL_KEY):
        inject_sidebar_menu_wire()
        inject_sidebar_nav_align()
        inject_sidebar_layout_state(collapsed)
        if st.session_state.pop(IPS_SIDEBAR_TOGGLE_REQUEST_KEY, False):
            components.html(_toggle_script(collapsed=collapsed, after_nav=True), height=0)
        return
    st.session_state[IPS_SIDEBAR_SHELL_KEY] = True

    if st.session_state.pop(IPS_SIDEBAR_TOGGLE_REQUEST_KEY, False):
        components.html(_toggle_script(collapsed=collapsed, after_nav=True), height=0)

    nav_json = _fallback_nav_json()
    components.html(_shell_script(nav_json), height=0)
    st.markdown(_shell_css(), unsafe_allow_html=True)
    inject_sidebar_menu_wire()
    inject_sidebar_nav_align()
    inject_sidebar_layout_state(collapsed)


def inject_sidebar_nav_override_css() -> None:
    """Inject flat sidebar nav overrides last so they beat global button + theme CSS."""
    st.markdown(_sidebar_nav_override_css(), unsafe_allow_html=True)


def _sidebar_nav_override_css() -> str:
    """Final cascade override for sidebar navigation rows (not button chrome)."""
    return """
<style id="ips-sidebar-nav-override-v8">
section[data-testid="stSidebar"] > div,
section[data-testid="stSidebar"] [data-testid="stSidebarContent"],
section[data-testid="stSidebar"] .block-container {
  position: relative !important;
}
section[data-testid="stSidebar"] .sidebar-section-title {
  text-align: left !important;
  padding-left: 20px !important;
  margin-left: 0 !important;
  margin-right: 0 !important;
}
section[data-testid="stSidebar"]:has(.ips-sidebar-nav-expanded) [class*="st-key-nav_"],
section[data-testid="stSidebar"]:has(.ips-sidebar-nav-expanded) [class*="st-key-nav_"] [data-testid="stElementContainer"] {
  width: 100% !important;
  max-width: 100% !important;
  margin: 0 !important;
  padding: 0 !important;
  display: block !important;
  justify-content: flex-start !important;
}
section[data-testid="stSidebar"] [class*="st-key-nav_"],
section[data-testid="stSidebar"] [class*="st-key-nav_"] [data-testid="stElementContainer"] {
  width: 100% !important;
  max-width: 100% !important;
  margin: 0 !important;
  padding: 0 !important;
}
section[data-testid="stSidebar"] [class*="st-key-nav_"] .stButton,
section[data-testid="stSidebar"] [class*="st-key-nav_"] [data-testid="stButton"] {
  width: 100% !important;
  max-width: 100% !important;
  flex: 1 1 auto !important;
  margin: 0 !important;
}
section[data-testid="stSidebar"] [class*="st-key-nav_"] .stButton > button,
section[data-testid="stSidebar"] [class*="st-key-nav_"] [data-testid="stButton"] > button,
section[data-testid="stSidebar"] [class*="st-key-nav_"] button[data-testid="stBaseButton-secondary"],
section[data-testid="stSidebar"] [class*="st-key-nav_"] button[data-testid="stBaseButton-primary"],
section[data-testid="stSidebar"] [class*="st-key-nav_"] button[data-testid="baseButton-secondary"],
section[data-testid="stSidebar"] [class*="st-key-nav_"] button[data-testid="baseButton-primary"] {
  width: 100% !important;
  max-width: 100% !important;
  min-width: 0 !important;
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
  height: auto !important;
  padding: 10px 14px 10px 22px !important;
  margin: 0 !important;
  border-radius: 8px !important;
  transition: background 0.12s ease, color 0.12s ease !important;
}
section[data-testid="stSidebar"] [class*="st-key-nav_"] .stButton > button p,
section[data-testid="stSidebar"] [class*="st-key-nav_"] [data-testid="stButton"] > button p,
section[data-testid="stSidebar"] [class*="st-key-nav_"] button[data-testid="stBaseButton-secondary"] p,
section[data-testid="stSidebar"] [class*="st-key-nav_"] button[data-testid="stBaseButton-primary"] p,
section[data-testid="stSidebar"] [class*="st-key-nav_"] button[data-testid="stBaseButton-secondary"] span,
section[data-testid="stSidebar"] [class*="st-key-nav_"] button[data-testid="stBaseButton-primary"] span {
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
}
section[data-testid="stSidebar"] [class*="st-key-nav_"] .sidebar-nav-icon {
  width: 20px !important;
  min-width: 20px !important;
  max-width: 20px !important;
  flex: 0 0 20px !important;
  text-align: center !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  line-height: 1 !important;
}
section[data-testid="stSidebar"] [class*="st-key-nav_"] .sidebar-nav-label {
  flex: 1 1 auto !important;
  min-width: 0 !important;
  text-align: left !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  display: block !important;
}
section[data-testid="stSidebar"] [class*="st-key-nav_"] .stButton > button:hover,
section[data-testid="stSidebar"] [class*="st-key-nav_"] [data-testid="stButton"] > button:hover,
section[data-testid="stSidebar"] [class*="st-key-nav_"] button[data-testid="stBaseButton-secondary"]:hover {
  background: #f8fafc !important;
  background-color: #f8fafc !important;
  color: #0f172a !important;
  border: none !important;
  box-shadow: none !important;
}
section[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.sidebar-nav-item.active) + [class*="st-key-nav_"] .stButton > button,
section[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.sidebar-nav-item.active) + [class*="st-key-nav_"] [data-testid="stButton"] > button,
section[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.sidebar-nav-item.active) + [class*="st-key-nav_"] button[data-testid="stBaseButton-secondary"],
section[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.sidebar-nav-item.active) + [class*="st-key-nav_"] button[data-testid="stBaseButton-primary"],
section[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.sidebar-nav-item.active) + [class*="st-key-nav_"] .stButton > button:hover,
section[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.sidebar-nav-item.active) + [class*="st-key-nav_"] [data-testid="stButton"] > button:hover,
section[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.sidebar-nav-item.active) + [class*="st-key-nav_"] button[data-testid="stBaseButton-secondary"]:hover,
section[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.sidebar-nav-item.active) + [class*="st-key-nav_"] button[data-testid="stBaseButton-primary"]:hover {
  background: #2563eb !important;
  background-color: #2563eb !important;
  color: #ffffff !important;
  font-weight: 600 !important;
  border: none !important;
  box-shadow: none !important;
}
section[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.sidebar-nav-item.active) + [class*="st-key-nav_"] .stButton > button p,
section[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.sidebar-nav-item.active) + [class*="st-key-nav_"] [data-testid="stButton"] > button p,
section[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.sidebar-nav-item.active) + [class*="st-key-nav_"] button[data-testid="stBaseButton-secondary"] p,
section[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.sidebar-nav-item.active) + [class*="st-key-nav_"] button[data-testid="stBaseButton-primary"] p {
  color: #ffffff !important;
  font-weight: 600 !important;
}
section[data-testid="stSidebar"] .sidebar-logo-wrap img,
section[data-testid="stSidebar"] .sidebar-logo-wrap [data-testid="stImage"] img,
section[data-testid="stSidebar"] .sidebar-logo-wrap--collapsed img,
section[data-testid="stSidebar"] .sidebar-logo-wrap--collapsed [data-testid="stImage"] img {
  max-width: 90% !important;
  max-height: 110px !important;
  width: auto !important;
  height: auto !important;
  object-fit: contain !important;
}
body.ips-sidebar-collapsed section[data-testid="stSidebar"] .sidebar-logo-wrap img,
body.ips-sidebar-collapsed section[data-testid="stSidebar"] .sidebar-logo-wrap [data-testid="stImage"] img,
body.ips-sidebar-collapsed section[data-testid="stSidebar"] .sidebar-logo-wrap--collapsed img,
body.ips-sidebar-collapsed section[data-testid="stSidebar"] .sidebar-logo-wrap--collapsed [data-testid="stImage"] img {
  max-width: 28px !important;
  max-height: 28px !important;
}
section[data-testid="stSidebar"] .sidebar-logo-wrap [data-testid="stImage"],
section[data-testid="stSidebar"] .sidebar-logo-wrap--collapsed [data-testid="stImage"] {
  display: flex !important;
  justify-content: center !important;
  align-items: center !important;
  width: 100% !important;
  max-width: 100% !important;
  margin: 0 auto !important;
  padding: 0 !important;
}
section[data-testid="stSidebar"] .sidebar-header-brand {
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  justify-content: center !important;
  width: 100% !important;
  text-align: center !important;
  padding-right: 0 !important;
  gap: 0 !important;
}
section[data-testid="stSidebar"] .sidebar-logo-wrap,
section[data-testid="stSidebar"] .sidebar-logo-wrap--collapsed {
  justify-content: center !important;
  align-items: center !important;
  width: 100% !important;
}
body.ips-sidebar-collapsed section[data-testid="stSidebar"] .sidebar-logo-wrap--collapsed,
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed) .sidebar-logo-wrap--collapsed {
  align-items: center !important;
}
body.ips-sidebar-collapsed section[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.sidebar-header--collapsed-rail),
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed) [data-testid="stElementContainer"]:has(.sidebar-header--collapsed-rail) {
  margin: 0 !important;
  padding: 0 !important;
  min-height: 0 !important;
  height: 56px !important;
  max-height: 56px !important;
  overflow: hidden !important;
}
section[data-testid="stSidebar"] .sidebar-logo-tagline {
  font-size: 0.875rem !important;
  font-weight: 500 !important;
  margin: 8px 0 0 !important;
  text-align: center !important;
  width: 100% !important;
  line-height: 1.25 !important;
}
section[data-testid="stSidebar"] [class*="st-key-ips_sidebar_collapse_toggle"] {
  position: static !important;
  top: auto !important;
  right: auto !important;
  z-index: 4 !important;
  width: auto !important;
  margin: 0 !important;
  padding: 0 !important;
}
section[data-testid="stSidebar"] [class*="st-key-ips_sidebar_collapse_toggle"] .stButton > button,
section[data-testid="stSidebar"] [class*="st-key-ips_sidebar_collapse_toggle"] button[data-testid="stBaseButton-secondary"] {
  width: 1.65rem !important;
  min-width: 1.65rem !important;
  max-width: 1.65rem !important;
  height: 1.65rem !important;
  min-height: 1.65rem !important;
  padding: 0 !important;
  margin: 0 !important;
  border-radius: 8px !important;
  border: none !important;
  background: transparent !important;
  color: #64748b !important;
  box-shadow: none !important;
  justify-content: center !important;
}
body.ips-sidebar-collapsed section[data-testid="stSidebar"] [class*="st-key-nav_"] .stButton,
body.ips-sidebar-collapsed section[data-testid="stSidebar"] [class*="st-key-nav_"] [data-testid="stButton"] {
  width: auto !important;
  max-width: none !important;
}
body.ips-sidebar-collapsed section[data-testid="stSidebar"] [class*="st-key-nav_"] .stButton > button,
body.ips-sidebar-collapsed section[data-testid="stSidebar"] [class*="st-key-nav_"] [data-testid="stButton"] > button,
body.ips-sidebar-collapsed section[data-testid="stSidebar"] [class*="st-key-nav_"] button[data-testid="stBaseButton-secondary"],
body.ips-sidebar-collapsed section[data-testid="stSidebar"] [class*="st-key-nav_"] button[data-testid="stBaseButton-primary"] {
  width: 48px !important;
  min-width: 48px !important;
  max-width: 48px !important;
  height: 44px !important;
  min-height: 44px !important;
  padding: 0 !important;
  margin: 4px auto !important;
  border-radius: 10px !important;
  justify-content: center !important;
}
body.ips-sidebar-collapsed section[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.sidebar-nav-item.active) + [class*="st-key-nav_"] .stButton > button,
body.ips-sidebar-collapsed section[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.sidebar-nav-item.active) + [class*="st-key-nav_"] [data-testid="stButton"] > button,
body.ips-sidebar-collapsed section[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.sidebar-nav-item.active) + [class*="st-key-nav_"] button[data-testid="stBaseButton-secondary"],
body.ips-sidebar-collapsed section[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.sidebar-nav-item.active) + [class*="st-key-nav_"] button[data-testid="stBaseButton-primary"],
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed) [data-testid="stElementContainer"]:has(.sidebar-nav-item.active) + [class*="st-key-nav_"] .stButton > button,
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed) [data-testid="stElementContainer"]:has(.sidebar-nav-item.active) + [class*="st-key-nav_"] [data-testid="stButton"] > button,
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed) [data-testid="stElementContainer"]:has(.sidebar-nav-item.active) + [class*="st-key-nav_"] button[data-testid="stBaseButton-secondary"],
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed) [data-testid="stElementContainer"]:has(.sidebar-nav-item.active) + [class*="st-key-nav_"] button[data-testid="stBaseButton-primary"] {
  width: 48px !important;
  min-width: 48px !important;
  max-width: 48px !important;
  height: 44px !important;
  min-height: 44px !important;
  background: #2563eb !important;
  color: #ffffff !important;
}
body.ips-sidebar-collapsed section[data-testid="stSidebar"] [class*="st-key-nav_"] .sidebar-nav-icon,
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed) [class*="st-key-nav_"] .sidebar-nav-icon {
  width: 18px !important;
  min-width: 18px !important;
  max-width: 18px !important;
  flex: 0 0 18px !important;
  font-size: 18px !important;
}
body.ips-sidebar-collapsed section[data-testid="stSidebar"] [class*="st-key-nav_"] .stButton > button p,
body.ips-sidebar-collapsed section[data-testid="stSidebar"] [class*="st-key-nav_"] [data-testid="stButton"] > button p,
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed) [class*="st-key-nav_"] .stButton > button p,
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed) [class*="st-key-nav_"] [data-testid="stButton"] > button p {
  justify-content: center !important;
  text-align: center !important;
  font-size: 18px !important;
  line-height: 1 !important;
  width: auto !important;
  max-width: 100% !important;
  overflow: visible !important;
  gap: 0 !important;
}
body.ips-sidebar-collapsed section[data-testid="stSidebar"]:not(:hover) [class*="st-key-nav_"] [data-testid="stElementContainer"],
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):not(:hover) [class*="st-key-nav_"] [data-testid="stElementContainer"] {
  margin: 0 !important;
  padding: 0 !important;
}
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
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):not(:hover) [class*="st-key-ips_sidebar_collapse_toggle"] {
  display: none !important;
  height: 0 !important;
  min-height: 0 !important;
  max-height: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  overflow: hidden !important;
  visibility: hidden !important;
  border: none !important;
}
body.ips-sidebar-collapsed section[data-testid="stSidebar"]:not(:hover) [class*="st-key-nav_"] .stButton > button,
body.ips-sidebar-collapsed section[data-testid="stSidebar"]:not(:hover) [class*="st-key-nav_"] [data-testid="stButton"] > button,
body.ips-sidebar-collapsed section[data-testid="stSidebar"]:not(:hover) [class*="st-key-nav_"] button[data-testid="stBaseButton-secondary"],
body.ips-sidebar-collapsed section[data-testid="stSidebar"]:not(:hover) [class*="st-key-nav_"] button[data-testid="stBaseButton-primary"],
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):not(:hover) [class*="st-key-nav_"] .stButton > button,
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):not(:hover) [class*="st-key-nav_"] [data-testid="stButton"] > button,
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):not(:hover) [class*="st-key-nav_"] button[data-testid="stBaseButton-secondary"],
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):not(:hover) [class*="st-key-nav_"] button[data-testid="stBaseButton-primary"] {
  width: 48px !important;
  min-width: 48px !important;
  max-width: 48px !important;
  height: 44px !important;
  min-height: 44px !important;
  padding: 0 !important;
  margin: 4px auto !important;
  border-radius: 10px !important;
  justify-content: center !important;
  overflow: visible !important;
}
body.ips-sidebar-collapsed section[data-testid="stSidebar"]:not(:hover) [class*="st-key-nav_"] .sidebar-nav-icon,
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):not(:hover) [class*="st-key-nav_"] .sidebar-nav-icon {
  display: inline-flex !important;
  opacity: 1 !important;
  visibility: visible !important;
  width: 18px !important;
  min-width: 18px !important;
  max-width: 18px !important;
  flex: 0 0 18px !important;
  font-size: 18px !important;
}
body.ips-sidebar-collapsed section[data-testid="stSidebar"]:not(:hover) .sidebar-section-title,
section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):not(:hover) .sidebar-section-title {
  display: none !important;
  height: 0 !important;
  min-height: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  overflow: hidden !important;
}
.sidebar-header--collapsed-rail {
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  width: 100% !important;
  height: 56px !important;
  min-height: 56px !important;
  max-height: 56px !important;
  padding: 0 !important;
  margin: 0 !important;
  overflow: hidden !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}
.sidebar-header--collapsed-rail .sidebar-logo-wrap--collapsed {
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  width: 100% !important;
  height: 56px !important;
  min-height: 56px !important;
  max-height: 56px !important;
  padding: 0 !important;
  margin: 0 !important;
}
.sidebar-logo-icon {
  width: 28px !important;
  height: 28px !important;
  min-width: 28px !important;
  min-height: 28px !important;
  max-width: 28px !important;
  max-height: 28px !important;
  object-fit: contain !important;
  display: block !important;
  margin: 0 auto !important;
}
</style>
"""


def inject_sidebar_layout_state(collapsed: bool) -> None:
    """Sync collapsed body class + localStorage after each render."""
    flag = "1" if collapsed else "0"
    components.html(
        f"""
<script>
(function () {{
  function rootDoc() {{
    try {{ return window.parent && window.parent.document ? window.parent.document : document; }}
    catch (e) {{ return document; }}
  }}
  function apply() {{
    var d = rootDoc();
    if (!d || !d.body) return;
    if ({flag} === '1') d.body.classList.add('ips-sidebar-collapsed');
    else d.body.classList.remove('ips-sidebar-collapsed');
    try {{ localStorage.setItem('{IPS_SIDEBAR_COLLAPSED_STORAGE_KEY}', '{flag}'); }} catch (e2) {{}}
  }}
  apply();
  setTimeout(apply, 40);
  setTimeout(apply, 180);
}})();
</script>
        """,
        height=0,
    )


def inject_sidebar_nav_align() -> None:
    """Split nav button labels into icon + text columns for left-aligned sidebar rows."""
    components.html(
        """
<script>
(function () {
  function rootDoc() {
    try { return window.parent && window.parent.document ? window.parent.document : document; }
    catch (e) { return document; }
  }
  function esc(s) {
    return String(s || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
  function splitNavLabel(text) {
    var raw = String(text || '').trim();
    if (!raw) return null;
    var sep = raw.indexOf('\u2002');
    if (sep < 0) sep = raw.indexOf('  ');
    if (sep >= 0) {
      return { icon: raw.slice(0, sep).trim(), label: raw.slice(sep + 1).trim() };
    }
    var m = raw.match(/^(\\S+)\\s+(.+)$/);
    if (m) return { icon: m[1], label: m[2] };
    return null;
  }
  function align(d) {
    if (!d || !d.body) return;
    if (!d.querySelector('section[data-testid="stSidebar"] [class*="st-key-nav_"] button')) return;
    d.querySelectorAll('section[data-testid="stSidebar"] [class*="st-key-nav_"] button').forEach(function (btn) {
      var p = btn.querySelector('p');
      if (!p) return;
      if (p.querySelector('.sidebar-nav-icon') && p.querySelector('.sidebar-nav-label')) {
        p.dataset.ipsNavSplit = '1';
        return;
      }
      var parts = splitNavLabel(p.textContent || '');
      if (!parts || !parts.label) return;
      p.innerHTML =
        '<span class="sidebar-nav-icon">' + esc(parts.icon) + '</span>' +
        '<span class="sidebar-nav-label">' + esc(parts.label) + '</span>';
      p.dataset.ipsNavSplit = '1';
    });
    d.querySelectorAll('section[data-testid="stSidebar"] [class*="st-key-nav_"] button').forEach(function (btn) {
      var text = '';
      var host = btn.closest('[data-testid="stElementContainer"]');
      var marker = host && host.previousElementSibling;
      if (marker) {
        var navItem = marker.querySelector('.sidebar-nav-item');
        if (navItem) text = navItem.getAttribute('data-nav-label') || '';
      }
      var splitLabel = btn.querySelector('.sidebar-nav-label');
      if (!text && splitLabel) text = String(splitLabel.textContent || '').trim();
      if (!text) text = String(btn.getAttribute('aria-label') || '').trim();
      if (text) btn.setAttribute('title', text);
      else btn.removeAttribute('title');
    });
  }
  function run() { align(rootDoc()); }
  run();
  setTimeout(run, 40);
  setTimeout(run, 180);
})();
</script>
        """,
        height=0,
    )


def inject_sidebar_menu_wire() -> None:
    """Re-bind header menu buttons after each module render."""
    components.html(
        """
<script>
(function () {
  function rootDoc() {
    try { return window.parent && window.parent.document ? window.parent.document : document; }
    catch (e) { return document; }
  }
  function wire(d) {
    if (!window.IPS || !window.IPS.toggleSidebar) return;
    d.querySelectorAll('button.ips-header-menu-btn').forEach(function (btn) {
      if (btn.dataset.ipsMenuWired === '1') return;
      btn.dataset.ipsMenuWired = '1';
      btn.addEventListener('click', function (ev) {
        ev.preventDefault();
        window.IPS.toggleSidebar(true);
      });
    });
  }
  setTimeout(function () { wire(rootDoc()); }, 40);
})();
</script>
        """,
        height=0,
    )


def request_sidebar_toggle() -> None:
    st.session_state[IPS_SIDEBAR_TOGGLE_REQUEST_KEY] = True


def _shell_css() -> str:
    exp = IPS_SIDEBAR_EXPANDED_WIDTH_PX
    col = IPS_SIDEBAR_COLLAPSED_WIDTH_PX
    nav_h = IPS_SIDEBAR_COLLAPSED_NAV_HEIGHT_PX
    icon = IPS_SIDEBAR_COLLAPSED_ICON_PX
    header_h = IPS_SIDEBAR_COLLAPSED_HEADER_HEIGHT_PX
    logo_px = IPS_SIDEBAR_COLLAPSED_LOGO_PX
    mobile_max = IPS_SIDEBAR_DESKTOP_MIN_PX - 1
    collapsed_sel = _collapsed_sidebar_selectors()
    return f"""
<style id="ips-sidebar-shell-v14">
section[data-testid="stSidebar"].app-sidebar,
[data-testid="stSidebar"].app-sidebar {{
  transition: width 0.2s ease, min-width 0.2s ease, max-width 0.2s ease, flex-basis 0.2s ease !important;
  overflow: hidden !important;
}}
.ips-main-header-menu,
button.ips-header-menu-btn {{
  display: none !important;
}}
@media (max-width: {mobile_max}px) {{
  .ips-main-header-menu {{
    display: flex !important;
    align-items: center !important;
    flex: 0 0 auto !important;
    margin-right: 0.5rem !important;
  }}
  button.ips-header-menu-btn {{
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 2.75rem !important;
    height: 2.75rem !important;
    min-width: 2.75rem !important;
    min-height: 2.75rem !important;
    padding: 0 !important;
    border-radius: 10px !important;
    border: 1px solid rgba(37, 99, 235, 0.16) !important;
    background: rgba(255, 255, 255, 0.96) !important;
    color: #2563eb !important;
    cursor: pointer !important;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08) !important;
  }}
  button.ips-header-menu-btn:hover,
  button.ips-header-menu-btn:focus-visible {{
    background: #eff6ff !important;
    border-color: rgba(37, 99, 235, 0.32) !important;
    color: #1d4ed8 !important;
    outline: none !important;
  }}
}}
#ips-sidebar-backdrop {{
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.38);
  z-index: 100001;
}}
#ips-sidebar-backdrop.is-open {{
  display: block;
}}
#ips-nav-fallback {{
  display: none;
  position: fixed;
  left: 0.75rem;
  top: 4.25rem;
  width: min(280px, calc(100vw - 1.5rem));
  max-height: min(70vh, 520px);
  overflow: auto;
  background: #ffffff;
  border: 1px solid #dbe3ef;
  border-radius: 12px;
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.18);
  z-index: 100003;
  padding: 0.65rem;
}}
#ips-nav-fallback.is-open {{
  display: block;
}}
@media (min-width: {IPS_SIDEBAR_DESKTOP_MIN_PX}px) {{
  .stApp [data-testid="stAppViewContainer"] {{
    display: flex !important;
    flex-direction: row !important;
    width: 100% !important;
    max-width: 100% !important;
    overflow-x: clip !important;
  }}
  section[data-testid="stSidebar"],
  [data-testid="stSidebar"] {{
    flex: 0 0 {exp}px !important;
    width: {exp}px !important;
    min-width: {exp}px !important;
    max-width: {exp}px !important;
    transform: none !important;
    visibility: visible !important;
    opacity: 1 !important;
    position: relative !important;
    z-index: 99995 !important;
    overflow: hidden !important;
    transition: flex-basis 0.2s ease, width 0.2s ease, min-width 0.2s ease, max-width 0.2s ease !important;
  }}
  {collapsed_sel} {{
    flex-basis: {col}px !important;
    width: {col}px !important;
    min-width: {col}px !important;
    max-width: {col}px !important;
    padding: 0 !important;
  }}
  {collapsed_sel}:hover {{
    flex-basis: {exp}px !important;
    width: {exp}px !important;
    min-width: {exp}px !important;
    max-width: {exp}px !important;
    box-shadow: 4px 0 18px rgba(15, 23, 42, 0.12) !important;
    z-index: 100010 !important;
  }}
  body.ips-sidebar-collapsed section[data-testid="stSidebar"]:not(:hover) .sidebar-nav-label,
  body.ips-sidebar-collapsed section[data-testid="stSidebar"]:not(:hover) .sidebar-section-title,
  body.ips-sidebar-collapsed section[data-testid="stSidebar"]:not(:hover) .sidebar-logo-tagline,
  body.ips-sidebar-collapsed section[data-testid="stSidebar"]:not(:hover) .sidebar-divider,
  body.ips-sidebar-collapsed section[data-testid="stSidebar"]:not(:hover) .sidebar-footer-label,
  body.ips-sidebar-collapsed section[data-testid="stSidebar"]:not(:hover) .ips-sidebar-user,
  body.ips-sidebar-collapsed section[data-testid="stSidebar"]:not(:hover) .sidebar-version,
  body.ips-sidebar-collapsed section[data-testid="stSidebar"]:not(:hover) .ips-sidebar-brand,
  body.ips-sidebar-collapsed section[data-testid="stSidebar"]:not(:hover) [data-testid="stWidgetLabel"],
  section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):not(:hover) .sidebar-nav-label,
  section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):not(:hover) .sidebar-section-title,
  section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):not(:hover) .sidebar-logo-tagline,
  section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):not(:hover) .sidebar-divider,
  section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):not(:hover) .sidebar-footer-label,
  section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):not(:hover) .ips-sidebar-user,
  section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):not(:hover) .sidebar-version,
  section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):not(:hover) .ips-sidebar-brand,
  section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):not(:hover) [data-testid="stWidgetLabel"] {{
    opacity: 0 !important;
    width: 0 !important;
    max-width: 0 !important;
    overflow: hidden !important;
    white-space: nowrap !important;
    margin: 0 !important;
    padding: 0 !important;
    pointer-events: none !important;
    transition: opacity 0.15s ease !important;
  }}
  body.ips-sidebar-collapsed section[data-testid="stSidebar"]:hover .sidebar-nav-label,
  body.ips-sidebar-collapsed section[data-testid="stSidebar"]:hover .sidebar-section-title,
  body.ips-sidebar-collapsed section[data-testid="stSidebar"]:hover .sidebar-logo-tagline,
  body.ips-sidebar-collapsed section[data-testid="stSidebar"]:hover .sidebar-divider,
  body.ips-sidebar-collapsed section[data-testid="stSidebar"]:hover .sidebar-footer-label,
  body.ips-sidebar-collapsed section[data-testid="stSidebar"]:hover .ips-sidebar-user,
  body.ips-sidebar-collapsed section[data-testid="stSidebar"]:hover .sidebar-version,
  body.ips-sidebar-collapsed section[data-testid="stSidebar"]:hover .ips-sidebar-brand,
  body.ips-sidebar-collapsed section[data-testid="stSidebar"]:hover [data-testid="stWidgetLabel"],
  section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):hover .sidebar-nav-label,
  section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):hover .sidebar-section-title,
  section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):hover .sidebar-logo-tagline,
  section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):hover .sidebar-divider,
  section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):hover .sidebar-footer-label,
  section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):hover .ips-sidebar-user,
  section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):hover .sidebar-version,
  section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):hover .ips-sidebar-brand,
  section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):hover [data-testid="stWidgetLabel"] {{
    opacity: 1 !important;
    width: auto !important;
    max-width: none !important;
    overflow: visible !important;
    pointer-events: auto !important;
  }}
  body.ips-sidebar-collapsed section[data-testid="stSidebar"]:not(:hover) .sidebar-logo-wrap:not(.sidebar-logo-wrap--collapsed) img,
  body.ips-sidebar-collapsed section[data-testid="stSidebar"]:not(:hover) .sidebar-logo-wrap:not(.sidebar-logo-wrap--collapsed) [data-testid="stImage"] img,
  section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):not(:hover) .sidebar-logo-wrap:not(.sidebar-logo-wrap--collapsed) img,
  section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):not(:hover) .sidebar-logo-wrap:not(.sidebar-logo-wrap--collapsed) [data-testid="stImage"] img {{
    max-width: 32px !important;
    max-height: 32px !important;
  }}
  body.ips-sidebar-collapsed section[data-testid="stSidebar"]:hover .sidebar-logo-wrap img,
  body.ips-sidebar-collapsed section[data-testid="stSidebar"]:hover .sidebar-logo-wrap [data-testid="stImage"] img,
  section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):hover .sidebar-logo-wrap img,
  section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):hover .sidebar-logo-wrap [data-testid="stImage"] img {{
    max-width: 90% !important;
    max-height: 110px !important;
  }}
  section[data-testid="stSidebar"] [class*="st-key-ips_sidebar_collapse_toggle"] {{
    display: none !important;
  }}
  body.ips-sidebar-collapsed section[data-testid="stSidebar"]:hover [class*="st-key-nav_"] .stButton,
  body.ips-sidebar-collapsed section[data-testid="stSidebar"]:hover [class*="st-key-nav_"] [data-testid="stButton"],
  section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):hover [class*="st-key-nav_"] .stButton,
  section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):hover [class*="st-key-nav_"] [data-testid="stButton"] {{
    width: 100% !important;
    max-width: 100% !important;
  }}
  body.ips-sidebar-collapsed section[data-testid="stSidebar"]:hover [class*="st-key-nav_"] .stButton > button,
  body.ips-sidebar-collapsed section[data-testid="stSidebar"]:hover [class*="st-key-nav_"] [data-testid="stButton"] > button,
  body.ips-sidebar-collapsed section[data-testid="stSidebar"]:hover [class*="st-key-nav_"] button[data-testid="stBaseButton-secondary"],
  body.ips-sidebar-collapsed section[data-testid="stSidebar"]:hover [class*="st-key-nav_"] button[data-testid="stBaseButton-primary"],
  section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):hover [class*="st-key-nav_"] .stButton > button,
  section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):hover [class*="st-key-nav_"] [data-testid="stButton"] > button,
  section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):hover [class*="st-key-nav_"] button[data-testid="stBaseButton-secondary"],
  section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed):hover [class*="st-key-nav_"] button[data-testid="stBaseButton-primary"] {{
    width: 100% !important;
    min-width: 0 !important;
    max-width: 100% !important;
    height: auto !important;
    min-height: 2.25rem !important;
    padding: 10px 14px 10px 22px !important;
    margin: 0 !important;
    justify-content: flex-start !important;
  }}
  section[data-testid="stSidebar"] > div {{
    width: 100% !important;
    min-width: 0 !important;
    max-height: 100dvh !important;
    overflow-x: hidden !important;
    overflow-y: auto !important;
    display: flex !important;
    flex-direction: column !important;
    padding-top: 0.35rem !important;
    padding-bottom: 0.5rem !important;
  }}
  {collapsed_sel} > div {{
    padding: 0 !important;
  }}
  {collapsed_sel} [data-testid="stSidebarContent"] {{
    padding-left: 0 !important;
    padding-right: 0 !important;
    padding-top: 0 !important;
    padding-bottom: 0 !important;
  }}
  .sidebar-header--collapsed-rail {{
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 100% !important;
    height: {header_h}px !important;
    min-height: {header_h}px !important;
    max-height: {header_h}px !important;
    padding: 0 !important;
    margin: 0 !important;
    overflow: hidden !important;
    flex-shrink: 0 !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
  }}
  .sidebar-header--collapsed-rail .sidebar-logo-wrap--collapsed {{
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 100% !important;
    height: {header_h}px !important;
    min-height: {header_h}px !important;
    max-height: {header_h}px !important;
    padding: 0 !important;
    margin: 0 !important;
  }}
  .sidebar-logo-icon {{
    width: {logo_px}px !important;
    height: {logo_px}px !important;
    min-width: {logo_px}px !important;
    min-height: {logo_px}px !important;
    max-width: {logo_px}px !important;
    max-height: {logo_px}px !important;
    object-fit: contain !important;
    display: block !important;
    margin: 0 auto !important;
    padding: 0 !important;
  }}
  .sidebar-logo-icon-fallback {{
    font-size: 0.62rem !important;
    font-weight: 800 !important;
    color: #2563eb !important;
    letter-spacing: 0.04em !important;
    line-height: 1 !important;
  }}
  {collapsed_sel}:not(:hover) [data-testid="stElementContainer"]:has(.sidebar-header--collapsed-rail) {{
    margin: 0 !important;
    padding: 0 !important;
    min-height: 0 !important;
    height: {header_h}px !important;
    max-height: {header_h}px !important;
    overflow: hidden !important;
  }}
  {collapsed_sel}:not(:hover) .st-key-sidebar_expanded_header_wrap,
  {collapsed_sel}:not(:hover) [data-testid="stVerticalBlock"].st-key-sidebar_expanded_header_wrap,
  {collapsed_sel}:not(:hover) [data-testid="stHorizontalBlock"]:has(.sidebar-header-brand-marker),
  {collapsed_sel}:not(:hover) [data-testid="stElementContainer"]:has(.sidebar-header-expanded-rail-marker),
  {collapsed_sel}:not(:hover) [data-testid="stElementContainer"]:has(.sidebar-header-brand-marker),
  {collapsed_sel}:not(:hover) [data-testid="stElementContainer"]:has(.sidebar-logo-wrap--expanded),
  {collapsed_sel}:not(:hover) [data-testid="stElementContainer"]:has(.sidebar-divider--expanded-rail),
  {collapsed_sel}:not(:hover) [class*="st-key-ips_sidebar_collapse_toggle"] {{
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
  {collapsed_sel}:not(:hover) .sidebar-section-title {{
    display: none !important;
    height: 0 !important;
    min-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: hidden !important;
  }}
  {collapsed_sel}:not(:hover) [class*="st-key-nav_"] .stButton > button,
  {collapsed_sel}:not(:hover) [class*="st-key-nav_"] [data-testid="stButton"] > button,
  {collapsed_sel}:not(:hover) [class*="st-key-nav_"] button[data-testid="stBaseButton-secondary"],
  {collapsed_sel}:not(:hover) [class*="st-key-nav_"] button[data-testid="stBaseButton-primary"] {{
    overflow: visible !important;
  }}
  {collapsed_sel}:not(:hover) [class*="st-key-nav_"] .sidebar-nav-icon {{
    display: inline-flex !important;
    opacity: 1 !important;
    visibility: visible !important;
  }}
  {collapsed_sel}:hover .sidebar-header--collapsed-rail {{
    display: none !important;
    height: 0 !important;
    min-height: 0 !important;
    max-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: hidden !important;
  }}
  {collapsed_sel}:hover [data-testid="stElementContainer"]:has(.sidebar-header--collapsed-rail) {{
    display: none !important;
    height: 0 !important;
    min-height: 0 !important;
    max-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: hidden !important;
  }}
  section[data-testid="stMain"] {{
    flex: 1 1 auto !important;
    min-width: 0 !important;
    width: auto !important;
    max-width: 100% !important;
  }}
  section[data-testid="stSidebar"][aria-expanded="false"],
  [data-testid="stSidebar"][aria-expanded="false"] {{
    flex: 0 0 {col}px !important;
    width: {col}px !important;
    min-width: {col}px !important;
    max-width: {col}px !important;
    display: flex !important;
    transform: none !important;
    margin-left: 0 !important;
    visibility: visible !important;
    opacity: 1 !important;
    pointer-events: auto !important;
  }}
  [data-testid="stSidebarCollapsedControl"],
  button[data-testid="collapsedControl"],
  [data-testid="stSidebarCollapseButton"],
  button[data-testid="stSidebarCollapseButton"] {{
    display: none !important;
  }}
  #ips-sidebar-backdrop {{
    display: none !important;
  }}
  .sidebar-header {{
    position: relative !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 0.35rem 0.45rem 0.25rem !important;
    min-height: 150px !important;
  }}
  .sidebar-header--collapsed-rail {{
    min-height: {header_h}px !important;
    padding: 0 !important;
  }}
  .sidebar-header--expanded-rail {{
    min-height: 0 !important;
  }}
  {collapsed_sel} [data-testid="stSidebarContent"] > [data-testid="stVerticalBlock"] {{
    gap: 0 !important;
  }}
  .sidebar-header-brand {{
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 0 !important;
    padding-right: 0 !important;
    min-width: 0 !important;
    width: 100% !important;
    text-align: center !important;
  }}
  .sidebar-header-top {{
    width: 100% !important;
    position: relative !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
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
    position: absolute !important;
    top: 0.2rem !important;
    right: 0.2rem !important;
    display: flex !important;
    justify-content: flex-end !important;
    align-items: flex-start !important;
    width: auto !important;
    flex: 0 0 auto !important;
    z-index: 2 !important;
  }}
  .sidebar-header--collapsed .sidebar-header-brand {{
    align-items: center !important;
    padding-right: 0 !important;
    padding-top: 0 !important;
  }}
  .sidebar-logo-wrap,
  .sidebar-logo-wrap--collapsed {{
    width: 100% !important;
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
    padding: 0 !important;
    margin: 0 !important;
    border: none !important;
    background: transparent !important;
  }}
  .sidebar-header--collapsed .sidebar-logo-wrap,
  .sidebar-header--collapsed .sidebar-logo-wrap--collapsed {{
    justify-content: center !important;
  }}
  .sidebar-logo-wrap img,
  .sidebar-logo-wrap [data-testid="stImage"] img,
  .sidebar-logo-wrap--collapsed img,
  .sidebar-logo-wrap--collapsed [data-testid="stImage"] img {{
    max-width: 90% !important;
    max-height: 110px !important;
    width: auto !important;
    height: auto !important;
    margin: 0 auto !important;
    object-fit: contain !important;
  }}
  .sidebar-header--collapsed-rail .sidebar-logo-wrap img,
  .sidebar-header--collapsed-rail .sidebar-logo-wrap [data-testid="stImage"] img,
  .sidebar-header--collapsed-rail .sidebar-logo-wrap--collapsed img,
  .sidebar-header--collapsed-rail .sidebar-logo-wrap--collapsed [data-testid="stImage"] img {{
    max-width: {logo_px}px !important;
    max-height: {logo_px}px !important;
  }}
  section[data-testid="stSidebar"] .sidebar-logo-wrap [data-testid="stImage"],
  section[data-testid="stSidebar"] .sidebar-logo-wrap--collapsed [data-testid="stImage"] {{
    width: 100% !important;
    max-width: 100% !important;
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
    background: transparent !important;
    padding: 0 !important;
    margin: 0 auto !important;
  }}
  .sidebar-logo-tagline {{
    font-size: 0.875rem !important;
    font-weight: 500 !important;
    margin: 8px 0 0 !important;
    text-align: center !important;
    width: 100% !important;
    line-height: 1.25 !important;
  }}
  body.ips-sidebar-collapsed .sidebar-section-title,
  body.ips-sidebar-collapsed .sidebar-logo-tagline,
  body.ips-sidebar-collapsed .sidebar-divider,
  section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed) .sidebar-section-title,
  section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed) .sidebar-logo-tagline,
  section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed) .sidebar-divider {{
    display: none !important;
  }}
  .ips-sidebar-nav-scroll,
  .sidebar-nav-scroll {{
    flex: 1 1 auto !important;
    min-height: 0 !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
    padding: 0.2rem 0.35rem !important;
  }}
  body.ips-sidebar-collapsed .ips-sidebar-nav-scroll,
  body.ips-sidebar-collapsed .sidebar-nav-scroll,
  section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed) .ips-sidebar-nav-scroll,
  section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed) .sidebar-nav-scroll {{
    padding: 0 !important;
  }}
  body.ips-sidebar-collapsed .ips-sidebar-footer,
  body.ips-sidebar-collapsed .sidebar-footer,
  section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed) .ips-sidebar-footer,
  section[data-testid="stSidebar"]:has(.ips-sidebar-shell.ips-sidebar-collapsed) .sidebar-footer {{
    padding: 0.2rem 0 0.15rem !important;
  }}
  {collapsed_sel}:not(:hover) [class*="st-key-nav_"] .stButton > button,
  {collapsed_sel}:not(:hover) [class*="st-key-nav_"] [data-testid="stButton"] > button,
  {collapsed_sel}:not(:hover) [class*="st-key-nav_"] button[data-testid="stBaseButton-secondary"],
  {collapsed_sel}:not(:hover) [class*="st-key-nav_"] button[data-testid="stBaseButton-primary"] {{
    width: {col}px !important;
    min-width: {col}px !important;
    max-width: {col}px !important;
    height: {nav_h}px !important;
    min-height: {nav_h}px !important;
    padding: 0 !important;
    margin: 4px auto !important;
    justify-content: center !important;
  }}
  {collapsed_sel}:not(:hover) [class*="st-key-nav_"] .sidebar-nav-icon {{
    width: {icon}px !important;
    min-width: {icon}px !important;
    max-width: {icon}px !important;
    flex: 0 0 {icon}px !important;
    font-size: {icon}px !important;
  }}
  {collapsed_sel}:not(:hover) [class*="st-key-nav_"] .stButton > button p,
  {collapsed_sel}:not(:hover) [class*="st-key-nav_"] [data-testid="stButton"] > button p {{
    justify-content: center !important;
    text-align: center !important;
    font-size: {icon}px !important;
    line-height: 1 !important;
    gap: 0 !important;
  }}
  {collapsed_sel}:not(:hover) [class*="st-key-ips_logout"] .stButton > button,
  {collapsed_sel}:not(:hover) [class*="st-key-ips_logout"] [data-testid="stButton"] > button {{
    width: {col}px !important;
    min-width: {col}px !important;
    max-width: {col}px !important;
    height: {nav_h}px !important;
    min-height: {nav_h}px !important;
    padding: 0 !important;
    margin: 4px auto 0 !important;
    justify-content: center !important;
  }}
  .ips-sidebar-footer,
  .sidebar-footer {{
    flex: 0 0 auto !important;
    margin-top: auto !important;
    padding: 0.45rem 0.35rem 0.3rem !important;
    border-top: 1px solid #e5eaf2 !important;
  }}
  section[data-testid="stSidebar"] [class*="st-key-ips_sidebar_collapse_toggle"] {{
    position: static !important;
    top: auto !important;
    right: auto !important;
    z-index: 3 !important;
    flex: 0 0 auto !important;
    width: auto !important;
    min-width: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
  }}
  section[data-testid="stSidebar"] [class*="st-key-ips_sidebar_collapse_toggle"] .stButton {{
    width: auto !important;
  }}
  section[data-testid="stSidebar"] [class*="st-key-ips_sidebar_collapse_toggle"] .stButton > button {{
    width: 1.65rem !important;
    min-width: 1.65rem !important;
    max-width: 1.65rem !important;
    height: 1.65rem !important;
    min-height: 1.65rem !important;
    padding: 0 !important;
    margin: 0 !important;
    border-radius: 8px !important;
    border: none !important;
    background: transparent !important;
    color: #64748b !important;
    font-size: 0.95rem !important;
    font-weight: 600 !important;
    line-height: 1 !important;
    box-shadow: none !important;
    justify-content: center !important;
  }}
  section[data-testid="stSidebar"] [class*="st-key-ips_sidebar_collapse_toggle"] .stButton > button:hover {{
    background: #f1f5f9 !important;
    color: #2563eb !important;
  }}
}}
@media (max-width: {mobile_max}px) {{
  .sidebar-header--collapsed-rail,
  section[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.sidebar-header--collapsed-rail) {{
    display: none !important;
    height: 0 !important;
    min-height: 0 !important;
    max-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: hidden !important;
  }}
  .st-key-sidebar_expanded_header_wrap,
  [data-testid="stVerticalBlock"].st-key-sidebar_expanded_header_wrap {{
    display: block !important;
    height: auto !important;
    min-height: 0 !important;
    max-height: none !important;
    overflow: visible !important;
  }}
  section[data-testid="stSidebar"],
  [data-testid="stSidebar"] {{
    position: fixed !important;
    left: 0 !important;
    top: 0 !important;
    height: 100dvh !important;
    max-height: 100dvh !important;
    z-index: 100002 !important;
    width: min({exp}px, 92vw) !important;
    min-width: min({exp}px, 92vw) !important;
    max-width: min({exp}px, 92vw) !important;
    transition: transform 0.2s ease-out !important;
    box-shadow: 4px 0 24px rgba(15, 23, 42, 0.18) !important;
    overflow-y: auto !important;
  }}
  section[data-testid="stSidebar"] > div {{
    max-height: 100dvh !important;
    overflow-y: auto !important;
  }}
  section[data-testid="stSidebar"][aria-expanded="false"],
  [data-testid="stSidebar"][aria-expanded="false"] {{
    transform: translateX(-100%) !important;
  }}
  section[data-testid="stSidebar"][aria-expanded="true"],
  [data-testid="stSidebar"][aria-expanded="true"] {{
    transform: translateX(0) !important;
  }}
  section[data-testid="stMain"] {{
    width: 100% !important;
    max-width: 100% !important;
    flex: 1 1 100% !important;
  }}
  [data-testid="stSidebarCollapsedControl"],
  button[data-testid="collapsedControl"],
  [data-testid="stSidebarCollapseButton"],
  button[data-testid="stSidebarCollapseButton"] {{
    display: none !important;
  }}
}}
section[data-testid="stMain"] {{
  position: relative !important;
  z-index: 1 !important;
}}
.stApp [data-testid="stAppViewContainer"] {{
  overflow-x: clip !important;
}}
</style>
"""


def _toggle_script(*, collapsed: bool = False, after_nav: bool = False) -> str:
    collapsed_flag = "true" if collapsed else "false"
    after_nav_flag = "true" if after_nav else "false"
    return f"""
<script>
(function () {{
  try {{
    var top = window.top || window.parent || window;
    if (top.IPS && top.IPS.applySidebarLayout) {{
      top.IPS.applySidebarLayout({{ collapsed: {collapsed_flag}, afterNav: {after_nav_flag} }});
    }} else if (top.IPS && top.IPS.toggleSidebar) {{
      top.IPS.toggleSidebar(true);
    }}
  }} catch (e) {{}}
}})();
</script>
"""


def _shell_script(nav_json: str) -> str:
    nav_literal = nav_json.replace("</", "<\\/")
    return f"""
<script>
(function () {{
  var NAV = {nav_literal};
  var DESKTOP_MIN = {IPS_SIDEBAR_DESKTOP_MIN_PX};
  function rootDoc() {{
    try {{
      return window.parent && window.parent.document ? window.parent.document : document;
    }} catch (e) {{
      return document;
    }}
  }}
  function vpW() {{
    try {{
      var t = window.top || window.parent || window;
      return t.innerWidth || window.innerWidth || 1200;
    }} catch (e2) {{
      return window.innerWidth || 1200;
    }}
  }}
  function isDesktop() {{ return vpW() >= DESKTOP_MIN; }}
  function sidebarEl(d) {{ return d.querySelector('[data-testid="stSidebar"]'); }}
  function toggleBtn(d) {{
    return d.querySelector('button[data-testid="stSidebarCollapseButton"]')
      || d.querySelector('[data-testid="stSidebarCollapseButton"] button')
      || d.querySelector('button[data-testid="collapsedControl"]')
      || d.querySelector('[data-testid="stSidebarCollapsedControl"] button');
  }}
  function clearStreamlitCollapsedStorage() {{
    try {{
      Object.keys(localStorage).forEach(function (key) {{
        if (key.indexOf('stSidebarCollapsed-') === 0) localStorage.removeItem(key);
      }});
    }} catch (e0) {{}}
  }}
  function forceExpandSidebar(side) {{
    if (!side) return;
    var col = {IPS_SIDEBAR_COLLAPSED_WIDTH_PX};
    side.setAttribute('aria-expanded', 'true');
    side.style.setProperty('width', col + 'px', 'important');
    side.style.setProperty('min-width', col + 'px', 'important');
    side.style.setProperty('max-width', col + 'px', 'important');
    side.style.setProperty('flex', '0 0 ' + col + 'px', 'important');
    side.style.setProperty('transform', 'none', 'important');
    side.style.setProperty('visibility', 'visible', 'important');
    side.style.setProperty('opacity', '1', 'important');
    side.style.setProperty('display', 'flex', 'important');
  }}
  function backdropEl(d) {{
    var el = d.getElementById('ips-sidebar-backdrop');
    if (el) return el;
    el = d.createElement('div');
    el.id = 'ips-sidebar-backdrop';
    el.addEventListener('click', function () {{
      var side = sidebarEl(d);
      if (side && side.getAttribute('aria-expanded') === 'true') {{
        var btn = toggleBtn(d);
        if (btn) btn.click();
      }}
      syncBackdrop(d);
    }});
    d.body.appendChild(el);
    return el;
  }}
  function fallbackEl(d) {{
    var el = d.getElementById('ips-nav-fallback');
    if (el) return el;
    el = d.createElement('div');
    el.id = 'ips-nav-fallback';
    el.innerHTML = '<p class="ips-nav-fallback-title">Navigation</p>';
    NAV.forEach(function (item) {{
      var a = d.createElement('a');
      a.href = '?ips_nav=' + encodeURIComponent(item.slug);
      a.textContent = item.label;
      el.appendChild(a);
    }});
    d.body.appendChild(el);
    return el;
  }}
  function syncBackdrop(d) {{
    var bd = backdropEl(d);
    var side = sidebarEl(d);
    if (!side || isDesktop()) {{
      bd.classList.remove('is-open');
      return;
    }}
    if (side.getAttribute('aria-expanded') === 'true') bd.classList.add('is-open');
    else bd.classList.remove('is-open');
  }}
  function readCollapsedPref() {{
    try {{ return localStorage.getItem('{IPS_SIDEBAR_COLLAPSED_STORAGE_KEY}') === '1'; }} catch (e) {{ return false; }}
  }}
  function writeCollapsedPref(collapsed) {{
    try {{ localStorage.setItem('{IPS_SIDEBAR_COLLAPSED_STORAGE_KEY}', collapsed ? '1' : '0'); }} catch (e2) {{}}
  }}
  function setBodyCollapsed(d, collapsed) {{
    if (!d || !d.body) return;
    if (collapsed) d.body.classList.add('ips-sidebar-collapsed');
    else d.body.classList.remove('ips-sidebar-collapsed');
    writeCollapsedPref(collapsed);
  }}
  function ensureDesktopVisible(d) {{
    if (!isDesktop()) return;
    var side = sidebarEl(d);
    if (!side) return;
    if (side.getAttribute('aria-expanded') !== 'true') {{
      clearStreamlitCollapsedStorage();
      var btn = toggleBtn(d);
      if (btn) btn.click();
      side = sidebarEl(d);
      if (side && side.getAttribute('aria-expanded') !== 'true') {{
        forceExpandSidebar(side);
      }}
    }}
    syncBackdrop(d);
  }}
  function restoreMobilePreference(d) {{
    if (isDesktop()) {{
      ensureDesktopVisible(d);
      return;
    }}
    var side = sidebarEl(d);
    if (!side) return;
    var pref = '0';
    try {{ pref = localStorage.getItem('ips_sidebar_open') || '0'; }} catch (e2) {{}}
    var expanded = side.getAttribute('aria-expanded') === 'true';
    var wantOpen = pref === '1';
    if (wantOpen !== expanded) {{
      var btn = toggleBtn(d);
      if (btn) btn.click();
    }}
    syncBackdrop(d);
  }}
  function closeMobileDrawer(d) {{
    if (isDesktop()) return;
    var side = sidebarEl(d);
    if (!side || side.getAttribute('aria-expanded') !== 'true') {{
      syncBackdrop(d);
      return;
    }}
    var btn = toggleBtn(d);
    if (btn) btn.click();
    try {{ localStorage.setItem('ips_sidebar_open', '0'); }} catch (e3) {{}}
    syncBackdrop(d);
  }}
  function tagSidebar(d) {{
    var side = sidebarEl(d);
    if (side) side.classList.add('app-sidebar');
  }}
  function wireMenuButtons(d) {{
    d.querySelectorAll('button.ips-header-menu-btn').forEach(function (btn) {{
      if (btn.dataset.ipsMenuWired === '1') return;
      btn.dataset.ipsMenuWired = '1';
      btn.addEventListener('click', function (ev) {{
        ev.preventDefault();
        window.IPS.toggleSidebar(true);
      }});
    }});
  }}
  function wireNavAutoCollapse(d) {{
    var side = sidebarEl(d);
    if (!side || side.dataset.ipsNavAutoCollapse === '1') return;
    side.dataset.ipsNavAutoCollapse = '1';
    side.addEventListener('click', function (ev) {{
      var btn = ev.target && ev.target.closest ? ev.target.closest('button') : null;
      if (!btn || !side.contains(btn)) return;
      if (btn.closest('.sidebar-collapse-btn') || btn.closest('[class*="st-key-ips_sidebar_collapse_toggle"]')) return;
      var txt = (btn.textContent || '').toLowerCase();
      if (txt.indexOf('log out') >= 0 || txt.indexOf('logout') >= 0) return;
      var testId = btn.getAttribute('data-testid') || '';
      if (testId === 'collapsedControl' || testId === 'stSidebarCollapseButton') return;
      setTimeout(function () {{ window.IPS.collapseAfterNav(); }}, 60);
    }});
  }}
  window.IPS = window.IPS || {{}};
  window.IPS.applySidebarLayout = function (opts) {{
    var d = rootDoc();
    opts = opts || {{}};
    if (isDesktop()) {{
      ensureDesktopVisible(d);
      setBodyCollapsed(d, true);
      tagSidebar(d);
    }} else if (opts.afterNav) {{
      closeMobileDrawer(d);
    }}
    syncBackdrop(d);
  }};
  window.IPS.setSidebarCollapsed = function (collapsed) {{
    var d = rootDoc();
    if (!isDesktop()) return;
    ensureDesktopVisible(d);
    setBodyCollapsed(d, true);
    tagSidebar(d);
  }};
  window.IPS.collapseAfterNav = function () {{
    var d = rootDoc();
    if (isDesktop()) {{
      syncBackdrop(d);
      return;
    }}
    closeMobileDrawer(d);
  }};
  window.IPS.toggleSidebar = function () {{
    var d = rootDoc();
    var side = sidebarEl(d);
    if (!side) {{
      var fb = fallbackEl(d);
      fb.classList.toggle('is-open');
      return;
    }}
    if (isDesktop()) {{
      ensureDesktopVisible(d);
      tagSidebar(d);
      return;
    }}
    var btn = toggleBtn(d);
    var expanded = side.getAttribute('aria-expanded') === 'true';
    if (btn) btn.click();
    else side.setAttribute('aria-expanded', expanded ? 'false' : 'true');
    try {{ localStorage.setItem('ips_sidebar_open', expanded ? '0' : '1'); }} catch (e3) {{}}
    syncBackdrop(d);
  }};
  window.IPS.showFallbackNav = function () {{
    fallbackEl(rootDoc()).classList.add('is-open');
  }};
  function boot() {{
    var d = rootDoc();
    wireMenuButtons(d);
    wireNavAutoCollapse(d);
    if (isDesktop()) {{
      ensureDesktopVisible(d);
      setBodyCollapsed(d, true);
      tagSidebar(d);
    }} else restoreMobilePreference(d);
    syncBackdrop(d);
    if (!sidebarEl(d) && NAV.length) window.IPS.showFallbackNav();
  }}
  setTimeout(boot, 80);
  setTimeout(boot, 400);
  setTimeout(boot, 1200);
  try {{
    window.addEventListener('resize', function () {{
      setTimeout(boot, 120);
    }});
  }} catch (e4) {{}}
}})();
</script>
"""
