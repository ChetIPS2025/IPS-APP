"""Form validation helpers."""

from __future__ import annotations


def require_fields(data: dict, fields: list[str]) -> list[str]:
    missing = []
    for f in fields:
        if not str(data.get(f) or "").strip():
            missing.append(f)
    return missing


def validate_email(email: str) -> bool:
    e = str(email or "").strip()
    return "@" in e and "." in e.split("@")[-1]
