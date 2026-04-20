"""
Split app/pages/estimate_editor.py into app/estimate/* modules.
Run from repo root: python scripts/split_estimate_editor.py
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "app" / "pages" / "estimate_editor.py"
OUT = ROOT / "app" / "estimate"


def main() -> None:
    text = SRC.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    def slice1(a: int, b: int) -> str:
        """1-based inclusive line numbers."""
        return "".join(lines[a - 1 : b])

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "__init__.py").write_text(
        '"""Estimate editor package (logic split from pages.estimate_editor)."""\n',
        encoding="utf-8",
    )

    # --- calculations.py ---
    calc_body = slice1(80, 230) + slice1(1067, 1070) + slice1(1303, 1393)
    (OUT / "calculations.py").write_text(
        'from __future__ import annotations\n\n'
        "from decimal import Decimal, ROUND_HALF_UP\n\n"
        + calc_body,
        encoding="utf-8",
    )

    # --- defaults.py ---
    (OUT / "defaults.py").write_text(
        'from __future__ import annotations\n\n'
        "import re\n\n"
        "import streamlit as st\n\n"
        "from auth import current_profile\n"
        "from db import fetch_table, fetch_table_admin\n\n"
        + slice1(815, 996),
        encoding="utf-8",
    )

    # --- customer_job.py ---
    (OUT / "customer_job.py").write_text(
        'from __future__ import annotations\n\n'
        "import difflib\n\n"
        "import streamlit as st\n\n"
        "from auth import current_role\n"
        "from db import (\n"
        "    fetch_by_match,\n"
        "    fetch_by_match_admin,\n"
        "    fetch_one,\n"
        "    fetch_table,\n"
        "    fetch_table_admin,\n"
        "    fetch_table_with_order_fallback,\n"
        "    insert_row_admin,\n"
        ")\n\n"
        "from app.estimate.defaults import _normalize_prepared_by_id_value\n\n"
        + slice1(48, 77)
        + slice1(318, 411)
        + slice1(701, 779)
        + slice1(782, 813),
        encoding="utf-8",
    )

    # --- proposal_exports.py ---
    (OUT / "proposal_exports.py").write_text(
        'from __future__ import annotations\n\n'
        "import re\n\n"
        "import streamlit as st\n\n"
        "from proposal import build_proposal_docx, proposal_preview_html, proposal_values\n\n"
        "from app.estimate.customer_job import (\n"
        "    _fetch_contacts_for_estimate_editor,\n"
        "    _fetch_customer_row_for_proposal,\n"
        "    _format_customer_location_line,\n"
        "    _lookup_prepared_by_phone,\n"
        ")\n\n"
        + slice1(37, 38)  # PROPOSAL_PDF_UNAVAILABLE_SHORT from original — line 37-38
        + "\n"
        + slice1(413, 698),
        encoding="utf-8",
    )

    # --- equipment.py ---
    (OUT / "equipment.py").write_text(
        'from __future__ import annotations\n\n'
        "from collections import Counter\n\n"
        "from db import fetch_table\n\n"
        "from app.estimate.calculations import _D0, _dec, money\n\n"
        + slice1(1072, 1301),
        encoding="utf-8",
    )

    # --- persistence.py ---
    (OUT / "persistence.py").write_text(
        'from __future__ import annotations\n\n'
        "import json\n"
        "from datetime import datetime\n"
        "from pathlib import Path\n\n"
        "import streamlit as st\n\n"
        "from auth import current_profile\n"
        "from db import (\n"
        "    fetch_by_match_admin,\n"
        "    fetch_one,\n"
        "    fetch_table,\n"
        "    insert_row_admin,\n"
        "    next_quote_number,\n"
        "    quote_number_in_use,\n"
        "    update_rows_admin,\n"
        "    upload_bytes,\n"
        ")\n\n"
        "from app.estimate.calculations import _D0, _q2, compute_totals, money_db\n"
        "from app.estimate.defaults import (\n"
        "    _apply_default_prepared_by_from_profile,\n"
        "    _normalize_prepared_by_id_value,\n"
        "    _payload_prepared_by_for_db,\n"
        "    blank_estimate,\n"
        ")\n"
        "from app.estimate.equipment import load_estimate_equipment_from_assets\n\n"
        + slice1(1396, 1611),
        encoding="utf-8",
    )

    editor_head = (
        'from __future__ import annotations\n\n'
        "import json\n"
        "import re\n"
        "from datetime import datetime\n"
        "from pathlib import Path\n\n"
        "import pandas as pd\n"
        "import streamlit as st\n"
        "from branding import render_header\n\n"
        "from auth import current_profile, current_role\n"
        "from db import (\n"
        "    create_signed_url,\n"
        "    fetch_by_match,\n"
        "    fetch_by_match_admin,\n"
        "    fetch_one,\n"
        "    fetch_table,\n"
        "    fetch_table_admin,\n"
        "    fetch_table_with_order_fallback,\n"
        "    insert_row_admin,\n"
        "    next_quote_number,\n"
        "    quote_number_in_use,\n"
        "    update_rows_admin,\n"
        "    upload_bytes,\n"
        ")\n"
        "from proposal import try_convert_proposal_docx_to_pdf\n\n"
        "try:\n"
        "    from services.job_service import job_number_display, job_row_select_label\n"
        "except ImportError:\n"
        "    from app.services.job_service import job_number_display, job_row_select_label  # type: ignore\n\n"
        "from app.estimate.calculations import (\n"
        "    compute_totals,\n"
        "    ensure_numeric_defaults,\n"
        "    money,\n"
        "    money_db,\n"
        "    money_str,\n"
        ")\n"
        "from app.estimate.customer_job import (\n"
        "    create_or_get_job_by_name,\n"
        "    resolve_estimate_linked_job,\n"
        "    _customer_dropdown_labels,\n"
        "    _fetch_contacts_for_estimate_editor,\n"
        "    _fetch_customer_row_by_id_for_editor,\n"
        "    _fetch_customers_for_editor,\n"
        "    _top_matches,\n"
        ")\n"
        "from app.estimate.defaults import (\n"
        "    _estimate_table_column_names,\n"
        "    _fetch_prepared_by_choices,\n"
        "    _normalize_prepared_by_id_value,\n"
        "    _payload_prepared_by_for_db,\n"
        "    merge_estimate_row_scalar_fields_into_editor,\n"
        "    blank_estimate,\n"
        ")\n"
        "from app.estimate.equipment import (\n"
        "    build_equipment_picker_maps,\n"
        "    enrich_equipment_rows_from_assets,\n"
        "    load_estimate_equipment_from_assets,\n"
        "    _equipment_core_with_picker_labels,\n"
        "    _equipment_rows_core_for_editor,\n"
        ")\n"
        "from app.estimate.persistence import (\n"
        "    attach_pending_pdf_import_source,\n"
        "    coalesce_imported_estimate,\n"
        "    insert_imported_estimate,\n"
        "    parse_estimate_json_bytes,\n"
        "    persist_estimate,\n"
        "    upload_generated_export,\n"
        "    validate_import_customer_id,\n"
        ")\n"
        "from app.estimate.proposal_exports import (\n"
        "    PROPOSAL_PDF_UNAVAILABLE_SHORT,\n"
        "    _build_proposal_docx_and_vals,\n"
        "    _inject_proposal_preview_styles,\n"
        "    _proposal_export_kwargs,\n"
        "    _render_proposal_preview_html,\n"
        ")\n\n"
        "FINAL_STATUSES = {'approved', 'awarded'}\n\n"
    )

    editor_body = slice1(233, 316) + slice1(998, 1064) + slice1(1613, 1679) + slice1(1681, 3734)
    (OUT / "editor.py").write_text(editor_head + editor_body, encoding="utf-8")

    # Truncate source page (drop duplicate compact block)
    truncated = "".join(lines[:3737])
    SRC.write_text(truncated, encoding="utf-8")

    shim = '''from __future__ import annotations

"""Estimate editor page — re-exports implementation from :mod:`app.estimate.editor`."""

from app.estimate.calculations import (
    compute_totals,
    ensure_numeric_defaults,
    money_db,
    money_str,
)
from app.estimate.defaults import blank_estimate, merge_estimate_row_scalar_fields_into_editor
from app.estimate.editor import ensure_state, render_estimate_editor
from app.estimate.equipment import load_estimate_equipment_from_assets
from app.estimate.persistence import (
    attach_pending_pdf_import_source,
    coalesce_imported_estimate,
    insert_imported_estimate,
    parse_estimate_json_bytes,
    persist_estimate,
    upload_generated_export,
    validate_import_customer_id,
)
from app.estimate.persistence import _sanitize_estimate_json_for_storage


def render() -> None:
    render_estimate_editor(embedded=False)
'''
    SRC.write_text(shim, encoding="utf-8")

    print("Done: app/estimate/*.py and pages/estimate_editor.py shim")


if __name__ == "__main__":
    main()
