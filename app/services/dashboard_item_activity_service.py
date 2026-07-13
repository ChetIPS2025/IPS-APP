"""
Recent Activity feed for the Dashboard — automated system events only.

Tracks inventory transactions and serialized tool check-in/out. Do not mix
with Company Updates (human announcements from ``company_updates``).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.inventory_service import normalize_inventory
from app.services.job_service import job_row_select_label
from app.services.repository import fetch_rows
from app.services.tracking_terminology import (
    inventory_action_label,
    serialized_tool_action_label,
)
_INV_TXN = "inventory_transactions"
_TOOL_TXN = "tool_transactions"
_INV_ITEMS = "inventory_items"
_ASSETS = "assets"
_EMPLOYEES = "employees"
_JOBS = "jobs"

_INVENTORY_ACTIONS = frozenset({
    "CONSUME_ON_JOB",
    "CONSUME",
    "ISSUE_TO_JOB",
    "TO_JOB",
    "SHOP",
    "SHOP_USE",
    "OUT",
})

_TOOL_ACTIONS = frozenset({
    "CHECK_OUT",
    "CHECK_IN",
    "ASSIGN",
    "RETURN",
    "REASSIGN",
})


def _norm_type(raw: object) -> str:
    return str(raw or "").strip().upper().replace("-", "_")


def _time_ago(ts: object) -> str:
    if not ts:
        return ""
    try:
        s = str(ts).strip().replace("Z", "+00:00")
        if "T" in s:
            dt = datetime.fromisoformat(s[:26])
        else:
            dt = datetime.fromisoformat(s[:10])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        sec = max(0, int((now - dt).total_seconds()))
        if sec < 3600:
            return f"{max(1, sec // 60)}m ago"
        if sec < 86400:
            return f"{sec // 3600}h ago"
        if sec < 604800:
            return f"{sec // 86400}d ago"
        return dt.strftime("%b %d")
    except Exception:
        return str(ts)[:16]


def _icon_for_action(action_label: str, *, domain: str) -> tuple[str, str]:
    label = action_label.casefold()
    if domain == "inventory":
        return "📦", "#f3e8ff"
    if "check in" in label or "returned" in label:
        return "🔧", "#dcfce7"
    if "check out" in label or "assign" in label:
        return "🔧", "#ffedd5"
    return "🔧", "#e0f2fe"


def _qty_suffix(row: dict[str, Any]) -> str:
    qty = abs(float(row.get("quantity") or row.get("qty") or 0))
    if not qty:
        return ""
    unit = str(row.get("unit") or "EA").strip() or "EA"
    body = f"{int(qty):,}" if qty == int(qty) else f"{qty:g}"
    return f" ({body} {unit})"


def _build_inventory_events(
    txns: list[dict[str, Any]],
    *,
    items_by_id: dict[str, dict[str, Any]],
    jobs_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for row in txns:
        txn_type = _norm_type(row.get("transaction_type") or row.get("txn_type"))
        if txn_type not in _INVENTORY_ACTIONS:
            continue
        iid = str(row.get("inventory_item_id") or "").strip()
        item = items_by_id.get(iid, {})
        name = str(item.get("name") or item.get("item_name") or "Inventory item")
        action = inventory_action_label(txn_type)
        jid = str(row.get("job_id") or "").strip()
        job = jobs_by_id.get(jid, {})
        job_label = job_row_select_label(job) if job else ""
        who = str(row.get("scanned_by_name") or row.get("created_by") or "").strip()
        meta_parts = [p for p in (job_label, who, _time_ago(row.get("created_at"))) if p]
        icon, icon_bg = _icon_for_action(action, domain="inventory")
        events.append({
            "icon": icon,
            "icon_bg": icon_bg,
            "title": f"{action} · {name}{_qty_suffix(row)}",
            "meta": " · ".join(meta_parts) or "—",
            "_sort_ts": str(row.get("created_at") or ""),
        })
    return events


def _build_tool_events(
    txns: list[dict[str, Any]],
    *,
    assets_by_id: dict[str, dict[str, Any]],
    jobs_by_id: dict[str, dict[str, Any]],
    employees_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for row in txns:
        txn_type = _norm_type(row.get("transaction_type"))
        if txn_type not in _TOOL_ACTIONS:
            continue
        tid = str(row.get("tool_id") or "").strip()
        asset = assets_by_id.get(tid, {})
        name = str(asset.get("asset_name") or asset.get("name") or "Tool")
        action = serialized_tool_action_label(txn_type)
        jid = str(row.get("job_id") or "").strip()
        job = jobs_by_id.get(jid, {})
        job_label = job_row_select_label(job) if job else ""
        eid = str(row.get("employee_id") or "").strip()
        emp = employees_by_id.get(eid, {})
        who = str(emp.get("name") or emp.get("full_name") or "").strip()
        meta_parts = [p for p in (job_label, who, _time_ago(row.get("created_at"))) if p]
        icon, icon_bg = _icon_for_action(action, domain="tool")
        events.append({
            "icon": icon,
            "icon_bg": icon_bg,
            "title": f"{action} · {name}",
            "meta": " · ".join(meta_parts) or "—",
            "_sort_ts": str(row.get("created_at") or ""),
        })
    return events


def recent_item_activity_feed(*, limit: int = 10) -> list[dict[str, Any]]:
    """Last N inventory use + serialized tool possession events."""
    inv_txns, _ = fetch_rows(_INV_TXN, limit=80, order_by="created_at")
    tool_txns, _ = fetch_rows(_TOOL_TXN, limit=80, order_by="created_at")

    items_by_id: dict[str, dict[str, Any]] = {}
    inv_rows, _ = fetch_rows(_INV_ITEMS, limit=5000, order_by="item_name", alt_tables=("inventory",))
    for row in inv_rows:
        norm = normalize_inventory(row)
        iid = str(norm.get("id") or "").strip()
        if iid:
            items_by_id[iid] = norm

    assets_by_id: dict[str, dict[str, Any]] = {}
    asset_rows, _ = fetch_rows(_ASSETS, limit=5000, order_by="asset_name", alt_tables=("asset_database",))
    for row in asset_rows:
        aid = str(row.get("id") or "").strip()
        if aid:
            assets_by_id[aid] = row

    jobs_by_id: dict[str, dict[str, Any]] = {}
    job_rows, _ = fetch_rows(_JOBS, limit=5000)
    for row in job_rows:
        jid = str(row.get("id") or "").strip()
        if jid:
            jobs_by_id[jid] = row

    employees_by_id: dict[str, dict[str, Any]] = {}
    emp_rows, _ = fetch_rows(_EMPLOYEES, limit=5000, order_by="name")
    for row in emp_rows:
        eid = str(row.get("id") or "").strip()
        if eid:
            employees_by_id[eid] = row

    events = _build_inventory_events(
        inv_txns,
        items_by_id=items_by_id,
        jobs_by_id=jobs_by_id,
    )
    events.extend(
        _build_tool_events(
            tool_txns,
            assets_by_id=assets_by_id,
            jobs_by_id=jobs_by_id,
            employees_by_id=employees_by_id,
        )
    )
    events.sort(key=lambda e: str(e.get("_sort_ts") or ""), reverse=True)
    out = events[:limit]
    for row in out:
        row.pop("_sort_ts", None)
    return out


__all__ = ["recent_item_activity_feed"]
