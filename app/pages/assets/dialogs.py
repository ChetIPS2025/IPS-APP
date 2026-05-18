"""Dialog workflows for the Assets module.

Each public function is decorated with @st.dialog and encapsulates a single
workflow (create, edit, or view) without exposing the table underneath.

Calling pattern (from page.py):
    if st.session_state.get("assets_show_create_dialog"):
        show_create_asset_dialog(assets=assets, jobs=jobs, ...)

    if st.session_state.get("assets_edit_mode") and st.session_state.get("selected_asset_id"):
        asset_row = get_asset_by_id(st.session_state["selected_asset_id"])
        if asset_row:
            show_edit_asset_dialog(asset_row, jobs=jobs, ...)
"""
from __future__ import annotations

import streamlit as st

try:
    from app.ui import IPS_NAV_PENDING_KEY
except ImportError:
    from ui import IPS_NAV_PENDING_KEY  # type: ignore

try:
    from app.pages.assets.utils import (
        ASSET_STATUSES,
        ASSET_TYPES,
        safe_date_value,
    )
    from app.pages.assets.services import create_asset, update_asset
    from app.pages.assets.queries import get_assets, build_job_options
    from app.pages.assets.components import render_asset_detail_panel
except ImportError:
    from pages.assets.utils import ASSET_STATUSES, ASSET_TYPES, safe_date_value  # type: ignore
    from pages.assets.services import create_asset, update_asset  # type: ignore
    from pages.assets.queries import get_assets, build_job_options  # type: ignore
    from pages.assets.components import render_asset_detail_panel  # type: ignore

try:
    from app.services.asset_service import optional_numeric
except ImportError:
    from services.asset_service import optional_numeric  # type: ignore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clear_edit_state() -> None:
    st.session_state["assets_edit_mode"] = False
    st.session_state["selected_asset_id"] = None
    st.session_state.pop("asset_form_data", None)
    st.session_state.pop("asset_return_to", None)


def _cv(asset: dict | None, field: str, default: str = "") -> str:
    """Safe current-value helper: returns '' for None / missing."""
    if asset is None:
        return default
    v = asset.get(field, default)
    return "" if v is None else str(v)


def _asset_form_fields(
    *,
    asset: dict | None,
    jobs: list[dict],
    key_prefix: str,
    can_edit: bool,
) -> dict:
    """Render the shared create / edit form fields and return collected values.

    Returns a flat dict ready to pass to create_asset() / update_asset().
    """
    from app.pages.assets.queries import build_job_options, build_job_label_by_id  # lazy import
    job_options = build_job_options(jobs)
    job_label_by_id = build_job_label_by_id(jobs)

    def pk(s: str) -> str:
        rid = str(asset.get("id") or "new") if asset else "new"
        return f"{key_prefix}_{rid}_{s}"

    selected_job_label_default = ""
    if asset:
        jid = str(asset.get("assigned_job_id") or "").strip()
        if jid and jid in job_label_by_id:
            selected_job_label_default = job_label_by_id[jid]

    c1, c2, c3 = st.columns(3)
    asset_id_val = c1.text_input("Asset ID (blank = auto)", value=_cv(asset, "asset_id"),
                                  disabled=not can_edit, key=pk("asset_id"))
    asset_name = c2.text_input("Asset Name", value=_cv(asset, "asset_name"),
                                disabled=not can_edit, key=pk("asset_name"))
    type_default = _cv(asset, "asset_type", "Other")
    asset_type = c3.selectbox(
        "Asset Type", ASSET_TYPES,
        index=ASSET_TYPES.index(type_default) if type_default in ASSET_TYPES else ASSET_TYPES.index("Other"),
        disabled=not can_edit, key=pk("asset_type"),
    )

    c4, c5, c6 = st.columns(3)
    serial_number = c4.text_input("Serial Number", value=_cv(asset, "serial_number"),
                                   disabled=not can_edit, key=pk("serial_number"))
    manufacturer = c5.text_input("Manufacturer", value=_cv(asset, "manufacturer"),
                                  disabled=not can_edit, key=pk("manufacturer"))
    model = c6.text_input("Model", value=_cv(asset, "model"),
                           disabled=not can_edit, key=pk("model"))

    c7, c8, c9 = st.columns(3)
    assigned_employee = c7.text_input("Assigned Employee", value=_cv(asset, "assigned_employee"),
                                       disabled=not can_edit, key=pk("assigned_employee"))
    job_keys = [""] + sorted(job_options.keys())
    assigned_job_label = c8.selectbox(
        "Assigned Job", job_keys,
        index=job_keys.index(selected_job_label_default) if selected_job_label_default in job_keys else 0,
        disabled=not can_edit, key=pk("assigned_job"),
    )
    status_default = _cv(asset, "status", "Available") or "Available"
    if status_default not in ASSET_STATUSES:
        status_default = "Available"
    status = c9.selectbox("Status", ASSET_STATUSES,
                           index=ASSET_STATUSES.index(status_default),
                           disabled=not can_edit, key=pk("status"))

    c10, c11, c12 = st.columns(3)
    location = c10.text_input("Location", value=_cv(asset, "location"),
                               disabled=not can_edit, key=pk("location"))
    purchase_date = c11.text_input("Purchase Date (YYYY-MM-DD)", value=_cv(asset, "purchase_date"),
                                    disabled=not can_edit, key=pk("purchase_date"))
    inspection_due = c12.text_input("Inspection Due (YYYY-MM-DD)",
                                     value=_cv(asset, "inspection_due_date"),
                                     disabled=not can_edit, key=pk("inspection_due_date"))

    c13, c14 = st.columns(2)
    maintenance_due = c13.text_input("Maintenance Due (YYYY-MM-DD)",
                                      value=_cv(asset, "maintenance_due_date"),
                                      disabled=not can_edit, key=pk("maintenance_due_date"))
    is_active = c14.checkbox("Active Asset", value=bool(asset.get("is_active", True) if asset else True),
                              disabled=not can_edit, key=pk("is_active"))

    cat1, cat2 = st.columns(2)
    category = cat1.text_input("Category", value=_cv(asset, "category"),
                                disabled=not can_edit, key=pk("category"))
    subcategory = cat2.text_input("Subcategory", value=_cv(asset, "subcategory"),
                                   disabled=not can_edit, key=pk("subcategory"))

    is_rental = st.checkbox(
        "Rent to Customer",
        value=bool(asset.get("is_rental", False) if asset else False),
        disabled=not can_edit, key=pk("is_rental"),
    )
    rental_daily = rental_weekly = rental_monthly = 0.0
    rental_notes_val = _cv(asset, "rental_notes")
    if is_rental:
        z1, z2, z3 = st.columns(3, gap="small")
        rental_daily = z1.number_input("Daily rate", min_value=0.0,
                                        value=float(asset.get("rental_daily_rate") or 0 if asset else 0),
                                        step=1.0, format="%.2f", disabled=not can_edit, key=pk("rental_daily"))
        rental_weekly = z2.number_input("Weekly rate", min_value=0.0,
                                         value=float(asset.get("rental_weekly_rate") or 0 if asset else 0),
                                         step=1.0, format="%.2f", disabled=not can_edit, key=pk("rental_weekly"))
        rental_monthly = z3.number_input("Monthly rate", min_value=0.0,
                                          value=float(asset.get("rental_monthly_rate") or 0 if asset else 0),
                                          step=1.0, format="%.2f", disabled=not can_edit, key=pk("rental_monthly"))
        rental_notes_val = st.text_area("Rental notes", value=rental_notes_val,
                                         height=72, disabled=not can_edit, key=pk("rental_notes"))

    notes = st.text_area("Notes", value=_cv(asset, "notes"), height=88,
                          disabled=not can_edit, key=pk("notes"))

    return {
        "asset_id": asset_id_val.strip(),
        "asset_name": asset_name.strip(),
        "asset_type": asset_type,
        "serial_number": serial_number.strip(),
        "manufacturer": manufacturer.strip(),
        "model": model.strip(),
        "assigned_employee": assigned_employee.strip(),
        "assigned_job_id": job_options.get(assigned_job_label),
        "status": status,
        "location": location.strip(),
        "purchase_date": safe_date_value(purchase_date.strip()),
        "inspection_due_date": safe_date_value(inspection_due.strip()),
        "maintenance_due_date": safe_date_value(maintenance_due.strip()),
        "is_active": bool(is_active),
        "category": category.strip(),
        "subcategory": subcategory.strip(),
        "is_rental": bool(is_rental),
        "rental_daily_rate": optional_numeric(rental_daily) if is_rental else None,
        "rental_weekly_rate": optional_numeric(rental_weekly) if is_rental else None,
        "rental_monthly_rate": optional_numeric(rental_monthly) if is_rental else None,
        "rental_notes": rental_notes_val.strip() if is_rental else "",
        "notes": notes.strip(),
    }


# ---------------------------------------------------------------------------
# Create dialog
# ---------------------------------------------------------------------------

@st.dialog("New Asset", width="large")
def show_create_asset_dialog(*, jobs: list[dict], can_edit: bool = True) -> None:
    """Full-page dialog for adding a new asset."""
    if not can_edit:
        st.warning("Only admin or manager users can add assets.")
        if st.button("Close", use_container_width=True):
            st.session_state.pop("assets_show_create_dialog", None)
            st.rerun()
        return

    st.caption("Fill in the details below. Asset ID is auto-generated if left blank.")

    form_data = _asset_form_fields(
        asset=None,
        jobs=jobs,
        key_prefix="create",
        can_edit=True,
    )

    col1, col2 = st.columns(2, gap="small")
    with col1:
        if st.button("Add Asset", type="primary", use_container_width=True, key="create_submit"):
            if not form_data["asset_name"]:
                st.error("Asset Name is required.")
                st.stop()
            assets = get_assets()
            new_id = create_asset(form_data, assets)
            st.session_state.pop("assets_show_create_dialog", None)
            st.toast(f"Asset {new_id} added.", icon="✅")
            st.rerun()
    with col2:
        if st.button("Cancel", type="secondary", use_container_width=True, key="create_cancel"):
            st.session_state.pop("assets_show_create_dialog", None)
            st.rerun()


# ---------------------------------------------------------------------------
# Edit dialog
# ---------------------------------------------------------------------------

@st.dialog("Edit Asset", width="large")
def show_edit_asset_dialog(
    asset_row: dict,
    *,
    jobs: list[dict],
    can_edit: bool = True,
) -> None:
    """Edit-only dialog.  Shows only the form — not the asset list behind it."""
    st.caption(
        f"Editing **{asset_row.get('asset_id', '')}** · "
        f"{asset_row.get('asset_name', '')}. "
        "Save to persist changes or Cancel to discard."
    )

    if not can_edit:
        st.warning("You do not have permission to edit assets.")
        if st.button("Close", use_container_width=True):
            _clear_edit_state()
            st.rerun()
        return

    form_data = _asset_form_fields(
        asset=asset_row,
        jobs=jobs,
        key_prefix="edit",
        can_edit=True,
    )

    col1, col2 = st.columns(2, gap="small")
    with col1:
        if st.button("Save Changes", type="primary", use_container_width=True, key="edit_save"):
            if not form_data["asset_name"]:
                st.error("Asset Name is required.")
                st.stop()
            update_asset(str(asset_row["id"]), form_data)

            ret = st.session_state.pop("asset_return_to", None)
            _clear_edit_state()

            if ret == "asset_detail":
                st.session_state["asset_detail_id"] = str(asset_row["id"])
                st.session_state[IPS_NAV_PENDING_KEY] = "Asset Detail"
                st.session_state["asset_detail_flash"] = "Asset updated."
            else:
                st.toast("Asset updated.", icon="✅")
            st.rerun()
    with col2:
        if st.button("Cancel", type="secondary", use_container_width=True, key="edit_cancel"):
            _clear_edit_state()
            st.rerun()


# ---------------------------------------------------------------------------
# View dialog
# ---------------------------------------------------------------------------

@st.dialog("Asset Details", width="large")
def show_view_asset_dialog(
    asset_row: dict,
    *,
    job_label_by_id: dict | None = None,
    emp_by_id: dict | None = None,
    can_edit: bool = False,
) -> None:
    """Read-only asset summary dialog with navigation to full profile."""
    render_asset_detail_panel(
        asset_row,
        job_label_by_id=job_label_by_id,
        emp_by_id=emp_by_id,
    )

    st.divider()
    b1, b2, b3 = st.columns([2, 2, 1], gap="small")
    with b1:
        if st.button("Open Full Profile", type="primary", use_container_width=True,
                     key="view_dlg_open_detail"):
            st.session_state["asset_detail_id"] = str(asset_row["id"])
            st.session_state[IPS_NAV_PENDING_KEY] = "Asset Detail"
            st.session_state.pop("assets_view_asset_id", None)
            st.rerun()
    with b2:
        if can_edit:
            if st.button("Edit Asset", type="secondary", use_container_width=True,
                         key="view_dlg_edit"):
                st.session_state.pop("assets_view_asset_id", None)
                st.session_state["assets_edit_mode"] = True
                st.session_state["selected_asset_id"] = str(asset_row["id"])
                st.rerun()
    with b3:
        if st.button("Close", type="secondary", use_container_width=True, key="view_dlg_close"):
            st.session_state.pop("assets_view_asset_id", None)
            st.rerun()
