"""Shared helpers for field-operations services (table probes, read/write routing)."""

from __future__ import annotations

import logging
from typing import Any, Callable

_LOG = logging.getLogger(__name__)


def table_exists(table_name: str, *, admin: bool = False) -> bool:
    try:
        if admin:
            from app.db import get_admin_client

            client = get_admin_client()
        else:
            from app.db import get_client

            client = get_client()
    except ImportError:
        if admin:
            from db import get_admin_client  # type: ignore

            client = get_admin_client()
        else:
            from db import get_client  # type: ignore

            client = get_client()
    try:
        if admin:
            client.table(table_name).select("id").limit(1).execute()
        else:
            try:
                from app.db import run_user_supabase_operation
            except ImportError:
                from db import run_user_supabase_operation  # type: ignore

            run_user_supabase_operation(
                f"read {table_name}",
                lambda: client.table(table_name).select("id").limit(1).execute(),
                friendly_on_failure=False,
            )
        return True
    except Exception as exc:
        _LOG.debug("table_exists(%s): %s", table_name, exc)
        return False


def fetch_fn(*, admin: bool) -> Callable[..., list[dict[str, Any]]]:
    try:
        from app.db import fetch_by_match, fetch_by_match_admin
    except ImportError:
        from db import fetch_by_match, fetch_by_match_admin  # type: ignore
    return fetch_by_match_admin if admin else fetch_by_match


def write_fn(*, admin: bool) -> tuple[
    Callable[..., dict[str, Any]],
    Callable[..., list[dict[str, Any]]],
    Callable[..., list[dict[str, Any]]],
]:
    try:
        from app.db import delete_rows, delete_rows_admin, insert_row, insert_row_admin, update_rows, update_rows_admin
    except ImportError:
        from db import (  # type: ignore
            delete_rows,
            delete_rows_admin,
            insert_row,
            insert_row_admin,
            update_rows,
            update_rows_admin,
        )
    if admin:
        return insert_row_admin, update_rows_admin, delete_rows_admin
    return insert_row, update_rows, delete_rows
