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
from app.services.company_update_banner_service import (
    enrich_company_update_banner,
    has_company_update_banner,
    remove_company_update_banner,
    resolve_company_update_banner_url,
    upload_company_update_banner,
    validate_banner_upload,
    BANNER_UPLOAD_TYPES,
)

__all__ = [
    "BANNER_UPLOAD_TYPES",
    "delete_company_update",
    "enrich_company_update_banner",
    "has_company_update_banner",
    "list_company_updates",
    "normalize_company_update",
    "remove_company_update_banner",
    "resolve_company_update_banner_url",
    "save_company_update",
    "upload_company_update_banner",
    "validate_banner_upload",
]
