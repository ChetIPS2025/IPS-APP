-- Run in Supabase SQL editor after prior migrations. Requires public.employee_time_entries.

create table if not exists public.employees (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    role text default '',
    trade text,
    hourly_rate numeric(12,2) not null default 0,
    overtime_rate numeric(12,2),
    is_active boolean not null default true,
    notes text,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create index if not exists idx_employees_is_active on public.employees(is_active);
create index if not exists idx_employees_name_lower on public.employees(lower(name));

-- Link time entries to employees; store computed labor dollars at save time (point-in-time).
alter table public.employee_time_entries
    add column if not exists employee_id uuid references public.employees(id) on delete set null;

alter table public.employee_time_entries
    add column if not exists labor_cost numeric(12,2);

comment on table public.employees is 'Workforce master: rates drive time entry labor_cost when employee_id is set.';
comment on column public.employee_time_entries.labor_cost is 'ST/OT dollars from employee hourly/overtime rates when saved; null on legacy rows uses labor classification rates in Job Costing.';
