"""Customer-facing estimate proposal export (IPS quote letter template)."""

from __future__ import annotations

from typing import Any

from app.estimate.proposal_document_layout import render_proposal_preview_page_html
from app.estimate.proposal_exports import (
    PROPOSAL_PDF_UNAVAILABLE_SHORT,
    _lookup_prepared_by_phone,
    _proposal_contact_name_for_export,
    build_proposal_view_bundle,
)


def _text(val: Any, default: str = "") -> str:
    s = str(val or "").strip()
    return s if s else default


def _merge_proposal_estimate(estimate: dict[str, Any], estimate_id: str) -> dict[str, Any]:
    """Map Phase 2B estimate fields onto the legacy proposal export shape."""
    out = dict(estimate)
    out["quote_number"] = _text(out.get("quote_number") or out.get("estimate_number"))
    out["prepared_by_name"] = _text(out.get("prepared_by_name") or out.get("created_by") or out.get("prepared_by"))
    out["scope_of_work"] = _text(out.get("scope_of_work") or out.get("description"))
    out["estimate_description"] = _text(out.get("estimate_description") or out.get("project_name"))
    out["customer_name"] = _text(out.get("customer_name") or out.get("customer"))
    if not out.get("contact_name"):
        out["contact_name"] = _proposal_contact_name_for_export(out)

    eid = _text(estimate_id or out.get("id"))
    if eid:
        try:
            from db import fetch_one
        except ImportError:
            from app.db import fetch_one  # type: ignore

        try:
            row = fetch_one(
                "estimates",
                {"id": eid},
                columns=(
                    "id,quote_number,scope_of_work,customer_responsibilities,estimate_description,"
                    "prepared_by_id,prepared_by_name,customer_id,customer_contact_id,contact_name,job_id"
                ),
            )
        except Exception:
            row = None
        if row:
            for key in (
                "quote_number",
                "scope_of_work",
                "customer_responsibilities",
                "estimate_description",
                "prepared_by_id",
                "prepared_by_name",
                "customer_id",
                "customer_contact_id",
                "contact_name",
                "job_id",
            ):
                if row.get(key) not in (None, ""):
                    out[key] = row[key]
            if not out.get("contact_name"):
                out["contact_name"] = _proposal_contact_name_for_export(out)

    return out


def _totals_for_proposal(totals: dict[str, Any]) -> dict[str, Any]:
    """Legacy proposal layout expects ``proposal_total`` (Phase 2 costing uses ``customer_price``)."""
    merged = dict(totals)
    if merged.get("proposal_total") in (None, "", 0):
        merged["proposal_total"] = merged.get("customer_price") or merged.get("total") or 0
    return merged


def _proposal_context(est: dict[str, Any]) -> dict[str, str]:
    job_name = _text(est.get("project_name") or est.get("job_name"))
    if not job_name and est.get("job_id"):
        jid = str(est.get("job_id") or "").strip()
        try:
            from db import fetch_one
        except ImportError:
            from app.db import fetch_one  # type: ignore

        try:
            job = fetch_one("jobs", {"id": jid}, columns="id,job_name")
            if job:
                job_name = _text(job.get("job_name"))
        except Exception:
            pass
    return {
        "customer_name": _text(est.get("customer_name") or est.get("customer")),
        "job_name": job_name,
        "contact_name": _proposal_contact_name_for_export(est),
        "prepared_by_phone": _lookup_prepared_by_phone(est),
    }


def build_customer_quote_bundle(
    estimate_id: str,
    estimate: dict[str, Any],
    *,
    totals: dict[str, Any] | None = None,
) -> tuple[bytes | None, bytes | None, str, str, str]:
    """
    Build customer quote exports from the IPS Word template + shared view model.

    Returns ``(docx_bytes, pdf_bytes, html_preview, word_error, pdf_note)``.
    """
    from app.services.estimate_costing_service import calculate_estimate_totals

    est = _merge_proposal_estimate(estimate, estimate_id)
    calc = _totals_for_proposal(totals or calculate_estimate_totals(str(estimate_id or est.get("id") or "")))
    pe = _proposal_context(est)
    _vals, docx, err, page_html, pdf_b = build_proposal_view_bundle(est, calc, pe)
    pdf_note = "" if pdf_b else PROPOSAL_PDF_UNAVAILABLE_SHORT
    return docx, pdf_b, page_html, err, pdf_note


def generate_estimate_proposal_pdf(
    estimate: dict[str, Any],
    line_items: dict[str, list[dict[str, Any]]] | None = None,
    *,
    company_profile: dict[str, Any] | None = None,
    terms_text: str | None = None,
) -> bytes:
    """Build a customer-facing proposal PDF using the IPS quote letter template."""
    del line_items, company_profile, terms_text  # template is fixed letter layout
    eid = str(estimate.get("id") or "").strip()
    _docx, pdf_b, _html, err, pdf_note = build_customer_quote_bundle(eid, estimate)
    if pdf_b:
        return pdf_b
    if _docx:
        raise RuntimeError(pdf_note or PROPOSAL_PDF_UNAVAILABLE_SHORT)
    raise RuntimeError(err or pdf_note or "Could not build customer quote PDF.")


def generate_estimate_proposal_pdf_by_id(estimate_id: str, estimate: dict[str, Any]) -> bytes:
    _docx, pdf_b, _html, err, pdf_note = build_customer_quote_bundle(estimate_id, estimate)
    if pdf_b:
        return pdf_b
    if _docx:
        raise RuntimeError(pdf_note or PROPOSAL_PDF_UNAVAILABLE_SHORT)
    raise RuntimeError(err or pdf_note or "Could not build customer quote PDF.")
