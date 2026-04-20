from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

import pandas as pd
import streamlit as st

from branding import render_header

try:
    from app.ips_crud_list_styles import render_crud_list_subtitle
except ImportError:
    from ips_crud_list_styles import render_crud_list_subtitle  # type: ignore
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
        get_selected_ids,
        inject_table_action_styles,
        render_selection_action_bar,
        set_selected_ids,
    )
except ImportError:
    from app.table_actions import (  # type: ignore
        IPS_PENDING_DELETE,
        TABLE_KEY_ESTIMATES,
        clear_selected_ids,
        get_selected_ids,
        inject_table_action_styles,
        render_selection_action_bar,
        set_selected_ids,
    )

try:
    from services.job_service import job_number_display
except ImportError:
    from app.services.job_service import job_number_display  # type: ignore

from app.utils.formatters import job_display_label

try:
    from services.estimate_import_customer_match import (
        PLACEHOLDER,
        build_sorted_customer_names,
        classify_import_customer_matches,
        name_to_customer_id_map,
        resolve_picked_customer_id,
    )
except ImportError:
    from app.services.estimate_import_customer_match import (  # type: ignore
        PLACEHOLDER,
        build_sorted_customer_names,
        classify_import_customer_matches,
        name_to_customer_id_map,
        resolve_picked_customer_id,
    )

from pages.estimate_editor import (
    blank_estimate,
    coalesce_imported_estimate,
    ensure_state,
    insert_imported_estimate,
    merge_estimate_row_scalar_fields_into_editor,
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


def _fetch_customers_for_import() -> list[dict[str, Any]]:
    """Directory rows for matching imported quotes to real customers."""
    if _estimates_page_admin_read():
        return fetch_table_admin(
            "customers",
            columns="id,customer_name",
            limit=3000,
            order_by="customer_name",
        )
    return fetch_table(
        "customers",
        columns="id,customer_name",
        limit=3000,
        order_by="customer_name",
    )


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


def _cleanup_est_list_row_pick_keys() -> None:
    """Clear per-row list checkbox keys after Select All / Clear so widgets resync to stored IDs."""
    for k in list(st.session_state.keys()):
        if str(k).startswith("est_list_pick_"):
            st.session_state.pop(k, None)


_MONEY_LIST_COLUMNS: frozenset[str] = frozenset({"proposal_total", "final_bid"})


def _estimate_money_display(val: Any) -> str:
    """DB / saved numeric → $ with commas and exactly 2 decimal places (Decimal-safe)."""
    if val is None:
        return ""
    try:
        if pd.isna(val):
            return ""
    except Exception:
        pass
    try:
        d = Decimal(str(val).replace(",", "").strip()).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return f"${d:,.2f}"
    except Exception:
        s = str(val).strip()
        return s[:72] + ("…" if len(s) > 72 else "")


def _estimate_money_csv(val: Any) -> str:
    """Same cents as display; plain numeric string for CSV (2 decimals, no $)."""
    if val is None:
        return ""
    try:
        if pd.isna(val):
            return ""
    except Exception:
        pass
    try:
        d = Decimal(str(val).replace(",", "").strip()).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return f"{d:.2f}"
    except Exception:
        return str(val).strip()


def _estimate_list_cell_text(val: Any, col: str | None = None) -> str:
    if col and col in _MONEY_LIST_COLUMNS:
        return _estimate_money_display(val)
    if val is None:
        return ""
    try:
        if pd.isna(val):
            return ""
    except Exception:
        pass
    s = str(val).strip()
    if len(s) > 72:
        return f"{s[:69]}…"
    return s


_EDITOR_TRANSIENT_PREFIXES: tuple[str, ...] = (
    # New form-based Materials/Labor widgets (avoid stale inputs across estimates)
    "est_material_",
    "est_labor_",
    # Customer/job match helpers
    "est_customer_",
    "est_job_",
    "est_import_cust_",
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
        "estimate_description": row.get("estimate_description", loaded.get("estimate_description", "")),
        "scope_of_work": row.get("scope_of_work", ""),
        "exclusions": row.get("exclusions", ""),
        "additional_charges": row.get("additional_charges", ""),
        "customer_responsibilities": row.get("customer_responsibilities", ""),
        "job_received": row.get("job_received", False),
        "po_number": row.get("po_number", ""),
        "po_date": str(row.get("po_date") or ""),
        "po_amount": float(row.get("po_amount", 0) or 0),
    })
    merge_estimate_row_scalar_fields_into_editor(row, loaded)
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

    def _norm_customer_id(v: Any) -> str:
        if v is None:
            return ""
        try:
            if pd.isna(v):
                return ""
        except Exception:
            pass
        s = str(v).strip()
        return s if s and s.lower() != "nan" else ""

    eid_to_customer: dict[str, str] = {}
    for r in rows:
        rid = str(r.get("id") or "").strip()
        if rid:
            eid_to_customer[rid] = _norm_customer_id(r.get("customer_id"))

    job_rows = _fetch_jobs_for_estimate_links()
    job_by_id = {str(r["id"]): r for r in job_rows if r.get("id")}
    job_by_estimate_id = {str(r["estimate_id"]): r for r in job_rows if r.get("estimate_id")}

    def _linked_job_display_cell(row: pd.Series) -> str:
        jid = row.get("job_id")
        eid = row.get("id")
        if jid is not None and pd.notna(jid) and str(jid).strip():
            sj = str(jid)
            if sj in job_by_id:
                job = job_by_id[sj]
                return job_display_label(job.get("job_number"), job.get("job_name"))
        if eid is not None and pd.notna(eid):
            se = str(eid)
            if se in job_by_estimate_id:
                job = job_by_estimate_id[se]
                return job_display_label(job.get("job_number"), job.get("job_name"))
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

    def _series_truthy_job_received(row: pd.Series) -> bool:
        v = row.get("job_received")
        if v is None:
            return False
        try:
            if pd.isna(v):
                return False
        except Exception:
            pass
        if isinstance(v, bool):
            return v
        if isinstance(v, (int, float)):
            try:
                return float(v) != 0.0
            except (TypeError, ValueError):
                return False
        s = str(v).strip().lower()
        return s in ("true", "1", "yes", "t")

    def _row_estimate_id(est_row: pd.Series) -> str:
        """Primary key for API calls — always the estimate ``id`` column, never quote text."""
        if "id" not in est_row.index:
            return ""
        raw = est_row["id"]
        if raw is None:
            return ""
        try:
            if pd.isna(raw):
                return ""
        except Exception:
            pass
        return str(raw).strip()

    def _estimate_description_display(est_row: pd.Series) -> str:
        """
        Row-level description shown in the Estimates list.
        Prefer explicit short estimate description; fall back to older compatibility keys.
        Avoid using Scope of Work unless nothing else exists.
        """
        desc = est_row.get("estimate_description")
        if desc is None or (isinstance(desc, float) and pd.isna(desc)):
            desc = ""
        if not str(desc).strip():
            ej = est_row.get("estimate_json")
            if isinstance(ej, dict):
                desc = ej.get("estimate_description") or ""
        if not str(desc).strip():
            ej = est_row.get("estimate_json")
            if isinstance(ej, dict):
                desc = ej.get("job") or ej.get("job_name") or ""
        if not str(desc).strip():
            # Absolute last resort: first line of Scope of Work (can be long proposal text).
            desc = est_row.get("scope_of_work") or ""
        s = str(desc or "").strip()
        if not s:
            return ""
        # Keep list rows scannable: first line, capped length.
        s = s.splitlines()[0].strip()
        return s[:60] + ("…" if len(s) > 60 else "")

    if not df.empty:
        keep = [
            c
            for c in [
                "quote_number",
                "status",
                "proposal_total",
                "job_received",
                "po_number",
                "scope_of_work",
                "estimate_json",
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
        df["Linked job"] = df.apply(_linked_job_display_cell, axis=1)

    if df.empty:
        st.info("No estimates found.")
        return

    # Visible columns (keep list-row layout clean).
    pref_order = [
        "quote_number",
        "Linked job",
        "status",
        "proposal_total",
        "po_number",
    ]
    show_cols = [c for c in pref_order if c in df.columns]
    if "id" not in df.columns:
        st.dataframe(df, use_container_width=True, hide_index=True)
        return

    try:
        from services.job_from_estimate import (
            create_job_from_estimate,
            estimate_status_allows_job_creation,
        )
    except ImportError:
        from app.services.job_from_estimate import (  # type: ignore
            create_job_from_estimate,
            estimate_status_allows_job_creation,
        )

    try:
        from ui import IPS_NAV_PENDING_KEY
    except ImportError:
        from app.ui import IPS_NAV_PENDING_KEY  # type: ignore

    def _job_received_disabled_reason(est_row: pd.Series, *, cust_id: str) -> str:
        """Non-empty means Job Received should stay disabled (linked estimates use **Job Created** instead)."""
        if not can_edit:
            return "Only admin or estimator can run this action."
        if _series_truthy_job_received(est_row):
            return "This estimate is already marked as job received."
        if not cust_id:
            return "Choose a customer on the estimate before creating a job."
        st_raw = str(est_row.get("status") or "")
        if not estimate_status_allows_job_creation(st_raw):
            return (
                f"Estimate status {st_raw!r} does not allow creating a job from this page. "
                "Job creation is only allowed after customer approval (approved/accepted/awarded/po_received). "
                "Update status first, or adjust ESTIMATE_STATUSES_ALLOWED_FOR_JOB_CREATION in job_from_estimate.py."
            )
        return ""

    st.caption(
        "**Estimate = quote/proposal** (stays here until accepted by the customer). "
        "**Job = approved work** (created from an accepted estimate)."
    )
    st.caption(
        "**Job Received** is the first column on each row; the **selection checkbox** is next, then fields. "
        "Use the **action bar** below for view, edit, delete, and export."
    )
    nav1, nav2 = st.columns([1.15, 3])
    with nav1:
        st.checkbox(
            "Open new job in Job Database",
            value=True,
            key="est_job_recv_open_job_db",
            help="After Job Received success, go to Job Database with that job open.",
        )
    with nav2:
        st.caption("Uncheck to stay on this list after creating a job (filters and search unchanged).")

    # Row layout: Job action | per-row delete | estimate description | selection checkbox | data columns
    col_weights = [1.15, 0.36, 1.65, 0.48] + [1.0] * len(show_cols)
    head = st.columns(col_weights)
    with head[0]:
        st.caption("Job")
    with head[1]:
        st.caption("Del")
    with head[2]:
        st.caption("Estimate Description")
    with head[3]:
        st.caption(" ")
    for hi, col_name in enumerate(show_cols):
        with head[4 + hi]:
            lab = str(col_name).replace("_", " ")
            st.caption(lab[:22] + ("…" if len(lab) > 22 else ""))

    picked: list[str] = []
    for _, est_row in df.iterrows():
        eid = _row_estimate_id(est_row)
        if not eid:
            continue
        linked_id = _linked_job_id_for_row(est_row)
        cust_id = eid_to_customer.get(eid, "")
        rc = st.columns(col_weights)
        with rc[0]:
            if linked_id:
                st.button(
                    "Job Created",
                    key=f"job_created_{eid}",
                    disabled=True,
                    use_container_width=True,
                    help="A job is already linked to this estimate.",
                )
            else:
                reason = _job_received_disabled_reason(est_row, cust_id=cust_id)
                ready = not reason
                clicked = st.button(
                    "Job Received",
                    key=f"job_received_{eid}",
                    disabled=not ready,
                    use_container_width=True,
                    help=(
                        "Create a job from this estimate, link it, and mark job received."
                        if ready
                        else reason
                    ),
                )
                if clicked and ready:
                    res = create_job_from_estimate(str(eid), mark_job_received=True)
                    if res.ok and res.job:
                        jid = str(res.job.get("id") or "")
                        if jid and st.session_state.get("est_job_recv_open_job_db", True):
                            st.session_state[IPS_NAV_PENDING_KEY] = "Job Database"
                            st.session_state["job_mode"] = "edit"
                            st.session_state["job_edit_id"] = jid
                        st.success(res.message)
                        st.rerun()
                    elif res.message:
                        if res.error_code == "duplicate":
                            st.warning(res.message)
                        elif res.error_code == "job_received":
                            st.info(res.message)
                        else:
                            st.error(res.message)
        with rc[1]:
            row_status = str(est_row.get("status") or "").strip().lower()
            del_enabled = bool(can_edit and row_status == "draft")
            if not can_edit:
                del_help = "Only admin or estimator can delete estimates."
            elif row_status != "draft":
                del_help = "Only draft estimates can be deleted"
            else:
                del_help = "Delete this draft estimate."
            if st.button(
                "🗑",
                key=f"est_row_del_{eid}",
                disabled=not del_enabled,
                use_container_width=True,
                help=del_help,
            ):
                # Trigger the same confirmation flow the bulk action bar uses.
                st.session_state[IPS_PENDING_DELETE] = {TABLE_KEY_ESTIMATES: [str(eid)]}
                st.rerun()
        with rc[2]:
            st.text(_estimate_description_display(est_row))
        with rc[3]:
            ck = f"est_list_pick_{eid}"
            if ck not in st.session_state:
                st.session_state[ck] = eid in get_selected_ids(TABLE_KEY_ESTIMATES)
            checked = st.checkbox("", key=ck, label_visibility="collapsed")
            if checked:
                picked.append(eid)
        for ci, col in enumerate(show_cols):
            with rc[4 + ci]:
                st.text(_estimate_list_cell_text(est_row.get(col), col=str(col)))

    set_selected_ids(TABLE_KEY_ESTIMATES, picked)
    sel = picked

    df_export = df.copy()
    for _mc in _MONEY_LIST_COLUMNS:
        if _mc in df_export.columns:
            df_export[_mc] = df_export[_mc].map(_estimate_money_csv)

    actions = render_selection_action_bar(
        TABLE_KEY_ESTIMATES,
        sel,
        can_view=True,
        can_edit=can_edit,
        export_df=df_export,
        visible_df=df,
        id_column="id",
        export_filename="estimates_export.csv",
        on_bulk_selection_change=_cleanup_est_list_row_pick_keys,
    )

    if can_edit and sel and len(sel) == 1:
        row_one = df[df["id"].astype(str) == str(sel[0])]
        open_jid: str | None = None
        linked_jn = ""
        linked_jnm = ""
        qn = ""
        if not row_one.empty:
            r0 = row_one.iloc[0]
            open_jid = _linked_job_id_for_row(r0)
            qn = str(r0.get("quote_number") or "").strip()
            if open_jid and str(open_jid) in job_by_id:
                job_row = job_by_id[str(open_jid)]
                linked_jn = job_number_display(job_row.get("job_number"))
                linked_jnm = str(job_row.get("job_name") or "").strip()
        with st.container(border=True):
            st.markdown('<span class="ips-list-top-anchor"></span>', unsafe_allow_html=True)
            if open_jid:
                jdisp = job_display_label(linked_jn, linked_jnm)
                if jdisp:
                    st.markdown(f"**Linked job** · **{jdisp}**", unsafe_allow_html=True)
                else:
                    st.markdown(
                        "**Linked job** · _This estimate is linked to a job, but the job details could not be loaded._",
                        unsafe_allow_html=True,
                    )
                if qn:
                    st.caption(f"Source estimate quote · {qn}")
                if st.button("Open Job", type="primary", use_container_width=True, key="est_list_open_job_btn"):
                    st.session_state[IPS_NAV_PENDING_KEY] = "Job Database"
                    st.session_state["job_mode"] = "edit"
                    st.session_state["job_edit_id"] = str(open_jid)
                    st.rerun()
            else:
                lc1, lc2, lc3 = st.columns([1, 1, 2], gap="small")
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
                    st.caption("Creates a **J#####** job once the estimate is customer-approved (approved/accepted/awarded/po_received).")
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
        _cleanup_est_list_row_pick_keys()
        st.success("Delete completed where permitted.")
        st.rerun()


def _import_customer_status_short(cls: dict[str, Any] | None) -> str:
    if not cls:
        return "—"
    res = cls.get("resolution")
    if res == "valid_existing":
        return "ID in file (ok)"
    if res == "auto_single":
        return "Auto-matched"
    if res == "choose_ambiguous":
        return "Pick customer (multi)"
    if res == "choose_open":
        return "Pick customer"
    if res == "choose_required":
        return "Pick customer"
    return "—"


def _render_json_ips_estimate_import() -> None:
    st.markdown("### JSON estimate import")
    st.caption(
        "Upload **JSON** exports (same shape as Review / Save: `estimate_json`). "
        "Each file is matched to your **customer directory** using names in the JSON (or vendor metadata). "
        "Confirm the customer below, then use **Import JSON file(s) to database**. "
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
        for k in list(st.session_state.keys()):
            if str(k).startswith("est_import_cust_"):
                st.session_state.pop(k, None)
        st.session_state["estimates_import_sig"] = sig
        cust_rows = _fetch_customers_for_import()
        cached: list[dict] = []
        for f in uploaded:
            raw = f.getvalue()
            try:
                parsed = parse_estimate_json_bytes(raw)
                merged = coalesce_imported_estimate(parsed)
                qn = str(merged.get("quote_number", "") or "").strip()
                cls = classify_import_customer_matches(merged, cust_rows)
                cid = merged.get("customer_id")
                row_has_id = bool(cid) and cls.get("resolution") == "valid_existing"
                cached.append(
                    {
                        "file": f.name,
                        "kind": "json",
                        "merged": merged,
                        "error": None,
                        "quote_number": qn or "(will assign)",
                        "has_customer_id": "yes" if row_has_id else "needs confirmation",
                        "customer_classify": cls,
                        "customer_status": _import_customer_status_short(cls),
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
                        "customer_classify": None,
                        "customer_status": "—",
                    }
                )
        st.session_state["estimates_import_cache"] = cached

    rows: list[dict] = st.session_state["estimates_import_cache"]
    cust_rows = _fetch_customers_for_import()
    name_map = name_to_customer_id_map(cust_rows)
    all_names = build_sorted_customer_names(cust_rows)
    select_options = [PLACEHOLDER] + all_names

    preview_df = pd.DataFrame(
        [
            {
                "file": r["file"],
                "kind": r["kind"],
                "quote_number": r["quote_number"],
                "customer": r.get("customer_status", "—"),
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
        st.markdown("##### Customer for each JSON file")
        st.caption(
            "Imports must be saved against a **real customer record**. "
            "If we found a single strong name match, the customer is pre-selected — change it if needed. "
            f"You cannot import while **{PLACEHOLDER}** is selected."
        )
        for i, r in json_ready:
            cls = r.get("customer_classify") or classify_import_customer_matches(r["merged"], cust_rows)
            st.markdown(f"**{r['file']}**")
            if cls.get("message"):
                st.info(str(cls["message"]))
            key = f"est_import_cust_{i}"
            if key not in st.session_state:
                default_name: str | None = None
                if cls.get("resolution") in ("valid_existing", "auto_single") and cls.get("customer_id"):
                    cid0 = str(cls["customer_id"])
                    default_name = next((n for n, cid in name_map.items() if cid == cid0), None)
                st.session_state[key] = default_name if default_name else PLACEHOLDER
            st.selectbox(
                "Customer directory",
                select_options,
                key=key,
                help="Pick the customer this estimate belongs to. This must match a row in Customers.",
            )

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
            cust_lookup = _fetch_customers_for_import()
            nm = name_to_customer_id_map(cust_lookup)
            for i, r in json_ready:
                f = uploaded[i]
                merged = r.get("merged")
                if merged is None:
                    errors.append(f"{f.name}: nothing to import")
                    continue
                chosen = st.session_state.get(f"est_import_cust_{i}")
                cid = resolve_picked_customer_id(chosen_label=chosen, name_to_id=nm)
                if not cid:
                    errors.append(
                        f"{f.name}: choose a customer from the directory before importing "
                        f"(cannot save on {PLACEHOLDER!r})."
                    )
                    continue
                try:
                    raw = f.getvalue()
                    merged_save = dict(merged)
                    merged_save["customer_id"] = cid
                    _, suffix = insert_imported_estimate(
                        merged_save, f.name, raw, source_content_type="application/json"
                    )
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
        render_crud_list_subtitle("Search and open estimates, create new rows, or import JSON / PDF vendor quotes.")
        with st.container(border=True):
            st.markdown(
                '<span class="ips-list-top-anchor ips-estimate-topbar"></span>',
                unsafe_allow_html=True,
            )
            a1, a2 = st.columns(2, gap="small")
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
        render_crud_list_subtitle("Upload PDF vendor quotes or JSON estimate exports, then return to the editor.")
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
        render_crud_list_subtitle("Line items, proposal export, and approval — use **Back to list** when finished.")
        with st.container(border=True):
            st.markdown(
                '<span class="ips-list-top-anchor ips-estimate-topbar"></span>',
                unsafe_allow_html=True,
            )
            c1, c2 = st.columns(2, gap="small")
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
        render_estimate_editor(embedded=True)