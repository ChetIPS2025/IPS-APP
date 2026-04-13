"""
Shared integer sequence for Quote (Q#####) and Job (J#####) numbers.

**Allocation** is database-backed: :func:`get_next_sequence_number` calls
:func:`db.allocate_next_shared_sequence_int`, which runs ``public.ips_next_job_quote_seq()`` — an
atomic ``UPDATE`` on ``public.ips_shared_sequence`` (row lock), safe for concurrent users.

Apply ``sql/012_ips_shared_sequence.sql`` in Supabase before relying on new numbers.

**Parsing** (for display / imports only) supports stored forms:
  - ``Q#####``, ``J#####``
  - ``JOB-{digits}`` (legacy job numbers)
"""

from __future__ import annotations

import re

# New unified: Q/J + exactly 5 digits
_RE_Q5 = re.compile(r"^Q(\d{5})$", re.IGNORECASE)
_RE_J5 = re.compile(r"^J(\d{5})$", re.IGNORECASE)
_RE_JOB_LEGACY = re.compile(r"^JOB-(\d+)$", re.IGNORECASE)


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


def get_next_sequence_number() -> int:
    """Next integer in the shared sequence (atomic increment in Postgres)."""
    try:
        from app.db import allocate_next_shared_sequence_int
    except ImportError:
        from db import allocate_next_shared_sequence_int  # type: ignore
    return allocate_next_shared_sequence_int()


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
