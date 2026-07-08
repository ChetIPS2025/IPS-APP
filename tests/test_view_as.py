"""Tests for admin View As preview helpers."""

from __future__ import annotations

import streamlit as st

from app.utils.view_as import (
    IPS_VIEW_AS_ACTIVE_KEY,
    IPS_VIEW_AS_MODE_KEY,
    clear_view_as,
    is_view_as_active,
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


def test_clear_view_as_restores_admin_preview(monkeypatch):
    _reset_view_as()
    monkeypatch.setattr("app.utils.view_as.current_role", lambda: "admin")
    monkeypatch.setattr("app.navigation.set_nav_slug", lambda _slug: None)
    set_view_as("employee")
    assert is_view_as_active()
    clear_view_as()
    assert not is_view_as_active()
    assert IPS_VIEW_AS_ACTIVE_KEY not in st.session_state
