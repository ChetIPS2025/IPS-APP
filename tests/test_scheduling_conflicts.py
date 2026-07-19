"""Scheduling conflict detection tests."""

from __future__ import annotations

from datetime import datetime, timezone

from app.services.scheduling_conflicts import (
    build_event_conflict_report,
    detect_asset_double_booking,
    detect_availability_conflicts,
    detect_certification_warnings,
    detect_employee_double_booking,
    detect_supervisor_double_booking,
    intervals_overlap,
)


def _dt(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 7, 6, hour, minute, tzinfo=timezone.utc)


def test_intervals_overlap_positive_duration():
    a_start, a_end = _dt(8), _dt(17)
    b_start, b_end = _dt(12), _dt(18)
    assert intervals_overlap(a_start, a_end, b_start, b_end) is True


def test_touching_boundaries_are_not_overlap():
    a_start, a_end = _dt(8), _dt(18)
    b_start, b_end = _dt(18), _dt(22)
    assert intervals_overlap(a_start, a_end, b_start, b_end) is False


def test_employee_double_booking_detected():
    report = detect_employee_double_booking(
        "emp-1",
        start_at=_dt(9),
        end_at=_dt(17),
        assignments=[
            {
                "employee_id": "emp-1",
                "schedule_event_id": "ev-other",
                "start_at": _dt(8).isoformat(),
                "end_at": _dt(12).isoformat(),
                "status": "confirmed",
                "title": "Morning job",
            }
        ],
    )
    assert report.has_warnings
    assert report.warnings[0].code == "employee_double_booking"


def test_cancelled_events_ignored_for_employee_conflicts():
    report = detect_employee_double_booking(
        "emp-1",
        start_at=_dt(9),
        end_at=_dt(17),
        assignments=[
            {
                "employee_id": "emp-1",
                "schedule_event_id": "ev-cancelled",
                "start_at": _dt(8).isoformat(),
                "end_at": _dt(12).isoformat(),
                "status": "cancelled",
                "title": "Cancelled job",
            }
        ],
    )
    assert not report.has_warnings


def test_supervisor_double_booking():
    report = detect_supervisor_double_booking(
        "sup-1",
        start_at=_dt(9),
        end_at=_dt(17),
        supervisor_events=[
            {
                "id": "ev-2",
                "supervisor_id": "sup-1",
                "start_at": _dt(7).isoformat(),
                "end_at": _dt(10).isoformat(),
                "status": "confirmed",
                "title": "Other site",
            }
        ],
    )
    assert report.has_warnings
    assert report.warnings[0].code == "supervisor_double_booking"


def test_asset_double_booking():
    report = detect_asset_double_booking(
        "asset-1",
        start_at=_dt(9),
        end_at=_dt(17),
        asset_assignments=[
            {
                "asset_id": "asset-1",
                "schedule_event_id": "ev-3",
                "start_at": _dt(8).isoformat(),
                "end_at": _dt(11).isoformat(),
                "status": "confirmed",
                "title": "Crane job",
            }
        ],
    )
    assert report.has_warnings
    assert report.warnings[0].code == "asset_double_booking"


def test_availability_conflict_vacation():
    report = detect_availability_conflicts(
        "emp-1",
        start_at=_dt(9),
        end_at=_dt(17),
        availability_rows=[
            {
                "employee_id": "emp-1",
                "availability_type": "vacation",
                "start_at": _dt(0).isoformat(),
                "end_at": _dt(23).isoformat(),
            }
        ],
    )
    assert report.has_warnings
    assert report.warnings[0].code == "availability_conflict"


def test_certification_warning_when_missing():
    report = detect_certification_warnings(
        "emp-1",
        required_certs=["TWIC"],
        employee_certs=[{"employee_id": "emp-1", "cert_type": "Forklift", "status": "active"}],
        employee_label="Jane Doe",
    )
    assert report.has_warnings
    assert "TWIC" in report.warnings[0].message


def test_build_event_conflict_report_excludes_self():
    report = build_event_conflict_report(
        start_at=_dt(9),
        end_at=_dt(17),
        employee_ids=["emp-1"],
        asset_ids=["asset-1"],
        supervisor_id="sup-1",
        required_certifications=["TWIC"],
        employee_assignments=[
            {
                "employee_id": "emp-1",
                "schedule_event_id": "ev-edit",
                "start_at": _dt(8).isoformat(),
                "end_at": _dt(12).isoformat(),
                "status": "confirmed",
                "title": "Same event",
            }
        ],
        supervisor_events=[
            {
                "id": "ev-edit",
                "supervisor_id": "sup-1",
                "start_at": _dt(8).isoformat(),
                "end_at": _dt(12).isoformat(),
                "status": "confirmed",
                "title": "Same event",
            }
        ],
        asset_assignments=[
            {
                "asset_id": "asset-1",
                "schedule_event_id": "ev-edit",
                "start_at": _dt(8).isoformat(),
                "end_at": _dt(12).isoformat(),
                "status": "confirmed",
                "title": "Same event",
            }
        ],
        availability_rows=[],
        employee_certs=[],
        assets_by_id={"asset-1": {"status": "active", "asset_name": "Lift"}},
        employee_labels={"emp-1": "Worker"},
        exclude_event_id="ev-edit",
    )
    double_booking = [w for w in report.warnings if w.code.endswith("double_booking")]
    assert double_booking == []
