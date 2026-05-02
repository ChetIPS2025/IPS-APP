-- Daily Work Packages: PM assigns WHAT; supervisor records HOW + EOD.
-- Depends on: public.jobs, public.job_tasks, public.task_photos (053).
-- Run in Supabase SQL editor after prior workflow migrations.

-- ---------------------------------------------------------------------------
-- daily_work_packages: one row per PM-published package for a job + work day.
-- ---------------------------------------------------------------------------
create table if not exists public.daily_work_packages (
    id uuid primary key default gen_random_uuid(),
    job_id uuid not null references public.jobs (id) on delete cascade,
    work_date date not null,
    supervisor_name text not null default '',
    pm_notes text not null default '',
    status text not null default 'open' check (status in ('open', 'submitted')),
    created_by text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_daily_work_packages_work_date
    on public.daily_work_packages (work_date desc);
create index if not exists idx_daily_work_packages_job_id
    on public.daily_work_packages (job_id);

comment on table public.daily_work_packages is 'PM-defined daily work package: job, calendar work date, assigned supervisor, notes.';

-- ---------------------------------------------------------------------------
-- daily_work_package_tasks: tasks in a package with PM ordering + notes.
-- ---------------------------------------------------------------------------
create table if not exists public.daily_work_package_tasks (
    daily_work_package_id uuid not null references public.daily_work_packages (id) on delete cascade,
    job_task_id uuid not null references public.job_tasks (id) on delete cascade,
    priority_order int not null default 0,
    pm_notes text not null default '',
    primary key (daily_work_package_id, job_task_id)
);

create index if not exists idx_daily_work_package_tasks_task
    on public.daily_work_package_tasks (job_task_id);

comment on column public.daily_work_package_tasks.priority_order is 'Crew execution order (0 = first).';

-- ---------------------------------------------------------------------------
-- supervisor_daily_execution: HOW + end-of-day (1:1 with package).
-- ---------------------------------------------------------------------------
create table if not exists public.supervisor_daily_execution (
    daily_work_package_id uuid primary key references public.daily_work_packages (id) on delete cascade,
    crew_plan text not null default '',
    first_task text not null default '',
    known_blockers text not null default '',
    tools_material text not null default '',
    eod_summary text not null default '',
    delay_reason text not null default 'none' check (
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
    ),
    tomorrow_plan text not null default '',
    submitted_at timestamptz null,
    updated_at timestamptz not null default now()
);

comment on table public.supervisor_daily_execution is 'Supervisor shift plan + EOD fields for one daily work package.';

-- ---------------------------------------------------------------------------
-- task_updates: every field status/notes change tied to task + package.
-- ---------------------------------------------------------------------------
create table if not exists public.task_updates (
    id uuid primary key default gen_random_uuid(),
    job_task_id uuid not null references public.job_tasks (id) on delete cascade,
    daily_work_package_id uuid not null references public.daily_work_packages (id) on delete cascade,
    status text not null,
    notes text not null default '',
    created_by text not null default '',
    created_at timestamptz not null default now()
);

create index if not exists idx_task_updates_package on public.task_updates (daily_work_package_id);
create index if not exists idx_task_updates_task on public.task_updates (job_task_id);
create index if not exists idx_task_updates_created on public.task_updates (created_at desc);

comment on table public.task_updates is 'Append-only task status/notes log scoped to a daily work package.';

-- ---------------------------------------------------------------------------
-- task_photos: optional link to the work session (package).
-- ---------------------------------------------------------------------------
alter table if exists public.task_photos
    add column if not exists daily_work_package_id uuid null references public.daily_work_packages (id) on delete set null;

create index if not exists idx_task_photos_daily_work_package_id
    on public.task_photos (daily_work_package_id)
    where daily_work_package_id is not null;

-- ---------------------------------------------------------------------------
-- RLS (match existing app tables: authenticated read/write).
-- ---------------------------------------------------------------------------
alter table if exists public.daily_work_packages enable row level security;
drop policy if exists "dwp read" on public.daily_work_packages;
create policy "dwp read" on public.daily_work_packages for select to authenticated using (true);
drop policy if exists "dwp insert" on public.daily_work_packages;
create policy "dwp insert" on public.daily_work_packages for insert to authenticated with check (true);
drop policy if exists "dwp update" on public.daily_work_packages;
create policy "dwp update" on public.daily_work_packages for update to authenticated using (true) with check (true);
drop policy if exists "dwp delete" on public.daily_work_packages;
create policy "dwp delete" on public.daily_work_packages for delete to authenticated using (true);

alter table if exists public.daily_work_package_tasks enable row level security;
drop policy if exists "dwpt read" on public.daily_work_package_tasks;
create policy "dwpt read" on public.daily_work_package_tasks for select to authenticated using (true);
drop policy if exists "dwpt insert" on public.daily_work_package_tasks;
create policy "dwpt insert" on public.daily_work_package_tasks for insert to authenticated with check (true);
drop policy if exists "dwpt update" on public.daily_work_package_tasks;
create policy "dwpt update" on public.daily_work_package_tasks for update to authenticated using (true) with check (true);
drop policy if exists "dwpt delete" on public.daily_work_package_tasks;
create policy "dwpt delete" on public.daily_work_package_tasks for delete to authenticated using (true);

alter table if exists public.supervisor_daily_execution enable row level security;
drop policy if exists "sde read" on public.supervisor_daily_execution;
create policy "sde read" on public.supervisor_daily_execution for select to authenticated using (true);
drop policy if exists "sde insert" on public.supervisor_daily_execution;
create policy "sde insert" on public.supervisor_daily_execution for insert to authenticated with check (true);
drop policy if exists "sde update" on public.supervisor_daily_execution;
create policy "sde update" on public.supervisor_daily_execution for update to authenticated using (true) with check (true);
drop policy if exists "sde delete" on public.supervisor_daily_execution;
create policy "sde delete" on public.supervisor_daily_execution for delete to authenticated using (true);

alter table if exists public.task_updates enable row level security;
drop policy if exists "tu read" on public.task_updates;
create policy "tu read" on public.task_updates for select to authenticated using (true);
drop policy if exists "tu insert" on public.task_updates;
create policy "tu insert" on public.task_updates for insert to authenticated with check (true);
drop policy if exists "tu update" on public.task_updates;
create policy "tu update" on public.task_updates for update to authenticated using (true) with check (true);
drop policy if exists "tu delete" on public.task_updates;
create policy "tu delete" on public.task_updates for delete to authenticated using (true);
