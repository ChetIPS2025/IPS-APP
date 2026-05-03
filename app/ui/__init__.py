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
_NAV_JOBS_SIDEBAR: tuple[str, ...] = (
    "Job Database",
    "Assign Tasks (PM)",
    "Work & Plan (Supervisor)",
    "Estimates",
    "Job Costing",
)

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
_NAV_JOBS_ROUTES: tuple[str, ...] = (
    "Job Database",
    "Assign Tasks (PM)",
    "Work & Plan (Supervisor)",
    "Estimates",
    "Customers",
    "Job Costing",
)
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
            "Assign Tasks (PM)",
            "Work & Plan (Supervisor)",
        }
    ),
    "manager": frozenset(
        {
            "Dashboard",
            "Job Database",
            "Assign Tasks (PM)",
            "Work & Plan (Supervisor)",
            "Estimates",
            "Job Costing",
            "Inventory",
            "Scan Inventory",
            "Inventory Usage",
            "Who Has What",
            "Asset Database",
            "Tool Trailer Audits",
        }
    ),
    "employee": frozenset(
        {
            "Dashboard",
            "Work & Plan (Supervisor)",
            "Time Tracking",
            "Asset Database",
            "Scan Inventory",
            "Who Has What",
            "Tool Trailer Audits",
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
    if pending == "Planning & Goals":
        pending = "Work & Plan (Supervisor)"
    if pending == "Daily Tasks":
        pending = "Work & Plan (Supervisor)"
    if pending in ("Supervisor Daily Reports", "Daily crew report"):
        pending = "Work & Plan (Supervisor)"
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
/* --- Sidebar: slightly darker than main (#d1d5db), high-contrast ink --- */
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] > div,
[data-testid="stSidebar"] {
  background-color: #cbd5e1 !important;
  background: #cbd5e1 !important;
  color: #111827 !important;
}
section[data-testid="stSidebar"] .block-container {
  background: transparent !important;
}
section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown li,
section[data-testid="stSidebar"] .stMarkdown h1,
section[data-testid="stSidebar"] .stMarkdown h2,
section[data-testid="stSidebar"] .stMarkdown h3,
section[data-testid="stSidebar"] .stMarkdown h4,
section[data-testid="stSidebar"] .stMarkdown h5,
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p,
section[data-testid="stSidebar"] [data-testid="stCaption"] {
  color: #111827 !important;
  font-weight: 500 !important;
}
section[data-testid="stSidebar"] .stMarkdown h1,
section[data-testid="stSidebar"] .stMarkdown h2,
section[data-testid="stSidebar"] .stMarkdown h3 {
  font-weight: 700 !important;
}
section[data-testid="stSidebar"] .stMarkdown h4,
section[data-testid="stSidebar"] .stMarkdown h5 {
  font-weight: 600 !important;
}
section[data-testid="stSidebar"] .stLinkButton > a {
  color: #111827 !important;
  font-weight: 600 !important;
}
/* Section labels: subtle hierarchy, still high contrast */
section[data-testid="stSidebar"] .ips-nav-section-title {
  color: #111827 !important;
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
  border-top: 1px solid #94a3b8 !important;
}
section[data-testid="stSidebar"] .ips-nav-primary-secondary-divider {
  margin: 28px 0 14px 0;
  padding: 0;
  border: none;
  border-top: 1px solid #94a3b8 !important;
  box-shadow: none !important;
  opacity: 1;
}
/* Sidebar buttons: light chrome, slate text */
section[data-testid="stSidebar"] div.stButton > button,
section[data-testid="stSidebar"] div.stButton > button[kind="secondary"],
section[data-testid="stSidebar"] div.stButton > button[data-testid="baseButton-secondary"] {
  font-size: 0.875rem !important;
  font-weight: 600 !important;
  min-height: 3rem !important;
  padding: 0.45rem 0.75rem !important;
  border-radius: 10px !important;
  line-height: 1.25 !important;
  box-sizing: border-box !important;
  background: #e5e7eb !important;
  border: 1px solid #9ca3af !important;
  color: #111827 !important;
  box-shadow: none !important;
}
section[data-testid="stSidebar"] div.stButton > button:hover:not(:disabled),
section[data-testid="stSidebar"] div.stButton > button[kind="secondary"]:hover:not(:disabled),
section[data-testid="stSidebar"] div.stButton > button[data-testid="baseButton-secondary"]:hover:not(:disabled) {
  background: #d1d5db !important;
  border-color: #6b7280 !important;
  color: #111827 !important;
}
section[data-testid="stSidebar"] div.stButton > button p {
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  margin: 0 !important;
  color: #111827 !important;
  font-weight: 600 !important;
}
section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] div.stButton > button {
  font-size: 0.8125rem !important;
  font-weight: 600 !important;
  min-height: 3rem !important;
  padding: 0.45rem 0.65rem !important;
  border-radius: 10px !important;
  box-sizing: border-box !important;
  background: #e5e7eb !important;
  border: 1px solid #9ca3af !important;
  color: #111827 !important;
}
section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] div.stButton > button:hover:not(:disabled) {
  background: #d1d5db !important;
  border-color: #6b7280 !important;
  color: #111827 !important;
}
/* Active page: white card on grey rail */
section[data-testid="stSidebar"] button[kind="primary"],
section[data-testid="stSidebar"] button[data-testid="baseButton-primary"] {
  background: #ffffff !important;
  border: 1px solid #9ca3af !important;
  color: #111827 !important;
  box-shadow: none !important;
  font-weight: 700 !important;
}
section[data-testid="stSidebar"] button[kind="primary"]:hover:not(:disabled),
section[data-testid="stSidebar"] button[data-testid="baseButton-primary"]:hover:not(:disabled) {
  background: #f3f4f6 !important;
  border-color: #6b7280 !important;
  color: #111827 !important;
}
section[data-testid="stSidebar"] button[kind="primary"] p,
section[data-testid="stSidebar"] button[data-testid="baseButton-primary"] p {
  color: #111827 !important;
  font-weight: 700 !important;
}
/* TOOLS expander */
section[data-testid="stSidebar"] [data-testid="stExpander"] details {
  border: 1px solid #cbd5e1 !important;
  border-radius: 8px !important;
  background: #e5e7eb !important;
  margin-top: 2px !important;
}
section[data-testid="stSidebar"] [data-testid="stExpander"] summary {
  font-size: 0.65rem !important;
  font-weight: 700 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.1em !important;
  color: #111827 !important;
  opacity: 1 !important;
  padding: 8px 10px !important;
}
section[data-testid="stSidebar"] [data-testid="stExpander"] svg,
section[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stExpanderToggleIcon"] {
  color: #374151 !important;
  fill: #374151 !important;
}
section[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stExpanderDetails"] {
  padding: 2px 8px 12px 8px !important;
  background: transparent !important;
}
section[data-testid="stSidebar"] [data-testid="stExpander"] div.stButton > button[kind="secondary"],
section[data-testid="stSidebar"] [data-testid="stExpander"] div.stButton > button[data-testid="baseButton-secondary"] {
  font-size: 0.8125rem !important;
  font-weight: 600 !important;
  min-height: 3rem !important;
  padding: 0.4rem 0.6rem !important;
  border-radius: 10px !important;
  background: #e5e7eb !important;
  border: 1px solid #9ca3af !important;
  color: #111827 !important;
  box-shadow: none !important;
  opacity: 1 !important;
}
section[data-testid="stSidebar"] [data-testid="stExpander"] div.stButton > button[kind="secondary"]:hover:not(:disabled) {
  background: #d1d5db !important;
  border-color: #6b7280 !important;
  color: #111827 !important;
}
section[data-testid="stSidebar"] [data-testid="stExpander"] div.stButton > button[kind="primary"],
section[data-testid="stSidebar"] [data-testid="stExpander"] div.stButton > button[data-testid="baseButton-primary"] {
  font-size: 0.875rem !important;
  font-weight: 700 !important;
  min-height: 3rem !important;
  padding: 0.4rem 0.75rem !important;
  border-radius: 10px !important;
  background: #ffffff !important;
  border: 1px solid #9ca3af !important;
  color: #111827 !important;
  box-shadow: none !important;
}
section[data-testid="stSidebar"] [data-testid="stExpander"] div.stButton > button[kind="primary"]:hover:not(:disabled) {
  background: #f3f4f6 !important;
  border-color: #6b7280 !important;
  color: #111827 !important;
}
section[data-testid="stSidebar"] .ips-nav-signout-spacer {
  height: 12px;
}
section[data-testid="stSidebar"] .ips-install-section-title {
  color: #111827 !important;
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
    if cur0 == "Employees":
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
    elif cur0 == "Daily Tasks":
        st.session_state[IPS_NAV_PAGE_KEY] = "Work & Plan (Supervisor)"
    elif cur0 in ("Supervisor Daily Reports", "Daily crew report"):
        st.session_state[IPS_NAV_PAGE_KEY] = "Work & Plan (Supervisor)"

    role = current_role()
    visible_secondary = set(_visible_secondary_pages(role))
    visible_all = set(
        p
        for p in (
            set(_NAV_PRIMARY)
            | set(_NAV_JOBS_ROUTES)
            | set(_NAV_ASSET_ROUTES)
            | set(_NAV_RESOURCES)
            | set(_NAV_INVENTORY_SUBPAGES)
            | set(_NAV_ADMIN_SIDEBAR)
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


def _set_sidebar_page(page: str) -> None:
    st.session_state[IPS_NAV_PAGE_KEY] = page
    st.session_state.pop(IPS_ACTIVE_PAGE_KEY, None)
    st.rerun()


def _sidebar_sign_out() -> None:
    sign_out()
    st.session_state.pop(IPS_ACTIVE_PAGE_KEY, None)
    st.session_state.pop(IPS_NAV_PAGE_KEY, None)
    st.rerun()


def _render_nav_button(page: str, *, current: str, indent: bool) -> None:
    active = current == page
    btn_type = "primary" if active else "secondary"
    key = _nav_btn_key(page)
    if indent:
        _, c2 = st.sidebar.columns([0.06, 0.94])
        with c2:
            if st.button(page, key=key, type=btn_type, use_container_width=True):
                _set_sidebar_page(page)
    else:
        if st.sidebar.button(page, key=key, type=btn_type, use_container_width=True):
            _set_sidebar_page(page)


def _render_nav_button_route(*, label: str, route: str, current: str, indent: bool, key_suffix: str) -> None:
    """Render a nav button whose label differs from its route key."""
    active = current == route
    btn_type = "primary" if active else "secondary"
    key = _nav_btn_key(route + "__" + key_suffix)
    if indent:
        _, c2 = st.sidebar.columns([0.06, 0.94])
        with c2:
            if st.button(label, key=key, type=btn_type, use_container_width=True):
                _set_sidebar_page(route)
    else:
        if st.sidebar.button(label, key=key, type=btn_type, use_container_width=True):
            _set_sidebar_page(route)


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
                st.session_state["asset_db_f_asset_category"] = "All" if cat_norm == "All" else cat_norm
                _set_sidebar_page("Asset Database")


def _sidebar_nav_title(extra_class: str, text: str) -> None:
    cls = "ips-nav-section-title" + (f" {extra_class}" if extra_class else "")
    st.sidebar.markdown(
        f'<div class="{cls.strip()}">{text}</div>',
        unsafe_allow_html=True,
    )


def _render_sidebar_office(*, current: str, role: str) -> None:
    """PM / admin / manager — jobs, packages, inventory, assets, office tools."""
    _sidebar_nav_title("", "Dashboard")
    _render_nav_button("Dashboard", current=current, indent=False)

    _sidebar_nav_title("ips-nav-group-spaced", "Jobs")
    st.sidebar.caption("Job records, estimates, and costing.")
    for p in _NAV_JOBS_SIDEBAR:
        if not role_can_open_page(role, p):
            continue
        if p == "Assign Tasks (PM)":
            _render_nav_button_route(
                label="Assign work (PM)",
                route="Assign Tasks (PM)",
                current=current,
                indent=True,
                key_suffix="pm",
            )
        elif p == "Work & Plan (Supervisor)":
            _render_nav_button_route(
                label="Work & plan (supervisor)",
                route="Work & Plan (Supervisor)",
                current=current,
                indent=True,
                key_suffix="sup",
            )
        else:
            _render_nav_button(p, current=current, indent=True)
    st.sidebar.caption(
        "**Assign work (PM)** — PM lines up today’s work packages. "
        "**Work & plan** — supervisor plans the shift, updates tasks and photos, and submits end-of-day review."
    )

    _sidebar_nav_title("ips-nav-group-spaced", "Assets")
    if role_can_open_page(role, "Asset Database"):
        _render_assets_sidebar_group(current=current, role=role)
    if role_can_open_page(role, "Who Has What"):
        _render_nav_button("Who Has What", current=current, indent=True)
    if role_can_open_page(role, "Tool Trailer Audits"):
        _render_nav_button("Tool Trailer Audits", current=current, indent=True)

    _sidebar_nav_title("ips-nav-group-spaced", "Inventory")
    inv_expanded = current in ("Inventory", *_NAV_INVENTORY_SUBPAGES)
    if role_can_open_page(role, "Inventory") or any(role_can_open_page(role, p) for p in _NAV_INVENTORY_SUBPAGES):
        with st.sidebar.expander("Inventory", expanded=inv_expanded):
            _, inv_inner = st.columns([0.06, 0.94])
            with inv_inner:
                _inv_focus = _sidebar_inventory_category_focus_norm()
                inv_list_active = current == "Inventory" and _inv_focus == "All"
                if role_can_open_page(role, "Inventory"):
                    if st.button(
                        "Inventory list",
                        key=_nav_btn_key("Inventory__list_all"),
                        type="primary" if inv_list_active else "secondary",
                        use_container_width=True,
                    ):
                        st.session_state["inv_f_cat"] = "All"
                        _set_sidebar_page("Inventory")
                if role_can_open_page(role, "Scan Inventory"):
                    if st.button(
                        "Scan inventory",
                        key=_nav_btn_key("Scan Inventory"),
                        type="primary" if current == "Scan Inventory" else "secondary",
                        use_container_width=True,
                    ):
                        _set_sidebar_page("Scan Inventory")
                if role_can_open_page(role, "Inventory Usage"):
                    if st.button(
                        "Inventory usage",
                        key=_nav_btn_key("Inventory Usage"),
                        type="primary" if current == "Inventory Usage" else "secondary",
                        use_container_width=True,
                    ):
                        _set_sidebar_page("Inventory Usage")

    _sidebar_nav_title("ips-nav-group-spaced", "Office & reports")
    for p in _NAV_ADMIN_SIDEBAR:
        if role_can_open_page(role, p):
            _render_nav_button(p, current=current, indent=True)
    if role == "admin" and role_can_open_page(role, "Admin"):
        _render_nav_button("Admin", current=current, indent=True)


def _render_sidebar_field(*, current: str, role: str) -> None:
    """Field supervisor / crew — one primary workflow plus scan and tools."""
    _sidebar_nav_title("", "Dashboard")
    _render_nav_button("Dashboard", current=current, indent=False)

    _sidebar_nav_title("ips-nav-group-spaced", "Today’s work")
    st.sidebar.caption("Plan the shift, tasks, photos, and end-of-day review — one screen.")
    if role_can_open_page(role, "Work & Plan (Supervisor)"):
        _render_nav_button_route(
            label="Work & plan (supervisor)",
            route="Work & Plan (Supervisor)",
            current=current,
            indent=True,
            key_suffix="sup",
        )

    _sidebar_nav_title("ips-nav-group-spaced", "Inventory")
    if role_can_open_page(role, "Scan Inventory"):
        _render_nav_button_route(
            label="Scan inventory",
            route="Scan Inventory",
            current=current,
            indent=True,
            key_suffix="scan",
        )

    _sidebar_nav_title("ips-nav-group-spaced", "Tools & assets")
    if role_can_open_page(role, "Who Has What"):
        _render_nav_button("Who Has What", current=current, indent=True)
    if role_can_open_page(role, "Asset Database"):
        _render_nav_button_route(
            label="Asset list",
            route="Asset Database",
            current=current,
            indent=True,
            key_suffix="ad",
        )
    if role_can_open_page(role, "Employee Toolbox"):
        _render_nav_button_route(
            label="My tools",
            route="Employee Toolbox",
            current=current,
            indent=True,
            key_suffix="tb",
        )
    if role_can_open_page(role, "Tool Trailer Audits"):
        _render_nav_button("Tool Trailer Audits", current=current, indent=True)
    if role_can_open_page(role, "Time Tracking"):
        _render_nav_button("Time Tracking", current=current, indent=True)


def _render_sidebar_viewer(*, current: str, role: str) -> None:
    _sidebar_nav_title("", "Dashboard")
    _render_nav_button("Dashboard", current=current, indent=False)
    for p in ("Asset Database", "Who Has What", "Inventory Usage"):
        if role_can_open_page(role, p):
            _render_nav_button(p, current=current, indent=True)


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
    r = str(role or "viewer").strip().lower()
    if r in ("pm", "estimator"):
        r = "manager"
    if r in ("admin", "manager"):
        _render_sidebar_office(current=current, role=role)
    elif r == "employee":
        _render_sidebar_field(current=current, role=role)
    else:
        _render_sidebar_viewer(current=current, role=role)

    st.sidebar.markdown('<div class="ips-nav-signout-spacer"></div>', unsafe_allow_html=True)
    if st.sidebar.button("Sign Out", use_container_width=True):
        _sidebar_sign_out()
    return current
