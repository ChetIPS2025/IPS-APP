"""Serialized tools HTML table bridge."""

from __future__ import annotations

from app.components.serialized_tools_list_table import build_serialized_tools_html_table


def test_build_serialized_tools_html_table_renders_open_links() -> None:
    html = build_serialized_tools_html_table(
        [
            {
                "_row_id": "tool-1",
                "_display_name": "M18 Drill",
                "_display_model": "2804-20",
                "_display_serial": "SN-1",
                "_display_trailer": "Trailer A",
                "_display_job": "Job 1",
                "_display_status": "Available",
                "_display_condition": "Good",
                "_thumb_asset": {"id": "tool-1", "asset_name": "M18 Drill"},
            }
        ],
        is_row_selected=lambda _rid: False,
    )
    assert 'data-st-action="open"' not in html
    assert 'href="' in html
    assert "asset_detail" in html
    assert "<a " in html
    assert "M18 Drill" in html
    assert 'data-st-action="select"' in html
    assert "ips-assets-html-equipment-table" in html
