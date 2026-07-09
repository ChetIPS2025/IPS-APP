"""Tests for Customers list table HTML helpers."""

from __future__ import annotations

from app.components.customers_list_table import (
    _customer_link_html,
    build_customers_html_table,
    customer_name,
    customer_status_pill_html,
    handle_customers_table_action,
    normalize_customer_status,
)


def test_normalize_customer_status_maps_aliases():
    assert normalize_customer_status("active") == "Active"
    assert normalize_customer_status("on hold") == "On Hold"
    assert normalize_customer_status("prospect") == "Prospect"


def test_customer_status_pill_html_includes_class():
    html_out = customer_status_pill_html("Active")
    assert "ips-customer-status-pill" in html_out
    assert "ips-customer-status-active" in html_out
    assert "Active" in html_out


def test_customer_link_html_uses_open_span():
    html_out = _customer_link_html("cust-1", "Acme Corp", extra_class="ips-dash-est-desc-link")
    assert 'role="button"' in html_out
    assert 'data-cust-action="open"' in html_out
    assert 'data-customer-id="cust-1"' in html_out
    assert "ips-customers-open-link" in html_out
    assert "Acme Corp" in html_out


def test_build_customers_html_table_includes_columns_and_link():
    rows = [
        {
            "id": "cust-1",
            "customer_name": "Acme Corp",
            "contact_count": 3,
            "open_jobs": 2,
            "open_estimates": 1,
            "status": "Active",
        }
    ]
    html_out = build_customers_html_table(rows)
    assert "ips-dash-est-html-table" in html_out
    assert "ips-customers-html-list-table" in html_out
    assert "CUSTOMER" in html_out
    assert "OPEN JOBS" in html_out
    assert 'data-cust-action="open"' in html_out
    assert 'data-customer-id="cust-1"' in html_out
    assert "Acme Corp" in html_out
    assert customer_name(rows[0]) == "Acme Corp"


def test_handle_customers_table_action_opens_customer(monkeypatch):
    opened: list[tuple[str, dict]] = []
    reran: list[str] = []

    import sys
    import types

    perf_mod = types.ModuleType("app.ui.streamlit_perf")
    perf_mod.ips_app_rerun = lambda: reran.append("app")
    monkeypatch.setitem(sys.modules, "app.ui.streamlit_perf", perf_mod)

    handle_customers_table_action(
        "open:cust-1",
        {"cust-1": {"id": "cust-1", "customer_name": "Acme Corp"}},
        last_action_key="_test_customers_last_action",
        open_item_fn=lambda customer_id, customer: opened.append((customer_id, customer)),
    )

    assert opened == [("cust-1", {"id": "cust-1", "customer_name": "Acme Corp"})]
    assert reran == ["app"]
