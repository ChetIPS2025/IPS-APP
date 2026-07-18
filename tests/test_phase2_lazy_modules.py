"""Lazy module registry for phase2 routing."""

from __future__ import annotations

import importlib
import sys

import pytest


@pytest.fixture(autouse=True)
def _clear_render_cache() -> None:
    from app import phase2

    phase2._render_cache.clear()
    yield
    phase2._render_cache.clear()


def test_importing_phase2_does_not_load_page_modules() -> None:
    import app.phase2 as phase2

    snapshot = dict(sys.modules)
    removed: list[str] = []
    for name in list(sys.modules):
        if name.startswith("app.pages.") and not name.startswith("app.pages._core."):
            removed.append(name)
            del sys.modules[name]

    try:
        importlib.reload(phase2)
        loaded_pages = [
            name
            for name in sys.modules
            if name.startswith("app.pages.")
            and not name.startswith("app.pages._core.")
            and name not in {"app.pages", "app.pages._import_render"}
        ]
        assert loaded_pages == []
    finally:
        for name in removed:
            sys.modules.pop(name, None)
        for name, module in snapshot.items():
            if name.startswith("app.pages.") and name not in sys.modules:
                sys.modules[name] = module
        phase2._render_cache.clear()


def test_lazy_registry_resolves_single_slug() -> None:
    from app.phase2 import BUILT_MODULES, _MODULE_SPECS

    assert "jobs" in BUILT_MODULES
    assert len(_MODULE_SPECS) == len(BUILT_MODULES)

    fn = BUILT_MODULES.get("dashboard")
    assert callable(fn)
    assert "app.pages.dashboard" in sys.modules

    jobs_fn = BUILT_MODULES.get("jobs")
    assert callable(jobs_fn)
    assert jobs_fn is not fn
    assert "app.pages.jobs" in sys.modules


def test_users_slug_aliases_employees_module() -> None:
    from app.phase2 import BUILT_MODULES

    users_fn = BUILT_MODULES.get("users")
    employees_fn = BUILT_MODULES.get("employees")
    assert users_fn is employees_fn
