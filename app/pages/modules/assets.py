"""Assets module (Phase 2B)."""

from __future__ import annotations

import html

import streamlit as st

try:
    from app.components.headers import render_page_header
    from app.components.layout import render_filter_bar as layout_filter_bar
    from app.components.layout import render_tab_placeholder
    from app.components.modals import render_record_detail_dialog
    from app.components.status import status_pill_html
    from app.components.tables import render_clickable_table, render_data_table
    from app.components.tabs import render_tabs
    from app.pages.modules._data import load_assets, lookup_options, persist_asset
    from app.pages.modules._crud import apply_persist_feedback, is_demo_id
    from app.pages.modules._session import select_key, tab_key
    from app.styles import inject_global_css
    from app.utils.constants import ASSET_STATUSES
    from app.utils.formatting import fmt_currency, fmt_date
except ImportError:
    from components.headers import render_page_header  # type: ignore
    from components.layout import render_filter_bar as layout_filter_bar  # type: ignore
    from components.layout import render_tab_placeholder  # type: ignore
    from components.modals import render_record_detail_dialog  # type: ignore
    from components.status import status_pill_html  # type: ignore
    from components.tables import render_clickable_table, render_data_table  # type: ignore
    from components.tabs import render_tabs  # type: ignore
    from pages.modules._data import load_assets, lookup_options, persist_asset  # type: ignore
    from pages.modules._crud import apply_persist_feedback, is_demo_id  # type: ignore
    from pages.modules._session import select_key, tab_key  # type: ignore
    from styles import inject_global_css  # type: ignore
    from utils.constants import ASSET_STATUSES  # type: ignore
    from utils.formatting import fmt_currency, fmt_date  # type: ignore

_SEL = select_key("assets")
_TAB = tab_key("assets")


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


def _render_detail(asset: dict) -> None:
    title = str(asset.get("asset_name") or asset.get("asset_number") or "")

    def _tabs() -> None:
        render_tabs(
            [
                "Overview",
                "Maintenance",
                "Documents",
                "Assignments",
                "Depreciation",
                "Notes",
                "Activity",
            ],
            session_key=_TAB,
            default="Overview",
        )

    def _body() -> None:
        ot = "d" + "iv"
        st.markdown(
            f'<{ot} class="ips-detail-meta-row">'
            f"<span>Status<br>{status_pill_html(str(asset.get('status') or ''))}</span>"
            f"<span>Category<br><strong>{html.escape(str(asset.get('category') or '—'))}</strong></span>"
            f"<span>Value<br><strong>{html.escape(fmt_currency(asset.get('value')))}</strong></span>"
            f"</{ot}>",
            unsafe_allow_html=True,
        )
        tab = str(st.session_state.get(_TAB) or "Overview")
        if tab == "Maintenance":
            st.markdown('<p class="ips-panel-title">Maintenance History</p>', unsafe_allow_html=True)
            maint = [
                {"id": "mx1", "date": "2025-04-12", "type": "Preventive", "description": "Annual inspection", "by": "Shop", "cost": 150, "status": "Completed"},
            ]

            def _mx_cell(field: str, row: dict) -> str:
                if field == "status":
                    return status_pill_html(str(row.get("status") or ""))
                if field == "cost":
                    return html.escape(fmt_currency(row.get("cost")))
                return html.escape(str(row.get(field) or "—"))

            render_data_table(
                maint,
                [
                    ("date", "DATE"),
                    ("type", "TYPE"),
                    ("description", "DESCRIPTION"),
                    ("by", "PERFORMED BY"),
                    ("cost", "COST"),
                    ("status", "STATUS"),
                ],
                row_id_key="id",
                selected_id=None,
                session_select_key="ips_sel_asset_maint",
                col_fr=["0.7fr", "0.7fr", "1.4fr", "0.9fr", "0.6fr", "0.7fr"],
                cell_renderer=_mx_cell,
            )
            return
        if tab != "Overview":
            st.info(f"{tab} will connect to Supabase in a later phase.")
            return
        c1, c2, c3 = st.columns([1.1, 1.1, 0.9])
        with c1:
            st.markdown("**Asset Details**")
            st.markdown(
                f'<dl class="ips-info-grid">'
                f"<dt>Asset #</dt><dd>{html.escape(str(asset.get('asset_number') or '—'))}</dd>"
                f"<dt>Name</dt><dd>{html.escape(str(asset.get('asset_name') or '—'))}</dd>"
                f"<dt>Category</dt><dd>{html.escape(str(asset.get('category') or '—'))}</dd>"
                f"<dt>Status</dt><dd>{status_pill_html(str(asset.get('status') or ''))}</dd>"
                f"<dt>Serial</dt><dd>{html.escape(str(asset.get('serial_number') or '—'))}</dd>"
                f"<dt>Description</dt><dd>{html.escape(str(asset.get('description') or '—'))}</dd>"
                f"</dl>",
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown("**Usage & Financial**")
            st.markdown(
                f'<dl class="ips-info-grid">'
                f"<dt>Location</dt><dd>{html.escape(str(asset.get('location') or '—'))}</dd>"
                f"<dt>Department</dt><dd>{html.escape(str(asset.get('department') or '—'))}</dd>"
                f"<dt>Operator</dt><dd>{html.escape(str(asset.get('operator') or '—'))}</dd>"
                f"<dt>Acquired</dt><dd>{html.escape(fmt_date(asset.get('acquired_date')))}</dd>"
                f"<dt>Current Value</dt><dd>{html.escape(fmt_currency(asset.get('value')))}</dd>"
                f"<dt>Mfr / Model</dt><dd>{html.escape(str(asset.get('manufacturer') or '—'))} / {html.escape(str(asset.get('model') or '—'))}</dd>"
                f"</dl>",
                unsafe_allow_html=True,
            )
        with c3:
            st.markdown("**Photo**")
            st.markdown(
                f'<{ot} class="ips-photo-card">📷 Asset photo<br><span style="font-size:0.75rem">'
                f"{html.escape(str(asset.get('asset_name') or 'Upload image'))}</span></{ot}>",
                unsafe_allow_html=True,
            )
        aid = str(asset.get("id") or "")
        if not is_demo_id(aid):
            with st.expander("Edit asset", expanded=False):
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

    render_record_detail_dialog(
        f"{title} — Asset Details",
        module_name="assets",
        session_select_key=_SEL,
        tabs_fn=_tabs,
        body_fn=_body,
    )


def render() -> None:
    try:
        from app.pages.modules._access import begin_module
    except ImportError:
        from pages.modules._access import begin_module  # type: ignore
    if not begin_module("assets"):
        return
    rows = load_assets()
    categories = sorted({str(r.get("category") or "") for r in rows if r.get("category")})
    locations = sorted({str(r.get("location") or "") for r in rows if r.get("location")})
    departments = sorted({str(r.get("department") or "") for r in rows if r.get("department")})

    act_l, act_r = st.columns([3, 1])
    with act_l:
        render_page_header("Assets", "Track and manage all company assets and equipment.")
    with act_r:
        st.button("Export", key="ast_export", use_container_width=True)
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
            if st.button("Clear", key="ast_clear", use_container_width=True):
                st.session_state["ast_search"] = ""
                st.session_state["ast_cat"] = "All Categories"
                st.session_state["ast_loc"] = "All Locations"
                st.session_state["ast_status"] = "All Statuses"
                st.session_state["ast_dept"] = "All Departments"
                st.rerun()

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

    def _cell(field: str, row: dict) -> str:
        if field == "status":
            return status_pill_html(str(row.get("status") or ""))
        if field == "asset_number":
            return f'<span style="color:#2563eb;font-weight:600">{html.escape(str(row.get("asset_number") or ""))}</span>'
        if field == "value":
            return html.escape(fmt_currency(row.get("value")))
        if field == "acquired_date":
            return html.escape(fmt_date(row.get("acquired_date")))
        return html.escape(str(row.get(field) or "—"))

    def _plain_cell(field: str, row: dict) -> str:
        if field == "value":
            return fmt_currency(row.get("value"))
        if field == "acquired_date":
            return fmt_date(row.get("acquired_date"))
        return str(row.get(field) or "—")

    sel = render_clickable_table(
        filtered,
        [
            ("asset_number", "ASSET #"),
            ("asset_name", "ASSET NAME"),
            ("category", "CATEGORY"),
            ("location", "LOCATION"),
            ("department", "DEPARTMENT"),
            ("status", "STATUS"),
            ("acquired_date", "ACQUIRED"),
            ("value", "VALUE"),
        ],
        "assets_list",
        row_id_key="id",
        session_select_key=_SEL,
        selected_id=selected_id or None,
        plain_cell=_plain_cell,
        html_cell=_cell,
    )

    if sel:
        asset = next((r for r in filtered if str(r.get("id")) == sel), None)
        if asset:
            _render_detail(asset)
