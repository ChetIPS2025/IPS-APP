from __future__ import annotations

import pandas as pd
import streamlit as st

from auth import current_role
from branding import render_header
from db import delete_rows_admin, fetch_table, insert_row, update_rows

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
    from services.customer_contacts import (
        contact_none_option_label,
        contact_option_label,
        fetch_contacts_for_customer,
        inject_contact_picker_styles,
        render_contact_detail_preview,
        render_contact_quick_add_when_empty,
    )
except ImportError:
    from app.services.customer_contacts import (  # type: ignore
        contact_none_option_label,
        contact_option_label,
        fetch_contacts_for_customer,
        inject_contact_picker_styles,
        render_contact_detail_preview,
        render_contact_quick_add_when_empty,
    )

try:
    from services.job_schema import (
        JOBS_JOB_DATABASE_OVERVIEW_DISPLAY_ORDER,
        fetch_jobs_for_job_database,
    )
    from services.job_service import (
        job_row_select_label,
        next_job_number,
        sort_jobs_by_name,
        sort_jobs_by_number_then_name,
    )
except ImportError:
    from app.services.job_schema import (  # type: ignore
        JOBS_JOB_DATABASE_OVERVIEW_DISPLAY_ORDER,
        fetch_jobs_for_job_database,
    )
    from app.services.job_service import (  # type: ignore
        job_row_select_label,
        next_job_number,
        sort_jobs_by_name,
        sort_jobs_by_number_then_name,
    )


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


def _safe_date_value(value):
    if value is None or str(value).strip() == "":
        return None
    return value


def _clear_job_mode() -> None:
    st.session_state.pop("job_mode", None)
    st.session_state.pop("job_edit_id", None)


def _render_job_form_panel(
    *,
    mode: str,
    can_edit: bool,
    selected_job: dict | None,
    jobs: list[dict],
    has_job_number_column: bool,
    customers: list[dict],
    estimates: list[dict],
    customer_name_by_id: dict,
    estimate_label_map: dict,
    estimate_quote_by_id: dict,
) -> None:
    """Right-side bordered panel: add/edit job form."""
    with st.container(border=True):
        title = "Add Job" if mode == "add" else "Edit Job"
        st.markdown(f"### {title}")

        if mode == "edit" and selected_job and selected_job.get("estimate_id"):
            _eq = str(estimate_quote_by_id.get(str(selected_job.get("estimate_id")), "") or "").strip()
            if _eq:
                with st.container(border=True):
                    st.markdown('<span class="ips-list-top-anchor"></span>', unsafe_allow_html=True)
                    st.markdown(f"**Linked estimate** · Quote **{_eq}**", unsafe_allow_html=True)

        customer_options = {
            c.get("customer_name", ""): c.get("id")
            for c in customers
            if str(c.get("customer_name", "")).strip()
        }
        estimate_options = {"": None}
        for e in estimates:
            estimate_options[estimate_label_map.get(e.get("id"), "")] = e.get("id")
        estimate_options.pop("", None)
        estimate_options = {"": None, **estimate_options}

        def current_value(field_name, default=""):
            if selected_job:
                value = selected_job.get(field_name, default)
                return "" if value is None else value
            return default

        _ro = not can_edit

        c1, c2 = st.columns(2)
        cust_keys = [""] + sorted(customer_options.keys())
        selected_cust_name = (
            customer_name_by_id.get(selected_job.get("customer_id")) if selected_job else ""
        )
        cust_index = cust_keys.index(selected_cust_name) if selected_cust_name in cust_keys else 0
        customer_name = c1.selectbox("Customer", cust_keys, index=cust_index, disabled=_ro, key="job_form_customer")
        job_name = c2.text_input("Job Name", value=current_value("job_name"), disabled=_ro, key="job_form_job_name")

        selected_contact_id: str | None = None
        cust_uuid = customer_options.get(customer_name) if customer_name else None
        if cust_uuid:
            inject_contact_picker_styles()
            contacts = fetch_contacts_for_customer(str(cust_uuid), include_inactive=False)
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
                ct_idx = min(max(ct_idx, 0), max(len(labels) - 1, 0))
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

        c5, c6 = st.columns(2)
        status_options = JOB_STATUSES
        current_status = current_value("status", "Draft") or "Draft"
        if current_status not in status_options:
            current_status = "Draft"
        status = c5.selectbox(
            "Status",
            status_options,
            index=status_options.index(current_status),
            disabled=_ro,
            key="job_form_status",
        )

        estimate_labels = [""] + [k for k in estimate_options.keys() if k]
        current_estimate_label = ""
        if selected_job and selected_job.get("estimate_id") in estimate_label_map:
            current_estimate_label = estimate_label_map[selected_job.get("estimate_id")]
        linked_estimate = c6.selectbox(
            "Linked Estimate",
            estimate_labels,
            index=estimate_labels.index(current_estimate_label) if current_estimate_label in estimate_labels else 0,
            disabled=_ro,
            key="job_form_linked_estimate",
        )

        c7, c8, c9 = st.columns(3)
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

        c10, c11, c12 = st.columns(3)
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

        notes = st.text_area("Notes", value=current_value("notes"), disabled=_ro, key="job_form_notes")

        if not can_edit:
            st.info("Only admin or estimator users can add or update jobs.")
            return

        b1, b2 = st.columns(2)
        if mode == "add":
            if b1.button("Create Job", type="primary", use_container_width=True, disabled=_ro, key="job_form_create"):
                if not customer_name:
                    st.error("Customer required")
                    st.stop()
                if not job_name.strip():
                    st.error("Job Name required")
                    st.stop()
                payload = {
                    "customer_id": customer_options[customer_name],
                    "customer_contact_id": selected_contact_id,
                    "job_name": job_name.strip(),
                    "location": location.strip(),
                    "status": status,
                    "estimate_id": estimate_options.get(linked_estimate),
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
                insert_row("jobs", payload)
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
                payload = {
                    "customer_id": customer_options[customer_name],
                    "customer_contact_id": selected_contact_id,
                    "job_name": job_name.strip(),
                    "location": location.strip(),
                    "status": status,
                    "estimate_id": estimate_options.get(linked_estimate),
                    "project_manager": project_manager.strip(),
                    "supervisor": supervisor.strip(),
                    "start_date": _safe_date_value(start_date.strip()),
                    "target_completion_date": _safe_date_value(target_completion_date.strip()),
                    "completed_date": _safe_date_value(completed_date.strip()),
                    "awarded_amount": float(awarded_amount or 0),
                    "notes": notes.strip(),
                }
                update_rows("jobs", payload, {"id": selected_job["id"]})
                _clear_job_mode()
                st.success("Job updated.")
                st.rerun()

        if b2.button("Cancel", use_container_width=True, key="job_form_cancel"):
            _clear_job_mode()
            st.rerun()


def render() -> None:
    render_header("Job Database")

    can_edit = current_role() in {"admin", "estimator"}

    customers = fetch_table("customers", limit=5000, order_by="customer_name")
    estimates = fetch_table(
        "estimates",
        columns="id,quote_number,customer_id,proposal_total,status,job_id",
        limit=5000,
        order_by="quote_number",
    )
    # Real columns only (see app/services/job_schema.py); jobs has no ``description`` — use ``notes``.
    jobs, has_job_number_column = fetch_jobs_for_job_database(limit=5000)
    if has_job_number_column:
        jobs = sort_jobs_by_number_then_name(jobs)
    else:
        jobs = sort_jobs_by_name(jobs)

    customer_name_by_id = {c.get("id"): c.get("customer_name", "") for c in customers}
    estimate_label_map = {
        e.get("id"): f"{e.get('quote_number', '')} | {customer_name_by_id.get(e.get('customer_id'), '')} | {e.get('status', '')}"
        for e in estimates
    }
    estimate_quote_by_id = {
        str(e.get("id")): str(e.get("quote_number") or "").strip()
        for e in estimates
        if e.get("id") is not None
    }

    st.subheader("Jobs Overview")

    jobs_df = pd.DataFrame(jobs)

    mode = st.session_state.get("job_mode")
    panel_open = bool(can_edit and mode in ("add", "edit"))
    if panel_open:
        main_col, side_col = st.columns([2.2, 1.1], gap="medium")
    else:
        main_col = st.container()
        side_col = None

    with main_col:
        if jobs_df.empty:
            st.info("No jobs found.")
            if can_edit:
                with st.container(border=True):
                    st.markdown('<span class="ips-list-top-anchor"></span>', unsafe_allow_html=True)
                    if st.button("Create New Job", key="job_add_btn_empty", type="primary", use_container_width=True):
                        st.session_state["job_mode"] = "add"
                        st.session_state.pop("job_edit_id", None)
                        st.rerun()
            return

        inject_table_action_styles()
        if "customer_id" in jobs_df.columns:
            jobs_df["customer_name"] = jobs_df["customer_id"].map(customer_name_by_id)
        else:
            jobs_df["customer_name"] = ""
        if "estimate_id" in jobs_df.columns:
            jobs_df["estimate_label"] = jobs_df["estimate_id"].map(estimate_label_map)

            def _quote_for_estimate_cell(v) -> str:
                if v is None or str(v).strip() == "":
                    return ""
                return estimate_quote_by_id.get(str(v), "")

            jobs_df["Quote (estimate)"] = jobs_df["estimate_id"].map(_quote_for_estimate_cell)
        else:
            jobs_df["estimate_label"] = ""
            jobs_df["Quote (estimate)"] = ""

        sel_ids = get_selected_ids(TABLE_KEY_JOBS)
        n_sel = len(sel_ids)
        one = n_sel == 1
        none = n_sel == 0

        # Top action bar (button-driven workflow)
        with st.container(border=True):
            st.markdown('<span class="ips-list-top-anchor"></span>', unsafe_allow_html=True)
            left, b1, b2, b3 = st.columns([1.25, 1, 1, 1], gap="small")
            with left:
                st.markdown(
                    f'<span class="ips-ta-summary"><span class="ips-ta-num">{n_sel}</span> selected</span>',
                    unsafe_allow_html=True,
                )
            with b1:
                if st.button(
                    "Create New Job",
                    key="job_add_btn",
                    type="primary",
                    use_container_width=True,
                    disabled=not can_edit,
                ):
                    st.session_state["job_mode"] = "add"
                    st.session_state.pop("job_edit_id", None)
                    st.rerun()
            with b2:
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
            with b3:
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
                st.warning(f"Delete **{len(pend_ids)}** job(s)? This cannot be undone.")
                dc1, dc2 = st.columns(2)
                with dc1:
                    if st.button("Confirm delete", type="primary", key="job_db_confirm_delete"):
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
                    if st.button("Cancel", key="job_db_cancel_delete"):
                        pend.pop(TABLE_KEY_JOBS, None)
                        st.rerun()

        f1, f2, f3 = st.columns([1, 1, 2])

        customer_names = sorted(
            [c.get("customer_name", "") for c in customers if str(c.get("customer_name", "")).strip()]
        )
        selected_customer = f1.selectbox(
            "Filter Customer",
            ["All"] + customer_names,
            disabled="customer_id" not in jobs_df.columns,
        )

        selected_status = f2.selectbox(
            "Filter Status",
            ["All"] + JOB_STATUSES,
            disabled="status" not in jobs_df.columns,
        )

        _search_hint = "Search across visible fields"
        if has_job_number_column:
            _search_hint = "job_number, job_name, customer, status, PM, supervisor, location, notes, …"
        else:
            _search_hint = "job_name, customer, status, PM, supervisor, location, notes, …"

        search = f3.text_input(
            "Search Jobs",
            placeholder=_search_hint,
        )

        filtered = jobs_df.copy()

        if selected_customer != "All" and "customer_name" in filtered.columns:
            filtered = filtered[filtered["customer_name"].astype(str) == selected_customer]

        if selected_status != "All" and "status" in filtered.columns:
            filtered = filtered[filtered["status"].astype(str) == selected_status]

        if search.strip():
            s = search.strip().lower()
            mask = filtered.astype(str).apply(lambda col: col.str.lower().str.contains(s, na=False))
            filtered = filtered[mask.any(axis=1)]

        show_cols: list[str] = []
        if has_job_number_column and "job_number" in filtered.columns:
            show_cols.append("job_number")
        show_cols.extend(
            [c for c in JOBS_JOB_DATABASE_OVERVIEW_DISPLAY_ORDER if c in filtered.columns]
        )

        if "id" not in filtered.columns:
            st.dataframe(filtered[show_cols], use_container_width=True, hide_index=True)
        else:
            st.caption("Checkbox column on the **left**. Select rows, then use the **buttons above**.")
            render_selectable_dataframe(
                filtered,
                table_key=TABLE_KEY_JOBS,
                id_column="id",
                columns=show_cols,
                editor_key="job_db_sel_editor",
            )

    if panel_open and side_col is not None:
        with side_col:
            selected_job = None
            if mode == "edit":
                edit_id = st.session_state.get("job_edit_id")
                if edit_id:
                    selected_job = next((j for j in jobs if str(j.get("id")) == str(edit_id)), None)
                if not selected_job:
                    st.error("Selected job could not be loaded. It may have been deleted.")
                    _clear_job_mode()
                    st.rerun()
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
            )