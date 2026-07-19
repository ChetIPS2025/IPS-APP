"""Scheduling overlap and conflict detection (pure logic, unit-testable)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

ACTIVE_EVENT_STATUSES = frozenset({"tentative", "confirmed", "in_progress", "completed"})
BLOCKING_AVAILABILITY_TYPES = frozenset({"unavailable", "vacation", "sick", "training"})

CERT_WARNING_ALIASES: dict[str, tuple[str, ...]] = {
    "twic": ("twic",),
    "site orientation": ("orientation", "site orientation", "site_orientation"),
    "forklift": ("forklift", "fork lift"),
    "welding certification": ("welding", "welder", "welding certification"),
    "supplied-air qualification": ("supplied air", "supplied-air", "supplied_air", "respirator"),
}


def parse_dt(value: object) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def intervals_overlap(
    start_a: datetime,
    end_a: datetime,
    start_b: datetime,
    end_b: datetime,
) -> bool:
    """True when ranges overlap with positive duration; touching boundaries is NOT overlap."""
    return start_a < end_b and end_a > start_b


def event_is_active(status: object) -> bool:
    return str(status or "").strip().lower() in ACTIVE_EVENT_STATUSES


def event_is_cancelled(status: object) -> bool:
    return str(status or "").strip().lower() == "cancelled"


@dataclass
class ScheduleConflict:
    code: str
    severity: str  # warning | error
    message: str
    related_event_id: str = ""
    related_entity_id: str = ""


@dataclass
class ConflictReport:
    warnings: list[ScheduleConflict] = field(default_factory=list)

    @property
    def has_warnings(self) -> bool:
        return bool(self.warnings)

    def merge(self, other: ConflictReport) -> None:
        self.warnings.extend(other.warnings)


def _overlap_conflicts(
    *,
    code: str,
    label: str,
    entity_id: str,
    new_start: datetime,
    new_end: datetime,
    existing_rows: list[dict[str, Any]],
    exclude_event_id: str = "",
) -> list[ScheduleConflict]:
    out: list[ScheduleConflict] = []
    for row in existing_rows:
        if not isinstance(row, dict):
            continue
        ev_id = str(row.get("schedule_event_id") or row.get("id") or "").strip()
        if exclude_event_id and ev_id == exclude_event_id:
            continue
        if event_is_cancelled(row.get("status")):
            continue
        ex_start = parse_dt(row.get("start_at"))
        ex_end = parse_dt(row.get("end_at"))
        if not ex_start or not ex_end:
            continue
        if not intervals_overlap(new_start, new_end, ex_start, ex_end):
            continue
        title = str(row.get("title") or row.get("event_title") or "Event").strip()
        out.append(
            ScheduleConflict(
                code=code,
                severity="warning",
                message=f"{label} conflict with “{title}”.",
                related_event_id=ev_id,
                related_entity_id=entity_id,
            )
        )
    return out


def detect_employee_double_booking(
    employee_id: str,
    *,
    start_at: datetime,
    end_at: datetime,
    assignments: list[dict[str, Any]],
    exclude_event_id: str = "",
) -> ConflictReport:
    report = ConflictReport()
    eid = str(employee_id or "").strip()
    if not eid:
        return report
    filtered = [
        r
        for r in assignments
        if str(r.get("employee_id") or "").strip() == eid
    ]
    report.warnings.extend(
        _overlap_conflicts(
            code="employee_double_booking",
            label="Employee",
            entity_id=eid,
            new_start=start_at,
            new_end=end_at,
            existing_rows=filtered,
            exclude_event_id=exclude_event_id,
        )
    )
    return report


def detect_supervisor_double_booking(
    supervisor_id: str,
    *,
    start_at: datetime,
    end_at: datetime,
    supervisor_events: list[dict[str, Any]],
    exclude_event_id: str = "",
) -> ConflictReport:
    report = ConflictReport()
    sid = str(supervisor_id or "").strip()
    if not sid:
        return report
    filtered = [
        r
        for r in supervisor_events
        if str(r.get("supervisor_id") or "").strip() == sid
    ]
    report.warnings.extend(
        _overlap_conflicts(
            code="supervisor_double_booking",
            label="Supervisor",
            entity_id=sid,
            new_start=start_at,
            new_end=end_at,
            existing_rows=filtered,
            exclude_event_id=exclude_event_id,
        )
    )
    return report


def detect_asset_double_booking(
    asset_id: str,
    *,
    start_at: datetime,
    end_at: datetime,
    asset_assignments: list[dict[str, Any]],
    exclude_event_id: str = "",
) -> ConflictReport:
    report = ConflictReport()
    aid = str(asset_id or "").strip()
    if not aid:
        return report
    filtered = [
        r
        for r in asset_assignments
        if str(r.get("asset_id") or "").strip() == aid
    ]
    report.warnings.extend(
        _overlap_conflicts(
            code="asset_double_booking",
            label="Asset",
            entity_id=aid,
            new_start=start_at,
            new_end=end_at,
            existing_rows=filtered,
            exclude_event_id=exclude_event_id,
        )
    )
    return report


def detect_availability_conflicts(
    employee_id: str,
    *,
    start_at: datetime,
    end_at: datetime,
    availability_rows: list[dict[str, Any]],
) -> ConflictReport:
    report = ConflictReport()
    eid = str(employee_id or "").strip()
    if not eid:
        return report
    for row in availability_rows:
        if str(row.get("employee_id") or "").strip() != eid:
            continue
        atype = str(row.get("availability_type") or "").strip().lower()
        if atype not in BLOCKING_AVAILABILITY_TYPES:
            continue
        av_start = parse_dt(row.get("start_at"))
        av_end = parse_dt(row.get("end_at"))
        if not av_start or not av_end:
            continue
        if not intervals_overlap(start_at, end_at, av_start, av_end):
            continue
        report.warnings.append(
            ScheduleConflict(
                code="availability_conflict",
                severity="warning",
                message=f"Employee marked {atype} during this window.",
                related_entity_id=eid,
            )
        )
    return report


def _cert_matches(required: str, cert_type: str) -> bool:
    req = str(required or "").strip().lower()
    ctype = str(cert_type or "").strip().lower()
    if not req or not ctype:
        return False
    if req in ctype or ctype in req:
        return True
    for aliases in CERT_WARNING_ALIASES.values():
        if req in aliases and any(alias in ctype for alias in aliases):
            return True
    return False


def detect_certification_warnings(
    employee_id: str,
    *,
    required_certs: list[str],
    employee_certs: list[dict[str, Any]],
    employee_label: str = "Employee",
) -> ConflictReport:
    report = ConflictReport()
    eid = str(employee_id or "").strip()
    if not eid or not required_certs:
        return report
    held = {
        str(c.get("cert_type") or "").strip().lower()
        for c in employee_certs
        if str(c.get("employee_id") or "").strip() == eid
        and str(c.get("status") or "").strip().lower() not in {"expired", "inactive"}
    }
    for req in required_certs:
        req_norm = str(req or "").strip()
        if not req_norm:
            continue
        if any(_cert_matches(req_norm, held_type) for held_type in held):
            continue
        report.warnings.append(
            ScheduleConflict(
                code="certification_warning",
                severity="warning",
                message=f"{employee_label} may be missing certification: {req_norm}.",
                related_entity_id=eid,
            )
        )
    return report


def detect_asset_status_warnings(
    asset_id: str,
    *,
    asset_row: dict[str, Any] | None,
) -> ConflictReport:
    report = ConflictReport()
    aid = str(asset_id or "").strip()
    if not aid or not isinstance(asset_row, dict):
        return report
    status = str(asset_row.get("status") or "").strip().lower()
    blocked = {"out for repair", "out of service", "retired", "maintenance due", "down"}
    if status in blocked:
        name = str(asset_row.get("asset_name") or asset_row.get("name") or aid).strip()
        report.warnings.append(
            ScheduleConflict(
                code="asset_status_warning",
                severity="warning",
                message=f"Asset “{name}” status is {status}.",
                related_entity_id=aid,
            )
        )
    return report


def build_event_conflict_report(
    *,
    start_at: datetime,
    end_at: datetime,
    employee_ids: list[str],
    asset_ids: list[str],
    supervisor_id: str,
    required_certifications: list[str],
    employee_assignments: list[dict[str, Any]],
    supervisor_events: list[dict[str, Any]],
    asset_assignments: list[dict[str, Any]],
    availability_rows: list[dict[str, Any]],
    employee_certs: list[dict[str, Any]],
    assets_by_id: dict[str, dict[str, Any]],
    employee_labels: dict[str, str] | None = None,
    exclude_event_id: str = "",
) -> ConflictReport:
    """Aggregate conflict checks for a proposed or edited event."""
    report = ConflictReport()
    labels = employee_labels or {}

    for eid in employee_ids:
        sub = detect_employee_double_booking(
            eid,
            start_at=start_at,
            end_at=end_at,
            assignments=employee_assignments,
            exclude_event_id=exclude_event_id,
        )
        report.merge(sub)
        sub = detect_availability_conflicts(
            eid,
            start_at=start_at,
            end_at=end_at,
            availability_rows=availability_rows,
        )
        report.merge(sub)
        sub = detect_certification_warnings(
            eid,
            required_certs=required_certifications,
            employee_certs=employee_certs,
            employee_label=labels.get(eid, "Employee"),
        )
        report.merge(sub)

    if supervisor_id:
        sub = detect_supervisor_double_booking(
            supervisor_id,
            start_at=start_at,
            end_at=end_at,
            supervisor_events=supervisor_events,
            exclude_event_id=exclude_event_id,
        )
        report.merge(sub)

    for aid in asset_ids:
        sub = detect_asset_double_booking(
            aid,
            start_at=start_at,
            end_at=end_at,
            asset_assignments=asset_assignments,
            exclude_event_id=exclude_event_id,
        )
        report.merge(sub)
        sub = detect_asset_status_warnings(aid, asset_row=assets_by_id.get(aid))
        report.merge(sub)

    return report
