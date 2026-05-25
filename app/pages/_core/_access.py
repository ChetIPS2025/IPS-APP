"""Access control and data-source hints for Phase 2 module pages."""

from __future__ import annotations

import streamlit as st

try:
    from app.auth import current_role
    from app.styles import inject_global_css
    from app.utils.permissions import role_can_access_page
except ImportError:
    from auth import current_role  # type: ignore
    from styles import inject_global_css  # type: ignore
    from utils.permissions import role_can_access_page  # type: ignore

_DEMO_FLAG = "ips_showing_demo_data"
_MODULE_SHELL_KEY = "_ips_module_page_shell_open"


def begin_module(slug: str, *, inject_css: bool = False) -> bool:
    """
    Per-page gate: foundation CSS + role check.

    Emits ``.ips-page-content`` / ``.ips-page-{slug}`` markers for main-area CSS
    (``:has(.ips-page-content)`` in global styles). ``end_module`` clears session state
    after the page body (``phase2.render_module`` does this automatically).

    Returns False when the user must not see page content.
    """
    if inject_css:
        inject_global_css()
    role = current_role()
    if not role_can_access_page(role, slug):
        st.error("You do not have access to this page.")
        return False
    end_module()
    # Marker span (Streamlit widgets are not DOM children of a following open <div>).
    # Layout/CSS scope uses section[data-testid="stMain"]:has(.ips-page-content) in global CSS.
    st.markdown(
        f'<span class="ips-page-content ips-page-shell-marker ips-page-{slug}" '
        f'aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    st.session_state[_MODULE_SHELL_KEY] = slug
    show_demo_banner_if_needed()
    return True


def end_module() -> None:
    """Clear module shell session state after :func:`begin_module` (called from ``render_module``)."""
    st.session_state.pop(_MODULE_SHELL_KEY, None)


def mark_demo_data(active: bool = True) -> None:
    if active:
        st.session_state[_DEMO_FLAG] = True


def clear_demo_flag() -> None:
    st.session_state.pop(_DEMO_FLAG, None)


def show_demo_banner_if_needed() -> None:
    if st.session_state.get(_DEMO_FLAG):
        st.caption(
            "Showing sample data — Supabase table missing, empty, or unreachable. "
            "Apply migrations in `sql/` (including `062_phase3_operations_hub.sql`) to use live data."
        )


def show_db_error(table: str, err: str | None) -> None:
    if not err:
        return
    low = err.lower()
    if "404" in err or "does not exist" in low or "relation" in low and "not exist" in low:
        st.warning(
            f"The `{table}` table is not available in Supabase yet. "
            f"Run the SQL migrations (see `sql/062_phase3_operations_hub.sql`). Showing sample data until then."
        )
    elif "column" in low:
        st.warning(
            f"A column may be missing on `{table}`. Check `SUPABASE_SCHEMA_NOTES.md` and apply pending migrations."
        )
