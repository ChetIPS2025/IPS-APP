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
_TOOLBOX_STYLE_KEY = "ips_employee_toolbox_styles_injected_v12"

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


# Optional absolute path (e.g. Cursor / Linux sandboxes). Checked before ``app/assets/``.
_TOOLBOX_MNT_DATA_DIR = Path("/mnt/data")
# Combined IPS icon sheet (fallback when a mapped per-title PNG is missing).
_COMBINED_ICON_SHEET_FILENAME = "894fdc1c-9c41-45b4-94a1-fcf7942c928d.png"


def _toolbox_brand_asset_search_roots() -> tuple[Path, ...]:
    """Search order for branded PNGs: ``/mnt/data`` (when present), then ``app/assets``."""
    roots: list[Path] = []
    try:
        if _TOOLBOX_MNT_DATA_DIR.is_dir():
            roots.append(_TOOLBOX_MNT_DATA_DIR)
    except OSError:
        pass
    app_assets = _employee_toolbox_assets_dir()
    if app_assets not in roots:
        roots.append(app_assets)
    return tuple(roots)


def _resolve_toolbox_brand_image(filename: str) -> Path | None:
    """First existing ``filename`` under :func:`_toolbox_brand_asset_search_roots`."""
    fn = str(filename or "").strip()
    if not fn or "/" in fn or "\\" in fn:
        return None
    for root in _toolbox_brand_asset_search_roots():
        p = root / fn
        try:
            if p.is_file():
                return p
        except OSError:
            continue
    return None


def _combined_icon_sheet_path() -> Path | None:
    """Optional sprite sheet used when a specific mapped PNG is not on disk."""
    return _resolve_toolbox_brand_image(_COMBINED_ICON_SHEET_FILENAME)


# Map normalized titles (see _norm_title_for_brand_lookup) to basenames in ``/mnt/data`` or ``app/assets``.
_BRAND_TITLE_TO_IMAGE: dict[str, str] = {
    "employee handbook": "ips_employee_handbook.png",
    "contract welder agreement": "ips_welder_service_agreement.png",
    "pipe tap chart": "ips_pipe_tap.png",
    "pipe tap": "ips_pipe_tap.png",
    "bolt tap chart bolt torque specs": "ips_bolt_torque.png",
    "#150 flange bolt chart": "ips_flange_150.png",
    "150 flange bolt chart": "ips_flange_150.png",
    "#300 flange bolt chart": "ips_flange_300.png",
    "300 flange bolt chart": "ips_flange_300.png",
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
    """
    Resolve branded artwork: title → basename, then search ``/mnt/data`` then ``app/assets``.

    * ``ips_flange_300.png``: if missing, use ``ips_flange_150.png`` (closest flange) from the same search order.
    * If the mapped PNG is still missing, use the combined icon sheet when present.
    """
    n = _norm_title_for_brand_lookup(title_raw)
    fn = _BRAND_TITLE_TO_IMAGE.get(n)
    if not fn:
        n2 = " ".join(n.replace("#", " ").split())
        n2 = " ".join(n2.split())
        fn = _BRAND_TITLE_TO_IMAGE.get(n2)
    if not fn and "pipe tap" in n:
        fn = _BRAND_TITLE_TO_IMAGE.get("pipe tap chart") or _BRAND_TITLE_TO_IMAGE.get("pipe tap")
    if not fn:
        if "300" in n and "flange" in n and "bolt" in n:
            fn = "ips_flange_300.png"
    if not fn:
        return None

    p = _resolve_toolbox_brand_image(fn)
    if p is not None:
        return p
    if fn == "ips_flange_300.png":
        p150 = _resolve_toolbox_brand_image("ips_flange_150.png")
        if p150 is not None:
            return p150
    return _combined_icon_sheet_path()


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


def _toolbox_document_title_two_lines(raw: str) -> tuple[str, str | None]:
    """
    Split a document title into one or two plain-text lines (tile + download overlay).

    Explicit ``\\n`` forces a two-line split. Otherwise two or more words: first ``ceil(n/2)``
    words on line 1, remainder on line 2.
    """
    s0 = str(raw or "").strip()
    if not s0:
        return ("—", None)
    if "\n" in s0:
        a, b = s0.split("\n", 1)
        a, b = a.strip(), b.strip()
        if a and b:
            return (a, b)
        s = " ".join((a or b).split()).strip()
    else:
        s = " ".join(s0.split()).strip()
    if not s:
        return ("—", None)
    words = s.split()
    n = len(words)
    if n == 1:
        w = words[0]
        if len(w) <= 16:
            return (w, None)
        cut = max(8, min(len(w) // 2 + 2, len(w) - 3))
        a, b = w[:cut].rstrip("-_ "), w[cut:].lstrip("-_ ")
        return (a or w, b or None)
    split_i = (n + 1) // 2
    line1 = " ".join(words[:split_i]).strip()
    line2 = " ".join(words[split_i:]).strip()
    return (line1, line2 or None)


def _build_tile_title_inner_html(raw: str) -> str:
    """Escaped HTML for ``<p class=\"ips-toolbox-launcher-title\">`` (1–2 lines, ``<br/>``, bold via CSS)."""
    a, b = _toolbox_document_title_two_lines(raw)
    out = html.escape(a)
    if b:
        out += f"<br/>{html.escape(b)}"
    return f"<strong>{out}</strong>"


def _truncate_overlay_button_line(s: str, *, max_len: int = 28) -> str:
    t = " ".join(str(s or "").split()).strip()
    if len(t) <= max_len:
        return t
    return t[: max(1, max_len - 1)].rstrip() + "…"


def _download_overlay_button_label(*, title_raw: str, file_fallback: str) -> str:
    """Visible label on the full-tile download overlay — preserves file name casing."""
    base = str(title_raw or "").strip() or str(file_fallback or "").strip() or "Document"
    a, b = _toolbox_document_title_two_lines(base)
    la = _truncate_overlay_button_line(a, max_len=30)
    if b:
        lb = _truncate_overlay_button_line(b, max_len=30)
        return f"{la}\n{lb}"
    return _truncate_overlay_button_line(la, max_len=34)


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
    title_inner_html: str,
    desc: str,
    badge: str,
    icon: str,
    can_manage: bool,
    active: bool,
    hint: str,
    brand_image_path: Path | None = None,
) -> tuple[str, bool]:
    """Branded: full-bleed image as button surface + footer title. Fallback: compact emoji tile.

    ``title_inner_html`` must be **pre-escaped** HTML (may include ``<br/>`` for a second line).

    Returns ``(html, full_bleed_brand)`` for matching outer tile padding / marker classes.
    """
    _ = badge, hint, desc  # full text stays on outer tooltip / Streamlit help where applicable
    has_brand_file = brand_image_path is not None and brand_image_path.is_file()
    if has_brand_file:
        try:
            data_uri = _image_to_data_uri(brand_image_path)
            parts = [
                '<div class="ips-toolbox-launcher-stack ips-toolbox-launcher-stack--fullbleed">',
                '<div class="ips-toolbox-fullbleed-media">',
                f'<img src="{html.escape(data_uri, quote=True)}" alt="" loading="lazy" />',
                "</div>",
                '<div class="ips-toolbox-launcher-footer">',
                f'<p class="ips-toolbox-launcher-title">{title_inner_html}</p>',
            ]
            if can_manage and not active:
                parts.append('<p class="ips-toolbox-tile-meta ips-toolbox-tile-meta--compact">Hidden</p>')
            parts.extend(["</div>", "</div>"])
            return "\n".join(parts), True
        except OSError:
            pass

    icon_block = (
        '<div class="ips-toolbox-launcher-icon-wrap ips-toolbox-launcher-icon-wrap--fallback">'
        f'<p class="ips-toolbox-tile-icon">{icon}</p></div>'
    )
    stack_cls = "ips-toolbox-launcher-stack ips-toolbox-launcher-stack--fallback"
    parts: list[str] = [
        f'<div class="{stack_cls}">',
        icon_block,
        f'<p class="ips-toolbox-launcher-title">{title_inner_html}</p>',
    ]
    if can_manage and not active:
        parts.append('<p class="ips-toolbox-tile-meta ips-toolbox-tile-meta--compact">Hidden</p>')
    parts.append("</div>")
    return "\n".join(parts), False


def _tile_tooltip_attr(description: str) -> str:
    """Native browser tooltip (full description); no JS — attribute only."""
    t = str(description or "").strip()
    if not t:
        return ""
    return f' title="{html.escape(t, quote=True)}"'


def _toolbox_tile_tip(*, desc: str, action: str = "") -> str:
    """Tooltip: description plus optional action hint (Open / Download) since on-tile hints were removed."""
    d = " ".join(str(desc or "").split()).strip()
    a = str(action or "").strip()
    if d and a:
        return _tile_tooltip_attr(f"{d} ({a})")
    if d:
        return _tile_tooltip_attr(d)
    return _tile_tooltip_attr(a)


def _strip_pdf_extension(text: str) -> str:
    return re.sub(r"\.pdf$", "", str(text or "").strip(), flags=re.IGNORECASE).strip()


# Longer keys first so specific matches win over generic substrings.
_PRETTY_TITLE_RULES: tuple[tuple[str, str], ...] = (
    ("#300 flange bolt chart", "#300 Flange Bolt Chart"),
    ("300 flange bolt chart", "#300 Flange Bolt Chart"),
    ("#150 flange bolt chart", "#150 Flange Bolt Chart"),
    ("150 flange bolt chart", "#150 Flange Bolt Chart"),
    ("flange bolt chart", "#150 Flange Bolt Chart"),
    ("bolt torque", "Bolt Torque Guide"),
    ("bolt tap chart", "Bolt Tap Chart"),
    ("pipe tap chart", "Pipe Tap Chart"),
    ("pipe tap", "Pipe Tap Chart"),
    ("contract welder", "Contract / Welding"),
    ("welder service agreement", "Contract / Welding"),
    ("welder service", "Contract / Welding"),
    ("employee handbook", "Employee Handbook"),
    ("conduit wire fill", "Conduit Wire Fill"),
    ("handrail standard", "Handrail Standard"),
    ("wire size", "Wire Size Chart"),
    ("tap drill", "Tap / Drill Chart"),
    ("tap / drill", "Tap / Drill Chart"),
)


def _pretty_display_title_for_row(row: dict) -> str:
    title = str(row.get("title") or "").strip()
    fn = str(row.get("original_filename") or row.get("file_name") or "").strip()
    if _is_file_row(row) and fn:
        combo_source = f"{fn} {title}".strip() if title and title.lower() != fn.lower() else fn
        base = _strip_pdf_extension(fn)
    else:
        combo_source = (title or fn or "—").strip()
        base = _strip_pdf_extension(combo_source)
    n = _norm_title_for_brand_lookup(_strip_pdf_extension(combo_source.replace("\n", " ")))
    for needle, pretty in _PRETTY_TITLE_RULES:
        if needle in n:
            return pretty
    n2 = _norm_title_for_brand_lookup(base)
    for needle, pretty in _PRETTY_TITLE_RULES:
        if needle in n2:
            return pretty
    return base if base else "—"


def _resource_icon_for_row(row: dict) -> str:
    n = _norm_title_for_brand_lookup(_pretty_display_title_for_row(row))
    fn = _norm_title_for_brand_lookup(str(row.get("original_filename") or row.get("file_name") or ""))
    blob = f"{n} {fn}"
    if "handbook" in blob:
        return "📘"
    if "weld" in blob or "contract" in blob or "welder" in blob:
        return "🔧"
    if "pipe tap" in blob:
        return "🧵"
    if "bolt tap" in blob or ("bolt" in blob and "tap" in blob):
        return "🪛"
    if "flange" in blob and "bolt" in blob:
        return "🔩"
    if "torque" in blob:
        return "⚙️"
    if "conduit" in blob or "wire fill" in blob:
        return "⚡"
    if "wire size" in blob or "awg" in blob:
        return "📐"
    if "handrail" in blob:
        return "🏗️"
    if "tap" in blob and "drill" in blob:
        return "🪛"
    if _is_file_row(row):
        return _toolbox_file_icon(str(row.get("original_filename") or row.get("file_name") or ""))
    return "🔗"


def _resource_subtitle_for_row(row: dict) -> str:
    cat = _category_display_label(str(row.get("category") or ""))
    if cat in {"HR", "Training", "Forms"}:
        return "Reference Guide"
    if cat in {"Safety", "IT"}:
        return "Spec Sheet"
    if cat in {"Operations"}:
        return "Field Tool"
    if cat and cat != "General":
        return "Quick Lookup"
    if _is_file_row(row):
        return "Quick Lookup"
    return "Quick Lookup"


def _href_attr(url: str) -> str:
    """Safe ``href`` value for HTML (http / https / data URLs from trusted storage)."""
    u = str(url or "").strip()
    if not u:
        return ""
    if u.startswith("data:"):
        return html.escape(u, quote=True)
    return html.escape(u, quote=True)


_MAX_INLINE_PDF_BYTES = 4_000_000


def render_resource_tile(
    title: str,
    subtitle: str,
    url: str | None,
    icon: str | None = None,
    *,
    tooltip: str = "",
    muted: bool = False,
) -> None:
    """
    IPS industrial tool tile for Resource Hub: chrome frame, blue header strip, uppercase title,
    footer subtitle. Whole card is wrapped in ``<a>`` when ``url`` is set (opens in a new tab).
    """
    ic = html.escape(icon or "📄", quote=True)
    safe_title = html.escape(title, quote=True)
    safe_sub = html.escape(subtitle, quote=True)
    tip = _tile_tooltip_attr(tooltip) if str(tooltip or "").strip() else ""
    muted_cls = " ips-resource-tile-card--muted" if muted else ""
    inner = f"""<div class="ips-resource-tile-card{muted_cls}"{tip}>
<div class="ips-resource-tile-chrome"></div>
<div class="ips-resource-tile-header-strip"></div>
<div class="ips-resource-tile-mid">
<div class="ips-resource-tile-icon">{ic}</div>
<div class="ips-resource-tile-title">{safe_title}</div>
</div>
<div class="ips-resource-tile-footer-strip">{safe_sub}</div>
</div>"""
    if url:
        h = _href_attr(url)
        st.markdown(
            f'<a class="ips-resource-tile-link" href="{h}" target="_blank" rel="noopener noreferrer">{inner}</a>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="ips-resource-tile-static">{inner}</div>',
            unsafe_allow_html=True,
        )


def _tile_marker_span(
    *,
    is_download: bool,
    has_admin_overlay: bool,
    interactive: bool,
    full_bleed_brand: bool = False,
) -> str:
    parts = ["ips-toolbox-card", "ips-toolbox-tile"]
    if full_bleed_brand:
        parts.append("ips-toolbox-tile--fullbleed")
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
            background: rgba(15, 23, 42, 0.72) !important;
            border: 1px solid rgba(71, 85, 105, 0.5) !important;
            border-radius: 18px !important;
            padding: 12px 10px 8px 10px !important;
            margin-bottom: 10px !important;
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
            display: flex;
            justify-content: center;
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
        /* Full-bleed branded tiles: no shell padding; artwork edge-to-edge */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-toolbox-tile--fullbleed) {
            padding: 0 !important;
            padding-bottom: 0 !important;
        }
        a.ips-toolbox-tile-link--fullbleed {
            display: block !important;
            width: 100% !important;
            padding: 0 !important;
            margin: 0 !important;
            border-radius: 0 !important;
        }
        a.ips-toolbox-tile-link--fullbleed:hover {
            background: transparent !important;
        }
        div.ips-toolbox-tile-body.ips-toolbox-tile-body--fullbleed.ips-toolbox-tile-body--launcher {
            max-width: none !important;
            width: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        div.ips-toolbox-launcher-stack--fullbleed {
            width: 100%;
            align-items: stretch;
        }
        div.ips-toolbox-fullbleed-media {
            width: 100%;
            aspect-ratio: 1 / 1;
            overflow: hidden;
            border-radius: 17px 17px 0 0;
            margin: 0;
            padding: 0;
            background: rgba(15, 23, 42, 0.5);
        }
        div.ips-toolbox-fullbleed-media img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            object-position: center;
            display: block;
            pointer-events: none;
            user-select: none;
        }
        div.ips-toolbox-launcher-footer {
            padding: 8px 10px 10px 10px;
            box-sizing: border-box;
            width: 100%;
        }
        div.ips-toolbox-launcher-stack--fullbleed p.ips-toolbox-launcher-title {
            min-height: auto;
            max-height: 3.1em;
            display: block;
            white-space: pre-line;
            text-transform: none;
            letter-spacing: 0.01em;
            word-break: break-word;
            overflow-wrap: anywhere;
            font-weight: 650 !important;
            overflow: hidden;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-toolbox-tile--fullbleed.ips-toolbox-tile-dl) div[data-testid="stButton"] > button {
            min-height: 300px !important;
        }
        div.ips-toolbox-tile-body.ips-toolbox-tile-body--launcher {
            position: relative;
            z-index: 0;
            min-height: 0;
            width: 100%;
            max-width: 148px;
            margin: 0 auto;
        }
        div.ips-toolbox-launcher-stack {
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            gap: 0;
        }
        div.ips-toolbox-launcher-icon-wrap {
            width: 100%;
            height: 128px;
            min-height: 128px;
            max-height: 128px;
            box-sizing: border-box;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 8px auto;
            max-width: 132px;
            border-radius: 20px;
            background: linear-gradient(165deg, rgba(30, 41, 59, 0.98) 0%, rgba(15, 23, 42, 0.9) 100%);
            border: 1px solid rgba(71, 85, 105, 0.55);
            box-shadow:
                inset 0 1px 0 rgba(255, 255, 255, 0.07),
                0 6px 18px rgba(0, 0, 0, 0.38);
            transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
        }
        div.ips-toolbox-launcher-icon-wrap--brand {
            padding: 10px;
        }
        div.ips-toolbox-launcher-icon-wrap--brand img {
            width: 104px;
            height: 104px;
            max-width: 104px;
            max-height: 104px;
            object-fit: contain;
            object-position: center;
            border-radius: 14px;
            filter: drop-shadow(0 3px 12px rgba(0,0,0,0.42));
            user-select: none;
            pointer-events: none;
        }
        div.ips-toolbox-launcher-icon-wrap--fallback {
            padding: 0;
        }
        p.ips-toolbox-tile-icon {
            text-align: center;
            font-size: 2.85rem;
            line-height: 1;
            margin: 0;
            width: 104px;
            height: 104px;
            display: flex;
            align-items: center;
            justify-content: center;
            user-select: none;
            filter: drop-shadow(0 2px 6px rgba(0,0,0,0.35));
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-toolbox-tile-interactive):hover
            div.ips-toolbox-launcher-icon-wrap {
            border-color: rgba(96, 165, 250, 0.55);
            box-shadow:
                inset 0 1px 0 rgba(255, 255, 255, 0.1),
                0 0 0 1px rgba(96, 165, 250, 0.25),
                0 12px 28px rgba(0, 0, 0, 0.4);
            transform: translateY(-1px);
        }
        p.ips-toolbox-launcher-title {
            color: #f1f5f9 !important;
            font-size: 0.76rem !important;
            font-weight: 650 !important;
            text-align: center;
            text-transform: none;
            letter-spacing: 0.01em;
            margin: 2px 0 0 0 !important;
            line-height: 1.22 !important;
            min-height: 2.2em;
            max-height: 3.1em;
            overflow: hidden;
            display: block;
            white-space: pre-line;
            padding: 0 4px;
            word-break: break-word;
            overflow-wrap: anywhere;
            hyphens: auto;
        }
        p.ips-toolbox-launcher-title strong {
            font-weight: 700 !important;
        }
        p.ips-toolbox-tile-meta--compact {
            color: #94a3b8 !important;
            font-size: 0.58rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            text-align: center;
            margin: 4px 0 0 0 !important;
            opacity: 0.9;
        }
        p.ips-toolbox-tile-meta {
            color: #64748b !important;
            font-size: 0.65rem !important;
            text-align: center;
            margin: 4px 0 0 0 !important;
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
            bottom: 44px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-toolbox-tile-dl):not(:has(.ips-toolbox-tile-has-admin)) div[data-testid="stButton"] {
            bottom: 0 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-toolbox-tile-dl) div[data-testid="stButton"] > button {
            position: absolute !important;
            inset: 0 !important;
            width: 100% !important;
            height: 100% !important;
            min-height: 210px !important;
            opacity: 0.03 !important;
            cursor: pointer !important;
            border-radius: 16px !important;
        }
        hr.ips-toolbox-tile-admin-sep {
            margin: 6px 0 4px 0 !important;
            border: none !important;
            border-top: 1px solid rgba(51, 65, 85, 0.42) !important;
            opacity: 0.9;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-toolbox-tile) div[data-testid="stHorizontalBlock"] button[kind="secondary"] {
            position: relative !important;
            z-index: 5 !important;
            min-height: 1.32rem !important;
            padding: 0.05rem 0.22rem !important;
            font-size: 0.56rem !important;
            border-radius: 6px !important;
            font-weight: 500 !important;
            opacity: 0.68 !important;
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
        [data-testid="stMain"] div[data-testid="stHorizontalBlock"]:has(.ips-toolbox-tile) {
            justify-content: center !important;
            align-items: start !important;
            gap: 0.55rem !important;
        }
        [data-testid="stMain"] div[data-testid="stHorizontalBlock"]:has(.ips-toolbox-tile) > div[data-testid="column"] {
            display: flex !important;
            justify-content: center !important;
        }
        @media (max-width: 900px) {
            p.ips-toolbox-tile-icon { font-size: 2.55rem; width: 92px !important; height: 92px !important; }
            p.ips-toolbox-launcher-title { font-size: 0.74rem !important; }
            div.ips-toolbox-launcher-icon-wrap {
                height: 118px !important;
                min-height: 118px !important;
                max-height: 118px !important;
                max-width: 124px !important;
            }
            div.ips-toolbox-launcher-icon-wrap--brand img {
                width: 92px !important;
                height: 92px !important;
                max-height: 92px !important;
            }
            [data-testid="stMain"] div[data-testid="stHorizontalBlock"]:has(.ips-toolbox-tile) {
                flex-direction: row !important;
                flex-wrap: wrap !important;
                align-items: stretch !important;
            }
            [data-testid="stMain"] div[data-testid="stHorizontalBlock"]:has(.ips-toolbox-tile) > div[data-testid="column"] {
                width: calc(50% - 0.25rem) !important;
                max-width: calc(50% - 0.25rem) !important;
                min-width: 0 !important;
                flex: 1 1 calc(50% - 0.25rem) !important;
            }
        }
        /* Resource hub: chrome tool tiles (no admin row — tile only) */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-resource-tile-grid-marker) {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 6px 4px 10px 4px !important;
            margin-bottom: 4px !important;
        }
        a.ips-resource-tile-link {
            display: block !important;
            text-decoration: none !important;
            color: inherit !important;
        }
        div.ips-resource-tile-static {
            display: block;
        }
        div.ips-resource-tile-card {
            position: relative;
            border-radius: 14px;
            height: 142px;
            min-height: 142px;
            max-height: 142px;
            box-sizing: border-box;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            background: linear-gradient(165deg, #0a1628 0%, #050d18 55%, #0a1424 100%);
            border: 1px solid rgba(148, 163, 184, 0.45);
            box-shadow:
                inset 0 1px 0 rgba(255, 255, 255, 0.14),
                inset 0 -2px 6px rgba(0, 0, 0, 0.45),
                0 0 0 1px rgba(30, 64, 175, 0.35),
                0 4px 14px rgba(0, 0, 0, 0.35);
            transition: transform 0.22s ease, box-shadow 0.22s ease, filter 0.22s ease;
        }
        div.ips-resource-tile-chrome {
            position: absolute;
            inset: 0;
            border-radius: 14px;
            pointer-events: none;
            box-shadow:
                inset 0 0 0 1px rgba(255, 255, 255, 0.08),
                inset 0 0 20px rgba(59, 130, 246, 0.06);
        }
        div.ips-resource-tile-header-strip {
            height: 7px;
            flex: 0 0 auto;
            background: linear-gradient(90deg, #1d4ed8, #3b82f6, #60a5fa, #3b82f6, #1d4ed8);
            box-shadow: 0 1px 0 rgba(255, 255, 255, 0.2) inset;
        }
        div.ips-resource-tile-mid {
            flex: 1 1 auto;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 8px;
            padding: 10px 10px 6px 10px;
            min-height: 0;
        }
        div.ips-resource-tile-icon {
            font-size: 1.75rem;
            line-height: 1;
            filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.5));
        }
        div.ips-resource-tile-title {
            color: #f1f5f9 !important;
            font-weight: 800 !important;
            font-size: 0.72rem !important;
            line-height: 1.2 !important;
            text-align: center;
            text-transform: uppercase;
            letter-spacing: 0.07em;
            padding: 0 4px;
            word-break: break-word;
            overflow-wrap: anywhere;
            max-height: 2.6em;
            overflow: hidden;
        }
        div.ips-resource-tile-footer-strip {
            flex: 0 0 auto;
            padding: 7px 10px 8px 10px;
            font-size: 0.68rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            color: #93c5fd !important;
            background: linear-gradient(180deg, rgba(15, 23, 42, 0.2), rgba(2, 6, 23, 0.92));
            border-top: 1px solid rgba(51, 65, 85, 0.65);
            text-align: center;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        div.ips-resource-tile-card--muted {
            opacity: 0.52;
            filter: grayscale(0.25);
        }
        a.ips-resource-tile-link:hover div.ips-resource-tile-card:not(.ips-resource-tile-card--muted) {
            transform: translateY(-4px);
            box-shadow:
                inset 0 1px 0 rgba(255, 255, 255, 0.18),
                inset 0 -2px 8px rgba(0, 0, 0, 0.5),
                0 0 0 1px rgba(96, 165, 250, 0.55),
                0 10px 28px rgba(0, 0, 0, 0.42),
                0 0 22px rgba(59, 130, 246, 0.35);
        }
        [data-testid="stMain"] div[data-testid="stHorizontalBlock"]:has(.ips-resource-tile-grid-marker) {
            gap: 1rem !important;
            align-items: stretch !important;
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


def _render_tool_tile(row: dict) -> None:
    """Resource hub: single clickable IPS tool tile (no on-tile admin controls)."""
    desc = str(row.get("description") or "").strip()
    url_raw = str(row.get("url") or "").strip()
    rid = str(row.get("id") or "")
    is_file = _is_file_row(row)
    fp = str(row.get("file_path") or "").strip()
    fn_display = (
        str(row.get("original_filename") or row.get("file_name") or "").strip() or Path(fp).name or "document"
    )

    display_title = _pretty_display_title_for_row(row)
    subtitle = _resource_subtitle_for_row(row)
    icon = _resource_icon_for_row(row)

    ref = ""
    if is_file and fp:
        ref = create_signed_url(fp, expires_in=3600) or ""

    tip_text = desc

    with st.container(border=True):
        st.markdown(
            '<span class="ips-toolbox-tile ips-resource-tile-grid-marker"></span>',
            unsafe_allow_html=True,
        )

        if is_file and fp:
            if not ref:
                render_resource_tile(
                    display_title, subtitle, None, icon=icon, tooltip=tip_text, muted=True
                )
                st.caption("File unavailable")
            elif ref.startswith("http://") or ref.startswith("https://"):
                render_resource_tile(display_title, subtitle, ref, icon=icon, tooltip=tip_text)
            else:
                p = Path(ref)
                if p.is_file():
                    try:
                        data_bytes = p.read_bytes()
                    except OSError:
                        data_bytes = b""
                    sz = len(data_bytes)
                    ctype = str(row.get("content_type") or "").strip().lower()
                    is_pdf = fn_display.lower().endswith(".pdf") or "pdf" in ctype
                    open_url: str | None = None
                    if is_pdf and sz and sz <= _MAX_INLINE_PDF_BYTES and data_bytes:
                        b64 = base64.b64encode(data_bytes).decode("ascii")
                        open_url = f"data:application/pdf;base64,{b64}"
                    if open_url:
                        render_resource_tile(display_title, subtitle, open_url, icon=icon, tooltip=tip_text)
                    else:
                        render_resource_tile(
                            display_title, subtitle, None, icon=icon, tooltip=tip_text, muted=True
                        )
                        ctype_mime = str(row.get("content_type") or "").strip() or "application/octet-stream"
                        _dl_help = " — ".join([x for x in (display_title, desc) if x]) or f"Download {fn_display}"
                        st.download_button(
                            "Download file",
                            data=data_bytes,
                            file_name=fn_display,
                            mime=ctype_mime,
                            type="primary",
                            use_container_width=True,
                            key=f"etb_dl_{rid}",
                            help=_dl_help,
                        )
                else:
                    render_resource_tile(
                        display_title, subtitle, None, icon=icon, tooltip=tip_text, muted=True
                    )
                    st.caption("Missing file")
        elif url_raw:
            nu = _normalize_url(url_raw)
            render_resource_tile(display_title, subtitle, nu, icon=icon, tooltip=tip_text)
        else:
            render_resource_tile(
                display_title, subtitle, None, icon=icon, tooltip=tip_text, muted=True
            )
            st.caption("No link for this item")


def _render_tools_hub(rows: list[dict]) -> None:
    if not rows:
        st.info("No toolbox resources yet. Admins can add links with **Add Tool** or upload files with **Upload Document**.")
        return

    _inject_toolbox_hub_styles()
    ensure_narrow_viewport_detected()
    is_narrow = bool(st.session_state.get(IPS_VIEWPORT_NARROW_KEY, False))
    ncols = 2 if is_narrow else 4

    st.markdown("##### Resource hub")
    st.caption(
        "Grouped by category — **click a tile** to open in a new tab. "
        "Large local PDFs may use **Download file** below the tile. Signed URLs expire after about one hour."
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
            cols = st.columns(ncols, gap="large")
            for k, row in enumerate(chunk):
                with cols[k]:
                    _render_tool_tile(row)


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
            ac1, ac2, ac3 = st.columns([1, 1, 3], gap="small")
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
            _render_tools_hub(display_rows)
        with side_col:
            if panel_add:
                _render_add_tool_panel(existing_rows=all_rows)
            elif panel_upload:
                _render_upload_document_panel(existing_rows=all_rows)
            elif panel_edit and edit_row:
                _render_edit_tool_panel(row=edit_row, existing_rows=all_rows)
    else:
        _render_tools_hub(display_rows)

    if not can_manage:
        st.caption("Need something added? Contact an administrator.")