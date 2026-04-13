"""PWA helpers: manifest, theme color, service worker, install prompt (Streamlit-friendly)."""

from __future__ import annotations

import json

import streamlit as st
import streamlit.components.v1 as components

_PWA_INJECTED_KEY = "ips_pwa_support_injected"

# Streamlit serves project files from `.streamlit/static/` at `/.streamlit/static/...`
_MANIFEST_HREF = "/.streamlit/static/manifest.json"
_SW_HREF = "/.streamlit/static/sw.js"
_THEME_COLOR = "#0e1117"


def inject_pwa_support() -> None:
    """
    PWA support for Streamlit:
    - Injects manifest link + theme-color (st.markdown in main body; valid HTML5)
    - Registers minimal service worker for static PWA assets
    - Wires ``beforeinstallprompt`` for optional native install (Chrome/Edge Android) — used by sidebar button
    """
    if st.session_state.get(_PWA_INJECTED_KEY):
        return
    st.session_state[_PWA_INJECTED_KEY] = True

    # User-requested: manifest + meta via markdown (IPS dark theme)
    st.markdown(
        f"""
<link rel="manifest" href="{_MANIFEST_HREF}">
<meta name="theme-color" content="{_THEME_COLOR}">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
""",
        unsafe_allow_html=True,
    )

    head_payload = {
        "manifest": _MANIFEST_HREF,
        "sw": _SW_HREF,
        "themeColor": _THEME_COLOR,
        "icons": {
            "favicon32": "/.streamlit/static/icons/icon-32.png",
            "apple180": "/.streamlit/static/icons/icon-180.png",
        },
    }

    components.html(
        f"""
<script>
(function() {{
  const cfg = {json.dumps(head_payload)};
  function upsertLink(rel, href, attrs) {{
    const head = document.head || document.getElementsByTagName('head')[0];
    if (!head) return;
    let el = head.querySelector(`link[rel="${{rel}}"][href="${{href}}"]`);
    if (!el) {{
      el = document.createElement('link');
      el.setAttribute('rel', rel);
      head.appendChild(el);
    }}
    el.setAttribute('href', href);
    if (attrs) Object.entries(attrs).forEach(([k,v]) => el.setAttribute(k, v));
  }}
  function upsertMeta(name, content) {{
    const head = document.head || document.getElementsByTagName('head')[0];
    if (!head) return;
    let el = head.querySelector(`meta[name="${{name}}"]`);
    if (!el) {{
      el = document.createElement('meta');
      el.setAttribute('name', name);
      head.appendChild(el);
    }}
    el.setAttribute('content', content);
  }}

  upsertLink('manifest', cfg.manifest, {{}});
  upsertMeta('theme-color', cfg.themeColor);
  upsertLink('icon', cfg.icons.favicon32, {{'sizes':'32x32', 'type':'image/png'}});
  upsertLink('apple-touch-icon', cfg.icons.apple180, {{'sizes':'180x180'}});

  if ('serviceWorker' in navigator) {{
    navigator.serviceWorker.register(cfg.sw).catch(() => {{}});
  }}

  window.__ipsBipEvent = null;
  window.addEventListener('beforeinstallprompt', (e) => {{
    e.preventDefault();
    window.__ipsBipEvent = e;
    window.dispatchEvent(new CustomEvent('ips:pwa-install-available'));
  }});
}})();
</script>
        """,
        height=0,
    )


def render_install_button(*, label: str = "Install App") -> None:
    """
    In-app install control for browsers that support ``beforeinstallprompt`` (e.g. Chrome Android).
    Hidden when not available; does not replace manual Add to Home Screen on iOS Safari.
    """
    components.html(
        f"""
<div id="ips-pwa-install-wrap" style="display:none; margin: 0.35rem 0 0 0;">
  <button id="ips-pwa-install-btn" type="button"
    style="
      width: 100%;
      min-height: 2.85rem;
      padding: 0.55rem 0.9rem;
      border-radius: 10px;
      border: 1px solid rgba(59, 130, 246, 0.55);
      background: linear-gradient(180deg, #1e3a8a 0%, #1d4ed8 100%);
      color: #f8fafc;
      font-weight: 650;
      font-size: 1rem;
      cursor: pointer;
    "
  >{label}</button>
  <div style="color:#94a3b8; font-size: 0.8rem; margin-top: 0.35rem;">
    Uses the browser install prompt when available (often Android Chrome).
  </div>
</div>
<script>
(function() {{
  const wrap = document.getElementById('ips-pwa-install-wrap');
  const btn = document.getElementById('ips-pwa-install-btn');
  function showIfAvailable() {{
    if (window.__ipsBipEvent) wrap.style.display = 'block';
  }}
  window.addEventListener('ips:pwa-install-available', showIfAvailable);
  showIfAvailable();
  btn.addEventListener('click', async () => {{
    if (!window.__ipsBipEvent) return;
    try {{
      window.__ipsBipEvent.prompt();
      await window.__ipsBipEvent.userChoice;
    }} finally {{
      window.__ipsBipEvent = null;
      wrap.style.display = 'none';
    }}
  }});
}})();
</script>
        """,
        height=120,
    )


def render_install_app_sidebar_block() -> None:
    """IPS-styled sidebar block: Add to Home Screen instructions + optional native install."""
    st.sidebar.markdown(
        '<p class="ips-install-section-title">Install App</p>',
        unsafe_allow_html=True,
    )
    st.sidebar.caption("Add IPS to your home screen for quick access.")
    (ib_col,) = st.sidebar.columns(1)
    with ib_col:
        if st.button("Install App", key="ips_sidebar_install_app", use_container_width=True, type="secondary"):
            st.session_state["ips_install_help"] = True
    if st.session_state.get("ips_install_help"):
        st.sidebar.info(
            "**iPhone:** Tap **Share** → **Add to Home Screen**\n\n"
            "**Android:** Tap **⋮** menu → **Install app** or **Add to Home Screen**"
        )
        if st.sidebar.button("Dismiss", key="ips_install_dismiss"):
            st.session_state["ips_install_help"] = False
            st.rerun()
    render_install_button(label="Install App (browser)")
