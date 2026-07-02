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
IPS_SIDEBAR_DESKTOP_MIN_PX = 900


def store_sidebar_nav_fallback(items: list[tuple[str, ...]]) -> None:
    """Persist current nav labels for client-side fallback menu."""
    rows: list[dict[str, str]] = []
    for item in items:
        if len(item) >= 2:
            rows.append({"slug": str(item[0]), "label": str(item[1])})
    st.session_state[IPS_SIDEBAR_NAV_FALLBACK_KEY] = rows


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
            if slug and label:
                safe.append({"slug": slug, "label": label})
    return json.dumps(safe)


def inject_sidebar_shell() -> None:
    """Inject sidebar layout CSS/JS once per authenticated session."""
    if st.session_state.get(IPS_SIDEBAR_SHELL_KEY):
        inject_sidebar_menu_wire()
        if st.session_state.pop(IPS_SIDEBAR_TOGGLE_REQUEST_KEY, False):
            components.html(_toggle_script(), height=0)
        return
    st.session_state[IPS_SIDEBAR_SHELL_KEY] = True

    if st.session_state.pop(IPS_SIDEBAR_TOGGLE_REQUEST_KEY, False):
        components.html(_toggle_script(), height=0)

    nav_json = _fallback_nav_json()
    components.html(_shell_script(nav_json), height=0)
    st.markdown(_shell_css(), unsafe_allow_html=True)
    inject_sidebar_menu_wire()


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
    return f"""
<style id="ips-sidebar-shell-v1">
button.ips-header-menu-btn {{
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 0.35rem !important;
  min-height: 2.35rem !important;
  padding: 0.35rem 0.85rem !important;
  border-radius: 10px !important;
  border: 1px solid #cbd5e1 !important;
  background: #ffffff !important;
  color: #0f172a !important;
  font-size: 0.875rem !important;
  font-weight: 700 !important;
  line-height: 1 !important;
  cursor: pointer !important;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06) !important;
  white-space: nowrap !important;
}}
button.ips-header-menu-btn:hover {{
  background: #f8fafc !important;
  border-color: #94a3b8 !important;
  color: #1d4ed8 !important;
}}
.ips-main-header {{
  position: relative !important;
  z-index: 2 !important;
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
#ips-nav-fallback .ips-nav-fallback-title {{
  margin: 0 0 0.45rem;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #64748b;
}}
#ips-nav-fallback a {{
  display: block;
  padding: 0.55rem 0.65rem;
  border-radius: 8px;
  color: #0f172a;
  font-size: 0.875rem;
  font-weight: 700;
  text-decoration: none;
}}
#ips-nav-fallback a:hover {{
  background: #eff6ff;
  color: #1d4ed8;
}}
@media (min-width: {IPS_SIDEBAR_DESKTOP_MIN_PX}px) {{
  section[data-testid="stSidebar"],
  [data-testid="stSidebar"] {{
    width: 248px !important;
    min-width: 248px !important;
    max-width: 248px !important;
    transform: none !important;
    visibility: visible !important;
    opacity: 1 !important;
    position: relative !important;
    z-index: 99995 !important;
    overflow: visible !important;
  }}
  section[data-testid="stSidebar"][aria-expanded="false"],
  [data-testid="stSidebar"][aria-expanded="false"] {{
    transform: none !important;
    width: 248px !important;
    min-width: 248px !important;
    max-width: 248px !important;
    margin-left: 0 !important;
  }}
  section[data-testid="stSidebar"] > div {{
    width: 100% !important;
    min-width: 248px !important;
    overflow-x: hidden !important;
    overflow-y: auto !important;
  }}
  [data-testid="stSidebarCollapsedControl"],
  button[data-testid="collapsedControl"] {{
    z-index: 100000 !important;
  }}
  #ips-sidebar-backdrop {{
    display: none !important;
  }}
}}
@media (max-width: {IPS_SIDEBAR_DESKTOP_MIN_PX - 1}px) {{
  section[data-testid="stSidebar"],
  [data-testid="stSidebar"] {{
    position: fixed !important;
    left: 0 !important;
    top: 0 !important;
    height: 100dvh !important;
    max-height: 100dvh !important;
    z-index: 100002 !important;
    width: 260px !important;
    min-width: 260px !important;
    max-width: min(260px, 92vw) !important;
    transition: transform 0.2s ease-out !important;
    box-shadow: 4px 0 24px rgba(15, 23, 42, 0.18) !important;
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
  [data-testid="stSidebarCollapsedControl"],
  button[data-testid="collapsedControl"] {{
    z-index: 100004 !important;
    min-width: 2.75rem !important;
    min-height: 2.75rem !important;
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


def _toggle_script() -> str:
    return """
<script>
(function () {
  try {
    var top = window.top || window.parent || window;
    if (top.IPS && top.IPS.toggleSidebar) top.IPS.toggleSidebar(true);
  } catch (e) {}
})();
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
  function ensureDesktopOpen(d) {{
    if (!isDesktop()) return;
    var side = sidebarEl(d);
    if (!side) return;
    if (side.getAttribute('aria-expanded') !== 'true') {{
      var btn = toggleBtn(d);
      if (btn) btn.click();
    }}
    try {{ localStorage.setItem('ips_sidebar_open', '1'); }} catch (e) {{}}
    syncBackdrop(d);
  }}
  function restoreMobilePreference(d) {{
    if (isDesktop()) {{
      ensureDesktopOpen(d);
      return;
    }}
    var side = sidebarEl(d);
    if (!side) return;
    var pref = '1';
    try {{ pref = localStorage.getItem('ips_sidebar_open') || '0'; }} catch (e2) {{}}
    var expanded = side.getAttribute('aria-expanded') === 'true';
    var wantOpen = pref === '1';
    if (wantOpen !== expanded) {{
      var btn = toggleBtn(d);
      if (btn) btn.click();
    }}
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
  window.IPS = window.IPS || {{}};
  window.IPS.toggleSidebar = function () {{
    var d = rootDoc();
    var side = sidebarEl(d);
    if (!side) {{
      var fb = fallbackEl(d);
      fb.classList.toggle('is-open');
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
    if (isDesktop()) ensureDesktopOpen(d);
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
