-- Estimate travel costing lines + rollup columns on estimates.
-- Safe to re-run (IF NOT EXISTS / ADD COLUMN IF NOT EXISTS).

alter table if exists public.estimates
    add column if not exists travel_cost numeric(14, 2) not null default 0;

alter table if exists public.estimates
    add column if not exists travel_markup numeric(14, 2) not null default 0;

alter table if exists public.estimates
    add column if not exists travel_price numeric(14, 2) not null default 0;

alter table if exists public.estimates
    add column if not exists default_travel_markup_pct numeric(8, 4) not null default 0;

create table if not exists public.estimate_travel (
    id uuid primary key default gen_random_uuid(),
    estimate_id uuid not null references public.estimates (id) on delete cascade,
    travel_type text not null default 'Mileage',
    description text not null default '',
    origin text not null default '',
    destination text not null default '',
    miles numeric not null default 0,
    mileage_rate numeric not null default 0,
    trips numeric not null default 1,
    people numeric not null default 1,
    travel_hours numeric not null default 0,
    hourly_rate numeric not null default 0,
    nights numeric not null default 0,
    lodging_rate numeric not null default 0,
    per_diem_days numeric not null default 0,
    per_diem_rate numeric not null default 0,
    airfare_cost numeric not null default 0,
    rental_vehicle_cost numeric not null default 0,
    fuel_cost numeric not null default 0,
    parking_tolls_cost numeric not null default 0,
    other_cost numeric not null default 0,
    cost_total numeric not null default 0,
    markup_percent numeric(8, 4) not null default 0,
    markup_amount numeric(14, 2) not null default 0,
    price_total numeric(14, 2) not null default 0,
    taxable boolean not null default false,
    notes text not null default '',
    sort_order int not null default 0,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_estimate_travel_estimate
    on public.estimate_travel (estimate_id, sort_order);

create index if not exists idx_estimate_travel_type
    on public.estimate_travel (travel_type);

drop trigger if exists trg_estimate_travel_updated_at on public.estimate_travel;
create trigger trg_estimate_travel_updated_at
    before update on public.estimate_travel
    for each row execute function public.ips_set_updated_at();

alter table if exists public.estimate_travel enable row level security;

drop policy if exists estimate_travel_all on public.estimate_travel;
create policy estimate_travel_all
    on public.estimate_travel
    for all
    to authenticated
    using (true)
    with check (true);
