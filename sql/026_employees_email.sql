-- Work email on employee roster (additive; safe to re-run). Required for app email edit/save.
alter table public.employees add column if not exists email text;

comment on column public.employees.email is 'Contact email for roster / ops; separate from Supabase Auth login on profiles.';
