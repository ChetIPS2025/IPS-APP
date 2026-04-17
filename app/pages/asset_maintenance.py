from __future__ import annotations

import pandas as pd
import streamlit as st

try:
    from app.auth import current_profile, current_role
    from app.branding import render_header
    from app.db import fetch_table
    from app.services.asset_service import save_maintenance_record
    from app.services.asset_maintenance_service import maintenance_due_status
except ImportError:
    from auth import current_profile, current_role  # type: ignore
    from branding import render_header  # type: ignore
    from db import fetch_table  # type: ignore
    from services.asset_service import save_maintenance_record  # type: ignore
    from services.asset_maintenance_service import maintenance_due_status  # type: ignore


def render() -> None:
    render_header("Asset Maintenance")

    assets = fetch_table("assets", limit=5000, order_by="asset_name")
    maintenance = fetch_table("asset_maintenance", limit=5000, order_by="service_date")

    latest_maintenance_by_asset = {}
    for record in maintenance:
        if record.get("asset_id") not in latest_maintenance_by_asset:
            latest_maintenance_by_asset[record.get("asset_id")] = record

    tab1, tab2 = st.tabs(["Due Status", "Log Service"])

    with tab1:
        rows = []
        for asset in assets:
            last_pm = latest_maintenance_by_asset.get(asset.get("id"))
            rows.append(
                {
                    "Asset ID": asset.get("asset_id"),
                    "Asset Name": asset.get("asset_name"),
                    "Type": asset.get("asset_type"),
                    "Hour Meter": asset.get("hour_meter"),
                    "Mileage": asset.get("mileage"),
                    "Due Status": maintenance_due_status(asset, last_pm),
                    "Next Service Date": (last_pm or {}).get("next_service_date"),
                    "Next Service Hours": (last_pm or {}).get("next_service_hours"),
                    "Next Service Mileage": (last_pm or {}).get("next_service_mileage"),
                }
            )
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("No assets found.")

    with tab2:
        if current_role() not in {"admin", "estimator"}:
            st.info("Only admin or estimator users can log maintenance.")
            return

        asset_options = {f"{a.get('asset_id')} - {a.get('asset_name')}": a for a in assets}
        selected_label = st.selectbox("Asset", list(asset_options.keys()))
        selected_asset = asset_options[selected_label]

        c1, c2, c3 = st.columns(3, gap="small")
        service_type = c1.text_input("Service Type", value="PM Service")
        service_date = c2.date_input("Service Date")
        vendor = c3.text_input("Vendor")

        c4, c5, c6 = st.columns(3, gap="small")
        hour_meter = c4.number_input("Hour Meter", min_value=0.0, value=float(selected_asset.get("hour_meter") or 0), step=1.0)
        mileage = c5.number_input("Mileage", min_value=0.0, value=float(selected_asset.get("mileage") or 0), step=1.0)
        cost = c6.number_input("Cost", min_value=0.0, value=0.0, step=10.0)

        c7, c8 = st.columns(2, gap="small")
        po_number = c7.text_input("PO Number")
        performed_by = c8.text_input("Performed By")

        notes = st.text_area("Notes", height=72)

        if st.button("Save Maintenance Record", use_container_width=True):
            record = save_maintenance_record(
                {
                    "asset_id": selected_asset["id"],
                    "service_type": service_type.strip(),
                    "service_date": service_date.isoformat(),
                    "hour_meter": hour_meter,
                    "mileage": mileage,
                    "vendor": vendor.strip(),
                    "cost": cost,
                    "po_number": po_number.strip(),
                    "performed_by": performed_by.strip(),
                    "notes": notes.strip(),
                },
                created_by=current_profile().get("id"),
            )
            st.success(f"Maintenance saved: {record.get('service_type')}")
