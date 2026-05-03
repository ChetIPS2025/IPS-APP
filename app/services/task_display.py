"""Single-field task number for display (legacy ``hazard_number`` merged away in DB)."""

from __future__ import annotations

from typing import Any


def task_number_display(row: dict[str, Any] | None) -> str:
    """Primary label: ``task_number``, falling back to legacy ``hazard_number`` if still present."""
    if not row:
        return "—"
    tn = str(row.get("task_number") or "").strip()
    if tn:
        return tn
    legacy = str(row.get("hazard_number") or "").strip()
    return legacy or "—"
