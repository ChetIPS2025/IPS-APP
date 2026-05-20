-- Phase 3: lookup tables, central documents hub, certifications, estimate lines, timekeeping weeks.
-- Run in Supabase SQL editor after prior migrations (jobs, estimates, employees, company_updates, todos).

-- ---------------------------------------------------------------------------
-- Lookup tables (dropdown values)
-- ---------------------------------------------------------------------------
create table if not exists public.ips_lookup_tables (
    id uuid primary key default gen_random_uuid(),
    slug text not null unique,
    label text not null,
    sort_order int not null default 0,
    created_at timestamptz not null default now()
);

create table if not exists public.ips_lookup_values (
    id uuid primary key default gen_random_uuid(),
    lookup_table_id uuid not null references public.ips_lookup_tables (id) on delete cascade,
    value text not null,
    sort_order int not null default 0,
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    constraint ips_lookup_values_table_value_unique unique (lookup_table_id, value)
);

create index if not exists idx_ips_lookup_values_table on public.ips_lookup_values (lookup_table_id, sort_order);

alter table public.ips_lookup_tables enable row level security;
alter table public.ips_lookup_values enable row level security;

drop policy if exists "ips_lookup_tables_select" on public.ips_lookup_tables;
create policy "ips_lookup_tables_select" on public.ips_lookup_tables for select to authenticated using (true);
drop policy if exists "ips_lookup_tables_write" on public.ips_lookup_tables;
create policy "ips_lookup_tables_write" on public.ips_lookup_tables for all to authenticated using (true) with check (true);

drop policy if exists "ips_lookup_values_select" on public.ips_lookup_values;
create policy "ips_lookup_values_select" on public.ips_lookup_values for select to authenticated using (true);
drop policy if exists "ips_lookup_values_write" on public.ips_lookup_values;
create policy "ips_lookup_values_write" on public.ips_lookup_values for all to authenticated using (true) with check (true);

-- Seed lookup table definitions (values can be managed in Admin UI)
insert into public.ips_lookup_tables (slug, label, sort_order) values
    ('customers', 'Customers', 10),
    ('vendors', 'Vendors', 20),
    ('departments', 'Departments', 30),
    ('locations', 'Locations', 40),
    ('crews', 'Crews', 50),
    ('job_statuses', 'Job Statuses', 60),
    ('estimate_statuses', 'Estimate Statuses', 70),
    ('inventory_categories', 'Inventory Categories', 80),
    ('asset_categories', 'Asset Categories', 90),
    ('certification_types', 'Certification Types', 100),
    ('document_types', 'Document Types', 110),
    ('user_roles', 'User Roles', 120),
    ('permission_groups', 'Permission Groups', 130)
on conflict (slug) do nothing;

-- ---------------------------------------------------------------------------
-- Central documents hub
-- ---------------------------------------------------------------------------
create table if not exists public.documents_hub (
    id uuid primary key default gen_random_uuid(),
    file_name text not null,
    doc_type text not null default '',
    linked_module text not null default '',
    linked_ref text not null default '',
    linked_record_id uuid null,
    upload_date date not null default current_date,
    uploaded_by text not null default '',
    expiration_date date null,
    is_restricted boolean not null default false,
    storage_path text not null default '',
    notes text not null default '',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_documents_hub_module on public.documents_hub (linked_module);
create index if not exists idx_documents_hub_type on public.documents_hub (doc_type);

alter table public.documents_hub enable row level security;
drop policy if exists "documents_hub_select" on public.documents_hub;
create policy "documents_hub_select" on public.documents_hub for select to authenticated using (true);
drop policy if exists "documents_hub_write" on public.documents_hub;
create policy "documents_hub_write" on public.documents_hub for all to authenticated using (true) with check (true);

-- ---------------------------------------------------------------------------
-- Employee certifications (HR compliance)
-- ---------------------------------------------------------------------------
create table if not exists public.employee_certifications (
    id uuid primary key default gen_random_uuid(),
    employee_id uuid not null references public.employees (id) on delete cascade,
    cert_type text not null,
    cert_number text not null default '',
    issuer text not null default '',
    issue_date date null,
    expiration_date date null,
    status text not null default 'Active',
    notes text not null default '',
    attachment_path text not null default '',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_employee_certifications_employee on public.employee_certifications (employee_id);
create index if not exists idx_employee_certifications_exp on public.employee_certifications (expiration_date);

alter table public.employee_certifications enable row level security;
drop policy if exists "employee_certifications_all" on public.employee_certifications;
create policy "employee_certifications_all" on public.employee_certifications for all to authenticated using (true) with check (true);

-- ---------------------------------------------------------------------------
-- Per-estimate material lines (UI estimate materials tab)
-- ---------------------------------------------------------------------------
create table if not exists public.estimate_line_items (
    id uuid primary key default gen_random_uuid(),
    estimate_id uuid not null,
    item_number text not null default '',
    description text not null default '',
    category text not null default '',
    qty numeric not null default 0,
    unit text not null default 'EA',
    unit_cost numeric not null default 0,
    total_cost numeric not null default 0,
    sort_order int not null default 0,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_estimate_line_items_estimate on public.estimate_line_items (estimate_id);

alter table public.estimate_line_items enable row level security;
drop policy if exists "estimate_line_items_all" on public.estimate_line_items;
create policy "estimate_line_items_all" on public.estimate_line_items for all to authenticated using (true) with check (true);

-- Optional FK when estimates table exists
do $$
begin
    if exists (
        select 1 from information_schema.tables
        where table_schema = 'public' and table_name = 'estimates'
    ) then
        alter table public.estimate_line_items
            drop constraint if exists estimate_line_items_estimate_id_fkey;
        alter table public.estimate_line_items
            add constraint estimate_line_items_estimate_id_fkey
            foreign key (estimate_id) references public.estimates (id) on delete cascade;
    end if;
exception when others then
    null;
end $$;

-- ---------------------------------------------------------------------------
-- Weekly timekeeping summaries (Phase 2C UI)
-- ---------------------------------------------------------------------------
create table if not exists public.employee_timekeeping_weeks (
    id uuid primary key default gen_random_uuid(),
    employee_id uuid not null references public.employees (id) on delete cascade,
    week_start date not null,
    st_total numeric not null default 0,
    ot_total numeric not null default 0,
    dt_total numeric not null default 0,
    status text not null default 'Pending',
    notes text not null default '',
    updated_at timestamptz not null default now(),
    constraint employee_timekeeping_weeks_unique unique (employee_id, week_start)
);

create table if not exists public.employee_timekeeping_days (
    id uuid primary key default gen_random_uuid(),
    employee_id uuid not null references public.employees (id) on delete cascade,
    week_start date not null,
    work_date date not null,
    job_label text not null default '',
    job_id uuid null references public.jobs (id) on delete set null,
    st_hours numeric not null default 0,
    ot_hours numeric not null default 0,
    dt_hours numeric not null default 0,
    notes text not null default '',
    constraint employee_timekeeping_days_unique unique (employee_id, work_date)
);

alter table public.employee_timekeeping_weeks enable row level security;
alter table public.employee_timekeeping_days enable row level security;
drop policy if exists "employee_timekeeping_weeks_all" on public.employee_timekeeping_weeks;
create policy "employee_timekeeping_weeks_all" on public.employee_timekeeping_weeks for all to authenticated using (true) with check (true);
drop policy if exists "employee_timekeeping_days_all" on public.employee_timekeeping_days;
create policy "employee_timekeeping_days_all" on public.employee_timekeeping_days for all to authenticated using (true) with check (true);

-- ---------------------------------------------------------------------------
-- Extend employees for Phase 2 UI (optional columns)
-- ---------------------------------------------------------------------------
alter table public.employees add column if not exists email text;
alter table public.employees add column if not exists department text;
alter table public.employees add column if not exists phone text;
alter table public.employees add column if not exists username text;

-- ---------------------------------------------------------------------------
-- Extend todos for linked job / estimate labels
-- ---------------------------------------------------------------------------
alter table public.todos add column if not exists job_id uuid null;
alter table public.todos add column if not exists estimate_id uuid null;
alter table public.todos add column if not exists job_label text not null default '';
alter table public.todos add column if not exists estimate_label text not null default '';
alter table public.todos add column if not exists assignee_name text not null default '';

-- ---------------------------------------------------------------------------
-- Employee documents (HR files per employee)
-- ---------------------------------------------------------------------------
create table if not exists public.employee_documents (
    id uuid primary key default gen_random_uuid(),
    employee_id uuid not null references public.employees (id) on delete cascade,
    doc_type text not null,
    file_name text not null,
    upload_date date not null default current_date,
    uploaded_by text not null default '',
    expiration_date date null,
    is_restricted boolean not null default false,
    storage_path text not null default '',
    created_at timestamptz not null default now()
);

alter table public.employee_documents enable row level security;
drop policy if exists "employee_documents_all" on public.employee_documents;
create policy "employee_documents_all" on public.employee_documents for all to authenticated using (true) with check (true);
