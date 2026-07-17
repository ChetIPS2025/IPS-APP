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


def test_users_catalog_fragment_escalates_modal_to_app_rerun() -> None:
    src = _employees_source().replace("\r\n", "\n")
    fragment_block = src.split("@fragment\ndef _render_users_catalog_fragment")[1].split(
        "\ndef render("
    )[0]
    assert "_rerun_if_user_modal_pending()" in fragment_block
    assert "fragment_rerun()" in fragment_block


def test_pricing_guide_table_open_prepares_modal_without_rerun() -> None:
    from app.pages import pricing_guide as pricing_guide_page

    src = inspect.getsource(pricing_guide_page._prepare_open_pg_table_item)
    assert "_open_modal(" in src
    assert "ips_app_rerun()" not in src


def test_pricing_guide_catalog_fragment_escalates_modal_to_app_rerun() -> None:
    src = _pricing_guide_source().replace("\r\n", "\n")
    fragment_block = src.split("@fragment\ndef _render_pricing_guide_catalog_fragment")[1].split(
        "\ndef render("
    )[0]
    assert "_rerun_if_pg_modal_pending()" in fragment_block
    assert "fragment_rerun()" in fragment_block
