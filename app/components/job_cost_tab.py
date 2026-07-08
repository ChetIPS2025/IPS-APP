"""Job Details — Cost tab: unified ledger lines with invoice visibility controls."""

from __future__ import annotations

import html
from typing import Any

import pandas as pd
import streamlit as st

try:
    from app.pages._core._data import load_inventory
    from app.services.catalog_images import catalog_thumbnail_html
    from app.services.job_cost_transaction_service import (
        can_manage_cost_invoice_visibility,
        fetch_job_cost_transactions,
        invalidate_job_cost_session,
        sync_all_sources_for_job,
        transaction_cost_tab_source,
        transaction_cost_unit,
        transaction_datetime_display,
        transaction_employee_name,
        transaction_show_on_invoice,
        update_job_cost_show_on_invoice,
    )
    from app.utils.formatting import fmt_currency
except ImportError:
    from pages._core._data import load_inventory  # type: ignore
    from services.catalog_images import catalog_thumbnail_html  # type: ignore
    from services.job_cost_transaction_service import (  # type: ignore
        can_manage_cost_invoice_visibility,
        fetch_job_cost_transactions,
        invalidate_job_cost_session,
        sync_all_sources_for_job,
        transaction_cost_tab_source,
        transaction_cost_unit,
        transaction_datetime_display,
        transaction_employee_name,
        transaction_show_on_invoice,
        update_job_cost_show_on_invoice,
    )
    from utils.formatting import fmt_currency  # type: ignore


def _join_employee_notes(employee: object, notes: object) -> str:
    emp = str(employee or "").strip()
    note = str(notes or "").strip()
    if emp and emp != "—" and note:
        return f"{emp} · {note}"
    if emp and emp != "—":
        return emp
    return note or "—"


def _format_qty_unit(qty: object, unit: object) -> str:
    try:
        q = float(qty or 0)
    except (TypeError, ValueError):
        q = 0.0
    unit_label = str(unit or "").strip()
    if abs(q - round(q)) < 0.0001:
        qty_text = str(int(round(q)))
    else:
        qty_text = f"{q:g}"
    return f"{qty_text} {unit_label}".strip() if unit_label else qty_text


def _format_amount_line(unit_cost: object, total_cost: object, qty: object) -> str:
    try:
        total = float(total_cost or 0)
        unit = float(unit_cost or 0)
        q = float(qty or 0)
    except (TypeError, ValueError):
        return fmt_currency(0)
    if q > 1.005 and unit > 0:
        return f"{fmt_currency(unit)}/ea · {fmt_currency(total)}"
    return fmt_currency(total)


def _compact_cost_display_df(df: pd.DataFrame) -> pd.DataFrame:
    """Fewer, narrower columns so rows fit without horizontal scrolling."""
    if df.empty:
        return pd.DataFrame(
            columns=["id", "description", "qty_unit", "amount", "detail", "show_on_invoice"]
        )
    out = df.copy()
    out["qty_unit"] = [
        _format_qty_unit(row.get("qty"), row.get("unit")) for _, row in out.iterrows()
    ]
    out["amount"] = [
        _format_amount_line(row.get("unit_cost"), row.get("total_cost"), row.get("qty"))
        for _, row in out.iterrows()
    ]
    out["detail"] = [
        _join_employee_notes(row.get("employee"), row.get("notes")) for _, row in out.iterrows()
    ]
    keep = ["id", "description", "qty_unit", "amount", "detail"]
    if "show_on_invoice" in out.columns:
        keep.append("show_on_invoice")
    return out[keep]


def inject_job_cost_tab_css() -> None:
    st.markdown(
        """
<style id="ips-job-cost-tab-v2">
.ips-job-cost-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.55rem;
  margin-bottom: 0.75rem;
}
@media (max-width: 900px) {
  .ips-job-cost-summary { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
.ips-job-cost-summary-card {
  background: #ffffff;
  border: 1px solid #dbe3ef;
  border-radius: 10px;
  padding: 0.6rem 0.75rem;
  min-width: 0;
}
.ips-job-cost-summary-label {
  font-size: 0.65rem;
  font-weight: 700;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.ips-job-cost-summary-value {
  font-size: 1rem;
  font-weight: 800;
  color: #0f172a;
  font-variant-numeric: tabular-nums;
}
.st-key-job_cost_table_wrap [data-testid="stDataFrame"],
.st-key-job_cost_table_wrap [data-testid="stDataEditor"] {
  border: 1px solid #dbe3ef;
  border-radius: 10px;
  overflow: hidden;
}
.st-key-job_cost_table_wrap [data-testid="stDataEditor"] > div,
.st-key-job_cost_table_wrap [data-testid="stDataFrame"] > div {
  width: 100% !important;
  max-width: 100% !important;
}
.st-key-job_cost_table_wrap [data-testid="stDataEditor"] [data-testid="glideDataEditor"],
.st-key-job_cost_table_wrap [data-testid="stDataFrame"] [data-testid="glideDataEditor"] {
  width: 100% !important;
  max-width: 100% !important;
}
.st-key-job_cost_table_wrap .dvn-scroller {
  overflow-x: hidden !important;
}
.st-key-job_cost_table_wrap canvas {
  max-width: 100% !important;
}
.ips-job-cost-thumb {
  width: 36px !important;
  height: 36px !important;
  max-width: 36px !important;
  max-height: 36px !important;
  object-fit: cover !important;
  border-radius: 6px !important;
  border: 1px solid #e2e8f0 !important;
}
.ips-job-cost-thumb-cell {
  width: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
        """,
        unsafe_allow_html=True,
    )


def _employees_map() -> dict[str, dict[str, Any]]:
    try:
        from app.db import fetch_table
    except ImportError:
        from db import fetch_table  # type: ignore
    try:
        rows = fetch_table("employees", limit=5000, order_by="name") or []
    except Exception:
        rows = []
    return {str(row.get("id") or ""): row for row in rows if row.get("id")}


def _inventory_map() -> dict[str, dict[str, Any]]:
    return {str(r.get("id") or ""): r for r in load_inventory() if str(r.get("id") or "")}


def _thumbnail_html(row: dict[str, Any], *, inv_by_id: dict[str, dict[str, Any]]) -> str:
    iid = str(row.get("inventory_item_id") or "").strip()
    if iid and iid in inv_by_id:
        return catalog_thumbnail_html(
            inv_by_id[iid],
            kind="inventory",
            css_class="ips-job-cost-thumb",
            cell_class="ips-job-cost-thumb-cell",
            alt="Item",
        )
    return '<span class="ips-job-cost-thumb-cell" aria-hidden="true">—</span>'


def _cost_summary_metrics(txns: list[dict[str, Any]]) -> dict[str, float]:
    totals = {"lines": 0.0, "invoice": 0.0, "internal": 0.0, "total_cost": 0.0}
    for row in txns:
        amt = float(row.get("total_cost") or 0)
        totals["lines"] += 1
        totals["total_cost"] += amt
        if transaction_show_on_invoice(row):
            totals["invoice"] += amt
        else:
            totals["internal"] += amt
    totals["total_cost"] = round(totals["total_cost"], 2)
    totals["invoice"] = round(totals["invoice"], 2)
    totals["internal"] = round(totals["internal"], 2)
    return totals


def _build_cost_dataframe(
    txns: list[dict[str, Any]],
    *,
    employees: dict[str, dict[str, Any]],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for txn in txns:
        desc = str(txn.get("description") or txn.get("item_name") or "—").strip() or "—"
        rows.append(
            {
                "id": str(txn.get("id") or ""),
                "date_time": transaction_datetime_display(txn),
                "source": transaction_cost_tab_source(txn),
                "description": desc,
                "qty": float(txn.get("quantity") or 0),
                "unit": transaction_cost_unit(txn),
                "unit_cost": float(txn.get("unit_cost") or 0),
                "total_cost": float(txn.get("total_cost") or 0),
                "employee": transaction_employee_name(txn, employees),
                "notes": str(txn.get("notes") or "").strip(),
                "show_on_invoice": transaction_show_on_invoice(txn),
            }
        )
    columns = [
        "id",
        "date_time",
        "source",
        "description",
        "qty",
        "unit",
        "unit_cost",
        "total_cost",
        "employee",
        "notes",
        "show_on_invoice",
    ]
    if not rows:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(rows)


def _render_cost_summary(txns: list[dict[str, Any]]) -> None:
    metrics = _cost_summary_metrics(txns)
    st.markdown(
        f"""
        <div class="ips-job-cost-summary">
          <div class="ips-job-cost-summary-card">
            <div class="ips-job-cost-summary-label">Cost lines</div>
            <div class="ips-job-cost-summary-value">{int(metrics["lines"])}</div>
          </div>
          <div class="ips-job-cost-summary-card">
            <div class="ips-job-cost-summary-label">Total job cost</div>
            <div class="ips-job-cost-summary-value">{html.escape(fmt_currency(metrics["total_cost"]))}</div>
          </div>
          <div class="ips-job-cost-summary-card">
            <div class="ips-job-cost-summary-label">On invoice</div>
            <div class="ips-job-cost-summary-value">{html.escape(fmt_currency(metrics["invoice"]))}</div>
          </div>
          <div class="ips-job-cost-summary-card">
            <div class="ips-job-cost-summary-label">Internal only</div>
            <div class="ips-job-cost-summary-value">{html.escape(fmt_currency(metrics["internal"]))}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _apply_invoice_visibility_changes(
    job_id: str,
    original: pd.DataFrame,
    edited: pd.DataFrame,
) -> int:
    if original.empty or edited.empty:
        return 0
    changed = 0
    orig_by_id = {str(r["id"]): bool(r["show_on_invoice"]) for _, r in original.iterrows()}
    for _, row in edited.iterrows():
        tid = str(row.get("id") or "").strip()
        if not tid or tid not in orig_by_id:
            continue
        new_val = bool(row.get("show_on_invoice"))
        if new_val == orig_by_id[tid]:
            continue
        if update_job_cost_show_on_invoice(tid, new_val):
            changed += 1
    if changed:
        invalidate_job_cost_session(job_id)
    return changed


def render_job_cost_tab(job: dict[str, Any], *, key_prefix: str = "job_cost_tab") -> None:
    """Unified job cost ledger for the Job Details Cost tab."""
    jid = str(job.get("id") or "").strip()
    if not jid:
        st.caption("Save this job before viewing cost lines.")
        return

    inject_job_cost_tab_css()
    st.markdown(
        '<span class="ips-job-cost-tab-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )

    hdr1, hdr2 = st.columns([1.2, 1], gap="small")
    with hdr1:
        st.markdown("#### Job cost lines")
        st.caption(
            "All costs tied to this job — scans, inventory issues, materials, equipment, labor, and other entries. "
            "Lines sync automatically from timekeeping, inventory, and job costing."
        )
    with hdr2:
        if st.button("Refresh costs", key=f"{key_prefix}_refresh", use_container_width=True):
            try:
                sync_all_sources_for_job(jid)
            except Exception:
                pass
            invalidate_job_cost_session(jid)
            st.rerun()

    try:
        sync_all_sources_for_job(jid)
    except Exception:
        pass

    txns = fetch_job_cost_transactions(jid)
    employees = _employees_map()
    inv_by_id = _inventory_map()
    _render_cost_summary(txns)

    if not txns:
        st.info(
            "No cost lines recorded for this job yet. "
            "Scan inventory to this job, add materials, record equipment, or approve timekeeping to populate this tab."
        )
        return

    base_df = _build_cost_dataframe(txns, employees=employees)
    is_admin = can_manage_cost_invoice_visibility()

    cat_filter = st.selectbox(
        "Source filter",
        ["All", "QR Scan", "Inventory", "Material", "Equipment", "Labor", "Other"],
        key=f"{key_prefix}_source_filter",
        label_visibility="collapsed",
    )
    display_df = base_df
    if cat_filter != "All":
        display_df = base_df[base_df["source"] == cat_filter].copy()
    compact_df = _compact_cost_display_df(display_df)

    with st.container(key="job_cost_table_wrap"):
        if is_admin:
            st.caption("Admins can toggle **Show on invoice** — hidden lines stay in job cost but are excluded from customer billing.")
            column_config = {
                "id": None,
                "description": st.column_config.TextColumn("Description", disabled=True, width="medium"),
                "qty_unit": st.column_config.TextColumn("Qty", disabled=True, width="small"),
                "amount": st.column_config.TextColumn("Amount", disabled=True, width="small"),
                "detail": st.column_config.TextColumn("Who / notes", disabled=True, width="small"),
                "show_on_invoice": st.column_config.CheckboxColumn(
                    "Invoice",
                    help="Include this line on customer invoice / T&M billing output.",
                    default=True,
                    width="small",
                ),
            }
            edited = st.data_editor(
                compact_df,
                column_config=column_config,
                hide_index=True,
                use_container_width=True,
                key=f"{key_prefix}_editor",
            )
            if st.button("Save invoice visibility", type="primary", key=f"{key_prefix}_save_invoice"):
                changed = _apply_invoice_visibility_changes(jid, compact_df, edited)
                if changed:
                    st.success(f"Updated {changed} cost line(s).")
                    st.rerun()
                else:
                    st.caption("No invoice visibility changes to save.")
        else:
            view_df = compact_df.drop(columns=["id", "show_on_invoice"], errors="ignore")
            st.dataframe(
                view_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "description": st.column_config.TextColumn("Description", width="medium"),
                    "qty_unit": st.column_config.TextColumn("Qty", width="small"),
                    "amount": st.column_config.TextColumn("Amount", width="small"),
                    "detail": st.column_config.TextColumn("Who / notes", width="small"),
                },
            )

    with st.expander("Full line details (date, source, unit cost)", expanded=False):
        detail_df = display_df.drop(columns=["id", "show_on_invoice"], errors="ignore")
        st.dataframe(
            detail_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "date_time": "Date / time",
                "source": "Source",
                "description": "Description",
                "qty": st.column_config.NumberColumn("Qty", format="%.4f"),
                "unit": "Unit",
                "unit_cost": st.column_config.NumberColumn("Unit cost", format="$%.2f"),
                "total_cost": st.column_config.NumberColumn("Total", format="$%.2f"),
                "employee": "Employee / scanned by",
                "notes": "Notes",
            },
        )

    with st.expander("Line thumbnails", expanded=False):
        thumb_rows = []
        for txn in txns[:80]:
            thumb_rows.append(
                f'<div style="display:flex;gap:0.5rem;align-items:center;margin:0.25rem 0;">'
                f"{_thumbnail_html(txn, inv_by_id=inv_by_id)}"
                f'<span style="font-size:0.8rem;">{html.escape(str(txn.get("description") or txn.get("item_name") or "—"))}</span>'
                f"</div>"
            )
        if thumb_rows:
            st.markdown("".join(thumb_rows), unsafe_allow_html=True)
        else:
            st.caption("No inventory-linked lines with images.")
