"""Rental Equipment dashboard — inspection status and history."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

try:
    from app.components.rental_equipment_inspection_launcher import open_rental_inspection
    from app.pages._core._access import begin_module
    from app.pages._core._data import load_jobs
    from app.services.rental_equipment_inspection_service import (
        create_auto_inspection,
        inspection_type_label,
        list_rental_equipment_assets,
        list_rental_inspections_for_asset,
        rental_inspection_dashboard_status,
    )
except ImportError:
    from components.rental_equipment_inspection_launcher import open_rental_inspection  # type: ignore
    from pages._core._access import begin_module  # type: ignore
    from pages._core._data import load_jobs  # type: ignore
    from services.rental_equipment_inspection_service import (  # type: ignore
        create_auto_inspection,
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


def _job_label(job_id: str | None) -> str:
    jid = str(job_id or "").strip()
    if not jid:
        return "—"
    for j in load_jobs():
        if str(j.get("id") or "") == jid:
            num = str(j.get("job_number") or j.get("number") or "").strip()
            name = str(j.get("job_name") or j.get("name") or "").strip()
            return f"{num} — {name}".strip(" —") if num or name else jid
    return jid


def render() -> None:
    begin_module("Rental Equipment", "Checkout, daily, and return inspections with photo proof.")
    assets = list_rental_equipment_assets()
    if not assets:
        st.info("No rental equipment assets found. Mark assets as rentable or set category to Rental Equipment.")
        return

    st.caption(f"{len(assets)} rental asset(s)")
    for asset in assets:
        aid = str(asset.get("id") or "")
        inspections = list_rental_inspections_for_asset(aid)
        status = rental_inspection_dashboard_status(asset, inspections)
        bg = _STATUS_COLORS.get(status, "#f1f5f9")
        name = html.escape(str(asset.get("asset_name") or asset.get("name") or "Asset"))
        num = html.escape(str(asset.get("asset_number") or asset.get("asset_id") or "—"))
        job_id = str(asset.get("assigned_job_id") or "").strip() or None
        with st.container(border=True):
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start;">'
                f"<div><strong>{name}</strong><div style='color:#64748b;font-size:0.85rem;'>"
                f"Asset {num} · Job: {html.escape(_job_label(job_id))}</div></div>"
                f'<span style="background:{bg};padding:4px 10px;border-radius:999px;font-size:0.78rem;font-weight:700;">'
                f"{html.escape(status)}</span></div>",
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
            with c1:
                if open_checkout:
                    if st.button("Open Checkout", key=f"rei_open_co_{aid}", use_container_width=True):
                        open_rental_inspection(inspection_id=str(open_checkout.get("id") or ""), asset_id=aid)
                elif job_id:
                    if st.button("Start Checkout", key=f"rei_start_co_{aid}", use_container_width=True):
                        res = create_auto_inspection(asset_id=aid, inspection_type="checkout", job_id=job_id)
                        if res.ok:
                            open_rental_inspection(inspection_id=str((res.data or {}).get("id") or ""), asset_id=aid)
                        else:
                            st.error(res.error or "Could not create checkout inspection.")
            with c2:
                if job_id:
                    if st.button("Daily Inspection", key=f"rei_daily_{aid}", use_container_width=True):
                        res = create_auto_inspection(asset_id=aid, inspection_type="daily", job_id=job_id)
                        if res.ok:
                            open_rental_inspection(inspection_id=str((res.data or {}).get("id") or ""), asset_id=aid)
                        else:
                            st.error(res.error or "Could not create daily inspection.")
            with c3:
                if open_return:
                    if st.button("Open Return", key=f"rei_open_ret_{aid}", use_container_width=True):
                        open_rental_inspection(inspection_id=str(open_return.get("id") or ""), asset_id=aid)
                else:
                    if st.button("Start Return", key=f"rei_start_ret_{aid}", use_container_width=True):
                        res = create_auto_inspection(
                            asset_id=aid,
                            inspection_type="return",
                            job_id=job_id,
                        )
                        if res.ok:
                            open_rental_inspection(inspection_id=str((res.data or {}).get("id") or ""), asset_id=aid)
                        else:
                            st.error(res.error or "Could not create return inspection.")
            with c4:
                completed = [i for i in inspections if i.get("status") in {"complete", "failed", "exported"}]
                st.caption(f"{len(completed)} completed")
            if inspections:
                with st.expander("Inspection history"):
                    for insp in inspections[:12]:
                        label = inspection_type_label(str(insp.get("inspection_type") or ""))
                        st.markdown(
                            f"**{label}** — {insp.get('status')} · "
                            f"{str(insp.get('completed_at') or insp.get('updated_at') or '')[:19]}"
                        )
                        pdf_url = str(insp.get("pdf_url") or "").strip()
                        if pdf_url.startswith("http"):
                            st.link_button("Download PDF", pdf_url, key=f"rei_pdf_{insp.get('id')}")
