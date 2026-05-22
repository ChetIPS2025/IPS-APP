"""Supabase read/write for Phase 2 rebuilt modules (with demo fallbacks)."""

from __future__ import annotations

from datetime import date
from typing import Any

try:
    from app.services.repository import (
        ServiceResult,
        delete_row,
        fetch_list,
        fetch_rows,
        insert_row,
        update_row,
    )
except ImportError:
    from services.repository import (  # type: ignore
        ServiceResult,
        delete_row,
        fetch_list,
        fetch_rows,
        insert_row,
        update_row,
    )

def _money_field(row: dict[str, Any], primary: str, *fallbacks: str) -> float:
    """Use ``primary`` when the key is present (including 0); else first present fallback."""
    if primary in row:
        raw = row[primary]
        if raw is not None and str(raw).strip() != "":
            try:
                return float(raw)
            except (TypeError, ValueError):
                pass
    for key in fallbacks:
        raw = row.get(key)
        if raw is not None and str(raw).strip() != "":
            try:
                return float(raw)
            except (TypeError, ValueError):
                continue
    return 0.0


def normalize_customer(row: dict[str, Any]) -> dict[str, Any]:
    cid = str(row.get("id") or "").strip()
    active = row.get("is_active", True)
    if isinstance(active, str):
        active = active.lower() in ("true", "1", "active", "yes")
    return {
        "id": cid or str(row.get("customer_name") or "—"),
        "customer_name": str(row.get("customer_name") or row.get("name") or "—"),
        "address": str(row.get("address") or ""),
        "city": str(row.get("city") or ""),
        "state": str(row.get("state") or ""),
        "zip": str(row.get("zip") or row.get("zip_code") or ""),
        "is_active": bool(active),
        "status": "Active" if active else "Inactive",
        "notes": str(row.get("notes") or ""),
    }


def normalize_customer_location(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("id") or ""),
        "customer_id": str(row.get("customer_id") or ""),
        "site_name": str(row.get("site_name") or row.get("location_name") or row.get("name") or "—"),
        "address": str(row.get("address_line1") or row.get("address") or ""),
        "city": str(row.get("city") or ""),
        "state": str(row.get("state") or ""),
        "zip": str(row.get("zip") or ""),
        "status": "Active" if row.get("is_active", True) else "Inactive",
        "notes": str(row.get("notes") or ""),
    }


def normalize_customer_contact(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("id") or ""),
        "customer_id": str(row.get("customer_id") or ""),
        "customer_location_id": str(row.get("customer_location_id") or ""),
        "contact_name": str(row.get("contact_name") or row.get("name") or "—"),
        "title": str(row.get("title") or row.get("role") or ""),
        "email": str(row.get("email") or ""),
        "phone": str(row.get("phone") or ""),
        "status": "Active" if row.get("is_active", True) else "Inactive",
        "is_primary": bool(row.get("is_primary")),
        "notes": str(row.get("notes") or ""),
    }


def _customer_name_by_id() -> dict[str, str]:
    """Map customer UUID -> company name for job list normalization."""
    try:
        from app.services.customers_service import list_customers
    except ImportError:
        from services.customers_service import list_customers  # type: ignore
    rows, _ = list_customers(demo=[])
    return {
        str(c.get("id") or "").strip(): str(c.get("customer_name") or c.get("name") or "").strip()
        for c in rows
        if str(c.get("id") or "").strip()
    }


def _resolve_customer_id_for_job(ui: dict[str, Any]) -> str:
    cid = str(ui.get("customer_id") or "").strip()
    if cid:
        return cid
    name = str(ui.get("customer") or "").strip()
    if not name:
        return ""
    try:
        from app.pages._core._data import customer_id_for_name
    except ImportError:
        from pages._core._data import customer_id_for_name  # type: ignore
    return customer_id_for_name(name)


def normalize_job(row: dict[str, Any]) -> dict[str, Any]:
    jid = str(row.get("id") or row.get("job_id") or "").strip()
    num = str(row.get("job_number") or row.get("number") or jid[:8] or "—")
    customer = str(row.get("customer_name") or row.get("customer") or "").strip()
    if not customer:
        cid = str(row.get("customer_id") or "").strip()
        if cid:
            customer = _customer_name_by_id().get(cid, "")
    if not customer:
        customer = "—"
    end = str(row.get("end_date") or row.get("target_completion_date") or "")[:10]
    return {
        "id": jid or num,
        "job_number": num,
        "job_name": str(row.get("job_name") or row.get("name") or row.get("description") or "—"),
        "customer": customer,
        "customer_id": str(row.get("customer_id") or "").strip(),
        "estimate_number": str(row.get("estimate_number") or row.get("quote_number") or "—"),
        "supervisor": str(row.get("supervisor") or row.get("supervisor_name") or "—"),
        "status": str(row.get("status") or "Draft"),
        "start_date": str(row.get("start_date") or "")[:10],
        "end_date": end,
        "progress": int(row.get("progress") or row.get("percent_complete") or 0),
        "description": str(row.get("notes") or row.get("description") or ""),
    }


def normalize_estimate(row: dict[str, Any]) -> dict[str, Any]:
    eid = str(row.get("id") or "").strip()
    num = str(row.get("quote_number") or row.get("estimate_number") or eid[:8] or "—")
    return {
        "id": eid or num,
        "estimate_number": num,
        "project_name": str(row.get("project_name") or row.get("job_name") or row.get("title") or "—"),
        "customer": str(row.get("customer_name") or row.get("customer") or "—"),
        "estimate_date": str(row.get("estimate_date") or row.get("created_at") or "")[:10],
        "expiration_date": str(row.get("expiration_date") or row.get("valid_through") or "")[:10],
        "total": float(row.get("total") or row.get("grand_total") or 0),
        "status": str(row.get("status") or "Draft"),
        "created_by": str(row.get("created_by") or row.get("prepared_by") or "—"),
        "job_number": str(row.get("job_number") or "—"),
        "description": str(row.get("description") or row.get("notes") or ""),
        "subtotal": _money_field(row, "subtotal", "total", "grand_total"),
        "tax": float(row.get("tax") or 0),
        "markup": float(row.get("markup") or 0),
        "customer_contact_id": str(row.get("customer_contact_id") or ""),
    }


def normalize_material_line(row: dict[str, Any], estimate_id: str) -> dict[str, Any]:
    return {
        "id": str(row.get("id") or ""),
        "estimate_id": estimate_id,
        "item_number": str(row.get("item_number") or row.get("item_key") or row.get("sku") or ""),
        "description": str(row.get("description") or ""),
        "category": str(row.get("category") or ""),
        "qty": float(row.get("qty") or row.get("quantity") or 0),
        "unit": str(row.get("unit") or "EA"),
        "unit_cost": float(row.get("unit_cost") or row.get("purchase_price") or 0),
        "total_cost": float(row.get("total_cost") or row.get("line_total") or 0),
    }


def normalize_inventory(row: dict[str, Any]) -> dict[str, Any]:
    iid = str(row.get("id") or "").strip()
    sku = str(row.get("sku") or row.get("item_number") or iid[:8])
    qty = row.get("qty_on_hand")
    if qty is None:
        qty = row.get("quantity_on_hand")
    return {
        "id": iid or sku,
        "sku": sku,
        "name": str(row.get("name") or row.get("item_name") or "—"),
        "category": str(row.get("category") or "—"),
        "location": str(row.get("location") or row.get("storage_location") or "—"),
        "department": str(row.get("department") or "—"),
        "status": str(row.get("status") or "In Stock"),
        "qty_on_hand": int(float(qty or 0)),
        "reorder_point": int(float(row.get("reorder_point") or 0)),
        "unit_cost": float(row.get("unit_cost") or 0),
        "vendor": str(row.get("vendor") or "—"),
    }


def normalize_asset(row: dict[str, Any]) -> dict[str, Any]:
    aid = str(row.get("id") or "").strip()
    num = str(row.get("asset_number") or row.get("asset_id") or row.get("tag") or aid[:8])
    return {
        "id": aid or num,
        "asset_number": num,
        "asset_name": str(row.get("asset_name") or row.get("name") or "—"),
        "category": str(row.get("category") or row.get("asset_type") or "—"),
        "location": str(row.get("location") or "—"),
        "department": str(row.get("department") or "—"),
        "status": str(row.get("status") or "In Service"),
        "acquired_date": str(row.get("acquired_date") or row.get("purchase_date") or "")[:10],
        "value": float(row.get("value") or row.get("current_value") or row.get("purchase_cost") or 0),
        "serial_number": str(row.get("serial_number") or "—"),
        "manufacturer": str(row.get("manufacturer") or "—"),
        "model": str(row.get("model") or "—"),
        "operator": str(row.get("operator") or row.get("assigned_employee") or "—"),
        "description": str(row.get("description") or row.get("notes") or ""),
        "qr_code_value": str(row.get("qr_code_value") or "").strip(),
    }


def normalize_employee(row: dict[str, Any]) -> dict[str, Any]:
    eid = str(row.get("id") or "").strip()
    active = row.get("is_active", row.get("status") == "Active")
    status = "Active" if active in (True, "true", "Active", 1) else "Inactive"
    if str(row.get("status") or "") in {"Active", "Inactive"}:
        status = str(row.get("status"))
    return {
        "id": eid,
        "name": str(row.get("name") or row.get("full_name") or "—"),
        "email": str(row.get("email") or "—"),
        "role": str(row.get("role") or "Employee"),
        "department": str(row.get("department") or "—"),
        "status": status,
        "last_login": str(row.get("last_login") or "—"),
        "phone": str(row.get("phone") or "—"),
        "username": str(row.get("username") or eid[:8]),
        "member_since": str(row.get("created_at") or row.get("member_since") or "")[:10],
    }


def normalize_cert(row: dict[str, Any], employee_name: str = "") -> dict[str, Any]:
    return {
        "id": str(row.get("id") or ""),
        "employee_id": str(row.get("employee_id") or ""),
        "employee_name": employee_name or str(row.get("employee_name") or ""),
        "cert_type": str(row.get("cert_type") or row.get("type") or ""),
        "cert_number": str(row.get("cert_number") or row.get("number") or ""),
        "issuer": str(row.get("issuer") or row.get("issuing_organization") or ""),
        "issue_date": str(row.get("issue_date") or "")[:10],
        "expiration_date": str(row.get("expiration_date") or "")[:10],
        "status": str(row.get("status") or "Active"),
        "notes": str(row.get("notes") or ""),
    }


def normalize_document_hub(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("id") or ""),
        "file_name": str(row.get("file_name") or row.get("name") or ""),
        "doc_type": str(row.get("doc_type") or row.get("document_type") or ""),
        "linked_module": str(row.get("linked_module") or ""),
        "linked_ref": str(row.get("linked_ref") or row.get("linked_record") or ""),
        "upload_date": str(row.get("upload_date") or row.get("created_at") or "")[:10],
        "uploaded_by": str(row.get("uploaded_by") or ""),
        "expiration_date": str(row.get("expiration_date") or "")[:10],
        "is_restricted": bool(row.get("is_restricted")),
    }


def normalize_company_update(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("id") or ""),
        "category": str(row.get("category") or "General"),
        "title": str(row.get("title") or ""),
        "body": str(row.get("body") or row.get("message") or ""),
        "date": str(row.get("date") or row.get("created_at") or "")[:10],
        "pinned": bool(row.get("pinned")),
        "is_new": bool(row.get("is_new")),
    }


def normalize_task(row: dict[str, Any]) -> dict[str, Any]:
    pri = str(row.get("priority") or "Medium")
    if pri == "Normal":
        pri = "Medium"
    status = str(row.get("status") or "Open")
    if status == "Complete":
        status = "Done"
    return {
        "id": str(row.get("id") or ""),
        "title": str(row.get("title") or ""),
        "status": status,
        "priority": pri,
        "assigned_to": str(row.get("assignee_name") or row.get("assigned_to") or "—"),
        "linked_job": str(row.get("job_label") or row.get("linked_job") or "— None —"),
        "linked_estimate": str(row.get("estimate_label") or row.get("linked_estimate") or "— None —"),
        "due_date": str(row.get("due_date") or "")[:10],
        "description": str(row.get("description") or ""),
        "activity": list(row.get("activity") or []),
    }


def normalize_timekeeping_summary(row: dict[str, Any], week_start: date) -> dict[str, Any]:
    return {
        "id": str(row.get("id") or row.get("employee_id") or ""),
        "name": str(row.get("name") or row.get("employee_name") or ""),
        "department": str(row.get("department") or ""),
        "week_start": str(row.get("week_start") or week_start.isoformat())[:10],
        "st_total": float(row.get("st_total") or 0),
        "ot_total": float(row.get("ot_total") or 0),
        "dt_total": float(row.get("dt_total") or 0),
        "status": str(row.get("status") or "Pending"),
    }


# --- Reads ---


def list_jobs(*, demo: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    rows, used = fetch_list("jobs", order_by="job_number", normalize=normalize_job, demo=demo)
    return rows if rows or not used else demo, used


def list_estimates(*, demo: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    rows, used = fetch_list("estimates", order_by="quote_number", normalize=normalize_estimate, demo=demo)
    return rows if rows or not used else demo, used


def list_estimate_materials(estimate_id: str, *, demo: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    eid = str(estimate_id or "").strip()
    rows, used_demo = fetch_list(
        "estimate_line_items",
        order_by="sort_order",
        demo=[],
        alt_tables=("estimate_materials",),
    )
    if rows and not used_demo:
        out = [normalize_material_line(r, eid) for r in rows if str(r.get("estimate_id") or "") == eid]
        if out:
            return out, False
    demo_match = [m for m in demo if m.get("estimate_id") == eid]
    return (demo_match if demo_match else demo), True


def list_inventory(*, demo: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    return fetch_list(
        "inventory_items",
        order_by="item_name",
        normalize=normalize_inventory,
        demo=demo,
        alt_tables=("inventory",),
    )


def list_assets(*, demo: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    rows, used = fetch_list(
        "assets",
        order_by="asset_id",
        normalize=normalize_asset,
        demo=demo,
        alt_tables=("asset_database",),
    )
    return rows, used


def list_employees(*, demo: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    return fetch_list("employees", order_by="name", normalize=normalize_employee, demo=demo)


def list_certifications(employee_id: str, *, demo: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    eid = str(employee_id or "").strip()
    rows, used = fetch_list("employee_certifications", order_by="expiration_date", demo=[], alt_tables=("certifications",))
    if rows and not used:
        out = [normalize_cert(r) for r in rows if not eid or str(r.get("employee_id") or "") == eid]
        if out:
            return out, False
    demo_match = [c for c in demo if c.get("employee_id") == eid] if eid else demo
    return (demo_match if demo_match else demo[:2]), True


def list_all_certifications(*, demo: list[dict[str, Any]], employees: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    rows, used = fetch_list("employee_certifications", demo=[], alt_tables=("certifications",))
    if rows and not used:
        name_map = {str(e.get("id")): str(e.get("name")) for e in employees}
        return [normalize_cert(r, name_map.get(str(r.get("employee_id") or ""), "")) for r in rows], False
    out = []
    for c in demo:
        emp = next((e for e in employees if e.get("id") == c.get("employee_id")), None)
        out.append({**c, "employee_name": str((emp or {}).get("name") or "")})
    return out, True


def list_documents_hub(*, role: str, demo: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    rows, used = fetch_list("documents_hub", order_by="upload_date", demo=[], alt_tables=("documents",))
    if rows and not used:
        out = [normalize_document_hub(r) for r in rows]
        if role != "admin":
            out = [d for d in out if not d.get("is_restricted")]
        return out, False
    out = list(demo)
    if role != "admin":
        out = [d for d in out if not d.get("is_restricted")]
    return out, True


def list_company_updates(*, category: str, demo: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    rows, used = fetch_list("company_updates", order_by="created_at", demo=demo)
    out = [normalize_company_update(r) for r in rows]
    if category and category != "All Updates":
        out = [u for u in out if u.get("category") == category]
    return out, used


def list_tasks(*, demo: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    rows, used = fetch_list("todos", order_by="due_date", normalize=normalize_task, demo=demo, alt_tables=("tasks",))
    return rows, used


def list_timekeeping_summaries(week_start: date, *, demo: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    ws = week_start.isoformat()
    rows, used = fetch_list(
        "employee_timekeeping_weeks",
        order_by="week_start",
        demo=[],
        alt_tables=("timekeeping",),
    )
    if rows and not used:
        filtered = [r for r in rows if str(r.get("week_start") or "")[:10] == ws]
        if filtered:
            return [normalize_timekeeping_summary(r, week_start) for r in filtered], False
        return [normalize_timekeeping_summary(r, week_start) for r in rows], False
    return [normalize_timekeeping_summary(r, week_start) for r in demo], True


# --- Writes (map UI -> DB) ---


def save_job(ui: dict[str, Any], *, row_id: str | None = None) -> ServiceResult:
    customer_name = str(ui.get("customer") or "").strip()
    customer_id = _resolve_customer_id_for_job(ui)
    if customer_name and not customer_id:
        return ServiceResult(ok=False, error=f"Customer not found: {customer_name}")

    payload: dict[str, Any] = {
        "job_number": ui.get("job_number"),
        "job_name": ui.get("job_name"),
        "status": ui.get("status"),
        "supervisor": ui.get("supervisor"),
        "project_manager": ui.get("project_manager"),
        "location": ui.get("location"),
        "start_date": ui.get("start_date") or None,
        "target_completion_date": ui.get("end_date") or None,
        "notes": ui.get("description") or ui.get("notes") or "",
    }
    if customer_id:
        payload["customer_id"] = customer_id
    if row_id:
        return update_row("jobs", payload, {"id": row_id})
    return insert_row("jobs", payload)


def save_estimate(ui: dict[str, Any], *, row_id: str | None = None) -> ServiceResult:
    payload = {
        "quote_number": ui.get("estimate_number"),
        "project_name": ui.get("project_name"),
        "customer_name": ui.get("customer"),
        "customer_id": ui.get("customer_id") or None,
        "customer_contact_id": ui.get("customer_contact_id") or None,
        "status": ui.get("status"),
        "estimate_date": ui.get("estimate_date") or None,
        "expiration_date": ui.get("expiration_date") or None,
        "prepared_by_name": ui.get("created_by") or ui.get("prepared_by_name"),
        "subtotal": ui.get("subtotal"),
        "tax": ui.get("tax"),
        "markup": ui.get("markup"),
        "total": ui.get("total"),
        "notes": ui.get("description") or ui.get("notes"),
    }
    if row_id:
        return update_row("estimates", payload, {"id": row_id})
    return insert_row("estimates", payload)


def save_estimate_line_item(ui: dict[str, Any], *, row_id: str | None = None) -> ServiceResult:
    qty = float(ui.get("qty") or 0)
    unit_cost = float(ui.get("unit_cost") or 0)
    payload = {
        "estimate_id": ui.get("estimate_id"),
        "item_number": ui.get("item_number"),
        "description": ui.get("description"),
        "category": ui.get("category"),
        "qty": qty,
        "unit": ui.get("unit") or "EA",
        "unit_cost": unit_cost,
        "total_cost": ui.get("total_cost") if ui.get("total_cost") is not None else qty * unit_cost,
        "vendor": ui.get("vendor") or "",
        "notes": ui.get("notes") or "",
        "sort_order": int(ui.get("sort_order") or 0),
    }
    if row_id:
        return update_row("estimate_line_items", payload, {"id": row_id})
    return insert_row("estimate_line_items", payload)


def save_inventory_item(ui: dict[str, Any], *, row_id: str | None = None) -> ServiceResult:
    payload = {
        "item_name": ui.get("name") or ui.get("item_name"),
        "sku": ui.get("sku") or ui.get("item_number"),
        "category": ui.get("category"),
        "storage_location": ui.get("location"),
        "department": ui.get("department") or "",
        "quantity_on_hand": ui.get("qty_on_hand"),
        "reorder_point": ui.get("reorder_point"),
        "unit_cost": ui.get("unit_cost"),
        "vendor": ui.get("vendor"),
        "status": ui.get("status") or "In Stock",
    }
    table = "inventory_items"
    if row_id:
        return update_row(table, payload, {"id": row_id})
    return insert_row(table, payload)


def save_asset(ui: dict[str, Any], *, row_id: str | None = None) -> ServiceResult:
    payload = {
        "asset_id": ui.get("asset_number") or ui.get("asset_id"),
        "asset_name": ui.get("asset_name"),
        "category": ui.get("category"),
        "location": ui.get("location"),
        "department": ui.get("department") or "",
        "status": ui.get("status"),
        "serial_number": ui.get("serial_number"),
        "manufacturer": ui.get("manufacturer"),
        "model": ui.get("model"),
        "notes": ui.get("description") or ui.get("notes"),
        "current_value": ui.get("value") or ui.get("current_value"),
        "acquired_date": ui.get("acquired_date") or None,
    }
    if row_id:
        return update_row("assets", payload, {"id": row_id})
    return insert_row("assets", payload)


def save_employee(ui: dict[str, Any], *, row_id: str | None = None) -> ServiceResult:
    active = str(ui.get("status", "Active")).lower() in ("active", "true", "1")
    payload = {
        "name": ui.get("name"),
        "email": ui.get("email"),
        "role": ui.get("role"),
        "department": ui.get("department"),
        "phone": ui.get("phone"),
        "username": ui.get("username"),
        "crew": ui.get("crew") or "",
        "position": ui.get("position") or "",
        "status": ui.get("status") or ("Active" if active else "Inactive"),
        "is_active": active,
        "notes": ui.get("notes") or "",
    }
    if row_id:
        return update_row("employees", payload, {"id": row_id})
    return insert_row("employees", payload)


def save_employee_document(ui: dict[str, Any], *, row_id: str | None = None) -> ServiceResult:
    payload = {
        "employee_id": ui.get("employee_id"),
        "doc_type": ui.get("doc_type"),
        "file_name": ui.get("file_name"),
        "uploaded_by": ui.get("uploaded_by") or "",
        "expiration_date": ui.get("expiration_date") or None,
        "is_restricted": bool(ui.get("is_restricted")),
        "storage_path": ui.get("storage_path") or "",
        "notes": ui.get("notes") or "",
    }
    table = "employee_documents"
    if row_id:
        return update_row(table, payload, {"id": row_id})
    return insert_row(table, payload)


def save_certification(ui: dict[str, Any], *, row_id: str | None = None) -> ServiceResult:
    payload = {
        "employee_id": ui.get("employee_id"),
        "cert_type": ui.get("cert_type"),
        "cert_number": ui.get("cert_number"),
        "issuer": ui.get("issuer"),
        "issue_date": ui.get("issue_date") or None,
        "expiration_date": ui.get("expiration_date") or None,
        "status": ui.get("status"),
        "notes": ui.get("notes"),
    }
    table = "employee_certifications"
    if row_id:
        return update_row(table, payload, {"id": row_id})
    return insert_row(table, payload)


def save_document_hub(ui: dict[str, Any], *, row_id: str | None = None) -> ServiceResult:
    payload = {
        "file_name": ui.get("file_name"),
        "doc_type": ui.get("doc_type"),
        "linked_module": ui.get("linked_module"),
        "linked_ref": ui.get("linked_ref"),
        "uploaded_by": ui.get("uploaded_by"),
        "expiration_date": ui.get("expiration_date") or None,
        "is_restricted": bool(ui.get("is_restricted")),
    }
    table = "documents_hub"
    if row_id:
        return update_row(table, payload, {"id": row_id})
    return insert_row(table, payload)


def save_company_update(ui: dict[str, Any], *, row_id: str | None = None) -> ServiceResult:
    payload = {
        "title": ui.get("title"),
        "message": ui.get("body") or ui.get("message"),
        "category": ui.get("category") or "Announcements",
        "priority": ui.get("priority") or "Normal",
        "pinned": bool(ui.get("pinned")),
        "is_active": ui.get("is_active", True) is not False,
    }
    if row_id:
        return update_row("company_updates", payload, {"id": row_id})
    return insert_row("company_updates", payload)


def save_task(ui: dict[str, Any], *, row_id: str | None = None) -> ServiceResult:
    pri = str(ui.get("priority") or "Medium")
    if pri == "Medium":
        pri = "Normal"
    status = str(ui.get("status") or "Open")
    if status == "Done":
        status = "Complete"
    payload = {
        "title": ui.get("title"),
        "description": ui.get("description"),
        "status": status,
        "priority": pri,
        "due_date": ui.get("due_date") or None,
        "assignee_name": ui.get("assigned_to"),
        "job_label": ui.get("linked_job"),
        "estimate_label": ui.get("linked_estimate"),
    }
    table = "todos"
    if row_id:
        return update_row(table, payload, {"id": row_id})
    return insert_row(table, payload)


def delete_job(row_id: str) -> ServiceResult:
    return delete_row("jobs", {"id": row_id})


def delete_estimate(row_id: str) -> ServiceResult:
    return delete_row("estimates", {"id": row_id})


def delete_inventory_item(row_id: str) -> ServiceResult:
    return delete_row("inventory_items", {"id": row_id})


def delete_asset(row_id: str) -> ServiceResult:
    return delete_row("assets", {"id": row_id})


def delete_employee(row_id: str) -> ServiceResult:
    return delete_row("employees", {"id": row_id})


def delete_certification(row_id: str) -> ServiceResult:
    return delete_row("employee_certifications", {"id": row_id})


def delete_document(row_id: str) -> ServiceResult:
    return delete_row("documents_hub", {"id": row_id})


def delete_company_update(row_id: str) -> ServiceResult:
    return delete_row("company_updates", {"id": row_id})


def delete_task(row_id: str) -> ServiceResult:
    return delete_row("todos", {"id": row_id})


def save_timekeeping_week(employee_id: str, week_start: date, ui_summary: dict[str, Any]) -> ServiceResult:
    payload = {
        "employee_id": employee_id,
        "week_start": week_start.isoformat(),
        "st_total": ui_summary.get("st_total"),
        "ot_total": ui_summary.get("ot_total"),
        "dt_total": ui_summary.get("dt_total"),
        "status": ui_summary.get("status") or "Pending",
        "notes": ui_summary.get("notes") or "",
    }
    rows, err = fetch_rows("employee_timekeeping_weeks", limit=500)
    existing: dict[str, Any] | None = None
    if not err:
        for r in rows:
            if (
                str(r.get("employee_id")) == str(employee_id)
                and str(r.get("week_start") or "")[:10] == week_start.isoformat()
            ):
                existing = r
                break
    if existing and existing.get("id"):
        return update_row("employee_timekeeping_weeks", payload, {"id": existing["id"]})
    return insert_row("employee_timekeeping_weeks", payload)


def save_timekeeping_day(ui: dict[str, Any], *, row_id: str | None = None) -> ServiceResult:
    payload = {
        "employee_id": ui.get("employee_id"),
        "week_start": ui.get("week_start"),
        "work_date": ui.get("work_date"),
        "job_id": ui.get("job_id") or None,
        "job_label": ui.get("job_label") or "",
        "st_hours": ui.get("st_hours") or 0,
        "ot_hours": ui.get("ot_hours") or 0,
        "dt_hours": ui.get("dt_hours") or 0,
        "notes": ui.get("notes") or "",
    }
    if row_id:
        return update_row("employee_timekeeping_days", payload, {"id": row_id})
    return insert_row("employee_timekeeping_days", payload)


def delete_estimate_line_item(row_id: str) -> ServiceResult:
    return delete_row("estimate_line_items", {"id": row_id})


def delete_employee_document(row_id: str) -> ServiceResult:
    return delete_row("employee_documents", {"id": row_id})


def list_customers(*, demo: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    return fetch_list("customers", order_by="customer_name", normalize=normalize_customer, demo=demo)


def list_customer_locations(customer_id: str, *, demo: list[dict[str, Any]] | None = None) -> tuple[list[dict[str, Any]], bool]:
    cid = str(customer_id or "").strip()
    rows, err = fetch_rows("customer_locations", limit=200, order_by="site_name")
    if err:
        demo_rows = [normalize_customer_location(r) for r in (demo or []) if str(r.get("customer_id")) == cid]
        return demo_rows, True
    out = [normalize_customer_location(r) for r in rows if str(r.get("customer_id")) == cid]
    return out, False


def save_customer_location(ui: dict[str, Any], *, row_id: str | None = None) -> ServiceResult:
    cid = str(ui.get("customer_id") or "").strip()
    if not cid:
        return ServiceResult(ok=False, error="Customer is required.")
    name = str(ui.get("site_name") or ui.get("location_name") or "").strip()
    if not name:
        return ServiceResult(ok=False, error="Location name is required.")
    active = str(ui.get("status", "Active")).lower() in ("active", "true", "1")
    address = str(ui.get("address") or "").strip()
    payload = {
        "customer_id": cid,
        "site_name": name,
        "location_name": name,
        "address_line1": address,
        "address": address,
        "city": str(ui.get("city") or "").strip(),
        "state": str(ui.get("state") or "").strip(),
        "zip": str(ui.get("zip") or "").strip(),
        "is_active": active,
        "notes": str(ui.get("notes") or "").strip(),
    }
    if row_id:
        return update_row("customer_locations", payload, {"id": row_id})
    return insert_row("customer_locations", payload)


def delete_customer_location(row_id: str) -> ServiceResult:
    return delete_row("customer_locations", {"id": row_id})


def list_customer_contacts(customer_id: str, *, demo: list[dict[str, Any]] | None = None) -> tuple[list[dict[str, Any]], bool]:
    cid = str(customer_id or "").strip()
    rows, err = fetch_rows("customer_contacts", limit=200, alt_tables=("contacts",))
    if err:
        demo_rows = [normalize_customer_contact(r) for r in (demo or []) if str(r.get("customer_id")) == cid]
        return demo_rows, True
    out = [normalize_customer_contact(r) for r in rows if str(r.get("customer_id")) == cid]
    return out, False


def save_customer_contact(ui: dict[str, Any], *, row_id: str | None = None) -> ServiceResult:
    cid = str(ui.get("customer_id") or "").strip()
    if not cid:
        return ServiceResult(ok=False, error="Customer is required.")
    name = str(ui.get("contact_name") or ui.get("name") or "").strip()
    if not name:
        return ServiceResult(ok=False, error="Contact name is required.")
    active = str(ui.get("status", "Active")).lower() in ("active", "true", "1")
    is_primary = bool(ui.get("is_primary")) and active
    title = str(ui.get("title") or "").strip()
    loc_id = str(ui.get("customer_location_id") or "").strip() or None
    payload = {
        "customer_id": cid,
        "contact_name": name,
        "role": title,
        "email": str(ui.get("email") or "").strip(),
        "phone": str(ui.get("phone") or "").strip(),
        "is_active": active,
        "is_primary": is_primary,
        "notes": str(ui.get("notes") or "").strip(),
        "customer_location_id": loc_id,
    }
    if row_id:
        result = update_row("customer_contacts", payload, {"id": row_id})
        contact_id = str(row_id).strip()
    else:
        result = insert_row("customer_contacts", payload)
        if not result.ok:
            return result
        row = result.data if isinstance(result.data, dict) else {}
        contact_id = str(row.get("id") or "").strip()
    if not result.ok:
        return result
    if is_primary and contact_id:
        _apply_primary_contact_scope(customer_id=cid, contact_id=contact_id, location_id=loc_id)
    return result


def _apply_primary_contact_scope(*, customer_id: str, contact_id: str, location_id: str | None) -> None:
    """Keep at most one primary contact per customer location scope (including company-wide)."""
    cid = str(customer_id or "").strip()
    keep = str(contact_id or "").strip()
    scope_loc = str(location_id or "").strip()
    if not cid or not keep:
        return
    rows, err = fetch_rows("customer_contacts", limit=500)
    if err:
        return
    for row in rows:
        if str(row.get("customer_id") or "").strip() != cid:
            continue
        rid = str(row.get("id") or "").strip()
        if not rid or rid == keep:
            continue
        row_loc = str(row.get("customer_location_id") or "").strip()
        if row_loc != scope_loc:
            continue
        if row.get("is_primary"):
            update_row("customer_contacts", {"is_primary": False}, {"id": rid})
    update_row("customer_contacts", {"is_primary": True}, {"id": keep})


def delete_customer_contact(row_id: str) -> ServiceResult:
    return delete_row("customer_contacts", {"id": row_id})


def save_customer(ui: dict[str, Any], *, row_id: str | None = None) -> ServiceResult:
    active = str(ui.get("status", "Active")).lower() in ("active", "true", "1")
    payload = {
        "customer_name": ui.get("customer_name") or ui.get("name"),
        "address": ui.get("address") or "",
        "city": ui.get("city") or "",
        "state": ui.get("state") or "",
        "zip": ui.get("zip") or "",
        "is_active": active,
        "notes": ui.get("notes") or "",
    }
    if row_id:
        return update_row("customers", payload, {"id": row_id})
    return insert_row("customers", payload)


def delete_customer(row_id: str) -> ServiceResult:
    return delete_row("customers", {"id": row_id})
