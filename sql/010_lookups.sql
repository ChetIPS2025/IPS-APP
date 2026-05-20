-- =============================================================================
-- 010_lookups.sql — Admin-managed dropdown lookups + seed data
-- Depends on: 001_core.sql
-- Run after core tables; seeds align with app/utils/constants.py
-- =============================================================================

create table if not exists public.ips_lookup_tables (
    id uuid primary key default gen_random_uuid(),
    slug text not null unique,
    label text not null,
    description text not null default '',
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

create index if not exists idx_ips_lookup_values_table
    on public.ips_lookup_values (lookup_table_id, sort_order);

alter table public.ips_lookup_tables enable row level security;
alter table public.ips_lookup_values enable row level security;

drop policy if exists ips_lookup_tables_select on public.ips_lookup_tables;
create policy ips_lookup_tables_select on public.ips_lookup_tables for select to authenticated using (true);
drop policy if exists ips_lookup_tables_write on public.ips_lookup_tables;
create policy ips_lookup_tables_write on public.ips_lookup_tables
    for all to authenticated using (public.ips_is_admin()) with check (public.ips_is_admin());

drop policy if exists ips_lookup_values_select on public.ips_lookup_values;
create policy ips_lookup_values_select on public.ips_lookup_values for select to authenticated using (true);
drop policy if exists ips_lookup_values_write on public.ips_lookup_values;
create policy ips_lookup_values_write on public.ips_lookup_values
    for all to authenticated using (public.ips_is_admin()) with check (public.ips_is_admin());

-- -----------------------------------------------------------------------------
-- Seed lookup table definitions
-- -----------------------------------------------------------------------------
insert into public.ips_lookup_tables (slug, label, sort_order) values
    ('customers', 'Customers', 10),
    ('vendors', 'Vendors', 20),
    ('departments', 'Departments', 30),
    ('locations', 'Locations', 40),
    ('crews', 'Crews', 50),
    ('job_statuses', 'Job Statuses', 60),
    ('estimate_statuses', 'Estimate Statuses', 70),
    ('inventory_categories', 'Inventory Categories', 80),
    ('inventory_statuses', 'Inventory Statuses', 85),
    ('asset_categories', 'Asset Categories', 90),
    ('asset_statuses', 'Asset Statuses', 95),
    ('certification_types', 'Certification Types', 100),
    ('document_types', 'Document Types', 110),
    ('task_statuses', 'Task Statuses', 120),
    ('task_priorities', 'Task Priorities', 130),
    ('labor_types', 'Labor Types', 140),
    ('units', 'Units', 150),
    ('update_categories', 'Update Categories', 160),
    ('user_roles', 'User Roles', 170),
    ('permission_groups', 'Permission Groups', 180)
on conflict (slug) do nothing;

-- Helper: insert values for a slug
create or replace function public.ips_seed_lookup_values(p_slug text, p_values text[])
returns void
language plpgsql
as $$
declare
    v_table_id uuid;
    v_sort int := 0;
    v_val text;
begin
    select id into v_table_id from public.ips_lookup_tables where slug = p_slug limit 1;
    if v_table_id is null then
        return;
    end if;
    foreach v_val in array p_values loop
        v_sort := v_sort + 10;
        insert into public.ips_lookup_values (lookup_table_id, value, sort_order)
        values (v_table_id, v_val, v_sort)
        on conflict (lookup_table_id, value) do nothing;
    end loop;
end;
$$;

select public.ips_seed_lookup_values('customers', array[
    'Acme Industrial', 'Bayou Petrochemical', 'Coastal Refining',
    'Gulf Coast Fabricators', 'IPS Internal'
]);

select public.ips_seed_lookup_values('vendors', array[
    'Grainger', 'Ferguson Supply', 'Louisiana Welding Supply',
    'Sunbelt Rentals', 'Local Hardware Co.'
]);

select public.ips_seed_lookup_values('departments', array[
    'Field Operations', 'Project Management', 'Estimating',
    'Warehouse', 'Safety', 'Administration', 'HR'
]);

select public.ips_seed_lookup_values('locations', array[
    'Main Warehouse', 'Yard 1', 'Yard 2', 'Shop Office', 'Tool Trailer A'
]);

select public.ips_seed_lookup_values('crews', array[
    'Crew A — Field Ops', 'Crew B — Field Ops', 'Crew C — Maintenance', 'PM Support'
]);

select public.ips_seed_lookup_values('job_statuses', array[
    'Planning', 'Active', 'On Hold', 'Completed', 'Cancelled'
]);

select public.ips_seed_lookup_values('estimate_statuses', array[
    'Draft', 'Sent', 'Pending', 'Approved', 'Rejected', 'Awarded'
]);

select public.ips_seed_lookup_values('inventory_categories', array[
    'Electrical', 'Plumbing', 'Fasteners', 'Safety', 'Consumables', 'Tools'
]);

select public.ips_seed_lookup_values('inventory_statuses', array[
    'In Stock', 'Low Stock', 'Out of Stock', 'Discontinued'
]);

select public.ips_seed_lookup_values('asset_categories', array[
    'Vehicle', 'Trailer', 'Heavy Equipment', 'Tool', 'Lift', 'Generator'
]);

select public.ips_seed_lookup_values('asset_statuses', array[
    'Active', 'In Service', 'Maintenance', 'Retired', 'Disposed'
]);

select public.ips_seed_lookup_values('certification_types', array[
    'TWIC', 'OSHA 10', 'OSHA 30', 'NCCER', 'Forklift', 'Aerial Lift',
    'Confined Space', 'First Aid / CPR', 'Site Orientation', 'Fire Watch',
    'Hot Work', 'Driver''s License', 'Medical Clearance', 'Other'
]);

select public.ips_seed_lookup_values('document_types', array[
    'Driver''s License', 'TWIC Card', 'OSHA Card', 'NCCER', 'Site Orientation',
    'Medical Clearance', 'Training Record', 'Resume', 'Employment Form',
    'Safety Document', 'HR Document', 'Other'
]);

select public.ips_seed_lookup_values('task_statuses', array[
    'Open', 'In Progress', 'Blocked', 'Done', 'Cancelled'
]);

select public.ips_seed_lookup_values('task_priorities', array[
    'Low', 'Medium', 'High', 'Urgent'
]);

select public.ips_seed_lookup_values('labor_types', array['ST', 'OT', 'DT']);

select public.ips_seed_lookup_values('units', array[
    'EA', 'FT', 'LF', 'SF', 'CY', 'GAL', 'LB', 'TON', 'HR', 'DAY'
]);

select public.ips_seed_lookup_values('update_categories', array[
    'All Updates', 'Announcements', 'Safety Alerts', 'Events',
    'HR Updates', 'Project Updates'
]);

select public.ips_seed_lookup_values('user_roles', array[
    'Admin', 'Supervisor', 'Project Manager', 'Employee', 'Viewer'
]);

select public.ips_seed_lookup_values('permission_groups', array[
    'Full Access', 'Operations', 'Field Only', 'Read Only', 'HR Restricted'
]);

-- Mirror seed into departments master (optional sync)
insert into public.departments (name, sort_order)
select v.value, v.sort_order
from public.ips_lookup_values v
join public.ips_lookup_tables t on t.id = v.lookup_table_id
where t.slug = 'departments'
on conflict (name) do nothing;

drop function if exists public.ips_seed_lookup_values(text, text[]);

comment on table public.ips_lookup_tables is 'Dropdown group definitions (Admin / Settings).';
comment on table public.ips_lookup_values is 'Dropdown option values per group.';
