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
IPS_SIDEBAR_DESKTOP_MIN_PX = 900
IPS_SIDEBAR_EXPANDED_WIDTH_PX = 240
IPS_SIDEBAR_COLLAPSED_WIDTH_PX = 72


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
    collapsed = is_sidebar_collapsed()
    if st.session_state.get(IPS_SIDEBAR_SHELL_KEY):
        inject_sidebar_menu_wire()
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
    inject_sidebar_layout_state(collapsed)


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
  setTimeout(apply, 20);
  setTimeout(apply, 180);
}})();
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
    mobile_max = IPS_SIDEBAR_DESKTOP_MIN_PX - 1
    return f"""
<style id="ips-sidebar-shell-v4">
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
    transition: flex-basis 0.18s ease, width 0.18s ease, min-width 0.18s ease, max-width 0.18s ease !important;
  }}
  body.ips-sidebar-collapsed section[data-testid="stSidebar"],
  body.ips-sidebar-collapsed [data-testid="stSidebar"] {{
    flex-basis: {col}px !important;
    width: {col}px !important;
    min-width: {col}px !important;
    max-width: {col}px !important;
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
  section[data-testid="stMain"] {{
    flex: 1 1 auto !important;
    min-width: 0 !important;
    width: auto !important;
    max-width: 100% !important;
  }}
  section[data-testid="stSidebar"][aria-expanded="false"],
  [data-testid="stSidebar"][aria-expanded="false"] {{
    transform: none !important;
    margin-left: 0 !important;
    visibility: visible !important;
  }}
  [data-testid="stSidebarCollapsedControl"],
  button[data-testid="collapsedControl"] {{
    display: none !important;
  }}
  #ips-sidebar-backdrop {{
    display: none !important;
  }}
  .sidebar-header {{
    display: flex !important;
    align-items: flex-start !important;
    justify-content: space-between !important;
    gap: 0.35rem !important;
    padding: 0.35rem 0.55rem 0.25rem !important;
  }}
  .sidebar-header--collapsed {{
    flex-direction: column !important;
    align-items: center !important;
    padding: 0.35rem 0.25rem 0.2rem !important;
  }}
  .sidebar-logo-wrap--collapsed {{
    width: 100% !important;
    display: flex !important;
    justify-content: center !important;
    padding: 0 !important;
    margin: 0 !important;
    border: none !important;
  }}
  .sidebar-logo-wrap--collapsed img,
  .sidebar-logo-wrap--collapsed [data-testid="stImage"] img {{
    max-height: 28px !important;
    width: auto !important;
    margin: 0 auto !important;
  }}
  body.ips-sidebar-collapsed .sidebar-section-title,
  body.ips-sidebar-collapsed .sidebar-logo-tagline,
  body.ips-sidebar-collapsed .sidebar-divider {{
    display: none !important;
  }}
  .ips-sidebar-nav-scroll,
  .sidebar-nav-scroll {{
    flex: 1 1 auto !important;
    min-height: 0 !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
    padding: 0.15rem 0.45rem !important;
  }}
  .ips-sidebar-footer,
  .sidebar-footer {{
    flex: 0 0 auto !important;
    margin-top: auto !important;
    padding: 0.5rem 0.45rem 0.35rem !important;
    border-top: 1px solid #e5eaf2 !important;
  }}
  section[data-testid="stSidebar"] [class*="st-key-ips_sidebar_collapse_toggle"] {{
    flex: 0 0 auto !important;
    width: auto !important;
    min-width: 0 !important;
  }}
  section[data-testid="stSidebar"] [class*="st-key-ips_sidebar_collapse_toggle"] .stButton {{
    width: auto !important;
  }}
  section[data-testid="stSidebar"] [class*="st-key-ips_sidebar_collapse_toggle"] .stButton > button {{
    width: 1.75rem !important;
    min-width: 1.75rem !important;
    max-width: 1.75rem !important;
    height: 1.75rem !important;
    min-height: 1.75rem !important;
    padding: 0 !important;
    margin: 0 !important;
    border-radius: 8px !important;
    border: none !important;
    background: transparent !important;
    color: #64748b !important;
    font-size: 1rem !important;
    font-weight: 600 !important;
    line-height: 1 !important;
    box-shadow: none !important;
    justify-content: center !important;
  }}
  section[data-testid="stSidebar"] [class*="st-key-ips_sidebar_collapse_toggle"] .stButton > button:hover {{
    background: #eff6ff !important;
    color: #2563eb !important;
  }}
  body.ips-sidebar-collapsed section[data-testid="stSidebar"] .sidebar-header--collapsed [class*="st-key-ips_sidebar_collapse_toggle"] {{
    width: 100% !important;
  }}
  body.ips-sidebar-collapsed section[data-testid="stSidebar"] .sidebar-header--collapsed [class*="st-key-ips_sidebar_collapse_toggle"] .stButton > button {{
    width: 100% !important;
    max-width: 100% !important;
  }}
}}
@media (max-width: {mobile_max}px) {{
  section[data-testid="stSidebar"],
  [data-testid="stSidebar"] {{
    position: fixed !important;
    left: 0 !important;
    top: 0 !important;
    height: 100dvh !important;
    max-height: 100dvh !important;
    z-index: 100002 !important;
    width: min(240px, 92vw) !important;
    min-width: min(240px, 92vw) !important;
    max-width: min(240px, 92vw) !important;
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
  button[data-testid="collapsedControl"] {{
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
  function toggleBtn(d) {{ return d.querySelector('button[data-testid="collapsedControl"]'); }}
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
      var btn = toggleBtn(d);
      if (btn) btn.click();
    }}
    syncBackdrop(d);
  }}
  function restoreDesktopCollapsed(d) {{
    if (!isDesktop()) return;
    ensureDesktopVisible(d);
    setBodyCollapsed(d, readCollapsedPref());
  }}
  function restoreMobilePreference(d) {{
    if (isDesktop()) {{
      restoreDesktopCollapsed(d);
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
      if (btn.getAttribute('data-testid') === 'collapsedControl') return;
      setTimeout(function () {{ window.IPS.collapseAfterNav(); }}, 60);
    }});
  }}
  window.IPS = window.IPS || {{}};
  window.IPS.applySidebarLayout = function (opts) {{
    var d = rootDoc();
    opts = opts || {{}};
    if (isDesktop()) {{
      ensureDesktopVisible(d);
      if (typeof opts.collapsed === 'boolean') setBodyCollapsed(d, opts.collapsed);
      else setBodyCollapsed(d, readCollapsedPref());
    }} else if (opts.afterNav) {{
      closeMobileDrawer(d);
    }}
    syncBackdrop(d);
  }};
  window.IPS.setSidebarCollapsed = function (collapsed) {{
    var d = rootDoc();
    if (!isDesktop()) return;
    ensureDesktopVisible(d);
    setBodyCollapsed(d, !!collapsed);
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
      var collapsed = readCollapsedPref();
      setBodyCollapsed(d, !collapsed);
      ensureDesktopVisible(d);
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
    if (!sessionStorage.getItem('ips_sb_session_sync')) {{
      try {{
        var collapsed = readCollapsedPref();
        var url = new URL(window.location.href);
        if (!url.searchParams.has('ips_sb')) {{
          url.searchParams.set('ips_sb', collapsed ? 'c' : 'e');
          sessionStorage.setItem('ips_sb_session_sync', '1');
          window.location.replace(url.toString());
          return;
        }}
      }} catch (syncErr) {{}}
      sessionStorage.setItem('ips_sb_session_sync', '1');
    }}
    if (isDesktop()) restoreDesktopCollapsed(d);
    else restoreMobilePreference(d);
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
