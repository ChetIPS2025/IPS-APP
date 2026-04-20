-- Job costing: materials and equipment lines keyed by job_id (run after inventory_items, assets, jobs).
-- Labor for costing continues to use public.time_entries (PM grid) plus legacy employee_time_entries.

create table if not exists public.job_materials (
    id uuid primary key default gen_random_uuid(),
    job_id uuid not null,
    inventory_item_id uuid null references public.inventory_items (id) on delete set null,
    item_name text not null default '',
    quantity numeric(14, 4) not null default 0,
    unit_cost numeric(14, 4) not null default 0,
    line_total numeric(14, 2) not null default 0,
    notes text not null default '',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_job_materials_job_id on public.job_materials (job_id);

comment on table public.job_materials is 'Job costing: material usage lines per job (qty × unit cost).';

create table if not exists public.job_equipment (
    id uuid primary key default gen_random_uuid(),
    job_id uuid not null,
    asset_id uuid null references public.assets (id) on delete set null,
    asset_label text not null default '',
    usage_hours numeric(14, 4) not null default 0,
    usage_days numeric(14, 4) not null default 0,
    rate_per_hour numeric(14, 4) not null default 0,
    rate_per_day numeric(14, 4) not null default 0,
    line_total numeric(14, 2) not null default 0,
    notes text not null default '',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_job_equipment_job_id on public.job_equipment (job_id);

comment on table public.job_equipment is 'Job costing: equipment charge lines per job (hours/days × rates).';

-- RLS: align with sql/019_authenticated_crud posture.
alter table if exists public.job_materials enable row level security;

drop policy if exists "Allow read access" on public.job_materials;
create policy "Allow read access" on public.job_materials for select to authenticated using (true);

drop policy if exists "Allow insert access" on public.job_materials;
create policy "Allow insert access" on public.job_materials for insert to authenticated with check (true);

drop policy if exists "Allow update access" on public.job_materials;
create policy "Allow update access" on public.job_materials for update to authenticated using (true) with check (true);

drop policy if exists "Allow delete access" on public.job_materials;
create policy "Allow delete access" on public.job_materials for delete to authenticated using (true);

alter table if exists public.job_equipment enable row level security;

drop policy if exists "Allow read access" on public.job_equipment;
create policy "Allow read access" on public.job_equipment for select to authenticated using (true);

drop policy if exists "Allow insert access" on public.job_equipment;
create policy "Allow insert access" on public.job_equipment for insert to authenticated with check (true);

drop policy if exists "Allow update access" on public.job_equipment;
create policy "Allow update access" on public.job_equipment for update to authenticated using (true) with check (true);

drop policy if exists "Allow delete access" on public.job_equipment;
create policy "Allow delete access" on public.job_equipment for delete to authenticated using (true);
