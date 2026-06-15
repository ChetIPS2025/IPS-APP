"""Single-path proposal tab preview: canonical Word-aligned HTML (same as Estimate Builder Proposal tab)."""
from __future__ import annotations

from typing import Any

import streamlit as st

from app.estimate.persistence import upload_generated_export
from app.estimate.proposal_document_layout import (
    ProposalViewModel,
    build_proposal_view_model,
    render_proposal_preview_page_html,
)
from app.estimate.proposal_exports import PROPOSAL_PDF_UNAVAILABLE_SHORT, _inject_proposal_preview_styles


def build_proposal_tab_estimate_data(
    est: dict,
    totals: dict,
    pe: dict[str, Any],
    *,
    docx_bytes: bytes | None,
    pdf_bytes: bytes | None,
    word_error: str,
    loaded_estimate_id: str | None,
    is_locked: bool,
) -> dict[str, Any]:
    """Flatten estimate + export context into one dict for HTML + tab actions."""
    vm = build_proposal_view_model(
        est,
        totals,
        customer_name=pe["customer_name"],
        job_name=pe["job_name"],
        contact_name=pe["contact_name"],
        prepared_by_phone=pe["prepared_by_phone"],
    )
    slug = str(est.get("quote_number") or "proposal").strip() or "proposal"
    return {
        "estimate_description": vm.job_title_token,
        "quote_number": vm.quote_number,
        "customer": vm.customer_name,
        "contact": vm.contact_name if vm.contact_name else "—",
        "proposal_total": vm.proposal_amount,
        "scope_of_work": vm.scope_of_work,
        "customer_responsibilities": vm.customer_responsibilities,
        "prepared_by": vm.prepared_by,
        "date": vm.date_display,
        "footer_phone": vm.prepared_by_phone,
        "quote_file_slug": slug,
        "_vm": vm,
        "_docx_bytes": docx_bytes,
        "_pdf_bytes": pdf_bytes,
        "_word_error": word_error,
        "_loaded_estimate_id": loaded_estimate_id,
        "_is_locked": is_locked,
    }


def render_proposal_document_preview(estimate_data: dict[str, Any]) -> None:
    """
    Render the on-screen proposal preview using the same layout as Word/PDF export.

    Uses ``st.markdown`` with injected CSS so scope text cannot break Markdown parsing.
    """
    vm = estimate_data.get("_vm")
    if not isinstance(vm, ProposalViewModel):
        vm = None
    _inject_proposal_preview_styles()
    page_html = render_proposal_preview_page_html(vm)
    if not page_html.strip():
        st.info("No preview content for this estimate.")
        return
    st.markdown(page_html, unsafe_allow_html=True)


def render_proposal_export_actions(estimate_data: dict[str, Any]) -> None:
    """Downloads and cloud saves — single place (**Review / Save**)."""
    docx = estimate_data.get("_docx_bytes")
    pdf_b = estimate_data.get("_pdf_bytes")
    err = str(estimate_data.get("_word_error") or "")
    loaded_id = estimate_data.get("_loaded_estimate_id")
    locked = bool(estimate_data.get("_is_locked"))
    slug = str(estimate_data.get("quote_file_slug") or "proposal")

    r1, r2 = st.columns(2, gap="small")
    with r1:
        st.download_button(
            "Download Word",
            data=docx if isinstance(docx, (bytes, bytearray)) and docx else b"",
            file_name=f"{slug}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
            type="primary",
            disabled=not docx,
            key="proposal_export_word_review",
        )
    with r2:
        st.download_button(
            "Download PDF",
            data=pdf_b if pdf_b else b"",
            file_name=f"{slug}.pdf",
            mime="application/pdf",
            use_container_width=True,
            disabled=not pdf_b,
            key="proposal_export_pdf_review",
        )

    if loaded_id and docx and not locked:
        u1, u2 = st.columns(2, gap="small")
        with u1:
            if st.button("Save Word to library", use_container_width=True, key="proposal_save_word_cloud_review"):
                upload_generated_export(
                    str(loaded_id),
                    f"{slug}.docx",
                    docx,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "generated_docx",
                )
                st.success("Word saved to storage.")
        with u2:
            if st.button("Save PDF to library", use_container_width=True, key="proposal_save_pdf_cloud_review"):
                try:
                    from proposal import try_convert_proposal_docx_to_pdf
                except ImportError:
                    from app.proposal import try_convert_proposal_docx_to_pdf  # type: ignore

                epdf = pdf_b
                if epdf is None and docx is not None:
                    epdf, _conv = try_convert_proposal_docx_to_pdf(docx)
                if epdf is None:
                    st.warning(PROPOSAL_PDF_UNAVAILABLE_SHORT)
                else:
                    upload_generated_export(
                        str(loaded_id),
                        f"{slug}.pdf",
                        epdf,
                        "application/pdf",
                        "generated_pdf",
                    )
                    st.success("PDF saved to storage.")

    if err:
        st.error(err)
    elif not pdf_b and docx:
        st.caption(PROPOSAL_PDF_UNAVAILABLE_SHORT)


def render_proposal_tab(estimate_data: dict[str, Any]) -> None:
    """Proposal tab: always show the Word-aligned quote preview. Exports live under **Review / Save**."""
    render_proposal_document_preview(estimate_data)
