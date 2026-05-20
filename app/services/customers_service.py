"""Customers module — Supabase reads/writes."""

from __future__ import annotations

from app.services.phase2_modules_service import (
    delete_customer,
    list_customer_contacts,
    list_customer_locations,
    list_customers,
    normalize_customer,
    normalize_customer_contact,
    normalize_customer_location,
    save_customer,
)

__all__ = [
    "delete_customer",
    "list_customer_contacts",
    "list_customer_locations",
    "list_customers",
    "normalize_customer",
    "normalize_customer_contact",
    "normalize_customer_location",
    "save_customer",
]
