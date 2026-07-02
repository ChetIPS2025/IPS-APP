"""Tests for dashboard Company Updates feed helpers."""

from __future__ import annotations

from app.components.company_updates_feed import (
    connecteam_feed_card_html,
    dashboard_company_updates_feed_html,
    dashboard_update_visible,
    sort_dashboard_updates,
)


def test_dashboard_update_visible_filters_drafts_and_projects():
    assert dashboard_update_visible({"title": "Hello", "status": "published", "category": "General"})
    assert not dashboard_update_visible({"title": "Draft", "status": "draft", "category": "General"})
    assert not dashboard_update_visible(
        {"title": "Build", "status": "published", "category": "Project Update"}
    )
    assert not dashboard_update_visible({"title": "", "status": "published", "category": "General"})


def test_sort_dashboard_updates_pins_first():
    rows = [
        {"id": "1", "date": "2026-05-01", "pinned": False},
        {"id": "2", "date": "2026-05-10", "pinned": True},
        {"id": "3", "date": "2026-05-20", "pinned": False},
    ]
    sorted_rows = sort_dashboard_updates(rows)
    assert sorted_rows[0]["id"] == "2"
    assert [r["id"] for r in sorted_rows[1:]] == ["3", "1"]


def test_connecteam_feed_card_html_includes_author_and_status():
    html = connecteam_feed_card_html(
        {
            "id": "abc",
            "title": "Safety Reminder",
            "body": "Stay hydrated on hot days.",
            "category": "Safety Alert",
            "date": "2026-05-29",
            "created_by_name": "Jane Smith",
            "is_new": True,
        }
    )
    assert "Jane Smith" in html
    assert "Safety Reminder" in html
    assert "ips-ct-status-new" in html
    assert "JS" in html


def test_dashboard_company_updates_feed_html_empty():
    assert "No announcements" in dashboard_company_updates_feed_html([], empty_message="No announcements")


def test_dashboard_company_updates_feed_html_renders_cards():
    html = dashboard_company_updates_feed_html(
        [{"id": "1", "title": "BBQ", "body": "May 20", "category": "Event", "date": "2026-05-01"}]
    )
    assert "ips-ct-feed-stack" in html
    assert "BBQ" in html
