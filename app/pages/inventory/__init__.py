"""
Inventory page package.

Exposes ``render`` so that ``from pages import inventory; inventory.render()``
continues to work unchanged in ``app/main.py``.
"""

from app.pages.inventory.page import render

__all__ = ["render"]
