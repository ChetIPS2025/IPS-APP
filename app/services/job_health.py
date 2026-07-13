from __future__ import annotations

# NOTE: IPS Dashboard KPIs are task / Daily Work Package based (daily_work_packages.py).
# This module provides job-level report/labor signals for optional future use — not shown as R/Y/G health tiles.

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from app.services.supervisor_daily_reports import (
    delay_labels_map,
    estimated_bid_labor_hours_from_estimate_json,
    job_status_needs_daily_report,
)
from app.services.supervisor_planning import active_goal_job_ids_for_date, active_task_job_ids
_DELAY_KEYS = tuple(delay_labels_map().keys())
_MAJOR_DELAY_KEYS = frozenset(
    {
        "delay_customer",
        "delay_safety",
        "delay_rework",
        "delay_equipment",
    }
)
_MATERIAL_TOOL_KEYS = frozenset({"delay_waiting_material", "delay_waiting_tools"})


def _parse_estimate_json(raw: Any) -> dict[str, Any] | None:
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            import json

            v = json.loads(raw)
            return v if isinstance(v, dict) else None
        except Exception:
            return None
    return None


def _report_date_str(r: dict[str, Any]) -> str:
    return str(r.get("report_date") or "")[:10]


def _active_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [j for j in (jobs or []) if isinstance(j, dict) and job_status_needs_daily_report(j.get("status"))]


def _reports_by_job(reports: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in reports or []:
        if not isinstance(r, dict):
            continue
        jid = str(r.get("job_id") or "").strip()
        if jid:
            out[jid].append(r)
    for lst in out.values():
        lst.sort(key=lambda x: _report_date_str(x))
    return dict(out)


def _date_set_for_job(reports: list[dict[str, Any]]) -> set[str]:
    return {_report_date_str(r) for r in reports if _report_date_str(r)}


def _consecutive_missing_days_from_today(*, today: date, report_dates: set[str]) -> int:
    """How many consecutive calendar days ending at ``today`` have no report (0 = report exists today)."""
    n = 0
    d = today
    for _ in range(0, 62):
        if d.isoformat() in report_dates:
            break
        n += 1
        d -= timedelta(days=1)
    return n


def _latest_report(reports: list[dict[str, Any]], *, today: date) -> dict[str, Any] | None:
    if not reports:
        return None
    best: dict[str, Any] | None = None
    best_d: date | None = None
    for r in reports:
        ds = _report_date_str(r)
        if not ds:
            continue
        try:
            rd = date.fromisoformat(ds)
        except ValueError:
            continue
        if rd > today:
            continue
        if best_d is None or rd > best_d:
            best_d = rd
            best = r
    return best


def _report_on_date(reports: list[dict[str, Any]], *, target: date) -> dict[str, Any] | None:
    want = target.isoformat()[:10]
    for r in reports:
        if _report_date_str(r) == want:
            return r
    return None


def _delay_labels_for_report(r: dict[str, Any]) -> list[str]:
    labels = delay_labels_map()
    out: list[str] = []
    for k in _DELAY_KEYS:
        if bool(r.get(k)):
            out.append(labels.get(k, k))
    return out


def _has_major_delay(r: dict[str, Any] | None) -> bool:
    if not r:
        return False
    return any(bool(r.get(k)) for k in _MAJOR_DELAY_KEYS)


def _has_minor_delay_only(r: dict[str, Any] | None) -> bool:
    if not r:
        return False
    if _has_major_delay(r):
        return False
    return any(bool(r.get(k)) for k in _DELAY_KEYS)


def _material_tool_days_in_window(reports: list[dict[str, Any]], *, today: date, days: int) -> set[str]:
    start = today - timedelta(days=days - 1)
    days_set: set[str] = set()
    for r in reports:
        try:
            rd = date.fromisoformat(_report_date_str(r))
        except ValueError:
            continue
        if rd < start or rd > today:
            continue
        if any(bool(r.get(k)) for k in _MATERIAL_TOOL_KEYS):
            days_set.add(rd.isoformat()[:10])
    return days_set


def _labor_ratio(*, actual: float, estimated: float | None) -> tuple[float | None, str]:
    """Bands: <=10% over = ok, 10–20% over = yellow, >20% over = red."""
    if estimated is None or estimated <= 0:
        return None, "na"
    ratio = (actual - estimated) / estimated
    if ratio <= 0.10 + 1e-9:
        return ratio, "ok"
    if ratio <= 0.20 + 1e-9:
        return ratio, "yellow"
    return ratio, "red"


def _estimate_hours_for_job(job: dict[str, Any], estimates_by_id: dict[str, dict[str, Any]]) -> float | None:
    eid = str(job.get("estimate_id") or "").strip()
    if not eid:
        return None
    est = estimates_by_id.get(eid)
    if not est:
        return None
    est_json = _parse_estimate_json(est.get("estimate_json"))
    return estimated_bid_labor_hours_from_estimate_json(est_json)


def _safety_signal_counts(reports: list[dict[str, Any]], *, today: date, days: int) -> tuple[int, bool]:
    """(days_with_safety_delay_in_window, safety_delay_on_latest_report)."""
    start = today - timedelta(days=days - 1)
    days_with = 0
    seen_days: set[str] = set()
    latest = _latest_report(reports, today=today)
    latest_flag = bool(latest and latest.get("delay_safety"))
    for r in reports:
        try:
            rd = date.fromisoformat(_report_date_str(r))
        except ValueError:
            continue
        if rd < start or rd > today:
            continue
        if bool(r.get("delay_safety")):
            ds = rd.isoformat()[:10]
            if ds not in seen_days:
                seen_days.add(ds)
                days_with += 1
    return days_with, latest_flag


def compute_job_health_row(
    job: dict[str, Any],
    *,
    today: date,
    reports_for_job: list[dict[str, Any]],
    hours_by_job: dict[str, float],
    hours_today_by_job: dict[str, float],
    estimates_by_id: dict[str, dict[str, Any]],
    goal_active_job_ids: set[str],
    task_work_job_ids: set[str],
) -> dict[str, Any]:
    jid = str(job.get("id") or "").strip()
    date_set = _date_set_for_job(reports_for_job)
    missing_streak = _consecutive_missing_days_from_today(today=today, report_dates=date_set)
    report_today = _report_on_date(reports_for_job, target=today)
    latest = _latest_report(reports_for_job, today=today)
    hours_today = float(hours_today_by_job.get(jid, 0.0))

    est_h = _estimate_hours_for_job(job, estimates_by_id)
    act_h = float(hours_by_job.get(jid, 0.0))
    ratio, labor_band = _labor_ratio(actual=act_h, estimated=est_h)

    safety_days, safety_latest = _safety_signal_counts(reports_for_job, today=today, days=14)

    if not report_today and hours_today <= 0 and jid not in goal_active_job_ids and jid not in task_work_job_ids:
        detail_idle = {
            "last_report_date": _report_date_str(latest) if latest else None,
            "last_supervisor": str((latest or {}).get("supervisor_name") or "").strip() or "—",
            "crew_size": None,
            "reported_delays": _delay_labels_for_report(latest) if latest else [],
            "repeated_delay_reasons": [],
            "labor_ratio_vs_estimate": (round(ratio * 100.0, 1) if ratio is not None else None),
            "est_labor_hrs": est_h,
            "act_labor_hrs": round(act_h, 2),
            "safety_delay_days_14d": safety_days,
            "safety_delay_on_latest": safety_latest,
            "missing_streak_days": missing_streak,
            "recommended_action": (
                "No daily report, no labor hours, no active goal window today, and no qualifying job-task activity "
                "today on this job. Health stays **Idle** until one of those is true."
            ),
        }
        last_crew = (latest or {}).get("crew_size")
        try:
            detail_idle["crew_size"] = (
                int(last_crew) if last_crew is not None and str(last_crew).strip() != "" else None
            )
        except (TypeError, ValueError):
            detail_idle["crew_size"] = None

        return {
            "job_id": jid,
            "label": "",
            "status": "idle",
            "pill": "Idle",
            "has_report_today": False,
            "has_activity_today": False,
            "reasons_red": [],
            "reasons_yellow": [],
            "green_reasons": [],
            "detail": detail_idle,
        }

    per_key_days: dict[str, set[str]] = defaultdict(set)
    start7 = today - timedelta(days=6)
    for r in reports_for_job:
        try:
            rd = date.fromisoformat(_report_date_str(r))
        except ValueError:
            continue
        if rd < start7 or rd > today:
            continue
        ds = rd.isoformat()[:10]
        for k in _DELAY_KEYS:
            if bool(r.get(k)):
                per_key_days[k].add(ds)
    repeated_keys_red = any(len(v) >= 2 for v in per_key_days.values())
    lbl_map = delay_labels_map()
    repeated_list = sorted(
        ((lbl_map.get(k, k), len(v)) for k, v in per_key_days.items() if len(v) >= 2),
        key=lambda x: (-x[1], x[0]),
    )

    mt_days = _material_tool_days_in_window(reports_for_job, today=today, days=7)
    material_tool_once = len(mt_days) == 1

    tomorrow_blank_today = bool(
        report_today and not str(report_today.get("tomorrows_plan") or "").strip()
    )

    reasons_red: list[str] = []
    reasons_yellow: list[str] = []

    if missing_streak >= 2:
        reasons_red.append(f"No daily report for {missing_streak} consecutive day(s).")
    if repeated_keys_red:
        reasons_red.append("Same delay category reported on multiple days this week.")
    if labor_band == "red":
        reasons_red.append("Labor hours are more than 20% over the bid estimate.")
    if report_today and _has_major_delay(report_today):
        reasons_red.append("Major blocker reported today (customer, safety, rework, or equipment).")
    if tomorrow_blank_today:
        reasons_red.append("Today’s report has no tomorrow plan.")
    if latest and bool(latest.get("delay_safety")):
        try:
            ld = date.fromisoformat(_report_date_str(latest))
        except ValueError:
            ld = None
        if ld and ld < today:
            reasons_red.append("Safety delay still flagged on the last submitted report with no newer update.")

    if not reasons_red:
        if missing_streak == 1:
            reasons_yellow.append("Daily report missing today.")
        if report_today and _has_minor_delay_only(report_today) and not _has_major_delay(report_today):
            reasons_yellow.append("Minor delay / inefficiency reported today.")
        if labor_band == "yellow":
            reasons_yellow.append("Labor hours are between 10% and 20% over the bid estimate.")
        if material_tool_once and not repeated_keys_red:
            reasons_yellow.append("Material or tool wait reported once this week.")

    # GREEN conditions (only meaningful if not red/yellow)
    green_ok = True
    green_reasons: list[str] = []
    if not report_today:
        green_ok = False
    elif _has_major_delay(report_today):
        green_ok = False
    elif _has_minor_delay_only(report_today):
        green_ok = False
    elif labor_band not in ("ok", "na"):
        green_ok = False
    elif bool(report_today.get("delay_waiting_material")) or bool(report_today.get("delay_waiting_tools")):
        green_ok = False
    elif bool(report_today.get("delay_safety")):
        green_ok = False
    else:
        green_reasons.append("Daily report submitted today.")
        green_reasons.append("No major delays on today’s report.")
        if labor_band == "ok":
            green_reasons.append("Labor hours are within 10% of the bid estimate (or below).")
        elif labor_band == "na":
            green_reasons.append("No bid labor estimate to compare (linked estimate labor blank).")
        green_reasons.append("No material/tool waits on today’s report.")
        green_reasons.append("No safety delay flagged on today’s report.")

    status = "green"
    pill = "On Track"
    if reasons_red:
        status = "red"
        pill = "At Risk"
    elif reasons_yellow or not green_ok:
        status = "yellow"
        pill = "Needs Attention"

    last_sup = str((latest or {}).get("supervisor_name") or "").strip() or "—"
    last_crew = (latest or {}).get("crew_size")
    try:
        last_crew_i = int(last_crew) if last_crew is not None and str(last_crew).strip() != "" else None
    except (TypeError, ValueError):
        last_crew_i = None

    rec_action = "No action needed."
    if status == "red":
        rec_action = "Escalate with PM/ops: review blockers, labor plan, and customer communication today."
    elif status == "yellow":
        rec_action = "Supervisor follow-up: submit today’s report and clear material/tool waits if possible."
    else:
        rec_action = "Maintain cadence: keep daily reports and labor tracking current."

    detail = {
        "last_report_date": _report_date_str(latest) if latest else None,
        "last_supervisor": last_sup,
        "crew_size": last_crew_i,
        "reported_delays": _delay_labels_for_report(latest) if latest else [],
        "repeated_delay_reasons": repeated_list,
        "labor_ratio_vs_estimate": (round(ratio * 100.0, 1) if ratio is not None else None),
        "est_labor_hrs": est_h,
        "act_labor_hrs": round(act_h, 2),
        "safety_delay_days_14d": safety_days,
        "safety_delay_on_latest": safety_latest,
        "missing_streak_days": missing_streak,
        "recommended_action": rec_action,
    }

    return {
        "job_id": jid,
        "label": "",  # filled by caller
        "status": status,
        "pill": pill,
        "has_report_today": bool(report_today),
        "has_activity_today": True,
        "reasons_red": reasons_red,
        "reasons_yellow": reasons_yellow,
        "green_reasons": green_reasons if status == "green" else [],
        "detail": detail,
    }


def compute_job_health_rows(
    *,
    today: date,
    jobs: list[dict[str, Any]],
    reports: list[dict[str, Any]],
    hours_by_job: dict[str, float],
    hours_today_by_job: dict[str, float],
    estimates_by_id: dict[str, dict[str, Any]],
    goals: list[dict[str, Any]] | None = None,
    job_tasks: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    from app.services.job_service import job_row_select_label
    by_job = _reports_by_job(reports)
    goal_ids = active_goal_job_ids_for_date(goals=list(goals or []), target=today)
    task_job_ids = active_task_job_ids(tasks=list(job_tasks or []), today=today)
    rows: list[dict[str, Any]] = []
    for job in _active_jobs(jobs):
        jid = str(job.get("id") or "").strip()
        if not jid:
            continue
        r = compute_job_health_row(
            job,
            today=today,
            reports_for_job=by_job.get(jid, []),
            hours_by_job=hours_by_job,
            hours_today_by_job=hours_today_by_job,
            estimates_by_id=estimates_by_id,
            goal_active_job_ids=goal_ids,
            task_work_job_ids=task_job_ids,
        )
        r["label"] = job_row_select_label(job)
        rows.append(r)

    def _health_sort_key(row: dict[str, Any]) -> tuple[int, str]:
        s = str(row.get("status") or "")
        rank = {"red": 0, "yellow": 1, "green": 2, "idle": 3}.get(s, 9)
        return (rank, str(row.get("label") or "").lower())

    rows.sort(key=_health_sort_key)
    return rows


def job_health_summary_counts(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Alert-style counts exclude Idle jobs (no report and no labor logged today)."""
    engaged = [r for r in rows if r.get("status") != "idle"]
    c_idle = sum(1 for r in rows if r.get("status") == "idle")
    c_red = sum(1 for r in engaged if r.get("status") == "red")
    c_yellow = sum(1 for r in engaged if r.get("status") == "yellow")
    c_green = sum(1 for r in engaged if r.get("status") == "green")
    missing_today = sum(1 for r in engaged if not r.get("has_report_today"))
    over_est = sum(
        1
        for r in engaged
        if (r.get("detail") or {}).get("est_labor_hrs") is not None
        and float((r.get("detail") or {}).get("act_labor_hrs") or 0)
        > float((r.get("detail") or {}).get("est_labor_hrs") or 0) * 1.001
    )
    repeated = sum(1 for r in engaged if (r.get("detail") or {}).get("repeated_delay_reasons"))
    return {
        "field_jobs": len(rows),
        "active_today": len(engaged),
        "idle": c_idle,
        "green": c_green,
        "yellow": c_yellow,
        "red": c_red,
        "missing_daily": missing_today,
        "over_labor_estimate": over_est,
        "repeated_delays": repeated,
    }
