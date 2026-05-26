-- =============================================================================
-- 089_create_estimate_labor_lines.sql — Estimate labor ST/OT/DT line items
-- Depends on: public.estimates, public.employees (optional FK)
-- Safe to re-run.
-- =============================================================================

create table if not exists public.estimate_labor_lines (
    id uuid primary key default gen_random_uuid(),
    estimate_id uuid not null references public.estimates (id) on delete cascade,
    description text not null default '',
    labor_type text not null default 'Other',
    role_name text not null default '',
    employee_id uuid null references public.employees (id) on delete set null,
    hours numeric not null default 0,
    rate numeric not null default 0,
    total numeric not null default 0,
    st_hours numeric not null default 0,
    ot_hours numeric not null default 0,
    dt_hours numeric not null default 0,
    st_rate numeric not null default 0,
    ot_rate numeric not null default 0,
    dt_rate numeric not null default 0,
    cost_total numeric not null default 0,
    markup_percent numeric(8, 4) not null default 0,
    markup_amount numeric(14, 2) not null default 0,
    price_total numeric(14, 2) not null default 0,
    notes text not null default '',
    sort_order int not null default 0,
    created_at timestamptz not null default now()
);

alter table public.estimate_labor_lines
    add column if not exists role_name text not null default '',
    add column if not exists employee_id uuid references public.employees (id) on delete set null,
    add column if not exists st_hours numeric not null default 0,
    add column if not exists ot_hours numeric not null default 0,
    add column if not exists dt_hours numeric not null default 0,
    add column if not exists st_rate numeric not null default 0,
    add column if not exists ot_rate numeric not null default 0,
    add column if not exists dt_rate numeric not null default 0,
    add column if not exists cost_total numeric not null default 0,
    add column if not exists markup_percent numeric(8, 4) not null default 0,
    add column if not exists markup_amount numeric(14, 2) not null default 0,
    add column if not exists price_total numeric(14, 2) not null default 0,
    add column if not exists notes text not null default '';

update public.estimate_labor_lines
set st_hours = coalesce(nullif(st_hours, 0), hours, 0),
    st_rate = coalesce(nullif(st_rate, 0), rate, 0),
    cost_total = coalesce(nullif(cost_total, 0), total, 0),
    role_name = coalesce(nullif(role_name, ''), nullif(description, ''), labor_type, '')
where true;

create index if not exists idx_estimate_labor_estimate
    on public.estimate_labor_lines (estimate_id, sort_order);

alter table public.estimate_labor_lines enable row level security;

drop policy if exists estimate_labor_lines_all on public.estimate_labor_lines;
create policy estimate_labor_lines_all
    on public.estimate_labor_lines
    for all
    to authenticated
    using (true)
    with check (true);

comment on table public.estimate_labor_lines is 'Estimate labor lines with ST/OT/DT hours and rates.';
