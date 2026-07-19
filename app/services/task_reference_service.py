"""Lightweight assignee, job, and estimate reference data for Tasks."""

from __future__ import annotations

import re

from app.pages._core.page_data_cache import page_data_cache_get

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _employees_version() -> int:
    try:
        from app.pages._core._data import employees_catalog_data_version

        return employees_catalog_data_version()
    except Exception:
        return 0


def _jobs_version() -> int:
    try:
        from app.pages._core._data import jobs_catalog_data_version

        return jobs_catalog_data_version()
    except Exception:
        return 0


def _tasks_version() -> int:
    from app.services.tasks_cache import tasks_data_version

    return tasks_data_version()


def _match_query(*parts: str, search: str) -> bool:
    query = str(search or "").strip().casefold()
    if not query:
        return True
    hay = " ".join(str(p or "") for p in parts).casefold()
    return query in hay


def resolve_task_assignee_labels(assignee_values: list[str]) -> dict[str, str]:
    """Batch-resolve assignee IDs/names for current-page tasks only."""
    from app.perf_debug import perf_span

    unique = sorted({str(v or "").strip() for v in assignee_values if str(v or "").strip()})
    if not unique:
        return {}
    emp_ver = _employees_version()
    cache_key = f"task_ref:assignees:{emp_ver}:{','.join(unique[:50])}"

    def _build() -> dict[str, str]:
        with perf_span("tasks.assignee_labels"):
            lookup: dict[str, str] = {}
            unresolved_uuids: set[str] = set()
            for val in unique:
                if val in {"—", "— Unassigned —"}:
                    continue
                if _UUID_RE.match(val):
                    unresolved_uuids.add(val)
                else:
                    lookup[val] = val
            if unresolved_uuids:
                from app.services.repository import fetch_by_id

                for uid in unresolved_uuids:
                    row = fetch_by_id("employees", uid) or fetch_by_id("user_profiles", uid)
                    if row:
                        name = str(row.get("name") or row.get("full_name") or "").strip()
                        if name:
                            lookup[uid] = name
            return lookup

    return page_data_cache_get(cache_key, _build)


def resolve_task_job_labels(job_ids: list[str]) -> dict[str, str]:
    """Batch-resolve job display labels for current-page tasks."""
    from app.perf_debug import perf_span

    unique = sorted({str(j or "").strip() for j in job_ids if str(j or "").strip()})
    if not unique:
        return {}
    jobs_ver = _jobs_version()
    cache_key = f"task_ref:jobs:{jobs_ver}:{','.join(unique[:50])}"

    def _build() -> dict[str, str]:
        with perf_span("tasks.job_labels"):
            from app.services.repository import fetch_by_id

            out: dict[str, str] = {}
            for jid in unique:
                row = fetch_by_id("jobs", jid)
                if not row:
                    continue
                num = str(row.get("job_number") or "").strip()
                name = str(row.get("job_name") or "").strip()
                if num and name:
                    out[jid] = f"{num} — {name}"
                elif num:
                    out[jid] = num
                elif name:
                    out[jid] = name
            return out

    return page_data_cache_get(cache_key, _build)


def search_task_job_options(
    *,
    search: str = "",
    include_current_ids: list[str] | None = None,
    limit: int = 100,
) -> list[dict[str, str]]:
    from app.perf_debug import perf_span

    jobs_ver = _jobs_version()
    cache_key = f"task_ref:job_opts:{jobs_ver}:{search}:{limit}"

    def _build() -> list[dict[str, str]]:
        with perf_span("tasks.form.options"):
            from app.services.repository import fetch_rows

            out: list[dict[str, str]] = [{"id": "", "label": "— None —", "display_label": "— None —"}]
            seen: set[str] = set()
            for include_id in include_current_ids or []:
                iid = str(include_id or "").strip()
                if iid and iid not in seen:
                    labels = resolve_task_job_labels([iid])
                    if iid in labels:
                        out.append({"id": iid, "label": labels[iid], "display_label": labels[iid]})
                        seen.add(iid)
            rows, err = fetch_rows("jobs", limit=min(400, limit * 4), order_by="job_number")
            if err:
                return out
            for row in rows:
                if row.get("is_deleted"):
                    continue
                jid = str(row.get("id") or "").strip()
                if not jid or jid in seen:
                    continue
                num = str(row.get("job_number") or "").strip()
                name = str(row.get("job_name") or "").strip()
                label = f"{num} — {name}" if num and name else num or name or jid
                if not _match_query(label, num, name, search=search):
                    continue
                out.append({"id": jid, "label": label, "display_label": label})
                seen.add(jid)
                if len(out) >= limit + 1:
                    break
            return out

    return page_data_cache_get(cache_key, _build)


def search_task_estimate_options(
    *,
    search: str = "",
    job_id: str | None = None,
    include_current_ids: list[str] | None = None,
    limit: int = 100,
) -> list[dict[str, str]]:
    from app.perf_debug import perf_span

    cache_key = f"task_ref:est_opts:{search}:{job_id}:{limit}"

    def _build() -> list[dict[str, str]]:
        with perf_span("tasks.form.options"):
            from app.services.repository import fetch_rows

            out: list[dict[str, str]] = [{"id": "", "label": "— None —", "display_label": "— None —"}]
            rows, err = fetch_rows("estimates", limit=min(400, limit * 4), order_by="quote_number")
            if err:
                return out
            jid = str(job_id or "").strip()
            count = 1
            for row in rows:
                eid = str(row.get("id") or "").strip()
                if not eid:
                    continue
                if jid and str(row.get("job_id") or "").strip() not in {"", jid}:
                    continue
                num = str(row.get("estimate_number") or row.get("quote_number") or "").strip()
                project = str(row.get("project_name") or row.get("name") or "").strip()
                label = f"{num} — {project}" if num and project else num or project or eid
                if not _match_query(label, num, project, search=search):
                    continue
                out.append({"id": eid, "label": label, "display_label": label})
                count += 1
                if count >= limit + 1:
                    break
            return out

    return page_data_cache_get(cache_key, _build)


def load_task_filter_options() -> dict[str, list[str]]:
    """Lightweight filter metadata — not derived from full task enrichment."""
    version = _tasks_version()
    emp_ver = _employees_version()
    jobs_ver = _jobs_version()
    cache_key = f"task_ref:filters:{version}:{emp_ver}:{jobs_ver}"

    def _build() -> dict[str, list[str]]:
        from app.perf_debug import perf_span

        with perf_span("tasks.filter_options"):
            from app.services.tasks_service import get_tasks
            from app.services.task_display_helpers import normalize_task_priority

            priorities: set[str] = set()
            assignees: set[str] = set()
            jobs: set[str] = set()
            assignee_ids: list[str] = []
            job_ids: list[str] = []
            for task in get_tasks():
                priorities.add(normalize_task_priority(task.get("priority")))
                aid = str(task.get("assigned_to") or "").strip()
                if aid and aid not in {"—", "— Unassigned —"}:
                    assignee_ids.append(aid)
                jid = str(task.get("job_id") or "").strip()
                if jid:
                    job_ids.append(jid)
            assignee_map = resolve_task_assignee_labels(assignee_ids)
            job_map = resolve_task_job_labels(job_ids)
            for task in get_tasks():
                aid = str(task.get("assigned_to") or "").strip()
                if aid and aid not in {"—", "— Unassigned —"}:
                    lbl = assignee_map.get(aid, aid if not _UUID_RE.match(aid) else "")
                    if lbl:
                        assignees.add(lbl)
                jid = str(task.get("job_id") or "").strip()
                if jid and jid in job_map:
                    jobs.add(job_map[jid])
            return {
                "priority_display": sorted(priorities),
                "assigned_to_display": sorted(assignees),
                "job_display": sorted(jobs),
            }

    return page_data_cache_get(cache_key, _build)


__all__ = [
    "load_task_filter_options",
    "resolve_task_assignee_labels",
    "resolve_task_job_labels",
    "search_task_estimate_options",
    "search_task_job_options",
]
