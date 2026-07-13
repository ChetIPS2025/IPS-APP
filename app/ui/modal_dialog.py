"""Shared IPS modal / dialog patterns."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import streamlit as st

try:
    from app.components.record_modal import (
        build_modal_cache,
        clear_record_modal,
        get_modal_record,
        open_record_modal,
        render_missing_record,
        render_modal_header,
        render_modal_meta_grid,
        render_modal_shell,
        show_modal_if_pending,
    )
    from app.ui.ips_modal_form import ensure_modal_styles
except ImportError:
    from components.record_modal import (  # type: ignore
        build_modal_cache,
        clear_record_modal,
        get_modal_record,
        open_record_modal,
        render_missing_record,
        render_modal_header,
        render_modal_meta_grid,
        render_modal_shell,
        show_modal_if_pending,
    )
    from ui.ips_modal_form import ensure_modal_styles  # type: ignore

_ActionFn = Callable[[], None]


def render_dialog_shell() -> None:
    """Inject modal shell markup and styles."""
    ensure_modal_styles()
    render_modal_shell()


def render_dialog_header(
    title: str,
    *,
    subtitle: str = "",
    status: str = "",
) -> None:
    render_modal_header(title=title, subtitle=subtitle, status=status)


def render_dialog_footer(
    *,
    cancel_key: str,
    save_key: str,
    on_cancel: Callable[[], None] | None = None,
    on_save: Callable[[], None] | None = None,
    cancel_label: str = "Cancel",
    save_label: str = "Save",
    save_disabled: bool = False,
) -> None:
    """Aligned Cancel / Save footer for dialogs."""
    st.markdown(
        '<span class="ips-dialog-footer ips-dialog-footer-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    _, cancel_col, save_col = st.columns([2, 1, 1], gap="small")
    with cancel_col:
        if st.button(cancel_label, key=cancel_key, use_container_width=True):
            if on_cancel:
                on_cancel()
    with save_col:
        if st.button(
            save_label,
            key=save_key,
            type="primary",
            use_container_width=True,
            disabled=save_disabled,
        ):
            if on_save:
                on_save()


__all__ = [
    "build_modal_cache",
    "clear_record_modal",
    "get_modal_record",
    "open_record_modal",
    "render_missing_record",
    "render_dialog_shell",
    "render_dialog_header",
    "render_dialog_footer",
    "render_modal_meta_grid",
    "show_modal_if_pending",
    "ensure_modal_styles",
]
