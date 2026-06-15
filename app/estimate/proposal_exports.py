from __future__ import annotations

import re

import streamlit as st

from db import fetch_one
from proposal import (
    build_proposal_docx,
    proposal_preview_page_html,
    try_convert_proposal_docx_to_pdf,
)

from app.estimate.customer_job import (
    _fetch_contacts_for_estimate_editor,
    _fetch_customer_row_for_proposal,
)
from app.estimate.defaults import _normalize_prepared_by_id_value
from app.estimate.proposal_document_layout import (
    build_proposal_view_model,
    proposal_placeholder_map_from_view_model,
    render_proposal_preview_page_html,
)

# Shown when Word built OK but server-side PDF conversion is missing (no error/warning box).
PROPOSAL_PDF_UNAVAILABLE_SHORT = "PDF export not available on this server"


def proposal_pdf_preview_pngs(
    pdf_bytes: bytes | None,
    *,
    dpi: int = 115,
    max_pages: int = 8,
) -> list[bytes]:
    """
    Rasterize PDF pages to PNG for on-screen preview.

    Uses the same bytes as **Export PDF**, so the preview matches the Word layout after conversion
    (logo size, margins, typography) more closely than a parallel HTML mock.
    """
    if not pdf_bytes:
        return []
    try:
        import fitz  # type: ignore  # PyMuPDF
    except ImportError:
        return []
    out: list[bytes] = []
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        try:
            n = min(int(doc.page_count or 0), max_pages)
            for i in range(n):
                page = doc.load_page(i)
                pix = page.get_pixmap(dpi=int(dpi), alpha=False)
                out.append(pix.tobytes("png"))
        finally:
            doc.close()
    except Exception:
        return []
    return out


def _lookup_prepared_by_phone(est: dict) -> str:
    """Estimator phone for {{PREPARED_BY_PHONE}} when ``profiles.phone`` exists."""
    pid = _normalize_prepared_by_id_value(str(est.get("prepared_by_id") or ""))
    if not pid.startswith("p:"):
        return ""
    uid = pid[2:].strip()
    if not uid:
        return ""
    try:
        row = fetch_one("profiles", {"id": uid}, columns="id,phone")
        if row and str(row.get("phone") or "").strip():
            return str(row.get("phone") or "").strip()
    except Exception:
        pass
    return ""


def _inject_proposal_preview_styles() -> None:
    """One-time CSS: Word-like page (8.5in) on a light mat + structured quote blocks."""
    if st.session_state.get("_ips_proposal_preview_css_injected_v11"):
        return
    st.markdown(
        """
        <style>
        .ips-proposal-preview-root.ips-proposal-preview-desk {
            box-sizing: border-box;
            width: 100%;
            max-width: 8.75in;
            display: flex;
            justify-content: center;
            align-items: flex-start;
            margin: 0.25rem auto 0.75rem auto;
            padding: 0.5rem 0.35rem;
            background: #ececec;
            border: none;
            border-radius: 0;
            box-shadow: none;
        }
        .ips-proposal-preview-page.ips-proposal-template-page {
            box-sizing: border-box;
            width: 8.5in;
            max-width: 100%;
            min-height: 11in;
            background: #ffffff;
            color: #000000;
            font-size: 11pt;
            line-height: 1.45;
            border-radius: 0;
            /* Match Word template narrow margins (0.5in on all sides). */
            padding: 0.5in;
            margin: 0 auto;
            border: 1px solid #b0b0b0;
            box-shadow: none;
            font-family: "Times New Roman", Times, serif;
        }
        .ips-proposal-page .ips-quote-doc {
            display: flex;
            flex-direction: column;
            min-height: 9.35in;
        }
        .ips-proposal-page .ips-ph-grow-block {
            flex: 1 1 auto;
            display: flex;
            flex-direction: column;
            min-height: 2.35in;
            margin: 0 0 0.08in 0;
        }
        .ips-proposal-page .ips-proposal-page-inner {
            box-sizing: border-box;
            width: 100%;
            max-width: 100%;
        }
        .ips-proposal-page .ips-ph-logo-wrap {
            text-align: center;
            width: 100%;
            margin: 0 0 0.28in 0;
        }
        .ips-proposal-page .ips-ph-logo-img {
            width: 100%;
            max-width: 100%;
            height: auto;
            object-fit: contain;
            display: block;
            margin: 0;
        }
        .ips-proposal-page .ips-ph-logo-missing {
            min-height: 0.35in;
        }
        .ips-proposal-page .proposal-header {
            box-sizing: border-box;
            width: 100%;
            background: #0b4f8a;
            color: #ffffff;
            text-align: center;
            padding: 14px 18px 16px 18px;
            margin: 0 0 0.12in 0;
            font-family: Arial, Helvetica, sans-serif;
            border-radius: 0;
            box-shadow: none;
            letter-spacing: 0.2px;
            -webkit-font-smoothing: antialiased;
        }
        .ips-proposal-page .proposal-header-title {
            color: #ffffff;
            font-size: clamp(1.25rem, 3.2vw, 22pt);
            font-weight: 800;
            font-style: italic;
            margin: 0;
            line-height: 1.15;
            letter-spacing: 0.2px;
        }
        .ips-proposal-page .proposal-header-subtitle,
        .ips-proposal-page .proposal-header-quote {
            color: #ffffff;
            font-size: clamp(1rem, 2.4vw, 14pt);
            font-weight: 700;
            font-style: italic;
            margin: 10px 0 0 0;
            line-height: 1.2;
            letter-spacing: 0.2px;
        }
        .ips-proposal-page .ips-ph-quote-lbl {
            text-decoration: underline;
            text-underline-offset: 2px;
        }
        .ips-proposal-page .proposal-header-subtitle + .proposal-header-subtitle {
            margin-top: 8px;
        }
        .ips-proposal-page .ips-ph-customer-block {
            border-bottom: 3px double #000000;
            padding: 0.12in 0 0.14in 0;
            margin: 0 0 0.14in 0;
        }
        .ips-proposal-page .ips-ph-customer-line {
            font-family: "Times New Roman", Times, serif;
            font-size: 11pt;
            margin: 0 0 0.08in 0;
        }
        .ips-proposal-page .ips-ph-attn-line {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            flex-wrap: wrap;
            align-items: baseline;
            font-family: "Times New Roman", Times, serif;
            font-size: 11pt;
            margin: 0;
        }
        .ips-proposal-page .ips-ph-quote-amt {
            margin-left: auto;
            white-space: nowrap;
        }
        .ips-proposal-page .ips-ph-meta-k {
            font-weight: 700;
        }
        .ips-proposal-page .ips-ph-intro {
            font-family: "Times New Roman", Times, serif;
            font-size: 11pt;
            margin: 0.12in 0 0.12in 0;
            line-height: 1.45;
            color: #000000;
        }
        .ips-proposal-page .ips-ph-ul {
            text-decoration: underline;
            text-underline-offset: 2px;
        }
        .ips-proposal-page .ips-ph-scope {
            font-family: "Times New Roman", Times, serif;
            font-size: 11pt;
            font-weight: 400;
            line-height: 1.5;
            white-space: normal;
            flex: 1 1 auto;
            margin: 0;
            min-height: 1.85in;
            color: #000000;
            word-break: break-word;
        }
        .ips-proposal-page .ips-ph-section-spacer {
            height: 0.08in;
        }
        .ips-proposal-page .ips-ph-resp-heading {
            font-family: "Times New Roman", Times, serif;
            font-size: 12pt;
            font-weight: 700;
            font-style: italic;
            margin: 0.12in 0 0.06in 0;
            color: #000000;
            line-height: 1.35;
        }
        .ips-proposal-page .ips-ph-resp-body {
            font-family: "Times New Roman", Times, serif;
            font-size: 11pt;
            line-height: 1.5;
            white-space: normal;
            margin: 0 0 0.14in 0;
            color: #000000;
        }
        .ips-proposal-page .ips-ph-close-block {
            margin-top: auto;
            padding-top: 0.12in;
        }
        .ips-proposal-page .ips-ph-prep-line,
        .ips-proposal-page .ips-ph-date-line {
            font-family: "Times New Roman", Times, serif;
            font-size: 11pt;
            margin: 0.04in 0;
        }
        .ips-proposal-page .ips-ph-footer-rule {
            border-top: 3px double #000000;
            margin: 0.14in 0 0.1in 0;
            height: 0;
        }
        .ips-proposal-page .ips-ph-footer {
            font-family: "Times New Roman", Times, serif;
            font-size: 11pt;
            font-weight: 700;
            font-style: italic;
            text-align: center;
            margin: 0;
            line-height: 1.45;
            color: #000000;
        }
        .ips-proposal-fields-wrap {
            max-height: min(440px, 48vh);
            overflow: auto;
            margin: 0;
            padding: 0;
            -webkit-overflow-scrolling: touch;
        }
        .ips-proposal-fallback-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.875rem;
            font-family: "Times New Roman", Times, serif;
            color: #000000;
            border: 1px solid #000000;
            border-radius: 0;
            overflow: visible;
            background: #fff;
        }
        .ips-proposal-fallback-table td {
            padding: 0.35rem 0.45rem;
            vertical-align: top;
            border-bottom: 1px solid #000000;
            line-height: 1.4;
        }
        .ips-proposal-fallback-table tr:last-child td {
            border-bottom: 1px solid #000000;
        }
        .ips-proposal-fallback-label {
            font-weight: 700;
            width: 9.5rem;
            background: #ffffff;
            color: #000000;
            border-right: 1px solid #000000;
        }
        .ips-proposal-fallback-val {
            white-space: pre-wrap;
            word-break: break-word;
            color: #000000;
        }
        .ips-proposal-preview-error {
            margin: 0.65rem 0 0 0;
            font-size: 0.875rem;
            font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
            color: #b45309;
            line-height: 1.45;
        }
        .ips-proposal-letterhead {
            font-size: 10pt;
            color: #334155;
            line-height: 1.4;
            margin-bottom: 0.55rem;
            padding-bottom: 0.45rem;
            border-bottom: 1px solid #cbd5e1;
            font-family: "Times New Roman", Times, serif;
        }
        .ips-proposal-docx-body {
            max-height: min(720px, 78vh);
            overflow: auto;
            margin: 0;
            padding: 0;
            font-family: "Times New Roman", Times, serif;
            font-size: 11pt;
            color: #000000;
        }
        .ips-proposal-docx-body p {
            margin: 0.28em 0;
            line-height: 1.45;
            color: #000000;
        }
        .ips-proposal-docx-preview h3 {
            font-size: 12pt;
            font-weight: 700;
            margin: 0.5em 0 0.28em 0;
            line-height: 1.25;
            color: #000000;
            font-family: "Times New Roman", Times, serif;
        }
        .ips-proposal-docx-preview h4 {
            font-size: 11.5pt;
            font-weight: 700;
            margin: 0.45em 0 0.22em 0;
            line-height: 1.25;
            color: #000000;
            font-family: "Times New Roman", Times, serif;
        }
        .ips-proposal-docx-preview h5 {
            font-size: 11pt;
            font-weight: 700;
            margin: 0.38em 0 0.2em 0;
            line-height: 1.25;
            color: #000000;
            font-family: "Times New Roman", Times, serif;
        }
        .ips-proposal-docx-preview p {
            font-family: "Times New Roman", Times, serif;
        }
        .ips-proposal-docx-table {
            width: 100%;
            border-collapse: collapse;
            margin: 0.4em 0;
            font-size: 11pt;
            border: 1px solid #000000;
            background: #fff;
        }
        .ips-proposal-docx-td {
            border: 1px solid #000000;
            padding: 0.28rem 0.38rem;
            vertical-align: top;
            color: #000000;
            line-height: 1.45;
            word-break: break-word;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.session_state["_ips_proposal_preview_css_injected_v11"] = True


def _render_proposal_preview_html(
    html_block: str,
    *,
    caption: str | None = None,
    html_width: int = 920,
) -> None:
    """
    Render proposal HTML using ``st.html`` (Streamlit-native). ``components.html`` iframes and
    ``st.markdown(..., unsafe_allow_html=True)`` both tended to show an empty/white panel for this
    content while the Word download was correct.
    """
    _inject_proposal_preview_styles()
    if caption:
        st.caption(caption)
    raw = html_block or ""
    plain = re.sub(r"<[^>]+>", " ", raw)
    plain = re.sub(r"\s+", " ", plain).strip()
    if not plain:
        st.info(
            "Proposal preview has no readable content. "
            "Use **Download Proposal (Word)** — the file matches this estimate."
        )
        return
    try:
        # Constrain width so Streamlit does not stretch the document to full app width.
        st.html(raw, width=html_width)
    except TypeError:
        try:
            st.html(raw)
        except Exception:
            st.markdown(raw, unsafe_allow_html=True)
    except Exception:
        st.markdown(raw, unsafe_allow_html=True)


def _render_proposal_document_preview(
    pdf_bytes: bytes | None,
    html_block: str,
    *,
    caption: str | None = None,
    html_width: int = 900,
    compact: bool = False,
) -> None:
    """
    Prefer rasterizing the **filled proposal PDF** (same bytes as Export PDF) so the preview
    tracks the packaged Word template 1:1. Falls back to structured HTML when PDF is unavailable.
    """
    pngs = proposal_pdf_preview_pngs(pdf_bytes)
    if pngs:
        _inject_proposal_preview_styles()
        if caption:
            st.caption(caption)
        if not compact:
            st.caption(
                "Preview is rendered from the **same PDF** as **Export PDF** (filled Word → PDF), "
                "so layout, logo size, and spacing match the downloaded document."
            )
        _l, _c, _r = st.columns([0.06, 1.0, 0.06])
        with _c:
            for buf in pngs:
                st.image(buf, use_container_width=True)
        return
    _render_proposal_preview_html(html_block, caption=caption, html_width=html_width)


def _normalize_contact_placeholder_text(val) -> str:
    """Strip and drop literal 'none' / empty so {{CONTACT_NAME}} / Attn never show junk."""
    if val is None:
        return ""
    t = str(val).strip()
    if not t:
        return ""
    if t.lower() in ("none", "null"):
        return ""
    return t


def _proposal_contact_name_for_export(est: dict) -> str:
    """
    Display name for proposal {{CONTACT_NAME}} (Attn).

    Prefer ``est['contact_name']`` (kept in sync with the Contact picker). Otherwise resolve
    ``customer_contact_id`` using the same contact list fetch as the UI (RLS-aware), then
    fall back to a direct ``customer_contacts`` row read.
    """
    t = _normalize_contact_placeholder_text(est.get("contact_name"))
    if t:
        return t
    ccid = str(est.get("customer_contact_id") or "").strip()
    cid = str(est.get("customer_id") or "").strip()
    if not ccid or not cid:
        return ""
    try:
        loc = str(est.get("customer_location_id") or "").strip() or None
        for r in _fetch_contacts_for_estimate_editor(cid, loc):
            if str(r.get("id") or "").strip() == ccid:
                return _normalize_contact_placeholder_text(r.get("contact_name"))
    except Exception:
        pass
    try:
        crow = fetch_one("customer_contacts", {"id": ccid}, columns="id,contact_name")
        if crow:
            return _normalize_contact_placeholder_text(crow.get("contact_name"))
    except Exception:
        pass
    return ""


def _proposal_export_kwargs(est: dict, customer_name_by_id: dict, jobs: list) -> dict:
    """Shared context for Word/PDF proposal generation (same DOCX template + placeholders)."""
    cid = str(est.get("customer_id") or "").strip()
    cust_row = _fetch_customer_row_for_proposal(cid) if cid else None
    cust_name = customer_name_by_id.get(cid, "") or (
        str(cust_row.get("customer_name") or "").strip() if cust_row else ""
    )
    jid = est.get("job_id")
    job_name = ""
    for j in jobs:
        if j.get("id") == jid:
            job_name = str(j.get("job_name") or "").strip()
            break
    contact_name = _proposal_contact_name_for_export(est)
    phone = _lookup_prepared_by_phone(est)
    return {
        "customer_name": cust_name,
        "job_name": job_name,
        "contact_name": contact_name,
        "prepared_by_phone": phone,
    }


def build_proposal_view_bundle(
    est: dict,
    totals: dict,
    pe: dict,
) -> tuple[dict[str, str], bytes | None, str, str, bytes | None]:
    """
    Shared proposal view for the editor: placeholder map, filled ``.docx`` bytes, build error (if any),
    structured HTML preview, and optional **PDF bytes** (same pipeline as Export PDF).

    When PDF conversion succeeds, the UI should rasterize those bytes for a pixel-accurate preview.
    """
    vm = build_proposal_view_model(
        est,
        totals,
        customer_name=pe["customer_name"],
        job_name=pe["job_name"],
        contact_name=pe["contact_name"],
        prepared_by_phone=pe["prepared_by_phone"],
    )
    vals = proposal_placeholder_map_from_view_model(vm)
    page_html = render_proposal_preview_page_html(vm)
    try:
        docx = build_proposal_docx(est, totals, placeholder_values=vals)
        err = ""
    except FileNotFoundError as e:
        docx = None
        err = str(e)
    except Exception as e:
        docx = None
        err = f"Could not build the Word proposal: {type(e).__name__}: {e}"
    pdf_b: bytes | None = None
    if docx:
        pdf_b, _note = try_convert_proposal_docx_to_pdf(docx)
    return vals, docx, err, page_html, pdf_b
