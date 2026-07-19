-- Scheduling module — events, crew/asset assignments, employee availability.
-- Run after sql/133_small_hand_tools_images.sql.

-- ---------------------------------------------------------------------------
-- schedule_events
-- ---------------------------------------------------------------------------
create table if not exists public.schedule_events (
    id uuid primary key default gen_random_uuid(),
    event_type text not null default 'job',
    title text not null,
    job_id uuid null references public.jobs (id) on delete set null,
    customer_id uuid null references public.customers (id) on delete set null,
    location text null,
    start_at timestamptz not null,
    end_at timestamptz not null,
    all_day boolean not null default false,
    status text not null default 'tentative',
    supervisor_id uuid null references public.employees (id) on delete set null,
    required_crew_count integer null,
    shift_name text null,
    per_diem_amount numeric(12, 2) null,
    lodging_name text null,
    lodging_address text null,
    mobilization_notes text null,
    work_instructions text null,
    internal_notes text null,
    required_certifications text[] not null default '{}'::text[],
    created_by uuid null references public.profiles (id) on delete set null,
    updated_by uuid null references public.profiles (id) on delete set null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint schedule_events_end_after_start check (end_at > start_at),
    constraint schedule_events_event_type_check check (
        event_type in (
            'job', 'travel', 'orientation', 'training', 'shop',
            'meeting', 'outage', 'time_off', 'other'
        )
    ),
    constraint schedule_events_status_check check (
        status in ('tentative', 'confirmed', 'in_progress', 'completed', 'cancelled')
    )
);

create index if not exists idx_schedule_events_start_at on public.schedule_events (start_at);
create index if not exists idx_schedule_events_end_at on public.schedule_events (end_at);
create index if not exists idx_schedule_events_job_id on public.schedule_events (job_id);
create index if not exists idx_schedule_events_supervisor_id on public.schedule_events (supervisor_id);
create index if not exists idx_schedule_events_status on public.schedule_events (status);
create index if not exists idx_schedule_events_range on public.schedule_events (start_at, end_at);

comment on table public.schedule_events is 'Planned work events — jobs, travel, training, etc.';

drop trigger if exists trg_schedule_events_updated_at on public.schedule_events;
create trigger trg_schedule_events_updated_at
    before update on public.schedule_events
    for each row execute function public.ips_set_updated_at();

-- ---------------------------------------------------------------------------
-- schedule_event_employees
-- ---------------------------------------------------------------------------
create table if not exists public.schedule_event_employees (
    id uuid primary key default gen_random_uuid(),
    schedule_event_id uuid not null references public.schedule_events (id) on delete cascade,
    employee_id uuid not null references public.employees (id) on delete cascade,
    assignment_role text null,
    is_supervisor boolean not null default false,
    notes text null,
    created_at timestamptz not null default now(),
    constraint schedule_event_employees_unique unique (schedule_event_id, employee_id)
);

create index if not exists idx_schedule_event_employees_event
    on public.schedule_event_employees (schedule_event_id);
create index if not exists idx_schedule_event_employees_employee
    on public.schedule_event_employees (employee_id);

-- ---------------------------------------------------------------------------
-- schedule_event_assets
-- ---------------------------------------------------------------------------
create table if not exists public.schedule_event_assets (
    id uuid primary key default gen_random_uuid(),
    schedule_event_id uuid not null references public.schedule_events (id) on delete cascade,
    asset_id uuid not null references public.assets (id) on delete cascade,
    quantity numeric(12, 2) null default 1,
    notes text null,
    created_at timestamptz not null default now(),
    constraint schedule_event_assets_unique unique (schedule_event_id, asset_id)
);

create index if not exists idx_schedule_event_assets_event
    on public.schedule_event_assets (schedule_event_id);
create index if not exists idx_schedule_event_assets_asset
    on public.schedule_event_assets (asset_id);

-- ---------------------------------------------------------------------------
-- employee_availability
-- ---------------------------------------------------------------------------
create table if not exists public.employee_availability (
    id uuid primary key default gen_random_uuid(),
    employee_id uuid not null references public.employees (id) on delete cascade,
    start_at timestamptz not null,
    end_at timestamptz not null,
    availability_type text not null,
    notes text null,
    created_by uuid null references public.profiles (id) on delete set null,
    created_at timestamptz not null default now(),
    constraint employee_availability_end_after_start check (end_at > start_at),
    constraint employee_availability_type_check check (
        availability_type in (
            'unavailable', 'vacation', 'sick', 'training', 'available', 'other'
        )
    )
);

create index if not exists idx_employee_availability_employee
    on public.employee_availability (employee_id);
create index if not exists idx_employee_availability_start
    on public.employee_availability (start_at);
create index if not exists idx_employee_availability_end
    on public.employee_availability (end_at);

-- ---------------------------------------------------------------------------
-- RLS helpers
-- ---------------------------------------------------------------------------
create or replace function public.ips_current_employee_id()
returns uuid
language sql
stable
security definer
set search_path = public
as $$
    select employee_id from public.profiles where id = auth.uid() limit 1;
$$;

create or replace function public.ips_can_manage_scheduling()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
    select public.ips_is_admin()
        or public.ips_current_role() in ('Supervisor', 'Project Manager', 'Admin', 'admin');
$$;

create or replace function public.ips_schedule_event_visible(ev public.schedule_events)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
    select public.ips_can_manage_scheduling()
        or ev.supervisor_id = public.ips_current_employee_id()
        or exists (
            select 1
            from public.schedule_event_employees see
            where see.schedule_event_id = ev.id
              and see.employee_id = public.ips_current_employee_id()
        );
$$;

-- ---------------------------------------------------------------------------
-- RLS policies
-- ---------------------------------------------------------------------------
alter table public.schedule_events enable row level security;
alter table public.schedule_event_employees enable row level security;
alter table public.schedule_event_assets enable row level security;
alter table public.employee_availability enable row level security;

drop policy if exists schedule_events_select on public.schedule_events;
create policy schedule_events_select on public.schedule_events
    for select to authenticated
    using (public.ips_schedule_event_visible(schedule_events));

drop policy if exists schedule_events_write on public.schedule_events;
create policy schedule_events_write on public.schedule_events
    for all to authenticated
    using (public.ips_can_manage_scheduling())
    with check (public.ips_can_manage_scheduling());

drop policy if exists schedule_event_employees_select on public.schedule_event_employees;
create policy schedule_event_employees_select on public.schedule_event_employees
    for select to authenticated
    using (
        public.ips_can_manage_scheduling()
        or employee_id = public.ips_current_employee_id()
        or exists (
            select 1 from public.schedule_events ev
            where ev.id = schedule_event_employees.schedule_event_id
              and public.ips_schedule_event_visible(ev)
        )
    );

drop policy if exists schedule_event_employees_write on public.schedule_event_employees;
create policy schedule_event_employees_write on public.schedule_event_employees
    for all to authenticated
    using (public.ips_can_manage_scheduling())
    with check (public.ips_can_manage_scheduling());

drop policy if exists schedule_event_assets_select on public.schedule_event_assets;
create policy schedule_event_assets_select on public.schedule_event_assets
    for select to authenticated
    using (
        public.ips_can_manage_scheduling()
        or exists (
            select 1 from public.schedule_events ev
            where ev.id = schedule_event_assets.schedule_event_id
              and public.ips_schedule_event_visible(ev)
        )
    );

drop policy if exists schedule_event_assets_write on public.schedule_event_assets;
create policy schedule_event_assets_write on public.schedule_event_assets
    for all to authenticated
    using (public.ips_can_manage_scheduling())
    with check (public.ips_can_manage_scheduling());

drop policy if exists employee_availability_select on public.employee_availability;
create policy employee_availability_select on public.employee_availability
    for select to authenticated
    using (
        public.ips_can_manage_scheduling()
        or employee_id = public.ips_current_employee_id()
    );

drop policy if exists employee_availability_write on public.employee_availability;
create policy employee_availability_write on public.employee_availability
    for all to authenticated
    using (
        public.ips_can_manage_scheduling()
        or employee_id = public.ips_current_employee_id()
    )
    with check (
        public.ips_can_manage_scheduling()
        or employee_id = public.ips_current_employee_id()
    );
