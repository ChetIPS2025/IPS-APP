"""Phone normalization and display helpers."""

from __future__ import annotations


def normalize_phone(phone: str) -> str:
    """Store-friendly phone: E.164 when possible, else digits only."""
    s = str(phone or "").strip()
    if not s:
        return ""
    keep = []
    for ch in s:
        if ch.isdigit() or ch == "+":
            keep.append(ch)
    out = "".join(keep)
    digits = "".join(c for c in out if c.isdigit())
    if out.startswith("+"):
        return "+" + digits
    if len(digits) == 10:
        return "+1" + digits
    if len(digits) == 11 and digits.startswith("1"):
        return "+" + digits
    return digits


def format_phone_display(phone: str) -> str:
    """Human-readable US display when possible."""
    norm = normalize_phone(phone)
    digits = "".join(c for c in norm if c.isdigit())
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) == 10:
        return f"({digits[0:3]}) {digits[3:6]}-{digits[6:10]}"
    return norm or str(phone or "").strip() or "—"


def is_valid_phone(phone: str) -> bool:
    norm = normalize_phone(phone)
    digits = "".join(c for c in norm if c.isdigit())
    return len(digits) >= 10
