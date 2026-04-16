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
        delete_asset_photo,
        optional_numeric,
        save_maintenance_record,
        set_asset_primary_photo,
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
        delete_asset_photo,
        optional_numeric,
        save_maintenance_record,
        set_asset_primary_photo,
    )
    from services.job_service import job_row_select_label  # type: ignore
    from ui import IPS_NAV_PENDING_KEY  # type: ignore

# Centered primary hero image (not full container width; ``width=`` for Streamlit 1.33+).
_PRIMARY_IMAGE_WIDTH_DESKTOP = 380
_PRIMARY_IMAGE_WIDTH_MOBILE = 240
# Gallery thumbnail / preview sizing
_GALLERY_THUMB_WIDTH_DESKTOP = 140
_GALLERY_THUMB_WIDTH_MOBILE = 180
_GALLERY_PREVIEW_IMAGE_WIDTH_DESKTOP = 480
_GALLERY_PREVIEW_IMAGE_WIDTH_MOBILE = 260

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
    font-size: 16px;
    font-weight: 700;
    color: #f8fafc;
    margin: 0 0 10px 0;
    line-height: 1.25;
}
.ips-hero-title {
    font-size: 26px;
    font-weight: 800;
    color: #f8fafc;
    margin: 0 0 16px 0;
    line-height: 1.2;
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
/* Uploaded-files gallery: click thumbnail to expand (linked image) */
.ips-ad-gallery-wrap a[href*="ips_gpv"] {
    cursor: zoom-in;
    border-radius: 8px;
    display: inline-block;
    line-height: 0;
}
.ips-ad-gallery-wrap a[href*="ips_gpv"]:hover {
    outline: 2px solid rgba(96, 165, 250, 0.9);
    outline-offset: 2px;
}
.ips-ad-gallery-wrap a[href*="ips_gpv"] img {
    border-radius: 8px;
}
.ips-ad-gallery-thumb-hint {
    font-size: 12px;
    color: #94a3b8;
    margin-top: 2px;
    margin-bottom: 6px;
}
.ips-ad-gallery-preview-panel {
    background: rgba(15, 23, 42, 0.75);
    border: 1px solid rgba(51, 65, 85, 0.95);
    border-radius: 12px;
    padding: 12px 14px 14px 14px;
    margin-top: 4px;
}
.ips-ad-gallery-preview-panel h5 {
    color: #e2e8f0 !important;
    margin-bottom: 10px !important;
}
.ips-ad-gallery-preview-pos {
    text-align: center;
    color: #94a3b8;
    font-size: 0.95rem;
    margin: 0.25rem 0 0.5rem 0;
}
.ips-ad-qr-label {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #94a3b8;
    margin: 0 0 8px 0;
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
</style>
"""

_ASSET_DETAIL_SECTIONS_CSS = """
<style>
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ad-section-primary) {
    background: rgba(15, 23, 42, 0.62) !important;
    border-color: rgba(71, 85, 105, 0.55) !important;
    border-radius: 10px !important;
    padding: 10px 12px 10px 12px !important;
    margin-bottom: 8px !important;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05);
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ad-section-primary) h5 {
    color: #e2e8f0 !important;
    border-bottom: 1px solid rgba(100, 116, 139, 0.35) !important;
    padding-bottom: 6px !important;
    margin-bottom: 6px !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ad-section-photos) {
    background: rgba(15, 23, 42, 0.58) !important;
    border-color: rgba(71, 85, 105, 0.55) !important;
    border-radius: 10px !important;
    padding: 8px 10px 10px 10px !important;
    margin-bottom: 8px !important;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ad-section-photos) h5 {
    color: #e2e8f0 !important;
    border-bottom: 1px solid rgba(100, 116, 139, 0.35) !important;
    padding-bottom: 4px !important;
    margin-bottom: 4px !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ad-section-docs) {
    background: rgba(15, 23, 42, 0.52) !important;
    border-color: rgba(71, 85, 105, 0.48) !important;
    border-radius: 10px !important;
    padding: 8px 10px 10px 10px !important;
    margin-bottom: 8px !important;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ad-section-docs) h5 {
    color: #e2e8f0 !important;
    border-bottom: 1px solid rgba(100, 116, 139, 0.35) !important;
    padding-bottom: 4px !important;
    margin-bottom: 4px !important;
}
/* Compact QR tool card (col1) */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ad-qr-tool) {
    max-width: 260px !important;
    background: rgba(15, 23, 42, 0.65) !important;
    border-color: rgba(71, 85, 105, 0.55) !important;
    border-radius: 10px !important;
    padding: 10px 12px 12px 12px !important;
    margin-bottom: 10px !important;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
}
</style>
"""

_IPS_AD_SECTIONS_CSS_KEY = "ips_ad_detail_sections_css_injected_v4"


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
    """QR downloads in a bordered card; ``compact`` uses a smaller image (still scannable on phones)."""
    qr_text = qr_payload(asset)
    if not qr_text:
        return
    img_w = 120 if compact else 220
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
                caption=None if compact else f"Asset QR · {qr_text}",
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


def _render_asset_detail_meta_and_rental(
    asset: dict,
    jobs: list[dict],
    aid: str,
    *,
    quick_edit: bool,
    qe_key: str,
    can_edit: bool,
    is_narrow: bool,
) -> None:
    """Hero title, optional quick edit, field grid (desktop) or stacked summary + expander (mobile), rental rates."""
    st.markdown('<div class="ips-ad-meta-col ips-ad-hero-stack">', unsafe_allow_html=True)
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
        st.caption("Exit Quick Edit (✏️) to use the full **rental rates** form below.")

    if is_narrow:
        _kv("Asset ID", _disp(asset.get("asset_id")))
        if not quick_edit and str(asset.get("category") or "").strip():
            _kv("Category", _disp(asset.get("category")))
        _kv("Status", _disp(asset.get("status")))
        if not quick_edit:
            if bool(asset.get("is_rental")):
                st.markdown(
                    '<span class="ips-badge-rental">Rental · rent to customer</span>',
                    unsafe_allow_html=True,
                )
            else:
                _kv("Rent to Customer", "No")
        _kv("Serial number", _disp(asset.get("serial_number")))
        _kv("Model", _disp(asset.get("model")))
        _kv("Brand", _disp(asset.get("manufacturer")))
        with st.expander("More details", expanded=False):
            _kv("Location", _disp(asset.get("location")))
            _kv("Assigned job", _job_name(jobs, asset.get("assigned_job_id")))
            _kv("Assigned employee", _disp(asset.get("assigned_employee")))
            _kv("Condition", _disp(asset.get("condition")))
            _kv("Mileage", _disp(asset.get("mileage")))
            _kv("Hour meter", _disp(asset.get("hour_meter")))
            if str(asset.get("year") or "").strip():
                _kv("Year", _disp(asset.get("year")))
    else:
        c1, c2 = st.columns(2)
        with c1:
            _kv("Brand", _disp(asset.get("manufacturer")))
            _kv("Serial number", _disp(asset.get("serial_number")))
            _kv("Status", _disp(asset.get("status")))
            _kv("Assigned employee", _disp(asset.get("assigned_employee")))
            _kv("Condition", _disp(asset.get("condition")))
            _kv("Mileage", _disp(asset.get("mileage")))
        with c2:
            _kv("Model", _disp(asset.get("model")))
            _kv("Asset ID", _disp(asset.get("asset_id")))
            _kv("Location", _disp(asset.get("location")))
            _kv("Assigned job", _job_name(jobs, asset.get("assigned_job_id")))
            _kv("Hour meter", _disp(asset.get("hour_meter")))
            if str(asset.get("year") or "").strip():
                _kv("Year", _disp(asset.get("year")))
            if not quick_edit:
                if str(asset.get("category") or "").strip():
                    _kv("Category", _disp(asset.get("category")))
                rent_yes = bool(asset.get("is_rental"))
                _kv("Rent to Customer", "Yes" if rent_yes else "No")
    st.markdown("</div>", unsafe_allow_html=True)

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
    """One action per row: open cloud signed URL or local file URI in a new tab (same storage resolution as before)."""
    _ = key_prefix
    _ = mobile_layout
    if not documents:
        st.caption("No documents uploaded yet.")
        return
    if show_hint:
        st.caption("Signed links expire after about one hour — use the button again if needed.")
    for doc in documents:
        fp = str(doc.get("file_path") or "").strip()
        fn = str(doc.get("file_name") or "").strip() or Path(fp).name or "document"
        ref = create_signed_url(fp, expires_in=3600) if fp else ""
        is_pdf = ".pdf" in fn.lower()
        label = "Manual" if is_pdf else "Open"

        open_url: str | None = None
        if ref:
            if ref.startswith("http://") or ref.startswith("https://"):
                open_url = ref
            else:
                p = Path(ref)
                if p.is_file():
                    open_url = str(p.resolve().as_uri())

        _, mid, _ = st.columns([1, 10, 1])
        with mid:
            if open_url:
                st.link_button(label, url=open_url, use_container_width=True)
            elif ref:
                st.caption("Missing file")
            else:
                st.caption("Unavailable")
        st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)


def _gallery_image_row_indices(rows: list[dict]) -> list[int]:
    """Indices into ``rows`` that are image files (preview navigates across these only)."""
    out: list[int] = []
    for i, row in enumerate(rows):
        fp = str(row.get("file_path") or "").strip()
        fn = str(row.get("file_name") or "").strip() or Path(fp).name or "file"
        if _asset_file_kind(fn) == "image":
            out.append(i)
    return out


def _gallery_preview_session_key(aid: str) -> str:
    return f"asset_gallery_preview_{aid}"


_GALLERY_PREVIEW_QP = "ips_gpv"


def _sync_asset_gallery_preview_query(aid: str) -> None:
    """Apply ?ips_gpv=<index> from a thumbnail click into session state, then clear the URL."""
    raw = st.query_params.get(_GALLERY_PREVIEW_QP)
    if raw is None:
        return
    try:
        idx = int(raw)
    except (TypeError, ValueError):
        st.query_params.pop(_GALLERY_PREVIEW_QP, None)
        return
    st.session_state[_gallery_preview_session_key(aid)] = idx
    st.query_params.pop(_GALLERY_PREVIEW_QP, None)


def _clear_asset_gallery_preview(aid: str) -> None:
    """Clear expanded preview: session index and any lingering ``ips_gpv`` query param."""
    st.session_state.pop(_gallery_preview_session_key(aid), None)
    st.query_params.pop(_GALLERY_PREVIEW_QP, None)


def _back_to_asset_list(*, aid: str | None) -> None:
    """Clear asset-detail state and navigate back to Asset Database list."""
    if aid:
        _clear_asset_gallery_preview(str(aid))
        st.session_state.pop(_pending_delete_session_key(str(aid)), None)
        st.session_state.pop(f"del_confirm_{aid}", None)
        st.session_state.pop(f"ad_quick_edit_{aid}", None)

    st.session_state.pop("asset_detail_id", None)
    st.session_state.pop("asset_edit_id", None)
    st.session_state.pop("asset_return_to", None)
    st.session_state.pop("asset_detail_action", None)

    # Ensure we don't rely on a second click for rerun/nav.
    st.session_state.pop("_asset_detail_do_nav_rerun", None)
    st.session_state[IPS_NAV_PENDING_KEY] = "Asset Database"
    st.rerun()


def _pending_delete_session_key(aid: str) -> str:
    return f"asset_photo_delete_pending_{aid}"


def _paths_equal_storage(a: str, b: str) -> bool:
    return str(a or "").strip().replace("\\", "/") == str(b or "").strip().replace("\\", "/")


def _render_one_asset_file_tile(
    aid: str,
    idx: int,
    row: dict,
    asset: dict,
    can_edit: bool,
    *,
    thumb_width: int = 160,
) -> None:
    """Thumbnail for images; PDF/other via link or download (cloud URL vs local path)."""
    storage_path = str(row.get("file_path") or "").strip()
    file_name = str(row.get("file_name") or "").strip() or Path(storage_path).name or "file"
    row_id = str(row.get("id") or "").strip()
    key_base = f"af_{aid}_{idx}"
    pending_key = _pending_delete_session_key(aid)
    pending = str(st.session_state.get(pending_key) or "").strip()

    if can_edit and row_id and pending == row_id:
        st.warning("Delete this file from storage and the database?")
        c_yes, c_no = st.columns(2)
        if c_yes.button("Yes, delete", key=f"{key_base}_del_yes", use_container_width=True):
            try:
                delete_asset_photo(row, asset)
            except Exception as exc:
                st.error(f"Could not delete file: {exc}")
            else:
                st.session_state.pop(pending_key, None)
                _clear_asset_gallery_preview(aid)
                st.session_state["asset_detail_flash"] = "File removed."
                st.rerun()
        if c_no.button("Cancel", key=f"{key_base}_del_no", use_container_width=True):
            st.session_state.pop(pending_key, None)
            st.rerun()
        return

    def _offer_delete(suffix: str = "del") -> None:
        if not (can_edit and row_id):
            return
        if st.button("Delete", key=f"{key_base}_{suffix}", use_container_width=True):
            st.session_state[pending_key] = row_id
            st.rerun()

    def _offer_set_primary() -> None:
        cur = str(storage_path or "").strip()
        primary = str(asset.get("photo_path") or "").strip()
        is_primary = _paths_equal_storage(primary, cur)
        if is_primary:
            st.markdown(
                '<span class="ips-primary-badge">Primary Image</span>',
                unsafe_allow_html=True,
            )
            if can_edit:
                st.button(
                    "Set as Primary Image",
                    key=f"{key_base}_primary",
                    use_container_width=True,
                    disabled=True,
                    help="This photo is already the primary image for this asset.",
                )
            return
        if not (can_edit and row_id):
            return
        if st.button(
            "Set as Primary Image",
            key=f"{key_base}_primary",
            use_container_width=True,
        ):
            try:
                set_asset_primary_photo(asset, storage_path)
            except Exception as exc:
                st.error(f"Could not set primary image: {exc}")
            else:
                st.session_state["asset_detail_flash"] = "Primary image updated"
                st.rerun()

    ref = create_signed_url(storage_path, expires_in=3600) if storage_path else ""
    if not ref:
        st.caption(f"Unavailable · {file_name}")
        _offer_delete("del_unavail")
        return

    kind = _asset_file_kind(file_name)
    is_http = ref.startswith("http://") or ref.startswith("https://")

    if kind == "image":
        cap_short = file_name[:48] + ("…" if len(file_name) > 48 else "")
        try:
            # Streamlit 1.33: st.image has no ``link=``; use same-page query param for gallery preview.
            safe_ref = html.escape(str(ref), quote=True)
            st.markdown(
                f'<a href="?{_GALLERY_PREVIEW_QP}={idx}" class="ips-ad-gallery-thumb-link" '
                'style="display:block;text-decoration:none;">'
                f'<img src="{safe_ref}" alt="" '
                f'style="max-width:100%;width:{int(thumb_width)}px;height:auto;border-radius:8px;'
                f'cursor:pointer;object-fit:cover;" />'
                f"</a>",
                unsafe_allow_html=True,
            )
            st.caption(cap_short)
            st.markdown(
                '<p class="ips-ad-gallery-thumb-hint">Click image to enlarge</p>',
                unsafe_allow_html=True,
            )
        except Exception:
            st.caption(file_name)
            if is_http:
                st.link_button("Open file", url=ref, use_container_width=True)
            else:
                p = Path(ref)
                if p.is_file():
                    st.download_button(
                        "Download",
                        data=p.read_bytes(),
                        file_name=file_name,
                        key=f"{key_base}_img_dl",
                    )
        _offer_set_primary()
        _offer_delete()
        return

    if kind == "pdf":
        st.markdown("##### 📄")
        if is_http:
            st.link_button(file_name[:40] + ("…" if len(file_name) > 40 else ""), url=ref, use_container_width=True)
        else:
            p = Path(ref)
            if p.is_file():
                st.download_button(
                    f"Download · {file_name[:32]}",
                    data=p.read_bytes(),
                    file_name=file_name,
                    mime="application/pdf",
                    key=f"{key_base}_pdf_dl",
                )
            else:
                st.caption(file_name)
        _offer_delete()
        return

    st.markdown("##### 📎")
    if is_http:
        st.link_button(file_name[:40] + ("…" if len(file_name) > 40 else ""), url=ref, use_container_width=True)
    else:
        p = Path(ref)
        if p.is_file():
            st.download_button(
                f"Download · {file_name[:32]}",
                data=p.read_bytes(),
                file_name=file_name,
                key=f"{key_base}_oth_dl",
            )
        else:
            st.caption(file_name)
    _offer_delete()


def _render_asset_image_preview_panel(aid: str, rows: list[dict], *, mobile: bool = False) -> None:
    """Full-width image below the gallery when user expands a thumbnail."""
    pk = _gallery_preview_session_key(aid)
    raw = st.session_state.get(pk)
    if raw is None:
        return
    try:
        idx = int(raw)
    except (TypeError, ValueError):
        st.session_state.pop(pk, None)
        return
    if idx < 0 or idx >= len(rows):
        st.session_state.pop(pk, None)
        return

    row = rows[idx]
    fp = str(row.get("file_path") or "").strip()
    fn = str(row.get("file_name") or "").strip() or Path(fp).name or "file"
    if _asset_file_kind(fn) != "image":
        st.session_state.pop(pk, None)
        return

    ref = create_signed_url(fp, expires_in=3600) if fp else ""
    if not ref:
        st.session_state.pop(pk, None)
        return

    image_indices = _gallery_image_row_indices(rows)
    try:
        img_pos = image_indices.index(idx)
    except ValueError:
        st.session_state.pop(pk, None)
        return
    prev_idx = image_indices[img_pos - 1] if img_pos > 0 else None
    next_idx = image_indices[img_pos + 1] if img_pos < len(image_indices) - 1 else None
    pos_label = f"{img_pos + 1} / {len(image_indices)}"

    st.markdown('<div class="ips-ad-gallery-preview-panel">', unsafe_allow_html=True)
    if mobile:
        st.markdown("##### Preview")
        if st.button(
            "Close Preview",
            key=f"asset_gallery_close_{aid}",
            use_container_width=True,
            type="secondary",
            help="Exit full-size preview",
        ):
            _clear_asset_gallery_preview(aid)
            st.rerun()
        st.markdown(
            f'<p class="ips-ad-gallery-preview-pos">{html.escape(pos_label)}</p>',
            unsafe_allow_html=True,
        )
        prev_c, next_c = st.columns(2)
        with prev_c:
            if st.button(
                "Previous",
                key=f"asset_gallery_prev_{aid}",
                use_container_width=True,
                disabled=prev_idx is None,
                help="Previous image",
            ):
                if prev_idx is not None:
                    st.session_state[pk] = prev_idx
                    st.rerun()
        with next_c:
            if st.button(
                "Next",
                key=f"asset_gallery_next_{aid}",
                use_container_width=True,
                disabled=next_idx is None,
                help="Next image",
            ):
                if next_idx is not None:
                    st.session_state[pk] = next_idx
                    st.rerun()
    else:
        ch_l, ch_r = st.columns([4, 1])
        with ch_l:
            st.markdown("##### Preview")
        with ch_r:
            if st.button(
                "Close Preview",
                key=f"asset_gallery_close_{aid}",
                use_container_width=True,
                type="secondary",
                help="Exit full-size preview",
            ):
                _clear_asset_gallery_preview(aid)
                st.rerun()

        np1, np2, np3 = st.columns([1, 2, 1])
        with np1:
            if st.button(
                "Previous",
                key=f"asset_gallery_prev_{aid}",
                use_container_width=True,
                disabled=prev_idx is None,
                help="Previous image",
            ):
                if prev_idx is not None:
                    st.session_state[pk] = prev_idx
                    st.rerun()
        with np2:
            st.markdown(
                f'<p style="text-align:center;color:#94a3b8;font-size:0.9rem;margin:0.35rem 0 0 0;">{pos_label}</p>',
                unsafe_allow_html=True,
            )
        with np3:
            if st.button(
                "Next",
                key=f"asset_gallery_next_{aid}",
                use_container_width=True,
                disabled=next_idx is None,
                help="Next image",
            ):
                if next_idx is not None:
                    st.session_state[pk] = next_idx
                    st.rerun()

    prev_w = _GALLERY_PREVIEW_IMAGE_WIDTH_MOBILE if mobile else _GALLERY_PREVIEW_IMAGE_WIDTH_DESKTOP
    try:
        _, _prev_mid, _ = st.columns([1, 2, 1])
        with _prev_mid:
            st.image(ref, width=prev_w)
    except Exception as exc:
        st.warning(f"Could not load image: {exc}")
    st.caption(fn)
    st.markdown("</div>", unsafe_allow_html=True)


def _render_asset_uploaded_files_gallery(
    aid: str,
    rows: list[dict],
    asset: dict,
    can_edit: bool,
    *,
    mobile: bool = False,
) -> None:
    if not rows:
        return
    st.caption(
        "Image thumbnails — **tap** for a large preview below. "
        "Use **Set as Primary Image** for the hero image above."
    )
    st.markdown('<div class="ips-ad-gallery-wrap">', unsafe_allow_html=True)
    per_row = 2 if mobile else 4
    thumb_w = _GALLERY_THUMB_WIDTH_MOBILE if mobile else _GALLERY_THUMB_WIDTH_DESKTOP
    for i in range(0, len(rows), per_row):
        chunk = rows[i : i + per_row]
        cols = st.columns(len(chunk))
        for j, row in enumerate(chunk):
            with cols[j]:
                _render_one_asset_file_tile(aid, i + j, row, asset, can_edit, thumb_width=thumb_w)

    st.markdown("</div>", unsafe_allow_html=True)
    _render_asset_image_preview_panel(aid, rows, mobile=mobile)


def render() -> None:
    render_header("Asset Detail")
    inject_asset_workflow_mobile_css()
    ensure_narrow_viewport_detected()
    flash = st.session_state.pop("asset_detail_flash", None)
    if flash:
        st.success(flash)
    st.caption("Equipment profile — key facts, actions, and history")

    st.markdown(_PROFILE_CARD_CSS, unsafe_allow_html=True)
    _inject_asset_detail_sections_css()

    can_edit = current_role() in {"admin", "estimator"}

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
    quick_edit = can_edit and bool(st.session_state.get(qe_key, False))

    if can_edit:
        _ed_l, _ed_r = st.columns([3, 1])
        with _ed_l:
            st.markdown('<span class="ips-ad-detail-top-actions"></span>', unsafe_allow_html=True)
        with _ed_r:
            if st.button("Edit Asset", key="edit_asset_btn", type="primary", use_container_width=True):
                st.session_state["assets_view"] = "edit"
                st.session_state["asset_edit_id"] = str(asset["id"])
                st.session_state["asset_return_to"] = "asset_detail"
                st.session_state[IPS_NAV_PENDING_KEY] = "Asset Manager"
                st.rerun()

    _sync_asset_gallery_preview_query(str(aid))

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

    documents.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)
    maintenance.sort(key=lambda r: str(r.get("service_date") or ""), reverse=True)
    assignments.sort(key=lambda r: str(r.get("created_at") or r.get("check_out_at") or ""), reverse=True)
    inspections.sort(key=lambda r: str(r.get("inspection_date") or ""), reverse=True)

    asset_photos = fetch_by_match("asset_photos", {"asset_id": asset["id"]}, limit=500)
    asset_photos.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)
    photo_rows, doc_rows_from_photos = _split_asset_photos_rows(asset_photos)
    merged_documents = _merge_asset_document_rows(documents, doc_rows_from_photos)

    photo_path = str(asset.get("photo_path") or "").strip()
    signed = ""
    if photo_path:
        signed = create_signed_url(photo_path, expires_in=3600)

    _hero_w = _PRIMARY_IMAGE_WIDTH_MOBILE if is_narrow else _PRIMARY_IMAGE_WIDTH_DESKTOP
    with st.container(border=True):
        st.markdown('<span class="ips-ad-section-primary"></span>', unsafe_allow_html=True)
        st.markdown("##### Primary image")
        if signed:
            try:
                _, _hero_mid, _ = st.columns([1, 2, 1])
                with _hero_mid:
                    st.image(signed, width=_hero_w)
            except Exception as exc:
                st.warning(f"Could not load primary image: {exc}")
        else:
            st.caption(
                "No primary image on file. Upload photos below or choose **Set as Primary Image** on a gallery thumbnail."
            )

    with st.container(border=True):
        st.markdown('<span class="ips-ad-section-photos"></span>', unsafe_allow_html=True)
        st.markdown("##### Photos")
        st.caption("Visual images only — PDFs and manuals appear under **Documents** below.")
        if photo_rows:
            _render_asset_uploaded_files_gallery(str(aid), photo_rows, asset, can_edit, mobile=is_narrow)
        else:
            st.caption("No photos in the gallery yet. Use **Upload photos** in the actions below.")

    with st.container(border=True):
        st.markdown('<span class="ips-ad-section-docs"></span>', unsafe_allow_html=True)
        st.markdown("##### Documents")
        st.caption("Manuals, PDFs, and office files — open or download.")
        _render_asset_documents_list(
            merged_documents,
            key_prefix="ad_main_doc",
            show_hint=True,
            mobile_layout=is_narrow,
        )

    st.markdown("---")

    if is_narrow:
        _render_asset_detail_meta_and_rental(
            asset,
            jobs,
            str(aid),
            quick_edit=quick_edit,
            qe_key=qe_key,
            can_edit=can_edit,
            is_narrow=True,
        )
        _render_asset_detail_qr_block(asset, str(aid), compact=True)
    else:
        col1, col2 = st.columns([1.5, 2.5], gap="medium")
        with col1:
            _render_asset_detail_qr_block(asset, str(aid), compact=False)
        with col2:
            _render_asset_detail_meta_and_rental(
                asset,
                jobs,
                str(aid),
                quick_edit=quick_edit,
                qe_key=qe_key,
                can_edit=can_edit,
                is_narrow=False,
            )

    if not can_edit:
        st.info("You can view this profile. Admin or estimator role is required for check-out and other actions.")
    else:
        if not quick_edit:
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
        st.caption("Upload images or PDFs, then **Upload photos** or **Run AI autofill**.")
        _up_lbl = (
            "Photos & files"
            if is_narrow
            else "Equipment photos & files (images → **Photos**; PDFs → **Documents**)"
        )
        if is_narrow:
            detail_photos = st.file_uploader(
                _up_lbl,
                type=["pdf", "heic", "jpg", "jpeg", "png", "webp"],
                accept_multiple_files=True,
                key=f"ad_photos_{aid}",
                help="PDF, HEIC, JPG, JPEG, PNG, WEBP. PDFs use rendered pages for AI.",
            )
            st.markdown('<div class="ips-ad-actions-updates">', unsafe_allow_html=True)
            pa1, pa2 = st.columns(2)
            with pa1:
                upload_photos = st.button("Upload photos", key=f"ad_upphotos_{aid}", use_container_width=True)
            with pa2:
                run_ai = st.button("Run AI autofill", key=f"ad_runai_{aid}", use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            _au_u, _au_b = st.columns([2.5, 1])
            with _au_u:
                detail_photos = st.file_uploader(
                    _up_lbl,
                    type=["pdf", "heic", "jpg", "jpeg", "png", "webp"],
                    accept_multiple_files=True,
                    key=f"ad_photos_{aid}",
                    help="Supported: PDF, HEIC, JPG, JPEG, PNG, WEBP. PDFs use rendered pages for AI; HEIC is converted for analysis.",
                )
            with _au_b:
                st.markdown('<div class="ips-ad-actions-updates">', unsafe_allow_html=True)
                upload_photos = st.button("Upload photos", key=f"ad_upphotos_{aid}", use_container_width=True)
                run_ai = st.button("Run AI autofill", key=f"ad_runai_{aid}", use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

        if upload_photos:
            if not detail_photos:
                st.error("Choose one or more photos first.")
            else:
                batch = [{"file_name": f.name, "file_bytes": f.getvalue(), "photo_type": "overview"} for f in detail_photos]
                append_asset_photos(asset, batch, uploaded_by=current_profile().get("id"))
                st.success("Photos saved.")

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

        st.markdown("##### Primary actions")
        st.markdown('<div class="ips-ad-actions-primary">', unsafe_allow_html=True)
        b1, b2 = st.columns(2)
        with b1:
            if st.button("Check out", key=f"ad_co_{aid}", use_container_width=True):
                st.session_state["asset_detail_action"] = "checkout"
        with b2:
            if st.button("Check in", key=f"ad_ci_{aid}", use_container_width=True):
                st.session_state["asset_detail_action"] = "checkin"
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("##### Service & documents")
        st.markdown('<div class="ips-ad-actions-service">', unsafe_allow_html=True)
        s1, s2, s3, s4 = st.columns(4)
        with s1:
            if st.button("Report broken", key=f"ad_rb_{aid}", use_container_width=True):
                st.session_state["asset_detail_action"] = "broken"
        with s2:
            if st.button("Add maintenance", key=f"ad_maint_{aid}", use_container_width=True):
                st.session_state["asset_detail_action"] = "maint"
        with s3:
            if st.button("Add inspection", key=f"ad_insp_{aid}", use_container_width=True):
                st.session_state["asset_detail_action"] = "insp"
        with s4:
            if st.button("Upload document", key=f"ad_doc_{aid}", use_container_width=True):
                st.session_state["asset_detail_action"] = "doc"
        st.markdown("</div>", unsafe_allow_html=True)

        if current_role() == "admin":
            st.markdown("##### Danger zone")
            st.markdown('<div class="ips-ad-actions-danger">', unsafe_allow_html=True)
            (del_col,) = st.columns(1)
            with del_col:
                delete_clicked = st.button("Delete asset", key=f"ad_del_{aid}", use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            delete_clicked = False

        if delete_clicked:
            st.session_state["asset_detail_action"] = "delete"

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

    st.markdown("##### History & notes")
    tab_doc, tab_maint, tab_asg, tab_insp, tab_notes = st.tabs(
        ["Documents", "Maintenance history", "Assignment history", "Inspections", "Notes"]
    )

    with tab_doc:
        st.markdown("##### Documents library")
        st.caption("Same as **Documents** above · signed links expire in about one hour.")
        _render_asset_documents_list(
            merged_documents,
            key_prefix="ad_tab_doc",
            show_hint=False,
            mobile_layout=is_narrow,
        )

    with tab_maint:
        if maintenance:
            show = pd.DataFrame(maintenance)
            drop = [c for c in ("id", "asset_id", "created_by") if c in show.columns]
            if drop:
                show = show.drop(columns=drop, errors="ignore")
            st.dataframe(show, use_container_width=True, hide_index=True)
        else:
            st.caption("No maintenance records.")

    with tab_asg:
        if assignments:
            show = pd.DataFrame(assignments)
            drop = [c for c in ("id", "asset_id", "created_by") if c in show.columns]
            if drop:
                show = show.drop(columns=drop, errors="ignore")
            st.dataframe(show, use_container_width=True, hide_index=True)
        else:
            st.caption("No assignment history.")

    with tab_insp:
        if inspections:
            show = pd.DataFrame(inspections)
            drop = [c for c in ("id", "asset_id", "created_by") if c in show.columns]
            if drop:
                show = show.drop(columns=drop, errors="ignore")
            st.dataframe(show, use_container_width=True, hide_index=True)
        else:
            st.caption("No inspections.")

    with tab_notes:
        if can_edit:
            new_notes = st.text_area("Notes", value=str(asset.get("notes") or ""), height=160, key=f"notes_ed_{aid}")
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