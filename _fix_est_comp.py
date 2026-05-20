from pathlib import Path

p = Path(r"c:\IPS APP\app\ui\estimates_components.py")
text = p.read_text(encoding="utf-8")
idx = text.find("    body = \"\".join(body_parts)")
if idx < 0:
    raise SystemExit("anchor not found")
tail = '''
    return (
        f'<motion.div class="ips-est-summary-card">'
        f"<h4>{html.escape(title)}</h4>"
        f"<table class='ips-est-kv'>{body}</table>"
        f"</motion.div>"
    )


def donut_chart_html(
    segments: list[tuple[str, float, str]],
    *,
    total_label: str = "Total",
) -> str:
    amounts = [max(0.0, float(a or 0)) for _, a, _ in segments]
    total = sum(amounts)
    if total <= 0:
        return (
            '<div class="ips-est-donut-wrap">'
            '<div class="ips-est-donut" style="background:#e5eaf2;"></div>'
            '<p style="color:#6b7280;font-size:0.78rem;margin:0;">No breakdown data</p></div>'
        )
    pct = [a / total * 100.0 for a in amounts]
    gradient_parts: list[str] = []
    start = 0.0
    for p, (_, _, color) in zip(pct, segments):
        end = start + p
        gradient_parts.append(f"{color} {start:.2f}% {end:.2f}%")
        start = end
    gradient = f"conic-gradient({', '.join(gradient_parts)})"
    legend = "".join(
        f'<div class="row"><span><span class="dot" style="background:{html.escape(c)};"></span>'
        f"{html.escape(lbl)}</span><span>{html.escape(_money_short(amt))} "
        f"({(amt / total * 100):.0f}%)</span></div>"
        for lbl, amt, c in segments
        if amt > 0 or total > 0
    )
    return (
        f'<div class="ips-est-donut-wrap">'
        f'<motion.div class="ips-est-donut" style="background:{gradient};"></div>'
        f'<div class="ips-est-donut-legend">{legend}'
        f'<div class="ips-est-donut-total"><span>{html.escape(total_label)}</span>'
        f"<span>{html.escape(_money_short(total))}</span></div></div></div>"
    )


def _money_short(val: float) -> str:
    try:
        d = Decimal(str(val)).quantize(Decimal("0.01"))
        return f"${d:,.2f}"
    except Exception:
        return "$0.00"


def meta_block_html(label: str, value: str) -> str:
    return (
        f'<div class="ips-est-meta-block">'
        f'<div class="lbl">{html.escape(label)}</div>'
        f'<div class="val">{html.escape(value or "-")}</div></div>'
    )


def date_range_label_html(d_from, d_to) -> str:
    def _fmt(d):
        if d is None:
            return ""
        try:
            return d.strftime("%b %d, %Y")
        except Exception:
            return str(d)[:10]

    a, b = _fmt(d_from), _fmt(d_to)
    if a and b:
        text = f"{a} – {b}"
    elif a:
        text = f"From {a}"
    elif b:
        text = f"Until {b}"
    else:
        text = "Date range"
    return (
        f'<span class="ips-est-date-range-label">'
        f'<span aria-hidden="true">📅</span> {html.escape(text)}</span>'
    )


def render_estimates_header_html() -> None:
    render_estimates_header_left_html()
'''
tail = tail.replace("<motion.div", "<motion.div")  # noop
tail = tail.replace('f\'<motion.div class="ips-est-summary-card">\'', 'f\'<div class="ips-est-summary-card">\'')
tail = tail.replace('f"</motion.div>"', 'f"</div>"')
tail = tail.replace('f\'<motion.div class="ips-est-donut" style="background:{gradient};"></div>\'', 'f\'<div class="ips-est-donut" style="background:{gradient};"></div>\'')
p.write_text(text[:idx] + tail, encoding="utf-8")
print("ok")
