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


def _install_page_scripts() -> str:
    return """
<script>
(function() {
  function appWindow() {
    return window.parent || window;
  }

  function detectInstallDevice() {
    const ua = navigator.userAgent || "";
    const isIpad = /iPad/.test(ua)
      || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
    if (/iPhone|iPod/i.test(ua) || isIpad) return "ios";
    if (/Android/i.test(ua)) return "android";
    return "desktop";
  }

  function openInstructions() {
    const details = document.querySelector(".ips-install-help details");
    if (details) details.open = true;
  }

  function setInstallStatus(message) {
    document.querySelectorAll(".ips-install-status").forEach(function(el) {
      el.textContent = message;
      el.style.display = message ? "block" : "none";
    });
  }

  async function handleInstallClick() {
    const card = document.querySelector(".ips-install-card");
    const device = card ? card.getAttribute("data-device") : detectInstallDevice();
    const w = appWindow();

    if (device === "ios") {
      openInstructions();
      setInstallStatus("Use Safari Share → Add to Home Screen.");
      return;
    }

    if (typeof w.__ipsTriggerInstall === "function") {
      const ok = await w.__ipsTriggerInstall();
      if (ok) {
        setInstallStatus("");
        return;
      }
    }

    openInstructions();
    if (device === "android") {
      setInstallStatus("Tap Chrome menu → Install app if no prompt appeared.");
    } else {
      setInstallStatus("Use the install icon in your browser address bar if needed.");
    }
  }

  function wireInstallButtons() {
    document.querySelectorAll(".ips-install-btn-install").forEach(function(btn) {
      if (btn.dataset.ipsInstallWired === "1") return;
      btn.dataset.ipsInstallWired = "1";
      btn.addEventListener("click", function(ev) {
        ev.preventDefault();
        handleInstallClick();
      });
    });
    document.querySelectorAll(".ips-install-copy-btn").forEach(function(btn) {
      if (btn.dataset.ipsCopyWired === "1") return;
      btn.dataset.ipsCopyWired = "1";
      btn.addEventListener("click", async function(ev) {
        ev.preventDefault();
        const url = btn.getAttribute("data-copy-url") || "";
        if (!url) return;
        try {
          await navigator.clipboard.writeText(url);
          btn.textContent = "Copied!";
          setTimeout(function() { btn.textContent = "Copy Link"; }, 2000);
        } catch (err) {
          btn.textContent = "Copy failed";
          setTimeout(function() { btn.textContent = "Copy Link"; }, 2000);
        }
      });
    });
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
    wireInstallButtons();
  }

  applyInstallDevice();
  wireInstallButtons();
  document.addEventListener("DOMContentLoaded", function() {
    applyInstallDevice();
    wireInstallButtons();
  });
})();
</script>
"""


def _install_page_html(*, icon_url: str, open_url: str, share_url: str) -> str:
    return f"""
<div class="ips-install-card" data-device="pending">
  <img class="ips-install-icon" src="{html.escape(icon_url)}" alt="IPS App icon" width="120" height="120" />
  <h1 class="ips-install-title">Install IPS App</h1>
  <p class="ips-install-lead">Open IPS on this device or add it to your home screen.</p>
  <div class="ips-install-actions">
    <a class="ips-install-btn ips-install-btn-primary" href="{html.escape(open_url)}">Open IPS App</a>
    <button type="button" class="ips-install-btn ips-install-btn-secondary ips-install-btn-install"
            aria-label="Install IPS App on this device">Install on This Device</button>
  </div>
  <p class="ips-install-status" role="status" aria-live="polite" style="display:none"></p>
  <div class="ips-install-help">
    <p class="ips-install-help-label">Need help installing?</p>
    <details class="ips-install-help-details">
      <summary class="ips-install-help-summary">Show Instructions</summary>
      <div class="ips-install-steps ips-install-steps-ios">
        <ol>
          <li>Open this page in <strong>Safari</strong>.</li>
          <li>Tap <strong>Share</strong> → <strong>Add to Home Screen</strong>.</li>
          <li>Tap <strong>Add</strong>.</li>
        </ol>
      </div>
      <div class="ips-install-steps ips-install-steps-android">
        <ol>
          <li>Tap <strong>Install on This Device</strong> above.</li>
          <li>If needed: Chrome menu (⋮) → <strong>Install app</strong>.</li>
        </ol>
      </div>
      <div class="ips-install-steps ips-install-steps-desktop">
        <ol>
          <li>Click <strong>Install on This Device</strong> above.</li>
          <li>If needed: use the install icon in the Chrome or Edge address bar.</li>
        </ol>
      </div>
    </details>
  </div>
  <div class="ips-install-share">
    <p class="ips-install-share-note">Share this link:</p>
    <p class="ips-install-share-url">{html.escape(share_url)}</p>
    <button type="button" class="ips-install-btn ips-install-btn-copy ips-install-copy-btn"
            data-copy-url="{html.escape(share_url)}">Copy Link</button>
  </div>
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
    open_url = _open_app_url()
    share_url = install_page_url()

    _left, center, _right = st.columns([0.35, 1.3, 0.35])
    with center:
        st.markdown(
            _install_page_html(
                icon_url=icon_url,
                open_url=open_url,
                share_url=share_url,
            ),
            unsafe_allow_html=True,
        )
        st.markdown(_install_page_scripts(), unsafe_allow_html=True)
        render_install_share_admin()
