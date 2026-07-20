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


def test_estimates_list_table_uses_native_detail_links() -> None:
    src = _estimates_source().replace("\r\n", "\n")
    table_block = src.split("def _render_custom_estimates_table(")[1].split("def _contact_label_for_estimate")[0]
    assert "build_estimates_html_table" in table_block
    assert "open_estimate_fn=None" in table_block
    assert "estimate_detail_href" in src


def test_estimates_catalog_fragment_uses_directory_service() -> None:
    src = _estimates_source().replace("\r\n", "\n")
    fragment_block = src.split("@fragment\ndef _render_estimates_catalog_fragment")[1].split(
        "\ndef render("
    )[0]
    assert "list_estimates_page" in fragment_block
    assert "_rerun_if_estimates_detail_pending()" not in fragment_block


def test_customers_list_table_open_prepares_navigation_without_rerun() -> None:
    from app.pages import customers as customers_page

    src = inspect.getsource(customers_page._prepare_open_customer_table_row)
    assert "_open_customer_detail(" in src
    assert "ips_app_rerun()" not in src
    assert "st.rerun()" not in src


def test_customers_list_table_uses_native_detail_links() -> None:
    from app.components import customers_list_table

    src = _customers_source()
    table_block = src.split("def _render_custom_customers_table(")[1].split("def _service_feedback")[0]
    list_table_src = inspect.getsource(customers_list_table.build_customers_html_table)
    assert "build_customers_html_table" in table_block
    assert "render_customers_table_bridge_legacy" not in table_block
    assert "render_customers_table_open_buttons" not in table_block
    assert "customer_name_link_html" in list_table_src


def test_inline_meta_grid_renders_html_grid_without_streamlit_columns() -> None:
    from app.pages import customers as customers_page

    grid_src = inspect.getsource(customers_page._inline_meta_grid)
    card_src = inspect.getsource(customers_page._inline_meta_card_html)
    assert "st.columns" not in grid_src
    assert "ips-inline-meta-grid" in grid_src
    assert "ips-inline-meta-card" in card_src
    assert "inline_contact_meta_" in grid_src


def test_customers_catalog_fragment_uses_directory_service() -> None:
    src = _customers_source().replace("\r\n", "\n")
    fragment_block = src.split("@fragment\ndef _render_customers_catalog_fragment")[1].split(
        "\ndef render("
    )[0]
    assert "list_customers_page" in fragment_block
    assert "_rerun_if_customers_detail_pending()" not in fragment_block



def test_estimates_approve_panel_uses_app_rerun_not_st_rerun() -> None:
    from app.pages import estimates as estimates_page

    src = inspect.getsource(estimates_page._render_approve_confirmation_panel)
    assert "ips_app_rerun()" in src
    assert "st.rerun()" not in src
