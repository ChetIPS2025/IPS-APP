from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

try:
    from app.asset_responsive import inject_asset_workflow_mobile_css
    from app.mobile_ui import IPS_VIEWPORT_NARROW_KEY, ensure_narrow_viewport_detected
    from app.auth import current_profile, current_role
    from app.branding import render_header
    from app.db import (
        create_signed_url,
        fetch_by_match,
        fetch_by_match_admin,
        fetch_one,
        fetch_table,
        insert_row_admin,
        update_rows_admin,
    )
    from app.services.asset_constants import DOCUMENT_TYPES
    from app.services.asset_document_util import persist_asset_document_upload
    from app.services.asset_photo_autofill import extract_asset_from_photos
    from app.services.asset_qr import (
        qr_label_2x1_sticker_download_filename,
        qr_label_2x1_sticker_pdf_bytes,
        qr_label_for_download,
        qr_payload,
        qr_png_bytes,
    )
    from app.services.asset_service import (
        append_asset_photos,
        apply_extraction_to_asset,
        delete_asset_and_related,
        optional_numeric,
        save_maintenance_record,
    )
    from app.services.job_service import job_row_select_label
    from app.ui import IPS_NAV_PENDING_KEY
except ImportError:
    from asset_responsive import inject_asset_workflow_mobile_css  # type: ignore
    from mobile_ui import IPS_VIEWPORT_NARROW_KEY, ensure_narrow_viewport_detected  # type: ignore
    from auth import current_profile, current_role  # type: ignore
    from branding import render_header  # type: ignore
    from db import (  # type: ignore
        create_signed_url,
        fetch_by_match,
        fetch_by_match_admin,
        fetch_one,
        fetch_table,
        insert_row_admin,
        update_rows_admin,
    )
    from services.asset_constants import DOCUMENT_TYPES  # type: ignore
    from services.asset_document_util import persist_asset_document_upload  # type: ignore
    from services.asset_photo_autofill import extract_asset_from_photos  # type: ignore
    from services.asset_qr import (  # type: ignore
        qr_label_2x1_sticker_download_filename,
        qr_label_2x1_sticker_pdf_bytes,
        qr_label_for_download,
        qr_payload,
        qr_png_bytes,
    )
    from services.asset_service import (  # type: ignore
        append_asset_photos,
        apply_extraction_to_asset,
        delete_asset_and_related,
        optional_numeric,
        save_maintenance_record,
    )
    from services.job_service import job_row_select_label  # type: ignore
    from ui import IPS_NAV_PENDING_KEY  # type: ignore

# Primary hero image: visually dominant on desktop (``width=`` for Streamlit 1.33+).
_PRIMARY_IMAGE_WIDTH_DESKTOP = 520
_PRIMARY_IMAGE_WIDTH_MOBILE = 280
# QR in hero: secondary, compact (still scannable).
_QR_IMAGE_WIDTH_DESKTOP = 118
_QR_IMAGE_WIDTH_MOBILE = 102

_PROFILE_CARD_CSS = """
<style>
.ips-k {
    font-size: 11px;
    font-weight: 600;
    color: #9fb6d9;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin: 0 0 2px 0;
}
.ips-v {
    font-size: 15px;
    font-weight: 600;
    color: #f8fafc;
    margin: 0 0 6px 0;
    line-height: 1.3;
}
.ips-ad-facts-panel .ips-k { margin-bottom: 1px !important; }
.ips-ad-facts-panel .ips-v { margin-bottom: 8px !important; font-size: 14px !important; }
.ips-hero-title {
    font-size: 24px;
    font-weight: 800;
    color: #f8fafc;
    margin: 0 0 10px 0;
    line-height: 1.2;
}
.ips-ad-hero-centerblock {
    max-width: 600px;
    margin: 0 auto 2px auto;
}
/* Desktop hero: title under left-aligned primary image */
.ips-ad-meta-col.ips-ad-hero-stack:not(.ips-ad-hero-centerblock) {
    margin-top: 2px;
    max-width: 640px;
}
.ips-ad-meta-col.ips-ad-hero-stack:not(.ips-ad-hero-centerblock) .ips-hero-title {
    margin-bottom: 6px;
}
@media (max-width: 900px) {
    .ips-hero-title { font-size: 1.35rem !important; margin-bottom: 12px !important; }
    .ips-v { font-size: 15px !important; margin-bottom: 10px !important; }
    .ips-k { font-size: 10px !important; }
}
.ips-primary-badge {
    display: inline-block;
    background: linear-gradient(135deg, #2563eb, #1d4ed8);
    color: #f8fafc;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 5px 11px;
    border-radius: 7px;
    margin: 0 0 8px 0;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}
/* Quick Edit active: full-width callout */
.ips-ad-edit-mode-banner {
    display: block;
    width: 100%;
    box-sizing: border-box;
    text-align: center;
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 0.06em;
    color: #fffbeb;
    background: linear-gradient(90deg, rgba(180, 83, 9, 0.55), rgba(217, 119, 6, 0.7), rgba(180, 83, 9, 0.55));
    border: 1px solid rgba(251, 191, 36, 0.85);
    border-radius: 8px;
    padding: 10px 14px;
    margin: 0 0 14px 0;
    box-shadow: 0 2px 8px rgba(245, 158, 11, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.12);
}
.ips-badge-rental {
    display: inline-block;
    background: rgba(56, 189, 248, 0.2);
    color: #e0f2fe;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    padding: 5px 10px;
    border-radius: 7px;
    border: 1px solid rgba(56, 189, 248, 0.45);
    margin: 0 0 10px 0;
}
.ips-ad-photos-upload-row {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    flex-wrap: wrap;
    margin-top: 6px;
}
.ips-ad-qr-label {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #94a3b8;
    margin: 0 0 4px 0;
}
/* Read-only rental rates (IPS dark) */
.ips-ad-rental-panel {
    margin-top: 12px;
    padding: 12px 14px;
    border-radius: 10px;
    background: rgba(15, 23, 42, 0.65);
    border: 1px solid rgba(56, 189, 248, 0.28);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
}
.ips-ad-rental-panel .ips-ad-rental-title {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    color: #7dd3fc;
    margin: 0 0 10px 0;
}
.ips-ad-rental-panel .ips-ad-rental-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px 12px;
    font-size: 14px;
    color: #e2e8f0;
}
.ips-ad-rental-panel .ips-ad-rental-grid span.k {
    display: block;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #94a3b8;
    margin-bottom: 2px;
}
.ips-ad-rental-panel .ips-ad-rental-notes {
    margin-top: 10px;
    font-size: 13px;
    color: #cbd5e1;
    line-height: 1.45;
}
.ips-ad-rental-panel .ips-ad-rental-notes .k {
    display: block;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #94a3b8;
    margin-bottom: 4px;
}
/* Equipment portal: light top bar + hero */
.ips-ad-portal-top {
    padding: 4px 4px 8px 4px;
    margin-bottom: 2px;
    border-bottom: 1px solid rgba(71, 85, 105, 0.35);
}
.ips-ad-portal-top .ips-ad-portal-kicker {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #94a3b8;
    margin: 0 0 2px 0;
}
.ips-ad-portal-top .ips-ad-portal-title {
    font-size: 1.05rem;
    font-weight: 600;
    color: #e2e8f0;
    margin: 0;
    line-height: 1.35;
}
.ips-ad-facts-panel {
    background: rgba(15, 23, 42, 0.48);
    border: 1px solid rgba(71, 85, 105, 0.4);
    border-radius: 10px;
    padding: 8px 10px 8px 10px;
    margin-top: 0;
}
.ips-ad-facts-panel .ips-facts-head {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #7dd3fc;
    margin: 0 0 8px 0;
    padding-bottom: 6px;
    border-bottom: 1px solid rgba(100, 116, 139, 0.3);
}
.ips-ad-actions-hero {
    margin: 2px 0 8px 0;
}
/* Single dashboard row: equal-height buttons */
.ips-ad-dash-actions [data-testid="column"] button {
    min-height: 2.35rem !important;
    font-size: 0.82rem !important;
    padding-left: 0.35rem !important;
    padding-right: 0.35rem !important;
}
.ips-ad-doc-table {
    border: 1px solid rgba(51, 65, 85, 0.45);
    border-radius: 8px;
    overflow: hidden;
    margin-top: 2px;
}
.ips-ad-doc-table-head {
    display: flex;
    align-items: baseline;
    gap: 8px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #94a3b8;
    margin: 0;
    padding: 6px 10px 8px 10px;
    background: rgba(15, 23, 42, 0.65);
    border-bottom: 1px solid rgba(100, 116, 139, 0.35);
}
.ips-ad-doc-table-head span:nth-child(1) { flex: 1; min-width: 0; }
.ips-ad-doc-table-head span:nth-child(2) { width: 22%; text-align: center; }
.ips-ad-doc-table-head span:nth-child(3) { width: 18%; text-align: right; }
.ips-ad-doc-table .ips-ad-docs-row {
    margin-bottom: 0;
    border-radius: 0;
    border-left: none;
    border-right: none;
    border-top: none;
    border-bottom: 1px solid rgba(51, 65, 85, 0.35);
}
.ips-ad-doc-table .ips-ad-docs-row:last-child {
    border-bottom: none;
}
.ips-ad-docs-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 6px 8px;
    margin-bottom: 4px;
    border-radius: 6px;
    background: rgba(30, 41, 59, 0.45);
    border: 1px solid rgba(51, 65, 85, 0.42);
}
.ips-ad-docs-row .ips-ad-docs-name {
    flex: 1;
    min-width: 0;
    font-size: 0.9rem;
    font-weight: 500;
    color: #f1f5f9;
    word-break: break-word;
}
.ips-ad-docs-row .ips-ad-docs-meta {
    font-size: 11px;
    color: #94a3b8;
    white-space: nowrap;
}
</style>
"""

_ASSET_DETAIL_SECTIONS_CSS = """
<style>
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ad-section-primary) {
    background: rgba(15, 23, 42, 0.58) !important;
    border-color: rgba(71, 85, 105, 0.5) !important;
    border-radius: 10px !important;
    padding: 6px 8px 8px 8px !important;
    margin-bottom: 4px !important;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ad-section-primary) h5 {
    color: #e2e8f0 !important;
    border-bottom: 1px solid rgba(100, 116, 139, 0.35) !important;
    padding-bottom: 6px !important;
    margin-bottom: 6px !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ad-section-photos) {
    background: rgba(15, 23, 42, 0.55) !important;
    border-color: rgba(71, 85, 105, 0.5) !important;
    border-radius: 10px !important;
    padding: 6px 8px 8px 8px !important;
    margin-bottom: 6px !important;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ad-section-photos) h5 {
    color: #e2e8f0 !important;
    border-bottom: 1px solid rgba(100, 116, 139, 0.35) !important;
    padding-bottom: 4px !important;
    margin-bottom: 4px !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ad-section-docs) {
    background: rgba(15, 23, 42, 0.5) !important;
    border-color: rgba(71, 85, 105, 0.45) !important;
    border-radius: 10px !important;
    padding: 6px 8px 8px 8px !important;
    margin-bottom: 6px !important;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ad-section-docs) h5 {
    color: #e2e8f0 !important;
    border-bottom: 1px solid rgba(100, 116, 139, 0.35) !important;
    padding-bottom: 4px !important;
    margin-bottom: 4px !important;
}
/* Compact QR tool card (secondary; narrow width) */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ad-qr-tool) {
    max-width: 200px !important;
    background: rgba(15, 23, 42, 0.65) !important;
    border-color: rgba(71, 85, 105, 0.55) !important;
    border-radius: 8px !important;
    padding: 6px 8px 8px 8px !important;
    margin-top: 4px !important;
    margin-bottom: 0 !important;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ad-qr-tool) [data-testid="stImage"] {
    margin-bottom: 0.25rem !important;
}
</style>
"""

_IPS_AD_SECTIONS_CSS_KEY = "ips_ad_detail_sections_css_injected_v5"


def _inject_asset_detail_sections_css() -> None:
    if st.session_state.get(_IPS_AD_SECTIONS_CSS_KEY):
        return
    st.session_state[_IPS_AD_SECTIONS_CSS_KEY] = True
    st.markdown(_ASSET_DETAIL_SECTIONS_CSS, unsafe_allow_html=True)


def _disp(val) -> str:
    if val is None or val == "":
        return "—"
    return str(val)


def _rate_disp(val) -> str:
    """Format currency for rental rates; empty/zero-ish shows em dash."""
    if val is None or val == "":
        return "—"
    try:
        f = float(val)
    except (TypeError, ValueError):
        return "—"
    if f == 0.0:
        return "—"
    return f"${f:,.2f}"


def _job_name(jobs: list[dict], job_id) -> str:
    if not job_id:
        return "—"
    for j in jobs:
        if str(j.get("id")) == str(job_id):
            return job_row_select_label(j)
    return "—"


def _kv(label: str, value: str) -> None:
    st.markdown(f'<p class="ips-k">{label}</p><p class="ips-v">{value}</p>', unsafe_allow_html=True)


def _render_asset_detail_qr_block(asset: dict, aid: str, *, compact: bool) -> None:
    """QR downloads in a bordered card; width follows layout constants (compact = stacked/mobile)."""
    qr_text = qr_payload(asset)
    if not qr_text:
        return
    img_w = _QR_IMAGE_WIDTH_MOBILE if compact else _QR_IMAGE_WIDTH_DESKTOP
    with st.container(border=True):
        st.markdown(
            '<span class="ips-ad-qr-tool"></span>'
            '<p class="ips-ad-qr-label">Scan Asset QR</p>',
            unsafe_allow_html=True,
        )
        try:
            st.image(
                qr_png_bytes(qr_text),
                width=img_w,
                caption=None,
            )
        except Exception:
            st.caption(f"QR value: {qr_text} (image unavailable)")
        try:
            dl_bytes, dl_mime, dl_name = qr_label_for_download(asset, qr_text)
            st.download_button(
                "Download QR Label",
                data=dl_bytes,
                file_name=dl_name,
                mime=dl_mime,
                key=f"ad_qr_label_dl_{aid}",
                use_container_width=True,
            )
        except Exception:
            st.caption("Print label file could not be generated.")
        try:
            st.download_button(
                "Download 2x1 Sticker Label",
                data=qr_label_2x1_sticker_pdf_bytes(asset, qr_text),
                file_name=qr_label_2x1_sticker_download_filename(asset),
                mime="application/pdf",
                key=f"ad_qr_label_2x1_{aid}",
                use_container_width=True,
            )
        except Exception:
            st.caption("2x1 sticker PDF could not be generated.")


def _render_asset_title_quick_edit(
    asset: dict,
    aid: str,
    *,
    quick_edit: bool,
    qe_key: str,
    can_edit: bool,
    is_narrow: bool,
    centered: bool = True,
) -> None:
    """Asset name under hero image + optional quick-edit fields (name, category, rental flag)."""
    _hero_wrap = "ips-ad-meta-col ips-ad-hero-stack"
    if centered:
        _hero_wrap += " ips-ad-hero-centerblock"
    st.markdown(f'<div class="{_hero_wrap}">', unsafe_allow_html=True)
    if centered and not quick_edit:
        st.markdown(
            f'<p class="ips-hero-title" style="text-align:center;margin:0 0 6px 0;">'
            f"{html.escape(_disp(asset.get('asset_name')))}</p>",
            unsafe_allow_html=True,
        )
        _pe1, _pe2, _pe3 = st.columns([1, 1, 1])
        with _pe2:
            if can_edit:
                if st.button(
                    "✏️",
                    key=f"ad_qe_toggle_{aid}",
                    help="Quick edit: name, category, rent to customer",
                ):
                    st.session_state[qe_key] = not bool(st.session_state.get(qe_key, False))
                    st.rerun()
    elif centered and quick_edit:
        st.text_input(
            "Asset name",
            value=str(asset.get("asset_name") or ""),
            key=f"ad_qe_name_{aid}",
            label_visibility="collapsed",
            placeholder="Asset name",
        )
        _qe1, _qe2, _qe3 = st.columns([1, 1, 1])
        with _qe2:
            if can_edit:
                if st.button(
                    "✏️",
                    key=f"ad_qe_toggle_{aid}",
                    help="Quick edit: name, category, rent to customer",
                ):
                    st.session_state[qe_key] = not bool(st.session_state.get(qe_key, False))
                    st.rerun()
    else:
        title_left, title_right = st.columns([6.5, 1])
        with title_left:
            if quick_edit:
                st.text_input(
                    "Asset name",
                    value=str(asset.get("asset_name") or ""),
                    key=f"ad_qe_name_{aid}",
                    label_visibility="collapsed",
                    placeholder="Asset name",
                )
            else:
                st.markdown(
                    f'<p class="ips-hero-title">{html.escape(_disp(asset.get("asset_name")))}</p>',
                    unsafe_allow_html=True,
                )
        with title_right:
            if can_edit:
                if st.button(
                    "✏️",
                    key=f"ad_qe_toggle_{aid}",
                    help="Quick edit: name, category, rent to customer",
                ):
                    st.session_state[qe_key] = not bool(st.session_state.get(qe_key, False))
                    st.rerun()

    if quick_edit:
        if is_narrow:
            st.text_input("Category", value=str(asset.get("category") or ""), key=f"ad_qe_cat_{aid}")
            st.checkbox(
                "Rent to Customer",
                value=bool(asset.get("is_rental")),
                key=f"ad_qe_rent_{aid}",
            )
        else:
            _qe_c1, _qe_c2 = st.columns(2)
            with _qe_c1:
                st.text_input("Category", value=str(asset.get("category") or ""), key=f"ad_qe_cat_{aid}")
            with _qe_c2:
                st.checkbox(
                    "Rent to Customer",
                    value=bool(asset.get("is_rental")),
                    key=f"ad_qe_rent_{aid}",
                )
        if not is_narrow:
            _qe_sl, _qe_sr = st.columns([2, 1])
            with _qe_sr:
                qe_save_clicked = st.button(
                    "Save quick changes", type="primary", key=f"ad_qe_save_{aid}", use_container_width=True
                )
        else:
            qe_save_clicked = st.button(
                "Save quick changes", type="primary", key=f"ad_qe_save_{aid}", use_container_width=True
            )
        if qe_save_clicked:
            qn = str(st.session_state.get(f"ad_qe_name_{aid}", "")).strip()
            if not qn:
                st.error("Asset name is required.")
                st.stop()
            else:
                update_rows_admin(
                    "assets",
                    {
                        "asset_name": qn,
                        "category": str(st.session_state.get(f"ad_qe_cat_{aid}", "")).strip(),
                        "is_rental": bool(st.session_state.get(f"ad_qe_rent_{aid}", False)),
                    },
                    {"id": asset["id"]},
                )
                st.session_state["asset_detail_flash"] = "Quick changes saved."
                st.session_state[qe_key] = False
                st.rerun()
        st.caption("**Rental rates**, **uploads**, and **AI autofill** are available below while Quick Edit is active.")
    st.markdown("</div>", unsafe_allow_html=True)


def _render_asset_facts_panel(
    asset: dict,
    jobs: list[dict],
    *,
    quick_edit: bool,
) -> None:
    """Compact key facts (portal right column / stacked): brand, model, serial, ID, status + more + rental summary."""
    st.markdown('<div class="ips-ad-facts-panel">', unsafe_allow_html=True)
    st.markdown('<p class="ips-facts-head">Equipment details</p>', unsafe_allow_html=True)

    # Requested order: brand, model, serial, asset/tool id, status
    _kv("Brand / manufacturer", _disp(asset.get("manufacturer")))
    _kv("Model", _disp(asset.get("model")))
    _kv("Serial number", _disp(asset.get("serial_number")))
    _kv("Asset / tool ID", _disp(asset.get("asset_id")))
    _kv("Status", _disp(asset.get("status")))
    if bool(asset.get("is_checkout_item")):
        st.caption("Checkout tool — possession is logged on **Scan Inventory** (not consumable inventory).")
        _kv("Last checkout", _disp(asset.get("last_checkout_at")))
        _kv("Last check-in", _disp(asset.get("last_checkin_at")))

    if not quick_edit and str(asset.get("category") or "").strip():
        _kv("Category", _disp(asset.get("category")))
    if not quick_edit:
        if bool(asset.get("is_rental")):
            st.markdown(
                '<span class="ips-badge-rental">Rental · rent to customer</span>',
                unsafe_allow_html=True,
            )
        else:
            _kv("Rent to Customer", "No")

    with st.expander("More details", expanded=False):
        _kv("Location", _disp(asset.get("location")))
        _kv("Assigned job", _job_name(jobs, asset.get("assigned_job_id")))
        _kv("Assigned employee", _disp(asset.get("assigned_employee")))
        _kv("Condition", _disp(asset.get("condition")))
        _kv("Mileage", _disp(asset.get("mileage")))
        _kv("Hour meter", _disp(asset.get("hour_meter")))
        if str(asset.get("year") or "").strip():
            _kv("Year", _disp(asset.get("year")))

    if bool(asset.get("is_rental")):
        d = _rate_disp(asset.get("rental_daily_rate"))
        w = _rate_disp(asset.get("rental_weekly_rate"))
        m = _rate_disp(asset.get("rental_monthly_rate"))
        notes_rn = str(asset.get("rental_notes") or "").strip()
        notes_block = (
            f'<div class="ips-ad-rental-notes"><span class="k">Rental notes</span>{html.escape(notes_rn)}</div>'
            if notes_rn
            else ""
        )
        st.markdown(
            '<div class="ips-ad-rental-panel">'
            '<p class="ips-ad-rental-title">Rental rates</p>'
            '<div class="ips-ad-rental-grid">'
            "<div><span class=\"k\">Daily</span>" + d + "</div>"
            "<div><span class=\"k\">Weekly</span>" + w + "</div>"
            "<div><span class=\"k\">Monthly</span>" + m + "</div>"
            "</div>"
            + notes_block
            + "</div>",
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)


_IMAGE_SUFFIXES = frozenset({".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".heic"})


def _asset_file_kind(file_name: str) -> str:
    ext = Path(file_name).suffix.lower()
    if ext in _IMAGE_SUFFIXES:
        return "image"
    if ext == ".pdf":
        return "pdf"
    return "other"


def _split_asset_photos_rows(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Split ``asset_photos`` into images (gallery + primary) vs document-like files.

    Uses ``file_kind`` / ``content_type`` when present, else filename extension.
    """
    images: list[dict] = []
    docs: list[dict] = []
    for row in rows:
        fp = str(row.get("file_path") or "").strip()
        fn = str(row.get("file_name") or "").strip() or Path(fp).name or "file"
        fk = str(row.get("file_kind") or "").strip().lower()
        ct = str(row.get("content_type") or "").strip().lower()
        if fk in ("document", "manual", "pdf"):
            docs.append(row)
            continue
        if fk in ("photo", "image", "overview", "thumbnail", "gallery"):
            images.append(row)
            continue
        if ct.startswith("image/"):
            images.append(row)
            continue
        if ct == "application/pdf" or "pdf" in ct:
            docs.append(row)
            continue
        if _asset_file_kind(fn) == "image":
            images.append(row)
        else:
            docs.append(row)
    return images, docs


def _merge_asset_document_rows(asset_documents: list[dict], from_asset_photos: list[dict]) -> list[dict]:
    """Combine registered documents with non-image rows still stored on ``asset_photos``."""
    out: list[dict] = []
    for d in asset_documents:
        x = dict(d)
        x["_doc_source"] = "asset_documents"
        out.append(x)
    for p in from_asset_photos:
        x = dict(p)
        x["_doc_source"] = "asset_photos"
        if not str(x.get("document_type") or "").strip():
            pt = str(x.get("photo_type") or "").strip()
            x["document_type"] = pt or "Equipment upload"
        out.append(x)
    out.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)
    return out


def _render_asset_documents_list(
    documents: list,
    *,
    key_prefix: str = "ad_doc",
    show_hint: bool = True,
    mobile_layout: bool = False,
) -> None:
    """Table-style rows: name, type, Manual/Open (signed URL or local file URI — same behavior as before)."""
    if not documents:
        st.caption("No documents uploaded yet.")
        return
    if show_hint:
        st.caption("Signed links expire after about one hour — use **Open** / **Manual** again if needed.")

    for i, doc in enumerate(documents):
        fp = str(doc.get("file_path") or "").strip()
        fn = str(doc.get("file_name") or "").strip() or Path(fp).name or "document"
        ref = create_signed_url(fp, expires_in=3600) if fp else ""
        is_pdf = ".pdf" in fn.lower()
        label = "Manual" if is_pdf else "Open"

        dtype = str(doc.get("document_type") or doc.get("photo_type") or "").strip() or "—"

        open_url: str | None = None
        if ref:
            if ref.startswith("http://") or ref.startswith("https://"):
                open_url = ref
            else:
                p = Path(ref)
                if p.is_file():
                    open_url = str(p.resolve().as_uri())

        if mobile_layout:
            st.markdown(
                f'<div class="ips-ad-docs-row">'
                f'<div class="ips-ad-docs-name">{html.escape(fn[:120] + ("…" if len(fn) > 120 else ""))}</div>'
                f'<div class="ips-ad-docs-meta">{html.escape(dtype[:32])}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )
            bcol1, bcol2 = st.columns(2)
            with bcol1:
                if open_url:
                    st.link_button(label, url=open_url, use_container_width=True, key=f"{key_prefix}_{i}_open")
                elif ref:
                    st.caption("Missing file")
                else:
                    st.caption("Unavailable")
        else:
            if i == 0:
                st.markdown(
                    '<div class="ips-ad-doc-table">'
                    '<div class="ips-ad-doc-table-head">'
                    "<span>Document</span><span>Type</span><span>Action</span>"
                    "</div>",
                    unsafe_allow_html=True,
                )
            c1, c2, c3 = st.columns([3.4, 1.15, 1.0])
            with c1:
                st.markdown(
                    f'<p style="margin:0;font-size:0.9rem;color:#f1f5f9;font-weight:500;">'
                    f"{html.escape(fn[:140] + ('…' if len(fn) > 140 else ''))}</p>",
                    unsafe_allow_html=True,
                )
            with c2:
                st.markdown(
                    f'<p style="margin:0;text-align:center;font-size:0.8rem;color:#94a3b8;">'
                    f"{html.escape(dtype[:36] + ('…' if len(dtype) > 36 else ''))}</p>",
                    unsafe_allow_html=True,
                )
            with c3:
                if open_url:
                    st.link_button(label, url=open_url, use_container_width=True, key=f"{key_prefix}_{i}_open")
                elif ref:
                    st.caption("Missing")
                else:
                    st.caption("—")
    if documents and not mobile_layout:
        st.markdown("</div>", unsafe_allow_html=True)


_GALLERY_PREVIEW_QP = "ips_gpv"

_ASSET_EXPENSE_TYPES = ("Repair", "Maintenance", "Parts", "Fuel", "Inspection", "Registration", "Other")
_KIT_FREQ_MONTH_DAYS = 31


def _money(v) -> str:
    try:
        if v is None or str(v).strip() == "":
            return "—"
        return f"${float(v):,.2f}"
    except (TypeError, ValueError):
        return "—"


def _as_float(v, default: float = 0.0) -> float:
    try:
        if v is None or str(v).strip() == "":
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def _as_int(v, default: int = 0) -> int:
    try:
        if v is None or str(v).strip() == "":
            return default
        return int(v)
    except (TypeError, ValueError):
        return default


def _is_tool_trailer(asset_row: dict) -> bool:
    return str(asset_row.get("asset_type") or "").strip().lower() == "tool trailer"


def _safe_fetch_by_match(table: str, match: dict, *, limit: int = 500) -> list[dict]:
    """Fetch rows; return [] when the table doesn't exist yet (migration not applied)."""
    try:
        return fetch_by_match(table, match, limit=limit)  # type: ignore[name-defined]
    except Exception:
        try:
            return fetch_by_match_admin(table, match, limit=limit)  # type: ignore[name-defined]
        except Exception:
            return []


def _todo_like_job_label(jobs: list[dict], job_id: str | None) -> str:
    if not job_id:
        return "—"
    for j in jobs or []:
        if str(j.get("id") or "").strip() == str(job_id).strip():
            return str(j.get("job_name") or "").strip() or "—"
    return "—"


def _render_asset_expenses(
    *,
    asset_row: dict,
    expenses: list[dict],
    can_edit: bool,
    profiles: list[dict],
) -> None:
    aid = str(asset_row.get("id") or "").strip()
    if not aid:
        st.caption("—")
        return

    # Totals
    total_repair = sum(_as_float(r.get("amount")) for r in expenses if str(r.get("expense_type")) == "Repair")
    total_maint = sum(_as_float(r.get("amount")) for r in expenses if str(r.get("expense_type")) == "Maintenance")
    lifetime = sum(_as_float(r.get("amount")) for r in expenses)

    c1, c2, c3 = st.columns(3, gap="small")
    c1.metric("Total repair", _money(total_repair))
    c2.metric("Total maintenance", _money(total_maint))
    c3.metric("Lifetime expense", _money(lifetime))

    if can_edit:
        with st.expander("Add repair / expense", expanded=False):
            et = st.selectbox("Expense type", list(_ASSET_EXPENSE_TYPES), key=f"ae_type_{aid}")
            ed = st.date_input("Expense date", value=None, key=f"ae_date_{aid}")
            vendor = st.text_input("Vendor", key=f"ae_vendor_{aid}")
            desc = st.text_input("Description", key=f"ae_desc_{aid}")
            amt = st.number_input("Amount", min_value=0.0, value=0.0, step=0.01, format="%.2f", key=f"ae_amt_{aid}")
            odo = st.number_input(
                "Odometer / hours (optional)",
                min_value=0.0,
                value=0.0,
                step=1.0,
                format="%.2f",
                key=f"ae_odo_{aid}",
            )
            notes = st.text_area("Notes", height=72, key=f"ae_notes_{aid}")
            # Receipt upload stored as an Asset Document; expense row keeps the file path in receipt_url.
            up = st.file_uploader(
                "Receipt (optional)",
                accept_multiple_files=False,
                key=f"ae_receipt_{aid}",
                type=["pdf", "png", "jpg", "jpeg"],
            )
            receipt_path = ""
            if st.button("Save expense", type="primary", use_container_width=True, key=f"ae_save_{aid}"):
                if up:
                    try:
                        doc = persist_asset_document_upload(
                            asset_row=asset_row,
                            uploaded=up,
                            document_type="Receipt",
                            expiration_date=None,
                            notes=f"Receipt for {et}: {desc}".strip(),
                            uploaded_by=current_profile().get("id"),
                        )
                        receipt_path = str((doc or {}).get("file_path") or "").strip()
                    except Exception as exc:
                        st.error(f"Receipt upload failed: {exc}")
                        receipt_path = ""
                payload = {
                    "asset_id": aid,
                    "expense_type": str(et or "Other"),
                    "expense_date": ed.isoformat() if ed else datetime.utcnow().date().isoformat(),
                    "vendor": str(vendor or "").strip(),
                    "description": str(desc or "").strip(),
                    "amount": float(amt or 0),
                    "receipt_url": receipt_path,
                    "odometer_hours": float(odo) if float(odo or 0) > 0 else None,
                    "created_by": str(current_profile().get("id") or "").strip() or None,
                    "notes": str(notes or "").strip(),
                }
                try:
                    insert_row_admin("asset_expenses", payload)  # type: ignore[name-defined]
                except Exception:
                    # fall back to RLS client when admin key missing
                    try:
                        from app.db import insert_row
                    except ImportError:
                        from db import insert_row  # type: ignore
                    insert_row("asset_expenses", payload)  # type: ignore
                st.success("Expense saved.")
                st.rerun()

    if not expenses:
        st.caption("No expenses recorded.")
        return

    show = pd.DataFrame(expenses).copy()
    for drop in ("asset_id",):
        if drop in show.columns:
            show = show.drop(columns=[drop], errors="ignore")
    st.dataframe(show, use_container_width=True, hide_index=True)


def _render_tool_trailer_kit(
    *,
    asset_row: dict,
    kits: list[dict],
    kit_items: list[dict],
    replacements: list[dict],
    jobs: list[dict],
    can_edit: bool,
) -> None:
    aid = str(asset_row.get("id") or "").strip()
    if not aid:
        return

    active_kits = [k for k in (kits or []) if bool((k or {}).get("is_active", True))]
    active_items = [r for r in kit_items if bool((r or {}).get("is_active", True))]
    total_small_tool_value = sum(_as_float(r.get("total_value")) for r in active_items)

    # Replacement summaries (31 days + lifetime totals)
    now = datetime.utcnow().date()
    repl_this_month = 0
    repl_cost_month = 0.0
    repl_cost_life = 0.0
    for r in replacements or []:
        tc = _as_float(r.get("total_cost"))
        repl_cost_life += tc
        try:
            ds = str(r.get("replacement_date") or "").strip()
            if ds and (now - datetime.fromisoformat(ds).date()).days <= _KIT_FREQ_MONTH_DAYS:
                repl_this_month += 1
                repl_cost_month += tc
        except Exception:
            pass

    # Most replaced item (by replacement_count, then replacement_cost)
    most = None
    if active_items:
        most = sorted(
            active_items,
            key=lambda r: (-_as_int(r.get("replacement_count")), -_as_float(r.get("replacement_cost"))),
        )[0]
    most_name = str((most or {}).get("item_name") or "").strip() or "—"

    c1, c2, c3, c4 = st.columns(4, gap="small")
    c1.metric("Number of kits", len(active_kits))
    c2.metric("Total small tool value", _money(total_small_tool_value))
    c3.metric("Replacement cost (31d)", _money(repl_cost_month))
    c4.metric("Most replaced item", most_name)

    # Kit selection + CRUD
    kit_options: list[tuple[str, str]] = []
    for k in active_kits:
        kid = str(k.get("id") or "").strip()
        if not kid:
            continue
        nm = str(k.get("kit_name") or "").strip() or "Kit"
        kit_options.append((kid, nm))
    kit_options.sort(key=lambda x: x[1].lower())
    kit_labels = ["All kits"] + [nm for _, nm in kit_options]
    kit_ids_by_label = {nm: kid for kid, nm in kit_options}
    kit_pick = st.selectbox("Tool Kits", kit_labels, key=f"tk_pick_{aid}")
    selected_kit_id = kit_ids_by_label.get(kit_pick) if kit_pick and kit_pick != "All kits" else None

    if can_edit:
        with st.expander("Add kit", expanded=False):
            kn = st.text_input("Kit name", key=f"tk_add_name_{aid}")
            kd = st.text_area("Description", height=72, key=f"tk_add_desc_{aid}")
            if st.button("Save kit", type="primary", use_container_width=True, key=f"tk_add_go_{aid}"):
                t = str(kn or "").strip()
                if not t:
                    st.error("Kit name is required.")
                    st.stop()
                payload = {
                    "asset_id": aid,
                    "kit_name": t,
                    "description": str(kd or "").strip(),
                    "created_by": str(current_profile().get("id") or "").strip() or None,
                    "is_active": True,
                }
                try:
                    insert_row_admin("asset_kits", payload)  # type: ignore[name-defined]
                except Exception as exc:
                    st.error(f"Could not save kit: {exc} — run **`sql/040_asset_kits.sql`**.")
                    st.stop()
                st.success("Kit saved.")
                st.rerun()

    if can_edit:
        with st.expander("Add item to kit", expanded=False):
            if not active_kits:
                st.info("Add a kit first.")
                st.stop()
            add_labels = [nm for _, nm in kit_options]
            default_label = kit_pick if kit_pick in add_labels else (add_labels[0] if add_labels else "")
            add_kit_label = st.selectbox("Kit", add_labels, index=add_labels.index(default_label) if default_label in add_labels else 0, key=f"kit_add_pick_{aid}")
            add_kit_id = kit_ids_by_label.get(add_kit_label)
            nm = st.text_input("Item name", key=f"kit_add_name_{aid}")
            cat = st.text_input("Category", key=f"kit_add_cat_{aid}")
            c1, c2, c3 = st.columns(3, gap="small")
            qty = c1.number_input("Qty", min_value=0.0, value=1.0, step=1.0, format="%.2f", key=f"kit_add_qty_{aid}")
            uv = c2.number_input(
                "Unit value", min_value=0.0, value=0.0, step=0.5, format="%.2f", key=f"kit_add_uv_{aid}"
            )
            rc = c3.number_input(
                "Replacement cost", min_value=0.0, value=0.0, step=0.5, format="%.2f", key=f"kit_add_rc_{aid}"
            )
            exp_days = st.number_input(
                "Expected life (days, optional)", min_value=0, value=0, step=1, key=f"kit_add_life_{aid}"
            )
            inv_link = st.text_input(
                "Inventory item id (optional)",
                key=f"kit_add_inv_{aid}",
                help="Optional link to inventory_items.id for replacements from stock.",
            )
            qr_val = st.text_input("QR code value (optional)", key=f"kit_add_qr_{aid}")
            notes = st.text_area("Notes", height=72, key=f"kit_add_notes_{aid}")
            if st.button("Save kit item", type="primary", use_container_width=True, key=f"kit_add_save_{aid}"):
                t = str(nm or "").strip()
                if not t:
                    st.error("Item name is required.")
                    st.stop()
                payload = {
                    "parent_asset_id": aid,
                    "kit_id": add_kit_id,
                    "item_name": t,
                    "category": str(cat or "").strip(),
                    "quantity": float(qty or 0),
                    "unit_value": float(uv or 0),
                    "replacement_cost": float(rc or 0),
                    "quantity_on_hand": float(qty or 0),
                    "missing_count": 0.0,
                    "expected_life_days": int(exp_days) if int(exp_days or 0) > 0 else None,
                    "inventory_item_id": str(inv_link or "").strip() or None,
                    "qr_code_value": str(qr_val or "").strip(),
                    "is_active": True,
                    "notes": str(notes or "").strip(),
                }
                try:
                    insert_row_admin("asset_kit_items", payload)  # type: ignore[name-defined]
                except Exception as exc:
                    low = str(exc).lower()
                    if "kit_id" in low and "column" in low:
                        st.warning("Kit linking not enabled yet — run **`sql/041_asset_kit_items_kits.sql`**.")
                        payload.pop("kit_id", None)
                        insert_row_admin("asset_kit_items", payload)  # type: ignore[name-defined]
                    elif ("quantity_on_hand" in low or "missing_count" in low) and "column" in low:
                        payload.pop("quantity_on_hand", None)
                        payload.pop("missing_count", None)
                        insert_row_admin("asset_kit_items", payload)  # type: ignore[name-defined]
                    else:
                        raise
                except Exception:
                    try:
                        from app.db import insert_row
                    except ImportError:
                        from db import insert_row  # type: ignore
                    insert_row("asset_kit_items", payload)  # type: ignore
                st.success("Kit item saved.")
                st.rerun()

    if not kit_items:
        st.caption("No kit items yet.")
        return

    # Filter view by selected kit when kit_id is available.
    if selected_kit_id:
        kit_items = [r for r in kit_items if str((r or {}).get("kit_id") or "").strip() == str(selected_kit_id)]

    # Quick insights
    by_repl = sorted(active, key=lambda r: (-_as_int(r.get("replacement_count")), -_as_float(r.get("replacement_cost"))))
    top = by_repl[:5]
    if top:
        st.markdown("###### Frequently replaced")
        st.caption("Highest replacement count, then highest replacement cost.")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Item": str(r.get("item_name") or ""),
                        "Count": _as_int(r.get("replacement_count")),
                        "Replacement cost": _money(r.get("replacement_cost")),
                        "Last replaced": str(r.get("last_replaced_at") or "—"),
                    }
                    for r in top
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("###### Kit items")
    for it in kit_items:
        kid = str(it.get("id") or "").strip()
        if not kid:
            continue
        nm = str(it.get("item_name") or "").strip() or "—"
        qty = _as_float(it.get("quantity"), 0)
        uv = _as_float(it.get("unit_value"), 0)
        tv = _as_float(it.get("total_value"), qty * uv)
        rc = _as_float(it.get("replacement_cost"), 0)
        lr = str(it.get("last_replaced_at") or "").strip() or "—"
        cnt = _as_int(it.get("replacement_count"), 0)
        active_flag = bool(it.get("is_active", True))

        with st.container(border=True):
            h1, h2, h3, h4, h5, h6, h7, h8 = st.columns([2.6, 0.9, 1.1, 1.15, 1.05, 1.2, 1.3, 1.2], gap="small")
            h1.markdown(f"**{html.escape(nm)}**")
            h2.caption(f"Qty: {qty:g}")
            h3.caption(f"Unit: {_money(uv)}")
            h4.caption(f"Total: {_money(tv)}")
            h5.caption(f"Repl: {_money(rc)}")
            h6.caption(f"Last: {lr}")
            h7.caption(f"Count: {cnt}")
            h8.caption("Active" if active_flag else "Inactive")

            if not can_edit:
                continue

            with st.expander("Replace / edit", expanded=False):
                r1, r2, r3 = st.columns(3, gap="small")
                rdate = r1.date_input("Replacement date", value=None, key=f"kit_r_date_{kid}")
                rqty = r2.number_input(
                    "Qty replaced", min_value=0.0, value=1.0, step=1.0, format="%.2f", key=f"kit_r_qty_{kid}"
                )
                ruc = r3.number_input(
                    "Unit cost", min_value=0.0, value=float(rc), step=0.5, format="%.2f", key=f"kit_r_uc_{kid}"
                )
                reason = st.text_input("Reason", key=f"kit_r_reason_{kid}")
                job_names = ["— No job —"] + [str(j.get("job_name") or "").strip() for j in jobs if str(j.get("job_name") or "").strip()]
                job_pick = st.selectbox("Job (optional)", job_names, key=f"kit_r_job_{kid}")
                job_id = None
                if job_pick and not job_pick.startswith("—"):
                    for j in jobs:
                        if str(j.get("job_name") or "").strip() == job_pick:
                            job_id = str(j.get("id") or "").strip() or None
                            break
                notes = st.text_area("Notes", height=72, key=f"kit_r_notes_{kid}")
                from_inventory = st.checkbox(
                    "Deduct from linked inventory item (if set)",
                    value=True,
                    key=f"kit_r_from_inv_{kid}",
                    help="If this kit item has inventory_item_id, deduct qty and write an inventory_transactions row.",
                )
                if st.button("Record replacement", type="primary", use_container_width=True, key=f"kit_r_go_{kid}"):
                    q = float(rqty or 0)
                    if q <= 0:
                        st.error("Qty replaced must be greater than zero.")
                        st.stop()
                    u = float(ruc or 0)
                    # Optional inventory deduction
                    inv_id = str(it.get("inventory_item_id") or "").strip()
                    if from_inventory and inv_id:
                        inv = fetch_one("inventory_items", {"id": inv_id})
                        if inv:
                            qoh = _as_float(inv.get("quantity_on_hand"), 0)
                            update_rows_admin("inventory_items", {"quantity_on_hand": qoh - q}, {"id": inv_id})
                            insert_row_admin(
                                "inventory_transactions",
                                {
                                    "inventory_item_id": inv_id,
                                    "qty": -q,
                                    "txn_type": "KIT_REPLACEMENT",
                                    "job_id": job_id,
                                    "profile_id": str(current_profile().get("id") or "").strip() or None,
                                    "notes": f"Kit replacement for trailer {asset_row.get('asset_id')}: {nm}".strip(),
                                },
                            )
                    # Replacement history
                    rep_payload = {
                        "parent_asset_id": aid,
                        "kit_item_id": kid,
                        "replacement_date": rdate.isoformat() if rdate else datetime.utcnow().date().isoformat(),
                        "quantity_replaced": q,
                        "unit_cost": u,
                        "reason": str(reason or "").strip(),
                        "replaced_by": str(current_profile().get("id") or "").strip() or None,
                        "job_id": job_id,
                        "notes": str(notes or "").strip(),
                    }
                    try:
                        insert_row_admin("asset_kit_replacements", rep_payload)  # type: ignore[name-defined]
                    except Exception:
                        try:
                            from app.db import insert_row
                        except ImportError:
                            from db import insert_row  # type: ignore
                        insert_row("asset_kit_replacements", rep_payload)  # type: ignore
                    # Update kit item counters
                    update_rows_admin(
                        "asset_kit_items",
                        {
                            "replacement_count": cnt + 1,
                            "last_replaced_at": rep_payload["replacement_date"],
                            "replacement_cost": u,
                        },
                        {"id": kid},
                    )
                    st.success("Replacement recorded.")
                    st.rerun()

                st.markdown("-----")
                enm = st.text_input("Item name", value=nm, key=f"kit_e_name_{kid}")
                ecat = st.text_input("Category", value=str(it.get("category") or ""), key=f"kit_e_cat_{kid}")
                ec1, ec2, ec3 = st.columns(3, gap="small")
                eqty = ec1.number_input("Qty", min_value=0.0, value=float(qty), step=1.0, format="%.2f", key=f"kit_e_qty_{kid}")
                euv = ec2.number_input("Unit value", min_value=0.0, value=float(uv), step=0.5, format="%.2f", key=f"kit_e_uv_{kid}")
                erc = ec3.number_input("Replacement cost", min_value=0.0, value=float(rc), step=0.5, format="%.2f", key=f"kit_e_rc_{kid}")
                eactive = st.checkbox("Active", value=active_flag, key=f"kit_e_active_{kid}")
                enotes = st.text_area("Notes", value=str(it.get("notes") or ""), height=72, key=f"kit_e_notes_{kid}")
                b1, b2 = st.columns(2, gap="small")
                with b1:
                    if st.button("Save item", type="secondary", use_container_width=True, key=f"kit_e_save_{kid}"):
                        update_rows_admin(
                            "asset_kit_items",
                            {
                                "item_name": str(enm or "").strip() or nm,
                                "category": str(ecat or "").strip(),
                                "quantity": float(eqty or 0),
                                "unit_value": float(euv or 0),
                                "replacement_cost": float(erc or 0),
                                "is_active": bool(eactive),
                                "notes": str(enotes or "").strip(),
                            },
                            {"id": kid},
                        )
                        st.success("Saved.")
                        st.rerun()
                with b2:
                    if st.button("Delete item", type="secondary", use_container_width=True, key=f"kit_e_del_{kid}"):
                        delete_asset_and_related  # keep linter quiet about imported symbol in file scope
                        try:
                            from app.db import delete_rows_admin as _del_admin
                        except ImportError:
                            from db import delete_rows_admin as _del_admin  # type: ignore
                        _del_admin("asset_kit_items", {"id": kid})
                        st.success("Deleted.")
                        st.rerun()


def _render_tool_trailer_replacement_history(*, replacements: list[dict], jobs: list[dict]) -> None:
    if not replacements:
        st.caption("No replacements recorded.")
        return
    show = []
    for r in replacements:
        show.append(
            {
                "Date": str(r.get("replacement_date") or "—"),
                "Kit item id": str(r.get("kit_item_id") or "")[:8] + "…",
                "Qty": _as_float(r.get("quantity_replaced"), 0),
                "Unit cost": _money(r.get("unit_cost")),
                "Total": _money(r.get("total_cost")),
                "Job": _todo_like_job_label(jobs, str(r.get("job_id") or "") or None),
                "Reason": str(r.get("reason") or "").strip(),
                "Notes": str(r.get("notes") or "").strip(),
            }
        )
    st.dataframe(pd.DataFrame(show), use_container_width=True, hide_index=True)


def _clear_legacy_gallery_state(aid: str) -> None:
    """Clear stale thumbnail-gallery preview/session state (gallery UI removed)."""
    st.session_state.pop(f"asset_gallery_preview_{aid}", None)
    st.query_params.pop(_GALLERY_PREVIEW_QP, None)


def _pending_delete_session_key(aid: str) -> str:
    return f"asset_photo_delete_pending_{aid}"


def _back_to_asset_list(*, aid: str | None) -> None:
    """Clear asset-detail state and navigate back to Asset Database list."""
    if aid:
        _clear_legacy_gallery_state(str(aid))
        st.session_state.pop(_pending_delete_session_key(str(aid)), None)
        st.session_state.pop(f"del_confirm_{aid}", None)
        st.session_state.pop(f"ad_quick_edit_{aid}", None)

    st.session_state.pop("asset_detail_id", None)
    st.session_state.pop("asset_edit_id", None)
    st.session_state.pop("assets_view", None)
    st.session_state["asset_view_mode"] = "list"
    st.session_state["selected_asset_id"] = None
    st.session_state.pop("asset_return_to", None)
    st.session_state.pop("asset_detail_action", None)

    # Ensure we don't rely on a second click for rerun/nav.
    st.session_state.pop("_asset_detail_do_nav_rerun", None)
    st.session_state[IPS_NAV_PENDING_KEY] = "Asset Database"
    st.rerun()


def render() -> None:
    render_header("Asset Detail")
    inject_asset_workflow_mobile_css()
    ensure_narrow_viewport_detected()
    flash = st.session_state.pop("asset_detail_flash", None)
    if flash:
        st.success(flash)
    st.caption("Equipment portal — photo, details, and history")

    st.markdown(_PROFILE_CARD_CSS, unsafe_allow_html=True)
    _inject_asset_detail_sections_css()

    can_edit = current_role() in {"admin", "pm"}

    assets_all = fetch_table("assets", limit=5000, order_by="asset_name")
    if not assets_all:
        st.info("No assets found.")
        return

    if not st.session_state.get("asset_detail_id"):
        labels = {f"{a.get('asset_id')} — {a.get('asset_name')}": a.get("id") for a in assets_all}
        pick = st.selectbox("Select an asset", list(labels.keys()), key="asset_detail_pick_fallback")
        if st.button("Load profile", key="asset_detail_load_fallback", use_container_width=True):
            st.session_state["asset_detail_id"] = labels[pick]
        if not st.session_state.get("asset_detail_id"):
            st.stop()

    aid = st.session_state.get("asset_detail_id")
    asset = fetch_one("assets", {"id": aid})
    if not asset:
        st.warning("Asset not found. Choose another from Asset Database.")
        st.session_state.pop("asset_detail_id", None)
        st.stop()

    is_narrow = bool(st.session_state.get(IPS_VIEWPORT_NARROW_KEY, False))

    qe_key = f"ad_quick_edit_{aid}"
    # In-page edit mode (✏️): rental form, uploads, AI. Full-form edit uses ``asset_view_mode`` / ``selected_asset_id`` on Asset Manager, not this page.
    quick_edit = can_edit and bool(st.session_state.get(qe_key, False))

    jobs = fetch_table("jobs", limit=5000, order_by="job_number")
    job_options: dict[str, str | None] = {"": None}
    for j in jobs:
        name = str(j.get("job_name", "")).strip()
        if name:
            job_options[name] = j.get("id")

    documents = fetch_by_match_admin("asset_documents", {"asset_id": asset["id"]}, limit=500)
    maintenance = fetch_by_match("asset_maintenance", {"asset_id": asset["id"]}, limit=500)
    assignments = fetch_by_match("asset_assignments", {"asset_id": asset["id"]}, limit=500)
    inspections = fetch_by_match("asset_inspections", {"asset_id": asset["id"]}, limit=500)

    # Optional modules (migrations may not be applied yet)
    asset_expenses = _safe_fetch_by_match("asset_expenses", {"asset_id": asset["id"]}, limit=1000)
    kits = _safe_fetch_by_match("asset_kits", {"asset_id": asset["id"]}, limit=2000)
    kit_items = _safe_fetch_by_match("asset_kit_items", {"parent_asset_id": asset["id"]}, limit=2000)
    kit_replacements = _safe_fetch_by_match("asset_kit_replacements", {"parent_asset_id": asset["id"]}, limit=5000)

    documents.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)
    maintenance.sort(key=lambda r: str(r.get("service_date") or ""), reverse=True)
    assignments.sort(key=lambda r: str(r.get("created_at") or r.get("check_out_at") or ""), reverse=True)
    inspections.sort(key=lambda r: str(r.get("inspection_date") or ""), reverse=True)
    asset_expenses.sort(key=lambda r: str(r.get("expense_date") or r.get("created_at") or ""), reverse=True)
    kits.sort(key=lambda r: str(r.get("kit_name") or ""), reverse=False)
    kit_items.sort(key=lambda r: str(r.get("created_at") or ""), reverse=False)
    kit_replacements.sort(key=lambda r: str(r.get("replacement_date") or r.get("created_at") or ""), reverse=True)

    asset_photos = fetch_by_match("asset_photos", {"asset_id": asset["id"]}, limit=500)
    asset_photos.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)
    photo_rows, doc_rows_from_photos = _split_asset_photos_rows(asset_photos)
    merged_documents = _merge_asset_document_rows(documents, doc_rows_from_photos)

    photo_path = str(asset.get("photo_path") or "").strip()
    signed = ""
    if photo_path:
        signed = create_signed_url(photo_path, expires_in=3600)

    _hero_w = _PRIMARY_IMAGE_WIDTH_MOBILE if is_narrow else _PRIMARY_IMAGE_WIDTH_DESKTOP

    # --- Portal top bar (light header + navigation) ---
    st.markdown('<span class="ips-ad-detail-top-actions"></span>', unsafe_allow_html=True)
    _pt1, _pt2, _pt3 = st.columns([1.05, 2.4, 1.1])
    with _pt1:
        if st.button("← Back", key="ad_portal_back_top"):
            _back_to_asset_list(aid=str(aid))
    with _pt2:
        st.markdown(
            '<div class="ips-ad-portal-top">'
            '<p class="ips-ad-portal-kicker">Equipment</p>'
            f'<p class="ips-ad-portal-title">{html.escape(_disp(asset.get("asset_name")))} · '
            f'<span style="color:#94a3b8;font-weight:500;">{html.escape(_disp(asset.get("asset_id")))}</span></p>'
            "</div>",
            unsafe_allow_html=True,
        )
    with _pt3:
        if can_edit:
            if st.button("Edit Asset", key="edit_asset_btn", type="primary", use_container_width=True):
                st.session_state["asset_view_mode"] = "edit"
                st.session_state["selected_asset_id"] = str(asset["id"])
                st.session_state["asset_return_to"] = "asset_detail"
                st.session_state.pop("assets_view", None)
                st.session_state.pop("asset_edit_id", None)
                st.session_state[IPS_NAV_PENDING_KEY] = "Asset Manager"
                st.rerun()

    if quick_edit:
        st.markdown(
            '<div class="ips-ad-edit-mode-banner" role="status">Editing Asset</div>',
            unsafe_allow_html=True,
        )

    # --- Hero: large image + title + compact facts / QR ---
    with st.container(border=True):
        st.markdown('<span class="ips-ad-section-primary"></span>', unsafe_allow_html=True)
        st.markdown('<span class="ips-ad-portal-hero"></span>', unsafe_allow_html=True)
        if is_narrow:
            if signed:
                try:
                    st.image(signed, width=_hero_w)
                except Exception as exc:
                    st.warning(f"Could not load primary image: {exc}")
            else:
                st.caption(
                    "No primary image. Add files in **Photos & files** below while **Quick Edit** (✏️) is on."
                )
            _render_asset_title_quick_edit(
                asset,
                str(aid),
                quick_edit=quick_edit,
                qe_key=qe_key,
                can_edit=can_edit,
                is_narrow=True,
                centered=True,
            )
            _render_asset_facts_panel(asset, jobs, quick_edit=quick_edit)
            _render_asset_detail_qr_block(asset, str(aid), compact=True)
        else:
            # Left: dominant primary photo + title; right: equipment details + compact QR
            _h_left, _h_right = st.columns([1.9, 1.0], gap="small")
            with _h_left:
                if signed:
                    try:
                        st.image(signed, width=_hero_w)
                    except Exception as exc:
                        st.warning(f"Could not load primary image: {exc}")
                else:
                    st.caption(
                        "No primary image. Add files in **Photos & files** below while **Quick Edit** (✏️) is on."
                    )
                _render_asset_title_quick_edit(
                    asset,
                    str(aid),
                    quick_edit=quick_edit,
                    qe_key=qe_key,
                    can_edit=can_edit,
                    is_narrow=False,
                    centered=False,
                )
            with _h_right:
                _render_asset_facts_panel(asset, jobs, quick_edit=quick_edit)
                _render_asset_detail_qr_block(asset, str(aid), compact=False)

    # --- Field actions (always for editors) + edit-only actions (Quick Edit on) ---
    if can_edit:
        st.markdown('<div class="ips-ad-actions-hero"></div>', unsafe_allow_html=True)
        st.markdown("##### Field actions")
        st.markdown(
            '<div class="ips-ad-actions-primary ips-ad-actions-service ips-ad-dash-actions">',
            unsafe_allow_html=True,
        )
        _ac = st.columns(5)
        with _ac[0]:
            if st.button("Check out", key=f"ad_co_{aid}", use_container_width=True):
                st.session_state["asset_detail_action"] = "checkout"
        with _ac[1]:
            if st.button("Check in", key=f"ad_ci_{aid}", use_container_width=True):
                st.session_state["asset_detail_action"] = "checkin"
        with _ac[2]:
            if st.button("Report broken", key=f"ad_rb_{aid}", use_container_width=True):
                st.session_state["asset_detail_action"] = "broken"
        with _ac[3]:
            if st.button("Add maintenance", key=f"ad_maint_{aid}", use_container_width=True):
                st.session_state["asset_detail_action"] = "maint"
        with _ac[4]:
            if st.button("Add inspection", key=f"ad_insp_{aid}", use_container_width=True):
                st.session_state["asset_detail_action"] = "insp"
        st.markdown("</div>", unsafe_allow_html=True)

        if quick_edit:
            st.caption("While **Quick Edit** is on: upload documents or remove this asset.")
            if current_role() == "admin":
                ed1, ed2 = st.columns(2, gap="small")
                with ed1:
                    if st.button("Upload document", key=f"ad_doc_{aid}", use_container_width=True):
                        st.session_state["asset_detail_action"] = "doc"
                with ed2:
                    if st.button("Delete asset", key=f"ad_del_{aid}", use_container_width=True):
                        st.session_state["asset_detail_action"] = "delete"
            else:
                if st.button("Upload document", key=f"ad_doc_{aid}", use_container_width=True):
                    st.session_state["asset_detail_action"] = "doc"

    detail_photos = None
    upload_photos_clicked = False

    # --- Photos & files (compact upload; thumbnail gallery removed) ---
    with st.container(border=True):
        st.markdown('<span class="ips-ad-section-photos"></span>', unsafe_allow_html=True)
        st.markdown("##### Photos & files")
        if can_edit and quick_edit:
            st.caption("Add images or PDFs. PDFs are also listed under **Documents**.")
            detail_photos = st.file_uploader(
                "Choose files",
                type=["pdf", "heic", "jpg", "jpeg", "png", "webp"],
                accept_multiple_files=True,
                key=f"ad_photos_{aid}",
                help="PDF, HEIC, JPG, JPEG, PNG, WEBP. PDFs use rendered pages for AI; HEIC is converted for analysis.",
            )
            st.markdown('<div class="ips-ad-photos-upload-row">', unsafe_allow_html=True)
            upload_photos_clicked = st.button(
                "Upload",
                type="primary",
                key=f"ad_upphotos_{aid}",
                use_container_width=False,
            )
            st.markdown("</div>", unsafe_allow_html=True)
        elif can_edit and not quick_edit:
            st.caption("Open **Quick Edit** (✏️) to add photos or files.")
        else:
            st.caption("Editors can add files using **Quick Edit** (✏️).")

    if can_edit and quick_edit and upload_photos_clicked:
        if not detail_photos:
            st.error("Choose one or more files first.")
        else:
            batch = [
                {"file_name": f.name, "file_bytes": f.getvalue(), "photo_type": "overview"}
                for f in detail_photos
            ]
            append_asset_photos(asset, batch, uploaded_by=current_profile().get("id"))
            st.success("Files saved.")
            st.rerun()

    with st.container(border=True):
        st.markdown('<span class="ips-ad-section-docs"></span>', unsafe_allow_html=True)
        st.markdown("##### Documents")
        st.caption("Manuals, PDFs, and office files.")
        _render_asset_documents_list(
            merged_documents,
            key_prefix="ad_main_doc",
            show_hint=True,
            mobile_layout=is_narrow,
        )

    st.markdown("---")

    if not can_edit:
        st.info("You can view this profile. Admin or pm role is required for check-out and other actions.")
    else:
        # Full rental form + uploads + AI only while Quick Edit (✏️) is active — same session keys as before.
        if quick_edit:
            st.markdown("##### Rent to Customer")
            st.caption("Flag for customer rental and optional daily / weekly / monthly rates.")
            rc1 = st.checkbox(
                "Rent to Customer",
                value=bool(asset.get("is_rental")),
                key=f"ad_is_rental_{aid}",
            )
            rd = rw = rm = 0.0
            rnotes = str(asset.get("rental_notes") or "")
            if rc1:
                r1, r2, r3 = st.columns(3)
                rd = r1.number_input(
                    "Daily rate",
                    min_value=0.0,
                    value=float(asset.get("rental_daily_rate") or 0),
                    step=1.0,
                    format="%.2f",
                    key=f"ad_rr_daily_{aid}",
                )
                rw = r2.number_input(
                    "Weekly rate",
                    min_value=0.0,
                    value=float(asset.get("rental_weekly_rate") or 0),
                    step=1.0,
                    format="%.2f",
                    key=f"ad_rr_weekly_{aid}",
                )
                rm = r3.number_input(
                    "Monthly rate",
                    min_value=0.0,
                    value=float(asset.get("rental_monthly_rate") or 0),
                    step=1.0,
                    format="%.2f",
                    key=f"ad_rr_monthly_{aid}",
                )
                rnotes = st.text_area(
                    "Rental notes",
                    value=rnotes,
                    height=68,
                    key=f"ad_rr_notes_{aid}",
                )
            if is_narrow:
                (rent_save_col,) = st.columns(1)
            else:
                _, rent_save_col = st.columns([2, 1])
            with rent_save_col:
                if st.button("Save rental settings", key=f"ad_save_rental_{aid}", use_container_width=True):
                    pay = {
                        "is_rental": bool(rc1),
                        "rental_notes": str(rnotes or "").strip()
                        if rc1
                        else str(asset.get("rental_notes") or "").strip(),
                    }
                    if rc1:
                        pay["rental_daily_rate"] = optional_numeric(rd)
                        pay["rental_weekly_rate"] = optional_numeric(rw)
                        pay["rental_monthly_rate"] = optional_numeric(rm)
                    update_rows_admin("assets", pay, {"id": asset["id"]})
                    st.success("Rental settings saved.")
                    st.rerun()

            st.markdown("##### Asset updates")
            st.caption(
                "Choose files in **Photos & files** above, then **Upload** or **Run AI autofill** to suggest field values."
            )
            run_ai = st.button("Run AI autofill", key=f"ad_runai_{aid}", use_container_width=True)

            if run_ai:
                if not detail_photos:
                    st.error("Choose one or more files before running AI autofill.")
                else:
                    try:
                        with st.spinner("Analyzing uploads…"):
                            batch_tuples = [(f.getvalue(), f.name) for f in detail_photos]
                            result = extract_asset_from_photos(batch_tuples)
                        apply_extraction_to_asset(asset, result)
                        st.session_state["asset_detail_flash"] = "Asset fields updated from AI — review history and notes below."
                    except ValueError as exc:
                        st.error(str(exc))
                    except Exception as exc:
                        st.error(f"AI autofill failed: {exc}")

        act = st.session_state.get("asset_detail_action")
        if act:
            if is_narrow:
                (close_act_col,) = st.columns(1)
            else:
                _, close_act_col = st.columns([2, 1])
            with close_act_col:
                if st.button("Close action panel", key=f"ad_close_{aid}", use_container_width=True):
                    st.session_state.pop("asset_detail_action", None)
        act = st.session_state.get("asset_detail_action")

        if act == "checkout":
            st.markdown("**Check out**")
            _co_x, _co_y = st.columns(2)
            with _co_x:
                co_emp = st.text_input("Assign to", key=f"co_emp_{aid}")
            with _co_y:
                co_job = st.selectbox("Job", list(job_options.keys()), key=f"co_job_{aid}")
            co_loc = st.text_input("Assignment location", value=str(asset.get("location", "")), key=f"co_loc_{aid}")
            co_notes = st.text_area("Notes", key=f"co_notes_{aid}", height=96)
            if is_narrow:
                (co_btn_col,) = st.columns(1)
            else:
                _, co_btn_col = st.columns([2, 1])
            with co_btn_col:
                co_do = st.button("Confirm check out", key=f"co_go_{aid}", use_container_width=True)
            if co_do:
                insert_row_admin(
                    "asset_assignments",
                    {
                        "asset_id": asset["id"],
                        "assigned_to": co_emp.strip(),
                        "assigned_job_id": job_options.get(co_job),
                        "assigned_location": co_loc.strip(),
                        "check_out_at": datetime.utcnow().isoformat(),
                        "notes": co_notes.strip(),
                        "created_by": current_profile().get("id"),
                    },
                )
                update_rows_admin(
                    "assets",
                    {
                        "status": "Assigned",
                        "assigned_employee": co_emp.strip(),
                        "assigned_job_id": job_options.get(co_job),
                        "location": co_loc.strip(),
                    },
                    {"id": asset["id"]},
                )
                st.session_state.pop("asset_detail_action", None)
                st.success("Checked out.")

        elif act == "checkin":
            st.markdown("**Check in**")
            ci_loc = st.text_input("Location", value=str(asset.get("location", "")), key=f"ci_loc_{aid}")
            ci_notes = st.text_area("Notes", key=f"ci_notes_{aid}", height=96)
            if is_narrow:
                (ci_btn_col,) = st.columns(1)
            else:
                _, ci_btn_col = st.columns([2, 1])
            with ci_btn_col:
                ci_do = st.button("Confirm check in", key=f"ci_go_{aid}", use_container_width=True)
            if ci_do:
                insert_row_admin(
                    "asset_assignments",
                    {
                        "asset_id": asset["id"],
                        "assigned_to": str(asset.get("assigned_employee", "")),
                        "assigned_job_id": asset.get("assigned_job_id"),
                        "assigned_location": ci_loc.strip(),
                        "check_in_at": datetime.utcnow().isoformat(),
                        "notes": ci_notes.strip(),
                        "created_by": current_profile().get("id"),
                    },
                )
                update_rows_admin(
                    "assets",
                    {
                        "status": "Available",
                        "assigned_employee": "",
                        "assigned_job_id": None,
                    },
                    {"id": asset["id"]},
                )
                st.session_state.pop("asset_detail_action", None)
                st.success("Checked in.")

        elif act == "broken":
            st.markdown("**Report broken**")
            rb_notes = st.text_area("Describe the issue (optional)", key=f"rb_notes_{aid}", height=88)
            if is_narrow:
                rb_clicked = st.button("Set status to Out for Repair", key=f"rb_go_{aid}", use_container_width=True)
            else:
                _, _rb_col = st.columns([2, 1])
                with _rb_col:
                    rb_clicked = st.button(
                        "Set status to Out for Repair", key=f"rb_go_{aid}", use_container_width=True
                    )
            if rb_clicked:
                payload = {"status": "Out for Repair"}
                if rb_notes.strip():
                    prev = str(asset.get("notes") or "").strip()
                    payload["notes"] = (prev + "\n\n" if prev else "") + f"[Reported broken] {rb_notes.strip()}"
                update_rows_admin("assets", payload, {"id": asset["id"]})
                st.session_state.pop("asset_detail_action", None)
                st.success("Status updated.")

        elif act == "maint":
            st.markdown("**Add maintenance**")
            m1, m2, m3 = st.columns(3)
            svc_type = m1.text_input("Service type", value="PM Service", key=f"m_type_{aid}")
            svc_date = m2.date_input("Service date", key=f"m_date_{aid}")
            vendor = m3.text_input("Vendor", key=f"m_vendor_{aid}")
            m4, m5, m6 = st.columns(3)
            hm = m4.number_input("Hour meter", min_value=0.0, value=float(asset.get("hour_meter") or 0), key=f"m_hm_{aid}")
            mi = m5.number_input("Mileage", min_value=0.0, value=float(asset.get("mileage") or 0), key=f"m_mi_{aid}")
            cost = m6.number_input("Cost", min_value=0.0, value=0.0, key=f"m_cost_{aid}")
            m7, m8 = st.columns(2)
            po = m7.text_input("PO number", key=f"m_po_{aid}")
            perf = m8.text_input("Performed by", key=f"m_perf_{aid}")
            m_notes = st.text_area("Notes", key=f"m_notes_{aid}", height=90)
            if is_narrow:
                (m_btn_col,) = st.columns(1)
            else:
                _, m_btn_col = st.columns([2, 1])
            with m_btn_col:
                m_go = st.button("Save maintenance", key=f"m_go_{aid}", use_container_width=True)
            if m_go:
                save_maintenance_record(
                    {
                        "asset_id": asset["id"],
                        "service_type": svc_type.strip(),
                        "service_date": svc_date.isoformat(),
                        "hour_meter": hm,
                        "mileage": mi,
                        "vendor": vendor.strip(),
                        "cost": cost,
                        "po_number": po.strip(),
                        "performed_by": perf.strip(),
                        "notes": m_notes.strip(),
                    },
                    created_by=current_profile().get("id"),
                )
                st.session_state.pop("asset_detail_action", None)
                st.success("Maintenance logged.")

        elif act == "insp":
            st.markdown("**Add inspection**")
            i1, i2, i3 = st.columns(3)
            itype = i1.selectbox(
                "Inspection type",
                ["Daily", "Weekly", "Monthly", "Pre-Use", "Damage Report"],
                key=f"i_type_{aid}",
            )
            idate = i2.date_input("Inspection date", key=f"i_date_{aid}")
            inspector = i3.text_input("Inspector", key=f"i_insp_{aid}")
            istatus = st.selectbox("Status", ["Pass", "Needs Attention", "Fail"], key=f"i_stat_{aid}")
            _i_iss, _i_cor = st.columns(2)
            with _i_iss:
                issues = st.text_area("Issues found", key=f"i_issues_{aid}", height=90)
            with _i_cor:
                corrective = st.text_area("Corrective action", key=f"i_corr_{aid}", height=90)
            if is_narrow:
                (i_btn_col,) = st.columns(1)
            else:
                _, i_btn_col = st.columns([2, 1])
            with i_btn_col:
                i_go = st.button("Save inspection", key=f"i_go_{aid}", use_container_width=True)
            if i_go:
                insert_row_admin(
                    "asset_inspections",
                    {
                        "asset_id": asset["id"],
                        "inspection_type": itype,
                        "inspection_date": idate.isoformat(),
                        "inspector": inspector.strip(),
                        "status": istatus,
                        "issues_found": issues.strip(),
                        "corrective_action": corrective.strip(),
                        "created_by": current_profile().get("id"),
                    },
                )
                st.session_state.pop("asset_detail_action", None)
                st.success("Inspection saved.")

        elif act == "delete":
            if current_role() != "admin":
                st.session_state.pop("asset_detail_action", None)
            else:
                st.markdown("**Delete asset**")
                st.warning(
                    "This permanently removes this asset and its documents, photos, maintenance, "
                    "assignments, and inspection rows from the database. Storage files may remain in the bucket."
                )
                del_confirm = st.text_input(
                    f"Type `{asset.get('asset_id')}` to confirm",
                    key=f"del_confirm_{aid}",
                )
                aid_str = str(asset.get("asset_id") or "")
                if st.button(
                    "Permanently delete",
                    key=f"del_go_{aid}",
                    disabled=del_confirm.strip() != aid_str,
                    use_container_width=True,
                ):
                    delete_asset_and_related(str(asset["id"]))
                    st.session_state.pop("asset_detail_id", None)
                    st.session_state.pop("asset_detail_action", None)
                    st.session_state["asset_detail_flash"] = f"Deleted asset {aid_str}."
                    st.session_state[IPS_NAV_PENDING_KEY] = "Asset Database"
                    st.session_state["_asset_detail_do_nav_rerun"] = True

        elif act == "doc":
            st.markdown("**Upload document**")
            if is_narrow:
                dtype = st.selectbox("Document type", DOCUMENT_TYPES, key=f"d_type_{aid}")
                exp = st.date_input("Expiration date", value=None, key=f"d_exp_{aid}")
                d_notes = st.text_area("Notes", key=f"d_notes_{aid}", height=72)
                up = st.file_uploader(
                    "File",
                    accept_multiple_files=False,
                    key=f"d_up_{aid}",
                    type=["pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "csv", "png", "jpg", "jpeg"],
                )
                d_upload_clicked = st.button("Upload", key=f"d_go_{aid}", use_container_width=True)
            else:
                _d_t1, _d_t2 = st.columns(2)
                with _d_t1:
                    dtype = st.selectbox("Document type", DOCUMENT_TYPES, key=f"d_type_{aid}")
                with _d_t2:
                    exp = st.date_input("Expiration date", value=None, key=f"d_exp_{aid}")
                _d_m1, _d_m2 = st.columns(2)
                with _d_m1:
                    d_notes = st.text_area("Notes", key=f"d_notes_{aid}", height=80)
                with _d_m2:
                    up = st.file_uploader(
                        "File",
                        accept_multiple_files=False,
                        key=f"d_up_{aid}",
                        type=["pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "csv", "png", "jpg", "jpeg"],
                    )
                _, _d_go_col = st.columns([2, 1])
                with _d_go_col:
                    d_upload_clicked = st.button("Upload", key=f"d_go_{aid}", use_container_width=True)
            if d_upload_clicked:
                if not up:
                    st.error("Choose a file first.")
                else:
                    try:
                        persist_asset_document_upload(
                            asset_row=asset,
                            uploaded=up,
                            document_type=dtype,
                            expiration_date=exp,
                            notes=d_notes,
                            uploaded_by=current_profile().get("id"),
                        )
                    except Exception as exc:
                        st.error(f"Could not save document (storage or database): {exc}")
                    else:
                        st.session_state.pop("asset_detail_action", None)
                        st.session_state["asset_detail_flash"] = "Manual uploaded successfully."
                        st.rerun()

    # --- Tool Trailer: kit + expenses + replacement history ---
    if _is_tool_trailer(asset):
        st.markdown("### Tool trailer")
        _tt_key = f"ad_tool_trailer_panel_{aid}"
        st.session_state.setdefault(_tt_key, "Overview")
        st.radio(
            "Tool trailer sections",
            ["Overview", "Tool Kits", "Repairs / Expenses", "Replacement History"],
            horizontal=True,
            key=_tt_key,
            label_visibility="collapsed",
        )
        tt_panel = str(st.session_state.get(_tt_key) or "Overview")
        if tt_panel == "Overview":
            st.caption("Tool trailer summary (asset + kit value).")
            _render_tool_trailer_kit(
                asset_row=asset,
                kits=kits,
                kit_items=kit_items,
                replacements=kit_replacements,
                jobs=jobs,
                can_edit=can_edit,
            )
        elif tt_panel == "Tool Kits":
            _render_tool_trailer_kit(
                asset_row=asset,
                kits=kits,
                kit_items=kit_items,
                replacements=kit_replacements,
                jobs=jobs,
                can_edit=can_edit,
            )
        elif tt_panel == "Repairs / Expenses":
            _render_asset_expenses(
                asset_row=asset,
                expenses=asset_expenses,
                can_edit=can_edit,
                profiles=[],
            )
        elif tt_panel == "Replacement History":
            _render_tool_trailer_replacement_history(replacements=kit_replacements, jobs=jobs)

    st.markdown("### History & records")
    _hist_key = f"ad_hist_panel_{aid}"
    st.session_state.setdefault(_hist_key, "Documents")
    st.radio(
        "History sections",
        ["Documents", "Maintenance", "Assignments", "Inspections", "Notes"],
        horizontal=True,
        key=_hist_key,
        label_visibility="collapsed",
    )
    hp = str(st.session_state.get(_hist_key) or "Documents")
    if hp == "Documents":
        st.markdown("##### Documents library")
        st.caption("Same as **Documents** above · signed links expire in about one hour.")
        _render_asset_documents_list(
            merged_documents,
            key_prefix="ad_tab_doc",
            show_hint=False,
            mobile_layout=is_narrow,
        )

    elif hp == "Maintenance":
        if maintenance:
            show = pd.DataFrame(maintenance)
            drop = [c for c in ("id", "asset_id", "created_by") if c in show.columns]
            if drop:
                show = show.drop(columns=drop, errors="ignore")
            st.dataframe(show, use_container_width=True, hide_index=True)
        else:
            st.caption("No maintenance records.")

    elif hp == "Assignments":
        if assignments:
            show = pd.DataFrame(assignments)
            drop = [c for c in ("id", "asset_id", "created_by") if c in show.columns]
            if drop:
                show = show.drop(columns=drop, errors="ignore")
            st.dataframe(show, use_container_width=True, hide_index=True)
        else:
            st.caption("No assignment history.")

    elif hp == "Inspections":
        if inspections:
            show = pd.DataFrame(inspections)
            drop = [c for c in ("id", "asset_id", "created_by") if c in show.columns]
            if drop:
                show = show.drop(columns=drop, errors="ignore")
            st.dataframe(show, use_container_width=True, hide_index=True)
        else:
            st.caption("No inspections.")

    else:
        if can_edit:
            new_notes = st.text_area("Notes", value=str(asset.get("notes") or ""), height=120, key=f"notes_ed_{aid}")
            if is_narrow:
                (notes_save_col,) = st.columns(1)
            else:
                _, notes_save_col = st.columns([3, 1])
            with notes_save_col:
                notes_saved = st.button("Save notes", key=f"notes_save_{aid}", use_container_width=True)
            if notes_saved:
                update_rows_admin("assets", {"notes": new_notes.strip()}, {"id": asset["id"]})
                st.success("Notes saved.")
        else:
            st.markdown("**Notes**")
            st.write(str(asset.get("notes") or "").strip() or "—")

    st.markdown('<div class="ips-ad-back-wrap">', unsafe_allow_html=True)
    if st.button("← Back to Asset List", use_container_width=True):
        _back_to_asset_list(aid=str(aid))
    st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.pop("_asset_detail_do_nav_rerun", None):
        st.rerun()