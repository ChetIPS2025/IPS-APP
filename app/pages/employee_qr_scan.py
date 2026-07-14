"""Employee QR Scan — launch inventory, asset, and equipment scan workflows."""

from __future__ import annotations

import streamlit as st

from app.components.headers import render_page_header
from app.navigation import set_nav_slug
from app.pages._core._access import begin_module
from app.styles import inject_employee_portal_css
def render() -> None:
    if not begin_module("employee_qr_scan"):
        return
    inject_employee_portal_css()
    st.markdown(
        '<span class="ips-employee-qr-page" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    render_page_header(
        "QR Scan",
        "Choose what you are scanning — inventory, assets, or equipment.",
        icon="📷",
    )

    if st.button("📦  Scan Inventory / Stock", type="primary", use_container_width=True, key="eqs_inv"):
        set_nav_slug("scan_inventory")
        st.rerun()
    if st.button("🚜  Scan Asset / Equipment", use_container_width=True, key="eqs_ast"):
        set_nav_slug("scan_asset")
        st.rerun()

    st.caption("Inventory scans can be charged to a job from the scan form when prompted.")
