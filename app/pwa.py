"""PWA helpers for IPS Streamlit app."""

from __future__ import annotations

import json
import re
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

from app.config import APP_VERSION
_PWA_INJECTED_KEY = "ips_pwa_support_injected"
_IPS_TRIGGER_INSTALL_KEY = "ips_trigger_install"

_THEME_COLOR = "#2563eb"
_APP_NAME = "IPS Operations"

_INSTALL_UNAVAILABLE_MSG = (
    "Install prompt is not available yet. On iPhone use Share → Add to Home Screen. "
    "On Android use Chrome menu → Install app."
)


def _streamlit_base_path() -> str:
    """Optional ``server.baseUrlPath`` prefix (empty for default local dev)."""
    try:
        from streamlit import config

        base = (config.get_option("server.baseUrlPath") or "").strip().strip("/")
        return f"/{base}" if base else ""
    except Exception:
        return ""


def _static_url(filename: str) -> str:
    base = _streamlit_base_path()
    return f"{base}/app/static/{filename}"


def _start_url() -> str:
    base = _streamlit_base_path()
    return f"{base}/" if base else "/"


def install_page_url() -> str:
    """Public share link for the Install IPS App page (``?install=1`` on the app root)."""
    from app.config import settings
    base = str(getattr(settings, "app_base_url", "") or "").strip().rstrip("/")
    prefix = _streamlit_base_path()
    path = f"{prefix}/" if prefix else "/"
    if base:
        return f"{base}{path}?install=1"
    return f"{path}?install=1"


def _manifest_id() -> str:
    """Stable PWA manifest id tied to :data:`APP_VERSION` (incl. ``IPS_APP_VERSION`` env)."""
    safe = re.sub(r"[^a-zA-Z0-9._-]", "-", str(APP_VERSION or "0").strip()) or "0"
    return f"ips-operations-platform-{safe}"


def manifest_json_bytes(*, indent: int | None = None) -> bytes:
    """Serialize :func:`build_web_manifest` for HTTP responses and optional file sync."""
    kwargs: dict[str, Any] = {}
    if indent is not None:
        kwargs["indent"] = indent
        kwargs["ensure_ascii"] = False
        text = json.dumps(build_web_manifest(), **kwargs) + "\n"
    else:
        text = json.dumps(build_web_manifest(), separators=(",", ":"))
    return text.encode("utf-8")


def build_web_manifest() -> dict[str, str | list[dict[str, str]]]:
    """
    Web app manifest with ``start_url`` / ``scope`` aligned to ``server.baseUrlPath``.

    Single source of truth — used by :func:`inject_pwa_support` (blob link),
    :func:`manifest_json_bytes`, and ``scripts/sync_pwa_manifest.py``.
    """
    start = _start_url()
    return {
        "id": _manifest_id(),
        "name": _APP_NAME,
        "short_name": "IPS",
        "description": "Industrial Plant Solutions operations platform",
        "start_url": start,
        "scope": start,
        "display": "standalone",
        "orientation": "any",
        "background_color": "#f4f6f9",
        "theme_color": _THEME_COLOR,
        "icons": [
            {
                "src": _static_url("favicon.png"),
                "sizes": "32x32",
                "type": "image/png",
                "purpose": "any",
            },
            {
                "src": _static_url("apple-touch-icon.png"),
                "sizes": "180x180",
                "type": "image/png",
                "purpose": "any",
            },
            {
                "src": _static_url("icon-192.png"),
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any",
            },
            {
                "src": _static_url("icon-512.png"),
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable",
            },
        ],
    }


def inject_pwa_support() -> None:
    """Register manifest + service worker (same entry URL as browser)."""
    inject_key = f"{_PWA_INJECTED_KEY}_{APP_VERSION}"
    if st.session_state.get(inject_key):
        return
    st.session_state[inject_key] = True

    sw_href = _static_url("sw.js")
    start_url = _start_url()
    manifest_data = build_web_manifest()

    payload = {
        "sw": f"{sw_href}?v={APP_VERSION}",
        "manifestData": manifest_data,
        "startUrl": start_url,
        "scope": start_url,
        "swPathMarker": "app/static/sw.js",
        "themeColor": _THEME_COLOR,
        "appName": _APP_NAME,
        "version": APP_VERSION,
        "faviconPng": _static_url("favicon.png"),
        "faviconIco": _static_url("favicon.ico"),
        "appleTouchIcon": _static_url("apple-touch-icon.png"),
    }

    from app.ui.app_shell_styles import inject_app_shell_script

    with st.sidebar:
        inject_app_shell_script(
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

  const manifestBlob = new Blob([JSON.stringify(cfg.manifestData)], {{
    type: 'application/manifest+json'
  }});
  const manifestUrl = URL.createObjectURL(manifestBlob);
  upsertLink('manifest', manifestUrl);
  if (cfg.faviconIco) {{
    upsertLink('icon', cfg.faviconIco, {{ type: 'image/x-icon' }});
  }}
  if (cfg.faviconPng) {{
    upsertLink('icon', cfg.faviconPng, {{ type: 'image/png', sizes: '32x32' }});
  }}
  if (cfg.appleTouchIcon) {{
    upsertLink('apple-touch-icon', cfg.appleTouchIcon, {{ sizes: '180x180' }});
  }}
  upsertMeta('theme-color', cfg.themeColor);
  upsertMeta('mobile-web-app-capable', 'yes');
  upsertMeta('apple-mobile-web-app-capable', 'yes');
  upsertMeta('apple-mobile-web-app-title', cfg.appName);
  upsertMeta('apple-mobile-web-app-status-bar-style', 'default');
  upsertMeta('application-name', cfg.appName);

  w.__ipsBipEvent = null;
  w.__ipsAppVersion = cfg.version;

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

  async function registerServiceWorker() {{
    if (!('serviceWorker' in w.navigator)) return;
    try {{
      const regs = await w.navigator.serviceWorker.getRegistrations();
      const swMarker = cfg.swPathMarker || 'app/static/sw.js';
      for (const reg of regs) {{
        const worker = reg.active || reg.waiting || reg.installing;
        const script = worker && worker.scriptURL ? worker.scriptURL : '';
        const isIpsSw = script.includes(swMarker);
        const isCurrentVersion = script.includes(cfg.version);
        if (isIpsSw && !isCurrentVersion) {{
          await reg.unregister();
        }}
      }}
    }} catch (err) {{
      console.warn('IPS SW cleanup:', err);
    }}
    try {{
      const reg = await w.navigator.serviceWorker.register(cfg.sw, {{ scope: cfg.scope }});
      console.log('IPS SW registered', reg.scope, cfg.version);
      if (reg.waiting) reg.waiting.postMessage({{ type: 'SKIP_WAITING' }});
      reg.update();
    }} catch (err) {{
      console.error('IPS SW registration failed:', err);
    }}
  }}

  registerServiceWorker();

  if (w.location.pathname !== cfg.startUrl && w.location.search.indexOf('tsign=') < 0) {{
    try {{
      const target = new URL(cfg.startUrl, w.location.origin);
      if (w.location.pathname + '/' !== target.pathname && w.location.pathname !== target.pathname) {{
        console.log('IPS PWA aligning route to', target.href);
      }}
    }} catch (e) {{}}
  }}
}})();
</script>
            """
        )


def trigger_pwa_install_prompt() -> None:
    """Run browser install prompt once (height-0 component; no main-area banner)."""
    if not st.session_state.pop(_IPS_TRIGGER_INSTALL_KEY, False):
        return
    msg = json.dumps(_INSTALL_UNAVAILABLE_MSG)
    from app.ui.app_shell_styles import inject_app_shell_script

    with st.sidebar:
        inject_app_shell_script(
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
            """
        )


def render_install_app_sidebar_block() -> None:
    """Optional install block — prefer ``components.sidebar`` footer for unified chrome."""
    st.sidebar.markdown(
        '<p class="ips-install-section-title">Install App</p>',
        unsafe_allow_html=True,
    )
    st.sidebar.caption("Add IPS to your home screen for quick access.")
    st.sidebar.link_button(
        "Open install page",
        install_page_url(),
        use_container_width=True,
    )

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
