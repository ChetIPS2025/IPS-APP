"""UI for serialized Milwaukee tools — add, import, tracking panel."""

from __future__ import annotations

from typing import Any

import streamlit as st

from app.pages._core._data import load_assets, load_employees, load_jobs
from app.services.asset_kits_service import asset_is_kit, get_tool_trailers
from app.services.quick_add_tool_service import bulk_import_tools, parse_bulk_import_file
from app.services.serialized_tool_service import (
    MILWAUKEE_TOOL_TYPES,
    SERIALIZED_TOOL_STATUSES,
    assign_tool_to_trailer,
    checkin_serialized_tool,
    checkout_serialized_tool,
    create_serialized_tool,
    is_serialized_tool_asset,
    mark_serialized_tool_status,
    serialized_tool_view,
)
from app.utils.formatting import fmt_date
def _trailer_options() -> tuple[list[str], dict[str, str]]:
    trailers = get_tool_trailers()
    labels = ["— None —"]
    label_to_id: dict[str, str] = {}
    for trailer in trailers:
        number = str(trailer.get("asset_number") or "").strip()
        name = str(trailer.get("asset_name") or trailer.get("name") or "Trailer").strip()
        label = f"{number} · {name}" if number else name
        labels.append(label)
        label_to_id[label] = str(trailer.get("id") or "")
    return labels, label_to_id


def _employee_options() -> tuple[list[str], dict[str, str]]:
    employees = load_employees()
    labels: list[str] = []
    label_to_id: dict[str, str] = {}
    for emp in employees:
        eid = str(emp.get("id") or "").strip()
        if not eid:
            continue
        name = str(emp.get("name") or emp.get("full_name") or "Employee").strip()
        label = name
        labels.append(label)
        label_to_id[label] = eid
    return labels, label_to_id


def _job_options() -> tuple[list[str], dict[str, str]]:
    jobs = load_jobs()
    labels = ["— None —"]
    label_to_id: dict[str, str] = {}
    for job in jobs:
        jid = str(job.get("id") or "").strip()
        if not jid:
            continue
        number = str(job.get("job_number") or "").strip()
        name = str(job.get("job_name") or job.get("name") or "").strip()
        label = f"{number} · {name}" if number and name else (number or name or jid[:8])
        labels.append(label)
        label_to_id[label] = jid
    return labels, label_to_id


def render_serialized_tools_toolbar() -> None:
    """Add/import Milwaukee serialized tools from the Serialized Tools tab."""
    with st.expander("Add Milwaukee Tool", expanded=False):
        trailer_labels, trailer_map = _trailer_options()
        c1, c2 = st.columns(2)
        with c1:
            st.text_input("Tool name", key="st_new_name", placeholder="M18 FUEL Hammer Drill")
            st.text_input("Serial number", key="st_new_serial", placeholder="Required")
            st.text_input("Asset #", key="st_new_asset_number", placeholder="Optional tag")
            st.selectbox("Tool type", MILWAUKEE_TOOL_TYPES, key="st_new_type")
        with c2:
            st.text_input("Manufacturer", value="Milwaukee", key="st_new_mfr")
            st.text_input("Model #", key="st_new_model_number", placeholder="2804-20")
            st.selectbox("Tool Trailer", trailer_labels, key="st_new_trailer")
            st.selectbox("Status", SERIALIZED_TOOL_STATUSES[:4], key="st_new_status")
        st.text_area("Notes", key="st_new_notes", height=60)
        if st.button("Save Serialized Tool", type="primary", key="st_save_new"):
            trailer_pick = str(st.session_state.get("st_new_trailer") or "")
            trailer_id = trailer_map.get(trailer_pick) if trailer_pick != "— None —" else ""
            result = create_serialized_tool(
                {
                    "asset_name": st.session_state.get("st_new_name"),
                    "serial_number": st.session_state.get("st_new_serial"),
                    "asset_number": st.session_state.get("st_new_asset_number"),
                    "asset_type": st.session_state.get("st_new_type"),
                    "category": "Tool",
                    "manufacturer": st.session_state.get("st_new_mfr"),
                    "model_number": st.session_state.get("st_new_model_number"),
                    "status": st.session_state.get("st_new_status"),
                    "notes": st.session_state.get("st_new_notes"),
                    "current_container_asset_id": trailer_id,
                }
            )
            if result.ok:
                warning = str((result.data or {}).get("warning") or "")
                if warning:
                    st.warning(warning)
                st.success("Serialized tool saved.")
                st.rerun()
            st.error(result.error or "Could not save tool.")

    with st.expander("Import tools (CSV)", expanded=False):
        st.caption(
            "Columns: tool_name (or asset_name), model_number, serial_number, asset_type, asset_number, "
            "notes, trailer (or trailer_asset_number). Header spacing/case is normalized automatically."
        )
        uploaded = st.file_uploader("CSV file", type=["csv", "xlsx", "xls"], key="st_import_csv")
        trailer_labels, trailer_map = _trailer_options()
        trailer_pick = st.selectbox(
            "Default Tool Trailer",
            trailer_labels,
            key="st_import_trailer",
        )
        parsed_rows: list[dict[str, Any]] = []
        if uploaded:
            try:
                parsed_rows = parse_bulk_import_file(uploaded.getvalue(), uploaded.name)
            except Exception as exc:
                st.error(f"Could not read file: {exc}")
            if parsed_rows:
                preview = []
                for row in parsed_rows[:25]:
                    preview.append(
                        {
                            "Tool": str(row.get("tool_name") or "").strip() or "—",
                            "Model #": str(row.get("model_number") or "").strip() or "—",
                            "Serial": str(row.get("serial_number") or "").strip() or "—",
                            "Trailer #": str(row.get("trailer_asset_number") or "").strip() or "—",
                        }
                    )
                st.caption(f"{len(parsed_rows)} row(s) parsed — preview below.")
                st.dataframe(preview, use_container_width=True, hide_index=True)
            elif uploaded:
                st.warning("No rows found in file.")
        if uploaded and parsed_rows and st.button("Import CSV", key="st_import_go"):
            trailer_id = trailer_map.get(trailer_pick) if trailer_pick != "— None —" else ""
            result = bulk_import_tools(
                parsed_rows,
                default_kind="serialized",
                default_trailer_id=trailer_id,
            )
            if result.ok:
                data = result.data or {}
                st.success(str(data.get("message") or f"Imported {data.get('created', 0)} tool(s)."))
                errors = data.get("errors") or []
                for err in errors[:5]:
                    st.warning(str(err))
                st.rerun()
            st.error(result.error or "Import failed.")


def render_serialized_tool_tracking_panel(asset: dict[str, Any]) -> None:
    """Tracking actions for a standalone serialized tool asset."""
    if not is_serialized_tool_asset(asset):
        return
    if asset_is_kit(asset):
        return

    assets = load_assets()
    assets_by_id = {str(a.get("id") or ""): a for a in assets if str(a.get("id") or "")}
    employees = load_employees()
    employees_by_id = {str(e.get("id") or ""): e for e in employees if str(e.get("id") or "")}
    jobs = load_jobs()
    jobs_by_id = {str(j.get("id") or ""): j for j in jobs if str(j.get("id") or "")}
    view = serialized_tool_view(
        asset,
        assets_by_id=assets_by_id,
        employees_by_id=employees_by_id,
        jobs_by_id=jobs_by_id,
    )

    st.markdown("**Serialized tool tracking**")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.caption("Tool Trailer")
        st.write(view.get("current_container_label") or "—")
    with c2:
        st.caption("Current job")
        st.write(view.get("current_job_label") or "—")
    with c3:
        st.caption("Checked out to")
        st.write(view.get("current_operator") or "—")

    c4, c5, c6 = st.columns(3)
    with c4:
        st.caption("Status / condition")
        st.write(f"{view.get('status') or '—'} · {view.get('condition') or '—'}")
    with c5:
        st.caption("Last seen")
        st.write(fmt_date(view.get("last_seen_at")) if view.get("last_seen_at") else "—")
    with c6:
        st.caption("Last audited")
        st.write(fmt_date(view.get("last_audited_at")) if view.get("last_audited_at") else "—")

    aid = str(asset.get("id") or "")
    trailer_labels, trailer_map = _trailer_options()
    emp_labels, emp_map = _employee_options()
    job_labels, job_map = _job_options()

    with st.expander("Assign to Tool Trailer", expanded=False):
        pick = st.selectbox("Tool Trailer", trailer_labels, key=f"st_trailer_pick_{aid}")
        if st.button("Assign trailer", key=f"st_assign_trailer_{aid}"):
            trailer_id = trailer_map.get(pick) if pick != "— None —" else ""
            if not trailer_id:
                st.error("Select a Tool Trailer.")
            else:
                result = assign_tool_to_trailer(aid, trailer_id)
                if result.ok:
                    st.success("Tool assigned to trailer.")
                    st.rerun()
                st.error(result.error or "Assignment failed.")

    status = str(view.get("status") or "")
    if status == "Available" and emp_labels:
        with st.expander("Check out tool (assign to employee)", expanded=False):
            emp = st.selectbox("Employee", emp_labels, key=f"st_checkout_emp_{aid}")
            job = st.selectbox("Job (optional)", job_labels, key=f"st_checkout_job_{aid}")
            notes = st.text_input("Notes", key=f"st_checkout_notes_{aid}")
            if st.button("Check out", key=f"st_checkout_go_{aid}"):
                result = checkout_serialized_tool(
                    aid,
                    employee_id=emp_map.get(emp, ""),
                    employee_name=emp,
                    job_id=job_map.get(job) if job != "— None —" else None,
                    notes=notes,
                )
                if result.ok:
                    st.success("Tool checked out.")
                    st.rerun()
                st.error(result.error or "Checkout failed.")
    elif status == "Checked Out":
        if st.button("Check in tool", key=f"st_checkin_{aid}"):
            result = checkin_serialized_tool(aid)
            if result.ok:
                st.success("Tool checked in.")
                st.rerun()
            st.error(result.error or "Check-in failed.")

    with st.expander("Mark missing / damaged / out of service", expanded=False):
        new_status = st.selectbox(
            "Status",
            ["Missing", "Damaged", "Out of Service", "In Repair", "Available", "Retired"],
            key=f"st_mark_status_{aid}",
        )
        new_condition = st.selectbox(
            "Condition",
            ["Good", "Fair", "Damaged", "Needs Repair", "Missing", "Retired"],
            key=f"st_mark_condition_{aid}",
        )
        mark_notes = st.text_input("Notes", key=f"st_mark_notes_{aid}")
        if st.button("Update status", key=f"st_mark_go_{aid}"):
            result = mark_serialized_tool_status(
                aid,
                status=new_status,
                condition=new_condition,
                notes=mark_notes,
            )
            if result.ok:
                st.success("Tool status updated.")
                st.rerun()
            st.error(result.error or "Update failed.")
