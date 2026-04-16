from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from branding import render_header
from auth import current_role
from db import (
    delete_rows_admin,
    fetch_by_match_admin,
    fetch_one,
    fetch_table,
    fetch_table_admin,
)

try:
    from table_actions import (
        IPS_PENDING_DELETE,
        TABLE_KEY_ESTIMATES,
        clear_selected_ids,
        inject_table_action_styles,
        render_selectable_dataframe,
        render_table_action_bar,
    )
except ImportError:
    from app.table_actions import (  # type: ignore
        IPS_PENDING_DELETE,
        TABLE_KEY_ESTIMATES,
        clear_selected_ids,
        inject_table_action_styles,
        render_selectable_dataframe,
        render_table_action_bar,
    )

try:
    from services.job_service import job_number_display
except ImportError:
    from app.services.job_service import job_number_display  # type: ignore

from pages.estimate_editor import (
    blank_estimate,
    coalesce_imported_estimate,
    ensure_state,
    insert_imported_estimate,
    parse_estimate_json_bytes,
    render_estimate_editor,
)


def _estimates_page_admin_read() -> bool:
    """Internal roles use service-role reads so admin-written rows stay visible under RLS."""
    return current_role() in {"admin", "estimator"}


def _fetch_one_estimate_row(estimate_id: str) -> dict[str, Any] | None:
    eid = str(estimate_id or "").strip()
    if not eid:
        return None
    if _estimates_page_admin_read():
        rows = fetch_by_match_admin("estimates", {"id": eid}, limit=1)
        return rows[0] if rows else None
    return fetch_one("estimates", {"id": eid})


def _fetch_estimates_list_rows() -> list[dict[str, Any]]:
    if _estimates_page_admin_read():
        return fetch_table_admin("estimates", limit=1000, order_by="updated_at")
    return fetch_table("estimates", limit=1000, order_by="updated_at")


def _fetch_jobs_for_estimate_links() -> list[dict[str, Any]]:
    if _estimates_page_admin_read():
        return fetch_table_admin(
            "jobs",
            columns="id,job_number,estimate_id",
            limit=5000,
            order_by="job_number",
        )
    return fetch_table(
        "jobs",
        columns="id,job_number,estimate_id",
        limit=5000,
        order_by="job_number",
    )


_EDITOR_TRANSIENT_PREFIXES: tuple[str, ...] = (
    # New form-based Materials/Labor widgets (avoid stale inputs across estimates)
    "est_material_",
    "est_labor_",
    # Customer/job match helpers
    "est_customer_",
    "est_job_",
    # Equipment picker/filter widgets
    "est_eq_",
)


def _reset_estimate_editor_transients(*, clear_import_hints: bool = True) -> None:
    """
    Clear editor-only transient session keys so switching between estimates (or starting a new one)
    doesn't carry over stale widget state that can feel like "double entry" on rerun.
    """
    # Known singleton keys (safe even if absent)
    for k in (
        "est_material_edit_idx",
        "est_labor_edit_idx",
        "materials_editor_db",
        "labor_editor_db",
        "equipment_editor_db",
        "estimates_import_sig",
        "estimates_import_cache",
    ):
        st.session_state.pop(k, None)

    # Prefix-based cleanup for dynamically-indexed edit-form keys.
    to_drop: list[str] = []
    for k in list(st.session_state.keys()):
        if any(str(k).startswith(p) for p in _EDITOR_TRANSIENT_PREFIXES):
            to_drop.append(str(k))
    for k in to_drop:
        st.session_state.pop(k, None)

    if clear_import_hints:
        st.session_state.pop("estimate_pending_import_pdf", None)
        st.session_state.pop("estimate_pdf_suggestions", None)


def _load_estimate_into_session(selected_id: str) -> None:
    _reset_estimate_editor_transients(clear_import_hints=True)
    row = _fetch_one_estimate_row(selected_id)
    if not row:
        return
    loaded = row.get("estimate_json") or {}
    loaded.update({
        "quote_number": row.get("quote_number", ""),
        "customer_id": row.get("customer_id"),
        "customer_contact_id": row.get("customer_contact_id"),
        "job_id": row.get("job_id"),
        "status": row.get("status", "draft"),
        "scope_of_work": row.get("scope_of_work", ""),
        "exclusions": row.get("exclusions", ""),
        "additional_charges": row.get("additional_charges", ""),
        "customer_responsibilities": row.get("customer_responsibilities", ""),
        "job_received": row.get("job_received", False),
        "po_number": row.get("po_number", ""),
        "po_date": str(row.get("po_date") or ""),
        "po_amount": float(row.get("po_amount", 0) or 0),
    })
    # Only fill missing numeric fields; never overwrites real saved values.
    try:
        from pages.estimate_editor import ensure_numeric_defaults
    except ImportError:
        from app.pages.estimate_editor import ensure_numeric_defaults  # type: ignore
    ensure_numeric_defaults(loaded)
    st.session_state["estimate_editor_state"] = loaded
    st.session_state["loaded_estimate_id"] = selected_id
    st.session_state["estimate_editor_quote_ready"] = True
    # Ensure editor defaults exist (does not overwrite loaded values).
    ensure_state()


def _render_estimate_list() -> None:
    can_edit = current_role() in {"admin", "estimator"}
    rows = _fetch_estimates_list_rows()
    df = pd.DataFrame(rows)

    job_rows = _fetch_jobs_for_estimate_links()
    job_by_id = {str(r["id"]): r for r in job_rows if r.get("id")}
    job_by_estimate_id = {str(r["estimate_id"]): r for r in job_rows if r.get("estimate_id")}

    def _linked_job_number_cell(row: pd.Series) -> str:
        jid = row.get("job_id")
        eid = row.get("id")
        if jid is not None and pd.notna(jid) and str(jid).strip():
            sj = str(jid)
            if sj in job_by_id:
                return job_number_display(job_by_id[sj].get("job_number"))
        if eid is not None and pd.notna(eid):
            se = str(eid)
            if se in job_by_estimate_id:
                return job_number_display(job_by_estimate_id[se].get("job_number"))
        return ""

    def _linked_job_id_for_row(row: pd.Series) -> str | None:
        jid = row.get("job_id")
        eid = row.get("id")
        if jid is not None and pd.notna(jid) and str(jid).strip():
            return str(jid)
        if eid is not None and pd.notna(eid):
            se = str(eid)
            if se in job_by_estimate_id:
                return str(job_by_estimate_id[se].get("id"))
        return None

    if not df.empty:
        keep = [
            c
            for c in [
                "quote_number",
                "status",
                "revision_number",
                "proposal_total",
                "final_bid",
                "job_received",
                "po_number",
                "updated_at",
            ]
            if c in df.columns
        ]
        if "id" in df.columns:
            keep = ["id"] + [c for c in keep if c != "id"]
        if "job_id" in df.columns and "job_id" not in keep:
            keep.insert(1, "job_id")
        df = df[keep]

        if "status" in df.columns:
            statuses = ["All"] + sorted(df["status"].dropna().astype(str).unique().tolist())
            selected = st.selectbox("Filter Status", statuses, key="est_list_status")
            if selected != "All":
                df = df[df["status"] == selected]

        search = st.text_input("Search Quote / PO Number", key="est_list_search")
        if search.strip():
            s = search.strip().lower()
            mask = df.astype(str).apply(lambda col: col.str.lower().str.contains(s, na=False))
            df = df[mask.any(axis=1)]

        df = df.copy()
        df["Linked job"] = df.apply(_linked_job_number_cell, axis=1)

    if df.empty:
        st.info("No estimates found.")
        return

    pref_order = ["quote_number", "Linked job"]
    show_cols = [c for c in pref_order if c in df.columns]
    show_cols.extend(
        c for c in df.columns if c not in ("id", "job_id") and c not in show_cols
    )
    if "id" not in df.columns:
        st.dataframe(df, use_container_width=True, hide_index=True)
        return

    st.caption(
        "Checkbox column on the **left**. Select rows, then use the **action bar** directly under the grid."
    )
    _, sel = render_selectable_dataframe(
        df,
        table_key=TABLE_KEY_ESTIMATES,
        id_column="id",
        columns=show_cols,
        editor_key="est_list_sel_editor",
    )
    actions = render_table_action_bar(
        TABLE_KEY_ESTIMATES,
        sel,
        can_view=True,
        can_edit=can_edit,
        can_delete=can_edit,
        export_df=df,
        visible_df=df,
        id_column="id",
        export_filename="estimates_export.csv",
    )
    if can_edit and sel and len(sel) == 1:
        try:
            from services.job_from_estimate import create_job_from_estimate
        except ImportError:
            from app.services.job_from_estimate import create_job_from_estimate  # type: ignore
        try:
            from ui import IPS_NAV_PENDING_KEY
        except ImportError:
            from app.ui import IPS_NAV_PENDING_KEY  # type: ignore
        row_one = df[df["id"].astype(str) == str(sel[0])]
        open_jid: str | None = None
        linked_jn = ""
        if not row_one.empty:
            r0 = row_one.iloc[0]
            open_jid = _linked_job_id_for_row(r0)
            linked_jn = str(r0.get("Linked job") or "").strip()
        with st.container(border=True):
            st.markdown('<span class="ips-list-top-anchor"></span>', unsafe_allow_html=True)
            if open_jid:
                if linked_jn:
                    st.markdown(f"**Linked job** · **{linked_jn}**", unsafe_allow_html=True)
                else:
                    st.markdown("**Linked job** · _Open in Job Database to view details._", unsafe_allow_html=True)
                if st.button("Open Job", type="primary", use_container_width=True, key="est_list_open_job_btn"):
                    st.session_state[IPS_NAV_PENDING_KEY] = "Job Database"
                    st.session_state["job_mode"] = "edit"
                    st.session_state["job_edit_id"] = str(open_jid)
                    st.rerun()
            else:
                lc1, lc2, lc3 = st.columns([1.1, 1, 2])
                with lc1:
                    run_cj = st.button(
                        "Create Job from Estimate",
                        key="est_list_create_job_btn",
                        use_container_width=True,
                    )
                with lc2:
                    st.checkbox(
                        "Open Job Database after create",
                        value=True,
                        key="est_list_create_job_open_db",
                    )
                with lc3:
                    st.caption("Creates a **J#####** job when customer and status rules pass.")
                if run_cj:
                    res = create_job_from_estimate(str(sel[0]))
                    if res.ok and res.job:
                        st.success(res.message)
                        jid = str(res.job.get("id") or "")
                        if jid and st.session_state.get("est_list_create_job_open_db", True):
                            st.session_state[IPS_NAV_PENDING_KEY] = "Job Database"
                            st.session_state["job_mode"] = "edit"
                            st.session_state["job_edit_id"] = jid
                        st.rerun()
                    elif res.message:
                        if res.error_code == "duplicate":
                            st.warning(res.message)
                        else:
                            st.error(res.message)
    if (actions.get("view") or actions.get("edit")) and sel and len(sel) == 1:
        _load_estimate_into_session(str(sel[0]))
        st.session_state["estimates_view"] = "edit"
        st.rerun()
    pend = st.session_state.get(IPS_PENDING_DELETE) or {}
    if actions.get("confirm_delete") and pend.get(TABLE_KEY_ESTIMATES):
        for eid in pend[TABLE_KEY_ESTIMATES]:
            try:
                delete_rows_admin("estimates", {"id": eid})
            except Exception as exc:
                st.error(f"Could not delete {eid}: {exc}")
        pend.pop(TABLE_KEY_ESTIMATES, None)
        clear_selected_ids(TABLE_KEY_ESTIMATES)
        st.success("Delete completed where permitted.")
        st.rerun()


def _render_json_ips_estimate_import() -> None:
    st.markdown("### JSON estimate import")
    st.caption(
        "Upload **JSON** exports (same shape as Review / Save: `estimate_json`). "
        "Use **Import JSON file(s) to database** after preview. "
        "Vendor **PDF** quotes use the section above. Duplicate quote numbers are reassigned on import."
    )

    uploaded = st.file_uploader(
        "Upload JSON",
        type=["json"],
        accept_multiple_files=True,
        key="est_import_json_upload",
    )

    if not uploaded:
        st.caption("Upload one or more JSON estimate files above to preview and import.")
        return

    sig = tuple((i, f.name, len(f.getvalue())) for i, f in enumerate(uploaded))
    if st.session_state.get("estimates_import_sig") != sig:
        st.session_state["estimates_import_sig"] = sig
        cached: list[dict] = []
        for f in uploaded:
            raw = f.getvalue()
            try:
                parsed = parse_estimate_json_bytes(raw)
                merged = coalesce_imported_estimate(parsed)
                qn = str(merged.get("quote_number", "") or "").strip()
                cid = merged.get("customer_id")
                cached.append(
                    {
                        "file": f.name,
                        "kind": "json",
                        "merged": merged,
                        "error": None,
                        "quote_number": qn or "(will assign)",
                        "has_customer_id": "yes" if cid else "MISSING",
                    }
                )
            except Exception as exc:
                cached.append(
                    {
                        "file": f.name,
                        "kind": "json",
                        "merged": None,
                        "error": str(exc),
                        "quote_number": "—",
                        "has_customer_id": f"Error: {exc}",
                    }
                )
        st.session_state["estimates_import_cache"] = cached

    rows: list[dict] = st.session_state["estimates_import_cache"]

    preview_df = pd.DataFrame(
        [
            {
                "file": r["file"],
                "kind": r["kind"],
                "quote_number": r["quote_number"],
                "has_customer_id": r["has_customer_id"],
            }
            for r in rows
        ]
    )
    st.dataframe(preview_df, use_container_width=True, hide_index=True)

    json_ready = [
        (i, r)
        for i, r in enumerate(rows)
        if r.get("kind") == "json" and r.get("merged") is not None and not r.get("error")
    ]

    if json_ready:
        st.markdown("##### JSON Import (direct)")
        if st.button(
            "Import JSON file(s) to database",
            type="secondary",
            use_container_width=True,
            key="est_import_json_run",
        ):
            errors: list[str] = []
            ok = 0
            notes: list[str] = []
            for i, r in json_ready:
                f = uploaded[i]
                merged = r.get("merged")
                if merged is None:
                    errors.append(f"{f.name}: nothing to import")
                    continue
                try:
                    raw = f.getvalue()
                    _, suffix = insert_imported_estimate(merged, f.name, raw, source_content_type="application/json")
                    ok += 1
                    if suffix:
                        notes.append(f"{f.name}:{suffix}")
                except Exception as exc:
                    errors.append(f"{f.name}: {exc}")
            if notes:
                for n in notes:
                    st.info(n)
            if errors:
                for e in errors:
                    st.error(e)
            if ok:
                st.success(f"Imported {ok} JSON estimate(s). Returning to list.")
                st.session_state["estimates_view"] = "list"
                st.rerun()


def _render_estimate_import() -> None:
    """PDF import then JSON import (Estimates page when ``estimates_view == \"import\"``)."""
    try:
        from services.pdf_quote_import import render_vendor_pdf_quote_section
    except ImportError:
        from app.services.pdf_quote_import import render_vendor_pdf_quote_section  # type: ignore

    st.markdown("### PDF vendor quotes")
    render_vendor_pdf_quote_section()

    st.markdown("---")
    _render_json_ips_estimate_import()


def render() -> None:
    if "estimates_view" not in st.session_state:
        st.session_state["estimates_view"] = "list"

    # Legacy session value from older builds
    if st.session_state.get("estimates_view") == "editor":
        st.session_state["estimates_view"] = "edit"

    view = st.session_state["estimates_view"]
    if view not in ("list", "import", "edit"):
        st.session_state["estimates_view"] = "list"
        view = "list"

    # Single branding header per request; each branch renders one body section only.
    render_header("Estimates")
    inject_table_action_styles()

    if view == "list":
        st.caption("Search and open estimates, create new, or import JSON / PDF quotes.")
        with st.container(border=True):
            st.markdown(
                '<span class="ips-list-top-anchor ips-estimate-topbar"></span>',
                unsafe_allow_html=True,
            )
            a1, a2, a3 = st.columns([1, 1, 2])
            with a1:
                if st.button("New estimate", type="primary", use_container_width=True, key="est_list_new"):
                    _reset_estimate_editor_transients(clear_import_hints=True)
                    st.session_state["estimate_editor_state"] = blank_estimate()
                    st.session_state["loaded_estimate_id"] = None
                    st.session_state["estimate_editor_quote_ready"] = False
                    ensure_state()
                    st.session_state["estimates_view"] = "edit"
                    st.rerun()
            with a2:
                if st.button(
                    "Import Existing Quotes",
                    type="secondary",
                    use_container_width=True,
                    key="est_list_imp",
                ):
                    _reset_estimate_editor_transients(clear_import_hints=True)
                    st.session_state["estimates_view"] = "import"
                    st.rerun()
        _render_estimate_list()

    elif view == "import":
        st.caption("Upload PDF vendor quotes or JSON estimate exports.")
        with st.container(border=True):
            st.markdown(
                '<span class="ips-list-top-anchor ips-estimate-topbar"></span>',
                unsafe_allow_html=True,
            )
            c1, c2 = st.columns([1, 4])
            with c1:
                if st.button("← Back to list", type="secondary", use_container_width=True, key="est_imp_back"):
                    st.session_state["estimates_view"] = "list"
                    st.rerun()
            with c2:
                _render_estimate_import()

    else:
        # view == "edit"
        with st.container(border=True):
            st.markdown(
                '<span class="ips-list-top-anchor ips-estimate-topbar"></span>',
                unsafe_allow_html=True,
            )
            c1, c2, c3 = st.columns([1, 1, 4])
            with c1:
                if st.button("← Back to list", type="secondary", use_container_width=True, key="est_ed_back"):
                    _reset_estimate_editor_transients(clear_import_hints=True)
                    st.session_state["estimates_view"] = "list"
                    st.rerun()
            with c2:
                if st.button(
                    "Import Existing Quotes",
                    type="secondary",
                    use_container_width=True,
                    key="est_ed_imp",
                ):
                    _reset_estimate_editor_transients(clear_import_hints=True)
                    st.session_state["estimates_view"] = "import"
                    st.rerun()
            with c3:
                pass
        render_estimate_editor(embedded=True)
