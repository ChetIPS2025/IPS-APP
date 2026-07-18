"""Rental Equipment dashboard — inspection status and history."""

from __future__ import annotations

from typing import Any

import streamlit as st

from app.components.rental_equipment_inspection_launcher import open_rental_inspection
from app.services.rental_equipment_inspection_service import (
    create_auto_inspection,
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
    from app.navigation import set_nav_slug
    set_nav_slug("assets")
    st.rerun()
