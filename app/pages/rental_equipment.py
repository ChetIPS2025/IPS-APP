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
    if not begin_module("rental_equipment"):
        return
    assets = list_rental_equipment_assets()
    if not assets:
        st.info("No rental equipment assets found. Mark assets as rentable or set category to Rental Equipment.")
        return

    list_view = str(st.session_state.get(_LIST_VIEW_KEY) or "")
    list_asset = _find_asset(assets, st.session_state.get(_LIST_ASSET_KEY))
    if list_view == "damage" and list_asset:
        _render_damage_report(list_asset)
        return
    if list_view == "history" and list_asset:
        _render_history(list_asset)
        return

    st.caption(f"{len(assets)} rental asset(s)")
    for asset in assets:
        aid = str(asset.get("id") or "")
        summary = get_rental_equipment_dashboard_summary(asset)
        inspections = list_rental_inspections_for_asset(aid)
        status = summary.get("rental_status") or rental_inspection_dashboard_status(asset, inspections)
        bg = _STATUS_COLORS.get(str(status), "#f1f5f9")
        name = html.escape(str(summary.get("asset_name") or "Asset"))
        num = html.escape(str(summary.get("asset_number") or "—"))
        customer = html.escape(str(summary.get("customer_name") or "—"))
        job_label = html.escape(str(summary.get("job_label") or "—"))
        image_url = get_asset_image_url(asset)

        with st.container(border=True):
            cols = st.columns([1, 3], gap="medium")
            with cols[0]:
                if image_url:
                    st.image(image_url, width=96)
                else:
                    st.caption("No photo")
            with cols[1]:
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start;">'
                    f"<div><strong>{name}</strong><div style='color:#64748b;font-size:0.85rem;'>"
                    f"Asset {num}<br/>Customer: {customer}<br/>Job: {job_label}</div></div>"
                    f'<span style="background:{bg};padding:4px 10px;border-radius:999px;font-size:0.78rem;font-weight:700;">'
                    f"{html.escape(str(status))}</span></div>",
                    unsafe_allow_html=True,
                )

            c1, c2, c3, c4 = st.columns(4)
            open_checkout = next(
                (i for i in inspections if i.get("inspection_type") == "checkout" and i.get("status") == "draft"),
                None,
            )
            open_return = next(
                (i for i in inspections if i.get("inspection_type") == "return" and i.get("status") == "draft"),
                None,
            )
            job_id = str(asset.get("assigned_job_id") or "").strip() or None
            with c1:
                if open_checkout:
                    if st.button("Checkout Inspection", key=f"rei_open_co_{aid}", use_container_width=True):
                        open_rental_inspection(inspection_id=str(open_checkout.get("id") or ""), asset_id=aid)
                else:
                    if st.button("Checkout Inspection", key=f"rei_start_co_{aid}", use_container_width=True):
                        _start_inspection(asset, "checkout")
            with c2:
                if open_return:
                    if st.button("Return Inspection", key=f"rei_open_ret_{aid}", use_container_width=True):
                        open_rental_inspection(inspection_id=str(open_return.get("id") or ""), asset_id=aid)
                else:
                    if st.button("Return Inspection", key=f"rei_start_ret_{aid}", use_container_width=True):
                        _start_inspection(asset, "return")
            with c3:
                if st.button("Report Damage", key=f"rei_damage_{aid}", use_container_width=True):
                    st.session_state[_LIST_VIEW_KEY] = "damage"
                    st.session_state[_LIST_ASSET_KEY] = aid
                    st.rerun()
            with c4:
                if st.button("Rental History", key=f"rei_hist_{aid}", use_container_width=True):
                    st.session_state[_LIST_VIEW_KEY] = "history"
                    st.session_state[_LIST_ASSET_KEY] = aid
                    st.rerun()
