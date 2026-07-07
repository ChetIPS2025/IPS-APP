"""Tests for Users list table HTML helpers."""

from __future__ import annotations

from app.components.users_list_table import handle_users_table_action, user_list_link_html


def test_user_list_link_html_includes_action_and_id():
    html_out = user_list_link_html("u-456", "Alice Admin")
    assert 'data-user-action="open"' in html_out
    assert 'data-user-id="u-456"' in html_out
    assert "Alice Admin" in html_out
    assert "ips-users-list-link" in html_out


def test_handle_users_table_action_strips_open_prefix():
    opened: list[dict] = []

    handle_users_table_action(
        "open:u-456",
        {"u-456": {"id": "u-456", "name": "Alice Admin"}},
        last_action_key="users_test_last_action",
        open_user_fn=lambda user: opened.append(user),
    )

    assert opened == [{"id": "u-456", "name": "Alice Admin"}]
