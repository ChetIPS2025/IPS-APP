from __future__ import annotations

import pandas as pd
import streamlit as st

try:
    from app.auth import current_profile, current_role
    from app.ui.page_shell import render_page_header
    from app.db import fetch_table, insert_row_admin
except ImportError:
    from auth import current_profile, current_role  # type: ignore
    from branding import render_header  # type: ignore
    from db import fetch_table, insert_row_admin  # type: ignore


def render() -> None:
    render_page_header("Asset Inspections", "Inspection history and checklists.")

    assets = fetch_table("assets", limit=5000, order_by="asset_name")
    inspections = fetch_table("asset_inspections", limit=5000, order_by="inspection_date")

    st.session_state.setdefault("asset_insp_panel", "Inspection Log")
    st.radio(
        "Inspections view",
        ["Inspection Log", "New Inspection"],
        horizontal=True,
        key="asset_insp_panel",
        label_visibility="collapsed",
    )
    _ip = str(st.session_state.get("asset_insp_panel") or "Inspection Log")
    if _ip == "Inspection Log":
        if inspections:
            st.dataframe(pd.DataFrame(inspections), use_container_width=True, hide_index=True)
        else:
            st.info("No inspections found.")

    else:
        if current_role() not in {"admin", "pm"}:
            st.info("Only admin or pm users can add inspections.")
            return

        asset_options = {f"{a.get('asset_id')} - {a.get('asset_name')}": a for a in assets}
        selected_label = st.selectbox("Asset", list(asset_options.keys()))
        selected_asset = asset_options[selected_label]

        c1, c2, c3 = st.columns(3, gap="small")
        inspection_type = c1.selectbox("Inspection Type", ["Daily", "Weekly", "Monthly", "Pre-Use", "Damage Report"])
        inspection_date = c2.date_input("Inspection Date")
        inspector = c3.text_input("Inspector")

        status = st.selectbox("Status", ["Pass", "Needs Attention", "Fail"])
        ia1, ia2 = st.columns(2, gap="small")
        with ia1:
            issues_found = st.text_area("Issues Found", height=72)
        with ia2:
            corrective_action = st.text_area("Corrective Action", height=72)

        if st.button("Save Inspection", use_container_width=True):
            insert_row_admin(
                "asset_inspections",
                {
                    "asset_id": selected_asset["id"],
                    "inspection_type": inspection_type,
                    "inspection_date": inspection_date.isoformat(),
                    "inspector": inspector.strip(),
                    "status": status,
                    "issues_found": issues_found.strip(),
                    "corrective_action": corrective_action.strip(),
                    "created_by": current_profile().get("id"),
                },
            )
            st.success("Inspection saved.")
