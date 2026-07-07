"""Tests for Users list deleted-user visibility filtering."""

from __future__ import annotations

from app.pages.employees import (
    _filter_users_by_deleted_visibility,
    _user_filter_status,
    _user_is_deleted,
)


def test_user_is_deleted_from_status() -> None:
    assert _user_is_deleted({"status": "Deleted"}) is True


def test_user_is_deleted_from_deleted_at() -> None:
    assert _user_is_deleted({"status": "Active", "deleted_at": "2026-01-02T00:00:00Z"}) is True


def test_user_is_deleted_from_is_deleted_flag() -> None:
    assert _user_is_deleted({"status": "Active", "is_deleted": True}) is True


def test_user_filter_status_marks_deleted_rows() -> None:
    assert _user_filter_status({"status": "Active", "deleted_at": "2026-01-02"}) == "Deleted"


def test_default_visibility_hides_deleted_users() -> None:
    rows = [
        {"id": "1", "status": "Active"},
        {"id": "2", "status": "Deleted"},
        {"id": "3", "status": "Active", "deleted_at": "2026-01-02"},
    ]
    visible = _filter_users_by_deleted_visibility(rows, status_filter=[])
    assert [row["id"] for row in visible] == ["1"]


def test_deleted_status_filter_shows_deleted_users() -> None:
    rows = [
        {"id": "1", "status": "Active"},
        {"id": "2", "status": "Deleted"},
    ]
    visible = _filter_users_by_deleted_visibility(rows, status_filter=["Deleted"])
    assert [row["id"] for row in visible] == ["1", "2"]


def test_active_status_filter_hides_deleted_users() -> None:
    rows = [
        {"id": "1", "status": "Active"},
        {"id": "2", "status": "Deleted"},
    ]
    visible = _filter_users_by_deleted_visibility(rows, status_filter=["Active"])
    assert [row["id"] for row in visible] == ["1"]
