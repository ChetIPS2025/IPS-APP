"""Weekly job timesheet — build, save, render HTML/PDF, and customer sign-off."""

from __future__ import annotations

import base64
import html
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

from app.branding import get_header_logo_path, header_logo_html
from app.utils.formatting import fmt_hours, fmt_money
from app.db import (
    create_signed_url,
    delete_rows_admin,
    fetch_by_match_admin,
    fetch_table_admin,
    insert_row_admin,
    update_rows_admin,
    upload_bytes_admin,
)
from app.services.job_weekly_timesheets import monday_of_week, week_bounds
_TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "templates" / "weekly_job_timesheet.html"
_FALLBACK_TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "weekly_timesheet_form.html"

TIMESHEET_TABLE = "weekly_timesheets"
TIMESHEET_LINES_TABLE = "weekly_timesheet_lines"
TIMESHEET_TABLE_MISSING_MSG = "Weekly timesheets table is missing. Run the weekly timesheet migration."

_SHEET_TABLE = TIMESHEET_TABLE
_LINES_TABLE = TIMESHEET_LINES_TABLE
_STORAGE_PREFIX = "weekly_timesheets"
_table_available: bool | None = None

_DAY_KEYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
TIMESHEET_LABOR_MIN_ROWS = 10
TIMESHEET_MATERIAL_MIN_ROWS = 6
TIMESHEET_CHARGE_MIN_ROWS = 4
TIMESHEET_PAGE_MIN_HEIGHT = "10.5in"
TIMESHEET_CONTENT_WIDTH = "8in"
TIMESHEET_GRID_ROW_HEIGHT = "0.26in"
TIMESHEET_GRID_HEAD_HEIGHT = "0.30in"
_HOUR_COLS = ("hours_mon", "hours_tue", "hours_wed", "hours_thu", "hours_fri", "hours_sat", "hours_sun")
_LEGACY_HOUR_COLS = (
    ("mon", "hours_mon", "monday_st"),
    ("tue", "hours_tue", "tuesday_st"),
    ("wed", "hours_wed", "wednesday_st"),
    ("thu", "hours_thu", "thursday_st"),
    ("fri", "hours_fri", "friday_st"),
    ("sat", "hours_sat", "saturday_st"),
    ("sun", "hours_sun", "sunday_st"),
)


def _is_missing_table_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return "could not find" in msg or "does not exist" in msg


def timesheet_table_available(*, force: bool = False) -> bool:
    """Return False when ``public.weekly_timesheets`` is not present (graceful UI fallback)."""
    global _table_available
    if not force and _table_available is not None:
        return _table_available
    try:
        fetch_table_admin(TIMESHEET_TABLE, columns="id", limit=1)
        _table_available = True
    except Exception as exc:
        if _is_missing_table_error(exc):
            _table_available = False
        else:
            raise
    return bool(_table_available)


def ensure_timesheet_table() -> None:
    if not timesheet_table_available():
        raise RuntimeError(TIMESHEET_TABLE_MISSING_MSG)


def _day_hours(row: dict[str, Any], _day: str, legacy_col: str, modern_col: str) -> float:
    for key in (legacy_col, modern_col):
        if key in row and row.get(key) is not None:
            val = _num(row.get(key))
            if val or str(row.get(key) or "").strip():
                return val
    return 0.0


def _parse_date(v: Any) -> date | None:
    if v is None:
        return None
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    try:
        return date.fromisoformat(str(v).strip()[:10])
    except ValueError:
        return None


def _num(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


@dataclass
class TimesheetLine:
    line_type: str = "labor"
    description: str = ""
    class_name: str = ""
    mon: float = 0.0
    tue: float = 0.0
    wed: float = 0.0
    thu: float = 0.0
    fri: float = 0.0
    sat: float = 0.0
    sun: float = 0.0
    st_hours: float = 0.0
    ot_hours: float = 0.0
    dt_hours: float = 0.0
    qty: float = 0.0
    cost: float = 0.0
    unit: str = ""
    unit_cost: float = 0.0
    markup_pct: float = 0.0
    sort_order: int = 0

    @property
    def charge_unit(self) -> str:
        return str(self.unit or self.class_name or "").strip()

    @property
    def line_total(self) -> float:
        if self.cost > 0:
            return round(self.cost, 2)
        if self.qty > 0 and self.unit_cost > 0:
            return round(self.qty * self.unit_cost, 2)
        return 0.0

    def markup_label(self) -> str:
        if self.markup_pct > 0.005:
            return f"{self.markup_pct:.1f}%"
        return "—"

    @property
    def total_hours(self) -> float:
        return round(self.st_hours + self.ot_hours + self.dt_hours, 2)

    @property
    def day_total(self) -> float:
        return round(self.mon + self.tue + self.wed + self.thu + self.fri + self.sat + self.sun, 2)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WeeklyJobTimesheetData:
    job_id: str = ""
    job_number: str = ""
    client_name: str = ""
    job_name: str = ""
    po_number: str = ""
    sheet_date: str = ""
    week_start: str = ""
    week_end: str = ""
    approved_by: str = ""
    work_performed: str = ""
    status: str = "Draft"
    signature_data: str = ""
    signed_at: str = ""
    labor_lines: list[TimesheetLine] = field(default_factory=list)
    material_lines: list[TimesheetLine] = field(default_factory=list)
    equipment_lines: list[TimesheetLine] = field(default_factory=list)
    other_lines: list[TimesheetLine] = field(default_factory=list)

    def to_snapshot(self) -> dict[str, Any]:
        return {
            "header": {
                "job_id": self.job_id,
                "job_number": self.job_number,
                "client_name": self.client_name,
                "job_name": self.job_name,
                "po_number": self.po_number,
                "sheet_date": self.sheet_date,
                "week_start": self.week_start,
                "week_end": self.week_end,
                "approved_by": self.approved_by,
                "work_performed": self.work_performed,
                "status": self.status,
            },
            "labor_lines": [ln.to_dict() for ln in self.labor_lines],
            "material_lines": [ln.to_dict() for ln in self.material_lines],
            "equipment_lines": [ln.to_dict() for ln in self.equipment_lines],
            "other_lines": [ln.to_dict() for ln in self.other_lines],
        }

    @classmethod
    def from_snapshot(cls, snap: dict[str, Any]) -> WeeklyJobTimesheetData:
        hdr = dict(snap.get("header") or {})
        labor = [TimesheetLine(**{k: v for k, v in ln.items() if k in TimesheetLine.__dataclass_fields__}) for ln in snap.get("labor_lines") or []]
        mats = [TimesheetLine(**{k: v for k, v in ln.items() if k in TimesheetLine.__dataclass_fields__}) for ln in snap.get("material_lines") or []]
        equip = [TimesheetLine(**{k: v for k, v in ln.items() if k in TimesheetLine.__dataclass_fields__}) for ln in snap.get("equipment_lines") or []]
        other = [TimesheetLine(**{k: v for k, v in ln.items() if k in TimesheetLine.__dataclass_fields__}) for ln in snap.get("other_lines") or []]
        if not equip:
            equip = [ln for ln in labor if ln.line_type == "equipment"]
            labor = [ln for ln in labor if ln.line_type == "labor"]
        if not other:
            other = [ln for ln in mats if ln.line_type == "expense"]
            mats = [ln for ln in mats if ln.line_type != "expense"]
        return cls(
            job_id=str(hdr.get("job_id") or ""),
            job_number=str(hdr.get("job_number") or ""),
            client_name=str(hdr.get("client_name") or ""),
            job_name=str(hdr.get("job_name") or ""),
            po_number=str(hdr.get("po_number") or ""),
            sheet_date=str(hdr.get("sheet_date") or ""),
            week_start=str(hdr.get("week_start") or ""),
            week_end=str(hdr.get("week_end") or ""),
            approved_by=str(hdr.get("approved_by") or ""),
            work_performed=str(hdr.get("work_performed") or ""),
            status=str(hdr.get("status") or "Draft"),
            labor_lines=labor,
            material_lines=mats,
            equipment_lines=equip,
            other_lines=other,
        )


def _empty_labor_row() -> TimesheetLine:
    return TimesheetLine(line_type="labor")


def _pad_labor_rows(lines: list[TimesheetLine], min_rows: int = 8) -> list[TimesheetLine]:
    out = list(lines)
    while len(out) < min_rows:
        out.append(_empty_labor_row())
    return out


def _pad_material_rows(lines: list[TimesheetLine], min_rows: int = 6) -> list[TimesheetLine]:
    out = list(lines)
    while len(out) < min_rows:
        out.append(TimesheetLine(line_type="material"))
    return out


def _pad_charge_rows(lines: list[TimesheetLine], min_rows: int = TIMESHEET_CHARGE_MIN_ROWS) -> list[TimesheetLine]:
    out = [ln for ln in lines if ln.description or ln.qty or ln.line_total]
    while len(out) < min_rows:
        out.append(TimesheetLine(line_type="material"))
    return out


def _weekly_summary(data: WeeklyJobTimesheetData) -> dict[str, float]:
    labor_hours = round(
        sum(ln.total_hours for ln in data.labor_lines if ln.line_type == "labor"),
        2,
    )
    materials = round(sum(ln.line_total for ln in data.material_lines), 2)
    equipment = round(sum(ln.line_total for ln in data.equipment_lines), 2)
    other = round(sum(ln.line_total for ln in data.other_lines), 2)
    charges = round(materials + equipment + other, 2)
    return {
        "labor_hours": labor_hours,
        "materials": materials,
        "equipment": equipment,
        "other": other,
        "charges": charges,
        "grand_total": charges,
    }


def _charge_row_html(ln: TimesheetLine) -> str:
    unit_cost = ln.unit_cost
    if not unit_cost and ln.qty > 0 and ln.line_total > 0:
        unit_cost = round(ln.line_total / ln.qty, 4)
    return (
        f"<tr>"
        f'<td class="left">{html.escape(ln.description)}</td>'
        f'<td class="num">{html.escape(fmt_hours(ln.qty, empty_zero=True))}</td>'
        f'<td class="left">{html.escape(ln.charge_unit)}</td>'
        f'<td class="num">{html.escape(fmt_money(unit_cost, empty="", zero_as_empty=True))}</td>'
        f'<td class="num">{html.escape(ln.markup_label())}</td>'
        f'<td class="num">{html.escape(fmt_money(ln.line_total, empty="", zero_as_empty=True))}</td>'
        f"</tr>"
    )


def _summary_row_html(label: str, value: str, *, bold: bool = False) -> str:
    weight = "font-weight:800;" if bold else ""
    return (
        f"<tr>"
        f'<td class="left" style="{weight}">{html.escape(label)}</td>'
        f'<td class="num" style="{weight}">{html.escape(value)}</td>'
        f"</tr>"
    )


def _summary_table_html(data: WeeklyJobTimesheetData) -> str:
    totals = _weekly_summary(data)
    rows = [
        _summary_row_html("Approved labor hours", fmt_hours(totals["labor_hours"], empty_zero=True)),
        _summary_row_html("Inventory / materials", fmt_money(totals["materials"], empty="", zero_as_empty=True)),
        _summary_row_html("Equipment", fmt_money(totals["equipment"], empty="", zero_as_empty=True)),
        _summary_row_html("Other charges", fmt_money(totals["other"], empty="", zero_as_empty=True)),
        _summary_row_html("Weekly charges total", fmt_money(totals["charges"], empty="", zero_as_empty=True), bold=True),
    ]
    return "".join(rows)


def _infer_charge_unit(txn: dict[str, Any]) -> str:
    notes = str(txn.get("notes") or "").lower()
    for token, unit in (
        ("(hour)", "hr"),
        ("(day)", "day"),
        ("(week)", "week"),
        ("(month)", "month"),
    ):
        if token in notes:
            return unit
    cat = str(txn.get("cost_category") or "").strip().lower()
    qty = _num(txn.get("quantity"))
    if cat in {"equipment", "rental"}:
        if qty and qty <= 24 and "hour" in notes:
            return "hr"
        if qty and qty >= 1 and qty <= 31:
            return "day"
        return "ea"
    if cat == "material":
        return "ea"
    if cat in {"subcontract", "other"}:
        return "ea"
    return "ea"


def _markup_from_txn(txn: dict[str, Any]) -> float:
    asset_id = str(txn.get("asset_id") or "").strip()
    if not asset_id:
        return 0.0
    rows = _safe_admin_fetch("assets", {"id": asset_id}, limit=1)
    if not rows:
        return 0.0
    return _num(rows[0].get("rental_default_markup_percent"))


def _txn_to_charge_line(txn: dict[str, Any], line_type: str) -> TimesheetLine:
    qty = _num(txn.get("quantity"))
    unit_cost = _num(txn.get("unit_cost"))
    total = _num(txn.get("total_cost"))
    if total <= 0 and qty > 0 and unit_cost > 0:
        total = round(qty * unit_cost, 2)
    desc = str(txn.get("description") or txn.get("item_name") or "").strip()
    if not desc:
        desc = str(txn.get("cost_category") or "Charge").strip().title()
    return TimesheetLine(
        line_type=line_type,
        description=desc,
        unit=_infer_charge_unit(txn),
        qty=qty or (1.0 if total > 0 else 0.0),
        unit_cost=unit_cost or (round(total / qty, 4) if qty > 0 else total),
        markup_pct=_markup_from_txn(txn),
        cost=total,
    )


def _build_charges_from_job_cost_transactions(
    job_id: str,
    ws: date,
    we: date,
) -> tuple[list[TimesheetLine], list[TimesheetLine], list[TimesheetLine]]:
    from app.services.job_cost_transaction_service import (
        COST_EQUIPMENT,
        COST_LABOR,
        COST_MATERIAL,
        COST_OTHER,
        COST_RENTAL,
        COST_SUBCONTRACT,
        fetch_job_cost_transactions,
        transaction_show_on_invoice,
    )
    materials: list[TimesheetLine] = []
    equipment: list[TimesheetLine] = []
    other: list[TimesheetLine] = []
    for txn in fetch_job_cost_transactions(job_id):
        txn_date = _parse_date(txn.get("transaction_date"))
        if txn_date is None or txn_date < ws or txn_date > we:
            continue
        cat = str(txn.get("cost_category") or "").strip().lower()
        if cat == COST_LABOR:
            continue
        total = _num(txn.get("total_cost"))
        if total <= 0:
            continue
        if not transaction_show_on_invoice(txn):
            continue
        if cat == COST_MATERIAL:
            materials.append(_txn_to_charge_line(txn, "material"))
        elif cat in {COST_EQUIPMENT, COST_RENTAL}:
            equipment.append(_txn_to_charge_line(txn, "equipment"))
        elif cat in {COST_SUBCONTRACT, COST_OTHER}:
            other.append(_txn_to_charge_line(txn, "expense"))
        else:
            other.append(_txn_to_charge_line(txn, "expense"))
    key_fn = lambda ln: ln.description.lower()
    return (
        sorted(materials, key=key_fn),
        sorted(equipment, key=key_fn),
        sorted(other, key=key_fn),
    )


def _split_materials(lines: list[TimesheetLine]) -> tuple[list[TimesheetLine], list[TimesheetLine]]:
    padded = _pad_material_rows(lines, 12)
    mid = (len(padded) + 1) // 2
    return padded[:mid], padded[mid:]


def _day_labels(week_start: date) -> list[str]:
    labels = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    return [f"{labels[i]}<br>{(week_start + timedelta(days=i)).strftime('%m/%d')}" for i in range(7)]


def _labor_row_html(ln: TimesheetLine) -> str:
    days = [ln.mon, ln.tue, ln.wed, ln.thu, ln.fri, ln.sat, ln.sun]
    cells = "".join(f'<td class="num">{html.escape(fmt_hours(d, empty_zero=True))}</td>' for d in days)
    return (
        f"<tr>"
        f'<td class="left">{html.escape(ln.description)}</td>'
        f'<td class="left">{html.escape(ln.class_name)}</td>'
        f"{cells}"
        f'<td class="num">{html.escape(fmt_hours(ln.st_hours, empty_zero=True))}</td>'
        f'<td class="num">{html.escape(fmt_hours(ln.ot_hours + ln.dt_hours, empty_zero=True))}</td>'
        f'<td class="num">{html.escape(fmt_hours(ln.total_hours, empty_zero=True))}</td>'
        f"</tr>"
    )


def _material_row_html(ln: TimesheetLine) -> str:
    return _charge_row_html(ln)


def _signature_html(signature_data: str) -> str:
    sig = str(signature_data or "").strip()
    if not sig:
        return '<div style="height:36px;border-bottom:1px solid #000;margin-top:8px;"></div>'
    src = sig if sig.startswith("data:") else f"data:image/png;base64,{sig}"
    return f'<img src="{src}" alt="Signature"/>'


def render_timesheet_html(
    data: WeeklyJobTimesheetData,
    *,
    week_start: date | None = None,
    embed: bool = False,
) -> str:
    """Render printable HTML from template."""
    ws = _parse_date(data.week_start) or week_start or date.today()
    ws = monday_of_week(ws)
    labels = _day_labels(ws)
    template_path = _TEMPLATE_PATH if _TEMPLATE_PATH.is_file() else _FALLBACK_TEMPLATE
    template = template_path.read_text(encoding="utf-8")
    labor = _pad_labor_rows(
        [ln for ln in data.labor_lines if ln.line_type == "labor"],
        min_rows=TIMESHEET_LABOR_MIN_ROWS,
    )
    materials = _pad_charge_rows(data.material_lines, TIMESHEET_CHARGE_MIN_ROWS)
    equipment = _pad_charge_rows(data.equipment_lines, TIMESHEET_CHARGE_MIN_ROWS)
    other = _pad_charge_rows(data.other_lines, TIMESHEET_CHARGE_MIN_ROWS)
    logo = header_logo_html(height=48) or "IPS"
    replacements = {
        "{{body_class}}": "ips-wt-embed" if embed else "",
        "{{logo_html}}": logo,
        "{{job_number}}": html.escape(data.job_number),
        "{{client_name}}": html.escape(data.client_name),
        "{{job_name}}": html.escape(data.job_name),
        "{{po_number}}": html.escape(data.po_number),
        "{{sheet_date}}": html.escape(data.sheet_date),
        "{{day_mon_label}}": labels[0],
        "{{day_tue_label}}": labels[1],
        "{{day_wed_label}}": labels[2],
        "{{day_thu_label}}": labels[3],
        "{{day_fri_label}}": labels[4],
        "{{day_sat_label}}": labels[5],
        "{{day_sun_label}}": labels[6],
        "{{labor_rows_html}}": "".join(_labor_row_html(ln) for ln in labor),
        "{{materials_rows_html}}": "".join(_charge_row_html(ln) for ln in materials),
        "{{equipment_rows_html}}": "".join(_charge_row_html(ln) for ln in equipment),
        "{{other_rows_html}}": "".join(_charge_row_html(ln) for ln in other),
        "{{summary_rows_html}}": _summary_table_html(data),
        "{{work_performed}}": html.escape(data.work_performed),
        "{{approved_by}}": html.escape(data.approved_by),
        "{{signature_html}}": _signature_html(data.signature_data),
        "{{signed_date}}": html.escape(data.signed_at[:10] if data.signed_at else ""),
    }
    out = template
    for k, v in replacements.items():
        out = out.replace(k, v)
    return out


def build_timesheet_pdf_bytes(data: WeeklyJobTimesheetData) -> bytes:
    """Portrait PDF export matching TIMESHEET WEEKLY layout."""
    from app.services.weekly_timesheet_export_service import export_data_to_pdf
    return export_data_to_pdf(data)


def _safe_admin_fetch(table: str, match: dict[str, Any], *, limit: int = 500) -> list[dict[str, Any]]:
    try:
        return fetch_by_match_admin(table, match, limit=limit) or []
    except Exception as exc:
        if _is_missing_table_error(exc):
            return []
        raise


def _fetch_job(job_id: str) -> dict[str, Any]:
    rows = fetch_by_match_admin("jobs", {"id": job_id}, limit=1)
    return rows[0] if rows else {}


def _fetch_customer_name(customer_id: str | None) -> str:
    if not customer_id:
        return ""
    rows = fetch_by_match_admin("customers", {"id": customer_id}, limit=1)
    return str(rows[0].get("customer_name") or "") if rows else ""


def _fetch_po_for_job(job: dict[str, Any]) -> str:
    est_id = str(job.get("estimate_id") or "").strip()
    if est_id:
        rows = fetch_by_match_admin("estimates", {"id": est_id}, limit=1)
        if rows:
            return str(rows[0].get("po_number") or rows[0].get("customer_po") or "").strip()
    jid = str(job.get("id") or "")
    if jid:
        rows = fetch_by_match_admin("estimates", {"job_id": jid}, limit=1)
        if rows:
            return str(rows[0].get("po_number") or rows[0].get("customer_po") or "").strip()
    return str(job.get("po_number") or "").strip()


def _employees_map() -> dict[str, dict[str, Any]]:
    rows = fetch_table_admin("employees", limit=5000, order_by="name")
    return {str(r.get("id")): r for r in rows if r.get("id")}


def _timekeeping_row_matches_job(job_id: str, job: dict[str, Any], row: dict[str, Any]) -> bool:
    if str(row.get("job_id") or "") == job_id:
        return True
    label = str(row.get("job_label") or "").strip()
    low = label.lower()
    if not label or low in {"— no job —", "- no job -", "no job", "none", "—", "-"}:
        return False
    from app.services.jobs_service import resolve_job_id_from_label
    resolved = resolve_job_id_from_label(label)
    if resolved and resolved == job_id:
        return True
    job_num = str(job.get("job_number") or "").strip()
    job_name = str(job.get("job_name") or "").strip()
    if job_num and label.startswith(job_num):
        return True
    friendly = f"{job_num} — {job_name}" if job_num and job_name else job_num or job_name
    return bool(friendly and label == friendly)


def _build_labor_from_timekeeping_days(
    job_id: str,
    ws: date,
    we: date,
    emp_map: dict[str, dict],
    *,
    approved_only: bool = True,
) -> list[TimesheetLine]:
    job = _fetch_job(job_id)
    rows = fetch_table_admin("employee_timekeeping_days", limit=20000)
    buckets: dict[tuple[str, str], TimesheetLine] = {}
    for row in rows:
        if approved_only and str(row.get("status") or "").strip().lower() != "approved":
            continue
        if not _timekeeping_row_matches_job(job_id, job, row):
            continue
        wd = _parse_date(row.get("work_date"))
        if wd is None or wd < ws or wd > we:
            continue
        di = (wd - ws).days
        if di < 0 or di > 6:
            continue
        eid = str(row.get("employee_id") or "")
        emp = emp_map.get(eid, {})
        name = str(emp.get("name") or row.get("employee_name") or "Unknown").strip()
        cls = str(emp.get("trade") or emp.get("department") or row.get("job_label") or "").strip()
        key = (name, cls)
        if key not in buckets:
            buckets[key] = TimesheetLine(line_type="labor", description=name, class_name=cls)
        ln = buckets[key]
        st = _num(row.get("st_hours"))
        ot = _num(row.get("ot_hours"))
        dt = _num(row.get("dt_hours"))
        day_total = st + ot + dt
        setattr(ln, _DAY_KEYS[di], getattr(ln, _DAY_KEYS[di]) + day_total)
        ln.st_hours += st
        ln.ot_hours += ot
        ln.dt_hours += dt
    return sorted(buckets.values(), key=lambda x: (x.description.lower(), x.class_name.lower()))


def _build_labor_from_time_entries(job_id: str, ws: date, we: date, emp_map: dict[str, dict]) -> list[TimesheetLine]:
    rows = fetch_table_admin("time_entries", limit=50000)
    buckets: dict[tuple[str, str], TimesheetLine] = {}
    for row in rows:
        if str(row.get("job_id") or "") != job_id:
            continue
        wd = _parse_date(row.get("work_date"))
        if wd is None or wd < ws or wd > we:
            continue
        di = (wd - ws).days
        if di < 0 or di > 6:
            continue
        eid = str(row.get("employee_id") or "")
        emp = emp_map.get(eid, {})
        name = str(emp.get("name") or "Unknown").strip()
        cls = str(emp.get("trade") or emp.get("department") or "").strip()
        ttype = str(row.get("time_type") or "ST").strip().upper()
        hrs = _num(row.get("hours"))
        key = (name, cls)
        if key not in buckets:
            buckets[key] = TimesheetLine(line_type="labor", description=name, class_name=cls)
        ln = buckets[key]
        setattr(ln, _DAY_KEYS[di], getattr(ln, _DAY_KEYS[di]) + hrs)
        if ttype == "OT":
            ln.ot_hours += hrs
        elif ttype == "DT":
            ln.dt_hours += hrs
        else:
            ln.st_hours += hrs
    return sorted(buckets.values(), key=lambda x: (x.description.lower(), x.class_name.lower()))


def _build_equipment_lines(job_id: str, ws: date, we: date) -> list[TimesheetLine]:
    rows = _safe_admin_fetch("job_equipment", {"job_id": job_id}, limit=500)
    lines: list[TimesheetLine] = []
    for row in rows:
        created = _parse_date(row.get("created_at"))
        if created and (created < ws or created > we):
            continue
        label = str(row.get("asset_label") or "Equipment").strip()
        hrs = _num(row.get("usage_hours"))
        days = _num(row.get("usage_days"))
        rate_h = _num(row.get("rate_per_hour"))
        rate_d = _num(row.get("rate_per_day"))
        total = _num(row.get("line_total"))
        if hrs > 0:
            qty, unit, unit_cost = hrs, "hr", rate_h or (total / hrs if hrs and total else 0.0)
        elif days > 0:
            qty, unit, unit_cost = days, "day", rate_d or (total / days if days and total else 0.0)
        else:
            qty, unit, unit_cost = 1.0, "ea", total
        if not total and qty > 0 and unit_cost > 0:
            total = round(qty * unit_cost, 2)
        if not total and not label:
            continue
        markup = 0.0
        asset_id = str(row.get("asset_id") or "").strip()
        if asset_id:
            asset_rows = _safe_admin_fetch("assets", {"id": asset_id}, limit=1)
            if asset_rows:
                markup = _num(asset_rows[0].get("rental_default_markup_percent"))
        lines.append(
            TimesheetLine(
                line_type="equipment",
                description=label,
                unit=unit,
                qty=qty,
                unit_cost=unit_cost,
                markup_pct=markup,
                cost=total,
            )
        )
    return lines


def _build_material_lines(job_id: str, ws: date, we: date) -> list[TimesheetLine]:
    lines: list[TimesheetLine] = []
    for row in _safe_admin_fetch("job_materials", {"job_id": job_id}, limit=500):
        used = _parse_date(row.get("used_at") or row.get("created_at"))
        if used and (used < ws or used > we):
            continue
        qty = _num(row.get("quantity"))
        unit_cost = _num(row.get("unit_cost"))
        total = _num(row.get("line_total") or (qty * unit_cost))
        lines.append(
            TimesheetLine(
                line_type="material",
                description=str(row.get("item_name") or "Material").strip(),
                unit="ea",
                qty=qty,
                unit_cost=unit_cost,
                cost=total,
            )
        )
    try:
        txns = fetch_table_admin("inventory_transactions", limit=10000)
    except Exception:
        txns = []
    for row in txns:
        if str(row.get("job_id") or "") != job_id:
            continue
        created = _parse_date(row.get("created_at"))
        if created and (created < ws or created > we):
            continue
        qty = abs(_num(row.get("quantity")))
        if not qty:
            continue
        unit_cost = _num(row.get("unit_cost"))
        total = _num(row.get("line_total") or (qty * unit_cost))
        lines.append(
            TimesheetLine(
                line_type="material",
                description=str(row.get("item_name") or row.get("notes") or "Inventory issue").strip(),
                unit="ea",
                qty=qty,
                unit_cost=unit_cost or (total / qty if qty else 0.0),
                cost=total,
            )
        )
    try:
        for row in _safe_admin_fetch("job_expenses", {"job_id": job_id}, limit=500):
            status = str(row.get("status") or "").strip()
            if status in {"Rejected", "Open"}:
                continue
            exp_date = _parse_date(row.get("expense_date") or row.get("created_at"))
            if exp_date and (exp_date < ws or exp_date > we):
                continue
            amount = _num(row.get("amount"))
            if amount <= 0:
                continue
            category = str(row.get("category") or "").strip()
            desc = str(row.get("description") or row.get("vendor") or category or "Expense").strip()
            line_type = "material" if category == "Materials" else "expense"
            lines.append(
                TimesheetLine(
                    line_type=line_type,
                    description=desc,
                    unit="ea",
                    qty=1.0,
                    unit_cost=amount,
                    cost=amount,
                )
            )
    except Exception:
        pass
    return lines


def get_job_timesheet_header(job_id: str, week_start: date) -> dict[str, str]:
    """Header fields for weekly timesheet UI (job #, client, name, PO, week ending date)."""
    job = _fetch_job(job_id)
    if not job:
        return {}
    ws, we = week_bounds(monday_of_week(week_start))
    client = _fetch_customer_name(str(job.get("customer_id") or "").strip() or None)
    if not client:
        client = str(job.get("customer") or job.get("customer_name") or "").strip()
    job_name = str(
        job.get("job_name")
        or job.get("project_name")
        or job.get("description")
        or job.get("scope_of_work")
        or ""
    ).strip()
    return {
        "job_number": str(job.get("job_number") or job.get("job_id") or "").strip(),
        "client_name": client,
        "job_name": job_name,
        "po_number": _fetch_po_for_job(job),
        "sheet_date": we.isoformat(),
        "week_start": ws.isoformat(),
        "week_end": we.isoformat(),
    }


def _build_work_performed(job_id: str, ws: date, we: date) -> str:
    parts: list[str] = []
    from app.services.job_updates_service import get_job_daily_updates_for_week, format_work_performed_from_updates
    try:
        daily = format_work_performed_from_updates(get_job_daily_updates_for_week(job_id, ws))
        if daily:
            parts.append(daily)
    except Exception:
        pass
    try:
        for row in _safe_admin_fetch("job_daily_work_plans", {"job_id": job_id}, limit=200):
            wd = _parse_date(row.get("work_date"))
            if wd and ws <= wd <= we:
                for fld in ("eod_summary", "tomorrow_plan", "plan_text"):
                    txt = str(row.get(fld) or "").strip()
                    if txt:
                        parts.append(f"{wd.isoformat()}: {txt}")
                        break
    except Exception:
        pass
    try:
        for row in _safe_admin_fetch("job_notes", {"job_id": job_id}, limit=100):
            created = _parse_date(row.get("created_at"))
            if created and ws <= created <= we:
                txt = str(row.get("note_text") or row.get("notes") or "").strip()
                if txt:
                    parts.append(txt)
    except Exception:
        pass
    return "\n".join(parts[:20])


def build_timesheet_data(
    job_id: str,
    week_start: date,
    *,
    po_number: str = "",
    approved_by: str = "",
    work_performed: str = "",
    approved_timekeeping_only: bool = True,
) -> WeeklyJobTimesheetData:
    """Auto-populate weekly timesheet from jobs, approved timekeeping, materials, and notes."""
    job = _fetch_job(job_id)
    if not job:
        raise ValueError("Job not found.")
    from app.services.job_cost_transaction_service import sync_all_sources_for_job
    try:
        sync_all_sources_for_job(job_id)
    except Exception:
        pass
    ws, we = week_bounds(monday_of_week(week_start))
    header = get_job_timesheet_header(job_id, week_start)
    try:
        emp_map = _employees_map()
    except Exception:
        emp_map = {}
    labor: list[TimesheetLine] = []
    try:
        labor = _build_labor_from_timekeeping_days(
            job_id,
            ws,
            we,
            emp_map,
            approved_only=approved_timekeeping_only,
        )
        if not labor and not approved_timekeeping_only:
            labor = _build_labor_from_time_entries(job_id, ws, we, emp_map)
    except Exception:
        labor = []
    materials: list[TimesheetLine] = []
    equipment: list[TimesheetLine] = []
    other: list[TimesheetLine] = []
    try:
        materials, equipment, other = _build_charges_from_job_cost_transactions(job_id, ws, we)
    except Exception:
        materials, equipment, other = [], [], []
    if not materials and not equipment and not other:
        try:
            legacy_materials = _build_material_lines(job_id, ws, we)
            materials = [ln for ln in legacy_materials if ln.line_type == "material"]
            other = [ln for ln in legacy_materials if ln.line_type == "expense"]
            equipment = _build_equipment_lines(job_id, ws, we)
        except Exception:
            materials, equipment, other = [], [], []
    po = po_number.strip() or str(header.get("po_number") or "").strip() or _fetch_po_for_job(job)
    wp = work_performed.strip() or _build_work_performed(job_id, ws, we)
    return WeeklyJobTimesheetData(
        job_id=job_id,
        job_number=str(header.get("job_number") or "").strip(),
        client_name=str(header.get("client_name") or "").strip(),
        job_name=str(header.get("job_name") or "").strip(),
        po_number=po,
        sheet_date=str(header.get("sheet_date") or we.isoformat()),
        week_start=ws.isoformat(),
        week_end=we.isoformat(),
        approved_by=approved_by.strip(),
        work_performed=wp,
        labor_lines=labor or [_empty_labor_row()],
        material_lines=materials,
        equipment_lines=equipment,
        other_lines=other,
    )


def _line_to_db(line: TimesheetLine, timesheet_id: str, sort_order: int) -> dict[str, Any]:
    total_h = round(line.st_hours + line.ot_hours + line.dt_hours, 2)
    class_name = line.class_name
    if line.line_type != "labor" and line.charge_unit:
        class_name = line.charge_unit
    line_cost = line.line_total
    return {
        "timesheet_id": timesheet_id,
        "line_type": line.line_type,
        "sort_order": sort_order,
        "description": line.description,
        "class_name": class_name,
        "hours_mon": line.mon,
        "hours_tue": line.tue,
        "hours_wed": line.wed,
        "hours_thu": line.thu,
        "hours_fri": line.fri,
        "hours_sat": line.sat,
        "hours_sun": line.sun,
        "st_hours": line.st_hours,
        "ot_hours": line.ot_hours,
        "dt_hours": line.dt_hours,
        "qty": line.qty,
        "cost": line_cost,
        "monday_st": line.mon,
        "tuesday_st": line.tue,
        "wednesday_st": line.wed,
        "thursday_st": line.thu,
        "friday_st": line.fri,
        "saturday_st": line.sat,
        "sunday_st": line.sun,
        "total_st": line.st_hours,
        "total_ot": line.ot_hours,
        "total_dt": line.dt_hours,
        "total_hours": total_h,
        "quantity": line.qty,
        "total_cost": line_cost,
    }


def _line_from_db(row: dict[str, Any]) -> TimesheetLine:
    mon, tue, wed, thu, fri, sat, sun = (
        _day_hours(row, d, leg, mod) for d, leg, mod in _LEGACY_HOUR_COLS
    )
    qty = _num(row.get("qty") or row.get("quantity"))
    cost = _num(row.get("cost") or row.get("total_cost"))
    lt = str(row.get("line_type") or "labor")
    class_name = str(row.get("class_name") or "")
    unit = ""
    if lt != "labor":
        unit = class_name
        class_name = ""
    unit_cost = _num(row.get("unit_cost"))
    if not unit_cost and qty > 0 and cost > 0:
        unit_cost = round(cost / qty, 4)
    return TimesheetLine(
        line_type=lt,
        description=str(row.get("description") or row.get("employee_equipment") or ""),
        class_name=class_name,
        unit=unit,
        unit_cost=unit_cost,
        mon=mon,
        tue=tue,
        wed=wed,
        thu=thu,
        fri=fri,
        sat=sat,
        sun=sun,
        st_hours=_num(row.get("st_hours") or row.get("total_st")),
        ot_hours=_num(row.get("ot_hours") or row.get("total_ot")),
        dt_hours=_num(row.get("dt_hours") or row.get("total_dt")),
        qty=qty,
        cost=cost,
        sort_order=int(row.get("sort_order") or 0),
    )


def _header_from_db(
    row: dict[str, Any],
    labor: list[TimesheetLine],
    materials: list[TimesheetLine],
    equipment: list[TimesheetLine],
    other: list[TimesheetLine],
) -> WeeklyJobTimesheetData:
    snap = row.get("locked_snapshot")
    if snap and isinstance(snap, dict):
        data = WeeklyJobTimesheetData.from_snapshot(snap)
        data.status = str(row.get("status") or data.status)
        data.signature_data = str(row.get("signature_data") or data.signature_data)
        data.signed_at = str(row.get("signed_at") or "")[:19]
        return data
    return WeeklyJobTimesheetData(
        job_id=str(row.get("job_id") or ""),
        job_number=str(row.get("job_number") or ""),
        client_name=str(row.get("client_name") or ""),
        job_name=str(row.get("job_name") or ""),
        po_number=str(row.get("po_number") or ""),
        sheet_date=str(row.get("sheet_date") or "")[:10],
        week_start=str(row.get("week_start") or "")[:10],
        week_end=str(row.get("week_end") or "")[:10],
        approved_by=str(row.get("approved_by") or row.get("approved_by_name") or ""),
        work_performed=str(row.get("work_performed") or ""),
        status=str(row.get("status") or "Draft"),
        signature_data=str(row.get("signature_data") or row.get("signature_path") or row.get("signature_png_base64") or ""),
        signed_at=str(row.get("signed_at") or "")[:19],
        labor_lines=labor,
        material_lines=materials,
        equipment_lines=equipment,
        other_lines=other,
    )


def fetch_timesheet_by_job_week(job_id: str, week_start: date) -> dict[str, Any] | None:
    if not timesheet_table_available():
        return None
    ws = monday_of_week(week_start)
    try:
        rows = fetch_by_match_admin(_SHEET_TABLE, {"job_id": job_id, "week_start": ws.isoformat()}, limit=1)
    except Exception as exc:
        if _is_missing_table_error(exc):
            return None
        raise
    return rows[0] if rows else None


def load_timesheet_data(timesheet_id: str) -> WeeklyJobTimesheetData | None:
    if not timesheet_table_available():
        return None
    try:
        rows = fetch_by_match_admin(_SHEET_TABLE, {"id": timesheet_id}, limit=1)
    except Exception as exc:
        if _is_missing_table_error(exc):
            return None
        raise
    if not rows:
        return None
    row = rows[0]
    try:
        all_lines = fetch_table_admin(_LINES_TABLE, limit=5000)
    except Exception as exc:
        if _is_missing_table_error(exc):
            all_lines = []
        else:
            raise
    line_rows = [r for r in all_lines if str(r.get("timesheet_id") or "") == str(timesheet_id)]
    line_rows = sorted(line_rows, key=lambda r: int(r.get("sort_order") or 0))
    labor = [_line_from_db(r) for r in line_rows if str(r.get("line_type") or "") == "labor"]
    equipment = [_line_from_db(r) for r in line_rows if str(r.get("line_type") or "") == "equipment"]
    materials = [_line_from_db(r) for r in line_rows if str(r.get("line_type") or "") == "material"]
    other = [_line_from_db(r) for r in line_rows if str(r.get("line_type") or "") == "expense"]
    return _header_from_db(row, labor, materials, equipment, other)


def list_timesheets_for_job(job_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
    if not timesheet_table_available():
        return []
    try:
        rows = fetch_table_admin(_SHEET_TABLE, limit=limit, order_by="week_start")
    except Exception as exc:
        if _is_missing_table_error(exc):
            return []
        raise
    return [r for r in rows if str(r.get("job_id") or "") == str(job_id)]


def save_timesheet(
    data: WeeklyJobTimesheetData,
    *,
    created_by: str | None = None,
    lock: bool = False,
    regenerate_exports: bool = True,
) -> dict[str, Any]:
    """Persist draft or lock approved snapshot."""
    ensure_timesheet_table()
    if lock and data.status in {"Approved", "Signed"}:
        data.status = "Approved" if data.status == "Approved" else "Signed"
    ws = _parse_date(data.week_start) or date.today()
    ws = monday_of_week(ws)
    _, we = week_bounds(ws)
    existing = fetch_timesheet_by_job_week(data.job_id, ws)
    if existing and str(existing.get("status") or "") in {"Approved", "Signed"} and existing.get("locked_at"):
        raise RuntimeError("This timesheet is locked after approval and cannot be edited.")

    pdf_bytes = build_timesheet_pdf_bytes(data)
    job_num = data.job_number or str(data.job_id)[:8]
    pdf_storage = f"{_STORAGE_PREFIX}/{job_num}/{ws.isoformat()}/timesheet.pdf"
    upload_bytes_admin(pdf_storage, pdf_bytes, content_type="application/pdf")

    excel_storage = ""
    if regenerate_exports:
        from app.services.weekly_timesheet_export_service import ensure_excel_template, export_data_to_excel_bytes
        try:
            ensure_excel_template()
            excel_bytes = export_data_to_excel_bytes(data)
            excel_storage = f"{_STORAGE_PREFIX}/{job_num}/{ws.isoformat()}/timesheet.xlsx"
            upload_bytes_admin(
                excel_storage,
                excel_bytes,
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except Exception:
            excel_storage = ""

    payload: dict[str, Any] = {
        "job_id": data.job_id,
        "week_start": ws.isoformat(),
        "week_end": we.isoformat(),
        "job_number": data.job_number,
        "client_name": data.client_name,
        "job_name": data.job_name,
        "po_number": data.po_number,
        "sheet_date": (_parse_date(data.sheet_date) or we).isoformat(),
        "approved_by": data.approved_by,
        "approved_by_name": data.approved_by,
        "work_performed": data.work_performed,
        "status": data.status,
        "signature_data": data.signature_data,
        "signature_path": data.signature_data,
        "unsigned_pdf_url": pdf_storage,
        "pdf_file_url": pdf_storage,
        "pdf_path": pdf_storage,
        "pdf_url": pdf_storage,
        "excel_path": excel_storage,
        "excel_url": excel_storage,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "sign_token_expires_at": (datetime.now(timezone.utc) + timedelta(days=14)).isoformat(),
    }
    if data.signed_at:
        payload["signed_at"] = data.signed_at
        payload["approved_at"] = data.signed_at
    if lock:
        payload["locked_snapshot"] = data.to_snapshot()
        payload["locked_at"] = datetime.now(timezone.utc).isoformat()
    if created_by:
        payload["created_by"] = created_by

    if existing:
        tid = str(existing["id"])
        update_rows_admin(_SHEET_TABLE, payload, {"id": tid})
        delete_rows_admin(_LINES_TABLE, {"timesheet_id": tid})
    else:
        ins = insert_row_admin(_SHEET_TABLE, payload)
        tid = str(ins.get("id"))

    sort_i = 0
    for ln in data.labor_lines:
        if not ln.description and not ln.class_name and ln.total_hours == 0 and ln.day_total == 0:
            continue
        insert_row_admin(_LINES_TABLE, _line_to_db(ln, tid, sort_i))
        sort_i += 1
    for ln in data.material_lines:
        if not ln.description and ln.qty == 0 and ln.line_total == 0:
            continue
        insert_row_admin(_LINES_TABLE, _line_to_db(ln, tid, sort_i))
        sort_i += 1
    for ln in data.equipment_lines:
        if not ln.description and ln.qty == 0 and ln.line_total == 0:
            continue
        insert_row_admin(_LINES_TABLE, _line_to_db(ln, tid, sort_i))
        sort_i += 1
    for ln in data.other_lines:
        if not ln.description and ln.qty == 0 and ln.line_total == 0:
            continue
        insert_row_admin(_LINES_TABLE, _line_to_db(ln, tid, sort_i))
        sort_i += 1

    fresh = fetch_by_match_admin(_SHEET_TABLE, {"id": tid}, limit=1)
    return fresh[0] if fresh else {"id": tid, **payload}


def signed_url_for_timesheet(path: str) -> str:
    p = str(path or "").strip()
    if not p:
        return ""
    return create_signed_url(p, expires_in=3600)


def fetch_timesheet_by_sign_token(token: str) -> dict[str, Any] | None:
    if timesheet_table_available():
        try:
            rows = fetch_by_match_admin(_SHEET_TABLE, {"sign_token": token}, limit=1)
            if rows:
                return rows[0]
        except Exception as exc:
            if not _is_missing_table_error(exc):
                raise
    rows = fetch_by_match_admin("job_weekly_timesheets", {"sign_token": token}, limit=1)
    return rows[0] if rows else None
