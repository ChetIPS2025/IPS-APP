"""Display formatting helpers — single source for dates, money, qty, and percent."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any


def safe_str(val: Any) -> str:
    if val is None:
        return ""
    return str(val).strip()


def _parse_datetime(val: Any) -> datetime | date | None:
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, date):
        return val
    s = safe_str(val)
    if not s:
        return None
    try:
        if "T" in s or " " in s:
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        return date.fromisoformat(s[:10])
    except Exception:
        return None


def fmt_date(val: Any) -> str:
    if not val:
        return "—"
    if isinstance(val, date) and not isinstance(val, datetime):
        return val.strftime("%b %d, %Y")
    parsed = _parse_datetime(val)
    if parsed is None:
        s = safe_str(val)
        return s[:10] if len(s) >= 10 else s or "—"
    if isinstance(parsed, datetime):
        return parsed.strftime("%b %d, %Y")
    return parsed.strftime("%b %d, %Y")


def fmt_datetime(
    val: Any,
    *,
    include_seconds: bool = False,
    compact: bool = False,
) -> str:
    """Format a timestamp for display.

    compact=True → ``2026-05-30 14:45`` (or with seconds).
    compact=False → ``May 30, 2026 2:45 PM``.
    """
    if not val:
        return "—"
    parsed = _parse_datetime(val)
    if parsed is None:
        s = safe_str(val)
        if not s:
            return "—"
        if compact:
            end = 19 if include_seconds else 16
            return s[:end].replace("T", " ")
        return s[:32]
    if isinstance(parsed, date) and not isinstance(parsed, datetime):
        if compact:
            return parsed.isoformat()
        return parsed.strftime("%b %d, %Y")
    if compact:
        fmt = "%Y-%m-%d %H:%M:%S" if include_seconds else "%Y-%m-%d %H:%M"
        return parsed.strftime(fmt)
    stamp = parsed.strftime("%b %d, %Y %I:%M %p")
    if include_seconds:
        stamp = parsed.strftime("%b %d, %Y %I:%M:%S %p")
    return stamp.lstrip("0").replace(" 0", " ")


def fmt_money(
    val: Any,
    *,
    empty: str = "$0.00",
    zero_as_empty: bool = False,
) -> str:
    if val is None or safe_str(val) == "":
        return empty
    try:
        d = Decimal(str(val))
    except Exception:
        return empty
    if d == 0 and zero_as_empty:
        return empty
    return f"${d:,.2f}"


fmt_currency = fmt_money


def fmt_qty(val: Any, unit: str = "", *, decimals: int | None = None) -> str:
    if val is None or safe_str(val) == "":
        return "—"
    try:
        q = float(val)
    except (TypeError, ValueError):
        return "—"
    u = safe_str(unit)
    if decimals is None:
        if q == int(q):
            body = f"{int(q):,}"
        else:
            body = f"{q:g}"
    else:
        body = f"{q:,.{decimals}f}".rstrip("0").rstrip(".")
    return f"{body} {u}".strip() if u else body


def fmt_percent(val: Any, *, decimals: int = 1) -> str:
    if val is None or safe_str(val) == "":
        return "—"
    try:
        return f"{float(val):.{decimals}f}%"
    except (TypeError, ValueError):
        return "—"


def fmt_hours(val: Any, *, empty_zero: bool = False) -> str:
    try:
        v = float(val)
    except (TypeError, ValueError):
        return "" if empty_zero else "0.0"
    if not v and empty_zero:
        return ""
    if empty_zero:
        r = round(v, 2)
        return f"{r:g}"
    return f"{v:.1f}"
