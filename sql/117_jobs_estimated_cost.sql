-- =============================================================================
-- 117_jobs_estimated_cost.sql — Manual / synced estimated cost on jobs
-- Depends on: 002_jobs.sql
-- =============================================================================

alter table public.jobs
    add column if not exists estimated_cost numeric(14, 2);

comment on column public.jobs.estimated_cost is
    'Internal cost basis for the job; synced from approved estimates or entered manually.';

comment on column public.jobs.awarded_amount is
    'Customer contract value; synced from approved estimates or entered manually.';
