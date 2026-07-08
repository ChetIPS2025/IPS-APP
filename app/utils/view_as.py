"""Admin-only role preview (session UI override; does not change auth or database role)."""

from __future__ import annotations

import html

import streamlit as st

try:
    from app.auth import current_role
    from app.mobile_ui import IPS_VIEWPORT_NARROW_KEY
    from app.utils.constants import EMPLOYEE_NAV_PAGES
    from app.utils.permissions import normalize_role, role_default_nav_slug
except ImportError:
    from auth import current_role  # type: ignore
    from mobile_ui import IPS_VIEWPORT_NARROW_KEY  # type: ignore
    from utils.constants import EMPLOYEE_NAV_PAGES  # type: ignore
    from utils.permissions import normalize_role, role_default_nav_slug  # type: ignore

IPS_VIEW_AS_ACTIVE_KEY = "ips_view_as_active"
IPS_VIEW_AS_MODE_KEY = "ips_view_as_mode"
IPS_VIEW_AS_ROLE_KEY = "ips_view_as_role"
IPS_VIEW_AS_FORCED_NARROW_KEY = "ips_view_as_forced_narrow"

VIEW_AS_OPTIONS: tuple[tuple[str, str], ...] = (
    ("admin", "Admin"),
    ("supervisor", "Supervisor"),
    ("employee", "Employee"),
    ("field_mobile", "Field Mode (Mobile Preview)"),
)

VIEW_AS_PICKER_SUFFIXES: tuple[str, ...] = ("admin_page", "header_bar", "sidebar", "active_toolbar")

_VIEW_AS_LABELS = {
    "supervisor": "Supervisor",
    "employee": "Employee",
    "field_mobile": "Field Mode (Mobile Preview)",
}


def is_real_admin() -> bool:
    return normalize_role(current_role()) == "admin"


def is_view_as_active() -> bool:
    return is_real_admin() and bool(st.session_state.get(IPS_VIEW_AS_ACTIVE_KEY))


def view_as_mode() -> str:
    return str(st.session_state.get(IPS_VIEW_AS_MODE_KEY) or "").strip()


def is_view_as_mobile_preview() -> bool:
    return is_view_as_active() and view_as_mode() == "field_mobile"


def ui_role() -> str:
    """Role for navigation, page gates, and UI visibility (preview-aware for admins)."""
    if not is_view_as_active():
        return current_role()
    mode = view_as_mode()
    if mode == "supervisor":
        return "supervisor"
    if mode in {"employee", "field_mobile"}:
        return "employee"
    return current_role()


def view_as_display_label() -> str:
    return _VIEW_AS_LABELS.get(view_as_mode(), view_as_mode().replace("_", " ").title())


def _landing_slug_for_mode(mode: str) -> str:
    if mode == "supervisor":
        return role_default_nav_slug("supervisor", field_mode=False)
    if mode in {"employee", "field_mobile"}:
        return role_default_nav_slug("employee", field_mode=False)
    return role_default_nav_slug("admin", field_mode=False)


def _picker_label_for_mode(mode: str) -> str:
    picked = str(mode or "admin").strip().lower()
    for value, label in VIEW_AS_OPTIONS:
        if value == picked:
            return label
    return VIEW_AS_OPTIONS[0][1]


def _active_picker_mode() -> str:
    return view_as_mode() if is_view_as_active() else "admin"


def _clear_view_as_picker_widgets() -> None:
    for suffix in VIEW_AS_PICKER_SUFFIXES:
        st.session_state.pop(f"ips_view_as_select_{suffix}", None)


def ensure_view_as_navigation() -> None:
    """Keep admins on pages allowed by the active preview role."""
    if not is_view_as_active():
        return
    try:
        from app.navigation import current_nav_slug, default_nav_slug, set_nav_slug
        from app.utils.permissions import role_can_access_page
    except ImportError:
        from navigation import current_nav_slug, default_nav_slug, set_nav_slug  # type: ignore
        from utils.permissions import role_can_access_page  # type: ignore
    slug = current_nav_slug()
    role = ui_role()
    if role_can_access_page(role, slug):
        return
    target = default_nav_slug()
    if slug != target and role_can_access_page(role, target):
        set_nav_slug(target)
        st.rerun()


def set_view_as(mode: str) -> None:
    """Activate or clear admin preview mode (session only)."""
    if not is_real_admin():
        return
    picked = str(mode or "admin").strip().lower()
    if picked in {"", "admin"}:
        clear_view_as()
        try:
            from app.navigation import set_nav_slug
        except ImportError:
            from navigation import set_nav_slug  # type: ignore
        set_nav_slug("dashboard")
        _clear_view_as_picker_widgets()
        return

    st.session_state[IPS_VIEW_AS_ACTIVE_KEY] = True
    st.session_state[IPS_VIEW_AS_MODE_KEY] = picked
    st.session_state["ips_field_mode"] = False

    if picked == "supervisor":
        st.session_state[IPS_VIEW_AS_ROLE_KEY] = "supervisor"
        st.session_state.pop(IPS_VIEW_AS_FORCED_NARROW_KEY, None)
    elif picked == "employee":
        st.session_state[IPS_VIEW_AS_ROLE_KEY] = "employee"
        st.session_state.pop(IPS_VIEW_AS_FORCED_NARROW_KEY, None)
    elif picked == "field_mobile":
        st.session_state[IPS_VIEW_AS_ROLE_KEY] = "employee"
        st.session_state[IPS_VIEWPORT_NARROW_KEY] = True
        st.session_state[IPS_VIEW_AS_FORCED_NARROW_KEY] = True
    else:
        clear_view_as()
        return

    try:
        from app.navigation import set_nav_slug
    except ImportError:
        from navigation import set_nav_slug  # type: ignore
    set_nav_slug(_landing_slug_for_mode(picked))
    _clear_view_as_picker_widgets()


def clear_view_as() -> None:
    for key in (IPS_VIEW_AS_ACTIVE_KEY, IPS_VIEW_AS_MODE_KEY, IPS_VIEW_AS_ROLE_KEY):
        st.session_state.pop(key, None)
    if st.session_state.pop(IPS_VIEW_AS_FORCED_NARROW_KEY, None):
        st.session_state.pop(IPS_VIEWPORT_NARROW_KEY, None)
    _clear_view_as_picker_widgets()


def inject_view_as_styles() -> None:
    if not st.session_state.get("_ips_view_as_base_css"):
        st.session_state["_ips_view_as_base_css"] = True
        st.markdown(
            """
<style id="ips-view-as-base-v2">
.ips-view-as-banner-wrap {
  margin: 0 0 0.5rem 0;
}
.ips-view-as-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  flex-wrap: wrap;
  background: linear-gradient(90deg, #eff6ff 0%, #f8fafc 100%);
  border: 1px solid #93c5fd;
  border-left: 4px solid #2563eb;
  border-radius: 10px;
  padding: 0.55rem 0.85rem;
}
.ips-view-as-banner-text {
  margin: 0;
  font-size: 0.84rem;
  font-weight: 700;
  color: #1e3a8a;
}
.ips-view-as-banner-text strong {
  color: #1d4ed8;
}
.ips-view-as-banner-sub {
  margin: 0.1rem 0 0;
  font-size: 0.72rem;
  font-weight: 600;
  color: #475569;
}
.ips-view-as-admin-panel {
  background: #f8fafc;
  border: 1px solid #dbeafe;
  border-left: 4px solid #2563eb;
  border-radius: 12px;
  padding: 0.85rem 1rem;
  margin: 0 0 0.85rem 0;
}
.ips-view-as-admin-title {
  margin: 0 0 0.2rem 0;
  font-size: 0.95rem;
  font-weight: 800;
  color: #1e3a8a;
}
.ips-view-as-admin-copy {
  margin: 0 0 0.65rem 0;
  font-size: 0.78rem;
  color: #475569;
  line-height: 1.4;
}
.ips-view-as-header-bar {
  margin: 0 0 0.35rem 0;
  padding: 0.35rem 0.5rem;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}
.ips-view-as-header-label {
  font-size: 0.72rem;
  font-weight: 700;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin: 0 0 0.15rem 0;
}
.ips-view-as-mobile-nav {
  position: fixed;
  left: 50%;
  transform: translateX(-50%);
  bottom: 0;
  width: min(430px, 100vw);
  z-index: 99990;
  display: flex;
  background: #ffffff;
  border-top: 1px solid #dbeafe;
  box-shadow: 0 -4px 16px rgba(15, 23, 42, 0.08);
  padding: 0.2rem 0.15rem calc(0.2rem + env(safe-area-inset-bottom));
}
.ips-view-as-mobile-nav-btn {
  flex: 1 1 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.1rem;
  min-height: 52px;
  border: none;
  background: transparent;
  color: #64748b;
  font-size: 0.62rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  cursor: pointer;
  padding: 0.2rem 0.1rem;
}
.ips-view-as-mobile-nav-btn .ips-view-as-mobile-nav-icon {
  font-size: 1rem;
  line-height: 1;
}
.ips-view-as-mobile-nav-btn.is-active {
  color: #2563eb;
}
</style>
            """,
            unsafe_allow_html=True,
        )

    marker_classes = "ips-view-as-marker"
    mobile_css = """
<style id="ips-view-as-mobile-v2">
html.ips-view-as-mobile-active section[data-testid="stMain"],
section[data-testid="stMain"]:has(.ips-view-as-mobile-active) {
  max-width: 430px !important;
  margin: 0 auto !important;
  box-shadow: 0 0 0 1px #dbeafe, 0 12px 40px rgba(37, 99, 235, 0.12) !important;
  border-radius: 16px !important;
  overflow: hidden !important;
  padding-bottom: 4.25rem !important;
}
html.ips-view-as-mobile-active section[data-testid="stMain"] .ips-jobs-summary-cards,
section[data-testid="stMain"]:has(.ips-view-as-mobile-active) .ips-jobs-summary-cards {
  grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
}
html.ips-view-as-mobile-active .ips-desktop-nav-rail {
  display: none !important;
}
</style>
"""
    mobile_on = "true" if is_view_as_mobile_preview() else "false"
    if is_view_as_mobile_preview():
        marker_classes += " ips-view-as-mobile-active"
    st.markdown(
        f"""
{mobile_css}
<script>
(function () {{
  try {{
    var root = document.documentElement;
    if (!root) return;
    root.classList.toggle("ips-view-as-mobile-active", {mobile_on});
  }} catch (e) {{}}
}})();
</script>
<span class="{marker_classes}" aria-hidden="true"></span>
        """,
        unsafe_allow_html=True,
    )


def render_view_as_banner() -> None:
    if not is_view_as_active():
        return
    render_view_as_active_toolbar()


def render_view_as_active_toolbar() -> None:
    """Prominent preview status bar with role picker and Return to Admin."""
    if not is_view_as_active():
        return
    inject_view_as_styles()
    label = html.escape(view_as_display_label())
    st.markdown(
        f"""
<div class="ips-view-as-banner-wrap">
  <div class="ips-view-as-banner">
    <div>
      <p class="ips-view-as-banner-text">Viewing As: <strong>{label}</strong> (Preview Mode)</p>
      <p class="ips-view-as-banner-sub">UI preview only — your signed-in role is still Admin.</p>
    </div>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )
    picker_col, return_col = st.columns([5, 1], gap="small")
    with picker_col:
        _render_view_as_picker(key_suffix="active_toolbar", show_help=True)
    with return_col:
        if st.button("Return to Admin", key="ips_view_as_return_admin", type="primary", use_container_width=True):
            clear_view_as()
            try:
                from app.navigation import set_nav_slug
            except ImportError:
                from navigation import set_nav_slug  # type: ignore
            set_nav_slug("dashboard")
            st.rerun()


def _render_view_as_picker(*, key_suffix: str, show_help: bool = False) -> None:
    labels = [label for _, label in VIEW_AS_OPTIONS]
    values = [value for value, _ in VIEW_AS_OPTIONS]
    active_mode = _active_picker_mode()
    widget_key = f"ips_view_as_select_{key_suffix}"
    expected_label = _picker_label_for_mode(active_mode)
    if st.session_state.get(widget_key) not in labels:
        st.session_state[widget_key] = expected_label
    picked_label = st.selectbox(
        "View As",
        labels,
        value=st.session_state.get(widget_key, expected_label),
        key=widget_key,
        help=(
            "Preview the app as another role without changing your signed-in account."
            if show_help
            else None
        ),
        label_visibility="collapsed",
    )
    picked_mode = values[labels.index(picked_label)]
    if picked_mode != active_mode:
        set_view_as(picked_mode)
        st.rerun()


def render_view_as_admin_panel() -> None:
    """Prominent View As control on the Admin page."""
    if not is_real_admin():
        return
    inject_view_as_styles()
    st.markdown(
        """
<div class="ips-view-as-admin-panel">
  <p class="ips-view-as-admin-title">View As (Preview Mode)</p>
  <p class="ips-view-as-admin-copy">
    Safely preview Supervisor, Employee, or mobile field workflows. This only changes what you see in the UI —
    your account stays Admin and nothing is written to the database.
  </p>
</div>
        """,
        unsafe_allow_html=True,
    )
    _render_view_as_picker(key_suffix="admin_page", show_help=True)


def render_view_as_header_bar() -> None:
    """Compact View As picker below the main brand bar (admin only, preview off)."""
    if not is_real_admin() or is_view_as_active():
        return
    inject_view_as_styles()
    with st.container(key="ips_view_as_header_bar"):
        st.markdown(
            '<p class="ips-view-as-header-label">Admin preview</p>',
            unsafe_allow_html=True,
        )
        _render_view_as_picker(key_suffix="header_bar", show_help=True)


def render_view_as_selector() -> None:
    """Sidebar control — admin only."""
    if not is_real_admin():
        return
    inject_view_as_styles()
    st.markdown('<p class="sidebar-section-title sidebar-footer-label section-header">View As</p>', unsafe_allow_html=True)
    _render_view_as_picker(key_suffix="sidebar")


def render_view_as_mobile_bottom_nav(active_slug: str) -> None:
    if not is_view_as_mobile_preview():
        return
    icons = {
        "employee_portal": "🏠",
        "employee_qr_scan": "📷",
        "employee_resources": "📚",
        "employee_profile": "👤",
    }
    parts: list[str] = ['<nav class="ips-view-as-mobile-nav" aria-label="Employee mobile preview">']
    for slug, label in EMPLOYEE_NAV_PAGES:
        active = " is-active" if slug == active_slug else ""
        parts.append(
            f'<button type="button" class="ips-view-as-mobile-nav-btn{active}" '
            f'data-view-as-nav="{html.escape(slug, quote=True)}">'
            f'<span class="ips-view-as-mobile-nav-icon">{icons.get(slug, "•")}</span>'
            f"<span>{html.escape(label)}</span></button>"
        )
    parts.append("</nav>")
    st.markdown("".join(parts), unsafe_allow_html=True)

    picked = st.session_state.get("ips_view_as_mobile_nav_pick")
    if picked and str(picked) != active_slug:
        st.session_state.pop("ips_view_as_mobile_nav_pick", None)
        try:
            from app.navigation import set_nav_slug
        except ImportError:
            from navigation import set_nav_slug  # type: ignore
        set_nav_slug(str(picked))
        st.rerun()

    try:
        from app.ui.clean_table import _components_html
    except ImportError:
        from ui.clean_table import _components_html  # type: ignore

    nav_pick = _components_html(
        """
<script>
(function () {
  const doc = document;
  function bind() {
    doc.querySelectorAll("[data-view-as-nav]").forEach(function (btn) {
      if (btn.dataset.ipsViewAsNavBound === "1") return;
      btn.dataset.ipsViewAsNavBound = "1";
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        const slug = btn.getAttribute("data-view-as-nav");
        if (!slug) return;
        const payload = { type: "streamlit:setComponentValue", value: slug };
        try {
          if (window.Streamlit && window.Streamlit.setComponentValue) {
            window.Streamlit.setComponentValue(slug);
            return;
          }
        } catch (err) {}
        try { window.parent.postMessage(payload, "*"); } catch (err) {}
      });
    });
  }
  bind();
  if (!doc.ipsViewAsNavObserver) {
    doc.ipsViewAsNavObserver = new MutationObserver(bind);
    doc.ipsViewAsNavObserver.observe(doc.body, { childList: true, subtree: true });
  }
})();
</script>
        """,
        component_key="ips_view_as_mobile_nav",
        height=0,
    )
    if nav_pick:
        st.session_state["ips_view_as_mobile_nav_pick"] = str(nav_pick)
