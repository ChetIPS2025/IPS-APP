"""Estimates page — delegates to the modular app/estimates/ package.

This module is the Streamlit page entry point registered in app/main.py.
It forwards the render() call to app/estimates/page.py, which implements
the clean, modular structure.

The original implementation is preserved inline below and used as a fallback
if the new module cannot be imported (e.g. partial deployments).
"""
from __future__ import annotations


def render() -> None:
    """Entry point called by main.py."""
    try:
        from app.estimates.page import render as _new_render
        _new_render()
    except Exception as _err:
        import streamlit as st
        st.error(f"Estimates page failed to load: {_err}")
        import traceback
        st.code(traceback.format_exc())
        st.stop()
