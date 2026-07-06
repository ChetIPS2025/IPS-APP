"""Rental Equipment dashboard — inspection status and history."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

try:
    from app.components.rental_equipment_inspection_launcher import open_rental_inspection
    from app.pages._core._access import begin_module
    from app.pages.rental_equipment_dashboard import _render_damage_report, _render_history
    from app.services.assets_service import get_asset_image_url
    from app.services.rental_equipment_inspection_service import (
        create_auto_inspection,
        get_rental_equipment_dashboard_summary,
        inspection_type_label,
        list_rental_equipment_assets,
        list_rental_inspections_for_asset,
        rental_inspection_dashboard_status,
    )
except ImportError:
    from components.rental_equipment_inspection_launcher import open_rental_inspection  # type: ignore
    from pages._core._access import begin_module  # type: ignore
    from pages.rental_equipment_dashboard import _render_damage_report, _render_history  # type: ignore
    from services.assets_service import get_asset_image_url  # type: ignore
    from services.rental_equipment_inspection_service import (  # type: ignore
        create_auto_inspection,
        get_rental_equipment_dashboard_summary,
        inspection_type_label,
        list_rental_equipment_assets,
        list_rental_inspections_for_asset,
        rental_inspection_dashboard_status,
    )

_STATUS_COLORS = {
    "Checked Out": "#dbeafe",
    "Returned": "#dcfce7",
    "Damage Reported": "#fee2e2",
    "Awaiting Inspection": "#fef3c7",
    "Available": "#f1f5f9",
}

_LIST_VIEW_KEY = "_rental_list_view"
_LIST_ASSET_KEY = "_rental_list_asset_id"


def _find_asset(assets: list[dict[str, Any]], asset_id: str | None) -> dict[str, Any] | None:
    aid = str(asset_id or "").strip()
    if not aid:
        return None
    return next((a for a in assets if str(a.get("id") or "") == aid), None)


def _start_inspection(asset: dict[str, Any], inspection_type: str) -> None:
    aid = str(asset.get("id") or "")
    job_id = str(asset.get("assigned_job_id") or "").strip() or None
    result = create_auto_inspection(asset_id=aid, inspection_type=inspection_type, job_id=job_id)
    if result.ok:
        open_rental_inspection(
            inspection_id=str((result.data or {}).get("id") or ""),
            asset_id=aid,
            job_id=job_id,
            inspection_type=inspection_type,
        )
    else:
        st.error(result.error or f"Could not start {inspection_type} inspection.")


def render() -> None:
    """Legacy slug — rental equipment is managed under Assets → Equipment."""
    try:
        from app.navigation import set_nav_slug
    except ImportError:
        from navigation import set_nav_slug  # type: ignore
    set_nav_slug("assets")
    st.rerun()
