"""Session-state management and estimate lifecycle helpers.

Standardised session state key constants
-----------------------------------------
EST_VIEW_KEY        "estimates_view"          list | import | edit
EST_SELECTED_ID     "selected_estimate_id"    last loaded estimate PK (mirror of loaded_estimate_id)
EST_DATA_VERSION    "est_data_version"        int counter; increment to bust @st.cache_data list cache
EST_FILTER_STATUS   "estimates_filter_status" list status dropdown key
EST_SEARCH_QUERY    "estimates_search_query"  list search text key

Note: The estimate editor (app/estimate/editor.py) retains its own legacy internal
keys (``estimate_editor_state``, ``loaded_estimate_id``, …).  This module writes
those keys so the editor stays compatible, while also writing EST_SELECTED_ID for
convenience of any new code that prefers the canonical name.
"""
from __future__ import annotations

import streamlit as st

# ---------------------------------------------------------------------------
# Public session-state key constants
# ---------------------------------------------------------------------------

EST_VIEW_KEY = "estimates_view"
EST_SELECTED_ID = "selected_estimate_id"
EST_DATA_VERSION = "est_data_version"
EST_FILTER_STATUS = "estimates_filter_status"
EST_SEARCH_QUERY = "estimates_search_query"


# ---------------------------------------------------------------------------
# Internal transient-key management
# ---------------------------------------------------------------------------

# Widget-key prefixes that must be flushed when switching between estimates
# to prevent stale values appearing in the next estimate's inputs.
_EDITOR_TRANSIENT_PREFIXES: tuple[str, ...] = (
    "est_material_",
    "est_labor_",
    "est_customer_",
    "est_job_",
    "est_import_cust_",
    "est_eq_",
)

# Individual singleton keys (not prefix-matched) that must also be cleared.
_EDITOR_SINGLETON_KEYS: tuple[str, ...] = (
    "est_material_edit_idx",
    "est_labor_edit_idx",
    "materials_editor_db",
    "labor_editor_db",
    "equipment_editor_db",
    "estimates_import_sig",
    "estimates_import_cache",
)


# ---------------------------------------------------------------------------
# Cache management
# ---------------------------------------------------------------------------

def bump_estimates_cache() -> None:
    """Increment the version counter to invalidate the cached estimates list.

    Must be called after any write operation (create, edit, delete, approve)
    so the next list render fetches fresh data from the database.
    """
    st.session_state[EST_DATA_VERSION] = int(st.session_state.get(EST_DATA_VERSION, 0)) + 1


# ---------------------------------------------------------------------------
# State management helpers
# ---------------------------------------------------------------------------

def reset_estimate_transients(*, clear_import_hints: bool = True) -> None:
    """Clear editor-only transient session keys.

    Prevents stale widget state from carrying over when switching between
    estimates or starting a new one (avoids double-entry / ghost values).
    """
    for k in _EDITOR_SINGLETON_KEYS:
        st.session_state.pop(k, None)

    to_drop = [
        k for k in list(st.session_state.keys())
        if any(str(k).startswith(p) for p in _EDITOR_TRANSIENT_PREFIXES)
    ]
    for k in to_drop:
        st.session_state.pop(k, None)

    if clear_import_hints:
        st.session_state.pop("estimate_pending_import_pdf", None)
        st.session_state.pop("estimate_pdf_suggestions", None)


def load_estimate_into_session(estimate_id: str) -> bool:
    """Load a saved estimate row into the editor's session state.

    Fetches the row from the DB (short-TTL cache), merges all scalar fields
    into the editor dict, initialises editor defaults, and binds Job Scope
    widgets.

    Returns True on success, False when the row is not found or imports fail.
    """
    from app.estimates.queries import fetch_estimate_by_id

    try:
        from app.estimate.defaults import (
            ensure_numeric_defaults,
            merge_estimate_narrative_scalars_from_row,
            merge_estimate_row_scalar_fields_into_editor,
        )
        from app.estimate.editor import ensure_state
        from app.estimate.job_scope import ensure_scope_widgets_bound
    except ImportError:
        return False

    reset_estimate_transients(clear_import_hints=True)
    row = fetch_estimate_by_id(estimate_id)
    if not row:
        return False

    loaded: dict = row.get("estimate_json") or {}
    if not isinstance(loaded, dict):
        loaded = {}

    # Always pull scalar columns from the DB row so they override stale JSON values.
    loaded.update({
        "quote_number": row.get("quote_number", "") or "",
        "customer_id": row.get("customer_id"),
        "customer_contact_id": row.get("customer_contact_id"),
        "job_id": row.get("job_id"),
        "status": row.get("status", "draft"),
        "estimate_description": row.get(
            "estimate_description", loaded.get("estimate_description", "")
        ),
        "job_received": row.get("job_received", False),
        "po_number": row.get("po_number", ""),
        "po_date": str(row.get("po_date") or ""),
        "po_amount": float(row.get("po_amount", 0) or 0),
    })

    merge_estimate_narrative_scalars_from_row(row, loaded)
    merge_estimate_row_scalar_fields_into_editor(row, loaded)
    ensure_numeric_defaults(loaded)

    # Write to both legacy keys (for editor.py) and canonical key.
    st.session_state["estimate_editor_state"] = loaded
    st.session_state["loaded_estimate_id"] = estimate_id
    st.session_state[EST_SELECTED_ID] = estimate_id
    st.session_state["estimate_editor_quote_ready"] = True

    ensure_state()
    ensure_scope_widgets_bound(loaded, estimate_id)
    return True


def start_new_estimate() -> None:
    """Initialise a blank estimate ready for the editor."""
    try:
        from app.estimate.defaults import blank_estimate
        from app.estimate.editor import ensure_state
    except ImportError:
        return

    reset_estimate_transients(clear_import_hints=True)
    st.session_state["estimate_editor_state"] = blank_estimate()
    st.session_state["loaded_estimate_id"] = None
    st.session_state[EST_SELECTED_ID] = None
    st.session_state["estimate_editor_quote_ready"] = False
    ensure_state()


# ---------------------------------------------------------------------------
# Navigation helpers
# ---------------------------------------------------------------------------

def go_to_list() -> None:
    """Switch to the estimates list view and clear transient editor state."""
    reset_estimate_transients(clear_import_hints=True)
    st.session_state[EST_VIEW_KEY] = "list"


def go_to_edit() -> None:
    """Switch to the estimate editor view."""
    st.session_state[EST_VIEW_KEY] = "edit"


def go_to_import() -> None:
    """Switch to the import view and clear transient editor state."""
    reset_estimate_transients(clear_import_hints=True)
    st.session_state[EST_VIEW_KEY] = "import"
