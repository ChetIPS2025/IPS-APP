from __future__ import annotations

import html
import logging
from typing import Any

_LOG = logging.getLogger(__name__)

import pandas as pd
import streamlit as st

from auth import current_role
from branding import render_header
from db import (
    delete_rows_admin,
    fetch_by_match,
    fetch_by_match_admin,
    fetch_jobs_with_order_fallback,
    fetch_table,
    fetch_table_admin,
    insert_row_admin,
    update_rows_admin,
)

try:
    from table_actions import (
        IPS_PENDING_DELETE,
        TABLE_KEY_JOBS,
        clear_selected_ids,
        get_selected_ids,
        inject_table_action_styles,
        render_selectable_dataframe,
    )
except ImportError:
    from app.table_actions import (  # type: ignore
        IPS_PENDING_DELETE,
        TABLE_KEY_JOBS,
        clear_selected_ids,
        get_selected_ids,
        inject_table_action_styles,
        render_selectable_dataframe,
    )

try:
    from app.ips_crud_list_styles import (
        IPS_CRUD_LIST_PAGE_GAP,
        IPS_CRUD_LIST_PAGE_SPLIT,
        inject_ips_crud_list_styles,
        render_crud_list_subtitle,
    )
except ImportError:
    from ips_crud_list_styles import (  # type: ignore
        IPS_CRUD_LIST_PAGE_GAP,
        IPS_CRUD_LIST_PAGE_SPLIT,
        inject_ips_crud_list_styles,
        render_crud_list_subtitle,
    )

try:
    from services.customer_contacts import (
        contact_none_option_label,
        contact_option_label,
        inject_contact_picker_styles,
        render_contact_detail_preview,
        render_contact_quick_add_when_empty,
    )
except ImportError:
    from app.services.customer_contacts import (  # type: ignore
        contact_none_option_label,
        contact_option_label,
        inject_contact_picker_styles,
        render_contact_detail_preview,
        render_contact_quick_add_when_empty,
    )

try:
    from services.job_from_estimate import create_job_from_estimate
    from services.job_schema import (
        JOB_SOURCE_TYPE_ESTIMATE,
        JOB_SOURCE_TYPE_STANDALONE,
        JOBS_JOB_DATABASE_OVERVIEW_DISPLAY_ORDER,
        fetch_jobs_for_job_database,
    )
    from services.job_service import (
        job_number_display,
        job_row_select_label,
        next_job_number,
        sort_jobs_by_name,
        sort_jobs_by_number_then_name,
    )
except ImportError:
    from app.services.job_from_estimate import create_job_from_estimate  # type: ignore
    from app.services.job_schema import (  # type: ignore
        JOB_SOURCE_TYPE_ESTIMATE,
        JOB_SOURCE_TYPE_STANDALONE,
        JOBS_JOB_DATABASE_OVERVIEW_DISPLAY_ORDER,
        fetch_jobs_for_job_database,
    )
    from app.services.job_service import (  # type: ignore
        job_number_display,
        job_row_select_label,
        next_job_number,
        sort_jobs_by_name,
        sort_jobs_by_number_then_name,
    )

from app.utils.formatters import job_display_label


JOB_STATUSES = [
    "Draft",
    "Quoted",
    "Submitted",
    "Approved",
    "Awarded",
    "Scheduled",
    "In Progress",
    "On Hold",
    "Completed",
    "Closed",
]

# Shown in the Job Database grid; kept on the DataFrame for filters / search / logic.
_JOB_DB_COLUMNS_HIDDEN_FROM_TABLE: frozenset[str] = frozenset(
    {"customer_id", "estimate_label", "Source"}
)


def _job_db_visible_table_columns(columns: list[str]) -> list[str]:
    return [c for c in columns if c not in _JOB_DB_COLUMNS_HIDDEN_FROM_TABLE]


def _job_db_admin_read() -> bool:
    """Admin/estimator use service-role reads so linked estimate/customer rows stay visible under RLS."""
    return current_role() in {"admin", "estimator"}


def _fetch_customers_for_job_db() -> list[dict[str, Any]]:
    if _job_db_admin_read():
        try:
            return fetch_table_admin("customers", limit=5000, order_by="customer_name")
        except Exception:
            return fetch_table("customers", limit=5000, order_by="customer_name")
    return fetch_table("customers", limit=5000, order_by="customer_name")


def _fetch_estimates_for_job_db() -> list[dict[str, Any]]:
    """Columns for labels + optional scope; fall back if a column is missing."""
    if _job_db_admin_read():
        for cols in (
            "id,quote_number,customer_id,proposal_total,status,job_id,scope_of_work",
            "id,quote_number,customer_id,proposal_total,status,job_id",
        ):
            try:
                return fetch_table_admin(
                    "estimates",
                    columns=cols,
                    limit=5000,
                    order_by="quote_number",
                )
            except Exception:
                continue
        try:
            return fetch_table_admin("estimates", limit=5000, order_by="quote_number")
        except Exception:
            return fetch_table("estimates", limit=5000, order_by="quote_number")
    for cols in (
        "id,quote_number,customer_id,proposal_total,status,job_id,scope_of_work",
        "id,quote_number,customer_id,proposal_total,status,job_id",
    ):
        try:
            return fetch_table(
                "estimates",
                columns=cols,
                limit=5000,
                order_by="quote_number",
            )
        except Exception:
            continue
    return fetch_table("estimates", limit=5000, order_by="quote_number")


def _fetch_contacts_for_job_database(customer_id: str) -> list[dict[str, Any]]:
    """Same pattern as Estimates editor: admin read for internal roles (RLS)."""
    admin_read = current_role() in {"admin", "estimator"}
    cid = str(customer_id or "").strip()
    if not cid:
        return []
    try:
        if admin_read:
            rows = fetch_by_match_admin("customer_contacts", {"customer_id": cid}, limit=500)
        else:
            rows = fetch_by_match("customer_contacts", {"customer_id": cid}, limit=500)
    except Exception:
        return []
    rows = list(rows or [])
    rows = [r for r in rows if bool(r.get("is_active", True))]

    def _sort_key(r: dict) -> tuple:
        prim = 0 if r.get("is_primary") else 1
        name = str(r.get("contact_name") or "").strip().lower()
        return (prim, name)

    rows.sort(key=_sort_key)
    return rows


def _fetch_estimate_row_by_id(estimate_id: str) -> dict[str, Any] | None:
    eid = str(estimate_id or "").strip()
    if not eid:
        return None
    if _job_db_admin_read():
        try:
            rows = fetch_by_match_admin("estimates", {"id": eid}, limit=1)
            return rows[0] if rows else None
        except Exception:
            pass
    try:
        rows = fetch_by_match("estimates", {"id": eid}, limit=1)
        return rows[0] if rows else None
    except Exception:
        return None


def _contact_row_by_id(contact_id: str) -> dict[str, Any] | None:
    cid = str(contact_id or "").strip()
    if not cid:
        return None
    if _job_db_admin_read():
        try:
            rows = fetch_by_match_admin("customer_contacts", {"id": cid}, limit=1)
            return rows[0] if rows else None
        except Exception:
            pass
    try:
        rows = fetch_by_match("customer_contacts", {"id": cid}, limit=1)
        return rows[0] if rows else None
    except Exception:
        return None


def _customer_display_name_for_id(
    customer_id: str | None,
    customers: list[dict[str, Any]],
    name_by_id: dict[str, str],
) -> str:
    cid = str(customer_id or "").strip()
    if not cid:
        return ""
    n = name_by_id.get(cid)
    if n:
        return str(n).strip()
    for c in customers:
        if str(c.get("id") or "").strip() == cid:
            return str(c.get("customer_name") or "").strip()
    return ""


def _text_snippet(text: str, *, max_len: int = 600) -> str:
    t = (text or "").strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


def _safe_date_value(value):
    if value is None or str(value).strip() == "":
        return None
    return value


def _clear_job_mode() -> None:
    st.session_state.pop("job_mode", None)
    st.session_state.pop("job_edit_id", None)


def _job_form_linked_estimate_id(estimate_options: dict[str, Any], linked_label: str) -> str | None:
    """Map the Linked estimate select label to an estimate UUID, or ``None`` for a standalone job."""
    if not str(linked_label or "").strip():
        return None
    raw = estimate_options.get(linked_label)
    if raw is None:
        return None
    s = str(raw).strip()
    return s or None


def _render_job_form_panel(
    *,
    mode: str,
    can_edit: bool,
    selected_job: dict | None,
    jobs: list[dict],
    has_job_number_column: bool,
    customers: list[dict],
    estimates: list[dict],
    customer_name_by_id: dict[str, str],
    estimate_label_map: dict[str, str],
    estimate_quote_by_id: dict[str, str],
    estimate_detail: dict[str, Any] | None = None,
) -> None:
    """Right-side bordered panel: add/edit job form."""
    with st.container(border=True):
        title = "Add Job" if mode == "add" else "Edit Job"
        st.markdown(f"### {title}")
        if mode == "add":
            st.caption(
                "Standalone job — **no estimate required**. Leave **Linked estimate** empty, "
                "or pick a quote only if you are attaching this job to an existing estimate."
            )

        if mode == "edit" and selected_job and selected_job.get("estimate_id"):
            st.markdown("#### Estimate source")
            _eid = str(selected_job.get("estimate_id"))
            _eq = str(
                estimate_quote_by_id.get(_eid)
                or (estimate_detail or {}).get("quote_number")
                or ""
            ).strip()
            _est = estimate_detail or {}
            _st = str(_est.get("status") or "").strip()
            _cust = _customer_display_name_for_id(
                _est.get("customer_id"),
                customers,
                customer_name_by_id,
            )
            _scope = _text_snippet(str(_est.get("scope_of_work") or ""))
            with st.container(border=True):
                st.markdown('<span class="ips-list-top-anchor"></span>', unsafe_allow_html=True)
                line_parts: list[str] = []
                if _eq:
                    line_parts.append(f"Source estimate **{_eq}**")
                else:
                    line_parts.append(f"Source estimate id `{_eid[:8]}…`")
                if _st:
                    line_parts.append(f"estimate status **{_st}**")
                if _cust:
                    line_parts.append(f"customer **{_cust}**")
                st.markdown("**Source** · " + " · ".join(line_parts), unsafe_allow_html=True)
                st.caption("This job originated from an estimate (jobs.estimate_id is set).")
                if _scope:
                    st.caption("Scope (from estimate)")
                    st.markdown(
                        f"<div style='white-space:pre-wrap;font-size:0.88rem'>{html.escape(_scope)}</div>",
                        unsafe_allow_html=True,
                    )

        customer_options: dict[str, str] = {}
        for c in customers:
            nm = str(c.get("customer_name") or "").strip()
            cid = str(c.get("id") or "").strip()
            if nm and cid:
                customer_options[nm] = cid

        estimate_options: dict[str, Any] = {"": None}
        for e in estimates:
            eid = str(e.get("id") or "").strip()
            if not eid:
                continue
            lab = estimate_label_map.get(eid)
            if lab:
                estimate_options[lab] = eid
        if mode == "edit" and selected_job and selected_job.get("estimate_id"):
            _leid = str(selected_job.get("estimate_id"))
            existing_ids = {str(v) for v in estimate_options.values() if v is not None}
            if _leid not in existing_ids:
                lab = estimate_label_map.get(_leid)
                if not lab and estimate_detail:
                    qn = str(estimate_detail.get("quote_number") or "").strip()
                    cn = _customer_display_name_for_id(
                        estimate_detail.get("customer_id"),
                        customers,
                        customer_name_by_id,
                    )
                    _est_status_lbl = str(estimate_detail.get("status") or "").strip()
                    lab = (
                        f"{qn} | {cn} | {_est_status_lbl}"
                        if qn or cn or _est_status_lbl
                        else f"Estimate ({_leid[:8]}…)"
                    )
                elif not lab:
                    lab = f"Estimate ({_leid[:8]}…)"
                estimate_options[lab] = _leid

        def current_value(field_name, default=""):
            if selected_job:
                value = selected_job.get(field_name, default)
                return "" if value is None else value
            return default

        _ro = not can_edit

        st.markdown("#### Customer & job")
        c1, c2 = st.columns(2, gap="small")
        cust_keys = [""] + sorted(customer_options.keys())
        selected_cust_name = ""
        if selected_job:
            scid = str(selected_job.get("customer_id") or "").strip()
            if scid:
                selected_cust_name = _customer_display_name_for_id(
                    scid,
                    customers,
                    customer_name_by_id,
                )
                if selected_cust_name and selected_cust_name not in customer_options:
                    customer_options[selected_cust_name] = scid
                    cust_keys = [""] + sorted(customer_options.keys())
        cust_index = cust_keys.index(selected_cust_name) if selected_cust_name in cust_keys else 0
        customer_name = c1.selectbox("Customer", cust_keys, index=cust_index, disabled=_ro, key="job_form_customer")
        job_name = c2.text_input("Job Name", value=current_value("job_name"), disabled=_ro, key="job_form_job_name")

        selected_contact_id: str | None = None
        cust_uuid = customer_options.get(customer_name) if customer_name else None
        if cust_uuid:
            inject_contact_picker_styles()
            contacts = _fetch_contacts_for_job_database(str(cust_uuid))
            cur_ct = str(current_value("customer_contact_id") or "").strip()
            if cur_ct:
                cids = {str(c.get("id") or "") for c in contacts}
                if cur_ct not in cids:
                    orphan = _contact_row_by_id(cur_ct)
                    if orphan:
                        contacts = [orphan] + contacts
            if not contacts:
                st.caption("No contacts found for this customer.")
                render_contact_quick_add_when_empty(
                    customer_id=str(cust_uuid),
                    key_prefix="job",
                    disabled=_ro,
                )
                selected_contact_id = None
            else:
                cur_ct = str(current_value("customer_contact_id") or "").strip()
                by_id = {str(c.get("id") or ""): c for c in contacts}
                chosen_id: str | None = cur_ct if cur_ct in by_id else None
                if chosen_id is None:
                    primary = next((c for c in contacts if c.get("is_primary")), None)
                    if primary and primary.get("id"):
                        chosen_id = str(primary["id"])
                    elif len(contacts) == 1 and contacts[0].get("id"):
                        chosen_id = str(contacts[0]["id"])

                labels = ["(none)"] + [contact_option_label(c) for c in contacts]
                ct_ids: list[str | None] = [None] + [str(c["id"]) for c in contacts]
                try:
                    ct_idx = ct_ids.index(str(chosen_id)) if chosen_id else 0
                except ValueError:
                    ct_idx = 0
                    chosen_id = None
                ct_idx = min(max(ct_idx, 0), len(labels) - 1)
                ct_sel = st.selectbox(
                    "Contact",
                    options=list(range(len(labels))),
                    index=ct_idx,
                    format_func=lambda i: labels[i],
                    disabled=_ro,
                    key=f"job_form_contact_{cust_uuid}",
                    help="Optional: primary contact for this job.",
                )
                selected_contact_id = ct_ids[int(ct_sel)]
                render_contact_detail_preview(by_id.get(str(selected_contact_id or "")))
        else:
            st.caption("Select a customer to choose a contact.")

        st.markdown("#### Job number & location")
        if has_job_number_column and selected_job:
            st.text_input(
                "Job Number",
                value=str(current_value("job_number") or ""),
                disabled=True,
                help="Assigned automatically when the job is created.",
                key="job_form_job_number",
            )
        elif has_job_number_column and mode == "add":
            st.caption(f"Next job number: **{next_job_number()}** (saved when you create the job).")

        location = st.text_input("Location", value=current_value("location"), disabled=_ro, key="job_form_location")

        st.markdown("#### Status & linked estimate")
        if mode == "add":
            st.caption("*Linked estimate* is optional — leave the first row selected for a job with no quote.")
        c5, c6 = st.columns(2, gap="small")
        status_options = list(JOB_STATUSES)
        current_status = str(current_value("status", "Draft") or "Draft").strip() or "Draft"
        if current_status not in status_options:
            status_options = status_options + [current_status]
        status_idx = status_options.index(current_status)
        status = c5.selectbox(
            "Status",
            status_options,
            index=status_idx,
            disabled=_ro,
            key="job_form_status",
        )

        estimate_labels = [""] + [k for k in estimate_options.keys() if k]
        current_estimate_label = ""
        if selected_job and selected_job.get("estimate_id"):
            _seid = str(selected_job.get("estimate_id"))
            current_estimate_label = estimate_label_map.get(_seid, "")
            if not current_estimate_label:
                for lab, eid in estimate_options.items():
                    if lab and str(eid) == _seid:
                        current_estimate_label = lab
                        break
        _link_lbl = "Linked estimate (optional)" if mode == "add" else "Linked estimate"
        linked_estimate = c6.selectbox(
            _link_lbl,
            estimate_labels,
            index=estimate_labels.index(current_estimate_label) if current_estimate_label in estimate_labels else 0,
            disabled=_ro,
            key="job_form_linked_estimate",
            help="Leave blank for a standalone job. Pick a row only when this job should reference an estimate.",
        )

        st.markdown("#### Team & awarded amount")
        c7, c8, c9 = st.columns(3, gap="small")
        project_manager = c7.text_input("Project Manager", value=current_value("project_manager"), disabled=_ro, key="job_form_pm")
        supervisor = c8.text_input("Supervisor", value=current_value("supervisor"), disabled=_ro, key="job_form_supervisor")
        awarded_amount = c9.number_input(
            "Awarded Amount",
            min_value=0.0,
            value=float(current_value("awarded_amount", 0) or 0),
            step=100.0,
            format="%.2f",
            disabled=_ro,
            key="job_form_awarded_amount",
        )

        st.markdown("#### Dates")
        c10, c11, c12 = st.columns(3, gap="small")
        start_date = c10.text_input("Start Date (YYYY-MM-DD)", value=str(current_value("start_date")), disabled=_ro, key="job_form_start")
        target_completion_date = c11.text_input(
            "Target Completion (YYYY-MM-DD)",
            value=str(current_value("target_completion_date")),
            disabled=_ro,
            key="job_form_target",
        )
        completed_date = c12.text_input(
            "Completed Date (YYYY-MM-DD)",
            value=str(current_value("completed_date")),
            disabled=_ro,
            key="job_form_completed",
        )

        st.markdown("#### Notes")
        notes = st.text_area(
            "Notes",
            value=current_value("notes"),
            disabled=_ro,
            height=80,
            key="job_form_notes",
        )

        if not can_edit:
            st.info("Only admin or estimator users can add or update jobs.")
            return

        b1, b2 = st.columns(2, gap="small")
        if mode == "add":
            if b1.button("Create Job", type="primary", use_container_width=True, disabled=_ro, key="job_form_create"):
                if not customer_name:
                    st.error("Customer required")
                    st.stop()
                if not job_name.strip():
                    st.error("Job Name required")
                    st.stop()
                linked_eid = _job_form_linked_estimate_id(estimate_options, linked_estimate)
                payload = {
                    "customer_id": customer_options[customer_name],
                    "customer_contact_id": selected_contact_id,
                    "job_name": job_name.strip(),
                    "location": location.strip(),
                    "status": status,
                    "estimate_id": linked_eid,
                    "source_type": JOB_SOURCE_TYPE_ESTIMATE if linked_eid else JOB_SOURCE_TYPE_STANDALONE,
                    "project_manager": project_manager.strip(),
                    "supervisor": supervisor.strip(),
                    "start_date": _safe_date_value(start_date.strip()),
                    "target_completion_date": _safe_date_value(target_completion_date.strip()),
                    "completed_date": _safe_date_value(completed_date.strip()),
                    "awarded_amount": float(awarded_amount or 0),
                    "notes": notes.strip(),
                }
                if has_job_number_column:
                    payload["job_number"] = next_job_number()
                insert_row_admin("jobs", payload)
                _clear_job_mode()
                st.success("Job created.")
                st.rerun()
        else:
            if b1.button("Update Job", type="primary", use_container_width=True, disabled=_ro, key="job_form_update"):
                if not selected_job:
                    st.error("Select a job first.")
                    st.stop()
                if not customer_name:
                    st.error("Customer required")
                    st.stop()
                if not job_name.strip():
                    st.error("Job Name required")
                    st.stop()
                linked_eid = _job_form_linked_estimate_id(estimate_options, linked_estimate)
                payload = {
                    "customer_id": customer_options[customer_name],
                    "customer_contact_id": selected_contact_id,
                    "job_name": job_name.strip(),
                    "location": location.strip(),
                    "status": status,
                    "estimate_id": linked_eid,
                    "source_type": JOB_SOURCE_TYPE_ESTIMATE if linked_eid else JOB_SOURCE_TYPE_STANDALONE,
                    "project_manager": project_manager.strip(),
                    "supervisor": supervisor.strip(),
                    "start_date": _safe_date_value(start_date.strip()),
                    "target_completion_date": _safe_date_value(target_completion_date.strip()),
                    "completed_date": _safe_date_value(completed_date.strip()),
                    "awarded_amount": float(awarded_amount or 0),
                    "notes": notes.strip(),
                }
                update_rows_admin("jobs", payload, {"id": selected_job["id"]})
                _clear_job_mode()
                st.success("Job updated.")
                st.rerun()

        if b2.button("Cancel", use_container_width=True, key="job_form_cancel"):
            _clear_job_mode()
            st.rerun()


def _build_jobs_overview_dataframe(
    jobs_df: pd.DataFrame,
    *,
    customer_name_by_id: dict[str, str],
    estimate_label_map: dict[str, str],
    estimate_quote_by_id: dict[str, str],
    contact_label_by_id: dict[str, str],
) -> pd.DataFrame:
    """Augment jobs rows for overview (customer name, ``source_type``, estimate labels, linked-quote copy)."""
    if jobs_df.empty:
        return jobs_df
    out = jobs_df.copy()
    if "customer_id" in out.columns:

        def _cust_name_cell(v) -> str:
            if v is None:
                return ""
            try:
                if pd.isna(v):
                    return ""
            except Exception:
                pass
            return customer_name_by_id.get(str(v).strip(), "")

        out["customer_name"] = out["customer_id"].map(_cust_name_cell)
    else:
        out["customer_name"] = ""
    if "estimate_id" in out.columns:

        def _est_label_cell(v) -> str:
            if v is None:
                return ""
            try:
                if pd.isna(v):
                    return ""
            except Exception:
                pass
            return estimate_label_map.get(str(v).strip(), "")

        out["estimate_label"] = out["estimate_id"].map(_est_label_cell)

        def _quote_for_estimate_cell(v) -> str:
            if v is None or str(v).strip() == "":
                return ""
            q = estimate_quote_by_id.get(str(v), "")
            return f"Estimate {q}" if q else ""

        out["Quote (estimate)"] = out["estimate_id"].map(_quote_for_estimate_cell)

        def _source_cell(v) -> str:
            if v is None:
                return "—"
            try:
                if pd.isna(v):
                    return "—"
            except Exception:
                pass
            eid = str(v).strip()
            if not eid:
                return "—"
            q = estimate_quote_by_id.get(eid, "")
            return f"From estimate: {q}" if q else "From estimate"

        out["Source"] = out["estimate_id"].map(_source_cell)
    else:
        out["estimate_label"] = ""
        out["Quote (estimate)"] = ""
        out["Source"] = "—"

    if "customer_contact_id" in out.columns:

        def _contact_cell(v) -> str:
            if v is None:
                return ""
            try:
                if pd.isna(v):
                    return ""
            except Exception:
                pass
            return contact_label_by_id.get(str(v).strip(), "")

        out["Contact"] = out["customer_contact_id"].map(_contact_cell)
    else:
        out["Contact"] = ""
    # User-facing estimate link; ``Source`` is retained for the Source filter and search.
    if "Source" in out.columns:
        out["Linked estimate"] = out["Source"].astype(str)
    else:
        out["Linked estimate"] = "—"
    return out


def _filter_jobs_overview_dataframe(
    filtered: pd.DataFrame,
    *,
    selected_customer: str,
    selected_status: str,
    selected_source: str,
    search: str,
    bypass: bool,
) -> pd.DataFrame:
    """Apply customer/status/source/search filters (matches Source cell text for estimate-linked rows)."""
    out = filtered.copy()
    if not bypass:
        if selected_customer != "All" and "customer_name" in out.columns:
            out = out[out["customer_name"].astype(str) == selected_customer]

        if selected_status != "All" and "status" in out.columns:
            out = out[out["status"].astype(str) == selected_status]

        if selected_source != "All" and "Source" in out.columns:
            src_series = out["Source"].astype(str)
            is_from_estimate = src_series.str.contains("From estimate", case=False, na=False)
            if selected_source == "Estimate":
                out = out[is_from_estimate]
            elif selected_source == "Other":
                out = out[~is_from_estimate]

    if search.strip():
        s = search.strip().lower()
        mask = out.astype(str).apply(lambda col: col.str.lower().str.contains(s, na=False))
        out = out[mask.any(axis=1)]
    return out


def _render_job_db_top_bar(
    *,
    can_edit: bool,
    estimates: list[dict[str, Any]],
    estimate_label_map: dict[str, str],
) -> None:
    """Primary actions: create job, refresh, convert from estimate (same rhythm as Estimates top bar)."""
    with st.container(border=True):
        st.markdown(
            '<span class="ips-list-top-anchor ips-job-topbar"></span>',
            unsafe_allow_html=True,
        )
        st.caption(
            "**Create New Job** — standalone work (no estimate). "
            "**Create job from estimate** — converts an approved quote and links the new job."
        )
        c1, c2, c3 = st.columns([1.0, 1.0, 1.45], gap="small")
        with c1:
            if st.button(
                "Create New Job",
                type="primary",
                use_container_width=True,
                disabled=not can_edit,
                key="job_top_create",
            ):
                st.session_state["job_mode"] = "add"
                st.session_state.pop("job_edit_id", None)
                st.rerun()
        with c2:
            if st.button("Refresh", type="secondary", use_container_width=True, key="job_top_refresh"):
                st.rerun()
        with c3:
            if not can_edit:
                st.caption("Sign in as admin or estimator to convert estimates.")
            else:
                ecandidates = [e for e in estimates if e.get("id") is not None and not str(e.get("job_id") or "").strip()]
                if not ecandidates:
                    st.caption("No estimates without a linked job.")
                else:
                    labels = [estimate_label_map.get(str(e.get("id")), str(e.get("id"))) for e in ecandidates]
                    idx_opts = list(range(len(ecandidates)))
                    pick = st.selectbox(
                        "Convert estimate → job",
                        idx_opts,
                        format_func=lambda i: labels[int(i)],
                        key="job_conv_est",
                        label_visibility="visible",
                    )
                    if st.button(
                        "Create job from estimate",
                        type="secondary",
                        use_container_width=True,
                        key="job_conv_go",
                    ):
                        eid = str(ecandidates[int(pick)].get("id") or "")
                        res = create_job_from_estimate(eid)
                        if res.ok:
                            st.success(res.message)
                            st.rerun()
                        else:
                            st.error(res.message)


def _render_job_db_debug_expander(*, jobs: list[dict[str, Any]], admin_read: bool) -> None:
    with st.expander("Database debug & checklist", expanded=False):
        st.write("DEBUG - Job Count:", len(jobs))
        preview = jobs[:12] if jobs else []
        st.write("DEBUG - Jobs Raw (first rows):", preview)
        st.checkbox(
            "Bypass customer / status / source filters (search still applies)",
            key="job_db_bypass_filters",
        )
        try:
            from app.config import settings

            url = (getattr(settings, "supabase_url", "") or "").strip()
            pk = (
                (getattr(settings, "supabase_publishable_key", "") or "").strip()
                or (getattr(settings, "supabase_anon_key", "") or "").strip()
            )
            st.caption(
                f"Supabase URL set: {bool(url)} · Public key set: {bool(pk)} · "
                f"Admin/service reads for this page: {admin_read} · Table: public.jobs"
            )
        except Exception:
            st.caption("Could not read local settings for debug summary.")

        st.caption(
            "If the count is zero but Supabase shows rows: check RLS policies for `authenticated`, "
            "or ensure `SUPABASE_SERVICE_ROLE_KEY` / `SUPABASE_SECRET_KEY` is set for admin/estimator reads."
        )


def render() -> None:
    render_header("Job Database")
    inject_ips_crud_list_styles()
    inject_table_action_styles()
    render_crud_list_subtitle(
        "Search and maintain jobs — standalone or estimate-linked — and keep customer contacts aligned."
    )
    st.caption(
        "**Standalone jobs** use **Create New Job** (no quote). **Estimate-linked jobs** use **Convert estimate → job** "
        "or **Job Received** on the Estimates list once the quote is customer-approved."
    )

    can_edit = current_role() in {"admin", "estimator"}
    st.session_state.setdefault("job_db_bypass_filters", True)

    customers: list[dict[str, Any]] = []
    estimates: list[dict[str, Any]] = []
    try:
        customers = list(_fetch_customers_for_job_db() or [])
    except Exception as exc:
        _LOG.exception("Job Database: could not load customers")
        st.error(f"Database error (customers): {exc}")
    try:
        estimates = list(_fetch_estimates_for_job_db() or [])
    except Exception as exc:
        _LOG.exception("Job Database: could not load estimates")
        st.error(f"Database error (estimates): {exc}")

    admin_read = _job_db_admin_read()
    jobs: list[dict[str, Any]] = []
    has_job_number_column = False
    try:
        jobs, has_job_number_column = fetch_jobs_for_job_database(limit=5000, admin_read=admin_read)
    except Exception as exc:
        _LOG.exception("Job Database: fetch_jobs_for_job_database failed")
        st.error(f"Database error (jobs): {exc}")
        try:
            jobs = list(fetch_jobs_with_order_fallback(limit=5000, use_admin=admin_read) or [])
            has_job_number_column = bool(jobs) and any("job_number" in (r or {}) for r in jobs)
            if jobs:
                st.info("Loaded jobs using a relaxed query (typed column list failed).")
        except Exception as exc2:
            _LOG.exception("Job Database: fetch_jobs_with_order_fallback failed")
            st.error(f"Database error (jobs fallback): {exc2}")
            jobs = []
            has_job_number_column = False

    if has_job_number_column:
        jobs = sort_jobs_by_number_then_name(jobs)
    else:
        jobs = sort_jobs_by_name(jobs)

    customer_name_by_id: dict[str, str] = {}
    for c in customers:
        cid = str(c.get("id") or "").strip()
        if cid:
            customer_name_by_id[cid] = str(c.get("customer_name") or "").strip()

    estimate_label_map: dict[str, str] = {}
    for e in estimates:
        eid = str(e.get("id") or "").strip()
        if not eid:
            continue
        ecust = str(e.get("customer_id") or "").strip()
        cn = customer_name_by_id.get(ecust, "")
        estimate_label_map[eid] = f"{e.get('quote_number', '')} | {cn} | {e.get('status', '')}"

    estimate_quote_by_id = {
        str(e.get("id")): str(e.get("quote_number") or "").strip()
        for e in estimates
        if e.get("id") is not None
    }

    contact_label_by_id: dict[str, str] = {}
    try:
        if admin_read:
            ct_rows = fetch_table_admin("customer_contacts", limit=10000, order_by=None)
        else:
            ct_rows = fetch_table("customer_contacts", limit=10000, order_by=None)
        for cr in ct_rows or []:
            rid = str(cr.get("id") or "").strip()
            if rid:
                contact_label_by_id[rid] = contact_option_label(cr)
    except Exception:
        pass

    _render_job_db_top_bar(can_edit=can_edit, estimates=estimates, estimate_label_map=estimate_label_map)
    _render_job_db_debug_expander(jobs=jobs, admin_read=admin_read)

    jobs_df = pd.DataFrame(jobs)

    st.markdown("### Jobs overview")
    st.caption(
        "**Source** shows estimate links; **Quote (estimate)**, **customer**, and **Contact** summarize linked data."
    )

    mode = st.session_state.get("job_mode")
    panel_open = bool(can_edit and mode in ("add", "edit"))
    if panel_open:
        main_col, side_col = st.columns(IPS_CRUD_LIST_PAGE_SPLIT, gap=IPS_CRUD_LIST_PAGE_GAP)
    else:
        main_col = st.container()
        side_col = None

    with main_col:
        if jobs_df.empty:
            st.warning("No jobs found in database.")
            if can_edit and not panel_open:
                with st.container(border=True):
                    st.markdown(
                        '<span class="ips-list-top-anchor ips-job-topbar"></span>',
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        "Create New Job",
                        key="job_add_btn_empty",
                        type="primary",
                        use_container_width=True,
                    ):
                        st.session_state["job_mode"] = "add"
                        st.session_state.pop("job_edit_id", None)
                        st.rerun()
                return
            if not panel_open:
                return

            st.caption("Use **Create New Job** in the top bar, or **Convert estimate → job**.")
        else:
            jobs_df = _build_jobs_overview_dataframe(
                jobs_df,
                customer_name_by_id=customer_name_by_id,
                estimate_label_map=estimate_label_map,
                estimate_quote_by_id=estimate_quote_by_id,
                contact_label_by_id=contact_label_by_id,
            )

            with st.container(border=True):
                st.markdown('<span class="ips-list-top-anchor"></span>', unsafe_allow_html=True)
                st.markdown("##### Filters & search")
                f1, f2, f3, f4 = st.columns([1.05, 1.05, 2.35, 1.0], gap="small")
                customer_names = sorted(
                    [c.get("customer_name", "") for c in customers if str(c.get("customer_name", "")).strip()]
                )
                with f1:
                    selected_customer = st.selectbox(
                        "Filter Customer",
                        ["All"] + customer_names,
                        disabled="customer_id" not in jobs_df.columns,
                        key="job_filt_customer",
                    )
                with f2:
                    selected_status = st.selectbox(
                        "Filter Status",
                        ["All"] + JOB_STATUSES,
                        disabled="status" not in jobs_df.columns,
                        key="job_filt_status",
                    )
                with f3:
                    _search_hint = (
                        "Source, quote, contact, job_number, job_name, customer, status, …"
                        if has_job_number_column
                        else "Source, quote, contact, job_name, customer, status, …"
                    )
                    search = st.text_input(
                        "Search Jobs",
                        placeholder=_search_hint,
                        key="job_filt_search",
                    )
                with f4:
                    selected_source = st.selectbox(
                        "Source",
                        ["All", "Estimate", "Other"],
                        disabled="Source" not in jobs_df.columns,
                        help="Estimate = rows linked to an estimate (same rule as the **Linked estimate** column).",
                        key="job_filt_source",
                    )

            bypass = st.session_state.get("job_db_bypass_filters", True)
            filtered = _filter_jobs_overview_dataframe(
                jobs_df,
                selected_customer=selected_customer,
                selected_status=selected_status,
                selected_source=selected_source,
                search=search,
                bypass=bypass,
            )

            show_cols: list[str] = []
            if has_job_number_column and "job_number" in filtered.columns:
                show_cols.append("job_number")
            for c in (
                "Linked estimate",
                "job_name",
                "customer_name",
                "source_type",
                "Quote (estimate)",
                "Contact",
                "status",
            ):
                if c in filtered.columns and c not in show_cols:
                    show_cols.append(c)
            show_cols.extend(
                [c for c in JOBS_JOB_DATABASE_OVERVIEW_DISPLAY_ORDER if c in filtered.columns and c not in show_cols]
            )
            visible_cols = _job_db_visible_table_columns(show_cols)

            with st.container(border=True):
                st.markdown('<span class="ips-list-top-anchor"></span>', unsafe_allow_html=True)
                st.markdown("##### Job list")
                st.caption("Checkbox on the **left**. Select rows, then use **Actions** below the table.")
                if "id" not in filtered.columns:
                    st.dataframe(filtered[visible_cols], use_container_width=True, hide_index=True)
                else:
                    render_selectable_dataframe(
                        filtered,
                        table_key=TABLE_KEY_JOBS,
                        id_column="id",
                        columns=visible_cols,
                        editor_key="job_db_sel_editor",
                    )

            sel_ids = get_selected_ids(TABLE_KEY_JOBS)
            n_sel = len(sel_ids)
            one = n_sel == 1
            none = n_sel == 0

            with st.container(border=True):
                st.markdown('<span class="ips-ta-bar-anchor"></span>', unsafe_allow_html=True)
                left, b1, b2 = st.columns([1.35, 1, 1], gap="small")
                with left:
                    st.markdown(
                        f'<span class="ips-ta-summary"><span class="ips-ta-num">{n_sel}</span> selected</span>',
                        unsafe_allow_html=True,
                    )
                with b1:
                    if st.button(
                        "Edit",
                        key="job_edit_btn",
                        type="secondary",
                        use_container_width=True,
                        disabled=(not can_edit or not one),
                    ):
                        st.session_state["job_mode"] = "edit"
                        st.session_state["job_edit_id"] = str(sel_ids[0])
                        st.rerun()
                with b2:
                    if st.button(
                        "Delete",
                        key="job_delete_btn",
                        type="secondary",
                        use_container_width=True,
                        disabled=(not can_edit or none),
                    ):
                        pending = st.session_state.get(IPS_PENDING_DELETE)
                        if not isinstance(pending, dict):
                            pending = {}
                            st.session_state[IPS_PENDING_DELETE] = pending
                        pending[TABLE_KEY_JOBS] = list(sel_ids)
                        st.rerun()

            pend = st.session_state.get(IPS_PENDING_DELETE) or {}
            if isinstance(pend, dict) and pend.get(TABLE_KEY_JOBS):
                pend_ids = [str(x) for x in pend.get(TABLE_KEY_JOBS) or [] if str(x).strip()]
                if pend_ids:
                    with st.container(border=True):
                        st.warning(f"Delete **{len(pend_ids)}** job(s)? This cannot be undone.")
                        dc1, dc2 = st.columns(2, gap="small")
                        with dc1:
                            if st.button(
                                "Confirm delete",
                                type="primary",
                                use_container_width=True,
                                key="job_db_confirm_delete",
                            ):
                                for jid in pend_ids:
                                    try:
                                        delete_rows_admin("jobs", {"id": jid})
                                    except Exception as exc:
                                        st.error(f"Could not delete job {jid}: {exc}")
                                pend.pop(TABLE_KEY_JOBS, None)
                                clear_selected_ids(TABLE_KEY_JOBS)
                                _clear_job_mode()
                                st.success("Delete completed where permitted.")
                                st.rerun()
                        with dc2:
                            if st.button("Cancel", use_container_width=True, key="job_db_cancel_delete"):
                                pend.pop(TABLE_KEY_JOBS, None)
                                st.rerun()

    if panel_open and side_col is not None:
        with side_col:
            selected_job = None
            estimate_detail: dict[str, Any] | None = None
            if mode == "edit":
                edit_id = st.session_state.get("job_edit_id")
                if edit_id:
                    selected_job = next((j for j in jobs if str(j.get("id")) == str(edit_id)), None)
                if not selected_job:
                    st.error("Selected job could not be loaded. It may have been deleted.")
                    _clear_job_mode()
                    st.rerun()
                if selected_job and selected_job.get("estimate_id"):
                    eid_est = str(selected_job.get("estimate_id"))
                    estimate_detail = next(
                        (e for e in estimates if str(e.get("id")) == eid_est),
                        None,
                    )
                    if not estimate_detail:
                        estimate_detail = _fetch_estimate_row_by_id(eid_est)
            _render_job_form_panel(
                mode=str(mode),
                can_edit=can_edit,
                selected_job=selected_job,
                jobs=jobs,
                has_job_number_column=has_job_number_column,
                customers=customers,
                estimates=estimates,
                customer_name_by_id=customer_name_by_id,
                estimate_label_map=estimate_label_map,
                estimate_quote_by_id=estimate_quote_by_id,
                estimate_detail=estimate_detail,
            )