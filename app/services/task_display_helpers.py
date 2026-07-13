"""Display normalization helpers for the Tasks inline editor."""

from __future__ import annotations

from app.services.status_maps import (
    normalize_task_status,
    normalize_task_status_label,
    task_priority_to_db,
    task_status_filter_bucket,
    task_status_to_db,
)
__all__ = [
    "display_to_priority",
    "display_to_status",
    "normalize_task_priority",
    "normalize_task_status",
    "priority_to_db",
    "priority_to_display",
    "status_to_db",
    "status_to_display",
]


def _strip_emoji(value: object) -> str:
    import re

    _EMOJI_PREFIX = re.compile(
        r"^[\U0001F300-\U0001FAFF\U00002600-\U000027BF\u2705\u2B50\uFE0F?\s]+"
    )
    raw = str(value or "").strip()
    cleaned = _EMOJI_PREFIX.sub("", raw).strip()
    return cleaned or raw


def normalize_task_priority(value: object) -> str:
    cleaned = _strip_emoji(value)
    if not cleaned:
        return "Medium"
    key = cleaned.lower()
    if key in {"high", "urgent"}:
        return "High"
    if key == "low":
        return "Low"
    return "Medium"


def status_to_display(value: object) -> str:
    return "✅ Closed" if task_status_filter_bucket(value) == "Closed" else "🔵 Open"


def priority_to_display(value: object) -> str:
    pri = normalize_task_priority(value)
    return {
        "High": "🔴 High",
        "Medium": "🟠 Medium",
        "Low": "🟢 Low",
    }[pri]


def display_to_status(value: object) -> str:
    return normalize_task_status_label(_strip_emoji(value))


def display_to_priority(value: object) -> str:
    return normalize_task_priority(_strip_emoji(value))


def priority_to_db(value: object) -> str:
    return task_priority_to_db(normalize_task_priority(value))


def status_to_db(value: object) -> str:
    return task_status_to_db(value)
