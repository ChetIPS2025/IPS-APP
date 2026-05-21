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


def begin_module(slug: str, *, inject_css: bool = True) -> bool:
    """
    Per-page gate: foundation CSS + role check.

    Returns False when the user must not see page content.
    """
    if inject_css:
        inject_global_css()
    role = current_role()
    if not role_can_access_page(role, slug):
        st.error("You do not have access to this page.")
        return False
    st.markdown(
        f'<div class="ips-page-content ips-page-{slug}"></div>',
        unsafe_allow_html=True,
    )
    show_demo_banner_if_needed()
    return True


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
