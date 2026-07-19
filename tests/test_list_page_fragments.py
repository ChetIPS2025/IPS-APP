"""Regression tests: Users and Pricing Guide list fragments."""

from __future__ import annotations

import inspect
from pathlib import Path


def _employees_source() -> str:
    path = Path(__file__).resolve().parents[1] / "app" / "pages" / "employees.py"
    return path.read_text(encoding="utf-8")


def _pricing_guide_source() -> str:
    path = Path(__file__).resolve().parents[1] / "app" / "pages" / "pricing_guide.py"
    return path.read_text(encoding="utf-8")


def test_users_table_open_prepares_modal_without_rerun() -> None:
    from app.pages import employees as employees_page

    src = inspect.getsource(employees_page._open_users_table_user)
    assert "_prepare_open_user_from_list(" in src
    assert "ips_app_rerun()" not in src


def test_users_catalog_fragment_uses_native_detail_links() -> None:
    src = _employees_source().replace("\r\n", "\n")
    fragment_block = src.split("@fragment\ndef _render_users_catalog_fragment")[1].split(
        "\ndef _maybe_seed_core_employees"
    )[0]
    assert "list_people_page" in fragment_block
    assert "_render_custom_users_table" in fragment_block
    assert "render_users_table_open_buttons" not in src
    assert "build_people_directory_table" in src
    assert "fragment_rerun()" in fragment_block


def test_users_render_shows_modal_outside_fragment() -> None:
    src = _employees_source().replace("\r\n", "\n")
    render_block = src.split("\ndef render(")[1]
    assert "show_modal_if_pending" in render_block
    assert "_detail_pending()" in render_block


def test_pricing_guide_table_uses_native_detail_links() -> None:
    src = _pricing_guide_source().replace("\r\n", "\n")
    assert "render_pricing_guide_table_open_buttons" not in src
    assert "render_pricing_guide_table_bridge_legacy" not in src
    assert "list_pricing_guide_page" in src
    assert "_capture_pricing_detail_query" in src
    assert "pricing_guide_detail_href" in src


def test_pricing_guide_catalog_fragment_uses_directory_service() -> None:
    src = _pricing_guide_source().replace("\r\n", "\n")
    fragment_block = src.split("@fragment\ndef _render_pricing_guide_catalog_fragment")[1].split(
        "\ndef render("
    )[0]
    assert "list_pricing_guide_page" in fragment_block
    assert "_rerun_if_pg_modal_pending()" not in fragment_block
    assert "fragment_rerun()" in fragment_block
