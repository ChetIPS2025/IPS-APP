"""Inventory module (Phase 2B)."""

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
    from app.pages.modules._data import load_inventory, lookup_options, persist_inventory
    from app.pages.modules._crud import apply_persist_feedback, is_demo_id
    from app.pages.modules._session import select_key, tab_key
    from app.styles import inject_global_css
    from app.utils.constants import INVENTORY_STATUSES
    from app.utils.formatting import fmt_currency
except ImportError:
    from components.headers import render_page_header  # type: ignore
    from components.layout import render_filter_bar as layout_filter_bar  # type: ignore
    from components.layout import render_selected_detail_panel, render_tab_placeholder  # type: ignore
    from components.status import status_pill_html  # type: ignore
    from components.tables import render_data_table  # type: ignore
    from components.tabs import render_tabs  # type: ignore
    from pages.modules._data import load_inventory, lookup_options, persist_inventory  # type: ignore
    from pages.modules._crud import apply_persist_feedback, is_demo_id  # type: ignore
    from pages.modules._session import select_key, tab_key  # type: ignore
    from styles import inject_global_css  # type: ignore
    from utils.constants import INVENTORY_STATUSES  # type: ignore
    from utils.formatting import fmt_currency  # type: ignore

_SEL = select_key("inventory")
_TAB = tab_key("inventory")


def _filter_rows(rows: list[dict], *, q: str, category: str, location: str, status: str) -> list[dict]:
    out = rows
    if q:
        ql = q.lower()
        out = [
            r
            for r in out
            if ql in str(r.get("sku", "")).lower() or ql in str(r.get("name", "")).lower()
        ]
    if category and category != "All Categories":
        out = [r for r in out if str(r.get("category", "")) == category]
    if location and location != "All Locations":
        out = [r for r in out if str(r.get("location", "")) == location]
    if status and status != "All Statuses":
        out = [r for r in out if str(r.get("status", "")) == status]
    return out


def _render_detail(item: dict) -> None:
    title = str(item.get("name") or item.get("sku") or "")

    def _tabs() -> None:
        render_tabs(
            [
                "Overview",
                "Stock History",
                "Transactions",
                "Purchase Orders",
                "Vendors",
                "Notes",
                "Attachments",
            ],
            session_key=_TAB,
            default="Overview",
        )

    def _body() -> None:
        ot = "d" + "iv"
        st.markdown(
            f'<{ot} class="ips-detail-meta-row">'
            f"<span>Status<br>{status_pill_html(str(item.get('status') or ''))}</span>"
            f"<span>SKU<br><strong>{html.escape(str(item.get('sku') or '—'))}</strong></span>"
            f"<span>On Hand<br><strong>{int(item.get('qty_on_hand') or 0)}</strong></span>"
            f"</{ot}>",
            unsafe_allow_html=True,
        )
        tab = str(st.session_state.get(_TAB) or "Overview")
        if tab != "Overview":
            render_tab_placeholder(f"{tab} will connect to Supabase in a later phase.")
            return
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Item Details**")
            st.markdown(
                f'<dl class="ips-info-grid">'
                f"<dt>SKU</dt><dd>{html.escape(str(item.get('sku') or '—'))}</dd>"
                f"<dt>Name</dt><dd>{html.escape(str(item.get('name') or '—'))}</dd>"
                f"<dt>Category</dt><dd>{html.escape(str(item.get('category') or '—'))}</dd>"
                f"<dt>Status</dt><dd>{status_pill_html(str(item.get('status') or ''))}</dd>"
                f"<dt>Location</dt><dd>{html.escape(str(item.get('location') or '—'))}</dd>"
                f"<dt>Department</dt><dd>{html.escape(str(item.get('department') or '—'))}</dd>"
                f"</dl>",
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown("**Stock**")
            st.markdown(
                f'<dl class="ips-info-grid">'
                f"<dt>Qty On Hand</dt><dd>{int(item.get('qty_on_hand') or 0)}</dd>"
                f"<dt>Reorder Point</dt><dd>{int(item.get('reorder_point') or 0)}</dd>"
                f"<dt>Unit Cost</dt><dd>{html.escape(fmt_currency(item.get('unit_cost')))}</dd>"
                f"<dt>Vendor</dt><dd>{html.escape(str(item.get('vendor') or '—'))}</dd>"
                f"</dl>",
                unsafe_allow_html=True,
            )
        iid = str(item.get("id") or "")
        if not is_demo_id(iid):
            with st.expander("Edit item", expanded=False):
                ic1, ic2 = st.columns(2)
                with ic1:
                    st.text_input("SKU", value=str(item.get("sku") or ""), key=f"inv_edit_sku_{iid}")
                    st.text_input("Name", value=str(item.get("name") or ""), key=f"inv_edit_name_{iid}")
                    st.selectbox("Category", lookup_options("inventory_categories"), key=f"inv_edit_cat_{iid}")
                    st.selectbox("Status", lookup_options("inventory_statuses"), key=f"inv_edit_status_{iid}")
                with ic2:
                    st.text_input("Location", value=str(item.get("location") or ""), key=f"inv_edit_loc_{iid}")
                    st.number_input("Qty on hand", value=int(item.get("qty_on_hand") or 0), key=f"inv_edit_qty_{iid}")
                    st.number_input("Unit cost", value=float(item.get("unit_cost") or 0), key=f"inv_edit_cost_{iid}")
                if st.button("Save item", key=f"inv_save_{iid}", type="primary"):
                    ok, msg = persist_inventory(
                        {
                            "sku": st.session_state.get(f"inv_edit_sku_{iid}"),
                            "name": st.session_state.get(f"inv_edit_name_{iid}"),
                            "category": st.session_state.get(f"inv_edit_cat_{iid}"),
                            "status": st.session_state.get(f"inv_edit_status_{iid}"),
                            "location": st.session_state.get(f"inv_edit_loc_{iid}"),
                            "qty_on_hand": st.session_state.get(f"inv_edit_qty_{iid}"),
                            "unit_cost": st.session_state.get(f"inv_edit_cost_{iid}"),
                        },
                        row_id=iid,
                    )
                    if apply_persist_feedback(ok, msg):
                        st.rerun()

    render_record_detail_dialog(
        f"{title} — Inventory Details",
        module_name="inventory",
        session_select_key=_SEL,
        tabs_fn=_tabs,
        body_fn=_body,
    )


def render() -> None:
    try:
        from app.pages.modules._access import begin_module
    except ImportError:
        from pages.modules._access import begin_module  # type: ignore
    if not begin_module("inventory"):
        return
    rows = load_inventory()
    categories = sorted({str(r.get("category") or "") for r in rows if r.get("category")})
    locations = sorted({str(r.get("location") or "") for r in rows if r.get("location")})

    act_l, act_r = st.columns([3, 1])
    with act_l:
        render_page_header("Inventory", "Track stocked materials, supplies, and warehouse levels.")
    with act_r:
        st.button("Export", key="inv_export", use_container_width=True)
        if st.button("+ New Item", key="inv_new", type="primary", use_container_width=True):
            st.session_state["ips_inv_form"] = True

    if st.session_state.get("ips_inv_form"):
        with st.expander("New inventory item", expanded=True):
            st.text_input("SKU", key="inv_new_sku")
            st.text_input("Item name", key="inv_new_name")
            st.selectbox("Category", lookup_options("inventory_categories"), key="inv_new_cat")
            st.selectbox("Status", lookup_options("inventory_statuses"), key="inv_new_status")
            if st.button("Save item", key="inv_save_new", type="primary"):
                ok, msg = persist_inventory(
                    {
                        "sku": st.session_state.get("inv_new_sku"),
                        "name": st.session_state.get("inv_new_name"),
                        "category": st.session_state.get("inv_new_cat"),
                        "status": st.session_state.get("inv_new_status"),
                    }
                )
                if apply_persist_feedback(ok, msg, clear_keys=("ips_inv_form",)):
                    st.rerun()

    def _filters() -> None:
        c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1, 0.7])
        with c1:
            st.text_input("Search", placeholder="Search inventory…", key="inv_search", label_visibility="collapsed")
        with c2:
            st.selectbox("Category", ["All Categories", *categories], key="inv_cat", label_visibility="collapsed")
        with c3:
            st.selectbox("Location", ["All Locations", *locations], key="inv_loc", label_visibility="collapsed")
        with c4:
            st.selectbox(
                "Status",
                ["All Statuses", *lookup_options("inventory_statuses")],
                key="inv_status",
                label_visibility="collapsed",
            )
        with c5:
            if st.button("Clear", key="inv_clear", use_container_width=True):
                for k in ("inv_search",):
                    st.session_state[k] = ""
                st.session_state["inv_cat"] = "All Categories"
                st.session_state["inv_loc"] = "All Locations"
                st.session_state["inv_status"] = "All Statuses"
                st.rerun()

    layout_filter_bar(_filters)

    filtered = _filter_rows(
        rows,
        q=str(st.session_state.get("inv_search") or "").strip(),
        category=str(st.session_state.get("inv_cat") or "All Categories"),
        location=str(st.session_state.get("inv_loc") or "All Locations"),
        status=str(st.session_state.get("inv_status") or "All Statuses"),
    )

    selected_id = str(st.session_state.get(_SEL) or "")
    if selected_id and not any(str(r.get("id")) == selected_id for r in filtered):
        st.session_state.pop(_SEL, None)
        selected_id = ""

    def _cell(field: str, row: dict) -> str:
        if field == "status":
            return status_pill_html(str(row.get("status") or ""))
        if field == "sku":
            return f'<span style="color:#2563eb;font-weight:600">{html.escape(str(row.get("sku") or ""))}</span>'
        if field == "unit_cost":
            return html.escape(fmt_currency(row.get("unit_cost")))
        return html.escape(str(row.get(field) or "—"))

    def _plain_cell(field: str, row: dict) -> str:
        if field == "unit_cost":
            return fmt_currency(row.get("unit_cost"))
        return str(row.get(field) or "—")

    sel = render_clickable_table(
        filtered,
        [
            ("sku", "SKU"),
            ("name", "ITEM NAME"),
            ("category", "CATEGORY"),
            ("location", "LOCATION"),
            ("department", "DEPARTMENT"),
            ("status", "STATUS"),
            ("qty_on_hand", "QTY"),
            ("unit_cost", "UNIT COST"),
        ],
        "inventory_list",
        row_id_key="id",
        session_select_key=_SEL,
        selected_id=selected_id or None,
        plain_cell=_plain_cell,
    )

    if sel:
        item = next((r for r in filtered if str(r.get("id")) == sel), None)
        if item:
            _render_detail(item)
