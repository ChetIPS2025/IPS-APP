"""Pricing Guide Links tab — linked records, presence, and stock policy."""

from __future__ import annotations

from typing import Any

import streamlit as st

from app.components.catalog_presence_panel import render_catalog_presence_panel
from app.components.catalog_stock_policy_panel import render_catalog_stock_policy_panel
from app.components.record_modal import detail_field_html, dialog_card_html
from app.services.pricing_guide_service import clear_pricing_guide_cache


def render_pricing_guide_links_panel(row: dict[str, Any], *, permissions: Any) -> None:
    inv_label = str(row.get("inventory_label") or "").strip() or "Not linked"
    asset_label = str(row.get("asset_label") or "").strip() or "Not linked"
    body = (
        f"{detail_field_html('Inventory item', inv_label)}"
        f"{detail_field_html('Asset / equipment', asset_label)}"
        f"{detail_field_html('Stock policy', row.get('stock_policy_label') or 'Not stocked')}"
        f"{detail_field_html('Default reorder point', int(float(row.get('default_reorder_point') or 0)))}"
        f"{detail_field_html('Vendor', row.get('vendor') or '—')}"
        f"{detail_field_html('Labor role', row.get('labor_role') or '—')}"
        f"{detail_field_html('Equipment type', row.get('equipment_type') or '—')}"
        f"{detail_field_html('Travel type', row.get('travel_type') or '—')}"
    )
    st.markdown(dialog_card_html("Linked Records", body), unsafe_allow_html=True)
    if not permissions.can_manage:
        return
    render_catalog_presence_panel(
        row,
        can_manage=permissions.can_manage,
        on_change=clear_pricing_guide_cache,
    )
    render_catalog_stock_policy_panel(
        row,
        can_manage=permissions.can_manage_stock_policy,
        on_change=clear_pricing_guide_cache,
    )
