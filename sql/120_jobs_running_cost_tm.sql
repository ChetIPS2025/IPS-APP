-- =============================================================================
-- 120_jobs_running_cost_tm.sql — Cached running cost + T&M billing type on jobs
-- Depends on: 113_job_cost_transactions.sql, 118_jobs_projected_financials.sql
-- =============================================================================

alter table public.jobs
    add column if not exists actual_cost numeric(14, 2) not null default 0;

alter table public.jobs
    add column if not exists billing_type text not null default 'fixed_price';

comment on column public.jobs.actual_cost is
    'Sum of job_cost_transactions.total_cost; refreshed when ledger rows change.';

comment on column public.jobs.billing_type is
    'fixed_price or time_and_material — controls Jobs UI emphasis for running cost.';

-- Backfill running cost from ledger (safe if table empty or missing).
update public.jobs j
set actual_cost = coalesce(src.total, 0)
from (
    select job_id, round(sum(total_cost)::numeric, 2) as total
    from public.job_cost_transactions
    group by job_id
) src
where j.id = src.job_id;
