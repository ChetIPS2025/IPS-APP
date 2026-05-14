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
# URL-style route slug (mirrors Office & reports sidebar); kept in sync with ``IPS_NAV_PAGE_KEY`` for those pages.
IPS_ROUTE_SLUG_KEY = "page"

# Slugs for Office & reports + Admin (``main`` may read ``IPS_ROUTE_SLUG_KEY`` before rendering).
_ROUTE_SLUG_BY_PAGE: dict[str, str] = {
    "Users": "users",
    "Time Tracking": "time_tracking",
    "Weekly Timesheet": "weekly_timesheet",
    "PO / Expenses": "po_expenses",
    "Admin": "admin",
}
_PAGE_BY_ROUTE_SLUG: dict[str, str] = {v: k for k, v in _ROUTE_SLUG_BY_PAGE.items()}

# ---- Sidebar structure (simple, field + office friendly) ----
# Keep routes separate from sidebar visibility so deep links / pending-nav still work.
_NAV_PRIMARY: tuple[str, ...] = ("Dashboard",)

# Jobs (routable; sidebar layout is built in ``_render_sidebar_office``).
_NAV_ASSETS_EXPANDER_PAGES: tuple[str, ...] = ("Asset Database", "Who Has What", "Tool Trailer Audits")

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
# Routable asset-area pages (sidebar: nested under **Assets** expander when shown).
_NAV_ASSET_ROUTES: tuple[str, ...] = ("Asset Database", "Who Has What", "Tool Trailer Audits")
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


def _set_sidebar_nav_page(page: str) -> None:
    """Update primary nav and optional route slug (``IPS_ROUTE_SLUG_KEY``)."""
    p = str(page or "").strip()
    if not p:
        return
    st.session_state[IPS_NAV_PAGE_KEY] = p
    slug = _ROUTE_SLUG_BY_PAGE.get(p)
    if slug:
        st.session_state[IPS_ROUTE_SLUG_KEY] = slug
    else:
        st.session_state.pop(IPS_ROUTE_SLUG_KEY, None)


def sync_session_route_slug_to_nav_page() -> None:
    """If ``page`` holds a known slug, align ``ips_nav_page`` (runs before ``render_sidebar``)."""
    raw = st.session_state.get(IPS_ROUTE_SLUG_KEY)
    if not isinstance(raw, str) or not raw.strip():
        return
    target = _PAGE_BY_ROUTE_SLUG.get(raw.strip())
    if target is None:
        return
    st.session_state[IPS_NAV_PAGE_KEY] = target


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
    st.session_state.pop(IPS_ROUTE_SLUG_KEY, None)
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
        st.sidebar.image(str(logo_path), width=64)

    st.sidebar.markdown("**IPS** Estimating")


def _inject_sidebar_nav_css() -> None:
    st.sidebar.markdown(
        """
<style>
/* --- Sidebar: slightly darker than main (#d1d5db), high-contrast ink --- */
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] > div,
[data-testid="stSidebar"] {
  background-color: #b8c2ce !important;
  background: #b8c2ce !important;
  color: #0f172a !important;
  max-width: 15.5rem !important;
  min-width: 14rem !important;
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
  margin-top: 8px !important;
  padding-top: 8px !important;
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
  min-height: 2.5rem !important;
  padding: 0.4rem 0.65rem !important;
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
  min-height: 2.5rem !important;
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
/* Active page: blue highlight */
section[data-testid="stSidebar"] button[kind="primary"],
section[data-testid="stSidebar"] button[data-testid="baseButton-primary"] {
  background: #2563eb !important;
  border: 1px solid #2563eb !important;
  color: #ffffff !important;
  box-shadow: none !important;
  font-weight: 700 !important;
}
section[data-testid="stSidebar"] button[kind="primary"]:hover:not(:disabled),
section[data-testid="stSidebar"] button[data-testid="baseButton-primary"]:hover:not(:disabled) {
  background: #1d4ed8 !important;
  border-color: #1d4ed8 !important;
  color: #ffffff !important;
}
section[data-testid="stSidebar"] button[kind="primary"] p,
section[data-testid="stSidebar"] button[data-testid="baseButton-primary"] p {
  color: #ffffff !important;
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
  min-height: 2.5rem !important;
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
  min-height: 2.5rem !important;
  padding: 0.4rem 0.75rem !important;
  border-radius: 10px !important;
  background: #2563eb !important;
  border: 1px solid #2563eb !important;
  color: #ffffff !important;
  box-shadow: none !important;
}
section[data-testid="stSidebar"] [data-testid="stExpander"] div.stButton > button[kind="primary"]:hover:not(:disabled),
section[data-testid="stSidebar"] [data-testid="stExpander"] div.stButton > button[data-testid="baseButton-primary"]:hover:not(:disabled) {
  background: #1d4ed8 !important;
  border-color: #1d4ed8 !important;
  color: #ffffff !important;
}
section[data-testid="stSidebar"] [data-testid="stExpander"] div.stButton > button[kind="primary"] p,
section[data-testid="stSidebar"] [data-testid="stExpander"] div.stButton > button[data-testid="baseButton-primary"] p {
  color: #ffffff !important;
  font-weight: 700 !important;
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

    if st.session_state.get(IPS_NAV_PAGE_KEY) != cur0:
        st.session_state.pop(IPS_ROUTE_SLUG_KEY, None)

    role = current_role()
    cur = st.session_state.get(IPS_NAV_PAGE_KEY)
    routable = frozenset(IPS_SIDEBAR_PAGES) | {"Admin"}
    if cur not in routable:
        st.session_state[IPS_NAV_PAGE_KEY] = IPS_SIDEBAR_PAGES[0]
        st.session_state.pop(IPS_ROUTE_SLUG_KEY, None)
        return

    if not role_can_open_page(role, str(cur or "")):
        st.session_state[IPS_NAV_PAGE_KEY] = "Dashboard"
        st.session_state.pop(IPS_ROUTE_SLUG_KEY, None)


def _render_nav_button(page: str, *, indent: bool) -> None:
    current = str(st.session_state.get(IPS_NAV_PAGE_KEY) or "")
    active = current == page
    btn_type = "primary" if active else "secondary"
    key = _nav_btn_key(page)
    if indent:
        _, c2 = st.sidebar.columns([0.06, 0.94])
        with c2:
            if st.button(page, key=key, type=btn_type, use_container_width=True):
                _set_sidebar_nav_page(page)
    else:
        if st.sidebar.button(page, key=key, type=btn_type, use_container_width=True):
            _set_sidebar_nav_page(page)


def _render_nav_button_route(*, label: str, route: str, indent: bool, key_suffix: str) -> None:
    current = str(st.session_state.get(IPS_NAV_PAGE_KEY) or "")
    active = current == route
    btn_type = "primary" if active else "secondary"
    key = _nav_btn_key(route + "__" + key_suffix)
    if indent:
        _, c2 = st.sidebar.columns([0.06, 0.94])
        with c2:
            if st.button(label, key=key, type=btn_type, use_container_width=True):
                _set_sidebar_nav_page(route)
    else:
        if st.sidebar.button(label, key=key, type=btn_type, use_container_width=True):
            _set_sidebar_nav_page(route)


def _sidebar_inventory_category_focus_norm() -> str:
    v = str(st.session_state.get("inv_f_cat") or "All").strip()
    if not v or v.lower() == "all":
        return "All"
    return v


def _visible_assets_expander_pages(role: str) -> tuple[str, ...]:
    return tuple(p for p in _NAV_ASSETS_EXPANDER_PAGES if role_can_open_page(role, p))


def _render_assets_sidebar_group(*, role: str) -> None:
    """Collapsible **ASSETS** group."""
    visible = _visible_assets_expander_pages(role)
    if not visible:
        return
    cur = str(st.session_state.get(IPS_NAV_PAGE_KEY) or "")
    expanded = cur in visible
    with st.sidebar.expander("ASSETS", expanded=expanded, key="ips_sidebar_assets_group"):
        _, inner = st.columns([0.08, 0.92])
        with inner:
            for page in visible:
                cur = str(st.session_state.get(IPS_NAV_PAGE_KEY) or "")
                active = cur == page
                btn_type = "primary" if active else "secondary"
                if page == "Asset Database":
                    key = _nav_btn_key("Asset_Database__sidebar_assets")
                    if st.button("Assets", key=key, type=btn_type, use_container_width=True):
                        _set_sidebar_nav_page("Asset Database")
                        st.session_state["asset_db_f_asset_category"] = "All"
                else:
                    key = _nav_btn_key(page)
                    if st.button(page, key=key, type=btn_type, use_container_width=True):
                        _set_sidebar_nav_page(page)


def _sidebar_nav_title(extra_class: str, text: str) -> None:
    cls = "ips-nav-section-title" + (f" {extra_class}" if extra_class else "")
    st.sidebar.markdown(
        f'<div class="{cls.strip()}">{text}</div>',
        unsafe_allow_html=True,
    )


def _render_sidebar_office(*, role: str) -> None:
    _sidebar_nav_title("", "HOME")
    _render_nav_button("Dashboard", indent=False)

    _sidebar_nav_title("ips-nav-group-spaced", "JOBS")
    for p in ("Job Database", "Job Costing"):
        if role_can_open_page(role, p):
            _render_nav_button(p, indent=True)

    _sidebar_nav_title("ips-nav-group-spaced", "ESTIMATES")
    if role_can_open_page(role, "Estimates"):
        _render_nav_button("Estimates", indent=True)

    _sidebar_nav_title("ips-nav-group-spaced", "WORK / PLANNING")
    if role_can_open_page(role, "Assign Tasks (PM)"):
        _render_nav_button_route(
            label="Assign tasks (PM)",
            route="Assign Tasks (PM)",
            indent=True,
            key_suffix="pm",
        )
    if role_can_open_page(role, "Work & Plan (Supervisor)"):
        _render_nav_button_route(
            label="Work & plan (field)",
            route="Work & Plan (Supervisor)",
            indent=True,
            key_suffix="sup",
        )

    _render_assets_sidebar_group(role=role)

    nav_page = str(st.session_state.get(IPS_NAV_PAGE_KEY) or "")
    inv_expanded = nav_page in ("Inventory", *_NAV_INVENTORY_SUBPAGES)
    if role_can_open_page(role, "Inventory") or any(role_can_open_page(role, p) for p in _NAV_INVENTORY_SUBPAGES):
        with st.sidebar.expander("INVENTORY", expanded=inv_expanded):
            _, inv_inner = st.columns([0.06, 0.94])
            with inv_inner:
                if role_can_open_page(role, "Inventory"):
                    if st.button(
                        "Estimate materials",
                        key=_nav_btn_key("Inventory__est_materials"),
                        type="secondary",
                        use_container_width=True,
                    ):
                        _set_sidebar_nav_page("Inventory")
                        st.session_state["inv_f_cat"] = "Materials"
                _inv_focus = _sidebar_inventory_category_focus_norm()
                inv_list_active = nav_page == "Inventory" and _inv_focus == "All"
                if role_can_open_page(role, "Inventory"):
                    if st.button(
                        "Inventory list",
                        key=_nav_btn_key("Inventory__list_all"),
                        type="primary" if inv_list_active else "secondary",
                        use_container_width=True,
                    ):
                        _set_sidebar_nav_page("Inventory")
                        st.session_state["inv_f_cat"] = "All"
                if role_can_open_page(role, "Scan Inventory"):
                    if st.button(
                        "Scan inventory",
                        key=_nav_btn_key("Scan Inventory"),
                        type="primary" if nav_page == "Scan Inventory" else "secondary",
                        use_container_width=True,
                    ):
                        _set_sidebar_nav_page("Scan Inventory")
                if role_can_open_page(role, "Inventory Usage"):
                    if st.button(
                        "Inventory usage",
                        key=_nav_btn_key("Inventory Usage"),
                        type="primary" if nav_page == "Inventory Usage" else "secondary",
                        use_container_width=True,
                    ):
                        _set_sidebar_nav_page("Inventory Usage")

    _sidebar_nav_title("ips-nav-group-spaced", "REPORTS")
    for p in _NAV_ADMIN_SIDEBAR:
        if role_can_open_page(role, p):
            _render_nav_button(p, indent=True)
    if role == "admin" and role_can_open_page(role, "Admin"):
        _render_nav_button("Admin", indent=True)


def _render_sidebar_field(*, role: str) -> None:
    _sidebar_nav_title("", "HOME")
    _render_nav_button("Dashboard", indent=False)

    _sidebar_nav_title("ips-nav-group-spaced", "WORK / PLANNING")
    if role_can_open_page(role, "Work & Plan (Supervisor)"):
        _render_nav_button_route(
            label="Work & plan (field)",
            route="Work & Plan (Supervisor)",
            indent=True,
            key_suffix="sup",
        )

    if role_can_open_page(role, "Scan Inventory"):
        _sidebar_nav_title("ips-nav-group-spaced", "INVENTORY")
        _render_nav_button_route(
            label="Scan inventory",
            route="Scan Inventory",
            indent=True,
            key_suffix="scan",
        )

    _render_assets_sidebar_group(role=role)
    if role_can_open_page(role, "Employee Toolbox"):
        _render_nav_button_route(
            label="My tools",
            route="Employee Toolbox",
            indent=True,
            key_suffix="tb",
        )
    if role_can_open_page(role, "Time Tracking"):
        _render_nav_button("Time Tracking", indent=True)


def _render_sidebar_viewer(*, role: str) -> None:
    _sidebar_nav_title("", "HOME")
    _render_nav_button("Dashboard", indent=False)
    _render_assets_sidebar_group(role=role)
    if role_can_open_page(role, "Inventory Usage"):
        _render_nav_button("Inventory Usage", indent=True)


def render_sidebar() -> str:
    _sidebar_brand()

    profile = current_profile()
    st.sidebar.caption(f"{profile.get('email', '—')} · {profile.get('role', 'viewer')}")

    render_install_app_sidebar_block()

    _ensure_valid_nav_page()
    _inject_sidebar_nav_css()
    inject_ips_global_mobile_css()
    inject_sidebar_mobile_auto_collapse_once()

    role = current_role()
    r = str(role or "viewer").strip().lower()
    if r in ("pm", "estimator"):
        r = "manager"
    if r in ("admin", "manager"):
        _render_sidebar_office(role=role)
    elif r == "employee":
        _render_sidebar_field(role=role)
    else:
        _render_sidebar_viewer(role=role)

    st.sidebar.markdown('<div class="ips-nav-signout-spacer"></div>', unsafe_allow_html=True)
    st.sidebar.button("Sign Out", on_click=sign_out, use_container_width=True)
    return str(st.session_state.get(IPS_NAV_PAGE_KEY) or "Dashboard")
