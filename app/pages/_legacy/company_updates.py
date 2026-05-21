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
    from app.ui.company_updates_components import (
        DISPLAY_TABS,
        KPI_SPECS,
        TAB_TO_CATEGORIES,
        display_category,
        display_department,
        feed_card_html,
        inject_company_updates_page_styles,
        kpi_stat_card_html,
        page_marker,
        pagination_info_html,
        parse_event_date,
        quick_links_widget_html,
        recent_updates_widget_html,
        render_page_header_html,
        upcoming_events_widget_html,
    )
except ImportError:
    from ui.company_updates_components import (  # type: ignore
        DISPLAY_TABS,
        KPI_SPECS,
        TAB_TO_CATEGORIES,
        display_category,
        display_department,
        feed_card_html,
        inject_company_updates_page_styles,
        kpi_stat_card_html,
        page_marker,
        pagination_info_html,
        parse_event_date,
        quick_links_widget_html,
        recent_updates_widget_html,
        render_page_header_html,
        upcoming_events_widget_html,
    )

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

_PAGE_SIZE = 5
_PRIORITY_RANK = {"Urgent": 0, "Important": 1, "Normal": 2}


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


@st.cache_data(ttl=60, show_spinner=False)
def _cached_load_updates(session_key: str, use_admin: bool) -> list[dict[str, Any]]:
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


@st.cache_data(ttl=30, show_spinner=False)
def _cached_read_ids(user_id: str) -> frozenset[str]:
    return frozenset(_read_update_ids(user_id=user_id))


@st.cache_data(ttl=120, show_spinner=False)
def _cached_profile_labels(session_key: str, use_admin: bool) -> dict[str, str]:
    return _profile_label_map(session_key, use_admin=use_admin)


def _invalidate_cu_cache() -> None:
    clear_session_table_cache()
    _cached_load_updates.clear()
    _cached_read_ids.clear()
    _cached_profile_labels.clear()


def _is_pinned(row: dict[str, Any]) -> bool:
    pri = str(row.get("priority") or "Normal").strip()
    return pri in ("Important", "Urgent")


def _sort_updates(rows: list[dict[str, Any]], sort_mode: str) -> list[dict[str, Any]]:
    mode = str(sort_mode or "Newest First").strip()
    if mode == "Oldest First":
        return sorted(rows, key=lambda r: str(r.get("created_at") or ""))
    if mode == "Priority":
        by_date = sorted(rows, key=lambda r: str(r.get("created_at") or ""), reverse=True)
        return sorted(
            by_date,
            key=lambda r: _PRIORITY_RANK.get(str(r.get("priority") or "Normal").strip(), 9),
        )
    return sorted(rows, key=lambda r: str(r.get("created_at") or ""), reverse=True)


def _active_rows(
    rows: list[dict[str, Any]], *, show_retired: bool
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in rows:
        if not show_retired:
            if not bool(r.get("is_active", True)):
                continue
            if _is_expired(r):
                continue
        out.append(r)
    return out


def _build_upcoming_events(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    events: list[tuple[str, dict[str, Any]]] = []
    now = datetime.now(timezone.utc)
    for r in rows:
        if str(r.get("category") or "").strip() != "Schedule":
            continue
        raw = r.get("expires_at") or r.get("created_at")
        parsed = parse_event_date(raw)
        if not parsed:
            continue
        month, day, iso = parsed
        try:
            dt = datetime.fromisoformat(iso + "T12:00:00").replace(tzinfo=timezone.utc)
            if dt < now.replace(hour=0, minute=0, second=0, microsecond=0):
                continue
        except Exception:
            pass
        events.append(
            (
                iso,
                {
                    "month": month,
                    "day": day,
                    "title": str(r.get("title") or "—")[:56],
                    "time": "All day",
                    "location": "Company",
                },
            )
        )
    events.sort(key=lambda x: x[0])
    return [ev for _, ev in events[:6]]


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


def _clear_filter_keys() -> None:
    st.session_state["cu_sf_search_raw"] = ""
    st.session_state["cu_sf_category"] = "All"
    st.session_state["cu_sf_priority"] = "All"
    st.session_state["cu_kpi_filter"] = "all"
    st.session_state["cu_tab_active"] = "All Updates"
    st.session_state["cu_page"] = 1
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
            _invalidate_cu_cache()
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
                _invalidate_cu_cache()
                st.session_state.pop("cu_admin_modal_id", None)
                st.success("Saved.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
        elif del_sub:
            try:
                delete_rows_admin("company_updates", {"id": sel})
                _invalidate_cu_cache()
                st.session_state.pop("cu_admin_modal_id", None)
                st.success("Deleted.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    if st.button("Cancel", type="secondary", key=f"cu_ed_close_{sel}", use_container_width=True):
        st.session_state.pop("cu_admin_modal_id", None)
        st.rerun()



def _render_cu_tab_bar(active: str) -> None:
    st.markdown('<span class="ips-cu-tab-bar"></span>', unsafe_allow_html=True)
    tab_cols = st.columns(len(DISPLAY_TABS), gap="small")
    for col, tab in zip(tab_cols, DISPLAY_TABS):
        cell_cls = "ips-cu-tab-active" if tab == active else "ips-cu-tab-cell"
        with col:
            st.markdown(f'<span class="{cell_cls}"></span>', unsafe_allow_html=True)
            if st.button(tab, key=f"cu_tab_{tab}", use_container_width=True):
                st.session_state["cu_tab_active"] = tab
                st.session_state["cu_page"] = 1
                st.rerun()


def _render_cu_toolbar() -> None:
    st.markdown('<span class="ips-cu-toolbar-row"></span>', unsafe_allow_html=True)
    sort_c, search_c = st.columns([0.34, 0.66], gap="small")
    with sort_c:
        st.selectbox(
            "Sort by",
            ("Newest First", "Oldest First", "Priority"),
            key="cu_sort",
        )
    with search_c:
        st.text_input(
            "Search updates",
            key="cu_sf_search_raw",
            placeholder="Search updates...",
            label_visibility="collapsed",
        )


def _format_feed_date(raw: Any) -> str:
    s = str(raw or "").strip()
    if not s:
        return "—"
    try:
        if "T" in s:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(s[:10] + "T12:00:00")
        return dt.strftime("%b %d, %Y")
    except Exception:
        return s[:10] if len(s) >= 10 else s


def render() -> None:
    inject_field_light_theme()
    inject_company_updates_page_styles()
    page_marker()

    role = current_role()
    prof = current_profile()
    me = str(prof.get("id") or "").strip()
    sk = me or "anonymous"
    use_admin = _norm_role(role) in ("admin", "manager")
    can_manage = _can_manage_updates(role)

    st.session_state.setdefault("cu_sf_search_raw", "")
    st.session_state.setdefault("cu_sf_category", "All")
    st.session_state.setdefault("cu_sf_priority", "All")
    st.session_state.setdefault("cu_sf_show_retired", False)
    st.session_state.setdefault("cu_tab_active", "All Updates")
    st.session_state.setdefault("cu_sort", "Newest First")
    st.session_state.setdefault("cu_page", 1)
    st.session_state.setdefault("cu_kpi_filter", "all")

    labels = _cached_profile_labels(sk, use_admin)
    rows_all = _cached_load_updates(sk, use_admin)
    read_ids = set(_cached_read_ids(me)) if me else set()

    show_retired = bool(st.session_state.get("cu_sf_show_retired")) and can_manage
    active_rows = _active_rows(rows_all, show_retired=show_retired)

    unread_all = sum(
        1 for r in active_rows if str(r.get("id") or "").strip() not in read_ids
    )
    pinned_all = sum(1 for r in active_rows if _is_pinned(r))
    events_all = len(_build_upcoming_events(active_rows))

    cat_f = str(st.session_state.get("cu_sf_category") or "All")
    pri_f = str(st.session_state.get("cu_sf_priority") or "All")
    q_low = str(st.session_state.get("cu_sf_search_raw") or "").strip().lower()
    tab_active = str(st.session_state.get("cu_tab_active") or "All Updates")
    kpi_filter = str(st.session_state.get("cu_kpi_filter") or "all")
    tab_cats = TAB_TO_CATEGORIES.get(tab_active)

    filtered: list[dict[str, Any]] = []
    for r in active_rows:
        rid = str(r.get("id") or "").strip()
        if tab_cats is not None and str(r.get("category") or "").strip() not in tab_cats:
            continue
        if cat_f != "All" and str(r.get("category") or "").strip() != cat_f:
            continue
        if pri_f != "All" and str(r.get("priority") or "").strip() != pri_f:
            continue
        if kpi_filter == "unread" and rid in read_ids:
            continue
        if kpi_filter == "pinned" and not _is_pinned(r):
            continue
        if q_low:
            blob = (str(r.get("title") or "") + " " + str(r.get("message") or "")).lower()
            if q_low not in blob:
                continue
        filtered.append(r)

    filtered = _sort_updates(filtered, str(st.session_state.get("cu_sort") or "Newest First"))

    total = len(filtered)
    page_size = _PAGE_SIZE
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(1, min(int(st.session_state.get("cu_page") or 1), total_pages))
    st.session_state["cu_page"] = page
    start_ix = (page - 1) * page_size
    page_rows = filtered[start_ix : start_ix + page_size]
    show_start = start_ix + 1 if total else 0
    show_end = min(start_ix + page_size, total)

    modal_id = str(st.session_state.get("cu_admin_modal_id") or "").strip()
    view_id = str(st.session_state.get("cu_view_id") or "").strip()
    post_open = bool(can_manage and st.session_state.get("cu_open_post_dialog"))

    if modal_id and can_manage:
        by_id_all = {str(r.get("id")): r for r in rows_all if str(r.get("id") or "").strip()}
        if modal_id in by_id_all:
            _company_update_admin_dialog(row=dict(by_id_all[modal_id]), sel=modal_id)
    elif view_id:
        by_all = {str(r.get("id")): r for r in rows_all if str(r.get("id") or "").strip()}
        if view_id in by_all:
            _cu_view_dialog(row=dict(by_all[view_id]))
    elif post_open:
        _cu_post_dialog(me=me)

    st.markdown('<span class="ips-cu-header-flat"></span>', unsafe_allow_html=True)
    hdr_l, hdr_r = st.columns([0.68, 0.32], gap="medium")
    with hdr_l:
        render_page_header_html()
    with hdr_r:
        st.markdown('<span class="ips-cu-hdr-actions"></span>', unsafe_allow_html=True)
        act1, act2 = st.columns(2, gap="small")
        with act1:
            if can_manage and st.button(
                "+ New Update", type="primary", use_container_width=True, key="cu_hdr_new"
            ):
                st.session_state["cu_open_post_dialog"] = True
                st.rerun()
            elif not can_manage:
                st.empty()
        with act2:
            with st.popover("🔽 Filters", use_container_width=True):
                st.selectbox("Category", ["All"] + list(_CATEGORIES), key="cu_sf_category")
                st.selectbox("Priority", ["All"] + list(_PRIORITIES), key="cu_sf_priority")
                if can_manage:
                    st.checkbox("Show inactive / expired", key="cu_sf_show_retired")
                if st.button("Clear filters", key="cu_pop_clear", use_container_width=True):
                    _clear_filter_keys()
                    st.rerun()

    st.markdown('<span class="ips-cu-kpi-row"></span>', unsafe_allow_html=True)
    kpi_vals = {
        "unread": unread_all,
        "pinned": pinned_all,
        "events": events_all,
        "all": len(active_rows),
    }
    kpi_links = {
        "unread": "View all",
        "pinned": "View all",
        "events": "View calendar",
        "all": "View all",
    }
    kcols = st.columns(4, gap="small")
    for col, (kpi_key, icon_bg, icon_svg, label) in zip(kcols, KPI_SPECS):
        with col:
            st.markdown(
                kpi_stat_card_html(
                    icon_svg=icon_svg,
                    icon_bg=icon_bg,
                    value=kpi_vals.get(kpi_key, 0),
                    label=label,
                ),
                unsafe_allow_html=True,
            )
            st.markdown('<span class="ips-cu-kpi-link-btn"></span>', unsafe_allow_html=True)
            link_lbl = kpi_links[kpi_key]
            if st.button(link_lbl, key=f"cu_kpi_btn_{kpi_key}", use_container_width=True):
                if kpi_key == "events":
                    st.session_state["cu_tab_active"] = "Events"
                    st.session_state["cu_kpi_filter"] = "all"
                else:
                    st.session_state["cu_kpi_filter"] = kpi_key
                st.session_state["cu_page"] = 1
                st.rerun()

    main_l, main_r = st.columns([0.7, 0.3], gap="medium")

    with main_l:
        with st.container(border=True):
            st.markdown('<span class="ips-cu-feed-panel"></span>', unsafe_allow_html=True)
            tab_row_l, tab_row_r = st.columns([0.58, 0.42], gap="small")
            with tab_row_l:
                _render_cu_tab_bar(tab_active)
            with tab_row_r:
                _render_cu_toolbar()

            if not filtered and not rows_all:
                try:
                    from app.ui.components.empty_states import render_empty_state
                except ImportError:
                    from ui.components.empty_states import render_empty_state  # type: ignore
                if render_empty_state(
                    "No company updates yet",
                    "Post the first announcement for your team.",
                    icon="📢",
                    action_label="Post update",
                    action_key="cu_feed_empty_post",
                ):
                    if can_manage:
                        st.session_state["cu_open_post_dialog"] = True
                        st.rerun()
            elif not filtered:
                try:
                    from app.ui.components.empty_states import render_empty_state
                except ImportError:
                    from ui.components.empty_states import render_empty_state  # type: ignore
                if render_empty_state(
                    "No updates match filters",
                    "Try clearing search or category filters.",
                    icon="🔍",
                    action_label="Clear filters",
                    action_key="cu_feed_empty_clear",
                ):
                    _clear_filter_keys()
                    st.rerun()
            else:
                for r in page_rows:
                    uid = str(r.get("id") or "").strip()
                    if not uid:
                        continue
                    title = str(r.get("title") or "—").strip()
                    body = str(r.get("message") or "")
                    raw_cat = str(r.get("category") or "General").strip()
                    disp_cat = display_category(raw_cat)
                    pri = str(r.get("priority") or "Normal").strip() or "Normal"
                    created = _format_feed_date(r.get("created_at"))
                    is_read = uid in read_ids
                    urgent = pri == "Urgent" or raw_cat == "Urgent"
                    dept = display_department(disp_cat)

                    st.markdown('<span class="ips-cu-feed-item"></span>', unsafe_allow_html=True)
                    card_row_l, card_row_r = st.columns([0.97, 0.03], gap="small")
                    with card_row_l:
                        st.markdown(
                            feed_card_html(
                                title=title,
                                preview=_preview_text(body, 180),
                                display_cat=disp_cat,
                                date_label=created,
                                department=dept,
                                is_pinned=_is_pinned(r),
                                is_read=is_read,
                                urgent=urgent,
                            ),
                            unsafe_allow_html=True,
                        )
                        att = _attachment_display_url(str(r.get("attachment_url") or "").strip() or None)
                        if att:
                            low = att.lower()
                            if low.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
                                st.image(att, use_container_width=True)
                            else:
                                st.markdown(f"[Attachment]({html.escape(att)})", unsafe_allow_html=True)
                    with card_row_r:
                        st.markdown('<span class="ips-cu-feed-menu-col"></span>', unsafe_allow_html=True)
                        with st.popover("⋯", key=f"cu_pop_{uid}"):
                            if st.button("View", key=f"cu_view_{uid}", use_container_width=True):
                                st.session_state["cu_view_id"] = uid
                                st.rerun()
                            if me and not is_read and st.button(
                                "Mark read", key=f"cu_ack_{uid}", use_container_width=True
                            ):
                                try:
                                    insert_row(
                                        "company_update_reads",
                                        {"update_id": uid, "user_id": me},
                                    )
                                except Exception:
                                    pass
                                _invalidate_cu_cache()
                                st.rerun()
                            if can_manage and st.button(
                                "Edit", key=f"cu_edit_{uid}", use_container_width=True
                            ):
                                st.session_state["cu_admin_modal_id"] = uid
                                st.rerun()

            st.markdown(
                f'<div class="ips-cu-pagination">{pagination_info_html(show_start, show_end, total)}</div>',
                unsafe_allow_html=True,
            )
            if total_pages > 1:
                nav_l, nav_pages, nav_r = st.columns([0.12, 0.76, 0.12], gap="small")
                with nav_l:
                    st.markdown('<span class="ips-cu-page-btn"></span>', unsafe_allow_html=True)
                    if st.button("‹", key="cu_page_prev", disabled=page <= 1, use_container_width=True):
                        st.session_state["cu_page"] = page - 1
                        st.rerun()
                with nav_pages:
                    pcols = st.columns(min(total_pages, 7), gap="small")
                    window_start = max(1, min(page - 3, total_pages - 6))
                    window_end = min(total_pages, window_start + 6)
                    for i, pnum in enumerate(range(window_start, window_end + 1)):
                        with pcols[i]:
                            cls = "ips-cu-page-active" if pnum == page else "ips-cu-page-btn"
                            st.markdown(f'<span class="{cls}"></span>', unsafe_allow_html=True)
                            if st.button(str(pnum), key=f"cu_page_{pnum}", use_container_width=True):
                                st.session_state["cu_page"] = pnum
                                st.rerun()
                with nav_r:
                    st.markdown('<span class="ips-cu-page-btn"></span>', unsafe_allow_html=True)
                    if st.button("›", key="cu_page_next", disabled=page >= total_pages, use_container_width=True):
                        st.session_state["cu_page"] = page + 1
                        st.rerun()

    with main_r:
        upcoming = _build_upcoming_events(active_rows)
        with st.container(border=True):
            st.markdown('<span class="ips-cu-sidebar-widget"></span>', unsafe_allow_html=True)
            st.markdown(upcoming_events_widget_html(upcoming), unsafe_allow_html=True)
            cal_l, cal_r = st.columns([0.7, 0.3])
            with cal_r:
                if st.button("View Calendar", key="cu_sidebar_cal", type="secondary"):
                    st.session_state["cu_tab_active"] = "Events"
                    st.session_state["cu_page"] = 1
                    st.rerun()

        with st.container(border=True):
            st.markdown('<span class="ips-cu-sidebar-widget"></span>', unsafe_allow_html=True)
            st.markdown(quick_links_widget_html(), unsafe_allow_html=True)

        recent_items = [
            {
                "title": str(r.get("title") or "—")[:48],
                "date": _format_feed_date(r.get("created_at")),
            }
            for r in active_rows[:5]
        ]
        with st.container(border=True):
            st.markdown('<span class="ips-cu-sidebar-widget"></span>', unsafe_allow_html=True)
            st.markdown(recent_updates_widget_html(recent_items), unsafe_allow_html=True)
            va_l, va_r = st.columns([0.7, 0.3])
            with va_r:
                if st.button("View All", key="cu_sidebar_all", type="secondary"):
                    st.session_state["cu_tab_active"] = "All Updates"
                    st.session_state["cu_kpi_filter"] = "all"
                    st.session_state["cu_page"] = 1
                    st.rerun()
