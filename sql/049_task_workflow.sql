-- Task-based workflow: status values, supervisor assignment name, daily plan + daily review.
-- Run after sql/048_job_tasks_planning_links.sql.

alter table if exists public.job_tasks
    add column if not exists assigned_supervisor_name text not null default '';

alter table if exists public.job_tasks drop constraint if exists job_tasks_status_check;

update public.job_tasks
set status = case
    when status = 'open' then 'not_started'
    when status = 'electrical_others' then 'electrical'
    when status = 'customer_hold' then 'waiting_on_customer'
    else status
end
where status in ('open', 'electrical_others', 'customer_hold');

update public.job_tasks
set status = 'not_started'
where status not in (
    'not_started',
    'in_progress',
    'complete',
    'partial',
    'blocked',
    'duplicate',
    'electrical',
    'waiting_on_customer',
    'cancelled'
);

alter table if exists public.job_tasks
    add constraint job_tasks_status_check check (
        status in (
            'not_started',
            'in_progress',
            'complete',
            'partial',
            'blocked',
            'duplicate',
            'electrical',
            'waiting_on_customer',
            'cancelled'
        )
    );

alter table if exists public.job_tasks alter column status set default 'not_started';

create table if not exists public.supervisor_daily_task_plans (
    id uuid primary key default gen_random_uuid(),
    job_id uuid not null references public.jobs (id) on delete cascade,
    work_date date not null,
    supervisor_name text not null default '',
    task_id uuid not null references public.job_tasks (id) on delete cascade,
    created_at timestamptz not null default now(),
    constraint uq_supervisor_daily_task_plans_job_date_task unique (job_id, work_date, task_id)
);

create index if not exists idx_supervisor_daily_task_plans_work_date on public.supervisor_daily_task_plans (work_date desc);
create index if not exists idx_supervisor_daily_task_plans_task_id on public.supervisor_daily_task_plans (task_id);

comment on table public.supervisor_daily_task_plans is 'Supervisor-selected tasks for a calendar work day on a job.';

create table if not exists public.job_task_daily_reviews (
    id uuid primary key default gen_random_uuid(),
    task_id uuid not null references public.job_tasks (id) on delete cascade,
    review_date date not null,
    supervisor_name text not null default '',
    status_after text not null,
    delay_reason text not null default 'none',
    notes text not null default '',
    created_at timestamptz not null default now(),
    constraint uq_job_task_daily_reviews_task_date unique (task_id, review_date),
    constraint job_task_daily_reviews_status_check check (
        status_after in (
            'not_started',
            'in_progress',
            'complete',
            'partial',
            'blocked',
            'duplicate',
            'electrical',
            'waiting_on_customer',
            'cancelled'
        )
    ),
    constraint job_task_daily_reviews_delay_check check (
        delay_reason in (
            'none',
            'material',
            'tools',
            'direction',
            'rework',
            'customer',
            'safety',
            'equipment',
            'weather',
            'other'
        )
    )
);

create index if not exists idx_job_task_daily_reviews_review_date on public.job_task_daily_reviews (review_date desc);

comment on table public.job_task_daily_reviews is 'End-of-day update per task (status, delay, notes).';

alter table if exists public.supervisor_daily_task_plans enable row level security;
drop policy if exists "Allow read access" on public.supervisor_daily_task_plans;
create policy "Allow read access" on public.supervisor_daily_task_plans for select to authenticated using (true);
drop policy if exists "Allow insert access" on public.supervisor_daily_task_plans;
create policy "Allow insert access" on public.supervisor_daily_task_plans for insert to authenticated with check (true);
drop policy if exists "Allow update access" on public.supervisor_daily_task_plans;
create policy "Allow update access" on public.supervisor_daily_task_plans for update to authenticated using (true) with check (true);
drop policy if exists "Allow delete access" on public.supervisor_daily_task_plans;
create policy "Allow delete access" on public.supervisor_daily_task_plans for delete to authenticated using (true);

alter table if exists public.job_task_daily_reviews enable row level security;
drop policy if exists "Allow read access" on public.job_task_daily_reviews;
create policy "Allow read access" on public.job_task_daily_reviews for select to authenticated using (true);
drop policy if exists "Allow insert access" on public.job_task_daily_reviews;
create policy "Allow insert access" on public.job_task_daily_reviews for insert to authenticated with check (true);
drop policy if exists "Allow update access" on public.job_task_daily_reviews;
create policy "Allow update access" on public.job_task_daily_reviews for update to authenticated using (true) with check (true);
drop policy if exists "Allow delete access" on public.job_task_daily_reviews;
create policy "Allow delete access" on public.job_task_daily_reviews for delete to authenticated using (true);
