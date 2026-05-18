from __future__ import annotations

import html
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from urllib.parse import urlencode

import pandas as pd
import streamlit as st

from branding import render_header

try:
    from app.ips_crud_list_styles import render_crud_list_subtitle
except ImportError:
    from ips_crud_list_styles import render_crud_list_subtitle  # type: ignore
from auth import current_role
from db import (
    fetch_by_match_admin,
    fetch_one,
    fetch_table,
    fetch_table_admin,
)

try:
    from services.delete_safety import delete_estimate_unlink_first
except ImportError:
    from app.services.delete_safety import delete_estimate_unlink_first  # type: ignore

from app.utils.formatters import job_display_label

try:
    from services.estimate_import_customer_match import (
        PLACEHOLDER,
        build_sorted_customer_names,
        classify_import_customer_matches,
        name_to_customer_id_map,
        resolve_picked_customer_id,
    )
except ImportError:
    from app.services.estimate_import_customer_match import (  # type: ignore
        PLACEHOLDER,
        build_sorted_customer_names,
        classify_import_customer_matches,
        name_to_customer_id_map,
        resolve_picked_customer_id,
    )

from pages.estimate_editor import (
    blank_estimate,
    coalesce_imported_estimate,
    ensure_state,
    insert_imported_estimate,
    merge_estimate_row_scalar_fields_into_editor,
    parse_estimate_json_bytes,
    render_estimate_editor,
)


def _estimates_page_admin_read() -> bool:
    """Internal roles use service-role reads so admin-written rows stay visible under RLS."""
    return current_role() in {"admin", "manager", "pm"}


def _estimates_page_can_edit() -> bool:
    return current_role() in {"admin", "manager", "pm"}


@st.cache_data(ttl=60, show_spinner=False)
def _fetch_estimates_list_rows_cached(admin_read: bool) -> list[dict[str, Any]]:
    if admin_read:
        return fetch_table_admin("estimates", limit=1000, order_by="updated_at")
    return fetch_table("estimates", limit=1000, order_by="updated_at")


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_estimate_customer_rows_cached(admin_read: bool) -> list[dict[str, Any]]:
    columns = "id,customer_name"
    if admin_read:
        return fetch_table_admin("customers", columns=columns, limit=3000, order_by="customer_name")
    return fetch_table("customers", columns=columns, limit=3000, order_by="customer_name")


@st.cache_data(ttl=120, show_spinner=False)
def _fetch_jobs_for_estimate_links_cached(admin_read: bool) -> list[dict[str, Any]]:
    columns = "id,job_number,job_name,estimate_id"
    if admin_read:
        return fetch_table_admin("jobs", columns=columns, limit=5000, order_by="job_number")
    return fetch_table("jobs", columns=columns, limit=5000, order_by="job_number")


def _clear_estimates_page_cache() -> None:
    _fetch_estimates_list_rows_cached.clear()
    _fetch_estimate_customer_rows_cached.clear()
    _fetch_jobs_for_estimate_links_cached.clear()


def _fetch_one_estimate_row(estimate_id: str) -> dict[str, Any] | None:
    eid = str(estimate_id or "").strip()
    if not eid:
        return None
    if _estimates_page_admin_read():
        rows = fetch_by_match_admin("estimates", {"id": eid}, limit=1)
        return rows[0] if rows else None
    return fetch_one("estimates", {"id": eid})


def _fetch_estimates_list_rows() -> list[dict[str, Any]]:
    return _fetch_estimates_list_rows_cached(_estimates_page_admin_read())


def _fetch_customers_for_import() -> list[dict[str, Any]]:
    """Directory rows for matching imported quotes to real customers."""
    return _fetch_estimate_customer_rows_cached(_estimates_page_admin_read())


def _fetch_jobs_for_estimate_links() -> list[dict[str, Any]]:
    return _fetch_jobs_for_estimate_links_cached(_estimates_page_admin_read())



_MONEY_LIST_COLUMNS: frozenset[str] = frozenset({"proposal_total", "final_bid"})


def _estimate_money_display(val: Any) -> str:
    """DB / saved numeric → $ with commas and exactly 2 decimal places (Decimal-safe)."""
    if val is None:
        return ""
    try:
        if pd.isna(val):
            return ""
    except Exception:
        pass
    try:
        d = Decimal(str(val).replace(",", "").strip()).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return f"${d:,.2f}"
    except Exception:
        s = str(val).strip()
        return s[:72] + ("…" if len(s) > 72 else "")


def _estimate_money_csv(val: Any) -> str:
    """Same cents as display; plain numeric string for CSV (2 decimals, no $)."""
    if val is None:
        return ""
    try:
        if pd.isna(val):
            return ""
    except Exception:
        pass
    try:
        d = Decimal(str(val).replace(",", "").strip()).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return f"{d:.2f}"
    except Exception:
        return str(val).strip()


def _estimate_list_cell_text(val: Any, col: str | None = None) -> str:
    if col and col in _MONEY_LIST_COLUMNS:
        return _estimate_money_display(val)
    if val is None:
        return ""
    try:
        if pd.isna(val):
            return ""
    except Exception:
        pass
    s = str(val).strip()
    if len(s) > 72:
        return f"{s[:69]}…"
    return s


_EDITOR_TRANSIENT_PREFIXES: tuple[str, ...] = (
    # New form-based Materials/Labor widgets (avoid stale inputs across estimates)
    "est_material_",
    "est_labor_",
    # Customer/job match helpers
    "est_customer_",
    "est_job_",
    "est_import_cust_",
    # Equipment picker/filter widgets
    "est_eq_",
)


def _reset_estimate_editor_transients(*, clear_import_hints: bool = True) -> None:
    """
    Clear editor-only transient session keys so switching between estimates (or starting a new one)
    doesn't carry over stale widget state that can feel like "double entry" on rerun.
    """
    # Known singleton keys (safe even if absent)
    for k in (
        "est_material_edit_idx",
        "est_labor_edit_idx",
        "materials_editor_db",
        "labor_editor_db",
        "equipment_editor_db",
        "estimates_import_sig",
        "estimates_import_cache",
    ):
        st.session_state.pop(k, None)

    # Prefix-based cleanup for dynamically-indexed edit-form keys.
    to_drop: list[str] = []
    for k in list(st.session_state.keys()):
        if any(str(k).startswith(p) for p in _EDITOR_TRANSIENT_PREFIXES):
            to_drop.append(str(k))
    for k in to_drop:
        st.session_state.pop(k, None)

    if clear_import_hints:
        st.session_state.pop("estimate_pending_import_pdf", None)
        st.session_state.pop("estimate_pdf_suggestions", None)


def _load_estimate_into_session(selected_id: str) -> None:
    _reset_estimate_editor_transients(clear_import_hints=True)
    row = _fetch_one_estimate_row(selected_id)
    if not row:
        return
    loaded = row.get("estimate_json") or {}
    loaded.update({
        "quote_number": row.get("quote_number", ""),
        "customer_id": row.get("customer_id"),
        "customer_contact_id": row.get("customer_contact_id"),
        "job_id": row.get("job_id"),
        "status": row.get("status", "draft"),
        "estimate_description": row.get("estimate_description", loaded.get("estimate_description", "")),
        "scope_of_work": row.get("scope_of_work", ""),
        "exclusions": row.get("exclusions", ""),
        "additional_charges": row.get("additional_charges", ""),
        "customer_responsibilities": row.get("customer_responsibilities", ""),
        "job_received": row.get("job_received", False),
        "po_number": row.get("po_number", ""),
        "po_date": str(row.get("po_date") or ""),
        "po_amount": float(row.get("po_amount", 0) or 0),
    })
    merge_estimate_row_scalar_fields_into_editor(row, loaded)
    # Only fill missing numeric fields; never overwrites real saved values.
    try:
        from pages.estimate_editor import ensure_numeric_defaults
    except ImportError:
        from app.pages.estimate_editor import ensure_numeric_defaults  # type: ignore
    ensure_numeric_defaults(loaded)
    st.session_state["estimate_editor_state"] = loaded
    st.session_state["loaded_estimate_id"] = selected_id
    st.session_state["estimate_editor_quote_ready"] = True
    # Ensure editor defaults exist (does not overwrite loaded values).
    ensure_state()


def _new_estimate() -> None:
    _reset_estimate_editor_transients(clear_import_hints=True)
    st.session_state["estimate_editor_state"] = blank_estimate()
    st.session_state["loaded_estimate_id"] = None
    st.session_state["estimate_editor_quote_ready"] = False
    ensure_state()
    st.session_state["estimates_view"] = "edit"
    st.rerun()


def _open_estimate_editor(estimate_id: str) -> None:
    _load_estimate_into_session(estimate_id)
    st.session_state["estimates_view"] = "edit"
    st.rerun()


def _select_estimate(estimate_id: str) -> None:
    st.session_state["est_selected_id"] = str(estimate_id or "").strip()


def _consume_estimate_query_selection() -> None:
    try:
        raw = st.query_params.get("est")
    except Exception:
        raw = None
    eid = raw[0] if isinstance(raw, list) and raw else raw
    eid = str(eid or "").strip()
    if not eid:
        return
    st.session_state["est_selected_id"] = eid
    try:
        action = str(st.query_params.get("est_action") or "").strip()
        if action == "more":
            st.session_state["est_ref_show_more"] = eid
        for key in ("est", "est_action"):
            if key in st.query_params:
                del st.query_params[key]
    except Exception:
        pass


def _estimate_select_href(estimate_id: str, *, action: str | None = None) -> str:
    params = {"est": str(estimate_id or "").strip()}
    if action:
        params["est_action"] = action
    return "?" + urlencode(params)


def _estimate_text(val: Any, fallback: str = "—") -> str:
    if val is None:
        return fallback
    try:
        if pd.isna(val):
            return fallback
    except Exception:
        pass
    s = str(val).strip()
    return s if s else fallback


def _estimate_money_zero(val: Any) -> str:
    s = _estimate_money_display(val)
    return s if s else "$0.00"


def _estimate_decimal(val: Any) -> Decimal:
    if val is None:
        return Decimal("0")
    try:
        if pd.isna(val):
            return Decimal("0")
    except Exception:
        pass
    try:
        return Decimal(str(val).replace("$", "").replace(",", "").strip() or "0")
    except Exception:
        return Decimal("0")


def _estimate_percent(part: Decimal, total: Decimal) -> str:
    if total <= 0:
        return "0%"
    pct = (part / total * Decimal("100")).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return f"{pct}%"


def _estimate_date_display(val: Any) -> str:
    s = _estimate_text(val, "")
    if not s:
        return "—"
    return s[:10]


def _estimate_json(row: pd.Series | dict[str, Any]) -> dict[str, Any]:
    raw = row.get("estimate_json") if hasattr(row, "get") else None
    return raw if isinstance(raw, dict) else {}


def _estimate_description(row: pd.Series | dict[str, Any], *, max_len: int = 90) -> str:
    ej = _estimate_json(row)
    candidates = [
        row.get("estimate_description") if hasattr(row, "get") else "",
        ej.get("estimate_description"),
        ej.get("job"),
        ej.get("job_name"),
        row.get("scope_of_work") if hasattr(row, "get") else "",
    ]
    for raw in candidates:
        s = str(raw or "").strip()
        if s:
            s = s.splitlines()[0].strip()
            return s[:max_len] + ("…" if len(s) > max_len else "")
    return "No description"


def _estimate_project_title(row: pd.Series | dict[str, Any]) -> str:
    ej = _estimate_json(row)
    for raw in (
        ej.get("project_title"),
        ej.get("project_name"),
        ej.get("job_name"),
        ej.get("job"),
        row.get("estimate_description") if hasattr(row, "get") else "",
    ):
        s = str(raw or "").strip()
        if s:
            return s[:90] + ("…" if len(s) > 90 else "")
    return "Untitled project"


def _estimate_project_type(row: pd.Series | dict[str, Any]) -> str:
    ej = _estimate_json(row)
    row_type = row.get("project_type") if hasattr(row, "get") else ""
    return _estimate_text(ej.get("project_type") or row_type, "—")


def _estimate_created_by(row: pd.Series | dict[str, Any]) -> str:
    if not hasattr(row, "get"):
        return "—"
    ej = _estimate_json(row)
    for key in ("created_by", "created_by_name", "created_by_email", "salesperson", "prepared_by"):
        val = row.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
        val = ej.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return "—"


def _estimate_expiration_date(row: pd.Series | dict[str, Any]) -> str:
    if not hasattr(row, "get"):
        return "—"
    ej = _estimate_json(row)
    for key in ("expiration_date", "expires_at", "valid_until", "expiry_date"):
        val = row.get(key)
        if val is not None and str(val).strip():
            return _estimate_date_display(val)
        val = ej.get(key)
        if val is not None and str(val).strip():
            return _estimate_date_display(val)
    return "—"


def _estimate_date(row: pd.Series | dict[str, Any]) -> str:
    if not hasattr(row, "get"):
        return "—"
    ej = _estimate_json(row)
    for key in ("estimate_date", "created_at", "updated_at", "date"):
        val = row.get(key)
        if val is not None and str(val).strip():
            return _estimate_date_display(val)
        val = ej.get(key)
        if val is not None and str(val).strip():
            return _estimate_date_display(val)
    return "—"


def _customer_name_maps(customers: list[dict[str, Any]]) -> tuple[dict[str, str], dict[str, str]]:
    by_id: dict[str, str] = {}
    by_name: dict[str, str] = {}
    for row in customers:
        cid = str(row.get("id") or "").strip()
        name = str(row.get("customer_name") or "").strip()
        if cid and name:
            by_id[cid] = name
            by_name[name] = cid
    return by_id, by_name


def _estimate_customer_name(row: pd.Series | dict[str, Any], customer_by_id: dict[str, str]) -> str:
    cid = str(row.get("customer_id") or "").strip() if hasattr(row, "get") else ""
    if cid and cid in customer_by_id:
        return customer_by_id[cid]
    ej = _estimate_json(row)
    row_customer = row.get("customer_name") if hasattr(row, "get") else ""
    return _estimate_text(ej.get("customer_name") or row_customer, "—")


def _status_key(status: Any) -> str:
    s = str(status or "").strip().lower()
    if s in {"submitted", "sent_to_customer"}:
        return "sent"
    if s in {"accepted", "awarded", "po_received"}:
        return "approved"
    if s in {"waiting", "in_review", "review"}:
        return "pending"
    return s or "draft"


def _status_label(status: Any) -> str:
    key = _status_key(status)
    return {
        "approved": "Approved",
        "draft": "Draft",
        "sent": "Sent",
        "pending": "Pending",
        "rejected": "Rejected",
    }.get(key, key.replace("_", " ").title())


def _status_pill_html(status: Any) -> str:
    key = _status_key(status)
    palette = {
        "approved": ("#DCFCE7", "#15803D", "#86EFAC"),
        "draft": ("#F3F4F6", "#374151", "#D1D5DB"),
        "sent": ("#DBEAFE", "#1D4ED8", "#93C5FD"),
        "pending": ("#FEF3C7", "#B45309", "#FCD34D"),
        "rejected": ("#FEE2E2", "#B91C1C", "#FCA5A5"),
    }
    bg, fg, border = palette.get(key, ("#F3F4F6", "#374151", "#D1D5DB"))
    return (
        f'<span class="ips-est-status-pill" style="background:{bg};color:{fg};border-color:{border};">'
        f"{html.escape(_status_label(status))}</span>"
    )


def _line_item_rows(row: pd.Series | dict[str, Any], *, limit: int | None = None) -> list[dict[str, Any]]:
    ej = _estimate_json(row)
    out: list[dict[str, Any]] = []
    for item in ej.get("materials", []) or []:
        name = str(item.get("item") or item.get("description") or "Material").strip()
        qty = item.get("qty") or item.get("quantity") or 0
        unit_price = item.get("unit_price") or item.get("sell_price") or item.get("purchase_cost") or 0
        out.append({
            "Item": name,
            "Description": str(item.get("description") or name),
            "Qty": qty,
            "Unit": str(item.get("unit") or "ea"),
            "Unit Price": _estimate_money_zero(unit_price),
            "Total": _estimate_money_zero(_estimate_decimal(qty) * _estimate_decimal(unit_price)),
        })
    for item in ej.get("labor", []) or []:
        name = str(item.get("classification") or "Labor").strip()
        qty = _estimate_decimal(item.get("headcount")) * _estimate_decimal(item.get("days") or 1)
        rate = item.get("rate") or item.get("st_rate") or item.get("hourly_rate") or 0
        out.append({
            "Item": name,
            "Description": "Labor crew / classification",
            "Qty": qty,
            "Unit": "crew day",
            "Unit Price": _estimate_money_zero(rate),
            "Total": _estimate_money_zero(_estimate_decimal(qty) * _estimate_decimal(rate)),
        })
    for item in ej.get("equipment", []) or []:
        name = str(item.get("equipment_item") or "Equipment").strip()
        qty = _estimate_decimal(item.get("qty") or 0) * _estimate_decimal(item.get("duration") or 1)
        rate = item.get("rate") or item.get("daily_rate") or item.get("weekly_rate") or 0
        out.append({
            "Item": name,
            "Description": str(item.get("basis") or "Equipment rental/tool"),
            "Qty": qty,
            "Unit": str(item.get("basis") or "day"),
            "Unit Price": _estimate_money_zero(rate),
            "Total": _estimate_money_zero(_estimate_decimal(qty) * _estimate_decimal(rate)),
        })
    return out[:limit] if limit is not None else out


def _estimate_breakdown(row: pd.Series | dict[str, Any]) -> dict[str, Decimal]:
    ej = _estimate_json(row)
    labor = _estimate_decimal(row.get("labor_total") if hasattr(row, "get") else None)
    equipment = _estimate_decimal(row.get("equipment_total") if hasattr(row, "get") else None)
    material = _estimate_decimal(row.get("material_total") if hasattr(row, "get") else None)
    if labor <= 0:
        for item in ej.get("labor", []) or []:
            labor += _estimate_decimal(item.get("headcount")) * _estimate_decimal(item.get("days") or 1) * _estimate_decimal(item.get("rate") or item.get("st_rate"))
    if equipment <= 0:
        for item in ej.get("equipment", []) or []:
            equipment += _estimate_decimal(item.get("qty")) * _estimate_decimal(item.get("duration") or 1) * _estimate_decimal(item.get("rate") or item.get("daily_rate"))
    if material <= 0:
        for item in ej.get("materials", []) or []:
            material += _estimate_decimal(item.get("qty")) * _estimate_decimal(item.get("unit_price") or item.get("sell_price") or item.get("purchase_cost"))
    grand = _estimate_decimal(row.get("proposal_total") if hasattr(row, "get") else None)
    other = grand - labor - equipment - material
    if other < 0:
        other = Decimal("0")
    return {"Labor": labor, "Materials": material, "Equipment": equipment, "Other": other}


def _donut_svg_html(parts: dict[str, Decimal]) -> str:
    colors = {"Labor": "#2563EB", "Materials": "#10B981", "Equipment": "#F59E0B", "Other": "#94A3B8"}
    total = sum(parts.values(), Decimal("0"))
    if total <= 0:
        total = Decimal("1")
    circumference = Decimal("100")
    offset = Decimal("25")
    circles: list[str] = []
    for name, value in parts.items():
        pct = max(Decimal("0"), value) / total * circumference
        circles.append(
            f'<circle class="ips-est-donut-seg" r="15.9155" cx="18" cy="18" '
            f'fill="transparent" stroke="{colors[name]}" stroke-width="4" '
            f'stroke-dasharray="{pct:.3f} {circumference - pct:.3f}" '
            f'stroke-dashoffset="{offset:.3f}"></circle>'
        )
        offset -= pct
    legend = "".join(
        f'<div class="ips-est-donut-legend-row"><span><i style="background:{colors[name]}"></i>{html.escape(name)}</span>'
        f'<strong>{html.escape(_estimate_money_zero(value))} · {html.escape(_estimate_percent(value, sum(parts.values(), Decimal("0"))))}</strong></div>'
        for name, value in parts.items()
    )
    return (
        '<div class="ips-est-donut-wrap"><svg viewBox="0 0 36 36" class="ips-est-donut">'
        '<circle r="15.9155" cx="18" cy="18" fill="transparent" stroke="#E5EAF2" stroke-width="4"></circle>'
        + "".join(circles)
        + "</svg><div class=\"ips-est-donut-legend\">"
        + legend
        + f'<div class="ips-est-donut-total"><span>Total</span><strong>{html.escape(_estimate_money_zero(sum(parts.values(), Decimal("0"))))}</strong></div>'
        + "</div></div>"
    )


def _inject_estimates_page_styles() -> None:
    key = "ips_estimates_refactor_styles_v1"
    if st.session_state.get(key):
        return
    st.session_state[key] = True
    st.markdown(
        """
        <style>
        section[data-testid="stMain"] {
            background: #F6F8FB !important;
        }
        .ips-est-header-card,
        .ips-est-filter-card,
        .ips-est-table-card,
        .ips-est-detail-panel,
        .ips-est-summary-card {
            background: #FFFFFF;
            border: 1px solid #E5EAF2;
            border-radius: 14px;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
        }
        .ips-est-header-card {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 1rem;
            padding: 1rem 1.1rem;
            margin: 0 0 0.75rem;
        }
        .ips-est-header-left {
            display: flex;
            align-items: center;
            gap: 0.8rem;
        }
        .ips-est-icon {
            align-items: center;
            background: #EFF6FF;
            border-radius: 12px;
            color: #2563EB;
            display: inline-flex;
            font-size: 1.35rem;
            height: 44px;
            justify-content: center;
            width: 44px;
        }
        .ips-est-title {
            color: #111827;
            font-size: 1.35rem;
            font-weight: 750;
            letter-spacing: -0.02em;
            margin: 0;
        }
        .ips-est-subtitle {
            color: #64748B;
            font-size: 0.92rem;
            margin: 0.08rem 0 0;
        }
        .ips-est-filter-card {
            padding: 0.8rem;
            margin-bottom: 0.85rem;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-table-anchor),
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-detail-anchor) {
            background: transparent !important;
            border: none !important;
            padding: 0 !important;
        }
        .ips-est-table-card {
            overflow: hidden;
            margin-bottom: 0.9rem;
        }
        .ips-est-table-head,
        .ips-est-table-row {
            display: grid;
            grid-template-columns: 1.05fr 2.15fr 1.25fr 1fr 1fr 0.9fr 0.8fr 1fr 0.65fr;
            gap: 0;
            align-items: center;
        }
        .ips-est-table-head {
            background: #F8FAFC;
            border-bottom: 1px solid #E5EAF2;
            color: #64748B;
            font-size: 0.74rem;
            font-weight: 700;
            letter-spacing: 0.02em;
            padding: 0.65rem 0.85rem;
            text-transform: uppercase;
        }
        .ips-est-table-head span::after {
            color: #CBD5E1;
            content: " ↕";
            font-size: 0.7rem;
        }
        .ips-est-table-row {
            border-left: 4px solid transparent;
            border-bottom: 1px solid #EEF2F7;
            color: #111827;
            min-height: 56px;
            padding: 0.48rem 0.85rem 0.48rem calc(0.85rem - 4px);
        }
        .ips-est-table-row.is-selected {
            background: #EFF6FF;
            border-left-color: #2563EB;
        }
        .ips-est-quote-link {
            color: #2563EB;
            font-size: 0.9rem;
            font-weight: 700;
            text-decoration: none;
        }
        .ips-est-project-title {
            color: #111827;
            font-size: 0.9rem;
            font-weight: 700;
            line-height: 1.25;
            margin: 0;
        }
        .ips-est-project-desc {
            color: #64748B;
            font-size: 0.78rem;
            line-height: 1.25;
            margin: 0.1rem 0 0;
        }
        .ips-est-cell {
            color: #334155;
            font-size: 0.84rem;
            line-height: 1.25;
            overflow-wrap: anywhere;
        }
        .ips-est-status-pill {
            border: 1px solid;
            border-radius: 999px;
            display: inline-flex;
            font-size: 0.72rem;
            font-weight: 700;
            line-height: 1;
            padding: 0.28rem 0.55rem;
            white-space: nowrap;
        }
        .ips-est-actions {
            color: #64748B;
            display: flex;
            gap: 0.3rem;
            justify-content: flex-end;
        }
        .ips-est-actions a {
            align-items: center;
            border: 1px solid #E5EAF2;
            border-radius: 8px;
            color: #475569;
            display: inline-flex;
            height: 28px;
            justify-content: center;
            text-decoration: none;
            width: 28px;
        }
        .ips-est-actions a:hover {
            background: #EFF6FF;
            border-color: #BFDBFE;
            color: #2563EB;
        }
        .ips-est-detail-panel {
            padding: 1rem;
            margin-bottom: 1rem;
        }
        .ips-est-detail-head {
            display: grid;
            grid-template-columns: 1.8fr 1.2fr 1fr;
            gap: 1rem;
            align-items: start;
            border-bottom: 1px solid #E5EAF2;
            padding-bottom: 0.85rem;
            margin-bottom: 0.85rem;
        }
        .ips-est-detail-title {
            color: #111827;
            font-size: 1.25rem;
            font-weight: 800;
            margin: 0;
        }
        .ips-est-detail-title-row {
            align-items: center;
            display: flex;
            gap: 0.6rem;
            flex-wrap: wrap;
        }
        .ips-est-detail-sub {
            color: #64748B;
            font-size: 0.9rem;
            margin: 0.18rem 0;
        }
        .ips-est-meta-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 0.3rem;
        }
        .ips-est-meta-grid span {
            color: #64748B;
            display: block;
            font-size: 0.74rem;
            font-weight: 700;
            text-transform: uppercase;
        }
        .ips-est-meta-grid strong {
            color: #111827;
            font-size: 0.86rem;
        }
        .ips-est-summary-card {
            min-height: 230px;
            padding: 0.9rem;
        }
        .ips-est-card-title {
            color: #111827;
            font-size: 0.95rem;
            font-weight: 750;
            margin: 0 0 0.7rem;
        }
        .ips-est-kv {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            border-bottom: 1px solid #F1F5F9;
            padding: 0.42rem 0;
        }
        .ips-est-kv span {
            color: #64748B;
            font-size: 0.8rem;
        }
        .ips-est-kv strong {
            color: #111827;
            font-size: 0.82rem;
            text-align: right;
        }
        .ips-est-donut-wrap {
            align-items: center;
            display: grid;
            grid-template-columns: 120px 1fr;
            gap: 0.8rem;
        }
        .ips-est-donut {
            height: 120px;
            transform: rotate(-90deg);
            width: 120px;
        }
        .ips-est-donut-seg {
            transition: stroke-dasharray 0.2s ease;
        }
        .ips-est-donut-legend-row,
        .ips-est-donut-total {
            align-items: center;
            display: flex;
            justify-content: space-between;
            gap: 0.5rem;
            padding: 0.25rem 0;
        }
        .ips-est-donut-legend-row span,
        .ips-est-donut-total span {
            align-items: center;
            color: #64748B;
            display: inline-flex;
            font-size: 0.78rem;
            gap: 0.35rem;
        }
        .ips-est-donut-legend-row i {
            border-radius: 999px;
            display: inline-block;
            height: 8px;
            width: 8px;
        }
        .ips-est-donut-legend-row strong,
        .ips-est-donut-total strong {
            color: #111827;
            font-size: 0.78rem;
        }
        .ips-est-donut-total {
            border-top: 1px solid #E5EAF2;
            margin-top: 0.3rem;
            padding-top: 0.45rem;
        }
        .ips-est-section-title-row {
            align-items: center;
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            margin: 0.95rem 0 0.45rem;
        }
        .ips-est-section-title-row h4 {
            color: #111827;
            font-size: 0.98rem;
            font-weight: 750;
            margin: 0;
        }
        div[data-testid="stTextInput"] input,
        div[data-testid="stDateInput"] input,
        div[data-testid="stSelectbox"] [data-baseweb="select"] > div {
            border-color: #E5EAF2 !important;
            border-radius: 10px !important;
            min-height: 40px !important;
        }
        [data-testid="stTabs"] [role="tablist"] {
            border-bottom: 1px solid #E5EAF2 !important;
            gap: 1rem !important;
        }
        [data-testid="stTabs"] [role="tab"] {
            border-radius: 0 !important;
            color: #64748B !important;
            padding: 0.45rem 0 !important;
        }
        [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
            border-bottom: 2px solid #2563EB !important;
            color: #2563EB !important;
        }
        @media (max-width: 1100px) {
            .ips-est-table-head,
            .ips-est-table-row {
                grid-template-columns: 1fr 1.7fr 1.1fr 0.9fr 0.8fr;
            }
            .ips-est-hide-tablet {
                display: none;
            }
            .ips-est-detail-head {
                grid-template-columns: 1fr;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_estimates_header(df_export: pd.DataFrame) -> None:
    st.markdown(
        """
        <div class="ips-est-header-card">
          <div class="ips-est-header-left">
            <div class="ips-est-icon">📄</div>
            <div>
              <h1 class="ips-est-title">Estimates</h1>
              <p class="ips-est-subtitle">Create, review, and manage all project estimates.</p>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _, h2, h3, h4 = st.columns([5, 1.05, 1.25, 1.35], gap="small")
    with h2:
        st.download_button(
            "Export",
            data=df_export.to_csv(index=False).encode("utf-8"),
            file_name="estimates_export.csv",
            mime="text/csv",
            use_container_width=True,
            key="est_ref_export",
        )
    with h3:
        if st.button("Import Existing Quotes", type="secondary", use_container_width=True, key="est_ref_import"):
            _reset_estimate_editor_transients(clear_import_hints=True)
            st.session_state["estimates_view"] = "import"
            st.rerun()
    with h4:
        if st.button("+ New Estimate", type="primary", use_container_width=True, key="est_ref_new"):
            _new_estimate()


def _estimate_filtered_df(
    df: pd.DataFrame,
    *,
    customer_by_id: dict[str, str],
    customer_name_to_id: dict[str, str],
) -> pd.DataFrame:
    st.markdown('<div class="ips-est-filter-card">', unsafe_allow_html=True)
    c1, c2, c3, c4, c5, c6 = st.columns([2.2, 1.25, 1.45, 1.45, 1.35, 1.0], gap="small")
    with c1:
        search = st.text_input("Search", placeholder="Search estimates...", key="est_ref_search", label_visibility="collapsed")
    statuses = ["All Statuses"]
    if not df.empty and "status" in df.columns:
        statuses += sorted({_status_label(v) for v in df["status"].dropna().tolist()})
    with c2:
        status_pick = st.selectbox("Status", statuses, key="est_ref_status", label_visibility="collapsed")
    customers = ["All Customers"] + sorted(customer_name_to_id.keys())
    with c3:
        customer_pick = st.selectbox("Customer", customers, key="est_ref_customer", label_visibility="collapsed")
    creators = ["All Created By"]
    if not df.empty:
        creators += sorted({_estimate_created_by(r) for _, r in df.iterrows() if _estimate_created_by(r) != "—"})
    with c4:
        creator_pick = st.selectbox("Created By", creators, key="est_ref_creator", label_visibility="collapsed")
    with c5:
        date_range = st.date_input("Date range", value=(), key="est_ref_date_range", label_visibility="collapsed")
    with c6:
        if st.button("Clear Filters", use_container_width=True, key="est_ref_clear_filters"):
            for key in ("est_ref_search", "est_ref_status", "est_ref_customer", "est_ref_creator", "est_ref_date_range"):
                st.session_state.pop(key, None)
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    out = df.copy()
    if search.strip() and not out.empty:
        s = search.strip().lower()
        def _hay(row: pd.Series) -> str:
            return " ".join([
                _estimate_text(row.get("quote_number"), ""),
                _estimate_project_title(row),
                _estimate_description(row),
                _estimate_customer_name(row, customer_by_id),
                _estimate_created_by(row),
                _estimate_text(row.get("po_number"), ""),
            ]).lower()
        out = out[out.apply(lambda r: s in _hay(r), axis=1)]
    if status_pick != "All Statuses" and not out.empty:
        out = out[out["status"].map(_status_label) == status_pick] if "status" in out.columns else out
    if customer_pick != "All Customers" and not out.empty:
        cid = customer_name_to_id.get(customer_pick, "")
        out = out[out["customer_id"].astype(str) == cid] if cid and "customer_id" in out.columns else out
    if creator_pick != "All Created By" and not out.empty:
        out = out[out.apply(lambda r: _estimate_created_by(r) == creator_pick, axis=1)]
    if isinstance(date_range, tuple) and len(date_range) == 2 and not out.empty:
        start, end = date_range
        def _in_range(row: pd.Series) -> bool:
            raw = _estimate_date(row)
            if raw == "—":
                return False
            try:
                d = pd.to_datetime(raw).date()
                return start <= d <= end
            except Exception:
                return True
        out = out[out.apply(_in_range, axis=1)]
    return out


def _render_estimate_table(
    df: pd.DataFrame,
    *,
    customer_by_id: dict[str, str],
) -> str | None:
    if df.empty:
        st.markdown(
            '<div class="ips-est-table-card" style="padding:1.2rem;color:#64748B;">No estimates match the current filters.</div>',
            unsafe_allow_html=True,
        )
        return None
    selected_id = str(st.session_state.get("est_selected_id") or "").strip()
    ids = [str(r.get("id") or "").strip() for _, r in df.iterrows() if str(r.get("id") or "").strip()]
    if selected_id not in ids and ids:
        selected_id = ids[0]
        st.session_state["est_selected_id"] = selected_id

    st.markdown('<span class="ips-est-table-anchor"></span><div class="ips-est-table-card">', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="ips-est-table-head">
          <span>Estimate #</span><span>Project / Description</span><span>Customer</span>
          <span class="ips-est-hide-tablet">Estimate Date</span><span class="ips-est-hide-tablet">Expiration Date</span>
          <span>Total</span><span>Status</span><span class="ips-est-hide-tablet">Created By</span><span>Actions</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    for _, row in df.iterrows():
        eid = str(row.get("id") or "").strip()
        if not eid:
            continue
        is_selected = eid == selected_id
        quote = _estimate_text(row.get("quote_number"), f"EST-{eid[:8]}")
        project = _estimate_project_title(row)
        desc = _estimate_description(row)
        customer = _estimate_customer_name(row, customer_by_id)
        total = _estimate_money_zero(row.get("proposal_total") or row.get("final_bid"))
        row_cls = "ips-est-table-row is-selected" if is_selected else "ips-est-table-row"
        view_href = html.escape(_estimate_select_href(eid), quote=True)
        more_href = html.escape(_estimate_select_href(eid, action="more"), quote=True)
        st.markdown(
            f"""
            <div class="{row_cls}">
              <div><a class="ips-est-quote-link" href="{view_href}">{html.escape(quote)}</a></div>
              <div><p class="ips-est-project-title">{html.escape(project)}</p><p class="ips-est-project-desc">{html.escape(desc)}</p></div>
              <div class="ips-est-cell">{html.escape(customer)}</div>
              <div class="ips-est-cell ips-est-hide-tablet">{html.escape(_estimate_date(row))}</div>
              <div class="ips-est-cell ips-est-hide-tablet">{html.escape(_estimate_expiration_date(row))}</div>
              <div class="ips-est-cell"><strong>{html.escape(total)}</strong></div>
              <div>{_status_pill_html(row.get("status"))}</div>
              <div class="ips-est-cell ips-est-hide-tablet">{html.escape(_estimate_created_by(row))}</div>
              <div class="ips-est-actions"><a href="{view_href}" title="View">👁</a><a href="{more_href}" title="More">⋯</a></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)
    return selected_id


def _render_kv(label: str, value: Any) -> None:
    st.markdown(
        f'<div class="ips-est-kv"><span>{html.escape(label)}</span><strong>{html.escape(str(value))}</strong></div>',
        unsafe_allow_html=True,
    )


def _render_overview_tab(row: pd.Series, *, customer_by_id: dict[str, str], linked_job: str) -> None:
    c1, c2, c3 = st.columns(3, gap="medium")
    total = _estimate_decimal(row.get("proposal_total") or row.get("final_bid"))
    tax = _estimate_decimal(row.get("sales_tax_total") or row.get("tax"))
    subtotal = _estimate_decimal(row.get("subtotal")) or max(Decimal("0"), total - tax)
    markup = _estimate_decimal(row.get("markup_total") or row.get("profit_total"))
    with c1:
        st.markdown('<div class="ips-est-summary-card"><h3 class="ips-est-card-title">Estimate Summary</h3>', unsafe_allow_html=True)
        _render_kv("Description", _estimate_description(row))
        _render_kv("Project Type", _estimate_project_type(row))
        _render_kv("Customer", _estimate_customer_name(row, customer_by_id))
        st.markdown(f'<div class="ips-est-kv"><span>Status</span><strong>{_status_pill_html(row.get("status"))}</strong></div>', unsafe_allow_html=True)
        _render_kv("Linked Job", linked_job or "—")
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="ips-est-summary-card"><h3 class="ips-est-card-title">Financial Summary</h3>', unsafe_allow_html=True)
        _render_kv("Subtotal", _estimate_money_zero(subtotal))
        _render_kv("Tax", _estimate_money_zero(tax))
        _render_kv("Total", _estimate_money_zero(total))
        _render_kv("Markup", _estimate_money_zero(markup))
        _render_kv("Grand Total", _estimate_money_zero(total))
        st.markdown("</div>", unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="ips-est-summary-card"><h3 class="ips-est-card-title">Estimate Totals</h3>', unsafe_allow_html=True)
        st.markdown(_donut_svg_html(_estimate_breakdown(row)), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        '<div class="ips-est-section-title-row"><h4>Top Line Items</h4></div>',
        unsafe_allow_html=True,
    )
    lines = _line_item_rows(row, limit=5)
    if lines:
        st.dataframe(pd.DataFrame(lines), use_container_width=True, hide_index=True)
    else:
        st.info("No line items found on this estimate.")
    if st.button("View All Line Items", key="est_ref_view_all_lines"):
        st.session_state["est_ref_detail_tab_hint"] = "Line Items"


def _render_detail_tab_table(title: str, rows: list[dict[str, Any]], empty: str) -> None:
    st.markdown(f"#### {title}")
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info(empty)


def _render_estimate_detail_panel(
    row: pd.Series,
    *,
    customer_by_id: dict[str, str],
    linked_job: str,
) -> None:
    eid = str(row.get("id") or "").strip()
    quote = _estimate_text(row.get("quote_number"), f"EST-{eid[:8]}")
    ej = _estimate_json(row)
    st.markdown('<span class="ips-est-detail-anchor"></span><div class="ips-est-detail-panel">', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="ips-est-detail-head">
          <div>
            <div class="ips-est-detail-title-row">
              <h2 class="ips-est-detail-title">{html.escape(quote)}</h2>{_status_pill_html(row.get("status"))}
            </div>
            <p class="ips-est-detail-sub"><strong>{html.escape(_estimate_project_title(row))}</strong></p>
            <p class="ips-est-detail-sub">{html.escape(_estimate_customer_name(row, customer_by_id))}</p>
          </div>
          <div class="ips-est-meta-grid">
            <div><span>Estimate Date</span><strong>{html.escape(_estimate_date(row))}</strong></div>
            <div><span>Expiration Date</span><strong>{html.escape(_estimate_expiration_date(row))}</strong></div>
            <div><span>Created By</span><strong>{html.escape(_estimate_created_by(row))}</strong></div>
          </div>
          <div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    a1, a2, a3, a4, _ = st.columns([1, 1.2, 0.8, 0.75, 4], gap="small")
    with a1:
        if st.button("Edit", type="primary", key=f"est_ref_detail_edit_{eid}", use_container_width=True):
            _open_estimate_editor(eid)
    with a2:
        if st.button("Send Estimate", key=f"est_ref_detail_send_{eid}", use_container_width=True):
            st.info("Use Edit to preview/export the proposal with the existing estimate workflow.")
    with a3:
        if st.button("More", key=f"est_ref_detail_more_{eid}", use_container_width=True):
            st.session_state["est_ref_show_more"] = eid if st.session_state.get("est_ref_show_more") != eid else ""
            st.rerun()
    with a4:
        if st.button("⌃", key=f"est_ref_detail_collapse_{eid}", help="Collapse detail panel", use_container_width=True):
            st.session_state.pop("est_selected_id", None)
            st.rerun()
    if st.session_state.get("est_ref_show_more") == eid:
        m1, m2, _ = st.columns([1.2, 1.4, 4], gap="small")
        with m1:
            if linked_job:
                more_label = "Open Job"
                more_disabled = False
            else:
                more_label = "Create Job"
                more_disabled = not _estimates_page_can_edit()
                try:
                    from services.job_from_estimate import estimate_status_allows_job_creation
                except ImportError:
                    from app.services.job_from_estimate import estimate_status_allows_job_creation  # type: ignore
                if not str(row.get("customer_id") or "").strip() or not estimate_status_allows_job_creation(str(row.get("status") or "")):
                    more_disabled = True
            if st.button(more_label, key=f"est_ref_more_job_{eid}", use_container_width=True, disabled=more_disabled):
                job_rows = _fetch_jobs_for_estimate_links()
                job = next((j for j in job_rows if str(j.get("estimate_id") or "") == eid), None)
                if not job:
                    try:
                        from services.job_from_estimate import create_job_from_estimate
                    except ImportError:
                        from app.services.job_from_estimate import create_job_from_estimate  # type: ignore
                    res = create_job_from_estimate(eid)
                    if res.ok and res.job:
                        _clear_estimates_page_cache()
                        job = res.job
                        st.success(res.message)
                    elif res.message:
                        st.error(res.message)
                if job and job.get("id"):
                    try:
                        from ui import IPS_NAV_PENDING_KEY
                    except ImportError:
                        from app.ui import IPS_NAV_PENDING_KEY  # type: ignore
                    st.session_state[IPS_NAV_PENDING_KEY] = "Job Database"
                    st.session_state["job_mode"] = "edit"
                    st.session_state["job_edit_id"] = str(job["id"])
                    st.rerun()
        with m2:
            if st.button("Delete Estimate", key=f"est_ref_more_delete_{eid}", use_container_width=True, disabled=not _estimates_page_can_edit()):
                st.session_state["est_ref_confirm_delete"] = eid
                st.rerun()
        if st.session_state.get("est_ref_confirm_delete") == eid:
            st.warning("Delete this estimate? Linked jobs are kept and unlinked from this quote.")
            d1, d2, _ = st.columns([1, 1, 4], gap="small")
            with d1:
                if st.button("Confirm Delete", key=f"est_ref_delete_confirm_{eid}", type="primary"):
                    delete_estimate_unlink_first(eid, admin_read=_estimates_page_admin_read())
                    _clear_estimates_page_cache()
                    st.session_state.pop("est_selected_id", None)
                    st.session_state.pop("est_ref_confirm_delete", None)
                    st.success("Estimate deleted.")
                    st.rerun()
            with d2:
                if st.button("Cancel", key=f"est_ref_delete_cancel_{eid}"):
                    st.session_state.pop("est_ref_confirm_delete", None)
                    st.rerun()

    tabs = st.tabs(["Overview", "Line Items", "Labor", "Materials", "Equipment", "Attachments", "Notes", "Activity"])
    with tabs[0]:
        _render_overview_tab(row, customer_by_id=customer_by_id, linked_job=linked_job)
    with tabs[1]:
        _render_detail_tab_table("Line Items", _line_item_rows(row), "No line items found on this estimate.")
    with tabs[2]:
        _render_detail_tab_table("Labor", ej.get("labor", []) or [], "No labor entries found.")
    with tabs[3]:
        _render_detail_tab_table("Materials", ej.get("materials", []) or [], "No material entries found.")
    with tabs[4]:
        _render_detail_tab_table("Equipment", ej.get("equipment", []) or [], "No equipment entries found.")
    with tabs[5]:
        st.info("Attachments are managed in the existing estimate editor/export workflow.")
    with tabs[6]:
        notes = "\n\n".join(
            str(ej.get(k) or row.get(k) or "").strip()
            for k in ("scope_of_work", "exclusions", "additional_charges", "customer_responsibilities")
            if str(ej.get(k) or row.get(k) or "").strip()
        )
        st.text_area("Notes", value=notes, height=180, disabled=True, key=f"est_ref_notes_{eid}")
    with tabs[7]:
        activity_rows = [
            {"Action": "Created", "Date": _estimate_date_display(row.get("created_at")), "By": _estimate_created_by(row)},
            {"Action": "Updated", "Date": _estimate_date_display(row.get("updated_at")), "By": _estimate_created_by(row)},
            {"Action": f"Status: {_status_label(row.get('status'))}", "Date": _estimate_date(row), "By": _estimate_created_by(row)},
        ]
        st.dataframe(pd.DataFrame(activity_rows), use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)


def _render_estimate_management_list() -> None:
    _inject_estimates_page_styles()
    _consume_estimate_query_selection()
    rows = _fetch_estimates_list_rows()
    customers = _fetch_customers_for_import()
    customer_by_id, customer_name_to_id = _customer_name_maps(customers)
    jobs = _fetch_jobs_for_estimate_links()
    job_by_id = {str(r["id"]): r for r in jobs if r.get("id")}
    job_by_estimate_id = {str(r["estimate_id"]): r for r in jobs if r.get("estimate_id")}
    df = pd.DataFrame(rows)
    if df.empty:
        df_export = pd.DataFrame(columns=["Estimate #", "Project / Description", "Customer", "Estimate Date", "Expiration Date", "Total", "Status", "Created By"])
        _render_estimates_header(df_export)
        st.info("No estimates found.")
        return
    if "id" not in df.columns:
        _render_estimates_header(df)
        st.dataframe(df, use_container_width=True, hide_index=True)
        return

    export_rows = []
    for _, row in df.iterrows():
        export_rows.append({
            "Estimate #": _estimate_text(row.get("quote_number"), str(row.get("id") or "")),
            "Project / Description": _estimate_project_title(row),
            "Customer": _estimate_customer_name(row, customer_by_id),
            "Estimate Date": _estimate_date(row),
            "Expiration Date": _estimate_expiration_date(row),
            "Total": _estimate_money_csv(row.get("proposal_total") or row.get("final_bid")),
            "Status": _status_label(row.get("status")),
            "Created By": _estimate_created_by(row),
        })
    df_export = pd.DataFrame(export_rows)
    _render_estimates_header(df_export)

    filtered = _estimate_filtered_df(df, customer_by_id=customer_by_id, customer_name_to_id=customer_name_to_id)
    selected_id = _render_estimate_table(filtered, customer_by_id=customer_by_id)
    if not selected_id:
        return
    selected_rows = filtered[filtered["id"].astype(str) == str(selected_id)]
    if selected_rows.empty:
        return
    row = selected_rows.iloc[0]
    linked_job = ""
    jid = row.get("job_id")
    if jid is not None and pd.notna(jid) and str(jid).strip() in job_by_id:
        job = job_by_id[str(jid).strip()]
        linked_job = job_display_label(job.get("job_number"), job.get("job_name"))
    elif str(row.get("id") or "") in job_by_estimate_id:
        job = job_by_estimate_id[str(row.get("id"))]
        linked_job = job_display_label(job.get("job_number"), job.get("job_name"))
    _render_estimate_detail_panel(row, customer_by_id=customer_by_id, linked_job=linked_job)


def _import_customer_status_short(cls: dict[str, Any] | None) -> str:
    if not cls:
        return "—"
    res = cls.get("resolution")
    if res == "valid_existing":
        return "ID in file (ok)"
    if res == "auto_single":
        return "Auto-matched"
    if res == "choose_ambiguous":
        return "Pick customer (multi)"
    if res == "choose_open":
        return "Pick customer"
    if res == "choose_required":
        return "Pick customer"
    return "—"


def _render_json_ips_estimate_import() -> None:
    st.markdown("### JSON estimate import")
    st.caption(
        "Upload **JSON** exports (same shape as Review / Save: `estimate_json`). "
        "Each file is matched to your **customer directory** using names in the JSON (or vendor metadata). "
        "Confirm the customer below, then use **Import JSON file(s) to database**. "
        "Vendor **PDF** quotes use the section above. Duplicate quote numbers are reassigned on import."
    )

    uploaded = st.file_uploader(
        "Upload JSON",
        type=["json"],
        accept_multiple_files=True,
        key="est_import_json_upload",
    )

    if not uploaded:
        st.caption("Upload one or more JSON estimate files above to preview and import.")
        return

    sig = tuple((i, f.name, len(f.getvalue())) for i, f in enumerate(uploaded))
    if st.session_state.get("estimates_import_sig") != sig:
        for k in list(st.session_state.keys()):
            if str(k).startswith("est_import_cust_"):
                st.session_state.pop(k, None)
        st.session_state["estimates_import_sig"] = sig
        cust_rows = _fetch_customers_for_import()
        cached: list[dict] = []
        for f in uploaded:
            raw = f.getvalue()
            try:
                parsed = parse_estimate_json_bytes(raw)
                merged = coalesce_imported_estimate(parsed)
                qn = str(merged.get("quote_number", "") or "").strip()
                cls = classify_import_customer_matches(merged, cust_rows)
                cid = merged.get("customer_id")
                row_has_id = bool(cid) and cls.get("resolution") == "valid_existing"
                cached.append(
                    {
                        "file": f.name,
                        "kind": "json",
                        "merged": merged,
                        "error": None,
                        "quote_number": qn or "(will assign)",
                        "has_customer_id": "yes" if row_has_id else "needs confirmation",
                        "customer_classify": cls,
                        "customer_status": _import_customer_status_short(cls),
                    }
                )
            except Exception as exc:
                cached.append(
                    {
                        "file": f.name,
                        "kind": "json",
                        "merged": None,
                        "error": str(exc),
                        "quote_number": "—",
                        "has_customer_id": f"Error: {exc}",
                        "customer_classify": None,
                        "customer_status": "—",
                    }
                )
        st.session_state["estimates_import_cache"] = cached

    rows: list[dict] = st.session_state["estimates_import_cache"]
    cust_rows = _fetch_customers_for_import()
    name_map = name_to_customer_id_map(cust_rows)
    all_names = build_sorted_customer_names(cust_rows)
    select_options = [PLACEHOLDER] + all_names

    preview_df = pd.DataFrame(
        [
            {
                "file": r["file"],
                "kind": r["kind"],
                "quote_number": r["quote_number"],
                "customer": r.get("customer_status", "—"),
            }
            for r in rows
        ]
    )
    st.dataframe(preview_df, use_container_width=True, hide_index=True)

    json_ready = [
        (i, r)
        for i, r in enumerate(rows)
        if r.get("kind") == "json" and r.get("merged") is not None and not r.get("error")
    ]

    if json_ready:
        st.markdown("##### Customer for each JSON file")
        st.caption(
            "Imports must be saved against a **real customer record**. "
            "If we found a single strong name match, the customer is pre-selected — change it if needed. "
            f"You cannot import while **{PLACEHOLDER}** is selected."
        )
        for i, r in json_ready:
            cls = r.get("customer_classify") or classify_import_customer_matches(r["merged"], cust_rows)
            st.markdown(f"**{r['file']}**")
            if cls.get("message"):
                st.info(str(cls["message"]))
            key = f"est_import_cust_{i}"
            if key not in st.session_state:
                default_name: str | None = None
                if cls.get("resolution") in ("valid_existing", "auto_single") and cls.get("customer_id"):
                    cid0 = str(cls["customer_id"])
                    default_name = next((n for n, cid in name_map.items() if cid == cid0), None)
                st.session_state[key] = default_name if default_name else PLACEHOLDER
            st.selectbox(
                "Customer directory",
                select_options,
                key=key,
                help="Pick the customer this estimate belongs to. This must match a row in Customers.",
            )

        st.markdown("##### JSON Import (direct)")
        if st.button(
            "Import JSON file(s) to database",
            type="secondary",
            use_container_width=True,
            key="est_import_json_run",
        ):
            errors: list[str] = []
            ok = 0
            notes: list[str] = []
            cust_lookup = _fetch_customers_for_import()
            nm = name_to_customer_id_map(cust_lookup)
            for i, r in json_ready:
                f = uploaded[i]
                merged = r.get("merged")
                if merged is None:
                    errors.append(f"{f.name}: nothing to import")
                    continue
                chosen = st.session_state.get(f"est_import_cust_{i}")
                cid = resolve_picked_customer_id(chosen_label=chosen, name_to_id=nm)
                if not cid:
                    errors.append(
                        f"{f.name}: choose a customer from the directory before importing "
                        f"(cannot save on {PLACEHOLDER!r})."
                    )
                    continue
                try:
                    raw = f.getvalue()
                    merged_save = dict(merged)
                    merged_save["customer_id"] = cid
                    _, suffix = insert_imported_estimate(
                        merged_save, f.name, raw, source_content_type="application/json"
                    )
                    ok += 1
                    if suffix:
                        notes.append(f"{f.name}:{suffix}")
                except Exception as exc:
                    errors.append(f"{f.name}: {exc}")
            if notes:
                for n in notes:
                    st.info(n)
            if errors:
                for e in errors:
                    st.error(e)
            if ok:
                st.success(f"Imported {ok} JSON estimate(s). Returning to list.")
                st.session_state["estimates_view"] = "list"
                st.rerun()


def _render_estimate_import() -> None:
    """PDF import then JSON import (Estimates page when ``estimates_view == \"import\"``)."""
    try:
        from services.pdf_quote_import import render_vendor_pdf_quote_section
    except ImportError:
        from app.services.pdf_quote_import import render_vendor_pdf_quote_section  # type: ignore

    st.markdown("### PDF vendor quotes")
    render_vendor_pdf_quote_section()

    st.markdown("---")
    _render_json_ips_estimate_import()


def render() -> None:
    if "estimates_view" not in st.session_state:
        st.session_state["estimates_view"] = "list"

    # Legacy session value from older builds
    if st.session_state.get("estimates_view") == "editor":
        st.session_state["estimates_view"] = "edit"

    view = st.session_state["estimates_view"]
    if view not in ("list", "import", "edit"):
        st.session_state["estimates_view"] = "list"
        view = "list"

    # Single branding header per request; each branch renders one body section only.
    render_header("Estimates")
    if view == "list":
        _render_estimate_management_list()

    elif view == "import":
        render_crud_list_subtitle("Upload PDF vendor quotes or JSON estimate exports, then return to the editor.")
        with st.container(border=True):
            st.markdown(
                '<span class="ips-list-top-anchor ips-estimate-topbar"></span>',
                unsafe_allow_html=True,
            )
            c1, c2 = st.columns([1, 4])
            with c1:
                if st.button("← Back to list", type="secondary", use_container_width=True, key="est_imp_back"):
                    st.session_state["estimates_view"] = "list"
                    st.rerun()
            with c2:
                _render_estimate_import()

    else:
        # view == "edit"
        render_crud_list_subtitle("Line items, proposal export, and approval — use **Back to list** when finished.")
        with st.container(border=True):
            st.markdown(
                '<span class="ips-list-top-anchor ips-estimate-topbar"></span>',
                unsafe_allow_html=True,
            )
            c1, c2 = st.columns(2, gap="small")
            with c1:
                if st.button("← Back to list", type="secondary", use_container_width=True, key="est_ed_back"):
                    _reset_estimate_editor_transients(clear_import_hints=True)
                    st.session_state["estimates_view"] = "list"
                    st.rerun()
            with c2:
                if st.button(
                    "Import Existing Quotes",
                    type="secondary",
                    use_container_width=True,
                    key="est_ed_imp",
                ):
                    _reset_estimate_editor_transients(clear_import_hints=True)
                    st.session_state["estimates_view"] = "import"
                    st.rerun()
        render_estimate_editor(embedded=True)