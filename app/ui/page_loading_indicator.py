"""Visible page-loading feedback while Streamlit reruns (header spinner is hidden)."""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from app.ui.css_inject import inject_css_once

IPS_PAGE_LOADING_STYLE_ID = "ips-page-loading-indicator-v1"
IPS_PAGE_LOADING_HOOK_KEY = "ips_page_loading_hook_v1"


def inject_page_loading_indicator() -> None:
    """Top progress bar + badge shown during reruns and after user actions."""
    if not inject_css_once(IPS_PAGE_LOADING_STYLE_ID):
        return

    st.markdown(
        f"""
<style id="{IPS_PAGE_LOADING_STYLE_ID}">
body.ips-authed-app #ips-page-loading-bar {{
  position: fixed;
  top: 0;
  height: 3px;
  z-index: 1000001;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.15s ease;
  overflow: hidden;
  background: rgba(37, 99, 235, 0.12);
}}
body.ips-authed-app #ips-page-loading-bar.ips-active {{
  opacity: 1;
}}
body.ips-authed-app #ips-page-loading-bar .ips-bar-inner {{
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  width: 42%;
  background: linear-gradient(90deg, #2563eb 0%, #60a5fa 55%, #2563eb 100%);
  animation: ips-page-loading-slide 1.05s ease-in-out infinite;
}}
@keyframes ips-page-loading-slide {{
  0% {{ transform: translateX(-110%); }}
  100% {{ transform: translateX(320%); }}
}}
body.ips-authed-app #ips-page-loading-badge {{
  position: fixed;
  top: 12px;
  z-index: 1000001;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid #dbeafe;
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.12);
  color: #1e40af;
  font: 600 12px/1.2 system-ui, -apple-system, "Segoe UI", sans-serif;
  letter-spacing: 0.01em;
  pointer-events: none;
  opacity: 0;
  transform: translateY(-6px);
  transition: opacity 0.15s ease, transform 0.15s ease;
}}
body.ips-authed-app #ips-page-loading-badge.ips-active {{
  opacity: 1;
  transform: translateY(0);
}}
body.ips-authed-app #ips-page-loading-badge .ips-dot {{
  width: 8px;
  height: 8px;
  border-radius: 50%;
  border: 2px solid rgba(37, 99, 235, 0.25);
  border-top-color: #2563eb;
  animation: ips-page-loading-spin 0.75s linear infinite;
}}
@keyframes ips-page-loading-spin {{
  to {{ transform: rotate(360deg); }}
}}
body.ips-page-loading section[data-testid="stMain"] {{
  cursor: progress;
}}
</style>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.get(IPS_PAGE_LOADING_HOOK_KEY):
        return
    st.session_state[IPS_PAGE_LOADING_HOOK_KEY] = True

    with st.sidebar:
        components.html(
            """
<script>
(function () {
  const w = window.parent || window;
  const doc = w.document;
  if (w.__ipsPageLoadingHook) return;
  w.__ipsPageLoadingHook = true;

  function ensureNodes() {
    if (!doc.body) return null;
    let bar = doc.getElementById("ips-page-loading-bar");
    if (!bar) {
      bar = doc.createElement("div");
      bar.id = "ips-page-loading-bar";
      bar.setAttribute("aria-hidden", "true");
      bar.innerHTML = '<div class="ips-bar-inner"></div>';
      doc.body.appendChild(bar);
    }
    let badge = doc.getElementById("ips-page-loading-badge");
    if (!badge) {
      badge = doc.createElement("div");
      badge.id = "ips-page-loading-badge";
      badge.setAttribute("role", "status");
      badge.setAttribute("aria-live", "polite");
      badge.innerHTML = '<span class="ips-dot" aria-hidden="true"></span><span>Loading…</span>';
      doc.body.appendChild(badge);
    }
    return { bar, badge };
  }

  function layoutNodes() {
    const nodes = ensureNodes();
    if (!nodes) return;
    const main = doc.querySelector('[data-testid="stAppViewContainer"]');
    if (!main) return;
    const rect = main.getBoundingClientRect();
    nodes.bar.style.left = rect.left + "px";
    nodes.bar.style.width = Math.max(rect.width, 0) + "px";
    nodes.badge.style.left = Math.max(rect.right - 132, rect.left + 12) + "px";
  }

  let active = false;
  let hideTimer = null;
  let layoutTimer = null;

  function setActive(on) {
    const nodes = ensureNodes();
    if (!nodes) return;
    active = !!on;
    nodes.bar.classList.toggle("ips-active", active);
    nodes.badge.classList.toggle("ips-active", active);
    doc.body.classList.toggle("ips-page-loading", active);
    if (active) layoutNodes();
  }

  function showLoading() {
    if (hideTimer) {
      clearTimeout(hideTimer);
      hideTimer = null;
    }
    setActive(true);
  }

  function scheduleHide(delay) {
    if (hideTimer) clearTimeout(hideTimer);
    hideTimer = setTimeout(function () {
      hideTimer = null;
      if (!doc.querySelector('[data-testid="stSpinner"]')) {
        setActive(false);
      } else {
        scheduleHide(180);
      }
    }, delay || 220);
  }

  function isInteractive(target) {
    if (!target || !target.closest) return false;
    return !!target.closest(
      'button, a[href], input, select, textarea, [role="button"], [role="tab"], label, [data-baseweb="select"]'
    );
  }

  function hasRunningSpinner() {
    const spinners = doc.querySelectorAll('[data-testid="stSpinner"]');
    for (let i = 0; i < spinners.length; i += 1) {
      const text = (spinners[i].textContent || "").toLowerCase();
      if (text.includes("running") || spinners[i].classList.contains("stSpinner")) {
        return true;
      }
    }
    return false;
  }

  doc.addEventListener(
    "click",
    function (event) {
      if (isInteractive(event.target)) showLoading();
    },
    true
  );

  doc.addEventListener(
    "change",
    function (event) {
      if (isInteractive(event.target)) showLoading();
    },
    true
  );

  const mainRoot =
    doc.querySelector('[data-testid="stMain"]') ||
    doc.querySelector('[data-testid="stAppViewContainer"]') ||
    doc.body;

  const observer = new MutationObserver(function () {
    if (hasRunningSpinner()) {
      showLoading();
      return;
    }
    if (active) scheduleHide(240);
  });
  observer.observe(mainRoot, { childList: true, subtree: true, attributes: true });

  w.addEventListener("resize", function () {
    if (layoutTimer) clearTimeout(layoutTimer);
    layoutTimer = setTimeout(layoutNodes, 80);
  });

  layoutNodes();
  setTimeout(layoutNodes, 120);
  setTimeout(layoutNodes, 600);
})();
</script>
            """,
            height=0,
        )


__all__ = ["inject_page_loading_indicator"]
