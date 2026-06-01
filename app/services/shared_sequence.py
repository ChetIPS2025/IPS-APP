"""
Yearly resetting integer sequence for Quote (QYYNNN) and Job (JYYNNN) numbers.

**Allocation** is database-backed: :func:`get_next_sequence_number` calls the Supabase RPC
``public.ips_next_yearly_seq()`` via the admin client (atomic increment per year, safe for concurrent
users).

Apply the Supabase SQL that defines ``public.ips_next_yearly_seq()`` before relying on new numbers.

**Parsing** (for display / imports only) supports stored forms:
  - ``QYYNNN`` (current), ``JYYNNN`` (current)
  - legacy formats from earlier versions (no year / different digit counts)
  - ``JOB-{digits}`` (legacy job numbers)
"""

from __future__ import annotations

from datetime import datetime, timezone
import math
import re
from decimal import Decimal
from typing import Any

# Quote/job format (current):
# - Q + YY + seq padded to 3 digits
# - J + YY + seq padded to 3 digits
_RE_QYYN = re.compile(r"^Q(\d{2})(\d{3})$", re.IGNORECASE)
_RE_JYYN = re.compile(r"^J(\d{2})(\d{3})$", re.IGNORECASE)

# Legacy quote formats:
# - Q + YY + 5-digit sequence
# - Q + 5-digit sequence (no year)
_RE_QYY5_LEGACY = re.compile(r"^Q(\d{2})(\d{5})$", re.IGNORECASE)
_RE_Q5_LEGACY = re.compile(r"^Q(\d{5})$", re.IGNORECASE)

# Legacy job formats:
# - J + 5-digit sequence (no year)
_RE_J5_LEGACY = re.compile(r"^J(\d{5})$", re.IGNORECASE)
_RE_JOB_LEGACY = re.compile(r"^JOB-(\d+)$", re.IGNORECASE)

# New unified yearly RPC
_RPC_NAME = "ips_next_yearly_seq"

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

    # Current formats (already encoded as 3-digit sequences).
    m = _RE_QYYN.match(s)
    if m:
        return int(m.group(2))
    m = _RE_JYYN.match(s)
    if m:
        return int(m.group(2))

    # Legacy formats: best-effort, recover a trailing integer if possible.
    m = _RE_QYY5_LEGACY.match(s)
    if m:
        return int(m.group(2))
    m = _RE_Q5_LEGACY.match(s)
    if m:
        return int(m.group(1))
    m = _RE_J5_LEGACY.match(s)
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
    """Next integer in the yearly sequence (atomic increment in Postgres)."""
    try:
        from app.db import get_admin_client
    except ImportError:
        from db import get_admin_client  # type: ignore

    last_exc: Exception | None = None
    for rpc_name in (_RPC_NAME, "ips_next_job_quote_seq"):
        try:
            resp = get_admin_client().rpc(rpc_name, {}).execute()
            return _coerce_sequence_rpc_payload(resp.data)
        except Exception as exc:
            last_exc = exc
            continue

    raise RuntimeError(
        "Could not allocate the next quote/job sequence number from the database. "
        "Confirm SUPABASE_URL and the service-role key are set, that "
        f"the SQL that defines RPC {_RPC_NAME!r} (or legacy ips_next_job_quote_seq) "
        "has been applied, and that the RPC exists. "
        f"Request error: {last_exc!r}"
    ) from last_exc


def format_quote_number(n: int) -> str:
    yy = datetime.now(timezone.utc).strftime("%y")
    seq = int(n)
    if not (0 <= seq <= 999):
        raise ValueError(f"Quote sequence out of range (expected 0..999): {seq}")
    return f"Q{yy}{seq:03d}"


def format_job_number(n: int) -> str:
    yy = datetime.now(timezone.utc).strftime("%y")
    seq = int(n)
    if not (0 <= seq <= 999):
        raise ValueError(f"Job sequence out of range (expected 0..999): {seq}")
    return f"J{yy}{seq:03d}"


def next_quote_number_string() -> str:
    """Allocate the next quote number string (``Q`` + UTC year + 3-digit sequence)."""
    return format_quote_number(get_next_sequence_number())


def next_job_number_string() -> str:
    """Allocate the next job number string (``J`` + UTC year + 3-digit sequence)."""
    return format_job_number(get_next_sequence_number())


def quote_number_to_job_number(quote_number: str) -> str:
    """
    Map a quote/estimate number to its linked job number without consuming a new sequence slot.

    ``Q26208`` → ``J26208`` (same ``YY###`` tail). Used when creating a job from an estimate.
    """
    q = str(quote_number or "").strip()
    if not q:
        return ""
    first = q[:1].upper()
    if first == "Q":
        return f"J{q[1:]}"[:120]
    if first == "J":
        return q[:120]
    return f"J{q}"[:120]


def job_number_to_quote_number(job_number: str) -> str:
    """Inverse of :func:`quote_number_to_job_number` (``J26208`` → ``Q26208``)."""
    j = str(job_number or "").strip()
    if not j:
        return ""
    first = j[:1].upper()
    if first == "J":
        return f"Q{j[1:]}"[:120]
    if first == "Q":
        return j[:120]
    return f"Q{j}"[:120]


# Backward-compatible alias used across estimate/job workflow modules.
estimate_quote_to_job_number = quote_number_to_job_number
