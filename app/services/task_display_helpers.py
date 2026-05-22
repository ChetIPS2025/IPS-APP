"""Display normalization helpers for the Tasks inline editor."""

from __future__ import annotations

import re

_EMOJI_PREFIX = re.compile(
    r"^[\U0001F300-\U0001FAFF\U00002600-\U000027BF\u2705\u2B50\uFE0F?\s]+"
)

_CLOSED_ALIASES = frozenset({"done", "complete", "completed", "closed"})


def _strip_emoji(value: object) -> str:
    raw = str(value or "").strip()
    cleaned = _EMOJI_PREFIX.sub("", raw).strip()
    return cleaned or raw


def normalize_task_status(value: object) -> str:
    cleaned = _strip_emoji(value)
    if not cleaned:
        return "Open"
    if cleaned.lower() in _CLOSED_ALIASES:
        return "Closed"
    return "Open"


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
    return "✅ Closed" if normalize_task_status(value) == "Closed" else "🔵 Open"


def priority_to_display(value: object) -> str:
    pri = normalize_task_priority(value)
    return {
        "High": "🔴 High",
        "Medium": "🟠 Medium",
        "Low": "🟢 Low",
    }[pri]


def display_to_status(value: object) -> str:
    return normalize_task_status(_strip_emoji(value))


def display_to_priority(value: object) -> str:
    return normalize_task_priority(_strip_emoji(value))


def status_to_db(value: object) -> str:
    return "Complete" if normalize_task_status(value) == "Closed" else "Open"


def priority_to_db(value: object) -> str:
    pri = normalize_task_priority(value)
    return "Normal" if pri == "Medium" else pri
