-- Ensure phone columns exist for Users module (profiles + employees).
-- Safe/idempotent; does not modify existing data.

alter table public.profiles
    add column if not exists phone text;

alter table public.employees
    add column if not exists phone text;

alter table if exists public.users
    add column if not exists phone text;

comment on column public.profiles.phone is 'Contact phone for auth-linked user profile.';
comment on column public.employees.phone is 'Contact phone for employee / system user record.';
