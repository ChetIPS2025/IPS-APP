"""Estimates list view — table, filters, and inline detail panel."""

from __future__ import annotations

import html
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import pandas as pd
import streamlit as st

from auth import current_role
from db import fetch_table, fetch_table_admin, update_rows_admin

try:
    from app.ui.estimates_components import (
        date_range_button_label,
        donut_chart_html,
        estimate_status_badge_html,
        inject_estimates_page_styles,
        meta_block_html,
        render_estimates_header_left_html,
        summary_card_html,
    )
    from app.ui.page_shell import render_card
except ImportError:
    from ui.estimates_components import (  # type: ignore
        date_range_button_label,
        donut_chart_html,
        estimate_status_badge_html,
        inject_estimates_page_styles,
        meta_block_html,
        render_estimates_header_left_html,
        summary_card_html,
    )
    from ui.page_shell import render_card  # type: ignore

try:
    from table_actions import IPS_PENDING_DELETE, TABLE_KEY_ESTIMATES
except ImportError:
    from app.table_actions import IPS_PENDING_DELETE, TABLE_KEY_ESTIMATES  # type: ignore

try:
    from services.delete_safety import delete_estimate_unlink_first
    from services.job_from_estimate import (
        create_job_from_estimate,
        estimate_status_allows_job_creation,
    )
except ImportError:
    from app.services.delete_safety import delete_estimate_unlink_first  # type: ignore
    from app.services.job_from_estimate import (  # type: ignore
        create_job_from_estimate,
        estimate_status_allows_job_creation,
    )

try:
    from ui import IPS_NAV_PENDING_KEY
except ImportError:
    from app.ui import IPS_NAV_PENDING_KEY  # type: ignore

from app.utils.formatters import job_display_label

_EST_LIST_SORT_COLS = (
    "quote_number",
    "estimate_description",
    "customer_name",
    "estimate_date",
    "expiration_date",
    "proposal_total",
    "status",
    "prepared_by_name",
)


def _safe_str(val: Any) -> str:
    if val is None:
        return ""
    try:
        if pd.isna(val):
            return ""
    except Exception:
        pass
    return str(val).strip()


def _parse_date_cell(val: Any) -> date | None:
    s = _safe_str(val)
    if not s:
        return None
    try:
        if "T" in s:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
        return date.fromisoformat(s[:10])
    except Exception:
        return None


def _fmt_date(val: Any) -> str:
    d = _parse_date_cell(val)
    return d.strftime("%b %d, %Y") if d else "-"


@st.cache_data(ttl=120, show_spinner=False)
def _fetch_customers_name_map_cached(_admin: bool) -> dict[str, str]:
    try:
        if _admin:
            rows = fetch_table_admin(
                "customers",
                columns="id,customer_name",
                limit=5000,
                order_by="customer_name",
            )
        else:
            rows = fetch_table(
                "customers",
                columns="id,customer_name",
                limit=5000,
                order_by="customer_name",
            )
    except Exception:
        return {}
    out: dict[str, str] = {}
    for r in rows:
        cid = _safe_str(r.get("id"))
        if cid:
            out[cid] = _safe_str(r.get("customer_name")) or cid
    return out


def _estimate_json_dict(row: dict[str, Any]) -> dict[str, Any]:
    ej = row.get("estimate_json")
    return ej if isinstance(ej, dict) else {}


def _created_by_label(row: dict[str, Any]) -> str:
    name = _safe_str(row.get("prepared_by_name"))
    if name:
        return name
    ej = _estimate_json_dict(row)
    return _safe_str(ej.get("prepared_by_name")) or _safe_str(row.get("prepared_by_id")) or "-"


def _estimate_date_value(row: dict[str, Any]) -> Any:
    for key in ("estimate_date", "created_at", "updated_at"):
        if key in row and _safe_str(row.get(key)):
            return row.get(key)
    ej = _estimate_json_dict(row)
    return ej.get("estimate_date") or ej.get("created_at")


def _expiration_date_value(row: dict[str, Any]) -> Any:
    for key in ("expiration_date", "valid_until", "quote_expiration"):
        if key in row and _safe_str(row.get(key)):
            return row.get(key)
    ej = _estimate_json_dict(row)
    return ej.get("expiration_date") or ej.get("valid_until")


def _project_title(row: dict[str, Any]) -> str:
    desc = _safe_str(row.get("estimate_description"))
    if desc:
        return desc.splitlines()[0][:80]
    ej = _estimate_json_dict(row)
    for k in ("estimate_description", "job", "job_name"):
        v = _safe_str(ej.get(k))
        if v:
            return v.splitlines()[0][:80]
    scope = _safe_str(row.get("scope_of_work"))
    if scope:
        return scope.splitlines()[0][:60] + ("..." if len(scope) > 60 else "")
    return "-"


def _project_subtitle(row: dict[str, Any]) -> str:
    ej = _estimate_json_dict(row)
    parts: list[str] = []
    pt = _safe_str(ej.get("project_type") or row.get("project_type"))
    if pt:
        parts.append(pt)
    po = _safe_str(row.get("po_number"))
    if po:
        parts.append(f"PO {po}")
    return " · ".join(parts) if parts else ""


def _clear_est_list_filters() -> None:
    for k in (
        "est_list_search",
        "est_list_status_f",
        "est_list_customer_f",
        "est_list_created_f",
        "est_list_date_from",
        "est_list_date_to",
    ):
        st.session_state.pop(k, None)


def _sort_dataframe(df: pd.DataFrame, col: str, asc: bool) -> pd.DataFrame:
    if df.empty or col not in df.columns:
        return df
    try:
        return df.sort_values(by=col, ascending=asc, kind="mergesort")
    except Exception:
        return df


def _th(label: str, col: str, *, sort_col: str, sort_asc: bool) -> None:
    arrow = ""
    if sort_col == col:
        arrow = " &#9650;" if sort_asc else " &#9660;"
    st.markdown(
        f'<p class="ips-est-th">{html.escape(label)}'
        f'<span class="ips-est-th-sort">&#8693;{arrow}</span></p>',
        unsafe_allow_html=True,
    )


def _compute_breakdown_for_row(
    row: dict[str, Any],
    *,
    money_fn: Any,
) -> dict[str, float]:
    ej = _estimate_json_dict(row)
    labor = materials = equipment = other = 0.0
    try:
        from app.estimate.calculations import compute_totals
        from app.services.estimate_materials_catalog import cached_estimate_materials_catalog_rows
        from app.estimate.equipment import load_estimate_equipment_from_assets
        from db import fetch_table as _ft

        est = dict(ej)
        est.setdefault("materials", ej.get("materials") or [])
        est.setdefault("labor", ej.get("labor") or [])
        est.setdefault("equipment", ej.get("equipment") or [])
        est.setdefault("controls", ej.get("controls") or {})
        est.setdefault("travel", ej.get("travel") or {})
        mats = cached_estimate_materials_catalog_rows()
        labor_rates = _ft("labor_rates", limit=1000, order_by="classification")
        equip = load_estimate_equipment_from_assets()
        t = compute_totals(est, mats, labor_rates, equip)
        labor = float(t.get("labor_total") or 0)
        materials = float(t.get("material_sell_basis") or 0)
        equipment = float(t.get("equipment_total") or 0)
        other = float(t.get("travel_total") or 0) + float(t.get("overhead_total") or 0)
    except Exception:
        pt = row.get("proposal_total")
        try:
            total = float(pt or 0)
        except Exception:
            total = 0.0
        if total > 0:
            materials = total * 0.5
            labor = total * 0.35
            equipment = total * 0.1
            other = total - materials - labor - equipment
    return {"labor": labor, "materials": materials, "equipment": equipment, "other": max(0.0, other)}


def _line_items_preview_rows(row: dict[str, Any], *, limit: int = 8) -> list[dict[str, str]]:
    ej = _estimate_json_dict(row)
    rows_out: list[dict[str, str]] = []

    def _add(item: str, desc: str, qty: Any, unit: str, price: Any, total: Any) -> None:
        rows_out.append(
            {
                "Item": item,
                "Description": desc,
                "Qty": str(qty),
                "Unit": unit,
                "Unit Price": str(price),
                "Total": str(total),
            }
        )

    for m in ej.get("materials") or []:
        if not isinstance(m, dict):
            continue
        qty = m.get("qty", 0)
        _add(
            _safe_str(m.get("item")) or "Material",
            _safe_str(m.get("description")) or "-",
            qty,
            _safe_str(m.get("unit")) or "ea",
            m.get("unit_price", "-"),
            m.get("line_total", "-"),
        )
        if len(rows_out) >= limit:
            return rows_out
    for lb in ej.get("labor") or []:
        if not isinstance(lb, dict):
            continue
        _add(
            _safe_str(lb.get("classification")) or "Labor",
            "Labor",
            lb.get("days", 0),
            "days",
            "-",
            "-",
        )
        if len(rows_out) >= limit:
            return rows_out
    for eq in ej.get("equipment") or []:
        if not isinstance(eq, dict):
            continue
        _add(
            _safe_str(eq.get("equipment_item")) or "Equipment",
            _safe_str(eq.get("basis")) or "-",
            eq.get("qty", 0),
            _safe_str(eq.get("basis")) or "ea",
            "-",
            "-",
        )
        if len(rows_out) >= limit:
            return rows_out
    return rows_out


def render_estimates_list_page(
    *,
    rows: list[dict[str, Any]],
    df: pd.DataFrame,
    can_edit: bool,
    admin_read: bool,
    money_display: Any,
    money_csv: Any,
    estimate_description_display: Any,
    row_estimate_id: Any,
    linked_job_display_cell: Any,
    linked_job_id_for_row: Any,
    series_truthy_job_received: Any,
    job_by_id: dict[str, dict[str, Any]],
    job_by_estimate_id: dict[str, dict[str, Any]],
    eid_to_customer: dict[str, str],
    on_new_estimate: Any,
    on_import: Any,
    on_open_editor: Any,
    site_line_for_estimate: Any,
) -> None:
    inject_estimates_page_styles()
    st.markdown('<span class="ips-estimates-page" aria-hidden="true"></span>', unsafe_allow_html=True)

    customer_map = _fetch_customers_name_map_cached(admin_read)

    with st.container(border=True):
        st.markdown('<span class="ips-est-header-anchor"></span>', unsafe_allow_html=True)
        hc1, hc2 = st.columns([4.2, 2.35], gap="medium")
        with hc1:
            render_estimates_header_left_html()
        with hc2:
            st.markdown('<span class="ips-est-hdr-actions" aria-hidden="true"></span>', unsafe_allow_html=True)
            st.markdown('<div style="height:0.15rem"></div>', unsafe_allow_html=True)
            hb_exp, hb_new = st.columns(2, gap="small")
            with hb_exp:
                export_slot = st.empty()
            with hb_new:
                if st.button("+ New Estimate", type="primary", use_container_width=True, key="est_hdr_new"):
                    on_new_estimate()
                    return

    # Filters
    with st.container(border=True):
        st.markdown('<span class="ips-est-filter-anchor"></span>', unsafe_allow_html=True)
        f1, f2, f3, f4, f5, f6 = st.columns([2.2, 1.1, 1.2, 1.2, 1.5, 0.75], gap="small")
        statuses = ["All Statuses"]
        customers = ["All Customers"]
        creators = ["All Created By"]
        if not df.empty:
            if "status" in df.columns:
                statuses += sorted(df["status"].dropna().astype(str).unique().tolist())
            cust_names = sorted({customer_map.get(eid_to_customer.get(str(r.get("id") or ""), ""), "") for r in rows if customer_map.get(eid_to_customer.get(str(r.get("id") or ""), ""))})
            customers += cust_names
            creators += sorted({_created_by_label(r) for r in rows if _created_by_label(r) != "-"})

        with f1:
            st.text_input(
                "Search",
                placeholder="🔍  Search estimates...",
                key="est_list_search",
                label_visibility="collapsed",
            )
        with f2:
            st.selectbox("Status", statuses, key="est_list_status_f", label_visibility="collapsed")
        with f3:
            st.selectbox("Customer", customers, key="est_list_customer_f", label_visibility="collapsed")
        with f4:
            st.selectbox("Created By", creators, key="est_list_created_f", label_visibility="collapsed")
        with f5:
            st.markdown('<span class="ips-est-date-pop" aria-hidden="true"></span>', unsafe_allow_html=True)
            dr_lbl = date_range_button_label(
                st.session_state.get("est_list_date_from"),
                st.session_state.get("est_list_date_to"),
            )
            with st.popover(f"📅 {dr_lbl}", use_container_width=True):
                st.date_input("From", key="est_list_date_from", value=None)
                st.date_input("To", key="est_list_date_to", value=None)
                if st.button("Clear dates", key="est_list_clear_dates", use_container_width=True):
                    st.session_state.pop("est_list_date_from", None)
                    st.session_state.pop("est_list_date_to", None)
                    st.rerun()
        with f6:
            st.markdown('<div style="height:1.55rem"></div>', unsafe_allow_html=True)
            if st.button("Clear Filters", key="est_list_clear_filters", use_container_width=True):
                _clear_est_list_filters()
                st.rerun()

    filtered = df.copy() if not df.empty else df
    if not filtered.empty:
        search = _safe_str(st.session_state.get("est_list_search"))
        if search:
            mask = filtered.astype(str).apply(
                lambda col: col.str.lower().str.contains(search.lower(), na=False)
            )
            filtered = filtered[mask.any(axis=1)]

        st_f = st.session_state.get("est_list_status_f", "All Statuses")
        if st_f and st_f != "All Statuses" and "status" in filtered.columns:
            filtered = filtered[filtered["status"].astype(str) == st_f]

        cu_f = st.session_state.get("est_list_customer_f", "All Customers")
        if cu_f and cu_f != "All Customers" and "id" in filtered.columns:
            ids = [
                str(r["id"])
                for r in rows
                if customer_map.get(eid_to_customer.get(str(r.get("id") or ""), "")) == cu_f
            ]
            filtered = filtered[filtered["id"].astype(str).isin(ids)]

        cr_f = st.session_state.get("est_list_created_f", "All Created By")
        if cr_f and cr_f != "All Created By":
            ids = [str(r["id"]) for r in rows if _created_by_label(r) == cr_f]
            filtered = filtered[filtered["id"].astype(str).isin(ids)]

        d_from = st.session_state.get("est_list_date_from")
        d_to = st.session_state.get("est_list_date_to")
        if d_from is not None or d_to is not None:
            keep_ids: list[str] = []
            for r in rows:
                eid = str(r.get("id") or "")
                if not eid or eid not in set(filtered["id"].astype(str).tolist()):
                    continue
                ed = _parse_date_cell(_estimate_date_value(r))
                if ed is None:
                    continue
                if d_from and ed < d_from:
                    continue
                if d_to and ed > d_to:
                    continue
                keep_ids.append(eid)
            filtered = filtered[filtered["id"].astype(str).isin(keep_ids)]

        filtered = filtered.copy()
        filtered["customer_name"] = filtered["id"].astype(str).map(
            lambda i: customer_map.get(eid_to_customer.get(i, ""), "")
        )
        filtered["estimate_date"] = filtered["id"].astype(str).map(
            lambda i: next((_estimate_date_value(r) for r in rows if str(r.get("id")) == i), "")
        )
        filtered["expiration_date"] = filtered["id"].astype(str).map(
            lambda i: next((_expiration_date_value(r) for r in rows if str(r.get("id")) == i), "")
        )
        filtered["prepared_by_name"] = filtered["id"].astype(str).map(
            lambda i: next((_created_by_label(r) for r in rows if str(r.get("id")) == i), "-")
        )

    sort_col = str(st.session_state.get("est_list_sort_col") or "updated_at")
    sort_asc = bool(st.session_state.get("est_list_sort_asc", False))
    if sort_col in filtered.columns:
        filtered = _sort_dataframe(filtered, sort_col, sort_asc)

    if not filtered.empty and "id" in filtered.columns and "est_list_selected_id" not in st.session_state:
        first_eid = row_estimate_id(filtered.iloc[0])
        if first_eid:
            st.session_state["est_list_selected_id"] = first_eid

    selected_id = _safe_str(st.session_state.get("est_list_selected_id"))
    if selected_id and not filtered.empty and selected_id not in set(filtered["id"].astype(str)):
        st.session_state.pop("est_list_selected_id", None)
        selected_id = ""

    if not filtered.empty and "id" in filtered.columns:
        df_export = filtered.copy()
        for mc in ("proposal_total", "final_bid"):
            if mc in df_export.columns:
                df_export[mc] = df_export[mc].map(money_csv)
        csv_bytes = df_export.to_csv(index=False).encode("utf-8")
        with export_slot:
            st.download_button(
                "⬇ Export",
                data=csv_bytes,
                file_name="estimates_export.csv",
                mime="text/csv",
                key="est_hdr_export_dl",
                use_container_width=True,
            )

    if filtered.empty:
        try:
            from app.ui.components.empty_states import render_empty_state
        except ImportError:
            from ui.components.empty_states import render_empty_state  # type: ignore
        if render_empty_state(
            "No estimates found",
            "Create a new estimate or adjust filters to see results.",
            icon="📄",
            action_label="New estimate",
            action_key="est_list_empty_new_v2",
        ):
            on_new_estimate()
        return

    # Table
    with st.container(border=True):
        st.markdown('<span class="ips-est-table-anchor"></span>', unsafe_allow_html=True)
        weights = [1.0, 2.0, 1.3, 1.0, 1.0, 0.9, 0.85, 1.0, 0.75]
        head = st.columns(weights)
        sort_pairs = [
            ("ESTIMATE #", "quote_number"),
            ("PROJECT / DESCRIPTION", "estimate_description"),
            ("CUSTOMER", "customer_name"),
            ("ESTIMATE DATE", "estimate_date"),
            ("EXPIRATION DATE", "expiration_date"),
            ("TOTAL", "proposal_total"),
            ("STATUS", "status"),
            ("CREATED BY", "prepared_by_name"),
        ]
        for col, (lbl, scol) in zip(head, sort_pairs):
            with col:
                st.markdown('<span class="ips-est-sort-anchor"></span>', unsafe_allow_html=True)
                if st.button(f"{lbl} ↕", key=f"est_sort_{scol}", use_container_width=True):
                    if st.session_state.get("est_list_sort_col") == scol:
                        st.session_state["est_list_sort_asc"] = not bool(
                            st.session_state.get("est_list_sort_asc", True)
                        )
                    else:
                        st.session_state["est_list_sort_col"] = scol
                        st.session_state["est_list_sort_asc"] = True
                    st.rerun()
        with head[-1]:
            st.markdown('<p class="ips-est-th" style="margin:0;padding:0.35rem 0;">ACTIONS</p>', unsafe_allow_html=True)

        row_lookup = {str(r.get("id")): r for r in rows if r.get("id")}

        for _, est_row in filtered.iterrows():
            eid = row_estimate_id(est_row)
            if not eid:
                continue
            full_row = row_lookup.get(eid, est_row.to_dict())
            is_sel = eid == selected_id

            qn = _safe_str(est_row.get("quote_number")) or "-"
            title = _project_title(full_row if isinstance(full_row, dict) else {})
            subtitle = _project_subtitle(full_row if isinstance(full_row, dict) else {})
            cust = _safe_str(est_row.get("customer_name")) or customer_map.get(eid_to_customer.get(eid, ""), "-")
            total = money_display(est_row.get("proposal_total"))
            status_html = estimate_status_badge_html(est_row.get("status"))
            created = _safe_str(est_row.get("prepared_by_name")) or _created_by_label(
                full_row if isinstance(full_row, dict) else {}
            )
            est_date = _fmt_date(est_row.get("estimate_date"))
            exp_date = _fmt_date(est_row.get("expiration_date"))

            row_cls = "est-row selected" if is_sel else "est-row"
            sub_html = (
                f'<span class="est-cell-sub">{html.escape(subtitle)}</span>'
                if subtitle else ""
            )

            with st.container():
                st.markdown('<span class="est-row-wrap" aria-hidden="true"></span>', unsafe_allow_html=True)
                st.markdown(
                    f'<div class="{row_cls}">'
                    f'<span class="est-qnum" title="{html.escape(qn, quote=True)}">{html.escape(qn)}</span>'
                    f'<div class="est-cell-title-wrap">'
                    f'<div class="est-cell-title">{html.escape(title)}</div>{sub_html}'
                    f'</div>'
                    f'<span class="est-cell muted" title="{html.escape(cust, quote=True)}">{html.escape(cust)}</span>'
                    f'<span class="est-cell muted">{html.escape(est_date)}</span>'
                    f'<span class="est-cell muted">{html.escape(exp_date)}</span>'
                    f'<span class="est-cell bold">{html.escape(total)}</span>'
                    f'<span class="est-cell-stat">{status_html}</span>'
                    f'<span class="est-cell muted">{html.escape(created)}</span>'
                    f'<span class="est-act-slot"></span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                st.markdown('<span class="est-row-select-btn" aria-hidden="true"></span>', unsafe_allow_html=True)
                if st.button(
                    "\u200b",
                    key=f"est_pick_{eid}",
                    use_container_width=True,
                    help=f"Select estimate {qn}",
                ):
                    st.session_state["est_list_selected_id"] = eid
                    st.session_state.pop("est_list_detail_collapsed", None)
                    st.rerun()

                st.markdown('<span class="est-actcol" aria-hidden="true"></span>', unsafe_allow_html=True)
                a1, a2 = st.columns(2, gap="small")
                with a1:
                    if st.button("👁", key=f"est_view_{eid}", help="View estimate", use_container_width=True):
                        st.session_state["est_list_selected_id"] = eid
                        st.session_state.pop("est_list_detail_collapsed", None)
                        st.rerun()
                with a2:
                    with st.popover("⋯", use_container_width=True):
                        if st.button("Open editor", key=f"est_more_edit_{eid}", use_container_width=True):
                            on_open_editor(eid)
                        if st.button("Import quotes", key=f"est_more_imp_{eid}", use_container_width=True):
                            on_import()
                        if can_edit and st.button(
                            "Delete",
                            key=f"est_more_del_{eid}",
                            use_container_width=True,
                        ):
                            st.session_state[IPS_PENDING_DELETE] = {TABLE_KEY_ESTIMATES: [eid]}
                            st.rerun()

    # Delete confirmation
    pend = st.session_state.get(IPS_PENDING_DELETE) or {}
    if pend.get(TABLE_KEY_ESTIMATES):
        ids = pend[TABLE_KEY_ESTIMATES]
        st.warning(f"Delete {len(ids)} estimate(s)? This cannot be undone.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Confirm delete", type="primary", key="est_confirm_del"):
                for eid in ids:
                    try:
                        delete_estimate_unlink_first(str(eid), admin_read=admin_read)
                    except Exception as exc:
                        st.error(f"Could not delete {eid}: {exc}")
                pend.pop(TABLE_KEY_ESTIMATES, None)
                st.session_state.pop("est_list_selected_id", None)
                st.success("Delete completed where permitted.")
                st.rerun()
        with c2:
            if st.button("Cancel", key="est_cancel_del"):
                pend.pop(TABLE_KEY_ESTIMATES, None)
                st.rerun()

    if selected_id and not st.session_state.get("est_list_detail_collapsed"):
        full = row_lookup.get(selected_id)
        if full:
            _render_estimate_detail_panel(
                full,
                can_edit=can_edit,
                admin_read=admin_read,
                customer_map=customer_map,
                eid_to_customer=eid_to_customer,
                money_display=money_display,
                linked_job_display_cell=linked_job_display_cell,
                linked_job_id_for_row=linked_job_id_for_row,
                series_truthy_job_received=series_truthy_job_received,
                job_by_id=job_by_id,
                job_by_estimate_id=job_by_estimate_id,
                on_open_editor=on_open_editor,
                on_import=on_import,
            )


def _render_estimate_detail_panel(
    row: dict[str, Any],
    *,
    can_edit: bool,
    admin_read: bool,
    customer_map: dict[str, str],
    eid_to_customer: dict[str, str],
    money_display: Any,
    linked_job_display_cell: Any,
    linked_job_id_for_row: Any,
    series_truthy_job_received: Any,
    job_by_id: dict[str, dict[str, Any]],
    job_by_estimate_id: dict[str, dict[str, Any]],
    on_open_editor: Any,
    on_import: Any,
) -> None:
    eid = str(row.get("id") or "")
    qn = _safe_str(row.get("quote_number")) or "-"
    status = row.get("status")
    title = _project_title(row)
    cust_id = eid_to_customer.get(eid, "")
    cust = customer_map.get(cust_id, "-")

    with st.container(border=True):
        st.markdown('<span class="ips-est-detail-anchor"></span>', unsafe_allow_html=True)
        dl, dm, dr = st.columns([2.5, 2.8, 2.2], gap="medium")
        with dl:
            st.markdown(
                f'<div class="ips-est-detail-id-row">'
                f'<span class="ips-est-detail-title">{html.escape(qn)}</span> '
                f"{estimate_status_badge_html(status)}</div>"
                f'<p class="ips-est-detail-project">{html.escape(title)}</p>'
                f'<p class="ips-est-detail-customer">{html.escape(cust)}</p>',
                unsafe_allow_html=True,
            )
        with dm:
            m1, m2, m3 = st.columns(3)
            with m1:
                st.markdown(meta_block_html("Estimate Date", _fmt_date(_estimate_date_value(row))), unsafe_allow_html=True)
            with m2:
                st.markdown(meta_block_html("Expiration Date", _fmt_date(_expiration_date_value(row))), unsafe_allow_html=True)
            with m3:
                st.markdown(meta_block_html("Created By", _created_by_label(row)), unsafe_allow_html=True)
        with dr:
            b1, b2, b3, b4 = st.columns([1.1, 1.5, 0.7, 0.5], gap="small")
            with b1:
                if st.button("Edit", key=f"est_det_edit_{eid}", type="secondary", use_container_width=True):
                    on_open_editor(eid)
            with b2:
                if st.button("Send Estimate", key=f"est_det_send_{eid}", type="primary", use_container_width=True):
                    on_open_editor(eid)
            with b3:
                with st.popover("⋯", use_container_width=True):
                    _render_detail_more_menu(
                        row,
                        eid=eid,
                        can_edit=can_edit,
                        admin_read=admin_read,
                        linked_job_id_for_row=linked_job_id_for_row,
                        series_truthy_job_received=series_truthy_job_received,
                        job_by_id=job_by_id,
                        eid_to_customer=eid_to_customer,
                        on_import=on_import,
                    )
            with b4:
                if st.button("▲", key=f"est_det_collapse_{eid}", help="Collapse", use_container_width=True):
                    st.session_state["est_list_detail_collapsed"] = True
                    st.rerun()

        st.markdown('<div style="border-bottom:1px solid #f1f5f9;margin:0.5rem 0 0.65rem"></div>', unsafe_allow_html=True)
        tabs = st.tabs(
            [
                "Overview",
                "Line Items",
                "Labor",
                "Materials",
                "Equipment",
                "Attachments",
                "Notes",
                "Activity",
            ]
        )
        ej = _estimate_json_dict(row)
        breakdown = _compute_breakdown_for_row(row, money_fn=money_display)
        pt = money_display(row.get("proposal_total"))
        linked = linked_job_display_cell(pd.Series(row)) if callable(linked_job_display_cell) else ""

        with tabs[0]:
            _render_overview_tab(row, ej=ej, breakdown=breakdown, pt=pt, linked=linked, cust=cust)
        with tabs[1]:
            _render_line_items_tab(ej, full=True)
        with tabs[2]:
            _render_labor_tab(ej)
        with tabs[3]:
            _render_materials_tab(ej)
        with tabs[4]:
            _render_equipment_tab(ej)
        with tabs[5]:
            _render_attachments_tab(eid, admin_read=admin_read)
        with tabs[6]:
            _render_notes_tab(row, ej)
        with tabs[7]:
            _render_activity_tab(row)


def _render_detail_more_menu(
    row: dict[str, Any],
    *,
    eid: str,
    can_edit: bool,
    admin_read: bool,
    linked_job_id_for_row: Any,
    series_truthy_job_received: Any,
    job_by_id: dict[str, dict[str, Any]],
    eid_to_customer: dict[str, str],
    on_import: Any,
) -> None:
    est_series = pd.Series(row)
    linked_id = linked_job_id_for_row(est_series) if callable(linked_job_id_for_row) else None
    cust_id = eid_to_customer.get(eid, "")
    row_status = str(row.get("status") or "").strip().lower()

    if linked_id and str(linked_id) in job_by_id:
        if st.button("Open linked job", key=f"est_more_job_{eid}", use_container_width=True):
            st.session_state[IPS_NAV_PENDING_KEY] = "Job Database"
            st.session_state["job_view_mode"] = "edit"
            st.session_state["selected_job_id"] = str(linked_id)
            st.session_state["job_mode"] = "edit"
            st.session_state["job_edit_id"] = str(linked_id)
            st.rerun()
    elif can_edit:
        if st.button("Create job from estimate", key=f"est_more_cjob_{eid}", use_container_width=True):
            res = create_job_from_estimate(str(eid))
            if res.ok and res.job:
                st.success(res.message)
                jid = str(res.job.get("id") or "")
                if jid:
                    st.session_state[IPS_NAV_PENDING_KEY] = "Job Database"
                    st.session_state["selected_job_id"] = jid
                    st.session_state["job_mode"] = "edit"
                    st.session_state["job_edit_id"] = jid
                st.rerun()
            elif res.message:
                st.error(res.message)

    if can_edit and row_status in ("draft", "submitted"):
        if st.button("Approve estimate", key=f"est_more_appr_{eid}", use_container_width=True):
            try:
                update_rows_admin("estimates", {"status": "approved"}, {"id": eid})
                st.success("Estimate approved.")
                st.rerun()
            except Exception as exc:
                st.error(f"Could not approve: {exc}")

    if can_edit and not linked_id and not series_truthy_job_received(est_series):
        if estimate_status_allows_job_creation(row_status) and cust_id:
            if st.button("Job received", key=f"est_more_jrecv_{eid}", use_container_width=True):
                res = create_job_from_estimate(str(eid), mark_job_received=True)
                if res.ok:
                    st.success(res.message)
                    st.rerun()
                elif res.message:
                    st.error(res.message)

    if st.button("Import quotes", key=f"est_det_more_imp_{eid}", use_container_width=True):
        on_import()


def _render_overview_tab(
    row: dict[str, Any],
    *,
    ej: dict[str, Any],
    breakdown: dict[str, float],
    pt: str,
    linked: str,
    cust: str,
) -> None:
    controls = ej.get("controls") if isinstance(ej.get("controls"), dict) else {}
    try:
        tax_pct = float(controls.get("sales_tax_pct", 0) or 0)
    except (TypeError, ValueError):
        tax_pct = 0.0
    tax_label = f"Tax ({tax_pct:g}%)" if tax_pct else "Tax"
    c1, c2, c3 = st.columns(3, gap="small")
    with c1:
        st.markdown(
            summary_card_html(
                title="Estimate Summary",
                rows=[
                    ("Description", _project_title(row)),
                    ("Project Type", _safe_str(ej.get("project_type")) or "-"),
                    ("Customer", cust),
                    ("Status", str(row.get("status") or "-").replace("_", " ").title()),
                    ("Linked Job", linked or "-"),
                ],
            ),
            unsafe_allow_html=True,
        )
    with c2:
        sub = breakdown["labor"] + breakdown["materials"] + breakdown["equipment"] + breakdown["other"]
        sub_s = f"${sub:,.2f}" if sub else pt
        tax_amt_s = f"${sub * tax_pct / 100:,.2f}" if sub and tax_pct else "-"
        st.markdown(
            summary_card_html(
                title="Financial Summary",
                rows=[
                    ("Subtotal", sub_s),
                    (tax_label, tax_amt_s),
                    ("Total", pt),
                    ("Markup", f"{_safe_str(controls.get('material_markup_pct')) or '0'}%"),
                ],
                grand_row=("Grand Total", pt),
            ),
            unsafe_allow_html=True,
        )
    with c3:
        segments = [
            ("Labor", breakdown["labor"], "#2563eb"),
            ("Materials", breakdown["materials"], "#16a34a"),
            ("Equipment", breakdown["equipment"], "#d97706"),
            ("Other", breakdown["other"], "#ef4444"),
        ]
        st.markdown(
            f'<div class="ips-est-summary-card"><h4>Estimate Totals</h4>'
            f"{donut_chart_html(segments)}</div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="ips-est-line-items-head">'
        "<h4>Top Line Items</h4>"
        "<span>View All Line Items</span>"
        "</div>",
        unsafe_allow_html=True,
    )
    preview = _line_items_preview_rows(row)
    if preview:
        st.dataframe(pd.DataFrame(preview), use_container_width=True, hide_index=True)
    else:
        st.caption("No line items in saved estimate data.")


def _render_line_items_tab(ej: dict[str, Any], *, full: bool) -> None:
    rows = _line_items_preview_rows({"estimate_json": ej}, limit=500 if full else 8)
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.caption("No line items saved on this estimate.")


def _render_labor_tab(ej: dict[str, Any]) -> None:
    labor = [x for x in (ej.get("labor") or []) if isinstance(x, dict)]
    if labor:
        st.dataframe(pd.DataFrame(labor), use_container_width=True, hide_index=True)
    else:
        st.caption("No labor entries.")


def _render_materials_tab(ej: dict[str, Any]) -> None:
    mats = [x for x in (ej.get("materials") or []) if isinstance(x, dict)]
    if mats:
        st.dataframe(pd.DataFrame(mats), use_container_width=True, hide_index=True)
    else:
        st.caption("No materials on this estimate.")


def _render_equipment_tab(ej: dict[str, Any]) -> None:
    eq = [x for x in (ej.get("equipment") or []) if isinstance(x, dict)]
    if eq:
        st.dataframe(pd.DataFrame(eq), use_container_width=True, hide_index=True)
    else:
        st.caption("No equipment on this estimate.")


def _render_attachments_tab(eid: str, *, admin_read: bool) -> None:
    rows: list[dict[str, Any]] = []
    try:
        if admin_read:
            from db import fetch_by_match_admin as _fb
        else:
            from db import fetch_by_match as _fb  # type: ignore
        rows = list(_fb("attachments", {"estimate_id": eid}, limit=200) or [])
    except Exception:
        try:
            fn = fetch_table_admin if admin_read else fetch_table
            atts = fn("attachments", limit=500)
            rows = [a for a in atts if str(a.get("estimate_id") or "") == eid]
        except Exception:
            rows = []
    if rows:
        df = pd.DataFrame(
            [
                {
                    "File": a.get("file_name"),
                    "Category": a.get("category"),
                    "Type": a.get("file_type"),
                }
                for a in rows
            ]
        )
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.caption("No attachments. Add files in the estimate editor.")


def _render_notes_tab(row: dict[str, Any], ej: dict[str, Any]) -> None:
    notes = _safe_str(row.get("notes")) or _safe_str(ej.get("notes"))
    scope = _safe_str(row.get("scope_of_work")) or _safe_str(ej.get("scope_of_work"))
    if notes:
        st.text_area("Notes", value=notes, height=120, disabled=True, key=f"est_notes_ro_{row.get('id')}")
    elif scope:
        st.text_area("Scope / notes", value=scope[:4000], height=160, disabled=True, key=f"est_scope_ro_{row.get('id')}")
    else:
        st.caption("No notes on this estimate.")


def _render_activity_tab(row: dict[str, Any]) -> None:
    try:
        from app.ui.activity import render_activity_panel
    except ImportError:
        from ui.activity import render_activity_panel  # type: ignore
    render_activity_panel(
        title="Estimate activity",
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
        status=row.get("status"),
        created_by=_created_by_label(row),
        extra_lines=[("Quote #", _safe_str(row.get("quote_number")) or "-")],
    )
