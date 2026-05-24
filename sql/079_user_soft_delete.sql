-- Soft-delete / deactivation fields for Users module (profiles + employees).
-- Safe to re-run. Does not remove historical records.

alter table if exists public.profiles
    add column if not exists deleted_at timestamptz;

alter table if exists public.profiles
    add column if not exists deleted_by uuid references public.profiles (id) on delete set null;

alter table if exists public.profiles
    add column if not exists deactivation_reason text;

alter table if exists public.profiles
    add column if not exists status text not null default 'Active';

alter table if exists public.employees
    add column if not exists deleted_at timestamptz;

alter table if exists public.employees
    add column if not exists deleted_by uuid references public.profiles (id) on delete set null;

alter table if exists public.employees
    add column if not exists deactivation_reason text;

alter table if exists public.employees
    add column if not exists status text not null default 'Active';

comment on column public.profiles.deleted_at is 'When the login profile was deactivated (soft delete).';
comment on column public.employees.deleted_at is 'When the workforce/user record was deactivated (soft delete).';
