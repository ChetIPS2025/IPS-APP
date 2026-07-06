"""Tests for sidebar shell helpers."""

from __future__ import annotations

import streamlit as st

from app.components.sidebar_shell import (
    IPS_SIDEBAR_NAV_FALLBACK_KEY,
    _fallback_nav_json,
    store_sidebar_nav_fallback,
)
from app.utils.constants import FIELD_NAV_PAGES
from app.utils.permissions import filter_field_nav_for_role


def test_store_sidebar_nav_fallback_keeps_slug_and_label():
    store_sidebar_nav_fallback([("jobs", "My Jobs"), ("field_dashboard", "Field Home")])
    rows = st.session_state[IPS_SIDEBAR_NAV_FALLBACK_KEY]
    assert rows == [
        {"slug": "jobs", "label": "My Jobs"},
        {"slug": "field_dashboard", "label": "Field Home"},
    ]
    assert '"My Jobs"' in _fallback_nav_json()


def test_employee_field_nav_excludes_company_updates():
    items = filter_field_nav_for_role(FIELD_NAV_PAGES, "employee")
    labels = [label for _slug, label in items]
    assert "Field Home" in labels
    assert "Today's Work" in labels
    assert "My Jobs" in labels
    assert "My To-Do" in labels
    assert "Log Time" in labels
    assert "Company Updates" not in labels
