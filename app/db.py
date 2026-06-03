from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from supabase import Client, create_client

try:
    from storage3.exceptions import StorageApiError
except ImportError:
    class StorageApiError(Exception):
        """Fallback when storage3 is not installed."""

try:
    from app.config import ROOT_DIR, settings
except ImportError:
    from config import ROOT_DIR, settings  # type: ignore

_LOG = logging.getLogger(__name__)

try:
    import streamlit as _st_for_cache
except ImportError:  # scripts / tests without Streamlit
    _st_for_cache = None  # type: ignore


def _create_public_supabase_client(url: str, key: str) -> Client:
    _patch_supabase_publishable_keys()
    return create_client(url.strip(), key.strip())


def _create_admin_supabase_client(url: str, key: str) -> Client:
    _patch_supabase_publishable_keys()
    return create_client(url.strip(), key.strip())


if _st_for_cache is not None:
    _cached_public_supabase = _st_for_cache.cache_resource(_create_public_supabase_client)
    _cached_admin_supabase = _st_for_cache.cache_resource(_create_admin_supabase_client)
else:
    _cached_public_supabase = _create_public_supabase_client
    _cached_admin_supabase = _create_admin_supabase_client

_client_fallback: Client | None = None
_admin_client_fallback: Client | None = None
_supabase_publishable_patch_applied = False


def _patch_supabase_publishable_keys() -> None:
    """
    supabase-py < 2.16 rejects ``sb_publishable_*`` / ``sb_secret_*`` keys in ``SyncClient.__init__``.

    The API accepts them; only the client-side JWT regex is wrong. Patch once per process.
    """
    global _supabase_publishable_patch_applied
    if _supabase_publishable_patch_applied:
        return
    try:
        from gotrue import SyncMemoryStorage
        from supabase._sync.client import SupabaseException, SyncClient
        from supabase.lib.client_options import SyncClientOptions
    except ImportError:
        return

    import re

    _original_init = SyncClient.__init__

    def _init(self, supabase_url: str, supabase_key: str, options=None):
        key_s = str(supabase_key or "").strip()
        if not key_s.startswith(("sb_publishable_", "sb_secret_")):
            return _original_init(self, supabase_url, supabase_key, options)

        if not supabase_url:
            raise SupabaseException("supabase_url is required")
        if not supabase_key:
            raise SupabaseException("supabase_key is required")
        if not re.match(r"^(https?)://.+", supabase_url):
            raise SupabaseException("Invalid URL")
        if options is None:
            options = SyncClientOptions(storage=SyncMemoryStorage())

        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.options = options
        options.headers.update(self._get_auth_headers())
        self.rest_url = f"{supabase_url}/rest/v1"
        self.realtime_url = f"{supabase_url}/realtime/v1".replace("http", "ws")
        self.auth_url = f"{supabase_url}/auth/v1"
        self.storage_url = f"{supabase_url}/storage/v1"
        self.functions_url = f"{supabase_url}/functions/v1"
        self.auth = self._init_supabase_auth_client(
            auth_url=self.auth_url,
            client_options=options,
        )
        self.realtime = self._init_realtime_client(
            realtime_url=self.realtime_url,
            supabase_key=self.supabase_key,
            options=options.realtime if options else None,
        )
        self._postgrest = None
        self._storage = None
        self._functions = None
        self.auth.on_auth_state_change(self._listen_to_auth_events)

    SyncClient.__init__ = _init  # type: ignore[method-assign]
    _supabase_publishable_patch_applied = True


_patch_supabase_publishable_keys()

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


def _public_api_key() -> str:
    """Anon / publishable key only (browser-safe)."""
    return (
        (getattr(settings, "supabase_publishable_key", "") or "").strip()
        or (getattr(settings, "supabase_anon_key", "") or "").strip()
    )


def _admin_api_key_and_source() -> tuple[str, str]:
    """
    Service-role JWT for admin RPC/storage/auth.admin.

    Prefer ``SUPABASE_SERVICE_ROLE_KEY``; only if unset, use ``SUPABASE_SECRET_KEY``
    (some projects store the service role under the newer name).

    Returns ``(key, source_label)`` where ``source_label`` is safe to log (no secret material).
    """
    sr = (getattr(settings, "supabase_service_role_key", "") or "").strip()
    if sr:
        return sr, "SUPABASE_SERVICE_ROLE_KEY"
    sk = (getattr(settings, "supabase_secret_key", "") or "").strip()
    if sk:
        return sk, "SUPABASE_SECRET_KEY"
    return "", ""


def get_client() -> Client:
    """
    Supabase client with the **publishable / anon** key only (RLS applies).

    The underlying ``create_client`` is wrapped with ``streamlit.cache_resource`` so the
    heavy client is built once per process per (url, key) pair.
    """
    try:
        from app.config import validate_supabase_public_config
    except ImportError:
        from config import validate_supabase_public_config  # type: ignore

    cfg_err = validate_supabase_public_config()
    if cfg_err:
        raise RuntimeError(cfg_err)

    public_key = _public_api_key()
    url = (settings.supabase_url or "").strip()
    if not url or not public_key:
        raise RuntimeError(
            "Supabase URL or public API key is missing. Set SUPABASE_URL and "
            "SUPABASE_PUBLISHABLE_KEY or SUPABASE_ANON_KEY in `.streamlit/secrets.toml` or `.env`."
        )
    if _st_for_cache is not None:
        try:
            return _cached_public_supabase(url, public_key)
        except Exception as exc:
            raise RuntimeError(f"create_client (anon) failed: {exc!r}") from exc
    global _client_fallback
    if _client_fallback is None:
        try:
            _client_fallback = _create_public_supabase_client(url, public_key)
        except Exception as exc:
            raise RuntimeError(f"create_client (anon) failed: {exc!r}") from exc
    return _client_fallback


def get_admin_client() -> Client:
    """
    Supabase client with a **service-role** key (bypasses RLS for admin operations).

    Key resolution: ``SUPABASE_SERVICE_ROLE_KEY`` first, then ``SUPABASE_SECRET_KEY``.
    """
    key, source = _admin_api_key_and_source()
    url = (settings.supabase_url or "").strip()
    if not url or not key:
        raise RuntimeError(
            "Supabase URL or admin API key is missing. Set SUPABASE_URL and either "
            "SUPABASE_SERVICE_ROLE_KEY (preferred) or SUPABASE_SECRET_KEY for server-side admin access."
        )
    _LOG.debug("Creating Supabase admin client using credentials from %s", source)
    if _st_for_cache is not None:
        try:
            return _cached_admin_supabase(url, key)
        except Exception as exc:
            raise RuntimeError(f"create_client (admin) failed: {exc!r}") from exc
    global _admin_client_fallback
    if _admin_client_fallback is None:
        try:
            _admin_client_fallback = _create_admin_supabase_client(url, key)
        except Exception as exc:
            raise RuntimeError(f"create_client (admin) failed: {exc!r}") from exc
    return _admin_client_fallback


def allocate_next_shared_sequence_int() -> int:
    """Call DB RPC ``ips_next_yearly_seq`` (implementation in ``services.shared_sequence``)."""
    try:
        from app.services.shared_sequence import get_next_sequence_number
    except ImportError:
        from services.shared_sequence import get_next_sequence_number  # type: ignore
    return get_next_sequence_number()


def _auth_fp_for_streamlit_cache() -> str:
    """Auth partition for cached reads (RLS); avoids cross-user cache hits in Streamlit."""
    if _st_for_cache is None:
        return "__no_st__"
    try:
        u = _st_for_cache.session_state.get("auth_user")
        if u is None:
            return "__anon__"
        uid = getattr(u, "id", None)
        if uid is None and isinstance(u, dict):
            uid = u.get("id")
        s = str(uid or "").strip()
        return s or "__anon__"
    except Exception:
        return "__anon__"


def _match_json_for_cache(match: dict[str, Any]) -> str:
    return json.dumps(match or {}, sort_keys=True, default=str)


def _fetch_table_query(
    table_name: str,
    columns: str,
    limit: int,
    order_by: str | None,
    *,
    use_admin: bool,
) -> list[dict[str, Any]]:
    if table_name == "jobs":
        columns, order_by = _normalize_jobs_query(columns=columns, order_by=order_by)
    client = get_admin_client() if use_admin else get_client()
    query = client.table(table_name).select(columns).limit(limit)
    if order_by:
        query = query.order(order_by)
    try:
        resp = query.execute()
    except Exception as exc:
        tag = "fetch_table_admin" if use_admin else "fetch_table"
        raise RuntimeError(f"{tag}({table_name!r}) failed: {exc!r}") from exc
    return resp.data or []


def _fetch_by_match_query(
    table_name: str,
    match: dict[str, Any],
    columns: str,
    limit: int,
    *,
    use_admin: bool,
) -> list[dict[str, Any]]:
    if table_name == "jobs":
        columns, _ = _normalize_jobs_query(columns=columns, order_by=None)
    client = get_admin_client() if use_admin else get_client()
    query = client.table(table_name).select(columns).limit(limit)
    for key, value in match.items():
        query = query.eq(key, value)
    try:
        resp = query.execute()
    except Exception as exc:
        tag = "fetch_by_match_admin" if use_admin else "fetch_by_match"
        raise RuntimeError(f"{tag}({table_name!r}) failed: {exc!r}") from exc
    return resp.data or []


if _st_for_cache is not None:

    @_st_for_cache.cache_data(ttl=30)
    def _fetch_table_cached(
        table_name: str,
        columns: str,
        limit: int,
        order_by: str | None,
        _auth_fp: str,
    ) -> list[dict[str, Any]]:
        return _fetch_table_query(table_name, columns, limit, order_by, use_admin=False)

    @_st_for_cache.cache_data(ttl=30)
    def _fetch_table_admin_cached(
        table_name: str,
        columns: str,
        limit: int,
        order_by: str | None,
        _admin_partition: str,
    ) -> list[dict[str, Any]]:
        _ = _admin_partition
        return _fetch_table_query(table_name, columns, limit, order_by, use_admin=True)

    @_st_for_cache.cache_data(ttl=30)
    def _fetch_by_match_cached(
        table_name: str,
        match_json: str,
        columns: str,
        limit: int,
        _auth_fp: str,
    ) -> list[dict[str, Any]]:
        return _fetch_by_match_query(
            table_name, json.loads(match_json), columns, limit, use_admin=False
        )

    @_st_for_cache.cache_data(ttl=30)
    def _fetch_by_match_admin_cached(
        table_name: str,
        match_json: str,
        columns: str,
        limit: int,
        _admin_partition: str,
    ) -> list[dict[str, Any]]:
        _ = _admin_partition
        return _fetch_by_match_query(
            table_name, json.loads(match_json), columns, limit, use_admin=True
        )

else:

    def _fetch_table_cached(
        table_name: str,
        columns: str,
        limit: int,
        order_by: str | None,
        _auth_fp: str,
    ) -> list[dict[str, Any]]:
        return _fetch_table_query(table_name, columns, limit, order_by, use_admin=False)

    def _fetch_table_admin_cached(
        table_name: str,
        columns: str,
        limit: int,
        order_by: str | None,
        _admin_partition: str,
    ) -> list[dict[str, Any]]:
        return _fetch_table_query(table_name, columns, limit, order_by, use_admin=True)

    def _fetch_by_match_cached(
        table_name: str,
        match_json: str,
        columns: str,
        limit: int,
        _auth_fp: str,
    ) -> list[dict[str, Any]]:
        return _fetch_by_match_query(
            table_name, json.loads(match_json), columns, limit, use_admin=False
        )

    def _fetch_by_match_admin_cached(
        table_name: str,
        match_json: str,
        columns: str,
        limit: int,
        _admin_partition: str,
    ) -> list[dict[str, Any]]:
        return _fetch_by_match_query(
            table_name, json.loads(match_json), columns, limit, use_admin=True
        )


def clear_streamlit_db_read_cache() -> None:
    """Invalidate short-TTL read caches after writes (Streamlit ``cache_data`` only)."""
    if _st_for_cache is None:
        return
    for fn in (
        _fetch_table_cached,
        _fetch_table_admin_cached,
        _fetch_by_match_cached,
        _fetch_by_match_admin_cached,
    ):
        cl = getattr(fn, "clear", None)
        if callable(cl):
            try:
                cl()
            except Exception:
                pass


def fetch_table_admin(
    table_name: str,
    columns: str = "*",
    limit: int = 1000,
    order_by: str | None = None,
) -> list[dict[str, Any]]:
    return _fetch_table_admin_cached(table_name, columns, limit, order_by, "__admin__")


def fetch_table(
    table_name: str,
    columns: str = "*",
    limit: int = 1000,
    order_by: str | None = None,
) -> list[dict[str, Any]]:
    return _fetch_table_cached(
        table_name, columns, limit, order_by, _auth_fp_for_streamlit_cache()
    )


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
    except Exception:
        _LOG.warning(
            "fetch_table %r order_by=%r failed; retrying without order (see traceback).",
            table_name,
            order_by,
            exc_info=True,
        )
        return fetch_table(table_name, columns=columns, limit=limit, order_by=None)


def fetch_rows_unfiltered(
    table_name: str,
    *,
    limit: int = 5000,
    order_by: str | None = None,
    use_admin: bool = False,
) -> list[dict[str, Any]]:
    """
    ``select('*')`` with optional ``order_by`` — same normalization as :func:`fetch_table`
    (e.g. jobs column mapping). Use ``use_admin=True`` for service-role reads when RLS hides rows.
    """
    fn = fetch_table_admin if use_admin else fetch_table
    return fn(table_name, columns="*", limit=limit, order_by=order_by)


def fetch_jobs_with_order_fallback(
    *,
    limit: int = 5000,
    use_admin: bool = False,
) -> list[dict[str, Any]]:
    """
    Load ``public.jobs`` with ``select('*')``, trying common ``order_by`` columns until one works.

    Use when typed column lists fail (schema drift) or to diagnose empty Job Database grids.
    """
    last_err: BaseException | None = None
    for ob in ("created_at", "updated_at", "job_number", "job_name", "status", None):
        try:
            return fetch_rows_unfiltered("jobs", limit=limit, order_by=ob, use_admin=use_admin)
        except Exception as exc:
            last_err = exc
            _LOG.debug("fetch_jobs_with_order_fallback order_by=%r failed: %s", ob, exc)
    if last_err is not None:
        _LOG.warning("fetch_jobs_with_order_fallback: all order attempts failed: %s", last_err)
    return []


def fetch_by_match(
    table_name: str,
    match: dict[str, Any],
    columns: str = "*",
    limit: int = 1000,
) -> list[dict[str, Any]]:
    return _fetch_by_match_cached(
        table_name,
        _match_json_for_cache(match),
        columns,
        limit,
        _auth_fp_for_streamlit_cache(),
    )


def fetch_by_match_admin(
    table_name: str,
    match: dict[str, Any],
    columns: str = "*",
    limit: int = 1000,
) -> list[dict[str, Any]]:
    return _fetch_by_match_admin_cached(
        table_name,
        _match_json_for_cache(match),
        columns,
        limit,
        "__admin__",
    )


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
    try:
        resp = get_client().table(table_name).insert(payload).execute()
    except Exception as exc:
        raise RuntimeError(f"insert into {table_name!r} failed: {exc!r}") from exc
    rows = resp.data or []
    if not rows:
        raise RuntimeError(
            f"Insert into {table_name!r} returned no rows; check RLS and table permissions. response={resp!r}"
        )
    clear_streamlit_db_read_cache()
    return rows[0]


def update_rows(
    table_name: str,
    payload: dict[str, Any],
    match: dict[str, Any],
) -> list[dict[str, Any]]:
    query = get_client().table(table_name).update(payload)
    for key, value in match.items():
        query = query.eq(key, value)
    try:
        resp = query.execute()
    except Exception as exc:
        raise RuntimeError(f"update_rows({table_name!r}) failed: {exc!r}") from exc
    clear_streamlit_db_read_cache()
    return resp.data or []


def delete_rows(
    table_name: str,
    match: dict[str, Any],
) -> list[dict[str, Any]]:
    query = get_client().table(table_name).delete()
    for key, value in match.items():
        query = query.eq(key, value)
    try:
        resp = query.execute()
    except Exception as exc:
        raise RuntimeError(f"delete_rows({table_name!r}) failed: {exc!r}") from exc
    clear_streamlit_db_read_cache()
    return resp.data or []


def insert_row_admin(
    table_name: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    try:
        resp = get_admin_client().table(table_name).insert(payload).execute()
    except Exception as exc:
        raise RuntimeError(f"insert_row_admin into {table_name!r} failed: {exc!r}") from exc
    rows = resp.data or []
    if not rows:
        raise RuntimeError(
            f"Insert into {table_name!r} returned no rows; check schema and service-role permissions. "
            f"response={resp!r}"
        )
    clear_streamlit_db_read_cache()
    return rows[0]


def update_rows_admin(
    table_name: str,
    payload: dict[str, Any],
    match: dict[str, Any],
) -> list[dict[str, Any]]:
    query = get_admin_client().table(table_name).update(payload)
    for key, value in match.items():
        query = query.eq(key, value)
    try:
        resp = query.execute()
    except Exception as exc:
        raise RuntimeError(f"update_rows_admin({table_name!r}) failed: {exc!r}") from exc
    clear_streamlit_db_read_cache()
    return resp.data or []


def delete_rows_admin(
    table_name: str,
    match: dict[str, Any],
) -> list[dict[str, Any]]:
    query = get_admin_client().table(table_name).delete()
    for key, value in match.items():
        query = query.eq(key, value)
    try:
        resp = query.execute()
    except Exception as exc:
        raise RuntimeError(f"delete_rows_admin({table_name!r}) failed: {exc!r}") from exc
    clear_streamlit_db_read_cache()
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


def _effective_storage_bucket(bucket: str | None) -> str:
    """Explicit bucket, else default app storage bucket."""
    if bucket and str(bucket).strip():
        return str(bucket).strip()
    return str(getattr(settings, "storage_bucket", "") or "ips-storage").strip()


def _local_file_path_for_storage(storage_path: str, bucket: str | None) -> Path:
    key = _normalize_storage_key(storage_path)
    root = _local_storage_root()
    default_b = str(getattr(settings, "storage_bucket", "") or "ips-storage").strip()
    eff = _effective_storage_bucket(bucket)
    if eff == default_b:
        full = (root / key).resolve()
    else:
        full = (root / eff / key).resolve()
    if not str(full).startswith(str(root)):
        raise ValueError(f"Storage path escapes root: {storage_path!r}")
    return full


def _local_file_path(storage_path: str) -> Path:
    return _local_file_path_for_storage(storage_path, None)


def _upload_bytes_local(
    storage_path: str,
    data: bytes,
    content_type: str = "application/octet-stream",
    *,
    bucket: str | None = None,
) -> str:
    _ = content_type
    dest = _local_file_path_for_storage(storage_path, bucket)
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
    *,
    bucket: str | None = None,
) -> str:
    if _storage_is_local():
        return _upload_bytes_local(storage_path, data, content_type, bucket=bucket)

    client = get_admin_client()
    bucket_name = _effective_storage_bucket(bucket)
    st_bucket = client.storage.from_(bucket_name)
    opts = _storage_upload_options(content_type)
    try:
        st_bucket.upload(path=storage_path, file=data, file_options=dict(opts))
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
            try:
                st_bucket.update(path=storage_path, file=data, file_options=dict(opts))
            except Exception as upd_exc:
                raise RuntimeError(
                    f"Storage update after 409 failed for {storage_path!r}: {upd_exc!r}"
                ) from upd_exc
        else:
            raise
    return storage_path


def delete_storage_object_admin(storage_path: str, *, bucket: str | None = None) -> None:
    key = str(storage_path or "").strip()
    if not key:
        return
    if _storage_is_local():
        try:
            p = _local_file_path_for_storage(key, bucket)
        except ValueError:
            _LOG.warning("Invalid storage path for delete: %s", storage_path, exc_info=True)
            return
        if p.is_file():
            p.unlink()
            _LOG.debug("Local storage deleted %s", p)
        return

    norm = _normalize_storage_key(key)
    client = get_admin_client()
    bucket_name = _effective_storage_bucket(bucket)
    st_bucket = client.storage.from_(bucket_name)
    try:
        st_bucket.remove([norm])
    except StorageApiError:
        _LOG.warning("Storage remove failed for %s", norm, exc_info=True)
        raise


def upload_bytes(
    storage_path: str,
    data: bytes,
    content_type: str = "application/octet-stream",
    *,
    bucket: str | None = None,
) -> str:
    return upload_bytes_admin(storage_path, data, content_type, bucket=bucket)


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
    *,
    bucket: str | None = None,
) -> str:
    if _storage_is_local():
        _ = expires_in
        try:
            p = _local_file_path_for_storage(storage_path, bucket)
        except ValueError:
            return ""
        if p.is_file():
            return str(p)
        return ""

    client = get_admin_client()
    bucket_name = _effective_storage_bucket(bucket)
    try:
        resp = client.storage.from_(bucket_name).create_signed_url(storage_path, expires_in)
    except Exception as exc:
        raise RuntimeError(f"create_signed_url failed for {storage_path!r}: {exc!r}") from exc
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
    try:
        resp = query.execute()
    except Exception as exc:
        raise RuntimeError(f"quote_number_in_use query failed: {exc!r}") from exc
    rows = resp.data or []
    for row in rows:
        if exclude_estimate_id and row.get("id") == exclude_estimate_id:
            continue
        return True
    return False


def job_number_in_use(job_number: str, exclude_job_id: str | None = None) -> bool:
    jn = str(job_number or "").strip()
    if not jn:
        return False
    query = get_admin_client().table("jobs").select("id").eq("job_number", jn).limit(20)
    try:
        resp = query.execute()
    except Exception as exc:
        raise RuntimeError(f"job_number_in_use query failed: {exc!r}") from exc
    rows = resp.data or []
    for row in rows:
        if exclude_job_id and row.get("id") == exclude_job_id:
            continue
        return True
    return False


def create_auth_user(
    email: str,
    password: str,
    role: str = "viewer",
    full_name: str = "",
) -> dict[str, Any]:
    em_norm = str(email or "").strip().lower()
    if not em_norm:
        raise RuntimeError("Email is required.")
    if "@" not in em_norm:
        raise RuntimeError("A valid email is required.")
    if "indfustrial" in em_norm:
        raise RuntimeError("Check spelling of company domain (found 'indfustrial').")
    allowed_domain = (
        str(getattr(settings, "allowed_email_domain", "") or getattr(settings, "company_email_domain", "") or "").strip().lower()
        or "industrialplantsolution.com"
    )
    if allowed_domain:
        dom = em_norm.split("@", 1)[1]
        if dom != allowed_domain:
            raise RuntimeError("Email domain not allowed.")

    admin = get_admin_client()
    try:
        result = admin.auth.admin.create_user(
            {
                "email": em_norm,
                "password": password,
                "email_confirm": True,
                "user_metadata": {"full_name": full_name, "role": role},
            }
        )
    except Exception as exc:
        raise RuntimeError(f"auth.admin.create_user failed for {email!r}: {exc!r}") from exc

    user = getattr(result, "user", None)
    if user is None and isinstance(result, dict):
        user = result.get("user")
    if user is None:
        raise RuntimeError(f"Supabase did not return a created user. raw_result={result!r}")

    user_id = getattr(user, "id", None) or user.get("id")
    user_email = getattr(user, "email", None) or user.get("email") or em_norm

    profile_payload = {
        "id": user_id,
        "email": str(user_email or "").strip().lower() or em_norm,
        "full_name": full_name,
        "role": role,
        "is_active": True,
    }

    existing = fetch_one("profiles", {"id": user_id})
    try:
        if existing:
            update_rows_admin("profiles", profile_payload, {"id": user_id})
        else:
            get_admin_client().table("profiles").insert(profile_payload).execute()
    except Exception as exc:
        raise RuntimeError(
            f"profiles upsert failed after auth user creation (user_id={user_id!r}): {exc!r}"
        ) from exc

    # Best-effort: auto-link employee by email when possible (prevents "unlinked" accounts)
    try:
        emp_rows = fetch_table_admin("employees", columns="id,email,profile_id,auth_user_id,name", limit=5000, order_by="name")
    except Exception:
        emp_rows = []
    try:
        matches = [e for e in (emp_rows or []) if str(e.get("email") or "").strip().lower() == str(profile_payload.get("email") or "").strip().lower()]
        if len(matches) == 1:
            eid = str(matches[0].get("id") or "").strip()
            if eid:
                try:
                    update_rows_admin("profiles", {"employee_id": eid}, {"id": user_id})
                except Exception:
                    pass
                for col in ("auth_user_id", "profile_id"):
                    try:
                        update_rows_admin("employees", {col: str(user_id)}, {"id": eid})
                        break
                    except Exception:
                        continue
    except Exception:
        pass

    return {
        "id": user_id,
        "email": user_email,
        "role": role,
        "full_name": full_name,
    }


def invite_auth_user(
    *,
    email: str,
    role: str = "employee",
    employee_id: str | None = None,
    require_employee_link: bool = True,
) -> dict[str, Any]:
    """
    Invite a user by email (magic link) using Supabase Admin API.

    Also ensures a `public.profiles` row exists with `must_reset_password=true`.
    """
    em = str(email or "").strip().lower()
    if not em:
        raise RuntimeError("Email is required.")
    if "indfustrial" in em:
        raise RuntimeError("Check spelling of company domain (found 'indfustrial').")
    if "@" not in em:
        raise RuntimeError("A valid email is required.")
    allowed_domain = (
        str(getattr(settings, "allowed_email_domain", "") or getattr(settings, "company_email_domain", "") or "").strip().lower()
        or "industrialplantsolution.com"
    )
    if allowed_domain:
        dom = em.split("@", 1)[1]
        if dom != allowed_domain:
            raise RuntimeError("Email domain not allowed.")

    # Duplicate prevention: block invites when a profile already uses this email.
    try:
        existing_email = fetch_by_match_admin("profiles", {"email": em}, columns="id,email", limit=2)  # type: ignore[name-defined]
    except Exception:
        existing_email = []
    if existing_email:
        raise RuntimeError("A login/profile already exists for this email.")

    # Load employees and find match by normalized email (best-effort; employees.email is optional)
    emp_rows: list[dict[str, Any]] = []
    employees_has_email = False
    try:
        emp_rows = fetch_table_admin("employees", columns="id,email,profile_id,auth_user_id,name", limit=5000, order_by="name")  # type: ignore[name-defined]
        employees_has_email = any("email" in (r or {}) for r in emp_rows or [])
    except Exception:
        emp_rows = []
        employees_has_email = False

    def _norm_email(v: object) -> str:
        return " ".join(str(v or "").strip().lower().split())

    matched_emp_id: str | None = None
    if employees_has_email:
        matches = []
        for e in emp_rows or []:
            if _norm_email(e.get("email")) == _norm_email(em):
                matches.append(e)
        if len(matches) > 1:
            raise RuntimeError("Multiple employees share this email. Fix employee emails before inviting.")
        if len(matches) == 1:
            matched_emp_id = str(matches[0].get("id") or "").strip() or None

    if employee_id:
        matched_emp_id = str(employee_id or "").strip() or None
        # Block mismatch: selected employee must match the email (when employees.email exists)
        try:
            cur_emp = next((e for e in emp_rows if str(e.get("id") or "").strip() == matched_emp_id), None) or {}
            emp_email = str(cur_emp.get("email") or "").strip().lower()
            if emp_email and emp_email != em:
                raise RuntimeError("Employee email does not match invite email.")
        except RuntimeError:
            raise
        except Exception:
            pass

    # Prevent linking an employee that already has a different login
    if matched_emp_id:
        cur_emp = next((e for e in emp_rows if str(e.get("id") or "").strip() == matched_emp_id), None) or {}
        cur_auth = str(cur_emp.get("auth_user_id") or "").strip()
        cur_prof = str(cur_emp.get("profile_id") or "").strip()
        if cur_auth or cur_prof:
            raise RuntimeError("Employee already has login.")

    # Enforce: no standalone login accounts for work roles (preferred behavior).
    role_norm = str(role or "employee").strip().lower() or "employee"
    if role_norm in {"pm", "estimator"}:
        role_norm = "manager"
    if require_employee_link and role_norm not in {"admin", "viewer"} and not matched_emp_id:
        raise RuntimeError("Select/create an employee with a matching email before inviting this role.")

    admin = get_admin_client()
    try:
        # supabase-py versions differ slightly; support both call shapes.
        fn = getattr(admin.auth.admin, "invite_user_by_email", None)
        if fn is None:
            raise AttributeError("auth.admin.invite_user_by_email is not available in this Supabase client.")
        base = str(getattr(settings, "app_base_url", "") or "").strip().rstrip("/")
        redirect_to = f"{base}/" if base else None
        try:
            if redirect_to:
                result = fn(em, {"redirect_to": redirect_to})
            else:
                result = fn(em)
        except TypeError:
            try:
                if redirect_to:
                    result = fn({"email": em, "options": {"redirect_to": redirect_to}})
                else:
                    result = fn({"email": em})
            except TypeError:
                try:
                    result = fn(em)
                except TypeError:
                    result = fn({"email": em})
    except Exception as exc:
        raise RuntimeError(f"Could not send invite for {em!r}: {exc!r}") from exc

    user = getattr(result, "user", None)
    if user is None and isinstance(result, dict):
        user = result.get("user")
    if user is None:
        raise RuntimeError(f"Supabase did not return an invited user. raw_result={result!r}")

    user_id = getattr(user, "id", None) or (user.get("id") if isinstance(user, dict) else None)
    user_email = getattr(user, "email", None) or (user.get("email") if isinstance(user, dict) else None) or em
    if not user_id:
        raise RuntimeError(f"Invite succeeded but Supabase did not return a user id. raw_user={user!r}")

    profile_payload: dict[str, Any] = {
        "id": user_id,
        "email": user_email,
        "role": role_norm,
        "is_active": True,
        "must_reset_password": True,
    }
    if matched_emp_id:
        profile_payload["employee_id"] = matched_emp_id

    # Upsert profile with service role (bypass RLS).
    try:
        existing = fetch_one("profiles", {"id": user_id})
        if existing:
            update_rows_admin("profiles", profile_payload, {"id": user_id})
        else:
            admin.table("profiles").insert(profile_payload).execute()
    except Exception as exc:
        raise RuntimeError(f"Invite sent, but creating the profile row failed: {exc!r}") from exc

    # Link employee back to this auth/profile id when possible (columns may not exist yet).
    if matched_emp_id:
        for col in ("auth_user_id", "profile_id"):
            try:
                update_rows_admin("employees", {col: str(user_id)}, {"id": matched_emp_id})
                break
            except Exception:
                continue
        # If employee email is blank, fill it from the invited email when column exists.
        if employees_has_email:
            try:
                cur = next((e for e in emp_rows if str(e.get("id") or "").strip() == matched_emp_id), None) or {}
                if not _norm_email(cur.get("email")):
                    update_rows_admin("employees", {"email": em}, {"id": matched_emp_id})
            except Exception:
                pass

    return {"id": str(user_id), "email": str(user_email), "role": str(role_norm)}


def _invite_redirect_url() -> str | None:
    base = str(getattr(settings, "app_base_url", "") or "").strip().rstrip("/")
    return f"{base}/" if base else None


def _profile_for_email(email: str) -> dict[str, Any] | None:
    em = str(email or "").strip().lower()
    if not em:
        return None
    try:
        rows = fetch_by_match_admin("profiles", {"email": em}, columns="id,email", limit=2)  # type: ignore[name-defined]
        if rows:
            return rows[0]
    except Exception:
        pass
    try:
        row = fetch_one("profiles", {"email": em})
        if row:
            return row
    except Exception:
        pass
    return None


def _admin_invite_user_by_email(email: str, *, redirect_to: str | None = None) -> None:
    """Send Supabase invite email; creates auth user when missing."""
    admin = get_admin_client()
    fn = getattr(admin.auth.admin, "invite_user_by_email", None)
    if fn is None:
        raise AttributeError("auth.admin.invite_user_by_email is not available in this Supabase client.")
    try:
        if redirect_to:
            fn(email, {"redirect_to": redirect_to})
        else:
            fn(email)
    except TypeError:
        try:
            if redirect_to:
                fn({"email": email, "options": {"redirect_to": redirect_to}})
            else:
                fn({"email": email})
        except TypeError:
            try:
                fn(email)
            except TypeError:
                fn({"email": email})


def _send_password_setup_email(email: str, *, redirect_to: str | None = None) -> None:
    """Email an existing auth user a link to set or reset their password."""
    client = get_client()
    fn = getattr(client.auth, "reset_password_for_email", None)
    if fn is None:
        raise AttributeError("auth.reset_password_for_email is not available in this Supabase client.")
    opts = {"redirect_to": redirect_to} if redirect_to else {}
    try:
        if opts:
            fn(email, opts)
        else:
            fn(email)
    except TypeError:
        if opts:
            fn(email, options=opts)
        else:
            fn(email)


def resend_invite_by_email(*, email: str) -> None:
    """
    Re-send access email for an invited or existing login.

    New users get a Supabase invite. Existing linked logins get a password-setup
    email instead of ``invite_user_by_email`` (which fails once auth.users exists).
    """
    em = str(email or "").strip().lower()
    if not em:
        raise RuntimeError("Email is required.")
    if "@" not in em:
        raise RuntimeError("A valid email is required.")

    redirect_to = _invite_redirect_url()
    profile = _profile_for_email(em)

    try:
        if profile and str(profile.get("id") or "").strip():
            _send_password_setup_email(em, redirect_to=redirect_to)
            try:
                update_profile_admin(str(profile["id"]), {"must_reset_password": True})
            except Exception:
                pass
            return

        _admin_invite_user_by_email(em, redirect_to=redirect_to)
    except Exception as exc:
        raise RuntimeError(f"Could not resend invite for {em!r}: {exc!r}") from exc


def update_auth_user_email_admin(*, user_id: str, new_email: str) -> None:
    """
    Update the Supabase Auth user's email via Admin API (service role).

    Uses the admin client created with SUPABASE_SERVICE_ROLE_KEY (preferred).
    """
    uid = str(user_id or "").strip()
    em = str(new_email or "").strip().lower()
    if not uid:
        raise RuntimeError("Auth user id is required.")
    if not em or "@" not in em:
        raise RuntimeError("A valid email is required.")

    admin = get_admin_client()
    try:
        fn = getattr(admin.auth.admin, "update_user_by_id", None)
        if fn is None:
            raise AttributeError("auth.admin.update_user_by_id is not available in this Supabase client.")
        try:
            fn(uid, {"email": em})
        except TypeError:
            # Some versions accept a single dict payload.
            fn({"uid": uid, "attributes": {"email": em}})
    except Exception as exc:
        raise RuntimeError(f"Could not update auth email for user_id={uid!r}: {exc!r}") from exc


def update_profile_admin(profile_id: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        resp = get_admin_client().table("profiles").update(payload).eq("id", profile_id).execute()
        return resp.data or []
    except Exception as exc:
        raise RuntimeError(f"update_profile_admin failed: {exc}") from exc


def list_auth_users_admin(*, page: int = 1, per_page: int = 200) -> list[dict[str, Any]]:
    """
    Return Supabase Auth users (auth.users) via Admin API.

    Used for destructive actions where we must use the real `auth.users.id` (not profiles.id).
    """
    admin = get_admin_client()
    try:
        fn = getattr(admin.auth.admin, "list_users", None)
        if fn is None:
            raise AttributeError("auth.admin.list_users is not available in this Supabase client.")
        try:
            res = fn(page=page, per_page=per_page)
        except TypeError:
            # Some versions accept a single dict payload.
            res = fn({"page": page, "per_page": per_page})
    except Exception as exc:
        raise RuntimeError(f"Could not list auth users: {exc!r}") from exc

    users = getattr(res, "users", None)
    if users is None and isinstance(res, dict):
        users = res.get("users")
    if users is None:
        return []
    out: list[dict[str, Any]] = []
    for u in users or []:
        if isinstance(u, dict):
            out.append(u)
        else:
            out.append(
                {
                    "id": getattr(u, "id", None),
                    "email": getattr(u, "email", None),
                    "phone": getattr(u, "phone", None),
                    "created_at": getattr(u, "created_at", None),
                }
            )
    return out


def delete_auth_user_admin(*, user_id: str) -> None:
    """Delete a user from Supabase Auth (auth.users) via Admin API."""
    uid = str(user_id or "").strip()
    if not uid:
        raise RuntimeError("Auth user id is required.")
    admin = get_admin_client()
    fn = getattr(admin.auth.admin, "delete_user", None)
    if fn is None:
        raise RuntimeError("auth.admin.delete_user is not available in this Supabase client.")
    try:
        fn(uid)
    except TypeError:
        fn({"uid": uid})
