"""Tests for Users list table HTML helpers."""

from __future__ import annotations

import sys
import types

from app.components.users_list_table import (
    build_users_html_table,
    handle_users_table_action,
    user_avatar_html,
    user_initials,
    user_list_link_html,
)


def test_user_list_link_html_includes_action_and_id():
    html_out = user_list_link_html("u-456", "Alice Admin")
    assert 'data-user-action="open"' in html_out
    assert 'data-user-id="u-456"' in html_out
    assert "Alice Admin" in html_out
    assert "ips-users-list-link" in html_out
    assert 'role="button"' in html_out


def test_user_initials_from_name():
    assert user_initials("Alice Admin") == "AA"
    assert user_initials("Bob") == "BO"


def test_user_avatar_html_uses_initials_without_photo():
    html_out = user_avatar_html({"name": "Alice Admin"})
    assert "ips-users-avatar-initials" in html_out
    assert "AA" in html_out


def test_user_avatar_html_uses_profile_photo():
    html_out = user_avatar_html(
        {"name": "Alice Admin", "photo_url": "https://cdn.example.com/alice.jpg"},
    )
    assert 'class="ips-users-avatar"' in html_out
    assert "https://cdn.example.com/alice.jpg" in html_out


def test_build_users_html_table_includes_required_columns():
    rows = [
        {
            "id": "u-1",
            "name": "Alice Admin",
            "email": "alice@example.com",
            "permission_role": "Admin",
            "phone": "337-555-0100",
            "last_login": "2026-07-01T10:00:00",
            "status": "Active",
        }
    ]
    html_out = build_users_html_table(
        rows,
        display_phone_fn=lambda u: str(u.get("phone") or "—"),
        display_last_login_fn=lambda u: "Jul 01, 2026",
        display_status_fn=lambda u: "Active",
    )
    assert "ips-users-html-list-table" in html_out
    assert "NAME" in html_out
    assert "EMAIL" in html_out
    assert "ROLE" in html_out
    assert "LAST LOGIN" in html_out
    assert "ACTIONS" in html_out
    assert "Alice Admin" in html_out
    assert 'data-user-id="u-1"' in html_out


def test_handle_users_table_action_strips_open_prefix(monkeypatch):
    opened: list[tuple[str, dict]] = []
    reran: list[str] = []

    perf_mod = types.ModuleType("app.ui.streamlit_perf")
    perf_mod.ips_app_rerun = lambda: reran.append("app")
    monkeypatch.setitem(sys.modules, "app.ui.streamlit_perf", perf_mod)

    handle_users_table_action(
        "open:u-456",
        {"u-456": {"id": "u-456", "name": "Alice Admin"}},
        last_action_key="users_test_last_action",
        open_user_fn=lambda user_id, user: opened.append((user_id, user)),
    )

    assert opened == [("u-456", {"id": "u-456", "name": "Alice Admin"})]
    assert reran == ["app"]
