-- Multiple job sites per customer; link estimates and jobs to a specific site.
-- Run in Supabase after public.customers exists. Does not modify customers.

create table if not exists public.customer_locations (
    id uuid primary key default gen_random_uuid(),
    customer_id uuid not null references public.customers (id) on delete cascade,
    location_name text not null default '',
    address text not null default '',
    city text not null default '',
    state text not null default '',
    zip text not null default '',
    is_active boolean not null default true,
    created_at timestamptz not null default now()
);

create index if not exists idx_customer_locations_customer_id on public.customer_locations (customer_id);
create index if not exists idx_customer_locations_active on public.customer_locations (customer_id, is_active);

comment on table public.customer_locations is 'IPS job sites / ship-to locations per customer.';

alter table if exists public.estimates
    add column if not exists customer_location_id uuid references public.customer_locations (id) on delete set null;

alter table if exists public.jobs
    add column if not exists customer_location_id uuid references public.customer_locations (id) on delete set null;

create index if not exists idx_estimates_customer_location_id on public.estimates (customer_location_id);
create index if not exists idx_jobs_customer_location_id on public.jobs (customer_location_id);

-- RLS (aligned with sql/019)
alter table if exists public.customer_locations enable row level security;

drop policy if exists "Allow read access" on public.customer_locations;
create policy "Allow read access" on public.customer_locations for select to authenticated using (true);

drop policy if exists "Allow insert access" on public.customer_locations;
create policy "Allow insert access" on public.customer_locations for insert to authenticated with check (true);

drop policy if exists "Allow update access" on public.customer_locations;
create policy "Allow update access" on public.customer_locations for update to authenticated using (true) with check (true);

drop policy if exists "Allow delete access" on public.customer_locations;
create policy "Allow delete access" on public.customer_locations for delete to authenticated using (true);
