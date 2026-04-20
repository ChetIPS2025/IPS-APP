from __future__ import annotations

from collections.abc import Callable

from app.confirm_delete import render_destructive_confirmation


def render_delete_confirm(
    *,
    key_prefix: str,
    title: str,
    message: str,
    name_lines: list[str],
    on_confirm: Callable[[], None],
    on_cancel: Callable[[], None],
) -> None:
    render_destructive_confirmation(
        key_prefix=key_prefix,
        title=title,
        message=message,
        confirm_label="Confirm Delete",
        cancel_label="Cancel",
        on_confirm=on_confirm,
        on_cancel=on_cancel,
        name_lines=name_lines,
    )
