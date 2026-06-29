"""Dashboard metrics and lookup sync tests."""

from __future__ import annotations

from datetime import date, timedelta

from app.services.dashboard_metrics_service import (
    compute_dashboard_kpis,
    job_status_overview,
    open_quotes_aging_bars,
    sales_by_category,
    upcoming_deadlines,
)
from app.services.lookup_service import sync_lookup_for_label


def test_compute_dashboard_kpis_from_live_rows():
    today = date.today()
    kpis = compute_dashboard_kpis(
        [
            {"status": "Sent", "estimate_date": today.isoformat(), "customer_price": 5000},
            {"status": "Draft", "estimate_date": today.isoformat(), "total": 1000},
        ],
        [
            {"status": "Active", "start_date": today.isoformat(), "contract_value": 12000, "is_deleted": False},
        ],
        [{"qty_on_hand": 10, "unit_cost": 25.5}],
        period_start=today.replace(day=1),
        period_end=today,
    )
    assert kpis["open_estimates"] == 2
    assert kpis["open_invoices"] == 5000
    assert kpis["inventory_value"] == 255.0
    assert kpis["active_jobs"] == 1
    assert kpis["has_live_data"] is True


def test_open_quotes_aging_buckets():
    old = (date.today() - timedelta(days=45)).isoformat()
    bars = open_quotes_aging_bars(
        [{"status": "Sent", "estimate_date": old, "customer_price": 9000}],
    )
    assert any("31–60" in label or "60+" in label for label, _, _ in bars)
    assert sum(v for _, v, _ in bars) == 9000


def test_sales_by_category_uses_estimate_buckets():
    today = date.today()
    cats = sales_by_category(
        [
            {
                "status": "Approved",
                "estimate_date": today.isoformat(),
                "labor_total": 1000,
                "material_total": 500,
                "customer_price": 1800,
            }
        ],
        period_start=today.replace(day=1),
        period_end=today,
    )
    assert cats.get("Labor") == 1000
    assert cats.get("Materials") == 500


def test_upcoming_deadlines_includes_expiration():
    soon = (date.today() + timedelta(days=5)).isoformat()
    items = upcoming_deadlines(
        [{"estimate_number": "Q26001", "status": "Sent", "expiration_date": soon}],
        [],
    )
    assert len(items) == 1
    assert "Q26001" in items[0]["title"]


def test_job_status_overview_counts_normalized_statuses():
    counts = job_status_overview(
        [
            {"status": "Active", "is_deleted": False},
            {"status": "On Hold", "is_deleted": False},
            {"status": "Completed", "is_deleted": False},
            {"status": "Active", "is_deleted": True},
        ]
    )
    assert counts.get("Active") == 1
    assert counts.get("On Hold") == 1
    assert counts.get("Completed") == 1


def test_sync_lookup_deactivates_removed_values(monkeypatch):
    table_id = "tbl-1"
    row_a = {"id": "a1", "lookup_table_id": table_id, "value": "Alpha", "sort_order": 0, "is_active": True}
    row_b = {"id": "b2", "lookup_table_id": table_id, "value": "Beta", "sort_order": 1, "is_active": True}
    updates: list[tuple[dict, dict]] = []
    inserts: list[dict] = []

    def fake_fetch_rows(table, **kwargs):
        if table == "ips_lookup_tables":
            return [{"id": table_id, "slug": "crews"}], None
        if table == "ips_lookup_values":
            return [row_a, row_b], None
        return [], None

    def fake_update_row(table, payload, match):
        updates.append((payload, match))
        class R:
            ok = True
            error = None
        return R()

    def fake_insert_row(table, payload):
        inserts.append(payload)
        class R:
            ok = True
            data = {"id": "new-id"}
            error = None
        return R()

    monkeypatch.setattr("app.services.repository.fetch_rows", fake_fetch_rows)
    monkeypatch.setattr("app.services.repository.update_row", fake_update_row)
    monkeypatch.setattr("app.services.repository.insert_row", fake_insert_row)
    monkeypatch.setattr("app.services.lookup_service.clear_lookup_cache", lambda: None)

    ok, msg = sync_lookup_for_label(
        "Crews",
        [{"id": "a1", "value": "Alpha Renamed"}],
    )
    assert ok is True
    assert any(p.get("value") == "Alpha Renamed" for p, _ in updates)
    assert any(p.get("is_active") is False and m.get("id") == "b2" for p, m in updates)
