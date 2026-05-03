"""Reference attachments: Job Detail / Tasks (PM) and Work & Plan (supervisor read)."""

from __future__ import annotations

import html
from datetime import datetime, timezone
from typing import Any

import streamlit as st

try:
    from auth import current_profile
except ImportError:
    from app.auth import current_profile  # type: ignore

try:
    from app.db import (
        create_signed_url,
        delete_rows,
        delete_rows_admin,
        fetch_by_match,
        fetch_by_match_admin,
        insert_row,
        insert_row_admin,
        upload_bytes_admin,
        delete_storage_object_admin,
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
        upload_bytes_admin,
        delete_storage_object_admin,
    )

try:
    from app.services import job_reference_attachments as jra
except ImportError:
    import services.job_reference_attachments as jra  # type: ignore

try:
    from app.services.task_display import task_number_display
except ImportError:
    from services.task_display import task_number_display  # type: ignore

_CSS_KEY = "ips_job_reference_attachments_css_v1"


def _inject_ref_attachment_css() -> None:
    if st.session_state.get(_CSS_KEY):
        return
    st.session_state[_CSS_KEY] = True
    st.markdown(
        """
        <style>
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-ref-attach-card) {
            background: #ffffff !important;
            border: 1px solid #d1d5db !important;
            border-radius: 12px !important;
            padding: 0.65rem 0.75rem !important;
            margin-bottom: 0.55rem !important;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05) !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-ref-attach-card) p {
            color: #111827 !important;
            margin: 0.1rem 0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _fetch_rows(job_id: str, *, admin_read: bool) -> list[dict[str, Any]]:
    fn = fetch_by_match_admin if admin_read else fetch_by_match
    try:
        return list(
            fn(
                "job_reference_attachments",
                {"job_id": str(job_id).strip()},
                limit=300,
            )
            or []
        )
    except Exception:
        return []


def _ins_del(admin_read: bool) -> tuple[Any, Any]:
    if admin_read:
        return insert_row_admin, delete_rows_admin
    return insert_row, delete_rows


def _icon_for_filename(name: str) -> str:
    ext = jra.normalize_extension(name)
    if ext in {"jpg", "jpeg", "png", "webp"}:
        return "🖼️"
    if ext == "pdf":
        return "📄"
    if ext == "docx":
        return "📝"
    if ext == "xlsx":
        return "📊"
    return "📎"


def _fmt_dt(val: Any) -> str:
    s = str(val or "").strip()
    if not s:
        return "—"
    try:
        if "T" in s:
            return s[:16].replace("T", " ")
        return s[:16]
    except Exception:
        return s[:32]


def _task_label(t: dict[str, Any]) -> str:
    tid = str(t.get("id") or "")[:8]
    return f"{task_number_display(t)} ({tid}…)"


def render_job_reference_attachments_panel(
    *,
    job_id: str,
    tasks: list[dict[str, Any]],
    admin_read: bool,
    can_manage: bool,
) -> None:
    """PM/admin: upload + list + delete. Others: view/download only."""
    _inject_ref_attachment_css()
    st.markdown("##### Reference Attachments")
    st.caption(
        "PM / admin: upload drawings, PDFs, photos, or spreadsheets for the **whole job** or a **specific task**. "
        "Supervisors see these in **Work & Plan** for assigned work."
    )

    rows = sorted(_fetch_rows(job_id, admin_read=admin_read), key=lambda r: str(r.get("created_at") or ""), reverse=True)

    bucket = jra.reference_bucket()
    ins, dlt = _ins_del(admin_read)

    if can_manage:
        task_labels = ["Job-wide (all tasks)"]
        task_values: list[str | None] = [None]
        for t in tasks or []:
            if not isinstance(t, dict):
                continue
            tid = str(t.get("id") or "").strip()
            if not tid:
                continue
            task_labels.append(_task_label(t))
            task_values.append(tid)
        link_ix = st.selectbox(
            "Link to",
            options=list(range(len(task_labels))),
            format_func=lambda i: task_labels[int(i)],
            key=f"jra_link_{job_id}",
            label_visibility="visible",
        )
        target_task_id = task_values[int(link_ix)]

        up = st.file_uploader(
            "Upload files",
            type=["jpg", "jpeg", "png", "webp", "pdf", "docx", "xlsx"],
            accept_multiple_files=True,
            key=f"jra_up_{job_id}",
            help="Images, PDF, Word, or Excel — stored for supervisors to review.",
        )
        if up:
            if st.button("Save uploads", type="primary", key=f"jra_save_{job_id}"):
                uid = str((current_profile() or {}).get("id") or "").strip() or None
                n_ok = 0
                errs: list[str] = []
                files = up if isinstance(up, list) else [up]
                for f in files:
                    raw_name = str(getattr(f, "name", "") or "upload")
                    if not jra.is_allowed_attachment(raw_name):
                        errs.append(f"{raw_name}: type not allowed")
                        continue
                    try:
                        data = f.getvalue()
                        path, disp = jra.storage_path_for_upload(job_id, raw_name)
                        ctype = jra.content_type_for_filename(raw_name)
                        upload_bytes_admin(path, data, content_type=ctype, bucket=bucket)
                        ins(
                            "job_reference_attachments",
                            {
                                "job_id": str(job_id).strip(),
                                "task_id": target_task_id,
                                "file_name": disp[:500],
                                "file_type": ctype,
                                "file_url": path,
                                "uploaded_by": uid,
                                "created_at": datetime.now(timezone.utc).isoformat(),
                            },
                        )
                        n_ok += 1
                    except Exception as exc:
                        errs.append(f"{raw_name}: {exc}")
                if n_ok:
                    st.success(f"Uploaded {n_ok} file(s).")
                for e in errs:
                    st.error(e)
                if n_ok:
                    st.rerun()

    if not rows:
        st.info("No reference attachments yet." if can_manage else "No reference attachments for this job yet.")
        return

    for r in rows:
        rid = str(r.get("id") or "").strip()
        if not rid:
            continue
        fname = str(r.get("file_name") or "file").strip()
        path = str(r.get("file_url") or "").strip()
        ftype = str(r.get("file_type") or "").strip()
        task_id = str(r.get("task_id") or "").strip()
        link_lbl = "Job-wide"
        if task_id:
            match = next((x for x in (tasks or []) if str(x.get("id")) == task_id), None)
            link_lbl = _task_label(match) if match else f"Task {task_id[:8]}…"

        signed = ""
        if path:
            try:
                signed = create_signed_url(path, expires_in=3600, bucket=bucket)
            except Exception:
                signed = ""

        with st.container(border=True):
            st.markdown('<span class="ips-job-ref-attach-card"></span>', unsafe_allow_html=True)
            ic = _icon_for_filename(fname)
            c1, c2 = st.columns([1.15, 2.2], gap="small")
            with c1:
                if signed and jra.is_image_filename(fname):
                    st.markdown(
                        f'<img src="{html.escape(signed)}" alt="" '
                        'style="max-width:120px;width:100%;border-radius:8px;border:1px solid #d1d5db;" />',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f'<p style="font-size:2.5rem;text-align:center;margin:0.5rem 0;">{html.escape(ic)}</p>',
                        unsafe_allow_html=True,
                    )
            with c2:
                st.markdown(
                    f"<p style='font-weight:650;font-size:0.95rem;'>{html.escape(fname)}</p>"
                    f"<p style='font-size:0.82rem;color:#4b5563;'>{html.escape(ftype)} · {_fmt_dt(r.get('created_at'))}</p>"
                    f"<p style='font-size:0.8rem;color:#64748b;'>Scope: <strong>{html.escape(link_lbl)}</strong></p>",
                    unsafe_allow_html=True,
                )
                b1, b2 = st.columns(2, gap="small")
                with b1:
                    if signed:
                        st.link_button("View / Open", signed, use_container_width=True, type="primary")
                    else:
                        st.caption("Link unavailable")
                with b2:
                    if can_manage:
                        if st.button("Delete", key=f"jra_del_{job_id}_{rid}", type="secondary", use_container_width=True):
                            try:
                                if path:
                                    try:
                                        delete_storage_object_admin(path, bucket=bucket)
                                    except Exception:
                                        pass
                                dlt("job_reference_attachments", {"id": rid})
                                st.success("Deleted.")
                                st.rerun()
                            except Exception as exc:
                                st.error(str(exc))


def render_reference_attachments_for_package(
    *,
    job_id: str,
    package_task_ids: list[str],
    admin_read: bool,
) -> None:
    """Supervisor: read-only list filtered to job-wide + tasks on this daily package."""
    _inject_ref_attachment_css()
    st.markdown("##### Reference attachments")
    st.caption("Files from the PM for this job and today’s assigned tasks.")

    rows = _fetch_rows(job_id, admin_read=admin_read)
    vis = set(str(x).strip() for x in package_task_ids if str(x).strip())
    filtered = jra.filter_rows_for_package(rows, vis)
    if not filtered:
        st.info("No reference attachments for this package.")
        return

    bucket = jra.reference_bucket()
    for r in sorted(filtered, key=lambda x: str(x.get("created_at") or ""), reverse=True):
        rid = str(r.get("id") or "").strip()
        fname = str(r.get("file_name") or "file").strip()
        path = str(r.get("file_url") or "").strip()
        ftype = str(r.get("file_type") or "").strip()
        signed = ""
        if path:
            try:
                signed = create_signed_url(path, expires_in=3600, bucket=bucket)
            except Exception:
                signed = ""
        with st.container(border=True):
            st.markdown('<span class="ips-job-ref-attach-card"></span>', unsafe_allow_html=True)
            ic = _icon_for_filename(fname)
            c1, c2 = st.columns([1.05, 2.4], gap="small")
            with c1:
                if signed and jra.is_image_filename(fname):
                    st.markdown(
                        f'<img src="{html.escape(signed)}" alt="" '
                        'style="max-width:100px;width:100%;border-radius:8px;border:1px solid #d1d5db;" />',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f'<p style="font-size:2.1rem;text-align:center;margin:0.35rem 0;">{html.escape(ic)}</p>',
                        unsafe_allow_html=True,
                    )
            with c2:
                st.markdown(
                    f"<p style='font-weight:650;font-size:0.9rem;'>{html.escape(fname)}</p>"
                    f"<p style='font-size:0.78rem;color:#4b5563;'>{html.escape(ftype)} · {_fmt_dt(r.get('created_at'))}</p>",
                    unsafe_allow_html=True,
                )
                if signed:
                    st.link_button("View / Open", signed, use_container_width=True, type="primary")
