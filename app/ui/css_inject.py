"""Helpers for CSS injection across Streamlit reruns."""

from __future__ import annotations

import streamlit as st


def css_inject_key(style_id: str) -> str:
    """Normalize a ``<style id>`` value into a session_state key."""
    return f"ips_css_injected_{style_id}"


def inject_css_once(style_id: str) -> bool:
    """
    Record that a CSS bundle was emitted and allow injection on this run.

    Always returns True. Streamlit re-executes the script on every rerun and only
    keeps DOM nodes that are output again; skipping injection after the first run
    drops ``<style>`` tags and breaks layout. Duplicate ``<style id="...">`` blocks
    are harmless — browsers apply the same rules again.
    """
    st.session_state[css_inject_key(style_id)] = True
    return True


__all__ = ["css_inject_key", "inject_css_once"]
