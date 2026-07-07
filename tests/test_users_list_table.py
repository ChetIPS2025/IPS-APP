"""Tests for Users list table HTML helpers."""

from __future__ import annotations

from app.components.users_list_table import user_list_link_html


def test_user_list_link_html_includes_action_and_id():
    html_out = user_list_link_html("u-456", "Alice Admin")
    assert 'data-user-action="open"' in html_out
    assert 'data-user-id="u-456"' in html_out
    assert "Alice Admin" in html_out
    assert "ips-users-list-link" in html_out
