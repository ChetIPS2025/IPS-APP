"""Inventory list — table, filters, and inline detail panel."""

from __future__ import annotations

import html
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable

import pandas as pd
import streamlit as st

try:
    from app.auth import current_profile
    from app.confirm_delete import open_destructive_confirmation
    from app.db import fetch_by_match_admin, fetch_table_admin, insert_row_admin, update_rows_admin
    from app.ui.catalog_inventory_display import sanitize_catalog_inventory_export_df
    from app.ui.inventory_components import (
        detail_stats_row_html,
        inject_inventory_page_styles,
        render_inventory_header_inner_html,
        stock_status_badge_html,
        summary_card_html,
        table_header_html,
        transactions_table_html,
        usage_line_chart_html,
    )
    from app.ui.streamlit_perf import fragment, inject_scroll_preserve, ips_app_rerun
except ImportError:
    from auth import current_profile  # type: ignore
    from confirm_delete import open_destructive_confirmation  # type: ignore
    from db import fetch_by_match_admin, fetch_table_admin, insert_row_admin, update_rows_admin  # type: ignore
    from ui.catalog_inventory_display import sanitize_catalog_inventory_export_df  # type: ignore
    from ui.inventory_components import (  # type: ignore
        detail_stats_row_html,
        inject_inventory_page_styles,
        render_inventory_header_inner_html,
        stock_status_badge_html,
        summary_card_html,
        table_header_html,
        transactions_table_html,
        usage_line_chart_html,
    )
    from ui.streamlit_perf import fragment, inject_scroll_preserve, ips_app_rerun  # type: ignore

_TABLE = "inventory_items"
_TXN = "inventory_transactions"
_DELETE_CONFIRM_PREFIX = "inventory_delete"

_INV_TABS = (
    "Overview",
    "Stock History",
    "Transactions",
    "Purchase Orders",
    "Vendors",
    "Notes",
    "Attachments",
)


def _unit(row: dict[str, Any]) -> str:
    return _safe_str(row.get("unit")) or "EA"


def _fmt_qty_unit(row: dict[str, Any], qty: float | object) -> str:
    q = _qty_num(qty)
    u = _unit(row)
    if q == int(q):
        return f"{int(q):,} {u}"
    return f"{q:g} {u}"


def _txn_type_label(txn_type: str) -> str:
    t = str(txn_type or "").strip().upper()
    return {
        "TO_JOB": "Issue",
        "SHOP": "Issue",
        "ADJUST": "Adjustment",
        "RECEIPT": "Receipt",
        "COUNT": "Count",
        "KIT_REPLACEMENT": "Issue",
    }.get(t, str(txn_type or "—").replace("_", " ").title())

_SEARCH_COLS = (
    "item_name",
    "sku",
    "qr_code_value",
    "category",
    "storage_location",
    "vendor",
    "notes",
)


def _safe_str(val: object) -> str:
    if val is None:
        return ""
    try:
        if pd.isna(val):
            return ""
    except Exception:
        pass
    s = str(val).strip()
    return "" if s.lower() == "nan" else s


def _fmt_date(val: object) -> str:
    if val is None or str(val).strip() == "":
        return "—"
    s = str(val).strip()
    try:
        if "T" in s:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).strftime("%b %d, %Y")
        return datetime.fromisoformat(s[:10]).strftime("%b %d, %Y")
    except Exception:
        return s[:10] if len(s) >= 10 else s


def _money(val: object) -> str:
    if val is None or str(val).strip() == "":
        return "—"
    try:
        f = float(val)
        return f"${f:,.2f}"
    except (TypeError, ValueError):
        return "—"


def _qty_num(val: object) -> float:
    try:
        return float(val or 0)
    except (TypeError, ValueError):
        return 0.0


def _item_number(row: dict[str, Any]) -> str:
    sku = _safe_str(row.get("sku"))
    if sku:
        return sku
    qr = _safe_str(row.get("qr_code_value"))
    if qr:
        return qr
    rid = _safe_str(row.get("id"))
    return f"INV-{rid[:8].upper()}" if rid else "—"


def _stock_status(row: dict[str, Any]) -> str:
    if not bool(row.get("is_active", True)):
        return "Discontinued"
    q = _qty_num(row.get("quantity_on_hand"))
    rp = _qty_num(row.get("reorder_point"))
    if q <= 0:
        return "Out of Stock"
    if rp > 0 and q <= rp:
        return "Low Stock"
    return "In Stock"


def _total_value(row: dict[str, Any]) -> float:
    q = _qty_num(row.get("quantity_on_hand"))
    try:
        uc = float(row.get("unit_cost") or 0)
    except (TypeError, ValueError):
        uc = 0.0
    return q * uc


def _filter_options(df: pd.DataFrame, col: str) -> list[str]:
    if df.empty or col not in df.columns:
        return []
    return sorted({_safe_str(v) for v in df[col].dropna().unique() if _safe_str(v)})


def _clear_filters() -> None:
    st.session_state["inv_f_search"] = ""
    st.session_state["inv_f_cat"] = "All Categories"
    st.session_state["inv_f_loc"] = "All Locations"
    st.session_state["inv_f_stock_status"] = "All Statuses"


def _apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    search = _safe_str(st.session_state.get("inv_f_search")).lower()
    cat = _safe_str(st.session_state.get("inv_f_cat"))
    loc = _safe_str(st.session_state.get("inv_f_loc"))
    stt = _safe_str(st.session_state.get("inv_f_stock_status"))

    if cat and cat != "All Categories" and "category" in out.columns:
        out = out[out["category"].astype(str).str.strip() == cat]
    if loc and loc != "All Locations" and "storage_location" in out.columns:
        out = out[out["storage_location"].astype(str).str.strip() == loc]
    if stt and stt != "All Statuses":
        out = out[out.apply(lambda r: _stock_status(r.to_dict()) == stt, axis=1)]
    if search:
        cols = [c for c in _SEARCH_COLS if c in out.columns]
        if cols:
            mask = out[cols].astype(str).apply(lambda col: col.str.lower().str.contains(search, na=False))
            out = out[mask.any(axis=1)]
    return out


def _row_lookup(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(r.get("id") or "").strip(): r for r in rows if str(r.get("id") or "").strip()}


@st.cache_data(ttl=60, show_spinner=False)
def _cached_item_transactions(item_id: str, data_version: int) -> list[dict]:
    try:
        rows = list(fetch_by_match_admin(_TXN, {"inventory_item_id": item_id}, limit=500) or [])
        rows.sort(key=lambda t: str(t.get("created_at") or ""))
        return rows
    except Exception:
        return []


def _invalidate_txn_cache() -> None:
    try:
        _cached_item_transactions.clear()
    except Exception:
        pass


def _txn_actor(t: dict) -> str:
    sn = _safe_str(t.get("scanned_by_name"))
    if sn:
        return sn
    cb = _safe_str(t.get("created_by"))
    if cb:
        return cb
    pid = _safe_str(t.get("profile_id"))
    return (pid[:12] + "…") if len(pid) > 12 else (pid or "—")


def _txn_reference(t: dict) -> str:
    jid = _safe_str(t.get("job_id"))
    if jid:
        return f"Job {jid[:8]}…"
    notes = _safe_str(t.get("notes"))
    return notes[:40] if notes else "—"


def _parse_ts(v: object) -> datetime | None:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def _usage_series(txns: list[dict], *, days: int = 28) -> tuple[list[float], float, float]:
    today = date.today()
    labels = [today - timedelta(days=(days - 1 - i)) for i in range(days)]
    by_day: dict[date, float] = {d: 0.0 for d in labels}
    total_30 = 0.0
    cutoff_30 = today - timedelta(days=30)
    for t in txns:
        dt = _parse_ts(t.get("created_at"))
        if not dt:
            continue
        q = _qty_num(t.get("qty"))
        used = abs(q) if q < 0 else 0.0
        if dt.date() >= cutoff_30:
            total_30 += used
        if dt.date() in by_day:
            by_day[dt.date()] += used
    series = [by_day[d] for d in labels]
    avg = total_30 / 30.0 if total_30 else 0.0
    return series, total_30, avg


def _adjust_stock_on_dismiss() -> None:
    st.session_state.pop("inventory_adjust_item_id", None)


@st.dialog("Adjust stock", width="medium", on_dismiss=_adjust_stock_on_dismiss)
def _adjust_stock_dialog(row: dict[str, Any], *, bump_data_version: Callable[[], None]) -> None:
    iid = _safe_str(row.get("id"))
    name = _safe_str(row.get("item_name")) or "Item"
    qoh = _qty_num(row.get("quantity_on_hand"))
    st.markdown(f"### {html.escape(name)}")
    st.caption(f"Current on hand: **{qoh:g}**")

    mode = st.radio(
        "Adjustment type",
        ("Receive (add stock)", "Issue (remove stock)", "Set quantity on hand"),
        key=f"inv_adj_mode_{iid}",
    )
    qty = st.number_input(
        "Quantity",
        min_value=0.0,
        value=0.0,
        step=0.25,
        format="%.4f",
        key=f"inv_adj_qty_{iid}",
    )
    notes = st.text_area("Notes", key=f"inv_adj_notes_{iid}", height=72)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Cancel", key=f"inv_adj_cancel_{iid}", use_container_width=True):
            st.session_state.pop("inventory_adjust_item_id", None)
            ips_app_rerun()
    with c2:
        submit = st.button("Apply adjustment", type="primary", key=f"inv_adj_submit_{iid}", use_container_width=True)

    if not submit:
        return

    qv = float(qty or 0)
    if qv <= 0:
        st.error("Quantity must be greater than zero.")
        return

    if mode.startswith("Receive"):
        delta = qv
        txn_type = "RECEIPT"
        new_qoh = qoh + qv
    elif mode.startswith("Issue"):
        if qv > qoh:
            st.error("Cannot issue more than quantity on hand.")
            return
        delta = -qv
        txn_type = "ADJUST"
        new_qoh = qoh - qv
    else:
        new_qoh = qv
        delta = new_qoh - qoh
        if delta == 0:
            st.info("Quantity unchanged.")
            return
        txn_type = "ADJUST"

    ts = datetime.now(timezone.utc).isoformat()
    prof = current_profile()
    cb = _safe_str(prof.get("email") or prof.get("full_name") or prof.get("id"))

    try:
        update_rows_admin(_TABLE, {"quantity_on_hand": float(new_qoh), "updated_at": ts}, {"id": iid})
    except Exception as exc:
        st.error(f"Could not update stock: {exc}")
        return

    txn_payload: dict[str, Any] = {
        "inventory_item_id": iid,
        "qty": float(delta),
        "txn_type": txn_type,
        "notes": _safe_str(notes)[:2000],
    }
    if cb:
        txn_payload["created_by"] = cb[:500]
    pid = _safe_str(prof.get("id"))
    if pid:
        txn_payload["profile_id"] = pid

    pl = dict(txn_payload)
    for _ in range(4):
        try:
            insert_row_admin(_TXN, pl)
            break
        except Exception as exc:
            low = str(exc).lower()
            if "created_by" in low:
                pl.pop("created_by", None)
            elif "profile_id" in low:
                pl.pop("profile_id", None)
            else:
                try:
                    update_rows_admin(_TABLE, {"quantity_on_hand": float(qoh), "updated_at": ts}, {"id": iid})
                except Exception:
                    pass
                st.error(f"Stock updated but transaction log failed: {exc}")
                return

    st.session_state.pop("inventory_adjust_item_id", None)
    bump_data_version()
    _invalidate_txn_cache()
    st.session_state["inventory_success"] = "Stock adjusted."
    ips_app_rerun()


def _render_header(*, can_edit: bool, export_df: pd.DataFrame) -> None:
    with st.container(border=True):
        st.markdown('<span class="ips-inv-header-anchor"></span>', unsafe_allow_html=True)
        left, right = st.columns([2.4, 1.2], gap="medium")
        with left:
            st.markdown(render_inventory_header_inner_html(), unsafe_allow_html=True)
        with right:
            st.markdown('<span class="ips-inv-hdr-actions"></span>', unsafe_allow_html=True)
            b1, b2 = st.columns(2, gap="small")
            with b1:
                if not export_df.empty:
                    csv = sanitize_catalog_inventory_export_df(export_df).to_csv(index=False).encode("utf-8")
                    st.download_button(
                        "↓ Export",
                        data=csv,
                        file_name="inventory_export.csv",
                        mime="text/csv",
                        key="inv_hdr_export",
                        use_container_width=True,
                    )
                else:
                    st.button("↓ Export", key="inv_hdr_export_disabled", disabled=True, use_container_width=True)
            with b2:
                if can_edit and st.button("+ New Item", type="primary", key="inv_hdr_new", use_container_width=True):
                    st.session_state["inventory_panel_mode"] = "add"
                    st.session_state["inventory_panel_id"] = None
                    ips_app_rerun()


def _render_filters(df: pd.DataFrame) -> None:
    cats = ["All Categories"] + _filter_options(df, "category")
    locs = ["All Locations"] + _filter_options(df, "storage_location")
    stats = ["All Statuses", "In Stock", "Low Stock", "Out of Stock", "Discontinued"]

    st.session_state.setdefault("inv_f_search", "")
    st.session_state.setdefault("inv_f_cat", "All Categories")
    st.session_state.setdefault("inv_f_loc", "All Locations")
    st.session_state.setdefault("inv_f_stock_status", "All Statuses")

    with st.container(border=True):
        st.markdown('<span class="ips-inv-filter-anchor"></span>', unsafe_allow_html=True)
        c1, c2, c3, c4, c5 = st.columns([2.2, 1, 1, 1, 0.75], gap="small")
        with c1:
            st.markdown('<span class="ips-inv-search-cell"></span>', unsafe_allow_html=True)
            st.text_input(
                "Search inventory",
                placeholder="Search inventory...",
                key="inv_f_search",
                label_visibility="collapsed",
            )
        with c2:
            st.selectbox("Category", cats, key="inv_f_cat", label_visibility="collapsed")
        with c3:
            st.selectbox("Location", locs, key="inv_f_loc", label_visibility="collapsed")
        with c4:
            st.selectbox("Status", stats, key="inv_f_stock_status", label_visibility="collapsed")
        with c5:
            if st.button("Clear Filters", key="inv_clear_filters", use_container_width=True, help="Reset all filters"):
                _clear_filters()
                ips_app_rerun()


def _render_table(
    filtered: pd.DataFrame,
    lookup: dict[str, dict[str, Any]],
    *,
    can_edit: bool,
    data_version: int,
    bump_data_version: Callable[[], None],
) -> None:
    selected_id = _safe_str(st.session_state.get("inventory_selected_id"))
    weights = [0.85, 1.5, 0.85, 0.85, 0.7, 0.5, 0.75, 0.8, 0.85, 0.55]

    with st.container(border=True):
        st.markdown('<span class="ips-inv-table-anchor"></span>', unsafe_allow_html=True)
        st.markdown('<span class="ips-inv-table-head-row" aria-hidden="true"></span>', unsafe_allow_html=True)
        head = st.columns(weights)
        for col, lbl in zip(
            head,
            (
                "Item #",
                "Description",
                "Category",
                "Location",
                "Qty On Hand",
                "Unit",
                "Unit Cost",
                "Total Value",
                "Status",
                "Actions",
            ),
        ):
            with col:
                st.markdown(table_header_html(lbl), unsafe_allow_html=True)

        for _, r in filtered.iterrows():
            row = r.to_dict()
            iid = _safe_str(row.get("id"))
            if not iid:
                continue
            is_sel = iid == selected_id
            row_cls = " ips-inv-row-selected ips-inv-table-row" if is_sel else " ips-inv-table-row"
            rc = st.columns(weights)
            item_num = _item_number(row)
            desc = _safe_str(row.get("item_name")) or "—"
            status = _stock_status(row)

            with rc[0]:
                st.markdown(
                    f'<span class="ips-inv-row-marker{row_cls}" aria-hidden="true"></span>',
                    unsafe_allow_html=True,
                )
                st.markdown('<span class="ips-inv-link-anchor"></span>', unsafe_allow_html=True)
                if st.button(item_num, key=f"inv_pick_{iid}", use_container_width=True):
                    st.session_state["inventory_selected_id"] = iid
                    st.session_state.pop("inventory_detail_collapsed", None)
                    ips_app_rerun()
            with rc[1]:
                st.markdown(
                    f'<span class="ips-inv-cell-desc">{html.escape(desc)}</span>',
                    unsafe_allow_html=True,
                )
            with rc[2]:
                st.markdown(
                    f'<span class="ips-inv-cell-muted">{html.escape(_safe_str(row.get("category")) or "—")}</span>',
                    unsafe_allow_html=True,
                )
            with rc[3]:
                st.markdown(
                    f'<span class="ips-inv-cell-muted">{html.escape(_safe_str(row.get("storage_location")) or "—")}</span>',
                    unsafe_allow_html=True,
                )
            with rc[4]:
                st.markdown(
                    f'<span class="ips-inv-cell-muted">{html.escape(_fmt_qty_unit(row, row.get("quantity_on_hand")))}</span>',
                    unsafe_allow_html=True,
                )
            with rc[5]:
                st.markdown(
                    f'<span class="ips-inv-cell-muted">{html.escape(_safe_str(row.get("unit")) or "EA")}</span>',
                    unsafe_allow_html=True,
                )
            with rc[6]:
                st.markdown(
                    f'<span class="ips-inv-cell-muted">{html.escape(_money(row.get("unit_cost")))}</span>',
                    unsafe_allow_html=True,
                )
            with rc[7]:
                st.markdown(
                    f'<span class="ips-inv-cell-total">{html.escape(_money(_total_value(row)))}</span>',
                    unsafe_allow_html=True,
                )
            with rc[8]:
                st.markdown(stock_status_badge_html(status), unsafe_allow_html=True)
            with rc[9]:
                st.markdown('<span class="ips-inv-act-anchor"></span>', unsafe_allow_html=True)
                a1, a2 = st.columns(2, gap="small")
                with a1:
                    if st.button("👁", key=f"inv_view_{iid}", help="View item", use_container_width=True):
                        st.session_state["inventory_selected_id"] = iid
                        st.session_state.pop("inventory_detail_collapsed", None)
                        ips_app_rerun()
                with a2:
                    with st.popover("⋯", use_container_width=True):
                        if st.button("Edit item", key=f"inv_more_edit_{iid}", use_container_width=True):
                            st.session_state["inventory_edit_popup_open"] = True
                            st.session_state["editing_inventory_id"] = iid
                            ips_app_rerun()
                        if st.button("Adjust stock", key=f"inv_more_adj_{iid}", use_container_width=True):
                            st.session_state["inventory_adjust_item_id"] = iid
                            ips_app_rerun()

        if selected_id and not st.session_state.get("inventory_detail_collapsed"):
            sel_row = lookup.get(selected_id)
            if sel_row:
                _render_detail_inline(
                    sel_row,
                    can_edit=can_edit,
                    data_version=data_version,
                    bump_data_version=bump_data_version,
                )
            else:
                st.session_state.pop("inventory_selected_id", None)


def _render_tab_bar(iid: str, active: str) -> str:
    st.markdown('<span class="ips-inv-tab-picker"></span>', unsafe_allow_html=True)
    tab_cols = st.columns(len(_INV_TABS), gap="small")
    _tab_icons = {
        "Overview": "▦",
        "Stock History": "↕",
        "Transactions": "⇄",
        "Purchase Orders": "🛒",
        "Vendors": "🏢",
        "Notes": "📝",
        "Attachments": "📎",
    }
    for col, tab in zip(tab_cols, _INV_TABS):
        ico = _tab_icons.get(tab, "")
        label = f"{ico} {tab}".strip()
        cell_cls = "ips-inv-tab-cell-active" if tab == active else "ips-inv-tab-cell"
        with col:
            st.markdown(f'<span class="{cell_cls}"></span>', unsafe_allow_html=True)
            if st.button(label, key=f"inv_tab_{iid}_{tab}", use_container_width=True):
                st.session_state[f"inventory_detail_tab_{iid}"] = tab
                ips_app_rerun()
    return active


def _render_overview_tab(
    row: dict[str, Any],
    txns: list[dict],
    *,
    data_version: int,
    can_edit: bool,
) -> None:
    iid = _safe_str(row.get("id"))
    qoh = _qty_num(row.get("quantity_on_hand"))
    rp = _qty_num(row.get("reorder_point"))
    available = qoh
    warn_avail = rp > 0 and available < rp

    series, total_30, avg_daily = _usage_series(txns)
    chart_html = usage_line_chart_html(series)

    r1c1, r1c2, r1c3 = st.columns(3, gap="small")
    with r1c1:
        st.markdown(
            summary_card_html(
                "Item Details",
                [
                    ("Item Number", _item_number(row)),
                    ("Description", _safe_str(row.get("item_name"))),
                    ("Category", _safe_str(row.get("category"))),
                    ("Unit", _unit(row)),
                    ("Location", _safe_str(row.get("storage_location"))),
                    ("Barcode", _safe_str(row.get("qr_code_value") or row.get("sku"))),
                    ("Status", _stock_status(row)),
                    ("Created", _fmt_date(row.get("created_at"))),
                    ("Last Updated", _fmt_date(row.get("updated_at"))),
                ],
                badge_html={"Status": stock_status_badge_html(_stock_status(row))},
            ),
            unsafe_allow_html=True,
        )
    with r1c2:
        st.markdown(
            summary_card_html(
                "Stock Information",
                [
                    ("Qty On Hand", _fmt_qty_unit(row, qoh)),
                    ("Reorder Level", _fmt_qty_unit(row, rp)),
                    ("Reorder Quantity", "—"),
                    ("On Order", "—"),
                    ("Allocated", "—"),
                    ("Available", _fmt_qty_unit(row, available)),
                    ("Last Counted", "—"),
                ],
                value_class={"Available": "warn"} if warn_avail else None,
            ),
            unsafe_allow_html=True,
        )
    with r1c3:
        st.markdown('<div class="ips-inv-summary-card"><h4>Usage Overview</h4>', unsafe_allow_html=True)
        if chart_html:
            st.markdown(chart_html, unsafe_allow_html=True)
            st.markdown(
                f'<motion.div class="ips-inv-usage-metrics">'
                f"<span><strong>Total Used (30 Days):</strong> {total_30:g} {_unit(row)}</span>"
                f"<span><strong>Average Daily Use:</strong> {avg_daily:.1f} {_unit(row)}</span>"
                f"</motion.div>".replace("<motion.", "<").replace("</motion.", "</"),
                unsafe_allow_html=True,
            )
        else:
            st.markdown('<p class="ips-inv-usage-empty">No usage data for this item yet.</p>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<motion.div class="ips-inv-txn-section">'.replace("<motion.", "<"), unsafe_allow_html=True)
    st.markdown('<motion.div class="ips-inv-txn-head"><h4>Recent Transactions</h4></motion.div>'.replace("<motion.", "<").replace("</motion.", "</"), unsafe_allow_html=True)
    _, btn_r = st.columns([4, 1])
    with btn_r:
        if st.button("View All Transactions", key=f"inv_txn_all_{iid}", use_container_width=True):
            st.session_state[f"inventory_detail_tab_{iid}"] = "Transactions"
            ips_app_rerun()

    recent = sorted(txns, key=lambda tr: str(tr.get("created_at") or ""), reverse=True)[:8]
    txn_rows: list[dict[str, str]] = []
    for tr in recent:
        q = _qty_num(tr.get("qty"))
        uc = _qty_num(tr.get("unit_cost")) if tr.get("unit_cost") is not None else _qty_num(row.get("unit_cost"))
        u = _unit(row)
        qty_s = f"{q:+g} {u}" if q else f"0 {u}"
        txn_rows.append(
            {
                "Date": _fmt_date(tr.get("created_at")),
                "Type": _txn_type_label(str(tr.get("txn_type") or "")),
                "Reference": _txn_reference(tr),
                "Qty": qty_s,
                "Unit Cost": _money(uc),
                "Total Cost": _money(abs(q) * uc) if uc else "—",
                "Performed By": _txn_actor(tr),
            }
        )
    st.markdown(transactions_table_html(txn_rows), unsafe_allow_html=True)
    st.markdown("</motion.div>".replace("<motion.", "<").replace("</motion.", "</"), unsafe_allow_html=True)


def _txn_dataframe(txns: list[dict], row: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for t in sorted(txns, key=lambda x: str(x.get("created_at") or ""), reverse=True):
        q = _qty_num(t.get("qty"))
        uc = _qty_num(t.get("unit_cost")) if t.get("unit_cost") is not None else _qty_num(row.get("unit_cost"))
        rows.append(
            {
                "Date": _fmt_date(t.get("created_at")),
                "Type": _txn_type_label(str(t.get("txn_type") or "")),
                "Reference": _txn_reference(t),
                "Qty": f"{q:+g}" if q else "0",
                "Unit Cost": _money(uc),
                "Total Cost": _money(abs(q) * uc) if uc else "—",
                "Performed By": _txn_actor(t),
                "Notes": _safe_str(t.get("notes")) or "—",
            }
        )
    return pd.DataFrame(rows)


def _render_stock_history_tab(txns: list[dict], row: dict[str, Any]) -> None:
    hist = [t for t in txns if str(t.get("txn_type") or "").upper() in ("ADJUST", "RECEIPT", "COUNT")]
    if not hist:
        hist = list(txns)
    if not hist:
        st.caption("No stock history yet.")
        return
    st.dataframe(_txn_dataframe(hist, row), use_container_width=True, hide_index=True)


def _render_transactions_tab(txns: list[dict], row: dict[str, Any]) -> None:
    if not txns:
        st.caption("No transactions logged. Issues from **Scan Inventory** appear here.")
        return
    st.dataframe(_txn_dataframe(txns, row), use_container_width=True, hide_index=True)


def _render_purchase_orders_tab() -> None:
    st.caption("Purchase order linking is not configured yet. Connect PO lines when that module is available.")


def _render_vendors_tab(row: dict[str, Any]) -> None:
    vendor = _safe_str(row.get("vendor"))
    if vendor:
        st.markdown(f"**Preferred vendor:** {html.escape(vendor)}")
    else:
        st.caption("No vendor on file for this item.")


def _render_notes_tab(row: dict[str, Any], *, can_edit: bool, bump_data_version: Callable[[], None]) -> None:
    iid = _safe_str(row.get("id"))
    if can_edit:
        notes = st.text_area("Notes", value=_safe_str(row.get("notes")), height=140, key=f"inv_notes_{iid}")
        if st.button("Save notes", type="primary", key=f"inv_notes_save_{iid}", use_container_width=True):
            try:
                update_rows_admin(_TABLE, {"notes": notes.strip()}, {"id": iid})
                bump_data_version()
                st.success("Notes saved.")
                ips_app_rerun()
            except Exception as exc:
                st.error(str(exc))
    else:
        st.write(_safe_str(row.get("notes")) or "—")


def _render_attachments_tab(row: dict[str, Any], iid: str) -> None:
    img = _safe_str(row.get("image_url"))
    if img:
        try:
            from app.pages.inventory import _signed_url_for_inventory_image_cached
        except ImportError:
            from pages.inventory import _signed_url_for_inventory_image_cached  # type: ignore
        url = _signed_url_for_inventory_image_cached(img) if img else None
        if url:
            st.image(url, width=200)
        else:
            st.caption("Image on file but preview unavailable.")
    else:
        st.caption("No item photo uploaded.")

    qr = _safe_str(row.get("qr_code_value"))
    if qr:
        st.caption(f"Scan code: `{qr}`")
        try:
            from app.pages.inventory import _inv_qr_img_html, _inventory_label_html
        except ImportError:
            from pages.inventory import _inv_qr_img_html, _inventory_label_html  # type: ignore
        st.markdown(_inv_qr_img_html(qr, size=140), unsafe_allow_html=True)
        html_doc = _inventory_label_html(
            item_name=_safe_str(row.get("item_name")),
            sku=_safe_str(row.get("sku")),
            qr_value=qr,
            item_id=iid,
        )
        st.download_button(
            "Print QR label (HTML)",
            data=html_doc.encode("utf-8"),
            file_name=f"inventory_label_{iid[:8]}.html",
            mime="text/html",
            key=f"inv_att_label_{iid}",
        )


def _render_detail_inline(
    row: dict[str, Any],
    *,
    can_edit: bool,
    data_version: int,
    bump_data_version: Callable[[], None],
) -> None:
    iid = _safe_str(row.get("id"))
    txns = _cached_item_transactions(iid, data_version)
    tab_key = f"inventory_detail_tab_{iid}"
    st.session_state.setdefault(tab_key, "Overview")
    active_tab = str(st.session_state.get(tab_key) or "Overview")
    if active_tab not in _INV_TABS:
        active_tab = "Overview"

    status = _stock_status(row)
    qoh = _qty_num(row.get("quantity_on_hand"))
    rp = _qty_num(row.get("reorder_point"))
    tv = _total_value(row)

    st.markdown('<div class="ips-inv-detail-inline ips-inv-detail-anchor">', unsafe_allow_html=True)
    hl, hm, hr = st.columns([1.35, 2.2, 1.45], gap="medium")
    with hl:
        st.markdown(
            f'<div class="ips-inv-detail-id-row">'
            f'<span class="ips-inv-detail-id">{html.escape(_item_number(row))}</span>'
            f"{stock_status_badge_html(status)}"
            f"</motion.div>"
            f'<p class="ips-inv-detail-name">{html.escape(_safe_str(row.get("item_name")))}</p>'
            f'<p class="ips-inv-detail-cat">{html.escape(_safe_str(row.get("category")) or "—")}</p>'.replace(
                "<motion.", "<"
            ).replace("</motion.", "</"),
            unsafe_allow_html=True,
        )
    with hm:
        st.markdown(
            detail_stats_row_html(
                [
                    ("Location", _safe_str(row.get("storage_location")) or "—"),
                    ("Qty On Hand", _fmt_qty_unit(row, qoh)),
                    ("Reorder Level", _fmt_qty_unit(row, rp)),
                    ("Unit Cost", _money(row.get("unit_cost"))),
                    ("Total Value", _money(tv)),
                ]
            ),
            unsafe_allow_html=True,
        )
    with hr:
        st.markdown('<span class="ips-inv-det-actions"></span>', unsafe_allow_html=True)
        b1, b2, b3, b4 = st.columns([1, 1.25, 0.55, 0.35], gap="small")
        with b1:
            if can_edit and st.button("Edit", key=f"inv_det_edit_{iid}", use_container_width=True):
                st.session_state["inventory_edit_popup_open"] = True
                st.session_state["editing_inventory_id"] = iid
                ips_app_rerun()
        with b2:
            if can_edit and st.button("Adjust Stock", type="primary", key=f"inv_det_adj_{iid}", use_container_width=True):
                st.session_state["inventory_adjust_item_id"] = iid
                ips_app_rerun()
        with b3:
            with st.popover("More", use_container_width=True):
                if can_edit and st.button("Deactivate", key=f"inv_det_deact_{iid}", use_container_width=True):
                    try:
                        update_rows_admin(_TABLE, {"is_active": False}, {"id": iid})
                        bump_data_version()
                        st.session_state["inventory_success"] = "Item deactivated."
                        ips_app_rerun()
                    except Exception as exc:
                        st.error(str(exc))
                if can_edit and st.button("Delete item", key=f"inv_det_del_{iid}", use_container_width=True):
                    open_destructive_confirmation(_DELETE_CONFIRM_PREFIX)
                    st.session_state["inventory_pending_delete_ids"] = [iid]
                    ips_app_rerun()
                try:
                    from app.ui import IPS_NAV_PENDING_KEY
                except ImportError:
                    from ui import IPS_NAV_PENDING_KEY  # type: ignore
                if st.button("Scan Inventory", key=f"inv_det_scan_{iid}", use_container_width=True):
                    st.session_state[IPS_NAV_PENDING_KEY] = "Scan Inventory"
                    ips_app_rerun()
        with b4:
            if st.button("▲", key=f"inv_det_collapse_{iid}", help="Collapse", use_container_width=True):
                st.session_state["inventory_detail_collapsed"] = True
                ips_app_rerun()

    active_tab = _render_tab_bar(iid, active_tab)

    if active_tab == "Overview":
        _render_overview_tab(row, txns, data_version=data_version, can_edit=can_edit)
    elif active_tab == "Stock History":
        _render_stock_history_tab(txns, row)
    elif active_tab == "Transactions":
        _render_transactions_tab(txns, row)
    elif active_tab == "Purchase Orders":
        _render_purchase_orders_tab()
    elif active_tab == "Vendors":
        _render_vendors_tab(row)
    elif active_tab == "Notes":
        _render_notes_tab(row, can_edit=can_edit, bump_data_version=bump_data_version)
    else:
        _render_attachments_tab(row, iid)

    st.markdown("</div>", unsafe_allow_html=True)


@fragment
def _render_list_fragment(
    *,
    df: pd.DataFrame,
    rows: list[dict],
    can_edit: bool,
    data_version: int,
    bump_data_version: Callable[[], None],
) -> None:
    inject_scroll_preserve("inventory")
    inject_inventory_page_styles()
    st.markdown('<span class="ips-inventory-page ips-page-shell-marker"></span>', unsafe_allow_html=True)

    lookup = _row_lookup(rows)
    filtered = _apply_filters(df)

    _render_header(can_edit=can_edit, export_df=filtered)
    _render_filters(df)

    if df.empty:
        try:
            from app.ui.components.empty_states import render_empty_state
        except ImportError:
            from ui.components.empty_states import render_empty_state  # type: ignore
        if can_edit and render_empty_state(
            "No inventory items found",
            "Add your first item to start tracking stock.",
            icon="📦",
            action_label="+ New Item",
            action_key="inv_empty_add",
        ):
            st.session_state["inventory_panel_mode"] = "add"
            st.session_state["inventory_panel_id"] = None
            ips_app_rerun()
        else:
            render_empty_state(
                "No inventory items found",
                "No items are available in the catalog yet.",
                icon="📦",
            )
        return

    if filtered.empty:
        st.info("No items match your filters.")
        return

    _render_table(
        filtered,
        lookup,
        can_edit=can_edit,
        data_version=data_version,
        bump_data_version=bump_data_version,
    )


def render_inventory_list_page(
    *,
    df: pd.DataFrame,
    rows: list[dict],
    can_edit: bool,
    data_version: int,
    bump_data_version: Callable[[], None],
) -> None:
    """Inventory list UI (header, filters, table, detail panel)."""
    _render_list_fragment(
        df=df,
        rows=rows,
        can_edit=can_edit,
        data_version=data_version,
        bump_data_version=bump_data_version,
    )

    adj_id = _safe_str(st.session_state.get("inventory_adjust_item_id"))
    if adj_id and can_edit:
        pr = fetch_by_match_admin(_TABLE, {"id": adj_id}, limit=1)
        if pr:
            _adjust_stock_dialog(dict(pr[0]), bump_data_version=bump_data_version)
