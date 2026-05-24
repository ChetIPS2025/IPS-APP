"""Reusable destructive action button wrappers for Streamlit."""

from __future__ import annotations

from contextlib import contextmanager

import streamlit as st

DANGER_OUTLINE_PREFIX = "ips_danger_outline_"
DANGER_SOLID_PREFIX = "ips_danger_solid_"


@contextmanager
def danger_outline(key: str):
    """Wrap outlined red danger buttons (delete, deactivate, remove)."""
    with st.container(key=f"{DANGER_OUTLINE_PREFIX}{key}"):
        yield


@contextmanager
def danger_solid(key: str):
    """Wrap solid red confirmation buttons (permanent delete, confirm delete)."""
    with st.container(key=f"{DANGER_SOLID_PREFIX}{key}"):
        yield
