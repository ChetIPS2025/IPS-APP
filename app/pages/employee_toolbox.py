from __future__ import annotations

import base64
import html
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

# Module-level handle for nested callbacks (e.g. delete confirm). Using this avoids
# UnboundLocalError if an outer scope ever binds the name `st`.
_streamlit = st

try:
    from app.auth import current_role
    from app.branding import render_header
    from app.mobile_ui import IPS_VIEWPORT_NARROW_KEY, ensure_narrow_viewport_detected
    from app.confirm_delete import (
        close_destructive_confirmation,
        destructive_confirm_open_key,
        open_destructive_confirmation,
        render_destructive_confirmation,
    )
    from app.db import (
        create_signed_url,
        delete_rows_admin,
        delete_storage_object_admin,
        fetch_one,
        fetch_table_with_order_fallback,
        insert_row_admin,
        update_rows_admin,
        upload_bytes_admin,
    )
    from app.ips_crud_list_styles import (
        IPS_CRUD_LIST_PAGE_GAP,
        IPS_CRUD_LIST_PAGE_SPLIT,
        inject_ips_crud_list_styles,
    )
    from app.services.asset_document_util import guess_document_content_type
    from app.table_actions import inject_table_action_styles
except ImportError:
    from auth import current_role  # type: ignore
    from branding import render_header  # type: ignore
    from mobile_ui import IPS_VIEWPORT_NARROW_KEY, ensure_narrow_viewport_detected  # type: ignore
    from confirm_delete import (  # type: ignore
        close_destructive_confirmation,
        destructive_confirm_open_key,
        open_destructive_confirmation,
        render_destructive_confirmation,
    )
    from db import (  # type: ignore
        create_signed_url,
        delete_rows_admin,
        delete_storage_object_admin,
        fetch_one,
        fetch_table_with_order_fallback,
        insert_row_admin,
        update_rows_admin,
        upload_bytes_admin,
    )
    from ips_crud_list_styles import (  # type: ignore
        IPS_CRUD_LIST_PAGE_GAP,
        IPS_CRUD_LIST_PAGE_SPLIT,
        inject_ips_crud_list_styles,
    )
    from services.asset_document_util import guess_document_content_type  # type: ignore
    from table_actions import inject_table_action_styles  # type: ignore

_TABLE = "employee_toolbox_links"
_PANEL_MODE_KEY = "employee_toolbox_panel_mode"
_EDIT_ID_KEY = "employee_toolbox_edit_id"
_DELETE_PREFIX = "employee_toolbox_delete"
_PENDING_DELETE_KEY = "employee_toolbox_pending_delete_ids"
_TOOLBOX_STYLE_KEY = "ips_employee_toolbox_styles_injected_v6"

_FETCH_COLUMNS = (
    "id,title,url,description,category,is_active,sort_order,created_at,"
    "resource_type,file_name,original_filename,file_path,content_type"
)

# Allowed extensions for toolbox uploads (lowercase, no dot).
_ALLOWED_TOOLBOX_UPLOAD_EXT: frozenset[str] = frozenset(
    {"pdf", "doc", "docx", "xls", "xlsx", "jpg", "jpeg", "png"}
)
_TOOLBOX_UPLOAD_ACCEPT = ".pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png"
# Streamlit file_uploader: extensions without leading dot
_TOOLBOX_UPLOAD_TYPE_LIST = [x.strip().lstrip(".") for x in _TOOLBOX_UPLOAD_ACCEPT.split(",") if x.strip()]

# Suggested category order for grouping (case-insensitive match); unknown labels sort after these.
_CATEGORY_ORDER: tuple[str, ...] = (
    "HR",
    "Safety",
    "Training",
    "Forms",
    "IT",
    "Operations",
    "General",
)


def _category_display_label(raw: str) -> str:
    """Normalize category for display and grouping (suggested labels + General)."""
    s = str(raw or "").strip()
    if not s:
        return "General"
    lower = s.lower()
    for canon in _CATEGORY_ORDER:
        if canon.lower() == lower:
            return canon
    return s


def _category_section_sort_key(label: str) -> tuple[int, int | str]:
    if label in _CATEGORY_ORDER:
        return (0, _CATEGORY_ORDER.index(label))
    return (1, label.lower())


def _row_sort_key(r: dict) -> tuple:
    lab = _category_display_label(str(r.get("category") or ""))
    return (
        _category_section_sort_key(lab),
        int(r.get("sort_order") or 0),
        str(r.get("title") or "").strip().lower(),
    )


def _is_file_row(row: dict) -> bool:
    rt = str(row.get("resource_type") or "").strip().lower()
    if rt == "file":
        return True
    return bool(str(row.get("file_path") or "").strip())


def _employee_toolbox_assets_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "assets"


# Map normalized titles (see _norm_title_for_brand_lookup) to PNGs under ``assets/``.
_BRAND_TITLE_TO_IMAGE: dict[str, str] = {
    "employee handbook": "ips_employee_handbook.png",
    "contract welder agreement": "ips_welder_service_agreement.png",
    "pipe tap chart": "ips_pipe_tap.png",
    "bolt tap chart bolt torque specs": "ips_bolt_torque.png",
    "#150 flange bolt chart": "ips_flange_150.png",
    "150 flange bolt chart": "ips_flange_150.png",
    "conduit wire fill": "ips_conduit_fill.png",
    "handrail standard": "ips_handrail_standard.png",
    "wire size": "ips_wire_size.png",
    "tap/drill": "ips_tap_drill.png",
    "tap drill": "ips_tap_drill.png",
}


def _norm_title_for_brand_lookup(raw: str) -> str:
    s = " ".join(str(raw or "").split()).strip().lower()
    s = s.replace("/", " ")
    s = " ".join(s.split())
    return s


def _brand_image_path_for_title(title_raw: str) -> Path | None:
    """Return path to a branded tile image when title matches and the file exists on disk."""
    n = _norm_title_for_brand_lookup(title_raw)
    fn = _BRAND_TITLE_TO_IMAGE.get(n)
    if not fn:
        n2 = " ".join(n.replace("#", " ").split())
        n2 = " ".join(n2.split())
        fn = _BRAND_TITLE_TO_IMAGE.get(n2)
    if not fn:
        return None
    p = _employee_toolbox_assets_dir() / fn
    return p if p.is_file() else None


def _image_to_data_uri(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in (".jpg", ".jpeg"):
        mime = "image/jpeg"
    elif ext == ".webp":
        mime = "image/webp"
    else:
        mime = "image/png"
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _toolbox_file_icon(file_name: str) -> str:
    """Fallback tile icons: PDF / Word / Excel / generic file when no branded image."""
    ext = Path(file_name).suffix.lower()
    if ext == ".pdf":
        return "📄"
    if ext in (".doc", ".docx"):
        return "📝"
    if ext in (".xls", ".xlsx"):
        return "📊"
    return "📁"


def _truncate_tile_title(raw: str, *, max_chars: int = 42) -> str:
    """Short, readable label for app-icon tiles."""
    s = " ".join(str(raw or "").split()).strip() or "—"
    if len(s) <= max_chars:
        return s
    return s[: max_chars - 1].rstrip() + "…"


def _normalize_url(url: str) -> str:
    u = " ".join(str(url or "").split()).strip()
    if not u:
        return ""
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", u):
        u = "https://" + u
    return u


def _upload_ext_allowed(raw_name: str) -> bool:
    name = str(raw_name or "").strip()
    if "." not in name:
        return False
    ext = name.rsplit(".", 1)[-1].lower()
    return ext in _ALLOWED_TOOLBOX_UPLOAD_EXT


def _build_toolbox_storage_path(*, original_filename: str) -> str:
    ext = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else "bin"
    tid = uuid.uuid4().hex[:12]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"employee_toolbox/{tid}/{ts}.{ext}"


def _tile_visual_inner_html(
    *,
    title: str,
    desc: str,
    badge: str,
    icon: str,
    can_manage: bool,
    active: bool,
    hint: str,
    brand_image_path: Path | None = None,
) -> str:
    """Inner HTML: branded image or icon (top) → title → category badge → optional one-line desc → hint."""
    if brand_image_path is not None and brand_image_path.is_file():
        try:
            data_uri = _image_to_data_uri(brand_image_path)
            top_html = (
                '<div class="ips-toolbox-tile-thumb">'
                f'<img src="{html.escape(data_uri, quote=True)}" alt="" loading="lazy" />'
                "</div>"
            )
        except OSError:
            top_html = f'<p class="ips-toolbox-tile-icon">{icon}</p>'
    else:
        top_html = f'<p class="ips-toolbox-tile-icon">{icon}</p>'
    parts: list[str] = [
        top_html,
        f'<p class="ips-toolbox-tile-title">{html.escape(title)}</p>',
        f'<div class="ips-toolbox-tile-badges"><span class="ips-toolbox-badge">{html.escape(badge)}</span></div>',
    ]
    if desc:
        short = desc if len(desc) <= 56 else desc[:53] + "…"
        desc_safe = html.escape(short).replace("\n", " ")
        parts.append(f'<p class="ips-toolbox-tile-desc">{desc_safe}</p>')
    if can_manage and not active:
        parts.append('<p class="ips-toolbox-tile-meta">Inactive · hidden from employees</p>')
    if hint:
        parts.append(f'<p class="ips-toolbox-tile-hint">{html.escape(hint)}</p>')
    return "\n".join(parts)


def _tile_tooltip_attr(description: str) -> str:
    """Native browser tooltip (full description); no JS — attribute only."""
    t = str(description or "").strip()
    if not t:
        return ""
    return f' title="{html.escape(t, quote=True)}"'


def _tile_marker_span(*, is_download: bool, has_admin_overlay: bool, interactive: bool) -> str:
    parts = ["ips-toolbox-card", "ips-toolbox-tile"]
    if interactive:
        parts.append("ips-toolbox-tile-interactive")
    if is_download:
        parts.append("ips-toolbox-tile-dl")
        if has_admin_overlay:
            parts.append("ips-toolbox-tile-has-admin")
    return f'<span class="{" ".join(parts)}"></span>'


def _inject_toolbox_hub_styles() -> None:
    if st.session_state.get(_TOOLBOX_STYLE_KEY):
        return
    st.session_state[_TOOLBOX_STYLE_KEY] = True
    st.markdown(
        """
        <style>
        /* App launcher tile shell */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-toolbox-tile) {
            position: relative !important;
            background: rgba(15, 23, 42, 0.68) !important;
            border: 1px solid rgba(71, 85, 105, 0.55) !important;
            border-radius: 16px !important;
            padding: 16px 12px 10px 12px !important;
            margin-bottom: 12px !important;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.045);
            transition: border-color 0.2s ease, box-shadow 0.2s ease, background 0.2s ease,
                transform 0.22s ease !important;
            overflow: hidden;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-toolbox-tile-interactive) {
            cursor: pointer !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-toolbox-tile):not(:has(.ips-toolbox-tile-interactive)) {
            cursor: default !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-toolbox-tile-interactive):hover {
            border-color: rgba(96, 165, 250, 0.65) !important;
            background: rgba(30, 41, 59, 0.88) !important;
            box-shadow:
                inset 0 1px 0 rgba(255, 255, 255, 0.08),
                0 0 0 1px rgba(96, 165, 250, 0.35),
                0 10px 28px rgba(0, 0, 0, 0.32),
                0 0 24px rgba(59, 130, 246, 0.12) !important;
            transform: scale(1.028) translateY(-2px);
            z-index: 4;
            overflow: visible;
        }
        /* Whole-tile link (http/https resources) */
        a.ips-toolbox-tile-link {
            display: block;
            text-decoration: none !important;
            color: inherit !important;
            border-radius: 12px;
            padding: 2px 4px 6px 4px;
            margin: -2px -4px 2px -4px;
            outline: none;
            cursor: pointer !important;
            transition: outline 0.15s ease, background 0.15s ease;
        }
        a.ips-toolbox-tile-link:hover {
            outline: 1px solid rgba(96, 165, 250, 0.45);
            outline-offset: 1px;
            background: rgba(15, 23, 42, 0.25);
        }
        a.ips-toolbox-tile-link:focus-visible {
            outline: 2px solid rgba(96, 165, 250, 0.85);
            outline-offset: 2px;
        }
        div.ips-toolbox-tile-body {
            position: relative;
            z-index: 0;
            min-height: 118px;
        }
        p.ips-toolbox-tile-icon {
            text-align: center;
            font-size: 3.1rem;
            line-height: 1;
            margin: 0 0 12px 0;
            user-select: none;
            filter: drop-shadow(0 2px 4px rgba(0,0,0,0.25));
        }
        div.ips-toolbox-tile-thumb {
            text-align: center;
            margin: 0 0 12px 0;
            min-height: 72px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        div.ips-toolbox-tile-thumb img {
            max-height: 96px;
            max-width: 100%;
            width: auto;
            height: auto;
            object-fit: contain;
            border-radius: 10px;
            filter: drop-shadow(0 2px 8px rgba(0,0,0,0.35));
            user-select: none;
            pointer-events: none;
        }
        p.ips-toolbox-tile-title {
            color: #f8fafc !important;
            font-size: 0.88rem !important;
            font-weight: 650 !important;
            text-align: center;
            margin: 0 0 6px 0 !important;
            line-height: 1.25 !important;
            min-height: 2.35em;
            max-height: 2.55em;
            overflow: hidden;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
        }
        div.ips-toolbox-tile-badges {
            text-align: center;
            margin: 0 0 6px 0;
            line-height: 1.4;
        }
        p.ips-toolbox-tile-desc {
            color: #94a3b8 !important;
            font-size: 0.65rem !important;
            line-height: 1.3 !important;
            text-align: center;
            margin: 0 0 4px 0 !important;
            max-height: 1.35em;
            overflow: hidden;
            white-space: nowrap;
            text-overflow: ellipsis;
        }
        p.ips-toolbox-tile-meta {
            color: #64748b !important;
            font-size: 0.68rem !important;
            text-align: center;
            margin: 0 0 6px 0 !important;
        }
        p.ips-toolbox-tile-hint {
            color: #64748b !important;
            font-size: 0.62rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            text-align: center;
            margin: 6px 0 0 0 !important;
        }
        /* Invisible download hit-area over tile body (local files only) */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-toolbox-tile-dl) div[data-testid="stButton"] {
            position: absolute !important;
            left: 0 !important;
            right: 0 !important;
            top: 0 !important;
            z-index: 2 !important;
            margin: 0 !important;
            padding: 0 !important;
            height: auto !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-toolbox-tile-has-admin) div[data-testid="stButton"] {
            bottom: 52px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-toolbox-tile-dl):not(:has(.ips-toolbox-tile-has-admin)) div[data-testid="stButton"] {
            bottom: 0 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-toolbox-tile-dl) div[data-testid="stButton"] > button {
            position: absolute !important;
            inset: 0 !important;
            width: 100% !important;
            height: 100% !important;
            min-height: 140px !important;
            opacity: 0.03 !important;
            cursor: pointer !important;
            border-radius: 14px !important;
        }
        hr.ips-toolbox-tile-admin-sep {
            margin: 8px 0 6px 0 !important;
            border: none !important;
            border-top: 1px solid rgba(51, 65, 85, 0.5) !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-toolbox-tile) div[data-testid="stHorizontalBlock"] button[kind="secondary"] {
            position: relative !important;
            z-index: 5 !important;
            min-height: 1.85rem !important;
            padding: 0.15rem 0.35rem !important;
            font-size: 0.64rem !important;
            border-radius: 7px !important;
            font-weight: 500 !important;
            opacity: 0.82 !important;
        }
        .ips-toolbox-category {
            color: #94a3b8;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 0.65rem;
            padding-bottom: 0.35rem;
            border-bottom: 1px solid rgba(71, 85, 105, 0.55);
        }
        .ips-toolbox-badge {
            display: inline-block;
            font-size: 0.62rem;
            font-weight: 700;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            padding: 0.2rem 0.5rem;
            border-radius: 999px;
            background: rgba(51, 65, 85, 0.75) !important;
            color: #cbd5e1 !important;
            border: 1px solid rgba(148, 163, 184, 0.32) !important;
            white-space: nowrap;
        }
        @media (max-width: 900px) {
            p.ips-toolbox-tile-icon { font-size: 2.75rem; margin-bottom: 10px; }
            p.ips-toolbox-tile-title { font-size: 0.84rem !important; }
            [data-testid="stMain"] div[data-testid="stHorizontalBlock"]:has(.ips-toolbox-tile) {
                flex-direction: row !important;
                flex-wrap: wrap !important;
                gap: 0.5rem !important;
                align-items: stretch !important;
            }
            [data-testid="stMain"] div[data-testid="stHorizontalBlock"]:has(.ips-toolbox-tile) > div[data-testid="column"] {
                width: calc(50% - 0.25rem) !important;
                max-width: calc(50% - 0.25rem) !important;
                min-width: 0 !important;
                flex: 1 1 calc(50% - 0.25rem) !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _fetch_all_toolbox_rows() -> list[dict]:
    rows = fetch_table_with_order_fallback(
        _TABLE,
        columns=_FETCH_COLUMNS,
        limit=500,
        order_by="sort_order",
    )
    return sorted(rows, key=_row_sort_key)


def _rows_for_viewer(all_rows: list[dict], *, for_admin: bool) -> list[dict]:
    if for_admin:
        return sorted(list(all_rows), key=_row_sort_key)
    return sorted([r for r in all_rows if r.get("is_active", True)], key=_row_sort_key)


def _group_by_category_ordered(rows: list[dict]) -> list[tuple[str, list[dict]]]:
    """Group rows by display category; section order follows _CATEGORY_ORDER then A–Z."""
    if not rows:
        return []
    sorted_rows = sorted(rows, key=_row_sort_key)
    bucket: dict[str, list[dict]] = {}
    for r in sorted_rows:
        lab = _category_display_label(str(r.get("category") or ""))
        bucket.setdefault(lab, []).append(r)
    labels = sorted(bucket.keys(), key=_category_section_sort_key)
    return [(lab, bucket[lab]) for lab in labels]


def _next_sort_order(rows: list[dict]) -> int:
    if not rows:
        return 0
    return max(int(r.get("sort_order") or 0) for r in rows) + 1


def _clear_toolbox_panel() -> None:
    st.session_state.pop(_PANEL_MODE_KEY, None)
    st.session_state.pop(_EDIT_ID_KEY, None)


def _render_add_tool_panel(*, existing_rows: list[dict]) -> None:
    inject_ips_crud_list_styles()
    with st.container(border=True):
        st.markdown('<span class="ips-crud-side-anchor"></span>', unsafe_allow_html=True)
        st.markdown("### Add tool")

        title = st.text_input("Title", key="etb_add_title")
        url = st.text_input("URL", key="etb_add_url", placeholder="https://…")
        description = st.text_area("Description", key="etb_add_desc", height=88)
        cat_col = st.text_input(
            "Category",
            key="etb_add_cat",
            placeholder="HR, Safety, Training, Forms, IT, Operations, or custom",
            help="Used for grouping on the page. Matches suggested labels when possible.",
        )
        so_default = _next_sort_order(existing_rows)
        sort_order = st.number_input(
            "Sort order",
            min_value=0,
            value=int(so_default),
            step=1,
            key="etb_add_sort",
            help="Lower numbers appear first within a category.",
        )
        is_active = st.checkbox("Active", value=True, key="etb_add_active")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Save Tool", type="primary", use_container_width=True, key="etb_add_save"):
                t = str(title or "").strip()
                raw_url = str(url or "").strip()
                nu = _normalize_url(raw_url)
                if not nu:
                    st.error("URL is required.")
                    st.stop()
                if not t:
                    st.error("Title is required.")
                    st.stop()
                cat_raw = str(cat_col or "").strip()
                if not cat_raw:
                    cat_db = ""
                else:
                    lab = _category_display_label(cat_raw)
                    cat_db = "" if lab == "General" else lab
                payload = {
                    "title": t,
                    "url": nu,
                    "resource_type": "link",
                    "description": str(description or "").strip(),
                    "category": cat_db,
                    "is_active": bool(is_active),
                    "sort_order": int(sort_order),
                }
                try:
                    insert_row_admin(_TABLE, payload)
                except Exception as exc:
                    st.error(f"Could not save: {exc}")
                    st.stop()
                _clear_toolbox_panel()
                st.success("Tool saved.")
                st.rerun()
        with c2:
            if st.button("Cancel", use_container_width=True, key="etb_add_cancel"):
                _clear_toolbox_panel()
                st.rerun()


def _render_upload_document_panel(*, existing_rows: list[dict]) -> None:
    inject_ips_crud_list_styles()
    with st.container(border=True):
        st.markdown('<span class="ips-crud-side-anchor"></span>', unsafe_allow_html=True)
        st.markdown("### Upload document")

        title = st.text_input("Title", key="etb_upload_title")
        cat_col = st.text_input(
            "Category",
            key="etb_upload_cat",
            placeholder="HR, Safety, Training, Forms, IT, Operations, or custom",
            help="Used for grouping on the page.",
        )
        description = st.text_area("Description", key="etb_upload_desc", height=88)
        uploaded = st.file_uploader(
            "File",
            type=_TOOLBOX_UPLOAD_TYPE_LIST,
            key="etb_upload_file",
            help=f"Allowed types: {_TOOLBOX_UPLOAD_ACCEPT}",
        )
        so_default = _next_sort_order(existing_rows)
        sort_order = st.number_input(
            "Sort order",
            min_value=0,
            value=int(so_default),
            step=1,
            key="etb_upload_sort",
            help="Lower numbers appear first within a category.",
        )
        is_active = st.checkbox("Active", value=True, key="etb_upload_active")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Save Document", type="primary", use_container_width=True, key="etb_upload_save"):
                t = str(title or "").strip()
                if not t:
                    st.error("Title is required.")
                    st.stop()
                if uploaded is None:
                    st.error("Please choose a file to upload.")
                    st.stop()
                raw_name = str(getattr(uploaded, "name", "") or "").strip() or "upload.bin"
                if not _upload_ext_allowed(raw_name):
                    st.error("Unsupported file type. Use PDF, Word, Excel, or common image types.")
                    st.stop()
                data = uploaded.getvalue()
                st_type = getattr(uploaded, "type", None)
                content_type = guess_document_content_type(
                    raw_name,
                    st_type if isinstance(st_type, str) else None,
                )
                storage_path = _build_toolbox_storage_path(original_filename=raw_name)
                cat_raw = str(cat_col or "").strip()
                if not cat_raw:
                    cat_db = ""
                else:
                    lab = _category_display_label(cat_raw)
                    cat_db = "" if lab == "General" else lab
                try:
                    upload_bytes_admin(storage_path, data, content_type=content_type)
                except Exception as exc:
                    st.error(f"Could not upload file: {exc}")
                    st.stop()
                payload = {
                    "title": t,
                    "url": None,
                    "resource_type": "file",
                    "description": str(description or "").strip(),
                    "category": cat_db,
                    "is_active": bool(is_active),
                    "sort_order": int(sort_order),
                    "file_name": raw_name,
                    "original_filename": raw_name,
                    "file_path": storage_path,
                    "content_type": content_type,
                }
                try:
                    insert_row_admin(_TABLE, payload)
                except Exception as exc:
                    try:
                        delete_storage_object_admin(storage_path)
                    except Exception:
                        pass
                    st.error(f"Could not save: {exc}")
                    st.stop()
                _clear_toolbox_panel()
                st.success("Document saved.")
                st.rerun()
        with c2:
            if st.button("Cancel", use_container_width=True, key="etb_upload_cancel"):
                _clear_toolbox_panel()
                st.rerun()


def _render_edit_link_panel(*, row: dict, existing_rows: list[dict]) -> None:
    rid = str(row.get("id") or "")
    pk = f"etb_ed_{rid}"
    with st.container(border=True):
        st.markdown('<span class="ips-crud-side-anchor"></span>', unsafe_allow_html=True)
        st.markdown("### Edit tool")
        st.caption(f"ID `{rid[:8]}…`")

        title = st.text_input("Title", value=str(row.get("title") or ""), key=f"{pk}_title")
        url = st.text_input("URL", value=str(row.get("url") or ""), key=f"{pk}_url")
        description = st.text_area(
            "Description",
            value=str(row.get("description") or ""),
            height=88,
            key=f"{pk}_desc",
        )
        category = st.text_input(
            "Category",
            value=str(row.get("category") or ""),
            key=f"{pk}_cat",
            placeholder="HR, Safety, Training, Forms, IT, Operations, General",
            help="Suggested: HR, Safety, Training, Forms, IT, Operations. Leave blank for General.",
        )
        sort_order = st.number_input(
            "Sort order",
            min_value=0,
            value=int(row.get("sort_order") or 0),
            step=1,
            key=f"{pk}_sort",
            help="Lower numbers appear first within a category.",
        )
        is_active = st.checkbox("Active", value=bool(row.get("is_active", True)), key=f"{pk}_active")

        u1, u2 = st.columns(2)
        with u1:
            if st.button("Update Tool", type="primary", use_container_width=True, key=f"{pk}_save"):
                t = str(title or "").strip()
                raw_url = str(url or "").strip()
                nu = _normalize_url(raw_url)
                if not nu:
                    st.error("URL is required.")
                    st.stop()
                if not t:
                    st.error("Title is required.")
                    st.stop()
                cat_raw = str(category or "").strip()
                lab = _category_display_label(cat_raw)
                cat_db = "" if lab == "General" else lab
                payload = {
                    "title": t,
                    "url": nu,
                    "resource_type": "link",
                    "description": str(description or "").strip(),
                    "category": cat_db,
                    "is_active": bool(is_active),
                    "sort_order": int(sort_order),
                }
                try:
                    update_rows_admin(_TABLE, payload, {"id": row["id"]})
                except Exception as exc:
                    st.error(f"Could not update: {exc}")
                    st.stop()
                _clear_toolbox_panel()
                st.success("Tool updated.")
                st.rerun()
        with u2:
            if st.button("Cancel", use_container_width=True, key=f"{pk}_cancel"):
                _clear_toolbox_panel()
                st.rerun()


def _render_edit_file_panel(*, row: dict, existing_rows: list[dict]) -> None:
    _ = existing_rows
    rid = str(row.get("id") or "")
    pk = f"etb_ed_{rid}"
    with st.container(border=True):
        st.markdown('<span class="ips-crud-side-anchor"></span>', unsafe_allow_html=True)
        st.markdown("### Edit document")
        st.caption(f"ID `{rid[:8]}…`")

        ofn = str(row.get("original_filename") or row.get("file_name") or "").strip() or "—"
        st.caption(f"Current file: **{html.escape(ofn)}**")

        title = st.text_input("Title", value=str(row.get("title") or ""), key=f"{pk}_title")
        category = st.text_input(
            "Category",
            value=str(row.get("category") or ""),
            key=f"{pk}_cat",
            placeholder="HR, Safety, Training, Forms, IT, Operations, General",
        )
        description = st.text_area(
            "Description",
            value=str(row.get("description") or ""),
            height=88,
            key=f"{pk}_desc",
        )
        replace = st.file_uploader(
            "Replace file (optional)",
            type=_TOOLBOX_UPLOAD_TYPE_LIST,
            key=f"{pk}_replace",
            help="Leave empty to keep the existing file.",
        )
        sort_order = st.number_input(
            "Sort order",
            min_value=0,
            value=int(row.get("sort_order") or 0),
            step=1,
            key=f"{pk}_sort",
        )
        is_active = st.checkbox("Active", value=bool(row.get("is_active", True)), key=f"{pk}_active")

        u1, u2 = st.columns(2)
        with u1:
            if st.button("Save Document", type="primary", use_container_width=True, key=f"{pk}_save"):
                t = str(title or "").strip()
                if not t:
                    st.error("Title is required.")
                    st.stop()
                cat_raw = str(category or "").strip()
                lab = _category_display_label(cat_raw)
                cat_db = "" if lab == "General" else lab
                old_path = str(row.get("file_path") or "").strip()
                payload: dict = {
                    "title": t,
                    "description": str(description or "").strip(),
                    "category": cat_db,
                    "is_active": bool(is_active),
                    "sort_order": int(sort_order),
                    "resource_type": "file",
                    "url": None,
                }
                if replace is not None:
                    raw_name = str(getattr(replace, "name", "") or "").strip() or "upload.bin"
                    if not _upload_ext_allowed(raw_name):
                        st.error("Unsupported file type. Use PDF, Word, Excel, or common image types.")
                        st.stop()
                    data = replace.getvalue()
                    st_type = getattr(replace, "type", None)
                    content_type = guess_document_content_type(
                        raw_name,
                        st_type if isinstance(st_type, str) else None,
                    )
                    storage_path = _build_toolbox_storage_path(original_filename=raw_name)
                    try:
                        upload_bytes_admin(storage_path, data, content_type=content_type)
                    except Exception as exc:
                        st.error(f"Could not upload file: {exc}")
                        st.stop()
                    payload.update(
                        {
                            "file_name": raw_name,
                            "original_filename": raw_name,
                            "file_path": storage_path,
                            "content_type": content_type,
                        }
                    )
                    try:
                        update_rows_admin(_TABLE, payload, {"id": row["id"]})
                    except Exception as exc:
                        try:
                            delete_storage_object_admin(storage_path)
                        except Exception:
                            pass
                        st.error(f"Could not update: {exc}")
                        st.stop()
                    if old_path and old_path != storage_path:
                        try:
                            delete_storage_object_admin(old_path)
                        except Exception:
                            pass
                else:
                    try:
                        update_rows_admin(_TABLE, payload, {"id": row["id"]})
                    except Exception as exc:
                        st.error(f"Could not update: {exc}")
                        st.stop()
                _clear_toolbox_panel()
                st.success("Document updated.")
                st.rerun()
        with u2:
            if st.button("Cancel", use_container_width=True, key=f"{pk}_cancel"):
                _clear_toolbox_panel()
                st.rerun()


def _render_edit_tool_panel(*, row: dict, existing_rows: list[dict]) -> None:
    if _is_file_row(row):
        _render_edit_file_panel(row=row, existing_rows=existing_rows)
    else:
        _render_edit_link_panel(row=row, existing_rows=existing_rows)


def _render_tool_tile(row: dict, *, can_manage: bool) -> None:
    """App-launcher tile: whole-tile open/link, overlay download, small admin actions."""
    title_raw = str(row.get("title") or "—").strip() or "—"
    title = _truncate_tile_title(title_raw)
    desc = str(row.get("description") or "").strip()
    url = str(row.get("url") or "").strip()
    rid = str(row.get("id") or "")
    active = bool(row.get("is_active", True))
    badge = _category_display_label(str(row.get("category") or ""))
    is_file = _is_file_row(row)
    fp = str(row.get("file_path") or "").strip()
    fn_display = (
        str(row.get("original_filename") or row.get("file_name") or "").strip() or Path(fp).name or "document"
    )
    icon = _toolbox_file_icon(fn_display) if is_file else "🔗"
    brand_path = _brand_image_path_for_title(title_raw)

    ref = ""
    use_dl_overlay = False
    interactive = False
    if is_file and fp:
        ref = create_signed_url(fp, expires_in=3600) or ""
        if ref:
            if ref.startswith("http://") or ref.startswith("https://"):
                interactive = True
            elif Path(ref).is_file():
                interactive = True
                use_dl_overlay = True
    elif url.strip():
        interactive = True

    tip = _tile_tooltip_attr(desc)

    with st.container(border=True):
        st.markdown(
            _tile_marker_span(
                is_download=use_dl_overlay,
                has_admin_overlay=bool(use_dl_overlay and can_manage),
                interactive=interactive,
            ),
            unsafe_allow_html=True,
        )

        if is_file:
            if not ref:
                inner = _tile_visual_inner_html(
                    title=title,
                    desc=desc,
                    badge=badge,
                    icon=icon,
                    can_manage=can_manage,
                    active=active,
                    hint="",
                    brand_image_path=brand_path,
                )
                st.markdown(f'<div class="ips-toolbox-tile-body"{tip}>{inner}</div>', unsafe_allow_html=True)
                st.markdown('<p class="ips-toolbox-tile-meta">File unavailable</p>', unsafe_allow_html=True)
            elif ref.startswith("http://") or ref.startswith("https://"):
                safe_href = html.escape(ref, quote=True)
                inner = _tile_visual_inner_html(
                    title=title,
                    desc=desc,
                    badge=badge,
                    icon=icon,
                    can_manage=can_manage,
                    active=active,
                    hint="Open",
                    brand_image_path=brand_path,
                )
                st.markdown(
                    f'<a class="ips-toolbox-tile-link" href="{safe_href}" target="_blank" rel="noopener noreferrer"{tip}>'
                    f'<div class="ips-toolbox-tile-body">{inner}</div></a>',
                    unsafe_allow_html=True,
                )
            else:
                p = Path(ref)
                if p.is_file():
                    inner = _tile_visual_inner_html(
                        title=title,
                        desc=desc,
                        badge=badge,
                        icon=icon,
                        can_manage=can_manage,
                        active=active,
                        hint="Download",
                        brand_image_path=brand_path,
                    )
                    st.markdown(f'<div class="ips-toolbox-tile-body"{tip}>{inner}</div>', unsafe_allow_html=True)
                    ctype = str(row.get("content_type") or "").strip() or "application/octet-stream"
                    st.download_button(
                        " ",
                        data=p.read_bytes(),
                        file_name=fn_display,
                        mime=ctype,
                        type="primary",
                        use_container_width=True,
                        key=f"etb_dl_{rid}",
                        help=desc if desc else None,
                    )
                else:
                    inner = _tile_visual_inner_html(
                        title=title,
                        desc=desc,
                        badge=badge,
                        icon=icon,
                        can_manage=can_manage,
                        active=active,
                        hint="",
                        brand_image_path=brand_path,
                    )
                    st.markdown(f'<div class="ips-toolbox-tile-body"{tip}>{inner}</div>', unsafe_allow_html=True)
                    st.markdown('<p class="ips-toolbox-tile-meta">Missing file</p>', unsafe_allow_html=True)
        elif url:
            nu = _normalize_url(url)
            safe_href = html.escape(nu, quote=True)
            inner = _tile_visual_inner_html(
                title=title,
                desc=desc,
                badge=badge,
                icon=icon,
                can_manage=can_manage,
                active=active,
                hint="Open",
                brand_image_path=brand_path,
            )
            st.markdown(
                f'<a class="ips-toolbox-tile-link" href="{safe_href}" target="_blank" rel="noopener noreferrer"{tip}>'
                f'<div class="ips-toolbox-tile-body">{inner}</div></a>',
                unsafe_allow_html=True,
            )
        else:
            inner = _tile_visual_inner_html(
                title=title,
                desc=desc,
                badge=badge,
                icon=icon,
                can_manage=can_manage,
                active=active,
                hint="",
                brand_image_path=brand_path,
            )
            st.markdown(f'<div class="ips-toolbox-tile-body"{tip}>{inner}</div>', unsafe_allow_html=True)
            st.markdown('<p class="ips-toolbox-tile-meta">No URL</p>', unsafe_allow_html=True)

        if can_manage:
            st.markdown(
                '<hr class="ips-toolbox-tile-admin-sep" />',
                unsafe_allow_html=True,
            )
            e1, e2 = st.columns(2, gap="small")
            with e1:
                if st.button("Edit", type="secondary", use_container_width=True, key=f"etb_edit_{rid}"):
                    st.session_state[_PANEL_MODE_KEY] = "edit"
                    st.session_state[_EDIT_ID_KEY] = rid
                    st.rerun()
            with e2:
                if st.button("Delete", type="secondary", use_container_width=True, key=f"etb_del_{rid}"):
                    open_destructive_confirmation(_DELETE_PREFIX)
                    st.session_state[_PENDING_DELETE_KEY] = [rid]
                    st.rerun()


def _render_tools_hub(rows: list[dict], *, can_manage: bool) -> None:
    if not rows:
        st.info("No toolbox resources yet. Admins can add links with **Add Tool** or upload files with **Upload Document**.")
        return

    _inject_toolbox_hub_styles()
    ensure_narrow_viewport_detected()
    is_narrow = bool(st.session_state.get(IPS_VIEWPORT_NARROW_KEY, False))
    ncols = 2 if is_narrow else 4

    st.markdown("##### Resource hub")
    st.caption(
        "Grouped by category — **tap the tile** to open a link or cloud document; **local files** use a full-tile "
        "download target. Admins: **Edit** / **Delete** below each tile. Signed URLs expire after about one hour."
    )

    for i, (cat_label, group) in enumerate(_group_by_category_ordered(rows)):
        margin = "0.25rem" if i == 0 else "1.25rem"
        st.markdown(
            f'<div class="ips-toolbox-category" style="margin-top:{margin};">'
            f"{html.escape(cat_label)}</div>",
            unsafe_allow_html=True,
        )
        for j in range(0, len(group), ncols):
            chunk = group[j : j + ncols]
            cols = st.columns(ncols, gap="medium")
            for k, row in enumerate(chunk):
                with cols[k]:
                    _render_tool_tile(row, can_manage=can_manage)


def render() -> None:
    render_header("Employee Toolbox")
    st.caption("Industrial Plant Solutions, LLC — curated links and documents for everyday work.")

    can_manage = current_role() == "admin"
    panel_mode = st.session_state.get(_PANEL_MODE_KEY)
    edit_id = st.session_state.get(_EDIT_ID_KEY)

    try:
        all_rows = _fetch_all_toolbox_rows()
    except Exception:
        st.warning(
            "Toolbox storage is not available yet. Run migrations **`sql/013_employee_toolbox_links.sql`** "
            "and **`sql/014_employee_toolbox_resource_files.sql`** in the Supabase SQL editor, then refresh."
        )
        return

    display_rows = _rows_for_viewer(all_rows, for_admin=can_manage)

    inject_table_action_styles()
    inject_ips_crud_list_styles()

    _del_open = destructive_confirm_open_key(_DELETE_PREFIX)
    if st.session_state.get(_del_open) and not can_manage:
        close_destructive_confirmation(_DELETE_PREFIX)
        st.session_state.pop(_PENDING_DELETE_KEY, None)
    elif st.session_state.get(_del_open) and can_manage:
        pending = list(st.session_state.get(_PENDING_DELETE_KEY) or [])
        if not pending:
            close_destructive_confirmation(_DELETE_PREFIX)
            st.session_state.pop(_PENDING_DELETE_KEY, None)
            st.rerun()

        id_to_title: dict[str, str] = {}
        for r in all_rows:
            id_to_title[str(r.get("id"))] = str(r.get("title") or "").strip() or str(r.get("id"))

        name_lines = [id_to_title.get(pid, pid[:10] + "…") for pid in pending]
        n_pending = len(pending)
        msg = (
            "Delete this toolbox resource? This cannot be undone."
            if n_pending == 1
            else f"Delete these {n_pending} toolbox resources? This cannot be undone."
        )

        def _on_confirm_delete() -> None:
            for lid in pending:
                row = fetch_one(_TABLE, {"id": lid})
                fp = str(row.get("file_path") or "").strip() if row else ""
                is_file = bool(row and _is_file_row(row) and fp)
                try:
                    delete_rows_admin(_TABLE, {"id": lid})
                except Exception as exc:
                    _streamlit.error(f"Could not delete {lid}: {exc}")
                    continue
                if is_file:
                    try:
                        delete_storage_object_admin(fp)
                    except Exception as exc:
                        _streamlit.warning(f"Could not remove stored file for {lid}: {exc}")
            _streamlit.session_state.pop(_PENDING_DELETE_KEY, None)
            eid = _streamlit.session_state.get(_EDIT_ID_KEY)
            if eid and str(eid) in {str(x) for x in pending}:
                _clear_toolbox_panel()
            _streamlit.success("Deleted where permitted.")

        def _on_cancel_delete() -> None:
            _streamlit.session_state.pop(_PENDING_DELETE_KEY, None)

        render_destructive_confirmation(
            key_prefix=_DELETE_PREFIX,
            title="Confirm Delete",
            message=msg,
            confirm_label="Delete",
            cancel_label="Cancel",
            on_confirm=_on_confirm_delete,
            on_cancel=_on_cancel_delete,
            name_lines=name_lines,
        )

    edit_row: dict | None = None
    if can_manage and panel_mode == "edit" and edit_id:
        edit_row = fetch_one(_TABLE, {"id": edit_id})
        if not edit_row:
            _clear_toolbox_panel()
            st.rerun()

    panel_add = bool(can_manage and panel_mode == "add")
    panel_upload = bool(can_manage and panel_mode == "upload")
    panel_edit = bool(can_manage and panel_mode == "edit" and edit_row)
    panel_open = panel_add or panel_upload or panel_edit

    if can_manage:
        with st.container(border=True):
            st.markdown(
                '<span class="ips-list-top-anchor ips-estimate-topbar"></span>',
                unsafe_allow_html=True,
            )
            ac1, ac2, ac3 = st.columns([1, 1, 3])
            with ac1:
                if st.button(
                    "Add Tool",
                    type="primary",
                    use_container_width=True,
                    key="etb_header_add",
                    disabled=panel_open,
                ):
                    _clear_toolbox_panel()
                    st.session_state[_PANEL_MODE_KEY] = "add"
                    st.rerun()
            with ac2:
                if st.button(
                    "Upload Document",
                    type="primary",
                    use_container_width=True,
                    key="etb_header_upload",
                    disabled=panel_open,
                ):
                    _clear_toolbox_panel()
                    st.session_state[_PANEL_MODE_KEY] = "upload"
                    st.rerun()
            with ac3:
                if panel_add:
                    st.caption("Use the panel on the right — **Save Tool** or **Cancel**.")
                elif panel_upload:
                    st.caption("Use the panel on the right — **Save Document** or **Cancel**.")
                elif panel_edit:
                    st.caption("Edit on the right — **Update Tool** / **Save Document** or **Cancel**.")
                else:
                    st.caption(
                        "Suggested categories: **HR**, **Safety**, **Training**, **Forms**, **IT**, **Operations**."
                    )

    if panel_open:
        main_col, side_col = st.columns(IPS_CRUD_LIST_PAGE_SPLIT, gap=IPS_CRUD_LIST_PAGE_GAP)
        with main_col:
            _render_tools_hub(display_rows, can_manage=can_manage)
        with side_col:
            if panel_add:
                _render_add_tool_panel(existing_rows=all_rows)
            elif panel_upload:
                _render_upload_document_panel(existing_rows=all_rows)
            elif panel_edit and edit_row:
                _render_edit_tool_panel(row=edit_row, existing_rows=all_rows)
    else:
        _render_tools_hub(display_rows, can_manage=can_manage)

    if not can_manage:
        st.caption("Need something added? Contact an administrator.")
