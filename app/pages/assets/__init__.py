"""Assets package — re-exports ``render`` from page.py for backward compatibility.

main.py uses:
    from pages import assets as assets_page
    "Asset Manager": assets_page.render,

This __init__.py makes ``assets.render`` resolve to ``page.render`` so that
import still works after converting assets.py into this package.
"""
from __future__ import annotations

try:
    from app.pages.assets.page import render
except ImportError:
    from pages.assets.page import render  # type: ignore

__all__ = ["render"]
