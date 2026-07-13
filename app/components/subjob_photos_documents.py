"""Photos and Documents sections for Job Details subjob detail view."""

from __future__ import annotations

import html
import re

import streamlit as st

from app.components.record_modal import dialog_card_html
from app.config import settings
from app.db import create_signed_url
from app.services.asset_document_util import guess_document_content_type
from app.services.job_documents import (
    delete_job_document,
    fetch_job_documents,
    link_job_document_to_task,
    unlink_job_document_from_task,
    upload_job_document,
)
from app.services.job_photos import (
    PHOTO_CATEGORIES,
    fetch_job_photos,
    link_job_photo_to_task,
    unlink_job_photo_from_task,
    upload_job_photos,
)
JOB_SUBJOB_PHOTO_LINK_MODE_KEY = "job_subjob_photo_link_mode"
JOB_SUBJOB_PHOTO_UPLOAD_MODE_KEY = "job_subjob_photo_upload_mode"
JOB_SUBJOB_DOC_LINK_MODE_KEY = "job_subjob_doc_link_mode"
JOB_SUBJOB_DOC_UPLOAD_MODE_KEY = "job_subjob_doc_upload_mode"
JOB_SUBJOB_DOC_PENDING_DELETE_KEY = "job_subjob_doc_pending_delete"

_IMG_EXT = re.compile(r"\.(jpe?g|png|gif|webp)$", re.IGNORECASE)


def clear_job_subjob_media_state() -> None:
    for key in (
        JOB_SUBJOB_PHOTO_LINK_MODE_KEY,
        JOB_SUBJOB_PHOTO_UPLOAD_MODE_KEY,
        JOB_SUBJOB_DOC_LINK_MODE_KEY,
        JOB_SUBJOB_DOC_UPLOAD_MODE_KEY,
        JOB_SUBJOB_DOC_PENDING_DELETE_KEY,
    ):
        st.session_state.pop(key, None)


def _scope_key(job_id: str, task_id: str) -> str:
    return f"{job_id}:{task_id}"


def _admin_read() -> bool:
    from app.auth import current_role, effective_role
    return effective_role() in {"admin", "manager"}


def _photo_bucket() -> str:
    return str(getattr(settings, "task_photos_bucket", "task-photos") or "task-photos")


def _storage_bucket() -> str:
    return str(getattr(settings, "storage_bucket", "ips-storage") or "ips-storage")


def _signed_url(path: str, *, bucket: str | None = None) -> str:
    p = str(path or "").strip()
    if not p:
        return ""
    try:
        return create_signed_url(p, expires_in=3600, bucket=bucket) or ""
    except Exception:
        return ""


def _mode_active(session_key: str, job_id: str, task_id: str) -> bool:
    return str(st.session_state.get(session_key) or "") == _scope_key(job_id, task_id)


def _set_mode(session_key: str, job_id: str, task_id: str, active: bool) -> None:
    key = _scope_key(job_id, task_id)
    if active:
        st.session_state[session_key] = key
    elif st.session_state.get(session_key) == key:
        st.session_state.pop(session_key, None)


def _current_uploader_name() -> str:
    from app.auth import current_profile
    prof = current_profile() or {}
    return str(prof.get("full_name") or prof.get("name") or prof.get("email") or "").strip()


def _photo_summary(ph: dict) -> str:
    when = str(ph.get("created_at") or "")[:10] or "—"
    cap = str(ph.get("caption") or ph.get("file_name") or "Photo").strip()
    cat = str(ph.get("category") or "").strip()
    return f"{when} · {cat + ': ' if cat else ''}{cap[:60]}"


def _doc_summary(doc: dict) -> str:
    when = str(doc.get("upload_date") or doc.get("created_at") or "")[:10] or "—"
    name = str(doc.get("file_name") or doc.get("name") or "Document").strip()
    dtype = str(doc.get("doc_type") or "").strip()
    return f"{when} · {dtype + ' · ' if dtype else ''}{name[:60]}"


def _render_photo_upload_panel(*, job_id: str, task_id: str, key_prefix: str, admin: bool) -> None:
    st.markdown(dialog_card_html("Photos", "<p style=\"margin:0;font-size:0.875rem;color:#64748b;\">Upload a photo for this subjob.</p>"), unsafe_allow_html=True)
    st.file_uploader(
        "Photo",
        type=["jpg", "jpeg", "png", "gif", "webp"],
        accept_multiple_files=True,
        key=f"{key_prefix}_photo_files",
    )
    st.text_input("Caption", key=f"{key_prefix}_photo_caption", placeholder="Optional")
    st.selectbox("Category", PHOTO_CATEGORIES, key=f"{key_prefix}_photo_cat")
    btn_l, btn_r = st.columns(2)
    with btn_l:
        if st.button("Upload", type="primary", key=f"{key_prefix}_photo_upload_go"):
            raw = st.session_state.get(f"{key_prefix}_photo_files")
            files = raw if isinstance(raw, list) else ([raw] if raw else [])
            payload: list[tuple[bytes, str, str]] = []
            for i, up in enumerate(files):
                if up is None:
                    continue
                data = up.getvalue()
                if not data:
                    continue
                name = str(getattr(up, "name", "") or f"photo_{i}.jpg")
                ctype = str(getattr(up, "type", "") or "image/jpeg")
                payload.append((data, ctype, name))
            if not payload:
                st.warning("Choose at least one photo.")
            else:
                try:
                    upload_job_photos(
                        job_id=job_id,
                        files=payload,
                        uploaded_by=_current_uploader_name(),
                        caption=str(st.session_state.get(f"{key_prefix}_photo_caption") or ""),
                        category=str(st.session_state.get(f"{key_prefix}_photo_cat") or "Progress"),
                        task_id=task_id,
                        admin=admin,
                    )
                    _set_mode(JOB_SUBJOB_PHOTO_UPLOAD_MODE_KEY, job_id, task_id, False)
                    st.success(f"Uploaded {len(payload)} photo(s).")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
    with btn_r:
        if st.button("Cancel", key=f"{key_prefix}_photo_upload_cancel"):
            _set_mode(JOB_SUBJOB_PHOTO_UPLOAD_MODE_KEY, job_id, task_id, False)
            st.rerun()


def _render_photo_link_panel(*, job_id: str, task_id: str, key_prefix: str, admin: bool) -> None:
    unlinked = fetch_job_photos(job_id, admin=admin, unlinked_only=True, limit=100)
    st.markdown(
        dialog_card_html("Photos", '<p style="margin:0;font-size:0.875rem;color:#64748b;">Link an existing job photo to this subjob.</p>'),
        unsafe_allow_html=True,
    )
    if not unlinked:
        st.caption("No unlinked photos for this job.")
        if st.button("Cancel", key=f"{key_prefix}_photo_link_cancel_empty"):
            _set_mode(JOB_SUBJOB_PHOTO_LINK_MODE_KEY, job_id, task_id, False)
            st.rerun()
        return
    labels = [_photo_summary(r) for r in unlinked]
    pick_ix = st.selectbox(
        "Photo",
        range(len(unlinked)),
        format_func=lambda i: labels[i],
        key=f"{key_prefix}_photo_link_pick",
    )
    btn_l, btn_r = st.columns(2)
    with btn_l:
        if st.button("Save link", type="primary", key=f"{key_prefix}_photo_link_save"):
            pid = str(unlinked[int(pick_ix)].get("id") or "").strip()
            if pid:
                try:
                    link_job_photo_to_task(pid, task_id, admin=admin)
                    _set_mode(JOB_SUBJOB_PHOTO_LINK_MODE_KEY, job_id, task_id, False)
                    st.success("Photo linked to this subjob.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
    with btn_r:
        if st.button("Cancel", key=f"{key_prefix}_photo_link_cancel"):
            _set_mode(JOB_SUBJOB_PHOTO_LINK_MODE_KEY, job_id, task_id, False)
            st.rerun()


def _render_linked_photos(
    photos: list[dict],
    *,
    job_id: str,
    task_id: str,
    key_prefix: str,
    admin: bool,
) -> None:
    body_parts: list[str] = []
    for ph in photos[:12]:
        when = str(ph.get("created_at") or "")[:10] or "—"
        cap = html.escape(str(ph.get("caption") or ph.get("file_name") or "Photo").strip())
        cat = html.escape(str(ph.get("category") or "").strip())
        body_parts.append(
            f'<p style="margin:0 0 0.5rem;font-size:0.875rem;color:#0f172a;">'
            f"<strong>{cat or 'Photo'}</strong> · {when}<br>{cap}</p>"
        )
    st.markdown(dialog_card_html("Photos", "".join(body_parts)), unsafe_allow_html=True)
    cols = st.columns(min(4, max(1, len(photos[:8]))))
    for i, ph in enumerate(photos[:8]):
        pid = str(ph.get("id") or "").strip()
        if not pid:
            continue
        with cols[i % len(cols)]:
            pth = str(ph.get("storage_path") or "").strip()
            url = _signed_url(pth, bucket=_photo_bucket())
            cap = str(ph.get("caption") or ph.get("file_name") or "photo")[:40]
            if url and (_IMG_EXT.search(pth.lower()) or _IMG_EXT.search(cap.lower())):
                st.image(url, caption=cap, use_container_width=True)
            elif url:
                st.link_button("Open", url, use_container_width=True, key=f"{key_prefix}_photo_open_{pid}")
            if st.button("Unlink", key=f"{key_prefix}_photo_unlink_{pid}", use_container_width=True):
                try:
                    unlink_job_photo_from_task(pid, admin=admin)
                    st.success("Photo unlinked.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))


def render_subjob_photos_section(task: dict, job: dict) -> None:
    job_id = str(job.get("id") or "").strip()
    task_id = str(task.get("id") or "").strip()
    if not job_id or not task_id:
        return
    admin = _admin_read()
    key_prefix = f"job_subjob_photo_{job_id}_{task_id}"

    if _mode_active(JOB_SUBJOB_PHOTO_LINK_MODE_KEY, job_id, task_id):
        _render_photo_link_panel(job_id=job_id, task_id=task_id, key_prefix=key_prefix, admin=admin)
        return
    if _mode_active(JOB_SUBJOB_PHOTO_UPLOAD_MODE_KEY, job_id, task_id):
        _render_photo_upload_panel(job_id=job_id, task_id=task_id, key_prefix=key_prefix, admin=admin)
        return

    linked = fetch_job_photos(job_id, admin=admin, task_id=task_id, limit=48)
    if linked:
        _render_linked_photos(linked, job_id=job_id, task_id=task_id, key_prefix=key_prefix, admin=admin)
        return

    empty_html = (
        '<p style="margin:0;font-size:0.875rem;color:#64748b;">'
        "No photos linked to this subjob yet.</p>"
    )
    st.markdown(dialog_card_html("Photos", empty_html), unsafe_allow_html=True)
    btn_l, btn_r = st.columns(2)
    with btn_l:
        if st.button("+ Upload Photo", type="primary", key=f"{key_prefix}_upload", use_container_width=True):
            _set_mode(JOB_SUBJOB_PHOTO_UPLOAD_MODE_KEY, job_id, task_id, True)
            st.rerun()
    with btn_r:
        if st.button("Link Existing Photo", key=f"{key_prefix}_link", use_container_width=True):
            _set_mode(JOB_SUBJOB_PHOTO_LINK_MODE_KEY, job_id, task_id, True)
            st.rerun()


def _render_doc_upload_panel(*, job_id: str, task_id: str, key_prefix: str, admin: bool) -> None:
    st.markdown(
        dialog_card_html(
            "Upload Documents",
            '<p style="margin:0;font-size:0.875rem;color:#64748b;">'
            "Choose one or more documents to attach to this subjob.</p>",
        ),
        unsafe_allow_html=True,
    )
    st.file_uploader(
        "Choose documents",
        type=["pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "csv", "png", "jpg", "jpeg"],
        accept_multiple_files=True,
        key=f"{key_prefix}_doc_file",
    )
    st.text_input("Document type", value="Job Document", key=f"{key_prefix}_doc_type")
    st.text_input("Notes", key=f"{key_prefix}_doc_notes", placeholder="Optional")
    btn_l, btn_r = st.columns(2)
    with btn_l:
        if st.button("Upload", type="primary", key=f"{key_prefix}_doc_upload_go"):
            raw = st.session_state.get(f"{key_prefix}_doc_file")
            files = raw if isinstance(raw, list) else ([raw] if raw else [])
            if not files:
                st.warning("Choose at least one document to upload.")
            else:
                doc_type = str(st.session_state.get(f"{key_prefix}_doc_type") or "Job Document")
                notes = str(st.session_state.get(f"{key_prefix}_doc_notes") or "")
                uploaded = 0
                errors: list[str] = []
                for i, up in enumerate(files):
                    if up is None:
                        continue
                    data = up.getvalue()
                    name = str(getattr(up, "name", "") or f"document_{i + 1}")
                    if not data:
                        errors.append(f"{name}: empty file")
                        continue
                    ctype = guess_document_content_type(name, str(getattr(up, "type", "") or ""))
                    try:
                        upload_job_document(
                            job_id=job_id,
                            file_data=data,
                            file_name=name,
                            content_type=ctype,
                            uploaded_by=_current_uploader_name(),
                            doc_type=doc_type,
                            notes=notes,
                            task_id=task_id,
                            admin=admin,
                        )
                        uploaded += 1
                    except Exception as exc:
                        errors.append(f"{name}: {exc}")
                for err in errors:
                    st.error(err)
                if uploaded:
                    _set_mode(JOB_SUBJOB_DOC_UPLOAD_MODE_KEY, job_id, task_id, False)
                    st.success(f"Uploaded {uploaded} document(s).")
                    st.rerun()
    with btn_r:
        if st.button("Cancel", key=f"{key_prefix}_doc_upload_cancel"):
            _set_mode(JOB_SUBJOB_DOC_UPLOAD_MODE_KEY, job_id, task_id, False)
            st.rerun()


def _render_doc_link_panel(*, job_id: str, task_id: str, key_prefix: str, admin: bool) -> None:
    unlinked = fetch_job_documents(job_id, admin=admin, unlinked_only=True, limit=100)
    st.markdown(
        dialog_card_html("Documents", '<p style="margin:0;font-size:0.875rem;color:#64748b;">Link an existing job document to this subjob.</p>'),
        unsafe_allow_html=True,
    )
    if not unlinked:
        st.caption("No unlinked documents for this job.")
        if st.button("Cancel", key=f"{key_prefix}_doc_link_cancel_empty"):
            _set_mode(JOB_SUBJOB_DOC_LINK_MODE_KEY, job_id, task_id, False)
            st.rerun()
        return
    labels = [_doc_summary(r) for r in unlinked]
    pick_ix = st.selectbox(
        "Document",
        range(len(unlinked)),
        format_func=lambda i: labels[i],
        key=f"{key_prefix}_doc_link_pick",
    )
    btn_l, btn_r = st.columns(2)
    with btn_l:
        if st.button("Save link", type="primary", key=f"{key_prefix}_doc_link_save"):
            did = str(unlinked[int(pick_ix)].get("id") or "").strip()
            if did:
                try:
                    link_job_document_to_task(did, task_id, admin=admin)
                    _set_mode(JOB_SUBJOB_DOC_LINK_MODE_KEY, job_id, task_id, False)
                    st.success("Document linked to this subjob.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
    with btn_r:
        if st.button("Cancel", key=f"{key_prefix}_doc_link_cancel"):
            _set_mode(JOB_SUBJOB_DOC_LINK_MODE_KEY, job_id, task_id, False)
            st.rerun()


def _pending_subjob_doc_delete_scope(*, job_id: str, task_id: str, doc_id: str) -> str:
    return f"{job_id}:{task_id}:{doc_id}"


def _clear_pending_subjob_doc_delete() -> None:
    st.session_state.pop(JOB_SUBJOB_DOC_PENDING_DELETE_KEY, None)


def _handle_delete_subjob_document(*, doc_id: str, job_id: str, admin: bool) -> None:
    did = str(doc_id or "").strip()
    jid = str(job_id or "").strip()
    if not did or not jid:
        return
    try:
        delete_job_document(did, job_id=jid, admin=admin)
    except Exception as exc:
        st.error(str(exc))
        return
    _clear_pending_subjob_doc_delete()
    st.success("Document deleted.")
    st.rerun()


def _render_subjob_document_delete_confirm(
    *,
    doc: dict,
    job_id: str,
    task_id: str,
    key_prefix: str,
    admin: bool,
) -> None:
    did = str(doc.get("id") or "").strip()
    name = str(doc.get("file_name") or doc.get("name") or "Document").strip() or "Document"
    safe_name = html.escape(name)
    with st.container(key=f"{key_prefix}_doc_delete_confirm_{did}"):
        st.markdown(
            '<span class="ips-job-doc-delete-confirm-marker" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        msg_col, action_col = st.columns([5.5, 1.5], gap="small", vertical_alignment="center")
        with msg_col:
            st.markdown(
                f'<div class="ips-job-doc-delete-confirm-message">Delete document “{safe_name}”?</div>',
                unsafe_allow_html=True,
            )
        with action_col:
            delete_col, cancel_col = st.columns(2, gap="small")
            with delete_col:
                if st.button(
                    "Delete",
                    key=f"{key_prefix}_confirm_delete_doc_{did}",
                    type="primary",
                    use_container_width=True,
                ):
                    _handle_delete_subjob_document(doc_id=did, job_id=job_id, admin=admin)
            with cancel_col:
                if st.button(
                    "Cancel",
                    key=f"{key_prefix}_cancel_delete_doc_{did}",
                    use_container_width=True,
                ):
                    _clear_pending_subjob_doc_delete()
                    st.rerun()


def _render_subjob_document_action_buttons(*, job_id: str, task_id: str, key_prefix: str) -> None:
    btn_l, btn_r = st.columns(2)
    with btn_l:
        if st.button("+ Upload Documents", type="primary", key=f"{key_prefix}_upload", use_container_width=True):
            _set_mode(JOB_SUBJOB_DOC_UPLOAD_MODE_KEY, job_id, task_id, True)
            st.rerun()
    with btn_r:
        if st.button("Link Existing Documents", key=f"{key_prefix}_link", use_container_width=True):
            _set_mode(JOB_SUBJOB_DOC_LINK_MODE_KEY, job_id, task_id, True)
            st.rerun()


def _render_linked_documents(
    docs: list[dict],
    *,
    job_id: str,
    task_id: str,
    key_prefix: str,
    admin: bool,
) -> None:
    lines: list[str] = []
    for doc in docs[:20]:
        name = html.escape(str(doc.get("file_name") or doc.get("name") or "Document"))
        dtype = html.escape(str(doc.get("doc_type") or ""))
        when = html.escape(str(doc.get("upload_date") or doc.get("created_at") or "")[:10])
        notes = html.escape(str(doc.get("notes") or "").strip()[:120])
        meta = f"{dtype} · {when}" if dtype else when
        note_html = f"<br><span style=\"color:#64748b;\">{notes}</span>" if notes else ""
        lines.append(f"<p style=\"margin:0 0 0.75rem;font-size:0.875rem;color:#0f172a;\"><strong>{name}</strong><br>{meta}{note_html}</p>")
    st.markdown(dialog_card_html("Documents", "".join(lines)), unsafe_allow_html=True)
    pending_delete = str(st.session_state.get(JOB_SUBJOB_DOC_PENDING_DELETE_KEY) or "").strip()
    for doc in docs[:20]:
        did = str(doc.get("id") or "").strip()
        if not did:
            continue
        if pending_delete == _pending_subjob_doc_delete_scope(job_id=job_id, task_id=task_id, doc_id=did):
            _render_subjob_document_delete_confirm(
                doc=doc,
                job_id=job_id,
                task_id=task_id,
                key_prefix=key_prefix,
                admin=admin,
            )
            continue
        path = str(doc.get("storage_path") or "").strip()
        url = _signed_url(path, bucket=_storage_bucket())
        open_col, unlink_col, delete_col = st.columns([1, 1, 0.35], gap="small")
        with open_col:
            if url:
                st.link_button(
                    f"Open · {str(doc.get('file_name') or 'Document')[:30]}",
                    url,
                    use_container_width=True,
                    key=f"{key_prefix}_doc_open_{did}",
                )
        with unlink_col:
            if st.button("Unlink", key=f"{key_prefix}_doc_unlink_{did}", use_container_width=True):
                try:
                    unlink_job_document_from_task(did, admin=admin)
                    st.success("Document unlinked.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
        with delete_col:
            if st.button(
                "🗑️",
                key=f"{key_prefix}_doc_delete_{did}",
                help="Delete document",
                type="tertiary",
            ):
                st.session_state[JOB_SUBJOB_DOC_PENDING_DELETE_KEY] = _pending_subjob_doc_delete_scope(
                    job_id=job_id,
                    task_id=task_id,
                    doc_id=did,
                )
                st.rerun()


def render_subjob_documents_section(task: dict, job: dict) -> None:
    job_id = str(job.get("id") or "").strip()
    task_id = str(task.get("id") or "").strip()
    if not job_id or not task_id:
        return
    admin = _admin_read()
    key_prefix = f"job_subjob_doc_{job_id}_{task_id}"

    if _mode_active(JOB_SUBJOB_DOC_LINK_MODE_KEY, job_id, task_id):
        _render_doc_link_panel(job_id=job_id, task_id=task_id, key_prefix=key_prefix, admin=admin)
        return
    if _mode_active(JOB_SUBJOB_DOC_UPLOAD_MODE_KEY, job_id, task_id):
        _render_doc_upload_panel(job_id=job_id, task_id=task_id, key_prefix=key_prefix, admin=admin)
        return

    linked = fetch_job_documents(job_id, admin=admin, task_id=task_id, limit=50)
    if linked:
        _render_linked_documents(linked, job_id=job_id, task_id=task_id, key_prefix=key_prefix, admin=admin)
    else:
        empty_html = (
            '<p style="margin:0;font-size:0.875rem;color:#64748b;">'
            "No documents linked to this subjob yet.</p>"
        )
        st.markdown(dialog_card_html("Documents", empty_html), unsafe_allow_html=True)

    _render_subjob_document_action_buttons(job_id=job_id, task_id=task_id, key_prefix=key_prefix)
