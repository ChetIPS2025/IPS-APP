"""Assets module (Phase 2B)."""

from __future__ import annotations

import html

import streamlit as st

try:
    from app.components.clickable_table import render_clickable_table
    from app.components.layout import render_filter_bar as layout_filter_bar
    from app.components.record_modal import (
        build_modal_cache,
        clear_record_modal,
        detail_field_html,
        dialog_card_html,
        get_modal_record,
        is_edit_mode,
        open_record_modal,
        placeholder_html,
        record_session_key,
        render_edit_form_header,
        render_missing_record,
        render_modal_header,
        render_modal_edit_button,
        render_modal_meta_grid,
        render_modal_shell,
        render_save_cancel_actions,
        safe_value,
        set_edit_mode,
        set_view_mode,
        show_modal_if_pending,
    )
    from app.pages._core._data import load_assets, lookup_options, persist_asset
    from app.pages._core._crud import apply_persist_feedback, is_demo_id
    from app.pages._core._session import select_key
    from app.ui.assets_components import (
        inject_assets_page_styles,
        maintenance_table_html,
        render_assets_header_inner_html,
        status_badge_html,
        summary_card_html,
    )
    from app.utils.formatting import fmt_currency, fmt_date
except ImportError:
    from components.clickable_table import render_clickable_table  # type: ignore
    from components.layout import render_filter_bar as layout_filter_bar  # type: ignore
    from components.record_modal import (  # type: ignore
        build_modal_cache,
        clear_record_modal,
        detail_field_html,
        dialog_card_html,
        get_modal_record,
        is_edit_mode,
        open_record_modal,
        placeholder_html,
        record_session_key,
        render_edit_form_header,
        render_missing_record,
        render_modal_header,
        render_modal_edit_button,
        render_modal_meta_grid,
        render_modal_shell,
        render_save_cancel_actions,
        safe_value,
        set_edit_mode,
        set_view_mode,
        show_modal_if_pending,
    )
    from pages._core._data import load_assets, lookup_options, persist_asset  # type: ignore
    from pages._core._crud import apply_persist_feedback, is_demo_id  # type: ignore
    from pages._core._session import select_key  # type: ignore
    from ui.assets_components import (  # type: ignore
        inject_assets_page_styles,
        maintenance_table_html,
        render_assets_header_inner_html,
        status_badge_html,
        summary_card_html,
    )
    from utils.formatting import fmt_currency, fmt_date  # type: ignore

_SEL = select_key("assets")
_MOD = "assets"
_ASSETS_MODAL_KEY = "ips_assets_detail_modal_id"
_ASSETS_CACHE_KEY = "_ips_assets_modal_by_id"
_ASSET_TABS = ["Overview", "Maintenance", "Documents", "Assignments", "Depreciation", "Notes", "Activity"]


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


def _clear_assets_detail_modal() -> None:
    clear_record_modal(
        table_key="assets_list",
        session_select_key=_SEL,
        modal_key=_ASSETS_MODAL_KEY,
        module=_MOD,
    )


def _open_assets_detail_modal(asset_id: str, asset: dict | None = None) -> None:
    open_record_modal(
        asset_id,
        asset,
        session_select_key=_SEL,
        modal_key=_ASSETS_MODAL_KEY,
        module=_MOD,
        id_fields=("id", "asset_number"),
    )


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


def _seed_asset_edit_form(asset: dict) -> None:
    aid = str(asset.get("id") or "")
    st.session_state[f"ast_edit_num_{aid}"] = str(asset.get("asset_number") or "")
    st.session_state[f"ast_edit_name_{aid}"] = str(asset.get("asset_name") or "")
    st.session_state[f"ast_edit_cat_{aid}"] = str(asset.get("category") or lookup_options("asset_categories")[0])
    st.session_state[f"ast_edit_status_{aid}"] = str(asset.get("status") or lookup_options("asset_statuses")[0])
    st.session_state[f"ast_edit_loc_{aid}"] = str(asset.get("location") or "")
    st.session_state[f"ast_edit_serial_{aid}"] = str(asset.get("serial_number") or "")


def _set_asset_view_mode(asset: dict) -> None:
    rk = record_session_key(asset, "id", "asset_number")
    set_view_mode(_MOD, rk)


def _set_asset_edit_mode(asset: dict) -> None:
    rk = record_session_key(asset, "id", "asset_number")
    set_edit_mode(_MOD, rk)
    _seed_asset_edit_form(asset)


def _render_asset_edit_form(asset: dict) -> None:
    aid = str(asset.get("id") or "")
    rk = record_session_key(asset, "id", "asset_number")
    if f"ast_edit_num_{aid}" not in st.session_state:
        _seed_asset_edit_form(asset)

    render_edit_form_header("Edit Asset")

    if is_demo_id(aid):
        st.caption("Demo records cannot be edited until saved to Supabase.")
        return

    ac1, ac2 = st.columns(2)
    with ac1:
        st.text_input("Asset #", key=f"ast_edit_num_{aid}")
        st.text_input("Name", key=f"ast_edit_name_{aid}")
        st.selectbox("Category", lookup_options("asset_categories"), key=f"ast_edit_cat_{aid}")
        st.selectbox("Status", lookup_options("asset_statuses"), key=f"ast_edit_status_{aid}")
    with ac2:
        st.text_input("Location", key=f"ast_edit_loc_{aid}")
        st.text_input("Serial", key=f"ast_edit_serial_{aid}")

    cancelled, saved = render_save_cancel_actions(
        module=_MOD,
        record_key=rk,
        cancel_key=f"ast_edit_cancel_{aid}",
        save_key=f"ast_edit_save_{aid}",
    )
    if cancelled:
        st.rerun()
    if saved:
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
        if ok:
            set_view_mode(_MOD, rk)
            st.success(msg or "Asset saved.")
            st.rerun()
        else:
            st.error(msg or "Could not save asset.")


def _render_asset_detail_tabs(asset: dict) -> None:
    aid = str(asset.get("id") or "")
    asset_number = safe_value(asset.get("asset_number"))
    asset_name = safe_value(asset.get("asset_name"))
    status = safe_value(asset.get("status"))

    (
        tab_overview,
        tab_maintenance,
        tab_documents,
        tab_assignments,
        tab_depreciation,
        tab_notes,
        tab_activity,
    ) = st.tabs(_ASSET_TABS)

    with tab_overview:
        c1, c2 = st.columns([1.2, 1])
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

        c3, c4 = st.columns([1, 1])
        with c3:
            st.markdown(
                summary_card_html(
                    "Financial Information",
                    [
                        ("Acquired Date", fmt_date(asset.get("acquired_date"))),
                        ("Purchase Price", fmt_currency(asset.get("purchase_price") or asset.get("value"))),
                        ("Current Value", fmt_currency(asset.get("value"))),
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
                f'<div class="ips-assets-summary-card"><h4>Image</h4>{_asset_image_html(asset)}</div>',
                unsafe_allow_html=True,
            )
            _render_asset_qr_block(asset, aid)

    with tab_maintenance:
        st.markdown(
            '<div class="ips-assets-maint-section">'
            '<div class="ips-assets-maint-head"><h4>Maintenance History</h4></div>'
            f"{maintenance_table_html(_maintenance_rows(asset))}"
            "</div>",
            unsafe_allow_html=True,
        )

    with tab_documents:
        placeholder_html("Asset documents will appear here when connected to Supabase.")

    with tab_assignments:
        assign_html = (
            f'<div class="ips-detail-grid">'
            f"{detail_field_html('Current Operator', asset.get('operator'))}"
            f"{detail_field_html('Department', asset.get('department'))}"
            f"{detail_field_html('Location', asset.get('location'))}"
            f"{detail_field_html('Primary Use', asset.get('primary_use') or asset.get('description'))}"
            f"</div>"
        )
        st.markdown(dialog_card_html("Assignments", assign_html), unsafe_allow_html=True)

    with tab_depreciation:
        dep_html = (
            f'<div class="ips-detail-grid">'
            f"{detail_field_html('Acquired Date', fmt_date(asset.get('acquired_date')))}"
            f"{detail_field_html('Purchase Price', fmt_currency(asset.get('purchase_price') or asset.get('value')))}"
            f"{detail_field_html('Current Value', fmt_currency(asset.get('value')))}"
            f"{detail_field_html('Salvage Value', fmt_currency(asset.get('salvage_value')))}"
            f"{detail_field_html('Depreciation Method', asset.get('depreciation_method') or 'Straight Line')}"
            f"{detail_field_html('Useful Life', asset.get('useful_life') or '7 years')}"
            f"{detail_field_html('Annual Depreciation', fmt_currency(asset.get('annual_depreciation')))}"
            f"</div>"
        )
        st.markdown(dialog_card_html("Depreciation", dep_html), unsafe_allow_html=True)

    with tab_notes:
        notes_text = safe_value(asset.get("description"), "No notes entered.")
        notes_html = (
            f'<p style="margin:0;font-size:0.875rem;color:#0f172a;line-height:1.5;white-space:pre-wrap;">'
            f"{html.escape(notes_text)}"
            f"</p>"
        )
        st.markdown(dialog_card_html("Notes", notes_html), unsafe_allow_html=True)

    with tab_activity:
        placeholder_html("Asset activity history will appear here when connected to Supabase.")


def render_asset_detail_dialog(asset: dict) -> None:
    rk = record_session_key(asset, "id", "asset_number")
    asset_number = safe_value(asset.get("asset_number"))
    asset_name = safe_value(asset.get("asset_name"))
    status = safe_value(asset.get("status"))

    render_modal_shell()
    render_modal_header(title=asset_number, subtitle=asset_name, status=status)

    render_modal_edit_button(
        module=_MOD,
        record_key=rk,
        on_edit=lambda: _set_asset_edit_mode(asset),
        key_prefix=f"assets_modal_{rk}",
    )

    render_modal_meta_grid(
        [
            ("Category", safe_value(asset.get("category"))),
            ("Location", safe_value(asset.get("location"))),
            ("Department", safe_value(asset.get("department"))),
            ("Current Value", fmt_currency(asset.get("value"))),
        ]
    )

    if is_edit_mode(_MOD, rk):
        _render_asset_edit_form(asset)
    else:
        _render_asset_detail_tabs(asset)


@st.dialog("Asset Details", width="large", on_dismiss=_clear_assets_detail_modal)
def _show_assets_detail_modal() -> None:
    asset = get_modal_record(
        cache_key=_ASSETS_CACHE_KEY,
        modal_key=_ASSETS_MODAL_KEY,
        session_select_key=_SEL,
    )
    if not asset:
        sel = str(st.session_state.get(_ASSETS_MODAL_KEY) or st.session_state.get(_SEL) or "").strip()
        rows = st.session_state.get(_ASSETS_CACHE_KEY)
        if isinstance(rows, dict) and sel:
            asset = rows.get(sel)
    if not asset:
        render_missing_record(_clear_assets_detail_modal, close_key="assets_modal_missing_close")
        return
    render_asset_detail_dialog(asset)


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

    def _display_cell(field: str, row: dict) -> str:
        if field == "acquired_date":
            return fmt_date(row.get("acquired_date"))
        if field == "value":
            return fmt_currency(row.get("value"))
        val = row.get(field)
        return str(val).strip() if val is not None and str(val).strip() else "—"

    build_modal_cache(filtered, cache_key=_ASSETS_CACHE_KEY)

    deeplink_sel = str(st.session_state.get(_SEL) or "").strip()
    if deeplink_sel and not str(st.session_state.get(_ASSETS_MODAL_KEY) or "").strip():
        cached = st.session_state.get(_ASSETS_CACHE_KEY)
        if isinstance(cached, dict) and deeplink_sel in cached:
            _open_assets_detail_modal(deeplink_sel, cached[deeplink_sel])

    render_clickable_table(
        filtered,
        [
            ("asset_number", "ASSET #"),
            ("asset_name", "ASSET NAME"),
            ("category", "CATEGORY"),
            ("location", "LOCATION"),
            ("department", "DEPARTMENT"),
            ("status", "STATUS"),
            ("acquired_date", "ACQUIRED DATE"),
            ("value", "VALUE"),
        ],
        "assets_list",
        row_id_key="id",
        session_select_key=_SEL,
        format_cell=_display_cell,
        click_caption=f"{len(filtered)} asset(s) · Click a row to open details.",
        on_row_selected=_open_assets_detail_modal,
    )

    show_modal_if_pending(_ASSETS_MODAL_KEY, _show_assets_detail_modal)
