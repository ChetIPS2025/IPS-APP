-- =============================================================================
-- 001_core.sql — IPS Operations Platform (fresh install)
-- Tier 0: extensions, shared helpers, org master data, workforce, auth profiles
-- Run first. Safe to re-run (IF NOT EXISTS / ADD COLUMN IF NOT EXISTS).
-- =============================================================================

create extension if not exists pgcrypto;

-- -----------------------------------------------------------------------------
-- Shared: updated_at trigger
-- -----------------------------------------------------------------------------
create or replace function public.ips_set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

-- -----------------------------------------------------------------------------
-- customers
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

drop trigger if exists trg_customers_updated_at on public.customers;
create trigger trg_customers_updated_at
    before update on public.customers
    for each row execute function public.ips_set_updated_at();

-- -----------------------------------------------------------------------------
-- vendors
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

drop trigger if exists trg_vendors_updated_at on public.vendors;
create trigger trg_vendors_updated_at
    before update on public.vendors
    for each row execute function public.ips_set_updated_at();

-- -----------------------------------------------------------------------------
-- departments
-- -----------------------------------------------------------------------------
create table if not exists public.departments (
    id uuid primary key default gen_random_uuid(),
    name text not null unique,
    is_active boolean not null default true,
    sort_order int not null default 0,
    created_at timestamptz not null default now()
);

create index if not exists idx_departments_active on public.departments (is_active, sort_order);

-- -----------------------------------------------------------------------------
-- employees (workforce master — extended in 007_employees.sql)
-- -----------------------------------------------------------------------------
create table if not exists public.employees (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    email text,
    phone text,
    username text,
    role text not null default 'Employee',
    trade text,
    department text not null default '',
    department_id uuid references public.departments (id) on delete set null,
    crew text not null default '',
    position text not null default '',
    supervisor_id uuid references public.employees (id) on delete set null,
    pay_type text not null default '',
    hire_date date,
    hourly_rate numeric(12, 2) not null default 0,
    overtime_rate numeric(12, 2),
    is_active boolean not null default true,
    status text not null default 'Active',
    notes text not null default '',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_employees_is_active on public.employees (is_active);
create index if not exists idx_employees_name_lower on public.employees (lower(name));
create index if not exists idx_employees_department on public.employees (department);
create index if not exists idx_employees_role on public.employees (role);

drop trigger if exists trg_employees_updated_at on public.employees;
create trigger trg_employees_updated_at
    before update on public.employees
    for each row execute function public.ips_set_updated_at();

-- -----------------------------------------------------------------------------
-- customer_locations
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

-- -----------------------------------------------------------------------------
-- profiles (Supabase Auth — requires auth.users)
-- -----------------------------------------------------------------------------
create table if not exists public.profiles (
    id uuid primary key references auth.users (id) on delete cascade,
    email text,
    full_name text,
    role text not null default 'Employee',
    must_reset_password boolean not null default true,
    is_active boolean not null default true,
    employee_id uuid references public.employees (id) on delete set null,
    permission_group text not null default '',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_profiles_email on public.profiles (email);
create index if not exists idx_profiles_role on public.profiles (role);
create index if not exists idx_profiles_employee_id on public.profiles (employee_id);

drop trigger if exists trg_profiles_updated_at on public.profiles;
create trigger trg_profiles_updated_at
    before update on public.profiles
    for each row execute function public.ips_set_updated_at();

-- -----------------------------------------------------------------------------
-- company_settings (Admin UI — single-row style config)
-- -----------------------------------------------------------------------------
create table if not exists public.company_settings (
    id uuid primary key default gen_random_uuid(),
    company_name text not null default 'Industrial Plant Solutions',
    logo_storage_path text not null default '',
    timezone text not null default 'America/Chicago',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

drop trigger if exists trg_company_settings_updated_at on public.company_settings;
create trigger trg_company_settings_updated_at
    before update on public.company_settings
    for each row execute function public.ips_set_updated_at();

insert into public.company_settings (company_name)
select 'Industrial Plant Solutions'
where not exists (select 1 from public.company_settings limit 1);

-- -----------------------------------------------------------------------------
-- RLS helpers
-- -----------------------------------------------------------------------------
create or replace function public.ips_current_role()
returns text
language sql
stable
security definer
set search_path = public
as $$
    select coalesce(
        (select role from public.profiles where id = auth.uid() limit 1),
        'Viewer'
    );
$$;

create or replace function public.ips_is_admin()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
    select public.ips_current_role() in ('Admin', 'admin');
$$;

-- -----------------------------------------------------------------------------
-- RLS: core tables
-- -----------------------------------------------------------------------------
alter table public.customers enable row level security;
alter table public.vendors enable row level security;
alter table public.departments enable row level security;
alter table public.employees enable row level security;
alter table public.customer_locations enable row level security;
alter table public.profiles enable row level security;
alter table public.company_settings enable row level security;

drop policy if exists customers_select on public.customers;
create policy customers_select on public.customers for select to authenticated using (true);
drop policy if exists customers_write on public.customers;
create policy customers_write on public.customers for all to authenticated using (true) with check (true);

drop policy if exists vendors_select on public.vendors;
create policy vendors_select on public.vendors for select to authenticated using (true);
drop policy if exists vendors_write on public.vendors;
create policy vendors_write on public.vendors for all to authenticated using (true) with check (true);

drop policy if exists departments_select on public.departments;
create policy departments_select on public.departments for select to authenticated using (true);
drop policy if exists departments_write on public.departments;
create policy departments_write on public.departments for all to authenticated using (public.ips_is_admin()) with check (public.ips_is_admin());

drop policy if exists employees_select on public.employees;
create policy employees_select on public.employees for select to authenticated using (true);
drop policy if exists employees_write on public.employees;
create policy employees_write on public.employees for all to authenticated using (public.ips_is_admin()) with check (public.ips_is_admin());

drop policy if exists customer_locations_select on public.customer_locations;
create policy customer_locations_select on public.customer_locations for select to authenticated using (true);
drop policy if exists customer_locations_write on public.customer_locations;
create policy customer_locations_write on public.customer_locations for all to authenticated using (true) with check (true);

drop policy if exists profiles_select on public.profiles;
create policy profiles_select on public.profiles for select to authenticated using (true);
drop policy if exists profiles_update_own on public.profiles;
create policy profiles_update_own on public.profiles for update to authenticated
    using (id = auth.uid()) with check (id = auth.uid());
drop policy if exists profiles_admin_write on public.profiles;
create policy profiles_admin_write on public.profiles for all to authenticated
    using (public.ips_is_admin()) with check (public.ips_is_admin());

drop policy if exists company_settings_select on public.company_settings;
create policy company_settings_select on public.company_settings for select to authenticated using (true);
drop policy if exists company_settings_write on public.company_settings;
create policy company_settings_write on public.company_settings for all to authenticated
    using (public.ips_is_admin()) with check (public.ips_is_admin());

comment on table public.customers is 'Customer companies (parent for jobs, estimates, sites).';
comment on table public.employees is 'Workforce master (timekeeping, certifications, labor).';
comment on table public.profiles is 'Auth user profile linked to Supabase auth.users.';
