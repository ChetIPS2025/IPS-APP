"""Job detail tabs: Tasks (with photos + reference attachments), Cost — field review in Work & Plan (Supervisor)."""

from __future__ import annotations

import hashlib
import html
import re
from datetime import date, datetime, timezone
from typing import Any, Callable
from urllib.parse import quote

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
try:
    from app.db import (
        create_signed_url,
        delete_rows,
        delete_rows_admin,
        fetch_by_match,
        fetch_by_match_admin,
        insert_row,
        insert_row_admin,
        update_rows,
        update_rows_admin,
        upload_bytes,
        upload_bytes_admin,
    )
except ImportError:
    from db import (  # type: ignore
        create_signed_url,
        delete_rows,
        delete_rows_admin,
        fetch_by_match,
        fetch_by_match_admin,
        insert_row,
        insert_row_admin,
        update_rows,
        update_rows_admin,
        upload_bytes,
        upload_bytes_admin,
    )

try:
    from app.services import task_photos as _tp_svc
except ImportError:
    import services.task_photos as _tp_svc  # type: ignore

try:
    from app.services.task_display import task_number_display
except ImportError:
    from services.task_display import task_number_display  # type: ignore

try:
    from app.pages import job_database_task_photos_ui as _tph
except ImportError:
    import pages.job_database_task_photos_ui as _tph  # type: ignore

try:
    from app.pages import job_database_mobile_task_ui as _mob
except ImportError:
    import pages.job_database_mobile_task_ui as _mob  # type: ignore

try:
    from app.pages import job_reference_attachments_ui as _jra_ui
except ImportError:
    import pages.job_reference_attachments_ui as _jra_ui  # type: ignore

try:
    from app.services import job_reference_attachments as _jra_svc
except ImportError:
    import services.job_reference_attachments as _jra_svc  # type: ignore

try:
    from app.services.supervisor_planning import TASK_STATUSES
except ImportError:
    from services.supervisor_planning import TASK_STATUSES  # type: ignore

try:
    from app.auth import current_role as _jra_role
except ImportError:
    from auth import current_role as _jra_role  # type: ignore

try:
    from app.ui.field_light_theme import inject_field_light_theme
except ImportError:
    from ui.field_light_theme import inject_field_light_theme  # type: ignore

try:
    from app.ui import IPS_NAV_PENDING_KEY
except ImportError:
    from ui import IPS_NAV_PENDING_KEY  # type: ignore

try:
    from app.ui.modal import ensure_modal_styles, modal_wide_marker
except ImportError:
    from ui.modal import ensure_modal_styles, modal_wide_marker  # type: ignore

try:
    from app.utils.formatters import job_display_label as _job_display_label
except ImportError:
    from utils.formatters import job_display_label as _job_display_label  # type: ignore

# Task status labels for badges / pickers
_JDT_STATUS_LABELS: dict[str, str] = {
    "not_started": "Not Started",
    "in_progress": "In Progress",
    "complete": "Complete",
    "partial": "Partial",
    "blocked": "Blocked",
    "duplicate": "Duplicate",
    "electrical": "Electrical / Other Trade",
    "waiting_on_customer": "Waiting on Customer",
    "cancelled": "Cancelled",
}

_REVIEW_STATUS_LABELS: dict[str, str] = {
    "complete": "Complete",
    "partial": "Partial",
    "blocked": "Blocked",
    "not_started": "Not Started",
    "duplicate": "Duplicate",
    "electrical": "Electrical / other trade",
    "waiting_on_customer": "Waiting on customer",
}


def _task_status_display(slug: str) -> str:
    s = str(slug or "").strip().lower()
    if s == "open":
        s = "not_started"
    return _REVIEW_STATUS_LABELS.get(s, s.replace("_", " ").title() or "—")


def _task_status_badge(slug: str) -> str:
    s = str(slug or "").strip().lower()
    if s == "open":
        s = "not_started"
    colors = {
        "complete": "#16a34a",
        "in_progress": "#f59e0b",
        "partial": "#f59e0b",
        "blocked": "#dc2626",
        "not_started": "#64748b",
        "duplicate": "#64748b",
        "electrical": "#7c3aed",
        "waiting_on_customer": "#0891b2",
        "cancelled": "#64748b",
    }
    col = colors.get(s, "#64748b")
    return (
        f'<span class="ips-status-badge" style="--ips-status-color:{html.escape(col)};">'
        f"{html.escape(_task_status_display(s))}</span>"
    )


def _priority_badge_html(priority: Any) -> str:
    pr = str(priority or "normal").strip().lower()
    if pr not in ("low", "normal", "high", "critical"):
        pr = "normal"
    label = pr.title()
    return f'<span class="ips-priority-badge {html.escape(pr)}">{html.escape(label)}</span>'


def _inject_task_card_row_css() -> None:
    key = "ips_jdt_task_card_css_v4"
    if st.session_state.get(key):
        return
    st.session_state[key] = True
    st.markdown(
        """
        <style>
        /* Compact work instruction card */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-jdt-task-card) {
            background-color: #ffffff !important;
            border: 1px solid #d1d5db !important;
            border-radius: 12px !important;
            margin-bottom: 12px !important;
            box-sizing: border-box !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-jdt-task-card) > div {
            padding: 12px 16px !important;
        }
        /* Main | preview row: desktop = info left, preview right; narrow = preview on top */
        div[data-testid="stHorizontalBlock"]:has(.ips-jdt-split-main):has(.ips-jdt-split-prev) {
            align-items: center !important;
            gap: 12px !important;
        }
        @media (max-width: 900px) {
            div[data-testid="stHorizontalBlock"]:has(.ips-jdt-split-main):has(.ips-jdt-split-prev) {
                flex-direction: column-reverse !important;
            }
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-jdt-task-card) button[kind] {
            min-height: 2.85rem !important;
            font-size: 1.02rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-jdt-task-card) button[kind="secondary"] {
            background-color: #f3f4f6 !important;
            color: #111827 !important;
            border: 1px solid #d1d5db !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-jdt-task-card) button[kind="secondary"]:hover {
            background-color: #e5e7eb !important;
            border-color: #9ca3af !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-jdt-task-card) button[kind="primary"] {
            background-color: #2563eb !important;
            color: #ffffff !important;
            border: 1px solid #1d4ed8 !important;
            border-radius: 0.5rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-jdt-task-card) button[kind="primary"]:hover {
            background-color: #1d4ed8 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _inject_jdt_field_tap_css() -> None:
    key = "ips_jdt_field_tap_css_v1"
    if st.session_state.get(key):
        return
    st.session_state[key] = True
    st.markdown(
        """
        <style>
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-jdt-field-zone) {
            background-color: #d1d5db !important;
            padding: 0.75rem !important;
            border-radius: 12px !important;
            margin-bottom: 0.75rem !important;
            box-sizing: border-box !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-jdt-task-card) {
            background: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 12px !important;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08) !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-jdt-task-card) div[data-testid="stSelectbox"] label {
            display: none !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-jdt-task-card) div[data-testid="stSelectbox"] > div {
            min-height: 3rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


_JDT_JOB_DATA_VER_PREFIX = "jdt_job_data_ver_"


def _jdt_job_data_ver_key(job_id: str) -> str:
    return f"{_JDT_JOB_DATA_VER_PREFIX}{str(job_id).strip()}"


def _bump_jdt_job_data_cache(job_id: str) -> None:
    """Invalidate cached job tasks + reference rows for this job (session-scoped version)."""
    k = _jdt_job_data_ver_key(job_id)
    st.session_state[k] = int(st.session_state.get(k, 0)) + 1


@st.cache_data(ttl=45)
def _cached_fetch_job_tasks(job_id: str, admin_token: int, data_ver: int) -> list[dict[str, Any]]:
    fn = fetch_by_match_admin if admin_token else fetch_by_match
    try:
        return list(fn("job_tasks", {"job_id": str(job_id).strip()}, limit=500) or [])
    except Exception:
        return []


@st.cache_data(ttl=45)
def _cached_fetch_job_reference_attachments(job_id: str, admin_token: int, data_ver: int) -> list[dict[str, Any]]:
    fn = fetch_by_match_admin if admin_token else fetch_by_match
    try:
        return list(
            fn("job_reference_attachments", {"job_id": str(job_id).strip()}, limit=300) or []
        )
    except Exception:
        return []


def _load_job_tasks_cached(job_id: str, *, admin_read: bool) -> list[dict[str, Any]]:
    ver = int(st.session_state.get(_jdt_job_data_ver_key(job_id), 0))
    return list(_cached_fetch_job_tasks(str(job_id).strip(), 1 if admin_read else 0, ver))


def _load_job_ref_attachments_cached(job_id: str, *, admin_read: bool) -> list[dict[str, Any]]:
    ver = int(st.session_state.get(_jdt_job_data_ver_key(job_id), 0))
    return list(_cached_fetch_job_reference_attachments(str(job_id).strip(), 1 if admin_read else 0, ver))


def _ref_attach_rows_for_job(job_id: str, *, admin_read: bool) -> list[dict[str, Any]]:
    return _load_job_ref_attachments_cached(job_id, admin_read=admin_read)


_JDT_REF_PDF_CSS_KEY = "ips_jdt_task_ref_pdf_css_v3"


def _inject_jdt_task_ref_pdf_css() -> None:
    """Shared job reference PDF viewer + reference modal layout (no per-card iframes)."""
    if st.session_state.get(_JDT_REF_PDF_CSS_KEY):
        return
    st.session_state[_JDT_REF_PDF_CSS_KEY] = True
    st.markdown(
        """
        <style>
        .ips-jdt-refpdf-host {
            width: 100%;
            max-width: 100%;
            overflow: hidden;
            box-sizing: border-box;
            margin: 0 0 0.65rem 0;
        }
        .ips-jdt-refpdf-host iframe.ips-jdt-refpdf-frame {
            width: 100% !important;
            max-width: 100% !important;
            border: 1px solid #d1d5db;
            border-radius: 10px;
            background: #ffffff;
            display: block;
            box-sizing: border-box;
        }
        .ips-jdt-refpdf-host--top iframe.ips-jdt-refpdf-frame {
            height: 500px !important;
            min-height: 320px !important;
        }
        .ips-jdt-refpdf-host--modal iframe.ips-jdt-refpdf-frame {
            height: min(72vh, 780px) !important;
            min-height: 280px !important;
        }
        div[data-testid="stDialog"]:has(.ips-jdt-refpdf-dialog-mark) {
            width: min(98vw, 1100px) !important;
            max-width: 98vw !important;
        }
        div[data-testid="stDialog"]:has(.ips-jdt-refpdf-dialog-mark) > div {
            max-width: 100% !important;
            overflow-x: hidden !important;
            box-sizing: border-box !important;
        }
        .ips-jdt-refimg-wrap {
            width: 100%;
            max-width: 100%;
            overflow: hidden;
            box-sizing: border-box;
            margin: 0 0 0.5rem 0;
        }
        .ips-jdt-refimg-wrap img {
            display: block;
            width: 100%;
            max-width: 100%;
            height: auto;
            max-height: min(70vh, 640px);
            object-fit: contain;
            border-radius: 10px;
            border: 1px solid #d1d5db;
            background: #f9fafb;
            box-sizing: border-box;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _jdt_job_id_matches_row(r: dict[str, Any], job_id: str) -> bool:
    """Match attachment row to current job (tolerate casing / missing job_id on scoped fetch)."""
    jid = str(job_id or "").strip()
    if not jid:
        return False
    rj = str((r or {}).get("job_id") or "").strip()
    if not rj:
        return True
    return rj.lower() == jid.lower()


def _jdt_row_is_pdf_attachment(r: dict[str, Any]) -> bool:
    fname = str((r or {}).get("file_name") or "")
    ftype = str((r or {}).get("file_type") or "").strip().lower()
    if _jra_svc.normalize_extension(fname) == "pdf":
        return True
    return ftype == "application/pdf"


def _jdt_row_is_image_attachment(r: dict[str, Any]) -> bool:
    fname = str((r or {}).get("file_name") or "")
    ftype = str((r or {}).get("file_type") or "").strip().lower()
    if _jra_svc.is_image_filename(fname):
        return True
    return ftype.startswith("image/")


def _jdt_dedupe_sort_attachments(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = sorted(rows, key=lambda x: str((x or {}).get("created_at") or ""), reverse=True)
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for r in rows:
        rid = str((r or {}).get("id") or "").strip()
        if rid:
            if rid in seen:
                continue
            seen.add(rid)
        out.append(r)
    return out


def _jdt_job_wide_attachments(job_id: str, att_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """``job_reference_attachments`` for this job with ``task_id`` null (job-wide)."""
    jid = str(job_id or "").strip()
    raw: list[dict[str, Any]] = []
    for r in att_rows or []:
        if not isinstance(r, dict):
            continue
        if not _jdt_job_id_matches_row(r, jid):
            continue
        if str((r or {}).get("task_id") or "").strip():
            continue
        if not str((r or {}).get("file_url") or "").strip():
            continue
        raw.append(r)
    return _jdt_dedupe_sort_attachments(raw)


def _jdt_merged_attachments_for_task(
    job_id: str, task_id: str, att_rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Job-wide (null ``task_id``) + rows for ``task_id``; all attachment types with storage path."""
    jid = str(job_id or "").strip()
    tid = str(task_id or "").strip()
    raw: list[dict[str, Any]] = []
    for r in att_rows or []:
        if not isinstance(r, dict):
            continue
        if not _jdt_job_id_matches_row(r, jid):
            continue
        rt = str((r or {}).get("task_id") or "").strip()
        if rt and rt != tid:
            continue
        if not str((r or {}).get("file_url") or "").strip():
            continue
        raw.append(r)
    return _jdt_dedupe_sort_attachments(raw)


def _jdt_gview_embed_url(public_file_url: str) -> str:
    q = quote(str(public_file_url).strip(), safe="")
    return f"https://docs.google.com/gview?url={q}&embedded=true"


# Task card reference preview: larger so PDFs are readable without scrolling.
_JDT_WCP_DESKTOP_H = 480
_JDT_WCP_MOBILE_H = 360
_JDT_CARD_PREVIEW_COMPONENT_H = _JDT_WCP_DESKTOP_H + 40

# Injected per components.html iframe (parent page CSS does not reach the sandbox).
_JDT_WCP_STYLE = (
    """
<style>
.ips-jdt-wcp-root{{width:100%;max-width:100%;margin:0;padding:0;box-sizing:border-box;}}
.ips-jdt-wcp-pad{{padding:14px 0;}}
.ips-jdt-wcp-fill{{
  width:100%;margin:0;padding:0;border-radius:10px;border:1px solid #d1d5db;
  box-sizing:border-box;overflow:hidden;background:#fff;
  height:{desktop_h}px;display:block;position:relative;
}}
@media (max-width:900px){{
  .ips-jdt-wcp-fill{{height:{mobile_h}px!important;}}
}}
.ips-jdt-wcp-fill iframe.ips-jdt-wcp-iframe{{
  width:100%!important;height:100%!important;border:none!important;display:block;margin:0;padding:0;
  box-sizing:border-box;overflow:hidden;
}}
.ips-jdt-wcp-fill img.ips-jdt-wcp-img{{
  width:100%;height:100%;object-fit:contain;object-position:center;display:block;margin:0;padding:0;
  background:#f3f4f6;
}}
.ips-jdt-wcp-ph{{
  width:100%;margin:0;padding:0;border-radius:10px;border:1px solid #d1d5db;box-sizing:border-box;
  height:{desktop_h}px;display:flex;flex-direction:column;align-items:center;justify-content:center;
  color:#6b7280;font-size:0.8125rem;
}}
@media (max-width:900px){{
  .ips-jdt-wcp-ph{{height:{mobile_h}px!important;}}
}}
.ips-jdt-wcp-ph--muted{{background:#f3f4f6;}}
.ips-jdt-wcp-ph--empty{{background:#e5e7eb;}}
.ips-jdt-wcp-link{{
  width:100%;height:{desktop_h}px;margin:0;padding:0;border-radius:10px;border:1px solid #d1d5db;
  box-sizing:border-box;display:flex;flex-direction:column;align-items:center;justify-content:center;
  text-align:center;background:#e5e7eb;color:#374151;text-decoration:none;font-size:0.8125rem;
}}
@media (max-width:900px){{
  .ips-jdt-wcp-link{{height:{mobile_h}px!important;}}
}}
</style>
"""
).format(desktop_h=_JDT_WCP_DESKTOP_H, mobile_h=_JDT_WCP_MOBILE_H)


def _jdt_work_card_preview_shell(inner: str) -> str:
    return f'{_JDT_WCP_STYLE}<div class="ips-jdt-wcp-root"><div class="ips-jdt-wcp-pad">{inner}</div></div>'


def _jdt_work_card_preview_placeholder_html() -> str:
    return _jdt_work_card_preview_shell(
        '<div class="ips-jdt-wcp-ph ips-jdt-wcp-ph--empty">'
        '<span style="font-size:1.75rem;line-height:1;">📄</span>'
        "<span style=\"margin-top:4px;\">No reference</span></div>"
    )


def _jdt_work_card_preview_unavailable_html() -> str:
    return _jdt_work_card_preview_shell(
        '<div class="ips-jdt-wcp-ph ips-jdt-wcp-ph--muted"><span>Preview unavailable</span></div>'
    )


def _jdt_work_card_preview_html(*, signed_url: str, row: dict[str, Any]) -> str:
    """Right-rail reference preview: Google viewer / image; lazy-loaded; compact margins."""
    fname = html.escape(str((row or {}).get("file_name") or "Reference"))
    if _jdt_row_is_pdf_attachment(row):
        v = _jdt_gview_embed_url(signed_url)
        src = html.escape(v, quote=True)
        inner = (
            f'<div class="ips-jdt-wcp-fill">'
            f'<iframe class="ips-jdt-wcp-iframe" src="{src}" title="{fname}" loading="lazy" '
            'referrerpolicy="no-referrer-when-downgrade"></iframe></div>'
        )
        return _jdt_work_card_preview_shell(inner)
    if _jdt_row_is_image_attachment(row):
        su = html.escape(signed_url, quote=True)
        inner = (
            '<div class="ips-jdt-wcp-fill" style="background:#f3f4f6;">'
            f'<img class="ips-jdt-wcp-img" src="{su}" alt="{fname}" loading="lazy" decoding="async" />'
            "</div>"
        )
        return _jdt_work_card_preview_shell(inner)
    su = html.escape(signed_url, quote=True)
    inner = (
        f'<a class="ips-jdt-wcp-link" href="{su}" target="_blank" rel="noopener noreferrer">'
        '<span style="font-size:1.75rem;line-height:1;">📄</span>'
        "<span style=\"margin-top:4px;\">Open file</span></a>"
    )
    return _jdt_work_card_preview_shell(inner)


def _jdt_pick_primary_modal_reference_row(merged: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Prefer first PDF, then first image, else first row (job-wide + task merged list)."""
    if not merged:
        return None
    for r in merged:
        if isinstance(r, dict) and _jdt_row_is_pdf_attachment(r):
            return r
    for r in merged:
        if isinstance(r, dict) and _jdt_row_is_image_attachment(r):
            return r
    m0 = merged[0]
    return m0 if isinstance(m0, dict) else None


def _jdt_gview_modal_90vh_iframe_html(*, signed_url: str, title: str) -> str:
    """Google Docs viewer for expanded reference modal (width 100%, ~90vh)."""
    v = _jdt_gview_embed_url(signed_url)
    src = html.escape(v, quote=True)
    safe_title = html.escape(title)
    return (
        f'<div style="width:100%;max-width:100%;box-sizing:border-box;margin:0;padding:0;">'
        f'<iframe src="{src}" title="{safe_title}" loading="lazy" '
        'referrerpolicy="no-referrer-when-downgrade" '
        'style="width:100%;height:90vh;min-height:360px;border:none;'
        'border-radius:10px;display:block;box-sizing:border-box;"></iframe>'
        f"</div>"
    )


def _clear_jdt_reference_overlay() -> None:
    st.session_state["show_reference"] = False
    for k in ("reference_url", "reference_modal_task_id", "reference_job_id"):
        if k in st.session_state:
            del st.session_state[k]


def _jdt_ref_pdf_iframe_html(*, signed_url: str, title: str, variant: str) -> str:
    """Google Docs viewer inside components.html; variant: 'top' (500px) or 'modal' (tall)."""
    viewer = _jdt_gview_embed_url(signed_url)
    src_attr = html.escape(viewer, quote=True)
    safe_title = html.escape(title)
    host_cls = "ips-jdt-refpdf-host ips-jdt-refpdf-host--top" if variant == "top" else "ips-jdt-refpdf-host ips-jdt-refpdf-host--modal"
    return f"""<style>
.ips-jdt-refpdf-host {{
  width: 100%;
  max-width: 100%;
  overflow: hidden;
  box-sizing: border-box;
  margin: 0;
}}
.ips-jdt-refpdf-host iframe.ips-jdt-refpdf-frame {{
  width: 100% !important;
  max-width: 100% !important;
  border: 1px solid #d1d5db;
  border-radius: 10px;
  background: #ffffff;
  display: block;
  box-sizing: border-box;
}}
.ips-jdt-refpdf-host--top iframe.ips-jdt-refpdf-frame {{
  height: 500px !important;
  min-height: 280px !important;
}}
.ips-jdt-refpdf-host--modal iframe.ips-jdt-refpdf-frame {{
  height: min(72vh, 780px) !important;
  min-height: 280px !important;
}}
</style>
<div class="{host_cls}">
<iframe class="ips-jdt-refpdf-frame" src="{src_attr}" title="{safe_title}" loading="lazy"
  referrerpolicy="no-referrer-when-downgrade"></iframe>
</div>"""


def _jdt_sign_attachment_row(r: dict[str, Any], *, bucket: str) -> tuple[str, str]:
    path = str((r or {}).get("file_url") or "").strip()
    fname = str((r or {}).get("file_name") or "file").strip() or "file"
    if not path:
        return "", fname
    try:
        signed = create_signed_url(path, expires_in=3600, bucket=bucket)
    except Exception:
        signed = ""
    return (str(signed or "").strip(), fname)


def _jdt_render_reference_preview(
    row: dict[str, Any],
    *,
    bucket: str,
    variant: str,
) -> None:
    """PDF: Google viewer iframe. Image: full-width img. Other: open link."""
    signed, fname = _jdt_sign_attachment_row(row, bucket=bucket)
    if not signed:
        st.caption("Preview link unavailable.")
        return
    _inject_jdt_task_ref_pdf_css()
    if _jdt_row_is_pdf_attachment(row):
        h = 520 if variant == "top" else 720
        components.html(
            _jdt_ref_pdf_iframe_html(signed_url=signed, title=fname, variant=variant),
            height=h,
            scrolling=True,
        )
    elif _jdt_row_is_image_attachment(row):
        safe_u = html.escape(signed, quote=True)
        safe_a = html.escape(fname)
        st.markdown(
            f'<div class="ips-jdt-refimg-wrap">'
            f'<img src="{safe_u}" alt="{safe_a}" loading="lazy" />'
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        st.link_button("View / Open", signed, use_container_width=True)


@st.dialog("Job reference", width="large")
def _jdt_reference_preview_dialog(*, job_id: str, admin_read: bool, bucket: str) -> None:
    """Opened when ``show_reference`` is true; previews signed ``reference_url`` (PDF / image / link)."""
    st.markdown('<span class="ips-jdt-refpdf-dialog-mark"></span>', unsafe_allow_html=True)
    _inject_jdt_task_ref_pdf_css()
    tid = str(st.session_state.get("reference_modal_task_id") or "").strip()
    if not tid:
        st.caption("Missing task context for this reference.")
        if st.button("Close", use_container_width=True, key=f"jdt_ref_overlay_close_notid_{job_id}"):
            _clear_jdt_reference_overlay()
            st.rerun()
        return
    rows = _ref_attach_rows_for_job(job_id, admin_read=admin_read)
    merged = _jdt_merged_attachments_for_task(job_id, tid, rows)
    if not merged:
        st.caption("No reference attachments for this task.")
        if st.button("Close", use_container_width=True, key=f"jdt_ref_overlay_close_empty_{job_id}"):
            _clear_jdt_reference_overlay()
            st.rerun()
        return

    hdr_l, hdr_r = st.columns([5, 1])
    with hdr_l:
        st.markdown("##### Reference preview")
    with hdr_r:
        if st.button("Close", type="primary", use_container_width=True, key=f"jdt_ref_overlay_close_{job_id}"):
            _clear_jdt_reference_overlay()
            st.rerun()

    sel_ix = 0
    if len(merged) > 1:
        labels = [str((r or {}).get("file_name") or f"File {i + 1}")[:120] for i, r in enumerate(merged)]
        sel_ix = int(
            st.selectbox(
                "Select Reference File",
                options=list(range(len(merged))),
                format_func=lambda i, _lbls=labels: _lbls[int(i)],
                key=f"jdt_ref_overlay_pick_{job_id}_{tid}",
            )
        )

    row = merged[sel_ix]
    signed, fname = _jdt_sign_attachment_row(row, bucket=bucket)
    if signed:
        st.session_state["reference_url"] = signed
    url = str(st.session_state.get("reference_url") or "").strip()
    if not url:
        st.caption("Preview link unavailable.")
        return

    if _jdt_row_is_pdf_attachment(row):
        components.html(
            _jdt_gview_modal_90vh_iframe_html(signed_url=url, title=fname),
            height=900,
            scrolling=True,
        )
    elif _jdt_row_is_image_attachment(row):
        safe_u = html.escape(url, quote=True)
        safe_a = html.escape(fname)
        st.markdown(
            f'<div class="ips-jdt-refimg-wrap" style="max-height:90vh;overflow:auto;">'
            f'<img src="{safe_u}" alt="{safe_a}" loading="lazy" '
            'style="width:100%;max-width:100%;max-height:90vh;object-fit:contain;border-radius:10px;'
            'border:none;display:block;box-sizing:border-box;" />'
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        st.link_button("View / Open", url, use_container_width=True, type="primary")


def _jdt_status_label(slug: str) -> str:
    s = str(slug or "not_started").strip().lower()
    if s == "open":
        s = "not_started"
    return _JDT_STATUS_LABELS.get(s, s.replace("_", " ").title())


def _norm_task_status_slug(val: Any) -> str:
    s = str(val or "not_started").strip().lower()
    if s == "open":
        return "not_started"
    return s


def _fetch_job_task_by_id(task_id: str, *, admin_read: bool) -> dict[str, Any] | None:
    tid = str(task_id or "").strip()
    if not tid:
        return None
    fn = fetch_by_match_admin if admin_read else fetch_by_match
    try:
        r = fn("job_tasks", {"id": tid}, limit=1) or []
        return r[0] if r and isinstance(r[0], dict) else None
    except Exception:
        return None


def _persist_quick_task_update(
    *,
    upd: Callable[..., Any],
    tid: str,
    task_row: dict[str, Any],
    status: str,
    notes: str,
    admin_read: bool,
) -> tuple[bool, str]:
    rows_all = _tph.fetch_task_photos(tid, admin=admin_read)
    by_tp = _tp_svc.photos_by_task_id(rows_all)
    ns = str(status or "").strip().lower()
    if ns == "complete" and not _tp_svc.task_has_after_photo(tid, task_row, by_tp):
        return False, "After photo required to complete task."
    try:
        payload: dict[str, Any] = {
            "status": ns,
            "notes": str(notes or "").strip()[:4000],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if ns == "complete":
            payload["completed_date"] = date.today().isoformat()[:10]
        else:
            payload["completed_date"] = None
        upd("job_tasks", payload, {"id": tid})
        return True, ""
    except Exception as exc:
        return False, str(exc)


def _make_jdt_status_save_cb(
    job_id: str,
    tid: str,
    *,
    admin_read: bool,
    upd: Callable[..., Any],
    can_edit_tasks: bool,
) -> Callable[[], None]:
    """Persist status on selectbox change (one DB write; cache bump; no extra rerun)."""

    def _cb() -> None:
        if not can_edit_tasks:
            return
        jid = str(job_id).strip()
        tid_s = str(tid).strip()
        ver = int(st.session_state.get(_jdt_job_data_ver_key(jid), 0))
        rows_now = list(_cached_fetch_job_tasks(jid, 1 if admin_read else 0, ver))
        rowp = next(
            (x for x in rows_now if isinstance(x, dict) and str(x.get("id") or "").strip() == tid_s),
            None,
        )
        if not rowp:
            return
        nst = _norm_task_status_slug(st.session_state.get(f"jdt_st_{jid}_{tid_s}"))
        old = _norm_task_status_slug(rowp.get("status"))
        if nst == old:
            return
        ok, err = _persist_quick_task_update(
            upd=upd,
            tid=tid_s,
            task_row=dict(rowp),
            status=nst,
            notes=str(rowp.get("notes") or ""),
            admin_read=admin_read,
        )
        if ok:
            _bump_jdt_job_data_cache(jid)
            try:
                st.toast("Status saved")
            except Exception:
                pass
            st.rerun()
        else:
            st.session_state[f"jdt_st_{jid}_{tid_s}"] = old
            st.session_state[f"jdt_st_flash_{jid}_{tid_s}"] = str(err)

    return _cb


@st.dialog("Camera", width="large")
def _task_camera_capture_dialog(*, job_id: str, tid: str, admin_read: bool) -> None:
    """Single camera capture → auto-save as progress photo; optional file upload."""
    row = _fetch_job_task_by_id(tid, admin_read=admin_read) or {}
    st.markdown(f"**{html.escape(task_number_display(row))}**")
    st.caption("Capture saves automatically as a **progress** photo.")
    ver = int(st.session_state.get(f"jdt_capver_{job_id}_{tid}", 0))
    cam = st.camera_input(
        "Capture",
        key=f"jdt_capinp_{job_id}_{tid}_{ver}",
        label_visibility="collapsed",
        help="Take a photo",
    )
    if cam is not None:
        raw = cam.getvalue()
        if len(raw) > 800:
            sig = hashlib.sha256(raw).hexdigest()
            last_sig = str(st.session_state.get(f"jdt_capsig_{job_id}_{tid}") or "")
            if sig != last_sig:
                try:
                    _tph.save_task_progress_photo_from_bytes(
                        task_id=tid,
                        raw=raw,
                        fname="capture.jpg",
                        admin_read=admin_read,
                    )
                    st.session_state[f"jdt_capsig_{job_id}_{tid}"] = sig
                    st.session_state[f"jdt_capver_{job_id}_{tid}"] = ver + 1
                    st.session_state.pop(f"jdt_cam_dlg_{job_id}", None)
                    _bump_jdt_job_data_cache(job_id)
                    try:
                        st.toast("Photo saved")
                    except Exception:
                        pass
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
    with st.expander("Upload from files instead", expanded=False):
        up = st.file_uploader(
            "Photo file",
            type=["jpg", "jpeg", "png", "webp"],
            key=f"jdt_capup_{job_id}_{tid}",
            label_visibility="collapsed",
        )
        if up is not None and st.button("Upload", type="primary", key=f"jdt_capup_go_{job_id}_{tid}"):
            try:
                raw = up.getvalue()
                nm = str(getattr(up, "name", "") or "upload.jpg")
                _tph.save_task_progress_photo_from_bytes(
                    task_id=tid,
                    raw=raw,
                    fname=nm,
                    admin_read=admin_read,
                )
                st.session_state.pop(f"jdt_cam_dlg_{job_id}", None)
                _bump_jdt_job_data_cache(job_id)
                try:
                    st.toast("Photo saved")
                except Exception:
                    pass
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    if st.button("Close", use_container_width=True, key=f"jdt_cap_close_{job_id}_{tid}"):
        st.session_state.pop(f"jdt_cam_dlg_{job_id}", None)
        st.rerun()


@st.dialog("Task details", width="large")
def _task_view_details_dialog(
    *,
    job_id: str,
    tid: str,
    task_row: dict[str, Any],
    att_rows: list[dict[str, Any]],
    bucket: str,
    can_edit: bool,
    admin_read: bool,
    upd: Callable[..., Any],
    dlt: Callable[..., Any],
    can_manage_attachments: bool,
) -> None:
    """Full action, reference files for this task, photo history, supervisor."""
    st.markdown(f"#### {html.escape(task_number_display(task_row))}")
    st.caption("Full task context — change status from the task list.")
    arq = str(task_row.get("action_required") or "").strip()
    st.markdown("**Action required**")
    if arq:
        st.markdown(f"<div style='white-space:pre-wrap;font-size:0.92rem'>{html.escape(arq[:8000])}</div>", unsafe_allow_html=True)
    else:
        st.caption("—")

    with st.spinner("Loading..."):
        _jra_ui.render_task_details_reference_attachments(
            job_id=job_id,
            task_id=tid,
            att_rows=list(att_rows or []),
            bucket=bucket,
            can_manage=can_manage_attachments,
            dlt=dlt,
        )

    st.markdown("**Photo history**")
    with st.spinner("Loading..."):
        try:
            ph_rows = list(_tph.fetch_task_photos(tid, admin=admin_read) or [])
        except Exception:
            ph_rows = []
    if not ph_rows:
        st.caption("No photos yet.")
    else:
        ph_rows.sort(key=lambda x: str((x or {}).get("created_at") or ""), reverse=True)
        cols = st.columns(min(4, max(1, len(ph_rows))))
        for i, pr in enumerate(ph_rows[:16]):
            pp = str((pr or {}).get("storage_path") or (pr or {}).get("file_url") or "").strip()
            pt = str((pr or {}).get("photo_type") or "").strip()
            with cols[i % len(cols)]:
                st.caption(html.escape(pt or "photo"))
                if pp:
                    url = _tph.sign_task_photo_url(pp, expires_in=1800) if not pp.startswith("http") else pp
                    if url:
                        try:
                            st.image(url, use_container_width=True)
                        except Exception:
                            st.caption("(preview)")
                else:
                    st.caption("—")

    with st.expander("Supervisor & assignment", expanded=False):
        if can_edit:
            with st.form(f"jdt_vd_sup_f_{job_id}_{tid}"):
                supw = st.text_input(
                    "Assigned supervisor",
                    value=str(task_row.get("assigned_supervisor_name") or ""),
                    key=f"jdt_vd_sup_{job_id}_{tid}",
                )
                if st.form_submit_button("Save supervisor"):
                    try:
                        upd(
                            "job_tasks",
                            {
                                "assigned_supervisor_name": " ".join(str(supw or "").split())[:200],
                                "updated_at": datetime.now(timezone.utc).isoformat(),
                            },
                            {"id": tid},
                        )
                        _bump_jdt_job_data_cache(job_id)
                        st.success("Saved.")
                    except Exception as exc:
                        st.error(str(exc))
        else:
            st.caption(str(task_row.get("assigned_supervisor_name") or "—"))

    if st.button("Close", use_container_width=True, key=f"jdt_vd_close_{job_id}_{tid}"):
        st.session_state.pop(f"jdt_vd_{job_id}", None)
        st.rerun()


@st.dialog("Delete this task?")
def _task_delete_confirm_dialog(
    *,
    job_id: str,
    tid: str,
    dlt: Callable[..., Any],
) -> None:
    st.caption("This removes the task from the job. You cannot undo this from the app.")
    c1, c2 = st.columns(2, gap="small")
    with c1:
        if st.button("Cancel", use_container_width=True, key=f"jdt_del_cancel_{job_id}_{tid}"):
            st.session_state.pop(f"jdt_del_dialog_{job_id}", None)
            st.rerun()
    with c2:
        if st.button("Delete", type="primary", use_container_width=True, key=f"jdt_del_go_{job_id}_{tid}"):
            try:
                dlt("job_tasks", {"id": tid})
            except Exception as exc:
                st.error(str(exc))
                return
            st.session_state.pop(f"jdt_del_dialog_{job_id}", None)
            st.session_state.pop(f"jdt_cam_dlg_{job_id}", None)
            st.session_state.pop(f"jdt_vd_{job_id}", None)
            st.session_state[f"jdt_task_del_ok_{job_id}"] = True
            _bump_jdt_job_data_cache(job_id)
            st.rerun()


def _inject_task_tab_add_form_css() -> None:
    key = "ips_job_task_add_form_css_v1"
    if st.session_state.get(key):
        return
    st.session_state[key] = True
    st.markdown(
        """
        <style>
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-add-task-anchor)
            div[data-testid="stHorizontalBlock"] {
            flex-wrap: wrap !important;
            gap: 0.65rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-add-task-anchor)
            div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
            flex: 1 1 calc(50% - 0.65rem) !important;
            max-width: calc(50% - 0.35rem) !important;
            min-width: min(280px, 100%) !important;
        }
        @media (max-width: 700px) {
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-add-task-anchor)
                div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
                flex: 1 1 100% !important;
                max-width: 100% !important;
                min-width: 0 !important;
                width: 100% !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _jdt_af_result_key(job_id: str) -> str:
    return f"jdt_af_result_{job_id}"


def _jdt_af_css_once() -> None:
    k = "ips_jdt_af_css_v1"
    if st.session_state.get(k):
        return
    st.session_state[k] = True
    st.markdown(
        """
        <style>
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-jdt-af-card) {
            background: #ffffff !important;
            border: 1px solid #d1d5db !important;
            border-radius: 12px !important;
            padding: 16px !important;
            margin-bottom: 0.75rem !important;
            box-sizing: border-box !important;
            max-width: 100% !important;
            overflow-x: hidden !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-jdt-af-card) button[kind] {
            min-height: 3rem !important;
            padding-top: 0.65rem !important;
            padding-bottom: 0.65rem !important;
            font-size: 1.05rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _af_should_apply_text(existing: str, proposed: str | None, overwrite: bool) -> bool:
    if proposed is None or not str(proposed).strip():
        return False
    if overwrite:
        return True
    return not str(existing or "").strip()


def _apply_autofill_to_add_task_widgets(job_id: str, parsed: dict[str, Any], *, overwrite: bool) -> None:
    """Write Add task widget session keys (must run before those widgets on next rerun)."""

    def gtn() -> str:
        v = st.session_state.get(f"jdt_add_tn_{job_id}")
        return str(v or "").strip() if v is not None else ""

    def gloc() -> str:
        v = st.session_state.get(f"jdt_add_loc_{job_id}")
        return str(v or "").strip() if v is not None else ""

    def giss() -> str:
        v = st.session_state.get(f"jdt_add_iss_{job_id}")
        return str(v or "").strip() if v is not None else ""

    def gact() -> str:
        v = st.session_state.get(f"jdt_add_act_{job_id}")
        return str(v or "").strip() if v is not None else ""

    tn = str(parsed.get("task_number") or "").strip()
    if _af_should_apply_text(gtn(), tn, overwrite):
        st.session_state[f"jdt_add_tn_{job_id}"] = tn[:200]

    pr = str(parsed.get("priority") or "").strip().lower()
    if pr in ("low", "normal", "high", "critical"):
        pr_touched = bool(st.session_state.get(f"jdt_add_pr_touched_{job_id}"))
        if overwrite or not pr_touched:
            st.session_state[f"jdt_add_pr_{job_id}"] = pr

    loc = str(parsed.get("location") or "").strip()
    if _af_should_apply_text(gloc(), loc, overwrite):
        st.session_state[f"jdt_add_loc_{job_id}"] = loc[:500]

    iss = str(parsed.get("issue") or "").strip()
    if _af_should_apply_text(giss(), iss, overwrite):
        st.session_state[f"jdt_add_iss_{job_id}"] = iss[:4000]

    act = str(parsed.get("action_required") or "").strip()
    if _af_should_apply_text(gact(), act, overwrite):
        st.session_state[f"jdt_add_act_{job_id}"] = act[:4000]

    pd = parsed.get("planned_date")
    if isinstance(pd, date):
        cur_pl = st.session_state.get(f"jdt_add_pl_{job_id}", date.today())
        pl_touched = bool(st.session_state.get(f"jdt_add_pl_touched_{job_id}"))
        if isinstance(cur_pl, date):
            if overwrite or (not pl_touched and cur_pl == date.today()):
                st.session_state[f"jdt_add_pl_{job_id}"] = pd


def _render_add_task_autofill_from_attachment(*, job_id: str, admin_read: bool) -> None:
    try:
        from app.services import job_reference_attachments as _jra_svc
        from app.services import task_attachment_autofill as _taf
    except ImportError:
        import services.job_reference_attachments as _jra_svc  # type: ignore
        import services.task_attachment_autofill as _taf  # type: ignore

    _jdt_af_css_once()
    rk = _jdt_af_result_key(job_id)
    toast_k = f"jdt_af_applied_{job_id}"
    if st.session_state.pop(toast_k, None):
        try:
            st.toast("Applied — review fields in **Add task**.")
        except Exception:
            st.success("Applied — review fields in **Add task**.")
    bucket = _jra_svc.reference_bucket()
    att_rows = _load_job_ref_attachments_cached(job_id, admin_read=admin_read)[:200]
    candidates = [
        r
        for r in att_rows
        if isinstance(r, dict) and _taf.is_autofill_supported_filename(str(r.get("file_name") or ""))
    ]
    id_to_row = {str(r.get("id")): r for r in candidates if str(r.get("id") or "").strip()}

    with st.container(border=True):
        st.markdown('<span class="ips-jdt-af-card"></span>', unsafe_allow_html=True)
        st.markdown("###### Auto fill from attachment")
        st.caption(
            "Pick a **saved reference** file or **upload** a PDF/image, then extract text to pre-fill **Add task** "
            "(best-effort; review before saving)."
        )
        ids = [str(r.get("id")) for r in candidates if str(r.get("id") or "").strip()]

        def _lbl(rid: str) -> str:
            if not rid:
                return "— Select saved reference —"
            row = id_to_row.get(rid) or {}
            return str(row.get("file_name") or rid)[:100]

        sel = st.selectbox(
            "Reference attachment",
            options=[""] + ids,
            format_func=_lbl,
            key=f"jdt_af_sel_{job_id}",
            label_visibility="visible",
        )
        up = st.file_uploader(
            "Or upload PDF / image (one-time, not saved as reference)",
            type=["jpg", "jpeg", "png", "webp", "pdf"],
            key=f"jdt_af_up_{job_id}",
            accept_multiple_files=False,
        )

        if st.button(
            "Auto Fill From Attachment",
            type="secondary",
            use_container_width=True,
            key=f"jdt_af_go_{job_id}",
        ):
            data: bytes | None = None
            fname = ""
            if up is not None:
                try:
                    data = up.getvalue()
                    fname = str(getattr(up, "name", "") or "upload")
                except Exception:
                    data = None
            elif str(sel or "").strip():
                row = id_to_row.get(str(sel).strip())
                if row:
                    data, fname = _taf.fetch_bytes_for_row(row, bucket=bucket)
            if not data:
                st.session_state[rk] = {
                    "ok": False,
                    "msg": "Choose a saved attachment or upload a file first.",
                }
                st.rerun()
            if not _taf.is_autofill_supported_filename(fname):
                st.session_state[rk] = {
                    "ok": False,
                    "msg": "Could not auto-fill from this attachment. Please enter task details manually.",
                }
                st.rerun()
            txt = _taf.extract_text_from_bytes(fname, data)
            if not str(txt or "").strip():
                st.session_state[rk] = {
                    "ok": False,
                    "msg": "Could not auto-fill from this attachment. Please enter task details manually.",
                }
                st.rerun()
            parsed = _taf.parse_hazard_sheet_text(txt)
            has_any = any(
                str(parsed.get(k) or "").strip()
                for k in ("task_number", "location", "issue", "action_required")
            ) or bool(parsed.get("priority")) or bool(parsed.get("planned_date"))
            if not has_any:
                st.session_state[rk] = {
                    "ok": False,
                    "msg": "Could not auto-fill from this attachment. Please enter task details manually.",
                }
                st.rerun()
            st.session_state[rk] = {"ok": True, "parsed": parsed}
            st.rerun()

    res = st.session_state.get(rk)
    if isinstance(res, dict):
        if not res.get("ok"):
            st.warning(str(res.get("msg") or "Could not auto-fill from this attachment."))
            if st.button("Dismiss", key=f"jdt_af_dismiss_{job_id}", use_container_width=True):
                st.session_state.pop(rk, None)
                st.rerun()
        else:
            parsed = dict(res.get("parsed") or {})
            with st.container(border=True):
                st.markdown('<span class="ips-jdt-af-card"></span>', unsafe_allow_html=True)
                pd = parsed.get("planned_date")
                pd_line = ""
                if isinstance(pd, date):
                    pd_line = f"- **Planned date:** {html.escape(pd.isoformat())}  \n"
                st.markdown(
                    "**Extracted preview**\n\n"
                    f"- **Task #:** {html.escape(str(parsed.get('task_number') or '—'))}  \n"
                    f"- **Priority:** {html.escape(str(parsed.get('priority') or '—'))}  \n"
                    f"{pd_line}"
                    f"- **Location:** {html.escape(str(parsed.get('location') or '—'))}  \n"
                    f"- **Issue:** {html.escape(str(parsed.get('issue') or '—'))}  \n"
                    f"- **Action required:** {html.escape(str(parsed.get('action_required') or '—'))}"
                )
                overwrite = st.checkbox(
                    "Replace fields I already filled",
                    value=False,
                    key=f"jdt_af_over_{job_id}",
                    help="When off, only empty Add task fields are updated.",
                )
                b1, b2 = st.columns(2, gap="small")
                with b1:
                    if st.button(
                        "Apply to Task Form",
                        type="primary",
                        use_container_width=True,
                        key=f"jdt_af_apply_{job_id}",
                    ):
                        _apply_autofill_to_add_task_widgets(job_id, parsed, overwrite=overwrite)
                        st.session_state.pop(rk, None)
                        st.session_state[f"jdt_af_applied_{job_id}"] = True
                        st.rerun()
                with b2:
                    if st.button("Cancel", type="secondary", use_container_width=True, key=f"jdt_af_cancel_{job_id}"):
                        st.session_state.pop(rk, None)
                        st.rerun()


def _fetch_tasks(job_id: str, *, admin: bool) -> list[dict[str, Any]]:
    return _load_job_tasks_cached(job_id, admin_read=admin)


def _fetch_plans_for_job(job_id: str, *, admin: bool) -> list[dict[str, Any]]:
    fn = fetch_by_match_admin if admin else fetch_by_match
    try:
        return list(fn("supervisor_daily_task_plans", {"job_id": str(job_id)}, limit=2000) or [])
    except Exception:
        return []


def _fetch_work_plan(job_id: str, work_date: str, *, admin: bool) -> dict[str, Any] | None:
    fn = fetch_by_match_admin if admin else fetch_by_match
    try:
        rows = fn(
            "job_daily_work_plans",
            {"job_id": str(job_id), "work_date": str(work_date)[:10]},
            limit=1,
        )
        return rows[0] if rows else None
    except Exception:
        return None


def _wrow(admin: bool) -> tuple[Callable, Callable, Callable]:
    if admin:
        return insert_row_admin, update_rows_admin, delete_rows_admin
    return insert_row, update_rows, delete_rows


_JDT_ADD_DLG_JOB_KEY = "_jdt_add_dialog_active_job"


def _jdt_clear_add_task_dialog() -> None:
    jid = str(st.session_state.pop(_JDT_ADD_DLG_JOB_KEY, "") or "").strip()
    if jid:
        st.session_state.pop(f"jdt_open_add_task_{jid}", None)


@st.dialog("Add task", width="large", on_dismiss=_jdt_clear_add_task_dialog)
def _task_add_dialog(*, job_id: str, admin_read: bool) -> None:
    ensure_modal_styles()
    modal_wide_marker()
    st.markdown("### Add task")
    ins, _upd, _dlt = _wrow(admin_read)
    _inject_task_tab_add_form_css()
    with st.container(border=True):
        _render_add_task_autofill_from_attachment(job_id=job_id, admin_read=admin_read)
        st.markdown('<span class="ips-job-add-task-anchor"></span>', unsafe_allow_html=True)
        with st.form(f"jdt_add_task_f_{job_id}", clear_on_submit=True):
            tn = st.text_input("Task #", key=f"jdt_add_tn_{job_id}")
            a1, a2 = st.columns(2, gap="small")
            with a1:
                pr = st.selectbox(
                    "Priority",
                    ("low", "normal", "high", "critical"),
                    index=1,
                    format_func=lambda x: x.title(),
                    key=f"jdt_add_pr_{job_id}",
                )
            with a2:
                pl = st.date_input(
                    "Planned date",
                    value=date.today(),
                    key=f"jdt_add_pl_{job_id}",
                )
            a3, a4 = st.columns(2, gap="small")
            with a3:
                loc = st.text_input("Location", key=f"jdt_add_loc_{job_id}")
            with a4:
                iss = st.text_input("Issue (short)", key=f"jdt_add_iss_{job_id}")
            act = st.text_input("Action required", key=f"jdt_add_act_{job_id}")
            submitted = st.form_submit_button("Create task", type="primary", use_container_width=True)

    if st.button("Cancel", type="secondary", use_container_width=True, key=f"jdt_add_dlg_cancel_{job_id}"):
        _jdt_clear_add_task_dialog()
        st.rerun()

    if submitted:
        iss_s = str(iss or "").strip()
        if not iss_s:
            st.error("Enter an issue description.")
            return
        try:
            ins(
                "job_tasks",
                {
                    "job_id": str(job_id),
                    "task_number": str(tn or "").strip()[:200],
                    "priority": pr,
                    "location": str(loc or "").strip()[:500],
                    "issue": iss_s[:4000],
                    "action_required": str(act or "").strip()[:4000],
                    "status": "not_started",
                    "planned_date": str(pl) if pl is not None else None,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            _bump_jdt_job_data_cache(job_id)
            _jdt_clear_add_task_dialog()
            st.success("Task added.")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))


def render_job_tasks_tab(
    *,
    job_id: str,
    job_label: str,
    can_edit_tasks: bool,
    admin_read: bool,
) -> None:
    inject_field_light_theme()
    if st.session_state.pop(f"jdt_task_del_ok_{job_id}", None):
        try:
            st.toast("Task deleted.")
        except Exception:
            st.success("Task deleted.")
    if st.session_state.pop(f"jdt_task_sv_ok_{job_id}", None):
        try:
            st.toast("Task updated.")
        except Exception:
            st.success("Task updated.")
    st.caption(
        "Jobs are containers — break work into **tasks**. "
        "Supervisors run status, photos, and end-of-day review in **Work & Plan (Supervisor)** (no separate report page)."
    )
    rows = _fetch_tasks(job_id, admin=admin_read)
    today_iso = date.today().isoformat()[:10]

    filt = st.selectbox(
        "Filter",
        (
            "All",
            "Planned today",
            "High priority",
            "Blocked",
            "Complete",
            "Electrical",
            "Duplicate",
        ),
        key=f"jdt_filt_{job_id}",
    )

    def _match(t: dict[str, Any]) -> bool:
        stt = str(t.get("status") or "").strip().lower()
        pr = str(t.get("priority") or "").strip().lower()
        pd = str(t.get("planned_date") or "")[:10]
        if filt == "Planned today":
            return pd == today_iso
        if filt == "High priority":
            return pr in ("high", "critical") and stt not in ("complete", "cancelled", "duplicate")
        if filt == "Blocked":
            return stt == "blocked"
        if filt == "Complete":
            return stt == "complete"
        if filt == "Electrical":
            return stt == "electrical"
        if filt == "Duplicate":
            return stt == "duplicate"
        return True

    visible = [t for t in rows if isinstance(t, dict) and _match(t)]
    if not rows:
        st.info("No tasks yet. Use **Add task** to create the first one.")
    elif not visible:
        st.caption("No tasks match this filter.")

    ins, upd, dlt = _wrow(admin_read)

    all_task_ids = {
        str(t.get("id") or "").strip()
        for t in rows
        if isinstance(t, dict) and str(t.get("id") or "").strip()
    }
    visible_ids = {
        str(t.get("id") or "").strip()
        for t in visible
        if isinstance(t, dict) and str(t.get("id") or "").strip()
    }
    for sk in (f"jdt_del_dialog_{job_id}", f"jdt_cam_dlg_{job_id}", f"jdt_vd_{job_id}"):
        tid0 = str(st.session_state.get(sk) or "").strip()
        if not tid0:
            continue
        if tid0 not in all_task_ids:
            st.session_state.pop(sk, None)
        elif visible and tid0 not in visible_ids:
            st.session_state.pop(sk, None)
        elif not visible:
            st.session_state.pop(sk, None)

    if st.session_state.get("show_reference"):
        rjb = str(st.session_state.get("reference_job_id") or "").strip()
        if rjb and rjb != str(job_id).strip():
            _clear_jdt_reference_overlay()
        else:
            tmk = str(st.session_state.get("reference_modal_task_id") or "").strip()
            if visible and tmk and tmk not in visible_ids:
                _clear_jdt_reference_overlay()

    if visible:
        _mob.inject_mobile_field_css()
        _jra_ui._inject_ref_attachment_css()
        _inject_task_card_row_css()
        _inject_jdt_field_tap_css()
        ref_bucket = _jra_svc.reference_bucket()
        att_rows_all = _ref_attach_rows_for_job(job_id, admin_read=admin_read)

        st.markdown('<span class="ips-jdt-field-zone"></span>', unsafe_allow_html=True)
        st.markdown("##### Tasks")
        st.caption(
            "Change **status** to save instantly. **📷** opens the camera (progress photos). "
            "Each card shows a **reference preview** on the right; **View details** for full files and photo history."
        )

        for t in visible:
            tid = str(t.get("id") or "").strip()
            if not tid:
                continue
            stt = str(t.get("status") or "not_started").strip().lower()
            if stt == "open":
                stt = "not_started"
            iss = str(t.get("issue") or "").strip()
            snip = (iss[:140] + "…") if len(iss) > 140 else iss
            loc = str(t.get("location") or "").strip() or "—"
            tno = html.escape(task_number_display(t))
            pr_badge = _priority_badge_html(t.get("priority"))
            opts = [s for s in TASK_STATUSES if s != "cancelled"]
            cur_sl = stt if stt in opts else "not_started"
            ix = opts.index(cur_sl)

            merged_refs = _jdt_merged_attachments_for_task(job_id, tid, att_rows_all)
            pref_row = _jdt_pick_primary_modal_reference_row(merged_refs)
            signed_pv, _pv_fn = (
                _jdt_sign_attachment_row(pref_row, bucket=ref_bucket)
                if isinstance(pref_row, dict)
                else ("", "")
            )
            _st_save = _make_jdt_status_save_cb(
                job_id,
                tid,
                admin_read=admin_read,
                upd=upd,
                can_edit_tasks=can_edit_tasks,
            )

            with st.container(border=True):
                expand_key = f"jdt_prev_expand_{job_id}_{tid}"
                is_expanded = bool(st.session_state.get(expand_key))
                c_main, c_prev = st.columns([0.57, 0.43], gap="medium")
                with c_main:
                    st.markdown(
                        '<span class="ips-jdt-task-card ips-jdt-split-main"></span>',
                        unsafe_allow_html=True,
                    )
                    fl = st.session_state.pop(f"jdt_st_flash_{job_id}_{tid}", None)
                    if fl:
                        st.warning(str(fl))
                    st.markdown(
                        '<div style="display:flex;flex-wrap:wrap;align-items:center;gap:0.5rem;margin:0 0 0.15rem 0;">'
                        f'<span style="font-size:1.28rem;font-weight:800;color:#111827;">{tno}</span>'
                        f"<span>{pr_badge}</span></div>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        '<p style="margin:0 0 0.35rem;font-size:1.02rem;font-weight:600;color:#111827;line-height:1.35;">'
                        f"{html.escape(snip or '—')}</p>",
                        unsafe_allow_html=True,
                    )
                    loc_show = str(loc).strip()
                    if loc_show and loc_show != "—":
                        st.markdown(
                            '<p style="margin:0 0 0.45rem;font-size:0.88rem;color:#6b7280;line-height:1.35;">'
                            f"<strong>Location</strong> {html.escape(loc_show)}</p>",
                            unsafe_allow_html=True,
                        )

                    cst, camc = st.columns([4.5, 1], gap="small")
                    with cst:
                        if can_edit_tasks:
                            st.selectbox(
                                "Status",
                                opts,
                                index=ix,
                                format_func=lambda s, _lb=_jdt_status_label: _lb(str(s)),
                                key=f"jdt_st_{job_id}_{tid}",
                                label_visibility="collapsed",
                                on_change=_st_save,
                            )
                            st.caption("Saves when changed")
                        else:
                            st.caption(_jdt_status_label(stt))
                    with camc:
                        if can_edit_tasks:
                            if st.button(
                                "📷",
                                type="primary",
                                key=f"jdt_cam_btn_{job_id}_{tid}",
                                use_container_width=True,
                            ):
                                st.session_state[f"jdt_cam_dlg_{job_id}"] = tid
                                st.rerun()
                        else:
                            st.caption("—")

                    bot_l, bot_r = st.columns(2, gap="small")
                    with bot_l:
                        if st.button(
                            "View details",
                            type="primary",
                            key=f"jdt_vd_btn_{job_id}_{tid}",
                            use_container_width=True,
                        ):
                            st.session_state[f"jdt_vd_{job_id}"] = tid
                            st.rerun()
                    with bot_r:
                        if can_edit_tasks and st.button(
                            "Delete",
                            type="secondary",
                            key=f"jdt_card_del_{job_id}_{tid}",
                            use_container_width=True,
                        ):
                            st.session_state[f"jdt_del_dialog_{job_id}"] = tid
                            st.rerun()

                    with st.expander("Location & notes", expanded=False):
                        st.markdown(
                            '<p style="margin:0.1rem 0;color:#374151;font-size:0.95rem;"><strong>Location</strong><br/>'
                            f"{html.escape(loc)}</p>",
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            '<p style="margin:0.35rem 0;color:#111827;font-size:0.95rem;"><strong>Issue</strong><br/>'
                            f"{html.escape(iss or '—')}</p>",
                            unsafe_allow_html=True,
                        )
                        if can_edit_tasks:
                            with st.form(f"jdt_notes_f_{job_id}_{tid}"):
                                nx = st.text_area(
                                    "Notes",
                                    value=str(t.get("notes") or ""),
                                    height=72,
                                    key=f"jdt_exp_notes_{job_id}_{tid}",
                                )
                                if st.form_submit_button("Save notes"):
                                    try:
                                        upd(
                                            "job_tasks",
                                            {
                                                "notes": str(nx or "").strip()[:4000],
                                                "updated_at": datetime.now(timezone.utc).isoformat(),
                                            },
                                            {"id": tid},
                                        )
                                        _bump_jdt_job_data_cache(job_id)
                                        try:
                                            st.toast("Notes saved")
                                        except Exception:
                                            pass
                                        st.rerun()
                                    except Exception as exc:
                                        st.error(str(exc))
                        else:
                            st.markdown(
                                '<p style="margin:0.35rem 0;color:#374151;font-size:0.92rem;"><strong>Notes</strong><br/>'
                                f"{html.escape(str(t.get('notes') or '—'))}</p>",
                                unsafe_allow_html=True,
                            )

                with c_prev:
                    st.markdown(
                        '<span class="ips-jdt-split-prev" aria-hidden="true"></span>',
                        unsafe_allow_html=True,
                    )
                    top_l, top_r = st.columns([3, 1], gap="small")
                    with top_l:
                        if isinstance(pref_row, dict) and signed_pv.strip():
                            if st.button(
                                "Collapse preview" if is_expanded else "Expand preview",
                                key=f"jdt_prev_tgl_{job_id}_{tid}",
                                type="secondary",
                                use_container_width=True,
                            ):
                                st.session_state[expand_key] = not is_expanded
                                if not is_expanded:
                                    st.session_state[f"jdt_ref_preview_loaded_{job_id}_{tid}"] = True
                                st.rerun()
                        else:
                            st.caption(" ")
                    with top_r:
                        if isinstance(pref_row, dict) and signed_pv.strip():
                            if st.button(
                                "⛶",
                                key=f"jdt_ref_expand_{job_id}_{tid}",
                                help="Open reference full screen",
                                use_container_width=True,
                            ):
                                st.session_state["reference_modal_task_id"] = tid
                                st.session_state["reference_job_id"] = str(job_id).strip()
                                st.session_state["show_reference"] = True
                                st.session_state["reference_url"] = signed_pv.strip()
                                st.rerun()

                    # Collapsed: defer heavy iframe until user clicks Load preview (or expands).
                    if not is_expanded:
                        _pv_loaded_key = f"jdt_ref_preview_loaded_{job_id}_{tid}"
                        if isinstance(pref_row, dict) and signed_pv.strip():
                            if not st.session_state.get(_pv_loaded_key):
                                st.caption("Preview not loaded (faster list).")
                                if st.button(
                                    "Load preview",
                                    key=f"jdt_load_pv_{job_id}_{tid}",
                                    use_container_width=True,
                                ):
                                    st.session_state[_pv_loaded_key] = True
                                    st.rerun()
                            else:
                                pv_html = _jdt_work_card_preview_html(signed_url=signed_pv.strip(), row=pref_row)
                                components.html(
                                    pv_html,
                                    height=_JDT_CARD_PREVIEW_COMPONENT_H,
                                    scrolling=False,
                                )
                        elif isinstance(pref_row, dict):
                            pv_html = _jdt_work_card_preview_unavailable_html()
                            components.html(
                                pv_html,
                                height=_JDT_CARD_PREVIEW_COMPONENT_H,
                                scrolling=False,
                            )
                        else:
                            pv_html = _jdt_work_card_preview_placeholder_html()
                            components.html(
                                pv_html,
                                height=_JDT_CARD_PREVIEW_COMPONENT_H,
                                scrolling=False,
                            )

                if is_expanded:
                    if isinstance(pref_row, dict) and signed_pv.strip():
                        pv_html_big = _jdt_work_card_preview_html(signed_url=signed_pv.strip(), row=pref_row)
                    elif isinstance(pref_row, dict):
                        pv_html_big = _jdt_work_card_preview_unavailable_html()
                    else:
                        pv_html_big = _jdt_work_card_preview_placeholder_html()
                    components.html(
                        pv_html_big,
                        height=_JDT_CARD_PREVIEW_COMPONENT_H,
                        scrolling=False,
                    )

        if st.session_state.get("show_reference"):
            _jdt_reference_preview_dialog(
                job_id=job_id,
                admin_read=admin_read,
                bucket=ref_bucket,
            )

        dlg_tid = str(st.session_state.get(f"jdt_del_dialog_{job_id}") or "").strip()
        cam_dlg = str(st.session_state.get(f"jdt_cam_dlg_{job_id}") or "").strip()
        vd = str(st.session_state.get(f"jdt_vd_{job_id}") or "").strip()
        if dlg_tid and can_edit_tasks:
            _task_delete_confirm_dialog(job_id=job_id, tid=dlg_tid, dlt=dlt)
        elif cam_dlg and can_edit_tasks:
            _task_camera_capture_dialog(job_id=job_id, tid=cam_dlg, admin_read=admin_read)
        elif vd:
            _jra_ui.run_reference_attachment_fullscreen_dialog_if_pending()
            tvd = next(
                (x for x in rows if isinstance(x, dict) and str(x.get("id") or "").strip() == vd),
                None,
            )
            if tvd:
                _task_view_details_dialog(
                    job_id=job_id,
                    tid=vd,
                    task_row=dict(tvd),
                    att_rows=att_rows_all,
                    bucket=ref_bucket,
                    can_edit=can_edit_tasks,
                    admin_read=admin_read,
                    upd=upd,
                    dlt=dlt,
                    can_manage_attachments=str(_jra_role() or "").strip().lower() in {"admin", "manager"},
                )

    st.divider()
    with st.expander("Job reference attachments", expanded=False):
        _jra_ui.render_job_reference_attachments_panel(
            job_id=job_id,
            tasks=list(rows or []),
            admin_read=admin_read,
            can_manage=str(_jra_role() or "").strip().lower() in {"admin", "manager"},
        )

    st.divider()
    with st.expander("All task photos (review)", expanded=False):
        render_job_photos_tab(job_id=job_id, admin_read=admin_read)

    if can_edit_tasks:
        c1, c2 = st.columns([1, 1.2], gap="small")
        with c1:
            if st.button(
                "Add task",
                type="primary",
                use_container_width=True,
                key=f"jdt_btn_open_add_{job_id}",
            ):
                jid = str(job_id).strip()
                st.session_state[_JDT_ADD_DLG_JOB_KEY] = jid
                st.session_state[f"jdt_open_add_task_{jid}"] = True
                st.rerun()
        with c2:
            st.caption("Opens a form to add a task, optional **auto fill from attachment**, then **Create task**.")

    if can_edit_tasks and st.session_state.get(f"jdt_open_add_task_{str(job_id).strip()}"):
        _task_add_dialog(job_id=str(job_id).strip(), admin_read=admin_read)


def render_job_daily_plan_tab(
    *,
    job_id: str,
    can_edit_tasks: bool,
    admin_read: bool,
) -> None:
    """Persist job day plans (supervisor_daily_task_plans, job_daily_work_plans). Not shown on Job Detail — use Work & Plan (Supervisor)."""
    st.caption(
        "Pick **today’s tasks**, assign the lead supervisor, and capture shift context. "
        "Supervisors execute and close the day in **Work & Plan (Supervisor)** — one screen."
    )
    wdate = st.date_input("Work date", value=date.today(), key=f"jdp_date_{job_id}")
    w_iso = wdate.isoformat()[:10]
    rows = _fetch_tasks(job_id, admin=admin_read)
    ids = [str(t.get("id") or "") for t in rows if str(t.get("id") or "").strip()]
    plans = _fetch_plans_for_job(job_id, admin=admin_read)
    planned_ids = {str(p.get("task_id")) for p in plans if str(p.get("work_date") or "")[:10] == w_iso}
    default = [i for i in ids if i in planned_ids]

    def _fmt(tid: str) -> str:
        tt = next((x for x in rows if str(x.get("id")) == tid), {})
        iss = str(tt.get("issue") or "")[:40]
        return f"{task_number_display(tt)} · {iss}"

    pick = st.multiselect(
        "Tasks for this day",
        options=ids,
        default=[i for i in default if i in ids],
        format_func=_fmt,
        key=f"jdp_pick_{job_id}_{w_iso}",
    )
    sup = st.text_input("Supervisor (lead)", key=f"jdp_sup_{job_id}_{w_iso}", placeholder="Field supervisor name")

    wp = _fetch_work_plan(job_id, w_iso, admin=admin_read) or {}
    crew = st.text_area("Crew plan", value=str(wp.get("crew_plan") or ""), height=68, key=f"jdp_crew_{job_id}")
    first = st.text_input("First task at start of shift", value=str(wp.get("first_task") or ""), key=f"jdp_first_{job_id}")
    tools = st.text_area("Tools / material needed", value=str(wp.get("tools_material") or ""), height=68, key=f"jdp_tools_{job_id}")
    block = st.text_area("Known blockers", value=str(wp.get("known_blockers") or ""), height=56, key=f"jdp_blk_{job_id}")
    risk = st.text_input("Biggest risk", value=str(wp.get("biggest_risk") or ""), key=f"jdp_risk_{job_id}")

    if not can_edit_tasks:
        st.info("You can view the plan; only field leads and office roles can edit.")
        return

    ins, upd, dlt = _wrow(admin_read)
    if st.button("Save daily plan", type="primary", key=f"jdp_save_{job_id}_{w_iso}"):
        if not str(sup or "").strip():
            st.error("Enter supervisor name.")
            st.stop()
        try:
            dlt("supervisor_daily_task_plans", {"job_id": str(job_id), "work_date": w_iso})
            sn = " ".join(str(sup or "").strip().split())[:200]
            for i, tid in enumerate(pick):
                if tid:
                    row_payload: dict[str, Any] = {
                        "job_id": str(job_id),
                        "work_date": w_iso,
                        "supervisor_name": sn,
                        "task_id": tid,
                        "sort_order": int(i),
                    }
                    try:
                        ins("supervisor_daily_task_plans", row_payload)
                    except Exception:
                        row_payload.pop("sort_order", None)
                        ins("supervisor_daily_task_plans", row_payload)
            summary = {
                "supervisor_name": sn,
                "crew_plan": str(crew or "").strip()[:8000],
                "first_task": str(first or "").strip()[:2000],
                "tools_material": str(tools or "").strip()[:8000],
                "known_blockers": str(block or "").strip()[:8000],
                "biggest_risk": str(risk or "").strip()[:2000],
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            existing = _fetch_work_plan(job_id, w_iso, admin=admin_read)
            if existing:
                upd("job_daily_work_plans", summary, {"job_id": str(job_id), "work_date": w_iso})
            else:
                ins(
                    "job_daily_work_plans",
                    {
                        "job_id": str(job_id),
                        "work_date": w_iso,
                        **summary,
                    },
                )
            st.success("Saved.")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))


def render_job_photos_tab(*, job_id: str, admin_read: bool) -> None:
    """Read-only gallery of before / progress / after per task (also embedded under Job Detail → Tasks)."""
    rows = _fetch_tasks(job_id, admin=admin_read)
    st.caption(
        "Before, progress, and after from each task. "
        "Add or replace photos with **Open / Edit** on the task above, or in **Work & Plan (Supervisor)**."
    )
    by_tid: dict[str, list[dict[str, Any]]] = {}
    for t in rows:
        if not isinstance(t, dict):
            continue
        tid = str(t.get("id") or "").strip()
        if not tid:
            continue
        try:
            ph = _tph.fetch_task_photos(tid, admin=admin_read)
        except Exception:
            ph = []
        by_tid[tid] = list(ph or [])

    cmp_opts: list[tuple[str, str, str, str]] = []
    for t in rows:
        if not isinstance(t, dict):
            continue
        tid = str(t.get("id") or "").strip()
        if not tid:
            continue
        b, a = _tp_svc.before_after_storage_paths(t, by_tid.get(tid), task_id=tid)
        if b and a:
            lab = task_number_display(t)
            cmp_opts.append((lab, tid, b, a))

    if cmp_opts:
        with st.expander("Before / after comparison", expanded=False):
            ix = st.selectbox(
                "Task",
                options=range(len(cmp_opts)),
                format_func=lambda i: cmp_opts[i][0],
                key=f"jbapho_cmp_{job_id}",
            )
            lab, _tid, bp, ap = cmp_opts[int(ix)]
            st.caption(lab)
            u1, u2 = st.columns(2, gap="small")
            bu = _tph.sign_task_photo_url(bp, expires_in=2400) if bp and not bp.startswith("http") else bp
            au = _tph.sign_task_photo_url(ap, expires_in=2400) if ap and not ap.startswith("http") else ap
            with u1:
                st.caption("Before")
                if bu:
                    try:
                        st.image(bu, use_container_width=True)
                    except Exception:
                        st.caption("(could not render)")
            with u2:
                st.caption("After")
                if au:
                    try:
                        st.image(au, use_container_width=True)
                    except Exception:
                        st.caption("(could not render)")

    tiles: list[tuple[dict[str, Any], str, str, list[dict[str, Any]]]] = []
    for t in rows:
        if not isinstance(t, dict):
            continue
        tid = str(t.get("id") or "").strip()
        if not tid:
            continue
        phs = by_tid.get(tid) or []
        latest = _tp_svc.latest_photo_path_by_type(phs, task_id=tid)
        b = str(latest.get(_tp_svc.PHOTO_TYPES_BEFORE) or t.get("before_photo_url") or "").strip()
        a = str(latest.get(_tp_svc.PHOTO_TYPES_AFTER) or t.get("after_photo_url") or "").strip()
        prog = [r for r in phs if str((r or {}).get("photo_type") or "").lower() == _tp_svc.PHOTO_TYPES_PROGRESS]
        if b or a or prog:
            tiles.append((t, b, a, prog))
    if not tiles:
        st.info("No task photos yet. Use **Open / Edit** on a task above or **Work & Plan (Supervisor)**.")
        return
    for t, b, a, prog in tiles[:50]:
        label = task_number_display(t)
        st.markdown(f"**{label}**")
        c1, c2 = st.columns(2, gap="small")
        with c1:
            st.caption("Before")
            if b:
                url = _tph.sign_task_photo_url(b, expires_in=1800) if not b.startswith("http") else b
                if url:
                    try:
                        st.image(url, use_container_width=True)
                    except Exception:
                        st.caption("(could not render image)")
            else:
                st.caption("—")
        with c2:
            st.caption("After")
            if a:
                url = _tph.sign_task_photo_url(a, expires_in=1800) if not a.startswith("http") else a
                if url:
                    try:
                        st.image(url, use_container_width=True)
                    except Exception:
                        st.caption("(could not render image)")
            else:
                st.caption("—")
        if prog:
            st.caption("Progress")
            pc = st.columns(min(4, len(prog[:8])))
            for i, pr in enumerate(prog[:8]):
                pp = str((pr or {}).get("storage_path") or "").strip()
                with pc[i % len(pc)]:
                    if pp:
                        url = _tph.sign_task_photo_url(pp, expires_in=1800) if not pp.startswith("http") else pp
                        if url:
                            try:
                                st.image(url, use_container_width=True)
                            except Exception:
                                st.caption("—")


def render_job_cost_tab(*, job_id: str, job_row: dict[str, Any]) -> None:
    label = str(_job_display_label(job_row.get("job_number"), job_row.get("job_name"))).strip() or "Job"
    st.markdown(f"**{label}**")
    st.caption("Labor, materials, and equipment are tracked on **Job Costing**.")
    if st.button("Open Job Costing", type="primary", key=f"jcost_open_{job_id}"):
        st.session_state["jc_focus_job_id"] = str(job_id)
        st.session_state[IPS_NAV_PENDING_KEY] = "Job Costing"
        st.rerun()
