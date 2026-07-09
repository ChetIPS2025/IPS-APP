"""Tests for admin View As preview helpers."""

from __future__ import annotations

import pytest
import streamlit as st

from app.utils.view_as import (
    IPS_VIEW_AS_ACTIVE_KEY,
    IPS_VIEW_AS_MODE_KEY,
    IPS_VIEWPORT_NARROW_KEY,
    clear_view_as,
    ensure_view_as_navigation,
    is_view_as_active,
    is_view_as_mobile_preview,
    set_view_as,
    ui_role,
)


def _reset_view_as() -> None:
    clear_view_as()


def test_ui_role_returns_real_role_when_preview_inactive(monkeypatch):
    _reset_view_as()
    monkeypatch.setattr("app.utils.view_as.current_role", lambda: "admin")
    assert ui_role() == "admin"


def test_set_view_as_supervisor_activates_preview(monkeypatch):
    _reset_view_as()
    monkeypatch.setattr("app.utils.view_as.current_role", lambda: "admin")
    monkeypatch.setattr("app.navigation.set_nav_slug", lambda _slug: None)
    set_view_as("supervisor")
    assert is_view_as_active()
    assert st.session_state[IPS_VIEW_AS_MODE_KEY] == "supervisor"
    assert ui_role() == "supervisor"


def test_set_view_as_field_mobile_uses_employee_role_and_narrow_viewport(monkeypatch):
    _reset_view_as()
    nav_calls: list[str] = []
    monkeypatch.setattr("app.utils.view_as.current_role", lambda: "admin")
    monkeypatch.setattr("app.navigation.set_nav_slug", nav_calls.append)
    set_view_as("field_mobile")
    assert is_view_as_active()
    assert ui_role() == "employee"
    assert is_view_as_mobile_preview()
    assert st.session_state[IPS_VIEWPORT_NARROW_KEY] is True
    assert nav_calls == ["employee_portal"]


def test_clear_view_as_restores_admin_preview(monkeypatch):
    _reset_view_as()
    monkeypatch.setattr("app.utils.view_as.current_role", lambda: "admin")
    monkeypatch.setattr("app.navigation.set_nav_slug", lambda _slug: None)
    set_view_as("employee")
    assert is_view_as_active()
    clear_view_as()
    assert not is_view_as_active()
    assert IPS_VIEW_AS_ACTIVE_KEY not in st.session_state


def test_clear_view_as_clears_picker_widget_state(monkeypatch):
    _reset_view_as()
    monkeypatch.setattr("app.utils.view_as.current_role", lambda: "admin")
    monkeypatch.setattr("app.navigation.set_nav_slug", lambda _slug: None)
    st.session_state["ips_view_as_select_admin_page"] = "Field Mode / Mobile Preview"
    set_view_as("employee")
    clear_view_as()
    assert "ips_view_as_select_admin_page" not in st.session_state


def test_ensure_view_as_navigation_redirects_off_admin_pages(monkeypatch):
    _reset_view_as()
    nav_calls: list[str] = []
    monkeypatch.setattr("app.utils.view_as.current_role", lambda: "admin")
    monkeypatch.setattr("app.navigation.set_nav_slug", nav_calls.append)
    monkeypatch.setattr("app.navigation.current_nav_slug", lambda: "dashboard")
    monkeypatch.setattr("app.navigation.default_nav_slug", lambda: "employee_portal")
    monkeypatch.setattr("app.utils.view_as.st.rerun", lambda: (_ for _ in ()).throw(RuntimeError("rerun")))
    set_view_as("field_mobile")
    with pytest.raises(RuntimeError, match="rerun"):
        ensure_view_as_navigation()
    assert nav_calls[-1] == "employee_portal"
