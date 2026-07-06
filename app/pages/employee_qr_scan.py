"""Employee QR Scan — launch inventory, asset, and equipment scan workflows."""

from __future__ import annotations

import streamlit as st

try:
    from app.navigation import set_nav_slug
    from app.pages._core._access import begin_module
    from app.styles import inject_employee_portal_css, inject_global_css
except ImportError:
    from navigation import set_nav_slug  # type: ignore
    from pages._core._access import begin_module  # type: ignore
    from styles import inject_employee_portal_css, inject_global_css  # type: ignore


def render() -> None:
    if not begin_module("employee_qr_scan"):
        return
    inject_global_css()
    inject_employee_portal_css()
    st.markdown(
        '<span class="ips-employee-qr-page ips-page-shell-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    st.markdown('<h2 class="ips-ep-page-title">QR Scan</h2>', unsafe_allow_html=True)
    st.markdown(
        '<p class="ips-ep-muted">Choose what you are scanning. IPS supports inventory, assets, and equipment QR codes.</p>',
        unsafe_allow_html=True,
    )

    if st.button("📦  Scan Inventory / Stock", type="primary", use_container_width=True, key="eqs_inv"):
        set_nav_slug("scan_inventory")
        st.rerun()
    if st.button("🚜  Scan Asset / Equipment", use_container_width=True, key="eqs_ast"):
        set_nav_slug("scan_asset")
        st.rerun()

    st.caption("Inventory scans can be charged to a job from the scan form when prompted.")
