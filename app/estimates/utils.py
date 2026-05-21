"""Shared display formatters and small helpers for the Estimating module."""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

import pandas as pd

# Column names that contain money values (formatted with $ prefix + commas).
MONEY_LIST_COLUMNS: frozenset[str] = frozenset({"proposal_total", "final_bid"})


# ---------------------------------------------------------------------------
# Decimal helpers (distinguish missing vs zero — do not use ``or`` for fallbacks)
# ---------------------------------------------------------------------------

def estimate_decimal_optional(val: Any) -> Decimal | None:
    """Parse money; return ``None`` when the value is missing (not when it is zero)."""
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except Exception:
        pass
    s = str(val).replace(",", "").strip()
    if not s:
        return None
    try:
        return Decimal(s).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        return None


def estimate_decimal(val: Any) -> Decimal:
    """Parse money for arithmetic; missing values become ``Decimal('0')``."""
    return estimate_decimal_optional(val) or Decimal("0")


def resolve_estimate_subtotal(
    row: Any,
    *,
    total: Decimal | None = None,
    tax: Decimal | None = None,
) -> Decimal:
    """
    Subtotal for display: use stored ``subtotal`` when present (including 0),
    otherwise ``max(0, total - tax)``.
    """
    if hasattr(row, "get"):
        stored = estimate_decimal_optional(row.get("subtotal"))
        if stored is not None:
            return stored
        if total is None:
            total = estimate_decimal_optional(row.get("proposal_total"))
            if total is None:
                total = estimate_decimal_optional(row.get("final_bid"))
            if total is None:
                total = estimate_decimal_optional(row.get("total"))
        if tax is None:
            tax = estimate_decimal_optional(row.get("sales_tax_total"))
            if tax is None:
                tax = estimate_decimal_optional(row.get("tax"))
    total = total if total is not None else Decimal("0")
    tax = tax if tax is not None else Decimal("0")
    return max(Decimal("0"), total - tax)


# Back-compat alias for older estimates page code.
_estimate_decimal = estimate_decimal


# ---------------------------------------------------------------------------
# Money formatters
# ---------------------------------------------------------------------------

def money_display(val: Any) -> str:
    """DB / saved numeric → $X,XXX.XX  (Decimal-safe, handles None / NaN)."""
    if val is None:
        return ""
    try:
        if pd.isna(val):
            return ""
    except Exception:
        pass
    try:
        d = Decimal(str(val).replace(",", "").strip()).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        return f"${d:,.2f}"
    except Exception:
        s = str(val).strip()
        return s[:72] + ("…" if len(s) > 72 else "")


def money_csv(val: Any) -> str:
    """Same precision as money_display but no $ — suitable for CSV export."""
    if val is None:
        return ""
    try:
        if pd.isna(val):
            return ""
    except Exception:
        pass
    try:
        d = Decimal(str(val).replace(",", "").strip()).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        return f"{d:.2f}"
    except Exception:
        return str(val).strip()


# ---------------------------------------------------------------------------
# Cell text helpers
# ---------------------------------------------------------------------------

def list_cell_text(val: Any, col: str | None = None) -> str:
    """Format a DataFrame cell value for the estimates list table."""
    if col and col in MONEY_LIST_COLUMNS:
        return money_display(val)
    if val is None:
        return ""
    try:
        if pd.isna(val):
            return ""
    except Exception:
        pass
    s = str(val).strip()
    return (s[:69] + "…") if len(s) > 72 else s


# ---------------------------------------------------------------------------
# Description helpers
# ---------------------------------------------------------------------------

def estimate_description_display(est_row: Any) -> str:
    """Short description text shown in the Estimates list.

    Priority order:
    1. Denormalised ``estimate_description`` column
    2. ``estimate_json['estimate_description']``
    3. ``estimate_json['job']`` / ``['job_name']``
    4. First line of ``scope_of_work`` (last resort — can be very long)
    """
    def _get(key: str) -> Any:
        if hasattr(est_row, "get"):
            return est_row.get(key)
        return None

    desc = _get("estimate_description")
    if desc is None or (isinstance(desc, float) and pd.isna(desc)):
        desc = ""

    if not str(desc).strip():
        ej = _get("estimate_json")
        if isinstance(ej, dict):
            desc = ej.get("estimate_description") or ""

    if not str(desc).strip():
        ej = _get("estimate_json")
        if isinstance(ej, dict):
            desc = ej.get("job") or ej.get("job_name") or ""

    if not str(desc).strip():
        desc = _get("scope_of_work") or ""

    s = str(desc or "").strip()
    if not s:
        return ""
    s = s.splitlines()[0].strip()
    return s[:60] + ("…" if len(s) > 60 else "")


# ---------------------------------------------------------------------------
# Boolean helpers
# ---------------------------------------------------------------------------

def truthy_job_received(row: Any) -> bool:
    """Safely extract job_received boolean from a DataFrame row or dict."""
    if hasattr(row, "get"):
        v = row.get("job_received")
    else:
        try:
            v = row["job_received"]
        except (KeyError, TypeError):
            return False
    if v is None:
        return False
    try:
        if pd.isna(v):
            return False
    except Exception:
        pass
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        try:
            return float(v) != 0.0
        except (TypeError, ValueError):
            return False
    return str(v).strip().lower() in ("true", "1", "yes", "t")


def row_estimate_id(row: Any) -> str:
    """Extract the primary-key string from a DataFrame row dict."""
    if not hasattr(row, "get"):
        return ""
    raw = row.get("id")
    if raw is None:
        return ""
    try:
        if pd.isna(raw):
            return ""
    except Exception:
        pass
    return str(raw).strip()
