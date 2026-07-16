"""Assets management page — shared layout, badges, and summary visuals."""

from __future__ import annotations

import html

import streamlit as st

_STATUS_PILL: dict[str, tuple[str, str, str]] = {
    "in service": ("#15803d", "#dcfce7", "In Service"),
    "out of service": ("#b91c1c", "#fee2e2", "Out of Service"),
    "maintenance": ("#b45309", "#fef3c7", "Maintenance"),
    "retired": ("#475569", "#f1f5f9", "Retired"),
}

_TAB_ICONS: dict[str, str] = {
    "Overview": "▦",
    "Kit / Contents": "🧰",
    "Maintenance": "🔧",
    "Documents": "📄",
    "Assignments": "👤",
    "Depreciation": "📉",
    "Notes": "📝",
    "Activity": "🕐",
}


def inject_assets_page_styles() -> None:
    """Legacy full page styles — prefer :func:`app.components.assets_css.inject_assets_page_css`."""
    from app.components.assets_css import (
        inject_assets_detail_css,
        inject_assets_equipment_css,
        inject_assets_hand_tools_css,
        inject_assets_serialized_css,
        inject_assets_shell_css,
        inject_assets_shared_module_css,
    )

    inject_assets_shell_css()
    inject_assets_shared_module_css()
    inject_assets_equipment_css()
    inject_assets_serialized_css()
    inject_assets_hand_tools_css()
    inject_assets_detail_css()


def render_assets_header_inner_html() -> str:
    return (
        '<div class="ips-assets-header-inner">'
        '<div class="ips-assets-header-icon" aria-hidden="true">🚛</div>'
        "<div>"
        '<p class="ips-assets-header-title">Assets</p>'
        '<p class="ips-assets-header-sub">Track and manage all company assets and equipment.</p>'
        "</div></div>"
    )

def table_header_html(label: str, *, sortable: bool = True) -> str:
    sort = '<span class="ips-assets-th-sort">⇅</span>' if sortable else ""
    return f'<p class="ips-assets-th">{html.escape(label)}{sort}</p>'


def asset_number_cell_html(asset: dict) -> str:
    """Asset # column: compact QR thumbnail beside the asset number."""
    from app.services.asset_qr import qr_embed_subject, qr_thumb_data_uri
    num = str(asset.get("asset_number") or "—")
    num_esc = html.escape(num)
    qr_asset = {
        **asset,
        "asset_id": str(asset.get("asset_number") or asset.get("asset_id") or "").strip(),
    }
    subject = qr_embed_subject(qr_asset)
    uri = qr_thumb_data_uri(subject) if subject else ""
    if not uri:
        return f'<span class="ips-clean-link">{num_esc}</span>'
    alt = html.escape(f"QR code for {num}", quote=True)
    return (
        f'<span class="ips-assets-num-qr-cell">'
        f'<img class="ips-assets-row-qr" src="{uri}" alt="{alt}" width="32" height="32" loading="lazy" />'
        f'<span class="ips-clean-link ips-assets-num-label">{num_esc}</span>'
        f"</span>"
    )

def status_pill_category(status: str) -> str:
    s = str(status or "").strip().lower()
    if s in ("retired", "inactive"):
        return "Retired"
    if s in ("maintenance", "in shop"):
        return "Maintenance"
    if s in ("out for repair", "lost"):
        return "Out of Service"
    return "In Service"

def status_badge_html(status: str) -> str:
    cat = status_pill_category(status)
    fg, bg, label = _STATUS_PILL.get(cat.lower(), ("#64748b", "#f1f5f9", cat))
    return (
        f'<span style="display:inline-block;padding:3px 10px;border-radius:999px;'
        f"font-size:0.68rem;font-weight:700;color:{fg};background:{bg};"
        f'white-space:nowrap;">{html.escape(label)}</span>'
    )

def completed_badge_html() -> str:
    fg, bg, _ = _STATUS_PILL["in service"]
    return (
        f'<span style="display:inline-block;padding:3px 10px;border-radius:999px;'
        f"font-size:0.68rem;font-weight:700;color:{fg};background:{bg};"
        f'white-space:nowrap;">Completed</span>'
    )

def summary_card_html(
    title: str,
    rows: list[tuple[str, str]],
    *,
    html_value_keys: frozenset[str] | None = None,
) -> str:
    raw_keys = html_value_keys or frozenset()
    body_parts: list[str] = []
    for k, v in rows:
        if k in raw_keys:
            val_cell = f'<td class="v">{v}</td>'
        else:
            val_cell = f'<td class="v">{html.escape(str(v or "—"))}</td>'
        body_parts.append(f'<tr><td class="k">{html.escape(k)}</td>{val_cell}</tr>')
    body = "".join(body_parts)
    return (
        f'<div class="ips-assets-summary-card">'
        f"<h4>{html.escape(title)}</h4>"
        f'<table class="ips-assets-kv"><tbody>{body}</tbody></table>'
        "</div>"
    )

def detail_header_html(*, asset_id: str, asset_name: str, status: str) -> str:
    return (
        '<div class="ips-assets-detail-top-left">'
        '<div class="ips-assets-detail-id-row">'
        f'<span class="ips-assets-detail-id">{html.escape(asset_id)}</span>'
        f"{status_badge_html(status)}"
        "</div>"
        f'<p class="ips-assets-detail-name-lg">{html.escape(asset_name)}</p>'
        "</div>"
    )

def detail_meta_grid_html(items: list[tuple[str, str]]) -> str:
    """Render compact asset detail metadata grid."""
    safe_items = items or []
    cells: list[str] = []
    for label, value in safe_items:
        cells.append(
            f'<div class="asset-meta-cell">'
            f'<div class="asset-meta-label">{html.escape(str(label or ""))}</div>'
            f'<div class="asset-meta-value">{html.escape(str(value if value is not None else "—"))}</div>'
            "</div>"
        )
    return f'<div class="asset-meta-grid">{"".join(cells)}</div>'


def detail_meta_strip_html(items: list[tuple[str, str]]) -> str:
    """Horizontal metadata row (reference mockup center strip)."""
    blocks = "".join(
        f'<div class="ips-assets-meta-block">'
        f'<span class="lbl">{html.escape(str(k))}</span>'
        f'<span class="val">{html.escape(str(v or "—"))}</span>'
        "</div>"
        for k, v in (items or [])
    )
    return f'<div class="ips-assets-meta-strip">{blocks}</div>'


def maintenance_table_html(rows: list[dict[str, str]]) -> str:
    if not rows:
        return '<p style="color:#9ca3af;font-size:0.8rem;margin:0;">No maintenance records yet.</p>'
    head = (
        "<tr><th>Date</th><th>Type</th><th>Description</th><th>Performed By</th>"
        "<th>Cost</th><th>Next Due</th><th>Status</th></tr>"
    )
    body_parts: list[str] = []
    for r in rows:
        st_cell = r.get("status_html") or completed_badge_html()
        body_parts.append(
            "<tr>"
            f"<td>{html.escape(r.get('date', '—'))}</td>"
            f"<td>{html.escape(r.get('type', '—'))}</td>"
            f"<td>{html.escape(r.get('description', '—'))}</td>"
            f"<td>{html.escape(r.get('performed_by', '—'))}</td>"
            f"<td>{html.escape(r.get('cost', '—'))}</td>"
            f"<td>{html.escape(r.get('next_due', '—'))}</td>"
            f"<td>{st_cell}</td>"
            "</tr>"
        )
    return (
        '<table class="ips-assets-maint-table"><thead>'
        f"{head}</thead><tbody>{''.join(body_parts)}</tbody></table>"
    )

def tab_button_label(tab: str) -> str:
    icon = _TAB_ICONS.get(tab, "")
    return f"{icon}  {tab}" if icon else tab
