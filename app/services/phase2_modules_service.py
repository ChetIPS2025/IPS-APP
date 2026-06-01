"""Supabase read/write for Phase 2 rebuilt modules (with demo fallbacks)."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

try:
    from app.services.repository import (
        ServiceResult,
        clear_all_data_caches,
        delete_row,
        fetch_list,
        fetch_rows,
        insert_row,
        table_column_names,
        update_row,
    )
except ImportError:
    from services.repository import (  # type: ignore
        ServiceResult,
        clear_all_data_caches,
        delete_row,
        fetch_list,
        fetch_rows,
        insert_row,
        table_column_names,
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


def _estimate_json_get(row: dict[str, Any], key: str) -> str:
    ej = row.get("estimate_json")
    if isinstance(ej, dict):
        return str(ej.get(key) or "").strip()
    return ""


def _normalize_estimate_status(raw: Any) -> str:
    s = str(raw or "").strip()
    if not s:
        return "Draft"
    mapping = {
        "draft": "Draft",
        "pending": "Pending",
        "sent": "Sent",
        "approved": "Approved",
        "awarded": "Awarded",
        "rejected": "Rejected",
        "expired": "Expired",
        "cancelled": "Cancelled",
        "canceled": "Cancelled",
    }
    return mapping.get(s.lower(), s)


def normalize_customer(row: dict[str, Any]) -> dict[str, Any]:
    cid = str(row.get("id") or "").strip()
    active = row.get("is_active", True)
    if isinstance(active, str):
        active = active.lower() in ("true", "1", "active", "yes")
    status = str(row.get("status") or "").strip()
    if not status:
        status = "Active" if active else "Inactive"
    company = str(row.get("company_name") or row.get("customer_name") or row.get("name") or "—")
    return {
        "id": cid or company,
        "customer_name": company,
        "company_name": company,
        "customer_number": str(row.get("customer_number") or ""),
        "address": str(row.get("address") or ""),
        "city": str(row.get("city") or ""),
        "state": str(row.get("state") or ""),
        "zip": str(row.get("zip") or row.get("zip_code") or ""),
        "website": str(row.get("website") or ""),
        "main_phone": str(row.get("main_phone") or row.get("phone") or ""),
        "main_email": str(row.get("main_email") or row.get("email") or ""),
        "billing_email": str(row.get("billing_email") or ""),
        "is_active": bool(active),
        "status": status,
        "notes": str(row.get("notes") or ""),
        "created_at": str(row.get("created_at") or "")[:19],
        "updated_at": str(row.get("updated_at") or "")[:19],
    }


def normalize_customer_location(row: dict[str, Any]) -> dict[str, Any]:
    name = str(row.get("location_name") or row.get("site_name") or row.get("name") or "—")
    active = row.get("is_active", True)
    if isinstance(active, str):
        active = active.lower() in ("true", "1", "active", "yes")
    status = str(row.get("status") or "").strip()
    if not status:
        status = "Active" if active else "Inactive"
    addr1 = str(row.get("address_line_1") or row.get("address_line1") or row.get("address") or "")
    return {
        "id": str(row.get("id") or ""),
        "customer_id": str(row.get("customer_id") or ""),
        "location_name": name,
        "site_name": name,
        "location_type": str(row.get("location_type") or "Other"),
        "address_line_1": addr1,
        "address_line_2": str(row.get("address_line_2") or row.get("address_line2") or ""),
        "address": addr1,
        "city": str(row.get("city") or ""),
        "state": str(row.get("state") or ""),
        "zip": str(row.get("zip") or ""),
        "country": str(row.get("country") or "USA"),
        "phone": str(row.get("phone") or ""),
        "email": str(row.get("email") or ""),
        "is_primary": bool(row.get("is_primary")),
        "is_billing": bool(row.get("is_billing")),
        "is_shipping": bool(row.get("is_shipping")),
        "is_active": bool(active),
        "status": status,
        "notes": str(row.get("notes") or ""),
        "created_at": str(row.get("created_at") or "")[:19],
        "updated_at": str(row.get("updated_at") or "")[:19],
    }


def normalize_customer_contact(row: dict[str, Any]) -> dict[str, Any]:
    loc_id = str(row.get("location_id") or row.get("customer_location_id") or "")
    full_name = str(row.get("full_name") or row.get("contact_name") or row.get("name") or "—")
    active = row.get("is_active", True)
    if isinstance(active, str):
        active = active.lower() in ("true", "1", "active", "yes")
    status = str(row.get("status") or "").strip()
    if not status:
        status = "Active" if active else "Inactive"
    role_type = str(row.get("role_type") or row.get("title") or row.get("role") or "Other")
    return {
        "id": str(row.get("id") or ""),
        "customer_id": str(row.get("customer_id") or ""),
        "location_id": loc_id,
        "customer_location_id": loc_id,
        "full_name": full_name,
        "contact_name": full_name,
        "title": str(row.get("title") or role_type),
        "department": str(row.get("department") or ""),
        "email": str(row.get("email") or ""),
        "phone": str(row.get("phone") or ""),
        "mobile": str(row.get("mobile") or ""),
        "role_type": role_type,
        "is_primary": bool(row.get("is_primary")),
        "is_estimating_contact": bool(row.get("is_estimating_contact")),
        "is_billing_contact": bool(row.get("is_billing_contact")),
        "is_site_contact": bool(row.get("is_site_contact")),
        "is_safety_contact": bool(row.get("is_safety_contact")),
        "is_active": bool(active),
        "status": status,
        "notes": str(row.get("notes") or ""),
        "created_at": str(row.get("created_at") or "")[:19],
        "updated_at": str(row.get("updated_at") or "")[:19],
    }


def _customer_name_by_id() -> dict[str, str]:
    """Map customer UUID -> company name for job/estimate normalization."""
    rows: list[dict[str, Any]] = []
    try:
        from app.services.customers_service import list_customers
    except ImportError:
        from services.customers_service import list_customers  # type: ignore
    try:
        listed, _ = list_customers(demo=[])
        rows = listed or []
    except Exception:
        rows = []
    if not rows:
        try:
            from app.db import fetch_table_admin
        except ImportError:
            from db import fetch_table_admin  # type: ignore
        try:
            rows = fetch_table_admin(
                "customers",
                columns="id,customer_name",
                limit=5000,
                order_by="customer_name",
            ) or []
        except Exception:
            rows = []
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
    loc_id = str(row.get("customer_location_id") or row.get("location_id") or "").strip()
    contact_id = str(row.get("customer_contact_id") or "").strip()
    location_text = str(row.get("location") or "").strip()
    notes = str(row.get("notes") or row.get("description") or row.get("scope_of_work") or "")
    return {
        "id": jid or num,
        "job_number": num,
        "job_name": str(row.get("job_name") or row.get("name") or row.get("description") or "—"),
        "customer": customer,
        "customer_id": str(row.get("customer_id") or "").strip(),
        "customer_location_id": loc_id,
        "location_id": loc_id,
        "customer_contact_id": contact_id,
        "location": location_text,
        "location_name": location_text,
        "estimate_number": str(row.get("estimate_number") or row.get("quote_number") or "—"),
        "supervisor": str(row.get("supervisor") or row.get("supervisor_name") or "—"),
        "status": str(row.get("status") or "Draft"),
        "start_date": str(row.get("start_date") or "")[:10],
        "end_date": end,
        "progress": int(row.get("progress") or row.get("percent_complete") or 0),
        "description": notes,
        "notes": notes,
        "scope": notes,
        "is_deleted": bool(row.get("is_deleted")),
        "completed_at": row.get("completed_at"),
        "cancelled_at": row.get("cancelled_at"),
        "deleted_at": row.get("deleted_at"),
    }


def normalize_estimate(
    row: dict[str, Any],
    *,
    customer_names: dict[str, str] | None = None,
) -> dict[str, Any]:
    eid = str(row.get("id") or "").strip()
    num = str(row.get("quote_number") or row.get("estimate_number") or eid[:8] or "—")
    total_cost = _money_field(row, "total_cost", "subtotal", "material_sell_basis")
    customer_price = _money_field(
        row,
        "customer_price",
        "total",
        "grand_total",
        "proposal_total",
        "final_bid",
    )
    customer = str(row.get("customer_name") or row.get("customer") or "").strip()
    if not customer:
        cid = str(row.get("customer_id") or "").strip()
        if cid:
            names = customer_names if customer_names is not None else _customer_name_by_id()
            customer = names.get(cid, "")
    if not customer:
        customer = "—"
    project_name = str(
        row.get("project_name")
        or row.get("estimate_description")
        or row.get("job_name")
        or row.get("title")
        or ""
    ).strip()
    if not project_name:
        project_name = _estimate_json_get(row, "estimate_description")
    if not project_name:
        project_name = "—"
    return {
        "id": eid or num,
        "estimate_number": num,
        "project_name": project_name,
        "customer": customer,
        "customer_id": str(row.get("customer_id") or ""),
        "customer_location_id": str(row.get("customer_location_id") or ""),
        "customer_contact_id": str(row.get("customer_contact_id") or ""),
        "job_id": str(row.get("job_id") or ""),
        "estimate_date": str(row.get("estimate_date") or row.get("created_at") or "")[:10],
        "expiration_date": str(row.get("expiration_date") or row.get("valid_through") or "")[:10],
        "total": customer_price,
        "customer_price": customer_price,
        "total_cost": total_cost,
        "status": _normalize_estimate_status(row.get("status")),
        "created_by": str(row.get("created_by") or row.get("prepared_by_name") or row.get("prepared_by") or "—"),
        "job_number": str(row.get("job_number") or "—"),
        "description": str(row.get("description") or row.get("scope_of_work") or row.get("notes") or ""),
        "scope_of_work": str(row.get("scope_of_work") or row.get("description") or ""),
        "notes": str(row.get("notes") or ""),
        "subtotal": _money_field(row, "subtotal", "total_cost", "total", "grand_total"),
        "tax": float(row.get("tax_amount") or row.get("tax") or 0),
        "tax_rate": float(row.get("tax_rate") or 0),
        "markup": float(row.get("total_markup") or row.get("markup") or 0),
        "material_cost": float(row.get("material_cost") or row.get("material_total") or 0),
        "labor_cost": float(row.get("labor_cost") or row.get("labor_total") or 0),
        "equipment_cost": float(row.get("equipment_cost") or row.get("equipment_total") or 0),
        "travel_cost": float(row.get("travel_cost") or 0),
        "travel_markup": float(row.get("travel_markup") or 0),
        "travel_price": float(row.get("travel_price") or 0),
        "subcontractor_cost": float(row.get("subcontractor_cost") or 0),
        "other_cost": float(row.get("other_cost") or 0),
        "gross_profit": float(row.get("gross_profit") or 0),
        "gross_margin_percent": float(row.get("gross_margin_percent") or 0),
        "default_material_markup_pct": float(row.get("default_material_markup_pct") or 0),
        "default_labor_markup_pct": float(row.get("default_labor_markup_pct") or 0),
        "default_equipment_markup_pct": float(row.get("default_equipment_markup_pct") or 0),
        "default_travel_markup_pct": float(row.get("default_travel_markup_pct") or 0),
        "default_subcontractor_markup_pct": float(row.get("default_subcontractor_markup_pct") or 0),
        "default_other_markup_pct": float(row.get("default_other_markup_pct") or 0),
        "global_markup_pct": float(row.get("global_markup_pct") or 0),
        "overhead_pct": float(row.get("overhead_pct") or 0),
        "profit_pct": float(row.get("profit_pct") or 0),
        "proposal_show_line_items": bool(row.get("proposal_show_line_items")),
        "proposal_show_category_totals": row.get("proposal_show_category_totals", True),
        "proposal_show_final_price_only": bool(row.get("proposal_show_final_price_only")),
        "approved_at": str(row.get("approved_at") or "")[:19],
        "approved_by": str(row.get("approved_by") or ""),
        "archived_from_estimates": bool(row.get("archived_from_estimates")),
        "converted_to_job_at": str(row.get("converted_to_job_at") or "")[:19],
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
    try:
        from app.services.inventory_display_helpers import resolve_inventory_qr_value, resolve_inventory_sku
    except ImportError:
        from services.inventory_display_helpers import resolve_inventory_qr_value, resolve_inventory_sku  # type: ignore
    iid = str(row.get("id") or "").strip()
    sku = resolve_inventory_sku(row)
    qty = row.get("qty_on_hand")
    if qty is None:
        qty = row.get("quantity_on_hand")
    pricing_guide_id = str(row.get("pricing_guide_id") or row.get("pricing_item_id") or "").strip() or None
    qty_allocated = float(row.get("quantity_allocated") or 0)
    qty_available = row.get("quantity_available")
    if qty_available is None:
        qty_available = max(float(qty or 0) - qty_allocated, 0)
    return {
        "id": iid or sku,
        "sku": sku,
        "barcode": str(row.get("barcode") or ""),
        "qr_code_value": resolve_inventory_qr_value(row),
        "name": str(row.get("name") or row.get("item_name") or "—"),
        "category": str(row.get("category") or "—"),
        "location": str(
            row.get("stock_location")
            or row.get("location")
            or row.get("storage_location")
            or row.get("location_name")
            or "—"
        ),
        "stock_location": str(row.get("stock_location") or row.get("storage_location") or ""),
        "department": str(row.get("department") or "—"),
        "status": str(row.get("status") or "In Stock"),
        "qty_on_hand": int(float(qty or 0)),
        "reorder_point": int(float(row.get("reorder_point") or 0)),
        "unit_cost": float(row.get("unit_cost") or 0),
        "last_purchase_cost": float(row.get("last_purchase_cost") or row.get("unit_cost") or 0),
        "average_cost": float(row.get("average_cost") or row.get("unit_cost") or 0),
        "vendor_id": str(row.get("vendor_id") or "") or None,
        "vendor": str(row.get("vendor") or row.get("vendor_name") or "—"),
        "description": str(row.get("description") or row.get("item_name") or row.get("name") or "—"),
        "pricing_guide_id": pricing_guide_id,
        "pricing_item_id": pricing_guide_id,
        "taxable": row.get("taxable") if row.get("taxable") is not None else True,
        "image_path": str(row.get("image_path") or ""),
        "image_url": str(row.get("image_url") or ""),
        "image_file_name": str(row.get("image_file_name") or ""),
        "image_mime_type": str(row.get("image_mime_type") or ""),
        "image_uploaded_at": str(row.get("image_uploaded_at") or "")[:19],
        "image_uploaded_by": str(row.get("image_uploaded_by") or ""),
        "image_status": str(row.get("image_status") or "missing"),
        "qr_token": str(row.get("qr_token") or "").strip(),
        "quantity_checked_out": float(row.get("quantity_checked_out") or 0),
        "quantity_allocated": qty_allocated,
        "quantity_available": float(qty_available or 0),
    }


def normalize_asset(row: dict[str, Any]) -> dict[str, Any]:
    aid = str(row.get("id") or "").strip()
    num = str(row.get("asset_number") or row.get("asset_id") or row.get("tag") or aid[:8])
    pricing_guide_id = str(row.get("pricing_guide_id") or row.get("pricing_item_id") or "").strip() or None
    return {
        "id": aid or num,
        "asset_number": num,
        "asset_tag": str(row.get("asset_tag") or row.get("asset_id") or row.get("tag") or num),
        "asset_name": str(row.get("asset_name") or row.get("name") or "—"),
        "category": str(row.get("category") or row.get("asset_type") or "—"),
        "location": str(row.get("location") or "—"),
        "department": str(row.get("department") or "—"),
        "status": str(row.get("status") or "In Service"),
        "acquired_date": str(row.get("acquired_date") or row.get("purchase_date") or "")[:10],
        "value": float(row.get("value") or row.get("current_value") or row.get("purchase_cost") or 0),
        "purchase_price": float(row.get("purchase_cost") or row.get("purchase_price") or 0),
        "current_value": float(row.get("current_value") or row.get("purchase_cost") or 0),
        "serial_number": str(row.get("serial_number") or "—"),
        "manufacturer": str(row.get("manufacturer") or "—"),
        "model": str(row.get("model") or "—"),
        "operator": str(row.get("operator") or row.get("assigned_employee") or row.get("assigned_to") or "—"),
        "assigned_to": str(row.get("assigned_to") or row.get("assigned_employee") or row.get("operator") or "—"),
        "assigned_trailer_id": str(row.get("assigned_trailer_id") or "") or None,
        "assigned_job_id": str(row.get("assigned_job_id") or row.get("job_id") or "") or None,
        "service_due": str(row.get("service_due") or row.get("next_service_due") or "")[:10],
        "inspection_due": str(row.get("inspection_due") or "")[:10],
        "manuals": str(row.get("manuals") or ""),
        "certifications": str(row.get("certifications") or ""),
        "pricing_guide_id": pricing_guide_id,
        "pricing_item_id": pricing_guide_id,
        "description": str(row.get("description") or row.get("notes") or ""),
        "qr_code_value": str(row.get("qr_code_value") or "").strip(),
        "qr_token": str(row.get("qr_token") or ""),
        "qr_value": str(row.get("qr_value") or ""),
        "condition": str(row.get("condition") or "Good"),
        "next_service_due": str(row.get("next_service_due") or row.get("maintenance_due_date") or "")[:10],
        "is_rental": bool(row.get("is_rental")),
        "rental_daily_rate": _money_field(row, "rental_daily_rate", "daily_rate"),
        "rental_weekly_rate": _money_field(row, "rental_weekly_rate", "weekly_rate"),
        "rental_monthly_rate": _money_field(row, "rental_monthly_rate"),
        "hourly_rate": _money_field(row, "hourly_rate"),
        "daily_rate": _money_field(row, "daily_rate", "rental_daily_rate"),
        "weekly_rate": _money_field(row, "weekly_rate", "rental_weekly_rate"),
        "image_path": str(row.get("image_path") or ""),
        "image_url": str(row.get("image_url") or ""),
        "image_file_name": str(row.get("image_file_name") or ""),
        "image_mime_type": str(row.get("image_mime_type") or ""),
        "image_uploaded_at": str(row.get("image_uploaded_at") or "")[:19],
        "image_uploaded_by": str(row.get("image_uploaded_by") or ""),
        "image_status": str(row.get("image_status") or "missing"),
        "photo_path": str(row.get("photo_path") or ""),
        "photo_url": str(row.get("photo_url") or ""),
        "is_kit": bool(row.get("is_kit")),
        "kit_type": str(row.get("kit_type") or ""),
        "kit_status": str(row.get("kit_status") or "Active"),
        "total_kit_value": float(row.get("total_kit_value") or 0),
        "last_kit_audit_at": str(row.get("last_kit_audit_at") or "")[:19],
        "assigned_to_employee_id": str(row.get("assigned_to_employee_id") or "").strip() or None,
        "assigned_to_name": str(row.get("assigned_to_name") or ""),
        "assigned_to_phone": str(row.get("assigned_to_phone") or ""),
        "assigned_job_id": str(row.get("assigned_job_id") or "").strip() or None,
        "include_in_pricing_guide": (
            bool(row.get("include_in_pricing_guide"))
            if "include_in_pricing_guide" in row
            else True
        ),
    }


def normalize_employee(row: dict[str, Any]) -> dict[str, Any]:
    eid = str(row.get("id") or "").strip()
    active = row.get("is_active", row.get("status") == "Active")
    status = "Active" if active in (True, "true", "Active", 1) else "Inactive"
    if str(row.get("status") or "") in {"Active", "Inactive"}:
        status = str(row.get("status"))
    is_employee_raw = row.get("is_employee")
    is_employee = bool(is_employee_raw) if is_employee_raw is not None else True
    phone = ""
    for key in ("phone", "phone_number", "mobile", "cell", "contact_phone"):
        val = str(row.get(key) or "").strip()
        if val and val not in {"—", "None", "-"}:
            phone = val
            break
    return {
        "id": eid,
        "name": str(row.get("name") or row.get("full_name") or "—"),
        "full_name": str(row.get("name") or row.get("full_name") or "—"),
        "email": str(row.get("email") or "—"),
        "role": str(row.get("role") or row.get("position") or "Employee"),
        "position": str(row.get("position") or row.get("role") or "—"),
        "trade": str(row.get("trade") or "—"),
        "employee_number": str(row.get("employee_number") or "—"),
        "hire_date": str(row.get("hire_date") or "")[:10] or "—",
        "department": str(row.get("department") or "—"),
        "status": status,
        "is_employee": is_employee,
        "last_login": str(row.get("last_login") or "—"),
        "phone": phone or "—",
        "username": str(row.get("username") or eid[:8]),
        "member_since": str(row.get("created_at") or row.get("member_since") or row.get("hire_date") or "")[:10],
    }


def normalize_cert(row: dict[str, Any], employee_name: str = "") -> dict[str, Any]:
    try:
        from app.services.certification_helpers import compute_certification_status
    except ImportError:
        from services.certification_helpers import compute_certification_status  # type: ignore

    normalized = {
        "id": str(row.get("id") or ""),
        "employee_id": str(row.get("employee_id") or ""),
        "employee_name": employee_name or str(row.get("employee_name") or ""),
        "cert_type": str(
            row.get("cert_type")
            or row.get("certification_type")
            or row.get("type")
            or ""
        ),
        "cert_number": str(
            row.get("cert_number")
            or row.get("certification_number")
            or row.get("number")
            or ""
        ),
        "issuer": str(row.get("issuer") or row.get("issuing_organization") or ""),
        "issue_date": str(row.get("issue_date") or "")[:10],
        "expiration_date": str(row.get("expiration_date") or "")[:10],
        "status": str(row.get("status") or "Active"),
        "attachment_path": str(row.get("attachment_path") or ""),
        "attachment_url": str(row.get("attachment_url") or ""),
        "attachment_file_name": str(row.get("attachment_file_name") or ""),
        "attachment_mime_type": str(row.get("attachment_mime_type") or ""),
        "attachment_uploaded_at": str(row.get("attachment_uploaded_at") or "")[:19],
        "attachment_uploaded_by": str(row.get("attachment_uploaded_by") or ""),
        "notes": str(row.get("notes") or ""),
        "created_at": str(row.get("created_at") or "")[:19],
        "updated_at": str(row.get("updated_at") or "")[:19],
    }
    normalized["status"] = compute_certification_status(normalized)
    return normalized


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
    jid = row.get("job_id")
    return {
        "id": str(row.get("id") or ""),
        "title": str(row.get("title") or ""),
        "status": status,
        "priority": pri,
        "assigned_to": str(row.get("assignee_name") or row.get("assigned_to") or "—"),
        "job_id": str(jid).strip() if jid else None,
        "linked_job": str(row.get("job_label") or row.get("linked_job") or "— None —"),
        "linked_estimate": str(row.get("estimate_label") or row.get("linked_estimate") or "— None —"),
        "due_date": str(row.get("due_date") or "")[:10],
        "description": str(row.get("description") or ""),
        "notes": str(row.get("notes") or ""),
        "activity": list(row.get("activity") or []),
    }


def normalize_timekeeping_summary(row: dict[str, Any], week_start: date) -> dict[str, Any]:
    return {
        "id": str(row.get("employee_id") or row.get("id") or ""),
        "week_id": str(row.get("id") or ""),
        "name": str(row.get("name") or row.get("employee_name") or ""),
        "department": str(row.get("department") or ""),
        "week_start": str(row.get("week_start") or week_start.isoformat())[:10],
        "st_total": float(row.get("st_total") or 0),
        "ot_total": float(row.get("ot_total") or 0),
        "dt_total": float(row.get("dt_total") or 0),
        "status": str(row.get("status") or "Pending"),
        "approved_by": str(row.get("approved_by") or ""),
        "approved_at": str(row.get("approved_at") or "")[:19],
        "notes": str(row.get("notes") or ""),
    }


# --- Reads ---


def list_jobs(*, demo: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    rows, used = fetch_list("jobs", order_by="job_number", normalize=normalize_job, demo=demo)
    return rows if rows or not used else demo, used


def list_estimates(*, demo: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    rows, err = fetch_rows("estimates", limit=5000)
    if not rows:
        try:
            from app.db import fetch_table_admin
        except ImportError:
            from db import fetch_table_admin  # type: ignore
        try:
            rows = fetch_table_admin("estimates", limit=5000, order_by="quote_number") or []
        except Exception:
            rows = []
    if not rows:
        return (demo if demo else []), True
    cust_names = _customer_name_by_id()
    out = [normalize_estimate(r, customer_names=cust_names) for r in rows]
    try:
        from app.services.estimate_job_workflow_service import enrich_estimates_with_job_numbers

        out = enrich_estimates_with_job_numbers(out)
    except Exception:
        pass
    out.sort(key=lambda r: str(r.get("estimate_number") or ""))
    return out, False


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
    demo_match = [normalize_cert(c) for c in demo if c.get("employee_id") == eid] if eid else [normalize_cert(c) for c in demo]
    return (demo_match if demo_match else [normalize_cert(c) for c in demo[:2]]), True


def list_all_certifications(*, demo: list[dict[str, Any]], employees: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    rows, used = fetch_list("employee_certifications", demo=[], alt_tables=("certifications",))
    if rows and not used:
        name_map = {str(e.get("id")): str(e.get("name")) for e in employees}
        return [normalize_cert(r, name_map.get(str(r.get("employee_id") or ""), "")) for r in rows], False
    out = []
    for c in demo:
        emp = next((e for e in employees if e.get("id") == c.get("employee_id")), None)
        out.append(normalize_cert(c, str((emp or {}).get("name") or "")))
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


def list_timekeeping_days(employee_id: str, week_start: date) -> list[dict[str, Any]]:
    eid = str(employee_id or "").strip()
    if not eid:
        return []
    ws = week_start.isoformat()
    rows, err = fetch_rows("employee_timekeeping_days", limit=100, order_by="work_date")
    if err:
        return []
    return [
        r
        for r in rows
        if str(r.get("employee_id") or "") == eid and str(r.get("week_start") or "")[:10] == ws
    ]


def _find_timekeeping_week(employee_id: str, week_start: date) -> dict[str, Any] | None:
    eid = str(employee_id or "").strip()
    if not eid:
        return None
    ws = week_start.isoformat()
    rows, err = fetch_rows("employee_timekeeping_weeks", limit=500)
    if err:
        return None
    for row in rows:
        if str(row.get("employee_id") or "") == eid and str(row.get("week_start") or "")[:10] == ws:
            return row
    return None


# --- Writes (map UI -> DB) ---


def save_job(ui: dict[str, Any], *, row_id: str | None = None) -> ServiceResult:
    customer_name = str(ui.get("customer") or "").strip()
    customer_id = _resolve_customer_id_for_job(ui)
    if customer_name and not customer_id:
        return ServiceResult(ok=False, error=f"Customer not found: {customer_name}")

    job_number = str(ui.get("job_number") or "").strip()
    if not row_id and not job_number:
        return ServiceResult(ok=False, error="Job number is required.")

    payload: dict[str, Any] = {
        "job_number": job_number or ui.get("job_number"),
        "job_name": ui.get("job_name"),
        "status": ui.get("status"),
        "supervisor": ui.get("supervisor"),
        "project_manager": ui.get("project_manager"),
        "start_date": ui.get("start_date") or None,
        "target_completion_date": ui.get("end_date") or None,
        "notes": ui.get("description") or ui.get("notes") or "",
    }
    if ui.get("progress") is not None:
        payload["percent_complete"] = int(ui.get("progress") or 0)
    if customer_id:
        payload["customer_id"] = customer_id

    cols = table_column_names("jobs")
    loc_id = str(ui.get("customer_location_id") or ui.get("location_id") or "").strip()
    contact_id = str(ui.get("customer_contact_id") or "").strip()
    if not cols or "customer_location_id" in cols:
        payload["customer_location_id"] = loc_id or None
    if cols and "location_id" in cols:
        payload["location_id"] = loc_id or None
    elif not cols and loc_id:
        payload["location_id"] = loc_id
    if not cols or "customer_contact_id" in cols:
        payload["customer_contact_id"] = contact_id or None

    if not cols or "location" in cols:
        if loc_id:
            try:
                from app.services.job_from_estimate import _location_text_from_customer_location
            except ImportError:
                from services.job_from_estimate import _location_text_from_customer_location  # type: ignore
            loc_text = _location_text_from_customer_location(loc_id)
            payload["location"] = loc_text or str(ui.get("location") or "").strip()
        else:
            payload["location"] = str(ui.get("location") or "").strip()

    if row_id:
        return update_row("jobs", payload, {"id": row_id})
    return insert_row("jobs", payload)


def save_estimate(ui: dict[str, Any], *, row_id: str | None = None) -> ServiceResult:
    quote_number = str(ui.get("estimate_number") or ui.get("quote_number") or "").strip()
    if not quote_number and not row_id:
        return ServiceResult(ok=False, error="Estimate number is required.")
    project_name = str(ui.get("project_name") or ui.get("estimate_description") or "").strip()
    scope_text = str(ui.get("description") or ui.get("scope_of_work") or "").strip()
    payload = {
        "quote_number": quote_number or None,
        "project_name": project_name or None,
        "job_name": project_name or None,
        "estimate_description": project_name[:500] if project_name else None,
        "customer_name": ui.get("customer"),
        "customer_id": ui.get("customer_id") or None,
        "customer_location_id": ui.get("customer_location_id") or None,
        "customer_contact_id": ui.get("customer_contact_id") or None,
        "job_id": ui.get("job_id") or None,
        "status": ui.get("status") or "Draft",
        "estimate_date": ui.get("estimate_date") or None,
        "expiration_date": ui.get("expiration_date") or None,
        "prepared_by_name": ui.get("created_by") or ui.get("prepared_by_name"),
        "description": scope_text or None,
        "scope_of_work": scope_text or None,
        "notes": ui.get("notes") or scope_text or "",
        "subtotal": ui.get("subtotal") or ui.get("total_cost") or 0,
        "total_cost": ui.get("total_cost") or ui.get("subtotal") or 0,
        "tax": ui.get("tax") or ui.get("tax_amount") or 0,
        "tax_amount": ui.get("tax_amount") or ui.get("tax") or 0,
        "tax_rate": ui.get("tax_rate") or 0,
        "markup": ui.get("markup") or ui.get("total_markup") or 0,
        "total_markup": ui.get("total_markup") or ui.get("markup") or 0,
        "total": ui.get("total") or ui.get("customer_price") or 0,
        "customer_price": ui.get("customer_price") or ui.get("total") or 0,
        "material_cost": ui.get("material_cost"),
        "labor_cost": ui.get("labor_cost"),
        "equipment_cost": ui.get("equipment_cost"),
        "travel_cost": ui.get("travel_cost"),
        "travel_markup": ui.get("travel_markup"),
        "travel_price": ui.get("travel_price"),
        "subcontractor_cost": ui.get("subcontractor_cost"),
        "other_cost": ui.get("other_cost"),
        "gross_profit": ui.get("gross_profit"),
        "gross_margin_percent": ui.get("gross_margin_percent"),
        "default_material_markup_pct": ui.get("default_material_markup_pct"),
        "default_labor_markup_pct": ui.get("default_labor_markup_pct"),
        "default_equipment_markup_pct": ui.get("default_equipment_markup_pct"),
        "default_travel_markup_pct": ui.get("default_travel_markup_pct"),
        "default_subcontractor_markup_pct": ui.get("default_subcontractor_markup_pct"),
        "default_other_markup_pct": ui.get("default_other_markup_pct"),
        "global_markup_pct": ui.get("global_markup_pct"),
        "overhead_pct": ui.get("overhead_pct"),
        "profit_pct": ui.get("profit_pct"),
        "proposal_show_line_items": ui.get("proposal_show_line_items"),
        "proposal_show_category_totals": ui.get("proposal_show_category_totals"),
        "proposal_show_final_price_only": ui.get("proposal_show_final_price_only"),
    }
    payload = {k: v for k, v in payload.items() if v is not None}
    cols = table_column_names("estimates")
    if cols and "customer_name" not in cols:
        payload.pop("customer_name", None)
    if row_id:
        result = update_row("estimates", payload, {"id": row_id})
    else:
        result = insert_row("estimates", payload)
        if result.ok:
            eid = str((result.data or {}).get("id") or "").strip()
            if eid:
                try:
                    from app.services.estimate_job_workflow_service import (
                        auto_create_linked_job_after_estimate_insert,
                    )
                except ImportError:
                    from services.estimate_job_workflow_service import (  # type: ignore
                        auto_create_linked_job_after_estimate_insert,
                    )
                link_result = auto_create_linked_job_after_estimate_insert(eid, estimate_row=result.data)
                if not link_result.ok and link_result.error_code not in ("duplicate",):
                    if link_result.error_code == "no_customer":
                        result = ServiceResult(
                            ok=True,
                            data=result.data,
                            error=None,
                        )
                    else:
                        return ServiceResult(
                            ok=False,
                            error=link_result.message or "Estimate saved but linked job could not be created.",
                            data=result.data,
                        )
    if result.ok:
        clear_all_data_caches()
    return result


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
    try:
        from app.services.inventory_display_helpers import resolve_inventory_qr_value, resolve_inventory_sku
    except ImportError:
        from services.inventory_display_helpers import resolve_inventory_qr_value, resolve_inventory_sku  # type: ignore
    sku = str(ui.get("sku") or ui.get("item_number") or "").strip()
    payload: dict[str, Any] = {
        "item_name": ui.get("name") or ui.get("item_name"),
        "sku": sku or None,
        "category": ui.get("category"),
        "storage_location": ui.get("location"),
        "department": ui.get("department") or "",
        "unit_cost": ui.get("unit_cost"),
        "vendor": ui.get("vendor"),
        "status": ui.get("status") or "In Stock",
    }
    qty = ui.get("qty_on_hand")
    if qty is not None:
        payload["quantity_on_hand"] = float(qty or 0)
    elif not row_id:
        payload["quantity_on_hand"] = 0.0
    reorder = ui.get("reorder_point")
    if reorder is not None:
        payload["reorder_point"] = int(float(reorder or 0))
    elif not row_id:
        payload["reorder_point"] = 0
    for key in (
        "image_path",
        "image_url",
        "image_file_name",
        "image_mime_type",
        "image_uploaded_at",
        "image_uploaded_by",
    ):
        if key in ui:
            payload[key] = ui.get(key)
    if row_id:
        rid = str(row_id).strip()
        if not payload.get("sku"):
            payload["sku"] = resolve_inventory_sku({"id": rid, **ui})
        if not str(ui.get("qr_code_value") or "").strip():
            payload["qr_code_value"] = resolve_inventory_qr_value({"id": rid, **ui})
        return update_row("inventory_items", payload, {"id": rid})
    result = insert_row("inventory_items", payload)
    return result


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
        "include_in_pricing_guide": bool(ui.get("include_in_pricing_guide")),
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
        "phone": ui.get("phone"),
        "username": ui.get("username"),
        "crew": ui.get("crew") or "",
        "position": ui.get("position") or ui.get("role") or "",
        "trade": ui.get("trade") or "",
        "hire_date": ui.get("hire_date") or None,
        "employee_number": ui.get("employee_number") or None,
        "status": ui.get("status") or ("Active" if active else "Inactive"),
        "is_active": active,
        "notes": ui.get("notes") or "",
    }
    if "department" in ui:
        payload["department"] = ui.get("department")
    if "is_employee" in ui:
        payload["is_employee"] = bool(ui.get("is_employee"))
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
    try:
        from app.services.certification_helpers import compute_certification_status, date_to_iso
    except ImportError:
        from services.certification_helpers import compute_certification_status, date_to_iso  # type: ignore

    payload = {
        "employee_id": ui.get("employee_id"),
        "cert_type": ui.get("cert_type") or ui.get("certification_type"),
        "cert_number": ui.get("cert_number") or ui.get("certification_number") or "",
        "issuer": ui.get("issuer") or ui.get("issuing_organization") or "",
        "issue_date": date_to_iso(ui.get("issue_date")),
        "expiration_date": date_to_iso(ui.get("expiration_date")),
        "notes": ui.get("notes") or "",
        "attachment_path": ui.get("attachment_path") or "",
        "attachment_url": ui.get("attachment_url") or "",
        "attachment_file_name": ui.get("attachment_file_name") or "",
        "attachment_mime_type": ui.get("attachment_mime_type") or "",
        "attachment_uploaded_at": ui.get("attachment_uploaded_at") or None,
        "attachment_uploaded_by": ui.get("attachment_uploaded_by") or None,
    }
    for key in (
        "attachment_path",
        "attachment_url",
        "attachment_file_name",
        "attachment_mime_type",
        "attachment_uploaded_at",
        "attachment_uploaded_by",
    ):
        if key not in ui:
            payload.pop(key, None)
    manual_status = str(ui.get("status") or "").strip()
    if manual_status == "Not Required":
        payload["status"] = "Not Required"
    else:
        payload["status"] = compute_certification_status(
            {
                **payload,
                "cert_type": payload["cert_type"],
                "expiration_date": payload["expiration_date"],
            }
        )
    table = "employee_certifications"
    if row_id:
        result = update_row(table, payload, {"id": row_id})
    else:
        result = insert_row(table, payload)
    if result.ok:
        clear_all_data_caches()
    return result


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
    linked_job = str(ui.get("linked_job") or "").strip()
    job_id = ui.get("job_id")
    if job_id is not None:
        resolved_job_id = str(job_id).strip() if job_id else None
    elif linked_job and linked_job not in {"— None —", "None", "—", "-"}:
        try:
            from app.services.jobs_service import resolve_job_id_from_label
        except ImportError:
            from services.jobs_service import resolve_job_id_from_label  # type: ignore
        resolved_job_id = resolve_job_id_from_label(linked_job)
    else:
        resolved_job_id = None
    payload = {
        "title": ui.get("title"),
        "description": ui.get("description"),
        "status": status,
        "priority": pri,
        "due_date": ui.get("due_date") or None,
        "assignee_name": ui.get("assigned_to"),
        "job_id": resolved_job_id,
        "job_label": "" if linked_job in {"— None —", "None", "—", "-", ""} else linked_job,
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
    result = delete_row("employee_certifications", {"id": row_id})
    if result.ok:
        clear_all_data_caches()
    return result


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
        "status": "Pending" if str(ui_summary.get("status") or "Pending") == "Draft" else (ui_summary.get("status") or "Pending"),
        "notes": ui_summary.get("notes") or "",
    }
    existing = _find_timekeeping_week(employee_id, week_start)
    if existing and existing.get("id"):
        result = update_row("employee_timekeeping_weeks", payload, {"id": existing["id"]})
    else:
        result = insert_row("employee_timekeeping_weeks", payload)
    if result.ok:
        clear_all_data_caches()
    return result


def submit_timekeeping_week(employee_id: str, week_start: date) -> ServiceResult:
    existing = _find_timekeeping_week(employee_id, week_start)
    if not existing:
        return ServiceResult(ok=False, error="Save hours before submitting for approval.")
    for day in list_timekeeping_days(employee_id, week_start):
        day_id = str(day.get("id") or "")
        if not day_id:
            continue
        hours = float(day.get("st_hours") or 0) + float(day.get("ot_hours") or 0) + float(day.get("dt_hours") or 0)
        if hours <= 0:
            continue
        if str(day.get("status") or "Draft") in ("Draft", "Rejected"):
            submit_timekeeping_day(day_id)
    payload = {
        "status": "Pending",
        "approved_by": None,
        "approved_at": None,
    }
    result = update_row("employee_timekeeping_weeks", payload, {"id": existing["id"]})
    if result.ok:
        clear_all_data_caches()
    return result


def approve_timekeeping_week(employee_id: str, week_start: date, *, approved_by: str) -> ServiceResult:
    existing = _find_timekeeping_week(employee_id, week_start)
    if not existing:
        return ServiceResult(ok=False, error="No timecard found for this week.")
    if str(existing.get("status") or "") != "Pending":
        return ServiceResult(ok=False, error="Only pending timecards can be approved.")
    approver = str(approved_by or "").strip()
    if not approver:
        return ServiceResult(ok=False, error="Missing approver profile.")
    for day in list_timekeeping_days(employee_id, week_start):
        if str(day.get("status") or "") == "Pending" and day.get("id"):
            update_timekeeping_day_status(str(day["id"]), status="Approved", approved_by=approver)
    payload = {
        "status": "Approved",
        "approved_by": approver,
        "approved_at": datetime.now(timezone.utc).isoformat(),
    }
    result = update_row("employee_timekeeping_weeks", payload, {"id": existing["id"]})
    if result.ok:
        clear_all_data_caches()
    return result


def reject_timekeeping_week(
    employee_id: str,
    week_start: date,
    *,
    approved_by: str,
    notes: str = "",
) -> ServiceResult:
    existing = _find_timekeeping_week(employee_id, week_start)
    if not existing:
        return ServiceResult(ok=False, error="No timecard found for this week.")
    if str(existing.get("status") or "") != "Pending":
        return ServiceResult(ok=False, error="Only pending timecards can be rejected.")
    approver = str(approved_by or "").strip()
    if not approver:
        return ServiceResult(ok=False, error="Missing approver profile.")
    payload: dict[str, Any] = {
        "status": "Rejected",
        "approved_by": approver,
        "approved_at": datetime.now(timezone.utc).isoformat(),
    }
    note = str(notes or "").strip()
    if note:
        payload["notes"] = note
    for day in list_timekeeping_days(employee_id, week_start):
        if str(day.get("status") or "") == "Pending" and day.get("id"):
            update_timekeeping_day_status(str(day["id"]), status="Rejected", approved_by=approver)
    result = update_row("employee_timekeeping_weeks", payload, {"id": existing["id"]})
    if result.ok:
        clear_all_data_caches()
    return result


def save_timekeeping_day(ui: dict[str, Any], *, row_id: str | None = None) -> ServiceResult:
    payload: dict[str, Any] = {
        "employee_id": ui.get("employee_id"),
        "week_start": ui.get("week_start"),
        "work_date": ui.get("work_date"),
        "job_id": ui.get("job_id") or None,
        "job_label": ui.get("job_label") or "",
        "st_hours": ui.get("st_hours") or 0,
        "ot_hours": ui.get("ot_hours") or 0,
        "dt_hours": ui.get("dt_hours") or 0,
        "notes": ui.get("notes") or "",
        "status": ui.get("status") or "Draft",
    }
    if row_id:
        result = update_row("employee_timekeeping_days", payload, {"id": row_id})
    else:
        result = insert_row("employee_timekeeping_days", payload)
    if result.ok:
        clear_all_data_caches()
    return result


def _derive_week_status_from_days(days: list[dict[str, Any]]) -> str:
    def _hours(row: dict[str, Any]) -> float:
        try:
            return float(row.get("st_hours") or 0) + float(row.get("ot_hours") or 0) + float(row.get("dt_hours") or 0)
        except (TypeError, ValueError):
            return 0.0

    active = [str(row.get("status") or "Draft") for row in days if _hours(row) > 0]
    if not active:
        return "Pending"
    statuses = {s for s in active}
    if statuses == {"Approved"}:
        return "Approved"
    if "Rejected" in statuses:
        return "Rejected"
    if "Pending" in statuses:
        return "Pending"
    return "Pending"


def sync_timekeeping_week_from_days(employee_id: str, week_start: date) -> ServiceResult:
    eid = str(employee_id or "").strip()
    if not eid:
        return ServiceResult(ok=False, error="Missing employee id.")
    days = list_timekeeping_days(eid, week_start)
    st_total = sum(float(row.get("st_hours") or 0) for row in days)
    ot_total = sum(float(row.get("ot_hours") or 0) for row in days)
    dt_total = sum(float(row.get("dt_hours") or 0) for row in days)
    week_status = _derive_week_status_from_days(days)
    return save_timekeeping_week(
        eid,
        week_start,
        {
            "st_total": st_total,
            "ot_total": ot_total,
            "dt_total": dt_total,
            "status": week_status,
        },
    )


def update_timekeeping_day_status(
    day_id: str,
    *,
    status: str,
    approved_by: str | None = None,
    clear_approval: bool = False,
) -> ServiceResult:
    rid = str(day_id or "").strip()
    if not rid:
        return ServiceResult(ok=False, error="Missing day id.")
    payload: dict[str, Any] = {"status": status}
    if clear_approval:
        payload["approved_by"] = None
        payload["approved_at"] = None
    elif approved_by:
        payload["approved_by"] = approved_by
        payload["approved_at"] = datetime.now(timezone.utc).isoformat()
    result = update_row("employee_timekeeping_days", payload, {"id": rid})
    if result.ok:
        clear_all_data_caches()
    return result


def submit_timekeeping_day(day_id: str) -> ServiceResult:
    return update_timekeeping_day_status(day_id, status="Pending", clear_approval=True)


def approve_timekeeping_day(day_id: str, *, approved_by: str) -> ServiceResult:
    approver = str(approved_by or "").strip()
    if not approver:
        return ServiceResult(ok=False, error="Missing approver profile.")
    return update_timekeeping_day_status(day_id, status="Approved", approved_by=approver)


def reject_timekeeping_day(day_id: str, *, approved_by: str) -> ServiceResult:
    approver = str(approved_by or "").strip()
    if not approver:
        return ServiceResult(ok=False, error="Missing approver profile.")
    return update_timekeeping_day_status(day_id, status="Rejected", approved_by=approver)


def delete_estimate_line_item(row_id: str) -> ServiceResult:
    return delete_row("estimate_line_items", {"id": row_id})


def delete_employee_document(row_id: str) -> ServiceResult:
    return delete_row("employee_documents", {"id": row_id})


def list_customers(*, demo: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    return fetch_list("customers", order_by="customer_name", normalize=normalize_customer, demo=demo)


def _is_unknown_column_error(message: str | None) -> bool:
    if not message:
        return False
    text = message.lower()
    return "pgrst204" in text or ("could not find" in text and "column" in text)


def _customer_location_write_payloads(ui: dict[str, Any]) -> list[dict[str, Any]]:
    """Build insert/update payloads from newest to oldest supported schemas."""
    cid = str(ui.get("customer_id") or "").strip()
    name = str(ui.get("location_name") or ui.get("site_name") or "").strip()
    status = str(ui.get("status") or "Active").strip()
    active = status.lower() in ("active", "true", "1")
    addr1 = str(ui.get("address_line_1") or ui.get("address") or "").strip()
    addr2 = str(ui.get("address_line_2") or "").strip()
    city = str(ui.get("city") or "").strip()
    state = str(ui.get("state") or "").strip()
    zip_code = str(ui.get("zip") or "").strip()
    notes = str(ui.get("notes") or "").strip()

    extended = {
        "customer_id": cid,
        "site_name": name,
        "location_name": name,
        "location_type": str(ui.get("location_type") or "Other").strip(),
        "address_line_1": addr1,
        "address_line_2": addr2,
        "address": addr1,
        "city": city,
        "state": state,
        "zip": zip_code,
        "country": str(ui.get("country") or "USA").strip(),
        "phone": str(ui.get("phone") or "").strip(),
        "email": str(ui.get("email") or "").strip(),
        "is_primary": bool(ui.get("is_primary")),
        "is_billing": bool(ui.get("is_billing")),
        "is_shipping": bool(ui.get("is_shipping")),
        "is_active": active,
        "status": status,
        "notes": notes,
    }
    modern_024 = {
        "customer_id": cid,
        "location_name": name,
        "address": addr1,
        "city": city,
        "state": state,
        "zip": zip_code,
        "is_active": active,
    }
    legacy_001 = {
        "customer_id": cid,
        "site_name": name,
        "address_line1": addr1,
        "address_line2": addr2,
        "city": city,
        "state": state,
        "zip": zip_code,
        "is_active": active,
        "notes": notes,
    }
    return [extended, modern_024, legacy_001]


def _write_customer_location(
    payloads: list[dict[str, Any]],
    *,
    row_id: str | None = None,
) -> ServiceResult:
    last_result = ServiceResult(ok=False, error="Could not save location.")
    for payload in payloads:
        if row_id:
            result = update_row("customer_locations", payload, {"id": row_id})
        else:
            result = insert_row("customer_locations", payload)
        if result.ok:
            return result
        last_result = result
        if not _is_unknown_column_error(result.error):
            return result
    return last_result


def _fetch_rows_by_customer_id(
    table: str,
    customer_id: str,
    *,
    limit: int = 500,
) -> tuple[list[dict[str, Any]], str | None]:
    cid = str(customer_id or "").strip()
    if not cid:
        return [], None
    try:
        from app.db import fetch_by_match
    except ImportError:
        from db import fetch_by_match  # type: ignore
    try:
        rows = fetch_by_match(table, {"customer_id": cid}, limit=limit) or []
        return rows, None
    except Exception as exc:
        return [], str(exc)


def list_customer_locations(customer_id: str, *, demo: list[dict[str, Any]] | None = None) -> tuple[list[dict[str, Any]], bool]:
    cid = str(customer_id or "").strip()
    rows, err = _fetch_rows_by_customer_id("customer_locations", cid, limit=500)
    if err:
        demo_rows = [normalize_customer_location(r) for r in (demo or []) if str(r.get("customer_id")) == cid]
        return demo_rows, True
    out = [normalize_customer_location(r) for r in rows if r]
    out.sort(
        key=lambda r: (
            str(r.get("location_name") or r.get("site_name") or "").lower(),
            str(r.get("id") or ""),
        )
    )
    return out, False


def save_customer_location(ui: dict[str, Any], *, row_id: str | None = None) -> ServiceResult:
    cid = str(ui.get("customer_id") or "").strip()
    if not cid:
        return ServiceResult(ok=False, error="Customer is required.")
    name = str(ui.get("location_name") or ui.get("site_name") or "").strip()
    if not name:
        return ServiceResult(ok=False, error="Location name is required.")
    payloads = _customer_location_write_payloads({**ui, "customer_id": cid})
    result = _write_customer_location(payloads, row_id=row_id)
    loc_id = str(row_id or "").strip()
    if result.ok and not loc_id:
        row = result.data if isinstance(result.data, dict) else {}
        loc_id = str(row.get("id") or "").strip()
    if result.ok and bool(ui.get("is_primary")) and loc_id:
        _apply_primary_location_scope(customer_id=cid, location_id=loc_id)
    return result


def _apply_primary_location_scope(*, customer_id: str, location_id: str) -> None:
    cid = str(customer_id or "").strip()
    keep = str(location_id or "").strip()
    if not cid or not keep:
        return
    rows, err = fetch_rows("customer_locations", limit=500)
    if err:
        return
    for row in rows:
        if str(row.get("customer_id") or "").strip() != cid:
            continue
        rid = str(row.get("id") or "").strip()
        if not rid or rid == keep:
            continue
        if row.get("is_primary"):
            clear_result = update_row("customer_locations", {"is_primary": False}, {"id": rid})
            if not clear_result.ok and _is_unknown_column_error(clear_result.error):
                return
    set_result = update_row("customer_locations", {"is_primary": True}, {"id": keep})
    if not set_result.ok and _is_unknown_column_error(set_result.error):
        return


def delete_customer_location(row_id: str) -> ServiceResult:
    return delete_row("customer_locations", {"id": row_id})


def list_customer_contacts(
    customer_id: str,
    *,
    location_id: str | None = None,
    demo: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], bool]:
    cid = str(customer_id or "").strip()
    loc_filter = str(location_id or "").strip()
    rows, err = fetch_rows("customer_contacts", limit=500, alt_tables=("contacts",))
    if err:
        demo_rows = [
            normalize_customer_contact(r)
            for r in (demo or [])
            if str(r.get("customer_id")) == cid
            and (not loc_filter or str(r.get("customer_location_id") or r.get("location_id") or "") == loc_filter)
        ]
        return demo_rows, True
    out = []
    for r in rows:
        if str(r.get("customer_id")) != cid:
            continue
        if loc_filter:
            row_loc = str(r.get("customer_location_id") or r.get("location_id") or "").strip()
            if row_loc != loc_filter:
                continue
        out.append(normalize_customer_contact(r))
    return out, False


def _customer_contact_write_payloads(ui: dict[str, Any]) -> list[dict[str, Any]]:
    """Build insert/update payloads from newest to oldest supported schemas."""
    cid = str(ui.get("customer_id") or "").strip()
    name = str(ui.get("full_name") or ui.get("contact_name") or ui.get("name") or "").strip()
    loc_id = str(ui.get("location_id") or ui.get("customer_location_id") or "").strip()
    status = str(ui.get("status") or "Active").strip()
    active = status.lower() in ("active", "true", "1")
    is_primary = bool(ui.get("is_primary")) and active
    title = str(ui.get("title") or "").strip()
    role_type = str(ui.get("role_type") or title or "Other").strip()
    notes = str(ui.get("notes") or "").strip()
    email = str(ui.get("email") or "").strip()
    phone = str(ui.get("phone") or "").strip()
    mobile = str(ui.get("mobile") or "").strip()

    extended_063 = {
        "customer_id": cid,
        "contact_name": name,
        "full_name": name,
        "title": title or role_type,
        "role": role_type,
        "role_type": role_type,
        "email": email,
        "phone": phone,
        "mobile": mobile,
        "is_active": active,
        "status": status,
        "is_primary": is_primary,
        "is_estimating_contact": bool(ui.get("is_estimating_contact")),
        "is_billing_contact": bool(ui.get("is_billing_contact")),
        "is_site_contact": bool(ui.get("is_site_contact")),
        "is_safety_contact": bool(ui.get("is_safety_contact")),
        "notes": notes,
        "customer_location_id": loc_id,
        "location_id": loc_id,
    }
    mid_025_018 = {
        "customer_id": cid,
        "contact_name": name,
        "title": title or role_type,
        "role": role_type,
        "email": email,
        "phone": phone,
        "mobile": mobile,
        "is_active": active,
        "is_primary": is_primary,
        "notes": notes,
        "customer_location_id": loc_id,
    }
    base_016 = {
        "customer_id": cid,
        "contact_name": name,
        "role": role_type,
        "email": email,
        "phone": phone,
        "is_active": active,
        "is_primary": is_primary,
        "notes": notes,
    }
    return [extended_063, mid_025_018, base_016]


def _write_customer_contact(
    payloads: list[dict[str, Any]],
    *,
    row_id: str | None = None,
) -> ServiceResult:
    last_result = ServiceResult(ok=False, error="Could not save contact.")
    for payload in payloads:
        if row_id:
            result = update_row("customer_contacts", payload, {"id": row_id})
        else:
            result = insert_row("customer_contacts", payload)
        if result.ok:
            return result
        last_result = result
        if not _is_unknown_column_error(result.error):
            return result
    return last_result


def save_customer_contact(ui: dict[str, Any], *, row_id: str | None = None) -> ServiceResult:
    cid = str(ui.get("customer_id") or "").strip()
    if not cid:
        return ServiceResult(ok=False, error="Customer is required.")
    name = str(ui.get("full_name") or ui.get("contact_name") or ui.get("name") or "").strip()
    if not name:
        return ServiceResult(ok=False, error="Contact name is required.")
    loc_id = str(ui.get("location_id") or ui.get("customer_location_id") or "").strip()
    if not loc_id:
        return ServiceResult(ok=False, error="Location is required for every contact.")
    status = str(ui.get("status") or "Active").strip()
    active = status.lower() in ("active", "true", "1")
    is_primary = bool(ui.get("is_primary")) and active
    payloads = _customer_contact_write_payloads({**ui, "customer_id": cid})
    result = _write_customer_contact(payloads, row_id=row_id)
    contact_id = str(row_id or "").strip()
    if result.ok and not contact_id:
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
    status = str(ui.get("status") or "Active").strip()
    active = status.lower() in ("active", "true", "1")
    company = ui.get("company_name") or ui.get("customer_name") or ui.get("name")
    payload = {
        "customer_name": company,
        "customer_number": str(ui.get("customer_number") or "").strip(),
        "address": ui.get("address") or "",
        "city": ui.get("city") or "",
        "state": ui.get("state") or "",
        "zip": ui.get("zip") or "",
        "website": str(ui.get("website") or "").strip(),
        "main_phone": str(ui.get("main_phone") or "").strip(),
        "main_email": str(ui.get("main_email") or "").strip(),
        "billing_email": str(ui.get("billing_email") or "").strip(),
        "is_active": active,
        "status": status,
        "notes": ui.get("notes") or "",
    }
    if row_id:
        return update_row("customers", payload, {"id": row_id})
    return insert_row("customers", payload)


def delete_customer(row_id: str) -> ServiceResult:
    return delete_row("customers", {"id": row_id})
