"""Charts for coastal dashboard."""

from __future__ import annotations

import streamlit as st


def render_sales_line_chart(current: dict[str, float], previous: dict[str, float]) -> None:
    if not current and not previous:
        try:
            from app.ui.components.empty_states import render_empty_state
        except ImportError:
            from ui.components.empty_states import render_empty_state  # type: ignore
        render_empty_state(
            "No sales data",
            "Sales appear when estimates or paid expenses exist in this date range.",
            icon="📈",
        )
        return

    months = sorted(set(list(current.keys()) + list(previous.keys())))
    if not months:
        months = ["—"]
    cur_vals = [current.get(m, 0.0) for m in months]
    prev_vals = [previous.get(m, 0.0) for m in months]
    labels = [f"{m[5:7]}/{m[2:4]}" if len(m) >= 7 and "-" in m else m for m in months]

    st.markdown(
        '<div class="ips-coastal-chart-legend">'
        '<span><span class="ips-coastal-legend-dot" style="background:#2563eb"></span>This Period</span>'
        '<span><span class="ips-coastal-legend-dot" style="background:#e2e8f0;border:1px dashed #94a3b8"></span>'
        "Last Period</span></div>",
        unsafe_allow_html=True,
    )

    try:
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(7.2, 2.85))
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")
        x = list(range(len(labels)))
        ax.plot(x, cur_vals, color="#2563eb", linewidth=2.2, marker="o", markersize=4)
        ax.plot(
            x,
            prev_vals,
            color="#94a3b8",
            linewidth=1.8,
            linestyle=(0, (5, 4)),
            marker="o",
            markersize=3,
        )
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=8, color="#64748b")
        ax.tick_params(axis="y", labelsize=8, colors="#64748b")
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v/1000:.0f}K" if v >= 1000 else f"${v:.0f}"))
        ax.grid(axis="y", color="#f1f5f9", linewidth=0.8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#e2e8f0")
        ax.spines["bottom"].set_color("#e2e8f0")
        fig.tight_layout(pad=0.6)
        st.pyplot(fig, use_container_width=True, clear_figure=True)
        plt.close(fig)
    except Exception:
        import pandas as pd

        df = pd.DataFrame({"This Period": cur_vals, "Last Period": prev_vals}, index=labels)
        st.line_chart(df, use_container_width=True, color=["#2563eb", "#94a3b8"])


def _render_donut(
    breakdown: dict[str, float | int],
    *,
    center_label: str,
    center_value: str,
    money_legend: bool,
    colors: list[str],
) -> None:
    labels = [k for k, v in breakdown.items() if float(v or 0) > 0]
    values = [float(breakdown[k]) for k in labels]
    if not labels:
        st.caption("No data to display.")
        return
    total = sum(values)
    chart_col, legend_col = st.columns([1.05, 1], gap="small")
    with chart_col:
        try:
            import matplotlib.pyplot as plt

            fig, ax = plt.subplots(figsize=(2.6, 2.6))
            fig.patch.set_facecolor("white")
            ax.pie(
                values,
                colors=colors[: len(values)],
                startangle=90,
                wedgeprops=dict(width=0.42, edgecolor="white", linewidth=1.2),
            )
            ax.text(0, 0.04, center_value, ha="center", va="center", fontsize=10, fontweight="bold", color="#0f172a")
            ax.text(0, -0.14, center_label, ha="center", va="center", fontsize=7.5, color="#64748b")
            ax.axis("equal")
            st.pyplot(fig, use_container_width=True, clear_figure=True)
            plt.close(fig)
        except Exception:
            for lbl, val in zip(labels, values):
                pct = (val / total * 100) if total else 0
                st.markdown(f"**{lbl}** — {val:,.0f} ({pct:.0f}%)")
    with legend_col:
        for lbl, val in zip(labels, values):
            pct = (val / total * 100) if total else 0
            val_s = f"${val:,.0f}" if money_legend else f"{int(val):,}"
            st.markdown(
                f'<div class="ips-coastal-donut-legend"><div><span>{lbl}</span>'
                f"<span><strong>{val_s}</strong> ({pct:.0f}%)</span></div></div>",
                unsafe_allow_html=True,
            )


def render_category_donut(breakdown: dict[str, float]) -> None:
    total = sum(float(v or 0) for v in breakdown.values())
    _render_donut(
        breakdown,
        center_label="Total",
        center_value=f"${total:,.0f}",
        money_legend=True,
        colors=["#2563eb", "#22c55e", "#f59e0b", "#8b5cf6"],
    )


def render_job_status_donut(breakdown: dict[str, int]) -> None:
    total = int(sum(breakdown.values()))
    _render_donut(
        {k: float(v) for k, v in breakdown.items()},
        center_label="Jobs",
        center_value=str(total),
        money_legend=False,
        colors=["#94a3b8", "#2563eb", "#f59e0b", "#22c55e"],
    )
