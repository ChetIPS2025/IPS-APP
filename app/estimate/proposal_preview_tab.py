"""Single-path proposal tab preview: one HTML builder + markdown renderer (no PDF raster, no expander)."""
from __future__ import annotations

import html
from typing import Any

import streamlit as st

from app.estimate.persistence import upload_generated_export
from app.estimate.proposal_document_layout import build_proposal_view_model
from app.estimate.proposal_exports import PROPOSAL_PDF_UNAVAILABLE_SHORT


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
        "_docx_bytes": docx_bytes,
        "_pdf_bytes": pdf_bytes,
        "_word_error": word_error,
        "_loaded_estimate_id": loaded_estimate_id,
        "_is_locked": is_locked,
    }


def build_proposal_html(estimate_data: dict[str, Any]) -> str:
    """
    One HTML document card for the on-screen preview (inline styles; no logo; no st.columns).
    """
    title = html.escape(str(estimate_data.get("estimate_description") or "Project"))
    qn = html.escape(str(estimate_data.get("quote_number") or ""))
    cust = html.escape(str(estimate_data.get("customer") or ""))
    contact = html.escape(str(estimate_data.get("contact") or "—"))
    amt = html.escape(str(estimate_data.get("proposal_total") or "$0.00"))
    scope = (estimate_data.get("scope_of_work") or "").strip()
    scope_esc = html.escape(scope, quote=False).replace("\n", "<br/>") if scope else "—"
    resp = (estimate_data.get("customer_responsibilities") or "").strip()
    resp_esc = html.escape(resp, quote=False).replace("\n", "<br/>") if resp else ""
    prep = html.escape(str(estimate_data.get("prepared_by") or ""))
    dt = html.escape(str(estimate_data.get("date") or ""))
    phone = html.escape(str(estimate_data.get("footer_phone") or "(337) 577-3944"))

    resp_block = ""
    if resp_esc and resp_esc != "—":
        resp_block = f"""
        <div style="margin-top:18px;">
            <div style="font-weight:800;border-bottom:1px solid #999;padding-bottom:4px;margin-bottom:8px;">Responsibilities</div>
            <div style="line-height:1.45;">{resp_esc}</div>
        </div>"""

    return f"""
<div style="max-width:850px;margin:16px auto;background:#ffffff;color:#000000;padding:40px 44px;border:1px solid #d0d0d0;box-shadow:0 2px 10px rgba(0,0,0,0.12);font-family:Arial,Calibri,sans-serif;line-height:1.45;">
    <div style="background:#0b5f9e;color:#ffffff;text-align:center;padding:14px 20px;margin-bottom:22px;">
        <div style="color:#ffffff;font-weight:800;font-size:22px;margin-bottom:8px;">{title} – Quote</div>
        <div style="color:#ffffff;font-weight:800;font-size:18px;">Quote #: {qn}</div>
    </div>
    <div style="display:flex;justify-content:space-between;gap:24px;margin-bottom:12px;flex-wrap:wrap;">
        <div><span style="font-weight:700;">Customer:</span> {cust}</div>
        <div><span style="font-weight:700;">Quote Amt:</span> {amt}</div>
    </div>
    <div style="margin-bottom:12px;"><span style="font-weight:700;">Contact:</span> {contact}</div>
    <div style="margin-top:18px;line-height:1.45;">
        Industrial Plant <span style="text-decoration:underline;text-underline-offset:2px;">Solutions</span>, LLC (IPS) proposes to perform the following scope of work:
    </div>
    <div style="margin-top:18px;">
        <div style="font-weight:800;border-bottom:1px solid #999;padding-bottom:4px;margin-bottom:8px;">Scope</div>
        <div style="line-height:1.45;">{scope_esc}</div>
    </div>
    {resp_block}
    <div style="margin-top:28px;">
        <p style="margin:6px 0;"><span style="font-weight:700;">Prepared By:</span> {prep}</p>
        <p style="margin:6px 0;"><span style="font-weight:700;">Date:</span> {dt}</p>
        <p style="margin:12px 0 0 0;">If you have any questions regarding this Quote, please contact {prep} at {phone}.</p>
    </div>
</div>
""".strip()


def render_proposal_document_preview(estimate_data: dict[str, Any]) -> None:
    """
    Render the on-screen proposal preview using the same field values as the Word export.
    This is the only preview renderer for the Proposal tab.
    """
    h = build_proposal_html(estimate_data)
    st.markdown(h, unsafe_allow_html=True)


def render_proposal_tab(estimate_data: dict[str, Any]) -> None:
    """
    Render Proposal tab controls and preview (single session key ``proposal_preview_open``).
    """
    if "proposal_preview_open" not in st.session_state:
        st.session_state["proposal_preview_open"] = False

    docx = estimate_data.get("_docx_bytes")
    pdf_b = estimate_data.get("_pdf_bytes")
    err = str(estimate_data.get("_word_error") or "")
    loaded_id = estimate_data.get("_loaded_estimate_id")
    locked = bool(estimate_data.get("_is_locked"))
    slug = str(estimate_data.get("quote_file_slug") or "proposal")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Preview", key="proposal_preview_btn", use_container_width=True):
            st.session_state["proposal_preview_open"] = True
            st.rerun()
    with c2:
        st.download_button(
            "Export Word",
            data=docx if isinstance(docx, (bytes, bytearray)) and docx else b"",
            file_name=f"{slug}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
            type="primary",
            disabled=not docx,
            key="proposal_export_word_btn",
        )

    row2 = st.columns([1, 1, 1, 1], gap="small")
    with row2[0]:
        st.download_button(
            "Export PDF",
            data=pdf_b if pdf_b else b"",
            file_name=f"{slug}.pdf",
            mime="application/pdf",
            use_container_width=True,
            disabled=not pdf_b,
            key="proposal_export_pdf_btn",
        )
    if loaded_id:
        with row2[1]:
            if st.button(
                "Save Word to cloud",
                use_container_width=True,
                key="proposal_save_word_cloud_btn",
                disabled=locked,
            ):
                if not docx:
                    st.caption("Build the Word proposal first (check the standard template file).")
                else:
                    upload_generated_export(
                        str(loaded_id),
                        f"{slug}.docx",
                        docx,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        "generated_docx",
                    )
                    st.success("Word proposal saved to Supabase Storage.")
        with row2[2]:
            if st.button(
                "Save PDF to cloud",
                use_container_width=True,
                key="proposal_save_pdf_cloud_btn",
                disabled=locked or not pdf_b,
            ):
                if pdf_b:
                    upload_generated_export(
                        str(loaded_id),
                        f"{slug}.pdf",
                        pdf_b,
                        "application/pdf",
                        "generated_pdf",
                    )
                    st.success("PDF saved to storage and linked to this estimate.")

    if err:
        st.error(err)
    elif not pdf_b and docx:
        st.caption(PROPOSAL_PDF_UNAVAILABLE_SHORT)
    if not docx:
        st.caption("Ensure **assets/estimate_template_autofill_logo_updated.docx** exists in the app bundle.")

    with st.expander("Template & export notes", expanded=False):
        st.caption(
            "Downloads use the same **estimate_template_autofill_logo_updated.docx** pipeline as before. "
            "The **Preview** above is a single HTML summary aligned to the same field values."
        )

    if st.session_state["proposal_preview_open"]:
        if st.button("Hide Preview", key="proposal_hide_preview_btn", use_container_width=True):
            st.session_state["proposal_preview_open"] = False
            st.rerun()
        render_proposal_document_preview(estimate_data)
