"""PDF / Word / download export actions for the Estimating module.

All functions accept a ``estimate_data`` dict produced by
estimates.preview.build_estimate_data_for_preview() (or the equivalent
build_proposal_tab_estimate_data() call from proposal_preview_tab.py).

This module does NOT duplicate any build logic — it delegates to the
canonical export helpers in app.estimate.proposal_preview_tab and
app.estimate.proposal_exports.
"""
from __future__ import annotations

from typing import Any

import streamlit as st


def render_export_actions(estimate_data: dict[str, Any]) -> None:
    """Render Download Word / Download PDF + optional cloud-save buttons.

    Delegates to the single canonical implementation in proposal_preview_tab.
    """
    from app.estimate.proposal_preview_tab import render_proposal_export_actions

    render_proposal_export_actions(estimate_data)


def build_proposal_bundle(
    est: dict[str, Any],
    totals: dict[str, Any],
    *,
    customer_name: str,
    job_name: str,
    contact_name: str,
    prepared_by_phone: str,
) -> tuple[dict[str, str], bytes | None, str, str, bytes | None]:
    """Build the proposal DOCX + PDF bundle.

    Returns (placeholder_map, docx_bytes, error_str, html_str, pdf_bytes).
    Delegates to the canonical build_proposal_view_bundle in proposal_exports.py.
    """
    from app.estimate.proposal_exports import build_proposal_view_bundle

    pe = {
        "customer_name": customer_name,
        "job_name": job_name,
        "contact_name": contact_name,
        "prepared_by_phone": prepared_by_phone,
    }
    return build_proposal_view_bundle(est, totals, pe)


def get_proposal_export_kwargs(
    est: dict[str, Any],
    customer_name_by_id: dict[str, str],
    jobs: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return the export context dict (customer_name, job_name, contact_name, phone).

    Delegates to _proposal_export_kwargs in proposal_exports.py.
    """
    from app.estimate.proposal_exports import _proposal_export_kwargs

    return _proposal_export_kwargs(est, customer_name_by_id, jobs)
