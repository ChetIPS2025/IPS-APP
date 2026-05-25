"""Reusable column header filters for custom IPS tables."""

from __future__ import annotations

import html
from collections.abc import Callable
from typing import Any

import streamlit as st

_FILTER_CSS_SESSION_KEY = "ips_table_header_filter_css_v6"


def inject_table_header_filter_css_once() -> None:
    if st.session_state.get(_FILTER_CSS_SESSION_KEY):
        return
    try:
        from app.styles import inject_table_header_filter_css
    except ImportError:
        from styles import inject_table_header_filter_css  # type: ignore
    inject_table_header_filter_css()
    st.session_state[_FILTER_CSS_SESSION_KEY] = True


def filter_session_key(table_key: str, field: str) -> str:
    return f"{table_key}_{field}_filter"


def get_column_filter_values(table_key: str, field: str) -> list[str]:
    raw = st.session_state.get(filter_session_key(table_key, field))
    if not raw:
        return []
    if isinstance(raw, str):
        return [raw] if raw.strip() else []
    return [str(v) for v in raw if str(v).strip()]


def clear_table_filters(
    table_key: str,
    filter_fields: list[str],
    *,
    extra_keys: list[str] | None = None,
) -> None:
    for field in filter_fields:
        st.session_state.pop(filter_session_key(table_key, field), None)
    for key in extra_keys or []:
        st.session_state.pop(key, None)


def get_unique_filter_options(
    records: list[dict[str, Any]],
    field: str,
    *,
    formatter: Callable[[dict[str, Any]], str] | None = None,
) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for row in records:
        if formatter:
            val = str(formatter(row) or "").strip() or "—"
        else:
            val = str(row.get(field) or "").strip() or "—"
        if val not in seen:
            seen.add(val)
            out.append(val)
    return sorted(out, key=lambda s: (s == "—", s.lower()))


def build_filter_options(
    records: list[dict[str, Any]],
    specs: list[tuple[str, Callable[[dict[str, Any]], str] | None]],
) -> dict[str, list[str]]:
    return {
        field: get_unique_filter_options(records, field, formatter=formatter)
        for field, formatter in specs
    }


def apply_column_filters(
    records: list[dict[str, Any]],
    table_key: str,
    specs: list[tuple[str, Callable[[dict[str, Any]], str] | None]],
) -> list[dict[str, Any]]:
    out = list(records)
    for field, formatter in specs:
        selected = get_column_filter_values(table_key, field)
        if not selected:
            continue
        selected_set = set(selected)
        filtered: list[dict[str, Any]] = []
        for row in out:
            if formatter:
                val = str(formatter(row) or "").strip() or "—"
            else:
                val = str(row.get(field) or "").strip() or "—"
            if val in selected_set:
                filtered.append(row)
        out = filtered
    return out


def render_header_filter(
    table_key: str,
    label: str,
    field: str,
    options: list[str],
    *,
    wrap_class: str = "ips-table-header-filter-wrap",
    header_class: str = "",
) -> None:
    inject_table_header_filter_css_once()
    session_key = filter_session_key(table_key, field)
    active = get_column_filter_values(table_key, field)
    option_set = set(options)
    for val in active:
        option_set.add(val)
    merged = sorted(option_set, key=lambda s: (s == "—", s.lower()))

    active_class = " ips-table-header-filter-active" if active else ""

    label_html = html.escape(label)
    if active:
        label_html += ' <span class="ips-filter-dot" aria-hidden="true"></span>'

    st.markdown(
        f'<span class="ips-table-header-filter-marker{active_class}" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    label_col, arrow_col = st.columns([0.92, 0.08], gap="small", vertical_alignment="center")
    with label_col:
        st.markdown(
            f'<span class="ips-table-header-filter-text{active_class}">{label_html}</span>',
            unsafe_allow_html=True,
        )
    with arrow_col:
        with st.popover("▾", help=f"Filter {label}", type="tertiary"):
            st.multiselect(
                f"Filter {label}",
                options=merged,
                key=session_key,
                label_visibility="collapsed",
            )
            if st.button("Clear filter", key=f"clear_{table_key}_{field}_filter"):
                st.session_state[session_key] = []
                st.rerun()


def render_table_header_cell(
    label: str,
    *,
    table_key: str | None = None,
    filter_field: str | None = None,
    filter_options: list[str] | None = None,
    base_class: str = "ips-timekeeping-header-row ips-timekeeping-cell",
) -> None:
    if table_key and filter_field and filter_options is not None:
        render_header_filter(
            table_key,
            label,
            filter_field,
            filter_options,
            header_class=base_class,
        )
    else:
        st.markdown(
            f'<div class="{base_class}">{html.escape(label)}</div>',
            unsafe_allow_html=True,
        )
