-- Per-job daily plan narrative (one row per job + work date) + after photo on task daily reviews.
-- Run after sql/049_task_workflow.sql.

create table if not exists public.job_daily_work_plans (
    id uuid primary key default gen_random_uuid(),
    job_id uuid not null references public.jobs (id) on delete cascade,
    work_date date not null,
    supervisor_name text not null default '',
    crew_plan text not null default '',
    first_task text not null default '',
    tools_material text not null default '',
    known_blockers text not null default '',
    biggest_risk text not null default '',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint uq_job_daily_work_plans_job_date unique (job_id, work_date)
);

create index if not exists idx_job_daily_work_plans_work_date on public.job_daily_work_plans (work_date desc);

comment on table public.job_daily_work_plans is 'Shift-level plan text for a job calendar day (tasks listed separately in supervisor_daily_task_plans).';

alter table if exists public.job_daily_work_plans enable row level security;
drop policy if exists "Allow read access" on public.job_daily_work_plans;
create policy "Allow read access" on public.job_daily_work_plans for select to authenticated using (true);
drop policy if exists "Allow insert access" on public.job_daily_work_plans;
create policy "Allow insert access" on public.job_daily_work_plans for insert to authenticated with check (true);
drop policy if exists "Allow update access" on public.job_daily_work_plans;
create policy "Allow update access" on public.job_daily_work_plans for update to authenticated using (true) with check (true);
drop policy if exists "Allow delete access" on public.job_daily_work_plans;
create policy "Allow delete access" on public.job_daily_work_plans for delete to authenticated using (true);

alter table if exists public.job_task_daily_reviews
    add column if not exists after_photo_url text not null default '';
