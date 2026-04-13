from __future__ import annotations

import pandas as pd
import streamlit as st

try:
    from app.branding import render_header
    from app.db import fetch_table
    from app.services.asset_maintenance_service import maintenance_due_status
except ImportError:
    from branding import render_header  # type: ignore
    from db import fetch_table  # type: ignore
    from services.asset_maintenance_service import maintenance_due_status  # type: ignore


def render() -> None:
    render_header("Asset Dashboard")

    assets = fetch_table("assets", limit=5000, order_by="asset_name")
    maintenance = fetch_table("asset_maintenance", limit=5000, order_by="service_date")

    latest_maintenance_by_asset = {}
    for record in maintenance:
        asset_id = record.get("asset_id")
        if asset_id not in latest_maintenance_by_asset:
            latest_maintenance_by_asset[asset_id] = record

    overdue = 0
    due_soon = 0
    assigned = 0
    in_shop = 0
    available = 0

    rows = []
    for asset in assets:
        status = str(asset.get("status", ""))
        if status == "Assigned":
            assigned += 1
        elif status == "In Shop":
            in_shop += 1
        elif status == "Available":
            available += 1

        due_status = maintenance_due_status(asset, latest_maintenance_by_asset.get(asset.get("id")))
        if due_status == "Overdue":
            overdue += 1
        elif due_status == "Due Soon":
            due_soon += 1

        rows.append(
            {
                "Asset ID": asset.get("asset_id"),
                "Asset Name": asset.get("asset_name"),
                "Type": asset.get("asset_type"),
                "Status": status,
                "Location": asset.get("location"),
                "Assigned Employee": asset.get("assigned_employee"),
                "Maintenance": due_status,
            }
        )

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Assets", len(assets))
    c2.metric("Available", available)
    c3.metric("Assigned", assigned)
    c4.metric("In Shop", in_shop)
    c5.metric("Overdue PM", overdue)

    st.caption(f"Due Soon: {due_soon}")

    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No asset records found.")
