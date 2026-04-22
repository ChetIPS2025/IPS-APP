"""
Browser-oriented device labels for audit (e.g. inventory QR scans).

True OS hostnames are not exposed to web apps; we combine a rough UA family
(iPhone, Windows-PC, …) with a short stable id. Cross-session stability uses
localStorage in the bootstrap script + optional ``?ipsdev=`` query bootstrap
(see ``maybe_bootstrap_inventory_device`` in inventory_scan).
"""
from __future__ import annotations

import json
import re
import secrets
import string

import streamlit as st

_LS_KEY = "ips_inv_device_suffix_v1"
_QP = "ipsdev"


def request_user_agent() -> str:
    """Best-effort User-Agent from Streamlit request context (Streamlit >= 1.33)."""
    try:
        ctx = getattr(st, "context", None)
        if ctx is None:
            return ""
        hdrs = getattr(ctx, "headers", None)
        if hdrs is None:
            return ""
        if hasattr(hdrs, "get"):
            return str(hdrs.get("User-Agent") or hdrs.get("user-agent") or "")[:2000]
        return str(hdrs)[:2000]
    except Exception:
        return ""


def device_family_from_user_agent(ua: str) -> str:
    """Rough device / OS class from User-Agent (privacy-safe)."""
    u = (ua or "").lower()
    if "ipad" in u or ("macintosh" in u and "tablet" in u):
        return "iPad"
    if "iphone" in u or "ipod" in u:
        return "iPhone"
    if "android" in u:
        return "Android"
    if "windows phone" in u:
        return "Windows-Phone"
    if "windows" in u or "win64" in u or "wow64" in u:
        return "Windows-PC"
    if "mac os x" in u or "macintosh" in u:
        return "Mac"
    if "cros" in u or "chromeos" in u:
        return "Chromebook"
    if "linux" in u or "x11" in u:
        return "Linux"
    return "Unknown-Device"


def normalize_suffix(raw: str | None) -> str:
    """4–6 uppercase alphanumeric chars for display suffix."""
    s = re.sub(r"[^A-Za-z0-9]", "", str(raw or "")).upper()
    if len(s) > 6:
        s = s[:6]
    while len(s) < 4:
        s += secrets.choice(string.ascii_uppercase + string.digits)
    return s[:6]


def auto_device_label(user_agent: str, existing_suffix: str | None = None) -> str:
    """
    Human-friendly label: ``{Family}-{SUFFIX}`` e.g. ``iPhone-7F3A``, ``Windows-PC-91B2``.
    """
    fam = device_family_from_user_agent(user_agent)
    if existing_suffix and str(existing_suffix).strip():
        suf = normalize_suffix(str(existing_suffix))
    else:
        suf = normalize_suffix(secrets.token_hex(2).upper())
    return f"{fam}-{suf}"


def format_device_label(family: str, suffix: str) -> str:
    return f"{(family or 'Unknown-Device').replace(' ', '-')}-{normalize_suffix(suffix)}"


def _query_param_first(name: str) -> str | None:
    try:
        qp = st.query_params.get(name)
    except Exception:
        return None
    if qp is None:
        return None
    if isinstance(qp, list):
        return str(qp[0]) if qp else None
    return str(qp)


def try_consume_device_suffix_from_query() -> bool:
    """
    If ``?ipsdev=`` is present, persist normalized suffix to session_state and remove the param.
    Returns True if a rerun is recommended (URL cleanup).
    """
    raw = _query_param_first(_QP)
    if not raw:
        return False
    st.session_state["ips_inv_device_suffix"] = normalize_suffix(str(raw))
    try:
        del st.query_params[_QP]
    except Exception:
        try:
            st.query_params.pop(_QP, None)  # type: ignore[attr-defined]
        except Exception:
            pass
    return True


def inventory_device_bootstrap_html() -> str:
    """JS: reuse suffix from localStorage or create one; redirect parent with ``?ipsdev=`` once."""
    # Same-origin parent navigation; localStorage is per-origin (persists across Streamlit sessions).
    return f"""
<div></div>
<script>
(function () {{
  const LS = "{_LS_KEY}";
  const QP = "{_QP}";
  try {{
    const parent = window.parent;
    const u = new URL(parent.location.href);
    if (u.searchParams.get(QP)) return;
    let s = null;
    try {{ s = window.localStorage.getItem(LS); }} catch (e) {{}}
    if (!s) {{
      s = Math.random().toString(36).slice(2, 6).toUpperCase();
      if (s.length < 4) s = (s + "X7K2").slice(0, 4);
      try {{ window.localStorage.setItem(LS, s); }} catch (e) {{}}
    }}
    u.searchParams.set(QP, s);
    parent.location.replace(u.toString());
  }} catch (e) {{}}
}})();
</script>
"""


def ensure_inventory_device_suffix_initialized() -> None:
    """
    Ensure ``st.session_state['ips_inv_device_suffix']`` exists: consume ``?ipsdev=``,
    or run one-shot localStorage + redirect bootstrap, or fall back to a server-only suffix.
    """
    key = "ips_inv_device_suffix"
    if key in st.session_state:
        return
    if try_consume_device_suffix_from_query():
        st.rerun()
    if not st.session_state.get("_ips_inv_boot_attempted"):
        st.session_state["_ips_inv_boot_attempted"] = True
        import streamlit.components.v1 as components

        components.html(inventory_device_bootstrap_html(), height=0, width=0)
        st.info("Establishing a stable device id for this browser…")
        st.stop()
    st.session_state[key] = normalize_suffix(secrets.token_hex(2).upper())


def persist_device_label_to_browser(label: str) -> None:
    """Best-effort: store user-chosen full label in localStorage for the same origin."""
    try:
        import streamlit.components.v1 as components
    except ImportError:
        return
    safe = json.dumps(str(label or "")[:200])
    components.html(
        f"""
<script>
try {{
  localStorage.setItem("ips_inv_device_display_v1", {safe});
}} catch (e) {{}}
</script>
""",
        height=0,
        width=0,
    )
