from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from supabase import Client, create_client

try:
    from storage3.exceptions import StorageApiError
except ImportError:
    class StorageApiError(Exception):
        """Fallback when storage3 is not installed."""

from app.config import ROOT_DIR, settings

_LOG = logging.getLogger(__name__)

_client: Client | None = None
_admin_client: Client | None = None

_JOBS_STALE_COLUMN_DESCRIPTION = "description"
_JOBS_ORDER_BY_FOR_STALE_DESCRIPTION = "job_name"


def _normalize_jobs_query(*, columns: str, order_by: str | None) -> tuple[str, str | None]:
    col = (columns or "*").strip() or "*"
    if col != "*":
        parts: list[str] = []
        seen: set[str] = set()
        for raw in col.split(","):
            p = raw.strip()
            if not p:
                continue
            pl = p.lower()
            if pl == _JOBS_STALE_COLUMN_DESCRIPTION:
                mapped = "notes"
            else:
                mapped = p
            ml = mapped.lower()
            if ml not in seen:
                seen.add(ml)
                parts.append(mapped)
        col = ", ".join(parts) if parts else "*"

    ob: str | None = None
    if order_by:
        o = order_by.strip()
        if o.lower() == _JOBS_STALE_COLUMN_DESCRIPTION:
            _LOG.warning(
                "jobs: order_by=%r is not a real column; using %r instead.",
                order_by,
                _JOBS_ORDER_BY_FOR_STALE_DESCRIPTION,
            )
            ob = _JOBS_ORDER_BY_FOR_STALE_DESCRIPTION
        else:
            ob = o
    return col, ob


def get_client() -> Client:
    global _client
    if _client is None:
        public_key = (
            getattr(settings, "supabase_publishable_key", "")
            or getattr(settings, "supabase_anon_key", "")
        )
        if not settings.supabase_url or not public_key:
            raise RuntimeError("Supabase URL or public key is missing from .env")
        _client = create_client(settings.supabase_url, public_key)
    return _client


def get_admin_client() -> Client:
    global _admin_client
    if _admin_client is None:
        # Prefer legacy service-role JWT first, because your current RPC/admin path is rejecting
        # the newer secret key with "Invalid API key".
        secret_key = (
            getattr(settings, "supabase_service_role_key", "")
            or getattr(settings, "supabase_secret_key", "")
        )
        if not settings.supabase_url or not secret_key:
            raise RuntimeError("Supabase URL or admin key is missing from .env")
        _admin_client = create_client(settings.supabase_url, secret_key)
    return _admin_client


def _coerce_sequence_rpc_result(data: Any) -> int:
    if data is None:
        raise RuntimeError("ips_next_job_quote_seq returned no data")
    if isinstance(data, bool):
        raise RuntimeError("unexpected bool from ips_next_job_quote_seq")
    if isinstance(data, int):
        return data
    if isinstance(data, float) and data == int(data):
        return int(data)
    s = str(data).strip()
    if s.lstrip("-").isdigit():
        return int(s)
    if isinstance(data, list):
        if len(data) == 1:
            return _coerce_sequence_rpc_result(data[0])
        raise RuntimeError(f"unexpected list from ips_next_job_quote_seq: {data!r}")
    if isinstance(data, dict):
        for k in ("ips_next_job_quote_seq", "value"):
            if k in data:
                return _coerce_sequence_rpc_result(data[k])
        raise RuntimeError(f"unexpected dict from ips_next_job_quote_seq: {data!r}")
    raise RuntimeError(f"unexpected ips_next_job_quote_seq payload: {type(data)!r} {data!r}")


def allocate_next_shared_sequence_int() -> int:
    try:
        resp = get_admin_client().rpc("ips_next_job_quote_seq", {}).execute()
    except Exception as exc:
        raise RuntimeError(
            f"Could not allocate next sequence number. Supabase error: {exc!r}"
        ) from exc
    return _coerce_sequence_rpc_result(resp.data)


def fetch_table_admin(
    table_name: str,
    columns: str = "*",
    limit: int = 1000,
    order_by: str | None = None,
) -> list[dict[str, Any]]:
    if table_name == "jobs":
        columns, order_by = _normalize_jobs_query(columns=columns, order_by=order_by)
    query = get_admin_client().table(table_name).select(columns).limit(limit)
    if order_by:
        query = query.order(order_by)
    resp = query.execute()
    return resp.data or []


def fetch_table(
    table_name: str,
    columns: str = "*",
    limit: int = 1000,
    order_by: str | None = None,
) -> list[dict[str, Any]]:
    if table_name == "jobs":
        columns, order_by = _normalize_jobs_query(columns=columns, order_by=order_by)
    query = get_client().table(table_name).select(columns).limit(limit)
    if order_by:
        query = query.order(order_by)
    resp = query.execute()
    return resp.data or []


def fetch_table_with_order_fallback(
    table_name: str,
    columns: str = "*",
    limit: int = 1000,
    order_by: str | None = None,
) -> list[dict[str, Any]]:
    if not order_by:
        return fetch_table(table_name, columns=columns, limit=limit, order_by=None)
    try:
        return fetch_table(table_name, columns=columns, limit=limit, order_by=order_by)
    except Exception as exc:
        _LOG.warning(
            "fetch_table %r order_by=%r failed (%s); retrying without order.",
            table_name,
            order_by,
            exc,
        )
        return fetch_table(table_name, columns=columns, limit=limit, order_by=None)


def fetch_by_match(
    table_name: str,
    match: dict[str, Any],
    columns: str = "*",
    limit: int = 1000,
) -> list[dict[str, Any]]:
    if table_name == "jobs":
        columns, _ = _normalize_jobs_query(columns=columns, order_by=None)
    query = get_client().table(table_name).select(columns).limit(limit)
    for key, value in match.items():
        query = query.eq(key, value)
    resp = query.execute()
    return resp.data or []


def fetch_by_match_admin(
    table_name: str,
    match: dict[str, Any],
    columns: str = "*",
    limit: int = 1000,
) -> list[dict[str, Any]]:
    if table_name == "jobs":
        columns, _ = _normalize_jobs_query(columns=columns, order_by=None)
    query = get_admin_client().table(table_name).select(columns).limit(limit)
    for key, value in match.items():
        query = query.eq(key, value)
    resp = query.execute()
    return resp.data or []


def fetch_one(
    table_name: str,
    match: dict[str, Any],
    columns: str = "*",
) -> dict[str, Any] | None:
    rows = fetch_by_match(table_name, match, columns=columns, limit=1)
    return rows[0] if rows else None


def insert_row(
    table_name: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    resp = get_client().table(table_name).insert(payload).execute()
    rows = resp.data or []
    if not rows:
        raise RuntimeError(
            f"Insert into {table_name!r} returned no rows; check RLS and table permissions."
        )
    return rows[0]


def update_rows(
    table_name: str,
    payload: dict[str, Any],
    match: dict[str, Any],
) -> list[dict[str, Any]]:
    query = get_client().table(table_name).update(payload)
    for key, value in match.items():
        query = query.eq(key, value)
    resp = query.execute()
    return resp.data or []


def delete_rows(
    table_name: str,
    match: dict[str, Any],
) -> list[dict[str, Any]]:
    query = get_client().table(table_name).delete()
    for key, value in match.items():
        query = query.eq(key, value)
    resp = query.execute()
    return resp.data or []


def insert_row_admin(
    table_name: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    resp = get_admin_client().table(table_name).insert(payload).execute()
    rows = resp.data or []
    if not rows:
        raise RuntimeError(
            f"Insert into {table_name!r} returned no rows; check schema and service-role permissions."
        )
    return rows[0]


def update_rows_admin(
    table_name: str,
    payload: dict[str, Any],
    match: dict[str, Any],
) -> list[dict[str, Any]]:
    query = get_admin_client().table(table_name).update(payload)
    for key, value in match.items():
        query = query.eq(key, value)
    resp = query.execute()
    return resp.data or []


def delete_rows_admin(
    table_name: str,
    match: dict[str, Any],
) -> list[dict[str, Any]]:
    query = get_admin_client().table(table_name).delete()
    for key, value in match.items():
        query = query.eq(key, value)
    resp = query.execute()
    return resp.data or []


def _storage_is_local() -> bool:
    return getattr(settings, "storage_backend", "supabase") == "local"


def storage_is_local() -> bool:
    return _storage_is_local()


def _local_storage_root() -> Path:
    raw = getattr(settings, "local_storage_root", "") or ""
    if raw:
        return Path(raw).expanduser().resolve()
    return (ROOT_DIR / "data" / "ips_storage").resolve()


def _normalize_storage_key(storage_path: str) -> str:
    s = storage_path.replace("\\", "/").strip().lstrip("/")
    if any(part == ".." for part in s.split("/")):
        raise ValueError(f"Invalid storage path: {storage_path!r}")
    return s


def _local_file_path(storage_path: str) -> Path:
    key = _normalize_storage_key(storage_path)
    root = _local_storage_root()
    full = (root / key).resolve()
    if not str(full).startswith(str(root)):
        raise ValueError(f"Storage path escapes root: {storage_path!r}")
    return full


def _upload_bytes_local(
    storage_path: str,
    data: bytes,
    content_type: str = "application/octet-stream",
) -> str:
    _ = content_type
    dest = _local_file_path(storage_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    _LOG.debug("Local storage wrote %s (%s bytes)", dest, len(data))
    return storage_path


def _storage_upload_options(content_type: str) -> dict[str, str]:
    return {
        "content-type": content_type,
        "upsert": "true",
        "x-upsert": "true",
    }


def upload_bytes_admin(
    storage_path: str,
    data: bytes,
    content_type: str = "application/octet-stream",
) -> str:
    if _storage_is_local():
        return _upload_bytes_local(storage_path, data, content_type)

    client = get_admin_client()
    bucket = client.storage.from_(settings.storage_bucket)
    opts = _storage_upload_options(content_type)
    try:
        bucket.upload(path=storage_path, file=data, file_options=dict(opts))
    except StorageApiError as exc:
        msg = (exc.message or "").lower()
        status = 0
        try:
            st_raw = str(exc.status).strip()
            if st_raw:
                status = int(st_raw) if st_raw.isdigit() else int(st_raw.split()[0])
        except Exception:
            status = 0
        if status == 409 or "duplicate" in msg or "already exists" in msg:
            _LOG.info("Storage upload conflict for %s; retrying with update()", storage_path)
            bucket.update(path=storage_path, file=data, file_options=dict(opts))
        else:
            raise
    return storage_path


def delete_storage_object_admin(storage_path: str) -> None:
    key = str(storage_path or "").strip()
    if not key:
        return
    if _storage_is_local():
        try:
            p = _local_file_path(key)
        except ValueError:
            _LOG.warning("Invalid storage path for delete: %s", storage_path)
            return
        if p.is_file():
            p.unlink()
            _LOG.debug("Local storage deleted %s", p)
        return

    norm = _normalize_storage_key(key)
    client = get_admin_client()
    bucket = client.storage.from_(settings.storage_bucket)
    try:
        bucket.remove([norm])
    except StorageApiError as exc:
        _LOG.warning("Storage remove failed for %s: %s", norm, exc)
        raise


def upload_bytes(
    storage_path: str,
    data: bytes,
    content_type: str = "application/octet-stream",
) -> str:
    return upload_bytes_admin(storage_path, data, content_type)


def _signed_url_from_response(resp: Any) -> str:
    if resp is None:
        return ""
    if isinstance(resp, dict):
        return str(
            resp.get("signedURL")
            or resp.get("signedUrl")
            or resp.get("signed_url")
            or ""
        )
    return str(
        getattr(resp, "signedURL", None)
        or getattr(resp, "signedUrl", None)
        or getattr(resp, "signed_url", None)
        or ""
    )


def create_signed_url(
    storage_path: str,
    expires_in: int = 3600,
) -> str:
    if _storage_is_local():
        _ = expires_in
        try:
            p = _local_file_path(storage_path)
        except ValueError:
            return ""
        if p.is_file():
            return str(p)
        return ""

    client = get_admin_client()
    resp = client.storage.from_(settings.storage_bucket).create_signed_url(storage_path, expires_in)
    return _signed_url_from_response(resp)


try:
    from app.services.shared_sequence import next_quote_number_string
except ImportError:
    from services.shared_sequence import next_quote_number_string  # type: ignore


def next_quote_number() -> str:
    return next_quote_number_string()


def quote_number_in_use(quote_number: str, exclude_estimate_id: str | None = None) -> bool:
    qn = str(quote_number or "").strip()
    if not qn:
        return False
    query = get_admin_client().table("estimates").select("id").eq("quote_number", qn).limit(20)
    resp = query.execute()
    rows = resp.data or []
    for row in rows:
        if exclude_estimate_id and row.get("id") == exclude_estimate_id:
            continue
        return True
    return False


def create_auth_user(
    email: str,
    password: str,
    role: str = "viewer",
    full_name: str = "",
) -> dict[str, Any]:
    admin = get_admin_client()
    result = admin.auth.admin.create_user(
        {
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {"full_name": full_name, "role": role},
        }
    )

    user = getattr(result, "user", None)
    if user is None and isinstance(result, dict):
        user = result.get("user")
    if user is None:
        raise RuntimeError("Supabase did not return a created user.")

    user_id = getattr(user, "id", None) or user.get("id")
    user_email = getattr(user, "email", None) or user.get("email") or email

    profile_payload = {
        "id": user_id,
        "email": user_email,
        "full_name": full_name,
        "role": role,
        "is_active": True,
    }

    existing = fetch_one("profiles", {"id": user_id})
    if existing:
        update_rows_admin("profiles", profile_payload, {"id": user_id})
    else:
        get_admin_client().table("profiles").insert(profile_payload).execute()

    return {
        "id": user_id,
        "email": user_email,
        "role": role,
        "full_name": full_name,
    }