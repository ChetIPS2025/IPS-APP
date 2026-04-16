-- Optional columns for customer_contacts (title + mobile). Safe if already present.

alter table public.customer_contacts
    add column if not exists title text not null default '';

alter table public.customer_contacts
    add column if not exists mobile text not null default '';

-- Backfill title from legacy role when title is empty
update public.customer_contacts
set title = coalesce(nullif(trim(role), ''), '')
where coalesce(nullif(trim(title), ''), '') = ''
  and coalesce(nullif(trim(role), ''), '') <> '';
