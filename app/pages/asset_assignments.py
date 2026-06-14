from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

try:
    from app.auth import current_profile, current_role
    from app.ui.page_shell import render_page_header
    from app.db import fetch_table, insert_row_admin, update_rows_admin
    from app.services.job_service import job_row_select_label, sort_jobs_by_number_then_name
except ImportError:
    from auth import current_profile, current_role  # type: ignore
    from branding import render_header  # type: ignore
    from db import fetch_table, insert_row_admin, update_rows_admin  # type: ignore
    from services.job_service import job_row_select_label, sort_jobs_by_number_then_name  # type: ignore


def render() -> None:
    render_page_header("Asset Assignments", "Who has which assets assigned.")

    if current_role() not in {"admin", "pm"}:
        st.info("Only admin or pm users can manage assignments.")
        return

    assets = fetch_table("assets", limit=5000, order_by="asset_name")
    jobs = sort_jobs_by_number_then_name(fetch_table("jobs", limit=5000, order_by="job_number"))
    assignments = fetch_table("asset_assignments", limit=5000, order_by="created_at")

    asset_options = {f"{a.get('asset_id')} - {a.get('asset_name')}": a for a in assets}
    job_options: dict[str, str | None] = {"": None}
    for job in jobs:
        label = job_row_select_label(job)
        if label and label != "—":
            job_options[label] = job.get("id")

    st.session_state.setdefault("asset_asg_panel", "Assign Asset")
    st.radio(
        "Assignments view",
        ["Assign Asset", "History"],
        horizontal=True,
        key="asset_asg_panel",
        label_visibility="collapsed",
    )
    _ap = str(st.session_state.get("asset_asg_panel") or "Assign Asset")
    if _ap == "Assign Asset":
        selected_label = st.selectbox("Asset", list(asset_options.keys()))
        selected_asset = asset_options[selected_label]
        employee = st.text_input("Assign To")
        job_name = st.selectbox("Job", list(job_options.keys()))
        location = st.text_input("Assignment Location", value=str(selected_asset.get("location", "")))
        notes = st.text_area("Notes", height=72)

        c1, c2 = st.columns(2, gap="small")
        if c1.button("Check Out", use_container_width=True):
            assignment_row = insert_row_admin(
                "asset_assignments",
                {
                    "asset_id": selected_asset["id"],
                    "assigned_to": employee.strip(),
                    "assigned_job_id": job_options.get(job_name),
                    "assigned_location": location.strip(),
                    "check_out_at": datetime.utcnow().isoformat(),
                    "notes": notes.strip(),
                    "created_by": current_profile().get("id"),
                },
            )
            update_rows_admin(
                "assets",
                {
                    "status": "Assigned",
                    "assigned_employee": employee.strip(),
                    "assigned_job_id": job_options.get(job_name),
                    "location": location.strip(),
                },
                {"id": selected_asset["id"]},
            )
            job_id = job_options.get(job_name)
            if job_id and isinstance(assignment_row, dict):
                try:
                    from app.services.job_cost_transaction_service import (
                        _safe_sync,
                        sync_asset_assignment_to_job,
                    )
                except ImportError:
                    from services.job_cost_transaction_service import (  # type: ignore
                        _safe_sync,
                        sync_asset_assignment_to_job,
                    )
                _safe_sync(
                    sync_asset_assignment_to_job,
                    assignment_id=str(assignment_row.get("id") or ""),
                    asset=selected_asset,
                    job_id=str(job_id),
                    check_out_at=str(assignment_row.get("check_out_at") or ""),
                )
            st.success("Asset checked out.")
            st.rerun()

        if c2.button("Check In", use_container_width=True):
            try:
                from app.services.job_cost_transaction_service import void_asset_assignment_cost
            except ImportError:
                from services.job_cost_transaction_service import void_asset_assignment_cost  # type: ignore
            asset_id = str(selected_asset.get("id") or "")
            for row in sorted(assignments, key=lambda r: str(r.get("check_out_at") or ""), reverse=True):
                if (
                    str(row.get("asset_id") or "") == asset_id
                    and row.get("check_out_at")
                    and not row.get("check_in_at")
                ):
                    void_asset_assignment_cost(str(row.get("id") or ""))
                    break
            insert_row_admin(
                "asset_assignments",
                {
                    "asset_id": selected_asset["id"],
                    "assigned_to": selected_asset.get("assigned_employee", ""),
                    "assigned_job_id": selected_asset.get("assigned_job_id"),
                    "assigned_location": location.strip(),
                    "check_in_at": datetime.utcnow().isoformat(),
                    "notes": notes.strip(),
                    "created_by": current_profile().get("id"),
                },
            )
            update_rows_admin(
                "assets",
                {
                    "status": "Available",
                    "assigned_employee": "",
                    "assigned_job_id": None,
                },
                {"id": selected_asset["id"]},
            )
            st.success("Asset checked in.")
            st.rerun()

    else:
        if assignments:
            st.dataframe(pd.DataFrame(assignments), use_container_width=True, hide_index=True)
        else:
            st.info("No assignment history found.")
