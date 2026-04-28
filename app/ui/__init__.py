from __future__ import annotations

from pathlib import Path
import streamlit as st

from auth import current_profile, current_role, sign_out

try:
    from app.mobile_ui import inject_ips_global_mobile_css, inject_sidebar_mobile_auto_collapse_once
    from app.pwa import render_install_app_sidebar_block
except ImportError:
    from mobile_ui import inject_ips_global_mobile_css, inject_sidebar_mobile_auto_collapse_once  # type: ignore
    from pwa import render_install_app_sidebar_block  # type: ignore

def _repo_root() -> Path:
    """Resolve repository root whether this module is ``app/ui/__init__.py`` or legacy ``app/ui.py``."""
    p = Path(__file__).resolve()
    if p.parent.name == "ui":
        return p.parents[2]
    return p.parents[1]


def _find_round_logo() -> Path | None:
    root = _repo_root()
    search_paths = [
        root / "assets" / "ips_logo_round.png",
        root / "assets" / "IPS LOGO ROUND.png",
        root / "assets" / "ips_logo.png",
        root / "assets" / "logo.png",
    ]
    for path in search_paths:
        if path.exists():
            return path
    return None


# Set from pages after save/actions; consumed in apply_pending_navigation() before render_sidebar().
IPS_NAV_PENDING_KEY = "ips_nav_pending"
# When Asset Detail is not a sidebar option, main() uses this to render the detail page.
IPS_ACTIVE_PAGE_KEY = "ips_active_page"
# Current sidebar page (one of IPS_SIDEBAR_PAGES). Replaces legacy key "ips_nav_radio".
IPS_NAV_PAGE_KEY = "ips_nav_page"

# ---- Sidebar structure (simple, field + office friendly) ----
# Keep routes separate from sidebar visibility so deep links / pending-nav still work.
_NAV_PRIMARY: tuple[str, ...] = ("Dashboard",)

# Jobs (sidebar)
_NAV_JOBS_SIDEBAR: tuple[str, ...] = ("Job Database", "Estimates", "Job Costing")

# Assets (sidebar)
_NAV_ASSETS_SIDEBAR: tuple[str, ...] = ("Asset Database", "Scan", "Tool Trailer Audits")

# Inventory expander (sidebar)
_NAV_INVENTORY_SIDEBAR: tuple[str, ...] = ("Inventory List", "Scan Inventory", "Inventory Usage")

# Admin / office tools (sidebar)
_NAV_ADMIN_SIDEBAR: tuple[str, ...] = ("Users", "Time Tracking", "Weekly Timesheet", "PO / Expenses")

# Pages that remain routable (deep links / internal navigation) but are not shown in the simplified sidebar.
_NAV_HIDDEN_ROUTES: tuple[str, ...] = (
    "People",
    "Employees",
    "Employee Toolbox",
    "PM Matrix Time Entry",
    "Labor",
    "Customers",
    "Asset Scanner",
    "Admin",
    "Asset Detail",
    "Asset Manager",
)

# All keys that may appear in the sidebar or session for routing validation.
_NAV_JOBS_ROUTES: tuple[str, ...] = ("Job Database", "Estimates", "Customers", "Job Costing")
# Routable asset-area pages (Who Has What moved to Dashboard; still routable for View All).
_NAV_ASSET_ROUTES: tuple[str, ...] = ("Asset Database", "Who Has What", "Tool Trailer Audits")
# Sidebar shortcuts → Asset Database + ``asset_db_f_asset_category`` (assets are rows in ``assets``).
_NAV_ASSET_CATEGORY_FOCUS: tuple[tuple[str, str], ...] = (
    ("All assets", "All"),
    ("Equipment", "Equipment"),
    ("Trailer", "Trailer"),
    ("Vehicle", "Vehicle"),
    ("Tool", "Tool"),
)
# Labor catalog. Materials are **inventory_items** with ``category`` = Materials (see Inventory).
# Inventory / Supplies: stocked consumables (separate from Asset Database).
_NAV_RESOURCES: tuple[str, ...] = ("Inventory",)

# Inventory sub-pages (kept routable, but nested under Inventory in the sidebar UI).
_NAV_INVENTORY_SUBPAGES: tuple[str, ...] = ("Scan Inventory", "Inventory Usage")

# Role-based page access (UI hiding + routing validation; main.py enforces too).
# Supported roles: admin, manager, employee, viewer.
_ROLE_ALLOWED_PAGES: dict[str, frozenset[str]] = {
    "admin": frozenset(
        {
            *_NAV_PRIMARY,
            *_NAV_JOBS_ROUTES,
            *_NAV_ASSET_ROUTES,
            *_NAV_RESOURCES,
            "Admin",
            "Users",
            "Asset Detail",
            "Asset Manager",
            "Scan Inventory",
            "Inventory Usage",
            "Time Tracking",
            "Weekly Timesheet",
            "PO / Expenses",
            "Tool Trailer Audits",
            # legacy / power-user routes kept routable
            "People",
            "Employees",
            "Employee Toolbox",
            "PM Matrix Time Entry",
            "Labor",
            "Asset Scanner",
            "Customers",
        }
    ),
    "manager": frozenset(
        {
            "Dashboard",
            "Job Database",
            "Estimates",
            "Job Costing",
            "Scan Inventory",
            "Who Has What",
            "Asset Database",
            "Tool Trailer Audits",
            # Add reporting pages here when present
        }
    ),
    "employee": frozenset(
        {
            "Dashboard",
            "Time Tracking",
            "Asset Database",
            "Scan Inventory",
            "Inventory Usage",
            "Who Has What",
            "Tool Trailer Audits",
            # legacy routes kept routable (not necessarily in sidebar)
            "Employee Toolbox",
        }
    ),
    "viewer": frozenset({"Dashboard", "Inventory Usage", "Who Has What", "Asset Database"}),
}


def role_can_open_page(role: str, page: str) -> bool:
    r = str(role or "viewer").strip().lower()
    if r in {"pm", "estimator"}:
        r = "manager"
    allowed = _ROLE_ALLOWED_PAGES.get(r)
    if allowed is None:
        allowed = _ROLE_ALLOWED_PAGES.get("viewer", frozenset())
    return str(page or "").strip() in allowed

IPS_SIDEBAR_PAGES: tuple[str, ...] = (
    _NAV_PRIMARY
    + _NAV_JOBS_ROUTES
    + _NAV_ASSET_ROUTES
    + _NAV_RESOURCES
    + _NAV_ADMIN_SIDEBAR
    + _NAV_HIDDEN_ROUTES
)

# Keep Inventory sub-pages routable even though they are nested under "Inventory" in the sidebar.
IPS_SIDEBAR_PAGES = IPS_SIDEBAR_PAGES + _NAV_INVENTORY_SUBPAGES


def _nav_btn_key(page: str) -> str:
    return "ips_nav__" + page.replace(" ", "_").replace("/", "_")


def _sidebar_display_label(route_key: str) -> str:
    """Visible sidebar label; route/session keys stay unchanged (e.g. People → Users)."""
    if route_key == "People":
        return "Users"
    return route_key


def _visible_secondary_pages(role: str) -> tuple[str, ...]:
    # Secondary expander removed; keep function for compatibility (no pages).
    _ = role
    return tuple()


def apply_pending_navigation() -> None:
    """Apply a deferred sidebar selection change before the sidebar nav is rendered."""
    pending = st.session_state.pop(IPS_NAV_PENDING_KEY, None)
    if pending == "Tool Checkout":
        pending = "Scan Inventory"
    if not pending:
        return
    if pending == "Users":
        st.session_state[IPS_NAV_PAGE_KEY] = "People"
        st.session_state["people_section_radio"] = "User accounts"
        st.session_state.pop(IPS_ACTIVE_PAGE_KEY, None)
        return
    if pending == "Employees":
        st.session_state[IPS_NAV_PAGE_KEY] = "People"
        st.session_state["people_section_radio"] = "Employees"
        st.session_state.pop(IPS_ACTIVE_PAGE_KEY, None)
        return
    if pending == "Materials":
        st.session_state[IPS_NAV_PAGE_KEY] = "Inventory"
        st.session_state["inv_f_cat"] = "Materials"
        st.session_state.pop(IPS_ACTIVE_PAGE_KEY, None)
        return
    if pending == "Asset Detail":
        st.session_state[IPS_ACTIVE_PAGE_KEY] = "Asset Detail"
        st.session_state[IPS_NAV_PAGE_KEY] = "Asset Database"
        st.session_state["_ips_skip_nav_overlay_clear"] = True
    elif pending == "Asset Manager":
        st.session_state[IPS_ACTIVE_PAGE_KEY] = "Asset Manager"
        st.session_state[IPS_NAV_PAGE_KEY] = "Asset Database"
        st.session_state["_ips_skip_nav_overlay_clear"] = True
    else:
        st.session_state[IPS_NAV_PAGE_KEY] = pending
        st.session_state.pop(IPS_ACTIVE_PAGE_KEY, None)


def _sidebar_brand() -> None:
    logo_path = _find_round_logo()

    if logo_path and logo_path.exists():
        st.sidebar.image(str(logo_path), width=72)

    st.sidebar.markdown("### IPS Estimating")
    st.sidebar.caption("Industrial Plant Solutions")


def _inject_sidebar_nav_css() -> None:
    st.sidebar.markdown(
        """
<style>
/* Primary: section titles */
section[data-testid="stSidebar"] .ips-nav-section-title {
  color: #FFFFFF;
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  margin: 0 0 6px 0;
  padding: 0;
  line-height: 1.3;
}
section[data-testid="stSidebar"] .ips-nav-group-spaced {
  margin-top: 16px !important;
  padding-top: 14px !important;
  border-top: 1px solid rgba(110, 145, 190, 0.22);
}
/* Divider + air gap: primary vs TOOLS */
section[data-testid="stSidebar"] .ips-nav-primary-secondary-divider {
  margin: 28px 0 14px 0;
  padding: 0;
  border: none;
  border-top: 1px solid rgba(110, 145, 190, 0.22);
  box-shadow: 0 1px 0 0 rgba(255, 255, 255, 0.03);
  opacity: 1;
}
/* Primary nav buttons — align with main IPS button rhythm (height, radius, no wrap) */
section[data-testid="stSidebar"] div.stButton > button {
  font-size: 0.875rem !important;
  font-weight: 600 !important;
  min-height: 2.25rem !important;
  padding: 0.35rem 0.75rem !important;
  border-radius: 8px !important;
  line-height: 1.25 !important;
  box-sizing: border-box !important;
}
section[data-testid="stSidebar"] div.stButton > button p {
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  margin: 0 !important;
}
section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] div.stButton > button {
  font-size: 0.8125rem !important;
  font-weight: 500 !important;
  min-height: 2.25rem !important;
  padding: 0.35rem 0.65rem !important;
  border-radius: 8px !important;
  margin-left: 2px !important;
  border-left: 3px solid rgba(110, 145, 190, 0.26) !important;
  padding-left: 10px !important;
  box-sizing: border-box !important;
}
section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] div.stButton > button[kind="primary"] {
  border-left-color: #60a5fa !important;
}
section[data-testid="stSidebar"] button[kind="primary"] {
  background: linear-gradient(180deg, #1e3a8a 0%, #1d4ed8 100%) !important;
  color: #f8fafc !important;
  border: 1px solid #3b82f6 !important;
  box-shadow: inset 3px 0 0 0 #60a5fa !important;
}
section[data-testid="stSidebar"] button[kind="secondary"] {
  background: #14365C !important;
  color: #C0CAD8 !important;
  border: 1px solid rgba(120, 150, 200, 0.25) !important;
}
section[data-testid="stSidebar"] button[kind="secondary"]:hover {
  border-color: rgba(120, 150, 200, 0.35) !important;
  color: #FFFFFF !important;
  background: #1A3F6B !important;
}
/* TOOLS expander: muted label + chrome */
section[data-testid="stSidebar"] [data-testid="stExpander"] details {
  border: 1px solid rgba(110, 145, 190, 0.22) !important;
  border-radius: 6px !important;
  background: rgba(18, 47, 82, 0.35) !important;
  margin-top: 2px !important;
}
section[data-testid="stSidebar"] [data-testid="stExpander"] summary {
  font-size: 0.65rem !important;
  font-weight: 700 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.1em !important;
  color: rgba(159, 176, 199, 0.9) !important;
  opacity: 0.88 !important;
  padding: 8px 10px !important;
}
section[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stExpanderDetails"] {
  padding: 2px 8px 12px 8px !important;
}
/* Secondary tools: compact but same radius / nowrap as main chrome */
section[data-testid="stSidebar"] [data-testid="stExpander"] div.stButton > button[kind="secondary"] {
  font-size: 0.8125rem !important;
  font-weight: 500 !important;
  min-height: 2.125rem !important;
  padding: 0.28rem 0.6rem !important;
  border-radius: 8px !important;
  opacity: 0.92 !important;
  color: rgba(192, 202, 216, 0.92) !important;
  background: rgba(18, 47, 82, 0.45) !important;
  border: 1px solid rgba(140, 175, 220, 0.22) !important;
  box-shadow: none !important;
}
section[data-testid="stSidebar"] [data-testid="stExpander"] div.stButton > button[kind="secondary"]:hover {
  color: #FFFFFF !important;
  border-color: rgba(170, 205, 240, 0.35) !important;
  opacity: 1 !important;
}
/* Active tool: same treatment as primary nav buttons */
section[data-testid="stSidebar"] [data-testid="stExpander"] div.stButton > button[kind="primary"] {
  font-size: 0.875rem !important;
  font-weight: 600 !important;
  min-height: 2.25rem !important;
  padding: 0.35rem 0.75rem !important;
  border-radius: 8px !important;
  opacity: 1 !important;
  color: #f8fafc !important;
  background: linear-gradient(180deg, #1e3a8a 0%, #1d4ed8 100%) !important;
  border: 1px solid #3b82f6 !important;
  box-shadow: inset 3px 0 0 0 #60a5fa !important;
}
section[data-testid="stSidebar"] .ips-nav-signout-spacer {
  height: 12px;
}
section[data-testid="stSidebar"] .ips-install-section-title {
  color: #FFFFFF;
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  margin: 10px 0 4px 0;
  padding: 0;
  line-height: 1.3;
}
</style>
        """,
        unsafe_allow_html=True,
    )


def _migrate_legacy_nav_session_keys() -> None:
    """One-time migration from removed sidebar era (ips_nav_radio → ips_nav_page)."""
    if IPS_NAV_PAGE_KEY not in st.session_state:
        legacy = st.session_state.pop("ips_nav_radio", None)
        if legacy is not None:
            st.session_state[IPS_NAV_PAGE_KEY] = legacy


def _ensure_valid_nav_page() -> None:
    _migrate_legacy_nav_session_keys()
    cur0 = st.session_state.get(IPS_NAV_PAGE_KEY)
    if cur0 == "Users":
        st.session_state[IPS_NAV_PAGE_KEY] = "People"
        st.session_state["people_section_radio"] = "User accounts"
    elif cur0 == "Employees":
        st.session_state[IPS_NAV_PAGE_KEY] = "People"
        st.session_state["people_section_radio"] = "Employees"
    elif cur0 == "Inventory scan":
        st.session_state[IPS_NAV_PAGE_KEY] = "Scan Inventory"
    elif cur0 == "Materials":
        st.session_state[IPS_NAV_PAGE_KEY] = "Inventory"
        st.session_state["inv_f_cat"] = "Materials"
    elif cur0 == "Equipment":
        # Legacy standalone route; equipment is managed in Asset Database (category = Equipment).
        st.session_state[IPS_NAV_PAGE_KEY] = "Asset Database"
        st.session_state["asset_db_f_asset_category"] = "Equipment"
    elif cur0 == "Tool Checkout":
        st.session_state[IPS_NAV_PAGE_KEY] = "Scan Inventory"

    role = current_role()
    visible_secondary = set(_visible_secondary_pages(role))
    visible_all = set(
        p
        for p in (
            set(_NAV_PRIMARY)
            | set(_NAV_JOBS)
            | set(_NAV_ASSET_ROUTES)
            | set(_NAV_RESOURCES)
            | set(_NAV_INVENTORY_SUBPAGES)
            | visible_secondary
        )
        if role_can_open_page(role, p)
    )

    cur = st.session_state.get(IPS_NAV_PAGE_KEY)
    routable = frozenset(IPS_SIDEBAR_PAGES) | {"Admin"}
    if cur not in routable:
        st.session_state[IPS_NAV_PAGE_KEY] = IPS_SIDEBAR_PAGES[0]
        return

    admin_only_routes = {"Admin"} if role == "admin" else frozenset()
    if cur not in visible_all and cur not in admin_only_routes:
        st.session_state[IPS_NAV_PAGE_KEY] = "Dashboard"


def _render_nav_button(page: str, *, current: str, indent: bool) -> None:
    active = current == page
    btn_type = "primary" if active else "secondary"
    key = _nav_btn_key(page)
    if indent:
        _, c2 = st.sidebar.columns([0.06, 0.94])
        with c2:
            if st.button(page, key=key, type=btn_type, use_container_width=True):
                st.session_state[IPS_NAV_PAGE_KEY] = page
                st.rerun()
    else:
        if st.sidebar.button(page, key=key, type=btn_type, use_container_width=True):
            st.session_state[IPS_NAV_PAGE_KEY] = page
            st.rerun()


def _render_nav_button_route(*, label: str, route: str, current: str, indent: bool, key_suffix: str) -> None:
    """Render a nav button whose label differs from its route key."""
    active = current == route
    btn_type = "primary" if active else "secondary"
    key = _nav_btn_key(route + "__" + key_suffix)
    if indent:
        _, c2 = st.sidebar.columns([0.06, 0.94])
        with c2:
            if st.button(label, key=key, type=btn_type, use_container_width=True):
                st.session_state[IPS_NAV_PAGE_KEY] = route
                st.rerun()
    else:
        if st.sidebar.button(label, key=key, type=btn_type, use_container_width=True):
            st.session_state[IPS_NAV_PAGE_KEY] = route
            st.rerun()


def _sidebar_asset_category_focus_norm() -> str:
    v = str(st.session_state.get("asset_db_f_asset_category") or "All").strip()
    if not v or v.lower() == "all":
        return "All"
    return v


def _sidebar_inventory_category_focus_norm() -> str:
    v = str(st.session_state.get("inv_f_cat") or "All").strip()
    if not v or v.lower() == "all":
        return "All"
    return v


def _render_assets_sidebar_group(*, current: str, role: str) -> None:
    """Asset Database + category lenses (same ``assets`` table as the main list)."""
    if not role_can_open_page(role, "Asset Database"):
        return
    focus = _sidebar_asset_category_focus_norm()
    assets_expanded = current == "Asset Database"
    with st.sidebar.expander("Assets", expanded=assets_expanded):
        for nav_label, cat in _NAV_ASSET_CATEGORY_FOCUS:
            cat_norm = "All" if cat == "All" else cat
            active = current == "Asset Database" and (
                (cat_norm == "All" and focus == "All")
                or (cat_norm != "All" and focus.lower() == cat_norm.lower())
            )
            btn_type = "primary" if active else "secondary"
            key = _nav_btn_key(f"Asset_Database__focus_{cat_norm}")
            if st.button(nav_label, key=key, type=btn_type, use_container_width=True):
                st.session_state[IPS_NAV_PAGE_KEY] = "Asset Database"
                st.session_state["asset_db_f_asset_category"] = "All" if cat_norm == "All" else cat_norm
                st.rerun()


def render_sidebar() -> str:
    _sidebar_brand()

    profile = current_profile()
    st.sidebar.caption(f"Logged in as: {profile.get('email', '—')}")
    st.sidebar.caption(f"Role: {profile.get('role', 'viewer')}")

    render_install_app_sidebar_block()

    _ensure_valid_nav_page()
    _inject_sidebar_nav_css()
    inject_ips_global_mobile_css()
    inject_sidebar_mobile_auto_collapse_once()

    current = st.session_state[IPS_NAV_PAGE_KEY]
    role = current_role()
    # --- PRIMARY: Dashboard ---
    st.sidebar.markdown(
        '<div class="ips-nav-section-title">Dashboard</div>',
        unsafe_allow_html=True,
    )
    _render_nav_button("Dashboard", current=current, indent=False)

    # --- PRIMARY: Jobs ---
    st.sidebar.markdown(
        '<div class="ips-nav-section-title ips-nav-group-spaced">Jobs</div>',
        unsafe_allow_html=True,
    )
    for p in _NAV_JOBS_SIDEBAR:
        if role_can_open_page(role, p):
            _render_nav_button(p, current=current, indent=True)

    # --- PRIMARY: Assets ---
    st.sidebar.markdown(
        '<div class="ips-nav-section-title ips-nav-group-spaced">Assets</div>',
        unsafe_allow_html=True,
    )
    if role_can_open_page(role, "Asset Database"):
        # Keep category lenses under Assets.
        _render_assets_sidebar_group(current=current, role=role)
    if role_can_open_page(role, "Scan Inventory"):
        _render_nav_button_route(label="Scan", route="Scan Inventory", current=current, indent=True, key_suffix="scan")
    if role_can_open_page(role, "Tool Trailer Audits"):
        _render_nav_button("Tool Trailer Audits", current=current, indent=True)

    # --- PRIMARY: Inventory ---
    st.sidebar.markdown(
        '<div class="ips-nav-section-title ips-nav-group-spaced">Inventory</div>',
        unsafe_allow_html=True,
    )
    inv_expanded = current in ("Inventory", *_NAV_INVENTORY_SUBPAGES)
    if role_can_open_page(role, "Inventory") or any(role_can_open_page(role, p) for p in _NAV_INVENTORY_SUBPAGES):
        with st.sidebar.expander("Inventory", expanded=inv_expanded):
            # Nested links only under this expander (no standalone Scan / Usage in the sidebar).
            _, inv_inner = st.columns([0.06, 0.94])
            with inv_inner:
                _inv_focus = _sidebar_inventory_category_focus_norm()
                inv_list_active = current == "Inventory" and _inv_focus == "All"
                if role_can_open_page(role, "Inventory"):
                    if st.button(
                        "Inventory List",
                        key=_nav_btn_key("Inventory__list_all"),
                        type="primary" if inv_list_active else "secondary",
                        use_container_width=True,
                    ):
                        st.session_state[IPS_NAV_PAGE_KEY] = "Inventory"
                        st.session_state["inv_f_cat"] = "All"
                        st.rerun()
                if role_can_open_page(role, "Scan Inventory"):
                    if st.button(
                        "Scan Inventory",
                        key=_nav_btn_key("Scan Inventory"),
                        type="primary" if current == "Scan Inventory" else "secondary",
                        use_container_width=True,
                    ):
                        st.session_state[IPS_NAV_PAGE_KEY] = "Scan Inventory"
                        st.rerun()
                if role_can_open_page(role, "Inventory Usage"):
                    if st.button(
                        "Inventory Usage",
                        key=_nav_btn_key("Inventory Usage"),
                        type="primary" if current == "Inventory Usage" else "secondary",
                        use_container_width=True,
                    ):
                        st.session_state[IPS_NAV_PAGE_KEY] = "Inventory Usage"
                        st.rerun()

    # --- PRIMARY: Admin / office ---
    st.sidebar.markdown(
        '<div class="ips-nav-section-title ips-nav-group-spaced">Admin</div>',
        unsafe_allow_html=True,
    )
    for p in _NAV_ADMIN_SIDEBAR:
        if role_can_open_page(role, p):
            # Users is the route key already; Time Tracking / Weekly Timesheet / PO are direct routes too.
            _render_nav_button(p, current=current, indent=True)

    st.sidebar.markdown('<div class="ips-nav-signout-spacer"></div>', unsafe_allow_html=True)
    st.sidebar.button("Sign Out", on_click=sign_out, use_container_width=True)
    return current
