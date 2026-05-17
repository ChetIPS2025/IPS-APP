"""Company-wide announcements (not job-scoped) — internal announcement board layout."""

from __future__ import annotations

import html
import re
import uuid
from collections import Counter
from datetime import date, datetime, timezone
from typing import Any

import streamlit as st

from auth import current_profile, current_role
try:
    from app.ui.page_shell import render_page_header
except ImportError:
    from ui.page_shell import render_page_header  # type: ignore

try:
    from app.data_cache import clear_session_table_cache, fetch_table_for_session
except ImportError:
    from data_cache import clear_session_table_cache, fetch_table_for_session  # type: ignore

try:
    from app.db import (
        create_signed_url,
        delete_rows_admin,
        fetch_by_match,
        fetch_table_admin,
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
        fetch_table_admin,
        insert_row,
        insert_row_admin,
        update_rows_admin,
        upload_bytes_admin,
    )

try:
    from app.ui.field_light_theme import inject_field_light_theme
except ImportError:
    from ui.field_light_theme import inject_field_light_theme  # type: ignore

try:
    from app.ui.modal import ensure_modal_styles, modal_wide_marker
except ImportError:
    from ui.modal import ensure_modal_styles, modal_wide_marker  # type: ignore

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

_STYLE_KEY = "ips_company_updates_styles_v4"
_CU_CARD = "ips-cu-card"


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


def _read_counts_by_update(*, use_admin: bool) -> dict[str, int]:
    """Office roles: approximate acknowledgement counts (service read)."""
    if not use_admin:
        return {}
    try:
        rows = list(fetch_table_admin("company_update_reads", columns="update_id", limit=20000) or [])
    except Exception:
        return {}
    c = Counter(str((r or {}).get("update_id") or "").strip() for r in rows if (r or {}).get("update_id"))
    return dict(c)


def _recent_reads_for_user(*, user_id: str, title_by_id: dict[str, str], limit: int = 6) -> list[dict[str, Any]]:
    uid = str(user_id or "").strip()
    if not uid:
        return []
    try:
        hits = fetch_by_match("company_update_reads", {"user_id": uid}, limit=80)
    except Exception:
        return []
    out: list[dict[str, Any]] = []
    for h in hits or []:
        if not isinstance(h, dict):
            continue
        u = str(h.get("update_id") or "").strip()
        if not u:
            continue
        out.append(
            {
                "update_id": u,
                "read_at": str(h.get("read_at") or "")[:16],
                "title": title_by_id.get(u, "—")[:48],
            }
        )
    out.sort(key=lambda x: str(x.get("read_at") or ""), reverse=True)
    return out[:limit]


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


def _inject_page_styles() -> None:
    if st.session_state.get(_STYLE_KEY):
        return
    st.session_state[_STYLE_KEY] = True
    st.markdown(
        f"""
        <style>
        .{_CU_CARD} {{
          border: 1px solid rgba(148, 163, 184, 0.55);
          border-radius: 12px;
          padding: 14px 16px;
          margin-bottom: 12px;
          background: var(--ips-cu-card-bg, #ffffff);
          color: var(--ips-cu-card-fg, #0f172a);
          box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
          transition: box-shadow 0.15s ease, border-color 0.15s ease;
        }}
        .{_CU_CARD}:hover {{
          box-shadow: 0 4px 14px rgba(15, 23, 42, 0.1);
          border-color: rgba(100, 116, 139, 0.65);
        }}
        .{_CU_CARD}.ips-cu-card-urgent {{
          border-left: 4px solid #ef4444;
          background: linear-gradient(90deg, rgba(254, 226, 226, 0.35) 0%, var(--ips-cu-card-bg, #fff) 14%);
        }}
        .ips-cu-badge {{
          display: inline-flex;
          align-items: center;
          font-size: 0.65rem;
          font-weight: 700;
          letter-spacing: 0.04em;
          text-transform: uppercase;
          padding: 3px 8px;
          border-radius: 6px;
          margin-right: 6px;
          margin-bottom: 4px;
          border: 1px solid rgba(15, 23, 42, 0.1);
          white-space: nowrap;
        }}
        .ips-cu-badge-cat {{ background: #e0e7ff; color: #312e81; border-color: #a5b4fc; }}
        .ips-cu-badge-pri-normal {{ background: #f1f5f9; color: #334155; }}
        .ips-cu-badge-pri-important {{ background: #fef3c7; color: #92400e; border-color: #fcd34d; }}
        .ips-cu-badge-pri-urgent {{ background: #fee2e2; color: #991b1b; border-color: #f87171; }}
        .ips-cu-badge-read {{ background: #dcfce7; color: #14532d; border-color: #86efac; }}
        .ips-cu-card-title {{
          font-size: 1.08rem;
          font-weight: 700;
          margin: 0 0 8px 0;
          line-height: 1.3;
          color: var(--ips-cu-card-fg, #0f172a);
        }}
        .ips-cu-meta {{
          font-size: 0.8rem;
          color: #64748b;
          margin: 0 0 10px 0;
        }}
        .ips-cu-preview {{
          font-size: 0.92rem;
          line-height: 1.5;
          color: #334155;
          margin: 0;
        }}
        .ips-cu-img {{
          max-width: 100%;
          max-height: 220px;
          object-fit: cover;
          border-radius: 8px;
          margin-top: 10px;
          border: 1px solid #e2e8f0;
        }}
        /* Compact company-updates action row */
        section.main div[data-testid="column"] div.stButton > button p {{
          white-space: nowrap !important;
          font-size: 0.78rem !important;
        }}
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


def _preview_text(msg: str, max_len: int = 220) -> str:
    t = str(msg or "").strip().replace("\r\n", "\n").replace("\r", "\n")
    if len(t) <= max_len:
        return t
    return t[: max(0, max_len - 1)] + "…"


def _badge_pri_class(pri: str) -> str:
    p = str(pri or "Normal").strip()
    if p == "Important":
        return "ips-cu-badge ips-cu-badge-pri-important"
    if p == "Urgent":
        return "ips-cu-badge ips-cu-badge-pri-urgent"
    return "ips-cu-badge ips-cu-badge-pri-normal"


def _clear_filter_keys() -> None:
    st.session_state["cu_sf_search_raw"] = ""
    st.session_state["cu_sf_category"] = "All"
    st.session_state["cu_sf_priority"] = "All"
    if "cu_sf_show_retired" in st.session_state:
        st.session_state["cu_sf_show_retired"] = False


def _cu_on_dismiss_view() -> None:
    st.session_state.pop("cu_view_id", None)


def _cu_on_dismiss_admin() -> None:
    st.session_state.pop("cu_admin_modal_id", None)


def _cu_on_dismiss_post() -> None:
    st.session_state.pop("cu_open_post_dialog", None)


@st.dialog("Post announcement", width="large", on_dismiss=_cu_on_dismiss_post)
def _cu_post_dialog(*, me: str) -> None:
    ensure_modal_styles()
    modal_wide_marker()
    st.markdown("### Post announcement")
    with st.container(border=True):
        with st.form("cu_post_dlg", clear_on_submit=True):
            pt = st.text_input("Title", key="cu_post_title_dlg", placeholder="Headline")
            pm = st.text_area("Message", height=88, key="cu_post_msg_dlg", placeholder="Details…")
            p1, p2 = st.columns(2)
            with p1:
                pcat = st.selectbox("Category", list(_CATEGORIES), key="cu_post_cat_dlg")
            with p2:
                ppri = st.selectbox("Priority", list(_PRIORITIES), index=0, key="cu_post_pri_dlg")
            exp = st.date_input("Expires (optional)", value=None, key="cu_post_exp_dlg")
            att_url = st.text_input(
                "Attachment URL (optional)",
                key="cu_post_att_url_dlg",
                placeholder="https://…",
            )
            up = st.file_uploader(
                "Or upload",
                type=["png", "jpg", "jpeg", "webp", "gif", "pdf"],
                key="cu_post_file_dlg",
            )
            posted = st.form_submit_button("Post", type="primary", use_container_width=True)
    if st.button("Cancel", type="secondary", use_container_width=True, key="cu_post_cancel_dlg"):
        st.session_state.pop("cu_open_post_dialog", None)
        st.rerun()
    if posted:
        t = str(st.session_state.get("cu_post_title_dlg") or "").strip()
        body = str(st.session_state.get("cu_post_msg_dlg") or "").strip()
        if not t or not body:
            st.error("Title and message are required.")
            return
        pcat = str(st.session_state.get("cu_post_cat_dlg") or "General").strip()
        ppri = str(st.session_state.get("cu_post_pri_dlg") or "Normal").strip()
        exp = st.session_state.get("cu_post_exp_dlg")
        payload: dict[str, Any] = {
            "title": t,
            "message": body,
            "category": pcat,
            "priority": ppri,
            "posted_by": me or None,
            "is_active": True,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if exp is not None:
            payload["expires_at"] = str(exp)
        url_final = str(st.session_state.get("cu_post_att_url_dlg") or "").strip() or None
        up = st.session_state.get("cu_post_file_dlg")
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
                return
        payload["attachment_url"] = url_final
        try:
            insert_row_admin("company_updates", payload)
            clear_session_table_cache()
            st.session_state.pop("cu_open_post_dialog", None)
            st.success("Posted.")
            st.rerun()
        except Exception as exc:
            st.error(
                f"{exc} — Run **`sql/060_company_updates.sql`** in Supabase if this table is missing."
            )


@st.dialog("Announcement", width="large", on_dismiss=_cu_on_dismiss_view)
def _cu_view_dialog(*, row: dict[str, Any]) -> None:
    ensure_modal_styles()
    uid = str(row.get("id") or "").strip()
    st.markdown(f"### {html.escape(str(row.get('title') or '—'))}")
    st.caption(
        f"{html.escape(str(row.get('category') or ''))} · "
        f"{html.escape(str(row.get('priority') or ''))} · "
        f"{html.escape(str(row.get('created_at') or '')[:19].replace('T', ' '))}"
    )
    msg = str(row.get("message") or "")
    st.markdown(f"<div style='white-space:pre-wrap;font-size:0.95rem'>{html.escape(msg)}</div>", unsafe_allow_html=True)
    att = _attachment_display_url(str(row.get("attachment_url") or "").strip() or None)
    if att:
        low = att.lower()
        if low.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
            st.image(att, use_container_width=True)
        else:
            st.markdown(f"[Open attachment]({html.escape(att)})", unsafe_allow_html=True)
    if st.button("Close", type="secondary", key=f"cu_view_dlg_close_{uid}", use_container_width=True):
        st.session_state.pop("cu_view_id", None)
        st.rerun()


@st.dialog("Edit or retire update", width="large", on_dismiss=_cu_on_dismiss_admin)
def _company_update_admin_dialog(*, row: dict[str, Any], sel: str) -> None:
    ensure_modal_styles()
    st.markdown(f"**{html.escape(str(row.get('title') or '—'))}**")
    with st.form(f"cu_edit_form_{sel}"):
        et = st.text_input("Title", value=str(row.get("title") or ""), key=f"cu_ed_title_{sel}")
        em = st.text_area("Message", value=str(row.get("message") or ""), height=100, key=f"cu_ed_msg_{sel}")
        e1, e2, e3 = st.columns(3)
        with e1:
            cur_cat = str(row.get("category") or "General")
            ix = list(_CATEGORIES).index(cur_cat) if cur_cat in _CATEGORIES else 0
            ecat = st.selectbox("Category", list(_CATEGORIES), index=ix, key=f"cu_ed_cat_{sel}")
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
                st.session_state.pop("cu_admin_modal_id", None)
                st.success("Saved.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
        elif del_sub:
            try:
                delete_rows_admin("company_updates", {"id": sel})
                clear_session_table_cache()
                st.session_state.pop("cu_admin_modal_id", None)
                st.success("Deleted.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    if st.button("Cancel", type="secondary", key=f"cu_ed_close_{sel}", use_container_width=True):
        st.session_state.pop("cu_admin_modal_id", None)
        st.rerun()


def render() -> None:
    inject_field_light_theme()
    _inject_page_styles()
    role = current_role()
    prof = current_profile()
    me = str(prof.get("id") or "").strip()
    sk = me or "anonymous"
    use_admin = _norm_role(role) in ("admin", "manager")

    render_page_header(
        "Company Updates",
        "Announcements, safety notices, and schedule changes.",
    )

    st.session_state.setdefault("cu_sf_search_raw", "")
    st.session_state.setdefault("cu_sf_category", "All")
    st.session_state.setdefault("cu_sf_priority", "All")
    st.session_state.setdefault("cu_sf_show_retired", False)
    st.session_state.setdefault("cu_feed_limit", 30)

    labels = _profile_label_map(sk, use_admin=use_admin)
    rows_all = _load_updates(session_key=sk, use_admin=use_admin)
    read_ids = _read_update_ids(user_id=me)
    read_counts = _read_counts_by_update(use_admin=use_admin)
    title_by_id = {str(r.get("id")): str(r.get("title") or "—") for r in rows_all if str(r.get("id") or "").strip()}

    cat_f = str(st.session_state.get("cu_sf_category") or "All")
    pri_f = str(st.session_state.get("cu_sf_priority") or "All")
    show_retired = bool(st.session_state.get("cu_sf_show_retired")) and _can_manage_updates(role)
    q_low = str(st.session_state.get("cu_sf_search_raw") or "").strip().lower()

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

    lim = int(st.session_state.get("cu_feed_limit") or 30)
    filtered_visible = filtered[: max(10, lim)]

    modal_id = str(st.session_state.get("cu_admin_modal_id") or "").strip()
    view_id = str(st.session_state.get("cu_view_id") or "").strip()
    post_open = bool(_can_manage_updates(role) and st.session_state.get("cu_open_post_dialog"))

    if modal_id and _can_manage_updates(role):
        by_id_all = {str(r.get("id")): r for r in rows_all if str(r.get("id") or "").strip()}
        if modal_id in by_id_all:
            _company_update_admin_dialog(row=dict(by_id_all[modal_id]), sel=modal_id)
    elif view_id:
        by_all = {str(r.get("id")): r for r in rows_all if str(r.get("id") or "").strip()}
        if view_id in by_all:
            _cu_view_dialog(row=dict(by_all[view_id]))
    elif post_open:
        _cu_post_dialog(me=me)

    left, right = st.columns([0.72, 0.28], gap="medium")

    with left:
        st.markdown("##### Announcements")
        fc1, fc2, fc3, fc4, fc5 = st.columns([2.4, 1.05, 1.05, 0.95, 0.55], gap="small")
        with fc1:
            st.text_input(
                "Search",
                key="cu_sf_search_raw",
                placeholder="Search title or message…",
                label_visibility="collapsed",
            )
        with fc2:
            st.selectbox("Category", ["All"] + list(_CATEGORIES), key="cu_sf_category", label_visibility="collapsed")
        with fc3:
            st.selectbox("Priority", ["All"] + list(_PRIORITIES), key="cu_sf_priority", label_visibility="collapsed")
        with fc4:
            if _can_manage_updates(role):
                st.checkbox("Inactive", key="cu_sf_show_retired", help="Show retired / expired")
            else:
                st.caption("")
        with fc5:
            if st.button("Clear", key="cu_filters_clear", help="Reset filters"):
                _clear_filter_keys()
                st.session_state["cu_feed_limit"] = 30
                st.rerun()

        st.caption(f"{len(filtered)} matching · showing {len(filtered_visible)} newest")

        if not filtered and not rows_all:
            st.info("No company updates yet.")
        elif not filtered:
            st.caption("No updates match these filters.")
        else:
            for r in filtered_visible:
                uid = str(r.get("id") or "").strip()
                if not uid:
                    continue
                title = str(r.get("title") or "—").strip()
                body = str(r.get("message") or "")
                cat = str(r.get("category") or "General").strip()
                pri = str(r.get("priority") or "Normal").strip() or "Normal"
                posted = str(r.get("posted_by") or "").strip()
                by_lbl = labels.get(posted, "—")
                created = str(r.get("created_at") or "")[:16].replace("T", " ")
                att = _attachment_display_url(str(r.get("attachment_url") or "").strip() or None)
                is_read = uid in read_ids
                if use_admin:
                    n_ack = int(read_counts.get(uid, 0))
                    ack_line = f"{n_ack} acknowledged"
                else:
                    ack_line = "You acknowledged" if is_read else "Not read yet"
                urgent = pri == "Urgent" or cat == "Urgent"
                card_cls = f"{_CU_CARD} ips-cu-card-urgent" if urgent else _CU_CARD

                read_badge_html = (
                    '<span class="ips-cu-badge ips-cu-badge-read">Read</span>' if is_read else ""
                )
                cat_esc = html.escape(cat)
                pri_esc = html.escape(pri)
                title_esc = html.escape(title)
                preview_esc = html.escape(_preview_text(body))
                by_esc = html.escape(by_lbl)

                st.markdown(
                    f'<div class="{card_cls}">'
                    f'<div><span class="ips-cu-badge ips-cu-badge-cat">{cat_esc}</span>'
                    f'<span class="{_badge_pri_class(pri)}">{pri_esc}</span>{read_badge_html}</div>'
                    f'<p class="ips-cu-card-title">{title_esc}</p>'
                    f'<p class="ips-cu-meta">Posted by <strong>{by_esc}</strong> · {html.escape(created)} · {html.escape(ack_line)}</p>'
                    f'<p class="ips-cu-preview">{preview_esc}</p>'
                    f"</div>",
                    unsafe_allow_html=True,
                )
                if att:
                    low = att.lower()
                    if low.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
                        st.image(att, use_container_width=True)
                    else:
                        st.markdown(f"[Attachment]({html.escape(att)})", unsafe_allow_html=True)

                b1, b2, b3 = st.columns([0.65, 0.65, 0.65], gap="small")
                with b1:
                    if st.button("View", key=f"cu_view_{uid}", help="Full message", use_container_width=True):
                        st.session_state["cu_view_id"] = uid
                        st.rerun()
                with b2:
                    if me and not is_read:
                        if st.button("Ack", key=f"cu_ack1_{uid}", help="Mark read", use_container_width=True):
                            try:
                                insert_row("company_update_reads", {"update_id": uid, "user_id": me})
                            except Exception:
                                pass
                            clear_session_table_cache()
                            st.rerun()
                with b3:
                    if _can_manage_updates(role):
                        if st.button("Edit", key=f"cu_edit_{uid}", use_container_width=True):
                            st.session_state["cu_admin_modal_id"] = uid
                            st.rerun()

        if len(filtered) > len(filtered_visible):
            if st.button("Load more", key="cu_load_more"):
                st.session_state["cu_feed_limit"] = lim + 25
                st.rerun()

    with right:
        st.markdown("##### At a glance")

        # Quick stats
        s1, s2 = st.columns(2)
        with s1:
            st.metric("In feed", len(filtered))
        with s2:
            unread_n = sum(1 for x in filtered if str(x.get("id") or "").strip() not in read_ids)
            st.metric("Your unread", unread_n)
        urgent_n = sum(
            1
            for x in filtered
            if str(x.get("priority") or "") == "Urgent" or str(x.get("category") or "") == "Urgent"
        )
        st.caption(f"**Urgent in view:** {urgent_n}")

        st.markdown("---")

        # Acknowledge (compact)
        st.markdown("###### Acknowledge")
        if me and unread_n > 0:
            unread_rows = [x for x in filtered if str(x.get("id") or "").strip() not in read_ids]
            opts = [str(u.get("id")) for u in unread_rows if str(u.get("id") or "").strip()]

            def _fmt_ack(i: str) -> str:
                for u in unread_rows:
                    if str(u.get("id")) == i:
                        return str(u.get("title") or "—")[:56]
                return i

            st.multiselect(
                "Unread",
                options=opts,
                format_func=_fmt_ack,
                key="cu_ack_multi",
            )
            a1, a2 = st.columns(2)
            with a1:
                if st.button("Mark read", type="primary", key="cu_ack_sel", use_container_width=True):
                    pick = list(st.session_state.get("cu_ack_multi") or [])
                    for uid in pick:
                        uid = str(uid or "").strip()
                        if not uid:
                            continue
                        try:
                            insert_row("company_update_reads", {"update_id": uid, "user_id": me})
                        except Exception:
                            pass
                    clear_session_table_cache()
                    st.success("Recorded.")
                    st.rerun()
            with a2:
                if st.button("Mark all", key="cu_ack_all", use_container_width=True):
                    for u in unread_rows:
                        uid = str(u.get("id") or "").strip()
                        if not uid:
                            continue
                        try:
                            insert_row("company_update_reads", {"update_id": uid, "user_id": me})
                        except Exception:
                            pass
                    clear_session_table_cache()
                    st.success("All marked.")
                    st.rerun()
        else:
            st.caption("You're caught up.")

        recent = _recent_reads_for_user(user_id=me, title_by_id=title_by_id)
        if recent:
            st.caption("**Recent (you)**")
            for rr in recent:
                st.caption(f"· {rr['read_at']} — {rr['title']}")

        st.markdown("---")

        # Post update (admin) — modal
        if _can_manage_updates(role):
            if st.button("New update", type="primary", use_container_width=True, key="cu_btn_new_post"):
                st.session_state["cu_open_post_dialog"] = True
                st.rerun()

            st.caption("Use **Edit** on a card to change or retire posts.")
