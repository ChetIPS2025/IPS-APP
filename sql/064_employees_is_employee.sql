-- Users/Employees: flag whether a user record is also a workforce employee.
-- Safe to re-run.

alter table if exists public.employees
    add column if not exists is_employee boolean not null default true;

comment on column public.employees.is_employee is
    'When true, user appears in employee/timekeeping dropdowns; false = system user only.';

-- Optional auth profile mirror (when profiles link to employees)
alter table if exists public.profiles
    add column if not exists is_employee boolean not null default false;

comment on column public.profiles.is_employee is
    'Mirrors workforce eligibility for linked login profiles.';
