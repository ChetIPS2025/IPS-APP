"""Company-wide announcements (not job-scoped)."""

from __future__ import annotations

import html
import re
import uuid
from datetime import date, datetime, timezone
from typing import Any

import streamlit as st
from streamlit.components import v1 as components

from auth import current_profile, current_role
from branding import render_header

try:
    from app.data_cache import clear_session_table_cache, fetch_table_for_session
except ImportError:
    from data_cache import clear_session_table_cache, fetch_table_for_session  # type: ignore

try:
    from app.db import (
        create_signed_url,
        delete_rows_admin,
        fetch_by_match,
        insert_row,
        insert_row_admin,
        update_rows_admin,
        upload_bytes_admin,
    )
except ImportError:
    from db import (  # type: ignore
        create_signed_url,
        delete_rows_admin,
        fetch_by_match,
        insert_row,
        insert_row_admin,
        update_rows_admin,
        upload_bytes_admin,
    )

try:
    from app.ui.field_light_theme import inject_field_light_theme
except ImportError:
    from ui.field_light_theme import inject_field_light_theme  # type: ignore

_CATEGORIES = (
    "General",
    "Safety",
    "Schedule",
    "Policy",
    "Equipment",
    "HR / Payroll",
    "Training",
    "Urgent",
)
_PRIORITIES = ("Normal", "Important", "Urgent")

_STYLE_KEY = "ips_company_updates_styles_v1"


def _norm_role(role: str) -> str:
    r = str(role or "").strip().lower()
    if r in ("pm", "estimator"):
        return "manager"
    return r


def _can_manage_updates(role: str) -> bool:
    return _norm_role(role) in ("admin", "manager")


def _profile_label_map(session_key: str, *, use_admin: bool) -> dict[str, str]:
    try:
        profs = fetch_table_for_session(
            "profiles",
            session_key=session_key,
            limit=5000,
            order_by="email",
            use_admin=use_admin,
        )
    except Exception:
        profs = []
    out: dict[str, str] = {}
    for p in profs or []:
        if not isinstance(p, dict):
            continue
        pid = str(p.get("id") or "").strip()
        if not pid:
            continue
        nm = str(p.get("full_name") or "").strip()
        em = str(p.get("email") or "").strip()
        out[pid] = nm or em or f"{pid[:8]}…"
    return out


def _load_updates(*, session_key: str, use_admin: bool) -> list[dict[str, Any]]:
    try:
        rows = list(
            fetch_table_for_session(
                "company_updates",
                session_key=session_key,
                limit=500,
                columns="*",
                order_by="created_at",
                use_admin=use_admin,
            )
            or []
        )
    except Exception:
        rows = []
    rows = [r for r in rows if isinstance(r, dict) and str(r.get("id") or "").strip()]
    rows.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)
    return rows


def _read_update_ids(*, user_id: str) -> set[str]:
    uid = str(user_id or "").strip()
    if not uid:
        return set()
    try:
        hits = fetch_by_match("company_update_reads", {"user_id": uid}, columns="update_id", limit=5000)
    except Exception:
        hits = []
    return {str((h or {}).get("update_id") or "").strip() for h in hits if str((h or {}).get("update_id") or "").strip()}


def _parse_expires(v: Any) -> datetime | None:
    if v is None or str(v).strip() == "":
        return None
    s = str(v).strip()
    try:
        if "T" in s or "+" in s or s.endswith("Z"):
            s2 = s.replace("Z", "+00:00")
            dt = datetime.fromisoformat(s2)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        return datetime.combine(date.fromisoformat(s[:10]), datetime.min.time(), tzinfo=timezone.utc)
    except Exception:
        return None


def _is_expired(row: dict[str, Any]) -> bool:
    ex = _parse_expires(row.get("expires_at"))
    if ex is None:
        return False
    return ex < datetime.now(timezone.utc)


def _inject_styles() -> None:
    if st.session_state.get(_STYLE_KEY):
        return
    st.session_state[_STYLE_KEY] = True
    st.markdown(
        """
        <style>
        .ips-cu-badge {
          display: inline-block;
          font-size: 0.68rem;
          font-weight: 700;
          letter-spacing: 0.04em;
          text-transform: uppercase;
          padding: 3px 8px;
          border-radius: 6px;
          margin-right: 6px;
          margin-bottom: 4px;
          border: 1px solid rgba(15, 23, 42, 0.12);
          background: #f1f5f9;
          color: #0f172a;
        }
        .ips-cu-badge-pri-normal { background: #e2e8f0; color: #0f172a; }
        .ips-cu-badge-pri-important { background: #fef3c7; color: #92400e; border-color: #fcd34d; }
        .ips-cu-badge-pri-urgent { background: #fee2e2; color: #991b1b; border-color: #f87171; }
        .ips-cu-card-html {
          border: 1px solid #cbd5e1;
          border-radius: 10px;
          padding: 10px 12px 12px 12px;
          margin-bottom: 10px;
          background: #ffffff;
          color: #111827;
        }
        .ips-cu-card-html.ips-cu-standout {
          border-left: 5px solid #dc2626;
          background: linear-gradient(90deg, rgba(254,226,226,0.55) 0%, #ffffff 18%);
          border-color: #fca5a5;
        }
        .ips-cu-card-title { font-size: 1.02rem; font-weight: 700; margin: 0 0 6px 0; color: #0f172a; }
        .ips-cu-meta { font-size: 0.78rem; color: #475569; margin-bottom: 8px; }
        .ips-cu-body { font-size: 0.88rem; line-height: 1.45; color: #1e293b; white-space: pre-wrap; }
        .ips-cu-img { max-width: 100%; border-radius: 8px; margin-top: 8px; border: 1px solid #e2e8f0; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _attachment_display_url(raw: str | None) -> str:
    u = str(raw or "").strip()
    if not u:
        return ""
    low = u.lower()
    if low.startswith(("javascript:", "data:", "vbscript:")):
        return ""
    if low.startswith(("http://", "https://")):
        return u
    try:
        return create_signed_url(u, expires_in=7200) or ""
    except Exception:
        return ""


def _sanitize_filename(name: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9._-]+", "_", str(name or "file").strip()) or "file"
    return base[:180]


def _badge_pri_class(pri: str) -> str:
    p = str(pri or "Normal").strip()
    if p == "Important":
        return "ips-cu-badge ips-cu-badge-pri-important"
    if p == "Urgent":
        return "ips-cu-badge ips-cu-badge-pri-urgent"
    return "ips-cu-badge ips-cu-badge-pri-normal"


def _build_feed_html(
    rows: list[dict[str, Any]],
    labels: dict[str, str],
    read_ids: set[str],
) -> str:
    parts: list[str] = []
    for r in rows:
        uid = str(r.get("id") or "").strip()
        title = html.escape(str(r.get("title") or "—"))
        msg = html.escape(str(r.get("message") or ""))
        cat = html.escape(str(r.get("category") or "General"))
        pri = str(r.get("priority") or "Normal").strip() or "Normal"
        pri_esc = html.escape(pri)
        posted = str(r.get("posted_by") or "").strip()
        by = html.escape(labels.get(posted, "—"))
        created = html.escape(str(r.get("created_at") or "")[:19].replace("T", " "))
        ex = r.get("expires_at")
        ex_s = html.escape(str(ex)[:19].replace("T", " ")) if ex else ""
        att = _attachment_display_url(str(r.get("attachment_url") or "").strip() or None)
        read_badge = '<span class="ips-cu-badge" style="background:#dcfce7;color:#14532d;">Read</span>' if uid in read_ids else ""
        standout = pri == "Urgent" or str(r.get("category") or "") == "Urgent"
        card_cls = "ips-cu-card-html ips-cu-standout" if standout else "ips-cu-card-html"
        img_html = ""
        if att:
            img_html = f'<img class="ips-cu-img" src="{html.escape(att)}" alt="" loading="lazy" />'
        exp_line = f'<div class="ips-cu-meta">Expires: {ex_s}</div>' if ex_s else ""
        parts.append(
            f'<div class="{card_cls}">'
            f'<div class="ips-cu-card-title">{title}</div>'
            f'<div><span class="ips-cu-badge">{cat}</span>'
            f'<span class="{_badge_pri_class(pri)}">{pri_esc}</span>{read_badge}</div>'
            f'<div class="ips-cu-meta">Posted by <strong>{by}</strong> · {created}</div>'
            f'{exp_line}'
            f'<div class="ips-cu-body">{msg}</div>'
            f"{img_html}"
            f"</div>"
        )
    inner = "".join(parts) if parts else '<p style="color:#64748b;padding:12px;">No updates match the current filters.</p>'
    return f'<div style="max-height:min(560px,70vh);overflow-y:auto;-webkit-overflow-scrolling:touch;">{inner}</div>'


def render() -> None:
    inject_field_light_theme()
    _inject_styles()
    role = current_role()
    prof = current_profile()
    me = str(prof.get("id") or "").strip()
    sk = me or "anonymous"
    use_admin = _norm_role(role) in ("admin", "manager")

    render_header(
        "Company Updates",
        subtitle="Announcements, safety notices, schedule changes, and company communication — not tied to job activity.",
    )

    st.session_state.setdefault("cu_sf_search", "")
    st.session_state.setdefault("cu_sf_search_raw", str(st.session_state.get("cu_sf_search") or ""))
    st.session_state.setdefault("cu_sf_category", "All")
    st.session_state.setdefault("cu_sf_priority", "All")
    st.session_state.setdefault("cu_sf_show_retired", False)

    labels = _profile_label_map(sk, use_admin=use_admin)
    rows_all = _load_updates(session_key=sk, use_admin=use_admin)
    read_ids = _read_update_ids(user_id=me)

    with st.form("cu_filters", clear_on_submit=False):
        f1, f2, f3, f4 = st.columns([2.2, 1.1, 1.1, 1.2], gap="small")
        with f1:
            st.text_input("Search (apply to filter)", key="cu_sf_search_raw", help="Keywords in title or message.")
        with f2:
            st.selectbox("Category", ["All"] + list(_CATEGORIES), key="cu_sf_category")
        with f3:
            st.selectbox("Priority", ["All"] + list(_PRIORITIES), key="cu_sf_priority")
        with f4:
            if _can_manage_updates(role):
                st.checkbox(
                    "Show inactive / expired",
                    key="cu_sf_show_retired",
                    help="Include updates turned off or past expiration.",
                )
            else:
                st.caption("Inactive/expired are hidden.")
        if st.form_submit_button("Apply filters"):
            raw_q = str(st.session_state.get("cu_sf_search_raw") or "").strip().lower()
            st.session_state["cu_sf_search"] = raw_q
            st.rerun()

    q_low = str(st.session_state.get("cu_sf_search") or "").strip().lower()
    cat_f = str(st.session_state.get("cu_sf_category") or "All")
    pri_f = str(st.session_state.get("cu_sf_priority") or "All")
    show_retired = bool(st.session_state.get("cu_sf_show_retired")) and _can_manage_updates(role)

    filtered: list[dict[str, Any]] = []
    for r in rows_all:
        if not show_retired:
            if not bool(r.get("is_active", True)):
                continue
            if _is_expired(r):
                continue
        if cat_f != "All" and str(r.get("category") or "").strip() != cat_f:
            continue
        if pri_f != "All" and str(r.get("priority") or "").strip() != pri_f:
            continue
        if q_low:
            blob = (str(r.get("title") or "") + " " + str(r.get("message") or "")).lower()
            if q_low not in blob:
                continue
        filtered.append(r)

    st.markdown("##### Feed")
    if not filtered and not rows_all:
        st.caption("No company updates posted.")
    elif not filtered:
        st.caption("No updates match these filters.")
    else:
        h = min(620, 120 + 140 * min(len(filtered), 12))
        components.html(_build_feed_html(filtered, labels, read_ids), height=h, scrolling=True)

    unread = [r for r in filtered if str(r.get("id") or "").strip() not in read_ids]
    if me and unread:
        st.markdown("##### Acknowledge")
        st.caption("Optional: record that you have read one or more updates.")
        pick = st.multiselect(
            "Updates to mark as read",
            options=[str(u.get("id")) for u in unread if str(u.get("id") or "").strip()],
            format_func=lambda i: next(
                (str(u.get("title") or "—")[:80] for u in unread if str(u.get("id")) == i),
                i,
            ),
            key="cu_ack_multi",
        )
        if st.button("Mark selected as read", key="cu_ack_btn", type="primary"):
            for uid in pick:
                uid = str(uid or "").strip()
                if not uid:
                    continue
                try:
                    insert_row(
                        "company_update_reads",
                        {"update_id": uid, "user_id": me},
                    )
                except Exception:
                    pass
            clear_session_table_cache()
            st.success("Recorded.")
            st.rerun()

    if _can_manage_updates(role):
        st.markdown("##### Post update")
        with st.form("cu_post", clear_on_submit=True):
            pt = st.text_input("Title", key="cu_post_title")
            pm = st.text_area("Message", height=140, key="cu_post_msg")
            c1, c2, c3 = st.columns(3)
            with c1:
                pcat = st.selectbox("Category", list(_CATEGORIES), key="cu_post_cat")
            with c2:
                ppri = st.selectbox("Priority", list(_PRIORITIES), index=0, key="cu_post_pri")
            with c3:
                exp = st.date_input("Expires (optional)", value=None, key="cu_post_exp")
            att_url = st.text_input("Attachment URL (optional)", key="cu_post_att_url", placeholder="https://… or leave blank")
            up = st.file_uploader("Or upload image/PDF (optional)", type=["png", "jpg", "jpeg", "webp", "gif", "pdf"], key="cu_post_file")
            if st.form_submit_button("Post update", type="primary"):
                t = str(pt or "").strip()
                body = str(pm or "").strip()
                if not t or not body:
                    st.error("Title and message are required.")
                    st.stop()
                else:
                    payload: dict[str, Any] = {
                        "title": t,
                        "message": body,
                        "category": str(pcat or "General").strip(),
                        "priority": str(ppri or "Normal").strip(),
                        "posted_by": me or None,
                        "is_active": True,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                    if exp is not None:
                        payload["expires_at"] = str(exp)
                    url_final = str(att_url or "").strip() or None
                    if up is not None:
                        raw = up.getvalue()
                        ext = _sanitize_filename(up.name)
                        spath = f"company_updates/{uuid.uuid4().hex}_{ext}"
                        try:
                            upload_bytes_admin(
                                spath,
                                raw,
                                content_type=str(up.type or "application/octet-stream"),
                            )
                            url_final = spath
                        except Exception as exc:
                            st.error(f"Upload failed: {exc}")
                            st.stop()
                    payload["attachment_url"] = url_final
                    try:
                        insert_row_admin("company_updates", payload)
                        clear_session_table_cache()
                        st.success("Posted.")
                        st.rerun()
                    except Exception as exc:
                        st.error(
                            f"{exc} — Run **`sql/060_company_updates.sql`** in Supabase if this table is missing."
                        )

        st.markdown("##### Edit or retire (office)")
        ids = [str(r.get("id")) for r in rows_all if str(r.get("id") or "").strip()]
        if not ids:
            st.caption("No updates exist yet.")
        else:
            by_id = {str(r.get("id")): r for r in rows_all}
            sel = st.selectbox(
                "Choose update",
                ids,
                format_func=lambda i: str((by_id.get(i) or {}).get("title") or i)[:72],
                key="cu_edit_pick",
            )
            row = by_id.get(sel) or {}
            with st.form("cu_edit_form"):
                et = st.text_input("Title", value=str(row.get("title") or ""), key=f"cu_ed_title_{sel}")
                em = st.text_area("Message", value=str(row.get("message") or ""), height=120, key=f"cu_ed_msg_{sel}")
                e1, e2, e3 = st.columns(3)
                with e1:
                    ecat = st.selectbox(
                        "Category",
                        list(_CATEGORIES),
                        index=max(0, list(_CATEGORIES).index(str(row.get("category") or "General")))
                        if str(row.get("category") or "General") in _CATEGORIES
                        else 0,
                        key=f"cu_ed_cat_{sel}",
                    )
                with e2:
                    rpri = str(row.get("priority") or "Normal")
                    epri = st.selectbox(
                        "Priority",
                        list(_PRIORITIES),
                        index=list(_PRIORITIES).index(rpri) if rpri in _PRIORITIES else 0,
                        key=f"cu_ed_pri_{sel}",
                    )
                with e3:
                    raw_ex = row.get("expires_at")
                    ex_d: date | None = None
                    if raw_ex:
                        try:
                            ex_d = date.fromisoformat(str(raw_ex)[:10])
                        except Exception:
                            ex_d = None
                    eexp = st.date_input("Expires", value=ex_d, key=f"cu_ed_exp_{sel}")
                active = st.checkbox("Active (visible in default feed)", value=bool(row.get("is_active", True)), key=f"cu_ed_act_{sel}")
                save = st.form_submit_button("Save changes", type="primary")
                del_sub = st.form_submit_button("Delete permanently", type="secondary")
                if save:
                    pl: dict[str, Any] = {
                        "title": str(et or "").strip(),
                        "message": str(em or "").strip(),
                        "category": str(ecat or "General").strip(),
                        "priority": str(epri or "Normal").strip(),
                        "is_active": bool(active),
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                    if eexp is not None:
                        pl["expires_at"] = str(eexp)
                    else:
                        pl["expires_at"] = None
                    try:
                        update_rows_admin("company_updates", pl, {"id": sel})
                        clear_session_table_cache()
                        st.success("Saved.")
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))
                elif del_sub:
                    try:
                        delete_rows_admin("company_updates", {"id": sel})
                        clear_session_table_cache()
                        st.success("Deleted.")
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))
