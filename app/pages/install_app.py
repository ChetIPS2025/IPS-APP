"""Public Install IPS App page — share link, icon, and Add to Home Screen instructions."""

from __future__ import annotations

import html

import streamlit as st
import streamlit.components.v1 as components

try:
    from app.components.install_share import render_install_share_admin
    from app.config import settings
    from app.pwa import _start_url, _static_url, inject_pwa_support
    from app.styles import inject_install_page_css, inject_unauthenticated_shell_css
except ImportError:
    from components.install_share import render_install_share_admin  # type: ignore
    from config import settings  # type: ignore
    from pwa import _start_url, _static_url, inject_pwa_support  # type: ignore
    from styles import inject_install_page_css, inject_unauthenticated_shell_css  # type: ignore

_INSTALL_SESSION_KEY = "_ips_install_route"
_PATH_REDIRECT_KEY = "_ips_install_path_redirect_done"


def _first_query_param(name: str) -> str:
    raw = st.query_params.get(name)
    if isinstance(raw, list):
        return str(raw[0] or "").strip()
    return str(raw or "").strip()


def _absolute_static_url(filename: str) -> str:
    base = str(getattr(settings, "app_base_url", "") or "").strip().rstrip("/")
    path = _static_url(filename)
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{base}{path}" if base else path


def _open_app_url() -> str:
    base = str(getattr(settings, "app_base_url", "") or "").strip().rstrip("/")
    start = _start_url() or "/"
    if base:
        return f"{base}{start}" if start.startswith("/") else f"{base}/{start}"
    return start


def inject_install_path_redirect() -> None:
    """Map ``/install`` pathname to ``?install=1`` (Streamlit query routing)."""
    if st.session_state.get(_PATH_REDIRECT_KEY):
        return
    if _first_query_param("install").lower() in {"1", "true", "yes"}:
        st.session_state[_PATH_REDIRECT_KEY] = True
        return
    components.html(
        """
<script>
(function() {
  const w = window.parent || window;
  const path = (w.location.pathname || "").replace(/\\/+$/, "") || "/";
  if (!path.endsWith("/install")) return;
  const params = new URLSearchParams(w.location.search || "");
  if ((params.get("install") || "").toLowerCase() === "1") return;
  params.set("install", "1");
  const base = path.slice(0, -"/install".length) || "";
  const target = (base || "/") + "?" + params.toString();
  w.location.replace(target);
})();
</script>
        """,
        height=0,
    )


def capture_install_route_from_query() -> None:
    """Persist install route before auth gate."""
    inject_install_path_redirect()
    if _first_query_param("install").lower() in {"1", "true", "yes"}:
        st.session_state[_INSTALL_SESSION_KEY] = True
        return
    if _first_query_param("page").strip().lower() == "install":
        st.session_state[_INSTALL_SESSION_KEY] = True


def install_route_active() -> bool:
    return bool(st.session_state.get(_INSTALL_SESSION_KEY))


def _install_device_detect_script() -> str:
    return """
<script>
(function() {
  function detectInstallDevice() {
    const ua = navigator.userAgent || "";
    const isIpad = /iPad/.test(ua)
      || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
    if (/iPhone|iPod/i.test(ua) || isIpad) return "ios";
    if (/Android/i.test(ua)) return "android";
    return "desktop";
  }
  function applyInstallDevice() {
    const kind = detectInstallDevice();
    document.querySelectorAll(".ips-install-card").forEach(function(card) {
      card.setAttribute("data-device", kind);
    });
    document.body.classList.remove(
      "ips-install-device-ios",
      "ips-install-device-android",
      "ips-install-device-desktop"
    );
    document.body.classList.add("ips-install-device-" + kind);
  }
  applyInstallDevice();
  document.addEventListener("DOMContentLoaded", applyInstallDevice);
})();
</script>
"""


def _install_page_html(
    *,
    icon_url: str,
    icon_download_url: str,
    open_url: str,
    share_url: str,
) -> str:
    app_name = html.escape(str(getattr(settings, "app_name", "IPS Operations") or "IPS Operations"))
    return f"""
<div class="ips-install-card" data-device="pending">
  <img class="ips-install-icon" src="{html.escape(icon_url)}" alt="IPS App icon" width="120" height="120" />
  <h1 class="ips-install-title">Install IPS App</h1>
  <p class="ips-install-lead ips-install-lead-ios">
    Add <strong>{app_name}</strong> to your iPhone or iPad home screen for one-tap access.
  </p>
  <p class="ips-install-lead ips-install-lead-android">
    Add <strong>{app_name}</strong> to your Android home screen from Chrome.
  </p>
  <p class="ips-install-lead ips-install-lead-desktop">
    Open <strong>{app_name}</strong> in your browser, or install it as an app in Chrome or Edge.
  </p>
  <div class="ips-install-actions">
    <a class="ips-install-btn ips-install-btn-primary" href="{html.escape(open_url)}">Open IPS Operations</a>
    <a class="ips-install-btn ips-install-btn-secondary ips-install-btn-download"
       href="{html.escape(icon_download_url)}" download="IPS-App-Icon.png">Download App Icon</a>
  </div>
  <div class="ips-install-steps ips-install-steps-ios">
    <h2 class="ips-install-steps-title">iPhone / iPad (Safari)</h2>
    <ol>
      <li>Open this page in <strong>Safari</strong>.</li>
      <li>Tap <strong>Share</strong> (square with arrow).</li>
      <li>Tap <strong>Add to Home Screen</strong>.</li>
      <li>Confirm the name, then tap <strong>Add</strong>.</li>
    </ol>
    <p class="ips-install-note">The IPS app icon is applied automatically from this page.</p>
  </div>
  <div class="ips-install-steps ips-install-steps-android">
    <h2 class="ips-install-steps-title">Android (Chrome)</h2>
    <ol>
      <li>Open this page in <strong>Chrome</strong>.</li>
      <li>Tap the <strong>menu</strong> (three dots).</li>
      <li>Tap <strong>Install app</strong> or <strong>Add to Home screen</strong>.</li>
      <li>Confirm to add the shortcut with the IPS icon.</li>
    </ol>
  </div>
  <div class="ips-install-steps ips-install-steps-desktop">
    <h2 class="ips-install-steps-title">Computer (Chrome or Edge)</h2>
    <ol>
      <li>Click <strong>Open IPS Operations</strong> above to use the app in your browser.</li>
      <li><strong>Chrome:</strong> Click the install icon in the address bar, or Menu (⋮) →
          <strong>Install IPS Operations</strong> / <strong>Install app</strong>.</li>
      <li><strong>Microsoft Edge:</strong> Open the menu → <strong>Apps</strong> →
          <strong>Install this site as an app</strong>.</li>
      <li>Pin the installed app to your taskbar or desktop for quick access.</li>
    </ol>
  </div>
  <p class="ips-install-share-note">Share this install link with anyone:</p>
  <p class="ips-install-share-url"><a href="{html.escape(share_url)}">{html.escape(share_url)}</a></p>
</div>
"""


def render_install_page() -> None:
    """Public install landing page (no login required)."""
    inject_pwa_support()
    inject_unauthenticated_shell_css()
    inject_install_page_css()

    st.markdown(
        '<span class="ips-install-page-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )

    try:
        from app.pwa import install_page_url
    except ImportError:
        from pwa import install_page_url  # type: ignore

    icon_url = _absolute_static_url("apple-touch-icon.png")
    icon_download = _absolute_static_url("icon-512.png")
    open_url = _open_app_url()
    share_url = install_page_url()

    _left, center, _right = st.columns([0.35, 1.3, 0.35])
    with center:
        st.markdown(
            _install_page_html(
                icon_url=icon_url,
                icon_download_url=icon_download,
                open_url=open_url,
                share_url=share_url,
            ),
            unsafe_allow_html=True,
        )
        st.markdown(_install_device_detect_script(), unsafe_allow_html=True)
        render_install_share_admin()
