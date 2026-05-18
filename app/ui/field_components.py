"""Reusable field-ops UI blocks (timeline, job photos)."""

from __future__ import annotations

import re
from typing import Any

import streamlit as st

try:
    from app.config import settings
    from app.db import create_signed_url
except ImportError:
    from config import settings  # type: ignore
    from db import create_signed_url  # type: ignore


def _photo_bucket() -> str:
    return str(getattr(settings, "task_photos_bucket", "task-photos") or "task-photos")

try:
    from app.ui.components.badges import render_badge
    from app.ui.components.empty_states import render_empty_state
    from app.ui.page_shell import render_card
except ImportError:
    from ui.components.badges import render_badge  # type: ignore
    from ui.components.empty_states import render_empty_state  # type: ignore
    from ui.page_shell import render_card  # type: ignore

try:
    from app.services.job_photos import PHOTO_CATEGORIES, fetch_job_photos, upload_job_photos
    from app.services.job_timeline import fetch_timeline_for_job, timeline_badge_tone
except ImportError:
    from services.job_photos import PHOTO_CATEGORIES, fetch_job_photos, upload_job_photos  # type: ignore
    from services.job_timeline import fetch_timeline_for_job, timeline_badge_tone  # type: ignore

_IMG_EXT = re.compile(r"\.(jpe?g|png|gif|webp)$", re.IGNORECASE)


def render_job_timeline_panel(*, job_id: str, admin_read: bool, limit: int = 40) -> None:
    jid = str(job_id or "").strip()
    if not jid:
        return
    with render_card("Job timeline", subtitle="Field updates, reports, photos, and check-ins"):
        rows = fetch_timeline_for_job(jid, admin=admin_read, limit=limit)
        if not rows:
            render_empty_state(
                "No timeline entries yet.",
                icon="📋",
                hint="Daily reports, photos, and check-ins appear here after Phase 1 migration is applied.",
            )
            return
        for row in rows:
            et = str(row.get("event_type") or "note")
            tone = timeline_badge_tone(et)
            ts = str(row.get("created_at") or "")[:16].replace("T", " ")
            title = str(row.get("title") or "Update").strip()
            who = str(row.get("user_name") or "").strip()
            desc = str(row.get("description") or "").strip()
            c1, c2 = st.columns([0.85, 3.15], gap="small")
            with c1:
                render_badge(et.replace("_", " ").title()[:20], tone=tone)
            with c2:
                st.markdown(f"**{title}** · {ts}" + (f" · {who}" if who else ""))
                if desc:
                    st.caption(desc[:600])


def render_job_photos_panel(
    *,
    job_id: str,
    admin_read: bool,
    uploaded_by: str = "",
    compact: bool = False,
) -> None:
    jid = str(job_id or "").strip()
    if not jid:
        return
    title = "Photo timeline" if not compact else "Photos"
    with render_card(title, subtitle="Newest first · Before / During / Completed / Safety…"):
        cat_filter = st.selectbox(
            "Category",
            ["All"] + list(PHOTO_CATEGORIES),
            key=f"jp_cat_{jid}",
            label_visibility="collapsed" if compact else "visible",
        )
        cat = None if cat_filter == "All" else cat_filter
        photos = fetch_job_photos(jid, admin=admin_read, category=cat, limit=48)
        with st.expander("Upload photos", expanded=False):
            st.file_uploader(
                "Photos",
                type=["jpg", "jpeg", "png", "gif", "webp"],
                accept_multiple_files=True,
                key=f"jp_upload_{jid}",
            )
            st.text_input("Caption", key=f"jp_caption_{jid}", placeholder="Optional")
            st.selectbox("Category", PHOTO_CATEGORIES, key=f"jp_upload_cat_{jid}")
            if st.button("Upload", type="primary", key=f"jp_go_{jid}", use_container_width=True):
                raw = st.session_state.get(f"jp_upload_{jid}")
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
                            job_id=jid,
                            files=payload,
                            uploaded_by=uploaded_by,
                            caption=str(st.session_state.get(f"jp_caption_{jid}") or ""),
                            category=str(st.session_state.get(f"jp_upload_cat_{jid}") or "Progress"),
                            admin=admin_read,
                        )
                        st.success(f"Uploaded {len(payload)} photo(s).")
                        st.session_state.pop(f"jp_upload_{jid}", None)
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))

        if not photos:
            render_empty_state("No photos for this job yet.", icon="📷")
            return
        cols = st.columns(min(4, max(1, len(photos[:8]))))
        for i, ph in enumerate(photos[:16]):
            with cols[i % len(cols)]:
                pth = str(ph.get("storage_path") or "").strip()
                url = create_signed_url(pth, expires_in=3600, bucket=_photo_bucket()) if pth else ""
                cap = str(ph.get("caption") or ph.get("file_name") or "photo")[:50]
                cat_b = str(ph.get("category") or "")
                if url and (_IMG_EXT.search(pth.lower()) or _IMG_EXT.search(cap.lower())):
                    st.image(url, caption=f"{cat_b}: {cap}" if cat_b else cap, use_container_width=True)
                elif url:
                    st.link_button("Open", url, use_container_width=True)
