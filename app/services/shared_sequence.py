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

from datetime import date, datetime, timezone
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


def year_yy(value: int | date | datetime | None = None) -> str:
    """Two-digit calendar year for numbering (2026 → ``26``)."""
    if value is None:
        return datetime.now(timezone.utc).strftime("%y")
    if isinstance(value, datetime):
        return f"{value.year % 100:02d}"
    if isinstance(value, date):
        return f"{value.year % 100:02d}"
    year = int(value)
    if year >= 100:
        year = year % 100
    return f"{year:02d}"


def format_number(prefix: str, year: int | date | datetime, seq: int) -> str:
    """Format ``QYY###`` or ``JYY###``."""
    p = str(prefix or "").strip().upper()
    if p not in ("Q", "J"):
        raise ValueError("prefix must be 'Q' or 'J'")
    yy = year_yy(year)
    slot = int(seq)
    if not (0 <= slot <= 999):
        raise ValueError(f"Sequence out of range (expected 0..999): {slot}")
    return f"{p}{yy}{slot:03d}"


def parse_number_parts(value: str | None) -> tuple[str, str, int] | None:
    """Return ``(prefix, yy, seq)`` for current-format numbers, else None."""
    s = str(value or "").strip().upper()
    if not s:
        return None
    m = _RE_QYYN.match(s) or _RE_JYYN.match(s)
    if not m:
        return None
    prefix = s[0]
    return prefix, m.group(1), int(m.group(2))


def _strict_quote_job_number(value: str | None) -> str | None:
    """Return normalized ``QYY###`` / ``JYY###`` when ``value`` matches the current format."""
    parts = parse_number_parts(value)
    if not parts:
        return None
    prefix, yy, seq = parts
    return format_number(prefix, date(2000 + int(yy), 1, 1), seq)


def _job_row_is_deleted(row: dict[str, Any]) -> bool:
    if not row:
        return False
    if row.get("is_deleted") is True:
        return True
    if str(row.get("deleted_at") or "").strip():
        return True
    return False


def _values_for_shared_max(values: list[str]) -> list[str]:
    """
    Quote numbers always count toward the shared max.

    Job numbers count only when a saved estimate already has the paired
    ``QYY###`` (same YY + sequence). Orphan ``J`` rows without a matching
    quote — including preview-only linked numbers — are ignored.
    """
    quotes: list[str] = []
    jobs: list[str] = []
    for raw in values:
        normalized = _strict_quote_job_number(raw)
        if not normalized:
            continue
        if normalized[0] == "Q":
            quotes.append(normalized)
        else:
            jobs.append(normalized)
    quote_set = {q.upper() for q in quotes}
    out = list(quotes)
    for job_no in jobs:
        paired_q = job_number_to_quote_number(job_no).upper()
        if paired_q in quote_set:
            out.append(job_no)
    return out


def _collect_stored_quote_job_numbers() -> list[str]:
    """Load ``QYY###`` / paired ``JYY###`` from estimates and jobs tables only."""
    quotes: list[str] = []
    jobs: list[dict[str, Any]] = []
    try:
        from app.db import fetch_table_admin
    except ImportError:
        from db import fetch_table_admin  # type: ignore
    try:
        for row in fetch_table_admin("estimates", columns="quote_number", limit=10000) or []:
            normalized = _strict_quote_job_number(str(row.get("quote_number") or ""))
            if normalized:
                quotes.append(normalized)
    except Exception:
        pass
    job_columns = "job_number,estimate_id,is_deleted,deleted_at"
    try:
        job_rows = fetch_table_admin("jobs", columns=job_columns, limit=10000) or []
    except Exception:
        try:
            job_rows = fetch_table_admin("jobs", columns="job_number,estimate_id", limit=10000) or []
        except Exception:
            job_rows = []
    for row in job_rows or []:
        if _job_row_is_deleted(row):
            continue
        normalized = _strict_quote_job_number(str(row.get("job_number") or ""))
        if normalized:
            jobs.append({"job_number": normalized, "estimate_id": row.get("estimate_id")})
    quote_set = {q.upper() for q in quotes}
    values = list(quotes)
    for row in jobs:
        job_no = str(row.get("job_number") or "")
        paired_q = job_number_to_quote_number(job_no).upper()
        if paired_q in quote_set:
            values.append(job_no)
    return values


def max_sequence_for_year(year: int | date | datetime, *, existing_values: list[str] | None = None) -> int:
    """Highest 3-digit sequence slot used for ``year`` across quotes and paired jobs."""
    yy = year_yy(year)
    raw_values = (
        existing_values if existing_values is not None else _collect_stored_quote_job_numbers()
    )
    max_seq = 0
    for raw in _values_for_shared_max(raw_values):
        parts = parse_number_parts(raw)
        if parts and parts[1] == yy:
            max_seq = max(max_seq, parts[2])
    return max_seq


def peek_next_sequence_number(year: int | date | datetime) -> int:
    """Next sequence slot for ``year`` without allocating (reads existing rows only)."""
    return max_sequence_for_year(year) + 1


def get_next_sequence_number_for_year(year: int | date | datetime | None = None) -> int:
    """
    Return the next shared sequence slot for ``year`` from saved quote/job rows.

    Does not use the ``ips_yearly_sequence`` RPC counter (which can run ahead of
    real ``estimates.quote_number`` / ``jobs.job_number`` values).
    """
    y = year if year is not None else datetime.now(timezone.utc)
    return peek_next_sequence_number(y)


def get_next_sequence_number() -> int:
    """Next integer in the yearly sequence for the current UTC year."""
    return get_next_sequence_number_for_year(None)


def format_quote_number(n: int, *, year: int | date | datetime | None = None) -> str:
    return format_number("Q", year if year is not None else datetime.now(timezone.utc), n)


def format_job_number(n: int, *, year: int | date | datetime | None = None) -> str:
    return format_number("J", year if year is not None else datetime.now(timezone.utc), n)


def next_available_job_number(
    year: int | date | datetime | None = None,
    *,
    exclude_job_id: str | None = None,
) -> str:
    """Next free ``JYY###`` for ``year`` (paired quotes + in-use check)."""
    try:
        from app.db import job_number_in_use
    except ImportError:
        from db import job_number_in_use  # type: ignore

    y = year if year is not None else datetime.now(timezone.utc)
    start = max_sequence_for_year(y) + 1
    for seq in range(start, 1000):
        candidate = format_number("J", y, seq)
        if not job_number_in_use(candidate, exclude_job_id):
            return candidate
    yy = year_yy(y)
    raise ValueError(f"No available job number for year {yy} (sequence exhausted).")


def generate_quote_job_number(prefix: str, year: int | date | datetime) -> str:
    """
    Return the next shared ``QYY###`` or ``JYY###`` for ``year`` from saved rows.

    Linked jobs should use :func:`quote_number_to_job_number` instead of calling
    this again for the same sequence slot.
    """
    p = str(prefix or "").strip().upper()
    if p not in ("Q", "J"):
        raise ValueError("prefix must be 'Q' or 'J'")
    if p == "Q":
        return next_available_quote_number(year)
    return next_available_job_number(year)


def peek_quote_job_number(prefix: str, year: int | date | datetime) -> str:
    """Preview the next number without consuming a sequence slot."""
    p = str(prefix or "").strip().upper()
    if p not in ("Q", "J"):
        raise ValueError("prefix must be 'Q' or 'J'")
    return format_number(p, year, peek_next_sequence_number(year))


def _quote_number_in_use(quote_number: str, *, exclude_estimate_id: str | None = None) -> bool:
    try:
        from app.db import quote_number_in_use
    except ImportError:
        from db import quote_number_in_use  # type: ignore
    return quote_number_in_use(quote_number, exclude_estimate_id)


def next_available_quote_number(
    year: int | date | datetime | None = None,
    *,
    exclude_estimate_id: str | None = None,
) -> str:
    """
    Next free ``QYY###`` for ``year`` using max sequence across estimates and jobs.

    Does not call the yearly RPC; safe to use when a prefilled number is already taken.
    """
    y = year if year is not None else datetime.now(timezone.utc)
    start = max_sequence_for_year(y) + 1
    for seq in range(start, 1000):
        candidate = format_number("Q", y, seq)
        if not _quote_number_in_use(candidate, exclude_estimate_id=exclude_estimate_id):
            return candidate
    yy = year_yy(y)
    raise ValueError(f"No available quote number for year {yy} (sequence exhausted).")


def next_available_quote_job_pair(
    year: int | date | datetime | None = None,
    *,
    exclude_estimate_id: str | None = None,
    exclude_job_id: str | None = None,
) -> tuple[str, str]:
    """
    Next free ``(QYY###, JYY###)`` pair for ``year`` with the same sequence slot.

    Checks both ``estimates.quote_number`` and ``jobs.job_number`` (exact match).
    """
    try:
        from app.db import job_number_in_use, quote_number_in_use
    except ImportError:
        from db import job_number_in_use, quote_number_in_use  # type: ignore

    y = year if year is not None else datetime.now(timezone.utc)
    start = max_sequence_for_year(y) + 1
    for seq in range(start, 1000):
        candidate_q = format_number("Q", y, seq)
        candidate_j = format_number("J", y, seq)
        if quote_number_in_use(candidate_q, exclude_estimate_id) or job_number_in_use(
            candidate_j, exclude_job_id
        ):
            continue
        return candidate_q, candidate_j
    yy = year_yy(y)
    raise ValueError(f"No available quote/job number pair for year {yy} (sequence exhausted).")


def ensure_quote_number_for_save(
    quote_number: str,
    *,
    year: int | date | datetime | None = None,
    exclude_estimate_id: str | None = None,
) -> str:
    """
    Return a quote number safe to insert/update on ``estimates``.

    Keeps the requested value when it is unused; otherwise allocates the next
    available shared ``QYY###`` from both estimates and jobs.
    """
    y = year if year is not None else datetime.now(timezone.utc)
    qn = str(quote_number or "").strip()
    if not qn:
        return next_available_quote_number(y, exclude_estimate_id=exclude_estimate_id)
    if not _quote_number_in_use(qn, exclude_estimate_id=exclude_estimate_id):
        return qn
    return next_available_quote_number(y, exclude_estimate_id=exclude_estimate_id)


def next_quote_number_string(*, year: int | date | datetime | None = None) -> str:
    """Next quote number string (``QYY###``) from saved estimates and jobs."""
    y = year if year is not None else datetime.now(timezone.utc)
    return next_available_quote_number(y)


def next_job_number_string(*, year: int | date | datetime | None = None) -> str:
    """Next job number string (``JYY###``) from saved estimates and jobs."""
    y = year if year is not None else datetime.now(timezone.utc)
    return next_available_job_number(y)


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
