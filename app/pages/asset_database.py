from __future__ import annotations

import html
import pandas as pd
import streamlit as st

try:
    from app.asset_responsive import inject_asset_workflow_mobile_css
    from app.mobile_ui import ensure_narrow_viewport_detected
    from app.auth import current_role
    from app.branding import render_header
    from app.db import create_signed_url, delete_rows_admin, fetch_one, fetch_table, update_rows_admin
    from app.pages.asset_intake import render_asset_intake_form
    from app.services.asset_constants import ASSET_STATUSES
    from app.services.asset_service import optional_numeric
    from app.services.job_service import job_row_select_label, sort_jobs_by_number_then_name
    from app.ui import IPS_NAV_PENDING_KEY
except ImportError:
    from asset_responsive import inject_asset_workflow_mobile_css  # type: ignore
    from mobile_ui import ensure_narrow_viewport_detected  # type: ignore
    from auth import current_role  # type: ignore
    from branding import render_header  # type: ignore
    from db import create_signed_url, delete_rows_admin, fetch_one, fetch_table, update_rows_admin  # type: ignore
    from pages.asset_intake import render_asset_intake_form  # type: ignore
    from services.asset_constants import ASSET_STATUSES  # type: ignore
    from services.asset_service import optional_numeric  # type: ignore
    from services.job_service import job_row_select_label, sort_jobs_by_number_then_name  # type: ignore
    from ui import IPS_NAV_PENDING_KEY  # type: ignore

try:
    from app.table_actions import (
        IPS_PENDING_DELETE,
        TABLE_KEY_ASSETS,
        clear_selected_ids,
        inject_table_action_styles,
        render_selectable_dataframe,
        render_selection_action_bar,
    )
except ImportError:
    from table_actions import (  # type: ignore
        IPS_PENDING_DELETE,
        TABLE_KEY_ASSETS,
        clear_selected_ids,
        inject_table_action_styles,
        render_selectable_dataframe,
        render_selection_action_bar,
    )

try:
    from app.ips_crud_list_styles import render_crud_list_subtitle
except ImportError:
    from ips_crud_list_styles import render_crud_list_subtitle  # type: ignore

_ASSET_PANEL_CSS_KEY = "ips_asset_db_side_panel_css_injected"
_ADB_TOP_ACTIONS_CSS_KEY = "ips_asset_db_top_actions_css_injected"
_ADB_MOBILE_CSS_KEY = "ips_asset_db_mobile_css_injected_v2"


def _inject_asset_database_mobile_css() -> None:
    if st.session_state.get(_ADB_MOBILE_CSS_KEY):
        return
    st.session_state[_ADB_MOBILE_CSS_KEY] = True
    st.markdown(
        """
        <style>
        @media (max-width: 900px) {
          div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-adb-card-mobile) {
            padding-top: 8px !important;
            padding-bottom: 10px !important;
            margin-bottom: 8px !important;
          }
          div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-adb-card-mobile) .ips-adb-card-title-line {
            font-size: 0.98rem !important;
            line-height: 1.3 !important;
            color: #f8fafc !important;
            margin: 0 0 4px 0 !important;
            font-weight: 600 !important;
          }
          div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-adb-card-mobile) .ips-adb-card-title-line .ips-adb-card-id {
            font-weight: 750 !important;
            color: #f1f5f9 !important;
          }
          div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-adb-card-mobile) .ips-adb-card-title-line .ips-adb-card-name {
            font-weight: 600 !important;
            color: #e2e8f0 !important;
          }
          div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-adb-card-mobile) .ips-adb-card-title-line .ips-badge-rental {
            padding: 2px 7px !important;
            font-size: 9px !important;
            font-weight: 750 !important;
            letter-spacing: 0.06em !important;
            margin-left: 8px !important;
            vertical-align: middle !important;
            border-radius: 5px !important;
          }
          div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-adb-card-mobile) .ips-adb-card-meta {
            font-size: 0.8125rem !important;
            line-height: 1.4 !important;
            color: #94a3b8 !important;
            margin: 0 0 8px 0 !important;
            font-weight: 450 !important;
          }
          div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-adb-card-mobile) .stButton {
            width: 100% !important;
          }
          div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-adb-card-mobile) .stButton > button {
            width: 100% !important;
            min-height: 3rem !important;
            font-size: 1rem !important;
            font-weight: 650 !important;
            border-radius: 10px !important;
          }
          div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-adb-card-mobile) .stButton > button[kind="secondary"] {
            min-height: 2.75rem !important;
            font-weight: 550 !important;
          }
          div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-adb-card-mobile) [data-testid="stImage"] img {
            max-width: 92px !important;
            width: 92px !important;
            height: auto !important;
            border-radius: 8px !important;
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _inject_asset_db_top_actions_css() -> None:
    if st.session_state.get(_ADB_TOP_ACTIONS_CSS_KEY):
        return
    st.session_state[_ADB_TOP_ACTIONS_CSS_KEY] = True
    st.markdown(
        """
        <style>
        /* One row: Cards | Table | New Asset | Asset Scanner — equal columns, equal button height */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-list-top-anchor)
            div[data-testid="stHorizontalBlock"] {
            gap: 0.4rem !important;
            align-items: stretch !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-list-top-anchor)
            div[data-testid="column"] .stButton > button {
            width: 100% !important;
            box-sizing: border-box !important;
        }
        /* Keep this toolbar on one row on phones (global mobile CSS stacks columns elsewhere) */
        @media (max-width: 900px) {
          div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-list-top-anchor)
              div[data-testid="stHorizontalBlock"] {
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            align-items: stretch !important;
          }
          div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-list-top-anchor)
              div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
            width: auto !important;
            min-width: 0 !important;
            flex: 1 1 0 !important;
            max-width: none !important;
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_asset_db_top_action_row(*, vm: str, can_add: bool) -> None:
    """Cards, Table, New Asset (when allowed), Asset Scanner — single row, equal-width columns."""
    if can_add:
        c_cards, c_table, c_new, c_scan = st.columns(4, gap="small")
    else:
        c_cards, c_table, c_scan = st.columns(3, gap="small")
    with c_cards:
        if st.button(
            "Cards",
            type="primary" if vm == "Cards" else "secondary",
            use_container_width=True,
            key="adb_view_cards",
            help="Photo-first card layout for browsing.",
        ):
            st.session_state["asset_db_view_user_chose"] = True
            st.session_state["asset_db_view_mode"] = "Cards"
            st.rerun()
    with c_table:
        if st.button(
            "Table",
            type="primary" if vm == "Table" else "secondary",
            use_container_width=True,
            key="adb_view_table",
            help="Selectable rows, CSV export, and bulk delete.",
        ):
            st.session_state["asset_db_view_user_chose"] = True
            st.session_state["asset_db_view_mode"] = "Table"
            st.rerun()
    if can_add:
        with c_new:
            if st.button("New Asset", type="primary", use_container_width=True, key="asset_db_new"):
                _clear_asset_panel()
                st.session_state["asset_db_add_mode"] = True
                st.rerun()
        with c_scan:
            if st.button(
                "Asset Scanner",
                type="secondary",
                use_container_width=True,
                key="asset_db_scanner",
            ):
                _clear_asset_panel()
                st.session_state[IPS_NAV_PENDING_KEY] = "Asset Scanner"
                st.rerun()
    else:
        with c_scan:
            if st.button(
                "Asset Scanner",
                type="secondary",
                use_container_width=True,
                key="asset_db_scanner",
            ):
                _clear_asset_panel()
                st.session_state[IPS_NAV_PENDING_KEY] = "Asset Scanner"
                st.rerun()


ASSET_TYPES = [
    "Truck",
    "Trailer",
    "Welder",
    "Lift",
    "Forklift",
    "Generator",
    "Compressor",
    "Tool",
    "Machine",
    "Other",
]


def _safe_date_value(value):
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def _clear_asset_panel() -> None:
    st.session_state.pop("asset_panel_mode", None)
    st.session_state.pop("asset_panel_id", None)


def _inject_asset_side_panel_css() -> None:
    if st.session_state.get(_ASSET_PANEL_CSS_KEY):
        return
    st.session_state[_ASSET_PANEL_CSS_KEY] = True
    st.markdown(
        """
        <style>
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-asset-panel-anchor) {
            background: rgba(15, 23, 42, 0.72) !important;
            border-color: rgba(71, 85, 105, 0.55) !important;
            border-radius: 10px !important;
            padding: 12px 14px 14px 14px !important;
            margin-bottom: 8px !important;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-asset-panel-anchor) h3 {
            color: #e2e8f0 !important;
            font-size: 1.02rem !important;
            font-weight: 650 !important;
            margin: 0 0 10px 0 !important;
            padding-bottom: 8px !important;
            border-bottom: 1px solid rgba(100, 116, 139, 0.35) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_asset_panel_view(row: dict) -> None:
    _inject_asset_side_panel_css()
    with st.container(border=True):
        st.markdown('<span class="ips-asset-panel-anchor"></span>', unsafe_allow_html=True)
        st.markdown("### View asset")
        c_img, c_txt = st.columns([1, 2])
        with c_img:
            _render_asset_list_thumbnail(row)
        with c_txt:
            st.markdown(f"**{_disp(row.get('asset_name'))}**")
            st.caption(
                f"{_disp(row.get('manufacturer'))} · {_disp(row.get('model'))} · "
                f"Serial {_disp(row.get('serial_number'))}"
            )
            st.markdown(f"**Status:** {_disp(row.get('status'))}")
            if _is_checkout_tool_flag(row.get("is_checkout_item")):
                st.caption("Checkout tool — scan in sidebar **Tool Checkout** (QR / asset tag).")
                st.markdown(f"**Last checkout:** {_disp(row.get('last_checkout_at'))}")
                st.markdown(f"**Last check-in:** {_disp(row.get('last_checkin_at'))}")
            st.markdown(f"**Category:** {_disp(row.get('category'))}")
            st.markdown(f"**Location:** {_disp(row.get('location'))}")
            if str(row.get("notes") or "").strip():
                st.markdown(f"**Notes:** {row.get('notes')}")
        b1, b2 = st.columns(2)
        with b1:
            if st.button("Open full profile", use_container_width=True, key="adb_panel_open_detail"):
                _clear_asset_panel()
                st.session_state["asset_detail_id"] = str(row["id"])
                st.session_state[IPS_NAV_PENDING_KEY] = "Asset Detail"
                st.rerun()
        with b2:
            if st.button("Close", use_container_width=True, key="adb_panel_close_view"):
                _clear_asset_panel()
                st.rerun()


def _render_asset_panel_edit(
    row: dict,
    *,
    can_add: bool,
    job_options: dict[str, str | None],
    job_label_by_id: dict,
) -> None:
    if not can_add:
        st.warning("You do not have permission to edit assets.")
        if st.button("Close", use_container_width=True, key="adb_panel_close_edit_ro"):
            _clear_asset_panel()
            st.rerun()
        return

    _inject_asset_side_panel_css()
    rid = str(row.get("id") or "")

    def cv(field: str, default=""):
        v = row.get(field, default)
        return "" if v is None else v

    selected_job_label_default = ""
    _jid = str(row.get("assigned_job_id") or "").strip()
    if _jid and _jid in job_label_by_id:
        selected_job_label_default = job_label_by_id[_jid]

    def pk(s: str) -> str:
        return f"adb_p_{rid}_{s}"

    with st.container(border=True):
        st.markdown('<span class="ips-asset-panel-anchor"></span>', unsafe_allow_html=True)
        st.markdown("### Edit asset")
        # Business asset id (e.g. EQCAT-…) kept for save payload — not shown in the UI.
        asset_id = str(cv("asset_id") or "").strip()

        c1, c2 = st.columns(2)
        asset_name = c1.text_input("Asset Name", value=str(cv("asset_name")), key=pk("name"))
        asset_type = c2.selectbox(
            "Asset Type",
            ASSET_TYPES,
            index=ASSET_TYPES.index(cv("asset_type", "Other"))
            if cv("asset_type", "Other") in ASSET_TYPES
            else ASSET_TYPES.index("Other"),
            key=pk("atype"),
        )

        c4, c5, c6 = st.columns(3)
        serial_number = c4.text_input("Serial Number", value=str(cv("serial_number")), key=pk("sn"))
        manufacturer = c5.text_input("Manufacturer", value=str(cv("manufacturer")), key=pk("mfg"))
        model = c6.text_input("Model", value=str(cv("model")), key=pk("model"))

        c7, c8, c9 = st.columns(3)
        assigned_employee = c7.text_input("Assigned Employee", value=str(cv("assigned_employee")), key=pk("emp"))
        job_keys = [""] + sorted(job_options.keys())
        assigned_job_label = c8.selectbox(
            "Assigned Job",
            job_keys,
            index=job_keys.index(selected_job_label_default) if selected_job_label_default in job_keys else 0,
            key=pk("job"),
        )
        status_default = cv("status", "Available") or "Available"
        if status_default not in ASSET_STATUSES:
            status_default = "Available"
        status = c9.selectbox("Status", ASSET_STATUSES, index=ASSET_STATUSES.index(status_default), key=pk("st"))

        c10, c11, c12 = st.columns(3)
        location = c10.text_input("Location", value=str(cv("location")), key=pk("loc"))
        purchase_date = c11.text_input("Purchase Date (YYYY-MM-DD)", value=str(cv("purchase_date")), key=pk("pd"))
        inspection_due_date = c12.text_input(
            "Inspection Due (YYYY-MM-DD)", value=str(cv("inspection_due_date")), key=pk("insp")
        )

        c13, c14 = st.columns(2)
        maintenance_due_date = c13.text_input(
            "Maintenance Due (YYYY-MM-DD)", value=str(cv("maintenance_due_date")), key=pk("maint")
        )
        is_active = c14.checkbox("Active Asset", value=bool(row.get("is_active", True)), key=pk("active"))

        cat1, cat2 = st.columns(2)
        category = cat1.text_input("Category", value=str(cv("category")), key=pk("cat"))
        subcategory = cat2.text_input("Subcategory", value=str(cv("subcategory")), key=pk("subcat"))

        is_rental = st.checkbox("Rent to Customer", value=bool(row.get("is_rental", False)), key=pk("rental"))
        rental_daily = rental_weekly = rental_monthly = 0.0
        rental_notes_val = str(cv("rental_notes", "") or "")
        if is_rental:
            z1, z2, z3 = st.columns(3)
            rental_daily = z1.number_input(
                "Daily rate",
                min_value=0.0,
                value=float(cv("rental_daily_rate") or 0),
                step=1.0,
                format="%.2f",
                key=pk("rd"),
            )
            rental_weekly = z2.number_input(
                "Weekly rate",
                min_value=0.0,
                value=float(cv("rental_weekly_rate") or 0),
                step=1.0,
                format="%.2f",
                key=pk("rw"),
            )
            rental_monthly = z3.number_input(
                "Monthly rate",
                min_value=0.0,
                value=float(cv("rental_monthly_rate") or 0),
                step=1.0,
                format="%.2f",
                key=pk("rm"),
            )
            rental_notes_val = st.text_area("Rental notes", value=rental_notes_val, height=72, key=pk("rnotes"))

        is_checkout_item = st.checkbox(
            "Checkout tool (possession / Tool Checkout page)",
            value=_is_checkout_tool_flag(row.get("is_checkout_item")),
            key=pk("co_tool"),
            help="Reusable tools tracked via **Tool Checkout** — does not use consumable inventory.",
        )

        notes = st.text_area("Notes", value=str(cv("notes")), height=88, key=pk("notes"))

        u1, u2 = st.columns(2)
        with u1:
            if st.button("Update Asset", type="primary", use_container_width=True, key=pk("save")):
                if not str(asset_name).strip():
                    st.error("Asset Name required")
                    st.stop()
                payload = {
                    "asset_id": str(asset_id).strip() or row.get("asset_id"),
                    "asset_name": str(asset_name).strip(),
                    "asset_type": asset_type,
                    "category": str(category).strip(),
                    "subcategory": str(subcategory).strip(),
                    "serial_number": str(serial_number).strip(),
                    "manufacturer": str(manufacturer).strip(),
                    "model": str(model).strip(),
                    "assigned_employee": str(assigned_employee).strip(),
                    "assigned_job_id": job_options.get(assigned_job_label),
                    "location": str(location).strip(),
                    "status": status,
                    "purchase_date": _safe_date_value(str(purchase_date).strip()),
                    "inspection_due_date": _safe_date_value(str(inspection_due_date).strip()),
                    "maintenance_due_date": _safe_date_value(str(maintenance_due_date).strip()),
                    "notes": str(notes).strip(),
                    "is_active": bool(is_active),
                    "is_rental": bool(is_rental),
                    "rental_notes": str(rental_notes_val).strip(),
                    "is_checkout_item": bool(is_checkout_item),
                }
                if is_rental:
                    payload["rental_daily_rate"] = optional_numeric(rental_daily)
                    payload["rental_weekly_rate"] = optional_numeric(rental_weekly)
                    payload["rental_monthly_rate"] = optional_numeric(rental_monthly)
                try:
                    update_rows_admin("assets", payload, {"id": row["id"]})
                    _clear_asset_panel()
                    st.success("Asset updated.")
                    st.rerun()
                except Exception as exc:
                    low = str(exc).lower()
                    if "is_checkout_item" in low or "current_holder" in low or "last_checkout" in low:
                        st.error(
                            f"Could not update: {exc} — apply migration **`sql/029_tool_checkout.sql`** for checkout fields."
                        )
                    else:
                        st.error(f"Could not update: {exc}")
        with u2:
            if st.button("Close", use_container_width=True, key=pk("close")):
                _clear_asset_panel()
                st.rerun()


_ASSET_DB_LIST_CSS = """
<style>
.ips-adb-card-title-line {
  margin: 0;
  line-height: 1.35;
}
.ips-adb-card-title-line .ips-adb-card-name {
  font-weight: 650;
  font-size: 1.05rem;
  color: inherit;
}
.ips-asset-thumb-placeholder {
  width: 88px;
  height: 88px;
  border-radius: 8px;
  border: 1px dashed rgba(148, 163, 184, 0.45);
  background: rgba(15, 23, 42, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  color: #94a3b8;
  text-align: center;
  line-height: 1.2;
  padding: 6px;
  box-sizing: border-box;
}
/* Rentable assets — IPS dark theme */
.ips-badge-rental {
  display: inline-block;
  margin-left: 10px;
  vertical-align: middle;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #e0f2fe;
  background: linear-gradient(145deg, rgba(14, 165, 233, 0.38), rgba(37, 99, 235, 0.28));
  border: 1px solid rgba(56, 189, 248, 0.5);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.35);
}
.ips-badge-tool {
  display: inline-block;
  margin-left: 8px;
  vertical-align: middle;
  padding: 3px 9px;
  border-radius: 6px;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: #fef3c7;
  background: rgba(245, 158, 11, 0.22);
  border: 1px solid rgba(251, 191, 36, 0.45);
}
.ips-badge-tool-out {
  color: #fecaca;
  background: rgba(239, 68, 68, 0.2);
  border-color: rgba(248, 113, 113, 0.45);
}
</style>
"""


def _render_asset_list_thumbnail(asset_row: dict, *, thumb_px: int = 88) -> None:
    """List thumbnail from ``assets.photo_path`` only; placeholder when missing or unloadable."""
    pp = str(asset_row.get("photo_path") or "").strip()
    ph = (
        f'<div class="ips-asset-thumb-placeholder" style="width:{thumb_px}px;height:{thumb_px}px;" '
        'aria-label="No primary image">No photo</div>'
    )
    if not pp:
        st.markdown(ph, unsafe_allow_html=True)
        return
    url = create_signed_url(pp, expires_in=3600)
    if not url:
        st.markdown(ph, unsafe_allow_html=True)
        return
    try:
        st.image(url, width=thumb_px)
    except Exception:
        st.markdown(ph, unsafe_allow_html=True)


ASSET_TABLE_COLS = [
    "asset_id",
    "asset_name",
    "manufacturer",
    "model",
    "serial_number",
    "status",
    "category",
    "qr_code_value",
]


def _is_equipment_row_cat(val) -> bool:
    return str(val or "").strip().lower() == "equipment"


def _is_rental_row(val) -> bool:
    if val is None or val is pd.NA:
        return False
    try:
        if isinstance(val, (float, int)) and pd.isna(val):
            return False
    except (TypeError, ValueError):
        pass
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    return s in ("true", "1", "yes", "t")


def _is_checkout_tool_flag(val) -> bool:
    if val is None or val is pd.NA:
        return False
    try:
        if isinstance(val, (float, int)) and pd.isna(val):
            return False
    except (TypeError, ValueError):
        pass
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    return s in ("true", "1", "yes", "t")


def _tool_status_badge_class(status: str) -> str:
    stt = str(status or "").strip()
    if stt == "Checked Out":
        return "ips-badge-tool ips-badge-tool-out"
    return "ips-badge-tool"


def _checkout_tool_title_badge(rec: dict) -> str:
    if not _is_checkout_tool_flag(rec.get("is_checkout_item")):
        return ""
    stt = str(rec.get("status") or "").strip() or "—"
    cls = _tool_status_badge_class(stt)
    label = html.escape(stt)
    return f'<span class="{cls}" title="Checkout tool · status">{label}</span>'


def _enrich_asset_table_for_checkout(
    filtered: pd.DataFrame,
    *,
    job_label_by_id: dict,
    emp_by_id: dict[str, str],
) -> pd.DataFrame:
    """Display-only columns for checkout tools (does not mutate persisted rows)."""
    if filtered.empty:
        return filtered
    out = filtered.copy()
    if "is_checkout_item" not in out.columns:
        out["is_checkout_item"] = False
    if "current_holder_employee_id" not in out.columns:
        out["current_holder_employee_id"] = pd.NA
    if "assigned_job_id" not in out.columns:
        out["assigned_job_id"] = pd.NA
    if "assigned_employee" not in out.columns:
        out["assigned_employee"] = ""

    def holder_label(row: pd.Series) -> str:
        eid = str(row.get("current_holder_employee_id") or "").strip()
        if eid and eid in emp_by_id:
            return emp_by_id[eid]
        ae = str(row.get("assigned_employee") or "").strip()
        return ae or "—"

    def job_label(row: pd.Series) -> str:
        jid = row.get("assigned_job_id")
        if jid is None or (isinstance(jid, float) and pd.isna(jid)):
            return "—"
        return str(job_label_by_id.get(str(jid), "—"))

    out["Checkout tool"] = out["is_checkout_item"].map(lambda v: "Yes" if _is_checkout_tool_flag(v) else "")
    out["Held by"] = out.apply(holder_label, axis=1)
    out["On job"] = out.apply(job_label, axis=1)
    return out


def _disp(val) -> str:
    if val is None or val is pd.NA:
        return "—"
    try:
        if isinstance(val, (float, int)) and pd.isna(val):
            return "—"
    except (TypeError, ValueError):
        pass
    s = str(val).strip()
    if not s or s.lower() == "nan":
        return "—"
    return s


def prepare_assets_dataframe(rows: list) -> pd.DataFrame:
    """Normalize columns used by the Asset Database card list (thumbnails, badges, search)."""
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    for col in ASSET_TABLE_COLS:
        if col not in df.columns:
            df[col] = pd.NA
    if "photo_path" not in df.columns:
        df["photo_path"] = pd.NA
    if "is_rental" not in df.columns:
        df["is_rental"] = False
    if "is_checkout_item" not in df.columns:
        df["is_checkout_item"] = False
    if "current_holder_employee_id" not in df.columns:
        df["current_holder_employee_id"] = pd.NA
    if "last_checkout_at" not in df.columns:
        df["last_checkout_at"] = pd.NA
    if "last_checkin_at" not in df.columns:
        df["last_checkin_at"] = pd.NA
    if "qr_code_value" not in df.columns:
        df["qr_code_value"] = ""
    return df


def render_asset_database_card_list(
    records: list[dict],
    *,
    key_prefix: str = "asset_db",
    show_category_in_caption: bool = True,
    mobile_layout: bool = False,
    can_quick_edit: bool = False,
    emp_by_id: dict[str, str] | None = None,
    job_label_by_id: dict | None = None,
) -> None:
    """
    Shared card list: thumbnail, title, Rental badge, caption, Open profile.
    Used by Asset Database and the Equipment filtered view.
    """
    st.markdown(_ASSET_DB_LIST_CSS, unsafe_allow_html=True)
    thumb_px = 92 if mobile_layout else 88
    for i, rec in enumerate(records):
        aid = str(rec.get("id") or "").strip()
        if not aid:
            continue
        rental_badge = (
            '<span class="ips-badge-rental" title="Rent to customer">Rental</span>'
            if _is_rental_row(rec.get("is_rental"))
            else ""
        )
        tool_badge = _checkout_tool_title_badge(rec) if _is_checkout_tool_flag(rec.get("is_checkout_item")) else ""
        meta_lines: list[str] = []
        if show_category_in_caption and str(rec.get("category") or "").strip():
            meta_lines.append(f"Category: {_disp(rec.get('category'))}")
        meta_lines.append(f"Status: {_disp(rec.get('status'))}")
        meta_lines.append(f"Serial: {_disp(rec.get('serial_number'))}")
        if _is_checkout_tool_flag(rec.get("is_checkout_item")):
            meta_lines.append("Checkout tool (use **Tool Checkout**)")
            if emp_by_id:
                eid = str(rec.get("current_holder_employee_id") or "").strip()
                hn = emp_by_id.get(eid) or str(rec.get("assigned_employee") or "").strip()
                if hn:
                    meta_lines.append(f"Holder: {hn}")
            if job_label_by_id and rec.get("assigned_job_id"):
                jl = job_label_by_id.get(str(rec.get("assigned_job_id")), "")
                if jl and jl != "—":
                    meta_lines.append(f"Job: {jl}")
        mm = _disp(rec.get("manufacturer"))
        md = _disp(rec.get("model"))
        if mm != "—" or md != "—":
            meta_lines.append(f"{mm} · {md}" if mm != "—" and md != "—" else (mm if mm != "—" else md))
        meta_text = " · ".join(meta_lines)

        if mobile_layout:
            if i > 0:
                st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown('<span class="ips-adb-card-mobile"></span>', unsafe_allow_html=True)
                c_thumb, c_body = st.columns([1, 2.35], gap="small")
                with c_thumb:
                    _render_asset_list_thumbnail(rec, thumb_px=thumb_px)
                with c_body:
                    st.markdown(
                        '<p class="ips-adb-card-title-line">'
                        f'<span class="ips-adb-card-name">{html.escape(_disp(rec.get("asset_name")))}</span>'
                        f"{rental_badge}{tool_badge}</p>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f'<p class="ips-adb-card-meta">{html.escape(meta_text)}</p>',
                        unsafe_allow_html=True,
                    )
                if st.button(
                    "Open profile",
                    key=f"{key_prefix}_open_{i}_{aid}",
                    type="primary",
                    use_container_width=True,
                ):
                    st.session_state["asset_detail_id"] = aid
                    st.session_state[IPS_NAV_PENDING_KEY] = "Asset Detail"
                    st.rerun()
                if can_quick_edit and st.button(
                    "Quick edit",
                    key=f"{key_prefix}_qedit_{i}_{aid}",
                    type="secondary",
                    use_container_width=True,
                ):
                    st.session_state["asset_panel_mode"] = "edit"
                    st.session_state["asset_panel_id"] = aid
                    st.rerun()
            continue

        if i > 0:
            st.divider()
        ct, cm, cb = st.columns([1.15, 4.2, 1.25], vertical_alignment="center")
        with ct:
            _render_asset_list_thumbnail(rec, thumb_px=thumb_px)
        with cm:
            st.markdown(
                '<p class="ips-adb-card-title-line">'
                f'<span class="ips-adb-card-name">{html.escape(_disp(rec.get("asset_name")))}</span>'
                f"{rental_badge}{tool_badge}</p>",
                unsafe_allow_html=True,
            )
            cat_suffix = ""
            if show_category_in_caption and str(rec.get("category") or "").strip():
                cat_suffix = f" · Category: {_disp(rec.get('category'))}"
            st.caption(
                f"{_disp(rec.get('manufacturer'))} · {_disp(rec.get('model'))} · "
                f"Serial: {_disp(rec.get('serial_number'))} · Status: {_disp(rec.get('status'))}"
                + cat_suffix
            )
        with cb:
            if st.button("Open profile", key=f"{key_prefix}_open_{i}_{aid}", use_container_width=True):
                st.session_state["asset_detail_id"] = aid
                st.session_state[IPS_NAV_PENDING_KEY] = "Asset Detail"
                st.rerun()
    st.caption(
        "Thumbnails use each asset’s **primary image** (`photo_path`). "
        "Use **Open profile** to view details, rental rates, and the image gallery."
    )


def render() -> None:
    inject_asset_workflow_mobile_css()
    ensure_narrow_viewport_detected()
    _inject_asset_database_mobile_css()
    render_header("Asset Database")
    render_crud_list_subtitle(
        "Filter and browse assets. Use Table for checkboxes, export, and bulk delete; Cards when you want photo-first browsing."
    )

    can_add = current_role() in {"admin", "estimator"}
    if "asset_db_add_mode" not in st.session_state:
        st.session_state["asset_db_add_mode"] = False

    if can_add and st.session_state.get("asset_db_add_mode"):
        if st.button("← Back to list", key="asset_db_back", use_container_width=True):
            st.session_state["asset_db_add_mode"] = False
            st.rerun()
        st.caption("Intake: AI photos, review, duplicate check, then save.")
        st.subheader("New asset")
        render_asset_intake_form()
        return

    rows = fetch_table("assets", limit=5000, order_by="asset_name")
    jobs_raw = fetch_table("jobs", limit=5000, order_by="job_number")
    jobs = sort_jobs_by_number_then_name(jobs_raw)
    job_label_by_id = {str(j.get("id")): job_row_select_label(j) for j in jobs if j.get("id")}
    job_options = {
        job_row_select_label(j): j.get("id")
        for j in jobs
        if job_row_select_label(j) and job_row_select_label(j) != "—"
    }
    try:
        emp_rows = fetch_table("employees", columns="id,name", limit=4000, order_by="name")
    except Exception:
        emp_rows = []
    emp_by_id: dict[str, str] = {str(e["id"]): str(e.get("name") or "").strip() for e in emp_rows if e.get("id")}

    panel_mode = st.session_state.get("asset_panel_mode")
    panel_id = st.session_state.get("asset_panel_id")
    panel_row = None
    if panel_mode in ("view", "edit") and panel_id:
        panel_row = fetch_one("assets", {"id": panel_id})
        if not panel_row:
            _clear_asset_panel()
            panel_mode = None
            panel_id = None

    panel_open = bool(panel_row and panel_mode in ("view", "edit"))

    df = prepare_assets_dataframe(rows)

    def _render_list_block(*, filtered: pd.DataFrame, view_mode: str, emp_by_id: dict[str, str]) -> None:
        is_narrow = st.session_state.get("ips_viewport_narrow") is True
        if view_mode == "Cards":
            st.caption(
                "Card view — switch to **Table** for row selection, export, and bulk delete."
            )
            st.subheader("Browse by photo")
            render_asset_database_card_list(
                filtered.to_dict("records"),
                key_prefix="asset_db",
                show_category_in_caption=True,
                mobile_layout=is_narrow,
                can_quick_edit=can_add,
                emp_by_id=emp_by_id,
                job_label_by_id=job_label_by_id,
            )
            return

        if is_narrow:
            st.info(
                "**Table** on a phone can feel tight. Prefer **Cards** for browsing in the field; "
                "use **Table** when you need checkboxes, export, or bulk delete."
            )
        st.caption("Checkbox column on the left — action bar sits directly under the grid.")
        disp = _enrich_asset_table_for_checkout(filtered, job_label_by_id=job_label_by_id, emp_by_id=emp_by_id)
        table_cols = [
            c
            for c in [
                "asset_name",
                "asset_id",
                "serial_number",
                "status",
                "Checkout tool",
                "Held by",
                "On job",
                "manufacturer",
                "model",
                "category",
                "is_rental",
            ]
            if c in disp.columns
        ]
        if "id" not in disp.columns:
            st.dataframe(disp[table_cols], use_container_width=True, hide_index=True)
            return

        _, sel = render_selectable_dataframe(
            disp,
            table_key=TABLE_KEY_ASSETS,
            id_column="id",
            columns=table_cols,
            editor_key="asset_db_sel_editor",
            hide_id_column=True,
        )
        actions = render_selection_action_bar(
            TABLE_KEY_ASSETS,
            sel,
            can_view=True,
            can_edit=can_add,
            can_delete=can_add,
            export_df=disp,
            visible_df=disp,
            id_column="id",
            export_filename="asset_database_export.csv",
            view_label="View Asset",
            edit_label="Edit Asset",
            delete_label="Delete Asset",
            delete_selected_label="Delete Selected",
        )
        if actions.get("view") and sel and len(sel) == 1:
            st.session_state["asset_panel_mode"] = "view"
            st.session_state["asset_panel_id"] = str(sel[0])
            st.rerun()
        if actions.get("edit") and sel and len(sel) == 1 and can_add:
            st.session_state["asset_panel_mode"] = "edit"
            st.session_state["asset_panel_id"] = str(sel[0])
            st.rerun()
        pend = st.session_state.get(IPS_PENDING_DELETE) or {}
        if actions.get("confirm_delete") and pend.get(TABLE_KEY_ASSETS) and can_add:
            deleted = list(pend[TABLE_KEY_ASSETS])
            for aid in deleted:
                try:
                    delete_rows_admin("assets", {"id": aid})
                except Exception as exc:
                    st.error(f"Could not delete {aid}: {exc}")
            pend.pop(TABLE_KEY_ASSETS, None)
            clear_selected_ids(TABLE_KEY_ASSETS)
            pid = st.session_state.get("asset_panel_id")
            if pid and str(pid) in {str(x) for x in deleted}:
                _clear_asset_panel()
            st.success("Delete completed where permitted.")
            st.rerun()

    def _render_main_column() -> None:
        inject_table_action_styles()
        is_narrow = st.session_state.get("ips_viewport_narrow") is True

        if not st.session_state.get("asset_db_view_user_chose"):
            vn = st.session_state.get("ips_viewport_narrow")
            if vn is not None and not st.session_state.get("asset_db_vp_default_done"):
                st.session_state["asset_db_view_mode"] = "Cards" if vn else "Table"
                st.session_state["asset_db_vp_default_done"] = True

        st.session_state.setdefault("asset_db_view_mode", "Cards")
        vm = str(st.session_state.get("asset_db_view_mode", "Cards"))
        _inject_asset_db_top_actions_css()

        if is_narrow:
            st.caption(
                "Search and filters below — **Cards** is the default on phones. "
                "Use **Table** when you need export or bulk delete."
            )
            with st.container(border=True):
                st.markdown('<span class="ips-list-top-anchor"></span>', unsafe_allow_html=True)
                _render_asset_db_top_action_row(vm=vm, can_add=can_add)

            if df.empty:
                st.info("No assets found.")
                if can_add:
                    st.caption("Use **New Asset** for intake or **Asset Scanner** above.")
                return

            st.text_input(
                "Search Assets",
                placeholder="Search name, manufacturer, model, serial, status, category",
                key="asset_db_f_search",
            )
            statuses = sorted(
                [
                    s
                    for s in df.get("status", pd.Series(dtype=str))
                    .dropna()
                    .astype(str)
                    .unique()
                    .tolist()
                    if str(s).strip()
                ]
            )
            st.selectbox("Filter Status", ["All"] + statuses, key="asset_db_f_status")
            scope_options = ["All", "Rental Only", "Equipment Only", "Checkout tools only"]
            st.selectbox("Show", scope_options, key="asset_db_f_scope")
            serial_options = ["All", "Has serial", "No serial"]
            st.selectbox("Serial #", serial_options, key="asset_db_f_serial")
            st.caption(
                "**Show** filters rentable assets or **Equipment** category. "
                "View mode switches are in the top row above."
            )

        else:
            with st.container(border=True):
                st.markdown('<span class="ips-list-top-anchor"></span>', unsafe_allow_html=True)
                _render_asset_db_top_action_row(vm=vm, can_add=can_add)

            if df.empty:
                st.info("No assets found.")
                if can_add:
                    st.caption("Use **New Asset** for intake or **Asset Scanner** above.")
                return

            filter_cols = st.columns([1, 2, 1])
            statuses = sorted(
                [
                    s
                    for s in df.get("status", pd.Series(dtype=str))
                    .dropna()
                    .astype(str)
                    .unique()
                    .tolist()
                    if str(s).strip()
                ]
            )
            with filter_cols[0]:
                st.markdown('<span class="ips-adb-filter-row"></span>', unsafe_allow_html=True)
                st.selectbox("Filter Status", ["All"] + statuses, key="asset_db_f_status")
            filter_cols[1].text_input(
                "Search Assets",
                placeholder="Search name, manufacturer, model, serial, status, category",
                key="asset_db_f_search",
            )
            serial_options = ["All", "Has serial", "No serial"]
            filter_cols[2].selectbox("Serial #", serial_options, key="asset_db_f_serial")

            filter_cols2 = st.columns([1, 3])
            scope_options = ["All", "Rental Only", "Equipment Only", "Checkout tools only"]
            with filter_cols2[0]:
                st.markdown('<span class="ips-adb-filter-row2"></span>', unsafe_allow_html=True)
                st.selectbox("Show", scope_options, key="asset_db_f_scope")
            filter_cols2[1].caption(
                "Filter by rentable assets or **Equipment** category. **Cards** / **Table** is in the bar above."
            )

        selected_status = st.session_state.get("asset_db_f_status", "All")
        search = st.session_state.get("asset_db_f_search", "")
        selected_serial = st.session_state.get("asset_db_f_serial", "All")
        selected_scope = st.session_state.get("asset_db_f_scope", "All")

        filtered = df.copy()
        if selected_status != "All" and "status" in filtered.columns:
            filtered = filtered[filtered["status"].astype(str) == selected_status]
        if selected_serial == "Has serial" and "serial_number" in filtered.columns:
            sn = filtered["serial_number"].astype(str).str.strip()
            filtered = filtered[sn.ne("") & sn.ne("nan") & filtered["serial_number"].notna()]
        elif selected_serial == "No serial" and "serial_number" in filtered.columns:
            sn = filtered["serial_number"].astype(str).str.strip()
            filtered = filtered[filtered["serial_number"].isna() | sn.eq("") | sn.eq("nan")]
        if selected_scope == "Rental Only" and "is_rental" in filtered.columns:
            filtered = filtered[filtered["is_rental"].map(_is_rental_row)]
        elif selected_scope == "Equipment Only" and "category" in filtered.columns:
            filtered = filtered[filtered["category"].map(_is_equipment_row_cat)]
        elif selected_scope == "Checkout tools only" and "is_checkout_item" in filtered.columns:
            filtered = filtered[filtered["is_checkout_item"].map(_is_checkout_tool_flag)]
        if search.strip():
            s = search.strip().lower()
            search_cols = [c for c in ASSET_TABLE_COLS if c in filtered.columns]
            if search_cols:
                mask = filtered[search_cols].astype(str).apply(lambda col: col.str.lower().str.contains(s, na=False))
                filtered = filtered[mask.any(axis=1)]

        if filtered.empty:
            st.warning("No assets match your filters.")
        else:
            _render_list_block(
                filtered=filtered,
                view_mode=str(st.session_state.get("asset_db_view_mode", "Cards")),
                emp_by_id=emp_by_id,
            )

    if panel_open and panel_row is not None:
        stack_panel = st.session_state.get("ips_viewport_narrow") is True
        if stack_panel:
            _render_main_column()
            if panel_mode == "view":
                _render_asset_panel_view(panel_row)
            else:
                _render_asset_panel_edit(
                    panel_row,
                    can_add=can_add,
                    job_options=job_options,
                    job_label_by_id=job_label_by_id,
                )
        else:
            left, right = st.columns([2.2, 1.1], gap="medium")
            with left:
                _render_main_column()
            with right:
                if panel_mode == "view":
                    _render_asset_panel_view(panel_row)
                else:
                    _render_asset_panel_edit(
                        panel_row,
                        can_add=can_add,
                        job_options=job_options,
                        job_label_by_id=job_label_by_id,
                    )
    else:
        _render_main_column()
