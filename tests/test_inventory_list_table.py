"""Tests for Inventory list table HTML helpers."""

from __future__ import annotations

from app.components.inventory_list_table import (
    _inventory_link_html,
    _inventory_thumb_link_html,
    build_inventory_html_table,
    handle_inventory_table_action,
    inventory_description,
    inventory_status_pill_html,
    normalize_inventory_status,
)


def test_normalize_inventory_status_maps_aliases():
    assert normalize_inventory_status("in stock") == "In Stock"
    assert normalize_inventory_status("low stock") == "Low Stock"
    assert normalize_inventory_status("on order") == "On Order"


def test_inventory_status_pill_html_includes_class():
    html_out = inventory_status_pill_html("In Stock")
    assert "ips-inventory-status-pill" in html_out
    assert "ips-inventory-status-in-stock" in html_out
    assert "In Stock" in html_out


def test_inventory_link_html_uses_native_anchor():
    html_out = _inventory_link_html("inv-1", "Copper fitting", extra_class="ips-dash-est-desc-link")
    assert "<a " in html_out
    assert 'target="_self"' in html_out
    assert "inventory_detail=inv-1" in html_out
    assert "Copper fitting" in html_out
    assert "ips-inventory-open-link" in html_out
    assert "<button" not in html_out


def test_inventory_thumb_link_html_wraps_thumbnail():
    html_out = _inventory_thumb_link_html(
        "inv-1",
        {"id": "inv-1", "description": "Copper fitting"},
    )
    assert '<button type="button"' in html_out
    assert "ips-inventory-thumb-cell-link" in html_out
    assert 'data-inv-action="open"' in html_out
    assert 'data-inventory-id="inv-1"' in html_out
    assert "ips-inventory-thumb-img" in html_out or "ips-inventory-thumb-placeholder" in html_out


def test_build_inventory_html_table_includes_columns_and_link():
    rows = [
        {
            "id": "inv-1",
            "description": "Copper fitting",
            "category": "Pipe",
            "location": "Warehouse A",
            "quantity_on_hand": 12,
            "unit": "ea",
            "unit_cost": 4.5,
            "status": "In Stock",
            "vendor": "Acme Supply",
        }
    ]
    html_out = build_inventory_html_table(rows)
    assert "ips-dash-est-html-table" in html_out
    assert "IMAGE" in html_out
    assert "DESCRIPTION" in html_out
    assert "VENDOR" in html_out
    assert 'data-inv-action="open"' in html_out
    assert 'data-inventory-id="inv-1"' in html_out
    assert "ips-inventory-thumb-cell-link" in html_out
    assert '<button type="button"' in html_out
    assert "Copper fitting" in html_out
    assert "Acme Supply" in html_out
    assert inventory_description(rows[0]) == "Copper fitting"


def test_handle_inventory_table_action_opens_item():
    opened: list[tuple[str, dict]] = []

    handle_inventory_table_action(
        "open:inv-1",
        {"inv-1": {"id": "inv-1", "description": "Widget"}},
        last_action_key="inventory_test_last_action",
        open_item_fn=lambda item_id, item: opened.append((item_id, item)),
    )

    assert opened == [("inv-1", {"id": "inv-1", "description": "Widget"})]

    handle_inventory_table_action(
        "open:inv-1",
        {"inv-1": {"id": "inv-1", "description": "Widget"}},
        last_action_key="inventory_test_last_action",
        open_item_fn=lambda item_id, item: opened.append((item_id, item)),
    )

    assert opened == [("inv-1", {"id": "inv-1", "description": "Widget"})]
