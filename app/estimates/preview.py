"""Single-source proposal preview renderer for the Estimating module.

Design principle: ONE preview system.
--------------------------------------
Both the Proposal tab and the Review/Save tab use render_estimate_preview(),
which delegates to the canonical HTML builder in app.estimate.proposal_preview_tab.
This eliminates duplicate preview logic and ensures on-screen preview matches
the Word/PDF export exactly.

The HTML builder (build_proposal_html) uses build_proposal_view_model() internally,
so the preview and the Word document always pull from the same field mapping.

Notes
-----
- Customer location is intentionally excluded from the rendered proposal (matches
  the Word template design).
- The "Estimate Description" field maps to "Project" in the proposal title when set.
  If empty, falls back to Job name, then to the literal string "Project".
"""
from __future__ import annotations

from typing import Any

import streamlit as st


# ---------------------------------------------------------------------------
# Build helpers (thin wrappers; keep imports lazy to avoid circular deps)
# ---------------------------------------------------------------------------

def build_estimate_data_for_preview(
    est: dict[str, Any],
    totals: dict[str, Any],
    *,
    customer_name: str,
    job_name: str,
    contact_name: str,
    prepared_by_phone: str,
    docx_bytes: bytes | None = None,
    pdf_bytes: bytes | None = None,
    word_error: str = "",
    loaded_estimate_id: str | None = None,
    is_locked: bool = False,
) -> dict[str, Any]:
    """Flatten estimate + export context into a single preview data dict.

    This is the single source of truth for what the proposal preview shows.
    Both the Proposal tab and the Review/Save tab call this function.
    """
    from app.estimate.proposal_preview_tab import build_proposal_tab_estimate_data

    return build_proposal_tab_estimate_data(
        est,
        totals,
        {
            "customer_name": customer_name,
            "job_name": job_name,
            "contact_name": contact_name,
            "prepared_by_phone": prepared_by_phone,
        },
        docx_bytes=docx_bytes,
        pdf_bytes=pdf_bytes,
        word_error=word_error,
        loaded_estimate_id=loaded_estimate_id,
        is_locked=is_locked,
    )


def render_estimate_preview(estimate_data: dict[str, Any]) -> None:
    """Render the on-screen proposal preview (HTML card matching Word export).

    Uses the same field values as the Word document so layout and content are
    consistent.  Customer location is not shown (matches Word template).
    """
    from app.estimate.proposal_preview_tab import render_proposal_document_preview

    render_proposal_document_preview(estimate_data)


def render_proposal_tab(estimate_data: dict[str, Any]) -> None:
    """Proposal tab: Show/hide preview button + preview panel.

    Delegates to the canonical implementation in proposal_preview_tab.py.
    """
    from app.estimate.proposal_preview_tab import render_proposal_tab as _render

    _render(estimate_data)


def render_proposal_page_html(
    est: dict[str, Any],
    totals: dict[str, Any],
    *,
    customer_name: str,
    job_name: str,
    contact_name: str,
    prepared_by_phone: str,
) -> str:
    """Return the Word-aligned HTML preview string.

    Delegates to the CSS-rich renderer in proposal_exports.py / proposal_document_layout.py.
    """
    try:
        from app.estimate.proposal_exports import build_proposal_view_bundle, _proposal_export_kwargs
        from app.estimate.proposal_preview_tab import build_proposal_html, build_proposal_tab_estimate_data

        pe = {
            "customer_name": customer_name,
            "job_name": job_name,
            "contact_name": contact_name,
            "prepared_by_phone": prepared_by_phone,
        }
        _, docx, err, _live, pdf_b = build_proposal_view_bundle(est, totals, pe)
        pdata = build_proposal_tab_estimate_data(
            est, totals, pe,
            docx_bytes=docx,
            pdf_bytes=pdf_b,
            word_error=str(err or ""),
            loaded_estimate_id=None,
            is_locked=True,
        )
        return build_proposal_html(pdata)
    except Exception:
        return ""
