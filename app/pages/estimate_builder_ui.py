"""Estimate costing builder tabs (Streamlit UI — no direct Supabase)."""

from __future__ import annotations

import html
from typing import Any, Callable

import streamlit as st

try:
    from app.components.record_modal import detail_field_html, dialog_card_html, safe_value
    from app.pages._core._crud import is_demo_id
    from app.services.estimate_costing_service import (
        DURATION_UNITS,
        LABOR_ROLE_TYPES,
        add_estimate_equipment,
        add_estimate_labor,
        add_estimate_material,
        add_estimate_other_cost,
        add_estimate_subcontractor,
        add_estimate_travel,
        calculate_estimate_totals,
        delete_estimate_equipment,
        delete_estimate_labor,
        delete_estimate_material,
        delete_estimate_other_cost,
        delete_estimate_subcontractor,
        delete_estimate_travel,
        get_estimate_bundle,
        recalculate_and_save_estimate_totals,
    )
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
except ImportError:
    from components.record_modal import detail_field_html, dialog_card_html, safe_value  # type: ignore
    from pages._core._crud import is_demo_id  # type: ignore
    from services.estimate_costing_service import (  # type: ignore
        DURATION_UNITS,
        LABOR_ROLE_TYPES,
        add_estimate_equipment,
        add_estimate_labor,
        add_estimate_material,
        add_estimate_other_cost,
        add_estimate_subcontractor,
        calculate_estimate_totals,
        delete_estimate_equipment,
        delete_estimate_labor,
        delete_estimate_material,
        delete_estimate_other_cost,
        delete_estimate_subcontractor,
        get_estimate_bundle,
        recalculate_and_save_estimate_totals,
    )
    from utils.estimate_calculations import TRAVEL_TYPES, calc_travel_line, calc_travel_total, margin_warning_class  # type: ignore
    from services.estimate_builder_helpers import (  # type: ignore
        equipment_line_totals,
        labor_line_totals,
        labor_options_as_select,
        material_line_totals,
        resolve_equipment_cost_rate,
        simple_line_totals,
        travel_defaults,
    )
    from utils.formatting import fmt_currency, fmt_date  # type: ignore
    from services.proposal_pdf_service import build_customer_quote_bundle  # type: ignore
    from services.pricing_guide_service import create_pricing_item_from_estimate_line  # type: ignore


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

    totals = calculate_estimate_totals(eid)
    stored_price = float(est.get("customer_price") or est.get("total") or 0)
    calc_price = float(totals.get("customer_price") or 0)
    if calc_price > 0 and abs(stored_price - calc_price) > 0.01:
        ok, _ = _service_ok(recalculate_and_save_estimate_totals(eid))
        if ok and on_saved:
            on_saved()
        totals = calculate_estimate_totals(eid)
    render_cost_summary_cards(est, totals)

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
            ok, err = _service_ok(recalculate_and_save_estimate_totals(eid))
            if ok:
                st.success("Totals updated.")
                if on_saved:
                    on_saved()
                st.rerun()
            else:
                st.error(err)
    st.markdown("</div>", unsafe_allow_html=True)

    if add_mat:
        st.session_state[f"ecb_form_mat_{eid}"] = True
    if add_lab:
        st.session_state[f"ecb_form_lab_{eid}"] = True
    if add_eq:
        st.session_state[f"ecb_form_eq_{eid}"] = True
    if add_trv:
        st.session_state[f"ecb_form_trv_{eid}"] = True
    if add_sub:
        st.session_state[f"ecb_form_sub_{eid}"] = True
    if add_other:
        st.session_state[f"ecb_form_other_{eid}"] = True

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


def _render_add_material_form(
    eid: str,
    est: dict[str, Any],
    *,
    pricing_guide_options: list[tuple[str, dict[str, Any]]] | None = None,
    inventory_options: list[tuple[str, dict[str, Any]]] | None = None,
    key_prefix: str = "ecb_mat",
    form_state_key: str | None = None,
) -> None:
    _ = inventory_options
    fk = form_state_key or f"ecb_form_mat_{eid}"
    k = lambda field: _line_form_key(key_prefix, eid, field)  # noqa: E731
    default_markup = float(est.get("default_material_markup_pct") or 0)
    pg_opts = pricing_guide_options or []
    pg_map = {label: item for label, item in pg_opts}
    pg_labels = [label for label, _ in pg_opts]
    use_custom = k("custom") not in st.session_state and not pg_opts

    _compact_form_card("Add Pricing Item")
    custom = st.checkbox("Custom item (not in Pricing Guide)", key=k("custom"), value=use_custom)
    item: dict[str, Any] = {}

    c1, c2 = st.columns(2, gap="small")
    with c1:
        if not custom:
            if pg_opts:
                pick = st.selectbox("Pricing item", pg_labels, key=k("pg"))
                item = _sync_pricing_guide_pick_state(k, pick, pg_map, taxable_key=k("tax"))
                st.caption(f"Type: **{item.get('item_type') or 'Material'}**")
            else:
                custom = True
                st.info("No pricing guide items available — add items under Pricing Guide or use a custom item.")
        else:
            item = {}

        if custom:
            st.text_input("Description", key=k("desc"), placeholder="Item description")
            save_to_guide = st.checkbox(
                "Save to Pricing Guide for future estimates",
                key=k("save_pg"),
            )

        qty = st.number_input("Quantity", min_value=0.0, value=1.0, key=k("qty"), step=1.0)
        markup = st.number_input(
            "Markup %",
            value=float(st.session_state.get(k("mk"), item.get("markup_pct") or default_markup)),
            key=k("mk"),
        )
        if k("tax") not in st.session_state:
            st.session_state[k("tax")] = bool(item.get("taxable", True))
        taxable = st.checkbox("Taxable", key=k("tax"))

    with c2:
        override = st.checkbox("Override cost", key=k("ovr"), disabled=custom or not item)
        if override or custom or not item:
            unit_cost = st.number_input(
                "Unit cost",
                min_value=0.0,
                value=float(st.session_state.get(k("uc"), item.get("unit_cost") or 0)),
                key=k("uc"),
            )
        else:
            unit_cost = float(item.get("unit_cost") or 0)
            _display_field("Unit Cost", fmt_currency(unit_cost))
            if unit_cost <= 0:
                st.warning("No default cost found. Enter a unit cost or enable cost override.")

        unit = str(item.get("unit") or st.session_state.get(k("unit")) or "EA")
        if custom or override or not item:
            unit = st.text_input("Unit", value=unit, key=k("unit"))
        else:
            _display_field("Unit", unit)

        totals = material_line_totals(qty, unit_cost, markup)
        _live_totals_card(
            [
                ("Cost Total", fmt_currency(totals["cost_total"])),
                ("Markup Amount", fmt_currency(totals["markup_amount"])),
                ("Customer Price", fmt_currency(totals["price_total"])),
            ]
        )

    with st.expander("Advanced details", expanded=False):
        st.markdown('<div class="ips-estimate-advanced-details">', unsafe_allow_html=True)
        if not custom:
            st.text_input("Description", key=k("desc"))
        st.text_input("SKU / Item code", key=k("sku"))
        st.text_input("Category", key=k("cat"))
        st.text_input("Vendor", key=k("vendor"))
        st.markdown("</div>", unsafe_allow_html=True)

    notes = st.text_area("Notes", key=k("notes"), height=56, placeholder="Notes (optional)")
    b1, b2 = st.columns(2, gap="small")
    with b1:
        if st.button("Save Pricing Item", key=k("save"), type="primary", use_container_width=True):
            item_save: dict[str, Any] = {}
            if not custom:
                pick_save = st.session_state.get(k("pg"))
                item_save = pg_map.get(pick_save, {}) if pick_save else {}
            if custom or not item_save:
                item_save = {
                    "item_type": "Material",
                    "description": st.session_state.get(k("desc")),
                    "category": st.session_state.get(k("cat")),
                    "unit": st.session_state.get(k("unit")) or unit,
                    "unit_cost": float(st.session_state.get(k("uc")) or 0),
                    "taxable": bool(st.session_state.get(k("tax"), True)),
                }
            if custom and st.session_state.get(k("save_pg")):
                pg_ok, pg_msg, pg_id = create_pricing_item_from_estimate_line(
                    {
                        "description": st.session_state.get(k("desc")),
                        "sku": st.session_state.get(k("sku")),
                        "category": st.session_state.get(k("cat")),
                        "unit": st.session_state.get(k("unit")) or unit,
                        "unit_cost": float(st.session_state.get(k("uc")) or 0),
                        "markup_percent": markup,
                        "taxable": bool(st.session_state.get(k("tax"), True)),
                        "vendor_id": st.session_state.get(k("vendor_id")),
                        "notes": notes,
                    }
                )
                if not pg_ok:
                    st.error(pg_msg)
                    return
                if pg_id:
                    item_save["pricing_item_id"] = pg_id
                    item_save["id"] = pg_id
            ok, err = _save_pricing_item_line(
                eid,
                est,
                item_save,
                qty=qty,
                markup=markup,
                notes=notes,
                k=k,
            )
            if ok:
                st.session_state.pop(fk, None)
                if custom and st.session_state.get(k("save_pg")):
                    st.success("Pricing item added to this estimate and saved to the Pricing Guide.")
                else:
                    st.success("Pricing item added.")
                st.rerun()
            st.error(err)
    with b2:
        if st.button("Cancel", key=k("cancel"), use_container_width=True):
            st.session_state.pop(fk, None)
            st.rerun()
    _close_compact_form_card()


def _render_add_labor_form(
    eid: str,
    est: dict[str, Any],
    *,
    key_prefix: str = "ecb_lab",
    form_state_key: str | None = None,
) -> None:
    fk = form_state_key or f"ecb_form_lab_{eid}"
    k = lambda field: _line_form_key(key_prefix, eid, field)  # noqa: E731
    default_markup = float(est.get("default_labor_markup_pct") or 0)
    labor_options = labor_options_as_select()
    lab_map = {label: opt for label, opt in labor_options}
    role_labels = [label for label, _ in labor_options] or list(LABOR_ROLE_TYPES)

    _compact_form_card("Add Labor")
    c1, c2 = st.columns(2, gap="small")
    with c1:
        role = st.selectbox("Labor role", role_labels, key=k("role"))
        opt = _sync_labor_role_state(k, role, lab_map)
        st_h = st.number_input("ST hours", min_value=0.0, value=0.0, key=k("sth"), step=0.5)
        ot_h = st.number_input("OT hours", min_value=0.0, value=0.0, key=k("oth"), step=0.5)
        markup = st.number_input("Markup %", value=default_markup, key=k("mk"))

    with c2:
        override = st.checkbox("Override labor rates", key=k("ovr"))
        if override:
            st_r = st.number_input("ST rate", min_value=0.0, value=float(opt.get("st_rate") or 0), key=k("str"))
            ot_r = st.number_input("OT rate", min_value=0.0, value=float(opt.get("ot_rate") or 0), key=k("otr"))
        else:
            st_r = float(opt.get("st_rate") or st.session_state.get(k("str")) or 0)
            ot_r = float(opt.get("ot_rate") or st.session_state.get(k("otr")) or 0)
            _display_field("ST Rate", fmt_currency(st_r))
            _display_field("OT Rate", fmt_currency(ot_r))

        totals = labor_line_totals(st_h, ot_h, st_r, ot_r, markup)
        _live_totals_card(
            [
                ("Cost Total", fmt_currency(totals["cost_total"])),
                ("Markup Amount", fmt_currency(totals["markup_amount"])),
                ("Customer Price", fmt_currency(totals["price_total"])),
            ]
        )

    notes = st.text_area("Notes", key=k("notes"), height=56, placeholder="Notes (optional)")
    if st.button("Save Labor", key=k("save"), type="primary", use_container_width=True):
        description = st.session_state.get(k("desc")) or role
        ok, err = _service_ok(
            add_estimate_labor(
                eid,
                {
                    "labor_type": role,
                    "role_name": role,
                    "description": description,
                    "st_hours": st_h,
                    "ot_hours": ot_h,
                    "st_rate": st_r,
                    "ot_rate": ot_r,
                    "markup_percent": markup,
                    "notes": notes,
                },
            )
        )
        if ok:
            st.session_state.pop(fk, None)
            st.success("Labor line added.")
            st.rerun()
        st.error(err)
    if st.button("Cancel", key=k("cancel"), use_container_width=True):
        st.session_state.pop(fk, None)
        st.rerun()
    _close_compact_form_card()


def _render_add_equipment_form(
    eid: str,
    est: dict[str, Any],
    asset_options: list[tuple[str, dict[str, Any]]],
    *,
    key_prefix: str = "ecb_eq",
    form_state_key: str | None = None,
) -> None:
    fk = form_state_key or f"ecb_form_eq_{eid}"
    k = lambda field: _line_form_key(key_prefix, eid, field)  # noqa: E731
    default_markup = float(est.get("default_equipment_markup_pct") or 0)
    asset_map = {label: asset for label, asset in asset_options}
    labels = [label for label, _ in asset_options]

    _compact_form_card("Add Equipment")
    c1, c2 = st.columns(2, gap="small")
    with c1:
        if asset_options:
            pick = st.selectbox("Equipment / Asset", labels, key=k("asset"))
        else:
            pick = None
            st.info("No rentable assets available. Mark assets as Rentable on the Assets page.")

        dur_unit_seed = str(st.session_state.get(k("dunit")) or "Days")
        if dur_unit_seed not in DURATION_UNITS:
            dur_unit_seed = "Days"
        asset: dict[str, Any] = {}
        if pick:
            asset = _sync_asset_pick_state(k, pick, asset_map, dur_unit_seed)

        dur_unit = st.selectbox("Duration unit", DURATION_UNITS, key=k("dunit"))

        if pick:
            asset = asset_map.get(pick, asset)
            dur_last = k("last_dunit")
            if st.session_state.get(dur_last) != dur_unit:
                st.session_state[k("rate")] = resolve_equipment_cost_rate(asset, dur_unit)
                st.session_state[dur_last] = dur_unit
        duration = st.number_input("Duration", min_value=0.0, value=1.0, key=k("dur"), step=0.5)
        qty = st.number_input("Quantity", min_value=0.0, value=1.0, key=k("qty"), step=1.0)
        markup = st.number_input("Markup %", value=default_markup, key=k("mk"))

    with c2:
        override = st.checkbox("Override equipment rate", key=k("ovr"), disabled=not asset_options)
        preset_rate = resolve_equipment_cost_rate(asset, dur_unit)
        if override or not asset_options:
            cost_rate = st.number_input(
                "Cost rate",
                min_value=0.0,
                value=float(st.session_state.get(k("rate"), preset_rate)),
                key=k("rate"),
            )
        else:
            cost_rate = float(st.session_state.get(k("rate"), preset_rate) or preset_rate)
            _display_field("Cost Rate", fmt_currency(cost_rate))
            if cost_rate <= 0:
                st.warning("No equipment rate found. Add a rate to the asset or enable rate override.")

        totals = equipment_line_totals(qty, duration, cost_rate, markup)
        _live_totals_card(
            [
                ("Cost Total", fmt_currency(totals["cost_total"])),
                ("Markup Amount", fmt_currency(totals["markup_amount"])),
                ("Customer Price", fmt_currency(totals["price_total"])),
            ]
        )

    with st.expander("Advanced equipment details", expanded=False):
        st.markdown('<div class="ips-estimate-advanced-details">', unsafe_allow_html=True)
        st.text_input("Equipment name", key=k("name"))
        st.text_input("Type / category", key=k("type"))
        st.markdown("</div>", unsafe_allow_html=True)

    notes = st.text_area("Notes", key=k("notes"), height=56, placeholder="Notes (optional)")
    if st.button("Save Equipment", key=k("save"), type="primary", use_container_width=True):
        asset_id = str(asset.get("id") or "") if pick else ""
        if override or not asset_options:
            cost_rate_save = float(st.session_state.get(k("rate")) or 0)
        else:
            cost_rate_save = float(preset_rate or 0)
        ok, err = _service_ok(
            add_estimate_equipment(
                eid,
                {
                    "asset_id": asset_id or None,
                    "equipment_name": st.session_state.get(k("name")) or asset.get("asset_name"),
                    "equipment_type": st.session_state.get(k("type")) or asset.get("category"),
                    "quantity": qty,
                    "duration": duration,
                    "duration_unit": dur_unit,
                    "cost_rate": cost_rate_save,
                    "markup_percent": markup,
                    "notes": notes,
                },
            )
        )
        if ok:
            st.session_state.pop(fk, None)
            st.success("Equipment line added.")
            st.rerun()
        st.error(err)
    if st.button("Cancel", key=k("cancel"), use_container_width=True):
        st.session_state.pop(fk, None)
        st.rerun()
    _close_compact_form_card()


def _render_add_subcontractor_form(
    eid: str,
    est: dict[str, Any],
    vendor_options: list[str],
    *,
    key_prefix: str = "ecb_sub",
    form_state_key: str | None = None,
) -> None:
    fk = form_state_key or f"ecb_form_sub_{eid}"
    k = lambda field: _line_form_key(key_prefix, eid, field)  # noqa: E731
    default_markup = float(est.get("default_subcontractor_markup_pct") or 0)

    _compact_form_card("Add Subcontractor")
    c1, c2 = st.columns(2, gap="small")
    with c1:
        if vendor_options:
            vendor = st.selectbox("Vendor", vendor_options, key=k("vendor"))
        else:
            vendor = st.text_input("Subcontractor", key=k("vendor"))
        description = st.text_input("Scope / description", key=k("desc"))
        cost = st.number_input("Cost", min_value=0.0, value=0.0, key=k("cost"))
        markup = st.number_input("Markup %", value=default_markup, key=k("mk"))
    with c2:
        totals = simple_line_totals(cost, markup)
        _live_totals_card(
            [
                ("Cost Total", fmt_currency(totals["cost_total"])),
                ("Markup Amount", fmt_currency(totals["markup_amount"])),
                ("Customer Price", fmt_currency(totals["price_total"])),
            ]
        )
    notes = st.text_area("Notes", key=k("notes"), height=56, placeholder="Notes (optional)")
    if st.button("Save Subcontractor", key=k("save"), type="primary", use_container_width=True):
        ok, err = _service_ok(
            add_estimate_subcontractor(
                eid,
                {
                    "subcontractor_name": vendor,
                    "description": description,
                    "cost_total": cost,
                    "markup_percent": markup,
                    "notes": notes,
                },
            )
        )
        if ok:
            st.session_state.pop(fk, None)
            st.success("Subcontractor line added.")
            st.rerun()
        st.error(err)
    if st.button("Cancel", key=k("cancel"), use_container_width=True):
        st.session_state.pop(fk, None)
        st.rerun()
    _close_compact_form_card()


def _render_add_other_form(
    eid: str,
    est: dict[str, Any],
    *,
    key_prefix: str = "ecb_oth",
    form_state_key: str | None = None,
) -> None:
    fk = form_state_key or f"ecb_form_other_{eid}"
    k = lambda field: _line_form_key(key_prefix, eid, field)  # noqa: E731
    default_markup = float(est.get("default_other_markup_pct") or 0)

    _compact_form_card("Add Other Cost")
    c1, c2 = st.columns(2, gap="small")
    with c1:
        description = st.text_input("Description", key=k("desc"))
        cost = st.number_input("Cost", min_value=0.0, value=0.0, key=k("cost"))
        markup = st.number_input("Markup %", value=default_markup, key=k("mk"))
        taxable = st.checkbox("Taxable", value=False, key=k("tax"))
    with c2:
        totals = simple_line_totals(cost, markup)
        _live_totals_card(
            [
                ("Cost Total", fmt_currency(totals["cost_total"])),
                ("Markup Amount", fmt_currency(totals["markup_amount"])),
                ("Customer Price", fmt_currency(totals["price_total"])),
            ]
        )
    with st.expander("Advanced details", expanded=False):
        st.text_input("Category", key=k("cat"))
    notes = st.text_area("Notes", key=k("notes"), height=56, placeholder="Notes (optional)")
    if st.button("Save Other Cost", key=k("save"), type="primary", use_container_width=True):
        ok, err = _service_ok(
            add_estimate_other_cost(
                eid,
                {
                    "description": description,
                    "category": st.session_state.get(k("cat")),
                    "cost_total": cost,
                    "markup_percent": markup,
                    "taxable": taxable,
                    "notes": notes,
                },
            )
        )
        if ok:
            st.session_state.pop(fk, None)
            st.success("Other cost added.")
            st.rerun()
        st.error(err)
    if st.button("Cancel", key=k("cancel"), use_container_width=True):
        st.session_state.pop(fk, None)
        st.rerun()
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


def _render_add_travel_form(
    eid: str,
    est: dict[str, Any],
    *,
    key_prefix: str = "ecb_trv",
    form_state_key: str | None = None,
) -> None:
    fk = form_state_key or f"ecb_form_trv_{eid}"
    k = lambda field: _line_form_key(key_prefix, eid, field)  # noqa: E731
    default_markup = float(est.get("default_travel_markup_pct") or 0)
    if k("mk") not in st.session_state:
        st.session_state[k("mk")] = default_markup
    _seed_travel_rate_defaults(k)
    defaults = travel_defaults()

    _compact_form_card("Add Travel Cost")
    travel_type = st.selectbox("Travel type", TRAVEL_TYPES, key=k("type"))
    c1, c2 = st.columns(2, gap="small")
    with c1:
        if travel_type == "Mileage":
            st.number_input("Miles", min_value=0.0, value=0.0, key=k("miles"), step=1.0)
            st.number_input("Trips", min_value=0.0, value=1.0, key=k("trips"), step=1.0)
            _display_field("Mileage rate", fmt_currency(st.session_state.get(k("mrate"), defaults["mileage_rate"])))
        elif travel_type == "Drive Time":
            st.number_input("Travel hours", min_value=0.0, value=0.0, key=k("hours"), step=0.5)
            st.number_input("People", min_value=0.0, value=1.0, key=k("people"), step=1.0)
            _display_field("Hourly rate", fmt_currency(st.session_state.get(k("hrate"), defaults["hourly_travel_rate"])))
        elif travel_type == "Lodging":
            st.number_input("Nights", min_value=0.0, value=0.0, key=k("nights"), step=1.0)
            st.number_input("People", min_value=0.0, value=1.0, key=k("people"), step=1.0)
            _display_field("Lodging rate", fmt_currency(st.session_state.get(k("lrate"), defaults["lodging_rate"])))
        elif travel_type == "Per Diem":
            st.number_input("Per diem days", min_value=0.0, value=0.0, key=k("pdays"), step=1.0)
            st.number_input("People", min_value=0.0, value=1.0, key=k("people"), step=1.0)
            _display_field("Per diem rate", fmt_currency(st.session_state.get(k("prate"), defaults["per_diem_rate"])))
        elif travel_type == "Airfare":
            st.number_input("Airfare cost", min_value=0.0, value=0.0, key=k("air"))
            st.number_input("People", min_value=0.0, value=1.0, key=k("people"), step=1.0)
        elif travel_type == "Rental Vehicle":
            st.number_input("Rental vehicle cost", min_value=0.0, value=0.0, key=k("rental"))
        elif travel_type == "Fuel":
            st.number_input("Fuel cost", min_value=0.0, value=0.0, key=k("fuel"))
        elif travel_type == "Parking / Tolls":
            st.number_input("Parking / tolls cost", min_value=0.0, value=0.0, key=k("park"))
        else:
            st.number_input("Other travel cost", min_value=0.0, value=0.0, key=k("other"))
        markup = st.number_input("Markup %", value=float(st.session_state.get(k("mk"), default_markup)), key=k("mk"))

    with c2:
        calc = calc_travel_line(_travel_form_data(eid, key_prefix=key_prefix))
        _live_totals_card(
            [
                ("Cost Total", fmt_currency(calc["cost_total"])),
                ("Markup Amount", fmt_currency(calc["markup_amount"])),
                ("Customer Price", fmt_currency(calc["price_total"])),
            ]
        )
        st.checkbox("Taxable", value=False, key=k("tax"))

    with st.expander("Advanced travel details", expanded=False):
        st.markdown('<div class="ips-estimate-advanced-details">', unsafe_allow_html=True)
        st.text_input("Description", key=k("desc"))
        st.text_input("Origin", key=k("origin"))
        st.text_input("Destination", key=k("dest"))
        override = st.checkbox("Override travel rates", key=k("ovr"))
        if override:
            st.number_input("Mileage rate", min_value=0.0, value=float(defaults["mileage_rate"]), key=k("mrate"))
            st.number_input("Hourly rate", min_value=0.0, value=float(defaults["hourly_travel_rate"]), key=k("hrate"))
            st.number_input("Lodging rate", min_value=0.0, value=float(defaults["lodging_rate"]), key=k("lrate"))
            st.number_input("Per diem rate", min_value=0.0, value=float(defaults["per_diem_rate"]), key=k("prate"))
        st.markdown("</div>", unsafe_allow_html=True)

    notes = st.text_area("Notes", key=k("notes"), height=56, placeholder="Notes (optional)")
    b1, b2 = st.columns(2, gap="small")
    with b1:
        if st.button("Save Travel Cost", key=k("save"), type="primary", use_container_width=True):
            ok, err = _service_ok(add_estimate_travel(eid, _travel_form_data(eid, key_prefix=key_prefix)))
            if ok:
                st.session_state.pop(fk, None)
                st.success("Travel cost added.")
                st.rerun()
            st.error(err)
    with b2:
        if st.button("Cancel", key=k("cancel"), use_container_width=True):
            st.session_state.pop(fk, None)
            st.rerun()
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
    _render_deletable_lines(
        eid,
        ["Role", "ST/OT", "Cost", "Price"],
        bundle["labor"],
        row_cells=lambda r: [
            html.escape(str(r.get("role_name") or "—")),
            html.escape(f"{r.get('st_hours',0)}/{r.get('ot_hours',0)}"),
            html.escape(fmt_currency(r.get("cost_total"))),
            html.escape(fmt_currency(r.get("price_total"))),
        ],
        delete_fn=delete_estimate_labor,
        key_prefix="ecb_lab",
    )

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

    if st.button("+ Add Travel Cost", key=f"trv_tab_add_{eid}"):
        st.session_state[f"trv_tab_form_{eid}"] = True
        st.rerun()

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
                    ["Type", "Description", "Origin", "Destination", "Qty / Basis", "Cost", "Markup %", "Customer Price", "Taxable"],
                    [cells],
                )
            with c_del:
                if st.button("✕", key=f"trv_tab_del_{rid}", help="Delete travel line"):
                    ok, err = _service_ok(delete_estimate_travel(rid, estimate_id=eid))
                    if ok:
                        st.rerun()
                    st.error(err)

    if st.session_state.get(f"trv_tab_form_{eid}"):
        _render_add_travel_form(
            eid,
            est,
            key_prefix="trv_tab",
            form_state_key=f"trv_tab_form_{eid}",
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


def render_materials_tab(
    est: dict[str, Any],
    *,
    pricing_guide_options: list[tuple[str, dict[str, Any]]] | None = None,
    inventory_options: list[tuple[str, dict[str, Any]]] | None = None,
) -> None:
    eid = str(est.get("id") or "")
    bundle = get_estimate_bundle(eid)
    rows = bundle["materials"]
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
    if st.button("+ Add Pricing Item", key=f"mat_tab_add_{eid}"):
        st.session_state[f"mat_tab_form_{eid}"] = True
        st.rerun()
    if st.session_state.get(f"mat_tab_form_{eid}"):
        _render_add_material_form(
            eid,
            est,
            pricing_guide_options=pricing_guide_options,
            inventory_options=inventory_options,
            key_prefix="mat_tab",
            form_state_key=f"mat_tab_form_{eid}",
        )


def render_labor_tab(est: dict[str, Any]) -> None:
    eid = str(est.get("id") or "")
    bundle = get_estimate_bundle(eid)
    _render_deletable_lines(
        eid,
        ["Role", "ST/OT", "Cost", "Price"],
        bundle["labor"],
        row_cells=lambda r: [
            html.escape(str(r.get("role_name") or "—")),
            html.escape(f"{r.get('st_hours',0)}/{r.get('ot_hours',0)}"),
            html.escape(fmt_currency(r.get("cost_total"))),
            html.escape(fmt_currency(r.get("price_total"))),
        ],
        delete_fn=delete_estimate_labor,
        key_prefix="lab_tab",
    )
    if st.button("+ Add Labor", key=f"lab_tab_add_{eid}"):
        st.session_state[f"lab_tab_form_{eid}"] = True
        st.rerun()
    if st.session_state.get(f"lab_tab_form_{eid}"):
        _render_add_labor_form(
            eid,
            est,
            key_prefix="lab_tab",
            form_state_key=f"lab_tab_form_{eid}",
        )


def render_equipment_tab(est: dict[str, Any], *, asset_options: list[tuple[str, dict[str, Any]]] | None = None) -> None:
    eid = str(est.get("id") or "")
    bundle = get_estimate_bundle(eid)
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
        key_prefix="eq_tab",
    )
    if st.button("+ Add Equipment", key=f"eq_tab_add_{eid}"):
        st.session_state[f"eq_tab_form_{eid}"] = True
        st.rerun()
    if st.session_state.get(f"eq_tab_form_{eid}"):
        _render_add_equipment_form(
            eid,
            est,
            asset_options or [],
            key_prefix="eq_tab",
            form_state_key=f"eq_tab_form_{eid}",
        )


def render_subcontractors_tab(est: dict[str, Any], *, vendor_options: list[str] | None = None) -> None:
    eid = str(est.get("id") or "")
    bundle = get_estimate_bundle(eid)
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
        key_prefix="sub_tab",
    )
    if st.button("+ Add Subcontractor", key=f"sub_tab_add_{eid}"):
        st.session_state[f"sub_tab_form_{eid}"] = True
        st.rerun()
    if st.session_state.get(f"sub_tab_form_{eid}"):
        _render_add_subcontractor_form(
            eid,
            est,
            vendor_options or [],
            key_prefix="sub_tab",
            form_state_key=f"sub_tab_form_{eid}",
        )


def render_other_costs_tab(est: dict[str, Any]) -> None:
    eid = str(est.get("id") or "")
    bundle = get_estimate_bundle(eid)
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
        key_prefix="oth_tab",
    )
    if st.button("+ Add Other Cost", key=f"oth_tab_add_{eid}"):
        st.session_state[f"oth_tab_form_{eid}"] = True
        st.rerun()
    if st.session_state.get(f"oth_tab_form_{eid}"):
        _render_add_other_form(
            eid,
            est,
            key_prefix="oth_tab",
            form_state_key=f"oth_tab_form_{eid}",
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
        "Keep the **Project** name short on Overview (for example, Orange Turnaround Extra Work)."
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


def render_markups_tab(est: dict[str, Any], *, persist_fn: Callable[[dict[str, Any], str], tuple[bool, str]]) -> None:
    eid = str(est.get("id") or "")
    st.markdown("##### Default markups for new lines")
    c1, c2 = st.columns(2)
    with c1:
        mat_mk = st.number_input("Material markup %", value=float(est.get("default_material_markup_pct") or 0), key=f"mk_mat_{eid}")
        lab_mk = st.number_input("Labor markup %", value=float(est.get("default_labor_markup_pct") or 0), key=f"mk_lab_{eid}")
        eq_mk = st.number_input("Equipment markup %", value=float(est.get("default_equipment_markup_pct") or 0), key=f"mk_eq_{eid}")
        trv_mk = st.number_input("Travel markup %", value=float(est.get("default_travel_markup_pct") or 0), key=f"mk_trv_{eid}")
    with c2:
        sub_mk = st.number_input("Subcontractor markup %", value=float(est.get("default_subcontractor_markup_pct") or 0), key=f"mk_sub_{eid}")
        oth_mk = st.number_input("Other markup %", value=float(est.get("default_other_markup_pct") or 0), key=f"mk_oth_{eid}")
        tax_rate = st.number_input("Tax rate %", value=float(est.get("tax_rate") or 0), key=f"mk_tax_{eid}")
    global_mk = st.number_input("Global markup %", value=float(est.get("global_markup_pct") or 0), key=f"mk_global_{eid}")
    overhead = st.number_input("Overhead %", value=float(est.get("overhead_pct") or 0), key=f"mk_oh_{eid}")
    profit = st.number_input("Profit %", value=float(est.get("profit_pct") or 0), key=f"mk_profit_{eid}")

    if st.button("Save markup settings", key=f"mk_save_{eid}", type="primary"):
        ok, msg = persist_fn(
            {
                "default_material_markup_pct": mat_mk,
                "default_labor_markup_pct": lab_mk,
                "default_equipment_markup_pct": eq_mk,
                "default_travel_markup_pct": trv_mk,
                "default_subcontractor_markup_pct": sub_mk,
                "default_other_markup_pct": oth_mk,
                "global_markup_pct": global_mk,
                "overhead_pct": overhead,
                "profit_pct": profit,
                "tax_rate": tax_rate,
            },
            eid,
        )
        if ok:
            recalculate_and_save_estimate_totals(eid)
            st.success(msg or "Markup settings saved.")
            st.rerun()
        st.error(msg or "Could not save markup settings.")


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
    eid = str(est.get("id") or "")
    totals = calculate_estimate_totals(eid) if eid and not is_demo_id(eid) else {}
    try:
        from app.services.proposal_pdf_service import merge_proposal_totals
    except ImportError:
        from services.proposal_pdf_service import merge_proposal_totals  # type: ignore
    totals = merge_proposal_totals(totals, est)

    preview_fields = [
        detail_field_html("Estimate #", est.get("estimate_number")),
        detail_field_html("Customer", est.get("customer")),
        detail_field_html("Project", est.get("project_name")),
        detail_field_html("Valid through", fmt_date(est.get("expiration_date"))),
    ]
    travel_price = float(totals.get("travel_price") or 0)
    if travel_price > 0:
        preview_fields.append(detail_field_html("Travel (customer)", fmt_currency(travel_price)))
    preview_fields.append(detail_field_html("Proposal total", fmt_currency(totals.get("proposal_total"))))
    st.markdown(
        dialog_card_html(
            "Customer Quote",
            f'<div class="ips-detail-grid">{"".join(preview_fields)}</div>',
        ),
        unsafe_allow_html=True,
    )

    if is_demo_id(eid):
        st.info("Save estimate to Supabase to preview and download the customer quote.")
        return

    try:
        docx_bytes, pdf_bytes, page_html, word_err, pdf_note = build_customer_quote_bundle(eid, est, totals=totals)
    except Exception as exc:
        st.error(f"Could not build customer quote: {exc}")
        return

    if word_err:
        st.error(word_err)
        return

    try:
        from app.estimate.proposal_exports import _inject_proposal_preview_styles
    except ImportError:
        from estimate.proposal_exports import _inject_proposal_preview_styles  # type: ignore

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
        try:
            from app.pages._core._data import persist_estimate, get_estimate as _get_est
        except ImportError:
            from pages._core._data import persist_estimate, get_estimate as _get_est  # type: ignore
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
