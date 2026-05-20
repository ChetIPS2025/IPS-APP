"""
Company updates — announcements, safety, events.

Schema assumptions: ``company_updates`` with title, message, category, is_active, pinned.
"""

from __future__ import annotations

from app.services.phase2_modules_service import (
    delete_company_update,
    list_company_updates,
    normalize_company_update,
    save_company_update,
)

__all__ = [
    "delete_company_update",
    "list_company_updates",
    "normalize_company_update",
    "save_company_update",
]
