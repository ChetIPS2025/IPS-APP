"""Display formatting helpers."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any


def safe_str(val: Any) -> str:
    if val is None:
        return ""
    return str(val).strip()


def fmt_currency(val: Any) -> str:
    if val is None or safe_str(val) == "":
        return "$0.00"
    try:
        d = Decimal(str(val))
        return f"${d:,.2f}"
    except Exception:
        return "$0.00"


def fmt_date(val: Any) -> str:
    if not val:
        return "—"
    if isinstance(val, date):
        return val.strftime("%b %d, %Y")
    s = safe_str(val)
    if not s:
        return "—"
    try:
        if "T" in s:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).strftime("%b %d, %Y")
        return date.fromisoformat(s[:10]).strftime("%b %d, %Y")
    except Exception:
        return s[:10] if len(s) >= 10 else s


def fmt_hours(val: Any) -> str:
    try:
        return f"{float(val):.1f}"
    except Exception:
        return "0.0"
