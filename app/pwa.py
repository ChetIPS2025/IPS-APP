"""PWA helpers for IPS Streamlit app (fixed for /static folder)."""

from __future__ import annotations

import json
import streamlit as st
import streamlit.components.v1 as components

_PWA_INJECTED_KEY = "ips_pwa_support_injected"

# ✅ CORRECT PATHS FOR YOUR APP
_SW_HREF = "/app/static/sw.js"
_MANIFEST_HREF = "/app/static/manifest.json"

_THEME_COLOR = "#0b2247"
_BACKGROUND_COLOR = "#031633"
_APP_NAME = "IPS App"


def inject_pwa_support() -> None:
    if st.session_state.get(_PWA_INJECTED_KEY):
        return
    st.session_state[_PWA_INJECTED_KEY] = True

    # Basic meta + manifest
    st.markdown(
        f"""
<link rel="manifest" href="{_MANIFEST_HREF}">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="{_THEME_COLOR}">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="{_APP_NAME}">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
""",
        unsafe_allow_html=True,
    )

    # JS injection
    components.html(
        f"""
<script>
(function() {{
  const cfg = {{
    manifest: "{_MANIFEST_HREF}",
    sw: "{_SW_HREF}"
  }};

  // Inject manifest into head
  const head = document.head || document.getElementsByTagName('head')[0];

  function addLink(rel, href) {{
    let el = head.querySelector(`link[rel="${{rel}}"]`);
    if (!el) {{
      el = document.createElement('link');
      el.setAttribute('rel', rel);
      head.appendChild(el);
    }}
    el.setAttribute('href', href);
  }}

  addLink('manifest', cfg.manifest);

  // Register service worker
  if ('serviceWorker' in navigator) {{
    navigator.serviceWorker.register(cfg.sw)
      .then(() => console.log('SW registered'))
      .catch(err => console.log('SW failed', err));
  }}

  // Install prompt handling
  window.__ipsBipEvent = null;

  window.addEventListener('beforeinstallprompt', (e) => {{
    e.preventDefault();
    window.__ipsBipEvent = e;
    window.dispatchEvent(new Event('ips-install-ready'));
  }});
}})();
</script>
        """,
        height=0,
    )


def render_install_button(label: str = "Install App") -> None:
    components.html(
        f"""
<div id="installWrap" style="display:none;">
  <button id="installBtn"
    style="
      width:100%;
      padding:12px;
      border-radius:10px;
      background:#1d4ed8;
      color:white;
      border:none;
      font-weight:600;
      cursor:pointer;
    ">
    {label}
  </button>
</div>

<script>
(function() {{
  const wrap = document.getElementById('installWrap');
  const btn = document.getElementById('installBtn');

  function showBtn() {{
    if (window.__ipsBipEvent) {{
      wrap.style.display = 'block';
    }}
  }}

  window.addEventListener('ips-install-ready', showBtn);
  showBtn();

  btn.onclick = async () => {{
    if (!window.__ipsBipEvent) return;

    window.__ipsBipEvent.prompt();
    await window.__ipsBipEvent.userChoice;

    window.__ipsBipEvent = null;
    wrap.style.display = 'none';
  }};
}})();
</script>
        """,
        height=80,
    )


def render_install_app_sidebar_block() -> None:
    st.sidebar.markdown("### Install App")
    st.sidebar.caption("Add IPS to your home screen for quick access.")

    if st.sidebar.button("Install App"):
        st.session_state["show_install_help"] = True

    if st.session_state.get("show_install_help"):
        st.sidebar.info(
            "**iPhone:** Share → Add to Home Screen\n\n"
            "**Android:** Menu → Install App"
        )
        if st.sidebar.button("Dismiss"):
            st.session_state["show_install_help"] = False
            st.rerun()

    render_install_button("Install App")
