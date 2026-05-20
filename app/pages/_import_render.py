"""Resolve module render() for page wrappers (app/ vs project-root import paths)."""

from __future__ import annotations

import importlib
from typing import Callable


def _multipage_auth_gate() -> None:
    """
    Streamlit multipage scripts under ``app/pages/*.py`` run outside ``main.py``.

    Redirect unauthenticated visitors to the home entry so login and modules never mix.
    """
    import streamlit as st

    try:
        from app.auth import bootstrap_auth_at_startup, init_session, is_authenticated
    except ImportError:
        from auth import bootstrap_auth_at_startup, init_session, is_authenticated  # type: ignore

    init_session()
    bootstrap_auth_at_startup()
    if is_authenticated():
        return
    try:
        st.switch_page("main.py")
    except Exception:
        pass
    st.warning("Please sign in to continue.")
    st.stop()


def _load_render_impl(module_name: str) -> Callable[[], None]:
    for path in (f"app.pages.modules.{module_name}", f"pages.modules.{module_name}"):
        try:
            mod = importlib.import_module(path)
            fn = getattr(mod, "render", None)
            if callable(fn):
                return fn
        except ImportError:
            continue
    raise ImportError(f"Cannot import render() for pages.modules.{module_name}")


def load_render(module_name: str) -> Callable[[], None]:
    inner = _load_render_impl(module_name)

    def guarded_render() -> None:
        import streamlit as st

        _multipage_auth_gate()
        inner()

    return guarded_render
