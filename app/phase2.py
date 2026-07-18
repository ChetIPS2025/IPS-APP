"""Module registry for the unified IPS operations platform."""

from __future__ import annotations

import importlib
import logging
from collections.abc import Callable, Iterator, Mapping
from typing import Any

import streamlit as st

from app.auth import effective_role
from app.pages._core._session import clear_all_module_selections, nav_slug
from app.utils.constants import SESSION_NAV_KEY
from app.utils.permissions import role_can_access_page

# slug -> (import path, render attribute). Loaded on first navigation to each slug.
_MODULE_SPECS: dict[str, tuple[str, str]] = {
    "dashboard": ("app.pages.dashboard", "render"),
    "jobs": ("app.pages.jobs", "render"),
    "pipeline": ("app.pages.pipeline", "render"),
    "customers": ("app.pages.customers", "render"),
    "estimates": ("app.pages.estimates", "render"),
    "pricing_guide": ("app.pages.pricing_guide", "render"),
    "estimate_materials": ("app.pages.estimate_materials", "render"),
    "inventory": ("app.pages.inventory", "render"),
    "assets": ("app.pages.assets", "render"),
    "timekeeping": ("app.pages.timekeeping", "render"),
    "weekly_timesheets": ("app.pages.weekly_timesheets", "render"),
    "employees": ("app.pages.employees", "render"),
    "users": ("app.pages.employees", "render"),
    "employee_certifications": ("app.pages.employee_certifications", "render"),
    "employee_documents": ("app.pages.employee_documents", "render"),
    "employee_portal": ("app.pages.employee_portal", "render"),
    "employee_profile": ("app.pages.employee_profile", "render"),
    "employee_qr_scan": ("app.pages.employee_qr_scan", "render"),
    "employee_resources": ("app.pages.employee_resources", "render"),
    "company_updates": ("app.pages.company_updates", "render"),
    "documents": ("app.pages.documents", "render"),
    "tasks": ("app.pages.tasks", "render"),
    "reports": ("app.pages.reports", "render"),
    "admin": ("app.pages.admin", "render"),
    "settings": ("app.pages.settings", "render"),
    "field_dashboard": ("app.pages.field_dashboard", "render"),
    "field_day": ("app.pages.field_day", "render"),
    "field_daily_reports": ("app.pages.field_daily_reports", "render"),
    "field_crew_time": ("app.pages.field_crew_time", "render"),
    "coupling_inspection": ("app.pages.coupling_inspection", "render"),
    "rental_equipment": ("app.pages.rental_equipment", "render"),
    "rental_equipment_inspection": ("app.pages.rental_equipment_inspection", "render"),
}

_render_cache: dict[str, Callable[..., Any]] = {}


def _resolve_module_render(slug: str) -> Callable[..., Any] | None:
    """Import and cache one page module's ``render`` function."""
    key = str(slug or "").strip()
    if not key:
        return None
    if key in _render_cache:
        return _render_cache[key]
    spec = _MODULE_SPECS.get(key)
    if not spec:
        return None
    module_path, attr = spec
    module = importlib.import_module(module_path)
    fn = getattr(module, attr)
    _render_cache[key] = fn
    return fn


class _LazyBuiltModules(Mapping[str, Callable[..., Any]]):
    """Backward-compatible ``BUILT_MODULES`` mapping without eager page imports."""

    def __getitem__(self, slug: str) -> Callable[..., Any]:
        fn = _resolve_module_render(slug)
        if fn is None:
            raise KeyError(slug)
        return fn

    def get(self, slug: str, default: Any = None) -> Callable[..., Any] | Any:
        fn = _resolve_module_render(slug)
        return fn if fn is not None else default

    def __contains__(self, slug: object) -> bool:
        return str(slug or "").strip() in _MODULE_SPECS

    def __iter__(self) -> Iterator[str]:
        return iter(_MODULE_SPECS)

    def __len__(self) -> int:
        return len(_MODULE_SPECS)

    def keys(self) -> set[str]:
        return set(_MODULE_SPECS)

    def items(self) -> list[tuple[str, Callable[..., Any]]]:
        return [(slug, self[slug]) for slug in _MODULE_SPECS]


BUILT_MODULES: _LazyBuiltModules = _LazyBuiltModules()


def ensure_nav_defaults() -> None:
    from app.utils.permissions import role_default_nav_slug

    default = role_default_nav_slug(
        effective_role(),
        field_mode=bool(st.session_state.get("ips_field_mode")),
    )
    st.session_state.setdefault(SESSION_NAV_KEY, default)


def on_nav_change(prev_slug: str, new_slug: str) -> None:
    if prev_slug != new_slug:
        clear_all_module_selections()


def render_module(slug: str | None = None) -> None:
    from app.navigation import normalize_nav_slug

    active = normalize_nav_slug(slug or nav_slug() or "dashboard")
    role = effective_role()
    if not role_can_access_page(role, active):
        from app.navigation import default_nav_slug, set_nav_slug

        fallback = default_nav_slug()
        if active != fallback and role_can_access_page(role, fallback):
            set_nav_slug(fallback)
            st.rerun()
            return
        st.error("You do not have access to this page.")
        return

    from app.pages._core._access import clear_demo_flag, end_module, show_demo_banner_if_needed

    clear_demo_flag()
    fn = _resolve_module_render(active)
    if fn:
        try:
            from app.perf_debug import perf_span
            from app.auth import current_role
            from app.utils.permissions import normalize_role
            from app.utils.view_as import is_view_as_active, render_view_as_page_shell

            def _render_module() -> None:
                with perf_span(f"module.render:{active}"):
                    fn()

            if normalize_role(current_role()) == "admin" and is_view_as_active():
                render_view_as_page_shell(_render_module)
            else:
                _render_module()
        except Exception as exc:
            st.error(f"This page encountered an error: {exc}")
            logging.getLogger(__name__).exception("module %s failed", active)
        finally:
            end_module()
        show_demo_banner_if_needed()
        return

    st.markdown('<p class="ips-module-placeholder">Module not found.</p>', unsafe_allow_html=True)
