"""PWA helpers for IPS Streamlit app."""

from __future__ import annotations

import json
import streamlit as st
import streamlit.components.v1 as components

_PWA_INJECTED_KEY = "ips_pwa_support_injected"
_IPS_TRIGGER_INSTALL_KEY = "ips_trigger_install"

_MANIFEST_HREF = "/app/static/manifest.json"
_SW_HREF = "/app/static/sw.js"

_THEME_COLOR = "#0b2247"
_APP_NAME = "IPS App"

_INSTALL_UNAVAILABLE_MSG = (
    "Install prompt is not available yet. On iPhone use Share → Add to Home Screen. "
    "On Android use Chrome menu → Install app."
)


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
  upsertMeta('mobile-web-app-capable', 'yes');
  upsertMeta('apple-mobile-web-app-capable', 'yes');
  upsertMeta('apple-mobile-web-app-title', cfg.appName);
  upsertMeta('apple-mobile-web-app-status-bar-style', 'black-translucent');

  w.__ipsBipEvent = null;

  w.__ipsTriggerInstall = async function() {{
    if (!w.__ipsBipEvent) return false;
    try {{
      w.__ipsBipEvent.prompt();
      await w.__ipsBipEvent.userChoice;
      w.__ipsBipEvent = null;
      return true;
    }} catch (err) {{
      console.warn('IPS install prompt failed:', err);
      return false;
    }}
  }};

  w.addEventListener('beforeinstallprompt', function(e) {{
    e.preventDefault();
    w.__ipsBipEvent = e;
    w.dispatchEvent(new Event('ips-install-ready'));
  }});

  if ('serviceWorker' in w.navigator) {{
    w.navigator.serviceWorker.register(cfg.sw, {{ scope: '/app/static/' }})
      .then(() => console.log('SW registered:', cfg.sw))
      .catch(err => console.error('SW failed:', err));
  }}
}})();
</script>
        """,
        height=0,
    )


def trigger_pwa_install_prompt() -> None:
    """Run browser install prompt once (height-0 component; no main-area banner)."""
    if not st.session_state.pop(_IPS_TRIGGER_INSTALL_KEY, False):
        return
    msg = json.dumps(_INSTALL_UNAVAILABLE_MSG)
    components.html(
        f"""
<script>
(function() {{
  const w = window.parent || window;
  const fallback = function() {{ alert({msg}); }};
  if (typeof w.__ipsTriggerInstall === "function") {{
    w.__ipsTriggerInstall().then(function(ok) {{ if (!ok) fallback(); }});
  }} else {{
    fallback();
  }}
}})();
</script>
        """,
        height=0,
    )


def render_install_app_sidebar_block() -> None:
    st.sidebar.markdown(
        '<p class="ips-install-section-title">Install App</p>',
        unsafe_allow_html=True,
    )
    st.sidebar.caption("Add IPS to your home screen for quick access.")

    if st.sidebar.button("Install App", key="ips_sidebar_install_app", use_container_width=True):
        st.session_state[_IPS_TRIGGER_INSTALL_KEY] = True
        st.session_state["show_install_help"] = True
        st.rerun()

    if st.session_state.get("show_install_help"):
        st.sidebar.info(
            "**iPhone:** Share → Add to Home Screen\n\n"
            "**Android:** Menu → Install App"
        )
        if st.sidebar.button("Dismiss", key="ips_install_dismiss"):
            st.session_state["show_install_help"] = False
            st.rerun()
