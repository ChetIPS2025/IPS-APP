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
    from app.services.proposal_pdf_service import generate_estimate_proposal_pdf_by_id
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
    from services.proposal_pdf_service import generate_estimate_proposal_pdf_by_id  # type: ignore
    from utils.estimate_calculations import margin_warning_class  # type: ignore
    from utils.formatting import fmt_currency, fmt_date  # type: ignore


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


def render_cost_builder_tab(
    est: dict[str, Any],
    *,
    inventory_options: list[tuple[str, dict[str, Any]]] | None = None,
    asset_options: list[tuple[str, dict[str, Any]]] | None = None,
    vendor_options: list[str] | None = None,
    on_saved: Callable[[], None] | None = None,
) -> None:
    eid = str(est.get("id") or "")
    if is_demo_id(eid):
        st.info("Save this estimate to Supabase before building costs.")
        return

    bundle = get_estimate_bundle(eid)
    totals = calculate_estimate_totals(eid)
    render_cost_summary_cards(est, totals)

    qa1, qa2, qa3, qa4, qa5, qa6 = st.columns(6, gap="small")
    with qa1:
        add_mat = st.button("+ Material", key=f"ecb_add_mat_{eid}", use_container_width=True)
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

    if st.button("Recalculate Totals", key=f"ecb_recalc_{eid}", type="primary"):
        ok, err = _service_ok(recalculate_and_save_estimate_totals(eid))
        if ok:
            st.success("Totals updated.")
            if on_saved:
                on_saved()
            st.rerun()
        else:
            st.error(err)

    st.markdown("#### Recent Lines")
    preview_rows: list[list[str]] = []
    for row in bundle["materials"][:3]:
        preview_rows.append(["Material", row.get("description", ""), fmt_currency(row.get("price_total"))])
    for row in bundle["labor"][:2]:
        preview_rows.append(["Labor", row.get("role_name", ""), fmt_currency(row.get("price_total"))])
    for row in bundle["equipment"][:2]:
        preview_rows.append(["Equipment", row.get("equipment_name", ""), fmt_currency(row.get("price_total"))])
    for row in bundle.get("travel", [])[:2]:
        preview_rows.append(["Travel", row.get("description") or row.get("travel_type", ""), fmt_currency(row.get("price_total"))])
    _line_table(["Type", "Description", "Price"], preview_rows)

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
            inventory_options or [],
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


def _render_add_material_form(
    eid: str,
    est: dict[str, Any],
    inventory_options: list[tuple[str, dict[str, Any]]],
    *,
    key_prefix: str = "ecb_mat",
    form_state_key: str | None = None,
) -> None:
    fk = form_state_key or f"ecb_form_mat_{eid}"
    k = lambda field: _line_form_key(key_prefix, eid, field)  # noqa: E731
    st.markdown("##### Add Material")
    source = st.radio("Source", ["Inventory", "Custom"], horizontal=True, key=k("src"))
    default_markup = float(est.get("default_material_markup_pct") or 0)
    inv_map = {label: item for label, item in inventory_options}
    c1, c2 = st.columns(2)
    with c1:
        if source == "Inventory" and inventory_options:
            labels = [label for label, _ in inventory_options]
            pick = st.selectbox("Inventory item", labels, key=k("inv"))
            item = inv_map.get(pick, {})
            description = st.text_input("Description", value=str(item.get("name") or ""), key=k("desc"))
            sku = st.text_input("SKU", value=str(item.get("sku") or ""), key=k("sku"))
            category = st.text_input("Category", value=str(item.get("category") or ""), key=k("cat"))
            unit = st.text_input("Unit", value="EA", key=k("unit"))
            unit_cost = st.number_input("Unit cost", value=float(item.get("unit_cost") or 0), key=k("uc"))
            vendor = st.text_input("Vendor", value=str(item.get("vendor") or ""), key=k("vendor"))
            inv_id = str(item.get("id") or "")
        else:
            description = st.text_input("Description", key=k("desc"))
            sku = st.text_input("SKU / Item #", key=k("sku"))
            category = st.text_input("Category", key=k("cat"))
            unit = st.text_input("Unit", value="EA", key=k("unit"))
            unit_cost = st.number_input("Unit cost", value=0.0, key=k("uc"))
            vendor = st.text_input("Vendor", key=k("vendor"))
            inv_id = ""
    with c2:
        qty = st.number_input("Quantity", min_value=0.0, value=1.0, key=k("qty"))
        markup = st.number_input("Markup %", value=default_markup, key=k("mk"))
        taxable = st.checkbox("Taxable", value=True, key=k("tax"))
        notes = st.text_area("Notes", key=k("notes"), height=70)
    b1, b2 = st.columns(2)
    with b1:
        if st.button("Save material", key=k("save"), type="primary", use_container_width=True):
            ok, err = _service_ok(
                add_estimate_material(
                    eid,
                    {
                        "inventory_item_id": inv_id or None,
                        "sku": st.session_state.get(k("sku")),
                        "description": st.session_state.get(k("desc")),
                        "category": st.session_state.get(k("cat")),
                        "unit": st.session_state.get(k("unit")),
                        "unit_cost": st.session_state.get(k("uc")),
                        "quantity": qty,
                        "markup_percent": markup,
                        "taxable": taxable,
                        "vendor": st.session_state.get(k("vendor")),
                        "notes": notes,
                    },
                )
            )
            if ok:
                st.session_state.pop(fk, None)
                st.success("Material added.")
                st.rerun()
            st.error(err)
    with b2:
        if st.button("Cancel", key=k("cancel"), use_container_width=True):
            st.session_state.pop(fk, None)
            st.rerun()


def _render_add_labor_form(
    eid: str,
    est: dict[str, Any],
    *,
    key_prefix: str = "ecb_lab",
    form_state_key: str | None = None,
) -> None:
    fk = form_state_key or f"ecb_form_lab_{eid}"
    k = lambda field: _line_form_key(key_prefix, eid, field)  # noqa: E731
    st.markdown("##### Add Labor")
    default_markup = float(est.get("default_labor_markup_pct") or 0)
    c1, c2 = st.columns(2)
    with c1:
        role = st.selectbox("Labor role", LABOR_ROLE_TYPES, key=k("role"))
        description = st.text_input("Description", key=k("desc"))
        st_h = st.number_input("ST hours", min_value=0.0, value=0.0, key=k("sth"))
        ot_h = st.number_input("OT hours", min_value=0.0, value=0.0, key=k("oth"))
        dt_h = st.number_input("DT hours", min_value=0.0, value=0.0, key=k("dth"))
    with c2:
        st_r = st.number_input("ST rate", min_value=0.0, value=0.0, key=k("str"))
        ot_r = st.number_input("OT rate", min_value=0.0, value=0.0, key=k("otr"))
        dt_r = st.number_input("DT rate", min_value=0.0, value=0.0, key=k("dtr"))
        markup = st.number_input("Markup %", value=default_markup, key=k("mk"))
        notes = st.text_area("Notes", key=k("notes"), height=70)
    if st.button("Save labor", key=k("save"), type="primary"):
        ok, err = _service_ok(
            add_estimate_labor(
                eid,
                {
                    "labor_type": role,
                    "role_name": role,
                    "description": description or role,
                    "st_hours": st_h,
                    "ot_hours": ot_h,
                    "dt_hours": dt_h,
                    "st_rate": st_r,
                    "ot_rate": ot_r,
                    "dt_rate": dt_r,
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
    st.markdown("##### Add Equipment")
    default_markup = float(est.get("default_equipment_markup_pct") or 0)
    asset_map = {label: asset for label, asset in asset_options}
    c1, c2 = st.columns(2)
    with c1:
        if asset_options:
            labels = [label for label, _ in asset_options]
            pick = st.selectbox("Asset", labels, key=k("asset"))
            asset = asset_map.get(pick, {})
            name = st.text_input("Equipment name", value=str(asset.get("asset_name") or ""), key=k("name"))
            eq_type = st.text_input("Type", value=str(asset.get("category") or ""), key=k("type"))
            asset_id = str(asset.get("id") or "")
        else:
            name = st.text_input("Equipment name", key=k("name"))
            eq_type = st.text_input("Type", key=k("type"))
            asset_id = ""
        qty = st.number_input("Quantity", min_value=0.0, value=1.0, key=k("qty"))
        duration = st.number_input("Duration", min_value=0.0, value=0.0, key=k("dur"))
        dur_unit = st.selectbox("Duration unit", DURATION_UNITS, key=k("dunit"))
    with c2:
        cost_rate = st.number_input("Cost rate", min_value=0.0, value=0.0, key=k("rate"))
        markup = st.number_input("Markup %", value=default_markup, key=k("mk"))
        notes = st.text_area("Notes", key=k("notes"), height=70)
    if st.button("Save equipment", key=k("save"), type="primary"):
        ok, err = _service_ok(
            add_estimate_equipment(
                eid,
                {
                    "asset_id": asset_id or None,
                    "equipment_name": name,
                    "equipment_type": eq_type,
                    "quantity": qty,
                    "duration": duration,
                    "duration_unit": dur_unit,
                    "cost_rate": cost_rate,
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
    st.markdown("##### Add Subcontractor")
    default_markup = float(est.get("default_subcontractor_markup_pct") or 0)
    c1, c2 = st.columns(2)
    with c1:
        if vendor_options:
            vendor = st.selectbox("Vendor", vendor_options, key=k("vendor"))
        else:
            vendor = st.text_input("Subcontractor", key=k("vendor"))
        description = st.text_area("Scope / description", key=k("desc"), height=80)
    with c2:
        cost = st.number_input("Cost", min_value=0.0, value=0.0, key=k("cost"))
        markup = st.number_input("Markup %", value=default_markup, key=k("mk"))
        notes = st.text_area("Notes", key=k("notes"), height=80)
    if st.button("Save subcontractor", key=k("save"), type="primary"):
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


def _render_add_other_form(
    eid: str,
    est: dict[str, Any],
    *,
    key_prefix: str = "ecb_oth",
    form_state_key: str | None = None,
) -> None:
    fk = form_state_key or f"ecb_form_other_{eid}"
    k = lambda field: _line_form_key(key_prefix, eid, field)  # noqa: E731
    st.markdown("##### Add Other Cost")
    default_markup = float(est.get("default_other_markup_pct") or 0)
    c1, c2 = st.columns(2)
    with c1:
        description = st.text_input("Description", key=k("desc"))
        category = st.text_input("Category", key=k("cat"))
        cost = st.number_input("Cost", min_value=0.0, value=0.0, key=k("cost"))
    with c2:
        markup = st.number_input("Markup %", value=default_markup, key=k("mk"))
        taxable = st.checkbox("Taxable", value=False, key=k("tax"))
        notes = st.text_area("Notes", key=k("notes"), height=80)
    if st.button("Save other cost", key=k("save"), type="primary"):
        ok, err = _service_ok(
            add_estimate_other_cost(
                eid,
                {
                    "description": description,
                    "category": category,
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


def _render_add_travel_form(
    eid: str,
    est: dict[str, Any],
    *,
    key_prefix: str = "ecb_trv",
    form_state_key: str | None = None,
) -> None:
    fk = form_state_key or f"ecb_form_trv_{eid}"
    k = lambda field: _line_form_key(key_prefix, eid, field)  # noqa: E731
    st.markdown("##### Add Travel Cost")
    default_markup = float(est.get("default_travel_markup_pct") or 0)
    if k("mk") not in st.session_state:
        st.session_state[k("mk")] = default_markup
    travel_type = st.selectbox("Travel type", TRAVEL_TYPES, key=k("type"))
    c1, c2 = st.columns(2)
    with c1:
        st.text_input("Description", key=k("desc"))
        if travel_type in ("Mileage", "Drive Time", "Airfare"):
            st.text_input("Origin", key=k("origin"))
        if travel_type in ("Mileage", "Drive Time", "Lodging", "Per Diem", "Airfare"):
            st.text_input("Destination", key=k("dest"))
        if travel_type == "Mileage":
            st.number_input("Miles", min_value=0.0, value=0.0, key=k("miles"))
            st.number_input("Mileage rate", min_value=0.0, value=0.0, key=k("mrate"))
            st.number_input("Trips", min_value=0.0, value=1.0, key=k("trips"))
        elif travel_type == "Drive Time":
            st.number_input("Travel hours", min_value=0.0, value=0.0, key=k("hours"))
            st.number_input("Hourly rate", min_value=0.0, value=0.0, key=k("hrate"))
            st.number_input("People", min_value=0.0, value=1.0, key=k("people"))
        elif travel_type == "Lodging":
            st.number_input("Nights", min_value=0.0, value=0.0, key=k("nights"))
            st.number_input("Lodging rate", min_value=0.0, value=0.0, key=k("lrate"))
            st.number_input("People", min_value=0.0, value=1.0, key=k("people"))
        elif travel_type == "Per Diem":
            st.number_input("Per diem days", min_value=0.0, value=0.0, key=k("pdays"))
            st.number_input("Per diem rate", min_value=0.0, value=0.0, key=k("prate"))
            st.number_input("People", min_value=0.0, value=1.0, key=k("people"))
        elif travel_type == "Airfare":
            st.number_input("Airfare cost", min_value=0.0, value=0.0, key=k("air"))
            st.number_input("People", min_value=0.0, value=1.0, key=k("people"))
        elif travel_type == "Rental Vehicle":
            st.number_input("Rental vehicle cost", min_value=0.0, value=0.0, key=k("rental"))
        elif travel_type == "Fuel":
            st.number_input("Fuel cost", min_value=0.0, value=0.0, key=k("fuel"))
        elif travel_type == "Parking / Tolls":
            st.number_input("Parking / tolls cost", min_value=0.0, value=0.0, key=k("park"))
        else:
            st.number_input("Other travel cost", min_value=0.0, value=0.0, key=k("other"))
    with c2:
        st.number_input("Markup %", value=float(st.session_state.get(k("mk"), default_markup)), key=k("mk"))
        st.checkbox("Taxable", value=False, key=k("tax"))
        st.text_area("Notes", key=k("notes"), height=120)

    calc = calc_travel_line(_travel_form_data(eid, key_prefix=key_prefix))
    st.markdown(
        f"**Cost total:** {fmt_currency(calc['cost_total'])} · "
        f"**Markup:** {fmt_currency(calc['markup_amount'])} · "
        f"**Customer price:** {fmt_currency(calc['price_total'])}"
    )

    b1, b2 = st.columns(2)
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
    if st.button("+ Add Material", key=f"mat_tab_add_{eid}"):
        st.session_state[f"mat_tab_form_{eid}"] = True
        st.rerun()
    if st.session_state.get(f"mat_tab_form_{eid}"):
        _render_add_material_form(
            eid,
            est,
            inventory_options or [],
            key_prefix="mat_tab",
            form_state_key=f"mat_tab_form_{eid}",
        )


def render_labor_tab(est: dict[str, Any]) -> None:
    eid = str(est.get("id") or "")
    bundle = get_estimate_bundle(eid)
    _render_deletable_lines(
        eid,
        ["Role", "ST/OT/DT", "Cost", "Price"],
        bundle["labor"],
        row_cells=lambda r: [
            html.escape(str(r.get("role_name") or "—")),
            html.escape(f"{r.get('st_hours',0)}/{r.get('ot_hours',0)}/{r.get('dt_hours',0)}"),
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
    c1, c2, c3 = st.columns(3)
    with c1:
        show_lines = st.checkbox("Show detailed line items", value=bool(est.get("proposal_show_line_items")), key=f"pp_lines_{eid}")
    with c2:
        show_cats = st.checkbox("Show category totals", value=est.get("proposal_show_category_totals", True), key=f"pp_cats_{eid}")
    with c3:
        final_only = st.checkbox("Show final price only", value=bool(est.get("proposal_show_final_price_only")), key=f"pp_final_{eid}")

    preview_est = {
        **est,
        "proposal_show_line_items": show_lines,
        "proposal_show_category_totals": show_cats,
        "proposal_show_final_price_only": final_only,
    }
    totals = calculate_estimate_totals(eid)
    travel_price = float(totals.get("travel_price") or 0)
    preview_fields = [
        detail_field_html("Estimate #", est.get("estimate_number")),
        detail_field_html("Customer", est.get("customer")),
        detail_field_html("Project", est.get("project_name")),
        detail_field_html("Valid through", fmt_date(est.get("expiration_date"))),
    ]
    if travel_price > 0:
        preview_fields.append(detail_field_html("Travel (customer)", fmt_currency(travel_price)))
    preview_fields.append(detail_field_html("Proposal total", fmt_currency(totals.get("customer_price"))))
    st.markdown(
        dialog_card_html(
            "Proposal Preview",
            f'<div class="ips-detail-grid">{"".join(preview_fields)}</div>',
        ),
        unsafe_allow_html=True,
    )
    scope = safe_value(est.get("description") or est.get("scope_of_work"), "No scope entered.")
    st.markdown(f"**Scope:** {html.escape(scope)}")

    if is_demo_id(eid):
        st.info("Save estimate to Supabase to download PDF.")
        return

    try:
        pdf_bytes = generate_estimate_proposal_pdf_by_id(eid, preview_est)
    except Exception as exc:
        st.error(f"Could not generate PDF preview: {exc}")
        return

    st.download_button(
        "Download Proposal PDF",
        data=pdf_bytes,
        file_name=f"{est.get('estimate_number', 'estimate')}_proposal.pdf",
        mime="application/pdf",
        key=f"pp_download_{eid}",
        type="primary",
    )
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
                "proposal_show_line_items": show_lines,
                "proposal_show_category_totals": show_cats,
                "proposal_show_final_price_only": final_only,
            },
            row_id=eid,
        )
        if ok:
            st.success(msg or "Estimate marked as Sent.")
            st.rerun()
        st.error(msg or "Could not update status.")
