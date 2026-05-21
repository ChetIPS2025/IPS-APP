"""
Inventory usage dashboard: on-hand value, issuance trends, low stock (schema: inventory_items, inventory_transactions, jobs).
Assumes sql/027 + 028 + 030 applied; txn qty negative = issue; job_id links to jobs for labels.
Scan audit: scanned_by_name / scanned_by_user_id / device_label on inventory_transactions (030).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

import pandas as pd
import streamlit as st

try:
    from app.auth import current_role
    from app.ui.page_shell import render_page_header
    from app.db import create_signed_url, fetch_table_admin
    from app.services.job_service import job_row_select_label, sort_jobs_by_number_then_name
except ImportError:
    from auth import current_role  # type: ignore
    from ui.page_shell import render_page_header  # type: ignore
    from db import create_signed_url, fetch_table_admin  # type: ignore
    from services.job_service import job_row_select_label, sort_jobs_by_number_then_name  # type: ignore

_INV = "inventory_items"
_TXN = "inventory_transactions"

_PLACEHOLDER_THUMB = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def _dash_thumb_url(row: dict) -> str:
    s = str(row.get("image_url") or "").strip()
    if not s:
        return _PLACEHOLDER_THUMB
    if s.startswith("http://") or s.startswith("https://"):
        return s
    try:
        u = create_signed_url(s, expires_in=3600)
        return u or _PLACEHOLDER_THUMB
    except Exception:
        return _PLACEHOLDER_THUMB


def _is_low(r: dict) -> bool:
    try:
        q = float(r.get("quantity_on_hand") or 0)
        rp = float(r.get("reorder_point") or 0)
    except (TypeError, ValueError):
        return False
    return q <= rp


def _parse_ts(v: Any) -> datetime | None:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    try:
        s2 = s.replace("Z", "+00:00")
        return datetime.fromisoformat(s2)
    except ValueError:
        return None


def _money(v: float) -> str:
    try:
        return f"${float(v):,.2f}"
    except (TypeError, ValueError):
        return "—"


def _scanned_by_display(t: dict) -> str:
    sn = str(t.get("scanned_by_name") or "").strip()
    if sn:
        return sn
    cb = str(t.get("created_by") or "").strip()
    if cb:
        return cb
    pid = str(t.get("profile_id") or "").strip()
    return (pid[:12] + "…") if len(pid) > 12 else (pid or "—")


def _device_label_display(t: dict) -> str:
    return str(t.get("device_label") or "").strip() or "—"


def _txn_time_display(t: dict) -> str:
    dt = _parse_ts(t.get("created_at"))
    if not dt:
        return str(t.get("created_at") or "")[:16]
    h12 = dt.hour % 12 or 12
    return f"{h12}:{dt.minute:02d} {dt.strftime('%p').lower()}"


def _txn_activity_line(t: dict, *, item_by_id: dict, job_by_id: dict) -> str:
    iid = str(t.get("inventory_item_id") or "")
    nm = str(item_by_id.get(iid, {}).get("item_name") or "Item")
    qty = abs(float(t.get("qty") or 0))
    jid = str(t.get("job_id") or "").strip()
    jr = job_by_id.get(jid) if jid else None
    jt = job_row_select_label(jr) if jr else "—"
    who = _scanned_by_display(t)
    dev = _device_label_display(t)
    tm = _txn_time_display(t)
    parts = [nm, f"{qty:g} pcs", jt, who]
    if dev != "—":
        parts.append(f"Device {dev}")
    parts.append(tm)
    return " – ".join(parts)


def render() -> None:
    render_page_header(
        "Inventory Usage",
        "On-hand value, recent issues, and low stock visibility.",
    )

    if current_role() not in {"admin", "pm", "employee", "viewer"}:
        st.error("You do not have access to this page.")
        return

    try:
        items = fetch_table_admin(_INV, limit=8000, order_by="item_name")
    except Exception:
        st.warning("Could not load **inventory_items**.")
        return

    try:
        txns = fetch_table_admin(_TXN, limit=15000, order_by="created_at")
    except Exception:
        txns = []
        st.info("**inventory_transactions** not found or empty — run migration **027**.")

    try:
        jobs = sort_jobs_by_number_then_name(fetch_table_admin("jobs", limit=5000))
    except Exception:
        jobs = []
    job_by_id = {str(j.get("id")): j for j in jobs if j.get("id")}

    item_by_id = {str(r.get("id")): r for r in items if r.get("id")}

    filt = st.radio(
        "Date range for usage charts",
        ("This Week", "Last 30 Days", "All Time"),
        horizontal=True,
        key="inv_dash_range",
    )
    today = date.today()
    if filt == "This Week":
        start_d = today - timedelta(days=today.weekday())
    elif filt == "Last 30 Days":
        start_d = today - timedelta(days=30)
    else:
        start_d = None

    def _in_range(trow: dict) -> bool:
        if start_d is None:
            return True
        dt = _parse_ts(trow.get("created_at"))
        if not dt:
            return False
        return dt.date() >= start_d

    tx_f = [t for t in txns if _in_range(t) and float(t.get("qty") or 0) < 0]

    n_items = len([r for r in items if bool(r.get("is_active", True))])
    low_items = [r for r in items if bool(r.get("is_active", True)) and _is_low(r)]
    n_low = len(low_items)

    on_hand_value = 0.0
    for r in items:
        if not bool(r.get("is_active", True)):
            continue
        q = float(r.get("quantity_on_hand") or 0)
        try:
            uc = float(r.get("unit_cost") or 0)
        except (TypeError, ValueError):
            uc = 0.0
        on_hand_value += q * uc

    issued_week_units = sum(abs(float(t.get("qty") or 0)) for t in tx_f)

    c1, c2, c3, c4 = st.columns(4, gap="small")
    c1.metric("Active items", f"{n_items:,}")
    c2.metric("On-hand value (est.)", _money(on_hand_value))
    c3.metric("Units issued (range)", f"{issued_week_units:,.2f}")
    c4.metric("Low stock count", f"{n_low:,}")

    if n_low:
        st.subheader("Low stock")
        st.caption("Rule: **quantity_on_hand ≤ reorder_point** (reorder_point defaults to 0).")
        low_rows = []
        for r in sorted(low_items, key=lambda x: str(x.get("item_name") or "").lower())[:200]:
            low_rows.append(
                {
                    "Photo": _dash_thumb_url(r),
                    "Item": str(r.get("item_name") or ""),
                    "Qty": float(r.get("quantity_on_hand") or 0),
                    "Reorder at": float(r.get("reorder_point") or 0),
                    "Vendor": str(r.get("vendor") or ""),
                    "SKU": str(r.get("sku") or ""),
                }
            )
        st.dataframe(
            pd.DataFrame(low_rows),
            use_container_width=True,
            hide_index=True,
            column_config={"Photo": st.column_config.ImageColumn("Photo", width="small")},
        )

    # --- Usage by item (from filtered tx) ---
    usage_by_item: dict[str, float] = {}
    value_by_item: dict[str, float] = {}
    for t in tx_f:
        iid = str(t.get("inventory_item_id") or "")
        if not iid:
            continue
        q = abs(float(t.get("qty") or 0))
        usage_by_item[iid] = usage_by_item.get(iid, 0.0) + q
        ir = item_by_id.get(iid, {})
        try:
            uc = float(ir.get("unit_cost") or 0)
        except (TypeError, ValueError):
            uc = 0.0
        value_by_item[iid] = value_by_item.get(iid, 0.0) + q * uc

    top_qty = sorted(usage_by_item.items(), key=lambda x: -x[1])[:10]
    top_val = sorted(value_by_item.items(), key=lambda x: -x[1])[:10]

    st.subheader("Most issued (by quantity)")
    if top_qty:
        rows = []
        for iid, u in top_qty:
            ir = item_by_id.get(iid, {})
            nm = str(ir.get("item_name") or iid[:8])
            rows.append({"Photo": _dash_thumb_url(ir), "Item": nm, "Qty issued": u})
        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
            column_config={"Photo": st.column_config.ImageColumn("Photo", width="small")},
        )
    else:
        st.caption("No outbound transactions in this range.")

    st.subheader("Most issued (by est. dollar value)")
    if top_val:
        rows = []
        for iid, v in top_val:
            ir = item_by_id.get(iid, {})
            nm = str(ir.get("item_name") or iid[:8])
            rows.append({"Photo": _dash_thumb_url(ir), "Item": nm, "Value issued": _money(v)})
        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
            column_config={"Photo": st.column_config.ImageColumn("Photo", width="small")},
        )
    else:
        st.caption("No valued issues in this range.")

    st.subheader("Recent transactions")
    st.caption("**Scanned by** uses scan login (or **sql/030** fields); legacy rows may show **created_by** / profile id.")
    recent = sorted(tx_f, key=lambda t: str(t.get("created_at") or ""), reverse=True)[:40]
    if not recent:
        st.caption("No transactions in range.")
    else:
        rows = []
        for t in recent:
            iid = str(t.get("inventory_item_id") or "")
            jid = str(t.get("job_id") or "").strip()
            jr = job_by_id.get(jid) if jid else None
            if jr:
                jlab = f"{job_row_select_label(jr)}"
            else:
                jlab = "—"
            ir = item_by_id.get(iid, {})
            nm = str(ir.get("item_name") or iid[:8])
            rows.append(
                {
                    "When": str(t.get("created_at") or "")[:19],
                    "Photo": _dash_thumb_url(ir),
                    "Item": nm,
                    "Qty": float(t.get("qty") or 0),
                    "Type": str(t.get("txn_type") or ""),
                    "Job": jlab,
                    "Scanned by": _scanned_by_display(t),
                    "Device": _device_label_display(t),
                    "Notes": str(t.get("notes") or "")[:80],
                    "Activity": _txn_activity_line(t, item_by_id=item_by_id, job_by_id=job_by_id),
                }
            )
        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
            column_config={"Photo": st.column_config.ImageColumn("Photo", width="small")},
        )

    st.subheader("Issued by job (range)")
    by_job: dict[str, float] = {}
    for t in tx_f:
        jid = str(t.get("job_id") or "").strip()
        if not jid:
            continue
        q = abs(float(t.get("qty") or 0))
        try:
            uc = float(item_by_id.get(str(t.get("inventory_item_id") or ""), {}).get("unit_cost") or 0)
        except (TypeError, ValueError):
            uc = 0.0
        by_job[jid] = by_job.get(jid, 0.0) + q * uc
    if by_job:
        jr = []
        for jid, v in sorted(by_job.items(), key=lambda x: -x[1])[:25]:
            j = job_by_id.get(jid, {})
            jr.append({"Job": job_row_select_label(j), "Est. value issued": _money(v)})
        st.dataframe(pd.DataFrame(jr), use_container_width=True, hide_index=True)
    else:
        st.caption("No job-linked issues in this range.")
