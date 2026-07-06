"""Whole-number parsing, validation, and display for inventory quantities."""

from __future__ import annotations

import math
import re
from decimal import Decimal, InvalidOperation
from typing import Any

_WHOLE_NUMBER_ERR = "Quantity must be a whole number."
_NEGATIVE_ERR = "Quantity cannot be negative."
_ZERO_ERR = "Quantity must be greater than zero."


def _decimal_has_fraction(value: Decimal) -> bool:
    return value != value.to_integral_value()


def parse_inventory_quantity(
    value: Any,
    *,
    allow_negative: bool = False,
    allow_zero: bool = True,
    field_name: str = "Quantity",
) -> int:
    """Parse and validate a whole-number inventory quantity."""
    if value is None or value == "":
        if allow_zero:
            return 0
        raise ValueError(f"{field_name} is required.")

    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a whole number.")

    if isinstance(value, int):
        qty = value
    elif isinstance(value, float):
        if not math.isfinite(value) or _has_non_zero_fraction(value):
            raise ValueError(f"{field_name} must be a whole number.")
        qty = int(round(value))
    else:
        raw = str(value).strip().replace(",", "")
        if not raw:
            if allow_zero:
                return 0
            raise ValueError(f"{field_name} is required.")
        if re.fullmatch(r"-?\d+\.\d+", raw):
            try:
                dec = Decimal(raw)
            except InvalidOperation as exc:
                raise ValueError(f"{field_name} must be a whole number.") from exc
            if _decimal_has_fraction(dec):
                raise ValueError(f"{field_name} must be a whole number.")
            qty = int(dec)
        elif re.fullmatch(r"-?\d+", raw):
            qty = int(raw)
        else:
            try:
                num = float(raw)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{field_name} must be a whole number.") from exc
            if _has_non_zero_fraction(num):
                raise ValueError(f"{field_name} must be a whole number.")
            qty = int(round(num))

    if not allow_negative and qty < 0:
        raise ValueError(f"{field_name} cannot be negative.")
    if not allow_zero and qty <= 0:
        raise ValueError(f"{field_name} must be greater than zero.")
    return qty


def try_parse_inventory_quantity(
    value: Any,
    *,
    allow_negative: bool = False,
    allow_zero: bool = True,
    field_name: str = "Quantity",
) -> tuple[int | None, str | None]:
    try:
        return parse_inventory_quantity(
            value,
            allow_negative=allow_negative,
            allow_zero=allow_zero,
            field_name=field_name,
        ), None
    except ValueError as exc:
        return None, str(exc)


def read_inventory_quantity(row: dict[str, Any] | None, *keys: str) -> int:
    """Read the first present quantity key from a row as a whole number."""
    if not row:
        return 0
    for key in keys:
        if key in row and row.get(key) is not None and str(row.get(key)).strip() != "":
            try:
                return parse_inventory_quantity(row.get(key), allow_negative=True, allow_zero=True)
            except ValueError:
                return int(round(float(row.get(key) or 0)))
    return 0


def format_inventory_quantity(value: Any, unit: str = "") -> str:
    """Display inventory quantity as a whole number (no decimals)."""
    if value is None or str(value).strip() == "":
        return "—"
    try:
        qty = parse_inventory_quantity(value, allow_negative=True, allow_zero=True)
    except ValueError:
        return "—"
    body = f"{qty:,}"
    unit_text = str(unit or "").strip()
    return f"{body} {unit_text}".strip() if unit_text else body


def inventory_qty_input_kwargs(*, min_value: int = 0, value: int | float = 0) -> dict[str, Any]:
    """Streamlit number_input kwargs for whole-number inventory quantities."""
    safe_min = int(min_value)
    safe_value = max(safe_min, int(round(float(value or 0))))
    return {
        "min_value": safe_min,
        "step": 1,
        "format": "%d",
        "value": safe_value,
    }


def _has_non_zero_fraction(value: float) -> bool:
    return abs(value - round(value)) > 1e-9
