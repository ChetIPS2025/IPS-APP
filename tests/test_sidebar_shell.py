"""Tests for sidebar shell helpers."""

from __future__ import annotations

import streamlit as st

from app.components.sidebar_nav_icons import nav_icon_for_slug
from app.components.sidebar_shell import (
    IPS_SIDEBAR_COLLAPSED_HYDRATED_KEY,
    IPS_SIDEBAR_COLLAPSED_SESSION_KEY,
    IPS_SIDEBAR_COLLAPSED_WIDTH_PX,
    IPS_SIDEBAR_COLLAPSE_AFTER_NAV_KEY,
    IPS_SIDEBAR_EXPANDED_WIDTH_PX,
    IPS_SIDEBAR_NAV_FALLBACK_KEY,
    _fallback_nav_json,
    apply_pending_sidebar_collapse,
    capture_sidebar_collapsed_from_query,
    ensure_sidebar_collapsed_hydrated,
    is_sidebar_collapsed,
    request_sidebar_collapse_after_nav,
    set_sidebar_collapsed,
    store_sidebar_nav_fallback,
)
from app.utils.constants import EMPLOYEE_NAV_PAGES, FIELD_NAV_PAGES
from app.utils.permissions import filter_employee_nav_for_role, filter_field_nav_for_role


def test_store_sidebar_nav_fallback_keeps_slug_label_and_icon():
    store_sidebar_nav_fallback([("jobs", "My Jobs"), ("field_dashboard", "Field Home")])
    rows = st.session_state[IPS_SIDEBAR_NAV_FALLBACK_KEY]
    assert rows == [
        {"slug": "jobs", "label": "My Jobs", "icon": "💼"},
        {"slug": "field_dashboard", "label": "Field Home", "icon": "🏠"},
    ]
    assert '"My Jobs"' in _fallback_nav_json()


def test_sidebar_collapse_session_helpers():
    set_sidebar_collapsed(False)
    assert is_sidebar_collapsed() is False
    request_sidebar_collapse_after_nav()
    apply_pending_sidebar_collapse()
    assert is_sidebar_collapsed() is False
    assert IPS_SIDEBAR_COLLAPSE_AFTER_NAV_KEY not in st.session_state


def test_capture_sidebar_collapsed_from_query():
    st.session_state.pop(IPS_SIDEBAR_COLLAPSED_SESSION_KEY, None)
    st.query_params["ips_sb"] = "c"
    capture_sidebar_collapsed_from_query()
    assert is_sidebar_collapsed() is True
    assert "ips_sb" not in st.query_params


def test_ensure_sidebar_collapsed_hydrated_skips_when_session_set():
    st.session_state[IPS_SIDEBAR_COLLAPSED_HYDRATED_KEY] = True
    st.session_state[IPS_SIDEBAR_COLLAPSED_SESSION_KEY] = False
    ensure_sidebar_collapsed_hydrated()
    assert is_sidebar_collapsed() is False


def test_nav_button_label_collapsed_icon_only():
    from app.components.sidebar import _nav_button_label

    full = _nav_button_label("jobs", "Jobs", collapsed=False)
    icon_only = _nav_button_label("jobs", "Jobs", collapsed=True)
    assert "Jobs" in full
    assert "Jobs" not in icon_only
    assert icon_only == "💼"
    assert nav_icon_for_slug("jobs") == "💼"
    assert nav_icon_for_slug("unknown_slug") == "•"


def test_sidebar_width_tokens_match_design_spec():
    assert IPS_SIDEBAR_EXPANDED_WIDTH_PX == 240
    assert IPS_SIDEBAR_COLLAPSED_WIDTH_PX == 72


def test_employee_nav_is_simplified_portal_menu():
    items = filter_employee_nav_for_role(EMPLOYEE_NAV_PAGES, "employee")
    labels = [label for _slug, label in items]
    assert labels == ["Home", "QR Scan", "Resources", "My Profile"]
    assert "Dashboard" not in labels
    assert "Jobs" not in labels


def test_employee_field_nav_is_restricted_without_legacy_access():
    items = filter_field_nav_for_role(FIELD_NAV_PAGES, "employee")
    labels = [label for _slug, label in items]
    assert "Field Home" not in labels
    assert "My Jobs" not in labels
