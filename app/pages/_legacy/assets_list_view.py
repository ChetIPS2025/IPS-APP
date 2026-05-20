"""Assets list — table, filters, and inline detail panel (Asset Database page)."""

from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

try:
    from app.asset_responsive import inject_asset_workflow_mobile_css
    from app.auth import current_profile, current_role
    from app.db import (
        create_signed_url,
        delete_rows_admin,
        fetch_by_match,
        fetch_by_match_admin,
        fetch_table,
        update_rows_admin,
    )
    from app.mobile_ui import ensure_narrow_viewport_detected
    from app.pages.asset_database import (
        _asset_delete_dependency_state,
        _disp,
        prepare_assets_dataframe,
    )
    from app.pages.asset_intake import render_asset_intake_form
    from app.services.asset_constants import DOCUMENT_TYPES
    from app.services.asset_document_util import persist_asset_document_upload
    from app.services.asset_service import save_maintenance_record
    from app.services.job_service import job_row_select_label, sort_jobs_by_number_then_name
    from app.ui import IPS_NAV_PENDING_KEY
    from app.ui.assets_components import (
        completed_badge_html,
        detail_header_html,
        detail_meta_grid_html,
        detail_meta_strip_html,
        inject_assets_page_styles,
        maintenance_table_html,
        render_assets_header_inner_html,
        status_badge_html,
        summary_card_html,
        tab_button_label,
        table_header_html,
    )
except ImportError:
    from asset_responsive import inject_asset_workflow_mobile_css  # type: ignore
    from auth import current_profile, current_role  # type: ignore
    from db import (  # type: ignore
        create_signed_url,
        delete_rows_admin,
        fetch_by_match,
        fetch_by_match_admin,
        fetch_table,
        update_rows_admin,
    )
    from mobile_ui import ensure_narrow_viewport_detected  # type: ignore
    from pages.asset_database import (  # type: ignore
        _asset_delete_dependency_state,
        _disp,
        prepare_assets_dataframe,
    )
    from pages.asset_intake import render_asset_intake_form  # type: ignore
    from services.asset_constants import DOCUMENT_TYPES  # type: ignore
    from services.asset_document_util import persist_asset_document_upload  # type: ignore
    from services.asset_service import save_maintenance_record  # type: ignore
    from services.job_service import job_row_select_label, sort_jobs_by_number_then_name  # type: ignore
    from ui import IPS_NAV_PENDING_KEY  # type: ignore
    from ui.assets_components import (  # type: ignore
        completed_badge_html,
        detail_header_html,
        detail_meta_grid_html,
        detail_meta_strip_html,
        inject_assets_page_styles,
        maintenance_table_html,
        render_assets_header_inner_html,
        status_badge_html,
        summary_card_html,
        tab_button_label,
        table_header_html,
    )

_ASSET_TABS = (
    "Overview",
    "Maintenance",
    "Documents",
    "Assignments",
    "Depreciation",
    "Notes",
    "Activity",
)

_SEARCH_COLS = (
    "asset_id",
    "asset_name",
    "manufacturer",
    "model",
    "serial_number",
    "status",
    "category",
    "location",
    "department",
    "assigned_employee",
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
        if f == 0.0:
            return "—"
        return f"${f:,.2f}"
    except (TypeError, ValueError):
        return "—"


def _float_or_zero(val: object) -> float:
    if val is None or str(val).strip() == "":
        return 0.0
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def _financial_overview_rows(row: dict[str, Any]) -> list[tuple[str, str]]:
    purchase = _float_or_zero(row.get("purchase_cost"))
    salvage_raw = row.get("salvage_value")
    salvage: float | None = None
    if salvage_raw not in (None, ""):
        salvage = _float_or_zero(salvage_raw)
    elif purchase > 0:
        salvage = 500.0 if purchase >= 3000 else max(0.0, round(purchase * 0.16, 2))
    life_years = 7
    annual = (purchase - salvage) / life_years if salvage is not None and purchase > salvage else 0.0
    return [
        ("Acquired Date", _fmt_date(row.get("purchase_date"))),
        ("Purchase Price", _money(row.get("purchase_cost"))),
        ("Current Value", _money(row.get("current_value"))),
        ("Salvage Value", _money(salvage) if salvage is not None else "—"),
        ("Depreciation Method", "Straight Line"),
        ("Useful Life", f"{life_years} years"),
        ("Annual Depreciation", _money(annual) if annual else "—"),
    ]


def _invalidate_assets_cache() -> None:
    _cached_assets_rows.clear()
    _cached_jobs_labels.clear()


@st.cache_data(ttl=60, show_spinner=False)
def _cached_assets_rows() -> list[dict[str, Any]]:
    try:
        return list(fetch_table("assets", limit=5000, order_by="asset_name") or [])
    except Exception:
        return []


@st.cache_data(ttl=120, show_spinner=False)
def _cached_jobs_labels() -> dict[str, str]:
    try:
        jobs = sort_jobs_by_number_then_name(fetch_table("jobs", limit=5000, order_by="job_number"))
    except Exception:
        return {}
    return {str(j.get("id")): job_row_select_label(j) for j in jobs if j.get("id")}


def _filter_options(df: pd.DataFrame, col: str) -> list[str]:
    if df.empty or col not in df.columns:
        return []
    vals = sorted({_safe_str(v) for v in df[col].dropna().unique() if _safe_str(v)})
    return vals


def _apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    search = _safe_str(st.session_state.get("assets_f_search")).lower()
    cat = _safe_str(st.session_state.get("assets_f_category"))
    loc = _safe_str(st.session_state.get("assets_f_location"))
    stt = _safe_str(st.session_state.get("assets_f_status"))
    dept = _safe_str(st.session_state.get("assets_f_department"))

    if cat and cat != "All Categories" and "category" in out.columns:
        out = out[out["category"].astype(str).str.strip() == cat]
    if loc and loc != "All Locations" and "location" in out.columns:
        out = out[out["location"].astype(str).str.strip() == loc]
    if stt and stt != "All Statuses" and "status" in out.columns:
        out = out[out["status"].astype(str).str.strip() == stt]
    if dept and dept != "All Departments" and "department" in out.columns:
        out = out[out["department"].astype(str).str.strip() == dept]
    if search:
        cols = [c for c in _SEARCH_COLS if c in out.columns]
        if cols:
            mask = out[cols].astype(str).apply(lambda col: col.str.lower().str.contains(search, na=False))
            out = out[mask.any(axis=1)]
    return out


def _clear_filters() -> None:
    st.session_state["assets_f_search"] = ""
    st.session_state["assets_f_category"] = "All Categories"
    st.session_state["assets_f_location"] = "All Locations"
    st.session_state["assets_f_status"] = "All Statuses"
    st.session_state["assets_f_department"] = "All Departments"


def _row_dict_by_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(r.get("id") or "").strip(): r for r in rows if str(r.get("id") or "").strip()}


def _safe_fetch(table: str, match: dict, *, limit: int = 500) -> list[dict]:
    try:
        return fetch_by_match(table, match, limit=limit)  # type: ignore[misc]
    except Exception:
        try:
            return fetch_by_match_admin(table, match, limit=limit)  # type: ignore[misc]
        except Exception:
            return []


def _usage_hours_miles(row: dict) -> str:
    hm = row.get("hour_meter")
    mi = row.get("mileage")
    parts: list[str] = []
    if hm is not None and str(hm).strip() not in ("", "0", "0.0"):
        parts.append(f"{_disp(hm)} hrs")
    if mi is not None and str(mi).strip() not in ("", "0", "0.0"):
        parts.append(f"{_disp(mi)} mi")
    return " · ".join(parts) if parts else "—"


def _next_service_due(row: dict, maintenance: list[dict]) -> str:
    md = _safe_str(row.get("maintenance_due_date"))
    if md:
        return _fmt_date(md)
    for m in maintenance:
        nd = m.get("next_service_date")
        if nd:
            return _fmt_date(nd)
    return "—"


def _build_activity_events(
    *,
    maintenance: list[dict],
    assignments: list[dict],
    inspections: list[dict],
) -> list[dict[str, str]]:
    events: list[dict[str, str]] = []
    for m in maintenance:
        events.append(
            {
                "when": str(m.get("service_date") or m.get("created_at") or ""),
                "label": f"Maintenance — {m.get('service_type') or 'Service'}",
                "detail": _safe_str(m.get("notes")) or _money(m.get("cost")),
            }
        )
    for a in assignments:
        ts = str(a.get("check_out_at") or a.get("check_in_at") or a.get("created_at") or "")
        kind = "Check-out" if a.get("check_out_at") and not a.get("check_in_at") else "Assignment"
        events.append(
            {
                "when": ts,
                "label": kind,
                "detail": _safe_str(a.get("assigned_to")) or _safe_str(a.get("notes")),
            }
        )
    for i in inspections:
        events.append(
            {
                "when": str(i.get("inspection_date") or i.get("created_at") or ""),
                "label": f"Inspection — {i.get('inspection_type') or 'Inspection'}",
                "detail": _safe_str(i.get("status")),
            }
        )
    events.sort(key=lambda e: e.get("when") or "", reverse=True)
    return events


def _render_header(*, can_add: bool, export_df: pd.DataFrame) -> None:
    with st.container(border=True):
        st.markdown('<span class="ips-assets-header-anchor"></span>', unsafe_allow_html=True)
        left, right = st.columns([2.4, 1.2], gap="medium")
        with left:
            st.markdown(render_assets_header_inner_html(), unsafe_allow_html=True)
        with right:
            st.markdown('<div style="height:0.15rem"></div>', unsafe_allow_html=True)
            b1, b2 = st.columns(2, gap="small")
            with b1:
                st.markdown('<div class="ips-assets-export-btn">', unsafe_allow_html=True)
                if not export_df.empty:
                    csv = export_df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        "⬆ Export",
                        data=csv,
                        file_name="assets_export.csv",
                        mime="text/csv",
                        key="assets_hdr_export",
                        use_container_width=True,
                    )
                else:
                    st.button("⬆ Export", key="assets_hdr_export_disabled", disabled=True, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
            with b2:
                st.markdown('<div class="ips-assets-new-btn">', unsafe_allow_html=True)
                if can_add and st.button("+ New Asset", type="primary", key="assets_hdr_new", use_container_width=True):
                    st.session_state["asset_db_add_mode"] = True
                    st.session_state.pop("assets_selected_id", None)
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)


def _render_filters(df: pd.DataFrame) -> None:
    cats = ["All Categories"] + _filter_options(df, "category")
    locs = ["All Locations"] + _filter_options(df, "location")
    stats = ["All Statuses"] + _filter_options(df, "status")
    depts = ["All Departments"] + _filter_options(df, "department")

    st.session_state.setdefault("assets_f_search", "")
    st.session_state.setdefault("assets_f_category", "All Categories")
    st.session_state.setdefault("assets_f_location", "All Locations")
    st.session_state.setdefault("assets_f_status", "All Statuses")
    st.session_state.setdefault("assets_f_department", "All Departments")

    with st.container(border=True):
        st.markdown('<span class="ips-assets-filter-anchor"></span>', unsafe_allow_html=True)
        c1, c2, c3, c4, c5, c6 = st.columns([2.2, 1, 1, 1, 1, 0.75], gap="small")
        with c1:
            st.text_input(
                "Search assets",
                placeholder="🔍 Search assets...",
                key="assets_f_search",
                label_visibility="collapsed",
            )
        with c2:
            st.selectbox("Category", cats, key="assets_f_category", label_visibility="collapsed")
        with c3:
            st.selectbox("Location", locs, key="assets_f_location", label_visibility="collapsed")
        with c4:
            st.selectbox("Status", stats, key="assets_f_status", label_visibility="collapsed")
        with c5:
            st.selectbox("Department", depts, key="assets_f_department", label_visibility="collapsed")
        with c6:
            st.markdown('<div class="ips-assets-clear-filters">', unsafe_allow_html=True)
            if st.button("⛃ Clear Filters", key="assets_clear_filters", use_container_width=True):
                _clear_filters()
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)


def _render_assets_table(
    filtered: pd.DataFrame,
    row_lookup: dict[str, dict[str, Any]],
    *,
    selected_id: str,
    sel_row: dict[str, Any] | None,
    can_edit: bool,
    can_delete: bool,
    job_label_by_id: dict[str, str],
) -> None:
    collapsed = bool(st.session_state.get("assets_detail_collapsed"))
    weights = [0.95, 1.35, 0.9, 0.85, 0.85, 0.75, 0.85, 0.75, 0.55]

    with st.container(border=True):
        st.markdown('<span class="ips-assets-table-anchor"></span>', unsafe_allow_html=True)
        head = st.columns(weights)
        labels = (
            "Asset #",
            "Asset Name",
            "Category",
            "Location",
            "Department",
            "Status",
            "Acquired Date",
            "Value",
            "Actions",
        )
        for col, lbl in zip(head, labels):
            with col:
                if lbl == "Asset #":
                    st.markdown(
                        '<span class="ips-assets-table-head-row" aria-hidden="true"></span>',
                        unsafe_allow_html=True,
                    )
                st.markdown(table_header_html(lbl, sortable=lbl != "Actions"), unsafe_allow_html=True)

        for _, r in filtered.iterrows():
            aid = _safe_str(r.get("id"))
            if not aid:
                continue
            is_sel = aid == selected_id
            marker = " ips-assets-row-selected" if is_sel else ""
            rc = st.columns(weights)
            asset_num = _safe_str(r.get("asset_id")) or "—"
            name = _safe_str(r.get("asset_name")) or "—"
            status_html = status_badge_html(_safe_str(r.get("status")))
            acquired = _fmt_date(r.get("purchase_date"))
            value = _money(r.get("current_value") or r.get("purchase_cost"))

            with rc[0]:
                st.markdown(
                    f'<span class="ips-assets-row-marker{marker}" aria-hidden="true"></span>',
                    unsafe_allow_html=True,
                )
                st.markdown('<div class="ips-assets-link-btn">', unsafe_allow_html=True)
                if st.button(asset_num, key=f"assets_pick_{aid}", use_container_width=True):
                    st.session_state["assets_selected_id"] = aid
                    st.session_state.pop("assets_detail_collapsed", None)
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
            with rc[1]:
                st.markdown(
                    f'<span class="ips-assets-name-cell">{html.escape(name)}</span>',
                    unsafe_allow_html=True,
                )
            with rc[2]:
                st.markdown(
                    f'<span class="ips-assets-muted-cell">{html.escape(_safe_str(r.get("category")) or "—")}</span>',
                    unsafe_allow_html=True,
                )
            with rc[3]:
                st.markdown(
                    f'<span class="ips-assets-muted-cell">{html.escape(_safe_str(r.get("location")) or "—")}</span>',
                    unsafe_allow_html=True,
                )
            with rc[4]:
                st.markdown(
                    f'<span class="ips-assets-muted-cell">{html.escape(_safe_str(r.get("department")) or "—")}</span>',
                    unsafe_allow_html=True,
                )
            with rc[5]:
                st.markdown(status_html, unsafe_allow_html=True)
            with rc[6]:
                st.markdown(
                    f'<span class="ips-assets-muted-cell">{html.escape(acquired)}</span>',
                    unsafe_allow_html=True,
                )
            with rc[7]:
                st.markdown(
                    f'<span class="ips-assets-muted-cell">{html.escape(value)}</span>',
                    unsafe_allow_html=True,
                )
            with rc[8]:
                st.markdown('<div class="ips-assets-action-btn">', unsafe_allow_html=True)
                a1, a2 = st.columns(2, gap="small")
                with a1:
                    if st.button("👁", key=f"assets_view_{aid}", help="View asset", use_container_width=True):
                        st.session_state["assets_selected_id"] = aid
                        st.session_state.pop("assets_detail_collapsed", None)
                        st.rerun()
                with a2:
                    full = row_lookup.get(aid, {})
                    with st.popover("⋯", use_container_width=True):
                        if st.button("Open full profile", key=f"assets_more_detail_{aid}", use_container_width=True):
                            st.session_state["asset_detail_id"] = aid
                            st.session_state[IPS_NAV_PENDING_KEY] = "Asset Detail"
                            st.rerun()
                        if st.button("Asset Scanner", key=f"assets_more_scan_{aid}", use_container_width=True):
                            st.session_state[IPS_NAV_PENDING_KEY] = "Asset Scanner"
                            st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

        if selected_id and sel_row and not collapsed:
            _render_asset_detail_panel(
                sel_row,
                can_edit=can_edit,
                can_delete=can_delete,
                job_label_by_id=job_label_by_id,
                embedded=True,
            )


def _render_tab_bar(aid: str, active: str) -> str:
    tab_key = f"assets_detail_tab_{aid}"
    st.markdown('<span class="ips-assets-tabs-anchor" aria-hidden="true"></span>', unsafe_allow_html=True)
    tab_cols = st.columns(len(_ASSET_TABS), gap="small")
    picked = active
    for i, tab in enumerate(_ASSET_TABS):
        with tab_cols[i]:
            if st.button(
                tab_button_label(tab),
                key=f"assets_tab_btn_{aid}_{tab}",
                use_container_width=True,
                type="primary" if tab == active else "secondary",
            ):
                st.session_state[tab_key] = tab
                picked = tab
                st.rerun()
    st.session_state[tab_key] = picked
    return str(picked)


def _render_overview_tab(
    row: dict[str, Any],
    *,
    maintenance: list[dict],
) -> None:
    aid = _safe_str(row.get("id"))
    photo_path = _safe_str(row.get("photo_path"))

    r1c1, r1c2, r1c3, r1c4 = st.columns(4, gap="small")
    with r1c1:
        st.markdown(
            summary_card_html(
                "Asset Details",
                [
                    ("Asset Number", _disp(row.get("asset_id"))),
                    ("Asset Name", _disp(row.get("asset_name"))),
                    ("Category", _disp(row.get("category"))),
                    ("Status", status_badge_html(_safe_str(row.get("status")))),
                    ("Location", _disp(row.get("location"))),
                    ("Department", _disp(row.get("department"))),
                    ("Manufacturer", _disp(row.get("manufacturer"))),
                    ("Model", _disp(row.get("model"))),
                    ("Serial Number", _disp(row.get("serial_number"))),
                    ("License Plate", _disp(row.get("license_plate"))),
                    ("Description", (_safe_str(row.get("notes"))[:220] or "—")),
                ],
                html_value_keys=frozenset({"Status"}),
            ),
            unsafe_allow_html=True,
        )
    with r1c2:
        st.markdown(
            summary_card_html(
                "Usage Information",
                [
                    ("Current Operator", _disp(row.get("assigned_employee"))),
                    ("Primary Use", _disp(row.get("asset_type") or row.get("category"))),
                    ("Hours/Miles", _usage_hours_miles(row)),
                    ("Last Used", _fmt_date(row.get("last_checkout_at"))),
                    ("Condition", _disp(row.get("condition"))),
                    ("Next Service Due", _next_service_due(row, maintenance)),
                ],
            ),
            unsafe_allow_html=True,
        )
    with r1c3:
        st.markdown(
            summary_card_html("Financial Information", _financial_overview_rows(row)),
            unsafe_allow_html=True,
        )
    with r1c4:
        st.markdown('<div class="ips-assets-summary-card"><h4>Image</h4>', unsafe_allow_html=True)
        st.markdown('<div class="ips-assets-img-wrap">', unsafe_allow_html=True)
        if photo_path:
            url = create_signed_url(photo_path, expires_in=3600)
            if url:
                try:
                    st.image(url, use_container_width=True)
                except Exception:
                    st.markdown(
                        '<p class="ips-assets-img-empty">Image unavailable</p>',
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown(
                    '<p class="ips-assets-img-empty">No photo on file</p>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                '<p class="ips-assets-img-empty">No asset photo<br><span style="font-weight:500;">Upload via full profile or intake</span></p>',
                unsafe_allow_html=True,
            )
        st.markdown("</div></div>", unsafe_allow_html=True)

    st.markdown('<div class="ips-assets-maint-section">', unsafe_allow_html=True)
    hdr_r, btn_r = st.columns([3, 1], gap="small")
    with hdr_r:
        st.markdown('<div class="ips-assets-maint-head"><h4>Maintenance History</h4></div>', unsafe_allow_html=True)
    with btn_r:
        st.markdown('<div class="ips-assets-view-all-maint">', unsafe_allow_html=True)
        if st.button("View All Maintenance", key=f"assets_maint_all_{aid}", use_container_width=True):
            st.session_state[f"assets_detail_tab_{aid}"] = "Maintenance"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    maint_rows: list[dict[str, str]] = []
    for m in maintenance[:8]:
        desc = _safe_str(m.get("notes")) or _safe_str(m.get("service_type")) or "—"
        maint_rows.append(
            {
                "date": _fmt_date(m.get("service_date")),
                "type": _safe_str(m.get("service_type")) or "—",
                "description": desc,
                "performed_by": _safe_str(m.get("performed_by")) or "—",
                "cost": _money(m.get("cost")),
                "next_due": _fmt_date(m.get("next_service_date")),
                "status_html": completed_badge_html(),
            }
        )
    st.markdown(maintenance_table_html(maint_rows), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def _render_maintenance_tab(row: dict[str, Any], maintenance: list[dict], *, can_edit: bool) -> None:
    aid = _safe_str(row.get("id"))
    if can_edit:
        with st.expander("Add maintenance record", expanded=False):
            m1, m2, m3 = st.columns(3)
            svc_type = m1.text_input("Service type", value="PM Service", key=f"assets_m_type_{aid}")
            svc_date = m2.date_input("Service date", key=f"assets_m_date_{aid}")
            vendor = m3.text_input("Vendor", key=f"assets_m_vendor_{aid}")
            m4, m5, m6 = st.columns(3)
            cost = m4.number_input("Cost", min_value=0.0, value=0.0, key=f"assets_m_cost_{aid}")
            perf = m5.text_input("Performed by", key=f"assets_m_perf_{aid}")
            po = m6.text_input("PO number", key=f"assets_m_po_{aid}")
            notes = st.text_area("Notes", key=f"assets_m_notes_{aid}", height=72)
            if st.button("Save maintenance", type="primary", key=f"assets_m_save_{aid}", use_container_width=True):
                save_maintenance_record(
                    {
                        "asset_id": row["id"],
                        "service_type": svc_type.strip(),
                        "service_date": svc_date.isoformat(),
                        "vendor": vendor.strip(),
                        "cost": cost,
                        "po_number": po.strip(),
                        "performed_by": perf.strip(),
                        "notes": notes.strip(),
                    },
                    created_by=current_profile().get("id"),
                )
                _invalidate_assets_cache()
                st.success("Maintenance saved.")
                st.rerun()

    if maintenance:
        show = pd.DataFrame(maintenance)
        for drop in ("id", "asset_id", "created_by"):
            if drop in show.columns:
                show = show.drop(columns=[drop], errors="ignore")
        st.dataframe(show, use_container_width=True, hide_index=True)
    else:
        st.caption("No maintenance records.")


def _render_documents_tab(row: dict[str, Any], *, can_edit: bool) -> None:
    aid = _safe_str(row.get("id"))
    docs = _safe_fetch("asset_documents", {"asset_id": aid}, limit=500)
    docs.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)

    if can_edit:
        with st.expander("Upload document", expanded=False):
            dtype = st.selectbox("Document type", DOCUMENT_TYPES, key=f"assets_doc_type_{aid}")
            exp = st.date_input("Expiration (optional)", value=None, key=f"assets_doc_exp_{aid}")
            notes = st.text_area("Notes", key=f"assets_doc_notes_{aid}", height=64)
            up = st.file_uploader("File", key=f"assets_doc_up_{aid}", type=["pdf", "png", "jpg", "jpeg", "doc", "docx"])
            if st.button("Upload", type="primary", key=f"assets_doc_go_{aid}", use_container_width=True):
                if not up:
                    st.error("Choose a file first.")
                else:
                    try:
                        persist_asset_document_upload(
                            asset_row=row,
                            uploaded=up,
                            document_type=dtype,
                            expiration_date=exp,
                            notes=notes,
                            uploaded_by=current_profile().get("id"),
                        )
                        st.success("Document uploaded.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Upload failed: {exc}")

    if not docs:
        st.caption("No documents uploaded.")
        return
    for i, doc in enumerate(docs):
        fp = _safe_str(doc.get("file_path"))
        fn = _safe_str(doc.get("file_name")) or Path(fp).name or "document"
        ref = create_signed_url(fp, expires_in=3600) if fp else ""
        c1, c2 = st.columns([3, 1])
        with c1:
            st.markdown(f"**{html.escape(fn)}** · {_safe_str(doc.get('document_type')) or '—'}")
        with c2:
            if ref and (ref.startswith("http") or Path(ref).is_file()):
                url = ref if ref.startswith("http") else Path(ref).resolve().as_uri()
                st.link_button("Open", url=url, key=f"assets_doc_open_{aid}_{i}", use_container_width=True)
            else:
                st.caption("Unavailable")


def _render_assignments_tab(assignments: list[dict], job_label_by_id: dict[str, str]) -> None:
    if not assignments:
        st.caption("No assignment history.")
        return
    rows = []
    for a in assignments:
        jid = _safe_str(a.get("assigned_job_id"))
        rows.append(
            {
                "Check out": _fmt_date(a.get("check_out_at")),
                "Check in": _fmt_date(a.get("check_in_at")),
                "Assigned to": _safe_str(a.get("assigned_to")) or "—",
                "Job": job_label_by_id.get(jid, "—"),
                "Location": _safe_str(a.get("assigned_location")) or "—",
                "Notes": _safe_str(a.get("notes")) or "—",
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_depreciation_tab(row: dict[str, Any]) -> None:
    st.markdown(
        summary_card_html("Depreciation", _financial_overview_rows(row)),
        unsafe_allow_html=True,
    )
    st.caption("Straight-line estimates use purchase cost and a default 7-year life when salvage is not stored.")


def _render_notes_tab(row: dict[str, Any], *, can_edit: bool) -> None:
    aid = _safe_str(row.get("id"))
    if can_edit:
        notes = st.text_area("Notes", value=_safe_str(row.get("notes")), height=140, key=f"assets_notes_{aid}")
        if st.button("Save notes", type="primary", key=f"assets_notes_save_{aid}", use_container_width=True):
            update_rows_admin("assets", {"notes": notes.strip()}, {"id": row["id"]})
            _invalidate_assets_cache()
            st.success("Notes saved.")
            st.rerun()
    else:
        st.write(_safe_str(row.get("notes")) or "—")


def _render_activity_tab(
    *,
    maintenance: list[dict],
    assignments: list[dict],
    inspections: list[dict],
) -> None:
    events = _build_activity_events(
        maintenance=maintenance,
        assignments=assignments,
        inspections=inspections,
    )
    if not events:
        st.caption("No activity recorded.")
        return
    for ev in events[:40]:
        st.markdown(
            f"**{_fmt_date(ev.get('when'))}** — {html.escape(ev.get('label') or '')}  \n"
            f"<span style='color:#6b7280;font-size:0.8rem;'>{html.escape(ev.get('detail') or '')}</span>",
            unsafe_allow_html=True,
        )


def _render_asset_detail_panel(
    row: dict[str, Any],
    *,
    can_edit: bool,
    can_delete: bool,
    job_label_by_id: dict[str, str],
    embedded: bool = False,
) -> None:
    aid = _safe_str(row.get("id"))
    maintenance = _safe_fetch("asset_maintenance", {"asset_id": aid}, limit=500)
    maintenance.sort(key=lambda r: str(r.get("service_date") or ""), reverse=True)
    assignments = _safe_fetch("asset_assignments", {"asset_id": aid}, limit=500)
    assignments.sort(key=lambda r: str(r.get("check_out_at") or r.get("created_at") or ""), reverse=True)
    inspections = _safe_fetch("asset_inspections", {"asset_id": aid}, limit=500)
    documents = _safe_fetch("asset_documents", {"asset_id": aid}, limit=200)

    tab_key = f"assets_detail_tab_{aid}"
    st.session_state.setdefault(tab_key, "Overview")
    active_tab = str(st.session_state.get(tab_key) or "Overview")
    if active_tab not in _ASSET_TABS:
        active_tab = "Overview"

    wrap_open = '<div class="ips-assets-detail-wrap">' if embedded else ""
    wrap_close = "</div>" if embedded else ""
    if embedded:
        st.markdown(wrap_open, unsafe_allow_html=True)
    else:
        with st.container(border=True):
            st.markdown('<span class="ips-assets-detail-anchor"></span>', unsafe_allow_html=True)

    st.markdown('<div class="ips-assets-detail-top">', unsafe_allow_html=True)
    top_l, top_m, top_r = st.columns([2.1, 3.2, 1.55], gap="medium")
    with top_l:
        st.markdown(
            detail_header_html(
                asset_id=_disp(row.get("asset_id")),
                asset_name=_disp(row.get("asset_name")),
                status=_safe_str(row.get("status")),
            ),
            unsafe_allow_html=True,
        )
    with top_m:
        st.markdown(
            detail_meta_strip_html(
                [
                    ("Category", _disp(row.get("category"))),
                    ("Location", _disp(row.get("location"))),
                    ("Department", _disp(row.get("department"))),
                    ("Serial Number", _disp(row.get("serial_number"))),
                    ("Acquired Date", _fmt_date(row.get("purchase_date"))),
                    ("Current Value", _money(row.get("current_value"))),
                ]
            ),
            unsafe_allow_html=True,
        )
    with top_r:
        st.markdown('<div class="ips-assets-detail-actions">', unsafe_allow_html=True)
        if can_edit and st.button("✏️ Edit", key=f"assets_det_edit_{aid}", use_container_width=True):
            st.session_state["asset_view_mode"] = "edit"
            st.session_state["selected_asset_id"] = aid
            st.session_state["asset_return_to"] = "asset_database"
            st.session_state[IPS_NAV_PENDING_KEY] = "Asset Manager"
            st.rerun()
        st.markdown('<div class="ips-assets-maint-primary">', unsafe_allow_html=True)
        if can_edit and st.button("🔧 Maintenance", type="primary", key=f"assets_det_maint_{aid}", use_container_width=True):
            st.session_state[tab_key] = "Maintenance"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        more_c, collapse_c = st.columns(2, gap="small")
        with more_c:
            with st.popover("More", use_container_width=True):
                if st.button("Open full profile", key=f"assets_det_more_profile_{aid}", use_container_width=True):
                    st.session_state["asset_detail_id"] = aid
                    st.session_state[IPS_NAV_PENDING_KEY] = "Asset Detail"
                    st.rerun()
                if st.button("Asset Scanner", key=f"assets_det_more_scan_{aid}", use_container_width=True):
                    st.session_state[IPS_NAV_PENDING_KEY] = "Asset Scanner"
                    st.rerun()
                if can_delete and st.button("Delete asset", key=f"assets_det_del_{aid}", use_container_width=True):
                    blocked, has_hist = _asset_delete_dependency_state(aid)
                    if blocked:
                        st.error("Cannot delete while checked out.")
                    elif has_hist:
                        payload: dict[str, Any] = {}
                        if "is_active" in row:
                            payload["is_active"] = False
                        if "status" in row:
                            payload["status"] = "Inactive"
                        if not payload:
                            payload = {"status": "Inactive"}
                        try:
                            update_rows_admin("assets", payload, {"id": aid})
                            st.warning("Asset has history and was deactivated instead.")
                            _invalidate_assets_cache()
                            st.session_state.pop("assets_selected_id", None)
                            st.rerun()
                        except Exception as exc:
                            st.error(str(exc))
                    else:
                        try:
                            delete_rows_admin("assets", {"id": aid})
                            st.success("Asset deleted.")
                            _invalidate_assets_cache()
                            st.session_state.pop("assets_selected_id", None)
                            st.rerun()
                        except Exception as exc:
                            st.error(str(exc))
        with collapse_c:
            if st.button("▴", key=f"assets_det_collapse_{aid}", help="Collapse panel", use_container_width=True):
                st.session_state["assets_detail_collapsed"] = True
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    active_tab = _render_tab_bar(aid, active_tab)

    if active_tab == "Overview":
        _render_overview_tab(row, maintenance=maintenance)
    elif active_tab == "Maintenance":
        _render_maintenance_tab(row, maintenance, can_edit=can_edit)
    elif active_tab == "Documents":
        _render_documents_tab(row, can_edit=can_edit)
    elif active_tab == "Assignments":
        _render_assignments_tab(assignments, job_label_by_id)
    elif active_tab == "Depreciation":
        _render_depreciation_tab(row)
    elif active_tab == "Notes":
        _render_notes_tab(row, can_edit=can_edit)
    else:
        _render_activity_tab(
            maintenance=maintenance,
            assignments=assignments,
            inspections=inspections,
        )
    _ = documents  # fetched for future inline doc counts

    if embedded:
        st.markdown(wrap_close, unsafe_allow_html=True)


def render_assets_page() -> None:
    """Main Asset Database (Assets) page entry."""
    inject_asset_workflow_mobile_css()
    ensure_narrow_viewport_detected()
    inject_assets_page_styles()

    st.markdown('<span class="ips-assets-page ips-page-shell-marker"></span>', unsafe_allow_html=True)

    can_add = current_role() in {"admin", "manager"}
    can_edit = current_role() in {"admin", "manager", "pm"}
    can_delete = current_role() in {"admin", "manager"}

    if "asset_db_add_mode" not in st.session_state:
        st.session_state["asset_db_add_mode"] = False

    if can_add and st.session_state.get("asset_db_add_mode"):
        if st.button("← Back to Assets", key="assets_intake_back", use_container_width=True):
            st.session_state["asset_db_add_mode"] = False
            st.rerun()
        st.subheader("New asset")
        st.caption("Intake: photos, review, duplicate check, then save.")
        render_asset_intake_form()
        return

    rows = _cached_assets_rows()
    job_label_by_id = _cached_jobs_labels()
    df = prepare_assets_dataframe(rows)
    row_lookup = _row_dict_by_id(rows)

    filtered = _apply_filters(df)
    _render_header(can_add=can_add, export_df=filtered)
    _render_filters(df)

    if filtered.empty:
        st.info("No assets match your filters.")
        if can_add:
            st.caption("Use **+ New Asset** to add equipment via intake.")
        return

    selected_id = _safe_str(st.session_state.get("assets_selected_id"))
    sel_row = row_lookup.get(selected_id) if selected_id else None
    if selected_id and not sel_row:
        st.session_state.pop("assets_selected_id", None)
        selected_id = ""
        sel_row = None
    if not selected_id and not filtered.empty:
        first_id = _safe_str(filtered.iloc[0].get("id"))
        if first_id and first_id in row_lookup:
            st.session_state["assets_selected_id"] = first_id
            selected_id = first_id
            sel_row = row_lookup[first_id]

    _render_assets_table(
        filtered,
        row_lookup,
        selected_id=selected_id,
        sel_row=sel_row,
        can_edit=can_edit,
        can_delete=can_delete,
        job_label_by_id=job_label_by_id,
    )
