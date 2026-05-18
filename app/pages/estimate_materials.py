"""Estimate Materials page — professional estimate detail view.

When an estimate is loaded (``loaded_estimate_id`` / ``selected_estimate_id`` in
session state) this page renders a full estimate detail UI with:

  • Breadcrumb header
  • Estimate title / status / project / customer header with action buttons
  • Estimate info summary card (client, job, dates, prepared-by, total)
  • Horizontal navigation tabs (Overview, Materials active, Labor, Equipment, …)
  • Materials table with search, add controls, group-by, inline edit/delete
  • Right-side Materials Summary card with markup controls
  • Material Notes card and Linked Documents card

When no estimate is loaded the page falls back to the original catalog management
view so the existing workflow (import from inventory, add/edit catalog items) is
always accessible from the sidebar.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Backend imports (dual path: app.* or bare for Streamlit multi-page)
# ---------------------------------------------------------------------------
try:
    from app.auth import current_role
    from app.db import (
        fetch_by_match_admin,
        fetch_one,
        fetch_table,
        fetch_table_admin,
        insert_row_admin,
        update_rows_admin,
    )
    from app.ui.catalog_inventory_display import prepare_catalog_inventory_display_df
    from app.ui.modal import ensure_modal_styles, modal_wide_marker
    from app.services.estimate_materials_catalog import (
        clear_estimate_materials_catalog_cache,
        import_inventory_materials_into_estimate_catalog,
        sync_estimate_material_pricing_from_inventory,
    )
except ImportError:
    from auth import current_role  # type: ignore
    from db import (  # type: ignore
        fetch_by_match_admin,
        fetch_one,
        fetch_table,
        fetch_table_admin,
        insert_row_admin,
        update_rows_admin,
    )
    from ui.catalog_inventory_display import prepare_catalog_inventory_display_df  # type: ignore
    from ui.modal import ensure_modal_styles, modal_wide_marker  # type: ignore
    from services.estimate_materials_catalog import (  # type: ignore
        clear_estimate_materials_catalog_cache,
        import_inventory_materials_into_estimate_catalog,
        sync_estimate_material_pricing_from_inventory,
    )

# ---------------------------------------------------------------------------
# Session state / dialog keys
# ---------------------------------------------------------------------------
_EM_DLG_KEY = "em_catalog_dlg"          # catalog management dialog
_EM_EST_DLG_KEY = "em_est_mat_dlg"      # estimate material add/edit dialog
_EM_PAGE_KEY = "em_mat_page_num"        # materials table pagination
_EM_SEARCH_KEY = "em_mat_search"        # search query
_EM_GROUP_KEY = "em_mat_group_by"       # group-by setting
_EM_EDIT_IDX = "em_mat_edit_idx"        # row index being edited
_EM_PER_PAGE = 15                       # rows per page
_EM_ACTIVE_TAB = "em_active_tab"        # horizontal tab index
_UUID_SPLIT = re.compile(r"[\s,;]+")


# ---------------------------------------------------------------------------
# Money helpers
# ---------------------------------------------------------------------------

def _dec(v: Any) -> Decimal:
    if v is None or v == "":
        return Decimal("0")
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


def _q2(v: Any) -> Decimal:
    return _dec(v).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _money(v: Any) -> str:
    return f"${_q2(v):,.2f}"


# ---------------------------------------------------------------------------
# CSS injection
# ---------------------------------------------------------------------------

_EM_CSS_KEY = "_ips_em_page_css_v5"


def _inject_em_page_styles() -> None:
    if st.session_state.get(_EM_CSS_KEY):
        return
    st.markdown(
        """
        <style>
        /* ── Page background ── */
        .stApp,[data-testid="stAppViewContainer"]{background:#f0f2f5!important}
        section[data-testid="stMain"]{background:transparent!important}

        /* ── Breadcrumb ── */
        .em-breadcrumb{font-size:0.78rem;color:#6b7280;margin:0 0 .6rem 0;display:flex;
          align-items:center;gap:.3rem;flex-wrap:wrap}
        .em-breadcrumb a,.em-breadcrumb span.em-bc-link{color:#6b7280;text-decoration:none;
          transition:color .15s}
        .em-breadcrumb a:hover,.em-breadcrumb span.em-bc-link:hover{color:#2563eb}
        .em-breadcrumb .em-bc-sep{color:#d1d5db;font-size:.7rem}
        .em-breadcrumb .em-bc-current{color:#111827;font-weight:600}

        /* ── Page header ── */
        .em-page-header{margin:0 0 .75rem 0}
        .em-header-row1{display:flex;align-items:center;gap:.6rem;flex-wrap:wrap;
          margin-bottom:.25rem}
        .em-title{font-size:1.45rem;font-weight:800;color:#111827;margin:0;
          letter-spacing:-.02em;white-space:nowrap}
        .em-status-pill{display:inline-block;padding:.18rem .62rem;border-radius:999px;
          font-size:.72rem;font-weight:700;letter-spacing:.03em;text-transform:uppercase;
          white-space:nowrap}
        .em-status-draft{background:#e0f2fe;color:#0369a1}
        .em-status-submitted{background:#fef9c3;color:#a16207}
        .em-status-approved{background:#dcfce7;color:#166534}
        .em-status-awarded{background:#d1fae5;color:#065f46}
        .em-status-other{background:#f3f4f6;color:#374151}
        .em-header-sub{font-size:.85rem;color:#6b7280;margin:0;display:flex;
          align-items:center;gap:.35rem;flex-wrap:wrap}
        .em-header-sub .em-sep{color:#d1d5db}
        .em-header-actions{display:flex;align-items:center;gap:.5rem;flex-wrap:wrap;
          margin-left:auto}

        /* ── Info card ── */
        .em-info-card{background:#fff;border:1px solid #e5eaf2;border-radius:12px;
          padding:1rem 1.25rem;margin:0 0 .9rem 0;
          box-shadow:0 1px 3px rgba(0,0,0,.06)}
        .em-info-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));
          gap:.75rem 1.5rem}
        .em-info-cell{}
        .em-info-label{font-size:.72rem;font-weight:600;color:#6b7280;
          text-transform:uppercase;letter-spacing:.04em;margin:0 0 .18rem 0}
        .em-info-value{font-size:.9rem;font-weight:600;color:#111827;margin:0}
        .em-info-link{font-size:.75rem;color:#2563eb;cursor:pointer;margin:.1rem 0 0 0;
          text-decoration:none}
        .em-info-link:hover{text-decoration:underline}
        .em-info-total{font-size:1.35rem;font-weight:800;color:#111827}

        /* ── Nav tabs ── */
        .em-tabs-bar{display:flex;align-items:flex-end;gap:0;border-bottom:2px solid #e5eaf2;
          margin:0 0 1rem 0;overflow-x:auto;-webkit-overflow-scrolling:touch}
        .em-tab{padding:.55rem .9rem;font-size:.82rem;font-weight:600;color:#6b7280;
          cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-2px;
          white-space:nowrap;transition:color .15s,border-color .15s}
        .em-tab:hover{color:#2563eb}
        .em-tab.em-tab-active{color:#2563eb;border-bottom:2px solid #2563eb}

        /* ── Section card ── */
        .em-card{background:#fff;border:1px solid #e5eaf2;border-radius:12px;
          padding:1.1rem 1.15rem;margin:0 0 .85rem 0;
          box-shadow:0 1px 4px rgba(0,0,0,.05)}
        .em-card-title{font-size:.92rem;font-weight:700;color:#111827;margin:0 0 .7rem 0}

        /* ── Controls strip ── */
        .em-controls-strip{display:flex;align-items:center;gap:.45rem;flex-wrap:wrap;
          margin:0 0 .75rem 0}

        /* ── Materials HTML table ── */
        .em-mat-table{width:100%;border-collapse:collapse;font-size:.82rem}
        .em-mat-table th{background:#f8fafc;color:#374151;font-weight:700;font-size:.74rem;
          text-transform:uppercase;letter-spacing:.04em;padding:.5rem .7rem;
          border-bottom:1px solid #e5eaf2;white-space:nowrap;text-align:left}
        .em-mat-table td{padding:.55rem .7rem;border-bottom:1px solid #f1f5f9;
          color:#374151;vertical-align:middle}
        .em-mat-table tr:last-child td{border-bottom:none}
        .em-mat-table tr:hover td{background:#f8fafc}
        .em-mat-table .em-item-num{color:#2563eb;font-weight:700;cursor:pointer}
        .em-mat-table .em-item-num:hover{text-decoration:underline}
        .em-mat-empty{text-align:center;color:#9ca3af;padding:2rem;font-size:.88rem}

        /* ── Pagination ── */
        .em-pagination{display:flex;align-items:center;justify-content:space-between;
          padding:.45rem .5rem 0;font-size:.78rem;color:#6b7280;flex-wrap:wrap;gap:.3rem}
        .em-page-info{}

        /* ── Summary card ── */
        .em-summary-card{background:#fff;border:1px solid #e5eaf2;border-radius:12px;
          padding:1rem 1.1rem;box-shadow:0 1px 4px rgba(0,0,0,.05)}
        .em-sum-row{display:flex;justify-content:space-between;align-items:center;
          padding:.3rem 0;font-size:.83rem;color:#374151}
        .em-sum-row.em-sum-bold{font-weight:700;color:#111827}
        .em-sum-divider{border-top:1px solid #e5eaf2;margin:.35rem 0}
        .em-sum-total{font-size:1rem;font-weight:800;color:#111827}
        .em-sum-markup-box{background:#f0f4ff;border-radius:8px;padding:.7rem .8rem;
          margin:.6rem 0 0;border:1px solid #dbeafe}
        .em-sum-markup-title{font-size:.73rem;font-weight:700;color:#2563eb;
          text-transform:uppercase;letter-spacing:.04em;margin:0 0 .45rem 0}

        /* ── Notes / Docs cards ── */
        .em-notes-text{font-size:.84rem;color:#4b5563;line-height:1.55;
          padding:.2rem 0}
        .em-doc-row{display:flex;align-items:center;gap:.65rem;padding:.5rem 0;
          border-bottom:1px solid #f1f5f9;font-size:.82rem}
        .em-doc-row:last-child{border-bottom:none}
        .em-doc-icon{color:#94a3b8;font-size:1rem}
        .em-doc-name{font-weight:600;color:#111827;flex:1}
        .em-doc-meta{color:#9ca3af;font-size:.74rem}
        .em-empty-docs{text-align:center;color:#9ca3af;padding:1.2rem;font-size:.84rem}

        /* ── Responsive two-column layout ── */
        @media(max-width:900px){
          .em-two-col{flex-direction:column!important}
          .em-two-col .em-col-main{width:100%!important;max-width:100%!important}
          .em-two-col .em-col-side{width:100%!important;max-width:100%!important;
            min-width:0!important}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.session_state[_EM_CSS_KEY] = True


# ---------------------------------------------------------------------------
# Cached data helpers
# ---------------------------------------------------------------------------

@st.cache_data(ttl=30, show_spinner=False)
def _fetch_estimate_row(est_id: str, *, admin: bool) -> dict[str, Any] | None:
    eid = str(est_id or "").strip()
    if not eid:
        return None
    if admin:
        rows = fetch_by_match_admin("estimates", {"id": eid}, limit=1)
        return rows[0] if rows else None
    return fetch_one("estimates", {"id": eid})


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_customer_row(customer_id: str) -> dict[str, Any] | None:
    if not str(customer_id or "").strip():
        return None
    try:
        return fetch_one("customers", {"id": str(customer_id).strip()})
    except Exception:
        return None


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_job_row(job_id: str) -> dict[str, Any] | None:
    if not str(job_id or "").strip():
        return None
    try:
        return fetch_one("jobs", {"id": str(job_id).strip()})
    except Exception:
        return None


@st.cache_data(ttl=120, show_spinner=False)
def _fetch_catalog() -> list[dict[str, Any]]:
    try:
        return list(fetch_table_admin("estimate_materials", limit=5000, order_by="item_key") or [])
    except Exception:
        return []


@st.cache_data(ttl=120, show_spinner=False)
def _fetch_attachments(est_id: str) -> list[dict[str, Any]]:
    if not est_id:
        return []
    try:
        return list(
            fetch_by_match_admin(
                "attachments",
                {"estimate_id": est_id},
                limit=200,
            ) or []
        )
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Estimate-material helpers
# ---------------------------------------------------------------------------

def _get_est_json(est_row: dict[str, Any]) -> dict[str, Any]:
    """Safely extract the estimate JSON blob."""
    ej = est_row.get("estimate_json")
    if isinstance(ej, dict):
        return ej
    return {}


def _get_material_lines(est_row: dict[str, Any]) -> list[dict[str, Any]]:
    ej = _get_est_json(est_row)
    raw = ej.get("materials") or []
    return [r for r in raw if isinstance(r, dict)]


def _get_controls(est_row: dict[str, Any]) -> dict[str, Any]:
    ej = _get_est_json(est_row)
    c = ej.get("controls")
    return c if isinstance(c, dict) else {}


def _catalog_map(catalog: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(r.get("item_key") or ""): r for r in catalog if r.get("item_key")}


def _enrich_line(line: dict[str, Any], catalog: dict[str, dict[str, Any]], markup: Decimal) -> dict[str, Any]:
    key = str(line.get("item") or "").strip()
    cat_row = catalog.get(key) or {}
    qty = _dec(line.get("qty", 0) or 0)
    purchase = _dec(cat_row.get("purchase_price", 0) or 0)
    sell = _dec(cat_row.get("sell_price", 0) or 0)
    unit_sell = sell if sell > Decimal("0") else purchase * (Decimal("1") + markup)
    line_total = _q2(qty * unit_sell)
    return {
        "item_key": key,
        "description": str(cat_row.get("description") or key or "—"),
        "category": str(cat_row.get("category") or "—"),
        "qty": _q2(qty),
        "unit": str(cat_row.get("unit") or "EA"),
        "unit_cost": _q2(unit_sell),
        "total_cost": line_total,
    }


def _compute_material_totals(
    lines: list[dict[str, Any]],
    catalog: dict[str, dict[str, Any]],
    markup_pct: Decimal,
    sales_tax_pct: Decimal,
) -> dict[str, Decimal]:
    mat_total = Decimal("0")
    for ln in lines:
        enriched = _enrich_line(ln, catalog, markup_pct)
        mat_total += enriched["total_cost"]
    tax = _q2(mat_total * sales_tax_pct)
    markup_amt = _q2(mat_total * markup_pct)
    return {
        "material_total": _q2(mat_total),
        "freight": Decimal("0"),
        "tax": tax,
        "subtotal": _q2(mat_total),
        "markup_amount": markup_amt,
        "material_with_markup": _q2(mat_total + markup_amt),
    }


def _status_pill_class(status: str) -> str:
    s = str(status or "draft").lower().strip()
    mapping = {
        "draft": "em-status-draft",
        "submitted": "em-status-submitted",
        "approved": "em-status-approved",
        "awarded": "em-status-awarded",
    }
    return mapping.get(s, "em-status-other")


def _save_estimate_materials(est_id: str, new_lines: list[dict[str, Any]]) -> None:
    """Persist updated materials array into estimates.estimate_json."""
    row = fetch_one("estimates", {"id": est_id})
    if not row:
        return
    ej: dict[str, Any] = dict(row.get("estimate_json") or {})
    ej["materials"] = new_lines
    update_rows_admin(
        "estimates",
        {"estimate_json": ej, "updated_at": datetime.now(timezone.utc).isoformat()},
        {"id": est_id},
    )
    # Also sync session state if the estimate is currently loaded in the editor
    if str(st.session_state.get("loaded_estimate_id") or "") == est_id:
        editor_state = st.session_state.get("estimate_editor_state")
        if isinstance(editor_state, dict):
            editor_state["materials"] = new_lines
    # Bust caches
    _fetch_estimate_row.clear()


def _save_estimate_controls(est_id: str, updated_controls: dict[str, Any]) -> None:
    """Persist updated controls dict into estimates.estimate_json."""
    row = fetch_one("estimates", {"id": est_id})
    if not row:
        return
    ej: dict[str, Any] = dict(row.get("estimate_json") or {})
    ej["controls"] = {**(ej.get("controls") or {}), **updated_controls}
    update_rows_admin(
        "estimates",
        {"estimate_json": ej, "updated_at": datetime.now(timezone.utc).isoformat()},
        {"id": est_id},
    )
    if str(st.session_state.get("loaded_estimate_id") or "") == est_id:
        editor_state = st.session_state.get("estimate_editor_state")
        if isinstance(editor_state, dict):
            editor_state.setdefault("controls", {}).update(updated_controls)
    _fetch_estimate_row.clear()


# ---------------------------------------------------------------------------
# Dialogs: add / edit estimate material line item
# ---------------------------------------------------------------------------

@st.dialog("Add material to estimate", width="large")
def _dlg_add_estimate_material(
    est_id: str,
    existing_lines: list[dict[str, Any]],
    catalog_map: dict[str, dict[str, Any]],
) -> None:
    ensure_modal_styles()
    modal_wide_marker()
    st.markdown("### Add material")

    catalog_keys = sorted(catalog_map.keys())
    if not catalog_keys:
        st.warning("No materials in the catalog yet. Go to the Estimate Materials Catalog tab to add some first.")
        if st.button("Close", key="dlg_add_mat_close"):
            st.rerun()
        return

    tab_inv, tab_custom = st.tabs(["From Catalog / Inventory", "Custom Item"])

    with tab_inv:
        c1, c2 = st.columns([3, 1])
        with c1:
            search_q = st.text_input("Search catalog", key="dlg_add_cat_search", placeholder="Type to filter…")
        with c2:
            st.write("")

        filtered = [k for k in catalog_keys if search_q.lower() in k.lower() or
                    search_q.lower() in (catalog_map.get(k) or {}).get("description", "").lower()] if search_q else catalog_keys

        if not filtered:
            st.info("No items match the search.")
        else:
            chosen_key = st.selectbox(
                "Item",
                options=filtered,
                format_func=lambda k: f"{k} — {(catalog_map.get(k) or {}).get('description', '')[:60]}",
                key="dlg_add_cat_item",
            )
            if chosen_key and catalog_map.get(chosen_key):
                cm = catalog_map[chosen_key]
                st.caption(
                    f"Category: {cm.get('category', '—')} · "
                    f"Unit: {cm.get('unit', 'EA')} · "
                    f"Sell: {_money(cm.get('sell_price', 0))} · "
                    f"Purchase: {_money(cm.get('purchase_price', 0))}"
                )

            with st.form("dlg_add_inv_form", clear_on_submit=False):
                qty = st.number_input("Qty", min_value=0.0, step=1.0, format="%.2f",
                                      value=1.0, key="dlg_add_cat_qty")
                submitted = st.form_submit_button("Add to Estimate", type="primary", use_container_width=True)

            if submitted:
                key = str(st.session_state.get("dlg_add_cat_item") or "").strip()
                if not key:
                    st.error("Select an item.")
                    return
                new_lines = list(existing_lines) + [{"item": key, "qty": float(qty)}]
                _save_estimate_materials(est_id, new_lines)
                st.session_state.pop(_EM_EST_DLG_KEY, None)
                st.success(f"Added {key} × {qty:.2f}")
                st.rerun()

    with tab_custom:
        with st.form("dlg_add_custom_form", clear_on_submit=True):
            c_ik = st.text_input("Item key / code", placeholder="Unique identifier")
            c_desc = st.text_input("Description")
            c_cat = st.text_input("Category", value="Custom")
            c_unit = st.text_input("Unit", value="EA")
            c_sell = st.number_input("Unit sell price", min_value=0.0, step=0.01, format="%.2f")
            c_qty = st.number_input("Qty", min_value=0.0, step=1.0, format="%.2f", value=1.0)
            c_submitted = st.form_submit_button("Add Custom Item", type="primary", use_container_width=True)

        if c_submitted:
            ik = str(c_ik or "").strip()
            if not ik:
                st.error("Item key is required.")
                return
            # Add to catalog first (if not exists), then to estimate
            if not fetch_by_match_admin("estimate_materials", {"item_key": ik}, limit=1):
                insert_row_admin("estimate_materials", {
                    "item_key": ik[:500],
                    "description": str(c_desc or "")[:2000],
                    "category": str(c_cat or "Custom")[:200],
                    "unit": str(c_unit or "EA")[:32],
                    "purchase_price": float(c_sell),
                    "sell_price": float(c_sell),
                    "is_active": True,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                })
                clear_estimate_materials_catalog_cache()
                _fetch_catalog.clear()
            new_lines = list(existing_lines) + [{"item": ik, "qty": float(c_qty)}]
            _save_estimate_materials(est_id, new_lines)
            st.session_state.pop(_EM_EST_DLG_KEY, None)
            st.success(f"Added custom item {ik}")
            st.rerun()

    if st.button("Cancel", key="dlg_add_mat_cancel", use_container_width=True):
        st.session_state.pop(_EM_EST_DLG_KEY, None)
        st.rerun()


@st.dialog("Edit material line", width="large")
def _dlg_edit_estimate_material(
    est_id: str,
    line_idx: int,
    existing_lines: list[dict[str, Any]],
    catalog_map: dict[str, dict[str, Any]],
) -> None:
    ensure_modal_styles()
    if line_idx < 0 or line_idx >= len(existing_lines):
        st.error("Line not found.")
        st.session_state.pop(_EM_EST_DLG_KEY, None)
        return

    line = existing_lines[line_idx]
    cur_key = str(line.get("item") or "").strip()
    cur_qty = float(line.get("qty", 1) or 1)

    st.markdown(f"### Edit line #{line_idx + 1}")
    catalog_keys = sorted(catalog_map.keys())
    default_idx = catalog_keys.index(cur_key) if cur_key in catalog_keys else 0

    with st.form("dlg_edit_mat_form", clear_on_submit=False):
        if catalog_keys:
            new_key = st.selectbox(
                "Item",
                options=catalog_keys,
                index=default_idx,
                format_func=lambda k: f"{k} — {(catalog_map.get(k) or {}).get('description', '')[:60]}",
                key="dlg_edit_mat_item",
            )
        else:
            new_key = st.text_input("Item key", value=cur_key, key="dlg_edit_mat_item_txt")

        new_qty = st.number_input("Qty", min_value=0.0, step=1.0, format="%.2f",
                                   value=cur_qty, key="dlg_edit_mat_qty")
        c1, c2 = st.columns(2)
        with c1:
            save_ok = st.form_submit_button("Save", type="primary", use_container_width=True)
        with c2:
            cancel_ok = st.form_submit_button("Cancel", use_container_width=True)

    if cancel_ok:
        st.session_state.pop(_EM_EST_DLG_KEY, None)
        st.rerun()
    if save_ok:
        key = str(st.session_state.get("dlg_edit_mat_item") or new_key or "").strip()
        if not key:
            st.error("Select an item.")
            return
        new_lines = list(existing_lines)
        new_lines[line_idx] = {"item": key, "qty": float(new_qty)}
        _save_estimate_materials(est_id, new_lines)
        st.session_state.pop(_EM_EST_DLG_KEY, None)
        st.success("Line updated.")
        st.rerun()


# ---------------------------------------------------------------------------
# UI rendering components
# ---------------------------------------------------------------------------

def _render_breadcrumb(quote_number: str) -> None:
    qn = str(quote_number or "—").strip()
    st.markdown(
        f'<div class="em-breadcrumb">'
        f'<span class="em-bc-link">Estimates</span>'
        f'<span class="em-bc-sep">›</span>'
        f'<span class="em-bc-link">{qn}</span>'
        f'<span class="em-bc-sep">›</span>'
        f'<span class="em-bc-current">Materials</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_page_header(est_row: dict[str, Any], customer_name: str) -> None:
    qn = str(est_row.get("quote_number") or "—").strip()
    status = str(est_row.get("status") or "draft").strip()
    pill_cls = _status_pill_class(status)
    ej = _get_est_json(est_row)
    project = str(ej.get("estimate_description") or est_row.get("estimate_description") or "").strip()
    if not project:
        project = str(ej.get("job") or ej.get("job_name") or "").strip()
    if not project:
        project = "Project"

    sep = '<span class="em-sep">•</span>'
    sub_parts = [p for p in [project, customer_name] if p]
    sub_html = f" {sep} ".join(sub_parts)

    # Header HTML
    st.markdown(
        f'<div class="em-page-header">'
        f'<div class="em-header-row1">'
        f'<h1 class="em-title">Estimate {qn}</h1>'
        f'<span class="em-status-pill {pill_cls}">{status}</span>'
        f'</div>'
        f'<p class="em-header-sub">{sub_html}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Action buttons
    ha1, ha2, ha3, _spc = st.columns([1, 1, 1.4, 4], gap="small")
    with ha1:
        if st.button("More ▾", key="em_hdr_more", use_container_width=True):
            pass  # placeholder
    with ha2:
        if st.button("⬇ Export", key="em_hdr_export", use_container_width=True):
            try:
                from app.estimates.services import EST_VIEW_KEY, go_to_edit
                st.session_state[EST_VIEW_KEY] = "edit"
                try:
                    from app.ui import IPS_NAV_PENDING_KEY
                except ImportError:
                    from ui import IPS_NAV_PENDING_KEY  # type: ignore
                st.session_state[IPS_NAV_PENDING_KEY] = "Estimates"
                st.rerun()
            except Exception:
                st.info("Open the estimate editor to export.")
    with ha3:
        if st.button("✏ Edit Estimate", key="em_hdr_edit", type="primary", use_container_width=True):
            try:
                from app.ui import IPS_NAV_PENDING_KEY
            except ImportError:
                from ui import IPS_NAV_PENDING_KEY  # type: ignore
            st.session_state[IPS_NAV_PENDING_KEY] = "Estimates"
            st.session_state["estimates_view"] = "edit"
            st.rerun()


def _render_info_card(
    est_row: dict[str, Any],
    customer: dict[str, Any] | None,
    job: dict[str, Any] | None,
    mat_totals: dict[str, Decimal],
) -> None:
    ej = _get_est_json(est_row)
    customer_name = str((customer or {}).get("customer_name") or "—").strip()
    customer_id = str(est_row.get("customer_id") or "").strip()
    job_id = str(est_row.get("job_id") or "").strip()

    if job:
        try:
            from app.utils.formatters import job_display_label
        except ImportError:
            from utils.formatters import job_display_label  # type: ignore
        jn = str((job or {}).get("job_number") or "").strip()
        jnm = str((job or {}).get("job_name") or "").strip()
        job_display = job_display_label(jn, jnm) or "—"
    else:
        job_display = "—"

    created_at = est_row.get("created_at")
    est_date = "—"
    valid_through = "—"
    days_remaining = ""
    if created_at:
        try:
            dt = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
            est_date = dt.strftime("%b %d, %Y")
            vt = dt + timedelta(days=30)
            valid_through = vt.strftime("%b %d, %Y")
            rem = (vt - datetime.now(timezone.utc)).days
            if rem >= 0:
                days_remaining = f" ({rem}d remaining)"
            else:
                days_remaining = " (expired)"
        except Exception:
            pass

    prepared_by = str(ej.get("prepared_by_name") or est_row.get("prepared_by_name") or "—").strip()
    proposal_total_raw = est_row.get("proposal_total")
    if proposal_total_raw is not None:
        total_display = _money(proposal_total_raw)
    else:
        total_display = _money(mat_totals.get("material_with_markup", 0))

    st.markdown(
        f"""<div class="em-info-card">
        <div class="em-info-grid">
          <div class="em-info-cell">
            <p class="em-info-label">Client</p>
            <p class="em-info-value">{customer_name}</p>
            {'<a class="em-info-link" title="View client">View Client ↗</a>' if customer_id else ''}
          </div>
          <div class="em-info-cell">
            <p class="em-info-label">Job</p>
            <p class="em-info-value">{job_display}</p>
            {'<a class="em-info-link" title="View job">View Job ↗</a>' if job_id else ''}
          </div>
          <div class="em-info-cell">
            <p class="em-info-label">Estimate Date</p>
            <p class="em-info-value">{est_date}</p>
          </div>
          <div class="em-info-cell">
            <p class="em-info-label">Valid Through</p>
            <p class="em-info-value">{valid_through}<small style="color:#9ca3af">{days_remaining}</small></p>
          </div>
          <div class="em-info-cell">
            <p class="em-info-label">Prepared By</p>
            <p class="em-info-value">{prepared_by}</p>
          </div>
          <div class="em-info-cell" style="text-align:right">
            <p class="em-info-label">Estimated Total</p>
            <p class="em-info-total">{total_display}</p>
          </div>
        </div>
        </div>""",
        unsafe_allow_html=True,
    )


def _render_nav_tabs() -> int:
    """Render horizontal estimate-section tabs. Returns the active tab index (0-based)."""
    labels = [
        "Overview", "Materials", "Labor", "Equipment",
        "Subcontractors", "Markups", "Summary", "Notes",
        "Attachments", "History",
    ]
    active = int(st.session_state.get(_EM_ACTIVE_TAB, 1))
    if active < 0 or active >= len(labels):
        active = 1  # Materials

    # Build tab HTML
    tab_html_parts = []
    for i, lbl in enumerate(labels):
        cls = "em-tab em-tab-active" if i == active else "em-tab"
        tab_html_parts.append(f'<span class="{cls}" data-idx="{i}">{lbl}</span>')
    tabs_html = '<div class="em-tabs-bar">' + "".join(tab_html_parts) + "</div>"
    st.markdown(tabs_html, unsafe_allow_html=True)

    # Streamlit buttons to switch tabs (hidden behind the HTML tab bar visually)
    btn_cols = st.columns(len(labels), gap="small")
    for i, (lbl, col) in enumerate(zip(labels, btn_cols)):
        with col:
            if st.button(lbl, key=f"em_tab_btn_{i}", use_container_width=True,
                         label_visibility="collapsed" if i != active else "visible"):
                st.session_state[_EM_ACTIVE_TAB] = i
                st.rerun()

    return active


def _render_materials_table(
    lines: list[dict[str, Any]],
    catalog: dict[str, dict[str, Any]],
    markup_pct: Decimal,
    est_id: str,
) -> None:
    """Render search + controls + paginated HTML materials table with inline actions."""
    st.session_state.setdefault(_EM_PAGE_KEY, 0)
    st.session_state.setdefault(_EM_SEARCH_KEY, "")

    # ── Controls strip ──────────────────────────────────────────────
    cc1, cc2, cc3, cc4, _spc, cc5, cc6 = st.columns([2.2, 1.3, 1.3, 1.4, 0.2, 1.0, 1.4], gap="small")
    with cc1:
        st.text_input(
            "Search materials",
            key=_EM_SEARCH_KEY,
            placeholder="Search materials…",
            label_visibility="collapsed",
        )
    with cc2:
        if st.button("Add from Inventory", key="em_add_from_inv", use_container_width=True):
            st.session_state[_EM_EST_DLG_KEY] = "add"
            st.rerun()
    with cc3:
        if st.button("Add Custom Item", key="em_add_custom", use_container_width=True):
            st.session_state[_EM_EST_DLG_KEY] = "add_custom"
            st.rerun()
    with cc4:
        st.selectbox(
            "Group by",
            options=["Category", "None"],
            key=_EM_GROUP_KEY,
            label_visibility="collapsed",
            format_func=lambda v: f"Group by: {v}",
        )
    with cc5:
        if st.button("Import", key="em_mat_import", use_container_width=True):
            st.session_state[_EM_EST_DLG_KEY] = "catalog_import"
            st.rerun()
    with cc6:
        if st.button("＋ Add Material", key="em_mat_add_primary", type="primary", use_container_width=True):
            st.session_state[_EM_EST_DLG_KEY] = "add"
            st.rerun()

    # ── Filter & paginate ───────────────────────────────────────────
    search_q = str(st.session_state.get(_EM_SEARCH_KEY) or "").strip().lower()
    group_by_cat = str(st.session_state.get(_EM_GROUP_KEY) or "Category") == "Category"
    enriched = [_enrich_line(ln, catalog, markup_pct) for ln in lines]

    if search_q:
        enriched_filtered = [
            e for e in enriched
            if search_q in e["item_key"].lower()
            or search_q in e["description"].lower()
            or search_q in e["category"].lower()
        ]
        filtered_indices = [
            i for i, e in enumerate(enriched)
            if search_q in e["item_key"].lower()
            or search_q in e["description"].lower()
            or search_q in e["category"].lower()
        ]
    else:
        enriched_filtered = enriched
        filtered_indices = list(range(len(enriched)))

    total_rows = len(enriched_filtered)
    total_pages = max(1, (total_rows + _EM_PER_PAGE - 1) // _EM_PER_PAGE)
    cur_page = int(st.session_state.get(_EM_PAGE_KEY, 0))
    if cur_page >= total_pages:
        cur_page = 0
        st.session_state[_EM_PAGE_KEY] = 0

    page_start = cur_page * _EM_PER_PAGE
    page_end = min(page_start + _EM_PER_PAGE, total_rows)
    page_enriched = enriched_filtered[page_start:page_end]
    page_orig_indices = filtered_indices[page_start:page_end]

    # ── Build HTML table ────────────────────────────────────────────
    if not page_enriched:
        st.markdown(
            '<div class="em-mat-table"><div class="em-mat-empty">'
            '📦 No materials added yet. Use <strong>＋ Add Material</strong> or '
            '<strong>Add from Inventory</strong> to get started.'
            '</div></div>',
            unsafe_allow_html=True,
        )
    else:
        # Group by category if selected
        if group_by_cat:
            categories: dict[str, list[tuple[int, dict]]] = {}
            for orig_idx, e in zip(page_orig_indices, page_enriched):
                cat = e["category"]
                categories.setdefault(cat, []).append((orig_idx, e))
        else:
            categories = {"": list(zip(page_orig_indices, page_enriched))}

        rows_html = ""
        for cat_name, cat_rows in categories.items():
            if group_by_cat and cat_name:
                rows_html += (
                    f'<tr><td colspan="9" style="background:#f8fafc;font-size:.72rem;'
                    f'font-weight:700;color:#6b7280;text-transform:uppercase;'
                    f'letter-spacing:.05em;padding:.35rem .7rem;border-top:1px solid #e5eaf2">'
                    f'{cat_name}</td></tr>'
                )
            for orig_idx, e in cat_rows:
                item_num = f"#{orig_idx + 1}"
                rows_html += (
                    f"<tr>"
                    f'<td style="color:#94a3b8;cursor:grab;text-align:center">⠿</td>'
                    f'<td><span class="em-item-num">{item_num}</span></td>'
                    f"<td>{e['description'][:60]}</td>"
                    f"<td><span style='background:#f1f5f9;border-radius:4px;padding:.1rem .4rem;"
                    f"font-size:.74rem;color:#475569'>{e['category']}</span></td>"
                    f"<td style='text-align:right'>{e['qty']:.2f}</td>"
                    f"<td style='text-align:center'>{e['unit']}</td>"
                    f"<td style='text-align:right'>{_money(e['unit_cost'])}</td>"
                    f"<td style='text-align:right;font-weight:600'>{_money(e['total_cost'])}</td>"
                    f'<td style="text-align:center;white-space:nowrap">'
                    f'<span style="color:#6b7280;font-size:.8rem" data-edit="{orig_idx}">✏</span>&nbsp;&nbsp;'
                    f'<span style="color:#ef4444;font-size:.8rem" data-del="{orig_idx}">🗑</span>'
                    f"</td>"
                    f"</tr>"
                )

        table_html = (
            '<div style="overflow-x:auto"><table class="em-mat-table">'
            "<thead><tr>"
            "<th style='width:32px'></th>"
            "<th>Item #</th><th>Description</th><th>Category</th>"
            "<th style='text-align:right'>Qty</th>"
            "<th style='text-align:center'>Unit</th>"
            "<th style='text-align:right'>Unit Cost</th>"
            "<th style='text-align:right'>Total Cost</th>"
            "<th style='text-align:center'>Actions</th>"
            "</tr></thead>"
            f"<tbody>{rows_html}</tbody>"
            "</table></div>"
        )
        st.markdown(table_html, unsafe_allow_html=True)

    # ── Inline edit/delete buttons (below table, per row) ─────────────
    # Since HTML buttons can't trigger Python directly, we use Streamlit buttons
    # in a compact row below the table.
    if page_enriched:
        st.markdown('<div style="border-top:1px solid #f1f5f9;padding-top:.4rem;margin-top:.3rem">', unsafe_allow_html=True)
        for orig_idx, e in zip(page_orig_indices, page_enriched):
            c_lbl, c_edit, c_del = st.columns([4, 0.5, 0.5], gap="small")
            with c_lbl:
                st.caption(f"#{orig_idx + 1} · {e['item_key']} — {e['description'][:40]}")
            with c_edit:
                if st.button("✏", key=f"em_edit_{orig_idx}", use_container_width=True,
                             help=f"Edit line #{orig_idx + 1}"):
                    st.session_state[_EM_EST_DLG_KEY] = f"edit_{orig_idx}"
                    st.session_state[_EM_EDIT_IDX] = orig_idx
                    st.rerun()
            with c_del:
                if st.button("🗑", key=f"em_del_{orig_idx}", use_container_width=True,
                             help=f"Delete line #{orig_idx + 1}"):
                    new_lines = [ln for i, ln in enumerate(lines) if i != orig_idx]
                    _save_estimate_materials(est_id, new_lines)
                    st.session_state[_EM_PAGE_KEY] = 0
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Pagination ────────────────────────────────────────────────────
    pg1, pg2 = st.columns([3, 2], gap="small")
    with pg1:
        if total_rows > 0:
            st.caption(f"Showing {page_start + 1} to {min(page_end, total_rows)} of {total_rows} material{'s' if total_rows != 1 else ''}")
        else:
            st.caption("No materials")
    with pg2:
        if total_pages > 1:
            pager_cols = st.columns(min(total_pages + 2, 8), gap="small")
            with pager_cols[0]:
                if st.button("‹", key="em_page_prev", disabled=cur_page == 0, use_container_width=True):
                    st.session_state[_EM_PAGE_KEY] = max(0, cur_page - 1)
                    st.rerun()
            for i in range(min(total_pages, len(pager_cols) - 2)):
                with pager_cols[i + 1]:
                    btn_type = "primary" if i == cur_page else "secondary"
                    if st.button(str(i + 1), key=f"em_page_{i}", type=btn_type, use_container_width=True):
                        st.session_state[_EM_PAGE_KEY] = i
                        st.rerun()
            with pager_cols[min(total_pages, len(pager_cols) - 2) + 1] if len(pager_cols) > total_pages + 1 else pager_cols[-1]:
                if st.button("›", key="em_page_next", disabled=cur_page >= total_pages - 1, use_container_width=True):
                    st.session_state[_EM_PAGE_KEY] = min(total_pages - 1, cur_page + 1)
                    st.rerun()


def _render_materials_summary(
    mat_totals: dict[str, Decimal],
    est_row: dict[str, Any],
    est_id: str,
) -> None:
    """Render the right-side Materials Summary card with markup controls."""
    controls = _get_controls(est_row)
    markup_pct = _dec(controls.get("material_markup_pct", 0) or 0)
    sales_tax_pct = _dec(controls.get("sales_tax_pct", 0) or 0)
    markup_pct_display = float(markup_pct * 100)

    st.markdown('<div class="em-summary-card">', unsafe_allow_html=True)
    st.markdown('<p class="em-card-title">Materials Summary</p>', unsafe_allow_html=True)

    # Summary rows
    rows_html = (
        f'<div class="em-sum-row"><span>Material Total</span><span>{_money(mat_totals["material_total"])}</span></div>'
        f'<div class="em-sum-row"><span>Freight</span><span>$0.00</span></div>'
        f'<div class="em-sum-row"><span>Tax ({float(sales_tax_pct*100):.1f}%)</span>'
        f'<span>{_money(mat_totals["tax"])}</span></div>'
        f'<div class="em-sum-divider"></div>'
        f'<div class="em-sum-row em-sum-bold"><span>Total</span>'
        f'<span class="em-sum-total">{_money(mat_totals["subtotal"] + mat_totals["tax"])}</span></div>'
    )
    st.markdown(rows_html, unsafe_allow_html=True)

    # Markup box
    st.markdown('<div class="em-sum-markup-box">', unsafe_allow_html=True)
    st.markdown('<p class="em-sum-markup-title">Materials Markup</p>', unsafe_allow_html=True)

    markup_type = st.selectbox(
        "Markup type",
        options=["Percentage", "Fixed Amount"],
        index=0,
        key="em_markup_type_sel",
        label_visibility="collapsed",
    )
    new_markup_pct_display = st.number_input(
        "Markup %",
        min_value=0.0,
        max_value=500.0,
        value=markup_pct_display,
        step=1.0,
        format="%.1f",
        key="em_markup_pct_input",
        help="Material markup percentage applied to all catalog sell prices",
    )

    # Recompute with live markup input
    live_markup = _dec(new_markup_pct_display) / Decimal("100")
    live_markup_amt = _q2(mat_totals["material_total"] * live_markup)
    live_with_markup = _q2(mat_totals["material_total"] + live_markup_amt)

    markup_rows_html = (
        f'<div class="em-sum-row"><span>Markup Amount</span><span>{_money(live_markup_amt)}</span></div>'
        f'<div class="em-sum-row"><span>Markup Total</span><span>{_money(live_with_markup)}</span></div>'
        f'<div class="em-sum-divider"></div>'
        f'<div class="em-sum-row em-sum-bold"><span>Materials w/ Markup</span>'
        f'<span class="em-sum-total">{_money(live_with_markup)}</span></div>'
    )
    st.markdown(markup_rows_html, unsafe_allow_html=True)

    if st.button("Apply Markup", key="em_apply_markup", use_container_width=True, type="primary"):
        _save_estimate_controls(est_id, {"material_markup_pct": float(live_markup)})
        _fetch_estimate_row.clear()
        st.success(f"Markup set to {new_markup_pct_display:.1f}%")
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)  # markup-box
    st.markdown("</div>", unsafe_allow_html=True)  # summary-card


def _render_notes_card(est_row: dict[str, Any]) -> None:
    """Render Material Notes card."""
    ej = _get_est_json(est_row)
    notes_text = str(ej.get("material_notes") or "").strip()
    if not notes_text:
        notes_text = "All materials are estimated based on current supplier pricing and availability."

    with st.container(border=True):
        st.markdown("**Material Notes**")
        st.markdown(f'<p class="em-notes-text">{notes_text}</p>', unsafe_allow_html=True)


def _render_documents_card(est_id: str) -> None:
    """Render Linked Documents card from the attachments table."""
    attachments = _fetch_attachments(est_id)
    doc_rows = [
        a for a in attachments
        if a.get("category") in ("quote_attachment", "generated_docx", "generated_pdf", "import_source")
    ]

    with st.container(border=True):
        st.markdown("**Linked Documents**")
        if not doc_rows:
            st.markdown(
                '<div class="em-empty-docs">📎 No documents attached. '
                'Go to <strong>Attachments / P.O.</strong> in the estimate editor to upload files.</div>',
                unsafe_allow_html=True,
            )
        else:
            for doc in doc_rows[:10]:
                fn = str(doc.get("file_name") or "file").strip()
                cat = str(doc.get("category") or "").replace("_", " ").title()
                uploaded_at_raw = doc.get("uploaded_at") or doc.get("created_at") or ""
                uploaded_date = ""
                if uploaded_at_raw:
                    try:
                        dt = datetime.fromisoformat(str(uploaded_at_raw).replace("Z", "+00:00"))
                        uploaded_date = dt.strftime("%b %d, %Y")
                    except Exception:
                        pass
                storage_path = str(doc.get("storage_path") or "").strip()
                icon = "📄" if fn.endswith(".docx") else ("📕" if fn.endswith(".pdf") else "📎")

                dc1, dc2, dc3 = st.columns([4, 1.2, 1.2], gap="small")
                with dc1:
                    st.markdown(
                        f'<div class="em-doc-row">'
                        f'<span class="em-doc-icon">{icon}</span>'
                        f'<span class="em-doc-name">{fn}</span>'
                        f'<span class="em-doc-meta">{cat} · {uploaded_date}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                with dc2:
                    if storage_path:
                        try:
                            from db import create_signed_url
                            url = create_signed_url(storage_path)
                            if url:
                                st.link_button("View", url, use_container_width=True)
                        except Exception:
                            pass
                with dc3:
                    pass  # download button would need signed URL


# ---------------------------------------------------------------------------
# Tab content for non-Materials tabs
# ---------------------------------------------------------------------------

def _render_overview_tab(est_row: dict[str, Any]) -> None:
    ej = _get_est_json(est_row)
    scope = str(ej.get("scope_of_work") or "").strip()
    with st.container(border=True):
        st.markdown("**Scope of Work**")
        if scope:
            st.markdown(scope)
        else:
            st.caption("No scope of work entered. Open the estimate editor → Job Scope tab to add.")

    desc = str(ej.get("estimate_description") or est_row.get("estimate_description") or "").strip()
    excl = str(ej.get("exclusions") or "").strip()
    with st.container(border=True):
        st.markdown("**Project Description**")
        st.write(desc or "—")
        if excl:
            st.markdown("**Exclusions**")
            st.write(excl)


def _render_summary_tab(est_row: dict[str, Any], catalog: dict[str, dict[str, Any]]) -> None:
    ej = _get_est_json(est_row)
    controls = ej.get("controls") or {}
    from app.estimate.calculations import compute_totals
    try:
        from app.estimate.equipment import load_estimate_equipment_from_assets
        from app.services.estimate_materials_catalog import cached_estimate_materials_catalog_rows
        mat_catalog_rows = cached_estimate_materials_catalog_rows()
        equip_pricing = load_estimate_equipment_from_assets()
        labor_rates = list(fetch_table("labor_rates", limit=1000, order_by="classification") or [])
        totals = compute_totals(ej, mat_catalog_rows, labor_rates, equip_pricing)
    except Exception:
        totals = {}

    with st.container(border=True):
        st.markdown("**Estimate Totals**")
        if totals:
            for label, key in [
                ("Materials", "material_sell_basis"),
                ("Labor", "labor_total"),
                ("Equipment", "equipment_total"),
                ("Travel", "travel_total"),
                ("Overhead", "overhead_total"),
                ("Contingency", "contingency_total"),
                ("Profit", "profit_total"),
                ("Sales Tax", "sales_tax_total"),
            ]:
                c1, c2 = st.columns([3, 1])
                c1.write(label)
                c2.write(_money(totals.get(key, 0)))
            st.divider()
            c1, c2 = st.columns([3, 1])
            c1.markdown("**Proposal Total**")
            c2.markdown(f"**{_money(totals.get('proposal_total', 0))}**")
        else:
            st.caption("Totals unavailable. Open the estimate editor to compute.")


def _render_redirect_tab(tab_name: str) -> None:
    with st.container(border=True):
        st.markdown(f"**{tab_name}**")
        st.caption(f"Open the estimate editor to view and edit {tab_name.lower()}.")
        if st.button(f"Open Estimate Editor → {tab_name}", key=f"em_redir_{tab_name.lower()}",
                     type="primary", use_container_width=True):
            try:
                from app.ui import IPS_NAV_PENDING_KEY
            except ImportError:
                from ui import IPS_NAV_PENDING_KEY  # type: ignore
            st.session_state[IPS_NAV_PENDING_KEY] = "Estimates"
            st.session_state["estimates_view"] = "edit"
            st.rerun()


# ---------------------------------------------------------------------------
# Full estimate detail view
# ---------------------------------------------------------------------------

def _render_estimate_detail(est_id: str) -> None:
    admin = current_role() in {"admin", "pm", "manager", "estimator"}
    est_row = _fetch_estimate_row(est_id, admin=admin)
    if not est_row:
        st.warning(f"Estimate `{est_id}` not found. It may have been deleted or you may not have access.")
        if st.button("← Back to Estimates", key="em_back_est"):
            try:
                from app.ui import IPS_NAV_PENDING_KEY
            except ImportError:
                from ui import IPS_NAV_PENDING_KEY  # type: ignore
            st.session_state[IPS_NAV_PENDING_KEY] = "Estimates"
            st.rerun()
        return

    qn = str(est_row.get("quote_number") or "—").strip()
    customer_id = str(est_row.get("customer_id") or "").strip()
    job_id = str(est_row.get("job_id") or "").strip()
    customer = _fetch_customer_row(customer_id) if customer_id else None
    job = _fetch_job_row(job_id) if job_id else None
    customer_name = str((customer or {}).get("customer_name") or "").strip()

    catalog = _fetch_catalog()
    cat_map = _catalog_map(catalog)
    lines = _get_material_lines(est_row)
    controls = _get_controls(est_row)
    markup_pct = _dec(controls.get("material_markup_pct", 0) or 0)
    sales_tax_pct = _dec(controls.get("sales_tax_pct", 0) or 0)
    mat_totals = _compute_material_totals(lines, cat_map, markup_pct, sales_tax_pct)

    # ── Structural HTML marker (used by CSS rules in page_shell) ────
    st.markdown('<span class="ips-page-shell-marker"></span>', unsafe_allow_html=True)

    # ── Breadcrumb ──────────────────────────────────────────────────
    _render_breadcrumb(qn)

    # ── Header ─────────────────────────────────────────────────────
    _render_page_header(est_row, customer_name)

    # ── Info card ──────────────────────────────────────────────────
    _render_info_card(est_row, customer, job, mat_totals)

    # ── Navigation tabs ────────────────────────────────────────────
    active_tab = int(st.session_state.get(_EM_ACTIVE_TAB, 1))

    tab_labels = [
        "Overview", "Materials", "Labor", "Equipment",
        "Subcontractors", "Markups", "Summary", "Notes",
        "Attachments", "History",
    ]

    # Streamlit native tabs (works with hot reloading and back/forward)
    tabs = st.tabs(tab_labels)

    with tabs[0]:  # Overview
        _render_overview_tab(est_row)

    with tabs[1]:  # Materials (main content)
        st.markdown('<div class="em-card">', unsafe_allow_html=True)
        st.markdown('<p class="em-card-title">Materials</p>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Handle add/edit dialogs ───────────────────────────────
        dlg_state = str(st.session_state.get(_EM_EST_DLG_KEY) or "").strip()
        if dlg_state in ("add", "add_custom"):
            _dlg_add_estimate_material(est_id, lines, cat_map)
        elif dlg_state.startswith("edit_"):
            try:
                idx = int(dlg_state.split("_", 1)[1])
            except (ValueError, IndexError):
                idx = -1
            if 0 <= idx < len(lines):
                _dlg_edit_estimate_material(est_id, idx, lines, cat_map)
            else:
                st.session_state.pop(_EM_EST_DLG_KEY, None)
        elif dlg_state == "catalog_import":
            _catalog_import_inline(est_id)

        # ── Two-column layout: table + summary ────────────────────
        tbl_col, sum_col = st.columns([3, 1.2], gap="medium")
        with tbl_col:
            _render_materials_table(lines, cat_map, markup_pct, est_id)
        with sum_col:
            _render_materials_summary(mat_totals, est_row, est_id)

        # ── Bottom cards ─────────────────────────────────────────
        st.markdown("")
        nc, dc = st.columns(2, gap="medium")
        with nc:
            _render_notes_card(est_row)
        with dc:
            _render_documents_card(est_id)

    with tabs[2]:   # Labor
        _render_redirect_tab("Labor")
    with tabs[3]:   # Equipment
        _render_redirect_tab("Equipment")
    with tabs[4]:   # Subcontractors
        _render_redirect_tab("Subcontractors")
    with tabs[5]:   # Markups
        _render_redirect_tab("Markups")
    with tabs[6]:   # Summary
        _render_summary_tab(est_row, cat_map)
    with tabs[7]:   # Notes
        ej = _get_est_json(est_row)
        with st.container(border=True):
            st.markdown("**Notes**")
            scope = str(ej.get("scope_of_work") or "").strip()
            resp = str(ej.get("customer_responsibilities") or "").strip()
            if scope:
                st.markdown("**Scope of Work**")
                st.write(scope)
            if resp:
                st.markdown("**Customer Responsibilities**")
                st.write(resp)
            if not scope and not resp:
                st.caption("No notes. Edit the estimate to add scope and responsibility text.")
    with tabs[8]:   # Attachments
        _render_documents_card(est_id)
    with tabs[9]:   # History
        _render_redirect_tab("History / Revisions")


def _catalog_import_inline(est_id: str) -> None:
    """Inline catalog import expander when triggered from Materials tab."""
    with st.expander("Import from Inventory Catalog", expanded=True):
        st.caption("Add materials from the inventory catalog to this estimate.")
        cat = _fetch_catalog()
        cat_map = _catalog_map(cat)
        if not cat_map:
            st.info("No catalog items available.")
        else:
            search = st.text_input("Search catalog for import", key="em_cat_imp_search")
            keys = sorted(cat_map.keys())
            if search:
                keys = [k for k in keys if search.lower() in k.lower() or
                        search.lower() in (cat_map.get(k) or {}).get("description", "").lower()]
            with st.form("em_cat_bulk_import_form", clear_on_submit=True):
                chosen = st.multiselect("Select items to add", options=keys,
                                        format_func=lambda k: f"{k} — {(cat_map.get(k) or {}).get('description', '')[:50]}",
                                        key="em_cat_imp_chosen")
                qty_each = st.number_input("Qty for each", min_value=0.1, value=1.0, step=1.0,
                                           format="%.1f", key="em_cat_imp_qty")
                c1, c2 = st.columns(2)
                with c1:
                    add_ok = st.form_submit_button("Add Selected", type="primary", use_container_width=True)
                with c2:
                    cancel_ok = st.form_submit_button("Cancel", use_container_width=True)

            if cancel_ok:
                st.session_state.pop(_EM_EST_DLG_KEY, None)
                st.rerun()
            if add_ok and chosen:
                current = _get_material_lines(_fetch_estimate_row(est_id, admin=True) or {})
                new_lines = list(current) + [{"item": k, "qty": float(qty_each)} for k in chosen]
                _save_estimate_materials(est_id, new_lines)
                st.session_state.pop(_EM_EST_DLG_KEY, None)
                st.success(f"Added {len(chosen)} item(s).")
                st.rerun()


# ---------------------------------------------------------------------------
# Fallback: catalog management view (original behavior)
# ---------------------------------------------------------------------------

@st.dialog("Add catalog material", width="large", on_dismiss=lambda: st.session_state.pop(_EM_DLG_KEY, None))
def _em_add_material_dialog() -> None:
    ensure_modal_styles()
    modal_wide_marker()
    st.markdown("### Add material")
    with st.container(border=True):
        with st.form("em_add_form_dlg", clear_on_submit=True):
            ik = st.text_input("Item key", placeholder="Unique code or SKU")
            desc = st.text_input("Description")
            cat = st.text_input("Category", value="Quote Catalog")
            unit = st.text_input("Unit", value="EA")
            pp = st.number_input("Purchase price", min_value=0.0, value=0.0, step=0.01)
            sp = st.number_input("Sell price", min_value=0.0, value=0.0, step=0.01)
            vin = st.text_input("Vendor item #", value="")
            inv_ref = st.text_input("Linked inventory row (optional UUID)", value="")
            submitted = st.form_submit_button("Save material", type="primary", use_container_width=True)
    if st.button("Cancel", type="secondary", use_container_width=True, key="em_add_dlg_cancel"):
        st.session_state.pop(_EM_DLG_KEY, None)
        st.rerun()
    if submitted:
        key = str(ik or "").strip()
        if not key:
            st.error("Item key is required.")
            return
        if fetch_by_match_admin("estimate_materials", {"item_key": key}, limit=1):
            st.error("That item key already exists.")
            return
        payload: dict = {
            "item_key": key[:500],
            "description": str(desc or "")[:2000],
            "category": str(cat or "Quote Catalog")[:200],
            "subgroup": "",
            "unit": str(unit or "EA")[:32],
            "purchase_price": float(pp),
            "sell_price": float(sp),
            "vendor_item_number": str(vin or "")[:200],
            "is_active": True,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        ref = str(inv_ref or "").strip()
        if ref:
            payload["inventory_ref_id"] = ref
        insert_row_admin("estimate_materials", payload)
        clear_estimate_materials_catalog_cache()
        _fetch_catalog.clear()
        st.session_state.pop(_EM_DLG_KEY, None)
        st.success("Material added.")
        st.rerun()


@st.dialog("Manage categories", width="large", on_dismiss=lambda: st.session_state.pop(_EM_DLG_KEY, None))
def _em_manage_categories_dialog() -> None:
    ensure_modal_styles()
    modal_wide_marker()
    st.markdown("### Manage categories")
    st.caption("Bulk rename: exact **from** category → **to** category on all matching rows.")
    with st.container(border=True):
        with st.form("em_cat_rename_dlg"):
            old_c = st.text_input("Rename from", placeholder="Exact category text")
            new_c = st.text_input("Rename to", placeholder="New category text")
            apply_sub = st.form_submit_button("Apply rename", type="primary", use_container_width=True)
    if st.button("Cancel", type="secondary", use_container_width=True, key="em_cat_dlg_cancel"):
        st.session_state.pop(_EM_DLG_KEY, None)
        st.rerun()
    if apply_sub:
        o = str(old_c or "").strip()
        n = str(new_c or "").strip()
        if not o or not n:
            st.error("Enter both values.")
            return
        rows = fetch_by_match_admin("estimate_materials", {"category": o}, limit=5000)
        for r in rows or []:
            rid = str((r or {}).get("id") or "").strip()
            if rid:
                update_rows_admin(
                    "estimate_materials",
                    {"category": n[:200], "updated_at": datetime.now(timezone.utc).isoformat()},
                    {"id": rid},
                )
        clear_estimate_materials_catalog_cache()
        _fetch_catalog.clear()
        st.session_state.pop(_EM_DLG_KEY, None)
        st.success(f"Updated {len(rows or [])} row(s).")
        st.rerun()


def _parse_inventory_uuid_selection(text: str) -> frozenset[str]:
    ids: set[str] = set()
    for part in _UUID_SPLIT.split(str(text or "")):
        p = part.strip()
        if len(p) >= 32:
            ids.add(p)
    return frozenset(ids)


@st.dialog("Import from inventory — preview", width="large")
def _dialog_em_inventory_import_preview() -> None:
    scope = st.session_state.get("em_inv_scope", "all_active")
    if scope not in ("all_active", "materials_only"):
        scope = "all_active"
    mode = st.session_state.get("em_inv_sel_mode", "all_eligible")
    selected: frozenset[str] | None = None
    if mode == "selected_uuids":
        selected = _parse_inventory_uuid_selection(str(st.session_state.get("em_imp_uuids") or ""))
        if not selected:
            st.warning("Enter at least one UUID when using **Import selected**.")
            return
    with st.spinner("Computing preview…"):
        result = import_inventory_materials_into_estimate_catalog(
            fetch_table=fetch_table,
            insert_row_admin=insert_row_admin,
            update_rows_admin=update_rows_admin,
            fetch_table_admin=fetch_table_admin,
            dry_run=True,
            scope=scope,
            selected_inventory_ids=selected,
        )
    st.markdown(result.summary_text())


def _render_catalog_view() -> None:
    """Original catalog management view (fallback when no estimate is loaded)."""
    try:
        from app.ui.page_shell import render_page_header
    except ImportError:
        from ui.page_shell import render_page_header  # type: ignore

    render_page_header(
        "Estimate Materials Catalog",
        "Quote catalog for proposals — separate from inventory stock.",
    )

    st.info(
        "💡 **Tip:** Open an estimate from the Estimates list to see its materials here. "
        "You're currently viewing the shared materials catalog.",
        icon=None,
    )

    st.session_state.setdefault(_EM_DLG_KEY, "")

    if current_role() not in {"admin", "manager"}:
        st.info("Only admin or manager can manage the estimate materials catalog.")
        try:
            rows = fetch_table("estimate_materials", limit=2000, order_by="item_key")
        except Exception:
            rows = []
        if rows:
            st.dataframe(
                prepare_catalog_inventory_display_df(
                    pd.DataFrame(rows),
                    extra_hidden=frozenset({"created_at"}),
                ),
                use_container_width=True,
                hide_index=True,
            )
        return

    st.session_state.setdefault("em_inv_scope", "all_active")
    st.session_state.setdefault("em_inv_sel_mode", "all_eligible")

    with st.expander("Import from inventory — options", expanded=False):
        st.radio(
            "Which inventory rows to include",
            options=["all_active", "materials_only"],
            key="em_inv_scope",
            horizontal=True,
            format_func=lambda v: (
                "All **active** items" if v == "all_active" else "**Materials** category only"
            ),
        )
        st.radio(
            "Import mode",
            options=["all_eligible", "selected_uuids"],
            key="em_inv_sel_mode",
            horizontal=True,
            format_func=lambda v: (
                "**Import all** eligible rows" if v == "all_eligible" else "**Import selected** UUIDs only"
            ),
        )
        if str(st.session_state.get("em_inv_sel_mode") or "") == "selected_uuids":
            st.text_area(
                "Inventory row UUIDs",
                height=120,
                key="em_imp_uuids",
                placeholder="One UUID per line, or comma-separated",
            )

    a1, a2, a3, a4 = st.columns(4, gap="small")
    with a1:
        pv, imp = st.columns(2, gap="small")
        with pv:
            if st.button("Preview", use_container_width=True, key="em_imp_preview"):
                _dialog_em_inventory_import_preview()
        with imp:
            if st.button("Import", use_container_width=True, key="em_imp_inv"):
                scope = st.session_state.get("em_inv_scope", "all_active")
                if scope not in ("all_active", "materials_only"):
                    scope = "all_active"
                mode = st.session_state.get("em_inv_sel_mode", "all_eligible")
                selected_ids: frozenset[str] | None = None
                if mode == "selected_uuids":
                    selected_ids = _parse_inventory_uuid_selection(
                        str(st.session_state.get("em_imp_uuids") or "")
                    )
                    if not selected_ids:
                        st.error("Enter at least one UUID for **Import selected**.")
                if mode != "selected_uuids" or selected_ids:
                    with st.spinner("Importing from inventory…"):
                        result = import_inventory_materials_into_estimate_catalog(
                            fetch_table=fetch_table,
                            insert_row_admin=insert_row_admin,
                            update_rows_admin=update_rows_admin,
                            fetch_table_admin=fetch_table_admin,
                            dry_run=False,
                            scope=scope,
                            selected_inventory_ids=selected_ids,
                        )
                    clear_estimate_materials_catalog_cache()
                    _fetch_catalog.clear()
                    st.session_state.pop(_EM_DLG_KEY, None)
                    st.success("Import finished.")
                    with st.expander("Import summary", expanded=True):
                        st.markdown(result.summary_text())
                    st.rerun()
    with a2:
        if st.button("Sync Pricing", use_container_width=True, key="em_sync"):
            n = sync_estimate_material_pricing_from_inventory(
                fetch_table=fetch_table,
                fetch_table_admin=fetch_table_admin,
                update_rows_admin=update_rows_admin,
            )
            clear_estimate_materials_catalog_cache()
            _fetch_catalog.clear()
            st.session_state.pop(_EM_DLG_KEY, None)
            st.success(f"Updated pricing on {n} linked row(s).")
            st.rerun()
    with a3:
        if st.button("Add Material", type="primary", use_container_width=True, key="em_btn_add"):
            st.session_state[_EM_DLG_KEY] = "add"
            st.rerun()
    with a4:
        if st.button("Manage Categories", type="secondary", use_container_width=True, key="em_btn_cats"):
            st.session_state[_EM_DLG_KEY] = "cats"
            st.rerun()

    dlg = str(st.session_state.get(_EM_DLG_KEY) or "").strip()
    if dlg == "add":
        _em_add_material_dialog()
    elif dlg == "cats":
        _em_manage_categories_dialog()

    try:
        rows = list(fetch_table_admin("estimate_materials", limit=5000, order_by="item_key") or [])
    except Exception as exc:
        st.error(
            f"Could not load **estimate_materials**. Apply migration `sql/039_estimate_materials.sql` "
            f"in Supabase, then refresh. ({exc})"
        )
        return

    if not rows:
        st.info("No catalog rows yet. Use **Import** or **Add Material**.")
        return

    st.markdown("##### Catalog")
    st.dataframe(
        prepare_catalog_inventory_display_df(
            pd.DataFrame(rows),
            extra_hidden=frozenset({"created_at"}),
        ),
        use_container_width=True,
        hide_index=True,
    )


# ---------------------------------------------------------------------------
# Estimate picker (shown when no estimate is in session state)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60, show_spinner=False)
def _fetch_estimates_picker_list(*, admin: bool) -> list[dict[str, Any]]:
    """Fetch a lightweight list of estimates for the picker dropdown."""
    cols = "id,quote_number,status,customer_id,updated_at"
    try:
        if admin:
            return list(fetch_table_admin("estimates", columns=cols, limit=500, order_by="updated_at") or [])
        return list(fetch_table("estimates", columns=cols, limit=500, order_by="updated_at") or [])
    except Exception:
        return []


def _render_estimate_picker() -> str | None:
    """Render an estimate selector card. Returns the selected estimate ID or None."""
    admin = current_role() in {"admin", "pm", "manager", "estimator"}
    estimates = _fetch_estimates_picker_list(admin=admin)

    with st.container(border=True):
        st.markdown("**Select an Estimate**")
        st.caption(
            "No estimate is currently selected. Pick one below to view its materials, "
            "or navigate to the **Estimates** page to open one from the list."
        )

        if not estimates:
            st.info("No estimates found.")
            if st.button("Go to Estimates", key="em_picker_go_est", type="primary"):
                try:
                    from app.ui import IPS_NAV_PENDING_KEY
                except ImportError:
                    from ui import IPS_NAV_PENDING_KEY  # type: ignore
                st.session_state[IPS_NAV_PENDING_KEY] = "Estimates"
                st.rerun()
            return None

        # Build picker options
        def _picker_label(r: dict[str, Any]) -> str:
            qn = str(r.get("quote_number") or "—").strip()
            status = str(r.get("status") or "draft").strip()
            label = f"{qn}  [{status}]"
            return label

        options = ["-- Select an estimate --"] + [r["id"] for r in estimates]
        labels = {r["id"]: _picker_label(r) for r in estimates}

        sel = st.selectbox(
            "Estimate",
            options=options,
            format_func=lambda v: labels.get(v, v),
            key="em_picker_select",
            label_visibility="collapsed",
        )

        c1, c2 = st.columns([1, 3], gap="small")
        with c1:
            if st.button("Open Estimate Materials", key="em_picker_open",
                         type="primary", use_container_width=True,
                         disabled=(sel == "-- Select an estimate --")):
                if sel and sel != "-- Select an estimate --":
                    st.session_state["loaded_estimate_id"] = sel
                    st.session_state["selected_estimate_id"] = sel
                    st.rerun()
        with c2:
            if st.button("Manage Catalog →", key="em_picker_catalog",
                         use_container_width=True):
                st.session_state["em_show_catalog"] = True
                st.rerun()

    return None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def render() -> None:
    """Entry point called by app/main.py."""
    _inject_em_page_styles()

    # Show catalog view if explicitly requested
    if st.session_state.get("em_show_catalog"):
        if st.button("← Back", key="em_catalog_back"):
            st.session_state.pop("em_show_catalog", None)
            st.rerun()
        _render_catalog_view()
        return

    # Determine if an estimate is currently loaded
    est_id = str(
        st.session_state.get("loaded_estimate_id")
        or st.session_state.get("selected_estimate_id")
        or ""
    ).strip()

    if est_id:
        # Show a small "Switch estimate" link at top
        with st.expander("📋 Switch estimate", expanded=False):
            c1, c2 = st.columns([3, 1], gap="small")
            with c1:
                picker_est = _render_estimate_picker()
            with c2:
                if st.button("Clear / Show Catalog", key="em_clear_est", use_container_width=True):
                    st.session_state.pop("loaded_estimate_id", None)
                    st.session_state.pop("selected_estimate_id", None)
                    st.rerun()
        _render_estimate_detail(est_id)
    else:
        _render_estimate_picker()
        st.divider()
        st.markdown("**or manage the materials catalog directly:**")
        _render_catalog_view()
