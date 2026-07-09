"""Tests for Pricing Guide list table HTML helpers."""

from __future__ import annotations

from app.components.pricing_guide_list_table import (
    _pg_link_html,
    _pg_thumb_link_html,
    build_pricing_guide_html_table,
    handle_pricing_guide_table_action,
    pg_description,
    pg_status_pill_html,
)


def test_pg_status_pill_html_includes_class():
    html_out = pg_status_pill_html("Active")
    assert "ips-pg-status-pill" in html_out
    assert "ips-pg-status-active" in html_out
    assert "Active" in html_out


def test_pg_link_html_uses_open_span():
    html_out = _pg_link_html("pg-1", "Hydraulic hose", extra_class="ips-dash-est-desc-link")
    assert 'role="button"' in html_out
    assert 'data-pg-action="open"' in html_out
    assert 'data-pg-id="pg-1"' in html_out
    assert "ips-pg-open-link" in html_out
    assert "Hydraulic hose" in html_out


def test_pg_thumb_link_html_wraps_thumbnail():
    html_out = _pg_thumb_link_html(
        "pg-1",
        {"id": "pg-1", "item": "Hydraulic hose"},
    )
    assert '<button type="button"' in html_out
    assert "ips-pg-thumb-cell-link" in html_out
    assert 'data-pg-action="open"' in html_out
    assert 'data-pg-id="pg-1"' in html_out
    assert "ips-pg-thumb-img" in html_out or "ips-pg-thumb-placeholder" in html_out


def test_build_pricing_guide_html_table_includes_columns_and_link():
    rows = [
        {
            "id": "pg-1",
            "item": "Hydraulic hose",
            "item_class": "Inventory",
            "category": "Hose",
            "unit": "ft",
            "default_cost": 12.5,
            "markup_pct": 25.0,
            "customer_price": 15.62,
            "vendor": "Acme Supply",
            "status": "Active",
        }
    ]
    html_out = build_pricing_guide_html_table(rows)
    assert "ips-dash-est-html-table" in html_out
    assert "ips-pg-html-catalog-table" in html_out
    assert "IMAGE" in html_out
    assert "DESCRIPTION" in html_out
    assert "VENDOR" in html_out
    assert 'data-pg-action="open"' in html_out
    assert 'data-pg-id="pg-1"' in html_out
    assert "ips-pg-thumb-cell-link" in html_out
    assert "Hydraulic hose" in html_out
    assert "Acme Supply" in html_out
    assert pg_description(rows[0]) == "Hydraulic hose"


def test_handle_pricing_guide_table_action_opens_item():
    opened: list[tuple[str, dict]] = []

    def _open(row_id: str, row: dict) -> None:
        opened.append((row_id, row))

    rows_by_id = {"pg-1": {"id": "pg-1", "item": "Hydraulic hose"}}
    handle_pricing_guide_table_action(
        "open:pg-1",
        rows_by_id,
        last_action_key="_test_pg_last_action",
        open_item_fn=_open,
    )
    assert opened == [("pg-1", {"id": "pg-1", "item": "Hydraulic hose"})]
