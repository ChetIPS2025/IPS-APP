"""
Shared integer sequence for Quote (Q#####) and Job (J#####) numbers.

**Allocation** is database-backed: :func:`get_next_sequence_number` calls the Supabase RPC
``public.ips_next_job_quote_seq()`` via the admin client (atomic ``UPDATE`` on
``public.ips_shared_sequence``, safe for concurrent users).

Apply ``sql/012_ips_shared_sequence.sql`` in Supabase before relying on new numbers.

**Parsing** (for display / imports only) supports stored forms:
  - ``Q#####``, ``J#####``
  - ``JOB-{digits}`` (legacy job numbers)
"""

from __future__ import annotations

import math
import re
from decimal import Decimal
from typing import Any

# New unified: Q/J + exactly 5 digits
_RE_Q5 = re.compile(r"^Q(\d{5})$", re.IGNORECASE)
_RE_J5 = re.compile(r"^J(\d{5})$", re.IGNORECASE)
_RE_JOB_LEGACY = re.compile(r"^JOB-(\d+)$", re.IGNORECASE)

_RPC_NAME = "ips_next_job_quote_seq"

# PostgREST / wrappers may return the scalar under these keys (checked in order).
_DICT_KEYS: tuple[str, ...] = (
    _RPC_NAME,
    "value",
    "result",
    "data",
    "sequence_number",
    "seq",
    "n",
)


def parse_stored_sequence_value(value: str | None) -> int | None:
    """Return the integer sequence slot encoded in a stored quote or job number, or None."""
    s = (value or "").strip()
    if not s:
        return None
    m = _RE_J5.match(s)
    if m:
        return int(m.group(1))
    m = _RE_Q5.match(s)
    if m:
        return int(m.group(1))
    m = _RE_JOB_LEGACY.match(s)
    if m:
        return int(m.group(1))
    return None


def _coerce_sequence_rpc_payload(data: Any) -> int:
    """
    Normalize the Supabase Python client's ``rpc(...).data`` into a single integer.

    Handles common shapes: bare int, float with integer value, one-element list/tuple,
    string digits, and dicts (known keys or a single-entry dict).

    Raises:
        ValueError: payload cannot be interpreted as one integer (message is user-facing).
    """
    if data is None:
        raise ValueError(f"{_RPC_NAME} returned no data (empty response).")

    # bool subclasses int — reject before int branch
    if isinstance(data, bool):
        raise ValueError(f"{_RPC_NAME} returned an unexpected boolean: {data!r}.")

    if isinstance(data, int):
        return data

    if isinstance(data, Decimal):
        if data != data.to_integral_value():
            raise ValueError(f"{_RPC_NAME} returned a non-integer decimal: {data!r}.")
        return int(data)

    if isinstance(data, float):
        if not math.isfinite(data):
            raise ValueError(f"{_RPC_NAME} returned a non-finite float: {data!r}.")
        if not data.is_integer():
            raise ValueError(f"{_RPC_NAME} returned a non-integer float: {data!r}.")
        return int(data)

    if isinstance(data, str):
        s = data.strip()
        if s.lstrip("-").isdigit():
            return int(s)
        raise ValueError(f"{_RPC_NAME} returned a non-numeric string: {data!r}.")

    if isinstance(data, (list, tuple)):
        if len(data) == 0:
            raise ValueError(f"{_RPC_NAME} returned an empty list/tuple.")
        if len(data) == 1:
            return _coerce_sequence_rpc_payload(data[0])
        raise ValueError(
            f"{_RPC_NAME} returned a list/tuple with {len(data)} elements; "
            f"expected exactly one integer (or one wrapper value). Raw: {data!r}"
        )

    if isinstance(data, dict):
        for k in _DICT_KEYS:
            if k in data:
                return _coerce_sequence_rpc_payload(data[k])
        if len(data) == 1:
            return _coerce_sequence_rpc_payload(next(iter(data.values())))
        raise ValueError(
            f"{_RPC_NAME} returned a dict with no recognized keys "
            f"(tried {list(_DICT_KEYS)!r}). Raw: {data!r}"
        )

    # Last resort: some clients stringify numeric payloads (legacy parity with older coercion).
    s = str(data).strip()
    if s.lstrip("-").isdigit():
        return int(s)

    raise ValueError(
        f"{_RPC_NAME} returned an unsupported type {type(data).__name__!r}. Raw: {data!r}"
    )


def get_next_sequence_number() -> int:
    """Next integer in the shared sequence (atomic increment in Postgres)."""
    try:
        from app.db import get_admin_client
    except ImportError:
        from db import get_admin_client  # type: ignore

    try:
        resp = get_admin_client().rpc(_RPC_NAME, {}).execute()
    except Exception as exc:
        raise RuntimeError(
            "Could not allocate the next quote/job sequence number from the database. "
            "Confirm SUPABASE_URL and the service-role key are set, that "
            f"sql/012_ips_shared_sequence.sql has been applied, and that RPC {_RPC_NAME!r} exists. "
            f"Request error: {exc!r}"
        ) from exc

    try:
        return _coerce_sequence_rpc_payload(resp.data)
    except ValueError as exc:
        raise RuntimeError(
            f"Database RPC {_RPC_NAME!r} did not return a single usable integer. {exc}"
        ) from exc


def format_quote_number(n: int) -> str:
    return f"Q{n:05d}"


def format_job_number(n: int) -> str:
    return f"J{n:05d}"


def next_quote_number_string() -> str:
    """Allocate the next quote number string (``Q`` + five digits)."""
    return format_quote_number(get_next_sequence_number())


def next_job_number_string() -> str:
    """Allocate the next job number string (``J`` + five digits)."""
    return format_job_number(get_next_sequence_number())
