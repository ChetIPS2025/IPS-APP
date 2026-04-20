from __future__ import annotations

import re

import streamlit as st

from db import fetch_one
from proposal import build_proposal_docx, proposal_preview_html, proposal_values

from app.estimate.customer_job import (
    _fetch_contacts_for_estimate_editor,
    _fetch_customer_row_for_proposal,
)
from app.estimate.defaults import _normalize_prepared_by_id_value

# Shown when Word built OK but server-side PDF conversion is missing (no error/warning box).
PROPOSAL_PDF_UNAVAILABLE_SHORT = "PDF export not available on this server"


def _format_customer_location_line(row: dict | None) -> str:
    """Single-line location for {{CUSTOMER_LOCATION}} (matches Customers tab field names)."""
    if not row:
        return ""

    def _first(keys: tuple[str, ...]) -> str:
        for k in keys:
            v = row.get(k)
            if v is not None and str(v).strip():
                return str(v).strip()
        return ""

    addr = _first(("address", "street_address", "address_line1", "line1"))
    city = _first(("city",))
    state = _first(("state", "region", "province"))
    z = _first(("zip", "zip_code", "postal_code", "postcode"))
    parts: list[str] = []
    if addr:
        parts.append(addr)
    cs = ", ".join(p for p in (city, state) if p)
    if cs:
        parts.append(cs)
    if z:
        parts.append(z)
    return ", ".join(parts)


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
    """One-time CSS: proposal preview as a centered document on a dark workspace (see :mod:`app.proposal`)."""
    if st.session_state.get("_ips_proposal_preview_css_injected_v2"):
        return
    st.markdown(
        """
        <style>
        /* Narrow dark mat — one sheet of paper, not a full-width panel */
        .ips-proposal-preview-root.ips-proposal-preview-desk {
            box-sizing: border-box;
            width: 100%;
            max-width: 30rem;
            display: flex;
            justify-content: center;
            align-items: flex-start;
            margin: 0.1rem auto 0.35rem auto;
            padding: 0.45rem 0.4rem 0.55rem;
            background: #0f172a;
            border-radius: 6px;
            border: 1px solid rgba(255, 255, 255, 0.06);
        }
        .ips-proposal-preview-page {
            box-sizing: border-box;
            width: 100%;
            max-width: 26.25rem;
            background: #ffffff;
            color: #0f172a;
            font-size: 14px;
            line-height: 1.58;
            border-radius: 2px;
            padding: 1.45rem 1.6rem 1.6rem;
            margin: 0 auto;
            border: 1px solid #d1d5db;
            box-shadow:
                0 1px 2px rgba(15, 23, 42, 0.05),
                0 6px 20px rgba(15, 23, 42, 0.1);
            font-family: Georgia, "Times New Roman", serif;
        }
        .ips-proposal-intro {
            margin: 0 0 0.7rem 0;
            font-size: 0.78rem;
            font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
            letter-spacing: 0.01em;
            color: #64748b;
            line-height: 1.4;
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
        .ips-proposal-doc-section {
            margin-top: 0.85rem;
            padding-top: 0.75rem;
            border-top: 1px solid #e5e7eb;
        }
        .ips-proposal-section-hint {
            margin: 0 0 0.45rem 0;
            font-size: 0.75rem;
            font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
            line-height: 1.4;
        }
        .ips-proposal-section-hint--muted { color: #64748b; }
        .ips-proposal-section-hint--soft { color: #78716c; }
        .ips-proposal-preview-error {
            margin: 0.65rem 0 0 0;
            font-size: 0.8125rem;
            font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
            color: #b45309;
            line-height: 1.4;
        }
        .ips-proposal-letterhead {
            font-size: 0.8125rem;
            color: #475569;
            line-height: 1.4;
            margin-bottom: 0.65rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid #e5e7eb;
            font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
        }
        .ips-proposal-docx-body {
            max-height: min(680px, 72vh);
            overflow: auto;
            margin: 0;
            padding: 0;
            font-family: Georgia, "Times New Roman", serif;
            color: #1e293b;
        }
        .ips-proposal-docx-body p {
            margin: 0.32em 0;
            line-height: 1.58;
            color: #1e293b;
        }
        .ips-proposal-docx-preview h3 {
            font-size: 1rem;
            font-weight: 650;
            margin: 0.55em 0 0.3em 0;
            line-height: 1.32;
            color: #0f172a;
            font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
        }
        .ips-proposal-docx-preview h4 {
            font-size: 0.9375rem;
            font-weight: 600;
            margin: 0.48em 0 0.26em 0;
            line-height: 1.32;
            color: #0f172a;
            font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
        }
        .ips-proposal-docx-preview h5 {
            font-size: 0.875rem;
            font-weight: 600;
            margin: 0.4em 0 0.22em 0;
            line-height: 1.32;
            color: #1e293b;
            font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
        }
        .ips-proposal-docx-preview p {
            font-family: Georgia, "Times New Roman", serif;
        }
        .ips-proposal-docx-table {
            width: 100%;
            border-collapse: collapse;
            margin: 0.45em 0;
            font-size: 0.92em;
            border: 1px solid #94a3b8;
            border-radius: 3px;
            overflow: hidden;
            background: #fff;
        }
        .ips-proposal-docx-td {
            border: 1px solid #cbd5e1;
            padding: 0.35rem 0.45rem;
            vertical-align: top;
            color: #1e293b;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.session_state["_ips_proposal_preview_css_injected_v2"] = True


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
        for r in _fetch_contacts_for_estimate_editor(cid):
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
    location = _format_customer_location_line(cust_row)
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
        "customer_location": location,
        "contact_name": contact_name,
        "prepared_by_phone": phone,
    }


def _build_proposal_docx_and_vals(
    est: dict,
    totals: dict,
    pe: dict,
) -> tuple[dict[str, str], bytes | None, str]:
    """
    Single proposal pipeline: :func:`proposal_values` once, then :func:`build_proposal_docx` with those
    values so preview and download use the same DOCX bytes.
    """
    vals = proposal_values(est, totals, **pe)
    try:
        docx = build_proposal_docx(est, totals, placeholder_values=vals)
        return vals, docx, ""
    except FileNotFoundError as e:
        return vals, None, str(e)
    except Exception as e:
        return vals, None, f"Could not build the Word proposal: {type(e).__name__}: {e}"
