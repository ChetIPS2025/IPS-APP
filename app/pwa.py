"""PWA helpers for IPS Streamlit app."""

from __future__ import annotations

import json
import streamlit as st
import streamlit.components.v1 as components

_PWA_INJECTED_KEY = "ips_pwa_support_injected"

_MANIFEST_HREF = "/app/static/manifest.json"
_SW_HREF = "/app/static/sw.js"

_THEME_COLOR = "#0b2247"
_APP_NAME = "IPS App"


def inject_pwa_support() -> None:
    if st.session_state.get(_PWA_INJECTED_KEY):
        return
    st.session_state[_PWA_INJECTED_KEY] = True

    payload = {
        "manifest": _MANIFEST_HREF,
        "sw": _SW_HREF,
        "themeColor": _THEME_COLOR,
        "appName": _APP_NAME,
    }

    components.html(
        f"""
<script>
(function() {{
  const cfg = {json.dumps(payload)};

  const w = window.parent || window;
  const d = w.document;
  const head = d.head || d.getElementsByTagName('head')[0];

  function upsertLink(rel, href, attrs) {{
    let el = head.querySelector(`link[rel="${{rel}}"]`);
    if (!el) {{
      el = d.createElement('link');
      el.setAttribute('rel', rel);
      head.appendChild(el);
    }}
    el.setAttribute('href', href);
    if (attrs) Object.entries(attrs).forEach(([k,v]) => el.setAttribute(k, v));
  }}

  function upsertMeta(name, content) {{
    let el = head.querySelector(`meta[name="${{name}}"]`);
    if (!el) {{
      el = d.createElement('meta');
      el.setAttribute('name', name);
      head.appendChild(el);
    }}
    el.setAttribute('content', content);
  }}

  upsertLink('manifest', cfg.manifest);
  upsertMeta('theme-color', cfg.themeColor);
  upsertMeta('apple-mobile-web-app-capable', 'yes');
  upsertMeta('apple-mobile-web-app-title', cfg.appName);
  upsertMeta('apple-mobile-web-app-status-bar-style', 'black-translucent');

  w.__ipsBipEvent = null;

  w.addEventListener('beforeinstallprompt', function(e) {{
    e.preventDefault();
    w.__ipsBipEvent = e;
    w.dispatchEvent(new Event('ips-install-ready'));
  }});

  if ('serviceWorker' in w.navigator) {{
    w.navigator.serviceWorker.register(cfg.sw, {{ scope: '/' }})
      .then(() => console.log('SW registered:', cfg.sw))
      .catch(err => console.error('SW failed:', err));
  }}
}})();
</script>
        """,
        height=0,
    )


def render_install_button(label: str = "Install App") -> None:
    components.html(
        f"""
<div id="installWrap" style="display:block;">
  <button id="installBtn"
    style="
      width:100%;
      padding:12px;
      border-radius:10px;
      background:#1d4ed8;
      color:white;
      border:1px solid rgba(255,255,255,.18);
      font-weight:600;
      cursor:pointer;
    ">
    {label}
  </button>
</div>

<script>
(function() {{
  const w = window.parent || window;
  const btn = document.getElementById('installBtn');

  btn.onclick = async () => {{
    if (w.__ipsBipEvent) {{
      w.__ipsBipEvent.prompt();
      await w.__ipsBipEvent.userChoice;
      w.__ipsBipEvent = null;
    }} else {{
      alert("Install prompt is not available yet. On iPhone use Share → Add to Home Screen. On Android use Chrome menu → Install app.");
    }}
  }};
}})();
</script>
        """,
        height=80,
    )


def render_install_app_sidebar_block() -> None:
    st.sidebar.markdown("### Install App")
    st.sidebar.caption("Add IPS to your home screen for quick access.")

    if st.sidebar.button("Install App", key="ips_sidebar_install_app", use_container_width=True):
        st.session_state["show_install_help"] = True

    if st.session_state.get("show_install_help"):
        st.sidebar.info(
            "**iPhone:** Share → Add to Home Screen\n\n"
            "**Android:** Menu → Install App"
        )
        if st.sidebar.button("Dismiss", key="ips_install_dismiss"):
            st.session_state["show_install_help"] = False
            st.rerun()

    render_install_button("Install App")
