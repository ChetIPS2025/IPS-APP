"""Reusable delete / deactivate action panels for record detail modals."""

from __future__ import annotations

from collections.abc import Callable

import streamlit as st

try:
    from app.components.action_styles import danger_outline, danger_solid
except ImportError:
    from components.action_styles import danger_outline, danger_solid  # type: ignore


def can_admin_mutate() -> bool:
    try:
        from app.auth import current_role
    except ImportError:
        from auth import current_role  # type: ignore
    return str(current_role() or "").strip().lower() in {"admin", "manager", "supervisor"}


def _confirm_key(prefix: str) -> str:
    return f"{prefix}_delete_confirm_open"


def render_danger_button(
    label: str,
    *,
    prefix: str,
    button_key: str | None = None,
    disabled: bool = False,
    help: str | None = None,
    on_click: Callable[[], None] | None = None,
    use_container_width: bool = True,
) -> bool:
    """Outlined red action button. Returns True when clicked."""
    key = button_key or f"{prefix}_danger_btn"
    with danger_outline(prefix):
        return st.button(
            label,
            key=key,
            type="secondary",
            disabled=disabled,
            help=help,
            use_container_width=use_container_width,
            on_click=on_click,
        )


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
        st.markdown('<div class="ips-modal-delete-actions">', unsafe_allow_html=True)
        st.markdown('<span class="ips-modal-danger-zone" aria-hidden="true"></span>', unsafe_allow_html=True)
        with danger_outline(f"{prefix}_open"):
            if st.button(
                delete_label,
                key=f"{prefix}_delete_open",
                type="secondary",
                use_container_width=True,
            ):
                st.session_state[confirm_key] = True
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        return

    st.markdown('<div class="ips-modal-delete-confirm">', unsafe_allow_html=True)
    st.warning(confirm_message)
    btn_cancel, btn_confirm = st.columns(2, gap="small")
    with btn_cancel:
        if st.button("Cancel", key=f"{prefix}_delete_cancel", use_container_width=True):
            st.session_state.pop(confirm_key, None)
            st.rerun()
    with btn_confirm:
        with danger_solid(f"{prefix}_confirm"):
            if st.button(confirm_label, key=f"{prefix}_delete_go", type="secondary", use_container_width=True):
                on_confirm()
                st.session_state.pop(confirm_key, None)
    st.markdown("</div>", unsafe_allow_html=True)
