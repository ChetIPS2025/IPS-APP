from __future__ import annotations

import re

import streamlit as st

from db import fetch_one
from proposal import (
    build_proposal_docx,
    proposal_preview_page_html,
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
    if st.session_state.get("_ips_proposal_preview_css_injected_v5"):
        return
    st.markdown(
        """
        <style>
        .ips-proposal-preview-root.ips-proposal-preview-desk {
            box-sizing: border-box;
            width: 100%;
            max-width: 56rem;
            display: flex;
            justify-content: center;
            align-items: flex-start;
            margin: 0.25rem auto 0.75rem auto;
            padding: 0.75rem 0.5rem 1rem;
            background: #e2e8f0;
            border-radius: 8px;
            border: 1px solid #cbd5e1;
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
            border-radius: 2px;
            padding: 0.5in 0.5in 0.55in 0.52in;
            margin: 0 auto;
            border: 1px solid #94a3b8;
            box-shadow:
                0 1px 3px rgba(15, 23, 42, 0.08),
                0 12px 28px rgba(15, 23, 42, 0.12);
            font-family: "Times New Roman", Times, serif;
        }
        .ips-proposal-page .ips-proposal-page-inner {
            box-sizing: border-box;
            width: 100%;
        }
        .ips-proposal-page .ips-ph-logo-wrap {
            text-align: center;
            margin: 0 0 0.35rem 0;
        }
        .ips-proposal-page .ips-ph-logo-img {
            max-width: 100%;
            height: auto;
            display: inline-block;
        }
        .ips-proposal-page .ips-ph-logo-missing {
            min-height: 0.25rem;
        }
        .ips-proposal-page .proposal-header {
            box-sizing: border-box;
            width: 100%;
            background: #1f5d99;
            color: #fff;
            text-align: center;
            padding: 14px 20px;
            margin: 0 0 0.35rem 0;
            font-family: Arial, Helvetica, sans-serif;
        }
        .ips-proposal-page .proposal-header-title {
            font-size: 28px;
            font-weight: 700;
            color: #fff;
        }
        .ips-proposal-page .proposal-header-quote {
            font-size: 20px;
            font-weight: 700;
            color: #fff;
            margin-top: 6px;
        }
        .ips-proposal-page .ips-ph-meta-line {
            font-family: Arial, Helvetica, sans-serif;
            font-size: 11pt;
            border-bottom: 3px double #334155;
            padding: 0.28rem 0.08rem 0.32rem 0.08rem;
            margin: 0;
        }
        .ips-proposal-page .ips-ph-meta-k {
            font-weight: 700;
        }
        .ips-proposal-page .ips-ph-attn-line {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            flex-wrap: wrap;
            align-items: baseline;
        }
        .ips-proposal-page .ips-ph-quote-amt {
            margin-left: auto;
            white-space: nowrap;
        }
        .ips-proposal-page .ips-ph-intro {
            font-family: Calibri, "Segoe UI", Arial, sans-serif;
            font-size: 11pt;
            margin: 0.65rem 0 0.45rem 0;
            line-height: 1.45;
            color: #000000;
        }
        .ips-proposal-page .ips-ph-scope {
            font-family: "Times New Roman", Times, serif;
            font-size: 13.5pt;
            font-weight: 700;
            line-height: 1.45;
            white-space: normal;
            margin: 0.35rem 0 0.6rem 0;
            color: #000000;
        }
        .ips-proposal-page .ips-ph-section-spacer {
            height: 0.85rem;
        }
        .ips-proposal-page .ips-ph-resp-heading {
            font-family: "Times New Roman", Times, serif;
            font-size: 11pt;
            font-weight: 700;
            margin: 0.35rem 0 0.25rem 0;
            color: #000000;
        }
        .ips-proposal-page .ips-ph-resp-body {
            font-family: "Times New Roman", Times, serif;
            font-size: 11pt;
            line-height: 1.45;
            white-space: normal;
            margin: 0 0 0.85rem 0;
            color: #000000;
        }
        .ips-proposal-page .ips-ph-prep-line {
            margin-top: 0.35rem;
        }
        .ips-proposal-page .ips-ph-footer {
            font-family: "Times New Roman", Times, serif;
            font-size: 11pt;
            text-align: center;
            margin: 1rem 0 0 0;
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
            font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
            color: #0f172a;
            border: 1px solid #cbd5e1;
            border-radius: 4px;
            overflow: hidden;
            background: #fff;
        }
        .ips-proposal-fallback-table td {
            padding: 0.4rem 0.55rem;
            vertical-align: top;
            border-bottom: 1px solid #e2e8f0;
            line-height: 1.4;
        }
        .ips-proposal-fallback-table tr:last-child td {
            border-bottom: none;
        }
        .ips-proposal-fallback-label {
            font-weight: 600;
            width: 9.5rem;
            background: #f8fafc;
            color: #475569;
            border-right: 1px solid #e2e8f0;
        }
        .ips-proposal-fallback-val {
            white-space: pre-wrap;
            word-break: break-word;
            color: #0f172a;
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
            border: 1px solid #64748b;
            background: #fff;
        }
        .ips-proposal-docx-td {
            border: 1px solid #94a3b8;
            padding: 0.28rem 0.38rem;
            vertical-align: top;
            color: #000000;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.session_state["_ips_proposal_preview_css_injected_v5"] = True


def _render_proposal_preview_html(html_block: str, *, caption: str | None = None) -> None:
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
        # ``width`` on ``st.html`` is newer than our minimum Streamlit pin; default matches parent width.
        st.html(raw)
    except Exception:
        st.markdown(raw, unsafe_allow_html=True)


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
) -> tuple[dict[str, str], bytes | None, str, str]:
    """
    Shared proposal view for the editor: placeholder map, filled ``.docx`` bytes, build error (if any),
    and **structured** HTML preview from :mod:`app.estimate.proposal_document_layout` (same view model as Word placeholders).

    Download Word / PDF reuse ``docx`` from this tuple; preview HTML uses ``build_proposal_view_model``.
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
    return vals, docx, err, page_html
