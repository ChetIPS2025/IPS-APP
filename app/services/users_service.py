"""
User profiles and auth-linked employee records.

Schema assumptions: ``profiles`` linked to auth.users; role on profile or employees table.
"""

from __future__ import annotations

from typing import Any

try:
    from app.db import fetch_one, get_client
except ImportError:
    from db import fetch_one, get_client  # type: ignore


def get_profile_by_user_id(user_id: str) -> dict[str, Any] | None:
    """Fetch ``profiles`` row for the authenticated user."""
    if not user_id:
        return None
    return fetch_one("profiles", {"id": user_id})


def list_profiles(*, limit: int = 200) -> list[dict[str, Any]]:
    try:
        from app.services.repository import fetch_rows
    except ImportError:
        from services.repository import fetch_rows  # type: ignore
    rows, _ = fetch_rows("profiles", limit=limit, order_by="full_name")
    return rows
