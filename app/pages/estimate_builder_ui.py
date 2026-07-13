"""Estimate costing builder tabs (Streamlit UI — no direct Supabase)."""

from __future__ import annotations

import html
from typing import Any, Callable
from uuid import uuid4

import streamlit as st

from app.auth import current_role
from app.components.record_modal import detail_field_html, dialog_card_html, safe_value
from app.components.searchable_select import render_searchable_selectbox
from app.pages._core._crud import is_demo_id
from app.services.estimate_costing_service import (
    DURATION_UNITS,
    LABOR_ROLE_TYPES,
    add_estimate_equipment,
    add_estimate_equipment_batch,
    add_estimate_labor,
    add_estimate_labor_batch,
    add_estimate_material,
    add_estimate_material_batch,
    add_estimate_other_cost,
    add_estimate_other_cost_batch,
    add_estimate_subcontractor,
    add_estimate_subcontractor_batch,
    add_estimate_travel,
    add_estimate_travel_batch,
    calculate_estimate_totals,
    delete_estimate_equipment,
    delete_estimate_labor,
    delete_estimate_material,
    delete_estimate_other_cost,
    delete_estimate_subcontractor,
    delete_estimate_travel,
    get_estimate_bundle,
    get_estimate_labor,
    recalculate_and_save_estimate_totals,
    resolve_global_markup_pct,
    resolve_category_markup_defaults,
    save_category_markup_settings,
    save_global_markup_settings,
    update_estimate_labor,
    update_estimate_labor_batch,
)
from app.services.labor_rates_service import save_default_rates_from_lines
from app.ui.streamlit_perf import fragment, ips_app_rerun
from app.utils.estimate_calculations import TRAVEL_TYPES, calc_travel_line, calc_travel_total
from app.services.proposal_pdf_service import build_customer_quote_bundle
from app.services.pricing_guide_service import create_pricing_item_from_estimate_line
from app.services.estimate_builder_helpers import (
    equipment_line_totals,
    labor_line_totals,
    labor_options_as_select,
    material_line_totals,
    resolve_equipment_cost_rate,
    simple_line_totals,
    travel_defaults,
)
from app.utils.estimate_calculations import margin_warning_class
from app.utils.formatting import fmt_currency, fmt_date
def _estimate_tax_rate(est: dict[str, Any]) -> float:
    return float(est.get("tax_rate") or 0)


def _cost_builder_totals_cache_key(eid: str) -> str:
    return f"ecb_totals_{eid}"


def _read_cost_builder_totals(eid: str, est: dict[str, Any]) -> dict[str, float]:
    cached = st.session_state.get(_cost_builder_totals_cache_key(eid))
    if isinstance(cached, dict) and cached:
        return cached
    return calculate_estimate_totals(eid, tax_rate=_estimate_tax_rate(est))


def _cache_cost_builder_totals(eid: str, totals: dict[str, Any]) -> None:
    if totals:
        st.session_state[_cost_builder_totals_cache_key(eid)] = dict(totals)


def _recalc_and_cache_cost_builder_totals(eid: str, est: dict[str, Any]) -> tuple[bool, str | None]:
    result = recalculate_and_save_estimate_totals(eid, tax_rate=_estimate_tax_rate(est))
    if getattr(result, "ok", False):
        _cache_cost_builder_totals(eid, getattr(result, "data", None) or {})
        return True, ""
    return False, str(getattr(result, "error", None) or "Could not update totals.")


def _service_ok(result) -> tuple[bool, str]:
    if getattr(result, "ok", False):
        return True, ""
    return False, str(getattr(result, "error", None) or "Save failed.")


def _margin_banner_html(margin: float) -> str:
    level = margin_warning_class(margin)
    colors = {
        "danger": ("#991b1b", "#fee2e2"),
        "warning": ("#92400e", "#fef3c7"),
        "ok": ("#166534", "#dcfce7"),
    }
    fg, bg = colors.get(level, colors["ok"])
    label = {
        "danger": "Margin below 10% — review pricing.",
        "warning": "Margin 10–20% — consider adjusting markup.",
        "ok": "Margin above 20%.",
    }[level]
    return (
        f'<div style="background:{bg};color:{fg};border-radius:10px;padding:10px 14px;'
        f'font-size:0.82rem;font-weight:700;margin:8px 0;">{html.escape(label)}</div>'
    )


def render_cost_summary_cards(est: dict[str, Any], totals: dict[str, float] | None = None) -> None:
    t = totals or calculate_estimate_totals(str(est.get("id") or ""))
    cards = [
        ("Total Cost", fmt_currency(t.get("total_cost"))),
        ("Customer Price", fmt_currency(t.get("customer_price"))),
        ("Gross Profit", fmt_currency(t.get("gross_profit"))),
        ("Margin %", f"{t.get('gross_margin_percent', 0):.1f}%"),
    ]
    cols = st.columns(4, gap="small")
    for col, (label, value) in zip(cols, cards):
        with col:
            st.markdown(
                f'<div class="ips-est-summary-card">'
                f'<div class="ips-est-summary-label">{html.escape(label)}</div>'
                f'<div class="ips-est-summary-value">{html.escape(value)}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )
    st.markdown(_margin_banner_html(float(t.get("gross_margin_percent") or 0)), unsafe_allow_html=True)


def _line_form_key(prefix: str, eid: str, field: str) -> str:
    return f"{prefix}_{field}_{eid}"


def _display_field(label: str, value: str) -> None:
    st.markdown(
        f'<div class="ips-estimate-field-muted">{html.escape(label)}</div>'
        f'<div style="font-weight:700;font-size:0.9rem;margin-bottom:6px;">{html.escape(value)}</div>',
        unsafe_allow_html=True,
    )


def _live_totals_card(items: list[tuple[str, str]]) -> None:
    rows = "".join(
        f'<div style="display:flex;justify-content:space-between;gap:10px;margin:5px 0;">'
        f'<span class="ips-estimate-field-muted">{html.escape(label)}</span>'
        f'<span style="font-weight:700;color:#0f172a;">{html.escape(value)}</span>'
        f"</div>"
        for label, value in items
    )
    st.markdown(f'<div class="ips-estimate-live-total-card">{rows}</div>', unsafe_allow_html=True)


def _compact_form_card(title: str) -> None:
    st.markdown('<div class="ips-estimate-add-card ips-estimate-compact-form">', unsafe_allow_html=True)
    st.markdown(f"##### {html.escape(title)}")


def _close_compact_form_card() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def _sync_pick_state(
    k: Callable[[str], str],
    pick: str | None,
    inv_map: dict[str, dict[str, Any]],
    *,
    taxable_key: str = "tax",
) -> dict[str, Any]:
    last_key = k("last_pick")
    if pick and st.session_state.get(last_key) != pick:
        item = inv_map.get(pick, {})
        st.session_state[k("desc")] = str(item.get("description") or item.get("name") or "")
        st.session_state[k("sku")] = str(item.get("sku") or "")
        st.session_state[k("cat")] = str(item.get("category") or "")
        st.session_state[k("unit")] = str(item.get("unit") or "EA")
        st.session_state[k("vendor")] = str(item.get("vendor") or item.get("vendor_name") or "")
        st.session_state[k("vendor_id")] = item.get("vendor_id")
        st.session_state[taxable_key] = bool(item.get("taxable", True))
        st.session_state[last_key] = pick
        return item
    return inv_map.get(pick or "", {})


def _sync_labor_role_state(
    k: Callable[[str], str],
    role: str,
    lab_map: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    last_key = k("last_role")
    if st.session_state.get(last_key) != role:
        opt = lab_map.get(role, {})
        st.session_state[k("str")] = float(opt.get("st_rate") or 0)
        st.session_state[k("otr")] = float(opt.get("ot_rate") or 0)
        st.session_state[last_key] = role
        return opt
    return lab_map.get(role, {})


def _labor_batch_draft_key(key_prefix: str, eid: str) -> str:
    return f"{key_prefix}_lab_batch_{eid}"


def _new_labor_batch_row(
    *,
    role_labels: list[str],
    lab_map: dict[str, dict[str, Any]],
    default_markup: float,
) -> dict[str, str]:
    role = role_labels[0] if role_labels else "Other"
    return {"rid": uuid4().hex[:8], "role": role}


def _seed_labor_batch_row_widgets(
    k: Callable[[str], str],
    row: dict[str, str],
    *,
    lab_map: dict[str, dict[str, Any]],
    default_markup: float,
) -> None:
    rid = str(row.get("rid") or "")
    role = str(row.get("role") or "Other")
    if not rid:
        return
    opt = lab_map.get(role, {})
    if k(f"role_{rid}") not in st.session_state:
        st.session_state[k(f"role_{rid}")] = role
    if k(f"str_{rid}") not in st.session_state:
        st.session_state[k(f"str_{rid}")] = float(opt.get("st_rate") or 0)
    if k(f"otr_{rid}") not in st.session_state:
        st.session_state[k(f"otr_{rid}")] = float(opt.get("ot_rate") or 0)
    if k(f"mk_{rid}") not in st.session_state:
        st.session_state[k(f"mk_{rid}")] = float(default_markup)
    if k(f"sth_{rid}") not in st.session_state:
        st.session_state[k(f"sth_{rid}")] = 0.0
    if k(f"oth_{rid}") not in st.session_state:
        st.session_state[k(f"oth_{rid}")] = 0.0
    st.session_state[k(f"last_role_{rid}")] = role


def _sync_labor_batch_row_role(
    k: Callable[[str], str],
    row_id: str,
    role: str,
    lab_map: dict[str, dict[str, Any]],
) -> None:
    last_key = k(f"last_role_{row_id}")
    if st.session_state.get(last_key) == role:
        return
    opt = lab_map.get(role, {})
    st.session_state[k(f"str_{row_id}")] = float(opt.get("st_rate") or 0)
    st.session_state[k(f"otr_{row_id}")] = float(opt.get("ot_rate") or 0)
    st.session_state[last_key] = role


def _labor_rates_differ_from_default(
    role: str,
    st_rate: float,
    ot_rate: float,
    lab_map: dict[str, dict[str, Any]],
) -> bool:
    opt = lab_map.get(role, {})
    return (
        abs(float(st_rate or 0) - float(opt.get("st_rate") or 0)) > 0.009
        or abs(float(ot_rate or 0) - float(opt.get("ot_rate") or 0)) > 0.009
    )


def _labor_line_rate_text(row: dict[str, Any]) -> str:
    st_r = float(row.get("st_rate") or 0)
    ot_r = float(row.get("ot_rate") or 0)
    return f"{fmt_currency(st_r)} / {fmt_currency(ot_r)}"


def _clear_batch_form(*, form_state_key: str, draft_key: str) -> None:
    st.session_state.pop(form_state_key, None)
    st.session_state.pop(draft_key, None)


_DEFAULT_BATCH_ROW_COUNT = 5

_BATCH_ENTRY_CAPTION = (
    f"{_DEFAULT_BATCH_ROW_COUNT} blank rows ready — start typing on any line, then save. "
    "A new blank row appears automatically when you fill the last one."
)

# Pricing items batch entry uses the same default row count as other cost tabs.
_MATERIAL_BATCH_ROW_COUNT = _DEFAULT_BATCH_ROW_COUNT
_MATERIAL_BATCH_CAPTION = (
    f"{_MATERIAL_BATCH_ROW_COUNT} blank rows ready — type in Item to search the catalog, "
    "or choose Custom on each row, then save. A new blank row appears when you fill the last one."
)


def _new_blank_batch_row(**extra: str) -> dict[str, str]:
    return {"rid": uuid4().hex[:8], **extra}


def _initial_batch_draft_rows(count: int = _DEFAULT_BATCH_ROW_COUNT, **extra: str) -> list[dict[str, str]]:
    return [_new_blank_batch_row(**extra) for _ in range(count)]


def _single_batch_fallback_row(**extra: str) -> list[dict[str, str]]:
    return [_new_blank_batch_row(**extra)]


def _ensure_tab_batch_draft(
    draft_key: str,
    init_rows: Callable[[], list[dict[str, str]]],
) -> list[dict[str, str]]:
    rows = list(st.session_state.get(draft_key) or [])
    if len(rows) < _DEFAULT_BATCH_ROW_COUNT:
        st.session_state[draft_key] = init_rows()
        rows = list(st.session_state.get(draft_key) or [])
    return rows


def _maybe_auto_extend_batch_draft(
    draft_key: str,
    draft_rows: list[dict[str, str]],
    *,
    is_row_filled: Callable[[str], bool],
    append_row: Callable[[], dict[str, str]],
) -> None:
    if not draft_rows:
        return
    last_rid = str(draft_rows[-1].get("rid") or "")
    if last_rid and is_row_filled(last_rid):
        extended = list(draft_rows)
        extended.append(append_row())
        st.session_state[draft_key] = extended
        st.rerun()


def _reset_tab_batch_draft(draft_key: str, init_rows: Callable[[], list[dict[str, str]]]) -> None:
    st.session_state[draft_key] = init_rows()


def _open_tab_entry_form(*, form_state_key: str, draft_key: str, init_rows: Callable[[], list[dict[str, str]]]) -> None:
    st.session_state[form_state_key] = True
    _ensure_tab_batch_draft(draft_key, init_rows)


def _batch_draft_key_for_section(section: str, key_prefix: str, eid: str) -> str:
    if section == "lab":
        return _labor_batch_draft_key(key_prefix, eid)
    return _batch_draft_key(section, key_prefix, eid)


def _open_batch_add_form(*, form_state_key: str, draft_key: str) -> None:
    """Open a staged-entry form with a fresh set of default blank rows."""
    st.session_state[form_state_key] = True
    st.session_state.pop(draft_key, None)


_CUSTOM_MATERIAL_LABEL = "— Custom item —"


def _batch_draft_key(section: str, key_prefix: str, eid: str) -> str:
    return f"{key_prefix}_{section}_batch_{eid}"


def _travel_batch_payload(
    travel_type: str,
    *,
    qty: float,
    rate: float,
    multiplier: float,
    markup: float,
    defaults: dict[str, float],
) -> dict[str, Any]:
    tt = str(travel_type or "Mileage").strip()
    mult = float(multiplier or 1.0) or 1.0
    q = float(qty or 0)
    r = float(rate or 0)
    base = {
        "travel_type": tt,
        "markup_percent": float(markup or 0),
        "description": "",
        "origin": "",
        "destination": "",
        "notes": "",
        "taxable": False,
    }
    if tt == "Mileage":
        return {
            **base,
            "miles": q,
            "mileage_rate": r or defaults.get("mileage_rate", 0),
            "trips": mult,
        }
    if tt == "Drive Time":
        return {
            **base,
            "travel_hours": q,
            "hourly_rate": r or defaults.get("hourly_travel_rate", 0),
            "people": mult,
        }
    if tt == "Lodging":
        return {
            **base,
            "nights": q,
            "lodging_rate": r or defaults.get("lodging_rate", 0),
            "people": mult,
        }
    if tt == "Per Diem":
        return {
            **base,
            "per_diem_days": q,
            "per_diem_rate": r or defaults.get("per_diem_rate", 0),
            "people": mult,
        }
    if tt == "Airfare":
        return {**base, "airfare_cost": q, "people": mult}
    if tt == "Rental Vehicle":
        return {**base, "rental_vehicle_cost": q}
    if tt == "Fuel":
        return {**base, "fuel_cost": q}
    if tt == "Parking / Tolls":
        return {**base, "parking_tolls_cost": q}
    return {**base, "other_cost": q}


def _sync_asset_pick_state(
    k: Callable[[str], str],
    pick: str | None,
    asset_map: dict[str, dict[str, Any]],
    dur_unit: str,
) -> dict[str, Any]:
    last_key = k("last_asset")
    if pick and st.session_state.get(last_key) != pick:
        asset = asset_map.get(pick, {})
        st.session_state[k("name")] = str(asset.get("asset_name") or "")
        st.session_state[k("type")] = str(asset.get("category") or "")
        asset_unit = str(asset.get("rental_rate_unit") or "Days")
        if asset_unit in DURATION_UNITS:
            st.session_state[k("dunit")] = asset_unit
            st.session_state[k("last_dunit")] = asset_unit
            dur_unit = asset_unit
        st.session_state[k("rate")] = resolve_equipment_cost_rate(asset, dur_unit)
        asset_mk = float(asset.get("rental_default_markup_percent") or 0)
        if asset_mk > 0:
            st.session_state[k("mk")] = asset_mk
        st.session_state[last_key] = pick
        return asset
    return asset_map.get(pick or "", {})


def _line_table(headers: list[str], rows: list[list[str]]) -> None:
    if not rows:
        st.caption("No line items yet.")
        return
    head = "".join(
        f'<th class="ips-est-li-th">{html.escape(h)}</th>' for h in headers
    )
    body = ""
    for row in rows:
        cells = "".join(f'<td class="ips-est-li-td">{c}</td>' for c in row)
        body += f"<tr>{cells}</tr>"
    st.markdown(
        f'<div class="ips-est-line-table-wrap"><table class="ips-est-line-table">'
        f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>",
        unsafe_allow_html=True,
    )


def _sync_pricing_guide_pick_state(
    k: Callable[[str], str],
    pick: str | None,
    pg_map: dict[str, dict[str, Any]],
    *,
    taxable_key: str = "tax",
) -> dict[str, Any]:
    last_key = k("last_pg_pick")
    if pick and st.session_state.get(last_key) != pick:
        item = pg_map.get(pick, {})
        st.session_state[k("desc")] = str(item.get("description") or "")
        st.session_state[k("sku")] = str(item.get("sku") or item.get("item_key") or "")
        st.session_state[k("cat")] = str(item.get("category") or "")
        st.session_state[k("unit")] = str(item.get("unit") or "EA")
        st.session_state[k("vendor")] = str(item.get("vendor") or item.get("vendor_name") or "")
        st.session_state[k("vendor_id")] = item.get("vendor_id")
        st.session_state[k("uc")] = float(item.get("unit_cost") or 0)
        st.session_state[k("mk")] = float(item.get("markup_pct") or 0)
        st.session_state[k("type")] = str(item.get("item_type") or "Material")
        st.session_state[k("pricing_id")] = item.get("pricing_item_id") or item.get("id")
        st.session_state[taxable_key] = bool(item.get("taxable", True))
        st.session_state[last_key] = pick
        return item
    return pg_map.get(pick or "", {})


def _save_pricing_item_line(eid: str, est: dict[str, Any], item: dict[str, Any], *, qty: float, markup: float, notes: str, k: Callable[[str], str]) -> tuple[bool, str | None]:
    item_type = str(item.get("item_type") or st.session_state.get(k("type")) or "Material")
    description = str(st.session_state.get(k("desc")) or item.get("description") or "")
    unit = str(st.session_state.get(k("unit")) or item.get("unit") or "EA")
    unit_cost = float(st.session_state.get(k("uc")) or item.get("unit_cost") or 0)
    default_labor_markup = float(est.get("default_labor_markup_pct") or 0)
    default_eq_markup = float(est.get("default_equipment_markup_pct") or 0)
    default_sub_markup = float(est.get("default_subcontractor_markup_pct") or 0)
    default_other_markup = float(est.get("default_other_markup_pct") or 0)

    if item_type == "Labor":
        role = str(item.get("labor_role") or description)
        return _service_ok(
            add_estimate_labor(
                eid,
                {
                    "role_name": role,
                    "description": description,
                    "st_hours": qty,
                    "ot_hours": 0.0,
                    "dt_hours": 0.0,
                    "st_rate": unit_cost,
                    "ot_rate": unit_cost * 1.5,
                    "dt_rate": unit_cost * 2.0,
                    "markup_percent": markup if markup else default_labor_markup,
                    "notes": notes,
                },
            )
        )
    if item_type == "Equipment":
        return _service_ok(
            add_estimate_equipment(
                eid,
                {
                    "asset_id": item.get("asset_id"),
                    "equipment_name": description,
                    "equipment_type": str(item.get("equipment_type") or item.get("category") or ""),
                    "quantity": 1.0,
                    "duration": qty if qty else 1.0,
                    "duration_unit": "Hours" if unit.upper() in {"HR", "HRS", "HOUR", "HOURS"} else "Days",
                    "cost_rate": unit_cost,
                    "markup_percent": markup if markup else default_eq_markup,
                    "notes": notes,
                },
            )
        )
    if item_type == "Travel":
        travel_type = str(item.get("travel_type") or description or "Mileage")
        return _service_ok(
            add_estimate_travel(
                eid,
                {
                    "travel_type": travel_type,
                    "description": description,
                    "miles": qty,
                    "mileage_rate": unit_cost,
                    "markup_percent": markup if markup else default_other_markup,
                    "notes": notes,
                },
            )
        )
    if item_type == "Subcontractor":
        return _service_ok(
            add_estimate_subcontractor(
                eid,
                {
                    "vendor_id": item.get("vendor_id") or st.session_state.get(k("vendor_id")),
                    "subcontractor_name": description,
                    "description": description,
                    "cost_total": unit_cost * qty,
                    "markup_percent": markup if markup else default_sub_markup,
                    "notes": notes,
                },
            )
        )
    if item_type in {"Service", "Rental", "Assembly"}:
        return _service_ok(
            add_estimate_other_cost(
                eid,
                {
                    "description": description,
                    "category": str(item.get("category") or item_type),
                    "cost_total": unit_cost * qty,
                    "markup_percent": markup if markup else default_other_markup,
                    "taxable": bool(st.session_state.get(k("tax"), True)),
                    "notes": notes,
                },
            )
        )

    return _service_ok(
        add_estimate_material(
            eid,
            {
                "pricing_item_id": item.get("pricing_item_id") or item.get("id"),
                "inventory_item_id": item.get("inventory_item_id"),
                "sku": st.session_state.get(k("sku")),
                "description": description,
                "category": st.session_state.get(k("cat")) or item.get("category"),
                "unit": unit,
                "unit_cost": unit_cost,
                "quantity": qty,
                "markup_percent": markup,
                "taxable": bool(st.session_state.get(k("tax"), True)),
                "vendor": st.session_state.get(k("vendor")),
                "vendor_id": st.session_state.get(k("vendor_id")),
                "notes": notes,
            },
        )
    )


def render_cost_builder_tab(
    est: dict[str, Any],
    *,
    pricing_guide_options: list[tuple[str, dict[str, Any]]] | None = None,
    inventory_options: list[tuple[str, dict[str, Any]]] | None = None,
    asset_options: list[tuple[str, dict[str, Any]]] | None = None,
    vendor_options: list[str] | None = None,
    on_saved: Callable[[], None] | None = None,
) -> None:
    eid = str(est.get("id") or "")
    if is_demo_id(eid):
        st.info("Save this estimate to Supabase before building costs.")
        return

    totals = _read_cost_builder_totals(eid, est)
    stored_price = float(est.get("customer_price") or est.get("total") or 0)
    calc_price = float(totals.get("customer_price") or 0)
    if calc_price > 0 and abs(stored_price - calc_price) > 0.01:
        ok, _ = _recalc_and_cache_cost_builder_totals(eid, est)
        if ok and on_saved:
            on_saved()
        totals = _read_cost_builder_totals(eid, est)
    render_cost_summary_cards(est, totals)

    st.caption(
        "Staged entry: open a section for 5 blank rows, fill what you need, and save once."
    )

    st.markdown('<div class="ips-estimate-builder-actions">', unsafe_allow_html=True)
    qa1, qa2, qa3, qa4, qa5, qa6 = st.columns(6, gap="small")
    with qa1:
        add_mat = st.button("+ Pricing Item", key=f"ecb_add_mat_{eid}", use_container_width=True)
    with qa2:
        add_lab = st.button("+ Labor", key=f"ecb_add_lab_{eid}", use_container_width=True)
    with qa3:
        add_eq = st.button("+ Equipment", key=f"ecb_add_eq_{eid}", use_container_width=True)
    with qa4:
        add_trv = st.button("+ Travel", key=f"ecb_add_trv_{eid}", use_container_width=True)
    with qa5:
        add_sub = st.button("+ Subcontractor", key=f"ecb_add_sub_{eid}", use_container_width=True)
    with qa6:
        add_other = st.button("+ Other", key=f"ecb_add_other_{eid}", use_container_width=True)
    recalc_col, _ = st.columns([1, 3], gap="small")
    with recalc_col:
        if st.button("Recalculate Totals", key=f"ecb_recalc_{eid}", type="primary", use_container_width=True):
            ok, err = _recalc_and_cache_cost_builder_totals(eid, est)
            if ok:
                st.success("Totals updated.")
                if on_saved:
                    on_saved()
                st.rerun()
            else:
                st.error(err)
    st.markdown("</div>", unsafe_allow_html=True)

    if add_mat:
        _open_batch_add_form(
            form_state_key=f"ecb_form_mat_{eid}",
            draft_key=_batch_draft_key("mat", "ecb_mat", eid),
        )
    if add_lab:
        _open_batch_add_form(
            form_state_key=f"ecb_form_lab_{eid}",
            draft_key=_batch_draft_key_for_section("lab", "ecb_lab", eid),
        )
    if add_eq:
        _open_batch_add_form(
            form_state_key=f"ecb_form_eq_{eid}",
            draft_key=_batch_draft_key("eq", "ecb_eq", eid),
        )
    if add_trv:
        _open_batch_add_form(
            form_state_key=f"ecb_form_trv_{eid}",
            draft_key=_batch_draft_key("trv", "ecb_trv", eid),
        )
    if add_sub:
        _open_batch_add_form(
            form_state_key=f"ecb_form_sub_{eid}",
            draft_key=_batch_draft_key("sub", "ecb_sub", eid),
        )
    if add_other:
        _open_batch_add_form(
            form_state_key=f"ecb_form_other_{eid}",
            draft_key=_batch_draft_key("oth", "ecb_oth", eid),
        )

    if st.session_state.get(f"ecb_form_mat_{eid}"):
        _render_add_material_form(
            eid,
            est,
            pricing_guide_options=pricing_guide_options,
            inventory_options=inventory_options,
            key_prefix="ecb_mat",
            form_state_key=f"ecb_form_mat_{eid}",
        )
    if st.session_state.get(f"ecb_form_lab_{eid}"):
        _render_add_labor_form(eid, est, key_prefix="ecb_lab", form_state_key=f"ecb_form_lab_{eid}")
    if st.session_state.get(f"ecb_form_eq_{eid}"):
        _render_add_equipment_form(
            eid,
            est,
            asset_options or [],
            key_prefix="ecb_eq",
            form_state_key=f"ecb_form_eq_{eid}",
        )
    if st.session_state.get(f"ecb_form_trv_{eid}"):
        _render_add_travel_form(eid, est, key_prefix="ecb_trv", form_state_key=f"ecb_form_trv_{eid}")
    if st.session_state.get(f"ecb_form_sub_{eid}"):
        _render_add_subcontractor_form(
            eid,
            est,
            vendor_options or [],
            key_prefix="ecb_sub",
            form_state_key=f"ecb_form_sub_{eid}",
        )
    if st.session_state.get(f"ecb_form_other_{eid}"):
        _render_add_other_form(eid, est, key_prefix="ecb_oth", form_state_key=f"ecb_form_other_{eid}")

    _render_cost_builder_line_sections(est)


def _sync_material_batch_pick(
    k: Callable[[str], str],
    row_id: str,
    pick: str,
    pg_map: dict[str, dict[str, Any]],
    *,
    default_markup: float,
) -> None:
    last_key = k(f"last_pg_{row_id}")
    if st.session_state.get(last_key) == pick:
        return
    if pick and pick != _CUSTOM_MATERIAL_LABEL:
        item = pg_map.get(pick, {})
        st.session_state[k(f"desc_{row_id}")] = str(item.get("description") or item.get("name") or pick)
        st.session_state[k(f"uc_{row_id}")] = float(item.get("unit_cost") or 0)
        st.session_state[k(f"unit_{row_id}")] = str(item.get("unit") or "EA")
        st.session_state[k(f"mk_{row_id}")] = float(item.get("markup_pct") or default_markup)
        st.session_state[k(f"tax_{row_id}")] = bool(item.get("taxable", True))
    elif pick == _CUSTOM_MATERIAL_LABEL:
        st.session_state[k(f"desc_{row_id}")] = ""
        st.session_state[k(f"uc_{row_id}")] = 0.0
        st.session_state[k(f"unit_{row_id}")] = "EA"
        st.session_state[k(f"mk_{row_id}")] = float(default_markup)
        st.session_state[k(f"tax_{row_id}")] = True
    st.session_state[last_key] = pick


def _render_add_material_form(
    eid: str,
    est: dict[str, Any],
    *,
    pricing_guide_options: list[tuple[str, dict[str, Any]]] | None = None,
    inventory_options: list[tuple[str, dict[str, Any]]] | None = None,
    key_prefix: str = "ecb_mat",
    form_state_key: str | None = None,
    tab_entry: bool = False,
) -> None:
    _ = inventory_options
    fk = form_state_key or f"ecb_form_mat_{eid}"
    k = lambda field: _line_form_key(key_prefix, eid, field)  # noqa: E731
    default_markup = float(est.get("default_material_markup_pct") or 0)
    pg_opts = pricing_guide_options or []
    pg_map = {label: item for label, item in pg_opts}
    pg_labels = [label for label, _ in pg_opts]
    pick_labels = [*pg_labels, _CUSTOM_MATERIAL_LABEL] if pg_labels else [_CUSTOM_MATERIAL_LABEL]
    draft_key = _batch_draft_key("mat", key_prefix, eid)

    def _init_rows() -> list[dict[str, str]]:
        return _initial_batch_draft_rows(_DEFAULT_BATCH_ROW_COUNT, pick=_CUSTOM_MATERIAL_LABEL)

    if tab_entry:
        _ensure_tab_batch_draft(draft_key, _init_rows)
    elif draft_key not in st.session_state:
        st.session_state[draft_key] = _init_rows()

    if tab_entry:
        st.caption(_MATERIAL_BATCH_CAPTION)
    else:
        _compact_form_card("Add Pricing Items")
        st.caption(_MATERIAL_BATCH_CAPTION)
    if not pg_labels:
        st.info("No pricing guide items yet — use custom rows or add items under Pricing Guide.")

    hdr = st.columns([2.6, 0.75, 0.95, 0.75, 0.9, 0.9, 0.55], gap="small")
    for col, label in zip(hdr, ("Item", "Qty", "Unit Cost", "Markup %", "Cost", "Price", "")):
        with col:
            st.markdown(
                f'<div style="font-size:0.72rem;font-weight:700;color:#64748b;">{html.escape(label)}</div>',
                unsafe_allow_html=True,
            )

    draft_rows: list[dict[str, str]] = list(st.session_state.get(draft_key) or [])
    remove_rid = ""
    for row in draft_rows:
        rid = str(row.get("rid") or "")
        if not rid:
            continue
        if k(f"pick_{rid}") not in st.session_state:
            st.session_state[k(f"pick_{rid}")] = row.get("pick") or _CUSTOM_MATERIAL_LABEL
        if k(f"qty_{rid}") not in st.session_state:
            st.session_state[k(f"qty_{rid}")] = 1.0
        if k(f"uc_{rid}") not in st.session_state:
            st.session_state[k(f"uc_{rid}")] = 0.0
        if k(f"mk_{rid}") not in st.session_state:
            st.session_state[k(f"mk_{rid}")] = default_markup
        cols = st.columns([2.6, 0.75, 0.95, 0.75, 0.9, 0.9, 0.55], gap="small")
        with cols[0]:
            pick = render_searchable_selectbox(
                "Item",
                pick_labels,
                key=k(f"pick_{rid}"),
                placeholder="Type to search items…",
                searchable_options=pg_opts,
            )
            _sync_material_batch_pick(k, rid, pick, pg_map, default_markup=default_markup)
            if pick == _CUSTOM_MATERIAL_LABEL:
                st.text_input(
                    "Description",
                    key=k(f"desc_{rid}"),
                    label_visibility="collapsed",
                    placeholder="Custom description",
                )
        with cols[1]:
            qty = st.number_input(
                "Qty",
                min_value=0.0,
                step=1.0,
                key=k(f"qty_{rid}"),
                label_visibility="collapsed",
            )
        with cols[2]:
            unit_cost = st.number_input(
                "Unit cost",
                min_value=0.0,
                step=1.0,
                format="%.2f",
                key=k(f"uc_{rid}"),
                label_visibility="collapsed",
            )
        with cols[3]:
            markup = st.number_input(
                "Markup %",
                min_value=0.0,
                step=0.5,
                key=k(f"mk_{rid}"),
                label_visibility="collapsed",
            )
        totals = material_line_totals(qty, unit_cost, markup)
        with cols[4]:
            st.markdown(
                f'<div style="padding-top:0.45rem;font-weight:700;font-size:0.82rem;">'
                f"{html.escape(fmt_currency(totals['cost_total']))}</div>",
                unsafe_allow_html=True,
            )
        with cols[5]:
            st.markdown(
                f'<div style="padding-top:0.45rem;font-weight:700;font-size:0.82rem;">'
                f"{html.escape(fmt_currency(totals['price_total']))}</div>",
                unsafe_allow_html=True,
            )
        with cols[6]:
            if st.button("✕", key=k(f"rm_{rid}"), help="Remove row"):
                remove_rid = rid

    if tab_entry:
        _maybe_auto_extend_batch_draft(
            draft_key,
            draft_rows,
            is_row_filled=lambda row_id: float(st.session_state.get(k(f"qty_{row_id}")) or 0) > 0
            and bool(
                str(st.session_state.get(k(f"desc_{row_id}")) or "").strip()
                or (
                    str(st.session_state.get(k(f"pick_{row_id}")) or "") not in {"", _CUSTOM_MATERIAL_LABEL}
                )
            ),
            append_row=lambda: _new_blank_batch_row(pick=_CUSTOM_MATERIAL_LABEL),
        )

    if remove_rid:
        remaining = [r for r in draft_rows if str(r.get("rid")) != remove_rid]
        st.session_state[draft_key] = remaining or _init_rows()
        st.rerun()

    if not tab_entry:
        add_col, _ = st.columns([1, 3], gap="small")
        with add_col:
            if st.button("+ Add Row", key=k("add_row"), use_container_width=True):
                draft_rows.append({"rid": uuid4().hex[:8], "pick": _CUSTOM_MATERIAL_LABEL})
                st.session_state[draft_key] = draft_rows
                st.rerun()

    save_col, cancel_col, _ = st.columns([1, 1, 2], gap="small")
    with save_col:
        save_clicked = st.button("Save Pricing Items", key=k("save"), type="primary", use_container_width=True)
    if not tab_entry:
        with cancel_col:
            cancel_clicked = st.button("Cancel", key=k("cancel"), use_container_width=True)
    else:
        cancel_clicked = False

    if cancel_clicked:
        _clear_batch_form(form_state_key=fk, draft_key=draft_key)
        st.rerun()

    if save_clicked:
        payloads: list[dict[str, Any]] = []
        for row in draft_rows:
            rid = str(row.get("rid") or "")
            if not rid:
                continue
            pick = str(st.session_state.get(k(f"pick_{rid}")) or "")
            qty = float(st.session_state.get(k(f"qty_{rid}")) or 0)
            if qty <= 0:
                continue
            item = pg_map.get(pick, {}) if pick and pick != _CUSTOM_MATERIAL_LABEL else {}
            description = str(
                item.get("description")
                or st.session_state.get(k(f"desc_{rid}"))
                or pick
                or ""
            ).strip()
            if not description:
                continue
            payloads.append(
                {
                    "pricing_item_id": item.get("pricing_item_id") or item.get("id"),
                    "inventory_item_id": item.get("inventory_item_id"),
                    "sku": item.get("sku"),
                    "description": description,
                    "category": item.get("category"),
                    "unit": str(item.get("unit") or st.session_state.get(k(f"unit_{rid}")) or "EA"),
                    "unit_cost": float(st.session_state.get(k(f"uc_{rid}")) or item.get("unit_cost") or 0),
                    "quantity": qty,
                    "markup_percent": float(st.session_state.get(k(f"mk_{rid}")) or default_markup),
                    "taxable": bool(st.session_state.get(k(f"tax_{rid}"), item.get("taxable", True))),
                }
            )
        if not payloads:
            st.error("Enter at least one line with quantity and description.")
        else:
            ok, err = _service_ok(add_estimate_material_batch(eid, payloads))
            if ok:
                if tab_entry:
                    _reset_tab_batch_draft(draft_key, _init_rows)
                else:
                    _clear_batch_form(form_state_key=fk, draft_key=draft_key)
                count = len(payloads)
                st.success(f"Saved {count} pricing item{'s' if count != 1 else ''}.")
                st.rerun()
            st.error(err)

    if not tab_entry:
        _close_compact_form_card()


def _render_add_labor_form(
    eid: str,
    est: dict[str, Any],
    *,
    key_prefix: str = "ecb_lab",
    form_state_key: str | None = None,
    tab_entry: bool = False,
) -> None:
    fk = form_state_key or f"ecb_form_lab_{eid}"
    k = lambda field: _line_form_key(key_prefix, eid, field)  # noqa: E731
    default_markup = float(est.get("default_labor_markup_pct") or 0)
    labor_options = labor_options_as_select()
    lab_map = {label: opt for label, opt in labor_options}
    role_labels = [label for label, _ in labor_options] or list(LABOR_ROLE_TYPES)
    draft_key = _labor_batch_draft_key(key_prefix, eid)

    def _init_rows() -> list[dict[str, str]]:
        return [
            _new_labor_batch_row(
                role_labels=role_labels,
                lab_map=lab_map,
                default_markup=default_markup,
            )
            for _ in range(_DEFAULT_BATCH_ROW_COUNT)
        ]

    if tab_entry:
        _ensure_tab_batch_draft(draft_key, _init_rows)
    elif draft_key not in st.session_state:
        st.session_state[draft_key] = _init_rows()

    if tab_entry:
        st.caption(
            f"{_BATCH_ENTRY_CAPTION} Rates pre-fill from Pricing Guide → Labor Rates; "
            "change ST/OT on a row to override for this estimate only."
        )
    else:
        _compact_form_card("Add Labor")
        st.caption(
            f"{_BATCH_ENTRY_CAPTION} Rates pre-fill from Pricing Guide → Labor Rates; "
            "change ST/OT on a row to override for this estimate only."
        )

    hdr = st.columns([2.2, 0.75, 0.75, 0.85, 0.85, 0.7, 0.85, 0.85, 0.45], gap="small")
    for col, label in zip(
        hdr,
        ("Role", "ST Hrs", "OT Hrs", "ST Rate", "OT Rate", "Markup %", "Cost", "Price", ""),
    ):
        with col:
            st.markdown(
                f'<div style="font-size:0.72rem;font-weight:700;color:#64748b;">{html.escape(label)}</div>',
                unsafe_allow_html=True,
            )

    draft_rows: list[dict[str, str]] = list(st.session_state.get(draft_key) or [])
    remove_rid = ""
    for row in draft_rows:
        rid = str(row.get("rid") or "")
        if not rid:
            continue
        _seed_labor_batch_row_widgets(
            k,
            row,
            lab_map=lab_map,
            default_markup=default_markup,
        )
        cols = st.columns([2.2, 0.75, 0.75, 0.85, 0.85, 0.7, 0.85, 0.85, 0.45], gap="small")
        with cols[0]:
            role = st.selectbox(
                "Role",
                role_labels,
                key=k(f"role_{rid}"),
                label_visibility="collapsed",
            )
            _sync_labor_batch_row_role(k, rid, role, lab_map)
        with cols[1]:
            st_h = st.number_input(
                "ST hours",
                min_value=0.0,
                step=0.5,
                key=k(f"sth_{rid}"),
                label_visibility="collapsed",
            )
        with cols[2]:
            ot_h = st.number_input(
                "OT hours",
                min_value=0.0,
                step=0.5,
                key=k(f"oth_{rid}"),
                label_visibility="collapsed",
            )
        with cols[3]:
            st_r = st.number_input(
                "ST rate",
                min_value=0.0,
                step=1.0,
                format="%.2f",
                key=k(f"str_{rid}"),
                label_visibility="collapsed",
            )
        with cols[4]:
            ot_r = st.number_input(
                "OT rate",
                min_value=0.0,
                step=1.0,
                format="%.2f",
                key=k(f"otr_{rid}"),
                label_visibility="collapsed",
            )
        with cols[5]:
            markup = st.number_input(
                "Markup %",
                min_value=0.0,
                step=0.5,
                key=k(f"mk_{rid}"),
                label_visibility="collapsed",
            )
        totals = labor_line_totals(st_h, ot_h, st_r, ot_r, markup)
        with cols[6]:
            st.markdown(
                f'<div style="padding-top:0.45rem;font-weight:700;font-size:0.82rem;">'
                f"{html.escape(fmt_currency(totals['cost_total']))}</div>",
                unsafe_allow_html=True,
            )
        with cols[7]:
            st.markdown(
                f'<div style="padding-top:0.45rem;font-weight:700;font-size:0.82rem;">'
                f"{html.escape(fmt_currency(totals['price_total']))}</div>",
                unsafe_allow_html=True,
            )
        with cols[8]:
            if st.button("✕", key=k(f"rm_{rid}"), help="Remove row"):
                remove_rid = rid

    if tab_entry:
        _maybe_auto_extend_batch_draft(
            draft_key,
            draft_rows,
            is_row_filled=lambda row_id: float(st.session_state.get(k(f"sth_{row_id}")) or 0) > 0
            or float(st.session_state.get(k(f"oth_{row_id}")) or 0) > 0,
            append_row=lambda: _new_labor_batch_row(
                role_labels=role_labels,
                lab_map=lab_map,
                default_markup=default_markup,
            ),
        )

    if remove_rid:
        remaining = [r for r in draft_rows if str(r.get("rid")) != remove_rid]
        st.session_state[draft_key] = remaining or _init_rows()
        st.rerun()

    if not tab_entry:
        add_col, _ = st.columns([1, 3], gap="small")
        with add_col:
            if st.button("+ Add Row", key=k("add_row"), use_container_width=True):
                draft_rows.append(
                    _new_labor_batch_row(
                        role_labels=role_labels,
                        lab_map=lab_map,
                        default_markup=default_markup,
                    )
                )
                st.session_state[draft_key] = draft_rows
                st.rerun()

    save_as_default = False
    if current_role() == "admin":
        save_as_default = st.checkbox(
            "Save modified rates as defaults for future estimates",
            value=False,
            key=k("save_defaults"),
            help="Updates Pricing Guide labor rates. Does not change labor lines already saved on other estimates.",
        )
    save_col, cancel_col, _ = st.columns([1, 1, 2], gap="small")
    with save_col:
        save_clicked = st.button(
            "Save Labor Lines",
            key=k("save"),
            type="primary",
            use_container_width=True,
        )
    if not tab_entry:
        with cancel_col:
            cancel_clicked = st.button("Cancel", key=k("cancel"), use_container_width=True)
    else:
        cancel_clicked = False

    if cancel_clicked:
        _clear_batch_form(form_state_key=fk, draft_key=draft_key)
        st.rerun()

    if save_clicked:
        payloads: list[dict[str, Any]] = []
        for row in draft_rows:
            rid = str(row.get("rid") or "")
            if not rid:
                continue
            role = str(st.session_state.get(k(f"role_{rid}")) or row.get("role") or "")
            st_h = float(st.session_state.get(k(f"sth_{rid}")) or 0)
            ot_h = float(st.session_state.get(k(f"oth_{rid}")) or 0)
            if st_h <= 0 and ot_h <= 0:
                continue
            payloads.append(
                {
                    "labor_type": role,
                    "role_name": role,
                    "description": role,
                    "st_hours": st_h,
                    "ot_hours": ot_h,
                    "st_rate": float(st.session_state.get(k(f"str_{rid}")) or 0),
                    "ot_rate": float(st.session_state.get(k(f"otr_{rid}")) or 0),
                    "markup_percent": float(st.session_state.get(k(f"mk_{rid}")) or default_markup),
                }
            )
        if not payloads:
            st.error("Enter at least one labor line with ST or OT hours.")
        else:
            ok, err = _service_ok(add_estimate_labor_batch(eid, payloads))
            if ok:
                default_lines: list[dict[str, Any]] = []
                if save_as_default:
                    for row in payloads:
                        role = str(row.get("role_name") or "")
                        st_r = float(row.get("st_rate") or 0)
                        ot_r = float(row.get("ot_rate") or 0)
                        if _labor_rates_differ_from_default(role, st_r, ot_r, lab_map):
                            default_lines.append(row)
                    if default_lines:
                        def_ok, def_err = _service_ok(save_default_rates_from_lines(default_lines))
                        if not def_ok:
                            st.warning(f"Labor lines saved, but defaults were not updated: {def_err}")
                count = len(payloads)
                msg = f"Saved {count} labor line{'s' if count != 1 else ''}."
                if save_as_default and default_lines:
                    msg += f" Updated {len(default_lines)} default rate(s)."
                if tab_entry:
                    _reset_tab_batch_draft(draft_key, _init_rows)
                else:
                    _clear_batch_form(form_state_key=fk, draft_key=draft_key)
                st.success(msg)
                st.rerun()
            st.error(err)

    if not tab_entry:
        _close_compact_form_card()


def _sync_equipment_batch_asset(
    k: Callable[[str], str],
    row_id: str,
    pick: str,
    asset_map: dict[str, dict[str, Any]],
    dur_unit: str,
) -> dict[str, Any]:
    last_key = k(f"last_asset_{row_id}")
    asset = asset_map.get(pick, {})
    if st.session_state.get(last_key) != pick:
        st.session_state[k(f"name_{row_id}")] = str(asset.get("asset_name") or "")
        st.session_state[k(f"type_{row_id}")] = str(asset.get("category") or "")
        asset_unit = str(asset.get("rental_rate_unit") or dur_unit or "Days")
        if asset_unit in DURATION_UNITS:
            st.session_state[k(f"dunit_{row_id}")] = asset_unit
        st.session_state[k(f"rate_{row_id}")] = resolve_equipment_cost_rate(
            asset, str(st.session_state.get(k(f"dunit_{row_id}")) or dur_unit)
        )
        st.session_state[last_key] = pick
    return asset


def _render_add_equipment_form(
    eid: str,
    est: dict[str, Any],
    asset_options: list[tuple[str, dict[str, Any]]],
    *,
    key_prefix: str = "ecb_eq",
    form_state_key: str | None = None,
    tab_entry: bool = False,
) -> None:
    fk = form_state_key or f"ecb_form_eq_{eid}"
    k = lambda field: _line_form_key(key_prefix, eid, field)  # noqa: E731
    default_markup = float(est.get("default_equipment_markup_pct") or 0)
    asset_map = {label: asset for label, asset in asset_options}
    labels = [label for label, _ in asset_options]
    draft_key = _batch_draft_key("eq", key_prefix, eid)

    def _init_rows() -> list[dict[str, str]]:
        return _initial_batch_draft_rows(_DEFAULT_BATCH_ROW_COUNT, pick=labels[0] if labels else "")

    if tab_entry:
        _ensure_tab_batch_draft(draft_key, _init_rows)
    elif draft_key not in st.session_state:
        st.session_state[draft_key] = _init_rows()

    if tab_entry:
        st.caption(_BATCH_ENTRY_CAPTION)
    else:
        _compact_form_card("Add Equipment")
        st.caption(_BATCH_ENTRY_CAPTION)
    if not asset_options:
        st.info("No rentable assets available. Mark assets as Rentable on the Assets page.")

    hdr = st.columns([2.2, 0.75, 0.75, 0.6, 0.85, 0.7, 0.85, 0.85, 0.55], gap="small")
    for col, label in zip(
        hdr,
        ("Equipment", "Unit", "Duration", "Qty", "Rate", "Markup %", "Cost", "Price", ""),
    ):
        with col:
            st.markdown(
                f'<div style="font-size:0.72rem;font-weight:700;color:#64748b;">{html.escape(label)}</div>',
                unsafe_allow_html=True,
            )

    draft_rows: list[dict[str, str]] = list(st.session_state.get(draft_key) or [])
    remove_rid = ""
    for row in draft_rows:
        rid = str(row.get("rid") or "")
        if not rid:
            continue
        if k(f"dunit_{rid}") not in st.session_state:
            st.session_state[k(f"dunit_{rid}")] = "Days"
        if k(f"dur_{rid}") not in st.session_state:
            st.session_state[k(f"dur_{rid}")] = 1.0
        if k(f"qty_{rid}") not in st.session_state:
            st.session_state[k(f"qty_{rid}")] = 1.0
        if k(f"mk_{rid}") not in st.session_state:
            st.session_state[k(f"mk_{rid}")] = default_markup
        cols = st.columns([2.2, 0.75, 0.75, 0.6, 0.85, 0.7, 0.85, 0.85, 0.55], gap="small")
        pick = ""
        asset: dict[str, Any] = {}
        with cols[0]:
            if labels:
                pick = st.selectbox(
                    "Equipment",
                    labels,
                    key=k(f"asset_{rid}"),
                    label_visibility="collapsed",
                )
                dur_unit = str(st.session_state.get(k(f"dunit_{rid}")) or "Days")
                asset = _sync_equipment_batch_asset(k, rid, pick, asset_map, dur_unit)
            else:
                st.text_input(
                    "Equipment name",
                    key=k(f"name_{rid}"),
                    label_visibility="collapsed",
                    placeholder="Equipment name",
                )
        with cols[1]:
            dur_unit = st.selectbox(
                "Duration unit",
                DURATION_UNITS,
                key=k(f"dunit_{rid}"),
                label_visibility="collapsed",
            )
            if pick:
                dur_last = k(f"last_dunit_{rid}")
                if st.session_state.get(dur_last) != dur_unit:
                    asset = asset_map.get(pick, asset)
                    st.session_state[k(f"rate_{rid}")] = resolve_equipment_cost_rate(asset, dur_unit)
                    st.session_state[dur_last] = dur_unit
        with cols[2]:
            duration = st.number_input(
                "Duration",
                min_value=0.0,
                step=0.5,
                key=k(f"dur_{rid}"),
                label_visibility="collapsed",
            )
        with cols[3]:
            qty = st.number_input(
                "Qty",
                min_value=0.0,
                step=1.0,
                key=k(f"qty_{rid}"),
                label_visibility="collapsed",
            )
        with cols[4]:
            cost_rate = st.number_input(
                "Rate",
                min_value=0.0,
                step=1.0,
                format="%.2f",
                key=k(f"rate_{rid}"),
                label_visibility="collapsed",
            )
        with cols[5]:
            markup = st.number_input(
                "Markup %",
                min_value=0.0,
                step=0.5,
                key=k(f"mk_{rid}"),
                label_visibility="collapsed",
            )
        totals = equipment_line_totals(qty, duration, cost_rate, markup)
        with cols[6]:
            st.markdown(
                f'<div style="padding-top:0.45rem;font-weight:700;font-size:0.82rem;">'
                f"{html.escape(fmt_currency(totals['cost_total']))}</div>",
                unsafe_allow_html=True,
            )
        with cols[7]:
            st.markdown(
                f'<div style="padding-top:0.45rem;font-weight:700;font-size:0.82rem;">'
                f"{html.escape(fmt_currency(totals['price_total']))}</div>",
                unsafe_allow_html=True,
            )
        with cols[8]:
            if st.button("✕", key=k(f"rm_{rid}"), help="Remove row"):
                remove_rid = rid

    if tab_entry:
        _maybe_auto_extend_batch_draft(
            draft_key,
            draft_rows,
            is_row_filled=lambda row_id: float(st.session_state.get(k(f"dur_{row_id}")) or 0) > 0
            and float(st.session_state.get(k(f"rate_{row_id}")) or 0) > 0,
            append_row=lambda: _new_blank_batch_row(pick=labels[0] if labels else ""),
        )

    if remove_rid:
        remaining = [r for r in draft_rows if str(r.get("rid")) != remove_rid]
        st.session_state[draft_key] = remaining or _init_rows()
        st.rerun()

    if not tab_entry:
        add_col, _ = st.columns([1, 3], gap="small")
        with add_col:
            if st.button("+ Add Row", key=k("add_row"), use_container_width=True):
                draft_rows.append({"rid": uuid4().hex[:8], "pick": labels[0] if labels else ""})
                st.session_state[draft_key] = draft_rows
                st.rerun()

    save_col, cancel_col, _ = st.columns([1, 1, 2], gap="small")
    with save_col:
        save_clicked = st.button("Save Equipment Lines", key=k("save"), type="primary", use_container_width=True)
    if not tab_entry:
        with cancel_col:
            cancel_clicked = st.button("Cancel", key=k("cancel"), use_container_width=True)
    else:
        cancel_clicked = False

    if cancel_clicked:
        _clear_batch_form(form_state_key=fk, draft_key=draft_key)
        st.rerun()

    if save_clicked:
        payloads: list[dict[str, Any]] = []
        for row in draft_rows:
            rid = str(row.get("rid") or "")
            if not rid:
                continue
            duration = float(st.session_state.get(k(f"dur_{rid}")) or 0)
            qty = float(st.session_state.get(k(f"qty_{rid}")) or 0)
            cost_rate = float(st.session_state.get(k(f"rate_{rid}")) or 0)
            if duration <= 0 or cost_rate <= 0:
                continue
            pick = str(st.session_state.get(k(f"asset_{rid}")) or "") if labels else ""
            asset = asset_map.get(pick, {}) if pick else {}
            payloads.append(
                {
                    "asset_id": str(asset.get("id") or "") or None,
                    "equipment_name": str(st.session_state.get(k(f"name_{rid}")) or asset.get("asset_name") or pick),
                    "equipment_type": str(st.session_state.get(k(f"type_{rid}")) or asset.get("category") or ""),
                    "quantity": qty or 1.0,
                    "duration": duration,
                    "duration_unit": str(st.session_state.get(k(f"dunit_{rid}")) or "Days"),
                    "cost_rate": cost_rate,
                    "markup_percent": float(st.session_state.get(k(f"mk_{rid}")) or default_markup),
                }
            )
        if not payloads:
            st.error("Enter at least one equipment line with duration and rate.")
        else:
            ok, err = _service_ok(add_estimate_equipment_batch(eid, payloads))
            if ok:
                if tab_entry:
                    _reset_tab_batch_draft(draft_key, _init_rows)
                else:
                    _clear_batch_form(form_state_key=fk, draft_key=draft_key)
                count = len(payloads)
                st.success(f"Saved {count} equipment line{'s' if count != 1 else ''}.")
                st.rerun()
            st.error(err)

    if not tab_entry:
        _close_compact_form_card()


def _render_add_subcontractor_form(
    eid: str,
    est: dict[str, Any],
    vendor_options: list[str],
    *,
    key_prefix: str = "ecb_sub",
    form_state_key: str | None = None,
    tab_entry: bool = False,
) -> None:
    fk = form_state_key or f"ecb_form_sub_{eid}"
    k = lambda field: _line_form_key(key_prefix, eid, field)  # noqa: E731
    default_markup = float(est.get("default_subcontractor_markup_pct") or 0)
    draft_key = _batch_draft_key("sub", key_prefix, eid)

    def _init_rows() -> list[dict[str, str]]:
        return _initial_batch_draft_rows(_DEFAULT_BATCH_ROW_COUNT)

    if tab_entry:
        _ensure_tab_batch_draft(draft_key, _init_rows)
    elif draft_key not in st.session_state:
        st.session_state[draft_key] = _init_rows()

    if tab_entry:
        st.caption(_BATCH_ENTRY_CAPTION)
    else:
        _compact_form_card("Add Subcontractors")
        st.caption(_BATCH_ENTRY_CAPTION)

    hdr = st.columns([2.0, 2.2, 0.95, 0.75, 0.9, 0.9, 0.55], gap="small")
    for col, label in zip(hdr, ("Subcontractor", "Scope", "Cost", "Markup %", "Cost", "Price", "")):
        with col:
            st.markdown(
                f'<div style="font-size:0.72rem;font-weight:700;color:#64748b;">{html.escape(label)}</div>',
                unsafe_allow_html=True,
            )

    draft_rows: list[dict[str, str]] = list(st.session_state.get(draft_key) or [])
    remove_rid = ""
    for row in draft_rows:
        rid = str(row.get("rid") or "")
        if not rid:
            continue
        if k(f"mk_{rid}") not in st.session_state:
            st.session_state[k(f"mk_{rid}")] = default_markup
        if k(f"cost_{rid}") not in st.session_state:
            st.session_state[k(f"cost_{rid}")] = 0.0
        cols = st.columns([2.0, 2.2, 0.95, 0.75, 0.9, 0.9, 0.55], gap="small")
        with cols[0]:
            if vendor_options:
                st.selectbox(
                    "Subcontractor",
                    vendor_options,
                    key=k(f"vendor_{rid}"),
                    label_visibility="collapsed",
                )
            else:
                st.text_input(
                    "Subcontractor",
                    key=k(f"vendor_{rid}"),
                    label_visibility="collapsed",
                    placeholder="Subcontractor name",
                )
        with cols[1]:
            st.text_input(
                "Scope",
                key=k(f"desc_{rid}"),
                label_visibility="collapsed",
                placeholder="Scope / description",
            )
        with cols[2]:
            cost = st.number_input(
                "Cost",
                min_value=0.0,
                step=1.0,
                format="%.2f",
                key=k(f"cost_{rid}"),
                label_visibility="collapsed",
            )
        with cols[3]:
            markup = st.number_input(
                "Markup %",
                min_value=0.0,
                step=0.5,
                key=k(f"mk_{rid}"),
                label_visibility="collapsed",
            )
        totals = simple_line_totals(cost, markup)
        with cols[4]:
            st.markdown(
                f'<div style="padding-top:0.45rem;font-weight:700;font-size:0.82rem;">'
                f"{html.escape(fmt_currency(totals['cost_total']))}</div>",
                unsafe_allow_html=True,
            )
        with cols[5]:
            st.markdown(
                f'<div style="padding-top:0.45rem;font-weight:700;font-size:0.82rem;">'
                f"{html.escape(fmt_currency(totals['price_total']))}</div>",
                unsafe_allow_html=True,
            )
        with cols[6]:
            if st.button("✕", key=k(f"rm_{rid}"), help="Remove row"):
                remove_rid = rid

    if tab_entry:
        _maybe_auto_extend_batch_draft(
            draft_key,
            draft_rows,
            is_row_filled=lambda row_id: float(st.session_state.get(k(f"cost_{row_id}")) or 0) > 0
            and bool(str(st.session_state.get(k(f"vendor_{row_id}")) or "").strip()),
            append_row=_new_blank_batch_row,
        )

    if remove_rid:
        remaining = [r for r in draft_rows if str(r.get("rid")) != remove_rid]
        st.session_state[draft_key] = remaining or _init_rows()
        st.rerun()

    if not tab_entry:
        add_col, _ = st.columns([1, 3], gap="small")
        with add_col:
            if st.button("+ Add Row", key=k("add_row"), use_container_width=True):
                draft_rows.append(_new_blank_batch_row())
                st.session_state[draft_key] = draft_rows
                st.rerun()

    save_col, cancel_col, _ = st.columns([1, 1, 2], gap="small")
    with save_col:
        save_clicked = st.button(
            "Save Subcontractors",
            key=k("save"),
            type="primary",
            use_container_width=True,
        )
    if not tab_entry:
        with cancel_col:
            cancel_clicked = st.button("Cancel", key=k("cancel"), use_container_width=True)
    else:
        cancel_clicked = False

    if cancel_clicked:
        _clear_batch_form(form_state_key=fk, draft_key=draft_key)
        st.rerun()

    if save_clicked:
        payloads: list[dict[str, Any]] = []
        for row in draft_rows:
            rid = str(row.get("rid") or "")
            if not rid:
                continue
            cost = float(st.session_state.get(k(f"cost_{rid}")) or 0)
            if cost <= 0:
                continue
            vendor = str(st.session_state.get(k(f"vendor_{rid}")) or "").strip()
            if not vendor:
                continue
            payloads.append(
                {
                    "subcontractor_name": vendor,
                    "description": str(st.session_state.get(k(f"desc_{rid}")) or ""),
                    "cost_total": cost,
                    "markup_percent": float(st.session_state.get(k(f"mk_{rid}")) or default_markup),
                }
            )
        if not payloads:
            st.error("Enter at least one subcontractor line with a name and cost.")
        else:
            ok, err = _service_ok(add_estimate_subcontractor_batch(eid, payloads))
            if ok:
                if tab_entry:
                    _reset_tab_batch_draft(draft_key, _init_rows)
                else:
                    _clear_batch_form(form_state_key=fk, draft_key=draft_key)
                count = len(payloads)
                st.success(f"Saved {count} subcontractor line{'s' if count != 1 else ''}.")
                st.rerun()
            st.error(err)

    if not tab_entry:
        _close_compact_form_card()


def _render_add_other_form(
    eid: str,
    est: dict[str, Any],
    *,
    key_prefix: str = "ecb_oth",
    form_state_key: str | None = None,
    tab_entry: bool = False,
) -> None:
    fk = form_state_key or f"ecb_form_other_{eid}"
    k = lambda field: _line_form_key(key_prefix, eid, field)  # noqa: E731
    default_markup = float(est.get("default_other_markup_pct") or 0)
    draft_key = _batch_draft_key("oth", key_prefix, eid)

    def _init_rows() -> list[dict[str, str]]:
        return _initial_batch_draft_rows(_DEFAULT_BATCH_ROW_COUNT)

    if tab_entry:
        _ensure_tab_batch_draft(draft_key, _init_rows)
    elif draft_key not in st.session_state:
        st.session_state[draft_key] = _init_rows()

    if tab_entry:
        st.caption(_BATCH_ENTRY_CAPTION)
    else:
        _compact_form_card("Add Other Costs")
        st.caption(_BATCH_ENTRY_CAPTION)

    hdr = st.columns([2.4, 0.95, 0.75, 0.65, 0.9, 0.9, 0.55], gap="small")
    for col, label in zip(hdr, ("Description", "Cost", "Markup %", "Tax", "Cost", "Price", "")):
        with col:
            st.markdown(
                f'<div style="font-size:0.72rem;font-weight:700;color:#64748b;">{html.escape(label)}</div>',
                unsafe_allow_html=True,
            )

    draft_rows: list[dict[str, str]] = list(st.session_state.get(draft_key) or [])
    remove_rid = ""
    for row in draft_rows:
        rid = str(row.get("rid") or "")
        if not rid:
            continue
        if k(f"mk_{rid}") not in st.session_state:
            st.session_state[k(f"mk_{rid}")] = default_markup
        if k(f"cost_{rid}") not in st.session_state:
            st.session_state[k(f"cost_{rid}")] = 0.0
        if k(f"tax_{rid}") not in st.session_state:
            st.session_state[k(f"tax_{rid}")] = False
        cols = st.columns([2.4, 0.95, 0.75, 0.65, 0.9, 0.9, 0.55], gap="small")
        with cols[0]:
            st.text_input(
                "Description",
                key=k(f"desc_{rid}"),
                label_visibility="collapsed",
                placeholder="Description",
            )
        with cols[1]:
            cost = st.number_input(
                "Cost",
                min_value=0.0,
                step=1.0,
                format="%.2f",
                key=k(f"cost_{rid}"),
                label_visibility="collapsed",
            )
        with cols[2]:
            markup = st.number_input(
                "Markup %",
                min_value=0.0,
                step=0.5,
                key=k(f"mk_{rid}"),
                label_visibility="collapsed",
            )
        with cols[3]:
            st.checkbox("Tax", key=k(f"tax_{rid}"), label_visibility="collapsed")
        totals = simple_line_totals(cost, markup)
        with cols[4]:
            st.markdown(
                f'<div style="padding-top:0.45rem;font-weight:700;font-size:0.82rem;">'
                f"{html.escape(fmt_currency(totals['cost_total']))}</div>",
                unsafe_allow_html=True,
            )
        with cols[5]:
            st.markdown(
                f'<div style="padding-top:0.45rem;font-weight:700;font-size:0.82rem;">'
                f"{html.escape(fmt_currency(totals['price_total']))}</div>",
                unsafe_allow_html=True,
            )
        with cols[6]:
            if st.button("✕", key=k(f"rm_{rid}"), help="Remove row"):
                remove_rid = rid

    if tab_entry:
        _maybe_auto_extend_batch_draft(
            draft_key,
            draft_rows,
            is_row_filled=lambda row_id: float(st.session_state.get(k(f"cost_{row_id}")) or 0) > 0
            and bool(str(st.session_state.get(k(f"desc_{row_id}")) or "").strip()),
            append_row=_new_blank_batch_row,
        )

    if remove_rid:
        remaining = [r for r in draft_rows if str(r.get("rid")) != remove_rid]
        st.session_state[draft_key] = remaining or _init_rows()
        st.rerun()

    if not tab_entry:
        add_col, _ = st.columns([1, 3], gap="small")
        with add_col:
            if st.button("+ Add Row", key=k("add_row"), use_container_width=True):
                draft_rows.append(_new_blank_batch_row())
                st.session_state[draft_key] = draft_rows
                st.rerun()

    save_col, cancel_col, _ = st.columns([1, 1, 2], gap="small")
    with save_col:
        save_clicked = st.button(
            "Save Other Costs",
            key=k("save"),
            type="primary",
            use_container_width=True,
        )
    if not tab_entry:
        with cancel_col:
            cancel_clicked = st.button("Cancel", key=k("cancel"), use_container_width=True)
    else:
        cancel_clicked = False

    if cancel_clicked:
        _clear_batch_form(form_state_key=fk, draft_key=draft_key)
        st.rerun()

    if save_clicked:
        payloads: list[dict[str, Any]] = []
        for row in draft_rows:
            rid = str(row.get("rid") or "")
            if not rid:
                continue
            cost = float(st.session_state.get(k(f"cost_{rid}")) or 0)
            if cost <= 0:
                continue
            description = str(st.session_state.get(k(f"desc_{rid}")) or "").strip()
            if not description:
                continue
            payloads.append(
                {
                    "description": description,
                    "cost_total": cost,
                    "markup_percent": float(st.session_state.get(k(f"mk_{rid}")) or default_markup),
                    "taxable": bool(st.session_state.get(k(f"tax_{rid}"))),
                }
            )
        if not payloads:
            st.error("Enter at least one other cost line with a description and cost.")
        else:
            ok, err = _service_ok(add_estimate_other_cost_batch(eid, payloads))
            if ok:
                if tab_entry:
                    _reset_tab_batch_draft(draft_key, _init_rows)
                else:
                    _clear_batch_form(form_state_key=fk, draft_key=draft_key)
                count = len(payloads)
                st.success(f"Saved {count} other cost line{'s' if count != 1 else ''}.")
                st.rerun()
            st.error(err)

    if not tab_entry:
        _close_compact_form_card()


def _travel_basis_text(row: dict[str, Any]) -> str:
    t = str(row.get("travel_type") or "")
    if t == "Mileage":
        return f"{row.get('miles', 0)} miles x {fmt_currency(row.get('mileage_rate'))} x {row.get('trips', 1)} trips"
    if t == "Drive Time":
        return f"{row.get('travel_hours', 0)} hrs x {fmt_currency(row.get('hourly_rate'))} x {row.get('people', 1)} people"
    if t == "Lodging":
        return f"{row.get('nights', 0)} nights x {fmt_currency(row.get('lodging_rate'))} x {row.get('people', 1)} people"
    if t == "Per Diem":
        return f"{row.get('per_diem_days', 0)} days x {fmt_currency(row.get('per_diem_rate'))} x {row.get('people', 1)} people"
    if t == "Airfare":
        return f"{fmt_currency(row.get('airfare_cost'))} x {row.get('people', 1)} people"
    if t == "Rental Vehicle":
        return fmt_currency(row.get("rental_vehicle_cost"))
    if t == "Fuel":
        return fmt_currency(row.get("fuel_cost"))
    if t == "Parking / Tolls":
        return fmt_currency(row.get("parking_tolls_cost"))
    return fmt_currency(row.get("other_cost"))


def _travel_form_data(eid: str, *, key_prefix: str = "ecb_trv") -> dict[str, Any]:
    k = lambda field: _line_form_key(key_prefix, eid, field)  # noqa: E731
    return {
        "travel_type": st.session_state.get(k("type"), "Mileage"),
        "description": st.session_state.get(k("desc"), ""),
        "origin": st.session_state.get(k("origin"), ""),
        "destination": st.session_state.get(k("dest"), ""),
        "miles": st.session_state.get(k("miles"), 0.0),
        "mileage_rate": st.session_state.get(k("mrate"), 0.0),
        "trips": st.session_state.get(k("trips"), 1.0),
        "people": st.session_state.get(k("people"), 1.0),
        "travel_hours": st.session_state.get(k("hours"), 0.0),
        "hourly_rate": st.session_state.get(k("hrate"), 0.0),
        "nights": st.session_state.get(k("nights"), 0.0),
        "lodging_rate": st.session_state.get(k("lrate"), 0.0),
        "per_diem_days": st.session_state.get(k("pdays"), 0.0),
        "per_diem_rate": st.session_state.get(k("prate"), 0.0),
        "airfare_cost": st.session_state.get(k("air"), 0.0),
        "rental_vehicle_cost": st.session_state.get(k("rental"), 0.0),
        "fuel_cost": st.session_state.get(k("fuel"), 0.0),
        "parking_tolls_cost": st.session_state.get(k("park"), 0.0),
        "other_cost": st.session_state.get(k("other"), 0.0),
        "markup_percent": st.session_state.get(k("mk"), 0.0),
        "taxable": st.session_state.get(k("tax"), False),
        "notes": st.session_state.get(k("notes"), ""),
    }


def _seed_travel_rate_defaults(k: Callable[[str], str]) -> None:
    if st.session_state.get(k("seeded")):
        return
    defaults = travel_defaults()
    st.session_state.setdefault(k("mrate"), defaults["mileage_rate"])
    st.session_state.setdefault(k("prate"), defaults["per_diem_rate"])
    st.session_state.setdefault(k("lrate"), defaults["lodging_rate"])
    st.session_state.setdefault(k("hrate"), defaults["hourly_travel_rate"])
    st.session_state[k("seeded")] = True


def _seed_travel_batch_row_widgets(
    k: Callable[[str], str],
    row_id: str,
    *,
    default_markup: float,
    defaults: dict[str, float],
) -> None:
    if k(f"type_{row_id}") not in st.session_state:
        st.session_state[k(f"type_{row_id}")] = "Mileage"
    if k(f"qty_{row_id}") not in st.session_state:
        st.session_state[k(f"qty_{row_id}")] = 0.0
    if k(f"rate_{row_id}") not in st.session_state:
        st.session_state[k(f"rate_{row_id}")] = float(defaults.get("mileage_rate") or 0)
    if k(f"mult_{row_id}") not in st.session_state:
        st.session_state[k(f"mult_{row_id}")] = 1.0
    if k(f"mk_{row_id}") not in st.session_state:
        st.session_state[k(f"mk_{row_id}")] = default_markup


def _sync_travel_batch_type(
    k: Callable[[str], str],
    row_id: str,
    travel_type: str,
    defaults: dict[str, float],
) -> None:
    last_key = k(f"last_type_{row_id}")
    if st.session_state.get(last_key) == travel_type:
        return
    rate_defaults = {
        "Mileage": defaults.get("mileage_rate", 0),
        "Drive Time": defaults.get("hourly_travel_rate", 0),
        "Lodging": defaults.get("lodging_rate", 0),
        "Per Diem": defaults.get("per_diem_rate", 0),
    }
    if travel_type in rate_defaults:
        st.session_state[k(f"rate_{row_id}")] = float(rate_defaults[travel_type])
    st.session_state[last_key] = travel_type


def _render_add_travel_form(
    eid: str,
    est: dict[str, Any],
    *,
    key_prefix: str = "ecb_trv",
    form_state_key: str | None = None,
    tab_entry: bool = False,
) -> None:
    fk = form_state_key or f"ecb_form_trv_{eid}"
    k = lambda field: _line_form_key(key_prefix, eid, field)  # noqa: E731
    default_markup = float(est.get("default_travel_markup_pct") or 0)
    defaults = travel_defaults()
    draft_key = _batch_draft_key("trv", key_prefix, eid)

    def _init_rows() -> list[dict[str, str]]:
        return _initial_batch_draft_rows(_DEFAULT_BATCH_ROW_COUNT)

    if tab_entry:
        _ensure_tab_batch_draft(draft_key, _init_rows)
    elif draft_key not in st.session_state:
        st.session_state[draft_key] = _init_rows()

    travel_caption = (
        f"{_BATCH_ENTRY_CAPTION} Qty = miles, days, nights, hours, or flat cost. "
        "Rate = per-unit rate where applicable. × = trips or people."
    )
    if tab_entry:
        st.caption(travel_caption)
    else:
        _compact_form_card("Add Travel Costs")
        st.caption(travel_caption)

    hdr = st.columns([1.5, 0.75, 0.85, 0.65, 0.7, 0.85, 0.85, 0.55], gap="small")
    for col, label in zip(hdr, ("Type", "Qty", "Rate", "×", "Markup %", "Cost", "Price", "")):
        with col:
            st.markdown(
                f'<div style="font-size:0.72rem;font-weight:700;color:#64748b;">{html.escape(label)}</div>',
                unsafe_allow_html=True,
            )

    draft_rows: list[dict[str, str]] = list(st.session_state.get(draft_key) or [])
    remove_rid = ""
    for row in draft_rows:
        rid = str(row.get("rid") or "")
        if not rid:
            continue
        _seed_travel_batch_row_widgets(k, rid, default_markup=default_markup, defaults=defaults)
        cols = st.columns([1.5, 0.75, 0.85, 0.65, 0.7, 0.85, 0.85, 0.55], gap="small")
        with cols[0]:
            travel_type = st.selectbox(
                "Type",
                TRAVEL_TYPES,
                key=k(f"type_{rid}"),
                label_visibility="collapsed",
            )
            _sync_travel_batch_type(k, rid, travel_type, defaults)
        with cols[1]:
            qty = st.number_input(
                "Qty",
                min_value=0.0,
                step=1.0,
                key=k(f"qty_{rid}"),
                label_visibility="collapsed",
            )
        flat_types = {"Rental Vehicle", "Fuel", "Parking / Tolls", "Other Travel"}
        with cols[2]:
            if travel_type in flat_types:
                st.markdown(
                    '<div style="padding-top:0.45rem;font-size:0.78rem;color:#64748b;">—</div>',
                    unsafe_allow_html=True,
                )
                rate = 0.0
            else:
                rate = st.number_input(
                    "Rate",
                    min_value=0.0,
                    step=0.01,
                    format="%.2f",
                    key=k(f"rate_{rid}"),
                    label_visibility="collapsed",
                )
        with cols[3]:
            if travel_type in flat_types:
                st.markdown(
                    '<div style="padding-top:0.45rem;font-size:0.78rem;color:#64748b;">—</div>',
                    unsafe_allow_html=True,
                )
                mult = 1.0
            else:
                mult = st.number_input(
                    "×",
                    min_value=0.0,
                    step=1.0,
                    key=k(f"mult_{rid}"),
                    label_visibility="collapsed",
                )
        with cols[4]:
            markup = st.number_input(
                "Markup %",
                min_value=0.0,
                step=0.5,
                key=k(f"mk_{rid}"),
                label_visibility="collapsed",
            )
        payload = _travel_batch_payload(
            travel_type,
            qty=qty,
            rate=rate,
            multiplier=mult,
            markup=markup,
            defaults=defaults,
        )
        calc = calc_travel_line(payload)
        with cols[5]:
            st.markdown(
                f'<div style="padding-top:0.45rem;font-weight:700;font-size:0.82rem;">'
                f"{html.escape(fmt_currency(calc['cost_total']))}</div>",
                unsafe_allow_html=True,
            )
        with cols[6]:
            st.markdown(
                f'<div style="padding-top:0.45rem;font-weight:700;font-size:0.82rem;">'
                f"{html.escape(fmt_currency(calc['price_total']))}</div>",
                unsafe_allow_html=True,
            )
        with cols[7]:
            if st.button("✕", key=k(f"rm_{rid}"), help="Remove row"):
                remove_rid = rid

    if tab_entry:
        _maybe_auto_extend_batch_draft(
            draft_key,
            draft_rows,
            is_row_filled=lambda row_id: calc_travel_line(
                _travel_batch_payload(
                    str(st.session_state.get(k(f"type_{row_id}")) or "Mileage"),
                    qty=float(st.session_state.get(k(f"qty_{row_id}")) or 0),
                    rate=float(st.session_state.get(k(f"rate_{row_id}")) or 0),
                    multiplier=float(st.session_state.get(k(f"mult_{row_id}")) or 1),
                    markup=float(st.session_state.get(k(f"mk_{row_id}")) or default_markup),
                    defaults=defaults,
                )
            )["cost_total"]
            > 0,
            append_row=_new_blank_batch_row,
        )

    if remove_rid:
        remaining = [r for r in draft_rows if str(r.get("rid")) != remove_rid]
        st.session_state[draft_key] = remaining or _init_rows()
        st.rerun()

    if not tab_entry:
        add_col, _ = st.columns([1, 3], gap="small")
        with add_col:
            if st.button("+ Add Row", key=k("add_row"), use_container_width=True):
                draft_rows.append({"rid": uuid4().hex[:8]})
                st.session_state[draft_key] = draft_rows
                st.rerun()

    save_col, cancel_col, _ = st.columns([1, 1, 2], gap="small")
    with save_col:
        save_clicked = st.button("Save Travel Lines", key=k("save"), type="primary", use_container_width=True)
    if not tab_entry:
        with cancel_col:
            cancel_clicked = st.button("Cancel", key=k("cancel"), use_container_width=True)
    else:
        cancel_clicked = False

    if cancel_clicked:
        _clear_batch_form(form_state_key=fk, draft_key=draft_key)
        st.rerun()

    if save_clicked:
        payloads: list[dict[str, Any]] = []
        for row in draft_rows:
            rid = str(row.get("rid") or "")
            if not rid:
                continue
            travel_type = str(st.session_state.get(k(f"type_{rid}")) or "Mileage")
            qty = float(st.session_state.get(k(f"qty_{rid}")) or 0)
            rate = float(st.session_state.get(k(f"rate_{rid}")) or 0)
            mult = float(st.session_state.get(k(f"mult_{rid}")) or 1)
            markup = float(st.session_state.get(k(f"mk_{rid}")) or default_markup)
            payload = _travel_batch_payload(
                travel_type,
                qty=qty,
                rate=rate,
                multiplier=mult,
                markup=markup,
                defaults=defaults,
            )
            calc = calc_travel_line(payload)
            if calc["cost_total"] <= 0:
                continue
            payloads.append(payload)
        if not payloads:
            st.error("Enter at least one travel line with a cost.")
        else:
            ok, err = _service_ok(add_estimate_travel_batch(eid, payloads))
            if ok:
                if tab_entry:
                    _reset_tab_batch_draft(draft_key, _init_rows)
                else:
                    _clear_batch_form(form_state_key=fk, draft_key=draft_key)
                count = len(payloads)
                st.success(f"Saved {count} travel line{'s' if count != 1 else ''}.")
                st.rerun()
            st.error(err)

    if not tab_entry:
        _close_compact_form_card()


def _render_cost_builder_line_sections(est: dict[str, Any]) -> None:
    """Full line lists for each cost category (managed from Cost Builder)."""
    eid = str(est.get("id") or "")
    bundle = get_estimate_bundle(eid)

    st.markdown("#### Pricing Items")
    _render_deletable_lines(
        eid,
        ["SKU", "Description", "Qty", "Unit Cost", "Cost", "Price"],
        bundle["materials"],
        row_cells=lambda r: [
            html.escape(str(r.get("sku") or "—")),
            html.escape(str(r.get("description") or "—")),
            html.escape(str(r.get("quantity") or "")),
            html.escape(fmt_currency(r.get("unit_cost"))),
            html.escape(fmt_currency(r.get("cost_total"))),
            html.escape(fmt_currency(r.get("price_total"))),
        ],
        delete_fn=delete_estimate_material,
        key_prefix="ecb_mat",
    )

    st.markdown("#### Labor")
    _render_labor_lines_fragment(eid, est, key_prefix="ecb_lab")

    st.markdown("#### Equipment")
    _render_deletable_lines(
        eid,
        ["Equipment", "Duration", "Cost", "Price"],
        bundle["equipment"],
        row_cells=lambda r: [
            html.escape(str(r.get("equipment_name") or "—")),
            html.escape(f"{r.get('duration',0)} {r.get('duration_unit','')}" ),
            html.escape(fmt_currency(r.get("cost_total"))),
            html.escape(fmt_currency(r.get("price_total"))),
        ],
        delete_fn=delete_estimate_equipment,
        key_prefix="ecb_eq",
    )

    st.markdown("#### Travel")
    travel_lines = bundle.get("travel") or []
    if not travel_lines:
        st.caption("No travel lines yet.")
    else:
        for row in travel_lines:
            rid = str(row.get("id") or "")
            cells = [
                html.escape(str(row.get("travel_type") or "—")),
                html.escape(str(row.get("description") or "—")),
                html.escape(str(row.get("origin") or "—")),
                html.escape(str(row.get("destination") or "—")),
                html.escape(_travel_basis_text(row)),
                html.escape(fmt_currency(row.get("cost_total"))),
                html.escape(f"{float(row.get('markup_percent') or 0):.1f}%"),
                html.escape(fmt_currency(row.get("price_total"))),
                html.escape("Yes" if row.get("taxable") else "No"),
            ]
            c0, c_del = st.columns([8, 1], gap="small")
            with c0:
                _line_table(
                    [
                        "Type",
                        "Description",
                        "Origin",
                        "Destination",
                        "Qty / Basis",
                        "Cost",
                        "Markup %",
                        "Customer Price",
                        "Taxable",
                    ],
                    [cells],
                )
            with c_del:
                if st.button("✕", key=f"ecb_trv_del_{rid}", help="Delete travel line"):
                    ok, err = _service_ok(delete_estimate_travel(rid, estimate_id=eid))
                    if ok:
                        st.rerun()
                    st.error(err)

    st.markdown("#### Subcontractors")
    _render_deletable_lines(
        eid,
        ["Subcontractor", "Scope", "Cost", "Price"],
        bundle["subcontractors"],
        row_cells=lambda r: [
            html.escape(str(r.get("subcontractor_name") or "—")),
            html.escape(str(r.get("description") or "—")),
            html.escape(fmt_currency(r.get("cost_total"))),
            html.escape(fmt_currency(r.get("price_total"))),
        ],
        delete_fn=delete_estimate_subcontractor,
        key_prefix="ecb_sub",
    )

    st.markdown("#### Other Costs")
    _render_deletable_lines(
        eid,
        ["Description", "Category", "Cost", "Price"],
        bundle["other_costs"],
        row_cells=lambda r: [
            html.escape(str(r.get("description") or "—")),
            html.escape(str(r.get("category") or "—")),
            html.escape(fmt_currency(r.get("cost_total"))),
            html.escape(fmt_currency(r.get("price_total"))),
        ],
        delete_fn=delete_estimate_other_cost,
        key_prefix="ecb_oth",
    )


def render_travel_tab(est: dict[str, Any]) -> None:
    eid = str(est.get("id") or "")
    if is_demo_id(eid):
        st.info("Save this estimate to Supabase before adding travel costs.")
        return

    bundle = get_estimate_bundle(eid)
    travel_lines = bundle.get("travel") or []
    travel_totals = calc_travel_total(travel_lines)
    cols = st.columns(3, gap="small")
    cards = [
        ("Travel Cost", fmt_currency(travel_totals.get("travel_cost"))),
        ("Travel Markup", fmt_currency(travel_totals.get("travel_markup"))),
        ("Travel Customer Price", fmt_currency(travel_totals.get("travel_price"))),
    ]
    for col, (label, value) in zip(cols, cards):
        with col:
            st.markdown(
                f'<div class="ips-est-summary-card">'
                f'<div class="ips-est-summary-label">{html.escape(label)}</div>'
                f'<div class="ips-est-summary-value">{html.escape(value)}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )

    if travel_lines:
        st.caption("Saved rental/travel lines — remove with ✕, or add more lines below.")
        for row in travel_lines:
            rid = str(row.get("id") or "")
            cells = [
                html.escape(str(row.get("travel_type") or "—")),
                html.escape(str(row.get("description") or "—")),
                html.escape(str(row.get("origin") or "—")),
                html.escape(str(row.get("destination") or "—")),
                html.escape(_travel_basis_text(row)),
                html.escape(fmt_currency(row.get("cost_total"))),
                html.escape(f"{float(row.get('markup_percent') or 0):.1f}%"),
                html.escape(fmt_currency(row.get("price_total"))),
                html.escape("Yes" if row.get("taxable") else "No"),
            ]
            c0, c_del = st.columns([8, 1], gap="small")
            with c0:
                _line_table(
                    ["Type", "Description", "Origin", "Destination", "Qty / Basis", "Cost", "Markup %", "Customer Price", "Taxable"],
                    [cells],
                )
            with c_del:
                if st.button("✕", key=f"trv_tab_del_{rid}", help="Delete travel line"):
                    ok, err = _service_ok(delete_estimate_travel(rid, estimate_id=eid))
                    if ok:
                        st.rerun()
                    st.error(err)

    fk = f"trv_tab_form_{eid}"
    draft_key = _batch_draft_key("trv", "trv_tab", eid)
    _open_tab_entry_form(
        form_state_key=fk,
        draft_key=draft_key,
        init_rows=lambda: _initial_batch_draft_rows(_DEFAULT_BATCH_ROW_COUNT),
    )
    _render_add_travel_form(
        eid,
        est,
        key_prefix="trv_tab",
        form_state_key=fk,
        tab_entry=True,
    )


def _render_deletable_lines(
    eid: str,
    headers: list[str],
    rows: list[dict[str, Any]],
    *,
    row_cells: Callable[[dict[str, Any]], list[str]],
    delete_fn: Callable[[str, str], Any],
    key_prefix: str,
) -> None:
    if not rows:
        st.caption("No lines yet.")
        return
    for row in rows:
        rid = str(row.get("id") or "")
        cells = row_cells(row)
        c0, c_del = st.columns([8, 1], gap="small")
        with c0:
            _line_table(headers, [cells])
        with c_del:
            if st.button("✕", key=f"{key_prefix}_del_{rid}", help="Delete line"):
                ok, err = _service_ok(delete_fn(rid, estimate_id=eid))
                if ok:
                    st.rerun()
                st.error(err)


def _labor_line_update_payload(eid: str, row: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "estimate_id": eid,
        "labor_type": row.get("labor_type") or row.get("role_name"),
        "role_name": row.get("role_name"),
        "description": row.get("description") or row.get("role_name"),
        "st_hours": float(row.get("st_hours") or 0),
        "ot_hours": float(row.get("ot_hours") or 0),
        "st_rate": float(row.get("st_rate") or 0),
        "ot_rate": float(row.get("ot_rate") or 0),
        "markup_percent": float(row.get("markup_percent") or 0),
        "notes": row.get("notes") or "",
    }
    payload.update(overrides)
    return payload


def _labor_inline_hour_keys(key_prefix: str, rid: str) -> tuple[str, str]:
    return f"{key_prefix}_sth_{rid}", f"{key_prefix}_oth_{rid}"


def _labor_inline_hours_changed(key_prefix: str, row: dict[str, Any]) -> bool:
    rid = str(row.get("id") or "")
    st_key, ot_key = _labor_inline_hour_keys(key_prefix, rid)
    saved_st = float(row.get("st_hours") or 0)
    saved_ot = float(row.get("ot_hours") or 0)
    cur_st = float(st.session_state.get(st_key, saved_st))
    cur_ot = float(st.session_state.get(ot_key, saved_ot))
    return abs(cur_st - saved_st) > 0.001 or abs(cur_ot - saved_ot) > 0.001


def _sync_labor_row_hours_saved(key_prefix: str, row: dict[str, Any], *, st_hours: float, ot_hours: float) -> None:
    rid = str(row.get("id") or "")
    st_key, ot_key = _labor_inline_hour_keys(key_prefix, rid)
    sync_key = f"{key_prefix}_hrs_sync_{rid}"
    st.session_state[st_key] = float(st_hours)
    st.session_state[ot_key] = float(ot_hours)
    st.session_state[sync_key] = f"{float(st_hours):.3f}|{float(ot_hours):.3f}"


def _apply_labor_hours_save_result(eid: str, result) -> tuple[bool, str | None]:
    ok, err = _service_ok(result)
    if ok:
        totals = getattr(result, "data", None) or {}
        if totals:
            _cache_cost_builder_totals(eid, totals)
    return ok, err


def _finish_labor_hours_save(
    eid: str,
    rows: list[dict[str, Any]],
    *,
    key_prefix: str,
    result,
) -> tuple[bool, str | None]:
    ok, err = _apply_labor_hours_save_result(eid, result)
    if ok:
        for row in rows:
            rid = str(row.get("id") or "")
            st_key, ot_key = _labor_inline_hour_keys(key_prefix, rid)
            _sync_labor_row_hours_saved(
                key_prefix,
                row,
                st_hours=float(st.session_state.get(st_key, row.get("st_hours") or 0)),
                ot_hours=float(st.session_state.get(ot_key, row.get("ot_hours") or 0)),
            )
        ips_app_rerun()
    return ok, err


def _save_labor_line_hours(
    eid: str,
    row: dict[str, Any],
    *,
    key_prefix: str,
    st_hours: float,
    ot_hours: float,
) -> tuple[bool, str | None]:
    rid = str(row.get("id") or "")
    return _finish_labor_hours_save(
        eid,
        [row],
        key_prefix=key_prefix,
        result=update_estimate_labor(
            rid,
            _labor_line_update_payload(eid, row, st_hours=st_hours, ot_hours=ot_hours),
        ),
    )


def _save_labor_lines_hours_batch(
    eid: str,
    rows: list[dict[str, Any]],
    *,
    key_prefix: str,
) -> tuple[bool, str | None]:
    updates: list[dict[str, Any]] = []
    for row in rows:
        rid = str(row.get("id") or "")
        st_key, ot_key = _labor_inline_hour_keys(key_prefix, rid)
        updates.append(
            {
                "line_id": rid,
                **_labor_line_update_payload(
                    eid,
                    row,
                    st_hours=float(st.session_state.get(st_key, row.get("st_hours") or 0)),
                    ot_hours=float(st.session_state.get(ot_key, row.get("ot_hours") or 0)),
                ),
            }
        )
    return _finish_labor_hours_save(
        eid,
        rows,
        key_prefix=key_prefix,
        result=update_estimate_labor_batch(eid, updates),
    )


def _render_labor_edit_form(
    eid: str,
    row: dict[str, Any],
    *,
    key_prefix: str,
) -> None:
    rid = str(row.get("id") or "")
    pk = f"{key_prefix}_edit_{rid}"
    c1, c2, c3, c4, c5 = st.columns(5, gap="small")
    with c1:
        st_hours = st.number_input(
            "ST Hrs",
            min_value=0.0,
            step=0.5,
            value=float(row.get("st_hours") or 0),
            key=f"{pk}_sth",
        )
    with c2:
        ot_hours = st.number_input(
            "OT Hrs",
            min_value=0.0,
            step=0.5,
            value=float(row.get("ot_hours") or 0),
            key=f"{pk}_oth",
        )
    with c3:
        st_rate = st.number_input(
            "ST Rate",
            min_value=0.0,
            step=1.0,
            format="%.2f",
            value=float(row.get("st_rate") or 0),
            key=f"{pk}_str",
        )
    with c4:
        ot_rate = st.number_input(
            "OT Rate",
            min_value=0.0,
            step=1.0,
            format="%.2f",
            value=float(row.get("ot_rate") or 0),
            key=f"{pk}_otr",
        )
    with c5:
        markup = st.number_input(
            "Markup %",
            min_value=0.0,
            step=0.5,
            value=float(row.get("markup_percent") or 0),
            key=f"{pk}_mk",
        )
    s1, s2 = st.columns(2, gap="small")
    with s1:
        if st.button("Save line", key=f"{pk}_save", type="primary", use_container_width=True):
            ok, err = _service_ok(
                update_estimate_labor(
                    rid,
                    _labor_line_update_payload(
                        eid,
                        row,
                        st_hours=st_hours,
                        ot_hours=ot_hours,
                        st_rate=st_rate,
                        ot_rate=ot_rate,
                        markup_percent=markup,
                    ),
                )
            )
            if ok:
                st.session_state.pop(f"{key_prefix}_edit_id", None)
                st.rerun()
            st.error(err)
    with s2:
        if st.button("Cancel", key=f"{pk}_cancel", use_container_width=True):
            st.session_state.pop(f"{key_prefix}_edit_id", None)
            st.rerun()


def _render_labor_lines(
    eid: str,
    rows: list[dict[str, Any]],
    *,
    key_prefix: str,
) -> None:
    if not rows:
        st.caption("No lines yet.")
        return

    edit_id = str(st.session_state.get(f"{key_prefix}_edit_id") or "")
    pending = [r for r in rows if edit_id != str(r.get("id") or "") and _labor_inline_hours_changed(key_prefix, r)]
    if pending:
        if st.button(
            f"Save all hour changes ({len(pending)})",
            key=f"{key_prefix}_save_all_hrs_{eid}",
            type="primary",
        ):
            ok, err = _save_labor_lines_hours_batch(eid, pending, key_prefix=key_prefix)
            if err and not ok:
                st.error(err)

    st.caption("Edit ST/OT hours directly in each row. Use ✎ to change rates or markup.")
    col_widths = [2.3, 0.7, 0.7, 1.15, 0.85, 0.85, 1.05]
    header = st.columns(col_widths, gap="small")
    for idx, label in enumerate(["Role", "ST Hrs", "OT Hrs", "ST/OT Rate", "Cost", "Price", ""]):
        with header[idx]:
            st.markdown(f"**{label}**")

    for row in rows:
        rid = str(row.get("id") or "")
        if edit_id == rid:
            st.markdown(f"**Edit rates — {html.escape(str(row.get('role_name') or 'Labor'))}**")
            _render_labor_edit_form(eid, row, key_prefix=key_prefix)
            continue

        role_name = str(row.get("role_name") or "—")
        st_rate = float(row.get("st_rate") or 0)
        ot_rate = float(row.get("ot_rate") or 0)
        markup = float(row.get("markup_percent") or 0)
        st_key, ot_key = _labor_inline_hour_keys(key_prefix, rid)
        saved_st = float(row.get("st_hours") or 0)
        saved_ot = float(row.get("ot_hours") or 0)
        sync_key = f"{key_prefix}_hrs_sync_{rid}"
        snapshot = f"{saved_st:.3f}|{saved_ot:.3f}"
        if st.session_state.get(sync_key) != snapshot:
            st.session_state[st_key] = saved_st
            st.session_state[ot_key] = saved_ot
            st.session_state[sync_key] = snapshot

        cols = st.columns(col_widths, gap="small")
        with cols[0]:
            st.markdown(role_name)
        with cols[1]:
            st_hours = st.number_input(
                "ST Hrs",
                min_value=0.0,
                step=0.5,
                format="%.1f",
                key=st_key,
                label_visibility="collapsed",
            )
        with cols[2]:
            ot_hours = st.number_input(
                "OT Hrs",
                min_value=0.0,
                step=0.5,
                format="%.1f",
                key=ot_key,
                label_visibility="collapsed",
            )
        preview = labor_line_totals(st_hours, ot_hours, st_rate, ot_rate, markup)
        with cols[3]:
            st.caption(_labor_line_rate_text(row))
        with cols[4]:
            st.caption(fmt_currency(preview.get("cost_total")))
        with cols[5]:
            st.caption(fmt_currency(preview.get("price_total")))
        with cols[6]:
            act1, act2, act3 = st.columns(3, gap="small")
            changed = _labor_inline_hours_changed(key_prefix, row)
            with act1:
                if st.button(
                    "Save",
                    key=f"{key_prefix}_save_hrs_{rid}",
                    type="primary" if changed else "secondary",
                    disabled=not changed,
                    use_container_width=True,
                ):
                    ok, err = _save_labor_line_hours(
                        eid,
                        row,
                        key_prefix=key_prefix,
                        st_hours=float(st_hours),
                        ot_hours=float(ot_hours),
                    )
                    if err and not ok:
                        st.error(err)
            with act2:
                if st.button("✎", key=f"{key_prefix}_edit_{rid}", help="Edit rates / markup"):
                    st.session_state[f"{key_prefix}_edit_id"] = rid
                    st.rerun()
            with act3:
                if st.button("✕", key=f"{key_prefix}_del_{rid}", help="Delete line"):
                    ok, err = _service_ok(delete_estimate_labor(rid, estimate_id=eid))
                    if ok:
                        st.rerun()
                    st.error(err)


@fragment
def _render_labor_lines_fragment(
    eid: str,
    est: dict[str, Any],
    *,
    key_prefix: str,
) -> None:
    """Labor lines rerun locally so hour saves do not rebuild the whole Cost Builder."""
    labor, _ = get_estimate_labor(eid)
    _render_labor_lines(eid, labor, key_prefix=key_prefix)


def render_materials_tab(
    est: dict[str, Any],
    *,
    pricing_guide_options: list[tuple[str, dict[str, Any]]] | None = None,
    inventory_options: list[tuple[str, dict[str, Any]]] | None = None,
) -> None:
    eid = str(est.get("id") or "")
    bundle = get_estimate_bundle(eid)
    rows = bundle["materials"]
    if rows:
        st.caption("Saved pricing items — remove with ✕, or add more lines below.")
        _render_deletable_lines(
            eid,
            ["SKU", "Description", "Qty", "Unit Cost", "Cost", "Price"],
            rows,
            row_cells=lambda r: [
                html.escape(str(r.get("sku") or "—")),
                html.escape(str(r.get("description") or "—")),
                html.escape(str(r.get("quantity") or "")),
                html.escape(fmt_currency(r.get("unit_cost"))),
                html.escape(fmt_currency(r.get("cost_total"))),
                html.escape(fmt_currency(r.get("price_total"))),
            ],
            delete_fn=delete_estimate_material,
            key_prefix="mat_tab",
        )
    fk = f"mat_tab_form_{eid}"
    draft_key = _batch_draft_key("mat", "mat_tab", eid)
    _open_tab_entry_form(
        form_state_key=fk,
        draft_key=draft_key,
        init_rows=lambda: _initial_batch_draft_rows(_DEFAULT_BATCH_ROW_COUNT, pick=_CUSTOM_MATERIAL_LABEL),
    )
    _render_add_material_form(
        eid,
        est,
        pricing_guide_options=pricing_guide_options,
        inventory_options=inventory_options,
        key_prefix="mat_tab",
        form_state_key=fk,
        tab_entry=True,
    )


def render_labor_tab(est: dict[str, Any]) -> None:
    eid = str(est.get("id") or "")
    fk = f"lab_tab_form_{eid}"
    draft_key = _labor_batch_draft_key("lab_tab", eid)

    def _init_rows() -> list[dict[str, str]]:
        labor_options = labor_options_as_select()
        lab_map = {label: opt for label, opt in labor_options}
        role_labels = [label for label, _ in labor_options] or list(LABOR_ROLE_TYPES)
        default_markup = float(est.get("default_labor_markup_pct") or 0)
        return [
            _new_labor_batch_row(
                role_labels=role_labels,
                lab_map=lab_map,
                default_markup=default_markup,
            )
            for _ in range(_DEFAULT_BATCH_ROW_COUNT)
        ]

    _open_tab_entry_form(form_state_key=fk, draft_key=draft_key, init_rows=_init_rows)
    labor, _ = get_estimate_labor(eid)
    if labor:
        st.caption("Saved labor lines — edit hours inline, or add new lines below.")
        _render_labor_lines_fragment(eid, est, key_prefix="lab_tab")
    _render_add_labor_form(
        eid,
        est,
        key_prefix="lab_tab",
        form_state_key=fk,
        tab_entry=True,
    )


def render_equipment_tab(est: dict[str, Any], *, asset_options: list[tuple[str, dict[str, Any]]] | None = None) -> None:
    eid = str(est.get("id") or "")
    bundle = get_estimate_bundle(eid)
    equipment = bundle["equipment"]
    if equipment:
        st.caption("Saved equipment lines — remove with ✕, or add more lines below.")
        _render_deletable_lines(
            eid,
            ["Equipment", "Duration", "Cost", "Price"],
            equipment,
            row_cells=lambda r: [
                html.escape(str(r.get("equipment_name") or "—")),
                html.escape(f"{r.get('duration',0)} {r.get('duration_unit','')}" ),
                html.escape(fmt_currency(r.get("cost_total"))),
                html.escape(fmt_currency(r.get("price_total"))),
            ],
            delete_fn=delete_estimate_equipment,
            key_prefix="eq_tab",
        )
    fk = f"eq_tab_form_{eid}"
    draft_key = _batch_draft_key("eq", "eq_tab", eid)
    labels = [label for label, _ in (asset_options or [])]

    def _init_rows() -> list[dict[str, str]]:
        return _initial_batch_draft_rows(_DEFAULT_BATCH_ROW_COUNT, pick=labels[0] if labels else "")

    _open_tab_entry_form(form_state_key=fk, draft_key=draft_key, init_rows=_init_rows)
    _render_add_equipment_form(
        eid,
        est,
        asset_options or [],
        key_prefix="eq_tab",
        form_state_key=fk,
        tab_entry=True,
    )


def render_subcontractors_tab(est: dict[str, Any], *, vendor_options: list[str] | None = None) -> None:
    eid = str(est.get("id") or "")
    bundle = get_estimate_bundle(eid)
    subs = bundle["subcontractors"]
    if subs:
        st.caption("Saved subcontractor lines — remove with ✕, or add more lines below.")
        _render_deletable_lines(
            eid,
            ["Subcontractor", "Scope", "Cost", "Price"],
            subs,
            row_cells=lambda r: [
                html.escape(str(r.get("subcontractor_name") or "—")),
                html.escape(str(r.get("description") or "—")),
                html.escape(fmt_currency(r.get("cost_total"))),
                html.escape(fmt_currency(r.get("price_total"))),
            ],
            delete_fn=delete_estimate_subcontractor,
            key_prefix="sub_tab",
        )
    fk = f"sub_tab_form_{eid}"
    draft_key = _batch_draft_key("sub", "sub_tab", eid)
    _open_tab_entry_form(
        form_state_key=fk,
        draft_key=draft_key,
        init_rows=lambda: _initial_batch_draft_rows(_DEFAULT_BATCH_ROW_COUNT),
    )
    _render_add_subcontractor_form(
        eid,
        est,
        vendor_options or [],
        key_prefix="sub_tab",
        form_state_key=fk,
        tab_entry=True,
    )


def render_other_costs_tab(est: dict[str, Any]) -> None:
    eid = str(est.get("id") or "")
    bundle = get_estimate_bundle(eid)
    others = bundle["other_costs"]
    if others:
        st.caption("Saved other cost lines — remove with ✕, or add more lines below.")
        _render_deletable_lines(
            eid,
            ["Description", "Category", "Cost", "Price"],
            others,
            row_cells=lambda r: [
                html.escape(str(r.get("description") or "—")),
                html.escape(str(r.get("category") or "—")),
                html.escape(fmt_currency(r.get("cost_total"))),
                html.escape(fmt_currency(r.get("price_total"))),
            ],
            delete_fn=delete_estimate_other_cost,
            key_prefix="oth_tab",
        )
    fk = f"oth_tab_form_{eid}"
    draft_key = _batch_draft_key("oth", "oth_tab", eid)
    _open_tab_entry_form(
        form_state_key=fk,
        draft_key=draft_key,
        init_rows=lambda: _initial_batch_draft_rows(_DEFAULT_BATCH_ROW_COUNT),
    )
    _render_add_other_form(
        eid,
        est,
        key_prefix="oth_tab",
        form_state_key=fk,
        tab_entry=True,
    )


def _estimate_scope_display_text(est: dict[str, Any]) -> str:
    """Long-form scope for the Scope of Work tab (not project title)."""
    sow = str(est.get("scope_of_work") or "").strip()
    if sow:
        return sow
    desc = str(est.get("description") or "").strip()
    proj = str(est.get("project_name") or "").strip()
    if desc and desc != proj and desc != "—":
        return desc
    return ""


def render_scope_of_work_tab(
    est: dict[str, Any],
    *,
    persist_fn: Callable[[dict[str, Any], str], tuple[bool, str]],
    on_saved: Callable[[], None] | None = None,
) -> None:
    eid = str(est.get("id") or "")
    if is_demo_id(eid):
        st.info("Save this estimate to Supabase before editing scope of work.")
        return

    scope_text = _estimate_scope_display_text(est)
    cust_resp = str(est.get("customer_responsibilities") or "").strip()
    seed_key = f"est_sow_seeded_{eid}"
    if not st.session_state.get(seed_key):
        st.session_state[f"est_sow_text_{eid}"] = scope_text
        st.session_state[f"est_sow_cr_{eid}"] = cust_resp
        st.session_state[seed_key] = True

    st.caption(
        "Enter the full scope of work for proposals and field teams. "
        "Keep the **Project** name short on Overview (for example, Orange Turnaround Extra Work). "
        "**Click Save scope** below to persist your text — switching tabs does not auto-save."
    )
    st.text_area(
        "Scope of Work",
        height=320,
        key=f"est_sow_text_{eid}",
        placeholder=(
            "Describe work to be performed, exclusions, assumptions, "
            "schedule constraints, and deliverables…"
        ),
    )
    st.text_area(
        "Customer responsibilities (optional)",
        height=160,
        key=f"est_sow_cr_{eid}",
        placeholder="Customer-furnished items, access, permits, utilities, etc.",
    )

    if st.button("Save scope", key=f"est_sow_save_{eid}", type="primary"):
        ok, msg = persist_fn(
            {
                "scope_of_work": st.session_state.get(f"est_sow_text_{eid}", ""),
                "customer_responsibilities": st.session_state.get(f"est_sow_cr_{eid}", ""),
            },
            eid,
        )
        if ok:
            st.success(msg or "Scope of work saved.")
            if on_saved:
                on_saved()
            st.rerun()
        else:
            st.error(msg or "Could not save scope of work.")


def render_markups_tab(est: dict[str, Any]) -> None:
    eid = str(est.get("id") or "")
    current_mk = resolve_global_markup_pct(est)
    category_defaults = resolve_category_markup_defaults(est)

    st.markdown("##### Default Markup Settings")
    st.caption("Price = Cost × (1 + Markup %). Example: 15% markup on $100 cost → $115 price.")
    global_mk = st.number_input(
        "Global markup %",
        min_value=0.0,
        value=float(current_mk),
        step=0.01,
        format="%.2f",
        key=f"mk_global_{eid}",
    )

    if st.button("Save Default Markup", key=f"mk_save_default_{eid}"):
        result = save_global_markup_settings(eid, global_mk, apply_to_existing_lines=False, recalculate=False)
        if result.ok:
            st.success("Default markup saved. New Cost Builder lines will use this markup.")
            st.rerun()
        else:
            st.error(str(result.error or "Could not save default markup."))

    apply_existing = st.checkbox(
        "Apply to existing estimate lines",
        key=f"mk_apply_existing_{eid}",
        help="Update labor, equipment, travel, subcontractor, material, and other lines using saved markup defaults.",
    )

    if st.button("Save & Recalculate Estimate", key=f"mk_save_recalc_{eid}", type="primary"):
        result = save_global_markup_settings(
            eid,
            global_mk,
            apply_to_existing_lines=apply_existing,
            recalculate=True,
        )
        if result.ok:
            if apply_existing:
                st.success("Markup applied to all lines and estimate totals recalculated.")
            else:
                st.success("Default markup saved and estimate totals recalculated.")
            st.rerun()
        else:
            st.error(str(result.error or "Could not save markup settings."))

    with st.expander("Advanced", expanded=False):
        st.caption(
            "Optional per-category defaults for new lines only. "
            "When set, each category uses its own markup instead of the global default."
        )
        c1, c2 = st.columns(2)
        with c1:
            mat_mk = st.number_input(
                "Material markup %",
                min_value=0.0,
                value=float(category_defaults["material"]),
                step=0.01,
                format="%.2f",
                key=f"mk_adv_mat_{eid}",
            )
            lab_mk = st.number_input(
                "Labor markup %",
                min_value=0.0,
                value=float(category_defaults["labor"]),
                step=0.01,
                format="%.2f",
                key=f"mk_adv_lab_{eid}",
            )
            eq_mk = st.number_input(
                "Equipment markup %",
                min_value=0.0,
                value=float(category_defaults["equipment"]),
                step=0.01,
                format="%.2f",
                key=f"mk_adv_eq_{eid}",
            )
        with c2:
            trv_mk = st.number_input(
                "Travel markup %",
                min_value=0.0,
                value=float(category_defaults["travel"]),
                step=0.01,
                format="%.2f",
                key=f"mk_adv_trv_{eid}",
            )
            sub_mk = st.number_input(
                "Subcontractor markup %",
                min_value=0.0,
                value=float(category_defaults["subcontractor"]),
                step=0.01,
                format="%.2f",
                key=f"mk_adv_sub_{eid}",
            )
            oth_mk = st.number_input(
                "Other markup %",
                min_value=0.0,
                value=float(category_defaults["other"]),
                step=0.01,
                format="%.2f",
                key=f"mk_adv_oth_{eid}",
            )

        if st.button("Save category markups", key=f"mk_save_advanced_{eid}"):
            result = save_category_markup_settings(
                eid,
                {
                    "material": mat_mk,
                    "labor": lab_mk,
                    "equipment": eq_mk,
                    "travel": trv_mk,
                    "subcontractor": sub_mk,
                    "other": oth_mk,
                },
            )
            if result.ok:
                st.success("Category markup defaults saved.")
                st.rerun()
            else:
                st.error(str(result.error or "Could not save category markups."))


def render_summary_tab(est: dict[str, Any]) -> None:
    eid = str(est.get("id") or "")
    totals = calculate_estimate_totals(eid)
    render_cost_summary_cards(est, totals)

    cost_html = (
        f'<div class="ips-detail-grid">'
        f"{detail_field_html('Material cost', fmt_currency(totals.get('material_cost')))}"
        f"{detail_field_html('Labor cost', fmt_currency(totals.get('labor_cost')))}"
        f"{detail_field_html('Equipment cost', fmt_currency(totals.get('equipment_cost')))}"
        f"{detail_field_html('Travel cost', fmt_currency(totals.get('travel_cost')))}"
        f"{detail_field_html('Subcontractor cost', fmt_currency(totals.get('subcontractor_cost')))}"
        f"{detail_field_html('Other cost', fmt_currency(totals.get('other_cost')))}"
        f"{detail_field_html('Total job cost', fmt_currency(totals.get('total_cost')))}"
        f"</div>"
    )
    st.markdown(dialog_card_html("Cost Summary", cost_html), unsafe_allow_html=True)

    price_html = (
        f'<div class="ips-detail-grid">'
        f"{detail_field_html('Material markup', fmt_currency(totals.get('material_markup')))}"
        f"{detail_field_html('Labor markup', fmt_currency(totals.get('labor_markup')))}"
        f"{detail_field_html('Equipment markup', fmt_currency(totals.get('equipment_markup')))}"
        f"{detail_field_html('Travel markup', fmt_currency(totals.get('travel_markup')))}"
        f"{detail_field_html('Subcontractor markup', fmt_currency(totals.get('subcontractor_markup')))}"
        f"{detail_field_html('Other markup', fmt_currency(totals.get('other_markup')))}"
        f"{detail_field_html('Total markup', fmt_currency(totals.get('total_markup')))}"
        f"{detail_field_html('Subtotal before tax', fmt_currency(totals.get('subtotal_before_tax')))}"
        f"{detail_field_html('Taxable subtotal', fmt_currency(totals.get('taxable_subtotal')))}"
        f"{detail_field_html('Tax amount', fmt_currency(totals.get('tax_amount')))}"
        f"{detail_field_html('Final customer price', fmt_currency(totals.get('customer_price')))}"
        f"</div>"
    )
    st.markdown(dialog_card_html("Markup / Price Summary", price_html), unsafe_allow_html=True)

    margin_pct = f"{totals.get('gross_margin_percent', 0):.1f}%"
    profit_html = (
        f'<div class="ips-detail-grid">'
        f"{detail_field_html('Total cost', fmt_currency(totals.get('total_cost')))}"
        f"{detail_field_html('Customer price', fmt_currency(totals.get('customer_price')))}"
        f"{detail_field_html('Gross profit', fmt_currency(totals.get('gross_profit')))}"
        f"{detail_field_html('Gross margin %', margin_pct)}"
        f"</div>"
    )
    st.markdown(dialog_card_html("Profitability", profit_html), unsafe_allow_html=True)


def render_proposal_preview_tab(est: dict[str, Any]) -> None:
    """Customer quote preview and exports (single view aligned with Word/PDF)."""
    eid = str(est.get("id") or "")

    if is_demo_id(eid):
        st.info("Save estimate to Supabase to preview and download the customer quote.")
        return

    totals = calculate_estimate_totals(eid) if eid else {}
    from app.services.proposal_pdf_service import merge_proposal_totals
    totals = merge_proposal_totals(totals, est)

    try:
        docx_bytes, pdf_bytes, page_html, word_err, pdf_note = build_customer_quote_bundle(eid, est, totals=totals)
    except Exception as exc:
        st.error(f"Could not build customer quote: {exc}")
        return

    if word_err:
        st.error(word_err)
        return

    from app.estimate.proposal_exports import _inject_proposal_preview_styles
    _inject_proposal_preview_styles()
    st.markdown(page_html, unsafe_allow_html=True)

    slug = str(est.get("estimate_number") or est.get("quote_number") or "quote").strip() or "quote"
    d1, d2 = st.columns(2)
    with d1:
        st.download_button(
            "Download Quote (Word)",
            data=docx_bytes or b"",
            file_name=f"{slug}_quote.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            key=f"pp_word_{eid}",
            disabled=not docx_bytes,
            use_container_width=True,
        )
    with d2:
        st.download_button(
            "Download Quote (PDF)",
            data=pdf_bytes or b"",
            file_name=f"{slug}_quote.pdf",
            mime="application/pdf",
            key=f"pp_download_{eid}",
            type="primary",
            disabled=not pdf_bytes,
            use_container_width=True,
        )
    if not pdf_bytes and pdf_note:
        st.caption(pdf_note)

    if st.button("Mark as Sent", key=f"pp_sent_{eid}"):
        from app.pages._core._data import persist_estimate, get_estimate as _get_est
        cur = _get_est(eid) or est
        ok, msg = persist_estimate(
            {
                "estimate_number": cur.get("estimate_number"),
                "project_name": cur.get("project_name"),
                "customer": cur.get("customer"),
                "status": "Sent",
            },
            row_id=eid,
        )
        if ok:
            st.success(msg or "Estimate marked as Sent.")
            st.rerun()
        st.error(msg or "Could not update status.")
