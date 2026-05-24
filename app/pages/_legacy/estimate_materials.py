"""Estimate detail — Materials tab (line items for the active estimate)."""

from __future__ import annotations

import html
import math
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pandas as pd
import streamlit as st

try:
    from app.auth import current_profile, current_role
    from app.db import (
        create_signed_url,
        fetch_by_match,
        fetch_by_match_admin,
        fetch_one,
        fetch_table,
        fetch_table_admin,
        insert_row_admin,
        update_rows_admin,
    )
    from app.estimate.calculations import _D0, _dec, _q2, compute_totals, money, money_db, money_str
    from app.estimate.customer_job import (
        _fetch_customers_for_editor,
        resolve_estimate_linked_job,
    )
    from app.estimate.defaults import (
        _estimate_table_column_names,
        ensure_numeric_defaults,
        merge_estimate_narrative_scalars_from_row,
        merge_estimate_row_scalar_fields_into_editor,
        parse_estimate_json_bytes,
    )
    from app.estimate.editor import (
        _filter_materials_df_for_category,
        _material_selectbox_label,
        _materials_catalog_to_add_dataframe,
        ensure_state,
    )
    from app.estimate.equipment import load_estimate_equipment_from_assets
    from app.estimate.persistence import persist_estimate
    from app.estimate.proposal_exports import _proposal_export_kwargs
    from app.estimate.proposal_preview_tab import (
        build_proposal_tab_estimate_data,
        render_proposal_export_actions,
    )
    from app.pages.estimates import _fetch_one_estimate_row, _load_estimate_into_session
    from app.services.estimate_materials_catalog import (
        cached_estimate_materials_catalog_rows,
        clear_estimate_materials_catalog_cache,
        import_inventory_materials_into_estimate_catalog,
    )
    from app.services.job_service import job_number_display
    from app.ui import IPS_NAV_PENDING_KEY
    from app.ui.estimate_detail_shell import (
        inject_estimate_detail_styles,
        navigate_estimate_tab,
        render_breadcrumb,
        render_detail_header,
        render_estimate_detail_marker,
        render_info_card,
        render_tab_bar,
    )
    from app.ui.modal import ensure_modal_styles, modal_wide_marker
    from app.ui.page_shell import inject_ips_dashboard_layout
except ImportError:
    from auth import current_profile, current_role  # type: ignore
    from db import (  # type: ignore
        create_signed_url,
        fetch_by_match,
        fetch_by_match_admin,
        fetch_one,
        fetch_table,
        fetch_table_admin,
        insert_row_admin,
        update_rows_admin,
    )
    from estimate.calculations import _D0, _dec, _q2, compute_totals, money, money_db, money_str  # type: ignore
    from estimate.customer_job import _fetch_customers_for_editor, resolve_estimate_linked_job  # type: ignore
    from estimate.defaults import (  # type: ignore
        _estimate_table_column_names,
        ensure_numeric_defaults,
        merge_estimate_narrative_scalars_from_row,
        merge_estimate_row_scalar_fields_into_editor,
        parse_estimate_json_bytes,
    )
    from estimate.editor import (  # type: ignore
        _filter_materials_df_for_category,
        _material_selectbox_label,
        _materials_catalog_to_add_dataframe,
        ensure_state,
    )
    from estimate.equipment import load_estimate_equipment_from_assets  # type: ignore
    from estimate.persistence import persist_estimate  # type: ignore
    from estimate.proposal_exports import _proposal_export_kwargs  # type: ignore
    from estimate.proposal_preview_tab import build_proposal_tab_estimate_data, render_proposal_export_actions  # type: ignore
    from pages.estimates import _fetch_one_estimate_row, _load_estimate_into_session  # type: ignore
    from services.estimate_materials_catalog import (  # type: ignore
        cached_estimate_materials_catalog_rows,
        clear_estimate_materials_catalog_cache,
        import_inventory_materials_into_estimate_catalog,
    )
    from services.job_service import job_number_display  # type: ignore
    from ui import IPS_NAV_PENDING_KEY  # type: ignore
    from ui.estimate_detail_shell import (  # type: ignore
        inject_estimate_detail_styles,
        navigate_estimate_tab,
        render_breadcrumb,
        render_detail_header,
        render_estimate_detail_marker,
        render_info_card,
        render_tab_bar,
    )
    from ui.modal import ensure_modal_styles, modal_wide_marker  # type: ignore
    from ui.page_shell import inject_ips_dashboard_layout  # type: ignore

_EM_DLG_KEY = "em_page_dlg"
_EM_PAGE_SIZE = 10
_DEFAULT_MATERIAL_NOTES = (
    "All materials are estimated based on current supplier pricing and availability."
)


def _admin_read() -> bool:
    return current_role() in {"admin", "manager", "pm"}


@st.cache_data(ttl=60, show_spinner=False)
def _cached_estimates_picklist(_admin: bool, _v: int) -> list[dict[str, Any]]:
    try:
        if _admin:
            return list(fetch_table_admin("estimates", limit=1000, order_by="updated_at") or [])
        return list(fetch_table("estimates", limit=1000, order_by="updated_at") or [])
    except Exception:
        return []


@st.cache_data(ttl=120, show_spinner=False)
def _cached_labor_rates() -> list[dict[str, Any]]:
    try:
        return list(fetch_table("labor_rates", limit=1000, order_by="classification") or [])
    except Exception:
        return []


def _safe_col(row: dict[str, Any], *keys: str, default: str = "") -> str:
    for k in keys:
        v = row.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    return default


def _line_unit_cost(line: dict, catalog_row: dict | None, markup_dec) -> Any:
    if line.get("unit_cost") is not None:
        return _dec(line.get("unit_cost") or 0)
    if catalog_row:
        sell = _dec(catalog_row.get("sell_price") or 0)
        if sell > _D0:
            return sell
        purchase = _dec(catalog_row.get("purchase_price") or 0)
        return purchase * (Decimal("1") + markup_dec) if purchase > _D0 else _D0
    return _D0


def _build_display_rows(
    est: dict,
    material_map: dict[str, dict],
    *,
    markup_dec,
    search_q: str,
    group_by: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, line in enumerate(est.get("materials") or []):
        if not isinstance(line, dict):
            continue
        item_key = _safe_col(line, "item", "item_key")
        cat_row = material_map.get(item_key) or {}
        desc = _safe_col(line, "description") or _safe_col(cat_row, "description", "material_name") or item_key
        category = _safe_col(line, "category") or _safe_col(cat_row, "category") or "Uncategorized"
        unit = _safe_col(line, "unit") or _safe_col(cat_row, "unit") or "EA"
        sku = _safe_col(cat_row, "vendor_item_number", "item_key") or item_key
        qty = _dec(line.get("qty") or line.get("quantity") or 0)
        unit_cost = _line_unit_cost(line, cat_row or None, markup_dec)
        total = _q2(qty * unit_cost)
        rows.append(
            {
                "idx": idx,
                "item_key": item_key,
                "item_num": sku,
                "description": desc,
                "category": category,
                "qty": qty,
                "unit": unit,
                "unit_cost": unit_cost,
                "total_cost": total,
            }
        )
    q = str(search_q or "").strip().lower()
    if q:
        rows = [
            r
            for r in rows
            if q in str(r.get("description") or "").lower()
            or q in str(r.get("item_key") or "").lower()
            or q in str(r.get("item_num") or "").lower()
            or q in str(r.get("category") or "").lower()
        ]
    if group_by == "Category":
        rows.sort(key=lambda r: (str(r.get("category") or ""), str(r.get("description") or "")))
    else:
        rows.sort(key=lambda r: str(r.get("description") or ""))
    return rows


def _persist_estimate_state(est: dict, *, note: str = "Materials updated") -> bool:
    eid = str(st.session_state.get("loaded_estimate_id") or "").strip()
    if not eid or not est.get("customer_id"):
        return False
    try:
        materials_catalog = cached_estimate_materials_catalog_rows()
        labor_rates = _cached_labor_rates()
        equipment_pricing = load_estimate_equipment_from_assets()
        totals = compute_totals(est, materials_catalog, labor_rates, equipment_pricing)
        payload: dict[str, Any] = {
            "quote_number": str(est.get("quote_number") or "").strip(),
            "customer_id": est.get("customer_id"),
            "customer_contact_id": est.get("customer_contact_id"),
            "job_id": est.get("job_id"),
            "estimator_user_id": current_profile().get("id"),
            "status": est.get("status", "draft"),
            "proposal_total": money_db(totals["proposal_total"]),
            "final_bid": money_db(totals["final_bid"]),
            "material_sell_basis": money_db(totals["material_sell_basis"]),
            "labor_total": money_db(totals["labor_total"]),
            "equipment_total": money_db(totals["equipment_total"]),
            "travel_total": money_db(totals["travel_total"]),
            "overhead_total": money_db(totals["overhead_total"]),
            "profit_total": money_db(totals["profit_total"]),
            "contingency_total": money_db(totals["contingency_total"]),
            "sales_tax_total": money_db(totals["sales_tax_total"]),
            "scope_of_work": est.get("scope_of_work", ""),
            "exclusions": est.get("exclusions", ""),
            "additional_charges": est.get("additional_charges", ""),
            "customer_responsibilities": est.get("customer_responsibilities", ""),
            "job_received": bool(est.get("job_received", False)),
            "po_number": est.get("po_number", ""),
            "po_date": est.get("po_date") or None,
            "po_amount": float(est.get("po_amount", 0) or 0),
            "estimate_json": est,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        cols = _estimate_table_column_names()
        if "estimate_description" in cols:
            ed = str(est.get("estimate_description") or "").strip()
            payload["estimate_description"] = ed[:500] if ed else None
        persist_estimate(payload, est, note)
        st.session_state["est_data_version"] = int(st.session_state.get("est_data_version", 0)) + 1
        return True
    except Exception as exc:
        st.error(f"Could not save estimate: {exc}")
        return False


def _on_dismiss_dlg() -> None:
    st.session_state.pop(_EM_DLG_KEY, None)


@st.dialog("Add from inventory", width="large", on_dismiss=_on_dismiss_dlg)
def _dialog_add_from_inventory(est: dict, materials_df: pd.DataFrame, material_map: dict, *, is_locked: bool) -> None:
    ensure_modal_styles()
    modal_wide_marker()
    st.markdown("### Add from inventory")
    cat_options = ["All"] + sorted(materials_df["category"].dropna().astype(str).unique().tolist()) if not materials_df.empty else ["All"]
    sel_cat = st.selectbox("Category", options=cat_options, key="em_dlg_inv_cat")
    search_q = st.text_input("Search materials", key="em_dlg_inv_search", placeholder="Search materials...")
    filtered = _filter_materials_df_for_category(materials_df, selected_category=sel_cat, search_query=search_q)
    mat_keys = filtered["item_key"].tolist() if not filtered.empty else []
    label_by_key = {str(row["item_key"]): _material_selectbox_label(row) for _, row in filtered.iterrows()}
    if not mat_keys:
        st.info("No pricing guide items match this filter.")
        return
    pick = st.selectbox(
        "Material",
        options=mat_keys,
        format_func=lambda ik: label_by_key.get(ik, ik),
        key="em_dlg_inv_pick",
    )
    qty = st.number_input("Qty", min_value=0.0, step=1.0, value=1.0, key="em_dlg_inv_qty")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Add line", type="primary", use_container_width=True, key="em_dlg_inv_add", disabled=is_locked):
            est.setdefault("materials", [])
            est["materials"] = list(est.get("materials") or []) + [{"item": str(pick), "qty": float(qty or 0)}]
            st.session_state.pop(_EM_DLG_KEY, None)
            _persist_estimate_state(est)
            st.rerun()
    with c2:
        if st.button("Cancel", use_container_width=True, key="em_dlg_inv_cancel"):
            st.session_state.pop(_EM_DLG_KEY, None)
            st.rerun()


@st.dialog("Add custom item", width="large", on_dismiss=_on_dismiss_dlg)
def _dialog_add_custom_item(est: dict, *, is_locked: bool) -> None:
    ensure_modal_styles()
    modal_wide_marker()
    st.markdown("### Add custom item")
    with st.form("em_dlg_custom_form", clear_on_submit=True):
        item_key = st.text_input("Item # / code", key="em_dlg_custom_key")
        desc = st.text_input("Description", key="em_dlg_custom_desc")
        cat = st.text_input("Category", value="Custom", key="em_dlg_custom_cat")
        unit = st.text_input("Unit", value="EA", key="em_dlg_custom_unit")
        qty = st.number_input("Qty", min_value=0.0, step=1.0, value=1.0, key="em_dlg_custom_qty")
        unit_cost = st.number_input("Unit cost", min_value=0.0, step=0.01, value=0.0, key="em_dlg_custom_cost")
        submitted = st.form_submit_button("Add line", type="primary", disabled=is_locked)
    if st.button("Cancel", key="em_dlg_custom_cancel"):
        st.session_state.pop(_EM_DLG_KEY, None)
        st.rerun()
    if submitted:
        key = str(item_key or "").strip() or f"custom-{len(est.get('materials') or []) + 1}"
        est.setdefault("materials", [])
        est["materials"] = list(est.get("materials") or []) + [
            {
                "item": key,
                "qty": float(qty or 0),
                "description": str(desc or "")[:2000],
                "category": str(cat or "Custom")[:200],
                "unit": str(unit or "EA")[:32],
                "unit_cost": float(unit_cost or 0),
                "_custom": True,
            }
        ]
        st.session_state.pop(_EM_DLG_KEY, None)
        _persist_estimate_state(est)
        st.rerun()


@st.dialog("Add material", width="large", on_dismiss=_on_dismiss_dlg)
def _dialog_add_material(est: dict, materials_df: pd.DataFrame, *, is_locked: bool) -> None:
    _dialog_add_from_inventory(est, materials_df, {}, is_locked=is_locked)


@st.dialog("Import materials JSON", width="large", on_dismiss=_on_dismiss_dlg)
def _dialog_import_json(est: dict, *, is_locked: bool) -> None:
    ensure_modal_styles()
    modal_wide_marker()
    st.markdown("### Import materials from JSON")
    st.caption("Upload an IPS estimate export or JSON with a `materials` array (`item` + `qty`).")
    up = st.file_uploader("JSON file", type=["json"], key="em_dlg_import_json")
    if st.button("Cancel", key="em_dlg_import_cancel"):
        st.session_state.pop(_EM_DLG_KEY, None)
        st.rerun()
    if up and st.button("Merge materials", type="primary", key="em_dlg_import_merge", disabled=is_locked):
        try:
            parsed, _ = parse_estimate_json_bytes(up.getvalue(), up.name)
            incoming = parsed.get("materials") if isinstance(parsed, dict) else None
            if not isinstance(incoming, list):
                st.error("No `materials` array found in file.")
                return
            est.setdefault("materials", [])
            est["materials"] = list(est.get("materials") or []) + [x for x in incoming if isinstance(x, dict)]
            st.session_state.pop(_EM_DLG_KEY, None)
            _persist_estimate_state(est, note="Imported materials from JSON")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))


def _render_materials_table(
    est: dict,
    display_rows: list[dict[str, Any]],
    *,
    is_locked: bool,
    page: int,
) -> None:
    total = len(display_rows)
    pages = max(1, math.ceil(total / _EM_PAGE_SIZE))
    page = max(0, min(page, pages - 1))
    start = page * _EM_PAGE_SIZE
    chunk = display_rows[start : start + _EM_PAGE_SIZE]

    if not chunk:
        st.markdown('<p class="ips-est-empty">No materials match your filters.</p>', unsafe_allow_html=True)
    else:
        body_rows: list[str] = []
        for r in chunk:
            idx = int(r["idx"])
            body_rows.append(
                "<tr>"
                f'<td><span class="ips-est-drag">⋮⋮</span></td>'
                f'<td><span class="ips-est-item-link">{html.escape(str(r.get("item_num") or ""))}</span></td>'
                f"<td>{html.escape(str(r.get('description') or ''))}</td>"
                f"<td>{html.escape(str(r.get('category') or ''))}</td>"
                f"<td>{html.escape(money_str(r.get('qty')))}</td>"
                f"<td>{html.escape(str(r.get('unit') or ''))}</td>"
                f"<td>{html.escape(money(r.get('unit_cost')))}</td>"
                f"<td>{html.escape(money(r.get('total_cost')))}</td>"
                f"<td></td>"
                "</tr>"
            )
        st.markdown(
            '<table class="ips-est-mat-table"><thead><tr>'
            "<th></th><th>Item #</th><th>Description</th><th>Category</th>"
            "<th>Qty</th><th>Unit</th><th>Unit Cost</th><th>Total Cost</th><th>Actions</th>"
            f"</tr></thead><tbody>{''.join(body_rows)}</tbody></table>",
            unsafe_allow_html=True,
        )
        for r in chunk:
            idx = int(r["idx"])
            c1, c2, c3, c4, c5, c6, c7, c8, c9 = st.columns([0.35, 0.9, 2.2, 1.0, 0.55, 0.55, 0.85, 0.85, 0.9])
            with c9:
                b1, b2 = st.columns(2)
                with b1:
                    if st.button("✎", key=f"em_mat_edit_{idx}", disabled=is_locked, help="Edit"):
                        st.session_state["est_material_edit_idx"] = idx
                        st.session_state[_EM_DLG_KEY] = "edit"
                        st.rerun()
                with b2:
                    if st.button("🗑", key=f"em_mat_del_{idx}", disabled=is_locked, help="Delete"):
                        lines = list(est.get("materials") or [])
                        if 0 <= idx < len(lines):
                            est["materials"] = [x for j, x in enumerate(lines) if j != idx]
                            if st.session_state.get("est_material_edit_idx") == idx:
                                st.session_state.pop("est_material_edit_idx", None)
                            _persist_estimate_state(est)
                            st.rerun()

    end = min(start + _EM_PAGE_SIZE, total) if total else 0
    st.caption(f"Showing {start + 1 if total else 0} to {end} of {total} materials")
    if pages > 1:
        pc = st.columns(min(pages, 6) + 1)
        for p in range(min(pages, 5)):
            with pc[p]:
                if st.button(str(p + 1), key=f"em_mat_page_{p}", type="primary" if p == page else "secondary"):
                    st.session_state["em_mat_page"] = p
                    st.rerun()
        with pc[min(pages, 5)]:
            if page + 1 < pages and st.button("→", key="em_mat_page_next"):
                st.session_state["em_mat_page"] = page + 1
                st.rerun()


def _render_summary_card(
    est: dict,
    totals: dict,
    *,
    is_locked: bool,
) -> None:
    controls = est.get("controls", {}) or {}
    markup_pct = float(controls.get("material_markup_pct", 0) or 0)
    freight = float(controls.get("material_freight", 0) or 0)
    tax_pct = float(controls.get("sales_tax_pct", 0) or 0)
    material_total = totals.get("material_sell_basis", _D0)
    tax_amt = _q2(_dec(material_total) * _dec(tax_pct))
    subtotal = _q2(_dec(material_total) + _dec(freight) + tax_amt)
    markup_amt = _q2(_dec(material_total) * _dec(markup_pct))
    with_markup = _q2(_dec(material_total) + markup_amt)

    st.markdown('<div class="ips-est-summary-card">', unsafe_allow_html=True)
    st.markdown('<p class="ips-est-card-title">Materials Summary</p>', unsafe_allow_html=True)

    def _row(label: str, val: str, *, bold: bool = False) -> None:
        w = "strong" if bold else "span"
        st.markdown(
            f'<div class="ips-est-summary-row"><span>{html.escape(label)}</span>'
            f"<{w}>{html.escape(val)}</{w}></div>",
            unsafe_allow_html=True,
        )

    _row("Material Total", money(material_total))
    freight_val = st.number_input(
        "Freight",
        min_value=0.0,
        step=10.0,
        value=freight,
        key="em_summary_freight",
        disabled=is_locked,
        label_visibility="collapsed",
    )
    if not is_locked and freight_val != freight:
        controls["material_freight"] = float(freight_val or 0)
        est["controls"] = controls

    _row("Freight", money(freight_val))
    _row("Tax", money(tax_amt))
    st.markdown('<div class="ips-est-summary-divider"></div>'.replace("div", "div"), unsafe_allow_html=True)
    _row("Total", money(subtotal))

    st.markdown('<div class="ips-est-markup-box">', unsafe_allow_html=True)
    st.markdown("**Materials Markup**")
    mk_type = st.selectbox(
        "Markup type",
        options=["Percentage", "Fixed"],
        index=0,
        key="em_summary_markup_type",
        label_visibility="collapsed",
    )
    if mk_type == "Percentage":
        new_pct = st.number_input(
            "Markup %",
            min_value=0.0,
            step=0.5,
            value=markup_pct * 100.0 if markup_pct <= 1.0 else markup_pct,
            key="em_summary_markup_pct",
            disabled=is_locked,
        )
        if not is_locked:
            controls["material_markup_pct"] = float(new_pct or 0) / 100.0
            est["controls"] = controls
            markup_pct = controls["material_markup_pct"]
    _row("Markup Amount", money(markup_amt))
    _row("Markup Total", money(with_markup))
    st.markdown('<div class="ips-est-summary-divider"></div>'.replace("div", "div"), unsafe_allow_html=True)
    _row("Materials w/ Markup", money(with_markup), bold=True)
    st.markdown("</div></div>", unsafe_allow_html=True)

    if not is_locked and st.button("Save summary", key="em_summary_save", type="primary", use_container_width=True):
        _persist_estimate_state(est, note="Updated materials summary controls")
        st.rerun()


def _fetch_estimate_attachments(estimate_id: str) -> list[dict[str, Any]]:
    eid = str(estimate_id or "").strip()
    if not eid:
        return []
    try:
        fn = fetch_by_match_admin if _admin_read() else fetch_by_match
        return list(
            fn(
                "attachments",
                {"estimate_id": eid},
                limit=200,
            )
            or []
        )
    except Exception:
        return []


def _render_notes_and_documents(est: dict, estimate_id: str) -> None:
    notes = str(est.get("material_notes") or est.get("additional_charges") or "").strip()
    if not notes:
        notes = _DEFAULT_MATERIAL_NOTES
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        st.markdown('<div class="ips-est-surface-card">', unsafe_allow_html=True)
        st.markdown('<p class="ips-est-card-title">Material Notes</p>', unsafe_allow_html=True)
        st.markdown(f"<p style='font-size:0.88rem;color:#334155;'>{html.escape(notes)}</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="ips-est-surface-card">', unsafe_allow_html=True)
        st.markdown('<p class="ips-est-card-title">Linked Documents</p>', unsafe_allow_html=True)
        atts = _fetch_estimate_attachments(estimate_id)
        material_atts = [
            a
            for a in atts
            if str(a.get("category") or "").lower() in {
                "quote_attachment",
                "import_source",
                "material",
                "spec",
                "specification",
            }
        ]
        if not material_atts:
            st.markdown(
                '<p class="ips-est-empty">No linked material or specification documents yet.</p>',
                unsafe_allow_html=True,
            )
        else:
            for i, att in enumerate(material_atts):
                nm = str(att.get("file_name") or "file")
                uploaded = str(att.get("uploaded_at") or att.get("created_at") or "")[:16].replace("T", " ")
                signed = create_signed_url(att.get("storage_path") or "")
                st.markdown(
                    f'<div class="ips-est-doc-row"><span class="ips-est-doc-icon">📄</span>'
                    f"<div><strong>{html.escape(nm)}</strong><br>"
                    f'<span style="font-size:0.76rem;color:#64748b;">{html.escape(uploaded)}</span></div></div>'.replace(
                        "div", "div"
                    ),
                    unsafe_allow_html=True,
                )
                b1, b2 = st.columns(2)
                with b1:
                    if signed:
                        st.link_button("Download", signed, key=f"em_doc_dl_{i}", use_container_width=True)
                with b2:
                    if signed:
                        st.link_button("View", signed, key=f"em_doc_view_{i}", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)


def _render_estimate_picker() -> None:
    st.markdown("### Select an estimate")
    v = int(st.session_state.get("est_data_version", 0))
    rows = _cached_estimates_picklist(_admin_read(), v)
    if not rows:
        st.info("No estimates found. Create one from **Estimates**.")
        if st.button("Go to Estimates", type="primary", key="em_pick_go_est"):
            st.session_state[IPS_NAV_PENDING_KEY] = "Estimates"
            st.rerun()
        return
    labels: list[str] = []
    by_label: dict[str, str] = {}
    for r in rows:
        qn = str(r.get("quote_number") or r.get("id") or "").strip()
        desc = str(r.get("estimate_description") or "").strip()
        lab = f"{qn} — {desc}" if desc else qn
        labels.append(lab)
        by_label[lab] = str(r.get("id") or "")
    pick = st.selectbox("Estimate", options=labels, key="em_estimate_picker")
    if st.button("Open Materials", type="primary", key="em_estimate_picker_open"):
        eid = by_label.get(pick, "")
        if eid:
            _load_estimate_into_session(eid)
            st.rerun()


def _render_export_dialog(est: dict, totals: dict, pe: dict) -> None:
    if not st.session_state.get("est_det_export_open"):
        return
    with st.expander("Export estimate", expanded=True):
        pdata = build_proposal_tab_estimate_data(
            est,
            totals,
            pe,
            docx_bytes=None,
            pdf_bytes=None,
            word_error="",
            loaded_estimate_id=str(st.session_state.get("loaded_estimate_id") or "").strip() or None,
            is_locked=False,
        )
        render_proposal_export_actions(pdata)
        if st.button("Close", key="em_export_close"):
            st.session_state.pop("est_det_export_open", None)
            st.rerun()


def render() -> None:
    inject_ips_dashboard_layout()
    inject_estimate_detail_styles()
    render_estimate_detail_marker()

    role = current_role()
    is_locked = role not in {"admin", "manager", "pm"}
    can_catalog = role in {"admin", "manager"}

    eid = str(st.session_state.get("loaded_estimate_id") or "").strip()
    if not eid:
        _render_estimate_picker()
        if can_catalog:
            with st.expander("Pricing Guide administration (admin)", expanded=False):
                _render_catalog_admin_section()
        return

    row = _fetch_one_estimate_row(eid)
    if not row:
        st.error("Estimate could not be loaded.")
        if st.button("Choose another estimate", key="em_reload_pick"):
            st.session_state.pop("loaded_estimate_id", None)
            st.rerun()
        return

    if "estimate_editor_state" not in st.session_state:
        _load_estimate_into_session(eid)
    ensure_state()
    est: dict = st.session_state["estimate_editor_state"]
    merge_estimate_narrative_scalars_from_row(row, est)
    merge_estimate_row_scalar_fields_into_editor(row, est)
    ensure_numeric_defaults(est)

    materials_catalog = cached_estimate_materials_catalog_rows()
    materials_df = _materials_catalog_to_add_dataframe(materials_catalog)
    material_map = {
        str(m.get("item_key") or ""): m
        for m in materials_catalog
        if isinstance(m, dict) and m.get("item_key")
    }
    labor_rates = _cached_labor_rates()
    equipment_pricing = load_estimate_equipment_from_assets()
    totals = compute_totals(est, materials_catalog, labor_rates, equipment_pricing)

    customers = _fetch_customers_for_editor()
    customer_name_by_id = {str(c["id"]): str(c.get("customer_name") or "") for c in customers if c.get("id")}
    cust_name = customer_name_by_id.get(str(est.get("customer_id") or "").strip(), "")
    project = str(est.get("estimate_description") or row.get("estimate_description") or "").strip() or "—"
    qn = str(est.get("quote_number") or row.get("quote_number") or "—").strip() or "—"

    jobs: list[dict] = []
    try:
        if _admin_read():
            jobs = list(fetch_table_admin("jobs", columns="id,job_number,job_name,estimate_id", limit=5000) or [])
        else:
            jobs = list(fetch_table("jobs", columns="id,job_number,job_name,estimate_id", limit=5000) or [])
    except Exception:
        jobs = []
    linked_job_id, linked_job_row = resolve_estimate_linked_job(est, jobs, eid)
    job_label = "—"
    if linked_job_row:
        job_label = f"{job_number_display(linked_job_row.get('job_number'))} — {str(linked_job_row.get('job_name') or '').strip()}".strip(
            " —"
        )

    render_breadcrumb(quote_label=qn, tab_label="Materials")
    render_detail_header(
        quote_number=qn,
        status=str(est.get("status") or row.get("status") or "draft"),
        project_name=project,
        customer_name=cust_name,
    )
    render_info_card(
        customer_name=cust_name,
        customer_id=str(est.get("customer_id") or "").strip() or None,
        job_label=job_label,
        job_id=linked_job_id,
        estimate_date=row.get("created_at") or row.get("updated_at"),
        valid_through_base=row.get("updated_at") or row.get("created_at"),
        prepared_by=str(est.get("prepared_by_name") or "").strip() or "—",
        estimated_total=money(totals.get("final_bid", 0)),
    )

    clicked_tab = render_tab_bar(active_tab="Materials")
    if clicked_tab:
        navigate_estimate_tab(clicked_tab)

    controls = est.get("controls", {}) or {}
    markup_dec = _dec(controls.get("material_markup_pct", 0) or 0)

    st.markdown('<div class="ips-est-surface-card">', unsafe_allow_html=True)
    st.markdown('<p class="ips-est-card-title">Materials</p>', unsafe_allow_html=True)

    t1, t2, t3, t4, t5, t6, t7 = st.columns([1.4, 1.1, 1.1, 1.0, 0.5, 0.6, 0.9], gap="small")
    with t1:
        search_q = st.text_input(
            "Search",
            key="em_mat_search",
            placeholder="Search materials...",
            label_visibility="collapsed",
        )
    with t2:
        if st.button("Add from Inventory", key="em_btn_inv", use_container_width=True, disabled=is_locked):
            st.session_state[_EM_DLG_KEY] = "inventory"
            st.rerun()
    with t3:
        if st.button("Add Custom Item", key="em_btn_custom", use_container_width=True, disabled=is_locked):
            st.session_state[_EM_DLG_KEY] = "custom"
            st.rerun()
    with t4:
        st.selectbox(
            "Group by",
            options=["Category", "Description"],
            key="em_mat_group_by",
            label_visibility="visible",
        )
    with t5:
        if st.button("Import", key="em_btn_import", use_container_width=True, disabled=is_locked):
            st.session_state[_EM_DLG_KEY] = "import"
            st.rerun()
    with t7:
        if st.button("+ Add Material", key="em_btn_add_mat", type="primary", use_container_width=True, disabled=is_locked):
            st.session_state[_EM_DLG_KEY] = "add"
            st.rerun()

    group_by = str(st.session_state.get("em_mat_group_by") or "Category")
    display_rows = _build_display_rows(
        est,
        material_map,
        markup_dec=markup_dec,
        search_q=search_q,
        group_by=group_by,
    )
    page = int(st.session_state.get("em_mat_page", 0))

    left, right = st.columns([2.45, 1], gap="medium")
    with left:
        _render_materials_table(est, display_rows, is_locked=is_locked, page=page)
    with right:
        _render_summary_card(est, totals, is_locked=is_locked)

    st.markdown("</div>", unsafe_allow_html=True)

    _render_notes_and_documents(est, eid)

    dlg = str(st.session_state.get(_EM_DLG_KEY) or "").strip()
    if dlg == "inventory" or dlg == "add":
        _dialog_add_from_inventory(est, materials_df, material_map, is_locked=is_locked)
    elif dlg == "custom":
        _dialog_add_custom_item(est, is_locked=is_locked)
    elif dlg == "import":
        _dialog_import_json(est, is_locked=is_locked)
    elif dlg == "edit":
        st.session_state[IPS_NAV_PENDING_KEY] = "Estimates"
        st.session_state["estimates_view"] = "edit"
        st.session_state["estimate_editor_section"] = "Materials"
        st.session_state.pop(_EM_DLG_KEY, None)
        st.rerun()

    pe = _proposal_export_kwargs(est, customer_name_by_id, jobs)
    _render_export_dialog(est, totals, pe)

    if can_catalog:
        with st.expander("Pricing Guide administration", expanded=False):
            _render_catalog_admin_section()


def _render_catalog_admin_section() -> None:
    """Preserve global ``estimate_materials`` catalog tools for admins."""
    st.caption("Manage the shared quote catalog used by all estimates.")
    if st.button("Sync pricing from inventory", key="em_cat_sync"):
        try:
            from app.services.estimate_materials_catalog import sync_estimate_material_pricing_from_inventory
        except ImportError:
            from services.estimate_materials_catalog import sync_estimate_material_pricing_from_inventory  # type: ignore

        n = sync_estimate_material_pricing_from_inventory(
            fetch_table=fetch_table,
            fetch_table_admin=fetch_table_admin,
            update_rows_admin=update_rows_admin,
        )
        clear_estimate_materials_catalog_cache()
        st.success(f"Updated {n} linked row(s).")
        st.rerun()
    if st.button("Import inventory → catalog", key="em_cat_import"):
        result = import_inventory_materials_into_estimate_catalog(
            fetch_table=fetch_table,
            insert_row_admin=insert_row_admin,
            update_rows_admin=update_rows_admin,
            fetch_table_admin=fetch_table_admin,
            dry_run=False,
            scope="all_active",
        )
        clear_estimate_materials_catalog_cache()
        st.success("Catalog import finished.")
        st.markdown(result.summary_text())
