"""Session-guard helpers for one-time CSS injection per Streamlit session."""

from __future__ import annotations

import streamlit as st


def css_inject_key(style_id: str) -> str:
    """Normalize a ``<style id>`` value into a session_state key."""
    return f"ips_css_injected_{style_id}"


def inject_css_once(style_id: str) -> bool:
    """
    Mark a CSS bundle as injected for this session.

    Returns True when the caller should inject CSS; False when already injected.
    """
    key = css_inject_key(style_id)
    if st.session_state.get(key):
        return False
    st.session_state[key] = True
    return True


__all__ = ["css_inject_key", "inject_css_once"]
