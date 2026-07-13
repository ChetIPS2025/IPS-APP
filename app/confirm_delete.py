"""
Destructive-action confirmation UI for Streamlit (IPS dark theme).

**Visibility** uses ``<key_prefix>_confirm_open`` in session state (see
:func:`destructive_confirm_open_key`). Use :func:`open_destructive_confirmation` /
:func:`close_destructive_confirmation`, or set that key yourself. Pages store extra
payload (e.g. pending row IDs) under their own keys.

Example: open with ``open_destructive_confirmation('employees_delete')``, set
``employees_pending_delete_ids``, then call :func:`render_destructive_confirmation`
with ``on_confirm`` / ``on_cancel`` callables.
"""

from __future__ import annotations

import html
from collections.abc import Callable

import streamlit as st

from app.components.action_styles import danger_solid
IPS_DELETE_CONFIRM_STYLE_KEY = "ips_delete_confirm_styles_injected"


def destructive_confirm_open_key(key_prefix: str) -> str:
    """Session key used for panel visibility: ``{key_prefix}_confirm_open``."""
    return f"{key_prefix}_confirm_open"


def open_destructive_confirmation(key_prefix: str) -> None:
    st.session_state[destructive_confirm_open_key(key_prefix)] = True


def close_destructive_confirmation(key_prefix: str) -> None:
    st.session_state.pop(destructive_confirm_open_key(key_prefix), None)


def inject_delete_confirm_styles() -> None:
    """Bordered danger/warning panel — compact, distinct on dark background."""
    if st.session_state.get(IPS_DELETE_CONFIRM_STYLE_KEY):
        return
    st.session_state[IPS_DELETE_CONFIRM_STYLE_KEY] = True
    st.markdown(
        """
        <style>
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-del-anchor) {
            background: rgba(127, 29, 29, 0.2) !important;
            border-color: rgba(248, 113, 113, 0.5) !important;
            border-radius: 10px !important;
            padding: 10px 12px 12px 12px !important;
            margin-bottom: 12px !important;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-del-anchor) h3 {
            color: #fecaca !important;
            font-size: 1.05rem !important;
            font-weight: 700 !important;
            margin: 0 0 8px 0 !important;
        }
        .ips-del-msg {
            color: #e2e8f0;
            font-size: 0.92rem;
            line-height: 1.45;
            margin-bottom: 8px;
        }
        .ips-del-names-box {
            color: #cbd5e1;
            font-size: 0.88rem;
            margin: 0 0 10px 0;
            padding: 8px 10px;
            background: rgba(15, 23, 42, 0.55);
            border-radius: 6px;
            border: 1px solid rgba(148, 163, 184, 0.22);
            max-height: 140px;
            overflow-y: auto;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-del-anchor) .stButton > button p {
            white-space: nowrap !important;
            overflow: visible !important;
            text-overflow: clip !important;
            margin: 0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_destructive_panel_ui(
    *,
    key_prefix: str,
    title: str,
    message: str,
    confirm_label: str,
    cancel_label: str,
    name_lines: list[str] | None,
) -> tuple[bool, bool]:
    """Draw the bordered panel; returns (confirm_clicked, cancel_clicked)."""
    inject_delete_confirm_styles()
    confirm_key = f"ips_dc_{key_prefix}_confirm"
    cancel_key = f"ips_dc_{key_prefix}_cancel"
    with st.container(border=True):
        st.markdown('<span class="ips-del-anchor"></span>', unsafe_allow_html=True)
        st.markdown(f"### {html.escape(title)}")
        st.markdown(f'<p class="ips-del-msg">{html.escape(message)}</p>', unsafe_allow_html=True)
        if name_lines:
            st.caption("Selected")
            items = "\n".join(f"- {html.escape(n)}" for n in name_lines)
            st.markdown(
                f'<div class="ips-del-names-box"><pre style="margin:0;white-space:pre-wrap;font-size:0.88rem;">{items}</pre></div>',
                unsafe_allow_html=True,
            )
        bc1, bc2 = st.columns(2, gap="small")
        with bc1:
            with danger_solid(f"dc_{key_prefix}"):
                confirm = st.button(
                    confirm_label,
                    type="secondary",
                    use_container_width=True,
                    key=confirm_key,
                )
        with bc2:
            cancel = st.button(
                cancel_label,
                type="secondary",
                use_container_width=True,
                key=cancel_key,
            )
    return confirm, cancel


def render_destructive_confirmation(
    key_prefix: str,
    title: str,
    message: str,
    *,
    confirm_label: str,
    cancel_label: str,
    on_confirm: Callable[[], None],
    on_cancel: Callable[[], None] | None = None,
    name_lines: list[str] | None = None,
) -> None:
    """
    If ``{key_prefix}_confirm_open`` is truthy, render the panel and handle buttons.

    On **Confirm**, calls ``on_confirm``, clears the open flag, and reruns.
    On **Cancel**, calls ``on_cancel`` if provided, clears the open flag, and reruns.

    If the open flag is false, does nothing.
    """
    open_key = destructive_confirm_open_key(key_prefix)
    if not st.session_state.get(open_key):
        return

    confirm_clicked, cancel_clicked = _render_destructive_panel_ui(
        key_prefix=key_prefix,
        title=title,
        message=message,
        confirm_label=confirm_label,
        cancel_label=cancel_label,
        name_lines=name_lines,
    )

    if confirm_clicked:
        on_confirm()
        st.session_state.pop(open_key, None)
        st.rerun()

    if cancel_clicked:
        if on_cancel is not None:
            on_cancel()
        st.session_state.pop(open_key, None)
        st.rerun()

