-- Job tasks (hazard / work items) + links to PM goals, tactical plans, and EOD outcomes.
-- Run after public.jobs and sql/047_supervisor_planning_goals.sql.

create table if not exists public.job_tasks (
    id uuid primary key default gen_random_uuid(),
    job_id uuid not null references public.jobs (id) on delete cascade,
    task_number text not null default '',
    hazard_number text not null default '',
    priority text not null default 'normal' check (priority in ('low', 'normal', 'high', 'critical')),
    location text not null default '',
    issue text not null default '',
    action_required text not null default '',
    status text not null default 'open' check (
        status in (
            'open',
            'in_progress',
            'complete',
            'partial',
            'blocked',
            'not_started',
            'duplicate',
            'electrical_others',
            'customer_hold',
            'cancelled'
        )
    ),
    assigned_supervisor_id uuid null,
    planned_date date null,
    completed_date date null,
    before_photo_url text not null default '',
    after_photo_url text not null default '',
    notes text not null default '',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_job_tasks_job_id on public.job_tasks (job_id);
create index if not exists idx_job_tasks_planned_date on public.job_tasks (planned_date);
create index if not exists idx_job_tasks_status on public.job_tasks (status);
create index if not exists idx_job_tasks_priority on public.job_tasks (priority);

comment on table public.job_tasks is 'Discrete work/hazard items under a job; linked to goals, plans, and EOD.';

create table if not exists public.supervisor_goal_tasks (
    goal_id uuid not null references public.supervisor_goals (id) on delete cascade,
    task_id uuid not null references public.job_tasks (id) on delete cascade,
    created_at timestamptz not null default now(),
    primary key (goal_id, task_id)
);

create index if not exists idx_supervisor_goal_tasks_task_id on public.supervisor_goal_tasks (task_id);

create table if not exists public.supervisor_tactical_plan_tasks (
    plan_id uuid not null references public.supervisor_tactical_plans (id) on delete cascade,
    task_id uuid not null references public.job_tasks (id) on delete cascade,
    created_at timestamptz not null default now(),
    primary key (plan_id, task_id)
);

create index if not exists idx_supervisor_tactical_plan_tasks_task_id on public.supervisor_tactical_plan_tasks (task_id);

create table if not exists public.supervisor_eod_task_results (
    id uuid primary key default gen_random_uuid(),
    eod_review_id uuid not null references public.supervisor_eod_reviews (id) on delete cascade,
    task_id uuid not null references public.job_tasks (id) on delete cascade,
    outcome text not null check (
        outcome in (
            'complete',
            'partial',
            'blocked',
            'not_started',
            'duplicate',
            'electrical_others',
            'customer_hold'
        )
    ),
    notes text not null default '',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint uq_supervisor_eod_task_results_eod_task unique (eod_review_id, task_id)
);

create index if not exists idx_supervisor_eod_task_results_task_id on public.supervisor_eod_task_results (task_id);

comment on table public.supervisor_eod_task_results is 'Per-task supervisor outcome for one EOD review.';

alter table if exists public.job_tasks enable row level security;
drop policy if exists "Allow read access" on public.job_tasks;
create policy "Allow read access" on public.job_tasks for select to authenticated using (true);
drop policy if exists "Allow insert access" on public.job_tasks;
create policy "Allow insert access" on public.job_tasks for insert to authenticated with check (true);
drop policy if exists "Allow update access" on public.job_tasks;
create policy "Allow update access" on public.job_tasks for update to authenticated using (true) with check (true);
drop policy if exists "Allow delete access" on public.job_tasks;
create policy "Allow delete access" on public.job_tasks for delete to authenticated using (true);

alter table if exists public.supervisor_goal_tasks enable row level security;
drop policy if exists "Allow read access" on public.supervisor_goal_tasks;
create policy "Allow read access" on public.supervisor_goal_tasks for select to authenticated using (true);
drop policy if exists "Allow insert access" on public.supervisor_goal_tasks;
create policy "Allow insert access" on public.supervisor_goal_tasks for insert to authenticated with check (true);
drop policy if exists "Allow update access" on public.supervisor_goal_tasks;
create policy "Allow update access" on public.supervisor_goal_tasks for update to authenticated using (true) with check (true);
drop policy if exists "Allow delete access" on public.supervisor_goal_tasks;
create policy "Allow delete access" on public.supervisor_goal_tasks for delete to authenticated using (true);

alter table if exists public.supervisor_tactical_plan_tasks enable row level security;
drop policy if exists "Allow read access" on public.supervisor_tactical_plan_tasks;
create policy "Allow read access" on public.supervisor_tactical_plan_tasks for select to authenticated using (true);
drop policy if exists "Allow insert access" on public.supervisor_tactical_plan_tasks;
create policy "Allow insert access" on public.supervisor_tactical_plan_tasks for insert to authenticated with check (true);
drop policy if exists "Allow update access" on public.supervisor_tactical_plan_tasks;
create policy "Allow update access" on public.supervisor_tactical_plan_tasks for update to authenticated using (true) with check (true);
drop policy if exists "Allow delete access" on public.supervisor_tactical_plan_tasks;
create policy "Allow delete access" on public.supervisor_tactical_plan_tasks for delete to authenticated using (true);

alter table if exists public.supervisor_eod_task_results enable row level security;
drop policy if exists "Allow read access" on public.supervisor_eod_task_results;
create policy "Allow read access" on public.supervisor_eod_task_results for select to authenticated using (true);
drop policy if exists "Allow insert access" on public.supervisor_eod_task_results;
create policy "Allow insert access" on public.supervisor_eod_task_results for insert to authenticated with check (true);
drop policy if exists "Allow update access" on public.supervisor_eod_task_results;
create policy "Allow update access" on public.supervisor_eod_task_results for update to authenticated using (true) with check (true);
drop policy if exists "Allow delete access" on public.supervisor_eod_task_results;
create policy "Allow delete access" on public.supervisor_eod_task_results for delete to authenticated using (true);
