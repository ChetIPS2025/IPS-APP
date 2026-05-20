"""Top-level Estimates page entry point.

Orchestrates the three view states:
  list    — estimates list with filters, table, and quick actions
  import  — PDF vendor quote + JSON estimate import
  edit    — full estimate editor (delegates to app.estimate.editor)

This module contains no business logic itself; it delegates to:
  estimates.queries     — DB reads
  estimates.services    — session-state management
  estimates.components  — UI rendering
  estimates.dialogs     — import sections
  app.estimate.editor   — line-item editor (unchanged)
"""
from __future__ import annotations

import streamlit as st

from app.estimates.services import (
    EST_VIEW_KEY,
    bump_estimates_cache,
    go_to_edit,
    go_to_import,
    go_to_list,
    load_estimate_into_session,
    start_new_estimate,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_view_key() -> str:
    """Guarantee a valid estimates_view value and return it."""
    if EST_VIEW_KEY not in st.session_state:
        st.session_state[EST_VIEW_KEY] = "list"
    # Legacy alias used by older builds
    if st.session_state.get(EST_VIEW_KEY) == "editor":
        st.session_state[EST_VIEW_KEY] = "edit"
    view = st.session_state[EST_VIEW_KEY]
    if view not in ("list", "import", "edit"):
        st.session_state[EST_VIEW_KEY] = "list"
        view = "list"
    return view


def _render_list_view() -> None:
    """Render the estimates list with quick-action buttons above the table."""
    from app.estimates.components import (
        inject_estimates_mobile_styles,
        render_estimate_detail_panel,
        render_estimate_empty_state,
        render_estimates_filters,
        render_estimates_table,
    )
    from app.estimates.queries import (
        fetch_estimates_list,
        fetch_jobs_for_estimates,
        fetch_locations_index,
        is_admin_reader,
    )

    import pandas as pd
    from auth import current_role

    try:
        try:
            from app.ui.page_shell import action_bar_card, render_page_header
        except ImportError:
            from ui.page_shell import action_bar_card, render_page_header  # type: ignore
    except Exception:
        action_bar_card = None  # type: ignore
        render_page_header = None  # type: ignore

    try:
        try:
            from table_actions import inject_table_action_styles
        except ImportError:
            from app.table_actions import inject_table_action_styles  # type: ignore
    except Exception:
        inject_table_action_styles = lambda: None  # type: ignore

    inject_table_action_styles()
    inject_estimates_mobile_styles()

    if render_page_header:
        render_page_header("Estimates", "Quotes, imports, and customer-ready proposals.")
    else:
        st.title("Estimates")

    # Quick-action buttons
    ctx = action_bar_card(title="Quick Actions") if action_bar_card else _noop_ctx()
    with ctx:
        a1, a2 = st.columns(2, gap="small")
        with a1:
            if st.button("New estimate", type="primary", use_container_width=True, key="est_list_new"):
                start_new_estimate()
                go_to_edit()
                st.rerun()
        with a2:
            if st.button("Import Existing Quotes", type="secondary", use_container_width=True, key="est_list_imp"):
                go_to_import()
                st.rerun()

    # Fetch data
    rows = fetch_estimates_list()
    df = pd.DataFrame(rows)

    # Build lookup maps used by table rendering
    job_rows = fetch_jobs_for_estimates()
    job_by_id = {str(r["id"]): r for r in job_rows if r.get("id")}
    job_by_estimate_id = {str(r["estimate_id"]): r for r in job_rows if r.get("estimate_id")}

    eid_to_customer: dict[str, str] = {}
    for r in rows:
        rid = str(r.get("id") or "").strip()
        if rid:
            cid = r.get("customer_id")
            if cid is None:
                eid_to_customer[rid] = ""
            else:
                try:
                    eid_to_customer[rid] = "" if pd.isna(cid) else str(cid).strip()
                except Exception:
                    eid_to_customer[rid] = str(cid).strip()

    location_by_id = fetch_locations_index()

    # --- Restrict df columns to what the table uses (preserves all needed for search) ---
    if not df.empty:
        keep = [
            c for c in [
                "id", "job_id", "quote_number", "status", "proposal_total",
                "job_received", "po_number", "scope_of_work", "estimate_json",
                "customer_location_id", "estimate_description",
            ]
            if c in df.columns
        ]
        # Guarantee id is first; job_id second when present
        if "id" in df.columns:
            keep = ["id"] + [c for c in keep if c != "id"]
        if "job_id" in df.columns and "job_id" not in keep:
            keep.insert(1, "job_id")
        df = df[keep]

    # --- No estimates in DB at all ---
    if df.empty:
        if render_estimate_empty_state():
            start_new_estimate()
            go_to_edit()
            st.rerun()
        return

    # --- Filters (status + text search applied here) ---
    df_filtered = render_estimates_filters(df)

    # --- Empty after filtering ---
    if df_filtered.empty:
        st.info("No estimates match the current filter. Adjust or clear the filter above.")
        return

    # --- Table ---
    can_edit = current_role() in {"admin", "pm"}
    sel: list[str]
    actions: dict
    sel, actions = render_estimates_table(
        df_filtered,
        job_by_id=job_by_id,
        job_by_estimate_id=job_by_estimate_id,
        location_by_id=location_by_id,
        eid_to_customer=eid_to_customer,
        can_edit=can_edit,
    )

    # --- Detail panel (linked job / create-job) ---
    render_estimate_detail_panel(
        sel,
        df=df_filtered,
        job_by_id=job_by_id,
        job_by_estimate_id=job_by_estimate_id,
        can_edit=can_edit,
    )

    # --- View / Edit action triggered from action bar ---
    if (actions.get("view") or actions.get("edit")) and sel and len(sel) == 1:
        if load_estimate_into_session(str(sel[0])):
            go_to_edit()
            st.rerun()


def _render_import_view() -> None:
    """Render the PDF + JSON import page."""
    from app.estimates.dialogs import render_import_page

    try:
        try:
            from app.ui.page_shell import render_card, render_page_header
        except ImportError:
            from ui.page_shell import render_card, render_page_header  # type: ignore
    except Exception:
        render_card = None  # type: ignore
        render_page_header = None  # type: ignore

    if render_page_header:
        render_page_header("Estimates", "PDF or JSON import — return to list when done.")
    else:
        st.title("Import Estimates")

    ctx = render_card() if render_card else _noop_ctx()
    with ctx:
        st.markdown('<span class="ips-list-top-anchor ips-estimate-topbar"></span>', unsafe_allow_html=True)
        if st.button("← Back to list", type="secondary", use_container_width=True, key="est_imp_back"):
            go_to_list()
            st.rerun()
        render_import_page()


def _render_edit_view() -> None:
    """Render the estimate editor (delegates to app.estimate.editor)."""
    try:
        try:
            from app.ui.page_shell import render_card, render_page_header
        except ImportError:
            from ui.page_shell import render_card, render_page_header  # type: ignore
    except Exception:
        render_card = None  # type: ignore
        render_page_header = None  # type: ignore

    try:
        try:
            from app.ui.activity import render_activity_panel
        except ImportError:
            from ui.activity import render_activity_panel  # type: ignore
    except Exception:
        render_activity_panel = None  # type: ignore

    if render_page_header:
        render_page_header("Estimates", "Line items and save — Back to list when done.")
    else:
        st.title("Edit Estimate")

    # Navigation bar
    ctx = render_card() if render_card else _noop_ctx()
    with ctx:
        st.markdown('<span class="ips-list-top-anchor ips-estimate-topbar"></span>', unsafe_allow_html=True)
        c1, c2 = st.columns(2, gap="small")
        with c1:
            if st.button("← Back to list", type="secondary", use_container_width=True, key="est_ed_back"):
                go_to_list()
                st.rerun()
        with c2:
            if st.button("Import Existing Quotes", type="secondary", use_container_width=True, key="est_ed_imp"):
                go_to_import()
                st.rerun()

    # Activity panel for saved estimates — uses the 30-second cached single-row fetch
    # so it does not hit the DB on every widget interaction rerun.
    eid_edit = str(st.session_state.get("loaded_estimate_id") or "").strip()
    if eid_edit and render_activity_panel:
        from app.estimates.queries import fetch_estimate_by_id
        erow = fetch_estimate_by_id(eid_edit)
        if erow:
            render_activity_panel(
                title="Estimate activity",
                created_at=erow.get("created_at"),
                updated_at=erow.get("updated_at"),
                status=erow.get("status"),
                extra_lines=[("Quote #", str(erow.get("quote_number") or "—"))],
            )

    # Delegate to the canonical editor
    try:
        from app.estimate.editor import render_estimate_editor
    except ImportError:
        try:
            from estimate.editor import render_estimate_editor  # type: ignore
        except ImportError:
            st.error("Estimate editor could not be loaded.")
            return

    render_estimate_editor(embedded=True)


# ---------------------------------------------------------------------------
# Public render() entry point
# ---------------------------------------------------------------------------

def render() -> None:
    """Main entry point for the Estimates page.

    Called by app/pages/estimates.py (and by main.py via that module).
    """
    view = _ensure_view_key()

    if view == "list":
        _render_list_view()
    elif view == "import":
        _render_import_view()
    else:
        _render_edit_view()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

class _noop_ctx:
    """Fallback context manager when UI helpers are unavailable."""
    def __enter__(self): return self
    def __exit__(self, *_): pass
