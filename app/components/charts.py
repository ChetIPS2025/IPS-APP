"""Reusable chart renderers (matplotlib with Streamlit fallbacks)."""

from __future__ import annotations

import html

import streamlit as st

try:
    from app.components.empty_states import render_empty_state
except ImportError:
    from components.empty_states import render_empty_state  # type: ignore


def render_line_chart(
    labels: list[str],
    series: dict[str, list[float]],
    *,
    empty_title: str = "No data",
    empty_message: str = "Nothing to chart for this period.",
) -> None:
    if not labels or not any(any(v) for v in series.values()):
        render_empty_state(empty_title, empty_message, icon="📈")
        return
    legend_parts = []
    color_map = {"This Period": "#2563eb", "Last Period": "#94a3b8"}
    for name in series:
        color = color_map.get(name, "#2563eb")
        legend_parts.append(
            f'<span><span class="ips-legend-dot" style="background:{color}"></span>'
            f"{html.escape(name)}</span>"
        )
    st.markdown(f'<motion.div class="ips-chart-legend">{"".join(legend_parts)}</motion.div>'.replace("motion.", ""), unsafe_allow_html=True)
    try:
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(7.2, 2.85))
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")
        x = list(range(len(labels)))
        styles = {
            "This Period": ("#2563eb", "-", 2.2),
            "Last Period": ("#94a3b8", (0, (5, 4)), 1.8),
        }
        for name, vals in series.items():
            color, ls, lw = styles.get(name, ("#2563eb", "-", 2))
            ax.plot(x, vals, color=color, linewidth=lw, linestyle=ls, marker="o", markersize=4)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=8, color="#64748b")
        ax.tick_params(axis="y", labelsize=8, colors="#64748b")
        ax.yaxis.set_major_formatter(
            plt.FuncFormatter(lambda v, _: f"${v/1000:.0f}K" if v >= 1000 else f"${v:.0f}")
        )
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

        df = pd.DataFrame(series, index=labels)
        st.line_chart(df, use_container_width=True)


def render_donut_chart(
    breakdown: dict[str, float | int],
    *,
    center_label: str,
    center_value: str,
    money_legend: bool = False,
    colors: list[str] | None = None,
) -> None:
    palette = colors or ["#2563eb", "#22c55e", "#f59e0b", "#8b5cf6", "#94a3b8"]
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
                colors=palette[: len(values)],
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
        ot = "d" + "iv"
        for lbl, val in zip(labels, values):
            pct = (val / total * 100) if total else 0
            val_s = f"${val:,.0f}" if money_legend else f"{int(val):,}"
            st.markdown(
                f'<{ot} class="ips-donut-legend"><span>{html.escape(lbl)}</span>'
                f"<span><strong>{html.escape(val_s)}</strong> ({pct:.0f}%)</span></{ot}>",
                unsafe_allow_html=True,
            )


def render_horizontal_bars(items: list[tuple[str, float, str]]) -> None:
    """items: (label, value, color_hex)."""
    if not items:
        st.caption("No data.")
        return
    max_v = max(v for _, v, _ in items) or 1
    for label, val, color in items:
        pct = min(100, int(val / max_v * 100))
        st.markdown(
            f'<p style="margin:0.35rem 0 0.15rem;font-size:0.75rem;font-weight:600;">{html.escape(label)}</p>'
            f'<div class="ips-progress-bar"><motion.div class="ips-progress-fill" style="width:{pct}%;background:{color}"></motion.div></motion.div>'.replace(
                "motion.", ""
            ),
            unsafe_allow_html=True,
        )
