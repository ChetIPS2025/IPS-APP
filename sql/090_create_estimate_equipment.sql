-- =============================================================================
-- 090_create_estimate_equipment.sql — Equipment lines for Estimate Builder
-- Depends on: 003_estimates.sql (estimates)
-- Safe to re-run. Also included in 067_estimate_costing.sql.
-- =============================================================================

create table if not exists public.estimate_equipment (
    id uuid primary key default gen_random_uuid(),
    estimate_id uuid not null references public.estimates (id) on delete cascade,
    asset_id uuid,
    equipment_name text not null default '',
    equipment_type text not null default '',
    quantity numeric not null default 1,
    duration numeric not null default 0,
    duration_unit text not null default 'Hours',
    cost_rate numeric not null default 0,
    cost_total numeric not null default 0,
    markup_percent numeric(8, 4) not null default 0,
    markup_amount numeric(14, 2) not null default 0,
    price_total numeric(14, 2) not null default 0,
    notes text not null default '',
    sort_order int not null default 0,
    created_at timestamptz not null default now()
);

create index if not exists idx_estimate_equipment_estimate
    on public.estimate_equipment (estimate_id, sort_order);

alter table if exists public.estimate_equipment enable row level security;

drop policy if exists estimate_equipment_all on public.estimate_equipment;
create policy estimate_equipment_all on public.estimate_equipment
    for all to authenticated using (true) with check (true);

comment on table public.estimate_equipment is 'Equipment rental/usage lines on an estimate (Build Estimate).';
