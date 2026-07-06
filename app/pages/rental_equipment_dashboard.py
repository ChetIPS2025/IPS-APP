"""Mobile Rental Equipment page — opens when a rental asset QR code is scanned."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

try:
    from app.auth import current_profile
    from app.components.rental_equipment_inspection_launcher import (
        clear_rental_inspection_context,
        set_rental_inspection_context,
    )
    from app.pages.rental_equipment_inspection import render_inspection_form
    from app.services.assets_service import get_asset_image_url
    from app.services.rental_equipment_inspection_service import (
        create_auto_inspection,
        create_damage_report,
        get_rental_equipment_dashboard_summary,
        get_rental_inspection,
        inspection_type_label,
        list_rental_inspections_for_asset,
        save_rental_inspection,
        upload_inspection_photo,
        validate_for_complete,
    )
    from app.services.rental_equipment_inspection_specs import DAMAGE_ITEM_OPTIONS
    from app.styles import inject_trailer_dashboard_css
    from app.utils.formatting import fmt_date
except ImportError:
    from auth import current_profile  # type: ignore
    from components.rental_equipment_inspection_launcher import (  # type: ignore
        clear_rental_inspection_context,
        set_rental_inspection_context,
    )
    from pages.rental_equipment_inspection import render_inspection_form  # type: ignore
    from services.assets_service import get_asset_image_url  # type: ignore
    from services.rental_equipment_inspection_service import (  # type: ignore
        create_auto_inspection,
        create_damage_report,
        get_rental_equipment_dashboard_summary,
        get_rental_inspection,
        inspection_type_label,
        list_rental_inspections_for_asset,
        save_rental_inspection,
        upload_inspection_photo,
        validate_for_complete,
    )
    from services.rental_equipment_inspection_specs import DAMAGE_ITEM_OPTIONS  # type: ignore
    from styles import inject_trailer_dashboard_css  # type: ignore
    from utils.formatting import fmt_date  # type: ignore

_VIEW_KEY = "_rental_dash_view"


def _sk(asset_id: str, suffix: str) -> str:
    return f"rental_{suffix}_{asset_id}"


def _profile_user_id() -> str | None:
    uid = str((current_profile() or {}).get("id") or "").strip()
    return uid or None


def _set_view(asset_id: str, view: str) -> None:
    st.session_state[_VIEW_KEY] = view


def _render_info_rows(summary: dict[str, Any]) -> None:
    rows = [
        ("Current Status", summary.get("rental_status")),
        ("Assigned Customer", summary.get("customer_name")),
        ("Assigned Job", summary.get("job_label")),
    ]
    st.markdown('<div class="ips-trailer-dash-cards">', unsafe_allow_html=True)
    for label, value in rows:
        st.markdown(
            f'<div class="ips-trailer-dash-card">'
            f'<div class="ips-trailer-dash-card-label">{html.escape(str(label))}</div>'
            f'<div class="ips-trailer-dash-card-value">{html.escape(str(value or "—"))}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


def _start_inspection(asset: dict[str, Any], inspection_type: str) -> None:
    aid = str(asset.get("id") or "")
    job_id = str(asset.get("assigned_job_id") or "").strip() or None
    result = create_auto_inspection(asset_id=aid, inspection_type=inspection_type, job_id=job_id)
    if result.ok:
        set_rental_inspection_context(
            inspection_id=str((result.data or {}).get("id") or ""),
            asset_id=aid,
            job_id=job_id,
            inspection_type=inspection_type,
        )
        _set_view(aid, "inspection")
        st.rerun()
    else:
        st.error(result.error or f"Could not start {inspection_type} inspection.")


def _render_home(asset: dict[str, Any], summary: dict[str, Any]) -> None:
    aid = str(asset.get("id") or "")
    image_url = get_asset_image_url(asset)
    if image_url:
        st.markdown(
            f'<img class="ips-trailer-dash-hero" src="{html.escape(image_url, quote=True)}" alt="Equipment" />',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="ips-asset-scan-hero-placeholder">No photo</div>', unsafe_allow_html=True)

    st.markdown(
        f'<div class="ips-trailer-dash-title">{html.escape(str(summary.get("asset_name") or "Rental Equipment"))}</div>'
        f'<div class="ips-trailer-dash-sub">{html.escape(str(summary.get("asset_number") or ""))}</div>',
        unsafe_allow_html=True,
    )
    st.caption(f"Asset status: {html.escape(str(summary.get('asset_status') or '—'))}")
    _render_info_rows(summary)

    st.markdown("#### Actions")
    c1, c2 = st.columns(2, gap="small")
    with c1:
        if st.button("Checkout Inspection", type="primary", key=_sk(aid, "checkout"), use_container_width=True):
            _start_inspection(asset, "checkout")
    with c2:
        if st.button("Return Inspection", key=_sk(aid, "return"), use_container_width=True):
            _start_inspection(asset, "return")
    c3, c4 = st.columns(2, gap="small")
    with c3:
        if st.button("Report Damage", key=_sk(aid, "damage"), use_container_width=True):
            _set_view(aid, "damage")
            st.rerun()
    with c4:
        if st.button("Rental History", key=_sk(aid, "history"), use_container_width=True):
            _set_view(aid, "history")
            st.rerun()


def _clear_subviews(asset_id: str) -> None:
    st.session_state[_VIEW_KEY] = "home"
    st.session_state.pop("_rental_list_view", None)
    st.session_state.pop("_rental_list_asset_id", None)
    clear_rental_inspection_context()
    st.session_state.pop("rental_insp_draft", None)


def _render_history(asset: dict[str, Any]) -> None:
    aid = str(asset.get("id") or "")
    if st.button("← Back", key=_sk(aid, "hist_back"), use_container_width=True):
        _clear_subviews(aid)
        st.rerun()

    st.markdown("### Rental History")
    inspections = list_rental_inspections_for_asset(aid)
    if not inspections:
        st.info("No checkout, return, or damage reports recorded yet.")
        return

    for insp in inspections[:30]:
        label = inspection_type_label(str(insp.get("inspection_type") or ""))
        when = fmt_date(insp.get("completed_at") or insp.get("updated_at"))
        status = str(insp.get("status") or "—")
        st.markdown(f"**{html.escape(label)}** — {html.escape(status)} · {html.escape(when)}")
        if insp.get("damage_reported") or insp.get("inspection_type") == "damage":
            st.caption(
                f"Damage: {html.escape(str(insp.get('damage_location') or '—'))} — "
                f"{html.escape(str(insp.get('damage_description') or '')[:120])}"
            )
        pdf_url = str(insp.get("pdf_url") or "").strip()
        if pdf_url.startswith("http"):
            st.link_button("Download PDF", pdf_url, key=f"rental_hist_pdf_{insp.get('id')}")


def _render_damage_report(asset: dict[str, Any]) -> None:
    aid = str(asset.get("id") or "")
    if st.button("← Back", key=_sk(aid, "dmg_back"), use_container_width=True):
        _clear_subviews(aid)
        st.rerun()

    st.markdown("### Report Damage")
    st.caption("Equipment will be marked Needs Repair when this report is submitted.")
    damaged_item = st.selectbox("Damaged item", DAMAGE_ITEM_OPTIONS, key=_sk(aid, "dmg_item"))
    notes = st.text_area("Notes", height=100, key=_sk(aid, "dmg_notes"))
    photo = st.camera_input("Damage photo", key=_sk(aid, "dmg_cam"))
    upload = st.file_uploader(
        "Or upload photo",
        type=["png", "jpg", "jpeg", "webp"],
        key=_sk(aid, "dmg_up"),
        label_visibility="collapsed",
    )
    image_file = photo or upload

    if st.button("Submit Damage Report", type="primary", key=_sk(aid, "dmg_submit"), use_container_width=True):
        if not str(notes or "").strip():
            st.error("Notes are required.")
            return
        if image_file is None:
            st.error("A damage photo is required.")
            return

        draft = create_damage_report(
            asset_id=aid,
            damaged_item=damaged_item,
            notes=notes,
            job_id=str(asset.get("assigned_job_id") or "").strip() or None,
        )
        if not draft.ok:
            st.error(draft.error or "Could not create damage report.")
            return

        iid = str((draft.data or {}).get("id") or "").strip()
        if not iid:
            st.error("Could not create damage report.")
            return

        path, url = upload_inspection_photo(iid, "damage_photo", image_file, uploaded_by=_profile_user_id())
        if not path and not url:
            st.error("Could not upload damage photo.")
            return

        record = get_rental_inspection(iid) or {}
        record = {
            **record,
            "id": iid,
            "asset_id": aid,
            "inspection_type": "damage",
            "damage_reported": True,
            "damage_location": damaged_item,
            "damage_description": notes,
        }
        errs = validate_for_complete(record)
        if errs:
            st.error(" · ".join(errs[:3]))
            return

        result = save_rental_inspection(record, inspection_id=iid, mark_complete=True)
        if result.ok:
            st.success("Damage report saved. Equipment marked Needs Repair.")
            _clear_subviews(aid)
            st.rerun()
        else:
            st.error(result.error or "Could not save damage report.")


def _render_inspection(asset: dict[str, Any]) -> None:
    render_inspection_form(embedded=True)


def render_rental_equipment_dashboard(asset: dict[str, Any]) -> None:
    """Dedicated rental equipment landing page from QR scan."""
    inject_trailer_dashboard_css()
    st.markdown('<span class="ips-trailer-dash-scope" aria-hidden="true"></span>', unsafe_allow_html=True)

    aid = str(asset.get("id") or "")
    summary = get_rental_equipment_dashboard_summary(asset)
    view = str(st.session_state.get(_VIEW_KEY) or "home")

    st.markdown("## Rental Equipment")
    if view == "inspection":
        _render_inspection(asset)
    elif view == "history":
        _render_history(asset)
    elif view == "damage":
        _render_damage_report(asset)
    else:
        _render_home(asset, summary)
