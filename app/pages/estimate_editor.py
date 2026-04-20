from __future__ import annotations

"""Estimate editor page — re-exports from :mod:`app.estimate` for backward compatibility."""

from app.estimate.calculations import compute_totals, money_db, money_str
from app.estimate.defaults import (
    blank_estimate,
    coalesce_imported_estimate,
    ensure_numeric_defaults,
    merge_estimate_row_scalar_fields_into_editor,
    parse_estimate_json_bytes,
)
from app.estimate.editor import ensure_state, render, render_estimate_editor
from app.estimate.equipment import load_estimate_equipment_from_assets
from app.estimate.persistence import (
    attach_pending_pdf_import_source,
    insert_imported_estimate,
    persist_estimate,
    upload_generated_export,
    validate_import_customer_id,
)
from app.estimate.persistence import _sanitize_estimate_json_for_storage
