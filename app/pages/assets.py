from __future__ import annotations

import re
import pandas as pd
import streamlit as st

from auth import current_role
from branding import render_header
from db import delete_rows_admin, fetch_one, fetch_table, insert_row_admin, update_rows_admin
from ui import IPS_NAV_PENDING_KEY

try:
    from table_actions import (
        IPS_PENDING_DELETE,
        TABLE_KEY_ASSET_MANAGER,
        clear_selected_ids,
        render_selectable_dataframe,
        render_selection_action_bar,
    )
except ImportError:
    from app.table_actions import (  # type: ignore
        IPS_PENDING_DELETE,
        TABLE_KEY_ASSET_MANAGER,
        clear_selected_ids,
        render_selectable_dataframe,
        render_selection_action_bar,
    )

try:
    from services.asset_constants import ASSET_STATUSES
    from services.asset_service import optional_numeric
    from services.job_service import job_row_select_label, sort_jobs_by_number_then_name
except ImportError:
    from app.services.asset_constants import ASSET_STATUSES  # type: ignore
    from app.services.asset_service import optional_numeric  # type: ignore
    from app.services.job_service import job_row_select_label, sort_jobs_by_number_then_name  # type: ignore

ASSET_TYPES = [
    "Truck",
    "Trailer",
    "Welder",
    "Lift",
    "Forklift",
    "Generator",
    "Compressor",
    "Tool",
    "Machine",
    "Other",
]


def clean_asset_code(text: str) -> str:
    text = str(text).strip().upper()
    text = re.sub(r"[^A-Z0-9]+", "-", text)
    return text.strip("-")


def next_asset_id(rows) -> str:
    nums = []
    for r in rows:
        value = str(r.get("asset_id", "")).strip().upper()
        if value.startswith("AST-"):
            try:
                nums.append(int(value.replace("AST-", "")))
            except Exception:
                pass
    next_num = max(nums) + 1 if nums else 1
    return f"AST-{next_num:03d}"


def make_unique_asset_name(base_value: str, rows) -> str:
    existing = {str(r.get("asset_name", "")).strip().upper() for r in rows}
    if base_value.upper() not in existing:
        return base_value

    i = 2
    while True:
        candidate = f"{base_value}_{i}"
        if candidate.upper() not in existing:
            return candidate
        i += 1


def _safe_date_value(value):
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def render() -> None:
    render_header("Asset Manager")

    can_edit = current_role() in {"admin", "pm"}

    assets = fetch_table("assets", limit=5000, order_by="asset_name")
    jobs = sort_jobs_by_number_then_name(fetch_table("jobs", limit=5000, order_by="job_number"))

    asset_df = pd.DataFrame(assets)
    job_label_by_id = {j.get("id"): job_row_select_label(j) for j in jobs}

    assets_view = st.session_state.get("assets_view")
    asset_edit_id = st.session_state.get("asset_edit_id")
    if assets_view == "edit" and not asset_edit_id:
        st.session_state.pop("assets_view", None)
        assets_view = None
    editing_session = assets_view == "edit" and bool(asset_edit_id)
    asset_for_edit = fetch_one("assets", {"id": asset_edit_id}) if editing_session and asset_edit_id else None
    if editing_session and not asset_for_edit:
        st.warning("Could not load that asset for editing.")
        st.session_state.pop("asset_edit_id", None)
        st.session_state.pop("assets_view", None)
        st.session_state.pop("asset_return_to", None)
        editing_session = False

    return_to_detail = st.session_state.get("asset_return_to") == "asset_detail"

    st.subheader("Asset Overview")

    if editing_session and asset_for_edit and return_to_detail:
        st.caption(
            f"Opened from **Asset Detail** — editing **{asset_for_edit.get('asset_id', '')}** · "
            f"{asset_for_edit.get('asset_name', '')}. Use **Update Asset** below, or choose another page from the sidebar."
        )

    if asset_df.empty and not editing_session:
        st.info("No assets found.")
    elif not asset_df.empty:
        asset_df["assigned_job_name"] = asset_df["assigned_job_id"].map(job_label_by_id)

        f1, f2, f3, f4 = st.columns([1, 1, 1, 2])

        selected_type = f1.selectbox("Filter Type", ["All"] + ASSET_TYPES)

        selected_status = f2.selectbox("Filter Status", ["All"] + ASSET_STATUSES)

        active_options = ["All", "Active Only", "Inactive Only"]
        selected_active = f3.selectbox("Filter Active", active_options)

        search = f4.text_input(
            "Search Assets",
            placeholder="Search asset ID, name, serial, location, employee, job, notes",
        )

        filtered = asset_df.copy()

        if selected_type != "All" and "asset_type" in filtered.columns:
            filtered = filtered[filtered["asset_type"].astype(str) == selected_type]

        if selected_status != "All" and "status" in filtered.columns:
            filtered = filtered[filtered["status"].astype(str) == selected_status]

        if selected_active == "Active Only" and "is_active" in filtered.columns:
            filtered = filtered[filtered["is_active"] == True]
        elif selected_active == "Inactive Only" and "is_active" in filtered.columns:
            filtered = filtered[filtered["is_active"] == False]

        if search.strip():
            s = search.strip().lower()
            mask = filtered.astype(str).apply(lambda col: col.str.lower().str.contains(s, na=False))
            filtered = filtered[mask.any(axis=1)]

        show_cols = [
            c
            for c in [
                "asset_id",
                "asset_name",
                "asset_type",
                "category",
                "status",
                "is_rental",
                "serial_number",
                "manufacturer",
                "model",
                "assigned_employee",
                "assigned_job_name",
                "location",
                "inspection_due_date",
                "maintenance_due_date",
                "is_active",
            ]
            if c in filtered.columns
        ]

        if "id" not in filtered.columns:
            st.dataframe(filtered[show_cols], use_container_width=True, hide_index=True)
        else:
            _, sel = render_selectable_dataframe(
                filtered,
                table_key=TABLE_KEY_ASSET_MANAGER,
                id_column="id",
                columns=show_cols,
                editor_key="asset_mgr_sel_editor",
            )
            actions = render_selection_action_bar(
                TABLE_KEY_ASSET_MANAGER,
                sel,
                can_view=True,
                can_edit=can_edit,
                can_delete=can_edit,
                export_df=filtered,
                id_column="id",
                export_filename="assets_export.csv",
            )
            if actions["view"] and sel:
                st.session_state["asset_detail_id"] = str(sel[0])
                st.session_state[IPS_NAV_PENDING_KEY] = "Asset Detail"
                st.rerun()
            if actions["edit"] and sel:
                st.session_state["assets_view"] = "edit"
                st.session_state["asset_edit_id"] = str(sel[0])
                st.session_state.pop("asset_return_to", None)
                st.rerun()
            pend = st.session_state.get(IPS_PENDING_DELETE) or {}
            if actions.get("confirm_delete") and pend.get(TABLE_KEY_ASSET_MANAGER):
                for aid in pend[TABLE_KEY_ASSET_MANAGER]:
                    try:
                        delete_rows_admin("assets", {"id": aid})
                    except Exception as exc:
                        st.error(f"Could not delete {aid}: {exc}")
                pend.pop(TABLE_KEY_ASSET_MANAGER, None)
                clear_selected_ids(TABLE_KEY_ASSET_MANAGER)
                st.success("Delete completed where permitted.")
                st.rerun()

    st.markdown("---")
    st.subheader("Edit Asset" if (editing_session and asset_for_edit) else "Create / Update Asset")

    existing_asset_labels = [
        f"{a.get('asset_id', '')} | {a.get('asset_name', '')} | {a.get('status', '')}"
        for a in assets
    ]

    selected_mode = "Edit Existing Asset"
    selected_asset = None

    if editing_session and asset_for_edit:
        selected_asset = asset_for_edit
        selected_mode = "Edit Existing Asset"
    else:
        selected_mode = st.radio(
            "Mode",
            ["Add New Asset", "Edit Existing Asset"],
            horizontal=True,
        )

        if selected_mode == "Edit Existing Asset" and assets:
            selected_asset_label = st.selectbox("Select Asset", existing_asset_labels)
            selected_asset = next(
                a for a in assets
                if f"{a.get('asset_id', '')} | {a.get('asset_name', '')} | {a.get('status', '')}" == selected_asset_label
            )

    _sid = str(selected_asset["id"]) if selected_asset and selected_asset.get("id") else "new"

    def _am_key(field: str) -> str:
        return f"am_{_sid}_{field}"

    def current_value(field_name, default=""):
        if selected_asset:
            value = selected_asset.get(field_name, default)
            return "" if value is None else value
        return default

    job_options = {
        job_row_select_label(j): j.get("id")
        for j in jobs
        if job_row_select_label(j) and job_row_select_label(j) != "—"
    }

    selected_job_label_default = ""
    if selected_asset and selected_asset.get("assigned_job_id") in job_label_by_id:
        selected_job_label_default = job_label_by_id[selected_asset.get("assigned_job_id")]

    c1, c2, c3 = st.columns(3)
    asset_id = c1.text_input(
        "Asset ID (blank = auto)",
        value=current_value("asset_id"),
        disabled=not can_edit,
        key=_am_key("asset_id"),
    )
    asset_name = c2.text_input(
        "Asset Name",
        value=current_value("asset_name"),
        disabled=not can_edit,
        key=_am_key("asset_name"),
    )
    asset_type = c3.selectbox(
        "Asset Type",
        ASSET_TYPES,
        index=ASSET_TYPES.index(current_value("asset_type", "Other")) if current_value("asset_type", "Other") in ASSET_TYPES else ASSET_TYPES.index("Other"),
        disabled=not can_edit,
        key=_am_key("asset_type"),
    )

    c4, c5, c6 = st.columns(3)
    serial_number = c4.text_input(
        "Serial Number",
        value=current_value("serial_number"),
        disabled=not can_edit,
        key=_am_key("serial_number"),
    )
    manufacturer = c5.text_input(
        "Manufacturer",
        value=current_value("manufacturer"),
        disabled=not can_edit,
        key=_am_key("manufacturer"),
    )
    model = c6.text_input(
        "Model",
        value=current_value("model"),
        disabled=not can_edit,
        key=_am_key("model"),
    )

    c7, c8, c9 = st.columns(3)
    assigned_employee = c7.text_input(
        "Assigned Employee",
        value=current_value("assigned_employee"),
        disabled=not can_edit,
        key=_am_key("assigned_employee"),
    )
    assigned_job_label = c8.selectbox(
        "Assigned Job",
        [""] + sorted(job_options.keys()),
        index=([""] + sorted(job_options.keys())).index(selected_job_label_default)
        if selected_job_label_default in ([""] + sorted(job_options.keys()))
        else 0,
        disabled=not can_edit,
        key=_am_key("assigned_job"),
    )
    status_default = current_value("status", "Available") or "Available"
    if status_default not in ASSET_STATUSES:
        status_default = "Available"
    status = c9.selectbox(
        "Status",
        ASSET_STATUSES,
        index=ASSET_STATUSES.index(status_default),
        disabled=not can_edit,
        key=_am_key("status"),
    )

    c10, c11, c12 = st.columns(3)
    location = c10.text_input(
        "Location",
        value=current_value("location"),
        disabled=not can_edit,
        key=_am_key("location"),
    )
    purchase_date = c11.text_input(
        "Purchase Date (YYYY-MM-DD)",
        value=str(current_value("purchase_date")),
        disabled=not can_edit,
        key=_am_key("purchase_date"),
    )
    inspection_due_date = c12.text_input(
        "Inspection Due (YYYY-MM-DD)",
        value=str(current_value("inspection_due_date")),
        disabled=not can_edit,
        key=_am_key("inspection_due_date"),
    )

    c13, c14 = st.columns(2)
    maintenance_due_date = c13.text_input(
        "Maintenance Due (YYYY-MM-DD)",
        value=str(current_value("maintenance_due_date")),
        disabled=not can_edit,
        key=_am_key("maintenance_due_date"),
    )
    is_active = c14.checkbox(
        "Active Asset",
        value=bool(current_value("is_active", True)),
        disabled=not can_edit,
        key=_am_key("is_active"),
    )

    cat1, cat2 = st.columns(2)
    category = cat1.text_input(
        "Category",
        value=current_value("category"),
        disabled=not can_edit,
        key=_am_key("category"),
    )
    subcategory = cat2.text_input(
        "Subcategory",
        value=current_value("subcategory"),
        disabled=not can_edit,
        key=_am_key("subcategory"),
    )

    is_rental = st.checkbox(
        "Rent to Customer",
        value=bool(current_value("is_rental", False)),
        disabled=not can_edit,
        key=_am_key("is_rental"),
    )
    rental_daily = rental_weekly = rental_monthly = 0.0
    rental_notes_val = str(current_value("rental_notes", "") or "")
    if is_rental:
        z1, z2, z3 = st.columns(3, gap="small")
        rental_daily = z1.number_input(
            "Daily rate",
            min_value=0.0,
            value=float(current_value("rental_daily_rate") or 0),
            step=1.0,
            format="%.2f",
            disabled=not can_edit,
            key=_am_key("rental_daily"),
        )
        rental_weekly = z2.number_input(
            "Weekly rate",
            min_value=0.0,
            value=float(current_value("rental_weekly_rate") or 0),
            step=1.0,
            format="%.2f",
            disabled=not can_edit,
            key=_am_key("rental_weekly"),
        )
        rental_monthly = z3.number_input(
            "Monthly rate",
            min_value=0.0,
            value=float(current_value("rental_monthly_rate") or 0),
            step=1.0,
            format="%.2f",
            disabled=not can_edit,
            key=_am_key("rental_monthly"),
        )
        rental_notes_val = st.text_area(
            "Rental notes",
            value=rental_notes_val,
            height=80,
            disabled=not can_edit,
            key=_am_key("rental_notes"),
        )

    notes = st.text_area(
        "Notes",
        value=current_value("notes"),
        disabled=not can_edit,
        height=88,
        key=_am_key("notes"),
    )

    if not can_edit:
        st.info("Only admin or pm users can add or update assets.")
        return

    if selected_mode == "Add New Asset" and not editing_session:
        if st.button("Add Asset", use_container_width=True):
            if not asset_name.strip():
                st.error("Asset Name required")
                st.stop()

            final_asset_id = asset_id.strip() or next_asset_id(assets)
            final_asset_name = make_unique_asset_name(asset_name.strip(), assets)

            payload = {
                "asset_id": final_asset_id,
                "asset_name": final_asset_name,
                "asset_type": asset_type,
                "category": category.strip(),
                "subcategory": subcategory.strip(),
                "serial_number": serial_number.strip(),
                "manufacturer": manufacturer.strip(),
                "model": model.strip(),
                "assigned_employee": assigned_employee.strip(),
                "assigned_job_id": job_options.get(assigned_job_label),
                "location": location.strip(),
                "status": status,
                "purchase_date": _safe_date_value(purchase_date.strip()),
                "inspection_due_date": _safe_date_value(inspection_due_date.strip()),
                "maintenance_due_date": _safe_date_value(maintenance_due_date.strip()),
                "notes": notes.strip(),
                "is_active": bool(is_active),
                "is_rental": bool(is_rental),
                "rental_notes": rental_notes_val.strip(),
            }
            if is_rental:
                payload["rental_daily_rate"] = optional_numeric(rental_daily)
                payload["rental_weekly_rate"] = optional_numeric(rental_weekly)
                payload["rental_monthly_rate"] = optional_numeric(rental_monthly)

            insert_row_admin("assets", payload)
            st.success(f"Asset added: {final_asset_id}")
            st.rerun()

    elif selected_mode == "Edit Existing Asset":
        if st.button("Update Asset", use_container_width=True):
            if not selected_asset:
                st.error("Select an asset first.")
                st.stop()

            if not asset_name.strip():
                st.error("Asset Name required")
                st.stop()

            payload = {
                "asset_id": asset_id.strip() or selected_asset.get("asset_id"),
                "asset_name": asset_name.strip(),
                "asset_type": asset_type,
                "category": category.strip(),
                "subcategory": subcategory.strip(),
                "serial_number": serial_number.strip(),
                "manufacturer": manufacturer.strip(),
                "model": model.strip(),
                "assigned_employee": assigned_employee.strip(),
                "assigned_job_id": job_options.get(assigned_job_label),
                "location": location.strip(),
                "status": status,
                "purchase_date": _safe_date_value(purchase_date.strip()),
                "inspection_due_date": _safe_date_value(inspection_due_date.strip()),
                "maintenance_due_date": _safe_date_value(maintenance_due_date.strip()),
                "notes": notes.strip(),
                "is_active": bool(is_active),
                "is_rental": bool(is_rental),
                "rental_notes": rental_notes_val.strip(),
            }
            if is_rental:
                payload["rental_daily_rate"] = optional_numeric(rental_daily)
                payload["rental_weekly_rate"] = optional_numeric(rental_weekly)
                payload["rental_monthly_rate"] = optional_numeric(rental_monthly)

            update_rows_admin("assets", payload, {"id": selected_asset["id"]})

            st.session_state.pop("asset_edit_id", None)
            st.session_state.pop("assets_view", None)
            ret = st.session_state.pop("asset_return_to", None)
            if ret == "asset_detail":
                st.session_state["asset_detail_id"] = str(selected_asset["id"])
                st.session_state[IPS_NAV_PENDING_KEY] = "Asset Detail"
                st.session_state["asset_detail_flash"] = "Asset updated."
            else:
                st.success("Asset updated.")
            st.rerun()