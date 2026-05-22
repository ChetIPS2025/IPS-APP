-- Customer hierarchy: company -> locations -> contacts
-- Safe to re-run (IF NOT EXISTS / ADD COLUMN IF NOT EXISTS).

-- -----------------------------------------------------------------------------
-- customers — extend parent company fields (keep legacy address columns)
-- -----------------------------------------------------------------------------
alter table if exists public.customers
    add column if not exists customer_number text not null default '';

alter table if exists public.customers
    add column if not exists website text not null default '';

alter table if exists public.customers
    add column if not exists main_phone text not null default '';

alter table if exists public.customers
    add column if not exists main_email text not null default '';

alter table if exists public.customers
    add column if not exists billing_email text not null default '';

alter table if exists public.customers
    add column if not exists status text not null default 'Active';

comment on column public.customers.address is 'Legacy default address; prefer customer_locations for sites.';

-- -----------------------------------------------------------------------------
-- customer_locations — sites / plants / offices
-- -----------------------------------------------------------------------------
alter table if exists public.customer_locations
    add column if not exists location_type text not null default 'Other';

alter table if exists public.customer_locations
    add column if not exists address_line_1 text not null default '';

alter table if exists public.customer_locations
    add column if not exists address_line_2 text not null default '';

alter table if exists public.customer_locations
    add column if not exists country text not null default 'USA';

alter table if exists public.customer_locations
    add column if not exists phone text not null default '';

alter table if exists public.customer_locations
    add column if not exists email text not null default '';

alter table if exists public.customer_locations
    add column if not exists is_primary boolean not null default false;

alter table if exists public.customer_locations
    add column if not exists is_billing boolean not null default false;

alter table if exists public.customer_locations
    add column if not exists is_shipping boolean not null default false;

alter table if exists public.customer_locations
    add column if not exists status text not null default 'Active';

alter table if exists public.customer_locations
    add column if not exists notes text not null default '';

alter table if exists public.customer_locations
    add column if not exists updated_at timestamptz not null default now();

-- Bridge legacy column names
alter table if exists public.customer_locations
    add column if not exists site_name text not null default '';

alter table if exists public.customer_locations
    add column if not exists location_name text not null default '';

alter table if exists public.customer_locations
    add column if not exists address text not null default '';

alter table if exists public.customer_locations
    add column if not exists is_active boolean not null default true;

-- Backfill location_name / site_name from whichever exists
update public.customer_locations
set location_name = coalesce(nullif(location_name, ''), nullif(site_name, ''), 'Main Location')
where coalesce(location_name, '') = '';

update public.customer_locations
set site_name = coalesce(nullif(site_name, ''), nullif(location_name, ''), 'Main Location')
where coalesce(site_name, '') = '';

update public.customer_locations
set address_line_1 = coalesce(nullif(address_line_1, ''), nullif(address, ''), '')
where coalesce(address_line_1, '') = '';

update public.customer_locations
set address = coalesce(nullif(address, ''), nullif(address_line_1, ''), '')
where coalesce(address, '') = '';

update public.customer_locations
set status = case when is_active then 'Active' else 'Inactive' end
where coalesce(status, '') = '';

-- -----------------------------------------------------------------------------
-- customer_contacts — location-scoped people
-- -----------------------------------------------------------------------------
alter table if exists public.customer_contacts
    add column if not exists full_name text not null default '';

alter table if exists public.customer_contacts
    add column if not exists department text not null default '';

alter table if exists public.customer_contacts
    add column if not exists mobile text not null default '';

alter table if exists public.customer_contacts
    add column if not exists role_type text not null default 'Other';

alter table if exists public.customer_contacts
    add column if not exists is_estimating_contact boolean not null default false;

alter table if exists public.customer_contacts
    add column if not exists is_billing_contact boolean not null default false;

alter table if exists public.customer_contacts
    add column if not exists is_site_contact boolean not null default false;

alter table if exists public.customer_contacts
    add column if not exists is_safety_contact boolean not null default false;

alter table if exists public.customer_contacts
    add column if not exists status text not null default 'Active';

alter table if exists public.customer_contacts
    add column if not exists updated_at timestamptz not null default now();

alter table if exists public.customer_contacts
    add column if not exists location_id uuid references public.customer_locations (id) on delete cascade;

-- Mirror legacy nullable scope column
alter table if exists public.customer_contacts
    add column if not exists customer_location_id uuid references public.customer_locations (id) on delete set null;

update public.customer_contacts
set full_name = coalesce(nullif(full_name, ''), nullif(contact_name, ''), '')
where coalesce(full_name, '') = '';

update public.customer_contacts
set contact_name = coalesce(nullif(contact_name, ''), nullif(full_name, ''), '')
where coalesce(contact_name, '') = '';

update public.customer_contacts
set role_type = coalesce(nullif(role_type, ''), nullif(title, ''), nullif(role, ''), 'Other')
where coalesce(role_type, '') in ('', 'Other');

update public.customer_contacts
set location_id = customer_location_id
where location_id is null and customer_location_id is not null;

update public.customer_contacts
set customer_location_id = location_id
where customer_location_id is null and location_id is not null;

update public.customer_contacts
set status = case when is_active then 'Active' else 'Inactive' end
where coalesce(status, '') = '';

-- -----------------------------------------------------------------------------
-- jobs / estimates FKs
-- -----------------------------------------------------------------------------
alter table if exists public.jobs
    add column if not exists customer_location_id uuid references public.customer_locations (id) on delete set null;

alter table if exists public.jobs
    add column if not exists customer_contact_id uuid references public.customer_contacts (id) on delete set null;

alter table if exists public.estimates
    add column if not exists customer_location_id uuid references public.customer_locations (id) on delete set null;

alter table if exists public.estimates
    add column if not exists customer_contact_id uuid references public.customer_contacts (id) on delete set null;

create index if not exists idx_jobs_customer_contact_id on public.jobs (customer_contact_id);
create index if not exists idx_estimates_customer_contact_id on public.estimates (customer_contact_id);

-- -----------------------------------------------------------------------------
-- Data migration: one primary location per legacy customer address
-- -----------------------------------------------------------------------------
insert into public.customer_locations (
    customer_id,
    location_name,
    site_name,
    location_type,
    address_line_1,
    address,
    city,
    state,
    zip,
    country,
    is_primary,
    is_active,
    status,
    notes
)
select
    c.id,
    c.customer_name || ' Main Location',
    c.customer_name || ' Main Location',
    'Office',
    coalesce(c.address, ''),
    coalesce(c.address, ''),
    coalesce(c.city, ''),
    coalesce(c.state, ''),
    coalesce(c.zip, ''),
    'USA',
    true,
    c.is_active,
    case when c.is_active then 'Active' else 'Inactive' end,
    'Auto-created from legacy customer address.'
from public.customers c
where not exists (
    select 1 from public.customer_locations cl where cl.customer_id = c.id
)
and (
    coalesce(c.address, '') <> ''
    or coalesce(c.city, '') <> ''
    or coalesce(c.state, '') <> ''
    or coalesce(c.zip, '') <> ''
);

-- Customers with no address at all still get a placeholder primary location
insert into public.customer_locations (
    customer_id,
    location_name,
    site_name,
    location_type,
    is_primary,
    is_active,
    status,
    notes
)
select
    c.id,
    c.customer_name || ' Main Location',
    c.customer_name || ' Main Location',
    'Office',
    true,
    c.is_active,
    case when c.is_active then 'Active' else 'Inactive' end,
    'Auto-created primary location.'
from public.customers c
where not exists (
    select 1 from public.customer_locations cl where cl.customer_id = c.id
);
