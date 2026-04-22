-- Profiles table for Supabase Auth-backed IPS access control
-- Required columns (per app): id, email, role, must_reset_password, created_at
-- This migration is safe to run on an existing database (adds missing columns).

create table if not exists public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  email text,
  role text,
  must_reset_password boolean not null default true,
  created_at timestamp with time zone not null default now(),
  -- Existing app compatibility fields (optional)
  full_name text,
  is_active boolean not null default true
);

alter table public.profiles
  add column if not exists email text;

alter table public.profiles
  add column if not exists role text;

alter table public.profiles
  add column if not exists must_reset_password boolean not null default true;

alter table public.profiles
  add column if not exists created_at timestamp with time zone not null default now();

alter table public.profiles
  add column if not exists full_name text;

alter table public.profiles
  add column if not exists is_active boolean not null default true;

create index if not exists profiles_email_idx on public.profiles (email);

