"""Reference attachments: Job Detail / Tasks (PM) and Work & Plan (supervisor read)."""

from __future__ import annotations

import html
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

import streamlit as st
import streamlit.components.v1 as components

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
    from app.utils.formatting import fmt_datetime
except ImportError:
    from services.task_display import task_number_display  # type: ignore
    from utils.formatting import fmt_datetime  # type: ignore

_CSS_KEY = "ips_job_reference_attachments_css_v3"
IPS_JRA_FS_SESSION_KEY = "ips_jra_fullscreen_preview"


def bump_job_tasks_tab_data_cache(job_id: str) -> None:
    """Keep Job Database Tasks tab ``st.cache_data`` reads in sync after attachment changes."""
    k = f"jdt_job_data_ver_{str(job_id).strip()}"
    st.session_state[k] = int(st.session_state.get(k, 0)) + 1


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
            padding: 16px !important;
            margin-bottom: 1rem !important;
            box-sizing: border-box !important;
            max-width: 100% !important;
            overflow-x: hidden !important;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05) !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-ref-attach-card) p,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-ref-attach-card) .ips-jra-meta {
            color: #111827 !important;
            margin: 0.15rem 0 !important;
        }
        .ips-jra-preview-wrap {
            width: 100% !important;
            max-width: 100% !important;
            box-sizing: border-box !important;
            overflow-x: hidden !important;
            margin: 0 0 14px 0 !important;
        }
        .ips-jra-preview-wrap iframe {
            width: 100% !important;
            max-width: 100% !important;
            box-sizing: border-box !important;
            display: block !important;
            border: 1px solid #d1d5db !important;
            border-radius: 10px !important;
            background: #ffffff !important;
            min-height: 600px !important;
            height: min(75vh, 800px) !important;
        }
        .ips-jra-preview-wrap img.ips-jra-preview-img {
            width: 100% !important;
            max-width: 100% !important;
            height: auto !important;
            display: block !important;
            border-radius: 10px !important;
            border: 1px solid #d1d5db !important;
            box-sizing: border-box !important;
        }
        .ips-jra-doc-fallback {
            text-align: center;
            padding: 1.25rem 0.75rem;
            background: #ffffff;
            border: 1px dashed #d1d5db;
            border-radius: 10px;
            box-sizing: border-box;
            max-width: 100%;
        }
        /* Full-screen preview modal (only while dialog with marker is mounted) */
        .stApp:has(.ips-jra-fs-modal-root) [data-testid="stBackdrop"] {
            background: rgba(17, 24, 39, 0.85) !important;
        }
        div[data-testid="stDialog"]:has(.ips-jra-fs-modal-root) {
            width: min(95vw, 1600px) !important;
            max-width: 95vw !important;
            min-height: min(90vh, 900px) !important;
            max-height: 90vh !important;
            box-sizing: border-box !important;
        }
        div[data-testid="stDialog"]:has(.ips-jra-fs-modal-root) > div {
            background: #ffffff !important;
            border-radius: 12px !important;
            padding: 16px !important;
            width: 100% !important;
            max-width: 95vw !important;
            min-height: 85vh !important;
            max-height: 90vh !important;
            box-sizing: border-box !important;
            overflow-x: hidden !important;
            overflow-y: auto !important;
        }
        .ips-jra-fs-img-box {
            width: 100%;
            max-width: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        .ips-jra-fs-img-box img {
            max-width: 100%;
            max-height: calc(90vh - 120px);
            width: auto;
            height: auto;
            object-fit: contain;
            display: block;
            border-radius: 8px;
        }
        div[data-testid="stDialog"]:has(.ips-jra-fs-modal-root) button[kind="primary"] {
            min-height: 48px !important;
            font-weight: 600 !important;
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


def _task_label(t: dict[str, Any]) -> str:
    tid = str(t.get("id") or "")[:8]
    return f"{task_number_display(t)} ({tid}…)"


def _scope_label(task_id: str, tasks: list[dict[str, Any]] | None) -> str:
    tid = str(task_id or "").strip()
    if not tid:
        return "Job-wide"
    match = next((x for x in (tasks or []) if isinstance(x, dict) and str(x.get("id") or "").strip() == tid), None)
    return _task_label(match) if match else f"Task {tid[:8]}…"


def _is_pdf_filename(name: str) -> bool:
    return jra.normalize_extension(name) == "pdf"


def _is_pdf_mimetype(file_type: str) -> bool:
    return str(file_type or "").strip().lower() == "application/pdf"


def _is_pdf_document(fname: str, file_type: str) -> bool:
    """PDF by stored MIME (primary) or by filename extension."""
    return _is_pdf_mimetype(file_type) or _is_pdf_filename(fname)


def _gview_embed_url(public_file_url: str) -> str:
    """Google Docs viewer — fetches the PDF URL server-side; works where raw PDF iframe is blank."""
    q = quote(str(public_file_url).strip(), safe="")
    return f"https://docs.google.com/gview?url={q}&embedded=true"


def _pdf_iframe_html(*, signed_url: str, fname: str, iframe_height_px: int) -> str:
    """Iframe HTML for inline or modal PDF preview via Google viewer (border none)."""
    viewer = _gview_embed_url(signed_url)
    src_attr = html.escape(viewer, quote=True)
    safe_name = html.escape(fname)
    h = max(600, min(800, int(iframe_height_px)))
    return (
        f'<div style="width:100%;max-width:100%;overflow:hidden;box-sizing:border-box;margin:0;">'
        f'<iframe src="{src_attr}" title="{safe_name}" loading="lazy" '
        'referrerpolicy="no-referrer-when-downgrade" '
        f'style="width:100%;height:{h}px;min-height:600px;max-height:800px;'
        'border:none;background:#ffffff;box-sizing:border-box;display:block;">'
        "</iframe></div>"
    )


def _preview_kind(fname: str, file_type: str = "") -> str:
    if jra.is_image_filename(fname):
        return "image"
    if _is_pdf_document(fname, file_type):
        return "pdf"
    return "other"


@st.dialog("Attachment preview", width="large")
def _reference_attachment_fullscreen_dialog(fname: str, signed: str, kind: str) -> None:
    """Full-screen style preview (PDF iframe / image); close clears session flag."""
    st.markdown('<span class="ips-jra-fs-modal-root"></span>', unsafe_allow_html=True)
    top_l, top_r = st.columns([5, 1])
    with top_l:
        st.markdown(f"##### {html.escape(fname)}")
    with top_r:
        if st.button("✕ Close", key="ips_jra_fs_close_dialog", use_container_width=True, type="primary"):
            st.session_state[IPS_JRA_FS_SESSION_KEY] = None
            st.rerun()

    if kind == "image" and signed:
        safe_src = html.escape(signed, quote=True)
        safe_name = html.escape(fname)
        st.markdown(
            f'<div class="ips-jra-fs-img-box"><img src="{safe_src}" alt="{safe_name}" /></div>',
            unsafe_allow_html=True,
        )
    elif kind == "pdf" and signed:
        inner_h = 720
        components.html(
            _pdf_iframe_html(signed_url=signed, fname=fname, iframe_height_px=inner_h),
            height=min(820, inner_h + 40),
            scrolling=True,
        )
    else:
        st.info("Inline preview is not available for this file type. Use **View / Open** from the list.")
        if signed:
            st.link_button("View / Open", signed, use_container_width=True, type="primary")


def _maybe_run_fs_dialog() -> None:
    spec = st.session_state.get(IPS_JRA_FS_SESSION_KEY)
    if not isinstance(spec, dict):
        return
    signed = str(spec.get("signed") or "").strip()
    if not signed:
        st.session_state[IPS_JRA_FS_SESSION_KEY] = None
        return
    fname = str(spec.get("fname") or "Attachment")
    ftype = str(spec.get("file_type") or "")
    kind = str(spec.get("kind") or _preview_kind(fname, ftype))
    _reference_attachment_fullscreen_dialog(fname, signed, kind)


def _render_preview_block(*, signed: str, fname: str, file_type: str = "") -> None:
    """Full-width preview above metadata (image, PDF via Google viewer, or doc fallback)."""
    if not signed:
        st.markdown(
            '<div class="ips-jra-doc-fallback"><p style="margin:0;font-size:0.9rem;color:#374151;">'
            "Preview unavailable — use View / Open below if shown.</p></div>",
            unsafe_allow_html=True,
        )
        return
    safe_src = html.escape(signed, quote=True)
    safe_name = html.escape(fname)
    if jra.is_image_filename(fname):
        st.markdown(
            f'<div class="ips-jra-preview-wrap">'
            f'<img class="ips-jra-preview-img" src="{safe_src}" alt="{safe_name}" />'
            f"</div>",
            unsafe_allow_html=True,
        )
    elif _is_pdf_document(fname, file_type):
        components.html(
            _pdf_iframe_html(signed_url=signed, fname=fname, iframe_height_px=700),
            height=720,
            scrolling=True,
        )
    else:
        ic = _icon_for_filename(fname)
        st.markdown(
            f'<div class="ips-jra-preview-wrap"><div class="ips-jra-doc-fallback">'
            f'<p style="font-size:2.5rem;margin:0;line-height:1;">{html.escape(ic)}</p>'
            '<p style="margin:0.4rem 0 0;font-size:0.88rem;color:#374151;font-weight:500;">'
            "No inline preview — use View / Open below.</p>"
            "</div></div>",
            unsafe_allow_html=True,
        )


def _render_attachment_card(
    *,
    job_id: str,
    r: dict[str, Any],
    tasks: list[dict[str, Any]] | None,
    bucket: str,
    can_manage: bool,
    dlt: Any,
) -> None:
    rid = str(r.get("id") or "").strip()
    if not rid:
        return
    fname = str(r.get("file_name") or "file").strip()
    path = str(r.get("file_url") or "").strip()
    ftype = str(r.get("file_type") or "").strip()
    task_id = str(r.get("task_id") or "").strip()
    link_lbl = _scope_label(task_id, tasks)

    signed = ""
    if path:
        try:
            signed = create_signed_url(path, expires_in=3600, bucket=bucket)
        except Exception:
            signed = ""

    with st.container(border=True):
        st.markdown('<span class="ips-job-ref-attach-card"></span>', unsafe_allow_html=True)
        _render_preview_block(signed=signed, fname=fname, file_type=ftype)

        st.markdown(
            f"<p class='ips-jra-meta' style='font-weight:700;font-size:1rem;margin:0 0 0.25rem 0;'>{html.escape(fname)}</p>"
            f"<p class='ips-jra-meta' style='font-size:0.875rem;color:#1f2937;font-weight:500;margin:0.15rem 0;'>"
            f"{html.escape(ftype)} · {fmt_datetime(r.get('created_at'), compact=True)}</p>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<p class='ips-jra-meta' style='font-size:0.875rem;color:#1f2937;font-weight:500;margin:0.15rem 0 0.65rem 0;'>"
            f"Scope: <strong>{html.escape(link_lbl)}</strong></p>",
            unsafe_allow_html=True,
        )

        if can_manage:
            c_fs, c_vw, c_dl = st.columns(3, gap="small")
            with c_fs:
                if signed:
                    if st.button(
                        "Preview Full Screen",
                        key=f"jra_fs_open_{job_id}_{rid}",
                        use_container_width=True,
                        type="secondary",
                    ):
                        st.session_state[IPS_JRA_FS_SESSION_KEY] = {
                            "fname": fname,
                            "signed": signed,
                            "file_type": ftype,
                            "kind": _preview_kind(fname, ftype),
                        }
                        st.rerun()
                else:
                    st.button("Preview Full Screen", key=f"jra_fs_open_{job_id}_{rid}", disabled=True, use_container_width=True)
            with c_vw:
                if signed:
                    st.link_button("View / Open", signed, use_container_width=True, type="primary")
                else:
                    st.caption("Link unavailable")
            with c_dl:
                if st.button("Delete", key=f"jra_del_{job_id}_{rid}", type="secondary", use_container_width=True):
                    try:
                        if path:
                            try:
                                delete_storage_object_admin(path, bucket=bucket)
                            except Exception:
                                pass
                        dlt("job_reference_attachments", {"id": rid})
                        st.session_state.pop(IPS_JRA_FS_SESSION_KEY, None)
                        bump_job_tasks_tab_data_cache(job_id)
                        st.success("Deleted.")
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))
        else:
            c_fs, c_vw = st.columns(2, gap="small")
            with c_fs:
                if signed:
                    if st.button(
                        "Preview Full Screen",
                        key=f"jra_fs_open_{job_id}_{rid}",
                        use_container_width=True,
                        type="secondary",
                    ):
                        st.session_state[IPS_JRA_FS_SESSION_KEY] = {
                            "fname": fname,
                            "signed": signed,
                            "file_type": ftype,
                            "kind": _preview_kind(fname, ftype),
                        }
                        st.rerun()
                else:
                    st.button("Preview Full Screen", key=f"jra_fs_open_{job_id}_{rid}", disabled=True, use_container_width=True)
            with c_vw:
                if signed:
                    st.link_button("View / Open", signed, use_container_width=True, type="primary")
                else:
                    st.caption("Link unavailable")


def run_reference_attachment_fullscreen_dialog_if_pending() -> None:
    """Call early on the page when full-screen preview may open from reference attachments (any context)."""
    _maybe_run_fs_dialog()


def _render_task_details_attachment_row(
    *,
    job_id: str,
    task_id: str,
    section: str,
    r: dict[str, Any],
    bucket: str,
    can_manage: bool,
    dlt: Any,
) -> None:
    """Single reference row for Task Details modal (no upload); keys isolated from the job-wide panel."""
    rid = str(r.get("id") or "").strip()
    if not rid:
        return
    fname = str(r.get("file_name") or "file").strip()
    path = str(r.get("file_url") or "").strip()
    ftype = str(r.get("file_type") or "").strip()
    kp = f"jdtvd_{section}_{job_id}_{task_id}_{rid}"

    signed = ""
    if path:
        try:
            signed = create_signed_url(path, expires_in=3600, bucket=bucket)
        except Exception:
            signed = ""

    with st.container(border=True):
        st.markdown('<span class="ips-job-ref-attach-card"></span>', unsafe_allow_html=True)
        _render_preview_block(signed=signed, fname=fname, file_type=ftype)

        st.markdown(
            f"<p class='ips-jra-meta' style='font-weight:700;font-size:0.95rem;margin:0 0 0.25rem 0;color:#111827;'>"
            f"{html.escape(fname)}</p>"
            f"<p class='ips-jra-meta' style='font-size:0.8rem;color:#4b5563;margin:0;'>"
            f"{html.escape(ftype)} · {fmt_datetime(r.get('created_at'), compact=True)}</p>",
            unsafe_allow_html=True,
        )

        if can_manage:
            c_fs, c_vw, c_dl = st.columns(3, gap="small")
            with c_fs:
                if signed:
                    if st.button(
                        "Preview Full Screen",
                        key=f"{kp}_fs",
                        use_container_width=True,
                        type="secondary",
                    ):
                        st.session_state[IPS_JRA_FS_SESSION_KEY] = {
                            "fname": fname,
                            "signed": signed,
                            "file_type": ftype,
                            "kind": _preview_kind(fname, ftype),
                        }
                        st.rerun()
                else:
                    st.button("Preview Full Screen", key=f"{kp}_fs", disabled=True, use_container_width=True)
            with c_vw:
                if signed:
                    st.link_button("View / Open", signed, use_container_width=True, type="primary")
                else:
                    st.caption("Link unavailable")
            with c_dl:
                if st.button("Delete", key=f"{kp}_del", type="secondary", use_container_width=True):
                    try:
                        if path:
                            try:
                                delete_storage_object_admin(path, bucket=bucket)
                            except Exception:
                                pass
                        dlt("job_reference_attachments", {"id": rid})
                        st.session_state.pop(IPS_JRA_FS_SESSION_KEY, None)
                        bump_job_tasks_tab_data_cache(job_id)
                        st.success("Deleted.")
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))
        else:
            c_fs, c_vw = st.columns(2, gap="small")
            with c_fs:
                if signed:
                    if st.button(
                        "Preview Full Screen",
                        key=f"{kp}_fs",
                        use_container_width=True,
                        type="secondary",
                    ):
                        st.session_state[IPS_JRA_FS_SESSION_KEY] = {
                            "fname": fname,
                            "signed": signed,
                            "file_type": ftype,
                            "kind": _preview_kind(fname, ftype),
                        }
                        st.rerun()
                else:
                    st.button("Preview Full Screen", key=f"{kp}_fs", disabled=True, use_container_width=True)
            with c_vw:
                if signed:
                    st.link_button("View / Open", signed, use_container_width=True, type="primary")
                else:
                    st.caption("Link unavailable")


def render_task_details_reference_attachments(
    *,
    job_id: str,
    task_id: str,
    att_rows: list[dict[str, Any]],
    bucket: str,
    can_manage: bool,
    dlt: Any,
) -> None:
    """
    Task Details modal: show job-wide (task_id empty/null) and task-specific rows from ``att_rows``.
    Does not change upload behavior — display and actions only.
    """
    _inject_ref_attachment_css()
    jid = str(job_id or "").strip()
    tid = str(task_id or "").strip()

    def _row_job_matches(rr: dict[str, Any]) -> bool:
        rj = str((rr or {}).get("job_id") or "").strip()
        return (not rj) or (rj == jid)

    raw = [r for r in (att_rows or []) if isinstance(r, dict) and _row_job_matches(r)]
    job_wide = [r for r in raw if not str((r or {}).get("task_id") or "").strip()]
    task_only = [r for r in raw if str((r or {}).get("task_id") or "").strip() == tid]

    job_wide.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
    task_only.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
    job_wide = job_wide[:50]
    task_only = task_only[:50]

    st.markdown("##### Reference Attachments")
    if not job_wide and not task_only:
        st.caption("No reference attachments for this job or task.")
        return

    st.markdown("**Job-wide attachments**")
    if job_wide:
        for r in job_wide:
            _render_task_details_attachment_row(
                job_id=jid,
                task_id=tid,
                section="jw",
                r=r,
                bucket=bucket,
                can_manage=can_manage,
                dlt=dlt,
            )
    else:
        st.caption("No job-wide files.")

    st.markdown("**This task attachments**")
    if task_only:
        for r in task_only:
            _render_task_details_attachment_row(
                job_id=jid,
                task_id=tid,
                section="ts",
                r=r,
                bucket=bucket,
                can_manage=can_manage,
                dlt=dlt,
            )
    else:
        st.caption("No files linked only to this task.")


def render_job_reference_attachments_panel(
    *,
    job_id: str,
    tasks: list[dict[str, Any]],
    admin_read: bool,
    can_manage: bool,
) -> None:
    """PM/admin: upload + list + delete. Others: view/download only."""
    _inject_ref_attachment_css()
    _maybe_run_fs_dialog()
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
                    bump_job_tasks_tab_data_cache(job_id)
                    st.rerun()

    if not rows:
        st.info("No reference attachments yet." if can_manage else "No reference attachments for this job yet.")
        return

    for r in rows:
        if not isinstance(r, dict):
            continue
        _render_attachment_card(
            job_id=job_id,
            r=r,
            tasks=list(tasks or []),
            bucket=bucket,
            can_manage=can_manage,
            dlt=dlt,
        )


def render_reference_attachments_for_package(
    *,
    job_id: str,
    package_task_ids: list[str],
    admin_read: bool,
    tasks: list[dict[str, Any]] | None = None,
) -> None:
    """Supervisor: read-only list filtered to job-wide + tasks on this daily package."""
    _inject_ref_attachment_css()
    _maybe_run_fs_dialog()
    st.markdown("##### Reference attachments")
    st.caption("Files from the PM for this job and today’s assigned tasks.")

    rows = _fetch_rows(job_id, admin_read=admin_read)
    vis = set(str(x).strip() for x in package_task_ids if str(x).strip())
    filtered = jra.filter_rows_for_package(rows, vis)
    if not filtered:
        st.info("No reference attachments for this package.")
        return

    bucket = jra.reference_bucket()
    _, dlt_ro = _ins_del(admin_read)
    for r in sorted(filtered, key=lambda x: str(x.get("created_at") or ""), reverse=True):
        if not isinstance(r, dict):
            continue
        _render_attachment_card(
            job_id=job_id,
            r=r,
            tasks=tasks,
            bucket=bucket,
            can_manage=False,
            dlt=dlt_ro,
        )
