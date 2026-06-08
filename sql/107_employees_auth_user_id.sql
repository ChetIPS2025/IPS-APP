-- Canonical link from workforce record (employees) to Supabase Auth (auth.users).
-- Password and login admin APIs must use employees.auth_user_id — never employees.id.

alter table public.employees
    add column if not exists auth_user_id uuid;

alter table public.employees
    add column if not exists profile_id uuid;

comment on column public.employees.auth_user_id is
    'Supabase Auth user id (auth.users.id). Use for login/password operations — not employees.id.';

comment on column public.employees.profile_id is
    'Legacy profiles.id mirror; prefer auth_user_id for new links.';

create index if not exists idx_employees_auth_user_id
    on public.employees (auth_user_id)
    where auth_user_id is not null;

-- Backfill from legacy profile_id when present.
update public.employees
set auth_user_id = profile_id
where auth_user_id is null
  and profile_id is not null;
