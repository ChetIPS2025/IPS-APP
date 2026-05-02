"""Supervisor daily tasks: planning snapshots, delay labels, and legacy goal helpers (047/048)."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta
from typing import Any

try:
    from app.services import task_photos as _task_photos
except ImportError:
    import services.task_photos as _task_photos  # type: ignore

_GOAL_OPEN = frozenset({"open", "in_progress"})

_DELAY_LABELS: dict[str, str] = {
    "material": "Material",
    "tools": "Tools",
    "direction": "Direction",
    "rework": "Rework",
    "customer": "Customer",
    "safety": "Safety",
    "equipment": "Equipment",
    "weather": "Weather",
    "other": "Other",
    "none": "None",
}


def delay_reason_label(slug: str) -> str:
    return _DELAY_LABELS.get(str(slug or "").strip().lower(), str(slug or "Other"))


def _parse_date(v: Any) -> date | None:
    if v is None:
        return None
    s = str(v).strip()[:10]
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def goal_covers_date(g: dict[str, Any], d: date) -> bool:
    """Goal window [goal_date, due_date] inclusive; only open/in_progress."""
    st = str(g.get("status") or "").strip().lower().replace(" ", "_")
    if st not in _GOAL_OPEN:
        return False
    gd = _parse_date(g.get("goal_date"))
    dd = _parse_date(g.get("due_date"))
    if gd is None or dd is None:
        return False
    return gd <= d <= dd


def active_goal_job_ids_for_date(*, goals: list[dict[str, Any]], target: date) -> set[str]:
    out: set[str] = set()
    for g in goals or []:
        if not isinstance(g, dict):
            continue
        if goal_covers_date(g, target):
            jid = str(g.get("job_id") or "").strip()
            if jid:
                out.add(jid)
    return out


def active_task_job_ids(*, tasks: list[dict[str, Any]], today: date) -> set[str]:
    """Jobs with task work relevant today (planned, completed, or blocked)."""
    t_iso = today.isoformat()[:10]
    out: set[str] = set()
    for t in tasks or []:
        if not isinstance(t, dict):
            continue
        jid = str(t.get("job_id") or "").strip()
        if not jid:
            continue
        pd = str(t.get("planned_date") or "")[:10]
        cd = str(t.get("completed_date") or "")[:10]
        st = str(t.get("status") or "").strip().lower()
        if pd == t_iso or cd == t_iso or st == "blocked":
            out.add(jid)
    return out


def active_work_job_ids(
    *,
    today: date,
    reports_today: list[dict[str, Any]],
    labor_today_by_job: dict[str, float],
    goals: list[dict[str, Any]],
    job_tasks: list[dict[str, Any]] | None = None,
) -> set[str]:
    ids: set[str] = set()
    for r in reports_today or []:
        if not isinstance(r, dict):
            continue
        jid = str(r.get("job_id") or "").strip()
        if jid:
            ids.add(jid)
    for jid, hrs in (labor_today_by_job or {}).items():
        if float(hrs or 0) > 0 and jid:
            ids.add(jid)
    ids |= active_goal_job_ids_for_date(goals=list(goals or []), target=today)
    ids |= active_task_job_ids(tasks=list(job_tasks or []), today=today)
    return {j for j in ids if j}


_TASK_TERMINAL = frozenset(
    {"complete", "duplicate", "electrical", "waiting_on_customer", "cancelled"}
)
# Legacy DB values still recognized in reads until migration 049 is applied.
_TASK_TERMINAL_LEGACY = frozenset({"electrical_others", "customer_hold"})


def _task_terminal(st: str) -> bool:
    s = str(st or "").strip().lower()
    return s in _TASK_TERMINAL or s in _TASK_TERMINAL_LEGACY


def planned_tasks_today_count(
    *,
    today: date,
    tasks: list[dict[str, Any]],
    daily_plans: list[dict[str, Any]],
    active_task_ids: set[str] | None = None,
) -> int:
    """Distinct tasks ``planned`` for ``today`` (daily plan rows + task.planned_date)."""
    t_iso = today.isoformat()[:10]

    def _keep(tid: str) -> bool:
        if not tid:
            return False
        if active_task_ids is None:
            return True
        return tid in active_task_ids

    ids: set[str] = set()
    for p in daily_plans or []:
        if not isinstance(p, dict):
            continue
        if str(p.get("work_date") or "")[:10] != t_iso:
            continue
        tid = str(p.get("task_id") or "").strip()
        if _keep(tid):
            ids.add(tid)
    for t in tasks or []:
        if not isinstance(t, dict):
            continue
        if str(t.get("planned_date") or "")[:10] == t_iso:
            tid = str(t.get("id") or "").strip()
            if _keep(tid):
                ids.add(tid)
    return len(ids)


def dashboard_task_progress_snapshot(
    *,
    today: date,
    tasks: list[dict[str, Any]],
    daily_plans: list[dict[str, Any]] | None = None,
    active_task_ids: set[str] | None = None,
    photo_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Dashboard KPIs for task-based workflow (mobile-friendly)."""
    t_iso = today.isoformat()[:10]
    planned_today = planned_tasks_today_count(
        today=today,
        tasks=list(tasks or []),
        daily_plans=list(daily_plans or []),
        active_task_ids=active_task_ids,
    )
    completed_today = 0
    blocked = 0
    high_open = 0
    electrical_trade = 0
    photos_by_task = _task_photos.photos_by_task_id(list(photo_rows or []))
    missing_after_photo = _task_photos.tasks_completed_today_missing_after(
        list(tasks or []),
        photos_by_task,
        today=today,
    )
    photos_uploaded_today = _task_photos.count_tasks_with_photos_uploaded_today_filtered(
        list(photo_rows or []),
        today=today,
        allowed_task_ids=active_task_ids,
    )
    for t in tasks or []:
        if not isinstance(t, dict):
            continue
        st = str(t.get("status") or "").strip().lower()
        if st == "open":
            st = "not_started"
        pr = str(t.get("priority") or "").strip().lower()
        cd = str(t.get("completed_date") or "")[:10]
        if st == "complete" and cd == t_iso:
            completed_today += 1
        if st == "blocked":
            blocked += 1
        if pr in ("high", "critical") and not _task_terminal(st):
            high_open += 1
        if st == "electrical":
            electrical_trade += 1
    return {
        "planned_today": planned_today,
        "completed_today": completed_today,
        "blocked": blocked,
        "high_priority_open": high_open,
        "missing_after_photo": missing_after_photo,
        "photos_uploaded_today": photos_uploaded_today,
        "electrical_trade": electrical_trade,
    }


def repeated_task_review_delay_reasons(
    reviews: list[dict[str, Any]], *, today: date, days: int = 14
) -> list[tuple[str, int]]:
    """Delay reasons that appear on 2+ distinct review days in the window (task reviews)."""
    start = today - timedelta(days=days - 1)
    by_reason: dict[str, set[str]] = defaultdict(set)
    for r in reviews or []:
        if not isinstance(r, dict):
            continue
        rd = _parse_date(r.get("review_date"))
        if rd is None or rd < start or rd > today:
            continue
        dr = str(r.get("delay_reason") or "other").strip().lower()
        if not dr or dr == "none":
            continue
        by_reason[dr].add(rd.isoformat()[:10])
    pairs = [(delay_reason_label(k), len(v)) for k, v in by_reason.items() if len(v) >= 2]
    pairs.sort(key=lambda x: (-x[1], x[0]))
    return pairs[:10]


TASK_STATUSES: tuple[str, ...] = (
    "not_started",
    "in_progress",
    "complete",
    "partial",
    "blocked",
    "duplicate",
    "electrical",
    "waiting_on_customer",
    "cancelled",
)


def rollup_goal_result_from_task_outcomes(outcomes: list[str]) -> str:
    """Legacy helper (goal rollup); unused in task-only UI."""
    if not outcomes:
        return "missed"
    norm = [str(x or "").strip().lower() for x in outcomes]
    if all(x == "complete" for x in norm):
        return "met"
    if all(x == "not_started" for x in norm):
        return "missed"
    return "partial"


def job_task_status_from_outcome(outcome: str) -> str:
    """Normalize status slug (legacy EOD mapping)."""
    o = str(outcome or "").strip().lower()
    if o in ("electrical_others",):
        return "electrical"
    if o in ("customer_hold",):
        return "waiting_on_customer"
    if o in ("open",):
        return "not_started"
    return o if o in TASK_STATUSES else "partial"


def task_row_active_for_dashboard(task: dict[str, Any], *, today: date) -> bool:
    """Non-terminal work, or anything with activity / plan tied to ``today``."""
    t_iso = today.isoformat()[:10]
    if not isinstance(task, dict):
        return False
    st = str(task.get("status") or "").strip().lower()
    if st == "open":
        st = "not_started"
    pd = str(task.get("planned_date") or "")[:10]
    cd = str(task.get("completed_date") or "")[:10]
    if pd == t_iso or cd == t_iso:
        return True
    if st == "blocked":
        return True
    if st in ("not_started", "in_progress", "partial"):
        return True
    if _task_terminal(st):
        return False
    return True


def eod_scores(goal_result: str, *, delay_within_supervisor_control: bool) -> tuple[float, float]:
    """(raw_score, performance_score). Outside-control delays do not penalize performance score on misses."""
    gr = str(goal_result or "").strip().lower()
    raw = {"met": 1.0, "partial": 0.5, "missed": 0.0}.get(gr, 0.0)
    perf = raw
    if gr == "missed" and not delay_within_supervisor_control:
        perf = 1.0
    return raw, perf


def latest_pm_review_by_plan_id(reviews: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Most recent review per plan_id by created_at."""
    best: dict[str, dict[str, Any]] = {}
    best_ts: dict[str, str] = {}
    for r in reviews or []:
        if not isinstance(r, dict):
            continue
        pid = str(r.get("plan_id") or "").strip()
        if not pid:
            continue
        ts = str(r.get("created_at") or "")
        if pid not in best_ts or ts >= best_ts[pid]:
            best_ts[pid] = ts
            best[pid] = r
    return best


def plans_needing_pm_review(
    plans: list[dict[str, Any]], *, today: date, horizon_days: int = 3
) -> list[dict[str, Any]]:
    end = today + timedelta(days=horizon_days)
    out: list[dict[str, Any]] = []
    for p in plans or []:
        if not isinstance(p, dict):
            continue
        pd = _parse_date(p.get("plan_date"))
        if pd is None or pd < today or pd > end:
            continue
        if str(p.get("latest_pm_decision") or "").strip():
            continue
        if not str(p.get("crew_plan") or "").strip() and not str(p.get("first_task") or "").strip():
            continue
        out.append(p)
    return out


def plans_needing_adjustment(plans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bad = frozenset({"needs_adjustment", "direct_correction"})
    return [
        p
        for p in (plans or [])
        if isinstance(p, dict) and str(p.get("latest_pm_decision") or "").strip().lower() in bad
    ]


def goals_due_today(goals: list[dict[str, Any]], *, today: date) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for g in goals or []:
        if not isinstance(g, dict):
            continue
        dd = _parse_date(g.get("due_date"))
        if dd != today:
            continue
        st = str(g.get("status") or "").strip().lower().replace(" ", "_")
        if st in _GOAL_OPEN:
            out.append(g)
    return out


def goals_missed_today_from_eod(eods: list[dict[str, Any]], *, today: date) -> list[dict[str, Any]]:
    return [
        e
        for e in (eods or [])
        if isinstance(e, dict)
        and _parse_date(e.get("review_date")) == today
        and str(e.get("goal_result") or "").strip().lower() == "missed"
    ]


def eod_reviews_missing(
    *,
    today: date,
    goals: list[dict[str, Any]],
    plans: list[dict[str, Any]],
    eods: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Active goals covering ``today`` with a tactical plan for ``today`` but no EOD row
    for (goal_id, review_date=today).
    """
    eod_keys = {
        (str(e.get("goal_id") or "").strip(), str(e.get("review_date") or "")[:10])
        for e in (eods or [])
        if isinstance(e, dict) and str(e.get("goal_id") or "").strip()
    }
    t_iso = today.isoformat()[:10]
    plan_by_goal: dict[str, dict[str, Any]] = {}
    for p in plans or []:
        if not isinstance(p, dict):
            continue
        if str(p.get("plan_date") or "")[:10] != t_iso:
            continue
        gid = str(p.get("goal_id") or "").strip()
        if gid:
            plan_by_goal[gid] = p

    missing: list[dict[str, Any]] = []
    for g in goals or []:
        if not isinstance(g, dict):
            continue
        gid = str(g.get("id") or "").strip()
        if not gid or gid not in plan_by_goal:
            continue
        if not goal_covers_date(g, today):
            continue
        if (gid, t_iso) in eod_keys:
            continue
        missing.append(g)
    return missing


def repeated_eod_delay_reasons(eods: list[dict[str, Any]], *, today: date, days: int = 14) -> list[tuple[str, int]]:
    """Same (job, delay_reason) on 2+ distinct calendar days in the window → repeated pattern."""
    start = today - timedelta(days=days - 1)
    triples: dict[tuple[str, str], set[str]] = defaultdict(set)
    for e in eods or []:
        if not isinstance(e, dict):
            continue
        rd = _parse_date(e.get("review_date"))
        if rd is None or rd < start or rd > today:
            continue
        jid = str(e.get("job_id") or "").strip()
        dr = str(e.get("delay_reason") or "other").strip().lower()
        if not jid or dr in ("none", ""):
            continue
        triples[(jid, dr)].add(rd.isoformat()[:10])
    pairs: list[tuple[str, int]] = []
    for (_jid, dr), day_set in triples.items():
        if len(day_set) >= 2:
            pairs.append((delay_reason_label(dr), len(day_set)))
    pairs.sort(key=lambda x: (-x[1], x[0]))
    return pairs[:12]


def pm_interventions_count(reviews: list[dict[str, Any]]) -> int:
    return sum(
        1
        for r in (reviews or [])
        if isinstance(r, dict)
        and str(r.get("decision") or "").strip().lower() in ("needs_adjustment", "direct_correction")
    )


def _eods_for_supervisor(eods: list[dict[str, Any]], supervisor_name: str) -> list[dict[str, Any]]:
    sn = " ".join(str(supervisor_name or "").strip().split()).casefold()
    if not sn:
        return []
    return [
        e
        for e in (eods or [])
        if isinstance(e, dict) and " ".join(str(e.get("supervisor_name") or "").strip().split()).casefold() == sn
    ]


def supervisor_performance_snapshot(
    *,
    supervisor_name: str,
    today: date,
    eods: list[dict[str, Any]],
    pm_reviews: list[dict[str, Any]],
    plans: list[dict[str, Any]],
) -> dict[str, Any]:
    plan_sup: dict[str, str] = {}
    for p in plans or []:
        if not isinstance(p, dict) or not p.get("id"):
            continue
        plan_sup[str(p.get("id"))] = " ".join(str(p.get("supervisor_name") or "").strip().split()).casefold()

    mine = _eods_for_supervisor(eods, supervisor_name)
    t_iso = today.isoformat()[:10]
    today_rows = [e for e in mine if str(e.get("review_date") or "")[:10] == t_iso]
    week_start = today - timedelta(days=6)
    week_rows = [e for e in mine if (d := _parse_date(e.get("review_date"))) and week_start <= d <= today]

    def _avg_perf(rows: list[dict[str, Any]]) -> float | None:
        if not rows:
            return None
        vals = [float(e.get("score_for_performance") or 0) for e in rows]
        return round(sum(vals) / max(len(vals), 1), 3)

    today_score = _avg_perf(today_rows)
    week_avg = _avg_perf(week_rows)

    met = sum(1 for e in week_rows if str(e.get("goal_result") or "").lower() == "met")
    partial = sum(1 for e in week_rows if str(e.get("goal_result") or "").lower() == "partial")
    missed = sum(1 for e in week_rows if str(e.get("goal_result") or "").lower() == "missed")

    dr_counts: Counter[str] = Counter()
    for e in week_rows:
        dr = str(e.get("delay_reason") or "").strip().lower()
        if dr and dr != "none":
            dr_counts[dr] += 1
    top_delay = None
    if dr_counts:
        k, v = dr_counts.most_common(1)[0]
        top_delay = (delay_reason_label(k), v)

    sn_cf = " ".join(str(supervisor_name or "").strip().split()).casefold()
    interventions = 0
    for r in pm_reviews or []:
        if not isinstance(r, dict):
            continue
        cd = _parse_date(r.get("created_at"))
        if cd is None or not (week_start <= cd <= today + timedelta(days=1)):
            continue
        pid = str(r.get("plan_id") or "").strip()
        if plan_sup.get(pid, "") != sn_cf:
            continue
        if str(r.get("decision") or "").strip().lower() in ("needs_adjustment", "direct_correction"):
            interventions += 1

    return {
        "supervisor_name": supervisor_name,
        "today_score": today_score,
        "weekly_avg_score": week_avg,
        "week_met": met,
        "week_partial": partial,
        "week_missed": missed,
        "top_delay": top_delay,
        "pm_interventions_week": interventions,
    }


def goal_track_status(
    goal: dict[str, Any],
    *,
    today: date,
    plans_by_goal: dict[str, list[dict[str, Any]]],
    latest_review_by_plan: dict[str, dict[str, Any]],
    eods_by_goal_date: dict[tuple[str, str], dict[str, Any]],
    job_has_repeated_delay: bool,
) -> str:
    """
    On Track | Needs Attention | At Risk (active goals only; caller skips idle jobs).

    At Risk: missed goal, PM rejected plan, critical+deadline risk, repeated delay (2+ days), review missing.
    """
    gid = str(goal.get("id") or "").strip()
    st = str(goal.get("status") or "").strip().lower().replace(" ", "_")
    if st == "missed":
        return "at_risk"

    pr = str(goal.get("priority") or "").strip().lower()
    dd = _parse_date(goal.get("due_date"))
    if pr == "critical" and dd == today and st in _GOAL_OPEN:
        return "at_risk"

    t_iso = today.isoformat()[:10]
    plans = plans_by_goal.get(gid, [])
    for p in plans:
        if str(p.get("plan_date") or "")[:10] != t_iso:
            continue
        pid = str(p.get("id") or "").strip()
        rev = latest_review_by_plan.get(pid) if pid else None
        dec = str((rev or {}).get("decision") or "").strip().lower()
        if dec in ("needs_adjustment", "direct_correction"):
            return "at_risk"
        pm_dec = str(p.get("latest_pm_decision") or "").strip().lower()
        if pm_dec in ("needs_adjustment", "direct_correction"):
            return "at_risk"

    jid = str(goal.get("job_id") or "").strip()
    if jid and job_has_repeated_delay:
        return "at_risk"

    if goal_covers_date(goal, today) and gid:
        if (gid, t_iso) not in eods_by_goal_date:
            for p in plans:
                if str(p.get("plan_date") or "")[:10] == t_iso and str(p.get("goal_id") or "").strip() == gid:
                    return "at_risk"

    for p in plans:
        if str(p.get("plan_date") or "")[:10] != t_iso:
            continue
        pid = str(p.get("id") or "").strip()
        rev = latest_review_by_plan.get(pid) if pid else None
        if not rev:
            continue
        if str(rev.get("decision") or "").strip().lower() != "approved":
            continue
        if not bool(rev.get("hits_goal")) or not bool(rev.get("crew_utilized")) or not bool(rev.get("blockers_addressed")):
            return "needs_attention"

    return "on_track"


def build_planning_dashboard_snapshot(
    *,
    today: date,
    goals: list[dict[str, Any]],
    plans: list[dict[str, Any]],
    pm_reviews: list[dict[str, Any]],
    eods: list[dict[str, Any]],
) -> dict[str, Any]:
    latest_by_plan = latest_pm_review_by_plan_id(pm_reviews)
    plans_by_goal: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for p in plans or []:
        if not isinstance(p, dict):
            continue
        gid = str(p.get("goal_id") or "").strip()
        if gid:
            plans_by_goal[gid].append(p)

    eods_by_goal_date: dict[tuple[str, str], dict[str, Any]] = {}
    for e in eods or []:
        if not isinstance(e, dict):
            continue
        gid = str(e.get("goal_id") or "").strip()
        ds = str(e.get("review_date") or "")[:10]
        if gid and ds:
            eods_by_goal_date[(gid, ds)] = e

    # Repeated delay: same (job_id, delay_reason) on 2+ distinct dates in 14d
    start = today - timedelta(days=13)
    triples: dict[tuple[str, str], set[str]] = defaultdict(set)
    for e in eods or []:
        if not isinstance(e, dict):
            continue
        rd = _parse_date(e.get("review_date"))
        if rd is None or rd < start or rd > today:
            continue
        jid = str(e.get("job_id") or "").strip()
        dr = str(e.get("delay_reason") or "").strip().lower()
        if not jid or not dr or dr == "none":
            continue
        triples[(jid, dr)].add(rd.isoformat())

    jobs_with_repeat: set[str] = set()
    for (jid, _dr), days in triples.items():
        if len(days) >= 2:
            jobs_with_repeat.add(jid)

    track_counts: Counter[str] = Counter()
    for g in goals or []:
        if not isinstance(g, dict):
            continue
        if not goal_covers_date(g, today):
            continue
        jid = str(g.get("job_id") or "").strip()
        tr = goal_track_status(
            g,
            today=today,
            plans_by_goal=dict(plans_by_goal),
            latest_review_by_plan=latest_by_plan,
            eods_by_goal_date=eods_by_goal_date,
            job_has_repeated_delay=jid in jobs_with_repeat,
        )
        track_counts[tr] += 1

    return {
        "goals_due_today": len(goals_due_today(goals, today=today)),
        "plans_needing_pm_review": len(plans_needing_pm_review(plans, today=today)),
        "plans_needing_adjustment": len(plans_needing_adjustment(plans)),
        "reviews_missing": len(eod_reviews_missing(today=today, goals=goals, plans=plans, eods=eods)),
        "goals_missed_today": len(goals_missed_today_from_eod(eods, today=today)),
        "repeated_delay_reasons": repeated_eod_delay_reasons(eods, today=today, days=14),
        "goal_track_on_track": track_counts.get("on_track", 0),
        "goal_track_needs_attention": track_counts.get("needs_attention", 0),
        "goal_track_at_risk": track_counts.get("at_risk", 0),
        "pm_interventions_all_time_window": pm_interventions_count(pm_reviews),
    }


def supervisor_names_from_rows(goals: list[dict[str, Any]], eods: list[dict[str, Any]]) -> list[str]:
    names: set[str] = set()
    for g in goals or []:
        if isinstance(g, dict):
            n = str(g.get("supervisor_name") or "").strip()
            if n:
                names.add(n)
    for e in eods or []:
        if isinstance(e, dict):
            n = str(e.get("supervisor_name") or "").strip()
            if n:
                names.add(n)
    return sorted(names, key=lambda x: x.lower())
