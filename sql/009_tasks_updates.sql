-- =============================================================================
-- 009_tasks_updates.sql — Tasks (todos) and company updates
-- Depends on: 001_core.sql (profiles), 002_jobs.sql, 003_estimates.sql
-- =============================================================================

-- -----------------------------------------------------------------------------
-- todos (Tasks module)
-- -----------------------------------------------------------------------------
create table if not exists public.todos (
    id uuid primary key default gen_random_uuid(),
    title text not null,
    description text,
    status text not null default 'Open',
    priority text not null default 'Normal',
    due_date date,
    assigned_to uuid references public.profiles (id) on delete set null,
    assignee_name text not null default '',
    created_by uuid references public.profiles (id) on delete set null,
    job_id uuid references public.jobs (id) on delete set null,
    estimate_id uuid references public.estimates (id) on delete set null,
    job_label text not null default '',
    estimate_label text not null default '',
    notes text not null default '',
    created_at timestamptz not null default now(),
    completed_at timestamptz,
    updated_at timestamptz not null default now()
);

alter table public.todos
    drop constraint if exists todos_priority_check,
    add constraint todos_priority_check
        check (priority in ('Low', 'Normal', 'Medium', 'High', 'Urgent'));

alter table public.todos
    drop constraint if exists todos_status_check,
    add constraint todos_status_check
        check (status in ('Open', 'In Progress', 'Blocked', 'Complete', 'Done', 'Cancelled'));

create index if not exists idx_todos_status_due on public.todos (status, due_date);
create index if not exists idx_todos_assigned_to on public.todos (assigned_to);
create index if not exists idx_todos_job_id on public.todos (job_id);
create index if not exists idx_todos_estimate_id on public.todos (estimate_id);

drop trigger if exists trg_todos_updated_at on public.todos;
create trigger trg_todos_updated_at
    before update on public.todos
    for each row execute function public.ips_set_updated_at();

-- -----------------------------------------------------------------------------
-- task_activity_log
-- -----------------------------------------------------------------------------
create table if not exists public.task_activity_log (
    id uuid primary key default gen_random_uuid(),
    task_id uuid not null references public.todos (id) on delete cascade,
    description text not null default '',
    created_by uuid references public.profiles (id) on delete set null,
    created_at timestamptz not null default now()
);

create index if not exists idx_task_activity_task on public.task_activity_log (task_id, created_at desc);

-- -----------------------------------------------------------------------------
-- company_updates
-- -----------------------------------------------------------------------------
create table if not exists public.company_updates (
    id uuid primary key default gen_random_uuid(),
    title text not null,
    message text not null default '',
    body text generated always as (message) stored,
    category text not null default 'Announcements',
    priority text not null default 'Normal',
    pinned boolean not null default false,
    is_new boolean not null default true,
    event_date timestamptz,
    event_location text not null default '',
    visibility_roles text[] not null default '{}',
    visibility_departments text[] not null default '{}',
    posted_by uuid references public.profiles (id) on delete set null,
    attachment_url text,
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    expires_at timestamptz
);

alter table public.company_updates
    drop constraint if exists company_updates_category_check,
    add constraint company_updates_category_check check (
        category in (
            'All Updates',
            'Announcements',
            'Safety Alerts',
            'Events',
            'HR Updates',
            'Project Updates',
            'General',
            'Safety',
            'Schedule',
            'Policy',
            'Equipment',
            'Training',
            'Urgent'
        )
    );

alter table public.company_updates
    drop constraint if exists company_updates_priority_check,
    add constraint company_updates_priority_check check (
        priority in ('Normal', 'Important', 'Urgent')
    );

create index if not exists idx_company_updates_created_at
    on public.company_updates (created_at desc);
create index if not exists idx_company_updates_category
    on public.company_updates (category);
create index if not exists idx_company_updates_active
    on public.company_updates (is_active);
create index if not exists idx_company_updates_pinned
    on public.company_updates (pinned) where pinned = true;

drop trigger if exists trg_company_updates_updated_at on public.company_updates;
create trigger trg_company_updates_updated_at
    before update on public.company_updates
    for each row execute function public.ips_set_updated_at();

-- -----------------------------------------------------------------------------
-- company_update_reads
-- -----------------------------------------------------------------------------
create table if not exists public.company_update_reads (
    id uuid primary key default gen_random_uuid(),
    update_id uuid not null references public.company_updates (id) on delete cascade,
    user_id uuid not null references public.profiles (id) on delete cascade,
    read_at timestamptz not null default now(),
    constraint company_update_reads_unique unique (update_id, user_id)
);

create index if not exists idx_company_update_reads_user on public.company_update_reads (user_id);

-- -----------------------------------------------------------------------------
-- RLS
-- -----------------------------------------------------------------------------
alter table public.todos enable row level security;
alter table public.task_activity_log enable row level security;
alter table public.company_updates enable row level security;
alter table public.company_update_reads enable row level security;

drop policy if exists todos_select on public.todos;
create policy todos_select on public.todos for select to authenticated using (true);
drop policy if exists todos_write on public.todos;
create policy todos_write on public.todos for all to authenticated using (true) with check (true);

drop policy if exists task_activity_log_all on public.task_activity_log;
create policy task_activity_log_all on public.task_activity_log for all to authenticated using (true) with check (true);

drop policy if exists company_updates_select on public.company_updates;
create policy company_updates_select on public.company_updates for select to authenticated using (is_active = true);
drop policy if exists company_updates_write on public.company_updates;
create policy company_updates_write on public.company_updates for all to authenticated using (true) with check (true);

drop policy if exists company_update_reads_select on public.company_update_reads;
create policy company_update_reads_select on public.company_update_reads for select to authenticated using (true);
drop policy if exists company_update_reads_write on public.company_update_reads;
create policy company_update_reads_write on public.company_update_reads for all to authenticated using (true) with check (true);

comment on table public.todos is 'Tasks / to-do (IPS Tasks module). App maps Done → status Done or Complete.';
comment on column public.company_updates.message is 'App company update body text.';
