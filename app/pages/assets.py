"""Assets module (Phase 2B)."""

from __future__ import annotations

import html

import streamlit as st

try:
    from app.components.layout import render_filter_bar as layout_filter_bar
    from app.components.layout import render_tab_placeholder
    from app.components.status import status_pill_html
    from app.pages._core._data import load_assets, lookup_options, persist_asset
    from app.pages._core._crud import apply_persist_feedback, is_demo_id
    from app.pages._core._session import select_key, tab_key
    from app.ui.assets_components import (
        detail_header_html,
        detail_meta_strip_html,
        inject_assets_page_styles,
        maintenance_table_html,
        render_assets_header_inner_html,
        status_badge_html,
        summary_card_html,
        tab_button_label,
        table_header_html,
    )
    from app.utils.formatting import fmt_currency, fmt_date
except ImportError:
    from components.layout import render_filter_bar as layout_filter_bar  # type: ignore
    from components.layout import render_tab_placeholder  # type: ignore
    from components.status import status_pill_html  # type: ignore
    from pages._core._data import load_assets, lookup_options, persist_asset  # type: ignore
    from pages._core._crud import apply_persist_feedback, is_demo_id  # type: ignore
    from pages._core._session import select_key, tab_key  # type: ignore
    from ui.assets_components import (  # type: ignore
        detail_header_html,
        detail_meta_strip_html,
        inject_assets_page_styles,
        maintenance_table_html,
        render_assets_header_inner_html,
        status_badge_html,
        summary_card_html,
        tab_button_label,
        table_header_html,
    )
    from utils.formatting import fmt_currency, fmt_date  # type: ignore

_SEL = select_key("assets")
_TAB = tab_key("assets")
_ASSET_TABS = ["Overview", "Maintenance", "Documents", "Assignments", "Depreciation", "Notes", "Activity"]
_ASSET_GRID = "0.9fr 1.35fr 0.85fr 0.95fr 1fr 0.8fr 0.9fr 0.8fr 0.75fr"


def _filter_rows(
    rows: list[dict], *, q: str, category: str, location: str, status: str, department: str
) -> list[dict]:
    out = rows
    if q:
        ql = q.lower()
        out = [
            r
            for r in out
            if ql in str(r.get("asset_number", "")).lower()
            or ql in str(r.get("asset_name", "")).lower()
        ]
    if category and category != "All Categories":
        out = [r for r in out if str(r.get("category", "")) == category]
    if location and location != "All Locations":
        out = [r for r in out if str(r.get("location", "")) == location]
    if status and status != "All Statuses":
        out = [r for r in out if str(r.get("status", "")) == status]
    if department and department != "All Departments":
        out = [r for r in out if str(r.get("department", "")) == department]
    return out


def _clear_asset_filters() -> None:
    st.session_state["ast_search"] = ""
    st.session_state["ast_cat"] = "All Categories"
    st.session_state["ast_loc"] = "All Locations"
    st.session_state["ast_status"] = "All Statuses"
    st.session_state["ast_dept"] = "All Departments"


def _maintenance_rows(asset: dict) -> list[dict[str, str]]:
    operator = str(asset.get("operator") or "Mark Johnson")
    return [
        {
            "date": "Apr 20, 2025",
            "type": "Inspection",
            "description": "Quarterly inspection and safety check",
            "performed_by": operator,
            "cost": "$150.00",
            "next_due": "Jul 20, 2025",
            "status_html": status_badge_html("In Service").replace("In Service", "Completed"),
        },
        {
            "date": "Jan 20, 2025",
            "type": "Service",
            "description": "Grease bearings, check lights and brakes",
            "performed_by": operator,
            "cost": "$175.00",
            "next_due": "Apr 20, 2025",
            "status_html": status_badge_html("In Service").replace("In Service", "Completed"),
        },
        {
            "date": "Oct 20, 2024",
            "type": "Repair",
            "description": "Replaced left tail light and wiring",
            "performed_by": "Coastal Trailer Repair",
            "cost": "$85.00",
            "next_due": "Jan 20, 2025",
            "status_html": status_badge_html("In Service").replace("In Service", "Completed"),
        },
    ]


def _asset_image_html(asset: dict) -> str:
    url = str(
        asset.get("image_url")
        or asset.get("photo_url")
        or asset.get("asset_image_url")
        or ""
    ).strip()
    if url:
        safe = html.escape(url, quote=True)
        alt = html.escape(str(asset.get("asset_name") or "Asset image"), quote=True)
        return f'<div class="ips-assets-img-wrap"><img src="{safe}" alt="{alt}" style="width:100%;display:block;"></div>'
    return (
        '<div class="ips-assets-img-wrap">'
        '<div class="ips-assets-img-empty">Asset image<br><span style="font-weight:500;">Upload photo</span></div>'
        "</div>"
    )


def _asset_for_qr(asset: dict) -> dict:
    num = str(asset.get("asset_number") or asset.get("asset_id") or "").strip()
    return {**asset, "asset_id": num}


def _render_asset_qr_block(asset: dict, aid: str) -> None:
    try:
        from app.services.asset_qr import (
            asset_scan_link_url,
            qr_embed_subject,
            qr_label_2x1_sticker_download_filename,
            qr_label_2x1_sticker_pdf_bytes,
            qr_label_for_download,
            qr_payload,
            qr_png_bytes,
        )
    except ImportError:
        from services.asset_qr import (  # type: ignore
            asset_scan_link_url,
            qr_embed_subject,
            qr_label_2x1_sticker_download_filename,
            qr_label_2x1_sticker_pdf_bytes,
            qr_label_for_download,
            qr_payload,
            qr_png_bytes,
        )

    qr_asset = _asset_for_qr(asset)
    token = qr_payload(qr_asset)
    if not token:
        return
    subject = qr_embed_subject(qr_asset)
    scan_url = asset_scan_link_url(qr_code_value=token)

    with st.container(border=True):
        st.markdown(
            '<span class="ips-assets-qr-tool"></span>'
            '<p style="margin:0 0 0.35rem;font-weight:700;font-size:0.9rem;">Equipment QR</p>',
            unsafe_allow_html=True,
        )
        try:
            st.image(qr_png_bytes(subject), width=132)
        except Exception:
            st.caption(f"Scan code: {token}")
        st.caption(f"Asset tag: **{html.escape(token)}**", unsafe_allow_html=True)
        if scan_url.startswith("http"):
            st.caption("Scan with a phone camera to open this asset card.")
        else:
            st.caption("Set APP_BASE_URL so printed labels open the asset card when scanned.")
        dl1, dl2 = st.columns(2)
        with dl1:
            try:
                dl_bytes, dl_mime, dl_name = qr_label_for_download(qr_asset, subject)
                st.download_button(
                    "Print label",
                    data=dl_bytes,
                    file_name=dl_name,
                    mime=dl_mime,
                    key=f"ast_qr_label_{aid}",
                    use_container_width=True,
                )
            except Exception:
                st.download_button(
                    "Download QR (PNG)",
                    data=qr_png_bytes(subject),
                    file_name=f"{token}_qr.png",
                    mime="image/png",
                    key=f"ast_qr_png_{aid}",
                    use_container_width=True,
                )
        with dl2:
            try:
                st.download_button(
                    "2×1 sticker",
                    data=qr_label_2x1_sticker_pdf_bytes(qr_asset, subject),
                    file_name=qr_label_2x1_sticker_download_filename(qr_asset),
                    mime="application/pdf",
                    key=f"ast_qr_sticker_{aid}",
                    use_container_width=True,
                )
            except Exception:
                pass


def _render_detail(asset: dict) -> None:
    aid = str(asset.get("id") or "")
    asset_number = str(asset.get("asset_number") or "—")
    asset_name = str(asset.get("asset_name") or "Untitled asset")
    current_tab = str(st.session_state.get(_TAB) or "Overview")
    if current_tab not in _ASSET_TABS:
        current_tab = "Overview"
        st.session_state[_TAB] = current_tab

    with st.container(border=True):
        st.markdown('<span class="ips-assets-detail-anchor"></span>', unsafe_allow_html=True)
        top_l, top_meta, top_actions = st.columns([2.2, 3.7, 2.2], gap="medium")
        with top_l:
            st.markdown(
                detail_header_html(
                    asset_id=asset_number,
                    asset_name=asset_name,
                    status=str(asset.get("status") or ""),
                ),
                unsafe_allow_html=True,
            )
        with top_meta:
            st.markdown(
                detail_meta_strip_html(
                    [
                        ("Category", str(asset.get("category") or "—")),
                        ("Location", str(asset.get("location") or "—")),
                        ("Department", str(asset.get("department") or "—")),
                        ("Serial Number", str(asset.get("serial_number") or "—")),
                        ("Acquired Date", fmt_date(asset.get("acquired_date"))),
                        ("Current Value", fmt_currency(asset.get("value"))),
                    ]
                ),
                unsafe_allow_html=True,
            )
        with top_actions:
            st.markdown('<span class="ips-assets-detail-actions"></span>', unsafe_allow_html=True)
            a1, a2, a3 = st.columns([1, 1.35, 0.9], gap="small")
            with a1:
                if st.button("✎ Edit", key=f"ast_detail_edit_{aid}", use_container_width=True, disabled=is_demo_id(aid)):
                    st.session_state[f"ast_edit_open_{aid}"] = not st.session_state.get(f"ast_edit_open_{aid}", False)
            with a2:
                st.markdown('<span class="ips-assets-maint-primary"></span>', unsafe_allow_html=True)
                if st.button("⚒ Maintenance", key=f"ast_detail_maint_{aid}", type="primary", use_container_width=True):
                    st.session_state[_TAB] = "Maintenance"
                    st.rerun()
            with a3:
                if st.button("⌃", key=f"ast_detail_close_{aid}", use_container_width=True, help="Close details"):
                    st.session_state.pop(_SEL, None)
                    st.rerun()

        tabs = st.columns(len(_ASSET_TABS), gap="small")
        for col, tab in zip(tabs, _ASSET_TABS):
            with col:
                st.markdown('<span class="ips-assets-tabs-anchor"></span>', unsafe_allow_html=True)
                if st.button(
                    tab_button_label(tab),
                    key=f"ast_tab_{aid}_{tab}",
                    type="primary" if tab == current_tab else "secondary",
                    use_container_width=True,
                ):
                    st.session_state[_TAB] = tab
                    st.rerun()

        if current_tab != "Overview":
            if current_tab == "Maintenance":
                st.markdown(
                    '<div class="ips-assets-maint-section">'
                    '<div class="ips-assets-maint-head"><h4>Maintenance History</h4></div>'
                    f"{maintenance_table_html(_maintenance_rows(asset))}"
                    "</div>",
                    unsafe_allow_html=True,
                )
            else:
                render_tab_placeholder(f"{current_tab} will connect to Supabase in a later phase.")
        else:
            c1, c2, c3, c4 = st.columns([1.2, 1.1, 1.1, 1.15], gap="medium")
            with c1:
                st.markdown(
                    summary_card_html(
                        "Asset Details",
                        [
                            ("Asset Number", asset_number),
                            ("Asset Name", asset_name),
                            ("Category", str(asset.get("category") or "—")),
                            ("Status", status_badge_html(str(asset.get("status") or ""))),
                            ("Location", str(asset.get("location") or "—")),
                            ("Department", str(asset.get("department") or "—")),
                            ("Manufacturer", str(asset.get("manufacturer") or "—")),
                            ("Model", str(asset.get("model") or "—")),
                            ("Serial Number", str(asset.get("serial_number") or "—")),
                            ("Description", str(asset.get("description") or "—")),
                        ],
                        html_value_keys=frozenset({"Status"}),
                    ),
                    unsafe_allow_html=True,
                )
            with c2:
                st.markdown(
                    summary_card_html(
                        "Usage Information",
                        [
                            ("Current Operator", str(asset.get("operator") or "—")),
                            ("Primary Use", str(asset.get("primary_use") or asset.get("description") or "Equipment Transport")),
                            ("Hours/Miles", str(asset.get("hours_miles") or "—")),
                            ("Last Used", str(asset.get("last_used") or "—")),
                            ("Condition", str(asset.get("condition") or "Good")),
                            ("Next Service Due", str(asset.get("next_service_due") or "—")),
                        ],
                    ),
                    unsafe_allow_html=True,
                )
            with c3:
                value = fmt_currency(asset.get("value"))
                st.markdown(
                    summary_card_html(
                        "Financial Information",
                        [
                            ("Acquired Date", fmt_date(asset.get("acquired_date"))),
                            ("Purchase Price", fmt_currency(asset.get("purchase_price") or asset.get("value"))),
                            ("Current Value", value),
                            ("Salvage Value", fmt_currency(asset.get("salvage_value"))),
                            ("Depreciation Method", str(asset.get("depreciation_method") or "Straight Line")),
                            ("Useful Life", str(asset.get("useful_life") or "7 years")),
                            ("Annual Depreciation", fmt_currency(asset.get("annual_depreciation"))),
                        ],
                    ),
                    unsafe_allow_html=True,
                )
            with c4:
                st.markdown(
                    '<div class="ips-assets-summary-card"><h4>Image</h4>'
                    f"{_asset_image_html(asset)}</div>",
                    unsafe_allow_html=True,
                )
                _render_asset_qr_block(asset, aid)

            st.markdown(
                '<div class="ips-assets-maint-section">'
                '<div class="ips-assets-maint-head"><h4>Maintenance History</h4></div>'
                f"{maintenance_table_html(_maintenance_rows(asset))}"
                "</div>",
                unsafe_allow_html=True,
            )

        if st.session_state.get(f"ast_edit_open_{aid}") and not is_demo_id(aid):
            with st.expander("Edit asset", expanded=True):
                ac1, ac2 = st.columns(2)
                with ac1:
                    st.text_input("Asset #", value=str(asset.get("asset_number") or ""), key=f"ast_edit_num_{aid}")
                    st.text_input("Name", value=str(asset.get("asset_name") or ""), key=f"ast_edit_name_{aid}")
                    st.selectbox("Category", lookup_options("asset_categories"), key=f"ast_edit_cat_{aid}")
                    st.selectbox("Status", lookup_options("asset_statuses"), key=f"ast_edit_status_{aid}")
                with ac2:
                    st.text_input("Location", value=str(asset.get("location") or ""), key=f"ast_edit_loc_{aid}")
                    st.text_input("Serial", value=str(asset.get("serial_number") or ""), key=f"ast_edit_serial_{aid}")
                if st.button("Save asset", key=f"ast_save_{aid}", type="primary"):
                    ok, msg = persist_asset(
                        {
                            "asset_number": st.session_state.get(f"ast_edit_num_{aid}"),
                            "asset_name": st.session_state.get(f"ast_edit_name_{aid}"),
                            "category": st.session_state.get(f"ast_edit_cat_{aid}"),
                            "status": st.session_state.get(f"ast_edit_status_{aid}"),
                            "location": st.session_state.get(f"ast_edit_loc_{aid}"),
                            "serial_number": st.session_state.get(f"ast_edit_serial_{aid}"),
                        },
                        row_id=aid,
                    )
                    if apply_persist_feedback(ok, msg):
                        st.rerun()


def _render_assets_table(rows: list[dict], *, selected_id: str) -> None:
    if not rows:
        st.caption("No assets match the current filters.")
        return

    grid = f"grid-template-columns: {_ASSET_GRID};"

    with st.container(border=True):
        st.markdown(
            '<span class="ips-assets-table-anchor ips-assets-click-table ips-clean-table"></span>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="ips-clean-header ips-assets-table-head-row" style="{grid}">'
            f"{table_header_html('Asset #')}"
            f"{table_header_html('Asset Name')}"
            f"{table_header_html('Category')}"
            f"{table_header_html('Location')}"
            f"{table_header_html('Department')}"
            f"{table_header_html('Status')}"
            f"{table_header_html('Acquired Date')}"
            f"{table_header_html('Value')}"
            f"{table_header_html('Actions', sortable=False)}"
            "</div>",
            unsafe_allow_html=True,
        )

        for row_idx, asset in enumerate(rows):
            aid = str(asset.get("id") or "").strip()
            if not aid:
                continue
            selected = aid == selected_id
            row_cls = "ips-clean-row ips-assets-row selected" if selected else "ips-clean-row ips-assets-row"
            aid_attr = html.escape(aid, quote=True)
            number = html.escape(str(asset.get("asset_number") or "—"))
            name = html.escape(str(asset.get("asset_name") or "—"))
            category = html.escape(str(asset.get("category") or "—"))
            location = html.escape(str(asset.get("location") or "—"))
            department = html.escape(str(asset.get("department") or "—"))
            acquired = html.escape(fmt_date(asset.get("acquired_date")))
            value = html.escape(fmt_currency(asset.get("value")))
            with st.container():
                st.markdown(
                    '<span class="ips-assets-row-wrap ips-clean-row-wrap" aria-hidden="true"></span>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div class="{row_cls}" style="{grid}" data-row-id="{aid_attr}" role="button" tabindex="0">'
                    f'<span class="ips-clean-link">{number}</span>'
                    f'<span class="ips-assets-name-cell">{name}</span>'
                    f'<span class="ips-assets-muted-cell">{category}</span>'
                    f'<span class="ips-assets-muted-cell">{location}</span>'
                    f'<span class="ips-assets-muted-cell">{department}</span>'
                    f'<span>{status_badge_html(str(asset.get("status") or ""))}</span>'
                    f'<span class="ips-assets-muted-cell">{acquired}</span>'
                    f'<span class="ips-assets-muted-cell">{value}</span>'
                    f'<span class="ips-assets-act-slot" title="View">👁</span>'
                    "</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    '<span class="ips-assets-row-select-btn ips-clean-row-select-btn" aria-hidden="true"></span>',
                    unsafe_allow_html=True,
                )
                if st.button(
                    " ",
                    key=f"ast_row_sel_{row_idx}_{aid}",
                    help=f"Select asset {number}",
                ):
                    st.session_state[_SEL] = aid
                    st.session_state[_TAB] = "Overview"
                    st.rerun()
                st.markdown(
                    '<span class="ips-assets-actcol ips-clean-actions" aria-hidden="true"></span>',
                    unsafe_allow_html=True,
                )
                if st.button("👁", key=f"ast_view_{row_idx}_{aid}", help="View asset"):
                    st.session_state[_SEL] = aid
                    st.session_state[_TAB] = "Overview"
                    st.rerun()


def render() -> None:
    try:
        from app.pages._core._access import begin_module
    except ImportError:
        from pages._core._access import begin_module  # type: ignore
    if not begin_module("assets"):
        return
    try:
        from app.services.asset_qr import apply_pending_asset_deeplink
    except ImportError:
        from services.asset_qr import apply_pending_asset_deeplink  # type: ignore
    apply_pending_asset_deeplink()
    inject_assets_page_styles()
    st.markdown(
        '<span class="ips-assets-page ips-page-shell-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    rows = load_assets()
    categories = sorted({str(r.get("category") or "") for r in rows if r.get("category")})
    locations = sorted({str(r.get("location") or "") for r in rows if r.get("location")})
    departments = sorted({str(r.get("department") or "") for r in rows if r.get("department")})

    with st.container(border=True):
        st.markdown('<span class="ips-assets-header-anchor"></span>', unsafe_allow_html=True)
        act_l, act_r = st.columns([5.5, 1.8], gap="small")
        with act_l:
            st.markdown(render_assets_header_inner_html(), unsafe_allow_html=True)
        with act_r:
            st.markdown('<div style="height:1.35rem"></div>', unsafe_allow_html=True)
            e1, e2 = st.columns(2, gap="small")
            with e1:
                st.markdown('<span class="ips-assets-export-btn"></span>', unsafe_allow_html=True)
                st.button("⇩ Export", key="ast_export", use_container_width=True)
            with e2:
                st.markdown('<span class="ips-assets-new-btn"></span>', unsafe_allow_html=True)
                if st.button("+ New Asset", key="ast_new", type="primary", use_container_width=True):
                    st.session_state["ips_ast_form"] = True

    if st.session_state.get("ips_ast_form"):
        with st.expander("New asset", expanded=True):
            st.text_input("Asset #", key="ast_new_num")
            st.text_input("Asset name", key="ast_new_name")
            st.selectbox("Category", lookup_options("asset_categories"), key="ast_new_cat")
            st.selectbox("Status", lookup_options("asset_statuses"), key="ast_new_status")
            if st.button("Save asset", key="ast_save_new", type="primary"):
                ok, msg = persist_asset(
                    {
                        "asset_number": st.session_state.get("ast_new_num"),
                        "asset_name": st.session_state.get("ast_new_name"),
                        "category": st.session_state.get("ast_new_cat"),
                        "status": st.session_state.get("ast_new_status"),
                    }
                )
                if apply_persist_feedback(ok, msg, clear_keys=("ips_ast_form",)):
                    st.rerun()

    with st.container(border=True):
        st.markdown('<span class="ips-assets-filter-anchor"></span>', unsafe_allow_html=True)

        def _filters() -> None:
            c1, c2, c3, c4, c5, c6 = st.columns([1.8, 1, 1, 1, 1, 0.7])
            with c1:
                st.text_input("Search", placeholder="Search assets…", key="ast_search", label_visibility="collapsed")
            with c2:
                st.selectbox("Category", ["All Categories", *categories], key="ast_cat", label_visibility="collapsed")
            with c3:
                st.selectbox("Location", ["All Locations", *locations], key="ast_loc", label_visibility="collapsed")
            with c4:
                st.selectbox(
                    "Status",
                    ["All Statuses", *lookup_options("asset_statuses")],
                    key="ast_status",
                    label_visibility="collapsed",
                )
            with c5:
                st.selectbox("Department", ["All Departments", *departments], key="ast_dept", label_visibility="collapsed")
            with c6:
                st.markdown('<span class="ips-assets-clear-filters"></span>', unsafe_allow_html=True)
                st.button("Clear Filters", key="ast_clear", use_container_width=True, on_click=_clear_asset_filters)

        layout_filter_bar(_filters)

    filtered = _filter_rows(
        rows,
        q=str(st.session_state.get("ast_search") or "").strip(),
        category=str(st.session_state.get("ast_cat") or "All Categories"),
        location=str(st.session_state.get("ast_loc") or "All Locations"),
        status=str(st.session_state.get("ast_status") or "All Statuses"),
        department=str(st.session_state.get("ast_dept") or "All Departments"),
    )

    selected_id = str(st.session_state.get(_SEL) or "")
    if selected_id and not any(str(r.get("id")) == selected_id for r in filtered):
        st.session_state.pop(_SEL, None)
        selected_id = ""

    st.caption(f"{len(filtered)} asset(s) · Click a row to open details")

    _render_assets_table(filtered, selected_id=selected_id)

    sel = str(st.session_state.get(_SEL) or "")
    if sel:
        asset = next((r for r in filtered if str(r.get("id")) == sel), None)
        if asset:
            _render_detail(asset)
