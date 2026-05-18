"""UI rendering components for the Assets module.

All functions here are pure renderers — they receive data as arguments and
emit Streamlit widgets.  No direct database calls; use queries.py / services.py
from the caller.
"""
from __future__ import annotations

import html as html_module
from typing import Any

import pandas as pd
import streamlit as st

try:
    from app.db import create_signed_url
    from app.ui import IPS_NAV_PENDING_KEY
except ImportError:
    from db import create_signed_url  # type: ignore
    from ui import IPS_NAV_PENDING_KEY  # type: ignore

try:
    from app.pages.assets.utils import (
        ASSET_TYPES,
        ASSET_STATUSES,
        disp,
        is_checkout_tool_flag,
        is_rental_row,
        is_truthy,
        status_colour,
    )
except ImportError:
    from pages.assets.utils import (  # type: ignore
        ASSET_TYPES,
        ASSET_STATUSES,
        disp,
        is_checkout_tool_flag,
        is_rental_row,
        is_truthy,
        status_colour,
    )

# ── CSS injected once per session ─────────────────────────────────────────

_CSS_KEY = "ips_assets_module_css_v1"
_CARD_CSS = """
<style>
.ips-am-card-title { font-weight: 650; font-size: 1.05rem; margin: 0; line-height: 1.35; }
.ips-am-badge-rental {
  display: inline-block; margin-left: 8px; vertical-align: middle;
  padding: 3px 9px; border-radius: 6px; font-size: 10px; font-weight: 800;
  letter-spacing: 0.05em; text-transform: uppercase;
  color: #e0f2fe;
  background: linear-gradient(145deg, rgba(14,165,233,.38), rgba(37,99,235,.28));
  border: 1px solid rgba(56,189,248,.5);
}
.ips-am-badge-tool {
  display: inline-block; margin-left: 6px; vertical-align: middle;
  padding: 2px 8px; border-radius: 5px; font-size: 10px; font-weight: 800;
  letter-spacing: 0.04em; text-transform: uppercase;
  color: #fef3c7; background: rgba(245,158,11,.22);
  border: 1px solid rgba(251,191,36,.45);
}
.ips-am-badge-tool-out { color: #fecaca; background: rgba(239,68,68,.2); border-color: rgba(248,113,113,.45); }
.ips-asset-thumb-placeholder {
  width: 88px; height: 88px; border-radius: 8px;
  border: 1px dashed rgba(148,163,184,.45);
  background: rgba(15,23,42,.55);
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 600; color: #94a3b8;
  text-align: center; line-height: 1.2; padding: 6px; box-sizing: border-box;
}
@media (max-width: 900px) {
  .ips-am-mobile-card .stButton > button { width: 100% !important; min-height: 2.75rem !important; }
}
</style>
"""


def _inject_css() -> None:
    if st.session_state.get(_CSS_KEY):
        return
    st.session_state[_CSS_KEY] = True
    st.markdown(_CARD_CSS, unsafe_allow_html=True)


# ── Header ─────────────────────────────────────────────────────────────────

def render_assets_header(title: str = "Asset Manager", subtitle: str = "") -> None:
    """Render a compact page header."""
    try:
        from app.ui.page_shell import render_page_header
    except ImportError:
        from ui.page_shell import render_page_header  # type: ignore
    render_page_header(title, subtitle or "Overview and status of tools and equipment.")


# ── Status badge ───────────────────────────────────────────────────────────

def render_asset_status_badge(status: str) -> None:
    """Render a small coloured inline status badge using st.markdown."""
    colour = status_colour(status)
    label = html_module.escape(str(status or "—"))
    st.markdown(
        f'<span style="display:inline-block;padding:3px 10px;border-radius:5px;'
        f'font-size:12px;font-weight:700;color:#fff;background:{colour};">'
        f"{label}</span>",
        unsafe_allow_html=True,
    )


# ── Assignment info ────────────────────────────────────────────────────────

def render_asset_assignment_info(
    asset: dict,
    *,
    job_label_by_id: dict | None = None,
    emp_by_id: dict | None = None,
) -> None:
    """Render employee / job assignment as compact caption lines."""
    emp = str(asset.get("assigned_employee") or "").strip()
    if emp_by_id:
        eid = str(asset.get("current_holder_employee_id") or "").strip()
        emp = emp_by_id.get(eid) or emp
    jid = str(asset.get("assigned_job_id") or "").strip()
    job = ""
    if job_label_by_id and jid:
        job = job_label_by_id.get(jid, "")
    parts: list[str] = []
    if emp:
        parts.append(f"**Employee:** {emp}")
    if job and job != "—":
        parts.append(f"**Job:** {job}")
    if parts:
        st.caption(" · ".join(parts))


# ── Thumbnail ──────────────────────────────────────────────────────────────

def render_asset_thumbnail(asset_row: dict, *, thumb_px: int = 88) -> None:
    """Render a primary-image thumbnail or a styled placeholder."""
    pp = str(asset_row.get("photo_path") or "").strip()
    placeholder = (
        f'<div class="ips-asset-thumb-placeholder" '
        f'style="width:{thumb_px}px;height:{thumb_px}px;" aria-label="No photo">No photo</div>'
    )
    if not pp:
        st.markdown(placeholder, unsafe_allow_html=True)
        return
    url = create_signed_url(pp, expires_in=3600)
    if not url:
        st.markdown(placeholder, unsafe_allow_html=True)
        return
    try:
        st.image(url, width=thumb_px)
    except Exception:
        st.markdown(placeholder, unsafe_allow_html=True)


# ── Single card ────────────────────────────────────────────────────────────

def render_asset_card(
    rec: dict,
    *,
    index: int = 0,
    key_prefix: str = "am",
    mobile_layout: bool = False,
    show_category: bool = True,
    emp_by_id: dict | None = None,
    job_label_by_id: dict | None = None,
    on_view_click: Any = None,
) -> None:
    """Render one asset card row (photo + metadata + View button).

    *on_view_click* is an optional callable invoked when the button is clicked.
    If None, the card navigates to the Asset Detail page via session state.
    """
    _inject_css()
    aid = str(rec.get("id") or "").strip()
    if not aid:
        return

    rental_badge = (
        '<span class="ips-am-badge-rental" title="Rentable">Rental</span>'
        if is_rental_row(rec.get("is_rental"))
        else ""
    )
    tool_badge = ""
    if is_checkout_tool_flag(rec.get("is_checkout_item")):
        stt = str(rec.get("status") or "").strip()
        cls = "ips-am-badge-tool ips-am-badge-tool-out" if stt == "Checked Out" else "ips-am-badge-tool"
        tool_badge = f'<span class="{cls}" title="Checkout tool">{html_module.escape(stt or "Tool")}</span>'

    meta: list[str] = []
    if show_category and str(rec.get("category") or "").strip():
        meta.append(f"Category: {disp(rec.get('category'))}")
    meta.append(f"Status: {disp(rec.get('status'))}")
    meta.append(f"Serial: {disp(rec.get('serial_number'))}")
    mm, md = disp(rec.get("manufacturer")), disp(rec.get("model"))
    if mm != "—" or md != "—":
        meta.append(f"{mm} · {md}" if mm != "—" and md != "—" else (mm if mm != "—" else md))
    if is_checkout_tool_flag(rec.get("is_checkout_item")) and emp_by_id:
        eid = str(rec.get("current_holder_employee_id") or "").strip()
        hn = emp_by_id.get(eid) or str(rec.get("assigned_employee") or "").strip()
        if hn:
            meta.append(f"Holder: {hn}")

    def _view() -> None:
        if on_view_click:
            on_view_click(aid)
        else:
            st.session_state["asset_detail_id"] = aid
            st.session_state[IPS_NAV_PENDING_KEY] = "Asset Detail"
            st.rerun()

    thumb_px = 92 if mobile_layout else 88

    if mobile_layout:
        if index > 0:
            st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown('<span class="ips-am-mobile-card"></span>', unsafe_allow_html=True)
            c_thumb, c_body = st.columns([1, 2.35], gap="small")
            with c_thumb:
                render_asset_thumbnail(rec, thumb_px=thumb_px)
            with c_body:
                st.markdown(
                    f'<p class="ips-am-card-title">'
                    f'{html_module.escape(disp(rec.get("asset_name")))}'
                    f"{rental_badge}{tool_badge}</p>",
                    unsafe_allow_html=True,
                )
                st.caption(" · ".join(meta))
            if st.button("View Asset", key=f"{key_prefix}_view_{index}_{aid}",
                         type="primary", use_container_width=True):
                _view()
        return

    if index > 0:
        st.divider()
    ct, cm, cb = st.columns([1.15, 4.2, 1.25], vertical_alignment="center")
    with ct:
        render_asset_thumbnail(rec, thumb_px=thumb_px)
    with cm:
        st.markdown(
            f'<p class="ips-am-card-title">'
            f'{html_module.escape(disp(rec.get("asset_name")))}'
            f"{rental_badge}{tool_badge}</p>",
            unsafe_allow_html=True,
        )
        cat_suffix = f" · Category: {disp(rec.get('category'))}" if show_category and str(rec.get("category") or "").strip() else ""
        st.caption(
            f"{disp(rec.get('manufacturer'))} · {disp(rec.get('model'))} · "
            f"Serial: {disp(rec.get('serial_number'))} · Status: {disp(rec.get('status'))}"
            + cat_suffix
        )
    with cb:
        if st.button("View Asset", key=f"{key_prefix}_view_{index}_{aid}",
                     type="primary", use_container_width=True):
            _view()


# ── Card list ──────────────────────────────────────────────────────────────

def render_asset_card_list(
    records: list[dict],
    *,
    key_prefix: str = "am",
    show_category: bool = True,
    mobile_layout: bool = False,
    emp_by_id: dict | None = None,
    job_label_by_id: dict | None = None,
    on_view_click: Any = None,
) -> None:
    """Render a full card list from a list of asset dicts."""
    _inject_css()
    for i, rec in enumerate(records):
        render_asset_card(
            rec,
            index=i,
            key_prefix=key_prefix,
            mobile_layout=mobile_layout,
            show_category=show_category,
            emp_by_id=emp_by_id,
            job_label_by_id=job_label_by_id,
            on_view_click=on_view_click,
        )
    if records:
        st.caption(
            "Thumbnails use each asset's **primary image** (`photo_path`). "
            "Use **View Asset** for the full profile, gallery, and maintenance records."
        )


# ── Filters ────────────────────────────────────────────────────────────────

def render_assets_filters(
    df: pd.DataFrame,
    *,
    mobile: bool = False,
) -> dict[str, Any]:
    """Render filter controls and return a dict of current filter values.

    Uses standardised session-state keys: ``assets_filter_status``,
    ``assets_filter_category``, ``assets_search_query``, ``assets_filter_active``,
    ``assets_filter_type``.
    """
    statuses = ["All"] + sorted(
        s for s in df.get("status", pd.Series(dtype=str)).dropna().astype(str).unique()
        if str(s).strip()
    )
    categories = ["All"] + sorted(
        c for c in df.get("category", pd.Series(dtype=str)).dropna().astype(str).unique()
        if str(c).strip()
    )

    if mobile:
        st.text_input(
            "Search Assets",
            placeholder="Name, serial, manufacturer, model, status, category…",
            key="assets_search_query",
        )
        st.selectbox("Filter Status", statuses, key="assets_filter_status")
        st.selectbox("Filter Category", categories, key="assets_filter_category")
        st.selectbox("Filter Type", ["All"] + ASSET_TYPES, key="assets_filter_type")
        st.selectbox("Filter Active", ["All", "Active Only", "Inactive Only"], key="assets_filter_active")
    else:
        fc1, fc2, fc3, fc4 = st.columns([2, 1, 1, 1])
        fc1.text_input(
            "Search Assets",
            placeholder="Name, serial, manufacturer, model, status…",
            key="assets_search_query",
        )
        fc2.selectbox("Status", statuses, key="assets_filter_status")
        fc3.selectbox("Category", categories, key="assets_filter_category")
        fc4.selectbox("Active", ["All", "Active Only", "Inactive Only"], key="assets_filter_active")

    return {
        "search": st.session_state.get("assets_search_query", ""),
        "status": st.session_state.get("assets_filter_status", "All"),
        "category": st.session_state.get("assets_filter_category", "All"),
        "asset_type": st.session_state.get("assets_filter_type", "All"),
        "active": st.session_state.get("assets_filter_active", "All"),
    }


def apply_assets_filters(df: pd.DataFrame, filters: dict[str, Any]) -> pd.DataFrame:
    """Return a filtered copy of *df* based on the values from render_assets_filters."""
    result = df.copy()

    status = str(filters.get("status") or "All")
    if status != "All" and "status" in result.columns:
        result = result[result["status"].astype(str) == status]

    category = str(filters.get("category") or "All")
    if category != "All" and "category" in result.columns:
        result = result[result["category"].astype(str).str.strip().str.lower() == category.lower()]

    asset_type = str(filters.get("asset_type") or "All")
    if asset_type != "All" and "asset_type" in result.columns:
        result = result[result["asset_type"].astype(str) == asset_type]

    active = str(filters.get("active") or "All")
    if active == "Active Only" and "is_active" in result.columns:
        result = result[result["is_active"].map(is_truthy)]
    elif active == "Inactive Only" and "is_active" in result.columns:
        result = result[~result["is_active"].map(is_truthy)]

    search = str(filters.get("search") or "").strip().lower()
    if search:
        search_cols = [
            c for c in ("asset_id", "asset_name", "serial_number", "manufacturer",
                        "model", "status", "category", "assigned_employee", "location", "notes")
            if c in result.columns
        ]
        if search_cols:
            mask = result[search_cols].astype(str).apply(
                lambda col: col.str.lower().str.contains(search, na=False)
            )
            result = result[mask.any(axis=1)]

    return result


# ── Table ──────────────────────────────────────────────────────────────────

_TABLE_SHOW_COLS = [
    "asset_id", "asset_name", "asset_type", "category", "status",
    "is_rental", "serial_number", "manufacturer", "model",
    "assigned_employee", "location", "inspection_due_date",
    "maintenance_due_date", "is_active",
]


def render_assets_table(
    filtered: pd.DataFrame,
    *,
    table_key: str,
    can_edit: bool = False,
    editor_key: str = "assets_table_editor",
    job_label_by_id: dict | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    """Render the selectable asset dataframe; return (display_df, selected_ids).

    Falls back to a plain non-selectable dataframe when ``table_actions`` is
    unavailable.
    """
    try:
        from app.table_actions import render_selectable_dataframe
    except ImportError:
        from table_actions import render_selectable_dataframe  # type: ignore

    # Enrich with job name column for display
    disp_df = filtered.copy()
    if job_label_by_id and "assigned_job_id" in disp_df.columns:
        disp_df["assigned_job_name"] = disp_df["assigned_job_id"].map(
            lambda jid: job_label_by_id.get(str(jid), "") if jid else ""
        )

    show_cols = [c for c in _TABLE_SHOW_COLS if c in disp_df.columns]
    if "assigned_job_name" in disp_df.columns:
        show_cols.append("assigned_job_name")

    if "id" not in disp_df.columns:
        st.dataframe(disp_df[show_cols], use_container_width=True, hide_index=True)
        return disp_df, []

    _, sel = render_selectable_dataframe(
        disp_df,
        table_key=table_key,
        id_column="id",
        columns=show_cols,
        editor_key=editor_key,
    )
    return disp_df, list(sel or [])


# ── Detail panel (preview) ─────────────────────────────────────────────────

def render_asset_detail_panel(
    asset: dict,
    *,
    job_label_by_id: dict | None = None,
    emp_by_id: dict | None = None,
) -> None:
    """Render a compact read-only summary of one asset."""
    _inject_css()
    c_img, c_txt = st.columns([1, 2])
    with c_img:
        render_asset_thumbnail(asset)
    with c_txt:
        st.markdown(f"**{disp(asset.get('asset_name'))}**")
        st.caption(
            f"{disp(asset.get('manufacturer'))} · {disp(asset.get('model'))} · "
            f"Serial {disp(asset.get('serial_number'))}"
        )
        render_asset_status_badge(str(asset.get("status") or ""))
        st.markdown(f"**Category:** {disp(asset.get('category'))}")
        st.markdown(f"**Location:** {disp(asset.get('location'))}")
        render_asset_assignment_info(asset, job_label_by_id=job_label_by_id, emp_by_id=emp_by_id)
        if str(asset.get("notes") or "").strip():
            st.caption(f"Notes: {asset.get('notes')}")


# ── Empty states ───────────────────────────────────────────────────────────

def render_asset_empty_state(reason: str = "no_assets", *, can_add: bool = False) -> None:
    """Render a helpful empty-state message appropriate to the context."""
    messages = {
        "no_assets": ("No assets found.",
                      "Use **New Asset** above to add your first asset." if can_add else ""),
        "no_match": ("No assets match your current filters.",
                     "Try clearing the search or adjusting the status / category filter."),
        "no_category": ("No category selected.",
                        "Choose a category from the filter above to browse assets."),
        "no_assigned": ("No assets are currently assigned.",
                        "Assets with an assigned employee or job will appear here."),
    }
    title, hint = messages.get(reason, ("No assets found.", ""))
    st.info(title)
    if hint:
        st.caption(hint)
