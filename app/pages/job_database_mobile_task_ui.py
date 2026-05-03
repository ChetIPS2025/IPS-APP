"""Mobile-first task detail form (field / phone)."""

from __future__ import annotations

import html
from datetime import date, datetime, timezone
from typing import Any, Callable

import streamlit as st

try:
    from auth import current_profile
except ImportError:
    try:
        from app.auth import current_profile
    except ImportError:

        def current_profile() -> dict[str, Any]:  # type: ignore[misc]
            return {}

try:
    from app.services import task_photos as tp
except ImportError:
    import services.task_photos as tp  # type: ignore

try:
    from app.services.task_display import task_number_display
except ImportError:
    from services.task_display import task_number_display  # type: ignore

try:
    from app.services.supervisor_planning import TASK_STATUSES
except ImportError:
    from services.supervisor_planning import TASK_STATUSES  # type: ignore

try:
    from app.pages import job_database_task_photos_ui as tph
except ImportError:
    import pages.job_database_task_photos_ui as tph  # type: ignore

try:
    from app.ui.field_light_theme import inject_field_light_theme
except ImportError:
    from ui.field_light_theme import inject_field_light_theme  # type: ignore

import re

_DETAIL_STATUS_LABELS: dict[str, str] = {
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

_REVIEW_LABELS: dict[str, str] = {
    "complete": "Complete",
    "partial": "Partial",
    "blocked": "Blocked",
    "not_started": "Not started",
    "duplicate": "Duplicate",
    "electrical": "Electrical / trade",
    "waiting_on_customer": "Waiting on customer",
}

_TASK_STATUS_HEX: dict[str, str] = {
    "complete": "#16a34a",
    "completed": "#16a34a",
    "in_progress": "#f59e0b",
    "partial": "#f59e0b",
    "blocked": "#dc2626",
    "not_started": "#64748b",
    "open": "#64748b",
    "duplicate": "#64748b",
    "electrical": "#7c3aed",
    "waiting_on_customer": "#0891b2",
    "cancelled": "#64748b",
}


def _priority_badge_html(priority: Any) -> str:
    pr = str(priority or "normal").strip().lower()
    if pr not in ("low", "normal", "high", "critical"):
        pr = "normal"
    label = pr.title()
    return f'<span class="ips-priority-badge {html.escape(pr)}">{html.escape(label)}</span>'


def _status_badge_html(status: str) -> str:
    slug = str(status or "not_started").strip().lower()
    if slug == "open":
        slug = "not_started"
    label = _DETAIL_STATUS_LABELS.get(slug) or _REVIEW_LABELS.get(slug) or slug.replace("_", " ").title()
    safe_slug = re.sub(r"[^a-z0-9_]+", "_", slug)[:40]
    col = _TASK_STATUS_HEX.get(slug, "#64748b")
    return (
        f'<span class="ips-status-badge" style="--ips-status-color:{col};" '
        f'data-ips-status="{safe_slug}">{label}</span>'
    )


def inject_mobile_field_css() -> None:
    inject_field_light_theme()
    st.markdown(
        """
        <style>
        .block-container { padding-top: 0.75rem !important; }
        .ips-task-card-title {
            color: #0f172a;
            font-size: 1.35rem;
            font-weight: 700;
            line-height: 1.25;
            margin: 0 0 0.35rem;
            overflow-wrap: anywhere;
        }
        .ips-task-card-badges {
            display: flex;
            flex-wrap: wrap;
            gap: 0.35rem;
            align-items: center;
            margin: 0.25rem 0 0.5rem;
        }
        .ips-task-card-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.35rem 0.8rem;
            margin: 0.45rem 0;
        }
        .ips-task-card-grid span {
            color: #475569;
            display: block;
            font-size: 0.85rem;
            line-height: 1.35;
            overflow-wrap: anywhere;
        }
        .ips-task-card-grid strong {
            color: #0f172a;
            font-weight: 650;
        }
        .ips-task-issue {
            color: #0f172a;
            font-size: 0.94rem;
            line-height: 1.45;
            margin: 0.45rem 0;
            overflow-wrap: anywhere;
        }
        .ips-review-required {
            color: #dc2626;
            font-size: 0.9rem;
            font-weight: 650;
            margin: 0.35rem 0;
        }
        .ips-status-badge {
            align-items: center;
            background: color-mix(in srgb, var(--ips-status-color) 12%, white);
            border: 1px solid color-mix(in srgb, var(--ips-status-color) 38%, white);
            border-radius: 999px;
            color: var(--ips-status-color);
            display: inline-flex;
            font-size: 0.78rem;
            font-weight: 700;
            line-height: 1;
            margin: 0.15rem 0.35rem 0.15rem 0;
            padding: 0.35rem 0.55rem;
            white-space: nowrap;
        }
        .ips-priority-badge {
            border-radius: 999px;
            border: 1px solid #d1d5db;
            display: inline-flex;
            font-size: 0.76rem;
            font-weight: 700;
            line-height: 1;
            margin: 0.15rem 0.35rem 0.15rem 0;
            padding: 0.3rem 0.5rem;
            white-space: nowrap;
        }
        .ips-priority-badge.critical { color: #b91c1c; background: #fef2f2; border-color: #fecaca; }
        .ips-priority-badge.high { color: #c2410c; background: #fff7ed; border-color: #fed7aa; }
        .ips-priority-badge.normal { color: #1d4ed8; background: #eff6ff; border-color: #bfdbfe; }
        .ips-priority-badge.low { color: #4b5563; background: #f9fafb; border-color: #e5e7eb; }
        @media (max-width: 640px) {
            .ips-task-card-grid { grid-template-columns: 1fr; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _thumb(path: str, *, key: str, width: int = 200) -> None:
    p = str(path or "").strip()
    if not p:
        return
    url = tph.sign_task_photo_url(p, expires_in=2400) if not p.startswith("http") else p
    if url:
        try:
            st.image(url, width=width)
        except Exception:
            st.caption("Preview unavailable")


def _photo_meta_caption(row: dict[str, Any] | None) -> str:
    if not row or not isinstance(row, dict):
        return ""
    ts = str(row.get("created_at") or "").strip()
    if "T" in ts:
        ts = ts.replace("T", " ")[:19]
    elif len(ts) >= 16:
        ts = ts[:16]
    who = str(row.get("uploaded_by") or row.get("captured_by_name") or "").strip()
    if ts and who:
        return f"{ts} UTC · {who}"
    if who:
        return who
    if ts:
        return f"{ts} UTC"
    return ""


def render_mobile_task_detail_form(
    *,
    task_row: dict[str, Any],
    task_id: str,
    can_edit: bool,
    admin_read: bool,
    upd: Callable[..., Any],
) -> None:
    """Task summary, status, notes, Save Task Update; photos via before/progress/after strip."""
    inject_mobile_field_css()
    tid = str(task_id).strip()
    prof = current_profile()
    who = str(prof.get("full_name") or prof.get("email") or "").strip() or "—"

    with st.container(border=True):
        cur_st = str(task_row.get("status") or "not_started").strip().lower()
        if cur_st == "open":
            cur_st = "not_started"
        loc = str(task_row.get("location") or "").strip()
        iss = str(task_row.get("issue") or "").strip()
        tno = html.escape(task_number_display(task_row))
        st.markdown(
            f'<p class="ips-task-card-title">{tno}</p>'
            f'<div class="ips-task-card-badges">'
            f"{_priority_badge_html(task_row.get('priority'))}{_status_badge_html(cur_st)}</div>"
            f'<p style="margin:0.2rem 0;color:#475569;font-size:0.88rem;"><strong>Location</strong> '
            f"{html.escape(loc or '—')}</p>",
            unsafe_allow_html=True,
        )
        if iss:
            st.markdown(
                f'<p class="ips-task-issue">{str(iss[:2000] + ("…" if len(iss) > 2000 else ""))}</p>',
                unsafe_allow_html=True,
            )
        arq = str(task_row.get("action_required") or "").strip()
        if arq:
            st.caption("**Action required**")
            st.write(arq[:2000] + ("…" if len(arq) > 2000 else ""))

        opts = [s for s in TASK_STATUSES if s != "cancelled"]
        ix = opts.index(cur_st) if cur_st in opts else 0
        status = st.selectbox(
            "Status",
            opts,
            index=ix,
            format_func=lambda s: _DETAIL_STATUS_LABELS.get(str(s).lower(), str(s).replace("_", " ").title()),
            key=f"mt_detail_st_{tid}",
            disabled=not can_edit,
        )

        notes = st.text_area(
            "Notes (optional)",
            value=str(task_row.get("notes") or ""),
            height=88,
            key=f"mt_notes_{tid}",
            disabled=not can_edit,
        )

        if str(status).strip().lower() == "complete":
            st.markdown(
                '<p class="ips-review-required">After photo required to complete task.</p>',
                unsafe_allow_html=True,
            )
        st.caption(f"Signed in as **{who}** · server UTC on save.")

        if can_edit and st.button("Save Task Update", type="primary", use_container_width=True, key=f"mt_save_{tid}"):
            ns = str(status).strip().lower()
            rows_all = tph.fetch_task_photos(tid, admin=admin_read)
            by_tp = tp.photos_by_task_id(rows_all)
            if ns == "complete" and not tp.task_has_after_photo(tid, task_row, by_tp):
                st.error("After photo required to complete task.")
                st.stop()
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
                st.success("Saved.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    st.markdown("###### Photos")
    st.caption("Before, progress, and after — **Take photo** / **Upload photo**, thumbnails, replace or remove per section.")
    if can_edit:
        try:
            tph.render_task_photo_strip(
                task_id=tid, task_row=task_row, can_edit=True, admin_read=admin_read
            )
        except Exception as exc:
            st.caption(f"Photos unavailable ({exc}). Run **sql/053_task_photos.sql** and create Storage bucket **task-photos**.")
    else:
        rows_all = tph.fetch_task_photos(tid, admin=admin_read)
        latest = tp.latest_photo_path_by_type(rows_all, task_id=tid)
        for label, pt in (
            ("Before", tp.PHOTO_TYPES_BEFORE),
            ("After", tp.PHOTO_TYPES_AFTER),
        ):
            pth = str(latest.get(pt) or "").strip()
            st.caption(label)
            if pth:
                _thumb(pth, key=f"mt_ro_{tid}_{pt}", width=160)
            else:
                st.caption("—")
