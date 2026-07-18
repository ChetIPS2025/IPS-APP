"""Customer service lookups — direct fetch by id (no catalog N+1 scans)."""

from __future__ import annotations

from unittest.mock import patch

from app.services import customers_service


def test_get_customer_location_uses_fetch_by_id() -> None:
    loc_row = {"id": "loc-1", "customer_id": "cust-1", "location_name": "Plant A", "city": "Austin", "state": "TX"}
    with patch("app.services.repository.fetch_by_id", return_value=loc_row) as mock_fetch:
        result = customers_service.get_customer_location("loc-1")
    mock_fetch.assert_called_once_with(
        "customer_locations",
        "loc-1",
        normalize=customers_service.normalize_customer_location,
    )
    assert result is not None
    assert result.get("location_name") == "Plant A"


def test_get_customer_contact_uses_fetch_by_id_and_enriches() -> None:
    contact_row = {
        "id": "ct-1",
        "customer_id": "cust-1",
        "location_id": "loc-1",
        "full_name": "Jane Doe",
    }
    customer_row = {"id": "cust-1", "customer_name": "Acme Corp"}
    location_row = {"id": "loc-1", "location_name": "Plant A", "site_name": "Plant A"}

    def _fetch(table: str, row_id: str, *, normalize=None):
        if table == "customer_contacts" and row_id == "ct-1":
            return normalize(contact_row) if normalize else contact_row
        if table == "customers" and row_id == "cust-1":
            return normalize(customer_row) if normalize else customer_row
        if table == "customer_locations" and row_id == "loc-1":
            return normalize(location_row) if normalize else location_row
        return None

    with patch("app.services.repository.fetch_by_id", side_effect=_fetch):
        result = customers_service.get_customer_contact("ct-1")

    assert result is not None
    assert result.get("full_name") == "Jane Doe"
    assert result.get("customer_name") == "Acme Corp"
    assert result.get("location_name") == "Plant A"


def test_get_customer_contact_returns_none_for_missing_id() -> None:
    with patch("app.services.repository.fetch_by_id", return_value=None):
        assert customers_service.get_customer_contact("") is None
        assert customers_service.get_customer_contact("missing") is None
