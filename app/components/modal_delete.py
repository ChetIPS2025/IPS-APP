"""Reusable delete / deactivate action panels for record detail modals."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager

import streamlit as st

try:
    from app.components.action_styles import danger_outline_button, danger_solid_button
except ImportError:
    from components.action_styles import danger_outline_button, danger_solid_button  # type: ignore


def can_admin_mutate() -> bool:
    try:
        from app.auth import current_role
    except ImportError:
        from auth import current_role  # type: ignore
    return str(current_role() or "").strip().lower() in {"admin", "manager", "supervisor"}


def _confirm_key(prefix: str) -> str:
    return f"{prefix}_delete_confirm_open"


@contextmanager
def modal_danger_zone():
    """Compact bordered danger section for detail modals."""
    with st.container(border=True):
        st.markdown('<span class="ips-modal-danger-zone-marker"></span>', unsafe_allow_html=True)
        st.markdown('<p class="ips-modal-danger-zone-title">Danger zone</p>', unsafe_allow_html=True)
        yield


def render_modal_delete_panel(
    *,
    prefix: str,
    delete_label: str = "Delete",
    confirm_message: str,
    confirm_label: str = "Confirm Delete",
    can_delete: bool = True,
    disabled_reason: str | None = None,
    on_confirm: Callable[[], None],
    hidden: bool = False,
) -> None:
    """Two-step delete: outlined trigger, warning, cancel + solid confirm."""
    if hidden or (not can_delete and not disabled_reason):
        return
    if not can_delete:
        st.caption(disabled_reason or "You do not have permission to delete this record.")
        return

    confirm_key = _confirm_key(prefix)
    if not st.session_state.get(confirm_key):
        if danger_outline_button(
            delete_label,
            f"{prefix}_delete_open",
            use_container_width=True,
        ):
            st.session_state[confirm_key] = True
            st.rerun()
        return

    st.warning(confirm_message)
    btn_cancel, btn_confirm = st.columns(2, gap="small")
    with btn_cancel:
        if st.button("Cancel", key=f"{prefix}_delete_cancel", use_container_width=True):
            st.session_state.pop(confirm_key, None)
            st.rerun()
    with btn_confirm:
        if danger_solid_button(
            confirm_label,
            f"{prefix}_delete_go",
            use_container_width=True,
        ):
            on_confirm()
            st.session_state.pop(confirm_key, None)
