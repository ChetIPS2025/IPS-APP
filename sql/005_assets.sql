-- =============================================================================
-- 005_assets.sql — Assets module
-- Depends on: 001_core.sql, 002_jobs.sql
-- =============================================================================

create table if not exists public.assets (
    id uuid primary key default gen_random_uuid(),
    asset_id text not null,
    asset_number text generated always as (asset_id) stored,
    asset_name text not null,
    asset_type text not null default '',
    category text not null default '',
    status text not null default 'In Service',
    location text not null default '',
    department text not null default '',
    assigned_job_id uuid references public.jobs (id) on delete set null,
    operator_employee_id uuid references public.employees (id) on delete set null,
    serial_number text not null default '',
    manufacturer text not null default '',
    model text not null default '',
    license_plate text not null default '',
    description text not null default '',
    primary_use text not null default '',
    hours_miles numeric,
    last_used_at timestamptz,
    condition text not null default '',
    acquired_date date,
    purchase_date date generated always as (acquired_date) stored,
    purchase_cost numeric(14, 2),
    current_value numeric(14, 2),
    next_service_due date,
    notes text not null default '',
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create unique index if not exists uq_assets_asset_id on public.assets (asset_id);
create index if not exists idx_assets_status on public.assets (status);
create index if not exists idx_assets_category on public.assets (category);
create index if not exists idx_assets_location on public.assets (location);
create index if not exists idx_assets_department on public.assets (department);
create index if not exists idx_assets_next_service on public.assets (next_service_due);

drop trigger if exists trg_assets_updated_at on public.assets;
create trigger trg_assets_updated_at
    before update on public.assets
    for each row execute function public.ips_set_updated_at();

-- -----------------------------------------------------------------------------
-- asset_maintenance_records
-- -----------------------------------------------------------------------------
create table if not exists public.asset_maintenance_records (
    id uuid primary key default gen_random_uuid(),
    asset_id uuid not null references public.assets (id) on delete cascade,
    service_date date not null default current_date,
    service_type text not null default '',
    description text not null default '',
    cost numeric(14, 2),
    performed_by text not null default '',
    next_due_date date,
    created_at timestamptz not null default now()
);

create index if not exists idx_asset_maintenance_asset
    on public.asset_maintenance_records (asset_id, service_date desc);

-- -----------------------------------------------------------------------------
-- asset_assignments
-- -----------------------------------------------------------------------------
create table if not exists public.asset_assignments (
    id uuid primary key default gen_random_uuid(),
    asset_id uuid not null references public.assets (id) on delete cascade,
    employee_id uuid references public.employees (id) on delete set null,
    job_id uuid references public.jobs (id) on delete set null,
    assigned_at timestamptz not null default now(),
    returned_at timestamptz,
    notes text not null default '',
    created_at timestamptz not null default now()
);

create index if not exists idx_asset_assignments_asset on public.asset_assignments (asset_id);

-- -----------------------------------------------------------------------------
-- RLS
-- -----------------------------------------------------------------------------
alter table public.assets enable row level security;
alter table public.asset_maintenance_records enable row level security;
alter table public.asset_assignments enable row level security;

drop policy if exists assets_select on public.assets;
create policy assets_select on public.assets for select to authenticated using (true);
drop policy if exists assets_write on public.assets;
create policy assets_write on public.assets for all to authenticated using (true) with check (true);

drop policy if exists asset_maintenance_all on public.asset_maintenance_records;
create policy asset_maintenance_all on public.asset_maintenance_records for all to authenticated using (true) with check (true);

drop policy if exists asset_assignments_all on public.asset_assignments;
create policy asset_assignments_all on public.asset_assignments for all to authenticated using (true) with check (true);

comment on table public.assets is 'Fleet / equipment (IPS Assets module).';
comment on column public.assets.asset_id is 'App UI: asset_number / tag.';
