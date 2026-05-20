"""
Central documents hub — role-filtered reads/writes.

Schema assumptions: ``documents_hub`` (or ``documents``) with file_name, doc_type,
linked_module, linked_ref, uploaded_by, expiration_date, is_restricted.
"""

from __future__ import annotations

from app.services.phase2_modules_service import (
    delete_document,
    list_documents_hub,
    normalize_document_hub,
    save_document_hub,
)

__all__ = [
    "delete_document",
    "list_documents_hub",
    "normalize_document_hub",
    "save_document_hub",
]
