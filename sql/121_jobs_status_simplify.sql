-- =============================================================================
-- 121_jobs_status_simplify.sql — Collapse legacy job statuses to Active
-- Maps Draft, Pending, and Awarded (any casing) to Active without touching
-- Completed, Cancelled, On Hold, or lifecycle rows (Archived / Deleted).
-- =============================================================================

update public.jobs
set status = 'Active',
    updated_at = now()
where lower(trim(replace(replace(status, '_', ' '), '-', ' '))) in (
    'draft',
    'pending',
    'awarded',
    'estimate pending'
);

-- Refresh lookup dropdown values for admin Job Statuses (best-effort).
delete from public.lookup_values lv
using public.lookup_types lt
where lv.lookup_type_id = lt.id
  and lt.key = 'job_statuses'
  and lv.value in ('Draft', 'Pending', 'Awarded', 'Planning', 'Scheduled');

insert into public.lookup_values (lookup_type_id, value, sort_order, is_active)
select lt.id, v.value, v.sort_order, true
from public.lookup_types lt
cross join (
    values
        ('Active', 10),
        ('On Hold', 20),
        ('Completed', 30),
        ('Cancelled', 40)
) as v(value, sort_order)
where lt.key = 'job_statuses'
  and not exists (
      select 1
      from public.lookup_values lv2
      where lv2.lookup_type_id = lt.id
        and lv2.value = v.value
  );
