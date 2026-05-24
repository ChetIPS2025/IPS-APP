"""Asset Kit / Tool Trailer UI — inline panels inside Asset Details (no nested dialogs)."""

from __future__ import annotations

import csv
import html
import io
from typing import Any

import streamlit as st

try:
    from app.components.status import status_pill_html
    from app.pages._core._data import load_assets, load_inventory, load_jobs
    from app.services.asset_kits_service import (
        CONDITIONS,
        ITEM_STATUSES,
        ITEM_TYPES,
        KIT_TYPES,
        assign_asset_kit,
        asset_is_kit,
        convert_asset_to_kit,
        create_asset_kit_audit,
        create_asset_kit_item,
        delete_asset_kit_item,
        get_asset_kit_audits,
        get_asset_kit_items,
        get_asset_kit_summary,
        get_asset_kit_transactions,
        get_missing_tools_report,
        get_overdue_kit_audits,
        get_tool_trailers,
        update_asset_kit_item,
    )
    from app.utils.formatting import fmt_currency, fmt_date
except ImportError:
    from components.status import status_pill_html  # type: ignore
    from pages._core._data import load_assets, load_inventory, load_jobs  # type: ignore
    from services.asset_kits_service import (  # type: ignore
        CONDITIONS,
        ITEM_STATUSES,
        ITEM_TYPES,
        KIT_TYPES,
        assign_asset_kit,
        asset_is_kit,
        convert_asset_to_kit,
        create_asset_kit_audit,
        create_asset_kit_item,
        delete_asset_kit_item,
        get_asset_kit_audits,
        get_asset_kit_items,
        get_asset_kit_summary,
        get_asset_kit_transactions,
        get_missing_tools_report,
        get_overdue_kit_audits,
        get_tool_trailers,
        update_asset_kit_item,
    )
    from utils.formatting import fmt_currency, fmt_date  # type: ignore

_KIT_STATUS_COLORS = {
    "present": ("#15803d", "#dcfce7"),
    "missing": ("#b91c1c", "#fee2e2"),
    "damaged": ("#c2410c", "#ffedd5"),
    "checked out": ("#1d4ed8", "#dbeafe"),
    "needs repair": ("#b45309", "#fef3c7"),
    "needs replacement": ("#c2410c", "#ffedd5"),
    "retired": ("#64748b", "#f1f5f9"),
}


def _sk(aid: str, suffix: str) -> str:
    return f"kit_{suffix}_{aid}"


def kit_item_status_pill_html(status: str) -> str:
    key = str(status or "").strip().lower()
    fg, bg = _KIT_STATUS_COLORS.get(key, ("#475569", "#f1f5f9"))
    label = html.escape(str(status or "—"))
    return (
        f'<span class="ips-kit-status-pill" style="color:{fg};background:{bg};'
        f'border:1px solid {fg}22;padding:0.12rem 0.45rem;border-radius:999px;'
        f'font-size:0.72rem;font-weight:600;">{label}</span>'
    )


def inject_kit_ui_styles() -> None:
    if st.session_state.get("_ips_kit_ui_styles"):
        return
    st.session_state["_ips_kit_ui_styles"] = True
    st.markdown(
        """
        <style>
        .ips-kit-badge {
            display: inline-block;
            margin-left: 0.35rem;
            padding: 0.08rem 0.4rem;
            border-radius: 999px;
            font-size: 0.65rem;
            font-weight: 700;
            color: #1d4ed8;
            background: #dbeafe;
            border: 1px solid #93c5fd;
            vertical-align: middle;
        }
        .ips-kit-summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(9rem, 1fr));
            gap: 0.45rem;
            margin: 0.35rem 0 0.65rem;
        }
        .ips-kit-metric {
            background: #fff;
            border: 1px solid #e5eaf2;
            border-radius: 10px;
            padding: 0.45rem 0.55rem;
        }
        .ips-kit-metric-label {
            font-size: 0.68rem;
            color: #64748b;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.02em;
        }
        .ips-kit-metric-value {
            font-size: 0.95rem;
            font-weight: 700;
            color: #0f172a;
            margin-top: 0.15rem;
        }
        .ips-kit-table-row {
            border-bottom: 1px solid #eef2f7;
            padding: 0.15rem 0;
        }
        .ips-kit-detail-panel {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 0.65rem 0.75rem;
            margin-top: 0.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def kit_badge_html() -> str:
    return '<span class="ips-kit-badge">Kit</span>'


def render_kit_accountability_summary() -> None:
    """Report cards on Assets page — supervisor accountability."""
    inject_kit_ui_styles()
    trailers = get_tool_trailers()
    if not trailers:
        return
    missing_rows = get_missing_tools_report()
    overdue = get_overdue_kit_audits(days=30)
    total_val = sum(float(a.get("total_kit_value") or a.get("value") or 0) for a in trailers)
    missing_val = sum(float(r.get("missing_value") or 0) for r in missing_rows)
    damaged_val = sum(float(r.get("damaged_value") or 0) for r in missing_rows)

    st.markdown("#### Tool Trailers & Kits")
    c1, c2, c3, c4, c5 = st.columns(5, gap="small")
    c1.metric("Kits / Trailers", len(trailers))
    c2.metric("Total Kit Value", fmt_currency(total_val))
    c3.metric("Missing Tools Value", fmt_currency(missing_val))
    c4.metric("Damaged Value", fmt_currency(damaged_val))
    c5.metric("Audit Overdue", len(overdue))

    if missing_rows:
        with st.expander("Missing / damaged by supervisor", expanded=False):
            for row in missing_rows[:15]:
                st.markdown(
                    f"**{html.escape(str(row.get('asset_name') or '—'))}** · "
                    f"Supervisor: {html.escape(str(row.get('supervisor') or '—'))} · "
                    f"Missing: {fmt_currency(row.get('missing_value'))} · "
                    f"Damaged: {fmt_currency(row.get('damaged_value'))}"
                )


def _employee_options() -> list[tuple[str, dict[str, Any]]]:
    try:
        from app.pages._core._data import load_employees
    except ImportError:
        from pages._core._data import load_employees  # type: ignore
    out: list[tuple[str, dict[str, Any]]] = [("— None —", {})]
    for e in load_employees():
        name = str(e.get("name") or "").strip()
        if name:
            out.append((name, e))
    return out


def _job_options() -> list[tuple[str, str]]:
    opts: list[tuple[str, str]] = [("— None —", "")]
    for j in load_jobs():
        label = f"{j.get('job_number') or ''} — {j.get('job_name') or ''}".strip(" —")
        jid = str(j.get("id") or "")
        if jid:
            opts.append((label or jid, jid))
    return opts


def _asset_options(exclude_id: str) -> list[tuple[str, dict[str, Any]]]:
    out: list[tuple[str, dict[str, Any]]] = [("— None —", {})]
    for a in load_assets():
        aid = str(a.get("id") or "")
        if aid == exclude_id:
            continue
        label = f"{a.get('asset_number') or ''} — {a.get('asset_name') or ''}".strip(" —")
        out.append((label or aid, a))
    return out


def _inventory_options() -> list[tuple[str, dict[str, Any]]]:
    out: list[tuple[str, dict[str, Any]]] = [("— Select inventory item —", {})]
    for row in load_inventory():
        name = str(row.get("item_name") or row.get("name") or "").strip()
        if name:
            out.append((name, row))
    return out


def _render_kit_summary_cards(asset: dict, summary: dict[str, Any]) -> None:
    cards = [
        ("Total Kit Value", fmt_currency(summary.get("total_kit_value"))),
        ("Expected Items", str(summary.get("expected_items") or 0)),
        ("Present Items", str(summary.get("present_items") or 0)),
        ("Missing Items", str(summary.get("missing_items") or 0)),
        ("Damaged Items", str(summary.get("damaged_items") or 0)),
        ("Assigned Supervisor", str(summary.get("assigned_supervisor") or "—")),
        ("Last Audit", summary.get("last_audit") or "—"),
        ("Replacement Est.", fmt_currency(summary.get("replacement_cost"))),
    ]
    parts = ['<div class="ips-kit-summary-grid">']
    for label, val in cards:
        parts.append(
            f'<div class="ips-kit-metric"><div class="ips-kit-metric-label">{html.escape(label)}</div>'
            f'<div class="ips-kit-metric-value">{html.escape(str(val))}</div></div>'
        )
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)
    kt = str(asset.get("kit_type") or "").strip()
    if kt:
        st.caption(f"Kit type: **{kt}** · Status: **{asset.get('kit_status') or 'Active'}**")


def _render_assignment_section(asset: dict, aid: str) -> None:
    st.markdown("##### Assignment / Accountability")
    emp_opts = _employee_options()
    job_opts = _job_options()
    emp_labels = [x[0] for x in emp_opts]
    job_labels = [x[0] for x in job_opts]
    cur_sup = str(asset.get("assigned_to_name") or asset.get("operator") or "")
    cur_job_id = str(asset.get("assigned_job_id") or "")

    with st.form(f"kit_assign_{aid}"):
        c1, c2 = st.columns(2)
        with c1:
            sup_idx = emp_labels.index(cur_sup) if cur_sup in emp_labels else 0
            sup_label = st.selectbox("Assigned supervisor", emp_labels, index=sup_idx)
        with c2:
            job_idx = 0
            for i, (_, jid) in enumerate(job_opts):
                if jid == cur_job_id:
                    job_idx = i
                    break
            job_label = st.selectbox("Assigned job", job_labels, index=job_idx)
        notes = st.text_area("Assignment notes", value="", height=60)
        if st.form_submit_button("Save Assignment", type="primary"):
            emp = next((e for lbl, e in emp_opts if lbl == sup_label), {})
            jid = next((j for lbl, j in job_opts if lbl == job_label), "")
            result = assign_asset_kit(
                aid,
                {
                    "assigned_to_employee_id": emp.get("id"),
                    "assigned_to_name": sup_label if sup_label != "— None —" else "",
                    "assigned_to_phone": emp.get("phone"),
                    "job_id": jid or None,
                    "notes": notes,
                },
            )
            if result.ok:
                st.success("Assignment saved.")
                st.rerun()
            else:
                st.error(result.error or "Could not save assignment.")


def _export_kit_csv(items: list[dict]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        [
            "Item",
            "Type",
            "Expected Qty",
            "Actual Qty",
            "Condition",
            "Status",
            "Unit Value",
            "Total Value",
            "Assigned To",
            "Serial",
        ]
    )
    for it in items:
        w.writerow(
            [
                it.get("item_name"),
                it.get("item_type"),
                it.get("quantity_expected"),
                it.get("quantity_actual"),
                it.get("condition"),
                it.get("status"),
                it.get("unit_value"),
                it.get("total_value"),
                it.get("assigned_to_name"),
                it.get("serial_number"),
            ]
        )
    return buf.getvalue().encode("utf-8")


def _print_checklist_text(asset: dict, items: list[dict]) -> str:
    lines = [
        f"KIT CHECKLIST — {asset.get('asset_name') or ''} ({asset.get('asset_number') or ''})",
        f"Supervisor: {asset.get('assigned_to_name') or asset.get('operator') or '—'}",
        "",
        "Item | Exp | Act | Status | Condition",
        "-" * 60,
    ]
    for it in items:
        lines.append(
            f"{it.get('item_name')} | {it.get('quantity_expected')} | "
            f"{it.get('quantity_actual')} | {it.get('status')} | {it.get('condition')}"
        )
    return "\n".join(lines)


def _filter_kit_items(
    items: list[dict],
    *,
    type_f: str,
    cond_f: str,
    stat_f: str,
    assign_f: str,
) -> list[dict]:
    out = items
    if type_f and type_f != "All":
        out = [i for i in out if str(i.get("item_type") or "") == type_f]
    if cond_f and cond_f != "All":
        out = [i for i in out if str(i.get("condition") or "") == cond_f]
    if stat_f and stat_f != "All":
        out = [i for i in out if str(i.get("status") or "") == stat_f]
    if assign_f and assign_f != "All":
        out = [i for i in out if str(i.get("assigned_to_name") or "—") == assign_f]
    return out


def _render_kit_items_table(asset: dict, aid: str, items: list[dict]) -> None:
    sel_key = _sk(aid, "sel")
    view_key = _sk(aid, "view")
    selected_id = str(st.session_state.get(sel_key) or "")

    fc1, fc2, fc3, fc4 = st.columns(4)
    type_f = fc1.selectbox("Type", ["All", *ITEM_TYPES], key=_sk(aid, "f_type"), label_visibility="collapsed")
    cond_f = fc2.selectbox("Condition", ["All", *CONDITIONS], key=_sk(aid, "f_cond"), label_visibility="collapsed")
    stat_f = fc3.selectbox("Status", ["All", *ITEM_STATUSES], key=_sk(aid, "f_stat"), label_visibility="collapsed")
    assign_opts = ["All"] + sorted({str(i.get("assigned_to_name") or "—") for i in items})
    assign_f = fc4.selectbox("Assigned", assign_opts, key=_sk(aid, "f_assign"), label_visibility="collapsed")

    filtered = _filter_kit_items(items, type_f=type_f, cond_f=cond_f, stat_f=stat_f, assign_f=assign_f)

    hdr = st.columns([0.4, 2.2, 1.0, 0.7, 0.7, 1.0, 1.0, 0.9, 0.9, 1.0])
    labels = ["", "Item", "Type", "Exp", "Act", "Condition", "Status", "Unit $", "Total $", "Assigned"]
    for col, lbl in zip(hdr, labels):
        with col:
            st.markdown(f"**{lbl}**" if lbl else "")

    for it in filtered:
        iid = str(it.get("id") or "")
        cols = st.columns([0.4, 2.2, 1.0, 0.7, 0.7, 1.0, 1.0, 0.9, 0.9, 1.0])
        with cols[0]:
            picked = st.checkbox("", key=f"kit_chk_{aid}_{iid}", label_visibility="collapsed")
            if picked:
                st.session_state[sel_key] = iid
                st.session_state[view_key] = "detail"
        with cols[1]:
            st.markdown(html.escape(str(it.get("item_name") or "—")))
        with cols[2]:
            st.caption(str(it.get("item_type") or "—"))
        with cols[3]:
            st.caption(str(it.get("quantity_expected") or 0))
        with cols[4]:
            st.caption(str(it.get("quantity_actual") or 0))
        with cols[5]:
            st.markdown(kit_item_status_pill_html(str(it.get("condition") or "—")), unsafe_allow_html=True)
        with cols[6]:
            st.markdown(kit_item_status_pill_html(str(it.get("status") or "—")), unsafe_allow_html=True)
        with cols[7]:
            st.caption(fmt_currency(it.get("unit_value")))
        with cols[8]:
            st.caption(fmt_currency(it.get("total_value")))
        with cols[9]:
            st.caption(str(it.get("assigned_to_name") or "—"))

    if selected_id and st.session_state.get(view_key) == "detail":
        item = next((i for i in items if str(i.get("id")) == selected_id), None)
        if item:
            _render_kit_item_detail_inline(asset, aid, item)


def _render_kit_item_detail_inline(asset: dict, aid: str, item: dict) -> None:
    iid = str(item.get("id") or "")
    edit_key = _sk(aid, f"edit_{iid}")
    editing = st.session_state.get(edit_key, False)

    st.markdown('<div class="ips-kit-detail-panel">', unsafe_allow_html=True)
    h1, h2, h3 = st.columns([2, 1, 1])
    with h1:
        st.markdown(f"**{html.escape(str(item.get('item_name') or '—'))}**")
    with h2:
        if not editing and st.button("Edit", key=f"kit_edit_btn_{aid}_{iid}"):
            st.session_state[edit_key] = True
            st.rerun()
    with h3:
        if st.button("Close", key=f"kit_close_{aid}_{iid}"):
            st.session_state[_sk(aid, "sel")] = ""
            st.session_state[_sk(aid, "view")] = "list"
            st.rerun()

    if editing:
        _render_kit_item_edit_form(asset, aid, item)
    else:
        st.markdown(
            f"Type: **{item.get('item_type')}** · Category: **{item.get('category') or '—'}**  \n"
            f"Expected: **{item.get('quantity_expected')}** · Actual: **{item.get('quantity_actual')}** · "
            f"Unit: **{item.get('unit')}**  \n"
            f"Value: **{fmt_currency(item.get('total_value'))}** "
            f"(unit {fmt_currency(item.get('unit_value'))})  \n"
            f"Condition: {kit_item_status_pill_html(str(item.get('condition') or ''))} · "
            f"Status: {kit_item_status_pill_html(str(item.get('status') or ''))}  \n"
            f"Serial: **{item.get('serial_number') or '—'}** · Assigned: **{item.get('assigned_to_name') or '—'}**",
            unsafe_allow_html=True,
        )
        if item.get("description"):
            st.caption(str(item.get("description")))
        if item.get("notes"):
            st.caption(f"Notes: {item.get('notes')}")
        if item.get("child_asset_id"):
            st.caption(f"Linked asset ID: {item.get('child_asset_id')}")
        if item.get("inventory_item_id"):
            st.caption(f"Linked inventory ID: {item.get('inventory_item_id')}")
        if st.button("Delete item", key=f"kit_del_{aid}_{iid}"):
            result = delete_asset_kit_item(iid)
            if result.ok:
                st.session_state[_sk(aid, "sel")] = ""
                st.success("Item removed.")
                st.rerun()
            else:
                st.error(result.error or "Could not delete.")
    st.markdown("</div>", unsafe_allow_html=True)


def _render_kit_item_edit_form(asset: dict, aid: str, item: dict) -> None:
    iid = str(item.get("id") or "")
    emp_opts = _employee_options()
    asset_opts = _asset_options(aid)
    inv_opts = _inventory_options()
    with st.form(f"kit_item_edit_{aid}_{iid}"):
        name = st.text_input("Item name", value=str(item.get("item_name") or ""))
        item_type = st.selectbox("Type", ITEM_TYPES, index=ITEM_TYPES.index(str(item.get("item_type") or "Tool")) if str(item.get("item_type") or "Tool") in ITEM_TYPES else 0)
        category = st.text_input("Category", value=str(item.get("category") or ""))
        c1, c2, c3 = st.columns(3)
        with c1:
            qty_exp = st.number_input("Expected qty", min_value=0.0, value=float(item.get("quantity_expected") or 1), step=1.0)
        with c2:
            qty_act = st.number_input("Actual qty", min_value=0.0, value=float(item.get("quantity_actual") or 1), step=1.0)
        with c3:
            unit_val = st.number_input("Unit value", min_value=0.0, value=float(item.get("unit_value") or 0), step=1.0)
        condition = st.selectbox("Condition", CONDITIONS, index=CONDITIONS.index(str(item.get("condition") or "Good")) if str(item.get("condition") or "Good") in CONDITIONS else 1)
        status = st.selectbox("Status", ITEM_STATUSES, index=ITEM_STATUSES.index(str(item.get("status") or "Present")) if str(item.get("status") or "Present") in ITEM_STATUSES else 0)
        serial = st.text_input("Serial number", value=str(item.get("serial_number") or ""))
        emp_labels = [x[0] for x in emp_opts]
        cur_assign = str(item.get("assigned_to_name") or "")
        assign_label = st.selectbox("Assigned to", emp_labels, index=emp_labels.index(cur_assign) if cur_assign in emp_labels else 0)
        asset_labels = [x[0] for x in asset_opts]
        inv_labels = [x[0] for x in inv_opts]
        link_asset = st.selectbox("Link asset", asset_labels, index=0)
        link_inv = st.selectbox("Link inventory", inv_labels, index=0)
        notes = st.text_area("Notes", value=str(item.get("notes") or ""), height=60)
        csave, ccancel = st.columns(2)
        save = csave.form_submit_button("Save", type="primary")
        cancel = ccancel.form_submit_button("Cancel")
    if cancel:
        st.session_state[_sk(aid, f"edit_{iid}")] = False
        st.rerun()
    if save:
        emp = next((e for lbl, e in emp_opts if lbl == assign_label), {})
        child = next((a for lbl, a in asset_opts if lbl == link_asset), {})
        inv = next((r for lbl, r in inv_opts if lbl == link_inv), {})
        result = update_asset_kit_item(
            iid,
            {
                "item_name": name,
                "item_type": item_type,
                "category": category,
                "quantity_expected": qty_exp,
                "quantity_actual": qty_act,
                "unit_value": unit_val,
                "condition": condition,
                "status": status,
                "serial_number": serial,
                "assigned_to_name": assign_label if assign_label != "— None —" else "",
                "assigned_to_employee_id": emp.get("id"),
                "child_asset_id": child.get("id") if child else item.get("child_asset_id"),
                "inventory_item_id": inv.get("id") if inv else item.get("inventory_item_id"),
                "notes": notes,
            },
        )
        if result.ok:
            st.session_state[_sk(aid, f"edit_{iid}")] = False
            st.success("Item updated.")
            st.rerun()
        else:
            st.error(result.error or "Could not save item.")


def _render_add_kit_item_form(asset: dict, aid: str) -> None:
    if st.button("← Back to kit list", key=f"kit_back_add_{aid}"):
        st.session_state[_sk(aid, "view")] = "list"
        st.rerun()
    st.markdown("##### Add Kit Item")
    with st.form(f"kit_add_item_{aid}"):
        name = st.text_input("Item name *")
        item_type = st.selectbox("Item type", ITEM_TYPES)
        category = st.text_input("Category")
        c1, c2, c3 = st.columns(3)
        with c1:
            qty = st.number_input("Quantity expected", min_value=0.0, value=1.0, step=1.0)
        with c2:
            unit = st.text_input("Unit", value="EA")
        with c3:
            unit_val = st.number_input("Unit value", min_value=0.0, value=0.0, step=1.0)
        condition = st.selectbox("Condition", CONDITIONS, index=1)
        status = st.selectbox("Status", ITEM_STATUSES, index=0)
        serial = st.text_input("Serial number (optional)")
        notes = st.text_area("Notes", height=50)
        if st.form_submit_button("Save Kit Item", type="primary"):
            if not str(name or "").strip():
                st.error("Item name is required.")
            else:
                result = create_asset_kit_item(
                    aid,
                    {
                        "item_name": name,
                        "item_type": item_type,
                        "category": category,
                        "quantity_expected": qty,
                        "quantity_actual": qty,
                        "unit": unit,
                        "unit_value": unit_val,
                        "condition": condition,
                        "status": status,
                        "serial_number": serial,
                        "notes": notes,
                    },
                )
                if result.ok:
                    st.session_state[_sk(aid, "view")] = "list"
                    st.success("Kit item added.")
                    st.rerun()
                else:
                    st.error(result.error or "Could not add item.")


def _render_import_inventory_form(asset: dict, aid: str) -> None:
    if st.button("← Back to kit list", key=f"kit_back_imp_{aid}"):
        st.session_state[_sk(aid, "view")] = "list"
        st.rerun()
    st.markdown("##### Import From Inventory")
    inv_opts = _inventory_options()
    labels = [x[0] for x in inv_opts]
    with st.form(f"kit_import_inv_{aid}"):
        pick = st.selectbox("Inventory item", labels, index=0)
        qty = st.number_input("Quantity", min_value=0.0, value=1.0, step=1.0)
        if st.form_submit_button("Import", type="primary"):
            row = next((r for lbl, r in inv_opts if lbl == pick), {})
            if not row:
                st.error("Select an inventory item.")
            else:
                unit_cost = float(row.get("unit_cost") or row.get("purchase_cost") or 0)
                result = create_asset_kit_item(
                    aid,
                    {
                        "item_name": row.get("item_name") or row.get("name"),
                        "item_type": "Consumable" if str(row.get("category") or "").lower() == "materials" else "Material",
                        "category": row.get("category"),
                        "description": row.get("description"),
                        "quantity_expected": qty,
                        "quantity_actual": qty,
                        "unit": row.get("unit") or "EA",
                        "unit_value": unit_cost,
                        "inventory_item_id": row.get("id"),
                    },
                )
                if result.ok:
                    st.session_state[_sk(aid, "view")] = "list"
                    st.success("Imported from inventory.")
                    st.rerun()
                else:
                    st.error(result.error or "Import failed.")


def _render_link_asset_form(asset: dict, aid: str) -> None:
    if st.button("← Back to kit list", key=f"kit_back_link_{aid}"):
        st.session_state[_sk(aid, "view")] = "list"
        st.rerun()
    st.markdown("##### Link Existing Asset")
    opts = _asset_options(aid)
    labels = [x[0] for x in opts]
    with st.form(f"kit_link_asset_{aid}"):
        pick = st.selectbox("Asset", labels, index=0)
        if st.form_submit_button("Link Asset", type="primary"):
            row = next((a for lbl, a in opts if lbl == pick), {})
            if not row:
                st.error("Select an asset.")
            else:
                val = float(row.get("value") or row.get("current_value") or row.get("purchase_price") or 0)
                result = create_asset_kit_item(
                    aid,
                    {
                        "item_name": row.get("asset_name") or row.get("name"),
                        "item_type": "Equipment",
                        "category": row.get("category"),
                        "quantity_expected": 1,
                        "quantity_actual": 1,
                        "unit_value": val,
                        "serial_number": row.get("serial_number"),
                        "child_asset_id": row.get("id"),
                    },
                )
                if result.ok:
                    st.session_state[_sk(aid, "view")] = "list"
                    st.success("Asset linked as kit item.")
                    st.rerun()
                else:
                    st.error(result.error or "Link failed.")


def _render_audit_form(asset: dict, aid: str, items: list[dict]) -> None:
    if st.button("← Back to kit list", key=f"kit_back_audit_{aid}"):
        st.session_state[_sk(aid, "view")] = "list"
        st.rerun()
    st.markdown("##### Kit Audit / Inspection")
    emp_opts = _employee_options()
    job_opts = _job_options()
    emp_labels = [x[0] for x in emp_opts]
    job_labels = [x[0] for x in job_opts]

    with st.form(f"kit_audit_meta_{aid}"):
        c1, c2 = st.columns(2)
        with c1:
            performer = st.text_input("Performed by name")
            phone = st.text_input("Phone")
        with c2:
            sup = st.selectbox("Supervisor responsible", emp_labels)
            job_label = st.selectbox("Job", job_labels)
        audit_notes = st.text_area("Audit notes", height=50)
        st.markdown("**Checklist**")
        lines: list[dict[str, Any]] = []
        for it in items:
            iid = str(it.get("id") or "")
            st.markdown(f"**{it.get('item_name')}**")
            lc1, lc2, lc3, lc4 = st.columns([1, 1, 1.2, 1.2])
            with lc1:
                exp_q = st.number_input("Expected", min_value=0.0, value=float(it.get("quantity_expected") or 1), key=f"aud_exp_{aid}_{iid}")
            with lc2:
                act_q = st.number_input("Actual", min_value=0.0, value=float(it.get("quantity_actual") or 1), key=f"aud_act_{aid}_{iid}")
            with lc3:
                cond = st.selectbox("Condition", CONDITIONS, index=CONDITIONS.index(str(it.get("condition") or "Good")) if str(it.get("condition") or "Good") in CONDITIONS else 1, key=f"aud_cond_{aid}_{iid}")
            with lc4:
                stat = st.selectbox("Status", ITEM_STATUSES, index=ITEM_STATUSES.index(str(it.get("status") or "Present")) if str(it.get("status") or "Present") in ITEM_STATUSES else 0, key=f"aud_stat_{aid}_{iid}")
            line_notes = st.text_input("Notes", key=f"aud_note_{aid}_{iid}", label_visibility="collapsed", placeholder="Notes")
            lines.append(
                {
                    "kit_item_id": iid,
                    "expected_quantity": exp_q,
                    "actual_quantity": act_q,
                    "condition": cond,
                    "status": stat,
                    "notes": line_notes,
                }
            )
        submit = st.form_submit_button("Submit Audit", type="primary")

    if submit:
        if not str(performer or "").strip():
            st.error("Performed by name is required.")
            return
        emp = next((e for lbl, e in emp_opts if lbl == sup), {})
        jid = next((j for lbl, j in job_opts if lbl == job_label), "")
        result = create_asset_kit_audit(
            aid,
            {
                "performed_by_name": performer,
                "performed_by_phone": phone,
                "assigned_supervisor_id": emp.get("id"),
                "assigned_supervisor_name": sup if sup != "— None —" else "",
                "job_id": jid or None,
                "notes": audit_notes,
            },
            lines,
        )
        if result.ok:
            data = result.data or {}
            miss_v = data.get("missing_value") or 0
            dmg_v = data.get("damaged_value") or 0
            if miss_v or dmg_v:
                st.warning(
                    f"Audit saved with issues — missing value: {fmt_currency(miss_v)}, "
                    f"damaged value: {fmt_currency(dmg_v)}"
                )
            else:
                st.success("Audit completed — all items accounted for.")
            st.session_state[_sk(aid, "view")] = "list"
            st.rerun()
        else:
            st.error(result.error or "Audit failed.")


def render_kit_contents_tab(asset: dict) -> None:
    """Kit / Contents tab body — inline only, no nested @st.dialog."""
    inject_kit_ui_styles()
    aid = str(asset.get("id") or "")
    if not aid:
        st.warning("Missing asset id.")
        return

    is_kit = asset_is_kit(asset)
    view = str(st.session_state.get(_sk(aid, "view"), "list"))

    if not is_kit:
        st.info("This asset is not a kit.")
        kt = st.selectbox("Kit type", KIT_TYPES, key=_sk(aid, "convert_type"))
        if st.button("Convert to Kit", type="primary", key=_sk(aid, "convert_btn")):
            result = convert_asset_to_kit(aid, kt)
            if result.ok:
                st.success(f"Converted to kit ({kt}).")
                st.rerun()
            else:
                st.error(result.error or "Could not convert.")
        return

    items = get_asset_kit_items(aid)
    summary = get_asset_kit_summary(aid, asset)
    _render_kit_summary_cards(asset, summary)
    _render_assignment_section(asset, aid)

    if view == "add":
        _render_add_kit_item_form(asset, aid)
        return
    if view == "import":
        _render_import_inventory_form(asset, aid)
        return
    if view == "link":
        _render_link_asset_form(asset, aid)
        return
    if view == "audit":
        _render_audit_form(asset, aid, items)
        return

    b1, b2, b3, b4, b5, b6 = st.columns(6, gap="small")
    if b1.button("+ Add Kit Item", key=f"kit_btn_add_{aid}", use_container_width=True):
        st.session_state[_sk(aid, "view")] = "add"
        st.rerun()
    if b2.button("Import Inventory", key=f"kit_btn_imp_{aid}", use_container_width=True):
        st.session_state[_sk(aid, "view")] = "import"
        st.rerun()
    if b3.button("Link Asset", key=f"kit_btn_link_{aid}", use_container_width=True):
        st.session_state[_sk(aid, "view")] = "link"
        st.rerun()
    if b4.button("Start Audit", key=f"kit_btn_audit_{aid}", use_container_width=True):
        st.session_state[_sk(aid, "view")] = "audit"
        st.rerun()
    checklist = _print_checklist_text(asset, items)
    b5.download_button(
        "Print Checklist",
        checklist.encode("utf-8"),
        file_name=f"kit_checklist_{asset.get('asset_number') or aid}.txt",
        mime="text/plain",
        key=f"kit_btn_print_{aid}",
        use_container_width=True,
    )
    b6.download_button(
        "Export List",
        _export_kit_csv(items),
        file_name=f"kit_items_{asset.get('asset_number') or aid}.csv",
        mime="text/csv",
        key=f"kit_btn_export_{aid}",
        use_container_width=True,
    )

    st.markdown("##### Kit Items")
    if not items:
        st.caption("No kit items yet. Add items, import from inventory, or link an existing asset.")
    else:
        _render_kit_items_table(asset, aid, items)

    audits = get_asset_kit_audits(aid, limit=5)
    if audits:
        with st.expander("Recent audits", expanded=False):
            for a in audits:
                st.markdown(
                    f"**{fmt_date(a.get('audit_date'))}** — "
                    f"Missing: {a.get('missing_item_count')} · Damaged: {a.get('damaged_item_count')} · "
                    f"By: {a.get('performed_by_name') or '—'}"
                )


def render_mobile_kit_scan(asset: dict) -> None:
    """Kit-specific mobile QR card actions and compact tool list."""
    inject_kit_ui_styles()
    aid = str(asset.get("id") or "")
    items = get_asset_kit_items(aid)
    summary = get_asset_kit_summary(aid, asset)
    view = str(st.session_state.get("_kit_scan_view") or "card")

    st.markdown(
        f'<div class="ips-asset-scan-title">{html.escape(str(asset.get("asset_name") or "—"))}</div>'
        f'<span class="ips-kit-badge">Kit</span> '
        f'{kit_item_status_pill_html(str(asset.get("kit_status") or "Active"))}',
        unsafe_allow_html=True,
    )
    st.caption(
        f"Supervisor: **{summary.get('assigned_supervisor')}** · "
        f"Items: {summary.get('present_items')}/{summary.get('expected_items')} present · "
        f"Value: {fmt_currency(summary.get('total_kit_value'))}"
    )

    if view == "audit":
        _render_audit_form(asset, aid, items)
        return
    if view == "tools":
        st.markdown("#### Tool List")
        for it in items[:100]:
            st.markdown(
                f"**{html.escape(str(it.get('item_name') or '—'))}** · "
                f"Exp {it.get('quantity_expected')} / Act {it.get('quantity_actual')} · "
                f"{kit_item_status_pill_html(str(it.get('status') or ''))}",
                unsafe_allow_html=True,
            )
        if st.button("← Back", key="kit_scan_back_tools"):
            st.session_state["_kit_scan_view"] = "card"
            st.rerun()
        return
    if view == "missing":
        st.markdown("#### Report Missing Tool")
        if not items:
            st.caption("No kit items.")
        else:
            labels = [str(i.get("item_name") or "") for i in items]
            pick = st.selectbox("Tool", labels)
            note = st.text_area("Notes")
            if st.button("Mark Missing", type="primary", key="kit_scan_mark_missing"):
                item = next(i for i in items if i.get("item_name") == pick)
                update_asset_kit_item(
                    str(item.get("id")),
                    {"status": "Missing", "condition": "Missing", "performed_by_name": st.session_state.get("_kit_scan_name")},
                )
                st.success("Marked missing.")
                st.session_state["_kit_scan_view"] = "card"
                st.rerun()
        if st.button("← Back", key="kit_scan_back_missing"):
            st.session_state["_kit_scan_view"] = "card"
            st.rerun()
        return

    if st.button("Start Trailer Audit", type="primary", use_container_width=True, key="kit_scan_audit"):
        st.session_state["_kit_scan_view"] = "audit"
        st.rerun()
    if st.button("View Tool List", use_container_width=True, key="kit_scan_tools"):
        st.session_state["_kit_scan_view"] = "tools"
        st.rerun()
    if st.button("Report Missing Tool", use_container_width=True, key="kit_scan_missing"):
        st.session_state["_kit_scan_view"] = "missing"
        st.rerun()

    st.markdown("---")
    st.markdown("#### Tools in Kit")
    for it in items[:20]:
        cols = st.columns([3, 1, 1])
        with cols[0]:
            st.markdown(f"**{html.escape(str(it.get('item_name') or '—'))}**")
        with cols[1]:
            st.caption(f"{it.get('quantity_actual')}/{it.get('quantity_expected')}")
        with cols[2]:
            st.markdown(kit_item_status_pill_html(str(it.get("status") or "")), unsafe_allow_html=True)
