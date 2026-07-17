"""Regression tests: list pages use HTML table bridges."""

from __future__ import annotations

import inspect
from pathlib import Path


def _estimates_source() -> str:
    path = Path(__file__).resolve().parents[1] / "app" / "pages" / "estimates.py"
    return path.read_text(encoding="utf-8")


def _customers_source() -> str:
    path = Path(__file__).resolve().parents[1] / "app" / "pages" / "customers.py"
    return path.read_text(encoding="utf-8")


def test_estimates_list_table_open_prepares_navigation_without_rerun() -> None:
    from app.pages import estimates as estimates_page

    src = inspect.getsource(estimates_page._prepare_open_estimate_table_row)
    assert "_activate_estimate_detail_modal(" in src
    assert "ips_app_rerun()" not in src


def test_estimates_list_table_uses_html_bridge() -> None:
    src = _estimates_source()
    table_block = src.split("def _render_custom_estimates_table(")[1].split("def _contact_label_for_estimate")[0]
    assert "build_estimates_html_table" in table_block
    assert "render_estimates_table_bridge" in table_block
    assert "render_estimates_list_table_body" not in src
    assert "render_estimates_list_table_header" not in src


def test_customers_list_table_open_prepares_navigation_without_rerun() -> None:
    from app.pages import customers as customers_page

    src = inspect.getsource(customers_page._prepare_open_customer_table_row)
    assert "_open_customer_detail(" in src
    assert "ips_app_rerun()" not in src
    assert "st.rerun()" not in src


def test_customers_list_table_uses_html_bridge() -> None:
    src = _customers_source()
    table_block = src.split("def _render_custom_customers_table(")[1].split("def _service_feedback")[0]
    assert "build_customers_html_table" in table_block
    assert "render_customers_table_bridge_legacy" in table_block
    assert "render_customers_table_open_buttons" in table_block
    assert "customer_open_" not in table_block
    assert "customer_view_" not in table_block


def test_customers_catalog_fragment_escalates_detail_to_app_rerun() -> None:
    src = _customers_source().replace("\r\n", "\n")
    fragment_block = src.split("@fragment\ndef _render_customers_catalog_fragment")[1].split(
        "\ndef render("
    )[0]
    assert "_rerun_if_customers_detail_pending()" in fragment_block


def test_estimates_catalog_fragment_escalates_detail_to_app_rerun() -> None:
    src = _estimates_source().replace("\r\n", "\n")
    fragment_block = src.split("@fragment\ndef _render_estimates_catalog_fragment")[1].split(
        "\ndef render("
    )[0]
    assert "_rerun_if_estimates_detail_pending()" in fragment_block


def test_estimates_approve_panel_uses_app_rerun_not_st_rerun() -> None:
    from app.pages import estimates as estimates_page

    src = inspect.getsource(estimates_page._render_approve_confirmation_panel)
    assert "ips_app_rerun()" in src
    assert "st.rerun()" not in src
