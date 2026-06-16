-- =============================================================================
-- 115_create_estimate_other_costs.sql — Other cost lines for Estimate Builder
-- Depends on: 003_estimates.sql (estimates)
-- Safe to re-run. Also included in 067_estimate_costing.sql.
-- =============================================================================

alter table if exists public.estimates
    add column if not exists other_cost numeric(14, 2) not null default 0;

alter table if exists public.estimates
    add column if not exists default_other_markup_pct numeric(8, 4) not null default 0;

create table if not exists public.estimate_other_costs (
    id uuid primary key default gen_random_uuid(),
    estimate_id uuid not null references public.estimates (id) on delete cascade,
    description text not null default '',
    category text not null default '',
    cost_total numeric not null default 0,
    markup_percent numeric(8, 4) not null default 0,
    markup_amount numeric(14, 2) not null default 0,
    price_total numeric(14, 2) not null default 0,
    taxable boolean not null default false,
    notes text not null default '',
    sort_order int not null default 0,
    created_at timestamptz not null default now()
);

create index if not exists idx_estimate_other_costs_estimate
    on public.estimate_other_costs (estimate_id, sort_order);

alter table if exists public.estimate_other_costs enable row level security;

drop policy if exists estimate_other_costs_all on public.estimate_other_costs;
create policy estimate_other_costs_all on public.estimate_other_costs
    for all to authenticated using (true) with check (true);

comment on table public.estimate_other_costs is 'Miscellaneous / other cost lines on an estimate (Cost Builder).';
