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


def test_nav_button_label_includes_icon_and_text():
    from app.components.sidebar import _nav_button_label

    full = _nav_button_label("jobs", "Jobs")
    assert "Jobs" in full
    assert full == "💼\u2002Jobs"
    assert nav_icon_for_slug("jobs") == "💼"
    assert nav_icon_for_slug("unknown_slug") == "•"


def test_sidebar_width_tokens_match_design_spec():
    from app.components.sidebar_shell import (
        IPS_SIDEBAR_COLLAPSED_HEADER_HEIGHT_PX,
        IPS_SIDEBAR_COLLAPSED_LOGO_PX,
    )

    assert IPS_SIDEBAR_EXPANDED_WIDTH_PX == 232
    assert IPS_SIDEBAR_COLLAPSED_WIDTH_PX == 48
    assert IPS_SIDEBAR_COLLAPSED_HEADER_HEIGHT_PX == 56
    assert IPS_SIDEBAR_COLLAPSED_LOGO_PX == 28


def test_employee_nav_is_simplified_portal_menu():
    items = filter_employee_nav_for_role(EMPLOYEE_NAV_PAGES, "employee")
    labels = [label for _slug, label in items]
    assert labels == ["Home", "QR Scan", "Resources", "My Profile"]
    assert "Dashboard" not in labels
    assert "Jobs" not in labels


def test_sidebar_shell_script_targets_streamlit_156_collapse_button():
    from app.components.sidebar_shell import _shell_script

    script = _shell_script("[]")
    assert "stSidebarCollapseButton" in script
    assert "stSidebarCollapsed-" in script
    assert "forceExpandSidebar" in script


def test_inject_sidebar_shell_injects_layout_on_every_render():
    import inspect

    from app.components.sidebar_shell import inject_sidebar_shell

    source = inspect.getsource(inject_sidebar_shell)
    assert "_shell_css()" in source
    assert "if st.session_state.get(IPS_SIDEBAR_SHELL_KEY)" not in source


def test_employee_field_nav_is_restricted_without_legacy_access():
    items = filter_field_nav_for_role(FIELD_NAV_PAGES, "employee")
    labels = [label for _slug, label in items]
    assert "Field Home" not in labels
    assert "My Jobs" not in labels
