"""Chart helpers for coastal dashboard (matplotlib + Streamlit)."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st


def _mpl_available() -> bool:
    try:
        import matplotlib  # noqa: F401

        return True
    except ImportError:
        return False


def render_sales_line_chart(
  current: dict[str, float],
  previous: dict[str, float],
  *,
  key: str,
) -> None:
    if not current and not previous:
        try:
            from app.ui.components.empty_states import render_empty_state
        except ImportError:
            from ui.components.empty_states import render_empty_state  # type: ignore
        render_empty_state(
            "No sales data",
            "Sales will appear when estimates or paid expenses are recorded in this period.",
            icon="📈",
        )
        return

    months = sorted(set(list(current.keys()) + list(previous.keys())))
    if not months:
        months = ["—"]
    df = pd.DataFrame(
        {
            "This Period": [current.get(m, 0.0) for m in months],
            "Last Period": [previous.get(m, 0.0) for m in months],
        },
        index=months,
    )
    st.caption("This Period · Last Period")
    st.line_chart(df, use_container_width=True, color=["#2563eb", "#94a3b8"])


def _render_donut(
    breakdown: dict[str, float | int],
    *,
    center_label: str,
    center_value: str,
    key: str,
    colors: list[str] | None = None,
    money_legend: bool = True,
) -> None:
    labels = [k for k, v in breakdown.items() if safe_num(v) > 0]
    values = [safe_num(breakdown[k]) for k in labels]
    if not labels:
        st.caption("No data to display.")
        return

    total = sum(values)
    if not _mpl_available():
        for lbl, val in zip(labels, values):
            pct = (val / total * 100) if total else 0
            st.markdown(f"**{lbl}** — {val:,.0f} ({pct:.0f}%)")
        return

    import matplotlib.pyplot as plt

    colors = colors or ["#2563eb", "#60a5fa", "#93c5fd", "#cbd5e1", "#64748b"]
    fig, ax = plt.subplots(figsize=(3.2, 3.2))
    wedges, _ = ax.pie(
        values,
        labels=None,
        colors=colors[: len(values)],
        startangle=90,
        wedgeprops=dict(width=0.45, edgecolor="white"),
    )
    ax.text(0, 0, f"{center_value}\n{center_label}", ha="center", va="center", fontsize=9, fontweight="bold")
    ax.axis("equal")
    st.pyplot(fig, use_container_width=True, clear_figure=True)
    for lbl, val in zip(labels, values):
        pct = (val / total * 100) if total else 0
        val_s = f"${val:,.0f}" if money_legend else f"{int(val):,}"
        st.markdown(
            f'<div class="ips-coastal-donut-legend"><div><span>{lbl}</span>'
            f'<span><strong>{val_s}</strong> ({pct:.0f}%)</span></div></div>',
            unsafe_allow_html=True,
        )


def safe_num(v: Any) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def render_category_donut(breakdown: dict[str, float], *, key: str) -> None:
    total = sum(safe_num(v) for v in breakdown.values())
    _render_donut(
        breakdown,
        center_label="Total",
        center_value=f"${total:,.0f}",
        key=key,
        colors=["#2563eb", "#0ea5e9", "#6366f1", "#94a3b8"],
    )


def render_job_status_donut(breakdown: dict[str, int], *, key: str) -> None:
    total = int(sum(breakdown.values()))
    _render_donut(
        {k: float(v) for k, v in breakdown.items()},
        center_label="Jobs",
        center_value=str(total),
        key=key,
        colors=["#94a3b8", "#2563eb", "#f59e0b", "#22c55e"],
        money_legend=False,
    )
