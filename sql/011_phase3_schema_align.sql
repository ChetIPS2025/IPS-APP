-- =============================================================================
-- 011_phase3_schema_align.sql — Align existing DBs with Phase 3 app services
-- Safe to run after 001–010 (uses IF NOT EXISTS / additive columns only)
-- =============================================================================

-- Jobs: denormalized estimate reference for list views
alter table public.jobs add column if not exists estimate_number text not null default '';

-- Estimates: UI fields used by save_estimate
alter table public.estimates add column if not exists customer_name text not null default '';
alter table public.estimates add column if not exists prepared_by_name text not null default '';

-- Inventory
alter table public.inventory_items add column if not exists status text not null default 'In Stock';
alter table public.inventory_items add column if not exists department text not null default '';
alter table public.inventory_items add column if not exists sku text;

-- Assets
alter table public.assets add column if not exists department text not null default '';
alter table public.assets add column if not exists current_value numeric(14, 2);

-- Employees
alter table public.employees add column if not exists status text not null default 'Active';
alter table public.employees add column if not exists crew text not null default '';
alter table public.employees add column if not exists position text not null default '';
alter table public.employees add column if not exists username text not null default '';
alter table public.employees add column if not exists notes text not null default '';

-- Company updates
alter table public.company_updates add column if not exists priority text not null default 'Normal';
alter table public.company_updates add column if not exists pinned boolean not null default false;

-- Timekeeping weeks
alter table public.employee_timekeeping_weeks add column if not exists notes text not null default '';

-- Estimate line items (materials module)
alter table public.estimate_line_items add column if not exists item_number text not null default '';
alter table public.estimate_line_items add column if not exists vendor text not null default '';
alter table public.estimate_line_items add column if not exists notes text not null default '';

-- Documents hub
alter table public.documents_hub add column if not exists storage_path text not null default '';

-- Ensure lookup slugs from 010 exist on DBs that ran an older 010
insert into public.ips_lookup_tables (slug, label, sort_order) values
    ('inventory_statuses', 'Inventory Statuses', 85),
    ('asset_statuses', 'Asset Statuses', 95),
    ('labor_types', 'Labor Types', 140),
    ('units', 'Units', 150),
    ('update_categories', 'Update Categories', 160),
    ('task_statuses', 'Task Statuses', 120),
    ('task_priorities', 'Task Priorities', 130)
on conflict (slug) do nothing;

select public.ips_seed_lookup_values('inventory_statuses', array['In Stock', 'Low Stock', 'Out of Stock', 'On Order', 'Discontinued']);
select public.ips_seed_lookup_values('asset_statuses', array['Available', 'In Use', 'Maintenance', 'Retired', 'Disposed']);
select public.ips_seed_lookup_values('units', array['EA', 'LF', 'SF', 'HR', 'DAY', 'GAL', 'LB', 'BOX']);
select public.ips_seed_lookup_values('labor_types', array['Standard', 'Overtime', 'Double Time', 'Travel', 'Per Diem']);
