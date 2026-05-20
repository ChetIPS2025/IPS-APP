-- Field operations platform — Phase 1 (daily reports extensions, photos, check-ins, crew time, timeline, notifications).
-- Run in Supabase SQL editor after sql/045_supervisor_daily_reports.sql and sql/053_task_photos.sql.

-- ---------------------------------------------------------------------------
-- Daily reports: extend supervisor_daily_reports (canonical table; UI alias "Daily Reports")
-- ---------------------------------------------------------------------------
alter table if exists public.supervisor_daily_reports
    add column if not exists status text not null default 'Draft';

alter table if exists public.supervisor_daily_reports
    add column if not exists weather text not null default '';

alter table if exists public.supervisor_daily_reports
    add column if not exists safety_notes text not null default '';

alter table if exists public.supervisor_daily_reports
    add column if not exists equipment_used text not null default '';

alter table if exists public.supervisor_daily_reports
    add column if not exists materials_used text not null default '';

alter table if exists public.supervisor_daily_reports
    add column if not exists customer_conversations text not null default '';

alter table if exists public.supervisor_daily_reports
    add column if not exists hours_worked numeric(8, 2) not null default 0 check (hours_worked >= 0 and hours_worked <= 9999.99);

alter table if exists public.supervisor_daily_reports
    add column if not exists supervisor_signature text not null default '';

alter table if exists public.supervisor_daily_reports
    add column if not exists customer_signature text not null default '';

alter table if exists public.supervisor_daily_reports
    add column if not exists submitted_at timestamptz null;

alter table if exists public.supervisor_daily_reports
    add column if not exists reviewed_at timestamptz null;

alter table if exists public.supervisor_daily_reports
    add column if not exists reviewed_by uuid null;

alter table if exists public.supervisor_daily_reports
    drop constraint if exists supervisor_daily_reports_status_check;

alter table if exists public.supervisor_daily_reports
    add constraint supervisor_daily_reports_status_check
    check (status in ('Draft', 'Submitted', 'Reviewed'));

comment on column public.supervisor_daily_reports.status is 'Draft | Submitted | Reviewed';

create index if not exists idx_supervisor_daily_reports_status
    on public.supervisor_daily_reports (status, report_date desc);

-- ---------------------------------------------------------------------------
-- Job-level photo timeline (separate from task_photos)
-- ---------------------------------------------------------------------------
create table if not exists public.job_photos (
    id uuid primary key default gen_random_uuid(),
    job_id uuid not null references public.jobs (id) on delete cascade,
    task_id uuid null references public.job_tasks (id) on delete set null,
    uploaded_by text not null default '',
    caption text not null default '',
    category text not null default 'Progress',
    storage_path text not null,
    file_name text not null default '',
    content_type text not null default 'image/jpeg',
    latitude numeric(10, 7) null,
    longitude numeric(10, 7) null,
    location_note text not null default '',
    created_at timestamptz not null default now(),
    constraint job_photos_category_check check (
        category in (
            'Before', 'During', 'Completed', 'Safety', 'Damage', 'Materials', 'Progress'
        )
    )
);

create index if not exists idx_job_photos_job_created on public.job_photos (job_id, created_at desc);
create index if not exists idx_job_photos_category on public.job_photos (job_id, category);

comment on table public.job_photos is 'Job photo timeline / feed (field uploads).';

-- ---------------------------------------------------------------------------
-- GPS / manual job site check-ins
-- ---------------------------------------------------------------------------
create table if not exists public.job_checkins (
    id uuid primary key default gen_random_uuid(),
    job_id uuid not null references public.jobs (id) on delete cascade,
    user_id uuid null,
    user_name text not null default '',
    check_in_time timestamptz not null default now(),
    check_out_time timestamptz null,
    latitude numeric(10, 7) null,
    longitude numeric(10, 7) null,
    notes text not null default '',
    status text not null default 'checked_in',
    created_at timestamptz not null default now(),
    constraint job_checkins_status_check check (status in ('checked_in', 'checked_out'))
);

create index if not exists idx_job_checkins_job_in on public.job_checkins (job_id, check_in_time desc);
create index if not exists idx_job_checkins_user on public.job_checkins (user_id, check_in_time desc);

comment on table public.job_checkins is 'Supervisor/field check-in and check-out at a job site.';

-- ---------------------------------------------------------------------------
-- Crew time batches (supervisor field entry → approval → time_entries)
-- ---------------------------------------------------------------------------
create table if not exists public.crew_time_batches (
    id uuid primary key default gen_random_uuid(),
    job_id uuid not null references public.jobs (id) on delete cascade,
    work_date date not null,
    supervisor_name text not null default '',
    status text not null default 'draft',
    notes text not null default '',
    submitted_at timestamptz null,
    approved_at timestamptz null,
    approved_by uuid null,
    created_by uuid null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint crew_time_batches_status_check check (
        status in ('draft', 'submitted', 'approved')
    )
);

create index if not exists idx_crew_time_batches_job_date
    on public.crew_time_batches (job_id, work_date desc);

create table if not exists public.crew_time_entries (
    id uuid primary key default gen_random_uuid(),
    batch_id uuid not null references public.crew_time_batches (id) on delete cascade,
    employee_id uuid not null references public.employees (id) on delete cascade,
    time_type text not null default 'ST',
    hours numeric(8, 2) not null default 0 check (hours >= 0 and hours <= 24),
    notes text not null default '',
    sort_order integer not null default 0,
    constraint crew_time_entries_time_type_check check (
        time_type in ('ST', 'OT', 'DT', 'Travel', 'Per Diem')
    )
);

create index if not exists idx_crew_time_entries_batch on public.crew_time_entries (batch_id, sort_order);

comment on table public.crew_time_batches is 'Supervisor daily crew time submission header.';
comment on table public.crew_time_entries is 'Line items for a crew time batch.';

-- If crew_time_entries existed from a partial run without time_type, add it before constraints.
alter table if exists public.crew_time_entries
    add column if not exists time_type text;

update public.crew_time_entries
set time_type = 'ST'
where time_type is null or trim(time_type) = '';

alter table if exists public.crew_time_entries
    alter column time_type set default 'ST';

alter table if exists public.crew_time_entries
    alter column time_type set not null;

alter table if exists public.crew_time_entries
    drop constraint if exists crew_time_entries_time_type_check;

alter table if exists public.crew_time_entries
    add constraint crew_time_entries_time_type_check check (
        time_type in ('ST', 'OT', 'DT', 'Travel', 'Per Diem')
    );

-- Extend payroll time_entries time types (add column first — same as sql/027_time_entries_time_type.sql).
alter table if exists public.time_entries
    add column if not exists time_type text;

update public.time_entries
set time_type = 'ST'
where time_type is null or trim(time_type) = '';

alter table if exists public.time_entries
    alter column time_type set default 'ST';

alter table if exists public.time_entries
    alter column time_type set not null;

alter table if exists public.time_entries
    drop constraint if exists time_entries_time_type_check;

alter table if exists public.time_entries
    add constraint time_entries_time_type_check check (
        time_type in ('ST', 'OT', 'DT', 'Travel', 'Per Diem')
    );

comment on column public.time_entries.time_type is 'ST, OT, DT, Travel, or Per Diem; pairs with hours per job/day.';

-- ---------------------------------------------------------------------------
-- Unified job timeline / audit trail
-- ---------------------------------------------------------------------------
create table if not exists public.job_timeline (
    id uuid primary key default gen_random_uuid(),
    job_id uuid not null references public.jobs (id) on delete cascade,
    event_type text not null,
    title text not null default '',
    description text not null default '',
    user_name text not null default '',
    user_id uuid null,
    related_table text not null default '',
    related_id uuid null,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists idx_job_timeline_job_created on public.job_timeline (job_id, created_at desc);
create index if not exists idx_job_timeline_type on public.job_timeline (job_id, event_type);

comment on table public.job_timeline is 'Aggregated job activity feed for office transparency.';

-- ---------------------------------------------------------------------------
-- In-app notifications (Phase 2 hooks; basic table now)
-- ---------------------------------------------------------------------------
create table if not exists public.notifications (
    id uuid primary key default gen_random_uuid(),
    user_id uuid null,
    title text not null default '',
    body text not null default '',
    notification_type text not null default 'info',
    related_table text not null default '',
    related_id uuid null,
    read_at timestamptz null,
    created_at timestamptz not null default now()
);

create index if not exists idx_notifications_user_unread
    on public.notifications (user_id, created_at desc)
    where read_at is null;

comment on table public.notifications is 'In-app alerts; email/SMS can subscribe later.';

-- ---------------------------------------------------------------------------
-- RLS (authenticated CRUD — same posture as 045)
-- ---------------------------------------------------------------------------
alter table if exists public.job_photos enable row level security;
drop policy if exists "job_photos read" on public.job_photos;
create policy "job_photos read" on public.job_photos for select to authenticated using (true);
drop policy if exists "job_photos insert" on public.job_photos;
create policy "job_photos insert" on public.job_photos for insert to authenticated with check (true);
drop policy if exists "job_photos update" on public.job_photos;
create policy "job_photos update" on public.job_photos for update to authenticated using (true) with check (true);
drop policy if exists "job_photos delete" on public.job_photos;
create policy "job_photos delete" on public.job_photos for delete to authenticated using (true);

alter table if exists public.job_checkins enable row level security;
drop policy if exists "job_checkins read" on public.job_checkins;
create policy "job_checkins read" on public.job_checkins for select to authenticated using (true);
drop policy if exists "job_checkins insert" on public.job_checkins;
create policy "job_checkins insert" on public.job_checkins for insert to authenticated with check (true);
drop policy if exists "job_checkins update" on public.job_checkins;
create policy "job_checkins update" on public.job_checkins for update to authenticated using (true) with check (true);
drop policy if exists "job_checkins delete" on public.job_checkins;
create policy "job_checkins delete" on public.job_checkins for delete to authenticated using (true);

alter table if exists public.crew_time_batches enable row level security;
drop policy if exists "crew_time_batches read" on public.crew_time_batches;
create policy "crew_time_batches read" on public.crew_time_batches for select to authenticated using (true);
drop policy if exists "crew_time_batches insert" on public.crew_time_batches;
create policy "crew_time_batches insert" on public.crew_time_batches for insert to authenticated with check (true);
drop policy if exists "crew_time_batches update" on public.crew_time_batches;
create policy "crew_time_batches update" on public.crew_time_batches for update to authenticated using (true) with check (true);
drop policy if exists "crew_time_batches delete" on public.crew_time_batches;
create policy "crew_time_batches delete" on public.crew_time_batches for delete to authenticated using (true);

alter table if exists public.crew_time_entries enable row level security;
drop policy if exists "crew_time_entries read" on public.crew_time_entries;
create policy "crew_time_entries read" on public.crew_time_entries for select to authenticated using (true);
drop policy if exists "crew_time_entries insert" on public.crew_time_entries;
create policy "crew_time_entries insert" on public.crew_time_entries for insert to authenticated with check (true);
drop policy if exists "crew_time_entries update" on public.crew_time_entries;
create policy "crew_time_entries update" on public.crew_time_entries for update to authenticated using (true) with check (true);
drop policy if exists "crew_time_entries delete" on public.crew_time_entries;
create policy "crew_time_entries delete" on public.crew_time_entries for delete to authenticated using (true);

alter table if exists public.job_timeline enable row level security;
drop policy if exists "job_timeline read" on public.job_timeline;
create policy "job_timeline read" on public.job_timeline for select to authenticated using (true);
drop policy if exists "job_timeline insert" on public.job_timeline;
create policy "job_timeline insert" on public.job_timeline for insert to authenticated with check (true);
drop policy if exists "job_timeline update" on public.job_timeline;
create policy "job_timeline update" on public.job_timeline for update to authenticated using (true) with check (true);
drop policy if exists "job_timeline delete" on public.job_timeline;
create policy "job_timeline delete" on public.job_timeline for delete to authenticated using (true);

alter table if exists public.notifications enable row level security;
drop policy if exists "notifications read" on public.notifications;
create policy "notifications read" on public.notifications for select to authenticated using (true);
drop policy if exists "notifications insert" on public.notifications;
create policy "notifications insert" on public.notifications for insert to authenticated with check (true);
drop policy if exists "notifications update" on public.notifications;
create policy "notifications update" on public.notifications for update to authenticated using (true) with check (true);
drop policy if exists "notifications delete" on public.notifications;
create policy "notifications delete" on public.notifications for delete to authenticated using (true);
