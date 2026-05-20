-- =============================================================================
-- 000_core_bootstrap.sql
-- Parent / core tables for a FRESH Supabase project.
--
-- Run this FIRST before other sql/*.sql files. Many migrations assume
-- public.customers, public.jobs, and public.estimates already exist but never
-- CREATE them. This file prevents foreign-key failures on new databases.
--
-- Order matches MIGRATION_ORDER.md tiers 0–2 (your priority list).
-- Safe to re-run (IF NOT EXISTS / ADD COLUMN IF NOT EXISTS only).
-- =============================================================================

create extension if not exists pgcrypto;

-- -----------------------------------------------------------------------------
-- 1. customers (no FK)
-- -----------------------------------------------------------------------------
create table if not exists public.customers (
    id uuid primary key default gen_random_uuid(),
    customer_name text not null,
    address text not null default '',
    city text not null default '',
    state text not null default '',
    zip text not null default '',
    is_active boolean not null default true,
    notes text not null default '',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_customers_name on public.customers (customer_name);
create index if not exists idx_customers_active on public.customers (is_active);

comment on table public.customers is 'Customer companies (parent for jobs, estimates, sites, contacts).';

-- -----------------------------------------------------------------------------
-- 2. vendors (no FK) — reference master for PO / inventory (app + lookups)
-- -----------------------------------------------------------------------------
create table if not exists public.vendors (
    id uuid primary key default gen_random_uuid(),
    vendor_name text not null,
    contact_name text not null default '',
    email text not null default '',
    phone text not null default '',
    is_active boolean not null default true,
    notes text not null default '',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_vendors_name on public.vendors (vendor_name);
create index if not exists idx_vendors_active on public.vendors (is_active);

comment on table public.vendors is 'Vendor master (distinct from ips_lookup_values seed for dropdowns).';

-- -----------------------------------------------------------------------------
-- 3. departments (no FK) — org units; employees.department text remains for legacy
-- -----------------------------------------------------------------------------
create table if not exists public.departments (
    id uuid primary key default gen_random_uuid(),
    name text not null unique,
    is_active boolean not null default true,
    sort_order int not null default 0,
    created_at timestamptz not null default now()
);

create index if not exists idx_departments_active on public.departments (is_active, sort_order);

comment on table public.departments is 'Organizational departments (optional FK from employees later).';

-- -----------------------------------------------------------------------------
-- 4. employees (no FK to jobs; optional department_id added later if desired)
-- -----------------------------------------------------------------------------
create table if not exists public.employees (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    role text not null default '',
    trade text,
    department text not null default '',
    email text,
    phone text,
    username text,
    hourly_rate numeric(12, 2) not null default 0,
    overtime_rate numeric(12, 2),
    is_active boolean not null default true,
    notes text not null default '',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_employees_is_active on public.employees (is_active);
create index if not exists idx_employees_name_lower on public.employees (lower(name));

comment on table public.employees is 'Workforce master (timekeeping, certifications, labor).';

-- -----------------------------------------------------------------------------
-- 5. locations — customer job sites (FK → customers)
-- -----------------------------------------------------------------------------
create table if not exists public.customer_locations (
    id uuid primary key default gen_random_uuid(),
    customer_id uuid not null references public.customers (id) on delete cascade,
    site_name text not null default '',
    address_line1 text not null default '',
    address_line2 text not null default '',
    city text not null default '',
    state text not null default '',
    zip text not null default '',
    is_active boolean not null default true,
    notes text not null default '',
    created_at timestamptz not null default now()
);

create index if not exists idx_customer_locations_customer_id
    on public.customer_locations (customer_id);

comment on table public.customer_locations is 'Physical sites / locations per customer.';

-- -----------------------------------------------------------------------------
-- 6. jobs (FK → customers; contacts/locations added by 016/024)
-- -----------------------------------------------------------------------------
create table if not exists public.jobs (
    id uuid primary key default gen_random_uuid(),
    customer_id uuid references public.customers (id) on delete set null,
    job_number text,
    job_name text not null default '',
    location text not null default '',
    status text not null default 'Planning',
    project_manager text not null default '',
    supervisor text not null default '',
    start_date date,
    target_completion_date date,
    completed_date date,
    awarded_amount numeric(14, 2),
    notes text not null default '',
    estimate_id uuid,
    source_type text not null default 'standalone',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_jobs_customer_id on public.jobs (customer_id);
create index if not exists idx_jobs_status on public.jobs (status);
create unique index if not exists jobs_job_number_unique
    on public.jobs (job_number)
    where job_number is not null and trim(job_number) <> '';

comment on table public.jobs is 'Active work / costing records (parent for time, tasks, costing).';

-- -----------------------------------------------------------------------------
-- 7. estimates (FK → customers; job_id linked after jobs exist)
-- -----------------------------------------------------------------------------
create table if not exists public.estimates (
    id uuid primary key default gen_random_uuid(),
    customer_id uuid references public.customers (id) on delete set null,
    job_id uuid references public.jobs (id) on delete set null,
    quote_number text,
    customer_name text not null default '',
    project_name text not null default '',
    status text not null default 'Draft',
    subtotal numeric(14, 2) not null default 0,
    tax numeric(14, 2) not null default 0,
    total numeric(14, 2) not null default 0,
    estimate_date date,
    expiration_date date,
    prepared_by_name text not null default '',
    notes text not null default '',
    revision_number int not null default 1,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_estimates_customer_id on public.estimates (customer_id);
create index if not exists idx_estimates_job_id on public.estimates (job_id);
create index if not exists idx_estimates_quote_number on public.estimates (quote_number);

comment on table public.estimates is 'Quotes / proposals (parent for line items, revisions, attachments).';

-- Optional FK jobs.estimate_id (bidirectional link; add only when safe)
do $$
begin
    if not exists (
        select 1 from information_schema.table_constraints
        where constraint_schema = 'public'
          and table_name = 'jobs'
          and constraint_name = 'jobs_estimate_id_fkey'
    ) then
        alter table public.jobs
            add constraint jobs_estimate_id_fkey
            foreign key (estimate_id) references public.estimates (id) on delete set null;
    end if;
exception when others then
    null;
end $$;

-- -----------------------------------------------------------------------------
-- 8. inventory (no FK)
-- -----------------------------------------------------------------------------
create table if not exists public.inventory_items (
    id uuid primary key default gen_random_uuid(),
    item_name text not null,
    sku text not null default '',
    category text not null default '',
    unit text not null default 'EA',
    quantity_on_hand numeric not null default 0,
    reorder_point numeric not null default 0,
    unit_cost numeric,
    vendor text not null default '',
    storage_location text not null default '',
    notes text not null default '',
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_inventory_items_category on public.inventory_items (category);
create index if not exists idx_inventory_items_active on public.inventory_items (is_active);
create index if not exists idx_inventory_items_name on public.inventory_items (item_name);

comment on table public.inventory_items is 'Stocked supplies and consumables.';

-- -----------------------------------------------------------------------------
-- 9. assets (optional FK → jobs for assigned_job_id)
-- -----------------------------------------------------------------------------
create table if not exists public.assets (
    id uuid primary key default gen_random_uuid(),
    asset_id text unique not null,
    asset_name text not null,
    asset_type text not null default '',
    category text not null default '',
    status text not null default 'Available',
    location text not null default '',
    assigned_job_id uuid references public.jobs (id) on delete set null,
    serial_number text not null default '',
    manufacturer text not null default '',
    model text not null default '',
    notes text not null default '',
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_assets_asset_id on public.assets (asset_id);
create index if not exists idx_assets_status on public.assets (status);

comment on table public.assets is 'Tracked equipment, vehicles, tools (parent for maintenance, kits).';

-- -----------------------------------------------------------------------------
-- 10. time_entries (FK → employees, jobs)
-- -----------------------------------------------------------------------------
create table if not exists public.time_entries (
    id uuid primary key default gen_random_uuid(),
    employee_id uuid not null references public.employees (id) on delete cascade,
    job_id uuid not null references public.jobs (id) on delete cascade,
    work_date date not null,
    hours numeric(8, 2) not null default 0,
    time_type text not null default 'ST',
    notes text not null default '',
    created_by uuid,
    updated_at timestamptz not null default now()
);

create unique index if not exists uq_time_entries_employee_job_day
    on public.time_entries (employee_id, job_id, work_date);

create index if not exists idx_time_entries_work_date on public.time_entries (work_date);

comment on table public.time_entries is 'PM weekly calendar: hours per employee × job × day.';

-- -----------------------------------------------------------------------------
-- Auth profiles (requires Supabase Auth — run after enabling auth in project)
-- -----------------------------------------------------------------------------
create table if not exists public.profiles (
    id uuid primary key references auth.users (id) on delete cascade,
    email text,
    role text,
    must_reset_password boolean not null default true,
    full_name text,
    is_active boolean not null default true,
    employee_id uuid references public.employees (id) on delete set null,
    created_at timestamptz not null default now()
);

create index if not exists profiles_email_idx on public.profiles (email);
