"""Customers module — Supabase reads/writes."""

from __future__ import annotations

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

__all__ = [
    "delete_customer",
    "delete_customer_contact",
    "delete_customer_location",
    "list_customer_contacts",
    "list_customer_locations",
    "list_customers",
    "normalize_customer",
    "normalize_customer_contact",
    "normalize_customer_location",
    "save_customer",
    "save_customer_contact",
    "save_customer_location",
]
