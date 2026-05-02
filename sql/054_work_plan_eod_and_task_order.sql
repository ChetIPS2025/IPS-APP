-- Task order on daily plan + supervisor end-of-day fields on job daily work plan.
-- Run after sql/050_job_daily_work_plan_and_review_photo.sql.

alter table if exists public.supervisor_daily_task_plans
    add column if not exists sort_order smallint not null default 0;

create index if not exists idx_supervisor_daily_task_plans_job_date_order
    on public.supervisor_daily_task_plans (job_id, work_date, sort_order);

comment on column public.supervisor_daily_task_plans.sort_order is 'Execution order within a job day (0 = first).';

alter table if exists public.job_daily_work_plans
    add column if not exists eod_summary text not null default '';

alter table if exists public.job_daily_work_plans
    add column if not exists eod_delay_reason text not null default 'none';

alter table if exists public.job_daily_work_plans
    add column if not exists tomorrow_plan text not null default '';

comment on column public.job_daily_work_plans.eod_summary is 'Supervisor end-of-day narrative.';
comment on column public.job_daily_work_plans.eod_delay_reason is 'Coarse delay slug for the shift (same vocabulary as task reviews).';
comment on column public.job_daily_work_plans.tomorrow_plan is 'Plan for the next workday.';
