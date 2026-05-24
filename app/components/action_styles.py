"""Reusable destructive action button helpers for Streamlit."""

from __future__ import annotations

from contextlib import contextmanager

import streamlit as st

# Streamlit adds st-key-{button_key} on the widget wrapper — target these in CSS.
OUTLINE_BTN_PREFIX = "ips_dng_o_"
SOLID_BTN_PREFIX = "ips_dng_s_"

# Legacy container prefixes (kept for any remaining wrappers).
DANGER_OUTLINE_PREFIX = "ips_danger_outline_"
DANGER_SOLID_PREFIX = "ips_danger_solid_"


def outline_btn_key(suffix: str) -> str:
    return f"{OUTLINE_BTN_PREFIX}{suffix}"


def solid_btn_key(suffix: str) -> str:
    return f"{SOLID_BTN_PREFIX}{suffix}"


def danger_outline_button(
    label: str,
    suffix: str,
    *,
    disabled: bool = False,
    help: str | None = None,
    use_container_width: bool = True,
    **kwargs,
) -> bool:
    """Outlined red destructive button."""
    return st.button(
        label,
        key=outline_btn_key(suffix),
        type="secondary",
        disabled=disabled,
        help=help,
        use_container_width=use_container_width,
        **kwargs,
    )


def danger_solid_button(
    label: str,
    suffix: str,
    *,
    disabled: bool = False,
    help: str | None = None,
    use_container_width: bool = True,
    **kwargs,
) -> bool:
    """Solid red confirmation button."""
    return st.button(
        label,
        key=solid_btn_key(suffix),
        type="secondary",
        disabled=disabled,
        help=help,
        use_container_width=use_container_width,
        **kwargs,
    )


@contextmanager
def danger_outline(key: str):
    """Legacy container wrapper — prefer danger_outline_button()."""
    with st.container(key=f"{DANGER_OUTLINE_PREFIX}{key}"):
        yield


@contextmanager
def danger_solid(key: str):
    """Legacy container wrapper — prefer danger_solid_button()."""
    with st.container(key=f"{DANGER_SOLID_PREFIX}{key}"):
        yield
