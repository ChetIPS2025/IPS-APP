"""Mobile-first task detail and compact daily review rows (field / phone)."""

from __future__ import annotations

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
    from app.services.supervisor_planning import TASK_STATUSES, delay_reason_label
except ImportError:
    from services.supervisor_planning import TASK_STATUSES, delay_reason_label  # type: ignore

try:
    from app.pages import job_database_task_photos_ui as tph
except ImportError:
    import pages.job_database_task_photos_ui as tph  # type: ignore

try:
    from app.ui.field_light_theme import inject_field_light_theme
except ImportError:
    from ui.field_light_theme import inject_field_light_theme  # type: ignore

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

_REVIEW_SLUGS = (
    "complete",
    "partial",
    "blocked",
    "not_started",
    "duplicate",
    "electrical",
    "waiting_on_customer",
)
_REVIEW_LABELS: dict[str, str] = {
    "complete": "Complete",
    "partial": "Partial",
    "blocked": "Blocked",
    "not_started": "Not started",
    "duplicate": "Duplicate",
    "electrical": "Electrical / trade",
    "waiting_on_customer": "Waiting on customer",
}

_DELAY_REASONS = (
    "none",
    "material",
    "tools",
    "direction",
    "rework",
    "customer",
    "safety",
    "equipment",
    "weather",
    "other",
)


def _status_badge_html(status: str) -> str:
    slug = str(status or "not_started").strip().lower()
    if slug == "open":
        slug = "not_started"
    label = _DETAIL_STATUS_LABELS.get(slug) or _REVIEW_LABELS.get(slug) or slug.replace("_", " ").title()
    return f'<span class="ips-status-badge ips-status-{slug}">{label}</span>'


def inject_mobile_field_css() -> None:
    inject_field_light_theme()
    st.markdown(
        """
        <style>
        .block-container { padding-top: 0.75rem !important; }
        .ips-task-card-title {
            color: #0f172a;
            font-size: 1rem;
            font-weight: 700;
            line-height: 1.3;
            margin: 0 0 0.35rem;
            overflow-wrap: anywhere;
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
        sup = str(task_row.get("assigned_supervisor_name") or "").strip()
        planned = str(task_row.get("planned_date") or "").strip()[:10]
        st.markdown(
            f'<p class="ips-task-card-title">'
            f'Task {str(task_row.get("task_number") or "—").strip()} / '
            f'Hazard {str(task_row.get("hazard_number") or "—").strip()} '
            f'{_status_badge_html(cur_st)}</p>'
            f'<div class="ips-task-card-grid">'
            f'<span><strong>Priority</strong> {str(task_row.get("priority") or "—").strip().title()}</span>'
            f'<span><strong>Location</strong> {loc or "—"}</span>'
            f'<span><strong>Supervisor</strong> {sup or "—"}</span>'
            f'<span><strong>Planned</strong> {planned or "—"}</span>'
            f"</div>",
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


def render_daily_review_row_mobile(
    *,
    job_id: str,
    r_iso: str,
    task_row: dict[str, Any],
    prior: dict[str, Any],
    sup_day: str,
    can_edit: bool,
    admin_read: bool,
    ins: Callable[..., Any],
    upd: Callable[..., Any],
) -> None:
    """One compact row: title, status + photo popover, optional delay expander, notes, Save."""
    tid = str(task_row.get("id") or "").strip()
    if not tid:
        return
    jk = str(job_id).replace("-", "")[:12]
    iss = str(task_row.get("issue") or "")[:56]
    cur_st = str(prior.get("status_after") or task_row.get("status") or "not_started").strip().lower()
    if cur_st not in _REVIEW_SLUGS:
        cur_st = "not_started"

    with st.container(border=True):
        st.markdown(
            f'<p class="ips-task-card-title">{task_row.get("task_number") or "—"} / '
            f'{task_row.get("hazard_number") or "—"} {_status_badge_html(cur_st)}</p>'
            f'<p class="ips-task-issue">{iss or "—"}</p>',
            unsafe_allow_html=True,
        )

        c1, c2 = st.columns([1.35, 1], gap="small")
        with c1:
            new_status = st.selectbox(
                "Status",
                list(_REVIEW_SLUGS),
                index=list(_REVIEW_SLUGS).index(cur_st),
                format_func=lambda s: _REVIEW_LABELS.get(s, s),
                key=f"mjdr_{jk}_st_{tid}_{r_iso}",
                disabled=not can_edit,
            )
            if str(new_status).strip().lower() == "complete":
                st.markdown(
                    '<p class="ips-review-required">After photo required to complete task.</p>',
                    unsafe_allow_html=True,
                )
        with c2:
            if can_edit:
                with st.popover("After photo", use_container_width=True):
                    st.caption("Take Photo")
                    pcam = st.camera_input("qcam", key=f"mjdr_{jk}_pc_{tid}_{r_iso}", label_visibility="collapsed")
                    st.caption("Upload Photo")
                    pup = st.file_uploader("qup", type=["jpg", "jpeg", "png", "webp"], key=f"mjdr_{jk}_pu_{tid}_{r_iso}", label_visibility="collapsed")
                    if st.button("Save photo", key=f"mjdr_{jk}_psv_{tid}_{r_iso}", use_container_width=True):
                        raw: bytes | None = None
                        fn = "after.jpg"
                        if pcam is not None:
                            raw = pcam.getvalue()
                            fn = "camera.jpg"
                        elif pup is not None:
                            raw = pup.getvalue()
                            fn = str(getattr(pup, "name", "") or "after.jpg")
                        if not raw:
                            st.warning("Choose a photo first.")
                            st.stop()
                        try:
                            path = tph.save_task_after_photo_bytes(task_id=tid, raw=raw, fname=fn, admin_read=admin_read)
                            if path and prior:
                                try:
                                    upd(
                                        "job_task_daily_reviews",
                                        {"after_photo_url": path[:2000]},
                                        {"task_id": tid, "review_date": r_iso},
                                    )
                                except Exception:
                                    pass
                            st.success("Photo saved.")
                            st.rerun()
                        except Exception as exc:
                            st.error(str(exc))
            else:
                st.caption("—")

        delay = str(prior.get("delay_reason") or "none").strip().lower()
        notes_val = str(prior.get("notes") or "")
        if can_edit:
            with st.expander("Delay / details", expanded=False):
                dr_cur = str(prior.get("delay_reason") or "none").strip().lower()
                dr_ix = _DELAY_REASONS.index(dr_cur) if dr_cur in _DELAY_REASONS else 0
                delay = st.selectbox(
                    "Delay",
                    _DELAY_REASONS,
                    index=dr_ix,
                    format_func=lambda x: delay_reason_label(x),
                    key=f"mjdr_{jk}_dr_{tid}_{r_iso}",
                    disabled=False,
                )
                notes_val = st.text_area(
                    "Notes",
                    value=notes_val,
                    height=64,
                    key=f"mjdr_{jk}_nt_{tid}_{r_iso}",
                    disabled=False,
                )

        if not can_edit:
            return

        if st.button("Save row", key=f"mjdr_{jk}_sv_{tid}_{r_iso}", use_container_width=True):
            if not str(sup_day or "").strip():
                st.error("Enter supervisor sign-off at the top.")
                st.stop()
            ns = str(new_status).strip().lower()
            if ns == "complete" and not tph.task_has_after_for_validation(
                task_id=tid,
                task_row=task_row,
                prior_review=prior,
                pending_upload_bytes=None,
                admin_read=admin_read,
            ):
                st.error("After photo required to complete task.")
                st.stop()
            photo_path = str(prior.get("after_photo_url") or "").strip()
            try:
                payload_rev = {
                    "supervisor_name": " ".join(str(sup_day or "").strip().split())[:200],
                    "status_after": ns,
                    "delay_reason": str(delay or "none").strip().lower(),
                    "notes": str(notes_val or "").strip()[:4000],
                    "after_photo_url": photo_path[:2000],
                }
                if prior:
                    upd("job_task_daily_reviews", payload_rev, {"task_id": tid, "review_date": r_iso})
                else:
                    ins(
                        "job_task_daily_reviews",
                        {"task_id": tid, "review_date": r_iso, **payload_rev},
                    )
                task_upd: dict[str, Any] = {
                    "status": ns,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
                if ns == "complete":
                    task_upd["completed_date"] = r_iso
                else:
                    task_upd["completed_date"] = None
                if photo_path:
                    task_upd["after_photo_url"] = photo_path[:2000]
                upd("job_tasks", task_upd, {"id": tid})
                st.success("Saved.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
