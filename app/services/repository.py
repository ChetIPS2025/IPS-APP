"""Shared Supabase access for Phase 2/3 modules (no UI)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

_LOG = logging.getLogger(__name__)


@dataclass
class ServiceResult:
    ok: bool
    data: Any = None
    error: str | None = None
    used_demo: bool = False


def clear_all_data_caches() -> None:
    """Invalidate Streamlit/db read caches after mutations."""
    try:
        from app.perf_debug import perf_span
    except ImportError:
        from perf_debug import perf_span  # type: ignore

    with perf_span("repo.clear_all_data_caches"):
        _clear_all_data_caches_impl()


def _clear_all_data_caches_impl() -> None:
    try:
        from app.db import clear_streamlit_db_read_cache

        clear_streamlit_db_read_cache()
    except Exception:
        try:
            from db import clear_streamlit_db_read_cache  # type: ignore

            clear_streamlit_db_read_cache()
        except Exception:
            pass
    try:
        from app.data_cache import clear_session_table_cache

        clear_session_table_cache()
    except Exception:
        try:
            from data_cache import clear_session_table_cache  # type: ignore

            clear_session_table_cache()
        except Exception:
            pass


def _db():
    try:
        import app.db as db
    except ImportError:
        import db  # type: ignore
    return db


def fetch_rows(
    table: str,
    *,
    columns: str = "*",
    limit: int = 500,
    order_by: str | None = None,
    alt_tables: tuple[str, ...] = (),
) -> tuple[list[dict[str, Any]], str | None]:
    """Try primary table then alternates; return (rows, error_message)."""
    db = _db()
    last_err: str | None = None
    for name in (table, *alt_tables):
        try:
            rows = db.fetch_table(name, columns=columns, limit=limit, order_by=order_by) or []
            return rows, None
        except Exception as exc:
            last_err = str(exc)
            _LOG.debug("fetch_rows %s failed: %s", name, exc)
    return [], last_err


def fetch_list(
    table: str,
    *,
    order_by: str | None = None,
    limit: int = 500,
    normalize: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    demo: list[dict[str, Any]] | None = None,
    alt_tables: tuple[str, ...] = (),
) -> tuple[list[dict[str, Any]], bool]:
    """
    Return (rows, used_demo_fallback).

    Demo data is used only when the query fails (missing table, RLS, network).
    An empty successful response returns [] with used_demo=False — never overrides live data.
    """
    rows, err = fetch_rows(table, limit=limit, order_by=order_by, alt_tables=alt_tables)
    if err:
        _LOG.info("Using demo fallback for %s (%s)", table, err)
        if normalize and demo:
            return [normalize(r) for r in demo if r], True
        return list(demo or []), True
    if normalize:
        out = [normalize(r) for r in rows if r]
        return out, False
    return rows, False


def fetch_by_id(
    table: str,
    row_id: str,
    *,
    id_column: str = "id",
    normalize: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    rid = str(row_id or "").strip()
    if not rid:
        return None
    db = _db()
    try:
        rows = db.fetch_by_match(table, {id_column: rid}, limit=1) or []
    except Exception as exc:
        _LOG.debug("fetch_by_id %s failed: %s", table, exc)
        return None
    if not rows:
        return None
    row = rows[0]
    return normalize(row) if normalize else row


def table_column_names(table: str) -> frozenset[str]:
    """Best-effort column set from one sample row (handles legacy schemas)."""
    try:
        from app.perf_debug import perf_span
    except ImportError:
        from perf_debug import perf_span  # type: ignore

    with perf_span(f"repo.table_column_names:{table}"):
        rows, err = fetch_rows(table, limit=1)
        if err or not rows:
            return frozenset()
        return frozenset(str(k) for k in rows[0].keys())


def filter_payload_to_table(table: str, payload: dict[str, Any]) -> dict[str, Any]:
    cols = table_column_names(table)
    if not cols:
        return payload
    return {k: v for k, v in payload.items() if k in cols}


def insert_row(table: str, payload: dict[str, Any]) -> ServiceResult:
    try:
        from app.perf_debug import perf_span
    except ImportError:
        from perf_debug import perf_span  # type: ignore

    with perf_span(f"repo.insert_row:{table}"):
        payload = filter_payload_to_table(table, payload)
        try:
            row = _db().insert_row(table, payload)
            clear_all_data_caches()
            return ServiceResult(ok=True, data=row)
        except Exception as exc:
            msg = f"Could not save to {table}: {exc}"
            _LOG.warning(msg)
            return ServiceResult(ok=False, error=msg)


def insert_row_admin(table: str, payload: dict[str, Any]) -> ServiceResult:
    """Server-side insert using service role (Streamlit writes when user JWT may be stale)."""
    payload = filter_payload_to_table(table, payload)
    try:
        row = _db().insert_row_admin(table, payload)
        clear_all_data_caches()
        return ServiceResult(ok=True, data=row)
    except Exception as exc:
        msg = f"Could not save to {table}: {exc}"
        _LOG.warning(msg)
        return ServiceResult(ok=False, error=msg)


def update_row(table: str, payload: dict[str, Any], match: dict[str, Any]) -> ServiceResult:
    try:
        from app.perf_debug import perf_span
    except ImportError:
        from perf_debug import perf_span  # type: ignore

    with perf_span(f"repo.update_row:{table}"):
        payload = filter_payload_to_table(table, payload)
        try:
            rows = _db().update_rows(table, payload, match)
            clear_all_data_caches()
            return ServiceResult(ok=True, data=rows[0] if rows else None)
        except Exception as exc:
            msg = f"Could not update {table}: {exc}"
            _LOG.warning(msg)
            return ServiceResult(ok=False, error=msg)


def update_row_admin(table: str, payload: dict[str, Any], match: dict[str, Any]) -> ServiceResult:
    """Server-side update using service role (Streamlit writes when user JWT may be stale)."""
    payload = filter_payload_to_table(table, payload)
    try:
        rows = _db().update_rows_admin(table, payload, match)
        clear_all_data_caches()
        return ServiceResult(ok=True, data=rows[0] if rows else None)
    except Exception as exc:
        msg = f"Could not update {table}: {exc}"
        _LOG.warning(msg)
        return ServiceResult(ok=False, error=msg)


def delete_row(table: str, match: dict[str, Any]) -> ServiceResult:
    try:
        rows = _db().delete_rows(table, match)
        clear_all_data_caches()
        return ServiceResult(ok=True, data=rows)
    except Exception as exc:
        msg = f"Could not delete from {table}: {exc}"
        _LOG.warning(msg)
        return ServiceResult(ok=False, error=msg)


def user_facing_error(result: ServiceResult, *, demo_ok_message: str | None = None) -> str | None:
    """Message for st.error; None if ok."""
    if result.ok:
        return None
    return result.error or "An unexpected error occurred."
