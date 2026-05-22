"""Customers module service — parent company, locations, and contacts."""

from __future__ import annotations

from typing import Any

from app.services.phase2_modules_service import (
    delete_customer,
    delete_customer_contact,
    delete_customer_location,
    list_customer_contacts,
    list_customer_locations,
    list_customers,
    normalize_customer,
    normalize_customer_contact,
    normalize_customer_location,
    save_customer,
    save_customer_contact,
    save_customer_location,
)

LOCATION_TYPES = [
    "Plant",
    "Office",
    "Billing",
    "Shipping",
    "Warehouse",
    "Job Site",
    "Yard",
    "Other",
]

CONTACT_ROLE_TYPES = [
    "Primary Contact",
    "Project Contact",
    "Site Contact",
    "Safety Contact",
    "Billing Contact",
    "Estimating Contact",
    "Purchasing Contact",
    "Shipping Contact",
    "Emergency Contact",
    "Other",
]


def _demo_customers() -> list[dict[str, Any]]:
    try:
        from app.pages._core._data import (
            _DEMO_CUSTOMER_CONTACTS,
            _DEMO_CUSTOMER_LOCATIONS,
            _DEMO_CUSTOMERS,
        )
    except ImportError:
        from pages._core._data import (  # type: ignore
            _DEMO_CUSTOMER_CONTACTS,
            _DEMO_CUSTOMER_LOCATIONS,
            _DEMO_CUSTOMERS,
        )
    return list(_DEMO_CUSTOMERS)


def _demo_locations() -> list[dict[str, Any]]:
    try:
        from app.pages._core._data import _DEMO_CUSTOMER_LOCATIONS
    except ImportError:
        from pages._core._data import _DEMO_CUSTOMER_LOCATIONS  # type: ignore
    return list(_DEMO_CUSTOMER_LOCATIONS)


def _demo_contacts() -> list[dict[str, Any]]:
    try:
        from app.pages._core._data import _DEMO_CUSTOMER_CONTACTS
    except ImportError:
        from pages._core._data import _DEMO_CUSTOMER_CONTACTS  # type: ignore
    return list(_DEMO_CUSTOMER_CONTACTS)


def _primary_location(locations: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not locations:
        return None
    primary = next((loc for loc in locations if loc.get("is_primary")), None)
    return primary or locations[0]


def _enrich_customer(
    customer: dict[str, Any],
    *,
    locations: list[dict[str, Any]] | None = None,
    contacts: list[dict[str, Any]] | None = None,
    open_jobs: int | None = None,
    open_estimates: int | None = None,
) -> dict[str, Any]:
    cid = str(customer.get("id") or "").strip()
    locs = locations if locations is not None else get_customer_locations(cid)
    cons = contacts if contacts is not None else get_customer_contacts(cid)
    primary = _primary_location(locs)
    row = dict(customer)
    row["primary_location_name"] = str((primary or {}).get("location_name") or (primary or {}).get("site_name") or "—")
    row["primary_location_city"] = str((primary or {}).get("city") or customer.get("city") or "—")
    row["primary_location_state"] = str((primary or {}).get("state") or customer.get("state") or "—")
    row["location_count"] = len(locs)
    row["contact_count"] = len(cons)
    row["open_jobs"] = open_jobs if open_jobs is not None else 0
    row["open_estimates"] = open_estimates if open_estimates is not None else 0
    return row


def get_customers(*, enrich: bool = True) -> list[dict[str, Any]]:
    rows, _ = list_customers(demo=_demo_customers())
    if not enrich:
        return rows
    return [_enrich_customer(row) for row in rows]


def get_customer(customer_id: str) -> dict[str, Any] | None:
    cid = str(customer_id or "").strip()
    if not cid:
        return None
    row = next((c for c in get_customers(enrich=False) if str(c.get("id")) == cid), None)
    if not row:
        return None
    return _enrich_customer(row)


def create_customer(data: dict[str, Any]):
    return save_customer(data)


def update_customer(customer_id: str, data: dict[str, Any]):
    return save_customer(data, row_id=str(customer_id or "").strip() or None)


def delete_customer_record(customer_id: str):
    return delete_customer(str(customer_id or "").strip())


def get_customer_locations(customer_id: str) -> list[dict[str, Any]]:
    cid = str(customer_id or "").strip()
    rows, _ = list_customer_locations(cid, demo=_demo_locations())
    return rows


def get_customer_location(location_id: str) -> dict[str, Any] | None:
    lid = str(location_id or "").strip()
    if not lid:
        return None
    for customer in get_customers(enrich=False):
        for loc in get_customer_locations(str(customer.get("id") or "")):
            if str(loc.get("id")) == lid:
                return loc
    return None


def create_customer_location(customer_id: str, data: dict[str, Any]):
    payload = dict(data)
    payload["customer_id"] = str(customer_id or "").strip()
    return save_customer_location(payload)


def update_customer_location(location_id: str, data: dict[str, Any]):
    payload = dict(data)
    return save_customer_location(payload, row_id=str(location_id or "").strip() or None)


def delete_customer_location_record(location_id: str):
    return delete_customer_location(str(location_id or "").strip())


def get_customer_contacts(customer_id: str, location_id: str | None = None) -> list[dict[str, Any]]:
    cid = str(customer_id or "").strip()
    rows, _ = list_customer_contacts(
        cid,
        location_id=location_id,
        demo=_demo_contacts(),
    )
    return rows


def get_customer_contact(contact_id: str) -> dict[str, Any] | None:
    cid = str(contact_id or "").strip()
    if not cid:
        return None
    for customer in get_customers(enrich=False):
        for contact in get_customer_contacts(str(customer.get("id") or "")):
            if str(contact.get("id")) == cid:
                contact = dict(contact)
                contact["customer_name"] = str(customer.get("customer_name") or "")
                loc = get_customer_location(str(contact.get("location_id") or ""))
                if loc:
                    contact["location_name"] = str(loc.get("location_name") or loc.get("site_name") or "")
                return contact
    return None


def create_customer_contact(customer_id: str, location_id: str, data: dict[str, Any]):
    payload = dict(data)
    payload["customer_id"] = str(customer_id or "").strip()
    payload["location_id"] = str(location_id or "").strip()
    payload["customer_location_id"] = payload["location_id"]
    return save_customer_contact(payload)


def update_customer_contact(contact_id: str, data: dict[str, Any]):
    return save_customer_contact(data, row_id=str(contact_id or "").strip() or None)


def delete_customer_contact_record(contact_id: str):
    return delete_customer_contact(str(contact_id or "").strip())


def get_customer_options(*, active_only: bool = True) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for row in get_customers(enrich=False):
        if active_only and str(row.get("status") or "Active") != "Active":
            continue
        cid = str(row.get("id") or "").strip()
        name = str(row.get("customer_name") or row.get("company_name") or "").strip()
        if cid and name:
            out.append((name, cid))
    return sorted(out, key=lambda pair: pair[0].lower())


def get_customer_location_options(customer_id: str, *, active_only: bool = True) -> list[tuple[str, str]]:
    cid = str(customer_id or "").strip()
    out: list[tuple[str, str]] = []
    for loc in get_customer_locations(cid):
        if active_only and str(loc.get("status") or "Active") != "Active":
            continue
        lid = str(loc.get("id") or "").strip()
        name = str(loc.get("location_name") or loc.get("site_name") or "").strip()
        city = str(loc.get("city") or "").strip()
        state = str(loc.get("state") or "").strip()
        label = name
        tail = ", ".join(part for part in (city, state) if part)
        if tail:
            label = f"{name} — {tail}"
        if lid:
            out.append((label, lid))
    return out


def get_customer_contact_options(
    customer_id: str,
    location_id: str | None = None,
    *,
    active_only: bool = True,
) -> list[tuple[str, str]]:
    cid = str(customer_id or "").strip()
    loc_filter = str(location_id or "").strip()
    locs = {str(loc.get("id") or ""): loc for loc in get_customer_locations(cid)}
    out: list[tuple[str, str]] = []
    for contact in get_customer_contacts(cid, location_id=loc_filter or None):
        if active_only and str(contact.get("status") or "Active") != "Active":
            continue
        ct_id = str(contact.get("id") or "").strip()
        if not ct_id:
            continue
        name = str(contact.get("full_name") or contact.get("contact_name") or "").strip()
        role = str(contact.get("role_type") or contact.get("title") or "").strip()
        loc_id = str(contact.get("location_id") or contact.get("customer_location_id") or "").strip()
        loc = locs.get(loc_id, {})
        loc_name = str(loc.get("location_name") or loc.get("site_name") or "").strip()
        label = name
        if role:
            label = f"{name} ({role})"
        if loc_name and not loc_filter:
            label = f"{label} · {loc_name}"
        out.append((label, ct_id))
    return out


__all__ = [
    "CONTACT_ROLE_TYPES",
    "LOCATION_TYPES",
    "create_customer",
    "create_customer_contact",
    "create_customer_location",
    "delete_customer",
    "delete_customer_contact",
    "delete_customer_contact_record",
    "delete_customer_location",
    "delete_customer_location_record",
    "delete_customer_record",
    "get_customer",
    "get_customer_contact",
    "get_customer_contact_options",
    "get_customer_contacts",
    "get_customer_location",
    "get_customer_location_options",
    "get_customer_locations",
    "get_customer_options",
    "get_customers",
    "list_customer_contacts",
    "list_customer_locations",
    "list_customers",
    "normalize_customer",
    "normalize_customer_contact",
    "normalize_customer_location",
    "save_customer",
    "save_customer_contact",
    "save_customer_location",
    "update_customer",
    "update_customer_contact",
    "update_customer_location",
]
