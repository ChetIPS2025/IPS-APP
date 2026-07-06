"""Shared Supabase access for Phase 2/3 modules (no UI)."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Callable

_LOG = logging.getLogger(__name__)

_PGRST204_COLUMN_RE = re.compile(r"Could not find the '([^']+)' column", re.I)

# Fallback when the table has no rows yet — prevents sending columns that do not exist
# (e.g. cost_total on estimate_line_items, which uses total_cost instead).
TABLE_COLUMN_ALLOWLIST: dict[str, frozenset[str]] = {
    "estimate_line_items": frozenset(
        {
            "estimate_id",
            "inventory_item_id",
            "pricing_item_id",
            "item_number",
            "sku",
            "description",
            "category",
            "qty",
            "unit",
            "unit_cost",
            "total_cost",
            "markup",
            "markup_percent",
            "markup_amount",
            "price_total",
            "taxable",
            "vendor",
            "vendor_id",
            "notes",
            "sort_order",
        }
    ),
}

# Oldest deployed shape (062) when the table has no sample rows yet.
TABLE_COLUMN_CORE: dict[str, frozenset[str]] = {
    "estimate_line_items": frozenset(
        {
            "estimate_id",
            "item_number",
            "description",
            "category",
            "qty",
            "unit",
            "unit_cost",
            "total_cost",
            "sort_order",
        }
    ),
    "inventory_items": frozenset(
        {
            "item_name",
            "sku",
            "category",
            "storage_location",
            "unit_cost",
            "vendor",
            "quantity_on_hand",
            "reorder_point",
            "qr_code_value",
            "image_path",
            "image_url",
            "image_file_name",
            "image_mime_type",
            "image_uploaded_at",
            "image_uploaded_by",
        }
    ),
}


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


def _clear_db_read_caches() -> None:
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


def _clear_all_data_caches_impl() -> None:
    _clear_db_read_caches()
    try:
        from app.pages._core._data import clear_all_catalog_list_caches
    except ImportError:
        try:
            from pages._core._data import clear_all_catalog_list_caches  # type: ignore
        except ImportError:
            clear_all_catalog_list_caches = None  # type: ignore
    if clear_all_catalog_list_caches:
        try:
            clear_all_catalog_list_caches()
        except Exception:
            pass


def clear_data_cache_for_table(table: str) -> None:
    """Invalidate caches affected by a single-table write (narrower than clear_all)."""
    try:
        from app.perf_debug import perf_span
    except ImportError:
        from perf_debug import perf_span  # type: ignore

    name = str(table or "").strip().lower()
    with perf_span(f"repo.clear_data_cache:{name or 'unknown'}"):
        _clear_db_read_caches()
        try:
            from app.pages._core._data import (
                clear_all_catalog_list_caches,
                clear_assets_catalog_cache,
                clear_customers_catalog_cache,
                clear_employees_catalog_cache,
                clear_estimates_catalog_cache,
                clear_inventory_catalog_cache,
                clear_jobs_catalog_cache,
                clear_labor_rates_catalog_cache,
                clear_pricing_guide_catalog_cache,
                clear_tasks_catalog_cache,
                clear_timekeeping_catalog_cache,
            )
        except ImportError:
            from pages._core._data import (  # type: ignore
                clear_all_catalog_list_caches,
                clear_assets_catalog_cache,
                clear_customers_catalog_cache,
                clear_employees_catalog_cache,
                clear_estimates_catalog_cache,
                clear_inventory_catalog_cache,
                clear_jobs_catalog_cache,
                clear_labor_rates_catalog_cache,
                clear_pricing_guide_catalog_cache,
                clear_tasks_catalog_cache,
                clear_timekeeping_catalog_cache,
            )

        _handlers: dict[str, object] = {
            "jobs": clear_jobs_catalog_cache,
            "estimates": clear_estimates_catalog_cache,
            "estimate_line_items": clear_estimates_catalog_cache,
            "estimate_labor": clear_estimates_catalog_cache,
            "estimate_equipment": clear_estimates_catalog_cache,
            "estimate_materials": clear_estimates_catalog_cache,
            "estimate_travel": clear_estimates_catalog_cache,
            "estimate_subcontractors": clear_estimates_catalog_cache,
            "estimate_other_costs": clear_estimates_catalog_cache,
            "inventory_items": clear_inventory_catalog_cache,
            "assets": clear_assets_catalog_cache,
            "customers": clear_customers_catalog_cache,
            "employees": clear_employees_catalog_cache,
            "users": clear_employees_catalog_cache,
            "user_profiles": clear_employees_catalog_cache,
            "employee_certifications": clear_employees_catalog_cache,
            "todos": clear_tasks_catalog_cache,
            "tasks": clear_tasks_catalog_cache,
            "labor_rates": clear_labor_rates_catalog_cache,
            "pricing_guide_items": clear_pricing_guide_catalog_cache,
            "estimate_materials_catalog": clear_pricing_guide_catalog_cache,
            "employee_timekeeping_days": clear_timekeeping_catalog_cache,
            "employee_timekeeping_weeks": clear_timekeeping_catalog_cache,
            "job_cost_transactions": clear_jobs_catalog_cache,
            "job_expenses": clear_jobs_catalog_cache,
            "ips_lookup_values": _clear_db_read_caches,
            "ips_lookup_tables": _clear_db_read_caches,
        }
        handler = _handlers.get(name)
        if handler is not None and callable(handler):
            handler()
            return
        try:
            clear_all_catalog_list_caches()
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
    sampled = table_column_names(table)
    allowlist = TABLE_COLUMN_ALLOWLIST.get(table)
    core = TABLE_COLUMN_CORE.get(table)
    if sampled:
        cols = sampled
    elif core:
        cols = core
    elif allowlist:
        cols = allowlist
    else:
        return payload
    filtered = {k: v for k, v in payload.items() if k in cols}
    if table == "estimate_line_items":
        if "markup" in cols and "markup_percent" not in cols and "markup_percent" in payload:
            filtered["markup"] = payload["markup_percent"]
    return filtered


def _friendly_repo_error(exc: Exception, *, table: str, action: str) -> str:
    try:
        from app.auth import friendly_auth_error_message, is_jwt_expired_error
    except ImportError:
        from auth import friendly_auth_error_message, is_jwt_expired_error  # type: ignore
    if is_jwt_expired_error(exc):
        return friendly_auth_error_message(exc, operation=f"{action} {table}")
    low = str(exc or "").casefold()
    if "23505" in low or "duplicate key" in low or "unique constraint" in low:
        if table == "jobs":
            return "A job with this job number already exists. Choose a different number."
        return "That record already exists. Please refresh and try again."
    if "23502" in low or "not-null constraint" in low:
        return f"Missing required information for {table.replace('_', ' ')}. Check required fields and try again."
    if "23503" in low or "foreign key" in low:
        return (
            f"Could not link one or more related records while trying to {action} {table.replace('_', ' ')}. "
            "Refresh the page and try again."
        )
    if "pgrst204" in low or ("could not find" in low and "column" in low):
        return (
            f"Database schema for {table.replace('_', ' ')} is out of date. "
            "Apply pending Supabase migrations, then refresh and try again."
        )
    if "returned no rows" in low:
        return (
            f"Could not save to {table.replace('_', ' ')} — the server rejected the write. "
            "Refresh the page and try again."
        )
    if "22p02" in low or "invalid input syntax for type uuid" in low:
        return (
            f"Could not save to {table.replace('_', ' ')} — invalid record link. "
            "Refresh the page and re-select the item."
        )
    return friendly_auth_error_message(exc, operation=f"{action} {table}")


def _insert_with_optional_columns(
    table: str,
    payload: dict[str, Any],
    *,
    use_admin: bool,
    action: str,
) -> ServiceResult:
    """
    Insert while dropping columns the remote schema does not recognize (PGRST204).

    Needed when Supabase migrations lag behind the app or the table has no sample rows.
    """
    working = dict(payload)
    last_exc: Exception | None = None

    for _ in range(24):
        filtered = filter_payload_to_table(table, working)
        if not filtered:
            break
        try:
            if use_admin:
                row = _db().insert_row_admin(table, filtered)
            else:
                row = _db().insert_row(table, filtered)
            clear_data_cache_for_table(table)
            return ServiceResult(ok=True, data=row)
        except Exception as exc:
            last_exc = exc
            match = _PGRST204_COLUMN_RE.search(str(exc))
            if match:
                col = match.group(1)
                if col in working:
                    working.pop(col)
                    continue
                if col == "markup" and "markup_percent" in working:
                    working.pop("markup_percent")
                    continue
                if col == "markup_percent" and "markup" in working:
                    working.pop("markup")
                    continue
            break

    msg = _friendly_repo_error(last_exc or RuntimeError("Insert failed"), table=table, action=action)
    _LOG.warning("insert %s (%s) failed: %s", table, "admin" if use_admin else "user", last_exc)
    return ServiceResult(ok=False, error=msg)


def insert_row(table: str, payload: dict[str, Any]) -> ServiceResult:
    try:
        from app.perf_debug import perf_span
    except ImportError:
        from perf_debug import perf_span  # type: ignore

    with perf_span(f"repo.insert_row:{table}"):
        return _insert_with_optional_columns(table, payload, use_admin=False, action="save to")


def insert_row_admin(table: str, payload: dict[str, Any]) -> ServiceResult:
    """Server-side insert using service role (Streamlit writes when user JWT may be stale)."""
    return _insert_with_optional_columns(table, payload, use_admin=True, action="save to")


def _update_with_optional_columns(
    table: str,
    payload: dict[str, Any],
    match: dict[str, Any],
    *,
    use_admin: bool,
    action: str,
) -> ServiceResult:
    """
    Update while dropping columns the remote schema does not recognize (PGRST204).

    Mirrors :func:`_insert_with_optional_columns` for lagging Supabase migrations.
    """
    working = dict(payload)
    last_exc: Exception | None = None

    for _ in range(24):
        filtered = filter_payload_to_table(table, working)
        if not filtered:
            break
        try:
            if use_admin:
                rows = _db().update_rows_admin(table, filtered, match)
            else:
                rows = _db().update_rows(table, filtered, match)
            clear_data_cache_for_table(table)
            return ServiceResult(ok=True, data=rows[0] if rows else None)
        except Exception as exc:
            last_exc = exc
            match_col = _PGRST204_COLUMN_RE.search(str(exc))
            if match_col:
                col = match_col.group(1)
                if col in working:
                    working.pop(col)
                    continue
            break

    msg = _friendly_repo_error(last_exc or RuntimeError("Update failed"), table=table, action=action)
    _LOG.warning("update %s (%s) failed: %s", table, "admin" if use_admin else "user", last_exc)
    return ServiceResult(ok=False, error=msg)


def update_row(table: str, payload: dict[str, Any], match: dict[str, Any]) -> ServiceResult:
    try:
        from app.perf_debug import perf_span
    except ImportError:
        from perf_debug import perf_span  # type: ignore

    with perf_span(f"repo.update_row:{table}"):
        return _update_with_optional_columns(table, payload, match, use_admin=False, action="update")


def update_row_admin(table: str, payload: dict[str, Any], match: dict[str, Any]) -> ServiceResult:
    """Server-side update using service role (Streamlit writes when user JWT may be stale)."""
    return _update_with_optional_columns(table, payload, match, use_admin=True, action="update")


def delete_row(table: str, match: dict[str, Any]) -> ServiceResult:
    try:
        rows = _db().delete_rows(table, match)
        clear_data_cache_for_table(table)
        return ServiceResult(ok=True, data=rows)
    except Exception as exc:
        msg = _friendly_repo_error(exc, table=table, action="delete from")
        _LOG.warning("delete_row %s failed: %s", table, exc)
        return ServiceResult(ok=False, error=msg)


def delete_row_admin(table: str, match: dict[str, Any]) -> ServiceResult:
    """Server-side delete using service role."""
    try:
        rows = _db().delete_rows_admin(table, match)
        clear_data_cache_for_table(table)
        return ServiceResult(ok=True, data=rows)
    except Exception as exc:
        msg = _friendly_repo_error(exc, table=table, action="delete from")
        _LOG.warning("delete_row_admin %s failed: %s", table, exc)
        return ServiceResult(ok=False, error=msg)


def user_facing_error(result: ServiceResult, *, demo_ok_message: str | None = None) -> str | None:
    """Message for st.error; None if ok."""
    if result.ok:
        return None
    err = str(result.error or "").strip()
    if not err:
        return "An unexpected error occurred."
    try:
        from app.auth import is_jwt_expired_error, SESSION_EXPIRED_USER_MESSAGE
    except ImportError:
        from auth import is_jwt_expired_error, SESSION_EXPIRED_USER_MESSAGE  # type: ignore
    if is_jwt_expired_error(RuntimeError(err)):
        return SESSION_EXPIRED_USER_MESSAGE
    return err
