-- Optional site-specific contacts (nullable for legacy company-wide rows).
-- Run after public.customer_locations exists.

alter table if exists public.customer_contacts
    add column if not exists customer_location_id uuid references public.customer_locations (id) on delete set null;

create index if not exists idx_customer_contacts_customer_location_id
    on public.customer_contacts (customer_location_id);

comment on column public.customer_contacts.customer_location_id is
    'When set, contact applies to this job site; null = company-wide (legacy / fallback).';
